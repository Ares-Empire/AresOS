# 22c: every way back works after an update — builder report

Brief: `briefs/22c-ways-back-after-update.md`. Branch `pkg/22c-ways-back-after-update`, cut from main `6cca14b6`.
PR #46 (draft). Stage 0 is captured; step 2b closed the model under the destination follow-up.
Stage 1a is complete at the checkpoint below: only four stage-1b fingerprint pins fail. Stages 1b and 2 are not started. Shorthand: R27 the newer AresOS, R13 the older one, S the pinned stock.

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

### Part (b): model checkpoint — STOP, the brief's rules conflict

**This is not completion of B2 or a green stage 1a.** The builder stops under the instruction to report a
required rule change instead of making one. A4(b) and A6 require staging R28 from a running/default R13,
even when R27 is installed. B2 also requires every installed system to be selectable by one command in
that resting state. No defined command can select R27 there.

Reproduction, with the R28 test bundle:

1. Start `[R27*, R13, S]`; `previous`; restart with no menu choice: `[R13*, R27, S]`.
2. `title` confirms and archives the previous record. Nothing is staged, no restart is waiting, no trial or
   repair note exists, and all settings are whole. The conflict also exists before that title.
3. Independently try each destination command from that same state:

| Word | Required result under A4/A6 |
|---|---|
| `update` | Stage R28: `[R28(staged), R13*, R27, S]`; finalize removes R27. |
| `previous` | R13 already starts next; nothing changes. |
| `rollback` | S starts next. |
| `keep-stock` | STOP: AresOS runs, so use rollback. |

`ModelTest.test_brief_conflict_new_bundle_cannot_select_newest_installed_in_one_command` verifies this
counterexample against the real entry points, including the title that closes the journal. The separate
`ModelTest.test_reachable_state_space` retains B2's assertion and **fails** on the R13 default state.
It is not skipped, marked expected-failure, or changed to accept this gap. The request to add no hosted
failure cannot be satisfied together with that assertion and the instruction not to change a rule.
The hosted comparison below distinguishes this one new name from the inherited failures.

### Done in part (b)

- `os/tests/ways_back_ledger.py`: independent immutable event ledger. It imports no owner code or fake-host
  code. State includes named deployments, running identity, stage, full open journal, trial/session/boot
  equivalence, repair notes, and separate console/X11 settings for every installed deployment. All three
  profiles are explicit. Selection applied, restart waiting, and target boot confirmed stay separate.
- `os/tests/ways_back_host.py`: the B3 fake used by the model and the fixture tests. It runs the real
  reorder/update script assertions with intercepted subprocess calls, records mutations only at primitives,
  implements staged-row dropping on list writes, destructive cleanup's real rule, finalize's new/pinned/
  booted/merge/other-stateroot retention, and settings inheritance. bootc slots and boot order are independent
  of owner helpers. Reorders keep entry files fixed and swap the positional links, including the stale
  kernel link demonstrated by stage 0. Running identity always comes from the `booted` row.
- `os/tests/test_ways_back_model.py`: real `Tools` entry points over private in-memory records and the fake.
  The expected transition is computed from the ledger **before** calling the tools; their return values
  never choose the oracle branch or the next queued state. State comparisons include journal fields,
  archives, confirmations, persistent settings, pins and boot-entry identities. Power cuts bypass normal
  cleanup after intent, primitive, record, layout finishing intent, console write and both persistent writes.
  Each reachable phase has restart/default/menu-choice and power-off successors. Refused commands have no
  reached primitive at which to inject a cut.
- B10: all **15** stage-0 deployment/layout captures replayed through that same fake, with six set-default
  outputs and journal messages, every slot/flag/pin, unchanged entry bytes and their new resolved identities,
  and the misleading positional kernel link. Captured entry arrays follow directory enumeration, so files
  are compared by filename, not array position. Five older retained pair/first-switch captures also bind
  slots, queued flags and boot order. There is **no real triple-finalize evidence** here.
- B11's four named executable mutant proofs: append instead of prepend fails the stage-0 fixture; retaining
  bootc's rollback row fails the independent finalize retention assertion; a side check before resolution
  fails the rollback cut/restart-on-stock path; requiring the recorded target to run fails the rollback/
  restart-on-R27/check path. Four short regression paths preserve the defects below independently of where
  the exhaustive walk stops.
- Four narrow `owner.py` fixes, described below. Its payload copy and generated manifests were refreshed
  because tests read the payload; no guide, fingerprint pin, release/history pin, or commands.json changed.
  Generated payload fingerprint: `d2b40b50…`.
- Regenerated the 22c host walk, then the pending-rebind rows (25 bound files). Package 27's receipt is untouched.

### Defects found in the state machine, and fixes

The exploratory walk found these before the full invariant audit. Each sequence now has a short regression
in `RevertTest.test_the_four_found_defects_have_short_replaying_regressions`. No destination rule changed.
The tests use synthetic R21/R30 references as R27/R28, consistently with step 1.

1. **Unannounced removal at a staging cut (A6/B2).** `[R27*, R13, S]`, R28 bundle; `update`; cut immediately
   after bootc stages, before the completion record/returned output; a normal shutdown can then finalize
   and remove R13. The removal line previously existed only in returned output after recording. Fix: print
   `At shutdown, this update removes <role> <reference>` after intent and before staging. The previous
   completion lines and return values remain unchanged. The cut test failed with `unannounced removal`.
2. **`check` offered no way out of a runtime trial (A8/B2).** `[R13*, S]`; `layout begin us`; `check`.
   It STOPped with only `Loaded console keys differ from system layout`. Fix: while a trial exists, name a
   fresh physical administrator login, `sudo /var/lib/ares/at layout abandon`, then `sudo /var/lib/ares/at check`.
   Outside a trial the line now ends `; get help`. The check/recovery path leaves every deployment intact.
3. **Revert erased repair authorization after interrupted finish (A7).** `[R13*, S]`; begin US; proof;
   cut after the finish's console persistence; `layout revert` in the original session; fresh login;
   `layout abandon`. Revert cleared `proof`, so abandon refused the exact recorded half-written setting.
   Fix: before clearing proof on a finishing trial, retain it as `finish_proof`; abandon accepts that saved
   evidence too. Revert still requires a fresh proof before finishing. No arbitrary partial setting is accepted.
4. **A second trial stranded an existing repair note (A7).** `[R27*, R13, S]`; begin US, proof, cut after
   console persistence; boot R13; abandon (note for R27); `previous` makes the running R13 default;
   begin a trial on R13; boot R27; abandon. R27's exact partial setting was rejected before its own note's
   repair loop. Fix: while abandoning another deployment's trial, also accept the exact partial value
   authorized by this running deployment's existing repair note; the existing loop then restores it.
   The other deployment's `/etc` is never written.

### Verified locally

All commands ran in this worktree; tests ran one module at a time with `nice -n 10`, after `free -m`
showed at least 4500 MB available. No `test_owner_update` suite, full local suite, Gradle, VM or real owner
command ran. That module was imported only as a fixture library.

| Command/module | Result |
|---|---|
| `cd os/tests && nice -n 10 python3 -m unittest test_ways_back` (part a) | 34 tests, 11.761s, OK. |
| Same command after all four fixes and payload refresh | 34 tests, 12.110s, OK. Printed the new pre-staging removal lines. |
| `nice -n 10 python3 -m unittest -f test_ways_back_model.CaptureTest test_ways_back_model.FakeRulesTest test_ways_back_model.RevertTest test_ways_back_model.ModelTest.test_brief_conflict_new_bundle_cannot_select_newest_installed_in_one_command` | 11 tests, 0.242s, OK. |
| `nice -n 10 python3 -m unittest test_ways_back_model` (final local run) | 12 tests, 1.508s, **1 failure**, the B2/A4 conflict. The other 11 passed. |
| `python3 os/owner-tools/bundle.py --refresh` | `PASS bundle manifest SHA256 d2b40b50…`. |
| `python3 reviews/22c-ways-back-after-update/walk-host.py` | `PASS package 22c host walks (reorder-probe): 257 sources; no VM started`. |
| `python3 reviews/27-first-update-release/rebind.py pending "22c stage 1a step 2: layout/model regressions, four narrow fixes; B2 blocked by A4 destination conflict"` | `pending: 25 bound files differ from the active bindings`. |
| `git diff --check` | No output, success. |

**Size and time of the state space:** closure was **not reached** and no total size is claimed. The strict
model's final local run printed `417 discovered states, 151 checked states, 3602 edges, 1.293s; closure NOT
reached` before failing B2. Earlier transition-only exploration found defects 3 and 4 after 14.957s and
138.475s. A later exploratory run was stopped after 27,416 discovered states / 550,034 edges to bound work
and inspect runtime. Another was stopped after 20,000 checked states / 34,689 discovered states. A ledger-only
counting experiment (no Tools proof) was stopped after 980,000 expanded states / 1,183,904 discovered states /
24,213,237 edges at 276.37s; these are lower bounds, **not** completion evidence. The three processes were
interrupted by their own recorded PIDs, and their temporary directories cleaned by context managers. The
unfinished model will need runtime work after the rule conflict is settled; do not dispatch it as a claimed
full-state proof merely because the short counterexample is fixed. No asserted test was skipped to obtain green.

### B11 assertion map and its limits

The executable mutants above were run. The following maps every existing A rule to its guarding assertion;
this is **not** a claim that every row has had a separate production-code mutation run. Completing that campaign,
and the full model, remains open at this stop. All names below are in `test_ways_back` unless qualified.

| Rule removed | Assertion that detects it |
|---|---|
| A1, accepted deployment sets | `ShapeTest.test_wrong_sets_keep_refusing`, and `test_before_the_first_switch_nothing_changes_and_rule_10_does_not_speak`. |
| A2, free order/running member | `ShapeTest.test_every_order_and_running_system_of_the_pair_and_the_triple_is_accepted` (22 combinations). |
| A3, exact reorder/sync | `ScriptTest.test_reads_immediately_before_one_set_default_syncs_and_checks_the_result`, `test_a_wrong_list_afterwards_or_a_failed_call_fails`; `DestinationTest` compares exact rows and calls. |
| A4, named destinations | `DestinationTest.test_each_word_moves_only_its_target_to_the_front_from_every_order_and_system`; the new counterexample separately pins A4(b). **B2's stronger promise is blocked.** |
| A5, resolve first/three outcomes | `JournalTest.test_every_cut_of_every_reorder_resolves_from_the_list_alone`, `test_applied_nothing_waits_is_its_own_outcome_and_the_next_start_decides`; the two new journal mutants fail the model assertions. |
| A6, staging/retention/settings | `StagingTest.test_staging_from_the_older_aresos_prints_both_lines_and_finalize_keeps_three`, `test_completion_is_right_with_the_stock_in_the_middle`; the new finalize mutant fails `retention after finalize`. |
| A7, trial/repair ownership | All five new `LayoutTest` methods; the two new multi-trial/revert regressions compare every deployment's persistent settings. |
| A8, truthful title/next step | `ShapeTest.test_the_names_are_roles_with_a_short_digest_and_the_row_map_follows_the_boot_entries`, `JournalTest`'s same-boot confirmation assertions; new `check has no executable next step` assertion. |
| A9, schemas/compatibility | `JournalTest.test_any_other_list_stops_and_an_unknown_schema_refuses` covers unknown schemas. **Version 2 compatibility and its revert proofs remain B8, step 3.** |
| A10, stock updater protections | Both `ShapeTest` methods beginning `test_a_staged_row_on_running_stock` and `test_stock_updaters_warn`. |
| A11, one command helper | `ShapeTest.test_one_helper_spells_every_command_as_commands_json_does`. |
| B3 fake rules | `test_ways_back_model.CaptureTest.test_append_instead_of_prepend_fails_the_fixture`; `RevertTest.test_finalize_that_keeps_bootcs_rollback_fails_retention`; `FakeRulesTest` tests cleanup, list writes, other-stateroot/merge retention, and pre-primitive refusal. |

### JUDGMENT-CALL

12. No A4/A6 rule was widened to satisfy B2. A new command or changed `update` behavior would change the
    owner's destination/settings rule; excluding that resting state would change the invariant. None was chosen.
13. The removal notice is streamed before staging in addition to the existing completion summary. Removing it
    later would reopen the power-cut gap; the quoted completion lines are preserved.
14. `finish_proof` preserves authorization already earned by the interrupted finish while `proof` can be cleared
    for a new proof after revert. It is additive to layout records; no tools-update journal field changed.
15. If a running deployment needs repair while another deployment has an active trial, `layout abandon` can
    clear the other trial and repair the running deployment under its own recorded old settings in that call.
    Rejecting the call stranded the repair. No stock trial or arbitrary mixed profile becomes allowed.

### PLAN-GAP / not verified / open questions

9. **Blocking:** B2's one-command invariant contradicts A4(b)/A6 in the concrete sequence above. The integrator
   must settle the rule before another builder can finish the model; this report chooses neither alternative.
10. Even before closure, the independent ledger has over 1.18 million discovered states with all profiles and
    repair-note histories. Full execution must be made practical without collapsing the three journal outcomes,
    losing per-deployment settings/repair notes, or deriving expectations from the code. No full-space claim here.
11. B10 has the committed stage-0 and older pair captures; stage 2 has no captures yet. It still needs its future
    fixture hook. Triple-finalize is held only by the independent retention assertion and its mutant, never by
    a purported VM fixture.

Not verified: exhaustive closure/all-state invariants, all per-rule production mutations, tools 2-to-3 (B8),
old expectation/fake rewrites (B9), guides, fingerprint pins, stage 1b, VM rehearsal or physical laptop behavior.
No real keyboard, deployment, boot, system or window operation was performed. `.work/` had no file over
500 MB at the closing size check; no large download was made. No temp file was created outside the worktree.

### For the next builder

1. Read the **blocking A4/A6 versus B2 counterexample first**. This is a stop with a failing invariant, not a
   completed step 2 handed directly to step 3. `test_reachable_state_space` must not be disabled or marked an
   expected failure. The runtime issue also remains before a full-space acceptance claim.
2. The older module is still import-only on this laptop. Run only the changed safe modules locally, separately
   under `nice -n 10` after the memory check. Hosted checks remain necessary for the full suite.
3. B8 must include an interrupted finishing layout followed by revert: `finish_proof` may exist alongside
   `proof: null`. Old records without that field still use their original proof. `layout-repair1`, `change1`
   and `tools-update1` schemas are unchanged; the tools-update journal itself was not edited.
4. B9 still has step 1's 51 old expectations plus the nine older-fake updater failures. None was rewritten here.
   Preserve A4(b)/A6's staging-from-older behavior until the integrator changes the brief. The new pre-staging
   removal line is streamed; existing returned completion lines remain. `check`'s layout mismatch STOP now
   names fresh-login abandon. Do not reintroduce either layout dead end described above.
5. Reuse `ways_back_host.Host` and its fixture tests when extending the model; do not derive a running row from
   the positional kernel link. Initial fixture entries are immutable input; later link targets are simulated.
   The unfinished walker currently seeds the historical R13/S pair and the laptop triple. Add the R27/S pair
   explicitly too, so B2's target-already-installed pair is a seed under both bundles; that seed is not yet walked.
6. The payload was refreshed for source consistency only. Stage 1b still owns all published fingerprint pins,
   guides and the bundle/script removal work. Regenerate the host walk before the waiting-list generator after
   any further bound edit. No VM was dispatched in this step.

### Hosted check and final stop

`gh workflow run "OS image" --ref pkg/22c-ways-back-after-update -f checks_only=true`, followed by exactly one
blocking `gh run watch 43506717597 --exit-status` invocation (exit 1). No VM dispatched.

| Run | Tested head | Result |
|---|---|---|
| [43506717597](https://github.com/Ares-Empire/AresOS/actions/runs/43506717597) | `9dd4fc82cf525040ac8a86515d15f7260ce4f292` | **1019 tests in 736.154s; 41 failures, 23 errors, 0 skipped.** |

Hosted: `test_ways_back` **34 passed**; `test_ways_back_model` **12 run, 11 passed, 1 failed**. The strict model
printed `417 discovered states, 151 checked states, 3602 edges, 2.053s; closure NOT reached`.

A multiset comparison of every `FAIL:`/`ERROR:` header against baseline run 43496675626 found:

- Added: **only** `test_reachable_state_space (test_ways_back_model.ModelTest.test_reachable_state_space)`.
- Removed: none. All 63 inherited failure/error entries remain. There is no second new failure hidden behind
  the expected red baseline.
- The sole additional failure is the unresolved brief contradiction, not a claim of a passing model.
  Making it green needs a rule decision; the builder has not waived the invariant to satisfy the no-new-failure
  request. The test and the counterexample remain reviewable at this stop.

Small committed evidence: `runs/checks-43506717597.json`. The final commit changes only this report and that
receipt; the tested implementation stays at the head above. Temporary fetched logs under `.work/22c-step2/`
were removed after comparison. No file over 500 MB remains in `.work/`; no outside-worktree temp directory was
used, and no builder-started test or watch process remains. PR #46 is still open and draft; nothing merged.

## Stage 1a, step 2b: the model closed

This continues step 2 under `briefs/22c-b2-destination-invariant.md`. A4 and A6 are unchanged.
B8 (tools 2-to-3), B9 (the old expectations), and stage 1b remain separate work. No VM was dispatched.

### Done

- **The destination decision:** `ways_back_ledger.destination_paths` keeps the one-command assertion for
  every resting destination except the newer installed AresOS when an older AresOS runs first and the
  bundle's release is absent. It walks the menu choice, `update`, restart and `title`, and requires the
  target first, the same-boot **applied** outcome, then the later-boot confirmation and closed journal.
  `ModelTest.test_new_bundle_stages_and_the_newer_installed_release_has_a_walked_menu_path` executes that
  path against Tools. Its other branch still requires `update` to stage R28, name the removed release,
  and say whose settings R28 inherits. A6's repair-note lock remains: repair first if the running `/etc`
  has a note. Part (a) was committed and pushed as `318584c6`.
- **Closure:** the starts are R13/S, R27/S, and the laptop's R27/R13/S, each with the R27 and R28 bundles.
  `test_reachable_state_space` drains its queue; no depth, time, state-count cutoff or expected-failure
  marker terminates it. It prints and pins the resulting state/edge counts and checks all eight journal
  outcomes were visited. Each command's normal result and reachable intent/primitive/record cuts,
  layout proof/revert/finish/abandon, all three profiles, finish's two persistence boundaries, fresh
  login, default/menu restart and power-off without finalize are included.
- **Equivalence:** deployment roles, this/earlier boot, original/fresh trial session, and omitted archives,
  receipts and timestamps are as B2 requires. The additional future-equivalence removes journal
  provenance (old running identity and before-order) once the current rows and the recorded outcome
  determine it; mode, word, phase, target, boot age and outcome stay distinct. After a trial crosses a
  boot, old proof/reverted flags cannot affect a permitted command: proof/revert/finish refuse, while
  abandon still retains old/new/finishing and the recorded authority. Notes for a removed release are
  omitted **only from the search key**, since a fixed bundle cannot reinstall that removed release.
  Full records stay in each representative and are checked at each incoming edge. All live notes,
  installed console/X11 pairs, and the loaded profile remain literal. `EquivalenceTest` checks matching
  successors and actual Tools on each kind of quotient and rejects merging the three journal outcomes,
  a live repair, or an installed `/etc` pair.
- **Execution reuse:** `ways_back_memo.Executions` records the actual environment reads of each Tools
  execution. A later edge reuses its observed writes and output only if those input values match.
  Unread settings are carried through unchanged; restart reads the chosen deployment's settings too.
  Idempotent writes include their prior value. This is separate from state equivalence: the queue still
  explores each full live settings vector. Expected transitions are calculated first by the independent
  ledger and never selected by Tools' return value. A test compares reused and uncached execution with
  all three nonrunning layout profiles. Host boot events change record ages without sharing their
  provenance. The independent finalize assertion is checked by the real fake on every new observed
  input combination, including the deliberately broken finalize.
- **B10:** all 15 committed stage-0 deployment captures still replay through the same `Host` used by the
  model, including all six reorder outputs/journal messages, slots, queued flags, pins, immutable entry
  bytes, resolved entry identities, and the misleading positional kernel link. Five older retained
  pair/first-switch slot captures still pass. The fixture test now discovers every probe run and checks
  its replayed files equal **all** `*-deployments.json` files under this package's runs directory. New
  stage-2 captures therefore fail until their operation replay is registered; they cannot be silently
  ignored. No real triple-finalize capture has been invented or claimed.
- **B11:** `test_ways_back_reverts.py` supplies the remaining per-rule mutations in memory. They rerun the
  named assertions or the independent driver; an unrelated exception is explicitly rejected as a
  successful proof. Existing append/finalize/journal mutants and the four earlier defect paths remain. A final audit also
  requires the complete layout record (including finish authority) and all persistent profile fields to
  match before reconstructing a successor. Removing finish-authority preservation now fails at revert
  itself, before a later adapter could supply the missing field. This audit is `63a293ef`; parts (b) and
  (c) were pushed separately as `50aec9b8` and `030eeebc`.
- No production state-machine change, payload refresh, guide, bundle pin or fingerprint change was needed
  in this continuation. Only tests/model support, the pending-rebind notes and this report/receipt change.

### The closed space and its command table

The model closes at **486,627 states and 12,176,910 steps**, with **249,475 actual executions**
and **11,927,435 reuses of executions with the same observed inputs**. The final plain local run took
**371.901s** for the walk (**372.878s**, 15 tests, for the module). The final `-B` repeat took **376.743s** for the walk (**377.552s**, 15 tests, OK).
Both visited exactly the same states, edges, execution/reuse counts and journal outcomes.
The early ledger-only enumeration took 147.871s; that was a sizing experiment, not implementation evidence.
The full hosted timing and per-command edge counters are in the receipt linked below.

| Journal outcome | Reduced states |
|---|---:|
| none | 101,352 |
| not-applied | 149,682 |
| retry (staging intent, before primitive) | 261 |
| complete (staging primitive done, record missing) | 261 |
| waiting for restart | 42,051 |
| selection applied this boot | 66,384 |
| target boot confirmed, awaiting title/archive | 53,388 |
| in place, not yet started | 73,248 |

The table describes every reduced state's command behavior by its state predicates; the test's counters
count every edge, including refusals and cuts. These are synthetic Tools/host results, not VM observations.

| State predicate | `check` / `title` / `records` | Destination commands | Layout commands / way out |
|---|---|---|---|
| Resting, bundle target installed, no trial | Accept; title confirms only an earlier boot on the target | `update` selects newest, `previous` selects older if two, `rollback` on AresOS / `keep-stock` on S selects S | Begin only on first/running AresOS with no repair note |
| Resting, bundle absent, first/running AresOS | Accept | `update` stages bundle (unless repair note); previous/stock words retain their destinations; newer installed release uses the menu path below | Repair note: abandon on its own deployment before staging/begin |
| Resting, bundle absent, S runs or running AresOS is not first | Accept | `update` reorders newest installed, names the newer bundle and next step; no download | Begin refuses on stock or on a nondefault AresOS |
| Selection already first | Accept | Matching destination is a no-op; no new journal | Existing layout/repair locks still apply to an actual change |
| Same-boot staging intent, before primitive or before record | STOP names `update` | `update` retries staging or records its already-applied primitive; other list readers STOP | Restart/power-off resolves from the list, preserving the two possibilities |
| Change waiting this boot / staged record | Accept and describe restart waiting | A new change refuses; an already-first destination remains a no-op | Begin refuses; any available restart choice clears stage/waiting |
| Applied this boot, target already running | Accept, explicitly no restart waiting, no confirmation | New changes work and archive `applied-not-restarted` | Trial may begin under ordinary ownership rules |
| Earlier boot, target runs | Title/check/records confirm and archive; reboot itself does not confirm | A new change archives `confirmed` | Trial/repair locks still apply |
| Earlier boot, another installed row runs | Accept: in place, not yet started | New changes work and archive `in-place-not-started` | Ordinary trial/repair rules |
| List back at before | Resolve/archive `not-applied` before the command's own checks | Continue under ordinary destination rules | Same resolution before begin/abandon |
| Active layout trial | Check accepts or names fresh-login abandon for a runtime/system mismatch | Actual changes refuse; no-ops keep their usual behavior | Original-session proof/finish, revert then proof/finish, or fresh-login/restarted abandon; crossed-boot proof/finish/revert refuse |
| Interrupted finish / repair note | Check remains usable or its named recovery succeeds | No staging from the affected system; reorders and restart remain available after the active trial ends | On its owner, abandon restores old console **and** X11; on another system it preserves both `/etc`s and retains a bound note |

### Invariants (one line each)

1. **Usable check:** check passes, or its named update/fresh-login-abandon path reaches a passing check without deleting a deployment.
2. **Destinations:** every unlocked installed destination is one command away, with exactly the integrator's newer-installed/menu exception and its walked confirmation path.
3. **Restart:** every available default/menu choice, with finalize or a power-off before it, leaves no staged deployment and no same-boot restart wait.
4. **Trials end:** each permitted proof/finish, revert/proof/finish, or fresh-login/restarted abandon path ends the trial; its endpoint remains in the checked state space.
5. **Layout ownership:** a mixed console/X11 pair has its own trial/note, abandon there restores its recorded old pair without writing another `/etc`, and staging cannot inherit that mixture.
6. **Retention:** finalize leaves exactly new release, previously running release, stock, in that order; a fourth row or any missing row fails.
7. **Refusal/reorder:** refusals preserve actual rows/pins/entries; reorders preserve identities, settings and other-row order and execute one primitive followed by sync before recording.
8. **Removal:** only a staged row can disappear at a power-off/stop, and only the announced other AresOS can disappear at finalize.
9. **Confirmation:** an applied selection, a restart waiting, and a later target boot are different; only title (also via check/records) prints and archives the confirmation.

### Defects found

**No new state-machine defect was found in step 2b.** `os/owner-tools/owner.py` is unchanged. The four step-2
regressions above still execute: unannounced removal after a staging cut, check's runtime-trial dead end,
revert losing finish authority, and abandoning a second trial while the running deployment has a repair.
Their sequences and fixes remain in step 2's "Defects found" section; none was broadened or reverted.

An early execution-cache prototype treated archive filenames (timestamps) as state and failed with
`nondeterministic environment read order`; it was corrected to observe only the varying live inputs.
A later trial run was interrupted to factor host boot-age changes and track the *chosen* deployment's
keyboard read. Final audit found the adapter could reconstruct `finish_proof` before a later step without
first proving the preceding revert preserved it. The complete-record check and the new authority mutant
close that gap. These were test-harness corrections, not owner-tool defects or waived model assertions.

### B11 revert proofs

Every row below was executed. The first twelve are `test_ways_back_reverts.RuleRevertsTest`; the last rows
reuse the model module's existing proofs or its fake-rule assertions. A9's **version-2 compatibility**
mutants remain B8; its unknown-schema rule is proved here.

| Removed rule / mutant | Assertion that fails |
|---|---|
| A1: allow a third installed AresOS without a stage | `test_a1_third_installed_release_guard` → `ShapeTest.test_wrong_sets_keep_refusing`, expected STOP absent |
| A2: require running row first | `test_a2_running_member_need_not_be_first` → driver `accept/refuse` on title with S running beside the triple |
| A3: omit sync | `test_a3_reorder_requires_sync` → `ScriptTest.test_reads_immediately_before_one_set_default_syncs_and_checks_the_result`, exact call sequence |
| A4: previous selects max/newest | `test_a4_previous_names_the_older_release` → driver `ledger differs`, target/order/journal |
| A5: same-boot applied means confirmed | `test_a5_applied_on_this_boot_is_not_confirmed` → driver `ledger differs`, open journal prematurely archived |
| A6: ignore running repair note | `test_a6_repair_note_blocks_settings_inheritance` → driver `accept/refuse` after finish-console cut, menu S, abandon, menu R27, update |
| A7: abandon elsewhere discards repair note | `test_a7_abandon_elsewhere_keeps_a_bound_repair_note` → driver `ledger differs`, note missing after the console-cut/menu-S path |
| A7: revert erases the interrupted finish authority | `test_a7_revert_preserves_the_interrupted_finish_authority` → driver `finish authority lost`, before reconstructing any successor |
| A8: omit identity-based menu map | `test_a8_title_has_the_identity_based_menu` → ShapeTest's exact role/digest/entry-row lines |
| A9: accept unknown journal schema | `test_a9_unknown_schema_refuses` → JournalTest's unknown-schema STOP/unchanged assertion |
| A10: keep-stock omits updater check | `test_a10_keep_stock_checks_updaters` → ShapeTest's expected updater STOP absent |
| A11: command spelling bypasses the shared helper | `test_a11_one_command_spelling` → ShapeTest's commands.json equality |
| Fake cleanup removes only the stage | `test_b3_cleanup_must_remove_unpinned_preceding_rows` → FakeRulesTest's exact retained identities |
| Fake list write keeps a nonfirst stage | `test_b3_a_list_write_must_drop_a_nonfirst_stage` → FakeRulesTest's exact retained identities |
| Fake queued flag is always false | `test_b3_queued_flag_follows_order` → stage-0 capture's `rollbackQueued` equality |
| Fake set-default appends | `CaptureTest.test_append_instead_of_prepend_fails_the_fixture` → `walk-1-moved: order, identities, pins and stage` |
| Fake finalize also retains bootc rollback | `RevertTest.test_finalize_that_keeps_bootcs_rollback_fails_retention` → **B2 driver `retention after finalize`**, four rows instead of three; no fixture claim |
| Side check before resolution | `RevertTest.test_side_check_before_resolution_fails_the_rollback_cut_path` → `ledger differs` after rollback primitive cut, menu S, rollback |
| Require recorded target running | `RevertTest.test_requiring_target_to_run_fails_a_boot_menu_start` → `accept/refuse` after rollback, menu R27, check |

### Systems reachable only through the boot menu

In the **unlocked resting states**, the only exception is R27 with the R28 bundle in either
`[R13*, R27, S]` or `[R13*, S, R27]`. R13 already starts next; rollback selects S; update stages R28.
To retain/select installed R27: choose its boot-menu row, run update there (selection applied, nothing
waiting), restart normally, then title confirms R27. This remains the destination path if R13 has a
repair note, although update on R13 first refuses and names layout abandon, as A6 requires.

Active trials and same-boot waits intentionally impose temporary locks: choosing a different row before
ending the trial/restarting requires the menu. Ending the trial or taking the requested restart restores
the ordinary commands. During staging, the announced other AresOS will be removed at finalize; it is not
promised as a post-finalize menu destination. A power-off *without* finalize preserves it, as separately
walked by the model. Stock-side protections and wrong-side command refusals do not remove the proper way
back (`update`/`previous` from stock, `keep-stock` there, `rollback` on AresOS).

### Verified

All local tests ran one module at a time under `nice -n 10`, after `free -m` showed at least 4500 MB available.
`test_owner_update` was imported as a library only. No full local discovery, Gradle, system command, VM,
owner-session input or window was used. Temporary test stores were inside this worktree.

Commands below ran from `os/tests` unless a repository-root command is shown. Long model runs used
`python3 -u` and redirected output into `.work/22c-step2b/`; `-f` was used on the final plain runs to stop
immediately on a failure. Neither option changes which successful tests run.

| Command / test selection | Printed result |
|---|---|
| `nice -n 10 python3 -m unittest test_ways_back_model.CaptureTest test_ways_back_model.FakeRulesTest test_ways_back_model.RevertTest test_ways_back_model.ModelTest.test_new_bundle_stages_and_the_newer_installed_release_has_a_walked_menu_path` (part a) | 11 tests, 0.193s, OK |
| `nice -n 10 python3 -u -m unittest test_ways_back_model` (first cache prototype) | 12 tests, 4.351s, 1 failure: timestamp-dependent cache read order, corrected |
| Same command, next prototype | Interrupted by this builder at the last printed 40,000 processed / 59,941 discovered / 978,308 edges, 82.938s, to factor host events; no completion claim |
| Same command, first full closure | 12 tests, 385.586s, OK; model 384.907s |
| `nice -n 10 python3 -u -m unittest -f test_ways_back_model` (with equivalence tests and stronger invariants) | 15 tests, 414.120s, OK; model 413.230s |
| `nice -n 10 python3 -m unittest test_ways_back_model.EquivalenceTest` (after no-op cache fast path) | 3 tests, 0.149s, OK |
| `nice -n 10 python3 -B -u -m unittest test_ways_back_model` (before authority audit) | Interrupted to replace it with the audited run; last printed 250,000 processed / 310,272 discovered / 6,179,554 edges, 192.391s; no completion claim |
| Focused model classes plus destination path after the authority audit (the first row's command plus `test_ways_back_model.EquivalenceTest`) | 14 tests, 0.307s, OK |
| **Final** `nice -n 10 python3 -u -m unittest -f test_ways_back_model` | **15 tests, 372.878s, OK; model 371.901s, queue exhausted** |
| **Final** `nice -n 10 python3 -B -u -m unittest test_ways_back_model` | **15 tests, 377.552s, OK; model 376.743s, queue exhausted** |
| `nice -n 10 python3 -m unittest test_ways_back_reverts` before / after authority mutant | 14 tests, 0.474s, OK / **15 tests, 0.521s, OK** |
| `nice -n 10 python3 -B -m unittest test_ways_back_reverts` before / after authority mutant | 14 tests, 0.527s, OK / **15 tests, 0.553s, OK** |
| `python3 reviews/27-first-update-release/rebind.py pending "<part-specific note>"`, after each of a/b/c and the authority audit | Four runs, each `pending: 25 bound files differ from the active bindings` |
| `git diff --check` | No output, success |

A source-list comparison found **no changed file bound by the 22c host walk** in this continuation; that
receipt and package 27's receipt were not regenerated. The normal pre-push checks were never bypassed.
Part a, part b, part c and the authority audit were each committed and pushed separately.

The exploratory ledger-only command imported `ways_back_ledger`, used `deque(starts())`, applied every
`events(s)` transition, checked `invariants(s)` and keyed successors by `reduced(s)` until empty. It printed
`DONE 486627 12176910 147.87064183599796`; it never substituted for the Tools execution proof.

### JUDGMENT-CALL

16. Applied the integrator's explicit decision: installing a newer bundle while the older release runs
    makes update stage that bundle. The rejected alternative, routing through the newer installed release
    first, would change A4/A6 and the owner's settings choice. Revisiting this requires a rule decision,
    destination assertions and owner-facing guidance; it is not an incidental test adjustment.
17. Used future-equivalence and observed-input execution reuse to make the complete model practical.
    An unreduced history/product walk was the rejected alternative: step 2 had already exceeded a million
    states without closure. This changes no owner behavior. If future events change bundle targets or
    reinstall a removed release, the dead-note equivalence must be revised; if the environment gains a
    new varying input, its read must be recorded. Live settings, repair ownership and journal outcomes
    are not dropped to save time.

### PLAN-GAP / not verified / open questions

12. The follow-up resolves step 2's blocking destination contradiction. Its update-stages assertion must
    still respect A6's explicit repair-note refusal; the model tests both, without weakening either rule.
13. No stage-2 captures exist yet. The fixture inventory gate now requires their operation replay when
    they are committed. Neither stage 0 nor stage 2 proves finalize over three installed rows; a real
    capture of that remains the **next update release's gate** from the original brief.

Not verified here: tools 2-to-3 compatibility (B8), rewritten old expectations/fakes (B9), stage 1b's guides,
commands/bundle/fingerprint pins, stage 2, physical keyboard typing, real shutdown durability or any VM
behavior beyond the already committed stage-0 captures. The complete model covers staging/finalize from
`[R27*, S, R13]`, staging from `[R13*, R27, S]`, and triple finalize synthetically. First installation with
version 3 remains the direct tests/B8's concern. No rule change is requested and no new blocking question
was found.

### For the next builder

1. **Read the three journal outcomes and the new destination exception first.** Preserve A4/A6: update
   from default/running R13 with an absent R28 stages R28; the way to installed R27 is menu R27, update,
   restart, title. With a repair note on R13, update must name abandon and refuse staging, with no fallback
   reorder. The prior "B2 blocked" statement is historical; the model now closes and must stay green.
2. **B8:** source/tools-update journal were unchanged in this continuation. Keep step 1's version-2 record
   migration and tools-update publication checks. Include interrupted finish → revert, where
   `finish_proof` can coexist with `proof: null`; old records without the additive field keep working.
   Keep `tools-update1`, `layout-repair1` and `change1` compatibility separate from the no-unknown-schema
   revert proof completed here.
3. **B9:** the baseline log has 50 failure/error headers in test_owner_update, nine older-fake entries
   and four stage-1b fingerprint pins. These 63 entries remain inherited (the earlier handoff described
   the first group as 51 expectations; the header comparison counts 50). Do not rewrite the new assertions to accept old pair-only, direction-only,
   target-must-run or same-boot-confirmed behavior. Keep the streamed pre-staging removal notice, the two
   completion lines, the fresh-login abandon next step, and both multi-trial repair fixes.
4. Reuse `ways_back_host.Host`; its cleanup, list-write, slots and finalize rules have executable mutants.
   Running identity comes from `booted`, never the positional kernel link. Keep all six seeds, literal
   live per-deployment settings, the eight journal outcomes, queue exhaustion, and the model counters.
   Expected transitions stay independent of Tools; cache hits are observed execution effects, not oracle
   results. Alter the equivalence deliberately if a new event invalidates its stated proof.
5. Run only the changed safe modules locally, separately and at nice 10 after the memory gate. Full counts
   still come from hosted checks-only. Stage 1b still owns the pins/guides/old-script removal; no payload
   refresh was needed here. If editing a bound source, regenerate the 22c host walk before rebind pending.
6. When stage 2 commits captures, extend the fixture operation replay; the all-captures inventory assertion
   will reject an unregistered directory. Do not claim those fixtures prove triple finalize. The next
   release still needs that real capture and the original brief's release gates.

### Hosted check and closing state

Final implementation head: `63a293ef277daa333ff2de31ceacc5d12c29bc1a`. Dispatched with
`gh workflow run "OS image" --ref pkg/22c-ways-back-after-update -f checks_only=true`, then one blocking
`gh run watch 43513299977 --exit-status` (exit 1, the expected inherited red suite).

| Run | Result | Focused modules |
|---|---|---|
| [43513299977](https://github.com/Ares-Empire/AresOS/actions/runs/43513299977) | **1037 tests in 1368.427s; 40 failures, 23 errors, 0 skipped** | `test_ways_back` **34/34**, `test_ways_back_model` **15/15**, `test_ways_back_reverts` **15/15** |

The hosted model printed **486,627 states, 12,176,910 edges, 249,475 executions, 11,927,435 reuses,
620.304s; queue exhausted**. Compared with run 43506717597's exact `FAIL:`/`ERROR:` header multiset:
**no added entry**, and **only** `test_reachable_state_space (test_ways_back_model.ModelTest.test_reachable_state_space)`
removed. The 63 inherited entries remain: 50 headers in `test_owner_update`, nine older-fake entries, and
four fingerprint/guide-pin entries. Their complete names, all command-edge counters, journal-outcome
counts and menu-only states are retained in [checks-43513299977.json](runs/checks-43513299977.json).

The preliminary checks-only run [43512715278](https://github.com/Ares-Empire/AresOS/actions/runs/43512715278)
on `030eeebc` was cancelled after the layout-authority audit required a new test head. It produced no full
counts and is not completion evidence. It also had exactly one blocking watch invocation, which exited 1
on cancellation. Its metadata is included in the final receipt. No VM was dispatched in either run.

The closing commit changes only this report and the receipt; the tested implementation remains the head
above. Temporary logs, the comparison script and interrupted-run files under `.work/22c-step2b/` were
removed. No temporary directory outside this worktree was created; all test-store contexts are closed.
The final `.work/` size check found **no file over 500 MB**; no large download was made. No builder-started
test or watch process remains. PR #46 stays open and draft; no merge or push to main occurred.

## Stage 1a, step 3: the old expectations and the compatibility tests

Done: B9, B8 and their B11 proofs, including two narrow production fixes. Builder model: GPT-6 (Codex).
Final implementation `8d236619` has 1059 hosted tests, four stage-1b failures, zero errors and zero skipped.
No VM dispatched and no owner entry executed on this laptop. `test_owner_update` remains import-only here; its complete results come from hosted checks.

### B9: changed expectations

No test is deleted or skipped. Renamed methods below keep the old scenarios and assert their replacement
rule; the unchanged invalid-shape, identity, signature, interruption and no-write checks remain. The earlier
handoff's “51” means 50 failure/error headers (including subtests), not 51 separate methods.

| Test (in `test_owner_update` unless qualified) | Old expectation | New expectation | Rule |
|---|---|---|---|
| `ShapeTest.test_wrong_shapes_are_refused`, stock-not-last / stock-running subcases | Refuse these orders | Accept both; retain every invalid flag/slot/set refusal | A1–A2, B9 |
| `ShapeTest.test_recovery_and_layout_pair_accepts_any_known_release_but_only_the_pair` → `test_recovery_and_layout_accept_known_pairs_and_triples_but_refuse_staging` | Pair-only helper decides recovery | Handler reorders pair/triple to stock, preserves all rows; staged/unknown refuse; obsolete helper is never called | A3, A7 |
| `HistoryTest.test_reviewed_history_ends_with_the_pinned_release_and_r13_is_not_wheel` | Tools 2 | Tools 3, same release history and account rules | A9 |
| `UpdateCommandTest.test_update_verifies_then_stages_keeping_running_release_and_pinned_stock` | `kind`, `booted`, `pending`, `expected` journal fields | `schema=change1`, `mode=staging`, `word`, explicit `running`, `target`, `staged`, `intended` | A5.1 |
| `UpdateCommandTest.test_refusals_before_any_change`, queued stock rollback | Refuse queued rollback | Select installed R13 without network, name newer absent bundle | A2, A4(c) |
| same, queued previous | Refuse queued rollback | Select installed R21 without network, name newer absent bundle | A2, A4(c) |
| same, nothing newer | Refuse already running | No-op, no journal, say it runs | A4 |
| same, booted stock | Refuse staging from stock | Reorder to installed R13, no staging, name restart/update next step | A4(c) |
| same, target already deployed | Refuse installed target | Reorder to installed R21, no login/signature check | A4(a) |
| same, bundle older than running release | Old final-pair diagnostic | Unknown-deployment refusal, state and records unchanged | A1 |
| `UpdateCommandTest.test_old_direction_refusals_now_select_the_destination_without_network` | Five subcases above refused | Separate positive test retains all five, checks exact destination, row conservation and absent network/journal on no-op | A2, A4 |
| `PreviousTest.test_previous_queues_the_older_release_and_keeps_every_deployment` | `bootc rollback` | One `ostree admin set-default 1`, then `sync`, same rows | A3 |
| `PreviousTest.test_previous_refuses_without_an_older_release_or_with_pending_work`, pair/staged | Pair/pending wording | Only-one-release/staged wording; unchanged state and records | A3–A4 |
| same, other-is-newer / already-queued | Direction/pending refusal | Older release already first: no-op, distinguish running from waiting, no journal | A4 |
| `LoginTest.test_login_on_aresos_needs_a_newer_target_and_otherwise_keeps_the_stock_rules` | Already-running diagnostic | Installed target needs no login; staged and real-prompt checks retained | A4 |
| `OutcomeTest.test_failed_finalization_stops_every_confirmation_until_help_retries_the_update` → `test_lost_finalization_is_archived_and_commands_continue_without_help` | Every command refuses lost stage | Each read/reboot/change resolves and archives not-applied before own checks; previous/keep-stock refuse only their own preconditions; update retries | A5.2 |
| `OutcomeTest.test_an_unsuccessful_previous_stops_and_a_successful_one_is_confirmed` → `test_previous_elsewhere_stays_open_and_lost_selection_can_be_repeated` | Another running row blocks; before-list requires Help | Same boot waits; later boot elsewhere passes with open record and no confirmation; before-list archives not-applied; later target boot confirms | A5.2–A5.4 |
| `IntentTest.interrupted` / `test_the_intent_is_written_before_the_change` | Interrupt script `previous`; read `kind` | Interrupt shared `start-next`; inspect `word`; intent still precedes the primitive at all four cuts | A3, A5.1 |
| `IntentTest.test_every_interruption_leaves_an_unresolved_intent_that_check_title_records_refuse` → `test_every_interruption_resolves_by_list_except_same_boot_staging` | Every cut blocks every read forever | Same-boot staging names update; reorder before-list archives, intended-list records without another primitive; after restart lost change archives | A5.2, staging exception |
| `IntentTest.test_the_same_command_redoes_an_unmade_change_or_records_a_made_one` | Old retry text and one mutation for previous | Exact primitive counts (separate sync); retries only unmade/undone changes, applied reorder no-ops, later target boot confirms | A3, A5 |
| `IntentTest.test_after_a_restart_the_same_command_records_a_finished_change_or_redoes_a_lost_one` → `test_after_a_restart_reads_resolve_finished_or_lost_intents_before_the_command` | Reads refuse until same command continues | Reads resolve and confirm/archive first; applied target needs no second primitive; lost change can be repeated | A5.2–A5.4 |
| `IntentTest.test_other_commands_never_continue_an_intent_and_a_wrong_change_is_not_recorded` | Same-boot staging intent refuses | Retained unchanged: names update and refuses different running identity | A5.2 exception |
| `LockTest.test_changes_during_verification_are_caught_immediately_before_staging`, queued rollback | Queue flag diagnostic | Running system must start next; no stage, mutation or intent | A6 |
| `ToolsUpdateTest.test_older_installed_tools_are_replaced_and_kept_and_records_survive` | Version 1→2 | Version 1→3; same retirement, receipt and surviving records | A9 |
| `ToolsUpdateTest.test_downgrade_same_version_foreign_history_and_unknown_legacy_refuse_without_writes` | Installed 3→bundle 2 downgrade; installed 2 same-version | Installed 4→bundle 3 downgrade; installed 3 same-version; retain no-write/history/unknown-legacy checks | A9 |
| `test_owner_commands.CommandTest.pair` (eight inherited errors, also used by six abandon tests and owner-path) | Pair helper loses `kargs` and updater state | Explicit AresOS boot arguments, finished keyboard and paused updater fixture observations | A3 read-only BLS preflight, A10 |
| `test_owner_retained.RetainedTest.test_title_switch_and_recovery_real_pairs_and_bls` | No updater read modeled | Explicit paused-system/global-user unit listings and inactive units; retained captures remain unchanged | A10 |

### Initial verification (before the first hosted round)

- AST parsing of the three edited Python modules: OK.
- Baseline hosted [43513299977](https://github.com/Ares-Empire/AresOS/actions/runs/43513299977): 1037 tests,
  40 failures, 23 errors, 0 skipped; downloaded its failure log for the individual rewrites.
- Memory gate during editing: 4379 MB available, below 4500; no local test run yet.
- Correction to the earlier handoff: eight “older updater fake” errors are actually missing `kargs` in the
  pair fixture, newly read by A3's BLS preflight. The ninth is the retained stock host's missing updater reads.
- At that initial checkpoint, part (b), its B11 proofs and hosted totals were pending; no production defect
  had yet been found. The two defects and final results are recorded below.

- Local `cd os/tests && nice -n 10 python3 -m unittest test_ways_back`: **34 tests in 14.047s, OK**, after 5087 MB available. This imports the edited older module without running it.

- Local `cd os/tests && nice -n 10 python3 -B -m unittest test_ways_back`: **34 tests in 11.876s, OK**,
  after 5013 MB available. An initial invocation from the repo root failed import (`ModuleNotFoundError`,
  one loader error); corrected the working directory and ran the command above.


### Part (a), first hosted round and corrections

[43517900883](https://github.com/Ares-Empire/AresOS/actions/runs/43517900883), tested head `85c037b1`:
**1038 tests in 974.729s; 11 failures, 1 error, 0 skipped**. One blocking watch, exit 1. The four existing
fingerprint pins remain; eight other entries were fixed as below. No test is removed or skipped.

| Test | Old / first-round expectation or fake | Correct expectation / fake | Rule |
|---|---|---|---|
| `ShapeTest.test_recovery_and_layout_accept_known_pairs_and_triples_but_refuse_staging`, R99 pair | Expected unknown-installed diagnostic | With no recognized installed AresOS this is the unchanged prepared-list refusal; exact diagnostic asserted | A1 |
| same, layout portion | Old shared pair gate | Begin succeeds on known pair/triple without calling the obsolete pair helper; binds the trial to the running identity | A7 |
| `IntentTest.test_every_interruption_resolves_by_list_except_same_boot_staging`, records at all four cuts | Refused command must leave private records unchanged | Keep that assertion; production `records` must resolve before writing `record-c` | A5.2 |
| `test_owner_abandon.AbandonTest.test_stock_side_recovery_preserves_stocks_own_installer_layout` | Fake menu choice swapped slots but kept `rollbackQueued=false` | The first other row precedes running stock: queued true, bootOrder rollback; persistent stock settings still unchanged | B3, A2 |
| `test_owner_retained.RetainedTest.test_title_switch_and_recovery_real_pairs_and_bls` | Fixture accidentally sees runner's `/run/user` bus | Explicit empty user-manager bus list for retained captures lacking that observation; modeled paused system units still read | A10 |
| `test_owner_path.OwnerPathTest.test_card_clears_real_pending_state_then_completion_does_not_abandon_again` | Missing-private-trial diagnostic after completion | No active trial **and** no repair note; exact new diagnostic; card completion still never abandons twice | A7 |

**Defect found (A5.2):** same-boot staging intent at any of its four cuts → `records` → the disk read and
`record-c.json` write happened before `title` refused the unresolved intent. Fix: `records` calls the common
`survey()` first. The unchanged-record assertion that caught this is retained. A B11 mutant will remove
that call and must reproduce the assertion failure. This changes no schema, destination or PASS line.

The older fake failures exposed additional missing observations only after the first fixture repair let
those tests reach their later assertions. The route test's new diagnostic follows A7's repair-note support;
no guide, route sequence or binding assertion is changed.

### B8 and the publication boundary (verified in hosted run 43521572800)

`test_ways_back_compatibility.py` loads the exact version-2 `owner.py` and manifest-listed payload bytes from
`41b06513` with `git show`, checks fingerprint `851eb742…`, and executes that code as an imported module.
It never invokes an installed owner entry. Synthetic rows use the real R13/R27 references for this matrix.

Coverage added:

- The 13 named shapes accepted by version 2 over its unchanged two-release history: six resting pairs,
  four resting triples, prepared stock, first switch staged, and an update staged over a pair. The
  prepared-single-stock and single-stock first-switch variants are checked separately. Old and new
  first-install title output must be equal. Tools update runs over every one of those states.
- Each modified-deployment field and `unlocked` remains readable and accepts a tools update, preserving
  step 1's PLAN-GAP 5 (changing deployments still refuses modifications).
- Both named stuck states, with no journal and with version 2's actual `previous` intent and record,
  plus stock after previous. Also both before/intended orders × each running row × intent/record ×
  same/later boot during tools update. A journal's keys, running identity and boot id remain distinct.
- Version 2's own `intend`/`finish` produce update/previous records. A literal expected-outcome table
  checks same-boot staging's exception, pending, confirmed, elsewhere and not-applied; old accepted
  outcomes remain the same. Lost staging, an unknown list and a stage still present after a restart
  stay separate. Reading an old intent may never repeat its primitive.
- Version 2 writes the layout trial, revert, proof, interrupted finish (one and both persistent writes),
  completed and abandoned records and the title. Version 3 reads/continues them. A version-2 finish cut
  followed by version-3 revert must preserve `finish_proof` beside `proof: null`, and fresh-login abandon
  must restore the old persistent settings. Old records without that additive field still work.
- Version 2's actual `settle_tools` reads version 3's `tools-update1` at every copy, rename and record-write
  cut before publication, for first-install and versioned old directories. The old entry and verified
  toolset must return, remain unretired, and version 3 must resume the update. Unknown change schemas
  refuse both reads and tools update with unchanged records/deployments.

**Defect found (A9, tools update):** version 2 `previous` writes an intent; the reorder happens; a restart
runs R13; version 3's bootstrap runs `system_ready()`; that calls the new `qualified()` and writes a
`change1` record **before publication**. A cut then returns the old version-2 entry via `settle_tools`, but
version 2 cannot read that new record. Even a refused tools update could prematurely change its records.
The same readiness call could archive a not-applied record and silently lose its explanation.

Fix: both pre-publication readiness calls judge the list/journal with the new rules while suppressing
journal writes/archives. Once the tools journal says `retire` (new tools published), resolve persistently,
also on a resumed `retire`, and return the resolution notes with the existing install result. The
`tools-update1` schema, phases and fields are unchanged. The regression asserts byte/data preservation
of the old intent after the first tools-journal cut, version 2's `complete` result, then a resumed update.
A second test binds the archive to `retire` and requires the “was not applied” line.

The payload's `owner.py` and its two generated hash manifests were refreshed solely to keep that fix equal
to its source (brief's stage-1a source-consistency provision). The bundle inventory, release history,
commands, old scripts and published fingerprint pins are untouched; all inventory/pin work remains 1b.

**B11 additions:** removing legacy-journal support fails the literal outcome table; restoring version 2's
shape gate fails the named stuck-state install assertions; premature readiness writes fail the old-intent
preservation assertion; changing `tools-update1` is rejected by actual version-2 recovery. Earlier steps'
A1–A11 and fake mutants remain intact.

**JUDGMENT-CALL:** readiness is a read-only preview until publication, rather than migrating records while
the old tools can still become current. New tools persist the same A5 decision immediately after publication.
This keeps version 2's recovery route usable; it changes no destination, schema or owner command. Reverting
this choice costs the demonstrated unreadable-old-record window. No new owner-facing rule is requested.

**PLAN-GAP:** A9's requirement to judge readiness with the new rules did not specify when that judgment's
journal writes become safe. The publication boundary is necessary for its old-reader compatibility guarantee.


Part (a)'s fixes were committed and pushed separately as `6b0e209b`, after initial checkpoint `85c037b1`.
The next hosted run tests those fixes together with B8/B11. The old card-route helper still models the
current guide's old missing-trial quote; only the handler's new A7 diagnostic assertion changed here.
Stage 1b must update that guide quote and its route expectation together.

Additional local verification (one test module at a time, `nice -n 10`, memory ≥4500 MB):

- After the tools-update readiness fix, `cd os/tests && nice -n 10 python3 -m unittest test_ways_back`:
  **34 tests in 11.972s, OK**; `nice -n 10 python3 -B -m unittest test_ways_back`: **34 in 11.869s, OK**.
- `nice -n 10 python3 -m unittest test_ways_back_model`: **15 in 378.339s, OK**; **486627 states,
  12176910 edges, 249475 executions, 11927435 reuses, queue exhausted** (377.541s exploration). This process
  started before the `records` ordering fix; the final source's completed `-B` rerun is recorded below.
- Import-only audit of B8: the historical acceptance predicate accepts **13** candidates; 15 manifest-listed
  version-2 payload files verified. No compatibility test method or `test_owner_update` suite ran locally.
- AST parsing of the new compatibility module and changed owner source: OK. The B8 module has **21** tests,
  including five executable B11 proofs. Hosted execution remains required.

**B11 records proof:** removing `records`' first `survey()` reruns the real four-cut interruption test and
must fail its unchanged-private-records assertion, with no unrelated test error.


The old wrong-shape subcase named “running not default” also forces a contradictory `rollbackQueued=false`;
its refusal remains an agreement check under A2/B3. Valid non-default starts are accepted by all pair/triple
shape cases and the historical queued-pair tests.

### Final verification and B11 assertion map

Both rounds used `gh workflow run "OS image" --ref pkg/22c-ways-back-after-update -f checks_only=true`
and exactly **one** blocking `gh run watch <id> --exit-status` each (exit 1 for the red suite). The second
run spent about nine minutes queued before its regression step; neither dispatched a VM.

| Hosted run | Tested implementation | Result |
|---|---|---|
| [43517900883](https://github.com/Ares-Empire/AresOS/actions/runs/43517900883) | `85c037b1` | 1038 tests in 974.729s; 11 failures, 1 error, 0 skipped |
| [43521572800](https://github.com/Ares-Empire/AresOS/actions/runs/43521572800) | `8d2366197413074b97ef3dbf80de09ae310059fc` | **1059 tests in 1163.247s; 4 failures, 0 errors, 0 skipped** |

Final hosted focused counts, taken from the log's individual test entries:

| Module | Passed / run |
|---|---|
| `test_owner_update` | **73 / 73** (including its namespace cases; none skipped) |
| `test_ways_back` | **34 / 34** |
| `test_ways_back_compatibility` | **21 / 21** |
| `test_ways_back_model` | **15 / 15** |
| `test_ways_back_reverts` | **15 / 15** |
| `test_ways_back_probe` | **40 / 40** |

B8 printed **13/13 historical shapes accepted**, identical before-first-switch title text, and tools update
over all 13 shapes without deployment mutation. Its additional prepared-single-stock and staged-single-stock
variants passed too. Its actual version-2 recovery passed **98** pre-publication cuts: 25 with `tools/` and
24 with `tools-<fingerprint>/`, each repeated with and without an old open previous intent. Every case resumed
successfully with the new tools. The five executable revert proofs passed:

| Rule / removal | Guarding assertion that fails |
|---|---|
| A5.2: remove `records`' first `survey()` | `IntentTest.test_every_interruption_resolves_by_list_except_same_boot_staging`: the private-record bytes must equal their before-snapshot at all four staging cuts |
| A9: reject schema-less version-2 change records | `CompatibilityTest.test_old_intents_and_records_obey_the_explicit_journal_outcome_table`: `result == expected` |
| A9/A2: restore version 2's shape gate | `CompatibilityTest.test_tools_update_on_both_named_stuck_states_with_each_old_previous_form`: install must succeed, with version 2→3 result |
| A9: persist readiness before publication | `PublicationTest.test_readiness_does_not_migrate_legacy_intents_before_publication`: restored version 2's original intent must remain equal; its own retry result must be `complete` |
| A9: replace `tools-update1` with `tools-update3` | `PublicationTest.test_version2_settles_every_v3_cut_before_publication_and_v3_resumes`: journal schema must be `tools-update1` and old `settle_tools()` must accept it; the schema mutant proves actual version 2 rejects it with `Invalid tools update journal` and changes nothing |

The model again exhausted **486627 states / 12176910 edges**, **249475 executions / 11927435 reuses**,
426.169s in this hosted run. All eight journal outcome counts match step 2b. The two named menu-only paths
remain the absent-R28 cases from default/running R13 with installed R27; the follow-up's exception stands.

Final-source local `cd os/tests && nice -n 10 python3 -B -m unittest test_ways_back_model` passed **15 tests in
376.573s**, exploration 375.417s, with exactly those same states, edges, executions, reuses and outcome counts.
Its start gate was 4581 MB available. A further final-source plain model/direct-suite rerun was **not run**:
available memory stayed below 4500 MB after that run (4476, 4448, down to 4044 MB). Earlier local plain/`-B`
counts above are identified as before the `records` fix; the final-source truth comes from this `-B` run and
hosted full execution. `test_owner_update` and the compatibility module's test methods were never run locally.
This is a verification limit, not a skipped or weakened hosted test.

Small committed evidence: [checks-43521572800.json](runs/checks-43521572800.json), with both rounds' totals,
focused counts, remaining test names, publication-cut counts and the model's outcome counts. The 22c host walk
printed `PASS package 22c host walks (reorder-probe): 257 sources; no VM started`; the waiting-list generator
printed `pending: 28 bound files differ from the active bindings`. `git diff --check` passed. The bundle
source-consistency refresh printed intermediate fingerprint `621d59e3…`; it is not a published pin.

### What still fails, why, and open questions

Only these four failures remain; **nothing else** remains red:

1. `test_owner_bootstrap.BootstrapTest.test_documented_command_is_generated_from_complete_system_manifest`:
   `commands.json` still pins the old bundle fingerprint.
2. `test_owner_equality.EqualityTest.test_bootstrap_is_byte_equal_to_the_block_exercised_by_package_14_tamper_tests`:
   the guide's bootstrap blocks and command pin still contain the old fingerprint.
3. `test_owner_equality.EqualityTest.test_reviewed_windows_payload_is_exact_generated_ci_payload`:
   generated payload/source equality passes; the subsequent guide-fingerprint assertion fails on its old pin.
4. `test_owner_path.OwnerPathTest.test_update_route_orders_windows_tools_update_title_reboot_check_with_pass_stop_and_returns`:
   the guide's `PASS tools manifest SHA256 …` line still has the old fingerprint.

Those pins, guides, inventory changes and routes belong to stage 1b. No state-machine, compatibility, fixture,
model or revert-proof failure remains. No new rule is needed. Open questions for this checkpoint: **none**;
the historical council/laptop limits below remain limits, not new claims of physical verification.

### For stage 1b

1. Start from the final hosted receipt below and the two defect regressions above. Preserve the three
   journal states, the absent-bundle destination exception, and `finish_proof` beside `proof: null`.
   Keep readiness read-only until tools publication; keep `records` resolution ahead of disk writes.
2. Finish C/D/F, B12 and B9's payload test. The bundle still has `rollback.sh`, `default-stock.sh` and
   `previous.sh`; its inventory was deliberately unchanged here. Their repository copies stay byte-identical.
   Remove the three payload entries, then generate the final fingerprint and update every pin together.
3. The four remaining test failures are the fingerprint/bootstrap/guide pins named below. The guide still
   quotes the old missing-trial diagnostic and its route helper models that quote. Update both to A7's
   no-trial-and-no-repair-note wording; do not weaken the route assertion. All other guide/route changes
   (including forward update after previous) remain yours, as do the refusal invariant and binding tests.
4. Regenerate the 22c host walk before `rebind.py pending` after bound edits. This step's walk still covers
   only the probe route. Add E's route, then refresh bindings as D/B12 require. Do not rewrite package 27's walk.
5. Dispatch no rehearsal until the integrator supplies the tools review's verdict. No VM was dispatched here.
   The next release still needs real staging/finalize captures over three installed rows; this model is not
   that capture. A first install with version 3 remains tests only.

## Stage 1a: summary

The installed set is the saved pinned stock plus one or two known AresOS releases, in any order and with
any member running. Before the first switch, version 2's prepared and staged-switch rules and title text
remain unchanged. All four destination words share one identity-bound `set-default` reorder with `sync`;
it preserves the rows, pins and boot entries. `update` reorders to an installed newest release without
network access, or stages a missing bundle only from a default/running AresOS with whole settings. Staging
announces the removed release before the primitive and keeps the running system's settings, even when it
is the older one (owner decisions 1 and 5 remain judgment calls for merge).

The journal resolves from the deployment list before command-specific checks. Selection applied on the
same boot, restart waiting, and target boot confirmed are distinct. A later start elsewhere stays usable;
a lost change archives not-applied; same-boot staging intents still name update. Layout trials and repair
notes belong to their deployment; abandoning elsewhere writes no other system's settings, and interrupted
finish authorization survives revert. Stock updater findings warn on reads, refuse keep-stock, and never
block the return to AresOS; staging on stock beside installed AresOS gets its dedicated danger refusal.
Tools 3 reads version 2's records and accepts its shapes. Tools publication retains `tools-update1` and
preserves old-readable journals until the new tools become current.

Differences/clarifications from the brief: modified AresOS remains readable/rebootable as version 2 allowed,
while changes refuse it (step 1 PLAN-GAP 5); stock-stage wording names one installed release when only one
exists; a no-op does not refresh title; bootc slots/flags must agree with the list but never supply a cause.
Same-boot staged-record loss still refuses until another boot; stale repair notes for removed deployments
block nothing. The B2 follow-up keeps strict staging from default/running older AresOS with an absent
newer bundle: the installed newer release is then reached through its boot-menu path. This step changes
no rule or schema; its new clarification is deferring tools-update journal resolution writes to publication.

Known limits remain the council's: the small set-default index race; early finalize prune near a full
`/boot`; modified deployments refusing changes; no inference of why a non-default row runs; identical menu
titles; separate settings per system; an owner-started Bazzite update outside the tools; no cancellation
before restart; and no staging from stock. Accepted shape/model results do not prove the laptop's cleanup
implementation, menu link-swap path, desktop updater triggers or pin storage. Stage 0 proves only its
captured VM reorders/menu choice and pair staging; triple finalize and settings inheritance are synthetic.
No first install with tools 3, real keyboard typing, shutdown durability, stage-2 rehearsal or laptop change
was performed in this step.

For the next update release: rehearse staging from **both** `[R27*, S, R13]` and `[R27*, R13, S]`, retain
`[new, R27, S]` by identity with stock pinned, start stock from the menu and reorder back. Commit raw staging
and triple-finalize captures and hold the fake to them; this is that release's acceptance and laptop gate,
not proved here. Its bundle must pass A9 against whichever tools are then installed, and use tools version 4.


The closing commit changes this report and its receipt only; the tested implementation remains `8d236619`.
Temporary logs, scripts and model outputs under `.work/22c-step3/` are removed before the closing push. No
outside-worktree temporary directory was created. The closing `.work/` inventory has **no file over 500 MB**;
no large download was made. No builder-started test/watch process remains, and no Gradle daemon was started.
PR #46 stays open and draft; nothing was merged and nothing was pushed to main.

## Review fixes 1

Builder: Codex GPT-6.1-sol, xhigh. **All three findings are fixed.** Tested
implementation: `cfa98e20ea4c37d8446813704e4a3f92de45db25`. Closing commits change
this report and receipts only. PR #46 remains open and draft; no merge or main push.

### Done, tests and revert proofs

**1. Interrupted layout restoration resumes.** `owner.py` saves the exact
persistent pair in additive `restoring` data before either restoration write,
for both pending trials and repair notes. A retry accepts its recorded start,
its own console-first intermediate, and the old finished pair. Without intent,
a reverse partial pair still refuses. Retries re-publish the same intent;
they never replace its original snapshot. Abandoning elsewhere carries the
intent into that deployment's repair note and writes no other system's `/etc`.
`check` names fresh-login abandon when a repair note owns a console mismatch.

A further cut was reproduced: save the note on stock, cut before clearing the
trial, return and interrupt restoration, then transfer back on stock. Exact
object deduplication previously left two notes, one lacking the new authority.
Transfer now replaces the note by deployment identity, retains its old/new
settings and intent, and refuses conflicting records.

- `LayoutTest.test_every_restoration_cut_resumes_only_its_own_settings` covers
  all six directed profile pairs, both finish write cuts, pending/repair owners,
  and restoration intent/console/X11 cuts: **72 cases**. It checks durable intent,
  exact old settings, untouched other settings, cleared records and a usable
  destination command. The unauthorized reverse-pair test preserves the boundary.
- `RevertTest.test_abandon_cuts_resume_pending_notes_and_transferred_restoration`
  replays restoration cuts, restarts and intent transfer. Removing reverse-pair
  acceptance makes the pending and repair-note retries fail `accept/refuse`.
  Removing the save fails `restoration intent missing before write`.
- `LayoutTest.test_cut_during_note_transfer_then_restoration_updates_the_same_note`
  reproduces the private note-save cut, requires one intent-bearing note and
  repairs it. Before the fix it printed `Ran 1 test in 0.084s` /
  `FAILED (failures=1)` (an additional note). Its executable replacement-removal
  proof fails that same assertion, with no unrelated exception accepted.

**2. Reorder reads the list that the caller journalled.** `start_next` passes
its complete pre-change deployment snapshot as hex-encoded JSON (`BEFORE`),
which cannot introduce quoting or substitutions. `start-next.sh` compares its
fresh read before `set-default`, alongside the existing target checks. Drift
reports an outside change and executes no primitive. Exact postconditions and
`sync` remain. The accepted race after that final read is unchanged.

- `ScriptTest.test_fresh_read_must_equal_the_callers_snapshot_before_any_mutation`
  covers order, pin, identity, running row and deployment metadata drift: one
  read, zero primitives.
- `DestinationTest.test_outside_reorder_between_intent_and_script_does_not_add_an_owner_mutation`
  injects `[R13, R27*, S]` after rollback journalled `[R27*, R13, S]`. It requires
  the outside state unchanged, zero owner changes and an open intent.
- Removing only the snapshot assertion in memory makes that owner-level
  regression fail because it observes `ostree admin set-default 2` instead of
  no mutation. The postcondition still refuses the resulting wrong order.

**3. All reviewed installed-list entry points survey first.** `survey_installed`
resolves the installed lifecycle before prepare's disk/setup checks, before
`before_switch`'s checks (verify/switch), and before login chooses its side.
With no installed AresOS, prepared and first-switch checks stay in charge.

- `JournalTest.test_install_commands_resolve_the_installed_journal_before_their_own_refusals`
  cuts rollback before/after its primitive, starts stock, then separately tries
  login, verify, switch and prepare. It requires recorded/not-applied resolution
  before each own refusal, without another deployment mutation.
- The existing every-command A10 test now includes those four, check and layout
  begin. The prepared/first-switch boundary test preserves the old refusal,
  including foreign staging. Its account boundary is explicitly synthetic;
  the fake disk record supplies prepare's full required structure.
- Removing the installed survey in memory makes both the journal and mandatory
  danger-message assertions fail; unrelated exceptions are rejected as proof.

### Model and verification cost

The independent ledger now cuts abandon before persistence, between console
and X11, and after both writes. Every deployment's settings, all eight journal
outcomes and restoration evidence remain literal in representatives and actual
execution checks. The reference catalogue generated the new exact pins;
reference-only counting is **not** Tools verification.

Restoration intent provenance is future-equivalent for reachable settings:
both initial restoration and retry publish intent before writing old settings.
Reverse partial pairs remain reachable only with intent. The equivalence test
executes every successor of **48 pairs**, across all profiles and both record
owners. Execution reuse additionally checks cached against uncached results in
**both fill directions**, with an unrelated live repair intent. It frames exact
snapshots, adds a re-published intent when absent, preserves it on retry, and
clears it when its trial/note is removed. Every cache hit still compares the
**full literal ledger** with the independent prediction. No assertion, event or
state was removed. Predictions are computed once and shared with invariants.

One cache implementation omitted an idempotent write when the first execution
already had intent. The unchanged full-ledger assertion caught that missing
intent after 80000 states (`20 tests in 106.714s`, one failure). The driver now
records actual restoration write attempts, including the pre-write cut. The
both-direction cache regression guards the correction.

The private note-save interruption above has its own direct regression; the
model's closure counts cover its encoded persistent-write event set, **not all
possible private JSON-save cuts**.

### Verified

Final local commands were run separately, at nice 10, after `free -m` gates:

| Command (from `os/tests`, with `TMPDIR=/var/home/ares/pkg22c-work`) | Available at start | Exact final result |
|---|---:|---|
| `nice -n 10 python3 -B -m unittest test_ways_back` | 10166 MB | **44 tests in 24.930s; OK** |
| `nice -n 10 python3 -B -m unittest test_ways_back_model` | 10196 MB | **20 tests in 885.963s; OK** |

The final model exhausted **879291 states / 23108154 edges**, with **779125
executions / 22329029 reuses**, in 880.559s. It includes **1077696 abandon
interruption edges**. The eight outcomes and two menu-only destinations remain
separate and match the earlier full uncached-provenance run (19 tests in
1188.656s, OK). Full exact counts are in
[runs/checks-43536170182.json](runs/checks-43536170182.json).

Other local checkpoints: focused 36 tests in 21.160s, OK; focused 42 tests in
24.221s and 22.456s, OK; model equivalence/reverts 11 tests in 1.131s, OK;
equivalence 5 tests in 1.816s and then 3.261s, OK. Initial model adapter attempts
printed 17 tests with 4 failures in 4.169s, 1 failure in 14.589s, and 1 failure
in 105.523s; missing intent encoding, the repair-note next step and cut selection
were corrected. The first 42-test focused attempt had one unmodelled account
fixture failure in 24.763s, corrected as described above. Interrupted exploration
runs were explicitly stopped with SIGINT on their own Python process and are
not passing evidence. No owner-update or compatibility test method ran locally;
those results come from hosted execution.

Each hosted dispatch used
`gh workflow run "OS image" --ref pkg/22c-ways-back-after-update -f checks_only=true`,
followed by exactly one blocking `gh run watch <id> --exit-status` for that run:

| Hosted run | Result |
|---|---|
| [43530837211](https://github.com/Ares-Empire/AresOS/actions/runs/43530837211) | Cancelled by the unchanged 25-minute job limit during the expanded model; no full totals. Watch exit 1. |
| [43534401745](https://github.com/Ares-Empire/AresOS/actions/runs/43534401745) | Explicitly cancelled after the local cache defect was found; no acceptance totals. Watch exit 1. |
| [43535052672](https://github.com/Ares-Empire/AresOS/actions/runs/43535052672) | Explicitly cancelled for the repair-note transfer correction; no acceptance totals. Watch exit 1. |
| **[43536170182](https://github.com/Ares-Empire/AresOS/actions/runs/43536170182)** | **1074 tests in 1366.551s; 4 failures, 0 errors, 0 skipped.** Watch exit 1 for the four deferred pins. |

Final hosted module counts: `test_owner_update` **73/73**,
`test_ways_back` **44/44**, `test_ways_back_model` **20/20**,
`test_ways_back_compatibility` **21/21**, `test_ways_back_reverts` **15/15**,
`test_ways_back_probe` **40/40**. The hosted model exhausted the identical
**879291 states / 23108154 edges**, with **779125 executions / 22329029 reuses**,
in **723.035s**; every journal outcome count matches local execution.

The only failures are the same stage-1b pins as baseline 43521572800:

1. `test_owner_bootstrap.BootstrapTest.test_documented_command_is_generated_from_complete_system_manifest`.
2. `test_owner_equality.EqualityTest.test_bootstrap_is_byte_equal_to_the_block_exercised_by_package_14_tamper_tests`.
3. `test_owner_equality.EqualityTest.test_reviewed_windows_payload_is_exact_generated_ci_payload`
   (source/payload equality passed; the following guide-fingerprint assertion failed).
4. `test_owner_path.OwnerPathTest.test_update_route_orders_windows_tools_update_title_reboot_check_with_pass_stop_and_returns`.

The source-consistency refresh printed
`PASS bundle manifest SHA256 610e1b27…`.
The inventory/guides/pins remain for stage 1b. After the final bound edit,
`python3 -B reviews/22c-ways-back-after-update/walk-host.py` printed
`PASS package 22c host walks (reorder-probe): 257 sources; no VM started`, then
`python3 -B reviews/27-first-update-release/rebind.py pending "22c review fixes 1: replace repair notes by identity across interrupted transfers"`
printed `pending: 28 bound files differ from the active bindings`.
`git diff --check` passed. Package 27's walk was not rewritten.

### Not verified, judgment and re-review

**Not verified:** real typing/password entry, real persistence after power loss,
VM rehearsal, first install with tools 3, triple finalize and the laptop gates.
No owner entry, deployment binary, keyboard command or mod/Gradle build was run
on the laptop. No VM was dispatched. Existing stage-1a limits still apply.

**JUDGMENT-CALL:** none added; no numbered rule or schema changed. `restoring`
is additive. Existing decisions and stage-1b work remain as previously recorded.

**PLAN-GAP:** the expanded model initially exceeded the hosted time budget;
execution reuse resolved it without changing the workflow, harness or budget.
The extra private note-transfer cut was part of making finding 1 resumable.
The review got none of its three findings wrong; all were confirmed and fixed.

**For re-review:** inspect layout restoration authorization and note replacement
by identity, both record owners and their negative proofs; the exact caller
snapshot assertion before any reorder and its injected outside writer; installed
surveys before side/refusal checks with the pre-install boundary preserved; and
the model's actual-write framing, both cache-fill orders and literal ledger
assertion. Closure is a claim about the stated event set. Final local and hosted
counts above refer to `cfa98e20`; closing changes are report/receipts only.

**Open questions:** none for this review round. Only the four deferred stage-1b
pin failures remain; stage 1b and the later VM gates are outside this round.

Cleanup: all temporary files this run created under `/var/home/ares/pkg22c-work/`
were removed. The closing `.work/` inventory has **no file over 500 MB**; no large
download was made. No builder-started test/watch process remains, and no Gradle
daemon was started. PR #46 is open and draft; nothing was merged or pushed to main.

## Review fixes 2

Builder: a Claude agent on Opus 5.5 (`briefs/22c-review-fixes-2.md`). **Both should-fix
findings of [REVIEW-2](REVIEW-2.md) are fixed**, each with a test that fails without it
and an executable revert proof. Fix 1 is `4dd39fbf`, fix 2 is `1c651b8a`, and `12af3787`
gives the checks-only CI job room for the grown model (see PLAN-GAP below); the closing commit
changes this report and a receipt only. No rule of the brief was widened. PR #46 stays open
and draft; nothing was merged or pushed to main.

### 1. A refusal before the change closes its intent

**What changed.**
- `os/release/start-next.sh`: every check before `set-default` (the fresh read equals the
  caller's snapshot, nothing staged, the target once, its digest and reference, not already
  first) calls `refuse()`, which writes `STOP: <reason>; nothing was changed` to stderr and
  exits with status **3**. Nothing else exits 3: the postcondition stays an `assert`
  (status 1), a failed status read, `set-default` or `sync` ends with status 1, a kill with a
  signal status. Status 3 is reached only before the `set-default` process was ever started,
  so the caller knows it, it does not infer it.
- `owner.py`: `Failed(Stop)` carries a release step's own non-zero exit status from
  `Host.script`, with the same message as before, so every other caller is unchanged
  (`REFUSED_BEFORE_CHANGE = 3`). `start_next` reads it: on status 3 it archives its intent
  as `refused-before-change` and STOPs with *"The deployment list changed outside the tools
  before the <change>; nothing was changed and the change is closed; run
  sudo /var/lib/ares/at check to see what runs and what starts next"*. Any other status
  re-raises the step's STOP with the journal open, as before, and rule 5 resolves it from the
  list at the next command.
- The fakes that run the script's Python (`test_owner_update.Machine.script`,
  `ways_back_host.Host.script`) report its exit status as the real host does: `SystemExit`
  with its status, an assertion with status 1, both as `Failed`.

**Tests.**
- `DestinationTest.test_outside_reorder_before_the_script_closes_the_intent_and_every_way_back_works`
  replaces round 1's `…_does_not_add_an_owner_mutation`, which expected the open intent.
  The review's sequence: rollback journals `[R27*, R13, S] → [S, R27*, R13]`, an outside
  writer makes `[R13, R27*, S]` before the script reads. Required: no owner change, the
  outside list unchanged, no open journal, one archive `refused-before-change`, the exact
  STOP. Then, with no restart and after a restart on each of the three rows: `title` (nothing
  left to resolve), `reboot`, and every destination (`rollback` or `keep-stock`, `previous`,
  `update`) one command away, each from the same state. Last, the refused word typed again
  goes through and the next start (stock) confirms it.
- `DestinationTest.test_a_script_failure_that_may_follow_the_change_keeps_the_intent_open`:
  status 1 with and without the change on disk, a kill (-9) after it, status 4: the intent
  stays open with no archive and the step's own STOP; the next `title` records the change
  (`had made its change`) or archives `not-applied`.
- `ScriptTest`: wrong lists and snapshot drift now require status 3, one read, no `ostree`
  call and the `STOP: …; nothing was changed` line; a wrong list afterwards and a failed call
  stay ordinary failures. `test_the_host_reports_a_steps_own_exit_status` runs the real
  `Host.script` over a stub step: status 3, 1 and -9 give `Failed` with that status and the
  old message; status 0 with a process left behind, and a timeout, give a plain `Stop`.
- `FakeRulesTest.test_script_refusal_before_primitive_has_no_mutation` also requires status 3.

**Revert proofs** (`test_ways_back_reverts.RuleRevertsTest.test_review2_1_only_a_refusal_before_the_change_closes_the_intent`,
each in memory, unrelated exceptions rejected):
- the caller never closes (`if True:`, round 1's behaviour): the regression fails in all
  four boot choices at *"the refused intent is still open"*;
- the caller closes on every failure (`if False:`): the may-follow test fails, because an
  intent whose change may be on disk is archived as `refused-before-change`;
- the script refuses with status 1 (`sys.exit(1)`): the regression fails at *"the refused
  intent is still open"*.
- `ScriptTest.test_removing_snapshot_guard_fails_the_outside_writer_regression` still holds:
  without the snapshot guard the regression fails in all four choices with
  `ostree admin set-default 2`.

### 2. Restoration is an exclusive phase

**What changed.** `owner.py`, `layout finish`: when the pending trial carries a restoration
intent (`restoring`), finish STOPs before the login, proof and settings checks and before any
write: *"Layout abandon has begun restoring the settings from before this trial: from a fresh
physical administrator login run sudo /var/lib/ares/at layout abandon to complete it; nothing
changed"*. That holds from the original login as well. `revert` and `proof` are unchanged
(runtime only); a finish after them refuses the same way.

**The model.**
- A new step, `original-login`: in the trial's own boot, from a fresh login, the owner goes
  back to the trial's administrator login, which is still open. The driver makes that login
  current again; after a restart the step does not exist.
- The ledger's finish refuses with `layout abandon` while a restoration intent exists for the
  trial's deployment (after "crossed a reboot", in the tools' order).
- The reduced key: for a trial still in its own boot, *whether* its restoration began is
  state now. Round 1 quotiented it away as provenance, which held only as long as nothing
  but abandon could write that `/etc` again; the missing step hid the renewed finish. After a
  restart it stays provenance (finish refuses before reading it), so round 1's equivalence
  tests stand unchanged. The execution memo keys the same input for `layout-pending` and
  treats `original-login` as a host event like `fresh-login`.

**Tests.**
- `LayoutTest.test_restoration_is_exclusive_and_finish_from_the_original_login_names_abandon`,
  the review's sequence on the keyboard fake: German to US, proof; finish cut after its
  console write (US console, German X11); abandon from a fresh second login cut after its
  console write (both German; trial and intent remain); back in the original login, finish
  refuses with the exact text and changes nothing (settings, list, host changes). Then the
  review's next steps: restart, abandon completes (German), no trial and no note; a new trial
  (begin, proof, finish) works.
- `RevertTest.test_restoration_is_exclusive_also_from_the_original_login` (model): the same
  path through the driver against the ledger, `original-login` included; finish has no cut
  points; fresh-login abandon completes; a new trial finishes.
- `EquivalenceTest.test_journal_outcomes_and_live_repairs_are_not_equivalent`: a trial in its
  own boot with and without a begun restoration are different states.
- The exhaustive model, with the new step (below).

**Before and after, by hand** (a one-off script under `/var/home/ares/pkg22c-work/`, not
committed, removed): without the guard, finish from the original login was accepted and, cut
after both writes, left US/US; abandon after the restart STOPped *"Finished system layout
changed during the abandoned trial"*, the review's dead end. With the guard, finish STOPs as
above, and abandon after the restart passes with German.

**Revert proof** (`test_ways_back_reverts.RuleRevertsTest.test_review2_2_restoration_is_an_exclusive_phase`):
`require('restoring' not in value,` becomes `require(True,`. The model path fails
`accept/refuse` at finish, and the focused regression fails (`Stop not raised`).

### The model with the new step

`ModelTest.test_reachable_state_space` exhausts **963003 states / 25257042 edges**
(round 1: 879291 / 23108154), with **813553 executions / 24443489 reuses**, in 911.268 s
locally. Every one of the 115176 fresh-login edges now has an `original-login` edge.
`finish`: 26196 PASS, 292914 STOP, 39294 cut. Outcomes: complete 333, in-place-not-started
135720, none 217560, not-applied 277098, retry 333, selection-applied 150528,
target-boot-confirmed 91956, waiting 89475; the eight stay separate, and the two menu-only
destinations are unchanged. The new states are trial states (outcomes `none` and
`selection-applied` grew by 41856 each). The new pins came from a ledger-only exploration of
the same queue and keys (a one-off script, 299.6 s, removed) and were then confirmed by the
full run, which executes and checks every edge against the tools.

### Verified

Local commands, each from `os/tests` with `TMPDIR=/var/home/ares/pkg22c-work`, at nice 10,
one at a time, after a `free -m` gate, on the committed source of `1c651b8a`:

| Command | Available at start | Result |
|---|---:|---|
| `python3 -B -m unittest test_ways_back` | 8367 MB | **47 tests in 28.174s; OK** |
| `python3 -B -m unittest test_ways_back_model` | 10191 MB | **21 tests in 916.816s; OK** |
| `python3 -B -m unittest test_ways_back_reverts` | 9287 MB | **17 tests in 1.213s; OK** |

Checkpoints on the way: after fix 1, `test_ways_back` 46 tests in 25.333s OK and
`test_ways_back_reverts` 16 tests OK. Two earlier reverts attempts had one failure each,
both in the new proof's own checks: its expected text was hidden by a truncated repr, then a
mutated `Stop` escaped `assertRaises(Failed)` as an error. Both assertions were made explicit. The model classes outside the exhaustive run
(20 tests) passed in 3.705s and 3.822s. A one-off shell check showed `bash -seu` with
`set -euo pipefail` passing a heredoc `python3`'s status 3 through unchanged. No
`test_owner_update` test, owner command, deployment binary or keyboard command ran on the
laptop; that module was only imported as the fakes' library, as before.

Bound files: after each fix `python3 -B os/owner-tools/bundle.py --refresh` (payload copy and
checksums; `PASS bundle manifest SHA256 91d2b5cf…`, then `5869d519…`), then
`python3 -B reviews/22c-ways-back-after-update/walk-host.py` printed
`PASS package 22c host walks (reorder-probe): 257 sources; no VM started`, and
`python3 -B reviews/27-first-update-release/rebind.py pending "<note>"` printed
`pending: 28 bound files differ from the active bindings` (one note per fix).
`git diff --check` passed. The stage-1b pins still name the old fingerprint.

Hosted, each `gh workflow run "OS image" --ref pkg/22c-ways-back-after-update -f checks_only=true`
followed by one `gh run watch <id> --exit-status --interval 60`:

| Hosted run | Result |
|---|---|
| [43542336319](https://github.com/Ares-Empire/AresOS/actions/runs/43542336319) | **Cancelled by the unchanged 25-minute job limit** (25m14s) inside `test_reachable_state_space`, at 680000 states after 777s. Before it: **1001 ok, exactly the four stage-1b pins FAIL, 0 errors, 0 skipped**. This runner was about 1.4× slower per state than round 1's (whose whole 879291-state model took 723s). Watch exit 1. |
| [43544822860](https://github.com/Ares-Empire/AresOS/actions/runs/43544822860) | **Cancelled by the same limit** (25m17s), at 860000 states after 882s. Before it: again **1001 ok, exactly the four pins FAIL, 0 errors, 0 skipped**. On this runner the model needs about 990s and the suite about 27 minutes; round 1's head would also have run past 25 minutes here. Watch exit 1. |
| **[43547375701](https://github.com/Ares-Empire/AresOS/actions/runs/43547375701)** | On `12af3787` (the 40-minute limit; tools and tests as `1c651b8a`): **1080 tests in 1948.831s; 4 failures, 0 errors, 0 skipped**, the job in 32m53s. Watch exit 1 for the four deferred pins. |

That is round 1's 1074 plus this round's six new tests. Hosted module counts:
`test_owner_update` **73/73**, `test_ways_back` **47/47**, `test_ways_back_model` **21/21**,
`test_ways_back_compatibility` **21/21**, `test_ways_back_reverts` **17/17**,
`test_ways_back_probe` **40/40**. The hosted model exhausted the identical **963003 states /
25257042 edges** with **813553 executions / 24443489 reuses** and the same eight outcome
counts as locally, in 1275.008s on that runner. The only failures are the same four stage-1b
pins as in run 43536170182 (`test_owner_bootstrap…test_documented_command_is_generated_from_complete_system_manifest`,
`test_owner_equality…test_bootstrap_is_byte_equal_to_the_block_exercised_by_package_14_tamper_tests`,
`test_owner_equality…test_reviewed_windows_payload_is_exact_generated_ci_payload`, failing on
the guide's fingerprint `5869d519…` after source/payload equality passed, and
`test_owner_path…test_update_route_orders_windows_tools_update_title_reboot_check_with_pass_stop_and_returns`).
Exact counts: [runs/checks-43547375701.json](runs/checks-43547375701.json).

### Not verified, judgment and re-review

**Not verified:** a real `Step` running the real `start-next.sh` (it reads `rpm-ostree`,
which never runs on this laptop): `Host.script`'s status handling is tested with a stub step,
the script's statuses through the fakes, and the shell's pass-through by the one-off check
above. Real typing, real power loss, the VM rehearsal and the laptop gates stay open as before.

**Known limit (added, fails safe):** a power cut after the script's status-3 exit and
before the archive's directory sync leaves the intent open. The next command then STOPs as in
round 1 (rule 5 (d)), with nothing changed. The window is one JSON save and one unlink; the
refusal itself is known only after the script returns. If the script cannot even write its
STOP line, Python ends with status 1 and the intent stays open (the safe direction).

**Changed PASS and STOP lines:** no PASS line changed. Two new STOP lines, for stage 1b's
`docs/INSTALL-REFERENCE.md` if it quotes them: *"The deployment list changed outside the tools
before the <change>; nothing was changed and the change is closed; run
sudo /var/lib/ares/at check to see what runs and what starts next"* and *"Layout abandon has
begun restoring the settings from before this trial: from a fresh physical administrator login
run sudo /var/lib/ares/at layout abandon to complete it; nothing changed"*. The script's own
stderr lines now end `; nothing was changed` (the drift line no longer says `get help`; the
tools' STOP names `check`).

**JUDGMENT-CALL:** none. No numbered rule, journal schema or field changed: the archive name
`refused-before-change` is new, and archives are not state.

**PLAN-GAP, and one change outside the two fixes:** the checks-only job's 25-minute limit
was already tight in round 1 (its final job took 23m09s, with an unusually fast model phase).
This round adds about 3.5% model time locally (880.6s to 911.3s), and the two runners above
were slower: both runs were cut short inside the model, and round 1's head would not have fit
on the second either. Without a complete hosted run the acceptance cannot be shown, and a third
attempt on the off chance of a fast runner is not dependable. So `12af3787` raises **only**
the `regressions` job's `timeout-minutes` from 25 to 40 in `.github/workflows/os-image.yml`
(a comment names the two runs), with the host walk and the pending list regenerated. No test
pins that value; the tools, the VM harness and every other job are unchanged. The fix brief
puts the harness out of scope, not this CI limit, and the change is one line to revert. The
integrator decides whether it stays; stage 1b adds tests to the same job.

**For re-review:**
- `start-next.sh`: every exit before the `set-default` line is `refuse()` with status 3;
  nothing after it can exit 3. `Failed` keeps the old message, and only `start_next` reads its
  status; it archives, then STOPs naming `check`.
- The fakes now report an assertion as status 1 and `SystemExit` with its status, both as
  `Failed`, as the real host does.
- `layout finish`'s guard comes before the login and proof checks. `revert` and `proof`
  stay allowed while restoring (runtime only), as the fix brief names finish alone.
- The model's `original-login` exists only from a fresh login in the trial's boot. Whether a
  restoration began is now in the reduced key and the memo's `layout-pending` input for a
  trial in its own boot only; after a restart it stays provenance, as round 1 proved.
- The CI limit change in `12af3787` (PLAN-GAP above): keep it or revert it.

**Open questions:** none for this round beyond the CI limit above.

Cleanup: every temporary file this round made under `/var/home/ares/pkg22c-work/` (the two
one-off scripts, run logs and test lists) was removed. `.work/` holds no file over 500 MB; no
download was made. No builder-started test or watch process remains, and no Gradle daemon was
started. PR #46 is open and draft; nothing was merged or pushed to main.

## Stage 1b, step 1

Builder: a Claude agent on Opus 5.5 (`briefs/22c-stage-1b-additions.md`, step 1). Additions 1 and 2,
section D (bundle, pins, the waiting list), B9's payload test, F, B12 and addition 3's start block are
built, each pushed after its part. Section C (the guides) is step 2. No VM was dispatched, nothing was
merged or pushed to main, and no owner tool, deployment binary or keyboard command ran on the laptop.
Tested head: **`464f92b4`**; the closing commit changes this report only.

**Two things did not fit the briefs** (details under PLAN-GAP): the tools update itself still requires the
stick, so the folder start block hands over to an `at install` that STOPs `Tools USB label not found` until
the integrator changes that rule (PLAN-GAP 1); and one guide test stays red for step 2, because the guide
quotes a STOP that rule 5 removed (PLAN-GAP 4).

### What is built, per part

**Addition 1: a bounded slice in every checks run, the full model when its sources change**
(`97787831`, `464f92b4`).
- `test_ways_back_model.explore(budget)` is the old exploration loop, unchanged, with an optional state
  budget. `ModelTest.test_reachable_state_space` reads `ARESOS_MODEL_SCOPE`: `full` (the default when
  unset) keeps the pins 963003 states / 25257042 edges; `slice` processes the first **120,000** states in
  the same breadth-first order from `starts()` (each with its invariants and every edge executed against
  the tools) and pins **173,476 discovered states and 3,043,109 edges**. It reaches all eight journal
  outcomes, now asserted for both scopes. The order has no randomness: the pins held locally under two
  hash seeds and on the hosted runner.
- `os/ci/model_scope.py` (new) prints `scope=full` or `scope=slice` from the diff between the merge base
  with `origin/main` and the checkout (`--no-renames`, so both sides of a rename count). Dependencies:
  `os/owner-tools/**`, `os/release/**`, `os/manifest/release.json`, `os/manifest/releases/**`, every
  non-Python file under `os/tests/` (fixtures and anything else beside the tests), the classifier itself,
  and the model's import closure: every module `test_ways_back_model` imports from `os/tests` or `os/ci`,
  recursively, including imports inside functions, also when the file was deleted or a new file would
  shadow the name. That closure is conservative: through `test_owner_update`'s lazy imports it holds most
  of the VM harness (`owner_vm`, `registry_auth`, …), so harness changes select the full model too.
  Anything uncertain (git fails, no merge base, a module that does not parse) selects `full`. On this
  branch it selects `full` (26 dependency paths changed since `16a0c886`).
- The workflow: a new input `full_model` (boolean) forces the full model. The `regressions` job runs the
  whole suite with `ARESOS_MODEL_SCOPE: slice` and its limit is back at **25** minutes (from 40). A new
  `model` job, with the same condition, runs beside it: it classifies, and only when the result is `full`
  installs the two Python packages and runs the one test with `ARESOS_MODEL_SCOPE: full`
  (`unittest discover -s os/tests -p test_ways_back_model.py -k test_reachable_state_space`), limit
  **35** minutes. 22c's ledger bound for an unaccountable checks job follows the larger limit (15 → 35).
  `test_ways_back_probe` and `test_release27` now name both jobs for a checks-only dispatch.
- `ScopeTest` (4 tests): a change to each listed path (also a deleted imported module, a shadowing file,
  a non-Python test file) selects `full` and changes elsewhere (guides, the mod, the report, other tests,
  the waiting list, CI shell scripts) select `slice`; in a fixture git repository the merge base decides
  (main moving on with a model change does not count), a rename lists the old import, the input forces,
  and a missing ref or a missing `.git` select `full`; a child process with an audit hook on every file
  open runs a 2,000-state exploration and every tracked repository file it opens must be a dependency;
  the workflow wiring (input, both jobs' steps, scopes, limits, full history, the ledger bound).

**Addition 2: the namespace step in the image and rehearsal jobs** (`1d3619a3`). 27c's step
(`sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0`, `unshare -Urm true`) now also stands
before the image job's `Install tools on disposable runner` and before the rehearsal job's
`Qualify tools, regressions, …` step. Both suites explore the slice (`ARESOS_MODEL_SCOPE: slice`): the
rehearsal's qualification step has 35 minutes, and the suite with the full model took 32 to 33 minutes
on its own. `SuiteJobsTest` holds every job that runs `unittest discover -s os/tests -v` to the step,
before the suite, unconditional, and to the slice; there are exactly three such jobs.

**D, B9 and F** (`314062a2`).
- `bundle.py`: `rollback.sh`, `default-stock.sh` and `previous.sh` left the payload (`start-next.sh` was
  already in); `os/release/` keeps all three byte-identical. `bundle.py --refresh` printed
  `PASS bundle manifest SHA256 ba4c2bb4…`.
- The 15f stand-in bundle of `ToolsUpdateTest` no longer drops `release/previous.sh` (it is gone from the
  payload); it keeps dropping `history.json` and `release/update.sh`.
- B9: `test_shell_assertions.ShellAssertionTest.test_payload_no_longer_carries_the_three_old_scripts_and_their_repository_copies_stay`
  replaces the old "payload `default-stock.sh` equals the repository copy" lines: none of the three is in
  the payload's `SHA256.json`, `SHA256SUMS` or folder, `start-next.sh` is, and each repository copy keeps
  the SHA-256 version 2's payload recorded for it.
- Bindings: `rebind.py pending` could not express a bound file that no longer exists (two of the deleted
  payload copies were bound by package 27's tables; `checkout_sources` asserts on a missing file). It now
  lists such paths under `removed` in the waiting list; `record` is unchanged. `test_checkout_sources`
  holds the list (bound, absent, never also waiting, not twice; a deleted bound file that is not listed
  fails) and the dda72ed record test leaves out exactly those two gone files and still refuses on its
  CRLF row. The host walk names them under `no_longer_bound`.
- F: `test_invariant_one_working_toolset_after_any_interruption_and_any_refusal` now runs each of the 70
  cells through `refusal_cell` against two tables in the test: the journal phase each cut leaves (asserted
  after the cut) and the cuts at which each injected check runs. Where it runs, both attempts raise the
  exact refusal text (anchored), the phase stays, and the entry reaches the previous tools before
  publication and the new ones after. Where it does not run, the first run completes the update (or, at
  cut 10, says `Tools already installed; nothing changed`), the next run says
  `Tools already installed; nothing changed`, and the new tools answer. The empty `staged bundle` row is
  now `unpublished bundle`: a changed `tools-<fingerprint>/owner.py` while the journal is at copy or
  publish. `test_revert_proof_without_the_layout_check_the_invariant_fails_where_it_runs` executes
  `update_tools` with the layout-trial line removed and requires the layout row to fail at exactly the
  cuts the table names.

  | Refusal | Cuts where its check runs | Exact refusal |
  |---|---|---|
  | layout trial | 1–7 (copy, publish, and retire through `system_ready(resolve=True)`) | `Layout trial is unfinished; prove it or revert first` |
  | transaction | 1–7 | `Deployment transaction active or unknown` |
  | preflight error (`observations`) | 1–7 | `Read failed: rpm-ostree status --json` |
  | unexpected exception (`installed_commands`) | 1–5 (`exclusive()` only) | `unexpected` (RuntimeError) |
  | disk record | 1–10 | `Wrong or ambiguous target disk serial` |
  | resume identity (the stick's UUID in the journal) | 1–9 (not compared once complete) | `Interrupted tools update does not exactly match this bundle/stick; get help` |
  | unpublished bundle | 2–5 (cut 1 dies before the copy; from 6 it is published) | `Bundle hash mismatch: owner.py` |

  Phases: copy after renames 1–2, publish 3–5, retire 6–7, records 8–9, complete 10, as the integrator
  read them. The integrator's reading of the checks differed in one point: `system_ready` also runs at
  retire, so the layout-trial, transaction and observation rows refuse at cuts 6 and 7 too, and the
  revert proof fails at cuts **1 to 7**, not 1 to 5 (PLAN-GAP 2).

**Addition 3: the folder start block** (`c2dcc8e1`). `bootstrap.py` generates two blocks that differ in
exactly their source lines (lines 4–6 of the stick block, lines 4–5 of the folder block). The stick
block is byte for byte what it was (`command(fingerprint)` keeps its default, so `commands.json` and
`owner_vm` are unchanged). The folder block takes `/var/home/ares/ares-tools`, copies it with the same
`cp -R --no-preserve=mode,ownership` into a fresh `mktemp -d /run/ares-bootstrap.XXXXXX`, and then runs
the shared tail. Tests: every tamper case runs for both sources (changed `at`, changed `owner.py`, an
extra file, a missing file, the folder itself a link, a link inside it whose target has the right bytes,
a FIFO in a listed file's place, a wrong fingerprint), nothing executes before verification, the source
is left untouched, and the folder block calls no `mount`; a structure test holds the two blocks to their
source lines; `test_owner_equality` accepts a quoted folder block only byte-equal to the generated one
(each of its 12 lines changed refuses) and an `install-folder` command only equal to it.

### The fingerprint and its pins

`ba4c2bb4…` (tools version 3, this package's
bundle). Pinned in: `docs/INSTALL.md` (both `PASS tools manifest SHA256` copy checks and the fingerprint
line of both bootstrap blocks: four places), `os/owner-tools/commands.json` (`install`),
`docs/INSTALL-STATUS.md` (the update row: "Package 22c's bundle (tools version 3; built, **not on the
laptop**)"; the row's old full `851eb742…` became that short form, still named as the laptop's tools) and
this report. `test_owner_equality.fingerprint_documents()` now treats this report as the current one
(package 27's becomes history); its two intermediate payload fingerprints from stage 1a are shortened to
`d2b40b50…` and `610e1b27…`, as package 27's report shortened its own.

### Slice against the full model

| | States processed / discovered | Edges | Local (nice 10) | Hosted |
|---|---|---|---|---|
| Slice | 120,000 / 173,476 | 3,043,109 | 139.0 s (twice, two hash seeds) | 174.6 s and 159.5 s (runs 43552726228, 43554331874) |
| Full model | 963,003 / 963,003 | 25,257,042 | 911 s (review fixes 2; not rerun here) | 999.4 s and 1271.2 s (model job of the same runs) |

The slice is 12.5 % of the processed states and 12 % of the edges, at 15 % (local) to 17.5 % (hosted) of
the time. Its menu-only destinations and outcome counts are printed in the job log. The model job has
13 minutes of room over the slowest full model seen (1275 s); the checks-only job about 11 over 13m34s.

### Verified

Local, each from the worktree with `TMPDIR=/var/home/ares/pkg22c-work`, at nice 10, one at a time, with
at least 4500 MB available (`free -m` showed 8,500 to 10,000 MB):

| Command | Result |
|---|---|
| `ARESOS_MODEL_SCOPE=slice python3 -B -m unittest discover -s os/tests -p test_ways_back_model.py` | 25 tests in 155.8 s, OK |
| `ARESOS_MODEL_SCOPE=slice PYTHONHASHSEED=12345 … test_ways_back_model.ModelTest.test_reachable_state_space` | 1 test in 139.0 s, OK |
| `python3 -m unittest discover -s os/tests -p test_ways_back_model.py -k ScopeTest` (with bytecode, as hosted) | 4 tests, OK |
| `… -p test_owner_bootstrap.py` | 8 tests in 0.4 s, OK |
| `… -p test_owner_equality.py` | 10 tests in 27.7 s, OK |
| `… -p test_checkout_sources.py`, `test_owner_step_limits.py`, `test_owner_abandon.py`, `test_owner_entry.py`, `test_owner_tools.py` | 5, 4, 6, 3, 13 tests, OK |
| `… -p test_owner_walk.py` | 27 tests in 104.4 s, OK |
| `… -p test_ways_back_probe.py` | 41 tests in 25.0 s, OK |
| `… -p test_owner_path.py` | 39 tests, 1 failure: the update route test (PLAN-GAP 4) |
| `… -p test_owner_retained.py`, `test_owner_commands.py` | 1 and 5 errors, local only: a mocked `glob` gets Python 3.14's `case_sensitive` argument; both pass hosted (Python 3.12) and neither was changed |
| workflow guards: `test_release27.DispatchMatrixTest`, `test_ci_api_permissions`, `test_ci_step_environment`, `test_owner_guard`, `test_rehearsal_budget`, `test_build_tools`, `test_ways_back_probe.DispatchTest`/`SuiteJobsTest`/`JobGatesTest` | 35 tests, OK |
| B9 alone: `test_shell_assertions.ShellAssertionTest.test_payload_no_longer_carries_…` | OK (the rest of that module runs bash fixtures and was left to the hosted run) |

The full model was not run locally in this step. `test_owner_update` ran only hosted. After every bound
change `python3 -B reviews/22c-ways-back-after-update/walk-host.py` ran first (last:
`PASS package 22c host walks (reorder-probe): 255 sources; no VM started`), then
`python3 -B reviews/27-first-update-release/rebind.py pending "<note>"` (last:
`pending: 33 bound files differ from the active bindings, 2 removed`). `git diff --check` passed.

Hosted, each `gh workflow run "OS image" --ref pkg/22c-ways-back-after-update -f checks_only=true`, then
one `gh run watch <id> --exit-status --interval 60`:

| Hosted run | Head | Regressions job | Model job | Result |
|---|---|---|---|---|
| [43552726228](https://github.com/Ares-Empire/AresOS/actions/runs/43552726228) | `1d3619a3` (additions 1 and 2) | 15m57s: **1085 tests in 931.1 s, 5 failures, 0 errors, 0 skipped** | 17m31s: full model, 1 test in 1001.6 s, OK | The four stage-1b pins, plus the audit test's sanity set, which named `owner.py`'s source (the runner had its compiled copy); fixed in `464f92b4`. Watch exit 1. |
| **[43554331874](https://github.com/Ares-Empire/AresOS/actions/runs/43554331874)** | **`464f92b4`** (all four parts) | **13m34s: 1090 tests, 1 failure, 0 errors, 0 skipped** | **21m39s: full model, 1 test in 1273.4 s, OK** | The one failure is PLAN-GAP 4's guide test. Watch exit 1. |

Run 43554331874's regressions log has no unittest summary line: the failing assertion prints all of
`owner.py` as its message and the hosted log ends inside it. The counts above come from the verbose result
lines: 1089 `ok` (1080 `... ok`, 9 `ok` after printed output), 1 `FAIL`, no `ERROR`, no `skipped`. That is
run 43552726228's 1085 plus this head's five new tests (F's revert proof, B9's payload test, two bootstrap
tests, the folder-quote test). F's invariant test, its revert proof (so the layout row fails at exactly
cuts 1 to 7 without the check), every new bootstrap, equality, scope and suite-jobs test, and every
`test_owner_update` test passed there. The slice explored 173,476 states / 3,043,109 edges again
(159.5 s); the model job's full model matched its pins (1271.2 s on that runner). Both jobs ran side by
side: the run took 21m39s instead of 32m53s (run 43547375701).

### JUDGMENT-CALL

1. **The full model runs in its own job beside the checks.** Chosen: a parallel `model` job (35 minutes)
   that classifies and runs only the full model; the checks-only job always explores the slice (25
   minutes). Rejected: classifying inside the checks-only job and running the full model there, which
   needs a limit that depends on a step's output (a second job anyway) and runs 33 minutes in a row;
   raising only the limit. Cost of changing later: one job and a few test lines. A branch that changes the
   model's sources now uses two runners per checks run (on this branch about 16 + 17.5 runner minutes
   instead of 33 on one), counted by the minute ledger.
2. **The image and rehearsal suites explore the slice.** The rehearsal runs on a head whose checks-only
   run explored the full model when its sources changed; the full model would not fit the rehearsal's
   35-minute qualification step. Changing it back is one environment line per job.
3. **Two blocks, not one, and the folder `/var/home/ares/ares-tools`.** Two literal blocks that differ in
   their source lines keep the stick block byte-identical (its tamper tests, `commands.json`, `owner_vm`
   and the laptop's guide stay as reviewed) and give the owner a block with no argument to fill in; one
   block with the source as an argument would put a branch and an untrusted parameter into the trusted
   start. The folder is a fixed literal in the ares home, outside `/var/tmp` (no other account can
   pre-create it), and named like the stick's folder, so the shared lines stay the same. `/var` is shared
   by every deployment, so the path is the same on R27, R13 and stock. Changing the path later means a new
   generated block and its guide quotes.

### PLAN-GAP

1. **The tools update requires the stick (addition 3 cannot work with the start block alone).** The
   bootstrap ends in `bash ./at install`, which on the laptop is a tools update: `install()` →
   `update_tools()` calls `tools_stick()` first (`os/owner-tools/owner.py`, `update_tools`, and
   `tools_stick`), which requires exactly one `ARESTOOLS` USB, mounted once, exFAT, holding a bundle equal
   to the private copy, and the `tools-update1` journal and its receipt record the stick's
   `tools_volume_uuid` and compare it on every resume. From the folder block, `at install` would STOP
   `Tools USB label not found` with nothing changed (the private copy stays in `/run` until restart). The
   change belongs to the owner tools' rules (reviewed SAFE in stage 1a) and to rule 9's journal fields,
   which version 2's `settle_tools` reads until publication; this step was told not to change a rule, so
   it did not. The integrator decides: for example, accept a source that is either the stick or the folder
   and journal which one (a folder's identity in place of the volume UUID), with tests that version 2's
   `settle_tools` still reads the journal at every cut before publication. The F table's resume-identity
   row would change with it.
2. **F, the integrator's reading.** `system_ready` runs in copy and publish **and at retire**
   (`system_ready(resolve=True)` before the old tools retire), so three rows refuse at cuts 1–7 and the
   layout revert proof fails at cuts 1–7. `installed_commands` runs in copy and publish only, the disk
   record at every cut, the stick identity comparison at cuts 1–9, as read. The staged-bundle injection was
   indeed empty at every cut; it is now the new directory before publication (cuts 2–5).
3. **Deleted bound files.** D deletes payload files that package 27's tables bind, and neither
   `rebind.py pending` nor `checkout_sources` could express that. `pending` now writes `removed`; stage 2's
   record step must move `removed` into the `rebound` history with the rest and empty it.
4. **One guide test stays red for step 2.** `test_owner_path.OwnerPathTest.test_update_route_orders_windows_tools_update_title_reboot_check_with_pass_stop_and_returns`
   now passes its fingerprint pin and stops at the next assertion: the update route quotes
   **did not finish at the restart** (`docs/INSTALL.md` update route, `docs/EMERGENCY.md` "Failed or bad
   update"), and the test requires that STOP text in `owner.py`; rule 5 removed it. Rewriting those
   sentences is section C; the test's quote list is one of B9's expectations that change on purpose.
5. **E's route in the 22c host walk.** D and B12 ask for the walk regenerated for E's route, which needs
   E's mode in `owner_vm` (the rehearsal harness) and the guide's tools-only route (step 2). Neither was in
   this step's list; the walk still covers the probe route and was regenerated after every bound change.
6. **The ledger's checks cap.** `os/ci/rehearsal-packages.json` allows 12 checks-only dispatches for 22c;
   the branch now has 18 since its first dispatch (16 before this step). `rehearsal_guard.budget` asserts
   that cap when stage 2 dispatches its rehearsal, so it will STOP there until the integrator raises the
   cap (a budget decision; not changed here).
7. `os/ci/model_scope.py` is a new file outside the original brief's file list; addition 1 needs it.

### Open questions

- PLAN-GAP 1 needs an integrator decision before the guides promise the folder route.
- PLAN-GAP 6 needs a ledger decision before stage 2.

### For step 2

**Tool lines** (Claude on the laptop, as `ares`, never as root; `<commit>` is the announced commit):

```bash
git -C /var/home/ares/AresOS fetch origin
rm -rf /var/home/ares/ares-tools
git -C /var/home/ares/AresOS archive --prefix=ares-tools/ <commit>:os/owner-tools/payload | tar -x -C /var/home/ares
sha256sum /var/home/ares/ares-tools/SHA256SUMS
```

The last line must print `ba4c2bb4…` (the block
checks it again). `git archive` takes the committed payload, whatever the checkout's working tree holds.
The folder must hold nothing else: an extra file refuses. Then the owner approves the password prompt of
this block, the exact text the guide must quote (`bootstrap.command(fingerprint, 'folder')`):

```bash
sudo bash -c 'set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin; umask 077
trap "echo STOP bootstrap: verification or install refused" ERR
p=$(mktemp -d /run/ares-bootstrap.XXXXXX)
cd "$p"; cp -R --no-preserve=mode,ownership /var/home/ares/ares-tools .; test ! -L ares-tools; cd ares-tools
test -z "$(find . ! -type d ! -type f -print -quit)"
echo "ba4c2bb4…  SHA256SUMS" | sha256sum -c --strict
cmp -s \
  <(find . -type f -printf "%P\n" | sort) \
  <({ cut -c67- SHA256SUMS; echo SHA256SUMS; } | sort)
sha256sum -c --strict SHA256SUMS
bash ./at install'
```

It prints what the stick block prints after its source lines: sha256sum's `SHA256SUMS: OK` and one `: OK`
per file, then `at install`'s lines. Until PLAN-GAP 1 is resolved, `at install` STOPs there with
`Tools USB label not found`, so the guide must not present the folder route as working yet. The stick
block stays as it is (`commands.json` `install`, two copies in `docs/INSTALL.md`).

What the tests expect from step 2:
- A quoted folder block must be byte-equal to the generated one (`check_bootstrap` already enforces this
  and returns how many the guide quotes). Add it to `commands.json` as `install-folder` (the check holds
  that key to the generated block); then `test_every_owner_command_equals_the_command_physically_typed_by_ci`
  requires it in the guides and typed by a CI walk, or listed under `unwalked_commands` in the waiting
  list, which `rebind.py` does not write.
- Add the route assertions (the folder way first, the stick as the fallback) to `test_owner_path`.
- PLAN-GAP 4: rewrite the **did not finish at the restart** sentences and that test's quote list.
- The fingerprint pins are done; keep `851eb742…` short wherever it names the laptop's tools.

Cleanup: the run logs under `/var/home/ares/pkg22c-work/` were removed with the folder. `.work/` holds no
file over 500 MB; no download was made. No builder-started test or watch process remains, and no Gradle
daemon was started. PR #46 is open and draft; nothing was merged or pushed to main.

## Stage 1b, step 2: the guides

Builder: a Claude agent on Opus 5.5 (`briefs/22c-stage-1b-additions.md`, step 2, and its "Decision after step 1").
Section C is written against step 1's lines; the guides keep the stick route and no guide routes to the folder
block (package 22d). Nothing else in the owner tools changed. No VM was dispatched, nothing was merged or pushed to
main, and no owner tool, deployment binary or start block ran on the laptop. Tested heads: `45059edf` (hosted run 1) and **`3908ec4e`** (hosted run 2); the closing commit changes this report only.

### What changed, per guide

**`docs/INSTALL.md`, update route** (`51fa6868`, one wording fix in `898ac0d4`).
- The gate line keeps its pinned sentence and adds that step 7's record also covers the new last box (forward
  again, or back from plain Bazzite: no announcement, stick, login or network), while new tools or a new release
  still need the announcement and this guide's fingerprint.
- The paragraph on three deployments now says what works: three installed systems (newer AresOS, older AresOS,
  plain Bazzite); each command names where the next start goes, works from every installed system and never creates
  or deletes one (update the newest, previous the older, rollback on an AresOS and keep-stock on plain Bazzite the
  stock); layout trials on an AresOS that starts next; titles with the boot menu's rows; links to the boot menu and
  the notice list. **Older tools STOP these with `Expected exact stock/AresOS pair`: install the current tools first.**
- New box **Tools only** after the tools box: `check` and `title` in the same root session, then unplug (the block
  has unmounted the stick), record, return to step 8. Nothing else: no stage, no restart. This is the route E step 1
  rehearses and the laptop session will follow.
- Stage box: only on the AresOS that runs and starts next; rule 6's two lines (the AresOS removed at shutdown,
  whichever it is; from the older AresOS the settings line); the refusals as v3 has them (a change waiting for the
  restart, a half-written layout, no more "queued rollback" or "not newer"); on stock or a non-first AresOS it stages
  nothing and names the next step; the same-boot interrupted STOP moved here (it can only appear before a restart).
- Title box: the provisional title's **Boot menu after the update finishes at shutdown (expected):** line, which the
  card uses. Restart box: "take only a row your last title named" replaces "never a guessed GRUB title".
- Check box: the confirmation plus rule 5's other outcomes: **was not applied** (finalize did not happen; nothing
  lost; Help decides a repeat), **is in place and has not started yet** with **this start was not the default**
  (another row taken: restart with no choice), and the STOP **did not finish as recorded**.
- Misbehaves box: previous as before, then forward again (the last box) and, if the older release misbehaves too,
  rollback, then Windows.
- New last box **Forward again, or back from plain Bazzite**: `update` and `title`, no stick/login/network; the
  three answers (**Newest AresOS starts next**, **… already starts next; nothing changed** with **It runs now** or
  **It does not run yet: …**, **Newest installed AresOS starts next** with its next step); restart with no choice;
  check **Update to … confirmed after the restart**; from plain Bazzite previous the same way.
- Step 8's list of later work links the new "Back to AresOS from stock".

**`docs/EMERGENCY.md`, "Failed or bad update"** (`2a79c65d`). New order: not starting → F12 → Bazzite → the boot-menu
row the last (provisional) title named for the AresOS before the update → previous → title → reboot → check
**Return to … confirmed after the restart**. Misbehaving → previous first, then rollback, then Windows. The old
AresOS returning by itself → `check` first; **Update to … was not applied** means nothing is lost and previous must
**not** run (it would go one release further back). "Choose the row the last title named"; without a title any row
is safe. The removed STOP is replaced (PLAN-GAP 4 of step 1): **did not finish as recorded** / **interrupted before
its result was recorded** → export, Help. The "they refuse with three deployments" sentence is gone; the old
tools' line means install the current tools first. Also: the stale-title card says it holds until AresOS has started
once; the layout card quotes rule 7's new abandon refusal.

**`docs/INSTALL-PROCEDURES.md`** (`16eb2e92`).
- Later layout: each installed system keeps its own layout; a trial only on a running AresOS that starts next; on
  plain Bazzite it refuses (quoted); with old tools, install the current ones first.
- Abandoned trial: the repeat's refusal is now `No layout trial and no half-written layout to abandon on this
  system; nothing changed`; the repair note (rule 7) is explained: run abandon once on the system it names.
- Recovery menu: rows **Bazzite (ostree:N)** that differ only in the number; take the row the last title's
  **Boot menu at the next start:** line named; a wrong choice is harmless (check names what runs and what starts
  next, every command works, a restart with no choice starts the default). First switch and pre-AresOS stale titles
  keep Windows → Help. With the old tools, do not use the menu after an update.
- Rollback and keep-stock beside two releases, each with the lines the tools print and the side refusal.
- New **Back to AresOS from stock**: update (or previous) through the update route's last box; no stick, login or
  network. New **What you notice on each system** (the notice list).
- "Keep stock", "Back to AresOS from stock" and the notice list carry, word for word: **Never start a Bazzite update
  while AresOS is installed: it deletes both AresOS versions at the next shutdown.** "until the owner chooses stock
  permanently" is deleted; choosing plain Bazzite for good links to step 9. Rule 10's WARNING line and its STOP
  are named with their next step.

**`docs/INSTALL-REFERENCE.md`** (`a14caf27`): the hung-restart note quotes `Unknown deployment beside AresOS and the
saved stock; get help` in place of version 2's `Final pair has extra/missing deployments` (gone from `owner.py`);
the console's return list names "back to AresOS from stock".

**`docs/INSTALL-STATUS.md`** (`07d4dfad`): a new row **Ways back after an update (package 22c)** — BUILT AND
REVIEWED (the state machine, review 3; the stage 1b review follows); NOT REHEARSED YET; NOT ON THE LAPTOP; the
laptop's tools stay `851eb742…` until the owner installs these; the full fingerprint `ba4c2bb4…`; what must happen
before it may say "on the laptop" (the rehearsal, the install through the tools-only update, then the owner's calm
test); LOQ shortcuts and recovery menu stays OPEN. The update row keeps 27b's pinned record word for word and now
names `851eb742…` as the laptop's tools until 22c's are installed. The owner-path documents row names 22c's rewrite.

**What he will notice**, now in the guides: plain Bazzite has no `ares` account and keeps German; the AresOS from
before an update has no `ares` password and no administrator rights; his files stay; each system keeps its own
passwords, Wi-Fi and layout; once releases carry My apps (packages 34 and 35), the app list stays empty after going
back to an older release until he goes forward again, nothing lost.

### The tool lines the guides quote

Every bold or code quote below is checked against `owner.py` by `test_owner_path` (literal source fragments);
`Expected exact stock/AresOS pair` against version 2's code at `41b06513` (`git show`, as
`test_ways_back_compatibility` does).

| Where | Quoted line (… = a name or reference the tools fill in) |
|---|---|
| Titles | `… runs and starts next`, `… runs; … starts next, after the restart`, `… runs; … starts next; this start was not the default`, `… runs and now starts next; no restart is waiting`, `Boot menu at the next start:`, `Boot menu after the update finishes at shutdown (expected):`, `WARNING: … Bazzite must not update while AresOS is installed` |
| Rule 5 | `Update to / Return to / Rollback to / Change to … confirmed after the restart`, `… was not applied: the deployments are as before it, and nothing is waiting`, `… is in place and has not started yet`, STOPs `… did not finish as recorded`, `… was interrupted before its result was recorded; do not reboot` |
| Destinations | `Newest AresOS starts next`, `Newest installed AresOS starts next`, `The release of these tools is newer still`, `… already starts next; nothing changed` with `It runs now` / `It does not run yet: it starts at the next restart`, `Saved stock rollback queued`, `Saved stock is default`, `Previous AresOS queued for the next start`, `Plain Bazzite runs here: use … keep-stock` |
| Rule 6 | `… is removed when the update finishes at shutdown`, `The new release starts with this system's settings (Wi-Fi, passwords, layout), not …'s` |
| Rule 7 | `Plain Bazzite keeps the installer's German layout: no layout trial here`, `No layout trial and no half-written layout to abandon on this system; nothing changed`, `The trial began on another system and its finish had started`, `This system's half-written layout is restored to the settings before its trial` |
| Rule 10 | `A Bazzite update is waiting. Do not restart`, `Bazzite must not update while AresOS is installed` |
| Gone | `did not finish at the restart` (rule 5), `Missing private layout-pending record` (rule 7), `Final pair has extra/missing deployments` (rule 1); each is asserted absent from the guides it was in |

### Test expectations changed on purpose (B9, guides)

All in `os/tests/test_owner_path.py`; no test was deleted or skipped.

| Test | Old expectation | New expectation | Rule |
|---|---|---|---|
| `test_update_route_orders_…` | 8 boxes; intro says three deployments refuse, the previous box or Windows; quotes "did not finish at the restart"; "never a guessed GRUB title" | 10 boxes (tools only third, forward again last) in order; intro says what works and what the old tools' STOP means; rule 5's outcomes, rule 6's lines and both new boxes in order; every quote found in `owner.py`; the old phrases absent | C, A4–A6, A8 |
| `test_failed_update_card_returns_to_previous_aresos_or_windows_never_a_grub_title` → `test_failed_update_card_takes_the_titled_row_then_previous_rollback_and_windows` | Windows before previous; "Never choose a guessed GRUB title"; "they refuse with three deployments"; recovery menu and later layout say "three deployments" | The titled row, then previous; misbehaving: previous, rollback, Windows in that order; "choose the row the last title named", any row safe; was-not-applied → no previous; recovery menu and later layout say what works now | C, A5, A8 |
| `test_hung_restart_…` | `Final pair has extra/missing deployments` | `Unknown deployment beside AresOS and the saved stock; get help`, found in `owner.py`; the old line absent there and in the guide | A1 |
| `abandon_card_route`, `test_card_clears_real_pending_state_…` | `Missing private layout-pending record` | `NO_TRIAL` (the exact rule 7 refusal, anchored) in the guide, the route and the handler | A7 |
| new `test_stock_procedures_go_back_to_aresos_and_never_update_bazzite` | — | the Bazzite sentence in keep-stock, back-to-AresOS and the notice list; no fenced update outside the gated route; rollback/keep-stock lines beside two releases; the notice list's facts | C, A10 |
| new `test_status_names_22c_built_not_rehearsed_and_not_on_the_laptop` | — | the 22c row's status, fingerprint (equal to the payload's), `851eb742…`, the conditions for "on the laptop"; the recovery-menu gate OPEN | C |

### The checks-only cap

`os/ci/rehearsal-packages.json`, 22c: `dispatch_caps.checks` **12 → 30** (`45059edf`), with the reason in the ledger's
`budget` text. Why: the ledger (read-only, `rehearsal_guard.budget` against the API on 2026-11-14) showed **18 checks
runs and 1 probe, 446 of 1200 minutes**, so `budget()` already STOPped with `checks dispatch allowance exhausted` and
stage 2's dispatch could not start. Each checks run now costs about 35 runner minutes on this branch (the full model
job runs beside the checks while its sources differ from main). After one rehearsal reservation (345) about 11
more checks runs fit in 1200 minutes, so 30 (12 more) lets the minute cap stay the real bound, which is what the cap
is for: it stops a runaway dispatch loop, not spending (standard runners are free for this public repository). The
minute cap and the four-VM cap are unchanged. Stage 2 should know the minutes are the tighter limit now: every
further checks run costs about 35 of the remaining minutes (688 after this step's two runs: the ledger reads 20 checks runs, 1 probe and 512 of 1200 minutes).

### Verified

Local, from the worktree, `TMPDIR=/var/home/ares/pkg22c-work`, `nice -n 10`, one module at a time:

| Command | Result |
|---|---|
| `python3 -B -m unittest discover -s os/tests -p test_owner_path.py` | 41 tests, OK (first run: 2 failures, both in my edits, fixed: a quoted fragment and the stage box's pinned lead) |
| `… -p test_owner_entry.py`, `test_owner_equality.py`, `test_owner_bootstrap.py`, `test_grub_bls.py` | 3, 10, 8, 6 tests, OK |
| `… -p test_ways_back_probe.py` | 41 tests, OK after the host walk was regenerated |
| `… -p test_checkout_sources.py` | 5 tests, OK |
| `python3 -B reviews/22c-ways-back-after-update/walk-host.py` | `PASS package 22c host walks (reorder-probe): 255 sources; no VM started` |
| `python3 -B reviews/27-first-update-release/rebind.py pending "<note>"` | `pending: 34 bound files differ from the active bindings, 2 removed` (`docs/EMERGENCY.md` joins the list) |

`test_owner_update` did not run locally. `git diff --check` passed before each commit.

Hosted:

Each `gh workflow run "OS image" --ref pkg/22c-ways-back-after-update -f checks_only=true`, then one
`gh run watch <id> --exit-status --interval 60`. Totals from the regressions log's own summary line.

| Hosted run | Head | Regressions job | Model job | Result |
|---|---|---|---|---|
| [43557895861](https://github.com/Ares-Empire/AresOS/actions/runs/43557895861) | `45059edf` (all five guides, the route tests, the cap, the bindings) | 13m52s: **`Ran 1092 tests in 764.752s` / `OK`: 0 failures, 0 errors, 0 skipped**; the slice 173,476 states / 3,043,109 edges (154.8 s) | 18m38s: full model, 963,003 states / 25,257,042 edges, 1 test in 1090.7 s, OK | Watch exit 0. 1092 = step 1's 1090 + the two new route tests; PLAN-GAP 4's test passes. |
| **[43559488500](https://github.com/Ares-Empire/AresOS/actions/runs/43559488500)** | **`3908ec4e`** (the two precision fixes `898ac0d4` and this section) | **14m01s: `Ran 1092 tests in 781.076s` / `OK`: 0 failures, 0 errors, 0 skipped**; the slice again 173,476 / 3,043,109 (160.5 s) | **17m11s: full model, 963,003 states / 25,257,042 edges, 1 test in 992.6 s, OK** | Watch exit 0. |

Both logs end with the unittest summary line, so no per-test summing was needed. After run 2 the ledger reads 20 checks runs,
1 probe and **512 of 1200 minutes** (each run 33). The closing commit after run 2 changes this report only.

### JUDGMENT-CALL

1. **The way back from plain Bazzite is the update route's last box, behind its gate.** The walk test treats a fenced
   `at update` line as an update and allows it only inside the gated route; a fenced one in INSTALL-PROCEDURES fails
   it, and an inline one there would only slip past it. So the box sits at the end of the route, the gate line says
   step 7's record covers it, and "Back to AresOS from stock" links to the route's start (the walk enters through the
   gate). Cost: on the phone he scrolls to the last box. Changing it means a second gated section and a walk change.
2. **The tools-only box unplugs the stick without `at export`.** The brief says check and title, nothing else; the
   block unmounts the stick on exit (step 4 already says so). Adding export later is one line.
3. **The card's "old AresOS returns by itself" branch** says check first and never previous after **was not
   applied**: previous would go one release further back. The brief's card did not name this case.
4. **The notice list's password fact names release 13.** The brief's "the AresOS from before the update has no
   `ares` password" is true on the laptop (R13 is not wheel; the password was set on R27). After a later update from
   R27 the older system would be R27, with its password. The list says "the AresOS from before your first update
   (release 13)" and that a later update starts the new release with the running system's settings (`898ac0d4`).

### PLAN-GAP

1. The STEP8_RECORD clause in the INSTALL-STATUS update row ("… refuse … until package 22c") is pinned word for word
   as 27b's record; it stays, and is still true for the laptop's version 2 tools. Rewrite it with the record step
   when 22c reaches the laptop.
2. The 22c host walk still covers only the probe route; E's route and its regeneration are stage 2's (step 1,
   PLAN-GAP 5). The tools-only box is the guide text E step 1 must type.
3. `test_owner_path` now runs `git show 41b06513:…` (the old tools' STOP); every job checks out full history
   (`fetch-depth: 0`), as `test_ways_back_compatibility` already needs.
4. `os/tests/ways_back_ledger.py` still labels a model stop `Missing private layout-pending`: the model's own word,
   not a guide quote; left alone (the model must not change for the guides).

### For the reviewer of the guides (read in this order)

1. `docs/EMERGENCY.md` "Failed or bad update": the order, and the was-not-applied branch.
2. `docs/INSTALL.md` "Update AresOS to a new release": the gate line, the intro, the tools-only box, the check box's
   outcomes, the last box.
3. `docs/INSTALL-PROCEDURES.md`: recovery menu, rollback, keep-stock, back to AresOS from stock, what you notice.
4. `docs/INSTALL-STATUS.md`: the 22c row (does it claim more than built and reviewed?).
5. `os/tests/test_owner_path.py`: the two rewritten and two new tests, and that each quote is bound to `owner.py`.

Cleanup: the run logs under `/var/home/ares/pkg22c-work/` are removed; `.work/` holds no file over 500 MB; no download
was made; no builder-started test or watch process remains; no Gradle daemon was started. PR #46 stays draft; nothing
was merged or pushed to main.

## Review fixes 3

Builder: a Claude agent on Opus 5.5 (`briefs/22c-review-fixes-3.md`; review 4, gpt-6-astra high on `f3369b8d`,
CHANGES-NEEDED). Four fixes, one commit each, pushed after each: `3bfcfecf` (1), `a2666ac9` (2), `d4bb6314` (3),
`02f52057` (4), then `5c7dbef6`: the 22c row of `docs/INSTALL-STATUS.md` still said the card "takes the titled row,
then previous" and that the stage 1b review "follows"; it now names the card's new route, that the forward and back
box never installs a release, and review 4 with its fix check to come. **No rule of the owner tools changed:** nothing under `os/owner-tools/` or `os/release/` was touched,
and the bundle stays `ba4c2bb4…`. No VM was dispatched, nothing was merged or pushed to main, and no owner tool,
start block, `rpm-ostree`, `bootc` or `ostree admin` ran on the laptop. Tested head: **`5c7dbef6`**; the closing
commit changes this report only.

**How the routes were traced.** Each guide route was followed in `os/tests/ways_back_ledger.py`, the reference rules
that the full model holds to the tools on every reachable edge (963,003 states, 25,257,042 edges), so a route traced
in the ledger is what the tools do. Every traced case below is also asserted by a test in `os/tests/test_owner_path.py`,
so each checks run traces them again. The provisional title's expected menu is `(ostree:0)` the new release,
`(ostree:1)` the AresOS that ran before the update, `(ostree:2)` plain Bazzite. "Finish lost" is the ledger's power-off
during the shutdown: the staged release is discarded and the list stays as before the update. Release names below are
the ledger's (13, 27, 28; S is plain Bazzite); "tools 28" means the bundle's release is 28.

### 1. (Blocking) Check before previous

**Changed.** `docs/EMERGENCY.md`, "Failed or bad update": the three ways in (the new AresOS does not start: the row the
provisional title named for the AresOS before the update; it starts but misbehaves, or the old one returns by itself:
stay) all lead to `sudo /var/lib/ares/at check` **first**, never previous before it, however Linux started. Then one
branch per result: **Update to … is in place and has not started yet** → previous, title, reboot with no choice, check
**Return to … confirmed after the restart**; **Update to … confirmed after the restart** (on a later day the first line
**newer AresOS … runs and starts next** with that confirmation in the record) → misbehaves: previous the same way, works:
the update route's check; **Update to … was not applied** → do **not** run previous, and only if the first line says
**this start was not the default**, reboot with no choice so the AresOS from before the update starts again; Help
decides each repeat; a STOP → export, Help. Then rollback, then Windows, as before. The update route's misbehaves box
now runs check first and previous only on the newer release this route installed (its confirmation; anything else,
above all **was not applied**, goes to the card); its check box's not-applied outcome says "Do **not** run previous";
the recovery menu says check comes first after any boot-menu choice after an update, and why.

**Traced** (37 cases: four starts stage an update; a finished shutdown with no choice and each of three rows, the
new release's two ways counted twice; a lost one with no choice and each row of the list as before):

| Before the update | Shutdown | Row taken → boots | check shows | Stage 1b card | This card ends on |
|---|---|---|---|---|---|
| 27, 13, S; tools 28 | finished | no choice or row 0 → 28 | Update … confirmed | (the new one runs) | 28; misbehaves: previous → 27, Return confirmed |
| | finished | row 1 → 27 | in place, not started | previous → 27 | previous → 27, Return confirmed |
| | finished | row 2 → S | in place, not started | (stock started) | previous → 27, Return confirmed |
| | lost | no choice or row 0 → 27 | was not applied | check first → 27 | no previous; 27 runs and starts next |
| | lost | **row 1 → 13** (the titled row) | was not applied | **previous → 13: one release back** | no previous; restart, no choice → 27 |
| | lost | row 2 → S | was not applied | (stock started) | no previous; restart, no choice → 27 |
| 13, S (tools 27 or 28); 27, S (tools 28) | finished | each row, no choice | as above | as above | the new one, or previous → the AresOS before |
| | lost | each row, no choice | was not applied | previous refuses (`Only one AresOS is installed …`) | no previous; restart, no choice → the AresOS before |

Every case ends on the AresOS from before the update, or on the new release when it runs and works. The test also
follows stage 1b's route (previous straight after the titled row) and requires it to go wrong in exactly one case,
review 4's: three systems before the update, finish lost, row 1.

**Tests.** `test_failed_update_card_takes_the_titled_row_then_previous_rollback_and_windows` is renamed
`test_failed_update_card_checks_first_then_previous_only_where_the_update_is_in_place` with its expectations changed on
purpose (table below), and also holds the misbehaves box, the check box's outcome and the recovery menu. New:
`test_failed_update_card_routes_every_traced_case_to_the_aresos_from_before_the_update` reads each branch from the card
(its commands in order, previous absent from the not-applied branch) and follows it in the ledger for the 37 cases.

### 2. (Blocking) The back-from-stock box never starts an update

**Changed.** `docs/INSTALL.md`, last box **Forward again, or back from plain Bazzite**: "This box only chooses between
installed systems; it never installs a release." Update's answers are now three bullets: a change (**Newest AresOS
starts next** or **Newest installed AresOS starts next**: restart, confirmation), nothing changed (fix 3), and **The
release of these tools is newer still** (after either line): "do **not** follow it here: it would stage that release
without its announcement. This box ends once the installed release runs; a new release comes only through the boxes
above, with the maintainer's announcement." `docs/INSTALL-PROCEDURES.md`, "Back to AresOS from stock", says the same
in one sentence. The old "names its next step: follow it" is gone (asserted absent).

**Traced.** All 750 states that update, previous, rollback, keep-stock, title, every restart and every lost finish
reach from the model's starts; 417 of them are box entries (idle, on plain Bazzite or on the older of two AresOS):

| update runs on | Tools' release installed | update does (states) |
|---|---|---|
| plain Bazzite | yes | reorder (100), nothing changed (52) |
| plain Bazzite | no | reorder (46), nothing changed (26), each with "newer still" |
| older AresOS, not first | yes | reorder (42), nothing changed (49) |
| older AresOS, not first | no | reorder (14), nothing changed (14), each with "newer still" |
| older AresOS, first | yes | reorder (54) |
| older AresOS, first | no | **stages the tools' release at once (20)** |

Wherever "newer still" is printed, following it (restart unless the newest runs, then update again) stages that
release: the review's case is tools 28 with 27 and S installed, on S. **A second way to stage, not in the review:** the
last row. Forward again from the older AresOS that starts next, while the tools' release is not installed, stages it
with the box's first command, before any line can be "not followed" (for example tools 28, list 13, 27, S, running 13:
reached by previous after an update that was not applied, or by new tools installed before their release). It is the
same failure (the "no new release" box starting an update), so the box now says: "**Forward again** only when the last
update route you followed finished: its check showed **Update to … confirmed after the restart**, or it was the
tools-only box. Otherwise, on an AresOS that starts next, update would stage the release of your newer tools without its
announcement → **STOP → Help**." That condition is exactly the ledger's "tools' release installed": a confirmed update
installed it, a tools-only announcement carries an installed release, and only an update removes one. On plain
Bazzite update never stages (the box says so). This is a guide fix; a tool-side guard would be firmer (open question 1).

**Tests.** New `test_forward_and_back_box_never_installs_a_release`: the box's and the procedure's sentences; then over
the 417 entries, update and previous never stage except in the excluded row (where the test requires that update
stages, so the condition is needed), previous beside one release refuses with the list unchanged, and following
"newer still" stages. The update route's order list changed on purpose for the box's new layout.

### 3. (Should-fix) A return that changes nothing has its own completion

**Changed.** The box's nothing-changed bullet: "nothing was needed and nothing was recorded, so no confirmation line is
needed (one can still appear for an earlier change). With **It runs now** you are there. With **It does not run yet: it
starts at the next restart**, restart as in the bullet above, with no boot-menu choice. Either way the box is complete
with `PASS check` whose first line names that AresOS with **… runs and starts next**." Previous from plain Bazzite names
both outcomes. "Back to AresOS from stock" gives the no-op PASS. **Found while tracing:** "Rollback from running
AresOS" had the same gap (an AresOS taken in the boot menu while plain Bazzite starts next: rollback says **Plain
Bazzite … already starts next; nothing changed** and **It does not run yet**, then neither **Saved stock rollback
queued** nor the confirmation can come); it now names that case and its completion. Keep-stock already told the two
apart.

**Traced** (the same 750 states; every idle state and each command that neither refuses nor stages; after a change the
restart with no choice, after nothing changed a restart only for "It does not run yet"):

| Command | Changed: confirmed after the restart | Nothing changed, no confirmation | Nothing changed, an earlier open change confirms |
|---|---|---|---|
| update | 382 | 47 | 159 |
| previous | 389 | 46 | 144 |
| rollback | 293 | 20 | 104 |
| keep-stock | 136 | 32 | 56 |

In every case the command's system then runs and starts next and check passes. Review 4's case (27, 13, S, no
journal, S taken in the menu, update) is in the second column. The third column is why the guides say a confirmation
is not *needed* rather than "none follows": an earlier change still open (for example an update in place and not
started) confirms itself at that start.

**Tests.** New `test_a_return_that_changes_nothing_completes_without_a_confirmation`: the three places' sentences
(and "no confirmation line follows" absent); the table above, with each column non-empty for all four commands.

### 4. (Should-fix) Changed tools always get the full model

**Changed.** `os/ci/rehearsal_guard.py`: `model_gate(result, sha)`, called for every package 22c VM mode in both guard
steps of the rehearsal job (the budget step, `probe-budget-ci`, so such a dispatch stops before it spends its minutes;
and the gate before any VM, `ci`). It asks `model_scope.decide()` for the checkout (uncertain counts as changed); with
`slice` it records `not-needed`; with `full` it requires a passing checks-only run on the same head whose job **Full
ways-back model when its sources changed (no image build or VM)** completed the step **Run the full ways-back model**
with success, read from GitHub's jobs listing, and STOPs `the full ways-back model has not passed on this head, and
its sources changed (…); dispatch checks_only on this head first` otherwise. The authorization records the result
under `model`. The workflow's comment beside the rehearsal's `ARESOS_MODEL_SCOPE: slice` names the gate. Rejected: running
the model job for rehearsal dispatches too (a parallel job does not hold the VM back, and making the rehearsal job wait
on it changes the rehearsal condition every package shares); `owner_vm` checking the record as well (the gate has no
pending state: both guard steps STOP, so the VM step never runs).

**Tests** (`test_ways_back_probe.LedgerTest`): new `test_the_model_gate_reads_the_model_jobs_full_step_by_its_workflow_names`
(the constants equal the workflow's job and step, which runs only for scope `full` with `ARESOS_MODEL_SCOPE: full`);
new `test_changed_model_sources_need_the_full_model_passed_on_the_same_head` (slice: nothing read; passed; and seven
STOPs: no checks-only run, the full step skipped or failed, another head, a failed run, the job of another head, a
step of that name in another job); new `test_a_direct_vm_dispatch_stops_before_its_minutes_and_its_vm_without_the_full_model`
(the review's case through `main()`: in both guard steps a direct dispatch STOPs with changed sources, passes as
before with unchanged ones, in `ci` through its own native step, and passes naming the run with a passing full model).
Revert proof: with `model_gate` replaced by a no-op, the direct-dispatch test fails in both steps (2 failures); with
it, it passes. `test_ci_api_permissions` declares the gate's jobs GET (`actions: read`, already granted to the jobs
that run the guard). The existing `test_the_guard_step_reserves_and_writes_package_22cs_authorization` now pins the
scope to `slice` so it does not depend on the checkout's git state, and asserts the `model` record.

**Cost for stage 2.** While the model's sources differ from main (every head of this branch), the rehearsal needs a
passing checks-only run on its exact head first: about 35 ledger minutes each, beside the rehearsal's 345.

### Test expectations changed on purpose (B9)

| Test | Old expectation | New expectation | Finding |
|---|---|---|---|
| `test_failed_update_card_…` (renamed, see 1) | the titled row, then previous; "misbehaves: **previous** first"; "every command still works" on the card; "do **not** run previous" only for the old AresOS returning by itself | check first however Linux started; previous only in the in-place and confirmed branches, once on the card; "Do **not** run previous" in the not-applied branch; the misbehaves box, the check box and the recovery menu say the same | 1 |
| `test_update_route_orders_…` (the last box's part) | one paragraph: **Newest AresOS starts next**, nothing changed, then reboot and the confirmation for both | the box's never-installs and forward-again sentences, then three bullets in order: change (restart, confirmation), nothing changed, newer still | 2 |
| `test_the_guard_step_reserves_and_writes_package_22cs_authorization` | no model record | scope pinned to `slice`; the record `not-needed` | 4 |

No test was deleted or skipped; `test_owner_path` grows from 41 to 44 tests, `test_ways_back_probe` from 41 to 44.

### Verified

Local, from the worktree, `TMPDIR=/var/home/ares/pkg22c-work`, `nice -n 10`, one module at a time (8.5–10 GB free):

| Command | Result |
|---|---|
| `python3 -B -m unittest discover -s os/tests -p test_owner_path.py` | after each fix: 42, 43, 44 tests, OK (fix 1's first run: the count placeholder and a reboot without its PASS line in my card text, both fixed; fix 2's: my test sliced at the wrong **Record:** and treated previous's one-release refusal as a failure, fixed; fix 3's: my test expected a confirmation in the same boot as a change, fixed) |
| `… -p test_owner_entry.py`, `test_owner_equality.py` | after each guide fix: 3 and 10 tests, OK |
| `… -p test_checkout_sources.py`, `test_ways_back_probe.py` | after each fix: 5 tests OK; 41, then 44 tests OK |
| `… -p test_ci_api_permissions.py` | first 8 failures (the gate's GET not yet declared), then 4 tests OK |
| `… -p` each of `test_build_tools`, `test_ci_step_environment`, `test_installer_webui`, `test_job_accounting`, `test_keyboard_release`, `test_organization_budget`, `test_owner_capabilities`, `test_owner_devices_native`, `test_owner_guard`, `test_owner_login`, `test_owner_staged_release`, `test_owner_step_limits`, `test_probe_native`, `test_rehearsal_auth`, `test_rehearsal_budget`, `test_rehearsal_history`, `test_rehearsal_retry`, `test_release27`, `test_release_squash_binding` (every module that reads the guard or the workflow) | 3, 4, 9, 11, 5, 19, 6, 14, 12, 18, 7, 4, 4, 9, 4, 9, 7, 41, 7 tests, all OK |
| `python3 -m unittest discover -s os/tests -p test_ways_back_model.py -k ScopeTest` | 4 tests, OK |
| `python3 -B reviews/22c-ways-back-after-update/walk-host.py` (after every bound change) | `PASS package 22c host walks (reorder-probe): 255 sources; no VM started` |
| `python3 -B reviews/27-first-update-release/rebind.py pending "<note>"` (after it) | 34 bound files differ, 2 removed; after fix 4: **35**, 2 removed |
| after the status row (`5c7dbef6`): `test_owner_path`, `test_owner_equality`, `test_owner_entry`, `test_checkout_sources`, `test_ways_back_probe`; the host walk; `rebind.py pending` | 44, 10, 3, 5, 44 tests, OK; 255 sources; 35 bound files, 2 removed |

`test_owner_update` did not run locally, nor the full model. `git diff --check` passed before each commit.

Hosted, `gh workflow run "OS image" --ref pkg/22c-ways-back-after-update -f checks_only=true`, then one
`gh run watch <id> --exit-status --interval 60`; totals from each job log's own unittest summary:

| Hosted run | Head | Regressions job | Model job | Result |
|---|---|---|---|---|
| [43563857314](https://github.com/Ares-Empire/AresOS/actions/runs/43563857314) | `02f52057` (the four fixes) | cancelled after about 7 minutes | cancelled | I found the stale status row while it ran; the next head is a superset, and the branch's concurrency group would have queued a second run behind it. No result is claimed from it. |
| **[43564190565](https://github.com/Ares-Empire/AresOS/actions/runs/43564190565)** | **`5c7dbef6`** (the four fixes and the status row) | **17m49s: `Ran 1098 tests in 1018.549s` / `OK`: 0 failures, 0 errors, 0 skipped**; the slice 173,476 states / 3,043,109 edges (233.0 s) | **17m09s: scope `full` (31 dependency paths), 963,003 states / 25,257,042 edges, `Ran 1 test in 982.576s` / `OK`** | Watch exit 0. 1098 = step 2's 1092 + three new tests in `test_owner_path` and three in `test_ways_back_probe`. |

The log has no `... FAIL`, `... ERROR` or `... skipped` result line. Ledger afterwards (read-only, `rehearsal_guard.budget`
against the API): **22 checks runs, 1 probe, 558 of 1200 minutes** (this run 36, the cancelled one 10).

### JUDGMENT-CALL

1. **Previous where check shows the update in place, not only where the newer release runs.** The brief says "run
   previous only when check shows the newer release is running"; review 4 prescribes check after the menu boot,
   before previous, and verifying the running system against the intended destination. When the new AresOS does not
   start, the newer release can never run, and check shows **… is in place and has not started yet** with the AresOS
   from before the update (or plain Bazzite) running. I followed the review: previous there makes the AresOS from
   before the update the next start in every traced case, from stock too. A literal reading would leave the broken
   release as the next start with Help as the only way on. To change: that bullet becomes STOP → Help (one line and
   its test).
2. **Forward again guarded by the guide, not by the tools.** The condition (a finished update route) is one the owner
   can read from his record; no command shows the tools' release before update runs. Changing it later to a tool rule
   needs a rule change, its model and a review.
3. **The full-model requirement in the guard, not a model job for rehearsals** (see 4).

### PLAN-GAP / open questions

1. **A tool-side guard for the box would be firmer than its text.** Forward again from an AresOS that starts next
   stages whenever the tools' release is not installed; the guide now forbids that case, but the command itself would
   still do it. An integrator decision whether update should refuse to stage unless asked to (a rule change, so not
   done here).
2. The rollback no-op was outside the lines review 4 named; fixed with finding 3 as the same rule.
3. Stage 2 must dispatch a passing checks-only run on its rehearsal head before the rehearsal (fix 4).

### For the fix check (read in this order)

1. `docs/EMERGENCY.md` "Failed or bad update" against the first table; `docs/INSTALL.md` misbehaves box and check box.
2. `docs/INSTALL.md` last box and `docs/INSTALL-PROCEDURES.md` "Back to AresOS from stock" and "Rollback from running
   AresOS" against the second and third tables.
3. `os/tests/test_owner_path.py`: the four tests named above, and that each branch is read from the guide.
4. `os/ci/rehearsal_guard.py` `model_gate` and its call; `os/tests/test_ways_back_probe.py` `LedgerTest`'s three new tests.

Cleanup: the run logs under `/var/home/ares/pkg22c-work/` are removed; `.work/` is empty (no file over 500 MB); no
download was made; no builder-started test or watch process remains; no Gradle daemon was started. PR #46 stays
draft; nothing was merged or pushed to main.

## Review fixes 4

Builder: a Claude agent on Opus 5.5 (`briefs/22c-review-fixes-4.md`; review 5, gpt-6-astra high on `2312fa99`,
CHANGES-NEEDED: one blocking, one should-fix; it confirmed round 3's four fixes and the judgment call on previous).
Two fixes, one commit each, pushed after each: `f646fe03` (1), `953aa973` (2). **No rule of the owner tools changed**
(nothing under `os/owner-tools/` or `os/release/`; the bundle stays `ba4c2bb4…`); no CI file changed. No VM was
dispatched, nothing was merged or pushed to main, and no owner tool, start block, `rpm-ostree`, `bootc` or `ostree
admin` ran on the laptop. Tested head: **`953aa973`**; the closing commit changes this report only. The routes were
traced in `os/tests/ways_back_ledger.py` as in round 3, and every traced case is a test assertion.

### 1. (Blocking) Forward again never stages

**The case** (review 5, reproduced in the ledger): release 28's tools installed, its update's finish lost, so 27, 13
and plain Bazzite stay. Rollback to plain Bazzite, back with update: "Newest installed AresOS starts next" (27) and,
after the restart, **Update to … confirmed after the restart**, which round 3's condition took as "the last update
route finished". Later previous to 13. Round 3's box then ran update on 13, which runs and starts next: it staged 28,
and the restart keeps 28, 13 and plain Bazzite, so 27 is gone.

**What a line can tell.** Neither `check` nor `title` prints the tools' own release: rule 8 names each system by its
role and digest, never by release, and the tools' release appears only in update's own lines (staging, **Newest AresOS
starts next**, **newer still**). So no line tells, before update runs, whether the tools' release is installed. What
check does show is the fact that decides staging: `update` stages only on an AresOS that runs and starts next (on
plain Bazzite, or where `rows[0] is not booted`, it only reorders: `owner.py`, `update`).

**Changed** (`docs/INSTALL.md`, last box). The box now starts with `sudo /var/lib/ares/at check` and goes by its line
naming what runs:
- **plain Bazzite …**, or a line ending **this start was not the default**: run the update block;
- **older AresOS … runs and starts next** (forward again's first step): do **not** run update there; reboot, take the
  newer AresOS's row from the boot menu (the row this check's **Boot menu at the next start:** line names), then check
  again: the line is now **newer AresOS … runs; older AresOS … starts next; this start was not the default** (the
  integrator's two-step path; update there only reorders);
- **newer AresOS … runs and starts next**: forward already, nothing to do; anything else → Help.

The change bullet names both titles a change prints (**starts next, after the restart** from plain Bazzite or the
older AresOS, **runs and now starts next; no restart is waiting** from the newer one). Round 3's condition ("the last
update route you followed finished") is gone. The status row's calm test follows the box (previous, restart, the newer
AresOS from the boot menu, update, restart, …). And a slip of mine in round 3: "`PASS check` whose first line names"
is now "`PASS check` showing", since check prints its console and layout lines before the title's (asserted absent).

**Traced** (the 750 destination states of round 3; every idle state on plain Bazzite or with two releases; the box
followed from check, whether or not the tools' release is installed):

| check's running line | Box entries | What the box does | Result |
|---|---|---|---|
| plain Bazzite … | 224 | update block | never stages; the newest installed runs and starts next after the restart |
| … this start was not the default | 233 (+ 58 after the first step) | update block | never stages; same end; a change confirms |
| older AresOS … runs and starts next | 58 | first step: the newer AresOS's row, then the block | never stages; in 16 of these, update at once would have staged |
| newer AresOS … runs and starts next | 63 | nothing to do | — |
| anything else (… runs and now starts next; no restart is waiting, or one release) | 32 | Help | — |

Wherever update says **The release of these tools is newer still**, following it would stage (146 cases); the box
says not to. The connected regression replays review 5's sequence step by step: round 3's box stages 28 and the
restart leaves 28, 13 and plain Bazzite; this box ends with 27 running and starting next, **Update to … confirmed**,
nothing staged.

**Tests.** `test_forward_and_back_box_never_installs_a_release` is rewritten: it reads the box's three dispatch
bullets and follows them from check's running line, computed from the ledger state as rule 8 prints it (round 3's
version substituted "the tools' release is installed" for the guide's own condition, which review 5 rightly
criticised). New: `test_forward_again_after_a_failed_update_a_stock_return_and_previous_never_stages`. The update
route's order list changes on purpose for the box's dispatch.

### 2. (Should-fix) The failed-update card keeps the result of a check just run

**The case** (review 5): release 28's finish lost; the provisional title's `(ostree:1)` boots 13. The boot menu's
check (or the update route's check box) shows **Update to … was not applied** and archives the journal (rule 5); its
link leads to the card, whose own check then shows only **older AresOS … runs; newer AresOS … starts next; this start
was not the default**: none of the card's results, so no branch led back to 27.

**Changed.** The card: "check comes **first**, never previous before it. If you came here from a check you just ran
(the update route's check box or misbehaves box, or the boot menu), use that check's result: **was not applied** shows
only once, and a second check no longer shows it. Otherwise … `sudo /var/lib/ares/at check` now." A new last branch:
"Any other result, also a check with none of these lines: do **not** run previous; **STOP → go to Help**." The three
places that run check and link to the card say "with this/that check's result (it shows only once)": the update
route's check box (not-applied outcome), its misbehaves box, and the recovery menu. The card and the misbehaves box
now quote the line itself ("check shows …") instead of "the first line".

**Traced** (the linked entry: four staged starts, both ends of the shutdown, every row and no choice, 29 cases): each
of the 13 lost finishes shows "not applied" at the linked check, and a second check shows nothing the card names (the
card's last branch: Help, nothing changed); with the kept result the card ends on the AresOS from before the update
(a restart with no choice where another row runs). "In place, not started" (8) shows again at a second check;
"confirmed" (8) shows once, after which the card's later-day line applies. Review 5's sequence is asserted explicitly.

**Tests.** `test_failed_update_card_checks_first_then_previous_only_where_the_update_is_in_place`: expectations
changed on purpose (the entry sentence, the last branch, the linking places' wording, "first line" absent). New:
`test_failed_update_card_keeps_the_result_of_a_check_just_run`.

### Test expectations changed on purpose (B9)

| Test | Old expectation | New expectation | Finding |
|---|---|---|---|
| `test_update_route_orders_…` (the last box) | "**Forward again** only when the last update route you followed finished" | check first, then the three dispatch bullets in order (block; first step without update, the boot menu, the newer AresOS's row; forward already, anything else → Help) | 1 |
| `test_forward_and_back_box_never_installs_a_release` | the finished-route sentence; the ledger stand-in "tools' release installed" | the box's dispatch followed from check's running line in every entry | 1 |
| `test_a_return_that_changes_nothing_…` | "`PASS check` whose first line names that AresOS" | "`PASS check` showing that AresOS"; "whose first line" absent | 1 |
| `test_failed_update_card_checks_first_…` | "`sudo /var/lib/ares/at check` **first**, never previous before it"; "the first line" | the kept result of a check just run, otherwise check now; the "Any other result" branch; "with this/that check's result" in the three linking places | 2 |

No test was deleted or skipped; `test_owner_path` grows from 44 to 46 tests (the shared 750-state helper is now one
function, `destination_space`).

### Verified

Local, from the worktree, `TMPDIR=/var/home/ares/pkg22c-work`, `nice -n 10`, one module at a time:

| Command | Result |
|---|---|
| `python3 -B -m unittest discover -s os/tests -p test_owner_path.py` | after fix 1: 45 tests, OK; after fix 2: 46 tests, OK |
| `… -p test_owner_entry.py`, `test_owner_equality.py`, `test_checkout_sources.py`, `test_ways_back_probe.py` | after each fix: 3, 10, 5, 44 tests, OK |
| `python3 -B reviews/22c-ways-back-after-update/walk-host.py`, then `rebind.py pending "<note>"` (after each fix) | `PASS package 22c host walks (reorder-probe): 255 sources; no VM started`; 35 bound files differ, 2 removed |

`test_owner_update` and the full model did not run locally. `git diff --check` passed before each commit.

Hosted, `gh workflow run "OS image" --ref pkg/22c-ways-back-after-update -f checks_only=true`, then one
`gh run watch <id> --exit-status --interval 60`; totals from each job log's own unittest summary:

| Hosted run | Head | Regressions job | Model job | Result |
|---|---|---|---|---|
| **[43567101039](https://github.com/Ares-Empire/AresOS/actions/runs/43567101039)** | **`953aa973`** (both fixes) | **13m43s: `Ran 1100 tests in 766.638s` / `OK`: 0 failures, 0 errors, 0 skipped**; the slice 173,476 states / 3,043,109 edges (153.7 s) | **17m17s: scope `full` (31 dependency paths), 963,003 states / 25,257,042 edges, `Ran 1 test in 978.749s` / `OK`** | Watch exit 0. 1100 = round 3's 1098 + the two new tests in `test_owner_path`. |

The log has no `... FAIL`, `... ERROR` or `... skipped` result line. Ledger afterwards (read-only): **23 checks runs,
1 probe, 590 of 1200 minutes** (this run 32).

### JUDGMENT-CALL

1. **Every forward again takes the two-step path, gated on check's running line.** The integrator asked for the
   two-step path when the tools' release is not installed, and for the box to tell the case from check's or title's
   lines. No such line names the tools' release (rule 8), so the box tells apart the case that decides staging (does
   the running AresOS start next?) and uses the two-step path for forward again whether or not the tools' release is
   installed. Cost: when it is installed, one extra restart and a boot-menu choice that the one-step path did not need.
   A line naming the tools' release in `title` would allow the one-step path again: a tools change (rule 8), not done.

### PLAN-GAP / open questions

1. Stage 2's rehearsal (E) walks the box: it must take forward again's two steps (the newer AresOS's boot-menu row,
   then update), not update on the older AresOS.
2. Round 3's open question 1 (a tool-side guard against staging outside the stage box) stands; the box no longer
   depends on it.

### For the fix check (read in this order)

1. `docs/INSTALL.md` last box (its check-first dispatch) against the first table and review 5's sequence.
2. `docs/EMERGENCY.md` "Failed or bad update" (the entry sentence and the last branch); the three linking places.
3. `os/tests/test_owner_path.py`: `forward_box`, `running_line`, the two forward tests and
   `test_failed_update_card_keeps_the_result_of_a_check_just_run`.

Cleanup: the run logs under `/var/home/ares/pkg22c-work/` are removed; `.work/` is empty (no file over 500 MB); no
download was made; no builder-started test or watch process remains; no Gradle daemon was started. PR #46 stays
draft; nothing was merged or pushed to main.

## One word per meaning, step 1

Builder: a Claude agent on Fable 5.2 (`briefs/22c-forward-command.md`, step 1 of 2: the rule change in the owner
tools, its tests and the model). Three commits, pushed after each part: `03ec4613` (rules), `218fb15d` (tests),
`501e9229` (model, the 22c host walk and the waiting list). **Tested head: `501e9229`**; later commits change this
report only. Not in this step, on purpose (step 2): the payload copy under `os/owner-tools/payload/`, the fingerprint
pins and the guides. No VM was dispatched, nothing was merged or pushed to main, and no owner tool, start block,
`rpm-ostree`, `bootc`, `ostree admin` or `systemctl reboot` ran on the laptop. Tools version stays 3.

### The rules as built (`os/owner-tools/owner.py`)

`update` has one meaning: install the release of these tools by staging. `forward` (new) has one meaning: make the
newest installed AresOS the next start. With AresOS installed:

| State | `update` | `forward` |
|---|---|---|
| The tools' release is not installed, an AresOS runs and starts next, nothing staged or waiting | Stages it (rule 6, unchanged, also from the older AresOS beside a newer one, with A6's two lines) | The reorder, or nothing to do |
| The tools' release is not installed; plain Bazzite runs, or the running AresOS does not start next | STOP, nothing changed, names forward (line 2 below) | The reorder, or nothing to do |
| The tools' release is installed, runs and starts next | PASS, nothing to do: **… already starts next; nothing changed**, **It runs now** (the lines every word prints) | The same two lines |
| The tools' release is installed, in every other order or with another system running | STOP, nothing changed, names forward (line 1 below) | The reorder, or nothing to do |
| An update staged or a change waiting in this boot, a layout trial, a busy or modified system | The existing STOPs, unchanged (**… waits for the restart: restart first**, **Layout trial is unfinished**, …) | The same STOPs wherever it would have to change the order; nothing to do where its target already starts next |
| A layout repair note for the running AresOS | **… run … layout abandon first, then update again** (unchanged, no fallback) | The reorder (reorders stay available) |
| A staging interrupted in this boot | Continues it (unchanged) | STOP naming update (rule 5's exception, unchanged): it never continues a staging |
| No AresOS installed | **Update starts only from a running AresOS release; get help** (unchanged) | **No AresOS is installed yet: this command works after the first switch; nothing changed** |

`update` never calls the reorder. `forward` is `select('forward', …)` over rule 3's one reorder (`start_next`: the
identity-checked script, the journal before, the record after), so it needs no network, login or signature check
and never stages, downloads, removes or creates a deployment. It prints **Newest installed AresOS starts next
<reference>** and the title; the journal's sentence is **Forward to <reference> …** (`is not finished until the
restart`, `confirmed after the restart`, `is in place and has not started yet`, `was not applied`). The journal
gains the word `forward` (always mode `reorder`); `update` journals only mode `staging`. `login` on an AresOS refuses
where `update` would, with line 1, line 2 or line 3.

The wording is in one place, beside `typed()` (the one helper that spells a command; the commands.json test and
its "no hand-spelled command" count still hold):

| Name | Text |
|---|---|
| `FORWARD` | `sudo /var/lib/ares/at forward (it makes the newest installed AresOS the next start and says whether a restart is needed)` |
| 1. `RELEASE_INSTALLED` | `The release of these tools is installed already, so update has nothing to install: run ` + FORWARD + `; nothing changed` |
| 2. `FORWARD_FIRST` | `Update installs a new release only from a running AresOS that starts next: run ` + FORWARD + `, then run this command again; nothing changed` |
| 3. `RELEASE_RUNS` (login only) | `The release of these tools already runs and starts next: update has nothing to install and needs no login; nothing changed` |
| `BACK_TO_ARESOS` | `run sudo /var/lib/ares/at forward to go back to AresOS` |

Other lines that named update as the way back now name the right word: the stock updater warning in `check` and
`title` and keep-stock's refusal (**… Bazzite must not update while AresOS is installed: run … forward to go back to
AresOS, then get help**), `layout begin` on plain Bazzite (**… nothing changed; run … forward to go back to AresOS
first**), and `layout begin` on an AresOS that does not start next, which names the one word that selects that
system (**make it the next start first (… forward)** on the newest installed AresOS, **(… previous)** on the older
one; it said "update or previous"). The lines that name update for a staging stay (an interrupted staging, the repair
note, a stopped update). `commands.json` gains `forward`; the entry accepts it.

The three states stay apart for forward as for every reorder: from a system that is not its target the selection is
applied and a restart waits; on its target (started from the boot menu) it is applied and nothing waits, with no
confirmation; only a later boot that runs the target confirms. `test_forward_keeps_applied_waiting_and_confirmed_apart`
pins each, and the model keeps its eight journal outcomes.

### Moved tests (B9: expectations changed on purpose)

Every test that pinned `update` returning to an installed system, with the rule that replaces it (rows of the
brief's table: U = update's row, F = forward's row, L = login's sentence, W = "every message names the right word").

| Test | Old expectation | New expectation | Rule |
|---|---|---|---|
| `test_ways_back.DestinationTest.test_each_word_moves_only_its_target_to_the_front_from_every_order_and_system` | `update` moves the newest AresOS to the front, journal word `update` | `forward` does, journal word `forward` | F |
| `…DestinationTest.test_update_with_a_newer_bundle_reorders_where_it_may_not_stage_and_says_what_is_next` | update reorders to the newest installed AresOS and prints "newer still … update again" | replaced by `test_where_update_named_forward_forward_then_update_installs_the_release`: update refuses (line 2), forward selects and says nothing of an update, then update stages once that AresOS runs and starts next | U, F |
| `…DestinationTest.test_login_refuses_where_update_needs_no_download` | "update needs no login" | replaced by `test_login_refuses_where_update_would_refuse_or_has_nothing_to_install`: lines 1, 2 and 3 in five states | L |
| `…DestinationTest.test_outside_reorder_before_the_script_closes_the_intent_and_every_way_back_works` | the newest AresOS is one `update` away | one `forward` away | F |
| `…ShapeTest.test_stock_updaters_warn_in_title_stop_keep_stock_and_never_block_the_way_off` | the warning names update; update is the way off plain Bazzite | the warning and keep-stock's refusal name forward; forward is the way off, as a no-op and as a real reorder while the updaters are on | W, F |
| `…JournalTest.test_waits_for_the_restart_then_confirmed_by_a_later_boot_that_runs_the_target` | a second change by update refuses "restart first" | forward does; update refuses with line 1 | U, F |
| `…JournalTest.test_a_new_change_supersedes_an_in_place_record_and_update_works_at_once` | **Newest AresOS starts next**, **Update to … confirmed** | renamed `…_and_forward_works_at_once`: **Newest installed AresOS starts next**, **Forward to … confirmed** | F |
| `…JournalTest.test_every_cut_of_every_reorder_resolves_from_the_list_alone` | the fourth reorder is the reordering update | it is forward; the newest AresOS is one forward away after every cut | F |
| `…LayoutTest.test_begin_refuses_on_stock_when_not_default_and_with_a_change_waiting` | "German layout", "does not start next" | the same refusals with the word they name (forward on plain Bazzite; forward or previous by the running system), five cases | W |
| `test_owner_update.UpdateCommandTest.test_old_direction_refusals_now_select_the_destination_without_network` | update selects in five states, "newer still" where the bundle is newer | renamed `test_forward_selects_the_destination_without_network_where_update_only_names_it`: update refuses (line 1 or 2) or has nothing to do; forward selects, never mentions an update | U, F |
| `test_owner_update.LoginTest.test_login_on_aresos_needs_a_newer_target_and_otherwise_keeps_the_stock_rules` | "needs no login" | line 3 where the release runs and starts next; line 1 where it is installed elsewhere | L |
| `test_ways_back_model.ModelTest.test_new_bundle_stages_and_the_newer_installed_release_has_a_walked_menu_path` | update stages R28; R27 only through the boot menu, then update | renamed `…_and_forward_selects_the_newer_installed_release_in_one_command`: update stages R28, forward selects R27 (waiting, then confirmed after the restart) | U, F, B2 |
| `test_ways_back_model.ModelTest.test_reachable_state_space` | 963,003 states, 25,257,042 edges; slice 173,476 / 3,043,109 | 967,215 states, 26,519,328 edges; slice 173,130 / 3,185,862 | the new word |

Loops that list every list-reading word gained forward beside update, with no other change (`test_wrong_sets_keep_refusing`,
the rule 10 test, the first-switch test, `test_any_other_list_stops_and_an_unknown_schema_refuses`), and
`test_owner_entry` patches the new handler. No test was deleted or skipped. New: `test_update_never_selects_an_installed_system`,
`test_forward_selects_the_newest_installed_aresos_from_anywhere_and_never_stages`,
`test_forward_never_touches_a_staged_update_or_continues_an_interrupted_one`,
`test_from_the_older_aresos_with_a_newer_bundle_each_installed_system_is_one_command_away`,
`test_forward_keeps_applied_waiting_and_confirmed_apart` (`test_ways_back`: 47 to 52 tests) and three revert proofs
(`test_ways_back_reverts`: 17 to 20).

### Invariants and revert proofs

1. **B2's destination invariant, at its original strength.** `ways_back_ledger.destinations`: from every state with
   nothing staged or waiting and no active layout trial, each installed system that does not start next is made
   the next start by **one** command (forward the newest installed AresOS, previous the older one, rollback or
   keep-stock plain Bazzite). The boot-menu exception of `briefs/22c-b2-destination-invariant.md` and its walked
   path are gone; the model prints no menu-only states any more. In that brief's state, `[R13*, R27, S]` with a
   bundle for R28, update still stages R28 and forward selects R27.
2. **update never selects an installed system.** In the ledger over every phase of update (full and each cut): the
   installed rows keep their order, the only row it may add is the bundle's release staged in front, and it never
   journals a reorder. In the driver, on every executed edge, by the fake's state before and after and before
   anything is compared with the ledger: no `set-default`, and the rows that are not staged are exactly as before.
   Direct: `test_update_never_selects_an_installed_system` (the pair and the triple in every order with every running
   system, the tools' release installed and not: 44 states; 5 stage, 3 have nothing to do, 36 name forward).
3. **forward never stages and never changes the set of deployments.** In the ledger: the same rows, the same stage,
   and where the order changes only the newest installed AresOS moves, to the front. In the driver, by the fake's
   state: the same rows with the same flags and pins, and no change but `set-default` and `sync`. Direct:
   `test_forward_selects_…_and_never_stages` (88 states, with no login and no signature available).
4. **A refusal that names forward is right.** In every resting state where update names forward, forward does not
   refuse and ends with the newest installed AresOS first. And where staging is allowed, update stages the bundle and
   announces the other release (A6), or refuses with the repair note.

| Rule taken out | Assertion that fails |
|---|---|
| update's reorder put back where the tools' release is installed (`raise Stop(RELEASE_INSTALLED)` becomes the old `select`) | `test_one_word_update_never_selects_an_installed_system`: the driver's `update selected an installed system` (`[R13*, R27, S]`, bundle R27), and `test_update_never_selects_an_installed_system` |
| update's reorder put back where it may not stage (plain Bazzite runs, or the running AresOS is not first) | the same test: the driver's `update selected an installed system` (`[S*, R27, R13]`, bundle R28), and the direct test |
| forward stages where the bundle's release is not installed (the old update under the new word) | `test_one_word_forward_never_stages_or_changes_the_set_of_deployments`: the driver's `forward staged or changed the set of deployments` (`[R27*, R13, S]`, bundle R28) |
| forward removes a deployment (`cleanup --pending` after its reorder) | the same test: the same driver assertion (`[R13*, R27, S]`), and `test_forward_selects_…_and_never_stages` |
| forward narrowed to update's old condition (no reorder from a running AresOS that starts next) | `test_one_word_each_installed_system_is_one_command_away`: the driver's `accept/refuse` in `[R13*, R27, S]` with a bundle for R28, and the same narrowing in the ledger fails `destination refuses` in `invariants` |

An unrelated exception is not accepted as a proof (`detected_by` requires failures and no errors).

### The model's size and time

The reduced space grows from 963,003 to **967,215 states** and from 25,257,042 to **26,519,328 edges**: forward
adds one command with its three cuts to every state, and its reorder from a running AresOS that starts next reaches
orders with a waiting journal that update's staging never left. All eight journal outcomes are visited. The slice
(the first 120,000 states): **173,130 states, 3,185,862 edges**. Both are pinned in `test_reachable_state_space`.
A ledger-only sizing run (the same breadth-first order, the ledger's invariants on every state, no tools) gave the
pins first: 322 s. The slice against the tools: 143 s locally. The full model against the tools, run once locally:
**967,215 states, 26,519,328 edges, 820,691 executions, 25,698,637 reuses, 926.2 s, queue exhausted** (the module:
25 tests in 944.2 s, OK). Journal outcomes (reduced states): none 217,560; not-applied 279,204; retry 333; complete
333; waiting 91,581; selection applied 150,528; target boot confirmed 91,956; in place, not yet started 135,720.
Command edges for the two words: update 160,260 PASS, 806,955 STOP, 151,827 cuts; forward 745,584 PASS, 221,631 STOP,
1,198,419 cuts.

### Verified

Local, from the worktree, `TMPDIR=/var/home/ares/pkg22c-work`, `nice -n 10`, one module at a time, Python 3.14,
with 6,500 MB or more available:

| Command | Result |
|---|---|
| `python3 -B -m unittest discover -s os/tests -p test_ways_back.py` | 52 tests in 27.7 s, OK |
| `python3 -B -m unittest test_ways_back_reverts` (from `os/tests`) | 20 tests in 6.7 s, OK |
| `ARESOS_MODEL_SCOPE=slice python3 -B -u -m unittest test_ways_back_model.ModelTest.test_reachable_state_space` | 1 test in 143.3 s, OK (173,130 states, 3,185,862 edges) |
| `python3 -B -u -m unittest test_ways_back_model` (the full module, once) | 25 tests in 944.2 s, OK (the numbers above) |
| `… -p test_ways_back_compatibility.py`, `test_ways_back_probe.py`, `test_checkout_sources.py`, `test_owner_step_limits.py`, `test_owner_abandon.py`, `test_owner_tools.py` | 21, 44, 5, 4, 6, 13 tests, OK |
| `… -p test_owner_bootstrap.py`, `test_owner_equality.py`, `test_owner_walk.py`, `test_owner_entry.py`, `test_owner_path.py` | 8, 10, 27, 3, 46 tests; 1, 6, 1 (two subtests), 1, 5 failures: step 2's, each named below |
| `… -p test_owner_retained.py`, `test_owner_commands.py` | 1 and 5 errors, local only, as in stage 1b (a mocked `glob` gets Python 3.14's `case_sensitive` argument); neither was changed |
| `python3 -B reviews/22c-ways-back-after-update/walk-host.py`, then `rebind.py pending "<note>"` | `PASS package 22c host walks (reorder-probe): 255 sources; no VM started`; `pending: 36 bound files differ from the active bindings, 2 removed` |

`test_owner_update` did not run locally (hosted only). `git diff --check` passed before the commits; the push went
through the privacy check. A first start of the full module was ended after about 20 seconds (its 12 quick tests
had passed; the exploration had printed no progress line yet) to restart it detached from the agent tool's time
limit; the run above is the only one that completed.

Hosted: `gh workflow run "OS image" --ref pkg/22c-ways-back-after-update -f checks_only=true`, then
`gh run watch 43570946876 --exit-status --interval 60`. The first watch lost its connection after about ten minutes
(a dropped read, not HTTP 403); one second watch with the same options followed the run to its end (exit 1, the
regressions job).

| Hosted run | Head | Regressions job | Model job |
|---|---|---|---|
| **[43570946876](https://github.com/Ares-Empire/AresOS/actions/runs/43570946876)** | **`501e9229`** | **17m23s: 1108 tests: 1093 ok, 15 failed, 0 errors, 0 skipped**; the slice 173,130 states / 3,185,862 edges (244.8 s) | **18m1s: scope `full`, 967,215 states / 26,519,328 edges, 820,691 executions, `Ran 1 test in 1038.456s` / `OK`** |

As in stage 1b, the regressions log has no unittest summary line (a failing guide test prints all of `owner.py` and
the hosted log ends inside it). The counts come from the verbose result lines: 1,093 ok (1,084 `... ok`, 9 `ok`
after printed output), 16 `... FAIL` lines for 15 tests (one test fails in its two subtests), no `... ERROR`, no
skipped. 1108 is run 43567101039's 1100 plus this step's eight new tests. Every test of `test_owner_update`
(the moved tests among them), `test_ways_back`, `test_ways_back_model`, `test_ways_back_reverts` and
`test_ways_back_compatibility` passed. By this report's count it is the branch's 24th checks run (cap 30) and costs
about 36 runner minutes, so about 626 of the 1200; I did not read the ledger from the API again.

**All 15 failures are step 2's.** Seven wait for the bundle refresh: `bundle.check` finds the payload copy older
than `owner.py` ("Regenerate the reviewed payload").

| Test | Reason |
|---|---|
| `test_owner_bootstrap.BootstrapTest.test_documented_command_is_generated_from_complete_system_manifest` | payload copy, fingerprint pin |
| `test_owner_equality.EqualityTest.test_a_quoted_folder_block_is_byte_equal_to_the_generated_one` | payload copy, fingerprint pin |
| `test_owner_equality.EqualityTest.test_bootstrap_is_byte_equal_to_the_block_exercised_by_package_14_tamper_tests` | payload copy, fingerprint pin |
| `test_owner_equality.EqualityTest.test_every_owner_command_equals_the_command_physically_typed_by_ci` | payload copy first; then forward must be in the guides and under `unwalked_commands` (PLAN-GAP 2) |
| `test_owner_equality.EqualityTest.test_extra_stale_fingerprint_is_rejected_in_every_owner_page` | payload copy, fingerprint pin |
| `test_owner_equality.EqualityTest.test_reviewed_windows_payload_is_exact_generated_ci_payload` | payload copy, fingerprint pin |
| `test_owner_walk.OwnerWalkTest.test_update_route_walks_the_laptop_tools_update_password_and_previous` (ps2 false and true) | payload copy (the walk's stick takes the checked bundle) |

Eight bind the guides, which still say update where forward is the word and do not have forward yet:

| Test | Reason |
|---|---|
| `test_owner_entry.EntryTest.test_every_real_entry_pass_line_equals_the_guide` | `PASS forward` is in no guide |
| `test_owner_equality.EqualityTest.test_every_documented_owner_pass_equals_captured_entry_stdout` | `PASS forward` is in no guide |
| `test_owner_session.SessionTest.test_harness_sudo_i_then_exact_commands_matches_the_guide` | every command of `commands.json` must be in the guides; `sudo /var/lib/ares/at forward` is in none (not run locally; read from the test) |
| `test_owner_path.OwnerPathTest.test_update_route_orders_windows_tools_update_title_reboot_check_with_pass_stop_and_returns` | quotes `'Newest AresOS starts next '` from `owner.py` (the last box) |
| `test_owner_path.OwnerPathTest.test_forward_and_back_box_never_installs_a_release` | quotes `'The release of these tools is newer still and is not installed ('`; the box's update dispatch |
| `test_owner_path.OwnerPathTest.test_forward_again_after_a_failed_update_a_stock_return_and_previous_never_stages` | follows the box with update from plain Bazzite: the ledger now refuses there (`at forward`) |
| `test_owner_path.OwnerPathTest.test_a_return_that_changes_nothing_completes_without_a_confirmation` | counts returns by update that are confirmed: there are none any more (they are forward's) |
| `test_owner_path.OwnerPathTest.test_stock_procedures_go_back_to_aresos_and_never_update_bazzite` | quotes `'. Bazzite must not update while AresOS is installed: run '` and the guide's "update back to AresOS" |

### JUDGMENT-CALL

1. **Where the tools' release already runs and starts next, update passes with the lines every word prints**
   (**… already starts next; nothing changed**, **It runs now**), as before. The brief calls this state "nothing to
   do" in a sentence about refusals. Rejected: a STOP, which would print the general "do not reboot … get help"
   trailer for a harmless state and change two lines the guides already handle. Changing it later is one line and
   the tests that pin it.
2. **Update names forward wherever the newest installed AresOS is not the system that runs and starts next**, also
   when the newest AresOS runs but does not start next (a start from the boot menu, for example `[S, R27*, R13]`).
   Read word for word, the brief names forward only "when a newer installed AresOS exists or stock runs" and sends
   everything else to Help. There forward is exactly the right word (it makes the running system the next start, and
   nothing waits), and Help would be a step back from today. "Help otherwise" stays for the existing STOPs (a staged
   row, a modified system, an unknown list).
3. **Forward says nothing about a newer release of the tools.** Update's old line "The release of these tools is
   newer still …: … update again" is gone, not moved: it was the line that reviews 4 and 5 found followed into a
   staging without its announcement. An owner who wants the update types update, and its refusal (line 2) gives the
   sequence. Adding a hint later is one line.
4. **Update's refusal with a newer bundle names only forward**, also on the older AresOS that runs but does not
   start next (`[R27, R13*, S]` with R28's tools). Forward leads to the newer installed AresOS; an owner who wants to
   update from the older one (owner decision 5) runs previous there, which applies at once, then update. From the
   older AresOS that starts next, update stages as before.
5. **One change line for forward**, **Newest installed AresOS starts next <reference>**, whether or not the tools'
   release is installed (update had two), and the journal's sentence **Forward to <reference> …**.

### PLAN-GAP / open questions

1. `login` on plain Bazzite beside an installed AresOS keeps the first-install path's refusal (**Stock list/pin/
   pending/BLS changed before switch**). It refuses, as the brief asks, but names no next step. Not changed here (it
   is the first switch's check); `test_login_refuses_where_update_would_refuse_or_has_nothing_to_install` pins it,
   so a later change is deliberate. No guide sends him to login on plain Bazzite.
2. `forward` is typed by no walk yet. `test_every_owner_command_equals_the_command_physically_typed_by_ci` wants
   every command in `commands.json` in the guides and either typed by a walk or listed under `unwalked_commands` in
   `os/manifest/ci/16/pending-rebind.json`. Until stage 2's rehearsal types forward, step 2 lists it there (and
   rewords `unwalked_rule`, which says none is waiting).
3. Package 27's rehearsal code (`os/ci/owner_vm.py`, `previous-13-update-refused`) expects version 2's text and is
   untouched. With these rules update after previous refuses again there, with line 1.

### For step 2

**Tool lines that are gone** (the guides and `test_owner_path` still quote them):

- **Newest AresOS starts next <reference>** (update's reorder).
- **The release of these tools is newer still and is not installed (<reference>): run / restart, then run … update
  again**.
- **The release of these tools is installed already: … update needs no login**.
- **Update stages only from a running AresOS that starts next; get help**.
- **… run … update to go back to AresOS, then get help** (the warning in check and title, keep-stock's STOP), **… run
  … update to go back to AresOS first** (layout begin on plain Bazzite), **(… update or … previous)** (layout begin).
- **Update to <reference> …** after a return to an installed system: update's journal sentence now follows only a
  staging.

**Tool lines that are new or moved** (quote these):

- The command `sudo /var/lib/ares/at forward` and `PASS forward`.
- **Newest installed AresOS starts next <reference>**: forward's one change line.
- **Forward to <reference> is not finished until the restart**, **… confirmed after the restart**, **… is in place
  and has not started yet**, **… was not applied: the deployments are as before it, and nothing is waiting**; the
  STOP **The forward to <reference> waits for the restart: restart first (…)**.
- **… already starts next; nothing changed** with **It runs now** or **It does not run yet: it starts at the next
  restart**: unchanged text. Forward prints it; update prints it only where the tools' release runs and starts next
  (then always **It runs now**).
- Update's STOPs, lines 1 and 2 of the wording table, and login's line 3; the warning and the two layout lines with
  forward (the wording table and the paragraph under it).

**Where the guides quote the old lines today:** `docs/INSTALL.md` 323 to 336 (the last box, "Forward again, or back
from plain Bazzite": its check-first dispatch, the boot-menu two-step path, the bullets **Newest AresOS starts
next** and **newer still**); `docs/INSTALL-PROCEDURES.md` 168 to 170 (back from plain Bazzite with update; the
updater warning) and 178 ("go forward again with update"); `docs/INSTALL-STATUS.md` row 27; `docs/EMERGENCY.md`
"Failed or bad update", whose **Update to …** lines now come only from a staging: a return prints **Forward to …**,
so **Update to … confirmed after the restart** can no longer be a return's confirmation (review 5's case). With
forward the box needs no dispatch on check's running line: forward is right from every state the box is entered in
(the model's destination invariant).

**Bundle, pins, waiting list:** the payload copy (`os/owner-tools/payload/owner.py`) is the old `owner.py`, so every
test that calls `bundle.check` fails with "Regenerate the reviewed payload" (named below); the install fingerprint in
`commands.json` and the guides changes with the refresh; then the 22c host walk and `rebind.py pending` again, and
PLAN-GAP 2's `unwalked_commands`.

**Guide tests that fail until the guides change** (named below with their reasons): five in `test_owner_path`, and
the documented-PASS test in `test_owner_entry` and `test_owner_equality`. Their source-literal pins need the new
literals: `'Newest installed AresOS starts next '` stays in `owner.py`; `'Newest AresOS starts next '`, `'The release
of these tools is newer still and is not installed ('` and `'. Bazzite must not update while AresOS is installed: run
'` are gone (the last is now `'. Bazzite must not update while AresOS is installed: '` + `BACK_TO_ARESOS`).
`test_owner_path` traces the guides through `ways_back_ledger.transition`: a return is `('forward', 'full')` now,
update's refusal has `stop == 'at forward'`, and `destinations(s)` replaces `destination_paths(s)`.

Cleanup: the logs and helper scripts under `/var/home/ares/pkg22c-work/` are removed with the folder; `.work/` holds
no file over 500 MB; no download was made; no builder-started test or watch process remains; no Gradle daemon was
started. PR #46 stays draft; nothing was merged or pushed to main.
