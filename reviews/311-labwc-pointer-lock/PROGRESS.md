# 311 progress: labwc that holds a pointer lock on layer-shell surfaces

**State: ready for review.** Briefs 311 and 311b are built and checked locally. Guard 5 (the session starts in the
check build's VM pass) is `NOT RUN (lead, after the cut)`. Nothing was dispatched, merged or changed on the laptop.

## Done

- `os/labwc/0001-allow-constraints-for-layer-surfaces.patch`: upstream `b7820667a2` adapted to 0.9.6.
- `os/labwc/labwc.lock.json`: the pinned `fedora:44` and its 146 packages, the source package, the patch, the result
  and 306 build dependencies, each by exact NEVRA, SHA-256 and Fedora's signed copy on Koji.
- `os/labwc/stage.py`: `fetch`, `build`, `install` and `resolve`. Every refusal is one `LABWC_REFUSED` line.
- `os/labwc/install-inputs.sh`: puts the checked inputs into `fedora:44`, signatures on, repositories off.
- `os/labwc/resolve-download.sh`: the half of `check_build=resolve` that runs on `fedora:44`.
- `os/Containerfile`: the `labwc-inputs` stage (pinned base), the `labwc` stage (pinned `fedora:44`), the final swap.
- `os/ci/check-build.sh`, `os/ci/check-resolve.sh`: the fresh resolution and candidate lock (`evidence/resolve/labwc.txt`).
- `os/ci/image-checks.sh`: the NEVRA, only one labwc, `rpm -V labwc`, and guards 3 and 4.
- `os/ci/check-image.sh`: the image's copy of the lock must equal the reviewed one.
- `os/tests/test_labwc_stage.py`: 84 tests. `os/tests/test_aresos_desktop.py`: the stage list and one fixture.
- `reviews/311-labwc-pointer-lock/lock-probe/`, `install-proof.sh`: the behaviour probe and the swap proof.

## The `fedora:44` digest

`registry.fedoraproject.org/fedora@sha256:b02bb57e0e8ec2e057f0826436d2fc58765fa2b3b82d2abd322ece06e39c88f5`

Two digests name this image. `sha256:7c338691...` is the multi-architecture index and `sha256:b02bb57e...` is the
x86_64 image inside it (`skopeo inspect --raw`). A fresh `podman pull` of each, in an empty private store, gave the same
image ID `9e2f6840a826...`. The x86_64 digest is pinned because it names exactly the bytes that are built on, and
cannot resolve to another architecture.

## Acceptance of 311b

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | `podman build --target labwc` gives the NEVRA from the locked environment | PASS | `LABWC_BUILT labwc-0.9.6-1.fc44.aresos1.x86_64 e5e33686...f25364d` |
| 2 | Brief 311's items 1 to 4 on that RPM | PASS | See below |
| 3 | `stage.py install` for real in the pinned base, `rpm -V`, guards 2 to 4 | PASS | `install-proof.sh` ended `INSTALL_PROOF_PASSED` |
| 4 | `test_labwc_stage`, `test_aresos_desktop` and the first builder's modules | PASS | See below |
| 5 | `rebind.py pending` after the last bound change | PASS | 10 files before and after, only the note was added |
| 6 | This file ends with the NEVRA and the file list | PASS | Last section |

Commands, from the repository root (`$F` is the digest above, `$P` the pinned base):

```
podman --cgroup-manager=cgroupfs build --target labwc --format=oci --tag localhost/aresos-labwc:311b --file os/Containerfile os
podman run --rm --cgroups=disabled -v <rpms>:/rpms:ro -v reviews/311-labwc-pointer-lock/lock-probe:/probe:ro $F bash /probe/in-container.sh /rpms/<rpm> /probe
podman run --rm --cgroups=disabled -v ...:/proof/... -v os:/os:ro --entrypoint /usr/bin/bash $P /install-proof.sh
```

### Comparison with Fedora's RPM

Fedora's `labwc-0.9.6-1.fc44.x86_64`, SHA-256 `9438b595...16f60b`: the same hash as `os/packages.lock.json`, and
`rpmkeys --checksig` reports its signature OK.

- **Files:** 64 in each. The only difference is the two `/usr/lib/.build-id/` entries (a folder and a link each). Those
  names are hashes of the compiled binaries, so a patched binary must differ.
- **Requires:** 59 in each, identical.
- **Provides:** 2 in each. They differ only in the version of `labwc` and `labwc(x86-64)`, which is the release suffix.
- **Compiler flags:** `%{OPTFLAGS}` is identical.

### Headless probe (`WLR_BACKENDS=headless`, private `XDG_RUNTIME_DIR`, inside a `fedora:44` container)

| Check | Fedora, layer | Ours, layer | Fedora, window | Ours, window |
|---|---|---|---|---|
| Lock activated | FAIL | PASS | PASS | PASS |
| Relative motion arrives in full | PASS | PASS | PASS | PASS |
| No absolute motion while locked | FAIL (20 events) | PASS (0) | PASS | PASS |
| Cursor stays still | FAIL | PASS | PASS | PASS |
| Second lock activated | FAIL | PASS | PASS | PASS |
| Unlock moves the cursor to the hint | FAIL | PASS | PASS | PASS |
| Confinement activated | FAIL | PASS | PASS | PASS |
| Pointer stops at the region's edge | FAIL | PASS | PASS | PASS |
| **Exit code** | **1** | **0** | **0** | **0** |

The RPM is the one the locked stage produced. The probe exits 2, not 1, when the compositor cannot be used.

### Tests

Each module ran alone with `python3 -m unittest discover -s os/tests -p '<module>'`.

| Module | Result |
|---|---|
| `test_labwc_stage` | 84 tests, OK |
| `test_aresos_desktop` | 189 tests, OK, 1 skipped (no user systemd manager reachable) |
| `test_shell_assertions` | 9 tests, OK |
| `test_control_image` | 15 tests, OK |
| `test_checkout_sources` | 8 tests, OK |
| `test_aresos_shell_icons`, `test_aresos_cover`, `test_control_vm` | 43, 9 and 62 tests, OK |
| `test_owner_equality`, `test_everyday_account`, `test_owner_path` | 11, 34 and 48 tests, OK |
| `test_release_squash_binding`, `test_release27` | 7 and 41 tests, OK |
| `test_console_keymap`, `test_tools_local_wiring` | 21 and 42 tests, OK |
| `test_ways_back_model` | **NOT FINISHED**: stopped by this run's 280-second limit. It only names `os/Containerfile` in a fixture |

### `check_build=resolve`

Both halves ran against the committed lock: `Resolved 306 build dependencies; the lock has 306`, `LABWC_LOCK_CURRENT`, and
the candidate file is byte-identical to `os/labwc/labwc.lock.json`. The hosted job itself has not run.

## The five guards

| # | Guard | Result | How it was shown to fire |
|---|---|---|---|
| 1 | Same wlroots | PASS | Real swap with a changed lock: `LABWC_REFUSED the locked wlroots0.19-devel-0.19.4-1.fc44.x86_64 is not the same build as the image's wlroots0.19-0.19.3-1.fc44.x86_64`. `fetch` refuses too (tests) |
| 2 | Checked install | PASS | An RPM of the same NEVRA with an unmet Requires: `LABWC_REFUSED ... did not install (dnf5 exit 1)`, Fedora's labwc stayed |
| 3 | No missing library | PASS | Library moved away: `LABWC_RUNTIME_FAILED ldd exit 0, not found: ['libwlroots-0.19.so => not found']` |
| 4 | Requires met by the base | PASS | wlroots0.19 taken out of the package database: `LABWC_RUNTIME_FAILED no package of this image provides: ['libwlroots-0.19.so()(64bit)']`. On the real swap: `LABWC_RUNTIME_OK 55 requirements` |
| 5 | The session starts | NOT RUN (lead, after the cut) | The check build's VM pass |

## PLAN-GAP

1. **`fedora:44` has no Python and no `rpmbuild`.** `stage.py` cannot start there. The pinned base therefore downloads and
   checks every input in a new `labwc-inputs` stage, `install-inputs.sh` installs them, and `stage.py build` then proves
   that the installed packages are exactly the locked environment. `check_build=resolve` has two halves for the same
   reason. No check was weakened.
2. **The pinned base has no `wlroots0.19`.** Brief 311b's guard 1 says it does. The package comes from
   `os/packages.lock.json`, in the `packages` stage. The guard therefore compares against that lock in `fetch`, and against
   the package really installed in the image at the swap.
3. **R29's release-diff rule (for `linux-aresos`, out of scope here).** `os/ci/release_diff.py` stops on a package outside
   `packages.lock.json`, so it will stop on `labwc-0.9.6-1.fc44.aresos1.x86_64`. The rule must also accept the new
   `usr/share/aresos/manifest/labwc.lock.json`.

## JUDGMENT-CALL

None. Nothing here changes what the owner sees.

## Not verified

- A full image build, and guard 5. The swap proof installed Fedora's labwc and its dependencies from the live Fedora
  repositories with wlroots pinned, not through `build.sh packages`.
- The probe ran on `fedora:44`. labwc has not been started on the pinned base's libraries: guards 3 and 4 show that they
  resolve, and the VM pass must show that the session runs.
- Real hardware and Lan Mouse's `test-capture`.

## What the code does not show

- The source package in the lock is Koji's unsigned copy. Its payload and header digests equal those of Fedora's signed copy,
  whose signature was verified.
- The build environment has `mesa-libgbm-26.2.7`, the image Terra's `26.2.4`. labwc's Requires are identical to Fedora's.
- A locked package may replace its older copy in the base (`expected_environment`). The current lock replaces none.
- `evidence/` is ignored by git, so the results that matter are written out in this file.

## Final NEVRA and file list (for `linux-aresos`'s R29 rule)

`labwc-0.9.6-1.fc44.aresos1.x86_64`, built here with SHA-256
`e5e33686e6e30e9c74132ce145ffe3aaa0948a612c9047f8b2067be04f25364d`. The two `.build-id` names follow the compiled binaries.

```
/usr/bin/lab-sensible-terminal
/usr/bin/labnag
/usr/bin/labwc
/usr/lib/.build-id
/usr/lib/.build-id/0d
/usr/lib/.build-id/0d/65667b21a13425316714134871edf36aca3728
/usr/lib/.build-id/46
/usr/lib/.build-id/46/b7b1406d74be14d9197545cc6d317b7db65d53
/usr/share/doc/labwc
/usr/share/doc/labwc/NEWS.md
/usr/share/doc/labwc/README
/usr/share/doc/labwc/autostart
/usr/share/doc/labwc/environment
/usr/share/doc/labwc/menu.xml
/usr/share/doc/labwc/rc.xml
/usr/share/doc/labwc/rc.xml.all
/usr/share/doc/labwc/shutdown
/usr/share/doc/labwc/themerc
/usr/share/licenses/labwc
/usr/share/licenses/labwc/LICENSE
/usr/share/locale/ar/LC_MESSAGES/labwc.mo
/usr/share/locale/ca/LC_MESSAGES/labwc.mo
/usr/share/locale/cs/LC_MESSAGES/labwc.mo
/usr/share/locale/da/LC_MESSAGES/labwc.mo
/usr/share/locale/de/LC_MESSAGES/labwc.mo
/usr/share/locale/el/LC_MESSAGES/labwc.mo
/usr/share/locale/es/LC_MESSAGES/labwc.mo
/usr/share/locale/et/LC_MESSAGES/labwc.mo
/usr/share/locale/eu/LC_MESSAGES/labwc.mo
/usr/share/locale/fa/LC_MESSAGES/labwc.mo
/usr/share/locale/fi/LC_MESSAGES/labwc.mo
/usr/share/locale/fr/LC_MESSAGES/labwc.mo
/usr/share/locale/gl/LC_MESSAGES/labwc.mo
/usr/share/locale/he/LC_MESSAGES/labwc.mo
/usr/share/locale/hr/LC_MESSAGES/labwc.mo
/usr/share/locale/hu/LC_MESSAGES/labwc.mo
/usr/share/locale/id/LC_MESSAGES/labwc.mo
/usr/share/locale/it/LC_MESSAGES/labwc.mo
/usr/share/locale/ja/LC_MESSAGES/labwc.mo
/usr/share/locale/ka/LC_MESSAGES/labwc.mo
/usr/share/locale/kk/LC_MESSAGES/labwc.mo
/usr/share/locale/ko/LC_MESSAGES/labwc.mo
/usr/share/locale/lt/LC_MESSAGES/labwc.mo
/usr/share/locale/ms/LC_MESSAGES/labwc.mo
/usr/share/locale/nl/LC_MESSAGES/labwc.mo
/usr/share/locale/pa/LC_MESSAGES/labwc.mo
/usr/share/locale/pl/LC_MESSAGES/labwc.mo
/usr/share/locale/pt/LC_MESSAGES/labwc.mo
/usr/share/locale/pt_BR/LC_MESSAGES/labwc.mo
/usr/share/locale/ru/LC_MESSAGES/labwc.mo
/usr/share/locale/sk/LC_MESSAGES/labwc.mo
/usr/share/locale/sv/LC_MESSAGES/labwc.mo
/usr/share/locale/tr/LC_MESSAGES/labwc.mo
/usr/share/locale/uk/LC_MESSAGES/labwc.mo
/usr/share/locale/vi/LC_MESSAGES/labwc.mo
/usr/share/locale/zh_CN/LC_MESSAGES/labwc.mo
/usr/share/locale/zh_TW/LC_MESSAGES/labwc.mo
/usr/share/man/man1/labnag.1.gz
/usr/share/man/man1/labwc.1.gz
/usr/share/man/man5/labwc-actions.5.gz
/usr/share/man/man5/labwc-config.5.gz
/usr/share/man/man5/labwc-menu.5.gz
/usr/share/man/man5/labwc-theme.5.gz
/usr/share/xdg-desktop-portal/labwc-portals.conf
```
