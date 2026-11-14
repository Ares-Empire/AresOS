I found **three should-fix issues** at `169d2f9e`. The core journal repair works for the original council dead ends, but the interruption coverage misses a broken recovery path.

1. **Should-fix — interrupted layout restoration cannot resume.**  
   Locations: [owner.py:2010](/var/home/ares/AresOS-22c-review/os/owner-tools/owner.py:2010), [owner.py:2039](/var/home/ares/AresOS-22c-review/os/owner-tools/owner.py:2039), [ways_back_ledger.py:257](/var/home/ares/AresOS-22c-review/os/tests/ways_back_ledger.py:257).

   Concrete sequence:

   - On R27 with German settings, begin a US trial and prove it.
   - Cut `finish` after both persistent writes, before clearing the trial.
   - From a fresh login, run `layout abandon`.
   - Cut restoration after it writes the old console setting, before restoring X11.
   - Restart R27 and retry `layout abandon`.

   The persistent pair is now **German console / US X11**. The code accepts the original settings, the new settings, or the *forward* partial write—US console / German X11—but rejects this reverse partial write.

   I reproduced:
   ```
   abandon STOP: Finished system layout changed during the abandoned trial
   previous STOP: Layout trial is unfinished; prove it or revert first
   rollback STOP: Layout trial is unfinished; prove it or revert first
   reboot STOP: Layout trial is unfinished; prove it or revert first
   ```

   Choosing stock and abandoning there can clear the global trial, but leaves a repair note whose restoration rejects the same mixed settings. The affected AresOS remains unrepaired and cannot stage an update. Stock remains bootable; this is not deployment loss.

   **Fix:** make restoration resumable, with durable restoration intent and acceptance of its exact intermediate settings. Cover both pending-trial restoration and repair-note restoration. Add cuts during `abandon`: the model currently treats it as one indivisible event, although it cuts `finish` between writes.

2. **Should-fix — the fresh reorder read is not bound to the journalled list.**  
   Locations: [start-next.sh:12](/var/home/ares/AresOS-22c-review/os/release/start-next.sh:12), [owner.py:1550](/var/home/ares/AresOS-22c-review/os/owner-tools/owner.py:1550).

   Concrete sequence, requiring a concurrent external deployment writer:

   - `rollback` reads `[R27*, R13, S]` and journals intended `[S, R27, R13]`.
   - Before the script’s fresh read, another writer changes the order to `[R13, R27*, S]`.
   - The script finds S correctly, then writes `[S, R13, R27*]`.
   - The caller detects the disagreement **after performing its mutation**.

   I reproduced the owner primitive and subsequent refusal on every boot choice:
   ```
   Owner primitive executed: ['ostree admin set-default 2', 'sync']
   Actual order: ['S', '13', '27']
   Journal intended order: ['S', '27', '13']
   ```

   The open journal then matches neither `before` nor `intended`, so the ordinary recovery commands refuse across restarts. Nothing was deleted, but the tools added a mutation despite already-observable drift.

   This is distinct from the council’s accepted window **after the script’s final read**. Here the changed list is already available to that read.

   **Fix:** pass the expected pre-change deployment snapshot into the script and compare it before `set-default`, alongside target validation. On mismatch, perform no owner mutation and report the external change. Keep the postcondition and `sync`; the irreducible final read/call race remains the accepted limit. Add a test injecting drift between caller preflight and script execution.

3. **Should-fix — installed-state protection does not cover every list-reading command.**  
   Locations: [owner.py:1499](/var/home/ares/AresOS-22c-review/os/owner-tools/owner.py:1499), [owner.py:1574](/var/home/ares/AresOS-22c-review/os/owner-tools/owner.py:1574), [owner.py:1606](/var/home/ares/AresOS-22c-review/os/owner-tools/owner.py:1606).

   `login` on stock, `verify`, and `switch` enter `before_switch()` without the common journal resolution or A10 installed-stock-stage check.

   Two reproduced sequences:

   - Cut `rollback` after its primitive, restart onto stock, then run any of those three commands. Each refuses with `Stock list/pin/pending/BLS changed before switch`; the journal remains an **intent**.
   - With stock running beside installed AresOS and a staged update, `title` prints the required deletion warning, but those three commands print only that generic refusal.

   These commands make no deployment change, and `check` still provides recovery. Nevertheless, A5’s “every command” and A10’s mandatory danger message are not implemented universally. The missing warning matters when shutdown would delete the AresOS deployments.

   **Fix:** run the common installed-lifecycle survey before these commands’ own refusal checks, preserving the existing prepared-stock and first-switch behavior. Audit `prepare` similarly. Extend the “every command” tests to include these entry points.

The remaining safety conclusions are favorable:

- Reorder recovery distinguishes **applied this boot**, **restart waiting**, and **confirmed on a later boot**. The original cut/stock-boot and wrong-menu-choice dead ends are repaired.
- Target selection uses deployment identities; I found no running-system lookup through the kernel’s positional `ostree=` link.
- The reorder primitive preserves deployments and pins, and calls `sync` after `set-default`.
- For the intended single-stateroot installed sets, staging requires the running AresOS first. The retention rule preserves the new release, that running release, and pinned stock. The cleanup guard excludes additional unpinned rows before the running deployment.
- I found no normal destination-command path that unpins stock or writes its `/etc`.
- Version-2 journal translation and delayed migration at tools publication are sound. The legacy `before[0]` interpretation is confined to records whose version-2 producer required the running row first.

The model has meaningful independence: its ledger does not import owner helpers, and the fake replays operations against all 15 stage-0 captures. The named append, excessive-finalize-retention, premature-side-check, and target-must-run mutants genuinely fail guarding assertions. However, **closure proves only the encoded event set**. Finding 1 demonstrates a missing event, not a failure of the state-count assertion.

No entire numbered rule A1–A11 lacks a guarding test/mutant. The uncovered portions include A7’s interrupted restoration, A3’s caller-to-script snapshot drift, and A5/A10’s omitted list-reading commands. A per-rule mutation table does not establish coverage of every clause.

My assessment of the report’s **JUDGMENT-CALLs**:

| Call | Assessment |
|---|---|
| 1: serial-root probe commands | Sound for probing the primitive; owner interaction remains stage 2. |
| 2: probe network disconnected | Sound isolation. |
| 3: shared branch time bounds | Sound; no owner-tool behavior change. |
| 4: collect contradictions before failing | Sound for a disposable probe. |
| 5: consistent capture redaction | Sound; relevant identities and relationships remain testable. |
| 6: defer a second probe | Sound given the retained evidence and explicit integrator decision; the job must remain described as red. |
| 7: staging from older settings | Sound implementation of owner decision 5. |
| 8: update returns to newest installed | Sound implementation of owner decision 1. |
| 9: singular stock-stage warning | Sound and more accurate with one AresOS. |
| 10: preserve existing PASS wording | Sound with the accompanying identity-based title. |
| 11: resolution notes before a later STOP | Sound; explains changes to journal state. |
| 12: stop at the destination contradiction | Sound; subsequently resolved explicitly. |
| 13: removal notice before staging | Sound and necessary for interruption coverage. |
| 14: preserve `finish_proof` | Sound; restoration itself still needs finding 1 fixed. |
| 15: abandon another trial and repair this system | Sound ownership rule; same restoration caveat. |
| 16: narrowed destination invariant | Sound under the integrator’s follow-up. |
| 17: equivalence and execution reuse | Sound within the stated fixed-bundle/input assumptions; does not justify omitting interruption events. |
| Step 3: migrate only after publication | Sound and necessary to preserve version-2 recovery. |

My assessment of the **PLAN-GAPs**:

| Gap | Assessment |
|---|---|
| 1: existing menu helpers suffice | Sound. |
| 2: share package-27 route | Sound scope clarification. |
| 3: hosted namespace restrictions | Sound diagnosis; reported hosted resolution is appropriate. |
| 4: probe lacks final source bindings | Sound stage boundary; stage 2 still owes them. |
| **5: modified deployments remain readable/rebootable** | **Safe to leave.** Preserves version-2 compatibility without permitting an actual reorder or staging through the modification guard. |
| **6: compare bootc rollback slot/flag** | **Safe to leave.** It checks agreement with captured behavior rather than inferring why this system booted. Disagreement refuses safely. |
| **7: same-boot staging record loses its stage** | **Safe to leave as the explicit A5 exception.** I found no ordinary tools-only path producing it; external cleanup can. It requires Help in that boot and resolves after a later boot with the unchanged list. |
| **8: repair note for a removed deployment** | **Safe to leave.** Matching uses full deployment identity; the stale note does not attach to another installed deployment. |
| 9: destination contradiction | Resolved correctly by the follow-up. |
| 10: model practicality | The stated reduction/reuse approach is reasonable; coverage still needs finding 1. |
| 11: missing later fixtures | Correct limitation, carried forward. |
| 12: follow-up versus repair lock | Sound: the destination exception does not waive repair before staging. |
| 13: stage-2/triple-finalize evidence | Correct limitation. Triple finalize remains the next release’s real-VM gate. |
| Step 3: publication boundary unspecified | Sound clarification; the resulting fix is necessary. |

Verification performed read-only: **8 focused script/fixture/fake tests passed**, then **17 existing model/mutation/equivalence tests passed with an in-memory store adapter**. I also checked **13 historical accepted shapes** and **20 version-2 intent/record outcome cases**, and reproduced the three findings in memory. Source/payload equality passed for the changed implementation files; the three retained legacy release scripts match `main`.

I did not rerun the full exploration or publication filesystem tests. No owner entry, deployment binary, or `test_owner_update` module was run. No files were edited. The four deferred fingerprint failures are not findings.

CHANGES-NEEDED