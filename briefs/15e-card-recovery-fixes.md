# 15e: Emergency-card layout recovery fixes; keep the mounted-child runtime check explicitly open

Follow-up on branch `pkg/15-owner-path` (PR #14). Briefs 15 to 15d still apply. Read `reviews/15-owner-path/REVIEW-3.md` (CHANGES-NEEDED at `e074f6e`).

All three points are accepted. These are document and test changes only. **No change** to the tools, payload, harness, workflows or Windows helpers: `git diff 79a67d2 -- os/owner-tools docs/install-tools .github os/ci` must stay empty.

1. **No second abandon.**
   - Add a completion anchor right after the `layout abandon` command and its PASS line in INSTALL-PROCEDURES. Link the card's "after PASS" to that anchor, not to the start of the procedure.
   - The procedure also covers "already abandoned": if `layout abandon` refuses with `Missing private layout-pending record` after you already saw `PASS layout abandon`, go to the completion anchor. Any other refusal goes to Help.
   - Test the whole card → procedure route, including the already-cleared state.
2. **Distinguish an interrupted finish.** Separate an interruption during `layout begin` or `revert` from one during `layout finish`.
   - **During `layout begin` or `revert`:** the login uses the last confirmed layout.
   - **During `layout finish`, before `PASS layout finish` appeared:** the console may already use the new, proven layout. Give a bounded route:
     1. Try the last confirmed layout once.
     2. If the login fails, try the proven new layout once. The proof already showed the password types on it.
     3. Then go to Help.
     4. After logging in, run `layout abandon`, which handles the interrupted-finish state, and use its PASS line and returns.
   - **Check the lockout limit.** Find the installed image's actual `pam_faillock` (or equivalent) settings from the retained evidence or source, and make sure the route stays well below any lockout threshold. State the threshold in the reference.
   - Test both branches in the owner-path tests, instead of requiring the old-layout wording unconditionally.
3. **Council RECHECK condition.**
   - In INSTALL-STATUS.md, list the "protected child mounted at runtime, refusal with zero mutations" check as **OPEN, synthetic evidence only**. What closes it is a native runtime check: a real loop fixture with a mounted protected child partition, refused with zero mutations, added by maintainers to a probe before release.
   - Keep package 14's VM acceptance described accurately as met.
4. **Run:**
   - the owner-path, equality and full owner suites in WSL, with and without `-B`
   - the Windows Pester test
   - the pinned gitleaks
5. **Then:** commit, push once through the privacy hook (fast-forward only, never `--no-verify`), and add a 15e REPORT section. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 15 Codex session).
