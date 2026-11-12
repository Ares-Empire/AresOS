# Security re-review of brief 19 (Mail), rounds 7 and 8

Reviewer: Codex `gpt-6-astra`, xhigh, read-only, fresh context, 2026-11-07. Reviewed `ec4a8bba..5b0a0fb7` against SECURITY-REVIEW.md. Run by the lead; saved by the lead.

Reviewed `ec4a8bba..5b0a0fb7`. **Three blocking findings remain.** Findings 1 and 2 are not fully closed.

1. **Blocking — A role change can still turn a free move into deletion.**  
   [adapter.py:1038](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:1038) performs the final role check, but nothing binds that snapshot to the subsequent MOVE at [adapter.py:1057](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:1057).

   Concrete reproduction: `Ordinary` passes the final check; another client/server reassigns `\Trash` from `Trash` to `Ordinary`. The additional LIST at line 1040 actually sees the new designation, but checks only selectability. The service then executes `UID MOVE` into current Trash, with **zero approval operations**. I reproduced this through the actual engine/adapter paths with an IMAP substitute.

   Drafts and optional-role protections have the same check/action gap. Another LIST closer to the command would narrow, rather than eliminate, it. The action needs an enforceable stability guarantee or a policy that refuses these vulnerable free mutations.

2. **Blocking — Required roles use INBOX’s separator, allowing Trash and Drafts descendants to escape protection.**  
   [roles.py:60](/Users/pab/AresOS-19-mail/control/aresos_control/mail/roles.py:60) retains only each required role’s name; line 64 retains only INBOX’s hierarchy separator. [adapter.py:132](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:132) consequently tests every required-role descendant using that separator.

   Concrete reproduction: LIST reports INBOX with `/`, but Trash and Drafts in a namespace using `.`. Setup and every fresh-role check pass. `mail_move(target="Trash.Child")` issues MOVE without approval. An unmarked, unflagged owner draft in `Drafts.Child` also passes `authored()` and exports its decoded body through `attachment_save(part="1")`.

   This requires no race or changing roles. It reopens both findings 1 and 2. Store, compare and apply the actual separator for each protected root, including remembered roots after owner refresh. Optional-role metadata already retains individual separators.

3. **Blocking — The shared blob downloader bypasses the new draft-export prohibition.**  
   Draft composition stores its decoded body as a blob and exposes its hash at [adapter.py:379](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:379). [engine.py:313](/Users/pab/AresOS-19-mail/control/aresos_control/engine.py:313) permits downloading any existing shared blob by hash, without checking draft provenance or export authorization. The shipped configuration exposes `testapp`, whose [file_save action](/Users/pab/AresOS-19-mail/control/aresos_control/definitions.py:84) reaches that downloader through [proxy.py:37](/Users/pab/AresOS-19-mail/control/aresos_control/proxy.py:37).

   Concrete route: compose and save a long draft → compose it with `mode=draft` → take `generated_parts[0].sha256` → `testapp.file_save` as `notes.txt` → attach that path to a new Mail composition → prepare/send.

   Using the actual proxy, engine, composition and submission code with in-memory files/storage and protocol substitutes, direct draft export correctly refused, but this route exported **23,017 bytes** and delivered them unchanged under a **771-byte approval containing none of the draft text**. No shell or file editing was needed. Enforce provenance/export restrictions at the shared download and reimport boundaries; refusing only `mail_attachment_save` is insufficient.

The should-fix findings are:

- **Historical operation status becomes inaccessible after unrelated role drift.**  
  [engine.py:205](/Users/pab/AresOS-19-mail/control/aresos_control/engine.py:205) combines the recorded operation with live evidence; [adapter.py:645](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:645) now requires valid current roles for that evidence. Removing Trash’s designation caused `operation_status` for an existing send to return only `special_folders_changed`, withholding its stored approval and stages. Return the recorded operation with a separate evidence error, especially when the owner needs to investigate uncertainty.

- **The new comparison rejects legitimate leading-space subjects.**  
  [guard.py:230](/Users/pab/AresOS-19-mail/control/aresos_control/mail/guard.py:230) compares the reparsed subject with the unnormalized input. `" invoice"` passes input validation but fails composition because serialization/parsing removes the leading whitespace. Normalize before constructing the immutable approval. Ordinary non-ASCII display names, internationalized domains and long folded subjects passed my additional checks.

For original findings 3 and 5, I found no remaining bypass in the reviewed paths. Encoded-word/control attacks in Subject and From/To/Cc/Bcc names refused; derived formatting characters are escaped, and homoglyph names remain accompanied by explicit addresses. A substituted wire subject failed before DATA, altered approval input refused, and replay did not send again. Standard draft source exports and nested marked-draft parts also refused; the export failures above are alternate routes.

The audit changes correctly keep Mail references, recipient stages, caller-save metadata and historical summaries inside escaped `untrusted_content`. I checked the actual storage/log code using SQLite in memory. The `engine.py` changes did not weaken approval equality or replay checks.

Finding 4 is truthfully described in both the owner section and round 7: the replacement empty folder can be deleted. The “no mail lost” statement remains conditional on actual server enforcement of nonempty-folder refusal, which the report leaves for provider qualification.

Verification: **19 plain-Python tests passed**; generated artifacts matched. Additional reproductions used in-memory substitutes, not real providers. No files were edited and no containers ran.

CHANGES-NEEDED