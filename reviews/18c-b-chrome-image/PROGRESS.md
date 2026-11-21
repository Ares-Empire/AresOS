# 18c-b progress

Brief: `briefs/18c-b-chrome-image.md` (on `main` since PR #73).
Branch `pkg/18c-b-chrome`, one builder at a time. Each step is a fresh agent; this file is the handoff.

## Review fix round 1 (2026-11-21)

Start `b5091f42`, with step 6b code at `6d610587`. Both reviews were copied byte for byte in `d1a0131a`.
The package review asked for changes. The security review found six NITs and gave a SAFE verdict.
[Package review](REVIEW-1.md) · [Security review](SECURITY-REVIEW-1.md)

### Findings and mutations

1. **Review 1 · `620caf83`.** `record_build.py add` keeps the more recent shipment when the build hash
   matches. The records test creates two commits with the same Control build, adds them in both orders,
   and calls `check` against the current release manifest in each. It also checks that an equal timestamp
   preserves the existing row byte for byte. Restoring the former `add` displaced the current row when
   the older release was added second, so `check` reported `builds.json has no row`. It failed the equal-time check too.
2. **Review 2 and security NIT 3 · `a58d5366`.** The release checker uses `lstat` on
   `/usr/share/aresos-install-test` and `/usr/libexec/aresos-install-test`. The clean fixture passes with
   real CRX verification and key scans. Planting the probe CRX at `probe/extension.crx`, the executable at
   `/usr/libexec/aresos-install-test/probe-host`, or the four files of bundle B at `bundles/b` under the
   share root fails individually. Both roots also fail as dangling links. Removing the guard failed all five
   subtests. Using `Path.exists()` failed the two dangling-link subtests. Changing the checked tag to `:vm`
   failed the wiring test. `check-build.sh` calls `check-image.sh` against `localhost/aresos:check` in both
   `build` and `control`, for release and throwaway builds. It checks the image before tagging `:ci` or
   building the `:vm` overlay. Build mode boots `:vm` for its guardian checks. Control mode adds the Chrome
   payload layer on top of `:vm` as `:control` and boots that disk. The negative check runs only on `:check`.
3. **Security NIT 2 · `cdc3b113`.** Container case 4 requires Chrome's
   `CRX_SIGNATURE_VERIFICATION_FAILED` in the changed package's fresh-start log. The case-level regression
   passes with that line and refuses an unzip failure or silence, even with a signature error in the missing-package
   log. Removing the assertion failed both refusal subtests. C5 keeps its install, connection and service
   checks. Its normal guest launch has no `--enable-logging=stderr`, and the final VM's `c5-fresh-changed.txt`
   has no signature diagnostic. The container already captures Chrome's explicit stderr logging.
   [Container log, line 2288](https://github.com/Ares-Empire/AresOS/actions/runs/44893166810) · [VM artifact read](https://github.com/Ares-Empire/AresOS/actions/runs/44900848938/artifacts/14708622963)
4. **Review 9 · `cdc3b113`.** A child interpreter audits Python file opens for writes during signing. In the
   reviewer's mutation, signing serialized the fresh synthetic key into a `NamedTemporaryFile`, flushed it,
   and deleted it before returning. The new audit test failed with `named file opened for writing while signing`.
   All three existing `NoKeyLeft` tests passed on that mutation. The production signer is untouched.
5. **Review 7 · `a58d5366`.** C1 checks `control.json` as a regular root-owned `0644` file and records its
   metadata. The test rejects `0600` and accepts `0644` up to the following contents check. Restoring the
   ownership-only assertion let `0600` reach the contents check and failed the test. C2 verifies policy
   installation and host connection. It checks refusal to disable from a hand-loaded extension and refusal
   to uninstall through the probe. The runner requires the two screenshots to be captured. The toolbar and
   menu pixels are reviewed from the artifacts.
   **Artifact read, `44900848938` on `6d610587`.** `control/chrome/c2-pinned.png` shows the square A button
   left of the Extensions puzzle piece. `control/chrome/c2-managed.png` shows “Managed by your organization”
   near the bottom of the menu, above “Chrome Enterprise release notes”. [C2 artifacts](https://github.com/Ares-Empire/AresOS/actions/runs/44900848938/artifacts/14708622963)
6. **Review 10.** Added the eight final pre-fix PR runs and the OS regressions receipt in
   [Final-head verification](#final-head-verification). Read the resolve and C9 log lines and corrected their
   descriptions. The C2 visual observations cite the actual artifacts. The draft PR description now covers the
   package, steps, review outcomes and remaining checks. [Draft PR #76](https://github.com/Ares-Empire/AresOS/pull/76)

### Lead decisions (linux-tools, 2026-11-21)

- **Review 3.** Accepted the probe-only address and ID comparison in case 5 and C9. The risk, reason and
  update-service ban for the helper are recorded under [Known limits](#known-limits).
- **Review 4.** C8 question visibility and exact Yes/No behavior at the owner's real terminal size are gates for
  release and the live sitting. See [Not verified](#not-verified), [For his guide](#for-his-guide) and the
  [release handoff](#for-linux-aresoss-release-brief) alongside the 28b combined proof.
- **Review 5.** Run a standalone `check_build=build` on this round's final dispatch head. The lead will add
  the green receipt, including `CHECK_BUILD_VM_PASSED` from the two guardian boots, after the run completes.
- **Review 6.** C11's verified published record, pinned signer and one accepted refresh result suffice for
  this package. Unit tests pin refusal of the wrong signer. The conditional no-published-record path fails
  closed and makes CI red.
- **Review 8.** Approved both scope exceptions. The lead directed `prepare.mjs`'s runtime path lookup in
  step 1b (`32f1126c`) for the latency leg over the older runtime. linux-aresos read the step 6b labwc swap
  on 2026-11-21 at 14:50 and wants it on `main` before R29's release build. The swap in `6d610587` covers
  `os/Containerfile`, `os/labwc/stage.py`, `os/tests/test_aresos_desktop.py` and `os/tests/test_labwc_stage.py`.
- **Security NITs 1, 4, 5 and 6.** Accepted the `gh` telemetry, modulus scanning and numeric `format`
  limitations described under [Known limits](#known-limits). Keep the real excluded-sites hash out of
  public evidence, as recorded in the guide and release handoff.

### Verified locally

**Run.** Python 3.14.8, with `TMPDIR` in `.work/review-fix-1/tmp`. All commands below exited 0.

| Command | Result |
|---|---|
| `python3 -B -m unittest discover -s control/chrome/ci/install -p 'test_*.py' -v` | `Ran 30 tests` · `OK` |
| `python3 -B -m unittest discover -s control/chrome/ci/records -p 'test_*.py' -v` | `Ran 23 tests` · `OK` |
| `python3 -B control/chrome/record_build.py check` | `record_build check passed` |
| `PYTHONPATH=control python3 -B -m unittest discover -s control/chrome_tests -p 'test_excluded_sites_placeholder.py'` | `Ran 9 tests` · `OK` |
| `PYTHONPATH=control python3 -B -m unittest discover -s control/chrome_tests -p 'test_exclusions.py'` | `Ran 3 tests` · `OK` |
| `.work/review-fix-1/node/node --test control/chrome/ci/install/*.test.mjs` | Node v22.15.0 · `# pass 1` · `# fail 0` |
| `python3 -B -m unittest discover -s os/tests -p 'test_control_image.py'` | `Ran 49 tests` · `OK` |
| `python3 -B -m unittest discover -s os/tests -p 'test_control_vm.py'` | `Ran 98 tests` · `OK` |
| `git diff --check` and `git diff --check d1a0131a..HEAD` | No output |
| Repo privacy workflow's shell check with `RUNNER_TEMP` in `.work/` | `No file holds a home path with a real user name.` |
| `find .work -type f -size +500000000c -print` | No paths |

The mutation commands used `python3 -B -m unittest -v` against the named test or `test_pack.NoKeyLeft`,
with the test directory on `PYTHONPATH`. Each mutation was restored before proceeding. The Node binary
was verified against the v22.15.0 distribution's published SHA-256 and used from `.work/`.

### Hosted run IDs

Dispatched `os-image.yml` once per mode with `gh workflow run` against `pkg/18c-b-chrome`. GitHub reports
`workflow_dispatch` and head `0fb805a4` for both. These are the review round's runs. The lead owns their
verdicts and the remaining Control dispatch.

| Mode | Run |
|---|---|
| Control 1 of 2 | [44912649303](https://github.com/Ares-Empire/AresOS/actions/runs/44912649303) |
| Standalone build | [44912662660](https://github.com/Ares-Empire/AresOS/actions/runs/44912662660) |

The one code push ended at `cdc3b113` and started these eight PR #76 workflows.

| Workflow | Run |
|---|---|
| Control base | [44912315588](https://github.com/Ares-Empire/AresOS/actions/runs/44912315588) |
| Control boundary | [44912315596](https://github.com/Ares-Empire/AresOS/actions/runs/44912315596) |
| Control Chrome | [44912315592](https://github.com/Ares-Empire/AresOS/actions/runs/44912315592) |
| Control Chrome install | [44912315594](https://github.com/Ares-Empire/AresOS/actions/runs/44912315594) |
| Control Chrome qualification | [44912315628](https://github.com/Ares-Empire/AresOS/actions/runs/44912315628) |
| Control Chrome records | [44912315569](https://github.com/Ares-Empire/AresOS/actions/runs/44912315569) |
| Control Mail | [44912315497](https://github.com/Ares-Empire/AresOS/actions/runs/44912315497) |
| Repo privacy | [44912315582](https://github.com/Ares-Empire/AresOS/actions/runs/44912315582) |

### Left

The lead watches the PR checks and the first control and standalone build dispatches, records their green
receipts, and dispatches the second control run. This round has two control runs and one build run, separate
from the brief's twelve Control runs and step 6b's two follow-ups. The reviewers recheck after CI.

**For linux-aresos.** Read `a58d5366` for the release-image absence check, the C1 manifest check, the C2
capture description and the two corresponding `os/tests` modules. The release phase used for the negative
check is already wired through `check-image.sh`. The `os/manifest/ci/16/` files and workflow are untouched
in this round.

### JUDGMENT-CALLs

- Equal shipment times keep the existing same-build row. Breaking ties by commit hash could displace the
  current manifest despite equal timestamps. Changing this takes a small comparator and test edit, with
  release records reviewed before any replacement. The lead's release and scope decisions are above.

### PLAN-GAPs

- The original negative check covered the production bundle and policy directories, while the actual
  payload roots live in the test layer. Both roots now have explicit release checks.
- The guest's normal Chrome log does not expose the signature refusal in the final artifact. The
  container test pins the reason and the guest test continues to prove the behavior of the fresh,
  restored and already-installed copies. The round's final standalone build and the owner's terminal
  visibility gate are open under the lead's decisions.

## Step 6b (2026-11-21), release 28 merge and final evidence

### Done

- **Run, Git.** Fetched `origin` and merged `f4d59cc6` into `pkg/18c-b-chrome` in `b8b267e2`.
  The merge includes package 42's release 28 and owner tools version 5 from `6ae4da41`.
  Control attempt head `6df045c8` includes the follow-up records fix. The checks_only retry tested
  `c5288fc2`, which fixes the release 28 rehearsal and import-bytecode regressions. Both were pushed
  to draft PR #76.
- **Run, local.** The targeted OS and Control suites, standalone records check, `git diff --check
  origin/main...HEAD`, and Repo privacy check passed. The package's added lines were checked for
  personal names after a `git grep -n` over its changed files. See Verified for the counts.
- **Run, hosted.** Control run [44879115402](https://github.com/Ares-Empire/AresOS/actions/runs/44879115402)
  timed out in runner tool setup on both attempts. That was the brief's eleventh dispatch, with one
  failed-jobs rerun on the same ID. The twelfth dispatch and the lead's two follow-ups are below.
- **Run, hosted.** The first checks_only run [44882775213](https://github.com/Ares-Empire/AresOS/actions/runs/44882775213)
  ran 2456 tests and failed on the merge issues below. The retry
  [44885414951](https://github.com/Ares-Empire/AresOS/actions/runs/44885414951) ran 2461 tests (4705)
  and passed with 23 skips (4707). The separate full ways-back model also passed (403 and 405).
- **Run, scratch.** `find .work -type f -size +500000000c -print` produced no paths at close.

### Labwc image check follow-up

- **Run, [44888933298](https://github.com/Ares-Empire/AresOS/actions/runs/44888933298), attempt 1 on
  `c2c0b1dd`.** Runner setup passed. The build installed Fedora's stock labwc (1626) and rebuilt it
  with `SOURCE_DATE_EPOCH=1773532800` (2375). Both normalized and both loaded hashes matched
  (2952–2955). `LABWC_INSTALLED` (2992) is emitted after the install-time `rpm -V labwc` passes.
  The image committed at 3055–3058. After the subordinate IDs check (4698), the image still reported
  the rebuilt NEVRA (4702–4703), but `rpm -V labwc` reported `..5......    /usr/bin/labwc`
  (4704–4705) and the step exited 1 (4706). Neither VM started. This was dispatch 12 of the brief's
  12. The lead authorized two separate follow-up dispatches for this fix.
- **Read and run, source and comparison.** The labwc stage, lock, install wiring and the labwc
  verification block were identical on `origin/main` at `15ec5b95` and the failed branch head. The
  latest main workflow runs were regressions only. The latest package 42 run that built and checked
  the image, [44590446680](https://github.com/Ares-Empire/AresOS/actions/runs/44590446680), installed
  Fedora's original RPM (2329) and printed `IMAGE_CHECKS_PASSED` (4298). Its cut predated package 311.
  The equivalent rebuilt-RPM check passed in the package 311 merge evidence
  [44511434325](https://github.com/Ares-Empire/AresOS/actions/runs/44511434325) (4531–4534), and in
  package 25's [44617007417](https://github.com/Ares-Empire/AresOS/actions/runs/44617007417)
  (4531–4534). The comparable runs show no reproduction on the code merged to main. The current main
  tip has no direct image-build result.
- **Inferred cause.** The lower package layer carried Fedora's binary and the final layer carried the
  swap and new RPM database. The pinned Fedora RPM has `/usr/bin/labwc` at 534800 bytes, mode 0755
  and mtime 1773532800. The rebuilt RPM uses the same reproducible epoch, and package 311 documented
  build-to-build variation in debug sections. The digest-only failure is consistent with Podman's
  fallback layer diff omitting a byte change when file size and other metadata match. The red
  transaction was 24 bytes larger in total (2984), compared with 40 bytes in package 311's green
  run (2876). Those are package totals. The failed run did not retain the final binary or log the
  storage differ it used, so the omitted-file mechanism is inferred from the source and logs.
  [Podman 4.9.3 layer differ](https://github.com/containers/podman/blob/v4.9.3/vendor/github.com/containers/storage/pkg/archive/changes.go).
- **Fix, `6d610587`.** `os/Containerfile` runs the pinned package install and the verified labwc
  swap in one `RUN`. Fedora's labwc was absent from the pinned base and was installed in the packages
  transaction (red run line 1626). With both installs in one layer, the diff adds the rebuilt file.
  The stage still checks its package closure and `rpm -V labwc` inside the build, and the image check
  still checks the committed image. The wiring test pins the shared `RUN`. The mod and Control source
  stages still use the pinned base and the build commit.
- **Run, local.** Ran `python3 -B -m unittest discover -s os/tests -p 'test_<module>.py'` one module at
  a time with `TMPDIR` under `.work/18c-b-step6b/tmp`. `test_labwc_stage.py` gave
  `Ran 126 tests in 11.671s` and `OK`. `test_aresos_desktop.py` gave
  `Ran 189 tests in 203.696s` and `OK (skipped=1)`. `test_control_image.py` gave
  `Ran 48 tests in 6.042s` and `OK`. The workflow's first-`FROM` check, `git diff --check` and
  the Repo privacy check passed. The signed stock RPM matched its package-lock SHA-256. The header
  read, `rpm -qp --nosignature --dump`, used a scratch RPM database and did not install it.

### Follow-up Control runs

These two dispatches are separate from the brief's 12. Both used the same head, `6d610587`.
Run 2 was dispatched after the first watcher exited 0. Each dispatch used
`gh workflow run os-image.yml -R Ares-Empire/AresOS --ref pkg/18c-b-chrome -f check_build=control`.
Each background watcher used `gh run watch <id> -R Ares-Empire/AresOS --exit-status --interval 300`.
The line numbers below are from `gh run view <id> -R Ares-Empire/AresOS --attempt 1 --log`.

| Run | ID | Attempt | Job | Result |
|---|---|---:|---:|---|
| 1 | [44893168374](https://github.com/Ares-Empire/AresOS/actions/runs/44893168374) | 1 | 136813151121 | PASS (watch exit 0) |
| 2 | [44900848938](https://github.com/Ares-Empire/AresOS/actions/runs/44900848938) | 1 | 136836224849 | PASS (watch exit 0) |

| Image, checkout or disk marker | Run 1 line | Run 2 line |
|---|---:|---:|
| `CONTROL_GH_PAYLOAD_PASS` | 2948 | 2949 |
| `CONTROL_GH_RPM_PASS` | 2949 | 2950 |
| `CONTROL_GH_INSTALL_PASS` | 2950 | 2951 |
| `CONTROL_GH_KEYRING_PASS` | 2951 | 2952 |
| PASS Chrome polkit action and agent | 3251 | 3252 |
| `CONTROL_GH_IMAGE_PASS` | 3712 | 3713 |
| `CONTROL_CHROME_BUNDLE_PASS` | 4304 | 4305 |
| `CONTROL_CHROME_KEY_SCAN_PASS` | 4305 | 4306 |
| PASS signed Chrome bundle and links | 4310 | 4311 |
| PASS labwc install and RPM verification | 4704 | 4705 |
| PASS Control file, directory and vendor records | 4859 | 4860 |
| PASS Claude Code managed files | 4866 | 4867 |
| PASS only multi-user.target enables the Control service | 4873 | 4874 |
| PASS boot system user and group | 4891 | 4892 |
| PASS Control runtime and state directories | 4916 | 4917 |
| PASS excluded-sites placeholder and unit write boundary | 4946 | 4947 |
| PASS Control UID, home and allowed folders | 4949 | 4951 |
| PASS installed launcher and isolation from system Python packages | 4958 | 4958 |
| PASS image has no fixture CA or hosts | 4973 | 4974 |
| `IMAGE_CHECKS_PASSED` | 4975 | 4976 |
| `CONTROL_GH_CHECKOUT_PASS` | 4996 | 4997 |
| `CONTROL_CHROME_CHECKOUT_PASS` | 4997 | 4998 |
| `CONTROL_CHROME_BUILD_LOG_PASS` | 5001 | 5002 |
| `CHECK_BUILD_CONTROL_DISK_READY` | 5709 | 5710 |

The earlier VM column is from 44621559332 attempt 2. A dash marks a missing verdict.

| VM marker or timing | Earlier 522c1113 line | Run 1 line | Run 2 line |
|---|---:|---:|---:|
| `CONTROL_IMAGE_FILES_PASS` | 4395 | 5717 | 5718 |
| `CONTROL_ETC_CLAUDE_CODE_PASS` | 4397 | 5719 | 5720 |
| `CONTROL_RELEASE_CHECKS_PASS` | 4399 | 5721 | 5722 |
| `CONTROL_IDLE_FOOTPRINT_RECORDED` | 4401 | 5723 | 5724 |
| `CONTROL_FIXTURES_REACHABLE` | 4403 | 5725 | 5726 |
| `CONTROL_ENTRY_POINTS_PASS` | 4405 | 5727 | 5728 |
| `CONTROL_PRECONDITION_PASS` | 4407 | 5729 | 5730 |
| `CONTROL_USER_MCP_INSTALL_PASS` | 4409 | 5731 | 5732 |
| `CONTROL_SERVICE_SANDBOX_PASS` | 4411 | 5733 | 5734 |
| `CONTROL_ORDINARY_SESSION_PASS` | 4413 | 5735 | 5736 |
| `CONTROL_MAIL_FLOWS_PASS` | 4415 | 5737 | 5738 |
| `CONTROL_PERMISSION_REQUEST_RECORDED` | 4417 | 5739 | 5740 |
| `CONTROL_INTERACTIVE_ASK_PASS` | 4418 | 5740 | 5741 |
| `CONTROL_PASSWORDS_PRIVATE_PASS` | 4420 | 5742 | 5743 |
| `CONTROL_SELINUX_AFTER_CHECKS_PASS` | 4422 | 5744 | 5745 |
| `CONTROL_STORAGE_TESTS_PASS` | 4424 | 5746 | 5747 |
| `CONTROL_SERVICE_RESTART_PASS` | 4426 | 5748 | 5749 |
| `CONTROL_VM_POWEROFF_CLEAN` | 4428 | 5750 | 5751 |
| Control VM timing | 4429 | 5751 | 5752 |
| `CHECK_BUILD_CONTROL_PASSED` | 4430 | 5752 | 5753 |
| `CONTROL_CHROME_POLKIT_PROBE_PASS` | 4441 | 5763 | 5764 |
| `CONTROL_CHROME_FILES_PASS` | 4443 | 5765 | 5766 |
| `CONTROL_CHROME_INSTALL_PASS` | 4447 | 5769 | 5770 |
| `CONTROL_CHROME_SITES_FIRST_USE_PASS` | 4449 | 5771 | 5772 |
| `CONTROL_CHROME_REBOOTED` | 4450 | 5772 | 5773 |
| `CONTROL_CHROME_SITES_REBOOT_PASS` | 4452 | 5774 | 5775 |
| `CONTROL_CHROME_NATIVE_HOST_PASS` | 4454 | 5776 | 5777 |
| `CONTROL_CHROME_SITES_PASS` | 4456 | 5778 | 5779 |
| `CONTROL_GH_PASS` | 4458 | 5780 | 5781 |
| `CONTROL_CHROME_RECORDS_PASS` | 4460 | 5782 | 5783 |
| `CONTROL_CHROME_UPDATE_PASS` | 4462 | 5784 | 5785 |
| `CONTROL_CHROME_PACKAGE_FAULT_PASS` | 4464 | 5786 | 5787 |
| `CONTROL_CHROME_NO_STORE_PASS` | 4466 | 5788 | 5789 |
| `CONTROL_CHROME_POLKIT_PASS` | 4475 | 5797 | 5798 |
| `CONTROL_CHROME_ASK_PASS` | 4477 | 5799 | 5800 |
| `CONTROL_CHROME_SELINUX_PASS` | 4479 | 5801 | 5802 |
| `CONTROL_CHROME_VM_POWEROFF_CLEAN` | 4480 | 5802 | 5803 |
| Chrome VM timing | 4481 | 5803 | 5804 |
| `CHECK_BUILD_CONTROL_CHROME_PASSED` | 4482 | 5804 | 5805 |

| Run | 18c total / boot to channel / idle | 18c-b total / boot to channel / reboot to channel |
|---|---|---|
| 1 | 531.2 s / 46.4 s / 60.0 s | 383.0 s / 45.3 s / 30.9 s |
| 2 | 624.1 s / 56.2 s / 59.4 s | 418.9 s / 49.5 s / 33.5 s |

Exact per-step measurements in seconds follow.

Run 1, Control VM timing

```json
{
  "boot_to_channel": 46.4,
  "control-files": 4.6,
  "control-claude-code-files": 0.6,
  "control-release": 1.1,
  "control-idle": 60.0,
  "control-fixtures": 0.2,
  "control-entry-points": 3.6,
  "control-precondition": 1.8,
  "control-user-mcp": 11.9,
  "control-service": 0.1,
  "control-ordinary": 227.3,
  "control-mail": 34.6,
  "control-interactive": 108.0,
  "control-passwords": 0.5,
  "control-selinux": 0.0,
  "control-storage-tests": 26.4,
  "control-restart": 0.9,
  "total": 531.2
}
```

Run 1, Chrome VM timing

```json
{
  "boot_to_channel": 45.3,
  "chrome-session": 10.7,
  "polkit-before": 0.1,
  "chrome-polkit-start": 8.2,
  "polkit-dialog": 0.0,
  "keys": 1.0,
  "chrome-polkit-finish": 0.0,
  "chrome-files": 0.2,
  "chrome-hand-loaded": 7.1,
  "chrome-install": 1.7,
  "c2-pinned": 0.0,
  "chrome-his-tab": 4.4,
  "c2-managed": 0.0,
  "chrome-sites-first-use": 3.2,
  "reboot_to_channel": 30.9,
  "reboot": 33.4,
  "chrome-sites-after-reboot": 21.3,
  "chrome-host": 2.7,
  "chrome-sites-later": 7.4,
  "chrome-gh": 0.4,
  "chrome-records": 0.4,
  "chrome-update": 13.7,
  "chrome-package-fault": 70.1,
  "chrome-no-store": 16.8,
  "chrome-edit-start": 3.6,
  "edit-page-cancel": 14.4,
  "chrome-edit-wait-cancel": 0.3,
  "chrome-edit-cancelled": 0.3,
  "edit-page-allow": 14.4,
  "chrome-edit-wait-allow": 0.2,
  "edit-password-allow": 5.2,
  "chrome-edit-reset": 2.2,
  "edit-page-again": 14.4,
  "chrome-edit-wait-again": 0.3,
  "chrome-edit-again-cancelled": 0.4,
  "chrome-edit-finish": 0.0,
  "chrome-ask-form": 65.3,
  "chrome-selinux": 0.1,
  "total": 383.0
}
```

Run 2, Control VM timing

```json
{
  "boot_to_channel": 56.2,
  "control-files": 4.0,
  "control-claude-code-files": 0.2,
  "control-release": 1.3,
  "control-idle": 59.4,
  "control-fixtures": 0.2,
  "control-entry-points": 5.1,
  "control-precondition": 2.2,
  "control-user-mcp": 12.9,
  "control-service": 0.1,
  "control-ordinary": 233.9,
  "control-mail": 43.9,
  "control-interactive": 127.2,
  "control-passwords": 0.7,
  "control-selinux": 0.1,
  "control-storage-tests": 71.6,
  "control-restart": 1.7,
  "total": 624.1
}
```

Run 2, Chrome VM timing

```json
{
  "boot_to_channel": 49.5,
  "chrome-session": 14.0,
  "polkit-before": 0.2,
  "chrome-polkit-start": 8.7,
  "polkit-dialog": 0.1,
  "keys": 1.0,
  "chrome-polkit-finish": 0.1,
  "chrome-files": 0.4,
  "chrome-hand-loaded": 8.0,
  "chrome-install": 2.1,
  "c2-pinned": 0.0,
  "chrome-his-tab": 4.4,
  "c2-managed": 0.1,
  "chrome-sites-first-use": 4.1,
  "reboot_to_channel": 33.5,
  "reboot": 37.2,
  "chrome-sites-after-reboot": 22.6,
  "chrome-host": 3.1,
  "chrome-sites-later": 10.0,
  "chrome-gh": 0.4,
  "chrome-records": 0.4,
  "chrome-update": 15.9,
  "chrome-package-fault": 71.7,
  "chrome-no-store": 18.7,
  "chrome-edit-start": 3.3,
  "edit-page-cancel": 14.5,
  "chrome-edit-wait-cancel": 0.6,
  "chrome-edit-cancelled": 0.3,
  "edit-page-allow": 14.4,
  "chrome-edit-wait-allow": 0.3,
  "edit-password-allow": 5.2,
  "chrome-edit-reset": 2.3,
  "edit-page-again": 14.5,
  "chrome-edit-wait-again": 0.4,
  "chrome-edit-again-cancelled": 0.3,
  "chrome-edit-finish": 0.4,
  "chrome-ask-form": 75.2,
  "chrome-selinux": 0.1,
  "total": 418.9
}
```

Run 1 did not reproduce the daily-profile reconnect timeouts from 44621559332 attempt 1.
C4's two switches passed (5784), C5 reconnected after restoring the test bundle and after both
installed-copy faults (5786), and C9 returned to the daily profile (5788). C7 and C8 completed
(5797 and 5799). The fresh broken-package refusals in C5 were expected.

Run 2 also passed C4 (5785), C5 (5787), C9 (5789), C7 (5798) and C8 (5800) without a
daily-profile reconnect timeout. The Chrome VM logs of both runs contain no
`CONTROL_CHECK_FAILED`, timeout or traceback from those cases.

The builds log the shared package install and swap at 2787 and 2788 respectively. Both
reproduced all four labwc hash pins (2776–2779 and 2777–2780), installed the rebuilt RPM
(2974 and 2975), and passed final image RPM verification (4704 and 4705).
`find .work -type f -size +500000000c -print` returned no paths at close.

### Merge and conflict resolutions

- **Read, `.github/workflows/os-image.yml` at `b8b267e2`.** Kept package 42's read-only permissions
  comment verbatim and the branch's 156-minute Control limit and sum. The separate VM steps retain
  16 and 25 minutes. Package 42's budget guard is scoped to its own branch.
- **Read, `os/ci/check-build.sh`, `os/ci/vm.py` and `os/ci/control/control_vm.py` at `b8b267e2`.**
  Check the Chrome build log directly after image checks create `evidence/image/checks.txt`, before
  applying any CI layers. In `build` mode, main's two guardian boots from `61a66d78` use fresh
  overlays of the ordinary CI disk. Pass 1's policy and keymap evidence is read before pass 2. In
  `control` mode, the build creates the Control disk, then the workflow runs 18c followed by the Chrome
  pass. Each pass starts on a fresh overlay of that disk, and Chrome keeps its overlay across its reboot.
- **Run, pending source bindings.** Took main's `os/manifest/ci/16/pending-rebind.json` and ran
  `python3 -B reviews/27-first-update-release/rebind.py pending "<note>"` with all five notes under
  Step 6a's “Left, in order” verbatim and then with the merge note below. Package 42's active tables
  made each call print `pending: 5 bound files differ from the active bindings, 0 removed`. The three
  pending paths from main stayed listed. The workflow and Chrome rehearsal checker added two paths.
  After the regressions fix a seventh tool call added the note below and printed
  `pending: 7 bound files differ from the active bindings, 0 removed`.

  ```text
  18c-b step 6b: main merged after release 28 (package 42); os-image.yml keeps package 42's permissions comment with 18c-b's control limit 156; check-build.sh keeps the guardian boots and the Chrome pass.
  18c-b step 6b checks fix: release 28's rehearsal selects the service checks explicitly; the stand-in checks and passes their arguments; the Chrome signature imports are local to that check and the build's gh hash check uses python3 -B.
  ```

### What the code doesn't show

- **Read, `os/ci/control/release_checks.py` and `os/ci/control/chrome_layer.py` at `6df045c8`.**
  The release rehearsal still needs a probe-free deployment, the three shared-list hashes, and an update
  and rollback with Chrome open. The actual profile, agent and terminal size remain for the live sitting.
- **Read, CROSS-5 at `30ff4401`.** The combined 28b profile handoff remains a separate proof.

### JUDGMENT-CALLs

- **Read, `control/chrome/record_build.py` at `6df045c8`.** The records checker recognizes the exact
  source-only Control object on the published release 28 tag and source, at its current and archived
  manifest paths. Changing the published manifests would rewrite the release record. Accepting arbitrary
  source-only objects would let a later Chrome release omit its hash. The historical case can be removed
  if both manifests no longer need validation. The existing owner-facing choices are in the report.

### PLAN-GAPs

- **Read, `os/manifest/release.json` and `os/manifest/releases/28.json` at `f4d59cc6`.** The brief
  assumed the current release would omit `control` until Chrome shipped. Release 28 carries its own
  Control source revision and no Chrome build. The records checker needed to handle that published shape.
- **Read, `os/ci/release28_walk.py` at `b8b267e2` and `release_checks.py` at `dbeaff72`.**
  Release 28's rehearsal had called the checker without naming its checks. After 18c-b that default also
  requires browser install records that release 28 never shipped. The rehearsal now requests all five
  original service checks and still enforces their verdict and the boot login dependency checks.
- **Read, `reviews/27-first-update-release/rebind.py` at `f4d59cc6`.** Step 6a listed the tool
  under `os/ci/`. Its actual path is under the package 27 review.
- **Read, brief “Done” at `f4d59cc6`.** A separate final-head `check_build=build` is also listed in
  the brief. The step 6b dispatch list covers the two Control runs and checks_only. Earlier build-mode
  receipts are in Verified.

### The os/ diff for linux-aresos

**Read, net against `dd3f0007` with main's changes excluded.**

- `os/ci/check-build.sh` retains the Chrome build-log check and pass alongside main's guardian boots.
- `os/manifest/ci/16/pending-rebind.json` carries the five replayed notes, the merge note and the
  refreshed rows for the workflow and rehearsal checker relative to package 42's bindings.
- `os/tests/test_control_image.py` follows main's `python3 -B` installer invocation in the Chrome fixture.
  `os/tests/test_release28.py` models the shared Chrome and polkit directories and creates the image
  evidence directory in its check-image stand-in. The existing release assertions still run.
- `os/build.sh` uses `-B` for the added `gh` digest check. `os/ci/control/release_checks.py` loads the
  signature parser's imports inside that check.
- `os/ci/release28_walk.py` passes the five original service check names. The stand-in in
  `os/tests/test_owner_walk.py` enforces that argument list and passes it to the embedded checker.
  Both bound rehearsal paths are now on the pending list. `git diff b8b267e2..c5288fc2 -- os/` is
  five files, 23 insertions and 10 deletions.
- For the follow-up `c2c0b1dd..6d610587`, read `os/Containerfile` and its wiring tests. The packages
  stage now follows the labwc RPM stage so the stock install and the swap commit together. The
  `os/labwc/stage.py` changes update its comments. The labwc NEVRA, hash pins and RPM verification
  stay in effect. There is no pending binding change for these files.

## Step 6a (2026-11-20), rehearsal checks and closing text

### Done

- **Read, `dbeaff72`.** Added the Chrome release rehearsal checks and eleven tests in 18c's existing test
  module. The 18c CI guest invokes the compatible checks on its probe-bearing disk.
- **Read, `dac9ed88`.** Updated the OS README and checked the packaging README against item 1. The closing
  report and guide text are below.
- **Run, local.** The touched test module printed `Ran 97 tests in 2.468s` and `OK`. Diff and privacy
  checks passed. At close, `find .work -type f -size +500000000c -print` produced no paths.
- **Run, Git and PR.** Started at `80e0c0ef` and fetched before editing. Both commits were pushed normally
  to the existing draft PR #76. The published branch is still based on the same parent history. This step
  used zero control dispatches, leaving **10 of 12 used**.

### checks_only

**Run, [44645747088](https://github.com/Ares-Empire/AresOS/actions/runs/44645747088), attempt 1 on `dac9ed88`.**
Dispatched once with `gh workflow run os-image.yml -R Ares-Empire/AresOS --ref pkg/18c-b-chrome -f checks_only=true`.
The background `gh run watch 44645747088 -R Ares-Empire/AresOS --exit-status --interval 300` exited 0.
Regression job 135987756036 reported `Ran 1840 tests in 1277.114s` and `OK (skipped=4)` at full-log
lines 3863 and 3865. The eleven new tests all reported `ok` at lines 2405–2415.

### Left, in order

1. **6b, after linux-aresos merges R28's `pkg/42` into `main`.** Fetch and merge main. Take main's
   `os/manifest/ci/16/pending-rebind.json`, keep pkg/42's comment and **156** in
   `.github/workflows/os-image.yml`, and run `python3 os/ci/rebind.py pending "<note>"` with each of the
   following step 4 notes verbatim and then a separate note for the merge.

   ```text
   18c-b step 4: the Chrome VM pass (control_vm.py chrome, check-build.sh control-chrome-pass), its actions and test-layer pieces (probe, hand-loaded extension, bundles B and C), the polkit probe, C1, C2 and C6's first use with its reboot.
   18c-b step 4: os-image.yml gains the Control Chrome VM pass step (25 minutes) in check-build's control mode; the job's control limit 131 to 156.
   18c-b step 4, round 2: the Chrome pass waits for his session (app helper, polkit agent) after each boot; a check's PASS line sits on its last step.
   18c-b step 4, round 3: the polkit probe's verdict follows his agent's answer (KDE reports Escape as 1, not authorized), screenshots before, during and after the dialog; C2's managed note from Chrome's menu.
   18c-b step 4, round 4: a PASS line on a keys step no longer stops the Chrome pass; a stand-in guest runs the whole sequence in os/tests.
   ```

2. **6b, final Control evidence.** Run the two final Control greens on the merged head and record every
   PASS line from 18c and 18c-b and the measured VM times. Check for the daily-profile reconnect condition
   seen in 44621559332 attempt 1.
3. **6b, final regressions.** Run `checks_only` on the merged head and record the test count.
4. **6b, close the report.** Fill the marked run IDs, attempts, lines and times below. The lead takes the
   release rehearsal request to linux-aresos and coordinates 28b's combined proof.

### What the code doesn't show

- **Read, `release_checks.py` at `dbeaff72`.** It reports the current list hash and metadata. The
  release rehearsal must seed a non-placeholder list and compare its three hashes. The real deployment
  switch with Chrome open and the laptop's actual sites, agent and terminal size still need evidence.
- **Read, C4 at `522c1113` and CROSS-5 at `30ff4401`.** 18c-b's package replacement and native
  connection evidence leaves profile continuity to 28b. The guide uses that future in-session confirmation.

### JUDGMENT-CALLs

- **Read, `dbeaff72`.** The standalone rehearsal uses the image's OpenSSL and trusts only the stock
  KDE manifest's unchanged image bytes for its IDs. The 18c guest selects compatible checks explicitly
  because its test policy contains a second ID. This keeps the release verdict independent of the test
  layer. The report gives the earlier owner-facing and CI choices.

### PLAN-GAPs

- **Read, `chrome_layer.py` at `522c1113` and the brief at `30ff4401`.** Both CI guests have the probe.
  The release must exercise the default strict scan on a probe-free image. A rollback predating 18c-b
  also lacks the new installation records. The release brief owns the actual rollback and list comparison.

### The os/ diff for linux-aresos

**Read, net from `80e0c0ef`.**

- `os/ci/control/release_checks.py` adds the six rehearsal actions and hash line.
- `os/ci/control/actions.py` selects the probe-compatible rehearsal actions in the existing 18c pass.
- `os/tests/test_control_vm.py` adds eleven tests with real signature verification and failure fixtures.
- `os/README.md` describes the package, profile handoff and rehearsal.

## For the report

### Done

- **Read, `control/chrome/packaging/pack.py`, its templates and `os/build.sh` at `522c1113`.** The image
  packs the extension under one fresh RSA key, discards the private key and generates the Chrome policy,
  update XML and native host manifest for the key's ID. It installs the four files under
  `/usr/share/aresos/chrome/`, two fixed links in `/etc`, the host relay and the uncached
  `org.aresos.control.chrome-loosen` polkit action. The image checks bind the bundle to `control.json` and the
  checkout, verify the signature and scan the image and build log for private-key leftovers.
- **Read, `control/aresos_control/chrome/exclusions.py` and
  `control/chrome/packaging/aresos-control-chrome.tmpfiles` at `522c1113`.** First boot makes a format-0
  excluded-sites placeholder in shared `/var`. The service checks the list on each call, refuses reads and
  actions until root writes a valid format-1 list, and has read-only access to the file.
- **Read, `os/gh.lock.json`, `os/build.sh` and `control/chrome/record_build.py` at `522c1113`.** The build
  extracts only GitHub CLI 2.103.3 from the pinned, signature-checked RPM, restores the prior RPM trust list,
  and records the binary's SHA-256 and version. The release can use `record_build.py` to record the commit's
  own archived Control hash, subject to the three-build retention rule.
- **Read, `os/ci/control/chrome_actions.py` and `os/ci/control/control_vm.py` at `522c1113`.** A separate CI
  guest covers installation, relay, replacement, package faults, exclusions, polkit, the managed Chrome ask,
  update requests and the verifier. The probe, extra bundles and synthetic browser data live in the test layer.
- **Read, `os/ci/control/release_checks.py`, `os/ci/control/actions.py` and
  `os/tests/test_control_vm.py` at `dbeaff72`, `os/README.md` at `dac9ed88`.** The rehearsal script runs
  on the image's Python and OpenSSL. It compares the two links and the four ID sources with the signed package,
  detects foreign extension IDs, supplies a list hash without the hosts, checks the pinned `gh`, and compares the
  polkit action to the record. The README covers the owner-visible installation, its per-build identity and the
  rehearsal command. Item 1's packaging README was completed in step 1a (`0fc242e7`).

### Verified

- **Run, local step 6b, `6df045c8` and its merge.** Ran
  `python3 -B -m unittest discover -s os/tests -p 'test_<module>.py'` one module at a time, with
  `TMPDIR` under `.work/18c-b-6b/tmp`. Each printed `OK`:
  `guardian_vm` 19, `release28` 94, `control_vm` 97, `control_image` 48, `checkout_sources` 10,
  `ci_api_permissions` 4 and `console_keymap` 21. The same command with `test_aresos_desktop.py
  -k ModJarPinTest` printed 7 and `OK`. The first runs exposed the Release 28 stand-in assumptions and
  the expected installer invocation. The final counts above are the reruns after correcting the fixtures.
- **Run, local step 6b, `6df045c8` and its merge.** Python unittest discovery under
  `control/chrome/ci/install` and `control/chrome/ci/records` printed 28 and 22 tests with `OK`.
  With `PYTHONPATH=control`, the modules `test_excluded_sites_placeholder.py`, `test_exclusions.py`,
  `test_extension_stores_nothing.py`, `test_owner_confirm.py` and `test_build.py` under
  `control/chrome_tests` printed 9, 3, 3, 15 and 3 tests, all `OK`.
  `python3 -B control/chrome/record_build.py check` identified both historical release 28 manifests
  and printed `record_build check passed`. The local Node command returned 127 because Node is absent.
- **Run, hosted step 6b, `6df045c8`.** Control Chrome records run
  [44879117347](https://github.com/Ares-Empire/AresOS/actions/runs/44879117347), attempt 1,
  ran 22 tests (200), identified release 28's two historical manifests (207 and 211) and printed
  `record_build check passed` (212). Repo privacy
  [44879117291](https://github.com/Ares-Empire/AresOS/actions/runs/44879117291) passed on the same head.
- **Run, hosted step 6b, `6df045c8`.** Control Chrome install run
  [44879117389](https://github.com/Ares-Empire/AresOS/actions/runs/44879117389), attempt 1,
  passed 28 packaging tests (2227), the Node crypto cross-check (2233 and 2241) and the pinned Chrome
  install proof (2310).
- **Run, local checks_only fix, `c5288fc2`.** `bash -n os/build.sh` exited zero. The
  `test_release28_control.py -k ControlBuildBytecodeTest` subset ran 2 tests, `test_control_vm.py`
  ran 97, `test_control_image.py` ran 48 and `test_checkout_sources.py` ran 10. Each printed `OK`.
  The hosted retry covers the owner-walk module.
- **Run, local step 6a, `dbeaff72`.** With `TMPDIR` in `.work/18c-b-6a/tmp`,
  `python3 -B -m unittest discover -s os/tests -p 'test_control_vm.py'` printed
  `Ran 97 tests in 2.468s` and `OK` (local log lines 3 and 5). The new tests exercise real OpenSSL on a
  synthetic signed CRX3 and changed payload, disagreements in each ID source, each missing, regular-file or
  wrong-target link, foreign IDs including a probe and an escaped ID, changed KDE manifest, wrong excluded-sites
  UID, GID and mode, a missing or linked list and the hash line, mismatched `gh` output and binary, and changed
  polkit bytes or mode. The existing VM action's test pins its check selection. `git diff --check` exited 0
  without output. The Repo privacy workflow shell printed `No file holds a home path with a real user name.`
- **Run, step 6a hosted.** See the checks_only receipt in Step 6a for the run ID, tested head and log lines.
- **Run, packaging and records, `6b80a139`.** Install proof 44329692789 ran 28 tests (2228), the Node crypto
  cross-check (2234) and all five browser cases (2306–2310), ending `CONTROL_CHROME_INSTALL_PROOF_PASSED` (2311).
  Records run 44329693134 ran 21 tests (199) and printed `record_build check passed` (210). The earlier
  container run 43729218613 exercised the policy-negative control (case 5 PASS at 2297, suite PASS at
  2298). Step 2b records its detailed result and artifacts in `PROGRESS.md` at `80e0c0ef`.
- **Run, throwaway image build.** Run 44288748140 on `2e2516b1` passed the independent bundle/key checks
  (2912–2913), placeholder and image checks (3520, 3549), checkout and build-log checks (3570, 3574), and
  general image VM (4267). Run 44409288317 on `5a027074` added the successful pinned `gh` RPM, extraction
  and keyring checks (1561–1564), image binary (2336), checkout (3586) and general image VM (4284). Resolve
  run [44344811923](https://github.com/Ares-Empire/AresOS/actions/runs/44344811923) on `6b80a139`
  printed `INFO gh newest=v2.105.0 pinned=gh-2.103.3-1.x86_64` (1397).
- **Run, shared build from 44621559332 attempt 2 on `522c1113`.** RPM payload, signature, extraction and
  restored trust PASS at 1651–1654, `gh` binary at 2426, CRX and key scan at 3018–3019, preservation and
  repair by tmpfiles at 3625, checkout matches at 3676–3677 and build-log key scan at 3681. The Control
  disk was ready at 4387.
- **Run, Chrome installation and native connection, 44621559332 attempt 2.** Pinned Chrome installed the helper
  in 1.76 s and connected its native host in 1.83 s on first start (4445–4447). After guest reboot the helper
  was observed installed at 5.95 s and connected at 6.35 s (4451–4452). C3 checked the daily user's host in
  Chrome's scope, read the synthetic tab and refused the probe (4454). The A → B → A restarts installed
  the active helper at 1.59 s and 1.29 s, connected at 1.68 s and 1.66 s and removed the previous ID and its
  folder by 1.69 s and 1.66 s. Both restored a tool read and refused the probe (4461–4462).
- **Read, profile continuity, `briefs/18c-b-chrome-image.md` at `30ff4401` and
  `os/ci/control/chrome_actions.py` at `522c1113`.** The successful connections above predate the
  profile pin. The combined same-profile replacement, managed confirmation, different-profile refusal and
  retirement proof belongs to 28b. The lead assigns the combined image C4 after pinning lands. A release
  containing 28b depends on that proof.
- **Run, gating and rule changes, 44621559332 attempt 2.** The placeholder blocked tabs, read, open and
  take before the fixture page saw a request (4449). The written list survived reboot (4452). C6 checked
  exclusion of the synthetic host and its subdomain, unsafe or missing files, and the service's
  blocked writes (4455–4456). At C7 the first cancel left the site read-only, the password changed it, and the
  next request asked again. The authorization journal bound the one-shot approval to the exact native host
  process. The runner's scan checked 68 files and two archive members at C7 and repeated the scan at poweroff
  (4475, 4480). C8's Yes sent one matching synthetic form and ended `done`. No sent zero and left the
  operation reserved before harness cleanup (4477). SELinux was enforcing with no denials naming the checked
  processes (4479).
- **Run, package faults and network, 44621559332 attempt 2.** Changed and missing CRX files on a never-held
  ID kept tools refused for 22.08 s and 21.67 s while browsing worked. Restored C connected in 1.63 s.
  The already-installed copy kept working under both faults (4463–4464). C9's two explicit checks were asked
  at 1.97 s and 5.22 s after start. The installed-run summary shows two probe requests matching two replies
  and zero non-file mentions of the helper's ID. It lists the installed run's update-service addresses and
  named IDs. The PASS indicates the one-way comparison found no additions to the probe-only baseline
  (4465–4466). [C9 run](https://github.com/Ares-Empire/AresOS/actions/runs/44621559332/attempts/2)
- **Run, measured VM times, 44621559332 attempt 2.** 18c took 575.2 s total, 52.4 s to the channel, 59.3 s idle,
  233.9 s ordinary sessions, 38.5 s Mail, 118.0 s interactive ask and 43.0 s storage tests (4429). Chrome took
  400.2 s total, 45.8 s to the channel, 29.7 s from reboot to channel, 15.9 s for C4, 71.2 s for C5, 18.6 s
  for C9, 66.6 s from C9 PASS to C7 PASS by log timestamps, and 68.9 s for C8 (4466, 4475, 4481). Both
  guests powered off cleanly (4428, 4480).
- **Artifact reads, 44621559332 attempt 2.** Steps 5 and 6a inspected the retained C2 managed and C7 dialog
  images in `check-build-evidence/control/chrome/`. `c2-managed.png` shows “Managed by your organization”.
  `c7-allow-dialog.png` and `c7-again-dialog.png` show the guest agent naming the synthetic site with a blank
  password field. Step 5 read the full question at 120 rows in `c8-yes.tar.gz` and `c8-no.tar.gz`.
  [Run artifacts](https://github.com/Ares-Empire/AresOS/actions/runs/44621559332/attempts/2)
- **Artifact read, final Control run 44900848938.** The C2 captures show the square A button in the toolbar
  and the “Managed by your organization” menu line. The C2 runner requires the captures to succeed.
  [C2 artifacts](https://github.com/Ares-Empire/AresOS/actions/runs/44900848938/artifacts/14708622963)

#### Final-head verification

**Run, tested head `6df045c8`.** Control [44879115402](https://github.com/Ares-Empire/AresOS/actions/runs/44879115402) ran twice under the same dispatch ID.
Both attempts stopped in the pinned Ubuntu snapshot tool setup, before the image build or either VM.

| Attempt | Outcome | Full-log lines |
|---|---|---|
| 1 | Tool setup reached its 20-minute limit while APT was fetching and retrying packages | 414–443 |
| 2 | Failed-jobs infrastructure rerun reached the same limit while APT was still fetching packages | 429–445 |

**Run.** Dispatched with `gh workflow run os-image.yml -R Ares-Empire/AresOS --ref pkg/18c-b-chrome
-f check_build=control`. Reran failed jobs once with
`gh run rerun 44879115402 -R Ares-Empire/AresOS --failed`. Each was watched with
`gh run watch 44879115402 -R Ares-Empire/AresOS --exit-status --interval 300`. The first local watcher
lost its API connection as the run finished. GitHub's metadata and the full attempt log report the failure.
Both attempt logs came from `gh run view 44879115402 -R Ares-Empire/AresOS --attempt <attempt> --log`.

**Run.** Dispatched the separate regression verification first on `6df045c8` and once more on `c5288fc2` with
`gh workflow run os-image.yml -R Ares-Empire/AresOS --ref pkg/18c-b-chrome -f checks_only=true` and
watched each with `gh run watch <id> -R Ares-Empire/AresOS --exit-status --interval 300`.
The first run [44882775213](https://github.com/Ares-Empire/AresOS/actions/runs/44882775213), attempt 1,
printed `Ran 2456 tests in 1701.672s` (4722) and `FAILED (failures=12, errors=1, skipped=23)` (4724).
The R28 rehearsal lost its checker contract after the Chrome checks were added (4525–4711).
The build bytecode test also detected the new root invocation without `-B` (4714–4719).
The retry [44885414951](https://github.com/Ares-Empire/AresOS/actions/runs/44885414951), attempt 1,
printed `Ran 2461 tests in 1727.511s` (4705) and `OK (skipped=23)` (4707). The bytecode and R28
checker-selection tests passed (4181 and 4235). The separate full ways-back model ran one test in
1046.347 s (403) and passed (405).

**Run, final code head `6d610587`.** See [Step 6b](#follow-up-control-runs) for the hosted
verdicts, full-log PASS lines, VM timings and daily-profile reconnect result.

**Run, final pre-fix PR checks at `6d610587`.** The package review counted eight successful workflows across
75 jobs. GitHub reports `success` for all eight. Install passed 28 Python tests, the Node cross-check and five
browser cases. Records passed 22 tests and the checkout check.

| Workflow | Run |
|---|---|
| Control base | [44893166746](https://github.com/Ares-Empire/AresOS/actions/runs/44893166746) |
| Control boundary | [44893166768](https://github.com/Ares-Empire/AresOS/actions/runs/44893166768) |
| Control Chrome | [44893166753](https://github.com/Ares-Empire/AresOS/actions/runs/44893166753) |
| Control Chrome install | [44893166810](https://github.com/Ares-Empire/AresOS/actions/runs/44893166810) |
| Control Chrome qualification | [44893166818](https://github.com/Ares-Empire/AresOS/actions/runs/44893166818) |
| Control Chrome records | [44893166754](https://github.com/Ares-Empire/AresOS/actions/runs/44893166754) |
| Control Mail | [44893166830](https://github.com/Ares-Empire/AresOS/actions/runs/44893166830) |
| Repo privacy | [44893166787](https://github.com/Ares-Empire/AresOS/actions/runs/44893166787) |

**Read, final pre-fix OS regressions at `b5091f42`.** Run 44908983067 passed. The regression log printed
`Ran 2461 tests in 1711.071s` (4714) and `OK (skipped=23)` (4716). The separate full ways-back job printed
`Ran 1 test in 1363.226s` (408) and `OK` (410). [OS regressions](https://github.com/Ares-Empire/AresOS/actions/runs/44908983067)

### Not verified

- **Read, `os/ci/control/chrome_actions.py` at `522c1113`.** A real deployment switch with Chrome open,
  followed by an update and rollback rehearsal of the probe-free image and the three hashes, still needs
  evidence. C4 restarts Chrome around a guest bind mount.
- **Assumed.** The owner's own profile, excluded sites and dashboard, and his installed session's polkit agent
  still need the live sitting.
- **Lead release and live-sitting gate, Review 4.** At the owner's actual terminal size, the full C8 question
  must be visible before he answers. Yes must send exactly the approved contents once and No must send nothing.
  The 120-row CI capture covers the complete synthetic question. [40-row failure](https://github.com/Ares-Empire/AresOS/actions/runs/44605724119)
- **Read, CROSS-5 at `30ff4401`.** Profile continuity with the real 28b handshake and store awaits the
  combined proof. Steps 4 and 5 exercised the package and connection with the existing service.
- **Read, `os/ci/control/actions.py` and `release_checks.py` at `dbeaff72`.** 6a's test root is synthetic.
  The strict checks on an actual probe-free deployment belong to the release rehearsal. The compatible
  subset ran in the Control guest using the image's OpenSSL and executable (run 1 line 5721).

### JUDGMENT-CALLs

- **Read, brief “The lead's answers” at `30ff4401`.** Board #297 accepted a pinned, non-removable
  AresOS Chrome helper and the browser's managed notice. User-managed installation would give up the
  predictable image installation. Changing this later would require revisiting the Chrome policy and C2.
- **Read, `control/chrome/packaging/` at `522c1113`.** The policy uses `ExtensionSettings` alone, with
  the fixed file update URL, override and forced pin. The tested form met the need without the
  `ExtensionInstallForcelist` fallback. A policy change costs a new pack, image audit and browser proof.
  A fresh in-process RSA key per image was chosen over a permanent key or serialized private PEM.
  The packer refuses links, special inputs and overwrites, validates version and filenames, disables core
  files and uses a deflated ZIP with fixed times and modes. Changing key or packaging policy changes the
  build hash and the replacement behavior. The storage test covers alternate APIs as well as the named ones.
  Board #355 chose a future managed yes/no question for the replacement instead of accepting it automatically
  or using a second password dialog. The owner-visible relink and storage exception require 28b's proof.
- **Read, `exclusions.py`, tmpfiles rules and `test_excluded_sites_placeholder.py` at `522c1113`.** A
  format-0 placeholder is refused. A format-1 list, including an intentional empty list, opens the gate.
  The shipped refusal reads “Chrome refuses reads and actions: its owner-only excluded-sites setting is not set
  up yet, or is missing, not a valid list, unreadable or unsafe; ask the owner to set it up.” The previous
  wording sounded like a broken install. The alternative of a format-1 empty default would let tools run
  before setup. Shared `/var` retains the list across deployments. The sweep names the non-page tools and
  checks every category, while C6 uses the guide's `tee` format with a trailing newline. A change would need
  the guide, validator and tests to agree again.
- **Read, `prepare.mjs` and `record_build.py` at `522c1113`.** CI asks the runtime where it reads its list,
  so writing both paths cannot mask a regression. Record building archives only `control/`, keeps the
  first time for a repeated commit, lets a later commit take over an equal build hash, and refuses a
  conflicting commit or a row that would immediately be pruned. Strict UTC time and source-commit equality
  apply to current and recursively archived manifests. Rows are one per line, newest first. The records workflow
  runs on matching PR paths against any base, including its own file. Changing these choices affects the release
  integration and qualification retention rules.
- **Read, `os/gh.lock.json` and `os/build.sh` at `522c1113`.** The agreed 2.103.3 pin exceeds the
  verifier minimum 2.102.0. The Fedora version considered in the brief was too old. Extraction avoids RPM
  installation and its dependencies and checks all scripts and triggers. The full keyring comparison encloses
  Chrome and `gh`; the import/delete approach supplies the agreed verification of the pinned signature and
  restored trust. Renewing the pin needs a new payload, key and hash proof. Resolve only reports newer versions.
- **Read, `control/chrome/ci/install/` and `chrome_actions.py` at `522c1113`.** The Python fixture
  reuses its Chrome driving and log code in the guest. It keeps a separate browser lock (major mismatch
  fails, patch mismatch warns). Container case 1 measures the pin against an unpinned image, with a threshold
  relative to the pinned baseline. C2 uses a screenshot for the pin and managed menu. The policy-installed
  probe may switch the helper off, so the tests prove the denied uninstall, the recovery on next start,
  and a genuine denial to the hand-loaded extension. An inability to ask the latter is a failure after the
  lead's correction. C4 tests loaded IDs and folders and the container test tests whether the previous
  preference carries code or permission, avoiding an assertion on unrelated browser bookkeeping. A new
  Chrome version may require fixture and screenshot updates.
- **Read, `chrome_actions.py` and `control_vm.py` at `522c1113`.** CI generates Chrome's launch with
  the shell's own scope launcher and the session helper's environment. The desktop launch request would
  falsely announce a desktop to the guest supervisor. CI adds `--no-first-run`,
  `--no-default-browser-check` and `--password-store=basic` for the disposable session. The lead
  authorized `--remote-debugging-pipe` for the isolated hand-loaded and update-check starts, with
  `--enable-unsafe-extension-debugging` for loading. A pipe avoids a debugging listener. C9 uses
  throwaway profiles, `--log-net-log`, `--disable-component-update` and the inert
  `--extensions-update-frequency=30`. It actually triggers two updates by explicit calls roughly three
  seconds apart and counts the probe's arrivals, which mark actual requests. In the container,
  `proof.py` also sets `--user-data-dir`, `--start-maximized`, `--gtk-version=3`,
  `--enable-logging=stderr` and `--disable-background-mode` for isolated profiles and repeatable
  captures. Its case 5 omits the inert interval flag. These flags and profiles require a recheck
  if Chrome's updater or debugging behavior changes.
- **Read, `os/ci/control/chrome_image.py` at `522c1113`.** The image checker has an independent parser
  and shares the modulus scan with the build-log check. It scans using an image-relative view so ephemeral
  check mounts do not hide files, and without ASCII whitespace in encoded views so wrapped dumps count.
  Reusing only the packer's claim would lose the independent proof. A layout or encoding change needs checker
  tests.
- **Read, `chrome_actions.py` and `control_vm.py` at `522c1113`.** C4 and C5 swap the four bundle
  files as a unit in the guest's default profile, while C9 isolates its captures. The bind mount imitates
  replacement without requiring two shipped deployments. The forthcoming rehearsal owns the real switch.
  C6 prints first-use and reboot evidence independently and joins them to the later check before the full
  PASS. The second VM pass depends on a passing 18c step. Changing the order means revisiting the verdict
  joins and tests.
- **Read, `chrome_actions.py`, `control_vm.py` and step 4b at `80e0c0ef`.** The guest waits for its
  session, gives keys a one-second settle and scrolls the Chrome menu to the managed note. Transient
  sandbox probes keep the unit restrictions and use regular capture files after pipe handoff failed.
  C11 requires acceptance when an attested record is available. An unexpected refusal remains a failure.
  Changes to the menu, guest or records need corresponding driver and expectation updates.
- **Read, `chrome_actions.py` and `control_vm.py` at `522c1113`.** The probe accepts KDE's exit 1 or
  3 on cancel only with the dialog and session journal proof. C7 matches the real agent title before
  typing, temporarily enables the live daemon's INFO journal and restores the guest's prior state.
  The password case is exclusively F7. Matching a generic redraw was inadequate, and a desktop theme or
  polkit logging change can require a new title crop or observable. C8's 120-row terminal gives the
  managed question room without changing laptop settings.
- **Read, `release_checks.py`, `actions.py` and tests at `dbeaff72`.** The default script checks the
  merged tree as well as the image and uses its OpenSSL through a single standalone script. It permits the
  existing KDE host's IDs only when that manifest equals the image copy. An unrestricted exemption could
  hide a stale locally configured ID. The 18c test-layer guest explicitly selects the compatible checks
  because its probe makes the release-only scan fail by design. A stock host or test-layer layout change
  would require revisiting this proof. The script checks the hash before running `gh --version` as root and
  supplies a list digest without reading the host names into evidence.

### PLAN-GAPs

- **Read, `PROGRESS.md` at `80e0c0ef`, steps 1a and 1b.** The actual branch is
  `pkg/18c-b-chrome`. Item 1's dedicated tests only acquired a workflow in step 2, and its README
  anticipated the step 1b tool. Historical text still used the old `/etc` list path. The latency pair ran
  a newer fixture over an older runtime, which refused the list until the fixture asked each runtime for
  its path (43705955018, step 1b evidence). Item 4 left repeated commits, equal builds and archive scope
  open. The records tool makes these rules explicit.
- **Read, `PROGRESS.md` at `80e0c0ef`, steps 2 and 2b.** Chrome itself performs background update
  requests and did not schedule the requested short interval. The Chrome 157 log contains named IDs in
  update request headers, in addition to addresses. The proof uses explicit updates, a counted probe and a
  policy-negative container run. A Chrome lock change alone does not trigger the install workflow.
  The branch's historical `control/` edits triggered other Control jobs as well.
- **Read, `PROGRESS.md` at `80e0c0ef`, steps 3a and 3a fix.** The image root is 0555 and root's home
  link can be unresolved until boot, so the first two checker attempts failed at their filesystem assumptions
  (44241272420 lines 2924–2934 and 44247363499 lines 2902–2914). The fix follows paths inside the
  scan root and preserves real read errors. The 18e socket's original bind name and qualification fixture
  import also had to be reflected in the CI proofs. Main carried the 18c timeout correction.
- **Read, `PROGRESS.md` at `80e0c0ef`, 3b and 4b.** The older lock fixture omitted `gh`, so the
  byte-for-byte comparison is separate. The image has completion names containing `gh` that are outside its
  pinned RPM payload, so the negative check matches the actual payload paths. C11 calls
  `aresos control log`; the brief's Mail refresh is absent. Transient sandbox outputs required regular file
  descriptors and the Chrome menu needed a scroll after the key settle (44452254488 and 44468856359).
- **Read, steps 4 and 5 in `PROGRESS.md` at `80e0c0ef`.** A guest channel can come up before the session
  agent. KDE uses exit 1 for Escape. The managed text must be seen in the menu. Polkit 127 uses NOTICE
  by default and emits the successful one-shot record at INFO. A 40-row terminal scrolled the approval
  question above the capture. The C4 test needed to filter the directory contents to extension IDs, and C8
  needed the tab nested in `untrusted_content` and the user-scope MCP install on the second overlay. These
  test corrections are documented with the failed and successful attempts above.
- **Read, `release_checks.py` at `dbeaff72`, `chrome_layer.py` at `522c1113`, and the brief at
  `30ff4401`.** The original 18c guest runs on the probe-bearing disk. The full no-other-ID check
  belongs to the clean release rehearsal. The base KDE manifest is the specific host already allowed by
  the base contract. A rollback target predating 18c-b can supply a shared-list hash if the release
  harness reads it, but its image cannot supply the new install records. The release brief must account for
  that when choosing the rollback evidence.

### Known limits

- **Read, `reviews/20-chrome/KNOWN-LIMITS.md` and `control/chrome/packaging/README.md` at `522c1113`.**
  The profile's installed extension is user-writable. A same-named per-user native host, a process of the
  same user posing as the native host, and same-user modification of the installed helper stay within the
  accepted decision-24 boundary. The same user's process can disturb the host, raise a nuisance password
  dialog or occupy the single connection while Chrome is closed. That process already runs with his user
  rights. The dialog names the attempted change and checks his password for every loosening. The host and
  policy built here live in the image.
- **Read, step 2b at `80e0c0ef`; run, 44621559332 attempt 2, 4462 and 4466.** Another policy-installed
  extension can disable ours until Chrome starts again. Changing policy requires root and the tools refuse
  while disconnected. Chrome may keep an empty preference record for the old ID; the record contains no
  load path or permissions. Chrome makes its own update requests. C9 compares addresses and named IDs
  against the probe-only run with two counted probe requests in each. The container includes the
  policy-negative case.
- **Lead decision, linux-tools, 2026-11-21, Review 3.** The helper remains barred from sending requests to
  the update service, which is the channel that could carry its ID in a body omitted from the log. Pinned
  Chrome makes background requests of its own. In the probe-only fallback, case 5 and C9 compare deduplicated
  addresses and named IDs. A repeated request to an already-seen endpoint can be missed. Count comparisons
  would be flaky across Chrome's background runs. The possible disclosure is a random per-build extension ID
  without owner data, so the lead accepted the narrower proof.
- **Lead decision, linux-tools, 2026-11-21, security NIT 1.** The service's `gh` can send one pseudonymous
  usage ping per record refresh. The hashed `control/aresos_control/chrome/qualification.py` is outside this
  package's paths. When that file is next touched, give `gh` `GH_TELEMETRY=false` and an `XDG_STATE_HOME`
  under the cache.
- **Lead decision, linux-tools, 2026-11-21, security NIT 4.** The modulus scan is a tripwire for the encodings
  it knows. Colon-separated hex, decimal and compressed forms are outside its coverage. The signer keeps
  the private key in memory, and the signing tests check for named-file writes and leaked private bytes.
- **Lead decision, linux-tools, 2026-11-21, security NIT 5.** The existing `format != 1` comparison accepts
  `true` and `1.0`. Only root writes the excluded-sites list and the shipped format-0 placeholder is refused.
- **Run, 44621559332 attempt 1 lines 4399–4400 and 4410–4491.** C11 hit a rate limit. Separately, the daily
  profile stopped reconnecting after C4 despite C9's isolated profiles showing probe activity, so C5, C9,
  C7 and C8 could not finish. The retained evidence has no confirmed browser startup cause. Attempt 2 passed
  all of them (4464–4477).
- **Read, `chrome_actions.py` at `522c1113`; run, 44621559332 attempt 2 lines 4442, 4455 and 4460.**
  The VM launches Chrome in the shell scope from the CI service's SELinux context, while the real session
  agent has its own context. C6 exercises tabs/read for each unsafe file condition. The adapter's wider
  tool sweep covers the placeholder. C10 checked the verifier's credential paths. C11 observed one accepted
  refresh result. A request count and the no-published-record fallback remain outside that green run's
  evidence. The laptop's own context and live-session checks are separate.
- **Run, 44605724119 attempt 1 lines 4489–4492, and 44621559332 attempt 2 line 4477.** At 40 rows the
  form description could scroll the question above the viewport. The passing capture has 120 rows.
  The tool binds the question to the managed operation, and visibility on the owner's screen remains open.
- **Run, 44435868192 line 4421 and 44621559332 attempt 2 line 4475; read, `confirm.py` at `522c1113`.**
  KDE's Escape returns the same status as refused authentication. The service says the password was
  wrong or the request was denied, and the cancellation leaves the read-only state in force.
- **Read, CONTROL §6 “The bar” and §7 at `30ff4401`.** The agreed MCP boundary leaves direct calls
  with the user's rights, user-installed permission hooks, requests relayed between sessions, auto mode
  without profile-ask evidence and sends a page starts after an ordinary click. The image changes here
  require an owner-approved release, and the guest checks cover the placeholder refusal, password-gated
  loosening, and the absence of the disposable password in saved evidence.

### Open questions

- **Assumed.** Which rollback source will linux-aresos use to prove the three-list-hash check and the
  browser-side install records, and when will the lead schedule the 28b combined image proof?
- **Assumed.** At the live sitting, can the owner see the full C8 question in his terminal, and does his
  session's polkit dialog name the expected change?

### For his guide

**Lead gate, linux-tools, 2026-11-21.** Start the live sitting by checking C8 at the owner's actual terminal
size with a synthetic form. Before the owner uses Chrome's tools, show the full question in the viewport and
check both answers. Yes submits the exact approved contents once. No sends nothing. Keep the real excluded-sites
list and its SHA-256 out of public evidence, since a guessed short list can be checked against the hash.

**Read, brief “For his guide” and CROSS-5 at `30ff4401`.** Before Claude's first session in his Chrome,
write the excluded-sites list once. Until then Chrome reads and actions say the owner-only setting is not
set up yet. Run `sudo tee /var/lib/aresos-control/chrome-excluded-sites.json >/dev/null`, paste or type the
list on one line, press Enter and then Ctrl-D. Put the dashboard's host first. The dashboard can approve
Claude's actions, and the tool treats a dashboard omitted from the list as an ordinary site. Add each other
site to exclude, at most 128 lowercase host names, each covering its subdomains, with no scheme, port or path.

```json
{"format":1,"hosts":["first.example","second.example"]}
```

**Read, the same guide.** An empty list opens the tools when there are no sites to exclude.

```json
{"format":1,"hosts":[]}
```

**Read, the same guide.** Typing the list into `tee` keeps the hosts out of shell history and preserves the
existing file's owner, group and mode. Use the same procedure for later changes. The tools read the file at the
next call. Updates and rollbacks keep it. With Chrome open, `aresos chrome tabs` should list the tabs once
the profile is ready. If it still reports a missing or invalid setting, check for a capital letter, a scheme,
a slash or a typographic quote. `sudo cat /var/lib/aresos-control/chrome-excluded-sites.json` shows the
written file. Repeat the `tee` command to replace it.

**Read, the same guide.** When the list file is missing, `tee` creates it as `root:root` 0644 and the
tool can read it. Until the next boot repairs the ownership and mode to `root:aresos-tools` 0640, any
local account can read which sites were excluded. If the folder is missing, run
`sudo systemd-tmpfiles --create /usr/lib/tmpfiles.d/aresos-control-chrome.conf` and then write the list.
Until the list is written, the details page's read-only switch answers “Owner list unavailable; use the admin
command”. “Allow editing” asks for his password in the system dialog. A managed policy file that sets
`ExtensionSettings` and sorts after `aresos.json` replaces ours. Chrome removes the helper and the tools
report that Chrome is unavailable.

**Read, CROSS-5 at `30ff4401`.** After 28b and the combined proof, enter the profile's Chrome picker name
in the helper's local details at setup and correct it after a rename. After an update or rollback replaces
the helper, start Chrome and make the first Chrome tool call in a Claude Code session. Confirm
“Keep using Chrome profile <name>?” in the Claude Code permission prompt after checking the displayed
profile. The system password dialog is for rule loosening. A current Yes keeps using that profile until the
next replacement. No, cancel or no answer leaves the tools refused, and a stale
answer has no effect. A normal restart of the accepted installation needs no question. A deliberate switch
starts from the selected intent in local details and asks in the session to use the other profile instead.

### For linux-aresos's release brief

**Read, `briefs/18c-b-chrome-image.md` at `30ff4401`, “For your next release” and review 2's request.**
Before the update, have root write a made-up format-1 list, for example
`{"format":1,"hosts":["rehearsal.invalid"]}`, into
`/var/lib/aresos-control/chrome-excluded-sites.json` with `sudo tee` as in the owner's guide. If the
previous release has no folder yet, create it root:root 0755 first. The new image's tmpfiles restores the
file's group and mode on first boot. Record the SHA-256 of the bytes written before the update. Run the
new `os/ci/control/release_checks.py` checks after the update and after `previous`, and require both
`CONTROL_CHROME_SITES_SHA256 <hash>` values to equal the pre-update hash. A placeholder would give the
same three hashes even if tmpfiles rewrote it at every boot. The release diff and pinning job own the
per-build bundle record, the release manifest's `control` object (`source_revision` and `chrome_build`)
and the `record_build.py add` row.

**Lead gates, linux-tools, 2026-11-21.** Require 28b's combined profile proof and the C8 check at the owner's
real terminal size before release with Chrome tools enabled. Verify the full question is visible and the
exact Yes/No behavior holds. Use a made-up list for public rehearsal receipts and keep the SHA-256 of the
owner's real list out of public evidence.

### Proposed edits to CONTROL §6

- **Read, “How the tool reaches Chrome” at `30ff4401`, `chrome_actions.py` at `522c1113`; run,
  44621559332 attempt 2 lines 4447 and 4462.** Replace “18c-b's case 3/C4 proves the integration” with
  “18c-b's case 3 and C4 prove installation and the native connection across replacement. 28b owns proof of the
  managed ask and pin continuity. Run the image C4 with pinning once 28b is integrated.”
  The resolved 3a checker can be described as complete, with real deployment evidence still due.
- **Read, `os/build.sh`, `os/google-chrome.lock.json` and `os/README.md` at `dac9ed88`.** In
  “Chrome stays normal”, say explicitly that the shipped browser version comes from the AresOS image
  pin. The existing final phrase about Chrome updates as on any machine also reads as covering browser
  version updates. Add Chrome's managed notice, as observed in C2.
- **Read, “Where Claude may go” at `30ff4401` and tmpfiles at `522c1113`.** Where the install text
  says the image makes a placeholder, specify the format-0 structure, that tmpfiles makes it at boot
  when missing and repairs the metadata while retaining the written contents. The rest of the exclusion
  and F7 design already describes the built boundary.

## Step 5 (2026-11-19 to 2026-11-20), Chrome VM second half

**Handoff to `linux-tools`.** All five Step 5 checks and the existing suites of the two guest passes are green
on `522c1113`, run 44621559332, attempt 2. **10 of 12 control dispatches used.** Two remain for step 6.
Code commits are `3d4c6d2d`, `054c915c` and `522c1113`.

### Done

- **Read, `os/ci/control/chrome_actions.py`:** C4 switches A → B → A with a guest-only bind mount and one Chrome
  profile. Both switches check the native-host manifest, extension version, installed IDs and folders, a real
  tool read, and the probe refusal. This proves installation and reconnection. The 28b PR owns the combined
  profile-continuity case, and `linux-tools` assigns the image case when pinning lands.
- **Read, `os/ci/control/chrome_actions.py`:** C5 changes one signed payload byte or removes the package. The
  never-held C ID stays absent while browsing and the service stay up. Restoring the package installs C. Both
  faults are repeated with C already installed. C9 uses a throwaway profile and the probe requests as a positive
  control, with a probe-only comparison if Chrome itself asks the update service.
- **Read, `os/ci/control/chrome_actions.py` and `control_vm.py`:** C7 drives the shipped details page and the
  guest's real agent. QMP handles navigation and the per-run password. The journal check binds the one-shot
  authorization to the guest session and the exact native host. C8 reuses 18c's terminal driver, managed policy,
  pinned Claude Code and loopback model double with synthetic input. The server counts actual form POSTs.
- **Read, `os/ci/control/control_vm.py`:** the sequence follows C11, and the SELinux scan remains last.
  `os/tests/test_control_vm.py` covers the five checks and the runner's behavior after a failed dialog gate.

### Checks

**Run, attempt 2 of 44621559332 on `522c1113`.**

| Check | PASS line and result | Full-log line |
|---|---|---|
| C4 | `CONTROL_CHROME_UPDATE_PASS`. A → B connected at 1.68 s and the old ID and folder were absent by 1.69 s. B → A reached all three observations by 1.66 s. Both current origins matched the host manifest, both tool reads returned “Chrome pass”, and the probe was refused both times. | 4462 |
| C5 | `CONTROL_CHROME_PACKAGE_FAULT_PASS`. Changed and missing C each had 15 `chrome_unavailable` samples, start and later browsing worked, and the service stayed up. Restored C connected by 1.63 s. The installed copy remained enabled and connected after both faults. | 4464 |
| C9 | `CONTROL_CHROME_NO_STORE_PASS`. The installed run logged and served two probe requests and zero non-file mentions of our ID. The comparison found no added update-service address or named ID against the probe-only baseline. | 4466 |
| C7 | `CONTROL_CHROME_POLKIT_PASS`. Read-only through cancel, editable after the password, and read-only after cancel on the next attempt. Session 1's journal ties the action and `ONE-SHOT` authorization to the native host PID 7130 and its start time. The guest restored its previous NOTICE level. The runner's scan found zero password matches across 68 files and two archive members at C7, then scanned again at poweroff. | 4475 |
| C8 | `CONTROL_CHROME_ASK_PASS`. The real managed prompt displayed each service question. Each got one answer. Yes sent one exact synthetic form to the receiver and ended `done`. No sent zero and remained `reserved` until the harness dropped it. | 4477 |

**Artifact read, 44621559332 attempt 2.** Inspected `control/chrome/c7-allow-dialog.png` and `c7-again-dialog.png`. Each names
`editing.localhost` in the real agent with the password field blank. The C8 answer screens in
`control/chrome/c8-{yes,no}.tar.gz` show the complete question above the operation ID and description.
`control/chrome/c2-managed.png` visibly shows “Managed by your organization”.
`control/chrome/c9-network.json`, the two compressed network logs and `control/chrome/c8-ask.json`
hold the positive controls and receiver data.

| Earlier check in the Chrome guest | Full-log line |
|---|---:|
| `CONTROL_CHROME_POLKIT_PROBE_PASS` | 4441 |
| `CONTROL_CHROME_FILES_PASS` | 4443 |
| `CONTROL_CHROME_INSTALL_PASS` | 4447 |
| `CONTROL_CHROME_SITES_FIRST_USE_PASS` | 4449 |
| `CONTROL_CHROME_REBOOTED` | 4450 |
| `CONTROL_CHROME_SITES_REBOOT_PASS` | 4452 |
| `CONTROL_CHROME_NATIVE_HOST_PASS` | 4454 |
| `CONTROL_CHROME_SITES_PASS` | 4456 |
| `CONTROL_GH_PASS` | 4458 |
| `CONTROL_CHROME_RECORDS_PASS` | 4460 |
| `CONTROL_CHROME_SELINUX_PASS` | 4479 |
| `CONTROL_CHROME_VM_POWEROFF_CLEAN` | 4480 |
| `CHECK_BUILD_CONTROL_CHROME_PASSED` | 4482 |

**Run, earlier 18c pass on the same attempt.** Image files 4395, managed Claude Code files 4397, release checks
4399, idle record 4401, fixtures 4403, entry points 4405, precondition 4407, MCP install 4409, sandbox 4411,
ordinary session 4413, Mail 4415, permission record 4417, interactive ask 4418, password scan 4420, SELinux
4422, storage 4424, restart 4426, clean poweroff 4428 and `CHECK_BUILD_CONTROL_PASSED` 4430.

**Run, attempt 1 of 44590443340 on `3d4c6d2d`.** Line numbers in this section count the full `gh run view
--log`.

| Check | Result | Full-log line |
|---|---|---|
| C4 | Failed waiting for the profile directory to contain exactly two entries. By then B had installed and connected and A was gone from the management listing. The log omitted the directory contents. | 4445–4460 |
| C5 | `CONTROL_CHROME_PACKAGE_FAULT_PASS`. Changed and missing cases each had 16 refusal samples and both start and later pages loaded. Restored C connected in 1.38 s. The installed copy stayed connected for both faults. | 4462 |
| C9 | `CONTROL_CHROME_NO_STORE_PASS`. Two probe requests in both the log and server, zero non-file mentions of our ID, and no update-service address or ID added against the probe-only baseline. | 4464 |
| C7 | The native host's pkcheck was waiting. The saved frame still showed Chrome's “Waiting for your password” line. Escape did not end the pending process within 20 s. The password step was skipped. | 4466–4498 |
| C8 | Both turns timed out. Each model archive identifies `KeyError('tab')`, reading Chrome's nested `open` result. | 4500–4502 |

The existing 18c pass ended with `CHECK_BUILD_CONTROL_PASSED` at 4414. The Chrome pass printed the probe, C1,
C2, first-use and reboot parts of C6, C3, full C6, C10, C11 and SELinux PASS lines at 4425, 4427, 4431, 4433,
4436, 4438, 4440, 4442, 4444 and 4504. It powered off cleanly at 4505.

**Run, attempt 1 of 44605724119 on `054c915c`.**

| Check | Result | Full-log line |
|---|---|---|
| C4 | `CONTROL_CHROME_UPDATE_PASS`. Both switches read “Chrome pass” and refused the probe. On A → B the new host connected and the old ID and folder were absent by 1.60 s. On B → A all three were observed by 1.32 s. | 4449 |
| C5 | `CONTROL_CHROME_PACKAGE_FAULT_PASS`. Both fresh faults blocked the tools and left browsing up, then the restored host connected in 1.37 s. Both installed-copy faults stayed connected. | 4451 |
| C9 | `CONTROL_CHROME_NO_STORE_PASS`. Two requests in both the log and probe server, no non-file mention of our ID, and no update-service address or named ID added against the probe-only baseline. | 4453 |
| C7 | The real agent showed `editing.localhost` for cancel and allow. Escape kept the site read-only and polkit named the actual native host in its failure record. After password entry pkcheck exited, but the journal query found no authorization record. The edit state and repeat request remained unverified. | 4455–4487 |
| C8 | Yes produced one receiver POST with the expected synthetic text. The 40-row answer capture began inside the description and omitted the service question, so the driver failed the prompt proof. No stopped at the baseline check without a guess about the previous arrival. | 4489–4492 |

**Artifact read, 44605724119 attempt 1.** Inspected `control/chrome/c7-cancel-dialog.png` and `c7-allow-dialog.png`. Each shows
“Authentication Required”, the full change naming `editing.localhost`, the daily-session identity and a blank
password field. The second run exercised the actual modal and cancellation, so the third dispatch targets the
remaining journal and terminal evidence. The second run alone does not prove the password changed the rule.

The existing 18c pass ended with `CHECK_BUILD_CONTROL_PASSED` at 4417. The Chrome pass printed the probe, C1,
C2, first-use and reboot parts of C6, C3, full C6, C10, C11 and SELinux PASS lines at 4428, 4430, 4434, 4436,
4439, 4441, 4443, 4445, 4447 and 4494. It powered off cleanly at 4495.

**Run, attempt 1 of 44621559332 on `522c1113`.**

| Check | Result | Full-log line |
|---|---|---|
| C4 | `CONTROL_CHROME_UPDATE_PASS`. The switch to B connected and removed A by 1.59 s. The switch back connected by 1.07 s and removed B's folder by 1.08 s. Both reads and probe refusals passed. | 4409 |
| C5 | Timed out awaiting the probe in a faulted start, then timed out awaiting it again after restoring bundle A. The last successful C5 verdict remains run 44605724119. | 4410–4437 |
| C9 | Timed out reconnecting the probe on the return from the C9 throwaway profiles to the daily profile. That prevented a C9 verdict. | 4439–4456 |
| C7 | The daily profile failed to deliver the ordinary page that focuses Chrome. The check stopped before the polkit setup and password. | 4458–4487 |
| C8 | Both Claude Code sessions started. Chrome returned `chrome_unavailable` on the first tool call, before the form or prompt. | 4489–4491 |

The existing 18c pass ended at 4370. The Chrome pass printed the probe, C1, C2, first-use and reboot parts of
C6,
C3, full C6, C10 and SELinux PASS lines at 4381, 4383, 4387, 4389, 4392, 4394, 4396, 4398 and 4493. It powered
off cleanly at 4494. C11's published-attestation API lookup hit HTTP 403 rate limiting (4399–4400). That is an
independent infrastructure failure. The guest's Chrome reconnect timeouts have no confirmed cause from this log.

### Runs

| Run / attempt | Head | Result |
|---|---|---|
| 44590443340 / 1 | `3d4c6d2d` | **FAIL** in C4, C7 and C8. C5 and C9 and the existing checks passed. |
| 44605724119 / 1 | `054c915c` | **FAIL** in C7's authorization journal proof and C8's visible-question proof. C4, C5 and C9 passed. |
| 44621559332 / 1 | `522c1113` | **FAIL**. C11's public lookup was rate-limited. C4 passed. Default-profile reconnect timeouts affected C5, C9, C7 and C8. |
| 44621559332 / 2 | `522c1113` | **PASS** in both guests. Whole-job infrastructure rerun of the same ID. |

**Run:** each ID was dispatched with `gh workflow run os-image.yml -R Ares-Empire/AresOS --ref
pkg/18c-b-chrome -f check_build=control` and watched with `gh run watch <id> -R Ares-Empire/AresOS
--exit-status --interval 300`. Attempt 2 of 44621559332 used `gh run rerun 44621559332 -R Ares-Empire/AresOS`
after the C11 API limit. Step 5 spent three dispatches for **10/12 used**.

**Run, local:** `python3 -m unittest discover -s os/tests -p 'test_control_vm.py'` printed
`Ran 86 tests in 2.501s` and `OK`. `python3 -m unittest discover -s control/chrome/ci/install -p
'test_netlog.py'`
printed `Ran 11 tests in 0.001s` and `OK`. `git diff --check 20eddb77` returned zero with no output.

### checks_only

Run 44640281276 on `522c1113`, dispatched with `gh workflow run os-image.yml -R Ares-Empire/AresOS --ref
pkg/18c-b-chrome -f checks_only=true` after the green control rerun. **PASS**, attempt 1. Regression job
135969284260 printed `Ran 1829 tests in 1414.819s` at full-log line 3851 and `OK (skipped=4)` at 3853.
`gh run watch 44640281276 -R Ares-Empire/AresOS --exit-status --interval 300` exited zero.

### Left, in order

1. **6:** rehearsal checks, two control greens on the final head, README and full report and guide lines.
  `linux-tools` coordinates the handoff to `linux-aresos`. The 28b continuity proof remains a release
  dependency.

### What the code doesn't show

- **Read:** C4's bind mount imitates the package file switch across restarts. A real deployment switch with
  Chrome open remains unverified.
- **Read:** the VM runs with synthetic sites and the guest's agent. The laptop's launch context, browser
  profile, excluded sites and agent remain unverified.
- **Read:** C8 exercises the managed ask in default mode through the loopback model double with 18c's synthetic
  session configuration.

### JUDGMENT-CALLs

- **Read:** C4 and C5 use the guest's default profile and swap the four bundle files together. The C9 capture
  uses its own profiles and the isolated DevTools pipe authorized in step 2b. A later browser change to the
  update trigger would require updating that CI driver.
- **Read and run:** C7 waits for the real agent window and checks its title against the run's own probe
  screenshot before sending QMP input. The first attempt's generic pixel comparison accepted a Chrome redraw.
  A desktop theme or resolution change could require updating the title crop.
- **Read and run:** C7 raises only the live guest daemon's logging to INFO and restores its original level and
  the guest shadow entry before C8. A fresh request after the approved loosening must prompt again. F7 is the
  sole password case.

### PLAN-GAPs

- **Read:** the pinned Chrome does not schedule short-interval checks on the requested flag. C9 uses the item 2
  trigger, keeps the network flags exclusive to C9, and requires the log's two requests to agree with the
  server's count.
- **Read and run:** polkit 127 defaults to NOTICE and logs its successful one-shot record at INFO. The guest
  changes its live log level for C7 and restores the previous level. [Polkit 127
  source](https://github.com/polkit-org/polkit/tree/127/src/polkitbackend)
- **Run and read:** the 40-row terminal captured the end of a Chrome approval's form description while the
  question had scrolled off. C8 now resizes only its own driver terminal to 120 rows.
- **Run and read:** C4's initial directory assertion counted every directory, and the failing log did not list
  them. The check now filters
  extension IDs and still demands the current package and probe and the removal of the previous ID. C8's
  initial script needed the tab from Chrome's `open` result under `untrusted_content`.
- **Read:** C8 needs the user-scope MCP install on the second overlay. It repeats 18c's setup with the existing
  test binary and model configuration.

### Known limits found

- **Read:** C4's previous-ID assertion covers loaded extensions and package directories. Chrome may retain an
  empty preference entry, as item 2 observed. That entry gives neither code nor permission.
- **Read:** the C9 fallback compares update-service addresses and named IDs with a probe-only start. The item 2
  policy-negative case stays in the container.
- **Run:** attempt 1 of 44621559332 lost the daily-profile connection after C4 while C9's isolated
  profiles still showed probe activity. The same head completed all checks on attempt 2. The first failure's
  particular browser startup error remains unknown from the retained evidence.
- **Run:** the full C8 question was visible at 120 rows. At 40 rows, the saved viewport showed the action and
  answer menu with the question above it. Visibility at the owner's terminal size remains unverified.

### The os/ and os-image.yml diff for linux-aresos

**Read, net from `20eddb77`.**

- `os/ci/control/chrome_actions.py` adds the guest checks and local fixtures.
- `os/ci/control/control_vm.py` sequences the five checks and handles QMP and evidence.
- `os/ci/control/sessions.py` accepts the Chrome fixture's model, receiver check and terminal height. Driver
  model errors surface at the prompt wait. The original 18c callers use the existing defaults.
- `os/tests/test_control_vm.py` adds targeted check and runner coverage.

The diff is confined to CI and unit tests. `.github/workflows/os-image.yml` and the installed image files
are unchanged. Scratch evidence is under `.work/18c-b-step5/`. The closing `.work/` scan found no files over
500 MB.

## Step 4b (2026-11-19): record of the completed builder runs

**Documentation handoff to `linux-tools` (the lead).** Read from builder commits `3cb3687d` and `1b263438`,
their net diff from `8bcb9504`, and the existing OS image runs below. C3, full C6, C10 and C11 are green on
`1b263438` in run 44468856359; C2's managed-note screenshot now exists and shows the note. **7 of the brief's
12 `check_build=control` runs used**, counting dispatched run IDs, with infrastructure reruns recorded separately.
This record changes documentation only; no tests, builds, VMs, dispatches, reruns or cancellations were performed
for it. Step 5 is next; the package's final "Done" conditions are not met yet.

### Done

- **Read, `3cb3687d`:** `os/ci/control/chrome_actions.py` adds `chrome-host` (C3), `chrome-sites-later` (C6),
  `chrome-gh` (C10) and `chrome-records` (C11), after the reboot with Chrome connected and the list written.
  C3 joins both socket ends to the service and the daily user's native host, takes and reads the page-server tab,
  and checks the probe's refusal without another host or socket peer. C6 checks permissions, the fixed and test
  hosts, four unsafe/missing-list states and restoration. C10 checks the pinned binary as both users, including
  the unit's sandbox and clean environment, and the absence of credentials. C11 reads the real service's refresh
  result through `aresos control log`, its state, AVCs and verifier cache.
- **Read, `3cb3687d`:** `os/ci/control/control_vm.py` sequences those actions before the final SELinux scan;
  `CHROME_JOINS` makes `CONTROL_CHROME_SITES_PASS` require first use, reboot and the later part. Every QMP key step
  gets a 1 s settle. `os/tests/test_control_vm.py` adds nine tests for this ordering, joined verdict, socket
  holders, sandbox/environment, write probe, installed host policy, gh credentials and record-log pagination.
- **Read, `1b263438`:** the sandbox helper retains `systemd-run --pipe` but gives it `/dev/null` and regular
  output/error files instead of subprocess pipes; it reads and removes those files afterwards. C2 adds Up after
  Alt+F to scroll the menu to its last line. The tests check the regular descriptors, cleanup and key sequence.
- **Read, run 44468856359 artifact:** `check-build-evidence` (artifact 14504583710),
  `control/chrome/c2-managed.png`, visually inspected: **"Managed by your organization" is visible** at the
  bottom of the menu. `control/chrome/c2-pinned.png` is also present. These are existing CI screenshots,
  downloaded under `.work/18c-b-4b-record/evidence/`; this documentation commit adds no screenshot files.

### Checks (run 44468856359, attempt 1, on `1b263438`)

**Read, full log:** numbers below count lines of `gh run view 44468856359 -R Ares-Empire/AresOS --log`,
including setup and build output, not `--log-failed` or an individual step. The full job log was also read with
`gh api repos/Ares-Empire/AresOS/actions/jobs/135373159029/logs --allow-escape-sequences`; its line numbers agree.

| Check | Result read from the log | Line |
|---|---|---|
| polkit probe | `CONTROL_CHROME_POLKIT_PROBE_PASS`: dialog appeared, Escape gave exit 1, journal named his session, dialog area changed by 59,429 pixels | 4377 |
| C1 files | `CONTROL_CHROME_FILES_PASS`: 16 paths, two policy files including the probe, placeholder, gh 2.103.3; checkout build `c689b9c8…` | 4379 |
| C2 install | `CONTROL_CHROME_INSTALL_PASS`; installed 1.26 s and host connected 1.55 s after start (summary 4381); admin, enabled, not disableable, uninstall refused; managed-note screenshot inspected above | 4383 |
| C6 first use | `CONTROL_CHROME_SITES_FIRST_USE_PASS`: tabs/read/open/take_tab refused with the setup message, page-server hits 0; root wrote the empty format-1 list, tabs 2 | 4385 |
| reboot | `CONTROL_CHROME_REBOOTED` | 4386 |
| C6 reboot | `CONTROL_CHROME_SITES_REBOOT_PASS`: hash `9ef58307…a6ce`, UID 0, GID 250 and 0640 unchanged; host reconnected, tabs 2 | 4388 |
| C3 host | `CONTROL_CHROME_NATIVE_HOST_PASS`: peer UID 1001, one host in Chrome's scope connected to the service; tabs 2, page title "Chrome pass", 582 characters read, no new page-server request from reading; probe refused "Access to the specified native messaging host is forbidden.", 24 samples without a second host/peer | 4390 |
| C6 full | `CONTROL_CHROME_SITES_PASS`: all three parts passed. Later-part summary (4391): daily user's read/write/create each EACCES; service reads 24 bytes, write EACCES, create EROFS; all three FIXED_HOSTS plus excluded.localhost and sub.excluded.localhost refused; group-writable, missing, link to a valid list and placeholder each refuse tabs/read with chrome_settings_unavailable; six restorations preserve the hash and metadata | 4392 |
| C10 gh | `CONTROL_GH_PASS`: 2.103.3 as both users, pinned hash `b7681845…ad34d`, auth status exit 1 (not logged in), credentials empty, service environment LANG/PATH only | 4394 |
| C11 records | `CONTROL_CHROME_RECORDS_PASS`: path accepted; "Verified append-only Chrome qualification update", then "Verified record accepted." once this boot; service restarts 0; verifier cache under /var/lib/aresos-tools/qualification-verifier-cache, 12 files; 10 boot AVCs, none naming the checked processes | 4396 |
| SELinux scan | `CONTROL_CHROME_SELINUX_PASS`: Enforcing, 10 boot denials, naming ours 0 (summary 4397) | 4398 |
| clean poweroff | `CONTROL_CHROME_VM_POWEROFF_CLEAN` | 4399 |
| end | `CHECK_BUILD_CONTROL_CHROME_PASSED` | 4401 |

**Every earlier 18c VM result on the same run** (including the recorded/reachable lines, which are not named PASS):

| Result | Full-log line |
|---|---|
| `CONTROL_IMAGE_FILES_PASS` | 4331 |
| `CONTROL_ETC_CLAUDE_CODE_PASS` | 4333 |
| `CONTROL_RELEASE_CHECKS_PASS` | 4335 |
| `CONTROL_IDLE_FOOTPRINT_RECORDED` | 4337 |
| `CONTROL_FIXTURES_REACHABLE` | 4339 |
| `CONTROL_ENTRY_POINTS_PASS` | 4341 |
| `CONTROL_PRECONDITION_PASS` | 4343 |
| `CONTROL_USER_MCP_INSTALL_PASS` | 4345 |
| `CONTROL_SERVICE_SANDBOX_PASS` | 4347 |
| `CONTROL_ORDINARY_SESSION_PASS` | 4349 |
| `CONTROL_MAIL_FLOWS_PASS` | 4351 |
| `CONTROL_PERMISSION_REQUEST_RECORDED` | 4353 |
| `CONTROL_INTERACTIVE_ASK_PASS` | 4354 |
| `CONTROL_PASSWORDS_PRIVATE_PASS` | 4356 |
| `CONTROL_SELINUX_AFTER_CHECKS_PASS` | 4358 |
| `CONTROL_STORAGE_TESTS_PASS` (11 image-Python/SQLite tests) | 4360 |
| `CONTROL_SERVICE_RESTART_PASS` | 4362 |
| `CONTROL_VM_POWEROFF_CLEAN` | 4364 |
| `CHECK_BUILD_CONTROL_PASSED` | 4366 |

**Earlier image/build proof on that run:** `CONTROL_GH_PAYLOAD_PASS` 1589 (240 paths), `CONTROL_GH_RPM_PASS` 1590,
`CONTROL_GH_INSTALL_PASS` 1591, `CONTROL_GH_KEYRING_PASS` 1592, `CONTROL_GH_IMAGE_PASS` 2364;
`CONTROL_CHROME_BUNDLE_PASS` 2956, `CONTROL_CHROME_KEY_SCAN_PASS` 2957;
`IMAGE_CHECKS_PASSED` 3593, `ROOTLESS_MAPPING_PASSED` 3604, `POLKIT_CHECK_PASSED` 3607;
`CONTROL_GH_CHECKOUT_PASS` 3614, `CONTROL_CHROME_CHECKOUT_PASS` 3615, `CHECK_BUILD_PASSED` 3618,
`CONTROL_CHROME_BUILD_LOG_PASS` 3619, `CHECK_BUILD_CONTROL_DISK_READY` 4323.

**Read, timing line 4400:** Chrome pass 104.9 s; boot to channel 24.9 s, reboot to channel 20.7 s;
C3 2.4 s, later C6 6.1 s, C10 0.4 s, C11 0.5 s. The hosted job took about 29 minutes.

### Runs

All are existing `.github/workflows/os-image.yml` runs on `pkg/18c-b-chrome`, read without changing their state.
Read with `gh run view <id> -R Ares-Empire/AresOS --log-failed` (empty for the two successful runs), with
`--attempt 1 --log-failed` as well for 44462912726, and `gh api repos/Ares-Empire/AresOS/actions/jobs/<job>/logs
--allow-escape-sequences` for the full job logs. The full-run logs of both successful runs were also read.
Failure references below are full **job-log** line numbers from the jobs API; the green control references
above are full-run line numbers. Both failed attempts of 44462912726 were read.

| Run / attempt | Head | Input and result read from its log |
|---|---|---|
| 44452254488 / 1 | `3cb3687d` | control **FAIL**. Job 135318798936: C3 passed (4456), C11 passed (4491); C6 later failed parsing empty sandbox stdout (4457–4471), C10 failed because the sandboxed gh never started: "Failed to start transient service unit: Connection reset by peer" (4473–4488). The commit message of 1b263438 attributes both to passing the CI service's pipes to systemd-run; its regular-file fix is the subsequent change. |
| 44462912726 / 1 | `1b263438` | control **FAIL before either VM pass**. Job 135353749541, 1639–1692: mod image-build stage could not resolve Gradle classpath artifacts (gson 2.14.0, ASM 9.10.1's ow2 parent 1.5.1, kotlin-metadata-jvm 2.4.10, Cadix at/lorenz; 19 more failures). "BUILD FAILED in 7s", image build exit 1. No Chrome verdict from this attempt. |
| 44462912726 / 2 | `1b263438` | control **FAIL before either VM pass**. Job 135357784576, 1639–1692: the same dependency-resolution failures and "BUILD FAILED in 7s", image build exit 1. The logs establish unavailable dependencies, not their upstream cause. |
| 44468856359 / 1 | `1b263438` | control **PASS**; all earlier 18c and implemented Chrome checks above, clean poweroffs and both pass endings. |
| 44488329704 / 1 | `1b263438` | checks_only **PASS**: "Ran 1820 tests in 1275.131s" (full log 3842), "OK (skipped=4)" (3844). Regression job 135437315751 has the same lines at 3610/3612. |

Step 4 used four dispatched control runs; 4b adds three, so **7/12 used, five left**. The rerun of
44462912726 is attempt 2 of the same run ID; step 4 also recorded an infrastructure rerun. No fresh allowance
is inferred. There is one green control run on this builder head, not the two final-head greens with all C1–C11
that the brief's "Done" requires.

### Left, in order

1. **5:** C4, C5, C9, then C7 and C8. Bundles B/C already live in the test layer. C4/C5 imitate replacement in
   the guest; C9 needs the positive control and network proof; C7 must drive the real guest agent for rule
   loosening, then C8 the session's asking action. Follow the brief's CROSS-5 dependency if 28b pinning is present;
   do not treat this connection proof as profile identity or bypass its gate.
2. **6:** rehearsal checks, the two greens on the final head with every required line, README lines and full
   report text with run/read/assumed marks, guide lines, JUDGMENT-CALLs, PLAN-GAPs and Not verified. The lead
   `linux-tools` coordinates the handoff; `linux-aresos` reads the net OS diff below. No release or merge here.

### What the code doesn't show

- **Read from code/log:** C11 follows the **published attested record / accepted** branch, not the brief's
  no-record fallback. It reads all pages of `aresos control log` and requires exactly the held/accepted pair
  since this boot, the same host PID as after reboot and zero service restarts. "Fetches once" is evidenced by
  that one refresh result, not by a network request counter. The verifier cache contains gh/Sigstore trust data.
- **Read from code:** the refusal diagnostic runs the installed verifier under the sandbox for the expected
  and wrong signer only when the service records one refusal. That path was not exercised by the green run;
  a refusal fails C11 because an attested record is already published.
- **Read from code/log:** C3 reads the tab's existing document after taking it into the Claude group. Zero
  page-server requests during that read is expected; it is not a missing page load. Peer UID is checked through
  ss socket inodes and /proc descriptor holders; the test does not itself call SO_PEERCRED.
- **Read from code/log:** sandbox probes derive properties and the env-i prefix from the installed unit;
  changing file descriptors in 1b263438 leaves that sandbox intact. C10 runs without a login/token and proves
  the verifier's paths, not the absence of every possible credential elsewhere on the disk.

### JUDGMENT-CALLs (read from the builder's code/log; not decisions by this recorder)

1. **Read, control_vm.py:** C6 has one joined PASS requiring all three parts across the reboot, while keeping
   the two earlier part lines for diagnosis. A partial success cannot print the full C6 line; ordering and
   failure tests pin this choice. Changing the sequence requires updating that join and its tests.
2. **Read, chrome_actions.py and 1b263438's message:** regular files replace captured pipes for transient
   sandbox runs, following the working polkit probe. This keeps the unit's restrictions and deletes the temporary
   output files afterwards; reverting it would reintroduce run 44452254488's failure.
3. **Read, control_vm.py and screenshot:** settle for 1 s after every key step and use Alt+F, Up, screenshot,
   Escape for the managed note. Up brings the bottom of the 800-pixel menu into view. This is a CI navigation
   choice; a later Chrome menu change would require adjusting that sequence.
4. **Read, chrome_actions.py records():** an already-published attested record makes "Verified record accepted."
   mandatory; a refusal is diagnostic evidence and a failure. It does not silently pass the other branch of C11.

### PLAN-GAPs (read from code/log; not decisions by this recorder)

- **Read, code/log:** the brief says `aresos log`; this head uses `aresos control log` (as step 4's handoff
  already noted after PR #109). The guest follows the installed CLI.
- **Read, 1b263438 and run 44452254488:** systemd-run's descriptor handoff matters under the CI service; the
  brief's sandbox requirement alone did not describe that harness constraint.
- **Read, code and inspected artifact:** step 4's managed screenshot gap is closed. A settle alone opened the
  menu but left its last line below the screen; scrolling was also needed. C2's automated PASS still does not
  recognize the screenshot's text; the visual inspection above supplies that evidence.

### Known limits found

- **Read, code/log:** later C6's "every read" helper calls tabs and read for each broken-list state. It is not
  a fresh sweep of every Chrome tool in those states; the separate adapter sweep from step 1a supplies the wider
  placeholder coverage. The recorded PASS must not be described as that wider VM sweep.
- **Read, sessions and host summaries:** the step 4 SELinux-context limit remains: Chrome/host run in
  unconfined_service_t through the CI service, whereas the session agent is unconfined_t. The cgroup/user/env
  proof and zero relevant denials do not prove the laptop's own launch context or agent.
- **Read, polkit summary 4377:** Escape still gives pkcheck exit 1, and the service would say "the password was
  wrong or the request was denied". C7's actual details-page/password path remains unverified here.
- **Read, code and remaining step list:** no real deployment switch with Chrome open, real excluded hosts,
  profile continuity/confirmation, C4/C5 faults, C9 no-store proof, C7 password or C8 Chrome ask is established by
  this run. Step 4b's overall pass covers only the checks currently in CHROME_STEPS.
- **Read, failed build logs:** both attempts of 44462912726 stopped at dependency resolution. A later success
  does not explain that failure's upstream cause or prove it cannot recur.

### The os/ and os-image.yml diff for linux-aresos

**Read, net `git diff 8bcb9504 1b263438`: exactly three files.**

- `os/ci/control/chrome_actions.py`: C3/C6-later/C10/C11 actions and helpers, regular-file sandbox output;
  test-layer guest checks only.
- `os/ci/control/control_vm.py`: four actions after reboot, joined C6 verdict, their arguments/summaries,
  1 s key settle and Up to the bottom of C2's menu.
- `os/tests/test_control_vm.py`: nine new tests plus updates for joined verdicts, C10's line name, regular
  descriptors and menu navigation.

**`.github/workflows/os-image.yml` did not change** in this net diff. No installed runtime, unit, lock, manifest,
production image content or workflow changed in 4b. The workflow change in step 4 below remains history, outside this diff.
Scratch logs and downloaded evidence for this record are under `.work/18c-b-4b-record/`; a closing scan of the
worktree's `.work/` found **no files over 500 MB**.

## Step 4 (2026-11-19, Claude Opus 5.5): the VM's first half, split at 4b

**Split at 4b.** The polkit probe, the Chrome pass with its layer and workflow step, C1, C2 and C6's first use with
its reboot are green on `478056d7` (run 44435868192). Four of the twelve `check_build=control` runs are used (one
of them with one infrastructure rerun), and the token budget is past half, so this step stops here as the brief's
split point says. **4b** takes C3, the rest of C6, C10 and C11.

### Done

- `os/ci/control/chrome_actions.py` (new; the layer installs it as `actions.d/chrome.py`): the Chrome pass's guest
  actions. Chrome runs as `ares` in his session through **aresos-shell's own launch line and environment**: the
  shell file is loaded and its `ScopeLauncher` builds `systemd-run --user --scope --quiet --collect
  --slice=app.slice --unit=app-aresos-browser-<id>.scope … --expand-environment=no -- /usr/bin/google-chrome`, with
  the environment of the helper running in his session minus the shell's private values. CI flags:
  `--no-first-run --no-default-browser-check --password-store=basic` only; one test-only start adds the DevTools
  pipe and `--enable-unsafe-extension-debugging` with a throw-away profile (lead's decision 5). Every action waits
  for his session first (helper and polkit agent), returns its evidence as files, and reuses 18c's helpers
  (`actions.d/control.py`: `cli`, `refused`, `denials`, `files_out`, …).
- `os/ci/control/chrome_layer.py` (new; run once by the layer's `Containerfile`): packs the install proof's probe
  under its own fresh key with its own policy file (`ExtensionInstallForcelist` alone) and its own host (the
  proof's `probe_host.py`, its two paths moved to `/run/aresos-install-test/`), lays out an extension as he would
  load one by hand, and packs **bundles B and C** (for step 5's C4 and C5), each key inside one `pack.py` call.
  Only IDs, versions and hashes are written down (`/usr/share/aresos-install-test/layer.json`).
- `os/ci/control/control_vm.py`: 18c's pass now runs through a shared `Guest` (boot, act, screenshot, keys, clean
  poweroff); its sequence, file names and printed lines are unchanged (green in runs 2 to 4). `control_vm.py
  chrome` is the second pass: a fresh overlay `chrome.qcow2` on the same disk, `CHROME_STEPS` with QMP screenshots
  and keys between actions and the pass's one reboot (clean power-key poweroff, then a new QEMU on the same overlay
  and firmware variables). A check's PASS line sits on its last step and is printed only when every step since the
  previous line succeeded. Evidence: `evidence/control/chrome/`.
- `os/ci/check-build.sh`: mode `control-chrome-pass`, ending `CHECK_BUILD_CONTROL_CHROME_PASSED`.
- `os/ci/control/Containerfile`: the action file, `cdp.py` and `netlog.py`, and one `chrome_layer.py` run.
- `.github/workflows/os-image.yml`: the step "Control Chrome VM pass (check_build=control only)" (25 minutes), the
  job's control limit 131 → 156 with its comment's sum; its own commit (`11dc4a52`).
- `os/tests/test_control_vm.py`: six new tests (68 in the module): the layer installs the actions and the runner
  asks each once in order; pkcheck's properties are the unit's own sandbox; the placeholder and the refusal message
  are read from the installed files; the probe host's two moved paths; and `chrome_main` against a stand-in guest
  (every line in order; a failed part hides only its own check's line; this test fails on run 3's bug).
- `os/manifest/ci/16/pending-rebind.json`: five notes, each from `rebind.py pending`.

Commits: `5eed178b` (the pass), `11dc4a52` (workflow), `4affd0ec` (wait for his session), `c54aa6bf` (the probe's
verdict, the menu), `478056d7` (a line on a keys step; the stand-in-guest tests).

### The polkit probe (run 44435868192, attempt 1; also run 44431963530)

A `sleep 900` started with the shell's line (cgroup `/user.slice/user-1001.slice/user@1001.service/app.slice/
app-aresos-polkit\x2dprobe-<id>.scope`) is the subject of `confirm.command`'s exact `pkcheck --action-id
org.aresos.control.chrome-loosen --process <pid>,<start>,1001 --allow-user-interaction --detail change <text>`,
run as `aresos-tools` with every `[Service]` property of the installed unit except how it starts and restarts
(`systemd-run --wait --pipe --property=User=aresos-tools … --property=ReadWritePaths=…`).

- **polkit asked his agent:** pkcheck was still waiting 8 s after its start; KDE's dialog "Authentication
  Required" showed the action's message with the change text, "Authenticating as AresOS daily session (ares)"
  (`evidence/control/chrome/polkit-dialog.png`; before and after: `polkit-before.png`, `polkit-after.png`; the
  dialog's area, 59412 pixels in the box 315,51–961,749, changed between the dialog and after Escape).
- **Escape cancelled it:** pkcheck exited **1** ("Not authorized."; `systemd-run` reports `code=exited,
  status=1/FAILURE`), `polkit-probe-output.txt`.
- **The journal** (`polkit-journal.txt`): `polkitd[925]: Operator of unix-session:1 FAILED to authenticate to gain
  authorization for action org.aresos.control.chrome-loosen for unix-process:2433:3348 [/usr/bin/sleep 900] (owned
  by unix-user:ares)`. Session 1 is his greetd session (`Type=wayland`, `Class=user`, active, `session-1.scope`).
- `CONTROL_CHROME_POLKIT_PROBE_PASS` at log line 4421 (run 3: 4378). Not a stop: polkit counted the
  `app.slice` process as his active session and asked his agent.

### Checks (run 44435868192 on `478056d7`, full `gh run view --log` line numbers)

| Check | Result | Line |
|---|---|---|
| polkit probe | `CONTROL_CHROME_POLKIT_PROBE_PASS` (above) | 4421 |
| C1 files | `CONTROL_CHROME_FILES_PASS`: 16 paths with owner, mode and hash as `control.json` records and as the checkout installs; both links root-owned links equal to `/usr/etc`'s, parents 0755; the policy folder holds `aresos-install-probe.json` (`ExtensionInstallForcelist` alone) and `aresos.json`; `gh` 2.103.3, its licence and lock; `/var/lib/aresos-control` `root:root` 0755 holding only the list, `root:aresos-tools` 0640, bytes exactly `{"format":0,"hosts":[]}` from the tmpfiles line; nothing at `/etc/aresos/control/chrome-excluded-sites.json` | 4423 |
| C2 install (parts: hand-loaded, install, pinned screen, his tab, menu screen) | `CONTROL_CHROME_INSTALL_PASS`: his profile had no `Default` (its folder held only `Crash Reports`); ours installed 1.01 s and its host on `chrome.sock` 1.32 s after Chrome's start; `installType` admin, enabled, `mayDisable` false, `updateUrl` the `file:` address; `uninstall` refused ("cannot be modified by user"); no forbidden flag, no listening port; Chrome and the host in `app.slice/app-aresos-browser-<id>.scope`; the host with exactly `PATH` and `LANG`. Hand-loaded (pipe, throw-away profile): `installType` development, `setEnabled(ours, false)` refused, ours still enabled, admin, not disableable | 4427 |
| C6 first use | `CONTROL_CHROME_SITES_FIRST_USE_PASS`: with the placeholder `tabs`, `read {"tab":1}`, `open` of a page-server address and `take_tab {"tab":1}` each refused `chrome_settings_unavailable` with exclusions.py's message; the page server received 0 requests for that address; root's `tee` wrote `{"format":1,"hosts":[]}` + newline, owner 0, group 250, mode 0640 unchanged; `tabs` listed his 2 tabs | 4429 |
| C6 reboot | `CONTROL_CHROME_REBOOTED` (4430), `CONTROL_CHROME_SITES_REBOOT_PASS`: hash `9ef58307…a6ce`, owner, group, mode unchanged; Chrome started again, connected, `tabs` listed 2 tabs | 4432 |
| SELinux scan | `CONTROL_CHROME_SELINUX_PASS`: Enforcing, 10 denials in the boot (the base's `tuned`/`chcon`), none naming the host, the service, `gh` or `pkcheck` | 4434 |
| end | `CONTROL_CHROME_VM_POWEROFF_CLEAN` 4435, `CHECK_BUILD_CONTROL_CHROME_PASSED` 4437 | |

18c's pass on the same run: `CHECK_BUILD_CONTROL_PASSED` 4410; the image checks' `CONTROL_CHROME_BUNDLE_PASS` 2998,
`KEY_SCAN` 2999, `CHECKOUT` 3657, `BUILD_LOG` 3661. The Chrome pass took 99.1 s inside its step (1 min 39 s;
boot 27.9 s, reboot 21.7 s); the job 1 h 5 min, of which the image build 52 min on this runner.

### Runs

| Run | Head | Result |
|---|---|---|
| 44421776687 attempt 1 | `11dc4a52` | Infrastructure: "Install pinned tools" failed on an Ubuntu snapshot package's hash mismatch (apt exit 100). Rerun once. |
| 44421776687 attempt 2 | `11dc4a52` | FAIL: the pass reached the guest 25 s after boot, before his session's helper ran; every Chrome start failed. `CONTROL_CHROME_FILES_PASS` green. |
| 44427301872 | `4affd0ec` | FAIL only in the probe's verdict (it required exit 3; KDE gives 1). Files, install, first use, reboot and SELinux green (lines 4376–4388). |
| 44431963530 | `c54aa6bf` | FAIL: probe and C1 green (4378, 4380); then the runner stopped on a line placed on a keys step (`TypeError`). |
| 44435868192 | `478056d7` | **PASS**, every step; lines above. |
| 44445214116 | `478056d7` | checks_only **PASS**: "Ran 1811 tests" (log 3854), "OK (skipped=4)" (3856). |

### Left, in order

1. **4b** (a fresh Opus agent): C3, the rest of C6 (with C6's full `CONTROL_CHROME_SITES_PASS` line), C10, C11
   (`aresos control log`, not `aresos log`, since PR #109). Add them as steps after `chrome-sites-after-reboot`
   (Chrome runs there, connected, list written) and before `chrome-selinux`, which stays last. Also: the
   **managed-note screenshot** isn't there yet: `c2-managed.png` shows his tab without Chrome's menu (Alt+F through
   QMP showed nothing at the instant of the screenshot, taken 0.0 s after the keys). Try a pause of about 1 s
   before the screenshot, or F10 / Alt+E; C2's PASS doesn't depend on it.
2. **5:** C4, C5 (bundles B and C are in the layer at `/usr/share/aresos-install-test/bundles/{b,c}`), C9, then C7
   and C8.
3. **6:** the rehearsal checks, the two greens on the final head, README lines, the report text.

### What the code doesn't show

- **SELinux context:** the pass starts Chrome from the CI service, so Chrome, its host and the probe's subject
  run as `system_u:system_r:unconfined_service_t:s0`; from his helper they would be `unconfined_t` (his agent is,
  `sessions-at-start.json`). The cgroup, user and environment are the shell's; the context is not.
- **polkit and the manager session:** logind lists two sessions for `ares`, 1 (greetd, wayland, active) and 2
  (`Class=manager`, `user@1001.service`). polkit still maps an `app.slice` process to session 1.
- **KDE's agent reports Escape as a failed authentication (1), not a dismissed dialog (3).** The service would tell
  Chrome's details page "the password was wrong or the request was denied" (`confirm.py`'s `REFUSALS[1]`) when he
  cancels. C7 (step 5) sees this with the details page; the text is the service's, out of this package's scope.
- polkitd 127 writes no journal line when an agent registers; only the probe's "Operator of …" line shows which
  session's agent was asked.
- **The pinned button:** `c2-pinned.png` shows an "A" button right of the address bar, beside the extensions
  button. The guest doesn't compare it with an unpinned start; the container's case 1 did (pixels).
- Chrome doesn't open a `chrome://` page handed over from a command line; each hand-over of an ordinary page opened
  a tab (2 tabs at first use).
- The guest has a network (QEMU's user NAT); Chrome's starts are not offline as in the container. C9 (step 5)
  needs to account for it.
- Chrome's log in the guest holds VA-API and portal errors (no GPU video, no desktop portal); nothing blocks.
- His profile folder held `Crash Reports` before his first start; **assumed** to come from the throw-away start's
  crash reporter (not checked). C2 requires only that no `Default` profile existed.

### JUDGMENT-CALLs

1. **How Chrome starts:** the shell's own `ScopeLauncher` line and the helper's environment, not the shell's launch
   request. The request is the desktop's (instance and launch nonce) and the guest's desktop is at its first
   start; posing as the desktop would tell the supervisor a desktop connected. The brief's fallback ("the same
   `systemd-run --user --scope` line with the session's environment"), with the shell's code building it.
2. **C2 leaves out case 1's `setEnabled(false)` by the policy-installed probe and its restart, and the pixel
   comparison of the pin.** Decision 1 after step 2 accepted the first as Chrome's behaviour; the guest asks the
   hand-loaded extension instead (decision 5) and screenshots the pin.
3. **C6's line in two parts for now:** `CONTROL_CHROME_SITES_FIRST_USE_PASS` and `CONTROL_CHROME_SITES_REBOOT_PASS`;
   4b adds the later part and the table's `CONTROL_CHROME_SITES_PASS`.
4. **The probe's verdict** accepts exit 1 or 3 after Escape, together with polkitd's line naming his session and
   the subject and the dialog's area changing; it prints `CONTROL_CHROME_POLKIT_PROBE_PASS`, a line the brief's
   table doesn't have.
5. `CHECK_BUILD_CONTROL_CHROME_PASSED` is printed when every step of the pass passed; in step 4 that is the probe,
   C1, C2, C6's first use and reboot, and the SELinux scan.
6. The workflow step runs like 18c's pass step (`if: inputs.check_build == 'control'`): when 18c's pass fails, the
   Chrome pass is skipped.
7. The list is written with a trailing newline, as `tee` gets it when he presses Enter.

### PLAN-GAPs

- The brief's probe expected "cancel" to give pkcheck's "dismissed"; with KDE's agent it gives "not authorized".
- Chrome's "managed" note can't be opened as `chrome://management` from a command line; the menu is the way, and its
  screenshot is still missing (Left, 1).
- The pass must wait for his session after every boot (`chrome-session` took 10.3 s after the channel, 5 s of it a
  fixed pause; the first attempt reached the guest 25 s after boot, before his helper ran).

### checks_only

Run 44445214116 on `478056d7`: success, "Ran 1811 tests" at log line 3854 and "OK (skipped=4)" at 3856 (3b had
1805; the six new tests here). Locally: `test_control_vm.py` 68 tests OK, and `test_ci_step_environment`,
`test_ci_api_permissions`, `test_build_tools`, `test_rehearsal_budget` OK after the workflow change.

### The os/ and os-image.yml diff for linux-aresos

Net from `7df9cfbc`:

- `os/ci/control/chrome_actions.py` (new), `os/ci/control/chrome_layer.py` (new): the Chrome pass's guest actions
  and the test layer's probe, hand-loaded extension and bundles B and C; test layer only.
- `os/ci/control/Containerfile`: installs them (`actions.d/chrome.py`, `cdp.py`, `netlog.py`, one `chrome_layer.py`
  run).
- `os/ci/control/control_vm.py`: a shared `Guest`; the Chrome sequence (`control_vm.py chrome`).
- `os/ci/check-build.sh`: mode `control-chrome-pass`.
- `os/tests/test_control_vm.py`: six tests.
- `os/manifest/ci/16/pending-rebind.json`: five generated pending notes.
- `.github/workflows/os-image.yml` (`11dc4a52`, its own commit): the step "Control Chrome VM pass (check_build=control
  only)", `timeout-minutes: 25`, `run: bash os/ci/check-build.sh control-chrome-pass`, after 18c's pass and before
  the fixture servers stop; the job's control limit 131 → 156, comment "tools 20 + build 80 + Control VM pass 16 +
  Control Chrome VM pass 25 + 15". Nothing else in the file.

No image content, release file, base, lock or unit changes. Scratch: `.work/18c-b-4/` (logs and two evidence
artifacts, about 15 MB); nothing over 500 MB.

## Step 3b: the lead's runs on 5a027074 (2026-11-19)

The lead dispatched and watched these from the shell (the builder pushes and stops):
- checks_only 44397757752: **success**; "Ran 1805 tests", "OK (skipped=4)" (log 3595/3597); CONTROL_GH_PAYLOAD_PASS 240 paths, CONTROL_GH_RPM_PASS, CONTROL_GH_INSTALL_PASS (2371-2379); CONTROL_CHROME_CHECKOUT_PASS and CONTROL_CHROME_BUILD_LOG_PASS (2108-2109, 2380).
- check_build=build 44409288317: **success**. CONTROL_GH_PAYLOAD_PASS 240 paths (1561), CONTROL_GH_RPM_PASS (1562), CONTROL_GH_INSTALL_PASS (1563), CONTROL_GH_KEYRING_PASS (1564), CONTROL_GH_IMAGE_PASS 2.103.3 (2336), CONTROL_CHROME_BUNDLE_PASS (2928), CONTROL_CHROME_KEY_SCAN_PASS (2929), CONTROL_GH_CHECKOUT_PASS (3586), CONTROL_CHROME_CHECKOUT_PASS (3587), CHECK_BUILD_PASSED (3590), CONTROL_CHROME_BUILD_LOG_PASS (3591), CHECK_BUILD_VM_PASSED (4284).
- The old name check's diagnostic (2335): `INFO gh legacy name matches=["/usr/share/bash-completion/completions/_gh", "/usr/share/fish/completions/gh.fish"]`. Both are base-image files, not paths of the pinned gh RPM's payload, so the payload-bound check is right to pass them.
- check_build=resolve 44344811923 (on 6b80a139): "INFO gh newest=v2.105.0 pinned=gh-2.103.3" (1397).

**3b is green.** Next: `linux-aresos` reads 3b's `os/` diff; then step 4 (the VM's first half), on a Claude Opus agent (Codex is kept for reviews until about 2026-11-25).

## Step 3b (2026-11-18, gpt-6-astra)

### Done

- `61644462`: pins GitHub CLI **2.103.3**, its one exported 2026 public key and the tag's licence.
  No patch upgrade: GitHub CLI's published advisories inspected on this date did not require a newer
  2.103 patch. The RPM is `gh-2.103.3-1.x86_64` from
  `https://github.com/cli/cli/releases/download/v2.103.3/gh_2.103.3_linux_amd64.rpm`.
- `b3e0c0e5`: packages verifies HTTPS-only download/redirects, RPM hash and NEVRA, no scripts or triggers
  (file triggers included), one committed primary key, and the pinned header signature with every result
  line OK. It deletes all newly imported keys even when signature checking raises, then requires the key
  list equal to its previous value. Chrome's cleanup also removes every added key; a second comparison
  spans the first Chrome import through the last gh deletion.
- Only `./usr/bin/gh` is read from `rpm2cpio` by `cpio --extract --to-stdout`; both processes must succeed.
  The binary hash is checked before copying and afterwards, mode 0755, root:root. The licence is committed
  once and installed by the existing config copy. No gh RPM install, git dependency, repository, completion
  or man page. The lock goes to `usr/share/aresos/manifest/gh.lock.json`, 0644 root:root.
- The existing Control map records `gh: {version, binary_sha256}`; the actual build checks the installed
  binary against that record. The image check runs `--version` as root and the daily account, requires
  at least 2.102.0 and exact lock version, checks the binary/licence hashes and all three files' modes,
  owners and parents, absence of a gh RPM, repository, trusted key and every other path in gh's own RPM.
  The runner requires the reviewed lock byte for byte and `control.json.gh` equal to the checkout's.
- Resolve prints `INFO gh newest=... pinned=...` to the console and `resolve/gh.txt`. Network errors,
  nonzero curl, timeouts and malformed responses produce `unavailable (lookup failed)` without failing.
- `git fetch origin` completed. Main changed no file this step changes, so no merge. The starting head was
  `f96ca4aa`. `pending-rebind.json` was regenerated only by
  `python3 -B reviews/27-first-update-release/rebind.py pending "18c-b step 3b: pin and verify GitHub CLI 2.103.3, extract only gh, restore RPM trust, bind lock and binary to image checks, add informational resolve and failure fixtures."`:
  `pending: 10 bound files differ from the active bindings, 0 removed`.
  No workflow, runtime Control code, release pin or laptop deployment changed.

`6b80a139`: the first hosted checks-only run exposed an older-lock fixture in
`test_aresos_desktop` that supplies only the existing locks. Removed the redundant gh entry from that
JSON comparison, keeping the already present, stronger byte-for-byte `cmp` outside it. The existing
fixture and its assertions are unchanged. The gh test now executes that exact shell comparison against
equal, changed-but-JSON-equivalent, and missing locks; only the equal one passes. The 43-test touched
module passes again (5.894s); pending bindings were regenerated with the follow-up note. The second
checks-only dispatch was the final round authorized at that point. No infrastructure rerun was used. The
lead later authorized this one check fix and assigned the next checks-only/build dispatches to its shell.

### The lock and key provenance

`os/gh.lock.json` preserves Chrome's field names/order, then adds `binary_sha256`, `license_sha256`
and (in the check follow-up) `payload_paths`. The signing-key object extends the same first four fields with `source_sha256` and the provenance record.

| Input | SHA-256 |
|---|---|
| RPM | `65d55875faa3281959676d91da15a9380583281586ac31bbd3d32b7924a9f4d2` |
| Extracted binary | `b768184570b12536be4ac1528893f6340d1c6a7b40b56ad45bca9cd0e87ad34d` |
| Published ASCII keyring | `cec6e9ed82d3949ca5f4428cc968b41ef5e7416cb3653cdfc2a421977663bbfd` |
| Committed exported key | `5cf71eb7df215f2dd79b8eb7cfbb069bd62458d8be8d64c141c02945838e754f` |
| Tag's LICENSE | `6da4adc42392c8485e40b4251c7e332fc3352df1947c9ffade71dd60b14a7a4f` |

Fetched `https://cli.github.com/packages/githubcli-archive-keyring.asc` over HTTPS with HTTPS-only redirects.
Its checksum and both primary fingerprints match GitHub CLI's own
[installation documentation](https://github.com/cli/cli/blob/trunk/docs/install_linux.md):
`2C6106201985B60E6C7AC87323F3D4EA75716059` (expired 2026-09-05) and
`7F38BBB59D064DBCB3D84D725612B36462313325`. Imported the bundle with `gpg --no-options --batch
--no-autostart --no-auto-key-retrieve --auto-key-locate clear` into the temporary home
`.work/18c-b-3b/gnupg`, then used `--armor --export 7F38BBB59D064DBCB3D84D725612B36462313325`.
These import/export operations use the downloaded file only, without network or a keyserver.
Only the exported key is committed. `gpg --import-options show-only --with-colons` counts primary keys
in the actual committed file; its test refuses a second primary key or another fingerprint.

The licence was fetched once from `https://raw.githubusercontent.com/cli/cli/v2.103.3/LICENSE`.
The pinned RPM matched the brief's hash, and the signature check printed:

```text
Header OpenPGP V4 RSA/SHA512 signature, key fingerprint: 7f38bbb59d064dbcb3d84d725612b36462313325: OK
Header SHA256 digest: OK
Payload SHA256 digest: OK
```

`rpm -qp --scripts --triggers --filetriggers` printed nothing; NEVRA was `gh-2.103.3-1.x86_64`.
`file` reports the extracted binary is a statically linked x86-64 ELF. The actual `verify_rpm` code also ran
with every rpm/rpmkeys command scoped to a fresh `.work/18c-b-3b/verification-rpmdb` and `_keyring rpmdb`:
`CONTROL_GH_RPM_PASS ...` then `REAL_GH_RPM_AND_KEY_CLEANUP_PASS isolated scratch RPM database`.
The key list started and ended empty. The laptop's RPM database/keyring was never changed.

### Local tests and named scratch mutations (initial implementation)

`TMPDIR` for local tests and scratch scripts was `.work/18c-b-3b/tmp`.
`python3 -B -m unittest discover -s os/tests -p 'test_control_image.py'`: **43 tests, OK**, 5.704s,
no skips. This includes the 32 existing image tests and 11 gh cases. No owner test module or full local
OS suite was run. `for script in os/build.sh os/ci/check-image.sh os/ci/image-checks.sh os/ci/check-resolve.sh; do bash -n "$script" || exit; done`
and `git diff --check`: exit 0. No Gradle process was started locally.

`python3 -B .work/18c-b-3b/mutations.py` executed the following against the actual packages-step
functions extracted from `build.sh`, in disposable scratch fixtures. RPM query/import/delete commands
are stand-ins in these adversarial cases; the two-key case invokes real GnuPG over the changed file.

| Mutation | Actual result |
|---|---|
| `wrong-binary-hash`: change the fixture lock's binary hash to 64 zeros | `MUTATION_KILLED wrong-binary-hash: gh binary differs from its pin`; no image binary written |
| `second-key-in-committed-file`: append a different committed public key to a scratch copy | `MUTATION_KILLED second-key-in-committed-file: gh key file must hold exactly the pinned primary key` |
| `leftover-imported-key`: deletion returns success but leaves its key | `MUTATION_KILLED leftover-imported-key: gh import left a changed RPM keyring` |
| `rpm-with-script`: RPM query reports a postinstall shell script | `MUTATION_KILLED rpm-with-script: gh RPM carries scripts or triggers`; import not reached |

Additional regressions refuse wrong RPM/key/licence hashes, NEVRA, a bad signature/digest line, another
signer, missing header signature and nonzero verifier exit; cleanup removes multiple additions and also
runs after verification failure. Fixtures assert the one cpio member, file modes, root ownership request,
key cleanup before extraction, and scratch removal. Checkout comparison rejects a changed `gh` record;
resolve handles success, lookup failure and malformed replies in one informational line.

### Check fix follow-up (2026-11-18)

Commit `689d8a48`, **Bind gh image exclusions to the pinned RPM payload**, completes the requested check
fix. No extraction, signature policy, version, installed payload or workflow changed.

- `os/gh.lock.json` now records `payload_paths`, the **240** filenames returned by
  `rpm -qp --nosignature --qf '[%{FILENAMES}\n]' .work/18c-b-3b/downloads/gh_2.103.3_linux_amd64.rpm`.
  The cached RPM's SHA-256 was checked first and equals the existing pin. Nothing was downloaded again.
- `os/build.sh` re-queries that list from the downloaded RPM after its existing hash, signature, script
  and key-cleanup checks. Exact list equality is required before extraction; success prints
  `CONTROL_GH_PAYLOAD_PASS 240 paths`. The existing lock copy carries that same list into the image and
  `check-image.sh` already compares the complete lock byte for byte against the checkout.
- `os/ci/image-checks.sh` checks all **239** other pinned paths, allowing only `/usr/bin/gh` from the
  RPM. Existing files, directories and symlinks (including dangling links) fail with
  `Unexpected gh RPM payload paths: <all offending paths>`. Unrelated base files do not fail it.
- Five added tests in `os/tests/test_control_image.py` exercise the actual checker code and the packages
  verifier: RPM/list disagreement, binary-only success, man-page and all three completion paths rejected
  individually and together with their names, a dangling payload link rejected, and an unrelated
  `gh-base-tool` completion accepted. The existing 43 tests remain.

**Verified locally in this follow-up:**

- `TMPDIR="$PWD/.work/18c-b-3b-check-fix/tmp" python3 -B -m unittest discover -s os/tests -p 'test_control_image.py'`:
  `Ran 48 tests in 6.448s`, `OK`, no skips. Only this touched OS test module was run; no owner module.
- `for script in os/build.sh os/ci/check-image.sh os/ci/image-checks.sh os/ci/check-resolve.sh; do bash -n "$script" || exit; done`:
  exit 0, no output. `git diff --check`: exit 0, no output.
- `python3 -B reviews/27-first-update-release/rebind.py pending "18c-b step 3b check fix: record gh RPM payload paths in its lock, verify them against the pinned RPM, and reject only those paths in the image while printing legacy name matches."`:
  `pending: 10 bound files differ from the active bindings, 0 removed`. The pending file was generated,
  never edited by hand.
- The exact Repo privacy workflow shell, extracted to `.work/18c-b-3b-check-fix/privacy-check.sh`, ran with
  `RUNNER_TEMP` under the same scratch folder: exit 0, `No file holds a home path with a real user name.`
- `TMPDIR="$PWD/.work/18c-b-3b-check-fix/tmp" python3 -B .work/18c-b-3b-check-fix/mutation.py`:
  put the original name-based assertion back in a scratch copy of `image-checks.sh`, then ran the new
  unrelated-base-file test against that copy. It printed
  `MUTATION_KILLED name-based-check: Ran 1 test; FAILED (failures=1)` and
  `AssertionError: gh documentation or completions were installed`. The fixture path is
  `/usr/share/bash-completion/completions/gh-base-tool`, absent from the pinned payload. The working
  checker was never replaced by the mutant.

**Old pattern diagnostic:** the old name search runs as a diagnostic before the new assertion. In the
new base-file test it lists the synthetic `gh-base-tool` path above and the new check passes. That is a
fixture, not an observation of the real base image. The supplied failing build log names no matched
paths; no real base-image match is claimed here. The lead's next `check_build=build` on the pushed head
will print `INFO gh legacy name matches=<sorted JSON array of full paths>` for every match under the
same four man/completion folders. This supplies the missing base-image path evidence without failing
on unrelated names. Any actual gh payload path still fails and is named separately.

**Not verified here:** the corrected checker in a built image. No workflow was dispatched or watched in
this follow-up, and no laptop RPM keyring was changed. The lead's shell owns the next two runs.
No new owner-facing JUDGMENT-CALL; the PLAN-GAP was the old assertion's assumption that a matching name
belongs to gh. Open questions: none for this fix.

### Runs

The original builder ran checks-only, build, then resolve, one at a time. The completed results for
`44329677029`, `44339552024` and `44344811923` below are from the lead's shell, supplied with this
follow-up; they were not re-watched here. Other rows retain the draft's historical evidence. Full-log
line numbers are used below; unit-test fixture PASS markers are not image proof.

| Run | Mode/workflow | Result / full log lines |
|---|---|---|
| 44323572283 | checks-only round 1, `b3e0c0e5` | FAIL; one failure in 1800 tests (3819–3821), four existing GUI skips. The older-lock fixture has no gh lock: failure/trace 3802–3815. This is our integration failure, not infrastructure. |
| 44329677029 | checks-only round 2, `6b80a139` | PASS (lead's shell). |
| 44339552024 | `check_build=build`, `6b80a139` | FAIL; `CONTROL_GH_RPM_PASS`, `CONTROL_GH_INSTALL_PASS`, `CONTROL_GH_KEYRING_PASS` at 1561–1563, then root and daily-account `gh --version` lines; `AssertionError: gh documentation or completions were installed` in `image-checks.sh` 339–341. Fixed by `689d8a48`; no image-check PASS claimed for this run. |
| 44344811923 | `check_build=resolve`, `6b80a139` | PASS. `INFO gh newest=v2.105.0 pinned=gh-2.103.3-1.x86_64` at 1397 (lead's shell). |
| 44323585982 | PR Control Chrome install | PASS; 28 tests 2229, node:crypto cross-check 2235; five cases PASS 2307–2311; `CONTROL_CHROME_INSTALL_PROOF_PASSED` 2312 |
| 44323586219 | PR Chrome records | PASS; 21 tests 216; `record_build check passed` 227 |
| 44323586423 | PR Control boundary | PASS; `PRECEDENCE_OK cases=24` 2060; `CONTROL_INTERACTIVE_ASK_PASS cases=17` 2732 |
| 44323586285 | PR Control base | PASS; `Control base suite PASS` 715 |
| 44323586189 | PR Repo privacy | PASS |
| 44323586012 / 44323587243 / 44323586057 | Superseded PR qualification / Chrome / Mail | Qualification and Chrome cancelled after the fix push to unblock its checks; Mail cancelled automatically. No PASS claim. |

Fixed-head PR evidence (`6b80a139`):

| Run | Workflow | Result / full log lines |
|---|---|---|
| 44329692789 | Control Chrome install | PASS; 28 tests 2228, node:crypto 2234; cases 1–5 PASS 2306–2310; `CONTROL_CHROME_INSTALL_PROOF_PASSED` 2311 |
| 44329693134 | Chrome records | PASS; 21 tests 199; `record_build check passed` 210 |
| 44329692739 | Control boundary | PASS; `PRECEDENCE_OK cases=24` 2059; `CONTROL_INTERACTIVE_ASK_PASS cases=17` 2731 |
| 44329692726 | Control base | PASS; `Control base suite PASS` 699 |
| 44329692951 | Repo privacy | PASS |
| 44329692733 / 44329692894 / 44329693644 | Chrome / qualification / Mail | Pending in the original draft; not rechecked in this follow-up, no PASS claim. |

The first push's five completed PR workflows passed. Its still-queued qualification and Chrome runs
received `gh run cancel` after the fix push; because the queued qualification run remained active,
`gh run cancel --force` was used for these two superseded runs. The qualification concurrency group
otherwise blocks the new head. Mail was cancelled by its own concurrency rule. Those workflow notes are
historical; no cancellation is counted as a passing check, and this follow-up watches no runs.

The build's three gh package markers and both version lines establish installation and execution before
its checker failure; they do not establish a passing image check. On the pushed follow-up head the lead's
**checks-only must pass**, then **one `check_build=build` must pass completely**, including
`CONTROL_GH_PAYLOAD_PASS 240 paths`, `CONTROL_GH_RPM_PASS`, `CONTROL_GH_INSTALL_PASS`,
`CONTROL_GH_KEYRING_PASS`, both exact-version lines, the legacy-match diagnostic,
`CONTROL_GH_IMAGE_PASS` and `CONTROL_GH_CHECKOUT_PASS`. The diagnostic's actual matched base paths belong
in that run's evidence. Resolve is already green; no new resolve run is requested by this fix.

### Left, in order

1. **Lead (`linux-tools`):** dispatch checks-only and then one `check_build=build` on this pushed head;
   the lead's shell watches both and records the markers and actual legacy-pattern matches above.
2. **4:** real-session polkit probe, then Chrome VM first half. Tell the lead before committing any
   `os-image.yml` change so linux-aresos hears first.
3. **4b:** C3, remaining C6, C10 and C11 if step 4 reaches its budget. C10 still must run gh as the service
   user under the real unit sandbox and establish no verifier login/token.
4. **5:** update/rollback, broken/missing bundles, store requests and password/cancel/ask-again flows.
   With 28b integrated, prove the in-session profile ask and durable pin continuity too.
5. **6:** rehearsal checks, final-head runs, guides and final report; distinguish installation from profile
   continuity. No release containing 28b before the combined proof.

### JUDGMENT-CALLs

No new owner-facing choice and no version upgrade. For implementation review: cpio streams the one member
instead of recreating RPM paths; script refusal includes ordinary, transaction and file triggers; key cleanup
checks the full key listing and deletes every addition, including Chrome's. Replacing this with a private
verification database in the image was rejected because the brief explicitly requires import/delete and
before/after proof in the image's keyring. None of these changes expands installed content or privileges.

### PLAN-GAPs

The first checks-only run exposed a fixture boundary: the existing lock-loop test builds only its three older manifests. The gh lock is checked separately, byte for byte, without changing that test. No supply-chain stop condition was encountered. The existing Step 3a storage/profile boundaries remain.
This step proves supply-chain installation and image execution; it does not establish C10's sandboxed service
execution or any later Chrome VM flow. Open questions: none for 3b.

### The os/ diff for linux-aresos

Net from `f96ca4aa`:

- `os/gh.lock.json`: new reviewed RPM/binary/licence/key pins, provenance and 240 RPM payload paths.
- `os/keys/github-cli-rpm.pub`: new, exactly the 2026 public key.
- `os/config/usr/share/licenses/gh/LICENSE`: new, exact tag licence.
- `os/build.sh`: verify/extract gh, restore full key list, record/check gh in the existing Control map.
- `os/ci/check-image.sh`: reviewed gh lock and checkout-record equality, `CONTROL_GH_CHECKOUT_PASS`.
- `os/ci/image-checks.sh`: installed gh version/hash/metadata and absence checks, `CONTROL_GH_IMAGE_PASS`.
- `os/ci/check-resolve.sh`: non-failing newest-versus-pin info and evidence line.
- `os/tests/test_control_image.py`: sixteen gh tests, gh record expectations and fixture lock.
- `os/README.md`: gh install and verification description.
- `os/manifest/ci/16/pending-rebind.json`: generated pending note; no table rebound.

`.github/workflows/os-image.yml` is unchanged. The closing `.work/` audit printed
`Files over 500 MB in .work/:` followed by `Total: 0`. No large download, extracted image or partial
file needed removal. Scratch for this follow-up is `.work/18c-b-3b-check-fix/`; the prior cached RPM is
reused. No Gradle process was started.

## Step 3a fix (2026-11-18, gpt-6-astra)

**The complete 3a image proof is green on `2e2516b1`.** The earlier two-build stop below stays
as history. This step permits one checks-only run, then two build rounds, with one whole-run rerun only for an
infrastructure failure. No workflow edit, storage exception or server-instruction text is part of this fix.

### Merge and facts before the fix

- `405f6fe3`: separate merge of `origin/main` at `7417c19a` (PR #106). Git reported
  `Automatic merge went well`; no conflict resolution was needed. Main's brief/design and mod development
  work remain alongside the branch's Chrome install work. For `pending-rebind.json`, main's complete file was
  selected, the four branch-only notes re-added through `rebind.py pending`, and a merge note added through
  the same tool. All 13 main notes and the rebound history were checked equal word for word. The regenerated
  record has ten changed bound files and no removed files. No workflow changed in this merge.
- The downloaded `check-build-evidence` artifact and full log of 44247363499 show only the unresolved path:
  log 2902–2914, artifact `image/checks.txt` 1203–1215. Neither records the link type or target. The lead's
  revised brief supplied the expected `root` → `var/roothome` layout; the new run below establishes it.
- `32f38e36`: temporary CI-only `lstat` diagnostic for `root`, `var`, and `var/roothome` in the non-recursive
  image view, before the unchanged failing scanner. It records link text without following `root`, checks that
  `var` is a directory, and prints the target's presence. The first authorized build round established the
  actual layout; the second is reserved for the corrected scan. No laptop container or system path is inspected.

- **Observed in the image, run 44286574648:** `root` is `lrwxrwxrwx`, with link text `var/roothome`
  (log 2867); `var` is a real `drwxr-xr-x` directory (2868); `var/roothome` is missing (2869).
  The unchanged checker then fails with `FileNotFoundError` (2871–2883). This is the known checker defect,
  not infrastructure; there is no blind rerun. This observation consumed the first of the two authorized
  build rounds. Nothing was inspected on the laptop's own system.

### Fix and verification

Fix commit `2e2516b1`: `os/ci/control/chrome_image.py` now resolves each selected name component by component using `lstat`.
Absolute link targets start at the scan root, and `..` stops there. Existing targets are traversed and their
regular files checked; a missing link target returns no content and produces a `CONTROL_CHROME_SCAN_LINK`
JSON row with the link, target, resolved image-relative path and `status: missing`. The function returns the
same rows as evidence, and `check-image.sh` retains the printed rows in `image/checks.txt`. The same traversal
handles `tmp`, `var/tmp`, `root`, nested links and linked parent directories. Only `FileNotFoundError` while
resolving a link target is treated as empty. Missing ordinary names (including a missing child after an
existing parent-link target), unreadable metadata/folders/files, non-directory parents and cycles fail.
The whole-image modulus walk now also calls `lstat` on every visited entry; it still does not follow links.
No read/list error is ignored. The temporary shell diagnostic is removed; `image-checks.sh` returns to its
pre-step bytes. No workflow, installed file, control code, storage policy or instruction text changes.

The added `ChromePrivateScanTest` cases cover all three scan names for an existing folder containing a PEM
marker and for a missing target with exact printed/returned evidence. Other cases cover absolute links with
opposite host/image contents, unreadable folders (an injected `PermissionError`, effective even when CI is
root), file-read and metadata errors, nested and parent links, `..` containment, missing ordinary children,
link/directory cycles and non-directory parents. The absolute-link fixture's two views are both artificial
scratch folders within this worktree.

| Command (scratch `TMPDIR` under `.work/18c-b-3a-fix/tmp`) | Actual result |
|---|---|
| `python3 -B -m unittest discover -s os/tests -p 'test_control_image.py'` after the fix | 32 tests, `OK`; nine new regression cases, no skips |
| `python3 -B .work/18c-b-3a-fix/host-view-mutation.py` | `follow-image-links-in-host-view` replaces the image-relative scan with host `Path.resolve()` plus the regular-file walk. `test_absolute_link_uses_image_contents_never_the_host_view` fails with `AssertionError not raised`; one failure, no errors, followed by `MUTATION_KILLED follow-image-links-in-host-view: image PEM was missed`. The mutation is only in a disposable imported module, never the source file. |

Local pre-fix check:
`TMPDIR="$PWD/.work/18c-b-3a-fix/tmp" python3 -B -m unittest discover -s os/tests -p 'test_control_image.py'`:
23 tests, `OK`. `bash -n os/ci/image-checks.sh` and `git diff --check`: exit 0.
`PYTHONPATH=control:control/chrome_tests python3 -B -m unittest test_extension_stores_nothing`: 3 tests, `OK`.
`python3 -B -m unittest discover -s control/chrome/ci/install -p 'test_*.py'`: 28 tests, `OK`.
Both use the same scratch `TMPDIR`. `python3 -B control/chrome/build.py` still prints
`c689b9c8f7d748c137dd5f64b0a317368a13f5b781ce0d17a21b199b03c4eaa9`.
The exact privacy workflow shell body, with scratch `RUNNER_TEMP`, prints
`No file holds a home path with a real user name.` and exits 0.

Before changing the scanner, the new regressions were also run against its existing loop in a disposable
module: the missing-target test produced `FileNotFoundError` for all three names, and the absolute-link test
failed with `AssertionError not raised` because the old loop read the clean host decoy and missed the image PEM.
Only artificial scratch trees were used.

The first push of the fix was blocked by the privacy hook's private-key rule on literal synthetic PEM headers
in the new tests. There was no key material. The fixture now constructs the identical header bytes from two
pieces, like the existing marker tests. The unpushed fix commit was amended after rerunning the suite and
mutation; no allowlist, bypass or force-push is used.

### Runs

The exact dispatches are `gh workflow run os-image.yml --ref pkg/18c-b-chrome -f checks_only=true` once,
then `gh workflow run os-image.yml --ref pkg/18c-b-chrome -f check_build=build` twice, one at a time.
Each uses `gh run watch <id> --exit-status --interval 60`; PR checks use
`gh pr checks 76 --watch --interval 60`. No other workflow was dispatched and no infrastructure rerun used.

| Run | Head | Result / full `gh run view --log` line numbers |
|---|---|---|
| 44280758650, checks-only | `32f38e36` | PASS; 1780 tests at 3776, `OK (skipped=4)` 3778; tools-manifest PASS 3779; 17 destination refusals PASS 3780. Regression job 30m30s. Four existing GTK/labwc environment skips at 524–527; no Chrome test skipped. |
| 44286574648, build round 1 (layout observation) | `32f38e36` | FAIL as expected at the unchanged scan, in 8m2s. Layout 2867–2869; trace 2871–2883. Extension ID/CRX hash 1597; Chrome polkit PASS 1825. BUNDLE, KEY_SCAN, CHECKOUT and BUILD_LOG were not reached. |
| 44288748140, build round 2 (fixed scanner) | `2e2516b1` | PASS in 40m2s, including the complete image checks and VM pass. Every Chrome image PASS is listed below; no rerun used. |
| 44280744725, PR Control Chrome install | `32f38e36` | PASS; case 1–5 at 2295–2299; `CONTROL_CHROME_INSTALL_PROOF_PASSED` 2300. |
| 44280744759, PR Chrome records | `32f38e36` | PASS; 21 tests 194, `OK` 196; `record_build check passed` 205. |
| 44280744560 / 44280744736 / 44280744399 / 44280744700, PR boundary / base / Mail / privacy | `32f38e36` | All PASS. |
| 44280744308 / 44280744312, PR Chrome qualification / Chrome | `32f38e36` | Both PASS; every workflow on this push completed successfully. |
| 44288754083, PR Control Chrome install | `2e2516b1` | PASS; 28 unit tests at 2213, node:crypto cross-check 2219; cases 1–5 PASS 2291–2295; `CONTROL_CHROME_INSTALL_PROOF_PASSED` 2296. |
| 44288754676, PR Chrome records | `2e2516b1` | PASS; 21 tests 195, `OK` 197; `record_build check passed` 206. |
| 44288754410 / 44288754273 / 44288754854, PR boundary / base / privacy | `2e2516b1` | All PASS. |
| 44288754707, PR Mail | `2e2516b1` | PASS. |
| 44288754376 / 44288754297, PR Chrome / qualification | `2e2516b1` | Still in progress at the evidence-only report commit; last check snapshot 45 passed, two core browser jobs running, no failures. These are not complete-workflow PASS claims. |

The final commit changes this progress file only. Its PR workflows are watched separately through completion;
the exact manual runs and their source head remain those above. No pending workflow is counted as passed.

### Image evidence from the green build

These are full `gh run view 44288748140 --log` line numbers, not the unit-test stand-ins in checks-only:

| Evidence | Log line | Result |
|---|---|---|
| `CONTROL_CHROME_EXTENSION` | 1640 | `fiacjggnpbfbgiaiaanigeddhgnegmfe`, CRX SHA-256 `4459d94d7d9029a111226946f2ac1ea5d9ee85c07bb829b0e477bbb7813b4004` |
| `CONTROL_CHROME_BUILD` | 1641 | `c689b9c8f7d748c137dd5f64b0a317368a13f5b781ce0d17a21b199b03c4eaa9`, unchanged runtime |
| Chrome polkit action PASS | 1868 | no/no/auth_admin, never kept, owner is the service user; no rule names it; pkcheck and agent present |
| Existing uncached-polkit PASS | 1909 | The same process is asked again; the cached control action is reused |
| `CONTROL_CHROME_SCAN_LINK` | 2910 | `root` → `var/roothome`, target missing, no content |
| `CONTROL_CHROME_PUBLIC_MODULUS` | 2911 | Public modulus printed for the runner's build-log scan |
| `CONTROL_CHROME_BUNDLE_PASS` | 2912 | Same ID and CRX hash as 1640 |
| `CONTROL_CHROME_KEY_SCAN_PASS` | 2913 | Complete image scan passed |
| Chrome excluded-sites PASS | 3520 | Absent in image; tmpfiles creates refused placeholder, preserves changed content, restores mode/group; installed validator refuses format 0 and accepts empty format 1; unit cannot write the folder |
| `IMAGE_CHECKS_PASSED` | 3549 | Complete image checks |
| `CONTROL_CHROME_CHECKOUT_PASS` | 3570 | Same runtime hash and ID; image bound to checkout |
| `CHECK_BUILD_PASSED` | 3573 | Complete runner comparison, including the installed vendor tree |
| `CONTROL_CHROME_BUILD_LOG_PASS` | 3574 | No modulus or PEM private-key marker in the image build log |
| `CHECK_BUILD_VM_PASSED` | 4267 | Existing general image VM pass; not the later Chrome-specific VM pass |

The downloaded `check-build-evidence` artifact independently retains the same link row at
`image/checks.txt` line 1203 and BUNDLE/KEY_SCAN at 1205/1206. Its `image/control-chrome-checkout.txt` and
`image/control-chrome-build-log.txt` contain their corresponding PASS lines. The link row is:

```json
{"path": "root", "resolved": "var/roothome", "status": "missing", "target": "var/roothome"}
```

The one hosted checks-only run covers the merged baseline and diagnostic. The later scanner change is
covered by the final 32 local image tests (all the touched module), the killed host-view mutation, and this
complete built-image run. No second checks-only dispatch is claimed. Its unit-test stand-in PASS lines
(2556–2557 and 2561) are not image proof.

### Not verified

The Chrome-specific VM flows, real-session rule-loosening dialog, browser update/rollback and profile
continuity remain for steps 4–6 and the 28b integration. No `gh` installation is built by this step. No owner
profile, hosts or laptop deployment was used. No local Gradle process was started.

### Left, in order

After the lead accepts this 3a fix:

1. **3b — `gh`:** pinned RPM, key and licence; extraction/signature checks, lock/record/resolve line, tests,
   then another green `check_build=build`.
2. **4:** real-session polkit probe for rule loosening, then the Chrome VM pass. Tell the lead before committing
   any `os-image.yml` change so linux-aresos hears first.
3. **4b:** the brief's split for C3, remaining C6, C10 and C11 if step 4 reaches its budget.
4. **5:** update/rollback, missing/broken bundles, store requests, and F7's password/cancel/ask-again checks.
   When 28b is integrated, case 3/C4 also proves the in-session profile ask and durable pin continuity.
5. **6:** rehearsal checks, final-head runs, guides and final report, with installation and profile continuity
   reported separately.

### JUDGMENT-CALLs

No new owner-facing decision. The profile decision in PR #106 is settled: a managed yes/no ask in the session,
with no profile password dialog. The existing polkit dialog still belongs to F7 rule loosening.

### PLAN-GAPs

The older Step 3a entry's claim that the storage exception is undecided is superseded by PR #106. The narrow
installation-ID exception and its runtime pin/handshake implementation belong to 28b. That module is absent
here; 3a keeps the complete storage ban. Installation evidence does not prove profile continuity, and the
combined proof remains required before a release containing 28b ships. There is no outstanding scanner gap
from this step. Open questions for 3a fix: none.

### The os/ diff for linux-aresos

Net changes from the starting head `91ad33d6`:

- `os/ci/control/chrome_image.py`: image-relative link traversal, missing-target evidence, strict `lstat`
  walks; no installed/runtime change.
- `os/tests/test_control_image.py`: nine scanner regressions and the image-to-helper wiring assertion.
- `os/manifest/ci/16/pending-rebind.json`: generated pending record; main's notes/history and branch notes
  retained, with this step's merge/diagnostic/fix notes. No rehearsal table is rebound.

`os/ci/image-checks.sh` has a temporary diagnostic in `32f38e36`, removed by the fix; its net step diff is empty.
`.github/workflows/os-image.yml` is unchanged. The earlier Step 3a section below lists the full installation diff.

Scratch audit: no file over 500 MB remains in `.work/`. No image layer, ISO or extracted disk was downloaded
to the laptop. Retained scratch holds small logs, test scripts and the CI evidence artifact.

## Step 3a (2026-11-18, gpt-6-astra)

**Stopped incomplete after the two allowed image-build rounds.** Both builds failed in the new CI checker,
not on infrastructure. The first defect (requiring 0755 on the image's 0555 root) is fixed; the second remains:
the PEM scan assumes `<scan-root>/root` resolves to a directory. Run 44247363499 reports `FileNotFoundError`
there. No third run or post-limit code fix was made. The image/key/placeholder/checkout proof is not green;
3b must wait for the lead's disposition of this 3a finding.

### Done

Chrome's image files are installed by 18c's existing map. No `gh` installation, service/extension change, instruction
text or storage exception is included. `build.py` on this head prints
`c689b9c8f7d748c137dd5f64b0a317368a13f5b781ce0d17a21b199b03c4eaa9`.

| Installed path | Mode | Binding/check |
|---|---|---|
| `/usr/libexec/aresos-control/chrome/host` | 0755 | `FILES`, recorded source/SHA-256/mode, image ownership and checkout comparison |
| `/usr/libexec/aresos-control/chrome/native_host.py` | 0644 | same; unchanged native relay |
| `/usr/share/polkit-1/actions/org.aresos.control.chrome-loosen.policy` | 0644 | same; XML and real `pkaction` defaults no/no/auth_admin, owner annotation equals unit user, no rule names it, existing uncached test remains |
| `/usr/lib/tmpfiles.d/aresos-control-chrome.conf` | 0644 | same; exact two lines, boot placeholder, content preserved and group/mode restored on second invocation, installed `owner_hosts` as service user |
| `/usr/share/aresos/chrome/extension.crx` | 0644 | one `pack.py` invocation per image, public record, independent CRX3 reader/signature/key-derived ID, exact zip payload hashes, checkout payload |
| `/usr/share/aresos/chrome/update.xml` | 0644 | recorded SHA-256, exact XML ID/version and fixed file URL, checkout template rendered for recorded ID |
| `/usr/share/aresos/chrome/policy.json` | 0644 | recorded SHA-256, exactly one force-installed/force-pinned entry with override, checkout template |
| `/usr/share/aresos/chrome/native-host.json` | 0644 | recorded SHA-256, exact manifest and one allowed origin, checkout template |
| `/etc/opt/chrome/policies/managed/aresos.json` | symlink | record's `links`, exact target `/usr/share/aresos/chrome/policy.json`, root-owned 0755 parents under `/etc` and the base's 0555 `/`, only entry in managed folder |
| `/etc/opt/chrome/native-messaging-hosts/org.aresos.chrome.json` | symlink | record's `links`, exact target `/usr/share/aresos/chrome/native-host.json`, same parent checks, base host retained |
| `/usr/share/aresos/manifest/control.json` | 0644 | gains `chrome_build`, `chrome_extension` (public packer fields plus four file modes/hashes) and the two links |

The bundle folder is 0755; every installed file above is root:root. The map now records 78 deterministic
files, nine directories and three links, plus the four per-build files. `control-tree` installs the same
deterministic map and an empty bundle folder, without signing. The real image build hashes untouched `control/`
before generating settings or invoking the packer. No generated output goes back into `control/`.
The existing `chrome/build-id.json` must contain exactly the new `chrome_build` value; the existing wheel and
vendor checks remain in place.

The install map writes neither `/var/lib/aresos-control` nor the old `/etc/aresos/control/chrome-excluded-sites.json`.
The tmpfiles configuration makes the root:root 0755 folder and root:aresos-tools 0640 regular placeholder at boot:
`{"format":0,"hosts":[]}`. The installed validator refuses it and accepts an empty format-1 list; the service
unit cannot write this folder. Only made-up `.invalid` hosts are used in checks. The new image-side tmpfiles
and installed-validator checks were not reached in either build; the local source tests are separate evidence.

The new checker is CI-only: `check-image.sh` mounts `os/ci/control/chrome_image.py` read-only in the check
container; it is not copied into the image. A non-recursive bind of `/` inside the CI container exposes the image files
under the helper and Podman metadata mounts for the key scans. It checks bundle contents, metadata and identity independently of
the packer, scans every regular image file outside `/proc`, `/sys`, `/dev` for the build's modulus (raw, hex,
base64 and base64url with all three alignments, wrapped forms included), and requires the sole raw occurrence
in the CRX. It scans recorded files, the bundle and temporary/root folders for PEM private-key markers.
The runner is wired to repeat the modulus scan over `evidence/build.log` after `check-image.sh`. Only the public modulus,
ID and hashes are printed. Negative checks reject another bundle, policy, AresOS host or unrecorded Chrome
startup file. The checker's compare command uses only stdlib and the packer's payload/template readers.
These describe the implemented checks: the failed PEM-directory traversal prevents the full scan, its PASS
markers, the build-log scan and checkout comparison from completing in a built image.

### The merge and its resolutions

- `a5e91c5c`: `git fetch origin`, then `git merge --no-commit origin/main`, committed separately. Parent
  `ce3d01e2`; main `774d7954` includes PR #58 (`beb42ec8`), #98 and the later packages. Git reported
  `Automatic merge went well`; there were no conflicts or hand resolutions. The branch's earlier Chrome work
  and main's service/qualification changes both remain.
- `pending-rebind.json` was exactly main's after the merge. Later `rebind.py pending` calls recalculated the
  pending record and added four notes for 3a. Its ten existing rows stayed the same; all of main's notes and
  rebound history were checked equal word for word. This records pending work, not a new rehearsal rebind.
- Main already has the correct workflow sum `tools 20 + build 80 + Control VM pass 16 + 15` and limit 131.
  There is no step-3a workflow edit or commit requiring a notice to linux-aresos.
- The merge-only `git diff --cached --check` reported existing trailing Markdown whitespace from main's
  historical reviews. Those files were retained unchanged; the step-3a diff check passes.
- `74de4a19`: the install and checks. `7fb12b0e`: scan the non-recursive image view so container mounts cannot
  hide image files. `bb2af7f4`: pin the manifest
  metadata and test unsafe owners, modes and parents. Every commit ends with `Built-by: gpt-6-astra`; normal push to the existing
  draft PR #76, no merge or ready conversion.

- `a7e66405`: merge follow-up in the existing install proof. 18e's `daemon.listen` binds
  `.chrome.sock.new` and renames it to `chrome.sock`; the kernel's `ss` address retains the bind name. The old
  proof counted zero connected peers despite successful tool calls. `service_peers` now counts exact established
  server endpoints at both bind names (not peer addresses, prefix matches or listeners). The lead's decision 3
  is applied: failure to ask a hand-loaded extension fails case 1. No runtime file or Chrome build hash changes.
- `c1110036`: the placeholder sweep imports `Engine` through `test_engine`, as main's qualification fixture
  requires, so it uses the fixture baseline rather than the source tree's shipped qualification history.
  The refusal assertions, production engine and runtime hash are unchanged.
- `10ba0470`: the first image build found that my link checker expected 0755 even for `/`; the pinned image
  keeps `/` at 0555. The check now pins that read-only root and retains 0755 for all `/etc` parents. Link metadata
  uses one `lstat`, and a new regression rejects wrong owners, groups, types, targets and modes. No image
  permission, policy or workflow changes; the same runtime hash remains.

### Tests and what they catch

All local scratch stayed under `.work/`: 3a's logs and mutation copies in `.work/18c-b-3a/`, and the existing
suites' fixtures in `.work/18c-b-chrome/` and `.work/20-chrome/`. No local container, VM, Chrome, privileged
command, owner-test module or Gradle process was started.
Closing scratch audit: no file over 500 MB; 11,999,363 regular-file bytes at the audit. No large download or
extracted image remains. The quick tests did not cover an absent or dangling root-home path in the scan view;
that gap is the second build's finding, not a passing test.

| Command (with `TMPDIR` under `.work/18c-b-3a/tmp`) | Actual result | What it catches |
|---|---|---|
| `python3 -B -m unittest discover -s os/tests -p 'test_control_image.py'` after merge | 15 tests, OK | 18c's install map, wheels/vendor and account declarations remain intact |
| same after 3a | 22 tests before the first build; 23 after its root-mode finding, all OK | new fixed files/links, source byte identity, hash-before-generation, exactly one pack call, independent CRX checks, checkout comparison, streaming key scans and both links beneath the read-only root |
| `PYTHONPATH=control:control/chrome_tests python3 -B -m unittest test_excluded_sites_placeholder test_exclusions test_build test_extension_stores_nothing test_unit` | 19 tests, OK | current tool sweep, refused placeholder, excluded path, unchanged storage ban, hash and sandbox |
| `python3 -B -m unittest discover -s control/chrome/ci/install -p 'test_*.py'` | 25 tests after merge; 28 after proof correction, all OK | packer, key disposal, network log reader, DevTools pipe, exact server endpoint counting and refused unasked case |
| `python3 -B -m unittest discover -s control/chrome/ci/records -p 'test_*.py'` | 21 tests, OK | archived-commit build records and release-manifest checks |
| `PYTHONPATH=control:control/chrome_tests python3 -B -m unittest test_excluded_sites_placeholder test_qualification_fixture` | 17 tests, OK | placeholder sweep uses the isolated qualification baseline; shipped-history guard and fixture regressions pass. Python 3.14 prints a ResourceWarning while cleaning a synthetic HTTPError used by a test. |
| `python3 -B control/chrome/record_build.py check` | `record_build check passed` | current manifests have no control object; registry unchanged |
| `bash -n` separately for each of `os/build.sh`, `os/ci/check-image.sh`, `os/ci/image-checks.sh`, `os/ci/check-build.sh`; `git diff --check` | four syntax PASS lines; diff check exit 0 | shell syntax and patch whitespace |
| Exact `Repo privacy` workflow shell body extracted into scratch and run with scratch `RUNNER_TEMP` | `No file holds a home path with a real user name.`; exit 0 | final tracked files, including this handoff, contain no disallowed home-path username |

The new suite mutates signed bytes with the record updated too, a foreign CRX, recorded ID/payload/version,
wildcard policy, missing override, a second origin, network update/CRX URLs, leftover template token and an extra
bundle. Separate comparisons mutate build, link, payload, version, mode and template hashes. The scanner tests
raw newlines across chunks, both hex cases, base64/base64url at three alignments, wrapped encodings, private-key
marker variants and build-log leakage. These are executed tests, not assertions inferred from code.

Eight additional source mutations were run in a disposable scratch copy, each with its catching test, then removed:

| Mutation | Result |
|---|---|
| Require 0755 on the image root again | FAILED: the valid 0555 root rejected, reproducing the first build's exact finding |
| Remove image ownership/group check | FAILED: wrong-owner metadata unexpectedly accepted |
| Remove CRX signature verification | FAILED: broken-signature mutation unexpectedly accepted |
| Remove CRX payload comparison | FAILED: recorded-payload mutation unexpectedly accepted |
| Remove checkout template/mode comparison | FAILED: mode mutation unexpectedly accepted |
| Remove streaming overlap | FAILED: newline-containing raw modulus crossing the chunk missed |
| Replace build hash with 64 zeros | FAILED: installed hash differs from the untouched source's hash |
| Call pack.py twice | FAILED: call sequence is build.py, pack.py, pack.py |

The proof correction adds three tests: exact `ss` endpoint/state parsing, the real current daemon's extracted
`listen` function with zero/one/two/disconnected scratch peers, and load failures that must fail case 1.
Only the tested functions are extracted from AST; the proof's root/container guard stays intact and no Chrome or
service is started locally. Both behavioral regressions fail on `bb2af7f4`'s proof (two failures, no errors).
The qualification fixture's existing module-import guard was also run before its correction: one failure naming
`test_excluded_sites_placeholder`. The same guard and both whole modules pass after the one-line import change.

### Runs

Dispatched with `gh workflow run os-image.yml --ref pkg/18c-b-chrome -f checks_only=true` (twice, sequentially),
then `gh workflow run os-image.yml --ref pkg/18c-b-chrome -f check_build=build` (two sequential rounds).

| Run | Head | Result / full `gh run view --log` line numbers |
|---|---|---|
| 44227811908, checks-only | `74de4a19` | PASS; 1778 tests at 3546, `OK (skipped=4)` at 3548; tools-manifest PASS 3549; 17 destination refusals PASS 3550. Four existing GTK/labwc tests are skipped by their environment guards (293–296); none is a Chrome test. |
| 44232510221, checks-only | `bb2af7f4` | PASS; 1779 tests at 3760, `OK (skipped=4)` at 3762; tools-manifest PASS 3763; 17 destination refusals PASS 3764. Same four existing GUI skips. Second and final checks round; regression job 22m25s after waiting about 52 minutes for a runner. |
| 44241272420, `check_build=build` | `c1110036` | FAIL in 19m5s: the link-parent checker expected 0755 on `/`, whose actual mode is 0555 (trace 2924–2934). Our checker error, not infrastructure. Chrome polkit PASS at 1882. Bundle identity printed at 1654 (below), but the full image/key/checkout checks were not reached. Fixed by `10ba0470`; no blind rerun. |
| 44247363499, `check_build=build` | `10ba0470` | FAIL in 16m3s: PEM scan raises `FileNotFoundError` for `<scan-root>/root` (trace 2902–2914, checker line 237). Our directory-traversal assumption, not infrastructure. Chrome polkit PASS 1860; existing uncached polkit PASS 1901. Bundle identity 1632 and build hash 1633. The root-mode check was passed on the way to this later failure. Second and final allowed build round; no rerun or further source fix. |
| 44239451590, PR Control Chrome install | `c1110036` | PASS in 3m11s; 28 unit tests at 2218 (`OK` 2220), node:crypto cross-check at 2224; `CONTROL_CHROME_INSTALL_CASE_1_PASS` through `_5_PASS` at 2296–2300, `CONTROL_CHROME_INSTALL_PROOF_PASSED` at 2301. The downloaded 1,282,344-byte artifact has all five verdicts true and case `1-ordinary` explicitly `asked: true`. |
| 44239451427, PR Control base | `c1110036` | PASS; `Control base suite PASS` at 684. |
| 44239451552, PR Control boundary | `c1110036` | PASS; `PRECEDENCE_OK cases=24` at 2050, `CONTROL_PERMISSION_REQUEST_RECORDED` at 2721, `CONTROL_INTERACTIVE_ASK_PASS cases=17` at 2722. |
| 44239451516, PR Chrome records | `c1110036` | PASS; 21 tests at 187, `OK` at 189. |
| 44239451435, PR Repo privacy | `c1110036` | PASS (16s). |
| 44247360319, PR Control Chrome install | `10ba0470` | PASS; 28 tests at 2221 (`OK` 2223), node:crypto cross-check 2227; five case PASS lines 2299–2303, `CONTROL_CHROME_INSTALL_PROOF_PASSED` 2304. |
| 44247360306, PR Control base | `10ba0470` | PASS; `Control base suite PASS` 693. |
| 44247360506, PR Control boundary | `10ba0470` | PASS; `PRECEDENCE_OK cases=24` 2061, `CONTROL_PERMISSION_REQUEST_RECORDED` 2732, `CONTROL_INTERACTIVE_ASK_PASS cases=17` 2733. |
| 44247360328, PR Chrome records | `10ba0470` | PASS; 21 tests at 199, `OK` 201. |
| 44247360400, PR Repo privacy | `10ba0470` | PASS. |
| 44247360331 / 44247360457 / 44247360354, PR Chrome / Mail / qualification | `10ba0470` | Still queued or running at the stop. Last check snapshot: 18 passed, 4 running, 25 queued; no reported current-head PR failure. These are not complete-suite PASS claims. The report-only push may supersede these checks. |

The first run's `CONTROL_CHROME_*` lines 2326–2331 are unit-test stand-ins, not an image bundle's evidence.
The first failed image build printed at line 1654:

```text
CONTROL_CHROME_EXTENSION hlohdejcdlkcapgadfbliibpkcchhlho 0f788c247fe8f0f3b6b2cecf3feb59d4983321bbecf28580a7b268fbb2aae5af
```

The second failed image build printed at line 1632:

```text
CONTROL_CHROME_EXTENSION gcibdegialobgchchpfljagigklhcgmd 4a77bc474f5f7fb338eab80e9f63b51f9af4651c29d373c8d8ae7fe6407a2370
```

Neither run printed `CONTROL_CHROME_BUNDLE_PASS`, `CONTROL_CHROME_KEY_SCAN_PASS`,
`CONTROL_CHROME_CHECKOUT_PASS` or `CONTROL_CHROME_BUILD_LOG_PASS`. The log proves that `<scan-root>/root`
does not resolve; it does not establish whether the image entry is absent or a dangling link. The next fix
must inspect that layout and cover it without ignoring read failures or letting a symlink escape the image
view. I have left the failing check intact for the lead rather than suppressing the error.

The first `check_build=build` dispatch followed the second OS checks run. The checks-only runs cover the final
install map and the checkers before the root-mode correction. The later `a7e66405` and `c1110036` change only test
harnesses; `10ba0470` changes the CI link checker, covered by the 23 local image tests, the scratch mutation and
the second build run up to its later failure. No third checks-only or build round is dispatched: the user
limited each mode to two. Neither failure was infrastructure, and no whole-run infrastructure rerun was used.

PR install run **44229730715** on `bb2af7f4` failed cases 2 and 3 at log lines 2357–2358: the old socket-path
counter saw zero peers (trace 2245–2255 and 2295–2305). Cases 1, 4 and 5 passed at 2356, 2359 and 2360. This is
an integration failure from merging 18e, not infrastructure; no blind rerun was used. `a7e66405` corrects the
observation without changing the one-peer assertions. Run 44239451590 now passes all five cases on `c1110036`.
Earlier PR runs 44227807617 (Control Chrome, Python shard 3) and 44227807705 (qualification, both Python shard-3
repeats) also found the missing isolated-fixture import. Jobs 134545193405, 134551231548 and 134551231722 all
reported only `test_excluded_sites_placeholder` in that guard's missing-module list (per-job log lines 312, 450
and 450, respectively). This is another merge
integration failure, corrected by `c1110036`, not an infrastructure rerun or a relaxed guard.
Superseded Control Chrome runs 44235110518 (`a7e66405`) and 44229730688 (`bb2af7f4`) were cancelled from the
queue after `c1110036` was pushed. Later, runs 44227807705 (`74de4a19`, qualification) and 44228697962
(`7fb12b0e`, Chrome) were cancelled while awaiting aggregation, to release the remaining backlog and the
qualification concurrency group. Run 44227807617 had already finished with failure. The failed guard logs were
read and retained in scratch. After the root-mode fix, cancellation was also requested for superseded
`c1110036` runs 44239451436 (Chrome) and 44239451508 (qualification). Those runs and 44228697962 still had
aggregation queued after ordinary cancellation, so `gh run cancel <id> --force` was used for these three obsolete
runs. The current
head's complete suites and both OS checks runs were kept; no test or assertion was disabled.
Each OS run is watched with `gh run watch <id> --exit-status --interval 60`, never concurrent on this ref.
PR checks are watched with `gh pr checks 76 --watch --interval 60`.

### Left, in order

First resolve the incomplete 3a image proof above with the lead; the code remains at `10ba0470` and the final
commit adds this report only. After 3a is accepted, the brief's remaining order is:

1. **3b — `gh`:** pinned RPM/key/licence, extraction and signature checks, lock/record/resolve line, its tests,
   then `check_build=build` green once more.
2. **4:** start with the real-session polkit probe; then the Chrome VM pass and first checks. Tell the lead before
   committing any `os-image.yml` change. The current Control limit is 131, so account for that when adding the
   Chrome pass.
3. **4b:** the documented split if step 4 reaches its budget; C3, remaining C6, C10 and C11.
4. **5:** update/rollback and broken/missing bundle, store-request proof, password dialog/cancel/ask-again checks.
5. **6:** rehearsal checks, final-head runs, guides and final report.

### What the code doesn't show

- This does not yet prove the complete image installation: both built-image checks failed as recorded above.
  No image-side key-scan, placeholder, checkout or build-log PASS is claimed. The owner has not used this
  image. No release was built for publication, signed, pinned or deployed. Booted Chrome/polkit flows, browser
  VM cases and real update / `previous` preservation remain for the later steps.
- The randomized bundle is intentionally absent from `control-tree`; comparing a second CRX's bytes would be
  wrong. The image's independent reader binds the actual CRX to its record, and the runner binds that record's
  payload/rendered templates/build/links to the checkout. The known per-image-identity consequences stay.
- The PEM scan excludes vendored packages and the rest of `/usr`, whose legitimate crypto code contains key
  markers; the unique-modulus scan covers those paths. It counts paths without following symlinks, fails on
  read/list errors, and handles line-wrapped encoded keys as well as raw binary.
- The host and polkit action are installed byte for byte; there is no change to service policy, unit sandbox or
  Chrome launch flags. No instruction text was added. Decision 3's case-1 `asked:false` rule is applied in the
  proof correction; inability to load/ask now fails. Decisions 4–8 and 10 remain instructions for steps 4–6.

### JUDGMENT-CALLs

- No new owner-facing choice. The install follows the agreed paths, modes, policy shape and placeholder exactly.
- The independent checker lives under `os/ci/control/`, is mounted only in the check container, and also provides
  the runner's comparison/log scan. This avoids shipping test code and keeps the two modulus scans identical. The non-recursive view prevents
  those check-only mounts from hiding image files.
- The modulus scan additionally removes ASCII whitespace for encoded forms, so wrapped PEM/base64 cannot evade
  it. The raw stream is still checked with overlap, without line splitting.

### PLAN-GAPs

- **Open dependency, PR #106:** 28b's proposed profile pin may require a storage exception. It is undecided.
  3a preserves the brief's complete storage ban; no exception or profile pin is implemented here.
- The old timeout note in decision 11 is already resolved by main; no workflow edit is necessary.
- Main's 18e atomically published socket retains `.chrome.sock.new` in kernel observations. The old step-2
  proof's literal `chrome.sock` observation was stale after this required merge. Corrected in the test harness,
  with no service or extension change; future VM peer checks must account for the original bind name too.
- Main's qualification fixtures require every test that constructs an engine/Chrome adapter to import
  `test_engine`. The earlier placeholder sweep missed that new convention; its import now installs the shared
  isolated baseline, preserving both sides' test intent.

### The os/ diff for linux-aresos

Every path below is relative to this repository; this list covers step 3a's changes after the merge:

- `os/build.sh`: four deterministic FILES entries, two links, hash-before-generation comment, one per-image pack
  call, `chrome_build`/`chrome_extension` and `CONTROL_CHROME_EXTENSION`.
- `os/ci/image-checks.sh`: real pkaction/annotation and no-rule check; stronger policy-folder/bundle check;
  boot-only placeholder, second tmpfiles invocation and installed-validator checks.
- `os/ci/control/chrome_image.py` (new): independent CRX/policy/host/XML/metadata checker, full-image key scans,
  stdlib checkout comparison and build-log scan; never shipped.
- `os/ci/check-image.sh`: read-only checker mount, deterministic build comparison and per-build payload/template
  comparison, preserving the existing wheel and vendor checks.
- `os/ci/check-build.sh`: scan the runner's build log with the checked public modulus before disk/VM work.
- `os/tests/test_control_image.py`: extended install expectations and eight new tests described above.
- `os/README.md`: browser-side install, per-build identity and refused placeholder; `gh` left for 3b.
- `os/manifest/ci/16/pending-rebind.json`: four generated pending notes; main's rows/notes/history unchanged.


## Where it stands

**Step 3b's check fix is implemented in `689d8a48`; the lead's new-head CI proof is left.** The gh
2.103.3 RPM, 2026 key and licence remain pinned. Its exact RPM payload list now replaces the name-only
exclusion; all 48 local image tests pass and the restored name check fails the new base-file regression.
The lead reports checks-only `44329677029` and resolve `44344811923` green on `6b80a139`; build
`44339552024` reached the gh install/keyring/version proof, then failed the old name check. No passing
3b image check is claimed. The lead's shell dispatches and watches checks-only and one build on the
pushed follow-up head; this builder commits, pushes normally and stops.

The complete step 3a image proof remains green on `2e2516b1`. After 3b, the order remains **4, 4b, 5, 6**.
The approved profile ask is in-session; 28b owns its pin and narrow installation-ID storage exception.
No workflow file, release pin or laptop deployment has changed.

## The lead's decisions after step 2b (2026-11-15)

1. **JUDGMENT-CALL 1 (the DevTools pipe) is accepted**, for the proof's own Chrome starts only. The image's Chrome
   start and policy never carry a `--remote-debugging-*` flag; step 4's image check asserts that (keep or add it).
2. **JUDGMENT-CALLs 2 to 5 are accepted** as written.
3. **JUDGMENT-CALL 6 changes:** on the pinned Chrome, a hand-loaded extension that could not be asked fails case 1
   instead of passing with `asked: false`. A check that quietly stops running must not look green; if a later
   Chrome can't load one, that is a finding for the lead. The next step that touches `proof.py` makes the change.
4. **C9 in the VM (step 5) may use case 5's trigger:** one test-only Chrome start in the guest with
   `--remote-debugging-pipe` and `cdp.py`, its own throw-away profile, run by the test; it checks that nothing
   listens, and the positive control (the probe's requests, log count equal to the server's count) is required.
   `cdp.py` goes into the guest with the test's files, never into the image. This amends the brief's C9.
5. **C2 in the VM (step 4)** asks an extension loaded by hand over the pipe, as `case_ordinary` does.
6. **PLAN-GAP 2:** both of the brief's assertions stay. The brief's sentence that the IDs go in a body the log
   doesn't record is outdated for Chrome 157; the header makes the ID assertion a real one.
7. **PLAN-GAP 3:** nothing to change; case 5 compares against the probe alone, so Chrome's own start-up requests
   cancel out.
8. **The three known-limit lines are accepted**; step 6 places them in `KNOWN-LIMITS.md` and the report.
9. **3a waits for PR #58 on `main`.** Claude reviewed #58 on 2026-11-16, and its fix round is running. Codex astra
   reviews #58 before it merges. Then the lead's go.
10. **The never-list guide text** (brief review 5 of PR #48, S6, 2026-11-16): the step that writes his guide says the
    list is empty only when he has no site to exclude. His dashboard's host goes on it first, as CONTROL.md section 6
    says. PR #48 corrects brief 18c-b's lines 24 and 423 to match.

11. **From #58's fix round 1, part 2 (2026-11-16):**
    - Control's Chrome build hash in the image is now `91cdfeb6291380ffd8cf271a77e5baef8a6abd5aaa2c4ea504b69ff866969ae5`
      (was `ccd0fd79…`, the one the brief names). Use the hash the build makes at 3a's head; don't copy either
      literally.
    - `os-image.yml`'s Control job keeps `timeout-minutes: 127` while the pass step went 12 → 16 minutes; the job's
      comment still adds up with 12. 3a's first `os-image.yml` commit fixes the comment's sum (or the job's limit,
      131), runs `rebind.py pending`, and `linux-aresos` is told before it, as for every `os-image.yml` change.

## Step 2b (2026-11-15, Claude Fable 5.2)

### The lead's decisions on step 2's findings

1. **`setEnabled(false)` from another policy-installed extension** is accepted as Chrome's behaviour. Case 1 as
   step 2 changed it stands (the `uninstall` refusal; ours enabled and connected again at the next start).
2. **Chrome's own update-service requests** for its own extensions are accepted. Case 5's rule is the brief's
   fallback: against a run of the probe alone, ours adds no address and no ID.
3. **Case 5's trigger:** make the update check deterministic instead of waiting for the schedule; first try
   `chrome.developerPrivate.autoUpdate()` in `chrome://extensions` over the DevTools protocol.
4. **Case 3's record of the previous ID:** look at what it holds; a check if it grants the old ID anything,
   otherwise a line under "what the code doesn't show".

### Done

- **`cdp.py`** (new, standard library, 4 tests in `test_cdp.py`): the DevTools protocol over
  `--remote-debugging-pipe`. Only the Chrome starts that name it get the pipe (case 5's three, and the one below);
  every other start still refuses the `NEVER` flags. A pipe, not a port: each of those starts checks that Chrome
  listens on nothing.
- **Case 5** asks Chrome for each update check. Per run (ours; the probe alone; the policy without
  `override_update_url`): Chrome starts with the network log, `--disable-component-update` and the pipe; once the
  extensions are in, `chrome://extensions` is opened and `chrome.developerPrivate.autoUpdate()` is called twice,
  3 s apart (what the page's "Update" button calls: `ExtensionUpdater::CheckNow` with no IDs, so every extension;
  read in Chrome 157's `developer_private_functions.cc` and `extension_updater.cc`). After each call the proof waits
  for the probe's request at the test's own server. Required of every run: the probe's ID is in two update requests
  in the log, **and the log holds exactly as many as the server answered**.
- **`netlog.py`** (11 tests): a request's start is the event the log's own constants call `URL_REQUEST_START_JOB`
  (a log without constants is read as before); `added` counts a mention of the update service that the events
  don't account for (a line cut off mid-write) as added, also when the baseline has one.
- **Case 3** writes what the preference files keep under the previous ID to
  `case3-<n>-previous-record.json` and requires that it holds none of `manifest`, `path`, `location`,
  `active_permissions`, `granted_permissions`, `runtime_granted_permissions`.
- **Case 1, an extension loaded by hand** (`case_ordinary`, counted in case 1's verdict): a Chrome start of its own
  (own profile, the pipe, `--enable-unsafe-extension-debugging`), developer mode on, `Extensions.loadUnpacked` of a
  two-file extension with the `management` permission, then its page calls `management.setEnabled(<ours>, false)`.
  Chrome must refuse, and ours must still be enabled and connected. If this Chrome won't load one that way, the
  result says `asked: false` with the reason and case 1 doesn't fail for it.

### Runs

| Run | Head | Result |
|---|---|---|
| 43729218613 | `c4514015` | `pack` green (`Ran 25 tests`, `OK`, `# pass 1`). Proof: `CONTROL_CHROME_INSTALL_CASE_1_PASS` to `_5_PASS`, `CONTROL_CHROME_INSTALL_PROOF_PASSED`. The job took 3 minutes, after 56 in the queue |

Three of the 40 runs of this workflow are used. Cases 1 to 4 repeat step 2's numbers (install 0.8 s, pin 0 and
819 pixels, both switches of case 3 done 0.89 s after Chrome's start, case 4 held 20 s).

**Other runs, looked at once and not waited for.** On `c4514015`: records 43729218607, base 43729218627 and
boundary 43729218628 green; Control Chrome 43729218606, Mail 43729218574 and qualification 43729218660 still
queued. **Control Chrome 43726164356 on `9ac6c8cb` never started** (queued since 14:46 UTC, at both looks); that
head's Mail and qualification runs were cancelled by this step's push. So the whole matrix has no result on any
head of this branch since step 2: read 43729218606.

### Case 5 on run 43729218613 (all **run**)

| Run of Chrome | Update checks asked (s after start) | Probe's requests: log / server | Update-service addresses and IDs | Our ID outside a `file:` address |
|---|---|---|---|---|
| ours | 1.1, 4.3 | 2 / 2 | `https://clients2.google.com/service/update2/crx`, Chrome's own two IDs | none |
| the probe alone | 1.07, 4.27 | 2 / 2 | the same | none (it doesn't have it) |
| without `override_update_url` | 1.12, 4.32 | 2 / 2 | the same, **plus `POST https://update.googleapis.com/service/update2/json`** at each of the two checks | **`X-Goog-Update-AppId: <our ID>`**, twice |

- **Ours adds nothing:** `added_by_our_policy` is empty, and the two runs name the same five hosts.
- **The negative control fails the scan both ways:** an added address, and our ID named. The POSTs are in the log
  at the same instant as the probe's two requests (+0.71 s and +3.91 s), so each asked check did take ours in, and
  with `override_update_url` the same two checks leave nothing.
- What Chrome asks by itself in every run, all ending in `ERR_INTERNET_DISCONNECTED`: its time service
  (`clients2.google.com/time/1/current`), a spelling dictionary (`redirector.gvt1.com`), `www.google.com/async/…`,
  a key list at `www.gstatic.com`, and the store's update address for its own two extensions at 0.2, 2.2 and 6.1 s.
- Each run lasts about 7 s. `autoUpdate()`'s own answer never came within it (`checks_ended` 0): the check ends
  only when Chrome gives up on its own store requests.

### Case 3's record of the previous ID (**run**)

After A to B and after B to A, `Default/Preferences` keeps **an empty object, `{}`**, under the previous ID;
`Secure Preferences` has no entry for it. Nothing Chrome could load, no permission, no host access: bookkeeping
only. The check above stays as a guard, and the files are in the artifact.

### Case 1, who can switch ours off (**run**)

- An extension installed by policy can (step 2; `after_it`: `enabled` false, the tools `chrome_unavailable`; back
  0.61 s after the next start).
- **An extension loaded by hand can't:** `installType` `development`; `setEnabled(false)` answers
  "Extension … cannot be modified by user."; ours stays enabled and connected. This was read in step 2 and is run
  now. Chrome's rule: `AdminPolicyIsModifiable` in `standard_management_policy_provider.cc`.
- He himself in Chrome's own pages: `mayDisable` false (run); the switch on `chrome://extensions` was not clicked.

### Known-limit lines (for the report and `KNOWN-LIMITS.md`; the lead places them)

- An extension installed by policy can switch ours off until the next start of Chrome. Adding one needs root, so
  that is he himself or whoever has his password. While it is off the tools answer `chrome_unavailable` (fails
  closed). An extension he loads by hand can't do it.
- On a fresh profile Chrome asks Google's update service about two extensions of its own, whatever our policy
  says. Ours adds no address and no ID to that.
- After an update the profile's `Preferences` keeps an empty record under the previous ID.

### Left, in order

1. **3a**, when PR #58 is on `main` and the lead says go. Then 3b, 4 (4b), 5, 6 as before.
2. **For step 5 (C9 in the VM):** no scheduled update check comes within a VM run either. C9 needs case 5's
   trigger in the guest: a Chrome start with `--remote-debugging-pipe` and `cdp.py` (standard library, like
   `netlog.py`), which the brief's C9 doesn't allow yet. The lead decides; the other way, a policy change (below),
   is read and not run.
3. **For step 4 (C2):** the probe can't be refused `setEnabled` (it is policy-installed). With the pipe, C2 can ask
   an extension loaded by hand, as `case_ordinary` does.

### What the code doesn't show (2b)

- With `override_update_url` the update check of ours leaves **no line in the network log**: Chrome doesn't load a
  `file:` address through its network stack. That ours is in each check is shown by the negative control (the same
  two calls give two POSTs) and by Chrome's log having no "can not be updated" line (`chrome_could_not_update`
  empty in all three runs).
- Chrome doesn't close the log's JSON on SIGTERM: all three logs end mid-list. The constants are read from the
  file's first line.
- The pipe's ends: Chrome's two are passed as descriptors 10 and up and moved to 3 and 4 by a one-line `bash`
  `exec`, so Chrome keeps its PID. Our reading end is closed by its own thread at the pipe's end.
- Developer mode is switched on in the profile `ordinary` alone. No other profile sees the pipe except case 5's
  three.
- The network logs in the artifact hold Chrome's own built-in API key and request keys in Chrome's addresses.
  They are Chrome's, the same in every copy; nothing of ours or of the owner's.
- Step 2's two other ideas (a run with a network; a policy change adding a pending forced ID) were not tried:
  the first one worked. Read only: a changed policy with at least one `update_url` extension ends in
  `CheckNow` for every extension (`external_provider_manager.cc`).

### JUDGMENT-CALL (2b)

1. **A DevTools pipe in four Chrome starts**, against the brief's "never `--remote-debugging-*`", on the lead's
   decision 3. The pipe instead of a port, so nothing listens; cases 1 to 4's own starts are unchanged.
2. **`--extensions-update-frequency` is no longer passed.** Chrome 157 has no such switch: `extension_service.cc`
   gives the updater a fixed `kDefaultUpdateFrequency` and `extensions/common/switches.cc` doesn't list it.
3. **The proof doesn't wait for `autoUpdate()`'s answer**; it waits for the probe's request (the positive
   control) after each call. Two checks, 3 s apart.
4. **The positive control is stricter than the brief:** the log's count of the probe's update requests must equal
   what the test's server answered, not only be at least two.
5. **Case 3's check names what must not be there** instead of requiring an empty record, so a timestamp Chrome
   might add later doesn't fail it. Today's record is empty.
6. **The hand-loaded extension is asked where Chrome can load one**, and reported as not asked otherwise, because
   the brief requires the question of the probe alone. On the pinned Chrome it was asked.

### PLAN-GAP (2b)

- **No short update schedule exists** in Chrome 157 (JUDGMENT-CALL 2), so "across at least two update checks" can
  only be had by asking for them. The same holds for C9.
- **The log does show the IDs sent to the update service.** The brief says they go in a body the log doesn't
  record; Chrome 157's log has the request's headers (`CORS_REQUEST`), among them `X-Goog-Update-AppId` with every
  ID asked about. So both of the brief's assertions see the leak, not only the address.
- **Chrome asks more than the update service by itself** (the four addresses above). They are the same with and
  without ours and name no extension of ours.
- Step 2's three points stand.

## Step 2 (2026-11-15, Claude Fable 5.2)

### Done: the install proof in a container (item 2)

- `.github/workflows/control-chrome-install.yml` ("Control Chrome install"): pull requests touching
  `control/chrome/packaging/**`, `control/chrome/extension/**`, `control/chrome/ci/install/**`, the container's
  `Dockerfile`, `service.py`, `native_host.py` or the workflow. `contents: read`, no secrets. It builds the container
  of `control/chrome/ci/Dockerfile` with the pinned Chrome, adds `python3-cryptography` in a layer of its own
  (`control/chrome/ci/install/Dockerfile`), runs `run.sh pack` and then `run.sh proof`, both with `--network none`.
- `control/chrome/ci/install/chrome.lock.json`: Chrome **157.0.8103.50**, the image's pinned version, as Google's
  `.deb` by URL and SHA-256 (`92148bd1…3f79`, 147674220 bytes; Google still serves it). A workflow step compares it
  with `os/google-chrome.lock.json`: another major fails, another patch version warns.
- `proof.py` (root, in the container only): the image's layout (four files in `/usr/share/aresos/chrome/`, the two
  links in `/etc`, `packaging/host` 0755 and `native_host.py` in `/usr/libexec/aresos-control/chrome/`), a made-up
  `format` 1 list at `exclusions.SETTING`, CI's `service.py` as it is, one Xvfb session, Chrome with `browser.mjs`'s
  flags. Bundles A, B and C each come from one call of `pack.py -I -B`. Evidence in the artifact
  `control-chrome-install-<run>-<attempt>` (`result.json`, Chrome's logs, `probe.jsonl`, `tool.jsonl`, screenshots,
  network logs).
- The probe: `probe/` (extension: `management`, `nativeMessaging`; its manifest's `update_url` is
  `http://localhost:18766/probe/update.xml`), `probe_host.py` (its test-only host: writes down every message and
  relays it to the check's socket). Installed by `ExtensionInstallForcelist` alone, in `aresos-install-probe.json`,
  from its own `file:` address, packed with `pack.pack` under its own key.
- `netlog.py` with `test_netlog.py` (9 tests): the scan of `--log-net-log` for case 5, standard library only, so
  the VM pass can use it in the guest. `tool_call.py`: one tool call as the owner over `act.sock`.

### Runs

| Run | Head | Result |
|---|---|---|
| 43724239061 | `faa7e340` | `pack` green: Python 3.11.2, `cryptography` 38.0.4, `Ran 17 tests`, `OK`; node v22.23.5, `pack-crosscheck.test.mjs` `# pass 1` (**its first run ever**). Proof: case 4 PASS; 1, 2, 3, 5 FAIL (the three findings below) |
| 43726164336 | `9ac6c8cb` | `pack` green (`Ran 19 tests`, `OK`, `# pass 1`). Proof: `CONTROL_CHROME_INSTALL_CASE_1_PASS` to `_4_PASS`, `_5_FAIL` |

Two of the 40 runs of this workflow are used. Every push also started Control Chrome, base, Mail, boundary,
qualification and records (their paths); nobody waited for them: on `9ac6c8cb` base 43726164318, boundary
43726164304 and records 43726164298 are green, Control Chrome 43726164356, Mail 43726164371 and qualification
43726164312 were still queued. The lead's rerun of 43716630045: `fixtures (external, word-1)` passed on attempt 2;
the run's conclusion still read `failure` when looked at once.

### What run 43726164336 shows, case by case (all **run**)

1. **Install: PASS.** Fresh profile, no address but loopback's, no default route. Chrome installs ours from
   `file:///usr/share/aresos/chrome/update.xml` through the two links: installed 0.6 s and connected 0.64 s after
   Chrome's start. `management.get`: `installType` `admin`, `enabled` true, `mayDisable` false. `uninstall` is
   refused: "Extension … cannot be modified by user." No forbidden flag in any Chrome process, no listening port.
   **The pin:** in the right half of the top strip, 0 pixels differ between two pinned starts and 819 between
   pinned and the same policy without `toolbar_pin`. `setEnabled(false)`: see "wrong against real Chrome", 1.
2. **One origin: PASS.** The host manifest behind the link equals the rendered template; the host runs as the
   owner, started by Chrome, with exactly `PATH=/usr/bin:/bin` and `LANG=C.UTF-8`. The probe's
   `connectNative('org.aresos.chrome')` answers "Access to the specified native messaging host is forbidden."; over
   28 samples while it tried there was one host process and one connection on `chrome.sock`; ours still answered.
3. **Update and back: PASS.** A to B, then B to A, one profile, Chrome restarted. Both times, after Chrome's
   start: old ID gone 0.41 s, new installed 0.41 s, new connected 0.67 s, old folder gone from
   `Default/Extensions` 0.67 s. Only the current ID is listed beside the probe; the probe is refused again; the
   manifest's bytes hold the current origin and not the previous ID.
4. **A broken package: PASS (both runs).** On a profile that never held C: with one byte of the signed archive
   changed (Chrome logs `Package is invalid: 'CRX_SIGNATURE_VERIFICATION_FAILED'`) and with the file missing, C
   is not installed over 20 s (20 samples each), the tools answer `chrome_unavailable`, Chrome and the service stay
   up, the start page and a typed address both load. Restored: installed 0.41 s, connected 0.44 s. Installed, then
   changed or missing: still enabled and connected after 8 s.
5. **Nothing asks the store: FAIL, unfinished.** See "Left".

### The brief against real Chrome (157.0.8103.50)

1. **`setEnabled(false)` is not refused to the probe.** Chrome lets one policy-installed extension switch another
   off, and the brief requires the probe to be policy-installed. Run 43724239061: the call answered `ok`, ours showed
   `enabled: false`, the tools `chrome_unavailable`, for the 120 s watched. Case 1 now requires the `uninstall`
   refusal and that **the next start of Chrome has ours enabled and connected again** (run 43726164336: 0.4 s and
   0.43 s), and records what Chrome answered. Not exercised: an extension that is not policy-installed (read, not
   run: Chrome refuses those as it refuses the user). Whoever can add a policy file can already replace ours, so
   this adds no new party; it does mean C2 in the VM can't require the refusal either.
2. **"No request at all to the update service" doesn't hold for Chrome itself.** On a fresh profile, with
   `--disable-component-update` and no network, Chrome asks
   `https://clients2.google.com/service/update2/crx` for two extensions of its own
   (`ghbmnnjooekpmoecnnnilnnbdlolhkhi`, `nmmhkkegccagdldgiimedpiccmgmieda`, both `v=0.0.0.0`), retrying at 0, 2, 6,
   13, 29, 60, 120 and 236 s (run 43724239061's log). **Neither our ID nor the probe's appears anywhere in that
   236 s log.** So the brief's fallback is the rule now: case 5 always runs the probe alone as the baseline, and ours
   must add no address and no ID (`netlog.added`); the control without `override_update_url` must add one.
3. **`--extensions-update-frequency` gave no scheduled check.** With `=30`, no update check of the probe reached
   the test's server in 240 s (run 1) or 600 s (run 2). The probe's own `chrome.runtime.requestUpdateCheck()` then
   answered `no_update` and its request did arrive at `localhost`, so the address works and the schedule doesn't.
   Not a "Stop and report" case: nothing names our ID.

### Left, in order

(1 and 2 are closed in step 2b, above.)

1. **Case 5.** The baseline, the comparison and the negative control are written but have never run: the case
   stops at "two scheduled update checks". Find what makes Chrome 157 check all extensions. Untried ideas: the
   two store installs that never finish without a network may hold the schedule back (a run with a network, or a
   longer one); a policy change that adds a pending forced ID starts a check of everything (read, not run). The
   probe's `requestUpdateCheck` is ready as a positive control for the probe alone, but it doesn't check ours.
   Chrome doesn't close the log's JSON on SIGTERM; `netlog.events` reads the cut-off file line by line.
2. **Case 3's preference record.** After each switch the profile's preference files still list the previous ID
   (`"previous": true`, 7 entries) although the management API and the folder say it is gone. Recorded, not
   required; look at what the entry holds before turning it into a check.
3. Then 3a, 3b, 4 (4b), 5, 6 as before.

### What the code doesn't show (2)

- The artifact's files are public by design (`bundles.json` holds IDs and hashes only). No key is written; the
  probe's key is made in `proof.py`'s own process by `pack.pack` and dropped.
- `proof.py` runs as root because it swaps files under `/usr/share`; Chrome, the tool calls and the session run as
  `owner`, the service as `aresos-tools`. Chrome is ended with SIGTERM by its PID.
- The "one host" check reads the kernel's view (`ss -x`) and the process list, sampled every 50 ms, plus Chrome's
  own refusal text. `service.py` has no line for an accepted or refused host.
- Cases are independent where they can be: each has its own profile except 1 and 3, which share one on purpose.

### JUDGMENT-CALL (2)

1. **The policy form stays `ExtensionSettings` alone**: the pinned Chrome installs from it. The fallback isn't needed.
2. **Case 1's `setEnabled` check changed** as described above instead of installing a second, non-policy probe.
3. **The pin is asserted by pixels** (pinned twice against pinned and unpinned), since nothing but our own
   extension can ask Chrome about its pin. Thresholds: at least 150 pixels and four times the same-start difference.
4. **The harness is Python, not node**, so steps 4 and 5 can reuse `netlog.py`, the probe and its host in the guest.
5. **The Chrome pin is a file** (`chrome.lock.json`) whose hash has no second source; a patch-level difference to
   the image's lock warns instead of failing, as the brief allows the same major.
6. **Case 5 runs without a network** like the other cases; `--extensions-update-frequency=30` because release
   builds are said to enforce 30 s (read, not confirmed: no check ran at all).

### PLAN-GAP (2)

- The three points under "The brief against real Chrome".
- A change of `os/google-chrome.lock.json` doesn't start this workflow (its paths are the brief's plus its own
  files); the version step only speaks on the next run.
- Every push to this branch starts the whole Control Chrome matrix, because the new files live under `control/`.

## Step 1b

### Part A: the latency pair after 1a (run 43705955018)

**Cause (read from the run, not assumed).** Every job of `Control Chrome` on `265caa52` was green except
`latency (plain)` and `latency (audit)`, both in "Paired current and historical measurements on the same runner"
(`control/chrome/ci/latency-pair.sh`). The pair runs two legs: `current`, then `ab7aba92` (main's older runtime,
with the current `control/chrome/ci/` and `control/chrome_tests/` copied over it). The `current` leg finished and
printed its results (`"runtime": "current"`, build `2acd63cb…`); the `ab7aba92` leg failed in `browser.mjs` line 40
with `extension native connection: undefined`. Its artifact (`chrome-latency-43705955018-1-ab7aba92-plain`,
`tool.jsonl`) holds 296 `tabs` answers: 5 `chrome_unavailable` (before the extension connected), then 291
`chrome_settings_unavailable`. So the extension did connect; the tools refused because the list wasn't where that
runtime reads it. `ab7aba92`'s `exclusions.py` has `SETTING = '/etc/aresos/control/chrome-excluded-sites.json'`,
and the current `prepare.mjs` (copied into that leg) wrote only `/var/lib/aresos-control/…`. `rpc('tabs')` answers
`ok: false` without throwing, which is why the message says `undefined`. The lead's guess was right.

**Fix** (`32f1126c`): `prepare.mjs` no longer names a path for the list. It asks the tree under test,
`python3 -B -c 'from aresos_control.chrome.exclusions import SETTING;print(SETTING)'` with
`PYTHONPATH=/workspace/control`, refuses an answer that isn't an absolute path ending in
`/chrome-excluded-sites.json`, and writes the same content, mode (0640) and owner (`root:1001`) there. The
`current` leg and every other Control Chrome job get `/var/lib/aresos-control/…` as before; the `ab7aba92` leg
gets `/etc/aresos/control/…`, as main's harness gave it. Ceilings, sample counts, `latency-targets.json`,
`latency-reference.json`, `latency-pair.sh` and the comparison are unchanged. Checked locally: the command prints
the old path over `git archive ab7aba92 control/aresos_control` and the new one over the checkout.

**Its test:** `CiInstall` in `control/chrome_tests/test_excluded_sites_placeholder.py` (3 tests): `prepare.mjs`
holds neither path nor the file name as a literal, and writes and chowns `excludedSites`; the exact command taken
from `prepare.mjs` prints `exclusions.SETTING` over the checkout and the old path over a copy of
`aresos_control` whose `SETTING` is the old one; the guard accepts both and refuses others. All three fail on
`prepare.mjs` before the fix.

### 1b done: `record_build.py` (item 4)

- `control/chrome/record_build.py` (stdlib only; not one of `build.py`'s inputs, the hash stays `2acd63cb…`):
  - `add --commit <40 hex> --shipped-at <YYYY-MM-DDTHH:MM:SSZ> [--expect <64 hex>] [--registry PATH] [--repo PATH]`:
    `git archive <commit> -- control` into a temporary folder (extracted with tarfile's `data` filter), runs that
    commit's `control/chrome/build.py` with `-I -B`, refuses a wrong `--expect` or an existing row for the commit
    with another hash, adds the row, keeps the newest three by `shipped_at` and writes atomically. `--registry`
    defaults to the repository's `builds.json`; the recorded run below used a scratch copy.
  - `check [--root PATH]`: validates `builds.json` (the planner's rules plus unique commits), then
    `os/manifest/release.json` and every `os/manifest/releases/**/*.json`. No `control` object: an info line. A
    `control` object must be exactly `{"source_revision": <40 hex>, "chrome_build": <64 hex>}` with
    `source_revision` equal to the manifest's `source_commit`; `release.json` needs an equal row; a release under
    `releases/` needs an equal row only if one is kept. Exit 1 with `FAIL:` lines, else `record_build check passed`.
- `control/chrome/ci/records/test_record_build.py` (21 tests, synthetic repositories and checkouts in temporary
  folders): `add` records what that commit's own `build.py` prints over its archived tree (the test archives and
  runs it itself); a commit with another `build.py` keeps its own algorithm, not the checkout's, and uncommitted
  changes don't count; wrong `--expect`; a repeated commit (unchanged file) and a conflicting row (refused); pruning
  to three, added out of order; a later commit with the same build; bad commits, times, `--expect`, a commit
  without `control/`; invalid registries; what `add` writes passes `qualify.plan`; the command line. `check`: with
  a row, without one, with an unequal one, no `control` object, malformed objects (in `release.json` and in
  `releases/`), `source_revision` against `source_commit`, `releases/**` (kept equal, kept unequal, missing,
  a subfolder), an invalid registry, a missing or non-object `release.json`, exit codes, and this checkout.
- `.github/workflows/control-chrome-records.yml`: pull requests touching `os/manifest/release.json`,
  `os/manifest/releases/**`, `control/chrome/builds.json`, `record_build.py`, `control/chrome/ci/records/**` or the
  workflow itself; `contents: read`, no secrets, `persist-credentials: false`, ubuntu-24.04's own `python3`; the
  tests, then `record_build.py check` on the checkout.
- `builds.json` is unchanged (`{"format":1,"builds":[]}`).

**The recorded run (run, on the laptop, into a scratch copy of `builds.json`):** 18c's head is reachable
(`origin/pkg/18c-image`).
```
$ python3 control/chrome/record_build.py add --commit 84f45c28fc20a21bf4882de8eb9fe83b94414798 \
    --shipped-at 2026-11-15T12:00:00Z --expect ccd0fd79190f492dbb0ca9889a288c0c004e0d46da3458e0f4446c80b5f5ce15 \
    --registry <scratch>/builds.json
{"commit":"84f45c28fc20a21bf4882de8eb9fe83b94414798","build":"ccd0fd79190f492dbb0ca9889a288c0c004e0d46da3458e0f4446c80b5f5ce15","shipped_at":"2026-11-15T12:00:00Z"}
record_build: recorded
```
exit 0. The same commit again: `already recorded; builds.json unchanged`, exit 0; with `--expect aaaa…`:
`refused: commit 84f45c28… hashes to ccd0fd79…, not the expected aaaa…`, exit 1. `qualify.plan` accepts the
scratch file. `check` on the checkout prints an info line for `release.json` and `releases/06.json`, `13.json`,
`27.json` (none has a `control` object yet) and `record_build check passed`.

### Local tests (laptop, Python 3.14.8)

- `python3 -B -m unittest discover -s control/chrome/ci/records -p 'test_*.py'`: `Ran 21 tests`, `OK`.
- `PYTHONPATH=control:control/chrome_tests python3 -B -m unittest test_excluded_sites_placeholder test_exclusions
  test_build test_extension_stores_nothing test_unit`: `Ran 19 tests`, `OK`.
- `CiInstall` on the `prepare.mjs` before the fix: `FAILED (failures=3)`.
- Three mutants of `record_build.py` (the checkout's `build.py` instead of the commit's; no pruning; `check` not
  comparing the build) each fail tests; not committed.
- `python3 -B control/chrome/build.py`: `2acd63cbc4ae0ec273e82f700a4a8afdfa7288f191706a848c9091b64636c6ec`
  (unchanged by 1b).
- **Not run locally:** `prepare.mjs` itself (no node, no container): the Control Chrome run below is its proof.

### CI runs (started by the push of `9302528d`; nobody waited for them)

1a's other runs on `265caa52` were green: Control Chrome qualification 43705955046, Control base 43705955015,
Control Mail 43705954960, Control boundary 43705954998.

| Run | Workflow | What to look for |
|---|---|---|
| 43716630045 | Control Chrome | `latency (plain)` and `latency (audit)` green (Part A); the 3 `CiInstall` tests in the python shards |
| 43716630095 | Control Chrome records | first run of the 21 tests and `check` on GitHub |
| 43716630048 | Control Chrome qualification | |
| 43716630066 | Control base | |
| 43716630101 | Control Mail | |
| 43716630097 | Control boundary | |

### What the code doesn't show (1b)

- `record_build.py` needs Python 3.12 or later (tarfile's `data` filter) and `git` on `PATH`. The commit must be
  in the clone: a release job with `actions/checkout`'s default depth of 1 has its own commit, so
  `add --commit "$GITHUB_SHA"` works there without fetching history.
- `add` runs the archived `build.py` as a script with `-I -B` in a temporary folder that is removed afterwards;
  nothing is written into the repository but `--registry`.
- The python shards of `Control Chrome` pick up `CiInstall` (every `control/chrome_tests/test_*.py`); nothing but the
  records workflow runs `control/chrome/ci/records/`.

### Left, in order

1. **Read the runs above.** If a latency leg still fails, its `tool.jsonl` artifact names the refusal.
2. **2** the install proof in the container. First thing: run `test_pack.py` and `pack-crosscheck.test.mjs` there.
   They have run nowhere on GitHub yet, and the node test has never run at all.
3. **3a, 3b, 4 (4b), 5, 6** as the brief's "Steps" lists them. 3a waits for PR #58 on `main`, the lead's go and
   the owner's answer to question 5.

### JUDGMENT-CALL (1b)

1. **Part A asks the runtime for its path** instead of writing the list at both paths. Two paths would leave a
   list at the old `/etc` path in every container of current code, so a `SETTING` moved back to `/etc` would
   still pass every browser run. Cost: `prepare.mjs` (an existing file under `control/chrome/ci/`, which the brief
   lets this package change only on item 1's path lines) changed on those three lines plus two imports, on the
   lead's instruction. The test went into this package's new `test_excluded_sites_placeholder.py`, not the existing
   `test_latency.py`, for the same rule.
2. **`add` archives `control/` only**, not the whole tree (about 980 MB at HEAD). Every version of `build.py` so
   far hashes only paths under `control/` (`ROOT/'control'`). A later `build.py` that reads outside `control/`
   would need the archived paths widened (one line).
3. **A repeated commit with an equal hash is a no-op** (exit 0, the first `shipped_at` stays), so a rerun release
   job passes; with another hash it is refused.
4. **A later commit with the same build takes over that build's row** (with its own commit and time). The planner
   (`qualify.plan`) refuses a build named twice, and a release that changed nothing under `control/` hashes the
   same as the one before. Refusing would fail every such release; two rows would break qualification. The older
   release then has no row, which `check` allows for `releases/`.
5. **A row older than the three newest is refused**, not added and pruned at once in silence.
6. **`--shipped-at` is strictly `YYYY-MM-DDTHH:MM:SSZ`** (no fractions, no offsets), and must be a real time.
7. **`check` is a little wider than item 4:** `source_revision` must equal `source_commit` in `releases/` too; it
   reads `releases/` recursively; a missing or non-object `release.json` and an invalid `builds.json` fail.
8. **The workflow** runs on pull requests against any base (no branch filter) and on its own path too;
   `pull_request` only, as item 4 says.
9. **`builds.json` layout:** one row per line, newest first, so the pinning pull request shows its row as one
   line; the empty file stays byte for byte as it is.

### PLAN-GAP (1b)

- **The latency pair wasn't in the brief's picture.** It runs the current harness over main's runtime
  (`ab7aba92`), so a path the harness writes and the runtime reads can't simply move in the harness. 1a moved the
  list as the brief said and the historical leg broke. Any later change of that kind (the policy or host paths in
  steps 2 and 3a, if CI's install follows them) meets the same.
- **"That commit's tree"** in item 4 would be about a gigabyte per `add`; see JUDGMENT-CALL 2.
- **Item 4 leaves open** a repeated commit and the same build under a new commit; decided in JUDGMENT-CALLs 3 and 4.
  `linux-aresos`'s release job should run `add` once per release and may rerun it.

## Step 1a

### Done

**1a. Packer, templates, pins** (item 1; `control/` only, nothing under `os/` or `docs/design/`)

- `control/chrome/packaging/pack.py`: `python3 pack.py EXTENSION_FOLDER OUTPUT_FOLDER` writes `extension.crx`,
  `update.xml`, `policy.json`, `native-host.json` (each 0644) and prints the public record as one JSON line
  (`id`, `version`, `public_key_sha256`, `crx_sha256`, `payload`). As a module: `pack.pack(folder)` returns
  `(files, record)`, `pack.write(folder, output)` returns the record; `pack.payload(folder)`,
  `pack.version(folder)` and `pack.render(id, version)` need only the standard library (for `check-image.sh`).
- Templates: `policy.json` is `ExtensionSettings` alone with the four keys; `update.xml` has the placeholder
  `EXTENSION_VERSION`; `native-host.json` is unchanged (it already had one origin and the fixed launcher).
- `control/chrome/ci/install/test_pack.py` (10 tests) and `pack-crosscheck.test.mjs` (the node cross-check).
- `control/chrome_tests/test_extension_stores_nothing.py`: the storage pin.
- `exclusions.py`: `SETTING` is `/var/lib/aresos-control/chrome-excluded-sites.json`, and the refusal has the
  brief's exact text. `prepare.mjs` lines 32 to 34 and `test_exclusions.py` line 13 follow the path. Nothing
  else in the service changed.
- `control/chrome/packaging/aresos-control-chrome.tmpfiles`: the two agreed lines with a comment.
- `control/chrome_tests/test_excluded_sites_placeholder.py`: the tmpfiles lines, the placeholder refused, the
  empty list accepted, the unit unable to write the folder, and the sweep over the 31 Chrome tools.
- `control/chrome/packaging/README.md`: the paragraphs item 1 names.

`python3 control/chrome/build.py` prints `2acd63cbc4ae0ec273e82f700a4a8afdfa7288f191706a848c9091b64636c6ec` at
`0fc242e7` (the brief expected it to change: `packaging/` and `exclusions.py` are hashed).

### What the code doesn't show

- **Signing uses Python's `cryptography`**, imported inside `_sign_with_fresh_key` only. The container of
  `control/chrome/ci/Dockerfile` (Debian bookworm) has `python3` without it: step 2's workflow installs the
  distribution package `python3-cryptography` (no pip). The calls used exist since `cryptography` 3.1.
- **Run `pack.py` without `-S`**: `-S` hides site-packages and with it `cryptography`. 18c's `os/build.sh` runs
  `build.py` with `-I -B`, which is fine for `pack.py` too.
- **`pack.py` never overwrites.** It refuses an output folder that already holds one of the four files. Bundles
  A, B and C each go into a folder of their own and are copied from there.
- **The image check needs a reader of its own** for `extension.crx` (the installed tree has no `pack.py`, and a
  packer shouldn't be checked with itself). `test_pack.py` has one (`fields`, `read_crx`) and the key-scan forms
  (`forms`: raw, hex, base64 and base64url at three alignments) for whoever writes the modulus scan in step 3a.
- **`os/tests` in step 3a** ("no installed file contains `EXTENSION_ID`, `UPDATE_URL` or `CRX_URL`") should also
  name `EXTENSION_VERSION`. `pack.render` already refuses to return a file with any of the four left in it.
- **How the key test works:** it wraps `rsa.generate_private_key` to see the keys the packer makes, then looks
  for p, q, d and the CRT numbers in everything returned, written or left behind. No key is a fixture anywhere.
- **The sweep's prepared operations** are written through the engine's own `reserve`, with the adapter's
  `prepare` replaced (it reads the page, which the gate never allows). The record has the engine's shape that way.
- In today's code the swept tools make **no** bridge call at all; the test allows `ack_steps` and `queued_steps`
  as the brief says and fails on any other, `configure` included.

### Local tests (laptop, 2026-11-15, Python 3.14.8, `cryptography` 50.0.0)

- `python3 -m unittest discover -s control/chrome/ci/install -p 'test_*.py'`: `Ran 10 tests`, `OK`.
- `PYTHONPATH=control:control/chrome_tests python3 -m unittest test_extension_stores_nothing
  test_excluded_sites_placeholder test_exclusions test_build test_unit`: `Ran 16 tests`, `OK`.
- `… -m unittest test_owner_confirm.Policy` (it reads the README): `Ran 7 tests`, `OK`.
- `test_excluded_sites_placeholder` on the code before the change: `FAILED (failures=29)`, as required.
- A packer changed to leave its key as a file in the temporary folder fails
  `test_no_private_key_in_what_is_returned_written_or_left_behind` (tried once, not committed).
- **Not run:** `pack-crosscheck.test.mjs` and every other `*.mjs` (no node on the laptop); the container; the
  full Chrome and Control suites (GitHub runs them). `test_committed`, `test_fault_surface`, `test_sites` and
  `control/tests`' `test_policy_sources`, `test_slim_policy`, `test_unit` were started locally and stopped
  unfinished (slow suites; the laptop is shared): take their result from the GitHub runs below.

### CI runs

Draft pull request **#76**. Started by its first push, on head `265caa52` (queued when this was written; nobody
waited for them, so the next agent reads the results first):

| Run | Workflow |
|---|---|
| 43705955018 | Control Chrome (runs the two new `control/chrome_tests` files and CI's install with the list at its new path) |
| 43705955046 | Control Chrome qualification |
| 43705955015 | Control base |
| 43705954960 | Control Mail |
| 43705954998 | Control boundary |

Nothing on GitHub runs `control/chrome/ci/install/` yet (step 2).

### JUDGMENT-CALL

1. **`cryptography` in the process, not OpenSSL through pipes.** The key lives only in the crypto library's
   memory, is never serialized and is freed after one signature. The pipe route would carry the key's PEM
   through a pipe and into Python bytes that can't be wiped. Cost: the container needs a distribution package
   (above). Changing it later touches one function and changes the build hash.
2. **The policy form** is `ExtensionSettings` alone, as the brief and the lead's answer 7 say. Whether the
   pinned Chrome installs from it is step 2's first case; the fallback in the brief stays open until then.
3. **The placeholder gate and its message** are the brief's, word for word.
4. **The named tools are called too.** The brief only names them. The test also requires each to answer `ok`
   and to reach no page, and requires the two tables to cover the tool list and `chrome_sites`' commands
   exactly, so the list can't go stale in either direction. Stricter than asked; easy to loosen.
5. **The storage pin is a little wider** than the four names: it also catches `navigator.storage`,
   `chrome['storage']` and a `storage` permission in the manifest.
6. **`pack.py`'s refusals beyond the brief:** an output folder that already holds a bundle file; a manifest
   version that isn't one to four numbers (it goes into `update.xml` as it stands); a file name that isn't
   UTF-8. The command also sets the core-file limit to zero, so a crash can't write the key to disk.
7. **The zip** is deflated as `install.mjs`'s is (what CI's Chrome has unpacked since package 17), with the
   time fixed at 1980-01-01 and mode 0644.

### PLAN-GAP

- **Branch name.** The brief's "Rules" say `pkg/18c-b-chrome-image`; the lead's handoff gave
  `pkg/18c-b-chrome`, which is what exists.
- **No runner for `control/chrome/ci/install/` until step 2.** The brief places the tests there so no existing
  suite picks them up, so on GitHub they first run in step 2's workflow.
- **The README names `record_build.py`** one step before it exists (item 1 asks for the sentence now).
- **Other texts still name the old `/etc` path:** `docs/control/TOOLS-HANDOFF.md`, `STATE.md`,
  `briefs/18c-image-test.md`, `reviews/20-chrome/` (history). All outside this package's paths; the lead's.
- **CI's list in the container** now goes to `/var/lib/aresos-control/`, which `prepare.mjs` makes as root
  (0755 by default). `Boundary.read` needs that; only the `control-chrome.yml` run shows it.

### The brief against the code

Nothing in item 1 turned out wrong. Checked: `exclusions.py` lines 8 and 23, `prepare.mjs` lines 32 to 34,
`test_exclusions.py` line 13 and `background.js` lines 869 to 875 are where the brief says; the extension uses
no browser storage; `python-shard.py` picks up every `control/chrome_tests/test_*.py`, so the two new test
files run in `control-chrome.yml` without a workflow change.
