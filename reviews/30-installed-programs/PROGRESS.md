# Package 30, review fixes 2: progress

Step 1 (Claude agent, Opus 5.5, 2026-11-14) stopped at a clean point after about 90 tool calls.

## Done (committed and pushed)

- `origin/main` merged (packages 31 and 34; `os/ci/image-checks.sh` kept both blocks).
- All six code fixes, one commit each, each with tests in `os/tests/test_aresos_shell_review_fixes_2.py` (and one
  changed test in `test_aresos_shell_review_fixes.py`). Every part of every fix was taken out alone with a scratch
  mutation script and its tests failed then; the table is in REPORT.md, "Review fixes 2".
- REPORT.md: review fixes 1's claims corrected (controls named, the FlatpakAppIdTest count withdrawn, nit 6's visible
  consequences, the superseded JUDGMENT-CALL), and the whole "Review fixes 2" section.
- `os/ci/image-checks.sh`: `rm -rf /tmp/pkg31-home` right after package 31's `gsettings` call.
- Laptop: `test_aresos_shell*.py` 271 tests OK; `check_aresos_shell_icons.py` 7 OK.

## Left, in order

1. On the laptop: `check_aresos_shell_launch.py` (real `systemd-run --user --scope`, a stand-in only) and
   `test_window_frame.py` (package 31's, since `image-checks.sh` changed); then `test_aresos_shell*.py` once more.
2. The headless end to end: `python3 os/tests/check_aresos_shell_headless.py` (kcalc and btop), only while no Java runs
   from `~/.lunarclient/` and `free -g` shows at least 4 GB available; it prints `HEADLESS_KCALC_BTOP_PASSED` and
   `owned processes and scopes stopped`. Check afterwards that no `app-aresos-check*` unit is left.
3. Both hosted runs on the pushed head: `gh workflow run "OS image" --ref pkg/30-installed-programs -f checks_only=true`,
   then `-f check_build=build`; each awaited with one `gh run watch <id> --exit-status` in the background.
4. Replace the "PENDING" line under "Verified (review fixes 2)" in REPORT.md with 1 to 3's commands, counts, run URLs
   and results; delete this file; commit; push.

## Not in the code

- The mutation script and its list lived in the step's scratch folder; the REPORT table records what each run showed.
- The SVG pre-check child must run with the converter's environment (`LC_ALL=C`): with a UTF-8 locale, glibc maps the
  223 MB locale archive and a Python child no longer fits under the 256 MiB ceiling (seen while building FIX 2).
