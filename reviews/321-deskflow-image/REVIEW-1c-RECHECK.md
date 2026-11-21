# Package 321 step 1c: recheck of review findings 7 and 8 (Codex gpt-6.2-sol high, read-only, fresh context, at 7d38fa7b, 2026-11-21)

SAFE

**7 — RESOLVED.** One `sh -c` waits for `--release` to return, then launches the recovery stand-in even if release fails. Both saved test10 runs show the new window receiving the next key press and release during capture. Step 3 specifies the same sequence for the image’s `rc.xml` and keeps the separate `hide-cover` action. `os/input-portal/harness/in-container.sh:70`, `os/input-portal/harness/driver.py:1380`, `reviews/321-deskflow-image/PROGRESS.md:410`

**8 — RESOLVED.** Every harness run checks both binaries against the checkout’s loaded-image and normalized SHA-256 pins before starting tests. The saved wrong-pin run stopped at that gate. CI checks the finished image’s binaries against its manifest lock and compares that lock with the checkout’s copy. `os/input-portal/harness/run.sh:67`, `os/labwc/stage.py:319`, `os/ci/image-checks.sh:606`, `os/ci/check-image.sh:73`

The CI wrapper preserves the working directory and the script’s `set -e`. Tar consumes the input stream, and the existing checks supply any stdin they need. The script’s new `$0` points to the extracted file and locates the checker. The other `$0` belongs to a generated fixture. `os/ci/check-image.sh:14`, `os/ci/image-checks.sh:4`, `os/ci/image-checks.sh:439`

Read-only review and shell syntax checks completed. The finished-image check and the actual recovery terminal were not run.
Lead: 7 and 8 resolved; 1 to 6 are known limits (REVIEW-1c.md). Step 1c is done once check builds 44935351683 and 44937064135 are green.
