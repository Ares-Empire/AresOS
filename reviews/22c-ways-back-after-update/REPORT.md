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

## Stage 1a, step 1: the state machine

Stage 1a is cut into three runs. This is the first: section A in `os/owner-tools/owner.py`, the new release
script, and the tests that pin each rule directly. The model (B2) and the tools 2-to-3 tests (B8) are the next two
runs. Head after this step: see the last commit of the branch; main (`16a0c886`) is merged in.

### The merge of main

One conflict, in `os/manifest/ci/16/pending-rebind.json`: main's two 27c notes and file row against this branch's
stage 0 note and rows. Resolved by keeping every change note of both sides; the file rows and the 22c host walk
were regenerated (`walk-host.py`, then `rebind.py pending`), not merged by hand. `.github/workflows/os-image.yml`
merged without a conflict and holds both sides (27c's namespace step and 25-minute limit; the probe mode).

### Built, rule by rule

- **Rules 1 and 2** (`qualified_state`): before the first switch the two states of version 2, by the same checks
  and messages, returning `None`. With AresOS installed: the saved pinned stock, one or two known releases, at most
  one staged target in front of a running AresOS that is first; any order, any running member. It returns the rows
  by role (`stock`, `ares`, `staged`, `booted`), which every command then uses.
- **Rule 3** (`Tools.may_change`, `Tools.start_next`, `os/release/start-next.sh`): the read-only preflight, the
  intent, the script (re-read, index by checksum and serial, digest and reference, nothing staged, one
  `ostree admin set-default`, `sync`, re-read and compare), then the postcondition (the same rows, the target
  first, the others in their old order), boot entries equal, the record, a fresh title.
- **Rule 4** (`update`, `previous`, `recover`, `select`, `login`): each word a destination. A destination that is
  already first writes nothing and says whether it runs. `rollback` and `keep-stock` refuse on the other side
  after the resolution and name the other word. `update` (c) reorders to the newest installed AresOS and says the
  bundle's release is newer still, with the next step.
- **Rule 5** (`journalled`, `Tools.outcome`, `intend`, `completion`, `finish`, `archive`): one journal for staging
  and every reorder, with `schema` (`change1`), `mode`, `word`, `boot`, `target`, `running`, `before`, `intended`
  (and `staged` for a staging record). `outcome` returns `retry`, `complete`, `pending` (waits for the restart),
  `applied` (applied, nothing waits), `done` (confirmed by a later boot), `elsewhere` (in place, not yet started),
  or `None` after archiving `not-applied`. Only `title` confirms. A new change archives the open record as
  `confirmed`, `applied-not-restarted`, `in-place-not-started` or `retried`.
- **Rule 6** (`may_stage`, `update`, `reconcile_update`): staging only from a running AresOS that is first; the
  line names the other AresOS, whichever it is; the second line when the running one is the older; the stop
  routine deletes nothing unless the staged row is the only row before the running one.
- **Rule 7** (`layout`, `repair_notes`): begin and abandon no longer use the pair check; abandon works on any
  system; a trial whose finish had begun leaves a note in `layout-repair.json` when it is abandoned elsewhere, and
  `layout abandon` on the note's deployment restores the old settings. **Built, not tested**: see "Not built".
- **Rule 8** (`standing`, `role`, `name`): the title's first two lines with AresOS installed, and the cause only
  where a record proves one.
- **Rule 9**: `history.json` says tools version 3; `journalled` reads version 2's records; an unknown schema
  refuses. The tools-update journal is untouched.
- **Rule 10**: the staged-row STOP comes first in `qualified_state`, so every command gives it; `title` prints
  the updater finding as a `WARNING:` line; `keep-stock` STOPs on it; `update` never reads it.
- **Rule 11** (`typed`): every message that names a command builds it there.
- `os/owner-tools/bundle.py` lists `start-next`; the payload is refreshed (fingerprint `28900bf1…`, which changes
  again in 1b). The three old scripts stay in the payload until 1b.

### Not built in this step

- **B7, the layout tests.** Rule 7's code has no direct test yet. The next builder must write them before
  trusting it: begin and abandon with three deployments, begin refused on stock and with a change waiting, abandon
  on stock from the menu, and the repair sequence.
- B2 (the model), B8 (tools 2 to 3), B10 (the fixture test), B11's table, and B3 as a whole: the machine in
  `test_owner_update.py` now models `set-default` (it also drops a staged row), `sync` and `cleanup --pending`'s
  rule, but finalize lives in `test_ways_back.restart`, and the machine still logs a script as a mutation before
  the script's own checks.
- **B9, the changed expectations in the older modules.** `test_owner_update.py`'s classes `ShapeTest`,
  `UpdateCommandTest`, `PreviousTest`, `LoginTest`, `OutcomeTest` and `IntentTest` still pin version 2's refusals
  and its journal fields (`kind`, `pending`, `expected`). The hosted run under "Verified" lists what fails. None of
  them was weakened or deleted.
- `preflight_recovery` is no longer called by the tools. It is still in `owner.py` because tests in six modules
  call it; delete it together with those expectations.

### Verified

- Local, Python 3.14, one module at a time: `test_ways_back` 29 tests OK, plain and with `-B`;
  `test_checkout_sources` 5, `test_owner_step_limits` 4, `test_ways_back_probe` 40, `test_owner_walk` 27, all OK
  on the pushed head.
- Hosted checks-only, two runs (about 12 minutes each; 149 of 1200 minutes used so far, still 1 of 4 VM dispatches):

| Run | Head | Result |
|---|---|---|
| 43494381106 | `dba353e8` | 1002 tests, 150 failures, 50 errors, 0 skipped. 135 of them were one bug of this step: `main()` has a local named `command`, which hid the helper of that name, so every entry through `main` STOPped. Fixed by naming the helper `typed`. |
| 43496675626 | `962283c5` | 1002 tests, 40 failures, 23 errors, 0 skipped. `test_ways_back` passed (29). The 136 namespace tests ran. The head after it adds only this report. |

What fails in run 43496675626, and why (counts are failing tests and subtests):

- **Expectations that change on purpose (B9), not yet rewritten:** `test_owner_update` `IntentTest` 22 (it reads
  the journal's old fields `kind` and interrupts a script named `previous`), `OutcomeTest` 8 and `PreviousTest` 5
  (they pin "did not finish at the restart", `bootc rollback`, the direction refusal), `UpdateCommandTest` 7 (the
  old refusals `rollback is queued`, `already deployed`, `Final pair has extra/missing deployments`),
  `ShapeTest` 2 (`stock not last`, `stock booted beside two releases`, and the pair check), `LoginTest` 1,
  `LockTest` 1, `HistoryTest` 1 (tools version 3), `ToolsUpdateTest` 4 (its newer test bundle is version 3 too;
  it needs version 4). These are tests of the state machine and of the tools update: **they must be rewritten to
  the new rules in the next runs, not left for 1b.**
- **Fakes that do not answer the updater read on running stock (rule 10's warning in the title):**
  `test_owner_abandon` 6, `test_owner_commands` 1, `test_owner_path` 1, `test_owner_retained` 1. Their hosts need
  `systemctl list-unit-files`, or `paused_state` patched as `test_owner_update.route` does.
- **The fingerprint (1b):** `test_owner_bootstrap` 1, `test_owner_equality` 2, `test_owner_path` 1.

`test_ways_back` by class: `ShapeTest` 8 (all 4 pair and 18 triple combinations, the names and the row map,
version 2's queued pair, wrong sets, rule 10 in every order, before the first switch, the updater warning, the
command helper), `ScriptTest` 3, `DestinationTest` 5, `JournalTest` 7 (among them every cut of every reorder,
each followed by no restart and by a start of each row), `StagingTest` 6.

### Changed lines so far

- New PASS lines: `<name> runs and starts next`, `<name> runs; <name> starts next, after the restart`,
  `<name> runs; <name> starts next; this start was not the default`,
  `<name> runs and now starts next; no restart is waiting`, `Boot menu at the next start: …`,
  `Boot menu after the update finishes at shutdown (expected): …`, `<Name> already starts next; nothing changed`
  with `It runs now` or `It does not run yet: it starts at the next restart`, `Newest AresOS starts next <ref>`,
  `Newest installed AresOS starts next <ref>`, `<Change> is in place and has not started yet`,
  `Newer AresOS <ref> is removed when the update finishes at shutdown` and the settings line after it.
- Kept as they were: `Saved stock rollback queued`, `Saved stock is default`,
  `Previous AresOS queued for the next start <ref>`, `Older AresOS <ref> is removed …`, the two confirmation lines.
- Reworded STOPs: the two side refusals, `Only one AresOS is installed …`, `… waits for the restart: restart
  first …`, the interrupted-update STOP (it now names `update`), `… did not finish as recorded (…)`.

### JUDGMENT-CALL

7. Rule 6's two lines when `update` stages from the older AresOS are built as owner decision 5 says.
8. `update` goes to the newest installed AresOS from anywhere (owner decision 1), built as rule 4 says.
9. Rule 10's message says "the installed AresOS" in place of "both AresOS releases" when only one is installed.
10. The old PASS lines for `rollback`, `keep-stock` and `previous` stay word for word; they name the system by the
    old words, and the title's first line names it by role and digest.
11. A note that rule 5 resolved something (`… was not applied …`, `The interrupted … had made its change; it is
    recorded now`) is printed before the command's own result, also before a STOP (`Tools.notes`, printed by
    `main`).

### PLAN-GAP

5. Rule 1 says every AresOS is "unmodified"; rule 9 says version 3 accepts every state version 2 accepts, and
   version 2's `check`, `title` and `reboot` accept a modified AresOS. Built: every change (reorder, staging,
   `layout begin`) refuses a modified AresOS, as known limit 3 says; `check`, `title`, `records` and `reboot` do
   not look, so he keeps working commands.
6. Rule 2 lets nothing depend on `rollbackQueued`. `qualified_state` still compares bootc's rollback slot and flag
   with the order (first other row; queued when the running row is not first), as the probe showed at all 15
   stages. Nothing is decided by it, but a bootc that ever disagreed would STOP every command. No capture has a
   staged row over three deployments, so with something staged only `rollbackQueued` false is required, as today.
7. In the boot that staged, a staging record whose staged list is gone STOPs every command, `update` included,
   as version 2 does ("changed before the restart"). After a restart rule 5 resolves it as not applied. The model
   should say whether that same-boot state is reachable (a `cleanup --pending` typed with Help).
8. A repair note for a deployment that a later update removed stays in `layout-repair.json`. It blocks nothing.

### For the next builder

- **Run locally:** `cd os/tests && nice -n 10 python3 -m unittest test_ways_back`. It imports
  `test_owner_update` as a library (`machine`, `Machine`, `route`, the rows); importing is safe on the laptop,
  running that module is not.
- **The three states.** `outcome` never merges them: "applied" is `keys == intended`; "restart waiting" is that
  with `boot == boot_id()` and a target that does not run (`pending`); "confirmed" needs another boot id and the
  target running (`done`), and only `title` archives it. `applied` and `elsewhere` leave the record open.
- **What differs from the brief**, for the model's own rules: the points under PLAN-GAP 5 to 7 and JUDGMENT-CALL
  9 to 11; a destination that is already first runs no `title` and writes nothing but the command's receipt;
  `keep-stock` checks the updaters before it answers "already starts next"; before the first switch the title
  prints no new line and `update`, `previous`, `rollback` and `keep-stock` refuse; `(ostree:N)` is read from the
  entry's title, and "starts next" marks the first deployment.
- **For the compatibility tests:** `journalled()` turns a version 2 record into version 3's form (`update` →
  staging, `previous` → reorder with the target first). A version 2 intent that is in place becomes a `change1`
  record. `system_ready()` calls `qualified()`, so a tools update can archive or record the open journal with the
  new tools' code before they are published: check that this is what rule 9 wants.
- **For 1b:** the fingerprint pins, the three old scripts out of the payload, `preflight_recovery` out, the
  guides' quoted lines above.

## Stage 1a, step 2: layout tests and the model

### Part (a): layout tests (B7)

- Added five direct layout tests to `test_ways_back`, backed by `ways_back_keyboard.py`:
  three-row begin/abandon, refusal on stock/non-default AresOS/while waiting, menu-stock abandon without
  persistent writes, the interrupted-finish repair round trip, and the repair note's staging lock with the
  R28 test bundle. The latter also exercises previous, rollback, check and reboot, then repair and staging.
- Each deployment has separate persistent console/X11 settings. A `PowerCut` between the real
  `set_keyboard` method's two fake localed calls bypasses normal exception cleanup. No host keyboard
  command executes. The direct tests use synthetic R21/R30 as the brief's R27/R28, as step 1 does.
- Local: `cd os/tests && nice -n 10 python3 -m unittest test_ways_back` printed
  `Ran 34 tests in 11.761s`, `OK` (7187 MB available before it). No code defect was found by B7;
  `owner.py` is unchanged in this part. The full model and fixture/revert proofs follow in part (b).
