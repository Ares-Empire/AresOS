# Security review 17 of brief 19 (Mail): round 24, under owner decision 24

Reviewer: Codex `gpt-6-astra`, xhigh, read-only, fresh context, 2026-11-08. Reviewed `de1098d7` (round diff `dd8ea4f6..de1098d7` plus a sweep of the tools' own safety), against the fail-closed disk bar of round 21. Run by the lead; saved by the lead.

Blocking findings at `de1098d7`, reproduced with in-memory probes:

1. **Large filing observations swallow the disk-full response.** [filing.py:321](/Users/pab/AresOS-19-mail/control/aresos_control/mail/filing.py:321) attaches every observed location without paging; the shared result layer adds these after the result-size check. Reproduction: move a message with a 20,000-character Message-ID into a folder containing 350 identical copies, change that destination’s role to Trash, then fail the post-MOVE write with ENOSPC. The schema-valid request produced a **7,134,315-byte response**, exceeding the 6,291,456-byte socket limit. Transmission refuses; the daemon suppresses that exception. The caller receives neither the disk-full diagnosis nor the filing warning. Bound the response and make retained observations pageable.

2. **Background admission failure unnecessarily locks a recovered disk.** [engine.py:119](/Users/pab/AresOS-19-mail/control/aresos_control/engine.py:119) sets `write_failed` for every storage refusal, including checks that precede all writes. Reproduction: let background blob expiry encounter insufficient free space at ledger admission, then restore ample space. Admission now succeeds, but subsequent composition requests still refuse, and background expiry returns immediately. No journal transaction started; nevertheless, only restarting clears the block. Preserve the warning without setting the incomplete-transaction latch for admission failures.

3. **Blob cleanup can still replace the original disk-full cause.** [blobs.py:128](/Users/pab/AresOS-19-mail/control/aresos_control/blobs.py:128) unconditionally unlinks the temporary file in `finally`. Reproduction: fail the private outgoing-wire write with ENOSPC, then fail that unlink with EIO. Through the submission handler, the result reports only `storage_error` / “Storage I/O failed”; disk full disappears. Preserve the first storage failure across this cleanup, too.

Should-fix: the expanded sweep still exceeds its demonstrated guarantees. It injects one failure per scenario, omits archive compaction, and does not exercise persistent exhaustion or combinations of primary and cleanup failures. Its recovery assertions accept `done` after any attempted remote action. Probing the actual assertion function with a two-message deletion reported done after only `MOVE:1`, while UID 2 remained, passed. Assert completion against every requested target, and validate serialized responses through the transport limit.

Generated artifacts match; four pure-Python ingress tests passed. Another test module could not load because `jsonschema` is missing. I did not rerun the filesystem-writing sweep. No files changed or containers ran. I found no additional approval-binding, replay, credential-disclosure, or free-action bypass in the inspected paths.

CHANGES-NEEDED