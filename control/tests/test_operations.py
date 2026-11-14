import copy
import json
from pathlib import Path
import sqlite3
import time
from unittest.mock import Mock, patch

from aresos_control.common import ASK_LIMIT, Refused, approval_input, canonical, digest, visible
from aresos_control.definitions import ACTIONS, BY_NAME, tools_for
from aresos_control.hooks import output
from support import EngineCase, ROOT, message


class Operations(EngineCase):
    def test_default_approval_lasts_fifteen_minutes_at_boundary(self):
        self.assertEqual(self.engine.ttl, 900)
        self.assertEqual(json.loads((ROOT / "control/settings/service.json").read_text())["approval_ttl"], 900)
        for elapsed, expected in ((899.999, "done"), (900.001, "failed")):
            with self.subTest(elapsed=elapsed):
                with patch("aresos_control.engine.time.time", return_value=1000):
                    approval = self.reserve()
                self.assertEqual(approval["description"]["expires_at"], 1900)
                adapter = self.engine.adapters["testapp"]
                with patch("aresos_control.engine.time.time", return_value=1000 + elapsed), patch.object(adapter, "drop") as drop:
                    result = self.data("testapp_send", approval)["operation"]
                self.assertEqual(result["state"], expected)
                self.assertEqual(drop.call_count, int(expected == "failed"))
                arrivals = self.engine.receiver.evidence(approval["operation_id"])["arrivals"]
                self.assertEqual(arrivals, [] if expected == "failed" else ["alpha", "beta", "hidden"])

    def test_idempotency_hash_and_restart(self):
        approval = self.reserve()
        first = self.data("testapp_send", approval)
        self.assertEqual(first["operation"]["state"], "done")
        arrivals = self.engine.receiver.evidence(approval["operation_id"])["arrivals"]
        self.assertEqual(arrivals, ["alpha", "beta", "hidden"])
        self.restart()
        self.assertEqual(self.data("testapp_send", approval), first)
        self.assertEqual(self.engine.receiver.evidence(approval["operation_id"])["arrivals"], arrivals)
        altered = copy.deepcopy(approval)
        altered["description"]["text"] = "different"
        self.assertEqual(self.call("testapp_send", altered)["error"]["code"], "stale_approval")
        self.assertEqual(self.call("testapp_delete", approval)["error"]["code"], "stale_approval")

    def test_cancel_expire_only_reserved_and_notices(self):
        approval = self.reserve()
        op = {"operation_id": approval["operation_id"]}
        self.assertEqual(self.data("testapp_operation_cancel", op)["operation"]["state"], "failed")
        self.assertEqual(self.data("testapp_send", approval)["operation"]["state"], "failed")
        self.assertTrue(self.data("control_pending")["total"])
        self.data("testapp_notice_ack", op)
        self.assertEqual(self.data("control_pending")["total"], 0)
        self.engine.ttl = -1
        expired = self.reserve()
        self.engine.expire()
        self.assertIn("expired", self.data("testapp_operation_status", {"operation_id": expired["operation_id"]})["operation"]["reason"])
        self.assertEqual(self.data("testapp_send", expired)["operation"]["state"], "failed")
        self.assertFalse(self.call("testapp_operation_cancel", {"operation_id": expired["operation_id"]})["ok"])
        self.engine.ttl = 120
        submitted = self.reserve()
        self.data("testapp_send", submitted)
        self.assertFalse(self.call("testapp_operation_cancel", {"operation_id": submitted["operation_id"]})["ok"])
        manual = self.reserve()
        record = self.engine.operation(manual["operation_id"])
        record["state"], record["expires"] = "submitting", 0
        self.engine.store.write({"op:" + record["id"]: record}, "testapp_send", "fixture submitting")
        self.engine.expire()
        self.assertEqual(self.engine.operation(record["id"])["state"], "submitting")
        self.assertFalse(self.call("testapp_operation_cancel", {"operation_id": record["id"]})["ok"])
        self.restart()
        self.assertEqual(self.engine.operation(record["id"])["state"], "unknown")

    def test_partial_refused_recipients_lost_answer_and_failures(self):
        self.configure(refuse=["beta"])
        approval = self.reserve()
        op = self.data("testapp_send", approval)["operation"]
        self.assertEqual(op["state"], "partial")
        self.assertEqual(op["stages"]["recipient:beta"], "refused")
        self.assertEqual(self.data("testapp_list")["items"][0]["flagged"], False)
        self.assertEqual(self.call("testapp_list")["pending"]["total"], 1)
        self.assertEqual(self.call("testapp_flag", {"reference": self.data("testapp_list")["items"][0]["reference"], "flagged": True})["pending"]["total"], 1)
        for failure, expected in [("before_submit", "failed"), ("lost_answer", "unknown"), ("sent_copy", "partial"), ("answered_flag", "partial")]:
            with self.subTest(failure=failure):
                self.configure(failure)
                approval = self.reserve()
                op = self.data("testapp_send", approval)["operation"]
                self.assertEqual(op["state"], expected)
                evidence = self.engine.receiver.evidence(op["id"])
                self.assertEqual(len(evidence["arrivals"]), 0 if failure == "before_submit" else 1 if failure == "lost_answer" else 3)
                self.data("testapp_send", approval)
                self.assertEqual(evidence, self.engine.receiver.evidence(op["id"]))
        self.configure(refuse=["alpha", "beta", "hidden"])
        self.assertEqual(self.data("testapp_send", self.reserve())["operation"]["state"], "failed")

    def test_repair_new_operation_never_submits(self):
        self.configure("sent_copy")
        approval = self.reserve()
        self.data("testapp_send", approval)
        self.configure()
        evidence = self.engine.receiver.evidence(approval["operation_id"])["arrivals"]
        for stage in ("sent_copy", "answered_flag"):
            repaired = self.data("testapp_operation_repair", {"operation_id": approval["operation_id"], "stage": stage})
            self.assertNotEqual(repaired["operation"]["id"], approval["operation_id"])
            self.assertEqual(repaired["operation"]["repair_of"], approval["operation_id"])
            self.assertEqual(repaired["operation"]["state"], "done")
            self.assertEqual(self.engine.receiver.evidence(approval["operation_id"])["arrivals"], evidence)
        self.assertEqual(repaired["original"]["state"], "done")
        self.restart()
        self.data("testapp_operation_repair", {"operation_id": approval["operation_id"], "stage": "sent_copy"})
        self.assertEqual(self.engine.receiver.evidence(approval["operation_id"])["arrivals"], evidence)
        ref = self.data("testapp_list")["items"][0]["reference"]
        deleted = self.data("testapp_prepare_delete", {"references": [ref]})["approval"]
        self.data("testapp_delete", deleted)
        refused = self.data("testapp_operation_repair", {"operation_id": deleted["operation_id"], "stage": "sent_copy"})
        self.assertEqual(refused["operation"]["state"], "failed")
        self.assertIn("refused before acting", refused["operation"]["reason"])

    def test_expiry_and_cancel_drop_only_reserved_never_release(self):
        adapter = self.engine.adapters["testapp"]
        adapter.drop = Mock()
        cancelled = self.reserve()
        self.data("testapp_operation_cancel", {"operation_id": cancelled["operation_id"]})
        self.assertEqual(adapter.drop.call_count, 1)
        self.engine.ttl = -1
        expired = self.reserve()
        self.engine.expire()
        self.assertEqual(adapter.drop.call_count, 2)
        self.data("testapp_send", expired)
        self.engine.expire()
        self.assertEqual(adapter.drop.call_count, 2)
        self.assertEqual(self.engine.receiver.evidence(expired["operation_id"])["arrivals"], [])

    def test_deadline_crossed_during_adapter_checks_never_submits(self):
        for verb in ("send", "delete"):
            for check in ("revalidate", "has_submission_evidence"):
                with self.subTest(verb=verb, check=check), patch("aresos_control.engine.time.time", return_value=100) as clock:
                    if verb == "send":
                        approval = self.reserve()
                    else:
                        ref = self.data("testapp_list")["items"][0]["reference"]
                        approval = self.data("testapp_prepare_delete", {"references": [ref]})["approval"]
                    before = self.engine.store.get("testapp")
                    adapter = self.engine.adapters["testapp"]
                    original = getattr(adapter, check)

                    def cross_deadline(*args):
                        result = original(*args)
                        clock.return_value = approval["description"]["expires_at"] + 1
                        return result

                    with patch.object(adapter, check, side_effect=cross_deadline), \
                         patch.object(adapter, "drop", wraps=adapter.drop) as drop, \
                         patch.object(adapter, "execute", wraps=adapter.execute) as execute:
                        result = self.data("testapp_" + verb, approval)
                        self.assertEqual(result["operation"]["state"], "failed")
                        self.assertEqual(result["operation"]["reason"], "expired: nothing submitted")
                        self.assertEqual(result["operation"]["stages"], {})
                        drop.assert_called_once()
                        execute.assert_not_called()
                        self.assertEqual(self.data("testapp_" + verb, approval), result)
                        drop.assert_called_once()
                    self.assertEqual(self.engine.receiver.evidence(approval["operation_id"])["arrivals"], [])
                    self.assertEqual(self.engine.store.get("testapp"), before)
                    self.restart()
                    self.assertEqual(self.data("testapp_" + verb, approval), result)

    def test_exact_references_metadata_and_delete_targets(self):
        listing = self.data("testapp_list", {"limit": 2})
        refs = [i["reference"] for i in listing["items"]]
        approval = self.data("testapp_prepare_delete", {"references": refs})["approval"]
        for target in approval["description"]["items"]:
            self.assertEqual(set(target), {"reference", "sender", "subject", "date"})
        self.data("testapp_flag", {"reference": refs[0], "flagged": True})
        self.assertFalse(self.call("testapp_delete", approval)["ok"])
        self.assertFalse(self.call("testapp_list", {"cursor": listing["cursor"]})["ok"])
        refs = [i["reference"] for i in self.data("testapp_list", {"limit": 2})["items"]]
        approval = self.data("testapp_prepare_delete", {"references": refs})["approval"]
        result = self.data("testapp_delete", approval)["operation"]
        self.assertEqual(result["state"], "done")
        self.assertEqual(result["stages"], {"target:1": "deleted", "target:2": "deleted"})
        self.assertEqual(self.data("testapp_list")["items"][0]["reference"]["id"], "3")
        self.assertEqual(self.data("testapp_delete", approval)["operation"], result)
        self.assertFalse(self.call("testapp_flag", {"reference": refs[0], "flagged": False})["ok"])

    def test_runtime_revalidates_metadata_even_without_revision(self):
        ref = self.data("testapp_list")["items"][0]["reference"]
        approval = self.data("testapp_prepare_delete", {"references": [ref]})["approval"]
        data = self.engine.store.get("testapp")
        data["items"][ref["id"]]["subject"] = "Changed externally"
        self.engine.store.write({"testapp": data}, "fixture", "external edit")
        self.assertEqual(self.call("testapp_delete", approval)["error"]["code"], "stale_approval")
        self.assertEqual(len(self.engine.store.get("testapp")["items"]), 24)

    def test_truthful_escape_full_text_size_refusal_and_far_side_evidence(self):
        text = "a\nb\r\t\x00\u202e\u2066\\u202e"
        approval = self.reserve(text=text)
        self.assertEqual(approval["description"]["text"], visible(text))
        self.assertNotIn("\u202e", approval["description"]["text"])
        self.data("testapp_send", approval)
        payload = json.loads(self.engine.receiver.db.execute("SELECT payload FROM arrivals WHERE op=? LIMIT 1", (approval["operation_id"],)).fetchone()[0])
        self.assertEqual(payload["text"], text)
        self.assertEqual(payload["bcc"], ["hidden"])
        count = len(self.engine.store.items("op:"))
        result = self.call("testapp_prepare_send", message(text="x" * ASK_LIMIT))
        self.assertEqual(result["error"]["code"], "asking_input_too_large")
        self.assertEqual(len(self.engine.store.items("op:")), count)
        for following in ("cancel", "expiry"):
            with self.subTest(following=following):
                duplicate = self.reserve()
                op_id = duplicate["operation_id"]
                self.engine.receiver.accept(op_id, "alpha", {})
                evidence = self.engine.receiver.evidence(op_id)
                self.assertFalse(self.call("testapp_send", duplicate)["ok"])
                self.assertEqual(evidence["arrivals"], ["alpha"])
                op = self.data("testapp_operation_status", {"operation_id": op_id})["operation"]
                self.assertEqual(op["state"], "unknown")
                self.assertEqual(op["stages"]["preflight_evidence"], evidence)
                self.assertIn("never submit again", op["reason"])
                self.restart()
                if following == "cancel":
                    self.assertFalse(self.call("testapp_operation_cancel", {"operation_id": op_id})["ok"])
                else:
                    with patch("aresos_control.engine.time.time", return_value=op["expires"] + 1):
                        self.engine.expire()
                self.assertEqual(self.engine.operation(op_id)["state"], "unknown")
                self.assertEqual(self.data("testapp_send", duplicate)["operation"], op)
                self.assertEqual(self.engine.receiver.evidence(op_id), evidence)

    def test_positive_preflight_finding_survives_evidence_detail_failure(self):
        approval = self.reserve()
        op_id = approval["operation_id"]
        self.engine.receiver.accept(op_id, "alpha", {})
        adapter = self.engine.adapters["testapp"]
        with patch.object(adapter, "has_submission_evidence", return_value=True), \
             patch.object(adapter, "evidence", side_effect=Refused("refused", "fixture: evidence details unavailable")):
            self.assertFalse(self.call("testapp_send", approval)["ok"])
        self.restart()
        op = self.engine.operation(op_id)
        self.assertEqual(op["state"], "unknown")
        self.assertEqual(op["stages"]["preflight_evidence"], "present")
        self.assertFalse(self.call("testapp_operation_cancel", {"operation_id": op_id})["ok"])
        self.assertEqual(self.data("testapp_send", approval)["operation"], self.engine.public_operation(op))
        self.assertEqual(self.engine.receiver.evidence(op_id)["arrivals"], ["alpha"])

    def test_read_is_unchanged_bounded_untrusted_and_errors_actionable(self):
        initial = self.engine.store.get("testapp")
        head = len(self.engine.store.events)
        seen, args = [], {"limit": 3}
        while True:
            result = self.data("testapp_list", args)
            self.assertLess(len(canonical(result)), 6000)
            self.assertTrue(all("untrusted_content" in i for i in result["items"]))
            seen.extend(i["reference"]["id"] for i in result["items"])
            if result["cursor"] is None:
                break
            args["cursor"] = result["cursor"]
        self.assertEqual(len(set(seen)), 24)
        self.assertEqual(self.engine.store.get("testapp"), initial)
        self.data("control_pending")
        self.data("control_log")
        self.assertEqual(len(self.engine.store.events), head)
        error = self.call("testapp_list", {"limit": 100})
        self.assertIn("range", error["error"]["message"])
        self.assertFalse(self.call("testapp_list", {"surprise": True})["ok"])

    def test_result_cap_refuses_instead_of_truncating(self):
        data = self.engine.store.get("testapp")
        data["items"]["1"]["text"] = "untrusted content " * 4096
        self.engine.store.write({"testapp": data}, "fixture", "oversized result fixture")
        result = self.call("testapp_list", {"limit": 1})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "result_too_large")
        self.assertNotIn("data", result)
        self.assertEqual(self.engine.store.get("testapp"), data)

    def test_service_refuses_caller_paths_and_descriptions_do_not_authorize_reuse(self):
        result = self.call("testapp_file_import", {"path": "/fixture/never-opened"})
        self.assertEqual(result["error"]["code"], "proxy_required")
        first, second = self.reserve(), self.reserve()
        self.assertFalse(self.call("testapp_send", {"question": second["question"], "operation_id": second["operation_id"], "description": first["description"]})["ok"])
        self.assertEqual(self.engine.receiver.evidence(first["operation_id"])["arrivals"], [])
        self.assertEqual(self.engine.receiver.evidence(second["operation_id"])["arrivals"], [])

    def test_changes_logged_and_pending_in_every_result_and_hooks(self):
        approval = self.reserve()
        pending = self.data("control_pending")
        self.assertEqual(pending["items"][0]["operation_id"], approval["operation_id"])
        self.assertEqual(output({"hook_event_name": "Stop", "stop_hook_active": False}, pending)["decision"], "block")
        self.assertEqual(output({"hook_event_name": "Stop", "stop_hook_active": True}, pending), {})
        prompt = output({"hook_event_name": "UserPromptSubmit", "prompt": "new owner message"}, pending)
        self.assertEqual(prompt["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")
        self.assertIn(approval["operation_id"], prompt["hookSpecificOutput"]["additionalContext"])
        self.assertNotIn("decision", prompt)
        self.assertEqual(output({"hook_event_name": "Stop"}, {"total": 0}), {})
        self.assertEqual(output({"hook_event_name": "Stop"}, {"service_unavailable": True})["decision"], "block")
        self.assertFalse(self.call("testapp_fixture_configure", {"refuse": [], "failure": "none"})["ok"])
        self.assertEqual(self.call("missing_action")["pending"]["total"], 1)
        events = self.data("control_log", {"limit": 10})["items"]
        self.assertTrue(any(e["operation_id"] == approval["operation_id"] and e["summary"].startswith("reserved") for e in events))
        self.assertTrue(all("time" in e and "outcome" in e for e in events))

    def test_restore_older_log_rejects_earlier_ids_missing_ops_unknown(self):
        older = self.reserve()
        backup = sqlite3.connect(self.root / "backup.sqlite")
        self.engine.store.db.backup(backup)
        backup.close()
        recent = self.reserve(subject="Recent description must survive restore")
        self.data("testapp_send", recent)
        self.engine.close()
        (self.root / "state" / "control.sqlite").write_bytes((self.root / "backup.sqlite").read_bytes())
        from aresos_control.engine import Engine
        self.engine = Engine(self.root / "state", self.root / "independent")
        self.assertTrue(self.engine.store.locked)
        self.assertEqual(self.call("testapp_send", older)["error"]["code"], "restore_required")
        self.assertEqual(self.call("testapp_send", recent)["error"]["code"], "restore_required")
        self.assertFalse(self.call("control_restore_confirm", {"confirm": "invalidate earlier approvals"})["ok"])
        restored = self.data("control_restore_confirm", {"confirm": "invalidate earlier approvals"}, admin=True)
        self.assertIn(recent["operation_id"], restored["unknown"])
        op = self.data("testapp_operation_status", {"operation_id": recent["operation_id"]})["operation"]
        self.assertEqual(op["state"], "unknown")
        self.assertIn("Recent description", op["approval"]["description"]["subject"])
        self.assertFalse(self.call("testapp_send", older)["ok"])
        self.assertFalse(self.call("testapp_send", recent)["ok"])
        self.assertNotEqual(self.reserve()["operation_id"].split(":")[0], recent["operation_id"].split(":")[0])
        self.restart()
        self.assertFalse(self.engine.store.locked)
        self.assertEqual(self.engine.operation(recent["operation_id"])["state"], "unknown")


class Generated(EngineCase):
    def test_artifact_drift_effects_ask_rules_and_owner_only_absent(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("generator", ROOT / "control" / "generate.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name, content in module.generated().items():
            self.assertEqual((ROOT / name).read_text(), content, name)
        ask = json.loads((ROOT / "control/settings/ask-rules.json").read_text())["permissions"]["ask"]
        self.assertEqual(set(ask), {f"mcp__{a.app}__{a.verb}" for a in ACTIONS if (a.effect in {"send", "delete"} or a.asking_read) and not a.owner_only and not a.trusted_send})
        for action in ACTIONS:
            self.assertIn(action.effect, {"read", "change", "send", "delete"})
            self.assertEqual(action.input.get("additionalProperties"), False)
            from aresos_control.definitions import instructions_for
            self.assertIn("untrusted", action.description + instructions_for(action.app))
            if action.owner_only:
                self.assertNotIn(action.verb, [t["name"] for t in tools_for(action.app)])
        self.assertEqual(len(BY_NAME), len(ACTIONS))
