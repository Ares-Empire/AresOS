# Review 3: 334a after review fixes round 2

**Verdict:** SAFE

## Must fix

None.

## Should fix

None.

## Known limits

- A manual bench dispatch on a ledger-managed ref still creates a history entry. R29 charges unknown titles against its budget, older guards can stop on them, and a mixed bench and rehearsal dispatch can consume a rehearsal allowance.
- The evidence scanner checks PNG bytes and has no OCR. Its bare-token rule also rejects some harmless values. I confirmed that a valid 32-character script basename can trigger refusal through `run.json`.
- Repeated dispatches of the same ref and SHA share one pending slot. A newer pending run can replace an older one. [GitHub Actions concurrency](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency)

## Checked

- **Release safety.** The bench uses a separate local tag and build context. `os/.containerignore` excludes the bench sources, tests, and test bytecode while preserving `os/tests/audit.py`. The hosted scan checked 134 raw layers and refused the file hidden by a later layer. All four release isolation blocks passed clean and rejected 64 simulated present-path or dangling-link cases. [Hosted bench run](https://github.com/Ares-Empire/AresOS/actions/runs/45094038830)
- **Dispatch and workflow effects.** The job conditions exclude bench from package 13 publishing, the other release and dry-run jobs, rehearsal, and switch. The client and the pre-build job guard use ledger data. Removing the rehearsal guard in memory made the package 16 probe regression fail. The diff leaves `os/ci/rehearsal_guard.py` and the R29 jobs untouched. The pending workflow rebind row matches the checkout SHA-256.
- **Credentials and evidence.** `exec` exports only an exit code, journal text is screened inside the guest, QEMU gets an explicit environment allow-list, and serial output is discarded. The upload requires a successful regular-file, size, and token scan. Adding `success()` in memory broke the failed-VM upload regression, and the existing negative run confirms that scanned evidence uploaded after the VM failed. [GitHub Actions status functions](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions#status-check-functions) · [Negative run](https://github.com/Ares-Empire/AresOS/actions/runs/45086546954)
- **Health and reboot.** I exercised the real helper and probe in memory. The named view authenticated and called `list_apps`, a bad token was refused, and the existing desktop connection survived. The negative commit still ran `--list`, passed hosted image checks, and failed at helper health. The saved clean artifact shows first-start setup and two distinct offline boot IDs. Its dispatched SHA, image and guest revisions, and committed script digest agree. [Clean run](https://github.com/Ares-Empire/AresOS/actions/runs/45094038830) · [Negative run](https://github.com/Ares-Empire/AresOS/actions/runs/45086546954)
- **Judgment calls.** The German keymap supplies the launcher’s required layout on the disposable disk and matches the installed profile. Ref-plus-SHA concurrency lets clean and negative commits run independently while existing modes retain their original groups.
- **Tests.** The five bench modules exercise production code and actual workflow conditions. I ran them individually. Nine tests passed locally, and 15 could not create fixtures on the read-only filesystem. Shell syntax and `git diff --check` passed. The existing hosted checks-only run passed 2,589 tests with 24 skips. This review started no workflow, VM, container, or sudo command. [Hosted checks-only run](https://github.com/Ares-Empire/AresOS/actions/runs/45094038198)
