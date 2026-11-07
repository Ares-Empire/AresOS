**blocking — Unmarked drafts lose protection after move/copy.**  
At [adapter.py:43](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:43), draft classification depends on the current folder or marker. [The move/copy path](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:928) preserves bytes but records no provenance for an unmarked Drafts source.

I reproduced:

1. An unmarked owner draft in SPECIAL-USE Drafts refuses attachment.
2. `mail_move` or `mail_copy` puts it in an ordinary folder.
3. Attaching its `source`, attaching part `1`, or forwarding it as an attachment now succeeds.
4. Compose, prepare and submission complete; the receipt contains the draft body, while the approval contains no full-text disclosure.

All six move/copy combinations reproduced using the actual adapter and submission paths with in-memory storage and IMAP/SMTP substitutes. This violates point 1 and the requested protection after move/copy. The tests cover moved/copied **marked** drafts and stationary **unmarked** Drafts separately, missing their intersection.

**Fix:** durably preserve draft provenance across move/copy and consult it for attachments, quotes and `mode=draft`; alternatively refuse moves/copies that cannot preserve it. Keep marker writing exclusive to `mail_draft_save`. Add unmarked-Drafts regressions for both operations, source/part/attached forwarding, and full inline disclosure or oversized refusal.

The remaining assessment of `59a2c029..614c0e0a` is:

| Brief point | Assessment |
|---|---|
| **1** | **Incomplete**, as above. Marked drafts, nested markers and original-byte checks otherwise work; refusal names both alternatives. |
| **2** | Implemented: only draft-save writes the marker; tested outgoing and Sent messages are unmarked, and newly sent mail forwards successfully. |
| **3** | Implemented: guard remains independent; container and decoded-leaf markers refuse, including immediately before DATA. Failed submissions do not submit on replay. |
| **4** | Implemented: text stays literal and line-scanned; colon-leading prose works. Declared containers and encodings retain strict validation. |
| **5** | Implemented for saved marked drafts: header-like bodies remain whole, and the 23,100-character case refuses approval without truncation. |
| **6** | Report includes the requested `.eml` judgment call, all five programs, sources and read/assumed distinctions. Exact recipient presentation remains untested. |

**REVIEW-5’s three original reproductions are fixed.** The finding above leaves the broader draft rule incomplete.

The earlier expectation changes are justified by the new rules: attachment disclosure becomes refusal, Sent markers disappear, and text is no longer recursively interpreted. Unmarked equivalents retain successful sanitization, payload and hash checks. I found no unrelated weakening.

The defective non-text-header expectation also follows point 4’s explicit opaque-content rule. I found no additional path from that change for the owner’s private recipients or draft text to escape, beyond the deferred local-file class. Saved-mail detection remains intact, and actual declared containers remain strict.

**Verification:** 14 focused tests passed; six new and six earlier adapter tests passed with in-memory substitutes; generated artifacts matched. Forty additional compose/prepare/submit combinations passed across both formats, received/Sent sources, replies and both forward styles, preserving PDF/image bytes and excluding private Bcc data. I read retained twice-passing final-head Mail/base logs; I did not rerun the container suites or recipient applications.

CHANGES-NEEDED.