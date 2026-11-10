from contextlib import contextmanager
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile

from aresos_control.engine import Engine
from aresos_control.storage import short_description
from support import EngineCase, ROOT, WORK, message


class Crashes(EngineCase):
    def kill_at(self, point, mode, arguments, occurrence=1, restore_backup=False):
        self.engine.close()
        (self.root / ("arguments.json" if mode in {"reserve", "reserve_delete", "repair"} else "approval.json")).write_text(json.dumps(arguments))
        command = [sys.executable, str(ROOT / "control/tests/crash_worker.py"), str(self.root), point, mode, str(occurrence)]
        if restore_backup:
            command.append("backup")
        result = subprocess.run(command,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, -signal.SIGKILL, result.stdout + result.stderr)
        # Inspect the killed record and copy the backup before constructing an
        # Engine: startup recovery must not hide a missing durability fence.
        self.killed_records = [row for raw in (self.root / "independent/operations.jsonl").read_text().splitlines()
                               if "commit" not in (row := json.loads(raw))]
        if restore_backup:
            (self.root / "state/control.sqlite").write_bytes((self.root / "preceding.sqlite").read_bytes())
        self.engine = Engine(self.root / "state", self.root / "independent")
        latest = {}
        for event in self.engine.store.events:
            latest.update({op["id"]: op for op in event["operations"]})
        for _, op in self.engine.store.items("op:"):
            self.assertIn(op["id"], latest, "SQLite operation missing from independent record")
            if not self.engine.store.locked:
                self.assertEqual(op["state"], latest[op["id"]]["state"])

    @contextmanager
    def fresh_store(self):
        previous = self.root, self.engine
        with tempfile.TemporaryDirectory(dir=WORK) as directory:
            self.root = Path(directory)
            self.engine = Engine(self.root / "state", self.root / "independent")
            try:
                yield
            finally:
                self.engine.close()
                self.root, self.engine = previous

    def check_backup_recovery(self, expected_ids=None):
        seq = json.loads((self.root / "preceding-seq.json").read_text())["seq"]
        record = self.killed_records[-1]
        self.assertEqual(record["seq"], seq, "The killed write must already be fenced outside SQLite")
        known = {op["id"]: op for op in record["operations"]}
        if expected_ids is not None:
            self.assertEqual(set(known), set(expected_ids))
        self.assertTrue(self.engine.pending()["restore_required"])
        refused = self.call("testapp_list", {"limit": 1})
        self.assertEqual(refused["error"]["code"], "restore_required")
        arrivals = {op_id: self.engine.receiver.evidence(op_id)["arrivals"] for op_id in known}
        confirmed = self.data("control_restore_confirm", {"confirm": "invalidate earlier approvals"}, admin=True)
        self.assertTrue(set(known) <= set(confirmed["unknown"]))
        for op_id, compact in known.items():
            op = self.engine.operation(op_id)
            self.assertEqual(op["state"], "unknown")
            self.assertEqual(short_description(op), compact["description"])
            if op["action"] in {"testapp_send", "testapp_delete"}:
                self.assertFalse(self.call(op["action"], op["approval"])["ok"])
        self.restart()
        self.assertFalse(self.engine.store.locked)
        for op_id in known:
            self.assertEqual(self.engine.operation(op_id)["state"], "unknown")
            self.assertEqual(self.engine.receiver.evidence(op_id)["arrivals"], arrivals[op_id])
            self.assertEqual(len(arrivals[op_id]), len(set(arrivals[op_id])))
        return known

    def test_backup_before_first_restart_at_every_reservation_write(self):
        for mode in ("reserve", "reserve_delete"):
            for point in ("journal_appended", "sqlite_prepared", "sqlite_committed", "journal_committed"):
                with self.subTest(mode=mode, point=point), self.fresh_store():
                    args = message(subject="Missing reservation", text="Private body stays out of record")
                    if mode == "reserve_delete":
                        refs = [item["reference"] for item in self.data("testapp_list", {"limit": 2})["items"]]
                        args = {"references": refs}
                    self.kill_at(point, mode, args, restore_backup=True)
                    known = self.check_backup_recovery()
                    self.assertEqual(len(known), 1)
                    op_id = next(iter(known))
                    op = self.engine.operation(op_id)
                    self.assertEqual(op["payload"], {})
                    self.assertNotIn("text", op["approval"]["description"])
                    if mode == "reserve":
                        self.assertEqual(op["approval"]["description"]["subject"], args["subject"])
                    else:
                        self.assertEqual([item["reference"] for item in op["approval"]["description"]["targets"]], refs)
                    self.assertEqual(self.engine.receiver.evidence(op_id)["arrivals"], [])

    def test_backup_before_first_restart_at_every_send_write(self):
        # The same durability points occur in submission, each recipient/local
        # stage and the final outcome, so target each occurrence explicitly.
        writes = (("submission+receive", 0), ("alpha", 1), ("beta", 2),
                  ("hidden+sent_copy_context", 3), ("sent_copy+answered_context", 3),
                  ("answered_flag", 3), ("outcome", 3))
        for occurrence, (write, arrivals) in enumerate(writes, 1):
            for point in ("journal_appended", "sqlite_prepared", "sqlite_committed", "journal_committed"):
                with self.subTest(write=write, point=point), self.fresh_store():
                    approval = self.reserve(subject="Send write " + write)
                    self.kill_at(point, "send", approval, occurrence, restore_backup=True)
                    self.check_backup_recovery([approval["operation_id"]])
                    before = self.engine.receiver.evidence(approval["operation_id"])["arrivals"]
                    self.assertEqual(len(before), arrivals)
                    self.assertFalse(self.call("testapp_send", approval)["ok"])
                    self.restart()
                    self.assertFalse(self.call("testapp_send", approval)["ok"])
                    self.assertEqual(self.engine.receiver.evidence(approval["operation_id"])["arrivals"], before)

    def test_backup_before_first_restart_at_every_delete_write(self):
        writes = ("submission+delete_context", "delete:1", "stage:1", "delete:2", "stage:2", "outcome")
        for occurrence, write in enumerate(writes, 1):
            for point in ("journal_appended", "sqlite_prepared", "sqlite_committed", "journal_committed"):
                with self.subTest(write=write, point=point), self.fresh_store():
                    refs = [item["reference"] for item in self.data("testapp_list", {"limit": 2})["items"]]
                    approval = self.data("testapp_prepare_delete", {"references": refs})["approval"]
                    self.kill_at(point, "delete", approval, occurrence, restore_backup=True)
                    self.check_backup_recovery([approval["operation_id"]])
                    items = self.engine.store.get("testapp")["items"]
                    self.assertFalse(self.call("testapp_delete", approval)["ok"])
                    self.restart()
                    self.assertFalse(self.call("testapp_delete", approval)["ok"])
                    self.assertEqual(self.engine.store.get("testapp")["items"], items)

    def test_backup_before_first_restart_at_every_repair_write(self):
        for occurrence, write in enumerate(("reservation", "submission+context", "outcome"), 1):
            for point in ("journal_appended", "sqlite_prepared", "sqlite_committed", "journal_committed"):
                with self.subTest(write=write, point=point), self.fresh_store():
                    self.configure("sent_copy")
                    approval = self.reserve()
                    self.data("testapp_send", approval)
                    self.configure()
                    op_id = approval["operation_id"]
                    before = self.engine.receiver.evidence(op_id)["arrivals"]
                    self.kill_at(point, "repair", {"operation_id": op_id, "stage": "sent_copy"}, occurrence, restore_backup=True)
                    known = self.check_backup_recovery()
                    repairs = [op for op in known.values() if op["description"]["action"] == "testapp_operation_repair"]
                    self.assertEqual(len(repairs), 1)
                    self.assertEqual(repairs[0]["description"]["targets"], [op_id])
                    self.assertFalse(self.call("testapp_send", approval)["ok"])
                    self.assertEqual(self.engine.receiver.evidence(op_id)["arrivals"], before)

    def test_backup_before_first_restart_at_every_restore_write(self):
        for tail in (False, True):
            for point in ("journal_appended", "sqlite_prepared", "sqlite_committed", "journal_committed"):
                with self.subTest(uncommitted_tail=tail, point=point), self.fresh_store():
                    approval = self.reserve()
                    if tail:
                        self.kill_at("journal_appended", "reserve", message(subject="Unacknowledged before restore"), restore_backup=True)
                        missing = self.killed_records[-1]["operations"][0]["id"]
                        before = []
                    else:
                        backup = sqlite3.connect(self.root / "older.sqlite")
                        self.engine.store.db.backup(backup)
                        backup.close()
                        recent = self.reserve(subject="Sent before restore")
                        missing = recent["operation_id"]
                        self.data("testapp_send", recent)
                        before = self.engine.receiver.evidence(missing)["arrivals"]
                        self.engine.close()
                        (self.root / "state/control.sqlite").write_bytes((self.root / "older.sqlite").read_bytes())
                        self.engine = Engine(self.root / "state", self.root / "independent")
                    self.assertTrue(self.engine.store.locked)
                    self.kill_at(point, "restore", {}, restore_backup=True)
                    known = self.check_backup_recovery([approval["operation_id"], missing])
                    self.assertEqual(known[missing]["state"], "unknown")
                    self.assertFalse(self.call("testapp_send", approval)["ok"])
                    self.assertEqual(self.engine.receiver.evidence(missing)["arrivals"], before)

    def test_restart_without_restore_at_every_send_delete_and_repair_write(self):
        for mode, writes in (("send", 7), ("delete", 6), ("repair", 3), ("reserve_delete", 1)):
            for occurrence in range(1, writes + 1):
                for point in ("journal_appended", "sqlite_prepared", "sqlite_committed", "journal_committed"):
                    with self.subTest(mode=mode, write=occurrence, point=point), self.fresh_store():
                        if mode in {"delete", "reserve_delete"}:
                            refs = [item["reference"] for item in self.data("testapp_list", {"limit": 2})["items"]]
                            args = {"references": refs}
                            if mode == "delete":
                                args = self.data("testapp_prepare_delete", args)["approval"]
                        else:
                            if mode == "repair":
                                self.configure("sent_copy")
                            args = self.reserve()
                            if mode == "repair":
                                self.data("testapp_send", args)
                                self.configure()
                                args = {"operation_id": args["operation_id"], "stage": "sent_copy"}
                        self.kill_at(point, mode, args, occurrence)
                        self.assertEqual(self.engine.store.locked, point == "journal_appended")
                        if self.engine.store.locked:
                            self.data("control_restore_confirm", {"confirm": "invalidate earlier approvals"}, admin=True)
                        known = self.killed_records[-1]["operations"]
                        before = {op["id"]: self.engine.receiver.evidence(op["id"])["arrivals"] for op in known}
                        for compact in known:
                            op = self.engine.operation(compact["id"])
                            expected = "unknown" if point == "journal_appended" or compact["state"] == "submitting" else compact["state"]
                            self.assertEqual(op["state"], expected)
                            self.assertEqual(short_description(op), compact["description"])
                            if op["state"] == "reserved":
                                self.data("testapp_operation_cancel", {"operation_id": op["id"]})
                        items = self.engine.store.get("testapp")["items"]
                        self.restart()
                        for compact in known:
                            op = self.engine.operation(compact["id"])
                            self.assertNotIn(op["state"], {"reserved", "submitting"})
                            if op["action"] in {"testapp_send", "testapp_delete"}:
                                self.call(op["action"], op["approval"])
                            self.assertEqual(self.engine.receiver.evidence(op["id"])["arrivals"], before[op["id"]])
                        self.assertEqual(self.engine.store.get("testapp")["items"], items)

    def test_uncommitted_record_with_missing_staged_event_requires_restore(self):
        import sqlite3
        backup = sqlite3.connect(self.root / "backup.sqlite")
        self.engine.store.db.backup(backup)
        backup.close()
        self.kill_at("sqlite_prepared", "reserve", message(subject="Unacknowledged reservation"))
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
                self.assertEqual(self.engine.store.locked, point == "journal_appended")
                if self.engine.store.locked:
                    self.data("control_restore_confirm", {"confirm": "invalidate earlier approvals"}, admin=True)
                op = self.engine.operation(approval["operation_id"])
                self.assertEqual(op["state"], "reserved" if point == "revalidated" else "done" if point == "outcome" else "unknown")
                before = self.engine.receiver.evidence(op["id"])["arrivals"]
                self.assertEqual(len(before), len(set(before)))
                if op["state"] == "reserved":
                    self.assertEqual(before, [])
                    self.data("testapp_operation_cancel", {"operation_id": op["id"]})
                if point == "journal_appended":
                    self.assertEqual(self.call("testapp_send", approval)["error"]["code"], "refused")
                else:
                    self.data("testapp_send", approval)
                self.restart()
                if point == "journal_appended":
                    self.assertEqual(self.call("testapp_send", approval)["error"]["code"], "refused")
                else:
                    self.data("testapp_send", approval)
                self.assertEqual(self.engine.receiver.evidence(op["id"])["arrivals"], before)

    def test_kill9_reservation_boundaries_never_sends(self):
        for point in ["sqlite_prepared", "journal_appended", "sqlite_committed", "journal_committed", "reserved"]:
            with self.subTest(point=point):
                self.kill_at(point, "reserve", message(subject=point))
                self.assertEqual(self.engine.store.locked, point == "journal_appended")
                if self.engine.store.locked:
                    self.data("control_restore_confirm", {"confirm": "invalidate earlier approvals"}, admin=True)
                ops = [op for _, op in self.engine.store.items("op:") if op["approval"]["description"]["subject"] == point]
                self.assertEqual(len(ops), 1)
                self.assertEqual(ops[0]["state"], "unknown" if point == "journal_appended" else "reserved")
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
