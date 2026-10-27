# 14v payload format audit (local, no VM acceptance)

`packages.json` records the exact RPM headers read from the pinned Bazzite 44
ISO's squashfs `usr/lib/sysimage/rpm-ostree-base-db/rpmdb.sqlite`. The database
was extracted to an ordinary ignored file, opened SQLite read-only/immutable,
and its RPM header NAME/VERSION/RELEASE/ARCH/SOURCERPM tags decoded. No mount,
RPM installation, guest, firmware access or privileged local command occurred.
The ISO is 9,068,650,496 bytes, SHA256
`776b76f3417723440ee1823d79ec02a2c22860df196d219024edb062ad00d8e6`.
The database hash and extraction path are in `packages.json`; the 99,921,920-byte
database stays ignored. These are the installer/stock packages, also used by
the release derived from that exact frozen base.

This is independently checked against the frozen stock OCI manifest: its
`rpmostree-unpackaged-content` layer was fully rehashed and matched its pinned
descriptor. The layer's hard-linked RPM database member is **byte-identical**
to the ISO database. `packages.json.frozen_base` binds manifest, layer, member,
link target and both database hashes. The read-only header verifier also
passed all15 packages on that separately extracted stock database.

The relevant versions are efibootmgr **18-11.fc44**, efivar-libs **39-12.fc44**,
util-linux **2.41.5-1.fc44**, systemd **259.9-1.fc44**, coreutils **9.10-5.fc44**,
glibc **2.43-9.fc44**, kbd **2.9.0-4.fc44**, rpm-ostree **2026.3-2.fc44**,
ostree **2026.4-1.fc44**, and bootc **1.16.13-1.fc44**.

Replay the package-header check with
`python -X utf8 reviews/14-owner-tools/verify-parser-rpmdb.py .work/14/14v/rpmdb.sqlite`.

`index.json` binds `source-files.zip` and its 40 original primary-source members
by SHA256 before path/member and immutable source URL/commit. The plaintext
source directory was scanned with pinned gitleaks: zero findings. The
deterministic archive preserves original patch context whitespace and bytes;
the source-hash regression verifies every member without extracting it.
Upstream tags were peeled to commits. Fedora f44
dist-git specs exactly match the installed efibootmgr/efivar releases:
efibootmgr's patch list is empty; efivar has three ABI-description patches and
one efivarfs SetVariable storage patch. None changes device-path formatting.
Their original source/license headers are retained. glibc's authoritative
`glibc-2.43` sourceware tag was used because the old GitHub mirror is archived.

## Firmware grammar and OptionalData

Read together:

- [efivar 39 media formatter](https://github.com/rhboot/efivar/blob/39/src/dp-media.c),
  `_format_media_dn`: HD is `HD(decimal,GPT,guid,0xhex,0xhex)`; its File case
  calls `format_ucs2` without a `File(...)` wrapper.
- [efivar 39 formatter macros](https://github.com/rhboot/efivar/blob/39/src/dp.h),
  `format_ucs2`: prints the converted file string with `%s`.
- [efivar 39 path join](https://github.com/rhboot/efivar/blob/39/src/dp.c),
  `efidp_format_device_path`: joins non-end nodes with `/`.
- [efibootmgr 18 output](https://github.com/rhboot/efibootmgr/blob/18/src/efibootmgr.c),
  `show_vars` and `show_var_path`: `Boot` plus four hexadecimal digits,
  active `*` or inactive space, a space, description, TAB, formatted path.
  `show_var_path` appends OptionalData directly, then newline. With `-v`, it
  also prints `      dp: ` followed by space-separated hex bytes, with
  ` / ` between nodes, and `    data: ` with space-separated OptionalData
  bytes when present. The terminating EndEntire node is included.
- [efibootmgr 18 optional-data printers](https://github.com/rhboot/efibootmgr/blob/18/src/parse_loader_data.c):
  exactly 16 bytes use efivar's `{guid}`/known `{alias}` printer; other raw
  bytes print as text if every byte is 32..127, otherwise contiguous hex.
  Legacy `/File(\EFI\...\shim...efi)` gets the special UTF-16
  ` File(.<decoded optional data>)` suffix. The owner invocation uses `-v`,
  never `--unicode`. OptionalData has **no general delimiter** before it.

The parser reads Boot records, unique numbers and known metadata; it does not
search descriptions or OptionalData for an HD node. It accepts both the
current `/\EFI\...` and the explicitly required legacy
`/File(\EFI\...)` node. When verbose bytes exist, their node lengths, GPT
identity, file string and EndEntire terminator must agree with the text;
OptionalData must render exactly under the rules above. An unreviewed GUID
alias is a STOP. Without byte rows, only an unambiguous terminal `.efi` bare
path or closed legacy File node without OptionalData is accepted. Multiple
instances, missing/duplicate IDs or byte rows, unknown node grammar, a wrong
GUID, non-`\EFI\` file, disagreement, or zero/multiple target matches STOP.
An inactive target option still counts, so it cannot hide a duplicate.

Other hardware/network/FvFile options remain non-candidates; their labels or
OptionalData cannot manufacture a Linux match. The conservative recognized
node names come from the retained efivar media/hardware/ACPI/message formatters.
No NVRAM, BootNext, Windows-first, protected-disk or detached-device rule changed.

`os/tests/fixtures/owner-tools/efibootmgr18-efivar39.txt` is a **source-rendered
reconstruction**, not captured guest stdout. Its HD/File/End bytes and Bazzite
description come from qualification 2's retained Boot000A load option. There
is no OptionalData. `tool-output-sources.json` binds the private varstore hash,
run and variable and the generated fixture. The failed qualification did not
retain the actual `efibootmgr -v` stdout; the new private refusal record does.
The native loop stand-in uses these same pinned printf formats and independently
queried GPT GUID, including correct verbose bytes, rather than the former
made-up space-separated `Linux HD(...)/File(...)` line.

## Every other external-output parser in the 12-file payload

The audit includes `owner.py`, `media.py`, `at`, release.json and all eight
copied `release/*.sh` files, including the duplicate updater helpers inside
pin-stock.sh. The shared release scripts are unchanged.

| Input and consumers | Pinned format checked and fixture/result |
|---|---|
| `systemctl ... --no-pager --no-legend list-unit-files`, owner paused_state and shared pause/pin unit_files | systemd output_unit_file_list has UNIT FILE, STATE, PRESET, no legend/footer under these flags; captured stdout is non-TTY. The first two fields used by both parsers are correct. The executable shim now emits all three source-defined columns, including `-` for a masked preset; the real paused_state parser is exercised. |
| `systemctl show` and `runuser ... systemctl --user show`, owner paused_state and shared pause/pin unit_state | bus_print_property_value emits one `Name=Value` per selected property. LoadState/ActiveState/SubState are string enums; missing required state fails their predicates. No translated headings or human status summaries are parsed. The real parser tests use these source rows. |
| `id -u`, `id -nG`, account/check and release shell guards | coreutils id.c prints decimal UID plus LF or space-separated group names plus LF. strip/split and exact UID/wheel comparisons match. No prose from `id`'s default mode is parsed. |
| `getent passwd`, account, shared pause/pin user manager and stock-session | glibc getent.c uses putpwent: colon-delimited passwd record, username before first colon; absent key has empty stdout and exit 2. Prefix lookup and absence/exit tests match. Password hashes are not queried or stored. |
| `loginctl list-sessions --json=short`, session | loginctl list_sessions builds session/uid/user/seat/leader/class/tty/idle/since table; JSON is an array, USER is the login name, UID numeric, tty nullable. JSON mode disables legend. The real session parser is exercised with all source-defined fields and a remote-login refusal. |
| `loginctl show-session ... --property=TimestampMonotonic --value`, session | bus_print_property: uint64 TimestampMonotonic is neither a name ending Timestamp nor containing USec, so it prints raw decimal plus LF, not a human date/timespan. The integer predicate is correct. |
| `loginctl show-session ... Service,Type,Remote,Name,User`, session | bus_print_property_value emits `Name=Value`, booleans `yes`/`no` and uint32 UID decimal; exact five-property equality is correct. |
| `busctl --json=short call ... Properties.GetAll`, keyboard | busctl JSON transform retains outer data array, dictionary and typed variant objects (`type`, `data`); localed exports all six named strings. Real keyboard() reads a full source-shaped response, including empty variants/toggles. |
| `dumpkeys --keys-only`, check/layout proof | kbd dump.c emits padded `keycode <decimal> = <symbols>` rows; dumpkeys.c's flags do not add a prefix to this row. First symbol can be `+letter` or Unicode letter notation. The layout-sensitive y/z predicates stay exact. Shims and walk now use losslessly JSON-encoded, verbatim keycode21/44 projections from retained package13 captures, all columns/spaces kept, with hashes and source paths. |
| `rpm-ostree kargs`, prepare/shared system-keyboard | rpmostree_builtin_kargs prints old_kernel_arg_string and LF. Existing shlex parsing and refusal of non-round-tripping quoted arguments match. Existing de/us, wrong serial, old deployment and whole-list refusal tests remain. |
| `rpm-ostree status --json`, observations and shared scripts | pinned status JSON emitter/deployment utilities produce deployments and transaction plus exact checksum/serial/osname/booted/pinned/origin/digest fields. Retained 11f/13 fixtures exercise real identities, one/two entries and staged states; no invented text-summary fixture replaces JSON. |
| `bootc status --json`, observations and switch/rollback/default-stock/system-keyboard/pin | pinned Rust serde spec defines status slots, camelCase fields and OSTree identities. Retained paired rpm/bootc captures and whole-list/pin/pending checks remain. |
| `lsblk --json --tree --output ...`, disk_record and media.find | util-linux lsblk explicitly enables tree JSON independently of NAME. Lowercase named fields, root blockdevices, nested children, numeric/boolean columns and mountpoints arrays match. Existing real-helper flat/tree/mounted-protected/two-label refusal tests and native loop test remain. No partition ancestry inferred from a flat list. |
| `findmnt --json --list ... --output SOURCE,TARGET,FSTYPE`, mount_record | findmnt plus libsmartcols print flat filesystems rows with selected lowercase string keys. Btrfs SOURCE may include `[/subvolume]`; only that suffix is removed before comparing a known child path. Existing nested/duplicate/wrong-target refusals remain. |
| `sfdisk --json`, disk_record | pinned sfdisk prints partitiontable JSON. It is retained as diagnostic JSON, with no text/row inference or partition mutation. |
| Host.script output from shared pause/pin/keyboard/switch/recovery/verify | Recorded, not parsed as a tool's human-readable status. Each shared implementation checks its own immediate identity/idle/pin/postconditions. Signature verification is cosign's exit/policy result, not a regex over its prose. |
| localectl, ostree pin/set-kargs/set-default, bootc switch/rollback, rpm-ostree cleanup/reload/cancel, mount/umount/sync/systemctl mutation commands | Exit status plus independent postcondition re-read; no formatted stdout parser. |
| pgrep | Success exit status proves the named process; PID text is not parsed. |
| journalctl, Flatpak application IDs/runtime-sync check/systemctl runtime state | Opaque private diagnostics only; no text can authorize a deployment, pin, reboot or disk choice. |

Additional file/protocol parsers were inspected: BLS title/options and ostree
deployment links use retained entries and pinned libostree writers; proc
cmdline uses NUL separation, cgroup uses colon fields and the exact daemon
unit path, loginuid is decimal, boot_id is a UUID, and /proc/cmdline is split
only for the existing override prohibition. Bundle/private-record JSON is our
own explicit protocol. The registry HTTP JSON parser accepts token/access_token
only in memory and verifies exact manifest bytes/digest; it is outside Host's
trace. Podman login uses hidden stdin with both outputs discarded, and no
credential content enters a command record. These paths retain their existing
transport/zero-mutation refusal tests. No other payload output parser was found.

New regressions run locally with read-only command responses, ordinary repo
files and explicit POSIX metadata stand-ins. They do not prove native mounted
hardware or VM acceptance; no dispatch is authorized by this audit.
