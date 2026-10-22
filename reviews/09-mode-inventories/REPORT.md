# Package 09: separate Build and Live inventories

**Done**

- `ModeInventories` and `ModeInventoryMixin`: per-player, per-save Live/Build snapshots, including every inventory/equipment slot and the selected hotbar slot. The first Live-to-Build switch loads an empty inventory. Components and stack counts use Minecraft's registry-aware item codecs, with strict decoding and an exact round-trip check before mutation. A failed transaction restores inventory, mode, previous mode, flight and stored snapshots; failures display a diagnostic. Malformed/unsupported saved data is preserved rather than replaced with empty inventories.
- Persistence uses the version-1 `aresos_mode_inventories` tag in vanilla player data. Both snapshots, the current inventory and the game mode are written in the same vanilla player record. The active inventory remains authoritative; its stored snapshot is refreshed when leaving that mode. Transactions run synchronously on the server thread, so disconnect/save handling cannot interleave halfway through a switch. No independent inventory file or forced disk flush per G.
- `LiveMode`, `NetherHome`, join handling: G swaps inventories and synchronizes the selected slot. Home login swaps Build to Live before vanilla sends its login packet; a failed inventory load leaves Build and its items intact. Player replacement copies the stored snapshots. Normal worlds never initialize or save inventory storage.
- Pin/menu integration: only Live inventory moves update `pinned`; swaps clear any pending menu pin comparison. G refuses open inventory/container/catalogue/pause menus with a message. The server also refuses container, cursor and crafting-grid transactions. G and home arrival from Build restore snapshots without app population, model refresh or pin promotion changing the saved layout. Ordinary joins already in Live retain package-07 catalogue population.
- Added six server game tests, one client game test, reusable inventory assertions and a test-only one-shot fault after vanilla changes game mode. Added the screenshot destination to Gradle and documented the behavior/save format in `mod/README.md`.

**Verified**

All commands below ran from `mod/` with Java `25.0.4.1`, the checked-in Gradle wrapper, and the isolated Gradle test game directories. No real Minecraft installation was used.

| Command | Result/output |
| --- | --- |
| `.\gradlew.bat compileJava compileClientJava compileGametestJava` | Initial compile failed: `displayClientMessage` is unavailable in 26.2. Replaced it with the HUD overlay API. |
| `.\gradlew.bat build` (first attempt) | Compile failed: `ChatComponent.addMessage` needs four arguments in 26.2. Replaced the attempted chat call with the HUD overlay API. |
| `.\gradlew.bat build` (next attempt) | `All 26 required tests passed :)`; all 45 JUnit tests passed; `BUILD SUCCESSFUL in 26s`. |
| `.\gradlew.bat build runClientGameTest --rerun-tasks` (development run 1) | All 45 unit/26 server tests passed; client failed `Open container packet changed mode`. Fixed the new fixture to wait for the earlier Escape close packet before opening the chest. |
| Same command (development run 2) | All 45 unit/28 server tests passed; client failed `Host rapid switch failed 0`. Fixed the fixture to wait for chest-close acknowledgement before switching. Assertions were retained and a server-side fixture check was added. |
| `.\gradlew.bat runClientGameTest` (two diagnostic runs) | Both failed `Inactive Live survived restart: item/components/count in slot 40`. Actual and expected were both `1 minecraft:shield {}`. The expected fixture contained registry holders from the previous server. Restart fixtures now retain the complete serialized item/component values, compare those values, and rebind expected items to the reopened server's registry before the same exact stack assertions. |
| `.\gradlew.bat build runClientGameTest --rerun-tasks` (development run 3) | All 45 unit/28 server tests and the new 09 client checks passed. The earlier package-01 test then timed out at its app-repopulation assertion after clearing the inventory and rejoining. Fixed the implementation to skip population only for a home login that actually restores an inventory from Build; ordinary Live joins keep existing population. The earlier test was unchanged. |
| `.\gradlew.bat build runClientGameTest --rerun-tasks` (final pass 1) | `All 28 required tests passed :)`; all 45 JUnit tests and all nine client entrypoints passed; `BUILD SUCCESSFUL in 6m 33s`, `19 actionable tasks: 19 executed`. |
| Same command (final pass 2) | `All 28 required tests passed :)`; all 45 JUnit tests and all nine client entrypoints passed; `BUILD SUCCESSFUL in 6m 36s`, `19 actionable tasks: 19 executed`. Zero unit-test failures, errors or skips. Both complete passes ran on the same final code. |
| `git diff --check` | Passed; no output. |
| `.\gradlew.bat --stop` | `Stopping Daemon(s)` / `1 Daemon stopped`. No other Gradle versions were started. |

Server coverage: exact slot/count/component/selection restoration through 50 rapid switches; first Build empty; failed item serialization; invalid stored slot, unknown item, unsupported version and malformed tag; injected failure after the actual game-mode mutation and successful retry; separate players; container/cursor/crafting refusal without moving items; normal saves have no inventory tag.

Client coverage: actual G and selected-slot packets; Live unpin and repin persisted to fixture `apps.json`; a creative-supplied app placed in Build's hotbar changes no pin; G's menu message and server container refusal; 50 immediate host switches; save immediately after a switch; complete Build inventory and inactive Live inventory across server restarts; exact home-arrival Live restoration and inactive Build recovery. All eight earlier client entrypoints also run unmodified in each final pass, including ordinary-Live-join repopulation. The injected failure tests deliberately log `AresOS inventory switch failed; original state kept` at ERROR level; those are expected assertions, not failed tests.

Screenshots, captured by the client game test and visually inspected:

- [Live hotbar](screenshots/0000_09-live-hotbar.png): book app, numbered Live stacks, selected slot 6, armor/hearts/hunger and offhand shield.
- [Build hotbar](screenshots/0001_09-build-hotbar.png): creative-supplied app, quartz/pickaxe building inventory, selected slot 3 and offhand torch.

Kept the final pass's two package-09 screenshots. Removed 22 untracked screenshots generated in earlier packages' review directories; their original committed evidence and tests are unchanged. Branch: `pkg/09-mode-inventories`; PR: <https://github.com/carlsenares/AresOS/pull/8>. The PR targets `main` and was not merged.

**Not verified**

- Human play feel with the owner's actual app layout and an existing desktop backup. Suggested check: arrange Live apps, press G and collect building blocks, switch back, quit in Build, reopen, and inspect both modes.
- Forced process termination, power loss, disk-full conditions and save-file corruption during a vanilla disk write were not induced. This uses vanilla's save/recovery behavior and autosave interval; it does not promise durability of unsaved changes after a crash. Serialization/load failures and rollback after a real mode mutation were induced automatically.

**JUDGMENT-CALL**

1. **Refuse menus rather than close them.** Cursor and crafting contents must be settled and menus closed before G. Closing automatically can return/drop items or finish pin changes during a mode transition; refusal keeps those transactions untouched. Changing this later needs menu-close/cursor/crafting integration and corresponding tests; the save format is unaffected.
2. **Exact mode restoration takes precedence over package-07 population on Live entry, including home arrival from Build.** Those restored inventories are not repopulated or refreshed. Otherwise returning from Build could move a pinned app, change its components, or add items, contradicting this brief. Ordinary joins already in Live retain their existing catalogue population, including repinning an overflow app into a free slot. Additional apps remain available in the catalogue between joins. Changing this takes a couple of call-site edits and corresponding regression updates; no migration is needed.
3. **Legacy saves first encountered in creative keep their current items as Build.** A new Live inventory receives the normal app catalogue. Copying legacy items into both modes would duplicate them; guessing which are Live items could lose a creative build kit. This is reversible by moving items deliberately; automated reclassification would require a migration rule.
4. **One vanilla player record, no separate SavedData inventory file.** This avoids a two-file commit where a player inventory and its inactive snapshot could come from different saves. The tag is versioned and unknown versions block switching. A future format change needs an explicit version migration; future Minecraft inventory-size changes currently fail safely rather than truncating slots.

**PLAN-GAP**

- The brief does not specify an inventory migration for a legacy player already saved in creative, or how exact restoration interacts with package-07 automatic repopulation/appearance refresh. An earlier test explicitly requires ordinary Live rejoin population. The choices above preserve that behavior while keeping mode restoration exact.
- No other brief/design gap found. Per-dimension inventories, cross-player sharing, shops and `os/` remain outside this package.

**Open questions**

None blocking implementation. Owner review is needed for the judgment calls before merge under the repository workflow.

## 09b: review fixes

**Done**

- `ModeInventories`: the active inventory has its own owner, persisted as optional `build_active` in the existing version-1 player-data tag. Legacy tags adopt their saved vanilla mode once. Snapshot ownership no longer follows later vanilla mode changes. Ownership, snapshots and connection transaction state survive vanilla player replacement; a fresh connection starts unlocked.
- `ExternalModeMixin`: survival/creative changes through both vanilla game-mode setters use the same validated inventory transaction as G, covering commands, the mode-switcher packet and mods using those setters. Login/respawn initialization is distinguished from changes to the connected player. Open-menu and unsupported-mode changes are refused with messages.
- Switching sends a numbered begin marker, every destination inventory slot (including equipment omitted by `InventoryMenu`), the full menu contents, mode and selected slot, then a completion marker. The client acknowledges completion on the same ordered connection. The server ignores item packets until that acknowledgement; wrong transaction IDs and acknowledgements before completion do not unlock it. Failure sends the retained state through the same boundary. No timeout releases an unconfirmed inventory.
- `ModeSwitchClient` and input mixins: G locks immediately; server-initiated changes lock on their begin marker. Drop/use/attack, hand swap, menu clicks, hotbar selection and creative edits are blocked before client prediction. Queued item keys and extra G presses are discarded. Server guards also cover stale vanilla item packets and catalogue item requests.
- Regressions: command changes preserve both inventories; delayed G and external mode-switcher changes exercise real local inputs and deliberately stale packets, check both client/server inventories, the cursor, block placement/breaking and entity damage, and replace the player during a pending transaction. Failure recovery and command/save/rejoin/G are checked. Server-only fixtures explicitly simulate acknowledgement; the existing 50-switch client loop now makes 50 real acknowledged G transactions with all original inventory assertions retained.
- `mod/README.md` documents ownership, external changes and acknowledgement behavior. Test-only mixins hold inventory synchronization without sleeping either game thread.

**Verified**

All Gradle commands below ran from `mod/` with Java `25.0.4.1`, the checked-in wrapper, and isolated Gradle game directories. The real Minecraft installation was not used.

| Command | Result/output |
| --- | --- |
| `.\gradlew.bat genSources` | `BUILD SUCCESSFUL in 13s`; `2 actionable tasks: 2 executed`. Used local official sources to check packet and setter behavior. |
| `.\gradlew.bat runGameTest runClientGameTest` | Initial regression fixture compile failed: `int` cannot be converted to `PermissionSet` for `withPermission(4)`. Corrected the fixture to use the server command source with the test player as executor. |
| `.\gradlew.bat runGameTest --continue runClientGameTest` (before fixes) | Both regressions failed: `/gamemode survival must restore Live: selected slot 2`; `Delayed switch accepted a stale drop` with Live slot 5 reduced from 6 paper to 4. `1 required tests failed :(`; both run tasks failed; `BUILD FAILED in 42s`. [Recorded failure excerpts](09b-regressions.txt). Tests were committed before fixes as `9c7bc96`. |
| `.\gradlew.bat compileJava compileClientJava compileGametestJava` | `BUILD SUCCESSFUL in 6s`; `5 actionable tasks: 5 executed`. |
| `.\gradlew.bat runGameTest --continue runClientGameTest` (development 1) | `BUILD FAILED in 39s`. Seven server failures exposed fixtures switching out of their initial creative mode before setting up their intended baseline/acknowledgement. Client failed because a concrete mixin class cannot be referenced as an invoker. Fixed fixture setup and used an accessor interface. Assertions retained. |
| Same command (development 2) | `All 29 required tests passed :)`; all ten client entrypoints passed; `BUILD SUCCESSFUL in 6m 41s`. |
| `.\gradlew.bat build runClientGameTest --rerun-tasks` (development 3) | All 45 unit and 29 server tests passed; stronger client assertion failed on inventory slot 41 missing from vanilla menu synchronization. Added explicit synchronization for every player inventory slot, including fixture initialization. `BUILD FAILED in 50s`. |
| Same command (development 4) | All unit/server tests passed; mode-switcher fixture timed out because commands were disabled and vanilla refused its packet (`tried to change game mode ... without required permissions`). Enabled commands in this isolated command/switcher fixture. `BUILD FAILED in 59s`. |
| Same command (development 5) | Unit/server tests passed; the client fixture reached player replacement, then failed before cleanup could print its assertion. Cleanup hung in Fabric's test-thread phaser. Captured `jcmd 17288 Thread.print` in `mod/build/09b-thread-dump.txt` and stopped only that verified worktree dev-client process; run task failed. This was not a green run. |
| `.\gradlew.bat runClientGameTest` (diagnostic 1) | Added logging before cleanup; `Failure fixture was not exercised` showed that the next G was attempted while the respawn loading screen was open. `BUILD FAILED in 27s`. |
| `.\gradlew.bat build runClientGameTest --rerun-tasks` (development 6) and `.\gradlew.bat runClientGameTest` (diagnostic 2) | Waiting for the screen timed out: `BUILD FAILED in 59s` and `BUILD FAILED in 37s`. Diagnostic output identified `LevelLoadingScreen`, with `pending=false` and the complete replacement player present. |
| `.\gradlew.bat build runClientGameTest --rerun-tasks` (development 7) | `BUILD FAILED in 59s`; requesting a section-render rebuild still left the loading screen open. Inspection of vanilla's loading state identified the cause: the test delay hook also discarded `LEVEL_CHUNKS_LOAD_START` when holding game-mode events. Narrowed that hook to `CHANGE_GAME_MODE`, retained the rebuild for same-position respawn, and kept every assertion. |
| `.\gradlew.bat build runClientGameTest --rerun-tasks` (final pass 1, `f7fa6db`) | `All 29 required tests passed :)`; all 45 unit tests and ten client entrypoints passed; `BUILD SUCCESSFUL in 6m 53s`; `19 actionable tasks: 19 executed`. Unit XML: zero failures, errors or skipped tests. |
| Same command (final pass 2, `f7fa6db`) | `All 29 required tests passed :)`; all 45 unit tests and ten client entrypoints passed; `BUILD SUCCESSFUL in 6m 52s`; `19 actionable tasks: 19 executed`. Both full passes ran on identical implementation code. |
| `git diff --check` | Passed; no diff errors. |
| `.\gradlew.bat --stop` | `Stopping Daemon(s)` / `1 Daemon stopped`. No other Gradle versions were started. |

Final screenshots were captured by the tests and visually inspected: [Live hotbar](screenshots/0000_09-live-hotbar.png), [Build hotbar](screenshots/0001_09-build-hotbar.png), and [pending switch](screenshots/0000_09b-switch-pending.png). The pending screenshot retains Build's hotbar while Live is already prepared on the server; exact client/server assertions and the acknowledgement checks supply the behavioral evidence. Generated duplicates and earlier-package screenshots are archived under the ignored `.work/09b-generated-screenshots/` directory, preserving the original committed earlier-package evidence.

**Not verified**

- Human keyboard feel of F3+F4 and the owner's live third-party mod stack. The actual vanilla mode-switcher packet is exercised automatically; command and vanilla setter routing is covered in the isolated dev game.
- Process termination, power loss and disk-full conditions during vanilla disk writes were not induced; the original package's vanilla save/recovery limits still apply.

**JUDGMENT-CALL**

1. **Refuse adventure/spectator in marked worlds.** AresOS defines only Live and Build. Keeping another mode's abilities over an inventory with a different owner could introduce untested item paths. The alternative is an explicit policy for those modes while retaining inventory ownership. Changing this later requires transaction-policy and regression changes; the save format need not change. Normal worlds retain vanilla behavior.
2. **No timer-based unlock.** Missing acknowledgement keeps item input locked; disconnect/rejoin resets connection state while retaining the save's inventory ownership. A timer could allow stale actions onto the destination. A future recovery UI must perform another confirmed synchronization rather than merely clear the lock.

**PLAN-GAP**

- Vanilla's inventory menu does not synchronize every player equipment slot. A completion marker after menu synchronization alone would not meet the brief's complete-destination requirement; every slot is now sent explicitly.
- Vanilla can replace a player while retaining its connection. The acknowledgement counter and pending state must transfer with that replacement; fresh login state must remain distinct. The delayed external-change test exercises this case.

**Open questions**

None blocking implementation. The judgment calls remain for owner review before merge.

## 09c: protocol support and bounded acknowledgement recovery

**Done**

- `ModeInventories`: connected changes check `ServerPlayNetworking.canSend(player, ModeSwitchStatePayload.TYPE)` before initializing ownership, beginning a transaction, or touching inventory/mode/snapshots. Unsupported clients receive a system-chat explanation. Both external vanilla setters and refused-toggle synchronization follow this check.
- Supported clients still need the matching acknowledgement after complete-state synchronization. Each pending transaction retains its original inventory (all slots, components, counts and selection), game mode/history, flight, ownership and stored snapshots. A valid acknowledgement discards recovery state. A missing acknowledgement reaches a 200-server-tick deadline, restores that original state, and disconnects with a visible recovery explanation before the connection can accept item input again. Player replacement carries both recovery state and the original deadline.
- `LiveMode`: drives timeout checks on every server tick, including if the desktop marker has since changed; iterates a player-list copy because recovery may remove a player. `mod/README.md` documents compatibility, timeout and recovery behavior.
- Regressions cover an actually unregistered state channel, both external setters and refusal synchronization, unchanged transaction counter/storage/ownership/mode/inventory, lost acknowledgement rollback, late/wrong acknowledgements, replacement without extending the deadline, and cancellation after a valid acknowledgement. Embedded server fixtures explicitly advertise the receiver through Fabric's real channel-registration path; their existing assertions remain intact.
- `ModeProtocolClientGameTest` unregisters the real client receiver, asserts server refusal and visible chat, then restores the receiver and drops only acknowledgement payloads. It checks the supported destination remains locked on the server, the timeout recovery screen, and exact original Build plus inactive Live after restarting the save and retrying G. Test-only mixins expose received chat and simulate lost acknowledgement packets.

**Verified**

Commands ran from `mod/`, using Java `25.0.4.1`, the checked-in wrapper and isolated Gradle test game directories. The owner's Minecraft folder and other worktrees were not used.

| Command | Result/output |
| --- | --- |
| `.\gradlew.bat runGameTest` (before production fix, regression commit `6d50c12`) | Both new regressions failed: `Unregistered state channel accepted an external mode change`; `Lost acknowledgement must roll back Build: selected slot 5`. The scheduled assertion stopped the server; `BUILD FAILED in 21s`. [Committed failure evidence](09c-red-evidence.txt); full local log `.work/09c-red-server.log`. |
| `.\gradlew.bat runGameTest` (initial fix) | `All 31 required tests passed :)`; `BUILD SUCCESSFUL in 16s`. Additional deadline/replacement tests were added afterward. |
| `.\gradlew.bat build runClientGameTest --rerun-tasks` (development 1) | New client fixture did not compile: `Gui.getChat()` is unavailable; `BUILD FAILED in 4s`. Fixed access through `Gui.hud.getChat()`. |
| Same command (development 2) | All 33 server and 45 unit tests passed; the new client reached both message screenshots, then Fabric's cleanup rejected the expected timeout disconnect: `Exited the world before closing singleplayer context`; `BUILD FAILED in 59s`. Adjusted fixture cleanup to recognize that the timeout already closed the world; behavior assertions were retained. |
| Same command (final pass 1, `224f276`) | `All 33 required tests passed :)`; all 45 unit tests and all eleven client entrypoints passed; `BUILD SUCCESSFUL in 7m 35s`; `19 actionable tasks: 19 executed`. JUnit XML: 9 suites, zero failures, errors or skipped tests. Full local log `.work/09c-full-development-3.log`. |
| Same command (final pass 2, `224f276`) | `All 33 required tests passed :)`; all 45 unit tests and all eleven client entrypoints passed again; `BUILD SUCCESSFUL in 7m 29s`; `19 actionable tasks: 19 executed`. JUnit XML: 9 suites, zero failures, errors or skipped tests. Full local log `.work/09c-full-pass-2.log`. |
| `git diff --exit-code 224f276 -- mod` and `git diff --check` | Passed; no output. Both complete green runs used the final implementation and tests. |
| `.\gradlew.bat --stop` and `.\gradlew.bat --status` | `Stopping Daemon(s)` / `1 Daemon stopped`; `No Gradle daemons are running.` No other Gradle versions were started. |

Both full runs use identical implementation/test sources (`224f276`). Existing serialization and injected mode-change failures deliberately print `AresOS inventory switch failed; original state kept`; those assertions pass. No tests were weakened, removed or skipped.

Final-pass screenshots were captured by the client game test and visually inspected:

- [Unsupported client refusal](screenshots/0000_09c-unsupported-client.png): the visible compatibility explanation, original Live hotbar, offhand, armor, survival bars and selection.
- [Timeout recovery](screenshots/0001_09c-timeout-recovery.png): the connection-lost screen explains that the original inventory/mode were restored and asks the player to reconnect. Exact rollback and persistence are asserted by the tests, rather than inferred from this screen.

The 25 generated duplicate screenshots from the existing packages are archived inside the ignored `.work/09c-generated-screenshots/` directory; their committed evidence is retained unchanged. Branch `pkg/09-mode-inventories`, existing PR <https://github.com/carlsenares/AresOS/pull/8>, target `main`. No merge.

**Not verified**

- A separate physical LAN guest with an installed vanilla/older AresOS client, and the owner's third-party mod stack. Actual Fabric channel unregistration is exercised on both the embedded server fixture and the current real dev client.
- Human feel of the recovery delay and reconnect flow. Power loss, process termination and disk failures during vanilla saving were not induced; the existing vanilla save/recovery limitations still apply.

**JUDGMENT-CALL**

1. **Restore and disconnect after 200 server ticks (10 seconds at 20 TPS).** This supersedes 09b's indefinite-lock judgment call. The brief requires bounded rollback but does not choose a recovery protocol or timeout value. Simply unlocking the destination violates the acknowledgement boundary; rolling back and unlocking the same connection could apply destination-era packets to the original inventory. Disconnecting after restoration gives a bounded escape, a visible explanation, and vanilla's save-on-disconnect behavior. An automatic connected retry would need another confirmed synchronization plus its own bounded failure path. Changing the delay is one constant; replacing reconnect with automatic recovery needs protocol and regression changes, with no save-format migration.

**PLAN-GAP**

- The brief leaves the timeout value/unit and post-rollback connection behavior unspecified. The choice above uses server ticks so a paused integrated server does not time out during pause, and closes the connection to preserve the stale-input safety required by 09b.

**Open questions**

None blocking implementation. The recovery-flow judgment call is recorded for owner review before merge; no merge is performed in this run.

## 09d: pending pickups and external inventory changes

**Done**

- `PendingPickupMixin`: pending server transactions cancel vanilla item-entity and XP-orb collisions before spending their contents, pickup delay, or mending value. Items and orbs stay in the world. Acknowledgement restores normal pickup behavior.
- `PendingInventoryMixin`: refuses both ordinary and indexed/damaged-stack `Inventory.add` calls without modifying the supplied stack, including creative's overflow-discard path. Container insertion/extraction eligibility blocks hopper-style transfers and stack merges. `placeItemBackInInventory` uses vanilla's full-inventory drop fallback while pending: merely refusing its nested `add` would lose the stack it splits before calling that method. Normal inventories retain vanilla eligibility.
- `ModeInventories`: remembers the complete synchronized destination through player replacement. If an external command, equipment setter or in-place stack edit bypasses insertion checks, timeout recovery serializes and validates that changed destination into its inactive mode before restoring the original active inventory/mode/history/flight. First-switch recovery initializes both snapshots when necessary. A refused/failed switch retains external changes in its original, still-active inventory. Untouched destinations retain the exact original rollback snapshots and all 09c assertions.
- Regression tests first committed in `0f6c457`; production fix and expanded tests in `ef69f1b`; the earlier chest fixture packet barrier is `394b7e1`. The server and actual client timeout/reconnect regressions each demonstrated **12 emeralds becoming 5 before the fix**. [Committed red evidence](09d-red-evidence.txt); complete local log `.work/09d-red.log`.
- Five additional server tests cover timeout pickup conservation, direct `/item replace` plus equipment/in-place changes and player replacement, first-switch destination retention, refused-switch retention, and blocked/resumed insertions/hopper merges/mending/pickup in both Live and Build. The existing protocol client test now leaves inventory space, collides with a seven-emerald drop during the lost-ack window, and asserts all twelve emeralds across active inventory, inactive inventory and world after timeout and restart. Its original exact Build/Live/retry and unsupported-client assertions remain.
- `mod/README.md` documents the pending-transfer and recovery behavior. No dependency or save-format change.

**Verified**

Gradle commands ran from `mod/` with Java `25.0.4.1`, the checked-in Gradle wrapper and isolated dev/test directories. The owner's Minecraft folder, other worktrees and system settings were not used.

| Command | Result/output |
| --- | --- |
| `.\gradlew.bat runGameTest --continue runClientGameTest` (regressions before production fix, `0f6c457`) | Server: `Pending pickup lost items on rollback: expected 12 across both inventories and world, got 5`. Client: `Pending pickup lost items after timeout/reconnect: expected 12 across both inventories and world, got 5`. Both tasks failed; `BUILD FAILED in 57s`; `13 actionable tasks: 5 executed, 8 up-to-date`. |
| `.\gradlew.bat runGameTest` (development 1) | Test fixture compilation failed because the `ListTag(List<Tag>)` constructor is package-private; `BUILD FAILED in 3s`. Fixed the comparison to compare list contents directly. |
| Same command (development 2) | `3 required tests failed :(`; `BUILD FAILED in 16s`. The command fixture used `inventory.9` while checking slot 9 (vanilla maps it to slot 18); two item fixtures spawned at the unloaded default login location. Corrected the command to `inventory.0` and placed item fixtures at their loaded, fixed test coordinates. |
| Same command (development 3) | Pickup count assertion failed with `expected 12 ... got 19`; `BUILD FAILED in 15s`. A leftover emerald entity from the earlier failed dev run loaded later in the reused test level. The server fixture now marks all twelve of its emeralds with the same unique per-player component and counts those exact stacks across both inventories and the entire loaded world. It still requires exactly twelve and a surviving seven-item entity. |
| Same command (development 4) | `All 38 required tests passed :)`; `BUILD SUCCESSFUL in 16s`; `11 actionable tasks: 4 executed, 7 up-to-date`. |
| `.\gradlew.bat build runClientGameTest --rerun-tasks` (full development 1, `ef69f1b`) | All 38 server/45 unit tests and the 09/09b/09c/09d client checks passed; an older app fixture failed `Full hotbar did not overflow into inventory`; `BUILD FAILED in 2m 1s`; `19 actionable tasks: 19 executed`. Its previous chest-close packet raced the next mode change, which vanilla correctly refused. Added a close-screen/serverbound-packet barrier and explicit mode assertions; retained every existing behavior assertion. Log `.work/09d-full-pass-1.log`. |
| Same command (final pass 1, `394b7e1`) | `All 38 required tests passed :)`; all 45 unit tests and all eleven client entrypoints passed; `BUILD SUCCESSFUL in 7m 10s`; `19 actionable tasks: 19 executed`. Nine JUnit suites: zero failures/errors/skips. Log `.work/09d-full-development-2.log`. |
| Same command (final pass 2, `394b7e1`) | `All 38 required tests passed :)`; all 45 unit tests and all eleven client entrypoints passed again; `BUILD SUCCESSFUL in 7m 20s`; `19 actionable tasks: 19 executed`. Nine JUnit suites: zero failures/errors/skips. Log `.work/09d-full-pass-2.log`. |
| `git diff --exit-code 394b7e1 -- mod` and `git diff --check` | Passed; no output. Both full runs used identical implementation/test sources. |
| `.\gradlew.bat --stop` and `.\gradlew.bat --status` | `Stopping Daemon(s)` / `1 Daemon stopped`; `No Gradle daemons are running.` No other Gradle versions were started. |

Both complete green runs used `394b7e1`. [Committed green-run excerpts](09d-green-evidence.txt) include the new regression result and unit XML totals. The pre-existing serialization and injected-mode-failure tests deliberately log `AresOS inventory switch failed; original state kept`; those tests pass. No test was weakened, skipped or removed.

Final-pass screenshot, captured by the client test and visually inspected: [pickup after reconnect](screenshots/0002_09d-pickup-after-reconnect.png). The original Build hotbar is restored and the emerald drop remains visible in the world. Exact slot/component/count assertions and the twelve-item total provide the conservation evidence.

Archived 26 other generated screenshots under the ignored `.work/09d-generated-screenshots/` directory and restored the earlier packages' committed screenshot evidence unchanged.

**Not verified**

- Human feel with the owner's app layout and third-party mod stack. Suggested check: leave a block item nearby, press G, and confirm pickup resumes normally once the mode change completes. Timeout and reconnect are induced automatically by dropping only acknowledgement payloads.
- A physical hopper/minecart layout feeding a player is not a vanilla transfer destination. Automated tests call vanilla's shared `HopperBlockEntity.addItem` routine against the actual player inventory, covering empty slots and merges, and check extraction eligibility. Direct setter and in-place bypasses are covered separately. Unserializable item components supplied by arbitrary third-party code, power loss and disk-write failures were not induced.

**JUDGMENT-CALL**

1. **Retain external changes in the inventory that received them.** Most incoming transfers are refused before consuming their source. A void setter or in-place edit has no reliable refusal signal, so recovery preserves the whole changed destination as its inactive inventory instead of restoring its stale snapshot. The original mode and active inventory still return; a later acknowledged switch retrieves the retained destination. A refused/failed switch keeps changes in its still-active inventory. Silently cancelling a void setter could spend a transfer's source anyway; merging destination changes into the original inventory would need slot/component/conflict policies and could duplicate items. A caller-specific transfer journal would be considerably larger. Changing this policy later requires recovery logic and regression changes, with no save migration.

**PLAN-GAP**

- Blocking only `Inventory.add` is insufficient: vanilla returned-stack handling splits before calling it and ignores refusal; equipment/command setters and existing stack references bypass it entirely. The drop fallback and retained-destination recovery cover these paths without pretending a void setter rejected a transfer. No other brief gap found.

**Open questions**

None blocking implementation. The recovery policy above is recorded for owner review before merge. Branch `pkg/09-mode-inventories` updates existing [PR #8](https://github.com/carlsenares/AresOS/pull/8), targeting `main`; no merge is performed.
