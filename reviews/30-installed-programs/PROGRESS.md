# Package 30 progress — step 1 of 4

## Files changed under `os/`

- `config/usr/libexec/aresos-shell`
- `config/usr/share/aresos/apps/browser.json`
- `config/usr/share/aresos/apps/terminal.json`
- `config/usr/share/aresos/apps/notepad.json`
- `tests/test_aresos_shell_discovery.py` (new)
- `tests/fixtures/installed-programs/README.md` (new)
- `tests/fixtures/installed-programs/{lunarclient,org.mozilla.firefox,com.discordapp.Discord,steam,btop,foot}.desktop` (six new text fixtures)

`os/tests/test_aresos_shell.py` is unchanged. No mod files, image checks, source bindings, live configuration or other worktrees were changed.

## Done: A1–A4

The helper has a separate internal `load_catalogue()` entry point. It merges the reviewed registry with desktop entries in the brief's five-directory order, including recursive desktop-file IDs and file symlinks used by Flatpak exports. Overrides reserve their desktop ID before parsing or visibility checks, so a hidden, malformed or unusable override never falls through to a system copy. Registry IDs always win; `replaces` suppresses the shipped Chrome, Foot and KWrite entries. The registry's launch definitions and window behavior remain intact.

Discovery reads only regular files, with nonblocking open and a 1 MiB read limit, UTF-8 replacement, and only the main Desktop Entry group's keys. It filters visibility, desktop, TryExec and usable Exec, skips individual malformed files with one log line, and logs when MAX_APPS cuts the combined catalogue. Names and IDs are bounded and deterministic; collisions keep the earlier entry.

Discovered argv is parsed with the existing Exec grammar, with Flatpak's complete empty file-forwarding groups removed. The executable is resolved once against `/usr/local/bin:/usr/bin` or kept absolute as written, then checked again at use without searching again. Absolute Path is honored, otherwise launch uses HOME. Terminal programs are wrapped with `TERMINAL_COMMAND`, currently Foot, and `terminal_app_id(app)` supplies `aresos.app.<id>`. The command remains argv throughout; no shell is introduced.

The existing ScopeLauncher launches the resolved definition in its own `app-aresos-…scope` under `app.slice`. Every launch drops all six inherited GPU keys as well as the existing private environment. Only `gpu='discrete'` plus a detected NVIDIA driver adds the three supervisor offload variables. Desktop GPU hints and Game categories set that policy; reviewed entries can opt in with the strictly validated optional `gpu` key. Tests compare both GPU sets against package 23's actual source constants.

There are 36 new tests, including sanitized laptop fixtures, generated malformed/oversized/binary entries, 500 entries, hidden overrides, ID collisions, literal shell characters, executable permissions, terminal launches, scope names/slice, GPU presence/absence, and unchanged 1.0 listing/open behavior. All launches in these tests are mocked.

## Where the next builder starts

**Discovery is intentionally not connected to `build()`, `Helper`'s default loader or `--list` yet.** MINOR stays 0, all existing wire messages stay 1.0, and the live helper still lists and opens the three reviewed apps. A7 will expose discovered apps only after negotiating 1.1. Do not switch the default registry loader early and expose incomplete discovered-window handling to old clients.

`App.discovered` distinguishes definitions that have already resolved argv. `desktop_entry` on a discovered App holds its desktop-file ID; `resolve()` takes the discovered branch before the old reviewed-desktop-entry branch. `App.app_ids` is deliberately empty and `instance` still has its existing default for discovered entries: A5 must supply their identities and handover behavior. No discovered-window policy was attempted in this run. Tests for A5 can pass the catalogue via the existing `Helper(..., registry=(apps, revision))` injection without changing production loading.

The new discovery loader does not retain metadata for icons, search, source or window identities. A5/A6/A7 can extend the model to keep the desktop path/parsed values and originating folder when they need them. The current catalogue digest covers only fields implemented in this step; later steps must extend it for their metadata and completed icons. `read_desktop_entry()`, `desktop_files()` and `desktop_directories()` are available to share precedence and bounded parsing.

The laptop's real `btop.desktop` has `Hidden=true`. Its checked-in fixture preserves that. The terminal unit test changes only its private copy to `Hidden=false`; the later headless acceptance test will also need an explicit visible test entry. Never change the owner's installed entry to make this test possible.

## Decisions and limits

- **JUDGMENT-CALL:** same-folder collisions use sorted files, followed by sorted subfolders, with root files first. Earlier source folders always win. The brief does not choose a same-folder tie breaker; this makes it repeatable without adding persistent IDs. Changing it later can change the owner of an already colliding ID.
- Directory symlinks are not followed; desktop-file symlinks are. This avoids recursive symlink traversal while supporting Flatpak's actual exports. A program installed solely beneath a symlinked subdirectory is left out. Following those directories later would need cycle handling.
- The visibility desktop is explicitly AresOS, independently of the environment of a CLI inspection or a headless compositor. Relative/empty XDG_DATA_HOME falls back to the specified home default.
- Malformed booleans, duplicate main-group keys, missing printable names and malformed forwarding markers are skipped. Missing executables/TryExec or a missing terminal are excluded rather than guessed. A terminal that disappears after discovery becomes `not_installed` at launch.
- Relative Path uses HOME for discovery, following A4's wording; the old `desktop_exec()` behavior for reviewed entries is preserved. File/URL field codes are removed, while `%i`, `%c`, `%k` and `%%` retain the existing parser's expansion behavior. This matches the brief's “as today” requirement and the [Desktop Entry Exec specification](https://specifications.freedesktop.org/desktop-entry/latest/exec-variables.html).
- Only `foot.desktop` is declared replaced by the Terminal starter. The distinct `footclient.desktop` entry is still discoverable when its executable is installed; it explicitly requests Foot's client/server behavior rather than the starter's standalone Foot command.
- **PLAN-GAP for A7:** the original `ProtocolTest.test_hello_negotiates_version_and_capabilities` sends minor 7 and hardcodes the helper's current maximum minor 0 and old capability set. Advertising 1.1 necessarily changes that specific expectation, although genuine 1.0-client behavior must remain unchanged. Step 1 leaves it untouched and passing. Reconcile that version-test expectation explicitly in step 4; do not break negotiation to satisfy an obsolete maximum-version assertion.

## Verification

Commands run from the worktree root. Test logs are local, ignored files in `.work/30-installed-programs/`.

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

The one skip is `test_aresos_desktop.WrapperTest.test_the_real_jvm_runs_in_its_own_scope_with_the_memory_target`: `no user systemd manager reachable here (CI runner); WSL and the image have one`. No desktop test failed and needed a busy-laptop rerun. No source-binding check failed. The affected tests were not weakened or skipped, and restricted owner-tool code was not edited. **PLAN-GAP:** local whole-suite green needs the OS lead to address these existing native/unprivileged/Python-3.14 assumptions; package 30 cannot fix them within its permitted files. Keep these failures visible until resolved or independently qualified in the intended CI environment.

No GUI apps, game, compositor or Gradle process were started by this step. There are no screenshots or real scope/window/GPU-effect claims. Image/VM checks and the two neutral-program headless acceptance test remain for step 4. After the full suite, an orphaned fixture process was identified by its environment marker pointing into this worktree's temporary test directory, and stopped through its own PID descriptor. A final scan found no remaining owned fixture PIDs. No processes were stopped by name. No downloads were made; the closing `.work/` scan found no file over 500 MB.

## Remaining, in order

1. **Step 2 — A5 windows.** Add ordered discovered identities with reviewed identities winning and discovered collisions losing only the conflicting identity. Track terminal programs by `terminal_app_id()`. Treat clean early exits as handovers, suppress `no_window` while a discovered scope runs, return when the last window closes even if the process stays alive, and allow a later launch to bring that window back. Keep Lunar's launcher-to-Java transition inside `windows_changed()` and replay event streams at every split/order. Preserve all reviewed-app behavior. Update this progress file, commit and push, then stop.
2. **Step 3 — A6 icons.** Add bounded icon lookup, explicit PNG/SVG sniffing, confirmed librsvg coder, limits and timeout in a child process, atomic private 128×128 RGBA cache, and asynchronous revision changes. Assess bwrap without installing anything. Add image-check assertions in their own block, alongside package 31's independent checks. Draw test images; commit no third-party icon assets. Update progress, commit and push, then stop.
3. **Step 4 — A7 interface, A8 and final report.** Negotiate minor 1/capabilities; retain the old client's exact starter-only shape and launch access. Wire discovery, five source kinds, replacement-starter details, safe optional metadata, paging/cursors under 64 KiB, rescan throttling and `apps_changed`. Read and test the copied, unchanged package-34 contract messages under `mod/src/test/resources/shell-1.1/`; stop if their contract cannot be met. Update OS-BASE Appendix B1 and the helper's header. Address the version-test PLAN-GAP above and replace the new step-1 compatibility test's temporary loader assertion with real 1.0 compatibility coverage.
4. **Finish verification and review handoff in step 4.** Run helper tests and all `os/tests`; perform the real-socket kcalc/btop scope/window/return checks on an owned headless compositor/display/runtime folder, with grim evidence. Before every heavy step check memory and the owner's game; never touch wayland-0 or reconfigure labwc. Stop owned processes by held PIDs/scopes. Write REPORT.md with all touched OS paths, exact evidence, judgment calls/gaps, unverified Lunar/Steam/offload behavior, and the three-line owner trial note. Push and open the PR only at the final step, then run the branch's requested OS image check build and wait with one `gh run watch` (including image and VM gates). Obtain the package, security and OS-lead reviews; never merge.

Only step 1 was authorized in this run. No PR or workflow dispatch was requested or performed here.
