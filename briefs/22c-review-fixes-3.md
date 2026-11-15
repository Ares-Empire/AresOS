# 22c: review fixes, round 3 (stage 1b)

Review: `reviews/22c-ways-back-after-update/REVIEW-4.md` (gpt-6-astra high on `f3369b8d`, CHANGES-NEEDED: two blocking, two should-fix). It confirms the bundle, the pins, the waiting list, the start block, part F and the CI permissions. Three findings are in the guides' recovery routes, one in CI. Fix all four as the review prescribes:

1. **(Blocking) `check` before `previous`.** The failed-update card tells him to take the boot-menu row the last title named, then run `previous`. If the update never took effect, that row is another system, and `previous` goes one release further back. Fix the card (and every guide box with the same route): after any boot-menu choice, run `check` first; apply the "was not applied" and STOP branches however Linux started; run `previous` only when `check` shows the newer release is running and is the one he wants to leave.
2. **(Blocking) The "back from stock" box must not start an update.** With newer tools but no newer release installed, `update` on stock returns to the installed release and then says the tools' release is newer still, and the guide says to follow it, which stages a release without an announcement. The box ends once he is back on the installed release; staging a new release goes only through the announcement-gated route, and the box says so in plain words.
3. **(Should-fix) A return that changes nothing has its own completion.** When the system he wants already starts next, `update` writes no journal, so no "confirmed after the restart" line can follow. The guides tell the two apart: after a real change, the confirmation line; after nothing to do, `PASS check` with the intended system running and starting next.
4. **(Should-fix) Changed tools always get the full model.** A direct rehearsal dispatch runs only the slice, and the rehearsal guard accepts it without a full-model run on that head. Require, for a dispatch whose head changed the model's sources, a passing full-model run on the same head (or run the model job for those dispatches too), with a test of the direct-dispatch case.

For each: a test where the repository's tests can hold it (the guide-binding tests, the walk test, the guard's tests), and a note in the report. No rule of the owner tools changes; if a guide fix seems to need one, stop and report.

**Acceptance:** hosted checks-only with 0 failures, 0 errors, 0 skipped and the full-model job green; a section "Review fixes 3" in the report.

**Model:** a Claude agent on Opus (guides and CI with clear rules). Fix check: Codex if any is left, otherwise a Claude reviewer.
