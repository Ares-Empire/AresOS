1. **blocking — Authored body text can still escape full disclosure.**  
   At [codec.py:328](/Users/pab/AresOS-19-mail/control/aresos_control/mail/codec.py:328), reparsing a text payload as mail takes precedence over collecting its authored text. The guard repeats this omission at [guard.py:183](/Users/pab/AresOS-19-mail/control/aresos_control/mail/guard.py:183).

   I created a marked draft through `compose → draft_save` whose body begins `From: …`, then a long `Subject: …`, an empty line and `Small body`. Attaching its source or forwarding it as an attachment produced an approximately **1.3 KiB approval showing only “Small body”**. Submission completed; decoding the submitted attachment recovered the undisclosed 23,100-character Subject originally written as body text.

   **Fix:** collect and require disclosure of each original authored text payload **before** interpreting its contents as another MIME entity. Recursive inspection must add checks without replacing that disclosure obligation. Add this free-draft round trip and require oversized approval refusal.

2. **blocking — The independent guard accepts undisclosed markers on containers.**  
   [guard.py:115](/Users/pab/AresOS-19-mail/control/aresos_control/mail/guard.py:115) initially permits marker lines. Multipart and message branches return before the final marker check; inherited provenance is enforced only for text leaves at [guard.py:186](/Users/pab/AresOS-19-mail/control/aresos_control/mail/guard.py:186).

   A marked multipart containing an `application/octet-stream` child with `Hidden authored words` passes with **no disclosed text**. Injected past the builder, it passed compose, prepare and both send checks, reaching DATA. A marked `message/rfc822` container with an opaque child behaves similarly. Reconstruction also removes these original markers without retaining an enforceable disclosure obligation when no text is collected.

   **Fix:** account for every original marker across every traversal branch. Refuse marked content whose disclosure cannot be established, regardless of its claimed type. Add builder-bypassing container tests requiring `failed`, no DATA and no submission on replay.

3. **should-fix — Ordinary prose beginning with a colon-bearing line is rejected.**  
   At [guard.py:183](/Users/pab/AresOS-19-mail/control/aresos_control/mail/guard.py:183), any parsed header key triggers strict recursive MIME validation, including a partial parse of ordinary prose.

   Both plain and formatted new messages containing:
   ```
   FYI: the documents are attached.
   Please review them before Friday.
   ```
   fail compose with `defective nested header block`. `Status: all green` followed by prose also fails.

   **Fix:** distinguish an incomplete speculative parse of prose from an actual MIME entity. Keep private-line scanning and strict inspection of declared encodings/containers, while allowing ordinary approved text. Add these plain/formatted regressions.

The brief’s points assess as follows:

| Point | Result |
|---|---|
| **1 — Reconstruction and provenance** | Allowlisted reconstruction and explicit/implicit nested-message handling are implemented. Original authored-text disclosure still fails finding 1. |
| **2 — Independent final check** | No codec imports; compose and exact-before-DATA checks are present. Recognized Bcc refusals become failed and do not submit on replay. Header parsing now stops only at truly empty lines. Marker enforcement fails finding 2; ordinary-mail compatibility fails finding 3. |
| **3 — Binary integrity** | PDF/PNG binary and base64 payloads remained byte-exact in my adapter tests. The exact-source IMAP fixture honestly supplies raw input before service processing; its independent SMTP receipt assertions still test outgoing preservation. It does not establish native Dovecot binary preservation. |
| **4 — Regressions** | The three original REVIEW-4 cases are addressed and have regression coverage. The additional failures above remain uncovered. |
| **5 — Change time** | Correctly captures caller-side `max(mtime, ctime)` from the stable descriptor and includes local offset/zone in approval metadata. |

**Verification:** ran the 10 focused tests successfully, generated-artifact verification, and 20 synthetic adapter compose/prepare/submit combinations covering plain/formatted new mail, replies, reply-all and both forward styles. PDF/image bytes matched. Final-check Bcc refusals stayed failed on replay without DATA. Read the retained twice-passing CI logs; did not rerun the container suite. The adapter experiments used in-memory storage and SMTP capture.

CHANGES-NEEDED