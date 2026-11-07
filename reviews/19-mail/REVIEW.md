Reviewed head `bc38016`. Four blocking findings and one description mismatch.

1. **blocking — Drafts can hide Claude-authored text from approval.**  
   [adapter.py:303](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:303) converts an existing draft’s body into `generated_parts` when `text` is omitted. Claude can compose arbitrary text, save it through the free draft tool, then compose from that draft. The send approval shows empty `text` and a hash reference, while SMTP receives the complete body. My in-memory reproduction reduced **21,016 authored characters to a 713-byte approval**. This bypasses both the full-authored-text requirement and the asking-size limit.  
   **Fix:** preserve authored-text provenance across draft saves and reloads, or include the entire draft body in approval. Refuse oversized approvals. Add a compose → save draft → reload → prepare-send regression test.

2. **blocking — Forwarding a Sent message as an attachment leaks its Bcc.**  
   [adapter.py:287](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:287) attaches the original source unchanged. Client-managed Sent copies contain Bcc, so forwarding one exposes those addresses inside `forward.eml`, despite the outgoing approval showing `bcc: []`. I reproduced an absent outer Bcc header alongside `Bcc: secret@mail.invalid` in the received attachment.  
   **Fix:** remove private recipient headers from automatically generated forwarded messages before hashing and approving them, including nested messages, or refuse this forwarding mode when preserving exact bytes would disclose Bcc. Test forwarding a service-created Sent copy containing Bcc.

3. **blocking — Mail exceptions can expose passwords through operation results and storage.**  
   [transport.py:79](/Users/pab/AresOS-19-mail/control/aresos_control/mail/transport.py:79) allows IMAP login errors containing raw server text to escape. During deletion execution, these reach [engine.py:120](/Users/pab/AresOS-19-mail/control/aresos_control/engine.py:120), which appends `str(exc)` to the persisted, public operation reason. A server response echoing the password therefore reaches the log, act socket and Claude. The new outer request sanitizer never sees this exception because `submit` consumes it first. I confirmed the leak with a synthetic IMAP exception.  
   **Fix:** sanitize transport exceptions before persisting or returning them; retain only controlled error categories and safe messages. Test credential-echoing failures during execution, after successful preflight, and inspect responses and durable records.

4. **blocking — Any DELETE refusal falsely qualifies the server’s nonempty-folder guard.**  
   [adapter.py:615](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:615) interprets every non-OK response as protection against nonempty deletion. [onboarding.py:58](/Users/pab/AresOS-19-mail/control/aresos_control/mail/onboarding.py:58) then sets `safe_folder_delete=True`. A temporary `[INUSE]` refusal qualifies an otherwise unsafe server; I reproduced that classification. Later, mail arriving after the final empty-folder check can be deleted without being named. Cleanup deletion outcomes are also ignored.  
   **Fix:** leave deletion disabled on generic, permission or transient refusals. Require a qualified nonempty-specific refusal, verify the probe message survived, and verify successful empty-folder deletion before recording qualification. Add transient-refusal tests against an otherwise unsafe server.

5. **should-fix — Repair description promises unsupported evidence handling.**  
   [definitions.py:96](/Users/pab/AresOS-19-mail/control/aresos_control/mail/definitions.py:96) says repair accepts “durable successful DATA evidence **or qualified Sent evidence**.” [adapter.py:707](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:707) unconditionally requires recorded `accepted:250`.  
   **Fix:** describe the implemented restriction and regenerate the artifacts, so Claude knows unknown submissions require owner inspection even when Sent evidence exists.

Verification: generated-artifact checks passed; targeted reproductions used in-memory substitutes without real accounts. I did not rerun the container suite in this read-only environment.

CHANGES-NEEDED