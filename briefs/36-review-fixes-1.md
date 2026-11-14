# 36 review fixes 1: the town trusts its records only while they are provably its own

Follow-up on the same branch (`pkg/36-town`, PR #59). The review is `reviews/36-town/REVIEW-1.md` (gpt-6-astra, high): CHANGES-NEEDED, six FIX and three SHOULD. All are accepted. Points 2, 3, 6 and 8 of the review are confirmed (complete lists and `flat-1` only, loaded ground only, `hub rebuild` host-only, the step-4 tuning).

Read the review, `reviews/36-town/REPORT.md` (its JUDGMENT-CALL section), `docs/design/HUB.md` 2.5 and 3.4 to 3.5 with the corrections, and the code it names (`hub/HubData.java`, `hub/Town.java`, `hub/TownKeeper.java`, `zone/GateBuilder.java`, `zone/Placing.java`, `mixin/HubBlockChangeMixin.java`, `zone/ZoneCommands.java`) before changing anything.

**Builders:** Claude agents on Opus 5.5, two steps, one fresh builder per step. Opus and not Fable: the orchestrator has decided the designs below, so the work is carrying out stated rules; a builder that finds a rule cannot be carried out stops and says why instead of inventing another. **Review:** a fresh reviewer checks only these fixes.

## The principle

The town may remove or replace a block, entity or zone only on the strength of a record that is provably its own and still current. When that cannot be shown, it changes nothing that exists, says so in one chat line, and goes on building only on free ground. "When in doubt a logo is not built" (the brief) becomes "when in doubt nothing of the town's is taken down".

## Step A: the ledger (FIX 1, 2, 3)

1. **A seal shows that the town's file and the world were saved together** (FIX 1 and 2).
   - Every time the game writes `level.dat` it stamps `LastPlayed` (26.2: `PrimaryLevelData.writeLastPlayed`; `LevelStorageSource.LevelStorageAccess.saveDataTag`). Right after that write, this mod writes a small file of its own, `data/aresos/town-seal.dat`, holding exactly the `LastPlayed` value just written and the world's seed. Mixins on those two methods are fine; read the bytecode or sources of 26.2 to place them (the jar is under `~/.gradle/caches/fabric-loom/minecraftMaven/net/minecraft/minecraft-common-deobf/26.2/`).
   - When a world with a town opens, the town is **sealed** only if the seal file exists and its `LastPlayed` equals the one in `level.dat` (`LevelSummary` from `fixAndGetSummary`, or the level data the server read) and its seed equals the world's.
   - A world copied or renamed as a whole stays sealed (all files move together). A world that an older mod (packages 32 to 35) or plain Minecraft saved since, a `town.dat` restored from a backup or copied from another world, and a crash between the two writes all come out **unsealed**. The last is a false alarm on the safe side; say so in the report.
   - A world with no logos yet needs no seal.
2. **Unsealed means frozen.** In an unsealed world every standing logo of `town.dat` is frozen:
   - its blocks, sign and zone stay protected as before and its doorway still works, but **no pass removes or replaces anything of a frozen logo**: not when its app leaves, not on a new picture or name, not on `hub rebuild`;
   - its place counts as taken, so no second logo is built for that app while its frozen logo stands; new apps and changed places go to free places as usual;
   - one chat line when he enters: "This world was opened without the town's records since its last visit, so the town leaves its N logos as they are. Look them over, then type /aresos hub trust." (wording yours, one line);
   - `/aresos hub trust` (host-only where it is parsed) ends the freeze: the records are taken as the town's again and the seal is renewed at the next save. It says what it did in one line. Nothing else ends a freeze.
3. **The town's file is bound to its world and refused, not replaced, when it does not fit** (FIX 2, scenario B). A `town.dat` whose home differs from `hub.dat`'s, that cannot be read, or that fails the checks of point 4 is never replaced and never adopted: the file is kept as it is, the town does nothing in this world (no build, no take-down, no roads), and one chat line says so and where the file is. The town starts afresh only when he removes or renames that file himself; say how in the report and in `mod/README.md`.
4. **A loaded ledger is checked before any of it is used** (FIX 3). Refuse the whole file (point 3) when two logos name the same app, the same place, the same block position, the same sign ID or the same zone ID, or when a logo's place does not match its recorded origin. Loading must go through the same checks as `add`; a test decodes such files directly.
5. Tests (server and unit): sealed after a normal save and reopen; unsealed after a save without the seal (the older-mod case: the review's scenario with his own red concrete in a removed logo's position, which must stay); a foreign `town.dat`; a mismatched home; each kind of overlap on load; `hub trust` ending a freeze; a frozen logo whose app leaves (it stays, with its line); a whole-world copy staying sealed.

End of step A: `mod/dev/build.sh` passes; commit per point, push, and `reviews/36-town/PROGRESS.md` (new) with what is done, the decisions you took, and what step B needs.

## Step B: what the town takes down, and the rest

1. **A light he changed is his, however he changed it** (FIX 4). Any change of a recorded light's state (its level, waterlogging, anything) lets go of it at the moment it happens, as a changed block kind already does; changing it back does not give it back. Keep the accepted exception for the automatic mushroom faces. Remove the explicit `holds` call that hid this in `TownGameTests`, and test level 15 → 3 → 15 and wet → dry.
2. **A sign or zone is taken down only while it is still what the town made** (FIX 5). Before removing the sign entity: it must be a text display, at the recorded position, with the recorded text. Before removing the zone: same ID, same app, same dimension, same box. Anything else is left alone and dropped from the record, and the logo's removal still counts as done for the blocks that are the town's. A text display he edited is his. Tests with a reused ID and a changed sign.
3. **`/aresos logo <app>` never waits on a picture on the server thread** (FIX 6): read and convert the picture off the server thread (as `TownKeeper` does), then plan, check and build on the server thread in a later tick, checking that the same server and world are still running and that he still stands where he did (otherwise one line, nothing built).
4. **A name change reaches the signs** (SHOULD 7): a successful `/aresos app name` or `unname`, and a main name that changes by itself, ask the town for a pass. A test through the real command and the scheduler.
5. **A missing trigger zone is put back** (SHOULD 8): a pass checks that each standing logo's zone exists; a missing one is restored if nothing else claims that space (its box is free of other zones), otherwise the logo is left without a doorway and one line names it. Correct the report's and HUB.md's claim that the two files "cannot disagree".
6. **A first build says one line** (the orchestrator's decision): when the town had no logos and builds some in one pass, it says one line ("The town is built: 5 logos. /apps lists them." or similar), whatever the count; later passes keep the more-than-five rule.
7. **Tests that reopen** (SHOULD 9): at least one server test that saves and reloads the town's records between passes, and the client test reopens the world once (save, leave, join) and checks that nothing is built twice. Closing the server while pictures are pending must leave no stray work: a test or, if a test cannot reach it, a code path that drops pending picture work on server stop.
8. The report gets a section "Review fixes 1": per finding what changed, the tests, what ran and what it printed. HUB.md's corrections: the seal and the freeze, `/aresos hub trust`.

End of step B: `mod/dev/build.sh` twice, `mod/dev/client-test.sh` once (put other packages' pictures back as before; this package's own pictures change only if the chat lines in them change), commit, push, delete `PROGRESS.md` (its text goes into the report section), push.

## Rules

- As before. Worktree `~/AresOS-36-town`, branch `pkg/36-town`; push with `git push origin pkg/36-town`; never merge; never `--no-verify`. Build and test only through `mod/dev/build.sh` and `mod/dev/client-test.sh`; never `./gradlew`, never `--force`.
- Do not use `gh` (the account's GitHub API allowance is shared).
- Game tests build relative to their own plot and never force or release chunks they don't own.
- The repo is public: no personal data, no Mojang assets, no real app icons.
- Commit after each fix. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
