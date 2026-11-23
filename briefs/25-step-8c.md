# 25, step 8c: boot 2's Ctrl+Alt+F3 behind the black screen

This is the lead's brief for the next step of package 25, continuing the session that did step 8b.

## What happened

The check build OS run 44594035922 ran on `bb7bc420`. Attempt 1 failed in the mod build: Maven briefly returned
404s, which was an outside outage. Attempt 2 got to the VM.
- **Boot 1 passed.** The output was `GUARDIAN_VM_PASSED (save): guard stop 0.043 s to 6.097 s after the power key, then
  session-1.scope at 6.103 s, greetd.service at 6.105 s, user@1001.service at 6.319 s, var.mount at None s; record
  save=saved close=exited; power-off …`. That confirms step 8b's finding (b).
- **Boot 2 (hang) armed:** `GUARDIAN_ARMED (hang)`, and the offline journal passed for its power-key path.
- **Then the host failed:**

```
os/ci/vm.py line 176: guardian_host.check(evidence, guardian, ...)
os/ci/guardian_host.py line 233: AssertionError: ('Ctrl+Alt+F3 did not switch to a text console behind the black
screen', ['tty1', 'tty1', ... 20 × 'tty1'])
```

The evidence for both passes is at
`~/.cache/aresos-dev/25-check-44594035922/check-build-evidence/` (`vm-pass-1/`, `vm-pass-2/`). Treat
it as data. The rest of the run's log: `gh run view 44594035922 --attempt 2 --log`.

## Your job

1. **Decide from the evidence and the code whether this is real or the harness.**
   - **Real:** during a stop, the black screen, labwc or the stop routine keeps the owner from reaching tty3. This is
     the escape route during a hung shutdown, so it is real harm under decision 24.
   - **The harness:** the key is sent at the wrong moment, through a path that can't switch VTs in the guest (for
     example QMP key events while labwc holds the seat, or after logind has stopped), or the console is read wrongly.

   Say which, with the lines that prove it. Note what boot 1 shows about Ctrl+Alt+F3, if it checks it.
2. **Fix the real cause with a test that would have failed.** Never weaken what boot 2 must prove (brief,
   Acceptance): the guard ends at its limit, the machine powers off by itself within 3.1's worst case, and the record
   says `unsaved` and `overrun`. If tty3 behind the black screen isn't in the Acceptance list and turns out to be
   impossible to prove reliably in a VM, say so as a JUDGMENT-CALL. Don't drop it on your own.
3. **Tests by module name only**, as in step 8b. Never the whole `os/tests` suite, `test_owner_update`,
   `test_inherited_homebrew` or `test_sysusers`.
4. **Update `reviews/25-guardian/PROGRESS.md`** with the cause, the fix, the evidence, and boot 1's measured times
   from this run, which go into the report draft.
5. **Commit this brief with your first commit**, push `pkg/25-guardian`, and stop. Don't start or watch any GitHub
   run, don't open the PR, don't merge, and don't message anyone. Commit trailer:
   `Co-Authored-By: Codex gpt-6.2-astra <noreply@openai.com>`.

The rules are step 8b's. Your last message is under 250 words: real or harness, the proof, the fix, the tests with
counts, the new head SHA, and any JUDGMENT-CALL.
