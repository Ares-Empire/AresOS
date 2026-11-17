# Package 50: console keymap at boot

Worktree branch: `pkg/50-console-keymap`. Changes stay uncommitted for the lead.

## Read and established

- Read the whole brief, `AGENTS.md`, `CLAUDE.md`, the design, image build/configuration and static checks,
  disposable VM wiring, the owner tools' loaded-key check and runtime-only trial, binding helper, and package 42's
  release-28 classifier on `pkg/42-release-28` (read-only).
- systemd's [manual](https://www.freedesktop.org/software/systemd/man/latest/systemd-vconsole-setup.service.html)
  documents `/usr/lib/systemd/systemd-vconsole-setup [TTY]`.
  [v259 source](https://github.com/systemd/systemd/blob/v259/src/vconsole/vconsole-setup.c) confirms the explicit
  console is opened, checked for translated/Unicode keyboard mode, then passed to the normal configuration and
  keymap loader. Its no-argument scan skips consoles in graphics mode. No custom production parser is needed.
- systemd's [target documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd.target.html)
  says targets normally order themselves after their wanted units. The new service will disable those default
  dependencies and explicitly run after the graphical target, so it cannot hold up that target or graphical login.
  Shutdown ordering is restored explicitly, and a timeout bounds the one attempt. Failure remains visible in the
  journal and unit result; boot only wants the service.

## Built, in brief order

1. Done: `aresos-console-keymap.service`, enabled in `os/build.sh`. It runs after `graphical.target`,
   `plymouth-quit-wait.service` and `systemd-vconsole-setup.service`, once, with a 15-second limit.
2. Done: image checks require the regular unit's exact directives, 0644 root:root, executable systemd setup,
   enablement, and the root-owned graphical-target link.
3. Implemented, not run: a CI-overlay-only check observes the boot result and loaded keys before mutations,
   loads the opposite runtime map, puts allocated guest consoles into graphics mode, requires systemd's automatic
   scan to log its busy-console skip, restores the display modes, then restarts the real unit and requires the
   configured keys again. It keeps both journals, dumps, invocations and skip evidence in
   `evidence/vm-pass-1/console-keymap-result.json`. `CHECK_BUILD_VM_PASSED` now requires its marker.
4. Done: `os/tests/test_console_keymap.py` tests the actual image-check content block with mutations, supported
   configuration and dumpkeys spellings, the requirement for a completed service invocation, bounded waiting,
   display-mode cleanup on partial setup/skip/restore failure, map restoration on failed repair, and CI wiring.
   No whole-image `os/config` filename allowlist was found to update. The historical release-13 two-file diff pin
   in `test_owner_path.py` describes that frozen release and stays unchanged.
5. Done: package 42's rules inspected without changing its branch; exact image paths and remaining rules below.

## Files changed

- `os/config/usr/lib/systemd/system/aresos-console-keymap.service`: new production oneshot; systemd reads the
  finished configuration, including its normal kernel-command-line precedence. There is no polling, timer,
  restart policy or hard-coded layout. An active oneshot does not run again during runtime-only layout trials.
- `os/build.sh`: enables that unit through the image's existing `systemctl enable` convention. There is no
  AresOS system preset directory in this checkout; no preset file needed changing.
- `os/ci/image-checks.sh`: static installed-unit, root ownership, exact content, executable and enablement checks.
- `os/ci/overlay/console_keymap.py`: new disposable-guest boot and forced-skip/repair check; no work on import.
  Its configuration parser is deliberately limited to the CI's supported `de`, `us`, `us-intl` assignments;
  production delegates all parsing to systemd. The graphics-mode exercise holds the guest's allocated VTs,
  restores every original display mode with an ExitStack, and restores the finished map if the exercise fails.
  The automatic scan's log target is explicitly stderr so the busy-console notice is retained in the evidence.
- `os/ci/overlay/Containerfile`, `os/ci/overlay/checks.py`: install and expose that guest-only check.
- `os/ci/vm.py`: requires the check after the ordinary policy pass, before recovery shortcuts or keyboard input.
- `os/ci/check-build.sh`: requires the new result's `CONSOLE_KEYMAP_PASSED` marker before
  `CHECK_BUILD_VM_PASSED`.
- `os/tests/test_console_keymap.py`: 21 local tests, all console/service operations replaced with stand-ins.
- `os/manifest/ci/16/pending-rebind.json`: new note and updated checkout hash for bound `os/ci/vm.py`.
- This `reviews/50-console-keymap/PROGRESS.md`.

## Verified locally

Each module was invoked with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p '<module>.py'
```

| Module | Printed result |
| --- | --- |
| `test_console_keymap.py` | Final: `Ran 21 tests`, `OK` (0.018s). First run: `Ran 21 tests`, `FAILED (failures=4, errors=1)` (0.023s); the test harness had replaced fixture-file reads with config text and omitted `configparser.Error` from expected rejection types. Corrected those fixture issues; production assertions remain intact. |
| `test_system_keyboard.py` | `Ran 7 tests`, `OK` (0.012s). |
| `test_everyday_account.py` | `Ran 34 tests`, `OK` (0.105s), with the existing `load_module()` deprecation warning for Python 3.15. |
| `test_shell_assertions.py` | `Ran 9 tests`, `OK` (2.060s). |
| `test_audit.py` | `Ran 14 tests`, `OK` (0.034s); repeated with `Ran 14 tests`, `OK` (0.031s and 0.036s). The final run was serial after the other modules completed; two earlier invocations overlapped a still-running static module before I corrected the scheduling. |
| `test_checkout_sources.py` | `Ran 8 tests`, `OK` (1.156s). |
| `test_ci_api_permissions.py` | `Ran 4 tests`, `OK` (2.285s). |
| `test_ci_step_environment.py` | `Ran 4 tests`, `OK` (7.206s). |

Additional checks:

- `bash -n os/build.sh os/ci/check-build.sh os/ci/image-checks.sh`: exit 0, no output.
- `git diff --check`: exit 0, no output.
- Python `ast.parse` on the new helper/test and changed guest/host VM Python: `Python syntax: 4 files parsed`.
- Ran the required binding command after the last bound-file edit:

  ```sh
  PYTHONDONTWRITEBYTECODE=1 python3 reviews/27-first-update-release/rebind.py pending "50: boot-only console keymap after Plymouth; vm.py requires boot-key and forced busy-VT repair evidence in the disposable check build"
  ```

  It printed `pending: 9 bound files differ from the active bindings, 0 removed`. The other eight entries already
  waited before this package. `test_checkout_sources.py` passed with the updated record.
- Read `pkg/42-release-28:os/ci/release_diff.py` through `git show` and exercised its extracted `config_rule` and
  `audit_changes` functions against source bytes/metadata and a synthetic added audit row. Printed:

  ```text
  Release 28 config_rule accepts the new unit with a merged package 50 origin and exact source bytes/metadata
  Release 28 audit_changes rejects the added unit row; a narrow package 50 addition rule is needed
  Release 28 has no existing constant for the new graphical-target enablement link
  ```

  This confirms classifier behavior against synthetic records, not an actual image comparison.
- `.work/` scan before closing: `.work files over 500 MB: []`. No image/download was made.

## Not verified / needs the lead's check build

- No GitHub dispatch, image build, container-image check, VM boot, or real console operation was run here, as the
  brief requires. The lead must run the check build on the committed tree, including the full hosted test suite.
- `systemd-analyze verify --man=no os/config/usr/lib/systemd/system/aresos-console-keymap.service` exited 1 in this
  sandbox, printing:

  ```text
  Failed to turn off SO_PASSRIGHTS on user lookup socket, ignoring: Operation not permitted
  Failed to enable SO_PASSCRED on handoff timestamp socket: Operation not permitted
  ```

  This is not a successful systemd verification. Unit syntax/contents passed the local static tests; actual
  dependency handling and installed metadata still need the check build.
- Required image result: the new console-unit PASS line in `evidence/image/checks.txt` and `IMAGE_CHECKS_PASSED`.
- Required VM result: `CONSOLE_KEYMAP_PASSED` in `evidence/vm-pass-1/console-keymap-result.json`, followed by
  `CHECK_BUILD_VM_PASSED`. The JSON must show a successful **boot** invocation before any test mutation, the two
  correct keys, the opposite runtime map surviving the forced busy-console skip, a new successful unit invocation,
  correct keys again, and unchanged `vconsole.conf`.
- The forced-skip exercise is implemented and its logic/cleanup have stand-in tests, but **the race has not been
  reproduced in a real VM here**. A failure to reproduce the skip fails the check; it is not silently skipped.
- The overlay boots with `KEYMAP=us`. The exercise temporarily loads `de` without changing the finished file and
  proves repair back to `us`; local fixture tests cover configured `de`, `us`, `us-intl`. This does not prove a
  German-configured laptop boot, actual Plymouth timing on the Lenovo, or physical typing.
- After the release route and check build pass, the lead/owner still need a real reboot with the finished layout,
  recovery-console typing (including symbols), and the owner tools' `check`. No owner-tool code changed.
- No mod code changed and no Gradle process was started.

## Release 28 diff note for the lead

Compared with an otherwise identical image without package 50, the persistent image changes are exactly:

| Image path | Effect | Package 42 classifier on `pkg/42-release-28` |
| --- | --- | --- |
| `/usr/lib/systemd/system/aresos-console-keymap.service` | New regular file, 0644 root:root, exact `os/config` bytes. | Already covered by `Classifier28.config_rule` once package 50 is committed/merged on main and release 28 uses that main base; the source-history origin must include package 50. |
| `/etc/systemd/system/graphical.target.wants/aresos-console-keymap.service` | New root-owned 0777 symlink to `/usr/lib/systemd/system/aresos-console-keymap.service`, from `systemctl enable`. | **Needs a narrow build rule** for this exact new link, target and metadata. `Classifier28.build_rule` currently handles the desktop command, schemas, font caches and account dates, not this link. |
| `/usr/share/aresos/manifest/updaters.json` | Build-time audit gains the new system unit's row in sorted order. | **Needs a narrow audit-addition rule.** `audit_changes` currently requires equal list lengths and unchanged rows except newly reviewed drop-in sources. The new unit increases the list length. Preserve those checks and permit exactly the expected new row, while retaining the existing release-28 drop-in handling. |

The expected added audit row has scope `system`, name `aresos-console-keymap.service`, state `enabled`,
`suspicious: false`, commands `["ExecStart=/usr/lib/systemd/systemd-vconsole-setup /dev/tty3"]`,
sources `["/usr/lib/systemd/system/aresos-console-keymap.service"]`, and null `active_state`, `load_state`,
`sub_state` (the build's audit is offline). The existing graphical-target wants directory is already used by
greetd; this package adds no new persistent directory or package. The build-time `/tmp/aresos` copy is removed as
before. CI-overlay files, tests, notes and the pending-binding record are not shipped in the release image.
Other existing rebuild differences remain subject to package 42's existing rules; this list describes only
package 50's contribution. Package 42's branch was not changed.

## Judgment calls, gaps and remaining work

- **JUDGMENT-CALL:** No new owner decision. Disabling default unit dependencies and explicitly ordering after the
  graphical target implements the brief's requirement that this service cannot hold up login. Shutdown conflicts
  and ordering are restored explicitly. Failure is visible rather than masked with an ignored exit status.
- **PLAN-GAP:** None requiring a scope change. Runtime success and physical keyboard behavior remain unproven
  until the check build and laptop check above.
- **Open questions:** None for implementation; the lead must add the two release-diff rules before release 28's
  image comparison can accept package 50.
- Worktree changes are deliberately uncommitted. No owner tools, running-system settings or real worktree git
  metadata were changed; no CI dispatch, sudo, rpm-ostree, bootc or ostree command was run.
