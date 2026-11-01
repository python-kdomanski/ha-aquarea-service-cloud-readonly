"""Offline registration/availability checks with minimal HA interfaces."""
import importlib.util
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


class EntityChecks(unittest.TestCase):
    def test_registration_of_33_entities_with_dict_device_info(self):
        coordinator = types.SimpleNamespace(data={}, last_update_success=True)
        entry = types.SimpleNamespace(entry_id='entry', title='Sample pump', data={'device_id': 'sample-device'})
        hass = types.SimpleNamespace(data={const.DOMAIN: {'entry': (coordinator, None)}})
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
