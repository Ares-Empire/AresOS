# 21: review fixes, round 6, and the merge with package 24

Follow-up on `pkg/21-everyday-account-and-chrome` (PR #31). Review 6 (`reviews/21-everyday-account-and-chrome/REVIEW-6.md`) is SAFE with one Low, nonblocking finding. Package 24 (PR #33, the OS helper `aresos-shell`) is merged into main as `7cf0541b`, and PR #31 now conflicts with main in `os/build.sh`.

1. **Merge `origin/main` into the branch** with a merge commit (no rebase, no force-push).
   - Resolve `os/build.sh` by keeping both changes: 21's `chmod 0755` line with `/usr/bin/brew` and its `sudoers.d` line, plus 24's `/usr/libexec/aresos-shell`.
2. **Check that 21 and 24 work together:**
   - the helper's app files (`os/config/usr/share/aresos/apps/*.json`) reach 21's Chrome, KWrite and the terminals by absolute paths that exist in the image;
   - the helper works under the session's system PATH (JUDGMENT-CALL 9);
   - 21's audits (polkit, the updater audit, the PATH shadow check) accept the helper.

   If the in-image checks list session executables, add `aresos-shell`. Fix anything that doesn't fit, as narrowly as possible.
3. **Review 6's Low finding** (`os/ci/overlay/checks.py:89`): the profile assertion requires at least one noninteractive, non-login wrapper record before checking its PATH, so a missing probe fails.
4. Keep `pending-rebind.json` exact (regenerate it with `checkout_sources.records`) if any bound file changed.
5. **Evidence:**
   - Rerun the throwaway CI image build and its checks at the merged head, and record the run.
   - Run the focused suites.
   - Run the full WSL suites (plain and `-B`) only with at least 5 GB free and no other suite running; package 22's agent may be running its suites first. Use `pkg21-` names for scripts and `/tmp` paths.
   - The owner allows restarting a run that Claude Code stops for low memory once memory is free again (board #160).

Add a "Review fixes 6 and main merge" section to the REPORT, then push.

Owner answers so far: board #156 "Yes to all" covers JUDGMENT-CALLs 1 to 3. Calls 4 to 9 are asked as board #163 and still open.
