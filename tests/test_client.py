"""Offline checks: no network, credentials, Home Assistant or aiohttp required."""
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'custom_components/aquarea_service_cloud_ro'
package = types.ModuleType('checked_aquarea')
package.__path__ = [str(SOURCE)]
sys.modules[package.__name__] = package
# Only the exception class is imported; HTTP is supplied by FakeSession below.
aiohttp = types.ModuleType('aiohttp')
aiohttp.ClientError = type('ClientError', (Exception,), {})
sys.modules['aiohttp'] = aiohttp
for name in ('const', 'coordinator'):
    spec = importlib.util.spec_from_file_location('checked_aquarea.' + name, SOURCE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
client_module = sys.modules['checked_aquarea.coordinator']
BASE = 'https://aquarea-service.panasonic.com/'


class Response:
    def __init__(self, body):
        self.body = body if isinstance(body, str) else json.dumps(body)
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass
    def raise_for_status(self):
        pass
    async def text(self):
        return self.body


class FakeSession:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []
    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return Response(self.replies.pop(0))


def replies(with_tokens=True, status=None):
    page = lambda value: "const shiesuahruefutohkun = '" + value + "';" if with_tokens else '<html>app</html>'
    return [page('root'), {'errorCode': 0, 'agreementStatus': {}}, page('home'),
            {'endusers': [{'deviceId': 'sample-device', 'gwUid': 'sample-gateway'}]},
            page('device'), status or {'statusDataInfo': {'function-status-text-031': {'value': '8'}}}]


class ClientChecks(unittest.TestCase):
    def run_client(self, session, history=False):
        client = client_module.AquareaClient(session, 'sample-user', 'sample-password', 'sample-device')
        if not history:
            client._next_history_poll = float('inf')
        return self.drive(client.async_get_status())

    def drive(self, coroutine):
        # Fake HTTP coroutines complete synchronously; no Windows event-loop
        # sockets are needed for these isolated protocol checks.
        try:
            coroutine.send(None)
        except StopIteration as completed:
            return completed.value
        finally:
            coroutine.close()
        self.fail('Fake HTTP unexpectedly required an event loop')

    def test_go_sequence_and_token_rotation(self):
        session = FakeSession(replies())
        result = self.run_client(session)
        self.assertEqual(result['OutdoorTemperature'], '8')
        self.assertEqual([(m, u) for m, u, _ in session.calls], [
            ('GET', BASE), ('POST', BASE + 'installer/api/auth/login'),
            ('GET', BASE + 'installer/home'), ('POST', BASE + '/installer/api/endusers'),
            ('POST', BASE + '/installer/functionUserInformation'), ('POST', BASE + '/installer/api/function/status')])
        for index, token in ((1, 'root'), (3, 'home'), (5, 'device')):
            body = session.calls[index][2]['data']
            self.assertIsInstance(body, str)
            self.assertEqual(parse_qs(body, keep_blank_values=True)['shiesuahruefutohkun'], [token])
            self.assertEqual(session.calls[index][2]['headers']['Content-Type'], 'application/x-www-form-urlencoded')
        self.assertEqual(parse_qs(session.calls[4][2]['data']), {'var.functionSelectedGwUid': ['sample-gateway']})

    def test_go_keeps_empty_token_fields(self):
        session = FakeSession(replies(False))
        self.run_client(session)
        for index in (1, 3, 5):
            self.assertEqual(parse_qs(session.calls[index][2]['data'], keep_blank_values=True)['shiesuahruefutohkun'], [''])

    def test_nested_status_error_reauthenticates_once(self):
        session = FakeSession(replies(status={'errorCode': 0, 'message': [{'errorCode': '3000-0011'}]}) + replies())
        self.assertEqual(self.run_client(session)['OutdoorTemperature'], '8')
        self.assertEqual(len(session.calls), 12)

    def test_missing_readings_does_not_become_silent_unknown(self):
        with self.assertRaises(aiohttp.ClientError):
            self.run_client(FakeSession(replies(status={'errorCode': 0})))

    def test_history_requests_and_cache(self):
        now = 1800000000
        timestamp = str((now - 300) * 1000)
        history = [
            {'logData': json.dumps({timestamp: ['2.4000000000000004'], str((now-600)*1000): ['9.0']})},
            {'logData': {timestamp: ['0.562']}},
            {'logData': json.dumps({timestamp: ['0.0']})},
        ]
        session = FakeSession(replies() + history)
        client = client_module.AquareaClient(session, 'user', 'password', 'sample-device')
        with patch.object(client_module.time, 'time', return_value=now), patch.object(client_module.time, 'monotonic', return_value=1000):
            result = self.drive(client.async_get_status())
        self.assertAlmostEqual(result['OutdoorCurrent'], 2.4)
        self.assertEqual(result['HeatingInputPower'], 0.562)
        self.assertEqual(result['DhwInputPower'], 0.0)
        self.assertEqual(result['_history']['DhwInputPower']['timestamp'], now-300)
        for call, item in zip(session.calls[6:], (63, 72, 78)):
            self.assertEqual(call[:2], ('POST', BASE + '/installer/api/data/log'))
            fields = parse_qs(call[2]['data'], keep_blank_values=True)
            self.assertEqual(json.loads(fields['var.logItems'][0]), {'logItems': [item]})
            self.assertEqual(fields['var.startDate'], [str((now-3600)*1000)])
            self.assertEqual(fields['var.target'], ['0'])
            self.assertEqual(fields['shiesuahruefutohkun'], ['device'])
        session.replies.extend(replies()[4:])
        with patch.object(client_module.time, 'time', return_value=now+60), patch.object(client_module.time, 'monotonic', return_value=1060):
            second = self.drive(client.async_get_status())
        self.assertEqual(len(session.calls), 11)
        self.assertEqual(result['_history'], second['_history'])

    def test_history_failure_does_not_break_status_or_other_history(self):
        now = 1800000000
        history = [{'errorCode': 0, 'message': [{'errorCode': '3000-0011'}]},
                   '<html>unexpected page</html>',
                   {'logData': json.dumps({str(now*1000): ['0.0']})}]
        with patch.object(client_module.time, 'time', return_value=now):
            result = self.run_client(FakeSession(replies() + history), history=True)
        self.assertEqual(result['OutdoorTemperature'], '8')
        self.assertIsNone(result['OutdoorCurrent'])
        self.assertIsNone(result['HeatingInputPower'])
        self.assertEqual(result['DhwInputPower'], 0.0)

    def test_history_parser_ignores_invalid_and_future_values(self):
        now = 1800000000
        data = {str(now*1000): ['NaN'], str((now+600)*1000): ['99'],
                str((now-300)*1000): ['-'], str((now-600)*1000): ['0'],
                'not-a-timestamp': ['1'], str((now-900)*1000): [True]}
        sample = client_module.AquareaClient._latest_history_sample({'logData': json.dumps(data)}, now)
        self.assertEqual(sample, {'value': 0.0, 'timestamp': now-600})
        self.assertIsNone(client_module.AquareaClient._latest_history_sample({'logData': 'bad json'}, now))

    def test_failed_refresh_keeps_original_sample_timestamp(self):
        errors = [{'errorCode': 1} for _ in range(3)]
        client = client_module.AquareaClient(FakeSession(errors), 'user', 'password', 'sample-device')
        client._history = {'OutdoorCurrent': {'value': 2.4, 'timestamp': 1799999700}}
        before = {key: dict(value) for key, value in client._history.items()}
        self.drive(client._async_update_history())
        self.assertEqual(client._history, before)


if __name__ == '__main__':
    unittest.main()
