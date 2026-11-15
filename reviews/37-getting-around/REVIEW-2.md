Reviewed commit `60d66a0b26c065b96746843136d5f610586fc68d`. Review was read-only: files and read-only git commands; no builds, tests, game execution or file changes.

| Point | Status | Reason |
|---|---|---|
| 1. Teleports and arrival suppression | CLOSED/OK | The production-source search for teleport, position-setting and respawn paths agrees with the report’s list. Home, H, `/go` and doorway return use the shared teleport; void recovery, joining and respawn mark arrival separately. Membership is per player, persists while stationary, and clears on an observed exit, allowing re-entry. F1’s explicitly documented vanilla-teleport exclusion is acceptable within this brief. |
| 2. Catalogue snapshot and lock | CLOSED/OK | Gameplay catalogue writers use the same `AresOs` monitor as `saveSpotsIf`; the unsynchronized initial assignments precede gameplay. Construction uses snapshot app definitions, including names, groups and icon paths. Picture-cache updates occur on the server thread outside the command. The pass’s save callback still reads and merges the current apps file under the lock, preserving unrelated fields; it does not feed a fresh catalogue into construction. F2 and F3 close the reported helper-refresh race. |
| 3. Take-down and matching check inputs | OPEN | `takeDown` directly consumes `checkRemoval`’s decision: there is no duplicate sign-removal rule. `Gone` correctly models restored blocks, discarded versus retained signs, lost ownership and removed zones. The layout supports the exit-point exception, and ordinary preceding builds remain separated. However, same-place renewals remain unmodelled. F4 breaches the principle and can also overwrite the requested saved place; finding 1. |
| 4. Deferred `/go` | OPEN | Explicit tickets cover the candidate boxes, at most four chunks. Loaded destinations are checked in order; deferred arrival checks safety again and marks arrival without directly changing blocks. Arrival, obstruction, timeout, disconnect and successful replacement moves release tickets. Normal world closure removes pending state with the server. Timeout requires **both** 200 ticks and 10 seconds and is checked only while still unloaded. Player/destination changes are not revalidated; finding 2. The reported timings distinguish command latency from the remaining roughly 400 ms loading tick; they do not establish stall-free loading. |
| 5. Test cleanup and frozen/refused fixtures | OPEN | Ordinary wait expiry releases tickets in `finally`, before the enlarged framework tick limit. F6’s temporary reflection changes are restored within the same tick and are reasonable for these fixtures. F7’s 120-second duration is reasonable, but its enforcement still depends on the test thread advancing; finding 3. No forced-timeout regression demonstrates the cleanup guarantee. |
| 6. Previously established behavior | CLOSED/OK | No independent regression found in `/apps`, names, group handling, host-only command registration, H, freeze protection or ordinary package 33 gate removal. The `TakeDown` refactor preserves removal provenance, signs and changed lights. Swap/move’s remaining partial-commit problem and deferred navigation’s stale requests are covered above. |
| 7. Regression-test claims and missing paths | OPEN | Reading supports the `/home` and H arrival assertions, catalogue-change refusal assertions and moved-sign refusal assertion failing without their respective fixes. The deferred-arrival test would reject the old immediate teleport. Frozen/refused tests intentionally pass the old code. Timeout cleanup is reasoning about a branch, not a demonstrated failing-before regression. Important omissions are F4, pending-arrival cancellation/invalidation and timeout, four-chunk boundaries, and the separately marked void/join/respawn paths. The reported package 36 flake remains unexplained; these results were not rerun here. |

1. **FIX — F4 still allows a checked swap to commit a different arrangement.**

   `mod/src/main/java/dev/aresos/hub/TownMoves.java:234`, `mod/src/main/java/dev/aresos/hub/TownKeeper.java:411`, `mod/src/main/java/dev/aresos/hub/TownKeeper.java:436`

   Have three standing apps, A, B and C. C precedes A in the keeper’s build order and needs renewal because its name or picture changed. Move C’s recorded sign into a solid cell of A’s intended destination at B’s place, then swap A and B.

   Preflight excludes C from `gone` because its place is unchanged. C’s sign therefore remains exempt during A’s check. After saving the swap and removing A and B, the pass renews C. Its moved sign correctly survives, but loses its recorded-sign exemption. A’s actual build now refuses an entity that preflight ignored.

   This is not necessarily limited to “the requested place stays saved.” The refusal adds that place to `refused`; another round can assign A a different free place and save that replacement through `TownKeeper.save`. B can already stand at A’s former place. The command has changed the file, records and world despite failing to deliver the checked swap.

   Preserving the owner’s sign and avoiding duplicate logos do not satisfy the explicit check/commit principle. F4 is therefore blocking, rather than an acceptable documented limit. Model renewals through shared keeper rules, or refuse before saving whenever their effects cannot be established. Add this three-app regression and correct the claims at `reviews/37-getting-around/REPORT.md:540` and `:640`.

2. **SHOULD — a pending `/go` survives changes that make its destination stale.**

   `mod/src/main/java/dev/aresos/world/Arrivals.java:45`, `mod/src/main/java/dev/aresos/world/Arrivals.java:92`, `mod/src/main/java/dev/aresos/mode/LiveMode.java:43`

   Start a cold `/go`, then change dimension before its destination loads. The pending request retains only destination coordinates and looks up the player by UUID; it subsequently teleports that player back to the old destination. Void recovery and respawn likewise mark arrival without cancelling this request.

   Similarly, if the app is removed from My apps or its hand-made zone is removed while loading, the request still lands at the captured coordinates and can emit its obsolete arrival message. Successful `/home`, H and another accepted `Arrivals.go` do cancel it; refused commands do not.

   Safety is rechecked and arrival is marked, so this does not establish owner-data damage or an app launch and falls below the FIX bar. Bind pending work to the originating player/session and target identity, cancel it on superseding movement, and revalidate the target before landing. Test cancellation, dimension changes and target removal.

3. **SHOULD — the test’s wall-clock bound cannot operate when ticks stop.**

   `mod/src/gametest/java/dev/aresos/test/GettingAroundGameTests.java:132`

   If the test/server thread stops advancing during a chunk wait, the runnable never executes its `System.nanoTime()` comparison. After 120 seconds, it has neither failed nor released its tickets. Increasing `MAX_TICKS` cannot change that.

   The normal repeatedly-polled timeout path is improved, but the comment that stopped ticks still produce failure and cleanup is unsupported. There are also unguarded teleport steps at lines 589 and 606 whose exceptions bypass the new cleanup wrapper.

   This is suite reliability, below the owner-world FIX bar. Cover these steps with cleanup, distinguish a cooperative timeout from an independent watchdog, and force timeout/failure paths in verification rather than claiming universal cleanup from the success runs.

4. **NIT — “away from the server thread” overstates the measured result.**

   `mod/src/main/java/dev/aresos/world/Arrivals.java:31`, `mod/src/main/java/dev/aresos/world/GettingAround.java:37`

   The report records approximately 1 ms in the command but a later server tick lasting roughly 373–399 ms during cold loading. Those measurements are consistent with deferring the command’s work; they do not support the stronger source comments that loading happens away from the server thread.

   Say “requested through the game’s ticket system and checked on a later tick.” Keep the report’s distinction between command latency and loading latency, including the unmeasured owner-world case.

VERDICT: CHANGES-NEEDED