1. **blocking — Local-mail detection still permits saved-mail reimport.**  
   [codec.py:34](/Users/pab/AresOS-19-mail/control/aresos_control/mail/codec.py:34) rejects header names containing valid punctuation, such as `X_Custom:`, and immediately returns false. Adding that header to an exported mail and renaming it `.txt` bypasses [adapter.py:365](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:365). I reproduced compose → prepare → MIME accepting a marked 21,000-character draft with a **733-byte approval omitting its body**; the attachment retained its Bcc unchanged. These bytes remain a mail message, outside the deliberately deferred ordinary-file class.  
   **Fix:** recognize the full mail header-name syntax when scanning the leading header block. Add export/reimport regressions with punctuation-bearing extension headers, checking both disclosure refusal and Bcc protection.

2. **blocking — Transfer-encoded nested messages retain Bcc and bypass authored-text disclosure.**  
   [codec.py:176](/Users/pab/AresOS-19-mail/control/aresos_control/mail/codec.py:176) relies on the parser’s tree traversal, while decoding only non-multipart nodes. A base64-encoded `message/rfc822` or `message/global` appears multipart but its enclosed headers remain encoded. The sanitizer consequently returns it unchanged. I reproduced new, reply and forward compositions whose approval claimed Bcc removal while the emitted attachment decoded to both `Bcc` and `Resent-Bcc`. The nested authored marker/body also escaped [approval_texts](/Users/pab/AresOS-19-mail/control/aresos_control/mail/codec.py:160).  
   **Fix:** decode encapsulated-message transfer encodings before recursive sanitization and provenance inspection, then freeze the sanitized bytes; refuse unsupported cases. Test the fully decoded received contents.

Finding 3 appears fixed: focused collision, diagnostic-redaction and invalid-outcome checks passed. The report records the requested JUDGMENT-CALL and PLAN-GAP.

Reproductions used in-memory storage with actual composition/approval/MIME code. Generated-artifact verification passed; I read the recorded passing CI logs but did not rerun the container suite.

CHANGES-NEEDED