Reviewed PR #70, the fix step `5c9d2be6..ddffc4cb` (23b).

Reviewer: a fresh Claude agent on Opus 5.5, read-only; committed by the integrator from its final message (the per-question evidence is shortened; every finding is kept as written).

**Verdict: SAFE.** All three should-fixes from review 1 are fixed correctly and tested: finding 1 (the build rebuilds the font cache, and the VM proves the font), finding 2 (a retry out of AUTH_REQUIRED is never covered), finding 3 (a restart under the cover lets the restarted hub take the focus). Each test fails when its fix is reverted. Package 23's keep-foreground guarantee is still asserted for every uncovered case. The VM picture and the window titles are now Space Grotesk. Left: three wording nits and one documented edge, none blocking.

## Answers (short)

- **Q1, the font cache.** `os/build.sh:236` runs `fc-cache --system-only --really-force` in `configure`, after `config/` (the only AresOS font) is copied; nothing later touches fonts. Reproduced in a scratch fontconfig: a stale cache at mtime 0 gives Noto; the rebuilt one gives Space Grotesk, and a stale user cache loses to it in either cachedir order. The VM check (`checks.py:366`, as ares in the session) proves the drawing font; run 43683452542's `cover-result.json` names the aresos file for both faces; the committed screenshot is byte-identical to the run's and is Space Grotesk. Title bars: between review 1's run and this one the only changed pixels are the title text; a font-match score moved from Noto (12.1 vs 33.2) to Space Grotesk (30.2 vs 14.4), so package 31's titles are fixed too. `release_diff.py`'s `generated_rule` already lists every `usr/lib/fontconfig/cache/*` change as generated (its reason text "fontconfig cache trigger" becomes inexact); the release's own VM pass is what proves the font for a published image.
- **Q2, AUTH_REQUIRED retry:** right (`aresos-desktop:1855`, `self.state` still AUTH_REQUIRED, also after `restore()`), tested in four cases; the old `COVER_AGAIN` mutant fails exactly that test.
- **Q3, keep-foreground:** correct whenever the cover is gone before the restart begins (shortcut, Prism wait, world_ready, the cover's own end, never started, a supervisor restart). One edge: nit A. Package 23's test keeps every main assertion for each uncovered case; mutants M1 (condition removed) and M3 (never set) fail as expected.
- **Q4, JUDGMENT-CALLs 1–7:** complete and true against the code; wording: nit B.
- **Q5:** nothing blocking missed.

## Findings

### A. nit: the focus edge when the cover ends during the restart
- **Where:** `os/config/usr/libexec/aresos-desktop:1362`; PROGRESS JC2.
- **Why:** keep-foreground is decided when the restarted helper starts. If the cover then ends while the restarted Minecraft is still loading (Super+Ctrl+Escape, or the 25 s Prism wait), Minecraft's window takes the focus when it appears, as at a normal start; before 23b an automatic restart would have kept his window in front. A few seconds' window; the focus moves once; nothing is lost.
- **Fix:** one plain sentence in JC2. No code (restarting the helper from `hide_cover` would spend helper-restart budget for a few-second edge).

### B. nit: JUDGMENT-CALL wording for the owner (`PROGRESS.md:325-366`)
- JC6 is stale: run 43683452542 proves the font; turn it into "fixed and proven" or drop it.
- Code names in owner text (JC2 "state STARTING, reason `restarting`"; JC3 "`new_session`", "one condition in `start()`"): replace with words or move to the integrator notes.
- JC2's "…instead of Mojang's loading screen a second time, or the recovery window after a third crash" reads ambiguously; suggested: "…until the hub is ready, or until the recovery window opens after a third crash, instead of Mojang's loading screen a second time."
- JC4 "Every retry except the one after a failed sign-in" overclaims; say "Every retry that starts the hub, except the one after a failed sign-in".
- JC4/JC7 could add that the uncovered sign-in retry shows Minecraft's own loading screens, as before 23b.

### C. nit: PROGRESS is stale after the integrator's runs
Record check build with VM 43683452542 (passed; fonts line; screenshot committed; titles now Space Grotesk) and checks-only 43683462810 (passed, 1583 tests, 4 skipped), and move on to "Left" items 2 to 6.

### D. info, for the release package
Give `usr/lib/fontconfig/cache/*` the 23b reason in the next release's diff. Keep the release job's VM pass (`check-build.sh build`): Fedora's `fc-cache` wrapper ignores failures and the build-time check runs with real folder dates, so the VM's `session_fonts` is the only guard.

Review 1's findings 5 (merge order with 22d and 40) and 6 (late SIGTERM, package 25) stay with the integrator.

## What I ran
No display; one module at a time. `test_aresos_desktop.py` on `ddffc4cb`: 186 OK (skipped=1). Mutants M1–M3 on a scratch copy. A scratch test for nit A's edge. Scratch fontconfig experiments. Read-only `stat`/`fc-cache --version`/`fonts.conf`. `gh run view` and `gh run download` for 43683452542 and 43673448694 (compared, then deleted).

SAFE
