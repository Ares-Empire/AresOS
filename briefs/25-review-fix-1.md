# 25: review 1's fix round (the lead's brief)

Review 1 (`reviews/25-guardian/REVIEW-1.md`, a fresh Codex gpt-6.2-astra high) says CHANGES-NEEDED at `6b5e461e`.
`linux-aresos` read the os/ diff and found nothing blocking. The lead's calls under decision 24's bar:

## Fix (real harm)

1. **Finding 1: an unreadable lock is not "no writer".** `jvm_lock_held()` returns `False` when opening the lock fails
   (`aresos-desktop` about :3846), and the stop then reports a confirmed "nothing to stop" (:3212). Make a failure to
   open or test the lock mean "unknown". The stop must then end `unsaved` with its reason, or take the existing
   fallback path, and never report confirmed. Check every other caller of `jvm_lock_held()` for the same assumption.
   Add a test that fails on today's code.
2. **Finding 2: logout needs a fresh zero.** The brief's lead fix 4 asks for "a fresh count of zero immediately before
   it signals labwc, not only at the start". Today's final check rereads a cached count (:3402, `app_windows()` :2090).
   Before signalling labwc, get a fresh `windows` report from the helper, using the existing request path with a short
   deadline. Refuse logout if it doesn't come, or if it isn't zero. Add a test where the helper stalls after reporting
   zero and an app opens.

## Known limits (no code change; write them into REPORT.md's Known limits)

- Finding 3: during first setup, a heartbeat or the launch's exit can update the remembered inode. A home swapped by
  hand during setup could then be moved aside on `retry`. The no-overwrite rename keeps its files.
- Finding 4: a world that switches away and back by name within one save request can pass on the old answer. A home
  switch saves the world itself.
- The image rule reads only literal names in `Exec*=` lines in `/usr/lib/systemd/system` and `/etc/systemd/system`.
  A unit that passes the program through `Environment=` and `env` gets past it. So does one in `/run/systemd/system`
  or `/usr/local/lib/systemd/system`, which the image doesn't ship (`linux-aresos`'s note).
- The guard unit shows as failed in that shutdown's journal when the stop isn't confirmed. It exits 1 on purpose.
- `guardian_host.py` accepts a guard stop of 55–85 s for boot 2. The measured time is 60.6 s against the 60 s deadline.

## Then

- Run the tests by module name only (`test_aresos_desktop*`, `test_aresos_guardian*`, `test_guardian_vm`), as in
  step 8b.
- Update REPORT.md: the fixes, the Known limits above, and a line that a new check build on the final commit must pass
  (the brief's lead fix 7).
- Commit this brief and REVIEW-1.md with your first commit, push `pkg/25-guardian`, and stop. Don't start or watch any
  GitHub run.
- Commit trailer: `Co-Authored-By: Codex gpt-6.2-astra <noreply@openai.com>`.
- Your last message, under 200 words: each fix, its test, the test counts, and the new head SHA.
