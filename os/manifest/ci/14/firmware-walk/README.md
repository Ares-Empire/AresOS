# Tools USB: predictable unsupported firmware path

This is **source verification and synthetic parser replay**, not a new VM or
physical observation. No disk, boot configuration, device, service or credential
was accessed. The current audit is deliberately unchanged.

`source-files.zip` retains four upstream files at `edk2-stable202402`; all hashes,
URLs and byte counts are in `sources.json`. The entire 85,463-byte `BmBoot.c`
hash is `e961d1bc…e6f3c6`, exactly equal to the source hash recorded with the
runner's installed **OVMF 2024.02-2ubuntu0.10** in the retained 11k contract.
The USB driver/header files are tagged upstream source; they are not separately
attested Ubuntu binary-package files. This distinction is explicit in the index.

In the pinned `BmEnumerateBootOptions`, whole BlockIo handles are enumerated
whether fixed or removable. Only logical partitions, protocol errors and absent
removable media are skipped. The path comes from the handle. This branch does
not require a filesystem or an EFI boot file. Refresh assigns the exact
automatic-option GUID and registers missing options. A data-only exFAT stick
therefore does not avoid the expected automatic option.

The USB bus source appends the USB messaging node (type 3, subtype 5), with
parent port and interface. Multi-LUN storage can also append a logical-unit
node. `firmware_hardware` currently supports root PCI, the retained SATA path,
and the retained NIC MAC/IP/empty-URI paths. It rejects every USB path with
`PLAN-GAP: unsupported firmware device path`.

```powershell
python -X utf8 reviews/14-owner-tools/verify-firmware-walk.py
```

Expected exit **2** means dispatch remains blocked. The replay checks all source
hashes and the pinned BmBoot binding, then feeds three explicitly synthetic USB
paths to the actual unchanged parser. Each is rejected. No exact future USB
port, option number or description is claimed.

Mapping the stick merely to its controller is insufficient: that controller
also hosts the keyboard and remains attached after the stick is detached. It
would conceal precisely the detached-device condition the set rule must catch.
The inherited 11f rule says to stop before dispatch for a foreseeable transition
that fails the rules and forbids widening the rule independently. A narrow
USB-port/interface/LUN identity contract, bound to per-boot QMP and the verified
tools-image backing file, needs integrator settlement before implementation.
