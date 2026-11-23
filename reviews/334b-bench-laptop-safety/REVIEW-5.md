# Review 5: 334b, final check of round 4

**Verdict:** SAFE

## Must fix

None. The round-4 diff introduces no blocking harm under the stated laptop safety bar.

## Known limits

- The watcher fixture now signals through owned pidfds, removing the recycled process-group risk. Its fallback still has a gap. In `os/tests/test_bench_laptop_watch.py:99`, Python’s `socket.recv_fds` ignores `MSG_PEEK`. A socket probe confirmed that the first read consumes the descendant’s handle. If the fixture guardian dies between receiving the handle and signaling the descendant, the fallback can miss that stand-in. Production shutdown uses a pinned cgroup.
- Live Btrfs allocation peaks and real user-scope timing remain unverified in this review.

## Checked

- REVIEW-4’s must-fix is implemented in `os/ci/bench/store.py:350`. Managed writes, fixed disks, and polled outputs all use the same helper. On Btrfs it sets No_COW on the parent and checks the empty output before writing data. Verified inheritance permits one peak plus margin. Missing or unreadable No_COW and unknown filesystem types charge two peaks plus margin. The polled file ceiling uses the same multiplier. All 18 mocked admission checks matched the expected reserve boundary.
- REVIEW-4’s should-fix is implemented in `os/ci/bench/laptop.py:338`. A forced stop fails the phase after the scope empties, even when the foreground command returned zero. Read-only probes confirmed that command evidence stays unpublished and that recovery removes its partial file while preserving finished `Phase.write` evidence.
- Ran the requested `python3 -B -m unittest discover` commands one at a time. `test_bench_laptop_store.py` reported 19 setup errors and `test_bench_laptop_watch.py` reported 21. The read-only worktree rejected temporary fixture creation with `Errno 30` before any test body ran. `git diff --check 6221b5f3..HEAD -- os/` passed.
