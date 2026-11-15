# 22c council: architecture

Member: Architecture (Claude, Opus). Reviewed independently on 2026-11-13; I have not read the other members' answers.

Read: `QUESTION.md`, `BRIEF-DRAFT.md` (all of it), `os/owner-tools/owner.py` (`agree`, `preflight_prepare`, `preflight_recovery`, `qualified_state`, `Tools.outcome/intend/completion/finish`, `title`, `before_update`, `update`, `reconcile_update`, `previous`, `recover`, `layout`, `settle_tools`, `update_tools`, `main`), `os/release/{rollback,default-stock,previous,update}.sh`, `os/owner-tools/bundle.py`, `os/tests/test_owner_update.py` (model helpers, `Machine`, shape tests, outcome and intent tests, the refusal invariant), `os/tests/test_default_stock.py`, `os/tests/test_shell_assertions.py` (the payload comparison), `docs/INSTALL-PROCEDURES.md` (recovery menu, rollback, keep stock), `docs/EMERGENCY.md` (failed update), `reviews/22-update-route/REPORT.md` (judgment calls 1 and 4), the planner material, and package 23's `briefs/23-review-fixes-5.md` and `REVIEW-5.md` finding 4 (in its worktree) for the model failure the question refers to.

Upstream sources read (not run):
- ostree 2026.4 `ot-admin-builtin-set-default.c` (planner material): remove the index, insert it at 0, `ostree_sysroot_write_deployments`, then `ostree_sysroot_cleanup`.
- ostree 2026.4 `ostree-sysroot-deploy.c` retained in `os/manifest/ci/13/zero-cost/`: finalize at shutdown (`_ostree_sysroot_finalize_impl_staged_deployment`, lines 4062-4160) calls `ostree_sysroot_simple_write_deployment` with `NO_CLEAN`; `ostree_sysroot_write_deployments_with_options` (2822-2990) silently deletes a staged deployment that is not first in the new list; the bootloader switch is a rename of `/boot/loader` after a full sync (2210-2228, 2454).
- ostree `ostree-sysroot.c` retained in `os/manifest/ci/13/13e-zero-cost/` (2105-2185): `simple_write_deployment` keeps the new deployment first, then, in their old order, every pinned, other-stateroot, booted and merge deployment.
- bootc 1.16.13 `status.rs` (planner material, 342-365): rollback slot = first non-staged, non-booted deployment of the booted stateroot; `rollbackQueued` = that slot's index is lower than the booted one's.
- bootc 1.16.13 `deploy.rs` retained in `os/manifest/ci/13/zero-cost/`: `rollback` (1172-1232) writes `[rollback slot, booted]` or, when reverting, `[booted, rollback slot]`, followed by the others; staging takes ostree's merge deployment for the stateroot (985-1002), which `ostree_sysroot_get_merge_deployment` (`ostree-sysroot.c` 1821-1840) resolves to the booted deployment.

## Verdict on the structure

The direction is right. One accepted set with free order, one reorder primitive resolved by identity, and destinations instead of per-case moves is the structure that stops the tools producing states they refuse; option A would be the third patch on the same seam. `ostree admin set-default` is the right single primitive. `bootc rollback` only swaps the booted deployment with bootc's rollback slot (the first other deployment), so with three deployments it can never put the third row first. It also ends in the same `write_deployments` call (source: bootc `deploy.rs` 1172-1232 and `status.rs` 361-365). Neither path writes an origin file, and the pin lives in the origin file: ostree writes origins only at deploy.c 1038, 3554 and 3858, all outside `write_deployments`, 2386-3044. That the pin is stored in the origin is from memory. Dropping `bootc rollback` from the tools loses nothing. The split (preflight and journal in `owner.py`, one small re-checking script in the bundle, the old scripts kept byte-identical for older CI modes) is sound.

The gaps are in how the draft defines confirmation once a boot-menu start is a normal state, in what its model is allowed to skip, and in the order of the evidence. Eleven findings: 2 high, 4 medium, 5 low.

## High

### 1. The brief contradicts itself on a boot-menu start after a recorded change, and rule 2 leaves out the case that causes it

- **Gap.** Rule 2 has two cases (this boot's record, or no record); a third exists (a record from an earlier boot, not yet confirmed). B2 requires `check` and `title` to accept every reachable state, with a boot-menu choice from every state. B4 and rule 5 require a STOP when "a restart lands elsewhere". Both cannot hold, and the builder has to pick one without saying so.
- **Where it breaks.** Laptop list `[R27*, R13, S]`. `at rollback` makes the order `[S, R27*, R13]` and records `booted = S`. `at reboot`, F12, GRUB: the owner picks the R27 row (the three rows differ only in `(ostree:N)`, and the new guide text tells him a wrong choice is harmless). Now `[S, R27*, R13]` in a new boot. `Tools.outcome` (`owner.py:1161-1166`, kept by rule 5): the list equals `expected`, but `booted` does not, so it STOPs with "did not finish at the restart (another deployment runs); do not repeat it; export records and get help". `check`, `title`, `records` and `reboot` STOP, and so does every reorder command (rule 3: no unresolved record). The only way out is a restart with no choice, and no message says so. The same happens after `update` staging if he picks the old row at the first restart: finalize has run, the list is `[R28, R27, S]`, and `completion()` requires `booted == new` (`owner.py:1191-1194`).
- **Impact.** Either the model leaves the record out of its state (then B2 proves nothing about rule 5), or the builder makes `outcome` accept any booted row (then a boot loader that ignores the order looks exactly like a menu choice, and the tools claim "stock starts next" on every start without ever seeing it). The guides' new "a wrong choice is harmless" is false either way. Rule 5 also names two different confirmers ("`title` confirms" and "the first check after the next start"), and does not say whether a `keep-stock` record on the booted stock, where nothing waits, counts as "a change waiting" for the next command in the same boot.
- **Fix.** Split what the disk can prove from what only a start can prove, and write the third case into rule 2:
  1. List differs from the record (identities or order): STOP, as today. This is a real failure.
  2. List equals the record and the booted row is first, in a later boot: confirmed. Archive the record.
  3. List equals the record and the booted row is not first: the change is in place. Print "X runs; Y starts next; this start was not the default". Do not block. Keep the record open but non-blocking until a later boot shows case 2, or a new change supersedes it (archived as "in place, default start not seen").
  
  Name one confirmer (`title`, as today; `check` reports only). `keep-stock` on the booted stock is case 3 from the moment it is recorded. A reorder command may supersede an open case-3 record. This also answers question 4: after a power cut during the one write, the rename of `/boot/loader` leaves either the old or the new order (deploy.c 2210-2228), so the next start is either the unchanged list (the same command redoes it) or case 2/3 (the same command records it).
- **Check.** The shape tests (B1) need a row for "earlier boot's record" with each booted row. In the model (B2), the record is part of the state. Revert proof: restore `booted == value['booted']` as a condition of `done` and the model fails at "rollback, restart with menu choice R27". In the VM, step 4 can take one more restart: after `rollback`, choose the R27 row, then `check` must report the change as in place but not yet started; restart without a choice, and stock is confirmed. Today, step 6 makes its menu choice only after the record has been cleared, so the case is never rehearsed.

### 2. The model walks whole commands, so it cannot find the dead ends that the journal creates (package 23's failure)

- **Gap.** B2's transitions are "every command, a restart, a boot-menu choice". The journal's cut points (after the intent, after `set-default`, after the record) are tested only one at a time in B4, never combined with restarts and menu choices. This is the shape package 23's REVIEW-5 #4 rejected: an indivisible event hid the interleavings. The "no dead end" claim is only as wide as the event set.
- **Where it breaks.** `[R27*, R13, S]`, `at rollback`. Power is lost after `set-default` returns and before the record is written. The next start boots the first row, the stock. Then:
  - `check` and `title` STOP on the intent.
  - `at rollback` is the only command allowed to continue it, but rule 4 keeps its present refusal on the stock side ("Use keep-stock on booted stock…"), and today's `recover` runs that side check before the journal (`owner.py:568`, then `:1463`).
  - `at keep-stock` and `at update` STOP because only the same command may continue an intent.
  
  Every restart lands on the stock again. No tools command resolves it; only F12 → Windows → Help. The same cut followed by a menu choice of R27 leaves `completion()` returning None, so every command STOPs, the same command included.
- **Impact.** A narrow case, but it is not a known limit under the bar: the step it names is "get help". Every tools command stays blocked on every start until Help comes, and AresOS can be reached only by choosing it in GRUB each time. The brief promises a proof that this cannot happen. The model as specified cannot find it.
- **Fix.**
  1. Make each command's phases model events: intent written, primitive done, record written. Add a power cut at each of them, a restart (default row), a menu choice (any row), and finalize when something is staged.
  2. State the invariant over the tools' own words: from every reachable state, `check` passes, or the STOP text names a next step that, applied in the model, reaches a state `check` accepts, with nothing deleted, within a bounded number of steps.
  3. Add a rule to A.3: a command continues its own intent before any side or destination check.
- **Check.** The extended model. Revert proof: put the side check before the continuation and the model must report the sequence above.

## Medium

### 3. Rule 2 widens staging, which rule 6 and "If unsure" forbid, and no VM ever stages from the new orders

- **Gap.** Today staging needs the stock last (`qualified_state`, `owner.py:636`, and the three-row rule at `:645`). Rule 2 accepts any order, and rule 6 asks only for "a running AresOS that is first". So `update` with a newer bundle now also stages over `[R27*, S, R13]`, the order step 4 of the rehearsal ends in. The brief calls staging "as strict as today" and says widening rule 6 is never the safe default. Its own rules widen it.
- **What has been rehearsed.** No VM has staged over three deployments at all: package 27 staged over the pair, and staging over `[R13*, R27, S]` (allowed today) has never run. E cannot add this, because the 22c bundle's target, R27, is installed, so E never stages.
- **What the source says.** Finalize keeps the staged deployment first, then the pinned, booted and merge deployments in their old order (`ostree-sysroot.c` 2143-2185; called from deploy.c 4144-4151 with `NO_CLEAN`). bootc stages with ostree's merge deployment, which is the booted one (`deploy.rs` 985-1002, `ostree-sysroot.c` 1821-1840). So `[R27*, S, R13]` should become `[R28, R27, S]`. I read the source the same way the planner did. But the question lists this as unproven, and the first staging on the laptop under these tools is the next release.
- **Impact.** The first finalize with the pinned stock not last would happen on the owner's laptop, if he uses the new ways back before an update.
- **Fix.** Say in the brief that rule 6 deliberately accepts any order with the booted AresOS first. There is no narrower alternative: `set-default` moves one row to the front, so after `rollback` and then `update`, the stock can only end up second. Then do one of these:
  - (a) The next release's rehearsal finalizes over three rows for the first time anyway. Make it stage from `[R27*, S, R13]` as well as from the plain order, as a named must-walk item. Put it in 22c's report, under "only the model covers", and in the next release brief's acceptance. Until it is walked, the next release must not reach the laptop.
  - (b) Give E a throwaway test release to stage. It is CI-built and never pushed, but it needs a registry and signing that the harness may not have, so it costs more.
  
  I would take (a).
- **Check.** The next release's stage list must include the stock-second staging. The model test (B2) runs with a bundle whose target is not installed (R28), so staging, finalize, the four-row state and "the bundle's release is newer still" are in the model at all. Today B2 names no bundle, and with the 22c bundle none of this is reachable.

### 4. The model and the code share one picture of ostree and bootc, so they can agree by accident

- **Gap.** The model's transitions are only as true as the fake host, and nothing in the brief ties the fake to a real system:
  - `machine()` (`test_owner_update.py:77-91`) gives the fake host its bootc slots and is what any model built on it will use. It has been checked against real output for five package-13 pair stages only (`:336-345`). None of those has three deployments or a booted row that is not first.
  - The fake must now implement `ostree admin set-default` and finalize. Today `Machine.script` only knows `bootc switch` and `bootc rollback` (`:241-250`).
  - `Machine.script` writes `mutation=True` to the trace before the script's own checks run (`:216`). So "a refusal leaves no mutation in the trace" cannot tell a script that refused before `set-default` from one that ran it.
  - The brief forbids taking the tools' return values but not their helpers. A shared "reorder" helper, or `qualified_state` used as the model's acceptance rule, would repeat package 23's `self.accepted` mistake.
- **Where it breaks.** Example: the fake's finalize also keeps bootc's rollback row (a natural misreading of `RETAIN_ROLLBACK`). Then the model's four-row staged state finalizes to four rows, the tools' `completion()` is written to match, and both pass. The same holds for a wrong `rollbackQueued` for `[R13, S, R27*]`.
- **Fix.**
  1. The model computes nothing with `owner.py` code. It imports only the entry points under test.
  2. Build the fake's ostree from the sources above:
     - `set-default` removes the index and inserts it at 0;
     - `write_deployments` drops a staged row that is not first;
     - finalize keeps staged, pinned, booted and merge rows in their old order;
     - the bootc slots follow `status.rs` 348-365.
  3. Judge "no mutation" by the fake's list, pins and BLS before and after, not by the trace.
  4. Commit every rehearsal stage's raw `rpm-ostree status --json`, `bootc status --json` and BLS listing as fixtures. A test asserts that the fake reproduces each one: order, slots, `rollbackQueued`, pins and BLS identities. A difference fails the package.
- **Check.** Revert proofs: a fake whose finalize keeps the rollback row, and a `set-default` that appends instead of inserting, must each fail the fixture test.

### 5. The primitive is proven last: probe it before stage 1, and keep one package

- **Gap.** Everything rests on `set-default` with three deployments and a pin, followed by a default restart and a GRUB choice. It first runs in a VM in stage 2, after stage 1 has been built and reviewed. If it misbehaves, stage 1 and its review are redone:
  - the pin;
  - the default row on Bazzite's GRUB with three BLS entries;
  - what `ostree_sysroot_cleanup` does after the write;
  - the `(ostree:N)` titles after the reorder.
- **Fix (question 7).** One package, three stages, not two packages:
  - **Stage 0, a probe dispatch.** Package 27's route to R27, then plain `ostree admin set-default` through all six orders of {R27, R13, S}, a default restart after each, and one GRUB choice, capturing JSON and BLS at every stage. These are finding 4's fixtures.
  - **Stage 1** as drafted, built on those fixtures.
  - **Stage 2** as drafted.
  
  Cost: one of the four dispatches (about two hours on package 27's timing), and the harness lists wired earlier. Cutting into two packages instead (read-only acceptance first, the reorder second) does not work: the "no dead end" proof needs the commands, and accepting states without the commands gives no new way back. Part F can stay. It is test-only, but it is in the same file, so splitting it out would only cause conflicts.
- **Check.** Stage 1 acceptance: the fixture test from finding 4 passes on stage 0's captures.

### 6. The compatibility rule targets a transition the laptop will not make, and new records have no schema

- **Gap.**
  - **The real path is not rehearsed.** The 22c bundle is not installed on the laptop (board #196: the repaired tools come with the next release). The laptop's real path is version 2 (`851eb742…`) to the release bundle, which brings new tools, a new history and staging at once. Rule 9 and E step 1 rehearse version 2 to 3 tools-only, with the target unchanged.
  - **The rule is not carried forward.** Rule 9 is written as "version 3 reads version 2". It should hold for whichever bundle replaces the installed tools.
  - **No schema on the new records.** `outcome-pending.json` gets new kinds (rollback, keep-stock, an `update` that reorders), but no `schema` or `mode` field. `kind: update` then means either staging or a reorder, and every later version has to infer which from the shape: `completion()` today assumes the target was not in `before` (`owner.py:1197-1198`).
  - **The reverse direction is missing.** Until publication, the installed version 2 settles an interrupted tools update with its own `settle_tools` (`owner.py:2052-2107`, the same at `41b06513`). It accepts only `schema: tools-update1` with its fixed phases and fields. So the tools-update journal is frozen for every bundle that replaces version 2. Nothing says so, and part F invites changes to that path.
  - **The guide pins 22c's bundle.** Part D puts 22c's fingerprint into `docs/INSTALL.md`, so the owner may well install 22c's version 3 before the release arrives.
- **Where it breaks.** The next release bundle (tools ≥ 3, history with R28) over version 2: version 2's `previous` record is pending (same boot), the tools are updated, then the restart. `system_ready` accepts the pending record (`outcome` returns `pending`), and the new code must confirm it with version 2's positional fields. 22c tests that for its own bundle, but nothing obliges the release package to keep the test and to run that exact sequence.
- **Fix.**
  - State rule 9 against the installed fingerprint: "every bundle that can replace tools `851eb742…` reads its records and accepts its states", and carry it into the next release brief.
  - Name the version numbers: 22c's bundle is 3, so the release bundle must be 4. If it were also 3 and the owner had installed 22c's bundle, `update_tools` would refuse it as the same version.
  - State that the tools-update journal stays `tools-update1`, readable by version 2's `settle_tools`, and test it by running version 2's `settle_tools` from `41b06513` on a journal that version 3 wrote, at every cut before publication.
  - Write `schema` (and a staging or reorder `mode`) into every record version 3 writes, with one reader per schema. A version-2 record has no schema field.
- **Check.** B7 plus a test that version 3 refuses an unknown schema with nothing changed, and the release package's rehearsal starting from version 2's records.

## Low

### 7. Rule 2's "exactly one of two things is true" is false, and no decision needs it

- **Gap.** A booted row that is not first, with no record, can also come from three other sources:
  - version 2's unjournalled `rollback` in the pair. Version 2 accepts `[S, R*]` as a queued rollback (`owner.py:640-643`), and rule 9 makes version 3 accept it;
  - a `bootc rollback` typed in a Help session;
  - a boot loader that ignores the order.
  
  The title would print "this start was chosen in the boot menu" for all of them. Staging needs the booted row first and reorders work from any order, so the cause changes no decision, only a sentence.
- **Fix.** Print the facts ("X runs; Y starts next; this start was not the default") and state the cause only when the record proves it.
- **Check.** A shape row: version 2's queued pair, with no record, gets the neutral line.

### 8. `update` from the older AresOS has two destinations, and staging from it carries the older `/etc`

- **Gap.** The same running R13 with an R28 bundle gives two different results:
  - **After `previous`** (`[R13*, R27, S]`), `update` stages R28 over R13. Finalize removes R27, and R28's `/etc` is merged from R13's: the `ares` password set on R27 and anything else configured there is gone. C itself says R13 has no `ares` password.
  - **After a menu choice** (`[R27, R13*, S]`), `update` only makes R27 first.
  
  The owner cannot predict either from the word. This was already possible with version 2; 22c makes it a documented destination.
- **Fix.** This is a judgment call for the owner:
  - either stage only from the newest installed AresOS, so from R13, `update` first reorders to R27 and stages on the next run, keeping R27 as the rollback and its `/etc`;
  - or keep the rule, and have `update` print before staging which release is removed and that settings come from the running one, with the guides saying the same.
- **Check.** A model row for each choice, and the printed lines in the report's changed-lines list.

### 9. The brief's list of expectations that change on purpose misses a test that part D breaks

- **Gap.** D removes `rollback.sh`, `default-stock.sh` and `previous.sh` from the bundle. `test_shell_assertions.py:156-157` reads `owner-tools/payload/release/default-stock.sh`. B8's list does not name it, and AGENTS rule 5 then forbids changing it. Also, the "present message" rule 4 keeps for `rollback` on stock says "rollback would select the other deployment", which is no longer the reason.
- **A second conflict.** Stage 1's acceptance requires a hosted `checks_only` run, which is a `workflow_dispatch` input of `os-image.yml`, while the same section says "dispatch nothing until the integrator sends the tools review's verdict".
- **Fix.**
  - Add the test to B8 with its replacement: the payload no longer carries the old scripts, and the repository copies stay byte-identical.
  - Reword the message's reason.
  - Write "dispatch no rehearsal" instead of "dispatch nothing".
- **Check.** Stage 1's run of the full owner-tools suite.

### 10. Nothing schedules a calm proof on the laptop

- **Gap.** "Rehearse, review, then his laptop" ends with the tools installed, and the first real use of `rollback`, `keep-stock` or the menu would be during a real failure. Only the laptop can show:
  - its GRUB with three rows;
  - the pinned NVIDIA stock starting as the default after a reorder;
  - the owner reading the new two-line title.
- **Fix.** The next release's laptop record (27b-style) includes one calm round trip, with the owner's OK because it changes the boot order on his disk: `rollback` → stock → `update` → the newest AresOS, while nothing is wrong.
- **Check.** That record's stage list.

### 11. Rule 3's postcondition does not cover kernel arguments, which it promises not to touch

- **Gap.** "BLS equal" can be read as the identity set (`validate_bls`), which does not compare each entry's options. A reorder writes a new boot version with regenerated entries (deploy.c 2914-2990). The stock's keymap correction lives in its arguments. `check` would catch a returned keymap override later, but not other argument changes.
- **Fix.** The postcondition compares every entry's options, apart from `ostree=`, by identity before and after, as `unchanged_old` already does for the old stock.
- **Check.** A fake reorder that drops one argument must fail the script test (B3).

## Short answers to the seven questions

1. **The mechanism.** `set-default` on an index resolved by identity is the right single mechanism, and `bootc rollback` should leave the tools.
   - **What both can do that the postconditions would not see.** Both write the list through `ostree_sysroot_write_deployments_with_options`, and that call deletes a staged deployment without a word when it is not first (deploy.c 2840-2889). The preflight and the script both forbid a staged row, so this only matters if something stages between the script's read and the call. Then `set-default` deletes that staging, and the index it was given points one row off. Rule 3's postcondition catches the wrong order, but only after it has been written. With the updaters paused and masked, I would record this as a known limit, not add a mechanism.
   - Kernel arguments: finding 11.
   - `/etc` and pins: untouched (see the verdict).
   - Boot entries: every reorder changes the `(ostree:N)` titles, and rule 8's fresh title covers that.
2. **Accepting any order.** No order makes a later update delete the stock or the booted release: finalize keeps staged, pinned, booted and merge rows (source above), and staging needs the booted AresOS first. The questions that remain are which AresOS survives (finding 8) and the unrehearsed finalize orders (finding 3).
3. **Destinations.** The line is right. Staging from the booted stock would keep only the new release and the stock (booted and pinned), so both AresOS releases would go at shutdown. The surprise is finding 8.
4. **The journal.** Finding 1. The single write is atomic: a rename of `/boot/loader` after a full sync (deploy.c 2210-2228, 2454). The dead end after a cut is finding 2.
5. **Tools 2 to 3.** Findings 6 and 7.
6. **Evidence.** Findings 2, 3, 4 and 10.
   - VM walks the draft leaves to the model: staging and finalize from the new orders (finding 3), and a menu choice while a record is open (finding 1).
   - What only the laptop shows: finding 10.
7. **Size.** One package in three stages (finding 5).

## The next release, a third update, and more releases

The design makes these cheap, not a rewrite:
- Rule 1 already contains the four-row staged state.
- Destinations are relative to an append-only history, so "newest" and "older" stay defined as long as at most two AresOS are installed.
- A third update, from `[R28*, R27, S]` with an R29 bundle, has the same shape as the second.

What the next release needs from 22c:
- the must-walk stagings of finding 3;
- the compatibility rule of finding 6, stated against the installed fingerprint, with a schema on the records;
- the calm laptop proof of finding 10.

The one place the words stop naming a single destination is finding 8. Settle it before more releases build on it.
