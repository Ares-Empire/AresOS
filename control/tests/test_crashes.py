import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

from aresos_control.engine import Engine
from support import EngineCase, ROOT, WORK, message


class Crashes(EngineCase):
    def kill_at(self, point, mode, arguments):
        self.engine.close()
        (self.root / ("arguments.json" if mode in {"reserve", "repair"} else "approval.json")).write_text(json.dumps(arguments))
        result = subprocess.run([sys.executable, str(ROOT / "control/tests/crash_worker.py"), str(self.root), point, mode],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, -signal.SIGKILL, result.stdout + result.stderr)
        self.engine = Engine(self.root / "state", self.root / "independent")
        latest = {}
        for event in self.engine.store.events:
            latest.update({op["id"]: op for op in event["operations"]})
        for _, op in self.engine.store.items("op:"):
            self.assertIn(op["id"], latest, "SQLite operation missing from independent record")
            if not self.engine.store.locked:
                self.assertEqual(op["state"], latest[op["id"]]["state"])

    def test_uncommitted_record_with_missing_staged_event_requires_restore(self):
        import sqlite3
        backup = sqlite3.connect(self.root / "backup.sqlite")
        self.engine.store.db.backup(backup)
        backup.close()
        self.kill_at("journal_appended", "reserve", message(subject="Unacknowledged reservation"))
        # Remove only the commit marker recovery just wrote, reconstructing the
        # exact durable independent record at the killed write boundary.
        self.engine.close()
        journal = self.root / "independent/operations.jsonl"
        rows = journal.read_bytes().splitlines(keepends=True)
        journal.write_bytes(b"".join(rows[:-1]))
        (self.root / "state/control.sqlite").write_bytes((self.root / "backup.sqlite").read_bytes())
        self.engine = Engine(self.root / "state", self.root / "independent")
        self.assertTrue(self.engine.store.locked)
        restored = self.data("control_restore_confirm", {"confirm": "invalidate earlier approvals"}, admin=True)
        self.assertEqual(len(restored["unknown"]), 1)
        op_id = restored["unknown"][0]
        self.assertEqual(self.engine.operation(op_id)["approval"]["description"]["subject"], "Unacknowledged reservation")
        self.assertEqual(self.engine.receiver.evidence(op_id)["arrivals"], [])
        self.restart()
        self.assertFalse(self.engine.store.locked)
        self.assertEqual(self.engine.operation(op_id)["state"], "unknown")

    def test_kill9_every_send_boundary_never_resubmits(self):
        points = ["sqlite_prepared", "journal_appended", "sqlite_committed", "journal_committed", "revalidated", "submitting",
                  "receiver_arrival:alpha", "stage:recipient:alpha", "receiver_arrival:beta", "stage:recipient:beta",
                  "receiver_arrival:hidden", "stage:recipient:hidden", "receiver_stage:sent_copy", "stage:sent_copy",
                  "receiver_stage:answered_flag", "stage:answered_flag", "before_outcome", "outcome"]
        for point in points:
            with self.subTest(point=point):
                approval = self.reserve(subject="Crash at " + point)
                self.kill_at(point, "send", approval)
                self.assertFalse(self.engine.store.locked)
                op = self.engine.operation(approval["operation_id"])
                self.assertEqual(op["state"], "reserved" if point == "revalidated" else "done" if point == "outcome" else "unknown")
                before = self.engine.receiver.evidence(op["id"])["arrivals"]
                self.assertEqual(len(before), len(set(before)))
                if op["state"] == "reserved":
                    self.assertEqual(before, [])
                    self.data("testapp_operation_cancel", {"operation_id": op["id"]})
                self.data("testapp_send", approval)
                self.restart()
                self.data("testapp_send", approval)
                self.assertEqual(self.engine.receiver.evidence(op["id"])["arrivals"], before)

    def test_kill9_reservation_boundaries_never_sends(self):
        for point in ["sqlite_prepared", "journal_appended", "sqlite_committed", "journal_committed", "reserved"]:
            with self.subTest(point=point):
                self.kill_at(point, "reserve", message(subject=point))
                ops = [op for _, op in self.engine.store.items("op:") if op["payload"]["subject"] == point]
                self.assertEqual(len(ops), 1)
                self.assertEqual(ops[0]["state"], "reserved")
                self.assertEqual(self.engine.receiver.evidence(ops[0]["id"])["arrivals"], [])

    def test_kill9_every_delete_target_and_stage_no_resume(self):
        for point in ["deleted:1", "stage:target:1", "deleted:2", "stage:target:2", "before_outcome", "outcome"]:
            with self.subTest(point=point):
                # Seed a new app epoch for each independent deletion scenario.
                data = self.engine.store.get("testapp")
                for i in ("1", "2"):
                    data["items"][i] = {"id": i, "revision": 1, "sender": "fixture", "subject": "delete", "date": "2026-01-01", "text": "data", "flagged": False}
                self.engine.store.write({"testapp": data}, "fixture", "reset exact targets")
                refs = [i["reference"] for i in self.data("testapp_list", {"limit": 2})["items"]]
                approval = self.data("testapp_prepare_delete", {"references": refs})["approval"]
                self.kill_at(point, "delete", approval)
                items = self.engine.store.get("testapp")["items"]
                self.assertEqual(self.engine.operation(approval["operation_id"])["state"], "done" if point == "outcome" else "unknown")
                self.data("testapp_delete", approval)
                self.assertEqual(self.engine.store.get("testapp")["items"], items)

    def test_kill9_repair_no_submit_after_restart(self):
        self.configure("sent_copy")
        approval = self.reserve()
        self.data("testapp_send", approval)
        self.configure()
        evidence = self.engine.receiver.evidence(approval["operation_id"])["arrivals"]
        self.kill_at("receiver_stage:sent_copy", "repair", {"operation_id": approval["operation_id"], "stage": "sent_copy"})
        repairs = [op for _, op in self.engine.store.items("op:") if op.get("repair_of") == approval["operation_id"]]
        self.assertEqual(len(repairs), 1)
        self.assertEqual(repairs[0]["state"], "unknown")
        self.assertEqual(self.engine.receiver.evidence(approval["operation_id"])["arrivals"], evidence)

    def test_kill9_during_restore_confirmation_can_be_confirmed_again(self):
        import sqlite3
        for point in ("sqlite_prepared", "journal_appended", "sqlite_committed", "journal_committed"):
            with self.subTest(point=point):
                approval = self.reserve()
                backup = sqlite3.connect(self.root / "backup.sqlite")
                self.engine.store.db.backup(backup)
                backup.close()
                recent = self.reserve(subject="restore crash " + point)
                self.data("testapp_send", recent)
                self.engine.close()
                (self.root / "state/control.sqlite").write_bytes((self.root / "backup.sqlite").read_bytes())
                self.engine = Engine(self.root / "state", self.root / "independent")
                self.assertTrue(self.engine.store.locked)
                self.kill_at(point, "restore", {})
                if self.engine.store.locked:
                    self.data("control_restore_confirm", {"confirm": "invalidate earlier approvals"}, admin=True)
                self.assertFalse(self.call("testapp_send", approval)["ok"])
                self.assertFalse(self.call("testapp_send", recent)["ok"])
                self.restart()
                self.assertFalse(self.engine.store.locked)
                self.assertEqual(self.engine.operation(recent["operation_id"])["state"], "unknown")
                self.assertEqual(len(self.engine.receiver.evidence(recent["operation_id"])["arrivals"]), 3)
