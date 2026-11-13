# 22c: every way back works after an update

Empire board brief NNN (the integrator takes the number). Owner tools, guides and a VM rehearsal. Starts after 27b merges: both touch the update row of `docs/INSTALL-STATUS.md`, `os/tests/test_owner_path.py` and `os/manifest/ci/16/pending-rebind.json`. Must be on main before the second update release (packages 23 and 21b).

> **DRAFT. Three lines below are assumptions until the owner answers (marked OWNER in "Already decided").** The integrator replaces them before committing.

**Goal:** After an update the owner can always choose which installed system starts next, with one command each and a confirmation after the restart: the newest AresOS (`at update`, also forward again after `at previous`, and back from plain Bazzite), the AresOS before it (`at previous`), or plain Bazzite (`at rollback`, or `at keep-stock` after choosing it in the boot menu). Keyboard-layout trials work again. No command of the tools leaves a state that the other commands refuse.

## Today (read on main `25b7c8a6`; the laptop checked read-only on 2026-11-13)

- The laptop: R27 booted, R13 second, the pinned stock third, nothing pending. Installed tools: version 2, fingerprint `851eb742…` (the payload at `41b06513`). bootc 1.16.13, ostree 2026.4.
- `rollback`, `keep-stock`, `layout begin` and `layout abandon` STOP with `Expected exact stock/AresOS pair`: `preflight_recovery` requires two deployments (`owner.py:572`).
- Stock chosen in the boot menu: `check`, `title` and `reboot` STOP (`qualified_state`, `owner.py:646`), and `keep-stock` STOPs with `Pending deployment or rollback` (`:571`). With two deployments it is the same (`Wrong queued rollback`, `:642`). bootc reports `rollbackQueued` whenever the booted deployment is not first (`status.rs` at v1.16.13: `rollback.index() < booted.index()`), so that flag cannot tell a boot-menu choice from a queued rollback. No VM run has typed `keep-stock` after a boot-menu choice: qualification 21 typed it after a normal rollback, and package 11's Part B ran `default-stock.sh` directly.
- After `at previous`: `update` STOPs with `Target release is already deployed; get help` (`:1399`), and `previous` with `The other AresOS is newer; previous only returns from an update` (`:1628`).
- `qualified_state` accepts 4 of the 18 combinations of order and booted system for {newer AresOS, older AresOS, stock}.
- `test_owner_update.py:1254-1259` swallows the injected refusal (`except refusal: pass`) and never asserts it.

**In scope:**

### A. One rule (`os/owner-tools/owner.py`, one new release script)

1. **What may be installed** stays as reviewed: exactly one corrected stock with the saved identity, pinned, its reference and digest unchanged; one or two AresOS releases from the tools' history, each unpinned, unmodified and with its exact reference, no digest twice; during an update, one staged target in front. Everything else STOPs as today (an unknown or pinned release, an unpinned or changed stock, a third AresOS without a stage, two staged rows, a foreign deployment).
2. **Order is free; only "first" matters.** Any order of that set is accepted. The first deployment starts next. When the booted one is not first, exactly one of two things is true and the tools say which: this boot's journal recorded exactly this list (a change waits for the restart), or no journal covers it (this start was chosen in the boot menu). `rollbackQueued` alone proves neither.
3. **One reorder operation**, used by every command that changes what starts next:
   - Preflight, read-only: no layout trial, `idle`, the disk record, an accepted list with nothing staged and no change waiting, no unresolved journal (the same command may continue its own, as today), BLS entries equal to the deployments, and the target found exactly once by its saved identity (stock) or its history digest (AresOS), unmodified.
   - Journal the intent. Then one script (`os/release/start-next.sh`, or a name you justify): it reads the list again, finds the target's index by checksum and serial, asserts its digest and reference, runs `ostree admin set-default <index>` once and asserts the result.
   - Afterwards: the same identities and flags as before, the target first, the others in their old relative order, stock pinned, BLS equal. Then the record and a fresh title.

   It never creates or removes a deployment and never touches a pin, kernel arguments or any `/etc`. `bootc rollback` leaves the tools.
4. **Each word names a destination.** The tools work out whether that needs a download, a reorder or nothing:

   | Command | Destination |
   |---|---|
   | `update` | The newest AresOS. If the bundle's release is installed: the reorder (no network, no login, no cosign; its digest is the history's). If it is not installed and an AresOS is running, first and with nothing waiting: staging, as today. Otherwise (on stock, or on a system chosen in the boot menu): the newest AresOS that is installed, by reorder only; say so when the bundle's release is newer still. |
   | `previous` | The older of two installed AresOS releases. |
   | `rollback` on AresOS, `keep-stock` on stock | The pinned stock. Each keeps refusing on the other side with its present message. |

   A destination that already runs and is first changes nothing and says so. `login` on AresOS refuses when `update` would need no download.
5. **Every change is journalled and confirmed.** `rollback`, `keep-stock` and the reordering `update` use the journal `update` and `previous` use today: the intent before the change, the record after it, `check`, `title`, `records` and `reboot` STOP on an unresolved one, and `title` confirms after the restart with one line. `completion()` derives the expected list from identities (after staging: the new release, the running one, the stock), never from positions. When the target is the booted system (`keep-stock` after a boot-menu choice) nothing waits for a restart; record it anyway, and let the first check after the next start confirm that the laptop started it.
6. **Staging stays strict:** only from a running AresOS that is first, with nothing staged or waiting and no modified deployment; never from stock. The line that names the release removed at shutdown names the other AresOS, whichever it is (today it says "Older AresOS" for `retained[1]`, `owner.py:1521`).
7. **Layout trials.** `layout begin` needs an accepted list, the booted system first, nothing staged or waiting and a clear journal. `layout abandon` needs an accepted list with nothing staged, on whichever system is booted, stock included; a trial still belongs to the deployment it began on. Neither uses the pair check any more.
8. **What he reads.** Every title prints two plain lines: which system runs, and which starts next; and "this start was chosen in the boot menu" when that is so. STOP texts name the next step. Keep every PASS line the guides quote unless this brief changes its meaning; list each changed line in the report.
9. **The laptop's tools.** Tools version 3 with the unchanged history: the target stays R27. Version 3 accepts every state version 2 accepts, and reads version 2's records (`outcome-pending.json` in both statuses, `title.json`, `prepared.json`, the layout records) with the result version 2 would give.

### B. Tests (`os/tests`)

1. **Shapes:** all 4 pair and 18 triple combinations, each without a journal, with this boot's journal and with an earlier boot's, accepted or refused exactly by rule 2. Every wrong shape that rule 1 still forbids keeps refusing.
2. **A model over the whole state space**, as package 23's review fixes 4 built for its hand-off. From the laptop's list and from the pair, apply every command, a restart (the first deployment boots) and a boot-menu choice (any deployment boots) until no new state appears. For every step: a refusal leaves no mutation in the trace; a change meets rule 3's postconditions. For every state reached: `check` and `title` accept it, and each installed system can be made the next start by one command. The expected result of a step comes from the model's own rules, never from the tools' return values.
3. **The reorder script** against a modelled list, as `test_default_stock.py` does: a wrong identity, digest or reference, a staged row, a missing or doubled target, or a list that changes between the read and the write makes no `ostree admin` call; a wrong list afterwards fails.
4. **The journal** for each new use: interrupted before the change, after it, at the status read and at the record write. `check`, `title`, `records` and `reboot` refuse, the same command continues, and a restart that lands elsewhere STOPs.
5. **Staging:** refused on stock, on a boot-menu choice and with a change waiting; `completion()` right when the stock sits in the middle of the list.
6. **Layout:** begin and abandon with three deployments; begin refused with a change waiting; abandon on stock chosen in the boot menu.
7. **Tools 2 to 3:** the tools update over every accepted resting state; the "accepts everything version 2 accepts" rule; version 2's records. Load version 2's code from `41b06513`, as the release-13 tests load older tools.
8. **Expectations that change on purpose:** tests that pin today's refusals (for example `test_recovery_and_layout_pair_accepts_any_known_release_but_only_the_pair`; the `stock not last`, `stock booted beside two releases` and `running not default` cases; the direction refusal of `previous`; the rehearsal's `previous-13-update-refused`). List each in the report with the rule that replaces it. Apart from these, AGENTS rule 5 holds.
9. **A revert proof per rule:** name the assertion that fails when the rule is taken out.
10. The route and binding tests pass: `test_owner_path`, `test_owner_equality`, `test_owner_walk` (with the local walk of the new route), `test_owner_commands`, `test_owner_retained`, `test_owner_tools`, `test_owner_abandon`, `test_checkout_sources`, `test_owner_step_limits`.

### C. Guides (phone-readable boxes, PASS, STOP and a return in each, the existing style)

- `docs/INSTALL.md`, update route: the paragraph on three deployments says what works now; the "misbehaves" box gains forward again with `at update`; one line for a tools-only update (the Windows box and the tools box, nothing else); the fingerprint in both copy checks and both bootstrap blocks.
- `docs/INSTALL-PROCEDURES.md`: later layout (each installed system keeps its own layout); recovery menu (three rows that differ only in `(ostree:N)`; a wrong choice is harmless, because `check` says what runs and what starts next); rollback and keep-stock beside two AresOS releases; a new short "Back to AresOS from stock".
- `docs/EMERGENCY.md`, "Failed or bad update": previous first, then rollback, then Windows; the sentence that they refuse with three deployments goes.
- `docs/INSTALL-REFERENCE.md`: the quoted tool messages that changed.
- `docs/INSTALL-STATUS.md`: the update row and a 22c line: built, rehearsed (run link), **not on the laptop**, whose tools stay `851eb742…` until the owner installs newer ones. "LOQ shortcuts and recovery menu" stays OPEN.
- With the old tools these procedures STOP with `Expected exact stock/AresOS pair`. The guides say that this line means "install the current tools first".
- Say what he will notice: plain Bazzite has no `ares` account and keeps German; the AresOS from before the update has no `ares` password and no admin rights; the files in his home stay.

### D. Bundle and bindings

- `bundle.py`: the new script in, the scripts the tools no longer use out. `os/release/rollback.sh`, `default-stock.sh` and `previous.sh` stay in the repository byte-identical: older CI modes read them (`keyboard_vm.py:283`, `switch_vm.py:535` and `:547`, `two_disk_vm.py:669`).
- `python os/owner-tools/bundle.py --refresh`; the new fingerprint in `docs/INSTALL.md` (four places), `commands.json`, INSTALL-STATUS and this package's report, as PR #22 and package 27 did.
- Bound files that change get exact hashes in `pending-rebind.json` from `checkout_sources.records` until the rehearsal rebinds them. Never edit walk tables by hand.

### E. VM rehearsal (the two-disk harness; a new mode on this branch, package key `22c`)

Start from the laptop's history: package 27's route unchanged up to R27 confirmed and `sudo passwd ares` (the 15f tools `3ef85c4a…`, then version 2 from `41b06513`). Then, typed as the owner types, with package 11's protected-disk audits after every boot and every stage's list compared by identity (nothing created, nothing removed, stock pinned):

1. R27: this package's bundle through the guide's bootstrap (version 2 to 3, the first update of a versioned toolset in a VM); `check`, `title`.
2. R27: a layout trial to US International (begin, tty4 proof, finish), restart, typing proof; back to German the same way; one trial ended by a hard reset and `layout abandon`.
3. `previous`, restart, R13 confirmed. `update` there with the network off, restart, R27 confirmed; his password from the start still passes `sudo -v`.
4. `rollback`, restart, stock (greeter, German login), confirmed; `rollback` refused there with no mutation; `keep-stock` changes nothing; `update`, restart, R27 confirmed with the stock now second.
5. From that order: `previous`, restart, R13; `update`, restart, R27.
6. The boot menu: `title`, restart, choose the stock row in GRUB by its title (package 11's `select_grub_menu`, adapted to three rows); `check` says the start was chosen in the boot menu; `keep-stock`; restart with no choice: stock again, confirmed; `update`, restart, R27.

End on R27. Evidence under `reviews/22c-ways-back-after-update/runs/`: the result file, the transcript of every typed command, each stage's list, the audits. The run records its bound sources; a rebind step writes `os/manifest/ci/22c/source-bindings.json` and empties the pending list.

Wiring: extend every list that names packages 14, 16 and 27 (the workflow, `owner_media.require_runner`, `registry_auth`, `rehearsal_guard`, `rehearsal-packages.json`, `installer_webui`, `two_disk_vm`, `owner_vm`, `owner_capabilities`, `owner_devices`) and the tests that guard them (`UpdateJobGatesTest`, `OwnerHarnessPackagesTest`, `VmStepDecisionsTest`) before the first dispatch. Package 27's first two rehearsal runs died on such lists.

Budget: the repository is public, so standard runners cost nothing. Plan one checks-only run and at most four rehearsal dispatches, 1200 minutes in all; report before dispatching more. A run should take about 3.5 hours (an estimate: package 27's passing run took 109 minutes); raise the step and job bounds on purpose.

### F. The refusal invariant (PR #37, REVIEW-1)

In `test_invariant_one_working_toolset_after_any_interruption_and_any_refusal`:

- Give every cut and refusal an expectation derived from the journal phase the cut leaves (copy after renames 1 and 2, publish after 3 to 5, retire after 6 and 7, records after 8 and 9, complete after 10), written as a table in the test. Where the injected check runs, both attempts raise the expected refusal with its message and leave the phase unchanged. Where it does not run, assert what happens instead (the update completes; the next run says `Tools already installed; nothing changed`).
- The integrator's reading, to check and not to copy: the `system_ready` checks (layout trial, transaction, the failing `observations`) and `installed_commands` run only in copy and publish; `disk_record` runs at every cut; the stick identity at cuts 1 to 9; the staged-bundle injection changes nothing at any cut, because `.update-tools` exists only between the copy and rename 2. No row may stay empty like that: make the injection real (for example a changed `tools-<fingerprint>/owner.py` before publication) or cut inside the copy.
- Revert proof: with the layout-trial check taken out of `system_ready`, the test fails at cuts 1 to 5.

**Out of scope:**

- The image, `os/manifest/release.json`, the records in `history.json`, any publish, any new release, and the masks of the two finalize units (the next release).
- Installing this bundle on the laptop, and anything typed on the real laptop.
- Staging from stock, a command that cancels a waiting change, and new command words.
- Different boot-menu titles (an image change).
- `os/config`, `os/build.sh`, the desktop supervisor (package 23), backlight and power button (21b), `at logs`, `OwnerTools.psm1`.
- `STATE.md` and `HANDOFF.md` (the integrator).

**Acceptance:**

Two stages, one PR. **Stop after stage 1 and report; dispatch nothing until the integrator sends the tools review's verdict.**

- **Stage 1 (A to D and F):**
  - every test in B and F, with the count of each focused module, plain and `-B`;
  - `test_owner_update` with 0 skipped namespace tests, and where that ran;
  - a hosted `checks_only` run passing on the pushed head;
  - the fingerprint equal in every pin, and the pending list exact;
  - `git diff main --stat` shows no file outside this brief.
- **Stage 2 (E):** one rehearsal run passes steps 1 to 6 on the reviewed head with every audit unchanged; its result file is committed; the bindings are rebound; the INSTALL-STATUS row carries the run link.
- **`reviews/22c-ways-back-after-update/REPORT.md`** in the AGENTS format, with:
  - the table of every state and command from the model;
  - the changed test expectations and the changed PASS and STOP lines;
  - the revert proofs;
  - which transitions the VM walked and which only the model covers;
  - the known limits (what it is, the harm, why it is accepted);
  - the budget table and every JUDGMENT-CALL.

**Where tests run.** The builder works on the owner's laptop, which has the real `rpm-ostree`, `bootc` and `ostree`. The suite was written for WSL and the hosted runner, where they don't exist: `reached()` in `test_owner_update.py` uses `Required tool missing: rpm-ostree` as its marker. So the real-entry tests can't pass natively here, and nobody has shown what the rest does beside real tools. Run the owner-tools modules in a container that has user namespaces and none of those binaries, or on the hosted runner, and say in the report where each count comes from. One suite at a time: the owner uses the laptop, and package 23 tests on it.

**Already decided:**

- Rollback, keep-stock, previous and the reordering update never create or delete a deployment. The stock is never unpinned, never modified, and its `/etc` is never written.
- One mechanism for every reorder: `ostree admin set-default` on an index resolved by identity. (The council on this brief may reopen it.)
- The words stay `update`, `previous`, `rollback` and `keep-stock`, each with one destination. **OWNER (assumed yes):** `at update` also goes forward to a release that is already installed, and returns from stock.
- **OWNER (assumed yes):** the tools can bring him back from stock to AresOS. If he says no, drop the stock rows of rule 4's `update` and step 4's and 6's return; the model then records stock as a state with no way back.
- **OWNER (assumed "with the next release"):** this bundle is rehearsed as a tools-only update but not installed on the laptop by this package.
- A later update removes the other AresOS at shutdown (package 22's JUDGMENT-CALL 1, board #154).
- Going forward to an installed release needs no network and no new signature check.
- No change can be cancelled before the restart; he restarts and uses the opposite command.
- The bar (owner, 2026-11-11): reasonably safe, like any existing CLI; extra care for updates, rollback and disks. A narrow case that fails safe is a known limit for the report, not a reason for another mechanism.

**If unsure:** refuse with nothing changed and a message that names the next step. Leave the stock alone. Claim less in the guides. Widening rule 1 or rule 6 is never the safe default. Record the question as a JUDGMENT-CALL or PLAN-GAP.

**Model:** Builder: a Claude agent on Fable 5.2 for stage 1 (the owner tools' state machine on his real disks; CLAUDE.md's rule for hard AresOS tasks). Stage 2 may run on Opus with a fresh context, and goes back to Fable if two runs fail inside the new steps. Review: fresh, never the builder: Codex gpt-6-astra (high) while it is available (it ends on 2026-11-21), otherwise a Claude agent on Fable 5.2, because updates and rollback are the high-stakes class. The final review before this bundle reaches the laptop is Fable's.

## Rules

- `AGENTS.md` applies. Push `pkg/22c-ways-back-after-update` and open a PR. Never merge, never push to `main`, never `--no-verify`.
- The repository is public: no personal data, serials, GUIDs, emails or tokens.
- Never run the owner tools, `rpm-ostree`, `bootc`, `ostree admin`, `systemctl reboot`, `loadkeys` or `localectl` against this laptop. Don't touch other worktrees.
- Commits end with `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>` (or the model that wrote them).
