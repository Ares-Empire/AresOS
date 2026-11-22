# Responses to reviews 1 and 2

No finding is declined outright. One part of review 2's should-fix 11 is declined, and the two reviews disagree on one claim (see the `registry_auth` row).

| Finding | Result | How or why |
|---|---|---|
| R1 blocking 1 (host-side test bypass) | Fixed | Section 2 "Native tests": a reviewed list that starts empty, refusals by name before import, everything else in the desk or hosted. Section 5: the recorder has no `exec` or input verb, and lists the bans no OK lifts. Checked `os/tests/power-events.py` 68–79 and 107–113. |
| R1 blocking 2 (swap, OOM, full SSD) | Fixed | Section 3 "Memory" and "Disk space": the shared client-test lock, one capped slice, a watcher, a free-space gate and a run budget. Step 2 tests them under a real hog in the hosted guest before any laptop run. Checked `mod/dev/env.sh` 12–17, 70–89, 500–509. |
| R1 blocking 3 (bench code in an image layer) | Fixed | Code moves to `os/ci/bench/`, already excluded (`os/.containerignore` line 4, `os/Containerfile` line 39). Own build context, a layer scan, a planted-file test. The `image` job gets `check_build == ''` (line 264 lacks it, 421 has it). |
| R1 blocking 4 (evidence boundary) | Fixed | Section 5: a "what is kept" column and the boundary. `status` is cut to six fields (`aresos-desktop` 2626–2645 does return window and leftover names). Journal by unit and pattern; unreadable means `unverified`. |
| R1 blocking 5 (tier 1 example cannot pass) | Fixed | A launcher with `select_monitor` (the stock program picks `eDP` only: `aresos-laptop-home` 594–595, 2565–2572). The watching view waits on `apps_running`; the result is read on the home's own connection (`aresos-shell` 3429–3433, 3816–3821). The VM click waits for 23c with the same override. |
| R1 blocking 6 (step 1 pieces and gate) | Fixed | Section 3: own layer on the plain image, a minimal agent, a disk config with no users, an own timed step, network off, an evidence gate before upload. Step 1's gate is auto-login, helper health with a broken-helper dispatch, a QMP shot and a new boot ID. The world and open-app checks moved to step 5. |
| R1 blocking 7 (first disk, offline update) | Fixed | The disk (step 3) now comes before the live VM (step 4). Read-only export after `os/ci/two_disk_vm.py` line 100 and `os/ci/rehearsal_auth.py` line 127. The guest imports to its own disk; the switch target carries the bench layer; boot ID, revision and channel are required. KVM is opened inside the real container first. |
| R1 should-fix 1 (launch recipe) | Fixed | Section 2: two-phase start, globals and geometry check, the AresOS image as the desk image, systemd stand-ins as the baseline, no user-manager socket. |
| R1 should-fix 2 (script selector, budget) | Fixed | Section 3: `bench_script` bound to the dispatched commit, `run.json`, a cap of 8. The interactive gate sits on the laptop VM, now allowed (T500). |
| R1 should-fix 3 (lid evidence) | Fixed | Section 5 example: policy first, game ready, PIDs with start times, `unverified` on gaps. VM precedent corrected (`power-events.py` 87–94 sends both; `guardian.py` 395–426 holds the lid closed). A who-checks-what table is added. |
| R1 should-fix 4 (what the owner decides) | Fixed | Section 8 keeps only owner matters. RAM ceiling, dispatch cap and the CI artifact are design decisions. The KVM step is his to type. Consent is recorded apart from step 9. |
| R1 known limits 1–3 | Moved to known limits | Section 9, "Seeing" and "Hosted". |
| R1 claim: `no_host_mount` | Fixed | The bench adds an exact mount list; `in-container.sh` 32–36 checks four names only. |
| R1 claim: `client-test.sh` environment | Fixed | The note now cites `driver.py`'s `ENV` (49–55) only. `ISOLATE` (117–118) only removes names. |
| R1 claim: `registry_auth.create` | Fixed | The sentence is gone; section 3 cites the job's permissions instead. `create` has a legacy branch (`os/ci/registry_auth.py` 63–65 into `rehearsal_auth.py` 35–47), and `check-build` never calls it. Review 2's table says "yes"; that holds only for the org path. |
| R2 blocking 1 (laptop home quits headless) | Fixed | As R1 blocking 5. The launcher is named under "Missing" and in step 8. Boxes come from the scene model (`build_scene`, 1025–1040). Section 3 says the VM waits for 23c. The `eDP` limit is in section 9. |
| R2 blocking 2 (memory promise) | Fixed | Section 3 "Memory": watcher, `oom_score_adj`, no `MemorySwapMax=0`, the game found by its scope, step 2's tests. Section 8 says what it cannot promise. Checked `checks.py` 219–241, 263–265. |
| R2 should-fix 1 (bench code in a layer) | Fixed | Solved by `os/ci/bench/` instead of a new ignore line; release-isolation lines added. |
| R2 should-fix 2 (reuse list) | Fixed | Rows for `laptop_home_headless.py`, `laptop_home_helper.py` and `owner_keys.py` (`keyboard_vm.py` line 67 refuses non-ASCII). |
| R2 should-fix 3 (desk image list) | Fixed | The desk runs the locally built AresOS image, so KWrite (`notepad.json`), the fonts, `wlr-randr` and `bwrap` are the shipped ones. The output is set to 1920×1080. |
| R2 should-fix 4 (systemd, lifetime) | Fixed | No systemd in the desk. Lifetime by `--timeout`, an idle limit and clean-up by name. |
| R2 should-fix 5 (no memory cap in tier 1) | Fixed | Podman runs inside a capped scope of the bench slice; the game check is section 3's. |
| R2 should-fix 6 (hosted minutes) | Fixed | Minutes are free (`rehearsal-packages.json`, 22c, 22d and 42 notes). The cap moved to section 3. Read-only probes are recorded as answered (T501). |
| R2 should-fix 7 (password claim) | Fixed | A bench disk config with no user block (`prepare-disk.py` 11–22 sets root's). |
| R2 should-fix 8 (step 7 sizes) | Fixed | Section 3's disk table has every item, measured in step 3. The builder image is named. The build runs under the lock and gate. The export lives only in the bench store. `stock_image.py`'s share is called writable. |
| R2 should-fix 9 (release check cannot run) | Fixed | A unit test over the workflow text, plus a bench-mode layer check. |
| R2 should-fix 10 (CI gaps) | Fixed | Step 6 adds `tesseract-ocr` to `check-build`. Merge order with 321 and the rebind are in sections 3 and 10. |
| R2 should-fix 11 (Wi-Fi, Bluetooth, touchpad sources) | Fixed; one part declined | Sysfs sources and `modes` are added. `nmcli` is not used: it prints network names, which the brief bars. |
| R2 should-fix 12 (citations) | Fixed | The `nvidia-smi` claim is now an assumption (`STATE.md` line 148 does not say it). The `ISOLATE` citation is dropped. The stray-lines bullet is removed (the brief ends at line 120). |
| R2 known limit 1 (user manager) | Moved to known limits | Section 9, "The laptop VM". |
| R2 known limit 2 (another rig injects input) | Moved to section 10 | Listed beside the mod's rig, as the review asked. |
| R2 known limit 3 (desk shows real battery) | Fixed in design | The launcher passes a fixed reading, as `fixture_main` does (539–540). A note on battery tests is in section 9. |
| R2 known limits 4–9 | Moved to known limits | Section 9. Limit 8 (`/dev/kvm`) is also step 3's probe. |
