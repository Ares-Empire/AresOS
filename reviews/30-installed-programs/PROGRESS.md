# Package 30 progress — step 2 of 4

**Laptop rule:** never run the whole `os/tests` suite here. `test_owner_update` invokes real owner tools on the running AresOS system. Locally use `python3 -m unittest discover -s os/tests -p 'test_aresos_shell*.py'` and only other specifically touched modules. Step 4 gets the full-suite count from GitHub with `gh workflow run "OS image" --ref pkg/30-installed-programs -f checks_only=true`. The step-1 full-suite run below is historical evidence of an unsafe mistake, not a command to repeat or a local acceptance gate.

## Files changed under `os/`

- `config/usr/libexec/aresos-shell`
- `config/usr/share/aresos/apps/browser.json`
- `config/usr/share/aresos/apps/terminal.json`
- `config/usr/share/aresos/apps/notepad.json`
- `tests/test_aresos_shell_discovery.py` (new)
- `tests/test_aresos_shell_windows.py` (new in step 2)
- `tests/fixtures/installed-programs/README.md` (new)
- `tests/fixtures/installed-programs/{lunarclient,org.mozilla.firefox,com.discordapp.Discord,steam,btop,foot}.desktop` (six new text fixtures)

`os/tests/test_aresos_shell.py` is unchanged. No mod files, image checks, source bindings, live configuration or other worktrees were changed.

## Done: A1–A4

The helper has a separate internal `load_catalogue()` entry point. It merges the reviewed registry with desktop entries in the brief's five-directory order, including recursive desktop-file IDs and file symlinks used by Flatpak exports. Overrides reserve their desktop ID before parsing or visibility checks, so a hidden, malformed or unusable override never falls through to a system copy. Registry IDs always win; `replaces` suppresses the shipped Chrome, Foot and KWrite entries. The registry's launch definitions and window behavior remain intact.

Discovery reads only regular files, with nonblocking open and a 1 MiB read limit, UTF-8 replacement, and only the main Desktop Entry group's keys. It filters visibility, desktop, TryExec and usable Exec, skips individual malformed files with one log line, and logs when MAX_APPS cuts the combined catalogue. Names and IDs are bounded and deterministic; collisions keep the earlier entry.

Discovered argv is parsed with the existing Exec grammar, with Flatpak's complete empty file-forwarding groups removed. The executable is resolved once against `/usr/local/bin:/usr/bin` or kept absolute as written, then checked again at use without searching again. Absolute Path is honored, otherwise launch uses HOME. Terminal programs are wrapped with `TERMINAL_COMMAND`, currently Foot, and `terminal_app_id(app)` supplies `aresos.app.<id>`. The command remains argv throughout; no shell is introduced.

The existing ScopeLauncher launches the resolved definition in its own `app-aresos-…scope` under `app.slice`. Every launch drops all six inherited GPU keys as well as the existing private environment. Only `gpu='discrete'` plus a detected NVIDIA driver adds the three supervisor offload variables. Desktop GPU hints and Game categories set that policy; reviewed entries can opt in with the strictly validated optional `gpu` key. Tests compare both GPU sets against package 23's actual source constants.

There are 36 new tests, including sanitized laptop fixtures, generated malformed/oversized/binary entries, 500 entries, hidden overrides, ID collisions, literal shell characters, executable permissions, terminal launches, scope names/slice, GPU presence/absence, and unchanged 1.0 listing/open behavior. All launches in these tests are mocked.

## Done: A5 (step 2)

Discovered apps now keep ordered, deduplicated window identities: StartupWMClass, desktop-file stem, X-Flatpak ID, executable basename. The existing window-identity validator excludes unusable candidates without hiding their program. Terminal entries claim only `terminal_app_id(app)`, matching their wrapper instead of claiming Foot or the process inside it. The catalogue reserves the desktop and all reviewed identities first, including unavailable reviewed entries; each discovered entry keeps only candidates no earlier program reserved. Even losing every candidate does not make an entry unavailable. Window identities now participate in the catalogue revision.

`App.instance` is `None` for discovery. A clean early exit waits for a resident instance's window; nonzero early exits still fail. Without window tracking, a clean handover settles its launch answer as the reviewed single-instance path does. With tracking, the normal no-window timeout is deferred while its scope is live or unknown; after a confirmed gone scope, the remaining bounded wait can report `no_window`. No window is closed merely because its scope ended.

`windows_changed()` owns discovered window association and the return transition. A discovered launch counts all its program's windows and dialogs, including a restored existing window and additional windows the program creates. Closing the last window completes all its pending launch answers and returns only a foreground program to the hub, after the existing 0.5-second HANDOFF interval. The scope may continue running. A later deliberate click starts another independent scope and can hand over to that resident process to restore its window.

For Lunar, a newly announced, identified window no app claims is associated with the sole live discovered program candidate, provided no unresolved reviewed launch makes that ambiguous. Multiple live scopes of one program are one candidate; another program's unknown scope also blocks guessing. A candidate needs a confirmed active scope or its still-running local systemd-run proxy. The window must have appeared after that launch. Assignment lasts for the window's lifetime, including after its launcher/scope disappears; later explicit app/desktop identities take precedence. Blank identities wait for identification, preexisting unrelated windows are excluded, and discovered child dialogs retain their parent after it closes. A recovered live scope can also recover the game's window at helper restart without relaunching it.

Separate scope watches survive the last window and the journal's final launch state, and stop once the scope is confirmed gone. This supports child windows and resident apps without redefining “gone” as process exit. All reviewed-app transition branches, launch definitions and timeout policies are preserved.

There are 32 new A5 tests. Three replay tests feed actual foreign-toplevel wire messages through the existing decoder at every byte split: launcher close/game appearance in both orders; last close/compositor refocus in both orders; and both Lunar windows closing plus refocus in all six orders. They assert launch state, window handles, no premature activation and exactly one final return. Other tests cover identity clashes, all-candidates-lost availability, Terminal=true, clean/nonzero handovers, live/unknown/gone scopes, dialogs, background close, closing and reopening a resident program, explicit identity corrections, ambiguity and restart adoption. No real program or compositor is started.

## Where the next builder starts

**Discovery is intentionally not connected to `build()`, `Helper`'s default loader or `--list` yet.** MINOR stays 0, all existing wire messages stay 1.0, and the live helper still lists and opens the three reviewed apps. A7 will expose discovered apps only after negotiating 1.1. Do not switch the default registry loader early and expose discovered apps to old clients.

`App.discovered` distinguishes definitions that have already resolved argv. `desktop_entry` on a discovered App holds its desktop-file ID; `resolve()` takes the discovered branch before the old reviewed-desktop-entry branch. Discovered `App.app_ids` is an ordered tuple after precedence filtering, and `instance` is `None`; reviewed entries retain their existing frozensets and single/multi declarations. The A5 tests inject definitions with `Helper(..., registry=(apps, revision))` without changing production loading. A7 should use the catalogue's already resolved identity ownership rather than rebuild it in another order.

The discovery loader does not retain metadata for icons, search or source. A6/A7 can extend the model to keep the desktop path/parsed values and originating folder when they need them. The current catalogue digest covers only fields implemented so far; later steps must extend it for their metadata and completed icons. `read_desktop_entry()`, `desktop_files()` and `desktop_directories()` are available to share precedence and bounded parsing. Preserve `discovered_scopes` and window lifetime ownership across a rescan; a catalogue refresh must not reset running programs' transitions.

The laptop's real `btop.desktop` has `Hidden=true`. Its checked-in fixture preserves that. The terminal unit test changes only its private copy to `Hidden=false`; the later headless acceptance test will also need an explicit visible test entry. Never change the owner's installed entry to make this test possible.

## Decisions and limits

- **JUDGMENT-CALL (A5):** unclaimed-window association is conservative and based on the sole live discovered program, as described above. A background resident Discord/Steam scope, or another unresolved reviewed launch, can prevent guessing that an unknown Java window is Lunar's. Known identities still work. Assigning to the most recently clicked app would work in more ambiguous sessions but could attach unrelated windows and steal focus on close. Changing the rule later is local to `windows_changed()` and its replay tests; there are no persistent app-ID changes.
- **JUDGMENT-CALL (A5):** discovered last-window closes wait the existing `HANDOFF=0.5` seconds; a replacement window inside that gap cancels the close. Registry returns remain immediate. Waiting for scope exit would strand tray-only Discord/Steam/Lunar processes outside the hub; immediate closure would steal focus when launcher-close and game-open messages arrive in separate reads. The event loop can add up to its normal 0.5-second tick before applying the grace deadline. Changing this interval changes perceived close responsiveness and requires rerunning the transition tests.
- **PLAN-GAP / not verified (A5):** foreign-toplevel supplies no PID or scope and cannot distinguish an unrelated new window from a scope's child, nor predict a game that has not announced a window yet. The brief gives no handover-gap limit while also requiring return when windows disappear even if the scope runs. The bounded grace above resolves that conflict; a game first announcing its window more than 0.5 seconds after launcher close may follow a brief hub return. No real Lunar timing is claimed. The owner must check it in step 4's trial; a stronger guarantee would need process-aware compositor provenance or a separately chosen longer delay, beyond this protocol's evidence.
- A clean discovered handover whose scope is confirmed gone gets the existing bounded no-window wait; live/unknown scopes keep waiting without a false failure. All current windows of one discovered app are shared across its unresolved launch requests. This avoids inventing single/multi declarations from desktop entries, and allows an existing resident window to confirm a second deliberate click.

- **JUDGMENT-CALL:** same-folder collisions use sorted files, followed by sorted subfolders, with root files first. Earlier source folders always win. The brief does not choose a same-folder tie breaker; this makes it repeatable without adding persistent IDs. Changing it later can change the owner of an already colliding ID.
- Directory symlinks are not followed; desktop-file symlinks are. This avoids recursive symlink traversal while supporting Flatpak's actual exports. A program installed solely beneath a symlinked subdirectory is left out. Following those directories later would need cycle handling.
- The visibility desktop is explicitly AresOS, independently of the environment of a CLI inspection or a headless compositor. Relative/empty XDG_DATA_HOME falls back to the specified home default.
- Malformed booleans, duplicate main-group keys, missing printable names and malformed forwarding markers are skipped. Missing executables/TryExec or a missing terminal are excluded rather than guessed. A terminal that disappears after discovery becomes `not_installed` at launch.
- Relative Path uses HOME for discovery, following A4's wording; the old `desktop_exec()` behavior for reviewed entries is preserved. File/URL field codes are removed, while `%i`, `%c`, `%k` and `%%` retain the existing parser's expansion behavior. This matches the brief's “as today” requirement and the [Desktop Entry Exec specification](https://specifications.freedesktop.org/desktop-entry/latest/exec-variables.html).
- Only `foot.desktop` is declared replaced by the Terminal starter. The distinct `footclient.desktop` entry is still discoverable when its executable is installed; it explicitly requests Foot's client/server behavior rather than the starter's standalone Foot command.
- **PLAN-GAP for A7:** the original `ProtocolTest.test_hello_negotiates_version_and_capabilities` sends minor 7 and hardcodes the helper's current maximum minor 0 and old capability set. Advertising 1.1 necessarily changes that specific expectation, although genuine 1.0-client behavior must remain unchanged. Step 1 leaves it untouched and passing. Reconcile that version-test expectation explicitly in step 4; do not break negotiation to satisfy an obsolete maximum-version assertion.

## Verification

Commands run from the worktree root. Test logs are local, ignored files in `.work/30-installed-programs/`.

### Step 2

Only the helper pattern was run, with test scratch inside the worktree:

`TMPDIR="$PWD/.work/30-installed-programs/tmp" python3 -m unittest discover -s os/tests -p 'test_aresos_shell*.py'`

- Baseline: `Ran 110 tests in 12.489s`, `OK` (`helper-step2-baseline.log`).
- First implementation: `Ran 137 tests in 15.472s`, `OK` (`helper-step2-first.log`).
- Expanded event-order coverage: `Ran 140 tests in 19.456s`, `OK` (`helper-step2-expanded.log`).
- Full A5 coverage: `Ran 142 tests in 18.389s`, `OK` (`helper-step2-final.log`).
- After checking retained-scope/replay-ID lifetime and failed-scope ambiguity: `Ran 142 tests in 19.388s`, `OK` (`helper-step2-review.log`): all 74 original tests and 36 step-1 tests unchanged, plus 32 new A5 tests. The original test module emits socket ResourceWarnings, also present in the baseline; it was not edited to hide them. The shared-identity test deliberately logs that both reviewed entries are unavailable. Implementation and tests are committed as `32565074` (`Track discovered program windows and resident handovers`).

`git diff --check` passed. `git diff --quiet HEAD -- os/tests/test_aresos_shell.py os/tests/test_aresos_shell_discovery.py` returned 0. No full OS suite, Gradle, workflows, GUI programs or compositor were run in step 2; no owned background processes require stopping. No screenshots, real scope/window observations or GPU-effect claims are made. No downloads were made; `find .work -type f -size +500M -printf '%p %s bytes\n'` printed nothing.

Dead ends / rejected approaches: assigning discovered entries the default `multi` contract would falsely fail clean handovers; relying on scope exit for return would never leave a resident tray process; immediate last-window return fails split-read launcher/game transitions. No failing tests were weakened; all step-2 helper runs passed, with coverage expanded between runs.

### Step 1 (historical; do not repeat the full-suite commands)

1. `python3 -m unittest discover -s os/tests -p test_aresos_shell.py -v` before editing: `Ran 74 tests in 1.329s`, `OK` (`helper-baseline.log`).
2. The same command after implementation: `Ran 74 tests in 0.946s`, `OK` (`helper-existing.log`).
3. `TMPDIR="$PWD/.work/30-installed-programs/tmp" python3 -m unittest discover -s os/tests -p 'test_aresos_shell*.py' -v`: first run `Ran 110 tests in 11.916s`, `FAILED (failures=1)`. A new same-folder collision fixture incorrectly labeled the dot-containing filename as sorting before the hyphen-containing filename. Corrected the fixture labels to represent the intended ordering; implementation and original tests were not changed. Final run: `Ran 110 tests in 11.923s`, `OK` (`helper-step1.log`).
4. Before the full suite, `free -g` showed 6 GB available; a `/proc/<pid>/exe` scan found no Java executable beneath the owner's Lunar directory. `mkdir -p .work/tmp` then `TMPDIR="$PWD/.work/tmp" env -u REHEARSAL_PACKAGE python3 -m unittest discover -s os/tests -v`: `Ran 1131 tests in 873.337s`, `FAILED (failures=101, errors=23, skipped=1)` (`os-tests.log`). All 110 helper tests passed within that run. The shorter TMPDIR keeps Unix socket paths within their limit and all test scratch in this worktree. **The full suite is not green on this laptop; see the breakdown below.**
5. `git diff --check`: passed. `git diff --quiet -- os/tests/test_aresos_shell.py`: exit 0, confirming the existing test file is unchanged.
6. Isolated diagnosis: `TMPDIR="$PWD/.work/tmp" PYTHONPATH=os/tests python3 -m unittest test_owner_export.ExportTest.test_readonly_refusals_and_success_unmount_with_private_records_only -v`: `Ran 1 test in 0.005s`, `FAILED (errors=1)`, `owner.Stop: Unsafe private diagnostic parent` (`owner-export-diagnostic.log`). This test does not import the app helper. `git diff --quiet HEAD -- os/owner-tools os/tests/test_owner_export.py os/tests/test_owner_update.py os/tests/test_owner_setup_resume.py` returned 0; these sources and tests are unchanged.

Full-suite failures are outside the allowed package-30 files:

| Area | Result | Observed cause |
|---|---|---|
| `test_inherited_homebrew` | 1 failure, 7 errors | Existing tests invoke `sudo -n`; this account cannot elevate without a password. The suite printed `sudo: a password is required`. No password was supplied. |
| `test_sysusers` | 2 errors | Same noninteractive sudo refusal for `systemd-sysusers --root=<fixture>`. |
| `test_owner_commands`, `test_owner_retained`, `test_owner_setup_resume` | 12 errors total | Laptop Python is 3.14.8. `Path.rglob()` delegates to `glob(..., case_sensitive=..., recurse_symlinks=...)`; the existing mocked `glob` functions reject `case_sensitive`. |
| `test_owner_diagnostics`, `test_owner_export` | 2 errors and 1 failure total | Existing private-directory/root-ownership checks refuse non-root fixture metadata. The export survival test consequently sees no saved diagnostic. |
| `test_owner_update.ToolsUpdateTest` | 99 failures | The real-entry helpers identify a new toolset by `STOP: Required tool missing: rpm-ostree`. On AresOS rpm-ostree exists; the isolated namespace instead reports `STOP: Read failed: rpm-ostree status --json`, so their `reached()` returns None. Failures span five methods: 70 interruption/refusal subtests, 20 cut/bootstrap subtests, 7 broad-detection subtests, and the versioned-toolset and entry-settlement tests. |

The one skip is `test_aresos_desktop.WrapperTest.test_the_real_jvm_runs_in_its_own_scope_with_the_memory_target`: `no user systemd manager reachable here (CI runner); WSL and the image have one`. No desktop test failed and needed a busy-laptop rerun. No source-binding check failed. The affected tests were not weakened or skipped, and restricted owner-tool code was not edited. These are historical laptop failures, not a task to diagnose or fix here. The OS lead subsequently prohibited this suite on the running laptop because its owner-update tests invoke real owner tools. Obtain the full-suite result in the intended GitHub environment with `checks_only=true`; do not rerun these modules locally to reproduce the incident.

No GUI apps, game, compositor or Gradle process were started by this step. There are no screenshots or real scope/window/GPU-effect claims. Image/VM checks and the two neutral-program headless acceptance test remain for step 4. After the full suite, an orphaned fixture process was identified by its environment marker pointing into this worktree's temporary test directory, and stopped through its own PID descriptor. A final scan found no remaining owned fixture PIDs. No processes were stopped by name. No downloads were made; the closing `.work/` scan found no file over 500 MB.

## Remaining, in order

1. **Step 3 — A6 icons.** Add bounded icon lookup, explicit PNG/SVG sniffing, confirmed librsvg coder, limits and timeout in a child process, atomic private 128×128 RGBA cache, and asynchronous revision changes. Assess bwrap without installing anything. Add image-check assertions in their own block, alongside package 31's independent checks. Draw test images; commit no third-party icon assets. Preserve the A5 policies and replay tests. Update progress, commit and push, then stop.
2. **Step 4 — A7 interface, A8 and final report.** Negotiate minor 1/capabilities; retain the old client's exact starter-only shape and launch access. Wire discovery, five source kinds, replacement-starter details, safe optional metadata, paging/cursors under 64 KiB, rescan throttling and `apps_changed`. Read and test the copied, unchanged package-34 contract messages under `mod/src/test/resources/shell-1.1/`; stop if their contract cannot be met. Update OS-BASE Appendix B1 and the helper's header. Address the version-test PLAN-GAP above and replace the new step-1 compatibility test's temporary loader assertion with real 1.0 compatibility coverage.
3. **Finish verification and review handoff in step 4.** Run only helper/touched-module tests locally. Push and get the complete suite from GitHub: `gh workflow run "OS image" --ref pkg/30-installed-programs -f checks_only=true`, then wait with `gh run watch`. Never run the whole `os/tests` suite on this laptop. Perform the real-socket kcalc/btop scope/window/return checks on an owned headless compositor/display/runtime folder, with grim evidence. Before every heavy step check memory and the owner's game; never touch wayland-0 or reconfigure labwc. Stop owned processes by held PIDs/scopes. Write REPORT.md with all touched OS paths, exact evidence, judgment calls/gaps, unverified Lunar/Steam/offload behavior (including the A5 timing/ambiguity limits), and the three-line owner trial note. Push and open the PR only at the final step, then run `gh workflow run "OS image" --ref pkg/30-installed-programs -f check_build=build` and wait with one blocking `gh run watch` (including image and VM gates). Obtain the package, security and OS-lead reviews; never merge.

Step 2 ends here with a commit and push. No PR or workflow dispatch was requested or performed in this run. Steps 3 and 4 each need their own fresh run.
