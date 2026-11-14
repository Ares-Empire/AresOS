# Package 30 — installed programs (steps 1–4)

## Every `os/` file touched

- `os/config/usr/libexec/aresos-shell`
- `os/config/usr/share/aresos/apps/browser.json`
- `os/config/usr/share/aresos/apps/terminal.json`
- `os/config/usr/share/aresos/apps/notepad.json`
- `os/ci/image-checks.sh` (one separate, additive package-30 block)
- `os/tests/test_aresos_shell.py`
- `os/tests/test_aresos_shell_discovery.py`
- `os/tests/test_aresos_shell_windows.py`
- `os/tests/test_aresos_shell_icons.py`
- `os/tests/test_aresos_shell_protocol.py`
- `os/tests/check_aresos_shell_icons.py`
- `os/tests/check_aresos_shell_headless.py`
- `os/tests/fixtures/installed-programs/README.md`
- `os/tests/fixtures/installed-programs/lunarclient.desktop`
- `os/tests/fixtures/installed-programs/org.mozilla.firefox.desktop`
- `os/tests/fixtures/installed-programs/com.discordapp.Discord.desktop`
- `os/tests/fixtures/installed-programs/steam.desktop`
- `os/tests/fixtures/installed-programs/btop.desktop`
- `os/tests/fixtures/installed-programs/foot.desktop`
- `os/tests/fixtures/installed-programs/drawn.png`
- `os/tests/fixtures/installed-programs/drawn.svg`

Other package files: this report, `docs/design/OS-BASE.md` Appendix B1, the brief/progress history, and `headless.json` plus two screenshots beside this report. The unchanged package-34 examples were copied into this branch before step 1; step 4 only reads them. The main merge brought in packages 32/33 and their existing mod work; this package adds no mod implementation changes. No source bindings, owner tools, live configuration or other worktree were edited.

## Done

**Discovery and launch (A1–A4, step 1).** The helper merges reviewed starters with desktop entries in the five specified directories, recursively forming desktop-file IDs without following directory symlinks. Earlier desktop IDs reserve their override even if hidden, malformed or unusable. Reviewed IDs and `replaces` win, so browser/terminal/notepad keep their saved IDs. Each desktop file is bounded to 1 MiB, UTF-8 replacement and the main group only. Visibility, desktop, executable and TryExec rules apply; malformed entries log individually. Discovery is deterministic and capped at 256 combined programs.

Discovered commands use the existing Exec grammar without a shell, remove complete empty Flatpak forwarding groups, resolve the executable once, honor absolute Path or use HOME, and wrap terminal programs with the single `TERMINAL_COMMAND` definition (Foot today). Every launch uses an independent `app-aresos-…scope` under `app.slice`, with private variables and all six inherited GPU variables removed. Requested discrete graphics adds exactly the supervisor's three NVIDIA variables only if the same driver-presence test succeeds. Tests compare the actual supervisor/helper GPU constants.

**Windows (A5, step 2 and the step-4 real-check fix).** Reviewed identity and single/multi behavior are preserved. Discovered identities use StartupWMClass, desktop stem, Flatpak ID and executable basename, with earlier claims winning; terminal apps claim only their private Foot ID. Clean early exits can hand over to a resident process; live/unknown scopes defer a false no-window failure. Closing the last window, including dialogs, ends the launch and returns a foreground app even while its scope lives. Clicking again starts a new scope that can restore a resident window.

An identified, newly appearing window with no explicit owner can join the sole live discovered program, conservatively blocked by another possible program or unresolved reviewed launch. Lifetime ownership survives launcher closure. Event replay tests cover every byte split and ordering of launcher/game appearance, both closes and compositor refocus. The real headless check exposed a delayed close return stealing focus from a newly opened second app. The fix clears pending return intent when the compositor has already activated the desktop; a regression test opens btop within the first program's close grace and verifies it keeps focus.

**Icons (A6, step 3).** Named icon lookup searches the specified roots, hicolor then breeze, raster sizes through 256 then scalable; named paths cannot leave their root. Absolute Icon paths are accepted as written. One background worker converts bounded PNG/SVG snapshots to 128×128 RGBA PNGs with aspect preserved and transparent padding, writes mode-0600 files atomically in a mode-0700 cache, and publishes results independently. Filenames hash source path, size and nanosecond mtime; stale results cannot attach to a changed catalogue.

The converter is mandatory bubblewrap → explicit ImageMagick `png:`/`svg:` → `PNG32:-`, with the SVG row verified as librsvg/RSVG, never MSVG. The sandbox unshares network, drops capabilities, clears environment and mounts only the bounded input, private policy, binary/libraries and minimal devices. No external delegates, filters, home, session sockets or neighboring files are exposed. Resource limits, independent timeout, output cap, process-group termination and child reaping bound failures. An additive image check requires ImageMagick, bubblewrap, PNG and the librsvg-backed SVG coder.

**Interface (A7, step 4).** Minor 1 offers `app_details`, `apps_changed`, `list_paging`, and exposes ordered pages with optional signed cursors and `next`. Byte accounting includes the negotiated envelope, longest request ID, UTF-8 encoding and newline, staying within 64 KiB. Metadata covers all five source kinds, normalized icon paths, bounded categories/generic names/keywords, desktop ID, executable basename or Flatpak ID, and terminal status. A starter takes presentation from the first installed replacement in its declared order while retaining its own launch/window definition. No command, arguments, environment or source file path is sent to the game.

A stat fingerprint checks directories, desktop/registry files and executable dependencies at most every three seconds, including when listing. Unchanged inputs are not reparsed. It detects additions, edits, removals and executable permission/install changes. Rescans retain icons until updated and retain removed active definitions for window/scope lifecycle bookkeeping. The base catalogue revision stays separate from the picture revision; each accepted arrival/change emits `apps_changed` only to an offering, negotiated-1.1 desktop. The worker is stopped with the server.

Minor 0 retains the original starter-only fields, registry revision, capabilities, one-reply list and launch access; discovered apps are refused even by ID or replay ID. Future 1.x envelopes and optional fields remain acceptable. `--list` retains its reviewed-registry diagnostic contract, including the existing image check. Production discovery is enabled by `build()`; state-machine unit tests can still inject a registry without reading the host's applications.

The new protocol module reads every unchanged JSON example and checks hello, full/minimal entries, all source kinds, first/next requests, first/last reply envelopes and the event. Opaque example cursors/revisions/paths are documented as made up; tests use real issued cursors. Other tests cover byte limits with 256 large Unicode entries, stale/forged cursors, list/picture changes, cheap polling, stable digests across Python hash seeds, replacement policies, live uninstall, both helper-side version directions and the CLI contract. The newer mod against release 27's helper remains package 34's compatibility test.

Appendix B1 takes over HUB 3.8 in full, plus a paragraph on discovery; the helper header documents 1.1. HUB 3.8 and the unchanged example README govern where the brief is less precise.

## Verified

Commands below ran from this worktree. Local logs are ignored files in `.work/30-installed-programs/`; committed real-socket evidence is [headless.json](headless.json). Only helper modules ran locally in step 4; no full local OS suite, owner tools, Gradle, system install or elevated command was run.

### Step 4 local checks

`TMPDIR="$PWD/.work/30-installed-programs/tmp" python3 -m unittest discover -s os/tests -p 'test_aresos_shell*.py'`

| Local log | Result |
|---|---|
| `helper-step4-first.log` | 176 tests, failures=7, errors=23: newly enforced 1.1 access met A5 fixtures still negotiating 1.0; obsolete maximum-minor assertions also failed. Updated fixtures to negotiate 1.1 and the specific maximum-version expectations; preserved their behavioral assertions. Unknown-app journaling was restored before the next run. |
| `helper-step4-second.log` | `Ran 193 tests in 19.049s`, `OK` |
| `helper-step4-final.log` | `Ran 193 tests in 22.807s`, `OK` |
| `helper-step4-review.log` | `Ran 196 tests in 18.914s`, `OK` |
| `helper-step4-headless-fix.log` | `Ran 197 tests in 20.713s`, `OK` |
| `helper-step4-accepted.log` | **`Ran 198 tests in 19.585s`, `OK`, zero skips** |

The original test module changes only the obsolete future-client maximum-minor/capability expectation. Discovery's temporary “not yet exposed” test now proves the real negotiated boundary. A6's temporary MINOR=0 assertion becomes MINOR=1. A5 fixtures negotiate 1.1 to test discovered apps, and gain the focus regression above. Existing socket ResourceWarnings and the deliberate conflicting-reviewed-identity log remain visible, not suppressed.

`TMPDIR="$PWD/.work/30-installed-programs/tmp" python3 -m unittest discover -s os/tests -p 'test_aresos_shell_protocol.py'` → `Ran 21 tests in 0.474s`, `OK` (`helper-step4-cli.log`).

`TMPDIR="$PWD/.work/30-installed-programs/tmp" python3 -m unittest discover -s os/tests -p 'check_aresos_shell_icons.py' -v` → **`Ran 6 tests in 0.442s`, `OK`** (`helper-step4-converter.log`). These use the actual installed sandbox/converter, verify alpha/aspect/pixels and atomic permissions, misleading names, corrupt/huge input, absent-sandbox refusal and blocked neighboring-file/network reads. They are explicit checks outside hosted Ubuntu's portable `test_*.py` pattern.

`bash -n os/ci/image-checks.sh` and `git diff --check` → exit 0. `git fetch origin main` followed by `git merge origin/main` → clean merge `53af951c`; no conflicts or OS changes came from that merge. All commits have `Model: gpt-6.1-sol` trailers; pushes used the privacy hook.

### Headless end to end

`python3 os/tests/check_aresos_shell_headless.py` → **`HEADLESS_KCALC_BTOP_PASSED`**, then **`owned processes and scopes stopped`** (`headless-acceptance.log`). Before that run `free -g` showed **7 GB available**, and `/proc/*/exe` inspection found no Java executable beneath the owner's Lunar directory. Every earlier compositor attempt also passed the memory/game guard.

It starts its own headless labwc with pixman in `.work/h30/r`, its own HOME/config/cache/state/tmp, a stand-in `aresos-desktop` Foot window, and this worktree's helper/socket. The private runtime links only the existing user manager's `systemd/private` socket so the test can create its own scopes; no manager environment is imported and no real-session compositor/config/input is touched. Its private display is named `wayland-0` **inside that private directory**, never `/run/user/1001/wayland-0`.

KCalc is installed here as a Flatpak, not `/usr/bin/kcalc`. The test uses that already-deployed **real KCalc 26.08.1 executable directly**, against the host's installed Qt/KF libraries, behind `dbus-run-session` for a private app bus. This is not evidence for Flatpak's normal launch path or sandbox/cgroup behavior. Btop's real desktop entry is hidden; the test creates a visible entry only in its private XDG folder. Foot uses a private font/size config so btop can draw. Neither installed entry is edited.

Both are opened by 1.1 `open_app` over the real Unix socket, with no injected launcher or window events:

| Program | Owned scope suffix (full names in JSON) | Observed window identity | Evidence |
|---|---|---|---|
| KCalc | `449687ad4dbc3dad.scope` | `org.kde.kcalc` | `ActiveState=active`, `Slice=app.slice`, all observed PIDs' `/proc/<pid>/cgroup` match the scope; `app_state=focused` then `closed` |
| btop inside Foot | `69956cf08ceabc9c.scope` | `aresos.app.check-btop` | A separate active scope under `app.slice`, Foot and btop PIDs in it; `app_state=focused` then `closed` |

Closing each owned foreign-toplevel handle makes labwc activate the stand-in hub; the helper emits `shell_focus=foreground, reason=desktop_activated`. The test also checks that the app window is gone, hub is active, and the matching launch reaches `closed` before continuing. Async picture events appeared over the real socket as well. Scopes and processes are stopped by owned unit names/PIDs/process groups in `finally`, never by process name.

Screenshots, captured with grim against this private display and visually inspected:

- [KCalc](screenshots/check-kcalc.png)
- [btop](screenshots/check-btop.png)

Earlier harness attempts are retained only as local logs: the private runtime initially lacked the manager socket; a reused journal correctly replayed that failure until the test used a unique instance; the first foreign-toplevel opcode minimized instead of closing; and an overly narrow return predicate waited for `app_closed` after labwc had already sent `desktop_activated`. First screenshots caught an unpainted frame, a too-small btop terminal, and the real delayed-focus bug fixed above. The final script waits for painting, uses a suitable private Foot size and binds returns to the correct app. No failed application behavior or blank screenshot is counted as acceptance.

### Hosted checks

Tested implementation commit: `3a3e4134d3cd0d36df99078327f5f8226c292074`. The final report-only commit follows it.

- `gh workflow run "OS image" --ref pkg/30-installed-programs -f check_build=build`; one blocking `gh run watch 43510432674 --exit-status --interval 30`: [image/VM run](https://github.com/Ares-Empire/AresOS/actions/runs/43510432674) — **PASSED in 40m06s**. Its log contains `ICON_CONVERTER /usr/bin/magick; SVG coder: librsvg (RSVG); bubblewrap present`, the package-30 coder PASS, `IMAGE_CHECKS_PASSED`, `ARESOS_ACTIVE_SESSION_POLKIT_PASSED` and `CHECK_BUILD_VM_PASSED`; the disposable image and real VM gate both passed, without publishing.
- `gh workflow run "OS image" --ref pkg/30-installed-programs -f checks_only=true`; one blocking `gh run watch 43510437239 --exit-status --interval 30`: [full regression run](https://github.com/Ares-Empire/AresOS/actions/runs/43510437239) — **PASSED in 17m04s**. On the disposable GitHub runner, `env -u REHEARSAL_PACKAGE python3 -m unittest discover -s os/tests -v` printed **`Ran 1219 tests in 985.821s`, `OK`, zero skipped**. Regression/syntax checks, the real hosted manager query, release-input resolution and candidate signature verification passed. The workflow's private-org metadata step was skipped under its public-repository condition; no private-org verification is claimed.

Earlier runs [43510212242](https://github.com/Ares-Empire/AresOS/actions/runs/43510212242) and [43510217331](https://github.com/Ares-Empire/AresOS/actions/runs/43510217331), at `68ef4440`, were deliberately canceled while preparing the CLI compatibility fix, not counted as verification. Each was also started with a single blocking watch. The current hosted runs use the corrected implementation. The PR's separate hosted [mod build, tests and jar reproducibility check](https://github.com/Ares-Empire/AresOS/actions/runs/43510443156) also passed in 3m12s; that does not run or replace the Minecraft client game suite.

### Earlier steps (from PROGRESS.md, historical evidence)

- Step 1's original helper command `python3 -m unittest discover -s os/tests -p test_aresos_shell.py -v` passed 74 tests before/after (`1.329s` / `0.946s`). The helper pattern with `-v` first ran 110 tests with one new fixture's incorrect sort-order expectation; the corrected fixture passed **110 tests in 11.923s**. No implementation assertion was weakened.
- Step 2 ran the helper pattern only: **110 / 137 / 140 / 142 / 142 tests**, all OK, ending **142 in 19.388s**. The final 32 A5 tests include split-read/window-order replay. Earlier test modules stayed unchanged in that step.
- Step 3 ran the helper pattern: **142 / 173 / 175 / 176 tests**, all OK, ending **176 in 19.134s**, zero skips. Explicit six-converter checks first had a new missing `os` import, then passed **6 in 0.463s** and **6 in 0.437s**. A development-only color-sample failure in the original tiny drawing was resolved by making the drawn stripe two pixels wide; alpha/padding/color assertions remained. Normalized originals were actually inspected: PNG 468 bytes, SVG 439 bytes, each 128×128 8-bit RGBA, 0600/0700 permissions, clear/solid/half alpha 0/255/128. Actual tools: ImageMagick 7.1.2-32 Q16-HDRI, `SVG … (RSVG 2.62.3)`, bubblewrap 0.12.0. Using `magick identify … -list format` and list-length 2 resolved converter-command development failures; no MSVG/delegate/network fallback was added.
- **Historical unsafe step-1 run, never repeated:** a full local OS discovery command ran 1131 tests in 873.337s with failures=101, errors=23, skipped=1. All 110 helper tests passed within it. Failures came from existing root/sudo assumptions, Python-3.14 mocking differences, private-path ownership checks, and `test_owner_update` reaching the real laptop tools instead of the expected missing-rpm-ostree fixture result. Its isolated owner-export diagnosis also failed an existing path-ownership precondition. The OS lead then prohibited this full suite on the laptop. No affected tests or owner tools were changed; an orphan fixture was identified by its worktree environment marker and stopped through a held PID descriptor. The hosted full-suite result above is the acceptance gate. Step 4 does not repeat or diagnose those local modules.

## Not verified

- Real Lunar launcher → game timing, Steam, resident Discord/Steam/Lunar reopening, and the NVIDIA variables' effect on a real game. No Chrome profile, Lunar, Steam or owner's game was opened.
- The normal Flatpak KCalc launch path, or every installed app's chosen window IDs and availability. The neutral headless check above uses the deployed executable directly for isolation.
- Minecraft UI, icons rendered as items/logos, chat aliases, pins and real pointer/input return. No local Gradle build/client/game test was run: this step is restricted to helper tests and the headless protocol check. Package 34 owns the mod compatibility tests; the hosted image build's compilation is not a claim of running its client game suite twice.
- Package review, independent security review and `linux-aresos` OS-diff review are still required before merge. This builder did not review its own work or send review requests to others.
- No signed release, deployment, physical disk, boot setting, system configuration or running owner session was changed.

## JUDGMENT-CALL

- **Identity collisions:** root files then sorted subfolders, within sorted source folders, break same-folder sanitized-ID ties. Rejected filesystem enumeration order because it changes pins nondeterministically. Changing the rule can change which colliding entry owns a saved ID.
- **Unknown child windows:** attach only to the sole live discovered program, blocked by another possible program or unresolved reviewed launch. Rejected “most recently clicked” because it can claim unrelated windows and steal focus. Changes are local to transition/replay tests; app IDs need not change.
- **Close delay:** discovered last-window closure gets the existing 0.5-second HANDOFF grace (plus up to the normal 0.5-second tick); a new matching window cancels closure. Rejected waiting for scope exit because resident tray processes would strand the owner, and immediate return because split launcher/game events would steal focus. Changing timing needs transition tests and the owner's real Lunar trial. An observed desktop activation now fulfills return intent, preventing later focus theft.
- **Icon precedence:** theme across all roots, then descending raster size, then root order, then scalable; hicolor always precedes breeze. Rejected root-first sorting because it discards the brief's explicit size preference. Changing this local order may change pictures.
- **Sandbox is required:** missing bubblewrap/unusable librsvg loses only that icon, with no unsandboxed/MSVG fallback. Rejected broader mounts/network/delegates because these are untrusted files. SVG text needing host fonts or external assets may be incomplete; changing mounts needs a file-access review. Named symlinks escaping Flatpak icon roots are deliberately rejected, even when legitimate.
- **Converter caps:** 8 MiB input, 4096² pixels, 64 MiB memory, map/disk 0, internal time 2s, wall time 3s, stdout 1 MiB, one converter; PNG/SVG only, no DTD/entities/non-UTF-8 SVG signature/root after 4 KiB. Rejected permissive decoding/unbounded work; changing these reversible constants can admit more icons without changing app IDs.
- **Polling/paging:** three-second stat/picture refresh; opaque HMAC cursors live for this helper process and use positions in the current list. A mid-list revision change tells the mod to restart, as the shared contract says. Rejected retained per-client snapshots and inotify as unnecessary state/dependencies. A restart invalidates cursors with `invalid_cursor`, prompting a fresh first page. Changing these choices is local, with no persisted format change.

## PLAN-GAP

- **Lunar provenance/timing:** foreign-toplevel has neither PID/scope provenance nor advance knowledge of a game window. The brief requires both no early Lunar return and return when no windows remain despite a live scope, without a handover-gap bound. Conservative inference and a 0.5-second grace resolve that ambiguity, but a delayed game can follow a brief hub return. A stronger guarantee needs process-aware compositor evidence or a separately chosen longer delay. Real Lunar timing remains unverified.
- **Version assertions:** the old test of a future minor-7 client hardcoded maximum minor 0, and step 3 temporarily asserted MINOR=0. Advertising 1.1 requires those exact assertions to change. They now expect minor 1/capabilities, while real minor-0 payload/revision/access tests remain strict. A5 fixtures likewise must negotiate 1.1 once discovery is gated.
- **Interface authority:** HUB 3.8 and its example README settle optional fields, negotiated-envelope semantics and offered-capability event gating. They were followed unchanged; no example was found impossible and none was edited.
- **Laptop suite/environment:** the historical full-suite assumptions are incompatible with a running owner laptop; the lead's hosted-only rule takes precedence. The headless runtime also needs only a link to the existing user-manager socket for independent scopes. KCalc's host executable path is absent, so the neutral check uses the already-installed Flatpak binary directly instead of installing anything.

## Known limits

- *(Superseded by "Review fixes 1": there is no inference any more.)* A background resident program or unresolved reviewed launch can block unknown-child association; unrelated new windows cannot be proven to belong to a scope. A late Lunar window beyond the grace can follow a hub return. Known explicit identities still work.
- *(Superseded by "Review fixes 1": there is no inference any more.)* Discovered programs with no usable identities remain available; they need conservative inference and may never gain a matched window in an ambiguous session. A clean gone-scope handover gets the existing bounded no-window wait; live/unknown scopes keep waiting. Nonzero early exits still fail.
- Directory symlinks are not traversed, file symlinks are; malformed desktop files, missing executables/TryExec/terminal, unsupported forwarding syntax and unsupported icons are omitted rather than guessed. Locale-specific names/actions are out of scope. Relative Path means HOME for discovery. `%i`, `%c`, `%k`, `%%` retain the existing parser's expansions; file/URL codes are dropped.
- Only `foot.desktop` is replaced by the Terminal starter; the distinct Foot client/server entry can still appear. A starter borrows only presentation from replacement entries, never their command/window policy.
- Catalogue cap is 256. Polling gives changes up to roughly three seconds of discovery latency, then sequential icon work. Stat walking/parsing occurs on the helper loop only when due; untrusted huge directory trees are not a bounded-latency guarantee. This package does not add inotify or an icon-cache eviction policy.
- Converter limits and root containment intentionally lose some legitimate icons; fonts/external SVG assets are unavailable. Conversion failures are memoized by source fingerprint until restart or the bounded failure memo clears. Icons are reconstructible, not persistent app identity.
- Same-user socket nonce/instance checks bind the supervised desktop; they are not a security boundary against other programs running as the owner. A hostile entry in his own folder already has normal desktop-launcher power and can impersonate a friendly display name; no extra approval layer was added.

## Open questions

No implementation question blocks this handoff. Owner decisions on the judgment calls, the real Lunar/Steam trial, and independent package/security/OS review remain before merge. PR: [#55](https://github.com/Ares-Empire/AresOS/pull/55). Never merged by this run.

Closing housekeeping: all owned headless processes/scopes and converter/test children were stopped/reaped by held PIDs/groups or unit names. No Gradle daemon was started or stopped. No large download was made; `find .work -type f -size +500M -printf '%p %s bytes\n'` printed nothing. **Files left in `.work/` over 500 MB: none.**

## Try this (owner, after review)

1. From this worktree on your desktop: `mod/dev/run-hub.sh --helper "$PWD/os/config/usr/libexec/aresos-shell" --registry "$PWD/os/config/usr/share/aresos/apps"` (wait if it refuses for game/memory; do not force).
2. With the package-34 mod, find your programs/pictures in My apps; open Lunar, close its launcher after the game appears, then close the game and check that you return to the hub once.
3. Open Steam, close its last window while it stays running, reopen it from the hub, and check return, picture updates and the NVIDIA choice during real gameplay.

## Review fixes 1

Brief: `briefs/30-review-fixes-1.md`. Two fresh reviews of `08753aeb`, both CHANGES-NEEDED: `SECURITY-1.md` (five FIX
findings) and `REVIEW-1.md` (one blocking, six should-fix). All twelve fixed by two Claude builder steps (Opus 5.5),
2026-11-13/14: step A the security review's five, step B the package review's. Each fix was also taken out alone (a
scratch script that patches the helper in memory) and its tests run; "Verified" says how many failed then. Not every
new test is a regression test: some are controls that check unchanged behaviour and pass either way (corrected in
review fixes 2, REVIEW-2 nit 5): FlatpakMarkerTest's recognised-forwarding case, FlatpakAppIdTest's ordinary-program
case (it also passes the pre-review code), the hint for a program that is not installed, DroppedReturnTest's
no-choice case, and step A's positive cases (internal desktop links, accepted desktop exports, allowed SVG shapes,
the route without the systemd flag). The registry-return test beside an unowned window was a control for an exception
that review fixes 2 removed.

`os/` files touched: `config/usr/libexec/aresos-shell`; `config/usr/share/aresos/apps/hints/` (new: `lunarclient.json`,
`steam.json`); `ci/image-checks.sh` (two added checks: `/usr/bin/prlimit`; the hints load and are root's); tests
`test_aresos_shell.py`, `test_aresos_shell_discovery.py`, `test_aresos_shell_windows.py` (see "Existing tests changed"),
new `test_aresos_shell_hardening.py` (step A), new `test_aresos_shell_review_fixes.py` (step B), new
`check_aresos_shell_launch.py`, changed `check_aresos_shell_icons.py`. Docs: `docs/design/OS-BASE.md` B1. Nothing
under `mod/`; the examples under `mod/src/test/resources/shell-1.1/` are unchanged; the three registry entries are
unchanged.

### Step A: the security review (SECURITY-1.md)

- **FIX 1, discovery can't stall or exhaust the helper.** `Catalogue.scan()` is one bounded pass; `ScanBudget` counts
  every folder entry looked at, accepted or not: 4096 entries, 256 folders, nesting 8, 32 MiB of desktop entries,
  2 s. The byte bound is checked from stat sizes before reading (hard links cost no disk space) and again while
  reading. A pass that hits a bound, raises or blocks changes nothing (the last good catalogue stays) and is logged
  once. Folders are walked through descriptors; a linked subfolder is never entered, not even one swapped in after
  listing. `Discovery` runs scans on its own thread (`aresos-discovery`), at most one at a time and at most every 3 s;
  the serving loop only takes finished catalogues; a scan blocked over 4 s is logged once. Before the first scan the
  registry alone is in force; `build()` waits up to 3 s for it. Tests (`test_aresos_shell_hardening.py`): ten thousand
  hidden entries (no file read, one log line, recovery), 40 hard links to one 1 MiB malformed entry (none read),
  bytes counted while read, folder/depth/time bounds, a swapped-in linked subfolder, a blocked scan through `build()`
  (five ticks and lists each under 0.2 s), a folder a writer keeps changing for 2.5 s (no overlap, every tick under
  0.25 s), a failing scan, the registry-only start.
- **FIX 2, the converter has a real memory ceiling.** It starts under util-linux `prlimit --as=268435456 --`
  (256 MiB address space), set before `bwrap` and inherited by everything it starts; measured on the laptop, every
  icon that converts at all needs under 128 MiB. Chosen over a memory-limited systemd scope per conversion (a D-Bus
  round trip per icon for a two-process tree) and `preexec_fn` (unsafe in this threaded helper). `drawn_svg()`
  refuses before conversion an SVG with `image`, `feImage`, `foreignObject`, XInclude, any `href`/`url()` not to
  `#id` (`data:` included), CSS escapes or `@import`, processing instructions, a DTD or entity, or XML that is not
  well formed. Tests: a stand-in converter and its forked child both carry the limit and cannot map 512 MiB; a 41 KB
  SVG whose embedded PNG decodes to 16000x16000 is refused; 16 refused constructs, one subtest each; drawn shapes
  with local references still convert. Real converter (`check_aresos_shell_icons.py`): with the refusal bypassed, the
  bomb fails under the ceiling within the timeout.
- **FIX 3, the icon cache has a budget:** 512 files and 32 MiB, checked before converting and with the real size
  before writing; over it, the picture is not cached (fallback look, "budget used up" logged once, not remembered as a
  failure). A changed source's older picture is removed at once; after each complete pass, pictures no listed
  program uses and leftovers of interrupted writes are removed. Tests: one icon's time changed a thousand times
  leaves one picture; removed programs and leftovers pruned; a full cache keeps the fallback and says so once; the
  real size is checked before writing.
- **FIX 4, systemd changes no argument:** `systemd-run ... --expand-environment=no --` on every launch (the three
  registry apps' arguments contain no `$`, so nothing changes for them). Real route (`check_aresos_shell_launch.py`,
  laptop only: hosted Ubuntu has no user manager): a stand-in in a real `systemd-run --user --scope` receives
  `${HOME}` unchanged from `Exec`, `%c` and `%i`; a control without the flag shows systemd 259.9 expanding all three.
- **FIX 5, links are checked before anything is read:** `open_confined()` pins a file with `O_PATH`, checks its real
  location in `/proc/self/fd` and reopens it through the pin, so the file read is the file checked. A desktop file
  must resolve inside the five application folders or a Flatpak deployment (`~/.local/share/flatpak/app`,
  `/var/lib/flatpak/app`: exports only ever link into `app/<id>/...`); anything else is skipped with one log line.
  Icon theme and size folders are listed only after the same check; a Flatpak export's icon link into its deployment
  is accepted, so **Flatpak programs get their pictures (this settles the package review's finding 5)**. An explicit
  absolute `Icon` path is read as written, as before. Tests: a link to a file outside, links inside, the realistic
  layout `flatpak install` leaves (`exports/...` to `../../../app/<id>/current/active/export/...`), a link changed
  after the check, a link to a FIFO or device, a theme folder linking out, a Flatpak export icon found and converted.
- **Real-world smoke run** (no window, no launch; private runtime folder and icon cache, his real application
  folders): the old (`5fbe6d20`) and new helper both listed the same 56 programs from all five sources; pictures 33
  (old) and 45 (new): none lost, 12 gained (the Flatpak icons).

### Step B: the package review (REVIEW-1.md)

New tests are in `os/tests/test_aresos_shell_review_fixes.py` unless named otherwise.

- **Finding 1 (blocking), windows belong to a program by a reviewed identity, never by a guess.** The rule that the
  only live discovered program owns windows nobody claims is removed. Instead, reviewed image-shipped **hints** give
  an installed discovered program extra window identities, exact or by prefix (format below). They are validated as
  strictly as registry entries (`parse_hint`, `load_hints`), beat discovered programs' guessed identities, and never
  a registry entry's identity (valid or not) or the desktop's; hints that name one program twice or could claim the
  same window are all refused, with a log line. Exact identities always beat prefixes. Two ship: Lunar Client
  (`lunarclient.desktop`, game window `com.mojang.minecraft`; seen on the laptop on 2026-11-13: the launcher's window
  is `lunarclient`, which its own `StartupWMClass` already names, the game's is `com.mojang.minecraft`) and Steam
  (`steam.desktop`, prefix `steam_app_`, the identity Steam gives its games; **not seen on the laptop**). A window
  nobody owns is nobody's: it confirms no launch, keeps no program open and forces no return; when a discovered
  program's last window closes while such a window is open, the hub is not pulled in front of it and comes back only
  when the compositor gives it the focus. Tests (`HintTest`, `HintedOwnershipTest`), each with time moving and its
  closing consequences: Lunar with Chrome open (launcher closes while the game runs: no return; game closes: one
  return, Lunar closed, Chrome still background); Lunar's launcher closed shortly before, in the same compositor batch
  as, and after the game window appears (no return until the game closes, then one), and long before it (an honest
  return, then the game takes the focus and its close returns again); Discord resident without a window while an
  unrelated window opens (nobody's; it confirms no second launch, changes no launch state, forces no return; Discord's
  own window then confirms it); Steam with a game window (`steam_app_1086940` is Steam's, the bare prefix is nobody's,
  Steam's own window closing keeps it open, the game's close returns once); an unowned window in front keeps the hub
  away until the compositor gives it; a registry app still returns at once beside an unowned window; the shipped
  hints are exactly the two; 16 broken hints refused with one log line each; clashing hints refused; precedence
  (registry, desktop, exact over prefix, hint over guess); a hint for a program that is not installed changes
  nothing; a changed hint changes the catalogue and its revision. Mutations: without hints 8 of these fail; with the
  old guess back 5 fail; without the unowned-window rule 2 fail; without prefix matching 2 fail.
- **Finding 2, a 1.0 client sees today's behaviour, windows included.** Window ownership follows the last desktop's
  negotiated minor: with a 1.0 desktop only the registry's identities own windows and trigger returns, also while it
  is disconnected and after it reconnects. Before any hello, a journal that still holds an unfinished discovered
  launch (only a 1.1 client can start one) means 1.1, so a helper restart keeps its windows. A change applies at the
  next tick, after the hello reply. Tests (`LegacyWindowsTest`, through `build()` over real desktop folders, as
  production builds the catalogue): with a 1.0 desktop, Firefox started by hand over the terminal opens and closes
  three times (connected, disconnected, reconnected): never a return, the terminal stays focused, and the terminal's
  own close still returns; a 1.1 desktop owns Firefox's window, a 1.0 reconnect gives it up, and a 1.1 reconnect gets
  the discovered return back; a dialog that inherited a discovered parent's owner loses it for a 1.0 desktop too.
- **Finding 3, a 1.0 client asking for a discovered ID gets exactly the old failed-launch answer.** For a 1.0 client
  a discovered ID is an unknown one: answered and journaled exactly as the pre-package-30 helper answers any unknown
  ID, and a repeated request ID replays it (also after a restart) or answers `request_id_reused`. A 1.0 client
  resending a request ID a 1.1 client used for a discovered launch gets the same unknown answer, not journaled; the
  real launch is untouched. Tests (`LegacyDiscoveredIdTest`) compare whole answers and journal entries with the ones
  `origin/main`'s helper gives (checked once against that helper: `{"protocol": "aresos-shell/1.0", "id": "o-1",
  "ok": false, "request_id": "o-1", "launch_id": null, "app_id": "lunarclient", "state": "failed", "error":
  "unknown_app", "message": "no reviewed launch definition"}`, journal entry with the same fields and `updated`).
- **Finding 4, a return that is no longer wanted is dropped.** A discovered program's pending return remembers the
  compositor's pick after the close (the first window activated, also when that activation arrives before the close).
  A later switch to another window, or a launch, drops the return; the close still ends the launch. Without a choice
  the compositor's pick still gets the return. Tests (`DroppedReturnTest`): A closes, B takes focus, C is chosen
  without the hub in between, in both arrival orders; A closes, B takes focus, a launch; the control where nothing is
  chosen still returns once.
- **Finding 5, Flatpak export icons:** settled in step A (FIX 5 above).
- **Finding 6, Flatpak's markers only for Flatpak.** `@@`/`@@u` groups are removed only from a recognised
  `flatpak run [options] --file-forwarding APP` command (`--file-forwarding` before the app ID); in any other command
  `@@` is an ordinary argument. Tests (`FlatpakMarkerTest`): `tool @@`, `tool @@ %f @@`, `tool @@u %u @@ --flag` keep
  their markers; Flatpak without forwarding, or with it after the app ID, keeps them; recognised commands lose them.
- **Finding 7, a Flatpak's app ID from its command.** Without `X-Flatpak`, the app ID is the first word after
  `flatpak run`'s options, only when every option before it is understood (`--name=value` or one of flatpak 1.16's
  value-less flags) and it is a valid Flatpak ID; it is used for `exec_name` and as a window identity. Otherwise the
  detail is left out, not invented. `flatpak` itself is no longer an identity candidate. Tests (`FlatpakAppIdTest`):
  `my-firefox.desktop` running `org.mozilla.firefox` reports and matches `org.mozilla.firefox`; `X-Flatpak` still
  wins; a separate option value, `--command firefox`, a non-ID word and no app leave `exec_name` out.

### Hints file format

`/usr/share/aresos/apps/hints/<name>.json`, one program per file, image-shipped and owned by root:

```json
{"schema": 1, "desktop_id": "steam.desktop", "app_ids": [], "app_id_prefixes": ["steam_app_"]}
```

`schema` must be 1; `desktop_id` a desktop file ID (`[A-Za-z0-9._-]{1,128}.desktop`); `app_ids` at most 8 different
Wayland app IDs (`[A-Za-z0-9._-]{1,128}`); `app_id_prefixes` at most 8 different prefixes of 4 to 64 characters that
end in `.`, `_` or `-` (a window matches only when its identity is longer than the prefix). At least one identity;
no other keys; nothing that names or could match `aresos-desktop`. A broken file is skipped with a log line; files
that name the same desktop ID, or could claim the same window, are all refused.

### Existing tests changed in step B (all others unchanged)

- `test_aresos_shell_discovery.py` `test_flatpak_file_and_url_forwarding_markers_are_dropped_as_groups`: its
  commands gain `--file-forwarding` before the app ID. Real Flatpak exports always carry it, and finding 6 asks that
  markers count only then; the assertions (groups dropped, malformed groups refused with one log line each) keep their
  meaning.
- `test_aresos_shell_windows.py`: `DiscoveredBase.start` applies the image's hints, as `load_catalogue` does. In
  `UnclaimedWindowTest`, the tests that asserted the removed guess now assert what finding 1 asks:
  `test_new_unclaimed_windows_belong_to_the_only_live_program_and_keep_their_owner` became
  `test_a_window_nobody_owns_stays_nobodys_even_with_one_live_program` (owner None, the launch closes, no return);
  `..._multiple_scopes_of_the_same_program_are_one_candidate` became
  `test_multiple_launches_of_the_same_program_share_its_hinted_window`; `..._a_confirmed_scope_can_claim_...` became
  `test_scopes_decide_no_owner_and_scope_death_never_closes_a_real_window`; `..._restart_recovers_an_unclaimed_game_window_from_the_live_scope`
  became `test_restart_recovers_the_hinted_game_window`. Where Lunar's game window was the invented `java-lunar`
  (claimed by the guess), it is now `com.mojang.minecraft`, claimed by the shipped hint:
  `test_unclaimed_window_waits_for_an_identity_...`, `test_a_delayed_game_inside_the_existing_handoff_interval_...`
  and the three byte-split tests of `DiscoveredSplitReadTest` (their focus and return assertions unchanged).
- No assertion about the three registry apps was touched. The registry apps' tests (`test_aresos_shell.py`) connect
  as 1.0 clients and pass unchanged.

### JUDGMENT-CALL (review fixes 1)

- *(Superseded by review fixes 2, finding 4: with a 1.1 desktop the registry apps leave a window nobody owns in
  front too; a 1.0 desktop keeps the immediate return.)* Unowned windows stopped only discovered programs' returns.
- **"A window nobody owns is open" means any such window, not only the one in front** (the brief's words). A window
  nobody owns that stays open all the time (a tray helper, a program with no identity) means discovered programs'
  closes leave the focus to the compositor; the hub comes when the compositor gives it. Narrowing it to the active
  window later is a one-line change.
- **Window rules follow the last hello's minor**; before any hello, 1.0 unless the journal holds an unfinished
  discovered launch. Rejected: deciding per connection (no desktop connected would have no rule) and always 1.1
  (finding 2's regression for an old mod).
- **Hints:** prefixes must end at a separator and be at least 4 characters; exact identities beat prefixes; hints
  beat discovered guesses; clashing hints are all refused, like registry entries with a shared window identity; a
  hint applies only to a discovered program (a starter that replaces the desktop file keeps its reviewed identities).
- **Lunar's hint names every Minecraft game window `com.mojang.minecraft`**, whichever launcher started it, as Lunar's
  while Lunar Client is installed (the desktop's own window is `aresos-desktop`, which no hint can claim).
- **A deliberate launch drops pending returns** too (finding 4 says "a deliberate switch or launch"), as soon as the
  launch starts; a launch that fails at once does not.
- **Flatpak options:** only `--name=value` and flatpak 1.16's value-less flags are understood; anything else before
  the app ID leaves the ID out.

### Known limits (review fixes 1)

- **Windows nobody owns:** a program whose windows carry none of its identities (no hint yet, an Xwayland window
  without a class) gets no confirmed launch (`no_window` after 30 s, or it keeps waiting while its scope lives), no
  "open" state and no forced return; the hub comes back only when the compositor gives it the focus. The fix is a
  reviewed hint for that program.
- **Steam's prefix was not seen on the laptop.** `steam_app_<appid>` is the identity Steam is known to give its games;
  Proton or native games that set their own identity would be nobody's until hinted.
- A permanently open window nobody owns stops forced returns (see the JUDGMENT-CALL; since review fixes 2 also the
  registry apps' with a 1.1 desktop).
- **What he sees of the missing provenance (REVIEW-2 nit 6).** A Lunar game window that appears more than half a second
  after the launcher's window closed leaves that launch `closed`: the hub came back once, and My apps shows Lunar as not
  open while the game runs (the window is still Lunar's: closing it returns to the hub). Another launcher's Minecraft
  window (`com.mojang.minecraft`, e.g. Prism's) counts as Lunar Client's while Lunar is installed: it confirms a waiting
  Lunar launch, keeps Lunar open, and closing it returns to the hub as Lunar's.
- A mod that reconnects with a lower minor while discovered programs are open makes their windows nobody's; their
  launches close after the hand-over interval.

### Verified (review fixes 1)

On the laptop, 2026-11-14, at the step-B code (the last code commit is the one after `228ae93c`; the headless
check ran at `228ae93c`, before a one-function change to `Windows.set_registry` that it does not reach):

- `TMPDIR="$PWD/.work/30-installed-programs/tmp" python3 -m unittest discover -s os/tests -p 'test_aresos_shell*.py'`
  → **Ran 255 tests, OK**, twice (198 before review fixes 1, 224 after step A).
- `... -p 'check_aresos_shell_launch.py'` (FIX 4's real `systemd-run --user --scope` route) → **Ran 2 tests, OK**.
- `... -p 'check_aresos_shell_icons.py'` (the real sandboxed converter) → **Ran 7 tests, OK**.
- **Each fix taken out alone** (scratch script, helper patched in memory, the fix's tests run): without hints 8 of
  15 fail; with the old guess back 5 of 21; without the unowned-window rule 2 of 21; without prefix matching 2 of 7;
  with the full catalogue for 1.0 desktops two of three `LegacyWindowsTest` tests, and with inherited dialog owners
  kept the third; with the old generic refusal both
  `LegacyDiscoveredIdTest` tests; without the switch cancel 2 of 4 and without the launch cancel 1 of 4
  `DroppedReturnTest` tests; with markers removed everywhere 2 of 3; with the old invented Flatpak ID 3 of 4
  `FlatpakAppIdTest` tests are regression tests (the fourth, the ordinary program, is a control: REVIEW-2 found that it
  passes the pre-review code too, so the earlier count of 4 is withdrawn). With every fix in, all pass.
- **Headless end to end once more:** `python3 os/tests/check_aresos_shell_headless.py` → **`HEADLESS_KCALC_BTOP_PASSED`**,
  then **`owned processes and scopes stopped`**. Before it, the owner's Lunar game had been running (its Java under
  `~/.lunarclient/`, 3 GB available), so the run waited until it had ended: the script's own guard then printed
  9 GB available and no Lunar Java. Its own headless labwc (`.work/h30/r/wayland-0`), its own HOME and socket, the
  real KCalc executable and btop in Foot, both opened by 1.1 `open_app` over the real socket: KCalc in
  `app-aresos-check\x2dkcalc-b57c7e1f78977b7e.scope` (active, `app.slice`, nine PIDs, window `org.kde.kcalc`), btop in
  `app-aresos-check\x2dbtop-f0e17785b873ade4.scope` (window `aresos.app.check-btop`); each `app_state=focused`, then on
  closing labwc activated the stand-in hub (`shell_focus=foreground, reason=desktop_activated`) and the launch
  `closed`. `headless.json` and `screenshots/check-btop.png` are this run's (btop drawn in its Foot window in front
  of the stand-in hub, inspected); the KCalc picture came out identical. Afterwards no `app-aresos-check*` unit was
  left and the compositor's PID was gone.
- Hosted runs: see below.

### Not verified (review fixes 1)

- A real Lunar Client session through the helper (launcher to game hand-over with the hint) and a real Steam game's
  window identity: both need the owner's own programs, which this run never starts. The Lunar identities are the ones
  read from his session's window list on 2026-11-13; Steam's prefix was not seen there.
- The real package-34 mod against these windows rules (1.0 and 1.1): covered here at the protocol level only.

## Review fixes 2

Brief: `briefs/30-review-fixes-2.md`. Two fix checks of `ab58d12f`, both CHANGES-NEEDED: `SECURITY-2.md` (FIX 1 and 2
open in a new form) and `REVIEW-2.md` (findings 2 and 4 open in a narrower form, two new should-fix, two nits). Built by
a Claude agent (Opus 5.5), 2026-11-14, after merging `origin/main` (packages 31 and 34; `image-checks.sh` kept both
blocks). One commit per fix. New tests are in `os/tests/test_aresos_shell_review_fixes_2.py` unless named otherwise.

`os/` files touched: `config/usr/libexec/aresos-shell`; `ci/image-checks.sh` (package 31's `/tmp/pkg31-home` removed
right after its `gsettings` call, for the OS lead); tests `test_aresos_shell_review_fixes.py` (one test changed, below),
`check_aresos_shell_icons.py` (its two bypasses of the SVG refusal now patch `IconCache.check_svg`), new
`test_aresos_shell_review_fixes_2.py`. Nothing under `mod/`; the examples under `mod/src/test/resources/shell-1.1/` are
unchanged.

### The fixes

- **Security FIX 1, no filesystem call on the serving loop.** Whether a program can start is worked out where its
  catalogue is built, on the discovery worker (`with_availability`, also for the 1.0 list), and published as
  `App.unavailable`; `list_apps` serves it and touches no file. Opening an app checks its program, and the folder it
  starts in (Popen's child changes into it while the helper waits), on a `LaunchChecks` thread: the loop waits 0.2 s (a
  local file answers in microseconds), then answers when the check does, or after 3 s fails the launch as `unavailable`
  with reason `not_responding`. A resent request ID joins its waiting launch; launches of one program share its check;
  at most 4 checks are outstanding, beyond that a launch fails at once with reason `checks_busy`. The scan's deadline
  is also checked per parsed entry, per program's availability and right before a catalogue is published.
  Tests: `StalledMountTest` (a stand-in for a stalled mount whose check never returns until the test ends, and which
  fails the test at once if the serving loop ever touches it): listing, heartbeats and another program's launch go on
  while the stalled program's launch and one whose folder is on the dead mount wait; both fail as `not_responding`
  after 3 s and replay that answer; once the mount answers, it opens. And with 4 stuck checks the next launches fail at
  once (`checks_busy`), no fifth thread starts, the helper answers, and the waiting launches go on once it answers.
  `ScanDeadlineTest`: out of time while parsing, after parsing, and right before publishing, the last good catalogue
  stays and the work stops there.
- **Security FIX 2, the SVG pre-check runs under the memory ceiling.** The helper never runs `drawn_svg` itself any
  more: `IconCache.check_svg` runs the helper file in `--check-svg` mode (`python3 -I -S`), a short-lived process under
  the converter's `prlimit --as=268435456` and timeout, on the work folder's private copy, right before conversion; a
  cached picture skips it (it was made only after its SVG passed). It costs about 70 ms per conversion. The pre-check is
  bounded as well: namespace addresses 512 and names 128 characters, 8192 elements, 32768 attributes, nesting 64; a
  namespace declaration over the bound is refused before any name in it is expanded. The 42,575 SVG icons installed on
  the laptop have at most 957 elements, 3,883 attributes, nesting 11, addresses of 50 and names of 31 characters.
  Tests (`SvgPreCheckTest`): the review's case (a 256 KiB namespace address and 50,000 differently named elements) is
  refused, the helper's peak memory grows under 32 MiB, no picture is made and the program keeps its fallback look (the
  test caps its own address space 1 GiB above its size first, so a regression fails instead of taking the laptop's
  memory); the pre-check never runs in the helper but in `prlimit --as=268435456 -- python3 -I -S <helper>
  --check-svg <work copy>`; each bound refuses (8 cases) and a drawing at the bounds passes.
- **Package review finding 1, going back to a 1.0 client drops what was pending.** A 1.0 hello cancels discovered
  programs' pending returns, and an overdue discovered close forces a return only while the window rules are 1.1's.
  Tests (`LegacyReconnectTest`): Lunar closes, the compositor activates the terminal, a 1.0 desktop connects inside the
  waiting time: no return, Lunar closed, terminal in front; the same with a 1.1 reconnect right after; a close the
  helper had not processed yet when the 1.0 hello arrived; a 1.1 control that still returns.
- **Package review finding 2, the switch he just made wins.** `windows_changed` takes the current activation into
  account (the compositor's first pick keeps the return, a later switch drops it) before an overdue return runs.
  Tests (`LateSwitchTest`): the switch to the editor arrives after the deadline, before any tick ran the return: no
  return, the editor in front, no focus event; a control where only other compositor news arrives after the deadline
  and the return still runs.
- **Package review finding 3, a reviewed prefix beats a discovered exact identity.** `apply_hints` removes from every
  other discovered program each identity a hint names or a hint's prefix covers (`App.hint_ids` records a hint's exact
  identities). `Windows` owns in this order: the desktop and the registry, then hints (exact, then prefix), then
  discovered programs' own candidates. Tests (`PrefixPrecedenceTest`): a discovered entry with
  `StartupWMClass=steam_app_1086940` beside Steam keeps only its own identity; the game window is Steam's; Steam's
  launcher closing right after the game took the focus forces no return and Steam stays open; the game's close returns
  once and closes Steam's launch. And `Windows` ranks registry, hint exact, prefix, discovered in both insertion orders.
- **Package review finding 4, the protection holds for the registry apps under 1.1.** When Chrome, Terminal or
  Notepad closes its last window while a window nobody owns is open, a 1.1 desktop's hub is not pulled in front of it;
  it comes back when the compositor gives it the focus. A 1.0 desktop keeps the immediate return. Changed test:
  `test_aresos_shell_review_fixes.py` `test_registry_apps_still_return_when_their_last_window_closes_beside_an_unowned_window`
  (it asserted the exception) became `test_registry_apps_leave_an_unowned_window_in_front_too_under_1_1`. New:
  `RegistryBesideUnownedTest` (Chrome under 1.1; the 1.0 immediate return).

### Which tests are regression tests, which are controls

Each fix, or part of a fix, was taken out alone (scratch script: the helper's source changed in memory and run in the
loaded module, never on disk) and its tests run:

| Taken out | Fails then |
|---|---|
| list_apps checks executables on the loop | both `StalledMountTest` tests |
| the launch check on the loop | both `StalledMountTest` tests |
| the folder check | `StalledMountTest` listing test |
| the 4-check limit | `StalledMountTest` limit test |
| each of the three deadline checks | `ScanDeadlineTest` (its own subtest) |
| the pre-check back in the helper | `SvgPreCheckTest` own-process test |
| the bounds | `SvgPreCheckTest` bounds test, all 8 subtests |
| both (the review-1 pre-check) | also the review's case: the worker never answers (out of memory at the test's guard) |
| the cancel at a 1.0 hello | `LegacyReconnectTest` 1.1-right-after test |
| the 1.0 condition on discovered returns | `LegacyReconnectTest` not-yet-processed test |
| both | also the 1.0-reconnect test |
| the old order (activation after expiry) | `LateSwitchTest` switch test |
| the catalogue removal under a prefix | `PrefixPrecedenceTest` Steam test |
| the `Windows` order | `PrefixPrecedenceTest` ranking test (both subtests) |
| the registry-app condition | `RegistryBesideUnownedTest` 1.1 test and the changed `HintedOwnershipTest` test |
| that condition without the 1.0 exception | `RegistryBesideUnownedTest` 1.0 test |

Controls (pass with or without their fix, kept to pin unchanged behaviour): `LegacyReconnectTest`'s 1.1 control,
`LateSwitchTest`'s other-news control, review fixes 1's `DroppedReturnTest` (unchanged, passes either way). The
review's name bomb (`SvgPreCheckTest`) fails only with both halves of FIX 2 out: each half alone stops that case.

### JUDGMENT-CALL (review fixes 2)

- **A launch whose check is slow is answered later.** Over 0.2 s the reply waits for the check (at most 3 s), then
  `unavailable` with reason `not_responding`; the mod (package 34's `ShellClient.reason`) shows that as "unavailable
  (not_responding)", with no wording of its own. Rejected: waiting the whole 3 s on the loop (heartbeats would stall).
- **Four stuck checks block every launch.** With four different programs on dead mounts, any further launch, Terminal
  included, fails at once (`checks_busy`, "unavailable (checks_busy)") until one answers; listing and heartbeats go on.
  Rejected: falling back to the published value then (systemd-run's child would hang on the dead mount and the launch
  wait 30 s for a window). The limit is one constant.
- **A 1.0 desktop's list shows availability from the last scan**, not a live check per list: a program removed between
  scans shows as available for up to about 3 s (the scan notices executables changing); opening it still checks.
- **The pre-check process is the helper file itself** (`--check-svg`, hidden from `--help`), so there is one copy of
  the check. Rejected: inside the converter's sandbox (Python is not bound into it).

### Known limits (review fixes 2), with what he would see

- **A style rule split across pieces passes the pre-check** (`u&#114;l(` or `@im&#112;ort` in `<style>`, or a CDATA
  boundary): the converter still renders it inside its sandbox (no network, no home folder, only the icon), under the
  timeout and memory ceiling. At worst an icon looks odd or falls back to the plain look; nothing outside the icon is
  read.
- **An icon can be missing for a moment while it is replaced:** the old picture is removed before the new one is
  published, and two programs sharing one source can briefly get different versions. The program shows its fallback
  look until the next icon pass (seconds). Nothing of his is lost.
- **A scan stuck on a dead drive stops new programs from appearing until the helper restarts:** the last good list
  stays, listing and opening keep working, and the helper logs it once after 4 s. A logout and login (or a restart of
  the desktop) brings discovery back.
- **Window identities are claims:** a program can name another's window identity; another launcher's Minecraft window
  counts as Lunar Client's and a stray `steam_app_*` window as Steam's. He would see a wrong open state in My apps or
  the hub coming back at an unexpected moment; no command runs because of it.
- A mount that stalls in the microseconds between a launch's check and its start still holds the helper while Popen
  waits for the child; a stuck check thread lives until its file call returns.

### Verified (review fixes 2)

On the laptop, 2026-11-14:

- `TMPDIR="$PWD/.work/30-installed-programs/tmp" python3 -m unittest discover -s os/tests -p 'test_aresos_shell*.py'`
  → **Ran 271 tests, OK** (255 before this round). Each per-fix commit's snapshot (`git checkout-index` of `os/` into a
  scratch folder) also passed: 265, 267, 269, 271 for findings 1 to 4.
- `... -p 'check_aresos_shell_icons.py'` (the real sandboxed converter) → **Ran 7 tests, OK** (after FIX 2).
- PENDING (step 2, see PROGRESS.md): `check_aresos_shell_launch.py`, the headless end to end, the hosted runs.

### Not verified (review fixes 2)

- A real stalled mount (NFS or a pulled USB drive): only the stand-in. A real Lunar Client or Steam session, as before.
