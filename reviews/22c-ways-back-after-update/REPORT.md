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
  Generated payload fingerprint: `d2b40b50e091b377bc8d9258a35643065202525f27053599f16dbeef08dcb679`.
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
| `python3 os/owner-tools/bundle.py --refresh` | `PASS bundle manifest SHA256 d2b40b50e091b377bc8d9258a35643065202525f27053599f16dbeef08dcb679`. |
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

Builder: Codex GPT-6.1-sol, xhigh. Scope: the three findings in REVIEW-1 only;
stage 1b, the harness and VM rehearsal remain deferred. This section is updated
and pushed with each finding so work can continue from a checkpoint.

### Finding 1 — interrupted layout restoration

**Done:** `layout abandon` saves `restoring` (the exact persistent pair before
restoration) into the pending trial or repair note before either persistent
write. A retry accepts only that pair, its console-first restoration intermediate,
and the old finished pair. Initial restoration still accepts only old settings,
the authorized forward partial finish, or the authorized new settings. A reverse
partial pair without restoration intent still refuses. Abandoning on another
deployment carries that intent into its repair note without writing another
system's settings; retries do not duplicate that note. `check` also names
fresh-login abandon when a repair note owns a loaded/persistent console mismatch.
Existing schemas stay unchanged; `restoring` is an additive field.

**Tests:** `LayoutTest.test_every_restoration_cut_resumes_only_its_own_settings`
covers all six directed profile pairs, both interrupted-finish write points,
pending trials and repair notes, and restoration intent/console/X11 cuts (72
cases). It checks durable intent, exact restoration, untouched other settings,
cleared records and an immediately usable destination command.
`test_reverse_partial_without_a_restoration_intent_is_not_authorized` preserves
the refusal boundary. The independent ledger now models abandon intent, console
and persistent cuts; the driver reconstructs and checks restoration intent, and
the execution memo observes it as an input. Closure counts will be updated for
this expanded event set, not treated as coverage of unencoded interruptions.

**Revert proof:**
`RevertTest.test_rejecting_reverse_partial_restoration_fails_pending_and_note_regressions`
removes restoration-intermediate acceptance in memory. The same pending and
repair-note sequences then fail the driver's `accept/refuse` assertion. The
positive regression also covers moving an interrupted restoration onto stock,
transferring its intent to a repair note, returning and repairing.

**Verified so far:** after a `free -m` gate of 10330 MB available,
`cd os/tests && TMPDIR=/var/home/ares/pkg22c-work nice -n 10 python3 -B -m unittest test_ways_back`
printed `Ran 36 tests in 21.160s` / `OK`. Initial model runs caught missing adapter
encoding for the new field and a missing abandon next step from `check` during
repair-note restoration; both were fixed. Full model verification is in progress.

**Not verified:** physical typing, real shutdown durability, VM and laptop
operations remain outside this round. No Gradle or mod command is applicable.
No new JUDGMENT-CALL or rule change. No review finding is rejected.

### Finding 2 — bind the script read to the journalled list

**Done:** the caller passes its entire pre-change deployment list as hex-encoded
JSON (`BEFORE`), so it cannot introduce quoting or script substitutions. The
script compares its fresh read with that snapshot before target lookup and
`set-default`. A mismatch reports an outside change and performs no mutation.
Target identity/origin/stage checks, exact postcondition and `sync` remain.
The accepted race after the final read and before the primitive remains.

**Tests and revert proof:**
`ScriptTest.test_fresh_read_must_equal_the_callers_snapshot_before_any_mutation`
checks order, pin, identity, running row and deployment metadata drift, with
exactly one read and no primitive. The owner-level
`DestinationTest.test_outside_reorder_between_intent_and_script_does_not_add_an_owner_mutation`
injects `[R13, R27*, S]` after rollback has journalled `[R27*, R13, S]`; it
requires unchanged outside state, an open intent and zero owner changes.
`ScriptTest.test_removing_snapshot_guard_fails_the_outside_writer_regression`
removes only the fresh snapshot assertion in memory; that same regression must
fail because it observes `ostree admin set-default 2` instead of no owner change.
Local execution of these new tests is pending completion of the one-at-a-time
model run; no test result is claimed at this checkpoint.

The payload was refreshed without changing stage-1b inventory or fingerprint
pins. The host walk and pending bindings were refreshed in that order. No new
JUDGMENT-CALL, PLAN-GAP or changed brief rule.

### Finding 3 — survey every installed-list entry point

**Done:** `survey_installed` sends an installed lifecycle through the existing
`qualified`/journal resolution before install-only command checks. It runs at
the start of `prepare`, before `before_switch`'s refusals (thus verify and
switch), and before login chooses its stock/AresOS branch. With no installed
AresOS, the prepared and first-switch checks stay in charge. The audit found
prepare had the same gap; its disk/setup checks now follow the installed survey.

**Tests and revert proof:**
`JournalTest.test_install_commands_resolve_the_installed_journal_before_their_own_refusals`
cuts rollback before/after its primitive, starts stock, then tries each of login,
verify, switch and prepare separately. It requires the recorded/not-applied
outcome before each own refusal and zero further deployment mutations.
The existing every-command A10 test now includes those four, check and layout
begin. `ShapeTest.test_install_survey_leaves_prepared_and_first_switch_checks_in_charge`
checks the pre-install boundary, including foreign staging and the unchanged
before-switch refusal. The fake disk record now supplies its full structural
shape, so prepare's own refusal is exercised rather than a fixture KeyError.
`JournalTest.test_removing_install_survey_fails_resolution_and_danger_warning_regressions`
removes the gate in memory and requires both guarding tests to fail assertions,
with no unrelated exception accepted. Local execution and hosted totals follow
below after the current full-model process completes.

No brief rule changed. The review's three findings stand; the extra `check`
next-step case belongs to interrupted restoration, and prepare was explicitly
part of the requested audit. All three fixes have separate pushed commits;
final verification and any follow-up corrections will be recorded below.

### Verification continuation and model cost

The first final-focused attempt ran 42 tests in 24.763s with one fixture failure:
the new prepared-state boundary test reached an unmodelled account read. Its
account boundary is now explicitly replaced; no production account check changed.
The next run (10329 MB available at its start) printed `Ran 42 tests in 24.221s`
/ `OK`, including both finding-2 and finding-3 executable revert proofs.

The initial unrestricted restoration-history exploration was stopped explicitly
with SIGINT on its own Python PID (not another builder's process). It had not
closed and is not passing evidence. It exposed an avoidable multiplication of
historical restoration snapshots. The model now quotients that provenance:
for a reachable persistent pair, an existing restoration intent and a newly
published one have identical future actions. Restoration republishes the same
intent on every retry before writes, so both have an intent cut, console cut,
X11 cut and the same eventual old setting. Reverse partial settings remain
reachable only with durable intent. No setting, deployment, trial ownership or
journal outcome is merged. Full literal intent records remain in each
representative and are checked against actual Tools execution. Memoized
executions still depend on the actual intent value, never oracle predictions.
`steps()` also supplies the once-computed candidate transition to the exploration
instead of calculating every interruption twice; no event was removed.

`EquivalenceTest.test_saved_restoration_intent_has_identical_future_commands`
checks every successor and actual command for pending trials and repair notes,
all six directed profile pairs, and old/forward-partial/new settings, with and
without already-saved intent (48 pairs). The additional
`RevertTest.test_restoration_intent_must_be_saved_before_either_write` removes
the save in memory for both owners: the pre-write assertion then fails with
`restoration intent missing before write`. The existing reverse-partial
acceptance mutant continues to fail the driver's `accept/refuse` assertion.
The targeted local command was
`cd os/tests && TMPDIR=/var/home/ares/pkg22c-work nice -n 10 python3 -B -m unittest test_ways_back_model.EquivalenceTest test_ways_back_model.RevertTest`:
**11 tests in 1.131s, OK**, after a 10646 MB available gate.

Reference-only queue exhaustion is used to generate the new exact state/edge
pins, then the full model is run against actual Tools. Generating those pins
is not Tools verification. The final local/hosted totals follow below.

The reference-only catalogue exhausted **879291 states / 23108154 edges** in
237.974s; those exact counts replace the old pins for the expanded event set.
The catalogue imports only the independent ledger and is not reported as a
passing test. Invariant checks now reuse the same per-state reference
predictions used for command comparisons; every invariant and event is retained.
The full actual-Tools model must reach those exact pins with its queue empty.

Final-source focused verification (7303 MB available at start):
`cd os/tests && TMPDIR=/var/home/ares/pkg22c-work nice -n 10 python3 -B -m unittest test_ways_back`
printed **`Ran 42 tests in 22.456s` / `OK`**. Full model and hosted verification
are the remaining checkpoint work.

Hosted checks-only run dispatched on implementation
`05fb2a927dc9bc5776b92733c6ac246022c87dad`:
[43530837211](https://github.com/Ares-Empire/AresOS/actions/runs/43530837211).
Command: `gh workflow run "OS image" --ref pkg/22c-ways-back-after-update -f checks_only=true`,
then exactly one blocking `gh run watch 43530837211 --exit-status` (in progress).
The final local full model command is
`cd os/tests && TMPDIR=/var/home/ares/pkg22c-work nice -n 10 python3 -B -m unittest test_ways_back_model`,
started with **6990 MB available**; its result is still pending. The report-only
checkpoint does not change the implementation being tested.

**Final local full model:** `Ran 19 tests in 1188.656s` / **`OK`**.
It exhausted exactly **879291 states / 23108154 edges**, with **1385183 actual
executions / 21722971 reuses**, in 1184.688s. The added abandon events include
**1077696 interruption edges**. All eight journal outcomes remain separate;
counts and the test receipt are in
[runs/checks-43530837211.json](runs/checks-43530837211.json).
The two menu-only destination cases are unchanged. This full run includes the
new intent-save and reverse-partial acceptance revert proofs and the execution
of every successor in the restoration equivalence test. No module was skipped
or weakened. The hosted run remains in progress at this checkpoint.

### Hosted time limit and execution reuse

Run **43530837211** reached the regression job's unchanged **25-minute limit**
and was cancelled. Its single `gh run watch ... --exit-status` returned 1.
It stopped during the expanded model at 680000 processed states (881.803s in
that model); **there are no full suite totals, so this run is not acceptance**.
The previously recorded local 19-test full model remains passing evidence.

**PLAN-GAP (verification cost, no rule change):** the extra cut events exceeded
the hosted time budget when the execution trie keyed every literal restoration
snapshot. The existing equivalence proof already establishes the relevant
reachable histories have identical future behavior. The trie now reuses those
actual executions while framing exact restoration intent values through, like
unrelated `/etc` values. It preserves a retry's original snapshot, adds an
intent only when absent, and clears it whenever its trial/note is removed,
including when the first execution had no intent to clear. It still compares
the full literal ledger against the independently predicted result on every
cache hit; no state, edge, assertion, cut or test is removed. The harness,
workflow budget and owner implementation are unchanged by this optimization.

`EquivalenceTest.test_execution_reuse_frames_exact_restoration_intents` compares
cached and uncached execution for both sides of all 48 equivalence pairs and
all their events, including an unrelated live repair intent. The targeted
local equivalence class passed **5 tests in 1.816s**, after a 10570 MB gate.
The full 20-test model and another hosted checks-only run follow. The new test
adds one to the expected suite count; the state/edge pins remain unchanged.
