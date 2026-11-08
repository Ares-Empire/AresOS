import base64
import imaplib
import time
import uuid

from .adapters import NothingLeft, Uncertain
from .blobs import Blobs
from .boundary import Boundary
from .requests import envelope, UPLOAD_CHUNK, DOWNLOAD_CHUNK
from .common import CHUNK_SIZE, FILE_LIMIT, RESULT_LIMIT, Refused, approval_input, approval_order, canonical, digest, require_question, validate, visible
from .definitions import APPS, BY_NAME, tools_for
from .storage import Store
from .testapp import Receiver, TestApp
from .mail.adapter import Mail


class Engine:
    def __init__(self, state_dir, evidence_dir, ttl=900, checkpoint=lambda _: None, file_limit=FILE_LIMIT):
        self.boundary = Boundary()
        self.store = Store(state_dir, evidence_dir, checkpoint)
        self.blobs = Blobs(self.store.state_dir / "blobs", file_limit, self.store.ensure_writable)
        self.receiver = Receiver(self.store.evidence_dir, checkpoint)
        self.adapters = {"testapp": TestApp(self.store, self.blobs, self.receiver), "mail": Mail(self.store, self.blobs)}
        self.ttl = ttl

    def close(self):
        self.receiver.db.close()
        self.store.close()

    def operation(self, op_id, app=None):
        op = self.store.get("op:" + op_id)
        if op is None or (app and op["app"] != app):
            raise Refused("stale_reference", "Operation not found for this app; list pending or ask the owner to check the independent record.")
        return op

    def notices(self, app=None):
        from .mail.filing import notice_page
        page = notice_page(self.store, app=app)
        if not page['items']:
            return {}
        result = {'notices': page['items']}
        if page['cursor']:
            result['notices_more'] = {'count': page['total'] - len(page['items']),
                                      'action': 'mail_filing_notices'}
        return result

    def pending(self, app=None, args=None):
        values = [{"operation_id": op["id"], "app": op["app"], "state": op["state"],
                   "description": op["approval"]["description"], "reason": op["reason"]}
                  for _, op in self.store.items("op:") if (app is None or op["app"] == app) and
                  (op["state"] in {"reserved", "submitting", "partial", "unknown"} or (op.get("notice") and not op.get("ack")))]
        # Notifications stay compact; operation_status has the full description, never a truncated approval.
        summaries = [{k: v for k, v in op.items() if k != "description"} for op in values]
        notices = self.notices(app)
        return self.page(summaries, args or {}, "pending") | {"restore_required": self.store.locked} | notices

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
        if self.store.locked or self.store.write_failed:
            return
        for key, op in self.store.items("op:"):
            if op["state"] == "reserved" and time.time() >= op["expires"]:
                op.update(state="failed", reason="expired: nothing submitted", notice=True)
                self.store.write({key: op}, op["action"], "approval expired without submission", op["id"])
                self.adapters[op["app"]].drop(op)

    def reserve(self, app, verb, arguments):
        self.boundary.require()
        self.store.ensure_writable()
        adapter = self.adapters[app]
        question, description, payload = adapter.prepare(verb, arguments)
        op_id = self.store.generation + ":" + uuid.uuid4().hex
        expires = time.time() + self.ttl
        approval = approval_input(op_id, {**description, "expires_at": expires}, question)
        op = {"id": op_id, "generation": self.store.generation, "app": app, "action": app + "_" + verb,
              "input_hash": digest(approval), "approval": approval, "payload": payload, "state": "reserved",
              "expires": expires, "stages": {}, "reason": "Awaiting exact approval; nothing submitted."}
        self.store.write({"op:" + op_id: op}, op["action"], "reserved " + op["action"], op_id)
        self.store.checkpoint("reserved")
        return {"approval": approval, "state": "reserved"}

    def stage(self, op_id, name, outcome):
        op = self.operation(op_id)
        if op["app"] == "mail":
            outcome = self.adapters["mail"].stage_outcome(op, name, outcome)
        op["stages"][name] = outcome
        if op["app"] == "mail":
            self.store.write({"op:" + op_id: op}, op["action"], "Mail operation stage recorded", op_id,
                             untrusted_content={"stage": name, "outcome": outcome})
        else:
            self.store.write({"op:" + op_id: op}, op["action"], "stage " + visible(name) + ": " + outcome, op_id)
        self.store.checkpoint("stage:" + name)

    def submit(self, action, args):
        self.boundary.require()
        self.store.ensure_writable()
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
            self.adapters[op["app"]].drop(op)
            return {"operation": self.public_operation(op)}
        adapter = self.adapters[action.app]
        adapter.revalidate(op)
        if adapter.has_submission_evidence(op["id"]):
            op.update(state="unknown", reason="Far-side submission evidence already exists; inspect evidence, never submit again.")
            op["stages"]["preflight_evidence"] = "present"
            # Persist the positive finding before another adapter call can fail.
            self.store.write({"op:" + op["id"]: op}, action.name, "existing submission evidence: unknown", op["id"])
            op = self.operation(op["id"])
            op["stages"]["preflight_evidence"] = adapter.evidence(op["id"])
            self.store.write({"op:" + op["id"]: op}, action.name, "record preflight evidence", op["id"])
            raise Refused("refused", "Far-side evidence already exists; inspect status, never submit again.")
        self.store.checkpoint("revalidated")
        if time.time() >= op["expires"]:
            op.update(state="failed", reason="expired: nothing submitted", notice=True)
            self.store.write({"op:" + op["id"]: op}, action.name, "approval expired after adapter checks", op["id"])
            adapter.drop(op)
            return {"operation": self.public_operation(op)}
        op["state"], op["reason"] = "submitting", "Durably submitting; do not cancel or retry."
        self.store.write({"op:" + op["id"]: op}, action.name, "submitting", op["id"])
        self.store.checkpoint("submitting")
        try:
            state, reason = adapter.execute(op, lambda name, outcome: self.stage(op["id"], name, outcome))
        except NothingLeft as exc:
            state, reason = "failed", "Submission stopped before delivery; no mail submitted." if action.app == "mail" else str(exc)
        except Exception as exc:
            # Unqualified adapter errors cannot prove that the far side did nothing.
            state, reason = "unknown", "Submission outcome uncertain; inspect evidence, never retry."
        if action.app == "mail":
            reason = self.adapters["mail"].transport.scrub(reason)
        op = self.operation(op["id"])
        op["state"], op["reason"] = state, reason
        self.store.checkpoint("before_outcome")
        self.store.write({"op:" + op["id"]: op}, action.name, state, op["id"])
        self.store.checkpoint("outcome")
        return {"operation": self.public_operation(op)}

    def public_operation(self, op):
        return approval_order({k: v for k, v in op.items() if k not in {"payload", "input_hash"}})

    def repair(self, app, args):
        old = self.operation(args["operation_id"], app)
        if old["state"] not in {"partial", "unknown", "done"}:
            raise Refused("refused", "Repair requires accepted-send evidence and a completed submission attempt; inspect status.")
        op_id = self.store.generation + ":" + uuid.uuid4().hex
        description = {"repair_of": old["id"], "stage": args["stage"]}
        approval = approval_input(op_id, description, self.adapters[app].question("operation_repair", description))
        repair = {"id": op_id, "generation": self.store.generation, "app": app, "action": app + "_operation_repair",
                  "approval": approval, "input_hash": digest(args), "payload": args,
                  "state": "reserved", "stages": {}, "reason": "Reserved local repair only.", "expires": time.time() + self.ttl,
                  "repair_of": old["id"]}
        self.store.write({"op:" + op_id: repair}, repair["action"], "reserved local repair of " + old["id"], op_id)
        repair.update(state="submitting", reason="Repairing local stage only.")
        self.store.write({"op:" + op_id: repair}, repair["action"], "local repair of " + old["id"], op_id)
        try:
            result = self.adapters[app].repair(old, args["stage"])
            old["stages"][args["stage"]] = result
            old["state"], old["reason"] = self.adapters[app].repaired_outcome(old)
            repair["state"], repair["reason"] = "done", "Local repair completed; never submitted."
            changes = {"op:" + op_id: repair, "op:" + old["id"]: old}
        except Refused as exc:
            repair["state"], repair["reason"] = "failed", "Local repair refused before acting; inspect operation status." if app == "mail" else "Local repair refused before acting: " + str(exc)
            changes = {"op:" + op_id: repair}
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
        if action.effect in {"send", "delete"}:
            require_question(args)
        validate(args, action.input)
        if action.effect != 'read':
            self.store.ensure_writable()
        if self.store.locked and name != "control_restore_confirm":
            raise Refused("restore_required", "Older log refused; owner must confirm restore before any app access.")
        if name == "control_restore_confirm":
            return self.store.confirm_restore()
        if name == "control_pending":
            return self.pending(args=args)
        if name == "control_log":
            day = time.strftime("%Y-%m-%d", time.localtime())
            entries = []
            for event in self.store.audit():
                if time.strftime("%Y-%m-%d", time.localtime(event["time"])) != day:
                    continue
                entry = {k: event[k] for k in ("seq", "time", "action", "summary", "outcome", "operation_id")}
                if event["action"].startswith("mail_"):
                    # Historical Mail summaries may predate structured marking.
                    entry["summary"] = "Mail audit event"
                    content = event.get("untrusted_content", {})
                    if event["action"] in {"mail_move", "mail_copy"}:
                        from .mail.filing import audit_content
                        content = audit_content(content)
                    entry["untrusted_content"] = {"summary": visible(event["summary"]), **content}
                elif "untrusted_content" in event:
                    entry["untrusted_content"] = event["untrusted_content"]
                entries.append(entry)
            notices = self.notices()
            return self.page(entries, args, "log:" + day) | notices
        app, verb = action.app, action.verb
        adapter = self.adapters[app]
        if verb.startswith("prepare_"):
            return self.reserve(app, verb.removeprefix("prepare_"), args)
        if action.effect in {"send", "delete"}:
            return self.submit(action, args)
        if verb == "operation_status":
            op = self.operation(args["operation_id"], app)
            result = {"operation": self.public_operation(op)}
            try:
                result["evidence"] = adapter.evidence(op["id"])
            except (Refused, OSError, imaplib.IMAP4.error, Uncertain) as exc:
                result["evidence_error"] = {"code": getattr(exc, "code", "transport_error"),
                                            "message": "Live evidence unavailable; recorded operation is unchanged."}
            return result
        if verb == "operation_repair":
            return self.repair(app, args)
        if verb == "operation_cancel":
            op = self.operation(args["operation_id"], app)
            if op["state"] != "reserved":
                raise Refused("refused", "Only reserved operations can be cancelled; inspect operation_status.")
            op.update(state="failed", reason="cancelled: nothing submitted", notice=True)
            self.store.write({"op:" + op["id"]: op}, name, "cancelled before submission", op["id"])
            adapter.drop(op)
            return {"operation": self.public_operation(op)}
        if verb == "notice_ack":
            notice = self.store.get("notice:" + args["operation_id"])
            if notice and notice["app"] == app:
                notice["ack"] = True
                self.store.write({"notice:" + notice["id"]: notice}, name, "filing notice acknowledged")
                from .mail.filing import public_notice
                return {"notice": {**public_notice(self.store, notice), "id": notice["id"], "ack": True}}
            op = self.operation(args["operation_id"], app)
            if not op.get("notice"):
                raise Refused("refused", "Only cancelled/expired notices may be acknowledged; unresolved work stays visible.")
            op["ack"] = True
            self.store.write({"op:" + op["id"]: op}, name, "notice acknowledged", op["id"])
            return {"operation": self.public_operation(op)}
        if verb in {"file_import", "file_save"}:
            raise Refused("proxy_required", "File transfer must run on the caller side through aresos-mcp or aresos; the service never opens home paths.")
        return adapter.call(verb, args)

    def transfer(self, connection, request):
        from .protocol import receive, send
        result = self.request(request)
        send(connection, result, result=True)
        if not result["ok"]:
            return
        offset = 0
        if request["method"] == "upload":
            blob = request["file"]

            def chunks():
                nonlocal offset
                while True:
                    frame = receive(connection)
                    validate(frame, UPLOAD_CHUNK, 'upload chunk')
                    if type(frame) is not dict or type(frame.get("offset")) is not int or frame["offset"] != offset:
                        raise Refused("invalid_input", "Upload chunks are out of order; import refused.")
                    if frame == {"end": True, "offset": offset}:
                        return
                    if set(frame) != {"offset", "bytes"} or type(frame["bytes"]) is not str:
                        raise Refused("invalid_input", "Malformed upload chunk; import refused.")
                    data = base64.b64decode(frame["bytes"], validate=True)
                    if not 0 < len(data) <= CHUNK_SIZE:
                        raise Refused("invalid_input", "Use nonempty upload chunks of at most 1 MiB.")
                    offset += len(data)
                    yield data
                    send(connection, {"ok": True, "data": {"offset": offset}}, result=True)

            self.blobs.put_stream(chunks(), blob["size"], blob["sha256"], origin="caller_import")
            self.store.write({"blob:" + digest(blob): blob}, request["app"] + "_file_import", "import immutable blob " + blob["sha256"])
            send(connection, {"ok": True, "data": {"file": blob}, "pending": self.pending(request["app"])}, result=True)
        else:
            data = self.blobs.require_origin(request["sha256"], "export")
            while True:
                frame = receive(connection)
                validate(frame, DOWNLOAD_CHUNK, 'download chunk')
                if frame == {"end": True, "offset": offset} and offset == len(data):
                    send(connection, {"ok": True, "data": {"complete": True}}, result=True)
                    return
                if frame != {"offset": offset} or offset == len(data):
                    raise Refused("invalid_input", "Download chunks are out of order or incomplete; save refused.")
                chunk = data[offset:offset + CHUNK_SIZE]
                send(connection, {"ok": True, "data": {"offset": offset, "bytes": base64.b64encode(chunk).decode()}}, result=True)
                offset += len(chunk)

    def request(self, request, admin=False):
        app = None
        try:
            envelope(request)
            method = request.get("method")
            if method == "tools":
                app = request.get("app")
                if app not in APPS:
                    raise Refused("invalid_input", "Unknown app; inspect configured MCP servers.")
                data = {"tools": tools_for(app)}
            elif method == "mail_account_add" and admin:
                self.store.ensure_writable()
                from .mail.onboarding import onboard
                from .mail.definitions import ACCOUNT_CONFIG
                validate(request["arguments"], ACCOUNT_CONFIG)
                if self.store.locked:
                    raise Refused("restore_required", "Confirm restore before account setup.")
                app = "mail"
                try:
                    data = onboard(self, request["arguments"], request["password"])
                finally:
                    self.adapters["mail"].onboarding_id = None
            elif method == "call":
                name, arguments = request.get("action"), request.get("arguments")
                app = BY_NAME[name].app if name in BY_NAME else None
                data = self.dispatch(name, arguments, admin)
            elif method in {"upload", "download", "saved"} and not admin:
                self.store.ensure_writable()
                if self.store.locked:
                    raise Refused("restore_required", "Confirm restored log before transferring files.")
                app = request.get("app")
                if app not in self.adapters:
                    raise Refused("invalid_input", "Unknown file-transfer app.")
                if method == "upload":
                    from .definitions import BLOB
                    blob = request["file"]
                    validate(blob, BLOB)
                    if blob["size"] > self.blobs.limit:
                        raise Refused("file_refused", "File exceeds the service's configured per-file limit.")
                    if "bytes" in request:
                        raise Refused("invalid_input", "Use an offset-checked chunk stream for uploads.")
                    data = {"ready": True}
                elif method == "download":
                    key = request["sha256"]
                    data_bytes = self.blobs.require_origin(key, "export")
                    data = {"sha256": key, "size": len(data_bytes)}
                    self.store.write({}, app + "_file_save", "export blob " + key + "; caller must report save outcome", outcome="started")
                else:
                    self.store.write({}, app + "_file_save", "caller reported file save outcome",
                                     outcome="refused" if request.get("outcome") == "refused" else "done",
                                     untrusted_content={"save": request.get("outcome")})
                    data = {"recorded": True}
            else:
                raise Refused("invalid_input", "Unknown method or wrong socket; inspect the protocol.")
            result = {"ok": True, "data": data, "pending": self.pending(app)}
            # Blob transfer is private framing, never a model-facing result.
            if method != "download" and len(canonical(result).encode()) > RESULT_LIMIT and method != "tools":
                raise Refused("result_too_large", "Result exceeds 49152 bytes; request a smaller page. Check status before repeating changes.")
            return result
        except (OSError, imaplib.IMAP4.error, Uncertain):
            return {"ok": False, "error": {"code": "transport_error", "message": "Mail transport failed; inspect operation status before repeating changes. No automatic retry."}, "pending": self.pending(app)}
        except (Refused, ValueError, KeyError, TypeError) as exc:
            message = str(exc) if isinstance(exc, Refused) else "Invalid input or unsupported server data; inspect the tool schema and operation status."
            if app == "mail":
                message = self.adapters["mail"].transport.scrub(message)
            return {"ok": False, "error": {"code": getattr(exc, "code", "invalid_input"), "message": message}, "pending": self.pending(app)}
