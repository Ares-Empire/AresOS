Reviewed commit `ce8b45dc756ef6cd5e32c7ce15f6b1053a5c0cb1`; read-only review of `cd640a6c..HEAD`. No files changed, builds or tests run.

| Point | Status | Reason |
|---|---|---|
| 1. Node ownership | OPEN | Ordinary same-root replacement now preserves the incoming command, children and requirement. Content checks prevent removing a changed node, and reload/rejoin have meaningful tests. However, `beforeAdd` can remove an owned command from a different parent than the registration being intercepted; see FIX 2. |
| 2. `name`/`unname` | CLOSED | Both branches now require `allowed` during parsing. The guest and console-originated `execute as <host>` assertions would fail without this change. Execution still checks the host. The compilation-probe qualification is covered separately in point 7. |
| 3. Clicks and typed `/open` | CLOSED | Both listing paths use `/aresos app open <id>`, with a parse requirement. Typed matching no longer gives IDs precedence. Duplicate-name, ID/alias collision and foreign-`/open` tests distinguish the old behavior. |
| 4. Missing programs | CLOSED | Complete helper lists persist `absent`; command registration, `/open` matching/completion and ID launches exclude absent entries. `/apps` renders them without a click as “not installed.” Incomplete/failed listings do not announce a replacement catalogue. Windows uses the merge overload that does not mark absence. Disappearance/return assertions exercise the resulting behavior, beyond merely checking the new field. |
| 5. `A → a2` | CLOSED | Numbered candidates are validated after adding the suffix. Tests cover `a2`, occupied numbered forms and an earlier one-letter candidate preceding another occupied candidate. These fail under the previous implementation. |
| 6. Save failure | CLOSED | Reconciliation proceeds after a failed name save, and failure remains pending with bounded exponential backoff. The test checks immediate removal, no immediate retry, and recovery without another catalogue edit; the old early-return/cached-state behavior fails those assertions. |
| 7. Permission probe | OPEN | The exception accepts **any** serverless source holding the exact `NO_PERMISSIONS` singleton. Server-bearing guest, console and command-block sources still take the host check; ordinary `execute as` cannot bypass the parse requirement. The test proves rejection of a synthetic `ALL_PERMISSIONS` compilation context, but does not establish what every real function-loading path supplies. I found no demonstrated real-source exploit through this exception, but cannot close the stronger compilation claim from the inspected evidence; see SHOULD 1. |
| 8. `add`/`remove`/`list` | OPEN | The documented impersonation route violates the stated bar. Add the parse requirement before merge; see FIX 1. |
| 9. Schema and package 36 | OPEN | Package 34 rejects schema 4 without changing it and starts with apps disabled, as reported. Package 36’s inspected `AppGroup`, `Place` and `Assignment` contracts remain compatible: existing constructors/accessors remain, and `Assignment` already accepts an explicit `wanted` flag. Its integration must account for `absent`, which PLAN-GAP identifies. The downgrade instructions incorrectly promise no other data loss; see FIX 3. |
| 10. Tests and suite safety | OK | Each original fix has a discriminating assertion, as described above; running old code is unnecessary to establish those particular differences. Reload and retry tests have separate batches. The new server tests force/release no chunks, and the client test remains last. The report records two passing client runs and five committed screenshots; no `mod/` changes follow the tested `bb014aef`. These are builder results, not independently rerun evidence. Coverage gaps for the new findings remain. |

1. **FIX — app membership can still be changed by something impersonating the host.**  
   `mod/src/main/java/dev/aresos/item/AppCommands.java:28`

   With Discord in My apps, a command block or function can issue:

   ```text
   execute as <host> run aresos app remove discord
   ```

   The `app`/`remove` path has no parse requirement. At execution, `host()` sees the selected host player, so removal succeeds: saved membership and pin state change, and `/discord` and `/dc` disappear. This directly meets the bar that his commands must not be lost through someone or something else’s command.

   Add `.requires(AppCommands::allowed)` to the `app` parent, covering `add`, `remove` and `list` as well as the already guarded children. Add regression coverage for console/command-block-originated `execute as <host>` and a real function, asserting unchanged membership, pins and commands.

2. **FIX — the global merge hook can remove a command from the wrong parent.**  
   `mod/src/main/java/dev/aresos/names/OwnedNodes.java:87`  
   `mod/src/main/java/dev/aresos/names/OwnedNodes.java:76`

   `beforeAdd(parent, incoming)` finds an existing child under the supplied `parent`, but `remove(existing)` deletes it from the **recorded installation parent** without checking that these parents match.

   Concrete scenario: another mod reuses the existing `/open` node beneath its own namespace:

   ```java
   namespace.addChild(root.getChild("open"));
   root.addChild(namespace);
   namespace.addChild(Commands.literal("open").executes(otherCommand).build());
   ```

   The final registration is beneath `namespace`. The hook nevertheless removes `/open` from the dispatcher root. Brigadier then continues merging beneath `namespace`, where the old node remains. AresOS does not reinstall `/open` during ordinary `SlashCommands.refresh`, so the owner loses it until registration happens again, such as on reload.

   This meets the bar both by removing the owner’s command and by making a registration elsewhere mutate an unrelated command path. Require the intercepted parent to be the recorded installation parent before stepping aside. Add a shared-node/different-parent regression test; the existing tests only register replacements under the original root.

3. **FIX — the documented downgrade can discard saved apps and choices, despite promising otherwise.**  
   `reviews/35-slash-names/REPORT.md:104`

   Scenario: migrate to schema 4, add an app or change pins/My apps, then follow the instruction to copy the migration-time schema-3 backup over `apps.json`. That restores the entire old snapshot. All subsequent additions and membership/pin changes disappear—not just names and absence marks.

   The instruction does not preserve the current file first and explicitly says “nothing else” is lost. Following it can therefore lose the owner’s saved app state, meeting the data-loss bar.

   Correct the instructions to preserve the current schema-4 file before any replacement and explain that restoring the backup rolls back **all changes since migration**. A conversion preserving later edits would be a separate recovery operation; this fix need not implement one.

4. **SHOULD — prove the permission exception against real function compilation, rather than a chosen permission constant.**  
   `mod/src/main/java/dev/aresos/item/AppCommands.java:62`  
   `mod/src/gametest/java/dev/aresos/test/SlashNamesGameTests.java:401`

   The test labels `createCompilationContext(ALL_PERMISSIONS)` as a function source. It establishes that this chosen context fails, but the predicate accepts a context produced by the same factory with `NO_PERMISSIONS`. It identifies source properties, not the provenance of Minecraft’s click probe.

   Thus the concrete unproven case is function compilation using the latter context: guarded nodes would parse successfully. I have not established that the actual integrated-server loader supplies it, so this is **not a demonstrated launch exploit** and is not classified FIX.

   Trace and document the actual loader’s permission construction, and test real datapack function loading, including macro functions and subsequent execution as the host. Keep runtime authorization separate from the probe exception where practical. The report’s assertion that “exactly that probe” passes is stronger than the predicate or current test demonstrates.

5. **SHOULD — weak keys do not release old command trees because the values retain their keys.**  
   `mod/src/main/java/dev/aresos/names/OwnedNodes.java:42`

   After reload or leaving/rejoining worlds, `INSTALLED` retains `Installed.parent` and the subtree snapshots. Each snapshot strongly references its node, including the map’s own weak key; the parent also references that child. Consequently, the entries cannot disappear through weak-key collection.

   Repeated reloads retain successive command trees indefinitely. This does not itself demonstrate command loss or unauthorized execution, so it is SHOULD. Remove ownership records when their dispatcher is retired, or redesign the references so values do not strongly retain their weak keys.

VERDICT: CHANGES-NEEDED