# Security review 7 of brief 19 (Mail): whole approval and ingress path

Reviewer: Codex `gpt-6-astra`, xhigh, read-only, fresh context, 2026-11-08. Reviewed the whole path at `6a2e0e36` (not a diff), on mac-capacity's suggestion after six per-round diff reviews. Run by the lead; saved by the lead.

Reviewed `6a2e0e36`. I found three blocking issues under the requested whole-path rule.

1. **A prepared operation can be submitted without any Claude Code approval.**  
   [daemon.py:48](/Users/pab/AresOS-19-mail/control/aresos_control/daemon.py:48) authenticates the Unix user; [engine.py:101](/Users/pab/AresOS-19-mail/control/aresos_control/engine.py:101) checks the returned approval object, but has no evidence that the owner approved it.

   Reproduction: as the configured assistant UID, compose mail, call `prepare_send`, then pass its unchanged `approval` to `aresos mail send --input …` or directly to `act.sock`. No forgery is necessary: preparation supplies everything submission requires. Through the actual CLI/proxy/engine/Mail paths, with transport and storage substituted in memory, this reached SMTP and returned `done` without MCP or a permission prompt.

   The documented Bash sandbox is intended to prevent Claude from reaching this route. I did not establish a sandbox escape. However, the service accepts unconfined same-UID clients, and the supplied settings remain drafts with a separate ask-rules file. **Whole-path approval therefore remains a deployment dependency.** Make verified confinement and installed mandatory ask rules a prerequisite for enabling Mail, or authenticate a trusted prompt-mediated submission path. Disabling only the CLI would leave the socket route open.

2. **Free folder renaming can silently move an entire mailbox under Trash.**  
   [adapter.py:1042](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:1042) checks roles before `RENAME`, but performs no subsequent check or persistent warning.

   Reproduction: `Source` contains three messages; `Parent` is ordinary. Call `mail_folder_rename` with `folder="Source", name="Parent/Subfolder"`. After the final role check, another client/server reassigns `\Trash` from `Trash` to `Parent`. The service then renames the populated mailbox beneath current Trash.

   My in-memory IMAP reproduction returned success, left all three messages under Trash, and produced **zero approval operations and no pending warning**. This extends the earlier role-race finding to an uncovered action: the owner’s documented reporting compromise applies to MOVE/COPY, whose post-checks are absent here. Require an enforceable destination-role guarantee, or explicitly extend that owner-reviewed policy to renames with durable intent, post-checking and bounded warnings.

3. **Exponent overflow can corrupt the independent operation journal.**  
   [common.py:59](/Users/pab/AresOS-19-mail/control/aresos_control/common.py:59) rejects literal `Infinity`, but accepts `1e400` as infinity. The socket’s [`saved` method](/Users/pab/AresOS-19-mail/control/aresos_control/engine.py:350) accepts an unvalidated outcome.

   Reproduction: send `{"v":1,"method":"saved","app":"mail","outcome":1e400}`, then perform an ordinary composition. The first request returns `invalid_input`, but [storage.py:170](/Users/pab/AresOS-19-mail/control/aresos_control/storage.py:170) has already appended its independent record before serializing the invalid event. The service continues writing past that incomplete transaction. Restart validation then fails with `evidence_corrupt`, requiring owner recovery.

   I reproduced this using the real journal-writing and validation code with SQLite and journal bytes in memory. Reject overflowing numbers, validate every transport envelope, serialize the complete event before changing durable state, and stop further writes after an incomplete journal transaction.

Should-fix:

- **Finish decoder bounds and encoding validation.** A `saved.outcome` containing 1,200 nested arrays raises an uncaught `RecursionError`; sufficiently deep input also escapes the decoder itself. MCP lines and hook input lack explicit byte limits. The decoder additionally accepts lone surrogates, surrogate-encoded invalid UTF-8, and byte-input BOMs. Enforce consistent UTF-8, Unicode-scalar, depth and size rules before dispatch, including the error-classification parser.
- **Keep attachment disclosure as the existing owner decision.** Routes carrying Claude-written text as attachment bytes remain should-fix, as requested.

Verification: **38 existing tests passed** with filesystem storage/blob operations substituted in memory; generated artifacts matched. Additional probes confirmed rejection of changed questions, boolean UIDs and a Unicode hash alias, plus single execution on replay, expiry refusal and old-generation refusal. No files were edited or containers run. Real Claude Code, Linux confinement and providers were not exercised.

CHANGES-NEEDED
