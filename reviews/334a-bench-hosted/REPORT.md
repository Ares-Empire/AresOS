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

## PLAN-GAP and known limits

- The existing `ci/` build exclusion covered the agent and host runner. The new hosted regressions live under `os/tests/` and needed their own exclusion because the package stage copies the OS context into a raw layer.
- Each dispatch plays one script with the offline guest. The acceptance probe covers the first-start desktop. The evidence scan matches token-shaped file bytes and has no OCR.
- Normal OS checks retain the suite's existing environment-dependent skips for graphical and namespace harnesses.

## Open questions

- The next rehearsal will incorporate the pending source binding. The later bench packages cover laptop operation and other network levels.
