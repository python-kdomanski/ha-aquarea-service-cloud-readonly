"""Configuration flow. Credentials are never written to logs."""
import voluptuous as vol
from homeassistant import config_entries
from aiohttp import CookieJar
from homeassistant.const import CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import TextSelector

from .const import CONF_DEVICE_ID, CONF_PASSWORD, DOMAIN
from .coordinator import AquareaAuthError, AquareaClient, AquareaProtocolError


class AquareaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            client = AquareaClient(
                async_create_clientsession(self.hass, auto_cleanup=False, cookie_jar=CookieJar()),
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            try:
                devices = await client.async_login_and_list_devices()
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    await self.async_set_unique_id(user_input[CONF_USERNAME].casefold())
                    self._abort_if_unique_id_configured()
                    self._devices = devices
                    self._credentials = user_input
                    return await self.async_step_device()
            except AquareaAuthError:
                errors["base"] = "invalid_auth"
            except AquareaProtocolError as err:
                errors["base"] = err.stage
            except Exception:
                errors["base"] = "cannot_connect"
            finally:
                client.async_close()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): TextSelector({"type": "password"}),
            }),
            errors=errors,
        )

    async def async_step_device(self, user_input=None):
        if user_input is not None:
            device = self._devices[user_input[CONF_DEVICE_ID]]
            return self.async_create_entry(
                title=device["name"],
            data={**self._credentials, CONF_DEVICE_ID: user_input[CONF_DEVICE_ID], "gw_uid": device["gw_uid"]},
            )
        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_ID): vol.In({d["id"]: d["name"] for d in self._devices.values()})
            }),
        )
