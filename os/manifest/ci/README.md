# CI evidence snapshot

This directory's original files remain the package-03 snapshot. The separate
[03b snapshot](03b/README.md) records the latest failed follow-up, the successfully
exported raw bootc status and a runtime inventory recovered from its serial log.
Neither snapshot is evidence of completed power/TTY acceptance.

The generated files are downloaded from the `os-image-evidence` Actions artifact
for run 39685234531. `jobs.json` comes from the GitHub API; the explicitly labeled
`backend-observation.json` records the observed guest output from that artifact.
`provenance.json` identifies the exact checkout, run, verified base reference and
resulting OCI manifest digest. The result digest hashes `image-oci-manifest.json`;
it is distinct from Podman's image configuration ID.

- `base-signature.json`, `base-key-sha256.txt`: successful upstream public-key
  verification output and SHA-256 fingerprint of its DER public key. This is
  container verification material, separate from firmware/MOK trust.
- `packages.txt`, `packages.lock.json`, `kernel-nvidia.txt`: complete RPM
  inventory, exact added RPM versions/content hashes, and the unchanged upstream
  kernel/NVIDIA package subset.
- `updaters.json`: image-build inventory of system/user unit enablement and
  command lines, including masked candidates and reviewed bookkeeping.
- `backend-observation.json`: recorded result of the successful live guest
  `bootc status --json` assertion. Raw status JSON was not exported because the
  later TTY prompt wait failed; this file explicitly records that limitation.
- `metrics.json`, `disk-samples.jsonl`, disk/time text files: measured runner
  usage, image size and sparse VM disk sizes. Files/disks are not byte-identical
  rebuild promises; UUIDs, build timestamps and VM-only credentials can differ.
- `tool-versions.txt`, `vm-acceleration.txt`: host tool versions and selected
  QEMU acceleration. No `poweroff.txt` exists: the failed TTY wait prevented the
  clean ACPI-button shutdown test from running.

Screenshots live under `reviews/03-os-image/screenshots/`; the report links the
tested source commit and failed run. No container image, VM disk, VM credential or disk
builder configuration is committed or uploaded. The derived image is unsigned
and unpublished in this package. This directory is excluded from build context
and workflow source-change triggers so recording evidence does not rebuild it.
