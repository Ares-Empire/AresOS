import json
import sqlite3
from unittest.mock import patch

from aresos_control.common import ASK_LIMIT, FILE_LIMIT, canonical, digest, sha256
from support import EngineCase


class Record(EngineCase):
    def test_record_size_is_independent_of_body_and_attachment(self):
        journal = self.root / "independent/operations.jsonl"
        attachment = (b"private-attachment-marker-" * (FILE_LIMIT // 26 + 1))[:FILE_LIMIT]
        self.assertEqual(len(attachment), FILE_LIMIT)
        key = self.engine.blobs.put(attachment)
        ref = {"sha256": key, "size": len(attachment), "name": "private-attachment.txt", "real_path": "/fixture/private-path"}
        self.engine.store.write({"blob:" + digest(ref): ref}, "testapp_file_import", "fixture import")
        while len(self.engine.store.events) < 10:
            self.engine.store.write({}, "fixture", "align sequence widths")
        sizes = []
        with patch("aresos_control.engine.time.time", return_value=1000):
            for large in (False, True):
                # IDs and timestamps have fixed length, as do all input hashes.
                args = {"text": "tiny-body-marker", "to": ["alpha"], "bcc": []}
                if large:
                    args["attachments"] = [ref]
                    template = {"operation_id": "0" * 32 + ":" + "0" * 32,
                                "description": {"action": "testapp_send", "account": "fixture", "to": ["alpha"],
                                                "cc": [], "bcc": [], "subject": "Fixture message", "text": "",
                                                "attachments": [ref], "expires_at": 1900}}
                    args["text"] = "private-body-marker-" + "z" * (ASK_LIMIT - len(canonical(template).encode()) - 20)
                    self.assertEqual(len(args["text"]) + len(canonical(template).encode()), ASK_LIMIT)
                before = journal.stat().st_size
                approval = self.reserve(**args)
                if large:
                    self.assertEqual(len(canonical(approval).encode()), ASK_LIMIT)
                self.assertEqual(self.data("testapp_send", approval)["operation"]["state"], "done")
                sizes.append(journal.stat().st_size - before)
        self.assertEqual(sizes[0], sizes[1])
        with patch("aresos_control.engine.time.time", return_value=1000):
            before = journal.stat().st_size
            typical = self.reserve()
            self.data("testapp_send", typical)
            typical_size = journal.stat().st_size - before
        raw = journal.read_bytes()
        for forbidden in (b"tiny-body-marker", b"private-body-marker", b"private-attachment-marker",
                          b"private-attachment.txt", b"private-path", attachment[:64].hex().encode(), b"Untrusted fixture content"):
            self.assertNotIn(forbidden, raw)
        for line in raw.splitlines():
            row = json.loads(line)
            if "operations" in row:
                self.assertEqual(set(row), {"format", "seq", "previous", "time", "generation", "operations", "hash"})
                for op in row["operations"]:
                    self.assertEqual(set(op), {"id", "generation", "input_hash", "description", "state"})
                    self.assertLessEqual(op["description"].keys(), {"action", "account", "to", "cc", "bcc", "subject", "title", "targets"})
        # This send has six durable state/stage records, each with a commit marker.
        print(f"Record growth: tiny send={sizes[0]} bytes; maximum body + 25 MiB send={sizes[1]} bytes; "
              f"6 state/stage records, mean={sizes[0] / 6:.1f} bytes per record including commit")
        print(f"Record growth: typical three-recipient send={typical_size} bytes across 8 state/stage records")
        self.assertTrue(any("private-body-marker" in canonical(e) for e in self.engine.store.audit()))
        self.assertIn(b"private-attachment-marker", self.engine.blobs.read(key))

    def test_log_reads_sqlite_even_when_independent_record_has_no_audit_data(self):
        approval = self.reserve(text="body-only-in-main-log")
        ref = self.data("testapp_list", {"limit": 1})["items"][0]["reference"]
        self.data("testapp_flag", {"reference": ref, "flagged": True})
        raw = (self.root / "independent/operations.jsonl").read_text()
        self.assertNotIn("flag exact", raw)
        self.assertNotIn("body-only-in-main-log", raw)
        entries, args = [], {"limit": 10}
        while True:
            page = self.data("control_log", args)
            entries.extend(page["items"])
            if not page["cursor"]:
                break
            args["cursor"] = page["cursor"]
        self.assertTrue(any(e["action"] == "testapp_flag" and e["summary"].startswith("flag exact") for e in entries))
        self.assertTrue(any(e["operation_id"] == approval["operation_id"] for e in entries))
        self.restart()
        self.assertEqual(self.data("control_log", {"limit": 10})["items"], entries)

    def test_restore_retains_only_short_missing_send_and_delete_descriptions(self):
        backup = sqlite3.connect(self.root / "backup.sqlite")
        self.engine.store.db.backup(backup)
        backup.close()
        sent = self.reserve(subject="Recognisable send", text="body must not return after restore")
        self.data("testapp_send", sent)
        reference = self.data("testapp_list", {"limit": 1})["items"][0]["reference"]
        deleted = self.data("testapp_prepare_delete", {"references": [reference]})["approval"]
        self.data("testapp_delete", deleted)
        self.engine.close()
        (self.root / "state/control.sqlite").write_bytes((self.root / "backup.sqlite").read_bytes())
        from aresos_control.engine import Engine
        self.engine = Engine(self.root / "state", self.root / "independent")
        self.assertTrue(self.engine.store.locked)
        restored = self.data("control_restore_confirm", {"confirm": "invalidate earlier approvals"}, admin=True)
        self.assertEqual(set(restored["unknown"]), {sent["operation_id"], deleted["operation_id"]})
        send_op = self.engine.operation(sent["operation_id"])
        self.assertEqual(send_op["approval"]["description"]["subject"], "Recognisable send")
        self.assertNotIn("text", send_op["approval"]["description"])
        delete_op = self.engine.operation(deleted["operation_id"])
        self.assertEqual(delete_op["approval"]["description"]["targets"][0]["reference"], reference)
        self.restart()
        for approval, action in ((sent, "send"), (deleted, "delete")):
            self.assertEqual(self.engine.operation(approval["operation_id"])["state"], "unknown")
            self.assertFalse(self.call("testapp_" + action, approval)["ok"])
