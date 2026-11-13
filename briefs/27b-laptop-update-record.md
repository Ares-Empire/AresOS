# 27b: record the laptop's update to release 27

Follow-up to `briefs/27-first-update-release.md`. Empire brief 274.

**Goal:** `docs/INSTALL-STATUS.md` says what is true since 2026-11-13: the owner's laptop runs release 27, reached through the step 8 update route, with release 13 as its rollback and the corrected stock still pinned. Nothing else changes.

**Evidence the maintainer checked:**

- The guiding session's report (`mac-aresos-install`, board #189, 2026-11-13 13:47). It followed the owner through the route and checked each screen: the tools updated themselves from version 1 to 2, then `at update`, `at title`, `at export` and `at reboot` passed; after the restart the check was confirmed, and records, typing and password sudo passed; the owner set `ares`'s password and `sudo -v` passed. `at previous` was not used. Two earlier bootstrap attempts stopped on typing mistakes before anything was installed.
- A read-only check on the laptop itself (`linux-aresos`, 2026-11-13 14:22): the booted deployment is R27 (`sha256:5fad242f…d944c`), the second is R13 (`sha256:9b19b794…f3eb`), the third is the pinned stock `bazzite-nvidia-open:stable`; the transaction state is idle; `ares` is in `wheel`.
- Raw records stay private and off this public repository.

**In scope:**

- `docs/INSTALL-STATUS.md`:
  - the "as of" line at the top;
  - the R13 and R27 lines (R27 runs on the laptop since 2026-11-13; R13 is its rollback);
  - the Stage C row: step 8 PASSED on 2026-11-13, replacing "No step 8 update has run";
  - the update route row: no longer NOT USED. It was used once on the laptop on 2026-11-13; say what ran and passed, that `at previous` has run in the VM rehearsal only, and that after this first update the stock rollback, keep-stock, recovery-menu and layout-trial procedures refuse until package 22c (the guide already says so). Keep the rehearsal evidence and the announcement text.
- `os/tests/test_owner_path.py`: the phrases it pins in those rows move to the new truth, with the same strictness. The test must still fail when a row claims less or more than the record.
- Whatever the repository's own mechanism asks for when a bound document changes (`os/manifest/ci/16/pending-rebind.json` and the like). Follow it; do not regenerate rehearsal evidence.
- A short "Laptop update recorded (27b)" section at the top of `reviews/27-first-update-release/REPORT.md`.

**Out of scope:** `docs/INSTALL.md`, `docs/EMERGENCY.md`, the tools, the image, `STATE.md` and `HANDOFF.md` (the integrator updates those), the Early hardware row (brightness and power button stay as they are until 21b), and anything that belongs to 22c.

**Acceptance:**

- `git diff main --stat` shows only the files named above.
- The changed test passes, and fails when the Stage C row or the update row is put back (revert proof, shown in the report).
- The test modules that read the owner documents pass (`test_owner_path`, `test_owner_equality`, and any module that binds `INSTALL-STATUS.md`). Do not run the full suite locally: another package is running it on this machine, and the owner is using the laptop. The integrator runs the hosted checks on the PR.
- No serials, no names, no personal data; the text reads as the other rows do.

**Already decided:** the update was the owner's own step and is done. The status table states facts with their evidence and limits, never more than the records show.

**If unsure:** claim less, leave the gate as it was, and say so in the report.

**Model:** a Claude agent on Opus (a routine document and test change). Review: a fresh Codex context.
