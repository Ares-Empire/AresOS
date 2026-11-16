# Brief 20-ci-noise: two Chrome CI fixes

Lead: `linux-tools`, 2026-11-15. Builder: a Claude agent on Opus (small, tight brief). Then a fresh reviewer on Opus.
Source: `docs/control/TOOLS-HANDOFF.md`, sections "Main fix merged" and "Popup races merged" (notes from
`mac-aresos-control`, 2026-11-15). Branch `ci/20-ci-noise`, worktree `~/AresOS-20-ci-noise`, one draft PR.

## Item 1: the failing-groups issue names only this run's results

**Today.** `qualify.py notify` lists failing groups over the whole append-only record. The old build `4c1eccb9…`'s
all-false beta entry (issue #74's cause, fixed by P4) is therefore reported on every run, so #74 can't be closed.

**Change.**
- "Chrome qualification has failing groups" lists only the entries this run published: `entry['run']` equals
  `GITHUB_RUN_ID`.
- Notify runs only on main, where the variable is always set. If it is missing or empty, notify refuses
  (`SystemExit`) instead of reporting the whole record.
- The shipped-copy issue ("Update shipped Chrome qualification record") stays as it is and lists every entry on the
  data branch.
- The trust path doesn't change: validation, attestation and publishing are untouched.

**Tests** in `control/chrome_tests/test_publisher.py`:
- an earlier run's failing entry is not reported;
- this run's failing entry is;
- with no failing entry from this run, the failing-groups issue gets no new issue and no new comment;
- a missing run ID refuses.

After the merge the lead closes #74.

## Item 2: the latency gate measures the product, not the runner's disk

**Evidence.** Six latency jobs failed on p95 tails alone; the run numbers are in the handoff's "Latency gate and the
runner's disk".
- Their medians were normal, and nothing regressed against the reference.
- In every slow sample H5's stages put the extra time in `store_write` (up to 940 ms against a median of
  10–50 ms), while `bridge_round_trip` and `extension_total` stayed normal.
- Re-runs were clean.

The gate is timing the shared runner's disk sync.

**Change**, in `control/chrome/ci/latency-pair.sh` and what it starts:

1. **Store on a tmpfs.** During the timed phases, the service's store (its journal and SQLite files) lives on a
   tmpfs, for both legs (reference and candidate), so they compare like for like.
   - Find where the store lives today inside the container (`docker run` already has a `/scratch` tmpfs and
     `--shm-size`).
   - Size the tmpfs from what a run writes, with room to spare.
   - The artifact states where the store was and that it was a tmpfs (check `/proc/self/mountinfo` or `stat -f`,
     don't assume).
2. **A count gate for disk syncs.** Per call kind, the number of fsyncs (`journal_fsync`'s count) and the number
   of SQLite commits in the candidate must not exceed the reference's. These counts are deterministic, so a change
   that adds disk syncs is still caught exactly.
   - If H5's stages don't count them yet, count them in the probe only (behind `LATENCY_PROBE`). The product's
     behaviour stays unchanged.
   - Show that the gate can fail: a test of the comparison with an added fsync fails it.
3. **Ceilings and sample counts stay as they are.** The timing gate stays on; only what it times changes.

**Conflicts.** PR #72 (`dceafc94`, the efficiency mode) and PR #76 (`32f1126c`) also change `latency-pair.sh`. Keep
this change small and local, so their merges stay easy.

## Rules

- Never merge, never push to `main`, never force-push, never `--no-verify`.
- The repo is public: no personal data.
- No Node, containers or root on the laptop: JavaScript and the latency pair run only in CI. Python tests run
  locally.
- Push at most twice (each push starts the Chrome workflows). Commits that touch only docs carry `[skip ci]`.
- Stop processes only by PID.
- Keep `reviews/20-ci-noise/PROGRESS.md` (done, runs, what the code doesn't show, JUDGMENT-CALLs, PLAN-GAPs).
  Its full text becomes the PR description at the end.
