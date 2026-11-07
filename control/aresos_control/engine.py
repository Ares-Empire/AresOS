import base64
import time
import uuid

from .adapters import NothingLeft, Uncertain
from .blobs import Blobs
from .common import RESULT_LIMIT, Refused, approval_input, canonical, digest, sha256, validate, visible
from .definitions import APPS, BY_NAME, tools_for
from .storage import Store
from .testapp import Receiver, TestApp


class Engine:
    def __init__(self, state_dir, evidence_dir, ttl=120, checkpoint=lambda _: None):
        self.store = Store(state_dir, evidence_dir, checkpoint)
        self.blobs = Blobs(self.store.state_dir / "blobs")
        self.receiver = Receiver(self.store.evidence_dir, checkpoint)
        self.adapters = {"testapp": TestApp(self.store, self.blobs, self.receiver)}
        self.ttl = ttl

    def close(self):
        self.receiver.db.close()
        self.store.close()

    def operation(self, op_id, app=None):
        op = self.store.get("op:" + op_id)
        if op is None or (app and op["app"] != app):
            raise Refused("stale_reference", "Operation not found for this app; list pending or ask the owner to check the independent record.")
        return op

    def pending(self, app=None, args=None):
        values = [{"operation_id": op["id"], "app": op["app"], "state": op["state"],
                   "description": op["approval"]["description"], "reason": op["reason"]}
                  for _, op in self.store.items("op:") if (app is None or op["app"] == app) and
                  (op["state"] in {"reserved", "submitting", "partial", "unknown"} or (op.get("notice") and not op.get("ack")))]
        # Notifications stay compact; operation_status has the full description, never a truncated approval.
        summaries = [{k: v for k, v in op.items() if k != "description"} for op in values]
        return self.page(summaries, args or {}, "pending") | {"restore_required": self.store.locked}

    def page(self, values, args, scope):
        token, offset = digest([scope, values]), 0
        if "cursor" in args:
            try:
                version, offset = args["cursor"].split(":")
                offset = int(offset)
                if version != token or offset < 0 or offset > len(values):
                    raise ValueError()
            except ValueError as exc:
                raise Refused("stale_reference", "Page changed; read again without the cursor.") from exc
        end = offset + args.get("limit", 5)
        return {"items": values[offset:end], "total": len(values), "cursor": f"{token}:{end}" if end < len(values) else None}

    def expire(self):
        if self.store.locked:
            return
        for key, op in self.store.items("op:"):
            if op["state"] == "reserved" and time.time() >= op["expires"]:
                op.update(state="failed", reason="expired: nothing submitted", notice=True)
                self.store.write({key: op}, op["action"], "approval expired without submission", op["id"])

    def reserve(self, app, verb, arguments):
        adapter = self.adapters[app]
        description, payload = adapter.prepare(verb, arguments)
        op_id = self.store.generation + ":" + uuid.uuid4().hex
        expires = time.time() + self.ttl
        approval = approval_input(op_id, {**description, "expires_at": expires})
        op = {"id": op_id, "generation": self.store.generation, "app": app, "action": app + "_" + verb,
              "input_hash": digest(approval), "approval": approval, "payload": payload, "state": "reserved",
              "expires": expires, "stages": {}, "reason": "Awaiting exact approval; nothing submitted."}
        self.store.write({"op:" + op_id: op}, op["action"], "reserved " + op["action"], op_id)
        self.store.checkpoint("reserved")
        return {"approval": approval, "state": "reserved"}

    def stage(self, op_id, name, outcome):
        op = self.operation(op_id)
        op["stages"][name] = outcome
        self.store.write({"op:" + op_id: op}, op["action"], "stage " + visible(name) + ": " + outcome, op_id)
        self.store.checkpoint("stage:" + name)

    def submit(self, action, args):
        op = self.operation(args["operation_id"], action.app)
        if op["generation"] != self.store.generation:
            raise Refused("refused", "Earlier-generation approval invalidated by restore; status and evidence remain readable. Never resubmit.")
        if action.name != op["action"] or digest(args) != op["input_hash"] or args != op["approval"]:
            raise Refused("stale_approval", "Id reuse with different input refused; use exactly the service's approval, or prepare anew.")
        if op["state"] != "reserved":
            return {"operation": self.public_operation(op)}
        if time.time() >= op["expires"]:
            op.update(state="failed", reason="expired: nothing submitted", notice=True)
            self.store.write({"op:" + op["id"]: op}, action.name, "approval expired", op["id"])
            return {"operation": self.public_operation(op)}
        adapter = self.adapters[action.app]
        adapter.revalidate(op)
        if adapter.has_submission_evidence(op["id"]):
            raise Refused("refused", "Far-side evidence already exists; inspect status, never submit again.")
        self.store.checkpoint("revalidated")
        op["state"], op["reason"] = "submitting", "Durably submitting; do not cancel or retry."
        self.store.write({"op:" + op["id"]: op}, action.name, "submitting", op["id"])
        self.store.checkpoint("submitting")
        try:
            state, reason = adapter.execute(op, lambda name, outcome: self.stage(op["id"], name, outcome))
        except NothingLeft as exc:
            state, reason = "failed", str(exc)
        except Exception as exc:
            # Unqualified adapter errors cannot prove that the far side did nothing.
            state, reason = "unknown", "Submission outcome uncertain; inspect evidence, never retry. " + str(exc)
        op = self.operation(op["id"])
        op["state"], op["reason"] = state, reason
        self.store.checkpoint("before_outcome")
        self.store.write({"op:" + op["id"]: op}, action.name, state, op["id"])
        self.store.checkpoint("outcome")
        return {"operation": self.public_operation(op)}

    def public_operation(self, op):
        return {k: v for k, v in op.items() if k not in {"payload", "input_hash"}}

    def repair(self, app, args):
        old = self.operation(args["operation_id"], app)
        if old["state"] not in {"partial", "unknown", "done"}:
            raise Refused("refused", "Repair requires accepted-send evidence and a completed submission attempt; inspect status.")
        op_id = self.store.generation + ":" + uuid.uuid4().hex
        repair = {"id": op_id, "generation": self.store.generation, "app": app, "action": app + "_operation_repair",
                  "approval": {"description": {"repair_of": old["id"], "stage": args["stage"]}}, "payload": {},
                  "state": "submitting", "stages": {}, "reason": "Repairing local stage only.", "expires": 0,
                  "repair_of": old["id"]}
        self.store.write({"op:" + op_id: repair}, repair["action"], "local repair of " + old["id"], op_id)
        try:
            result = self.adapters[app].repair(old, args["stage"])
            old["stages"][args["stage"]] = result
            old["state"], old["reason"] = self.adapters[app].repaired_outcome(old)
            repair["state"], repair["reason"] = "done", "Local repair completed; never submitted."
            changes = {"op:" + op_id: repair, "op:" + old["id"]: old}
        except Exception:
            repair["state"], repair["reason"] = "unknown", "Local repair uncertain; inspect far-side stage evidence. Never submit."
            changes = {"op:" + op_id: repair}
        self.store.write(changes, repair["action"], repair["state"], op_id)
        return {"operation": self.public_operation(repair), "original": self.public_operation(old)}

    def dispatch(self, name, args, admin=False):
        action = BY_NAME.get(name)
        if action is None:
            raise Refused("invalid_input", "Unknown action; inspect the tool list.")
        if action.owner_only and not admin:
            raise Refused("permission_denied", "Owner-only action requires sudo aresos admin over admin.sock.")
        if admin and not action.owner_only:
            raise Refused("permission_denied", "Use the owner's act.sock for ordinary app actions.")
        validate(args, action.input)
        if self.store.locked and name != "control_restore_confirm":
            raise Refused("restore_required", "Older log refused; owner must confirm restore before any app access.")
        if name == "control_restore_confirm":
            return self.store.confirm_restore()
        if name == "control_pending":
            return self.pending(args=args)
        if name == "control_log":
            day = time.strftime("%Y-%m-%d", time.localtime())
            entries = [{k: event[k] for k in ("seq", "time", "action", "summary", "outcome", "operation_id")} for event in self.store.events
                       if time.strftime("%Y-%m-%d", time.localtime(event["time"])) == day]
            return self.page(entries, args, "log:" + day)
        app, verb = action.app, action.verb
        adapter = self.adapters[app]
        if verb.startswith("prepare_"):
            return self.reserve(app, verb.removeprefix("prepare_"), args)
        if action.effect in {"send", "delete"}:
            return self.submit(action, args)
        if verb == "operation_status":
            op = self.operation(args["operation_id"], app)
            return {"operation": self.public_operation(op), "evidence": adapter.evidence(op["id"])}
        if verb == "operation_repair":
            return self.repair(app, args)
        if verb == "operation_cancel":
            op = self.operation(args["operation_id"], app)
            if op["state"] != "reserved":
                raise Refused("refused", "Only reserved operations can be cancelled; inspect operation_status.")
            op.update(state="failed", reason="cancelled: nothing submitted", notice=True)
            self.store.write({"op:" + op["id"]: op}, name, "cancelled before submission", op["id"])
            return {"operation": self.public_operation(op)}
        if verb == "notice_ack":
            op = self.operation(args["operation_id"], app)
            if not op.get("notice"):
                raise Refused("refused", "Only cancelled/expired notices may be acknowledged; unresolved work stays visible.")
            op["ack"] = True
            self.store.write({"op:" + op["id"]: op}, name, "notice acknowledged", op["id"])
            return {"operation": self.public_operation(op)}
        if verb in {"file_import", "file_save"}:
            raise Refused("proxy_required", "File transfer must run on the caller side through aresos-mcp or aresos; the service never opens home paths.")
        return adapter.call(verb, args)

    def request(self, request, admin=False):
        app = None
        try:
            if type(request) is not dict or request.get("v") != 1:
                raise Refused("invalid_input", "Use protocol version 1 and an object request.")
            method = request.get("method")
            if method == "tools":
                app = request.get("app")
                if app not in APPS:
                    raise Refused("invalid_input", "Unknown app; inspect configured MCP servers.")
                data = {"tools": tools_for(app)}
            elif method == "call":
                name, arguments = request.get("action"), request.get("arguments")
                app = BY_NAME[name].app if name in BY_NAME else None
                data = self.dispatch(name, arguments, admin)
            elif method in {"upload", "download", "saved"} and not admin:
                if self.store.locked:
                    raise Refused("restore_required", "Confirm restored log before transferring files.")
                app = request.get("app")
                if app not in self.adapters:
                    raise Refused("invalid_input", "Unknown file-transfer app.")
                if method == "upload":
                    validate(request.get("file"), {"type": "object"})
                    data_bytes = base64.b64decode(request["bytes"], validate=True)
                    blob = request["file"]
                    from .definitions import BLOB
                    validate(blob, BLOB)
                    if sha256(data_bytes) != blob["sha256"] or len(data_bytes) != blob["size"]:
                        raise Refused("stale_reference", "Transferred bytes do not match the file reference; import again.")
                    self.blobs.put(data_bytes)
                    self.store.write({"blob:" + digest(blob): blob}, app + "_file_import", "import immutable blob " + blob["sha256"])
                    data = {"file": blob}
                elif method == "download":
                    key = request["sha256"]
                    data = {"sha256": key, "bytes": base64.b64encode(self.blobs.read(key)).decode()}
                    self.store.write({}, app + "_file_save", "export blob " + key + "; caller must report save outcome", outcome="started")
                else:
                    self.store.write({}, app + "_file_save", "caller reports save " + visible(str(request.get("outcome")))[:512],
                                     outcome="refused" if request.get("outcome") == "refused" else "done")
                    data = {"recorded": True}
            else:
                raise Refused("invalid_input", "Unknown method or wrong socket; inspect the protocol.")
            result = {"ok": True, "data": data, "pending": self.pending(app)}
            # Blob transfer is private framing, never a model-facing result.
            if method != "download" and len(canonical(result).encode()) > RESULT_LIMIT and method != "tools":
                raise Refused("result_too_large", "Result exceeds 49152 bytes; request a smaller page. Check status before repeating changes.")
            return result
        except (Refused, ValueError, KeyError, TypeError) as exc:
            return {"ok": False, "error": {"code": getattr(exc, "code", "invalid_input"), "message": str(exc)}, "pending": self.pending(app)}
