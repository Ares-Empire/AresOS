# Review 3 of HOME-OUTSIDE.md (home styles)

Fresh review of revision 3 against `reviews/332-outside-game-design/INPUTS-2.md`, the earlier reviews in that folder, `docs/design/COMPONENTS.md` and the code. Read-only; nothing was run.

**Not checked.** I could only read files, so `git diff origin/main` was not run and the READY text on main was not read. "Unchanged" below means as the earlier reviews and the note's own change list record it. labwc's behaviour is not in the repo.

**In short.** Every input is folded in, and the flip is sound in structure. Two points block, both text fixes: finding 9 (video) and finding 14 (build order).

A bare `:N` is a line of `docs/design/HOME-OUTSIDE.md`.

## 1. The inputs, and what earlier reviews accepted

1. **Every input of INPUTS-2 is in, faithfully.**

| Input | Where |
|---|---|
| Styles replace "world off" | `:340-352`; the supervisor keeps its words |
| T493 | decision 17, `:354-364`, package 12 |
| The flip waits for picture, bar, search, switch and gate 2 | `:945`, `:995-998` |
| The boot starts the game only in the Minecraft style; the sign-in moves | `:366-386`, `:434-440` |
| Video: both ways measured, paused when covered and on battery, cost told before the owner picks | `:456-512`, `:1360-1367` |
| Icons on the background surface, keyboard only by a click | `:522-541`, `:1369-1373` |
| T494 | `:543-563` |
| The guideline | `:1057-1066`, `:1178-1223`; see findings 18 and 19 |

2. **Beyond INPUTS-2, and not on the note's list of three.**
   - His laptop keeps the Minecraft world (`:358-364`). T493 speaks of a fresh AresOS only. It is the safe reading, and he is told. Put it on the list.
   - `icon-align` starts on (`:561`). His words were "a setting that if activated".
   - Arrow keys, Enter and the Menu key on icons (`:538-541`).
   - The starter icons of question 8.

   The rest is detail a design needs. On the three the note lists, keep all three:
   - Without row 8 an unreadable pin file still ends the supervisor before anything shows (`os/config/usr/libexec/aresos-desktop:4568-4578`).
   - Without package 11 the bar is empty, because only the mod makes pins.
   - Without package 5 the first maximized app hides the bar for good. `rc.xml:47` maximizes `foot`, for one.

3. **What earlier reviews accepted still holds.** Gate 2's rows 1 to 7 and its rig-only VM pass read as RECHECK-4 left them. Gates 1 and 3 are not touched. The bar's one phrase for the zone is the same in sections 8, 11 and 12. No package removes a launcher. T482 to T485 stand.

4. **Should fix: the keep rule can start the world by itself and can overwrite his settings.**
   - It runs at every supervisor start and writes when "the file has no `home` value" (`:358-363`).
   - `aresos-settings` reads a file it cannot parse, or one of another version, as no values at all (`os/config/usr/libexec/aresos-settings:42-59`). Its `set` then writes a new file holding only the new value (`:110-115`).
   - So a damaged or newer-format file is replaced at boot, without his act.
   - A laptop on Picture whose file lost `home` gets its world started by a new supervisor. Gate 2's row 1 rules that out (`:1493-1494`). The note names only the `previous` case (`:1267-1271`).
   - Fix: write only when the file was read cleanly and holds no `home`. With an unreadable file, write nothing and say which style the session takes. Add both cases to package 12's VM row.

5. **Should fix: two surfaces can now hold the keyboard, but `view_focus` and `view_alive` still mean one.**
   - Revision 2 had only the search. Now the background takes the keyboard after a click (`:227-229`).
   - Super's route 1 falls through when the view "has not reported `view_focus` true within a second" (`:828-830`). With the background focused that is already true, so a search that fails to open is not seen.
   - `view_alive` is sent by "a view that holds the keyboard", and three silent seconds end the native home (`:309`). Read literally, a three-second stall after a click on the desktop kills the bar and the search.
   - Say that both rules are the search's alone, or let `view_focus` name the surface.

## 2. The default flip and the boot

6. **The boot table against the supervisor** (`os/config/usr/libexec/aresos-desktop`).

| The note says | The code | Holds? |
|---|---|---|
| A launch first checks the pins and makes the instance | `preflight()`, `:1943-1952` | Yes |
| An unreadable pin file ends the supervisor before anything starts | `supervise()`, `:4568-4578` | Yes; row 8 must move it |
| With no launch there is no helper | `ensure_helper()`, `:2005-2009` | Yes; package 1 stands before any normal-style boot |
| The guard is asked only before a game starts | `:1967`, `:2201` | Yes |
| A latch opens the window at boot | `:1838-1840` | Yes |
| The first start is SETUP: Prism without a world, never covered | `:1939-1940`, `:1989-1992` | Yes; so the sign-in comes with his first pick |
| A first start that ends without a home goes back to Picture | Today it stays in SETUP with `retry` (`:2425-2426`, `:2443`, `:2535-2537`) | New in package 12; the signal is Prism's exit |
| A shutdown in a normal style has "no black screen" | `request_stop()` goes black before it knows nothing runs (`:3221-3222`) | Not today; G2 changes it or the phrase goes |

7. **A fresh AresOS cannot start without a launcher, by the plan's order.**
   - Package 12 needs 3a, 4, 5, 6, 7 and 11 (`:945`), and 6 needs 23c's Super step. So the picture, the bar with starter pins, Super's search and the home menu exist before the flip.
   - The way to the Minecraft style is the home menu, the search and `aresos-settings set home minecraft`.
   - Recovery is section 12's chain, and the recovery key is untouched (`os/config/usr/share/aresos/labwc/rc.xml:19`).
   - One gap: the launcher check guards a change of style, not a boot. The chain covers a native home that fails (`:1137`). It does not cover a helper that keeps failing, whose window "stays for a running world" (`:274-275`). Say what opens in OFF then. With no live helper the supervisor has nobody to signal for Super.

8. **Should fix: "has a home" is tested two ways, and one way needs the pin file.**
   - The keep rule asks for `hub_seen` or "a home folder in his worlds folder" (`:361-362`). The boot rule asks "has no home" (`:384-386`).
   - A first home that died half made is a folder without `hub_seen` (`os/config/usr/libexec/aresos-desktop:1935-1940`, `:2675-2687`). There the two rules disagree, and the outcome depends on which runs last.
   - The folder's name comes from the pin file (`:891`). Gate 2's row 8 says a normal style never reads it (`:1510-1512`).
   - Define one test, say how the half-made home counts, and make it work without the pin file.
   - `forget-hub` clears `hub_seen` (`:2616-2624`). Say that his laptop then boots to the picture home.

## 3. Video and icons: real harm

9. **Blocking: in the Video style the home can be lost in two ways that rule 5 does not see.** The video is decoded inside the one program that is also the bar and the search (`:493-494`, `:1286`). Rule 5 turns the video off only "if the native home ends twice within a minute" (`:500-502`). Section 12 gives that as the whole answer (`:1136`).
   - **A stall is not an end.** The memory answer is `MemoryHigh` on the home's scope (`:502-504`, `:1172-1173`). `MemoryHigh` slows a scope; it does not end it. A video that grows to the ceiling leaves a bar and a search that crawl, and nothing turns the video off. A decoder or driver that hangs does the same. The alive beat is sent only while the view holds the keyboard (`:309`).
   - **A slow repeat is not "twice within a minute".** A file that ends the player at each loop, 90 seconds apart, never meets the rule. The restart waits grow to 60 seconds (`:197`), so the bar and the search are away much of the time.
   - In a normal style that program is the only launcher.
   - **Fix in the note:**
     - Count every end while a video was playing, with no one-minute window.
     - Make a stall count: a beat whenever a video plays, and Super's "the view did not answer" in the Video style.
     - At the ceiling the video stops before the scope is throttled.
     - A restart for a change of style is not an end.
     - Add three rows to 3V's test: a decoder that hangs, a file that fails at each loop, a player that grows to the ceiling. Each time the bar and the search answer within a stated time.

10. **Should fix: rule 3 can contradict itself.** "On the compositor's chip, never on NVIDIA" (`:495-497`) has no answer when labwc draws on NVIDIA, which the note lists as unknown (`:1316`). A wrong guess costs two and a half cores (`docs/design/LAPTOP-HOME.md:350-357`). Say that the GL way is off when the compositor is not on the Intel chip. With GL the whole program draws with GL, so 3V's memory figure must be of the whole home.

11. **Icons and the keyboard: the rule is right, the fallback is missing.** "Only by a click" is INPUTS-2's rule. Whether labwc gives an on-demand surface the keyboard when it maps, or when the last window closes, is listed to verify (`:1308-1309`). The native home restarts by itself, so a wrong answer takes the keyboard from his app at each restart. Add the fallback: then icons get no keyboard at all. The arrow keys are the note's own addition and can go.

12. **Icon places: I found no way to lose them.** The file is written whole and a bad file is moved aside. A removed app keeps its entry for 30 days. A smaller screen changes what is drawn, not what is kept (`:574-602`). An older release never rewrites the file, so `previous` leaves it alone. Two soft spots:
    - Screens are told apart by connector name (`:595`, `:1285`). A dock can give the same monitor another name, and his icons then look lost. Use the monitor's make, model and serial where the output gives them.
    - "Straighten icons" on a screen that came back smaller would save the displaced places. Say that it works on kept places.

13. **Memory and battery are bounded.** A normal style frees about 1.4 GiB and costs 60 to 80 MiB plus icons at drawn size (`:648-664`). Video is not offered before its cost is measured and told (`:510-512`). Apart from finding 9, nothing here threatens a 16 GB laptop.

## 4. The packages in section 10

14. **Blocking: icons and video on a second screen have no buildable place, and the first icons have no package.**
    - Package 3I includes "several screens" and needs only 4 and 7 (`:946`). Before 3b there is one picture surface (`:938`). 3b comes after 3I and 3V and waits for 23c (`:948`). So 3I cannot finish where it stands.
    - "One video for every screen" (`:695-696`) is in no package's row. 3b's row is the picture and the bar, sized S.
    - The flip also comes before 3b. Section 7 says a normal home shows on both screens (`:687`). What a fresh AresOS with a monitor shows before 3b is not said.
    - Question 8 recommends starter icons the first time a normal home shows (`:1070-1073`). The flip does not need 3I, so that first time has no icons whatever he answers. No row seeds them.
    - **Fix:**
      - Split 3b. Its "a surface on every output" part needs no 23c in a normal style. Put it before 3I and name it in 3I's and 3V's needs. Or cut "several screens" from 3I and give 3b the icons and the video on the second screen, with a new size.
      - Add the two-screen normal home before 3b to Known limits.
      - Put the seeding in 3I's row, and say whether it runs on a home already in use.
      - Say in question 8 that the flip has no icons until 3I, or make the flip wait.

15. **Should fix: three rows of the table.**
    - **Package 12 is not S.** It adds a supervisor transition with a settings write (`:633`), the boot rule, the keep rule, the first start from the home menu, the install guide and a VM row with six cases (`:968`). That is M.
    - **Package 3V needs `linux-aresos`.** Rules 5 and 6 have the supervisor start the home without the video, or in another form (`:500-508`). That contradicts "the native home's business, not the supervisor's" (`:351`). Name the exception there.
    - **G2 needs 3a.** Row 8's test starts "the helper and the native home" (`:1523-1524`). The supervisor starts the native home only from 3a on (`:194-195`).

16. **Should fix: package 11's own home document needs a wire rule.**
    - Its pins "carry no block logo" (`:282`). Today's reader expects 144 logo cells in every row (`os/config/usr/libexec/aresos-laptop-home:291-301`, `:945`). Send logo-less rows only to a view that negotiated `pins`.
    - The `town` picture "needs a published home" (`:452`). Say that a document the helper made does not count.
    - The starter apps come from a folder the note did not read (`:1332`). Say what happens with more than nine, or none.

17. **The rest holds.**
    - Needs are met in the listed order for G2, 7, 4, 5, 11 and 12.
    - Each new package has a "must still work" row and keeps the old path:
      - `set_pin` is refused while the mod is connected.
      - A broken `icons.json` costs only the icons.
      - A failed video leaves the picture.
      - The flip leaves a laptop with a home alone.

## 5. The guideline and the "Normal" look

18. **The guideline's words are faithful; its reach is not complete.** Section 12 says "a guideline, not a rigid rule" and uses the exception once, rightly, for the password windows (`:1180-1195`).
    - "Tools on or off" is one of his three kinds of switch. No row covers it, and the summary says "two switches" (`:1222-1223`). Add a row, or say tools are outside this note.
    - The status is mixed. Section 11 files the Normal look under "Answered" (`:1055-1066`). Section 12 calls it "question 7" and a "recommendation". Section 10 says "if the owner wants it" (`:985`). His guideline is answered; "one look, not a switch for each piece" is the lead's reading. His own example was "a normal taskbar or the AresOS one". File it under "To tell him" or as open.
    - The line in quotation marks at `:1058` is not INPUTS-2's wording.

19. **"Normal" as a look holds in direction, not against COMPONENTS.md as written.** Pieces ask the pack by role, and a missing pack falls back to A. These must change in COMPONENTS.md first:
    - Section 1 puts "where its parts sit relative to each other" in the piece's function (`docs/design/COMPONENTS.md:45-48`). The note moves the bar's shape into the pack (`:1211-1212`).
    - Every sprite scales by whole factors without smoothing (`docs/design/COMPONENTS.md:238-239`).
    - Every look has the same frame geometry and title font, so `rc.xml` never changes with the look (`docs/design/COMPONENTS.md:600-602`, `:696`). The fonts and the corner radius are in the image's file (`os/config/usr/share/aresos/labwc/rc.xml:8-15`). A switch at run time cannot edit an image file. "One thing" (`:1190`) undercounts this.
    - The fourth value of the look setting is already the Ares-apps look (`docs/design/COMPONENTS.md:613-614`, `:1449`). The owner planned "2 designs" (`STATE.md:175`). The note does not say whether "Normal" is that look or a third.

    None of this blocks. The look is "later", and he sees it first.

## 6. Section 11

20. **One open question, his to judge, with a recommendation.** Question 8 is right in kind; finding 14 covers its timing. Three more points:
    - "On from the start" for `icon-align` sits inside the answer to T494 (`:1052`). It is the note's choice. Move it to "To tell him".
    - Add to "To tell him": the default look is B (`os/config/usr/libexec/aresos-settings:24`). After his first try of the Minecraft world the game is installed, and his normal home turns to Minecraft textures.
    - When the Normal look is shown, ask whether it is the Ares-apps look.

## Known limits / nits

- A latch made during a normal-style start opens the window too (`os/config/usr/libexec/aresos-desktop:1828-1830`, `:1769-1777`). Gate 2's design step should name those.
- "The picture home … stay usable the whole time" (`:437`): the icons hide as soon as the style is Minecraft (`:1289-1290`).
- "When he closes the sign-in" (`:438-439`): the supervisor learns it from Prism's exit, ten seconds later (`os/config/usr/libexec/aresos-desktop:2478-2480`).
- Two rows of package 7's transition table hold only from package 12 (`:629`, `:633`). Mark them.
- "The keeper tries five times and then leaves a terminal" (`:152`): each failed try opens one (`os/config/usr/libexec/aresos-desktop:4575-4578`).
- `video-battery`: `always` means always paused on battery. It is easy to read the other way.
- "Never more than half a cell" (`:569`): a row and a column snap together move half a cell on each axis.
- "Icons at rest never jump" (`:547`) against straightening once when the setting is turned on (`:559-560`). Say "on a drop".
- The Menu key opens a menu (`:540`) that is "pointer-only" (`:231`).
- Say that icon pictures are dropped in the Minecraft style. 3I should also time 200 icons: each picture is one sandboxed child (`os/config/usr/libexec/aresos-laptop-home:214-278`).
- `set_setting` comes from "desktop and views" (`:310`). Say who may set the two path values; the video's file is decoded outside the sandbox.
- The switchable table has no row for shut down, restart and log out. The AresOS menu lists none either (`STATE.md:144`), but a fresh user meets the gap first.
- Decision 18's "and nothing else" (`:99-100`): the look-B sync also runs at session start and reads the instance (`docs/design/COMPONENTS.md:1553-1554`).
- Stale references: `STATE.md:202` and `:204` are now `:205` and `:207`. `docs/HUB-HANDOFF.md:46` and `:112` are now `:54` and `:120`.

NOT READY: (1) finding 9, in the Video style a stalled or slowly failing player takes the bar and the search away and rule 5 never turns the video off; (2) finding 14, package 3I's several-screens work, the video on a second screen and question 8's first icons have no buildable place in section 10's order.
