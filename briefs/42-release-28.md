# 42: Release 28 (Minecraft at startup, the home screen, Control; installed by the tools without the stick)

Empire board brief 295. Release package. Steps 1 and 2 start before 22d is merged; the rest waits for 22d (the tools
version 4 and its folder route) and for the integrator's cut of the release commit from `main` (planned Thu–Sat
2026-11-19 to 21). Written 2026-11-15 by `linux-aresos`; the integrator fills in the cut commit and the list under
"What rides" before step 3.

**Builders:** from Tue 2026-11-17 10:53 Codex (the owner's Codex plan for its last days, relayed by `mac-capacity`
on 2026-11-15): gpt-6.1-sol xhigh per step, one fresh run per step, each keeping `reviews/42-release-28/PROGRESS.md`
(done, left in order, what the code doesn't show). If the VM rehearsal resists two rounds, the integrator moves it to
a Claude agent on Fable 5.2. **Reviews:** gpt-6-astra (high), a fresh context per review, after steps 1, 3 and 6;
the final review before the laptop is astra high, or a Fable reviewer if Codex has run out. This release reaches the
owner's real laptop.

**Steps** (each ends with a commit, a push to `pkg/42-release-28` and PROGRESS.md):
1. **Diff rules and the release job, from `main`** (needs nothing from 22d): A.3's new rules in
   `os/ci/release_diff.py` with unit tests; the `release_28` input and job (A.4's shape), with an input that builds
   and diffs against release 27 but cannot reach the publish step, so the diff can be checked before the owner's OK;
   the mod jar's pin renewed through `check_build=resolve` (A.2). One dry run of the job; every difference explained
   or listed as open.
2. **Control's rules** (after PR #58 and 18c-b are merged, if they ride): A.3's Control rules, `verify_release.py`
   binding `control/`, the manifest's `control` object and `record_build.py add` in the job. Skip if Control does
   not ride.
3. **The rehearsal mode** (after 22d is merged; main merged into the branch): B's walk as a `rehearsal=release-28`
   mode built from 22d's tools-local route and package 27's update route; its local walk and host-walk receipt.
4. **The cut** (integrator): main at the cut commit merged in, the dry run again, the diff summary to the owner.
5. **Publish** (after the owner's OK): A.4 and A.5's release record.
6. **Rehearsal runs and pins:** B's VM runs (budget in C), then the pins and guides.

## Why

The laptop runs release 27 (`ghcr.io/ares-empire/aresos@sha256:5fad242f…`, source `b216f28f`, since 2026-11-13)
with the owner tools version 2 (`851eb742…`); version 4 (`dcbc375f…`, package 22d) goes on in a short session of its own
before this release (owner, board #308, 2026-11-15: "Soon"). Since then `main` gained what the owner sees next: Minecraft starts as
the desktop (package 23), the startup cover (23b), its memory settings (23d), the home screen (packages 30 to 40),
the Ares-Crown window frame (31), and, with the owner's yes, Control in the image (18c Part A and 18c-b; board #286:
"Yes, if reviews pass"). This package builds that release, rehearses the owner's real route on it, and pins it.

**Owner OK needed before publishing.** His standing OK (2026-11-09) covered packages 21–24 only. This release goes
beyond them, so the builder stops after the image diff (step A.3) and the integrator asks him, with the list of what
rides, before the publish job runs. Installing it on the laptop stays his step.

## What rides

Everything on `main` at the cut commit. Every image difference must trace to a merged package (step A.3). Expected:
23, 23b, 23d, 30, 30b, 31, 32 to 37, 39, 39b, 40; 22c's and 22d's tools (in the bundle, not the image); Control's
image part (18c Part A, PR #58; 18c-b, PR #76; 18e, PR #69) **only if merged by the cut with its reviews passed**.
If Control is not on `main` at the cut, the release goes without it and the integrator tells the owner so; nothing
of Control is added on this branch.

Not in this release: 21b (backlight, power button; the owner's key test is open), Konsole, the labwc pointer-lock
backport, unmasking the two finalize units, the online `aresos update` (22d's step 2), 22e, 23c.

The `aresos` command (board #195 and #262: `aresos update` goes forward when a newer AresOS is installed, otherwise
stages the tools' release; one of the two per run, said before anything changes) is its own package (43, for the release
after this one; it needs a tools change, see `STATE.md`). It does not ride in this release.

## Build

### A. The release image

1. **Build from the cut commit** on the same pinned base (`ed93d215…`) and locks, through the reviewed build path.
   A new base image is out of scope.
2. **Pin renewals:**
   - The mod jar: a release build refuses a jar that is not its pin (`ARESOS_BUILD_KIND=release`), and the pin in
     `os/minecraft/desktop.lock.json` is still package 23's. Renew it with `os/ci/build-mod.sh --twice` on the
     pushed cut commit (two clean builds, equal bytes). Mechanical, not a JUDGMENT-CALL.
   - Prism, Fabric, Java, Chrome, `gh` (18c-b's lock, renewed by the lead each release) and the Fedora packages:
     renew a pin only if it has vanished upstream, as package 21's JUDGMENT-CALLs 4 and 10 did, and record each
     renewal as a JUDGMENT-CALL.
3. **Image diff** against release 27, as `releases/27.json`'s `image_diff` did (`os/ci/release_diff.py`). Every
   difference traces to a merged package or a renewed pin; an unexplained one stops the release. New rules it needs:
   - `/usr/lib/fontconfig/cache`: rebuilt on purpose by 23b's `fc-cache --system-only --really-force` (on an ostree
     deployment `/usr/share/fonts` has mtime 0, so the base's stale cache hid `/usr/share/fonts/aresos`).
   - `gschemas.compiled`: package 31's override. Compiling rebuilds every default, so list each default that
     changed and trace it; only package 31's keys may differ.
   - Package 23's files (Prism, the instance template, the supervisor, its units), 23b's cover, 40's `rc.xml` rules.
   - Control, if it rides: `/usr/share/aresos/chrome/` as per-build (from `control.json`), `gh` from its lock, the
     `aresos-tools` user and group (fixed UID/GID 250) in the account rows, the polkit action, links, files and the
     tmpfiles line (18c-b's "For your next release").
   - A theme change moves its checksum in `os/ci/image-checks.sh`: confirm it matches package 31's.

   **Stop here** and hand the integrator the diff summary for the owner's OK.
4. **Publish** privately to `ghcr.io/ares-empire/aresos`, keyless-signed by this repo's workflow, from a publish job
   for `pkg/42-release-28` with the same reviewed shape as `release_27` (an input `release_28`). Don't loosen it into
   "any branch may publish". Record the signature identity. Delete nothing from GHCR; keep old release records.
   `verify_release.py` binds `control/` as it binds `os/` when Control rides.
5. **Records:**
   - `os/manifest/releases/28.json` with digest, signature proof, run and image diff; when Control rides, the
     top-level `"control": {"source_revision": …, "chrome_build": …}` from the image's `control.json`, and the
     release job runs `control/chrome/record_build.py add` (the pinning pull request carries the row);
   - append the release to `os/owner-tools/history.json` with `daily_wheel: true`;
   - regenerate the payload and the tools fingerprint (`bundle.py --refresh`) and move every pin: `docs/INSTALL.md`,
     `docs/OWNER-TOOLS.md` (line 1 and 2), `commands.json`, `EMERGENCY.md`, INSTALL-STATUS, the pending list.

   **The order is build, owner OK, publish, rehearse, then pin.** `os/manifest/release.json`, the guide's digest and
   `OWNER-TOOLS.md` change only after the rehearsal passes.

### B. Rehearsal: the owner's route, in a VM

The two-disk VM harness (a stand-in Windows disk that is never written), with 22d's tools-local route and its
stand-in origin. Start from **the laptop's state**: R27 booted, the release before it as rollback, stock pinned,
the tools the laptop has when step 3 starts (version 4 after the owner's 22d session; the integrator records which in
PROGRESS.md; if that session has not happened, version 2). Then walk the guides' route exactly as the laptop session will:

1. **Tools, from Claude's terminal** (22d): the folder line and the routine line at the announced commit on the
   stand-in origin's `main`; the password window approved; the 8 characters equal line 1 of `OWNER-TOOLS.md`. This
   proves the laptop's installed tools to the new bundle (version 4's code with R28's reference, so a new fingerprint).
2. **Before the update** (only when Control rides): root writes the made-up sites list
   `{"format":1,"hosts":["rehearsal.invalid"]}` to `/var/lib/aresos-control/chrome-excluded-sites.json` with
   `sudo tee` as the guide does (making `/var/lib/aresos-control/` `root:root` 0755 first if R27 lacks it), and
   records its SHA-256 (18c-b, "Requested after review 2"). The check must be able to fail.
3. **On the console** (22d's N10: these stay on the console in this release): `at update`, `at title`, `at reboot`;
   the boot-menu choice the guide names; `at check`. Then on R28's real boot:
   - package 21's rules still hold (wheel, `sudo` asks every time, no passwordless rule, his PATH);
   - Minecraft starts as the desktop, in its game scope with memory.high 2684354560 (23d);
   - the cover draws in Space Grotesk (`fc-match` in the VM, not the build-time check), and package 31's frame is
     the active theme;
   - Control, when it rides: `aresos-tools` has UID/GID 250, its state folders have the right owners, its service
     never delays login, `release_checks.py` passes and the sites list's hash is unchanged.
4. `at previous`: back to R27, `at check`, the sites list's hash unchanged. Then forward again by the guide's route
   (`at forward`), so the walk ends on R28 as the laptop will.
5. **Audits at every stage**, all of package 11's: the stand-in Windows disk and its boot entry byte-identical; stock
   untouched and pinned; no deployment lost beyond what 22's JUDGMENT-CALL 1 allows.
6. **Bindings:** the pending list ends empty; `source-bindings.json` exactly as the walk records it.

After it passes: pin the release in `release.json` and the guides, mark the update-route gate in INSTALL-STATUS with
the run links, keep `EMERGENCY.md` consistent. The guides say what he notices after `previous`: R27 has no
Minecraft desktop at all, so he gets R27's desktop; the home screen's files in his home stay and are used again when
he goes forward (check this on the walk's return to R28: the instance and `apps.json` survive the round trip).

### C. Verification and budget

- Unit tests for every changed rule; `test_checkout_sources`, `test_owner_equality`, `test_owner_step_limits`,
  `verify_release`. Locally one module at a time; the hosted checks-only run with the full model.
- **Budget** (public repo, standard runners, no cost): one release build, one publish, one checks-only suite, three
  rehearsal runs. Report before dispatching more; the integrator tells `mac-capacity` early. Stop if anything would
  need a paid runner or other spending.

## The laptop session afterwards (not this package)

**Lead's note (2026-11-16, from 43's review 1, S2):** on release 28 the login starts no `foot` (labwc's autostart runs only the polkit agent and `aresos-desktop session`), but tools version 4's `check` requires a `foot` of `ares` (`os/owner-tools/owner.py:2017`). So after the update, `at check` (and the routine line's check) STOPs while the hub is in the world unless a terminal is open. The VM rehearsal cannot show it: without a Minecraft account it sits in SETUP, which shows a `foot`. Until package 43's tools (D19) are on the laptop, the guide's R28 steps and this session say "open the Terminal app first, keep it open until the PASS lines", and B's walk adds one `at check` with no `foot` running that must STOP with the expected line (so the guide's wording is proven).

The integrator posts the board note with the announced commit and the fingerprint. Claude runs the folder and routine
lines; the owner approves the password window after comparing the 8 characters; then he runs `at update`, `at title`
and `at reboot` on the console, guided. Afterwards: the 23d check (the game scope's `memory.stat` anon and
`memory.events` high) and the owner's look at the home screen.

## Rules

- `AGENTS.md` applies. Push `pkg/42-release-28` only and open a PR. Never merge, never push to `main`, never
  `--no-verify`.
- The repo is public: no personal data, serials, GUIDs, emails or tokens. The image stays private. Never make anything
  public. Don't touch the laptop's disks or boot settings. Don't touch other worktrees.
- Commits name the builder and its model in a trailer (AGENTS.md).
- `gh run watch <id> --exit-status --interval 60` at the most often; dispatch one run per branch at a time (the
  workflow keeps only one pending run per branch).
- The report `reviews/42-release-28/REPORT.md` (a Claude builder leaves it in `PROGRESS.md`; the integrator commits it) in the AGENTS.md
  format, JUDGMENT-CALLs marked. Evidence: digest and signature proof, the image diff with every rule's reason, the
  rehearsal transcripts and audits, the emptied pending list, the fingerprint, the test results, the budget table.
