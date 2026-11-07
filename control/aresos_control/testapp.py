"""Fake app and a durable far-side receiver. Neither uses a network or real account."""
import json
from pathlib import Path
import sqlite3
import uuid

from .adapters import NothingLeft, Uncertain
from .common import Refused, canonical, digest


class Receiver:
    """Separate fixture storage represents the far side, never deduplicates arrivals."""
    def __init__(self, directory, checkpoint=lambda _: None):
        self.db = sqlite3.connect(Path(directory) / "receiver.sqlite")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("CREATE TABLE IF NOT EXISTS arrivals (id INTEGER PRIMARY KEY, op TEXT, recipient TEXT, payload TEXT);"
                              "CREATE TABLE IF NOT EXISTS stages (op TEXT, stage TEXT, PRIMARY KEY(op,stage));"
                              "CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY, value TEXT);")
        self.db.commit()
        self.checkpoint = checkpoint

    def config(self):
        row = self.db.execute("SELECT value FROM config WHERE id=1").fetchone()
        return json.loads(row[0]) if row else {"refuse": [], "failure": "none"}

    def configure(self, value):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO config VALUES (1,?)", (canonical(value),))

    def accept(self, operation_id, recipient, payload):
        config = self.config()
        if config["failure"] == "before_submit":
            raise NothingLeft("Fixture refused before any recipient submission.")
        if recipient in config["refuse"]:
            return "refused"
        with self.db:
            self.db.execute("INSERT INTO arrivals(op,recipient,payload) VALUES (?,?,?)", (operation_id, recipient, canonical(payload)))
        self.checkpoint("receiver_arrival:" + recipient)
        if config["failure"] == "lost_answer":
            raise Uncertain("Receiver recorded arrival but its answer was lost; do not resubmit.")
        return "accepted"

    def local_stage(self, operation_id, stage):
        if self.config()["failure"] == stage:
            raise RuntimeError("Fixture failed " + stage + "; repair this local stage only.")
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO stages VALUES (?,?)", (operation_id, stage))
        self.checkpoint("receiver_stage:" + stage)

    def evidence(self, operation_id):
        return {"message_id": "<" + operation_id + "@testapp.invalid>",
                "arrivals": [r[0] for r in self.db.execute("SELECT recipient FROM arrivals WHERE op=? ORDER BY id", (operation_id,))],
                "local_stages": [r[0] for r in self.db.execute("SELECT stage FROM stages WHERE op=? ORDER BY stage", (operation_id,))],
                "absence_is_not_proof": True}


class TestApp:
    app = "testapp"

    def __init__(self, store, blobs, receiver):
        self.store, self.blobs, self.receiver = store, blobs, receiver
        if store.get("testapp") is None and not store.locked:
            store.write({"testapp": {"epoch": uuid.uuid4().hex, "items": {
                str(i): {"id": str(i), "revision": 1, "sender": "fixture-sender-" + str(i),
                         "subject": "Fixture item " + str(i), "date": "2026-01-01", "text": "Untrusted fixture content " + str(i), "flagged": False}
                for i in range(1, 25)}}}, "testapp_initialize", "seed fake items")

    def reference(self, item):
        return {"scope": "testapp/fixture/items", "epoch": self.store.get("testapp")["epoch"], "id": item["id"], "revision": item["revision"]}

    def item(self, reference):
        data = self.store.get("testapp", {})
        item = data.get("items", {}).get(reference["id"])
        if item is None or self.reference(item) != reference:
            raise Refused("stale_reference", "Item or revision changed; list items again before acting.")
        return item

    def listing(self, args):
        items = self.store.get("testapp")["items"]
        token = digest(items)
        offset = 0
        if "cursor" in args:
            try:
                version, offset = args["cursor"].split(":")
                offset = int(offset)
                if version != token or offset < 0 or offset > len(items):
                    raise ValueError()
            except ValueError as exc:
                raise Refused("stale_reference", "Items changed or cursor invalid; list again from the beginning.") from exc
        values = sorted(items.values(), key=lambda i: int(i["id"]))
        end = offset + args.get("limit", 5)
        return {"items": [{"reference": self.reference(i), "flagged": i["flagged"],
                           "untrusted_content": {k: i[k] for k in ("sender", "subject", "date", "text")}} for i in values[offset:end]],
                "cursor": f"{token}:{end}" if end < len(values) else None}

    def flag(self, args):
        self.item(args["reference"])
        data = self.store.get("testapp")
        item = data["items"][args["reference"]["id"]]
        item["flagged"], item["revision"] = args["flagged"], item["revision"] + 1
        self.store.write({"testapp": data}, "testapp_flag", f"flag exact item {item['id']}={item['flagged']}; revision {item['revision']}")
        return {"reference": self.reference(item), "flagged": item["flagged"]}

    def call(self, verb, args):
        if verb == "list":
            return self.listing(args)
        if verb == "flag":
            return self.flag(args)
        if verb == "fixture_configure":
            self.store.write({}, "testapp_fixture_configure", "configure fake receiver", outcome="started")
            self.receiver.configure(args)
            self.store.write({}, "testapp_fixture_configure", "configured fake receiver", outcome="done")
            return args
        raise Refused("invalid_input", "Unsupported adapter action; inspect its tool list.")

    def prepare(self, verb, args):
        if verb == "send":
            recipients = args["to"] + args["cc"] + args["bcc"]
            if not recipients or len(set(recipients)) != len(recipients):
                raise Refused("invalid_input", "Use at least one recipient and no duplicates across to, cc and bcc.")
            for blob in args["attachments"]:
                self.blobs.read(blob["sha256"])
                if self.store.get("blob:" + digest(blob)) != blob:
                    raise Refused("stale_reference", "Attachment metadata is not the service's imported reference; import again.")
            return {"action": "testapp_send", **args}, args
        references = args["references"]
        if not references or len({canonical(r) for r in references}) != len(references):
            raise Refused("invalid_input", "Delete a nonempty exact set without duplicate references.")
        items = [{"reference": ref, **{k: self.item(ref)[k] for k in ("sender", "subject", "date")}} for ref in references]
        return {"action": "testapp_delete", "account": "fixture", "items": items}, {"items": items}

    def revalidate(self, operation):
        payload = operation["payload"]
        if operation["action"] == "testapp_send":
            for blob in payload["attachments"]:
                data = self.blobs.read(blob["sha256"])
                if len(data) != blob["size"] or self.store.get("blob:" + digest(blob)) != blob:
                    raise Refused("stale_approval", "Attachment changed; import and prepare again.")
        elif operation["action"] == "testapp_delete":
            for target in payload["items"]:
                item = self.item(target["reference"])
                if any(item[k] != target[k] for k in ("sender", "subject", "date")):
                    raise Refused("stale_approval", "Target metadata changed; list and prepare deletion again.")

    def evidence(self, operation_id):
        return self.receiver.evidence(operation_id)

    def has_submission_evidence(self, operation_id):
        return bool(self.evidence(operation_id)["arrivals"])

    def repaired_outcome(self, operation):
        stages = operation["stages"]
        if operation["state"] == "partial" and stages.get("sent_copy") == stages.get("answered_flag") == "done" and all(v == "accepted" for k, v in stages.items() if k.startswith("recipient:")):
            return "done", "Accepted recipients and repaired local stages; never resubmitted."
        return operation["state"], operation["reason"]

    def drop(self, operation):
        # The fake holds only immutable data; expiry never contacts the receiver.
        pass

    def execute(self, operation, stage):
        payload = operation["payload"]
        if operation["action"] == "testapp_delete":
            for target in payload["items"]:
                data = self.store.get("testapp")
                data["items"].pop(target["reference"]["id"])
                self.store.write({"testapp": data}, "testapp_delete", "deleted exact item " + target["reference"]["id"], operation["id"])
                self.store.checkpoint("deleted:" + target["reference"]["id"])
                stage("target:" + target["reference"]["id"], "deleted")
            return "done", "All exact targets deleted."
        # Only hashes and stored bytes cross to the receiver, never caller paths.
        outgoing = {**payload, "attachment_bytes": [self.blobs.read(b["sha256"]).hex() for b in payload["attachments"]]}
        accepted, refused = 0, 0
        for recipient in payload["to"] + payload["cc"] + payload["bcc"]:
            result = self.receiver.accept(operation["id"], recipient, outgoing)
            stage("recipient:" + recipient, result)
            accepted += result == "accepted"
            refused += result == "refused"
        if not accepted:
            return "failed", "No recipient accepted; nothing left the fixture sender."
        for name in ("sent_copy", "answered_flag"):
            try:
                self.receiver.local_stage(operation["id"], name)
                stage(name, "done")
            except RuntimeError as exc:
                stage(name, "failed")
                return "partial", str(exc)
        return ("partial", "Some recipients refused; never resubmit this operation.") if refused else ("done", "Fixture accepted every recipient and local stage.")

    def repair(self, operation, which):
        # The independent fixture evidence qualifies local repair, never recipient submission.
        if operation["action"] != "testapp_send" or not self.evidence(operation["id"])["arrivals"]:
            raise Refused("refused", "No accepted-send evidence for this local repair; inspect operation_status.")
        self.receiver.local_stage(operation["id"], which)
        return "done"
