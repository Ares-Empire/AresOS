# Review 1: 334b, the bench's laptop safety pieces

**Verdict:** CHANGES-NEEDED

## Must fix

1. **The start gates accept unreadable or malformed input.** `os/ci/bench/laptop.py:41` skips permission errors on Lunar executable links, treats an unrecognized battery type as a non-battery, and accepts any readable and writable path as KVM. The memory parser accepts a valid reading followed by a conflicting malformed one, and the PSI parser accepts a truncated record. The final memory reading also happens before the other gate reads and before systemd activates the scope. These paths can admit work when the owner’s game or the laptop needs protection. Validate each gate’s input, distinguish vanished or foreign processes from unreadable owner processes, verify that the KVM node can be opened, and repeat the memory check at the scoped command’s exec boundary. Gate refusals should return 75.

2. **Scope shutdown trusts the name without proving ownership.** `os/ci/bench/laptop.py:226` and `:257` call `systemctl stop` even if the launcher failed to create the scope. A conflicting unit with the exact generated name can therefore become the stop target. Shutdown also ignores a failed `systemctl stop` and treats a missing file at a guessed cgroup path as proof that the tree is gone. Bind shutdown to the scope invocation and cgroup created for the launcher. Treat an unverified scope as a shutdown failure and keep cleanup blocked until the owned tree is confirmed empty. [systemd scope launch source](https://github.com/systemd/systemd/blob/main/src/run/run.c)

3. **The guardian can die on its own and leave the workload running.** `os/ci/bench/laptop.py:303` treats guardian exit as the end of supervision. If the guardian is killed while the scope is live, the watcher reaps it and unwinds the phase. That can unlink a test disk with a live writer and release the shared lock while the workload still runs. Add an independent stop path for guardian loss and retain the lock until shutdown is confirmed. Add a guardian-only SIGKILL test alongside the existing watcher-only test.

4. **The declared disk peaks do not bound the launched workload.** `os/ci/bench/store.py:147` admits declared peaks and `:288` enforces them for `Phase.write`. `os/ci/bench/laptop_cli.py:16` then accepts an unrestricted command and relies on it to bound its own writes. A stand-in can grow an overlay, scratch file, Podman temporary output or evidence beyond its declared peak and consume the 20 GB reserve. Require an enforced budget for every writable destination before launch and refuse unbounded phases. The check can be proved with a file-writing stand-in.

5. **Deletion can escape the bench’s owned directories.** `os/ci/bench/laptop_cli.py:51` resolves `XDG_CACHE_HOME` before validation, accepting relative paths, `/`, and symlinked parents. `os/ci/bench/store.py:120` lets a registry record nominate any absolute path as a worktree. The filename hash is derived from that same path, so it proves no ownership. `clean`, evidence pruning, and interrupted-phase recovery then use that registration to select deletion targets. The path checks also precede path-based removal, and the device check misses mounts at the deletion root and same-device bind mounts. Reject unsafe cache roots, verify store and evidence ownership independently of the records, and anchor recursive deletion to verified directory handles with symlink and mount boundaries enforced.

## Should fix

- Report `unknown` for missing or malformed game cgroup events. `os/ci/bench/laptop.py:88` can report `idle` on those inputs, which later code could use to give the guest more CPUs.
- Preserve completed evidence on next-run recovery. `os/ci/bench/store.py:164` removes the entire evidence run after a hard kill, including files that `Phase.write` already finished. `clean` can still remove the full run.

## Known limits

- Build-cache expiry runs on the next locked phase or explicit expiry check. An idle laptop has no scheduled seven-day cleanup in this package.
- Real user-manager behavior, workload containment, memory pressure and stop timing remain step 6 checks. Real write peaks remain a step 7 check. The brief also assigns lock adoption by `build.sh` and `run-hub.sh` to step 6.

## Checked

- Reviewed `git diff origin/main...HEAD` against the brief and its named design sections. `git diff --check origin/main...HEAD` passed. The `AGENTS.md` changes match the brief’s narrow store exception and one-copy rule.
- The normal path uses the dev rig’s client-test lock at the same location and returns 75 on contention. The test sources use fixture paths and stand-in processes they start.
- Ran `python3 -B -m unittest discover -s os/tests -p 'test_bench_laptop_<name>.py'` one module at a time. Gates, store and watcher reported 6, 10 and 5 setup errors respectively. All failed with `Errno 30` when creating temporary fixture directories in the read-only worktree. No test body ran.
- Read-only mocks confirmed that malformed readings and a denied Lunar executable read can pass the gates, relative and root cache paths are accepted, an unrelated evidence path can be registered, and a failed stop can return as complete. No live bench store, shared lock, systemd unit, VM or container was used.
