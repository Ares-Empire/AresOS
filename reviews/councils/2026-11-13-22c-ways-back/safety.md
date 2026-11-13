# Safety member: 22c, every way back works after an update

Council of 2026-11-13. Reviewed: `BRIEF-DRAFT.md`, `os/owner-tools/owner.py` on main, the three release scripts, `test_owner_update.py`, `test_default_stock.py`, the guides, `planner-material/`. No test was run, no owner tool, `rpm-ostree`, `bootc` or `ostree admin` command was run, and nothing was written outside this file. Run read-only: the planner's `shapes.py` (it confirms the draft's "4 of 18"), and a read of the laptop's boot entries.

**Status: complete (15:16). Upstream claims are read from source. The answers to the seven questions are at the end.**

**Verdict.** Nothing the draft allows can touch the Windows drive, and nothing can unpin, modify or delete the pinned stock. No sequence I found locks him out of every system: the firmware default stays Windows, and no reorder creates or removes a deployment. The real gaps are two. The journal blocks every way back at the moment a way back is needed, and one ordinary action on stock deletes both AresOS releases at shutdown.

Count: 2 high, 3 medium, 2 low.

## Where each upstream claim comes from

Read today from the upstream tags, saved outside the repository:

| Claim | Source |
|---|---|
| Finalize at shutdown keeps the new deployment, pinned ones, the booted one, the merge deployment and other stateroots; it drops the rest. New is first, the kept ones follow in their old order. | ostree `v2026.4`, `src/libostree/ostree-sysroot.c`, `ostree_sysroot_simple_write_deployment`; called with only `NO_CLEAN` from `_ostree_sysroot_finalize_impl_staged_deployment` in `ostree-sysroot-deploy.c` |
| The merge deployment is the booted one when the stateroot matches | same file, `ostree_sysroot_get_merge_deployment`; bootc `v1.16.13`, `crates/lib/src/deploy.rs`, `MergeState::from_stateroot` |
| Finalize unlinks the staged state before it merges `/etc`: an interrupted finalize leaves the old list | `ostree-sysroot-deploy.c`, same function |
| Any deployment write drops a staged deployment that is not first, silently | `ostree-sysroot-deploy.c`, `ostree_sysroot_write_deployments_with_options` |
| `ostree admin set-default N` indexes the full list (a staged row counts), moves that row to the front and writes with `ostree_sysroot_write_deployments`, the same call `bootc rollback` makes; both end in a full cleanup with a repository prune | `src/ostree/ot-admin-builtin-set-default.c` (the planner's copy is byte-identical to the tag), `ot-admin-functions.c`, `ostree-sysroot-cleanup.c` |
| A reorder has two code paths. If kernel, initramfs, arguments, version and stateroot are equal at every position, only the `/ostree/boot.N` link is swapped and no boot entry is rewritten. Otherwise a new `loader.N` is written, synced, and `/boot/loader` is renamed. Both are atomic; only the second syncs after the swap. | `ostree-sysroot-deploy.c`: `deployment_bootconfigs_equal`, `swap_bootlinks`, `write_deployments_bootswap`, `swap_bootloader` |
| A killed `ostree admin` cannot leave `/boot` frozen: the thaw watchdog daemonizes and masks INT and TERM | `ostree-sysroot-deploy.c`, `fsfreeze_thaw_cycle` |
| `bootc rollback` is positional: it swaps the booted deployment with the first other one, toggles when a rollback is queued, drops a staged deployment, and writes `/run/reboot-required` | bootc `v1.16.13`, `crates/lib/src/deploy.rs`, `rollback`; `status.rs` (planner's copy) |
| `rpm-ostree cleanup --pending` removes every unpinned deployment of the stateroot listed before the booted one, not only a staged one | rpm-ostree `src/daemon/rpmostree-sysroot-core.cxx`, `rpmostree_syscore_filter_deployments`, read at upstream `main`; the laptop's version was not checked |

Read on the laptop, read-only (`/boot/loader/entries`, `/ostree/repo/config`, `df`): the three boot entries are all titled `Bazzite (ostree:N)`, use the same kernel and initramfs (one directory under `/boot/ostree`) and identical arguments apart from `ostree=`. ostree's bootloader setting is `none`. `/boot` is 2.0 GiB, 14% used.

Not verified: which Bazzite desktop actions start an update on stock (memory); the GRUB environment file (not readable without root).

## Gaps, most severe first

### 1. HIGH: a journal the restart did not fulfil blocks every command, including the ways back

**Gap.** Rule 5 and test B4 keep today's behaviour: `check`, `title`, `records` and `reboot` STOP on an unresolved journal, "a restart that lands elsewhere STOPs", and rule 3 refuses every reorder while another command's journal is open. Test B2 demands the opposite (apply a boot-menu choice from every state; then `check` and `title` accept and every system is one command away). The draft does not say which wins, and "if unsure: refuse" picks the dead end. The planned emergency card ("previous first, then rollback, then Windows") has the same hole: `previous` cannot be typed on a release that does not start, so the real path is the boot menu, and that path ends in STOP.

Package 22 chose this STOP on purpose (its review fixes: "an older booted release ... STOPs", Help decides each repeat). That held while the only answer to a failed update was Windows and Help. 22c changes the premise: it accepts starts chosen in the boot menu and promises one command per destination. Under that premise the same STOP is the dead end, so the decision needs to be made again, not carried over.

**Scenario a: the bad update, the case this package exists for.**
1. R27 runs, list `[R27*, R13, S]`. `at update` stages R28. Journal: recorded, expected `[R28, R27, S]`, booted R28.
2. `at reboot`. Finalize writes `[R28, R27, S]`.
3. R28 does not reach a usable screen. He restarts and takes the second row in GRUB. R27 runs, list `[R28, R27*, S]`.
4. `at check`: STOP (list equals `expected`, booted differs; today `owner.py:1165`, kept by B4). `at previous`: STOP, another command's journal. `at rollback`: STOP, same reason.
5. Every later start boots the broken R28 unless he picks a row by hand. The three rows read `Bazzite (ostree:0)`, `(ostree:1)`, `(ostree:2)` and nothing else.

**Scenario b: power lost before finalize.** `at update` stages R28; the laptop is held off or the battery dies during a slow shutdown. Next start: `[R27*, R13, S]`, nothing staged, journal recorded in an earlier boot. Only `at update` may continue, and it needs network, login and cosign again. Without network, `previous`, `rollback`, `check`, `title` and `reboot` all STOP although nothing changed.

**Scenario c: a reorder, then the wrong row.** `at previous` on `[R27*, R13, S]` writes `[R13, R27*, S]`. Restart, he takes the R27 row. `check` STOPs. The planned guide sentence "a wrong choice is harmless, because `check` says what runs and what starts next" is false in this state.

**Scenario d: confirmed late.** `at previous`, restart, R13 runs as expected, but he never types `check` or `title`. Days later he takes the R27 row. The journal still expects R13 booted: STOP with "did not finish at the restart", which is untrue.

**Impact.** No disk damage and no deletion. But the tools' ways back are gone at the one moment they are needed. What remains is a hand-picked row among three identical titles at every start, or Windows and help. This is the "state the tools produce and their own commands refuse" the package is meant to end.

**Fix.** Separate two facts the journal mixes: "the change was applied" and "the laptop started the target". After a restart (another boot id), with nothing staged:
- list equals `expected`, booted is the target: confirmed, as today;
- list equals `expected`, booted is another member: the change is applied. Say "X was installed (or selected), but this start runs Y: chosen in the boot menu, or X did not start". Archive the record as `landed-elsewhere`, then treat the state as an ordinary boot-menu state. Every command works;
- list equals `before`: the change did not happen. Say so, archive as `not-applied`, continue;
- anything else: STOP as today.

Never confirm silently: the line appears in `check` and `title`, and the archive keeps the observed state. Because the rows cannot be told apart by title, every `title` also prints the row map he will see after the restart, for example "(ostree:0) new AresOS, (ostree:1) the AresOS running now, (ostree:2) plain Bazzite". In B2, state the invariant for waiting states too: from every state, a restart with any boot-menu choice leads to a state that `check` and `title` accept and from which each installed system is one command away.

**Test that catches it.** B2 with the boot-menu transition applied from every state that has a recorded journal (update staged; each reorder made) and from "update staged, restart without finalize". B4's "a restart that lands elsewhere STOPs" is replaced by the outcomes above. Rehearsal: after step 5's `previous`, restart and take the R27 row; `check` must PASS and name both facts; `update` then puts R27 first again without a restart.

### 2. HIGH: on stock, one Bazzite self-update deletes both AresOS releases at shutdown, and the draft makes stock a normal place to stay

**Gap.** The draft makes `rollback` and `keep-stock` work with three deployments and adds a return (`update` from stock). Nothing checks, on stock, that Bazzite's own updaters are still off. The guide to be edited still says they stay paused only "until the owner chooses stock permanently" (`docs/INSTALL-PROCEDURES.md`, Keep stock). The pause itself is thin: `pause-stock-updates.sh` disables the timers for good, but its service masks are runtime-only and are gone after the first restart.

**Scenario.**
1. `[R27*, R13, S]`: `at rollback`, `at reboot`. Stock runs, `[S*, R27, R13]`.
2. On the Bazzite desktop he starts Bazzite's own update, or re-enables the timer because he means to stay. It stages a newer Bazzite, S2, with stock as merge deployment.
3. Any shutdown. Finalize keeps new, booted and pinned: `[S2, S]`. R27 and R13 are deleted with their `/etc` (the `ares` password, saved networks, layout).
4. `at update` on stock: STOP (`Unexpected prepared deployment list`). `before_switch` can never pass again, because the list no longer equals the prepared one.

**Impact.** Both AresOS deployments lost. His home files stay (same `/var`); Windows and the pinned stock are untouched. Getting AresOS back needs manual help, since the tools refuse the new list. Severity is high because it deletes and no tool can undo it; it needs one natural action outside the tools.

**Fix.**
- Tools: on booted stock, `check`, `title` and `keep-stock` run the existing `paused_state()` and STOP when a stock updater timer is enabled or a unit is active. A staged deployment seen on stock gets its own message: "A Bazzite update is waiting. Do not restart: the restart deletes both AresOS releases. Get help." The message must not suggest `rpm-ostree cleanup -p`: with stock booted behind the AresOS rows, that command deletes them too (source above). `update` from stock is never blocked by the pause check: leaving stock is the safe direction.
- Guides ("Back to AresOS from stock", Keep stock, the notice list in C): "Never update Bazzite itself while AresOS is installed: its update removes both AresOS releases at the next shutdown." Rewrite "until the owner chooses stock permanently".
- Residual risk: he can still update Bazzite and restart without typing a tools command. A stronger fix, pinning the AresOS releases while stock is the default, changes rule 1 and is a separate decision.

**Test that catches it.** A shape test: stock booted with a staged upstream deployment, in each accepted order, gives exactly that message and no mutation. A unit test that `check` on stock calls the pause check. In rehearsal step 4, assert on stock that the updater timers are still disabled after the round trip.

### 3. MEDIUM: an intent that changed nothing can only be cleared by the same word, and that word may refuse where he lands

**Gap.** Rule 5 reuses "only the same command may continue its own journal". Rule 4 says `keep-stock` refuses on AresOS and `rollback` refuses on stock. A power cut separates the two.

**Scenario.**
1. `[R27, R13, S*]`, stock chosen in the boot menu. `at keep-stock` journals its intent.
2. Power cut before or during `ostree admin set-default`. The swap is atomic: the list is the old one or the new one. Here it is the old one.
3. Next start, no choice: R27 runs. Journal: a `keep-stock` intent from an earlier boot.
4. `at keep-stock`: refuses, not on stock. `at rollback` (same destination): refuses, another command's journal. `check`, `title`, `reboot`: STOP.
5. The only exit is the boot menu, the stock row, and `keep-stock` again.

Two related defects in the same place:
- Today's journal reads `before[0]` as the booted deployment (`owner.py:1152`, `:1163`, `:1191`). After a boot-menu start that is false.
- On the laptop a reorder takes ostree's link-swap path (identical kernel and arguments in all three rows), which does not sync after the swap. The tools then fsync their record. A power cut within the filesystem's commit interval can leave a durable "recorded" beside the old order.

**Impact.** Fails safe, nothing changed. But the next step is a GRUB row among identical titles, which the package wants to make unnecessary.

**Fix.** For reorders, an intent or record whose list still equals `before`, with nothing staged, is void by proof: archive it as `not-applied` and let any command proceed (the rule of gap 1). Journal the destination identity, not the command word, and store `booted` beside `before`. In the script, call `sync` after `set-default` and before the result is recorded.

**Test that catches it.** B4 extended: for each reorder, cut before the change, then start on every deployment in turn. On each, `check` passes with the "did not happen" line and every command is available.

### 4. MEDIUM: the steps that delete, and one of the two reorder paths, are never walked; one model rule is wrong

**Gap.** Four holes in the evidence.
- **Finalize from a new order.** The six rehearsal steps only reorder. Nothing is staged after step 1, so finalize never runs on a list the draft newly accepts (stock in the middle; staging from the older release). By source it gives `[new, booted, stock]` in every order. But it is the step that deletes, and its first real run would be the next update on the laptop.
- **The second reorder path.** On the laptop, and probably in the VM, every reorder takes the link-swap path. After the next release with a new kernel, a reorder between R28 and R27 rewrites the boot entries and renames `/boot/loader`. The rehearsal as drafted would never see that path.
- **The journal against real status output.** The boot menu is used once, in step 6, from a confirmed state. No step lands elsewhere with a recorded journal (gap 1), and no step cuts between the reorder and its record.
- **The model's picture of `rpm-ostree cleanup --pending`.** `test_owner_update.py:207-209` models it as "the staged deployment goes, everything else stays". The real command removes every unpinned deployment listed before the booted one. Today the two agree, because staging requires the booted system first. Once any order is accepted, a later change that lets the stop routine run with an AresOS row before the booted one would delete that row, and the model would show nothing.

**Scenario.** Laptop after 22c: `at rollback`, restart, `at update`, restart: `[R27*, S, R13]`. Next release: `at update`, `at reboot`. Finalize runs for the first time on that order, and the first `at previous` afterwards takes the bootloader-swap path for the first time.

**Fix.**
- Rehearsal step 7 with a rehearsal-only newer release, as package 22 used its test release: from `[R27*, S, R13]`, `update`, restart, expect `[new, R27, S]` by identity with stock pinned; then take the stock row in GRUB and prove the pinned stock still starts; then one reorder back. Build that release so its kernel or initramfs differs, so the reorder takes the other path. If this is too large for 22c, write it into the next update release's brief as an entry condition: its rehearsal starts from a reordered list, not from `[R27, R13, S]`.
- One hard reset of the VM right after a reorder returns and before the tools record it; the same command must then record it from real `rpm-ostree` and `bootc` output.
- For every reorder in the rehearsal, save ostree's journal line (`bootconfig swap: yes` or `no`) with the stage's evidence, and state in the report which path each step took.
- Model: implement `cleanup --pending` and finalize by the source rules above; assert in the stop routine that the staged row is the only row before the booted one.

**Test that catches it.** Step 7; the hard reset; the two journal lines; a model test where a non-strict staging state plus the stop routine shows the deletion in the trace.

### 5. MEDIUM: the boot menu is the only exit from a default that does not start, and it has never been used on the laptop

**Gap.** The draft makes changing the Linux default routine, and every exit from a default that does not start goes through GRUB. `docs/INSTALL-STATUS.md` still lists "LOQ shortcuts and recovery menu" as OPEN: "exact fresh-title GRUB selection" has never been done on the real laptop. The draft keeps that row open and plans the first reorders on the laptop anyway.

**Scenario.** Tools version 3 on the laptop. `at previous`, `at reboot`. Suppose R13 does not start, for example on a `/var` that R27 has used for weeks. He presses Esc for the menu: it does not appear, or the keyboard does not move the selection. Linux is now unreachable until help; Windows still starts, because it is the firmware default.

**Impact.** Not a full lock-out, but every Linux system is out of reach by his own means.

**Fix.** An entry condition in the brief for the laptop step: before the first command that changes the default there, he opens the GRUB menu once with the list unchanged, reads the three rows against the row map `title` printed, and starts the default row. Only then the first reorder, and that one between the two AresOS releases (see question 6).

**Test that catches it.** That manual step, recorded in INSTALL-STATUS before the 22c line may say "on the laptop".

### 6. LOW: `update` from the older of two installed releases deletes the newer one and continues from the older one's `/etc`

**Gap.** Rule 4 allows staging whenever "an AresOS is running, first and with nothing waiting". With a later bundle (R28) on `[R13*, R27, S]` (after `previous`), `at update` stages R28 from R13. Finalize keeps `[R28, R13, S]`: R27 goes, and R28's `/etc` is merged from R13's. What he set on R27 (the `ares` password from `sudo passwd ares`, networks, layout) is not in R28.

**Impact.** Not a lock-out: `ares-recovery` exists on every system. A surprise the word does not announce. It cannot happen with this bundle (its target is R27), so it is about the rule, not the laptop today.

**Fix.** Rule 6's line says both things: "R27 is removed at shutdown, and the new release continues from this system's settings, not from R27's." Or refuse and point him to the newest installed release first; the owner's call.

**Test that catches it.** A staging test from `[older*, newer, S]` that asserts the two-part line.

### 7. LOW: rule 7 does not say that `layout begin` refuses on stock

**Gap.** "Already decided" says the stock's `/etc` is never written. Rule 7 asks only for "an accepted list, the booted system first". Read literally, after `keep-stock` a `layout begin` and `layout finish` on stock write the stock's `/etc` with `localectl`, and the emergency card's "backup stock always uses the installer's German layout" stops being true. Today `preflight_recovery(keep=False)` refuses on stock (`owner.py:568`); that check leaves with the pair check.

**Scenario.** `at rollback`, `at reboot`; on stock `at layout begin us`, the proof on tty4, `at layout finish`. The stock's `/etc/vconsole.conf` and X11 keymap are rewritten.

**Impact.** The fallback system no longer has the layout every guide promises for it; the password he types there lands on other keys than the card says.

**Fix.** One sentence in rule 7: `layout begin` on booted stock refuses with no mutation.

**Test that catches it.** One case in B6: begin on stock, first and booted, refuses and the trace has no mutation.

## Checked, no gap

- **Windows drive.** A reorder goes through the same `ostree_sysroot_write_deployments` as `bootc rollback` and as the finalize that already ran on the laptop. With the bootloader setting `none`, ostree writes boot entries and links on the Linux disk and starts no bootloader program (`write_deployments_bootswap` calls the backend only when one is set; that `none` yields no backend is from memory), so nothing probes or mounts another disk. Nothing in the draft touches firmware entries. The audit after every boot is the right check.
- **Pinned stock.** No pin operation and no removal in any reorder. Finalize and `cleanup --pending` both keep pinned deployments (source).
- **Interrupted reorder.** Both ostree paths are a single rename after a sync; stale temporary links are removed on the next write; a killed `ostree admin` thaws `/boot`. At the next start he gets the old order or the new one, both bootable.
- **Staging stays strict.** With the booted system first and nothing waiting, finalize can only drop the other, unpinned AresOS, which the tools announce. Rule 6 is what keeps `reconcile_update`'s cleanup safe; do not widen it.
- **Look-alike deployments inside the tools.** Stock by saved checksum, serial and stateroot plus pin; AresOS by history digest, no digest twice; the script re-reads before the write. Sound.
- **Tools 2 to 3 with three deployments.** `system_ready()` judges the laptop with the new tools; a refusal leaves version 2 in place. See question 5 for what the rule should add.

## Known limits (fail safe; for the report)

- `ostree admin set-default` takes an index. Between the script's read and the write, a newly staged deployment shifts the index; ostree then moves the wrong row and drops the staged one. The postcondition STOPs. B3's "a list that changes between the read and the write makes no `ostree admin` call" cannot be met strictly by a CLI call: word it as "the script narrows the window".
- With a nearly full `/boot`, finalize can remove a deployment it is about to drop in a first step and write the new one in a second (`auto_early_prune_old_deployments`). A power cut between the steps leaves a valid pair that the journal refuses. Not the laptop today (2.0 GiB, 14% used).
- Rule 1 calls every AresOS release "unmodified"; rule 3 asks it only of the target. Read the first way, a layered package or an overlay on the running AresOS blocks `rollback`, the way out of it. Bind "unmodified" to the reorder target and to staging, never to the system he is leaving.
- Each system keeps its own passwords and layout: a password changed on R27 is not changed on R13 or on stock. One line in the guides.

## The seven questions

1. **Mechanism.** One identity-resolved `set-default` is the right single mechanism. `bootc rollback` is positional and toggles: on `[R27*, S, R13]` it selects stock, and in a boot-menu state it selects the booted system. Keeping it for some cases means two sets of postconditions. Both mechanisms drop a staged deployment silently and neither touches pins, `/etc` or arguments. Underneath they make the same write and the same cleanup with a repository prune (it runs after the swap and takes time; a cut there leaves the new order and no record). What the postconditions would not catch: the missing sync in the link-swap path (gap 3), and which of the two paths ran (gap 4).
2. **Any order.** With rule 6 kept, no accepted order lets a later `update` delete anything but the other AresOS. The deletions that matter come from outside the tools (gap 2), and "no working way back" comes from the journal, not the order (gap 1).
3. **Destinations.** Reorder-only from stock is the right line: staging from stock would merge from the stock's `/etc` and finalize would keep only the new release and stock. Surprises: gap 6; and `update` on stock returns him to the newest release even when he had left it for the older one, so `previous` must also work on stock (B2 implies it; rule 4 should say it), and the PASS line must name the release.
4. **Journal.** Sufficient for the target-is-booted case if `booted` is stored on its own. A power cut gives the old or the new order; the four combinations with intent or record are in gaps 1 and 3. He can always get out only after those two fixes.
5. **Tools 2 to 3.** Missing from the rule:
   - where version 2 would STOP on a record and version 3's better rule resolves it (gap 1), version 3 wins;
   - version 3 must install from the states where version 2 is stuck today (stock taken in the boot menu beside two releases, which version 2's `check` refuses; R13 after `previous`, from which no version 2 command moves on), and B7 should list them by name;
   - there is no way back to version 2 (a downgrade is refused), so make it a standing rule with a test: each later tools version accepts every resting state the previous one can leave, and reads its journal kinds;
   - the same toolset runs on all three systems, so the new script must run under the stock's and R13's Python, ostree and rpm-ostree. Steps 3 and 4 do that; say it, so nobody trims them.
6. **Evidence.** See gaps 4 and 5. Only the laptop can prove: F12 and the GRUB menu with its keyboard, stock and R13 starting on today's `/var`, and the real three-deployment state version 2 made. "Rehearse, review, then his laptop" is enough only with an order for the first use there: tools update, `check`, the menu proof of gap 5, then `previous` and `update` (AresOS to AresOS), and only then `rollback`.
7. **Size.** If cut, cut by risk: first the reorder mechanism, the journal fix and the three-deployment commands from resting states; second the boot-menu states and the return from stock. The cost of that cut is that stock stays a one-way door for one more package, which is today's state. Do not cut the journal fix (gap 1) off the reorder mechanism: the mechanism without it adds more ways into the dead end.
