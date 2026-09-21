"""Package/schema conformance, not a model-host smoke test."""
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'skills/reader-state'
sys.path.insert(0,str(SKILL/'scripts'))
from reader_state import ReaderSkillStore
try:
    import jsonschema
    from referencing import Registry, Resource
except ImportError:
    jsonschema=None


class PackageTests(unittest.TestCase):
    def test_86_inherited_source_hashes_match(self):
        p=json.loads((ROOT/'PROVENANCE.json').read_text())
        self.assertEqual(len(p['unchanged_sources']),7)
        for record in p['unchanged_sources']:
            actual=(ROOT/record['packaged_path']).read_bytes()
            self.assertEqual(hashlib.sha256(actual).hexdigest(),record['sha256'])

    def test_87_skill_is_compact_with_resolvable_local_links(self):
        text=(SKILL/'SKILL.md').read_text()
        self.assertLess(len(text.split()),800)
        self.assertTrue(text.startswith('---\nname: reader-state\n'))
        for path in re.findall(r'\]\(([^)]+)\)',text):
            self.assertTrue((SKILL/path).is_file(),path)


@unittest.skipIf(jsonschema is None,'optional development dependency: jsonschema')
class BridgeSchemaTests(unittest.TestCase):
    def setUp(self):
        self.schemas={p.name:json.loads(p.read_text()) for p in (SKILL/'schemas').glob('*.json')}
        self.base='https://reader-state.invalid/schemas/'
        self.registry=Registry().with_resources((self.base+k,Resource.from_contents(v)) for k,v in self.schemas.items())

    def validator(self,name):
        return jsonschema.Draft202012Validator({'$ref':self.base+name},registry=self.registry)

    def test_88_bridge_schemas_well_formed(self):
        for name in ['preparation.schema.json','preparation-binding.schema.json','bridge-request.schema.json']:
            jsonschema.Draft202012Validator.check_schema(self.schemas[name])

    def test_89_preparation_and_binding_schema(self):
        with tempfile.TemporaryDirectory() as t:
            store=ReaderSkillStore(t)
            p=store.prepare(str(ROOT/'examples/document.md'),'fixture')
            prep=store.inspect_prepared(p['preparation_id'])
            self.validator('preparation.schema.json').validate(prep)
            reader=json.loads((ROOT/'examples/reader.json').read_text())
            config=json.loads((ROOT/'examples/config.json').read_text())
            run=store.create_prepared(p['preparation_id'],reader,config,reviewed=True)['run_id']
            self.validator('preparation-binding.schema.json').validate(store.preparation_for_run(run))

    def test_90_bridge_request_shapes(self):
        v=self.validator('bridge-request.schema.json')
        for req in [{'op':'prepare','source':'a.md','document_id':'a'},
                    {'op':'state_at','run_id':'run-x','position':'L2.1'},
                    {'op':'query_at','run_id':'run-x','position':'L2','session_id':'session-x'}]:
            v.validate(req)
        with self.assertRaises(jsonschema.ValidationError):
            v.validate({'op':'prepare','source':'a.md','document_id':'a','invented':True})

if __name__=='__main__':unittest.main()
