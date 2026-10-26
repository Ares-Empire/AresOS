# 14n payload JSON query audit

The audited files are `os/owner-tools/owner.py`, `media.py`, and the eight
`release/*.sh` files copied by `bundle.PAYLOAD`. The generated payload must
equal these files byte for byte; it has no independent implementation.

| Query | Consumer and shape | Result |
| --- | --- | --- |
| Both `lsblk --json --output ...` calls | `disk_record` needs a disk's EFI descendants; `media.find` needs a labelled partition's physical parent. Without `--tree` and without NAME, util-linux returns flat rows. | Both now request `--tree` explicitly through `media.block_tree`. Root partitions, repeated device paths/parents, nested disk roots, missing/non-list mountpoints, non-list children and malformed rows STOP. Optical/live loop roots are permitted; partitions must be direct children of a disk or loop root. No ancestry is reconstructed from names or order. |
| `findmnt --json --mountpoint /boot/efi`, `/boot`, `/sysroot`; `findmnt --json --target <payload>` | Each consumer expects one selected filesystem, never descendants. | All now use `--list` through `mount_record`, require exactly one row, no children, string SOURCE/TARGET/FSTYPE, and an exact TARGET for `--mountpoint`. Existing source/EFI/USB filesystem checks remain. The native regression runs these query options and the real helpers, with scratch paths replacing the guest mountpoint arguments. |
| `sfdisk --json <each selected whole disk>` | `disk_record` retains the complete `partitiontable` document for record C; it does not walk `children` or infer ancestry from these rows. | No tree/list selector assumption. Query remains read-only and unchanged; partition identity used by the preflight comes from validated lsblk ancestry and the firmware/EFI checks. |
| `rpm-ostree status --json` | `observations`, pause/pin/system-keyboard/default-stock shared programs consume the object and ordered `deployments` array, transaction and deployment identity/flags. | No selectable tree output. Existing complete-list identity, pin, staged, pending and before/after assertions remain. Retained stock one/two/staged fixtures and refusal tests exercise these consumers. No shared release script changed. |
| `bootc status --json` | `agree`/qualified-state and shared scripts consume the object `status` and its named booted/staged/rollback slots. | No selectable tree output or partition traversal. Existing cross-checks against the rpm-ostree list and complete state remain. No shared release script changed. |
| `busctl --system --json=short call ... Properties GetAll ... locale1` | `Tools.keyboard` reads the typed method reply's `data[0]` property map, then each variant's `data`. The same typed reply contract is used by the retained keyboard harness. | Not table/tree JSON; neither NAME nor a tree/list flag applies. Existing index/key/type errors propagate to the entry point's STOP handler. No flattening or alternate schema guess added; no decoder change is needed for this delta. |
| `loginctl list-sessions --json=short` | `Tools.session` selects exactly one row from the flat session array by tty and recovery user, then checks show-session service/type/remote/name/uid/time. | Not a device tree; the list is the intended contract. No `children` walk or inherited properties. Missing/unknown shapes raise into STOP before a layout change. No session predicate changed. |

Other JSON is file input (the hash-first bundle manifest, frozen release or
private records) or the documented output of embedded shared programs, not
another CLI's implicit tree. The manifest verifier, unique keys, recorded
identities and complete state comparisons remain in place.

The native-only regression uses two fresh GPT loop files. The target fixture
has an EFI-type FAT partition and an exFAT ARESTOOLS partition. Native lsblk
and findmnt output supplies every partition and tree/mount shape. Loops have
no hardware serial/USB transport, so its adapter supplies only root TYPE,
serial, TRAN and RM; it maps the three guest mountpoints to one scratch FAT
mount and supplies a synthetic firmware read using its real EFI PARTUUID.
It never reshapes a tree, changes a partition identity, reads/writes firmware,
or touches a physical disk. These fixture boundaries are recorded in evidence.
Successful real-helper checks, unchanged protected-file hash, confirmed
unmounts and backing-verified detaches are mandatory. This is query-contract
coverage, not a Linux installation or physical-device qualification.

Local tests run that entire native control path with closed stand-ins,
including flat output, failed FUSE mount, wrong backing and unconfirmed
unmount. Actual loop/mount execution is deferred to the November probe's
mandatory native suite. The tests do not install packages or invoke devices
locally.
