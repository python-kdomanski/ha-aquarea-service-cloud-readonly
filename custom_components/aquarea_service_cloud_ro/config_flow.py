"""Configuration and display-language options; credentials are never logged."""
import voluptuous as vol
from aiohttp import CookieJar
from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import SelectSelector, TextSelector

from .const import CONF_DEVICE_ID, CONF_NAME_LANGUAGE, CONF_PASSWORD, DOMAIN, NAME_LANGUAGES
from .coordinator import AquareaAuthError, AquareaClient, AquareaProtocolError


def _language_selector():
    return SelectSelector({
        "options": list(NAME_LANGUAGES),
        "translation_key": "name_language",
        "mode": "dropdown",
    })


class AquareaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AquareaOptionsFlow()

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            devices = None
            client = AquareaClient(
                async_create_clientsession(self.hass, auto_cleanup=False, cookie_jar=CookieJar()),
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            try:
                devices = await client.async_login_and_list_devices()
                if not devices:
                    errors["base"] = "no_devices"
            except AquareaAuthError:
                errors["base"] = "invalid_auth"
            except AquareaProtocolError as err:
                errors["base"] = err.stage
            except Exception:
                errors["base"] = "cannot_connect"
            finally:
                client.async_close()
            if devices:
                # AbortFlow must propagate to HA, not become a connection error.
                await self.async_set_unique_id(user_input[CONF_USERNAME].casefold())
                self._abort_if_unique_id_configured()
                self._devices = devices
                self._credentials = dict(user_input)
                return await self.async_step_device()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): TextSelector({"type": "password"}),
            }),
            errors=errors,
        )

    async def async_step_device(self, user_input=None):
        errors = {}
        if user_input is not None:
            language = user_input.get(CONF_NAME_LANGUAGE, "auto")
            if language not in NAME_LANGUAGES:
                errors["base"] = "invalid_language"
            else:
                device = self._devices[user_input[CONF_DEVICE_ID]]
                return self.async_create_entry(
                    title=device["name"],
                    data={**self._credentials, CONF_DEVICE_ID: user_input[CONF_DEVICE_ID], "gw_uid": device["gw_uid"]},
                    options={CONF_NAME_LANGUAGE: language},
                )
        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_ID): vol.In({d["id"]: d["name"] for d in self._devices.values()}),
                vol.Required(CONF_NAME_LANGUAGE, default="auto"): _language_selector(),
            }),
            errors=errors,
        )


class AquareaOptionsFlow(config_entries.OptionsFlowWithReload):
    """Changing the display language reloads the existing entry, preserving IDs."""

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            language = user_input.get(CONF_NAME_LANGUAGE)
            if language not in NAME_LANGUAGES:
                errors["base"] = "invalid_language"
            else:
                return self.async_create_entry(
                    title="", data={**self.config_entry.options, CONF_NAME_LANGUAGE: language},
                )
        current = self.config_entry.options.get(CONF_NAME_LANGUAGE)
        # Legacy entries have no language option. Require an explicit choice
        # rather than selecting a language merely by opening this form.
        marker = (
            vol.Required(CONF_NAME_LANGUAGE, default=current)
            if current in NAME_LANGUAGES else vol.Required(CONF_NAME_LANGUAGE)
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({marker: _language_selector()}),
            errors=errors,
        )
