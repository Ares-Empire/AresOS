1. **blocking — Failed-save cleanup can delete a replacement file and leave exported bytes behind.** [files.py:153](/Users/pab/AresOS-18-control-base/control/aresos_control/files.py:153)

   Cleanup checks the destination’s inode, then separately calls `unlink(name)`. A concurrent replacement between those calls causes it to delete someone else’s file. A mocked syscall reproduction deleted the replacement inode, despite the comment promising otherwise.

   Cleanup also removes only the requested name: the existing hard-link race test leaves `alias.txt` containing the downloaded bytes. An alias or renamed output outside the allowed folders can survive a reported refusal.

   **Fix:** avoid unlinking a concurrently replaceable pathname based on an earlier stat. Make rollback operate safely on the newly created pinned inode, and test replacement during cleanup plus surviving aliases outside allowed folders.

2. **blocking — An expired approval can still send or delete.** [engine.py:89](/Users/pab/AresOS-18-control-base/control/aresos_control/engine.py:89)

   Expiry is checked before `revalidate()` and `has_submission_evidence()`. Those potentially blocking checks can cross the deadline while the operation remains reserved; submission then proceeds without another expiry check. An in-memory reproduction produced `done` and a receiver arrival at time 221 for an approval expiring at 220.

   **Fix:** recheck expiry after those checks, immediately before transitioning to `submitting`. On expiry, record failure, drop the reservation, and perform no submission. Test deadlines crossed during both adapter checks.

3. **should-fix — Positive delivery evidence can later become “nothing submitted.”** [engine.py:96](/Users/pab/AresOS-18-control-base/control/aresos_control/engine.py:96)

   When the adapter finds existing submission evidence, the service refuses but leaves the operation `reserved`. Cancellation or expiry subsequently records `failed` with “nothing submitted.” I reproduced that result while the receiver still contained an arrival. This false assurance can lead the owner or Claude to prepare a duplicate send.

   **Fix:** durably transition the operation to `unknown`, retaining the evidence and explanation. It must no longer qualify for reserved-only cancellation or expiry. Extend the existing preflight-evidence test to cover both paths.

4. **should-fix — Large valid hook inputs disable both reminders.** [hooks.py:28](/Users/pab/AresOS-18-control-base/control/aresos_control/hooks.py:28)

   The hook truncates stdin at 65,537 bytes and parses it outside error handling. A valid input containing a 70,000-character prompt raises `JSONDecodeError` before querying pending work. Large pasted prompts are ordinary documented inputs; Stop also receives the assistant’s final message. ([Hook reference](https://code.claude.com/docs/en/hooks#userpromptsubmit-input))

   **Fix:** handle complete valid input without silently truncating JSON. If enforcing an input limit, return explicit, event-appropriate failure feedback. Add large-input subprocess tests for both hooks.

Generated-artifact drift checking passed. The reproductions used in-memory storage and mocked syscalls; I did not rerun the Linux container suite. No files were changed.

CHANGES-NEEDED