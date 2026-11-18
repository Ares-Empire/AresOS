# 311c: bind the labwc build to the locked Fedora digest

**Goal:** a release can never build labwc on one Fedora image while its lock records another. Briefs 311 and 311b stay in force.

**The defect (review 1, blocking):** `os/Containerfile`'s `labwc` stage names a Fedora digest in `FROM`, and `check_build=resolve` uses the digest in `os/labwc/labwc.lock.json`. Nothing compares the two. If they drift apart, the build environment check still passes, because it compares only the installed package list.

## In scope

1. The image build refuses, with one clear `LABWC_REFUSED` line and before any build dependency is installed, when the Fedora digest the `labwc` stage is built from differs from the lock's digest.
2. A test in `os/tests/test_labwc_stage.py` shows the refusal fires on a mismatch and stays quiet on the real files, and it runs the real check, not a copy of it.
3. If the check needs a file in the build context that the context excludes today, make the smallest change that provides it, and say so in `PROGRESS.md`.

## Out of scope

Everything in `reviews/311-labwc-pointer-lock/KNOWN-LIMITS.md`. Do not change the patch, the lock's pins or the other guards.

## Acceptance

1. Change the digest on one side in a scratch copy and show the build stops with the new line before dependencies are installed. Record the command and output in `PROGRESS.md`.
2. `podman build --target labwc` on the real files still produces `labwc-0.9.6-1.fc44.aresos1.x86_64` with the same SHA-256 as before, `e5e33686e6e30e9c74132ce145ffe3aaa0948a612c9047f8b2067be04f25364d`. If the hash differs, explain why.
3. `test_labwc_stage` and `test_aresos_desktop` pass.
4. `rebind.py pending` is run again if a bound file changed.

Brief 311's limits all hold: no hosted workflows, no merge, no push to `main`, nothing on the running laptop.

**Model:** Claude Opus 5.5: a small fix with a clear check.
