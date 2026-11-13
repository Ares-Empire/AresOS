# 22c: every way back works after an update — builder report

Brief: `briefs/22c-ways-back-after-update.md`. Branch `pkg/22c-ways-back-after-update`, cut from main `6cca14b6`.
PR #46 (draft). Stages 1a, 1b and 2 are not started. Shorthand as in the brief: R27 the newer AresOS, R13 the
older one, S the pinned stock.

## Stage 0 (P): the reorder probe

**Said first, as the brief asks:** no capture contradicts P6, rule A2 or rule A3. Three things the brief does not
say were found:

1. After a reorder, the running kernel's `ostree=` argument resolves to another deployment. The link is named by
   the row's place in the list, and the place then holds another row. rpm-ostree's `booted` and bootc's `booted`
   stay right. Nothing may find the running system through that link.
2. All six reorders took ostree's link-swap path (`Transaction complete; bootconfig swap: no`). The three
   deployments share one boot checksum and the same kernel arguments. `/boot/loader` and the entry files never
   changed; only `/ostree/boot.0` flipped between `boot.0.0` and `boot.0.1`. Rule 3's `sync` is needed.
3. bootc's `spec.bootOrder` reads `rollback` whenever the running row is not first, `default` otherwise.

The probe job itself ended red: see "Runs" and JUDGMENT-CALL 6.

### Done

- **Mode `reorder-probe`, package key `22c`, on this branch only.** `.github/workflows/os-image.yml` (option, package
  key, job condition, every step package 27's update rehearsal runs; bounds for this branch: job 345 minutes, VM
  step 315, reservation 345), `os/ci/rehearsal-packages.json` (1200 minutes, `vm_dispatch_cap: 4` for all VM modes
  together), `os/ci/rehearsal_guard.py`, and every list that named packages 14, 16 and 27:
  `owner_media.require_runner`, `registry_auth`, `owner_capabilities`, `owner_devices`, `installer_webui`,
  `two_disk_vm`, `owner_vm.main`.
- **The probe:** `os/ci/reorder_probe.py` (new) and `reorder_probe`, `reorder_boot` in `os/ci/owner_vm.py`. Package
  27's route up to release 27 confirmed, with the 15f tools (`3ef85c4a…`) and then version 2 from history
  (`41b06513`, `851eb742…`). Then six moves with plain `ostree admin set-default <index>`, a restart after each, one
  stock start from the boot menu, a last restart. Every expectation is recorded as met or contradicted and the walk
  goes on; the run fails at the end if one was contradicted.
- **Shared route:** `owner_vm.update_rehearsal` is split into `laptop_update` and `confirmed_update`. `laptop_payload`
  takes a commit and fingerprint; `owner_media.Media.replace` can copy a bundle from history.
- **Local walk:** `os/tests/test_owner_walk.py`, route `reorder-probe`, over `LaptopDisk`, a modelled disk that is
  held to the VM captures.
- **Host walk:** `reviews/22c-ways-back-after-update/walk-host.py` writes `os/manifest/ci/22c/host-walk.json` (257
  sources); `owner_vm.main` selects it and refuses a stale one.
- **Tests:** `os/tests/test_ways_back_probe.py` (new, 40 tests); `test_release27.py` demands `22c` in every package
  set; five tests that pin workflow lines follow them.
- **Captures:** `reviews/22c-ways-back-after-update/runs/reorder-probe-43470161858/` (76 files), taken by
  `reviews/22c-ways-back-after-update/collect.py`.
- **Pending rebind:** `os/manifest/ci/16/pending-rebind.json` lists 18 bound files (4 waited before).

### Runs and budget

| Run | Kind | Head | Result | Minutes |
|---|---|---|---|---|
| 43468641559 | checks-only | `f81fab91` | passed: 969 tests, 136 skipped | 9 |
| 43470161858 | `reorder-probe`, VM dispatch 1 of 4 | `f81fab91` | walk, menu choice and 21 audits through; job red on the probe's own check | 110 |
| 43489340083 | checks-only | `0c560a16` | passed: 973 tests, 136 skipped | 6 |

125 of 1200 minutes, 1 of 4 VM dispatches. One run at a time on this branch: the guard stops a VM run while
another run is queued or running, and on two passing checks-only runs of one head.

### Stage table (run 43470161858)

| Stage | Reached by | Order | Runs | bootc booted / rollback | rollbackQueued | Pinned | Titles top to bottom | Swap |
|---|---|---|---|---|---|---|---|---|
| `walk-0-start` | release 27 confirmed | R27 R13 S | R27 | R27 / R13 | false | S | 0 R27; 1 R13; 2 S | |
| `walk-1-moved` | set-default 2 | S R27 R13 | R27 | R27 / S | true | S | 0 S; 1 R27; 2 R13 | no |
| `walk-1-booted` | restart, no choice | S R27 R13 | S | S / R27 | false | S | 0 S; 1 R27; 2 R13 | |
| `walk-2-moved` | set-default 1 | R27 S R13 | S | S / R27 | true | S | 0 R27; 1 S; 2 R13 | no |
| `walk-2-booted` | restart, no choice | R27 S R13 | R27 | R27 / S | false | S | 0 R27; 1 S; 2 R13 | |
| `walk-3-moved` | set-default 2 | R13 R27 S | R27 | R27 / R13 | true | S | 0 R13; 1 R27; 2 S | no |
| `walk-3-booted` | restart, no choice | R13 R27 S | R13 | R13 / R27 | false | S | 0 R13; 1 R27; 2 S | |
| `walk-4-moved` | set-default 2 | S R13 R27 | R13 | R13 / S | true | S | 0 S; 1 R13; 2 R27 | no |
| `walk-4-booted` | restart, no choice | S R13 R27 | S | S / R13 | false | S | 0 S; 1 R13; 2 R27 | |
| `walk-5-moved` | set-default 1 | R13 S R27 | S | S / R13 | true | S | 0 R13; 1 S; 2 R27 | no |
| `walk-5-booted` | restart, no choice | R13 S R27 | R13 | R13 / S | false | S | 0 R13; 1 S; 2 R27 | |
| `walk-6-moved` | set-default 2 | R27 R13 S | R13 | R13 / R27 | true | S | 0 R27; 1 R13; 2 S | no |
| `walk-6-booted` | restart, no choice | R27 R13 S | R27 | R27 / R13 | false | S | 0 R27; 1 R13; 2 S | |
| `menu-stock` | stock row taken in the menu | R27 R13 S | S | S / R27 | true | S | 0 R27; 1 R13; 2 S | |
| `after-menu-booted` | restart, no choice | R27 R13 S | R27 | R27 / R13 | false | S | 0 R27; 1 R13; 2 S | |

"Pinned" is the same in rpm-ostree's flag and in the origin file (`[libostree-transient] pinned=true`). The title
column gives the `(ostree:N)` number and the row it starts. Every title is `Bazzite (ostree:N)`; the files are
`ostree-3.conf` (first row) to `ostree-1.conf`.

### Answers to P6

- **`set-default` removes the row and inserts it first; the others keep their order; nothing is created or removed:**
  yes, six of six. Identities, references, digests, versions and flags were equal to the first capture at all 15
  stages.
- **The stock stays pinned and its boot options stay the same:** yes, at all 15 stages. R27's and R13's options
  stayed the same too.
- **A start with no choice runs the first row, also the stock (greeter, German login):** yes, seven of seven. The
  stock ran three times (twice by order, once from the menu), each time with the password typed in German key
  positions on tty3 and a rendered greeter.
- **`rollbackQueued` is true whenever bootc's rollback slot comes before the running row:** yes, at all 15 stages. The
  slot was always the first other deployment.
- **Does `(ostree:N)` equal the row's place?** Yes, at all 15 stages.
- **Swap path:** `Transaction complete; bootconfig swap: no` for all six, printed and logged once each
  (`OSTREE_DID_BOOTSWAP=no`, `OSTREE_BOOTLOADER_ATOMIC=yes`).
- **Versions:** ostree 2026.4-1, rpm-ostree 2026.3-2, bootc 1.16.13-1, grub2-common 2.12-66 (all fc44).

### Verified

- Local, Python 3.14.8, one module at a time from the repository root: `test_ways_back_probe` 40, `test_owner_walk`
  27, `test_owner_equality` 9, `test_checkout_sources` 5, `test_owner_step_limits` 4, the five pinned-line modules,
  the guard and budget modules, and `test_release27`'s wiring classes (19), all OK.
- Hosted: the two checks-only runs above. `test_ways_back_probe` and `test_owner_walk` passed there in full.
- Package 27's route is unchanged by the split: its qualification and update walks on a copy of `6cca14b6` and on
  this branch have the same stages, guest commands, typed text, checks and markers. Only the two values each walk
  draws at random differ.
- The modelled disk reproduces every committed capture (`CapturesTest`); a disk whose `set-default` appends, or
  that names another rollback slot, does not.
- The committed captures hold no token, credential, password hash or UUID (checked by `collect.py` before writing
  and by `CapturesTest`).

### Not verified

- A green probe job, and the corrected check in a VM.
- The laptop itself. That a reorder takes the link-swap path there is shown for the VM only.
- Staging and finalize over three rows (not in stage 0).
- `test_owner_update` and the owner-tools modules that fail under Python 3.14 were not run locally. Hosted,
  `test_owner_update` skips 136 namespace tests (PLAN-GAP 3).
- The branch against today's main (`591e9a42`).

### JUDGMENT-CALL

1. The plain commands run in the harness's root shell on the serial console, not typed on tty3: it returns output
   and exit status as data.
2. The walk runs with the VM's network link down from the first restart after the confirmation, so nothing else can
   stage a deployment.
3. One bound for both modes of this branch (job 345, VM step 315 minutes), keyed on the branch name, so stage 2
   need not edit the pinned workflow lines again.
4. The probe records contradictions and goes on instead of stopping at the first.
5. Committed captures: the VM disk's filesystem UUID and the boot ids are replaced by fixed words, the same word for
   the same value; rpm-ostree's and bootc's JSON are as the guest gave them. The image's own labels inside that JSON
   name the earlier image repository, as `os/manifest/releases/13.json` already does.
6. No second probe run for a green job. Run 43470161858 met every point of P6 with every audit unchanged and ended
   red on a check the brief does not ask for. A rerun would be VM dispatch 2 of 4 and give the same captures. The
   integrator decides.

### PLAN-GAP

1. Package 11's `select_grub_menu` and `stock_bls_entry` needed no adapting to three rows. The probe adds the
   screen-reading loop around them. The menu was driven with this harness's PS/2 keyboard for the first time.
2. `owner_vm.py`'s route for package 27 had to be split to be shared; the brief lists `owner_vm` only among the
   lists to extend.
3. The hosted suite skips all 136 namespace tests of `test_owner_update.ToolsUpdateTest` (`unshare: write failed
   /proc/self/uid_map: Operation not permitted`), in the checks-only job and in the rehearsal job. The brief relies
   on hosted runs for that module and 1b asks for none skipped. The hosted jobs need unprivileged user namespaces
   allowed; that is a workflow change the brief does not name.
4. The probe does not record its bound sources; D's record step belongs to stage 2.

### For the next stage

- Never find the running row through `/proc/cmdline`'s `ostree=` link; use rpm-ostree's `booted`.
- The fake must model the link-swap path: entry files and titles fixed by place, the links under `/ostree/boot.0`
  swapped, the journal line `Transaction complete; bootconfig swap: no`. `test_owner_walk.LaptopDisk` does and can
  serve as a start.
- bootc's `spec.bootOrder` changes with the order; a comparison of whole bootc states must expect that.
- Stage 2 adds its mode in: the workflow's `options` and the job condition's mode-and-branch clause; the mode
  tuples in `owner_media.require_runner`, `registry_auth.require_dispatch`, `owner_capabilities.main`,
  `owner_devices` and `owner_vm.main`; and the ledger (`dispatch_caps`, `job_bounds`, `titles`).
  `test_ways_back_probe` reads the modes from the ledger and then demands the rest.
- After any change to a file the host walk binds: `python3 reviews/22c-ways-back-after-update/walk-host.py`, then
  `python3 reviews/27-first-update-release/rebind.py pending "<note>"`. `HostWalkReceiptTest` fails on a stale
  receipt.
- `owner_vm.laptop_update(..., bundle=(folder, fingerprint))` types version 2's bootstrap line built by this
  checkout's `bootstrap.py`. If stage 1 changes `bootstrap.py`, check that line.

### Integrator's decisions on this stage (2026-11-13)

- JUDGMENT-CALL 6: no second probe run now. The captures meet every point of P6 and are what stage 1's fake is held to; the job was red on a check the brief does not ask for, which is corrected. If stage 2 passes with dispatches to spare, the corrected probe runs once more for a green record.
- PLAN-GAP 3: main's checks-only job allows unprivileged user namespaces since 27c (PR #47), so hosted checks-only runs no longer skip the 136 tests once this branch has main merged in. The rehearsal job gets the same step in this package when stage 2 adds its mode.
- Stage 1a starts from this report with a fresh builder. Its first step is to merge `origin/main` (27c changed the workflow's checks-only job and its waiting-list row) and regenerate the host walk and the waiting list.
