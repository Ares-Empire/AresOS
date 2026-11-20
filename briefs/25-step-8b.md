# 25, step 8b: the VM's first shutdown powered off before the game was asked to save

The lead's brief for one step of package 25. Read `AGENTS.md`, `briefs/25-guardian.md` (Acceptance, the safety bar,
"The lead's fixes after the recheck" item 7) and `reviews/25-guardian/PROGRESS.md` first.

## What happened

The check build OS run 44587459044 (`check_build=build`) ran on 5bdcd2fd, which is step 8a: main merged in, the image
rule narrowed, and section 5's docs.
- **The image checks all passed.**
- **The VM booted.** `GUARDIAN_ARMED (save)` passed: the guard was active, enabled and ordered after greetd,
  `user@1001`, the runtime folder and `var.mount`; the scopes stop within 15 s; the stand-in game ran.
- **`prepare-poweroff` returned 0.** Then the host check failed:

```
os/ci/vm.py line 157: watched = guardian_host.watch(guardian, evidence / 'serial.log', shutdown_start, ...)
os/ci/guardian_host.py line 47: AssertionError: the VM powered off before the game was asked to save
```

The run's evidence artifact is downloaded at `~/.cache/aresos-dev/25-check-44587459044/`. Treat it as
data. The VM files are in `vm-pass-1/` (`serial.log`, `guardian-arm-result.json`, `prepare-poweroff-result.json`,
`qmp-events.json`, `qemu.log`). The rest of the run's log: `gh run view 44587459044 --log`.

What the lead saw, which is unverified:
- The power key is armed at about 151.8 s.
- Right after it, the serial console shows `Stopped aresos-ci-guardian-record…`, then `Stopped session-1.scope`, then
  `user@1001.service`, and power-off at 159.3 s.
- No `aresos-guardian.service` stop line appears anywhere in `serial.log`. The line before them is garbled by
  terminal escapes (an OSC 3008 context sequence), so a console line may be lost there.
- At about 74 s there is a deliberate OOM kill in `aresos-ci-pressure.scope`, an older check. It is probably
  unrelated; confirm.

## Your job

1. **Find the cause from the evidence and the code, not by guessing.** It is one of these:
   - **(a) The guard really didn't save:** `ExecStop` didn't run, ran too late, or `aresos-desktop stop --reason
     shutdown` did nothing useful (stop ordering, the session scope or the user manager going first, the unit's
     environment, the socket path, the supervisor gone, and so on).
   - **(b) The harness missed it:** `guardian_host.watch` reads the wrong signal, starts too late, or reads a serial
     line that the console lost.

   Say which, with the lines that prove it. If the evidence can't decide, make the harness record what decides it
   (for example, the guard's own journal lines or a serial marker the guard writes) and fix what the code reading
   shows. If you can, reproduce the ordering locally with the unit and loop tests (`test_aresos_guardian*`,
   `test_guardian_vm`).
2. **Fix the real cause.**
   - For (a): this is the world's save at shutdown, which is real harm under decision 24, so fix it properly, with a
     test that would have failed.
   - For (b): never weaken what boot 1 and boot 2 must prove (brief, Acceptance). The VM must still show that the
     fixture received the save request and answered it before power-off.
3. **Run the tests by module name only**, under `env -i` as PROGRESS.md shows, with `python3 -B`:
   - run `test_aresos_desktop*`, `test_aresos_guardian*`, `test_guardian_vm` and whatever else you touch;
   - never run the whole `os/tests` suite, `test_owner_update`, `test_inherited_homebrew` or `test_sysusers`.
4. **Update `reviews/25-guardian/PROGRESS.md`** with the cause, the fix, and the evidence lines. Also put in the
   report draft in AGENTS.md format: the exact new texts for the owner, the new image files for the release diff, the
   Known limits, and every JUDGMENT-CALL. Leave the VM's measured times as "from the next check build". Step 8a's
   JUDGMENT-CALL goes in too: the laptop home window is not an app window for `covering()` and `app_windows()`.
5. **Commit this brief with your first commit**, in small logical commits, then `git push origin pkg/25-guardian` and
   stop:
   - don't start, watch or wait on any GitHub run (the lead starts the next check build, which must pass before
     merge);
   - don't open the PR, don't merge, and don't message anyone.

   Commit trailer: `Co-Authored-By: Codex gpt-6.2-astra <noreply@openai.com>`.

## Rules

- **The machine:**
  - no sudo and no changes to the running system;
  - never touch the owner's session (`wayland-0`), `.minecraft`, Lunar Client or `~/AresOS-try`;
  - no client-test runs;
  - never write in `~/AresOS`.
- **The repo is public:** no personal details.
- **The safety bar (decision 24):** real harm (the world's save, data loss, system changes) gets fixed. Low-harm edge
  cases go under Known limits.
- **Your last message:** under 250 words, giving (a) or (b) and the proof, the fix, the tests and their counts, the new
  head SHA, and any JUDGMENT-CALL.
