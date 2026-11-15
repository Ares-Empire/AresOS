# Council verdict: package 22c, every way back works after an update

Chair: Claude (Opus 5.5), 2026-11-13. Members: OS reliability (Codex gpt-6-astra), safety (Claude Fable 5.2), architecture (Claude Opus). They did not see each other's answers.

**What the chair checked itself.** Everything was read; nothing was run, and the running system was not touched.
- `owner.py`: `outcome` (1125-1166), `completion` (1176-1213), `recover` (1458-1473), `preflight_recovery` (564-585), `qualified_state` (592-652), `before_update`, `update`, `reconcile_update`, `previous`, `layout` (1755-1867), `paused_state`, `update_tools` and `settle_tools`.
- `test_owner_update.py`: `machine()`, the fake host's `mutate` and `script` (195-260) and the refusal invariant (1222-1262). Also `test_shell_assertions.py:145-157`, `pause-stock-updates.sh`, the three release scripts, the `checks_only` input of `os-image.yml`, `INSTALL-PROCEDURES.md:111-162`, `EMERGENCY.md` "Failed or bad update", and INSTALL-STATUS's recovery-menu row.
- Upstream, from the copies retained in the repository and the planner material:
  - ostree 2026.4 `ot-admin-builtin-set-default.c`;
  - `ostree_sysroot_simple_write_deployment` (`os/manifest/ci/13/13e-zero-cost/ostree-sysroot.c` 2105-2185);
  - finalize, its merge deployment and its `NO_CLEAN` write (`os/manifest/ci/13/zero-cost/ostree-src_libostree_ostree-sysroot-deploy.c` 4099-4151);
  - the silent drop of a staged row that is not first (2836-2870);
  - the link-swap and bootconfig-swap paths (2915-3040);
  - bootc 1.16.13 `status.rs` 342-365.

## 1. Is the direction right?

Yes. Option C is the right structure, and all three members say so independently.
- `bootc rollback` is positional. bootc's rollback slot is the first other deployment of the stateroot, and it counts as "queued" whenever it comes before the booted one (`status.rs` 361-365). With three rows it can never put the third row first, and in a boot-menu state it toggles.
- `ostree admin set-default` removes one row and inserts it first, then writes through the same `ostree_sysroot_write_deployments` call. Resolved by identity, it is the one primitive that serves every destination.
- Finalize keeps the new deployment first, then every pinned, booted and merge deployment in their old order (`ostree-sysroot.c` 2143-2185). So accepting any order, while staging only from a running AresOS that is first, can delete nothing but the other AresOS.

**The one thing that must change is the journal.** Rule 5, test B4 and "only the same command continues" carry over package 22's rule: refuse unless the restart landed exactly as recorded. In a design that accepts starts chosen in the boot menu and promises one command per destination, that rule becomes the dead end the package exists to remove. After a restart that lands on another installed system, or a cut during a reorder, every tools command STOPs (gaps 1 and 2).

The deployment list, not the command word or the booted row, must decide:
- keep "the change is in place" apart from "the laptop started the target";
- let every command resolve an open journal from the list, before any check of its own.

The brief also contradicts itself here: B2 demands that `check` accepts every reachable state, and B4 demands a STOP. Under "If unsure: refuse", the builder would pick the dead end.

## 2. Ranked gaps

### Gap 1. HIGH: a restart that lands on another installed system leaves every tools command refusing

- **Gap.** After a recorded change, a start that is not the recorded target STOPs `check`, `title`, `records`, `reboot` and every reorder. That is today's `outcome()` (`owner.py:1161-1166`), which rule 5, B4 and rule 3's "no unresolved journal" keep. Rule 2 also leaves out the third case: a record from an earlier boot.
- **Sequence (22c's own bundle).**
  1. On `[R27*, R13, S]`: `sudo /var/lib/ares/at previous`, `at title`, `at reboot`.
  2. F12, Linux, and in GRUB he takes the stock row (or the R27 row).
  3. `at check` STOPs with "The return to R13 did not finish at the restart (another deployment runs)…".
  4. `at keep-stock`, `at update`, `at previous`, `at title` and `at reboot` all STOP. Every later default start boots R13.
- **Sequence (the next release, the case this package exists for).**
  1. `at update` stages R28, then `at reboot`.
  2. R28 does not reach a usable screen. He restarts and takes R27's row: `[R28, R27*, S]`.
  3. `at check` and `at previous` STOP. Every default start boots the broken R28.
- **Impact.** The tools give no way back at the moment one is needed. What remains is a hand-picked row among three identical `Bazzite (ostree:N)` titles at every start, or Windows and Help. Nothing is deleted.
- **Found by** all three: OS reliability 1, safety 1, architecture 1 and 7.
- **Brief changes.**
  - **Rule 2.** Replace "exactly one of two things is true…" with: "When the booted system is not first, the title states the facts: '<X> runs; <Y> starts next; this start was not the default'. It names a cause only when a record proves one (a change waiting from this boot, or rule 5's 'in place, not yet started'). A start that was not the default can also come from version 2's unjournalled queued rollback in the pair, from a `bootc rollback` typed with Help, or from a boot loader that ignores the order."
  - **Rule 5.** Replace "`check`, `title`, `records` and `reboot` STOP on an unresolved one" and "let the first check after the next start confirm". After a restart (another boot id), with nothing staged:
    - (a) the list equals the record's expected list and the target runs: confirmed;
    - (b) the list equals the expected list and another installed system runs: *in place, not yet started*. `check` and `title` print it and nothing blocks. The record stays open until a later default start confirms it (a), or a new change supersedes it (archived as `in-place-not-started`);
    - (c) the list equals the list before the change: *not applied*. It is archived as `not-applied` and nothing blocks;
    - (d) anything else STOPs, as today.
  - **One confirmer.** `title` confirms (`check` runs it). The record stores `booted` and the target identity beside `before`. Nothing reads `before[0]` as the booted row (today `owner.py:1152`, `:1163`, `:1191`). A record in state (b) is neither "waiting" nor "unresolved" for rule 3's preflight.
  - **B2.** The open record is part of the model's state, and the boot-menu choice is applied from every state that has one.
  - **B4.** Replace "a restart that lands elsewhere STOPs" with outcomes (a) to (d).
  - **E.** In step 4 (or 5), after `rollback` (or `previous`), restart and take another row. `check` must PASS and name both facts. The destination command then works without a restart, and a restart with no choice confirms.
  - **Guides.** The recovery-menu sentence "a wrong choice is harmless" is true only with this rule. Rewrite EMERGENCY's "new AresOS does not start" line: restart, F12, Linux, take the row the last title named for the AresOS before the update, then `at previous`.

### Gap 2. HIGH: an interrupted reorder can be finished only by the same word, and that word refuses where he lands

- **Gap.** Rule 5 reuses "only the same command may continue its own journal", and rule 4 keeps each word's refusal on the other side. Today `recover` runs that side check (`owner.py:568`, inside `preflight_recovery` at `:1462`) before the journal (`:1463`). A power cut between the intent and the record therefore separates the word from the side.
- **Sequence (change applied).**
  1. On `[R27*, R13, S]`, `at rollback` journals its intent, and `set-default` writes `[S, R27, R13]`.
  2. Power is lost before the record. ostree's repository prune runs after the write and takes time, so a forced power-off "because it hangs" fits here.
  3. The next start boots stock.
  4. `at check` and `at title` STOP on the intent. `at rollback` refuses on stock. `at keep-stock` and `at update` STOP, because they are not the same command.
  5. Every start lands on stock, and the only step left is Help.
- **Sequence (nothing applied).**
  1. On `[R27, R13, S*]`, stock was taken in the menu. `at keep-stock` is cut before its write.
  2. The next start runs R27. `keep-stock` refuses on AresOS, and everything else STOPs.
  3. The only exit is the stock row in GRUB.
- **Impact.** In the first variant the system changed and every tools command is blocked at every start. That is not a fail-safe refusal under the bar.
- **Found by** all three: OS reliability 2, architecture 2 (high), safety 3 (medium; it found the nothing-applied variant). The chair rates it high because of the applied variant.
- **Brief changes.**
  - **Rule 3.** The journal records the destination identity, the booted row, `before` and the intended list, not only the word.
  - **Rule 5, added.** "Every command, `check` and `title` included, first resolves an open reorder intent or record from the list alone, before any side or destination check:
    - equal to `before`: `not-applied`, continue;
    - equal to the intended list: recorded, then gap 1's outcomes;
    - anything else: STOP.
    A staging intent keeps today's rule: only `update` continues it in the same boot. After a restart, a staging intent or record whose list equals `before` with nothing staged is `not-applied` too." This also covers safety's power cut before finalize.
  - **Rule 3's script.** It runs `sync` after `ostree admin set-default` and before it returns. On identical boot entries (the laptop, as safety read it) ostree takes the link-swap path, which renames the boot link after its last sync (deploy.c 2986-2997). Without the extra `sync`, a durable record could sit beside an order that was not yet durable.
  - **B4.** For each reorder, cut before the change, after it and before the record. Then take a default restart and a menu choice of each row. On each, `check` passes and every destination is one command away.
  - **E.** One hard reset (QMP) right after a reorder returns and before its record. The next start resolves it from real `rpm-ostree` and `bootc` output.

### Gap 3. HIGH: on plain Bazzite, one Bazzite update deletes both AresOS releases at the next shutdown, and the guide invites it

- **Gap.** 22c makes stock a place he visits and returns from, but nothing checks on stock that Bazzite's updaters stay off. `pause-stock-updates.sh` disables the timers persistently, but masks the services only with `--runtime`. `INSTALL-PROCEDURES.md:156` says to leave the updaters paused only "until the owner chooses stock permanently".
- **Sequence.**
  1. On `[R27*, R13, S]`: `at rollback`, `at reboot`. Stock runs: `[S*, R27, R13]`.
  2. On Bazzite's desktop he starts Bazzite's own system update, or re-enables its updater because he means to stay a while.
  3. It stages S2, with the booted stock as merge deployment.
  4. At any shutdown, finalize keeps the new, pinned, booted and merge rows (`ostree-sysroot.c` 2143-2185). The result is `[S2, S]`: R27 and R13 are deleted with their `/etc`.
  5. `at update` STOPs, and the tools refuse that list from then on.
- **Impact.** Both AresOS releases are gone, including the `ares` password, saved networks and layout. His home files, Windows and the pinned stock are untouched. Getting AresOS back needs Help. The trigger is an action outside the tools, but it is a natural one, and the guide's wording points to it.
- **Found by** safety 2. The chair confirmed the retention rule from ostree's source, and confirmed the runtime-only masks and the guide sentence. Which desktop actions start an update with the timers off is not confirmed (section 6).
- **Brief changes.**
  - **Section C.** "Keep stock", "Back to AresOS from stock" and the notice list say: "Never start a Bazzite update while AresOS is installed: it deletes both AresOS versions at the next shutdown." Delete "until the owner chooses stock permanently": choosing stock for good is step 9's abandonment.
  - **New rule A.10.**
    - On booted stock, `keep-stock` runs the existing `paused_state()` and STOPs when an updater timer is enabled or an updater unit is active.
    - `check` and `title` print the same finding as a warning line, with the next step "`at update` back to AresOS, then Help". They do not STOP, so that `at reboot` and the way off stock keep working.
    - `update` from stock is never blocked by it.
    - A staged deployment while stock runs gets its own STOP in every command: "A Bazzite update is waiting. Do not restart: the restart deletes both AresOS releases. Get help." It never suggests `rpm-ostree cleanup -p`.
  - **B1.** Stock booted with a foreign staged deployment, in each order, gives that message and no mutation.
  - **E4.** After the round trip, assert that the stock's updater timers are still disabled.

### Gap 4. MEDIUM: the model cannot see the journal's dead ends, and its fake ostree is not tied to real output

- **Gap.**
  - B2's events are whole commands, a restart and a menu choice. Cuts are tested one at a time in B4, never combined with restarts and menu choices. That is package 23's REVIEW-5 #4 shape.
  - The fake host logs `mutation=True` before the script's own checks run (`test_owner_update.py:216`). "A refusal leaves no mutation in the trace" therefore cannot tell a refused script from one that ran `set-default`.
  - The fake's `cleanup --pending` keeps every non-staged row (`:207-209`). rpm-ostree also removes unpinned rows listed before the booted one.
  - Nothing checks the fake against real three-row status output. The only fixtures are package 13's pairs.
- **Sequence.** Gap 2's sequence (rollback, a cut after `set-default`, a default restart onto stock) cannot occur in B2 as written. B2 passes, and the report claims "no dead end" while one exists. A fake finalize that wrongly keeps bootc's rollback row would make the model and `completion()` agree on a four-row state that ostree never produces.
- **Impact.** False assurance on the one proof the draft relies on for "no dead end".
- **Found by** architecture 2 and 4, and safety 4 (the cleanup picture).
- **Brief changes.**
  - **B2.**
    - The events are each command's phases (intent written, primitive done, record written), a power cut at each, a default restart, a menu choice of any row, and finalize when something is staged. The journal is state.
    - The invariant: from every reachable state, `check` passes, or its STOP names a next step that, applied in the model, reaches a state `check` accepts, with nothing deleted.
    - The model imports only the entry points under test and computes nothing with `owner.py` helpers (no `qualified_state` as its acceptance rule).
  - **The fake's ostree, from the sources above.**
    - `set-default` removes the index and inserts it at 0.
    - A write drops a staged row that is not first.
    - Finalize keeps new, pinned, booted, merge and other-stateroot rows in their old order.
    - The bootc slots follow `status.rs` 348-365.
    - `cleanup --pending` removes the staged row and every unpinned row before the booted one.
  - **"No mutation"** is judged by the fake's list, pins and BLS before and after, not by the trace.
  - **A fixture test.** Every rehearsal and probe stage commits its raw `rpm-ostree status --json`, `bootc status --json` and BLS listing. The fake must reproduce each (order, slots, `rollbackQueued`, pins, BLS identities), and a difference fails the package.
  - **`reconcile_update`** asserts that the staged row is the only row before the booted one before it calls `cleanup --pending`.
  - **B9 revert proofs:** a finalize that keeps the rollback row, a `set-default` that appends, and a side check placed before the journal resolution.

### Gap 5. MEDIUM: the reorder on three rows, and staging and finalize from the newly accepted orders, are walked late or not at all

- **Gap.**
  - Stage 1 rests on `set-default` with three rows and a pin, but that first runs in a VM in stage 2. Package 11 ran `default-stock.sh` only over a pair.
  - No VM has ever staged over three rows: package 27 staged over the pair. E never stages, because the target R27 is installed.
  - After `rollback`, restart, `update`, restart, the order is `[R27*, S, R13]`: `set-default` can move only one row to the front, so the stock ends up second. Rule 6 now stages from that order, which today's `qualified_state` refuses (`retained[-1] is stock`, `owner.py:636`).
- **Sequence.** With 22c's tools: `at rollback`, restart, `at update`, restart gives `[R27*, S, R13]`. With the next release's bundle: `at update`, `at reboot`. Finalize runs for the first time on an order with the stock not last. By source it gives `[R28, R27, S]`. Unwalked, its first real run is the owner's next update.
- **Impact.** The step that deletes would run first on his laptop. If `set-default` behaves differently than modelled, stage 1 and its review are redone after stage 2.
- **Found by** all three: OS reliability 4, safety 4, architecture 3 and 5.
- **Brief changes.**
  - **Stage 0 (new).** A probe dispatch before stage 1 is built: package 27's route to R27, then plain `ostree admin set-default` through all six orders of {R27, R13, S}, a default restart after each, and one GRUB choice. It captures the status JSON, BLS and ostree's `bootconfig swap: yes/no` journal line at every stage. These are gap 4's fixtures. Wire the harness lists first, as E already demands.
  - **E.** Save ostree's `bootconfig swap` line for every reorder, and say in the report which path each step took.
  - **Report and next brief.** The report lists "staging and finalize from `[R27*, S, R13]`" under "only the model covers". The integrator writes into the next update release's brief, as acceptance and as a laptop gate, and posts it on the board now:
    - its rehearsal stages from `[R27*, S, R13]` (reached by rollback, restart, update, restart) as well as from `[R27*, R13, S]`;
    - it expects `[new, R27, S]` by identity with the stock pinned;
    - it starts the stock row from the menu, then makes one reorder back.

    No staging can happen on the laptop before that release's bundle exists, so this closes the window whenever 22c's tools are installed.

### Gap 6. MEDIUM: the boot menu becomes the exit from a default that does not start, and it has never been used on the laptop

- **Gap.** Reorders become routine, and every exit from a default that does not start goes through GRUB. INSTALL-STATUS keeps "LOQ shortcuts and recovery menu" OPEN: "exact fresh-title GRUB selection … must work physically". The three rows differ only in `(ostree:N)`, and nothing schedules a calm first use.
- **Sequence.**
  1. With version 3 tools on the laptop: `at previous`, `at reboot`.
  2. R13 does not reach a login.
  3. He presses Esc for the menu: it never appeared on this laptop, or the keys do not move the selection.
  4. Every Linux system is out of his reach until Help. Windows still starts as the firmware default.
- **Impact.** No lockout from Windows, but no way back to any Linux by his own means. The first real menu use would happen during a failure.
- **Found by** safety 5 and architecture 10.
- **Brief changes.**
  - **Rule 8.** Every title also prints the row map for the next start, for example "(ostree:0) AresOS R27, starts next; (ostree:1) AresOS R13; (ostree:2) plain Bazzite". A menu choice is then never a guess.
  - **Section C (INSTALL-STATUS and the laptop record).** The 22c line may say "on the laptop" only after:
    - the menu proof: with nothing changed, the owner opens the GRUB menu once, reads the rows against the title's map and starts the default row;
    - then one calm round trip, with his OK: `previous`, restart, `update`, restart (AresOS to AresOS first), then `rollback`, restart, `update`, restart.
  - **EMERGENCY.** "Never choose a guessed GRUB title" becomes "choose the row the last title named".

### Gap 7. LOW: rule 9 conflicts with the journal fix and is stated for a transition the laptop may not make

- **Gap.**
  - "With the result version 2 would give" re-imports gap 1's STOP.
  - `system_ready()` judges the laptop with the *new* tools' `qualified()` (`owner.py:2168-2176`). Read literally, the repair cannot install from the very state it repairs.
  - The rule names version 2 to 3. The laptop may go from version 2 straight to the release bundle.
  - Nothing freezes the tools-update journal. Version 2's `settle_tools` reads it until publication, and accepts only `tools-update1` (`:2075`).
- **Sequence.**
  1. Before new tools arrive: version 2's `at previous`, restart, and a menu choice of stock. Version 2 STOPs.
  2. He installs version 3. `system_ready` runs version 3's `outcome`, which by rule 9 must give version 2's STOP.
  3. The update refuses, and he stays in version 2's dead end.
- **Impact.** It fails safe (nothing is installed, version 2 stays), but the fix cannot reach him.
- **Found by** architecture 6 and safety (answer to question 5).
- **Brief changes.**
  - **Rule 9.**
    - "…with the result version 2 would give, except where rule 5 resolves a record version 2 refuses: there version 3's rule applies."
    - Version 3 installs from the states where version 2 is stuck today (stock taken in the menu beside two releases; R13 after `previous`). B7 names each.
    - The tools-update journal stays `tools-update1` with its phases and fields. A B7 test runs version 2's `settle_tools` from `41b06513` on a journal version 3 wrote, at every cut before publication.
    - Every record version 3 writes carries `schema` and `mode` (staging or reorder). A record without `schema` is version 2's. Version 3 refuses an unknown schema with nothing changed.
  - **Board.** The next release's brief states the same rule against the installed fingerprint `851eb742…` (or 22c's, if installed), and its tools version is 4.

### Gap 8. LOW: `update` from the older release removes the newer one, and the new release starts from the older one's settings, without saying so

- **Sequence.**
  1. `at previous`, restart: R13 confirmed, `[R13*, R27, S]`.
  2. The next release's bundle: `at update` stages R28 over R13.
  3. At shutdown the list becomes `[R28, R13, S]`. R27 is deleted, and R28's `/etc` is merged from R13's, so the `ares` password set on R27, its networks and its layout are gone.
  4. From `[R27, R13*, S]` (R13 taken in the menu), the same word only reorders to R27.

  Version 2 already allows this. 22c makes it a documented destination.
- **Impact.** A surprise, not a lockout: `ares-recovery` exists on every system. Usually he left R27 because it was bad, and then removing it is right.
- **Found by** safety 6 and architecture 8.
- **Brief change.** This is owner decision 5. With the recommended answer, rule 6's line has two parts: "<R27> is removed when the update finishes at shutdown. The new release starts with this system's settings (Wi-Fi, passwords, layout), not <R27>'s." The guide says the same, and B5 gets a staging test from `[older*, newer, S]` that asserts both lines.

### Gap 9. LOW: rule 7 does not say that `layout begin` refuses on stock

- **Sequence.**
  1. `at rollback`, `at reboot`.
  2. On stock: `at layout begin us`, the tty4 proof, then `at layout finish`.
  3. The stock's `/etc/vconsole.conf` and X11 keymap are rewritten. Today `preflight_recovery(keep=False)` refuses this (`owner.py:568`), and rule 7 drops that check.
- **Impact.** The fallback loses the German layout every guide promises for it, so his password lands on other keys there.
- **Found by** safety 7.
- **Brief change.** Rule 7 adds: "`layout begin` on booted stock refuses with nothing changed." B6 adds that case.

### Gap 10. LOW: a layout finish cut by power and abandoned on another system leaves the original AresOS with a mixed layout that no command repairs

- **Sequence.**
  1. On R27: `layout begin us-intl`, the proof, then `layout finish`.
  2. Power is lost after `set-keymap` and before `set-x11-keymap`.
  3. He starts stock from the menu and runs `layout abandon`. On another deployment it clears `layout-pending.json` without restoring anything (`owner.py:1806-1821`).
  4. `at update` and a restart bring back R27, whose console is now us-intl and its X11 German.
  5. `layout begin` STOPs with "Unsupported finished system layout; get help" (`:1770`), and `layout abandon` has no record.
- **Impact.** Narrow, and nothing is deleted. But the next step is Help, and the console and greeter layouts differ. 22c's return from stock makes the sequence reachable.
- **Found by** OS reliability 3, rated medium. The chair rates it low: it needs a cut inside a window of milliseconds plus three deliberate steps.
- **Brief change.** Rule 7 adds: "A trial whose finish began (`finishing`) and that is abandoned on another system leaves a repair note bound to the trial's deployment. When that deployment runs again, `layout abandon` restores the recorded old settings." B6 adds: cut between the two writes, abandon on stock, return, abandon restores, and a new trial then works.

### Gap 11. LOW: smaller contradictions in the brief that would stop or mislead the builder

- **The B8 list.** `test_shell_assertions.py:156-157` compares the payload's `default-stock.sh` with the repository copy. Part D removes it from the payload, B8 does not list it, and AGENTS rule 5 then forbids changing it. *Change:* add it to B8, with "the payload no longer carries the three old scripts; the repository copies stay byte-identical".
- **Stage 1 acceptance.** It requires a hosted `checks_only` run, which is a `workflow_dispatch` input of `os-image.yml`, but also says "dispatch nothing". *Change:* "dispatch no rehearsal".
- **B3.** "A list that changes between the read and the write makes no `ostree admin` call" cannot be met by a CLI call. *Change:* "the script re-reads immediately before the call and checks the result after it". The remaining window is known limit 1.
- **Rule 4 and `previous`.** Rule 4 does not say that `previous` works on stock, yet `update` from stock always picks the newest release, so `previous` is the only word to R13 from there. *Change:* "each word works from every system, stock included; every PASS line names the release it selected".
- **The message rule 4 keeps.** "Rollback would select the other deployment" is no longer the reason. *Change:* reword it to a reason that is true with `set-default`.
- **Found by** architecture 9 and safety (known limit, and answer to question 3).

**Dropped for want of a failing sequence:** architecture 11, that rule 3's "BLS equal" does not compare each entry's options. Neither write path rebuilds options; both reuse each deployment's bootconfig. Comparing "options by identity before and after, apart from `ostree=`" is still a free strengthening of rule 3's postcondition, and the integrator may add it.

## 3. Known limits the council accepts

1. **The index window in `set-default`.** A deployment staged between the script's read and the write shifts the index. ostree then moves the wrong row and silently drops the staged one; the postcondition STOPs after the write. *Why accepted:* the updaters are paused, the owner lock and `idle` check run first, and the window is milliseconds. Every row stays bootable, and the opposite command resolves it.
2. **Finalize's early prune with a nearly full `/boot`.** A cut between the prune and the write leaves a valid pair that the journal refuses (rule 5 (d)). *Why accepted:* it needs a nearly full `/boot` (safety read 14% used on the laptop) and a cut in a short window. It fails safe: a STOP, with a bootable system.
3. **A modified running AresOS blocks the way out of it.** A layered or overlaid running AresOS makes rule 1 refuse `rollback` too. *Why accepted:* it needs his own `rpm-ostree` action, a transient overlay is gone at the next restart, and widening rule 1 is never the safe default.
4. **The cause of a start that was not the default cannot be told.** It may be a menu choice, version 2's queued rollback, a Help-session `bootc rollback`, or firmware or GRUB ignoring the order. *Why accepted:* no decision depends on the cause, and gap 1's neutral line states only facts.
5. **Identical GRUB titles.** *Why accepted:* changing them is an image change and out of scope. The title's row map (gap 6) removes the guessing.
6. **Each system keeps its own `/etc`.** Passwords, Wi-Fi and layout differ between R27, R13 and stock. *Why accepted:* it is how ostree works. One line in the guides, which draft section C already mostly has.
7. **The residue of gap 3.** He can still start a Bazzite update and restart without typing a tools command. *Why accepted:* after the guide line and the checks it needs a deliberate act against the guide. Pinning the AresOS releases while stock is the default would change rule 1, and is a separate decision.
8. **No cancel before the restart** (already decided). He restarts and uses the opposite command. *Why accepted:* with gaps 1 and 2 fixed, that always works.
9. **No staging from stock.** *Why accepted:* finalize would keep only the new release and stock. `update` from stock reorders only, and says when the bundle's release is newer still.

## 4. Decisions for the owner

1. **Should `at update` always take you to the newest AresOS already on the laptop, without a download?** That covers going forward again after `at previous`, and coming back from plain Bazzite.
   *Recommendation: yes.* It is the only one-command way back from plain Bazzite. It needs no internet or sign-in, because that release was checked when it was installed. If no, plain Bazzite stays a one-way door except through the boot menu.
2. **When should the repaired tools go on your laptop?** Either on their own, soon after this package passes (one USB-stick session, no change to the system itself), or together with the next AresOS release.
   *Recommendation: on their own, first.* Each laptop session then changes one thing, and your ways back (rollback to Bazzite, forward again) work before the next release instead of after it. The next release then updates tools that this package rehearsed. This changes the draft's assumed answer ("with the next release").
3. **Will you do one calm test on the laptop before relying on the new ways back?** Open the boot menu once and check it against the title. Then go to the older AresOS and back, then to plain Bazzite and back: about half an hour and four restarts.
   *Recommendation: yes.* The boot menu and plain Bazzite as a default have never been used on this laptop, and the first time should not be during a failure. The test changes which system starts on your disk, which is why it needs your OK.
4. **Plain Bazzite must not update itself while AresOS is installed.** A Bazzite update would delete both AresOS versions at the next shutdown. Is it OK that Bazzite stays frozen, with a warning in the guides and in the tools?
   *Recommendation: yes.* Stronger protection (marking the AresOS versions as protected whenever Bazzite is the default) can come later if you want to stay on Bazzite for longer periods.
5. **If you went back to the older AresOS and a new release then arrives, what should `at update` do?** By default it installs from there: the newer one you left is removed, and the new release starts with the older one's settings, so you set your password and Wi-Fi again. The alternative is that `update` first takes you back to the newest one.
   *Recommendation: keep it as it is, with both facts printed before you restart.* You usually left the newer one because it was bad, so removing it is right.

## 5. One package or two?

**One package, in three stages.** Add stage 0, the probe of gap 5, before stage 1 is built. It costs one of the four planned dispatches (about two to three hours on free runners) plus wiring the harness lists earlier, which E needs anyway.

- Do not cut into two packages. The journal rewrite (gaps 1 and 2) cannot be separated from the reorder mechanism: the mechanism without it adds more ways into the dead end. Accepting the new states without the commands gives no new way back.
- Cutting "boot-menu states and the return from stock" into a second package (safety's fallback) would keep stock a one-way door for another package. It would also cost a second brief, review and rehearsal, for little less risk: the risky part, the reorder and its journal, stays in the first half.
- Part F stays. It is test-only, in the same file, and its phase table matches `update_tools` as the chair read it.
- If the owner answers no to decision 1, the cut is the one the draft already describes: drop the stock rows of rule 4's `update` and the returns in steps 4 and 6.

## 6. Claims the chair could not confirm

- **Safety's read of the laptop's boot entries:** same kernel and initramfs, options identical apart from `ostree=`, titles `Bazzite (ostree:N)`, bootloader `none`, `/boot` 2.0 GiB with 14% used. Not re-read, because the chair does not touch the running system. Gap 2's `sync` line and known limit 2 rest on it, but the fixes hold whichever ostree path a reorder takes.
- **That `rpm-ostree cleanup --pending` removes every unpinned row listed before the booted one.** Safety read it at upstream `main`, not at the laptop's version, and no copy is retained here. It matches the chair's memory, and gap 3's "never suggest it" holds either way.
- **Which Bazzite desktop actions start an update while the timers are disabled.** Safety says this comes from memory. Gap 3's likelihood depends on it; its mechanism does not.
- **Safety:** that bootloader `none` gives ostree no backend (memory), and that a killed `ostree admin` cannot leave `/boot` frozen (not re-read).
- **Architecture:** that the pin lives in the origin file and that `write_deployments` never writes origins (the pin's location is from memory). Also bootc `deploy.rs` (rollback, and staging's merge deployment), which was not re-read. Rule 3's postcondition (stock still pinned) catches a pin change either way.
- **OS reliability's in-memory probes.** Not run. Both results follow from the code: `owner.py:1161-1166`, and `:1770` with `:1806-1821`.
- **Architecture's references** to board #196 and to the registry and signing needs of a throwaway release in E: not checked.

**The planner's unproven points, after this council:**
1. `set-default` on three rows with a pin: consistent with source. Proving it in a VM is stage 0.
2. Finalize keeps the new, booted and pinned rows in every accepted order: confirmed from ostree's source. The walk belongs to the next release (gap 5).
3. "This boot's journal can always tell a waiting change from a menu choice": not true in general. See gap 1's neutral line and known limit 4.
4. Part F's table matches `update_tools` as the chair read it. `system_ready` and `installed_commands` run only before the journal and at copy and publish; `disk_record` runs at every cut; the stick identity is compared at cuts 1 to 9; `.update-tools` never exists at a cut.
5. Sizes and run times were not checked.

GAPS-FOUND (11)
