# 36 review fixes 2: an unproven town changes nothing, and a hand-built sign is taken down only while it is the mod's

Follow-up on the same branch (`pkg/36-town`, PR #59). The fix check of round 1 at `e9995dee` is `reviews/36-town/REVIEW-2.md` (gpt-6-astra, high): CHANGES-NEEDED, two FIX and one SHOULD. All three are accepted. Everything else of round 1 is confirmed: refused files and the load checks, the light rule, the town's sign and zone checks, the picture reader and server stop, names, doorway recovery, the reopen tests, and the rules that stood.

Read `REVIEW-2.md`, `briefs/36-review-fixes-1.md` (the principle stays), the section "Review fixes 1" of `reviews/36-town/REPORT.md` with JUDGMENT-CALLs A* and B*, and the code it names (`hub/HubData.java` `join`, `sealable`, `trust`; `hub/TownSeal.java`; `hub/TownKeeper.java` `frozen`, `trusted` and the pass; `hub/Town.java`; `hub/HubCommands.java`; `zone/GateBuilder.java` `made`, `remove`, `takeDown`; `zone/AppZone.java` `Gate`; `zone/PictureReader.java`) before changing anything.

**Builder:** one Claude agent on Opus 5.5, one step. Opus and not Fable: the orchestrator has decided the designs below, so the work is carrying out stated rules; a builder that finds a rule cannot be carried out stops and says why instead of inventing another. If the budget runs out first, commit what is done and leave `reviews/36-town/PROGRESS.md` with what remains. **Review:** a fresh reviewer checks only these fixes.

## 1. An unsealed world freezes the whole town, not only its recorded logos (FIX 1)

Why: a `town.dat` restored or copied on its own can leave out a logo that still stands (its blocks, sign and zone are in the world). The town cannot tell that app from a new one, so building "new" apps on free ground can build that app twice, and an empty restored file today skips the seal check and is sealed again at the next save.

1. **When the seal is checked.** The seal is checked whenever the world has a seal file or its town file holds logos. A world with neither is a town that never had logos: not frozen. A world whose seal does not hold, but whose seal and town file both show a town without logos (the seal's fingerprint is that of an empty town of this home, and the file is empty), needs no trust either: nothing of the town can stand there. Every other case where the seal does not hold is unsealed, whatever the town file holds (an empty file too).
2. **Unsealed means the town changes nothing in the world until `/aresos hub trust`.** No logo built (also not for an app the records do not know), none removed, renewed or rebuilt, no road paved, no missing zone put back (this replaces JUDGMENT-CALL B4's "a frozen logo's missing zone is put back"), and `hub rebuild` refuses with the freeze line. What stays: recorded blocks, signs and zones protected as before, doorways working, a light he changes leaving the record (that only gives ownership up), `/apps`, and hand-built gates (`/aresos logo`, not the town).
3. The freeze is one state of the town, not a set of apps; keep it as simple as that. It lasts across visits because the seal is not renewed while it lasts (as today). `/aresos hub trust` stays the only way out and stays host-only where it is parsed.
4. **The lines.** On entering a frozen world, one line, also when the town file holds no logo, for example: "This world was opened without the town's records since its last visit, so the town builds and removes nothing. Look over its 4 logos, then type /aresos hub trust." The trust reply says what trust means in one line, including that anything of a logo the records do not hold is his from now on (the town may then build that app a new logo). Wording yours.
5. **Starting afresh after a refused file** (`mod/README.md`, HUB.md): moving `town.dat` away leaves a seal that no longer fits, so the town is frozen once more and asks for trust. Say that, or have the instructions name both files; choose one and say which in the report.
6. Tests (server):
   - a subset restored: save with Chrome and Discord standing, put back an earlier `town.dat` that holds only Chrome, reopen: the town is frozen, a pass builds no Discord logo and takes nothing down, Discord's blocks, sign and zone are untouched, the line is said;
   - an empty `town.dat` restored while logos stand: frozen, nothing built, and the next save does not seal it;
   - saving and reopening while frozen, without trust: still frozen;
   - after trust: the pass runs, and the seal holds after the next save and reopen;
   - the older-mod case of round 1 (a save without the seal): a new app gets no logo while frozen, and gets one after trust;
   - `/aresos hub trust` through the real command from a source that is not the host: refused, still frozen (if a game test cannot make such a source, test the parsed requirement directly and say so);
   - a town file with overlapping records written to disk and opened (not only decoded): refused, the file untouched.

## 2. A hand-built gate's sign is taken down only while it is the one the mod made (FIX 2)

1. A hand-built gate (`/aresos logo <app>`) records its sign's planned place and the text it was built with, in its record in `zones.dat` (`AppZone.Gate`), as the town's records do. Removal takes the sign down only while it is a text display at that place with that text (the same check as the town's, `made`); anything else stays and the record lets go of it.
2. A record without that (built by packages 33 to 35, or rewritten by an older mod) never takes its sign down: the gate's blocks come down as before, the sign stays, and the reply says in its one line that the sign stayed and is his.
3. The new fields are optional in the codec: check what an older mod (packages 33 to 35) does with a `zones.dat` that has them (reads and keeps, reads and drops, or fails) and say it in the report. A record an older mod rewrote without them falls under point 2.
4. JUDGMENT-CALL B1 is withdrawn; say so in the report.
5. Tests through the real removal path (`/aresos logo remove` or `GateBuilder.remove`): an edited hand-built sign stays; a text display of his with the sign's ID at another place stays; an unedited sign is taken down; an old record without the sign's place and text leaves the sign and says so.

## 3. The picture reader's test waits for its own clean-up (SHOULD 3)

`PictureReaderTest` checks `waiting()` after `get()` on the result, but the removal runs in `whenComplete` after that. Wait for the clean-up (an executor barrier, as the shutdown test does) so the test cannot fail after a correct read.

## Known limits for the report

Say these in "Review fixes 2", each in a sentence or two:
- A failed `level.dat` write: the seal is written after `saveDataTag` returns, so it may name a `LastPlayed` that is not on disk; the next visit is then unsealed, a false alarm on the safe side. Check in 26.2 what `saveDataTag` does when the write fails, and say it.
- A crash in the middle of a save can leave blocks of a new logo in the world without its record; they are his then, and the town may build that app again. As with any data the game saves beside its chunks.
- Trust takes the records as they are: a logo they do not hold stays as his blocks and his doorway, and the town may build that app a logo of its own (the trust line says so).
- Another program writing into the world folder while the game runs.

## Verification

- A test for each fix that fails without it, where it can; say which claims are from reading.
- `mod/dev/build.sh` twice and `mod/dev/client-test.sh` once at the end (put other packages' pictures back as before; this package's pictures change only if their chat lines change).
- The report gets a section "Review fixes 2": per finding what changed, the tests, what ran and what it printed. HUB.md's freeze and hand-built-gate text and `mod/README.md` follow the change.

## Rules

- As before. Worktree `~/AresOS-36-town`, branch `pkg/36-town`; push with `git push origin pkg/36-town`; never merge; never `--no-verify`. Build and test only through `mod/dev/build.sh` and `mod/dev/client-test.sh`; never `./gradlew`, never `--force`.
- Do not use `gh` (the account's GitHub API allowance is shared).
- Game tests build relative to their own plot and never force or release chunks they don't own.
- The repo is public: no personal data, no Mojang assets, no real app icons.
- Commit after each fix. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
