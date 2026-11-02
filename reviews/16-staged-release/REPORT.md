# 16: staged release and native mounted-child refusal

**Done:** `docs/INSTALL-STATUS.md` quotes the owner's 2026-11-02 staged-release decision. A releases preparation/backup/recovery/installer test boot only; B requires checked A and owner fitting evidence; C still requires checked A/B, the native condition and a maintainer table update. Every physical gate retains its evidence and now says how the owner and maintainer close it. `docs/INSTALL.md` marks the three boundaries and the per-step review requirement during C. Battery warnings still require a qualified repairer first.

`os/ci/owner_devices.py` adds a real, read-only-mounted protected ESP stand-in. The real `owner.disk_record` and `owner.install` (checked private bootstrap copy) must both refuse with exactly `Protected disk is mounted`. Both image SHA256s, native partition tables, the whole mount inventory and target file inventory must remain unchanged. A stand-in omitting exactly the mounted-child requirement must be rejected by the same refusal oracle. Cleanup checks every partition for mounts, verifies loop backing before detach, confirms neither loop nor backing remains attached, compares the complete mount inventory and checks both hashes again after detach.

Fixture limits remain explicit: loop root type/serial/USB identity, mapped guest EFI mountpoints, synthetic firmware, supplied photographed serials and private install HOME. The install-only `findmnt` adapter maps the verified FUSE mount type to the native volume's independently queried exFAT type; partition trees and protected mountpoints are never invented. Local walks use closed subprocess stand-ins; only the authorized hosted probe may execute native fixture operations.

Package 16 dispatches only the owner-tools **probe**, with its own 120-minute ledger, probe cap 2, no qualification/publish allowance, organization reserve 150 and zero push/closing privacy reservations under 14zw. Matching runner/auth/VM/native guards admit package 16 only for that probe. Existing bad-proof tests now supply valid runner context and assert proof read counts for both packages, so early runner refusal cannot hide a broken proof check. Package 14's retained records and allowance are unchanged.

`os/manifest/ci/16/host-walk.json` retains this package's synthetic host walk. Its source receipts bind 244 unique Git checkout byte sequences across six tables, including CRLF PowerShell files. Package 14's historical walk/preparation/probe/qualification records remain untouched.

**Verified locally:** WSL uses worktree `TMPDIR=.work/16/tmp` with `PYTHONDONTWRITEBYTECODE` unset. Logs and local runners are in ignored `.work/16/`.

- `python3 -B -m unittest discover -s os/tests -p 'test_owner*.py' -v`: **334 tests /2105.377s, OK, zero skips**. `python3 -m unittest discover -s os/tests -p 'test_owner*.py' -v`: **334 tests /1863.645s, OK, zero skips**.

- Affected WSL suites: `python3 [-B] .work/16/affected.py`, discovering `test_checkout_sources.py`, `test_ci_api_permissions.py`, `test_ci_step_environment.py`, `test_rehearsal*.py`, `test_job_accounting.py`, `test_organization_budget.py`, `test_installer_webui.py` and `test_keyboard_vm.py`: **85 /88.484s with -B**, **85 /92.787s without -B**; each prints **FAILED (failures=1)**, zero skips. The same sole failure is the retained Windows-backed-filesystem `0600` assertion described below; the other 84 tests pass in both runs.
- Focused native walk: **14 tests /42.312s, OK**, including omission of the real mounted-child check, wrong refusal, target-file mutation and failed-cleanup cases.
- Focused guard: **12 /0.256s, OK**; capabilities **6 /0.601s, OK**; staged probe policy **7 /0.040s, OK**. These are local fixtures, not native mounts.
- Git checkout filter replay: **244 bindings, PASS**. `checkout_sources.verify_git(root, rows, ref=None)` against the staged Git index: **244, PASS**. Committed-head proof follows after the source commit.
- `pwsh -NoProfile -File os/tests/owner-tools.Tests.ps1 -Bundle os/owner-tools/payload -Work .work/16/windows-tools`: manifest PASS twice, ARESTOOLS ready, **17 destination refusals with zero writes; copied payload equals source**.
- `pwsh -NoProfile -File os/tests/owner-pass.Tests.ps1 -Bundle os/owner-tools/payload -Work .work/16/windows-pass`: **78 record checks**, **4 documented Windows PASS results equal captured entry stdout**, no hardware queries/writes; PowerShell **7.6.9**.
- Python compilation of CI, overlay and owner-tools modules; Bash syntax of the owner launcher, CI and release scripts: **PASS**.
- In `mod/`, `./gradlew.bat build runClientGameTest` twice: **BUILD SUCCESSFUL in 9m55s** (18 executed, 1 up-to-date), then **8m4s** (4 executed, 15 up-to-date). Generated screenshots are under [screenshots/mod-client-tests](screenshots/mod-client-tests/). Existing packages' screenshot files were restored after retaining these copies. `./gradlew.bat --stop`: **1 Daemon stopped**.
- Publisher-checksum-verified **gitleaks 8.21.2**: archive SHA256 `f238c85e5f47e18fac779ce71ee11091cf70a0a8fb4415f165efba2800eef133`; `git . --log-opts="--all --full-history -m" --redact=100`: **739 commits, scan completed in 58.8s, no leaks found**, exit 0. The committed head and privacy-hook range are checked again before pushing.
- Local budget gate: **0 package-16 dispatches**, 763 organization minutes used, 1,237 free minutes left, 72 reserved, 1,165 afterward, reserve 150 preserved; free-minutes-only, no paid-budget request. Refreshed authorization is required immediately before dispatch.

Initial checks exposed and fixed a documentation assertion wording mismatch, a closed `findmnt --target` stand-in that did not resolve a subdirectory to its containing mount, and the package-14-only capability/credential-cleanup workflow expectations. An initial full OS `-B` attempt was interrupted after the stale capability expectation failed; no green full-suite result is claimed for that attempt. An early binding replay correctly refused sources edited while the receipt was being generated; final receipts were regenerated after source edits ended. Local CLI wrappers needed LF endings and Windows Git for the worktree's Windows gitdir; no repository/system configuration was changed.

**Native probe:** not dispatched yet. The mounted-child status row stays OPEN until the completed run and its cleanup proof have been inspected and retained here.

**Not verified:** owner Stage A/B records, physical fitting, the phone/keyboard/media/NVIDIA/Windows/credential/early-hardware gates and Stage C release. A native loop pass does not qualify physical hardware or release C. This package changes no OS image, owner-tools payload, Windows helper or mod source.

**JUDGMENT-CALL:** the release policy is the owner's explicit decision in brief 16, not a new agent decision. "No SSD writes" during A means no installation writes; Windows preparation and record files still write Windows normally, as the existing guide already explains. No new hard-to-undo decision.

**PLAN-GAP:** on this worktree's Windows-backed WSL filesystem, the unchanged credential test requests mode `0600` but observes `0777` (`511 != 384`). That assertion is retained; no skip or filesystem setting change is used. Local affected-suite failures and the hosted Linux rerun are recorded separately below.

**Open questions:** none new. Maintainer evidence checks and release-table updates for B/C remain required.
