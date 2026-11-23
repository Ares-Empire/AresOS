# Review 2: 334a after review fixes round 1

**Verdict:** CHANGES-NEEDED

## Must fix

1. **Make the release isolation checks fail closed.** `.github/workflows/os-image.yml:385`, `:506`, `:619`, and `:733` chain absence checks with `&&` inside `bash -ec`. Bash ignores `errexit` failures before the final command in an `&&` list. I ran the extracted checks with one path marked present at a time. All four blocks exited zero with the existing CI executable path, the bench directory, the bench unit, or its enablement path present. This weakens a guard on images that can be published. Put each assertion on its own line or give each chain an explicit `|| exit 1`. Add a regression that executes the shell block with a planted path. The current test only checks for matching text.

## Should fix

- **Cover valid rehearsal inputs and failed-step behavior in the condition tests.** In `os/tests/test_bench_dispatch.py:66`, the only rehearsal value tested is `release-28`, which other predicates already exclude. Removing the rehearsal job’s bench guard still passes the test and allows bench plus `probe` on `pkg/16-staged-release`. At `:127`, adding `success()` to the upload condition also passes the test because the evaluator treats `success()` as true. Test rehearsal values valid on each guarded branch and model Actions status functions so a failed VM can still upload evidence that passed the scan.

## Known limits

- A stray manual bench dispatch remains in a guarded ref’s history. R29 charges unknown titles as rejected runs. Older guards can stop on them. A mixed bench and rehearsal selection can also take the rehearsal title and consume its allowance. Any deletion remains the OS lead’s decision.
- The screenshot gate scans file bytes. It has no OCR. Repeated dispatches of the same ref and SHA share one pending slot.

## Checked

- Traced the release contexts, image tags, and job conditions. `os/.containerignore` excludes the bench sources, tests, and bytecode while preserving the audit script. The bench build scans the plain image’s raw layers and requires its planted-file case to fail. Package 13, release and dry-run jobs, rehearsal, and switch all exclude bench at the workflow level.
- Confirmed that `exec` exports only an exit code, journal text is screened before virtio, and the evidence gate checks regular files, size, and token-shaped bytes before upload. QEMU and `qemu-img` use an environment allow-list. QEMU discards serial output. The health probe authenticates as a named view and calls the real helper’s `list_apps`. The regression test uses the real server and checks that the original desktop connection survives.
- Confirmed that both ledger checks derive managed refs from guard data and that the job guard runs before image tools. The R29 jobs and `os/ci/rehearsal_guard.py` have no diff. The pending workflow hash matches the checkout and `check-build.sh` is outside the active bindings. The bench-only German keymap and ref-plus-SHA concurrency are sound choices.
- Re-scanned both saved artifacts and checked their commit, image and guest revisions, and script digest. The clean run recorded two distinct offline boots and produced the first-start screenshot. The negative run passed image checks and failed at helper health. GitHub job records also confirmed the checks-only pass. [Clean run](https://github.com/Ares-Empire/AresOS/actions/runs/45086521725) · [Negative run](https://github.com/Ares-Empire/AresOS/actions/runs/45086546954) · [Checks-only run](https://github.com/Ares-Empire/AresOS/actions/runs/45089740931)
- Ran all five permitted test modules individually. Nine tests passed and 14 stopped at fixture creation on the read-only filesystem. Shell syntax and `git diff --check` passed.
