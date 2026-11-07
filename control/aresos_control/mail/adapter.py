from collections import Counter
from datetime import date
from email.message import EmailMessage
from email.utils import formatdate
import http.client
import imaplib
import json
import re
import smtplib
import socket
import ssl
import time
import uuid
from urllib.parse import parse_qs, unquote, urlsplit

from ..adapters import NothingLeft, Uncertain
from ..blobs import Blobs
from ..common import Refused, canonical, digest, sha256, visible
from . import codec
from .questions import people, question
from .roles import resolve, SETUP, REQUIRED, OPTIONAL, optional_roles, recorded_optional, optional_status, check_optional, root
from .transport import Transport, folders, select, fetch, fetch_headers, uids, ok, quote, context, nonempty_refusal


class Mail:
    app = "mail"
    question = staticmethod(question)
    PAGE_CHARS = 6000
    SCAN_LIMIT = 10000

    def __init__(self, store, blobs):
        self.store, self.blobs = store, blobs
        self.transport = Transport(store.state_dir / "mail-passwords")
        self.wires = Blobs(store.state_dir / "mail-wire", 64 * 1024 * 1024)

    def account(self, account_id, ready=True):
        value = self.store.get("mail:account:" + account_id)
        if value is None or (ready and not value.get("ready") and getattr(self, "onboarding_id", None) != account_id):
            raise Refused("account_unavailable", "Account missing or onboarding incomplete; owner must inspect setup over admin.sock.")
        return value

    def public_account(self, account):
        try:
            with self.transport.imap(account) as client:
                optional = optional_status(recorded_optional(account), optional_roles(folders(client)))
        except (Refused, OSError, imaplib.IMAP4.error):
            optional = {role: {"status": "needs_setup", "reason": "Current role could not be checked. " + SETUP} for role in OPTIONAL}
        return {k: account[k] for k in ("id", "addresses", "capabilities", "smtp_capabilities", "special", "sent_policy", "safe_folder_delete", "format", "signature", "ready")} | {"optional_roles": optional, "folder_delete_reason": account.get("folder_delete_reason", "Not qualified by onboarding.")}

    def fresh_roles(self, account, client=None, names=(), needed=()):
        if client is None:
            with self.transport.imap(account) as conn:
                return self.fresh_roles(account, conn, names, needed)
        current = resolve(folders(client))
        if (any(current['special'][k] != account['special'].get(k) for k in REQUIRED)
                or any(root(current, k) != root(account, k) for k in REQUIRED)):
            raise Refused("special_folders_changed", "SPECIAL-USE roles differ from owner setup. " + SETUP)
        check_optional(account, current['optional'], names, needed)
        return current

    def read_roles(self, account, listed):
        # Reading never requires a valid role map; exclude every current/recorded root.
        view = {**account, 'protected_special': {k: list(v) for k, v in account.get('protected_special', {}).items()}}
        for role in ('trash', 'junk'):
            roots = view['protected_special'].setdefault(role, [])
            roots.extend({'folder': f['name'], 'delimiter': f['delimiter']} for f in listed
                         if ('\\' + role).casefold() in {flag.casefold() for flag in f['flags']})
            if role == 'junk':
                roots.extend(recorded_optional(account)[role])
        return view

    def authored(self, message):
        self.fresh_roles(self.account(message["reference"]["account"]), names=[message['reference']['folder']])
        # message() fetches FLAGS with BODY.PEEK for this exact, validated reference.
        return (any(flag.casefold() == "\\draft" for flag in message["flags"])
                or self.under(self.account(message["reference"]["account"]), message["reference"]["folder"], "drafts")
                or codec.has_authored_marker(codec.split_entity(message["raw"])[0]))

    def snapshot(self, account_id, selected=None, project=None, headers_only=False):
        account = self.account(account_id)
        messages, state, message_states, scanned = [], [], [], 0
        with self.transport.imap(account) as client:
            listed = folders(client)
            read_account = self.read_roles(account, listed)
            names = [f["name"] for f in listed if "\\Noselect" not in f["flags"]]
            if selected is None:
                names = [f for f in names if not self.under(read_account, f, "trash") and not self.under(read_account, f, "junk")]
            else:
                if not set(selected) <= set(names):
                    raise Refused("stale_reference", "Folder is stale, search again.")
                names = selected
            for folder in sorted(names):
                validity = select(client, folder)
                modseq = client.response("HIGHESTMODSEQ")[1] if "CONDSTORE" in client.capabilities else None
                ids = uids(client)
                scanned += len(ids)
                if scanned > self.SCAN_LIMIT:
                    raise Refused("scan_too_large", "History exceeds scan limit; search selected smaller folders or use owner's mail program.")
                for uid in ids:
                    if headers_only:
                        raw, flags, size = fetch_headers(client, uid)
                    else:
                        raw, flags = fetch(client, uid, self.wires.limit)
                        size = len(raw)
                    msg = codec.parse(raw)
                    ref = {"account": account_id, "folder": folder, "uidvalidity": validity, "uid": uid,
                           "message_id": str(msg.get("Message-ID", ""))}
                    message_states.append([ref, sha256(raw), flags, size])
                    message = {"reference": ref, "raw": raw, "msg": msg, "flags": flags, "size": size}
                    projected = project(message) if project else message
                    if projected is not None:
                        messages.append(projected)
                state.append([folder, validity, ids, [v.decode("ascii") for v in (modseq or []) if v]])
        # Includes flags and bytes, not just UIDNEXT: works without CONDSTORE/QRESYNC.
        version = digest([state, message_states])
        return messages, version

    def message(self, reference, writable=False, client=None):
        account = self.account(reference["account"])
        def read(conn):
            validity = select(conn, reference["folder"], readonly=not writable)
            if validity != reference["uidvalidity"]:
                raise Refused("stale_reference", "Folder UIDVALIDITY changed: stale, search again.")
            raw, flags = fetch(conn, reference["uid"], self.wires.limit)
            msg = codec.parse(raw)
            if str(msg.get("Message-ID", "")) != reference["message_id"]:
                raise Refused("stale_reference", "Message identity changed: stale, search again.")
            return {"reference": reference, "raw": raw, "msg": msg, "flags": flags}
        if client is not None:
            return read(client)
        with self.transport.imap(account) as conn:
            return read(conn)

    def under(self, account, name, kind):
        entry = root(account, kind)
        roots = [(entry["folder"], entry["delimiter"])]
        roots += [(v["folder"], v["delimiter"]) for v in recorded_optional(account).get(kind, [])]
        roots += [(v["folder"], v["delimiter"]) for v in account.get("protected_special", {}).get(kind, [])]
        return any(root and (name == root or (delimiter and name.startswith(root + delimiter))) for root, delimiter in roots)

    def page(self, values, args, state, scope):
        token = digest([scope, state])
        offset = 0
        if "cursor" in args:
            try:
                version, offset = args["cursor"].split(":")
                offset = int(offset)
                if version != token or not 0 <= offset <= len(values):
                    raise ValueError()
            except ValueError as exc:
                raise Refused("stale_reference", "Folder/query state is stale, search again without cursor.") from exc
        end = offset + args.get("limit", 5)
        return {"items": values[offset:end], "total": len(values), "cursor": f"{token}:{end}" if end < len(values) else None,
                "untrusted_content": True}

    def summary(self, message):
        msg = message["msg"]
        return {"reference": message["reference"], "flags": message["flags"], "size": message.get("size", len(message["raw"])),
                "untrusted_content": {"from": str(msg.get("From", "")), "to": str(msg.get("To", "")),
                  "subject": str(msg.get("Subject", "")), "date": str(msg.get("Date", "")),
                  "preview": codec.body(msg)[:160], "attachment_names": [a["name"] for a in codec.attachments(msg)]}}

    def search(self, args):
        def matches(m):
            msg = m["msg"]
            for field in ("from", "to", "subject", "text"):
                if field in args:
                    haystack = codec.body(msg) + "\n" + str(msg) if field == "text" else " ".join(str(msg.get(h, "")) for h in ("To", "Cc", "Bcc")) if field == "to" else str(msg.get(field, ""))
                    if args[field].casefold() not in haystack.casefold():
                        return False
            for arg, flag, invert in (("unread", "\\Seen", True), ("flagged", "\\Flagged", False), ("answered", "\\Answered", False)):
                if arg in args and ((flag in m["flags"]) != invert) != args[arg]:
                    return False
            if "has_attachment" in args and bool(codec.attachments(msg)) != args["has_attachment"]:
                return False
            for arg in ("since", "before"):
                if arg in args:
                    try:
                        cutoff = date.fromisoformat(args[arg])
                    except ValueError as exc:
                        raise Refused("invalid_input", "Dates must be ISO YYYY-MM-DD.") from exc
                    from datetime import datetime, timezone
                    day = datetime.fromtimestamp(codec.timestamp(msg), timezone.utc).date()
                    if (arg == "since" and day < cutoff) or (arg == "before" and day >= cutoff):
                        return False
            return True
        values, version = self.snapshot(args["account"], args.get("folders"), project=lambda m: {**self.summary(m), "_sort_date": codec.timestamp(m["msg"])} if matches(m) else None)
        values.sort(key=lambda m: (m["_sort_date"], canonical(m["reference"])), reverse=True)
        for value in values:
            value.pop("_sort_date")
        scope = {k: v for k, v in args.items() if k not in {"cursor", "limit"}}
        return self.page(values, args, version, ["search", scope])

    def unsubscribe_choices(self, msg):
        return re.findall(r"<([^<>]+)>", str(msg.get("List-Unsubscribe", "")))

    def read(self, args):
        m = self.message(args["reference"])
        msg, raw = m["msg"], m["raw"]
        part = args.get("part", "body")
        if part == "source":
            text = raw.decode("latin1")
        elif part == "body":
            text = codec.body(msg)
        else:
            p = codec.parts(msg).get(part)
            if p is None or p.get_content_maintype() != "text":
                raise Refused("invalid_input", "Part is missing or binary; use attachment_save for decoded bytes.")
            text = codec.text_part(p)
        token = digest([args["reference"], sha256(raw), m["flags"], part])
        offset = args.get("offset", 0)
        if (offset and args.get("cursor") != token) or ("cursor" in args and args["cursor"] != token):
            raise Refused("stale_reference", "Mail/page state is stale, search again.")
        if offset > len(text):
            raise Refused("invalid_input", "Offset exceeds text length; read from zero.")
        end = min(offset + self.PAGE_CHARS, len(text))
        while len(canonical(text[offset:end]).encode()) > 16384:
            end = offset + max(1, (end - offset) // 2)
        headers = {h: str(msg.get(h, "")) for h in ("From", "To", "Cc", "Subject", "Date", "Message-ID", "Reply-To", "In-Reply-To", "References", "List-Unsubscribe", "List-Unsubscribe-Post")}
        return {"reference": args["reference"], "flags": m["flags"], "untrusted_content": {"headers": headers, "text": text[offset:end], "attachments": codec.attachments(msg), "unsubscribe": self.unsubscribe_choices(msg)},
                "part": part, "offset": offset, "next_offset": end if end < len(text) else None,
                "cursor": token if end < len(text) else None, "total_characters": len(text), "source_sha256": sha256(raw),
                "thread_reference": args["reference"], "source_encoding": "latin1 byte mapping" if part == "source" else None}

    def thread(self, args):
        seed = self.message(args["reference"])
        account = self.account(args["reference"]["account"])
        with self.transport.imap(account) as client:
            read_account = self.read_roles(account, folders(client))
        if self.under(read_account, args['reference']['folder'], 'trash'):
            raise Refused("refused", "Threads exclude Trash/Junk; read this mail directly or move it back first.")
        if self.under(read_account, args['reference']['folder'], 'junk'):
            return self.page([], args, digest([args['reference'], read_account]), ['thread', args['reference']])
        messages, version = self.snapshot(args["reference"]["account"], headers_only=True)
        def ids(m):
            return set(codec.message_ids(" ".join(str(m["msg"].get(h, "")) for h in ("Message-ID", "In-Reply-To", "References"))))
        connected, keys = [seed], ids(seed)
        selected = {canonical(seed["reference"])}
        changed = True
        while changed:
            changed = False
            for m in messages:
                key = canonical(m["reference"])
                if key not in selected and ids(m) & keys:
                    connected.append(m)
                    selected.add(key)
                    keys |= ids(m)
                    changed = True
        counts = Counter(m["reference"]["message_id"] for m in connected if m["reference"]["message_id"])
        values = [{**self.summary(m), "duplicate_message_id": bool(m["reference"]["message_id"] and counts[m["reference"]["message_id"]] > 1),
                   "internal_thread_id": digest(m["reference"]) if not m["reference"]["message_id"] else None}
                  for m in sorted(connected, key=lambda m: (codec.timestamp(m["msg"]), canonical(m["reference"])))]
        return self.page(values, args, version, ["thread", args["reference"]])

    def contacts(self, args):
        account = self.account(args["account"])
        messages, version = self.snapshot(args["account"], headers_only=True)
        own = {codec.mailbox(x).casefold() for x in account["addresses"]}
        result = {}
        for m in messages:
            msg = m["msg"]
            sent = any(codec.mailbox(x).casefold() in own for x in codec.addresses(msg, "From"))
            for value in codec.addresses(msg, *(('To', 'Cc', 'Bcc') if sent else ('From', 'Reply-To'))):
                addr = codec.mailbox(value)
                if addr.casefold() not in own and args.get("text", "").casefold() in value.casefold():
                    result[addr.casefold()] = {"untrusted_content": {"address": addr, "display": value}}
        return self.page([result[k] for k in sorted(result)], args, version, ["contacts", args["account"], args.get("text", "")])

    def attachment(self, args, outgoing=False):
        m = self.message(args["reference"])
        if self.authored(m):
            reason = codec.DRAFT_ATTACHMENT_REASON if outgoing else 'Draft parts and source cannot be saved by Claude; the owner saves draft attachments in his mail program, or Claude sends the draft itself with mode=draft.'
            raise Refused("file_refused", reason)
        if args["part"] == "source":
            data, name, content_type = m["raw"], "message.eml", "message/rfc822"
        else:
            part = codec.parts(m["msg"]).get(args["part"])
            if part is None:
                raise Refused("stale_reference", "MIME part is stale, read again.")
            data, name, content_type = codec.decoded(part), part.get_filename() or "attachment", part.get_content_type()
        texts, mail_source = [], args["part"] == "source"
        selected = "1" if mail_source else args["part"]
        if not outgoing:
            raw, _, _, ancestor_authored, default_type = codec.source_part(m["raw"], selected)
            try:
                codec.rebuild(raw, ancestor_authored, default_type)
            except Refused as exc:
                if codec.DRAFT_ATTACHMENT_REASON in str(exc):
                    raise Refused("file_refused", 'Draft parts and source cannot be saved by Claude; the owner saves draft attachments in his mail program, or Claude sends the draft itself with mode=draft.') from exc
                raise
        if outgoing:
            selected = "1" if mail_source else args["part"]
            raw, headers, payload, ancestor_authored, default_type = codec.source_part(m["raw"], selected)
            authored = self.authored(m) or ancestor_authored
            content_type = "message/rfc822" if mail_source else headers.get_content_type()
            mail_source = (mail_source or headers.get_content_maintype() in {"message", "multipart"}
                           or name.lower().endswith((".eml", ".msg"))
                           or (headers.get_content_maintype() != "text" and codec.possible_entity(codec._transfer(headers, payload))))
            clean, texts = codec.rebuild(raw, authored, default_type)
            clean_headers, clean_payload = codec.entity(clean, default_type)
            data = clean if args["part"] == "source" or headers.get_content_maintype() in {"message", "multipart"} else codec._transfer(clean_headers, clean_payload)
        item = {"sha256": self.blobs.put(data, origin="composition_part" if outgoing else "export"), "size": len(data), "name": name, "type": content_type,
                "source": {"reference": args["reference"], "part": args["part"]}}
        if outgoing and mail_source:
            item["transformation"] = "Attached mail rebuilt with only the listed headers; Bcc and Resent-Bcc removed recursively."
            item["allowed_message_headers"] = sorted(codec.MESSAGE_HEADERS)
            item["allowed_mime_headers"] = sorted(codec.MIME_HEADERS)
        if texts:
            item["authored_text"] = texts
            if authored:
                item["authored"] = True
        return data, item

    def composition(self, args):
        comp = self.store.get("mail:composition:" + args["composition_id"])
        if comp is None or comp["hash"] != args["composition_hash"] or digest(comp["mail"]) != comp["hash"]:
            raise Refused("stale_approval", "Composition changed or missing; compose again, never amend its approval.")
        self.account(comp["mail"]["account"])
        for item in comp["mail"]["attachments"] + comp["mail"]["generated_parts"]:
            data = self.blobs.read(item["sha256"])
            if len(data) != item["size"]:
                raise Refused("stale_approval", "Attachment or quote changed; compose again.")
        return comp

    def compose(self, args):
        account = self.account(args["account"])
        self.fresh_roles(account, names=[args['reference']['folder']] if 'reference' in args else [])
        mode = args.get("mode", "new")
        original = None
        if mode != "new":
            if "reference" not in args or args["reference"]["account"] != account["id"]:
                raise Refused("invalid_input", "Reply/forward/draft needs a reference in the same account.")
            original = self.message(args["reference"])
        elif "reference" in args:
            raise Refused("invalid_input", "New mail has no original reference; choose reply/forward/draft explicitly.")
        utf8 = "smtputf8" in account["smtp_capabilities"]
        def normal(values, derived=False):
            return [codec.address(v, utf8, authored=not derived, normalize=True) for v in values]
        own = {codec.mailbox(v).casefold() for v in account["addresses"]}
        sender = codec.address(args.get("from", account["addresses"][0]), utf8, normalize=True)
        if codec.mailbox(sender).casefold() not in own:
            raise Refused("invalid_input", "From must be a configured owner alias.")
        to, cc, bcc = args.get("to", []), args.get("cc", []), args.get("bcc", [])
        subject, reply_ids, generated = args.get("subject", ""), [], []
        attachment_refs = []
        if original:
            msg = original["msg"]
            subject = args.get("subject", str(msg.get("Subject", "")))
            if mode in {"reply", "reply_all"}:
                sent_by_owner = any(codec.mailbox(v).casefold() in own for v in codec.addresses(msg, "From"))
                derived_to = codec.addresses(msg, "To") if sent_by_owner else codec.addresses(msg, "Reply-To") or codec.addresses(msg, "From")
                derived_cc = codec.addresses(msg, "Cc") if sent_by_owner else (codec.addresses(msg, "To", "Cc") if mode == "reply_all" else [])
                if "to" in args or "cc" in args:
                    raise Refused("invalid_input", "Replies derive To/Cc from the original; use new mail to choose different recipients.")
                to, cc = derived_to, derived_cc
                to = [v for v in to if codec.mailbox(v).casefold() not in own]
                cc = [v for v in cc if codec.mailbox(v).casefold() not in own]
                if not subject.casefold().startswith("re:"):
                    subject = "Re: " + subject
                reply_ids = codec.message_ids(msg.get("Message-ID"))
                quote_text = "\n\n" + str(msg.get("From", "")) + " — " + str(msg.get("Date", "")) + ":\n" + "\n".join("> " + line for line in codec.body(msg).splitlines())
            elif mode == "forward":
                if not subject.casefold().startswith("fwd:"):
                    subject = "Fwd: " + subject
                if args.get("forward_as", "inline") == "attachment":
                    _, att = self.attachment({"reference": original["reference"], "part": "source"}, outgoing=True)
                    att["name"] = "forward.eml"
                    attachment_refs.append(att)
                    quote_text = ""
                else:
                    quote_text = "\n\n---------- Forwarded mail ----------\n" + "\n".join(h + ": " + str(msg.get(h, "")) for h in ("From", "Date", "Subject", "To", "Cc")) + "\n\n" + codec.body(msg)
                    for item in codec.attachments(msg):
                        _, att = self.attachment({"reference": original["reference"], "part": item["part"]}, outgoing=True)
                        attachment_refs.append(att)
            else:
                if not self.authored(original):
                    raise Refused("invalid_input", "mode=draft requires the draft marker, \\Draft flag or SPECIAL-USE Drafts.")
                to = args.get("to", codec.addresses(msg, "To"))
                cc = args.get("cc", codec.addresses(msg, "Cc"))
                bcc = args.get("bcc", codec.addresses(msg, "Bcc"))
                quote_text = ""
                if "text" not in args:
                    data = codec.body(msg).encode("utf8")
                    generated.append({"kind":"draft_body", "source":original["reference"], "sha256":self.blobs.put(data, origin="draft_body"), "size":len(data), "text":data.decode("utf8")})
                    html_part = msg.get_body(preferencelist=("html",))
                    if html_part is not None:
                        html_data = codec.decoded(html_part)
                        try:
                            html_data = html_data.decode(html_part.get_content_charset() or "utf8","replace").encode("utf8")
                        except LookupError:
                            html_data = html_data.decode("utf8","replace").encode("utf8")
                        html_info = {"kind":"draft_html", "source":original["reference"], "sha256":self.blobs.put(html_data, origin="draft_html"), "size":len(html_data)}
                        readable = codec.html_text(html_data.decode("utf8"))
                        if readable.strip() != data.decode("utf8").strip():
                            html_info["text"] = readable
                        generated.append(html_info)
                for item in codec.attachments(msg):
                    _, att = self.attachment({"reference": original["reference"], "part": item["part"]}, outgoing=True)
                    attachment_refs.append(att)
            if quote_text:
                data = quote_text.encode("utf8")
                part = {"kind": "quoted_mail", "source": original["reference"], "sha256": self.blobs.put(data, origin="quoted_mail"), "size": len(data)}
                if self.authored(original):
                    part["text"] = quote_text
                generated.append(part)
        subject = codec.clean_header(subject.strip(" \t"), authored="subject" in args or not original)
        seen = set()
        def unique(values, derived=False):
            out = []
            for value in normal(values, derived):
                key = codec.mailbox(value).casefold()
                if key not in seen:
                    out.append(value)
                    seen.add(key)
            return out
        to, cc, bcc = (unique(values, derived=bool(original) and ((mode in {"reply", "reply_all"} and key in {"to", "cc"}) or (mode == "draft" and key not in args)))
                       for key, values in (("to", to), ("cc", cc), ("bcc", bcc)))
        for item in args.get("attachments", []):
            if "reference" in item:
                _, att = self.attachment(item, outgoing=True)
            else:
                if "path" in item:
                    raise Refused("proxy_required", "Local attachments must be imported by the caller-side proxy.")
                if self.store.get("blob:" + digest(item)) != item:
                    raise Refused("stale_reference", "Not an imported caller blob; attach a path through the proxy.")
                if "last_changed" not in item:
                    raise Refused("proxy_required", "Local Mail attachments need caller-side last change metadata; import the path through the proxy again.")
                data = self.blobs.require_origin(item["sha256"], "caller_import")
                if len(data) != item["size"]:
                    raise Refused("stale_reference", "Attachment bytes changed; import again.")
                if item["name"].lower().endswith((".eml", ".msg")) or codec.is_mail(data):
                    raise Refused("file_refused", 'Saved mail cannot be attached from a local file; use mode=forward or attach the mail itself by {reference, part: "source"} so authored text and Bcc rules apply.')
                att = {**item, "type": "application/octet-stream"}
            attachment_refs.append(att)
        for att in attachment_refs:
            if att["type"].startswith(("message/", "multipart/")):
                att["source_type"], att["type"] = att["type"], "application/octet-stream"
        mail = {"account": account["id"], "from": sender, "to": to, "cc": cc, "bcc": bcc,
                "subject": subject, "text": args.get("text", ""), "format": args.get("format", "formatted" if any(p["kind"] == "draft_html" for p in generated) else account["format"]),
                "signature": "" if mode == "draft" and "text" not in args else account["signature"], "generated_parts": generated, "attachments": attachment_refs,
                "in_reply_to": reply_ids[-1] if reply_ids else "", "references": [],
                "answered_reference": original["reference"] if mode in {"reply", "reply_all"} else None}
        if reply_ids:
            mail["references"] = list(dict.fromkeys(codec.message_ids(original["msg"].get("References")) + reply_ids))
        if original:
            mail['source_reference'] = original['reference']
        for value in [mail["in_reply_to"], *mail["references"]]:
            codec.clean_header(value, authored=False)
        # Validate formatting before storing; MIME size also bounds total attachment work.
        if mail["format"] == "formatted":
            codec.formatted(mail["text"])
        comp = {"id": uuid.uuid4().hex, "hash": digest(mail), "mail": mail}
        self.check_mime(comp, self.mime(comp, self.message_id("0" * 32 + ":" + "0" * 32)))
        self.store.write({"mail:composition:" + comp["id"]: comp}, "mail_compose", "stored immutable composition " + comp["id"])
        return {"composition_id": comp["id"], "composition_hash": comp["hash"], "mail": visible(mail), "untrusted_content": {"derived_mail_fields": True}}

    def mime(self, comp, message_id, draft=False):
        mail = comp["mail"]
        utf8 = any(not codec.mailbox(v).isascii() for v in [mail["from"]] + mail["to"] + mail["cc"] + mail["bcc"])
        msg = EmailMessage(policy=codec.SMTP_POLICY.clone(utf8=utf8))
        for key, value in (("From", mail["from"]), ("To", ", ".join(mail["to"])), ("Cc", ", ".join(mail["cc"])),
                           ("Subject", mail["subject"]), ("Message-ID", message_id), ("Date", formatdate(localtime=False))):
            if value:
                msg[key] = value
        if draft and mail["bcc"]:
            msg["Bcc"] = ", ".join(mail["bcc"])
        if mail["in_reply_to"]:
            msg["In-Reply-To"] = mail["in_reply_to"]
        if mail["references"]:
            msg["References"] = " ".join(mail["references"])
        text = mail["text"]
        if mail["signature"]:
            text += "\n\n" + mail["signature"]
        generated = "".join(self.blobs.read(p["sha256"]).decode("utf8") for p in mail["generated_parts"] if p["kind"] != "draft_html")
        draft_html = "".join(self.blobs.read(p["sha256"]).decode("utf8") for p in mail["generated_parts"] if p["kind"] == "draft_html")
        if mail["format"] == "formatted":
            plain, html = codec.formatted(text)
            from html import escape
            msg.set_content(plain + generated, cte="quoted-printable")
            msg.add_alternative((html + draft_html) if draft_html else html + ("<pre>" + escape(generated) + "</pre>" if generated else ""), subtype="html", cte="quoted-printable")
        else:
            msg.set_content(text + generated, cte="quoted-printable")
        for item in mail["attachments"]:
            data = self.blobs.read(item["sha256"])
            # Freeze the rebuilt mail or byte-exact leaf payload approved during compose.
            major, minor = item["type"].split("/", 1)
            if item["type"] == "message/rfc822":
                major, minor = "application", "octet-stream"
            msg.add_attachment(data, maintype=major, subtype=minor, filename=codec.clean_header(item["name"], authored="source" not in item), cte="base64")
        raw = msg.as_bytes()
        if len(raw) > self.wires.limit:
            raise Refused("file_refused", "Encoded whole mail exceeds 64 MiB limit; reduce attachments.")
        return raw

    def check_mime(self, comp, raw, draft=False):
        from .guard import check
        mail = comp["mail"]
        text = mail["text"] + ("\n\n" + mail["signature"] if mail["signature"] else "")
        generated = "".join(self.blobs.read(p["sha256"]).decode("utf8") for p in mail["generated_parts"] if p["kind"] != "draft_html")
        draft_html = "".join(self.blobs.read(p["sha256"]).decode("utf8") for p in mail["generated_parts"] if p["kind"] == "draft_html")
        if mail["format"] == "formatted":
            plain, html = codec.formatted(text)
            from html import escape
            root_texts = [plain + generated, codec.html_text(html + draft_html if draft_html else html + ("<pre>" + escape(generated) + "</pre>" if generated else ""))]
        else:
            root_texts = [text + generated]
        disclosed = [t for att in mail["attachments"] for t in att.get("authored_text", [])]
        if all("text" in part for part in mail["generated_parts"] if part["kind"] != "draft_html"):
            disclosed.extend(root_texts)
        check(raw, root_texts, disclosed, draft)
        from .guard import check_headers
        check_headers(raw, mail, [codec.mailbox(v) for v in mail["to"] + mail["cc"] + mail["bcc"]], draft=draft)

    def message_id(self, operation_id):
        return "<" + operation_id.replace(":", ".") + "@mail.aresos.invalid>"

    def named_item(self, reference):
        msg = self.message(reference)["msg"]
        return {"reference": reference, **{k: str(msg.get(k, "")) for k in ("from", "subject", "date")}}

    def check_items(self, items):
        if not items or len({canonical(t["reference"]) for t in items}) != len(items):
            raise Refused("invalid_input", "Name a nonempty set of distinct exact messages.")
        if len({t["reference"]["account"] for t in items}) != 1:
            raise Refused("invalid_input", "A delete operation uses exactly one account.")
        for target in items:
            msg = self.message(target["reference"])["msg"]
            # str(header) may repair malformed syntax and discard its parse defects.
            people([msg.get("From", "")])
            if any(str(msg.get(k, "")) != target[k] for k in ("from", "subject", "date")):
                raise Refused("stale_approval", "Message sender, subject or date differs: stale, search again before deleting.")

    def delete_folders(self, account, payload):
        return [item['reference']['folder'] for item in payload['items']] + ([account['special']['trash']] if payload['mode'] == 'trash' else [])

    def composition_folders(self, mail):
        refs = [mail.get('source_reference'), mail.get('answered_reference')]
        for item in mail['attachments'] + mail['generated_parts']:
            source = item.get('source')
            if source:
                refs.append(source.get('reference', source))
        return [ref['folder'] for ref in refs if ref]

    def safe_folder(self, account, folder, empty=False):
        self.fresh_roles(account, names=[folder])
        if folder == "INBOX" or any(self.under(account, folder, k) for k in account["special"]):
            raise Refused("refused", "Special folders and their descendants cannot be renamed/deleted by these tools.")
        with self.transport.imap(account) as client:
            listed = folders(client)
            entry = next((f for f in listed if f["name"] == folder), None)
            if not entry:
                raise Refused("stale_reference", "Folder is stale, search again.")
            delimiter = entry["delimiter"]
            if delimiter and any(f["name"].startswith(folder + delimiter) for f in listed):
                raise Refused("refused", "Folder has subfolders; handle each explicitly first.")
            validity = select(client, folder)
            ids = uids(client)
            if empty and ids:
                raise Refused("stale_approval", "Folder received mail or is nonempty; name/delete those messages separately with approval.")
            return {"account": account["id"], "folder": folder, "uidvalidity": validity, "uids": ids}

    def prepare(self, verb, args):
        def prepared(description, payload, source=None):
            return self.question(verb, description, source), description, payload

        if verb == "onboarding_folder_probe":
            if not args["folder"].startswith("AresOS-probe-"):
                raise Refused("refused", "Not a disposable onboarding folder.")
            if args.get("empty"):
                args = {**args, "empty_state": self.safe_folder(self.account(args["account"]), args["folder"], empty=True)}
            return prepared({"action": "mail_onboarding_folder_probe", **args}, args)
        if verb == "send":
            comp = self.composition(args)
            account = self.account(comp['mail']['account'])
            self.fresh_roles(account, names=self.send_folders(account, comp['mail']))
            if not comp["mail"]["to"] + comp["mail"]["cc"] + comp["mail"]["bcc"]:
                raise Refused("invalid_input", "Composition has no recipients; compose with at least one recipient.")
            # Validate size and complete MIME before reserving; operation id is a fixed-size replacement.
            self.check_mime(comp, self.mime(comp, self.message_id("0" * 32 + ":" + "0" * 32)))
            description = {"action": "mail_send", "composition_id": comp["id"], "composition_hash": comp["hash"], **comp["mail"]}
            return prepared(description, {"composition": comp})
        if verb == "delete":
            self.check_items(args["items"])
            account = self.account(args["items"][0]["reference"]["account"])
            self.fresh_roles(account, names=self.delete_folders(account, args))
            capability = "MOVE" if args["mode"] == "trash" else "UIDPLUS"
            if capability not in account["capabilities"] or (args["mode"] == "trash" and not account["special"].get("trash")):
                raise Refused("unsupported_server", "Delete needs " + capability + " and an identified Trash for trash mode; ask owner to use his mail program.")
            if args["mode"] == "trash" and any(self.under(account, t["reference"]["folder"], "trash") for t in args["items"]):
                raise Refused("refused", "Already in Trash; permanent deletion requires a separate permanent approval.")
            return prepared({"action": "mail_delete", "account": account["id"], **args}, args)
        if verb == "folder_delete":
            account = self.account(args["account"])
            if not account["safe_folder_delete"]:
                raise Refused("unsupported_server", "Onboarding did not prove server-enforced refusal of nonempty DELETE; owner must delete folders in his mail program.")
            state = self.safe_folder(account, args["folder"], empty=True)
            return prepared({"action": "mail_folder_delete", **state}, state)
        if verb == "unsubscribe":
            self.fresh_roles(self.account(args['reference']['account']), names=[args['reference']['folder']])
            m = self.message(args["reference"])
            if args["target"] not in self.unsubscribe_choices(m["msg"]):
                raise Refused("stale_approval", "Target is not an exact List-Unsubscribe choice; read the mail again.")
            url = urlsplit(args["target"])
            if url.scheme == "https":
                if str(m["msg"].get("List-Unsubscribe-Post", "")).strip().casefold() != "list-unsubscribe=one-click":
                    raise Refused("refused", "Mail does not advertise RFC 8058 one-click POST; use owner's mail program.")
                if not url.hostname or url.username or url.password or url.fragment:
                    raise Refused("invalid_input", "Unsubscribe HTTPS URL contains unsupported credentials/fragment.")
                payload = {**args, "source_hash": sha256(m["raw"]), "method": "POST", "body": "List-Unsubscribe=One-Click"}
                return prepared({"action": "mail_unsubscribe", "account": args["reference"]["account"], **payload}, payload, m['msg'])
            if url.scheme == "mailto":
                query = parse_qs(url.query, keep_blank_values=True)
                if not query.keys() <= {"subject", "body"} or any(len(v) != 1 for v in query.values()):
                    raise Refused("refused", "Unsubscribe mailto has unsupported fields; use owner's mail program.")
                comp_args = {"account": args["reference"]["account"], "to": [unquote(url.path)],
                             "subject": query.get("subject", [""])[0], "text": query.get("body", [""])[0]}
                result = self.compose(comp_args)
                comp = self.composition(result)
                payload = {**args, "source_hash": sha256(m["raw"]), "composition": comp}
                return prepared({"action": "mail_unsubscribe", "target": args["target"], "reference": args["reference"], **comp["mail"],
                        "composition_id": comp["id"], "composition_hash": comp["hash"]}, payload, m['msg'])
            raise Refused("refused", "Only header-named mailto or RFC 8058 HTTPS POST is supported.")
        raise Refused("invalid_input", "Unsupported Mail operation.")

    def revalidate(self, operation):
        payload, action = operation["payload"], operation["action"]
        if action == "mail_send":
            comp = payload["composition"]
            account = self.account(comp['mail']['account'])
            self.fresh_roles(account, names=self.send_folders(account, comp['mail']))
            current = self.composition({"composition_id": comp["id"], "composition_hash": comp["hash"]})
            if current != comp:
                raise Refused("stale_approval", "Composition differs; compose/prepare again.")
            if comp["mail"]["answered_reference"]:
                self.message(comp["mail"]["answered_reference"])
        elif action == "mail_delete":
            account = self.account(payload["items"][0]["reference"]["account"])
            self.fresh_roles(account, names=self.delete_folders(account, payload))
            self.check_items(payload["items"])
        elif action == "mail_folder_delete":
            current = self.safe_folder(self.account(payload["account"]), payload["folder"], empty=True)
            if current != payload:
                raise Refused("stale_approval", "Folder state changed; read/prepare again.")
        elif action == "mail_unsubscribe":
            self.fresh_roles(self.account(payload['reference']['account']), names=[payload['reference']['folder']])
            m = self.message(payload["reference"])
            if sha256(m["raw"]) != payload["source_hash"] or payload["target"] not in self.unsubscribe_choices(m["msg"]):
                raise Refused("stale_approval", "Unsubscribe source changed; read/prepare again.")
            if "composition" in payload:
                comp = payload["composition"]
                self.composition({"composition_id": comp["id"], "composition_hash": comp["hash"]})

    def sent_matches(self, account, message_id):
        self.fresh_roles(account)
        folder = account["special"].get("sent")
        if not folder:
            raise Refused("unsupported_server", "SPECIAL-USE Sent missing; sending cannot safely check Message-ID evidence.")
        with self.transport.imap(account) as client:
            validity = select(client, folder)
            ids = ok(client.uid("SEARCH", None, "HEADER", "Message-ID", quote(message_id)), "Search Sent evidence")[0]
            result = []
            for uid in (ids or b"").split():
                raw, flags, _ = fetch_headers(client, int(uid))
                if str(codec.parse(raw).get("Message-ID", "")) == message_id:
                    result.append({"account": account["id"], "folder": folder, "uidvalidity": validity, "uid": int(uid), "message_id": message_id})
            return result

    def evidence(self, operation_id):
        op = self.store.get("op:" + operation_id)
        if not op or not op.get("payload", {}).get("composition"):
            return {"absence_is_not_proof": True}
        account = self.account(op["payload"]["composition"]["mail"]["account"], ready=False)
        return {"message_id": self.message_id(operation_id), "sent": self.sent_matches(account, self.message_id(operation_id)), "absence_is_not_proof": True}

    def has_submission_evidence(self, operation_id):
        return bool(self.evidence(operation_id).get("sent"))

    def stage_outcome(self, operation, name, outcome):
        # Free text has its own field; credential collisions must not alter evidence.
        if name == "diagnostic":
            return self.transport.scrub(outcome)
        patterns = {
            "wire_sha256": r"[a-f0-9]{64}", "sent_wire_sha256": r"[a-f0-9]{64}",
            "message_id": re.escape(self.message_id(operation["id"])),
            "smtp_data": r"attempting|accepted:250|refused:[1-5][0-9]{2}",
            "sent_copy": r"done|failed", "answered_flag": r"done|not_needed|failed",
            "folder_probe": r"nonempty_refusal|unqualified", "folder": r"deleted|refused",
            "dkim": r"refused|verified:[A-Za-z0-9_.-]+", "https_post": r"attempting|[1-5][0-9]{2}",
        }
        mail = operation["payload"].get("composition", {}).get("mail", {})
        for value in mail.get("to", []) + mail.get("cc", []) + mail.get("bcc", []):
            recipient = codec.mailbox(value)
            patterns["rcpt:" + recipient] = r"accepted:25[012]|refused:[1-5][0-9]{2}"
            patterns["recipient:" + recipient] = r"accepted|refused"
        for item in operation["payload"].get("items", []):
            key = digest(item["reference"])
            patterns["marked:" + key] = r"deleted flag set"
            patterns["target:" + key] = r"trashed|expunged|marked_deleted_not_expunged|refused|not_attempted"
        if name not in patterns or not isinstance(outcome, str) or not re.fullmatch(patterns[name], outcome):
            raise Refused("invalid_evidence", "Mail stage requires a service-defined key and typed outcome; no server diagnostic text is accepted.")
        return outcome

    def send_folders(self, account, mail):
        return [account['special']['sent']] + self.composition_folders(mail)

    def send_smtp(self, operation, comp, raw, stage):
        mail = comp["mail"]
        account = self.account(mail["account"])
        names = self.send_folders(account, mail)
        self.fresh_roles(account, names=names)
        accepted, refused = [], []
        started_data = False
        try:
            with self.transport.smtp(account) as smtp:
                recipients = [codec.mailbox(v) for v in mail["to"] + mail["cc"] + mail["bcc"]]
                needs_utf8 = any(not v.isascii() for v in [codec.mailbox(mail["from"])] + recipients)
                if needs_utf8 and not smtp.has_extn("smtputf8"):
                    raise NothingLeft("SMTPUTF8 not available now; no message submitted.")
                code, _ = smtp.mail(codec.mailbox(mail["from"]), options=["SMTPUTF8", "BODY=8BITMIME"] if needs_utf8 else [])
                if code != 250:
                    raise NothingLeft("SMTP refused envelope sender; no DATA sent.")
                for recipient in recipients:
                    code, _ = smtp.rcpt(recipient)
                    stage("rcpt:" + recipient, "accepted:" + str(code) if code in {250, 251, 252} else "refused:" + str(code))
                    (accepted if code in {250, 251, 252} else refused).append(recipient)
                if not accepted:
                    raise NothingLeft("All recipients refused; no DATA sent.")
                self.fresh_roles(account, names=names)
                self.check_mime(comp, raw)
                from .guard import check_headers
                check_headers(raw, mail, recipients)
                stage("smtp_data", "attempting")
                started_data = True
                code, _ = smtp.data(raw)
                self.store.checkpoint("smtp_answer")
                if code != 250:
                    stage("smtp_data", "refused:" + str(code))
                    return "failed", "Server explicitly refused DATA; no delivery accepted."
                stage("smtp_data", "accepted:250")
                for recipient in accepted:
                    stage("recipient:" + recipient, "accepted")
                for recipient in refused:
                    stage("recipient:" + recipient, "refused")
        except NothingLeft:
            raise
        except (OSError, smtplib.SMTPException, Refused) as exc:
            if not started_data:
                raise NothingLeft("Submission failed before DATA; no mail submitted (" + type(exc).__name__ + ").") from exc
            if isinstance(exc, smtplib.SMTPDataError):
                stage("smtp_data", "refused:" + str(exc.smtp_code))
                return "failed", "SMTP explicitly refused DATA; no delivery accepted."
            raise Uncertain("Final SMTP answer lost; delivery unknown, never resubmit.") from exc
        return ("partial", "Some recipients refused; accepted recipients must never be sent again.") if refused else ("done", "SMTP accepted delivery to every recipient.")

    def append(self, account, folder, raw, flags=None):
        with self.transport.imap(account) as client:
            response = ok(client.append(quote(folder), flags, None, raw), "APPEND")
            code = client.response("APPENDUID")[1]
            match = re.search(rb"(\d+) (\d+)", b" ".join(x for x in (code or []) if x))
            if not match:
                raise Uncertain("APPEND answer lacks UIDPLUS reference; search folder before retrying.")
            return {"account": account["id"], "folder": folder, "uidvalidity": int(match[1]), "uid": int(match[2]),
                    "message_id": str(codec.parse(raw).get("Message-ID", ""))}

    def local_stage(self, operation, which):
        comp = operation["payload"]["composition"]
        account = self.account(comp["mail"]["account"], ready=False)
        if which == "sent_copy":
            matches = self.sent_matches(account, self.message_id(operation["id"]))
            if matches:
                return "done"
            if account["sent_policy"] == "server":
                raise Refused("stage_missing", "Server-managed Sent copy not yet visible; owner must inspect it, no client APPEND.")
            key = operation["stages"].get("wire_sha256")
            if key is None:
                raise Refused("refused", "Exact wire bytes absent after restore; cannot recreate a Sent copy.")
            self.fresh_roles(account, names=[account['special']['sent']])
            self.append(account, account["special"]["sent"], self.wires.read(operation["stages"].get("sent_wire_sha256", key)), "(\\Seen)")
            self.store.checkpoint("mail_sent_copy")
            return "done"
        reference = comp["mail"]["answered_reference"]
        if reference is None:
            return "not_needed"
        with self.transport.imap(account) as client:
            self.fresh_roles(account, client, names=[reference['folder']])
            self.message(reference, writable=True, client=client)
            ok(client.uid("STORE", str(reference["uid"]), "+FLAGS.SILENT", "(\\Answered)"), "Answered flag")
            self.store.checkpoint("mail_answered_flag")
        return "done"

    def execute(self, operation, stage):
        action, payload = operation["action"], operation["payload"]
        if action == "mail_onboarding_folder_probe":
            account = self.account(payload["account"])
            if "empty_state" in payload and self.safe_folder(account, payload["folder"], empty=True) != payload["empty_state"]:
                raise Refused("stale_approval", "Probe cleanup folder changed; owner must inspect it.")
            with self.transport.imap(account) as client:
                response = client.delete(quote(payload["folder"]))
            qualified = nonempty_refusal(response)
            stage("folder_probe", "nonempty_refusal" if qualified else "unqualified")
            if qualified:
                return "refused", "Server specifically refused nonempty DELETE; survival and cleanup still need verification."
            return ("done" if response[0] == "OK" else "refused"), "Disposable DELETE completed or protection unproven; inspect onboarding qualification."
        if action == "mail_delete":
            # Complete set validated before the first mutation; each exact UID is pinned again at use.
            self.check_items(payload["items"])
            account = self.account(payload["items"][0]["reference"]["account"])
            completed = 0
            for index, target in enumerate(payload["items"]):
                ref = target["reference"]
                marked = False
                try:
                    with self.transport.imap(account) as client:
                        self.fresh_roles(account, client, names=self.delete_folders(account, payload))
                        m = self.message(ref, writable=True, client=client)
                        if any(str(m["msg"].get(k, "")) != target[k] for k in ("from", "subject", "date")):
                            raise Uncertain("Target changed during deletion; inspect per-target stages.")
                        if payload["mode"] == "trash":
                            if "MOVE" not in client.capabilities:
                                raise Uncertain("MOVE no longer available; inspect deletion status.")
                            ok(client.uid("MOVE", str(ref["uid"]), quote(account["special"]["trash"])), "UID MOVE to Trash")
                            self.store.checkpoint("mail_moved:" + str(ref["uid"]))
                        else:
                            if "UIDPLUS" not in client.capabilities:
                                raise Uncertain("UIDPLUS no longer available; no broad expunge allowed.")
                            ok(client.uid("STORE", str(ref["uid"]), "+FLAGS.SILENT", "(\\Deleted)"), "Mark exact UID deleted")
                            self.store.checkpoint("mail_marked:" + str(ref["uid"]))
                            stage("marked:" + digest(ref), "deleted flag set")
                            marked = True
                            ok(client.uid("EXPUNGE", str(ref["uid"])), "UID EXPUNGE exact message")
                            self.store.checkpoint("mail_expunged:" + str(ref["uid"]))
                    stage("target:" + digest(ref), "trashed" if payload["mode"] == "trash" else "expunged")
                    completed += 1
                except Refused:
                    stage("target:" + digest(ref), "marked_deleted_not_expunged" if marked else "refused")
                    for remaining in payload["items"][index + 1:]:
                        stage("target:" + digest(remaining["reference"]), "not_attempted")
                    return ("partial" if completed or marked else "refused"), "Server refused an exact target; inspect per-item stages and prepare a new named set only after owner review."
            return "done", "Exactly named messages deleted; no unnamed UID expunged."
        if action == "mail_folder_delete":
            account = self.account(payload["account"])
            self.revalidate(operation)
            with self.transport.imap(account) as client:
                self.fresh_roles(account, client, names=[payload['folder']])
                if client.delete(quote(payload["folder"]))[0] != "OK":
                    stage("folder", "refused")
                    return "refused", "Server refused DELETE (possibly concurrent new mail); refresh folders."
            self.store.checkpoint("mail_folder_deleted")
            stage("folder", "deleted")
            return "done", "Approved empty folder deleted."
        if action == "mail_unsubscribe" and "composition" not in payload:
            from .dkim import verify_one_click
            try:
                signature = verify_one_click(self.message(payload["reference"])["raw"])
                stage("dkim", "verified:" + signature["domain"])
            except Refused:
                stage("dkim", "refused")
                return "failed", "No valid DKIM covering both unsubscribe headers; no POST attempted. Use header mailto or owner mail program."
            url = urlsplit(payload["target"])
            account = self.account(payload["reference"]["account"])
            connection = http.client.HTTPSConnection(url.hostname, url.port or 443, context=context(account), timeout=20)
            try:
                stage("https_post", "attempting")
                connection.request("POST", url.path + ("?" + url.query if url.query else ""), payload["body"].encode(),
                                   {"Content-Type": "application/x-www-form-urlencoded"})
                response = connection.getresponse()
                stage("https_post", str(response.status))
                return ("done", "One-click endpoint accepted POST.") if 200 <= response.status < 300 else ("partial", "Endpoint refused/redirected; no redirect followed, inspect with owner.")
            finally:
                connection.close()
        comp = payload["composition"]
        raw = self.mime(comp, self.message_id(operation["id"]))
        try:
            self.check_mime(comp, raw)
        except Refused as exc:
            raise NothingLeft("Outgoing MIME guard refused the exact wire bytes; nothing submitted.") from exc
        stage("message_id", self.message_id(operation["id"]))
        stage("wire_sha256", self.wires.put(raw, origin="wire"))
        if comp["mail"]["bcc"]:
            sent_header = EmailMessage(policy=codec.SMTP_POLICY)
            sent_header["Bcc"] = ", ".join(comp["mail"]["bcc"])
            bcc_header = sent_header.as_bytes().split(b"\r\n\r\n",1)[0] + b"\r\n"
            stage("sent_wire_sha256", self.wires.put(bcc_header + raw, origin="wire"))
        state, reason = self.send_smtp(operation, comp, raw, stage)
        if state == "failed":
            return state, reason
        failed_stage = False
        for which in ("sent_copy", "answered_flag"):
            try:
                stage(which, self.local_stage(self.store.get("op:" + operation["id"]), which))
            except (Refused, OSError, imaplib.IMAP4.error, Uncertain):
                stage(which, "failed")
                failed_stage = True
        return ("partial", reason + " Missing local stages; repair without SMTP.") if failed_stage else (state, reason)

    def repair(self, operation, which):
        if operation["action"] not in {"mail_send", "mail_unsubscribe"} or "composition" not in operation.get("payload", {}):
            raise Refused("refused", "Only mail Sent/answered stages can be repaired; never deletes or POSTs.")
        if operation["stages"].get("smtp_data") != "accepted:250":
            raise Refused("refused", "No durable successful final DATA answer; Sent presence alone cannot identify accepted recipients. Inspect unknown with owner.")
        if which == "sent_copy" and operation["stages"].get(which) == "done":
            return "done"
        return self.local_stage(operation, which)

    def repaired_outcome(self, operation):
        stages = operation["stages"]
        if operation["state"] == "partial" and stages.get("sent_copy") == "done" and stages.get("answered_flag") in {"done", "not_needed"} and not any(v.startswith("refused:") for k, v in stages.items() if k.startswith("rcpt:")):
            return "done", "All recipients accepted and missing local stages repaired without resubmission."
        return operation["state"], operation["reason"]

    def drop(self, operation):
        pass

    def call(self, verb, args):
        if verb == "account_add":
            raise Refused("terminal_required", "Owner must run sudo aresos admin mail account add; password is read only from terminal over admin.sock.")
        read = verb in {"accounts", "folders", "search", "read", "thread", "contacts", "filing_locations", "filing_notices"}
        summary = {k: v for k, v in args.items() if k in {"account", "id", "reference", "references", "target", "name", "folder", "part", "composition_id", "previous", "add", "remove"}}
        if verb in {"move", "copy"}:
            from .filing import short_name
            summary = {"message_count": len(args["references"]),
                       "target": short_name(args.get("target", args.get("target_role", "")))}
        if not read:
            self.store.write({}, "mail_" + verb, "starting Mail change", outcome="started", untrusted_content=summary)
        try:
            result = self._call(verb, args)
        except Exception:
            if not read:
                self.store.write({}, "mail_" + verb, "Mail change incomplete; inspect server before repeating", outcome="unknown", untrusted_content=summary)
            raise
        if not read:
            self.store.write({}, "mail_" + verb, "Mail change completed", outcome=result.get("state", "done"), untrusted_content=summary)
        return result

    def _call(self, verb, args):
        if verb == "filing_locations":
            from .filing import location_page
            return location_page(self.store, args)
        if verb == "filing_notices":
            from .filing import notice_page
            return notice_page(self.store, args, app="mail")
        if verb == "account_folders":
            account = self.account(args["id"], ready=False)
            with self.transport.imap(account) as client:
                listed = folders(client)
                current = resolve(listed)
            roles_hash = digest(current)
            if "roles_hash" in args:
                if args["roles_hash"] != roles_hash:
                    raise Refused("stale_approval", "Folder roles changed since owner review; inspect account_folders again.")
                protected = account.setdefault("protected_special", {})
                if "roots" not in account:
                    # Older setups stamped INBOX's delimiter onto remembered
                    # roots too. Recover each from its own LIST row or refuse.
                    for kind, values in protected.items():
                        recovered = []
                        for value in values:
                            matches = [f for f in listed if f['name'] == value['folder']]
                            if len(matches) != 1:
                                raise Refused("special_folders_changed", "Remembered protected root cannot be resolved; owner must inspect setup before recording roles.")
                            entry = {"folder": matches[0]['name'], "delimiter": matches[0]['delimiter']}
                            if entry not in recovered:
                                recovered.append(entry)
                        protected[kind] = recovered
                for kind in ("trash", "drafts"):
                    values = protected.setdefault(kind, [])
                    for mapping in (account, current):
                        if mapping["special"].get(kind):
                            value = root(mapping, kind)
                            if "roots" not in mapping:
                                matches = [f for f in listed if f["name"] == value["folder"]]
                                if len(matches) != 1:
                                    raise Refused("special_folders_changed", "Old protected root cannot be resolved; owner must inspect setup before recording roles.")
                                value = {"folder": matches[0]["name"], "delimiter": matches[0]["delimiter"]}
                            if value not in values:
                                values.append(value)
                account.update(current)
                self.store.write({"mail:account:" + args["id"]: account}, "mail_account_folders", "owner recorded current special-folder roles")
            return {"untrusted_content": visible({**current, 'optional_roles': optional_status(recorded_optional(account), current['optional'])}), "roles_hash": roles_hash, "recorded": "roles_hash" in args}
        if verb == "account_settings":
            account = self.account(args["id"], ready=False)
            if "sent_policy" in args:
                if not account.get("onboarded"):
                    raise Refused("onboarding_incomplete", "Review incomplete probes; cannot enable this account by settings.")
                account["sent_policy"] = args["sent_policy"]
                account["ready"] = True
            account.update({k: args[k] for k in ("format", "signature") if k in args})
            self.store.write({"mail:account:" + args["id"]: account}, "mail_account_settings", "owner set Mail habits/Sent policy")
            return {"account": self.public_account(account)}
        if verb == "accounts":
            return {"accounts": [self.public_account(a) for _, a in self.store.items("mail:account:")]}
        if verb == "search":
            return self.search(args)
        if verb == "read":
            return self.read(args)
        if verb == "thread":
            return self.thread(args)
        if verb == "contacts":
            return self.contacts(args)
        if verb == "compose":
            return self.compose(args)
        if verb == "attachment_save":
            _, item = self.attachment(args)
            return {"file": item, "caller_save_required": True}
        if verb == "folders":
            account = self.account(args["account"])
            with self.transport.imap(account) as client:
                values = folders(client)
                for item in values:
                    if "\\Noselect" in item["flags"]:
                        item.update(total=0, unread=0)
                        continue
                    status = b" ".join(ok(client.status(quote(item["name"]), "(MESSAGES UNSEEN UIDVALIDITY UIDNEXT)"), "Folder counts"))
                    for field in ("MESSAGES", "UNSEEN", "UIDVALIDITY", "UIDNEXT"):
                        match = re.search(field.encode() + rb" (\d+)", status)
                        if match:
                            item[{"MESSAGES": "total", "UNSEEN": "unread"}.get(field, field.lower())] = int(match[1])
            return self.page(values, args, values, ["folders", account["id"]])
        if verb == "draft_save":
            comp = self.composition(args)
            account = self.account(comp["mail"]["account"])
            self.fresh_roles(account, names=[account['special']['drafts']] + self.composition_folders(comp['mail']) + ([args['previous']['folder']] if 'previous' in args else []))
            if "previous" in args:
                if args["previous"]["account"] != account["id"] or not self.under(account, args["previous"]["folder"], "drafts"):
                    raise Refused("invalid_input", "Previous must name a draft in this account.")
                self.message(args["previous"])
            folder = account["special"].get("drafts")
            if not folder or "UIDPLUS" not in account["capabilities"]:
                raise Refused("unsupported_server", "Draft save needs SPECIAL-USE Drafts and UIDPLUS for exact APPEND reference.")
            raw = self.mime(comp, "<draft." + uuid.uuid4().hex + "@mail.aresos.invalid>", draft=True)
            raw = b"X-AresOS-Authored: 1\r\n" + raw
            self.check_mime(comp, raw, draft=True)
            return {"reference": self.append(account, folder, raw, "(\\Draft)"), "previous_retained": args.get("previous"),
                    "next": "Delete previous only via named delete approval."}
        if verb in {"folder_create", "folder_rename"}:
            account = self.account(args["account"])
            names = [args['name']] + ([args['folder']] if verb == 'folder_rename' else [])
            self.fresh_roles(account, names=names)
            quote(args["name"])
            if any(self.under(account, args["name"], kind) for kind in account["special"]):
                raise Refused("refused", "Destination is a special folder or its descendant.")
            if verb == "folder_rename":
                self.safe_folder(account, args["folder"])
            with self.transport.imap(account) as client:
                self.fresh_roles(account, client, names=names)
                if verb == "folder_create":
                    ok(client.create(quote(args["name"])), "Create folder")
                else:
                    ok(client.rename(quote(args["folder"]), quote(args["name"])), "Rename folder")
            return {"account": account["id"], "folder": args["name"]}
        if verb in {"move", "copy", "flag"}:
            refs = args["references"]
            if not refs or len({r["account"] for r in refs}) != 1 or len({canonical(r) for r in refs}) != len(refs):
                raise Refused("invalid_input", "Name distinct references from exactly one account.")
            account = self.account(refs[0]["account"])
            names = [ref['folder'] for ref in refs]
            needed = []
            if verb != "flag":
                if ('target' in args) == ('target_role' in args):
                    raise Refused('invalid_input', 'Supply exactly one target folder or target_role (junk/archive).')
                needed = [args['target_role']] if 'target_role' in args else []
                current = self.fresh_roles(account, names=names + ([args['target']] if 'target' in args else []), needed=needed)
                target = current['special'][args['target_role']] if needed else args['target']
                names.append(target)
            self.fresh_roles(account, names=names, needed=needed)
            # Check the complete set before any UID mutation, including mixed batches.
            # An unmarked owner's draft would lose provenance outside this folder.
            if verb != "flag" and any(self.under(account, ref["folder"], "drafts") for ref in refs):
                raise Refused("refused", "Messages in SPECIAL-USE Drafts or its subfolders cannot be moved/copied; send it with mail_compose mode=draft, or delete it with mail_delete (which asks the owner).")
            if verb != "flag" and self.under(account, target, "trash"):
                raise Refused("refused", "Moving/copying to Trash is deletion; use named prepare_delete/delete approval.")
            for ref in refs:
                self.message(ref)
            result = []
            with self.transport.imap(account) as client:
                self.fresh_roles(account, client, names=names, needed=needed)
                if verb != "flag":
                    if target not in [f["name"] for f in folders(client) if "\\Noselect" not in f["flags"]]:
                        raise Refused("stale_reference", "Target folder is stale, search again.")
                    if "UIDPLUS" not in client.capabilities or (verb == "move" and "MOVE" not in client.capabilities):
                        raise Refused("unsupported_server", "Exact filing references require UIDPLUS; moving also requires MOVE.")
                    from .filing import file_messages
                    return file_messages(self, account, client, verb, refs, target, names, needed)
                else:
                    for value in args["add"] + args["remove"]:
                        if value not in {"\\Seen", "\\Flagged", "\\Answered"} and not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
                            raise Refused("invalid_input", "Only Seen, Flagged, Answered or simple custom keywords; Deleted/Recent/Draft forbidden.")
                for ref in refs:
                    m = self.message(ref, writable=True, client=client)
                    if verb == "flag":
                        for key, operator in (("add", "+FLAGS.SILENT"), ("remove", "-FLAGS.SILENT")):
                            if args[key]:
                                ok(client.uid("STORE", str(ref["uid"]), operator, "(" + " ".join(args[key]) + ")"), "Set flags")
                        _, flags = fetch(client, ref["uid"], self.wires.limit)
                        result.append({"reference": ref, "flags": flags})
            return {"items": result}
        raise Refused("invalid_input", "Unsupported Mail action.")
