1. **blocking — Saving and reimporting a draft bypasses full-text approval.**  
   [adapter.py:363](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:363) treats imported blobs as opaque attachments, ignoring their retained `X-AresOS-Authored` marker. Claude can save a draft, export its source, then attach the exported file through the normal import path. My in-memory reproduction produced a **910-byte approval with none of the attached draft’s 21,002 body characters displayed**. Finding 1 therefore remains bypassable.  
   **Fix:** preserve authored provenance by content hash across export/import, and enforce full-text disclosure or refusal for those blobs regardless of filename. Add the complete save → export → reimport → prepare-send regression.

2. **blocking — Explicit source attachments still leak Bcc during forwarding.**  
   [adapter.py:352](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:352) accepts caller-supplied mail attachments without the Bcc sanitization applied to automatic forward attachments. Composing a forward with `attachments=[{"reference": sent_reference, "part": "source"}]` transmitted the Sent source’s `Bcc: hidden@mail.invalid` while approval showed `bcc: []`. Finding 2 remains open through this forwarding path.  
   **Fix:** apply recursive Bcc/Resent-Bcc removal to every outgoing mail-source attachment before hashing and approval, including explicit references and reimported sources. Test the received attachment bytes.

3. **should-fix — Credential scrubbing corrupts machine-readable operation evidence.**  
   [engine.py:79](/Users/pab/AresOS-19-mail/control/aresos_control/engine.py:79) scrubs stage identifiers and outcomes indiscriminately. With the valid password `accepted:250`, recording successful DATA acceptance stores `smtp_data="[credential removed]"`; I confirmed that repair then refuses because its required evidence disappeared. Matching substrings can also corrupt stored wire hashes. This is introduced by finding 3’s fix.  
   **Fix:** separate typed evidence from diagnostic text. Scrub untrusted diagnostic fragments without rewriting internal stage keys, hashes or acceptance values. Add a credential-collision regression covering repair.

The folder-qualification checks and repair-description correction appear addressed by inspection. Generated-artifact verification printed `Generated artifacts match definitions`. Reproductions used in-memory substitutes; the full container suite was not rerun in this read-only review.

CHANGES-NEEDED