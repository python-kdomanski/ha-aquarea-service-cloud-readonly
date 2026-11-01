"""Offline registration/availability checks with minimal HA interfaces."""
import importlib.util
import json
import sys
import types
import unittest
from unittest.mock import patch

import test_client as protocol


def module(name, **attributes):
    result = types.ModuleType(name)
    result.__dict__.update(attributes)
    sys.modules[name] = result
    return result


class CoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator
    @property
    def available(self):
        return self.coordinator.last_update_success


class SensorEntity:
    pass


module('homeassistant')
module('homeassistant.components')
module('homeassistant.helpers')
module('homeassistant.components.sensor', SensorEntity=SensorEntity,
       SensorDeviceClass=types.SimpleNamespace(TEMPERATURE='temperature', CURRENT='current', POWER='power'),
       SensorStateClass=types.SimpleNamespace(MEASUREMENT='measurement'))
module('homeassistant.config_entries', ConfigEntry=object)
module('homeassistant.core', HomeAssistant=object)
module('homeassistant.helpers.device_registry', DeviceInfo=dict)
module('homeassistant.helpers.entity_platform', AddEntitiesCallback=object)
module('homeassistant.helpers.update_coordinator', CoordinatorEntity=CoordinatorEntity)
spec = importlib.util.spec_from_file_location('checked_aquarea.sensor', protocol.SOURCE / 'sensor.py')
sensor_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sensor_module
spec.loader.exec_module(sensor_module)
const = sys.modules['checked_aquarea.const']
names_module = sys.modules['checked_aquarea.names']


class EntityChecks(unittest.TestCase):
    def test_language_names_preserve_version_0_2_0_identities(self):
        baseline = json.loads((protocol.ROOT/'tests/fixtures/sensor_identity_v0_2_0.json').read_text(encoding='utf-8'))
        self.assertEqual(set(const.SENSORS), set(baseline))
        coordinator = types.SimpleNamespace(data={}, last_update_success=True)
        for key, definition in const.SENSORS.items():
            self.assertEqual(list(definition[1:]), [baseline[key]['unit'], baseline[key]['kind']])
            for language in (None, 'pl', 'en', 'auto'):
                names = names_module.sensor_names(language, 'pl')
                entity = sensor_module.AquareaSensor(coordinator, {'name': 'Renamed device'}, 'sample-device', key, definition, names.get(key))
                self.assertEqual(entity._attr_unique_id, 'sample-device_' + key)
        self.assertEqual(const.SENSORS['CompressorFrequency'][0], 'Compressor frequency')
        self.assertEqual(names_module.SENSOR_NAMES_PL['CompressorFrequency'], 'Częstotliwość sprężarki')
        self.assertEqual(names_module.SENSOR_NAMES_PL['PumpSpeed'], 'Prędkość pompy obiegowej')
        self.assertEqual(names_module.SENSOR_NAMES_PL['WaterInleet'], 'Temperatura wody na wejściu')

    def test_complete_language_catalogs_and_automatic_fallback(self):
        self.assertEqual(set(names_module.SENSOR_NAMES_EN), set(const.SENSORS))
        self.assertEqual(set(names_module.SENSOR_NAMES_PL), set(const.SENSORS))
        self.assertEqual(names_module.sensor_names(None, 'pl'), {})
        self.assertEqual(names_module.sensor_names('auto', 'pl-PL'), names_module.SENSOR_NAMES_PL)
        self.assertEqual(names_module.sensor_names('auto', 'pl_PL'), names_module.SENSOR_NAMES_PL)
        self.assertEqual(names_module.sensor_names('auto', 'de'), names_module.SENSOR_NAMES_EN)
        self.assertEqual(names_module.sensor_names('en', 'pl'), names_module.SENSOR_NAMES_EN)
        self.assertEqual(names_module.sensor_names('pl', 'en'), names_module.SENSOR_NAMES_PL)

    def test_registration_of_33_entities_with_dict_device_info(self):
        coordinator = types.SimpleNamespace(data={}, last_update_success=True)
        entry = types.SimpleNamespace(entry_id='entry', title='Sample pump', data={'device_id': 'sample-device'}, options={})
        hass = types.SimpleNamespace(data={const.DOMAIN: {'entry': (coordinator, None)}}, config=types.SimpleNamespace(language='pl'))
        entities = []
        coroutine = sensor_module.async_setup_entry(hass, entry, entities.extend)
        try:
            coroutine.send(None)
        except StopIteration:
            pass
        finally:
            coroutine.close()
        self.assertEqual(len(entities), 33)
        self.assertEqual(len({e._attr_unique_id for e in entities}), 33)
        selected = {e._key: e for e in entities}
        self.assertEqual(selected['OutdoorCurrent']._attr_name, 'Prąd zewnętrzny')
        self.assertEqual(selected['OutdoorCurrent']._attr_native_unit_of_measurement, 'A')
        self.assertEqual(selected['OutdoorCurrent']._attr_device_class, 'current')
        self.assertEqual(selected['HeatingInputPower']._attr_device_class, 'power')
        self.assertEqual(selected['HeatingInputPower']._attr_native_unit_of_measurement, 'kW')
        self.assertEqual(selected['DhwInputPower']._attr_name, 'Pobór mocy w trybie CWU')
        self.assertEqual(selected['CompressorFrequency']._attr_name, 'Compressor frequency')

    def test_registration_uses_selected_language_for_all_sensors(self):
        coordinator = types.SimpleNamespace(data={}, last_update_success=True)
        entry = types.SimpleNamespace(entry_id='entry', title='Sample pump', data={'device_id': 'sample-device'}, options={'name_language':'en'})
        hass = types.SimpleNamespace(data={const.DOMAIN: {'entry': (coordinator, None)}}, config=types.SimpleNamespace(language='pl'))
        entities = []
        coroutine = sensor_module.async_setup_entry(hass, entry, entities.extend)
        try:
            coroutine.send(None)
        except StopIteration:
            pass
        finally:
            coroutine.close()
        for entity in entities:
            self.assertEqual(entity._attr_name, names_module.SENSOR_NAMES_EN[entity._key])

    def test_fresh_zero_stale_and_missing_samples(self):
        now = 1800000000
        coordinator = types.SimpleNamespace(data={
            'DhwInputPower': 0.0,
            '_history': {'DhwInputPower': {'value': 0.0, 'timestamp': now-300}}
        }, last_update_success=True)
        entity = sensor_module.AquareaSensor(coordinator, {'identifiers': {(const.DOMAIN, 'sample-device')}},
                                            'sample-device', 'DhwInputPower', const.SENSORS['DhwInputPower'])
        with patch.object(sensor_module.time, 'time', return_value=now):
            self.assertTrue(entity.available)
            self.assertEqual(entity.native_value, 0.0)
            self.assertEqual(entity.extra_state_attributes['parametr_historii'], 78)
            self.assertIn('+00:00', entity.extra_state_attributes['czas_pomiaru'])
        with patch.object(sensor_module.time, 'time', return_value=now+901):
            self.assertFalse(entity.available)
        coordinator.data['_history'] = {}
        self.assertFalse(entity.available)


if __name__ == '__main__':
    unittest.main()
