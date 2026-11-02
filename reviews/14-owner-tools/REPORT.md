# 14: checked owner tools

## 14zzf REPORT: real-entry STOP, export and reboot-boundary survival

**Done:** replaced the unrelated-directory "reboot model" in
`test_owner_export.py` with the real owner `__main__` sequence. Three isolated
`python3 -I -B` processes run the controlled `records unexpected` STOP, checked
`export`, and checked `export` after the reboot boundary. The exact diagnostic
must first exist under `var/lib/ares/diagnostics`; the STOP performs only the
read-only firmware query. Both fixture bundles contain manifest entries only.
After the first export all tool processes have exited; the entire mapped `/run`
tree (including the real media mount directory) is removed and recreated
empty. The stick's diagnostic bytes are checked before and after the fresh
export, against the original persistent bytes. Two real export success records,
SHA readback and safe-unmount results are required.

`owner_export_fixture.py` relocates only the filesystem root prefix, before
loading the unchanged payload entry point. It never overrides HOME,
STOP_RECORDS, media.MOUNT, the recorder or export methods. Root/POSIX metadata
on unprivileged DrvFS and device/mount/sync/firmware command results are explicit
host stand-ins; real files, JSON, atomic writes, fsync, private-path checks,
manifest verification, copying and readback execute. Unknown host commands
refuse. No real mount, device, firmware or privilege operation occurs.

**Verified:** with PYTHONDONTWRITEBYTECODE unset, WSL Python 3.12.3 ran
`python3 -m unittest -v test_owner_export test_owner_diagnostics test_owner_entry test_owner_tools`:
**27 tests / 72.452 s, PASS, zero skips**. The same command with `-B`:
**27 tests / 71.217 s, PASS, zero skips**. The owner subprocesses retain the
production launcher's `-I -B` in both suite modes.

The unchanged regression ran against exact pre-14zzc payload commit
`bd855274143e564f832c873cf9d0c134fe340e29`: **one expected failure**, no errors or
skips, `0 != 1: STOP diagnostic missing from persistent /var/lib/ares/diagnostics`.
The preceding assertions prove a stopped diagnostic really was written. This
historical payload has its original JSON-only manifest; its fixture copier
copies precisely those historical entries, without adding the later SUMS file
or rewriting production code. See [local receipts and negative-control log](../../os/manifest/ci/14/14zzf-local/result.json).

During fixture bring-up, two local attempts exposed Python 3.12 Path subclass
construction errors in the test adapter; those were corrected before the final
module runs. The negative-control driver initially encountered the Windows
worktree gitfile from WSL and the historical absence of SHA256SUMS; using the
existing Windows Git read-only and the exact historical manifest resolved both.
These were fixture/driver errors; no payload defect was found.

The reviewed payload and every source copy remain unchanged; fingerprint:
`3e2c78ebedf7789b0616e7a4f21ad791d76784667344e76e97a1fbd95115a6fd`.
Pinned gitleaks 8.21.2 full-history and pending-file scans: **zero findings**.
`git diff --check` passed. Delivery is one fast-forward push through the actual
privacy hook, without bypass. No Actions dispatch or new VM claim.

**Corrected claim / not verified:** qualification 21 exported records before its
deliberate STOPs; it did **not** test STOP → export → reboot survival. The local
regression proves that exact diagnostic sequence across fresh processes and
loss of all mapped `/run` state. The existing VM evidence proves the checked
export route and `/var/lib/ares` persistence across actual reboots. There is no
new physical or VM reboot test. The historical qualification/source bindings
continue to identify `3fd7916`, not this test-only follow-up. Physical release
and followability gates remain open; **NOT RELEASED**.

**JUDGMENT-CALL / PLAN-GAP / open questions:** none. Review findings 1, 2, 3 and 5
remain closed; finding 4 now has the requested local regression and corrected
evidence claim for integrator re-check. No merge or release/publication.

## 14zze REPORT: checkout-byte bindings; probe 34 and qualification 21 passed

**Disposition:** [probe 34](https://github.com/Ares-Empire/AresOS/actions/runs/41371893590) **success**, [qualification 21](https://github.com/Ares-Empire/AresOS/actions/runs/41374876561) **success**, once each on pushed head `3fd79165fa96406948c17ea90f94f943cd9bc201`. Independent complete
evidence review passed; **VM acceptance is met**. There was one fast-forward push
through the installed privacy hook, no Actions rerun, no merge, and no image
build, release or publication. PR #13 is ready for review after closing checks.
This REPORT, curated evidence, ledger and actual-status guide/card update are
committed **locally only**, with no second push. Physical release is **NOT RELEASED**.

### Done

`os/ci/checkout_sources.py` copies explicitly named repository sources and their
declared attributes into a temporary, repository-local Git fixture. Git stages
the inputs and checkout-index materializes them into a separate empty directory
with core.autocrlf=false. Global/system attributes are excluded only for those
scratch processes; actual repository settings and its pre-push hook are intact.
The recorded SHA-256 is over those checkout bytes. No blob digest is compared
to a checkout digest. Staged/committed blobs are inputs to the same checkout
replay when the pre-push gates verify the future runner tree.

The native owner_vm check is unchanged: its actual working-tree bytes must
equal the recorded bytes. The PowerShell test now binds the 4,961-byte CRLF form,
including 72 CRLF endings, rather than the 4,889-byte LF blob. The attributes
file is itself bound. The reviewed payload fingerprint remains
`3e2c78ebedf7789b0616e7a4f21ad791d76784667344e76e97a1fbd95115a6fd`.

The binding audit covers qualification host-walk/result.json and
preflight/walk.json, probe-walk.json, preparation.source_bindings, archived
preflight tools, preflight/files.json, staged/committed gates, both replay
receipts, and closing archives. Archived tools have separate local_sha256 and
checkout sha256 fields. Private tool/log/artifact/ISO fingerprints still hash
their actual captured or delivered bytes. Historical records and frozen
payload/release fingerprints are preserved. The detailed generator/consumer
list is in preflight/binding-audit.json.

Three new tests replay every current source table, assert the real PowerShell
CRLF conversion, refuse the exact 195-row dda72ed record, and test real Git
LF/CRLF/binary behavior, changed/missing sources, unsafe paths, duplicates and
conflicts. That old CRLF-declared source itself is unchanged, isolating its old
LF hash as the negative control. No source comparison is relaxed. No owner
script, payload, workflow, harness, image/release path, privacy rule, package 13
or package allowance changes.

### Verified locally before the single push

Twelve affected modules (the new checkout tests and the eleven 14zzd modules)
ran with PYTHONDONTWRITEBYTECODE unset: **78 tests / zero skips**, normal
Python in 659.504 s; **78 tests / zero skips**, -B in
659.505 s. Both passed. The new three checkout tests also passed under
Windows Python. The three-test final replay passed against all six sealed
tables in 6.779 s, followed by staged- and committed-tree replay.

Full discovery under normal Python ran **630 tests in
2129.297 s**: **621 passed**,
9 documented local host limitations, **zero skips and zero
unknown failures**. The unchanged 30-second timing case overran locally at 71.04893822600025 s (the documented host limitation). All 630 tests, including that bound,
remain mandatory in native CI; any native overrun is a STOP.

The final coordinator was `python -u -X utf8 .work/14/14zze/final-local.py`.
Exact WSL commands, the environment policy, full discovery and safe local shims
are retained in preflight/final-local.py and whole.py. Qualification and probe
stand-in walks passed, including all remaining stages, 27 hidden transitions,
three handoffs, 154 cluttered waits, thirteen real typing-chain cases and final
Windows markers. No wait is uncovered. Strict syntax passed 1159 composed
guest commands, 954 embedded Python bodies, 12 shell files and
54 CI/overlay/owner Python files.

Local controller tests: 31 passed. Windows helper: seventeen zero-write
refusals and successful checked copy/private entry point passed. Actual
read-only release/git/GH replay and all 53 retained inputs passed. Four
credential-only registry steps remain fail-closed in CI.

Actual ISO inspection passed on driver attempt four, hashing all 9,068,650,496
bytes against the pin and fresh official checksum. Attempts one and three hit
the accepted Windows checkpoint Path.replace denial; attempt two was refused
by the local space preflight before inspection started. The bounded 10/20/30 s
retry sequence was kept. Two pairs of completed ISO/squash duplicates were
hash-verified before unlinking; failed partials, checkpoints, logs, master ISO
and canonical extraction remain. No CI inspector change. The coordinator's
first start preceded log creation; its corrected restart waited for those
files and did not restart a test.

Pinned gitleaks 8.21.2 pending/full-history scans, exact-range privacy precheck,
the real hook, source replay and fresh live guards passed before dispatch.
Source/result/control bindings are in
`os/manifest/ci/14/14zze-preflight/preparation.json`.

### Sizing / budget

Starting history: **155/155 IDs**, **2326 / 2750 minutes**, counts **33 probes /
20 qualifications**. Last-dispatch deltas agree at +16 package / +16 organization.
Organization free: **1385**, reserve **150**. Reservation 72+240=312 gives
**2638 <=2750** and leaves 1073 organization minutes. The retained projection
fits unchanged VM 200 / qualification 240 limits. Caps stay 34/21. November is
free-minutes-only, no paid budget read, with zero local-hook push/closing privacy
reservations. Fresh ledger/billing comparisons passed before both dispatches.

### Actual November round / independent review

[probe 34](https://github.com/Ares-Empire/AresOS/actions/runs/41371893590) **success**, [qualification 21](https://github.com/Ares-Empire/AresOS/actions/runs/41374876561) **success**. No run was rerun.

Run 41371893590: native **630 tests / zero skips**, 223.789 s. Independent review: complete and passed.

Artifact scan: 509 findings, comprising 507 exact pinned public ISO listing lines and 2 exact whole-line public kernel X.509 messages. Every occurrence is recorded by file, line, source-line SHA and approved-token cross-check in probe34-artifact-review.json. No ignore/rule/workflow changes.

Every completed job log was scanned; 4 findings were the exact pinned cosign-installer checksum class. Unknown findings: zero.

Run 41374876561: native **630 tests / zero skips**, 138.095 s. Independent review: complete and passed.

Artifact scan: 531 findings, comprising 507 exact pinned public ISO listing lines and 24 exact whole-line public kernel X.509 messages. Every occurrence is recorded by file, line, source-line SHA and approved-token cross-check in qualification21-artifact-review.json. No ignore/rule/workflow changes.

Every completed job log was scanned; 4 findings were the exact pinned cosign-installer checksum class. Unknown findings: zero.

Qualification 21 passed the real bootstrap/private-copy install, prepare and
zero-mutation rerun, checked records export, offline and network
boundaries, signature/private login, switch and all original layout proofs,
rollback, keep-stock and final attached/detached Windows markers. The extra
plain-US pending trial received QMP system_reset without a guest shutdown.
Next boot proved German on tty1..tty6, fresh German password/sudo login and
physical foot typing, then layout abandon and guarded reboot. Independent
review rechecked raw maps, persisted console/X11 equality, fresh-login receipts,
exact reset origin and absent tools stick. Protected-disk, BootNext, NVRAM,
detached-device and firmware audits remain unchanged and passed.

Correction for review finding 4 (14zzf): qualification 21 did **not** exercise
STOP → export → reboot survival of that exact diagnostic. Its export preceded
the deliberate STOPs. The VM proves the checked export route and `/var/lib/ares`
persistence across reboots; the local 14zzf real-entry regression separately
proves the STOP/export sequence with the entire mapped `/run` removed and fresh
processes. These are distinct evidence, not a new VM survival claim.

The fresh qualification ISO replay passed on its first attempt; read-only
release/git/GH and all 53 retained-input checks plus strict syntax were replayed
before its own guard. Probe review verified 37 guest transfers and twenty native
loop checks. Qualification review verified 43 physical owner-command records,
745 transfers, 27 hidden ready/left pairs, 18 raw varstores, nineteen zero-write/
unmap samples and every BootNext/NVRAM delta. Both native suites passed all 630
tests with zero skips, including the unchanged timing bound.

The first local qualification review reached its map checks then raised
`ModuleNotFoundError: keyboard_vm` because its launch lacked os/ci on
PYTHONPATH. The same unchanged review code passed after setting
`$env:PYTHONPATH=(Join-Path (Get-Location) 'os/ci')` and rerunning the local
review. No workflow or VM was rerun, no pushed-tree or check was changed, and
the actual keyboard_vm.loaded_map function checked all six recovery maps.
The private invocation and log hashes are recorded in
`14zze-round/local-review-invocation.json`.

Complete closing history: **157/157 IDs**. Package minutes **2474 / 2750**; added **148** this round. Counts **34 probes / 21 qualifications** (last caps 34/21). Organization free **1237**, reserve **150**. The saved last-dispatch package/organization comparison passed; the complete per-job charge rules and response hashes are in ledger.json. November remains free-minutes-only: no paid budget read or paid overflow; local-hook privacy reservations stay zero. No further dispatch is authorized.

Actual receipts are in `os/manifest/ci/14/14zze-round/round.json`. Raw consoles,
VCSA, screenshots, varstores and owner diagnostics remain only in private retained
artifacts/local evidence; they are not committed. The whole report's outstanding
physical release gates and the existing For package 15 list still apply.

### Not verified / JUDGMENT-CALL / PLAN-GAP / open questions

Fresh same-head native and VM acceptance passed. The fix changes
verification only. All physical release and followability gates remain open;
the product is **NOT RELEASED**. PR #13's readiness gate is met after the closing
local checks; merging remains the owner's decision. No additional run is
authorized: both dispatch caps are exhausted.

## 14zzd REPORT: manifest-only fixtures; STOP, no rerun

**Disposition:** [probe 33](https://github.com/Ares-Empire/AresOS/actions/runs/41363231606) **failure**, once on pushed head `dda72ed8a5bdb038d953f950f76c66fc37297115`. **Acceptance is not
met**: probe 33 passed all 627 native tests, then owner_vm.main refused Host walk is stale before guest boot. Read-only Git checkout-filter replay proves the PowerShell test source binding is LF while its declared checkout is CRLF. Qualification 21 was not dispatched. No further push, probe, qualification or rerun was attempted.
PR #13 remains draft. This STOP report, ledger and curated diagnostics receipts
are committed **locally only**. No merge, image build or publication occurred.
Physical release is **NOT RELEASED**.

### Done

`os/tests/owner_bundle_fixture.py` copies only the reviewed SHA256.json entries
plus SHA256.json and SHA256SUMS, checking the paths, manifest agreement and file
hashes. It never copies a directory tree. The common fixture builder validates
the result with the unchanged real checked_bundle implementation.

The fixture callers updated are test_owner_tools, test_owner_bootstrap,
test_owner_commands, test_owner_devices, test_owner_diagnostics, test_owner_entry,
test_owner_export and test_owner_setup_resume. The PowerShell copy stand-in
owner_fuse_shim also uses the same manifest-only copier. The remaining copytree
and copy2 references in the hidden-placement and setup-resume tests exercise
production placement/failure points; the bundle.build equality test exercises
the production generator. None constructs a fixture by copying the payload tree.

The new regression plants __pycache__/x.pyc and imports the real helper in the
source bundle. The copied bundle has exactly the manifest files, while the real
strict validator still refuses both a contaminated source bundle and a copied
bundle deliberately given an extra bytecode file. Install-resume direct helper
calls scope sys.dont_write_bytecode to that fixture, restoring it afterward,
matching the production entry point's existing -I -B without a global CI flag.

Only package 14's probe allowance changes, from 32 to 34. The qualification cap
stays 21 and the minute cap 2750. The extra probe allowance is not permission to
rerun a stopped run. No production payload, owner script, harness, workflow,
frozen image, release path, audit class, privacy rule, package 13 or operational
guide command changes. The payload fingerprint remains
`3e2c78ebedf7789b0616e7a4f21ad791d76784667344e76e97a1fbd95115a6fd`.

### Verified locally before the single push

The eleven affected modules ran with PYTHONDONTWRITEBYTECODE unset: **75
tests / zero skips** under normal Python in 595.827 s and the same
**75 tests / zero skips** with -B in 595.845 s. Both passed.
They include the fixture, bootstrap, command, device, diagnostics, entry, export,
setup-resume, media, guard and equality modules.

Full discovery under normal Python with that environment variable unset ran
**627 tests in 1995.985 s**: **618
passed**, 9 previously documented local host limitations,
**zero skips and zero unknown failures**. All 627 remain mandatory in native CI,
including the unchanged 30-second timing test. Native failure is a real STOP.
That test took **70.495 s** in this full run. This is the documented local host
timing limitation; the test, bound and native requirement are unchanged.

The final coordinator was `python -u -X utf8 .work/14/14zzd/final-local.py`.
It ran the qualification walk, probe walk, strict composed-command checks and
full discovery sequentially under normal WSL Python with
`env -u PYTHONDONTWRITEBYTECODE`, repository-local TMPDIR and safe PATH shims.
The exact commands are retained in preflight/final-local.py and whole.py.

The full stand-in walk passed all Linux stages, 27 hidden transitions, three
handoffs, all cluttered waits, thirteen real physical-typing cases and final
Windows markers. No wait or hidden input is uncovered. Strict checks passed
1,159 composed guest commands, 954 embedded Python bodies, twelve shell files
and 53 CI/overlay/owner Python files, refusing any Bash stderr. Local controller
tests: 31 passed. Windows copy/helper tests: seventeen zero-write refusals and
the successful checked copy/private entry point passed.

The actual read-only release/git/GH replay and 53 retained inputs passed; four
credential-only registry checks remain fail-closed in CI. Actual ISO inspection
passed on the first local attempt, rehashing all 9,068,650,496 bytes against the
pin and fresh official checksum. No Windows-specific CI behavior was changed.
Only completed SHA-verified duplicate ISO/squash cache bytes were reclaimed;
the master, canonical extraction, results and failed partials remain retained.

Source, command, result and private controller bindings are recorded in
`os/manifest/ci/14/14zzd-preflight/preparation.json`. Pinned local gitleaks 8.21.2
reported zero over pending files and full history before the push. The exact
range and actual push passed the installed aresync hook without bypass.

### Sizing / budget

Complete history: 154/154 IDs, **2310 consumed**, counts **32 probes / 20
qualifications**. Organization free minutes: **1401**, reserve **150**. The last
dispatch comparison is +9 package / +9 organization. Planned reservation is
72+240=312; 2310+312=**2622 <=2750**. Unchanged retained timing projection fits
VM 200 / qualification 240. November remains free-minutes-only, no paid budget
read, zero local-hook privacy reservations. Ledger and billing were rechecked
immediately before the only dispatch.

### Actual November round / independent review

[probe 33](https://github.com/Ares-Empire/AresOS/actions/runs/41363231606) **failure**. No run was rerun.

Native **627 tests passed in 163.918 s**, zero failures/errors/skips. The unchanged
30-second test explicitly passed. The real native loop-image test passed all
twenty checks, with zero helper mutations, protected fixture unchanged, all
mounts unmounted and loops detached. The deterministic real-kernel counter test
proved the old counting-fd query loses the press and the separate-client fix
preserves both events. Host capabilities, all four CI-only credential checks,
and ISO length/pin/fresh-checksum verification passed.

Artifact scan: 507 findings, comprising 507 exact pinned public ISO listing lines and 0 exact whole-line public kernel X.509 messages. Every occurrence is recorded by file, line, source-line SHA and approved-token cross-check in probe33-artifact-review.json. No ignore/rule/workflow changes.

Every completed job log was scanned; 4 findings were the exact pinned cosign-installer checksum class. Unknown findings: zero.

Complete closing history: **155/155 IDs**. Package minutes **2326 / 2750**; added **16** this round. Counts **33 probes / 20 qualifications** (last caps 34/21). Organization free **1385**, reserve **150**. The saved last-dispatch package/organization comparison passed; the complete per-job charge rules and response hashes are in ledger.json. November remains free-minutes-only: no paid budget read or paid overflow; local-hook privacy reservations stay zero. No further dispatch is authorized.

Actual receipts are in `os/manifest/ci/14/14zzd-round/round.json`. Raw consoles,
VCSA, screenshots, varstores and owner diagnostics remain only in private retained
artifacts/local evidence; they are not committed. The whole report's outstanding
physical release gates and the existing For package 15 list still apply.

### STOP diagnosis: Git checkout bytes were not covered locally

`owner_vm.main` refused `Host walk is stale` at line 1090, before Media.create,
any guest boot or live probe. Disposable file disks had been prepared; no guest
evidence/two-disk directory exists. The strict source-byte predicate was kept.

Read-only replay against the exact pushed tree checked all **195** host source
rows with `git show HEAD:path`; all match their bound Git-blob hashes. Replaying
`git cat-file --filters --path=path HEAD:path` found **one** mismatch:
`os/tests/owner-tools.Tests.ps1`. Its bound blob has 4,889 bytes, LF only; the
declared `.gitattributes` rule `*.ps1 text eol=crlf` yields 4,961 checkout bytes,
including 72 CRLF line endings. The content differs only by newline expansion.
The Windows working file remained LF, so both the local working-byte check and
Git-blob check missed the Linux checkout form.

Existing Linux Git 2.43.0 independently produced the same expanded bytes and
hash from a repository-local, isolated two-file fixture containing the exact
pushed attributes and PowerShell blob. Its first direct attempt could not read
the linked worktree's Windows absolute gitdir; no original Git metadata was
changed. Diagnostic commands/results are retained in stop-diagnosis.json and
linux-checkout-proof.json with their helper sources.

**Proven:** the pushed binding fails under its declared checkout filters, for
exactly that source row. **Inferred:** this explains the native assertion. The
assertion exported neither its failing path nor runtime hash, so the individual
native row cannot be independently read back. The other 194 rows pass the same
checkout-filter replay. This was a local preflight verification defect, not a
relaxation of the strict bundle validator. No pushed-tree fix, new push, probe
34, qualification 21 or Actions rerun was attempted.

### Not verified / JUDGMENT-CALL / PLAN-GAP / open questions

This round stopped without fresh VM acceptance. All prior physical
release and followability gates remain open; the product is **NOT RELEASED**.
The fixture correction does not claim laptop qualification or change a product
decision. Fresh live probe, complete owner route and review-fix VM acceptance
were not reached. The checkout-byte verification gap needs a future authorized
round; no additional run is authorized here. PR #13 remains draft.

## 14zzc REPORT: review fixes implemented; STOP, no rerun

**Disposition:** [Probe 32](https://github.com/Ares-Empire/AresOS/actions/runs/41356040290)
failed, once, on pushed head `b15d52f1a24c37fa4f4a3897919b88b591990c49`. **Acceptance is not
met**: probe 32 failed the native suite: 18 install-resume fixture errors at the strict bundle recheck; default bytecode writes contaminate the fixture bundle, unlike the production -I -B entry point. Qualification 21 was not dispatched. No further push, probe, qualification or rerun was attempted.
PR #13 remains draft. This STOP report, ledger and curated diagnostics receipts
are committed **locally only**. No merge, image build or publication occurred.
Physical release is **NOT RELEASED**.

### Done

The guide's single bootstrap block first copies the read-only stick into a
fresh private tmpfs directory. Only system tools then check the literal full
SHA256SUMS fingerprint, the exact file list, and every file's SHA-256. Only
afterward does Bash run the copied entry point; checked_bundle remains the
second layer. The Windows helper checks both manifests. The current full
fingerprint is `3e2c78ebedf7789b0616e7a4f21ad791d76784667344e76e97a1fbd95115a6fd`.
The copied bundle root is explicitly refused if it is a symlink, before cd.
A harmless real-Bash fixture demonstrated that the earlier recursive copy
preserved such a root link and returned success; the corrected command refuses
with zero payload execution. The command remains 13 lines, at most 107 columns;
the payload fingerprint and conservative timing geometry are unchanged.

Layout begin/revert change the running console map only. Saved system/X11 and
greeter settings stay at the last finished layout until explicit layout finish.
New layout abandon uses a fresh authenticated physical administrator session,
qualified deployments, disk identities and idle checks. It restores the finished
runtime map and clears/journals the pending trial. Stock retains its own finished
installer settings. Guide/card include the exact command and PASS line.

Installation journals its identity, stages privately, fsyncs and atomically
publishes. Matching interrupted phases resume; unknown partial state refuses.
Prepare journals before its first mutation and permits only precisely matching
already-completed effects on resume. STOP diagnostics now persist root-only
under /var/lib/ares/diagnostics and join the checked owner export/readback route.
The closing guide/card status names this round's actual result, retains the
completed Q20 history and keeps every outstanding physical gate.

The qualification adds a plain-US pending trial, QMP system_reset, next-boot
German checks on all six consoles, German password/sudo login, layout abandon
and guarded reboot. Every original subsequent stage remains, including US
failure/revert, US International proof/finish, German restoration, rollback,
keep-stock and final attached/detached Windows checks. The Audit class source
is unchanged; only the exact host-QMP shutdown origin joins the stop protocol.

### Verified locally before the single push

The full discovery ran **626 tests** in 2323.975 s: **617 passed**, 9 documented laptop/WSL limitations, **zero skips and zero new failures**. The same 626 tests, including the unchanged 30-second timing test, remain mandatory in native CI.

The real bootstrap tamper tests execute no payload for altered at, altered
owner.py, an extra file, a linked bundle root or a missing file. Session-loss/closed-login/stock-side
abandon, install/prepare failure injection, and failure -> export -> reboot
regressions pass. The initial suite exposed an old AST placement fixture;
it now executes the actual private-copy/atomic-publish/entry placement and
retains every original installed-path assertion. Its focused rerun passed,
then the full suite was restarted. No test bound or assertion was relaxed.

Local review also found that abandon's supported-profile check ran before its
known interrupted-finish branch, making the two-write intermediate unreachable.
That ordering is corrected: the exact mixed state needs the saved finish intent,
prior proof and deployment identity. A real first localectl write followed by an
abrupt-interruption injection now recovers; without the finish intent it refuses
with zero operational mutations. The final payload, full walk and whole suite
were regenerated/restarted after this correction; both superseded logs remain
in the private local work area.

The full stand-in walk passed ten Linux stage groups, 27 hidden transitions,
three handoffs, 154 cluttered waits with fresh authorized resyncs, 13 physical
typing cases and the final Windows markers. Real typing runs through the
layout adapter to recorded QMP key events. No wait/hidden input is uncovered.
Strict syntax checked all 1,159 composed guest commands and wrappers, 954
embedded Python bodies, 12 shell files and 53 CI/overlay/owner Python files;
any Bash parse stderr, including warnings, refuses. Local control tests: 31
passed. Windows copy/helper tests: 17 zero-write refusals plus successful copy
and entry point. Real read-only release/git/GH and all 53 retained-input steps
passed; four credential-only registry steps remain fail-closed in CI.

The actual ISO inspector replay verified all 9,068,650,496 bytes, pinned SHA-256
and a fresh official checksum. Attempt one hit the previously approved Windows
checkpoint Path.replace WinError 5; after the permitted 10-second wait, attempt
two passed in a fresh directory. CI inspector behavior is unchanged. No ISO
readers overlapped. Pinned gitleaks 8.21.2 pending/full-history zero and the
installed aresync exact-range privacy hook are required before the one push.

Source/results/control bindings are in
`os/manifest/ci/14/14zzc-preflight/preparation.json`. Pinned kbd 2.9.0-4.fc44 and
QEMU 8.2.2 source references and the unchanged Audit source hash are recorded
in source-proof.json. The frozen image, runtime, release scripts, keys, locks,
keyboard maps, privacy files, package 13 and package settings remain unchanged.

### Sizing / budget

Timing was calculated before limits changed, using retained Q17/Q19/Q20 stage
maxima. Each additional reset boot gets a whole slowest comparable boot; each
extra bootstrap line gets the original full typing/echo/record interval plus
timestamp granularity. VM 145.901 min +25% = **182.376**, exceeding 180 but fitting
the authorized **200**. Whole job +25% = **204.480**, fitting bound **240**. The
probe stays 72; job/guard use 240. Caps remain the last **32/21**, minute cap
2750. Projection sources and calculations are in 14zzc-timing/projection.json.

Complete history recomputation: 153/153 IDs, 2301 consumed, counts 31/20.
The prior qualification added 132 to both package and organization usage.
Organization included minutes: 590 used / 1410 left. Reservation 72+240=312
leaves more than the 150-minute reserve; 2301+312=2613 <=2750. November remains
free-minutes-only, no paid budget API read, zero hook privacy reservations.
Ledger and billing were rechecked immediately before every attempted dispatch.

### Actual November round / independent review

[probe 32](https://github.com/Ares-Empire/AresOS/actions/runs/41356040290) **failure**. No run was rerun.

Early STOP artifact scan: **0 findings**; ISO inspection was not reached, so no ISO/certificate exception was used. No ignore/rule/workflow changes.

Every completed job log was scanned: **zero findings**, no exception used.

Complete closing history: **154/154 IDs**. Package minutes **2310 / 2750**; added **9** this round. Counts **32 probes / 20 qualifications** (last caps 32/21). Organization free **1401**, reserve **150**. The saved last-dispatch package/organization comparison passed; the complete per-job charge rules and response hashes are in ledger.json. November remains free-minutes-only: no paid budget read or paid overflow; local-hook privacy reservations stay zero. No further dispatch is authorized.

Actual receipts are in `os/manifest/ci/14/14zzc-round/round.json`. Raw consoles,
VCSA, screenshots, varstores and owner diagnostics remain only in private retained
artifacts/local evidence; they are not committed. The whole report's outstanding
physical release gates and the existing For package 15 list still apply.

### Native stop diagnosis / unverified remainder

The native suite ran **626 tests in 218.621 s**, with **18 errors across five
install-resume test methods**, zero skips and 621 passing methods. All 18 stop
at owner.py:1150 with `Partial bundle or unexpected file`, before the intended
failure-injection point. The unchanged 30-second timing case itself passed;
there is no native timing exception.

The fixture passes its USB payload directly to `install()`. `media_module(payload)`
imports `media.py` before the second source-bundle validation. Native CI runs
normal Python, while my local whole-suite driver used **-B**. In an isolated
fixture, normal import adds `__pycache__/media.cpython-312.pyc` and reproduces
that exact refusal; **-B** adds no file and the bundle still validates. The
production entry already invokes **-I -B**. The native temporary directory was
not retained, so its exact added pathname is inferred from the matching trace
and this counterfactual, rather than a captured native directory listing.
See `native-stop.json` and its source/hash bindings for the executed diagnosis.

I missed this local/native invocation difference. The preflight did not faithfully
replay CI's interpreter mode; this is a verification gap, not an accepted host
limitation. No production code, test,
workflow, validator or ignore entry was changed after the CI stop. The isolated
import diagnostic ran no owner handler, device, credential or mutation command.
A future owner-authorized round should make the install fixture faithfully
model the production entry/private-copy boundary, replay normal CI invocation
locally, and keep the strict unlisted-file refusal. No fix or rerun is attempted
in this round.

The real native loop-helper test, registry/signature CI-only checks, ISO
inspection, Linux VM probe and qualification 21 were **not reached**. Host
capability proof passed. The new reset/German-login/abandon VM path and all five
review changes still require native and VM acceptance. PR #13 remains draft.
Both exported artifact and complete job-log scans found zero findings; raw
logs and 17-member diagnostics artifact remain private. Qualification 21 was
not dispatched, no Actions run was rerun, and no second push is made.

### Not verified / JUDGMENT-CALL / PLAN-GAP / open questions

Runtime-only trial was chosen over a new early-boot repair service: an unfinished
begin/revert never changes boot configuration. No image/service change is needed.
Only explicit finish persists a proved layout. Every original physical laptop,
USB restore/copy/forgotten-stick, firmware, keyboard, offline/notification and
followability gate remains outstanding. Backup stock keeps the installer's
layout; a US-then-rollback hardware run was not performed. This round
stopped without VM acceptance. No Gradle/Minecraft process was started. Never merge.

## 14zzb REPORT: sized limits; probe 31 and complete qualification 20 passed

**Disposition:** [Probe 31](https://github.com/Ares-Empire/AresOS/actions/runs/41321806985)
and [qualification 20](https://github.com/Ares-Empire/AresOS/actions/runs/41324240079)
both completed **successfully**, once each, on the same pushed head
`211df982b5bf080b0167b8fe6e8dd3c5eb264fe8`. Independent evidence review passed. **Acceptance is met** for this
package's VM scope. There was **one fast-forward push through the privacy hook**,
no rerun, no merge, no image build or publication. This closing REPORT, ledger
and curated evidence commit is **local only**. PR readiness: **ready for review** (PR #13).
Physical installation remains **NOT RELEASED**.

### Done: limits sized from retained runs

Only the owner-tools VM step and qualification limits changed: VM 106 to 180
minutes, job and guard qualification bound 160 to 220. Probe bound stays 72;
the other rehearsal modes, native/pinned-tools/ISO step limits, package cap 2750,
dispatch caps 32/21, organization reserve 150 and zero local-hook privacy
reservations are unchanged. Historical ordered job charges are unchanged; the
missing/unordered owner-tools fallback now reserves the full current 220.
No serial plan was built. Owner payload/fingerprint, bundle, runtime, image,
release, maps, owner scripts, guide/card and privacy rules remain frozen.

The projection was calculated before the limit changes. Each completed common
checkpoint uses the slower Q17/Q19 interval. Each of the three stock-tail logical
groups receives one entire slowest comparable ordinary stock-boot interval
(11.03 minutes, tools-stock); both final Windows markers each receive the
slowest observed Windows boot (0.92 minutes). One-time registry/image switch
and initial multi-login layout-failure work stays in the known total, but is
excluded from stock-tail comparables. The full source timestamps and SHA-256
bindings are in `os/manifest/ci/14/14zzb-timing/projection.json`.

The brief's parenthetical that neither run completed keep-stock is not literally
true: retained Q17 completed rollback-from-stock refusal, keep-stock and title;
its default-stock checkpoint was failure unwind. The projection still allocates
the conservative whole-boot allowances to all remaining groups.

| Stage / interval | Q17 min | Q19 min | Projection min |
| --- | ---: | ---: | ---: |
| `baseline-firmware` | 1.83 | 1.81 | 1.83 |
| `protected-second-install` | 22.52 | 24.98 | 24.98 |
| `boot-3-pre-login-reset` | 2.99 | 2.92 | 2.99 |
| `offline-first-stock` | 1.56 | 1.89 | 1.89 |
| `offline-roundtrip-unattended-windows` | 0.82 | 0.91 | 0.91 |
| `offline-roundtrip-detached-windows` | 0.81 | 0.91 | 0.91 |
| `tools-stock` | 9.12 | 11.03 | 11.03 |
| `prepared-unattended-windows` | 0.82 | 0.92 | 0.92 |
| `corrected-stock` | 16.48 | 21.10 | 21.10 |
| `aresos` | 14.04 | 17.94 | 17.94 |
| `aresos-intl` | 8.06 | 10.53 | 10.53 |
| `aresos-back-de` | 5.79 | 8.07 | 8.07 |
| `rollback-from-stock-refusal` | allowance | allowance | 11.03 |
| `keep-stock/title/reboot` | allowance | allowance | 11.03 |
| `default-stock-verification` | allowance | allowance | 11.03 |
| `final-unattended-windows` | allowance | allowance | 0.92 |
| `final-detached-windows` | allowance | allowance | 0.92 |
| Before VM | 17.43 | 15.42 | 17.43 |
| After VM | 0.12 | 0.25 | 0.25 |

VM total 138.05 minutes; with 25% margin 172.56, below 180. Slower pre-VM setup 17.43
minutes and post-VM work 0.25 give a full-job projection 155.73, or 194.66 with 25%
margin, below 220. The pre-dispatch round bound 2144+72+220=2436 fits 2750.

### Verified: local checks before the single push

- Affected regressions: 30 passed / 0.545 s, including three new retained-timing
  tests and preserved historical accounting/reservation refusals. Local artifact
  classifier 16/1.036 s, dispatch controls 6/0.007 s, local privacy 7/0.188 s and
  basic diagnostic collector 2/0.008 s passed, all zero skips.
- The entire local suite executed 600 tests in 1364.04 s (wrapper 1364.057 s): 591
  distinct passes and the same nine documented host limitations, zero skips and
  zero unknown failures. The unchanged 30-second timing case took 63.860 s on this
  laptop. Its assertion was not changed, skipped or marked; native CI remains
  mandatory. The other eight are the documented Pillow/ACL/privilege/DrvFS
  limitations, not native acceptance evidence.
- Physical stand-in walk: 9 cases, 973 commands, 23 hidden pairs, 3 handoffs,
  133 observer-authorized resyncs and 86 xHCI checks. Probe walk 7 commands.
  Strict composed-command checks: 980 commands/wrappers, 812 embedded Python,
  12 shell files and 52 Python source files, all passed.
- Fresh local read-only release/git/GitHub replay and 53 retained inputs passed
  before the probe and again before qualification. Each fresh ISO replay passed
  on its first attempt: 9,068,650,496 bytes, pin and fresh official checksum equal.
  Only completed SHA-verified duplicate replay caches were removed; original
  inputs, canonical files and diagnostic records were preserved.
- Pinned local Gitleaks 8.21.2 full history and pending scans were clean before
  the single fast-forward push. The installed pre-push hook and exact-range
  checker 8.30.1 passed, with no skipped-personal-terms warning and no hook bypass.
  No private terms, raw console/screenshot, token, unredacted scanner finding or
  certificate fingerprint value is included in this commit.

### Verified: actual probe and qualification

- Probe 31: **600 native tests / 142.001s / zero skips**; the mandatory unchanged
  30-second timing test passed. Actual kernel negative control saw 0 press / 1
  release with the old getter, and 1 / 1 with the separate-client fix. Twenty
  native loop checks, 37 SHA/syntax-verified transfers, one AT keyboard boot,
  57 static key mappings and seven healthy xHCI checkpoints passed. Raw replay:
  three protected captures, four zero-write/unmap samples, three BootNext
  replays and two NVRAM/all-variable delta replays.
- Qualification 20: **600 native tests / 202.315s / zero skips**, mandatory timing
  case and real-kernel negative/positive counter proof passed. Twenty native
  loop checks, 38 physical owner-action records and **633 SHA/syntax-verified
  root-only tmpfs transfers** passed. Every one of the **23 hidden-input
  readiness/completion pairs** and pre-Enter/counter proofs passed, without
  recording values. All three public handoffs passed. Five distinct prompt
  waits each used one observer-authorized Enter resync. Nine actual AT keyboard
  boots each checked 57 mappings; all **104** xHCI health checkpoints were healthy.
- Independent replay of actual raw qualification files passed: **16 protected
  captures, 17 zero-write/unmap samples, 16 decoded-varstore/BootNext replays,
  15 NVRAM rule replays and 15 complete variable-delta recomputations**. This
  includes `default-stock` and both final Windows stages, not just the prior tail.
- Complete log scans passed with **four** approved pinned cosign action checksum
  occurrences in each run. Probe artifacts: **509 = 507 exact public ISO-name
  lines + two whole kernel certificate messages**. Qualification artifacts:
  **527 = 507 ISO lines + 20 whole kernel certificate messages**. Every occurrence
  is recorded by file, line, label and whole-line SHA in the artifact review.
  Whole-source classification and the redacted token-position cross-check passed;
  **zero unknown findings**, zero native-log findings, no new ignore/rule entry.
- The first local qualification reviewer glob selected 12 files: three handoff
  receipts plus their transport and public-echo companions. The selector now
  requires `-handoff-<integer>.json`. The assertion still requires exactly three
  receipts and every original field check; every other AST node is identical.
  **Six tests / 0.037s** cover the real 12-file set and missing/extra/wrong-field
  refusals. Original dispatch-time bytes, the corrected reviewer and tests are
  archived. The complete local acceptance gate then passed. This was a zero-cost
  read-only reviewer correction; no CI rerun or pushed-tree change.

### Acceptance evidence for every remaining stage

| Stage | Retained qualification 20 evidence |
| --- | --- |
| Offline install / first stock boot | `owner-tools-result.json` records offline install, hardware boot, Windows round trip, hot-plugged tools, removal before every reboot, prepare, zero-mutation rerun, unchanged state after network and export. |
| Plain US failure and revert | `layout-us-begin`, rejected second-console login, `layout-unproved-reboot-refusal` with zero mutations, `layout-us-revert`, fresh German login, `layout-reverted-proof` and `layout-revert-finish` passed. |
| US International success | `layout-intl-begin`, fresh tty4 password login, `layout-intl-proof`, finish, subsequent `aresos-intl` system check, tty3 login/password sudo and physical foot typing passed under `us-intl`. |
| Back to German | `layout-de-begin`, fresh tty4 login, `layout-back-de-proof`, finish and subsequent `aresos-back-de` system/console/foot checks passed under `de`. |
| Rollback | `owner-rollback` passed on AresOS, followed by refreshed title and reboot. `rollback-stock` common boot verified the saved stock identity and physical checks. |
| Guard on booted stock | `rollback-from-stock-refused` returned the expected STOP with **zero mutations**. |
| Keep stock / default | `owner-keep-stock`, refreshed `owner-keep-stock-title` and reboot passed. `default-stock-check` and `default-stock-default-verified-deployments.json` confirm the saved stock identity first, booted and pinned, with no staged work; console, login/sudo, greeter and foot checks passed. |
| Final Windows | `final-unattended-windows` and `final-detached-windows` marker boots both completed, with tools absent and raw protected-disk, BootNext, NVRAM and full-variable audits passed. |

The completed VM step took **117.67 minutes** (below 180); setup before it took
**13.68 minutes**, post-step work **0.15 minutes**, and the whole job **131.50
minutes** (below 220). Full observed stage timings and action result/hash bindings
are in [terminal facts](../../os/manifest/ci/14/14zzb-round/terminal-facts.json).
The acceptance summaries and private artifact identities are archived under
[this round](../../os/manifest/ci/14/14zzb-round/round.json); raw consoles,
screenshots, varstores and diagnostics remain only in the retained private artifacts.

### Budget: complete history and organization comparison

| Point | Added package minutes | Package total / 2750 | Organization used / free |
| --- | ---: | ---: | ---: |
| Before this round | 0 | 2144 | 433 / 1567 |
| Probe 31 | 25 | 2169 | 458 / 1542 |
| Qualification 20 | 132 | **2301** | **590 / 1410** |

History completeness is proven against **153/153 IDs over two pages**. Counts
are **31 probes / 20 owner-tools qualifications**, below caps **32 / 21**.
The package has **449 minutes left**; organization reserve stays **150**.
Saved pre-qualification package and organization totals both increased by
**132**, so there is no undercount. Earlier ordered job charges did not change
in this limit-only round; the historical probe-29 accounting correction remains
recorded. Each job's charge rule and source-response SHA are in the ledger.
November is **free-minutes-only**: no paid budget API read, no paid overflow,
zero paid Actions-minute quantity/amount. Push and closing reservations remain
zero under 14zw's local-hook decision. No further dispatch is authorized.

Closing local checks passed: pinned Gitleaks **8.21.2** reports zero full-history
and pending findings; the hash-before-path equality test and `git diff --check`
passed, and all runtime, owner payload, release, configuration, workflow and
privacy-rule paths are byte-for-byte unchanged from the qualified head. PR #13
is ready for review, still open and unmerged. The report commit stays local.

### Not verified / release gate

No real laptop, physical USB restore/copy, physical installation, physical F12
boot, firmware, hardware keyboard or laptop-side followability gate was exercised.
The existing INSTALL, EMERGENCY and RELEASE-GATE remain unchanged and truthful;
physical release remains NOT RELEASED. The existing **For package 15** list below
still applies. The nine local-host limitations remain documented; native CI ran
all 600 tests without skips. No Gradle or Minecraft process was started.

### JUDGMENT-CALL / PLAN-GAP / open questions

The 180/220 limits are the integrator's decision. The conservative comparable
tail selection and the exact Q17 completion correction are documented above;
the resulting margin fits before any dispatch. No product choice, audit,
predicate, retry policy or owner command changed. No serial plan was implemented.
There is no remaining VM acceptance gap and no further round is needed for this
brief. Owner/integrator review and the physical release gates remain; never merge.

## 14zza REPORT — whole-source review fixed; qualification 19 reached rollback, then step deadline

**Disposition:** **No push and no new probe.** The corrected local gates accepted
retained [probe 30](https://github.com/Ares-Empire/AresOS/actions/runs/41301148135).
[Qualification 19](https://github.com/Ares-Empire/AresOS/actions/runs/41305049425)
ran once on the same pushed head `10921f81f481bd2b2c7bfb2da9e13deabdb1267f` and ended in **failure** when its
unchanged **106-minute VM step limit** expired. The run is terminal, diagnostics
are exported and scanned, and there is **no rerun**. Acceptance is false;
PR #13 stays draft. This REPORT/ledger/evidence commit is **local only**.

### Done — local tooling, whole lines, exact token positions

- The fix lives in `.work/14/14zza/classify.py`; its reviewed copy is archived
  [here](../../os/manifest/ci/14/14zza-round/classify.py). No pushed-tree change,
  owner-script/payload/fingerprint change, workflow change, image rebuild,
  publication, merge or force push was made.
- Each finding reads its actual complete source line at the reported file and
  line, classifies that complete line, and records the line SHA-256. The
  redacted `Match`/`Secret` only cross-check the reported secret's position
  **inside** the approved token. No class depends on a redacted excerpt's quote.
  Missing/unreadable/non-UTF8 lines, unknown whole lines, unrelated files,
  malformed metadata or positions outside the token stop the review.
- Kernel messages retain the exact whole-line 14v form and 40-hex fingerprint
  token. The ISO class binds the exact **507 public symlink-name lines** and
  target tokens to the retained, hash-pinned listing and earlier accepted scan.
  Cosign retains exact whole checksum lines, known values from the pinned action
  source, job/run/head identity and a unique complete matching action block in
  step and combined logs. No new scanner rule, ignore entry or allowlist exists.
- Source inspection of Gitleaks **8.21.2** confirmed its fixed-size file chunks
  and previous-LF column anchor. The local cross-check replays those byte
  coordinates, including a truncated fingerprint excerpt at a chunk boundary.
  Source URLs and downloaded hashes are
  [recorded](../../os/manifest/ci/14/14zza-round/upstream-sources.json):
  [chunk size](https://raw.githubusercontent.com/gitleaks/gitleaks/v8.21.2/detect/detect.go),
  [directory scanning](https://raw.githubusercontent.com/gitleaks/gitleaks/v8.21.2/detect/directory.go),
  [column calculation](https://raw.githubusercontent.com/gitleaks/gitleaks/v8.21.2/detect/location.go).
- A post-run local lookup initially assumed the combined log's numeric prefix
  was `0_`; qualification 19 supplied **`1_`**. The local reviewer now requires
  exactly one numeric-prefix file with the exact API-confirmed job name and the
  unique full pinned-action block. Missing/duplicate context still refuses.
  This was a read-only review correction after the CI stop, not a CI retry.
  The original dispatch-time classifier, tests and binding seal are retained
  alongside the post-review versions; the old dispatch seal was not rewritten.

### Verified — actual checks and retained evidence

- Before dispatch: **14 classifier tests / 1.025s**, including probe 30's exact
  refused row, probe 29's accepted 509 findings, their full-log findings, and
  refusal cases. **Four source-binding/control tests / 16.794s** proved that a
  changed implementation, wrong local head or changed local helper blocks use
  of the old probe. Local head `e3f4c93` differs from the pushed head only in
  the owner brief and prior closing REPORT/ledger/manifests.
- The first local coordinate check exposed the scanner's column convention.
  An initial negative unit fixture also used columns that actually selected a
  public fingerprint fragment in the second chunk. The fixture was corrected
  to select bytes outside the token, preserving its refusal assertion.
  Post-review **16 tests / 1.019s** pass, now also covering qualification 19's
  real `1_` log and missing/ambiguous combined-log refusals.
- Probe 30's entire local gate was rerun on retained inputs and passed:
  **597 native tests / 143.006s / zero skips**, mandatory unchanged timing test,
  real-kernel counter proof, 20 native loop checks, 37 verified tmpfs transfers,
  AT keyboard mappings, xHCI health and independent raw safety audits.
- Fresh local release/git/read-only GitHub replay, 53 retained inputs and ISO
  inspection passed. The ISO replay verified **9,068,650,496 bytes** against the
  pin and fresh official checksum on its **first attempt**. Only completed,
  SHA-verified duplicate caches were unlinked; master/canonical files, results
  and diagnostics remain. Strict checks passed for **980 commands/wrappers,
  812 embedded Python scripts, 12 shell files and 52 Python source files**.
- Pinned local gitleaks **8.21.2** reports **zero full-history findings**. Fresh
  validation of the existing pushed head's actual hook/exact-range proof passed
  with checker **8.30.1**, no skipped-personal-terms warning. No terms were read
  or recorded by the agent. No new push, hook bypass or GitHub privacy run.
- Actual qualification native suite: **597 passed / 202.891s / zero skips**;
  its native log scan has zero findings and its mandatory 30-second case passed.
  Actual kernel negative control again saw **0 press / 1 release** on the old
  counting client and **1 / 1** on the separate-client fix.
- Qualification privacy review passed: **523 artifact findings = 507 public
  ISO-name lines + 16 exact kernel certificate messages**, and **four** exact
  cosign full-log findings. Every kernel occurrence's file, line, label and
  whole-line hash is [recorded](../../os/manifest/ci/14/14zza-round/artifact-review.json).
  Each secret position lies inside its approved token. No raw console, screenshot,
  certificate fingerprint value, secret value or unredacted finding is committed.
- Independent replay of the **available** raw qualification evidence passed:
  **12 protected captures, 13 zero-write/unmap samples, 12 varstore/BootNext
  replays and 11 NVRAM/all-variable delta replays**. These cover completed
  checkpoints through `aresos-back-de`; they do not establish the uncompleted
  final tail. [Raw-audit summary](../../os/manifest/ci/14/14zza-round/independent-audits.json).

### What qualification 19 proved, and the exact stop

Retained owner result records prove install, prepare/rerun, network-boundary
records, export, real login, signature verification and switch. They also prove:

- **Plain US failure/revert:** second-console login was rejected as intended;
  unproved reboot refused without a mutation, then revert, fresh German login,
  proof and finish passed.
- **US International success:** `layout begin us-intl`, a fresh tty4 password
  login, physical layout proof and finish passed. The subsequent AresOS boot's
  system check and physical foot typing passed with profile `us-intl`.
- **Back to German:** fresh tty4 login/proof/finish and the next AresOS boot's
  check, tty3 login/password sudo and physical foot typing passed with `de`.
- **Rollback:** the owner `rollback` action passed, the staged-state assertions
  and refreshed title preceded reboot, and the recovered stock snapshot is
  booted/pinned with the **same checksum, serial1 and stateroot `default`** as
  corrected stock, transaction None and nothing staged. Its fresh tty3 login
  passed in **10.020s**, within the 30-second half-timeout budget.

The job log then reports the configured 106-minute step timeout at
**14:10:17 UTC**. The last sudo password window on recovered stock has exact
**33 presses / 33 releases, zero repeats/drops**, matching 66 sent events;
the counter result was written about **14:10:12 UTC**. Its subsequent public
completion-observer script had passed root-only staging, SHA and syntax checks,
but there is **no returned completion observation**. Archive timestamps have
two-second granularity and a final transport write appears during termination
grace. They do not prove the observer finished or that sudo stayed stuck.

**Proven cause:** the global step deadline terminated the run near that last
completion observation. **Not proven:** dropped input, a stuck reader, a new
owner-tool refusal or a new prompt-predicate failure. The last event counts
support no input-loss diagnosis. There is no recorded visual-taint flag.
This is a **qualification runtime/step-budget limitation**; no timeout was raised
and no product or harness fix was inferred. No final `owner-tools-result.json`
was produced. [Diagnosis and source hashes](../../os/manifest/ci/14/14zza-round/diagnosis.json).

### Remaining tail — plan only, owner/integrator decision required

Not verified: post-rollback sudo completion and `common_boot` check/public typing/
homebrew/greeter; rollback-from-stock refusal; `keep-stock`, refreshed title and
reboot; default-stock verification; final unattended/detached Windows checks;
their final protected-disk/NVRAM/BootNext audits and aggregate acceptance.

There is no demonstrated new console-typing failure. As a possible future serial
plan for these remaining state/boot stages: deliver the **same installed owner
commands** and existing audit scripts through the bounded SHA-checked serial
transport; run owner commands inside an already proven `ares-recovery` physical
logind/tty/sudo session, not an ordinary root serial shell. First prove that all
existing session facts survive that route; inability to do so is a PLAN-GAP,
never a session-check exception. Keep required physical layout/authentication
proofs and hidden-input counters; no secret may enter serial text or staged files.
Then run the stock rollback refusal, keep-stock/title/reboot, default-stock
identity/keyboard/homebrew checks and the two existing unattended Windows marker
paths, retaining every audit and tools-stick removal rule. No assertion is
silently dropped or replaced. A zero-cost walk must establish coverage and
runtime before a future dispatch. **This plan was not built**; an alternative
step-limit decision also belongs to the owner. The present round is over.

### Trusted ledger and release state

| Item | Minutes / count |
| --- | --- |
| Start of 14zza | 2,022; 30 probes / 18 qualifications |
| New push / new probe | 0 / 0 |
| Qualification 19 | 122 rounded minutes; normal job interval |
| Closing package | **2,144 / 2,750**; **30/32 probes, 19/21 qualifications** |
| Complete history | **151/151 unique IDs**, two pages |
| Organization | **1,567 included minutes left**, reserve150; no paid budget read |
| Push / closing privacy reservations | **0 / 0**, per14zw |

The before-dispatch package/organization comparison was **24 / 24**; the closing
comparison against that saved authorization is **122 / 122**. Every job's rule
is retained in the [trusted ledger](../../os/manifest/ci/14/14zza-round/ledger.json).
At least one further qualification round is needed; no upper bound is inferred
and **no further dispatch is authorized**. INSTALL/EMERGENCY/release gate and the
existing For-package-15 list remain unchanged and truthful: physical laptop work
is out of scope and stays **NOT RELEASED**. No real hardware, system settings,
software installation or credential scope was touched. PR #13 remains draft.

**JUDGMENT-CALL:** none beyond the integrator-approved local classification rule.
**PLAN-GAP/open question:** the observed route exhausted the fixed106-minute VM
step before its final tail. Decide the future runtime/transport plan; no limit,
session guard, typing assertion or audit was weakened in this round.

## 14zz REPORT — accounting restored; probe 30 passed; local artifact-review STOP

**Disposition:** One fast-forward push through the installed privacy hook to
`10921f81f481bd2b2c7bfb2da9e13deabdb1267f`. [Probe 30](https://github.com/Ares-Empire/AresOS/actions/runs/41301148135)
completed **success**. Its post-run local artifact reviewer then refused a
redacted-match shape, so **qualification 19 was not dispatched**. Both the
workflow and the local review are terminal. Acceptance is false; PR #13 remains
draft. No rerun, second push, merge, image publication or privacy-rule change.
This closing REPORT/ledger/evidence commit is **local only**, under 14zv/14zw.

### Done — fail-safe accounting and pinned public checksums

- `job_accounting` uses a job interval only when it encloses every ordered
  step. Otherwise it selects the widest ordered supported job/step span.
  Missing or unordered steps cost the full approved dispatch bound: **72 probe,
  160 qualification**. A negative interval is never clamped to one minute.
  Every job records its rule, charge and response hash; skipped jobs cost zero.
- The whole history was recomputed. **Only one job changed:** probe 29,
  run `41290621860`, job `124800927513`, **1 → 26 minutes**, using the retained
  first-step start `08:51:56Z` to job completion `09:17:30Z` on 1 November.
  The restored pre-round total is **1,998**, replacing the untrusted 1,973.
  [Accounting evidence](../../os/manifest/ci/14/14zz-round/accounting.json)
  lists the changed job and every job's rule is in the complete ledger.
- Before dispatch, package usage is compared with organization usage since
  the preceding dispatch. A gap greater than five minutes stops it. The legacy
  baseline was recomputed **once** under the new policy and saved; later
  responses cannot silently reprice it and erase undercount evidence.
  Complete histories, run identity, dispatch count, billing period, ordered
  observations and nondecreasing totals are required. The pre-probe increase
  was **5 package / 5 organization**; the closing observation is **24 / 24**.
- Package 14 dispatch caps are **32 probes / 21 owner-tools**; cap **2,750**,
  reserve **150**, push/closing privacy reservations **0** under 14zw. Package
  13 settings, owner payload/fingerprint, image/runtime, guides and workflows
  were verified unchanged by this round.
- The third full-log class requires exactly
  `RELEASE_COSIGN_PUB_KEY_SHA='<64 lowercase hex>'` in the pinned
  `sigstore/cosign-installer@398d4b0eeef1380460a10c8013a76f728fb906ac`
  step, with the value verbatim in its public
  [action.yml](https://raw.githubusercontent.com/sigstore/cosign-installer/398d4b0eeef1380460a10c8013a76f728fb906ac/action.yml).
  Its fetched SHA-256 is recorded in
  [source.json](../../os/manifest/ci/14/14zz-cosign/source.json). The template
  and two public checksum entries reconstruct those exact source bytes; the
  upstream license is retained. Combined-log matches must lie inside the
  unique complete matching step block. Four retained 14zy findings and the
  four new probe-log findings pass; other shapes/values/locations refuse.
  No ignore entry, allowlist, scanner rule or workflow was added or changed.

### Verified — actual results

- New regressions: **11 accounting/safety-net + 4 cosign**. The affected suite
  passed **60 in 4.656s**; legacy accounting fixture checks **20 in 0.601s**;
  controller/privacy/basic checks **6 / 7 / 2**. Three legacy fixture modules
  needed valid step intervals for their existing job-cost assertions; the
  first superseded whole run exposed them. Assertions were preserved.
- Final local whole suite: **597 executed in 1409.761s; 588 distinct passes,
  the same nine documented host limitations, zero skips, zero unknown
  failures**. Its unchanged 30-second case took **70.02388832899987s** on this
  host. Missing PIL, privileged fixture refusals, DrvFS mode behavior and that
  timing overrun are documented local limitations, never native exemptions.
- Actual probe native suite: **597 passed in 143.006s, zero skips**. The exact
  mandatory 30-second test explicitly passed. Native log scan: **zero findings**.
- Real-kernel uinput negative control: **0 press / 1 release** with the old
  counting-client getter; **1 / 1** with the separate-client fix, zero repeat
  or drops. Native proof ran; the guest fallback was not needed.
- Stand-in walk: nine real physical-typing cases, **973 commands**, 23 hidden
  pairs, three public handoffs, 133 bounded authorized resyncs and 86 health
  boundaries; probe route seven more commands. Strict checks passed for
  **980 composed commands/wrappers, 812 embedded Python scripts, 12 shell
  files, 52 Python source files**, including a fresh pre-qualification replay.
- Both actual local ISO replays passed on their first attempt, verifying
  **9,068,650,496 bytes** against the pin and fresh official checksum.
  Read-only release/git/GitHub replay and 53 retained inputs passed before
  push and again during probe preparation. The four CI-only credential checks
  passed in the actual probe. Completed duplicate caches were hash-verified
  before unlink; master ISO, canonical squashfs, receipts and diagnostics stay.
- The pre-commit staged-blob check caught CRLF in one archived local helper.
  It was normalized to LF, hash bindings refreshed, and local commit checks
  repeated before committing. Production code did not change in that recovery.
- Probe evidence: **20 native loop checks**, zero helper mutations, protected
  fixture unchanged, all mounts/loops cleaned; **37 SHA/syntax-verified tmpfs
  transfers**; actual AT keyboard boot with **57 mappings**, seven healthy xHCI
  receipts. Independent raw replay passed **3 protected captures, 4 zero-write/
  unmap samples, 3 BootNext/varstore replays and 2 NVRAM/all-variable replays**.
- Pinned local **gitleaks 8.21.2: zero pending/history findings** before push.
  Manual exact-range and actual installed pre-push hook checks both passed,
  checker **8.30.1**, no personal-terms-skipped warning. No terms were recorded;
  `--no-verify` was never used. Fresh exact-head hook proof preceded dispatch.

### STOP diagnosis — local reviewer metadata, not a new artifact class

The pinned artifact scan has **509 findings**: **507** in the public ISO file
listing, byte-identical to the retained probe 29 listing, and **two** in
`two-disk/live-ui-probe-boot-console.txt`. At lines **529 and 554**, both complete
source lines match the already approved 14v kernel X.509 certificate message
form and label **Fedora kernel signing key** with a 40-hex fingerprint.
Each source-line hash and label is recorded in
[artifact-review.json](../../os/manifest/ci/14/14zz-round/artifact-review.json).
No raw console, fingerprint value, token or unredacted scanner finding is
committed here.

The automatic reviewer first accepted each **whole source line**, then applied
an additional existing `Match` assertion. Line 529's redacted match is
`key: REDACTED'`; line 554's is `key: REDACTED`, without the closing quote.
That latter metadata fails the required `key: REDACTED'` pattern. This is the
**proven cause of the local refusal**. The exact reason the scanner selected
different substring boundaries is not established; no inference about a new
credential is needed or made. Source inspection found **zero findings outside
the existing approved classes**, and all four full-log cosign findings passed.

The automatic artifact receipt was **not overwritten or bypassed**. Its
fail-closed refusal remains latched; no qualification authorization or POST was
attempted. No after-push code/ignore/rule change, retry or rerun was used to
continue. This is a **local post-run reviewer defect**, not an owner-tool or
physical-console failure. The qualification-19 typing-stop serial-plan trigger
did not occur. An integrator decision and a regression based on these exact two
redacted rows/source lines are needed before a future round; no fix was built.

### Ledger, remaining work and release gate

The closing history proves **150/150 unique IDs over two pages**. Trusted
package usage is **2,022/2,750**, counts **30/32 probes, 18/21 qualifications**.
Probe 30 costs **24 minutes** under the normal enclosing-interval rule; the
organization rose by the same **24**, from 287 to 311 used. **1,689 included
organization minutes remain**. The November guard read no paid-budget amount,
counted no paid minutes, and observed zero net paid Actions usage. Reserve 150,
push 0 and closing 0 remain the 14zw settings. The closing guard reserves zero
new work; at least one further same-head probe/qualification round is needed,
with no reliable upper bound inferred. No further dispatch is authorized.

**Not verified:** qualification 19, installed US International success/back to
German, rollback, keep-stock and final Windows acceptance on this head. The
fresh local qualification preparation passed, but cannot substitute for the
withheld real run. INSTALL/EMERGENCY/release gate retain their physical-owner
checks and NOT RELEASED status. PR #13 remains draft. No real laptop hardware,
disk, settings, credential scope or software installation was touched.

**JUDGMENT-CALL:** the new accounting/classification decisions are exactly 14zz;
no new product decision was made. **PLAN-GAP/open question:** settle the local
reviewer's extra redacted-match quote requirement for the already approved
whole-line class. The run is over; this closing commit stays local for the
next authorized round's push.

## 14zy REPORT — counter fix proved; financial and full-log privacy STOP

**Disposition:** One fast-forward push through the installed privacy hook to
`cbaa985ed81eaea268d6f261cb212048da69d9cc`. [Probe 29](https://github.com/Ares-Empire/AresOS/actions/runs/41290621860)
completed successfully; its native/artifact/counter/disk/firmware checks passed.
[Qualification 18](https://github.com/Ares-Empire/AresOS/actions/runs/41292826573)
was dispatched once on that same head, then **cancelled by this agent before its
native/VM stages** after discovering malformed budget timestamps. Both runs are
terminal; diagnostics are exported. A subsequent full-job-log scan found four
additional unclassified findings. Acceptance is false; PR #13 remains draft.
**No rerun, second push, merge, publication or guard/ignore change. This closing
report/ledger/evidence commit is local only.**

### Done — separate evdev clients and complete audit

- `owner_key_counter.released(device)` opens and closes a separate evdev client
  for every `EVIOCGKEY`; it never duplicates or queries the counting fd.
- Startup identity/repeat getters use a query-only fd before the counting
  client opens. Both character-device checks remain. `observe` only selects,
  reads and closes its counting fd; state queries receive the device path.
- The login visibility audit checks state by a separate open before its own
  event-reading client opens. Its later observations read events and inspect
  `/proc`/tty state, without evdev getters.
- Boot keyboard identity, repeat and static `EVIOCGKEYCODE` getters use their
  own query-only client. No `EVIOCGLED`, `EVIOCGSND` or `EVIOCGSW` exists in the
  active harness. Tty LED/termios observations are on tty fds, not evdev clients.
- Only the deliberate real-kernel negative control queries a counting fd.
  The exact old ioctl is bound to retained 14zx source and checked by AST.
  **The strict press/release comparison is unchanged; no tolerance was added.**
- New `owner_counter_kernel.py` creates a private uinput F24 device, proves the
  press is queued before querying, and observes it before emitting release.
  Native CI runs it when `/dev/uinput` exists; otherwise a mandatory first-live-
  guest proof runs before hidden typing. Missing/refused proof stops the run.
  The native receipt and VM attestation are head-bound. No laptop input device
  was accessed, and no package was installed locally.
- The active after-run label reads the real accepted native test count. It
  printed **582 native tests/0 skips**, replacing the stale `native569` label.
  Historical archived controls are preserved.

### Verified — actual checks, with local limitations stated

- Affected local command: existing WSL, workspace `TMPDIR`, refusal-shim `PATH`,
  `PYTHONPATH=os/ci:os/tests python3 -B -m unittest test_owner_counter_flush
  test_owner_key_counter test_owner_ps2 test_owner_login -v`: **46 passed in
  13.650s**. Seven new models cover independent opens/close-on-error, all reader
  call sites, exact old ioctl, mandatory native/guest routing, wrong receipts,
  native refusal and the unchanged exact comparison.
- The initial local fixture test attempted Linux git on this Windows worktree
  and failed; it now reads a hash-bound extraction of the actual old function.
  No counter assertion was weakened. The preparation adapter initially rejected
  harmless model stdout after `OK`; its summary parser was corrected.
- Full local suite: **582 executed in 1416.373s; 573 distinct passes, the same
  nine documented host limitations, zero skips, zero unknown failures**. The
  unchanged 30-second timing test took **68.67903124300005s** here. PIL absence,
  refused privileged fixture operations, DrvFS mode behavior and that timing
  limit remain local limitations, never native exemptions.
- Actual native probe: **582 passed in 200.567s, zero skips**, including the
  explicit unchanged 30-second case. No host exception was applied in CI.
- Stand-in route: real typing chain, nine physical cases, 973 commands, all
  remaining stages and both Windows branches, 133 bounded observer-authorized
  resyncs, 23 hidden pairs, three public handoffs, 86 health boundaries. The
  probe walk adds seven commands, including mandatory proof routing. Strict
  checks passed for **980 commands/wrappers, 812 embedded Python scripts,
  12 shell files and 52 Python source files**, before push and again before
  the planned qualification. Controller/privacy/diagnostic suites passed 6/7/2.
- Both actual ISO replays verified all 9,068,650,496 bytes against the pin and
  fresh official checksum. Release/git/read-only-gh and 53 retained zero-cost
  inputs passed; the four CI-only credential checks stayed fail-closed and
  passed in the probe. The qualification replay hit WinError 5, then its free-
  space guard after a partial cache; immutable-adapter attempt 3 passed after
  the authorized 20-second wait and SHA-verified duplicate-cache cleanup.
  Master ISO, canonical extraction, receipts and failed diagnostics remain.
  The Windows holder was not identified because the fresh-path retry passed.
  No Linux inspector behavior, OS setting or installed software changed.
- Native deterministic proof ran on **7.0.0-1017-azure**: old getter
  **0 presses / 1 release**, comparison false; separate-client getter **1 / 1**,
  comparison true, zero repeat/drops. This is real kernel evidence, not a mock.
  The guest fallback was model/syntax checked and was not needed on this runner.
- Probe evidence: 20 native loop checks with zero helper mutations and cleanup,
  37 verified SHA/syntax tmpfs transfers, one actual AT keyboard boot/57 static
  mappings, seven healthy xHCI receipts. Independent replay passed three
  protected captures, four zero-write/unmap samples, three raw varstore/BootNext
  replays and two exact NVRAM/all-variable delta replays.

### STOP / PLAN-GAP — timestamps and a guard that clamps negative time

The retained job-list response and repeated direct-job endpoint agree:

| Probe job 124800927513 field | UTC value |
| --- | --- |
| `started_at` | `2026-11-01T09:51:55Z` |
| first setup step starts | `2026-11-01T08:51:56Z` |
| last step ends | `2026-11-01T09:17:28Z` |
| `completed_at` | `2026-11-01T09:17:30Z` |

The run also reports creation/start at 09:51:51Z but update at 09:17:31Z.
`rehearsal_guard.job_minutes` computes `max(1, ceil(end-start))`, accepting this
negative interval as **one minute**. Organization usage increased by **26**
minutes, consistent with the observed step span. History pagination is complete
(149/149 IDs, two pages), but that does not make timestamp-based accounting
valid. The source of the upstream timestamp discrepancy is **not proven**;
no timezone correction or substitute elapsed-time policy is assumed.

**Process error:** the guard returned success and the controller dispatched
qualification before I inspected the unexpected one-minute ledger delta. I
should have checked that delta first. I detected it while the run was still
in early setup, requested cancellation once and watched it become cancelled.
Actual qualification timestamps are valid (09:22:04Z–09:26:08Z), cost **five
rounded minutes**; the pinned-tools step was cancelled, native qualification
and the VM step were skipped. No owner command or real-token typing occurred.

**JUDGMENT-CALL:** cancel rather than continue under a silently understated
package ledger, even though the organization and conservative cap bounds had
room. Repairing or compensating for the accounting policy is outside this
counter brief; no guard/runtime code was changed after the push.

| Closing accounting | Minutes / state |
| --- | --- |
| Previously accepted package total | 1,967 |
| Guard's new raw total | 1,973 — **not trusted** |
| Step-span-inferred total | 1,998 — **not an approved authoritative charge** |
| Conservative total using the full 72-minute probe bound plus actual 5-minute cancellation | 2,044 / 2,750 |
| Original full-round reservation ceiling | 2,199 / 2,750 |
| Organization included usage / remaining | 287 / 1,713 of 2,000 |
| Organization reserve / push / closing reservations | 150 / 0 / 0 |
| Dispatch counters | probe 29/30; owner-tools 18/19 |

There is no exact trusted new package total; `BUDGET.json` therefore records
`consumed_minutes: null` and labels the raw/inferred/bounded figures separately.
No paid budget was read or counted; November net paid Actions usage is zero.
Caps and package 13 are unchanged. This is a correctness STOP, not a request to
raise or lower any limit. [Timing evidence](../../os/manifest/ci/14/14zy-round/budget-timing-stop.json).

### Privacy — approved artifact classes and additional unclassified logs

Pinned local gitleaks 8.21.2 reported zero findings over history and pending
files before the one push. Manual exact-range and actual aresync hooks both
passed with gitleaks 8.30.1, with no skipped-personal-terms warning, no bypass
and no terms recorded. The hook remains the pushed-head privacy proof.

The private probe artifact has **509 findings = 507 approved public ISO file
names + the two exact kernel signing-certificate lines below**; native log
scan is zero. No raw listing or console is committed.

| Whole-line SHA-256 | Private artifact member and line | Public certificate label |
| --- | --- | --- |
| `843ea7bb2f91a9525884cb3b17699baccb1319115a985462b28cab888db0aa6b` | `evidence/two-disk/live-ui-probe-boot-console.txt:491` | Fedora kernel signing key |
| `8bb3742faaf5997a69d3a75f9f7b7b253e142b8180de0335d38f45a593cc700b` | `evidence/two-disk/live-ui-probe-boot-console.txt:516` | Fedora kernel signing key |

After the financial stop, scanning the **full GitHub job-log archive** found
four additional `generic-api-key` findings in the cosign-installer output,
two in the step log and two in the combined log. They do not satisfy either approved
artifact exception. **Classification is not authorized; this is an additional
privacy STOP.** Values are neither reproduced nor committed; only these line
hashes/locations are recorded. No ignore, allowlist, rule or workflow privacy
change was made. The cancelled qualification artifact and full logs scan zero.

| Whole-line SHA-256 | Private extracted job log and line |
| --- | --- |
| `ed95dd6caa09f2eb336649083e012674b9dcceb4f7c83f5f0ed5593f626f046e` | `.work/14/14zy/logs-41290621860/Pinned live ISO inspection and two-disk rehearsal/12_Run sigstore_cosign-installer@398d4b0eeef1380460a10c8013a76f728fb906ac.txt:223` |
| `bcf2fa555ea21b2091d064d54b5ef7253e30ae67650114e35443d763d35157a3` | `.work/14/14zy/logs-41290621860/Pinned live ISO inspection and two-disk rehearsal/12_Run sigstore_cosign-installer@398d4b0eeef1380460a10c8013a76f728fb906ac.txt:227` |
| `7092f714b4c24c707b21e2ecd9680310b63812e68d04b678d9df7738a9330a25` | `.work/14/14zy/logs-41290621860/0_Pinned live ISO inspection and two-disk rehearsal.txt:4522` |
| `5ee574cd590fc7bde5a54b5e6646b8ba453e1056993ec8f92a829ece5bcaa325` | `.work/14/14zy/logs-41290621860/0_Pinned live ISO inspection and two-disk rehearsal.txt:4526` |

[Privacy evidence](../../os/manifest/ci/14/14zy-round/artifact-privacy.json) and
[private file hashes](../../os/manifest/ci/14/14zy-round/retained-files.json)
bind the receipts, original archives and raw timing responses without copying
raw evidence into git.

### Not verified / open questions / for package 15

- Qualification 18 never reached a VM. Same-head installed-system typing,
  US International/back-to-German, rollback, keep-stock, final stock verification
  and final Windows checks are **not qualified by this round**. Prior 14zx
  observations remain historical evidence and do not substitute for a complete
  passing run on this head.
- At least **one further explicitly authorized fresh probe/qualification round**
  is needed after trustworthy fail-closed accounting and the log-finding
  classification are settled; the retained output establishes no upper bound.
  One probe and one qualification allowance remain, not permission to use them.
- This stop is financial/privacy, not another console-typing stop. The 14zy
  conditional serial-run plan is not newly triggered; the existing 14zx proposal
  remains a proposal. No serial bypass or alternate owner route was built.
- Owner payload/fingerprint, pinned maps, frozen release paths, INSTALL,
  EMERGENCY, release gate, package 13 and package 15 worktree are untouched.
  The existing physical/followability items remain for the owner/package 15;
  physical installation stays **NOT RELEASED**. No real laptop hardware was used.
- No Gradle daemon or sub-agent was started. Closing validation consists of
  pinned history/pending/post-commit scans, the unchanged hash-order regression,
  `git diff --check` and immutable source-path comparisons, recorded alongside
  this local closing commit. PR #13 stays draft. No further action is authorized
  in this round.

## 14zx REPORT — actual profiles fixed; final stock-login counter STOP

**Disposition:** One fast-forward push through the installed hook to
`d8adc498064065d506917f6b45bf71ca49c36dc6`.
[Probe 28](https://github.com/Ares-Empire/AresOS/actions/runs/41276950908)
passed and its evidence was accepted. [Qualification 17](https://github.com/Ares-Empire/AresOS/actions/runs/41278848542)
failed at the final `default-stock` account-login counter check, on the same
head, attempt 1. Both were watched to completion and private diagnostics
exported. **No rerun, second push or merge.** This report/ledger/evidence commit
stays **local only**. Acceptance remains false; PR #13 stays draft.

### Done — profile-collapse audit

- `owner_vm.public_typing`: console and foot helpers receive the actual `de`,
  `us` or `us-intl` profile. Removed global `PROFILE` and the mapper that ignored
  its profile argument. Shared keyboard helper bindings are scoped and restored
  on success or refusal.
- `owner_vm.keyboard` and `keyboard_vm.loaded_map`: retain the actual profile
  instead of converting US International to plain US. An explicit XKB mapping
  checks `us-intl` as layout `us`, variant `intl`; `foot` checks both fields.
- `owner_vm.type_text` and `Console.send_hidden`: only omitted (`None`) layout
  selects the guest's current profile. Empty/unknown values refuse before keys;
  no truth-value fallback. The serial test model uses this same selector.
- Dumpkeys stand-ins select exact `de`/`us`/`us-intl` fixtures, rejecting unknown
  profiles. The new International fixture is the exact public `loaded_map`
  field from qualification 16, source/hash bound, not a fabricated plain-US map.
- The initial German guest/bootstrap context and deliberately wrong German
  positions for the plain-US failure trial remain explicit known contexts.
  Legacy package-13 two-layout typing is untouched outside the scoped owner
  adapter. Pinned input maps and QEMU keycode CSV are unchanged.
- `test_owner_walk`: the real `public_typing` → `physical_input` → `type_text`
  → `physical_keys` → `Guest.keys` chain runs unpatched. Only the final QMP
  boundary records sends. Nine public cases cover International, return to
  German, rollback and keep-stock/default-stock, with exact chords, including
  `alt_r` + `y` for `ü`. Final Windows marker branches have no typed text/profile;
  they are reached explicitly. Hidden model key sequences are not exported.

### Actual qualification progress

The profile fix is confirmed by actual VM evidence, beyond the local walk:

| Stage | Retained result |
| --- | --- |
| US International | tty3 login/password sudo; `layout proof`/`finish`; loaded console `us-intl`, X11 `us`/`intl`; console and foot `yz-/!ü` physical tests passed |
| Return to German | fresh second-console proof/finish, subsequent German boot, console and foot physical tests passed |
| Rollback | owner command passed; stock boot and console typing passed; rollback from stock refused with zero mutations |
| Keep-stock | owner command passed; following snapshot has saved stock at index 0, booted and pinned, no transaction/staging/rollback queued |
| Final stock verification | loaded map/read-only deployment checks passed; account-login completion, sudo/check/typing/homebrew/logout sequence did not complete |
| Final Windows | unattended and detached marker boots not reached |

Eight of the nine planned public physical cases have actual passing receipts;
the ninth, `default-stock-console`, was not reached. This does not qualify the
whole run. [Stage evidence](../../os/manifest/ci/14/14zx-round/stages.json)
binds the real records. No complete `owner-tools-result.json` or final Windows
prefix exists in this artifact.

### STOP diagnosis — proven versus likely

At `2026-11-01T07:47:17Z`, the actual traceback is `qualification` →
`common_boot(default-stock)` → `Console.login` → `send_hidden:541`:
**Final key counts differ; no post-Enter retry**. No owner command ran at this
failure point. This is a test keyboard/counter verification stop, not evidence
of an owner-tool refusal or a recurrence of the layout adapter bug.

- The prepared counter started before username. Its public baseline is 14
  presses/14 releases; the pre-Enter checkpoint is 46/46, giving **32/32** for
  all 64 password events. Exact pre-Enter proof passed on attempt 1, all keys up,
  no repeat or `SYN_DROPPED`, unchanged login reader, canonical hidden input.
- The harness then sent exactly one Return: **66 events**, 31 chords including
  Return. The final raw counter is **46 presses/47 releases**, or **32/33** after
  subtracting the public baseline: **65 received versus 66 sent**. No repeat or
  `SYN_DROPPED`; keys-up/complete were reported true, but the stronger comparison
  correctly refused the asymmetric counts. No Ctrl-U/retype or extra Enter followed.
- Username through Enter took **8.952960957999991s**, within half the guest's
  60-second timeout. All observed secret presses/releases were classified
  hidden; non-hidden/unknown exposure counts are zero. No secret value or key
  code is retained. No readiness Enter resync happened before this comparison;
  source places hidden-completion/resync after it, so those cannot explain this
  mismatch.
- Post-stop diagnostics show empty tty3 queues, login parent waiting and a
  child polling. That is compatible with a shell after authentication, but its
  identity and successful login are **not certified**: the hidden-left/login
  completion receipt was never obtained. Do not label it a passed login.

There is a concrete **counter race hypothesis**. `observe()` calls
`released(counting_fd)`, which uses `EVIOCGKEY`, after its select/read check.
The retained Linux v6.17 reference and [upstream evdev source](https://github.com/torvalds/linux/blob/master/drivers/input/evdev.c)
route that getter through `evdev_handle_get_val`, which flushes queued events
of that type for the client. A press arriving between select and that getter
can disappear from this observer while a later release is counted; successful
queue flushing need not emit `SYN_DROPPED`. This explains a possible mechanism,
not a proven interleaving. The guest is **7.2.9-ogc3.1.fc44.x86_64**; its exact
fork's evdev source was not verified identical. Counts alone do not prove QMP
or hardware key loss. No fix or weaker comparison was applied after STOP.

[Diagnosis](../../os/manifest/ci/14/14zx-round/qualification-stop.json) binds the
actual counts, timing, redacted diagnostics, source reference and log. Raw
consoles/VCSA/screenshots/ZIPs remain private under `.work/14/run-41278848542/`.

### Verified — local and native

Local commands included `python3 -B -m unittest test_owner_layout_adapter
test_owner_walk test_keyboard_vm test_keyboard_entries`,
`python3 -B .work/14/14zx/whole.py`, `python3 -B .work/14/14zx-walk.py`
and `python3 -B .work/14/14zx-syntax.py`, with workspace TMPDIR and the existing
privileged-command refusal shim for the final full pipeline. Focused runs
preceded the final recorder cleanup; the complete local/native runs below
exercise the final source. No package was installed locally.

- A new regression against unchanged 14zw code failed at the exact missing
  International `ü` mapping: 1 test/120.667s. The final real-chain test also
  rejected the actual retained old adapter function, 1 expected failure/149.490s;
  its wrapper verifies that exact assertion. No source rewrite or VM was used.
- Affected regressions: **22 tests/526.839s PASS**; adapter tests **5/0.028s PASS**;
  local dispatch **6/0.007s**, privacy **7/0.188s**, diagnostics **2/0.006s**, all
  PASS, zero skips. Early local setups needed an integer Mock input epoch and
  updated prior-round counter fixtures; these were corrected without weakening
  assertions or using live APIs in unit tests.
- Whole local suite: **575 tests/1415.070s**, **566 distinct passes**, the same
  **nine documented host limitations**, zero skips/new failure IDs. These are
  three missing-Pillow cases, three inherited-Homebrew privilege/ACL cases,
  sysusers privilege, DrvFS credential mode, and the approved 14zm timing limit.
  The unchanged 30-second case took **64.36261896199994s** locally. No test/bound,
  skip, marker or environment switch was changed. The local whole suite is not
  called fully green.
- Native probe: **575/150.609s PASS**; native qualification: **575/201.108s PASS**,
  zero skips. The mandatory 30-second case and all six new critical layout
  tests are explicitly `ok` in both real logs. The old wrapper's final status
  string still says `native569`; actual logs and count-pinned reviewers prove
  575. That cosmetic label is not an assertion or acceptance source.
- Native real loop/helper checks: **20**, zero helper mutations, protected
  fixture unchanged, all mounts/loops cleaned. Host capability, private access,
  signature and exact layer-pull steps passed on this head. Four credential-only
  local replay steps remain CI-only with reasons; no credential/scope change.
- Final stand-in walk: **973 composed commands, nine public physical cases,
  23 hidden pairs, three handoffs, 133 fresh-authorized resyncs, 86 health
  boundaries**. Probe adds six commands. Strict real Bash: **979 guest scripts
  and 979 serial wrappers**, 811 embedded Python programs, 12 shell and 51 Python
  files plus native shell body; parse stderr refuses. Walks are not VM acceptance.
- Actual ISO replay before each dispatch: **9,068,650,496 bytes**, pin and fresh
  official checksum match, first attempt each time. Actual release/git/read-only
  GitHub and 53 retained sources replayed on the committed head before each
  dispatch, plus strict checks. No Linux inspector behavior changed. Four
  completed SHA-verified duplicate old replay cache files were reclaimed only
  inside this worktree; canonical/master bytes, results and diagnostics remain.
- Through this STOP, independent raw replay passes **14 protected captures**
  equal to baseline, **15 zero-write/unmap samples**, **14 raw varstore/BootNext
  replays**, **13 exact NVRAM/all-variable deltas**. Nine actual AT keyboard boots
  report bus 17 and 57 static mappings; all **98** counts-only xHCI checkpoints
  report no stop. **587** staged transfers pass SHA/syntax verification. Probe
  separately passes 3/4/3/2 raw audit counts, 37 verified transfers, one AT boot
  and seven healthy checkpoints. Audits cover reached stages only.

[Local preparation](../../os/manifest/ci/14/14zx-preflight/preparation.json),
[native proofs](../../os/manifest/ci/14/14zx-round/local-and-native-checks.json)
and [private-file bindings](../../os/manifest/ci/14/14zx-round/retained-files.json)
retain the exact evidence. Closing hash-order regression, diff check and pinned
full-history/all-pending scans are performed before the local report commit.

### Privacy

Exactly three commits, `75a2c63..d8adc49`, passed the installed aresync manual
check with standard full-ref four-field stdin: exit 0, gitleaks **8.30.1**, no
personal-terms-skipped warning. The sole actual fast-forward push also passed
the unchanged hook, without `--no-verify` or hooksPath override. Both have zero
multibyte warnings. Terms were read only by aresync and never recorded by the
agent. Separate pinned **8.21.2** history/pending/committed-head scans were zero.

Artifact findings are only **509=507 ISO names+2 whole kernel certificate lines**
for the probe, and **527=507+20** for qualification. Both native logs and the VM
failure log scan zero. Every certificate match is exactly the approved complete
kernel X.509 line in a captured boot console; each occurrence is recorded below.
No new ignore entry, rule, allowlist or privacy-workflow change. No raw artifact,
ISO listing, screenshot, VCSA, typed password/token or secret key sequence is committed.

| Run | Matched-line SHA256 | Private artifact member and line | Public certificate label |
| --- | --- | --- | --- |
| probe28 | `fdae5ea07bbbce8b89a3e7ea100844ce7ec52442bc230bafc4a35b6946ee27dd` | `evidence/two-disk/live-ui-probe-boot-console.txt:496` | Fedora kernel signing key |
| probe28 | `95f4ef020bc2d67c0693b64ba18e796cc1a5c43ae74ec50fa7aa3ba392dff6af` | `evidence/two-disk/live-ui-probe-boot-console.txt:521` | Fedora kernel signing key |
| qualification17 | `3bd2c340131c37abd3e3272c8bda24b392295028c7567328735dfd2f416b7c51` | `evidence/two-disk/aresos-back-de-boot-console.txt:504` | Build time autogenerated kernel key |
| qualification17 | `c4de28d284c92fa44965e7bed65738a46fade07fdc2cacb5913627daf8c165b9` | `evidence/two-disk/aresos-back-de-boot-console.txt:514` | Build time autogenerated kernel key |
| qualification17 | `24ea639902c0d0a8a56e9ea2da44979c580a14c3e332c5a8b2d0c3ba672a26ae` | `evidence/two-disk/aresos-boot-console.txt:504` | Build time autogenerated kernel key |
| qualification17 | `1d30a716bac61c4c4291e9e7c7b34f628b5a8f417c27de94b9da015efa4cc450` | `evidence/two-disk/aresos-boot-console.txt:514` | Build time autogenerated kernel key |
| qualification17 | `41defb24dd991a4ac382cffa7879138d27b6098031b048ccd71d717bcad203aa` | `evidence/two-disk/aresos-intl-boot-console.txt:504` | Build time autogenerated kernel key |
| qualification17 | `3a56922a5754daef23f4c96aaaccf2dc9d2e640f9b9450a4bc9dfd93ef38fb14` | `evidence/two-disk/aresos-intl-boot-console.txt:514` | Build time autogenerated kernel key |
| qualification17 | `76f6f623edf93b9de8d00a684671de7b18c3f7d589e386590e41ff834e2842fd` | `evidence/two-disk/corrected-stock-boot-console.txt:504` | Build time autogenerated kernel key |
| qualification17 | `4bffb8c8ec0f9da171f14d77e4ec59faf24b71e82ca00ef9346e8a69c1838862` | `evidence/two-disk/corrected-stock-boot-console.txt:514` | Build time autogenerated kernel key |
| qualification17 | `c61eb967791328d431e487803a97e8896e7389a6c966be4019778b42f6b186bc` | `evidence/two-disk/default-stock-boot-console.txt:504` | Build time autogenerated kernel key |
| qualification17 | `a628f78e545de25eeb76585ea7a787043ed672a4da63416e4d30cb59238afe24` | `evidence/two-disk/default-stock-boot-console.txt:514` | Build time autogenerated kernel key |
| qualification17 | `2e52b658ae64ab6696e1e8be93261d018f242f8820a2fe0604993b877e07307c` | `evidence/two-disk/offline-first-stock-boot-console.txt:504` | Build time autogenerated kernel key |
| qualification17 | `c4f6e8d5b902e50f1fb1404b3f874eee0b97d68476e9f0dd768d98db8b76f961` | `evidence/two-disk/offline-first-stock-boot-console.txt:514` | Build time autogenerated kernel key |
| qualification17 | `6395f6bbfe3c2bf50f9d74cc27a5a949b71507e96ef897e5d777f51fbf5fa462` | `evidence/two-disk/protected-second-install-boot-console.txt:497` | Fedora kernel signing key |
| qualification17 | `cb5dabb51f34ad71b88cf39060db79697bd75c543715bea846ffb6975dbc05ec` | `evidence/two-disk/protected-second-install-boot-console.txt:522` | Fedora kernel signing key |
| qualification17 | `f91885ebdb778d3268bc9afd920dbed57672e1f7d7c3d7382e5eef20fe267a99` | `evidence/two-disk/rollback-stock-boot-console.txt:504` | Build time autogenerated kernel key |
| qualification17 | `fc3e9276ee82551310277fd4ff49afb11f8a05dff1fc52c27f3f1cb04aaa4b59` | `evidence/two-disk/rollback-stock-boot-console.txt:522` | Build time autogenerated kernel key |
| qualification17 | `8845a1481b6a1d28d4f25afb3212daf308f591b3ce4020600afce10c991f042c` | `evidence/two-disk/stock-initialization-0-boot-console.txt:504` | Build time autogenerated kernel key |
| qualification17 | `eb952e2d06e5a87e31f9ed7a008f1884abe0cbdeb57d8c3e29cb4fd4d41da5c7` | `evidence/two-disk/stock-initialization-0-boot-console.txt:524` | Build time autogenerated kernel key |
| qualification17 | `2746ab4dae9d9eb8c267167e80c13336b4fddf6661bcb918ca88f965e3125c69` | `evidence/two-disk/tools-stock-boot-console.txt:504` | Build time autogenerated kernel key |
| qualification17 | `b07449d4c8a88830adf89e492a10bc1da9c9c8a4b3b8e7db732cfcec883d155e` | `evidence/two-disk/tools-stock-boot-console.txt:514` | Build time autogenerated kernel key |

[Artifact classification](../../os/manifest/ci/14/14zx-round/artifact-privacy.json)
and [hook proof](../../os/manifest/ci/14/14zx-round/privacy.json) bind these decisions.

### Budget and stop state

Before probe: complete **145/145**, **1832+232/2750**, counts 27/16;
org free **1879**, after bound **1647**, reserve 150.
Before qualification: complete **146/146**, **1856+160/2750**, counts 28/16;
org free **1855**, after bound **1695**. Fresh exact-head local privacy, complete
ledger and billing passed before each dispatch.

Closing at **2026-11-01T07:57:53Z**: complete **147/147**, two pages,
**1967/2750 minutes**, **28/30 probes, 17/19 qualifications**. This round costs
**24+111=135 minutes**; one push, two dispatches, zero reruns. November summary
is **256 used / 1744 included minutes left**, Actions-minute net quantity and
amount zero. `paid_budget_read=false`, `paid_overflow=null`; no budget API read
or paid allowance counted. The owner's $0/stop-usage setting is the owner's
statement, not a new budget-API claim. Reserve **150**, push/closing **0** remain
as 14zw requires; no settings were lowered or restored to obsolete reservations.

### Not verified / remaining rounds

Final stock login completion and subsequent sudo/check/public typing/homebrew/
logout checks, plus both final Windows marker boots, remain incomplete.
**At least one further owner-authorized round** (fresh probe then qualification
on its head) is needed. One could suffice if this counter issue is the only
remaining blocker; retained output does not prove an upper bound. No further
run is authorized or dispatched here. Earlier reached Windows markers are not
substitutes for the two missing final checks.

Physical laptop, battery, forgotten-stick-at-power-on, real NVIDIA notification,
Media Writer restore, live KDE/KWrite and novice followability remain physical
gates. Backup stock keeps the installer's layout; no US-then-direct-rollback run
is claimed. INSTALL/EMERGENCY/release gate remain NOT RELEASED and unchanged.
No Mod/game tests or Gradle daemon, real laptop operation, other worktree,
image build/publication, owner-script/runtime/pinned-map change followed STOP.
Payload fingerprint stays `320ca9878367ee1da4d4634e74d1e3b2de0027d1e7436955f4c69eb21ab806a6`.

### PLAN-GAP / proposed next work only

Investigate the counter's same-client getter race against the guest kernel;
retain exact count comparison and the no-post-Enter-retry rule. This is a
proposal, not a fix. As requested by 14zv, another option for the remaining
non-typing default-stock/rollback/keep-stock/final-Windows checks is an approved
SHA-framed serial route reusing every existing check/audit. Keep International
and back-to-German typing physical. Direct serial-root owner commands would
fail the physical-session guard; any adapter must preserve that guard and the
guide/CI contract with explicit integrator approval. Nothing was implemented.

**JUDGMENT-CALL:** No product decision or privacy waiver. The stronger final
counter check stopped despite a passing pre-Enter proof; its assertion is kept.
**Open question:** Integrator decision on that counter hypothesis and the next
qualification route. This round is over. Closing report/ledger commit is local
only; no second push, no rerun, no merge.

## 14zw REPORT — local privacy proof; probe 27 passes, qualification 16 STOPs

**Disposition:** One fast-forward push through the installed privacy hook to
`75a2c638cecff042b528eb07e3089eda9129de02`. [Probe 27](https://github.com/Ares-Empire/AresOS/actions/runs/41264222963)
completed **success**; [qualification 16](https://github.com/Ares-Empire/AresOS/actions/runs/41266663581)
completed **failure** on that same head, attempt 1 each. Both were watched to
completion and their diagnostics exported. No rerun or second push. Acceptance
is **not met**; PR #13 stays draft. This report and closing ledger are committed
**locally only**, as 14zv/14zw require. No merge.

### Done

- Merge `9ad1a74` joins local brief `38ad8e6` with `origin/main`
  `1ac978644ea40182856a653aa5a767088e2b360b` (the HANDOFF-only child of
  `fabd476`). `HANDOFF.md` and `STATE.md` equal that main parent's versions.
  Main's deleted GitHub privacy workflow stays deleted. No rebase or force push.
- Guard commit `6c3b70b` adopts aresync local privacy proof and explicit package
  14 push/closing reservations of **0**, each bound to this brief. Organization
  reserve **150**, probe/qualification bounds **72/160**, cap **2750**, and caps
  **30 probes / 19 owner-tools** stay set. Package 13 and 11c settings are
  unchanged. Historical October/November tests remain on fixed dates.
- Preflight `2c12f71` binds 146 sources and 17 local controls. `75a2c63` corrects
  only the local manual checker's Windows stdin framing (described below).
  No owner payload, frozen runtime, release, image, keyboard map, physical
  typing helper or VM harness implementation was changed in 14zw.

### Proven qualification STOP, from actual retained output

At `2026-11-01T04:16:01Z`, after the `aresos-intl` protected-disk capture, the
actual traceback runs `owner_vm.public_typing:808` →
`keyboard_vm.physical_input:114` → `owner_vm.type_text:53` →
`owner_keys.physical_keys:64`, raising **Unknown or untypeable physical
character**. The first call converts every profile except German to `us`:
`'de' if profile == 'de' else 'us'`. At this stage the actual profile is
`us-intl`. The test text is `yz-/!ü`; U+00FC (`ü`) deliberately has no plain-US
physical mapping. Reading the unchanged pinned maps confirms that US
International maps it to `alt_r` + `y`. `type_text` receives the explicit
incorrect `us` argument, overriding the guest's correct `us-intl` profile.
The analogous `foot` call at line 810 has the same collapse, but was not reached.

The retained `aresos-intl-loaded-keyboard.json` shows `KEYMAP=us-intl`, X11
layout `us`, variant `intl`, and matching localed values; no forced vconsole
cmdline override. Actual tty3 login passed once in **9.003s** of a 30-second
half-timeout budget, with zero reader replacements and `secret_tainted=false`.
Account-login and password-sudo completion receipts passed. Owner `check`,
`layout proof` and `layout finish` records passed; the last explicitly asks for
post-boot console and labwc physical typing, which this harness then failed
to complete. These records do not establish full qualification acceptance.

**Classification:** a harness layout-adapter/console-test bug. This assertion
does not implicate an owner-tool refusal, a wrong installed layout or dropped
PS/2 key events. The retained run proves the failing call and stage; the pure
map lookup only explains the deterministic refusal. Source inspection also
shows the local stand-in walk replaces `public_typing` (`test_owner_walk.py`,
lines 234/273), so it never exercised the real helper/profile handoff. That is
a coverage gap, not actual VM success. No fix has been implemented after STOP.

[Qualification diagnosis](../../os/manifest/ci/14/14zw-round/qualification-stop.json)
binds the real log, loaded map and completion records. Raw logs, VCSA,
screenshots, private artifacts and ISO file listing stay uncommitted under
`.work/14/run-41266663581/`; the artifact ZIP binds all 2,068 members.

### Verified

- Local guard suites: **51 tests / 0.975s, PASS, zero skips**. Local privacy
  checks: **7 / 0.173s, PASS**; dispatch control **6 / 0.006s, PASS**, diagnostic
  exporter **2 / 0.006s, PASS**. No live API calls in these unit tests.
- `.work/14/14zw/whole.py` ran the whole local suite twice. Initial:
  **569 tests / 1535.101s, 559 distinct passes, nine documented host limits,
  zero skips, one metadata-order failure**. Two old 14zv warning records had
  paths before hashes; reordered only those keys, preserved all JSON values,
  refreshed their manifest, and passed the unchanged regression. Full second:
  **569 / 1600.079s, 560 distinct passes, the same nine host limits, zero skips,
  zero new failures**. The nine remain three PIL tests, three inherited-Homebrew
  privilege/ACL tests, credential filesystem-mode, sysusers privilege and 14zm
  host timing. The unchanged 30-second test took **72.34734368800014s** and
  **79.63881609000009s** locally; no bound/test/skip/environment change. This
  local whole suite is not reported as fully green.
- Actual release/git/read-only GitHub binding and **53 pinned sources** replayed
  on the final head before each dispatch. Four CI-only package/registry/digest/
  signature/pull credential checks remained fail-closed in CI; both native jobs
  passed. No credential scope or owner-secret use was added.
- Actual ISO replay before each dispatch passed on the first actual attempt:
  **9,068,650,496 bytes**, pin and fresh official checksum equal, four
  localization and 102 WebUI sources. Linux CI behavior unchanged. Only two
  completed, SHA-verified duplicate 14zv cache files were reclaimed inside this
  worktree; canonical/master data and results remained intact.
- Stand-in walk: eight stages, **23 hidden-input pairs, three handoffs,
  133 fresh-authorized resyncs, 86 health boundaries, 940 commands**; probe adds
  six commands. Strict real Bash: **946 guest scripts and 946 serial wrappers**,
  808 embedded Python programs, 12 shell and 51 Python files, plus native shell
  body; parse stderr refuses. Fresh replay/strict checks preceded each dispatch.
  These syntax/control-path checks did not cover the adapter defect above.
- Probe's actual native suite: **569 / 172.805s, PASS, zero skips**; qualification
  native suite: **569 / 125.363s, PASS, zero skips**. The exact mandatory
  30-second timing case passed natively in both, with no local exception applied.
  Probe native loop/helper checks: **20**, zero helper mutations, protected
  fixture unchanged, mounts/loops cleaned. Probe guest has **37** SHA/syntax
  verified tmpfs transfers, one actual AT keyboard record with 57 mappings,
  and seven healthy counts-only xHCI checkpoints.
- Through the qualification STOP, independent raw replay passes **11 protected
  captures** equal to baseline, **12 zero-write/unmap samples**, **11 raw
  varstore/BootNext replays** and **10 exact NVRAM/all-variable delta replays**.
  Six actual boots identify the AT Translated Set 2 keyboard, bus 17, 57 mappings
  each; all **71** counts-only xHCI checkpoints report no stop. Probe separately
  passes 3 protected captures, 4 zero-write/unmap samples, 3 varstore/BootNext
  and 2 NVRAM/all-variable delta replays. These audits cover only reached stages.
- `git diff --check`, unchanged hash-order regression and pinned closing
  full-history/all-pending scans are required before this local report commit;
  final receipts are in the round manifest. No Mod/game tests or Gradle daemon
  were started for this OS-only work.

[Bound local preparation](../../os/manifest/ci/14/14zw-preflight/preparation.json),
[probe review](../../os/manifest/ci/14/14zw-round/probe.json) and
[retained-file bindings](../../os/manifest/ci/14/14zw-round/retained-files.json)
preserve the evidence without committing raw private output.

### Privacy proof and artifact review

Before the actual push, the exact six-commit range from `becfb22` to `75a2c63`
was checked with standard four-field full-ref stdin by the installed aresync
checker. **Exit 0**, hook-selected gitleaks **8.30.1**, no “personal terms check
skipped” warning. The sole actual `git push origin
refs/heads/pkg/14-owner-tools:refs/heads/pkg/14-owner-tools` also returned 0
through the unchanged installed hook, without `--no-verify` or hooksPath
override. Terms were read only by aresync, not recorded or printed by the agent.
Separate pinned **8.21.2** full-history/pending/committed-head scans were zero.

An initial manual invocation, before any Git push, rejected malformed stdin:
Windows text-mode piping added CRLF, making the remote SHA 41 characters.
Real Bash reproduces old framing rejection and corrected binary-LF acceptance.
Only the local manual wrapper changed, with a regression; installed hook,
checker, terms, rules and ignores did not. This was a zero-cost local setup
failure under 14zd, not a finding or actual push-hook refusal. Both successful
manual and actual checks emitted one nonfatal awk multibyte warning, retained
privately; exit 0 and the required skipped-terms-warning absence are recorded.
No privacy failure was waived. Pushes now start no workflow; branch history
stayed at 143 until the probe dispatch. Local proof is bound to the pushed head.

Probe artifact: **509 findings = 507 reviewed public ISO filenames + two public
kernel certificate lines**. Qualification artifact: **521 = 507 + fourteen**.
Every matched source line was exactly the previously approved whole kernel
`[timestamp] Loaded X.509 cert '<name>: <40 hex>'` class, in captured boot
consoles. No other class occurred. Native logs and the failure log scan zero.
No new ignores/rules/allowlists or privacy workflow changes. These line hashes
identify each occurrence (not secret values); paths are private artifact members:

| Run | Matched-line SHA256 | Member and line | Public certificate label |
| --- | --- | --- | --- |
| probe27 | `eb024f15a7d3286eb67a6f7be7764d7f1b29cd1ce77a8534ec94b4c653e28785` | `evidence/two-disk/live-ui-probe-boot-console.txt:491` | Fedora kernel signing key |
| probe27 | `fa18da12ea089e3840b553efa8fed995f549764346517c4f1f3413128e9a5eee` | `evidence/two-disk/live-ui-probe-boot-console.txt:517` | Fedora kernel signing key |
| qualification16 | `d9de19b657e76122a4b8ed0f94abd3691fcf2384b3df7443207911a415743203` | `evidence/two-disk/aresos-boot-console.txt:502` | Build time autogenerated kernel key |
| qualification16 | `4f6b396b8fe1102bf4ebc34e0fd61bb25d6ed843d7381235ef532402594ab5d5` | `evidence/two-disk/aresos-boot-console.txt:512` | Build time autogenerated kernel key |
| qualification16 | `aaa06fab271645ca376bcfa3e86a21c91473ba771a1833b29a8c148b8e77eea1` | `evidence/two-disk/aresos-intl-boot-console.txt:502` | Build time autogenerated kernel key |
| qualification16 | `ffb1ec33f2c9c73a1be2e71a3c4c07fd89ec0dfa61fc9eeb158227cceed6e124` | `evidence/two-disk/aresos-intl-boot-console.txt:512` | Build time autogenerated kernel key |
| qualification16 | `f3318663d56f79f04ac374bef9377680c345766324d0e98040813285900a909b` | `evidence/two-disk/corrected-stock-boot-console.txt:502` | Build time autogenerated kernel key |
| qualification16 | `bdbe231144d71978a60cc0aee18210e3f59c74f5054dbbab083ba16055cd0dc8` | `evidence/two-disk/corrected-stock-boot-console.txt:512` | Build time autogenerated kernel key |
| qualification16 | `8381bfc312d2af54a025584719e51645e875e1b28d4b82197937e1bb5cd652bd` | `evidence/two-disk/offline-first-stock-boot-console.txt:502` | Build time autogenerated kernel key |
| qualification16 | `3eb6f65abbdaeb7809ca168c2749329f7142010a5d8dbb77f6d293c3a9426470` | `evidence/two-disk/offline-first-stock-boot-console.txt:512` | Build time autogenerated kernel key |
| qualification16 | `2773367107d11a15cd057029625a57b645a643f0acbece1b68e71216f4ec3d8f` | `evidence/two-disk/protected-second-install-boot-console.txt:495` | Fedora kernel signing key |
| qualification16 | `19a55db5027ed70e34be9017d1058c61a589f031bb0e2d1b1f10b6d22bb93d52` | `evidence/two-disk/protected-second-install-boot-console.txt:520` | Fedora kernel signing key |
| qualification16 | `9fa43e0d682e9380aa1fc68c10fa869bf245b93fdad938f6e73fefe7c243fc2b` | `evidence/two-disk/stock-initialization-0-boot-console.txt:502` | Build time autogenerated kernel key |
| qualification16 | `80bb8fb4f069818b77d6b9af4966252abe6adf0ce97080442f8ef89d73ae3c3a` | `evidence/two-disk/stock-initialization-0-boot-console.txt:512` | Build time autogenerated kernel key |
| qualification16 | `8c8d6d22256614ed8e1f08b178bd6108e6f6580c0821933f0156bee0c6f89ef1` | `evidence/two-disk/tools-stock-boot-console.txt:502` | Build time autogenerated kernel key |
| qualification16 | `d4fef9730e825a1fe798ec7adb4163a736db1ad0fbb8ccb06d78aeea0f43ce91` | `evidence/two-disk/tools-stock-boot-console.txt:512` | Build time autogenerated kernel key |

[Privacy proof](../../os/manifest/ci/14/14zw-round/privacy.json) and
[artifact classification](../../os/manifest/ci/14/14zw-round/artifact-privacy.json)
retain the per-line decisions. The raw 507-line-class findings and ISO listing
are never committed.

### Ledger / November billing

Before probe: **143/143** complete history, **1718 + 232 / 2750**, counts 26/15;
org free **1993**, after the 232 bound **1761**, above the 150 reserve.
Before qualification: **144/144**, **1744 + 160 / 2750**, counts 27/15;
org free **1967**, after 160 **1807**. Fresh hook proof, ledger and billing
passed immediately before each dispatch. No live operation preceded 00:05 UTC.

Closing at `2026-11-01T04:19:07Z`: **145/145 history entries**, two complete
pages, **1832/2750 package minutes**, **27/30 probes, 16/19 qualifications**.
Probe cost **26**, qualification **88**, total this round **114**; one push,
two dispatches, zero reruns. November summary: **121 used / 1879 included
minutes left**, Actions-minute net quantity and amount both zero.
`paid_budget_read=false`, `paid_overflow=null`: no budget API read and no paid
allowance counted. Owner's $0/stop-usage setting is the owner's statement,
not a fresh budget-API claim. Reserve **150**, push and closing **0** remain
explicitly bound to 14zw; no restoration to 12 is appropriate under this brief.

### Not verified / acceptance

Full post-boot US International console and foot typing, return to German,
rollback, keep-stock and final unattended/detached Windows checks **were not
completed**. The result file for complete qualification and all later stage
prefixes are absent. Earlier reached Windows/audit checkpoints are not a
substitute for final Windows acceptance. Physical laptop, battery, forgotten
stick, NVIDIA deferred-work behavior, live KDE/KWrite and novice followability
remain physical gates. INSTALL/EMERGENCY/release gate remain NOT RELEASED.

No harness/product/owner-script fix followed STOP. No image build, publication,
visibility change, credential-scope change, real laptop operation, other
worktree or real Minecraft access. Payload fingerprint stays
`320ca9878367ee1da4d4634e74d1e3b2de0027d1e7436955f4c69eb21ab806a6`.

### PLAN-GAP / proposed follow-up only

First repair and exercise **all three-layout helper handoffs** in a future
authorized round, retaining the unknown-character refusal. For remaining
non-typing rollback/keep-stock/title/reboot/final-Windows stages, propose the
existing SHA-framed serial command runner with the same owner commands and
all disk/NVRAM/BootNext/hotplug guards. Physical US International login/typing
and return-to-German tests must remain. Direct serial-root invocation would
fail the owner's physical-logind-session guard: an approved harness adapter
must preserve that verified physical session context, with no product guard
weakening. This is a proposal, not implemented or dispatched, and does not
by itself repair the profile bug.

**JUDGMENT-CALL:** No product choice or privacy waiver. Treat the malformed
manual stdin as the locally correctable setup error proven above; preserve the
real hook and report its warning. Keep raw evidence private and the closing
report commit local. Changing this later requires a new authorized round.

**Open question:** Integrator decision on the harness handoff fix, real-helper
coverage and optional non-typing serial route. This round is over; no further
push, dispatch or merge.

## 14zv REPORT — November settings verified; STOP at privacy gate

**Disposition:** Exactly one fast-forward push, on
`becfb2221ce0436e97ed117bd7be1028ad3e7648`, at `2026-11-01T00:35:21.775801+00:00`. **No probe or qualification dispatched.**
The sole new Actions run, [push privacy 41257409190](https://github.com/Ares-Empire/AresOS/actions/runs/41257409190),
finished success. Its personal-term scan was skipped, so the required privacy
gate did not pass. This report and closing ledger are committed **locally only**;
there is no second push. PR #13 stays draft; no merge.

**PLAN-GAP — proven from actual retained output:**

- Main commit `fabd476e39145feace9480c2301b6a2cb0419d6d`, at
  `2026-11-01T00:00:43Z`, deletes `.github/workflows/privacy-check.yml`
  (subject: “Remove the GitHub privacy check: it now runs locally before each
  push (aresync's pre-push hook)”). Both current main and PR #13's actual merge
  tree `7853858fa9d704d821caf21fc411938cd0a8d060` contain only `os-image.yml`
  under `.github/workflows/`. The package branch still contains the privacy
  workflow. The complete branch history and independent exact-head listing
  show only the push run, with no `pull_request` privacy run. The PR is open,
  draft, mergeable and clean. This conflicts with 14zv's explicit requirement
  to wait for both push and PR privacy checks before dispatch.
- All three push steps have GitHub conclusion `success`, but the actual
  `No personal terms` log says **`PRIVATE_TERMS secret is not set — skipped`**.
  The warning is at `scan/5_No personal terms.txt:14`, also duplicated in the
  combined `0_scan.txt:184`. Thus the job's green conclusion proves neither an
  executed personal-term check nor the required dispatch authorization.
  Gitleaks and private-email steps did execute successfully.
- This is a repository privacy-policy/gate conflict, not a newly observed
  owner-tool bug or console-emulation failure. No owner-tool or console ran in
  this round. No workflow, ignore, rule, credential or secret was changed; no
  replacement privacy dispatch or bypass was attempted. There is no console
  failure to diagnose or serial-stage proposal to implement in this round.

[Retained privacy proof](../../os/manifest/ci/14/14zv-round/privacy-gate.json)
records the real trees, run, step conclusions and warning locations/hashes.
Raw logs remain private under `.work/14/14zv/privacy-stop/`; the committed
[file manifest](../../os/manifest/ci/14/14zv-round/retained-files.json) binds
their bytes without copying raw logs, screenshots, VCSA or secrets.

**Done:** `rehearsal_guard.py` keeps the paid-overflow path only for October
2026; fixed-October tests preserve that history. Every later month uses only
included minutes, never reads the budgets API and refuses nonzero Actions-minute
`netQuantity` or `netAmount`. A valid empty current-month summary is zero used;
wrong organization, stale/malformed period and invalid usage still refuse.
Package 14 alone now has cap **2750** (`ceil((1715+1000)/50)*50`), dispatch caps
**30 probes / 19 owner-tools** (starting counts **26 / 15**, plus four each),
other-repo reserve **150**, closing reservation **12**. The starting ledger is
**1715**, below the 1800 stop. Package 13 and 11c settings are unchanged.
Code commit `08056b7` and bound-preflight commit `becfb22` include the pending
14zs/14zt/14zu work in this one push. The 14zv delta itself changes no owner
payload, frozen image/release, workflow or runtime path.

**Verified locally (actual executions):**

- Existing WSL: `PYTHONPATH=os/ci:os/tests python3 -B -m unittest
  test_organization_budget test_owner_guard test_rehearsal_budget
  test_rehearsal_retry test_rehearsal_history`: **49 tests, 1.207s, PASS,
  zero skips**. Includes October/November, valid empty month, paid-usage STOP,
  reserve/cap/history/retry regressions. An initial command named a nonexistent
  pagination module; the corrected complete command above passed.
- Local dispatch controller: **6 tests, 0.007s, PASS**, zero live API calls,
  including the UTC cutoff and one-attempt watcher. Basic diagnostic exporter:
  **2 tests, 0.005s, PASS**.
- `.work/14/14zv/whole.py` ran the whole local suite: **567 tests,
  1560.204s runner / 1560.307s wall; 558 distinct passes, nine documented host
  limitations, zero skips and no new failure IDs**. The nine retain the prior
  PIL, privilege/ACL/sysusers, filesystem-mode and approved 14zm timing limits.
  The unchanged 30-second serial test took **42.79034450799986s** here. It was
  not weakened or skipped; an overrun in native CI remains a real STOP.
  This local suite is not reported as fully green.
- `.work/14/14zv-read-only-replay.py`: actual release/git/read-only GitHub
  binding and 53 pinned source replays passed, including again on the committed
  pushed head. The four CI-only registry/package/signature/pull checks remain
  fail-closed in CI and were not replaced by local credential escalation.
- Actual `installer_inspect.main` replay passed for all **9,068,650,496**
  pinned ISO bytes against both pin and fresh official checksum. The first
  Windows checkpoint hit WinError 5; with no overlapping replay/reader, the
  authorized 14zd local retry after 10 seconds on fresh `14zv-replay-2` passed
  (four localization and 102 WebUI sources). No Linux CI inspector behavior
  changed. The adapter's descriptive `kind` still says probe26/qualification15;
  that stale label is not an Actions claim: this round planned 27/16 and sent
  neither.
- Bound stand-in walk passed all eight stages, **23 hidden-input pairs,
  three handoffs, 133 authorized resyncs, 86 health boundaries and 940 guest
  commands**. The probe walk added six commands. Strict real-Bash checks passed
  **946 guest scripts plus 946 serial wrappers**, 808 embedded Python programs,
  12 shell files, 51 Python files and the native workflow shell body; any parse
  stderr was a refusal. These are local syntax/control-path proofs, not VM or
  physical-owner acceptance evidence.
- Pinned gitleaks **8.21.2**: full-history and pending-file scans were zero
  before the one push; the committed-head receipt is bound to `becfb22`.
  Downloaded push-privacy logs also scan **zero findings**. Closing metadata is
  scanned before the local commit. `git diff --check` passes.

[Preparation and command bindings](../../os/manifest/ci/14/14zv-preflight/preparation.json)
retain the local results, source hashes and exact adapters. The same-head
probe/native requirement was never waived.

**Ledger / November billing:** The first live guard ran at
`2026-11-01T00:24:15.159266+00:00`, after `2026-11-01T00:05Z`; no live guard, push
or dispatch ran before that cutoff. Before push, the complete ledger was
142/142 runs, 1715 minutes. The closing ledger is **143/143 runs, two complete
pages, 1718/2750 minutes**, counts **26 / 15**; the sole push job adds three
minutes. One push, zero dispatches, zero reruns. November's closing summary at
`2026-11-01T00:43:54.073271+00:00` reports **6 used / 1994
free minutes remaining**; Actions-minute net quantity and amount are zero.
`paid_budget_read=false`, `paid_overflow=null`: no budget API was read and no
paid minutes were counted. The owner's $0/stop-usage setting is the integrator's
statement in 14zv, not a fresh budgets-API verification. Reserve 150 and closing
12 remain set. No further cost was authorized after the privacy STOP.

**Not verified / acceptance:** No native CI suite, probe 27 or qualification
16 ran. PS/2 physical typing, US International success, return to German,
rollback, keep-stock and final Windows acceptance remain unverified. Earlier
retained partial qualification results are unchanged. No laptop, disk, boot
configuration, publication, image, owner script or package 15 worktree was
touched; no Mod/Gradle/game test was run for this OS-only delta.

**JUDGMENT-CALL:** No product choice. The explicit privacy gate was preserved.
**Open question:** The integrator must reconcile 14zv's required GitHub push/PR
privacy evidence with the intentional workflow removal and absent
`PRIVATE_TERMS` before another dispatch. This round is over; the closing
REPORT/ledger commit stays local for the next authorized push.

## 14zu REPORT — local PS/2 typing and xHCI health gates

**Done:** Package14's VM and early native capability check no longer add
`usb-kbd`. All package14 QMP physical typing uses q35's built-in i8042/PS-2
keyboard, including VT selection, visible commands, hidden input, layout proof,
foot and bounded Enter resyncs. The tools stick remains on the same xHCI
controller/port2 and follows the existing attach/remove-before-reboot rules.
The event selector requires exactly one `AT Translated Set 2 keyboard`,
BUS_I8042 `0x11`, vendor/product `1/1`, required key capabilities, then rechecks
the opened device's EVIOCGID. Boot also reads every used static EVIOCGKEYCODE
slot and refuses a mapping mismatch before typing. It never assumes an event number. Boot evidence
and physical-typing receipts identify the AT transport; the native capability
step now requires `i8042` and `ps2-kbd`, with no `usb-kbd`, in QMP's qtree.

**Zero-cost source/device verification:** The retained Q15 guest already logged
the i8042 controller and `AT Translated Set 2 keyboard` on platform/i8042/serio0.
[Source proof](../../os/manifest/ci/14/14zu-local/source-proof.json) binds that
private boot console by hash and the public references by hash/URL. QEMU
v8.2.2's [q35 initialization](https://github.com/qemu/qemu/blob/v8.2.2/hw/i386/pc_q35.c)
calls the PC basic-device initialization; [pc.c](https://github.com/qemu/qemu/blob/v8.2.2/hw/i386/pc.c)
defaults i8042 enabled and creates TYPE_I8042. The pinned runner package remains
`1:8.2.2+ds-0ubuntu1.18`; no host package or guest setting changed.

The exact pinned ISO's de/us/us-intl VT maps still decide characters. The test
cross-checks every used qcode, modifiers and VT-selection keys through the pinned
QEMU keycodemapdb's AT set1/set2 fields and Linux's raw/translated AT tables to
the same Linux keycode. No layout-specific mapping override was needed. Linux
v6.17 atkbd is an explicitly identified upstream reference, not a claim that
the Bazzite fork's module was rebuilt or its bytes matched that reference.
QEMU [ps2.c](https://github.com/qemu/qemu/blob/v8.2.2/hw/input/ps2.c) has a
16-byte scancode admission limit and 8-byte reply headroom;
[ps2.h](https://github.com/qemu/qemu/blob/v8.2.2/include/hw/input/ps2.h) keeps a
256-byte compatibility backing buffer. Each qualification chord fits below 16
scancode bytes. Holds remain 30ms and gaps 120ms. This permits draining; it does
not prove immunity to arbitrary host stalls. Echo and count/refusal checks stay.

**xHCI health:** Every Linux boot-stage uses the full current-boot monotonic
interval beginning at 0, so early failures cannot be hidden by a late serial
login. Checks run at boot/owner-command/media/stage boundaries, inside every
cursor, idle, visible-echo, hidden-read, prepared-login and owner-result wait,
and after a completed not-ready observation. Read-only current-boot kernel
journal polls are throttled to once per second inside loops and forced at
observer entry/exit. The original predicates/deadlines/resync limit stay.
Missing/inconsistent journal data refuses. Only counts/classes leave the guest.
A controller-dead or unrequested USB-disconnect class while the stick is
attached or needed immediately STOPs with the explicit xHCI message; the
stop-endpoint timeout alone is counted diagnostically. One independently
requested tools removal is recognized only for its sysfs-resolved port2 under
the owned PCI00:05.0 controller. Repeated/unrelated disconnects or controller
death are not excused. Firmware/Windows markers have no Linux journal: existing
tools-absent, QMP, BootNext, NVRAM and protected-disk audits remain mandatory.

**Verified locally:** `PYTHONPATH=os/ci:os/tests python3 -B -m unittest -v test_owner_ps2 test_owner_key_counter test_owner_capabilities test_owner_console test_owner_hidden test_owner_login test_owner_walk test_owner_records_prompt test_owner_sudo_idle test_owner_equality test_keyboard_vm` in existing WSL: **103
tests, 848.898s, PASS, 0 skips**. This includes device selection,
AT ioctl/counter tests, source mapping/queue limits, exact retained Q15 failure
classes, since-boundary filtering, expected removal vs death, missing/invalid
journal refusal, a failure arriving during a wait, all guarded observer forms,
timeout receipts, old VCSA/idle fixtures, and exact owner-block/bundle checks.
The initial Windows-Python attempt could not run Linux terminal/pipe tests and
its Bash subprocess quoting differed; it is not passing evidence. WSL passed
the unchanged checks. No software was installed and no test bound was changed.
After correcting early-STOP diagnostic export to stderr, all
**14 PS/2/health/framing tests pass in
3.717s**. The added real-Bash regression verifies counts
survive failure before stdout's checksum export, in direct and serial modes.
Its first local setup correctly refused the production `/run` mktemp path;
the existing owned-repo-directory mktemp shim fixed that setup, with production
framing and assertions unchanged. An intermediate broader local run was
invalidated by concurrent inspected-source edits and is not passing evidence;
the 103-test rerun used frozen sources.

The separately retained healthy walk passes **8 stages,
23 hidden pairs, 3 public handoffs,
86 health boundaries and 940
composed guest commands**. Every composed command and its serial/staged wrapper
passes real `bash -n` with empty stderr. It covers US-intl proof/finish, back to
German, rollback, keep-stock and both final Windows markers. The Q15 screen
shape is injected as clutter into later-stage waits; a synthetic healthy AT
redraw follows one independently idle-authorized Enter. This is a local model,
not evidence that Q15 recovered or that a new VM ran. Historical dead-keyboard
fixtures still refuse; no old historical prompt becomes a readiness grant.
The host walk and source bindings are refreshed. `git diff --check` passes.
The final hash-manifest order and regenerated-payload equality checks also pass:2 tests,12.015s,0 skips.
Pinned gitleaks 8.21.2 full history and curated pending files: 0 findings.

**Not verified:** No new VM, native runner or laptop test. Actual AT event
delivery through all layouts, native qtree and guest journal timing await the
November probe/qualification. The whole native suite was not run locally in
this round; its existing host limitations remain documented and its native
requirements remain mandatory. No raw Q15 VCSA, screenshot, console or secret
was committed. The owner payload/fingerprint, owner scripts/guides, frozen
runtime/image/release paths, privacy policy/workflow and budget settings are
unchanged. Payload fingerprint stays
`320ca9878367ee1da4d4634e74d1e3b2de0027d1e7436955f4c69eb21ab806a6`.
INSTALL/EMERGENCY/release gate remains **NOT RELEASED** and PR13 remains draft.

**Budget / disposition:** 0 Actions minutes; no pull, push, dispatch, publication
or merge. The last closed ledger remains 1715/1900 (26 probes, 15 qualifications).
No new allowance was inferred. Commit locally only; the integrator will supply
fresh November settings including the 150-minute reserve before another CI round.

**JUDGMENT-CALL:** The keyboard topology change is the integrator's explicit 14zu
decision. Health polling and sysfs-identified intentional-removal handling are
confined to the CI harness; no owner workflow or product setting changes.
**PLAN-GAP:** 14zt's keyboard-transport gap is addressed in the harness, pending
real VM qualification. The original cause of xHCI death remains unproven.
**Open questions:** November native/VM acceptance remains outstanding.

## 14zt REPORT — PLAN-GAP: disconnected keyboard, unchanged prompt

**Done / finding:** Q15's problem is not an alternate rendered prompt form.
The strict refusal is correct for the retained state. The kernel reported the
xHCI controller dead and disconnected the qualified QEMU USB keyboard. A
readiness change that accepts the old row45 prompt would claim recovery without
any observed successful input. No runtime predicate, resync, hardware topology,
USB driver, guest setting, owner script or image was changed.

**Screen explanation (zero-based VCSA rows):**

| Row | Retained content / role |
|---|---|
|23|`root@bazzite:~# sudo /var/lib/ares/at title` — earlier command history.|
|33|`root@bazzite:~# sudo /var/lib/ares/at records` — the completed command.|
|34|`PASS records`.|
|35–43|Nine diagnostic result lines: target/serial, EFI GUID, stock identity/default, pin/idle, staged/rollback state, stock title, title invalidation, title resolution, Flatpak state.|
|44|`Full diagnostics: /var/lib/ares/records (private)` footer.|
|45|The ordinary `root@bazzite:~# ` prompt, immediately followed on that same row by the xHCI stop-endpoint-command error.|
|46|Kernel message: xHCI host controller not responding; assume dead.|
|47|Kernel message: HC died; cleaning up.|
|48|Kernel message: USB `1-1`, device2 disconnected.|
|49|Empty; the hardware cursor is `(0,49)` on the50x160 screen.|

The exact row transcript and cell attributes remain private at
`.work/14/14zt/exact-rows-private.json`; no raw VCSA is committed. Its source
artifact, each screen and each receipt are hash-bound in
[the analysis](../../os/manifest/ci/14/14zt-local/analysis.json).

**Proven:** all3 complete VCSA buffers (cells, attributes and cursor) have the
same SHA-256, `8649735e5bd80360e83a626321415b0e87aef64ffb4592f9eb15b14161f5fd8f`.
Neither recorded Enter produced a visible new line or prompt in the following
sample. Both host receipts say Enter issued, with a freshly verified idle
sudo-i relay leading to a foreground interactive bash; they do not contain guest EV_KEY delivery
proof for those Enters. The prompt occupies row45 columns0-15; the kernel text starts at column16.
Its16 printable cells are the same normal
`root@bazzite:~# ` form, without a different trailing character. Literal PS1
and original ANSI escape bytes are not recoverable from post-rendered VCSA
cells; color attributes do not turn the command-history rows into prompts.

`records` prints its result lines and diagnostic footer **after** PASS. The
returned shell prompt is on row45 directly after the footer, without an
intervening blank row. Kernel output follows/appends to that prompt, leaving
the cursor at row49. There is no active pager in either retained foreground
chain: it terminates in the idle interactive bash. Rows23/33 are commands;
row45 is a rendered prompt followed by kernel output, not a current cursor-line
prompt. Searching upward for a root prefix would therefore accept history.

The retained boot console maps xHCI PCI `0000:00:05.0` to USB bus1 and maps
`1-1`, vendor0627/product0001, to **QEMU USB Keyboard**. The retained QMP device
receipt identifies PCI slot5 as `usb-controller`. Thus the failure/disconnect
messages concern the qualified keyboard's controller/device, rather than an
unidentified unrelated stick. The exact source lines and mapping hashes are
recorded in the analysis. All evidence comes from the existing private Q15
artifact/receipts; no guest, VM, network source or Actions run was started.

**Likely, not independently proved:** the disconnected keyboard explains why
both Enters had no effect. We lack per-resync guest key counts, so no claim
about the exact arrival of either key event. Why the xHCI controller failed is
unproved. An idle process observer proves shell state, not keyboard transport
health. The three identical snapshots also cannot prove every intermediate
screen instant; they prove no retained visible result from either resync.

**Regression / local verification:**4 new mandatory tests use a deliberately
minimized synthetic fixture derived from the exact geometry/row/prompt/failure
shape; diagnostic values, hardware address, timestamps and attributes are
synthetic. Raw Q15 data remains private. The separate local regression executed
the actual exact private VCSA against the retained sudo relay shape. It refused
after2 authorized-but-ineffective Enters and retained3 identical samples.

The same exact private screen was injected into8 later readiness contexts:
US International proof/finish, German begin/proof/finish, rollback, keep-stock,
and final stock logout before Windows. Every context STOPped, without granting
completion. These are counterfactual local failure injections, not claims that
Q15 reached those stages. Busy-foreground tests still send no Enter. A first
new helper assertion accidentally combined the primary and observer timeout
files; it now separately asserts both captures. Runtime code/assertions and
all existing fixtures are unchanged.

`python3 -B` unittest runs of `test_owner_records_prompt`, `test_owner_console`
and `test_owner_sudo_idle` passed **32 tests/55.265s**, zero skips:4 new,
28 old. The existing positive full host walk passed all8 stages,23 hidden
pairs,3 handoffs, US International/back-to-German/rollback/keep-stock, and both
final Windows markers. That walk models a working keyboard/redraw. It is
explicitly **not** a successful recovery of the real disconnected-keyboard
fixture. Every composed guest command and serial wrapper was parsed by real
local Bash with any parse stderr refusing. No VM operation occurred.
[Exact refusal replay](../../os/manifest/ci/14/14zt-local/exact-replay.json),
[positive walk](../../os/manifest/ci/14/14zt-local/walk.json),
[source-bound checks](../../os/manifest/ci/14/14zt-local/verification.json).

**PLAN-GAP / not done:** a positive readiness/resync repair for this state cannot
be justified as a prompt-format correction. Making physical input work after
controller death requires a separately authorized transport/controller diagnosis
or fix. No historical-prompt acceptance, USB reset/fallback, extra Enter,
predicate/log-level/timeout change or invented successful redraw was added.
The requested positive remaining-stage walk with this dead-input fixture is
blocked; the negative walk and healthy-route walk are reported separately.
No new native CI or VM qualification was run; package14 acceptance remains unmet.

Discovery counted544 test cases; the full544-case suite was not executed
this round. Pinned gitleaks8.21.2 full-history (`git . --log-opts=--all`) and
curated-pending scans both found0; the local commit requires a final curated
snapshot scan0 as well. No ignore/rule/workflow was edited.

**Scope / budget:** local only; zero push/dispatch/Actions minutes. Existing
package ledger stays1715/1900,26 probes/15 qualifications. Caps, closing0 and
reserve0 are unchanged. Owner bundle remains
`320ca9878367ee1da4d4634e74d1e3b2de0027d1e7436955f4c69eb21ab806a6`.
INSTALL/EMERGENCY/release gates remain NOT RELEASED. No other worktree, real
laptop device, system software, billing setting, image or publication touched.
No push, dispatch or merge; the next planned CI round is1 November, subject
to the unresolved blocker and fresh authorization/guards.

**JUDGMENT-CALL / open questions:** preserve the existing strict refusal rather
than reinterpret a historical prompt as recovery. Determine the xHCI failure's
cause and authorize an input-transport response before another qualification.
This is an evidence-driven stop, not a tested readiness fix.

**14zs STOP:** probe26 passed; qualification15 stopped after the passed
`corrected-stock records` command, at its physical prompt-readiness wait.
The two completed tty3 logins met the new30s budget. No source fix, rerun or
extra push followed the stop. PR #13 remains draft; this STOP report is local.

## 14zs actual runs — bounded logins confirmed; later prompt-readiness STOP

Both runs used pushed head `65edb1195b12cade6f62d9952f70f5920ad13631`:

| Run | Result | Native suite | Package minutes |
|---|---|---|---:|
| [Probe26](https://github.com/Ares-Empire/AresOS/actions/runs/40892685683) | Independently accepted |540 /120.924s, zero skips |24 |
| [Qualification15](https://github.com/Ares-Empire/AresOS/actions/runs/40897501964) | STOP after corrected-stock records |540 /131.362s, zero skips |66 |

**Verified in the VM:** both `tools-stock` and `corrected-stock` tty3 logins
passed on their first attempt, without a replacement/restart. Runtime login
and agetty report util-linux2.41.5, timeout60s. Observers/counters were prepared
before the username. Measured username-to-verified-Enter windows were
**8.912992063s** and **8.933182460s**, both below the30s bound. The two
visibility observers completed with non-hidden0, unknown0, repeats0 and
SYN_DROPPED0; no current-run visual taint was observed. All4 completed hidden
windows (two account logins and two password-sudo steps) delivered66/66 events
including Return, with zero repeats/drops. No registry token was typed: the
private login/dummy-token stage had not been reached.
[Counts, identities and timing receipts](../../os/manifest/ci/14/14zs-qualification-stop/outcome.json).

The real install/copy, prepare, zero-mutation prepare rerun, first-network
deployment/pin/pending/BLS identity check, record export, refreshed stock title,
unattended Windows roundtrip, corrected-stock boot and password sudo passed.
Nine exported owner records have status passed; no owner command unexpectedly
refused. The corrected stock's saved deployment and German keymap checks passed.
The subsequent `records` owner diagnostic also has status passed.

**STOP / PLAN-GAP:** its completion wait never obtained the strict cursor-line
prompt. Both fresh observers reported the exact sudo-i relay leading to an idle
foreground interactive bash. The wait used both authorized physical Enter
resyncs, with unique receipts; neither restored the cursor-line predicate.
All3 retained VCSA samples are50x160, cursor `(0,49)`, with an empty cursor
line. Public root-prefix rows remain23/33/45 and `PASS records` occurs on row34;
no row ends in the accepted prompt delimiter. The configured90s readiness deadline then
raised `Physical console readiness deadline`. These facts establish the guard's
reason for stopping; **why the Enters did not restore the prompt is unproved**.
No claim of keyboard loss, reader replacement, active-VT change or a kernel
cause. No third Enter, predicate/log-level/limit change or new fix was attempted.
Raw VCSA, the redacted foreground chain, resync receipts and failure log remain
in the private artifact; only geometry/hashes/public process facts are committed.

The original Q14 expiry diagnosis remains source-and-timing evidence, not a
retained exit signal. Its private artifact now also has an explicit companion
visual-policy marker: all raw Q14 VCSA/screenshots/raw-screen fields are tainted,
private and never commit-safe; possible non-hidden events0..64. Its artifact
bytes are unchanged. [Policy metadata](../../os/manifest/ci/14/14zs-qualification-stop/q14-private-visual-policy.json).

**Independent verification:** probe20 native loop checks/zero helper mutations,
28 verified staged transfers and raw audits3 protected captures/4 zero-write
samples/3 BootNext/2 NVRAM-all-variable comparisons. Qualification131 staged
transfers verified SHA/syntax; raw replay passed9 protected captures,10 zero
write/unmap samples,9 BootNext checks and8 NVRAM/all-variable comparisons.
All detached-device, Windows-first and firmware audit rules are unchanged.
Both native runs explicitly passed the unchanged30s timing case. Native and
VM failure logs each scan0. Final local command-equality/manifest-refusal tests:
2 passed/.980s; `git diff --check` passed; runtime/tests/payload/release/guides/
workflow/privacy diff against the pushed head is empty.
[Safety replay](../../os/manifest/ci/14/14zs-qualification-stop/qualification-audits.json).

**Privacy:** probe509 findings =507 reviewed public ISO-listing names +2 exact
kernel certificate lines. Qualification517 =507 ISO names +10 exact kernel
certificate lines. Unclassified0; no ignore/rule/workflow changes. Each allowed
kernel occurrence is recorded below by whole-line hash, private path/line and
certificate label. No raw boot console, VCSA or screenshot is committed.

| SHA-256 of whole source line | Occurrence | Public certificate label |
|---|---|---|
| `2ccb076755b1bfe99bf34f3efbf4c516c621301d2f372e9511d53b882f6f48dc` | Probe26: `evidence/two-disk/live-ui-probe-boot-console.txt:497` | Fedora kernel signing key |
| `0943e71d027ce9b60582042ea3e6e1923d1dbce0c9c3ac47d3d82588a45aa5d9` | Probe26: `evidence/two-disk/live-ui-probe-boot-console.txt:530` | Fedora kernel signing key |
| `49ccdcc339a9507a41bfa52f00016449326dfae5fd6233a544eb095158619952` | Qualification15: `evidence/two-disk/corrected-stock-boot-console.txt:498` | Build time autogenerated kernel key |
| `632d9645e71bb8274e8a1d879889018cb64e962c1fb6bec41e3708ee181bbd8a` | Qualification15: `evidence/two-disk/corrected-stock-boot-console.txt:508` | Build time autogenerated kernel key |
| `39610970917955d5d67fb2a960d6a915339d0b5026d85a5b86ac85244b3060d7` | Qualification15: `evidence/two-disk/offline-first-stock-boot-console.txt:498` | Build time autogenerated kernel key |
| `72e0477ad291a46082da5ec21776df7168e6b6a7a911e950aa0062088428b3b7` | Qualification15: `evidence/two-disk/offline-first-stock-boot-console.txt:517` | Build time autogenerated kernel key |
| `69030d052b2db7a8871212379e9335b71ab3c7459ddb728e276219a7a4878a9f` | Qualification15: `evidence/two-disk/stock-initialization-0-boot-console.txt:499` | Build time autogenerated kernel key |
| `2e682aa663bbf0db73801fdefe58b9a99c2d0c345cc6954a4cd82f0d63dee2a2` | Qualification15: `evidence/two-disk/stock-initialization-0-boot-console.txt:522` | Build time autogenerated kernel key |
| `5804c2e2c951b31ff17937e4a127f5cf6fd198d3a41f47e044fb90010e429767` | Qualification15: `evidence/two-disk/protected-second-install-boot-console.txt:491` | Fedora kernel signing key |
| `acd683d99e60cd03a1eeadfc43bcfe7b1f9835cbfff9c0e4ca49653e891b5993` | Qualification15: `evidence/two-disk/protected-second-install-boot-console.txt:524` | Fedora kernel signing key |
| `83fb21d99aea6939f56a3e8f23891dcd357bc2d344dd31e4a42dacc6075e9ed0` | Qualification15: `evidence/two-disk/tools-stock-boot-console.txt:509` | Build time autogenerated kernel key |
| `e8ddbdbe9b3ae23d5a70f2c5adcb9b22a6cbee514fbb7ef1b7cf55c3df5ebe7e` | Qualification15: `evidence/two-disk/tools-stock-boot-console.txt:524` | Build time autogenerated kernel key |

**Budget / closing:** complete142/142 history, **1715/1900 minutes**:
1619 prior +6 push privacy +24 probe +66 qualification. Counts:26 probes,
15 owner qualifications. Exactly1 FF push,1 fresh probe and1 qualification;
reruns0. Closing read-only$10/prevent=true snapshot reports net$8.304 charged
and282 available minutes at that time; this is the API's reported charged
snapshot, not an assertion that all new usage has settled. No billing/budget
write occurred. Reserve0/closing0 remain because acceptance is unmet; no final
push or ready transition. [Complete closed ledger](../../os/manifest/ci/14/14zs-qualification-stop/closed-ledger.json).

**Not verified:** the later tty4 failure/revert/restart path in a VM; private
login and40-character dummy; verify/switch; AresOS boot and keymaps; plain-US
refusal/revert, US International and final German proof/finish; rollback,
keep-stock and final Windows checks. Those local stand-in paths were walked,
but are not passing VM evidence. Full package14 acceptance is **unmet**.
Owner bundle remains `320ca9878367ee1da4d4634e74d1e3b2de0027d1e7436955f4c69eb21ab806a6`;
INSTALL/EMERGENCY/release gates remain NOT RELEASED. No owner script, image,
publication, physical laptop or other worktree changed.

**JUDGMENT-CALL / open questions:** source-verified getty Ctrl-U/Ctrl-D restart
is documented in the preparation section; no restart was needed in these two
VM logins. Investigate the blank cursor-line/prompt resync failure from retained
evidence in a later authorized follow-up. This round is over; no more Actions
dispatch is authorized, and the owner can set the Actions budget back to$0.

## 14zs REPORT — bounded physical logins and safe reader replacement

**Done:** harness only. All tty3/tty4 logins prepare root-only tmpfs observers,
count-only keyboard counters and checksum-verified short control commands before
the username. The original hidden-reader, echo, three-sample, count, SHA/export
and prompt checks remain mandatory. Immediately before the password and Enter,
the same login PID/start identity and remaining half-timeout budget are checked.
No secret is sent without authority. The measured guest window includes username
through verified Enter; host time is an additional bound. No timeout was raised.

The pinned ISO has no active LOGIN_TIMEOUT override; util-linux2.41.5 uses60s,
with one alarm across authentication retries. The Q14 wrong-password and reverted
login reused PID13852; first hidden readiness to replacement receipt is66s
(ZIP timestamp resolution2s). This supports expiry; the exit signal itself was
not retained. [Pinned source, configuration, hashes and receipt metadata](../../os/manifest/ci/14/14zs-login-sources/timeout-proof.json).
Primary sources: [login.c](https://github.com/util-linux/util-linux/blob/230de59ffbee328506d92d3534e66d56de1afe5d/login-utils/login.c)
and [agetty.c](https://github.com/util-linux/util-linux/blob/230de59ffbee328506d92d3534e66d56de1afe5d/term-utils/agetty.c).

Reader replacement withholds Enter, verifies the new public reader, sends and
counts Ctrl-U, and proves a fresh getty prompt before one whole-login restart.
**JUDGMENT-CALL:** source-verified public agetty Ctrl-D, also counted, obtains a
new getty lifetime after line kill; it avoids trusting visual erasure of arbitrary
username bytes or an old login alarm. It cannot authenticate. Unsupported readers
or unproved clear refuse; a second replacement STOPs. No owner command changed.

The visibility observer retains only hidden/non-hidden/unknown event counts;
PID transitions, dropped or incomplete observations conservatively taint the
whole run's VCSA/raw screen fields/screenshots. Required OCR capture continues,
privately; raw visuals from a tainted run must never be committed. Q14 is
retroactively marked tainted: possible non-hidden secret events0..64, not an
invented exact count. Only hashes/times/counts are committed here.

**Verified locally:**14 focused login tests/7.473s,13 existing sudo/idle
tests/5.269s and4 controller tests/.006s passed. Cases include budget refusal
with zero secret typing, Q14 replacement, one restart, second replacement STOP,
strict generated-helper execution/export/checksum refusal, count-only visibility,
root-only staging, and preserving required private OCR captures. Earlier local
suite attempts were interrupted during implementation and are not passing
evidence. Final frozen-source suite:540 tests/879.542s, 531
distinct passes, 9 previously approved host limitations, zero skips.
The unchanged30s local timing test measured[55.74063323600001]; every540 test remains
mandatory in native CI, where any failure is a STOP. No test/bound/skip changed.

The actual pinned ISO replay passed on its first fresh checkpoint, with fresh
official checksum, exact length/SHA,53-source/release/git replay and four
credential-dependent checks explicitly CI-only under14f. No credential/scope
change or owner secret. The stand-in walk covers all8 stages,23 hidden pairs,
3 handoffs and no uncovered wait. Strict checks cover860
composed guest commands/wrappers, 722 embedded Python
blocks and the actual prepared helper; any Bash parse stderr refuses.
[Source-bound preparation](../../os/manifest/ci/14/14zs-preflight/preparation.json).

**Scope / budget / pending:** owner bundle fingerprint remains
`320ca9878367ee1da4d4634e74d1e3b2de0027d1e7436955f4c69eb21ab806a6`.
Owner scripts, INSTALL/EMERGENCY, frozen release/image paths, package13, privacy
workflow/rules/ignores and14s/14v classifier are unchanged. Physical gates remain
NOT RELEASED. Complete138/138 baseline:1619 +238 =1857/1900; read-only$10,
prevent=true, charged net deducted, org margin74 at that snapshot. Only package14
cap1900/probe27/owner-tools16 changed, closing/reserve remain0 for this dispatch.
Fresh guards are mandatory immediately before the one FF push and each dispatch.
Fresh exact-head privacy(all3 actual steps) precedes probe26; only accepted
probe26 permits qualification15 on the same head. Any CI stop: diagnostics,
report, no rerun. Acceptance alone permits closing12/reserve150 restoration,
one final push/closing privacy and ready status. Never merge.

**Not verified / open questions:** this head's native probe and full VM recovery
route; all real-laptop/physical gates. No real laptop or other worktree touched.
No new PLAN-GAP. Owner resets the Actions budget to0 when the round ends.

**14zr STOP:** the loginctl fix and scoped journal are confirmed in the VM.
Probe25 passed. Qualification14 passed plain-US refusal and layout revert,
then the tty4 hidden-reader guard withheld Enter when its verified login
process disappeared. No rerun, product fix or extra push. PR #13 stays draft;
this STOP report is committed locally.

## 14zr actual runs — properties fixed; later tty4 reader replacement STOP

Both runs used pushed head `a247ee898598636aee3f9cd1d9e60c01632d0280`:

| Run | Result | Native suite | Package minutes |
|---|---|---|---:|
| [Probe25](https://github.com/Ares-Empire/AresOS/actions/runs/40863215153) | Independently accepted |526 /105.897s, zero skips |22 |
| [Qualification14](https://github.com/Ares-Empire/AresOS/actions/runs/40866713472) | STOP at reverted tty4 login pre-Enter guard |526 /102.550s, zero skips |68 |

**Fix confirmed:** `layout begin us` and `layout revert` passed on AresOS.
Their6 actual loginctl queries use separate `--property=` options and return
every requested Key=Value exactly once, in the real systemd output order.
Identity, audit id, scope, login start, Service/Type/Remote/Name/User checks
all passed. No session predicate was relaxed. The real post-staging hold
exclusion was observed twice again; switch, refreshed title, AresOS boot,
physical tty3 login/password sudo and `check` passed.
[Exact property commands/output](../../os/manifest/ci/14/14zr-qualification-stop/property-proof.json).

The bounded previous-boot logind query returned24 JSON records, all transport
`journal`, with **zero kernel records**. The full-boot query was not run.
Qualification artifact privacy:519 findings =507 reviewed ISO-listing
findings +12 permitted whole kernel boot-console lines; unclassified0.
Probe509 =507 ISO +2 whole kernel lines. No decoded-MESSAGE exception, ignore,
rule or workflow change was needed. Native and VM failure logs scan0.
[Scoped-journal proof](../../os/manifest/ci/14/14zr-qualification-stop/journal-proof.json).

**STOP / PLAN-GAP:** the deliberate plain-US physical-key login was rejected,
and an attempted reboot during the unproved layout trial correctly refused
with zero mutations. The original tty3 administrator stayed available;
`layout revert` round-tripped the saved German settings. The subsequent
tty4 login reached the correct hidden password prompt with foreground
`login` PID13852, canonical input, ECHO off and syscall0/read. Before Enter,
that PID had disappeared and foreground PID20186 was an unexpected reader.
The guard correctly refused: `No unchanged hidden reader waiting in read;
Enter withheld`. It did not send Return, Ctrl-U, a retype or another attempt.
The retained diagnostics prove reader replacement; they **do not establish
why the old login exited**. Its proc files were absent; the replacement was
sleeping in syscall270 with wchan `poll_schedule_timeout.constprop.0`.
No claim that a timeout or a particular replacement executable is proved.
[Guard, counter and non-secret diagnostics](../../os/manifest/ci/14/14zr-qualification-stop/hidden-reader-stop.json).

The stopped30-character password window delivered **64/64 key events**
(32 presses +32 releases), repeats0, SYN_DROPPED0, keys released,21.825s.
`last_key_was_ret=false`. The counts prove no observed event loss, not the
old reader's exit cause. There were10 hidden windows with matching counts;
9 completed/read-rejection transitions and this guarded stop. The40-character
dummy delivered116/116 events and got the expected registry refusal. The
377-character CI token delivered1118/1118 events and authenticated. Totals
vary with generated modifiers; no credential value or ordered key codes were
retained. All10 windows used one attempt, zero clears/retypes,30ms holds and
minimum120ms gaps. [Counts and records](../../os/manifest/ci/14/14zr-qualification-stop/outcome.json).

The qualification contains19 owner records:17 passed and2 expected refusals
(dummy registry login and unproved-trial reboot). Its unexpected stop was in
the harness's hidden-input guard, not an owner-command refusal. All267 staged
transfers verified SHA and Bash syntax;36 visible-input echo proofs passed.
The paused VM STOP is retained. Independent raw replay passed10 protected
captures,11 zero-write/unmap samples,10 BootNext checks and9 NVRAM/all-variable
comparisons. Protected disks, detached-device rules, Windows firmware default,
firmware grammar and all safety gates remain unchanged.
[Raw safety replay](../../os/manifest/ci/14/14zr-qualification-stop/qualification-audits.json).

**Not reached / not verified:** fresh tty4 login after revert; its proof and
finish; US International trial/proof/finish and boot; final German proof and
boot; remaining labwc physical typing; rollback; keep-stock; final Windows
checks. The German setting was restored, but the trial remains pending and
unproved; a reboot was not authorized. Full package14 acceptance is **unmet**.
INSTALL/EMERGENCY/physical release gates remain NOT RELEASED.

**Budget / closing:** complete138/138 history, **1619/1800 minutes**:
1523 previous +6 push privacy +22 probe +68 qualification. Counts:25 probes,
14 owner qualifications. Exactly1 FF push,1 probe and1 qualification in this
follow-up; reruns0. The closing read-only$10/prevent=true budget snapshot
reports net$8.124 charged,312 available minutes. No budget API write occurred.
Reserve0/closing0 stay because acceptance was not met; no final push or ready
transition. This round is over; the owner can set Actions budget back to$0.
[Complete closing ledger](../../os/manifest/ci/14/14zr-qualification-stop/closed-ledger.json).

**Verified commands:** pinned gitleaks8.21.2 full-history (`git .
--log-opts=--all`) and curated-pending scans0 before the single push;
`python3 -B -m unittest discover -s os/tests -v` under existing WSL attempted
526 locally with only the9 approved14zm host limitations, then all526 passed
natively on both runs. The strict805-command/wrapper/799-embedded-Python
checks, full pinned ISO/fresh-checksum replay, release/git/53-source replay,
exact-head privacy's3 actual steps on both events, complete ledger/billing/
budget guards, independent probe review and final raw qualification audit
were executed. Local qualification ISO replay passed on attempt1. Product
source, generated payload, guides, workflow and privacy policy remain the
exact pushed head after this STOP; only report/accounting/evidence are added.

Final local STOP verification:2 manifest-order/payload-equality tests passed
in20.294s; `git diff --check` passed. The runtime/guide/privacy diff against
the pushed head is empty. Pinned full-history gitleaks is0; the local STOP
commit is gated on a fresh curated-pending scan with0 findings. Repository
privacy and PR draft state were rechecked. No additional Actions dispatch.

**JUDGMENT-CALL / open questions:** none changing owner behavior. Determine
why PID13852 exited during the reverted login window, using retained facts
and pinned login behavior. Any fix needs a later authorized follow-up; no
reader/identity predicate was loosened and no secret was automatically retyped.

Every accepted certificate occurrence is recorded below by source-line hash;
raw lines and fingerprint values stay in the private artifact only:

| Source-line SHA256 | Private artifact path:line | Certificate label |
|---|---|---|
| `99efc6ef27a9a84adf890257ade5fe9e4c70610439bd38ab82f0435e8f924ddb` | Probe25: `evidence/two-disk/live-ui-probe-boot-console.txt:496` | Fedora kernel signing key |
| `894a2fd45676374de68013315b6bf69dbeb92ebe614bfc39ada697df16e95441` | Probe25: `evidence/two-disk/live-ui-probe-boot-console.txt:529` | Fedora kernel signing key |
| `1eb8d7b777e7b2c9751b573445810fcbc4bff66160f85bd917d83f6dbdf465a7` | Qualification14: `evidence/two-disk/aresos-boot-console.txt:503` | Build time autogenerated kernel key |
| `31e2d7766898de605ac78dddc16a7465e5e2b26279e648b24dfe4c1d6f5ddee1` | Qualification14: `evidence/two-disk/aresos-boot-console.txt:513` | Build time autogenerated kernel key |
| `1cf339ee844afc020461183afa81fa5346d9266313a762f7f76d4591b3817a53` | Qualification14: `evidence/two-disk/corrected-stock-boot-console.txt:503` | Build time autogenerated kernel key |
| `0f1389df363c9fb44f9ed977d065f947ae1518a83f09e4aa8b996ef1c28caf1a` | Qualification14: `evidence/two-disk/corrected-stock-boot-console.txt:513` | Build time autogenerated kernel key |
| `c2db7812c96b178e961595fdb6814a4a6c86d56097104a68842a3a4718f20295` | Qualification14: `evidence/two-disk/offline-first-stock-boot-console.txt:503` | Build time autogenerated kernel key |
| `94c868d121f7eebd662d289e4088dfee056e5de3400ef4bd9e56b05c9f719de0` | Qualification14: `evidence/two-disk/offline-first-stock-boot-console.txt:517` | Build time autogenerated kernel key |
| `2d8f87d0c555b5ff8d9e78360319f7e779947f642dfcdc100a7fb68cf69b9f6c` | Qualification14: `evidence/two-disk/protected-second-install-boot-console.txt:496` | Fedora kernel signing key |
| `db3f2cbf855031ef119424dc76372374de12a9596d94989488427fe76ae71310` | Qualification14: `evidence/two-disk/protected-second-install-boot-console.txt:529` | Fedora kernel signing key |
| `d97e4a2243677be41bb2120e091a8e6de093586da9bbabcbfa4da5ff51c9d85c` | Qualification14: `evidence/two-disk/stock-initialization-0-boot-console.txt:503` | Build time autogenerated kernel key |
| `fcacc5b034e5bfd3628a441cb2d517d0ce04f8ef9427578af4cfbdc8591bca07` | Qualification14: `evidence/two-disk/stock-initialization-0-boot-console.txt:513` | Build time autogenerated kernel key |
| `cd4fca8ac4f6242c403679232ff2a4ec292eaf9f99d8a2abb7b990d5aed34cba` | Qualification14: `evidence/two-disk/tools-stock-boot-console.txt:503` | Build time autogenerated kernel key |
| `145c22f960ae3df55815771148d39cddddd8c0c1cc51c9aba0fe02ade3906962` | Qualification14: `evidence/two-disk/tools-stock-boot-console.txt:513` | Build time autogenerated kernel key |

## 14zr REPORT — literal loginctl selectors and bounded diagnostics

**Done:** all3 owner `show-session` queries now pass one `--property=` per
name. A shared parser requires each requested Key=Value exactly once,
independent of output order; duplicate, missing, extra, blank and malformed
rows refuse. All existing recovery session facts and physical sudo-relay
checks remain mandatory. The old test stand-ins that invented successful
comma-joined results now implement loginctl's literal selector matching.
Fixtures show both old comma queries returning empty output.

The requested systemd258 source and actual pinned-image259.9 source are both
verified and archived. `systemctl` explicitly splits comma lists; `loginctl`
does not. `busctl` uses positional property names / typed method results;
`localectl` uses positional setting arguments; systemd-run options are unit
assignments. Every payload/harness `--property` / standalone `-p` was audited.
[Tool-by-tool audit and exact primary-source citations](14zr-properties-audit.md).

`logs` now captures the previous boot's logind unit only, at most200 JSON
records. The full-boot journal read is removed. The tool has no dedicated
service unit; its own trace/result are already recorded privately. The source
unit filter has no matching origin for unrelated kernel boot certificates, so
the conditional decoded-MESSAGE exception is not needed. The14s/14v artifact
classifier and all rules/ignores/workflows are unchanged; journal JSON cannot
silently become an allowed whole boot-console line. Any such unexpected
finding is a STOP. Historical Q13 findings are not reclassified.

**Verified locally:**6 property/journal tests/.060s,16 session/.904s,
4 real-format/.045s,10 guard/.092s and4 local controller/.005s passed.
An initial new test mixed its explicit negative query call history with the
subsequent owner-route history; its setup was separated, then all6 passed.
No assertion or production requirement was weakened.

The full suite attempted526 tests in791.896s: 517 distinct
passes, 9 approved14zm host limitations, zero skips. Local timing
measurements: [54.607805094000014]. All526 tests
remain mandatory in native CI; a native failure is a STOP. The full pinned
ISO replay passes with fresh official checksum, and the14e/14f release/git/
53-source replay passes. CI-only registry steps retain their recorded reasons
and fail closed in CI; no credential or scope was changed.

The current stand-in walk covers all8 stages,23 hidden pairs and3 handoffs,
with no uncovered wait. Strict parsing covers805 guest
commands and wrappers and799 embedded Python blocks;
any Bash parse stderr is a refusal. The local qualification reviewer also
uses the regenerated bundle fingerprint and the actual retained switch-record
directory. [Source-bound preparation](../../os/manifest/ci/14/14zr-preflight/preparation.json).

The first standalone walk invocation used Windows Python and refused at its
Linux `fcntl` import; the identical script then passed under existing WSL.
ISO replay attempts1–3 hit the documented Windows checkpoint replace
WinError5. Attempt4 passed after the authorized10/20/30-second waits on fresh
paths, with no overlapping ISO replay and no Linux CI behavior change.

Final manifest-order/payload equality:2 tests/5.244s pass; `git diff --check`
passes. To reserve space for the later qualification replay, only two ended,
byte-identical14zq qualification cache files (ISO and squashfs) were removed
after resolved-path and full-hash checks. Canonical inputs and all diagnostics
remain. [Cleanup evidence](../../os/manifest/ci/14/14zr-preflight/cache-reclaim.json).

**Current bundle / For package15:**
`320ca9878367ee1da4d4634e74d1e3b2de0027d1e7436955f4c69eb21ab806a6`.
Generated Windows/CI payload equality and INSTALL's current copy/check pin
agree. Historical evidence keeps its historical pins. Package15's worktree
was not touched. No harness runtime, release script, image, publication,
firmware audit or physical gate changed. INSTALL/EMERGENCY retain NOT RELEASED.

**Budget / pending:** complete134/134 history:1523 +238 =1761/1800 pre-push.
The read-only$10/prevent=true guard deducts charged net spend and leaves170
org minutes after reservation. Only package14 cap1800/probe26/owner-tools15
changes; package13 stays byte-for-byte unchanged. Exactly one FF push is
allowed after pinned gitleaks0 and local checks. Fresh exact-head privacy
(all3 actual steps), ledger/billing/budget precede probe25. Only accepted
probe25 permits qualification14 on that same head. Any CI stop gets exported
diagnostics and no rerun. Closing12/reserve150 and ready status are restored
only after acceptance. Never merge; owner resets budget0 when the round ends.

**Not verified / open questions:** actual layout begin/proof/revert/finish and
the complete remaining VM recovery route on this head; all real-laptop gates.
No real laptop touched. No new JUDGMENT-CALL or PLAN-GAP beyond the documented
258 audit versus actual259.9 image version; both formats were checked.

**14zq STOP:** the hold fix is confirmed in the real VM. Probe24 passed;
qualification13 passed `switch`, refreshed `title`, AresOS boot and `check`, then
STOPped at `layout begin us` before any layout mutation. Four artifact findings
also fall outside the permitted privacy classes. No rerun, post-stop product
fix or extra push. PR #13 stays draft; this STOP report is committed locally.

## 14zq actual runs — hold fixed; layout property selector and artifact privacy STOPs

Both runs used pushed head `2755c70bd138678557ff0e44ead6d33fa7cabcc6`:

| Run | Result | Native suite | Package minutes |
|---|---|---|---:|
| [Probe24](https://github.com/Ares-Empire/AresOS/actions/runs/40841171586) | Accepted |520 /132.061s, zero skips |25 |
| [Qualification13](https://github.com/Ares-Empire/AresOS/actions/runs/40844950597) | STOP at layout session gate |520 /130.754s, zero skips |81 |

**Actual hold confirmation:** two post-staging process observations record
PID25368, executable `/usr/bin/ostree`, exact argv
`[/usr/bin/ostree, admin, finalize-staged, --hold]`, and exact cgroup
`0::/system.slice/ostree-finalize-staged-hold.service`. Both record
`excluded_as_system_helper=true`, `excluded_as_daemon=false`. The switch and
its explicit refreshed-title command passed; the VM rebooted into the exact
AresOS release and `check` passed. This supplies the actual runtime evidence
that Q12 lacked. It does not retroactively invent Q12's detected PID.
[Actual process observations](../../os/manifest/ci/14/14zq-qualification-stop/hold-confirmation.json).

**Layout STOP / PLAN-GAP:** the physical AresOS tty3 account login and password
sudo passed. `layout begin us` got through the recovery state and disk gates.
`loginctl list-sessions --json=short` identified session5 as `ares-recovery`,
UID1000, tty3. The next command was:
`loginctl show-session 5 --property=Id,TTY,Audit,Scope`.
It returned0 with **empty stdout and stderr**. The owner tool correctly
refused its required four-property shape with
`Use a physical tty3/tty4 recovery login`. The failed command's trace has
**zero mutation calls** and stopped before saving a layout trial or changing
settings. No session fact or relay requirement was relaxed.
[Exact command/output and refusal](../../os/manifest/ci/14/14zq-qualification-stop/layout-session.json).

Read-only inspection of the pinned-version upstream systemd259.9 source at
`63c0371fa71ae32ba02f05f90658bc40aaa19168` explains the result:
[`loginctl` stores each property argument as one selector](https://github.com/systemd/systemd/blob/63c0371fa71ae32ba02f05f90658bc40aaa19168/src/login/loginctl.c#L1572),
and [the printer matches property names exactly](https://github.com/systemd/systemd/blob/63c0371fa71ae32ba02f05f90658bc40aaa19168/src/shared/bus-print-properties.c#L380).
It does not expand the comma-separated argument into four names. The same
assumption affects the subsequent comma-joined facts query. Correct selector
spelling with all existing facts preserved needs its own authorized fix and
real-format regressions; none was made after this CI stop.

**Typing / other evidence:**8 hidden windows and their8 completion transitions
passed, with16 blocked-reader guards and32 current-cursor echo proofs. Every
window had exact press/release counts, keys released, repeats0, SYN_DROPPED0,
one attempt and no Ctrl-U/retype. The fresh40-character dummy had114/114 events
and the expected registry refusal; the real377-character CI token had
1100/1100 events (550 presses +550 releases),91.169s, and authenticated. These
totals include the verified Return. Modifier totals vary with each generated
value.30ms holds/minimum120ms gaps and the16-character/1s token schedule stayed
unchanged. No secret values or ordered event codes were retained.

Qualification retained241 SHA/syntax-verified transfers and17 owner records:
15 passed, expected dummy refusal, and the layout STOP. The paused VM STOP is
retained. Raw independent replay passes10 protected captures,11 zero-write/
unmap samples,10 BootNext replays and9 NVRAM/all-variable comparisons. The
protected disk, detached-device rule, Windows firmware default and firmware
audit are unchanged. Both native520-test suites explicitly passed the unchanged
30-second serial test; native and VM failure logs scan with pinned gitleaks:0.
[Counts, completions and records](../../os/manifest/ci/14/14zq-qualification-stop/outcome.json).

Final report/evidence verification:2 manifest/payload equality tests passed in
11.173s; `git diff --check` passed; pinned local full-history and curated-pending
gitleaks scans report0. The runtime, owner bundle, guides, workflow and privacy
policy remain exactly pushed head2755c70. The artifact privacy STOP remains.

**Artifact privacy STOP:** probe509 =507 reviewed ISO-listing findings +2
approved exact kernel messages. Qualification has **523 findings**:507 ISO,
12 approved exact boot-console messages, and **4 unclassified findings**:

| Source-line SHA256 | Private artifact path:line | Findings |
|---|---|---:|
| `1499d081b9068409c35ad9610056b59eff1e82add2c830b4044707ee62f66ca4` | `evidence/two-disk/owner-logind-diagnostics-owner-diagnostics.json:30` |2 |
| `1499d081b9068409c35ad9610056b59eff1e82add2c830b4044707ee62f66ca4` | `evidence/two-disk/owner-logind-diagnostics-owner-result.json:30` |2 |

All4 are generic-api-key matches redacted as `key: REDACTED'`. Decoded journal
stdout contains two X.509-shaped messages labelled `Build time autogenerated
kernel key`, repeated in result and diagnostics. That is **candidate context,
not an accepted classification**: the original matched source line is escaped
JSON journal stdout, not an exact whole kernel line in a captured boot-console
file. The unchanged14s/14v classifier refuses it. No ignore, rule, workflow or
exception was added; no raw source line or fingerprint value was committed.
[Refused finding metadata](../../os/manifest/ci/14/14zq-qualification-stop/qualification-privacy-stop.json).

Each approved kernel source line is recorded separately, SHA256 before path:

| Source-line SHA256 | Private artifact path:line | Certificate label |
|---|---|---|
| `f0209c07357d7fb1780b58b9ade61416ec304dd50cf1d5a28bbc5f783bd0c039` | Probe24: `evidence/two-disk/live-ui-probe-boot-console.txt:491` | Fedora kernel signing key |
| `ab737edfff4461ff20d48b88d03f0673ab373135b4398c3bd43fadbc8f34148a` | Probe24: `evidence/two-disk/live-ui-probe-boot-console.txt:524` | Fedora kernel signing key |
| `0825dac067b1c6db192622cc1d16a12a92554f54330d763a938746dc51222699` | Qualification13: `evidence/two-disk/aresos-boot-console.txt:498` | Build time autogenerated kernel key |
| `dc8ada5d03bdcdb7dbb6fd7f821732e626b0d75a6e933c039474e9509b527916` | Qualification13: `evidence/two-disk/aresos-boot-console.txt:519` | Build time autogenerated kernel key |
| `e3f034fe5ec43af9fafd580c44d0f4297f04d60672da41526d3a3b090e499163` | Qualification13: `evidence/two-disk/corrected-stock-boot-console.txt:498` | Build time autogenerated kernel key |
| `9b1f74cac7a5be361b253f4d165f12ce2523ff9394b18e23e84e07f0b0dc0240` | Qualification13: `evidence/two-disk/corrected-stock-boot-console.txt:508` | Build time autogenerated kernel key |
| `11582f7337ec13099e813a6b0427c35e3a3e5d493578bfe19978c26586a6df11` | Qualification13: `evidence/two-disk/offline-first-stock-boot-console.txt:498` | Build time autogenerated kernel key |
| `f111976d64fe05ba0cb493e202b5d618f8dd8c85d27ce74489339fcd512b09af` | Qualification13: `evidence/two-disk/offline-first-stock-boot-console.txt:516` | Build time autogenerated kernel key |
| `48400d856c6c0ccabbc79d4495f56014d63494ce3e76f6d23b5c3e062b53e1e8` | Qualification13: `evidence/two-disk/protected-second-install-boot-console.txt:491` | Fedora kernel signing key |
| `f28a5882a4c932d610a826c92d5323ffed854b693d68cb13ab12e8eb24261a28` | Qualification13: `evidence/two-disk/protected-second-install-boot-console.txt:524` | Fedora kernel signing key |
| `ba4737cbee0c6eff60a9452c22838a3e7f21384a854cecbab74cbb479bd94201` | Qualification13: `evidence/two-disk/stock-initialization-0-boot-console.txt:498` | Build time autogenerated kernel key |
| `9514637e96933321f6c0eb7e3e49d4ea5f892733be9ed9a7d6cde13df53c77f3` | Qualification13: `evidence/two-disk/stock-initialization-0-boot-console.txt:509` | Build time autogenerated kernel key |
| `b0d2e9b4f195b7d0cb2f2e7c75d8f4149b0b5c3bce68596a24527b04b7d2a454` | Qualification13: `evidence/two-disk/tools-stock-boot-console.txt:498` | Build time autogenerated kernel key |
| `f3c1fdaaaaf183879b86eb31e58121ed349fb390462658043e681b0ff7f81600` | Qualification13: `evidence/two-disk/tools-stock-boot-console.txt:509` | Build time autogenerated kernel key |

**Closing state:** complete134/134 history, **1523/1700** minutes consumed,
24 probes /13 owner qualifications cumulatively. This round used one FF push,
one probe, one qualification and zero reruns. Exact-head push/PR privacy both
executed all3 required steps. The read-only$10/prevent=true billing snapshot
reports$7.548 net charged and
408 minutes available; it is a timestamped snapshot.
Reserve0/closing0 remain because acceptance is unmet. No final push or ready
transition occurred. The run is over; the owner can set the budget back to$0.
[Complete closing ledger](../../os/manifest/ci/14/14zq-qualification-stop/closed-ledger.json).

**Not verified / open questions:** authorize the exact loginctl selector fix
with real CLI-format tests, and classify the4 journal-JSON findings explicitly
before another run. The plain-US failure/revert, US International success/
proof/finish, final German proof, later labwc typing, rollback, keep-stock and
final Windows checks were not reached. INSTALL/EMERGENCY/release gates retain
NOT RELEASED and all physical/For package15 gates. Bundle remains
`025622f56d61f669912ce9d6320e7171e2007194420c79ce54dc6b89a0570486`.
No image rebuild, release, publication, real-laptop work, merge or force push.

## 14zq REPORT — exact post-staging hold helper

**Done:** the owner tools and both shared pause-script bodies classify only the
verified `/usr/bin/ostree admin finalize-staged --hold` in the exact cgroup
`/system.slice/ostree-finalize-staged-hold.service` as
`excluded_as_system_helper`. The full argv, executable path and single cgroup-v2
membership must all match. Wrong argv/cgroup/executable remains a client.
Shutdown finalizers remain clients. The existing daemon exclusion and mandatory
transaction null check are unchanged. A single client filter is used by both
script bodies and all owner idle/prepare callers. Process classifications are
recorded in private owner diagnostics before a possible refusal.

The pinned ISO's RPM database verifies ostree2026.4, bootc1.16.13 and systemd259.9.
Read-only `unsquashfs -cat` gives these unit commands; expected cgroups follow
the verified default system-service slice, with no Slice/ExecStart override:

| Unit | ExecStart | ExecStop | Expected cgroup |
|---|---|---|---|
| ostree-finalize-staged-hold.service | `+/usr/bin/ostree admin finalize-staged --hold` | none | `/system.slice/ostree-finalize-staged-hold.service` |
| ostree-finalize-staged.service | none | `/usr/bin/ostree admin finalize-staged` | `/system.slice/ostree-finalize-staged.service` |
| bootc-finalize-staged.service | none | `/usr/bin/bootc composefs-finalize-staged` | `/system.slice/bootc-finalize-staged.service` |

There is no finalize-staged `.path` unit in this pinned listing. The pinned
ostreev2026.4 source starts `ostree-finalize-staged.service` programmatically;
its Wants/After dependency starts the hold unit. The hold branch loads the
sysroot unlocked, holds `/boot` and waits for SIGTERM. The actual finalizers run
at shutdown. The generic service drop-in only sets timeout abort behavior.
[Exact unit/source hashes and RPM provenance](../../os/manifest/ci/14/14zq-finalize-sources/index.json).

**Retained-evidence limitation / PLAN-GAP:** Q12's exported STOP record proves
successful exact staging and the subsequent client-active refusal. It does not
retain that client's PID/argv/cgroup. A complete JSON traversal finds only the
earlier real rpm-ostreed PID12599 from prepare. That real row and the real
Q12 staged/prepared state are fixtures. The hold PID and post-staging reuse of
the pre-stage BLS list are explicitly labelled unit-derived/model fixtures,
not claimed as observed Q12 processes/BLS. Future diagnostics now record the
process list; acceptance additionally requires an actual correctly classified
post-staging hold in the successful switch record. No missing process identity
is invented or used to authorize a broader exclusion.

**Verified locally:**9 finalize regressions/2.578s,6 stock-idle/.319s,
10 budget/.202s and4 no-repeat dispatch-controller/.016s pass. The tests execute
the real proc classifier against file fixtures and refuse wrong argv/cgroup,
real clients, shutdown finalizers and active/unknown transactions with no
mutation. Retained staged-state title/records tests pass, stale-title reboot
refuses, fresh-title mocked reboot passes, and verify/layout/recovery keep
their state refusals. [Every staged-capable gate](14zq-staged-gates.md) was
reviewed; no state, media, disk, firmware or session predicate is relaxed.

Whole local suite:520 attempted in835.541s, 511 distinct passes,
9 approved host limitations, zero skips. The unchanged30-second case
measured54.72680228400009s locally;14zm's host-timing decision
applies locally only. All520 tests, including that bound, remain mandatory in
native CI; any native failure stops this round. Frozen-image payload, workflow,
privacy policy and the PIN_STOCK mutation tail are unchanged.

The current stand-in walk covers all8 stages,23 hidden pairs and3 public
handoffs with no uncovered wait. Strict checks parse805
guest commands and wrappers and799 embedded Python
blocks; any parse stderr refuses. Full pinned ISO replay passed on attempt2:
attempt1 had the documented Windows checkpoint replace WinError5, then the
authorized10s retry used a fresh path. No Linux CI behavior changed. All pinned
bytes and a fresh official checksum pass. Release/git/53-source replay passes;
the four registry checks requiring only the CI token remain explicitly CI-only
and fail closed, with no owner-secret or scope change.
[Source-bound preparation](../../os/manifest/ci/14/14zq-preflight/preparation.json).

The final manifest-order regression passed1/9.487s. Pinned local gitleaks8.21.2
reports0 findings in full history and the curated pending files; ignore/rules
and the privacy workflow are unchanged.

**Current bundle / For package15:**
`025622f56d61f669912ce9d6320e7171e2007194420c79ce54dc6b89a0570486`.
The reviewed payload is regenerated and INSTALL's current copy/check pin uses
this value. Earlier REPORT sections and evidence retain their historical pins.
Package15 takes this fingerprint after qualification; its worktree was not
touched. INSTALL/EMERGENCY/release gates retain NOT RELEASED and all physical
followability, keyboard, firmware and forgotten-stick gates.

**JUDGMENT-CALL:** exclude the hold only. Excluding the two shutdown finalizers
would hide actual deployment work, so those exact commands still block idle.
No waiting, masking or process-name wildcard was added; any future expansion
requires source evidence and refusal regressions.

**Budget / pending:** complete130/130 history:1412 +238 pre-push bound =1650/1700.
Only package14 changes: cap1700, probe25, owner-tools14; reserve0/closing0 stay.
Package13 is byte-for-byte unchanged. The read-only$10/prevent=true budget guard
deducts net charged spend. Pinned local gitleaks0 precedes the single FF push;
fresh exact-head privacy/all3 actual steps, complete ledger and billing precede
probe24. Only accepted probe24 permits qualification13 on the same head. Any
CI stop is reported with diagnostics, without rerun. Restore closing12/reserve150
and mark PR #13 ready only after acceptance, then tell the owner the round is
over so the budget can be reset0. Never merge.

**Not verified / open questions:** actual VM post-staging hold classification,
the complete AresOS/layout/recovery route on this head, and the physical laptop
gates. No image rebuild, release or publication. No real laptop touched.

**14zp STOP:** probe23 passed. Qualification12 proved short-hold physical typing,
the owner-length dummy and the377-character CI login, then STOPped after staging
the exact AresOS release: the refreshed-title idle guard reported an active
deployment client. No rerun, product change or extra push. PR #13 stays draft;
acceptance is unmet. This STOP report is committed locally.

## 14zp actual runs — typing passes; post-staging title guard STOPs

Both runs used pushed head `c0ab14c3c442a6abea2d158311277ed30e4419b1`:

| Run | Result | Native suite | Package minutes |
|---|---|---|---:|
| [Probe23](https://github.com/Ares-Empire/AresOS/actions/runs/40823225012) | Accepted |511 /138.277s, zero skips |26 |
| [Qualification12](https://github.com/Ares-Empire/AresOS/actions/runs/40826092372) | STOP after staging, before refreshed title |511 /131.129s, zero skips |75 |

**Typing evidence:** all6 reached hidden values passed their pre-Enter count
proof and completed normally: four account/sudo passwords, the40-character
dummy and the377-character real CI token. Each window was complete with all
keys released, exact press/release counts, repeats0, SYN_DROPPED0, one attempt.
All12 blocked-reader guards passed, and24 current-cursor visible echo checks
passed. No Ctrl-U, retype, unverified Return, hidden-read timeout or pre-Enter
STOP occurred. VM clear/retype remains unexercised; its real owned-PTY and model
regressions remain local evidence.

| Hidden input | Sent / received events | Presses / releases | Counter seconds |
|---|---:|---:|---:|
| Initial account password |66 /66 |33 /33 |22.324 |
| Initial sudo password |66 /66 |33 /33 |22.768 |
| Corrected-stock account password |66 /66 |33 /33 |23.436 |
| Corrected-stock sudo password |66 /66 |33 /33 |26.067 |
| Fresh owner-length dummy (40 chars) |112 /112 |56 /56 |25.867 |
| Real CI token (377 chars) |1110 /1110 |555 /555 |91.364 |

These complete-window totals include the single verified Return.

The fresh dummy returned the existing registry-refusal STOP with zero mutation
calls. Its112 events differ from Q11's110 because each fresh random value has
its own modifier count. Q11's40-character110/110 owner-path proof remains
in the preparation section. The real CI token used16-character chunks with1s pauses and1s
before the pre-Enter proof; **registry login passed**, followed by owner
signature verification. Timing is recorded as30ms holds /minimum120ms gaps;
guest autorepeat stayed250/33ms. No credential values, ordered keys or event
codes were recorded. [Counts, guards and completion diagnostics](../../os/manifest/ci/14/14zp-qualification-stop/diagnostics.json).

**Exact STOP / PLAN-GAP:** `/var/lib/ares/at switch` physically reached the owner
tool. Its checked switch script returned0 (`Deploying...done (53 seconds)`).
The subsequent rpm-ostree/bootc observations agree on the exact pinned AresOS
release staged, saved stock serial1 still booted and pinned, the older stock
serial0 retained, transaction null and rollbackQueued false. Source/trace
analysis places the refusal in `Tools.title()`'s idle gate, after the staging
checks: `rpm-ostree/bootc/ostree client active`. The command did **one intended
switch mutation before this postcondition refusal**; it is not a zero-mutation
preflight refusal and is not claimed passed.

The detected process's PID/executable/argv/cgroup are not retained by this
refusal record. Its identity, whether it was still doing work, and whether a
bounded settle would be appropriate are **unproved**. No process exclusion,
sleep/retry, owner-tool edit or audit relaxation was added. A fresh post-switch
title was not saved, and AresOS boot, layout begin/proof/revert/finish, rollback,
keep-stock and final Windows checks were not reached. The harness exported the
private STOP diagnostics and observed a paused VM STOP; it did not reboot or
retry. [Staged-state summary](../../os/manifest/ci/14/14zp-qualification-stop/switch-state.json).

**Other verification:** both native511-test suites have zero skips and explicitly
pass the unchanged30-second serial timing test. Both native logs and the VM
failure-step log scan with pinned gitleaks8.21.2:0 findings. The probe proves
the live zero-event counter checkpoint, released-key state, Unicode VCSU getter,
restored VT, loop-image20 checks /zero helper mutations and28 verified tmpfs
transfers. Qualification retains180 SHA/syntax-verified transfers,13 owner
records (11 passed; expected dummy refusal plus switch STOP),6 successful hidden
completions, prepare/rerun, network checkpoint, record export, private login and
signature verification. Its independent raw replay passes9 protected captures,
10 zero-write/unmap samples,9 BootNext replays and8 NVRAM/all-variable comparisons.
No protected-disk write, firmware widening or frozen release change is accepted.

The fresh qualification local ISO replay passed on attempt1. Release/git and
53-source replay and strict805-command checks were refreshed before dispatch.
A redundant invocation through Windows text-mode pipes produced a CRLF Bash
heredoc parse error; the unchanged checker rerun under existing WSL passed all
805 commands/wrappers and799 embedded Python blocks. No CI behaviour or test
bound changed for that local invocation issue.

Final report/evidence checks: the4 owner equality/manifest tests passed in
153.061s, `git diff --check` passed, and the pinned full-history and pending-file
gitleaks scans report0. The final local commit changes only this REPORT, the
ledger and sanitized evidence; CI/tests/owner payload/runtime/guides/workflows
and privacy policy remain exactly the tested head.

**Artifact privacy:** probe509 =507 reviewed public-ISO listing matches +2 exact
whole-line kernel X.509 messages; qualification517 =507 +10 exact messages.
There are zero unclassified findings, no new ignore/rule/workflow entries, and
no raw console, ISO listing, credential file or screenshot committed. Each
accepted kernel source line is recorded below (SHA256 before path):

| Source-line SHA256 | Private artifact path:line | Certificate label |
|---|---|---|
| `6c83c3d69de4a558645c4881fefb1fed81d6032c842739701abd76a21d7ea891` | Probe23: `evidence/two-disk/live-ui-probe-boot-console.txt:491` | Fedora kernel signing key |
| `94b4bc7bb3ca061d67d806bbf61102d05be71d7997cfd4eda3222b95dd134d22` | Probe23: `evidence/two-disk/live-ui-probe-boot-console.txt:524` | Fedora kernel signing key |
| `c1b20ec3a9b4af46b0eb3136997d2e8cc6efa54bb486b72a2674865d95fe858a` | Qualification12: `evidence/two-disk/corrected-stock-boot-console.txt:498` | Build time autogenerated kernel key |
| `05626d7cf69f61eb52ed486942886265b778f81f24ee482fad82f44e1bccbbd7` | Qualification12: `evidence/two-disk/corrected-stock-boot-console.txt:509` | Build time autogenerated kernel key |
| `203244910ded9a6fd5f44aebdb7c0f5852ed3a10dcc8292d8abc9c9e111a5b67` | Qualification12: `evidence/two-disk/offline-first-stock-boot-console.txt:503` | Build time autogenerated kernel key |
| `7babf3b28b2bb8d4454b9f09a88a4f4594b911c9d21faca3d115652c48f67cd4` | Qualification12: `evidence/two-disk/offline-first-stock-boot-console.txt:520` | Build time autogenerated kernel key |
| `e5702c0c13e38d43c3f333bb7d8fb17e2b7517e14ec9269e34442ca06dcd5117` | Qualification12: `evidence/two-disk/protected-second-install-boot-console.txt:492` | Fedora kernel signing key |
| `e27b4b05c779c93562cca544400721c6f17b0a05c35e15104fa604a0b3622b24` | Qualification12: `evidence/two-disk/protected-second-install-boot-console.txt:524` | Fedora kernel signing key |
| `e1ae852f74d9d6bb3581c330ec39d5249086fb24524a5ef08d1583fccc4cb0af` | Qualification12: `evidence/two-disk/stock-initialization-0-boot-console.txt:502` | Build time autogenerated kernel key |
| `0ab1161b753161c7873634f24a47597f5cc4072d12e2149d7d3b4048254af6f0` | Qualification12: `evidence/two-disk/stock-initialization-0-boot-console.txt:519` | Build time autogenerated kernel key |
| `c20dd4a65bf16bfd31339a87b2a4308b9858978652d76083d1be6682524309f7` | Qualification12: `evidence/two-disk/tools-stock-boot-console.txt:498` | Build time autogenerated kernel key |
| `35259b28a129295f6ba8ad8cc45069f741c6abaea82a8f459e281f9080f0acb5` | Qualification12: `evidence/two-disk/tools-stock-boot-console.txt:511` | Build time autogenerated kernel key |

**Closing state:** complete130/130 history, **1412/1600** package minutes,
23 probes /12 owner qualifications dispatched cumulatively. This round used
one fast-forward push, one probe and one qualification; no reruns. Exact-head
push/PR privacy both executed all3 required steps successfully. The timestamped
read-only billing snapshot reports$6.414 net charged and597
available minutes under the$10/prevent=true budget; this is a snapshot, not a
final invoice. No further Actions work is authorized by this stopped round.
Reserve0/closing0 remain because the restore condition is unmet; no final
closing push or ready transition occurred. The owner can set the budget back
to$0 now that this run is over.
[Complete ledger and decision packet](../../os/manifest/ci/14/14zp-qualification-stop/closed-ledger.json).

**Not verified / open question:** identify the active client at the post-switch
title gate before authorizing a fix or a new run. The complete installed-AresOS,
layout/recovery route remains unqualified. INSTALL, EMERGENCY and the release
gate retain NOT RELEASED and their physical/For package15 gates. No real laptop,
image rebuild, release, publication, merge or force push. Owner payload remains
`683b1cff54d8a80406a70afd3f1173343a8a3fc95d301ef8cdbf05ab39010974`.

## 14zp REPORT — short holds and counter-verified hidden input

**Done:** package14's guest sends each physical chord with a30ms QMP hold and a
minimum120ms gap, recorded per boot and hidden value. Existing parent delays
can add time. No guest repeat, keymap, keyboard-mode or console setting is
changed. The owner bundle/fingerprint, frozen runtime/release, guides,
workflows, audit predicates and privacy rules are unchanged.

All23 hidden values use a continuous read-only evdev counter. Atomic numbered
checkpoints require a quiet window and all keys released. Before Return the
expected press/release totals must match exactly, repeats0 and SYN_DROPPED0;
the same expected foreground reader must still be waiting in read0 with ECHO
off. No hidden value, individual event code/value or ordered keys are exported.
The377-character CI token retains16-character chunks with1s pauses, plus1s
before its pre-Enter checks. The counter continues through the single Return.

One pre-Enter recovery is permitted: before and after Ctrl-U the unchanged
reader must be canonical with VKILL21, still waiting with no Return sent. The
Ctrl-U itself must have exactly2 presses +2 releases, no repeats/drops and all
keys released. Only that complete proof permits one retype. A drop, held key,
unproved clear, second bad value or final Return count mismatch STOPs. A
noncanonical reader cannot get the clear/retype. There is no post-Enter retry.
The complete window, failed attempt and clear counts remain in evidence;
accepted-attempt counts are also reported separately, so recovery cannot hide
a previous repeat. Existing60s/180s/840s completion and900s UART bounds stay.

Visible owner commands and public inputs now have an explicit current-cursor
echo check **before** Return. Q11 was caught by the later hidden-read readiness
check; this adds the earlier gate. Public prompt waits use the cursor instead
of old fullscreen text. Existing physical-text assertions remain. For the
umlaut proof the echo reader uses native32-bit Unicode VCSU cells, bounded by
stable VCSA geometry, rather than treating font slots as Unicode. The probe
must prove this getter and the live counter checkpoint before qualification;
its temporary VT selection restores the originally active VT. No firmware or
disk audit is widened.

**Q11 owner-path evidence:** the per-run40-character dummy traversed tty3, both
sudo relays and getpass, then returned the existing registry-refusal STOP with
zero mutation calls. All110 events arrived:55 presses,55 releases, repeats0,
SYN_DROPPED0, autorepeat250/33ms. This proves the owner-length hidden path,
not successful registry authentication. The integrator classifies Q11's
subsequent `/var/lib/ares/aatt` corruption as autorepeat from late100ms
releases. The same cause remains unproved for Q9/Q10. No real CI token was
typed in Q11. [Retained proof](../../os/manifest/ci/14/14zo-qualification-stop/owner-length-token-proof.json).

**Source verification:** the public Linux N_TTY reference implements canonical
VKILL line removal; a local owned PTY/getpass execution confirms Ctrl-U removes
the previous incomplete value before any Enter. The pinned sudo1.9.17p2
tgetpass source uses noecho (cbreak for pwfeedback), reads bytes and accepts CR
or LF. VCSU's native32-bit/no-header format and device creation are verified in
[the upstream reference](https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/v6.17/drivers/tty/vt/vc_screen.c).
Reference ABI sources are distinguished from the guest kernel fork; actual
guest capability is required in the probe. [Source hashes and Q11 binding](../../os/manifest/ci/14/14zp-preflight/input-reference-sources.json).

**Verified locally:** final whole suite511/806.326s, 502 distinct
passes, 9 previously approved host limitations, zero skips. The first
whole run511/815.037s found five older fixture setups that did not model the
new phases; their five regressions pass after setup/expected-chunk repairs,
with no refusal/completion assertion removed. The original serial-staging
assertions and30s timing bound are byte-structure equivalent to the brief head.
The lost-result case measured57.652880255s in the isolated run; final whole
run measured54.94096418999993s. Historical30.010278s and
31.896785s remain recorded under14zm. This is a local host-timing limitation;
all511 tests and that same30s bound remain mandatory natively, no skips or
environment switch. A native overrun is a real STOP.

The focused timing/counter/diagnostic/budget tests, actual all-stage walk,
real Bash/limited-line login, owned PTY clear, Unicode echo predicate, updated
fixture regressions and four no-repeat dispatch-controller tests were run.
The serial fixture explicitly models evdev and the non-parent proc-syscall
getter that local ptrace policy may deny; foreground identities, termios,
byte transport, ACKs and SHA framing run for real. No host keyboard is opened.
The stand-in walk covers all8 stages,23 hidden values,46 blocked-reader guards,
every existing cluttered-screen resync and all public/hidden inputs. Strict
checks compile 805 guest commands and the same number of
wrappers, 799 embedded Python blocks, all shell/Python
sources and the native workflow body; parse stderr including warnings refuses.
Full ISO replay passed on attempt1 against all9,068,650,496 pinned bytes and a
fresh official checksum, using a new local checkpoint and no overlapping ISO
reader. Release/git/53-source replay passes. The four credential-only registry
checks remain explicitly CI-only and fail closed, with no scope/secret change.
[Source-bound preparation](../../os/manifest/ci/14/14zp-preflight/preparation.json).

**Budget / pending:** complete126/126 history:1306 consumed +238 pre-push bound
=1544/1600. Package14 only is cap1600, probe24, owner-tools13, reserve0/closing0;
package13 is unchanged. The read-only$10/prevent=true guard deducts charged net
Actions spend. Pinned local full-history gitleaks0 is required before the
single fast-forward push. Fresh exact-head privacy (all3 actual steps), complete
ledger, billing and budget precede probe23. Only accepted probe23 permits
qualification12 on the same head. Any CI stop ends the round with counts and
diagnostics, no rerun. Restore reserve150/closing12 and mark PR #13 ready only
after acceptance, then say the run is over so the owner can reset the budget0.

**Not verified:** actual guest holds/checkpoints/Unicode getter and a complete
VM route on this head; accepted pre-Enter recovery in the VM if it is needed.
The physical install stays NOT RELEASED and all laptop gates / For package15
items remain. No physical laptop, image rebuild, release or publication.

**14zo STOP:** probe22 passed; qualification11 stopped before the real token's
hidden prompt. The owner-length dummy passed with all110 events accounted for.
The real CI token was never typed. No rerun or additional push. PR #13 remains
draft / NOT RELEASED; acceptance is unmet.

## 14zo actual runs — owner-length proof passes; next public command is corrupted

Both runs used pushed head `68df196fc9fbfa8a1f441045baaa57c540ee9e2c`:

| Run | Result | Native suite | Charged package minutes |
|---|---|---|---:|
| [Probe22](https://github.com/Ares-Empire/AresOS/actions/runs/40802757524) | Accepted |495 /100.279s, zero skips |25 |
| [Qualification11](https://github.com/Ares-Empire/AresOS/actions/runs/40805607265) | STOP before real-token readiness |495 /101.118s, zero skips |67 |

**Owner-length result:** a fresh in-memory40-character dummy reached the existing
registry-refusal STOP within the180s bound. Its owner record has zero mutation
calls. The guest received55 presses +55 releases, matching110 sent events across
41 chords (including the single Return); repeats0 and SYN_DROPPED0. Autorepeat
was250ms delay /33ms period. The11.128s counter window was complete; no codes,
values, individual keys or dummy value were recorded. The expected STOP was:
`Private release read failed; check read:packages permission/expiry and network; no credential was written`.
The resulting hidden completion and idle-shell proof passed.
[Dummy proof and counts](../../os/manifest/ci/14/14zo-qualification-stop/owner-length-token-proof.json).

**Actual stop:** the next intended command was `/var/lib/ares/at login`. The
retained timeout screen reports `/var/lib/ares/aatt: command not found`, then the
public username was also treated as a shell command. The readiness observer
found an interactive bash through the two sudo relay processes, no expected
reader, and no token prompt at the cursor. The cursor was an idle shell prompt.
The harness correctly refused with `No verified hidden prompt` before calling
the secret typer. There is no real-token counter window, no real-token180s
completion wait, and no real-token typing or retry. The chunked long-token path
is therefore **not VM-verified**. The malformed public path is observed;
dropped/duplicated HID events or stale public-prompt matching as its cause are
**unproved**. No source change or new dispatch followed this stop.
[Readiness](../../os/manifest/ci/14/14zo-qualification-stop/real-token-readiness.json),
[public predicates](../../os/manifest/ci/14/14zo-qualification-stop/public-command-predicates.json).

**Diagnostics:** the dummy's completion-start14zn snapshot was exported. Python
was3.14.8 and sudo1.9.17p2; tty3 was active in K_UNICODE with LEDs0. Remaining
tty3/pts1 queues were0; the finished owner's pts2 and processes were already gone
(explicit FileNotFoundError records, not lost evidence). Three live relay/shell
wchan values were `poll_schedule_timeout.constprop.0`, accepted by the corrected
symbol-only validator; no arguments were exported. The real-token readiness
refusal retained its redacted foreground chain and raw VCSA in the private
artifact. All3 timeout VCSA screens were decoded **only in memory**, scanned
with pinned gitleaks:0 findings, no decoded text saved. No token-completion
timeout occurred, so no timeout snapshot for an untyped real token is claimed.
[Diagnostics](../../os/manifest/ci/14/14zo-qualification-stop/diagnostics.json).

**Other evidence:** the probe's actual keyboard counter/getter window passed on
`/dev/input/event4` with all counts0 and autorepeat250/33ms;25 staged transfers
verified their syntax/SHA. Its native partitioned-loop test passed20 checks with
zero helper mutations. Qualification verified115 staged transfers,9 passed
owner records, the dummy's expected zero-mutation STOP and5 hidden completions.
The independent raw audits passed9 protected captures,10 zero-write/unmap
samples,9 BootNext replays,8 NVRAM-rule replays and8 full-variable delta
recomputations. The stopped guest was paused. Owner signature verification, switch,
AresOS boot, layout failure/revert/success, rollback, keep-stock and final
Windows checks were not reached. No image, frozen runtime, payload/fingerprint,
guide, privacy-rule or owner-script change; no physical laptop was touched.

**Privacy:** pinned local full-history and pending scans were0 before the one
fast-forward push. Both exact-head privacy runs passed all3 actual steps.
Native and failure-log scans were0. Probe artifact509 findings =507 public ISO
listing +2 exact kernel X.509 lines; qualification517 =507 ISO +10 such lines.
No other finding was accepted; no ignore/rule/workflow was changed. Every kernel
line is recorded below by its SHA-256 before its private-artifact path/line; raw
boot consoles and certificate fingerprint values are not committed.

| SHA-256 of whole matched line | Captured boot-console path and line | Public certificate label |
|---|---|---|
| `ccb4c6e0c9c41ed3b2f31b1f82b7e4e93211b5d084dd0447740db94c2c49b613` | Probe22: `evidence/two-disk/live-ui-probe-boot-console.txt:497` | Fedora kernel signing key |
| `f8be90af292aa0aa2431dace20561f9c280d03ad369e56d82fdfa4d538e35cd5` | Probe22: `evidence/two-disk/live-ui-probe-boot-console.txt:530` | Fedora kernel signing key |
| `6152333bb8acebdc70b236e53d06fd8344ecc1b4f7402ab613efe29e1708647b` | Qualification11: `evidence/two-disk/corrected-stock-boot-console.txt:499` | Build time autogenerated kernel key |
| `a8c7563945f7a50ae329b9f57a34013db4b2e3eada32144c76d19676d277645b` | Qualification11: `evidence/two-disk/corrected-stock-boot-console.txt:509` | Build time autogenerated kernel key |
| `d1d083d9611dbea5fb4abd35b7cda4858b40b66292d8b3ab340cba28d34aad72` | Qualification11: `evidence/two-disk/offline-first-stock-boot-console.txt:499` | Build time autogenerated kernel key |
| `7a912980fbbeeb4ba7a67115ae425ddd39dfdcaf947753348df28e8504294ddc` | Qualification11: `evidence/two-disk/offline-first-stock-boot-console.txt:519` | Build time autogenerated kernel key |
| `e20d132575a37557519863dcd5649674aadf9421b8fddcf8fbbac5c3b52fb4eb` | Qualification11: `evidence/two-disk/protected-second-install-boot-console.txt:491` | Fedora kernel signing key |
| `167e2dfdeef9ac76b922afe9067e5acf668dacdbaa2f2d17e674dcff2240352b` | Qualification11: `evidence/two-disk/protected-second-install-boot-console.txt:525` | Fedora kernel signing key |
| `6fa695a1740198af55792038bf738455a64dfddc02d0f1da4282edd7df931dd6` | Qualification11: `evidence/two-disk/stock-initialization-0-boot-console.txt:499` | Build time autogenerated kernel key |
| `f1fa2e90cc3c256e17904d8e14a2331d2c13403113890b7ced13613868ea6c54` | Qualification11: `evidence/two-disk/stock-initialization-0-boot-console.txt:521` | Build time autogenerated kernel key |
| `6b867424deeb54815e325c321b73cc3dd69650a43d9e77de9ab377a958cb10cd` | Qualification11: `evidence/two-disk/tools-stock-boot-console.txt:498` | Build time autogenerated kernel key |
| `ebdea4a6ab6cd67dacfb5778fd3175752551deb2e42ded78996310273bab097f` | Qualification11: `evidence/two-disk/tools-stock-boot-console.txt:513` | Build time autogenerated kernel key |

**Budget / closure:** complete126/126 history.1208 prior +6 push privacy +25 probe
+67 qualification = **1306/1500**. The closing read-only$10/prevent=true budget
snapshot reports$6.228 net Actions spend and628 available minutes. There was one
push, one probe, one qualification, no workflow reruns. Closing0/reserve0 remain
because acceptance is unmet; restoration to12/150 and PR readiness were not
performed. The STOP report/evidence/accounting are committed **locally only**;
there is no second push. The run is over: the owner can set the Actions budget
back to$0. Nothing was merged or made public.
[Complete STOP packet](../../os/manifest/ci/14/14zo-qualification-stop/summary.json).

**Open question / PLAN-GAP:** the owner-length hidden input is now demonstrated,
but the next public command was corrupted. Its cause and the long CI token path
remain unverified. Further diagnosis/fixes or a new VM dispatch require a new
integrator/owner decision under the stop rule. Existing physical release gates
and the For package15 work remain unchanged.

## 14zo REPORT — owner-length token proof and guest key-event counts

**Done:** during each token typing the harness starts a read-only evdev observer
over the acknowledged serial transport. It selects the exact retained QEMU USB
keyboard identity, checks no held keys, reads autorepeat settings and exports
only press/release/repeat/SYN_DROPPED totals. Raw events, codes, values and key
order are never saved. SYN_DROPPED invalidates completeness; any count mismatch
stops continuation. Root-only tmpfs counter files contain aggregate data and are
removed after collection. The probe checks actual device/getter/fork capability
with a zero-input window before qualification.

The first private login uses a fresh in-memory 40-character classic-PAT-shaped
dummy and must return the existing registry-refusal STOP within180s. A stall or
unexpected refusal exports counts/14zn diagnostics and blocks the real token.
Only after that proof does the real CI token use16-character chunks with1s
between chunks and1s before its single Return. No secret is retyped or gets a
second Return. Counters are finalized even if typing fails. Kernel wchan symbol
suffixes are accepted, while whitespace/argument text remains refused. Other
deadlines, owner payload/fingerprint, guides, runtime, workflows and privacy
rules are unchanged. No image dispatch or publication.

**Evidence / cause:** qualification10 established sent377 characters/1108 QMP
events, empty terminal queues and a waiting Python read, not actual HID delivery.
The integrator's17/377-character nested-sudo WSL reproductions succeed. Dropped
HID events remain unproved. The collector follows the public Linux input-event
ABI and QEMU8.2.2 base references; these are distinguished from the pinned Ubuntu
package patches. [Reference/retained-identity record](../../os/manifest/ci/14/14zo-preflight/input-reference-sources.json).

**Verified locally:** final whole suite495/638.961s, 486 distinct
passes, 9 previously approved host limitations, zero skips. The mandatory
30s test and every serial-staging assertion are unchanged. Earlier full local
run measured41.170695s (isolated affected run41.368544s); final run measured
37.36985975499999s. These are the explicit
14zm memory-pressure timing limitation, never native exceptions. The walk's
expected hidden-read count was corrected from22 to23 for the added dummy read.
Twenty-six focused counter/diagnostic/budget regressions and four controller
tests pass, including SYN_DROPPED, malformed events, aggregate-only output,
read-only ioctls, exact chunk pauses/one Return and dummy-stop-before-real wiring.
The current walk covers all8 stages,23 hidden pairs,3 public handoffs and both
token-start snapshots; no uncovered wait/input remains. Strict checks cover
570 guest commands and570 wrappers,545 embedded Python blocks,12 shell files,
49 Python files and the native workflow body, with no syntax warnings accepted.
Full ISO replay passed on attempt1 against all9,068,650,496 pinned bytes and a
fresh official checksum. Release/git/53-source replay passes; four credential-
only registry checks remain explicitly CI-only/fail-closed.
[Source-bound preparation](../../os/manifest/ci/14/14zo-preflight/preparation.json).

**Budget / pending:** complete122/122 history:1208 consumed +238 pre-push bound
/1500. Package14 only is probe23/owner-tools12; package13 is unchanged, reserve0,
closing0. The read-only$10/prevent=true guard deducts net charged Actions spend.
One fast-forward push follows pinned local gitleaks; fresh exact-head privacy,
ledger/billing/budget then precede probe22. Only accepted probe22 permits
qualification11 on the same head. Any CI stop ends the round without a rerun.
PR #13 remains draft; acceptance is unmet. Restore reserve150/closing12 only on
acceptance and tell the owner the round is over so the paid budget can return0.

**Not verified / open question:** actual received HID counts, owner-length proof
and full VM owner route on this head. No conclusion about lost keys yet. The
physical release/laptop gates remain outstanding; no real laptop was touched.

**14zn STOP: probe21 accepted; qualification10 stopped after the180s private-token
completion wait.** The secret was sent once, never retyped. No rerun or additional
dispatch/push. PR #13 stays draft / NOT RELEASED; acceptance is unmet.

## 14zn actual runs — token diagnostics exported, input delivery still unproved

**Done:** the single fast-forward push carried `d523fb257afd72d7438340c35f6bf463341ea02b`.
Exact-head privacy40784619811/40784610639 passed all three checks, including
personal terms actually executed. The fresh120/120 pre-probe guard authorized
1129+232/1500; the121/121 pre-qualification guard authorized1152+160/1500.
Both required$10/prevent=true and deducted reported net Actions charges. No
owner tool, frozen image/release/runtime, guide, workflow or privacy-rule change.

**Verified:** [probe21](https://github.com/Ares-Empire/AresOS/actions/runs/40785271949)
passed native484/80.333s, zero skips, including the unchanged30s timing case.
It passed20 native loop checks/zero helper mutations and23 verified guest tmpfs
transfers. Independent3 protected captures/4 zero-write-unmap/3 BootNext/
2 NVRAM and full-variable replays pass. Artifact12860151875:354 members,
4,743,904 bytes, SHA-256`1936f53639bfcc1eeca79ab039a2790676423d205d268f46f23cbdb5d616d288`.
The scan has509 findings:507 reviewed public ISO names and2 exact whole kernel
certificate messages. Native log0; unknown artifact findings0.

Before qualification, actual release/git/53-source replay, strict550 guest
commands/wrappers and the full ISO inspector replay passed again. The ISO replay
passed attempt1 against all9,068,650,496 bytes, the pin and a fresh official
checksum; no Windows retry was needed. Four registry steps remained CI-only and
passed live. [Qualification10](https://github.com/Ares-Empire/AresOS/actions/runs/40788594413)
was a fresh workflow_dispatch, attempt1, on the same head in protected-second order.

**STOP:** qualification10 passed native484/83.530s, zero skips, and the unchanged
timing case. Its20 native loop checks/zero mutations, immutable release/signature/
layer gates, exact ISO, offline install/first boot/hardware-setup reboot,
unattended/detached Windows round trips, tools install, prepare, zero-mutation
prepare rerun, first-network state equality, record export and public stock typing
passed. Nine owner command records passed; account login/password sudo on both
stock boots produced4 successful hidden transitions. All109 staged transfers,
including both new diagnostics snapshots and the completion observer, verify
guest SHA and syntax. The VM paused/exported/closed on STOP.

Readiness proved Python7999 on inner pts2, ECHO off, and the exact token prompt.
The checksum of the actual staged observer equals a reconstruction with180s:
`8132f9d56df699adce8a789805bdfc1dc73568454bf88e1b74fa1c8f9cf9880f`.
The UART execution deadline stayed900s. At expiry, the same expected reader
remained foreground: `reader_left=false`, `shell_idle=false`, no owner PASS/STOP
result. Retained VCSA50x160, cursor26,49 still ends at the token prompt; its
decoded-text scan is0. Decoding was in memory only. No token value, queued bytes,
ordered key sequence or syscall arguments were recorded.

Both serial-side snapshots (completion-start and completion-timeout) agree:

| Terminal | TIOCINQ / TIOCOUTQ | ICANON | ECHO | ICRNL | IXON | IEXTEN | ISIG |
|---|---|---|---|---|---|---|---|
| tty3 | 0 / 0 | false | false | false | false | false | false |
| pts1 | 0 / 0 | false | false | false | false | false | false |
| reader pts2 | 0 / 0 | true | false | true | true | true | true |

Active VT istty3; tty3 KDGKBMODE=3 (Unicode), KDGETLED=0, KDGKBLED=0. Runtime
versions confirm Python3.14.8 and sudo1.9.17p2. The sent value had377 characters;
the harness recorded378 accepted QMP send-key chords,1108 requested press/release
events, a final `ret`, and mapping classes`shift`/`layout_differs_from_us`.
These are counts/flags, not evidence that all events reached the guest reader.

| Process | PID | State | Syscall number (x86-64 ABI) | wchan |
|---|---|---|---|---|
| outer sudo | 4417 | S | 271 (ppoll) | unavailable: validation rejected text |
| outer monitor | 5355 | S | 271 (ppoll) | unavailable: validation rejected text |
| root Bash | 5356 | S | 61 (wait4) | do_wait |
| inner sudo | 7993 | S | 271 (ppoll) | unavailable: validation rejected text |
| inner monitor | 7998 | S | 271 (ppoll) | unavailable: validation rejected text |
| expected owner Python | 7999 | S | 0 (read) | wait_woken |

The syscall names follow the public
[Linux x86-64 ABI table](https://github.com/torvalds/linux/blob/v6.17/arch/x86/entry/syscalls/syscall_64.tbl).
The two samples show the expected VT, inner canonical mode and CR translation;
they do not reconstruct every instant during typing. Under the canonical
[Linux N_TTY input-count path](https://github.com/torvalds/linux/blob/v6.17/drivers/tty/n_tty.c#L2329),
an incomplete line can still produce zero TIOCINQ. Consequently these samples
cannot distinguish lost keys/Return from an incomplete buffered line. No queued
contents were read, and **the cause remains unproved**. No new experiment, fix,
secret retype or workflow rerun was attempted after the CI stop.

**PLAN-GAP / diagnostics defect:** my collector's wchan symbol validator rejected
the returned text for all4 sudo processes. Their exact strings were not retained,
so their names cannot be recovered from this artifact. Their states and syscall
numbers are present; Bash/reader wchan values are present. The model fixtures did
not cover those returned strings. The collector is not claimed complete or fixed;
it is left unchanged after this STOP. The owner tool is unchanged throughout.

The pinned image getpass byte comparison and sudo source comparison remain in
the preparation section below. Additional source verification found sudo1.9.15
and1.9.15p5 `exec_pty.c`/`exec_iolog.c` byte-identical, so that comparison covers
the integrator's stated baseline. Source changes alone do not establish this
failure's cause. Reference Linux ABI sources are distinguished from the guest's
kernel fork in the evidence metadata.

Qualification artifact12863022691:793 members,9,631,137 bytes,
SHA-256`049aadcf9144ba0cf31a8ce6ead1a9515b6db08fce4e64613ffbbc005c14497f`.
Scan517=507 public ISO names +10 exact whole kernel certificate lines; native
log0, failure log0 and all4 decoded VCSA screens0. Independent9 protected/
10 zero-write-unmap/9 BootNext/8 NVRAM/full-variable replays pass. No unknown
finding was accepted; no ignore/rule/workflow change. Each accepted kernel line:

| Run | Boot console and line | Public certificate label | Whole-line SHA-256 |
|---|---|---|---|
| probe21 | live-ui-probe-boot-console.txt:495 | Fedora kernel signing key | `004f47551d0828686404bf4b5bfbd34575295c2926e307f32d80eacf70efcd23` |
| probe21 | live-ui-probe-boot-console.txt:528 | Fedora kernel signing key | `c4b44134b72aa8c1f8e6aea6abdda7f523ec960a4947f17132ac6828d0191fd4` |
| qualification10 | corrected-stock-boot-console.txt:503 | Build time autogenerated kernel key | `524e3f79fe59dd10112e474de39d3baa049aa2622340f8e896dd75784a4e65f0` |
| qualification10 | corrected-stock-boot-console.txt:514 | Build time autogenerated kernel key | `9f45e110acef3179a371fbf0835d8907dea44651525cd64b5e14ffeb19ca98cc` |
| qualification10 | offline-first-stock-boot-console.txt:503 | Build time autogenerated kernel key | `bf6f09ffd9260524cfc8e8c780ad394aae140d820c9e57600e22ead9236614e3` |
| qualification10 | offline-first-stock-boot-console.txt:514 | Build time autogenerated kernel key | `ba4c39aaa05a15199737b1d6fe3ca457189cc21759a06e25b313b7709e9af80d` |
| qualification10 | protected-second-install-boot-console.txt:496 | Fedora kernel signing key | `eb741a2246454824cafc66dd90ff5e82d4a9f0e8660f1ef2b339c5d32db56a39` |
| qualification10 | protected-second-install-boot-console.txt:529 | Fedora kernel signing key | `57b31b754ff1cb0fe2a686a5ff6ad166ea166c84a46480552c3f5fba11f43c25` |
| qualification10 | stock-initialization-0-boot-console.txt:503 | Build time autogenerated kernel key | `5e5726b96d58cf45995cb4e44eee173e32e11ba39eaa091620734da6b0e3a612` |
| qualification10 | stock-initialization-0-boot-console.txt:513 | Build time autogenerated kernel key | `1842084a4ee1030b1d09b233ed9c053072ee93b43ed9dd6527bdb40a514f5f4f` |
| qualification10 | tools-stock-boot-console.txt:503 | Build time autogenerated kernel key | `90fcce03f72716e68a64710518dbe5c80038f7034f2fd4dee3d1eb5ff16f04d2` |
| qualification10 | tools-stock-boot-console.txt:513 | Build time autogenerated kernel key | `718abbb03c5ac2b35c6c3872c2813c94062e2d2be26a49bb30956b451e2abc6c` |

Raw consoles, VCSA, redacted foreground chains, both counts/flags snapshots,
transport receipts and private diagnostics remain in the private artifact and
ignored `.work/14/run-40788594413/`. The failed login never returned an owner
result record; its harness readiness/completion and new serial diagnostics were
exported. Committed metadata contains no raw console or secret value.
[STOP packet](../../os/manifest/ci/14/14zn-qualification-stop/summary.json).

**Budget:** fresh complete122/122 history; probe21/22, owner-tools10/11.

| Package14 ledger item | Minutes |
|---|---:|
| Before this follow-up | 1124 |
| Single push's privacy | 5 |
| Probe21 | 23 |
| Qualification10 | 56 |
| Consumed / cap | 1208 /1500 |

The closing read-only API snapshot still requires$10/prevent=true and reports
net charged Actions spend$5.304 (the API's value at capture, not an assertion
that all completed-run charges have posted). No budget setting was changed.
Acceptance is unmet, so reserve0/closing0 were not restored and PR #13 remains
draft. The STOP report/ledger are committed locally with pinned clean gitleaks;
the one pre-dispatch push is the only push this round. No merge/publication.

**Not verified / open questions:** input/Return delivery and the missing sudo
wchan names; owner verify/switch, AresOS boot, layout failure/revert/success/back,
rollback, keep-stock and final Windows checks were not reached. Physical install
and laptop followability remain NOT RELEASED. INSTALL, EMERGENCY, release gate
and the existing For package15 list are unchanged. The run is over; no Actions
remain from this round, and the owner can set the budget back to$0.

## 14zn REPORT — token read diagnostics and 180-second completion wait

**Done:** the harness collects read-only TIOCINQ/TIOCOUTQ counts and ICANON,
ECHO, ICRNL, IXON, IEXTEN and ISIG for tty3, every relay pts and the reader pts
(also the selected physical tty4). It exports per-process state, wchan and only
the syscall number; active VT, keyboard mode/LED getters and Python/sudo versions.
It never reads queued input, exports syscall arguments or stores a secret/key
sequence. Actual successfully sent QMP chord and press/release-event counts,
length, final-Return flag and non-default mapping classes accompany the snapshot.
Token completion gets an immediate serial snapshot and a **180s** observer wait;
any hidden completion refusal gets a final snapshot and raw VCSA before STOP.
Post-completion physical-idle refusals also collect diagnostics. Other60s/840s
waits and the900s UART deadline remain unchanged. There is no secret retype.
The owner payload/fingerprint, guides, runtime, workflows and privacy rules are
unchanged. Fixture adapters accept counters and distinguish readiness from the
new post-send diagnostics; no assertion, bound, skip or marker was weakened.

**Guest source check:** read-only extraction from the pinned image's layer
ancestry gives Python3.14.8, with getpass.py byte-identical to
[CPython3.14.8](https://raw.githubusercontent.com/python/cpython/v3.14.8/Lib/getpass.py).
Compared with [3.12](https://raw.githubusercontent.com/python/cpython/v3.12.0/Lib/getpass.py),
3.14 adds optional echo_char; this tool uses its default None, so it still clears
ECHO, preserves ICANON, flushes before printing the prompt, reads a line and
restores settings before newline/return. The3.13 getuser exception change does
not affect this read. Pinned sudo is1.9.17-10.p2.fc44 with use_pty enabled and no
override. Matching [1.9.17p2 relay source](https://github.com/sudo-project/sudo/blob/d1b48c651cec19fe37d1f0d3299d2283fb0f88e4/src/exec_pty.c)
versus [1.9.15p5](https://github.com/sudo-project/sudo/blob/SUDO_1_9_15p5/src/exec_pty.c)
has initialization, terminal-revocation/SIGHUP and fd-to-foreground-group matching
changes; ordinary read/write buffer forwarding is retained and exec_iolog.c is
byte-identical. The [release notes](https://github.com/sudo-project/sudo/blob/d1b48c651cec19fe37d1f0d3299d2283fb0f88e4/NEWS)
also describe Linux serial-console and password echo-flush fixes. These are
source differences, **not proof** of Q9's cause. The integrator's successful
3.12/1.9.15 nested-sudo reproduction is accepted; the new VM observations must
locate the remaining VT/keyboard/version/token difference.

**Verified locally:** final whole suite484/627.893s, 475 distinct
passes, 9 observed previously approved host limitations, zero skips.
The unchanged30s case remains mandatory in native CI; historical30.010278s and
31.896785s are host limitations, not CI exceptions. This full local run measured
32.613702s against that same30s bound; the isolated two-case run passed. Five collector/deadline/
counter tests pass with modelled proc/ioctls, including missing processes and
ioctl refusal without exported exception text. The two real PTY login/limited-
serial/lost-result tests pass with diagnostics staged and SHA-verified. The
current all-stage walk covers22 hidden pairs,3 public handoffs, the token-start
snapshot and every later wait; strict Bash/Python checks pass. Full ISO replay
passed against all9,068,650,496 bytes and a fresh official checksum; actual
release/git/53-source replay and four no-repeat controller tests pass. Four
credential-only registry checks remain explicitly CI-only and fail closed.
[Source-bound preparation](../../os/manifest/ci/14/14zn-preflight/preparation.json).

**Budget / pending:** complete118/118 history:1124 consumed +238 planned /1500.
Package14 remains probe22/owner-tools11, reserve0/closing0. The$10/prevent=true
guard deducts net charged Actions spend. Pinned local gitleaks must be clean
before the single fast-forward push. Fresh exact-head privacy and a fresh guard
precede probe21; qualification10 requires its acceptance on the same head.
Any CI stop ends the round with diagnostics and no rerun. PR #13 remains draft
and acceptance is unmet; restore reserve150/closing12 only upon acceptance.

**Not verified:** native484/no skips, actual new diagnostics and full VM owner
route on this head. **PLAN-GAP / open question:** where the private token input
stops remains unproved. No owner tool, image or physical laptop change.

**14zm STOP: probe20 passed; qualification9 stopped at the private registry
login's hidden-read completion.** One push and one of each planned dispatch;
no rerun or further push. PR #13 remains draft / NOT RELEASED.

## 14zm actual runs — installed login fixed; token reader did not return

**Done:** pushed `d1d18a7982d87b7bcf1fff6394659742adc7f62e` fast-forward once.
Both exact-head privacy runs40762971649/40762962724 passed all three checks,
with personal terms actually executed. The local timing test and30-second bound
remain unchanged and mandatory natively; the historical30.010s/31.897s overruns
remain an explicit host limitation, not a CI exception. No skip/marker/env switch.

**Verified:** [probe20](https://github.com/Ares-Empire/AresOS/actions/runs/40763979290)
passed native479/93.283s, zero skips, including the exact timing case. Its20 native
loop checks/zero helper mutations,23 verified staged transfers, private manifest/
signature/layer checks, exact ISO pin and independent3 protected/4 zero-write/
3 BootNext/2 NVRAM/full-variable replays pass. Artifact12851640148 has354 members
and4,739,802 bytes. Privacy509=507 public ISO names +2 exact kernel certificate
lines; native.log has0 findings. No unknown finding was accepted.

Before qualification: fresh privacy, local release/git/53-source and strict
replays pass; local full ISO replay passed attempt2 after one WinError5 checkpoint
denial and the authorized10s wait. Linux CI inspector behavior is unchanged.
The complete117/117 guard authorized1049+160/1500 with$10/prevent=true and billed
net spend deducted. [Qualification9](https://github.com/Ares-Empire/AresOS/actions/runs/40768498320)
used the same head, protected-second order, attempt1.

**STOP / PLAN-GAP:** qualification9 passed native479/93.063s with zero skips and
the unchanged timing case,20 loop checks/zero mutations, pinned ISO/offline install,
hardware setup/pre-login reboot, unattended/detached Windows, real installed tty3
login and password sudo on two stock boots, tools install, prepare, zero-mutation
prepare rerun, first-network state equality, record export and public stock typing.
Nine owner command diagnostics passed. Four hidden completions (account login
and sudo on both boots) now pass without ECHO. All107 staged transfers verify SHA
and syntax, including the final completion observer's transport.

It stopped at `private-owner-login -> send_hidden`: readiness proved Python7609
on inner pts2 through the two sudo relays, ECHO off and the exact token prompt.
The harness sent the secret once via the physical path and did not retype it.
After the bounded840s completion wait, the same reader remained foreground;
`reader_left=false`, `shell_idle=false`, no owner result and no shell prompt.
The retained50x160 VCSA still ends at `Read-only token (hidden):` (cursor26,49),
with no PASS login or STOP line. Its decoded-text privacy scan is0; decoded text
is not saved. Input arrival and the underlying cause are **not proved**. No
transport, predicate, timeout or owner-script fix was attempted after the CI stop.

The harness exported readiness/completion chains, raw VCSA, transport receipts,
QMP and firmware/disk snapshots. There is no failed-login owner result/diagnostics
record in the artifact: that command did not return, and post-command export was
not reached. The nine earlier passed command records are retained. Signature
verification in the owner tool, switch, AresOS boot/layout tests, rollback,
keep-stock and final Windows checks were not reached. The VM STOP event is saved.
[Structured observation](../../os/manifest/ci/14/14zm-qualification-stop/stop-observation.json),
[scope/diagnostic inventory](../../os/manifest/ci/14/14zm-qualification-stop/summary.json).

Qualification artifact12855223578:787 members/9,625,718 bytes. Privacy517=507 ISO
names +10 exact whole-line kernel X.509 messages,0 unknown; native/failure-console
text scans are clean. Independent9 protected captures,10 zero write/unmap samples,
9 BootNext and8 NVRAM/full-variable replays pass. Public certificate findings,
each matched against its exact whole source line under the unchanged14v rule:

| Run | Captured boot console and line | Public certificate label |
| --- | --- | --- |
| probe20 | live-ui-probe-boot-console.txt:497 | Fedora kernel signing key |
| probe20 | live-ui-probe-boot-console.txt:530 | Fedora kernel signing key |
| qualification9 | corrected-stock-boot-console.txt:498 | Build time autogenerated kernel key |
| qualification9 | corrected-stock-boot-console.txt:513 | Build time autogenerated kernel key |
| qualification9 | offline-first-stock-boot-console.txt:499 | Build time autogenerated kernel key |
| qualification9 | offline-first-stock-boot-console.txt:520 | Build time autogenerated kernel key |
| qualification9 | protected-second-install-boot-console.txt:491 | Fedora kernel signing key |
| qualification9 | protected-second-install-boot-console.txt:524 | Fedora kernel signing key |
| qualification9 | stock-initialization-0-boot-console.txt:512 | Build time autogenerated kernel key |
| qualification9 | stock-initialization-0-boot-console.txt:523 | Build time autogenerated kernel key |
| qualification9 | tools-stock-boot-console.txt:498 | Build time autogenerated kernel key |
| qualification9 | tools-stock-boot-console.txt:518 | Build time autogenerated kernel key |

**Not verified / closing:** acceptance is unmet. Ledger1124/1500, complete118/118;
counts20/22 probes and9/11 qualifications. No second attempt. Reserve0/closing0
are not restored and PR #13 is not marked ready. The $10/prevent=true budget is
untouched by this agent; latest net charge$5.136 leaves810 reported minutes.
No image rebuild/release/publication, real laptop/disk/boot access, or Gradle run.
The STOP packet is local-only, with pinned8.21.2 full-history/pending privacy0 and
clean diff checks. The pushed head remains the sole qualification head. This
round is over; no further Actions run is planned.

## 14zm REPORT — unchanged timing test mandatory natively

**Done:** the local30-second timing overrun is documented alongside the existing
eight host limitations. Measured times remain **30.010278s and31.896785s**; the
isolated fixture including setup took32.385s. Neither the test, its30-second
bound, the suite, nor the native workflow changed. No skip, marker or environment
switch was added. The local control-flow walk is accepted under the explicit
[14zm decision](../../briefs/14zm-host-timing-limit.md); this is not VM acceptance.

**Verified:** current full local suite479/776.538s, 471 distinct passes,
8 observed approved host-limited cases, zero skips. The270-test host suite's
269 passes/one timing limitation and standalone stage flow are retained honestly.
All549 composed commands/wrappers,524 embedded Python,12 shells,47 Python files
and the native workflow body pass strict checks. Fresh complete ISO replay passed
attempt1 against all9,068,650,496 pinned bytes and a fresh official checksum;
read-only release/git/53-source replay and four controller tests pass. Four
registry operations stay CI-only and fail closed. No credential/scope change.
[Bound preparation](../../os/manifest/ci/14/14zm-preflight/preparation.json).

The scheduling guard still requires$10/prevent=true, deducting billed net spend
at the API price; package14 alone is1500 minutes/probe22/owner-tools11. The fresh
114/114 snapshot is1019 consumed +238 planned /1500. Reserve0/closing0 stay
unchanged. No owner-tool, image/runtime, guide, workflow, privacy-rule or audit
change. Pinned8.21.2 history/pending scans and diff check must be clean before
the single fast-forward push. Fresh exact-head privacy and budget gates precede
probe20; qualification9 requires its passing native479/zero-skip suite, artifact
privacy review and the same head. Any CI stop ends this round without rerun.

**Not verified:** exact-head privacy CI and native/VM qualification on this head.
Acceptance remains unmet; PR #13 stays draft / NOT RELEASED until evidence passes.

**14zl STOP before push:** the mandatory local host suite fails an unchanged
wall-clock assertion. No push, probe20 or qualification9; PR state unchanged.

## 14zl REPORT — $10 guard prepared; local login-fixture timing gate failed

**Done:** package14 alone now has cap1500, probe22 and owner-tools11. The guard
requires exactly $10/prevent=true and deducts all net Actions spend at the API
price. Refusal tests follow those limits; package13, reserve0 and closing0 are
unchanged. No owner-tool, image/runtime, guide, workflow, privacy-rule or audit
change. The refreshed walk binding is explicitly **stopped**, not VM authority.

**Verified:** budget tests11 pass; the host suite ran270/688.296s, with269 passes,
one failure and zero skips. Read-only release/git and53-source replay pass. Fresh
ISO replay passed attempt1: all9,068,650,496 bytes equal the pin and fresh official
checksum. Actual standalone stage flow and strict549 guest/wrapper scripts,
524 embedded Python,12 shells,47 Python and the workflow body pass. The complete
114/114 ledger is1019 consumed +238 planned /1500. API budget is$10/prevent=true,
price$0.006, net spend$4.476;920 available minus238 leaves682. No reservation was
spent. Pinned8.21.2 full-history/pending privacy and diff checks pass.

**STOP / PLAN-GAP:**
`test_exact_login_driver_sequence_stops_on_lost_result_chunk_without_retry`
expects the whole login fixture to finish below30s. It took30.010278s; isolated
profiling reproduces31.896785s (32.385s including fixture setup). The13,302-byte
readiness transfer took6.680s and21,012-byte completion transfer11.131s; the
injected lost result then produced the expected TimeoutError in2.169s. Assertions
after the elapsed-time assertion were not reached. The end-to-end timing gate
is red; no assertion/timeout was relaxed and no new transport change was made.
[Structured diagnostics and scope](../../os/manifest/ci/14/14zl-local-stop/summary.json),
[timing profile](../../os/manifest/ci/14/14zl-local-stop/timing-profile.json).

**Not verified:** the current full OS suite (blocked by its prerequisite), fresh
privacy CI, native checks and VM qualification. No CI stop occurred: nothing was
pushed or dispatched. Ledger stays1019; acceptance is unmet, so reserve0/closing0
are not restored and PR #13 is not marked ready. The owner's budget remains
untouched by this agent. No product judgment call; local STOP commit only.

**14zk LOCAL ONLY:** hidden completion fixed and walked locally. Qualification8's
STOP remains the latest VM result; acceptance is unmet. No push or dispatch.

## 14zk REPORT — completion follows the reader transition

**Done:** every physical hidden read now requires its reader to leave the
foreground, followed by the verified idle shell/prompt or exact owner PASS/STOP:
cursor result. Completion never consults ECHO. Reader readiness, process identity,
parent/session/group and sudo-relay checks, one secret send, serial staging/SHA,
redaction and bounded prompt resync remain strict.

**Verified:** read-only pinned-base RPM/unit/source proof confirms util-linux
2.41.5/systemd 259.9 and login's persistent PAM parent/new Bash session. Exact
private q8 console/chain replay and a real PTY login-like parent with idle Readline
ECHO-off pass; waiting getpass, wrong-reader and stale-result refusals pass.
Host parser waits no longer consume the test's guest clock.
The host walk passes 270 tests/499.358s: 22 read pairs, 119 cluttered waits,
three public handoffs. Login, verify, switch, AresOS boots, all layout steps,
rollback and keep-stock are covered; no uncovered physical Console wait.
The deliberately rejected login and public challenge never grant completion.

Whole suite: 479 tests/601.101s, 471 distinct passes, the same eight documented
native host limitations (2 failures/9 errors), zero skips. Strict checks pass:
549 guest/wrapper scripts, 524 embedded Python, 12 shells, 47 Python files and
the native workflow body. Commands, results and
helper/VM coverage limits: [local verification](../../os/manifest/ci/14/14zk-local/verification.json),
[parent sources](../../os/manifest/ci/14/14zk-local/parent-sources.json).

**Not verified:** this fix in a VM; no Actions run, push, merge or PR-state change.
Owner payload, guides/release gate, frozen runtime/release, workflows/privacy rules
and budget settings are unchanged. Ledger stays 1019/1200, probe 19/19 and
qualification 8/8; closing 0/reserve 0 remain pending acceptance. Pinned gitleaks
8.21.2 full-history/pending scans report zero; diff check passes. Local commit only.
No new PLAN-GAP or product judgment call. Owner decides the next funded run.

**14zj STOP: probe19 passed; qualification8 stopped at the first installed-system
physical login's read-completion proof.** No rerun or extra push. PR #13 remains
draft / NOT RELEASED. The pushed implementation is `85c9cfeeeddd6a2592f86bdf4603818bbeb48ee7`; the STOP packet is
committed locally only. Acceptance is unmet, so closing0/reserve0 are unchanged.

## 14zj REPORT — ACK fix verified; direct-login completion false negative

**Done:** self-delimiting per-transfer nonce/phase/index/status ACKs, exact field
and canonical status validation, duplicate/out-of-order/mismatch refusal, shared
complete-kernel-line stripping for every UART marker and the checksum-framed
export decoder. Truncated records cannot grant completion. Existing bounded
waits, verified guest SHA,512-byte controls,96-byte chunks and root-only tmpfs/modes
are kept. No automatic re-send was added without a receiver not-stored receipt.
All login/readiness/CMD_DONE/hidden-resync paths and the passive UART journal
readiness poll use the shared filter. Raw diagnostics retain kernel output; no
physical VCSA predicate, idle/Enter authority or log-level/emission change.
A buffered stale ACK refuses another send and is retained redacted on refusal.

Only harness/tests and package14 probe cap19 changed (1200 minutes/owner-tools8).
Package13, owner scripts and payload hash
683b1cff54d8a80406a70afd3f1173343a8a3fc95d301ef8cdbf05ab39010974,
guides, runtime/image, workflows, privacy rules and disk/firmware audit rules are
unchanged. No image build/release/publication, local installation/privilege, real
laptop/disk/boot/Minecraft access or Gradle invocation occurred.

**Verified:** final local470 tests/588.251s had the same8 documented native host
limitations (2 failures/9 errors),0 skips; both CI jobs later passed all470 natively.
Host walk261/463.350s passes, with119 cluttered waits and22 hidden-read ready/left
pairs. All8 ACK tests, existing export/PTY regressions, exact private14zi transcript
replay, kernel insertion at every ACK byte/socket split, malformed/duplicate/order
and truncated-record refusals, real Bash/PTY staging/resync and buffered-ACK
zero-send diagnostic pass. Strict549 compositions/524 embedded Python/12 shells/
47 Python/native workflow body pass. Windows copy15 zero-write refusals and exact
bundle equality pass; dispatch controller4 and watcher7 tests pass. Full replay,
read-only release/git/53-source steps pass;4 CI-token-only checks stay fail-closed
in CI and passed there. No credential/scope change or owner-secret use locally.

Pre-push ISO replay passed fresh-path attempt4 after two authorized checkpoint
WinError5 failures and a no-reader free-space preflight. Failed partial duplicates
were prefix-hash-verified before removal; read-only holder snapshot found none.
The separate qualification ISO replay passed attempt1. Both inspect all9,068,650,496
bytes against the pin and fresh official checksum, extracting4 localization/102
WebUI sources. Linux CI inspector behavior is unchanged.

Exactly one fast-forward push, followed by both exact-head privacy runs40654614484
and40654606957 passing all3 steps with personal terms actually executed. Both VM
runs are workflow_dispatch, attempt1, protected-second order on `85c9cfeeeddd6a2592f86bdf4603818bbeb48ee7`.

[Probe19](https://github.com/Ares-Empire/AresOS/actions/runs/40655273119) passed and
was accepted after independent artifact review. Native470/80.203s,0 skips;20 real
loop-image checks, helper mutations0, protected fixture unchanged and all fixture
mounts/loops cleaned. All23 staged transfers verify. The same598-byte server
script which formerly stopped at syntax ACK10 now passes every ACK phase and
SHA verification (protocol-before-after.json); no transfer retry was introduced.
Independent audits pass:3 protected captures,4 zero-write/unmap samples,3 BootNext,
2 NVRAM and2 complete-variable replays. Artifact12802991391:4,744,424 bytes/354
members, SHA256 `2ef4a0c2f06b1f7388b2ec18ee9d7da74a6b43bac1997589a06962c7447f1e8c`.

Before qualification, fresh exact-head privacy, strict/read-only replay and the
fresh complete113/113 guard passed:970 consumed +160 bound /1200, org after bound146,
exact$6/prevent=true budget with net Actions spend deducted at API pricePerUnit.

**STOP / PLAN-GAP:** [qualification8](https://github.com/Ares-Empire/AresOS/actions/runs/40658792992)
passed native470/79.477s with0 skips,20 native checks/0 helper mutations, pinned
ISO inspection, offline installation, offline hardware first boot (including its
orderly pre-login reboot), unattended Windows and detached-device Windows checks.
All28 staged transfers verify, including the failing observer command's byte/SHA
transport. It stopped at `Console.login -> send_hidden` on tools-stock, before
physical sudo, tools-stick attachment/install or any owner command/registry token.
No stopped owner-command record exists because no owner command was reached;
the harness readiness/completion/foreground record and private VCSA are exported.

The pre-send receipt proves login PID1962 on physical tty3, ECHO off and Password
at the cursor. The password and Enter were typed once. The bounded completion
receipt then reports ready=false but `Foreground interactive bash`: Bash PID2926,
PPID1962, own foreground group/session2926, same physical tty. The retained VCSA
ends at a shell prompt, not Password, with no Login incorrect. Its decoded-text
stdin privacy scan reports0 findings; no decoded text is saved. The original
login PID remains with the same executable/start identity, and the physical tty
is still ECHO-off for Bash readline: this follows from the observer's recorded
Bash chain and the existing hidden_left condition branches, not a retained raw
post-read termios dump. Login succeeded; this is a read-completion false negative,
not a failed credential or serial ACK. The14zi completion alternatives omit this
login-parent/child-Bash shape. No secret was retyped. No completion predicate,
timeout, harness, product or owner script was changed after the CI stop.

Failure paused the VM at boot7. Independent replay passes:7 protected captures,
8 zero-write/unmap samples,7 BootNext,6 NVRAM rule checks and6 whole-variable delta
checks. Private registry login, prepare/rerun, network-after-prepare proof, AresOS
switch, layout/revert, rollback and keep-stock were not reached this round.
Artifact12805406854:5,403,502 bytes/448 members, SHA256
`92198cf3943f814eebe4cab1e149cf279c80943896412704702187e8476ae20b`.

**Privacy:** pinned8.21.2 artifact scans: probe509=507 reviewed public ISO-listing
names +2 exact whole-line kernel X.509 messages; qualification515=507+8. Unknown
findings0. Both native logs, the failure-step log and in-memory decoded VCSA scan
return0 findings. Raw ISO listing, boot consoles, VCSA, decoded console text and
credentials are not committed. Exact accepted certificate-line records follow;
no ignore/allowlist/rule/privacy workflow change.

| Run | Private artifact path | Line | Certificate name | Whole-line SHA256 |
|---|---|---:|---|---|
| probe19 | `evidence/two-disk/live-ui-probe-boot-console.txt` | 491 | Fedora kernel signing key | `114a2d10cbf1b875d243ad0b86832cfd9309fd1404a25b49d555f86cbb505321` |
| probe19 | `evidence/two-disk/live-ui-probe-boot-console.txt` | 524 | Fedora kernel signing key | `cb9a947c057d77f5a0932e8c21597dafbd93cd88b19194164d98b00248844ae3` |
| qualification8 | `evidence/two-disk/offline-first-stock-boot-console.txt` | 502 | Build time autogenerated kernel key | `2bc883c6fb32d9d097940ede459608a542072f11b642507460d28045efca6925` |
| qualification8 | `evidence/two-disk/offline-first-stock-boot-console.txt` | 519 | Build time autogenerated kernel key | `820f18a92ddfeb8fd78ef61c1f5ab41c364a0bab4d776cc50d89b99b001a8d8e` |
| qualification8 | `evidence/two-disk/protected-second-install-boot-console.txt` | 493 | Fedora kernel signing key | `859d0e408118b78b2106f88db6f1353ca1db713336c3bd6c027065b5024959b1` |
| qualification8 | `evidence/two-disk/protected-second-install-boot-console.txt` | 524 | Fedora kernel signing key | `e6abf9705b109be5277949a3338528f6d5643b18ef423f54984fddfa0240aff9` |
| qualification8 | `evidence/two-disk/stock-initialization-0-boot-console.txt` | 498 | Build time autogenerated kernel key | `35e50b230b78276203c19a489a0d4faec766a77d381db4f36db459bdf369ba95` |
| qualification8 | `evidence/two-disk/stock-initialization-0-boot-console.txt` | 519 | Build time autogenerated kernel key | `78c256d1071eeef4172d5b9c709badae423bbd52437322a839a0a6354797d920` |
| qualification8 | `evidence/two-disk/tools-stock-boot-console.txt` | 498 | Build time autogenerated kernel key | `7f55ef5ed8e5375da27a83ccfb4b065f87357829f905a8ff109ba476f758fd08` |
| qualification8 | `evidence/two-disk/tools-stock-boot-console.txt` | 509 | Build time autogenerated kernel key | `d97c569b852cf578dccfc655c5d1a2206311773076028ba82817a475aa0e0f12` |

**Local STOP commit checks:** pinned gitleaks8.21.2 full history and all pending files return0 findings; manifest-format verification and git diff --check pass. The implementation/runtime/workflow/guide/privacy diff from the dispatched head is empty. No extra push.

**Closed ledger:**1019/1200 consumed, probes19/19 and owner-tools8/8, complete114/114
history, reserved0. One push, two dispatches, zero reruns. Read-only billing/budget
snapshot `2026-10-28T09:36:33.304275+00:00` requires exact$6/prevent=true and deducts already
charged net Actions spend using API pricePerUnit; exact values and response hashes
are in closed-ledger.json. The API snapshot may lag completed-job accounting.
Closing0/reserve0 are not restored because acceptance is unmet. No extra push;
the STOP packet is local only. PR #13 remains draft; never merge.

**Not verified / JUDGMENT-CALL / open questions:** the new ACK transport passed the
real probe and both jobs' executed commands; full owner-tools acceptance did not.
The installed tools and remaining owner stages need another authorized round.
A verified login-parent/foreground-child completion rule needs an integrator
decision before any source change or dispatch. Physical/followability gates stay
open; INSTALL/EMERGENCY/release gate retain that truth. No new product decision.

## 14zj preflight — Self-delimiting ACKs and shared kernel-line filtering

Historical pre-dispatch snapshot; outcomes above supersede its pending statements.

**Done:** staged transfers and cleanup/resync use a fresh per-transfer nonce and
`ARESOS_ACK:<nonce>:<phase>:<index>:<status>:END`. No newline is required to delimit
an ACK. The parser requires exact nonce, phase and canonical index, and a complete
canonical status0..255; only0 grants success. Mismatches, duplicates (including a
buffered stale ACK before sending), out-of-order replies and malformed statuses
STOP. Refused nonzero integrity/syntax steps retain the existing acknowledged
cleanup. Per-ACK10-second/transfer120-second deadlines,512-byte controls,96-byte
chunks, root-only tmpfs/modes, guest SHA verification and checksum-framed result
protocol remain. A failed or ambiguous transfer is not retried or run.

One shared function removes only complete timestamped kernel records with their
newline wherever they interrupt a userspace marker. An incomplete kernel record
cannot grant an ACK/readiness/completion; the live wait remains bounded, and the
export decoder refuses incomplete input. The export decoder still verifies the
exact decoded-byte SHA. Guest.wait normalizes before matching all UART markers:
command completion, login/readiness and hidden-resync ACKs. The passive serial
journal-readiness poll uses the same function and its original60-second bound.
Raw transcripts/boot consoles retain the emitted kernel messages. Physical VCSA
prompt/idle/resync predicates and kernel log levels/emission are unchanged.
Failure exports the redacted received transcript, including an already-buffered
stale ACK on a pre-send refusal; no write is sent under that refusal.

**Marker audit:** marker-audit.json lists each source hash and receiver path.
Stock/keyboard result markers already consume normalized Guest.command output.
Native tool stdout, offline journal JSON and the firmware Windows marker's
separate debugcon are distinct channels; no firmware audit was widened. The
inherited binary check channel and runtime emitters are unchanged.

**Verified:** all8 new ACK tests pass: the exact retained14zi non-secret ACK span,
the complete private14zi transcript replay, a kernel record at every ACK byte
position, every socket split, incomplete records with bounded STOP, exact fields,
duplicate/out-of-order/malformed replies, every other UART readiness/completion
marker, export marker/checksum regressions, real Bash/PTY staging + hidden resync
and zero execution/retry on a duplicated ACK. The initial excerpt fixture omitted
the following userspace CRLF; it was corrected from the retained bytes, never by
loosening the assertion or adding legacy ACK acceptance. Whole raw transcripts
remain private; only the exact non-secret ACK span/source hash is a test fixture.
Existing export/terminal/real-PTY tests execute unchanged.

Final local470-test suite:599.076s on the first complete pass; the final rerun is
recorded as588.251s. Both have the same8 native host limitations (2 failures/9 errors),
listed by name in whole-suite.txt;462 distinct passes,0 skips. Native CI must pass
all470 before a VM can count. The261-test host walk passes and covers all remaining
stages,119 cluttered prompt waits and22 matched hidden-read ready/left pairs.
Strict checks pass549 guest/control compositions,524 embedded Python,12 shells,
47 Python files and the native workflow body, refusing any Bash parse stderr.
Windows copy:15 zero-write refusals plus exact payload equality. Local single-POST
controller4 tests and fixed watcher7 tests pass; counters are18-before/19-after
probe with qualification8 unused.

Actual release/git/file/read-only replay and53 zero-cost source checks pass. The
four14f credential steps remain explicitly CI-only/fail-closed; no local scope or
credential change and no owner secret use. Actual ISO replay rehashes9,068,650,496
bytes against the pin and fresh official checksum, extracting4 localization/102
WebUI sources. Attempts1/2 hit authorized Windows checkpoint WinError5; attempt3
was the local >25GiB preflight, with no reader started. Ended partial files were
prefix-hash-verified against the retained ISO and only those ordinary duplicates
removed. A read-only Restart Manager snapshot found no holders. After the final
30-second wait, fresh-path attempt4 passed. No overlapping ISO reader, process
termination, Windows setting, install or Linux CI inspector behavior change.

**Scope / safety / JUDGMENT-CALL:** harness/tests and package14's probe cap19 only;
minute cap1200 and owner-tools8. Package13 settings, owner commands, payload hash
683b1cff54d8a80406a70afd3f1173343a8a3fc95d301ef8cdbf05ab39010974,
INSTALL/EMERGENCY/release gate, frozen runtime/image, workflows, privacy policy,
firmware/BootNext/disk audits and credentials are unchanged. No automatic re-send
was introduced: no receiver not-stored receipt exists, so ambiguous chunk waits
STOP under the brief's conditional permission. This takes the allowed conservative
option without changing an owner/product decision. No image dispatch, publication,
local privilege or real laptop/disk/boot/Minecraft access. No Gradle started.

**Privacy / final local checks:** pinned gitleaks8.21.2 full history and pending files return0 findings. Manifest/session/console equality checks and git diff --check pass; no policy or ignore change.

**Budget / plan:** complete baseline941 consumed +238 bound /1200; probes18/19 and
owner-tools7/8, complete110/110 history, org after bound97 at that snapshot. Fresh
ledger/billing/$6 prevent=true budget (deducting net charged Actions spend at API
pricePerUnit) is required immediately before push/each dispatch. Exactly one clean
pinned-gitleaks fast-forward push, fresh exact-head privacy, probe19; only accepted
probe evidence permits qualification8 on the same head in protected-second order.
Any CI stop exports diagnostics and ends dispatches with no rerun. Only acceptance
permits closing12/reserve150 restoration, final clean push/privacy and PR-ready;
never merge. Physical/followability release gates remain unverified and true.

**Not verified / PLAN-GAP / open questions:** new native/probe/qualification results
are pending. The requested serial ACK repair is the integrator's explicit change;
no new product policy or owner-script change. Physical release gates remain open.

## 14zi REPORT — Inner-pts fix implemented; probe18 serial ACK stop

**Done:** the harness verifies the exact foreground reader through the bounded
sudo relay chain, its own tty ECHO off, and the expected prompt at the physical
cursor before typing once. A separate bounded read-completion receipt observes
echo restoration, exit/exec or authenticated sudo relay creation, without the
value. Direct physical-tty reads retain their own tty check. All hidden inputs
share this rule. Owner scripts, payload fingerprint
683b1cff54d8a80406a70afd3f1173343a8a3fc95d301ef8cdbf05ab39010974,
guides, frozen runtime, workflows and privacy policy are unchanged. Package14
only is1200 minutes/probe18/owner-tools8; package13 is unchanged.

**Diagnosis:** confirmed by pinned CPython3.14.8 getpass ordering and real two-PTY
flush/loss-versus-delivery tests. Qualification7 is consistent with early input
being flushed; qualification4 additionally retains its independent serial-framing
failure. Neither historical run retained inner termios/prompt at send, so the
precise historical flush timing and sole causation are not claimed. Source
metadata and the redacted retained process fixture are in14zi-preflight.

**Verified:** local462 tests ran with the same8 documented host limitations;
243 host-walk tests pass, including119 cluttered waits and22 matched hidden-read
ready/left pairs. All10 hidden tests pass, including the unchanged real at entry
point resolving the installer's actual tools/owner.py path. Strict checks pass
549 guest compositions,524 embedded Python,12 shells,47 Python and the native
workflow body. Local release/file/git/read-only replay passes; a fresh9,068,650,496
byte ISO replay also passed on its first attempt before this probe completed.
The four14f CI-only checks remain fail-closed and passed natively in this probe.
No laptop installation, privileged local operation, real disk/boot/Minecraft
access, image build, release or publication occurred. No Gradle started.

Exactly one fast-forward push was made. Both exact-head privacy runs40646398141
and40646392604 passed all3 checks with personal terms actually executed. The
fresh complete guard authorized919 consumed +232 bound /1200 with109/109 history.
[Probe18](https://github.com/Ares-Empire/AresOS/actions/runs/40646962291) was attempt1,
workflow_dispatch on pkg/14-owner-tools, exact head `9c3f8a3722e3321150813456fecad7abbfefda3e`.
Native CI passed all462 tests in67.200s with0 skips; all20 native loop-image checks
pass, helper mutations0, protected fixture unchanged and mounts/loops cleaned.
Pinned ISO length/SHA agree with the fresh official checksum. Native tools,
release identity, registry access/signature and layer checks passed.

**STOP / PLAN-GAP:** live VM probe stopped at webui-probe-server's staged transport,
before its script was run and before any owner hidden input. The598-byte script's
7 chunks and SHA/integrity phase were acknowledged. Syntax phase index10 actually
emitted status0, immediately followed by `[   58.604886] async_tx: api initialized (async)`
before the newline. The existing exact `:10:(status)\r?\n` ACK predicate therefore
has no match in the retained6,676-byte transcript and timed out after its bounded
10-second wait. The transport records `no acknowledgement; STOP; no retry` and
verified=false. This is a kernel-output interleave at the serial ACK boundary;
it is not evidence that the14zi hidden fix failed. No transport, log-level,
predicate, timeout, product or owner-script change was made after the stop.
Private raw transcript/diagnostics are retained in artifact12799091255; committed
metadata records their hashes and the exact parser observation, not raw consoles.

The failure path paused the VM at boot2. Independent replay of actual protected
captures, counters and varstores passes:2 protected captures,2 zero-write/unmap
samples,2 BootNext replays,1 NVRAM rule replay and1 complete-variable delta check.
The failed probe is not accepted. Qualification8, installed/private login, layout,
AresOS switch, rollback and keep-stock were not run this round.

**Privacy:** artifact SHA256
`df12af2c722e83a2d88b4f75b2dbba88f99b8bfe908a6efed8898e50d0f66508`,
3,121,033 bytes/217 members. Pinned8.21.2 artifact scan:509 findings =507 reviewed
public ISO-listing names +2 exact whole-line kernel X.509 messages below;
0 unknown findings. Native-suite and failure-step scans return0 findings.
No ignore, allowlist, rule or privacy workflow change. Raw boot consoles, VCSA,
ISO listing and credentials are not committed.

| Private artifact path | Line | Certificate name | Whole-line SHA256 |
|---|---:|---|---|
| `evidence/two-disk/live-ui-probe-boot-console.txt` | 495 | Fedora kernel signing key | `1a71b7af06abd9e4fdf934035749bdc41b986c66d1021be9e7879866ce19ecb0` |
| `evidence/two-disk/live-ui-probe-boot-console.txt` | 528 | Fedora kernel signing key | `2fa42f36634355498515b410eb5844db1af48c96624b3d4743f9034dd09c18fc` |

**Local STOP commit checks:** pinned gitleaks8.21.2 full history and all pending
files return0 findings; manifest-format verification and git diff --check pass.
Implementation/runtime/workflow/guide/privacy diff from the dispatched head is
empty. No extra push.

**Closed ledger:**941/1200 consumed, probes18/18 and owner-tools7/8;110/110 complete
history, reserved0. One push, one dispatch, zero reruns. Read-only billing/budget
snapshot `2026-10-28T07:22:25.296728+00:00` requires exact$6/prevent=true, deducts already charged
net spend and uses API pricePerUnit; see closed-ledger.json for the exact values.
Billing is a timestamped API snapshot and may lag the completed-job ledger.
Closing0/reserve0 remain because acceptance is unmet; restoration12/150 and a
final push/PR-ready are conditional on acceptance. No more dispatch or push this
round. The run is over; the owner can set the Actions budget back to$0.

**Not verified / JUDGMENT-CALL / open questions:** the hidden-input fix has real
PTY/native/model proof, but no VM owner-input qualification this round. Physical
and followability gates remain open and INSTALL/EMERGENCY/release gate retain
that truth. The ACK-boundary interleave needs an integrator decision before any
further change or dispatch. No new product decision was taken; never merge.

## 14zi preflight — Hidden prompts on the actual reader tty

Historical pre-dispatch snapshot; the STOP outcome above supersedes its pending statements.

**Done:** shared harness code follows the physical foreground through verified
sudo frontend/direct-monitor transitions, at most3 new pts, and exact expected
reader identity/executable/argv. Unknown processes, malformed/changed chains,
reused pts, extra foreground candidates and a fourth hop refuse. Owner reads
require the reviewed Python -I -B owner.py command, sudo passwords the exact
sudo command, and getty passwords login. Before a hidden value is sent, the
reader's own tty must have ECHO off and the expected public prompt must end the
physical cursor line. The physical tty is still used for direct getty/outer-sudo
reads; tty3 raw mode alone never authorizes an inner-pts value.

After its single physical send, a separate bounded60-second observation requires
reader echo restored, reader exit/exec, or the verified sudo relay starting.
Only identity/termios/phase facts are retained, never the value; all argv in
these chains are redacted. A consumed grant cannot send again, including after
a timeout or partial-key failure. Failure retains raw VCSA privately plus the
redacted chain and STOPs. The existing840-second command-to-idle observation,
three-sample shell predicate and max2 independently proved Enter resyncs remain.
Read completion itself grants no Enter and does not claim authentication passed.
Account login, outer sudo, second-console layout-proof sudo and private token
input all use this same path. Every read/left wait has a unique receipt name.

**Diagnosis, confirmed mechanism / historical limit:** pinned guest RPM metadata
is python3.14-3.14.8-1.fc44. The official
[CPython3.14.8 getpass source](https://raw.githubusercontent.com/python/cpython/v3.14.8/Lib/getpass.py)
sets TCSAFLUSH before writing the prompt and restores termios before returning.
The local real two-PTY child/getpass/relay test proves the old outer-echo check
fires early, queued input disappears at the flush, and the child remains waiting.
The new check waits for inner echo-off plus the prompt, delivers the synthetic
value exactly once, observes echo restoration and never echoes it. No actual
credential is used in this reproduction; the sudo ancestry is explicitly modelled,
while PTYs, termios, forwarding, queued-byte counts and getpass are real.
The external module is not committed; its source hash/version/URL are recorded.

Qualification7 supports this diagnosis: its old hidden check returned ready,
then physical tty3 stayed echo-off, the owner Python process remained foreground
on the innermost pts, and the retained screen ended at the hidden-token prompt.
Serial transport completed; no owner PASS/STOP was produced. The exact captured
redacted process shape is a fixture, not an invented sudo topology. Qualification4
also used the unsound physical-tty check, but its retained116-byte transcript has
continuation prompts and no CMD_DONE: an independent serial-framing failure is
present. Neither run retained inner termios/prompt at the instant of send, so
historical flush timing and sole causation cannot be proved from those artifacts.
The mechanism is confirmed by code and real reproduction; the records are
consistent with it, and no unseen token delivery is claimed.

**Verified locally:**10 hidden-input tests cover the real flush/delivery contrast,
the actual qualification7 process shape, busy/no-prompt, wrong argv/executable,
broken/reused pts links,3/4-hop boundary, both physical consoles and every reader
kind, bounded completion refusal and a second-send rejection.19 real Bash/PTY
transport tests and13 VCSA/idle tests pass. The full462-test suite ran in584.803s:
454 distinct passes plus the same8 native host limitations (2 failures/9 errors),
listed by name in whole-suite.txt; no skips or assertions were weakened. The
243-test host walk passes, executing real observer source over /proc fixtures at
119 cluttered shell waits and22 matched hidden-read readiness/completion pairs
through every remaining qualification stage. A real entry-point regression executes
the installer's ordinary-file placement statements and resolves the unchanged at
wrapper, requiring /var/lib/ares/tools/owner.py (the install audit caught and
corrected the initial harness expectation before push). An initial stand-in routing error
was corrected at its capture_json boundary; its failing result is retained.
Windows copy tests pass15 zero-write refusals with exact bundle equality; all
commands still equal the guide.4 single-dispatch controller and7 watcher tests pass.

Strict checks pass549 guest/serial/staging compositions (any Bash parse stderr
refuses),524 embedded Python,12 shells,47 Python files and the native workflow
body. Actual release/git/file/read-only replay and53 offline source checks pass.
Four CI-token-only registry steps remain deferred with their14f reasons and exact
fail-closed CI steps; no local credential/scope change or owner-secret use.
The real ISO inspector replay rehashed9,068,650,496 bytes against the pin and
fresh official checksum, with4 localization/102 WebUI sources. It passed on local
attempt2 after the authorized checkpoint WinError5/fresh-path10-second retry.
No Linux CI inspector behavior, package pin or package list changed.

**Scope / safety:** only harness/tests and package14 cap1200/probe18/owner-tools8
changed. Package13 settings, owner scripts/payload fingerprint
683b1cff54d8a80406a70afd3f1173343a8a3fc95d301ef8cdbf05ab39010974,
INSTALL/EMERGENCY/release gate, frozen image/runtime, workflows, disk/firmware/
BootNext audits, privacy policy and credentials are unchanged. No image build,
release/publication, system installation, local privilege, real disk/boot change
or laptop/Minecraft access. No Gradle started.

**Privacy / final local checks:** pinned gitleaks8.21.2 full history and pending files return0 findings. Manifest/session/console equality checks and git diff --check pass; no policy or ignore change.

**Budget / plan:** the complete pre-push snapshot is913 consumed +238 bound /1200,
probes17/18 and owner-tools7/8, complete107/107 history; org after bound128. The
read-only guard requires exact$6/prevent=true and deducts net Actions spend using
API pricePerUnit. Exactly one clean-gitleaks fast-forward push, then fresh exact-head
privacy, complete ledger/billing/budget, probe18, and only after full acceptance
qualification8 on that same head in protected-second order. Any CI stop exports
diagnostics/reports with no rerun or extra push. Closing12/reserve150 restoration,
final clean push/privacy and PR-ready require actual acceptance; never merge.

**Not verified / JUDGMENT-CALL / open questions:** fresh native/probe/qualification
and physical/followability gates remain pending. The stronger hidden-reader proof
is the explicit14zi integrator decision; no new product or owner-script policy.

## 14zh REPORT — Fresh prompt authority verified; private-login STOP

**Done:** every shell-prompt wait now requests a fresh14ze sudo-relay idle
observation before each bounded Enter when the cursor has no prompt. It exports
the observer answer/chain and cursor lines, rejects input-epoch changes, and gives
each wait/sample/observer a globally unique receipt name across guest instances.
The strict cursor predicate,3 stable samples,90-second prompt deadline,2-Enter
limit and console log level are unchanged. Busy/unknown foregrounds never grant
Enter. Login/getty/command-input waits still cannot inject resync Enter. The owner
payload/fingerprint, commands, guides, frozen runtime, workflows and audits were
unchanged; only package14 allowances became probe17/owner-tools7, cap1100.

**Local verification:** the exact retained qualification6 cursor region plus
modelled /proc sudo relay recovers with1 Enter; busy refuses with0; persistent
clutter stops after2. All5 shell-wait kinds and repeated stage names/new guests
are tested. The complete stand-in route covers119 cluttered shell waits through
export/Windows/corrected stock/login/verify/switch/AresOS/layout/rollback/keep-stock,
each with a real observer executed on /proc relay fixtures (tty3 and tty4).
The233-test walk passes; the452-test full local suite retains only8 known native
limitations (2 failures/9 errors; no skips), all resolved in both hosted runs.
The19 transport tests,13 console targets,15 zero-write Windows refusals, bundle/
command equality,4 controller and7 watcher tests pass. Strict checks cover527
guest/serial/staging scripts,502 embedded Python,12 shells,46 Python and the
native workflow body. Actual release/git/file replay and53 offline source checks
pass; CI-only registry checks remain fail-closed and passed in both runs.
The local probe ISO replay used the authorized fresh-path Windows retry after
one checkpoint WinError5 (10-second wait); qualification replay passed first try.
Both rehashed9,068,650,496 bytes against the pin/fresh official checksum; no CI
inspector behavior changed. Initial local adapter failures and final results
are retained in14zh-preflight; no assertion, skip, ignore or rule was weakened.

**Push/privacy/guards:** pinned gitleaks8.21.2 full history and43 pending files
returned0 before the single fast-forward push from `ea803fd` to `d15678d`.
Exact-head privacy40627657801 (push) and40627663601 (PR) passed all3 steps with
personal terms actually executed, rechecked before qualification. Pre-push:
810+238/1100; pre-probe816+232/1100, complete105/105 history, org after237;
pre-qualification836+160/1100, complete106/106, org after283. Both dispatches
verified exact$6/prevent=true, API pricePerUnit and net-spend subtraction. The
fixed returned-URL watcher confirmed each run directly; no repeat POST or list
fallback. There was no additional push while the qualification ran.

**Probe17:** [40628158654](https://github.com/Ares-Empire/AresOS/actions/runs/40628158654)
completed success, protected-second, no install. All452 native tests passed in
69.268s with0 skips; native loop integration passed20 checks/0 helper mutations,
unchanged protected fixture and complete cleanup. All23 staged transfers verified
guest SHA/syntax. Independent replay passed3 protected captures,4 zero write/unmap
samples,3 raw-varstore/exact-BootNext,2 NVRAM rules and2 whole-variable deltas.
Artifact12790199665:4,745,358 bytes /354 members; SHA256
`32998b67525a8efdaaca2bbaa8356f3d07794a83c4074f551372c900ead8842c`.
Privacy509 =507 reviewed ISO paths +2 whole kernel X.509 lines,0 unclassified.

**Qualification7 verified before STOP:**
[40630352782](https://github.com/Ares-Empire/AresOS/actions/runs/40630352782)
passed all452 native tests in74.134s,0 skips, all20 native loop checks/0 helper
mutations and cleanup, all4 private release/access checks and pinned ISO inspection.
Offline install/first stock boot, the allowed hardware-initialization reboot and
unattended/detached Windows round trips passed. Physical account login/password
sudo passed, tools were hot-plugged after login, install/prepare passed, and
prepare rerun recorded0 Host mutations. The former after-network-title completion
wait passed. Records and record export passed; exact before/after-network snapshots
are equal (deployments/pin/pending/BLS unchanged). The tools stick was detached
before reboot; prepared unattended Windows and corrected-stock boot, keyboard,
physical public typing, title/records and inherited Homebrew checks passed.
Two actual cluttered waits (`tools-install-ready-wait-5` and
`tools-before-reboot-title-ready-wait-19`) each recovered with1 physical Enter,
a fresh ready observer/foreground chain and a strict ready cursor afterwards.
There were no unproved resync Enters. All101 retained staged transfers verified
SHA/syntax; the serial hidden-input resync passed with prior completion observed,
input flushed and no physical Enter.14zh's known prompt-wiring gap is resolved.

**STOP / evidence:** the failure is
`qualification -> console.run(login, private-owner-login) -> after_hidden`:
`Hidden owner command did not return to an idle shell`. After840 seconds the
observer correctly refused: physical tty3's outer `sudo -i` relay led to root
Bash on pts/1 whose foreground group was the nested sudo5396, then monitor5399
and Python5400 on pts/2 (foreground5400). It was not foreground idle Bash.
The exported non-secret chain redacts every nested/post-hidden argv. No resync
Enter was sent into that busy command. Raw VCSA is50x160, cursor(x26,y49), ending
at `Read-only token (hidden):`; no `PASS login`, owner STOP or private-login result
record exists. Its SHA256 is
`63df235554d03b43788e97bfdfb7ba5c45dfa6eefaad8c074aa468c06ba84484`.
No decoded console text was saved or committed. An additional in-memory decoded
VCSA gitleaks scan returned0; no standard token prefix is present. Raw VCSA and
consoles stay in the private artifact. The failure counter records boot9, paused.

**Cause limit / PLAN-GAP:** the evidence proves the private owner command did
not return, while serial framing and transport completed. It supports an
uncompleted hidden input, but does not prove whether physical bytes arrived too
early, were flushed or were dropped. At the send instant there is no retained
inner-pts termios or visible-hidden-prompt observation: the existing hidden
readiness query observes physical tty3 echo/foreground, not the nested reader's
actual hidden-read state. No token delivery, credential-file write or successful
registry login is claimed. A next integrator decision must address that boundary;
this STOP includes no observer weakening, owner-script change or implementation
fix. Verify/switch, AresOS boot/layout/session-helper VM proof, rollback, keep-stock
and the final Windows checks were not reached. All physical/followability gates
remain NOT RELEASED. No laptop or Minecraft folder was touched; no Gradle started.

**Safety/privacy/export:** independent failure replay passed9 protected captures,
10 zero write/unmap samples,9 raw-varstore/exact-BootNext replays,8 NVRAM rules and
8 whole-variable deltas.9 passed owner records, refusal chain, raw VCSA, transports,
failure counters, block statistics and varstores were exported and retained.
Qualification artifact12794106604:9,592,320 bytes /762 members; SHA256
`a60611cdc103d29ed9ad1f42c64e1e095c7a465a63443657dd63c464268f8ba3`.
Native/failure logs scan0. Artifact517 =507 ISO paths +10 exact whole kernel X.509
messages,0 unclassified. Every accepted kernel source line is recorded by path,
line, certificate label and whole-line SHA below and in the manifest. No ignore,
allowlist, rule or workflow changed. Raw ISO listing paths were not committed.

**Local STOP commit checks:** pinned gitleaks8.21.2 full history and all pending files return0 findings; manifest-format verification and git diff --check pass. The implementation/runtime/workflow/guide/privacy diff from the dispatched head is empty. No extra push.

**Closed ledger:**913/1100 charged minutes, reservation0, probes17/17 and
owner-tools7/7, complete107/107 history. This round used1 push,2 single dispatches,
0 reruns,0 images/publications. Read-only billing: exact$6/prevent=true; reported
net Actions$3.804, API price$0.006/minute,
366 paid minutes available (billing may lag). Acceptance=false;
closing0/reserve0 were not restored because restoration requires acceptance.
PR #13 remains draft; all dispatch allowances are used. This round is over;
the owner can set the paid budget back to$0. No additional push or dispatch.

| Run | Captured boot console | Line | Certificate label | SHA256 of whole line |
| --- | --- | --- | --- | --- |
| probe17 | `evidence/two-disk/live-ui-probe-boot-console.txt` | 491 | Fedora kernel signing key | `f67606bae9b34bb8e3658435c51897f721bba72a9cc1423c228187dc948a6141` |
| probe17 | `evidence/two-disk/live-ui-probe-boot-console.txt` | 525 | Fedora kernel signing key | `9c0711fd1890904accd252fe50e3b6f47a5bf6193d5cc8d70496b7d92acbd96b` |
| qualification7 | `evidence/two-disk/corrected-stock-boot-console.txt` | 498 | Build time autogenerated kernel key | `3e2f80f2f2ea0d727caefdffa4c67a500968c60b795b0b9f5e2ffbd781b0a0f3` |
| qualification7 | `evidence/two-disk/corrected-stock-boot-console.txt` | 509 | Build time autogenerated kernel key | `3f660b367d624734980e88f03b1447c9f87e5d78a3f214c78178e699eb788865` |
| qualification7 | `evidence/two-disk/offline-first-stock-boot-console.txt` | 518 | Build time autogenerated kernel key | `08c4558e18d70f7e0325fd29f16d437d43cf43be6985fa31f2f717fe950a8795` |
| qualification7 | `evidence/two-disk/offline-first-stock-boot-console.txt` | 529 | Build time autogenerated kernel key | `dcae64be12127ace403380990e02e97fd136d728ee745d318b2efcd6e79f9560` |
| qualification7 | `evidence/two-disk/protected-second-install-boot-console.txt` | 491 | Fedora kernel signing key | `a39e487a8a0dc3ccad99344a32b3a0fcede4645e35bd5a3304c0a30bcc842384` |
| qualification7 | `evidence/two-disk/protected-second-install-boot-console.txt` | 524 | Fedora kernel signing key | `0c19882909b78bf37d5b6ac16c8d11e0644f317568733766c43acdebdd788895` |
| qualification7 | `evidence/two-disk/stock-initialization-0-boot-console.txt` | 499 | Build time autogenerated kernel key | `c1bd68c4e5be8487f8ed7c1abd0eca56b28fd41da1a404a10c871102ba55ec1d` |
| qualification7 | `evidence/two-disk/stock-initialization-0-boot-console.txt` | 520 | Build time autogenerated kernel key | `f0f92f4bd3e4e01d959caf68fd2f21972ca7322a8e09b98a7efaceb49e6ef3f9` |
| qualification7 | `evidence/two-disk/tools-stock-boot-console.txt` | 498 | Build time autogenerated kernel key | `399fdbae5afd6d1ee6a8f3375b7b1c68493ea2acb88b3faa7460c743821f9bbc` |
| qualification7 | `evidence/two-disk/tools-stock-boot-console.txt` | 515 | Build time autogenerated kernel key | `ca3527e291700ac4001ef62b62117fc7cc73b9e16427b2db3b04f2f82c3311c8` |

## 14zh preflight — Fresh idle observer in every prompt-readiness wait

Historical pre-dispatch checks; the outcomes above supersede pending statements.

**Done:** the shared Console.prompt path now offers the14ze sudo-relay observer
whenever a shell cursor line has no prompt, including completed, after-hidden,
after-hotplug/network and after-boot waits. Every Enter requires a fresh observer
answer and unchanged input epoch. An observer refusal records its redacted
foreground chain and raw VCSA, then STOPs without Enter. Each attempt retains
before/after cursor lines, stage and observer answer; sequence/sample/observer
names are unique across repeated stage labels, Console instances and guest boots.
The cursor predicate, three stable samples,90-second prompt deadline and maximum
2 Enters are unchanged. Login/getty, hidden-input and command-input predicates
still cannot send resync Enter. No console log-level change.

**Verified:** the exact retained qualification6 cursor region (geometry and last
2 rows; unrelated upper rows blanked) plus the real read-only observer on a
modelled /proc sudo relay recovers with1 Enter. The busy foreground refuses with
0 Enters and exports its chain;3 cluttered screens STOP after2 separately proved
Enters. All5 wait kinds use the same path, repeated labels retain unique receipts,
and typing during observation still revokes authority. The complete stand-in
qualification walks every later stage, with clutter at all119 shell waits:
export and Windows round trip, corrected stock/login/verify/switch, AresOS boots,
layout begin/proof/revert/finish, rollback and keep-stock. It executes the observer
on /proc relay fixtures for both tty3 and tty4 at every resync; all command/serial/
staging scripts pass strict bash -n (any stderr refuses). These are local stand-ins,
not evidence that the later stages passed in a VM.

The final whole suite ran452 tests in444.005s:444 distinct passes and the same8
known native host limitations (2 failures/9 errors), listed in whole-suite.txt.
No skips or assertions were weakened; the native probe must resolve every one.
The host walk passes233 tests;19 serial transport tests pass, including the exact
hidden-login sequence and a lost chunk STOP. New unique receipt suffixes required
updating that PTY fixture's public-prompt adapter; the initial failing results are
retained. Windows pwsh -NoProfile copy tests pass15 zero-write refusals and bundle
equality; two initial in-process setup invocations refused the mock root. The
established separate-process invocation passed without implementation changes.
4 controller and7 fixed-watcher tests pass.

Actual git/file/read-only release and53 zero-cost source checks pass. The ISO
inspector rehashes9,068,650,496 retained bytes against the pin and fresh official
HTTPS checksum, extracts4 localization/102 WebUI sources, and passes on local
attempt2. Attempt1 hit the authorized Windows checkpoint Path.replace WinError5;
there was only one replay/reader and the fresh-path retry followed a10-second
wait. Linux CI behavior was unchanged. Strict checks pass527
guest/serial/staging scripts, 502 embedded Python,12 shells,
46 Python sources and the native workflow body. The4 CI-token-only registry
steps remain deferred with their14f reasons and exact fail-closed CI step names.

**Scope/safety:** harness and regression changes only, plus package14 probe17/
owner-tools7 allowances; minute cap1100. Package13 settings, owner commands,
payload and fingerprint683b1cff54d8a80406a70afd3f1173343a8a3fc95d301ef8cdbf05ab39010974,
INSTALL/EMERGENCY/release gate, frozen image/runtime, audits, privacy policy and
credentials are unchanged. No local privilege, hardware, image, release or
publication operation; no Gradle started.

**Privacy / final local checks:** pinned gitleaks8.21.2 full history and pending files return0 findings. Manifest/session/console equality checks and git diff --check pass; no policy or ignore change.

**Budget / dispatch plan:** the complete pre-push snapshot counts
810 +238 bound /1100, probes16/17 and owner-tools6/7;
org after reservation231. The read-only budget
requires exact$6/prevent=true and deducts reported net Actions spend using API
pricePerUnit. Exactly1 fast-forward push, then fresh exact-head privacy, complete
ledger/billing/budget, probe17, and only if accepted qualification7 on that same
head. A CI stop exports diagnostics and ends the round with no rerun/extra push.
Closing12/reserve150 restoration and PR-ready require actual acceptance.

**Not verified / open questions / JUDGMENT-CALL:** fresh native/probe/qualification
and the physical/followability gates are pending. The fresh-authority wiring is
the explicit integrator decision14zh. No new product or owner-script policy.

## 14zg REPORT — Probe16 accepted; qualification6 console-readiness STOP

**Done / shipped head:** the integrator's max3 nested-sudo relay policy, all
14zf recovery-session facts, direct-tty consistency, generated payload and current
INSTALL fingerprint were committed/pushed as `ea803fd`. The16 session tests,
232-test host walk,20 session/parser targets,451-test local suite and fresh
read-only replay/strict/Windows-copy checks are described below. Both hosted
runs resolved the8 local native limitations: all451 native tests passed with
0 skips (probe57.075s; qualification57.077s). Native loop tests passed20 checks,
0 helper mutations, unchanged protected fixture and full cleanup. All4 CI-only
private registry/release checks passed in both runs. No credential or scope change.

**Push/privacy/guards:** exactly one normal fast-forward push from `e3751ad` to
`ea803fd`, after pinned gitleaks8.21.2 full history and pending files returned0.
Fresh exact-head privacy runs40614308783 (push) and40614313020 (PR) passed all3
steps with personal terms actually executed. They were rechecked before the full
qualification. The local broad email check encountered retained pre-rewrite refs;
HEAD and origin histories were independently checked clean. Those retained refs
were neither changed nor pushed; CI's unchanged all-ref check passed. The source
head's committed-byte bindings matched before dispatch. Both fixed watchers
confirmed the returned canonical run URL without a list fallback or repeat POST.
Pre-probe guard:733+232/1100, complete101/101 history, org after reservation320.
Pre-qualification guard:756+160/1100, complete102/102, org after reservation369.
Both verified exact$6 Actions budget/prevention=true, API price and net-spend
subtraction immediately before the single dispatch.

**Probe16:** [40614909488](https://github.com/Ares-Empire/AresOS/actions/runs/40614909488)
completed success, protected-second, no install, with all retained probe flags.
Independent replay passed3 protected captures,4 zero write/unmap samples,
3 raw-varstore/exact-BootNext replays,2 NVRAM rule and2 whole-variable deltas.
All23 retained staged-command transfers had guest SHA256 and strict syntax
verification. Artifact12786175701:4,745,042 bytes /354 members,
SHA256 `61757dc544b2b5555b6904898ac72af8896766a4ca7a4607878b012faa0236d5`.
Artifact privacy:509 findings =507 public pinned ISO paths +2 exact whole kernel
X.509 messages,0 unclassified; native log scan0.

**Qualification6 STOP:** [40617562735](https://github.com/Ares-Empire/AresOS/actions/runs/40617562735)
completed failure in the VM step at
`qualification -> console.run(title, after-first-network-title) -> prompt(completed)`.
Offline installation passed; stock completed its one permitted hardware-setup
reboot; offline first stock had no pending/staged/pinned state, network down and
no tools attached. Both unattended and detached Windows round trips passed.
Separate account-login and sudo readiness receipts passed, demonstrating that
the14ze root-sudo idle observer now returned. The tools stick was hot-plugged,
owner install passed, prepare passed, and prepare rerun reported0 Host mutations.
Network was then enabled. The actual owner `title` command produced `PASS title`,
pinned stock, idle transaction, no staged/queued state and resolved title
`Bazzite (ostree:0)`; its saved owner diagnostic record passed with0 Host mutations.

The subsequent raw VCSA sample has50 rows,160 columns and cursor(x0,y49), whose
line is empty. The previous row contains a displayed root prompt followed by
`[  273.927657] sched: DL replenish lagged too much`. The root prompt therefore
is not on the cursor line required by the unchanged predicate. There are0
completed-wait resync records and one retained timeout VCSA file. The owner
record passed before this wait; no fresh physical foreground-idle proof was
recorded at this completion wait, so the source's current epoch rules did not
grant an Enter. A visible earlier root prompt is not independent proof that
its foreground shell was idle at that instant. No log-level/prompt/idle-policy
relaxation or Enter injection was made after the stop.
Raw VCSA SHA256 `49fe0fb31a704316aaf873a5e3105009fc47384b014040bd99029d24f678dc23`;
raw console/VCSA remain private artifacts, not committed. No guest GH token was
typed: the stop precedes record export, the full before/after-network snapshot
comparison, corrected-stock reboot, private guest login, switch, AresOS boot,
layout/session validation, rollback and keep-stock. Those remain unverified.
The new product session helper is covered by native tests but was not reached
by the real VM layout stages.

**Safety / exported diagnostics:** the failure counter recorded boot7 with the
VM paused. Independent replay passed7 protected captures,8 zero write/unmap
samples,7 raw-varstore/exact-BootNext replays,6 NVRAM rule and6 whole-variable
deltas. Owner result/trace records, raw VCSA, separate account/sudo readiness,
serial framing, block counters and varstores were exported and retained.
Qualification artifact12787718785:7,048,250 bytes /540 members,
SHA256 `2d9db6f7c9ee0a41d376138bd0da27acef6fbeeb8e75709421dfba9638563854`.
Native and failure-log privacy scans returned0. Artifact privacy:515 findings =
507 ISO paths +8 exact whole kernel X.509 messages,0 unclassified. Every accepted
kernel source line is recorded by path/line/hash/label below and in the manifest;
no ignore entry, rule or workflow changed. Raw ISO listing paths were not committed.

**Local STOP commit checks:** pinned gitleaks8.21.2 full history and37 pending files returned0 findings. Hash-manifest validation passed; implementation/workflow/runtime diff from the dispatched head is empty. No extra push.

**Closed ledger:**810/1100 charged minutes,
reservation0, probes16/16 and owner-tools6/6. Complete103/103 history. This round
made1 push,2 single dispatches,0 reruns,0 image attempts/publications. Read-only
budget snapshot: amount$6, prevent=true, reported net Actions
spend$3.186, API price$0.006/minute,
469 paid minutes available (billing may lag). Acceptance=false;
closing0 and reserve0 were not restored because their restoration is conditional
on acceptance. PR #13 was not made ready. No further push/dispatch is authorized
in this stopped round. The owner can set the paid budget back to$0.

**Not verified / PLAN-GAP / open question:** the console-readiness completion
path needs an integrator decision: observe safe physical command completion and
idle authority before bounded14j resync when asynchronous text covers the prompt.
The retained owner passed record alone is not treated as shell-idle proof. No
implementation fix is included in this STOP report. All later VM and physical/
followability gates stay NOT RELEASED. The image/runtime/owner code, workflows,
privacy policy and audits are unchanged from the dispatched head. No Gradle daemon.

| Run | Captured boot console | Line | Certificate label | SHA256 of whole line |
| --- | --- | --- | --- | --- |
| probe16 | `evidence/two-disk/live-ui-probe-boot-console.txt` | 491 | Fedora kernel signing key | `c790a61f331cc88d7291f060afbc18d539a99da32627a8b62c039d85c80d5014` |
| probe16 | `evidence/two-disk/live-ui-probe-boot-console.txt` | 525 | Fedora kernel signing key | `c2a09f42d03c99aeed9a0e73391b0ae85a36cc5e5d5ee450086215fec3cbba2e` |
| qualification6 | `evidence/two-disk/offline-first-stock-boot-console.txt` | 505 | Build time autogenerated kernel key | `30101d1bb46a78c44670551bfd66f39db545a219da5884161e29590d0a4225f2` |
| qualification6 | `evidence/two-disk/offline-first-stock-boot-console.txt` | 527 | Build time autogenerated kernel key | `1275e799139f224813274f0661692b121765e1ef7a1bf22921e62d0281772adc` |
| qualification6 | `evidence/two-disk/protected-second-install-boot-console.txt` | 491 | Fedora kernel signing key | `c600d756814c95666e43d3d5a22d5557effed7f328dff3c2bb0b5abbe6608f6c` |
| qualification6 | `evidence/two-disk/protected-second-install-boot-console.txt` | 524 | Fedora kernel signing key | `75fa386fe26a2096466493a796009a042cc4390fb483201fdb5d3158a1a3390c` |
| qualification6 | `evidence/two-disk/stock-initialization-0-boot-console.txt` | 498 | Build time autogenerated kernel key | `ff8afb774751dce47884ad06017433c7facfe4a067e50fddebaa7add87d672c9` |
| qualification6 | `evidence/two-disk/stock-initialization-0-boot-console.txt` | 520 | Build time autogenerated kernel key | `3217577ebbb1565e55bc2cb1f459fb1fa08122bccb38d5e9b3b784230021a1a1` |
| qualification6 | `evidence/two-disk/tools-stock-boot-console.txt` | 511 | Build time autogenerated kernel key | `2e6d202d44723073a42f74a17e21c9099277ca2cddb6583ef8397f3e3e63c0f2` |
| qualification6 | `evidence/two-disk/tools-stock-boot-console.txt` | 529 | Build time autogenerated kernel key | `728a5d125d44a6295bd1332cc0ecffe9c71ffe192e76017029c9eaf6f3f00e75` |

## 14zg — Verified relay chain, max3 sudo hops

**Done:** the ancestry check now validates outside-in from the physical tty
selected by the same cgroup/logind/Audit session. A controlling-tty transition
is accepted only from a verified `/usr/bin/sudo` frontend to its direct sudo
monitor child, which must own a new pts/session. Each subsequent process stays
on that controlling tty/session until another verified sudo transition. A pts
already seen above its sudo is refused; at most3 transitions are allowed.
The innermost controlling tty must match this tool's stdin. Direct physical
stdin also requires the tool itself to control that physical tty.
Unknown processes, tmux/screen/script/ssh/emulators, uncreated/reused pts,
missing monitors, broken/changing/cyclic chains and four hops refuse with the
existing physical-login message. The original loginuid1000, unique cgroup and
logind session, Id/Scope/Audit/TTY cross-check, five login-service facts, start
time, boot ID and post-observation scope/audit consistency checks are retained.
No environment hint or argv is trusted to establish physical identity.

**Guide/CI equality:** a test runs the actual `Console.become_root` method and
checks `sudo -k; sudo -i` followed by the exact commands.json owner command shape.
The complete host walk still types every command shown by INSTALL. The approved
root-shell plus nested owner-command route uses2 verified hops and passes the
modelled helper; tty4's direct sudo proof uses1 hop. No guide/command route change.
The16 session tests include direct tty3/tty4, one/two/three hops, four-hop refusal,
unknown/reused pts, non-sudo transitions, terminal-owning programs at every hop,
graphical/remote sessions, all original facts and the real unprivileged pts
stdin reproduction with explicitly modelled guest proc/logind metadata. Every
refusal records0 host mutations. The20 session/parser targets pass.

**Verified locally:** the complete host walk passed232 tests in208.581s. The
whole suite ran451 tests in391.844s:443 distinct passes and8 known native host
limitations (2 failures/9 errors), exactly named in `14zg-preflight/whole-suite.txt`.
Those privileged host/DrvFS constraints remain mandatory in native CI; no test,
assertion or skip was weakened. Actual release/git/file replay and53 offline
source checks pass; four CI-token-only registry checks remain deferred with
their14f reasons and fail-closed CI steps. The ISO replay passed first attempt:
9,068,650,496 bytes, exact pinned/fresh official checksum,4 localization and102
WebUI sources. No local Windows retry or inspector behavior change was needed.
Strict checks pass283 guest/serial/staging scripts,258 embedded Python,12 shells,
46 Python sources and the native workflow body. Windows copy tests pass15
zero-write destination refusals and exact payload equality. Four local dispatch
controller and7 fixed-watcher regressions pass. No Gradle daemon started.

**Payload / For package15:** current generated bundle/INSTALL fingerprint is
`683b1cff54d8a80406a70afd3f1173343a8a3fc95d301ef8cdbf05ab39010974`.
Package15 must take that fingerprint after qualification. Historical receipts
retain the fingerprint actually tested at their recorded time. Frozen image,
release/config/policy, workflows, privacy rules and all disk/NVRAM/BootNext
rules are unchanged. INSTALL/EMERGENCY and the physical/followability release
gates remain true; no real laptop, image build or publication is involved.

**Privacy/local closing checks:** pinned gitleaks8.21.2 full history and36 pending files returned0 findings; final manifest/session validation passed17 tests. No ignore/rule/workflow changes.

**Dispatch plan / budget:** one normal fast-forward push, then fresh exact-head
privacy with all3 steps actually executed, complete ledger and read-only billing/
$6 budget (prevent true; net Actions spend deducted), probe16, then only after
probe/native/artifact acceptance a fresh guard and qualification6 on that same
head. The pre-push snapshot is727 consumed +238 bound /1100, complete99/99 history,
probes15/16 and owner-tools5/6; org after that bound320 minutes. Reserve0/closing0
remain until acceptance. Both run attempts are single dispatches, with the fixed
returned-URL watcher and no POST retry. Any CI stop requires diagnostics/report
and no rerun; no extra push before qualification finishes. Final reserve150/
closing12 restoration, closing privacy and PR-ready require actual acceptance.

**Not verified / open questions / JUDGMENT-CALL:** actual fresh native/probe/VM
results are pending. The integrator explicitly approved nested relays; the
implementation adds no broader terminal acceptance. No ready/laptop release
claim is made before the prescribed gates.

## 14zf — Physical recovery session through sudo, with the nested-route contradiction retained

**Done:** `Tools.session()` derives exactly one logind session from
`/proc/self/cgroup`, matches the same recovery session/tty3 or tty4 in
`loginctl list-sessions`, and cross-checks Id/Scope/TTY/Audit against
`/proc/self/sessionid`. Missing/unset/inconsistent audit facts refuse. The exact
original loginuid1000 and Service=login, Type=tty, Remote=no, Name=ares-recovery,
User=1000 checks remain, together with start time and boot ID. Scope/audit are
rechecked after ancestry validation. Direct physical stdin passes. A pts passes
only through a stable chain of the permitted interpreters and sudo, on one pts
owned by sudo's monitor, ending at sudo on that physical tty. Unknown programs,
terminal emulators, sshd, tmux/screen, cycles, broken/changed identities and
session/tty mismatches refuse. No environment hint is trusted.
The pinned PAM login file requires pam_loginuid before pam_systemd. Pinned
systemd259.9 exports Audit as the kernel audit session ID. Pinned sudo1.9.17
sets use_pty unconditionally from its enabled default and allocates a fresh pts
when /dev/tty is available, including another invocation from a root shell.
The shell profile audit found no sudo wrapper disabling that behavior.

**PLAN-GAP:** the guide and `owner_vm.Console.become_root()` enter `sudo -i`.
The exact owner command then begins with another sudo, for example
`sudo /var/lib/ares/at layout begin us`. The resulting model is physical tty3
→ sudo → monitor/pts2 → root Bash → sudo → monitor/pts3 → owner Python.
The outer sudo controls tty3 but the processes between it and Python cross two
pts; the inner sudo controls pts2 rather than tty3. The literal requirement
“Every process between sudo and this one must sit on that same pts” therefore
refuses the required route. The actual new helper reproduces that refusal with
`Use a physical tty3/tty4 recovery login` and0 mutations. A direct fresh tty4
worker through one sudo relay separately passes. These PIDs are explicitly
modelled from pinned source; they are not claimed as captured guest PIDs.
[Exact model and proof](../../os/manifest/ci/14/14zf-preflight/nested-route.json).

**Decision needed:** either authorize individually verified sudo-owned pts
relays ending at the same physical logind session, or change the owner/CI route
so it does not nest sudo. No recursive extension, command/guide-route change,
audit relaxation or paid run was made. The clarification is unresolved. The
inherited brief14 instruction to stop on anything the rules do not cover applies.
No push was made because that would spend privacy minutes before this gate is
resolved. Probe16 and qualification6 remain unused.

**Verified:**12 model/real-PTY session tests pass, including every listed refusal,
all original fact checks, qualification5's explicitly modelled sudo/monitor/Bash
shape, and real local pts stdin with modelled logind/proc metadata. The real
interpreter symlink/comm distinction (`python3` vs `python3.x`) is covered.
All refusals make0 host mutations. The20 session/parser/equality targets pass.
The complete host walk passed228 tests in186.080s, with warning-free Bash parsing
at every composed guest boundary. This walk uses stand-in guest responses and
does not establish that the nested real owner route is accepted.

The full local suite ran447 tests in327.862s:439 distinct passes and the8 known
native host limitations, reported as2 failures/9 errors. The full exact output
and failed names are retained in `14zf-preflight/whole-suite.txt`; no skip or
assertion was weakened. The ISO replay passed on its first attempt, rehashing
all9,068,650,496 bytes against the pin and a fresh official checksum, with4
localization and102 WebUI sources. No Windows retry was used and Linux CI's
inspector is unchanged. Actual release/git/file and53 offline-source replay
checks pass; four CI-token-only registry checks remain deferred fail-closed in CI.
Strict checks pass for283 guest/serial/staged scripts,258 embedded Python,
12 shells,46 Python sources and the native workflow body. Windows copy testing
passes15 zero-write refusals and exact payload equality.

**Payload / For package15:** generated owner payload and current INSTALL
fingerprint are now
`110bd009c3a60aa74afccd97f3b8d08be91db1acb8028aa1b02c5df23fb9bbba`.
Only the owner implementation/its generated copy and manifest changed; frozen
release/runtime/config/policy, workflows, privacy rules and disk/NVRAM audits
are unchanged. Historical evidence retains the fingerprint actually observed
at that time. Package15 must pick up the current fingerprint after qualification;
all existing physical/followability and INSTALL/EMERGENCY release gates remain.

**Privacy:** pinned gitleaks8.21.2 returned0 findings over full history and33 pending files. Final manifest/payload/session validation passed14 tests. No ignore/rule/workflow changes.

**Budget:** complete99/99 history,727/1100 consumed, probes15/16 and owner-tools5/6.
The read-only$6 Actions budget still has prevent_further_usage=true; reported
net spend$2.652 at$0.006/minute leaves558 paid minutes (billing may lag). This
follow-up made0 pushes,0 dispatches and0 reruns. Reserve0 and closing0 remain
because acceptance is false; no budget or credential/scope change was made.
No Gradle daemon started.

**Not verified / open questions / JUDGMENT-CALL:** fresh privacy/native/probe16/
qualification6 were held behind the contradiction above. No ready-for-review or
laptop acceptance is claimed. The strict single-pts policy is retained until an
integrator decision; no wider ancestry acceptance is inferred from elapsed time.

## 14ze — Verify sudo PTY relay and preserve idle authority

**PLAN-GAP / stop:** the pinned image's verified `use_pty` behavior also affects
the unchanged owner payload. `Console.become_root()` enters `sudo -i`, putting
the root shell and its command stdin on a pts. Every layout action calls
`Tools.session()`, which requires `os.ttyname(0)` to be `/dev/tty3` or `/dev/tty4`.
Thus the first `layout begin us` on that root shell must refuse; the fresh
second-console `sudo ... layout proof` has the same default-PTY conflict.
The existing handler fixtures substitute a physical tty name and missed it.

**Zero-cost proof:** invoked the actual unmodified `Tools.session()` on a real
unprivileged local PTY. `stdin.isatty()` was true and its real name was a pts;
it returned exactly `Use a physical tty3/tty4 recovery login`. There were
**0 host calls and0 mutations**. No sudo was run for the proof, no UID/terminal
setting was changed, and no fake tty name or replacement guard was used.
[Proof and exact source](../../os/manifest/ci/14/14ze-preflight/pts-session-refusal.json).
The requested observer fix is implemented and locally tested. The later owner
session conflict is a separate guard that this brief does not authorize bypassing.
The inherited brief14 rule says “stop on anything the rules don't cover.”
No owner script, bundle, guide, frozen runtime or image was changed to bypass it.
An integrator decision must resolve physical-session identity through sudo's
PTY while retaining the real recovery-login and second-console checks before
spending minutes on the planned qualification. Probe16 and qualification6 remain
unused; **0 pushes,0 Actions dispatches,0 reruns** this turn.


**Done:** read-only unsquashfs/RPM-header inspection found sudo1.9.17-10.p2.fc44.
The pinned sudoers manual and matching1.9.17p2 `init_defaults` source enable
`use_pty`; `/etc/sudoers` and `sudo.conf` have no override; `sudoers.d` is empty.
No image executable or privileged host sudo operation was run.
The observer accepts only exact `sudo -i`, one sudo monitor and one interactive
Bash on its pts, with matching session/pgrp/tpgid and no child work. Unknown,
multiple, broken, changing and busy trees refuse. The plain Bash case is kept.
Refusals export PID/comm/group links; argv is limited to exact public Bash/sudo
forms and otherwise fully redacted. Ten physical type call sites and every
commands.json command were reviewed: passwords/token are hidden stdin, never
shell argv. Account-login and sudo readiness/serial records now have separate
names. Prompt predicate, three samples, maximum two idle-only Enters, raw VCSA
retention, checksum framing and840/900-second deadlines are unchanged.

**Verified locally:**13 observer tests;216-test complete host walk;435 whole-suite
tests attempted,427 distinct passes and8 previously documented native host
limitations (privileged host utilities unavailable, DrvFS0600 and WSL runtime).
The exact failed names and all output are retained in `14ze-preflight/whole-suite.txt`.
A preliminary suite overlapped edits and is not acceptance evidence; the final
suite ran with frozen sources. A direct Windows console run hit the existing
Bash newline/platform limitation; the same12 console tests passed in WSL.
The19 real Bash/PTY staging tests passed, including exact hidden-login sequencing.
The actual ISO replay passed first attempt:9,068,650,496 bytes, exact pin/fresh
official checksum,4 localization and102 WebUI sources. No Windows retry used.
Actual release verifier and53 offline/file-source steps passed; strict guest,
serial, staging, embedded Python and native workflow syntax checks passed.
Four local dispatch-controller and7 fixed-watcher regressions passed.
Final manifest-order and observer validation passed14 tests after the STOP packet was written. Real
Windows-copy tests passed15 zero-write refusals and exact bundle equality.
Pinned gitleaks8.21.2 full history and39 pending files both returned0 findings. No ignore, rule or privacy workflow change.
Full native suite and four private registry checks remain fail-closed in CI.

**Evidence limits / JUDGMENT-CALL:** qualification5 captured a root-style prompt,
`ready=false`, echo off and successful framed completion; its PIDs were not
retained. The new regression combines those exact observations with an explicitly
modelled tree derived from the verified sudo source; it does not invent a captured
process tree. All non-public argv are redacted rather than relying on a secret
pattern. No owner script, bundle fingerprint, frozen image/runtime, release,
audit, privacy rule or workflow was changed. No Gradle daemon started.

**Closed ledger:**727/1100 minutes, probes15/16 and owner-tools5/6; complete99/99 run history. The read-only$6 Actions budget still has prevention true; reported net spend$2.652 at$0.006/minute leaves558 paid minutes (billing may lag). No Actions cost was incurred this turn. October reserve0/closing0 remain because acceptance is false.

**Budget / unexecuted dispatch plan:** existing1100-minute cap, probes16, owner-tools6,
$6 Actions budget with prevention true and net spend deducted. October reserve0
and closing0 stay pending actual acceptance. The authorized paid sequence is held behind the PLAN-GAP: one push, fresh
exact-head privacy and a guard, probe16, then a fresh guard and qualification6
on the same head only after probe acceptance. No automatic continuation.
Any future CI STOP requires diagnostics/report and no rerun.

**Not verified / open questions:** no fresh exact-head privacy or VM run was started. The owner-session PLAN-GAP above blocks the planned dispatch. The
physical laptop/followability gates and all prior release gates still apply.
No acceptance or ready-for-review claim before qualification and closing checks.

## 14zd — Local retry clarification completed; probe15 passed; qualification5 STOP

**Done locally:** the owner clarified that no-rerun covers paid Actions, not
zero-cost local checks. With no matching old replay process, a fresh checkpoint
directory and exclusive local replay lock, the actual unchanged inspector
passed on its first attempt. A separate fresh replay before qualification also
passed on its first attempt. Each read all9,068,650,496 retained ISO bytes,
matched the pin and a fresh official HTTPS checksum, and extracted4 localization
and102 WebUI sources. The wrapper allowed3 retries with10/20/30-second waits;
none were used. There was no checkpoint reader or overlapping cleanup/replay.
The old Windows denial did not recur; its holder remains unidentified. No
Defender/ACL/settings or Linux `installer_inspect.py` change was made.

Actual read-only release/git/file verification,53 offline-source checks, strict
283 guest/serial scripts and all staging controls,258 embedded Python,12 shells,
46 Python files/native workflow body passed before each dispatch. Windows copy
tests passed15 zero-write refusals and exact bundle equality before each.
Four stubbed controller and7 fixed-watcher tests passed. The unchanged-code
422-test local whole-suite result retained its8 documented host limitations;
the203-test host walk passed. Both hosted runs resolved those limits: all422
tests passed,0 skips, in46.799s (probe) and43.872s (qualification). The native
loop proof passed20 checks,0 helper mutations, protected fixture unchanged and
complete unmount/detach. No local privileged operation or software installation.
Gradle/client tests were not run; no Gradle daemon started.

**Push / authorization:** pinned gitleaks8.21.2 full history and pending files
were0 before the single normal push from `2fb695c` to `e3751ad`. Both exact-head
push/PR privacy runs passed all3 steps, with personal terms actually executed.
The complete ledger and read-only billing/budget were refreshed immediately
before each dispatch. Both required the exact$6 Actions budget, prevention true,
API price and subtraction of reported net spend. The fixed watcher confirmed
the canonical returned run URLs in2 direct GETs for probe and
2 for qualification; no list fallback or repeat POST.
The4 CI-only private package/manifest/signature/layer checks passed in both
hosted runs, without owner secrets or scope changes.

**Probe15:** [40592552658](https://github.com/Ares-Empire/AresOS/actions/runs/40592552658)
completed success on `e3751ad`, protected-second only, with no install. All
retained probe flags passed. Independent replay found3 identical protected-disk
captures,4 zero write/unmap samples,3 raw varstores/exact BootNext replays,
2 NVRAM rule replays and2 full-variable delta recomputations. All23 retained
large-command transfer receipts showed guest SHA256 and warning-free syntax
verification before execution. The new transport therefore ran in the real VM.

**Qualification5 STOP:** [40596167369](https://github.com/Ares-Empire/AresOS/actions/runs/40596167369)
completed failure in the VM step. Offline installation passed, stock completed
its permitted hardware-setup reboot, and offline first boot reported no staged
or queued deployment, network down and no tools attached. The unattended and
detached Windows round trips passed. On the next Linux boot, recovery account
login returned to a shell. The harness then typed the sudo sequence and password.
At `Console.become_root -> after_hidden('tools-stock')`, the physical observer
waited840 seconds and returned `ready=false`, `echo_enabled=false`,
`foreground_shell=false`. The saved cursor line has a root-style prompt.

This was **not** a missing serial completion: the public script was staged,
SHA256/syntax verified, returned valid checksum-framed JSON, and completed with
`ARESOS_CMD_DONE:0`. The subsequent assertion was
`Hidden owner command did not return to an idle shell`. The840/900-second
deadlines behaved as designed. A displayed prompt does not establish root UID
or the actual foreground process; its PID/cmdline was deliberately not exported,
so a sudo/PTY/proxy explanation remains unproved here. No prompt predicate,
console log level, idle authority or Enter limit was loosened after the STOP.

The earlier `tools-stock-hidden-completed.json` belongs to the **account login**,
not the failed sudo completion. Account/sudo observations share a stage prefix
and can overwrite the same readiness filenames. The exported summary labels
that limitation; no separate root-completion receipt is inferred from it.

The tools stick had not been attached, and no owner `install`/`prepare` or later
tool command ran in qualification5. No guest registry token was typed. Network
invariance after prepare, owner login/verify/switch, AresOS/layout failure-revert/
success/back, rollback/keep-stock/final pair remain unverified for this head.
The guest failure counter was recorded with the VM paused. Independent raw
replay passed7 protected captures,8 zero write/unmap samples,7 raw varstores/
exact BootNext checks,6 NVRAM rule replays and6 complete-variable deltas.
No firmware, BootNext, protected-disk or detached-device audit was widened.

**Privacy / exported diagnostics:** probe artifact12775123822 matched SHA256,
4,743,226 bytes/354 members; qualification artifact12779038742 matched SHA256,
5,470,322 bytes/458 members. Native and failure logs scanned0 before reading.
Probe findings509 =507 ISO-listing +2 whole-line kernel X.509 messages;
qualification515 =507 +8. **Zero unclassified findings**, no ignore/rule/privacy
workflow change. Each kernel match is recorded by path/line/hash in privacy.json
and below. Raw consoles, raw VCSA and private diagnostics remain in the ignored
private artifacts, not committed. The committed diagnostic summary binds their
exact bytes and records booleans/geometry without credential or screen text.

| Run | Captured boot console | Line | Public certificate label |
|---|---|---:|---|
|probe15|live-ui-probe-boot-console.txt|495|Fedora kernel signing key|
|probe15|live-ui-probe-boot-console.txt|527|Fedora kernel signing key|
|qualification5|offline-first-stock-boot-console.txt|503|Build time autogenerated kernel key|
|qualification5|offline-first-stock-boot-console.txt|514|Build time autogenerated kernel key|
|qualification5|protected-second-install-boot-console.txt|496|Fedora kernel signing key|
|qualification5|protected-second-install-boot-console.txt|529|Fedora kernel signing key|
|qualification5|stock-initialization-0-boot-console.txt|504|Build time autogenerated kernel key|
|qualification5|stock-initialization-0-boot-console.txt|524|Build time autogenerated kernel key|
|qualification5|tools-stock-boot-console.txt|503|Build time autogenerated kernel key|
|qualification5|tools-stock-boot-console.txt|513|Build time autogenerated kernel key|

Evidence: [probe review](../../os/manifest/ci/14/14zd-probe/),
[qualification STOP and diagnostic bindings](../../os/manifest/ci/14/14zd-qualification-stop/),
[owner-stop observations](../../os/manifest/ci/14/14zd-qualification-stop/owner-stop-observations.json),
[closed ledger](../../os/manifest/ci/14/14zd-qualification-stop/ledger.json).
Two completed ordinary duplicate ISO caches were hash/size verified and removed
after all local replays finished; original ISO, extracted sources, partial14zc
cache, logs and receipts preserved. The reclaim manifest is retained.

| Closed package ledger | Value |
|---|---:|
| Consumed / cap | 727 /1100 |
| Active reservation | 0 |
| Probes / cap | 15 /16 |
| Qualifications / cap | 5 /6 |
| Complete history | 99 /99 |
| This round pushes / dispatches / CI reruns | 1 /2 /0 |
| Image / publication attempts | 0 /0 |

Read-only billing at2026-10-27T23:34:32.970313+00:00: exact$6 budget, prevention true,
reported net Actions$2.652,
price$0.006/minute,0 included minutes left and
558 paid minutes available (billing can lag). No budget
mutation. Closing0/reserve0 were not restored because acceptance is unmet.
No further push or dispatch is planned in this round; the owner can set the
budget back to$0. Pinned local history/pending scans are0 before the local STOP
commit; `git diff --check` passes. The remote remains at the tested head.

**Not verified:** complete package14 acceptance, the stopped sudo-idle gate,
every later owner/VM stage on this head and physical laptop followability.
INSTALL, EMERGENCY and the release gate remain NOT RELEASED. Package13, owner
payload/fingerprint, all frozen runtime/release paths, workflow, harness and
audit source are unchanged after dispatch. Existing **For package15** lists
below remain applicable. No real laptop disk, boot state or settings were touched.

**JUDGMENT-CALL:** none after the explicit14zd local retry clarification.
**PLAN-GAP:** the new physical-idle observer rejected a root-style display after
sudo; raw foreground identity was not exported and some readiness names share
the account/sudo prefix. **Open questions:** the actual foreground process/PTY
at that moment and the correct verified completion proof. No implementation
change or further allowance is inferred; no CI rerun was attempted.

## 14zc — $6 guard updated; Windows replay STOP

**Done:** package14 alone now has cap1100, probe16 and owner-tools6. October
reserve0 and closing0 are unchanged. The guard requires an exact $6 organization
Actions budget with prevention true, subtracts all reported net Actions spend
and floors the remainder at the API's runner price. Regression boundaries now
accept the six-dollar decision, reject other amounts/prevention changes, refuse
probe17 / qualification7, and preserve the package13/11 settings exactly.
No owner tool, image, frozen release, credential, scope or workflow change.

The unchanged fixed watcher passed7 local tests. The prepared local controller
passed4 tests with every external boundary stubbed, including delayed direct
identity confirmation, one POST per mode, existing-attempt refusal, stale/wrong
budget refusal and forbidden-mode refusal. No real POST was sent.

**STOP / exported diagnostics:** the actual unchanged `installer_inspect.main`
replay failed at `installer_inspect.py:137 -> checkpoint():86 -> Path.replace`:
`PermissionError [WinError 5] Zugriff verweigert`, replacing
`iso-download.json.tmp` with `iso-download.json` in the local evidence directory.
It had read **3,422,552,064 of9,068,650,496 bytes** from the retained original ISO
through the existing file-response adapter, in one simulated HTTP200 response.
The fresh official HTTPS checksum equals the exact pin. The partial digest is
not a complete-image verification or an unexplained image difference. Full
verification and source extraction were not reached in this replay.

The inspector's own final checkpoint saved `status=stopped`,
`error_type=PermissionError`, the partial digest/count and attempt details. No
second replay attempt, resume, Windows ACL/antivirus/setting change, native
installer change or substitute success flag was made. The underlying cause of
Windows denying this particular replace is unproved; this does not establish
that Linux CI's atomic rename fails. The14e rule requires all non-CI-only replay
steps to pass, and14zc says any stop is reported with no rerun. Therefore the
single pre-dispatch push authorization was not used, and no probe was sent.

Evidence: [diagnosis and traceback locations](../../os/manifest/ci/14/14zc-local-stop/diagnosis.json),
[inspector's STOP record](../../os/manifest/ci/14/14zc-local-stop/iso-download.json),
[verification/source bindings](../../os/manifest/ci/14/14zc-local-stop/verification.json),
[fresh complete ledger and billing](../../os/manifest/ci/14/14zc-local-stop/ledger.json).
The partial ISO remains ignored/private. Only metadata, public checksum and
source/log provenance are committed; no credential or raw boot console.

To make room, four old ordinary duplicate ISO caches were individually
validated for exact size and pinned SHA256, then unlinked only inside this
worktree. I started replay while reclamation was finishing, so these briefly
overlapped; the inspector's own25GiB free-space check passed. No deleted cache
was the original ISO or a current replay path. The original and all extracted
evidence are preserved. Reclamation recorded54,753,402,880 free bytes at its
completion, not before replay. Whether the overlap contributed to the rename
denial is unproved. The hash-before-path reclaim manifest is retained.
No other worktree or real laptop disk/boot state touched.

**Verified / already-running checks collected after STOP:**

- `python3 -m unittest discover -s os/tests -v`:422 tests in431.353s,
  **414 distinct passes**,2 failures/9 errors from exactly the same eight
  native-only host limits,0 skips. Three need unavailable Pillow, four encounter
  the explicit no-privilege sudo refusal shim, one cannot prove0600 on DrvFS.
  Exact IDs and all output are retained; no test weakened and no package or
  privileged operation installed/executed locally. No green native-suite claim.
- `python3 -B reviews/14-owner-tools/walk-host.py`:203 passed in210.310s,
  no stick across reboot, no VM started. Updated source bindings are committed.
- Strict first replay:283 composed guest/old-serial wrappers, all large-script
  staging controls,258 embedded Python,12 shell files,46 Python files and the
  native workflow shell pass; parse stderr/warnings remain refusals.
- Actual read-only `verify_release.py 40154642447` and all53 retained offline
  source checks passed. The14f package/registry/digest/pull/signature checks stay
  CI-only and fail-closed. They were not run or represented as local successes.
- Pinned gitleaks8.21.2 full history and pending files:0 before local commit;
  `git diff --check` passes. No ignore/rule/privacy-workflow change. Log viewers
  use LF and replace absolute workspace paths with `<WORKTREE>`; original log
  hashes are recorded. Gradle/client tests were not run for this OS guard-only
  follow-up; no Gradle daemon started.

**Closed budget:** fresh read-only95/95 history,647/1100 minutes consumed,
reservation0; probes14/16, qualifications4/6. Actual Actions budget is$6 with
prevention true; net spend$1.638, API price$0.006/minute, included minutes left0,
**727 paid minutes available** at the recorded billing time (billing can lag).
No budget mutation. This round had0 pushes,0 dispatches,0 reruns,0 image or
publication attempts. No exact-new-head hosted privacy or VM result is claimed.

**Not verified:** the failed ISO replay and native/VM qualification of14zb;
registry login outcome and later package14 verify/switch/AresOS/layout/rollback/
keep-stock acceptance remain unproved. INSTALL, EMERGENCY and the release gate
stay NOT RELEASED. Firmware/BootNext/protected-disk audits, all frozen runtime
and release paths, owner payload/fingerprint and package13 remain unchanged.
Acceptance is unmet, so closing12/reserve150 restoration and PR-ready transition
were not performed. No further Actions work is running or planned in this round;
the owner can set the budget back to$0.

**JUDGMENT-CALL:** no new product/owner choice. **PLAN-GAP:** the actual Linux
inspector's checkpoint replay on Windows encountered an OS-level rename denial;
no assertion was bypassed to proceed. **Open questions:** what held/denied that
local checkpoint replacement and what replay adaptation the integrator permits.


## 14zb — Bounded command staging and hidden-input resynchronization

**Done / diagnosis:** the exact historical login reader is retained as a public,
hash-bound fixture: 2,652 source bytes, 3,633 transmitted bytes, maximum 1,024
per line. The 116 captured output bytes contain five continuation prompts, no
completion and no echoed received command body. Received UART input and the
login diagnostic record were not retained, so the exact failed guest state
cannot be reconstructed from this artifact.

Real local Bash/PTY execution establishes the following:

- The exact old script passes strict `bash -n` and returns its checksum-framed
  record when the record exists. No intrinsic quote/brace/heredoc defect was
  reproduced in these exact bytes.
- A fully received, unchanged old command reaches its diagnostic reader and
  emits **five** continuation prompts while waiting for an absent new record.
  Removing the heredoc terminator also reproduces continuation prompts. Thus
  the retained prompts alone do not prove that the guest was still parsing.
- A sender limited to 512 bytes per burst breaks the old unacknowledged send;
  the new acknowledged transfer completes. This proves a possible loss mode,
  without claiming that such loss occurred in qualification 4. The exact
  1,024-byte lines also work in the PTY. Linux documents a 4,096-character
  canonical line buffer, but the failed guest's termios/input state was not
  retained; no specific guest buffer-limit explanation is established.
  [Primary N_TTY documentation](https://www.kernel.org/doc/html/v6.1/driver-api/tty/n_tty.html).
- A real `getpass` blocked on the independent physical PTY cannot consume the
  serial command: the serial framed export completes before hidden input is
  supplied. This matches the harness's tty3/ttyS0 separation. A wrong guest
  routing configuration was not observed or proved.
- Idle interactive Bash/readline can itself have ECHO disabled. The old
  ECHO-only check could therefore declare hidden readiness at an idle prompt.
  This readiness defect is reproduced locally; its occurrence in the failed
  VM is unproved. The old 1,800-second reader exceeding its 900-second caller
  is a separate confirmed deadline defect.

**Transport:** `serial_transport.py` stages public scripts over 256 bytes under
`/run/ares-serial-<nonce>`. It requires uid0 and tmpfs before allocation, creates
a 0700 directory / 0600 file, sends 96-byte source chunks using control lines
of at most 512 bytes, and waits for a nonce/index/status ACK after every line.
Guest SHA-256, ownership/mode checks and warning-free `bash -n` must pass before
execution. The checksum-framed JSON protocol and tiny-command behavior remain.
Every missing ACK stops within 10 seconds, with no retransmission, execution or
speculative cleanup into a potentially busy shell. An acknowledged refusal
cleans only its owned temporary files/directory; normal execution cleans them
and reports the real exit code. Transfer is bounded separately at 120 seconds.
Evidence stores sizes, digest, step/status and deadlines, without script bytes.

Known secret-bearing scripts and NUL input refuse before hashing, evidence,
allocation or sending. The legacy inline registry-auth writer now refuses;
package14 continues to use the existing physically typed hidden prompt only.
Synthetic hidden input is absent from all staged UART packets and all saved
test evidence. No real credential was read, typed, recovered or copied locally.
Owner scripts, bundle/fingerprint, frozen release, image and publication paths
are unchanged.

**Hidden input / deadlines:** after account, sudo and owner-command hidden input,
the UART's completed-command epoch permits a bounded output drain and short
acknowledged input flush. No raw drained output is saved. The independent
physical observer reads only termios and foreground-process identity; command
line bytes remain guest memory and are never returned. Hidden readiness
requires ECHO off and a foreground program other than an idle interactive Bash.
After hidden input, return of that interactive shell plus an unchanged physical
input epoch grants the original strict cursor wait: three stable samples,
at most two recorded physical Enters, no Enter to an unknown/busy shell and raw
VCSA retained on readiness timeout. Wrong-password rejection drains serial but
never grants shell/Enter authority. No console logging suppression or predicate
relaxation. UART drain/ACK, physical completion and permitted Enter events are
recorded separately.

Both owner-result polling and post-hidden completion use **840 seconds within
900 seconds of execution**, leaving 60 seconds for framing/return. The separate
120-second transfer bound precedes execution; this is not a claim that the
whole multi-step login finishes in 900 seconds. No job/VM/Actions limits changed.

**Verified locally:**

- `python3 -B -m unittest discover -s os/tests -p test_serial_staging.py -v`:
  19 passed in 51.805s. Exact full login sequence on a limited line completes;
  lost result chunk stops without retry; original script, missing delimiter,
  no-record deadline, separate hidden PTY, foreground readiness, root/tmpfs/
  private-mode refusal, NUL/secret rejection, chunk loss, SHA mismatch,
  syntax-warning refusal, nonzero exit and unchanged framed checksum covered.
- `python3 -B -m unittest discover -s os/tests -p test_owner_console.py -v`:
  12 passed in 1.568s, including the retained14i clutter, busy/no Enter,
  two-resync cap, raw timeout retention and revoked completion authority.
- `python3 -B reviews/14-owner-tools/walk-host.py`: 203 passed in 212.202s;
  full host control flow passes, no stick across reboot, no VM started.
  Updated source bindings and 283 composed commands are committed.
- Strict composed-command replay: 283 guest bodies and old serial wrappers,
  every large body's staging controls, 258 embedded Python programs, 12 shell
  files, 46 Python files and the native workflow shell pass; any parse stderr,
  including warnings, refuses. All staged bodies are also checked guest-side.
- Whole OS suite: **422 tests, 414 distinct passes; 2 failures / 9 errors from
  exactly the same eight native host limits**, no skips. Full output and exact
  IDs/reasons are retained: Pillow unavailable (3), the local no-privilege sudo
  shim refuses Homebrew/sysusers operations (4), DrvFS cannot prove auth0600 (1).
  No packages installed, sudo operation performed or test weakened. This is
  explicitly not a green native-suite or VM claim. Gradle/client tests were not
  run for this OS harness-only change; no Gradle daemon started.
  The initial422-test run had one extra error: a keyword timeout in the new
  wrapper broke an existing positional wait stand-in. The wrapper now preserves
  the positional call contract; the original partial-output/redaction regression
  passes unchanged, and the final whole-suite run has only the eight host limits.
- Actual read-only `verify_release.py 40154642447` and the 53 offline/source
  checks passed. The14f registry/package credential steps remain CI-only and
  fail-closed, without new credentials/scopes. No new ISO inspection or hosted
  credential check is claimed. `git diff --check` passes. Pinned gitleaks8.21.2
  full history and pending files: 0 findings before the local commit.

**Later stages:** the refreshed full walk covers verify, switch, AresOS boot,
layout proof/revert/change-back, rollback and keep-stock through the same staged
transport; every composed command is parsed strictly. Real package11n signature
proof and package13 rpm-ostree/bootc/BLS/keyboard/map JSON traverse the actual
PTY/checksum transport unchanged. Existing owner parsers/preflights are executed
against those retained observations and real package14 install/prepare/network/
title outputs. Keep-stock uses retained rollback input; no nonexistent package14
keep-stock or other later-stage PASS record is invented. These tests prove
local parser/control/transport behavior, not a completed package14 VM route.

Evidence: [analysis and source bindings](../../os/manifest/ci/14/14zb-login-transport/analysis.json),
[verification and full logs](../../os/manifest/ci/14/14zb-login-transport/verification.json),
[normal-reader observation](../../os/manifest/ci/14/14zb-login-transport/observations.json).
Local root/tmpfs/private-mode stand-ins are explicit: the tests execute real
Bash, PTYs, termios, SHA-256 and framing on ordinary files inside this worktree;
they do not prove guest ownership or filesystem behavior on a fresh VM.
Tracked log viewers use LF and replace absolute workspace paths with
`<WORKTREE>`; original private log-byte hashes are retained separately.

**Not verified / budget / stop:** no new Actions use, push or dispatch. The last
closed ledger remains **647/800 minutes, probes14/14, qualifications4/4,
reservation0**, with reserve0/closing0 unchanged because acceptance is unmet.
No fresh billing snapshot or budget mutation was needed for this local-only
work. PR #13 remains draft; INSTALL, EMERGENCY and the release gate stay NOT
RELEASED. Firmware/protected-disk/BootNext audits, owner payload, all release
and frozen runtime paths, workflow permissions/privacy rules and package13
settings are unchanged. No real-laptop operation.

**JUDGMENT-CALL:** bounded transfer thresholds and independent transfer/execution
deadlines are harness implementation choices; no owner/product decision changed.
**PLAN-GAP:** received UART input and the login result are absent from the old
artifact, so definitive attribution is unavailable. **Open questions:** the
original login outcome and actual guest loss/readiness state; native/root-tmpfs
behavior and a complete VM qualification remain for a separately authorized run.


## 14za — Watcher fixed; qualification 4 login-result timeout

**Done / watcher diagnosis:** stable filtering and paging were ruled out: the
old predicate matches the retained/current probe, complete history 94/94 included
it, and direct metadata verified the integrator's exact identity. The defect was
requiring the input-specific display title from a newly created list row within
four reads/sleeps (8s plus request time), while ignoring the canonical run URL
already returned by the successful POST. Original per-read fields were not
saved, so their exact transient values cannot be recovered. Qualification 4
then reproduced the startup behavior directly: first GET had `OS image`, next
GET had `Two-disk rehearsal (owner-tools)` on the same ID/head/branch/attempt.
This confirms the asynchronous display-title assumption; no claim is made about
an unretained individual probe response.

The local watcher now parses exactly one canonical returned URL and performs at
most 6 direct identity GETs, with 1/2/4/8/16s metadata backoff and every observation
saved. Exact ID/head/branch/event/title/path/attempt must match. No list fallback,
ambiguous URL acceptance, auth-error multiplication or repeat POST. The complete
ledger pagination/total_count guard is unchanged. Seven watcher tests and two
fully stubbed controller tests passed before dispatch. A later test-isolation
fix made the controller tests repeatable after the real nonce exists and added
an explicit second-POST refusal: 3 controller tests passed. The exact original
2-test source/hash/log and the repeatable 3-test version are archived separately.
No executable watcher/controller change occurred after dispatch. Exact source/log bytes are in executed-sources.zip; Python/txt viewers use LF. The final file manifest was checked against committed Git bytes, including the tracked txt test logs.

Actual 14e/14f release/git/file/read-only gh replay, 53 retained offline-source/
full-listing checks, 258 guest/258 serial strict Bash parses, 233 embedded Python,
12 shells/45 Python/native workflow body all passed. The unchanged real inspector
rehashed all9,068,650,496 cached ISO bytes against pin and fresh official checksum,
with 4 localization/102 WebUI sources. Two hash-verified old duplicate ISO caches
were removed only inside this worktree to retain the existing 25GiB scratch
prerequisite; original ISO and all extracted evidence preserved. Four CI-only
credential checks remained fail-closed; no owner secret or extra scope used.
Pinned local gitleaks 8.21.2 full history 0 before dispatch. Exact pushed-head
push/PR privacy both freshly passed all 3 steps, including executed personal terms.

The fresh pre-dispatch guard showed 573+160/800, complete94/94 history, budget $3,
prevent true, net Actions$1.584 and 76 org minutes after reservation. One POST
created [qualification 4](https://github.com/Ares-Empire/AresOS/actions/runs/40566496658),
probe 40560134727, head `2fb695c`, attempt 1. Qualification charged 74 ledger minutes. Fixed watcher confirmed it in 2 direct
GETs; no push, duplicate POST, new probe or rerun. Source gate proved local HEAD's
extra commits changed only the reviewed STOP evidence/report and 14za brief;
all runtime/workflow/test/guide files matched the pushed qualified source.

**Verified hosted:** all 400 native tests in 32.354s, 0 skips, including all 8 local
host limits. Native loop 20 checks, 0 helper mutations, protected unchanged and
full cleanup. Host capabilities/private manifest/signature/exact layer pull and
credential cleanup passed. Hosted ISO pin/fresh official checksum/exact size
passed in one HTTP200 attempt. No publication/image attempt.

Actual owner `install` passed, validating the binary firmware fix on a fresh
installed VM. `prepare` passed; its rerun had 0 operational trace mutations.
Network came up after pause/pin: independent raw rpm-ostree, bootc and BLS JSON
before/after are equal. Records/title/export passed, tools were removed, and the
prepared unattended Windows roundtrip passed. Corrected stock booted; its title
and records passed. Recovery login/password sudo and the permitted Enter resyncs
were retained. The failure-path counter was recorded with the VM paused.

**STOP:** `console.run('login','private-owner-login',...)` reached the username
and hidden-input readiness checks. Its subsequent `capture_json` never received
`ARESOS_CMD_DONE` and raised TimeoutError at owner_vm.py:301 / switch_vm.py:230 /
two_disk_vm.py:193. No private-owner-login PASS or STOP diagnostic JSON was
exported. The saved 116-byte serial incomplete transcript has continuation prompts
and no completion. Read-only reconstruction is 2,652 framed bytes / 3,633 wire
bytes, maximum 1,024 per line; this does not establish a cause. The diagnostic
reader permits 1,800s while the outer command permits 900s. That mismatch is
recorded, not fixed; it does not establish the registry-login outcome. No token
or guest authentication file was read/recovered. Login outcome and credential
state remain unknown. No later verify/switch/AresOS/layout/rollback/keep-stock
claim is made. No runtime, harness or deadline was changed after the STOP.

**Audits / privacy:** all available independent raw checks passed: 9 protected
captures, 10 zero write/unmap samples, 9 raw varstores/exact BootNext replays,
8 NVRAM rule replays and 8 complete-variable delta recomputations. Windows-default,
protected-second, detached-device and firmware rules remain unchanged. Artifact
12767753092 SHA256 `fa66f7e99a2dd4961f9fb4e47bea3de5bf752c01ff35a709bd3c894e62188586` matched GitHub. Findings 517
= 507 reviewed ISO listing + 10 exact whole kernel X.509 lines; 0 unclassified.
Native and failure logs scanned 0 before reading. No ignore/rule/privacy-workflow
change. Each public certificate line is recorded below and with its line hash in
privacy.json; raw logs/consoles/diagnostics remain private and ignored.

| Captured boot console | Line | Public certificate name |
|---|---:|---|
|corrected-stock-boot-console.txt|506|Build time autogenerated kernel key|
|corrected-stock-boot-console.txt|520|Build time autogenerated kernel key|
|offline-first-stock-boot-console.txt|499|Build time autogenerated kernel key|
|offline-first-stock-boot-console.txt|518|Build time autogenerated kernel key|
|protected-second-install-boot-console.txt|491|Fedora kernel signing key|
|protected-second-install-boot-console.txt|524|Fedora kernel signing key|
|stock-initialization-0-boot-console.txt|500|Build time autogenerated kernel key|
|stock-initialization-0-boot-console.txt|522|Build time autogenerated kernel key|
|tools-stock-boot-console.txt|498|Build time autogenerated kernel key|
|tools-stock-boot-console.txt|509|Build time autogenerated kernel key|

Evidence: `os/manifest/ci/14/14za-qualification-stop/`. Local tools there are
archived provenance, not workflow inputs. Bundle stays `a6aff101a24af32229adcb92356fb2a79f0ec0d7227d19c050212346bb83ede3`. All frozen
runtime, owner payload, guides, harness, audits, workflow and privacy paths are
unchanged from `2fb695c`; package 13 unchanged. The watcher was local tooling only.

| Closed package ledger | Value |
|---|---:|
|Consumed / cap|647 /800|
|Active reservation|0|
|Probes / cap|14 /14|
|Qualifications / cap|4 /4|
|Complete history|95 /95|
|This follow-up pushes / dispatches / reruns|0 /1 /0|
|Image / publication attempts|0 /0|

Read-only billing at2026-10-27T20:25:39.733431+00:00: net Actions
$1.602, price$0.006/minute,
approved $3 budget with prevent_further_usage true, paid minutes
233 (billing can lag). No budget mutation.
Closing 0 / reserve 0 were not restored because acceptance was not met. This run is
over; the owner can set the budget back to $0. No further dispatch is planned.

**Not verified:** registry-login outcome, owner verify/switch, AresOS boot, layout
failure/revert/success/back, rollback guard/rollback/keep-stock/final pair, and
physical laptop/followability. Acceptance remains unmet. Guide/card/release gate
remain NOT RELEASED. **JUDGMENT-CALL:** none beyond the explicit owner decisions.
**PLAN-GAP:** no new product decision inferred; the observed blocker is the
login-result timeout. **Open questions:** its underlying cause and login outcome
are unproved; no fix or additional allowance is inferred.

## 14z — Passing probe; dispatch-confirmation STOP

**STOP / agent bookkeeping failure:** the local dispatch wrapper received a
successful POST response with the canonical URL for [probe 14](https://github.com/Ares-Empire/AresOS/actions/runs/40560134727).
Its four bounded history-list reads did not find a matching candidate and raised
`STOP: missing/duplicate dispatch identity; no repeat POST`. I did not send
another POST. A direct GET then confirmed the exact pushed head, workflow path,
probe title, workflow_dispatch event and attempt 1. A fresh complete 94/94 history
also showed exactly that one matching run. The original nonmatching row values
were not retained, so the cause is not established. This was the local watcher,
not a CI firmware-parser failure. Under the explicit any-STOP rule I withheld
qualification 4 and only collected the already-submitted probe. No confirmation
predicate, guard, payload or workflow was changed after push.

**Verified hosted:** probe passed; all 400 native tests in 23.023s, 0 skips, including
the 8 local host limitations. Native loop fixture 20 checks, 0 helper mutations,
protected unchanged, all mounts/loops cleaned. Host capabilities, private manifest,
signature and exact pinned-layer pull passed; CI registry credentials were removed
outside the workspace, CI registry checks used only the job token. ISO exact 9,068,650,496 bytes and
SHA256 pin/fresh official checksum passed in one HTTP200 attempt. Live review,
offline link, post-boot tools hotplug/removal, Windows-first, detached Windows,
BootNext and protected-second proof passed; no installation was performed.

Artifact 12761677554 SHA256 `ebfb8baa4645e2dd17393f9451bde877b81627fb5e275b7a94610f27f60bc952` matched GitHub.
Independent replay: 3 protected captures, 4 zero write/unmap samples, 3 raw
varstores/exact BootNext checks, 2 NVRAM rule replays and 2 complete-variable delta
recomputations. Artifact scan 509 = 507 reviewed ISO filenames + 2 exact whole kernel
certificate messages; 0 unclassified. Native log scan 0. No ignore/rule/workflow
change. Each approved kernel finding is recorded in privacy.json with source-line
hash; raw artifact/logs/consoles stay private and ignored.

| Console | Line | Public certificate name |
|---|---:|---|
|live-ui-probe-boot-console.txt|496|Fedora kernel signing key|
|live-ui-probe-boot-console.txt|529|Fedora kernel signing key|

Receipts: `os/manifest/ci/14/14z-probe-stop/`. Exact-head push/PR privacy both
passed all 3 checks, personal terms executed. Pinned local gitleaks 8.21.2 full
history 0 before the single push; pending STOP files/history scans are required
before the local report commit and checked again afterward. One audit/helper and
one classifier invocation initially received a filesystem path instead of their
required numeric run ID and refused; corrected read-only invocations passed on
the same retained bytes. No scanner/audit assertion was changed.

| Closed package ledger | Value |
|---|---:|
|Consumed / cap|573 /800|
|Active reservation|0|
|Probe dispatches / cap|14 /14|
|Qualification dispatches / cap|3 /4; fourth unused|
|Complete history|94 /94|
|This attempt: pushes / POSTs / reruns|1 /1 /0|
|Image / publication attempts|0 /0|

Read-only billing at2026-10-27T18:52:18.935353+00:00: Actions net
$0.84, approved budget $3 with prevention
true, price$0.006/minute, paid minutes remaining
360. Billing can lag. No budget mutation was made.
Closing 0 / reserve 0 were not restored because acceptance was not met. The owner can
set the paid budget back to $0; no further dispatch is planned in this run.

**Not verified / gates:** qualification 4 was not dispatched, so the fresh installed
owner install/prepare/rerun/network invariance, records/export, login/verify/switch,
layout failure/revert/success/back, rollback/keep-stock are unproved. Real retained
fixtures/native/probe passes do not replace that qualification. Guide/card/release
and physical laptop/followability gates remain open. No owner judgment beyond 14z;
no brief design PLAN-GAP was established. The open blocker is the recorded local
confirmation STOP; no new allowance or next action is inferred.

### 14z preparation and local verification

**Done:** Boot#### records and their verbose dp rows feed one binary decoder.
Bounded UEFI lengths, HD 04/01 partition/start/size/GPT mixed-endian GUID,
File 04/04 UTF-16LE and End 7fff decide. Unknown vendor/hardware nodes are skipped
by bounded length. Only the target GPT GUID plus a File under case-insensitive
\EFI\ counts; exactly one active/inactive entry is required. Display text,
OVMF aliases and OptionalData never decide. Non-target file semantics are ignored;
malformed/unclassifiable chains cannot safely exclude a target and STOP.
Malformed target nodes, duplicate IDs/matches or missing byte rows STOP. There
is no text fallback. The private raw firmware recorder remains. Every firmware-
consuming payload command uses disk_record and this decoder. The independent
harness firmware audit is unchanged. Reference: [UEFI Device Path Protocol](https://uefi.org/specs/UEFI/2.10/10_Protocols_Device_Path_Protocol.html).

The real qualification 3 stdout with Windows/six OVMF aliases is a hash-bound
fixture. Ten firmware tests cover real output, duplicate/inactive targets,
non-EFI/Windows, truncation, node lengths/end, UTF-16, mixed-endian GUID and
signature type, wrapped dp rows, unknown nodes, opaque optional data and missing
bytes. A diagnostics refusal fixture now changes the authoritative binary GUID;
no assertion relaxed.33 real package13/14 captures/projections exercise identities,
prepare preflight, actual BLS text/link resolution, title, staged switch, AresOS,
layout, rollback/keep-stock, localed/dumpkeys, lsblk/findmnt and disk_record.
Retained 11f staged-update and all shared-script tests remain. Login/verify use
exact manifest/exit/policy checks without a prose parser. No real fresh-second-
session loginctl or NVIDIA Flatpak state exists in the stopped qualifications;
pinned-source tests and the complete stand-in walk cover those formats, with
native/VM proof mandatory. Full per-command audit/source provenance:
`os/manifest/ci/14/parser-sources/README.md`.

The regenerated 12-file bundle is `a6aff101a24af32229adcb92356fb2a79f0ec0d7227d19c050212346bb83ede3`. INSTALL's active fingerprint and
bindings are refreshed; historical receipts keep their original hashes. AST
comparison proves every other owner definition unchanged. Frozen release/runtime,
shared scripts, harness/audits, workflow and privacy unchanged; guide changes only
the fingerprint. Package13 unchanged. Package14 cap800/probe 14/owner-tools4;
October reserve0/closing0 and probe72/qualification160 bounds remain.

**Verified locally:** final whole suite 400 tests in338.03s:
392 distinct passes, exactly the same 8 native-host limits, no skips (exit1;
2 failures/9 error records include cleanup errors). Limits: Pillow 3, no-privilege
Homebrew 3/sysusers 1, DrvFS credential mode 1, individually in preparation.json.
Probe must pass all 400 natively. Initial suite exposed the obsolete diagnostics
fixture; after fixing binary GUID, the whole suite was rerun. Host walk 181 tests
passed in164.749s, binding 99 sources. Strict 258 guest
commands/258 serial wrappers,233 embedded Python,12 shells,45 Python files and
the native workflow shell passed without stderr. Windows copy 15 zero-write
refusals/exact payload passed. Actual release/git/file/read-only gh replay and
53 retained offline-source/full-listing checks passed. The unchanged real ISO
inspector rehashed 9,068,650,496 cached bytes against pin/fresh official checksum,
with 4 localization / 102 WebUI sources. Platform/cached-transport adapters only,
no CI assertion patched. Four CI-only credential steps remain fail-closed per 14f.
Evidence: `os/manifest/ci/14/14z-preflight/`. Two verified old duplicate ISO caches
were removed only in this worktree for scratch space; original ISO and all
extracted evidence preserved (`cache-reclaim.json`).

Planning at2026-10-27T18:05:33.488955+00:00: consumed543/800;
13/14 probes,3/4 qualifications; history91/
91. Push6 + probe72 + qualification160 =238.
Billing net$0.84, approved$3 Actions budget,
prevent true, paid minutes360; after bound: 122 minutes. This is planning, not authorization: exact-head
privacy and complete ledger/billing/budget refreshed before each dispatch.
One pre-dispatch FF push; no further push until qualification finishes; no rerun
on any STOP. Owner budget is read-only.

**Not verified / gates:** probe 14/qualification 4, later VM commands and acceptance
pending. Physical laptop/followability gates stay open; guide/card/release gate
NOT RELEASED. No judgment beyond14z; no new PLAN-GAP or open question locally.
Restore closing 12 / reserve 150 and mark ready only after acceptance.

## 14y — Download gates passed; qualification3 firmware-parser refusal

**Verified outcome:** [probe13](https://github.com/Ares-Empire/AresOS/actions/runs/40538251599)
passed and cost23 ledger minutes. [Qualification3](https://github.com/Ares-Empire/AresOS/actions/runs/40543952228)
ran16:45:01Z–17:38:02Z on2026-10-27, failed, and cost54 minutes. Native preflight
passed all392 tests in both runs (32.490s /29.842s, no skips), including the8
local host limits. Both native-loop fixtures passed20 checks with0 helper
mutations/protected fixture unchanged/complete cleanup. Private manifest,
signature, exact-layer pull and credential removal outside the workspace passed.
No owner secret was used. Both ISO inspections passed all9,068,650,496 bytes,
SHA256 pin and fresh official checksum; each completed in one HTTP200 attempt.
No real resume was needed on these two transfers; the12 real fake-server tests
exercise resume/restart/exhaustion and refusal branches. No retry limit or pin
was changed after push. Receipts: `os/manifest/ci/14/14y-probe/` and
`os/manifest/ci/14/14y-qualification-stop/`.

Qualification reached offline protected-second installation, orderly stock
hardware-setup reboot, offline first-stock boot, unattended/detached Windows-like
roundtrip and tools-stock. Tty3 recovery login/password sudo and tools hotplug
reached the physically typed install command. It returned a preserved private
STOP record: `Unexpected efibootmgr grammar; preserve private diagnostics`.
The harness exported that record before asserting status, so the exact reason
is retained rather than replaced by a later framed-result timeout.

**Read-only diagnosis:** actual `efibootmgr -v` has six unrelated options ending
in `{auto_created_boot_option}`. At the first, Boot0002 UEFI Misc Device, the
owner parser treats16-byte OptionalData as a literal GUID, computes
`{8108ac4e-9f11-4d59-850e-e21a522c59b2}`, then refuses at
`os/owner-tools/owner.py:470`, `require(path.endswith(rendered), message)`.
The actual suffix is the named alias. Replaying the current pure parser against
the retained stdout and actual target ESP GUID reproduces that exact line,
without host queries or mutations. The exported command trace records0
operational mutations. No parser, bundle fingerprint, fixture or owner script
was changed. Raw firmware/diagnostics stay in the private artifact; source hash,
line, alias and read-only reproduction are in `firmware-stop-reproduction.json`.

**Audits:** independent replay passed the probe's3 protected captures/4 zero
write-unmap samples/3 raw varstores and BootNext checks/2 NVRAM transitions.
It also passed every available qualification audit:7 protected captures,
8 zero-write/unmap samples,7 raw varstores and exact BootNext replays,6 NVRAM
rule replays and6 complete-variable delta recomputations. Windows-default and
detached-device rules are unchanged. The failure-path counter was recorded
while the VM was paused. Private STOP diagnostics are permitted record writes;
no claim is made that the failed install step completed.

**Not verified:** prepare, its idempotent rerun, network-up deployment/pin/pending
invariance, record export, installed registry login/verify/switch, AresOS boot,
layout failure/revert/success/back, rollback guard/rollback and keep-stock were
not reached. The full package acceptance remains unmet despite green unit tests.
Physical release/followability gates and the existing For package15 list stay open.

**Privacy:** artifact digests matched GitHub (probe12751122453; qualification
12756345422). Probe findings509 =507 reviewed ISO filenames +2 exact whole kernel
X.509 messages; qualification515 =507 +8 exact whole kernel messages. There are
0 unclassified findings. Native logs and the qualification failure log scanned0
before reading. No ignore/rule/privacy-workflow changes. Both exact-head privacy
jobs passed all3 checks, including personal terms, before both POSTs. Each public
kernel line is recorded below and with its complete source-line hash in the
privacy receipts; no raw console, ISO listing or credential is committed.

| Run | Captured boot console | Line | Public certificate name |
|---|---|---:|---|
|probe|live-ui-probe-boot-console.txt|491|Fedora kernel signing key|
|probe|live-ui-probe-boot-console.txt|524|Fedora kernel signing key|
|qualification|offline-first-stock-boot-console.txt|501|Build time autogenerated kernel key|
|qualification|offline-first-stock-boot-console.txt|527|Build time autogenerated kernel key|
|qualification|protected-second-install-boot-console.txt|492|Fedora kernel signing key|
|qualification|protected-second-install-boot-console.txt|524|Fedora kernel signing key|
|qualification|stock-initialization-0-boot-console.txt|498|Build time autogenerated kernel key|
|qualification|stock-initialization-0-boot-console.txt|519|Build time autogenerated kernel key|
|qualification|tools-stock-boot-console.txt|512|Build time autogenerated kernel key|
|qualification|tools-stock-boot-console.txt|529|Build time autogenerated kernel key|

**Local replay resource note:** before qualification, the unchanged replay's
25GiB scratch-space prerequisite found only22.8GiB and stopped before copying.
One old duplicate ISO cache in this worktree was checked against the exact pin
and removed, restoring31.2GiB. The original ISO and all reports, logs and extracted
evidence remain. The same unmodified replay then passed all bytes/checks/sources;
no source or guard was relaxed. Its hash-first cache-reclaim receipt is retained.
All local release/source/strict/privacy gates and the fresh ledger/billing/budget
guard passed before qualification3; this was not a workflow rerun.

| Closed ledger | Value |
|---|---:|
| Consumed / package cap |543 /750|
| Active reservation |0|
| Probes consumed / cap |13 /13|
| Qualifications consumed / cap |3 /3|
| Complete run history |91 /91|
| This attempt: pushes / dispatches / reruns |1 /2 /0|
| Image / publication attempts |0 /0|

Closing read-only billing at2026-10-27T17:41:41.024619+00:00 reports included0, Actions
net spend$0.84, price$0.006/minute,
approved budget$3 with prevent_further_usage true, and remaining budget
$2.16 =360 whole paid minutes. Billing may
lag charges. Reserve0 and closing0 remain: acceptance failed, so conditional
restoration, final push and PR-ready steps were not taken. The owner budget was
not changed. All authorized dispatch allowances are exhausted; no more runs.

**PLAN-GAP / open decision:** the source-audited parser does not handle the
actual formatter's named OptionalData alias. Any source-backed parser/payload
change and renewed probe/qualification allowances need integrator/owner approval.
Stop here; no fix, relaxed firmware rule or rerun was attempted. No new product
JUDGMENT-CALL. The current bundle remains the14v fingerprint.

### Preparation completed before the dispatches

**Done:** the CI inspector permits at most6 ISO connection attempts with1–5s
backoff. After a short read or connection failure it requests exactly the stored
byte offset, including offset0. Only206 with a valid Content-Range starting at
that offset and total9,068,650,496 may append. End/length/framing inconsistencies
STOP before append. A200 response to Range truncates to zero and resets hashing;
that response still consumes one of the6 attempts. Exhaustion, HTTP refusal,
oversize, malformed ranges or any final hash mismatch STOP. Local file/evidence
write errors are not treated as network retries. Every attempt records requested
and applied offsets, HTTP status, received/stored bytes, restart/error/outcome;
atomic checkpoints retain progress after headers, chunks and refusals.

The live manifest now explicitly pins its already verified9,068,650,496-byte
size. Both ISO SHA256 values, filenames, URLs and checksum sources are unchanged.
The completed file must have that exact size and its SHA256 must equal both the
existing pin and the fresh official checksum. The checksum GET and exact
filename check remain. No cache may bypass validation. Inspector hash manifests
now put hashes before paths; the active readers and cached-transport replay
adapter were updated to the new receipt, without patching CI assertions.
HTTP range rules were checked against [RFC9110](https://www.rfc-editor.org/rfc/rfc9110.html#section-14.4).

The rehearsal pip invocation now explicitly uses retries5/timeout60, retaining
Playwright1.58.0. [That pinned Playwright source](https://github.com/microsoft/playwright/blob/v1.58.0/packages/playwright-core/src/server/registry/browserFetcher.ts)
already bounds each browser download to5 attempts, so no multiplying outer loop
was added. Source hash/URL and [pip option reference](https://pip.pypa.io/en/stable/cli/pip/#general-options)
are retained in `14y-preflight/retry-sources.json`. Apt retries3 and every14x
timeout/bound are unchanged (native35, probe70/72, qualification160, VM106,
pinned-tools20). Package14 alone changes to cap750/probe13/owner-tools3;
package13 is unchanged. October reserve0/closing0 and the $3/prevention/net-spend
read-only guard remain. The owner bundle stays `effdc5d9b91eff608b456a69a53843b52b9bcb3683093760b5016119f2f000b7`;
no product/owner-script, frozen release/runtime, guide/card or audit change.

**Verified locally:**392 whole-suite tests ran in315.860s:384 distinct passes
and exactly the same8 documented host limitations, no skips (unittest exit1).
All173 host-walk tests passed and bind96 current sources.
Twelve real loopback-server tests pass: dropped transfer and exact resume;
connection failure before headers; ignored Range restarts (including empty
restart); repeated drops STOP at6 with bounded backoff; wrong offset/total/end/
wildcard/missing Content-Range STOP before append; duplicate/wrong length,
oversize, changed bytes, fresh checksum mismatch, HTTP403 and invalid size pins
all refuse. Nine existing installer/UI tests and ten guard tests passed.
Strict checks parsed258 guest scripts and258 serial wrappers with no stderr,
233 embedded Python snippets,12 shell files,45 CI/overlay/owner Python files
and the native workflow shell. Windows copy passed15 zero-write refusals and
exact bundle equality. Actual14e/14f release/git/file/read-only gh and53 retained
offline-source/full-listing replays passed. The changed actual inspector replay
rehashed all9,068,650,496 cached ISO bytes, checked a fresh official checksum,
recorded one complete200 attempt and extracted4 localization/102 WebUI sources.
This replay verifies bytes and assertions; the real fake servers verify resume
transport. Four CI-only credential checks and the8 native-host limits remain
mandatory in probe13. Proof: `os/manifest/ci/14/14y-preflight/`.

Planning at2026-10-27T15:55:45.155765+00:00:
| Reservation | Minutes |
|---|---:|
| Closed package ledger |460 /750|
| One push |6|
| Probe13 bound |72|
| Qualification3 bound |160|
| Closing privacy (October exception) |0|
| Maximum planned package total |698 /750|

Complete history:87/87;
probes12/13, qualifications2/3. Billing records included0, Actions net spend
$0.318, approved$3 with prevention true,
price$0.006/minute,
447 floored paid minutes and
209 remaining after238. Billing may lag; this planning
receipt is not dispatch authorization. Pinned local full-history gitleaks must
clear before exactly one fast-forward push. Fresh exact-head privacy, complete
ledger/billing/budget then precede probe13. Only its success, cleared14v artifact
rules, fresh replay and fresh160-minute guard permit qualification3 on the same
head. Any stop means report and no rerun or further push.

**Not verified / gates:** At that planning point both runs were pending; the actual STOP above supersedes that plan. Physical gates and
the For package15 list remain open. Artifact exceptions remain only507 public
ISO listing findings and whole captured kernel X.509 lines with nonempty name
and40 hex digits, each recorded; anything else STOPs. Only acceptance permits
restoring closing12/reserve150, one final commit/push and marking PR #13 ready.
Closing privacy must pass before merge. At the end the owner sets the Actions
budget back to$0. No new product JUDGMENT-CALL, PLAN-GAP or open question.


## 14x — Limits passed; incomplete ISO transfer blocks qualification3

**Verified outcome:** [probe12](https://github.com/Ares-Empire/AresOS/actions/runs/40528739880)
(attempt1, exact pushed head above) failed on2026-10-27. The existing inspector
refused the transfer with:
`Incomplete ISO transfer: received 2128609280 of advertised 9068650496 bytes; this probe must stop`.
Only2,128,609,280 of9,068,650,496 advertised bytes arrived. It failed the length
guard before checksum acceptance; no substituted ISO, retry, resumed download
or downloader change was attempted. Raw headers and the partial digest remain
in the private artifact, with hash-first provenance in
`os/manifest/ci/14/14x-probe-stop/download.json`. The reason for the early EOF
is not established. The full pinned local inspector replay had passed before
push; it does not override the CI transfer refusal.

The disposable runner job ran15:12:59Z–15:29:06Z and cost17 ledger minutes.
The approved20-minute pinned-tool limit, early capability proof and35-minute
native preflight passed. All380 native tests printed `OK` in26.750s, no skips,
including the8 local host limitations. The real partitioned-loop test passed
20 checks,0 helper mutations, protected fixture unchanged and complete cleanup.
Windows copy passed15 zero-write refusals with the unchanged14v fingerprint.
The release/git binding, completed-native gate, CI-only private manifest,
signature and exact pinned-layer pull all passed. Only the CI GITHUB_TOKEN was
used; owner-token API calls0. Cleanup removed credentials outside the workspace.
No claim is made that retries caused the faster setup; its recorded step passed.

The live/installed two-disk VM step was skipped. Qualification3, installed owner
commands, layout failure/revert/success, rollback and full protected-disk/NVRAM/
BootNext qualification on this head remain **not verified**. The early mini-VM
and native loop fixture are prerequisite evidence only. No audit was weakened.

**Privacy:** the25-member private artifact ZIP digest matched GitHub
(artifact12745083909). Pinned gitleaks8.21.2 found0 findings in all artifacts,
0 in the native log and0 in the ISO-failure log before either log was read.
No ISO listing or captured boot console was produced; neither14s nor14v exception
was needed. Both exact-head privacy jobs had passed all3 required checks,
including personal terms, before dispatch. No ignore, rule or privacy-workflow
change. Detailed receipts: `os/manifest/ci/14/14x-probe-stop/`; raw logs remain
ignored and private.

| Closed ledger | Value |
|---|---:|
| Package minutes consumed / cap |460 /700|
| Active reservation |0|
| Probes consumed / cap |12 /12|
| Qualifications consumed / cap |2 /3|
| Complete branch run history |87 /87|
| This attempt: pushes / reruns |1 /0|
| Images / publications |0 /0|

Fresh closing read-only billing at2026-10-27T15:31:54.678463+00:00 records included0,
Actions net spend$0.318, price$0.006/minute,
approved$3 with prevent_further_usage true, and remaining budget
$2.682 =447 whole paid minutes. Billing
may lag charges. Reserve0/closing0 remain: acceptance was not met, so conditional
restoration and PR-ready steps were not taken. The owner budget was not changed.

**PLAN-GAP / open decision:** the pinned download was incomplete; stop here.
No further probe or qualification, timeout/URL/image/transport change, retry or
push is authorized by this failed run. No new product JUDGMENT-CALL. Physical
release gates and the existing For package15 list remain open and unchanged.

### Preparation completed before the probe

**Done:** native preflight limit15→35 minutes; package14 probe job40→70;
owner-tools qualification job130→160. The pinned-tools step remains20 and
the qualification VM step remains106. Other package job limits are unchanged.
Before Playwright's install, the disposable runner writes exactly
`Acquire::Retries "3";` to apt configuration, so its own apt calls retry too.
No mirror, package list/pin, image, payload, owner command or audit was changed.
Guard bounds are72/160, including both probe CI guard calls; full reservations
are238 before push,232 before probe and160 before qualification. Package14
keeps cap700 and owner-tools3, with probe cap12. Package13 settings are unchanged.
October reserve0/closing0 and the read-only $3/prevention/net-spend guard remain.
The14v bundle remains `effdc5d9b91eff608b456a69a53843b52b9bcb3683093760b5016119f2f000b7`.

**Verified locally:**380 whole-suite tests ran:372 distinct passes and exactly
the same8 documented native-host limitations, no skips (unittest exit1).
152 host-walk tests passed and bind92 current sources. Ten focused guard tests and four legacy-budget tests
passed, pinning every approved timeout, both CI reservations, retries before
Playwright, the unchanged20/106 limits and dispatch refusal boundaries.
The first whole run exposed one still-old timeout assertion (380 tests;
3 failures/9 errors); its expectations were updated to14x, then the whole
suite was repeated. That assertion now also runs in the host walk.
Strict checks parsed258 guest scripts and258 serial wrappers with no stderr,
233 embedded Python snippets,12 shell files,45 CI/overlay/owner Python files,
and the changed native workflow shell body. Windows copy passed15 zero-write
refusals with exact bundle equality. Actual14e/14f release/git/file/read-only gh
and53 retained offline-source/full-listing replays passed. Actual ISO inspection
rehashed9,068,650,496 bytes, checked a fresh publisher checksum and read4
localization/102 WebUI sources. Four credential-only checks and the8 host-limit
tests remain mandatory in CI. Current source-bound proof:
`os/manifest/ci/14/14x-preflight/`.

Pre-push planning at2026-10-27T14:54:22.274232+00:00:
| Reservation | Minutes |
|---|---:|
| Closed package ledger |437 /700|
| One push |6|
| Probe12 bound |72|
| Qualification3 bound |160|
| Closing privacy (October exception) |0|
| Maximum planned package total |675 /700|

Complete history:84/84;
probes11/12, qualifications2/3. Billing records included0, Actions net spend
$0.27, approved$3 with prevention true,
price$0.006/minute and
455 floored paid minutes;
217 remain after238. These read-only planning values
may lag charges and do not authorize a dispatch. The pinned local full-history
scan must pass before the exactly one fast-forward push. Then fresh exact-head
privacy, complete ledger/billing/budget precede probe12. Qualification3 requires
its passing probe, cleared14v artifact rules, fresh replay and a fresh160-minute
guard, all on the same head. Any stop means report, no rerun or further push.

**Not verified / gates:** At that planning point probe12 and qualification3 were pending; the STOP above supersedes that plan. Physical release
and laptop/followability gates remain open. Artifact exceptions remain only the
507 public ISO listing findings and exact whole captured kernel X.509 lines
with a nonempty name and40 hex digits, each recorded; anything else STOPs.
Only acceptance allows restoring closing12/reserve150, one final commit/push
and marking PR #13 ready. Closing privacy must pass before merge. This run ends
without merging; the owner then sets the Actions budget back to$0. No new
product JUDGMENT-CALL, PLAN-GAP or question. The existing For package15 list
remains unchanged.


## 14w — Probe11 native-preflight timeout; qualification3 blocked

**Verified outcome:** [probe11](https://github.com/Ares-Empire/AresOS/actions/runs/40519384061)
(attempt1, exact pushed head above) failed on2026-10-27. GitHub reports:
`The action 'Qualify tools, regressions, rewritten release identity and private access' has timed out after 15 minutes.`
The disposable runner job ran14:15:32Z–14:43:35Z and cost29 ledger minutes.
The early capability proof passed. Playwright's `install --with-deps chromium`
started dependency installation14:28:34Z; browser downloading began14:42:53Z,
about14m20s later. Its public Ubuntu mirror requests repeatedly printed `Ign:`
for four font packages. No mirror, timeout, package pin or dependency was changed
in response. The downloaded browser then completed;379 native tests printed
`OK` (21.696s, no skips), the exact real partitioned-loop test passed all20
checks with0 helper mutations/protected fixture unchanged/complete cleanup,
and Windows copy passed15 zero-write refusals with the exact14v bundle.
The release verifier printed its qualified private release/runtime PASS. GitHub
still marked the complete step failed at its15-minute limit. Individual PASS
lines do not satisfy the passing-probe gate.

The later credential, private manifest/signature/pull, live ISO inspection and
two-disk VM steps were skipped. Qualification3, layout/rollback trials and full
protected-disk/NVRAM/BootNext qualification remain **not verified** on this head.
The capability mini-VM and native loop fixture are prerequisite evidence only.
No check was loosened and no rerun, repair or extra dispatch was attempted.

**Privacy:** the private artifact ZIP digest matched GitHub exactly
(artifact12743785147,19 files). Pinned gitleaks8.21.2 found0 findings in all
retained artifact files and0 in the native log, before the log was read.
No ISO listing or boot console was produced, so neither14s nor14v exception
was needed. Both exact-head push/PR privacy runs had passed every required
step, including personal terms, before the probe POST. No ignore/rule/workflow
change. Detailed receipts and source hashes:
`os/manifest/ci/14/14w-probe-stop/`; raw private files remain ignored.

| Closed ledger | Value |
|---|---:|
| Package minutes consumed / cap |437 /700|
| Active reservation |0|
| Probes consumed / cap |11 /11|
| Qualifications consumed / cap |2 /3|
| Complete branch run history |84 /84|
| This attempt: pushes / reruns |1 /0|
| Images / publications |0 /0|

Fresh closing billing at2026-10-27T14:44:54.024703+00:00 reports included minutes0,
Actions net spend$0.264, price$0.006/minute,
approved budget$3 with prevent_further_usage true, and available paid budget
$2.736 =456 whole minutes. These are the read-only
API values, not a promise that delayed billing is final. Reserve0/closing0 are
unchanged: acceptance was not met, so their conditional restoration and PR-ready
step were not taken. The owner Actions budget was not changed. No further run
is authorized by this failed probe; the owner controls when to reset that budget.

**PLAN-GAP / open decision:** the15-minute native preflight was exhausted by
its dependency-installation delay. Stop here; don't change its timeout or mirror,
retry the probe, spend the remaining qualification, or push this report without
new authorization. No product JUDGMENT-CALL. All physical gates and the existing
For package15 list remain open and unchanged.

### Preparation completed before the probe

**Done:** package14 alone now has cap700, probe11 and owner-tools3. Package13
is unchanged. October's explicit reserve0/closing0 are unchanged. The guard
requires the read-only budgets API to show exactly the approved organization
Actions budget$3 and prevention true. It subtracts all reported net Actions
spend before dividing by the billing API's positive runner price and flooring.
Missing, malformed, stale, inconsistent or changed billing/budget data STOPs.
The single push carries the14s bounded loop-node fix,14t bookkeeping and14v
source-verified firmware parser/diagnostics fix. The14v owner bundle remains
`effdc5d9b91eff608b456a69a53843b52b9bcb3683093760b5016119f2f000b7`. No payload, frozen release/runtime,
workflow, permission, privacy ignore/rule or image change in14w.

**Verified locally:** 379 whole-suite tests ran: 371 distinct passes,
exactly the same8 native-host limitations and no skips (unittest exit1).
147 host-walk tests passed and bind91 current sources,
including billing regressions. Strict parsing passed258 guest commands and258
serial wrappers with no parse stderr,233 embedded Python snippets,12 shell
files and45 CI/overlay/owner Python files. Windows copy passed15 zero-write
refusals and exact bundle equality. Actual14e/14f git/file/read-only gh release
replay,53 retained offline sources and complete listing passed. Actual installer
inspection rehashed9,068,650,496 bytes, checked the fresh public publisher
checksum, and read4 localization/102 WebUI sources. Four credential-only
checks and the8 native-host limitations remain mandatory in CI. A supplemental Windows-Python equality invocation passed3/4 but failed the
Linux heredoc test because Windows text pipes add CRLF; no product fix or
assertion change was made. The authoritative suite and host walk use WSL Bash;
the final WSL equality check is retained separately. Current proof:
`os/manifest/ci/14/14w-preflight/`.

Pre-push planning at2026-10-27T14:00:52.769433+00:00: 403+178/700,
complete81/81 history.
Billing reports included0, net Actions spend
$0.174, price$0.006/minute,
available budget$2.826 and
471 floored paid minutes; 293
remain after the178-minute pre-push reservation. These are planning values,
not dispatch authorization. Pinned full-history gitleaks must clear before the
exactly one fast-forward push. Fresh exact-head privacy, complete ledger,
billing and budget precede probe11. Qualification3 requires the same head,
a successful probe, cleared14s/14v artifact classification, fresh replay and
a fresh130-minute guard. Any refusal or run/artifact stop means no rerun.
No further push until qualification has finished.

**Not verified / gates:** At that planning point probe11 and qualification3 were pending; the STOP below supersedes that plan. Physical
laptop/followability checks stay open. Artifact exceptions are only the507
public ISO listing findings and whole captured boot-console kernel X.509 lines
with a nonempty certificate name and exactly40 hex digits; each is recorded.
Anything else STOPs before qualification. Acceptance alone permits a final
commit restoring closing12/reserve150, one closing push and marking PR ready.
Closing privacy must pass before merge. The owner resets the Actions budget
to$0 after this run ends. No new product JUDGMENT-CALL, PLAN-GAP or question.


## 14v — Pinned firmware grammar, private STOP records and parser audit

**Done:** verified the exact pinned Bazzite44 RPM database: efibootmgr
**18-11.fc44**, efivar-libs **39-12.fc44**. The read-only header verifier passed
all15 recorded packages. A full hash/manifest check of the frozen stock OCI
layer confirms its RPM database is byte-identical to the ISO's; the same15
headers passed on that independent extraction too. Fedora f44 specs match
those releases: efibootmgr has
no patches; efivar's ABI/storage patches do not affect formatting. The40
original primary-source files, immutable URLs/commits, hashes and complete
payload parser inventory are retained in
[the format audit](../../os/manifest/ci/14/parser-sources/README.md) and its
deterministic source archive. Plaintext upstream sources scanned clean before
archiving; original patch whitespace and bytes are preserved.

The relevant upstream implementations are
[efivar39 media formatting](https://github.com/rhboot/efivar/blob/c47820c37ac26286559ec004de07d48d05f3308c/src/dp-media.c),
[the file-string macro](https://github.com/rhboot/efivar/blob/c47820c37ac26286559ec004de07d48d05f3308c/src/dp.h),
[node joining](https://github.com/rhboot/efivar/blob/c47820c37ac26286559ec004de07d48d05f3308c/src/dp.c),
and [efibootmgr18](https://github.com/rhboot/efibootmgr/blob/c3f9f0534e32158f62c43564036878b93b9e0fd6/src/efibootmgr.c).
The line is `Boot####` + active/inactive marker + space + description + TAB +
device path + directly appended OptionalData + LF. The HD node is
`HD(decimal,GPT,guid,0xhex,0xhex)`; efivar39 emits the file string itself and
joins it with `/`. `-v` additionally emits `dp:` node bytes and optional `data:`
bytes. OptionalData has no general delimiter; its raw-text, binary-hex, GUID
and legacy shim renderers are recorded in the audit.

`firmware_entry` parses those records instead of searching a loose regex. It
accepts current `/\EFI\...` and legacy `/File(\EFI\...)`, compares ESP GPT
GUIDs case-insensitively, and requires exactly one Boot number with that GUID
and an EFI path. Verbose node lengths, GUID, file and terminator must agree;
appended OptionalData cannot supply a fake match. Duplicate/ambiguous entries,
unknown grammar, non-EFI paths, malformed bytes or firmware stderr STOP. Every
existing disk, mount, serial, deployment, pin and pending-state check remains.
No firmware audit was widened. The native-loop fixture now emits the pinned
TAB/path/verbose-byte grammar, using its independently cross-checked native GUID.

The retained Boot000A varstore has one Bazzite HD/File option, consistent with
the integrator's diagnosis. Its fixture is explicitly a **source-rendered
reconstruction**, not guest stdout: qualification2 never retained that stdout.
The other payload tool-output parsers were checked against their pinned
emitters (systemd259.9, util-linux2.41.5, kbd2.9.0, coreutils9.10, glibc2.43,
rpm-ostree2026.3, ostree2026.4, bootc1.16.13). The executable systemctl shim now
has the real three columns. Dumpkeys fixtures are lossless verbatim y/z-row
projections of retained package13 output. Real session/keyboard/pause parsers
also run on source-shaped responses. The eight shared release scripts remain
byte-identical; the audit identifies every JSON/text/opaque-output consumer.

The real CLI now shares install's Host trace. Every root command refusal
collects raw `efibootmgr -v` (or the failed read's raw stdout/stderr and reason)
in a root-owned0700 `/run/ares-owner-diagnostics` directory, using exclusive
mode0600 atomic JSON records. An install preflight refusal does not create
`/var/lib/ares` or copy/install anything. Refusal handling writes only private
diagnostics and introduces no deployment, pin, BLS, disk, keymap or credential
mutation. An I/O failure after an authorized operation can leave partial state;
it preserves that state, records STOP and never emits a premature success.
Arbitrary argv and hidden credentials are never recorded. Non-root callers
still refuse before any host access. The administrator must keep the session
open: these pre-install records are volatile across a reboot.

The harness reads private command JSON from both stores through the existing
checksum-framed protocol, saves the complete STOP record **before** asserting
acceptance, and fails closed on unsafe metadata or ambiguous records. Tests
execute the real reader in real Bash with ordinary repo-file/metadata adapters;
no host privilege is used. Framing and owner commands themselves are unchanged.
An error saving a normal success record becomes a STOP record, never `passed`;
install writes its success record only after its final short-entry step. Both
failure paths have execution regressions that prove no premature success leaks.

Current local bundle manifest SHA256:
`effdc5d9b91eff608b456a69a53843b52b9bcb3683093760b5016119f2f000b7`.
INSTALL's Windows-copy check, BUDGET's current_bundle and all current bindings
use this value. Historical run artifacts, reports and old preflights retain
their actual fingerprints; the new reference inventory labels them historical.
Package15's worktree was not touched. This payload has **no VM qualification**.

**Verified locally:**

- Whole OS suite: `wsl.exe bash .work/14/local/whole-suite.sh` ran **378 tests in
  311.181s**:370 distinct passes; the same8 known host-limit tests;
  `FAILED (failures=2, errors=9)`, with cleanup errors accounting for duplicates.
  No skip, weakened assertion or new failure. Exact IDs/reasons and the log
  hash are in [preparation.json](../../os/manifest/ci/14/14v-preflight/preparation.json).
- Final zero-cost host walk: **135 tests in 138.760s, OK**; **90 source
  bindings**,258 composed guest commands, all retained order/hotplug/keyboard/
  refusal checks. Includes the new parser, diagnostics, classifier and source
  regressions; no stick crosses a reboot.
- Strict14i checks: **258 guest +258 serial wrappers**,233 embedded Python
  programs,12 CI/release shell files and45 CI/overlay/owner Python files passed;
  any Bash parse stderr, including warnings, remains a failure.
- Real read-only release/source replay passed (`verify_release.py 40154642447`,
  the14g git-only squash binding, and `verify-zero-cost.py --14b` with53 sources
  and the full1,439,437-line ISO listing). Actual installer_inspect.main passed
  with all9,068,650,496 ISO bytes rehashed against the exact pin and fresh public
  publisher checksum;4 localization and102 WebUI sources. Only existing Windows
  tar/WSL unsquashfs/path/LF adapters; no CI assertion changed.
- Windows `owner-tools.Tests.ps1`: **15 destination refusals, zero writes**;
  successful copy/readback equals the regenerated reviewed bundle.
- Source/command/bundle equality, manifest hash-before-path checks,
  `git diff --check`, frozen eight-path runtime diff and unchanged shared
  release/permission/privacy/budget-configuration checks passed. Pinned
  gitleaks8.21.2 scans are recorded in the local privacy receipt; no ignores,
  allowlists, rules, privacy workflows or scopes changed.

**Artifact classification:**14v allows only a complete captured-boot-console
line `[timestamp] Loaded X.509 cert '<nonempty name>: <exactly40 hex>'`. It is
not a substring match, does not strip arbitrary control characters, and does
not allow findings from unrelated files. Local tests accept the Fedora and
Build-time names and refuse prefix/suffix, bad lengths, nonhex, other messages,
multiline/control-prefixed or empty-name forms. Probe10's509 findings classify
as507 reviewed public ISO-listing +2 exact kernel lines; qualification2's515
classify as the same507 listing +8 exact kernel lines, **zero unclassified**.
Each whole source line is bound below (hash excludes the CR/LF terminator);
raw fingerprints/consoles are not committed. Any other finding still STOPs.

| Run | Whole-line SHA256 | Captured console | Line | Certificate name |
| --- | --- | --- | --- | --- |
| 40417291358 | `a86d89d3e5c82545ab1a88aaa8a05144f2969a08d956157d1129858ab04d3bbe` | `evidence/two-disk/live-ui-probe-boot-console.txt` | 497 | Fedora kernel signing key |
| 40417291358 | `c7fe0c4da26f1e3566ce0fe564457f5e54c64242e2f282a4e83e944f6e9686f9` | `evidence/two-disk/live-ui-probe-boot-console.txt` | 530 | Fedora kernel signing key |
| 40421596174 | `07c6d1c068f2758ab440484336f4ca34da7676d410ed415e2f3943d1c7b4bde2` | `evidence/two-disk/offline-first-stock-boot-console.txt` | 498 | Build time autogenerated kernel key |
| 40421596174 | `0a5279c21180c68282ef1e7f221cf166dcdfa44d784761002522ce57b6b6eeb6` | `evidence/two-disk/offline-first-stock-boot-console.txt` | 509 | Build time autogenerated kernel key |
| 40421596174 | `994b7a4d2def60914af1cf799024c402dccc29edfd89ab3f8fe143c131bdfd02` | `evidence/two-disk/protected-second-install-boot-console.txt` | 491 | Fedora kernel signing key |
| 40421596174 | `6f56aaa6390f73d73e479429351ba85c0bf3cf243c7009a13ce8805298cc92be` | `evidence/two-disk/protected-second-install-boot-console.txt` | 524 | Fedora kernel signing key |
| 40421596174 | `cc70dc42e82de798c4ca2e58938cc98e24813fc29d8fa7814ea1357b3f158192` | `evidence/two-disk/tools-stock-boot-console.txt` | 503 | Build time autogenerated kernel key |
| 40421596174 | `ec6bcd1c592c5785825e4fc7a62efb58ab9ef7c3542e1f27b6d5420b8edba2ba` | `evidence/two-disk/tools-stock-boot-console.txt` | 521 | Build time autogenerated kernel key |
| 40421596174 | `ed802d6e5af9d58522d56d1047dd98ab21ea1edb33d5e5b966502d1bbd7f5910` | `evidence/two-disk/stock-initialization-0-boot-console.txt` | 509 | Build time autogenerated kernel key |
| 40421596174 | `710c9170ab9a35e2cc8b29dc8d1909865756e5a7a4f134b63ed06b283f4b34e4` | `evidence/two-disk/stock-initialization-0-boot-console.txt` | 527 | Build time autogenerated kernel key |

**Not verified:** no new native hosted-runner or VM run is authorized. The
whole suite's8 local limits are3 missing-Pillow greeter tests,3 privileged
Homebrew/ACL tests,1 privileged sysusers test and1 DrvFS0600 metadata test;
no package install or sudo bypass was used. Native mounted-loop behavior,
actual private STOP-record ownership and the new parser on a fresh guest await
an owner-authorized fresh probe/qualification. The earlier355-test native
passes belong to `bbf228c`, not this payload. All physical/followability,
NVIDIA Flatpak, forgotten-stick and laptop release gates remain open.

**Budget / stop state:** the last closed ledger remains **403/520**,0 reserved,
all **10/10 probes** and **2/2 qualifications** spent.14v used0 Actions minutes,
0 pushes and0 dispatches; it did not reread billing/budgets or change caps,
price, paid budget, closing0 or reserve0. The brief's roughly$0.92 overflow
balance is the integrator's estimate, not a fresh billing claim. No future
dispatch is authorized. Acceptance is unmet; closing12/reserve150 restoration
and marking PR#13 ready remain conditional on acceptance and closing privacy.

**JUDGMENT-CALL:** only the explicitly requested private diagnostic write is
permitted on refusal; pre-install diagnostics use `/run` so a refusal cannot
start an installation or write a protected disk. Unknown formatter variants
and GUID aliases STOP rather than being guessed.

**PLAN-GAP:** no contradiction to the integrator diagnosis was found. The
missing original guest stdout cannot be reconstructed as observed evidence;
the new recorder fixes that evidence gap. Local proofs do not close VM or
physical acceptance.

**Open questions:** the owner's next budget/date and fresh run allowances.
No decision was inferred, no rerun attempted, and no PR readiness changed.

The following sections preserve their historical observations and superseded
decisions, including the narrower14u artifact classification.

## 14u — Public certificate classification; qualification2 STOP

**Done / verified classification:** the two probe10 findings at lines497/530
match the complete kernel `[timestamp] Loaded X.509 cert 'Fedora kernel signing
key: <hex>'` message, with40 hexadecimal digits. The local full-line matcher
passed1 valid and7 negative fixtures (extra prefix/suffix, another message/key,
nonhex, an extra line and an arbitrary prefix). The same exact rule classified
two live-installer console messages in qualification2. Each classified line is
recorded below by run, captured file, line and SHA-256 (excluding line ending);
all four labels are `Fedora kernel signing key`. No fingerprint value or raw
console was copied into Git. The other507 findings in each artifact remain the
14s public ISO file-name listing. No ignore, allowlist, rule or workflow change.

| Run | Captured artifact file | Line | Full-line SHA-256 |
| --- | --- | --- | --- |
|40417291358| `evidence/two-disk/live-ui-probe-boot-console.txt` |497| `a86d89d3e5c82545ab1a88aaa8a05144f2969a08d956157d1129858ab04d3bbe` |
|40417291358| `evidence/two-disk/live-ui-probe-boot-console.txt` |530| `c7fe0c4da26f1e3566ce0fe564457f5e54c64242e2f282a4e83e944f6e9686f9` |
|40421596174| `evidence/two-disk/protected-second-install-boot-console.txt` |491| `994b7a4d2def60914af1cf799024c402dccc29edfd89ab3f8fe143c131bdfd02` |
|40421596174| `evidence/two-disk/protected-second-install-boot-console.txt` |524| `6f56aaa6390f73d73e479429351ba85c0bf3cf243c7009a13ce8805298cc92be` |

**Pre-dispatch verification:** no pull or push. Remote/probed head remained
`bbf228c1dcb7800af5b9793f56acf77d11d5aff2`; local cece95a differed only by14u's
brief and prior STOP documentation. All182 preflight and76 host-walk source
bindings matched the target. Actual14e/14f release/git/file/read-only gh replay,
53 retained sources and the complete listing passed again. Strict parsing
passed258 guest/258 serial commands without stderr,233 embedded Python snippets,
12 shell files and45 CI/overlay/owner Python files. Fresh actual ISO inspection
rehashed9,068,650,496 bytes, checked a fresh publisher checksum and read4
localization/102 WebUI sources. Four credential-only checks stayed mandatory in
CI. Exact-head privacy40416793839 and40416787226 were rechecked: all3 checks
passed, including actual personal-term execution.

**Actual authorization:** complete80/80 pre-dispatch history; **335+130=465/520**.
Fresh billing/budget verified109 included minutes plus166 floored paid minutes,
price$0.006/minute, Actions budget$1 and prevent_further_usage true, leaving145
after reservation. Exactly one qualification POST used the remote branch on
the exact probe10 head, protected-second order and probe40417291358:
[40421596174](https://github.com/Ares-Empire/AresOS/actions/runs/40421596174),
run_attempt1. No push occurred in14u.

**Verified natively / partial VM evidence:** early loop/FUSE exFAT/fsck/QEMU /
OVMF/QMP capabilities passed. The whole native suite passed **355 tests in29.196s,
no skips**. Real native loop fixture:20 checks passed,0 helper mutations,
protected fixture unchanged and all fixture mounts/loops cleaned up. Private
metadata/manifest, signature and exact layer pull passed. The offline live
install completed; hardware setup and its orderly pre-login reboot completed;
first stock stayed offline with no staged deployment, pin or queued rollback.
Unattended Windows and the detached Windows round trip passed. Tty3 password
login and password sudo worked. Tools hot-plug succeeded after sign-in, and
14j's one physical Enter resync recovered the covered root prompt. The tool
received both independent serials. Native job-token cleanup passed: removed,
outside workspace, no owner token. Independent raw audit replay passed **7
protected captures,8 zero-write/unmap samples,7 decoded varstores/BootNext audits
and6 NVRAM/all-variable delta recomputations**, including the paused failure
counter. These are partial-stage results, not full qualification acceptance.

**Actual owner STOP:** `failure-tools-stock.png` shows the exact owner command,
Crucial/Micron inputs and **STOP: Linux firmware entry does not uniquely map to
target EFI**. The tool preserves the administrator session and tells the owner
not to reboot or retry a different target. The harness later timed out awaiting
the framed owner install result (`owner_vm.py`416→278; `switch_vm.py`230);
`tools-install-owner-result-incomplete.txt` is retained. `prepare` was not reached.
`disk_record` refuses before the install's first `HOME.mkdir`, so the tool's
installation writes did not begin. No guard was removed, retried or widened.

Raw retained firmware independently decodes **one** permitted Linux load option:
Boot000A/Bazzite, target ESP partition1, `\EFI\fedora\shimx64.efi`.
The exact guest `efibootmgr -v` stdout consumed by the refused helper was not
exported, so the text-matching cause is unresolved. This observation does not
relax the firmware audit or prove a parser fix. It needs an integrator decision;
no harness, owner-script, image or VM change was made.

**Artifact privacy STOP as well:** the pinned redacted artifact/native-log scan
reported515 generic-api-key findings:507 ISO-listing findings,2 exact14u kernel
messages above, and6 findings below that **did not match the permitted whole-line
class**. Both universal-newline and raw LF-counted reads were checked; no message
content/value is reproduced. They remain unclassified, not asserted credentials
and not declared harmless. No broader exception was accepted. The separately
extracted failure log scanned0 findings before its diagnostic tail was read.

| Unclassified artifact file | Line | Rule |
| --- | --- | --- |
| `evidence/two-disk/offline-first-stock-boot-console.txt` |498|generic-api-key|
| `evidence/two-disk/offline-first-stock-boot-console.txt` |509|generic-api-key|
| `evidence/two-disk/tools-stock-boot-console.txt` |503|generic-api-key|
| `evidence/two-disk/tools-stock-boot-console.txt` |521|generic-api-key|
| `evidence/two-disk/stock-initialization-0-boot-console.txt` |509|generic-api-key|
| `evidence/two-disk/stock-initialization-0-boot-console.txt` |527|generic-api-key|

API-digest-bound private artifact:12697122720 was probe10; qualification artifact
12701280757 is5,451,470 bytes/437 members, SHA-256
`c9a5ded1a436ef30b8314518f3a5aee3cee3c7d4c6c47e2f01ff2b4d1e7f4758`.
Raw artifact/logs/screenshot remain private under `.work/14/run-40421596174/`;
committed redacted receipt: `os/manifest/ci/14/14u-qualification-stop.json`.

| Closed package14 ledger | Value |
| --- | --- |
| Complete history |81/81|
| Consumed / cap |403/520 minutes|
| Reserved |0, closed bookkeeping only|
| Probes / qualifications |10/10;2/2|
|14u pushes / reruns |0/0|
| Image attempts / publications |0/0|
| Included minutes left |0 at the billing snapshot|
| Actions budget / prevention |$1 / true|
| Price / available paid minutes |$0.006 /156|
| Reported paid net spend |$0.06 at2026-10-27T00:56:51Z|
| Closing / org reserve |0/0; restoration condition not met|

**Not verified / PLAN-GAP / open questions:** owner installation/prepare and
rerun, first-network deployment invariance, record export, private owner login /
switch, AresOS/foot typing, guarded US failure/revert and US International change /
back, rollback and keep-stock remain unqualified. The exact real firmware text
and the6 artifact finding locations need integrator review. Acceptance is not
met: no closing12/org150 restoration, closing push or PR-ready transition.
No new product JUDGMENT-CALL; the observed firmware refusal/result wait is the
unresolved execution gap. Physical laptop/followability/release gates and the
package15 handoff remain open. No real laptop touched; frozen runtime, owner
payload/fingerprint, guides, CI source/tests/workflows and privacy rules stayed
unchanged. Pinned local gitleaks must be0 for the local STOP commit; no further
push, dispatch, rerun or merge. The run is over; owner can set the budget to$0.

## 14t — Approved paid overflow; probe10 passed; privacy STOP

**Done:** package14 cap520, probe10, owner-tools2; package13 unchanged.
October org reserve0 and closing0 remain explicit. The guard reads the complete
organization budgets response and requires exactly one organization Actions
ProductPricing budget, amount$1, prevent_further_usage true. Wrong amounts,
prevention/scope, duplicate/missing or incomplete responses STOP. The runner's
positive finite pricePerUnit comes from current billing usage. Both API sources
and response hashes, amount/prevention, SKU/price, included minutes and floored
paid minutes are recorded in the ledger. Reported net Actions spend is deducted
before flooring so it cannot be reserved twice; paid approval is October2026
only. Package13 retains its free-only policy. Billing stays outside CI; no
credential, scope or owner secret changed. No billing write was performed.

Exactly one fast-forward push advanced22e07b1 to
`bbf228c1dcb7800af5b9793f56acf77d11d5aff2`, carrying14s's loop-node fix, local
briefs and prior STOP reports. Pinned gitleaks8.21.2 full-history and pending /
preflight-file scans reported0 findings before this push. Exact-head privacy
40416793839 and40416787226 passed all3 checks, including actual personal-term
execution. Fresh authorization proved **79/79 complete history;312+172=484/520;
114 org minutes after reservation**. Budget$1/prevention true and the live
Linux price$0.006/minute were verified immediately before dispatch.

**Verified locally:**355 whole-suite tests ran in369.346s:347 distinct passes,
exactly8 known native-host limitations, no skips (unittest exit1, failures2 /
errors9 including cleanup duplicates).112 host-walk tests passed in157.203s,
23 focused guard/permission tests and2 manifest/bundle equality tests passed.
Strict parsing passed258 guest/258 serial commands with no stderr,233 embedded
Python snippets,12 shell files and45 CI/overlay/owner Python files. Windows copy
passed15 zero-write refusals and exact payload equality. Actual14e/14f release /
git/file/read-only gh replay and53 retained offline sources plus complete listing
passed. Fresh actual inspector replays for probe and qualification rehashed all
9,068,650,496 ISO bytes, checked fresh publisher checksums, and read4 localization /
102 WebUI sources. Current bindings: `os/manifest/ci/14/14t-preflight/`.

**Actual probe10:** [40417291358](https://github.com/Ares-Empire/AresOS/actions/runs/40417291358),
run_attempt1, succeeded on the exact pushed head. Early loop/FUSE exFAT/fsck /
QEMU/OVMF/QMP capabilities passed. The native suite passed **355 tests in28.102s,
no skips**. Real loop regression:20 checks passed,0 helper mutations, protected
fixture unchanged, all fixture mounts and loops cleaned up. Native private
metadata/manifest, signature and exact layer-pull checks passed. Live ISO and
live-environment probes passed, including tools hot-plug/removal, offline link,
bundle equality, detached Windows boot and target reset. The loop-node fix
therefore ran successfully natively. Auth cleanup confirmed job token removed
outside the workspace; no owner token used. Independent raw evidence replay
passed3 protected-disk captures,4 zero-write/unmap samples,3 decoded varstores /
BootNext audits and2 NVRAM/all-variable delta recomputations.

**STOP / privacy:** the pinned redacted artifact/native-log scan found509
`generic-api-key` findings.507 remain exclusively in the integrator14s-classified
public Bazzite ISO filename listing, private and never committed. The other2
are in `evidence/two-disk/live-ui-probe-boot-console.txt`, lines497 and530.
These are **unclassified findings**, not a claim that a credential leaked or
that they are harmless. No matching value or console content is reproduced.
The mandatory rule says a finding anywhere else is a STOP, so qualification2
was **not dispatched**. No ignore/allowlist/rule/privacy-workflow change, rerun,
additional push, PR-ready transition or merge occurred. Owner/integrator review
of those two private-artifact locations is required before any continuation.
Redacted metadata/receipts: `os/manifest/ci/14/14t-probe-stop.json`; raw artifact
and logs remain private under `.work/14/run-40417291358/`.

| Actual closed package14 ledger | Value |
| --- | --- |
| Complete history |80/80|
| Consumed / cap |335/520 minutes|
| Reserved |0 (closed bookkeeping only)|
| Probe dispatches |10/10|
| Owner-tools qualifications |1/2; second not dispatched|
| Publications / image attempts |0|
| Closing / org reserve |0/0; acceptance restoration condition not met|
| Included minutes left (billing snapshot) |109|
| Approved budget / prevention |$1 / true|
| Linux price / available paid minutes |$0.006 /166|
| Total available / reported paid net spend |275 minutes /$0|

**Not verified / gates / open questions:** the full owner-tools qualification,
layout failure/revert, complete switch/rollback and all remaining VM acceptance
stay pending. Physical laptop/followability gates and the package15 handoff
below remain open; no real laptop was touched. No image, frozen runtime, owner
payload/fingerprint, guide, workflow/permission or privacy-rule change in14t.
Budget reservation restoration (closing12/org150) and PR-ready remain conditional
on acceptance; it is not met. No new product JUDGMENT-CALL or product PLAN-GAP.
The privacy finding classification is unresolved. The run has ended; the owner
can now reset the org Actions budget to$0. No further run is authorized here.

## 14s — Loop partition readiness; local only

**Done:** one shared wait covers all four `losetup --partscan` callers (media,
protected-disk preparation, capabilities and native device regression). After
backing-file/GPT verification it settles udev, then checks exact block nodes,
sysfs start/size against the written GPT, and device identity. The15-second
wait permits one `partx --update` plus settle, then STOPs with sysfs/udev state.
It never selects another device. Native-device detach now settles udev too.
A readiness failure cannot reach media formatting/copying/hashing. Only CI
harness/tests and current walk bindings changed; owner bundle, image/runtime,
guides, budgets, workflows and privacy rules are unchanged.

**Verified locally:** `PYTHONPATH=os/tests python3 -m unittest test_loop_nodes
 test_owner_media test_owner_capabilities test_owner_devices_native -v` passed
30 tests. Final-source `python3 reviews/14-owner-tools/walk-host.py` passed112
in155.682s, with76 checked source bindings. The whole-suite command
`python3 -m unittest discover -s os/tests -v` ran349 in331.958s:341 distinct
passes and exactly the same eight native-host limitations, no skips; it printed
`FAILED (failures=2, errors=9)` (duplicate cleanup error records included).
All258 guest commands/258 serial wrappers parsed without stderr;233 embedded
Python snippets,12 shell files and45 Python files compiled. `git diff --check`
and frozen-path comparisons passed. Pinned gitleaks8.21.2 reported0 findings
over the full existing history and pending files. Logs are under `.work/14/`.

**Privacy classification (integrator, brief14s):** all507 generic-api-key
findings are public third-party file names in the pinned Bazzite ISO's
`evidence/installer/squashfs-files.txt`, held in the private artifact and never
committed. Redacted metadata confirms every finding is in that one listing.
No listing, ignore entry, allowlist, rule or privacy-workflow change is added.
Findings anywhere else remain a STOP; repository privacy remains mandatory.

**Not verified / open gate:** real runner node timing and VM qualification are
not rerun. Tests used stand-ins only; no local devices, privilege or installs.
No push, dispatch, publication or merge. Ledger/budget settings are unchanged
(last actual306/480,9/9 probes,1/2 qualifications). The owner decides paid
Actions budget versus1 November before any resume. No new product judgment
or PLAN-GAP; this implements the integrator's diagnosed CI race fix.

## 14r — Actual probe9 STOP after the one authorized push

**Done / actual authorization:** exactly one fast-forward push advanced
`47f795d072abcef9d9c1173557174b7abd9dd466` to
`22e07b1b6abb6f60da9df9c8646aef414e8589d4`, including the committed14q fix,
probe8 STOP and14q budget STOP, local briefs, and14r's explicit October closing
reservation0. Probe42 and qualification130 bounds stayed fixed. The pinned
full-history and pending-file gitleaks scans had0 findings before this push.
Exact-head privacy40406753823 and40406746890 passed all three checks; personal
terms actually ran. Fresh authorization proved **76/76 complete history,
292+172=464/480,6 org minutes after reservation ≥0**, including the recorded
closing0 decision. Probe9 was sent once, run_attempt1, on that immutable head:
[40407466983](https://github.com/Ares-Empire/AresOS/actions/runs/40407466983).

**Verified natively:** pinned tools and every early capability passed. The
complete native suite passed **341 tests in27.946s, no skips**. The14q real
loop-image regression passed:20 recorded checks, matching independent blkid /
sgdisk / disk_record GUIDs,2 raw lsblk trees,4 findmnt rows,0 helper mutations,
protected fixture unchanged, and all fixture mounts/loops cleaned up. The new
failure-evidence mechanism produced `14-native-owner-devices.json`. Windows
copy, compilation/shell checks and release verification completed. The four
credential-only metadata/manifest, signature and layer-pull checks all passed;
no owner secret or changed credential/scope. Pinned live ISO inspection passed.

**Actual failure:** the next step created disposable50-GiB protected and
49-GiB target file disks. While `owner_vm.main` was creating the separate
virtual ARESTOOLS stick, `owner_media.py:69` stopped:

```text
open failed : /dev/loop0p1, No such file or directory
subprocess.CalledProcessError: Command '['mkfs.exfat', '-L', 'ARESTOOLS',
'/dev/loop0p1']' returned non-zero exit status 255.
```

This was after `sgdisk` and the backing-verified `losetup --partscan` path,
before the FUSE mount/copy/readback/hash and before `Audit` or `live_probe`
were entered. No OS VM started, no virtual tools stick was attached, and no
OS disk/firmware stage audit or installation/keyboard qualification ran.
The earlier native capability smoke VM is a separate passed result. Native
loop/FUSE capabilities are proven; the reason this tools-media partition node
was absent is **not proven** by the retained log. No host-readiness workaround,
filesystem fallback, tool install, code change or rerun was attempted.

**Privacy STOP / retained evidence:** artifact12692287401 was checked against
its API digest before safe extraction:3,023,704 bytes,156 members, SHA256
`f606525a019be5e396cdda73802efa0f753691dee4eeb36515a231fdaa51d7df`.
Private raw receipts/logs remain in `.work/14/run-40407466983/` and the private
run's artifact. Scoped-auth cleanup passed: removed, outside workspace, no
owner token used. No raw artifact or listing is added to Git or made public.

Pinned8.21.2 retained-evidence scanning found **507 generic-api-key findings**,
all in `evidence/installer/squashfs-files.txt`; none in native/failure plaintext
logs. Only redacted rule/file/count metadata was inspected for this report;
no matched values are printed here. This is an unresolved **new-finding STOP**,
not a clean artifact scan. No ignore entry, allowlist, rule or privacy workflow
was changed, and no finding was suppressed or discarded. The clean pre-push
Git-history scan and exact-head privacy are distinct from this artifact result.

**Closed ledger:** **306/480 consumed,0 reserved;77/77 complete history;
9/9 probes,1/2 qualifications;0 publications**. This continuation used21 rounded
minutes (7 privacy +14 probe). Fresh billing showed155 org minutes free.
Cap480, closing0 and org reserve0 remain as approved because acceptance is
unmet; closing12/reserve150 restoration and PR-ready are not authorized. No
qualification2 or second push. The actual STOP report and ledger are local
commit bookkeeping only, with no new hosted action.

**Not verified / PLAN-GAP:** tools-media creation, the full live probe and
qualification2 remain unverified. The missing loop partition node and the
507 listing findings need integrator review before a correction or any new
allowance; none was made here. Every existing protected-disk, firmware,
BootNext, Windows-first, detached-device and privacy rule remains intact.
Owner tools/fingerprint, frozen image/release/runtime, INSTALL, EMERGENCY and
release gate are unchanged. No real laptop, other worktree, image build,
publication or merge. Physical/followability gates stay open.

**JUDGMENT-CALL / open questions:** no new product decision.14r only deferred
closing privacy reservation; it does not authorize ignoring findings or merging
before privacy passes. Native evidence is retained for review; acceptance is
not met and probe9 is exhausted.

## 14r — October closing reservation0; pre-dispatch preparation

**Done:** package14 now records closing_privacy_reservation with minutes0,
normal12, exception month2026-10 and the exact14r decision path. The local
reservation helper derives **178 before push,172 before probe,130 before
qualification**; push6, probe42 and qualification130 are unchanged. A host
dispatch guard requires the complete derived bound and records its plan in
authorization evidence. Zero closing outside October, an altered decision or
an incomplete reservation refuses. Tests also prove restoration to12 yields
the normal190/184/142 plan. Package13 text is unchanged; cap480,9 probes,
2 qualifications and org reserve0 remain as approved in14q.

The14q fixture fix and probe8 STOP are already committed locally and will
accompany the sole fast-forward push. Owner tools, bundle fingerprint,
workflows/permissions, frozen release/runtime and privacy rules are unchanged.
No image build, publication, token/scope change, pull or other-worktree action.

**Verified locally:**341 whole-suite tests ran:333 distinct passes, exactly the
same eight native-host limitations, no skips (unittest exit1).104 host-walk
tests passed, including the real low-level PART_ENTRY_UUID fixture, independent
GUID cross-check and failure-evidence cases, and all reservation/refusal tests.
The focused guard/API-permission suite passed12 tests. Strict parsing passed
258 guest commands and258 serial wrappers with no stderr,233 embedded Python
snippets,12 shell files and45 CI/overlay/owner Python files. Windows copy passed
15 zero-write refusals and exact bundle equality; current fingerprint:
`ef9cb33c7d08ff2be02e0b2fd62efb58dee9028963d66774422f5434b1168112`.

Actual14e/14f git/file/read-only release replay,53 retained offline sources
and the complete listing passed. Actual ISO inspection rehashed9,068,650,496
bytes, checked the fresh publisher checksum, and read4 localization/102 WebUI
sources. The four credential-only checks remain mandatory, fail-closed in CI.
Evidence and refreshed source bindings: `os/manifest/ci/14/14r-preflight/`.

Fresh pre-push planning: **74/74 complete history;285+178=463/480**;
**9 org minutes after reservation ≥0**. This is planning, not dispatch
authorization. Pinned full-history gitleaks must be0 before the sole push.
Then exact-head privacy must actually execute all three checks, followed by
fresh complete ledger/billing and the172-minute guard for probe9. Only its
success, including the real native loop fixture, permits qualification2 on
the same immutable head, behind its own local replay and130-minute guard.
No second push before qualification finishes. Any refusal/failure stops work,
with no rerun or smaller bound.

**Closing privacy / merge gate:** closing checks run after qualification;
if October minutes are exhausted, they wait/run again on1 November. They
remain required before any merge. Only VM acceptance permits a final commit
restoring closing reservation12 and org reserve150, plus PR-ready. No merge
is authorized. Physical/followability release gates remain open and the
product remains NOT RELEASED.

**Not verified / PLAN-GAP / JUDGMENT-CALL / open questions:** hosted native
GUID check, probe9 and qualification2 remain pending. No new product choice;
the explicit integrator14r decision changes only the closing reservation.

## 14q — Fixture PART_ENTRY_UUID fix; organization budget STOP

**Done:** the retained probe8 traceback is consistent with the integrator's
wrong-tag diagnosis; it contains no raw GUID/firmware values contradicting it.
Changed only the native fixture in `os/ci/owner_devices.py`: read
`blkid -p -s PART_ENTRY_UUID -o value <loop>p1`, cross-check against
`sgdisk -i 1 <target-image>`'s Partition unique GUID case-insensitively, and
require a full nonempty GUID. A bad or mismatched value stops with both shown.
No change to owner tools, their firmware predicate, bundle or fingerprint:
`ef9cb33c7d08ff2be02e0b2fd62efb58dee9028963d66774422f5434b1168112`.

The fixture's evidence file is updated before checks and real-helper calls,
including on failure: raw lsblk JSON/trees, native findmnt rows, independent
GUID commands/output, expected GUID, synthetic firmware line and the GUID
resolved by disk_record. Return values and cleanup checks are retained too.
Recorded source rows are copied before fixture-only root identity adaptations.
Subsequent media queries cannot erase the already resolved disk_record GUID.

The local stand-in now honors the requested lsblk columns and exact blkid tag;
it returns no GUID for the old PARTUUID low-level query. A real low-level output
line containing PART_ENTRY_UUID and no PARTUUID is retained with provenance
from [the upstream util-linux report](https://github.com/util-linux/util-linux/issues/1159).
It is a GPT NTFS partition used only for tag/GUID parsing, not a claimed EFI
capture. The runner's upstream2.39.3
[partition-tag implementation](https://github.com/util-linux/util-linux/blob/v2.39.3/libblkid/src/partitions/partitions.c)
uses PART_ENTRY_UUID as well. Native EFI type checking remains unchanged.

Only package14's settings changed to **cap480,9 probes,2 qualifications,
reserve0**. Package13 text is unchanged. The budget regression still refuses
481 after accepting480, and refuses a tenth probe after counting nine.
No workflow/permissions, owner script, image, frozen release/runtime, privacy
rule or ignore changed. No pull or other worktree/real laptop operation.

**Verified:** `PYTHONPATH=os/tests python3 -m unittest
 test_owner_devices_native test_owner_guard -v` passed **15 tests in10.914s,
no skips**. Coverage includes the real tag output and value-only output, empty /
invalid / mismatched GUIDs, uppercase sgdisk agreement, failure before helpers,
raw evidence on a firmware/shape refusal, and cleanup. All device/privileged
commands were stand-ins; no real local mount, device query or installation.
`git diff --check` passed. Git comparisons confirmed unchanged owner tools,
release scripts, workflows, privacy rules and frozen runtime/release paths.
Pinned local gitleaks8.21.2 is required clean before the local commit.

**Actual STOP / budget:** the initial complete guard read **74/74 history**.
The package fits: **285+190=475/480**. The organization guard refused:

```text
STOP: organization has 187 free minutes; 190 reserved must leave 0
```

The full190 is push6 + probe42 + qualification130 + closing privacy12. No
margin or bound was reduced and no authorization retry was made. A separate
zero-reservation bookkeeping snapshot confirmed **285/480 consumed,0 reserved;
8/9 probes,1/2 qualifications,0 publications**,74/74 history and187 org minutes
free. That snapshot is not dispatch authorization. Evidence and source bindings:
`os/manifest/ci/14/14q-stop/`; BUDGET contains the closed actual ledger.

**Not verified / next gate:** stopped before the whole local suite, refreshed
host stage walk/current walk bindings,14e/14f replay and14i strict composed-
command checks. The existing14p walk is historical and is not proof for this
changed fixture. These checks, pinned privacy, fresh exact-head CI privacy and
the complete ledger/billing guard must pass on resume before the sole probe9
and same-head qualification2. Native GUID cross-check and failure-evidence
behavior have not run on a disposable runner. No current VM acceptance.
The remaining verification/dispatch work waits for November per14q; no rerun
or push was made after refusal. Reserve0 is not restored to150 and PR #13 is
not ready because acceptance is unmet. INSTALL/EMERGENCY/release gate remain
unchanged and truthful; physical/followability checks stay open.

**JUDGMENT-CALL / PLAN-GAP / open questions:** no product decision or alternate
cause guessed. The approved plan is short of organization minutes by3. Nothing
is scheduled automatically; resume requires the permitted fresh checks.

## 14p — Actual probe8 STOP (after the one authorized push)

**Done:** committed the probe7 STOP report together with the step-local mode
fix, all-reader static regression,175 refreshed source bindings and the
approved package14-only460/8/0 settings. Exactly one fast-forward push advanced
`a80cacce5a29c4883e1f0b42e16f4cd860343969` to
`47f795d072abcef9d9c1173557174b7abd9dd466` (including local brief a6bd1bf).
Pinned gitleaks8.21.2 found0 over the complete pushed history and pending files.
Package13's configuration text, owner bundle/fingerprint, frozen runtime and
release are unchanged. No token/scope, privacy rule or permission change.

**Verified / actual hosted evidence:** exact-head privacy runs40400133838
and40400127175 passed all three required checks, with personal terms executed.
The final guard proved complete73/73 history, **271+184=455/460**, and **23
org minutes after reservation ≥0**. Probe8 was dispatched once, attempt1:
[40400763278](https://github.com/Ares-Empire/AresOS/actions/runs/40400763278).

Pinned tools and the early real native capabilities passed. **All333 native
unit tests passed in25.639 seconds, no skips.** The new static test ran with
them. `owner_devices.py` passed its mode guard, entered `prove`, created the
scratch partitioned loop fixtures and FAT/exFAT filesystems, and reached the
real `owner.disk_record`. It then stopped at `owner.py:437`:

```text
owner_owner.Stop: Linux firmware entry does not uniquely map to target EFI
```

The helper required exactly one matching synthetic firmware entry; that check
was preserved. The traceback is at `owner_devices.py:107`, before media.find,
protected-fixture final proof and the success JSON. The artifact contains no
`14-native-owner-devices.json`. The observed native PARTUUID and generated
synthetic firmware line were not exported before this assertion, so the raw
mismatch and its underlying cause are **not proven** by retained evidence.
Local stand-ins supplied a nonempty GUID; they did not reproduce this native
failure. No helper, fixture, audit or workflow was changed after the stop.

The rest of the native step (Windows-copy invocation, compile/shell checks,
release verification), private metadata/digest/signature/pull checks, CI ISO
inspection and the OS installer/owner-tools VM rehearsal were not reached.
The separate capability smoke VM passed; that is not an OS qualification.
Qualification2 was not dispatched. Local release/source/ISO/strict replay
also passed for a possible qualification, but cannot replace its hosted gate.

**Retained evidence / privacy:** artifact12688678736 was checked against its
API digest before safe extraction:48,087 bytes,17 members, SHA256
`f7a84d569a3e6b19d381164b61d675b411c3265e55bc736f900be0fcca38af73`.
Raw receipts and logs are under `.work/14/run-40400763278/`; the private run
retains the artifact. Scoped credential cleanup passed (removed, outside
workspace, no owner token). No loop-cleanup error appears in the traceback,
but there is no completed native-loop success proof. Pinned scans of retained
evidence/logs found0. No local privileged operation or device test was run.

**Closed ledger:** **285/460 consumed,0 reserved;74/74 complete history;
8/8 probes;1/2 qualifications;0 publications**. This continuation cost20
rounded minutes:6 privacy plus14 probe. Fresh billing reported190 org minutes
free. The approved cap460/reserve0 and allowances8/2 remain; acceptance was
not met, so reserve150 restoration and PR-ready are not authorized. No second
push, rerun, image build, release/publication, merge, real laptop or other
worktree operation. BUDGET and this actual STOP report remain local/uncommitted
because no further push is authorized before qualification finishes.

**Not verified / PLAN-GAP:** the native loop fixture failed its firmware
mapping check, so native-loop acceptance and every later hosted/VM stage are
unproven. Any correction or additional probe requires a new integrator/owner
decision; none was attempted. The second qualification and physical laptop /
followability release-gate checks remain open. INSTALL, EMERGENCY and the
release gate were not changed or relaxed.

**JUDGMENT-CALL / open questions:** no new product decision. Probe8 is exhausted;
the firmware fixture mismatch needs review before any resumed execution.

## 14p — Step-local mode binding and October allowance (pre-dispatch)

**Done:** the native qualification step now explicitly declares
`REHEARSAL_MODE: ${{ inputs.rehearsal }}`. Its exact
`sudo -E env -u GH_TOKEN python3 os/ci/owner_devices.py` remains unchanged.
The static YAML/AST regression discovers all CI scripts that read the variable
and requires a nonempty step-local env binding at every direct invocation.
Four other missing bindings (tool resolve and credential cleanup calls) are
explicit too; commands, permissions and cleanup behavior are unchanged.
Negative cases remove each binding, including with inherited job/global env,
refuse invalid values, and discover newly added Python and shell readers.

Only package14's settings changed: **460 minutes,8 probes,2 qualifications,
org reserve0**. Package13 text is unchanged. No owner payload, image, release,
credential, privacy rule or frozen runtime change. Current bundle fingerprint:
`ef9cb33c7d08ff2be02e0b2fd62efb58dee9028963d66774422f5434b1168112`.

**Verified locally:**333 whole-suite tests:325 passed, the same eight documented
native-host limitations, no skips (exit1).96 host-walk tests passed, including
four new mode tests and the exact460/461 and eighth/ninth-probe guard checks.
All258 guest commands and258 serial wrappers passed strict real bash parsing;
233 embedded Python snippets,12 shell files and45 CI/overlay/owner Python
files parsed. Windows copy passed15 zero-write refusals and source equality.
Actual release git/file/read-only gh replay,53 retained offline sources and
full listing passed. The actual ISO inspector rehashed all9,068,650,496 bytes,
fresh publisher checksum,4 localization and102 WebUI sources. Four credential-
only checks remain fail-closed in CI. Evidence and bindings:
`os/manifest/ci/14/14p-preflight/`.

Fresh pre-push planning: complete71/71 history; **265+190=455/460**
(push6, probe42, qualification130, closing privacy12). Billing left
**23 minutes after that bound**, against reserve0. This is planning;
exact-head privacy (all three checks actually run), complete ledger and billing
must pass freshly before the sole probe8 POST. Only a successful probe with
the real14n loop-query test permits qualification2 on the same head, behind
its own142-minute guard and fresh local replay. Exactly one fast-forward push
is authorized before dispatch; no additional push before qualification finishes.

**Not verified / stop:** hosted native suite, loop-query execution, probe8 and
qualification2 pending. Any guard refusal, run failure or minute exhaustion
means STOP/report, no rerun or lower limit; remaining work waits for a new
owner decision. Acceptance alone permits reserve150 restoration and PR ready.
The physical laptop/followability release gate remains open. No real laptop,
other worktree, image build or publication was touched.

**JUDGMENT-CALL / PLAN-GAP / open questions:** owner14p authorizes use of all
remaining October minutes. The probe7 environment gap is fixed as directed;
no further product decision. Physical release-gate checks remain required.

## 14o — Actual probe7 STOP (local report after the one push)

### Done / actual evidence

Exactly one fast-forward push advanced `5156f5f` to
`a80cacce5a29c4883e1f0b42e16f4cd860343969`, including all local14m/14n work
and14o limits440/7/20. Package13 is unchanged. Pinned gitleaks8.21.2 found0
over the complete pushed history. Exact-head privacy runs40394908641 and
40394899036 passed all three checks; personal terms actually executed.

The fresh guard proved complete70/70 history, **254+184=438/440** and **35
org minutes after reservation ≥20**. Probe7 was dispatched once, first attempt:
[40395477901](https://github.com/Ares-Empire/AresOS/actions/runs/40395477901).

Pinned tool installation passed with the approved20-minute step and retry3.
The early native capabilities passed real loop/FUSE exFAT rw/ro/fsck, fixture
tools, QEMU/OVMF/QMP, hotplug, serial/network/screenshot/keyboard checks on the
disposable runner. The native regression suite then passed **all329 tests in
23.682 seconds, no skips**. The preflight step stopped immediately afterwards
at `os/ci/owner_devices.py:128`:

```text
assert os.environ.get('REHEARSAL_MODE') in ('probe','owner-tools')
AssertionError
```

The new14n loop-query test did not enter `prove` or create its loop images.
Its entry point requires REHEARSAL_MODE, while **Qualify tools, regressions,
rewritten release identity and private access** declares only GH_TOKEN. The
adjacent capability/reservation steps' REHEARSAL_MODE values are step-scoped.
`sudo -E` cannot preserve a value absent from this step. No guard was weakened,
environment binding fixed or run repeated after this failure.

The remaining commands in that native step (Windows-copy invocation, compile /
shell checks and release verification), later registry/signature/pull checks,
CI ISO inspection and the OS installer/owner-tools VM rehearsal were not
reached. The native capability smoke VM is a separate result; no Linux
installation, keyboard, disk/firmware qualification or owner-tool success is
claimed from this attempt. Qualification2 was never dispatched.

### Privacy / closed ledger / not verified

Failure artifact12686612427 was verified against the API before extraction:
47,843 bytes,17 members, SHA256
`97a40a08ffcd5581e152e5e20322b38e4fbae54ef66b258ece876ee309e4e381`.
Raw receipts/logs remain under `.work/14/run-40395477901/`; the private run
retains the artifact. Scoped-auth cleanup passed: outside workspace, removed,
no owner token used. Both retained-evidence/log directory scans found0.

Fresh closed actuals: **265/440 consumed,0 reserved;71/71 complete history;
7/7 probes,1/2 qualifications;0 publications**. This continuation cost16
rounded minutes:5 for the only push's privacy and11 for probe7. Fresh billing
reported **214 org minutes free**. Reserve20, cap440 and allowances7/2 stay
as authorized; acceptance was not met, so reserve150/PR-ready closure is not
authorized. No second push. The local STOP report and BUDGET are deliberately
uncommitted/unpushed, preserving the no-more-push rule while qualification has
not finished. No image/release/publication, real laptop or other worktree action.

Pre-dispatch local evidence remains:329 discovery/321 passes with the same
eight host limits,92 host-walk tests,4 exact-budget regressions,2 regenerated
manifest/equality checks,258+258 strict guest/serial parses,15 zero-write
Windows refusals and actual release/source/ISO replay. These prerequisites do
not replace the unexecuted native loop query or VM qualification.

**PLAN-GAP:**14n's native invocation omitted the required step environment.
The local stand-in walk covered `prove` and the local-refusal guard, but did
not positively execute the exact workflow invocation with its declared
environment. An integrator decision is needed before a binding/regression fix
and any new probe allowance; no corrective change or rerun was made here.

**JUDGMENT-CALL / open questions:** no new product decision. Native loop-query,
full VM acceptance and all physical/followability release gates remain open.

## 14o — Run now: cap440, probe7, org reserve20 (pre-dispatch planning)

**Done:** applied exactly the three package14 settings approved in
`briefs/14o-run-now.md`: cap440,7 probes,2 qualifications and org reserve20.
Package13 is byte-for-byte unchanged. Refreshed the budget regression's literal
binding:440 succeeds,441 refuses, seven probes count and the eighth refuses.
The first local run caught its stale420/6/60 expectations; no guard algorithm,
assertion or refusal was removed. Owner tools/native14n loop test,14m download
controls, workflows/permissions, frozen runtime/release and privacy rules are
unchanged from the local14m/14n work. All unpublished14m/14n commits accompany
this one push; no pull, force push, merge, image build or publication.

**Verified locally:**329-test whole suite has321 passes and exactly the same
eight native-host limitations, no skips (unittest exit1);92 host-walk tests
passed; all4 updated budget regressions passed. Strict parsing passed258
guest scripts and258 serial wrappers,233 embedded Python snippets,12 shell
files and45 CI/overlay/owner Python files. Windows copy passed15 zero-write
refusals and source/copy equality with the current fingerprint.

Actual14e/14f release git/file/read-only gh replay and53 retained offline
sources/full listing passed. Actual ISO inspector rehashed all9,068,650,496
bytes against the pin plus fresh publisher checksum and read4 localization /
102 WebUI sources. Four credential-only checks stay CI-only and fail-closed;
no scope/credential change or owner secret. Raw commands/logs are retained in
`os/manifest/ci/14/14o-preflight/`; native and VM results remain pending.

Fresh pre-push planning proved complete68/68 history: **249+190=439/440**
(push6 + probe42 + qualification130 + closing privacy12). Fresh billing had
**223 free;33 after reservation ≥20**. This receipt is planning, not dispatch
authorization. The same immutable head must pass exact-head privacy's three
checks, fresh complete ledger/billing and the184-minute guard before the sole
probe7 POST. Only a successful probe including14n's native loop test can
authorize qualification2, with its own fresh142-minute guard and local replay.

**Not verified / stop:** actual native loop execution, probe7 and qualification2
are not run at this planning commit. A guard refusal or stopped hosted run
means STOP/report, no rerun, no lower limit and no additional push while the
qualification has not finished. Acceptance alone permits a final reserve150
commit and PR-ready transition. Physical laptop/followability release gates
remain open. No real laptop or other worktree has been touched.

**JUDGMENT-CALL / PLAN-GAP / open questions:** owner decision14o explicitly
replaces the November wait and reserve margin; no additional product choice.

## 14n — Council delta: explicit disk trees and exact PASS actions

**Done:** `media.block_tree` requests `lsblk --json --tree` for both real
helpers. It rejects flat/orphan partitions, repeated paths/parents, nested
disk roots, missing/non-list mountpoints and malformed children. It never
guesses ancestry. `disk_record` and install use `findmnt --json --list` with
one validated filesystem row and exact mountpoint identity. The full
[payload JSON audit](14n-json-audit.md) covers findmnt, sfdisk, rpm-ostree,
bootc, busctl and loginctl; no other tree/list mismatch was found. Shared
release scripts and frozen runtime/release paths remain unchanged.

The real entry point prints the whole action, including `PASS layout begin
us-intl`, `PASS layout proof`, `PASS layout revert` and `PASS layout finish`.
INSTALL documents all19 exact PASS lines. The regenerated payload, hash-first
manifest, guide and Windows copy agree on the current fingerprint above.
Archived pre14n fingerprints remain accurate historical receipts and are
explicitly superseded, inventoried in `14n-replay/fingerprint-references.json`.
Implementation/tests/guide/audit are committed locally as `8eab7f6`.

**Verified locally:**

- `PYTHONPATH=os/tests python3 -m unittest test_owner_devices test_owner_entry test_owner_export test_owner_devices_native -v` under existing WSL: **16 passed**. Real disk/media helpers and install pass realistic tree JSON; flat/malformed JSON STOP clearly. Mounted protected child and two labels refuse with identical fixture files, no installed directory, no subprocess mutations. Real bundled `owner.main` runs for every commands.json action; handler stand-ins keep it nonprivileged, and all19 actual PASS lines equal the guide. The full native host flow and failure/cleanup paths run through closed stand-ins.
- `wsl.exe bash .work/14/local/whole-suite.sh`: **329 tests;321 passed**, exactly the same eight host limitations, no skips; unittest exit1, failures2/errors9 including cleanup duplicates. Pillow accounts for3, refused privileged Homebrew/sysusers operations4, and DrvFS0600 semantics1. This is not a native-suite pass.
- `python3 reviews/14-owner-tools/walk-host.py` under WSL: **92 passed**; every composed guest command is strictly parsed. `python3 .work/14/14n-syntax.py`: **258 guest +258 serial scripts**,233 embedded Python,12 CI/release shells and45 CI/overlay/owner Python files passed; parse stderr, including warnings, refuses.
- `python -X utf8 .work/14/14n-read-only-replay.py`: actual release git/file/read-only gh checks and53 offline sources/full listing passed. Four14f credential-only checks remain CI-only, unchanged and fail-closed; no credential/scope change or owner secret.
- `python -X utf8 .work/14/14n-installer-windows.py`: all9,068,650,496 ISO bytes rehashed against the pin and fresh publisher checksum;4 localization and102 WebUI sources; actual inspector assertions unchanged.
- `pwsh -NoProfile -File os/tests/owner-tools.Tests.ps1 -Bundle os/owner-tools/payload -Work .work/14/14n-unit-copy`: **15 zero-write refusals passed** and copied payload equals source, with the new fingerprint.
- Post-retention `test_owner_equality` manifest-order and reviewed/generated-payload checks: **2 passed**.
- Frozen runtime/release/shared scripts, package pins,14m retry/timeouts, budget configuration, guard, release binding and privacy-rule comparisons against `cc11494` pass. `git diff --check` passes. Pinned gitleaks8.21.2 reports **0 full-history findings** through implementation commit `8eab7f6`; pending evidence is scanned before this local report commit, and the final history is scanned afterwards.

The first direct-install fixtures wrote Python bytecode into the copied bundle
because their interpreter lacked the shipped launcher's `-B` flag. Fixtures
now use that flag's `dont_write_bytecode` setting; all content/zero-write
assertions are retained and pass. Product guards were not bypassed to fix A.

**Not verified / stop:** actual partitioned-loop execution is deferred to the
mandatory native step in the November probe and qualification. It uses only
fresh runner files/verified loops, EFI-type FAT plus exFAT ARESTOOLS, exact
query options and the real helpers. Its documented adapters supply loop root
hardware identities, sandbox mount paths and a synthetic firmware read;
they preserve native tree/partition structure. Protected fixture hashes and
confirmed unmount/detach are required. No actual local device, mount, package
installation, firmware or laptop operation was run. Native/VM acceptance and
all physical release gates remain open; a native failure is STOP/no rerun.

Ledger unchanged: **249/420**,0 reserved,6/6 probes,1/2 qualifications,
reserve60; **zero additional Actions minutes**. No image rebuild, release or
publication. Await explicit owner resume on/after1November, restore reserve150
and set the cap/allowance then, followed by one push, fresh exact-head privacy,
complete ledger/billing, probe7 and qualification2 on the same head/bundle.

**JUDGMENT-CALL / PLAN-GAP / open questions:** no new product decision or
unresolved gap. Native loop adapters are test boundaries, not physical-device
evidence. Historical fingerprints were preserved rather than falsifying old
qualification receipts. November execution remains pending owner resume.

## 14m — Bounded snapshot download retries; November hold

### Done

Only the rehearsal step **Install pinned rehearsal tools on disposable
runner** changes from10 to20 minutes in `.github/workflows/os-image.yml`.
Its apt install gets `-o Acquire::Retries=3`. The same option joins the shared
APT options in `os/ci/install-tools.sh`, covering the update, exact-version
install, reinstall, source prerequisites and edk2 source download. `set -euo
pipefail`, candidate equality and all original failure checks remain.

An exact comparison against `f0d2e22` proves these are the only implementation
changes. Job timeouts remain40/130 minutes. The dated snapshot, suites, signed
indexes, every package/version and order, frozen runtime, owner scripts,
release payload, workflow permissions and privacy rules are unchanged.

Fresh evidence and hash-first source bindings are retained under
`os/manifest/ci/14/14m-replay/`; active host-walk evidence was regenerated.
Historical14j/14k/14l evidence has not been rewritten.

### Verified locally

| Command | Actual result |
| --- | --- |
| `wsl.exe bash -c 'cd /mnt/c/Users/pab/AresOS-14-owner-tools && python3 .work/14/14m-apt-regression.py'` | Four tests passed. Real workflow/install Bash text runs only repo-local shims: all six apt invocations receive exactly3 retries; all six injected failures preserve exit73 and stop without a shell rerun; wrong candidate refuses before install. Exact change scope, pins and packages match. |
| `wsl.exe bash .work/14/local/whole-suite.sh` | Discovery315;307 passed, eight unchanged local-host limitations; no skips. Unittest exit1, failures2/error records9 including cleanup duplicates. This is not a native-suite pass. |
| `wsl.exe bash -c 'cd /mnt/c/Users/pab/AresOS-14-owner-tools && python3 reviews/14-owner-tools/walk-host.py'` | 78 tests passed; no stick across reboot; no VM started. |
| `wsl.exe bash -c 'cd /mnt/c/Users/pab/AresOS-14-owner-tools && python3 .work/14/14m-syntax.py'` | Strict real Bash parsing:258 guest commands and258 serial wrappers, no stdout/stderr warnings accepted;233 embedded Python snippets,12 CI/release shells and44 CI/overlay/owner Python files passed. |
| `python -X utf8 .work/14/14m-read-only-replay.py` | Actual14e release verifier passed all git/file/read-only gh checks;53 retained offline sources and full ISO listing passed14b. Four14f CI-only checks remain explicitly classified and fail-closed, without changing credentials/scopes or using owner secrets. |
| `python -X utf8 .work/14/14m-installer-windows.py` | Actual inspector rehashed all9,068,650,496 retained ISO bytes and verified the pin plus fresh publisher checksum;4 localization and102 WebUI sources. Existing Windows tar / WSL unsquashfs adapters only; no inspector assertion changed. |
| `pwsh -NoProfile -File os/tests/owner-tools.Tests.ps1 -Bundle os/owner-tools/payload -Work .work/14/14m-unit-copy` | All15 destination refusals had zero writes; copied payload equals source; manifest fingerprint unchanged. |
| `git diff --exit-code f0d2e22 -- os/ci/toolchain.json os/ci/rehearsal-packages.json os/owner-tools os/release .gitleaksignore .gitleaks.toml .github/workflows/privacy.yml` and the frozen eight-path/runtime comparison against `775be05` | Passed. `git diff --check` passed. |

The eight local limitations are unchanged: three require Pillow, four require
privileged Homebrew/sysusers operations that the local denial shim refuses,
and one requires0600 semantics unavailable on DrvFS. Exact test names and
results are retained in `14m-replay/replay.json`; no skip or assertion changed.
The download fixture's first scope check used Linux Git against this Windows
worktree and failed on its Windows gitdir spelling. Using the existing Windows
Git fixed that fixture boundary; all four tests then passed without changing
any assertion or product code. No system software was installed.

Pinned local gitleaks8.21.2 (verified binary fingerprint) returned0 findings
over the full history including STOP commit `734c11b`. Pending retained changes
are scanned before the local implementation/report commit; the committed
history is scanned again afterwards. Scanner receipts stay under
`.work/14/gitleaks/14m-*`. No ignore entry, rule or workflow is changed.

### Budget / stop / not verified

The closed ledger remains **249/420 minutes**,0 reserved,6/6 probes and1/2
qualifications, with reserve60 unchanged. This local follow-up incurs **zero
Actions minutes**. Billing and exact-head CI privacy in the ledger are
historical14l receipts, not authorization for this changed head. No fresh
guard, native CI, probe7 or qualification2 was dispatched, and no acceptance
or physical-laptop result is claimed. The 184-minute complete-run bound stays
unchanged because the job timeouts did not change.

Per14m, wait for the owner to resume on/after1November. Then restore reserve150,
set a package cap covering the new bound, and require the fresh local replay,
pinned full-history privacy scan, single push, exact-head CI privacy, complete
ledger and billing before probe7 and qualification2 on the same head. Those
allowance/configuration changes have not been made prematurely. No rerun of
probe6 and no push before1November. No image, release, publication, firmware
audit, owner-tool or physical-laptop change was made.

**JUDGMENT-CALL / PLAN-GAP / open questions:** no new product decision or gap.
VM acceptance and the existing physical release gates remain pending. The
November execution requires the owner's explicit resume described in14m.

## 14l — Actual probe6 STOP (local report after the single push)

### Done / verified

The single commit `5156f5fac592e1e30077b22c196124a1feaafe89` contains the brief,
420/60 settings, unchanged6/2 allowances, refreshed162 source/65 host bindings,
ledger and planning REPORT. Pinned gitleaks8.21.2 scanned its full history with
**0 findings** before the one fast-forward push. Package13 and all frozen
runtime/owner-tool/workflow/privacy paths are unchanged.

Actual local replay passed: release run/git/file binding,53 offline sources
and full listing, all9,068,650,496 ISO bytes against the pin and fresh checksum,
4 localization/102 WebUI sources,258 guest scripts +258 serial wrappers under
strict Bash parsing, and15 zero-write Windows copy refusals. Local host walk
passed78 tests; local discovery passed307/315 with the same eight native-host
limitations, no skips. Prospective qualification local replay also passed,
but did not authorize a VM or substitute for the failed probe.

Both exact-head privacy jobs completed all three checks, with personal terms
actually executed, before probe creation:40362011848 and40362028134. Fresh
guard authorization proved complete67/67 history and **236 +184 =420**, org
**66 after reservation ≥60**. Probe6 was dispatched exactly once on this head:
[40363137526](https://github.com/Ares-Empire/AresOS/actions/runs/40363137526).

The step **Install pinned rehearsal tools on disposable runner** started at
16:54:06Z and completed as failure at17:04:19Z (613 seconds). Its final error:

```text
The action 'Install pinned rehearsal tools on disposable runner' has timed out after 10 minutes.
```

APT was still downloading pinned Ubuntu snapshot packages at
`snapshot.ubuntu.com/ubuntu/20261021T000000Z`; the last reported download was
`ovmf`. Native capabilities, the full native regression preflight, all four
CI-only registry checks, CI ISO inspection and VM/file-disk preparation were
skipped. This was not a keyboard/firmware result. No guest existed in this
attempt, so no protected-disk/NVRAM/BootNext/keyboard result is claimed.

The four-member failure artifact was downloaded and its API digest verified
before inspection: artifact12670770044,5936 bytes, SHA256
`24e8a6c80b0146a5e0003dc6bc4b5ec0e108ba8c6e70d4f4dc3a045728eb6dbe`.
It contains the two budget/native-pending receipts, partial toolchain package
list and scoped-auth cleanup. Cleanup passed: outside workspace, removed,
owner token not used. Pinned gitleaks on retained failure evidence:0 findings.
The complete run/jobs/log/artifact receipts stay under
`.work/14/run-40363137526/`; no credential or scope was changed.

### Closed ledger / cap note

Fresh complete **68/68** history: **249/420 consumed,0 reserved**; probe6 cost
**13 rounded minutes**, the single push's privacy cost6, total14l cost19.
Dispatch counters are **6/6 probes,1/2 qualifications**, publication attempts0.
Fresh billing read shows **247 org minutes free**. See local
`.work/14/final-14l-stop-ledger.json`; the committed230+190 ledger is explicitly
the pre-push planning snapshot, not the closed result.

### Not verified / PLAN-GAP / JUDGMENT-CALL / open questions

**Stop and report, no rerun.** Qualification2 was not dispatched because the
required same-head probe failed. No remaining probe allowance is inferred;
the unused qualification cannot bypass the probe. No timeout, mirror, package,
audit, cap or reserve was changed after the stop. No image or real-device work
occurred, and nothing was made public or merged.

**PLAN-GAP:** the pinned runner package download did not finish inside its
existing10-minute step limit. Any remedy or new attempt requires a new owner
decision; none was implemented. Acceptance is unmet, so reserve60 and cap420
remain as explicitly requested; the acceptance-conditioned reserve150/final
cap-note commit and PR-ready action were not performed. Physical/novice gates
stay OPEN / NOT RELEASED. No new product judgment was made.

The actual report and closed BUDGET are local modifications, with authoritative
run details also on PR #13. They are deliberately not committed/pushed: the
owner prohibited another push before qualification finishes, and no
qualification started. No Gradle process was started or left running.

## 14l — Planning record in the single pushed commit

**Pre-dispatch 14l status: owner's October margin decision recorded; one
pre-dispatch commit/push, then fresh replay/privacy/budget gates.** Package14
alone uses cap420 and org reserve60; allowances stay6 probes/2 qualifications.
No new VM acceptance is claimed by this planning commit. PR #13 remains draft
and physical installation NOT RELEASED until the appropriate gates close.

## 14l — One October push, then guarded probe6 and qualification2

### Done / owner decision

The owner decided on2026-10-26 to proceed in October: package14 only changes
cap400→420 and org reserve80→60. Probe allowance6 and owner-tools2 stay
unchanged; package13 and every other setting stay unchanged. Recorded the
decision in [`14l-october-margin.md`](../../briefs/14l-october-margin.md).
Updated the guard regression's exact cap/refusal boundary to420/421 and its
package14 reserve expectation to60; seven probes remain refused. No runtime,
owner tool, frozen release path, workflow permission or privacy rule changed.

The decision, settings, tests, active source bindings, ledger and this REPORT
are one commit and exactly one fast-forward push before dispatch. The final
commit's pinned full-history gitleaks8.21.2 receipt will be retained locally
and on PR #13, without a second receipt commit/push. No further push is allowed
before qualification finishes. A STOP is reported without rerunning a job or
lowering a limit; before qualification finishes, live receipts stay local and
in the existing PR rather than causing another push.

### Verified locally before the one push

Local owner host walk: **78/78 tests passed**, no skips. Full local discovery:
**315 tests;307 passed; the same eight native-host limitations**, no skips
(2 failure/9 error records including duplicate cleanup errors): three Pillow
greeter tests, three privileged Homebrew fixtures, sysusers and DrvFS auth-file
mode. No test or local safety restriction was weakened. Fresh source bindings
cover the changed config and guard test; historical receipts stay immutable.

The14e/14f actual read-only release/source/ISO replay and14i strict composed
guest/serial checks run after this push, before dispatch. All four private
registry checks remain explicitly CI-only with their reason and CI step name;
credentials/scopes and fail-closed implementations are unchanged. A fresh
passing exact-head privacy result (all three checks actually executed),
complete history and current billing are required before each dispatch.

### Planning ledger / cap note

The baseline read proves complete **65/65** history, **230 consumed**, **5/6
probes**, **1/2 qualifications**, **0 publications**; fresh org billing shows
**259 free**. The owner's earlier16:30Z observation was251, not reused as a live
authorization. Planning only: **230 +6 one push +184 remaining bound =420**;
org **259−6−184=69**, above60. The184 bound retains42 probe/native +130
qualification +12 closing privacy. Actual costs, not these estimates, decide
the post-push guard; any excess or other org usage can still stop dispatch.

The package ledger never resets. Cap420 is the owner's expanded cumulative
cap for this continuation, not permission for another attempt. Only probe6
may precede qualification2, and both must use the exact same pushed head.
After acceptance restore the org reserve to150 and update this cap/accounting
note with closed actuals in the final commit, then mark PR #13 ready. Never
merge, force-push, publish, widen an audit or touch the real laptop.

### Not verified / PLAN-GAP / JUDGMENT-CALL / open questions

This commit is a planning/local-validation record, not a probe/qualification
result. Fresh native CI and all VM acceptance remain pending. The final gate
will check actual counters, protected captures, NVRAM/BootNext, tools removal,
physical typing/layout/refusal/rollback/export and private-auth cleanup, not
just workflow success. Physical/novice package15 gates remain separately open.
No new product judgment or exception was inferred. If a guard or run stops,
report and stop with no rerun; do not spend the other run on a changed head.

## Prior 14k status

**14k status: STOP — package and organization budget guards refused
the complete required reservation.** Package14's requested400-minute cap,
six-probe allowance and80-minute org reserve are applied; package13 is
unchanged. No probe or qualification was dispatched. PR #13 remains
**draft / NOT RELEASED**.

## 14k — October limits applied; complete-plan budget STOP

### Done

Ran `git pull --ff-only` first: already at `bcf2070`. Read14k, AGENTS, README,
the14j ledger/report and existing guard, tests and replay code. Changed only
package14's `minute_cap`350→400, probe allowance5→6, org reserve150→80.
`owner-tools` remains2. Package13 and every other package setting are unchanged.

Updated the guard regression to accept exactly400 minutes and six probes,
refuse401 and seven probes, and assert package14's80 reserve with package13
still150. The active host-walk bindings and new14k replay bind the current
configuration/test bytes. Historical run/replay receipts remain unchanged.
No owner tool, console fix, frozen release path, workflow permission, privacy
rule/ignore entry, credential or scope changed.

### Verified

- Local owner host walk: **78 tests passed**, no skips. Strict composed-command
  checks passed **258 guest scripts +258 serial wrappers**,233 embedded Python
  programs,12 shell files and44 CI/overlay/owner Python files, refusing parse
  stderr including warnings.
- Full local discovery: **315 tests;307 passed; the same eight native-host
  limitations**, no skips (2 failure/9 error records, including duplicate
  cleanup errors). These remain the three Pillow greeter checks, three
  privileged Homebrew fixtures, sysusers fixture and DrvFS auth-file mode.
  No assertion or local restriction was waived.
- Actual read-only release verifier and offline source replay passed: pinned
  PR-head/squash ancestry, unchanged payload, release run/jobs,53 retained
  sources and complete ISO listing. Four private-registry checks remain
  explicitly CI-only with unchanged fail-closed implementations. No owner
  secret was used. The ISO inspector was **not rerun after the budget STOP**;
  retained14j evidence is labelled historical, not fresh VM qualification.
- Windows copy suite: **15 destination refusals with zero writes**, copied
  payload equal; fingerprint remains
  `118212ec60844043856b5531be95cf2319f9943319679fa6149f999db89bf6ba`.
- A preliminary read-only cost query deferred while the brief commit's normal
  privacy jobs were active. Once they settled, the guard proved complete
  **63/63** run history with all costs settled. The full184-minute reservation
  was checked once; its package and organization checks both refused.

### Guard STOP and ledger

| Item | Settled pre-push value |
|---|---:|
| Package consumed | 224/400 min |
| Complete branch history | 63/63 runs |
| Dispatches spent | 5/6 probes;1/2 qualifications |
| Required remaining plan | 42 probe/native +130 qualification +12 closing =184 min |
| Package after reservation | 408/400;8 over cap |
| Org minutes free | 262 |
| Org after reservation | 78;2 below required80 |
| Image publication attempts | 0 |

Production guard messages:

```text
STOP: 224 + 184 reserved exceeds 400 minutes
STOP: organization has 262 free minutes; 184 reserved must leave 80
```

Evidence: [`14k-ledger/preflight.json`](../../os/manifest/ci/14/14k-ledger/preflight.json)
and [`14k-replay`](../../os/manifest/ci/14/14k-replay/replay.json). This is a
pre-dispatch refusal, not a failed VM run. No smaller reservation was tried;
no workflow was dispatched or rerun. The new head has no passing probe.

The212 baseline in14k predates six minutes of14j closing privacy and six
minutes of privacy for the new brief: actual consumed is224. The committed
ledger therefore reserves **only12 closing/report privacy minutes** after
STOP, not a VM plan:224+12=236≤400,262−12=250≥80. Actual closing receipts/cost
will be recorded on PR #13 after those jobs settle, without another report
push loop. Pinned local gitleaks8.21.2 must report0 over the full history
before every push; no privacy exception is added.

### Not verified / PLAN-GAP / JUDGMENT-CALL / open questions

**Stopped as14k requires.** Probe6, the second qualification, fresh native CI,
private CI-only access checks and new VM acceptance were not run. No full-run
allowance was consumed and no probe result was reused from another head.
Physical installation remains NOT RELEASED. Acceptance is unmet, so PR #13
stays draft and the acceptance-conditioned restoration to150 has not occurred;
the explicitly requested80 stays in package14. Nothing was lowered further.

**PLAN-GAP:** the authorized400/80 limits still cannot cover the complete
hard-bound plan at the settled ledger/billing values. No further budget change
or retry is inferred. Only the owner can authorize a different continuation.
No product judgment, real-device action, image build/publication, merge or
force push occurred. The guide/card's existing unaccepted-route status remains
true; no new owner command or bypass was added.

## Prior 14j status

**14j status: local prompt-resync fix; NO DISPATCH, awaiting the
owner's budget decision.** PR #13 remains **draft / NOT RELEASED**. The
same-head qualification remains incomplete. This run changes no release,
owner tool, workflow, privacy rule, allowance or reserve.

## 14j — Idle-only console resync; stop after push

### Done

Ran `git fetch origin` and `git pull --ff-only` first: already at `2596489`.
Read 14j, the 14i stop/evidence, AGENTS and existing console/typing/walk code.
Only this worktree was used; neither retired worktree nor real laptop devices
were accessed.

`owner_vm.type_text` invalidates the console's completion proof before any
physical typing, including hidden input and the shared keyboard observers.
`Console.prompt` grants idle status only after observing the original strict
cursor-line prompt, with the original three stable samples. A later wait may
send an empty Enter through the same physical key path only if that completion
proof remains valid and the cursor line has no prompt. Input during the wait
revokes the grant before any Enter. Unknown/busy shells, login/input waits and
hidden-password waits never receive resync input. A failed wait invalidates
the completion proof.

The new `owner_console` helper shares the original 90-second wait across at
most three phases and permits at most two empty Enter resyncs. Each attempt
records stage, tty, UTC time, whether Enter was sent, and cursor lines before
and after. The existing prompt predicate and kernel logging are unchanged.
Each expired phase, including the final timeout and hidden-prompt timeout,
retains raw VCSA bytes plus a hash-first file/geometry/cursor record. The JSON
checksum export protocol is unchanged.

Nine local regressions execute the actual composed guest Python reader against
VCSA bytes, with only the `/dev/vcsa3`/`4` read and clock replaced. They cover
one-Enter recovery, busy/unknown shells, input during a wait, typing in another
console, login/input waits, hidden timeout, two-resync exhaustion, an unstable
but already visible prompt, strict three-sample readiness, and malformed VCSA
refusal. Bash parses both each composed command and its real serial wrapper.

The 14i fixture reconstructs the screenshot's exact ASCII root-prompt/kernel
region and cursor at its original **160×50**, **(0,49)** coordinates, using all
17 retained hotplug lines. Its source index binds the screenshot and fixture.
**It is not a raw dump from 14i:** no such dump was retained. Upper MOTD rows
are blank and attributes synthetic, explicitly recorded in the fixture index;
neither affects the predicate. Future timeouts now preserve the actual bytes.

Added the prescribed one-line Enter note to INSTALL's tools-stick step and
both historical "For package 15" lists. Canonical commands, bundle payload,
release paths, owner scripts, firmware/disk audits and stop rules are unchanged.

### Verified

- Console regressions: **9/9 passed**, existing WSL Python/Bash, no installs.
- Final local host walk: **78/78 passed**, no skips; all owner stages remain
  represented by explicit stand-ins, with no stick across reboot.
- Strict composed-command replay: **258 guest scripts +258 serial wrappers**,
  **233 embedded Python programs**, **12 CI/release shell files**, **44
  CI/overlay/owner Python files**; no parse stdout/stderr, including warnings.
- Complete local discovery: **315 tests**, **307 passed**, **8 existing
  native-host limitations**, no skips (2 failure and9 error records, including
  duplicate cleanup errors). The eight affected tests match the retained
  baseline exactly: Pillow-dependent greeter checks (3), privilege-dependent
  Homebrew fixtures (3), sysusers fixture (1), and DrvFS auth-file mode (1).
  No assertion or environment restriction was waived. The full suite was
  repeated after the final unstable-prompt guard was added.
- Exact command/bundle equality and zero-mutation refusals pass in the host
  suite. PowerShell copy tests: **15 destination refusals with zero writes**,
  copied payload equal, fingerprint unchanged
  `118212ec60844043856b5531be95cf2319f9943319679fa6149f999db89bf6ba`.
- Actual read-only `verify_release.py 40154642447`: passed the fetched PR-head
  source ancestry, pinned squash ancestry, release run/jobs and frozen payload
  comparisons. Offline source replay passed all **53 retained files** and the
  full listing. No credential or scope was changed.
- Actual installer inspector replay rehashed all **9,068,650,496 ISO bytes**,
  matched a fresh public checksum, and inspected **4 localization +102 WebUI
  sources**. An initial replay refused its 25-GiB free-space precondition;
  only resolved duplicate ISO/squash caches from the previous replay were
  removed inside this worktree, preserving original ISO and evidence, then the
  fresh replay passed. Windows bsdtar/WSL extraction/path/LF adapters only;
  no CI assertion changed.
- The four 14f CI-only checks remain explicitly classified with their reasons
  and CI step names: org package metadata, registry digest inspect, pinned pull
  and registry signature verification. They were **not run** here and remain
  fail-closed in CI. No native/VM workflow was dispatched.
- Frozen payload, owner bundle/scripts, workflows, privacy policy/ignore files
  and package configuration compare unchanged; `git diff --check` passes.

Hash-first evidence is in
[`14j-replay`](../../os/manifest/ci/14/14j-replay/replay.json) and the updated
[`host-walk`](../../os/manifest/ci/14/host-walk/result.json). These are local
prerequisites, not VM acceptance. Pinned full-history gitleaks8.21.2 must pass
with0 findings before the fast-forward push; the scan receipt is recorded in
the ledger. Normal push/PR privacy is the only hosted CI allowed this run.

### Ledger and both next-resume options

The fresh pre-push snapshot is **212/350 consumed +12 closing privacy
reserved**, complete **59/59** run history, **5/5 probes**, **1/2
qualifications**, **0 publications**. Org billing reports **274 free**. Probe6
must pass on the qualification's exact head; probe5 cannot qualify this fix.
Neither the exhausted probe allowance nor the150 reserve was changed.

| Cost/option | October now, smaller reserve only by owner decision | 1 November, fresh org month |
|---|---:|---:|
| Planned probe6 + qualification | 25 +130 =155 min | same155 min |
| Org free after that plan, before this closing CI | 119 min | 1845 if all2000 unused |
| Org free after plan and12 closing reservation | 107 min | 1833 if those12 fall in November |
| Conservative42 probe/native +130 qualification +12 closing | 184 min;90 free | 1816 free if all2000 unused |
| Package ledger after155, before closing | 367/350 | same367/350; package does not reset |
| Package including12 closing reservation | 379/350 | same379/350 |
| Package with conservative184 reservation | 396/350 | same396/350 |

These are planning bounds, not a dispatch authorization or reservation. The
monthly numbers assume no other org use; fresh complete history, billing and
exact-head privacy checks are still required at the next resume. Closing
actuals/receipts will be recorded on PR #13 after the reserved privacy jobs
settle, without a self-triggering report-push loop.

### Not verified / PLAN-GAP / JUDGMENT-CALL / open questions

**No dispatch in this run.** No fresh native CI, probe6, second qualification,
new guest timeout dump or physical resync is claimed. The eight local host
limitations remain for the next authorized native suite. Physical/novice
installation and package15 gates remain OPEN / NOT RELEASED; PR #13 stays
draft. The earlier VM failure and all its audit receipts remain below.

**Additional budget PLAN-GAP:** waiting for November resets org minutes only.
The package's350 cap is also too small: **212 +155 =367**, already17 over
before closing privacy. The owner therefore needs to settle the package cap
as well as the timing/reserve and fresh probe allowance before continuation.
No cap, reserve, ledger start or accounting rule was relaxed. No new product
judgment was made; the two-resync policy and owner note follow14j exactly.
Stop after the fast-forward push and normal privacy checks; never merge.

## Prior 14i status and retained qualification stop

**14i status: STOP / PLAN-GAP at tty3 prompt readiness after tools
hotplug.** The brace-group fix, all306 native tests and fifth probe passed.
The same-head qualification installed offline, completed hardware setup and
the Windows round trip, then timed out before typing the tools `install`
command. No rerun or second qualification. Snapshot: **203/350 consumed +12
closing privacy reserved**, **5/5 probes**, **1/2 qualifications**, org
**286 free /274 after reservation**. PR #13 stays **draft**; physical
installation stays **NOT RELEASED**.

## 14i — Brace-group guest framing and real Bash execution

**Done:** ran `git pull --ff-only` first, already at `b71de4a`. The only
executable harness change puts the supplied command inside a brace group,
with `{`, the command, and `} > "$result"` on separate lines. `set -e`, the
temporary-file cleanup and the checksum/base64 JSON export are unchanged.
No owner tool, script, frozen runtime, image or workflow permission changed.

Eight new regression tests run the actual `framed()` output in existing WSL
Bash, directly and through the unchanged `encode_command()` serial wrapper.
They cover single-line, multi-line, heredoc-ending with/without trailing
newline, exit7 with no export, and noisy stderr with byte-exact decoded JSON.
The allocation-only `mktemp` shim validates the production `/run` template
and allocates inside the test's ordinary worktree folder; the wrapper itself
is not rewritten. Both success and failure must clean up the temporary file.
Invalid syntax, an unterminated-heredoc warning with exit0, and an invalid
serial wrapper are independently refused.

`guest_shell.syntax` runs real `bash -n` on **both** the composed guest script
and its serial wrapper at each owner/keyboard stand-in boundary. Any stderr,
including warnings with exit0, fails the walk. Shared owner shell steps are
also parsed before their Python/shim adapters run. The owner walk now calls
the real offline-command composer instead of bypassing it; a separate test
checks the live pre-WebUI heredoc. The all-path walk asserts one syntax check
per stubbed command, so a synthetic response cannot silently bypass parsing.

**Verified locally:** the initial updated host walk passed **69 tests in
60.587s**, no skips. The real-Bash framing subset passed **8 in1.877s**.
Whole discovery ran **306 tests in184.337s**, with **298 passed**, the same
eight existing native-host limits, no skips; output was
`FAILED (failures=2, errors=9)`, exit1. The eight are unchanged: three need
absent local Pillow, three inherited-Homebrew and one sysusers fixture are
refused by the no-privilege shim, and DrvFS exposes0777 instead of0600 for
the credential-mode fixture. Cleanup produces extra error records. All306
remain mandatory on the native runner, without skips or waivers.

The actual release verifier again passed the read-only run/jobs requests,
Git fetches, both ancestry checks and both frozen-payload diffs. The actual
9,068,650,496-byte pinned ISO was freshly rehashed and inspected, including
the current public checksum, four localization and102 WebUI source files.
The53-source offline gate and full listing passed. Windows copy again passed
all15 zero-write refusals with the unchanged bundle fingerprint. The four
credential-limited registry checks remain explicitly CI-only under14f and
fail closed in the probe; no credential, scope or owner secret changed.
Final walk/source receipts are retained in `os/manifest/ci/14/14i-replay/`.
The final walk passed **69 tests in62.897s**, with61 source bindings. Strict
replay parsed all258 guest scripts **and** their258 serial wrappers without
any stderr, compiled233 embedded Python programs and43 CI/release/overlay/
owner Python files without writing caches, and parsed all12 CI/release shell
scripts. All157 canonical replay input hashes are retained for Git-blob
comparison before POST.

**Updated stage walk before dispatch:** real Bash framing/strict parsing;
whole/native suites; early loop/FUSE/QEMU capability gate; private checks and
pinned ISO; offline live preview with tools hotplug/removal, detached Windows
and target reset for the probe. On the same head, qualification follows the
unchanged protected-second route: offline install, first-stock hardware
setup/reboot, Windows round trip with tools absent, Linux sign-in/hotplug,
install/prepare/rerun, first network with whole deployment/pin/pending/BLS
invariance, record export/removal, Windows checkpoint, corrected stock and
signed switch, German → plain-US failed fresh login/revert → US International
success → German, rollback/keep-stock and Windows checkpoints. All protected
disk, NVRAM, BootNext, Windows-default and detached-device checks remain.

**Planning ledger:** complete51/51 history, **128 consumed +184 reserved /350**;
**4/5 probes**, **0/2 qualifications**, no image/publication attempts. The184
reserves42 probe/native +130 one qualification +12 closing privacy. Org billing
leaves **177 after reservation**, above150. The optional second qualification
needs its own fresh guard. Before every push, pinned gitleaks8.21.2 must scan
the full history with0 findings; before POST, refresh exact-head privacy,
14e/14f replay, complete ledger and billing. A different blocker means STOP,
with no rerun.

**Not verified:** successful complete owner-tools qualification. Physical
NVIDIA, media, forgotten-stick, laptop and followability gates remain open.
**JUDGMENT-CALL:** none beyond the integrator's prescribed brace grouping.
The14h framing gap is resolved by the actual passing probe below; the new
terminal-readiness gap remains open.

### Actual fresh gates and passing fifth probe

Committed the framing fix and regression/replay evidence, then ran pinned,
checksum-verified gitleaks8.21.2 over the full Git history with **0 findings**.
Recorded that scan, scanned the final head again with **0 findings**, and
pushed `5e8c0c961506af997a522190e194fbe9ca745308` fast-forward. No ignore entry,
privacy rule, credential or permission changed. All157 replay and61 host-walk
hashes matched actual committed Git blobs.

Privacy runs [40261603041](https://github.com/Ares-Empire/AresOS/actions/runs/40261603041)
and [40261599776](https://github.com/Ares-Empire/AresOS/actions/runs/40261599776)
passed all three checks, with personal terms executed, before POST. The
retained privacy proof was freshly re-read before qualification; the separate
event-order receipt independently confirms both jobs completed before the
probe was created. Immediately before dispatch the actual release verifier
passed again and the fresh guard established **53/53** history: **133 consumed
+184 reserved /350**, org **172 after reservation**, above150.

Sent fifth probe [40261916660](https://github.com/Ares-Empire/AresOS/actions/runs/40261916660)
once on that head. It **passed**. Native output was **`Ran 306 tests in
24.121s` / `OK`**, no skips; all eight new framing tests ran. The early native
capability smoke,15 Windows refusal cases, four CI-only private checks and
ISO inspection passed. The actual live offline command produced a valid
checksum-framed export: independent decoding of the raw console receipt
exactly equals the retained carrier0 / physical-link-down JSON.

Live WebUI preview, guest tools hotplug after login, guest every-file bundle
manifest check, removal before shutdown, detached Windows and target reset
passed. The [review image](screenshots/14i-probe-review.png) was inspected:
only target`vda` is selected and installation has not started. The
[detached marker](screenshots/14i-probe-detached-windows.png) shows
`BootCurrent=0000` / `MARKER_BOOT_COMPLETE`. Three protected captures exactly
match that run's whole-disk/GPT/EFI baseline; four write/unmap samples are
zero, all three BootNext checks passed, and both NVRAM rule records replay
exactly with the unchanged implementation. The paused failure-counter probe
also passed. Cleanup removed the outside-workspace job credentials.

Artifact **12625233566**,330 members,4,720,307 bytes, was digest-checked before
inspection: SHA-256
`99cb6eb9cb458ac560c556689ba2087b7750a8e11603752d026b97f8067b8bf1`.
Selected actual proofs, normalized audits, original member hashes and the raw
framing receipt are retained in `os/manifest/ci/14/14i-probe/`.

### Same-head qualification and new tty3 readiness STOP

While the probe ran, the qualification's actual ISO replay freshly rehashed
all9,068,650,496 bytes, fetched the current public checksum and passed all
four localization/102 WebUI source checks again. Its53-source offline gate,
15 Windows refusals,157 Git/file bindings and258 guest +258 serial syntax
checks passed on the unchanged head. The full local suite receipt is the
same-head execution above; no new test failure was waived.

After inspecting the passing probe, re-read exact-head privacy, reran the
actual release verifier and fetched a fresh ledger/billing/probe-artifact
guard: **54/54** history, **155 consumed +142 reserved /350**, org **192 after
reservation**, above150. That142 reserved130 for one qualification and12 for
closing privacy. Sent [qualification40263990213](https://github.com/Ares-Empire/AresOS/actions/runs/40263990213)
once, on the **same `5e8c0c9` head**, in protected-second order.

Native output was **`Ran 306 tests in 22.893s` / `OK`**, no skips. Capability,
private-access/signature/pull and ISO checks passed again. The actual offline
installation completed; the [completion screenshot](screenshots/14i-installation-complete.png)
was inspected. This is automated installer evidence, not a physical click-path
or followability qualification (`click_path_qualified` remains false).
First-stock hardware setup performed its single orderly pre-login reboot.
The following offline checkpoint recorded no staged or rollback-queued work,
no pins and no transaction. Attached and detached Windows-like round-trip
boots passed, with tools absent. Stock was then started with one-shot BootNext.

Actual physical tty3 `ares-recovery` login and password sudo reached a root
prompt. Tools hotplug then passed its hash/identity/label checks after login.
The next operation failed at **`tools-install-ready`**, exit1:

```text
Physical console readiness deadline: tty3
ARESOS_CMD_DONE:1
```

The traceback stops in `Console.run` → `prompt` → `wait_tty`, **before** record
listing or physical typing of `COMMANDS['install']`. This is not a bundle
installer refusal: the install command was never sent. `prepare`/rerun, first
network invariance, export, switch, layout failure/revert/success, rollback
and keep-stock were not reached.

**PLAN-GAP:** the [failure screenshot](screenshots/14i-tools-prompt-stop.png)
shows the earlier `root@bazzite:~#` prompt followed by USB kernel messages and
a blank active cursor line. The unchanged reader tests only the current
cursor line for a trailing `$`/`#`. Together these indicate a prompt
synchronisation failure after asynchronous hotplug output. No raw VCSA buffer
was retained, so the exact cursor bytes are not independently claimed. The
local walk's strict Bash parsing and stand-in responses did not exercise
this terminal-output timing. No kernel output was suppressed, readiness
assertion bypassed, owner code changed or harness fix attempted after STOP.

All **seven** reached protected captures match that run's whole-disk/GPT/EFI
baseline, all **eight** write/unmap samples are zero, all **seven** BootNext
checks passed, and all **six** NVRAM rule transitions replay exactly using
the unchanged audit code. Across the two runs, all eight full-variable
deltas also recompute exactly. The failure-path counter was retained while
the VM was paused. Failure cleanup then terminated QEMU with a recorded
host-signal shutdown; no later guest reboot occurred. The normal tools
detach/export/host readback path was **not reached** on this failed boot.
Do not infer it from the successful probe's removal. Job credential cleanup
passed, and no owner token was used.

Artifact **12626672908**,421 members,5,418,019 bytes, was digest-checked before
inspection: SHA-256
`4bd3fb9cd5bbc364848cb5ef1a23c060412889e92b7f67d83316e156b06b7c8c`.
Decisive native/guest/initial-state proofs, paused counter, source-member
hashes and read-only replay results are retained in
`os/manifest/ci/14/14i-qualification-stop/`. JSON hashes precede paths; EFI
maps are normalized without changing values. Console extracts remove only
terminal escapes and trailing prompt spaces. Screenshots were checked for
the stated evidence; none contains a token or typed password.

### Stopped ledger and remaining gates

Complete **55 unique IDs / total_count55**, all settled at this read:

| Item | Actual at stopped read | Cap/reservation |
|---|---:|---:|
| Five probes | 5 +6 +13 +22 +22 =68 min | 5/5 spent |
| Qualification1 | 48 min, failed | 1/2; no rerun |
| Privacy since first dispatch | 87 min | same ledger |
| Package consumed | 203 min | 350 min |
| Closing privacy reserved | 12 min | 215/350 including reservation |
| Image builds / publications | 0 /0 | 0 /0 |
| Org free / after closing reservation | 286 /274 min | minimum150 |

No VM reservation or further dispatch remains in the plan. The second
qualification allowance is unused; the new blocker invokes STOP regardless.
The final report push remains subject to a clean pinned full-history scan.
Its actual closing privacy receipts/cost are recorded in PR #13 after checks
finish, avoiding a self-triggering report-push loop. PR #13 remains draft
because automated owner-route acceptance is unmet. No merge or publication;
no Gradle work or daemon was started. The real laptop was never touched and
no package, mount or QEMU operation ran in local WSL.

**Not verified:** guest bundle installation/prepare, first-network invariance,
owner record export, signed switch, layout failure/revert/success, rollback,
keep-stock and their later audits in this package. All physical NVIDIA,
forgotten-stick, Media Writer, laptop and followability gates stay open and
installation **NOT RELEASED**.
**Open questions:** reviewed prompt synchronisation and an execution/timing
regression for asynchronous console output. A changed harness head would
need a fresh passing-probe allowance; all five current probes are spent.

**Closing local checks:** command/bundle equality and hash-order tests passed
**4 tests in4.858s**; frozen runtime/owner scripts/workflow/privacy diffs are
empty. Both newly retained evidence directories passed the pinned scanner
with0 findings before commit. The staged and branch-wide whitespace checks
and full-history scans still gate the final push.

## Historical 14h status

**Current 14h status: STOP / PLAN-GAP at guest JSON command framing.** The
native capability smoke, all297 native tests,15 Windows refusals, four private
checks, ISO inspection and real FUSE media copy/fsck/readback passed. The live
guest printed carrier0/offline success, then the wrapper treated its closing
`PY` delimiter as Python and exited1. No successful probe or qualification
exists. Snapshot: **113/350 consumed +12 closing privacy reserved**, **4/4
probes spent**, **0/2 qualifications**, org **382 free /370 after reservation**.
PR #13 stays **draft**; physical installation stays **NOT RELEASED**.
Earlier stops below retain their historical evidence.

## 14h — Explicit runner FUSE exFAT and early host capabilities

**Done:** ran `git pull --ff-only` first (already at`afd608b`). Rehearsal
bootstrap adds `exfat-fuse`, records installed packages, then runs a mandatory
three-minute native capability step on package14 before browser downloads,
private pull/signature work, ISO inspection or owner-tools VM startup. Both
probe and qualification use that same step and the same implementation.

`owner_fuse.py` supplies the shared host path: explicit `mount.exfat-fuse`,
exact loop source/target, block FUSE type and `blkid` exFAT identity; checked
VFS `nodev,nosuid,noexec` and exact rw/ro mode; unmount confirmation at both
mountpoint and source before loop detach. `owner_media.py` keeps `mkfs.exfat`,
the exact Windows copy implementation and sync. After writing/unmounting it
allocates a read-only loop, requires `fsck.exfat -n`, remounts with FUSE read-only,
checks **every bundle file** against the manifest, confirms unmount/detach and
only then hashes the backing for QMP attachment. Record export uses the same
fsck/read-only path. Unknown mount state, wrong driver/format/source/flags,
dirty fsck, corrupt readback or incomplete unmount fail closed. No kernel
exFAT or other-filesystem fallback exists.

The helper's Linux [v1.3 source](https://raw.githubusercontent.com/relan/exfat/v1.3.0/fuse/main.c)
and [v1.4 source](https://raw.githubusercontent.com/relan/exfat/v1.4.0/fuse/main.c)
use block FUSE and a device fsname, with limited option forwarding. Therefore
the code explicitly applies the VFS safety flags to the **already identified
FUSE mount** using an internal bind-remount, then checks the dedicated
[findmnt VFS-OPTIONS column](https://raw.githubusercontent.com/util-linux/util-linux/v2.39.3/misc-utils/findmnt.c)
before copying. This sets per-mount flags; it does not select another driver
or mount another filesystem. Source hashes/URLs are retained in the replay.
Native execution must still establish support; no successful host result is
inferred from source or shims.

`owner_capabilities.py` uses a separate fresh64MiB scratch exFAT image for
verified loop backing, FUSE rw write/sync, confirmed unmount, no-repair fsck,
read-only readback and an actual EROFS write refusal. It then exercises the
unchanged file-fixture builder (EFI compilation, GPT/FAT/NTFS), Q35/OVMF with
the existing acceleration selection and6GiB RAM, QMP sockets, PCI/block stats,
user-network link control, virtio-serial/serial sockets, USB add/remove,
keyboard and screenshot. Its toy USB is removed while the CPU is paused,
**before firmware starts**; firmware then boots only the synthetic marker.
These scratch fixtures are separate from the owner/protected/target rehearsal
files. This is host capability proof, not an OS installation or owner-route
qualification. QEMU failure cleanup kills only its own process. The owner VM
and qualification artifact guard require a complete proof for the exact head.
No firmware audit or owner hotplug timing rule changed.

**Verified locally:** **60 host-walk tests in59.633s**, no skips,56 source
bindings. Eleven new test methods cover FUSE identity/options and cleanup,
fsck/corrupt-manifest refusal, hash ordering, the real capability control flow
under closed stand-ins, QMP process failure, workflow ordering and incomplete/
wrong-head proof refusal. The existing full media/export walk now uses the same
safe volume stand-in and retains its assertions. All typed guest paths remain
covered; no tools stick crosses a reboot.

Whole local discovery printed **`Ran 297 tests in 184.955s`** and
**`FAILED (failures=2, errors=9)`**, exit1, no skips: **289 passed**, eight
existing host-limited cases. Three need absent WSL Pillow, three inherited-
Homebrew cases and one sysusers case are refused by the no-privilege shim,
and the credential-mode case sees DrvFS0777 instead of0600. Cleanup errors
produce extra records. All297 remain mandatory native checks; no assertion
was skipped, weakened or waived.

The actual git-only release verifier passed again with real run/jobs GETs and
all Git fetch/ancestry/payload checks. The actual full9,068,650,496-byte ISO
inspection passed its pin, fresh official checksum, four localization and102
Web UI sources. The offline14b source gate passed all53 retained files and the
full listing. Windows copy passed15 zero-write refusals with the unchanged
bundle fingerprint. CI/release shell syntax,257 guest commands,233 embedded
Python programs and48 CI/overlay/owner Python sources passed compilation.
Compact replay results, exact ISO adapter, host-walk log and153 canonical
input hashes are retained in `os/manifest/ci/14/14h-replay/`; all153 replay
and56 host-walk hashes matched the pushed Git blobs before dispatch.
Local proof used ordinary files, shims and fixtures only: no package install,
mount, real device operation or QEMU process on the laptop or WSL. Owner tools,
owner scripts, guest filesystem handling, frozen runtime and release are
unchanged. No image rebuild/publication is authorized.

**Stage walk:** offline install and first-stock hardware reboot; Windows-first
round trip with tools absent; Linux sign-in then tools hotplug/install/prepare/
rerun; first network with entire deployment/pin/pending/BLS state unchanged;
export/unmount/detach; Windows checkpoint; corrected stock and signed switch;
AresOS German, plain-US failed fresh login and revert, US International success,
back to German; rollback/keep-stock and Windows checkpoints. Every existing
protected-disk, NVRAM, BootNext, Windows-default and detached-device audit stays.
The additional host capability gate precedes this route and cannot authorize
an audit exception or a stick present during firmware startup.

**Planning snapshot:** complete40/40 history reported80 consumed,3/4 probes,
0/2 qualifications. Reserve42 probe/native +130 one qualification +12 closing
privacy =184, total264/350. Org415 free,231 after reservation, above150. The
second qualification is optional behind its own fresh guard and every STOP
rule. Before dispatch: pinned local gitleaks8.21.2 full-history zero findings,
fresh pushed-head privacy (all three rules executed), local14e/14f replay,
complete ledger and billing again. A missing native capability means STOP;
no fallback, blind rerun or qualification follows a failed probe.

### Actual fresh gates, native success and framed-heredoc STOP

The first FUSE implementation head `de322e9` was pushed after a clean pinned
full-history scan; both normal privacy runs passed. Final review then found
that a diagnostic from `findmnt` with no stdout could be mistaken for a clean
no-match. Tightened that refusal **before any dispatch**, repeated the whole
297-test discovery and60-test walk (results above), refreshed the bindings,
recorded both scans and pushed final candidate
`02eac4a226787a8879ee80d8d814221a22630323` fast-forward. Its pinned,
checksum-verified gitleaks8.21.2 full-history scan reported **0 findings**.
No ignore entry or privacy policy changed.

Privacy runs [40249678234](https://github.com/Ares-Empire/AresOS/actions/runs/40249678234)
and [40249682573](https://github.com/Ares-Empire/AresOS/actions/runs/40249682573)
passed all three rules, with personal terms executed. Immediately before POST,
the actual verifier passed again, source hashes matched and the fresh guard
proved complete **44/44** history: **91 consumed +184 reserved /350**,
**3/4 probes**, org **404 free /220 after reservation**, above150.

Sent one fresh probe: [40249992092](https://github.com/Ares-Empire/AresOS/actions/runs/40249992092)
on that exact head. The early native capability step passed in **11 seconds**
(00:40:13–00:40:24 UTC), before browser/private/ISO work. Its same-head proof
records every required capability, actual read-only EROFS refusal, synthetic
marker boot and toy USB removal before firmware. Installed `exfat-fuse` was
**1.4.0-2**, `exfatprogs` **1.2.2-1build1**, on kernel**6.17.0-1022-azure**.
No kernel-driver fallback was used.

Native output: **`Ran 297 tests in 19.693s` / `OK`**, no skips, including all
eight local host-limited cases. PowerShell passed all15 zero-write refusals;
the git-only verifier, private metadata/digest, exact signature and preserved-
digest layer pull all passed. Cleanup removed the outside-workspace job
credentials. Native ISO inspection passed the full pin/checksum, four
localization and102 Web UI sources.

The real128MiB tools image then passed the exact Windows copy implementation,
FUSE safety checks, sync/unmount confirmation, clean `fsck.exfat -n` and a
read-only every-file bundle check. The manifest fingerprint remains
`118212ec60844043856b5531be95cf2319f9943319679fa6149f999db89bf6ba`.
Its backing was hashed only after verification. The synthetic baseline marker
boot and live root login ran; the [baseline screenshot](screenshots/14h-baseline-firmware.png)
was visually checked for `BootCurrent=0000` / `MARKER_BOOT_COMPLETE`.

The live command `live-offline-before-webui` printed:

```text
{"status": "passed", "interfaces": [{"name": "enp0s1", "carrier": "0",
 "flags": 4099, "operstate": "down"}], "physical_link_down": true}
NameError: name 'PY' is not defined
ARESOS_CMD_DONE:1
```

The shell also warned that the here-document wanted `PY` at end-of-file.
The traceback ends at `Guest.assert_offline` through `capture_json` and
`switch_vm.framed`. The latter appends ` > "$result"` directly to the supplied
command; the generated command ends at the closing `PY` without a newline.
That changes the delimiter line into `PY > "$result"`. Python consequently
evaluates `PY` as a name after printing the valid network payload. The command
exits1 and never produces the required checksum-framed JSON export. Printed
offline data cannot substitute for a successful protocol receipt.

**PLAN-GAP:** the existing JSON wrapper does not safely compose this heredoc
command. The local walk used stand-in guest responses and syntax checks; it
did not execute this wrapper composition before dispatch. A zero-cost local
reproduction now runs the **unchanged** `framed` implementation with a literal
JSON heredoc, adapting only its `mktemp` directory from `/run` to this worktree:
same delimiter warning, valid printed JSON, same `NameError`, exit1. Its
single-line command control exits0 and decodes correctly. Exact scripts,
stdout/stderr, helper and hashes are retained in the STOP evidence. This
demonstrates a framing defect; it does not establish a network/carrier failure.
The needed wrapper correction and an execution regression require review
before any renewed probe allowance. No harness fix or rerun was attempted
after this STOP; all4 current probe allowances are spent.

The guest WebUI transport, browser preview, guest tools hotplug, final detached
Windows check and target reset were **not reached**. Nothing was installed.
The reached baseline/live protected-disk captures exactly match the baseline
whole-file SHA-256, GPT and EFI inventories; both counter samples have
**0 write bytes,0 writes,0 unmaps**. Both BootNext checks and the reached
`11f-linux-position` NVRAM replay passed. The failure-path counter was retained
while the VM was paused before cleanup. These partial audits do not qualify
the later stages or a successful live probe.

Artifact **12620338527**,214 members,3,116,273 bytes, was checked against its
GitHub SHA-256 **before reading**:
`636cfeccbcb527c13ba655f6bc6e0a322bac3d30bafc6cc6ba0fe6f0bd40cd93`.
Native/capability/media/private-check proofs, sanitized guest failure output,
actual step outcomes, original member hashes, reached audit data, fresh
privacy/guard receipts and the local reproduction are retained under
`os/manifest/ci/14/14h-probe-stop/`. Hashes precede paths; copied EFI file maps
were normalized to that shape without changing their values. The final
branch-wide whitespace check caught four trailing prompt spaces in the
sanitized console extract; those spaces were removed and its hash refreshed.
This evidence-only correction and its normal privacy runs share the closing
reservation. The executable paths remain unchanged after the STOP. No credential
value was printed or retained in repository/evidence; authorized temporary
job credentials were removed by cleanup.

While the probe ran, the qualification's local replay passed on the unchanged
head: **60 tests in65.435s**,15 Windows refusals, the53-source offline gate,
complete ISO replay,257 shell checks,233 embedded Python compilations and48
Python sources compiled without caches. A passing probe is still mandatory,
so no qualification was dispatched. No image/publication job ran. The real
laptop was never touched; no package, mount or QEMU operation ran in WSL.

### Stopped ledger

Complete **45 unique IDs / total_count45**, all settled at this read:

| Item | Actual at stopped read | Cap/reservation |
|---|---:|---:|
| Probe1 /2 /3 /4 | 5 +6 +13 +22 =46 min | 4/4 spent |
| Privacy since first dispatch | 67 min | same ledger |
| Package consumed | 113 min | 350 min |
| Closing privacy reserved | 12 min | 125/350 including reservation |
| Qualifications | 0 | 2; blocked by missing passing probe |
| Image builds / publications | 0 /0 | 0 /0 |
| Org free / after closing reservation | 382 /370 min | minimum150 |

No VM reservation remains. The closing report push is covered by12 reserved
minutes; its final scan, privacy receipts and actual closure cost are recorded
in PR #13 after checks finish. Every push still requires the pinned local
full-history scan to report zero findings. PR #13 remains draft because
acceptance is unmet. No merge or publication occurred, and no Gradle work or
daemon was started (the mod is unchanged).

**Not verified:** successful live probe, guest tools hotplug/readback, offline
installation/first-stock hardware boot, first-network invariance, physical
owner commands, layout failure/revert/success, switch/rollback/keep-stock and
their later audits. All physical NVIDIA/media/forgotten-stick/laptop/
followability gates remain open and installation NOT RELEASED.
**JUDGMENT-CALL:** no new owner-facing choice; explicit VFS flag application
implements the requested flags despite helper option filtering.
**Open questions:** reviewed framing correction/regression and authorization
for a new passing-probe attempt before the unrun qualification.

## 14g — Git-only squash binding and permission inventory

**Done:** ran `git pull --ff-only` first (already at integrator commit
`2d934d7`). The org verifier no longer reads the PR API. PR12's merged state,
exact squash SHA, head and base are pinned historical facts, verified by the
integrator on2026-10-25 in14e/14g. A changed pin refuses before external reads.
The verifier fetches the source, retained `refs/pull/12/head` and exact squash;
requires source ancestry in that PR head and squash ancestry in HEAD; and
compares all eight runtime paths source→HEAD **and** source→squash. Every other
release/run/job/signature/image-diff/job-token-read check remains intact.
Shallow or unknown history refuses explicitly before API reads. Both verifier
jobs (`switch`, `rehearsal`) now use full checkout history. No workflow
permission, credential, owner script, bundle, frozen runtime or release changed.

The permission regression inventories every Python `gh api` construction in
the CI tree, the verifier's suffixes and every caller of the guard GET wrapper,
plus shell/inline workflow API commands. It follows conservative local import/
literal-script-reference closures for each job and checks its declared grants.
Remaining calls are Actions run/jobs/artifact GETs (`actions: read`) and the
org package GET (`packages: read`, already qualified in package13's frozen
record). Billing stays scheduling-only under `not ci`; the existing runtime
regression also verifies CI never calls it. Unknown calls, endpoints or methods
refuse. Negative cases remove job grants/history or add unsupported calls.
This checks the declared contract; live package access remains fail-closed in
the four unchanged CI-only steps from14f.

**Local verification before dispatch:** the actual verifier passed using real original-run/jobs
GETs and all fetched Git checks, without a PR API request. Seven binding tests
cover all five pins, all three failed fetches, both ancestry links, both payload
diffs and shallow/unknown output. Four permission regressions passed. The
refreshed **49-test host walk** passed in48.621s, binds51 source files, and
requires no tools stick across any reboot. Windows copy passed **15 zero-write
refusals** with the unchanged bundle fingerprint. The offline14b source gate
again passed all53 source files and the complete retained listing. Frozen
runtime paths compare byte-identically with775be05.

The whole local discovery printed **`Ran 286 tests in 152.881s`** and
**`FAILED (failures=2, errors=9)`**, exit1, no skips: **278 tests passed** and
eight distinct cases retain the documented host limits. Three need absent
WSL Pillow, three inherited-Homebrew cases and one sysusers case require
privileged Linux operations (the local no-privilege shim refused every sudo),
and the credential-mode case sees DrvFS0777 instead of0600. Cleanup errors
account for the additional error records. These are not green local results
or waived assertions; all286 must pass natively before the VM.

The actual complete9,068,650,496-byte ISO replay passed, including a fresh
official checksum GET, four localization and102 Web UI sources. All four
retained firmware source hashes and the exact automatic-option predicate
passed. CI/overlay/owner Python compilation, every CI/release shell syntax
check, **257 guest shell checks** and **233 embedded Python compilations**
passed. The compilation command temporarily generated two `pyc` files inside
the bundle; its exact-file guard correctly refused. Removed only those cache
files and their empty directory; all four equality tests then passed. The
tracked bundle is unchanged. Compact results, exact inspector adapter,
host-walk log and **143 canonical source hashes** are retained in
`os/manifest/ci/14/14g-replay/`. All143 replay hashes and51 host-walk hashes
were checked against the pushed Git blobs before dispatch.

The stage walk remains the14c owner sequence: offline install and stock
hardware reboot; Windows-first round trip with tools absent; Linux sign-in,
hotplug/install/prepare/rerun; network deployment/pin/pending/BLS invariance;
export and detach; Windows checkpoint; corrected stock and signed switch;
AresOS German; plain-US failed fresh login and revert; US International success;
back to German; rollback/keep-stock and Windows checkpoints. All protected-disk,
NVRAM, BootNext, detached-device and Windows-default checks remain mandatory.

**Planning snapshot:** probe cap is now3, qualifications remain2, total cap350.
The required plan reserved42 probe/native +130 one qualification +12 closing privacy =184.
The optional second qualification requires its own fresh guard and all STOP
rules; it is not reserved as an assumed rerun. The complete33/33 planning read
reported51 consumed and447 org minutes free. The optional second qualification
remained behind its own fresh guard, not an assumed rerun.

### Actual fresh gates and third-probe media STOP

Pushed `4268a94d612a0d6890b14afbd332516dbae11c31` fast-forward after the
checksum-verified pinned gitleaks8.21.2 full-history scan reported **0 findings**.
Both privacy runs [40245221350](https://github.com/Ares-Empire/AresOS/actions/runs/40245221350)
and [40245226417](https://github.com/Ares-Empire/AresOS/actions/runs/40245226417)
passed gitleaks, private commit emails and personal terms; actual annotations
confirmed personal terms ran. Immediately before POST the actual verifier
passed again, all input hashes matched, and the guard proved complete **35/35**
history: **56 consumed +184 reserved /350**, **2/3 probes**, org **442 free**,
**258 after reservation**, above150. No credential or permission changed.

Sent one probe: [40245433868](https://github.com/Ares-Empire/AresOS/actions/runs/40245433868),
on that exact head. Native output was **`Ran 286 tests in 14.997s` / `OK`**,
no skips, including all eight local host-limited cases. PowerShell printed
**`PASS 15 destination refusals with zero writes; copied payload equals source`**.
The real release verifier passed. Org package visibility, exact registry digest,
signature identity/issuer and digest-preserving layer pull **all passed**.
Cleanup passed and removed the outside-workspace job credentials. None of the
four CI-only checks failed; no owner secret or local scope change was used.

Native ISO inspection then passed the full9,068,650,496-byte pin and fresh
official checksum, four localization sources and102 Web UI sources. The next
step created only disposable file-backed target/protected fixtures and began
the tools stick. `mkfs.exfat1.2.2` completed, but its subsequent mount failed:

```text
mount: .../.work/installer/owner-media-mount: unknown filesystem type 'exfat'.
subprocess.CalledProcessError: Command ['mount', '-t', 'exfat', '-o',
 'nodev,nosuid,noexec', '/dev/loop0p1', ...] returned non-zero exit status 32.
```

The traceback ends at `Media.create` (`os/ci/owner_media.py:70`), called before
the VM baseline/start in `owner_vm.main`. There is no `two-disk/` VM evidence
directory. The media's Windows-copy step, backing-hash completion, QMP hotplug,
firmware baseline and installation were not reached. The failure path executes
the existing loop-detach `finally`; no detach exception replaced the mount
error. No claim of guest or protected-disk/NVRAM/BootNext qualification follows
from fixture creation alone.

**PLAN-GAP:** the native prerequisite qualified exFAT formatting tools without
proving the runner could mount the file-backed exFAT filesystem. The observed
runner was `ubuntu24`, image`20261023.334.3`, kernel`6.17.0-1022-azure`;
`exfatprogs1.2.2-1build1` was installed. No matching `linux-modules-extra`
package appears in the retained installed-package list. The exact driver,
package or load-policy cause is **not established** by these records. No
driver/package repair, alternative filesystem or audit exception was tried.
A reviewed runner prerequisite and renewed passing-probe authorization are
needed before continuation; all three current probe allowances are spent.
Stopped without changing the harness, owner scripts, release or frozen image.

Artifact **12618767635** (`two-disk-evidence`,153 members,3,015,368 bytes) was
checked against GitHub's SHA-256 **before reading**:
`1f49f16f1dd1c251806dc301d2085a8620ed9a49880a7b4ad2070d11d26ffbca`.
Compact actual native/STOP output, CI step outcomes, four private-check and
cleanup proofs, original artifact provenance, fresh guard/privacy receipts and
the prospective qualification's local replay are retained under
`os/manifest/ci/14/14g-probe-stop/`. JSON key ordering is hash-first; original
member provenance is retained where copies were reformatted. No credential
value was printed or retained in repository/evidence; authorized temporary
job credentials were removed by cleanup.

While the probe ran, the qualification's local prerequisites were replayed on
the unchanged head: **49 tests in56.841s**,15 Windows refusals, the53-source
offline gate, complete ISO inspection,257 shell checks,233 embedded Python
compilations and46 Python sources compiled without creating caches. They
passed, but no passing probe exists, so **no qualification was dispatched**.
No image or publication job ran; those jobs were skipped. No real laptop was
touched. No Gradle work or daemon was started (the mod is unchanged).

### Stopped ledger

The fresh stopped read proves complete **36 unique IDs / total_count36**.
The19 charged records since the first dispatch total69 minutes:45 privacy and
24 across the three probes. The ledger reserves only closing privacy now;
there is no VM reservation or additional dispatch authorization.

| Item | Actual at stopped read | Cap/reservation |
|---|---:|---:|
| Probe1 / probe2 / probe3 | 5 +6 +13 =24 min | 3/3 probes spent |
| Privacy since first dispatch | 45 min | same ledger |
| Package consumed | 69 min | 350 min |
| Closing privacy reserved | 12 min | 81/350 including reservation |
| Qualifications | 0 | 2; blocked by missing passing probe |
| Image builds / publications | 0 /0 | 0 /0 |
| Org free / after closing reservation | 429 /417 min | minimum150 |

The report push is covered by that12-minute reservation. Its final scan,
privacy receipts and actual closure cost are recorded in PR #13 after the
checks finish. Every push requires the pinned full-history local scan to
report zero findings. No privacy workflow, ignore entry, rule or allowlist
was changed. PR #13 remains draft because acceptance is unmet.

**Not verified:** no package14 VM boot, live probe, offline installation/first
stock boot, network invariance, physical owner commands, layout failure/revert/
success, switch/rollback/keep-stock or associated guest audits ran. All physical
NVIDIA, media, forgotten-stick-at-power-on and laptop/followability gates stay
open. INSTALL, EMERGENCY and the release gate retain **NOT RELEASED**.
**JUDGMENT-CALL:** no new owner-facing decision; implemented the integrator's
historical binding and unchanged safety contract. **Open questions:** which
reviewed runner-side prerequisite will prove exFAT mount support before the
next expensive inspection, and whether a new probe allowance is granted.

## 14f — CI-only credential checks, unchanged fail-closed enforcement

Ran `git pull --ff-only` first; the worktree already contained `335141c`.
The integrator accepts the existing local package-metadata403 as an access
difference from the CI job, rather than a deterministic source mismatch.
No credential, local `gh` scope, owner secret or CI implementation changed.

The replay result explicitly records these four checks and their enforcing
steps. A failure of any one in the probe means **STOP and report, no rerun**.

| CI-only check | Reason | Enforcing CI step |
|---|---|---|
| Org package metadata visibility | Requires the job's `GITHUB_TOKEN` with `packages: read`; the local login lacks that access | Verify exact private manifest with scoped credentials |
| Registry digest inspect | Requires the scoped job auth file for the private image; success and exact pinned digest remain mandatory | Verify exact private manifest with scoped credentials |
| Private layer pull | Requires scoped job access; preserve digest, inspect the raw manifest and remove the temporary copy | Qualify the exact pinned layer pull without installing |
| Registry signature verification | Requires scoped job package access through its temporary `DOCKER_CONFIG`; exact release, identity and issuer remain mandatory | Verify the exact private signature natively for the offline guest |

Credential setup and always-run cleanup retain the existing outside-workspace,
job-token-only lifecycle. No owner-token fallback was added. The existing
privileged native bootstrap, full native suite, current-run proof and VM remain
on the disposable runner under brief14; they are not new credential exceptions.

### Local replay and stage walk before dispatch

The actual release verifier again passed using real original-run/job and PR12
APIs, source/PR fetches, both ancestry predicates and the entire eight-path
payload diff. The source gate14b again passed all53 retained source files and
the full listing. All50 bound host-walk source hashes still match current bytes;
the full284-case local discovery from14e covers this identical implementation
(276 passed, eight documented native-host limits, no skips). No new code change
requires repeating that discovery; the probe still runs the complete native
suite before its VM. The four CI-only implementations are unchanged.

Windows copy again passed **15 zero-write refusals** with unchanged bundle
fingerprint `118212ec60844043856b5531be95cf2319f9943319679fa6149f999db89bf6ba`.
The **257** guest shell syntax checks and **233** embedded Python compilations
passed again. The exact firmware automatic-option predicate and retained
source hashes passed, without changing the firmware audit or decoding rules.

The actual `installer_inspect.main` file inspection passed against
the retained ISO: its complete9,068,650,496-byte SHA-256 matches the pin and
the fresh public official checksum GET agrees. Only cached input transport and
the local archive executable/path spelling are adapted; no assertion, file
content or extractor result is substituted. Existing Windows system libarchive
and Linux `unsquashfs` operated on ordinary files inside this worktree. This
did not install software, mount a device or start a VM. All **four localization
sources** and **102 Web UI sources** passed the actual inspector's checks.
The exact local transport adapter, compact result, refreshed **47-test** host
walk output (**61.307s**), four CI-only classifications and **118 canonical
source input hashes** are retained in `os/manifest/ci/14/14f-replay/`.
The large raw replay output and extracted ordinary files remain under ignored
`.work/14/`; their source ISO is pinned. Every recorded file hash precedes its
path. Before the qualification the same local checks must be replayed again.

The owner stage table in14c remains unchanged: offline install/first stock and
hardware reboot; Windows-first round trip with tools absent; Linux sign-in,
hotplug/install/prepare/rerun; network unchanged-state proof and export/detach;
Windows checkpoint; corrected stock/signed switch; AresOS German; plain-US
failed fresh login and revert; US International success; back to German;
rollback/keep-stock and Windows checkpoints. No stage needs the stick across
a reboot. Every protected-disk, NVRAM, BootNext and Windows-first audit remains.

### Planning snapshot, not dispatch authorization

Complete **26/26** history at this read: **28 minutes** consumed, **1/2 probes**,
**0/2 qualifications**. The required remaining plan reserves **184 minutes**:
**42** for the fresh probe including native preflight, **130** for one
qualification and **12** for closing privacy. Total **212/350**. Org billing
reported **473** free and **289** after reservation, above **150**. Any optional
second qualification needs its own fresh guard and remains subject to all STOP
rules; it is not part of the currently planned run. No image build or publish
is permitted. The ledger, billing and all three privacy steps will be rechecked
immediately before dispatch on the pushed head.

### Actual fresh gates, final probe and PR-read PLAN-GAP

The replay and its scan ledger were pushed fast-forward at
`8fa7224ace336b6b1f6d0c181bd80a9303386a84` after a checksum-verified pinned
gitleaks8.21.2 full-history scan: **0 findings**. The scan is recorded in the
ledger. Both privacy runs
[40242272088](https://github.com/Ares-Empire/AresOS/actions/runs/40242272088)
and [40242274817](https://github.com/Ares-Empire/AresOS/actions/runs/40242274817)
passed **gitleaks, private commit emails and personal terms** on that head.
Actual warning annotations were checked: personal terms were not skipped.

Immediately before POST, the actual release verifier passed again on that
pushed head and all118 replay source hashes matched its Git blobs. Complete
**28/28** run history and billing passed: **34 consumed +184 reserved /350**,
**1/2** probes before dispatch, org **467** free and **283** after reservation,
above150. The single fresh/final allowed probe was dispatched once, on the
same head: [40242538685](https://github.com/Ares-Empire/AresOS/actions/runs/40242538685).

Native output: **`Ran 284 tests in 14.614s` / `OK`**, no skips. All eight local
host limitations passed natively. PowerShell printed **`PASS 15 destination
refusals with zero writes; copied payload equals source`**. Python and shell
compilation completed. The subsequent release verifier failed at line46:

```text
gh api repos/Ares-Empire/AresOS/pulls/12
gh: Resource not accessible by integration (HTTP 403)
subprocess.CalledProcessError ... returned non-zero exit status 1
```

The job's setup log reports effective **Actions: read, Contents: read,
Metadata: read, Packages: read**. Its YAML explicitly declares contents,
packages and actions read, with no `pull-requests` grant. The local login can
read PR12; that successful local replay did not establish integration access.
The replay review did not account for this difference before dispatch.

**Evidence versus inference:** HTTP403 on the required PR read is observed.
The missing explicit PR permission is a candidate explanation, not a proven
fix. GitHub's current [Get a pull request documentation](https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request)
lists either Pull requests read or Contents read, while its
[workflow permission documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idpermissions)
says omitted permissions become none when others are specified. Since this
job does have Contents read, those documents alone do not establish the exact
authorization cause. No permission change was tested or applied, and no new
credential was chosen. A narrowly reviewed PR-read grant is a possible next
integrator decision; it is not represented here as verified remediation.

**PLAN-GAP:** the pinned PR binding is mandatory but the actual CI integration
cannot read its record. The integrator must settle the permitted job access
for that read before continuation. Both **2/2 probes** are now spent, so a
new passing-probe allowance is also required. No owner token, scope refresh,
permission expansion, check bypass, job rerun or qualification dispatch was
used to get past this failure. This is **not** a failure or success of the four
package/registry CI-only checks: all four were **not reached**. No inference
about changed package visibility or signatures is supported by this run.

The completed-native gate, credential creation, registry checks, remote ISO
inspection and VM were skipped after the native-preflight failure. Cleanup
passed. Artifact **12617103845** was checked against GitHub's SHA-256 before
reading; exact native test/STOP output, pre-probe privacy/guard receipts,
cleanup result and compact artifact provenance are retained under
`os/manifest/ci/14/14f-probe-stop/`. All file hashes precede paths.

While the probe ran, the required local file inspection was repeated for the
prospective qualification, using native Windows file IO plus WSL extraction
and Linux LF output. Again the full ISO pin, fresh official checksum, four
localization and102 Web UI sources passed. The **47-test** host walk also
passed again. These receipts and the exact adapter are retained; they are
local prerequisites only and never qualification evidence. No qualification
was dispatched and no VM started in either package14 probe.

| Stopped ledger before closing push | Result |
|---|---:|
| First package dispatch (unchanged) | 2026-10-25 22:01:22 UTC |
| Final probe job | 2026-10-25 22:57:18–23:02:56 UTC |
| Final probe cost | 6 rounded minutes |
| Package consumed /cap | 40/350 minutes |
| Closing privacy reservation | 12 minutes |
| Consumed plus reservation | 52/350 minutes |
| Probes /allowance | 2/2 |
| Qualifications /allowance | 0/2 |
| Complete history | 29/29 runs |
| Org free /after closing reservation | 461 /449 minutes |
| Required org reserve | 150 minutes |

`BUDGET.json` retains this snapshot and scan receipts. Closing privacy and
actual costs will be checked and recorded in the PR after the reserved jobs
finish. No additional dispatch is permitted under the current probe allowance.

**Not verified:** live package checks, a passing package14 probe, VM owner-tools
qualification and all physical gates. **JUDGMENT-CALL:** no new permission or
credential decision was taken. CI-only implementations, workflow permissions,
all audits, owner scripts, frozen release/runtime paths and privacy policy stay
unchanged. INSTALL/EMERGENCY retain NOT RELEASED and name the current STOP.

## 14e — pinned PR12 squash binding and local replay STOP

**Done:** ran `git pull --ff-only` first; the worktree already contained
`e58457c`. In the org branch of `os/ci/verify_release.py`, replaced only the
source-to-HEAD ancestry command with the approved binding: PR12 must be merged,
its merge SHA exactly `775be05b7f0d6971cbdc8a3bd1aea617fc008c4d`, its head ref
`pkg/13-keyboard-layout`, and its base ref `main`. Fetch the retained
`refs/pull/12/head`, require the signed source in that history, and require the
pinned squash in current HEAD's history. All Git commands fail closed.

The verifier bytes before and after that replacement are unchanged from
`e58457c`: source fetch, release/run/job/branch/signature identities, every
release field, image diff, job-token read and the complete eight-path payload
diff are retained exactly. The legacy history-rewrite branch is unchanged.

`test_release_squash_binding.py` runs the complete actual verifier against
closed Git/GitHub stand-ins. **Nine tests passed in 0.029s**, with no CI
dispatch: the valid binding, unmerged PR, wrong merge SHA, wrong head, wrong
base, missing fields, source outside PR history, squash outside HEAD history,
and changed payload. No stub may fall through to a real command. The guard
now allows **two total probes**, keeps **two qualifications**, **350 minutes**
and the **150-minute org reserve**; its regression accepts two probes and
refuses a third. The source-bound host walk includes the verifier and tests.

### Actual zero-cost job replay

Copied the unchanged frozen release metadata to local ignored
`evidence/release.json` and ran the actual verifier with repository
`Ares-Empire/AresOS` and release run **40154642447**. All file, original-run/job
API, PR12 API, source/PR fetch, ancestry and payload checks passed. It printed:

```text
Qualified private org release 2abc12e8aa6089f7576143d1fbccb6648a3291bd; runtime payload unchanged; testing ghcr.io/ares-empire/aresos@sha256:9b19b7942bc131934eac3733a7f8a1c1de488659075897f60c006bc88c77f3eb
```

The next read-only GitHub check is the exact package visibility API used by
`registry_auth.py` before native registry preflight:

```text
gh api orgs/Ares-Empire/packages/container/aresos
HTTP 403: You need at least read:packages scope to get a package.
```

The existing local `gh` login is sufficient for repository/PR/run metadata,
but this endpoint refuses it. No authentication value was printed, read out,
stored or substituted; no scope was changed. In particular, no owner Actions
secret was retrieved or used as an API fallback. The CI job's own
`packages: read` context is distinct and has not been exercised by a new run.

**PLAN-GAP:** 14e requires every git/file/read-only `gh` step of the job to pass
locally before dispatch. That condition is not met. A decision on how this
local package-metadata read may be satisfied is needed before continuation;
this follow-up does not choose a new credential or a CI exception. Remaining
job replay stages are not claimed complete. The release ancestry issue itself
is resolved and the accepted binding remains ready for review.

The local refusal tests, Windows copy tests and offline source replay use no
Actions dispatch. Windows again printed **15 refusals with zero writes** and
the unchanged bundle fingerprint
`118212ec60844043856b5531be95cf2319f9943319679fa6149f999db89bf6ba`.
Offline replay again passed14b with all53 retained sources and the complete
listing. The refreshed host walk passed **47 tests in67.769s**, then its full
stand-in stage walk; all **50 source hashes** match. The complete local suite
ran **284 tests in218.778s**: **276 passed**, the same **eight** documented host
limitations, **0 skips**, `failures=2, errors=9` including cleanup records.
The limitations remain three missing-Pillow cases, three privileged
Homebrew/ACL cases, privileged sysusers and DrvFS auth-file modes. No test was
weakened or skipped; no native284-test result is claimed. **257** guest shell
syntax checks and **233** embedded Python compilations passed without execution.
`git diff --check` passed. Exact local output and hash-before-path receipts
are retained in `os/manifest/ci/14/14e-local-replay/`.
No new native run, VM, image build, publication, owner-script or frozen runtime
change occurred. INSTALL and EMERGENCY now name this current STOP.

| Ledger before closing push | Result |
|---|---:|
| Package first dispatch (unchanged) | 2026-10-25 22:01:22 UTC |
| Consumed including privacy | 17 minutes |
| Closing privacy reservation | 12 minutes |
| Consumed plus reservation /cap | 29/350 |
| Total probes /allowance | 1/2 |
| Total qualifications /allowance | 0/2 |
| Complete branch history | 22/22 runs |
| Org free /after closing reservation | 487 /475 minutes |
| Required org reserve | 150 minutes |

`BUDGET.json` and `os/manifest/ci/14/14e-local-replay/` retain the read-only
ledger and sanitized replay result. Before every eventual dispatch, all replay
steps, privacy CI, the complete ledger and billing guard must be fresh. No
dispatch is authorized by this stopped snapshot. Closing privacy outcomes and
actual costs will be recorded in the PR after its reserved jobs finish.

**Not verified:** a new passing probe, owner-tools qualification and remaining
job replay stages. **JUDGMENT-CALL:** none beyond the explicit14e decision; the
local API refusal was preserved. Physical and package15 gates remain open.

## 14d — hash-before-path manifests and resumed privacy gates

**Done:** pulled `1272b3e` fast-forward before resuming. The owner added exactly
the five historical fingerprints; this follow-up changes no ignore entry,
allowlist, rule or privacy workflow. The original finding classifier still
recomputes the original commit's Git blobs, rather than treating the rewritten
manifest as historical evidence.

The bundle manifest is now a list of `{sha256, path}` rows. Python and Windows
readers reject the old shape, reversed fields, duplicate paths/fields, extra
fields, malformed values, traversal, partial bundles and changed bytes before
any target write. Windows remains the same copy implementation CI uses. The
new reviewed bundle fingerprint is
`118212ec60844043856b5531be95cf2319f9943319679fa6149f999db89bf6ba`.
The earlier fingerprint and logs below are historical evidence, not the current
payload. INSTALL states the new fingerprint.

The host walk uses the same hash-before-path rows and the VM checks their shape,
uniqueness and current source bytes. All other package14 file/hash metadata now
puts hashes first, including source indices, archive members, retained fixture
provenance and old verification-log manifests. Their hash values, source/raw
archives and results did not change. A regression checks this ordering across
package14 metadata and the payload. Native preflight now explicitly runs the
PowerShell refusal suite as well as the complete Python suite before the VM.

**Verified so far:**

- Pinned portable gitleaks **8.21.2**, binary SHA-256 checked against the retained
  checksum-verified distribution: full-history `git . --redact=100 --no-banner
  --log-level warn` at `1272b3e`: exit **0**, **0 findings**. This is not a claim
  about a later unscanned commit. Every push requires a new clean scan.
- `pwsh -NoProfile -File os/tests/owner-tools.Tests.ps1 -Bundle
  os/owner-tools/payload -Work .work/14/14d-powershell`: **15 refusals with zero
  writes**, source/copy fingerprints equal, public entry tested with process-local
  storage stand-ins only.
- `python3 reviews/14-owner-tools/walk-host.py`: **38 tests passed**, then the
  actual host control-flow walk passed. All 48 source hashes match. The shell
  wrapper's exit-status forwarding had a quoting error after the successful
  Python command; the retained Python output says `OK` and the final PASS.
- **257** guest shell syntax checks and **233** embedded Python compilations
  passed without execution. Python source compilation and `git diff --check`
  passed. Offline source replay again reports `SOURCE-GATE-PASSED-14b`, with all
  53 retained files and the complete listing verified.
- Read-only planning guard: complete **15/15** run history, **0 dispatches**,
  **314/350** reserved, **512** org minutes free, **198** after reservation,
  required other-repository reserve **150**. A fresh guard is required before
  each dispatch; this is not dispatch authorization for a future state.

The complete local discovery ran **275 tests in 248.873s**: **267 passed**,
**8 host-limited cases**, **0 skips** (`failures=2, errors=9`, including cleanup
errors). These are the same local limits as14c: three Pillow cases without
WSL's PIL, three privileged Homebrew/ACL cases, privileged sysusers and DrvFS
auth-file modes. None was weakened or omitted. The full native suite must pass
all cases. Exact output is retained under
`os/manifest/ci/14/local-verification/14d/`; its file hashes precede paths.

### Actual continuation and PLAN-GAP

The final pre-push scan at `5dfe2b00955955eecaca6a9edb62da34b7bb5865`
reported **0 findings**, then the branch was pushed fast-forward. Both privacy
runs [40237880873](https://github.com/Ares-Empire/AresOS/actions/runs/40237880873)
and [40237883460](https://github.com/Ares-Empire/AresOS/actions/runs/40237883460)
passed **gitleaks, private commit emails and personal terms** on that head.
The personal-term step emitted no unset-secret/skip warning. An initial local
log check mistakenly matched the echoed workflow command; a read-only check of
actual warning annotations corrected that before dispatch.

A fresh complete **17/17** history and billing guard passed: package
**0 consumed +314 reserved /350**, org **506 free**, **192** after reservation,
above the required **150**. The single fresh probe was dispatched on the same
head: [40238209435](https://github.com/Ares-Empire/AresOS/actions/runs/40238209435).

Native output was **`Ran 275 tests in 17.307s` / `OK`**, no skips; all eight
local host limitations passed natively. The PowerShell suite printed **`PASS 15
destination refusals with zero writes; copied payload equals source`**. Source
compilation and shell syntax checks also completed. The next command failed:

```text
os/ci/verify_release.py:43
git merge-base --is-ancestor 2abc12e8aa6089f7576143d1fbccb6648a3291bd HEAD
exit status 1
```

That is the signed private image's historical source, while package13 was merged
as squash `775be05b7f0d6971cbdc8a3bd1aea617fc008c4d`. Read-only replay in this
worktree reproduces the failed ancestry test. Diffing the verifier's **entire
eight-path runtime payload** from that source to this head returns **0**; the
payload is unchanged. Diffing the frozen paths, including release metadata,
against `775be05` also returns **0**. The verifier's ancestry requirement remains
unchanged. No check was bypassed, no release manifest/image was altered, and no
second probe or job rerun was attempted. This ancestry incompatibility could
have been caught at zero cost before dispatch; the native failure is retained,
not counted as a passing probe.

**PLAN-GAP / integrator decision needed:** the current release-source ancestry
rule cannot accept the approved squash history. Any future continuation needs
an explicitly reviewed binding from the qualified historical source to the
reachable squash's exact runtime tree, while retaining all release-run,
signature, digest, private-access and payload checks. It also needs a fresh
probe allowance; the existing **1/1** is consumed. Removing the ancestry check
or rerunning against the exhausted allowance is not authorized here.

The native-preflight gate, credentials creation, signature/pull, ISO inspection
and VM steps after the failure were skipped. Cleanup passed. The private
artifact **12615638956** was verified against GitHub's archive digest before
reading. Its hash precedes its path in
`os/manifest/ci/14/14d-probe-stop/result.json`; that directory retains the exact
native test/STOP excerpt, privacy proof, pre-dispatch guard and cleanup result.
There is no `probe-result.json`, installed system or qualification evidence.

| Final dispatch ledger snapshot | Result |
|---|---:|
| First dispatch start | 2026-10-25 22:01:22 UTC |
| Failed probe, including native preflight | 5 rounded minutes |
| Package cap | 350 minutes |
| Probe dispatches | 1/1 |
| Qualification dispatches | 0/2 |
| Closing privacy reservation | 12 minutes |
| Consumed plus closing reservation | 17/350 minutes |
| Complete history at stop | 18/18 runs |
| Org free / after closing reservation | 501 /489 minutes |
| Required org reserve | 150 minutes |

`BUDGET.json` retains the fresh stopped ledger and clean pre-push scan receipts.
Closing push privacy will be checked and recorded in the PR; its 12-minute
reservation remains charged until actual jobs finish. No further dispatch is
permitted under this probe allowance. Package acceptance remains unmet.

**Not verified:** the package14 VM route and all owner-tools qualification
stages. The prior source, unit and stand-in checks remain prerequisites only.
No image/release/publication, laptop or physical USB operation was performed.
The stage table in14c remains the route: offline live install and first stock,
Windows-first round trip with the stick absent, attach after signed-in Linux,
prepare/rerun/network equality/export/detach, signed switch, guarded plain-US
failure/revert, US International success and back to German, rollback and
keep-stock. No stick is required across any reboot. All audit and STOP rules
remain in force. PR #13 stays draft until these automated gates pass; physical
release and package15/followability items remain open.

## Original prerequisite stop, before 14b

**The zero-cost offline first-boot prerequisite fails its explicit prohibition
on deferred first-boot network work.** The pinned stock enables NVIDIA Flatpak
runtime setup; the ISO does not contain either required matching runtime. With
the NVIDIA module loaded, setup attempts a Flathub installation and retries on
failure. No owner-tools implementation, probe, qualification, image build or
publication followed. This report does **not** claim that an offline VM was run
or that stock cannot reach its greeter offline. Physical installation remains
**NOT RELEASED**; the PR is draft because package acceptance is unmet.

## Done

Ran `git fetch` first in this new worktree. Verified clean
`pkg/14-owner-tools` at brief commit
`362d0770033b5146940f696ee2a9a40a70b6283a`. Read AGENTS, README, brief 14, the
install-gate council's question/verdict/member reports, the relevant existing
preparation/recovery scripts and harness paths, and retained 11k/11n/13f
evidence. No retired worktree was accessed.

Performed source/data verification before any dispatch. Retained
[53 original source/data files with complete hashes](../../os/manifest/ci/14/zero-cost/README.md)
and a [read-only replay](verify-zero-cost.py). The complete pinned ISO was freshly
downloaded and hashed in this worktree; two exact public base-image layers were
also downloaded, hashed and read as archives. No image/container, root command,
mount, hardware query, firmware operation or application on the laptop ran.

No installer bundle, Windows copy command, short Linux command, new guard,
harness change or guide replacement is presented as implemented. The existing
guides/card and their open council findings remain unchanged. There is no
hand-typed-block or third-stick fallback.

## PLAN-GAP — offline stock retains NVIDIA setup for the later network

Brief 14 requires offline first boot to finish hardware setup/reboot/login and
leave no pending first-boot service waiting for a later network. It explicitly
requires stopping before dispatch if that prerequisite fails.

The concrete counterexample is the laptop's expected installed NVIDIA module:

1. The exact ISO's local cached image is the qualified stock digest
   `sha256:ed93d2158a1bcba16b226bfb3ab6391446d11466646188c800b982d709435151`.
   The raw retained OCI manifest hashes to that same digest. The image's RPM
   [inventory](../../os/manifest/ci/06/image-6/kernel-nvidia.txt) pins NVIDIA
   **615.78.08**.
2. The frozen image enables
   `ublue-nvidia-flatpak-runtime-sync.service` in `multi-user.target.wants`.
   Its conditions require an installed OSTree boot and
   `/sys/module/nvidia/version`; this is a relevant path when the laptop's
   NVIDIA driver works. Its exact bytes match the
   [pinned upstream unit](https://github.com/ublue-os/bazzite/blob/2fab72cbc9a3257d80c607e173f22527aea3b39b/system_files/nvidia/shared/usr/lib/systemd/system/ublue-nvidia-flatpak-runtime-sync.service).
3. The [exact sync script](https://github.com/ublue-os/bazzite/blob/2fab72cbc9a3257d80c607e173f22527aea3b39b/system_files/nvidia/shared/usr/libexec/ublue-nvidia-flatpak-runtime-sync)
   skips work only when **both** versioned GL and GL32 runtimes are installed.
   The complete ISO filesystem inventory has **27 installed runtime IDs** and
   contains neither `org.freedesktop.Platform.GL.nvidia-615-78-08` nor
   `org.freedesktop.Platform.GL32.nvidia-615-78-08`. It contains no versioned
   NVIDIA runtime at all. The 20 other NVIDIA-named Flatpak paths are generic
   VA-API/Mesa files, not those runtime IDs.
4. The missing-runtime branch calls a Flathub `flatpak install`. The enabled
   unit has `Restart=on-failure`, `RestartSec=30`, and `TimeoutStartSec=600`.
   Thus an offline failure leaves network-dependent setup retrying; a later
   connection can complete that work. The paired verify/notification unit is
   also present. This is a source-derived consequence, not a new runtime result.
5. The current stock pause scripts target OS updater units, not this NVIDIA
   sync service. Pausing those units does not establish that NVIDIA setup is
   quiescent before reconnecting. No new `prepare` implementation was added to
   silently resolve or exempt this prerequisite.

This finding does **not** assert that a Flatpak installation stages an OSTree
deployment, or that the missing runtime necessarily prevents login. It
contradicts the separate, explicit **no deferred first-boot network work**
condition. A VM with virtual graphics would not establish this NVIDIA-dependent
condition merely by completing an offline login. Spending a probe to bypass
the failed source gate would not answer it.

The owner must settle how this deferred setup is handled within the two-stick,
offline-until-paused plan before package implementation/dispatch resumes. No
image change, new release, third stick, pre-pause network access, or manual
long-block workaround was chosen.

## Verified

### Pinned versions and zero-cost results

| Area | Source/data result |
| --- | --- |
| ISO | Full **9,068,650,496 bytes**, SHA-256 **`776b76f3417723440ee1823d79ec02a2c22860df196d219024edb062ad00d8e6`**, matching both the repository pin and a fresh [official checksum](https://download.bazzite.gg/bazzite-nvidia-open-stable-live-amd64.iso-CHECKSUM). |
| Anaconda | **44.30-2.fc44**; ISO network modules match [44.30 installation.py](https://github.com/rhinstaller/anaconda/blob/anaconda-44.30/pyanaconda/modules/network/installation.py) and [network.py](https://github.com/rhinstaller/anaconda/blob/anaconda-44.30/pyanaconda/modules/network/network.py) byte-for-byte. `NetworkInstallationTask` copies NetworkManager connection files into the target. The rule to avoid connecting in the live session is justified. |
| Local install payload | Actual ISO kickstart selects `containers-storage`; [pinned container-source code](https://github.com/rhinstaller/anaconda/blob/anaconda-44.30/pyanaconda/modules/payloads/source/rpm_ostree_container/rpm_ostree_container.py) does not require network for that transport. Actual post-install Flatpak script copies the ISO's local `/var/lib/flatpak` with rsync; it matches the pinned Bazzite source. These paths support offline installation at source level; a new complete offline install was not runtime-tested. |
| Origin change | ISO `%post` uses `bootc switch --mutate-in-place`; **bootc 1.16.13** [switch code](https://github.com/bootc-dev/bootc/blob/v1.16.13/crates/lib/src/cli.rs) takes the local origin-change branch and returns before the normal storage/pull path. `registry` in this command is not evidence of an install-time pull. |
| Stock/hardware setup | Bazzite **44.20261012.1**, revision **`2fab72cbc9a3257d80c607e173f22527aea3b39b`**; exact hardware setup is version **83** and equals the retained 13e source. OSTree **2026.4**, rpm-ostree **2026.3**, systemd **259.9** remain the pinned versions. Retained 11k, 11n and 13f each record the hardware-setup automatic reboot. Those runs are historical, not a new offline qualification. |
| Homebrew setup | The exact frozen service extracts `/usr/share/homebrew.tar.zst` locally; it does not download Homebrew at first boot. Its update/upgrade timers are separate. No brew command was executed in this run. |
| First later network | **Blocked:** enabled NVIDIA Flatpak setup can retry a network install, as detailed above. The no-deferred-work prerequisite is false; no complete new post-pause/network qualification is claimed. |
| Media Writer | **5.3.2**, the repository's pinned Windows release. [RestorePage.qml](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/src/app/qml/RestorePage.qml), [Windows restore helper](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/src/helper/win/restorejob.cpp), and [WinDiskManagement](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/src/lib/libwindisk/windisk.cpp) provide restore, clear the selected drive's old partitions/table, create a partition, assign/mount a drive letter and format exFAT, including the Windows API/CIMV2 fallback. This is a destructive stick restore, not preservation of its ISO/data. No writer or restore operation ran here. |

Media Writer's [5.3.2 German catalogue](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/po/mediawriter_de.po)
and system-locale selection were read, not translated from current `main`:
restore uses **Wiederherstellen**, finish uses **Fertig**, the drive-specific
heading uses **Laufwerk … wiederherstellen**, and success is **Das Laufwerk wurde
erfolgreich wiederhergestellt!** The multi-drive main selector and the
drive-selection prompt have empty translations; the generic heading is fuzzy.
Do not invent German rendering for those strings. The warning says the live
system and saved data are deleted. The Windows/German UI and expendable-media
trial remain unperformed. No guide tells the owner to use Disk Management,
diskpart or Windows Format as a fallback.

### Commands and actual outcomes

- `.work/14/fetch-sources.py` plus the additional pinned-source reads: retained
  **27 source files**, with URLs/byte counts/SHA-256 values in the source index.
- `.work/14/read-base-layer.py` and its `homebrew` invocation: verified complete
  public layer hashes **`1af49583…f96962` /324,644,312 bytes** and
  **`89d10b98…0b89` /156,741,603 bytes**. Read selected data only. The initial
  reader needed correction for OSTree archive hardlinks/symlink objects; the
  corrected reader preserved their content/targets as data, then reran.
- `.work/14/fetch-iso.py`, followed by `.work/14/complete-iso.py`: transferred the
  initial prefix and disjoint checked HTTP ranges, then hashed the **whole**
  ISO. Printed `PINNED_ISO_VERIFIED` with the exact hash and byte count above.
- Existing WSL `unsquashfs -ll -o 314167296` on that ordinary ISO: complete
  **1,439,437-line** listing. `unsquashfs -cat` read the **10** retained actual
  ISO files. No mounting, installation, sudo or software installation.
- `python -X utf8 reviews/14-owner-tools/verify-zero-cost.py --listing .work/14/squashfs-files.txt --record`:
  checked all **53** retained source/data hashes, the exact base manifest,
  matching source/ISO bytes, enabled unit, runtime inventory and source branch;
  printed **`STOP-PLAN-GAP`**, `source_integrity: passed`,
  `full_listing_replayed: true`, and zero dispatches. Native exit **2** denotes
  the failed prerequisite; this is not a passing owner-tools test.
- `.work/14/preclose-ledger.py`: read-only complete branch history and current
  org billing; results in [BUDGET.json](BUDGET.json). No dispatch API call.
- `git diff --check` and unchanged-path checks against `362d077` cover the
  existing harness, tests, owner scripts, guide/card, record helper, frozen
  Containerfile/context/locks/config/policy/base/keys/audit and release manifest.
  No runtime or qualified safety check was changed.

No new screenshots exist because no new VM or physical UI ran. All reported
observations are source/data verification or clearly identified old evidence.

## Budget

[Per-package ledger](BUDGET.json), measured before this closing push:

| Item | Actual / reservation |
| --- | ---: |
| Package cap | 350 minutes |
| First dispatch / ledger start | **Not started** |
| Probes | **0 /1** |
| Qualifications | **0 /2** |
| VM, image, release or publication minutes | **0** |
| Reserved VM minutes | **0** |
| Owner's initial branch privacy run, before first dispatch | 3 minutes |
| Closing push/PR privacy reservation | 8 minutes |

The complete pre-push branch history has **1 unique ID / total_count 1**,
completed push privacy run **40216222435**, no workflow_dispatch and no active
job. Per brief, the package dispatch clock has not started; pre-dispatch privacy
is separately recorded, not described as free org usage. Even charging its
3 minutes and the full 8-minute closing reservation conservatively gives only
11/350. No probe/qualification is authorized while the source gate is blocked.

Read-only org billing at **2026-10-25T17:49:28Z** reported **1,421 /2,000 used**,
**579 free**. Reserving 8 leaves **571**, above the **150-minute** reserve.
Known Linux-minute/storage SKUs, current period and zero paid net usage passed
the existing parser. The existing local gh login performed only GETs; no CI
billing credential or token scope was introduced. Closing privacy results,
actual minutes and final history are recorded in the PR body after the push,
avoiding a report-only push loop.

## Not verified

The owner bundle/copy step/commands and their refusal tests are **not built**;
the local whole suite and native preflight were **not run**. No offline VM,
tools-stick round trip, network-after-prepare, umlaut layout failure/revert,
successful change/back, guarded rollback or keep-stock qualification ran.
Existing 13f results do not fill those package 14 requirements. No Gradle build
or game/client tests ran; no mod changed, no green product claim is made, and
no Gradle daemon was started.

All physical, laptop, Windows/firmware, media, live-desktop and unaided
followability gates remain open. Package 14 acceptance is unmet; draft PR only.

## JUDGMENT-CALL

No new owner decision was made. Stopped at the brief's explicit source gate
instead of assuming virtual graphics proves the NVIDIA path, changing the
frozen image, suppressing a first-boot service without a settled plan, allowing
early network access, or inventing another stick/manual bootstrap. The owner's
two-stick/offline route remains the required design until revised by the owner.

## For package 15

If text appears over the prompt after you plug in or remove the stick, press Enter to get the prompt back.

Do not build the new owner path on unimplemented package 14 commands. After the
offline prerequisite and tools qualification are resolved, package 15 still
needs to address council findings **1, 4 and 8–11**: checkpoint return routes and
the mandatory Windows gate, permanent token retirement from Windows/phone,
symptom-first emergency navigation, German/Fn-mode shortcuts, exact localized
writer confirmations/cancellation, and one current status/boot-order table.
Include the checked stick restore/copy and explicit STOP/return destinations.
Physical/novice gates remain separate; no source check closes them.

## Open questions

At the original stop the owner needed to decide the handling of NVIDIA's
deferred first-boot network setup; **14b has now resolved that question**.
The rest of this paragraph records the original close. No user question or permission
prompt was issued mid-run, and no fallback was selected. No merge, force push,
visibility change, image dispatch or publication occurred. No token was printed
or retained in the evidence.

## 14b — accepted Flatpak deferral and tools USB stage walk

### Done

Ran `git pull --ff-only` first: **Already up to date**, on
`pkg/14-owner-tools` at `11728c531a6930a348bdaa2ae831a216d1f4d130`.
Read 14b and the inherited brief, council, guide, scripts and safety rules in
this worktree. Neither retired worktree was accessed.

Applied the integrator's NVIDIA decision to the source verifier, preserving
the original failed result as history. The new
[classification](../../os/manifest/ci/14/zero-cost/deferred-work-14b.json) and
[accepted source result](../../os/manifest/ci/14/zero-cost/verification-14b.json)
cover the retained scripts and known updaters:

| Work | Classification / handling |
| --- | --- |
| NVIDIA GL/GL32 sync and notification | Accepted deferred Flatpak-only work; never mask, disable, delay or replace it. Record its unit, check exit/result and runtime IDs without waiting. |
| Bazzite Flatpak manager 36 | Remotes, overrides, runtime cleanup, Firefox defaults and manager stamps; no deployment/BLS/disk operation in its complete script. |
| Homebrew setup/update/upgrade | Setup uses the local archive; mutable-prefix updates run as UID1000. Preserve the frozen AresOS Homebrew restrictions. |
| User setup 57 and its privileged helper | Desktop configuration/stamps, NTP and Tailscale operator settings; no network-dependent deployment path. |
| Hardware setup 83 | Local mandatory kargs/reboot before the round trip; not a deferred network job. Its one/two-serial result remains identity-checked. |
| OS updaters | Deployment-capable: pause before network, inspect system/global-user/active-manager units and transactions, and catch rpm-ostree/bootc/ostree clients. Never infer OS idleness from Flatpak's state. |

INSTALL and EMERGENCY now explain the expected offline notification. INSTALL's
release gate explicitly requires real-NVIDIA completion and unchanged complete
deployments/pins/pending/transactions/BLS after the network comes up. Virtio's
false NVIDIA condition cannot qualify that physical path. No stock service,
image policy or frozen runtime changed.

Read the actual ISO's XKB-derived console maps as data and retained them under
[keyboard-sources](../../os/manifest/ci/14/keyboard-sources/README.md). German
keycode26 includes U+00FC; US International includes U+00FC at AltGr+keycode21.
This supports a future plain-US failure/revert and US-International successful
trial with the unchanged umlaut password. No map was loaded; no physical trial
is claimed.

Drafted the bundle, copy checks, guarded commands and offline virtio-serial
WebUI transport locally before the stage walk reached the USB issue. **They
are not shipped or qualified.** The draft and its candidate patch are retained
only under ignored `.work/14/prototype/`; the active release scripts, harness,
workflow and test suite were restored exactly to the reviewed head. The
candidate's 11 pure preflight/bundle tests and eight PowerShell destination
refusals passed, but are development observations, not acceptance evidence for
an owner route. In particular, all-refusal shim coverage, full prepare/rerun,
stick diagnostics export and end-to-end layout proof still need completion.
No generated bundle/fingerprint or new owner command appears in the guide.

### PLAN-GAP: the virtual tools USB creates an unsupported firmware path

The expected attach transition is source-verifiable before spending minutes:

1. **OVMF 2024.02-2ubuntu0.10** enumerates whole BlockIo devices, fixed or
   removable, and creates missing automatic options from their device paths.
   This branch has **no filesystem or EFI boot-file test**. A data-only exFAT
   tools stick does not avoid enumeration.
2. The retained **whole BmBoot.c hash matches exactly** the hash recorded with
   that installed runner binary: `e961d1bc0ad7df99156a030dee92585fb2608ad5722f34d494459c2f74e6f3c6`.
   The tagged USB driver appends a USB messaging node, with port/interface;
   multi-LUN storage can add a logical-unit node. The latter driver/header
   files are upstream tagged source, not separately attested Ubuntu binaries.
3. The unchanged `disk_audit.firmware_hardware` only recognizes the retained
   PCI/SATA/NIC paths. Three source-derived USB path fixtures all produce
   **`PLAN-GAP: unsupported firmware device path`**, even with the exact
   16-byte automatic-option ownership GUID. These are synthetic fixtures,
   **not** a new observed VM store, and no exact future option number is assumed.
4. Reducing the USB identity to PCI controller `00:05.0` would be unsafe: the
   keyboard/controller remain present after removing the stick. It would hide
   the required detached-device failure. That shortcut was not implemented.

Pinned sources, hashes and scope are in
[firmware-walk](../../os/manifest/ci/14/firmware-walk/README.md). Primary sources:
[BmBoot.c](https://github.com/tianocore/edk2/blob/edk2-stable202402/MdeModulePkg/Library/UefiBootManagerLib/BmBoot.c),
[UsbEnumer.c](https://github.com/tianocore/edk2/blob/edk2-stable202402/MdeModulePkg/Bus/Usb/UsbBusDxe/UsbEnumer.c),
[device-path definitions](https://github.com/tianocore/edk2/blob/edk2-stable202402/MdePkg/Include/Protocol/DevicePath.h).

The applicable [11f stop rule](../../briefs/11f-linux-order-and-full-length.md#4-before-spending-minutes-walk-the-remaining-stages)
is explicit: **“If a transition you can foresee would fail the rules, stop and
report it as a PLAN-GAP before dispatching. Don't widen any rule yourself.”**
Stopped here. No controller-only exemption, USB-entry filtering, hotplug/media
substitution or other workaround was selected. The integrator must settle the
USB identity contract (exact port/interface/LUN, per-boot QMP attachment and
verified image backing), while keeping exact GUID ownership, detached-device
refusal, number takeover, fixed-entry order, Windows-first, Linux ESP/loader,
BootNext and protected-disk checks intact.

### Zero-cost stage walk, updated before any dispatch

All rows below are **planned**, not newly executed evidence.

| Stage | Expected NVRAM transition / existing rule |
| --- | --- |
| Baseline and live probe/install, protected second | Attached target/protected/DVD/NIC auto set; exact GUID and per-boot QMP ownership. Full disk/GPT/EFI/zero-write audits unchanged. |
| Installer completion | Target-only Fedora ESP/loader entry may be created/moved; Linux-first is permitted before the Windows-first step (11f). DVD removal recorded at next boot. |
| Offline first stock / hardware reboot | Local kargs initialization, at most the recognized orderly reboot; full audits at each reached stop. No external NIC traffic or copied live Wi-Fi profile is permitted. |
| Shutdown / detached Windows round trip | Target auto removal and any firmware relabel/number recycling under 11e; Windows entry byte-identical and first, no BootNext left over. |
| **Tools stick attached, next Linux start** | **Expected USB auto entry has an unsupported device path: STOP here before dispatch.** Existing one-time Linux BootNext must still be exact, recorded and consumed. |
| Install/prepare/network/title/records | Once unblocked, bundle copy/install equality and physical commands; pause/cleanup/repair/pin; complete deployment/BLS equality after network. Flatpak completion is diagnostic only. |
| Signed switch and AresOS boots | Exact staged target; pinned corrected stock preserved; expected final pair; title refreshed after each reorder; Windows remains firmware default. |
| Plain-US failure, revert, successful change/back | Original administrator session remains open; fresh second-console password/physical proof before every permitted reboot; no deployment/NVRAM change from localectl. |
| Rollback, stock, keep-stock and next default boot | Exact saved checksum/serial/stateroot/ref/digest/pin, no unrelated pending work; refreshed titles; all protected/NVRAM/BootNext checks at every stage. |
| Final Windows and detached Windows | Exact Windows default/entry and unchanged protected data; permitted auto-set removals/relabels only. |

For later scheduling only, 13f's full job took about **69 rounded minutes**.
A preliminary allowance of 42 for the probe plus 130 per qualification and 12
for closing privacy would total **314/350**, leaving 248 of the currently 562
free org minutes, above the 150 reserve. This is an estimate, **not a dispatch
authorization**; the USB contract, complete host walk, local checks, fresh
complete-history/org guard and same-head probe must all pass first. No timeout
or budget constant was changed while blocked.

### Verified

Actual receipts and the full unchanged-suite log are in
[local-verification](../../os/manifest/ci/14/local-verification/result.json).

| Command | Actual result |
| --- | --- |
| `python -X utf8 reviews/14-owner-tools/verify-zero-cost.py --14b --listing .work/14/squashfs-files.txt --record` | Exit 0; `SOURCE-GATE-PASSED-14b`; all 53 retained hashes and the complete 1,439,437-line listing replay passed. Original result preserved. |
| `python -X utf8 reviews/14-owner-tools/verify-firmware-walk.py --record` | Expected native script exit **2**; `STOP-PLAN-GAP`; four source hashes and pinned whole-file binding passed; all three USB fixtures rejected. A subprocess readback independently confirmed returncode2. |
| WSL `python3 -m unittest discover -s os/tests -v` | **237 tests /169.476s**, exit1, **2 failures +9 error records in eight distinct cases**, 229 passed; no skips or weakened tests. Repo TMPDIR; denying `sudo` shim returned126 before privileged commands. |
| Targeted exact owner keyboard/switch blocks, `test_disk_audit`, `test_firmware_contract` | **26 tests /0.301s, OK**, after the guide additions; current owner blocks still exactly match the release scripts. |
| `pwsh -NoProfile -File reviews/10b-own-ssd-fixes/test-install-record.ps1` | **78 checks passed**, PowerShell7.6.8. Synthetic inventory/decoder guards and unelevated pre-check; no disk/firmware query or setting change. |
| `git diff --check` | Passed. |
| Unchanged-path comparison with `11728c5` | Active `os/ci`, `os/tests`, `os/release`, workflow and release manifest unchanged. |
| Frozen runtime comparison with `2abc12e8aa6089f7576143d1fbccb6648a3291bd` | Containerfile/context/lock/config/policy/base/keys/audit unchanged; no image build/publication. |

Local limitations are explicit: three greeter cases lack WSL Pillow; three
Homebrew cases require forbidden privileged tmpfiles/ownership/ACL operations
(including duplicate cleanup errors); the sysusers case requires privilege;
one auth-file mode case sees DrvFS0777 rather than0600. Nothing was installed
or elevated to make these pass. Native CI must run the whole suite successfully
before a future probe VM. **No new native CI or VM run happened.** No Gradle
build/client test ran, no mod changed, no product-green claim is made and no
Gradle daemon was started.

### Ledger and privacy

[BUDGET.json](BUDGET.json) continues the same package ledger; it does not reset.
Fresh complete history: **5 unique IDs /total_count5**, one page, all completed
privacy runs, **17 rounded pre-dispatch privacy minutes**. **0/1 probes, 0/2
qualifications, 0 VM/image/publication minutes**, first dispatch/start still
null. Closing privacy reserves **12** minutes; even charging all pre-dispatch
privacy conservatively gives **29/350**. No POST dispatch was sent.

Read-only org billing at **2026-10-25T18:40:40Z** reports **1,438/2,000 used**,
**562 free**; reserving12 leaves **550**, above150. Current-period SKU/zero-paid
checks passed. Repo remains private; PR13 is open/draft against main. Closing
head privacy results, actual minutes and log hashes will be recorded in the PR
body after this push, without a report-only push loop.

### Not verified / remaining acceptance

The owner bundle, Windows copy route, short commands, every-refusal fake-tool
trace coverage, prepare/rerun/record exports, guarded layout and command/bundle
equivalence are **not shipped or accepted**. No offline install, first stock
boot, tools USB boot, network-after-prepare comparison, token login, signed
switch, umlaut failure/revert, successful change/back, rollback/keep-stock or
next-default VM evidence was produced for package14. All physical/followability
gates remain open. PR13 must remain draft; acceptance is not met.

### JUDGMENT-CALL and open decision

No new device-path exception was chosen. Resuming the deferred-Flatpak work is
authorized by14b; extending the firmware path contract independently would
contradict11f's explicit stop instruction. The needed integrator decision is
the narrow USB identity/evidence rule above. The physical owner route remains
two sticks, offline until the checked pause; no third stick or manual-block
fallback was substituted.

For package15, the council findings1,4,8–11 listed in the original section still
stand. Add the tools round-trip acquisition/return checkpoints and the expected
NVIDIA notification when the tool route is actually qualified; do not present
the ignored development prototype as an available command. Physical installation
remains **NOT RELEASED**. No merge, force push, visibility change, real-laptop
operation or secret printing/storage occurred.


## 14c — tools stick after login, absent at every reboot

### Done

Pulled `e96310d` fast-forward first in this worktree; read briefs 14/14b/14c,
AGENTS, README, the install-gate council, current guides/scripts/harness and
retained evidence. Neither retired worktree nor the real laptop was accessed.
The 14b classification/source gate stands: install and first stock boot use
local content; copied live network profiles are forbidden; the NVIDIA runtime
sync remains enabled and nonblocking because it cannot change deployments,
BLS entries or disks. No image, package lock, frozen runtime or release changed.

The reviewed bundle lives in `os/owner-tools/`, including its generated
`payload/` and SHA256 manifest. The Windows module checks the actual volume,
partition and USB disk before the shared copy implementation, checks every
copied byte and sets ARESTOOLS. CI uses that same copy implementation on an
attested disposable file-backed exFAT image. The first RO bootstrap validates
label/manifest/disk identities and installs root-only tools under shared
`/var/lib/ares`; all later entry points recheck the manifest and private tree.
Python bytecode generation is disabled so execution cannot invalidate it.

Short commands save full dated diagnostics and print compact PASS/STOP results.
`prepare` uses the original pause, cleanup/pin and keyboard implementations,
repairs only the booted serial, verifies the entire list and untouched old
arguments, then pins. Rerun is observational. `title` validates the exact saved
stock checksum/serial/stateroot/origin/digest/pin and resolves BLS afresh;
its first post-network checkpoint requires the full list/pending/pin/BLS state
equal to prepare. `records` captures target/protected disk identities, full
partition tables and the target ESP/firmware mapping. `export` mounts the unique
manifest-matching USB itself, inspects conflicts RO, copies only private record
JSON with SHA256 readback, syncs and unmounts. Reboot refuses attached tools,
unfinished layout proof or a stale title. No stage requires the stick across a
reboot. Refusal diagnostics and transient RO inspection mounts are distinguished
from persistent deployment/service/disk/credential mutations in tests.

Login accepts the token only at a hidden physical terminal prompt, validates
read access to the exact private manifest in memory, then writes only the
mode0600 root-owned `/etc/ostree/auth.json`; no owner-token GitHub API call or
fallback. Verify/switch use the unchanged release scripts after guards. Recovery
requires the exact qualified pair; rollback on stock refuses and points to
keep-stock. The guarded layout trial keeps the original tty3 login open,
requires a fresh local login session on tty4 after the change/revert, loaded-map
readback, fresh password sudo and physical text; an unfinished trial prevents
reboot. Partial localectl failure restores the old settings and stops.

`owner_vm.py` follows the same command catalog through physical QMP keys. Its
NIC carrier is down before CPU start for the live install and first stock boot;
WebUI bytes use a bounded virtio-serial relay to the unchanged guest loopback
listener, with no request-body logging. The exact private release signature is
verified natively before this offline guest. Guest registry login happens only
at the owner's later step; no credential filesystem is shared with the guest.

Hotplug uses explicit file/raw block nodes plus USB storage on the existing
xHCI controller, after sign-in and a fresh whole-image hash check. After tool
unmount, QMP device_del must emit DEVICE_DELETED, both block nodes are deleted,
and guest absence is checked before reboot. Every inherited protected-disk,
zero-write/failure-counter, NVRAM, BootNext, Windows-first and detached-device
check stays unchanged. The firmware audit/decoder has **no USB exception**.
The pinned QEMU8.2.2 net/QAPI/USB source files and hashes are retained in
`os/manifest/ci/14/hotplug-sources/`; set_link controls peer carrier, blockdev-add
owns the exact backing file, usb-storage exposes removable, and device_del has
an explicit completion event. Host tests exercise those exact request shapes.

INSTALL §4–§6 and EMERGENCY retain their anchors and safety checks while replacing
hand-typed Linux blocks with the canonical commands. They explain offline
installation, the two-stick restore/copy round trip, Windows-first restoration,
hotplug/eject, title invalidation, complete recovery login/command/reboot/F12
steps, and the backup's installer-layout exception. The existing laptop gates
remain open; forgotten-stick-at-power-on is added as physically untested, never
an accepted audit rule. Nothing breaks if forgotten: do not choose it; unplug
and continue with Windows first.

### Updated zero-cost stage walk, before any dispatch

| Stage | Network / tools stick | Decision and required evidence |
| --- | --- | --- |
| Native preflight | host only; no VM | Complete local suite attempted first; complete native suite, PowerShell copy test, release/privacy/access checks before any VM. |
| Probe | link down; no storage USB at boot | Read-only installer review/keyboard proof/OCR, stock recipe and idle/failure-counter probes. Hotplug tools after live root login, verify manifest/hash, unmount/device_del before shutdown; detached Windows and blank-target reset. No install. |
| Live install | link down before CPU starts; no tools stick | Same pinned ISO, German installer choice and read-only localization diagnostic, full destination/summary/audits; no live KDE/KWrite automation. |
| First stock | offline; USB absent | Hardware setup and its permitted automatic reboot, actual raw statuses, no staged/pinned/queued transaction, authenticated login. |
| Windows round trip | USB absent for boot/comparison | Restore Windows first, unattended and detached Windows-like markers. Windows owner restores/copies/ejects stick only after Windows starts. |
| Tools stock | offline boot; hotplug only after fresh tty3 password login/sudo | Install, prepare, unchanged prepared rerun; accept one/two qualified stock serials. Record raw statuses before repair, old arguments untouched, pin exact booted identity. |
| First network | link up only after prepare; USB currently mounted only by tool | title/records require complete prepared state/BLS unchanged; record NVIDIA condition/state without waiting. Export with hashes, unmount/device_del, fresh title then guarded reboot. |
| Prepared Windows / corrected stock | no tools storage at boot | Unattended Windows marker, BootNext Linux, German loaded-map/public text/password sudo, exact prepared state. Old stock override permitted only for the exact unchanged old serial until switch finalization. |
| Private switch | network up; tools absent | Physical hidden login, verify, switch with same scripts; staged identity and full list, title refreshed/provisional, guarded reboot. |
| AresOS German | tools absent | Exact final pair, no surviving old serial, no overrides, real tty3 password sudo and foot text, policy/Homebrew. Plain US trial rejects a German-position second login; reboot refuses pending proof; revert to de, fresh tty4 login/sudo/text proof, finish. |
| Successful trial | no reboot with pending proof | US International console `us-intl`, X11 `us`/`intl`; unchanged umlaut password and physical `yz-/!ü` on fresh tty4, original tty3 finish. |
| AresOS US International / German return | no tools at either boot | New loaded map/physical tty3/sudo/foot/policy checks; second-console proof back to de, finish/title/guarded reboot. |
| Normal rollback | tools absent | Same pair/identity guard, queued stock identity, fresh BLS title before reboot; BootNext Linux to corrected pinned German stock. |
| Recovered/default stock | tools absent | Rendered greeter, exact map/pair, physical login/password sudo/text and Homebrew; rollback refuses with zero mutations, keep-stock/title/reboot; second unattended-within-Linux stock default. Final unattended and detached Windows markers. |

The host walk executes the actual qualification/console driver with explicit
stand-ins and retained 13f JSON. It is not VM evidence. It walks every newly
introduced command/layout/recovery branch, the QMP attach/detach/bad-hash paths,
and every typed string against exact ISO maps plus pinned QEMU physical codes.
Unknown characters still raise. Tests replay five real 13f states, the retained
11f staged update, prepare de/us/no-override/one/two-serial cases, bad images,
serials/stateroots/targets, manual clients/transactions/pending/foreign stages,
stock rollback and damaged bundles, with zero persistent mutations on preflight
refusals. Window-side wrong-drive/partial/tampered/duplicate cases also write
nothing. Expected operation/postcondition failures stop with diagnostics;
they do not claim an operation already started was atomic.

### Budget and stops

The same new package14 ledger starts at the first dispatch: **350 minutes,
1 probe, at most 2 owner-tools qualifications, 0 image/publish attempts**. Fresh
complete-history/job accounting and read-only billing precede every dispatch;
no force push, main push, merge, rerun discount or audit widening is allowed.

| Planned reservation before first probe | Minutes |
| --- | ---: |
| Probe job / native preflight | 42 |
| Qualification 1 (job timeout130; VM step106) | 130 |
| Qualification 2, only if a fresh complete-plan guard fits | 130 |
| Closing push/PR privacy allowance | 12 |
| **Total** | **314 / 350** |

The preliminary billing GET reports **531 free org minutes**; reserving314
leaves217, above the mandatory150. This is planning, not dispatch authorization;
fresh usage/history/privacy are required immediately before POST. Pre-dispatch
privacy costs are recorded separately; no probe or qualification has yet run.
No image rebuild, release or publication is authorized or scheduled.

### Not verified / physical gates

No VM result is claimed in this pre-dispatch section. Real NVIDIA Flatpak sync,
Media Writer restore labels/click path, physical media/eject, forgotten-stick
power-on, real laptop hardware/keyboard/menu/logind, live KDE/KWrite and novice
followability remain untested. Backup Bazzite keeps the installer layout; no
US-then-direct-rollback run is claimed. Physical installation stays NOT RELEASED.

### JUDGMENT-CALL

Use root-only shared `/var/lib/ares`, with a reviewed RO label-based bootstrap
and an installed manifest check on every later command. USB inspection mounts
are temporary access, not a new boot-device/firmware allowance. Use plain US only
for the deliberately failed login/revert and US International for a successful
change retaining the exact umlaut password, as approved in14c. These choices
are owner-review items; changing commands/bundle later requires regeneration,
equality tests and a new qualification. No frozen image changes are needed.

### For package 15

If text appears over the prompt after you plug in or remove the stick, press Enter to get the prompt back.

Rewrite the whole novice route and emergency card around these commands without
moving checks back into prose-only assumptions. Improve record navigation,
STOP/help/photo handling, the FMW German click path, two-stick round-trip/eject
reminders, recovery menu followability, account/session entry/exit instructions,
and laptop physical gates. Test the unaided reader including a forgotten stick
and damaged-battery refusal. Keep the explicit backup-layout exception and
NVIDIA deferred-work distinction. Preserve the canonical command/bundle tests.

### PLAN-GAP / open questions

The historic NVIDIA and firmware-USB gaps are resolved by the integrator's14b
and14c decisions. There is no stage requiring a stick across reboot. Any new
unsupported runtime/audit state stops before another dispatch; no fallback is
preapproved. Native/probe/qualification acceptance and final privacy remain
pending until recorded below.


### 14c local verification before dispatch

- `python reviews/14-owner-tools/walk-host.py`: focused owner tests and complete
  host route pass; source-bound result and every captured guest command are in
  `os/manifest/ci/14/host-walk/`. Stand-ins never start a VM. The final adapter
  check also exercises the existing marker's 30-second shutdown API; its keyword
  timeout is preserved by the new USB-absence hook.
- `pwsh -NoProfile -File os/tests/owner-tools.Tests.ps1 -Bundle os/owner-tools/payload -Work <new worktree folder>`:
  PASS11 zero-write destination/bundle refusals, pure copy equality and public
  Windows entry with Storage commands replaced by stand-ins. No real hardware
  query or label change ran. Manifest SHA256
  `c55de63b4290de42a9f3e1d2b3cffd51ef1c98f6bd979f263030e19bed27c5be`.
- Captured route syntax: PASS257 guest shell commands (`bash -n`) and233 embedded
  Python programs compiled; none executed. Python compilation and
  `git diff --check` pass. The actual shared switch/rollback Bash fixtures retain
  every negative assertion; the fixture now supplies the real rollback script's
  required previous-image metadata instead of relying on the former guide's
  shorter block.
- Whole discovery was rerun after fixture/workflow expectation fixes. WSL has
  eight distinct host-limited cases: three greeter pixel tests lack Pillow;
  three Homebrew tests require privileged tmpfiles/chown/ACL access; one sysusers
  test requires privilege; one credential-mode test sees DrvFS0777 instead of0600.
  The no-privilege shim returns126 for privileged calls. These are listed, not
  skipped or weakened. The complete native suite and Windows-copy check must
  pass in the probe preflight, confirmed via GitHub's completed step before any
  VM is authorized. Final local discovery counts/log are retained below.
- `git diff --quiet 775be05 --` the frozen runtime/config/policy/base/release,
  keys, package lock and image Containerfile paths: PASS, no changes. The
  firmware decoder/audit is unchanged. No Gradle daemon was started; no mod or
  real Minecraft path was used. Repository visibility remains private.


Final local discovery: **273 tests / 251.355s;265 pass;8 distinct host-limited
cases (2 failure and9 error records including cleanup);0 skips**. Focused host
walk: **36 tests PASS /26.251s**, all48 source hashes fresh. Exact local logs
and summary are retained in
`os/manifest/ci/14/local-verification/14c/`. None of these local failures is
reported green; the complete native suite must close them before any probe VM.

## 14c privacy stop before any VM dispatch

**STOP / PLAN-GAP:** the required privacy gate is not green. Both the push
[40230930408](https://github.com/Ares-Empire/AresOS/actions/runs/40230930408) and PR
[40230932763](https://github.com/Ares-Empire/AresOS/actions/runs/40230932763) fail
gitleaks with **5 findings**. Commit-email and personal-term steps consequently
skip; they are not claimed verified by those runs. No VM/native/image workflow
was dispatched after this failure.

The exact pinned portable Windows **gitleaks8.21.2**, downloaded inside this
worktree and checked against its publisher's release checksums, reproduces the
same5 findings with `git . --redact=100 --no-banner --log-level error
--report-format json --report-path <worktree scratch file>`. It was not installed
system-wide. An earlier portable Linux attempt could not interpret the Windows
worktree's Git-directory pointer, so it is not scan evidence. The Windows result
is authoritative here; no unredacted report or token was printed or stored.

All5 are **generic-api-key matches on SHA256 source-integrity pins**, introduced
by the host-walk manifest in commit `54337da`:

| Manifest location | Source whose Git blob hashes to the value |
| --- | --- |
| `os/manifest/ci/14/host-walk/result.json:58` | `os/ci/owner_keys.py` |
| same file, line61 | `os/ci/registry_auth.py` |
| same file, line72 | `os/manifest/ci/14/hotplug-sources/qapi_block-core.json` |
| same file, line73 | `os/manifest/ci/14/hotplug-sources/qapi_net.json` |
| same file, line74 | `os/manifest/ci/14/hotplug-sources/qapi_qdev.json` |

[Finding metadata](../../os/manifest/ci/14/privacy-stop/findings.json) retains
rule IDs, exact commit/file/line fingerprints and classification, without
credential values. [Scanner provenance](../../os/manifest/ci/14/privacy-stop/scanner.json)
retains the official download/checksum URLs and verified binary/archive hashes.
`python reviews/14-owner-tools/verify-privacy-pins.py` independently reads each
manifest line from that commit and recomputes SHA256 of the corresponding Git
blob: **all5 match**. These values are integrity pins, not authentication
credentials. No real token was entered into the new tools or a guest this run.

The pinned scan should have run locally **before** pushing the manifest. A
forward-only file edit cannot remove its original committed history from a
history scan. Rewriting the pushed commits would require the explicitly
forbidden force push; exempting findings would change the privacy check. Under
AGENTS hard rule5 (never weaken/skip/delete a test to get green) and brief11c's
required privacy checks, neither is done. No `.gitleaks.toml`, ignore list or
privacy workflow change was made. The integrator must settle this verified
source-pin false-positive before the remaining native/probe/qualification work
can proceed; no exception is inferred from its noncredential classification.

### Final execution/budget state

The [complete-history ledger](../../os/manifest/ci/14/privacy-stop/ledger.json)
accounts for **all11 branch runs**, with complete total_count/unique-ID proof.
All were normal push/PR privacy checks; **34 rounded pre-dispatch privacy
minutes** precede the closing report push. The package's first-dispatch start is
still null: **0/350 package minutes,0/1 probes,0/2 qualifications,0 image or
publication attempts**. The latest read-only billing response reports526 free
org minutes;12 closing-privacy minutes are reserved, leaving514, above150.
No billable usage or new credential scope was requested. Closing privacy checks
are expected to remain blocked by the same historical findings and are not a
waiver or a VM dispatch.

Native273-test acceptance, the fresh one-probe gate, actual offline VM install/
first boot/network checkpoint, tools-media QMP runtime, physical command/login/
layout failure/revert/US International success, switch/rollback/default-stock
and their protected-disk/NVRAM/BootNext evidence remain **NOT VERIFIED for14**.
The36 focused tests, full local273-test attempt (eight documented host limits),
Windows11 refusal cases, syntax checks and source gates remain valid local
results. They do not substitute for this missing VM qualification. INSTALL,
EMERGENCY and the release gate explicitly retain NOT RELEASED and the open
physical items. PR #13 remains draft. Branch pushes are fast-forward only;
no merge, force push, image rebuild, release or publication occurred.
