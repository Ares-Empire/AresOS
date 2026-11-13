# 22c: every way back works after an update

Empire board brief 278. Owner tools, guides, a VM probe and a VM rehearsal. Branch `pkg/22c-ways-back-after-update`; report, reviews and runs go to `reviews/22c-ways-back-after-update/`. 27b is merged (`4d0c4dc5`). This package must be on main before the second update release (packages 23 and 21b).

A design council checked the draft of this brief on 2026-11-13 (`reviews/councils/2026-11-13-22c-ways-back/VERDICT.md`: the direction stands, 11 gaps, the journal rule changes). Every binding finding is written out below. You do not need the council folder.

**Goal:** After an update the owner can always choose which installed system starts next, with one command each and a confirmation after the restart: the newest AresOS (`at update`, also forward again after `at previous`, and back from plain Bazzite), the AresOS before it (`at previous`), or plain Bazzite (`at rollback`, or `at keep-stock` after choosing it in the boot menu). Keyboard-layout trials work again. No command of the tools leaves a state that the other commands refuse. A restart that lands on another installed system, or a power cut in the middle of a change, never leaves him without a working command.

**Shorthand in this brief.** R27 is the newer AresOS on the laptop, R13 the older one, S the pinned plain Bazzite ("stock"), R28 a later release that is not installed yet. `[R27*, R13, S]` is the deployment list in order: the first row starts next, the star marks the running one. `at <word>` stands for `sudo /var/lib/ares/at <word>`.

**Where builders go wrong.** Three facts look alike and are different: *the selection is applied* (the list has the target first), *a restart is waiting* (the target does not run yet), and *the target's boot is confirmed* (a later boot, with another boot id, ran the target). Never merge them into one state, in the code or in the fake. If the fake merges them, the model agrees with the same mistake and proves nothing. Rule A5, point 3, keeps them apart, and so does B2's state.

## Today (main `ffaac472`; the laptop was read, not changed, on 2026-11-13)

- The laptop: `[R27*, R13, S]`, nothing pending. Installed tools: version 2, fingerprint `851eb742…` (the payload at `41b06513`). bootc 1.16.13, ostree 2026.4.
- `rollback`, `keep-stock`, `layout begin` and `layout abandon` STOP with `Expected exact stock/AresOS pair`: `preflight_recovery` requires two deployments (`owner.py:572`).
- Stock chosen in the boot menu: `check`, `title` and `reboot` STOP (`qualified_state`, `owner.py:646`), and `keep-stock` STOPs with `Pending deployment or rollback` (`:571`). With two deployments it is the same (`Wrong queued rollback`, `:642`). bootc reports `rollbackQueued` whenever the booted deployment is not first (`status.rs` at v1.16.13), so that flag cannot tell a boot-menu choice from a queued rollback.
- After `at previous`: `update` STOPs with `Target release is already deployed; get help` (`:1399`), and `previous` with `The other AresOS is newer; previous only returns from an update` (`:1628`).
- `qualified_state` accepts 4 of the 18 combinations of order and running system for {R27, R13, S}.
- The journal: `Tools.outcome()` (`:1125-1166`) STOPs after a restart unless the recorded release runs in the recorded order (`:1161-1166`). It reads `before[0]` as the booted row (`:1152`, `:1163`; `completion()` at `:1191`). `recover()` runs its side check (`preflight_recovery`, `:568`, called at `:1462`) before it looks at the journal (`:1463`). Two dead ends follow:
  - `at previous`, restart, another row taken in GRUB: every command STOPs, at every later start.
  - `at rollback` cut by power after its change and before its record: the laptop starts stock, where `rollback` refuses and no other word may continue it.
- The stock side: `paused_state()` (`:757`) runs only before the first switch. `os/release/pause-stock-updates.sh` disables Bazzite's updater timers for good, but masks the services only until the next restart (`--runtime`). `docs/INSTALL-PROCEDURES.md:156` says to leave them paused only "until the owner chooses stock permanently". A Bazzite update started on stock stages a new Bazzite; at the next shutdown ostree keeps the new, pinned, booted and merge rows, so both AresOS releases are deleted.
- Layout: `layout abandon` on another deployment clears the trial without restoring anything (`:1806-1821`).
- Tools update: `system_ready()` (`:2168-2176`) judges the system with the new tools' `qualified()`. `settle_tools()` (`:2052`) accepts only the journal schema `tools-update1` (`:2075`), and the installed version 2 runs it until publication.
- Tests: `test_owner_update.py:1254-1259` swallows the injected refusal (`except refusal: pass`). The fake host there logs `mutation=True` before a script's own checks run (`:216`), models `cleanup --pending` as "only the staged row goes" (`:207-209`) and knows only `bootc switch` and `bootc rollback` (`:241-250`). Its status output was compared with real output only for package 13's pairs.
- No VM has run `set-default` over three deployments, staged over three deployments, or typed `keep-stock` after a boot-menu choice.
- `os/manifest/ci/16/pending-rebind.json` holds four waiting files (three tests and the workflow). The hosted checks-only job passes again (it fetches full history).

## Three stages, one PR

| Stage | Work | Ends with |
|---|---|---|
| 0 | P: wire the harness, probe plain `set-default` in a VM, commit its captures | **Stop and report.** |
| 1a | A and the tests B1 to B11: the state machine, its model and the compatibility tests, built on stage 0's captures (B9's payload test waits for 1b) | **Stop and report.** A checkpoint inside stage 1. |
| 1b | C, D, F, B12 and B9's payload test: guides, bundle, bindings, the refusal invariant, the route and binding tests | **Stop and report.** Dispatch no rehearsal until the integrator sends the tools review's verdict. |
| 2 | E: the rehearsal, its captures, the record step | The final report. |

Stage 1 has a checkpoint because it is too large for one builder context. If 1a's tests read the payload, 1a may refresh it; the fingerprint's pins in the guides and `commands.json` follow in 1b. "Stop and report" means: commit, push, bring `REPORT.md` up to date for the stage, end your run. The integrator starts the next stage or part, often in a fresh context: write each stage report so that a builder who has only this brief and the report can go on. Open the PR at the first stop.

**In scope:**

### P. Stage 0: probe the reorder before building on it

Everything in A rests on `ostree admin set-default` with three deployments and a pin. Package 11 ran it over a pair only. So it runs first and alone, and its real output becomes the fixtures the tests must reproduce.

1. **Wire the harness first.** A new mode on this branch for the probe (E adds a second one), package key `22c`. Extend every list that names packages 14, 16 and 27 (the workflow, `owner_media.require_runner`, `registry_auth`, `rehearsal_guard`, `os/ci/rehearsal-packages.json`, `installer_webui`, `two_disk_vm`, `owner_vm`, `owner_capabilities`, `owner_devices`) and the tests that guard them (`UpdateJobGatesTest`, `OwnerHarnessPackagesTest`, `VmStepDecisionsTest`) before the first dispatch. Package 27's first two rehearsal runs died on such lists.

   **The host walk belongs to the wiring.** `owner_vm.main` picks a host-walk receipt per package and refuses a dispatch whose sources changed (`os/ci/owner_vm.py:1640-1648`, "Host walk is stale"). There is none for 22c. Package 27's generator (`reviews/27-first-update-release/walk-host.py`) writes package 27's receipt, which must not be regenerated. So, before the first dispatch: write this package's generator (`reviews/22c-ways-back-after-update/walk-host.py`), add the probe's route to the local walk (`test_owner_walk`), generate `os/manifest/ci/22c/host-walk.json`, and make the probe mode select it.
2. **The route.** Package 27's route unchanged up to R27 confirmed (the 15f tools `3ef85c4a…`, then version 2 from `41b06513`). The list is then `[R27*, R13, S]`. From there the harness types plain commands as root. The owner tools are not used again in this run.
3. **The walk.** All six orders of {R27, R13, S} with plain `ostree admin set-default <index>`, the index found by checksum and serial each time. Moving S, R27, R13, S, R13, R27 to the front in turn visits all six and ends at the start: `[S, R27, R13]`, `[R27, S, R13]`, `[R13, R27, S]`, `[S, R13, R27]`, `[R13, S, R27]`, `[R27, R13, S]`. After each move: capture, restart with no choice, prove which row runs, capture again.
4. **One GRUB choice.** From `[R27, R13, S]`: restart and take the stock row, found through its boot entry (package 11's `select_grub_menu`, adapted to three rows). Capture. Restart with no choice: R27 runs.
5. **Captures at every stage:** the raw `rpm-ostree status --json`, the raw `bootc status --json`, the boot entries (file names, titles, options), the pins, which row runs, and after each move ostree's journal line `bootconfig swap: yes` or `no`. Package 11's protected-disk audits after every boot. Commit the captures under `reviews/22c-ways-back-after-update/runs/`. Check them for tokens first.
6. **What the probe must show** (expected from ostree 2026.4's source and bootc 1.16.13's `status.rs`):
   - `set-default` removes the row and inserts it first; the other rows keep their order; nothing is created or removed;
   - the stock stays pinned and its boot options stay the same;
   - a start with no choice runs the first row, also when that is the stock (greeter, German login);
   - `rollbackQueued` is true whenever bootc's rollback slot comes before the running row.

   Report also whether the `(ostree:N)` number in each menu title equals the row's place in the list. If a capture contradicts one of these points, or rule A2 or A3, say so first in the stage report and build nothing on it.

### A. One rule (`os/owner-tools/owner.py`, one new release script)

1. **What may be installed.** Two lifecycles, told apart by the list alone:
   - *Before the first switch* (no installed AresOS). The two states version 2 accepts stay exactly as they are: the prepared stock list, equal to the saved state (`owner.py:612-614`), and the first switch staged, where stock runs, the only staged row is the bundle's target and the rows that are not staged equal the prepared list (`:621-627`). `prepare`, `login`, `verify` and `switch`, and what `title`, `records`, `check` and `reboot` accept, refuse and print there, do not change. Rules 2 to 8 and 10 do not apply there.
   - *With AresOS installed* (at least one AresOS row that is not staged). The set stays as reviewed: exactly one corrected stock with the saved identity, pinned, its reference and digest unchanged; one or two AresOS releases from the tools' history, each unpinned, unmodified and with its exact reference, no digest twice; during an update, one staged target in front. Everything else STOPs as today (an unknown or pinned release, an unpinned or changed stock, a third AresOS without a stage, two staged rows, a foreign deployment). Rules 2 to 8 and 10 are about this lifecycle.
2. **Order is free; only "first" matters.** Any order of that set is accepted. The first deployment starts next. A running system that is not first is a normal state. Rule 8 says how the title words it.
3. **One reorder operation**, used by every command that changes what starts next:
   - Preflight, read-only: no layout trial, `idle`, the disk record, an accepted list with nothing staged, no change waiting from this boot, the journal resolved by rule 5, boot entries equal to the deployments, and the target found exactly once by its saved identity (stock) or its history digest (AresOS), unmodified.
   - Journal the intent (rule 5). Then one script (`os/release/start-next.sh`, or a name you justify). It reads the list again immediately before the call, finds the target's index by checksum and serial, asserts its digest and reference and that nothing is staged, runs `ostree admin set-default <index>` once, runs `sync`, then reads the list again and asserts the result. The `sync` is needed: with identical boot entries ostree swaps a link after its own last sync, so a durable record could otherwise sit beside an order that is not durable yet.
   - Afterwards: the same identities and flags as before, the target first, the others in their old relative order, stock pinned, boot entries equal. Then the record and a fresh title.

   It never creates or removes a deployment and never touches a pin, kernel arguments or any `/etc`. `bootc rollback` leaves the tools.
4. **Each word names a destination.** The tools work out whether that needs a download, a reorder or nothing:

   | Command | Destination |
   |---|---|
   | `update` | The newest AresOS. (a) The bundle's release is installed: the reorder (no network, no login, no cosign; its digest is the history's). (b) It is not installed, and an AresOS runs, is first, with nothing staged or waiting: staging, as today (rule 6). (c) It is not installed and staging is not allowed (stock runs, or the running AresOS is not first): the newest AresOS that is installed, by reorder only. It then says that the bundle's release is newer still and names the next step (from stock: restart, then `update` again). |
   | `previous` | The older of two installed AresOS releases. |
   | `rollback` on a running AresOS, `keep-stock` on running stock | The pinned stock. |

   - `update` and `previous` work from every system, stock included. From stock `previous` is the only word that leads to the older AresOS.
   - `rollback` and `keep-stock` keep their sides. Each refuses on the other side with nothing changed, after rule 5's resolution, and its text says which word applies here. The old reason "rollback would select the other deployment" is no longer true: reword it.
   - A destination that is already first changes nothing, writes no journal and says so, and says whether it runs now.
   - Every PASS line names the system it selected.
   - `login` on AresOS refuses when `update` would need no download.
5. **The journal: the deployment list decides, not the command word and not the running row.**
   1. *What is written.* Every change writes an intent before it and turns it into a record after it, in `outcome-pending.json`, as `update` and `previous` do today. `rollback`, `keep-stock` and the reordering `update` use the same journal. Both forms carry: `schema`, `mode` (`staging` or `reorder`), the word, the boot id, the target's identity (for staging its digest, because its identity does not exist yet), the running row's identity, `before` (the list before the change) and the intended list. `completion()` derives the intended list from identities (after staging: the new release, the system that ran, the stock), never from positions. Nothing reads `before[0]` as the running row.
   2. *Resolve first.* Every command that reads the list, `check` and `title` included, first resolves an open intent or record from the list alone, before any side check, destination check or check of its own:
      - the list equals `before` (for staging: with nothing staged, after a restart): **not applied**. Archive it as `not-applied`, say so in one line, and go on with the command;
      - the list equals the intended list: **in place**. An intent becomes the record, with no second `set-default`. Then point 3 applies;
      - anything else: STOP with nothing changed, as today.

      One exception keeps today's rule. In the boot that wrote it, a staging intent is continued only by `update` (it stages again from the unchanged list, or records the staging it made), and a staging record needs its staged list still there. The STOP that other commands give on such an intent names `update` as the next step.
   3. *What "in place" means*, with nothing staged. Three outcomes, never merged:
      - **Waits for the restart:** in the boot that made the change, with a target that does not run. `check`, `title`, `records` and `reboot` pass and say so. A second change refuses and says: restart first.
      - **Applied, nothing waits:** in the boot that made the change, with a target that runs already (`keep-stock` after a boot-menu choice; `update` on the newest AresOS when it was started from the boot menu). The default selection is applied and no restart is waiting. This is its own outcome. It is not (a): no start has been seen since the change. It is not (b): the target does run. The title states it ("<X> runs and now starts next; no restart is waiting") and prints no confirmation. Every command works at once. A new change archives the record as `applied-not-restarted`. The record stays open for the next start, which gives (a) or (b).
      - **After a restart** (another boot id; "confirmed after the restart" is printed only then):
        - (a) the target runs: **confirmed**. `title` prints one line and archives the record.
        - (b) another installed system runs: **in place, not yet started**. `check` and `title` print it, and nothing blocks. The record stays open until a later start gives (a), or until a new change supersedes it (archived as `in-place-not-started`). The line states facts. It never says that the change failed: the target may have started on a day when no command was typed.
        - (c) the list equals `before`: not applied, as in point 2.
        - (d) anything else STOPs, as today.
   4. *One confirmer.* `title` confirms and prints the line (`check` and `records` run it, as today). A change that follows without a title archives the open record under the state it is in, as `intend()` does today.
   5. *For rules 3, 6 and 7* a record that is "applied, nothing waits" or in state (b) is neither "waiting" nor "unresolved".
6. **Staging stays strict:** only from a running AresOS that is first, with nothing staged, no change waiting, no modified deployment and no layout repair note for the running system (rule 7); never from stock. The order of the other rows is free on purpose. After `rollback`, restart, `update`, restart the list is `[R27*, S, R13]`, because `set-default` can move only one row to the front. Finalize keeps the new, pinned, booted and merge rows in their old order, so staging from such a state removes nothing but the other AresOS.
   - Before the restart `update` names the AresOS that is removed when the update finishes at shutdown: the other one, whichever it is (today the line says "Older AresOS" for `retained[1]`, `owner.py:1521`).
   - When the running AresOS is the older one (`[R13*, R27, S]` after `previous`), a second line follows: "The new release starts with this system's settings (Wi-Fi, passwords, layout), not <the removed one>'s." This is owner decision 5. Build it so and report it as a JUDGMENT-CALL.
   - `reconcile_update` asserts that the staged row is the only row before the running one before it calls `rpm-ostree cleanup --pending`. Otherwise it deletes nothing and says so.
7. **Layout trials.** Neither command uses the pair check any more.
   - `layout begin` needs an accepted list, a running AresOS that is first, nothing staged and no change waiting. On running stock it refuses with nothing changed: the stock keeps the installer's German layout that every guide promises for it.
   - `layout abandon` needs an accepted list with nothing staged, on whichever system runs, stock included. A trial belongs to the deployment it began on. On another system abandon clears the trial and writes to neither `/etc`, as today.
   - If that trial's finish had begun (`finishing`), abandoning it on another system leaves a repair note bound to the trial's deployment, with the recorded old settings. When that deployment runs again, `layout abandon` restores them and clears the note. Until then `layout begin` there refuses and names `layout abandon`. The note also blocks staging from that deployment: `update` refuses there with `layout abandon` as the next step, and does not fall back to a reorder. The reason: a new release takes over the running system's settings, half-written layout included, and the note would stay behind with the old release. Reorders, checking and restarting stay available.
8. **What he reads.**
   - Every title says in plain lines: which system runs; which starts next; and the boot-menu rows for the next start, read from the boot entries by identity, for example `(ostree:0) newer AresOS, starts next; (ostree:1) older AresOS; (ostree:2) plain Bazzite`. With an update staged the rows are the ones expected after shutdown, and the line says so.
   - When the running system is not first, the title states the facts: "<X> runs; <Y> starts next; this start was not the default". It names a cause only when a record proves one: a change waiting from this boot, or rule 5's "in place, not yet started". Without a record it names none. Such a start can come from a boot-menu choice, from version 2's unjournalled queued rollback in the pair, from a `bootc rollback` typed with Help, or from a boot loader that ignores the order. No decision depends on the cause, and `rollbackQueued` proves none.
   - The history's records carry no release number and stay unchanged. One helper names each system the same way in every line, by role and short digest.
   - STOP texts name the next step. Keep every PASS line the guides quote unless this brief changes its meaning; list each changed line in the report.
9. **The laptop's tools.** Tools version 3 (`history.json`) with the unchanged release history: the target stays R27.
   - Version 3 accepts every state version 2 accepts. It reads version 2's records (`outcome-pending.json` in both statuses, `title.json`, `prepared.json`, the layout records) with the result version 2 would give, except where rule 5 resolves a record that version 2 refuses: there rule 5 applies.
   - Version 3 installs from the states where version 2 is stuck today: stock taken in the boot menu beside two releases, and R13 after `previous`. `system_ready()` judges with the new tools, so rule 5 must hold there too.
   - The tools-update journal stays `tools-update1` with its phases and fields: version 2's `settle_tools` reads it until publication.
   - Every record version 3 writes carries `schema` and `mode`. A record without `schema` is version 2's. Version 3 refuses an unknown schema with nothing changed.
10. **On plain Bazzite its own updaters must stay off.** This rule is for the lifecycle with AresOS installed (rule 1). Before the first switch the updater checks stay where they are (`before_switch`).
    - On running stock, `keep-stock` runs the existing `paused_state()` and STOPs with nothing changed when an updater timer is enabled or an updater unit is active.
    - `check` and `title` print the same finding as a warning line with the next step: `at update` back to AresOS, then Help. They do not STOP for it, so `reboot` and the way off stock keep working.
    - `update` from stock is never blocked by that finding.
    - A staged deployment while stock runs beside an installed AresOS gets its own STOP in every command that reads the list, `update` and `reboot` included: "A Bazzite update is waiting. Do not restart: the restart deletes both AresOS releases. Get help." No text ever suggests `rpm-ostree cleanup -p`: with stock running behind the AresOS rows it may delete them too.
    - The first switch is not this case. There no AresOS is installed yet, the staged row is the bundle's target, and rule 1 accepts it as today. A foreign stage on the prepared list keeps today's refusal: this message would be untrue there.
11. **One place for the command text.** The owner asked for a short command, `aresos update`, in place of `sudo /var/lib/ares/at update` (board #195). It is an image change and comes with the next release. Do not make it harder: every message that names a next command, new or old, builds it from one helper in `owner.py`. The printed text of existing lines stays the same. A test compares the helper with `os/owner-tools/commands.json`. New guide text writes the command in full, as the guides do today.

### B. Tests (`os/tests`)

1. **Shapes.**
   - All 4 pair and 18 triple combinations of order and running system: each without a record, with this boot's record in both same-boot outcomes of rule 5 (waits for the restart; applied, nothing waits), and with an earlier boot's record for each running row. Accepted or refused exactly by rules 1, 2 and 5.
   - Version 2's queued pair `[S, R*]` with no record: accepted, with rule 8's neutral line and no cause.
   - Every wrong shape that rule 1 forbids keeps refusing.
   - Before the first switch (rule 1): the prepared stock list and the first switch staged are accepted, refused and printed as by version 2, command by command.
   - Telling a first switch from a foreign stage: a first switch staged gets no rule 10 message; a foreign staged row on the prepared list gets today's refusal, not rule 10's message; a staged row on running stock beside an installed AresOS gets rule 10's message, also when that row is the bundle's target.
   - Rule 10, with AresOS installed: running stock with a foreign staged deployment, in each order, gives that message from every command and no change. With a timer enabled or a unit active, `keep-stock` STOPs, `check` and `title` pass with the warning, `update` and `reboot` are not blocked.
2. **A model over the whole state space**, as package 23's review fixes 4 built for its hand-off.
   - *State:* the list with pins and stage, the running row, the open journal with the outcome of rule 5 it is in, the layout trial, the repair notes, and each system's persistent keyboard settings (console and X11, one pair per `/etc`). The journal is state. "Selection applied", "restart waiting" and "target boot confirmed" are three different states.
   - *Equivalence, so that the run ends.* Compare states in a reduced form:
     - a row is its role (the stock, a named release), not its literal checksum and serial. A release staged again after a stop is the same row;
     - a boot id is only "this boot" or "an earlier boot", for the journal and for the trial; a login session is only "the trial's session" or "a fresh one";
     - archived records, receipts and time stamps are not state.

     The fake may hand out fresh literal values. The exploration stores the reduced form, and the test asserts that it ends and prints the number of states.
   - *Start:* the laptop's list and the pair, each with this package's bundle (target R27, installed) and with a test bundle whose target R28 is not installed. Without the second, staging, finalize and the four-row list are never reached.
   - *Events:* each command in its phases (intent written, primitive done, record written); the layout commands, with a power cut between the two persistent writes of `finish`; a power cut after each phase; a restart with no choice; a boot-menu choice of any row, from every state that has one; finalize at shutdown when something is staged (the new release takes over the running system's settings), and a power-off without it.
   - Run until no new reduced state appears.
   - *Invariants:*
     - from every reachable state `check` passes, or its STOP names a next step that, applied in the model, reaches a state `check` accepts, with nothing deleted;
     - from every state with nothing staged, nothing waiting and no active layout trial, each installed system can be made the next start by one command;
     - from a state with something staged or waiting, a restart with any row leads to a state with nothing staged and nothing waiting;
     - from a state with an active layout trial, the trial's own commands end it: `proof` and `finish`, `revert` and then those, or `abandon` after a restart or from a fresh login, on whichever system runs. Walk each of these paths. The state after it meets the two invariants above. The layout lock of rules 3 and 6 stays: do not remove it to make the model pass;
     - a system whose persistent layout is half written always has an open trial or a repair note bound to it, `layout abandon` on it restores the old settings, and no release is ever staged from it;
     - retention: after finalize the list is exactly the new release, the system that ran and the stock, by the model's own rule. Another row left, or one of these missing, fails;
     - a refusal leaves the list, the pins and the boot entries as they were, and a change meets rule 3's postconditions. Judge both by the fake's state before and after, not by the trace;
     - nothing is ever removed except a staged row (by the stop routine or a power-off) and the other AresOS at finalize, after the line that announced it.
   - *Independence:* the model imports only the entry points under test. It computes nothing with `owner.py` helpers: no `qualified_state` as its acceptance rule, no shared reorder helper. The expected result of a step comes from the model's own rules, never from the tools' return values.
3. **The fake's ostree and bootc**, written from the sources. Test 10 holds them to real output where this package has real output. The finalize rule over three rows has none yet: B2's retention invariant holds it (see test 11).
   - `set-default` removes the index and inserts it at 0;
   - a list write drops a staged row that is not first;
   - finalize keeps the new, pinned, booted, merge and other-stateroot rows in their old order;
   - bootc's slots and `rollbackQueued` follow `status.rs` 348-365 (the rollback slot is the first other deployment of the stateroot; it is "queued" when it comes before the booted one);
   - `cleanup --pending` removes the staged row and every unpinned row before the booted one;
   - a script that refuses before its primitive leaves no mutation.
4. **The reorder script** against a modelled list, as `test_default_stock.py` does. A wrong identity, digest or reference, a staged row, or a missing or doubled target makes no `ostree admin` call. The script re-reads immediately before the call, runs `sync` after it and checks the result; a wrong list afterwards fails.
5. **The journal.** For each reorder (`rollback`, `keep-stock`, `previous`, the reordering `update`): a cut before the change, after it and before the record, at the status read and at the record write. After each cut take a restart with no choice and a boot-menu choice of each row. In each of these states `check` passes and names the outcome, a change that is in place gets no second `set-default`, and every destination is one command away. Each of rule 5's outcomes (a) to (d) has a test. So has "applied, nothing waits": after `keep-stock` on stock chosen in the boot menu, the title that follows at once states it and prints no confirmation; a restart with no choice then confirms; a restart with another row gives (b). For staging: an intent and a record followed by a power-off before the shutdown finished (`not-applied`); a finished update followed by a boot-menu choice of the old row ((b), and `previous` then works); a target that started as recorded but was never confirmed, then another row chosen later ((b), and no line says the change failed).
6. **Staging:** refused on stock, on a running AresOS that is not first, with a change waiting, and with a layout repair note for the running system (the refusal names `layout abandon`). `completion()` right when the stock sits in the middle of the list. Staging from `[older*, newer, S]` asserts both lines of rule 6. `reconcile_update` with an unpinned row before the running one makes no `cleanup` call.
7. **Layout:** begin and abandon with three deployments; begin refused with a change waiting and on running stock; abandon on stock chosen in the boot menu. Rule 7's repair: a cut between the two writes of `set_keyboard`, abandon on stock, return to that AresOS, abandon restores, and a new trial then works. The sequence the note must stop: the same cut on R27, abandon on stock, return to R27, then `update` with the R28 test bundle refuses to stage and names `layout abandon`, while `previous`, `rollback`, `check` and `reboot` still work there. After `layout abandon` the staging works, and R28 takes over settings that are whole.
8. **Tools 2 to 3** (rule 9). Load version 2's code from `41b06513`, as the release-13 tests load older tools.
   - The tools update over every resting state version 2 can leave, and over the two stuck states by name, each also with version 2's `previous` record open.
   - "Accepts everything version 2 accepts", by name also the prepared stock list and the first switch staged (rule 1), and version 2's records read as rule 9 says.
   - Version 2's `settle_tools` on a tools-update journal that version 3 wrote, at every cut before publication.
   - A record with an unknown `schema` refuses with nothing changed.
9. **Expectations that change on purpose.** List each in the report with the rule that replaces it. Apart from these, AGENTS rule 5 holds.
   - Tests that pin today's refusals: for example `test_recovery_and_layout_pair_accepts_any_known_release_but_only_the_pair`; the `stock not last`, `stock booted beside two releases` and `running not default` cases; the direction refusal of `previous`; the rehearsal's `previous-13-update-refused`; the tests that pin the STOP after a restart that landed elsewhere.
   - `test_shell_assertions.py:156-157` compares the payload's `default-stock.sh` with the repository copy. The payload no longer carries the three old scripts; the repository copies stay byte-identical. Change the test to say that.
10. **The fixture test.** The fake must reproduce every committed capture of stage 0, and later of stage 2: order, slots, `rollbackQueued`, pins and boot-entry identities. A difference fails the package. These captures hold reorders, boot-menu starts and package 27's staging over a pair. They cannot show a wrong finalize over three rows: do not claim that they do.
11. **A revert proof per rule:** name the assertion that fails when the rule is taken out. Among them:
    - a fake `set-default` that appends fails the fixture test on stage 0's captures;
    - a fake finalize that also keeps bootc's rollback row fails B2's retention invariant now: staging over the triple then leaves four rows. No fixture of this package can catch it, because neither P nor E stages over three rows. The real capture is the next release's gate (see "For the next update release");
    - a side check placed before rule 5's resolution fails the model (`rollback`, a cut after `set-default`, a restart onto stock);
    - "the recorded row must run" put back as a condition fails the model (`rollback`, restart, the R27 row chosen).
12. The route and binding tests pass: `test_owner_path`, `test_owner_equality`, `test_owner_walk` (with the local walks of the probe's and the rehearsal's routes; regenerate `os/manifest/ci/22c/host-walk.json` after the last change to a file it binds), `test_owner_commands`, `test_owner_retained`, `test_owner_tools`, `test_owner_abandon`, `test_checkout_sources`, `test_owner_step_limits`.

### C. Guides (phone-readable boxes, PASS, STOP and a return in each, the existing style)

- `docs/INSTALL.md`, update route: the paragraph on three deployments says what works now. The "misbehaves" box gains forward again with `at update`. A short tools-only update (the Windows box and the tools box, then `check` and `title`, nothing else): the route E step 1 rehearses and the laptop session will follow. The fingerprint in both copy checks and both bootstrap blocks. Rule 6's two facts about an update from the older AresOS.
- `docs/INSTALL-PROCEDURES.md`:
  - later layout (each installed system keeps its own layout; no trial on stock);
  - recovery menu: three rows that differ only in `(ostree:N)`; take the row the last title named; a wrong choice is harmless, because `check` says what runs and what starts next, and every command still works;
  - rollback and keep-stock beside two AresOS releases;
  - a new short "Back to AresOS from stock";
  - "Keep stock", "Back to AresOS from stock" and the notice list say: "Never start a Bazzite update while AresOS is installed: it deletes both AresOS versions at the next shutdown." Delete "until the owner chooses stock permanently" (line 156): choosing stock for good is INSTALL step 9's permanent abandonment.
- `docs/EMERGENCY.md`, "Failed or bad update":
  - the new AresOS does not start: restart, F12, Linux, take the row the last title named for the AresOS before the update, then `at previous`;
  - it starts but misbehaves: `previous` first, then `rollback`, then Windows;
  - "Never choose a guessed GRUB title" becomes "choose the row the last title named";
  - the sentences that say the tools refuse with three deployments, and that a check STOPs after a restart that landed elsewhere, go or change to what rule 5 does.
- `docs/INSTALL-REFERENCE.md`: the quoted tool messages that changed.
- `docs/INSTALL-STATUS.md`: the update row and a 22c line: built, rehearsed (run link), **not on the laptop**, whose tools stay `851eb742…` until they are installed there. The line names what must happen before it may say "on the laptop": the tools installed, then the owner's calm test (the "try this" note below). "LOQ shortcuts and recovery menu" stays OPEN.
- With the old tools these procedures STOP with `Expected exact stock/AresOS pair`. The guides say that this line means "install the current tools first".
- Say what he will notice: plain Bazzite has no `ares` account and keeps German; the AresOS from before the update has no `ares` password and no admin rights; the files in his home stay; each system keeps its own passwords, Wi-Fi and layout.

### D. Bundle and bindings

- `bundle.py`: the new script in; `rollback.sh`, `default-stock.sh` and `previous.sh` out of the payload. They stay in `os/release/` byte-identical: older CI modes read them (`keyboard_vm.py:283`, `switch_vm.py:535` and `:547`, `two_disk_vm.py:669`).
- `python os/owner-tools/bundle.py --refresh`; the new fingerprint in `docs/INSTALL.md` (four places), `commands.json`, INSTALL-STATUS and the report, as PR #22 and package 27 did.
- Bound files: after the last change to a bound file in each stage, run `python3 reviews/27-first-update-release/rebind.py pending "<note>"`. It compares with the active tables and writes the exact rows. The four files that wait already stay listed. Never edit walk tables or the list's rows by hand.
- The host walk: `reviews/22c-ways-back-after-update/walk-host.py` is this package's generator and a permitted new file. It writes `os/manifest/ci/22c/host-walk.json`. Stage 0 generates it for the probe's route (P1). Stage 1 extends the generator for E's route and regenerates the receipt, and E's mode selects it. Regenerate it after the last change to a file it binds, or the dispatch stops as stale. Package 27's generator and receipt stay as they are.
- **The record step (stage 2).** This package's rehearsal is the next VM rehearsal, so it needs its own record step. `rebind.py record` is package 27's one-time step and stays as it is. Add a step for 22c, in that script or in a script of this package (say which and why), that:
  1. writes `os/manifest/ci/22c/source-bindings.json` exactly as the run recorded it, and checks every row against the checkout;
  2. makes these the active tables: `checkout_sources.active_tables()` names package 27's bindings in code (`os/ci/checkout_sources.py:106-116`) and must return 22c's once they exist;
  3. moves what waited into a new entry of the list's `rebound` history (what waited, for which bindings, the new bindings, the run link), and empties `files` and the waiting `changes`. The older history stays readable;
  4. leaves `rebind.py pending` working for the next package.

  `test_checkout_sources` passes before and after. No evidence of package 27 is regenerated or edited.

### E. Stage 2: VM rehearsal (the two-disk harness; a second new mode on this branch, package key `22c`)

Start from the laptop's history: package 27's route unchanged up to R27 confirmed and `sudo passwd ares` (the 15f tools `3ef85c4a…`, then version 2 from `41b06513`). Then, typed as the owner types, with package 11's protected-disk audits after every boot and every stage's list compared by identity (nothing created, nothing removed, stock pinned):

1. R27, list `[R27*, R13, S]`, tools `851eb742…`: this package's bundle through the guide's tools-only route (version 2 to 3, the first update of a versioned toolset in a VM, and the install the laptop will get); `check`, `title`. The title's row map equals the boot entries.
2. R27: a layout trial to US International (begin, tty4 proof, finish), restart, typing proof; back to German the same way; one trial ended by a hard reset and `layout abandon`.
3. `previous`, restart, R13 confirmed. `update` there with the network off, restart, R27 confirmed; his password from the start still passes `sudo -v`.
4. `rollback`, restart, stock (greeter, German login), confirmed. There: `rollback` refused with no change; `keep-stock` changes nothing; Bazzite's updater timers are still disabled and `check` shows no warning. `update`, restart, R27 confirmed with the stock now second.
5. From that order: `previous`, restart, R13 confirmed; `update`, restart, R27 confirmed. Then the restart that lands elsewhere: `previous`, restart, take the R27 row in GRUB by the title's row map. `check` PASSes and names both facts (R27 runs; R13 starts next, in place, not yet started). `update` works at once and puts R27 first; its title says "applied, nothing waits" (rule 5) and prints no confirmation. Restart with no choice: R27 confirmed after the restart.
6. The boot menu without a record: `title`, restart, take the stock row in GRUB by the title's row map (`select_grub_menu`, adapted to three rows). `check` prints rule 8's neutral line and names no cause. `keep-stock`: its title says "applied, nothing waits" and prints no confirmation. Restart with no choice: stock again, confirmed after the restart. `update`, restart, R27.
7. The cut: on R27, `rollback`, and one hard reset (QMP `system_reset`) after its reorder is on disk and before its record. The start that follows runs stock. `check` there PASSes: it records the change from real `rpm-ostree` and `bootc` output and confirms it, with no second reorder. `update`, restart, R27 confirmed.
   - How the harness hits that window is your choice, for example a second root console that freezes the tools' process as soon as the list shows the new order. No test-only switch goes into the bundle.
   - Before the reset the harness proves that the journal still holds the intent. If it holds the record, the step did not test the cut: repeat it.

End on R27. The same toolset runs on R27, R13 and stock in this route, so the new script is proved under each system's Python, ostree and rpm-ostree: do not trim steps 3 and 4.

Evidence under `reviews/22c-ways-back-after-update/runs/`: the result file, the transcript of every typed command, the audits, and for every stage the same captures as P5. For every reorder save ostree's `bootconfig swap` line, and say in the report which path each step took. The run records its bound sources for D's record step.

Budget: the repository is public, so standard runners cost nothing. At most four VM dispatches in all, the probe included, and 1200 minutes; report before dispatching more. Checks-only runs are short; count them in the budget table. Estimates, not measurements: the probe about two to three hours, the rehearsal about four (package 27's passing run took 109 minutes). Raise the step and job bounds on purpose; a hosted job ends at six hours.

### F. The refusal invariant (PR #37, REVIEW-1)

In `test_invariant_one_working_toolset_after_any_interruption_and_any_refusal`:

- Give every cut and refusal an expectation derived from the journal phase the cut leaves (copy after renames 1 and 2, publish after 3 to 5, retire after 6 and 7, records after 8 and 9, complete after 10), written as a table in the test. Where the injected check runs, both attempts raise the expected refusal with its message and leave the phase unchanged. Where it does not run, assert what happens instead (the update completes; the next run says `Tools already installed; nothing changed`).
- The integrator's reading, which the council's chair shared; check it, do not copy it: the `system_ready` checks (layout trial, transaction, the failing `observations`) and `installed_commands` run only in copy and publish; `disk_record` runs at every cut; the stick identity at cuts 1 to 9; the staged-bundle injection changes nothing at any cut, because `.update-tools` exists only between the copy and rename 2. No row may stay empty like that: make the injection real (for example a changed `tools-<fingerprint>/owner.py` before publication) or cut inside the copy.
- Revert proof: with the layout-trial check taken out of `system_ready`, the test fails at cuts 1 to 5.
- This part changes tests only. The tools-update journal keeps its schema, phases and fields (rule 9).

**Out of scope:**

- The image, `os/manifest/release.json`, the records in `history.json`, any publish, any new release, the masks of the two finalize units, and the short command `aresos update` (all with the next release).
- Installing this bundle on the laptop, the owner's calm test there, and anything typed on the real laptop.
- Staging from stock, a command that cancels a waiting change, and new command words.
- Pinning the AresOS releases while stock is the default (it changes rule 1; a separate decision).
- A throwaway third release to stage in E (see "For the next update release").
- Different boot-menu titles (an image change).
- `os/config`, `os/build.sh`, the desktop supervisor (package 23), backlight and power button (21b), `at logs`, `OwnerTools.psm1`.
- `STATE.md` and `HANDOFF.md` (the integrator).

**Acceptance:**

- **Stage 0 (P):**
  - the wiring tests pass, and a hosted `checks_only` run passes on the pushed head;
  - one probe run passes the walk and the GRUB choice with every audit unchanged;
  - the 22c host walk is generated by this package's generator and selected by the probe mode;
  - its captures are committed, and the stage report has a table of every stage (order, running row, bootc's slots and `rollbackQueued`, pins, titles, swap path) and an answer to each point of P6;
  - changed bound files are recorded in the pending list.
- **Stage 1a, the checkpoint (A and B1 to B11):**
  - the tests B1 to B8, B10 and B11 pass in a hosted `checks_only` run on the pushed head, with the count of each focused module; for modules that run locally, also the local counts, plain and `-B`;
  - the fixture test passes on stage 0's captures;
  - the model ends, with its number of states, and its table of states and commands is in the report;
  - the report names every test that still fails at this head and why it waits for 1b (the bundle fingerprint, the guides' quoted lines, the bindings, the host walk). None of them may be a test of the state machine or of compatibility;
  - the changed expectations (B9) and the revert proofs (B11) so far are in the report.
- **Stage 1b (C, D, F, B12):**
  - every test in B and F passes in a hosted `checks_only` run on the pushed head, and the whole suite is green;
  - `test_owner_update` with 0 skipped namespace tests (hosted);
  - the fingerprint equal in every pin, the pending list exact, and the host walk regenerated for E's route;
  - `git diff main --stat` shows no file outside this brief;
  - no rehearsal dispatched.
- **Stage 2 (E):**
  - one rehearsal run passes steps 1 to 7 on the reviewed head with every audit unchanged;
  - its result file and captures are committed, and the fixture test passes on them too;
  - the record step ran: 22c's bindings exist, the waiting rows are in `rebound`, the list is empty;
  - a hosted `checks_only` run passes on the final head, and the INSTALL-STATUS row carries the run link.
- **`reviews/22c-ways-back-after-update/REPORT.md`** in the AGENTS format, with:
  - stage 0's table and its answers to P6;
  - the table of every state and command from the model;
  - the changed test expectations and the changed PASS and STOP lines;
  - the revert proofs;
  - which transitions the VM walked and which only the model covers. The second list names "staging and finalize from `[R27*, S, R13]`", "staging from `[R13*, R27, S]`", "finalize over three rows (no real capture; the next release's gate)" and "a first install with version 3 (the prepared list and the first switch): tests only";
  - which `bootconfig swap` path each reorder took;
  - the known limits below (what it is, the harm, why it is accepted), and any you add;
  - the budget table, and where each test count comes from;
  - every JUDGMENT-CALL, with at least owner decisions 1 and 5;
  - "For the next update release", repeated from this brief;
  - at the end, the short "try this" note for the owner, for after the tools are on the laptop:
    1. `check` and `title`. With nothing changed, open the boot menu once, read its rows against the title's row map, and start the default row.
    2. Then, with his OK, because it changes which system starts on his disk: `previous`, restart, `update`, restart (AresOS to AresOS first); then `rollback`, restart, `update`, restart. About half an hour.

**Where tests run.** You work on the owner's laptop, which has the real `rpm-ostree`, `bootc` and `ostree`. The suite was written for machines without them: `reached()` in `test_owner_update.py` uses `Required tool missing: rpm-ostree` as its marker, and its real-entry tests start the tools unpatched in a namespace. On the laptop they would call the real binaries.

1. Full-suite counts and every acceptance count come from the hosted `checks_only` run (`os-image.yml`).
2. Locally, run only modules that do not depend on those tools being absent and never start the real entry. Check each module before its first local run. Never run `test_owner_update` locally: its changes (F and parts of B) are checked in hosted runs, so plan for those. Put the model, the shapes and the fixture test in modules that use only the fake host, so they run locally.
3. Never run the owner tools or those binaries against the laptop, also not "read-only".
4. One suite at a time: the owner uses the laptop, and package 23 tests on it.

**Known limits the council accepts.** Each fails safe. List them in the report; do not build a mechanism around them.

1. *The index window in `set-default`.* A deployment staged between the script's read and its write shifts the index; ostree then moves the wrong row and drops the staged one, and the postcondition STOPs. Accepted: the updaters are paused, the lock and `idle` run first, the window is milliseconds, every row stays bootable.
2. *Finalize's early prune with a nearly full `/boot`.* A cut between the prune and the write leaves a valid pair that rule 5 (d) refuses. Accepted: it needs a nearly full `/boot` and a cut in a short window, and the system stays bootable.
3. *A modified running AresOS blocks the way out of it* (rule 1 refuses `rollback` too). Accepted: it needs his own `rpm-ostree` action, a transient overlay is gone at the next restart, and widening rule 1 is never the safe default.
4. *The cause of a start that was not the default cannot be told.* Accepted: no decision depends on it, and rule 8 states facts only.
5. *Identical boot-menu titles.* Accepted: changing them is an image change; the title's row map removes the guessing.
6. *Each system keeps its own `/etc`* (passwords, Wi-Fi, layout). Accepted: it is how ostree works; one line in the guides.
7. *He can still start a Bazzite update and restart without typing a tools command.* Accepted: after the guide line and rule 10 it needs a deliberate act against the guide.
8. *No cancel before the restart.* Accepted: he restarts and uses the opposite command, which rule 5 makes work.
9. *No staging from stock.* Accepted: finalize would keep only the new release and the stock.

**Not confirmed by the council.** Treat these as open, not as facts:

- that `rpm-ostree cleanup --pending` removes every unpinned row before the booted one (read at upstream `main`, not at the laptop's version). Rule 6's assertion and rule 10's wording hold either way;
- that the laptop's boot entries are identical apart from `ostree=`, so that a reorder takes the link-swap path there. Rule 3's `sync` holds on either path, and P and E record the path in the VM;
- which actions on Bazzite's desktop start an update while the timers are disabled;
- where ostree keeps the pin, and that a list write never touches it. Rule 3's postcondition catches a change either way.

**For the next update release** (the integrator writes these into its brief and posts them on the board; repeat them in the report):

1. Its rehearsal stages from `[R27*, S, R13]` (reached by rollback, restart, update, restart) as well as from `[R27*, R13, S]`. It expects `[new, R27, S]` by identity with the stock pinned. It then starts the stock row from the menu and makes one reorder back. This is acceptance and a laptop gate for that release. No staging can happen on the laptop before that release's bundle exists. Its raw captures of staging and finalize over three rows become fixtures that the fake's finalize must reproduce. Until then only B2's retention invariant holds that rule; this package has no real output for it.
2. Rule 9 holds for its bundle against the tools installed then (this package's, or `851eb742…` if they are not on the laptop yet), and its tools version is 4.

**Already decided:**

- Owner decisions:
  1. `update` goes to the newest installed AresOS from anywhere, also forward after `previous` and back from stock. Decided by the integrator on the council's unanimous advice (2026-11-13). The owner was asked twice (board #195, #204) and had no view on it ("Idk I didn't try anything"). It is shown to him as a JUDGMENT-CALL with the "try this" note before the merge. If he then says no: drop the stock rows of rule 4's `update` and the returns from stock in E (steps 4, 6 and 7); the model then records stock as a state with no way back.
  2. The repaired tools go on the laptop in their own short session before the next release (owner, board #205, 2026-11-13: "Yes, tools on their own first"; this replaces his earlier "next release" on board #196). This package rehearses that tools-only install from the laptop's state (E step 1) and ends there. Installing on the laptop is outside it; Claude types the steps there with his password approval.
  3. The calm laptop test (boot menu, older AresOS and back, stock and back) is an owner step after that install, outside this package. The report ends with the "try this" note for it.
  4. Bazzite stays frozen while AresOS is installed (decided 2026-10-24). The tools now warn and STOP as rule 10 says.
  5. `update` from the older AresOS keeps removing the newer one, and prints both facts before the restart (rule 6). Build it so; it is a JUDGMENT-CALL for the owner at merge.
- Rollback, keep-stock, previous and the reordering update never create or delete a deployment. The stock is never unpinned, never modified, and its `/etc` is never written.
- One mechanism for every reorder: `ostree admin set-default` on an index resolved by identity. The council confirmed it.
- The words stay `update`, `previous`, `rollback` and `keep-stock`, each with one destination.
- The journal follows the deployment list (rule 5). Package 22's rule, "refuse unless the restart landed exactly as recorded", is replaced on purpose: in a design that accepts boot-menu starts it is the dead end.
- A later update removes the other AresOS at shutdown (package 22's JUDGMENT-CALL 1, board #154).
- Going forward to an installed release needs no network and no new signature check.
- No change can be cancelled before the restart; he restarts and uses the opposite command.
- One package, three stages, with a checkpoint inside stage 1. The reorder and the journal rule are not split.
- Before the first switch nothing changes: the prepared stock list and the first switch staged stay as version 2 accepts them (rule 1).
- The bar (owner, 2026-11-11): reasonably safe, like any existing CLI; extra care for updates, rollback and disks. A narrow case that fails safe is a known limit for the report, not a reason for another mechanism.

**If unsure:** refuse with nothing changed and a message that names the next step. Leave the stock alone. Claim less in the guides. Widening rule 1 or rule 6 is never the safe default. One limit on "refuse": a refusal that leaves him with no working command is not safe. Where a refusal would break B2's first invariant, rule 5 wins. Record the question as a JUDGMENT-CALL or PLAN-GAP.

**Model:** Builder: a Claude agent on Fable 5.2 for stages 0, 1a and 1b (the owner tools' state machine on his real disks; CLAUDE.md's rule for hard AresOS tasks). Stage 2 may run on Opus with a fresh context, and goes back to Fable if two runs fail inside the new steps. Review: fresh, never the builder: Codex gpt-6-astra (high) while it is available (it ends on 2026-11-21), otherwise a Claude agent on Fable 5.2, because updates and rollback are the high-stakes class. The final review before this bundle reaches the laptop is Fable's.

## Rules

- `AGENTS.md` applies. Push `pkg/22c-ways-back-after-update` and open a PR. Never merge, never push to `main`, never `--no-verify`.
- The repository is public: no personal data, serials, GUIDs, emails or tokens, also not in committed captures.
- Never run the owner tools, `rpm-ostree`, `bootc`, `ostree admin`, `systemctl reboot`, `loadkeys` or `localectl` against this laptop. Don't touch other worktrees.
- Commits end with `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>` (or the model that wrote them).
