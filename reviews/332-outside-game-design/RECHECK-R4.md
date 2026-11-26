# Recheck of HOME-OUTSIDE.md revision 4

I checked revision 4 against `reviews/332-outside-game-design/REVIEW-3.md` and the last part of `reviews/332-outside-game-design/INPUTS-2.md`, which holds T498 and the lead's four decisions. My tools were read-only and nothing was run. Besides the note, I read only the code a cited line needed: `os/config/usr/libexec/aresos-settings`, the helper's registry loader and the lines of `STATE.md` the note cites. A bare `:N` is a line of `docs/design/HOME-OUTSIDE.md`.

**In short.** Findings 9 and 14 are resolved as the lead decided, and 10, 15 and 16 are fixed. Nothing the earlier reviews accepted is broken. One new contradiction in the video's off rule blocks (finding 2): the notice tells him to pick Video again, but by section 5 that does nothing while the style is already Video. One line fixes it.

## 1. Finding 9: the video

1. **Resolved by the structure the lead chose.**
   - **Its own process.** `aresos-home` never opens, decodes or draws a video (`:109`, `:293-294`, `:575-576`, decisions 2 and 19 at `:125-126` and `:167-169`). The player gets no view token, no nonce and no helper socket (`:629-630`).
   - **Its own surface.** `aresos-video` is on the background layer, made after the picture's surface, and takes no input (`:577-578`, `:606-623`, `:1612`). If labwc's stacking order proves wrong, only the video is hidden (`:623`, `:1558-1559`).
   - **Its own scope with a hard limit.** `aresos-video.scope` has `MemoryMax` and `MemorySwapMax=0` (`:579-580`, `:675-678`).
   - **A fault loses only the video.** The picture lies under it (`:581-582`, `:593-595`), and section 8 puts every screen in row 4 whatever the video does (`:991-992`).
   - **Turned off, with a notice.** One missed beat (three seconds) turns it off, and so does a second end, with no time window. A toast says so. These are not ends: a change of style or settings, a restart after the native home came back, a new supervisor (`:637-647`). Review 3's watchdog fixes are covered by the new structure.
   - **Tests.** 3V's row (`:1181`) keeps the hanging decoder, the file that fails at each loop and the growth to the limit. In every run Super opens the search and a bar click opens an app within one second, during the fault and after it. The row also checks that the native home maps no GPU driver and no decoder.

2. **Blocking: "Pick Video again" does nothing by the note's own trigger rule.**
   - **What the note promises.** When the video is turned off, "The setting stays Video". The toast says "The video is off. Pick Video again to try it." (`:642-643`), and "To tell him" repeats it (`:1304-1305`). "On again" says that picking Video again, or setting a video file, restarts the count at zero (`:645`).
   - **What the trigger rule does.** The player is restarted only by `aresos-desktop video` (`:429`). Section 5 runs that command only on "a change between `picture` and `video`, of `video-file` or of `video-battery-pause`" (`:430`).
   - **The contradiction.** Picking Video while the style is already Video is no change, and neither is setting the same file again. A builder who follows `:430` makes the toast's one instruction a no-op. He then gets the video back only by a new login, or by picking Picture and then Video.
   - **The lists also differ the other way.** A change of `video-battery-pause` restarts the player and clears the count (`:429-430`), and `:645` does not list it.
   - **Fix.**
     - Say that setting `home` to `video` while it already is `video`, and setting `video-file` to any value, ends in `aresos-desktop video`.
     - Make the lists at `:430` and `:645` the same.
     - Add a run to 3V's row (`:1181`): after the video was turned off, picking Video again plays it.

## 2. Finding 14: the second screen and the first icons

3. **Resolved.**
   - **The flip waits for 3I.** Package 12 needs 3I (`:1155`). Decision 17 (`:159-161`), section 6 (`:459-460`), the order notes (`:1208-1212`, `:1219-1221`) and question 8 (`:1273-1276`) all say so.
   - **Seeding.**
     - It is in 3I's row, as the hub's part (`:1154`), with the rule at `:723-733` and the helper's part at `:374-377`.
     - The column is seeded on a first normal home only. A laptop with a home document gets none, and so does one with an `icons.json`, also an empty one or one moved aside.
     - The test row checks both cases, and that icons he removed never come back (`:1179`).
   - **3b is split.**
     - 3b1 puts a picture and a bar on every output in a normal style. It needs 3a, 4 and 7 and nothing of 23c (`:1153`).
     - 3I and 3V both name 3b1 in their needs (`:1154`, `:1156`), and both cover every screen (`:889-890`, `:898-900`).
     - Only 3b2 waits for 23c (`:1157`, `:1227`).
     - Package 12's VM row checks both screens on a fresh install (`:1180`).
   - **Known limit.** The two-screen normal home before 3b1 is listed at `:1471-1474`.
   - **Build order.** Every row's needs come earlier in the table.

## 3. Findings 10, 15 and 16, and decision 4

4. **Fixed as the lead decided.**
   - **10.** GL is used only when the compositor draws on the Intel chip. On NVIDIA, or when the player cannot tell, it plays the capped way, or the picture shows (`:668-672`, `:1567-1568`). The memory figures are now the player's own scope and what the native home gains, measured apart (`:681-684`). That fits GL living in the player only.
   - **15.**
     - Package 12 is M (`:1155`).
     - The exception is named right after "the native home's business" (`:446-454`), and `linux-aresos` is in 3V's lead (`:1156`, `:1687-1689`).
     - G2 needs 3a (`:1148`), and gate 2 says the same (`:1757-1758`, `:1799-1800`).
   - **16.**
     - Rows without a logo go only to a view that negotiated `pins`. To any other view a home the helper made is no home (`:366-368`, `:407`, test `:1177`).
     - `made_by` and the `town` rule are at `:369-370`, `:563` and `:1514-1515`.
     - The starter apps are nine at most. With more, the rest are not pinned. With none, the bar has nine empty pins and the search is still a launcher (`:361-365`, `:1483-1484`, test `:1177`).
   - **Decision 4.**
     - Screens are told apart by make, model and serial number (`:378-379`, `:408`, `:790-792`, `:1521-1522`, to verify at `:1557`).
     - Straightening works on kept places (`:752`, `:796-799`).
     - The switchable table has a row for shut down, restart and log out (`:1418`); its citations `STATE.md:144` and `:173` match.

## 4. Do all sections agree with the new structure and order?

5. **Yes, apart from finding 2 and the nits below.**
   - **Section 1.** Decisions 2, 10, 15, 17, 18, 19 and 21 match the player and the package order.
   - **Sections 4 to 7.**
     - Section 4: the parts table and the keyboard rules.
     - Section 5: the wire, with `picture_shown`, the pipe and `aresos-desktop video`.
     - Section 6: the boot table (`:474`), the stack and the supervisor's part.
     - Section 7: `:887-900`.
   - **Section 8.** `:991-992`.
   - **Section 12.**
     - The harm rows (`:1358`, `:1361`) and rule 7 (`:1394-1396`).
     - The switchable table (`:1409-1410`, `:1418`).
     - The Known limits (`:1471-1474`, `:1523-1534`) and the layers table (`:1611-1613`).
   - **Section 10.** The table and the order notes.
   - **Section 13.** The table (`:1700-1705`) and gate 2's "Blocks" line (`:1756`).
   - **Section 11.** It records T498 in his words and says nothing is open (`:1273-1276`, `:1291-1293`).
   - **Leftovers.** I found no "twice within a minute", no video under `aresos-home.scope`'s `MemoryHigh` and no bare "3b".

## 5. What earlier reviews accepted

6. **Nothing is broken.**
   - **Gates.** Gates 1 and 3 are unchanged, and so are gate 2's rows and its VM pass.
     - Row 7 only adds the latches a start can make by itself (`:1782-1784`).
     - "The video's player is no world" (`:1762`) weakens nothing.
     - Gate 2 now also blocks 3b1, 3I, 3V and 3b2 through package 7 (`:1702`, `:1756`). That is stricter, and the change list discloses it (`:63-64`).
   - **The bar rule.** The one phrase for the zone is the same at `:139`, `:985-987`, `:1315-1317`, `:1331` and `:1614`. 3b1 adds outputs, not a new rule.
   - **Migration.** `:1134-1136` is unchanged. The flip now waits for more, no package removes a launcher, and the rows of 3I and 3V check the bar and the search during their faults (`:1179`, `:1181`).
   - **The owner's answers.** T482 to T485, T493 and T494 stand. T498 is recorded in his words.

## Known limits / nits

- **Native home restart in the Video style.** `:619-622` says the player makes its surface again. `:646-647` and `:1529-1530` say the supervisor starts the player afresh. Pick one.
- **Decision 15's "Packages 1 to 6, 8 and 11 wait for none"** (`:155-156`). Read literally, that includes 3b1, 3I, 3V and 3b2, which the next sentence, `:1162-1165` and `:1700` put behind gate 2. Write "1, 2, 3a, 4, 5, 6".
- **Section 2's monitor line** says "from package 3b1" and "Each screen has its own icons" (`:193-194`). The icons come with 3I.
- **Seeding writes two files "in the same step"** (`:727-728`). If `home.json` is written and the helper dies before `icons.json`, the document exists and the column never comes. Write `icons.json` first.
- **Seeding's test for "a home already in use" is the home document alone.** A laptop with `hub_seen` whose `home.json` was lost gets the starter column (`:1485-1487`), against the lead's "never on a home already in use". The harm is small and the note discloses it. It belongs with finding 8's single test for "has a home", which waits for the lead.
- **"Loses only the video" is about memory and the process.**
  - In the GL way the decoder shares the Intel chip and its driver with labwc, so a GPU hang could still stall the whole screen.
  - The hang run uses a stopped process as a stand-in (`:1181`). It tests neither that case nor a player that beats but shows no new frame (`:637`).
  - Add a run for the second case, and list the first as a limit of the GL way.

NOT READY: finding 2. The notice tells him to pick Video again, but by section 5's trigger rule that does not restart a video that was turned off while the style is already Video.
