import base64
import copy
import imaplib
import logging
import sqlite3
import time
import uuid

from . import retention
from .adapters import NothingLeft, Uncertain
from .blobs import Blobs
from .boundary import Boundary
from .requests import envelope, changing, UPLOAD_CHUNK, DOWNLOAD_CHUNK
from .common import CHUNK_SIZE, FILE_LIMIT, RESULT_LIMIT, Refused, approval_input, approval_order, canonical, cleanup, digest, require_question, validate, visible, storage_refusal
from .definitions import APPS, BY_NAME, tools_for
from .storage import Store
from .results import Observations
from .paging import ordered_page
from .testapp import Receiver, TestApp
from .mail.adapter import Mail


class Engine:
    def __init__(self, state_dir, evidence_dir, ttl=900, checkpoint=lambda _: None, file_limit=FILE_LIMIT):
        self.boundary = Boundary()
        self.store = Store(state_dir, evidence_dir, checkpoint)
        self.receiver = None
        self._last_pending = {}
        try:
            self._initialize_adapters(ttl, checkpoint, file_limit)
        except BaseException as exc:
            with cleanup('engine initialization', exc):
                self.close()
            raise

    def _initialize_adapters(self, ttl, checkpoint, file_limit):
        self.blobs = Blobs(self.store.state_dir / "blobs", file_limit, self.store.ensure_writable, self.store.ledger)
        self.receiver = Receiver(self.store.evidence_dir, checkpoint, self.store.ledger)
        self.adapters = {"testapp": TestApp(self.store, self.blobs, self.receiver), "mail": Mail(self.store, self.blobs)}
        self.adapters['mail'].check_result = self.check_composition_result
        from .chrome.adapter import Chrome
        self.adapters['chrome'] = Chrome(self)
        self.ttl = ttl

    def check_composition_result(self, data):
        result = {'ok': True, 'data': data, 'pending': self.pending('mail', resolve_checks=False)}
        if len(canonical(result).encode()) > RESULT_LIMIT:
            raise Refused('result_too_large', 'Composition exceeds 49152 bytes including pending notices; use a shorter composition.')

    def close(self):
        if self.receiver is not None:
            self.receiver.db.close()
        if hasattr(self, 'adapters') and 'chrome' in self.adapters:
            self.adapters['chrome'].bridge.close()
        self.store.close()

    def operation(self, op_id, app=None):
        op = self.store.get("op:" + op_id)
        if op is None or (app and op["app"] != app):
            raise Refused("stale_reference", "Operation not found for this app; list pending or ask the owner to check the independent record.")
        return op

    def notices(self, app=None, resolve_checks=True):
        from .mail.filing import notice_page
        mail = self.adapters['mail']
        page = notice_page(self.store, app=app, checks=mail.resolve_sent_checks() if resolve_checks else mail.unresolved_sent_checks())
        if not page['items']:
            return {}
        result = {'notices': page['items']}
        if page['cursor']:
            result['notices_more'] = {'count': page['total'] - len(page['items']),
                                      'action': 'mail_filing_notices'}
        return result

    def pending(self, app=None, args=None, resolve_checks=True):
        try:
            result = self._pending(app, args, resolve_checks)
            self._last_pending[app] = copy.deepcopy(result)
            return result
        except (OSError, sqlite3.Error) as exc:
            if storage_refusal(exc) is None:
                raise
            self.store.observations.storage(exc)
            # Persistent exhaustion can prevent SQLite's rollback, so even a
            # SELECT may fail. Keep the last disclosure and newly seen warnings
            # in the reply instead of losing the entire storage-error frame.
            result = copy.deepcopy(self._last_pending.get(app, self._last_pending.get(None, {
                'items': [], 'total': 0, 'cursor': None, 'restore_required': self.store.locked})))
            result['unavailable'] = 'Live pending read failed on storage; snapshot only. Restart recovery and inspect status before any further change.'
            from .mail.filing import public_notice
            notices = {n['operation_id']: n for n in result.get('notices', [])}
            new_notices = []
            for changes, _, _ in self.store.deferred_notices.values():
                for key, value in changes.items():
                    if key.startswith('notice:') and not value.get('ack'):
                        notices[value['id']] = public_notice(self.store, value)
                        new_notices.append(value['id'])
                        self.store.observations.observe(value['id'], {'filing_warning': value['untrusted_content']})
            if notices:
                order = list(dict.fromkeys([*reversed(new_notices), *notices]))
                result['notices'] = [notices[key] for key in order[:3]]
                total = len(notices) + result.get('notices_more', {}).get('count', 0)
                if total > 3:
                    result['notices_more'] = {'count': total - 3, 'action': 'mail_filing_notices'}
            return result

    def _pending(self, app=None, args=None, resolve_checks=True):
        notices = self.notices(resolve_checks=resolve_checks)
        def rows():
            for key, op in self.store.iter_items('op:'):
                if ((app is not None and op['app'] != app) or
                        not (op['state'] in {'reserved', 'submitting', 'partial', 'unknown'} or
                             (op.get('notice') and not op.get('ack')))):
                    continue
                created = self.store.db.execute('SELECT created FROM retained WHERE k=?', (key,)).fetchone()
                yield ((created[0] if created else 0, op['id']),
                       {'operation_id': op['id'], 'app': op['app'], 'state': op['state'], 'reason': op['reason']})
        return ordered_page(rows, args, ['pending', app]) | {'restore_required': self.store.locked} | notices

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

    def background_error(self, exc):
        self.store.remember_storage(exc)
        error = self.store.storage_cause
        if error is not None:
            # Store.write/_append latch once a transaction may have started.
            # A ledger refusal before any write needs only the owner notice.
            notice_id = 'background-storage'
            notice = {'id': notice_id, 'app': 'mail', 'state': 'partial', 'ack': False,
                      'created_at': time.time_ns(), 'untrusted_content': {'reason': str(error)}}
            self.store.defer_notice(notice_id, {'notice:' + notice_id: notice},
                                    'control_maintenance', 'Background storage failure')
            logging.getLogger(__name__).error('Background maintenance: %s', error)
        else:
            logging.getLogger(__name__).error('Background maintenance failed; inspect service state.')

    def expire(self):
        try:
            self._expire()
        except Exception as exc:
            self.background_error(exc)
            raise

    def _expire(self):
        if self.store.locked or self.store.write_failed:
            return
        self.store.flush_notices()
        for key, op in self.store.iter_items("op:"):
            if op["state"] == "reserved" and time.time() >= op["expires"]:
                op.update(state="failed", reason="expired: nothing submitted", notice=True)
                self.store.write({key: op}, op["action"], "approval expired without submission", op["id"], recovery=True)
                self.adapters[op["app"]].drop(op)
        retention.expire(self)

    def reserve(self, app, verb, arguments):
        self.boundary.require()
        self.store.ensure_writable()
        self.store.require_index()
        adapter = self.adapters[app]
        question, description, payload = adapter.prepare(verb, arguments)
        if app == 'mail' and verb == 'send':
            for _, old in self.store.iter_items('op:'):
                if (old['action'] == 'mail_send' and old['generation'] == self.store.generation and
                        old['state'] == 'reserved' and time.time() < old['expires'] and old['payload'] == payload):
                    return {'approval': approval_order(old['approval']), 'state': 'reserved'}
            self.store.admit_history()
        op_id = self.store.generation + ":" + uuid.uuid4().hex
        expires = time.time() + self.ttl
        approval = approval_input(op_id, {**description, "expires_at": expires}, question)
        op = {"id": op_id, "generation": self.store.generation, "app": app, "action": app + "_" + verb,
              "input_hash": digest(approval), "approval": approval, "payload": payload, "state": "reserved",
              "expires": expires, "stages": {}, "reason": "Awaiting exact approval; nothing submitted."}
        if app == 'mail' and payload.get('composition'):
            op['sent_copy_check'] = {'state': 'open'}
        self.store.write({"op:" + op_id: op}, op["action"], "reserved " + op["action"], op_id)
        self.store.checkpoint("reserved")
        return {"approval": approval, "state": "reserved"}

    def stage(self, op_id, name, outcome):
        op = self.operation(op_id)
        if op["app"] == "mail":
            outcome = self.adapters["mail"].stage_outcome(op, name, outcome)
        op["stages"][name] = outcome
        if name == 'sent_copy' and outcome == 'done' and op.get('sent_copy_check', {}).get('state') == 'open':
            op['sent_copy_check'] = {'state': 'checked', 'clean': True}
            from .warnings import check_result
            check_result(self.store, op, 'op:' + op_id, 'sent_copies', [])
        self.store.observations.stage(op_id, name, outcome)
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
        if action.app == 'mail' and op.get('payload', {}).get('composition'):
            op['sent_copy_check'] = {'state': 'open'}
        self.store.write({"op:" + op["id"]: op}, action.name, "submitting", op["id"])
        self.store.checkpoint("submitting")
        try:
            state, reason = adapter.execute(op, lambda name, outcome: self.stage(op["id"], name, outcome))
        except NothingLeft as exc:
            self.store.observations.storage(exc.__cause__ or exc)
            state, reason = "failed", "Submission stopped before delivery; no mail submitted." if action.app == "mail" else str(exc)
        except Exception as exc:
            self.store.observations.storage(exc)
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
        result = {k: v for k, v in op.items() if k not in
                  {'payload', 'input_hash', 'attempt_ended_at', 'repair_identity_missing',
                   'sent_append_started_at', 'sent_append_ended_at', 'sent_copy_check', 'warning_checks'} and v is not None}
        if op.get('repair_identity_missing'):
            result['reason'] += ' Permanent repair stage identity is missing; another repair is refused.'
        elif (op['state'] == 'unknown' and op.get('repair_of')
              and op.get('payload', {}).get('stage') == 'sent_copy'):
            ended = op.get('attempt_ended_at')
            if ended is None:
                result['reason'] += ' Attempt end time is unavailable; absence cannot settle this repair. Ask the owner to inspect it.'
            else:
                retry = ended + Mail.SENT_QUIET_PERIOD
                result['reason'] = ('Sent-copy attempt remains uncertain. If still absent, try settlement after '
                                    + time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(retry))
                                    + f' (Unix {retry:.3f}); the earlier APPEND may still land.')
        warning = op.get('stages', {}).get('sent_copy_warning')
        if warning:
            result['reason'] += ' ' + warning
        return approval_order(result)

    def repair(self, app, args):
        old = self.operation(args["operation_id"], app)
        observation = {}
        def response(operation):
            result = {'operation': self.public_operation(operation), 'original': self.public_operation(old)}
            if 'evidence_error' in observation:
                result['evidence_error'] = observation['evidence_error']
            if observation.get('sent_copy_warning') or any(key.endswith('_storage_error') for key in observation):
                result['evidence'] = observation
            if observation:
                self.store.observations.observe(old['id'], observation)
            return result
        if old["state"] not in {"partial", "unknown", "done"}:
            raise Refused("refused", "Repair requires accepted-send evidence and a completed submission attempt; inspect status.")
        if app == 'mail' and not self.adapters[app].repair_needed(old, args['stage']):
            # Re-reading a completed stage must work even when admission is full.
            if args['stage'] == 'sent_copy':
                try:
                    self.adapters[app].repair_evidence(old, args['stage'], observation)
                except (Refused, OSError, sqlite3.Error, imaplib.IMAP4.error, Uncertain) as exc:
                    storage = self.store.observations.error or storage_refusal(exc)
                    observation['evidence_error'] = {'code': getattr(storage or exc, 'code', 'transport_error'),
                        'message': 'Sent-copy evidence is not yet checked. ' + (str(storage) if storage else
                                   'Server evidence is unavailable; inspect the recorded operation and your mail program.')}
            completed = old
            for _, op in self.store.iter_items('op:'):
                if (op.get('repair_of') == old['id'] and op.get('payload', {}).get('stage') == args['stage']
                        and op['state'] == 'done'):
                    completed = op
            return response(completed)
        if app == 'mail':
            for _, repair in self.store.iter_items('op:'):
                if (repair.get('repair_identity_missing') and repair['state'] == 'unknown'
                        and repair.get('repair_of') in {None, old['id']}):
                    raise Refused('repair_identity_missing', 'Restored unresolved repair lacks permanent stage identity; '
                                  'another repair for this send is refused. Inspect operation_status and ask the owner to recover the evidence.')
            for _, repair in self.store.iter_items('op:'):
                if (repair.get('repair_of') == old['id'] and repair.get('payload', {}).get('stage') == args['stage']
                        and repair['state'] in {'reserved', 'submitting', 'unknown'}):
                    # Repeated repair is the explicit read-then-settle path.
                    # Status remains read-only; an unreachable server adds no history.
                    try:
                        result = self.adapters[app].repair_evidence(old, args['stage'], observation)
                    except (Refused, OSError, imaplib.IMAP4.error, Uncertain):
                        return response(repair)
                    if observation.get('warning_storage_error'):
                        return response(repair)
                    if result == 'failed' and args['stage'] == 'sent_copy':
                        ended = repair.get('attempt_ended_at')
                        if (repair['state'] != 'unknown' or ended is None
                                or time.time() < ended + Mail.SENT_QUIET_PERIOD):
                            return response(repair)
                    recorded_old, recorded_repair = copy.deepcopy(old), copy.deepcopy(repair)
                    changes = {}
                    if result in {'done', 'not_needed'}:
                        old['stages'][args['stage']] = result
                        if args['stage'] == 'sent_copy' and old.get('sent_copy_check', {}).get('state') == 'open':
                            old['sent_copy_check'] = {'state': 'checked', 'clean': True, 'count': len(observation['sent'])}
                            from .warnings import check_result
                            check_result(self.store, old, 'op:' + old['id'], 'sent_copies', observation['sent'])
                        old['state'], old['reason'] = self.adapters[app].repaired_outcome(old)
                        changes['op:' + old['id']] = old
                        repair.update(state='done', reason='Read-only evidence confirms local repair; never submitted.')
                    else:
                        repair.update(state='failed', reason='Read-only check found local stage absent; a later repair may try again.')
                    changes['op:' + repair['id']] = repair
                    try:
                        self.store.write(changes, repair['action'], repair['state'], repair['id'])
                    except (Refused, OSError, sqlite3.Error) as exc:
                        storage = storage_refusal(exc)
                        if storage is None and isinstance(exc, (OSError, sqlite3.Error)):
                            storage = Refused('storage_error', 'Storage write failed during repair settlement; check the disk and operation status.')
                        if storage is None:
                            raise
                        observation['settlement_storage_error'] = {'code': storage.code, 'message': str(storage)}
                        self.store.observations.storage(storage)
                        # SQLite may have applied the prepared event before a
                        # commit-marker failure. Report the prior unresolved
                        # state until restart completes that transaction.
                        old, repair = recorded_old, recorded_repair
                    return response(repair)
            if args['stage'] == 'sent_copy':
                # An existing duplicate is useful evidence even when there is
                # no room to record a warning or start another repair attempt.
                try:
                    self.adapters[app].repair_evidence(old, args['stage'], observation)
                except (Refused, OSError, imaplib.IMAP4.error, Uncertain):
                    pass
                if observation.get('warning_storage_error'):
                    return response(old)
        self.store.admit_history(retention.RECOVERY_REQUEST, recovery=True)
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
            self.store.observations.stage(old['id'], args['stage'], result)
            old = self.operation(old['id'], app)
            old["stages"][args["stage"]] = result
            if args['stage'] == 'sent_copy' and old.get('sent_copy_check', {}).get('state') == 'open':
                old['sent_copy_check'] = {'state': 'checked', 'clean': True}
                from .warnings import check_result
                check_result(self.store, old, 'op:' + old['id'], 'sent_copies', [])
            old["state"], old["reason"] = self.adapters[app].repaired_outcome(old)
            repair["state"], repair["reason"] = "done", "Local repair completed; never submitted."
            changes = {"op:" + op_id: repair, "op:" + old["id"]: old}
        except Refused as exc:
            if self.store.observations.storage(exc):
                repair['state'], repair['reason'] = 'unknown', 'Local repair storage failed; inspect evidence, never submit.'
            else:
                repair["state"], repair["reason"] = "failed", "Local repair refused before acting; inspect operation status." if app == "mail" else "Local repair refused before acting: " + str(exc)
            changes = {"op:" + op_id: repair}
        except Exception as exc:
            self.store.observations.storage(exc)
            repair["state"], repair["reason"] = "unknown", "Local repair uncertain; inspect far-side stage evidence. Never submit."
            changes = {"op:" + op_id: repair}
        repair['attempt_ended_at'] = time.time()
        self.store.write(changes, repair["action"], repair["state"], op_id)
        return response(repair)

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
            from .definitions import RESTORE_WARNING
            return self.store.confirm_restore() | {'warning': RESTORE_WARNING}
        if name == 'control_archive':
            from .archive import archive
            return archive(self.store, args['before'], self.adapters['mail'])
        if name == "control_pending":
            return self.pending(args=args)
        if name == 'control_observations':
            from .results import observation_page
            return observation_page(self.store, args['cursor'])
        if name == "control_log":
            day = time.strftime("%Y-%m-%d", time.localtime())
            # Continuations read committed warnings: revalidating here would
            # itself add audit rows and invalidate every continuation forever.
            notices = self.notices(resolve_checks='cursor' not in args)
            def rows():
                for event in self.store.iter_audit():
                    if time.strftime("%Y-%m-%d", time.localtime(event["time"])) == day:
                        yield (event['time'], event['seq']), event
            page = ordered_page(rows, args, ['log', day])
            entries = []
            for event in page['items']:
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
            page['items'] = entries
            return page | notices
        app, verb = action.app, action.verb
        adapter = self.adapters[app]
        if verb.startswith("prepare_"):
            return self.reserve(app, verb.removeprefix("prepare_"), args)
        if app == "chrome" and verb == "submit_trusted":
            return adapter.call(verb, args)
        if action.effect in {"send", "delete"}:
            return self.submit(action, args)
        if verb == "operation_status":
            op = self.operation(args["operation_id"], app)
            result = {}
            try:
                result["evidence"] = adapter.evidence(op["id"])
                self.store.observations.observe(op['id'], result['evidence'])
                # Evidence may discover a late duplicate after a successful
                # repair. Return that warning in this very status response.
                op = self.operation(op['id'], app)
                warning = result['evidence'].get('sent_copy_warning')
                if warning:
                    op['stages']['sent_copy_warning'] = warning
            except (Refused, OSError, sqlite3.Error, imaplib.IMAP4.error, Uncertain) as exc:
                storage = self.store.observations.error or storage_refusal(exc)
                result["evidence_error"] = {"code": getattr(storage or exc, "code", "transport_error"),
                    "message": "Live evidence is not yet checked. " + (str(storage) if storage else
                               "Server evidence is unavailable; inspect the recorded operation and your mail program.")}
            result['operation'] = self.public_operation(op)
            return result
        if verb == "operation_repair":
            return self.repair(app, args)
        if verb == "operation_cancel" or app == "chrome" and verb == "drop":
            op = self.operation(args["operation_id"], app)
            if op["state"] != "reserved":
                raise Refused("refused", "Only reserved operations can be cancelled; inspect operation_status.")
            op.update(state="failed", reason="cancelled: nothing submitted", notice=True)
            self.store.write({"op:" + op["id"]: op}, name, "cancelled before submission", op["id"])
            adapter.drop(op)
            return {"operation": self.public_operation(op)}
        if verb == "notice_ack":
            # Persist this occurrence first: a delayed result must never
            # replace an acknowledgement with its earlier unacknowledged row.
            if any('notice:' + args['operation_id'] in changes
                   for changes, _, _ in self.store.deferred_notices.values()):
                self.store.flush_notices()
            notice = self.store.get("notice:" + args["operation_id"])
            if notice is None:
                from .recovery import recovery_notices
                notice = next((n for n in recovery_notices(self.store) if n['id'] == args['operation_id']), None)
            if notice and notice["app"] == app:
                if notice.get('check_only'):
                    raise Refused('refused', 'Only cancelled/expired notices may be acknowledged; unresolved work stays visible.')
                if not notice.get('ack'):
                    notice["ack"] = True
                    changes = {"notice:" + notice["id"]: notice}
                    source_key = notice.get('untrusted_content', {}).get('intent_key', '')
                    if source_key.startswith('intent:'):
                        changes[source_key] = None
                    elif source_key.startswith(('mail:filing:', 'mail:rename:')):
                        source = self.store.get(source_key)
                        if source and source.get('state') == 'started':
                            source['state'] = 'partial'
                            source['check_open'] = True
                            changes[source_key] = source
                    self.store.write(changes, name, "filing notice acknowledged")
                from .mail.filing import public_notice
                return {"notice": {**public_notice(self.store, notice), "id": notice["id"], "ack": True}}
            op = self.operation(args["operation_id"], app)
            if not op.get("notice"):
                raise Refused("refused", "Only cancelled/expired notices may be acknowledged; unresolved work stays visible.")
            if not op.get('ack'):
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
            send(connection, {"ok": True, "data": {"file": blob}, "pending": self.pending(request["app"], resolve_checks=False)}, result=True)
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
        previous_request = getattr(self.store, 'in_request', False)
        self.store.in_request = True
        try:
            self.store.observations = Observations()
            self.pending(resolve_checks=False)
            try:
                if not isinstance(request, dict) or request.get('action') not in {'control_archive', 'control_restore_confirm'}:
                    self.store.flush_notices()
            except Exception as exc:
                self.store.remember_storage(exc)
                self.store.observations.storage(exc)
            result = self._admitted_request(request, admin)
            if isinstance(request, dict) and str(request.get('action','')).startswith('chrome_'):
                chrome = self.adapters['chrome']
                if chrome.bridge.version:
                    try:
                        from .chrome.qualification import switches
                        notice = switches(chrome.qualification.record(), chrome.qualification.build, chrome.bridge.version)['notice']
                        if notice:
                            result.setdefault('pending', {})['chrome_version_notice'] = notice
                    except Exception as exc:
                        self.store.observations.storage(exc)
            return self.store.observations.finish(result, self.store)
        finally:
            self.store.in_request = previous_request

    def _admitted_request(self, request, admin=False):
        previous_recovery = self.store.recovering
        try:
            envelope(request)
            mutating = changing(request)
            if mutating:
                self.store.ensure_writable()
                self.store.recovering = retention.recovery_action(request.get('action', ''))
                if not self.store.recovering:
                    retention.expire(self)
                # Archive first exports durably, then makes room; it must also
                # work on a store already over quota from an older installation.
                if (request.get('action') not in {'control_archive', 'control_restore_confirm', 'mail_prepare_send', 'mail_operation_repair'}
                        and not request.get('action', '').endswith('_operation_cancel')
                        and not (request['method'] == 'saved' and request.get('export_id'))):
                    self.store.admit_history(retention.RECOVERY_REQUEST if self.store.recovering else retention.REQUEST_RESERVE)
            return self._request(request, admin)
        except Refused as exc:
            self.store.observations.storage(exc)
            return {'ok': False, 'error': {'code': exc.code, 'message': str(exc)}, 'pending': self.pending(resolve_checks=False)}
        except Exception as exc:
            self.store.observations.storage(exc)
            storage = storage_refusal(exc)
            if storage:
                return {'ok': False, 'error': {'code': storage.code, 'message': str(storage)}, 'pending': self.pending(resolve_checks=False)}
            return {'ok': False, 'error': {'code': 'internal_error', 'message': 'Request failed unexpectedly; inspect operation status before repeating changes.'}, 'pending': self.pending(resolve_checks=False)}
        finally:
            self.store.recovering = previous_recovery

    def _request(self, request, admin=False):
        app = None
        try:
            envelope(request)
            method = request.get("method")
            if method == "tools":
                app = request.get("app")
                if app not in APPS:
                    raise Refused("invalid_input", "Unknown app; inspect configured MCP servers.")
                data = {"tools": tools_for(app)}
            elif method == 'pending':
                # Rejection envelopes must retain warnings without entering an
                # adapter. Explicit control_pending remains the live check path.
                data = self.pending(resolve_checks=False)
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
                    self.blobs.admit(blob['size'], blob['sha256'])
                    self.store.admit_changes({'blob:' + digest(blob): blob})
                    data = {"ready": True}
                elif method == "download":
                    from . import exports
                    key = request["sha256"]
                    data_bytes = self.blobs.require_origin(key, "export")
                    export_id = request.get('export_id')
                    if export_id:
                        exports.get(self.store, export_id, app, key)
                    else:
                        export_id = exports.begin(self.store, self.blobs, app, key, len(data_bytes))
                    data = {"sha256": key, "size": len(data_bytes), 'export_id': export_id,
                            'other_holds': self.store.ledger.held - self.store.ledger.holds['export:' + export_id]}
                else:
                    changes = {}
                    if request.get('export_id'):
                        from . import exports
                        transfer = exports.get(self.store, request['export_id'], app)
                        if request['outcome'] == 'refused':
                            exports.discard_blob(self.store, self.blobs, transfer, request['export_id'])
                        changes['export:' + request['export_id']] = None
                    self.store.write(changes, app + "_file_save", "caller reported file save outcome",
                                     outcome="refused" if request.get("outcome") == "refused" else "done",
                                     untrusted_content={"save": request.get("outcome")})
                    data = {"recorded": True}
            else:
                raise Refused("invalid_input", "Unknown method or wrong socket; inspect the protocol.")
            result = {"ok": True, "data": data, "pending": self.pending(app, resolve_checks=False)}
            # Blob transfer is private framing, never a model-facing result.
            if method != "download" and len(canonical(result).encode()) > RESULT_LIMIT and method != "tools" and request.get("action") != "control_observations":
                raise Refused("result_too_large", "Result exceeds 49152 bytes; request a smaller page. Check status before repeating changes.")
            return result
        except (OSError, sqlite3.DatabaseError, imaplib.IMAP4.error, Uncertain) as exc:
            self.store.observations.storage(exc)
            storage = storage_refusal(exc)
            if storage:
                return {'ok': False, 'error': {'code': storage.code, 'message': str(storage)}, 'pending': self.pending(app, resolve_checks=False)}
            return {"ok": False, "error": {"code": "transport_error", "message": "Mail transport failed; inspect operation status before repeating changes. No automatic retry."}, "pending": self.pending(app, resolve_checks=False)}
        except (Refused, ValueError, KeyError, TypeError) as exc:
            self.store.observations.storage(exc)
            message = str(exc) if isinstance(exc, Refused) else "Invalid input or unsupported server data; inspect the tool schema and operation status."
            if app == "mail":
                message = self.adapters["mail"].transport.scrub(message)
            return {"ok": False, "error": {"code": getattr(exc, "code", "invalid_input"), "message": message}, "pending": self.pending(app, resolve_checks=False)}
        except Exception:
            return {"ok": False, "error": {"code": "internal_error", "message": "Request failed unexpectedly; inspect operation status before repeating changes."}, "pending": self.pending(app, resolve_checks=False)}
