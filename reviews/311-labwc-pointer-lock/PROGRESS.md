# 311 progress: labwc that holds a pointer lock on layer-shell surfaces

**State: ready for review.** Briefs 311, 311b, 311c and 311d are built and checked locally. Guard 5 (the session starts in the
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

## 311c: the labwc build is bound to the locked Fedora digest

Review 1's blocking finding. `stage.py fetch` (the `labwc-inputs` stage) now reads the Containerfile and refuses, before
any download, unless the `labwc` stage's `FROM` is exactly the lock's `base.reference`. The `labwc` stage copies from
`labwc-inputs`, so it cannot start after a refusal. A `FROM` line the check cannot read as that reference (two stages, a
tag, a build argument, a flag, a line continuation, no stage at all) is refused too.

The Containerfile was already in the build context (`os/.containerignore` does not exclude it), so the only context change
is one line in the stage: `COPY Containerfile /tmp/aresos/Containerfile`.

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | A changed digest stops the build before dependencies are installed | PASS | Both sides, below. 0 steps of the `labwc` stage started |
| 2a | `podman build --target labwc` produces the NEVRA | PASS | `LABWC_BUILT labwc-0.9.6-1.fc44.aresos1.x86_64 ef2cf81d...0404c82d` |
| 2b | The same SHA-256 as before (`e5e33686...`) | **FAIL, explained below** | The RPM is not byte-reproducible, with or without 311c |
| 3 | `test_labwc_stage` and `test_aresos_desktop` | PASS | 92 tests OK; 189 tests OK, 1 skipped |
| 4 | `rebind.py pending` if a bound file changed | PASS | No bound file changed: still 10 pending files. The run only added a note, which was dropped |

### Item 1: the refusal

From a scratch export of this commit's `os/`, with one digest replaced by `sha256:aaaa...`:

```
podman --cgroup-manager=cgroupfs build --target labwc --format=oci --tag localhost/aresos-labwc:311c-mismatch --file os/Containerfile os
```

Changed in `os/Containerfile` (exit 1):

```
LABWC_REFUSED the labwc stage must be built from the locked registry.fedoraproject.org/fedora@sha256:b02bb57e0e8ec2e057f0826436d2fc58765fa2b3b82d2abd322ece06e39c88f5, Containerfile says ['registry.fedoraproject.org/fedora@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa']
```

Changed in `os/labwc/labwc.lock.json` (exit 1):

```
LABWC_REFUSED the labwc stage must be built from the locked registry.fedoraproject.org/fedora@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, Containerfile says ['registry.fedoraproject.org/fedora@sha256:b02bb57e0e8ec2e057f0826436d2fc58765fa2b3b82d2abd322ece06e39c88f5']
```

Both logs stop at the `RUN ... stage.py fetch` step: no `LABWC_INPUTS` line and no `install-inputs.sh`.

The new tests run the real `stage.py` on fixtures and on copies of the real files. Five mutants were each caught: the call
removed, the call moved after the first download, the `COPY` removed, any matching line accepted, and the Containerfile
added to `.containerignore`.

### Item 2: why the hash differs

| Build | Source | SHA-256 |
|---|---|---|
| 311b's build | before 311c | `e5e33686e6e30e9c74132ce145ffe3aaa0948a612c9047f8b2067be04f25364d` |
| 311c | `4f36e0fd` | `ef2cf81d9bd79e78358f076588a4e0bcfd968c085ced21f78a16d3630404c82d` |
| Control | `1be3c0f9`, the commit before 311c | `8c10e78d888534db5312320df9fd5072cfac3e4b741228a7f7981df47cf78b5f` |

The control rebuilt the old source and also got a new hash, so 311c is not the cause. Compared with 311b's RPM, both new
builds differ in the same places only:

- **RPM header:** `BUILDTIME`, `BUILDHOST` (the build container's random name), the sizes, and the digests that follow.
- **`/usr/bin/labwc` and `/usr/bin/labnag`:** the `.note.gnu.build-id`, `.gnu_debuglink` and `.gnu_debugdata` sections.
  With those three sections removed, every remaining byte of both binaries is identical. The symbols in `.gnu_debugdata`
  are the same too.
- **File list:** the two `/usr/lib/.build-id/` names, which follow the build IDs.

Requires, Provides, the changelog and all other payload files are the same. Why the debug data varies was not traced: the
debug packages are not kept. A changing `BUILDTIME` alone already gives every build its own hash.

### Limit of the check

It reads the Containerfile in the build context, so a build given a different file with `--file` would not be seen. The
image build in `os/ci/check-build.sh` uses `--file os/Containerfile os`. `os/ci/build-mod.sh` uses the same file but stops
at `--target mod`, so it never runs these stages.

### PLAN-GAP

1. **Brief 311c's acceptance 2 expects a stable hash.** The RPM's SHA-256 changes with every build, so it cannot prove
   that a rebuild is the same. The comparison above is what does.
2. **For `linux-aresos`'s R29 rule:** the SHA-256 and the two `.build-id` paths in the list below describe one build.
   They differ in each build, so the rule cannot pin them.

## 311d: labwc's code is pinned with the varying sections removed

The `labwc` stage now unpacks `/usr/bin/labwc` and `/usr/bin/labnag` from the RPM it just built, removes exactly
`.note.gnu.build-id`, `.gnu_debuglink` and `.gnu_debugdata` from a copy with `objcopy --remove-section`, prints both
SHA-256 values and stops with one `LABWC_REFUSED` line if either differs from `result.normalized_sha256` in
`os/labwc/labwc.lock.json`. The RPM is handed over only after that check.

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Two `--no-cache` builds: different RPM hashes, same normalized hashes | PASS | Table below |
| 2 | A wrong pin stops the build with the new line | PASS | Below, exit 1, no image tagged |
| 3 | `test_labwc_stage` and `test_aresos_desktop` | PASS | 109 tests OK; 189 tests OK, 1 skipped |
| 4 | `rebind.py pending` if a bound file changed | PASS | No bound file changed. Run in a scratch export of `464918c0`: still 10 pending files, 0 removed |
| 5 | The final section gives `linux-aresos` what R29's rule needs | PASS | Last section of this file |

### Item 1: two builds

Run one after the other from the worktree at `464918c0`, each with a new tag:

```
podman --cgroup-manager=cgroupfs build --no-cache --target labwc --format=oci --tag localhost/aresos-labwc:311d-a --file os/Containerfile os
podman --cgroup-manager=cgroupfs build --no-cache --target labwc --format=oci --tag localhost/aresos-labwc:311d-b --file os/Containerfile os
```

| | Build A | Build B |
|---|---|---|
| RPM SHA-256 | `62b8b0dd54c8b27bdc97972c7e389cd052b0160458c8cfe67987fb95883352db` | `da48fe3c26eef6bff6b161460179691e9ffd180146d3044630c221428181f12d` |
| Normalized `/usr/bin/labwc` | `89cd0e901a5cc9f6a7df0d6337d38d817a753318cbdca8b8e620a7cfc0dd71c4` | `89cd0e901a5cc9f6a7df0d6337d38d817a753318cbdca8b8e620a7cfc0dd71c4` |
| Normalized `/usr/bin/labnag` | `7c6896e938198e7922105e01b52118e2bfd75d16c431ea9c9a615127b7cc1f6d` | `7c6896e938198e7922105e01b52118e2bfd75d16c431ea9c9a615127b7cc1f6d` |

Checked again outside the stage, on the RPMs copied out of both images: in both binaries the only sections whose contents
differ are the three removed ones. The two `.build-id` paths differ too, as expected.

### Item 2: the refusal

From a scratch export of `464918c0` with the `/usr/bin/labwc` pin replaced by `aaaa...`, the same command with
`--tag localhost/aresos-labwc:311d-wrongpin` printed the two `LABWC_NORMALIZED` lines and then, with exit 1:

```
LABWC_REFUSED the normalized SHA-256 of /usr/bin/labwc is 89cd0e901a5cc9f6a7df0d6337d38d817a753318cbdca8b8e620a7cfc0dd71c4, the lock says aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```

### Tests

- `python3 -m unittest discover -s os/tests -p 'test_labwc_stage.py'`: 109 tests, OK. The hashing tests use the real
  `objcopy` on small ELF files the test module makes.
- The same module in an `ubuntu:24.04` container, the hosted runners' system (objcopy 2.42, Python 3.12): 109 tests, OK.
- `python3 -m unittest discover -s os/tests -p 'test_aresos_desktop.py'`: 189 tests, OK, 1 skipped.
- 18 mutants of the new code, each caught: another section list (three kinds), the hash of the wrong file, `objcopy` on
  the original, the check missing or after the hand-over, one binary not compared, no printed hashes, a missing binary
  or a failed unpack ignored (three kinds), the pins' shape unchecked (two kinds), `resolve` silent or changing the pins,
  and a refusal that rewrites the lock.

### Renewing the pins

`check_build=resolve` prints this line in `evidence/resolve/labwc.txt`, and its candidate lock keeps the current pins:

```
LABWC_PINS_KEPT a candidate keeps the lock's result.normalized_sha256 and no build ever writes it. After a change to the patch or the locked build environment, run podman build --no-cache --target labwc twice: each run prints LABWC_NORMALIZED lines and stops with LABWC_REFUSED. If both runs print the same hashes, review the change and write them into result.normalized_sha256 by hand.
```

### PLAN-GAP

1. **The hash does not cover bytes outside every section.** `objcopy` writes the headers and the sections, so padding
   between sections and anything appended to the file never reach the hash. Measured on the real `labwc`, one changed
   byte at a time:

   | Changed | Normalized hash |
   |---|---|
   | `.text`, `.rodata`, `.data`, `.note.package`, the entry point, a segment's permissions | differs |
   | Any of the three removed sections | same, as intended |
   | Padding inside the executable segment (three places), padding after it, ELF identification padding | **same** |
   | Bytes appended to the file | **same** |

   A match means the sections are the same, not the whole file. Review 3 showed that some program header fields are
   not covered either, so a crafted file can keep the hash and run differently (`KNOWN-LIMITS.md`, "What the normalized
   pins prove"). In builds A and B the bytes outside the sections are identical and all zero (`labwc` 3202, `labnag`
   3734). The lead keeps this as a known limit.
2. **The pins depend on what `objcopy` writes.** The stage uses the locked `binutils-2.46.1-1.fc44`. Ubuntu's objcopy
   2.42 gave the same two hashes for build A, but a future version need not, so a change to the locked binutils can
   require new pins.

## 311e: the bytes the loader maps are pinned

`os/labwc/loaded_image.py` holds one function, `loaded_sha256(path)`. It hashes the file from offset 0 to the end of its
last segment, with only `e_shoff` and the GNU build-id descriptor set to zero, and it reads program headers only. The
`labwc` stage computes it on the RPM's own payload, prints `LABWC_LOADED <path> <hash>` and stops with one
`LABWC_REFUSED` line on a mismatch or on a file the function refuses. `result.loaded_sha256` in the lock holds both pins,
beside `result.normalized_sha256`, which did not change.

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Both real builds agree, and match the lead's prototype | PASS | Table below |
| 2 | One `--no-cache` build from the real files passes and prints the pinned values | PASS | Below, at `ffacc288`, exit 0 |
| 3 | A wrong loaded pin in a scratch export stops the build with the new line | PASS | Below, exit 1, no image tagged |
| 4 | `test_labwc_stage` and `test_aresos_desktop` pass, and `test_labwc_stage` passes in `ubuntu:24.04` | PASS | 126 tests OK; 189 tests OK, 1 skipped; 126 tests OK in Ubuntu |
| 5 | `rebind.py pending` if a bound file changed | PASS | No bound file changed. Run in a scratch export of `ffacc288`: the same 10 waiting files, 0 removed |

### Item 1: the real builds

The RPMs were copied out of `localhost/aresos-labwc:311d-a` and `311d-b`, and `python3 -I os/labwc/loaded_image.py` ran
on each binary from their payloads.

| | Build A | Build B | Lead's prototype |
|---|---|---|---|
| Loaded `/usr/bin/labwc` | `92b42d5f5174a91adab883a3f6196500483ac08e37adff7928568284d70422f2` | the same | the same |
| Loaded `/usr/bin/labnag` | `789da84fb23e482434c84e300d1a95c90f5cec5ffc1b9a156d2f6b5cdcff47d2` | the same | the same |

### Item 2: the build

```
podman --cgroup-manager=cgroupfs build --no-cache --target labwc --format=oci --tag localhost/aresos-labwc:311e --file os/Containerfile os
```

```
LABWC_NORMALIZED /usr/bin/labnag 7c6896e938198e7922105e01b52118e2bfd75d16c431ea9c9a615127b7cc1f6d
LABWC_NORMALIZED /usr/bin/labwc 89cd0e901a5cc9f6a7df0d6337d38d817a753318cbdca8b8e620a7cfc0dd71c4
LABWC_LOADED /usr/bin/labnag 789da84fb23e482434c84e300d1a95c90f5cec5ffc1b9a156d2f6b5cdcff47d2
LABWC_LOADED /usr/bin/labwc 92b42d5f5174a91adab883a3f6196500483ac08e37adff7928568284d70422f2
LABWC_BUILT labwc-0.9.6-1.fc44.aresos1.x86_64 8f9f4ea2ab3163ee2a760624cd10d7ceb105a3c84f1d980ed73cbea7aba565c6
```

This is a third build with its own RPM hash, and all four pins held.

### Item 3: the refusal

From a scratch export of `ffacc288` with the loaded `/usr/bin/labwc` pin replaced by `aaaa...`, the same command with
`--tag localhost/aresos-labwc:311e-wrongpin` printed the four hash lines and then, with exit 1:

```
LABWC_REFUSED the loaded SHA-256 of /usr/bin/labwc is 92b42d5f5174a91adab883a3f6196500483ac08e37adff7928568284d70422f2, the lock says aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```

No image was tagged. The six intermediate images that build left were matched to the IDs in its own log and removed.

### Review 3's edits on the real `labwc`

Each row is one edit to a copy of build A's `/usr/bin/labwc`. No copy was run.

| Edit | Normalized hash | Loaded hash |
|---|---|---|
| `PT_INTERP`'s `p_offset` + 1 | same | **differs** |
| `PT_GNU_RELRO` made `PT_NULL` | same | **differs** |
| `e_phnum` 13 to 12 | same | **differs** |
| A zero byte after the executable segment made `0xcc` | same | **differs** |
| Bytes appended after the end of the file | same | same, as defined |

### Tests

- `python3 -m unittest discover -s os/tests -p 'test_labwc_stage.py'`: 126 tests, OK. The new tests load the real
  `os/labwc/loaded_image.py`.
- The same module in `ubuntu:24.04` (Python 3.12.3, objcopy 2.42): 126 tests, OK.
- `python3 -m unittest discover -s os/tests -p 'test_aresos_desktop.py'`: 189 tests, OK, 1 skipped.
- 34 mutants of the new code, each caught. The first run of 35 left four: one showed a condition that could never fire
  alone, which was removed, and three led to new test cases.

### PLAN-GAP

1. **The build-id descriptor is in neither pin.** The brief names bytes after `end` as what stays open. The 20 descriptor
   bytes stay open too: both binaries map them in their read-and-execute segment, and they differ in every build. The
   entry point and every other mapped byte are pinned, so changing them alone gives pinned code nothing new to run. That
   is reasoning, not a test. `KNOWN-LIMITS.md` records it.
2. **`COPY labwc/` also copies a local `__pycache__`.** `os/.containerignore` does not exclude it, and a normal import
   would trust a matching `.pyc` over the source. The stage therefore compiles `loaded_image.py` from its source, and a
   test plants such a file to prove it.

### Not checked

No hosted workflow ran, and the final `aresos` image stage was not built: only `--target labwc`. `check_build=resolve`'s
new text is covered by unit tests, not by a real resolve run. No crafted binary was executed, by design.

## Final NEVRA and file list (for `linux-aresos`'s R29 rule)

`labwc-0.9.6-1.fc44.aresos1.x86_64`. The RPM's SHA-256 and the two `.build-id` names change with every build (see 311c
and 311d), so the rule cannot pin them; the other paths do not change.

**Use the loaded hash.** It covers the program headers, the interpreter and every mapped byte except the build-id
descriptor. The function is `loaded_sha256(path)` in `os/labwc/loaded_image.py`, standard library only. Running
`python3 -I os/labwc/loaded_image.py <path>` prints the hash, or prints one line on stderr and exits 1 if it refuses the
file.

| Binary | Loaded SHA-256 |
|---|---|
| `/usr/bin/labwc` | `92b42d5f5174a91adab883a3f6196500483ac08e37adff7928568284d70422f2` |
| `/usr/bin/labnag` | `789da84fb23e482434c84e300d1a95c90f5cec5ffc1b9a156d2f6b5cdcff47d2` |

The lock holds the same values under `result.loaded_sha256`. Bytes after the last segment are outside this hash because
the loader never reads them (`KNOWN-LIMITS.md`, "What the normalized pins prove").

The normalized hash stays pinned as well. It is the SHA-256 of each binary after removing exactly these three sections,
and no others: `.note.gnu.build-id`, `.gnu_debuglink` and `.gnu_debugdata`. A match means "same sections", not "same
file": it catches any ordinary rebuild with different code, but not a deliberately crafted file.

```
objcopy --remove-section .note.gnu.build-id --remove-section .gnu_debuglink --remove-section .gnu_debugdata <copy of the binary>
```

| Binary | Normalized SHA-256 |
|---|---|
| `/usr/bin/labwc` | `89cd0e901a5cc9f6a7df0d6337d38d817a753318cbdca8b8e620a7cfc0dd71c4` |
| `/usr/bin/labnag` | `7c6896e938198e7922105e01b52118e2bfd75d16c431ea9c9a615127b7cc1f6d` |

The lock holds the same values under `result.normalized_sha256`. The list below is from build A of 311d
(RPM SHA-256 `62b8b0dd54c8b27bdc97972c7e389cd052b0160458c8cfe67987fb95883352db`):

```
/usr/bin/lab-sensible-terminal
/usr/bin/labnag
/usr/bin/labwc
/usr/lib/.build-id
/usr/lib/.build-id/6c
/usr/lib/.build-id/6c/06931c13a8ea254717f2eb0d3d0abd8a89c1c4
/usr/lib/.build-id/78
/usr/lib/.build-id/78/3eca393f4b394777e06a7e629b40e556bbe3fc
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
