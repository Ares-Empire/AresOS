# 03e CI evidence

Exactly one full run, [39718803979](https://github.com/carlsenares/AresOS/actions/runs/39718803979),
workflow attempt 1, source `dc6fcfcf7b5ae4683369ae7c5c938203ee877498`, passed.
Both fresh KVM/UEFI guests read their offline journals and satisfied the full
marker → logind short-power-key record → logind poweroff → orderly logind stop
assertion. Both `offline-poweroff-check.json` results are `passed`. The
pre-authorized hardware-only fallback was not used.

Root files are unchanged copies from the small Actions evidence artifact,
including release/test-image OCI identities, provenance, signature evidence,
package/driver inventories and metrics. `vm-pass-1/` and `vm-pass-2/` preserve
raw bootc/updater/input exports, guest responses, journal-file hashes, reader
commands with stdout file names and stderr, extraction results and successful
structured poweroff results. `offline-verify.txt` is empty because journalctl
wrote its two PASS messages to stderr; `offline-commands.json` retains those
messages and return code 0 for each pass.

The runner rejected the `nologreplay` mount parameter. Read-only NBD and the
Podman `:r` device passed; `btrfs check --readonly` and journal-only extraction
from root 256 succeeded without ignored errors or backup-superblock fallback.
The guest-version journal reader exported and verified both stopped boots.

Large text/JSON exports are preserved without alteration in the lossless
[pass-1 journal/console ZIP](../../../../reviews/03-os-image/03e/vm-pass-1-journal-console.zip)
and [pass-2 ZIP](../../../../reviews/03-os-image/03e/vm-pass-2-journal-console.zip):
`offline-boot.jsonl`, `offline-boot.txt`, `offline-logind.jsonl`, `serial.log`,
`poweroff.txt`, `offline-mount-dmesg.txt` and the empty `qemu.log`. The original
console/dmesg whitespace is retained in the archives; all seven entries in
each archive were hash-compared to the downloaded artifact. The
[workflow ZIP](../../../../reviews/03-os-image/03e/workflow-output.zip)
contains complete output from `gh run view --log`; selected output and run/job/
artifact metadata are beside it. All framebuffer PNGs are under
`reviews/03-os-image/screenshots/03e-vm-pass-*`.

Screenshots show the labwc terminal and independent getty, not an interactive
authenticated shell. PAM evidence is separate. No image, disk, binary journal,
credential or builder configuration is included. The
[03e report](../../../../reviews/03-os-image/REPORT.md#03e-final-offline-power-key-run)
records commands, timestamps, measurements and the remaining hardware limits.
