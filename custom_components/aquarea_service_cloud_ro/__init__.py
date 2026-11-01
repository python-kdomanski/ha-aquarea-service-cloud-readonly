"""Read-only Aquarea Service Cloud integration."""
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
from aiohttp import CookieJar
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_DEVICE_ID, CONF_PASSWORD, DEFAULT_SCAN_INTERVAL, DOMAIN, PLATFORMS
from .coordinator import AquareaClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = AquareaClient(
        async_create_clientsession(hass, auto_cleanup=False, cookie_jar=CookieJar()),
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_DEVICE_ID],
        entry.data["gw_uid"],
    )

    async def async_update_data():
        try:
            return await client.async_get_status()
        except Exception:
            # Never include exception text: upstream errors can contain account or response data.
            raise UpdateFailed("Could not retrieve Aquarea status from Panasonic Service Cloud")

    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, name="Aquarea Service Cloud", update_method=async_update_data,
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
    )
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        client.async_close()
        raise
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = (coordinator, client)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        _, client = hass.data[DOMAIN].pop(entry.entry_id)
        client.async_close()
    return unloaded
