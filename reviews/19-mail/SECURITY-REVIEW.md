# Final security review of brief 19 (Mail), before round 7

Reviewer: Codex `gpt-6-astra`, xhigh, read-only, fresh context, 2026-11-07. Reviewed `46c19aeb..ec4a8bba` (brief 19 on brief 18's base), after seven package reviews. Run by the lead; saved by the lead.

Reviewed `46c19aeb..ec4a8bba`. Four blocking findings remain.

1. **Blocking — A free move can put mail into Trash after its designation changes.**  
   [adapter.py:911](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:911) checks the Trash name cached at onboarding. The fresh listing at [adapter.py:918](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:918) checks only whether the destination is selectable.

   If another client or the server changes Trash from `Trash` to `NewTrash`, `mail_move(target="NewTrash")` proceeds even when the current LIST explicitly marks it `\Trash`. My reproduction issued `UID MOVE` and reserved **zero approval operations**. Because the tool is classified `change`, the ask rules provide no protection.

   Resolve and validate current special-folder roles before mutations; refuse missing, ambiguous or changed mappings. The same stale mapping also affects Drafts protection.

2. **Blocking — Exporting a draft’s decoded body bypasses full-text approval.**  
   [adapter.py:239](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:239) exports a selected part’s decoded bytes. Draft protection applies only when `outgoing=True`. Reimport at [adapter.py:379](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:379) recognizes mail headers and extensions, but the exported body has neither.

   The complete route uses ordinary Mail tools: compose a long plain-text draft → save it → `attachment_save(part="1", name="notes.txt")` → compose another message attaching that path → prepare/send.

   Through the actual proxy and engine paths with in-memory storage, **23,002 bytes of draft body reached the SMTP substitute unchanged under a 781-byte approval containing none of that text**. No file editing was needed. This decoded-part route escapes the earlier source-export regressions.

   Preserve draft provenance on exported parts and imported matching blobs, then require full disclosure or refuse attachment. The documented ordinary-file exception does not satisfy the owner’s rule for this service-created draft export.

3. **Blocking — Encoded words conceal the actual outgoing subject and bypass control-character disclosure.**  
   [codec.py:45](/Users/pab/AresOS-19-mail/control/aresos_control/mail/codec.py:45) checks the supplied header string before decoding. [adapter.py:387](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:387) stores that string for approval, but assigning it to the MIME message at [adapter.py:406](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:406) interprets encoded words.

   I submitted a Base64 encoded-word subject. Approval displayed the encoded token; the delivered subject was **“I authorize the transfer.”** Both final MIME checks passed and the operation finished `done`. Encoded carriage returns, line feeds and a right-to-left override also passed, without their decoded characters appearing escaped in approval.

   Normalize or reject encoded-word input before constructing approval. Compare the decoded final headers against the approved values, and escape controls after normalization. Apply the same discipline to address display names.

4. **Blocking — Folder deletion can delete a replacement folder instead of the approved one.**  
   At [adapter.py:746](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:746), revalidation finishes before a separate connection deletes by name alone.

   Concrete race: approve empty `Invoices`, UIDVALIDITY 1; after the final check, another client renames it to `Invoices-kept` and creates a new empty `Invoices`, UIDVALIDITY 2. The service deletes the replacement and reports `done`. My simulated interleaving reproduced exactly that; the approved folder survived under its new name.

   The onboarded nonempty-folder guard cannot prevent this: both folders are empty. Folder deletion needs an atomic server guarantee binding deletion to the approved identity, or must remain unavailable where that guarantee cannot be established. Another non-atomic recheck does not close the race.

5. **Should-fix — Mail-derived instructions lose their untrusted marking in the general audit log.**  
   [adapter.py:821](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:821) incorporates references, including the sender-controlled Message-ID, into free-text audit summaries. [engine.py:182](/Users/pab/AresOS-19-mail/control/aresos_control/engine.py:182) returns those summaries through `control_log` without an `untrusted_content` marker.

   A hostile Message-ID therefore reappears after an ordinary flag operation as part of the service’s own “Mail change completed” record. Mail tools have a blanket warning about repeated mail-derived fields; `control_log` lacks that warning and only identifies explicitly marked fields as untrusted.

   Keep external values in structured, marked fields throughout audit output, including cross-app results.

Verification: 14 pure-Python codec/guard tests passed; generated artifacts matched. The new reproductions used actual implementation paths with in-memory files and protocol substitutes, not real servers. No files were edited and no containers ran.

CHANGES-NEEDED