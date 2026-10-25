# Package 14 zero-cost source prerequisite

**14b supersedes the original NVIDIA blocker.** Commit `11728c5` accepts its
Flatpak-only deferred retry. The original `verification.json` below remains
historical evidence. `deferred-work-14b.json` classifies the retained setup
paths; `verification-14b.json` records the accepted source gate. Replay with:

```powershell
python -X utf8 reviews/14-owner-tools/verify-zero-cost.py --14b
```

That source replay exits **0**; it does not authorize a dispatch or prove a VM
installation. The subsequent tools-USB stage walk is **STOP / PLAN-GAP**, recorded
in [../firmware-walk](../firmware-walk/README.md). No new audit rule was assumed.

## Original gate, before the integrator decision

The offline first-boot prerequisite fails its no-deferred-network-work condition.
This is a source/data finding, **not a newly executed offline VM failure**.
See [REPORT](../../../../../reviews/14-owner-tools/REPORT.md).

`source-files.zip` preserves 53 original files: 27 public pinned sources, 10
files read from the complete verified ISO, and 16 files/link targets read from
the exact frozen public stock image. Nothing in the archive was executed.
Enabled-unit symlink targets are stored as ordinary text, without following or
creating host symlinks. No image layers, installer media, credentials or laptop
records are committed.

- `source-archive.json`: complete ZIP-member hashes and ZIP hash/size.
- `sources/index.json`: public source URLs, original hashes and byte lengths.
- `iso-file-index.json`: exact ISO paths and hashes; member paths inside the ZIP.
- `base-files/index.json`: exact base paths, hashes, source manifest and layer
  identities. The complete downloaded layers were hashed before reading them.
- `iso-verification.json` and `live-CHECKSUM.txt`: full 9,068,650,496-byte ISO hash
  and the freshly obtained official checksum. Large local inputs stay ignored.
- `flatpak-cache-summary.json`: all 27 installed runtime IDs, all 20 paths
  containing `nvidia` under Flatpak, full listing hash and line count. Generic
  `nvidia-vaapi-driver`/Mesa files do not provide the required versioned NVIDIA
  runtime IDs. Neither required runtime is installed.
- `verification.json`: actual source-gate result, including the replay of the
  complete 1,439,437-line filesystem listing in this run.

The existing raw base manifest at `os/manifest/ci/06/image-6/base-oci-manifest.json`
itself hashes to the pinned base digest `ed93d215…435151`. Its downloaded layers
used here are `1af49583…f96962` (324,644,312 bytes, unpackaged files/initramfs)
and `89d10b98…0b89` (156,741,603 bytes, Homebrew). Only selected textual data is
retained. The actual ISO cache catalogue names the same base digest.

Replay the retained hashes and source decision, with no network or hardware use:

```powershell
python -X utf8 reviews/14-owner-tools/verify-zero-cost.py
```

It prints `STOP-PLAN-GAP` and exits **2**. A changed/corrupt input instead fails
an assertion. This is deliberately not a green feature test.

To reproduce the ISO inventory independently, obtain the pinned ISO, verify its
complete hash against the manifest and a fresh official checksum, then use the
already available unsquashfs reader on the ordinary file, without a mount:

```bash
unsquashfs -ll -o 314167296 .work/14/bazzite-nvidia-open-stable-live-amd64.iso > .work/14/squashfs-files.txt
python3 reviews/14-owner-tools/verify-zero-cost.py --listing .work/14/squashfs-files.txt
```

The optional listing replay requires the complete listing's retained hash and
line count, then recomputes every runtime ID and NVIDIA path. The default replay
checks the retained summary; it does not claim to independently rescan absent
large media. `--record` explicitly writes a result; the default is read-only.

The first-boot counterexample needs the installed NVIDIA module. Stock enables
`ublue-nvidia-flatpak-runtime-sync.service`; its condition checks both GL and
GL32 NVIDIA runtimes, its sync command installs missing runtimes from Flathub,
and systemd retries failed starts every 30 seconds (600-second start timeout).
The virtio-only VM is not evidence that this hardware-dependent path is idle.
At that original stop no workaround, alternative media route, helper
implementation or dispatch was authorized by the failed prerequisite. 14b now
permits continuation subject to the separate unchanged safety gates.
