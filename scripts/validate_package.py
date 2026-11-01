"""Validate the publishable layout without HA, network access or credentials."""
import ast
import importlib.util
import json
import re
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = 'aquarea_service_cloud_ro'
COMPONENT = ROOT / 'custom_components' / DOMAIN
URL = 'https://github.com/python-kdomanski/ha-aquarea-service-cloud-readonly'


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def keys(value, prefix=''):
    found = set()
    for key, item in value.items():
        name = prefix + key
        if isinstance(item, dict):
            found.update(keys(item, name + '.'))
        else:
            found.add(name)
    return found


def main():
    folders = [p.name for p in (ROOT/'custom_components').iterdir()
               if p.is_dir() and p.name != '__pycache__']
    assert folders == [DOMAIN], folders
    manifest = load_json(COMPONENT/'manifest.json')
    assert manifest['domain'] == DOMAIN
    assert re.fullmatch(r'\d+\.\d+\.\d+', manifest['version'])
    assert '## ' + manifest['version'] + ' ' in (ROOT/'CHANGELOG.md').read_text(encoding='utf-8')
    assert manifest['codeowners'] == ['@python-kdomanski']
    assert manifest['documentation'] == URL
    assert manifest['issue_tracker'] == URL + '/issues'
    assert load_json(ROOT/'hacs.json')['homeassistant'] == '2026.10.0'
    base_keys = keys(load_json(COMPONENT/'strings.json'))
    for language in ('en', 'pl'):
        assert keys(load_json(COMPONENT/'translations'/(language+'.json'))) == base_keys
    for path in COMPONENT.glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'))
    tree = ast.parse((COMPONENT/'coordinator.py').read_text(encoding='utf-8'))
    paths = {node.args[1].value for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
             and node.func.attr == '_request' and len(node.args) > 1
             and isinstance(node.args[1], ast.Constant)}
    assert paths == {'', 'installer/api/auth/login', 'installer/home',
                     '/installer/api/endusers', '/installer/functionUserInformation',
                     '/installer/api/function/status', '/installer/api/data/log'}, paths
    spec = importlib.util.spec_from_file_location('checked_const', COMPONENT/'const.py')
    const = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(const)
    assert len(const.SENSORS) == 33
    for name, size in (('icon.png', 256), ('icon@2x.png', 512)):
        image = (COMPONENT/'brand'/name).read_bytes()
        assert image[:8] == b'\x89PNG\r\n\x1a\n'
        assert struct.unpack('!II', image[16:24]) == (size, size)
    for path in ROOT.rglob('*'):
        if '.git' in path.parts or '__pycache__' in path.parts or not path.is_file():
            continue
        assert path.name not in {'secrets.yaml', 'configuration.yaml', '.env', 'config'}, path.name
        assert path.suffix.lower() not in {'.exe', '.db', '.har', '.log'}, path.name
    for name in ('README.md', 'LICENSE', 'AUTHORS.md', 'ATTRIBUTION.md', 'CHANGELOG.md'):
        assert (ROOT/name).is_file(), name
    print('Package layout, metadata, translations, 33 sensors, read-only routes and icons: OK')


if __name__ == '__main__':
    main()
