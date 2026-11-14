I found one blocking command collision bug, several correctness issues, and incomplete acceptance evidence. This was a read-only review; I ran neither Gradle nor Minecraft.

1. **Blocking — a later command can be mistaken for an app command and deleted.**  
   [SlashCommands.java:39](/var/home/ares/AresOS-35-slash-names/mod/src/main/java/dev/aresos/names/SlashCommands.java:39)

   `reserved()` excludes nodes by object identity. Brigadier’s `addChild` merges a later registration into the existing node: it keeps that identity while replacing its executable command and adding children. I confirmed this in the cached Brigadier bytecode.

   After `/discord` is installed, another mod registering `discord` therefore remains invisible to the reserved-name calculation. Its command inherits AresOS’s host-only requirement, and the next membership/name refresh removes the entire merged node and reinstalls the app command. The other mod’s command and children disappear.

   The same registration-order problem affects the host-only `/open` and `/apps` roots if another mod registers them later.

   **Fix:** handle foreign registrations before they merge into owned nodes, or explicitly preserve and hand off foreign command content and requirements. Object identity alone cannot establish ownership. Add tests registering another command **under an already-installed app name**, with children and different permissions, then refresh/remove the app. The current “later mod commands always win” test registers the unrelated name `future`, so it misses this bug. Also exercise a real dispatcher rebuild/reload and rejoin.

2. **Should-fix — command blocks and other operators can change the owner’s names through `/execute as`.**  
   [AppCommands.java:28](/var/home/ares/AresOS-35-slash-names/mod/src/main/java/dev/aresos/item/AppCommands.java:28), [AppCommands.java:56](/var/home/ares/AresOS-35-slash-names/mod/src/main/java/dev/aresos/item/AppCommands.java:56)

   The new `name` and `unname` branches have no `.requires` restriction. Their execution checks only the resulting player entity. Consequently, a command block or another permitted operator can run:

   ```text
   execute as <owner> run aresos app name discord changed
   ```

   The execution source now identifies the owner, so the saved names are changed. These branches are also visible outside the intended host context.

   **Fix:** restrict the new branches during parsing and validate the originating command source, rather than only the player selected by execution modifiers. Test guest and command-block attempts.

   This does **not** establish an equivalent direct launch exploit: `/dc`, `/open` and `/apps` have root requirements, which Brigadier checks against the original source before `/execute as` changes it.

3. **Should-fix — the click implementation changes `/open` matching and can dispatch another mod’s command.**  
   [OpenPrograms.java:20](/var/home/ares/AresOS-35-slash-names/mod/src/main/java/dev/aresos/names/OpenPrograms.java:20), [ProgramCommands.java:59](/var/home/ares/AresOS-35-slash-names/mod/src/main/java/dev/aresos/names/ProgramCommands.java:59)

   Exact IDs are checked before any name matching. With two programs named “Editor”, one having ID `editor`, `/open editor` silently opens that program instead of listing both matches. An ID can likewise take precedence over another app’s saved name.

   There is a second problem: if another mod already owns `/open`, AresOS correctly declines to register it, but `/apps` rows still issue `/open <id>`. Clicking them executes the other mod’s command.

   **Fix:** give clickable rows a separate, explicitly ID-based AresOS command or payload. Keep ordinary `/open` resolution within the specified matching rules. Test duplicate display names where one ID equals the query, alias/ID collisions, and a pre-existing foreign `/open`.

4. **Should-fix — commands remain available for programs missing from a later complete system list.**  
   [ProgramCommands.java:39](/var/home/ares/AresOS-35-slash-names/mod/src/main/java/dev/aresos/names/ProgramCommands.java:39), [SlashCommands.java:70](/var/home/ares/AresOS-35-slash-names/mod/src/main/java/dev/aresos/names/SlashCommands.java:70)

   Both paths use `AresOs.apps()`, which is the retained apps-file list. `AppsConfig.merge()` deliberately retains entries and their `mine` fields when a complete system list no longer contains them. There is no separate presence filter.

   Thus an uninstalled program retains its slash commands, appears in `/open` results/completion, and can generate launch requests despite no longer being listed by the system. The Linux helper may reject the request, but the mod’s promised behavior is still wrong.

   **Fix:** distinguish remembered app state from presence in the latest complete catalogue. Preserve names and membership choices for return, while filtering absent programs from active commands and `/open`. Update presence only after a complete list; helper downtime must preserve the last known list. Add disappearance/return tests.

5. **Should-fix — the number fallback discards usable one-letter candidates.**  
   [NameRules.java:112](/var/home/ares/AresOS-35-slash-names/mod/src/main/java/dev/aresos/names/NameRules.java:112)

   For a program named `A`, without useful executable/desktop metadata, the first candidate is `a`. It is initially invalid because it is too short, but the specified numbered fallback produces valid `a2`. The implementation filters bases through `valid()` first and returns `app2`.

   **Fix:** validate the completed numbered candidate. Use `app2` only when numbering the specified base cannot produce a valid name. Add `A → a2`, including occupied numbered variants.

6. **Should-fix — persistence failure prevents cleanup and suppresses recovery.**  
   [SlashCommands.java:59](/var/home/ares/AresOS-35-slash-names/mod/src/main/java/dev/aresos/names/SlashCommands.java:59)

   If name assignment fails, `refresh()` returns before removing stale registrations, then records the failed apps/reserved state as current. Once the I/O problem clears, ordinary ticks return early until another unrelated change occurs. Removed aliases can remain in completion, and newly added names remain unavailable. The execution membership check prevents an old alias from launching a removed app, but does not remove its registration.

   **Fix:** perform safe removals independently of successful name persistence. Keep failed reconciliation pending and retry with bounded backoff. Test failure followed by recovery without another catalogue edit.

7. **Blocking acceptance gap — the required client verification and screenshots are absent.**  
   [REPORT.md:30](/var/home/ares/AresOS-35-slash-names/reviews/35-slash-names/REPORT.md:30)

   The report clearly acknowledges this. Hosted compilation and unit/server passes do not verify the client assertions.

   Still unverified are the final guarded local build, two complete client-suite passes, actual chat completion, typed `/dc` launch/count and position after focus return, chat click handling, client command refresh, Build-mode launching, Apps screen rendering/search, sign rendering and preservation, and client payload rejection. None of the five requested screenshots exists for inspection. Real application windows, focus behavior and already-open behavior also remain human checks.

   **Fix:** after the code fixes, complete the guarded local build and two full client runs, inspect and commit screenshots, and update the report with actual results.

The remaining source checks look sound within those limits:

- All 27 worked-list rows have matching fixtures and expected results. Maker/filler lists, cleaning order, desktop-ID selection, ordinary nickname/starter assignment, validity and clash refusals follow the written rules, apart from the numbered fallback above. The additional examples test explicitly supplied metadata, rather than proving behavior for unspecified real installations.
- Normal successful edits preserve saved names through rename/removal/return. Name edits preserve unknown JSON fields and use atomic replacement. Genuine command conflicts are an explicitly required exception to name stability.
- The launch path sends `ZoneLaunchPayload(id, 0)` to the host; the client requires an integrated AresOS world and resolves the ID locally before calling the same launcher used by the hotbar. I found no remote-server packet path that passes this gate. Visit zero creates no return teleport, and there is no already-open suppression.
- The gate change supplies the saved main name to the existing slash-prefixed second line without rewriting standing signs. Apps screen search includes aliases and rendering reserves room for the main name. Their appearance remains unverified.
- The timeout changes from 10 to 20 minutes. The client test is appended after existing tests. I found no existing assertion weakened or deleted; the existing test edits accommodate schema 4.

For each report decision:

| Report entry | Review |
|---|---|
| Removed apps retain ownership of saved names | Agree; this protects remembered names on return. |
| Invalid-candidate fallback uses `app2` | Agree for an unusable numeric/non-Latin base; disagree with applying it to a one-letter base that becomes valid when numbered. |
| `/open` accepts exact stable IDs | Disagree with its precedence and use as the click route; finding 3 describes the resulting wrong launches. |
| No worked-list differences; extra examples supply metadata | Agree for the supplied fixtures. Those assumptions should remain explicit. |
| StartupWMClass is absent from shell/1.1 | Agree this is a real interface gap. The pure-function test does not provide runtime support; the report correctly discloses that limitation. |
| Numeric/non-Latin fallback is undefined | Agree; `app2` is reasonable for that gap, subject to finding 5. |

CHANGES-NEEDED