"""Optional development checks. Runtime helper has no jsonschema dependency."""
import copy
import json
from pathlib import Path
import unittest

try:
    import jsonschema
except ImportError:
    jsonschema = None

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'skills/reader-state/schemas/artifact.schema.json').read_text())

@unittest.skipIf(jsonschema is None, 'optional development dependency: jsonschema')
class SchemaTests(unittest.TestCase):
    def validator(self, name=None):
        s = copy.deepcopy(SCHEMA)
        if name:
            s.pop('oneOf')
            s['$ref'] = '#/$defs/' + name
        return jsonschema.Draft202012Validator(s)

    def test_45_schema_is_valid(self):
        jsonschema.Draft202012Validator.check_schema(SCHEMA)

    def test_46_example_inputs_validate(self):
        for name in ('document','reader','config'):
            self.validator(name).validate(json.loads((ROOT/'examples'/(name+'.json')).read_text()))

    def test_47_all_persisted_example_records_validate(self):
        paths = list((ROOT/'examples/sample-artifacts').rglob('*.json'))
        self.assertGreaterEqual(len(paths), 10)
        for p in paths:
            with self.subTest(path=str(p.relative_to(ROOT))):
                self.validator().validate(json.loads(p.read_text()))

    def test_48_unknown_fields_rejected(self):
        d = json.loads((ROOT/'examples/document.json').read_text()); d['invented'] = 1
        with self.assertRaises(jsonschema.ValidationError):
            self.validator('document').validate(d)

    def test_49_protocol_requests_validate(self):
        for op, kwargs in [('get', {'step':3}), ('query_context',{'step':3}),('verify',{}),('compare',{'first':3,'second':5})]:
            self.validator('request').validate(dict(op=op,run_id='run-example',**kwargs))

if __name__ == '__main__':
    unittest.main()
