#!/usr/bin/env python3
"""Use the original normalizer plus authored RC1 deltas. No model is invoked."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/reader-state/scripts'))
from reader_state import ReaderSkillStore
from reader_store import StoreError
from make_demo import inputs, proposal


def rebind(value, mapping):
    if isinstance(value, dict):
        if value.get('kind') == 'document' and value.get('ref') in mapping:
            return dict(value, ref=mapping[value['ref']])
        return {k: rebind(v, mapping) for k, v in value.items()}
    if isinstance(value, list):
        return [rebind(v, mapping) for v in value]
    return value


def run(root):
    store = ReaderSkillStore(root)
    source = ROOT / 'examples/document.md'
    prepared = store.prepare(str(source), 'reachability', 'block')
    old_doc, reader, config = inputs()
    made = store.create_prepared(prepared['preparation_id'], reader, config, reviewed=True)
    run_id = made['run_id']
    doc = store.manifest(run_id)['document']
    mapping = {a['unit_id']: b['unit_id'] for a, b in zip(old_doc['units'],doc['units'])}
    while True:
        try:
            ticket = store.context(run_id)
        except StoreError as exc:
            if exc.code == 'COMPLETE':
                break
            raise
        p = proposal(store,run_id,ticket['step'])
        p['delta'] = rebind(p['delta'],mapping)
        store.commit(run_id,p)
    before = store.state_at(run_id,'L3')
    s = store.open_session(run_id,3,'dialogue')
    store.append_exchange(run_id,s['session_id'],s['head_hash'],{
        'request_id':'demo-clarification','actor':'human',
        'question':'Clarification: seen prevents duplicate scheduling and is updated on scheduling.',
        'answer':'That explanation is now available in this dialogue, not in the original L3 snapshot.',
        'answer_kind':'clarification','claims':[{
            'text':'The author supplied a later clarification.','basis':'clarification',
            'evidence':[{'kind':'inquiry','ref':'t1.question'}]}],'added_sources':[]})
    unchanged = before == store.state_at(run_id,'L3')
    assert unchanged
    return {'mode':'authored-fixture','model_calls':0,'preparation_id':prepared['preparation_id'],
            'run_id':run_id,'reused_run':made['reused'],'L3':before,
            'L5':store.state_at(run_id,'L5'),'base_unchanged_after_dialogue':unchanged,
            'session_id':s['session_id'],'verification':store.verify(run_id)}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True)
    args = p.parse_args()
    print(json.dumps(run(args.root),ensure_ascii=False,indent=2))
