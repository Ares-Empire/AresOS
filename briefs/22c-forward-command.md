# 22c: one word per meaning, `forward` beside `update`

Follow-up to `briefs/22c-ways-back-after-update.md`, on the same branch, before stage 2. Integrator's decision of 2026-11-14.

**Why.** Reviews 4, 5 and 6 each found a recovery route in the guides that could go wrong, and all three came from `update` having two meanings: install the tools' release (staging, which at shutdown removes an older AresOS) or select the newest installed AresOS (a reorder that never removes anything). Which one happens depends on state the owner cannot see from `check` or `title`. REVIEW-6 (gpt-6-astra high, SAFE on `1e0f67da`) says the guides are now right but the interface stays fragile, and that a separate word that can never stage would remove the class. The guides are what he follows during a failed update, so the class goes.

**The rule (replaces the destination table of rule A4 and `briefs/22c-b2-destination-invariant.md`):**

| Command | Destination | Never |
|---|---|---|
| `update` | The tools' release, by staging, exactly as today's staging rule: only from a running AresOS that is first, nothing staged or waiting, the tools' release newer than every installed AresOS and not installed. | Selects an installed system. In every other state it refuses with nothing changed and names the next step: `forward` when a newer installed AresOS exists or stock runs; "nothing to do" when the tools' release already runs and starts next; Help otherwise. |
| `forward` (new) | The newest installed AresOS, by the identity-checked reorder of rule A3, journalled and confirmed like every reorder. From anywhere: plain Bazzite, the older AresOS, a start chosen in the boot menu. No network, no login, no signature check (the release was checked when it was installed). If it already runs and starts next: nothing to do, as the other words say it. | Stages, downloads, removes or creates a deployment. |
| `previous`, `rollback`, `keep-stock` | Unchanged. | |

`login` refuses when `update` would refuse (as today when no download is needed). Every message that names a next step names the right word. Keep the messages' wording in one place, because the owner wants these words behind a short `aresos <word>` command later (board #195).

**Tests and model:**
- B2's destination invariant returns to its original strength: from every state with nothing staged or waiting and no active layout trial, each installed system can be made the next start by **one** command. The narrowed exception of `briefs/22c-b2-destination-invariant.md` is gone.
- New invariants: `update` never selects an installed system; `forward` never stages and never changes the set of deployments.
- Every existing test that pinned `update` returning to an installed system moves to `forward`, named in the report with the rule that replaces it. Revert proofs for both new invariants.
- Tools version stays 3 (not released yet); `commands.json` gains `forward`; the bundle, pins, host walk and waiting list are refreshed as stage 1b did.

**Guides:** the forward-again and back-from-stock boxes become "run `forward`"; the boot-menu two-step path and the "tools' release" distinction leave them; the failed-update card uses `forward` where it returned with `update`. Shorter is the goal.

**Steps and models:**
1. Rules, tests and model: a Claude agent on Fable 5.2 (a rule change in the owner tools, the high-stakes class under the owner's model rule of 2026-11-14). Stop and report.
2. Bundle, pins and guides: a Claude agent on Opus.
3. One review of both: Codex if any is left, otherwise a Claude reviewer on Fable. Then stage 2 walks `forward` (from stock, after `previous`) instead of `update` for those steps.
