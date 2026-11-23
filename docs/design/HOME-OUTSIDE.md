# The home's parts outside the game

**Status.** Design note for board brief 332, written 2026-11-21 by one Fable design agent with read-only tools.
**Revision 4, after review 3 (2026-11-22).** Revisions 1 and 2 followed reviews 1 and 2
(`reviews/332-outside-game-design/REVIEW-1.md`, `REVIEW-2.md`, both NOT READY). The lead then fixed wording points by
hand, and the fourth recheck found the note READY (`reviews/332-outside-game-design/RECHECK-4.md`). Revision 3 folded
in `reviews/332-outside-game-design/INPUTS-2.md`: the owner's idea of home styles, his answers T493 and T494, and
`linux-desktop`'s points on video, icons and memory. Review 3 (`reviews/332-outside-game-design/REVIEW-3.md`) found
it NOT READY on two points: a video could take the bar and the search away, and the second screen and the first
icons had no place in the build order. This revision applies the lead's four decisions on that review and records
the owner's answer T498. Both are the last two parts of INPUTS-2. It has not been reviewed yet. Nothing here is
built. It decides the structure for the hub (`linux-hub`), the desktop (`linux-desktop`) and the supervisor
(`linux-aresos`).

**The lead's scope decision (2026-11-21).** The brief says this note gives the sleeping world its place and does
not design swap or prefetch. Two reviews pushed the sleeping world and memory pressure into full mechanism design.
That is the work of its own study (board T364). So this note keeps the structural decisions: the states exist, the
supervisor owns stop and admission, and the world is the one to give way. Review 2's blocking points 1, 2 and 3 are
now three gates (section 13). Each says what must be true, how a test shows it, and which package waits for it.

**What revision 4 changed**

- **The video is a program of its own** (the lead's decision 1, for review 3's finding 9). The player, working name
  `aresos-video`, has its own process, its own surface above the picture, and its own scope with a hard memory
  limit. `aresos-home` never decodes video. A video that stalls, leaks or crashes loses only the video: the picture
  shows under it, and the bar and the search are untouched. After a second end or one missed beat the supervisor
  turns the video off and says so (sections 4, 6 and 12).
- **The flip waits for the icons** (decision 2; the owner, T498). He chose the starter icons column, so package 12
  now needs package 3I. 3I seeds the column once, on a first normal home, and never on a home already in use.
- **Package 3b is split** (decision 2). 3b1 puts the picture and the bar on every screen in a normal style. It needs
  nothing of 23c and comes before 3I and 3V, which then cover the second screen themselves. 3b2 is the second screen
  beside the world, and it alone waits for 23c. The two-screen normal home before 3b1 is a Known limit.
- **Findings 10, 15 and 16** (decision 3).
  - GL video only when the compositor draws on the Intel chip.
  - Package 12 is M. Package 3V has `linux-aresos` in it, and the supervisor's part in the video is named as the
    one exception in section 6. G2 needs 3a.
  - Package 11's pins without a logo go only to a view that negotiated `pins`. The `town` picture does not count a
    home the helper made. The starter apps are nine at most, and may be none.
- **Finding 12's soft spots and the nits** (decision 4).
  - Screens are told apart by make, model and serial number. "Straighten icons" works on kept places. The
    switchable table has a row for shut down, restart and log out.
  - The nits, each fixed where it stood: the keeper's terminals (section 3); decision 18's "nothing else"; the
    icons during a first start; how the supervisor learns that the sign-in was closed; two transition rows marked
    "from package 12"; `video-battery` is now `video-battery-pause`; "half a cell on each axis"; "on a drop"; no
    Menu key on icons; icon pictures dropped in the Minecraft style, and 200 icons timed; `set_setting` never
    carries a path; the latches a start can make, named for gate 2; four stale line references.
- **T498 is answered** (section 11). No question is open.
- Sections 1 to 13 keep their numbers. Decisions 1 to 20 keep theirs; 21 is new.

**Beyond the lead's decisions, for the lead to confirm or drop.** The new structure needed these, and no input
names them.

- **In the Video style the icons get a surface of their own,** `aresos-icons`, on the bottom layer. The video's
  surface lies above the picture, so icons drawn on the picture would be hidden. INPUTS-2 put the icons on the
  picture's surface. That still holds in the Picture style. `linux-desktop` confirms the Video case.
- **The player holds no view token.** The supervisor tells it what it needs, and its beat goes to the supervisor on
  a pipe. One line is new on the helper's wire, `picture_shown`, and one supervisor command, `aresos-desktop video`.
- **Starting values:** three seconds for a missed beat, one restart after a first end, and swap closed to the
  player's scope.
- **3b1 also carries the bar** on every screen in a normal style. The lead named the picture surface.
- **The seeding moment:** when the helper makes its own home document and no `icons.json` exists.
- **The starter apps** are the first nine registry entries that can start, by file name.
- **Gate 2 through package 7.** 3b1, 3I, 3V and 3b2 need package 7, so they stand behind gate 2 with it. Revision 3
  listed 3I and 3V under "no gate".

**Review 3's findings that this revision leaves as they were.** The lead's four decisions do not name them. They
wait for the lead.

- Finding 2: three more things beyond INPUTS-2 that revision 3 did not list. His laptop keeps the Minecraft world,
  `icon-align` starts on, and the keys on icons.
- Finding 4: the keep rule when the settings file cannot be read.
- Finding 5: `view_focus` and `view_alive`, now that two surfaces can hold the keyboard.
- Finding 6, last row: a shutdown in a normal style still goes black first today (supervisor `:3221-3222`).
- Finding 7: what opens in OFF when the helper keeps failing.
- Finding 8: one test for "has a home".
- Finding 11: the fallback if labwc gives an on-demand surface the keyboard by itself.
- Findings 18 and 19: "tools on or off", and the "Normal" look against COMPONENTS.md as written.
- Finding 20: where "on from the start" for `icon-align` is filed, and telling him about look B.

**From revision 3, unchanged**

- **Home styles** replace "the world-off switch" (section 6): Picture, Video and Minecraft world. Every rule, state
  and gate for turning the world off and on is kept. To the supervisor a normal style is still "world off".
- **A fresh AresOS starts on the picture home** (the owner, T493). The owner's laptop keeps its Minecraft world until
  he switches.
- **Section 6 says what the supervisor's boot does in each style,** and that Prism's sign-in comes when he first
  picks the Minecraft world.
- **Revision 3's three additions stay:** gate 2's row 8, package 11, and the flip waiting for package 5. Review 3
  found each of them needed, and the lead's decisions build on them.
- **"Switchable" is the owner's guideline** (section 12, and answer 7 in section 11): AresOS can run as a normal OS,
  and its designs and features are switches, without forcing a key piece to be switchable where that isn't needed
  or possible. Nothing in the structure blocks it.
- **The `rc.xml` facts follow this checkout.** Package 329 already turned off labwc's clicks on a bare desktop.

**Sources.** The documents and code the brief names, as they are in this checkout, with INPUTS-2 and review 3.
Nothing was run and nothing was measured; every number names where it comes from. labwc's own behaviour, the image's
effective systemd-oomd settings, the image's video decoding and `briefs/328-look-around.md` could not be read here.
The image's registry folder could not be listed. What rests on them is marked.

**Words used below**

| Word | Meaning |
|---|---|
| Home style | What his home is: Picture, Video or Minecraft world. One setting, `home` (section 6). |
| A normal style, the normal home | Picture or Video: a background, his icons, the bar and the search. No game runs. |
| The world | The Minecraft home: the game, its window (`aresos-desktop`) and the mod. |
| The helper | `os/config/usr/libexec/aresos-shell`. "Helper `:N`" is line N of that file. |
| The supervisor | `os/config/usr/libexec/aresos-desktop`. "Supervisor `:N`" is line N of that file. |
| The native home | One program that draws the picture, the icons, the bar, the search and toasts without the game. It never decodes video. It grows out of `os/config/usr/libexec/aresos-laptop-home` ("laptop home `:N`"). Working name: `aresos-home`. |
| The player | The program that plays a video background, in a process, a surface and a scope of its own (section 6). Working name: `aresos-video`. |
| Home output | The screen the world shows on, or would show on (package 23c's rule). |
| Covered | A window fills the output: one on it is maximized or full-screen and not minimized. That is today's rule, applied per output. A full layout counts once the covering package ships (T372/T373). The world's own window, the start-up cover and the black screen never count. |
| Icon | An app's picture and name on the normal home (section 6). Not a bar slot and not a status icon. |
| Starter apps | The apps of the image's reviewed registry that a first normal home pins and shows as icons: nine at most (section 5). |
| Still | A picture of the world's last frame, made by the mod, kept in his cache folder. |
| Pending start | His own request to start the world that waits for memory. One durable record of the supervisor's, never a timer (section 6). |
| Gate | A condition that a test must show before a package starts (section 13). |

---

## 1. The decisions in short

1. **The home has three layers.** The helper holds the facts. The native home shows what must show without the game.
   The world is the third layer, and it is optional.
2. **One native program, always running.** It draws the picture, the icons, the bar, the search and toasts. A GTK
   program costs about 50 MiB each, so these are surfaces of one program. It never decodes video (decision 19).
3. **It is the laptop home, grown.** That file is split into modules first. `linux-desktop` leads the program and
   the hub leads its content modules.
4. **The helper lives as long as the supervisor.** Today it is started for each game launch. It must run with no
   game at all, its restarts must never stop for good, and every new helper gets the running launch's nonce.
5. **The helper is the one source** for programs, My apps and pins, icons, windows and outputs. `aresos-shell/1.3`
   adds `apps_state`, `activate_app`, `screens`, the window list, and search for a view.
6. **A left click means "open or bring back" everywhere**: bar, hotbar, gate, `/name`, search, icon. "New window" is
   a right click on the world's hotbar slot and a row in the app's menu outside.
7. **Both bars stay** (the owner, T483). In the world: the game's own hotbar, with open and active marks. Wherever
   the awake world is not in view: the bar outside.
8. **A bar on every screen, by one rule** (the owner, T484 and T485; section 8). It is `shown` on a screen nothing
   fills, also one with part-screen windows, and reserves its height there. It waits at the bottom `edge`, reserving
   nothing, while a window fills the screen. On the home output it reserves nothing while `world` is not `off`, and the awake world's own hotbar is the bar there.
9. **Search is outside the game.** Super opens it over anything, on the home output. Nothing is minimized for it.
10. **The background is one surface per output,** wherever the awake world is not showing. It holds a picture: the
    default is a plain picture in the look (the owner, T482), and black, a picture of his and the town are the other
    kinds. In the Video style a video plays above it, on a surface of the player's. In both normal styles his icons
    sit over the background.
11. **The home has a style: Picture, Video or Minecraft world** (the owner, 2026-11-22). It is a setting and holds
    across restarts. A normal style closes the game and Prism. In a normal style only his own request starts the
    world. A change to a normal style is refused while there is no launcher outside the game.
12. **A sleeping world is never a frozen window on screen.** Its still is on the picture and its window is
    minimized before anything is frozen.
13. **The supervisor owns stop and admission.** It alone starts, stops, freezes and thaws the world. A stop of a
    sleeping world needs no thaw and is not a crash. A start out of OFF and every wake is admitted, not forced.
14. **The world is the one to give way** when memory is full, and by the supervisor's own hand. Today nothing makes
    that true. It is an aim until gate 3 shows it.
15. **Three gates** stand before the packages that could hurt him (section 13). Package 7, the style switch, waits
    for gate 2, and package 12, the default flip, waits for it through package 7. Package 9, the sleeping world,
    waits for gates 1 and 3. Packages 1 to 6, 8 and 11 wait for none. Packages 3b1, 3I, 3V and 3b2 have no gate of
    their own; each needs package 7 and so stands behind gate 2 with it.
16. **There is always a way back.** Section 12 has the chain. Its last link is a message window, never a start.
17. **A fresh AresOS starts on the picture home** (the owner, T493). The owner's laptop keeps the Minecraft world
    until he switches. The default flips in package 12 and not before, and package 12 waits for the icons (package
    3I).
18. **In a normal style the session needs nothing of Minecraft's.** The supervisor's boot starts the helper and the
    native home, and in the Video style the player. It touches nothing of Minecraft's: no pin check, no Prism, no
    sign-in. Prism's sign-in comes when he first picks the Minecraft world. The look's sync step is not part of that
    boot: it runs at session start in every style, reads the instance if there is one, and the desktop never waits
    for it (`docs/design/COMPONENTS.md:1553-1555`).
19. **A video is a background like the picture, played by a program of its own:** looped, silent, paused when
    covered and on low battery. The player has its own process, surface and scope with a hard memory limit. A video
    that stalls, leaks or crashes loses only the video. It costs nothing in the other styles.
20. **Icons sit over the background in the normal styles** (the owner, T494). He places them freely, and a setting
    straightens the lines and grids he makes. The helper keeps their places.
21. **A first normal home has the starter apps as icons in one column** (the owner, T498), and pinned in the bar.
    They are seeded once, and never on a home already in use.

---

## 2. What he will see

- **A fresh AresOS** (after package 12). It starts with a plain picture, the starter apps as icons in a column at
  the top left, a bar at the bottom with the same apps pinned, and Super's search. Nothing asks him to sign in.
- **Making the home his own.** He drags icons where he wants them. He drops one near a row of others and it snaps
  into the row. He removes one with a right click. He sets a picture of his, or a video that loops silently behind
  his windows. If the video ever fails, the picture is there again, and the bar and the search never notice.
- **Picking the Minecraft world.** He picks "Minecraft world" in the home menu. The first time, Prism opens and asks
  him to sign in, and Minecraft downloads. When his home is ready, the picture gives way to the world. After that a
  pick starts the world as a boot does today.
- **His own laptop.** Nothing changes until he picks another style. When he picks Picture, the world is saved and
  closed, and about 1.4 GiB is free again. Super's search, the bar and every app work as before. The world stays
  closed until he picks it again.
- **Working in a full-screen app.** The bar is hidden. He moves the pointer to the bottom edge and rests there for
  a third of a second. The bar slides up over the app. Chrome's slot is marked open and lit as active. He clicks
  Terminal: its window comes back. The pointer leaves the bar and the bar slides away.
- **With the monitor plugged in, in a normal style** (from package 3b1). Both screens show the picture and a bar.
  Each screen has its own icons.
- **With the monitor plugged in, in the Minecraft style** (package 23c's plan). The world moves to the monitor. The
  laptop's screen shows the picture behind its apps, with its own bar. Windows there stop above the bar.
- **The world asleep** (package 9, after its gates). Its last view stays on screen, and the bar stands where the
  hotbar stood. A click on the view brings the world back to life. On a full laptop a line says the world is waiting
  for memory, and his apps stay.

---

## 3. Today, from the code

Facts read in this checkout. They are why his wishes cannot be met by settings alone, and what the new states must
fit into.

| Fact | Where |
|---|---|
| The helper is started for each game launch, with that launch's nonce in its environment. Without a launch it is not started. A game started from Prism's own window gets a fresh nonce and a new helper. | supervisor `:1988`, `:2005-2009`, `:2212-2215`; helper `:4705-4710` |
| The helper dies with the supervisor. Its restarts end after five failures in a minute, until the next launch. | supervisor `:3804-3805`, `:2036-2048` |
| The supervisor's one packet to the helper (`windows`) is a plain write, read 64 bytes at a time. Its answer is a `windows` report that carries the request's ID. There is no other acknowledgement. | supervisor `:3809-3816`, `:2095-2102`; helper `:4602-4615`, `:3984-3989` |
| A fresh, valid `open_app` starts a launch. No request brings an app's window back. A resent request ID gets the same launch, and an unknown or unavailable app is refused. | helper `:3599-3655`, `:3689-3733` |
| The `screen` hint on `open_app` is only recorded with the launch. Nothing places a window by it yet. | helper `:3689-3696` |
| The helper's window client can activate and minimize a window. It cannot bring one back or close one, reads no titles, and binds outputs at version 1, without names. | helper `:2847-2850`, `:2866-2876`, `:2942-2962` |
| Which apps have windows goes to views only (`apps_running`). The mod hears only about its own launches (`app_state`). | helper `:3354-3364`, `:3816-3821` |
| Covering is judged only for the world's outputs, and only while the world's window exists. | helper `:2705-2707` |
| An activated world means "he wants the world": the helper minimizes what covers it. Super's route activates the world's window, and only for a ready desktop that offered `shell_search`. | helper `:4134-4147`, `:4240-4252`, `:4274-4275` |
| The home the mod publishes is kept in memory only. Only the mod publishes one. With none, `get_home` answers with no revision and no rows. | helper `:3094`, `:3491-3496`, `:3514-3526` |
| The supervisor's states are SETUP, STARTING, IN_WORLD, AUTH_REQUIRED, RECOVERY and STOPPING. Its command list has no `search`, no world switch, no freeze. Its private environment list has no view token. | supervisor `:328-329`, `:4783-4785`, `:182-184` |
| At its start the supervisor begins a launch at once, unless it adopts a game, is latched, or the session is ending. A launch first checks Minecraft's pinned files and makes the Prism instance if it is missing. | supervisor `:1816-1845`, `:1943-1952`, `:617-661` |
| The first start ever is SETUP: no world yet and no home seen before. Prism opens without a world and shows its own sign-in, never under the cover, and a message window lists the steps. Whether a home was ever ready is kept as `hub_seen`. | supervisor `:1939-1940`, `:1982-1995`, `:1456-1472`, `:1111` |
| An unreadable pin file ends the supervisor before it starts anything, and each such try opens a terminal with the reason. After five tries within ten minutes the keeper stops and opens one more. | supervisor `:4568-4578`, `:238`, `:4612-4627` |
| A stop asks the game to save and then sends SIGTERM. The supervisor never sends SIGKILL. A plain stop without a confirmed save is called off; a shutdown closes anyway and latches `unsaved`. | supervisor `:3323-3355`, `:3380-3399`, `:79`, `:3370-3378`, `:3629-3633` |
| A launch that ends while an open stop record names it is `stopped`: never counted, never restarted by backoff, never latched `killed`. It latches `unsaved` if its save was not confirmed. | supervisor `:2388-2391`, `:3618-3659` |
| A stop or a logout counts as done only when the game's close is `exited` or `none`. | supervisor `:3425`, `:3600` |
| Any other end by SIGKILL latches `killed` and opens the recovery window. `retry` then waits for a full minute of clear memory pressure, sampled only while that latch holds. | supervisor `:2408-2420`, `:225-232`, `:2490-2492`, `:2589-2601` |
| A crash restarts the game after a backoff, with no memory test. That deadline and his own quit are kept across supervisor restarts. | supervisor `:1779-1812`, `:2437-2445` |
| Every JVM passes one gate at the supervisor, also one started from Prism's own window. | supervisor `:2182-2236` |
| The game runs in `aresos.slice/aresos-game-<launch>.scope` with `MemoryHigh` and `TimeoutStopSec` and nothing else. Apps run in `app.slice` scopes. The login session's scopes have `MemoryLow=1G` and `ManagedOOMPreference=avoid`. Nothing orders the game ahead of his apps. | supervisor `:1046-1066`; helper `:2279-2287`; `os/config/usr/lib/systemd/system/session-.scope.d/50-aresos-recovery.conf`; `os/config/usr/lib/systemd/system/user.slice.d/50-aresos-recovery.conf` |
| A restarted supervisor adopts a running game: STARTING for an unlatched hub launch, with `slow_start` after 120 s without readiness; SETUP for a setup launch; RECOVERY when latched. The new helper gets the nonce from the runtime file. | supervisor `:1855-1877`, `:2554-2558` |
| The shutdown guard waits 62 s for the supervisor, then up to 10 s for a new one, then writes its own record. | supervisor `:4688-4708`; `os/config/usr/lib/systemd/system/aresos-guardian.service:13-15` |
| The instance keeps Prism open: `CloseAfterLaunch=false`, `QuitAfterGameStop=false`. A later `--launch` is handed to a Prism that already runs. | supervisor `:572`, `:1053-1055` |
| The world's window is maximized, frameless and always below. Alt+Tab lists it. `rc.xml` binds no lone Super; its one Super chord is Super+Ctrl+Escape. Its `<mouse>` section keeps labwc's defaults and makes clicks on a bare desktop do nothing (package 329). Nothing sets a background colour. | `os/config/usr/share/aresos/labwc/rc.xml:19`, `:21`, `:34-45`, `:49-53`; `os/config/usr/share/aresos/labwc/autostart` |
| A left click on a hotbar slot with the free pointer ends in `open_app`. Any other click there, a right click too, enters the world. The search's Enter ends in `open_app`. The search is a game screen and needs a ready world. A 1.2 mod frees the mouse on any `background`. | `mod/src/client/java/dev/aresos/client/HomePointer.java:36-53`, `mod/src/main/java/dev/aresos/focus/PointerRules.java:20-22`, `WorldSearchScreen.java:125-127`, `ShellFocusClient.java:61-65` |
| The laptop home is on main: GTK 4 and Cairo, view `laptop-home` pinned to minor 2, a town model with hotbar slots, a finder. Its picture decoder is pure Python, for icons up to 512 × 512 within 5 s. Without the layer library it falls back to a full-screen window. Nothing starts it yet. | laptop home `:492-495`, `:36`, `:200`, `:270`, `:598-603` |
| The laptop home's surface is on the background layer, with the keyboard on demand. It draws with Cairo only and loads no GPU driver. Its scope has `MemoryHigh=640M`. | laptop home `:604-610`; `docs/design/LAPTOP-HOME.md:297-300`, `:313-319` |
| `aresos-settings` holds three lists of values. When it writes, it drops names it does not know. Its file holds only the values he set, so a changed default reaches every setting he never chose. | `os/config/usr/libexec/aresos-settings:4-6`, `:19-23`, `:60-68`, `:110-115` |
| A layer-shell piece in the look already exists: the indicator, with the look pack and `aresos-settings`. | `briefs/320-indicator.md` |

---

## 4. Where each part lives

| Part | Lives in | Content by | Surface and look by | Why |
|---|---|---|---|---|
| The bar's content: slots, marks, what a click does | The helper (the facts) and the native home's bar model | hub | | One model for every bar. |
| The bar's surface | The native home: `aresos-bar` and its strip `aresos-bar-edge`, per output | | desktop | It must show in a normal style, and with the world asleep or covered. |
| The in-game hotbar | The mod | hub | the game | It stays (the owner, T483). It gets the marks and the left-click rule. |
| Search | The native home: `aresos-search`, opened by Super | hub | desktop | It must work over a full-screen app and in a normal style. |
| Launching | The helper | hub | | It is there already and stays the only place that starts a program. |
| The open-app list and its marks | The helper works them out. Both bars draw them. | hub | | One answer to "what is open". |
| The app options menu | The native home: popups on the bar and on an icon. In the world a right click on a hotbar slot is "New window". | hub | desktop | One menu. The game gets none of its own. |
| The picture behind the windows | The native home: `aresos-picture`, per output | desktop; the town is the hub's | desktop | Needed in four cases: a normal style, a closed world, a sleeping world, a second screen. |
| The video background | The player: `aresos-video`, a program of its own, with its own surface above the picture | desktop | desktop; the supervisor starts, watches and stops it (aresos) | A video that fails must lose only the video. It costs nothing in the other styles (section 6). |
| Desktop icons | Kept by the helper. Drawn by the native home over the background: on the picture's surface in the Picture style, on a surface of their own above the video in the Video style. | hub: what a click and the menu do, and the keeper | desktop: the surface, dragging, the alignment rule, the look | One keeper. The native home keeps no state. |
| The still | The mod makes it; the native home shows it on the picture | hub | | Only the game can draw its own frame without windows on top. |
| Toasts | The native home: `aresos-toast` | hub for AresOS's lines; desktop for system notifications later | desktop | They must show over apps and in a normal style. |
| Status icons (Wi-Fi, battery, sound, clock) | The native home, as part of the bar | desktop | desktop | The bar is on every screen and reachable over every app. |
| The home style | A setting. The supervisor applies its world part, and runs the player in the Video style. The native home applies the picture and the icons. | hub (behaviour), aresos (supervisor) | desktop (the background) | The supervisor alone may stop and start the game. |
| The indicator, the overview | As COMPONENTS.md says | desktop | desktop | Unchanged. |

### The native home

- **One program, in a scope of its own** (`aresos-home.scope`), started by the supervisor at the session's start,
  from package 3a on. It runs in every home style and in every state of the world, and is never part of readiness.
  It is the same program, started the same way, in every style. It outlives a supervisor restart; the new
  supervisor finds it by its unit name and starts no second one.
- **Its restarts never stop for good.** After it ends: 2, 10 and 30 seconds, then every 60. LAPTOP-HOME.md's "then
  no more in this session" ends, because in a normal style this program is the home.
- **Why one program.** The laptop home measured 52 MiB with one picture and 61 MiB after a redraw
  (`docs/design/LAPTOP-HOME.md:327-328`). Five such programs would be about 250 MiB at rest. The owner called
  300 MB "crazy much" for a home screen. The player is a second program only in the Video style, by the lead's
  decision: there a fault in the video must not reach the bar.
- **Why the laptop home.** It already has the view connection with its token, reconnecting, a sandbox for decoding,
  a model with hotbar slots and a finder with seven kinds of hits.
- **What changes in it.**
  - More than one output; a bar surface apart from the picture; the finder as an overlay; static pictures.
  - In the normal styles it also draws the icons (section 6). It never plays a video: that is the player's work.
  - Its own hotbar, typing line, clock and battery leave, each in the package that ships its replacement: the
    typing line with the search (package 6), the rest with the bar (package 4). Until then the old view keeps them.
  - Its own copy of the last home leaves: the helper keeps the home on disk (section 5).
  - It watches the settings file, so a change of picture or style shows at once, whoever made it.
  - **No fallback window.** Today it falls back to a full-screen window (laptop home `:598-603`). The new program
    draws nothing and exits without the layer library, as the indicator does.
  - Its view is named `home`. The old `laptop-home` view on minor 2 keeps working until it is replaced. The
    helper's `LAPTOP_HOME_APP_ID` (helper `:165`) then matches no window and goes with the fallback.
- **Big pictures are never decoded in this program.** The icon decoder is too small and too slow for a screen-sized
  picture (laptop home `:36`, `:270`). A still or a picture of his goes through a converter child of the helper's
  kind: ImageMagick in bubblewrap, under an address-space ceiling and a coder policy for PNG, JPEG and WebP. It
  hands back raw pixels at the output's size. The native home only copies pixels. Without the sandbox tools the
  plain picture shows.
- **No video is decoded in this program either,** in any style. That is the player's work, in its own process
  (section 6).
- **Who owns which code.** The file is split into modules before anything is added (section 10). Surfaces, outputs,
  the reveal, the look kit, status icons, static pictures, the converter and the icons' layout are the desktop's.
  So is the player, a program of its own. The helper connection, the bar model, the finder, menu rows and the town
  are the hub's. The bar, the search, the menus and the icons name no colour and no layer; the town keeps its own
  painter (laptop home `:1478-1482`).
- **The keyboard.** Two surfaces can take it, and no other.
  - The search takes it while it is open, and only then.
  - The surface that holds the icons takes it in a normal style, and only after he clicks on it. That is
    `aresos-picture` in the Picture style and `aresos-icons` in the Video style. Its keyboard mode is "on demand",
    as the laptop home's surface has today (laptop home `:610`). It never gets the keyboard by default: not at the
    session's start and not when a window closes.
  - In the Minecraft style and under a still, the background never takes it. The bar, the strip, toasts and every
    menu never take it; the menus are pointer-only popups. The player's surface takes no keys and no clicks.
  - Section 12 says how a hung search is ended.

---

## 5. One source of truth

| Fact | Who makes it | Who keeps it for everyone | Who reads it |
|---|---|---|---|
| Installed programs, their pictures | the helper (desktop entries) | the helper | the mod, the native home |
| My apps, short names, groups, places, pins, logo cells | the mod (`publish_home`). For pins, while no world runs: the helper, on a view's request (package 11). | the helper, **now also on disk** | the native home (bar, town, search), the overview |
| Icons on the normal home: which apps, on which screen, where | him, by dragging in the native home. The first ones: the helper, once (T498). | the helper, on disk (package 3I) | the native home |
| Windows: whose, active, minimized, on which output, title | labwc | the helper | the mod, the native home, the overview, the supervisor |
| Outputs: names, the home output, where the world's window is, covered or not, what the bar does | labwc | the helper | the mod, the native home, the supervisor |
| The world's state: awake, asleep, starting, off; waiting for memory | the supervisor | the helper passes it on in `screens` | the native home |
| Settings: look, home style, picture, video, icon alignment | `aresos-settings` | its file | everyone |

**What this removes.** The laptop home's own file of the last home. A second rule for the home output. A second
covering rule for the bar. A second way to start a program. A keeper of his icons inside the program that draws them.

**What stays double, on purpose.** The mod's searches and the native search each rank hits in their own language.
One shared file of queries and expected hits, read by both sides' tests, keeps them in step.

### Changes to the helper that are not on the wire

- **Its life is the supervisor's.** The supervisor starts it once, with the instance and the view token and no
  nonce. It still dies with the supervisor (supervisor `:3804-3805`). The keeper restarts a failed supervisor after
  2 s (supervisor `:4628`), the new supervisor starts a new helper, and views reconnect with the same token.
- **Every helper gets what the running world needs, before it serves anyone.** The supervisor's first packet to a
  helper it started carries its whole state: the live launch's nonce and its keep-foreground flag, if a launch is
  alive or starting, and the world's state. That holds for the session's first helper, for one restarted after a
  failure, and for the one a new supervisor starts after it adopted a game. Without it the running mod could not say
  hello to the new helper (helper `:3391-3394`), and both the hotbar and the mod's search would stop opening apps.
- **The flag is worked out by today's rule at each send** (supervisor `:2020-2025`): an automatic restart with no
  cover waits below the app in front.
- **A new launch's nonce is in the helper before the game can use it.** For a start by the supervisor: before
  Prism is started. For a game started from Prism's own window, the supervisor makes the nonce at the JVM gate
  (supervisor `:2212-2215`). It hands it over there and answers the wrapper after the helper's `ack`, as a `save`
  reply comes later today (supervisor `:4402-4409`). With no helper running it answers at once, and the helper gets
  the nonce in its first packet.
- **Each packet is acknowledged.** The helper answers `ack`. The supervisor sends again each second until then. The
  read grows from 64 bytes. Until a nonce arrives, a desktop hello is refused.
  *To verify in package 1:* that the mod tries its hello again after a refusal.
- **Its restarts never stop for good.** After five failures in a minute it is tried every 30 seconds. Today's
  `helper` recovery window stays for a running world.
- **The home on disk.** The helper writes each complete `publish_home` to `home.json` in the supervisor's state
  folder (supervisor `:372-373`), whole or not at all, readable by him only. It loads it at start, so `get_home`
  answers with no game running.
- **Pins without a world** (package 11). Only the mod makes pins today, so a laptop that never ran the world has
  none (helper `:3491-3496`). Two hands write the home document, never at the same time: the mod while a world runs,
  and the helper on the native home's request while none runs.
  - **A home the helper makes itself.** With no document yet, the helper makes one the first time the home shows in
    a normal style: `home` is `picture` or `video`, and a view `home` asks for the home. Its rows are the starter
    apps. Each row has the app's ID, its name and its slot, and no logo cells.
  - **The starter apps** are the entries of the image's reviewed registry (helper `:137`) that can start, in the
    order the helper loads them: by file name (helper `:367`). The first nine fill the nine slots in that order.
  - **More than nine:** the rest are not pinned. The search finds them, and he can pin them.
  - **None:** the document has no rows. The bar shows nine empty pins. The search still lists every installed
    program, so a launcher is always there.
  - **Rows without a logo go only to a view that negotiated `pins`.** Today's reader needs 144 logo cells in every
    row (laptop home `:291-301`, `:945`). To any other view a home the helper made is no home: `get_home` answers
    with no revision and no rows, as today.
  - **The helper says who made the document,** so the `town` picture is never offered for one of its own
    (section 6).
  - This revision read one registry entry, `os/config/usr/share/aresos/apps/terminal.json`, and could not list the
    folder. Package 11's brief reads it. If file-name order is a poor order for him, the brief fixes another with
    `linux-aresos`.
- **The icons on disk** (package 3I). The helper keeps his icons' places in one file, `icons.json`, in his AresOS
  config folder beside `settings.json` (`os/config/usr/libexec/aresos-settings:35-39` names that folder). It writes
  the file whole or not at all, readable by him only. It also seeds the first icons, once (T498). Section 6 has the
  rules.
- **Output names.** The helper reads each output's name, so it and the views mean the same screen. For the icons it
  also keeps each screen's make, model and serial number where the output gives them (section 6).
  *To verify:* that labwc 0.9.6 offers `wl_output` version 4.
- **More window requests.** Bring back (`unset_minimized`) and close, beside activate and minimize. Titles are kept.
  The time each window was last active is kept, per app.
- **While the world sleeps** (package 9) the helper never activates the world's window and sends the mod nothing.
  On waking the mod gets one fresh snapshot: focus, covering, `screens`, `apps_state`, and the last `app_state` of
  each of its own launches that changed meanwhile. Never a backlog.

### `aresos-shell/1.3`

Everything in 1.2 stays. Minor 3 arrives with package 2, and each later capability joins it with its own package.
A side that did not offer a capability gets none of it. The laptop home pins minor 2 and keeps working (laptop home
`:492-495`). Example messages go to `mod/src/test/resources/shell-1.3/`.

| Capability | Package | Message | Direction | What it does |
|---|---|---|---|---|
| `apps_state` | 2 | event `apps_state` | to the desktop and to views | `{"apps": [{"id": "chrome", "windows": 2, "active": true, "hidden": false}]}`. Every catalogue app with a window. `active`: one of its windows has the keyboard. `hidden`: all of them are minimized. Sent once after hello and on each change, coalesced as `apps_running` is. `apps_running` stays for 1.2 views. |
| `activate_app` | 2 | request `activate_app` | desktop and views | `{"app_id": "chrome"}`. With a window: the helper brings back and activates the app's most recently active window; a layout that went down together comes back whole (COMPONENTS.md 4.3). No launch. Reply `{"state": "activated"}`. While a launch of that app is still starting, from any client: the reply is that launch's, and no second one starts. Otherwise: exactly `open_app` with this request ID. A client sends it only to a helper that offered it. To any other helper it sends `open_app`, as today. |
| `screens` | 3a | event `screens` | to the desktop and to views | `{"world": "awake", "screens": [{"name": "HDMI-A-1", "home": true, "world": true, "covered": false, "bar": "none", "reserve": false}, {"name": "eDP-1", "home": false, "world": false, "covered": false, "bar": "shown", "reserve": true}]}`. `world` is `awake`, `starting` or `off`, and from package 9 `asleep`. `off` is every state with no game: a normal style, a world closed for this session, also a session that waits for him in the supervisor's window. `"waits": "memory"` is there while a pending start or a wake waits. Per screen: `home` is the home output; `world` is true while the awake world's window is on it and not minimized; `covered` is today's rule; `bar` and `reserve` are section 8's rule. A reader takes a `world` value it does not know as "not awake". |
| `search_view` | 6 | event `search_requested` | to the view `home` | Super, on route 1 of section 8. Sent only to a view that negotiated it. The helper activates nothing and minimizes nothing. |
| `search_view` | 6 | `"screen": "world"` on `open_app` and `activate_app` | from a view | Allowed from a view in 1.3. It means the home output. Until 23c places windows it is only recorded. |
| (existing `shell_focus`) | 6 | reasons `view` and `view_closed` | to the desktop | The search took the keyboard while the world had it, or gave it back. |
| `notices` | 6 | event `notice` | to views | `{"text": "The world stays on: your home could not be saved."}`. One line for a toast. |
| `view_alive` | 6 | request `view_alive` | from a view | A view that holds the keyboard sends it once a second, from its drawing loop. After three silent seconds the helper tells the supervisor, which ends the native home's scope. |
| `settings` | 7 | request `set_setting` | desktop and views | The helper starts `aresos-settings set` off its loop and replies `accepted` at once. A change of style that closes the world can take a minute; the outcome shows in `screens`, and a refusal comes as a `notice`. It never carries a path: the helper refuses `picture-file` and `video-file` from every client. Those two are set only by the command, run by him or by Claude for him. |
| `world_power` | 7, 9 | request `wake_world` | views | `{"reason": "anyway"}` from package 7: his "Start anyway" for a pending start. From package 9 also `click`, `pointer` and `home`: a wake. The helper passes it to the supervisor, which decides. |
| `window_list` | 4 | `list_windows`, `windows_changed`, `activate_window`, `close_window`, `go_home` | views | As COMPONENTS.md 4.5 planned them for the overview. The app menu uses the first four. |
| `pins` | 11 | request `set_pin` | from the view `home` | `{"app_id": "chrome", "slot": 3}`, or `"slot": null` to unpin. Accepted only while no desktop is connected. With the mod connected it is refused as `invalid_state`: in the world he pins in the world. `home_changed` follows, as after a publish. |
| `pins` | 11 | `"made_by"` and rows without `cells` in `get_home`'s answer | to a view that negotiated `pins` | `"made_by"` is `mod` or `helper`. A row the helper made has no `cells`: it carries no block logo. A view that did not negotiate `pins` never gets such a row or that field. To it a home the helper made is no home, and `get_home` answers with no revision and no rows (helper `:3495-3496`). |
| `home_icons` | 3I | requests `get_icons`, `place_icons`, `remove_icon`; event `icons_changed` | views; the last two requests from the view `home` only | `get_icons` answers `{"revision": 12, "icons": [{"app_id": "chrome", "screen": "eDP-1", "x": 96, "y": 64}]}`, without icons whose app is gone. `screen` is the output's name as in `screens`. The helper maps it to and from the screen's kept identity (section 6), and lists an icon whose screen is not connected without `screen`. `place_icons` carries 1 to 200 such entries and adds or moves each. `remove_icon` names one app. The helper checks each app against the catalogue and each number against a fixed range, writes the file and sends `icons_changed`. It never judges a place against a screen's size. |
| `backgrounds` | 3V | request `picture_shown` | from the view `home` | `{"screens": ["eDP-1", "HDMI-A-1"]}`. The outputs whose picture surface is up, sent on each change. The helper passes it to the supervisor with each output's covered state. The supervisor tells the player, which makes its surface for a screen only after that (section 6). |
| `still` | 8 | event `still_changed`; request `still_shown` | to and from the view `home` | `{"id": 7}`. The view shows that still on the home output's picture and says so with the same number. |

- **Left over from earlier notes.** COMPONENTS.md 4.2 proposed "a field that says which apps have a minimized window"
  and "bring back this app's window". Those are `apps_state` and `activate_app`. `world_clicked` (4.3) is unchanged.
- **Views in 1.3** may also send `activate_app`, the window requests, `set_setting`, `wake_world`, `still_shown`,
  `view_alive`, `set_pin`, the icon requests and `picture_shown`.
- **From the search, in COMPONENTS.md 4.5's order** (`docs/design/COMPONENTS.md:1204-1208`): the search closes its
  surface, waits for one round trip to labwc, reports `view_focus` false, and only then sends `activate_app`.
- **Never sent to the game or a view:** a command, arguments, an environment, a path other than `icon`. As today.
- **The player is no view.** It never connects to the helper (section 6).

### Other interfaces

| Interface | Change |
|---|---|
| Lifecycle channel (mod and supervisor), 1.0 to 1.1 | Capability `still` (package 8): `{"op": "still", "id": n}`, answered `still_saved`. The mod writes one frame without its interface to a fixed file, `aresos/home/still.png` in his cache folder, whole or not at all. The supervisor never takes a path from the mod. Capability `sleep` (package 9): `sleep`, `wake` and `resume`, in outline in section 9. Gate 1 fixes their exact form. A mod without `sleep` never sleeps. |
| Supervisor to helper (status socket) | Packets beside today's `windows`: the live launch's nonce with its keep-foreground flag, and the world's state (package 1); a notice (package 6); a still's number (package 8). Each is acknowledged, and the first two are sent again to every new helper. Super stays SIGUSR1, as 23c plans it. |
| Helper to supervisor (status socket) | Lines beside today's: `ack`; the outputs with the home output; whether the view `home` is connected and what it negotiated; a view that stopped answering; his "Start anyway"; from package 8 `still_shown`; from package 9 a wake request with its reason; from package 3V each output's covered state and whether its picture is up. |
| Supervisor and the player (a pipe pair; package 3V) | To the player: the screens whose picture is up, which of them are covered, and whether a cover or the black screen is up. From the player: the beat (section 6). The exact form is 3V's brief. The player gets no view token, no nonce and no socket of the helper's. |
| Supervisor commands | `aresos-desktop world on`, `world off` and `world on --anyway` (package 7), `wake` (package 9), beside 23c's `search`. A normal style is `world off` to the supervisor, whichever of the two it is. From package 3V also `video`: the supervisor reads the settings and makes the player match. In the Video style it starts the player afresh and clears its count of ends. In any other style it stops the player. |
| Settings (`aresos-settings`) | `home` = `picture`, `video` or `minecraft`. Its default is `minecraft` until package 12 makes it `picture`; `video` joins with package 3V. `picture` = `plain`, `black`, `file` or `town` (default `plain`). `picture-file` and `video-file`: the program's first values that are not one of a list, each an absolute path to a file he can read, checked when set. They are set by the command only, never through `set_setting`. `video-battery-pause` = `never`, `below-20`, `below-50` or `always`: when a video pauses on battery (section 6). `icon-align` = `on` or `off` (default `on`). A change of `home` to or from `minecraft` ends in one supervisor request. In which order the file is written and the supervisor is asked, and what a crash between the two leaves, is gate 2's row 4. From package 3V a change between `picture` and `video`, setting `home` to `video` while it already is `video`, any write of `video-file` (also the same value), or a change of `video-battery-pause` ends in `aresos-desktop video`. |
| `publish_home` | The wire is unchanged. |

---

## 6. Home styles

**What it is.** The setting `home`. It says what his home is, and it holds until he picks another, across restarts
of the laptop.

| Style | The home output shows | The game and Prism | He opens apps from |
|---|---|---|---|
| Picture | a picture, his icons, the bar | closed | icons, the bar, Super's search |
| Video | a looping, silent video, his icons, the bar | closed | the same |
| Minecraft world | the world, with its own hotbar | running | gates, the hotbar, `/name`, Super's search |

**Two words for one thing.** To the supervisor, Picture and Video are both "world off", and the Minecraft world is
"world on". Its states, records, commands and gates keep those words: OFF, `world off`, `world on`. Which picture
shows is the native home's business, not the supervisor's. So everything revision 2 decided for the world-off switch
holds here unchanged, and the reviews' findings still apply to it.

**One exception: the video's player.** The supervisor starts it in the Video style, watches it and turns it off
("Video backgrounds" below; `linux-aresos` builds that part of package 3V). It does so as it runs every program of
the session. It never reads the video, and it starts or stops no world for it. A change between Picture and Video
is no world change: it ends in `aresos-desktop video` alone.

**The default, and the owner's laptop** (the owner, T493).

- Until package 12 the default is `minecraft`, as today. Package 7 only adds the choice.
- Package 12 makes the default `picture`. A fresh AresOS then starts on the picture home. Package 12 waits for
  package 3I, so that first home has its starter icons (the owner, T498).
- **A laptop that has a home keeps it.** The settings file holds only what he chose, so a new default would reach
  his laptop too (`os/config/usr/libexec/aresos-settings:4-6`). So the supervisor settles it before it reads the
  style. If the file has no `home` value, and this laptop has had a home, it writes `home = minecraft` once, through
  `aresos-settings`. "Has had a home" is the supervisor's own `hub_seen` (supervisor `:1111`), or a home folder in
  his worlds folder. From then on the file names his style like any choice of his.
- The rule runs at every supervisor start, so it also mends a file that lost the name after `previous`.
- **A style change never touches a world's files.** Whatever the setting says, his home is where it was.

**What the supervisor's boot does in each style**

| Style | Helper and native home | Minecraft's pins, the Prism instance | Prism and the game | Cover | The session is in |
|---|---|---|---|---|---|
| Picture | started first | not read, not made | not started | none | OFF (`off`) |
| Video | started first; then the player, once the native home has its picture up | not read, not made | not started | none | OFF (`off`) |
| Minecraft world | started first | checked, and the instance made if missing, as today | started, after today's checks and admission as today (section 12) | today's start-up cover; from package 8 the still | STARTING, then IN_WORLD |

- **In every style the helper and the native home are up before anything of Minecraft's is touched.** So a boot
  shows a home even when the world cannot start.
- **A normal style's boot reads nothing of Minecraft's.** Today an unreadable pin file ends the supervisor before
  it starts anything (supervisor `:4568-4578`). That check moves to the start of a world. In a normal style a broken
  pin file is a message when he picks the Minecraft world, never a dead desktop. This is gate 2's row 8.
- **A latch about the world waits.** Today a latch opens the recovery window at boot (supervisor `:1838-1840`). In a
  normal style it opens none. It shows when he picks the Minecraft world, and only `retry` clears it (gate 2, row 7).
  Gate 2's design step confirms this for each latch. A start can also make a latch by itself, before any launch: when
  it accounts for a game that ended while no supervisor ran, closes a stale stop record, or reads the guard's own
  record (supervisor `:1828-1830`, `:1769-1777`). The design step names those too.
- **The shutdown guard is asked only before a game starts** (supervisor `:1967`). A normal style's boot does not
  wait for it, and a shutdown in a normal style has nothing to save: no black screen and no wait.
- **A boot never begins a first start** (from package 12). While this laptop has no home, a boot starts no world,
  whatever the setting says. It shows the picture home and sets the style back to Picture. Only his pick opens
  Prism's sign-in.

**Where he picks it.**

- In the world: a row in the AresOS menu (Esc).
- Outside: the home menu. It opens from the bar's Home slot and from a right click on the empty background (both
  from package 4). It lists the three styles with his one marked. Super's search finds the styles by name.
- Until package 4 ships, the search shows "Home style: Minecraft world" as its first row in a normal style, as
  revision 2 had "Turn the world on".
- By command: `aresos-settings set home picture`, which Claude can run for him.
- All end in the same supervisor request. "Video" is offered only once package 3V has shipped and the lead has told
  the owner its measured cost.

**A normal style needs a launcher outside.** The supervisor refuses to turn the world off unless a view `home` is
connected that negotiated the search and answered its alive beat within the last few seconds. A silent or hung view
counts as absent. A notice says why. So he never trades the hotbar for nothing. Package 7 needs package 6 and 23c's
Super key for the same reason (section 10). The native home is the same program in every style, so the check meets
the program that will hold the home, also on a change to Video.

**Leaving the Minecraft world: the game and Prism are closed.** Not frozen, not swapped.

- His goal is memory while building. A frozen game keeps its memory until something pushes it to swap. Only a closed
  game gives all of it back for certain.
- Turning off is the supervisor's planned stop (package 25): the stop record, a confirmed save, SIGTERM, the wait for
  Java's real exit and the lock.
- **If the save is not confirmed, the world stays on.** The stop is called off as today (supervisor `:3370-3378`).
  The style stays Minecraft world, and a notice says why.
- **A normal style shows its background at once.** No still is made for it. Stills arrive with package 8.
- **A sleeping world is closed without a thaw** (package 9; gate 1).
- After Java has exited and the lock is free, the supervisor stops every `aresos-desktop-*.scope` of the session,
  not only this launch's. After a retry or a crash restart the live Prism sits in an earlier launch's scope
  (supervisor `:1053-1055`).
  *To verify in package 7:* that Prism stays open after the game exits, and that SIGTERM does not cost it its
  sign-in. If it does, Prism is left running in OFF, its 418 MiB stay, and the memory study takes it up.
- **His own quit and a plain `stop` end in OFF too,** for this session only. Today they open the `quit` window
  (supervisor `:2421-2428`, `:3590-3591`). The style is not changed, so the next login starts the world. While no
  view `home` is connected, today's window shows instead.

**Picking the Minecraft world.** The supervisor admits the start and then starts the game as it does today.

- Admission is the supervisor's, at two doors: before Prism is spawned, and again at the gate every JVM passes
  (section 12 has the test).
- On a full laptop the start is not refused and not forced. It becomes a pending start. `screens` says `waits`, and
  a toast says: "Memory is nearly full. The world starts when there is room."
- "Start anyway" is his own call: the search's first row while a start is pending, the home menu, and
  `aresos-desktop world on --anyway`.
- With no app window open, today's start-up cover hides the loading screens.
- With an app window open there is no cover: it must never hide his apps. Until package 8 the loading screens show
  behind his windows. From package 8 the world's window stays minimized until the world is ready.
- A start takes as long as a start at boot. Board T362 measures that.
- From the Video style, the player is stopped as soon as the style is the Minecraft world.
- **The first time, Prism asks him to sign in.** On a laptop with no home yet, the start is today's SETUP (supervisor
  `:1939-1940`). The instance is made, Prism opens without a world and shows its own sign-in, Minecraft downloads,
  and the mod makes his home. Nothing covers it. Today's message window lists the steps (supervisor `:1456-1472`).
  The picture, the bar and the search stay usable the whole time. His icons are hidden from the moment the style is
  the Minecraft world, and they are back if he backs out.
- **He can back out of it.** A first start that ends without a home puts the style back to Picture and tells him in
  one line. That holds when he closes the sign-in and when the setup fails; a failure also opens today's message
  window with the reason. The supervisor learns that he closed the sign-in from Prism's exit, and acts ten seconds
  after it (supervisor `:196`, `:2478-2480`). Picking the Minecraft world again starts over.

### The picture

The setting `picture`. The native home shows it on `aresos-picture`, on every output where the awake world is not
showing. In the Picture style it is the home's background. In the Video style it lies under the video, and shows
whenever the video does not.

| Kind | What |
|---|---|
| `plain` | A plain picture that `linux-desktop` draws in the look: A until B's files exist. The default (the owner, T482), and so the background of a fresh AresOS. |
| `black` | One flat colour, `#0d0d10`, look A's outline colour and the colour 23c plans for the laptop screen (`STATE.md:205`). Nothing sets a background colour today. A surface is still there, so a click never reaches labwc. |
| `file` | A picture of his, through the converter (section 4). It scales smoothly to cover the output, cropped centred. |
| `town` | His town from the side, by day, as LAPTOP-HOME.md designs it. Kept as a kind, not the default. It costs nothing extra: its model and painter are on main, and package 3a only places that drawing on the picture surface. It takes no clicks and has no bar, clock or battery of its own. It needs a home the mod published, so it is not offered on a laptop that never ran the world. A home document the helper made itself does not count: it has no town (package 11). If placing it shows a cost beyond that, the kind is left out. |

A left click on an empty picture does nothing. From package 9 a click on a still wakes the world (section 9).

### Video backgrounds

The Video style is the Picture style with a moving background. Everything else is the same: his icons, the bar, the
search, and a closed world.

**A program of its own** (the lead's decision on review 3, finding 9). The video is played by the player, working
name `aresos-video`. It is not a part of the native home.

- **Its own process.** `aresos-home` never opens, decodes or draws a video, in any style. The bar, the search, the
  icons and the picture share no loop, no renderer and no driver with the video.
- **Its own surface.** `aresos-video`, on the background layer, above the picture's surface. It takes no clicks and
  no keys.
- **Its own scope.** `aresos-video.scope`, with a hard memory limit: `MemoryMax`, not only `MemoryHigh`. At the
  limit the kernel ends the player, and only the player.
- **So a video that stalls, leaks or crashes loses only the video.** The picture lies under it and shows the moment
  the video's surface is gone. The bar, the search and the icons are untouched.
- **Only in the Video style.** The supervisor starts the player then and at no other time. In the Minecraft style a
  second screen shows the picture.
- **The image ships no video.** The file is his own.

**What it does**

- **Looped.** The video runs from its end back to its start, with no black frame between.
- **Silent.** Its sound track is never opened and no sound stream is made. The volume keys, the indicator and his
  headphones are not touched.
- **Fitted like a picture of his:** scaled smoothly to cover the output, cropped centred.
- **The picture is under it.** The chosen picture shows until the first frame is there, and whenever the video
  cannot play: no file is set, the file is gone, the decoder refuses it, the player failed, or the video was turned
  off. A missing video never leaves a bare screen.
- **Paused when nobody sees it.** Paused means decoding stops and the last frame stays. It goes on where it stopped.
  - On an output that is covered (section 7's rule), or under a start-up cover or the black screen.
  - Everywhere while the screens are off or the lid is closed.
- **Paused on battery below a level.** The setting `video-battery-pause` says when: `never` (it plays on battery at
  any level), `below-50`, `below-20`, or `always` (it never plays on battery). Which one is the default is open.
  This note starts at `below-50`. Package 3V measures what a playing video draws, and the lead asks the owner with
  that number. A machine with no battery never pauses for it.
- **The file** is the setting `video-file`, checked when set as `picture-file` is. A local file only: never an
  address, a stream or a list. Package 3V names the formats the image can decode.

**The stack on a screen in the Video style,** from the bottom:

| Surface | Whose | Layer | Holds |
|---|---|---|---|
| `aresos-picture` | the native home | background | the chosen picture |
| `aresos-video` | the player | background, made after the picture's surface | the video |
| `aresos-icons` | the native home | bottom | his icons, and nothing else |

Above these are his windows, and the bar by section 8's rule.

- **The icons get a surface of their own here.** The video lies above the picture, so icons drawn on the picture
  would be hidden. The bottom layer is above the background layer by the protocol, so the icons are above the video
  for certain ("Desktop icons" below).
- **The video's surface is always the newer one.** labwc stacks two surfaces of one layer in the order they were
  made (to verify, section 12). So the player makes its surface for a screen only after the native home has said
  its picture is up there (`picture_shown`, section 5). It makes it again whenever the native home has made the
  picture again: after a restart of the native home, and for a screen that was plugged in.
- **The safe side.** If the order ever goes wrong, the video is hidden under the picture. Nothing else is.

**How the supervisor runs it** (`linux-aresos`'s part of package 3V; the exception named above).

- **Start.** In the Video style, once the view `home` is connected and has said its picture is up. In its own scope,
  with the laptop home's pins to Mesa and Intel (`docs/design/LAPTOP-HOME.md:313-318`).
- **No secrets.** The player gets no view token, no nonce and no socket of the helper's. It can ask the helper for
  nothing. That matters because it decodes a file outside the picture converter's sandbox.
- **What it is told.** The supervisor passes on what the helper reports: which screens have their picture up and
  which of them are covered. It adds when a cover or the black screen is up. The player reads the video's settings
  and the battery itself.
- **The beat.** Once a second the player tells the supervisor that its loop runs, whether it plays or is paused, and
  how many frames it has shown. The beat goes on a pipe from the supervisor. It never passes through the native
  home or the helper.
- **A stall is a missed beat.** Three seconds with no beat, or with no new frame while it plays: the supervisor ends
  the player's scope and turns the video off.
- **An end.** The player ends by itself, or the kernel ends it at its limit. After the first end the supervisor
  starts it once more, 2 seconds later. After the second end the video is off. There is no time window: a file that
  ends the player at every loop, minutes apart, is counted the same.
- **Off.** The supervisor starts the player no more. The setting stays Video. The picture shows, with his icons, and
  a toast says: "The video is off. Pick Video again to try it." It stays off for the session, also across a new
  supervisor.
- **On again.** He picks Video again (also while the style already is Video), writes a video file (also the same one), changes `video-battery-pause`, or logs in again. Each of these runs `aresos-desktop video`, which starts the player afresh, and the count starts at zero then. This list and the settings row's trigger list in section 5 are the same list.
- **What is not an end:** the player stopped for a change of style or of its settings; started afresh after the
  native home came back; or replaced by a new supervisor, which ends a player it finds and starts its own.
- **What the supervisor does not do.** It never reads the file, and it starts or stops no world for a video. Gate
  2's rules for OFF are not touched.
- Three seconds, 2 seconds and "the second end" are starting values. The beat's exact form is package 3V's brief.

**How it is drawn** (`linux-desktop`, INPUTS-2). The native home draws with Cairo only and loads no GPU driver
(`docs/design/LAPTOP-HOME.md:297-300`). That stays so in every style. The choice of renderer is the player's alone.
There are two ways, and package 3V's first step measures both on the laptop's Intel chip.

| Way | What it is | What it costs |
|---|---|---|
| GL | The player draws with GL, and the chip decodes the video (VA-API on the Intel chip). | A GPU driver in the player's process. |
| Capped | The processor decodes the video in the player, and the frames go to the compositor as shared-memory pictures. | Processor time for every frame. So resolution and frame rate are capped, and the video stops on battery at any level. |

These rules hold whichever way wins:

1. **The native home pays nothing, in any style.** Cairo only, no GPU driver, no decoder loaded. LAPTOP-HOME.md's
   test that no driver is mapped holds for the native home in the Video style too. In the Picture and Minecraft
   styles no player runs.
2. **Three surfaces in a sure order** (the stack above). A fault in the video reaches nothing above it and nothing
   below it.
3. **GL only on the Intel chip, never on NVIDIA.** A program that draws on one chip while the compositor draws on
   the other cost two and a half cores in the study (`docs/design/LAPTOP-HOME.md:350-357`). So the GL way is used
   only when the compositor draws on the Intel chip. If labwc draws on NVIDIA, or the player cannot tell, the GL way
   is off: the capped way plays, or the picture shows if the capped way did not pass 3V's measurement. A background
   must never wake the NVIDIA card.
4. **A ceiling either way.** Never more pixels than the output has, and a ceiling on frames a second. Starting
   values: 30 frames a second with GL; 1280 × 720 at 24 without. Package 3V sets them from its measurement.
5. **A hard limit.** The player's scope has `MemoryMax`, and swap is closed to it (`MemorySwapMax=0`), so a leak
   ends the player instead of filling swap. Package 3V sets the figure from its measurement. If its runs show a
   busy player slowing the bar, the scope also gets a low processor weight. The native home's own ceiling is as in
   every style: the laptop home's is `MemoryHigh=640M` today (`docs/design/LAPTOP-HOME.md:319`).
6. **A change of style never restarts the native home.** The bar and the search are there through every change.

**Memory.** One video costs more than the laptop home's 60 MiB (`linux-desktop`). How much is not known. Package 3V
reports the measured figures on the Intel chip: the player's own scope, and what the native home gains in the Video
style, which is the icons' surface. Video is not offered in the home menu before the lead has told the owner those
figures.

### Desktop icons

**What an icon is.** One app from the helper's catalogue, shown as its picture with its name under it. One icon for
each app, up to 200. Icons are for apps only: no files, folders or web pages.

**Where they show.** In the Picture and Video styles, on every screen. Not in the Minecraft style: there his apps are
the world's gates, and a second screen shows the picture and the bar. His places are kept for when he comes back.

**Over the background, on a surface of the native home's** (`linux-desktop`, INPUTS-2; the Video case is new in
revision 4).

- In the Picture style icons are drawn on `aresos-picture`, the surface that holds the picture.
- In the Video style the video's surface lies above the picture. So there the native home draws the icons on a
  second surface of its own, `aresos-icons`, on the bottom layer: above the video and below every window. It is
  see-through but for the icons.
- Either way the surface's input region is the whole output, so every click and drag on the home is the home's.
  labwc's own clicks on a bare desktop are already off (`rc.xml:40-44`, package 329).
- One drawing routine and one layout serve both.

**What a click does, as on the bar**

- **Left click:** `activate_app`. It opens the app or brings its last window back, on that screen. A press that
  moves is a drag, not a click.
- **Right click on an icon:** the app's menu, the bar's own (section 8), with one more row: "Remove from home".
- **Right click on the empty background:** the home menu: the styles, the picture, "Straighten icons", and alignment
  on or off.
- **How an icon gets there:** "Add to home", a row in the app's menu on a bar slot and on a search hit. The first
  icons are seeded (below).
- An icon carries no open or active mark. The bar shows what is open.
- **It draws as a bar slot draws:** the block logo where his home document has one, otherwise the app's catalogue
  picture.

**The keyboard comes only by a click.** A click on the background or on an icon gives the home the keyboard, and
nothing else does (section 4). With it, the arrow keys move a frame from icon to icon, Enter opens, and Escape drops
the frame. No key removes an icon, and no key opens a menu: the menus are pointer-only. A click that opens an app
hands the keyboard to that app's window, as any launch does.

**The first icons** (the owner, T498: "Starter icons column (recommended)").

- A first normal home shows the starter apps as icons in one column at the top left of the home output, in the order
  of the bar's starter pins (section 5). He removes any of them with a right click.
- **Seeded once, by the helper.** When the helper makes its own home document (package 11) and no `icons.json`
  exists, it writes the column in the same step. That is the only moment.
- **Never on a home already in use.** A laptop with a home document gets none, whether the mod published it or the
  helper made it before package 3I. Neither does a laptop with an `icons.json`, also an empty one or one moved
  aside. So the owner's laptop is not touched, and icons he removed never come back.
- If the column is longer than the icon area, it goes on in a second column to the right.
- With no starter apps there is no column.

**Free placement, and straightening** (the owner, T494).

- He drops an icon anywhere in the icon area. With `icon-align` off it stays exactly there.
- With `icon-align` on, the drop is straightened against the icons already on that screen. On a drop only the icon
  he dropped moves; no icon at rest jumps.
  1. *Shared rows and columns.* If its centre is within half an icon cell of the row through another icon's centre,
     it takes that row. Columns are tested the same way, on their own. Near a crossing it takes both: that is how a
     grid forms.
  2. *Even spacing.* If two or more icons on that line already stand at one step, it takes the nearest place on that
     step, when that is within half a cell. The first two icons of a line set its step.
  3. *Free elsewhere.* Away from every line it stays where he dropped it.
- **Never on another icon, never out of reach.** With the setting on or off, a drop on another icon or outside the
  area goes to the nearest free place.
- **The icon area** is the output without the bar's height at the bottom. It is the same whether the bar shows or
  waits at the edge, so no icon ever sits under the bar.
- **"Straighten icons"** does it for a whole screen at once. Icons that nearly share a row or a column are put on
  one line, and nearly even gaps are made even. It is for icons he placed with the setting off, and it runs once when
  he turns the setting on. It works on the kept places, not on where a smaller screen draws them. The places from
  before are kept until his next drag, and the menu offers "Undo".
- **The setting starts on.** He asked for clean lines to be easy. Away from every line a drop is still free.
- "Half a cell" is a starting value. The icon cell's size comes from the look pack. `linux-desktop` tunes both on the
  laptop.

**The rule is one pure function** in the home's layout model: places and one drop in, places out. Its cases are in
one file that the tests read. They must show:

- With the setting off, places out equal places in.
- With it on, only the dropped icon moves, and never more than half a cell on each axis, except to clear another
  icon or the edge.
- No two icons overlap, and none is outside the area.
- A straightened screen is unchanged by straightening it again.
- "Straighten icons" keeps the order along every row and column, and moves no icon by more than one cell.

**Where the places are kept.** The helper keeps them in `icons.json` (section 5). The native home keeps none, so
ending it loses nothing.

- One entry for each icon: the app's ID, the screen's identity, and its place in logical pixels from the top left of
  that screen's icon area.
- The native home sends a place when he drops, not while he drags.
- It lives with his settings and not with the supervisor's state, because it is his arrangement. A backup of his
  settings should take it along.
- A file that cannot be read is moved aside under a dated name, never deleted. The home then starts without icons,
  and the bar and the search are untouched.

**An app that is removed.**

- Its icon is not shown and takes no part in straightening.
- Its entry is kept for 30 days (a starting value). An app that comes back after an update or a reinstall gets its
  place back. After that the entry is dropped.
- The helper calls an app gone only from a complete catalogue, never while its scan still runs (helper `:3577-3578`).
- An app that is there but cannot start keeps its icon. A click shows the helper's words as a toast, as on the bar.

**Several screens.**

- An icon belongs to the screen he dropped it on. A drag across the shared edge moves it to the other screen.
- **A screen is known by its make, model and serial number** where the output gives them, and by its connector name
  otherwise. So a monitor keeps its icons on another socket or behind a dock.
  *To verify in package 3I:* where labwc 0.9.6 gives a client those three.
- **An unplugged screen takes its icons with it.** They are kept and come back with the screen. They do not move to
  the other screen by themselves, because that would wreck both arrangements. "Bring all icons here" in the home
  menu moves them if he wants them. Every app stays reachable from the bar and the search meanwhile.
- **A screen that comes back smaller, or at another scale, still shows every icon.** One whose place is outside the
  area is drawn at the nearest free place inside. Its kept place is not changed, so it goes back when the screen is
  big again. "Straighten icons" there works on the kept places too, so a place the small screen only displaced is
  never saved as his.

**Memory.** A catalogue picture is decoded in the sandboxed child (section 4) and kept at its drawn size only. Kept
whole, a 512 × 512 picture is 1 MiB, and two hundred would be 200 MiB. In the Minecraft style the native home shows
no icons and drops their pictures. Package 3I measures the home with 50 icons. It also times the first draw of 200:
each picture is one sandboxed child (laptop home `:214-278`).

### The supervisor's states

| State | Game and Prism | The home output shows | New with |
|---|---|---|---|
| SETUP, AUTH_REQUIRED, RECOVERY | none, or waiting for him | the message window over the home he has | |
| STARTING | starting | the cover; from package 8 the still | |
| IN_WORLD | running | the world | |
| OFF (`off`): a normal style | none | the normal home: picture or video, his icons | package 7 |
| OFF (`quit`) | none, until he starts it or logs in again | the chosen picture | package 7 |
| ASLEEP | frozen, saved | the still | package 9 |
| WAKING | thawed, still paused | the still | package 9 |
| OFF (`asleep`) | none: a sleeping world was closed | the still | package 9 |
| STOPPING | being stopped | black, or his apps | |

**How OFF is entered and left** (package 7). The sleeping states' steps are in outline in section 9.

| From | Event | To |
|---|---|---|
| any state with a running game | he picks a normal style, and the save is confirmed | STOPPING, then OFF (`off`) |
| the same | the save is not confirmed | back where it was; the style stays Minecraft world |
| any state with a running game | his own quit, or a plain `stop` | OFF (`quit`), for this session |
| a boot in a normal style | | OFF (`off`): helper and native home, no Prism |
| OFF (`off`), OFF (`quit`) | his request (the home menu, a search row, `world on`), admitted | STARTING; from package 12, on a laptop with no home yet, SETUP |
| the same | his request, not admitted | OFF, with a pending start |
| OFF with a pending start | a later sample admits it | STARTING |
| OFF with a pending start | world off, `stop`, `logout`, a shutdown, the session's end | OFF, and the pending start is gone |
| SETUP, on a laptop with no home yet (from package 12) | it ends without a home | OFF (`off`), and the style is Picture again |

**OFF starts nothing by itself.**

- Only his own request starts a world in OFF. No timer is armed: no backoff restart, no wake. A wake request that
  reaches the supervisor in OFF (`off`) or OFF (`quit`) is logged and dropped.
- The gate every JVM passes (supervisor `:2182-2236`) refuses in OFF, also for Prism's own launch button.
- `restart` and `retry` in OFF (`off`) start nothing and answer with one line that names the home style.
- If the native home keeps failing in OFF, the supervisor opens its message window. It does not start the world
  (section 12).
- The first start ever (SETUP, the sign-in) begins only when he picks the Minecraft world. Until package 12 a fresh
  laptop's default is still the Minecraft world, and its first boot is the first start, as today.
- The video's player is no world. Starting or stopping it is no start in the sense of these rules.
- **What makes these rules hold across a crash, a new supervisor and an old restart deadline is gate 2.** Package 7
  does not start before it passes.

### Memory in each style

| Style | The game | Prism | The native home | The player | Source |
|---|---|---|---|---|---|
| Minecraft world, today | about 1,019 MiB (its scope's anonymous memory; soft limit 2,560 MiB) | about 418 MiB while the game runs | not running | not running | The laptop on R28, 2026-11-21 (`docs/HUB-HANDOFF.md:54`) |
| Minecraft world, this design | the same | the same | about 60 MiB with no picture surface | not running | 53f's measurement of the laptop home; an estimate for the new program |
| Picture | 0 | 0 | about 60 to 80 MiB, and his icons' pictures at their drawn size | not running | estimate from the same measurement |
| Video | 0 | 0 | as Picture, and one see-through surface for the icons on each screen | its own scope, under a hard limit; not measured | INPUTS-2; package 3V measures both |

- A normal style frees about 1.4 GiB of the laptop's 16.
- These are single readings of a settled world, not of a start. What a start needs at its peak is not measured;
  gate 3 measures it.
- A picture costs about 8 MiB for each 1920 × 1080 output. GTK may keep two (`docs/design/LAPTOP-HOME.md:331-335`),
  and a larger monitor costs more. The icons' surface in the Video style costs the same again.
- The helper and the supervisor are two small Python programs that run in every style. They were not measured.
  Package 7 measures all four on the laptop.
- The owner's own reading for the visible game is 1.2 to 1.3 GB.

---

## 7. Two screens

**Where the world goes.** To the home output. Package 23c's rule stands: any enabled screen that is not the laptop's
panel, the larger of two, the first connected on a tie; a closed lid counts as monitor only. 23c plans the move
itself: at boot the world opens there, plugged in later it moves there, unplugged it returns. Its mechanism is
still "the lead's first choice, a design step confirms" (`STATE.md:205`). This note relies on the rule, not on the
mechanism.

**One place for the rule.** The helper works out the home output, because it already binds every output and needs
the answer for covering, focus and placement. It tells the supervisor, which moves the world, and the views. In a
normal style there is no window to ask, so the rule cannot hang on the world's window as it does today.

**What each output shows.** The bar's state on each is section 8's rule.

| The world is | Home output | Other output |
|---|---|---|
| awake | the world with its own hotbar | the picture, and the bar |
| asleep or starting | the still, and the bar | the picture, and the bar |
| off, in the Minecraft style (closed for this session) | the picture, and the bar | the picture, and the bar |
| off, in a normal style | the picture or the video, that screen's icons, and the bar | the same, with its own icons |

- **Who builds which part.** In a normal style both screens are the home from package 3b1 on. That needs nothing of
  23c, because no world window is involved. The icons reach every screen with package 3I and the video with 3V.
  Beside the world, the second screen is package 3b2's, with 23c.
- **No screen is ever bare.** An output gets its picture surface the moment it appears. The surface goes away only
  once `screens` says the awake world's window is on that output, and it is back before the world leaves. So during
  a move the monitor shows the picture until the world arrives. This also ends "a monitor plugged in later stays
  black".
- With one screen and the world on, no picture surface exists and no picture memory is spent.
- **Icons go by their own screen** (section 6). Each screen shows the icons he dropped there.
- **One video for every screen.** The same video plays on every screen that shows the home, and it is decoded once.
  The player holds one surface for each screen. Each screen pauses by its own covering. Decoding stops when no
  screen shows it.
- **A screen plugged in while the world sleeps** (package 9). The still moves to the new home output at once,
  scaled as a picture of his is. The frozen window is left alone. At the next wake the supervisor moves the window
  first, and the helper shows it after that.

**How the cursor crosses.** The pointer is free unless he is in a look gesture (brief 328). labwc moves it between
the screens along their shared edge. Two rules for the look-around prototypes follow from this note:

- An edge shared with another screen belongs to crossing, never to turning. The mod learns the screens from `screens`.
- Where a strip exists, the bottom edge belongs to the bar.

Until 328 lands, the world still holds the pointer after a click on it, and he crosses with Esc first. That is
today's fault, not a new one.

**Covering, per output.** Every output has its own covered state: a maximized or full-screen window on it that is
not minimized. That is today's rule, applied per output, until the covering package gives the helper window
rectangles. The start-up cover and the black screen never cover. Three things read it. The world pauses only while
the home output is covered (`shell_covered`, unchanged for the mod). An output's bar waits at the edge while that
output is covered (section 8). And a video pauses on an output while it is covered (section 6).

**Where apps open, and where focus goes**

- An app opens on the screen the pointer is on (23c). A click in the laptop screen's bar, or on an icon there, opens
  the app there.
- The search opens on the home output, and its app opens there, as the owner chose on board #334. With two screens
  that needs 23c's placement (Known limits).
- `activate_app` focuses a window where it is. It never moves a window to another screen.
- When the last window of the app in front closes, the world gets the focus only if that window was on the home
  output and the world is awake. On the other output the focus stays there. A sleeping world gets a wake request
  instead.
- A click on the world or on the picture never hides a part-screen app. The world stays below every window, and the
  picture is below the world. A click on the home's background ends on a surface of the native home's: it never
  reaches labwc, and never the video. In a normal style it gives the home the keyboard (section 6), and it still
  hides no window.

---

## 8. The bar, and the bar over full-screen apps

### What the bar holds

| Slot | Content |
|---|---|
| Home | First slot. World awake: a click goes home, and what covers the world goes down by today's rule. Asleep: it wakes the world. In a normal style: it opens the home menu, which lists the three styles with his one marked, and the picture. In the Minecraft style with the world closed for this session: the menu's first row is "Start the Minecraft world". While a start is pending the menu has "Start anyway". |
| His nine pins | The Live hotbar's nine slots in its order, as `publish_home` gives them. An empty pin is an empty slot. On a laptop that never ran the world they are the helper's own pins (package 11): the starter apps, nine at most. |
| Other open apps | After a gap: every open app that is not pinned, in the order they opened. A slot leaves when its last window closes. |
| Status icons | The desktop's component. They sit in the bar. |

- **Marks**, from `apps_state`: open, active, and "all its windows are minimized". How a mark looks is the desktop's.
  The world's hotbar draws the same three.
- **Hover** shows the app's name.
- **Left click:** `activate_app`. It opens the app or brings its last window back.
- **Right click:** the app's menu: its windows by title, New window (`open_app`), Close all windows. Close goes
  through the window's own close, so an app still asks about unsaved work. With more than one window it asks once
  first ("Close 3 windows?"). From package 11 it has Pin and Unpin while no world runs, and from package 3I "Add to
  home".
- **In the world** a right click on a hotbar slot with the free pointer opens a new window (`open_app`). That
  gesture is new in package 2: today any click there but the left one enters the world
  (`mod/src/main/java/dev/aresos/focus/PointerRules.java:20-22`). Using an app item he holds, with the pointer in
  the world, is a different path and is left as it is.
- **A failed launch** shows the helper's words as a toast above the bar for five seconds.
- **The picture in a slot** is the app's logo as the mod published it (laptop home `:1751-1758` draws slots from the
  published cells). An open app outside My apps, and a pin the helper made itself, shows its catalogue picture.

### Where it shows: one rule

One bar on every output, the same content on each (the owner, T484). The helper works the rule out and says it in
`screens`, as `bar` and `reserve`. The native home only follows it. For each output, the first row that holds:

| # | On the output | `bar` | The bar | `reserve` |
|---|---|---|---|---|
| 1 | A start-up cover or the black screen is up. | `none` | Hidden, and no strip. | no |
| 2 | A window fills it (covered). | `edge` | Hidden. A strip at the bottom edge waits for the pointer. | no |
| 3 | The awake world's window shows on it. | `none` | Hidden, and no strip. The world's own hotbar is the bar there (the owner, T483). | no |
| 4 | Anything else: the picture, a video, a still or a starting world, with or without part-screen windows. | `shown` | Visible, on the top layer. | yes, except on the home output while `world` is not `off` |

- **`reserve` is the exclusive zone.** Yes: the bar's surface sets a zone of the bar's height, as a taskbar does.
  labwc then places, snaps and maximizes windows above it, so the bar covers none of their rows. No: the zone is 0.
- **`shown` means a screen nothing fills,** also one with part-screen windows (the owner, T485: "Visible there").
- **`edge` means a window fills the screen.** The zone is 0, so that window gets the whole output and hides the
  bar, which the owner likes.
- **On the home output the zone stays 0 while `world` is not `off`:** awake, asleep or starting
  (`linux-desktop`, revision 2). A zone would re-fit the world's own maximized window. Every switch between `none`
  and `shown` would then resize the game, and a still would no longer fit. The zone goes to 0 when a start begins,
  before the window maps, and comes back only when `world` is `off`.
- **So the zone applies only while the bar is `shown`,** on every output except the home output while `world` is not
  `off`. That one phrase is the rule wherever this note mentions the zone. In a normal style `world` is `off`, so a
  shown bar reserves its height on every screen.
- **No resize loop.** `edge` follows covering, and covering follows the maximized and full-screen states, not
  sizes. A maximized window covers its output whatever the zone is.
- **A full layout** counts as filling once the covering package ships. That is one condition in the helper.
- **A video changes nothing here.** The bar is the native home's, and the video is the player's. Whether the video
  plays, pauses, fails or is off, the screen is row 4.

### Reveal and hide

- **Reveal.** The pointer rests on the bottom edge of an output whose bar is at `edge`. After 300 ms the bar slides
  up in 150 ms, on the overlay layer: above the app and above a true full-screen window.
- **Not revealed** while a mouse button is held, during a Deskflow capture, or while the pointer is locked. A
  full-screen game keeps its screen. Alt+Tab and Super still work there.
- **Hide.** Half a second after the pointer leaves the bar. At once after a click that opened or brought back an app.
  It stays while one of its menus is open. Then it is back on the top layer.
- **Which output.** The one whose edge he touched.
- **The world stays as it is.** A reveal over a maximized app does not wake or unpause the world.
- **No keyboard.** The bar never takes it. The keyboard's way to an app is Super.

### In the look, without the game

- The bar is a new COMPONENTS.md piece, with the status icons. `linux-desktop` writes its A, B and C, its marks and
  its look-B map rows there before package 4's brief. In A it reuses the frame package's colours and button cells.
  The icons' cell, name line and frame go into the same piece before package 3I's brief.
- Look B reads the game's own bar sprites from the cache that COMPONENTS.md section 5 builds from the installed
  game's files. That cache is made from the jar on disk, so it does not need the game to run.
- No game installed, or a file that fails its check: the bar is drawn in A, as a whole piece. A fresh AresOS has no
  game installed, so it wears look A until he has picked the Minecraft world once.
- Nothing of Mojang's is committed. The bar's rows in the look-B map are names and numbers only. Every public picture
  of the bar is look A.

### Search

- Super opens the search on the home output, over whatever is there. The world, a full-screen app and the picture are
  all the same to it. It does not wake a sleeping world.
- It takes the keyboard for itself while it is open, and only then. Escape, a click outside it, or the recovery key
  ends it. It is exclusive, not "on demand", because labwc gives an on-demand surface the keyboard only on a click
  (LAPTOP-HOME.md section 6), and Super must give it at once.
- It finds as the laptop home's typing line does (LAPTOP-HOME.md 2.2). Enter opens the best hit or brings it back, on
  the home output.
- It finds the home styles by name. Its first row is "Start the Minecraft world" while that is his style and the
  world is closed for this session, and "Start anyway" while a start is pending. Until package 4 ships, its first
  row in a normal style is "Home style: Minecraft world" (section 6).
- It is drawn in the Bar look the owner chose for the search on board #382 (`STATE.md:143`), from the look pack.

**Super's one route.** labwc runs `aresos-desktop search`, and the supervisor signals its live helper in every
state. The helper takes the first route that holds:

1. **The native search.** A view `home` is connected and negotiated `search_view`: it gets `search_requested`.
   Nothing is activated, minimized or woken. If the view has not reported `view_focus` true within a second, the
   helper goes on down this list and tells the supervisor that the view did not answer.
2. **The mod's search.** The world is awake, and its desktop is ready and offered `shell_search`: today's route
   (helper `:4240-4284`). It is built, costs nothing, and is never removed.
3. **Otherwise the supervisor decides.** With a sleeping world, Super is a wake request with the keyboard. In OFF,
   or when the wake is not admitted, the supervisor opens its message window (section 12's chain, link 3).

**For 23c.** Its plan lets Super do nothing outside IN_WORLD, and signals only a helper whose desktop is connected
(`STATE.md:207`). Super must pass in every state, and also when only a view is connected.

---

## 9. The sleeping world

This note gives board T364 its place. It does not design swap, prefetch or when the world should sleep. After the
lead's scope decision it also does not fix the crash-safe mechanism or the memory rules. Those are gates 1 and 3
(section 13), and package 9 starts after them.

A sleeping world exists only in the Minecraft style. Picking a normal style closes a sleeping world without a thaw
(section 6).

**What is decided here**

1. **Never a frozen window on screen.** Asleep, the world is a still on the home output's picture, and its window
   is minimized. A frozen X11 window under the pointer would queue input it cannot read. No still on screen, no
   sleep.
2. **One still for three uses:** the sleeping world, the starting world (package 8), and a world closed in deep
   sleep. The mod makes it. The native home shows it and says so.
3. **The supervisor alone decides.** It alone freezes and thaws, as it alone starts and stops. The helper and the
   native home only send it signals and requests.
4. **The states exist:** ASLEEP and WAKING, beside OFF (`asleep`) for a world closed while asleep (section 6).
5. **Saved before frozen.** A world goes to sleep only after a confirmed save, taken when it is already paused.
6. **Nothing is asked of a sleeping world.** No save request, no SIGTERM, no heartbeat. The helper sends the mod
   nothing and never activates its window.
7. **A stop needs no thaw and is not a crash.** Today's stop routine cannot act on a frozen game. It would wait
   30 s for a save, send a SIGTERM nobody reads, run out its 60 s, and latch `unsaved` at the next boot (supervisor
   `:3323-3355`, `:3545-3557`, `:3629-3633`). So every stop of a sleeping world ends it as it is, and counts it as
   saved. How, and safely across a crash, is gate 1.
8. **A wake is admitted, not forced** (section 12). A world that cannot wake yet stays a still, `screens` says
   `waits`, and one toast says so.

**The order, in outline.** Gate 1 fixes the exact steps and what is on disk at each.

- *To sleep:* the still is made (`still`). The native home shows it (`still_shown`). The mod pauses the world and
  frees the pointer (`sleep`). The helper minimizes the window, and the compositor confirms it. The world is saved.
  The game's realtime threads are demoted, as package 318 found. The game's scope is frozen with the cgroup
  freezer. A step that fails before the freeze calls the sleep off.
- *To wake:* admission. The thaw. The mod draws, still paused, and ignores input that arrived before (`wake`). The
  helper shows the window. The mod runs again (`resume`). The native home takes the still away once `screens` says
  the world is on that output.
- *Why the save comes after the pause and the minimize:* from then on the world does not tick and he cannot touch
  it. So the save writes everything, and nothing changes after it.
- *T364's own steps* go after the freeze and before the thaw: memory to swap, Prism's memory, prefetch.

**Where the study starts.** Revision 1 of this note had a mechanism for decision 7: a durable sleep record, an end
by SIGKILL through the pidfd the supervisor already watches, and a new outcome, `dropped`, that is never counted,
restarted or latched. Review 2 found the middle sound and both ends of the record's life open. A supervisor that
dies between the mod's pause and the record, or between the record's close and `resume`, leaves a paused world that
nobody resumes. The study completes it. Whatever it settles on changes three written rules, for a sleeping world
only: "the supervisor never sends SIGKILL to the game" (supervisor `:79`), the `killed` latch for every SIGKILL end
(supervisor `:2408-2420`), and OS-BASE B5's "a killed game is an unclean stop" (`docs/design/OS-BASE.md:352`).
Package 9 changes those texts in the same commit as the code.

### Where the signals come from

| Signal | From | The world gets the keyboard |
|---|---|---|
| A click on the still | the native home (`wake_world`) | yes |
| Home: the bar's Home slot; Home picked in Alt+Tab; Super on its route 3 | the native home; the helper | yes |
| The app in front closed on the home output, and the world would get the focus | the helper | yes |
| The pointer comes onto the still (the owner's "predicted from the pointer") | the native home | no |
| The home output is no longer covered | the helper (`screens`) | no |
| To sleep: the home output covered, idle time, the lid, battery | the helper; the supervisor | |

- A wake that had to wait for memory never takes the keyboard when it finally runs. He has moved on.
- **The helper's own window calls for a wake are marked,** as Super's activation is (helper `:4143-4147`). It
  minimizes nothing because of them. For a wake without the keyboard it only brings the window back.
- **A frozen window is put away again.** Where the helper would have activated the world's window, it sends a wake
  request instead. If labwc shows the window itself, because he picked Home in Alt+Tab, the helper minimizes it
  again at once and asks for a wake. What holds while the helper is away is gate 1's row 8.

**Two depths of sleep.** Light sleep is the frozen game: a fast wake, but it keeps memory and may keep the NVIDIA
card awake. Deep sleep is OFF (`asleep`): the world closed, with its still left on screen. A wake starts it again.
The study decides when each applies.

**The same path at boot (package 8).** A starting world can look like a waking one: the last still and the bar show
at once, he can open apps, and the world comes alive when it is ready. The start-up cover is then needed only when
there is no still yet. Package 8 freezes nothing and wakes nothing, so it waits for no gate.

**Numbers so far, from the rigs only.** Package 318's three frozen games held 421 to 502 MiB resident with 598 to
682 MiB in swap; package 49's two held 494 and 510 MiB (`reviews/318-thaw-watchdog/FINDINGS.md:110`). The swap
figures were forced by the rigs' own reclaim of 600 MiB (`FINDINGS.md:29`). These are not product numbers. The
study measures the real session.

---

## 10. Migration

The in-game hotbar and the in-game search keep working throughout; neither is removed. No package takes a
launcher, the search or the hotbar away, or makes one worse, before its replacement works. The second table says
how each package shows that.

Sizes: S is one builder step, M two or three, L four or more. The rows are in build order. The numbers are kept
from the first version of this note. Package 3 is now five parts: 3a, 3b1, 3b2, 3I and 3V. Packages 11 and 12 came
with revision 3.

| # | Package | He sees | Lead | Needs | Size |
|---|---|---|---|---|---|
| 1 | **The helper for the session.** Started once per supervisor. The launch's nonce and keep-foreground flag handed over, acknowledged, and sent again to every new helper. Launches made at the JVM gate covered. Restarts that never stop. The home kept on disk. Output names. 23c's view token. | Nothing. Opening no longer breaks when the helper or the game restarts. | aresos (supervisor) with hub (helper) | Nothing. It reads 23c's plan first. | L |
| 2 | **Open apps and "bring back".** `apps_state` and `activate_app`, with `open_app` kept as the fallback. The mod marks hotbar slots, sends `activate_app` from a left click, gates and `/name`, and adds the right click on a slot. | Open and active marks on the hotbar. A left click brings Chrome back with its tab. A right click opens a new window. | hub | Nothing. Beside 1. | M |
| 3a | **The picture, one screen.** First the laptop home split into modules: no change in what it does, nothing removed. Then the program started by the supervisor, the view `home`, `aresos-picture` with `plain`, `black` and `file`, the converter, the picture settings, and `screens` from the helper. | The plain picture wherever no world shows, for example behind the sign-in window. | desktop, with hub for `screens` and aresos for the start | 1 | M |
| 6 | **Search outside.** The finder as `aresos-search`. Super's one route. The alive beat. The recovery key's third action. `notice`, and a first `aresos-toast` in look A. | Super works over any app and minimizes nothing. | hub, with desktop for the surfaces | 2, 3a, 23c's Super step | M |
| G2 | **Gate 2's step.** OFF, its records and the two doors in the supervisor, and a start that needs nothing of Minecraft's (row 8). Reachable by command only and only in the test rig. The image's command refuses OFF until package 7 ships. | Nothing. | aresos | 1, 3a (row 8's test starts the native home, which the supervisor starts from 3a on) | M (was S; row 8 is new) |
| 7 | **The home style switch.** The setting `home`, with `minecraft` still the default. The row in the AresOS menu, the search's rows, Prism's scopes, the memory check on the laptop. A normal style shows the chosen picture; no still, no icons and no video yet. | He can pick the picture home, and pick the Minecraft world again. | aresos with hub | 6 (so 1, 2 and 3a), gate 2 | M |
| 4 | **The bar outside.** `aresos-bar` in look A, slots and marks, the app menu, the home menu, the window requests, and section 8's rule with its zone. | A bar on the picture. Windows stop above it wherever section 8's rule gives it a zone. The home menu on the Home slot and on a right click on the picture. | desktop (surface) with hub (content) | 2, 3a, 6 (toasts) | L |
| 5 | **The bar at the bottom edge.** The strip, reveal and hide, tested against B321's barrier. | The pointer at the bottom edge brings the bar up over an app. | desktop | 4 | M |
| 11 | **Pins without the world.** The helper's own home document from the image's starter apps: nine at most, none if there are none. `set_pin`, and Pin and Unpin in the app's menu while no world runs. Rows without a logo only to a view that negotiated `pins`. | On a laptop that never ran the world, the bar has apps in it, and he can change them. | hub | 4 | M |
| 3b1 | **Every screen, in a normal style.** A picture surface and a bar on every output while the style is a normal one, made the moment an output appears. No world window is involved, so it needs nothing of 23c. | In a normal style with the monitor in, both screens show the picture and a bar. | desktop | 3a, 4, 7 | S |
| 3I | **Desktop icons.** The helper's `icons.json` and the icon requests. Icons over the background, click and menu, dragging, the alignment rule and its cases, the keyboard by a click. Each screen's own icons, by the screen's identity. The starter column, seeded once on a first normal home. | Icons on the normal home, on every screen, that he places freely and that straighten themselves. A first normal home starts with the starter apps in a column. | desktop (surface, dragging, alignment, look) with hub (the keeper, the seeding, click and menu rows) | 4, 7, 11, 3b1 | L |
| 12 | **The default flip.** The default of `home` becomes `picture`. The rule that keeps a laptop with a home on `minecraft`. A boot that never begins a first start. The first start from the home menu, and the way back out of it. The install guide's first-start steps (`docs/INSTALL.md`). | A fresh AresOS starts on the picture home, with its starter pins and icons. His own laptop does not change. | aresos with hub | 3a, 3b1, 3I, 4, 5, 6, 7 (so gate 2), 11 | M (was S; review 3, finding 15) |
| 3V | **Video backgrounds.** First one measuring step: both ways of drawing on the Intel chip, with memory, processor and battery, reported to the lead. Then the player, `aresos-video`: its own process, surface and scope; loop, no sound, the pause rules, `video-battery-pause`, a surface on every screen. The supervisor's part: start and stop, the hard limit, the beat, and turning the video off. The icons' own surface in the Video style. | "Video" in the home menu, on every screen. | desktop (the player, the surfaces), with aresos (the supervisor's part) and hub (the lines the helper passes on) | 3a, 3b1, 3I, 6, 7. The measuring step needs only 3a. | L (was M; a program of its own and a supervisor part) |
| 3b2 | **The second screen beside the world.** The picture and the bar on the output without the world, the surface that leaves when the world arrives, and the hotplug rules with a moving world. | With the monitor in and the world on it, the laptop screen shows the picture and a bar. | desktop with aresos | 3a, 4, 3b1, 23c | S |
| 8 | **Stills and the quiet start.** The lifecycle channel's `still`. A still before every planned stop. The boot path. The world's window minimized until ready. | Boot shows his home at once; it comes alive when ready. | hub (mod) with aresos | 3a, 4 | L |
| T364 | **The study: gates 1 and 3.** Its rigs and its measurements on the image. | Nothing. | hub with aresos | Nothing. Package 8's stills help its rig. | L |
| 9 | **The sleeping world.** `sleep`, `wake`, `resume`, the sleeping states, the wake signals. | The world sleeps and wakes. | hub with aresos | 7, 8, gates 1 and 3 | L |

**Packages 1, 2, 3a, 4, 5, 6 and 11 depend on no gate. Package 8 depends on none either:** it adds stills and a
hidden start, and no sleep, freeze, wake or new start. If its brief grows one of those, gates 1 and 3 apply to it.
Packages 3b1, 3I, 3V, 3b2 and 12 have no gate of their own. Each needs package 7, so each stands behind gate 2 with
it.

**What must still work after each package**

| After | Must still work | Shown by |
|---|---|---|
| 1 | The world's hotbar, gates, `/name`, the mod's search and Super's route to it, with any helper that replaces the first. | Under a running world: kill the helper; replace the supervisor; start the game from Prism's own window. Each time the mod's next hello is accepted and a hotbar click opens an app. A restart after a crash still waits below the app in front. |
| 2 | Opening from the world against a helper without `activate_app`. The laptop home's 1.2 view. | The mod against a 1.2 helper sends `open_app`. The 1.2 example messages pass unchanged. |
| 3a | All that the laptop home does today. | Its tests pass unchanged after the split. No surface, slot or typing line is removed. |
| 6 | Super over an awake world when the native search is absent, silent or hung. | Kill the native home: Super reaches the mod's search. Stop it mid-search: the alive beat ends it within seconds, and then Super does. The recovery key ends it with the supervisor stopped. |
| 7 | A launcher at every moment, and the way back. | With the native home killed, and again with it stopped (hung), a change to a normal style is refused with one line. In OFF, `world on` from the recovery terminal starts the world. With Minecraft's pin file made unreadable, a boot in a normal style still shows the home. |
| 4 | The world's own hotbar, untouched. | The mod's tests. The old view's slots, clock and battery leave only in this package. |
| 11 | The world's own pins, while a world runs. The old view. | With the mod connected, `set_pin` is refused and the published pins stand. With no home ever published, the bar shows the starter pins and the search opens every app. A view on minor 2, or one that did not negotiate `pins`, gets no row without a logo: its `get_home` answers as with no home. With an empty registry: nine empty pins, and the search still opens every installed program. |
| 3b1 | The home on one screen, and the Minecraft style as it is. | With one screen nothing changes. In a normal style a second output is added and taken away in the rig: the first screen's picture and bar never leave, and the second has both while it is there. In the Minecraft style nothing new is drawn on any output. |
| 3I | The bar and the search, whatever the icons do. A home already in use. | With a broken `icons.json`: no icons, the bar and the search work, and the file is kept aside. With the helper killed in mid-drag: the icon is back at its last kept place. An app removed and installed again gets its place back. On a laptop with a home document or an `icons.json`: nothing is seeded, and his pins and icons are as they were. On a first normal home the column appears once; after he has removed every icon, a new login brings none back. |
| 12 | His laptop as it was, and a fresh laptop without Minecraft. | In a VM. An update over a home that was ready once boots into the world; the file had no `home` value before and has `minecraft` after. A fresh install boots to the picture home with no network and with the pin file unreadable. Its first home shows the starter pins and the starter column, and with a second output the picture and a bar on both screens. Picking the Minecraft world shows Prism's sign-in uncovered. Closing it, failing it and rebooting in the middle each leave the picture home, and the next boot opens no sign-in. |
| 3V | The bar, the search and the icons, whatever the video does. | Five runs in the Video style. A file that is gone, and a file the decoder refuses: the picture shows and the setting is not changed. A decoder that hangs (the player stopped by a signal stands in): the video is off within five seconds, with its toast. A file that ends the player at each loop: the video is off after the second end, however far apart the ends are. After the video was turned off, picking Video again (the style is still Video) plays it again. A player that grows to its limit: the kernel ends it in its own scope, and no other scope is touched. In every run Super opens the search and a bar click opens an app within one second, during the fault and after it. In every style the native home's process has no GPU driver and no decoder mapped. In the Picture and Minecraft styles no player runs. |
| 8 | The start-up cover when there is no still, and every recovery window in view. | A first boot shows the cover. A slow start shows `slow_start` over the still. |

**Dropped:** package 10, "One bar". The owner keeps both bars (T483). Both look alike in look B, so one bar stays
possible later as a setting if he changes his mind.

**Later, each its own package:**

- system notifications in the toast surface (desktop);
- a program's own actions in its menu, such as a private window (hub: the helper parses no action groups today);
- pins he changed outside carried into the world (hub);
- look B for the bar, with the desktop's look work;
- a full layout that counts as filling, with the covering package;
- a chooser for the picture and the video file, and a settings window outside the game (desktop with hub). A video
  preview is never decoded in the native home;
- moving several icons at once, and files or folders on the home (desktop);
- shut down, restart and log out as rows in the home menu and the AresOS menu (hub with aresos);
- a "Normal" look, if the owner wants it (question 7; desktop).

**Order notes**

- Package 2 is the try-out's fixes 7 and 10 on the final protocol. It can start now, beside package 1.
- **The switch comes before the bar.** The owner asked for it first, and the search alone is a launcher. Between
  packages 7 and 4 a normal home has Super's search, Alt+Tab and the picture, and no bar. Until package 5 there is
  no bar over a maximized app.
- **The owner's switch does not wait for the flip.** Package 7 gives him the choice on his laptop. Package 12 only
  changes what a fresh AresOS starts with.
- **What the flip waits for.** INPUTS-2 names the picture, the bar, the search and the style switch: packages 3a, 4,
  6 and 7, and gate 2 through 7. Revision 3 added packages 5 and 11, and review 3 found both needed. Without 5 the
  first maximized app hides the bar for good, and `rc.xml:47` maximizes the terminal. Without 11 the bar has nine
  empty slots. The lead's decision on review 3 adds package 3I: the owner chose a first home with starter icons
  (T498). 3I needs 3b1, so a fresh AresOS with a monitor has its home on both screens.
- **Package 3 is split, not grown.** Only 3a stands before the switch, and it stays the size the reviews saw. The
  video needs a measurement before anyone can offer it. The icons need the bar's menu and a new file in the helper.
  Either one inside 3a would hold up the owner's switch for things it does not need.
- **3b is split too.** 3b1 is the part a normal style needs: a picture and a bar on every output, with no world
  window to move. It comes before 3I and 3V, so both are built for every screen from their first day. 3b2 is the
  part beside the world, and it waits for 23c.
- **3I before the flip, 3V after it.** The owner described the icons in detail (T494), chose the first ones (T498),
  and they carry no open choice of renderer. The flip waits for 3I and not for 3V. 3V's measuring step can run
  early, beside package 4, because it needs only 3a.
- **What the switch needs from the bar's package has moved forward.** `screens` comes with 3a, and `notice` with a
  first toast comes with 6. So package 7 can say that the world is closed, that a start waits, and why a request was
  refused.
- **Gate 2's step comes first, and alone.** It builds OFF in the supervisor with no setting, no menu row and no
  caller. Nothing of the switch that he can reach is built before its tests pass.
- **Only 3b2 waits for the monitor work.** The search needs 23c's Super step alone: the key binding and
  `aresos-desktop search`. If 23c is later, `linux-aresos` pulls that step forward. With two screens the search's
  app opens on the home output only once 23c places windows.
- **Who takes the laptop home over.** It belongs to `linux-laptop-home` today (`docs/HUB-HANDOFF.md:120`). This
  note's choice: `linux-laptop-home` splits the 2,637-line file into modules as its hand-over step, then
  `linux-desktop` leads the program and the hub leads its content modules. The three leads confirm that before
  package 3a's brief. Two leads in one file would be a merge hazard.
- Package 1 changes when the helper starts, so it touches 23c's plan. `linux-aresos` reads it first.
- Every `rc.xml` change goes to `linux-aresos` first, as always. This note adds one: the recovery key's third action
  (6). Clicks on a bare desktop are off since package 329.
- The desktop writes its own briefs for 3a, 3b1, 3b2, 3I, 3V, 4 and 5 once this note is reviewed.

---

## 11. Questions for the owner

### Answered on 2026-11-21

1. **The default picture** (T482): "A plain picture".
   The default behind apps and on the picture home is a plain picture that `linux-desktop` draws in the look. Black
   and his own picture stay settings. The town is no longer the default; it stays a kind, at no extra cost.

2. **One bar instead of the hotbar** (T483): "Ohhh good question. So the Mc hotbar wouldn't exist then? But isn't the
   taskbar design the Minecraft hotbar ? So I think keeping both makes sense".
   Both stay. In the world: the game's own hotbar, with the open and active marks. Wherever the awake world is not
   in view: the bar outside, which looks like the hotbar in look B.

3. **A bar on every screen** (T484): "Yea both makes sense but only when going down right?". And on whether it stays
   visible on a screen nothing fills (T485): "Visible there (recommended)".
   A bar on every screen. It is visible on a screen nothing fills and waits at the bottom edge while a window fills
   it. Each bar goes by its own screen's state.

### Answered on 2026-11-22

5. **What the home is, and what a fresh AresOS starts with.** His idea: "AresOS should offer completely normal
   homescreen customization with pictures and videos as backgrounds and app icons on top of that, with the minecraft
   home being one option." And on the start of a fresh AresOS (T493): "Normal picture home".
   The home has three styles: Picture, Video and Minecraft world. A fresh AresOS starts on the picture home, and the
   Minecraft world is the special option. His own laptop keeps the Minecraft world until he switches (section 6).

6. **How icons are placed** (T494): "Free dragging for sure but easy alignment and stuff. On Mac OS it's hard to get
   them in one clean line so that should be easy like a setting that if activated automatically recognizes lines,
   grids etc and straightens them".
   He drags icons freely. A setting, on from the start, recognizes the rows, columns and grids he is making and
   straightens them: shared lines and even spacing. With it off, an icon stays where he drops it (section 6).

8. **What is on a normal home the first time it shows** (T498): "Starter icons column (recommended)".
   The first normal home shows the picture, the bar with the image's starter apps pinned, and those apps as icons in
   one column at the top left. Each can be removed with a right click. The icons are seeded once, and never on a
   home already in use. The flip to the picture home waits for the package that brings them (sections 6 and 10).

### Answered by his guideline

7. **AresOS can also run as a completely normal OS** (the owner via `mac-capacity`, 2026-11-22, confirmed as a
   guideline, not a rigid rule): "AresOS designs and features are switches (which design, which home, tools on or
   off)", without forcing a key AresOS piece to be switchable where that isn't needed or possible. Normal features
   still get good design, technical as well as visual; icon arrangement is his own example.
   *How this note does it* (the lead's call, within his guideline): one more look, "Normal", beside A, B and C, and
   not a switch for each piece. He then
   has two choices that work in any mix: the home (Picture, Video, Minecraft world) and the look (A, B, C, Normal).
   One look changes the bar, the search and the frames together, so the pieces always fit each other. Every extra
   switch would double what must be built and tested. `linux-desktop` draws the Normal look and shows it to him
   before anything is built. Until then a fresh AresOS wears look A. Section 12 has what it covers.

### Open

Nothing is open. Question 8 was the last, and T498 answers it.

### To tell him, not to ask

- **His laptop keeps the Minecraft world.** Nothing changes for him until he picks another style, in the AresOS menu,
  the home menu or the search.
- **Minecraft's sign-in moves.** On a fresh AresOS, Prism asks him to sign in when he first picks the Minecraft
  world, not at the first boot. If he closes the sign-in, he is back on the picture home.
- **One click opens an icon,** as on the bar. A drag moves it. A right click opens the app's menu.
- **The video is silent** and pauses when a window fills the screen and on low battery. It is offered once its cost
  is measured.
- **A video that fails is turned off, and the picture stays.** The bar and the search are not affected. He picks
  Video again to try it.
- **His own picture or video is set by a command for now,** which Claude can run for him. A chooser comes later.
- **The search keeps its look.** The search outside the game replaces the one over the world that he chose the Bar
  look for (board #382). It is drawn in that same look.
- **A typed name and a gate now bring the app back.** On board #155 he chose that each Chrome-logo click opens a new
  window. After the try-out he asked for "left click opens or brings back the app, right click opens its options".
  So `/chrome`, a gate and a left click bring Chrome back. A right click on its hotbar slot opens a new window, from
  package 2 on. The full menu comes with the bar outside.
- **Home in a normal style opens the home menu.** It never starts the world by surprise. The menu lists the three
  styles.
- **Windows stop above a bar that reserves its height** (section 8's rule: `shown`, and not the home output while
  `world` is not `off`). There a maximized window first fits above the bar and then takes the whole screen as the bar
  slides away. On the home output with the world asleep or starting, the bar shows but reserves nothing.

### Decided by the lead (review 1's finding 17, review 2's point 4)

4. **The bar with a window that does not fill the screen** (lead's decision, 2026-11-21, with `linux-desktop`'s
   point from revision 2). The owner already answered the case: T485 asked about "just the picture or small
   windows", and he chose "Visible there". This is section 8's rule, in the same words:
   - **The bar is `shown` on a screen nothing fills,** also one with part-screen windows. Its layer surface then
     sets an exclusive zone of the bar's height, as the Windows taskbar does. labwc places, snaps and maximizes
     windows above it, so it covers none of their rows.
   - **It waits at `edge`, with zone 0, while a window fills the screen.** `edge` follows covering, and covering
     follows the maximized and full-screen states, so there is no resize loop.
   - **On the home output the zone stays 0 while `world` is not `off`:** awake, asleep or starting. A zone
     would re-fit the world's own maximized window. The in-game hotbar is the bar there anyway (T483).
   - **The zone applies only while the bar is `shown`,** on every output except the home output while `world` is not `off`.
   - **Known limits:** a part-screen window he drags down over the bar keeps its bottom rows under it; and on the
     home output a part-screen window can reach under the bar while the world sleeps or starts (section 12).
   - **For `linux-desktop`:** package 4's brief checks that labwc 0.9.6 honours a changing exclusive zone on a
     layer surface, and what it does to windows that are already maximized when the zone appears.

Not asked, because the note decides it or he has already answered: where the search opens (board #334), that a
sleeping world wakes on a click, that picking the Minecraft world never covers his apps, and that a normal home
stays until he picks the world. The desktop will show him the bar's and the icons' look in its own component
pictures. Package 3V will ask at which battery level a video pauses, with the measured drain. The T364 study will
ask how soon the world should sleep, with measured wake times.

---

## 12. Risks, known limits, assumptions

### Real harm, and how the structure answers it

| Harm | Answer |
|---|---|
| **Lost building work when he leaves the Minecraft world or it is put to sleep.** | Both go through a confirmed save. Without it the style stays Minecraft world and sleep does not happen. A style change never touches a world's files. |
| **A stop or shutdown that hangs on a sleeping world; a sleeping world taken for a crash; a paused world nobody resumes.** | Gate 1. Package 9 does not start before a rig shows that none of the three can happen. |
| **Memory is full when the world should start or wake** (the owner's worry). | See below, and gate 3. Until it passes, nothing thaws or starts a world by itself beyond what does so today. |
| **The world starting by itself after he chose a normal home.** | In OFF only his own request starts it (section 6). Gate 2 shows that this holds across a crash, a new supervisor, an old restart deadline and Prism's own button. |
| **A normal home with no way to open an app.** | A change to a normal style is refused while no view `home` with the search is connected (section 6). |
| **A normal home that dies with Minecraft's files.** | In a normal style the boot reads no pin file, makes no instance and starts no Prism. A fault there shows only when he picks the Minecraft world (gate 2, row 8). |
| **The update that flips the default takes his home away.** | A laptop that has had a home is set to `minecraft` before the style is read, at every supervisor start (section 6). Package 12's VM test shows it. His world's files are not touched either way. |
| **A video that takes the bar and the search down with it.** | The video is not in the program that holds them. It plays in a process, a surface and a scope of its own, under a hard memory limit. A stall, a leak or a crash loses only the video, and the picture shows under it. After a second end or one missed beat the supervisor turns the video off and says so (section 6). Package 3V's tests check the bar and the search during each fault. |
| **A home that cannot come back.** | A chain, each link independent of the one before: (1) the native home is restarted when it ends, for as long as the session lasts; (2) the world's own hotbar and the mod's search never depend on the native home; (3) in OFF, after the native home's third failed start, and whenever Super finds no view and no awake world, the supervisor opens its message window. It says how to try the bar again (`retry`) and how to start the world (`world on`), and it starts nothing; (4) the same commands work from the recovery terminal; (5) if the world cannot start either, today's recovery window says why. His open apps stay reachable by Alt+Tab throughout. |
| **A hung search that holds the keyboard.** | Three ways out. The search sends an alive beat from its drawing loop; after three silent seconds the supervisor ends the native home's scope. The recovery key gets a third action, first in line, that kills `aresos-home.scope` through the user manager. It needs no supervisor and no helper, and it is what lets the terminal get the keyboard (`docs/design/COMPONENTS.md:1204-1208`). And Escape or a click outside closes a search that still answers. The program keeps no state of its own, so ending it loses nothing. |
| **A dead session because a new piece fails.** | The native home is never part of readiness, and neither is the player. Their restarts are spaced and never end the session. A click on a bare desktop already does nothing (`rc.xml:40-44`, package 329). |
| **The helper is needed more than before.** | Its restarts never stop for good, and every new helper gets the running launch's nonce, so the world's own hotbar and search open apps again after it (section 5). While it is away the bar shows its last state and "Opening is back in a moment". |
| **A sleeping world while the helper or the native home is gone.** | Gate 1, row 8. |
| **Mojang's files in the repo.** | The still and look B's cache stay in his cache folder. They never go into the repo, an image, a backup or a report. Public pictures are look A. |

### When memory is full

The home must never kill his work. This note decides the structure. Gate 3 has to show that it holds.

1. **The picture and the bar need nothing new.** They are already in memory. They show whatever happens to the
   world.
2. **The supervisor owns admission.** A start out of OFF, and from package 9 every wake, first passes a memory test
   at the supervisor, at both doors (section 6). The test fails closed: a sample it cannot read, or an old one,
   admits nothing. Only he can override it, with "Start anyway".
   - *Package 7's form of the test* is the simplest one: the system-wide sample the supervisor already reads
     (`some avg10`, supervisor `:1069`; at most the 10 % of `PRESSURE_CLEAR`, supervisor `:228`), taken every 5 s
     while a start is pending. It is a courtesy to him, not a proof. Nothing hangs on it but a start he asked for.
   - *Starts that exist today do not change in package 7:* the session's first, the restart after a crash, `retry`
     and `restart`. The rule after a `killed` latch stays (supervisor `:2589-2601`). Whether admission later covers
     them is gate 3's call.
3. **The world is the one to give way.** Under pressure the supervisor ends a sleeping world itself, before the
   system has to choose. That costs no work, because a sleeping world is saved. A world he is using is never put to
   sleep or ended by force.
4. **Today nothing makes the world go first.** The game's scope has a soft limit and no kill preference. His apps
   run in `app.slice` scopes with none either. Only the login session's scopes are protected (section 3). An
   `oom_score_adj` on Java would bias the kernel's own killer and not systemd-oomd. Revision 1 compared the
   supervisor's system-wide pressure sample with systemd-oomd's upstream limits. Those are two different measures,
   so the comparison proves no order (review 2, point 3).
5. **So until gate 3 passes, nothing thaws or starts a world by itself** beyond what does so today. Package 9 waits
   for it.
6. **The awake world is the limit, as today.** If the system kills an awake world, up to five minutes of building
   are lost (`docs/design/HUB.md:59`) and `killed` latches as today. Before package 9 this note lowers that risk in
   one way: he can pick a normal style.
7. **A video never competes with his apps.** The player's scope has a hard memory limit and no swap. A video that
   grows is ended inside its own scope. His apps and the native home are not touched (section 6). Package 3V sets
   the figure.

What he notices on a full laptop once all of it is built: his apps stay, the home stays usable, and the world comes
back later.

### Switchable pieces (the owner's guideline, 2026-11-22)

AresOS can run as a completely normal OS, and its designs and features are switches (INPUTS-2, confirmed). It is a
guideline, not a rigid rule: a key AresOS piece isn't forced to be switchable where that isn't needed or possible.
This is what it covers, and whether the structure stands in its way.

| Piece | AresOS's own form | A normal form | What would switch it | In the way? |
|---|---|---|---|---|
| The home | the Minecraft world | Picture or Video, with icons | `home` (section 6) | No. Revision 3. The video is a program of its own, so it switches on and off without touching the rest. |
| The first start | Prism's sign-in | none; the starter pins and icons instead | follows the home | No. Package 12. |
| The bar outside | a hotbar: Home, nine slots, marks, in look A, B or C | a taskbar strip | one more look | No, with two cautions below. |
| The search | the Bar look (board #382) | a plain launcher | the look | No. It names no colour. |
| Window frames, labwc's menus, Alt+Tab | look A, B or C | a plain frame | the look | One thing: the title font is fixed in `rc.xml` for every look today (COMPONENTS.md 4.2). |
| The indicator, the overview, toasts | the look pack | the same pieces from another pack | the look | No. |
| The hotbar in the world, gates, `/name`, stills, the sleeping world | parts of the Minecraft world | they do not exist in a normal style | follows the home | No. |
| Recovery and setup windows | a terminal with the reason | none at boot in a normal style (section 6) | follows the home | No. |
| The settings screen | in the AresOS menu, drawn by the mod (COMPONENTS.md 4.7) | a settings window outside the game | | Not blocked, but missing. In a normal style he uses the home menu or a command until one exists. |
| Shut down, restart and log out | none: the AresOS menu lists none (`STATE.md:144`). The power button, held about a second, shuts down cleanly (`STATE.md:173`). The rest is a command in a terminal. | rows in the home menu, as any desktop has | not a switch: the same rows serve both forms | Not blocked, but missing in both forms. A fresh user on the picture home meets the gap first. A later package (section 10). |
| The password windows | look A inside, in every look, on purpose (COMPONENTS.md 4.6) | unchanged | not switched | No. That rule is about safety. |

**Why the structure allows it**

- Function and look are split for every piece (COMPONENTS.md section 1). The bar, the search, the menus and the
  icons here name no colour and no layer (section 4).
- The world is the optional third layer (decision 1). After gate 2's row 8 a normal style needs nothing of
  Minecraft's.
- The helper gives every bar and every home the same facts.

**What a normal look of the bar would need.** It is one more look beside A, B and C, and it is `linux-desktop`'s to
design in COMPONENTS.md. COMPONENTS.md already plans a later value of the look setting for the Ares-apps look
(`docs/design/COMPONENTS.md:1449`), so a "Normal" look would be another value of the same setting.

- A look pack with plain colours, a normal text font, and pictures that scale smoothly. Today every sprite scales
  by whole numbers without smoothing (COMPONENTS.md section 3). The pack would have to say which.
- Shape from the pack, not from the bar's code: edge to edge or centred; empty pins drawn or left out; names beside
  the pictures or not; where the clock and the status icons sit.
- The apps' own pictures in the slots, not the 12 × 12 block logos.
- For window frames: a title font for each look. Then the look switch must also change `rc.xml`'s font lines, and
  every `rc.xml` change goes to `linux-aresos` first.
- No new content. Pins, open apps, marks, the menu, and the left and right click stay the hub's one bar model.

**Two cautions for package 4,** so the choice stays open at no cost. The bar's code does not fix that nine slots are
always drawn, and it does not fix that the bar is centred. Both come from the look pack, where A, B and C say "nine"
and "centred".

This note's recommendation is question 7 in section 11: two switches, the home style and the look, and no switch for
each piece.

### Known limits (low harm)

- **Until brief 328 lands,** the world holds the pointer after a click on it. Crossing to the other screen needs Esc
  first. That is 328's job.
- **A full-screen app that locks the pointer** (a game) cannot reveal the bar. Alt+Tab and Super work.
- **The last pixel row** of a screen with a strip belongs to the strip. A click there brings the bar up.
- **Deskflow:** if the Mac sits below the laptop, that output's bottom edge is the barrier's and gets no strip.
  Apps there are reached by Super's search and Alt+Tab.
- **Screens stacked one above the other:** the upper screen's bottom edge is shared, so the pointer does not stop
  there. He rests on the boundary to reveal that bar.
- **A part-screen window he drags down over a visible bar** keeps its bottom rows under it. labwc does not move a
  window when the zone appears. He can drag it away.
- **On the home output the zone is 0 while `world` is not `off`.** With the world asleep or starting, a
  part-screen window that reaches the bottom has its last rows under the bar until the world is awake or he moves
  the window.
- **With the world awake and a part-screen window over the bottom centre,** the hotbar is behind that window and no
  outside bar comes up. Super's search and Alt+Tab work.
- **A window maximized on a screen where the bar reserves its height** resizes once more as the bar leaves.
- **A toast is on the top layer,** so a true full-screen window hides it. A launch that fails meanwhile is in the
  helper's log.
- **Between packages 7 and 4** a normal home has no bar, and until package 5 none over a maximized app. Super's
  search covers that time.
- **Between packages 7 and 3b1 a normal home is on one screen.** With a monitor plugged in, the other screen has no
  picture and no bar, as today. Windows there work, and Super's search and Alt+Tab reach every app. Icons and video
  are on every screen from their first day, because 3I and 3V come after 3b1. In the Minecraft style the second
  screen stays as it is today until 3b2 and 23c.
- **Until 23c places windows,** the search's app opens where labwc puts it when two screens are on. The `screen`
  hint is only recorded.
- **After Super woke a sleeping world** because no native search was there, the search does not open by itself. He
  presses Super again.
- **In a normal style:** no gates and no `/name`. Pins can be changed from package 11 on. A program installed
  meanwhile joins My apps when the world next runs. The search finds it at once anyway.
- **Pins he changed outside are replaced** by the world's own when the world next publishes its home. Carrying them
  into the world is a later hub package.
- **With more than nine starter apps,** the tenth and later are neither pinned nor seeded as icons. The search finds
  them, and he can pin them or add them to the home.
- **The starter icons are seeded once.** A laptop that already had a home, or whose icons he removed, never gets
  them. He adds icons with "Add to home". A laptop whose home document was lost is seeded as a first home is; he
  removes what he does not want.
- **A window nobody owns** has no slot in the bar, and its app starts a new instance on every left click. Ownership
  needs a reviewed identity; a hint fixes a known program.
- **Two rankers** for the search, one in the mod and one outside, kept in step by shared test cases.
- **The still can be old** after a crash, since it was made at the last sleep or planned stop. After a hotplug it is
  scaled to the new screen until the world wakes.
- **At sleep in view** the world's hotbar gives way to the bar outside at the same place. They look alike in look B,
  not in A. The bar's slots show the 12 × 12 logo, the hotbar the item icon.
- **Picking the Minecraft world with apps open** shows Prism's own window for a moment, and it may take the focus.
  Package 8 hides only the game's window.
- **A helper or supervisor restart** leaves the bar on its last state for a few seconds.
- **A shutdown while no supervisor answers** waits the guard's own times, up to 72 s, also with a sleeping world.
  Gate 1 only keeps a false `unsaved` latch from following it.
- **After `previous` to an older release,** its `aresos-settings set` drops the new names
  (`os/config/usr/libexec/aresos-settings:60-68`). A release from before package 7 knows no styles and starts the
  world, so a laptop that never signed in sees the first start at boot there. Back on the newer release, a laptop
  with a home is on `minecraft` again, even if he had picked Picture before, and the picture is plain again. Nothing
  is lost.
- **Prism's 418 MiB** stay while the world is on. Whether Prism can leave after the launch is the memory study's
  question.
- **Light sleep may keep the NVIDIA card awake** on battery. Not known. If it does, the study uses deep sleep there.
- **A click on the active app's slot** does nothing more. Minimizing it on a second click is a small later change.
- **A fresh AresOS wears look A.** Look B needs the installed game, which a normal home never downloads.
- **His own picture and video are set by a command** until a chooser exists. So is every setting but the style and
  the alignment, in a normal style, until a settings window exists outside the game.
- **Shut down, restart and log out have no row in any menu yet.** The power button and a command do it until the
  later package.
- **The `town` picture needs a home the mod published.** It is not offered on a laptop that never ran the world, and
  a home document the helper made does not count.
- **Icons are for apps only,** one at a time. No files or folders on the home, and no moving several icons at once.
- **Icons under a window** are reached by moving or minimizing it. There is no "show the desktop" yet. The bar and
  the search open the same apps.
- **An icon he drags is hidden while it passes under a window.** It is drawn below every window.
- **The icons of an unplugged screen wait** until it is back, or until he picks "Bring all icons here".
- **Two monitors of one make and model that give no serial number** are told apart by their connector name only. On
  one socket they share one icon arrangement.
- **The video's decoder is not sandboxed as the picture converter is.** A chip's decoder needs the GPU device. It
  runs in the player's own process and scope, which hold no view token and no launch secret. The file is his own
  pick and local, as in any video player.
- **A stalled video shows its last frame for up to three seconds** before the picture takes its place.
- **A video that was turned off stays off** until he picks Video again or logs in again. The setting still says
  Video meanwhile.
- **After the native home restarts in the Video style,** the video is away for a moment: the player is started
  afresh so that its surface is the newer one.
- **In the Video style the icons have a surface of their own,** so one more see-through picture per screen is kept
  in memory. Package 3V measures it.
- **While a start waits for memory,** the style is already Minecraft world, so his icons are hidden and the picture
  shows. Picking Picture again brings them back and ends the wait.

### Assumptions and things to verify

In a private labwc:

- The stacking: background, bottom, always-below windows (the world), windows, top, full-screen, overlay. That
  `set_layer` works. That a full-screen window hides the top layer.
- That labwc 0.9.6 honours an exclusive zone that changes on a live layer surface, and what it does to windows that
  are already maximized then.
- That labwc 0.9.6 offers `wl_output` version 4.
- That activating a minimized window brings it back, and that `unset_minimized` does not take the focus.
  COMPONENTS.md lists both as open.
- That an overlay surface with exclusive keyboard gets the keyboard while the game holds a pointer lock, and that a
  window gets the keyboard back when that surface's program is killed.
- That minimizing the world's X11 window from outside hides it without the game's help.
- That Minecraft loads normally while its window is minimized (package 8), and that the mod can ask for its own
  window back.
- For package 3I: that a background-layer surface with the keyboard on demand gets it on a click and at no other
  time, also not when the last window closes.
- For packages 4 and 3I: that a popup of a background-layer surface shows above windows.
- For package 3I: that a drag begun on the background keeps getting the pointer's movement over windows and across
  to the other screen.
- For package 3I: where labwc 0.9.6 gives a client a screen's make, model and serial number.
- For package 3V: that of two background-layer surfaces labwc keeps the one made later on top, and that it stays
  there. If labwc gives no sure order, 3V's first step reports that to the lead before a player is built.
- For package 3V: that a surface with an empty input region lets every click through to the surface under it.
- For package 3V: the three checks listed for package 3I above, for the icons' bottom-layer surface.

In package 1: that the mod tries its hello again after a refusal.

In package 3V:

- Which chip labwc draws on in his session (LAPTOP-HOME.md's laptop trial checks it), and how the player learns it.
  If it cannot tell, the GL way is off.
- That the image holds the Intel chip's VA-API driver and a decoder for the formats it names.
- That `MemoryMax` and closed swap on a scope of his user manager end the player and nothing else.
- Where "the screens are off" is read from. The image's idle set-up was not read.

Release checks (review 2, finding 6):

- The recovery key ends a hung search that holds the keyboard, with the supervisor stopped.
- Prism stays open after the game exits, and keeps its sign-in through SIGTERM.

The sleeping world's and the memory checks are rows of gates 1 and 3 now.

Not read or not there:

- The image has no notification service today.
- The laptop's swap set-up and the image's effective systemd-oomd settings were not read; the T364 study and
  `linux-aresos` own them.
- 23c's move of the world is a plan. Brief 328 was not in the checkout.
- The image's video decoding and the first-start steps in `docs/INSTALL.md` were not read.
- The helper's registry folder could not be listed with the tools at hand. One entry was read,
  `os/config/usr/share/aresos/apps/terminal.json`. How many starter apps the image has is not known here.
- For revision 3 these were read: the supervisor's start, pin check, instance making, SETUP text and keeper; the
  helper's `get_home`, `publish_home` and catalogue; the laptop home's surface and decoder; `aresos-settings`;
  `rc.xml`; LAPTOP-HOME.md's section 4. Revision 2's other line references were spot-checked in the supervisor and
  the helper and still match. Those of `rc.xml` were corrected.
- For revision 4 these were read: review 3 and INPUTS-2's last two parts; `aresos-settings` whole; the supervisor's
  constants, start, keeper, command list, latch and the first lines of its stop request; the helper's registry
  loader and `get_home`; the laptop home's saved-home reader; `rc.xml`; LAPTOP-HOME.md's section 4; and the lines
  this note cites in `STATE.md`, `docs/HUB-HANDOFF.md` and COMPONENTS.md. The four stale references review 3 named
  were corrected.

### The OS part, from `linux-desktop`

Written by `linux-desktop` on 2026-11-21 (`reviews/332-outside-game-design/INPUTS-1.md`) and folded in here, with
its point for revision 2 about the zone on the home output and its points for revision 3 on video, icons and memory
(`reviews/332-outside-game-design/INPUTS-2.md`). The sections above use these names and rules. Revision 4 changed
the video's and the icons' rows after the lead's decision on review 3. `linux-desktop` confirms them in package 3V's
brief.

**Layers** (wlr-layer-shell on labwc 0.9.6)

| Surface | Namespace | Layer | Keyboard | Details |
|---|---|---|---|---|
| Picture, and the icons in the Picture style | `aresos-picture` | background | on demand in the Picture style: only a click gives it the keyboard. None in the Video and Minecraft styles and under a still. | Anchored on all four edges, exclusive zone -1. Its input region is the whole output, so clicks and drags on the home are the home's and never reach labwc's Root context. In the Picture style icons are drawn on this same surface. |
| Video | `aresos-video`, the player's | background, made after the picture's surface, so above it | none | Anchored on all four edges, exclusive zone -1. An empty input region. One for each output that shows the video. Only in the Video style. |
| Icons in the Video style | `aresos-icons` | bottom: above the video, below every window | on demand: only a click gives it the keyboard | The native home's. See-through but for the icons. Its input region is the whole output, so clicks and drags stay the home's. |
| Bar | `aresos-bar` | top while `shown`: above windows, below a true full-screen window. Overlay while revealed, by `set_layer` (layer-shell version 2 or later), and back to top when it hides. | none | Anchored bottom, left and right. Exclusive zone: the bar's height while `shown` with `reserve` yes; 0 in every other case. So it is 0 at `edge`, at `none`, while revealed, and on the home output while `world` is not `off` (awake, asleep or starting). So it is the bar's height only while `shown`, on every output except the home output while `world` is not `off`. Its menus are popups on it, pointer only. |
| Strip | `aresos-bar-edge` | overlay | none | It exists only while that output's bar is `edge`. 1 logical pixel high, full width, exclusive zone -1, a transparent buffer with an input region. |
| Search | `aresos-search` | overlay | exclusive while open | Esc, a click outside, or the recovery key ends it. |
| Toast | `aresos-toast` | top | none | An empty input region, so clicks pass through, as with the indicator. Not over a full-screen video. |
| Indicator | as package 320 built it | overlay | none | It stays above all of these. |

- No surface uses the namespace `aresos-input-barrier`. B321's labwc patch treats that one as the capture surface.
- **Why 0 on the home output:** a zone also re-fits the world's own maximized window. Every switch between `none`
  and `shown` would resize the game, with a new layout and a still that no longer fits.

**Video** (INPUTS-2)

- The native home's renderer is Cairo only. So either the video surface gets GL with hardware decoding (VA-API on
  the Intel chip), or the video is capped in resolution and frame rate and stops on battery. Package 3V's brief
  measures both.
- A video is paused when covered, and on battery below some level. The level is an open setting
  (`video-battery-pause`).
- One video costs more than the laptop home's 60 MiB. Package 3V reports the measured figure on the Intel chip
  before the owner picks Video.
- Revision 4, after the lead's decision on review 3: the video surface belongs to a program of its own, the player.
  GL, if it wins, is loaded in the player only, and only when the compositor draws on the Intel chip. The native
  home stays Cairo only in every style.

**Icons** (INPUTS-2)

- Icons sit on the same background-layer surface as the picture, so clicks and drags stay the home's. labwc's Root
  context is already off (package 329).
- Icons take keyboard focus only by a click, never by default.
- Revision 4: in the Video style the video's surface lies between the picture and the icons. So there the icons are
  on a bottom-layer surface of the native home's, with the same input rule and the same keyboard rule.

**Strip and reveal**

- **Timing:** the pointer rests 300 ms; the slide takes 150 ms.
- **Drawing:** the bar's surface keeps a fixed size and draws at an offset, with its input region on the visible
  part only. It is never resized per frame.
- **No reveal** while a button is held, during a Deskflow capture, or while the pointer is locked.
- **Deskflow:** the barrier edge wins. If the Mac is configured below the laptop, that output gets no strip on its
  bottom edge.

**Covering, as it feeds `screens`**

- wlr-foreign-toplevel gives states and outputs but no window geometry. So until the layouts and covering packages
  ship (COMPONENTS.md 4.3's labwc patch that reports geometry), an output is covered when a window on it is
  maximized or full-screen and not minimized. That is today's rule, applied per output.
- A full layout counts only once covering ships.
- A covered output's bar is `edge`. A part-screen window never changes the bar's state.
- `aresos.cover` and `aresos.black` never cover. They make the bar `none`.

**Scaling**

- The town and every look sprite scale by whole numbers, nearest neighbour. Any leftover is centred on the picture's
  own edge colour.
- A picture of his scales smoothly to cover the output, cropped centred. A video and a still are scaled the same
  way.
- Each output uses its own scale factor.

**Look**

- The bar is a new COMPONENTS.md piece, with the status icons (try-out item 9). `linux-desktop` writes its A, B and
  C, its marks and its look-B map rows there before package 4's brief.
- The frame package (B329) sets A's colours and button cells, which the bar reuses.
- The plain picture is the desktop's to draw in the look. This note assumes its design goes into COMPONENTS.md
  with the bar's, and the icons' cell, name line and frame with it.

**`rc.xml`** (to `linux-aresos` first)

- Since package 329 the image has a `<mouse>` section. It keeps labwc's defaults and makes the left, right and middle
  click on a bare desktop do nothing (`rc.xml:34-45`). The image has no `menu.xml`.
- The picture covers the desktop from package 3a on, so those clicks matter only when no picture is up.
- Nothing else in `rc.xml` for packages 3 to 5. The bar takes no keys, and Super stays 23c's.
- The recovery key's third action is package 6's, not the desktop's.

**Packages.** 3a, 3b1, 3b2, 3I, 3V, 4 and 5 are `linux-desktop`'s. Each gets its own brief from `linux-desktop` once
this note is reviewed. Package 3V also has a part of `linux-aresos`'s: the supervisor runs the player. Package 5
also tests the 1-pixel strip against B321's barrier in its harness.

---

## 13. Gates for the home style switch and the sleeping world

A gate is passed by a test, not by an argument. Until it passes, the package it blocks gets no brief. This note
decides what each gate rests on. The mechanism that passes it is the gate's own work.

| Package | Waits for |
|---|---|
| 1, 2, 3a, 4, 5, 6, 11 | no gate |
| 7, the home style switch | gate 2 |
| 3b1, 3I, 3V, 3b2 | no gate of their own; each needs package 7, so gate 2 through it |
| 12, the default flip | gate 2, through package 7 |
| 8, stills and the quiet start | no gate, as long as it adds no sleep, freeze, wake or new start |
| 9, the sleeping world | gates 1 and 3, and gate 2 through package 7 |

### Gate 1: a sleeping world survives every crash and every stop

**Blocks:** package 9. **Passed by:** the T364 study (hub with aresos), in a rig of package 318's kind and in the
supervisor's own tests. **Rests on:** section 9's decisions 1 and 3 to 7. **From:** review 2, point 1.

What must be true:

1. **Every step is on disk before it is taken.** The supervisor records the change before it asks the mod to
   pause, and closes the record only after the mod has acknowledged `resume`. `resume` can be sent twice without
   harm.
2. **A new supervisor finishes it or undoes it.** Killed at any step of going to sleep or of waking, the
   supervisor's replacement ends in one of three places: the world runs and is not paused; the world sleeps and is
   adopted as ASLEEP (a WAKING found at adoption finishes its wake and is resumed, or goes back to ASLEEP; it is never
   a place to end in); the world is closed and counted as saved. Never a paused world that nobody
   resumes. Never STARTING with `slow_start`, and never `unready` for a missing heartbeat (supervisor
   `:1855-1877`, `:2554-2566`).
3. **Nothing is frozen in view.** The freeze comes only after the compositor has confirmed that the window is
   minimized.
4. **Every stop ends without a thaw.** `stop`, `restart`, `logout`, a shutdown and world off, in ASLEEP and in
   WAKING: each ends within a stated time, loses nothing, and leaves no `killed` latch and no false `unsaved`
   latch. Its outcome passes the tests a stop and a logout must pass today, which accept only `exited` or `none`
   (supervisor `:3425`, `:3600`), and the fresh check for open windows before labwc ends (supervisor `:3434-3439`).
5. **A kill from outside is not a crash.** A sleeping world that the system or he kills is counted as saved: no
   failure count, no backoff restart, no latch, no window. An awake world that is killed keeps today's rule.
6. **"Saved" stays true for a reader.** A `save` answered from a sleeping world, and a backup that follows it,
   either hold the world asleep until the copy ends, or wait for the writer's exit as OS-BASE B6 requires
   (`docs/design/OS-BASE.md:358`). A wake during the copy must not be able to change the files.
7. **A sleeping world writes nothing.** With the pause held, the mod's write observer (package 46) sees no write
   after the sleep's save.
8. **With a part gone there is still a way back.** While the helper or the native home is away, a frozen window
   does not come on screen, also not through Alt+Tab, which lists the world
   (`os/config/usr/share/aresos/labwc/rc.xml:21`). The still stays or the world is woken, and he is told if it
   waits for memory.

How a test shows it:

- **Kill points.** In the rig, each step of going to sleep and of waking is a kill point for the supervisor.
  Twenty runs for each point. After the replacement settles, the test asserts one of row 2's three places and no
  latch.
- **Stops.** Each stop kind against ASLEEP and against WAKING: the time, the reply, and no latch at the next boot.
  A logout with no app window open ends labwc.
- **Kills.** SIGKILL to the frozen scope from outside: the outcome of row 5. On the image's kernel, that SIGKILL
  ends the process without a thaw.
- **Readers.** A backup started after `saved`, with a wake fired during the copy: the files do not change under it.
- **Parts gone.** The helper killed while the world sleeps, then Home picked in Alt+Tab: no frozen window appears on
  screen, not even for one frame the compositor maps.

### Gate 2: OFF holds, and a waiting start is one durable record

**Blocks:** package 7, and through it packages 12, 3b1, 3I, 3V and 3b2. Package 9 builds on it for OFF (`asleep`).
**Passed by:** `linux-aresos`, with a short design step for the supervisor and the step G2 of section 10. That step
needs packages 1 and 3a. **Rests on:** section 6's rule that only his request starts a world in OFF, and section
12's rule 2. **From:** review 2, point 2; row 8 came with revision 3.

"World off" below is the supervisor's word for a normal style, and "world on" for the Minecraft world (section 6).
The video's player is no world: starting or stopping it is no start in the sense of these rows.

What must be true:

1. **Only his request starts a world in OFF.** Not a timer. Not a restart deadline kept from before (supervisor
   `:1786-1812`). Not a wake signal. Not a new supervisor that reads the setting. Not Prism's own launch button.
2. **Two doors.** The decision is applied before Prism is spawned (supervisor `:1982-1995`) and again at the gate
   every JVM passes (supervisor `:2182-2236`).
3. **OFF survives a new supervisor, in the same kind.** OFF (`quit`) is kept for the session, as today's quit is
   (supervisor `:1779-1784`, `:1796-1812`).
4. **Off and on are all or nothing.** A crash between the stop's end and the setting's write, or between the
   setting's write and the start, is settled by the next supervisor: either the world is closed and the style is a
   normal one, or the style is the Minecraft world and the start goes through the doors. The design step fixes the
   order of the write and the request.
5. **A waiting start is one record.** His request that is not admitted is kept in the supervisor's durable state.
   It survives a new supervisor. It is tested again only on the sampler's schedule. It starts the world once. These
   end it: world off, `stop`, `logout`, a shutdown, the session's end. Nothing but his request creates it.
   `screens` shows it as `waits`.
6. **Admission fails closed.** A sample that cannot be read, or an old one, admits nothing. "Start anyway" is his
   act at that moment and is never stored.
7. **A latch still holds.** Turning the world on does not clear what only `retry` may clear. The design step also
   names the latches a start can make by itself before any launch (supervisor `:1828-1830`), and says what a normal
   style does with each.
8. **A normal style needs nothing of Minecraft's.** A supervisor that starts in OFF (`off`) reads no pin file, makes
   no Prism instance and asks no shutdown guard. With the pin file unreadable or the instance broken, it still starts
   the helper and the native home and stays up. The fault shows only when he asks for the world.

How a test shows it. The supervisor takes its runner and its clock from outside, so each row is a plain test:

- **Replacement.** In each kind of OFF: a new supervisor on the same files, and the clock moved past every old
  deadline. No Prism is spawned, and the kind is the same.
- **Doors.** A wrapper's `jvm_start` in each kind of OFF is refused, with a line that names the home style. So are
  `retry`, `restart` and every wake signal in OFF (`off`).
- **Crash points.** The two of row 4. Each ends in one of its two settled states.
- **The pending start.** It is made only by his request, survives a replacement, starts once on the first clear
  sample, and is gone after each event of row 5. An old or unreadable sample never admits it.
- **Without Minecraft.** With the pin file removed and no Prism folder: a supervisor in OFF (`off`) starts the helper
  and the native home and stays up. `world on` then answers with the reason and starts nothing. The supervisor
  starts the native home only from package 3a on, so this row needs 3a.
- **On a test image built with gate 2's step and its rig-only command enabled,** one pass in a VM (never the owner's
  laptop before package 7): world off through that command, a reboot, and neither Prism nor Java runs. Then `world on`
  starts the world.

### Gate 3: the world gives way first

**Blocks:** package 9, and with it anything that would thaw or start a world by itself. **Passed by:** the T364
study with `linux-aresos`, which owns the image's memory policy, measured on the image: first the VM, then the
laptop. **Rests on:** section 12's rules 2 and 3. **From:** review 2, point 3.

What must be true:

1. **Shown, not argued.** With his usual apps open and memory driven to full, a sleeping world is gone before any
   app's scope is killed, in every run. A case where the system can still pick an app first is named, with what it
   costs him.
2. **In the image's own terms.** The study reads from the image which cgroups systemd-oomd watches, and with which
   limits. It names the game's scope, the apps' scopes and the session's scopes as they are (section 3). Upstream
   defaults are no evidence.
3. **One measure on both sides.** The supervisor's trigger and the system's are compared in the measure the system
   uses.
4. **A schedule for every state,** the awake one too, and an answer for a spike between two samples. Whether an
   awake world is asked to save more often under pressure is the study's call.
5. **Admission is defined.** What is sampled, how fresh it must be, and the room a start needs, measured apart
   from the 1.4 GiB reading of a settled world. It fails closed.
6. **`oom_score_adj` is not counted** as an order for systemd-oomd.
7. **Latches stay apart.** A saved sleeping world that is given up is not a crash (gate 1, row 5). An awake world
   that is killed keeps `killed`, the clear minute and his `retry` (supervisor `:2408-2420`, `:2589-2601`).

How a test shows it:

- **Contention runs.** On the image, a memory load beside representative apps in `app.slice` scopes and a sleeping
  world. Twenty runs each of a slow fill, a fast spike and full swap. systemd's own results give the order in which
  scopes ended. It passes only when, in every run where pressure reaches the point of killing, the sleeping world is dropped and
  ends before any app scope. A run that kills nothing doesn't count towards the twenty.
- **Blind runs.** With the pressure file unreadable, nothing is thawed and nothing is started.
- **A pinned check** in the image's tests: the supervisor's limits stay below the system's, read from the image at
  build time.

Revision 1's numbers are a place to begin and no more: 10 % pressure to admit, 25 % for 15 s or 75 % of swap to
give way, 2.5 GiB free to start.
