"""Sensor entities only; this platform cannot control the heat pump."""
from datetime import datetime, timezone
import time

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, CONF_NAME_LANGUAGE, DOMAIN, HISTORY_FIELDS, HISTORY_MAX_AGE, SENSORS
from .names import sensor_names


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator, _ = hass.data[DOMAIN][entry.entry_id]
    device_id = entry.data[CONF_DEVICE_ID]
    names = sensor_names(entry.options.get(CONF_NAME_LANGUAGE), hass.config.language)
    device = DeviceInfo(
        identifiers={(DOMAIN, device_id)},
        name=entry.title,
        manufacturer="Panasonic",
        model="Aquarea (Service Cloud)",
    )
    async_add_entities(
        AquareaSensor(coordinator, device, device_id, key, definition, names.get(key))
        for key, definition in SENSORS.items()
    )


class AquareaSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, device, device_id, key, definition, display_name=None):
        super().__init__(coordinator)
        name, unit, kind = definition
        self._key = key
        self._attr_name = display_name if display_name is not None else name
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_device_info = device
        self._attr_native_unit_of_measurement = unit
        if kind == "temperature":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif kind == "measurement":
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif kind in ("current", "power"):
            self._attr_device_class = SensorDeviceClass.CURRENT if kind == "current" else SensorDeviceClass.POWER
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_suggested_display_precision = 1 if kind == "current" else 3

    @property
    def available(self):
        if not super().available:
            return False
        if self._key in HISTORY_FIELDS:
            sample = self.coordinator.data.get("_history", {}).get(self._key)
            return bool(sample and sample.get("value") is not None
                        and -60 <= time.time() - sample["timestamp"] <= HISTORY_MAX_AGE)
        return True

    @property
    def extra_state_attributes(self):
        if self._key not in HISTORY_FIELDS:
            return None
        sample = self.coordinator.data.get("_history", {}).get(self._key)
        return {
            "czas_pomiaru": datetime.fromtimestamp(sample["timestamp"], timezone.utc).isoformat() if sample else None,
            "zrodlo": "Historia Aquarea Service Cloud",
            "parametr_historii": HISTORY_FIELDS[self._key],
        }

    @property
    def native_value(self):
        value = self.coordinator.data.get(self._key)
        if value is None:
            return None
        if self._attr_native_unit_of_measurement is not None or getattr(self, "_attr_state_class", None):
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        return value
