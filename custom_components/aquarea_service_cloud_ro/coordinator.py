"""Read-only port of the original Go client's HTTP sequence."""
from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import time
from urllib.parse import urlencode

from aiohttp import ClientError

from .const import (
    HISTORY_FIELDS, HISTORY_LOOKBACK, HISTORY_POLL_INTERVAL,
    SERVICE_URL, STATUS_FIELDS, TRANSLATIONS,
)

_LOGGER = logging.getLogger(__name__)
_TOKEN = re.compile(r"""\bconst\s+shiesuahruefutohkun\s*=\s*['"]([^'"]+)['"]""")


class AquareaAuthError(Exception):
    """Authentication was rejected by Panasonic."""


class AquareaProtocolError(Exception):
    """Panasonic returned an unexpected payload."""

    def __init__(self, stage: str):
        self.stage = stage
        super().__init__(stage)


def _error_codes(payload):
    """Return codes without upstream messages or personal data."""
    codes = []
    if payload.get("errorCode") not in (None, 0, "0"):
        codes.append(str(payload["errorCode"]))
    for item in payload.get("message") or []:
        if isinstance(item, dict) and item.get("errorCode"):
            codes.append(str(item["errorCode"]))
    return codes


class AquareaClient:
    def __init__(self, session, username: str, password: str, device_id: str | None = None, gw_uid: str | None = None):
        self._username = username
        self._password = password
        self._device_id = device_id
        self._gw_uid = gw_uid
        self._token = ""
        self._authenticated = False
        self._session = session
        self._history = {}
        self._next_history_poll = 0.0

    def async_close(self):
        """Detach this isolated session from Home Assistant's connector."""
        self._session.detach()

    async def _request(self, method, path, data=None):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:74.0) Gecko/20100101 Firefox/74.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
            "Accept-Encoding": "gzip, deflate, br" if not path else "deflate, br",
        }
        if data is not None:
            # Go sorts form field names and preserves empty values.
            data = urlencode(sorted(data.items()))
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        # Preserve Go's concatenation, including its //installer paths.
        async with self._session.request(
            method, SERVICE_URL + path, data=data, headers=headers
        ) as response:
            response.raise_for_status()
            return await response.text()

    @staticmethod
    def _page_token(html, fallback=""):
        match = _TOKEN.search(html)
        # Go continues when no token is found and still sends the empty field.
        return match.group(1) if match else fallback

    @staticmethod
    def _json(raw, stage):
        try:
            payload = json.loads(raw)
        except ValueError as err:
            raise AquareaProtocolError(stage) from err
        if not isinstance(payload, dict):
            raise AquareaProtocolError(stage)
        return payload

    async def async_login_and_list_devices(self):
        self._authenticated = False
        root = await self._request("GET", "")
        self._token = self._page_token(root, self._token)
        digest = hashlib.md5((self._username + self._password).encode()).hexdigest()
        raw = await self._request("POST", "installer/api/auth/login", {
            "var.loginId": self._username, "var.password": digest,
            "var.inputOmit": "false", "shiesuahruefutohkun": self._token,
        })
        login = self._json(raw, "login_response_invalid")
        if _error_codes(login):
            raise AquareaAuthError

        home = await self._request("GET", "installer/home")
        # GetInstallerHome in Go uses a separate local token for this request.
        home_token = self._page_token(home)
        raw = await self._request("POST", "/installer/api/endusers", {
            "var.name": "", "var.deviceId": "", "var.idu": "", "var.odu": "",
            "var.sortItem": "userName", "var.sortOrder": "0", "var.offset": "0",
            "var.limit": "999", "var.mapSizeX": "0", "var.mapSizeY": "0",
            "var.readNew": "1", "shiesuahruefutohkun": home_token,
        })
        payload = self._json(raw, "device_list_invalid")
        codes = _error_codes(payload)
        if codes:
            _LOGGER.warning("Panasonic device list error codes: %s", codes)
            raise ClientError("Panasonic rejected device list request")
        self._authenticated = True
        return {
            d["deviceId"]: {"id": d["deviceId"], "gw_uid": d.get("gwUid", ""), "name": d.get("name") or "Aquarea"}
            for d in payload.get("endusers", []) if d.get("deviceId")
        }

    async def async_get_status(self):
        if not self._authenticated:
            devices = await self.async_login_and_list_devices()
            self._gw_uid = devices.get(self._device_id, {}).get("gw_uid", self._gw_uid)
        payload = await self._async_fetch_status()
        if _error_codes(payload):
            self._authenticated = False
            devices = await self.async_login_and_list_devices()
            self._gw_uid = devices.get(self._device_id, {}).get("gw_uid", self._gw_uid)
            payload = await self._async_fetch_status()
        codes = _error_codes(payload)
        if codes:
            _LOGGER.warning("Panasonic status error codes: %s", codes)
            raise ClientError("Panasonic rejected status request")
        info = payload.get("statusDataInfo")
        if not isinstance(info, dict) or not any(key.startswith("function-status-text-") for key in info):
            _LOGGER.warning("Panasonic status has no readings; response fields: %s", sorted(payload.keys()))
            raise ClientError("Panasonic status response did not include readings")
        result = {}
        for name, (suffix, field) in STATUS_FIELDS.items():
            value = info.get(f"function-status-text-{suffix}", {}).get(field)
            if value in (None, "", "-"):
                result[name] = None
            elif field == "textValue":
                result[name] = TRANSLATIONS.get(value, value)
            else:
                result[name] = value
        await self._async_update_history()
        for name in HISTORY_FIELDS:
            result[name] = self._history.get(name, {}).get("value")
        result["_history"] = {key: dict(sample) for key, sample in self._history.items()}
        return result

    @staticmethod
    def _latest_history_sample(payload, now):
        """Decode one requested log item; timestamps are milliseconds since epoch."""
        data = payload.get("logData")
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except ValueError:
                return None
        if not isinstance(data, dict):
            return None
        latest = None
        for raw_timestamp, row in data.items():
            if not isinstance(row, list) or len(row) != 1 or isinstance(row[0], bool):
                continue
            try:
                timestamp = int(raw_timestamp) / 1000
                value = float(row[0])
            except (TypeError, ValueError, OverflowError):
                continue
            if not math.isfinite(value) or value < 0 or timestamp <= 0 or timestamp > now + 60:
                continue
            if latest is None or timestamp > latest["timestamp"]:
                latest = {"value": value, "timestamp": timestamp}
        return latest

    async def _async_update_history(self):
        """History failures affect only the new sensors, not working status reads."""
        if time.monotonic() < self._next_history_poll:
            return
        self._next_history_poll = time.monotonic() + HISTORY_POLL_INTERVAL
        now = time.time()
        for name, index in HISTORY_FIELDS.items():
            try:
                # Request one field per response so column order is unambiguous.
                raw = await self._request("POST", "/installer/api/data/log", {
                    "var.deviceId": self._device_id,
                    "shiesuahruefutohkun": self._token,
                    "var.target": "0",
                    "var.startDate": str(int((now - HISTORY_LOOKBACK) * 1000)),
                    "var.logItems": json.dumps({"logItems": [index]}, separators=(",", ":")),
                })
                payload = self._json(raw, "history_response_invalid")
                codes = _error_codes(payload)
                if codes:
                    _LOGGER.warning("Panasonic history item %s error codes: %s", index, codes)
                    continue
                sample = self._latest_history_sample(payload, now)
                if sample is None:
                    _LOGGER.warning("Panasonic history item %s has no valid samples", index)
                    continue
                previous = self._history.get(name)
                if previous is None or sample["timestamp"] >= previous["timestamp"]:
                    self._history[name] = sample
            except (ClientError, AquareaProtocolError, TimeoutError):
                # No upstream exception text: it can contain session information.
                _LOGGER.warning("Could not retrieve Panasonic history item %s", index)

    async def _async_fetch_status(self):
        ui = await self._request("POST", "/installer/functionUserInformation", {
            "var.functionSelectedGwUid": self._gw_uid,
        })
        self._token = self._page_token(ui, self._token)
        raw = await self._request("POST", "/installer/api/function/status", {
            "var.deviceId": self._device_id, "shiesuahruefutohkun": self._token,
        })
        return self._json(raw, "status_response_invalid")
