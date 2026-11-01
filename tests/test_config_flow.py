"""Offline checks of language selection with small HA/selector interfaces."""
import importlib.util
import sys
import types
import unittest
from unittest.mock import patch

import test_entities as entities


class Required:
    def __init__(self, name, **kwargs):
        self.schema = name
        self.settings = kwargs


class Schema:
    def __init__(self, value):
        self.schema = value


class Selector:
    def __init__(self, config):
        self.config = config


class AbortFlow(Exception):
    pass


class BaseFlow:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
    def async_show_form(self, **kwargs):
        return {'type': 'form', **kwargs}
    def async_create_entry(self, **kwargs):
        return {'type': 'create_entry', **kwargs}
    async def async_set_unique_id(self, value):
        self._unique_id = value
    def _abort_if_unique_id_configured(self):
        if getattr(self, '_configured', False):
            raise AbortFlow('already_configured')


class OptionsFlowWithReload(BaseFlow):
    pass


entities.module('voluptuous', Required=Required, Schema=Schema, In=lambda value: value)
entries = sys.modules['homeassistant.config_entries']
entries.ConfigFlow = BaseFlow
entries.OptionsFlowWithReload = OptionsFlowWithReload
sys.modules['homeassistant'].config_entries = entries
entities.module('homeassistant.const', CONF_USERNAME='username')
sys.modules['homeassistant.core'].callback = lambda function: function
entities.module('homeassistant.helpers.aiohttp_client', async_create_clientsession=lambda *args, **kwargs: object())
entities.module('homeassistant.helpers.selector', SelectSelector=Selector, TextSelector=Selector)
sys.modules['aiohttp'].CookieJar = lambda: object()
spec = importlib.util.spec_from_file_location('checked_aquarea.config_flow', entities.protocol.SOURCE/'config_flow.py')
flow_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = flow_module
spec.loader.exec_module(flow_module)


def drive(coroutine):
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value
    finally:
        coroutine.close()
    raise AssertionError('Fake flow unexpectedly needed an event loop')


class ConfigFlowChecks(unittest.TestCase):
    def new_flow(self):
        flow = flow_module.AquareaConfigFlow()
        flow._devices = {'device': {'id':'device', 'name':'Sample pump', 'gw_uid':'gateway'}}
        flow._credentials = {'username':'sample', 'password':'sample-password'}
        return flow

    def test_new_installation_defaults_to_auto(self):
        result = drive(self.new_flow().async_step_device())
        marker = next(key for key in result['data_schema'].schema if key.schema == 'name_language')
        self.assertEqual(marker.settings, {'default': 'auto'})
        self.assertEqual(result['data_schema'].schema[marker].config['options'], ['auto','pl','en'])

    def test_new_installation_saves_language_separately_from_credentials(self):
        result = drive(self.new_flow().async_step_device({'device_id':'device', 'name_language':'pl'}))
        self.assertEqual(result['options'], {'name_language':'pl'})
        self.assertNotIn('name_language', result['data'])
        self.assertEqual(result['data']['device_id'], 'device')

    def test_legacy_options_require_explicit_selection(self):
        flow = flow_module.AquareaConfigFlow.async_get_options_flow(None)
        self.assertIsInstance(flow, OptionsFlowWithReload)
        flow.config_entry = types.SimpleNamespace(options={})
        result = drive(flow.async_step_init())
        marker = next(iter(result['data_schema'].schema))
        self.assertEqual(marker.settings, {})
        self.assertEqual(flow.config_entry.options, {})

    def test_options_do_not_authenticate_and_preserve_other_options(self):
        flow = flow_module.AquareaOptionsFlow()
        flow.config_entry = types.SimpleNamespace(options={'future_option':True})
        with patch.object(flow_module, 'AquareaClient', side_effect=AssertionError('Options must not authenticate')):
            result = drive(flow.async_step_init({'name_language':'en'}))
        self.assertEqual(result['data'], {'future_option':True, 'name_language':'en'})
        self.assertNotIn('password', result['data'])

    def test_options_reject_invalid_language(self):
        flow = flow_module.AquareaOptionsFlow()
        flow.config_entry = types.SimpleNamespace(options={})
        result = drive(flow.async_step_init({'name_language':'invalid'}))
        self.assertEqual(result['type'], 'form')
        self.assertEqual(result['errors'], {'base':'invalid_language'})

    def test_duplicate_account_abort_is_not_hidden_as_connection_error(self):
        flow = self.new_flow()
        flow.hass = object()
        flow._configured = True
        class Client:
            closed = False
            async def async_login_and_list_devices(self):
                return flow._devices
            def async_close(self):
                self.closed = True
        client = Client()
        with patch.object(flow_module, 'AquareaClient', return_value=client):
            with self.assertRaises(AbortFlow):
                drive(flow.async_step_user(flow._credentials))
        self.assertTrue(client.closed)


if __name__ == '__main__':
    unittest.main()
