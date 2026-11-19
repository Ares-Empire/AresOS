# 311b: build the labwc stage on a pinned fedora:44

**Goal:** finish package 311. Brief 311 stays in force except where this brief changes it.

**Why:** the stage can't resolve its build dependencies on the pinned Bazzite base. `wlroots0.19-devel` needs `mesa-libgbm-devel`, and no source has one matching the base's Terra `mesa-libgbm-1:26.2.4-1.fc44` (PLAN-GAP 1 in `reviews/311-labwc-pointer-lock/PROGRESS.md`). `linux-aresos` decided on 2026-11-18: build the stage on a digest-pinned `fedora:44`. labwc links wlroots and not mesa, and the base's wlroots0.19 is Fedora's own `0.19.3-1.fc44`.

## In scope

1. **Stage base:** the `labwc` stage in `os/Containerfile` starts from `registry.fedoraproject.org/fedora:44` pinned by digest. Podman reports two digests for the local image (`sha256:b02bb57e…` and `sha256:7c338691…`). Pin the one that a fresh `podman pull` by digest reproduces for x86_64, and say in `PROGRESS.md` which it is and why.
2. **The lock records the whole build environment** in `os/labwc/labwc.lock.json`: the `fedora:44` digest, the source package, the patch, the expected NEVRA, and every build dependency by exact NEVRA and SHA-256. Any drift fails the stage with one clear `LABWC_REFUSED` line.
3. **`check_build=resolve`** prints a fresh resolution of that environment. Fedora's `updates` repository drops old builds, so a later resolve may renew the pins, as for `packages.lock.json`. Keep fetching locked packages by exact Koji URL where that works.

## The five guards

Each guard gets a test or a check that shows it fires.

1. **Same wlroots:** the locked `wlroots0.19-devel` must have the same version and release as the `wlroots0.19` in the pinned base. Otherwise the build refuses.
2. **Checked install:** the final stage installs our RPM with normal dependency checks. Never use `--nodeps` or `--nodigest`-style shortcuts. The exception for the missing signature stays limited to this exact NEVRA.
3. **No missing library:** an image check fails if `ldd /usr/bin/labwc` reports any library as not found.
4. **Requires met by the base:** an image check proves that every Requires of the installed labwc is provided by a package in the image that did not come from the `fedora:44` stage. `rpm -q --whatprovides` for each is enough.
5. **The session starts:** the check build's VM pass shows this. The lead dispatches that build after the R28 cut, so record it as `NOT RUN (lead, after the cut)`.

## Acceptance

Finish the steps left in `reviews/311-labwc-pointer-lock/PROGRESS.md`:

1. `podman build --target labwc` produces `labwc-0.9.6-1.fc44.aresos1.x86_64` from the locked environment.
2. Repeat brief 311's acceptance items 1 to 4 on that RPM: the build, the file and dependency comparison with Fedora's RPM, the headless probe failing on Fedora's build and passing on ours, and a normal window's lock.
3. Run `stage.py install` for real in a container made from the pinned base, followed by `rpm -V labwc` and guards 2, 3 and 4. A full final-image build is not required locally. If memory doesn't allow this step, record it as `NOT RUN` and say why.
4. `test_labwc_stage` and `test_aresos_desktop` pass in full, along with the other modules the first builder ran.
5. `rebind.py pending` is run again after the last change to a bound file.
6. `PROGRESS.md` ends with the final NEVRA and the RPM's file list, for `linux-aresos`'s R29 rule.

## Limits

Brief 311's limits all hold: no hosted workflow runs, no merge, no push to `main`, and nothing on the running laptop. Another session is running its own test compositor here, so match nothing by process name and never signal any labwc you didn't start. Check `free -g` before heavy steps and keep at least 4 GiB available. If less is available, wait and do lighter work first.

**Model:** Claude Opus 5.5: the design is decided and the remaining work is a tight checklist.
