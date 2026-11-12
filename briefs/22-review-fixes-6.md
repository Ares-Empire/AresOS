# 22: review fixes, round 6: no gap at the entry

Follow-up on `pkg/22-update-route` (PR #32). Read `reviews/22-update-route/REVIEW-6.md` (CHANGES-NEEDED). Recovery-first holds inside the code, but:

1. **High:** after `tools → .tools-held`, the documented entry `/var/lib/ares/at` dangles, so no installed command can reach `settle_tools()`, and a failing USB bootstrap leaves nothing working. The test hid this by calling an already-loaded `main()`.
2. **Medium:** a missing `/proc/<pid>/cwd` doesn't prove the process is gone. A thread group whose main thread called `pthread_exit()` keeps live workers.

**Direction for 1:** remove the gap rather than recover from it.
- Prefer a layout where the documented entry **always** reaches a complete, verified toolset, or a small trusted recovery launcher that lives **outside** any directory that gets swapped. For example, versioned tool directories, with the entry switched by an atomic rename of a symlink or a tiny launcher. The legacy 15f tools then stay put until the new ones are live, and "blocking" the legacy tools means atomically pointing the entry at a busy/recovery launcher rather than moving their directory.
- Whatever you choose, the 15f constraints from earlier rounds still hold: its `main()` refuses outside `/var/lib/ares/tools`, the bootstrap's fingerprint check stays, and the legacy exclusion stays at least as strong.
- If the old layout must stay, add a trusted recovery launcher outside the swapped directory that the documented entry falls back to.
- **Tests** run the **real subprocess entry** (`bash /var/lib/ares/at …`) right after every cut and after every kind of bootstrap failure (mount, copy, verify). It must reach a working toolset or the recovery route every time. Never call an already-loaded `main()` for this.

**For 2:** distinguish a confirmed kernel thread (e.g. no `mm`, PF_KTHREAD in `stat` flags) and a fully exited process (zombie, or the whole thread group gone) from a surviving thread group. Count the uncertain case as in use. Add a live-worker regression (main thread exits, a worker holds a tools file) beside the zombie test.

Keep the fingerprint, the pins and `pending-rebind.json` exact. Rerun the focused owner suites. Run a full WSL suite only with at least 5 GB free and nothing else heavy running: Claude Code kills background work when memory runs low. If it can't run, say so. Add a "Review fixes 6" section to the REPORT, then push.
