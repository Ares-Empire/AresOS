"""Owner-only, explicit terminal onboarding. Interrupted probes never resume."""
from email.message import EmailMessage
import time
import uuid

from ..common import Refused, digest
from ..adapters import Uncertain
from .transport import folders, select, ok, quote


def qualify_folder_delete(engine, account, probe_folder, ref):
    mail = engine.adapters["mail"]
    from ..definitions import BY_NAME
    account["safe_folder_delete"] = False
    account["folder_delete_reason"] = "Nonempty DELETE protection not proven: generic, unrelated or transient refusal, or deletion succeeded."
    try:
        approval = engine.reserve("mail", "onboarding_folder_probe", {"account": account["id"], "folder": probe_folder})["approval"]
        result = engine.submit(BY_NAME["mail_onboarding_folder_probe"], approval)["operation"]
        candidate = result["state"] == "refused" and result["stages"].get("folder_probe") == "nonempty_refusal"
        with mail.transport.imap(account) as client:
            exists = probe_folder in [f["name"] for f in folders(client)]
        if not exists:
            account["folder_delete_reason"] = "Probe folder did not survive nonempty DELETE; protection not proven."
            return
        # Re-fetch the exact UIDVALIDITY/UID/Message-ID, never a lookalike replacement.
        mail.message(ref)
        cleanup = engine.reserve("mail", "delete", {"items": [mail.named_item(ref)], "mode": "permanent"})["approval"]
        result = engine.submit(BY_NAME["mail_delete"], cleanup)["operation"]
        if result["state"] != "done" or result["stages"].get("target:" + digest(ref)) != "expunged":
            account["folder_delete_reason"] = "Exact probe UID EXPUNGE cleanup failed; owner must inspect probe folder and operation status."
            return
        mail.safe_folder(account, probe_folder, empty=True)
        if not candidate:
            account["folder_delete_reason"] += " Exact probe removed; empty folder retained for owner cleanup."
            return
        cleanup = engine.reserve("mail", "onboarding_folder_probe", {"account": account["id"], "folder": probe_folder, "empty": True})["approval"]
        result = engine.submit(BY_NAME["mail_onboarding_folder_probe"], cleanup)["operation"]
        with mail.transport.imap(account) as client:
            exists = probe_folder in [f["name"] for f in folders(client)]
        if result["state"] != "done" or exists:
            account["folder_delete_reason"] = "Empty probe folder DELETE cleanup failed; owner must inspect probe folder and operation status."
            return
        account["safe_folder_delete"] = True
        account["folder_delete_reason"] = "Qualified: nonempty-specific NO, exact probe survived, exact UID EXPUNGE and empty-folder DELETE succeeded."
    except (Refused, OSError, Uncertain):
        account["folder_delete_reason"] = "Probe survival or cleanup could not be verified; owner must inspect probe folder and operation status. Folder deletion stays disabled."


def onboard(engine, args, password):
    mail = engine.adapters["mail"]
    account_id = args["id"]
    previous = engine.store.get("mail:account:" + account_id)
    if previous is not None:
        raise Refused("refused", "Account id already exists; inspect interrupted probes/status with the owner. Never repeat onboarding sends automatically; choose a new id only after owner review.")
    if not password or len(password) > 8192 or "\x00" in password:
        raise Refused("invalid_input", "Terminal password is empty or too long.")
    from .codec import address
    if not args["addresses"]:
        raise Refused("invalid_input", "At least one owner address is required.")
    account = {**args, "addresses": [address(v, True) for v in args["addresses"]], "format": args.get("format", "plain"),
               "signature": args.get("signature", ""), "ready": False, "capabilities": [], "smtp_capabilities": [],
               "special": {"inbox": "INBOX"}, "sent_policy": "unqualified", "safe_folder_delete": False}
    mail.transport.store_password(account_id, password)
    engine.store.write({"mail:account:" + account_id: account}, "mail_account_add", "owner started onboarding; incomplete until probes finish", outcome="started")
    with mail.transport.imap(account) as client:
        account["capabilities"] = sorted(client.capabilities)
        listed = folders(client)
        from .roles import resolve
        try:
            account.update(resolve(listed))
        except Refused as exc:
            engine.store.write({"mail:account:" + account_id: account}, "mail_account_add", "special-folder configuration incomplete", outcome="refused")
            raise Refused("unsupported_server", "Server lacks complete, unique SPECIAL-USE roles; owner must configure folders before onboarding.") from exc
    with mail.transport.smtp(account) as smtp:
        account["smtp_capabilities"] = sorted(smtp.esmtp_features)
    # Missing special use is never guessed from English mailbox names.
    if "sent" not in account["special"] or "UIDPLUS" not in account["capabilities"]:
        engine.store.write({"mail:account:" + account_id: account}, "mail_account_add", "capabilities insufficient for safe onboarding", outcome="refused")
        raise Refused("unsupported_server", "Server lacks identified SPECIAL-USE Sent or UIDPLUS; onboarding stops without sending. Owner must configure special-use folders on server.")
    mail.onboarding_id = account_id  # In-memory only; a crash leaves persisted readiness false.
    account["sent_policy"] = "server"
    engine.store.write({"mail:account:" + account_id: account}, "mail_account_add", "record probe configuration", outcome="started")
    probe_folder = "AresOS-probe-" + uuid.uuid4().hex
    with mail.transport.imap(account) as client:
        ok(client.create(quote(probe_folder)), "Create disposable onboarding folder")
    message = EmailMessage()
    message["From"] = account["addresses"][0]
    message["To"] = account["addresses"][0]
    message["Subject"] = "AresOS disposable folder safety probe"
    message["Message-ID"] = "<probe." + uuid.uuid4().hex + "@mail.aresos.invalid>"
    message.set_content("Synthetic onboarding data only.")
    from .codec import SMTP_POLICY
    ref = mail.append(account, probe_folder, message.as_bytes(policy=SMTP_POLICY))
    # These owner-only probes and their exact cleanup use the same durable engine.
    qualify_folder_delete(engine, account, probe_folder, ref)
    engine.store.write({"mail:account:" + account_id: account}, "mail_account_add", "folder probe recorded; SMTP self-probe follows", outcome="started")
    comp = mail.compose({"account": account_id, "to": [account["addresses"][0]], "subject": "AresOS onboarding self-probe", "text": "Synthetic setup check. No reply needed."})
    approval = engine.reserve("mail", "send", comp)["approval"]
    result = engine.submit(__import__("aresos_control.definitions", fromlist=["BY_NAME"]).BY_NAME["mail_send"], approval)["operation"]
    if result["stages"].get("smtp_data") != "accepted:250":
        account["ready"] = False
        engine.store.write({"mail:account:" + account_id: account}, "mail_account_add", "self-probe incomplete; never repeat automatically", outcome="unknown")
        raise Refused("onboarding_incomplete", "Self-probe delivery not confirmed; inspect operation status with owner. Never repeat automatically.")
    # Poll read-only evidence, never resubmit. Missing Sent is not proof of non-delivery.
    for _ in range(5):
        if mail.sent_matches(account, mail.message_id(result["id"])):
            break
        time.sleep(0.2)
    account["sent_policy"] = "server" if mail.sent_matches(account, mail.message_id(result["id"])) else "client"
    account["onboarded"] = True
    account["ready"] = account["sent_policy"] == "server"
    engine.store.write({"mail:account:" + account_id: account}, "mail_account_add", "onboarding complete; Sent policy observed over bounded window", outcome="done")
    if account["sent_policy"] == "client":
        engine.repair("mail", {"operation_id": result["id"], "stage": "sent_copy"})
    mail.onboarding_id = None
    return {"account": mail.public_account(account), "self_probe_operation": result["id"],
            "probe_folder": probe_folder, "sent_detection_window_seconds": 1,
            "notice": "Client Sent is only an observation over a bounded window. Account stays unready until owner confirms sent_policy with admin account_settings; no automatic resubmission."}
