# Full attempt 1: green, including both VM passes

[Run 39756953602](https://github.com/carlsenares/AresOS/actions/runs/39756953602),
source **`a4eaca14b2b7c8aaef8dd4b815b2abe73fce47e5`**. Workflow elapsed:
**47m32s**. Preceded by [green checks-only CI](../checks-1/README.md).
This uses **1/2** authorized full runs. No source fix or second run was needed.

Printed `Ran 39 tests in 0.766s`, `OK`; syntax checks, signature/tool/package/driver
checks, the 818-unit build audit, release isolation and disk construction passed.
Each container lint reported 10 passed / 1 skipped / 4 inherited warnings.
Each fresh KVM guest rejected both static/generated canaries, then passed its
1,088-unit normal-policy audit with Cockpit masked. Recovery, ignored input
events, rejected direct sleep requests, clean ACPI shutdown and real offline
logind proof passed twice. No hardware-gate contingency was used.

- [Selected output](verification-output.txt), [run metadata](run.json),
  [job/step metadata](jobs.json), [artifact metadata](artifacts.json).
- [Original evidence ZIP](evidence.zip), [archive verification](archive-verification.txt).
  All 103 entries match the expanded download. SHA-256:
  `e7f0a793f46642f6be549dbb283b89b75c97d19b7fabbcf50022ef0b8b861f7a`.
- [Credential-redacted workflow ZIP](workflow-logs.zip),
  [redaction record](log-redaction.txt): two ephemeral VM password-hash occurrences.
- [Expanded raw release/VM provenance and proofs](../../../../os/manifest/ci/03i/README.md).

The original artifact includes both full offline boot text/JSON and logind JSON,
journal verification results/hashes, read-only extraction commands, passive
serial/QMP logs and checksum-protected exports. The kernel mount failed; Btrfs
userspace extraction and exact-boot journal verification succeeded in both passes.
Both QEMU processes exited 0 after guest-initiated shutdown and a poweroff target.
No image/disk, credentials, builder configuration or binary journal was uploaded.

## Screenshots

All six were visually inspected:

- VM 1: [AresOS terminal](../../screenshots/03i-vm-pass-1-aresos-labwc.png),
  [tty3 login prompt](../../screenshots/03i-vm-pass-1-aresos-tty3-getty.png),
  [last diagnostic frame](../../screenshots/03i-vm-pass-1-last-vm-frame.png).
- VM 2: [AresOS terminal](../../screenshots/03i-vm-pass-2-aresos-labwc.png),
  [tty3 login prompt](../../screenshots/03i-vm-pass-2-aresos-tty3-getty.png),
  [last diagnostic frame](../../screenshots/03i-vm-pass-2-last-vm-frame.png).

The session images show the terminal/recovery hints; tty3 shows a login prompt.
The dark last frames contain a small Bazzite label. They are diagnostics;
PAM/getty records prove the tested authentication path and journal/QMP records
prove shutdown. No interactive keyboard login or hardware test is claimed.
