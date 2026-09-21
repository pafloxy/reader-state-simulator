#!/usr/bin/env python3
"""Build an AUTHORED deterministic fixture, not an empirical LLM simulation."""
from __future__ import annotations
import argparse
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/reader-state/scripts"))
from reader_store import TraceStore

PARAGRAPHS = [
    "We want to find every vertex reachable from a chosen start vertex by following directed edges.",
    "Keep a collection called pending of vertices waiting to be explored. Initially it contains the start vertex.",
    "We also keep a set called seen, initially containing the start vertex.",
    "When we explore a vertex, inspect each of its outgoing neighbors and consider whether to schedule that neighbor.",
    "Schedule a neighbor only if it is absent from seen, and add it to seen immediately when scheduling it. Thus no vertex is scheduled twice, even when the graph has a cycle.",
]


def inputs():
    source = "\n\n".join(PARAGRAPHS)
    units, offset = [], 0
    for i, paragraph in enumerate(PARAGRAPHS, 1):
        units.append({"unit_id": "u%04d" % i, "position": "L%d" % i,
                      "text": paragraph, "start": offset, "end": offset + len(paragraph), "kind": "prose"})
        offset += len(paragraph) + 2
    document = {"document_id": "reachability", "revision": "demo-v1", "granularity": "paragraph", "source_text": source, "units": units}
    reader = {"reader_id": "cs-undergraduate", "persona": "A CS undergraduate comfortable with sets and directed graphs, but not assumed familiar with graph traversal algorithms. The name seen may suggest a purpose, but a suggestion is not an explained rule.", "strictness": 1,
              "background": [{"source_id": "b1", "kind": "assumption", "title": "Declared preparation", "text": "The reader understands directed edges, paths, sets, and membership tests. Prior knowledge of graph traversal algorithms is not assumed.", "limitations": "An explicit modeling assumption, not a measured individual profile."}],
              "initial_knowledge": {"K0.1": {"text": "A set supports membership tests; a directed path follows the directions of its edges.", "meaning": "understood", "justification": "background", "evidence": [{"kind": "background", "ref": "b1"}]}}}
    config = {"model": "authored-fixture-no-model", "prompt_version": "reader-state-0.1", "isolation": "fixture", "context_policy": "full-prefix-v1", "max_units": 50, "notes": "Synthetic expected behavior; not a live-model or human validation result."}
    return document, reader, config


def refs(step):
    return [{"kind": "document", "ref": "u%04d" % step}]


def put(register, item_id, text, step, **extra):
    return {"register": register, "item_id": item_id, "action": "put", "reason": "Update supported by this visible unit.", "evidence": refs(step), "value": dict(text=text, evidence=refs(step), **extra)}


def delta(step):
    changes = {
        1: [put("understanding", "K1", "The goal is to find vertices reachable from the start.", 1, meaning="understood", justification="explicit-definition")],
        2: [put("understanding", "K2", "pending stores vertices waiting to be explored; it starts with the start vertex.", 2, meaning="understood", justification="explicit-definition")],
        3: [put("understanding", "K3", "A set named seen is initialized with the start vertex. Its update and use rules have not yet been stated.", 3, meaning="partial", justification="explicit-definition"),
            put("vocabulary", "V1", "seen is named and initialized; its operational role is not yet explained.", 3, term="seen", status="named"),
            put("expectations", "E1", "Explain when seen is updated and how it affects scheduling.", 3)],
        4: [put("understanding", "K4", "Exploration considers outgoing neighbors for scheduling; the selection condition is still unspecified.", 4, meaning="partial", justification="explicit-definition")],
        5: [put("understanding", "K3", "seen records vertices already scheduled. Membership is tested before scheduling and insertion happens immediately, so a vertex is not scheduled twice.", 5, meaning="understood", justification="supported-argument"),
            put("vocabulary", "V1", "seen is the membership guard for scheduling, updated immediately on scheduling.", 5, term="seen", status="applied"),
            {"register": "expectations", "item_id": "E1", "action": "remove", "reason": "The scheduling rule has now been explained.", "evidence": refs(5)}],
    }
    events = []
    if step == 3:
        events = [{"action": "open", "issue_id": "Q1.L3", "introduced_at": "L3", "text": "What is seen used for, and when is it updated?", "category": "missing-explanation", "reason": "Only its name and initial contents are given.", "evidence": refs(3)}]
    if step == 5:
        events = [{"action": "resolve", "issue_id": "Q1.L3", "introduced_at": "L3", "reason": "The membership guard and immediate insertion rule answer the earlier question.", "evidence": refs(5)}]
    return {"updates": copy.deepcopy(changes.get(step, [])), "issue_events": events}


def proposal(store, run_id, step):
    ticket = store.context(run_id)
    assert ticket["step"] == step
    return dict(step=ticket["step"], expected_parent_hash=ticket["expected_parent_hash"], context_hash=ticket["context_hash"], delta=delta(step))


def run_demo(root):
    store = TraceStore(root)
    document, reader, config = inputs()
    run_id = store.create(document, reader, config)["run_id"]
    for step in range(1, 6):
        store.commit(run_id, proposal(store, run_id, step))
    before = store.get(run_id, 3)
    base = store.open_session(run_id, 3, "base")
    store.append_exchange(run_id, base["session_id"], base["head_hash"], {
        "request_id": "query-1", "actor": "human", "question": "After L3, what explanation does this reader expect?",
        "answer": "The stored expectation E1 asks when seen is updated and how it affects scheduling. Q1.L3 is still open at this position.", "answer_kind": "recorded",
        "claims": [{"text": "The scheduling role of seen remains an open question at L3.", "basis": "recorded", "evidence": [{"kind": "state", "ref": "3"}]}], "added_sources": []})
    dialogue = store.open_session(run_id, 3, "dialogue")
    store.append_exchange(run_id, dialogue["session_id"], dialogue["head_hash"], {
        "request_id": "clarify-1", "actor": "human", "question": "Clarification: seen is checked before scheduling and updated immediately when scheduling.",
        "answer": "That clarification explains the scheduling rule in this conversation; the original L3 snapshot still records the gap.", "answer_kind": "clarification",
        "claims": [{"text": "This conversation supplies the scheduling rule.", "basis": "clarification", "evidence": [{"kind": "inquiry", "ref": "t1.question"}]}], "added_sources": []})
    after = TraceStore(root).get(run_id, 3)
    assert before == after, "Inquiry changed the historical base state"
    return {"fixture": "authored; no live model invoked", "run_id": run_id, "base_session_id": base["session_id"], "dialogue_session_id": dialogue["session_id"], "at_L3": after, "comparison_L3_L5": store.compare(run_id, 3, 5), "verification": store.verify(run_id)}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default=str(ROOT / ".reader-state-demo"))
    args = p.parse_args()
    print(json.dumps(run_demo(args.root), indent=2, ensure_ascii=False))
