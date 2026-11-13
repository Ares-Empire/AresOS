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

- A background resident program or unresolved reviewed launch can block unknown-child association; unrelated new windows cannot be proven to belong to a scope. A late Lunar window beyond the grace can follow a hub return. Known explicit identities still work.
- Discovered programs with no usable identities remain available; they need conservative inference and may never gain a matched window in an ambiguous session. A clean gone-scope handover gets the existing bounded no-window wait; live/unknown scopes keep waiting. Nonzero early exits still fail.
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
