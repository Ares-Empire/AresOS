Codex gpt-6.2-sol high, read-only, at a9e7c522, 2026-11-22

Lead: 2 and 3 resolved; 1's behaviour resolved, its test evidence fixed first in step 4.

CHANGES-NEEDED

1. **NOT RESOLVED — teardown evidence.** The backend exits after bounded teardown on Off or last-session close, including when startup observes Off. Concurrent `--release` waits for labwc’s confirmation or takes the pidfd fallback. The one-armed-session rule, `--revoke`, forwarding gate, and bus-only discovery while Off are preserved. The VM gate fails on `pidfd_getfd` errors other than `EBADF` from a vanished descriptor.

   Test 8 claims the reactivated backend exited after Off, but it checks only that the D-Bus name lost its owner. Pin that process before Off and wait for its pidfd to become readable, as the VM gate does. The same test claims capture ended by the `--revoke` reply, but checks local input after waiting for process exit. Change that assertion’s wording to report eventual teardown. `os/input-portal/harness/driver.py:1255`, `os/input-portal/harness/driver.py:1301`

2. **RESOLVED.** The image check requires `rpm -V deskflow` to exit 0. The known limit records that manual replacement can restore Fedora’s entry and that ordinary image updates repeat the exclusion. `os/ci/image-checks.sh:711`, `reviews/321-deskflow-image/KNOWN-LIMITS.md:137`

3. **RESOLVED.** The prompt defaults to rejection. The saved run with real Deskflow peers and the real Qt prompt shows Enter and explicit rejection saved nothing, deliberate acceptance saved exactly one fingerprint, and a different certificate was refused. `os/config/usr/libexec/aresos-deskflow:153`, `.work/step3-round2/pairing.log:20`

Read-only recheck of `a9e7c522`. Diff and syntax checks passed. No files changed or builds or integration tests rerun. The hosted VM gate remains pending.