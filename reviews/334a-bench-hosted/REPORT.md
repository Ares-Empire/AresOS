# Package 334a — Hosted bench

## Done

- `os/ci/bench/` builds a disposable, passwordless guest from the checked-out image and runs one JSON script over virtio. The guest boots without a NIC. The root agent uses `runuser` for desktop commands and the authenticated `list_apps` probe. That probe returns a boolean to the host and keeps the launch credentials in the guest. QMP takes screenshots and the runner checks the boot ID across a reboot.
- `os/ci/check-build.sh` and `.github/workflows/os-image.yml` accept `check_build=bench` and a script selected from the dispatched commit. The bench has its own local image tag. Release, published-image switch, rehearsal and checks-only jobs exclude bench dispatches. The bench upload requires the evidence gate, and raw VM output stays out of retained job logs.
- `os/.containerignore` excludes the bench regressions from the release build context alongside the existing CI source exclusion. The raw-layer scan checks all of the plain image's layers, including paths hidden from its final filesystem. It also refuses a planted file removed by a later layer. The release jobs retain their own filesystem isolation checks.
- `os/tests/test_bench_*.py` covers the parser, dispatch exclusivity, the evidence boundary and the release-layer scan. The workflow changes are recorded in the pending source binding.

## Verified

| Bench dispatch | Result | Dispatch elapsed | VM elapsed | Evidence bytes |
| --- | --- | ---: | ---: | ---: |
| [45072067558](https://github.com/Ares-Empire/AresOS/actions/runs/45072067558) | Superseded after preflight | 14m47s | | |
| [45072177942](https://github.com/Ares-Empire/AresOS/actions/runs/45072177942) | Superseded in queue | 12m02s | | |
| [45073280329](https://github.com/Ares-Empire/AresOS/actions/runs/45073280329) | Stopped at active-session verification | 23m57s | 185.3s | 616 |
| [45073304117](https://github.com/Ares-Empire/AresOS/actions/runs/45073304117) | Stopped at active-session verification | 23m41s | 183.7s | 616 |
| [45075939129](https://github.com/Ares-Empire/AresOS/actions/runs/45075939129) | Active-session failure with startup diagnostics | 50m27s | 204.3s | 8,499 |
| [45076044610](https://github.com/Ares-Empire/AresOS/actions/runs/45076044610) | Active-session failure with startup diagnostics | 53m09s | 195.8s | 7,433 |
| [45080827587](https://github.com/Ares-Empire/AresOS/actions/runs/45080827587) | **Pass**, all six steps | 21m48s | 63.3s | 65,682 |
| [45080853329](https://github.com/Ares-Empire/AresOS/actions/runs/45080853329) | **Expected failure**, step 2 helper health | 19m32s | 72.9s | 873 |

- Ran `gh workflow run "OS image" --ref pkg/334a-bench-hosted -f check_build=bench -f bench_script=reviews/334a-bench-hosted/bench/session-health.json` and watched the runs with `gh run watch <id> --exit-status --interval 60`. Evidence sizes in the table are the sum of the uploaded files before compression.
- The clean bench run reported an active greetd session with labwc in its scope on both boots, with only loopback. The authenticated helper probe passed on both boots. The boot ID changed from `afeae23a-0de1-4007-9d8c-2b3d1c521890` to `17be4406-7fcd-458b-8a67-2d58f680c0c0`. I inspected `003.png` and confirmed it shows the first-start AresOS session. [Clean evidence](https://github.com/Ares-Empire/AresOS/actions/runs/45080827587/artifacts/14777414499)
- The broken-helper run printed `IMAGE_CHECKS_PASSED` after running the helper import and `--list` checks. It then printed `PASS 001 wait` and `FAIL 002 expect (helper_health did not pass)`. The temporary change to `list_apps` was reverted in `f29c12f3`. [Broken-helper evidence](https://github.com/Ares-Empire/AresOS/actions/runs/45080853329/artifacts/14778250805)
- I downloaded both artifacts and matched `run.json` to each dispatch SHA, the image label, each guest's installed revision and the committed script's SHA-256. Both runs scanned 134 plain-image layers and printed `BENCH_PLANTED_LAYER_REFUSED`. The hosted evidence preflight refused oversize files and a planted token.
- Ran `python3 -B -m unittest discover -s os/tests -p 'test_bench_<module>.py' -v` individually for `script` (3), `evidence` (5), `dispatch` (4), and `release_layers` (2). Each printed `OK`. Ran `bash -n` on each changed shell script and `git diff --check` successfully.
- Ran `gh workflow run "OS image" --ref pkg/334a-bench-hosted -f checks_only=true`. Run [45073493119](https://github.com/Ares-Empire/AresOS/actions/runs/45073493119) initially failed because the shell assertion checker flagged the new KVM permission guard. After reordering the equivalent condition, run [45077212411](https://github.com/Ares-Empire/AresOS/actions/runs/45077212411) printed `Ran 2579 tests in 2231.436s`, `OK (skipped=24)` and passed the live system manager check. The final restored head `f29c12f3` passed in [45080899317](https://github.com/Ares-Empire/AresOS/actions/runs/45080899317). Its regression job took 46m39s and printed `Ran 2579 tests in 2754.106s`, `OK (skipped=24)`, and `Live hosted system manager passed: 439 unit files, 480 unit names`.
- Hosted [Mod build 45072215651](https://github.com/Ares-Empire/AresOS/actions/runs/45072215651) built and ran the server game tests twice, and its JAR comparison passed. No files over 500 MB were left under `.work/`.

## Not verified

- Hosted Mod CI exercised the server tests. Minecraft client game tests, Prism sign-in, physical hardware and the installer, switch, and rollback routes are outside this package's hosted acceptance.

## JUDGMENT-CALL

- The bench layers the installed German keyboard profile onto its blank disk. The earlier runs reached greetd's PAM session, then fell back to the text login. The real desktop launcher requires an X11 layout, which the installer supplies on the normal installation path. Reusing the CI overlay would also supply a layout, but would bring its US map, fixtures and debug settings. The bench-only profile is two writes in its Containerfile.
- Bench concurrency is keyed to the ref and dispatched SHA. A commit-specific group lets the clean and temporary negative commits run together, while repeated dispatches of one commit share a group. The alternatives were serializing with every other OS run or giving every dispatch a group. Existing OS modes keep their groups. Changing this later is one workflow expression.

## PLAN-GAP

- The existing `ci/` build exclusion covered the agent and host runner. The new hosted regressions live under `os/tests/` and needed their own exclusion because the package stage copies the OS context into a raw layer.

## Known limits

- Each dispatch plays one script with the offline guest. The acceptance probe covers the first-start desktop. Repeated dispatches of the same ref and SHA share one pending slot.
- The evidence gate scans screenshot bytes for token-shaped strings. It has no OCR, so visible text can escape the scan.
- A stray manual bench dispatch remains in a guarded ref's history. R29 counts an unknown title as rejected and charges its minutes against the remaining budget. Older guards can stop on such a run. A mixed bench and rehearsal dispatch can take the rehearsal title and use its allowance. Deleting a run removes evidence and is a decision for the OS lead.
- Normal OS checks retain the suite's existing environment-dependent skips for graphical and namespace harnesses.

## Open questions

- The next rehearsal will incorporate the pending source binding. The later bench packages cover laptop operation and other network levels.

## Review fixes, round 1

1. `exec` still runs as the desktop user. The agent discards stdout and stderr in the guest and sends only the exit code. The evidence gate refuses raw `exec` files and detects bare and `ARESOS_LAUNCH_NONCE=` credentials. The agent checks journal text before it crosses virtio, including matches against live credentials embedded in longer text.
2. The bench layer generates a fresh view token at session startup and gives it to the real helper through the desktop supervisor's environment. Health uses the named `bench-health` view and sends `list_apps` over `aresos-shell/1.2`. A test with the real helper server rejects an incorrect token, passes with the provisioned token and then reads from the original desktop connection.
3. The hosted client checks the release ledger in the local checkout and reads the pushed branch's public ledger without credentials before submission. The workflow independently checks the dispatched checkout's ledger before starting image work. The package 331 entry is already present on its release branch, so the client covers it before that ledger reaches main.
4. The check-build job applies the release, dry-run, rehearsal, checks-only and switch exclusions to bench. Bench also requires an empty probe-run input and a false full-model flag.
5. The dispatch tests evaluate the job conditions with conflicting inputs and exercise the workflow's actual guard command. They evaluate the scan and upload conditions on the steps that handle `evidence/bench/`, including failure, skip and cancellation states.
6. `qemu-img` and QEMU receive `PATH` and `LC_ALL` from a fixed allow-list. A subprocess test supplies synthetic runner variables and checks the environment both commands receive.

### Verified

- Ran `python3 -B -m unittest discover -s os/tests -p 'test_bench_<module>.py'` one module at a time. The agent (4), dispatch (7), evidence (7) and script (3) modules each printed `OK`. `bash -n os/ci/bench/build.sh` and `git diff --check` exited zero.
- The client command `python3 -B os/ci/bench/dispatch.py --ref pkg/331-release-29 reviews/334a-bench-hosted/bench/session-health.json` printed `Bench dispatch refused on a ledger-managed ref` and exited 1 before submission.
- Submitted the hosted benches with `python3 -B os/ci/bench/dispatch.py --ref pkg/334a-bench-hosted reviews/334a-bench-hosted/bench/session-health.json`. Submitted checks-only with `gh workflow run 'OS image' --ref pkg/334a-bench-hosted -f checks_only=true`. Watched each with `gh run watch <id> --exit-status --interval 60`.

| Bench dispatch | Dispatched commit | Result | Dispatch elapsed | VM elapsed | Evidence bytes |
| --- | --- | --- | ---: | ---: | ---: |
| [45086521725](https://github.com/Ares-Empire/AresOS/actions/runs/45086521725) | `1fe72cb0` | Pass, all six steps | 20m19s | 64.3s | 65,682 |
| [45086546954](https://github.com/Ares-Empire/AresOS/actions/runs/45086546954) | `da6ff51f` | Expected failure at step 2, helper health | 46m20s | 74.9s | 873 |

- The clean run verified an active greetd session with labwc and only loopback on both boots. `helper_health` passed twice and the boot ID changed. I inspected `003.png`, which shows the first-start desktop. [Clean evidence](https://github.com/Ares-Empire/AresOS/actions/runs/45086521725/artifacts/14780202619)
- The broken helper passed import and `--list` in image checks, which printed `IMAGE_CHECKS_PASSED`. The VM printed `PASS 001 wait` and `FAIL 002 expect (helper_health did not pass)`. Commit `651ab2fa` restored the helper. [Broken-helper evidence](https://github.com/Ares-Empire/AresOS/actions/runs/45086546954/artifacts/14781452108)
- Both runs scanned 134 plain-image layers and printed `BENCH_PLANTED_LAYER_REFUSED`. I matched both `run.json` records to the dispatch SHA, image revision, guest revision and committed script digest, and reran the evidence scan on the downloaded files.
- The first checks-only dispatch ran 2,588 tests and reported `FAILED (failures=8, skipped=24)`. The failures came from the job-token audit detecting the client ledger read through `gh api`. Commit `b0b03755` switched this read to a public GET without credentials. [Initial checks-only run](https://github.com/Ares-Empire/AresOS/actions/runs/45086520794)
- The checks-only rerun on `b0b03755` passed in 33m05s. It printed `Ran 2588 tests in 1782.837s`, `OK (skipped=24)`, and `Live hosted system manager passed: 434 unit files, 421 unit names`. The change since the clean bench run is limited to the client ledger read and its test. [Passing checks-only run](https://github.com/Ares-Empire/AresOS/actions/runs/45089740931)
- The round used two hosted bench dispatches. No files over 500 MB remained under `.work/`.

## Review fixes, round 2

1. The package 13, release 27, release 28 and release 28 dry-run jobs now run each absence assertion on its own line under `bash -ec`. The regression executes all four extracted Bash blocks. It passes with a clean fixture and refuses every individual CI or bench path, including dangling links at the three installed bench paths. The pending source binding records the updated workflow bytes.
2. Dispatch tests confirm that each ledger-managed branch can select its rehearsal modes before checking that bench disables them. The evaluator models `success()`, `failure()`, `always()`, `cancelled()` and implicit success. The upload test requires scanned evidence to upload after a failed VM step. [GitHub Actions status functions](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions#status-check-functions)
3. The Known limits section records the dispatch-history, concurrency and screenshot boundaries from review 2.

### Verified

- Ran `python3 -B -m unittest discover -s os/tests -p test_bench_release_layers.py -v` and `python3 -B -m unittest discover -s os/tests -p test_bench_dispatch.py -v` one module at a time. The modules printed `Ran 3 tests` and `Ran 7 tests`, respectively, and both printed `OK`. `git diff --check` passed.
- The planted-path regression found 16 false passes across the four original Bash blocks before the fix. Removing the rehearsal bench guard in memory failed the `probe` case on `pkg/16-staged-release`. Adding `success()` to the upload condition in memory failed the case with a failed VM and safe evidence.
- Submitted one bench with `python3 -B os/ci/bench/dispatch.py --ref pkg/334a-bench-hosted reviews/334a-bench-hosted/bench/session-health.json` and watched it with `gh run watch 45094038830 --exit-status --interval 60`. Commit `fcfb4c13` passed all six steps in 19m20s, with 76.4s in the VM. Image checks printed `IMAGE_CHECKS_PASSED`, `No bench files in 134 raw image layers` and `BENCH_PLANTED_LAYER_REFUSED`. Hosted preflight passed the oversize and token refusal tests. [Bench run 45094038830](https://github.com/Ares-Empire/AresOS/actions/runs/45094038830)
- Downloaded `bench-evidence` and verified the dispatched SHA, image label, both guest revisions and committed script digest in `run.json`. The guest recorded an active greetd session with labwc and only loopback on both boots. The authenticated helper check passed twice, and the boot ID changed from `8ca54091-c9e2-4de4-a71a-8e4a6d38d2b7` to `29ad58bd-217a-40d9-9f8b-4f2ec9da159b`. `003.png` shows the first-start desktop and Prism setup. The evidence scan printed `Bench evidence safe: 3 files, 63255 bytes` on the runner and on the downloaded files. [Bench artifact](https://github.com/Ares-Empire/AresOS/actions/runs/45094038830/artifacts/14783466326)
- Ran `gh workflow run 'OS image' --ref pkg/334a-bench-hosted -f checks_only=true` and watched it with `gh run watch 45094038198 --exit-status --interval 60`. The run on `fcfb4c13` passed in 30m58s. It printed `Ran 2589 tests in 1790.699s`, `OK (skipped=24)` and `Live hosted system manager passed: 434 unit files, 419 unit names`. [Checks-only run 45094038198](https://github.com/Ares-Empire/AresOS/actions/runs/45094038198)
- `find .work -type f -size +500M` listed no files.
