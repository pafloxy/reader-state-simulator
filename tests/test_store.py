"""Contract tests using authored proposals; these do not validate human fidelity."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/reader-state/scripts"))
sys.path.insert(0, str(ROOT / "examples"))
from reader_store import TraceStore, StoreError, digest, read_json, stamped
from make_demo import inputs, proposal, delta, refs, put, run_demo


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = TraceStore(self.tmp.name)
        self.doc, self.reader, self.config = inputs()
        self.run = self.store.create(self.doc, self.reader, self.config)["run_id"]

    def compile(self, through=5):
        for i in range(1, through + 1):
            self.store.commit(self.run, proposal(self.store, self.run, i))

    def exchange(self, **kwargs):
        x = {"request_id": "q1", "actor": "human", "question": "What is expected?", "answer": "The saved state records the expectations available here.", "answer_kind": "recorded", "claims": [{"text": "This answer refers to the recorded state.", "basis": "recorded", "evidence": [{"kind": "state", "ref": "3"}]}], "added_sources": []}
        x.update(kwargs)
        return x

    def assertCode(self, code, function, *args, **kwargs):
        with self.assertRaises(StoreError) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def test_01_initial_state(self):
        s = self.store.get(self.run, 0)
        self.assertEqual(s["position"], "L0")
        self.assertIn("K0.1", s["state"]["understanding"])

    def test_02_fresh_instance_retrieval(self):
        self.compile(3)
        self.assertEqual(self.store.get(self.run, 3), TraceStore(self.tmp.name).get(self.run, 3))

    def test_03_carry_forward(self):
        self.compile()
        state = self.store.get(self.run, 5)["state"]
        self.assertIn("K0.1", state["understanding"])
        self.assertIn("K1", state["understanding"])
        self.assertNotIn("E1", state["expectations"])

    def test_04_prefix_context_excludes_suffix(self):
        self.compile(2)
        payload = self.store.context(self.run)["context"]
        self.assertEqual(len(payload["visible_units"]), 3)
        self.assertNotIn("source_text", payload)
        self.assertNotIn(self.doc["units"][4]["text"], json.dumps(payload))

    def test_05_future_evidence_rejected_without_commit(self):
        p = proposal(self.store, self.run, 1)
        p["delta"]["updates"][0]["evidence"] = refs(5)
        self.assertCode("VISIBILITY", self.store.commit, self.run, p)
        self.assertEqual(self.store.context(self.run)["step"], 1)
        self.assertEqual(list((self.store.path(self.run) / "trace").glob("*.json")), [])

    def test_06_future_value_evidence_rejected(self):
        p = proposal(self.store, self.run, 1)
        p["delta"]["updates"][0]["value"]["evidence"] = refs(5)
        self.assertCode("VISIBILITY", self.store.commit, self.run, p)

    def test_07_wrong_context_ticket_rejected(self):
        p = proposal(self.store, self.run, 1); p["context_hash"] = "wrong"
        self.assertCode("CONFLICT", self.store.commit, self.run, p)

    def test_08_wrong_parent_rejected(self):
        p = proposal(self.store, self.run, 1); p["expected_parent_hash"] = "wrong"
        self.assertCode("CONFLICT", self.store.commit, self.run, p)

    def test_09_idempotent_commit(self):
        p = proposal(self.store, self.run, 1)
        a = self.store.commit(self.run, p); b = self.store.commit(self.run, p)
        self.assertEqual(a["hash"], b["hash"])
        self.assertTrue(b["idempotent"])

    def test_10_conflicting_commit(self):
        p = proposal(self.store, self.run, 1)
        self.store.commit(self.run, p)
        p["delta"]["updates"][0]["reason"] = "Different proposal."
        self.assertCode("CONFLICT", self.store.commit, self.run, p)

    def test_11_out_of_order_commit(self):
        p = proposal(self.store, self.run, 1); p["step"] = 2
        self.assertCode("CONFLICT", self.store.commit, self.run, p)

    def test_12_issue_history_prefix(self):
        self.compile()
        self.assertEqual(self.store.get(self.run, 3)["issues"]["Q1.L3"]["status"], "open")
        self.assertEqual(self.store.get(self.run, 5)["issues"]["Q1.L3"]["status"], "resolved")
        self.assertEqual(self.store.get(self.run, 5)["issues"]["Q1.L3"]["introduced_at"], "L3")

    def test_13_issue_reopening(self):
        for step, action in enumerate(("open", "resolve", "reopen"), 1):
            ticket = self.store.context(self.run)
            ev = {"action": action, "issue_id": "Q1.L1", "introduced_at": "L1", "reason": "Fixture lifecycle event.", "evidence": refs(step)}
            if action == "open":
                ev.update(text="Is the goal specified?", category="ambiguity")
            p = {k: ticket[k] for k in ("step", "expected_parent_hash", "context_hash")}
            p["delta"] = {"updates": [], "issue_events": [ev]}
            self.store.commit(self.run, p)
        self.assertEqual(self.store.get(self.run, 2)["issues"]["Q1.L1"]["status"], "resolved")
        self.assertEqual(self.store.get(self.run, 3)["issues"]["Q1.L1"]["status"], "open")

    def test_14_issue_origin_mismatch(self):
        self.compile(2)
        p = proposal(self.store, self.run, 3)
        p["delta"]["issue_events"][0]["introduced_at"] = "L2"
        self.assertCode("INVALID", self.store.commit, self.run, p)

    def test_15_comparison_is_read_only(self):
        self.compile()
        before = {p.name: p.read_bytes() for p in (self.store.path(self.run) / "trace").glob("*.json")}
        result = self.store.compare(self.run, 3, 5)
        after = {p.name: p.read_bytes() for p in (self.store.path(self.run) / "trace").glob("*.json")}
        self.assertEqual(before, after)
        self.assertIn("K3", result["changes"]["understanding"]["changed"])
        self.assertEqual(result["model_calls"], 0)

    def test_16_base_clarification_rejected(self):
        self.compile(3)
        s = self.store.open_session(self.run, 3, "base")
        x = self.exchange(answer_kind="clarification")
        self.assertCode("VISIBILITY", self.store.append_exchange, self.run, s["session_id"], s["head_hash"], x)

    def test_17_dialogue_does_not_mutate_base(self):
        self.compile(3)
        before = self.store.get(self.run, 3)
        s = self.store.open_session(self.run, 3, "dialogue")
        x = self.exchange(answer_kind="clarification", claims=[{"text": "The author supplied a rule.", "basis": "clarification", "evidence": [{"kind": "inquiry", "ref": "t1.question"}]}])
        self.store.append_exchange(self.run, s["session_id"], s["head_hash"], x)
        self.assertEqual(before, self.store.get(self.run, 3))

    def test_18_fresh_session_does_not_inherit(self):
        self.compile(3)
        old = self.store.open_session(self.run, 3, "dialogue")
        self.store.append_exchange(self.run, old["session_id"], old["head_hash"], self.exchange())
        new = self.store.open_session(self.run, 3, "dialogue")
        self.assertEqual(self.store.query_context(self.run, 3, new["session_id"])["inquiry_history"], [])
        self.assertEqual(len(self.store.query_context(self.run, 3, old["session_id"])["inquiry_history"]), 1)

    def test_19_base_context_ignores_log(self):
        self.compile(3)
        s = self.store.open_session(self.run, 3, "base")
        self.store.append_exchange(self.run, s["session_id"], s["head_hash"], self.exchange())
        self.assertEqual(self.store.query_context(self.run, 3, s["session_id"])["inquiry_history"], [])
        self.assertEqual(len(self.store.conversation(self.run, s["session_id"])["events"]), 1)

    def test_20_query_context_bound(self):
        self.compile()
        q = self.store.query_context(self.run, 3)
        self.assertEqual(len(q["visible_units"]), 3)
        self.assertNotIn(self.doc["units"][4]["text"], json.dumps(q))

    def test_21_inquiry_future_reference_rejected(self):
        self.compile()
        s = self.store.open_session(self.run, 3, "dialogue")
        x = self.exchange(claims=[{"text": "Later rule.", "basis": "inference", "evidence": refs(5)}])
        self.assertCode("VISIBILITY", self.store.append_exchange, self.run, s["session_id"], s["head_hash"], x)

    def test_22_conversation_source_attribution(self):
        self.compile(3)
        s = self.store.open_session(self.run, 3, "dialogue")
        x = self.exchange(answer_kind="clarification", added_sources=[{"source_id": "c1", "title": "Author clarification", "text": "Only schedule vertices not yet in seen.", "limitations": "Supplied later, not in original prefix."}], claims=[{"text": "The new source provides the guard.", "basis": "clarification", "evidence": [{"kind": "inquiry", "ref": "t1.source:c1"}]}])
        self.store.append_exchange(self.run, s["session_id"], s["head_hash"], x)
        self.assertTrue(self.store.verify(self.run)["ok"])
        self.assertEqual(len(self.store.manifest(self.run)["reader"]["background"]), 1)

    def test_23_inquiry_idempotency(self):
        self.compile(3)
        s = self.store.open_session(self.run, 3, "base")
        x = self.exchange()
        a = self.store.append_exchange(self.run, s["session_id"], s["head_hash"], x)
        b = self.store.append_exchange(self.run, s["session_id"], s["head_hash"], x)
        self.assertTrue(b["idempotent"])
        self.assertEqual(a["hash"], b["hash"])

    def test_24_stale_inquiry_head(self):
        self.compile(3)
        s = self.store.open_session(self.run, 3, "base")
        self.store.append_exchange(self.run, s["session_id"], s["head_hash"], self.exchange())
        self.assertCode("CONFLICT", self.store.append_exchange, self.run, s["session_id"], s["head_hash"], self.exchange(request_id="q2"))

    def test_25_hash_corruption(self):
        self.compile(1)
        path = self.store.path(self.run) / "trace/000001.json"
        x = read_json(path); x["snapshot"]["understanding"]["K1"]["text"] = "Tampered"
        path.write_text(json.dumps(x))
        self.assertCode("CORRUPT", self.store.get, self.run, 1)

    def test_26_rehashed_inconsistent_snapshot_rejected(self):
        self.compile(1)
        path = self.store.path(self.run) / "trace/000001.json"
        x = read_json(path); x.pop("hash")
        x["snapshot"]["understanding"]["K1"]["text"] = "Inconsistent materialized view"
        path.write_text(json.dumps(stamped(x)))
        self.assertCode("CORRUPT", self.store.get, self.run, 1)

    def test_27_interrupted_publish_no_partial_commit(self):
        p = proposal(self.store, self.run, 1)
        with patch("reader_store.os.link", side_effect=OSError("Injected pre-publication failure")):
            with self.assertRaises(OSError):
                self.store.commit(self.run, p)
        self.assertEqual(self.store.context(self.run)["step"], 1)
        self.store.commit(self.run, p)
        self.assertEqual(self.store.get(self.run, 1)["step"], 1)

    def test_28_source_span_validation(self):
        self.doc["units"][0]["text"] = "Not the source"
        self.assertCode("INVALID", self.store.create, self.doc, self.reader, self.config)

    def test_29_source_gap_validation(self):
        self.doc["units"] = self.doc["units"][1:]
        self.assertCode("INVALID", self.store.create, self.doc, self.reader, self.config)

    def test_30_same_input_distinct_runs(self):
        a = self.store.manifest(self.run)
        b = self.store.create(self.doc, self.reader, self.config)
        self.assertEqual(a["input_digest"], b["input_digest"])
        self.assertNotEqual(self.run, b["run_id"])

    def test_31_changed_profile_changes_identity(self):
        self.reader["strictness"] = 2
        b = self.store.create(self.doc, self.reader, self.config)
        self.assertNotEqual(self.store.manifest(self.run)["input_digest"], b["input_digest"])

    def test_32_budget_guard(self):
        self.config["max_units"] = 3
        self.assertCode("BUDGET", self.store.create, self.doc, self.reader, self.config)

    def test_33_identifier_path_traversal(self):
        self.assertCode("INVALID", self.store.get, "../outside", 0)

    def test_34_missing_background_ref(self):
        self.reader["initial_knowledge"]["K0.1"]["evidence"][0]["ref"] = "missing"
        self.assertCode("VISIBILITY", self.store.create, self.doc, self.reader, self.config)

    def test_35_reject_unknown_register_and_missing_justification(self):
        p = proposal(self.store, self.run, 1)
        p["delta"]["updates"][0]["register"] = "made-up"
        self.assertCode("INVALID", self.store.commit, self.run, p)
        p = proposal(self.store, self.run, 1)
        p["delta"]["updates"][0]["value"].pop("justification")
        self.assertCode("INVALID", self.store.commit, self.run, p)

    def test_36_fresh_process_cli_query(self):
        self.compile(3)
        cmd = [sys.executable, str(ROOT / "skills/reader-state/scripts/reader_store.py"), "--root", self.tmp.name]
        result = subprocess.run(cmd, input=json.dumps({"op": "get", "run_id": self.run, "step": 3}), text=True, capture_output=True, check=True)
        answer = json.loads(result.stdout)
        self.assertTrue(answer["ok"])
        self.assertEqual(answer["result"]["issues"]["Q1.L3"]["status"], "open")
        self.assertEqual(answer["result"]["model_calls"], 0)

    def test_37_not_compiled_and_complete(self):
        self.assertCode("NOT_COMPILED", self.store.get, self.run, 1)
        self.compile()
        self.assertCode("COMPLETE", self.store.context, self.run)

    def test_38_query_wrong_session_anchor(self):
        self.compile()
        s = self.store.open_session(self.run, 3, "dialogue")
        self.assertCode("CONFLICT", self.store.query_context, self.run, 5, s["session_id"])

    def test_39_inquiry_cannot_self_cite_answer(self):
        self.compile(3)
        s = self.store.open_session(self.run, 3, "dialogue")
        x = self.exchange(claims=[{"text": "Circular claim.", "basis": "inference", "evidence": [{"kind": "inquiry", "ref": "t1.answer"}]}])
        self.assertCode("VISIBILITY", self.store.append_exchange, self.run, s["session_id"], s["head_hash"], x)

    def test_40_demo_end_to_end(self):
        result = run_demo(Path(self.tmp.name) / "demo")
        self.assertTrue(result["verification"]["complete"])
        self.assertEqual(result["verification"]["sessions"], 2)

    def test_41_duplicate_update_rejected(self):
        p = proposal(self.store, self.run, 1)
        p["delta"]["updates"].append(copy.deepcopy(p["delta"]["updates"][0]))
        self.assertCode("INVALID", self.store.commit, self.run, p)

    def test_42_invalid_remove_rejected(self):
        p = proposal(self.store, self.run, 1)
        p["delta"]["updates"] = [{"register": "understanding", "item_id": "absent", "action": "remove", "reason": "Fixture", "evidence": refs(1)}]
        self.assertCode("INVALID", self.store.commit, self.run, p)

    def test_43_no_nonfinite_configuration(self):
        self.config["sampling"] = {"temperature": float("nan")}
        with self.assertRaises(ValueError):
            self.store.create(self.doc, self.reader, self.config)

    def test_44_dispatch_surface(self):
        self.assertEqual(len(self.store.dispatch({"op": "list"})), 1)
        self.assertCode("INVALID", self.store.dispatch, {"op": "delete"})
        self.assertCode("INVALID", self.store.dispatch, {"op": "get", "unknown": 4})


if __name__ == "__main__":
    unittest.main()
