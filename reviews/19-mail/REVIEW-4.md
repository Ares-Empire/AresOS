1. **blocking — Saved mail still bypasses detection through a whitespace-only continuation line.**  
   [codec.py:34](/Users/pab/AresOS-19-mail/control/aresos_control/mail/codec.py:34) treats whitespace-only lines as the end of headers. Prefixing an unmarked Bcc-bearing Sent mail with `X_Custom: value\r\n \t\r\n` makes `is_mail` return false, although the email parser recognizes its From, Subject, Bcc and Resent-Bcc without defects. Renamed `.txt`, it passed compose, prepare and submission with both private headers intact. The approval showed only attachment metadata.

   The guard imports and calls this same detector at [guard.py:110](/Users/pab/AresOS-19-mail/control/aresos_control/mail/guard.py:110), so its decision about what to inspect is not independent. **Fix:** stop only at a genuinely empty line, give the guard independent classification, and add this saved-mail regression through the proxy.

2. **blocking — Implicit messages inside `multipart/digest` retain private headers.**  
   [codec.py:230](/Users/pab/AresOS-19-mail/control/aresos_control/mail/codec.py:230) and [guard.py:99](/Users/pab/AresOS-19-mail/control/aresos_control/mail/guard.py:99) inspect children without preserving their parent’s default Content-Type. A digest child lacking Content-Type defaults to `message/rfc822`; its enclosed message may have Subject without From. [RFC 2046](https://www.rfc-editor.org/rfc/rfc2046#section-5.1.5)

   I attached such a digest with `filename="inner.txt"` and enclosed Bcc/Resent-Bcc. Both survived sanitization, approval and submission; decoding the submitted attachment exposed both headers. **Fix:** carry the effective MIME type into recursive inspection in both implementations, or refuse these containers. Add sanitizer-bypassing guard tests for implicit digest messages.

3. **should-fix — Received binary PDF/image attachments are silently corrupted.**  
   [adapter.py:255](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:255) now serializes every outgoing source part with CRLF line endings before decoding it. For `Content-Transfer-Encoding: binary`, this changes payload bytes. My PDF and PNG fixtures containing LF and bare CR were preserved by `517d278` but changed at HEAD, including PNG signature bytes. Compose and the guard accepted the corrupted attachments.

   **Fix:** preserve original decoded binary payloads while inspecting their wrappers; re-emission must preserve those bytes. Add raw received-message fixtures and assert byte equality after sending.

Verification: five focused tests passed. Ten plain/formatted new, reply, reply-all and forward combinations passed using in-memory storage and an SMTP sink, including base64 PDF/image preservation. Recognized guard refusals produced `failed`, stayed failed on replay, and called no DATA. Both guard locations are correctly before DATA. I read the recorded passing CI logs; I did not rerun the container suite.

CHANGES-NEEDED