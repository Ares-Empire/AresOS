# 50: review 1 (Codex gpt-6-astra high, 2026-11-17)

Reviews `1191a328`. Read-only sandbox: test errors from temporary-file creation are environmental.

No blocking or should-fix findings in `1191a328`.

- The explicit `/dev/tty3` argument is supported. Systemd checks keyboard mode, tolerates graphics display mode for this path, and attempts keymap loading even after a font error. Missing `vconsole.conf` uses systemd’s fallback rather than aborting. [Systemd source](https://github.com/systemd/systemd/blob/v259/src/vconsole/vconsole-setup.c).
- `DefaultDependencies=no` avoids the target-ordering cycle; explicit shutdown dependencies are restored. I found no new dependency blocking graphical login. The completed oneshot does not rerun during layout trials. [Target dependency rules](https://www.freedesktop.org/software/systemd/man/latest/systemd.target.html).
- The image checks reject missing or disabled installation. The VM check requires an actual successful boot invocation and correct keys. Its forced-skip exercise verifies the opposite map remains loaded before restarting the unit, then requires repaired keys. Failure cleanup cannot turn that into a pass.
- The release-28 diff note matches the build and package-42 classifier: the unit is covered by the source-file rule; the enablement link and added audit row need the two documented rules.
- The mocked tests exercise meaningful rejection paths; they do not establish real boot success.

Ran:
`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p 'test_console_keymap.py'`

Result: **21 tests, 13 errors**, all caused by unavailable writable temporary directories in this sandbox. No assertion failures. The image/VM checks and physical reboot remain unverified here, as the progress notes acknowledge. No files changed.

SAFE