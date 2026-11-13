# Council question: package 22c, every way back works after an update

Date: 2026-11-13. Convened by the integrator before the brief is frozen (`docs/WORKFLOW.md`, step 2: a council on the brief for risky or foundational packages).

## What is reviewed

The draft brief `BRIEF-DRAFT.md` in this folder. It is a plan, not a diff: nothing has been built. A planning agent (Claude, Fable 5.2) wrote it on 2026-11-13 after reading the owner tools, their tests, the rehearsal harness and the upstream sources of bootc 1.16.13 and ostree 2026.4.

## What depends on it

The owner's laptop runs release 27 since 2026-11-13, with release 13 as its rollback and the corrected stock Bazzite pinned: three deployments. With the tools installed there (version 2, fingerprint `851eb742…`):

- `at rollback`, `at keep-stock`, `at layout begin` and `at layout abandon` refuse (`preflight_recovery` wants exactly two deployments);
- stock chosen in the boot menu makes `check`, `title` and `reboot` refuse, with two deployments as well, because bootc reports `rollbackQueued` whenever the booted deployment is not first;
- after `at previous` there is no way forward again (`update` says the target is already deployed, `previous` says the other release is newer).

His ways back today are `at previous` (one way) and F12 to Windows. 22c repairs this in the tools, and its bundle is the next thing that changes how his laptop chooses what to boot. It must be on main before the second update release.

## The draft's answer

Three options were weighed:

- **A, patch each case:** allow three rows in the recovery preflight, add a path to stock, add a forward branch. Smallest diff; stock stays a one-way door, boot-menu states stay refused, and it would be the third time the tools produce a state their own commands refuse.
- **B, keep "stock last" as an invariant:** `bootc rollback` between AresOS releases, `ostree admin set-default` only towards stock. It cannot return from stock.
- **C, the draft:** the set of installed systems is checked as today, but any order of it is accepted; one reorder operation, resolved by identity and done with one `ostree admin set-default`, serves every command; every change is journalled and confirmed after the restart; each command word names a destination; a model test walks every state and command and proves there is no dead end. Staging a new release stays as strict as today.

## What the planner did not prove

- That `ostree admin set-default` behaves on three deployments, one of them pinned, as its source reads. It has never run that way in a VM here. The current tools use `bootc rollback`, which is rehearsed.
- That ostree's finalize at shutdown keeps exactly the new, the booted and the pinned deployments in every order the draft now accepts.
- The claim that this boot's journal can always tell "a change waits for the restart" from "this start was chosen in the boot menu".
- The table in part F (which injected refusal runs at which cut).
- All sizes and run times.

## Read

- `BRIEF-DRAFT.md` (this folder), fully.
- `os/owner-tools/owner.py`: `qualified_state`, `preflight_recovery`, `recover`, the `update`, `previous`, `completion` and layout paths, and the journal they use.
- `os/release/rollback.sh`, `default-stock.sh`, `previous.sh`.
- `os/tests/test_owner_update.py` (the state model and the refusal invariant), `os/tests/test_default_stock.py`.
- `docs/INSTALL.md`, "Update AresOS to a new release"; `docs/EMERGENCY.md`, "Failed or bad update"; `docs/INSTALL-PROCEDURES.md` for rollback, keep-stock, the recovery menu and layout trials.
- `reviews/22-update-route/REPORT.md` and `reviews/27-first-update-release/REPORT.md`: the judgment calls and known limits (read the sections you need; both are long).
- `docs/design/OS-BASE.md`, the sections on updates and recovery.
- Upstream behaviour where you rely on it: say whether you read source, documentation, or reason from memory.

## Questions

1. **The mechanism.** Is one reorder by `ostree admin set-default` on an identity-checked index the right single mechanism, or should `bootc rollback` stay for the cases it already serves? What can each do to the pinned stock, to a staged deployment, to `/etc` merges and to the boot entries that the draft's postconditions would not catch?
2. **Accepting any order.** Does accepting every order of the checked set, including a start chosen in the boot menu, open a state from which a later `update` (staging, then finalize at shutdown) deletes a deployment the owner still needs, or leaves him on a system with no working way back? Name the sequence.
3. **Destinations.** `update` from stock goes to the newest installed AresOS by reorder only; staging from stock stays forbidden. Is that the right line? Is there a sequence where the word does something the owner would not expect from its name?
4. **The journal.** Is "journal the intent, change, record, confirm after the restart" sufficient for `keep-stock` when the target is the booted system, and for a power cut during the one write? What does he see at the next start in each case, and can he always get out?
5. **Tools version 2 to 3 on the laptop.** The new tools must read version 2's records and accept every state version 2 accepts. What is missing from that rule?
6. **Evidence.** Do the six rehearsal steps and the model test cover what matters, given that the model's transitions are only as true as its picture of ostree and bootc? Which transition must be walked in a VM that the draft leaves to the model? What can only the laptop prove, and is the order "rehearse, review, then his laptop" enough for it?
7. **Size.** One package in two stages, or two packages? Where would you cut, and what is the cost of each cut?

## The bar

The owner's bar (2026-11-11): reasonably safe, like any existing CLI, not "nothing could ever go wrong". Extra care applies here, because this is updates, rollback and the boot order on his real disks: a lost way back, a deleted fallback, or a laptop that cannot start anything of his must not happen. A narrow case that fails safe (a refusal with nothing changed and a clear next step) is a known limit, not a gap.

Report only real gaps, most severe first, each with a concrete sequence of commands and restarts where it breaks.

## Planner material (not part of the repository's sources)

`planner-material/` in this folder holds what the planner fetched or wrote: bootc 1.16.13's `status.rs`, ostree 2026.4's `ot-admin-builtin-set-default.c`, and `shapes.py`, the read-only script that ran today's `qualified_state` and `preflight_recovery` over every pair and triple ordering. Check them like any other claim.
