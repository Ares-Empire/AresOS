# The laptop-screen home: Night street

**Draft, waiting for the owner's choice.** Design study of package 44 (2026-11-16, a Fable design agent; review
fixes 1 the same day, a Claude Opus agent; the day look and section 11 the same day, a Fable design agent). Nothing
here is built. It describes the direction the study recommends; the other two directions, the pictures and the
measurements are in [the study's report](../../reviews/44-laptop-home/PROGRESS.md). If he chooses another
direction, sections 1 to 3 change and sections 4 to 8 stay.

**Night or day is open.** Sections 1 and 2 describe the town at night, as the study first drew it. The owner asked
why night, when the world is never dark. Section 11 answers, shows the same town by day and recommends day. If he
chooses day, sections 1, 2.1, 2.4 and 2.5 take section 11's table and nothing else changes.

The owner (2026-11-15): "the laptop needs to get a proper "monitor connected" homescreen so its not boring and still
unique and functional. Probably most useful will be to have apps easily accessible via it or a companions room or
similar. ... it doesnt need to be like a picture of the town or smth but it should fit."

Pictures (test apps, generated logos):
[home](../../reviews/44-laptop-home/pictures/street-1-home.png),
[finding](../../reviews/44-laptop-home/pictures/street-2-finding.png),
[finding "pdf"](../../reviews/44-laptop-home/pictures/street-3-all-programs.png),
[an app opened](../../reviews/44-laptop-home/pictures/street-4-opened.png),
[day one](../../reviews/44-laptop-home/pictures/street-5-day-one.png),
[forty apps](../../reviews/44-laptop-home/pictures/street-6-forty-apps.png),
[where companions can stand](../../reviews/44-laptop-home/pictures/street-7-ledges.png),
[forty-five apps, one group of twenty](../../reviews/44-laptop-home/pictures/street-8-forty-five-apps.png),
[a far house slid into view](../../reviews/44-laptop-home/pictures/street-9-far-house.png),
[every logo in full colour](../../reviews/44-laptop-home/pictures/street-10-full-colour.png).
The same town by day (section 11):
[home](../../reviews/44-laptop-home/pictures/day-1-home.png),
[finding](../../reviews/44-laptop-home/pictures/day-2-finding.png),
[an app opened](../../reviews/44-laptop-home/pictures/day-4-opened.png),
[forty apps](../../reviews/44-laptop-home/pictures/day-6-forty-apps.png).
The clickable prototype is `reviews/44-laptop-home/prototypes/street/index.html`; `?look=day` after the address
shows it by day.

---

## 1. What he will see

He plugs the monitor in. The world moves onto it (package 23c). The laptop's own screen, dark until now, shows his
town from the side, at night.

Four streets lie one above the other: Internet, Games, Work & Media, System & Tools. Each has its colour as a line
along its road. On each street his apps stand as their block logos, the same ones as in the world, each with its
dark doorway and its doormat. Over every logo is its sign: the name in white, the short name in gold. In the middle
of each street, between its two front logos, hangs the group's name, as it hangs over the avenue in the world. A
house stands on the same side of its street as its logo stands of the avenue, and the nearer it is to home in the
world, the nearer it is to the middle.

The houses are slightly dimmed. The ones whose app is open are bright, with warm light in the doorway.

Under the town runs a thin line with one gold block in its middle: his home block. Below it is the hotbar with his
nine pinned apps. Top left the time and the date, top right the battery.

**Opening Notepad, three ways.**
1. **A click** on its house. A purple puff in the doorway, Notepad opens on the laptop screen, the house lights up.
2. **A hotbar key.** Notepad is the third pinned app: he presses 3.
3. **Typing.** He types `note`. Every other house goes dark, Notepad gets a gold frame, Enter.

**From inside the world.** While he plays, the game holds the pointer and the keyboard. He presses Esc (or E, or
T) to free the pointer, moves it down to the laptop screen and clicks a house, or clicks once and types. When he is
working in an app already, the pointer is free and he just moves it down.

**Finding one he forgot.** He types `pdf`. No house fits, so a small list over the typing line shows the programs
outside My apps that do: here a document viewer whose name doesn't say "pdf" but whose keywords do. Enter opens the
first.

**A big group.** System & Tools grows to twenty apps. Its street is now longer than the screen: it stands in the
middle like the others, and a small sign at each end says how many houses are out of sight there ("‹ 2", "2 ›"). He
types `tool19` and the street slides until that house is in view. Escape slides it back.

**Later.** He installs a program. In the world a new logo is built; on the laptop a new house stands at the same
place of its street. He removes one: its place stays free, in the world and on the laptop. Nothing else has moved.

He unplugs the monitor. The world is back on the laptop screen and the street is gone.

---

## 2. The decisions

### 2.1 The town from the side

| What | Decision |
|---|---|
| Streets | Four, top to bottom in the order of HUB.md 2.2: Internet (north), Games (east), Work & Media (west), System & Tools (south). |
| Where a house stands | Left or right of the street's middle, as its place in the world is left or right of the avenue (the place's `L` or `R`). The nearer its place to home, the nearer it stands to the middle (section 3). A free place stays a gap, as in the world. |
| The group's name | In the middle of the street, where the avenue would be: the name in the group's colour, under it the direction and the count ("north · 7"). |
| The road | A dark strip with the group's colour as its top line, paved from the farthest house on the left to the farthest on the right, gaps included. A group without apps has the middle piece only. |
| The house | The logo's 12 x 12 front as the mod built it, drawn as solid blocks with a top and a right side (3 blocks deep, as in the world). The doorway is columns 5 and 6, three high, black. The doormat is the road's top line under the door, in the group's bright colour. |
| The sign | Over the house: the name (white), under it the main short name with its slash (gold, JetBrains Mono). A long name takes a second line, as the world's signs do; past two lines it ends in "…". |
| Night | The background is the session's `#0d0d10` with a faint Mars-red glow bottom left and a steel-blue one top right (the crown language). Houses are slightly dimmed: 62 % brightness and 82 % saturation (or full colour, section 10 question 3). The day look instead: section 11. |
| Open apps | A house whose app has a window is at full brightness and its doorway is lit gold. Its hotbar slot has a gold mark. |
| Home | A one-pixel line under the lowest street with one gold block in its middle. It is the only gold thing that is not text or a selection. |

### 2.2 Getting to an app

- **Click.** The whole house is the target, sign included. The pointer's house is at full brightness.
- **Hotbar.** Nine slots under the home line, the same apps in the same order as the world's hotbar. A click opens;
  the keys 1 to 9 open while nothing is typed.
- **Typing.** Any letter starts it, as in the chat; a leading slash is allowed and ignored. It searches every
  program the helper lists, his apps and the others, as HUB.md 2.4's Apps screen does. Kinds of hits, best first:
  1. the exact short name;
  2. a short name that starts so;
  3. a name that starts so;
  4. a word of the name that starts so;
  5. a name that holds it;
  6. a word of the generic name that starts so;
  7. a keyword that starts so.

  The generic name and the keywords are the helper's `generic_name` and `keywords` (from the desktop entry), so
  `pdf` or `mail` finds the right program. Within one kind of hit, My apps come first, then by name.
  - Houses that do not fit drop to 13 % brightness. The best hit gets a gold frame and the line says "Enter opens
    Notepad".
  - Programs outside My apps are listed over the line, five at most, each with its generic name when the helper has
    one. No group is shown. The groups are the mod's, the helper does not give them, and the laptop does not work
    one out.
  - Backspace deletes, Escape clears.
- **Arrow keys** move the gold frame to the nearest house in that direction; Enter opens it. A house beyond the
  screen's edge slides its street into view (section 3).
- **Opening** asks the helper, as the world does. While the app starts, its doorway is purple and a few purple
  squares rise from it (0.6 s), the world's own sign for walking in. If the helper says it failed, the typing line
  shows the helper's words for five seconds ("Couldn't open Notepad: it failed to start").
- **From inside the world** (the world on the monitor has the focus): the game holds the pointer and the keyboard
  (HUB.md, package 40). He frees the pointer first: Esc (the game menu), E or T, or he is in an app already. Then he
  moves the pointer down and clicks a house, or clicks once and types. A reserved key would be the only way across
  without Esc (section 6; section 10 question 5).
- **Version 1 does not change anything.** No pinning, no moving, no removing from the laptop. Those stay in the
  world.

### 2.3 What else it shows

The time (large, JetBrains Mono), the date, the battery. Nothing else in version 1: no notifications, no volume, no
picture of the world. A thing is added only when he asks for it.

### 2.4 Motion

**At rest nothing moves, so nothing is drawn again.** Anything that moves makes the engine draw new pictures, up
to 60 a second, on a screen he is mostly not looking at. Section 4 has what that costs.
- No animation that runs without end. No drifting, no video, no blinking without end. The typing caret blinks a
  few times after each key and then stays.
- What he typed is cleared when the laptop home loses the keyboard (he clicks an app or the world).
- One star changes its brightness every four seconds, in one step (the night look only; the day look has no
  stars and no timer for them).
- The clock changes once a minute.
- A house changes when its app opens or closes.
- Everything else is an answer to him and ends within a second: the puff (0.6 s), a hover (0.15 s), a street
  sliding (0.3 s).

### 2.5 Fonts and colours

Space Grotesk for text and labels, JetBrains Mono for the time, counts and short names (both SIL Open Font License
1.1). Colours are the Ares-Crown window theme's: wall `#0d0d10`, ink `#f3f1ea`, quiet ink `#a6a39a` and `#6f6b62`,
gold `#cfa24f` and `#edca77`. The group colours are `AppGroup`'s: `#3AB3DA`, `#FF6257`, `#C774F2`, `#FED83D`.

---

## 3. The layout rules

All numbers are for a 1920 x 1080 screen. On another size the whole page is scaled.

| Name | Value | Meaning |
|---|---|---|
| `TOP` | 150 | where the first street's strip begins |
| `STREET` | 196 | height of one street's strip; its road is the lowest 16 |
| `GAP` | 200 | the free middle of a street, for the group's name |
| `EDGE` | 40 | free at the left and right edge |
| `CELL` | 7 to 10 | pixels a block; one value for the whole town |
| `PITCH` | 14.6 x `CELL` | from one house to the next |
| `DEPTH` | 0.9 x `CELL` | how far a house reaches back, drawn up and to the right |
| `FLOOR` | 948 | the home line |
| hotbar | top at 966, slots 64 x 64 | centred |

**Where a house stands comes from its place in the world, never from a count** (HUB.md 3.3). Places have holes: a
removed app keeps its place free, a place with something of his on it is skipped, and `/aresos app move` and `swap`
move apps between places (HUB.md 2.5). So:
- **Side:** the place's `L` or `R`.
- **Slot:** the place's rank among that side's places, nearest first. Row `r` has `r + 1` places a side, so
  `slot = r(r+1)/2 + k`: `N0L0` 0, `N1L0` 1, `N1L1` 2, `N2L0` 3, `N2L1` 4, `N2L2` 5, `N3L0` 6 …
- **Position:** a left slot `s` has its right edge at `960 - GAP/2 - s x PITCH`. A right slot `s` has its left edge at
  `960 + GAP/2 + s x PITCH`. Its foot is on the road's top.
- **A free place stays a gap**, as in the world. The road runs on under it. Nothing else moves when a place empties
  or fills. (The other way, that side closing up, was not taken: every removal would move the houses after it, and
  they would stand where they do not stand in the world.)
- **An app without a place yet** (the mod has not placed it) takes the next places after the farthest one its group
  uses, in HUB.md 3.3's order, until the mod gives it one.

**`CELL`:** `floor((960 - GAP/2 - EDGE) / (SLOTS x 14.6))`, kept between 7 and 10. `SLOTS` is the farthest slot
used on any side of any street, plus one. A house is 120 wide up to 5 slots a side (10 apps in a group without
gaps), 108 at 6, 96 at 7 and 84 at 8 (16 apps).

**Past 8 slots on a side, the street slides.** That is more than 16 apps in a group, or fewer with gaps. `CELL`
stays 7, and every other street stays as it is.
- **At rest** the street stands in the middle like the others.
- **End signs.** At each end that runs off the screen the street shows a small sign in its colour, with the number
  of houses out of sight there ("‹ 2", "2 ›"), over a fade to the wall.
- **The gold frame is always in view.** When the best hit of his typing, or the house the arrow keys chose, is out
  of view, its street slides as little as shows the whole house.
- **A click on an end sign** slides the street until its last house on that side is in view.
- **Back to the middle.** A street without the frame goes back to the middle, unless he slid it by hand. A slide by
  hand lasts until Escape, a click on the group's name, or the laptop home losing the keyboard.
- **Each slide takes 0.3 s.** Ledges and boxes for the companions slide with it (section 7).

**What fits:** every app is on the screen up to 16 in a group. In HUB.md's planning mix that is about 45 apps
(System & Tools grows fastest: 42 of the laptop's 61 programs are System & Tools, HUB.md 5). Past that, the nearest
16 of that group are on the screen and the rest are one click, typed name or arrow key away. There is no upper
limit.

**Checked in the prototype** (`tools/shots.sh check`, Night street's own check, on a 45-app town with
`test-web-1`, place `N0L0`, removed):
- every other house keeps its side and slot, and the houses are drawn where the layout says;
- `test-web-2` stays on the right and `test-web-3` on the left;
- `test-tool-19` (slot 9 on the left) is out of view at rest, comes into view when he types `tool19`, and goes
  back on Escape;
- the end signs say "‹ 2" and "2 ›".

The build carries these over as tests.

---

## 4. What it is built from

**The system's web engine in a window program of its own.**

| Part | What | Where |
|---|---|---|
| The window program | Python, GTK 4, WebKitGTK 6.0, `gtk4-layer-shell`. One layer surface, one web view, no network. Holds the connection to the app helper. | `/usr/libexec/aresos-laptop-home` |
| The page | Plain HTML, CSS and JavaScript modules, no build step. Draws the town. | `/usr/share/aresos/laptop-home/` |
| The fonts | Space Grotesk is in the image. JetBrains Mono is added. | `/usr/share/fonts/aresos/` |

Why a web engine: the companions run on a web runtime and move into a web page as they are (section 7). A native
drawing would be lighter but would mean rebuilding them.

**Rules for the window program.**
- **The layer library from Python.** `gtk4-layer-shell` must be loaded before `libwayland-client`, and its own
  notes give `LD_PRELOAD` for Python. Without it the layer surface silently does not happen. The supervisor starts
  the program with `LD_PRELOAD` set to the library. The program checks that the layer surface is supported, and
  uses the fallback of section 6 when it is not.
- **The page's own address scheme.** The page is served as `aresos-home:`, from the page's folder only. The scheme
  is registered as secure and as CORS-enabled (WebKit's security manager). JavaScript is served as
  `text/javascript`, CSS as `text/css` and JSON as `application/json`. Otherwise module imports and `fetch` fail.
  Loose files would not let the page load modules or fetch data either, and the companions' runtime needs both.
- Every other address is refused. The network session is ephemeral. No developer tools, no context menu, no
  downloads, no new windows.
- App pictures of programs outside My apps (the finder's list) are served as `aresos-home://icon/<app id>`, read
  only from the path the helper gave for that ID.
- **The secret stays out of the engine.** The program reads the view token (section 5) and then removes it, and
  `LD_PRELOAD`, from its own environment before it creates the web view. The engine's processes start from that
  environment and never inherit them. The page never sees the token either way.
- **It draws on the compositor's chip.** The laptop has two graphics chips. GTK must hand its pictures to the
  compositor on the chip the compositor draws with, or every frame is copied between the two (see "Motion" below).
  The program never gets the game's NVIDIA environment.
- It runs in a systemd scope of its own with `MemoryHigh=640M`.

**What the page gets** (`window.aresosHome`):

| Call or event | Meaning |
|---|---|
| `home()` | his apps as the mod published them: ID, name, short name, group, place, hotbar slot, the logo's cells and colours |
| `programs()` | every program the helper lists: ID, name, generic name and keywords as the helper gives them, whether it has a picture. No group. |
| `open(id)` | asks the helper to open it; resolves with the launch's state or the helper's failure words |
| `status()` | battery level and whether it charges |
| event `home` | the town changed: read `home()` again |
| event `programs` | the program list changed |
| event `running` | the IDs of the apps that have a window now |
| event `status` | the battery changed |
| event `helper` | the helper went away or came back (opening is off in between, section 5) |

The page never gets a command, a path, the socket, the view token or the launch nonce.

**Memory** (measured in the study, 40 test apps, WebKitGTK 2.54.1, PSS from `smaps_rollup`):
- **About 335 MiB in all at rest.** 127 MiB of it is working memory. 208 MiB is the program and library files it
  maps: the engine, GTK and the graphics driver's libraries. Shared memory is under 1 MiB.
- Under 2 % of one processor core at rest.
- Memory the graphics chip holds for it does not show in these numbers.
- With the compositor and GTK on the Intel chip, as in his session (OS-BASE: Intel drives the session, NVIDIA
  renders Minecraft), it is about 265 MiB: 123 MiB working memory and 141 MiB files, because the NVIDIA
  driver's libraries are not loaded.
- The bare engine is about 255 MiB of it.

**Motion** (measured, review fix 7): one figure the size of a companion (80 x 80 pixels) walks along a street. It is
drawn on a see-through canvas over the whole town that is cleared and drawn again every frame, as the companions'
runtime draws, at 60 frames a second, for a minute.

| Set-up | Processor | Memory (PSS) |
|---|---|---|
| Compositor and GTK on the Intel chip, at rest | 0.5 % | 264 MiB |
| Compositor and GTK on the Intel chip, the figure walking | **22 %** (window program 7, page 15) | 268 MiB |
| Compositor and GTK on the NVIDIA chip (GTK's OpenGL renderer), at rest | 0.6 % | 289 MiB |
| the same, the figure walking | 26 % (window program 13, page 13) | 296 MiB |
| Compositor on NVIDIA, GTK's default renderer on Intel, the figure walking | **248 %** (window program 240) | 347 MiB |

- **On one chip, a moving companion costs about a fifth of one core** while it moves, and a few MiB.
- **On two chips it costs two and a half cores.** In the study's headless compositor GTK's default renderer (Vulkan,
  device 0, the Intel chip) drew while the compositor drew on NVIDIA. Every frame was then copied from one chip to
  the other by the processor. The study's first measurement, ten twinkling stars at 220 %, had the same cause.
- So the window program must draw on the compositor's chip. The laptop trial (section 9) checks it in his session.
  If they differ, the program sets GTK's renderer or device so they match.
- The cost is per frame, not per figure: the runtime redraws one canvas. Fewer frames cost less: 30 a second cost
  about half (measured on two chips: 145 % against 248 %).

---

## 5. The interface additions (`aresos-shell/1.2`)

Everything in 1.1 stays. A 1.2 helper offers the capabilities `views`, `home_state` and `apps_running`. A mod or a
helper that does not know them works as today.

- **A view.** `hello` may carry `"role": "view"` and `"view": "<name>"` (`[a-z0-9-]{1,32}`, here `laptop-home`).
  Without `role`, or with `"role": "desktop"`, hello means what it means today.
  - **A view proves who it is with a token of its own, not the nonce.**
    - The supervisor makes one view token per session (`ARESOS_VIEW_TOKEN`, as random as the nonce). It keeps the
      token beside the instance in its runtime file, so a restarted supervisor keeps it too.
    - It gives the token to every helper it starts and to the laptop home. The game never gets it.
    - A view's hello carries `instance` and `token`, never the nonce.
    - The helper takes the role from what the hello holds: the nonce makes a desktop, the view token a view. A
      hello whose `role` does not match what it holds is refused (`not_authorized`).
    - So a view can never displace the game, and the game's nonce never leaves the game and the helper.
    - The supervisor and the helper both add `ARESOS_VIEW_TOKEN` to their `PRIVATE_ENVIRONMENT`, so nothing they
      start inherits it.
  - **The token lasts the whole session.** Each game start gives the game and the helper a new nonce
    (`ensure_helper(restart=True)` in `aresos-desktop`), not a new view token.
    - The helper restarts, and the view's connection drops.
    - The window program connects again with the same token: after 0.5, 1 and 2 seconds, then every 2 seconds.
      These reconnects are not restarts of the program (section 6).
    - In between it shows the last town it had, with the open apps lit as they were. Opening is switched off, and
      the typing line says "Opening is back in a moment".
    - When the helper answers, the program reads `get_home`, `list_apps` and `apps_running` again.
  - **PLAN-GAP:** making the token, handing it over and starting the laptop home are the supervisor's, package 23c's
    side (`linux-aresos`).
  - **A view never becomes the desktop.** It does not close the desktop's connection, and a desktop's hello does not
    close a view's. A second view with the same name closes the first. At most four views.
  - **A view's hello leaves the desktop's state alone.** It does not set the window rules (`window_minor`), does not
    cancel returns (`cancel_returns()`), does not set `windows_pending`, and writes nothing to the supervisor's
    status pipe (`desktop_connected` is the game's).
  - A view may send `list_apps`, `open_app` and `get_home`. `world_ready`, `heartbeat` and `publish_home` are
    refused (`invalid_state`). A view never counts for readiness.
  - **Launches are kept per client.**
    - Journal entries are keyed by client (`desktop` or `view:<name>`) and request ID. B1's duplicate rule holds
      within one client, so a view's ID can never return one of the game's launches.
    - The desktop keeps its 256 entries (`JOURNAL_LIMIT`). Each view gets 32 of its own, so a busy view can never
      make the world's opens fail with `journal_full`.
    - A view's request IDs carry a random part for each connection, as the game's do (`ShellClient`: prefix,
      session, counter).
  - **Each launch remembers who asked**, in the journal, so it survives a helper restart. `app_state` goes to that
    client only, or to a view that comes back with the same name.
  - A view gets `apps_changed`, `home_changed` and `apps_running`, and `app_state` for its own launches. It never
    gets `shell_focus` or `shell_covered`.
  - A launch a view asked for is not "the desktop's": when its app closes, the helper does not give the focus to
    the world.
- **`publish_home`** (desktop to helper). The mod sends it after hello and after every change of My apps, a short
  name, a place, a hotbar slot or a logo:

  ```json
  {"op": "publish_home", "revision": "17", "part": 0, "last": true,
   "palette": {"a": "#e9ecec", "b": "#2389c6", "k": "#080a0f"},
   "apps": [{"id": "notepad", "short": "notepad", "group": "system_tools", "place": "S0L0", "slot": 2,
             "cells": "............ (144 characters)"}]}
  ```

  - `cells` is the logo as built, row by row from the top, one character a cell: `.` for no block, otherwise a key
    of `palette`. `palette` gives each block's colour (numbers the mod already holds). `slot` is 0 to 8 for a pinned
    app and missing otherwise. `place` is missing while the app has none. An app without a readable picture sends
    its plain front.
  - Several messages with `part` counting up carry a town that does not fit in 64 KiB; the helper takes the home
    over when the one with `"last": true` arrives.
  - The helper checks shapes and bounds only (at most 200 apps, strings as in 1.1) and keeps the last complete home
    in memory. It does not read meaning into it.
  - An app whose ID the helper no longer lists is dropped from the home, and the helper logs it; the rest of the
    town stands. An uninstall during a publish cannot empty the laptop screen.
- **`get_home`** (view to helper). The last complete home, paged like `list_apps`. Before the mod has published:
  `"revision": null` and no apps.
- **`home_changed`** (to views): `{"event": "home_changed", "revision": "17"}` when a new complete home arrived.
- **`apps_running`** (to views): `{"event": "apps_running", "apps": ["notepad", "terminal"]}` once after hello and
  at each change: the apps that have at least one window, from the helper's window tracking.
- **Never sent to a view:** a command, arguments, an environment, a path other than `icon`.
- **Example messages** go beside 1.1's (`mod/src/test/resources/shell-1.2/`), read by the tests of both sides.

Why the mod publishes instead of the page reading the mod's file: one description of the town for every client, no
second parser of `apps.json`, and one logo converter. The laptop draws the cells the mod worked out, so the two
screens cannot disagree.

**While the game is not there** (it restarts, or has not published yet): the window program keeps the last home it
got in a file of its own state folder and shows that, with open apps still lit from `apps_running`. Opening works
whenever the helper answers, because the view token does not change with the game. While the helper itself
restarts (with each new game start), opening is off for those seconds, as above.

---

## 6. Living in the session

- **A layer surface, not a window.** The window program puts its surface on the **background layer** of the
  laptop's own screen (the output whose name starts with `eDP`), anchored to all four edges, with keyboard mode "on
  demand".
  - It is below every app window by definition, and above nothing but the plain background.
  - It is not in Alt+Tab, has no title bar, cannot be closed, minimized or moved.
  - The helper's window tracking never sees it. It cannot count as covering the world, and "activating a covered
    world minimizes what covers it" (HUB.md, package 40) cannot touch it.
  - `rc.xml` needs no new rule.
  - A click gives it the keyboard; a click on an app window takes it away.
- **Fallback without `gtk4-layer-shell`:** a normal window `aresos.laptop-home`.
  - The program puts itself full-screen on the laptop's own screen: the monitor whose connector starts with `eDP`
    (GTK's `fullscreen_on_monitor`). A fixed `rc.xml` cannot do that with `MoveToOutput`, because the output's
    name (`eDP-1` or `eDP-2`) differs between machines.
  - A rule beside the world's: `serverDecoration="no"`, `skipTaskbar="yes"`, `skipWindowSwitcher="yes"`,
    `ToggleAlwaysOnBottom`.
  - The helper must then leave that app-id out of covering, of the return of focus and of the list of unknown
    windows, as it does for `aresos.cover`, and the window program must refuse to close.
- **From the world to the laptop home.** While the world on the monitor has the focus, the game holds the pointer
  and the keyboard (package 40: it lets go of the mouse only while an app is in front). So from inside the world
  he presses Esc (or E, or T), moves the pointer down to the laptop screen and clicks. From an app the pointer is
  free already.
  - **With a reserved key** (if he says yes, section 10 question 5; untried):
    - A labwc keybind (Super pressed and released alone) runs a small command that tells the window program.
    - The program shows its typing line on the laptop screen's top layer, with the keyboard (`exclusive`), until
      Enter or Escape. Then the keyboard goes back.
    - The world loses the keyboard meanwhile. The game must treat that as it treats an app in front: no pause
      menu, the mouse let go.
    - Part of the laptop trial.
- **Start.** The desktop supervisor (`/usr/libexec/aresos-desktop`) starts it when package 23c's rule says the world
  is on the monitor and an `eDP` output is on: after the world has moved, in its own scope, with the helper's
  socket, the instance and the view token (section 5), and `LD_PRELOAD` for the layer library (section 4). The
  start-up cover (23b) lies over every screen until the world is ready; the laptop home starts under it.
- **Stop.** When the monitor goes, or the laptop's screen is switched off (lid closed), the supervisor stops it
  (SIGTERM), before the world moves back.
- **It is never needed.** It is no part of readiness.
  - If the program ends by itself it is started again after 2, 10 and 30 seconds, then no more in this session:
    the laptop screen is then the plain background of today.
  - Losing the helper is not an end: the program stays and connects again (section 5). So game restarts never use
    up its restarts.
- **Apps** open on the screen the pointer is on (23c), so an app opened from the laptop home opens over it.

---

## 7. The companions later

The owner's plan: "the alternative laptop homescreen gets like a room or a city custom made where companions can
walk around in and do activities with a menu for opening apps".

The town is that city. What their runtime needs from a host (`~/companions/runtime/README.md`) is already here:

| The runtime asks for | The laptop home gives |
|---|---|
| a canvas it may draw on | a see-through canvas over the town, under the typing line and the hotbar |
| a world: floor, ledges, boxes | the home line as the floor; each street and each roof as a ledge with its free height; each house as a box (the prototype's `laptopHome.world.snapshot()`). A street that slides moves its ledges and boxes with it; the runtime reads a snapshot every frame, so companions standing there ride along. |
| input | the page's own pointer |
| storage | a small file kept by the window program, given to the page at its start |
| its files as modules over an address | the `aresos-home:` scheme (section 4) |

The menu for opening apps stays what it is: houses, hotbar, typing.

**What their motion costs on this engine** (section 4, "Motion"): about a fifth of one processor core while they
move at 60 frames a second, on one graphics chip. That is affordable for a screen beside the world. It is still
far from the near-zero of the town at rest, so the companions version needs a budget of its own:
- **Fewer frames.** The runtime takes its clock from the host, so the host can give it 30 frames a second or fewer.
- **No frames while nobody moves.**
- **None at all** while the laptop screen is off or an app covers it whole.

The two-chip trap (section 4) would make it two and a half cores. It is checked before anything moves.

Left to the companions package: how much room they get above the roofs (60 pixels under the next street at `CELL`
10; a street less or smaller houses would give more), what they do in the town, their memory, and that budget.

---

## 8. What I rejected and why

- **Map table** (the town from above, to scale; prototype `map/`). The most literal view of the same home. But a
  true map is a cross on a wide, low screen: logos are 84 pixels at 24 apps and 72 at 40, names no longer fit under
  them, and half the screen stays empty. Companions are drawn from the side and cannot walk a map. It can come back
  as a second look.
- **Console** (four columns of names; prototype `console/`). The fastest to read, and a launcher list, which this
  screen should not be.
- **A room under the town** (a cellar under the home block, logos on stone shelves). A good story for a screen that
  sits below the monitor, but the logos have no reason to stand in a cellar, and stone walls would need textures
  that look like the game's.
- **All four avenues as one panorama**, rows getting smaller with distance. The far rows become too small to click
  while space stays free elsewhere.
- **A native GTK drawing instead of a web page.** Lighter (an estimate: 50 to 80 MiB), but the companions would be
  rebuilt for it.
- **A browser in app mode.** Heavier than the bare engine, and it is his browser with his profile.
- **The page reading the mod's `apps.json`.** A second parser of a file that is the mod's own, and the logos would
  be converted twice.
- **Stars that twinkle, clouds that drift, a live view of the world.** Anything that moves without end makes the
  engine draw up to 60 pictures a second, a fifth of a core or more (section 4), on a screen he is mostly not
  looking at.
- **For a group past 16: smaller houses** (`CELL` 5, 22 apps a group, names under the pointer only). The names no
  longer fit, which is Map table's weakness again.
- **For a group past 16: a "+N" sign that opens the typing line** filtered to that group. The houses past 16 would
  never be seen. Sliding the street keeps every house at the town's size and every name readable, with no upper
  limit.

---

## 9. Build order

1. **`aresos-shell/1.2` in the helper:** views with the view token, `get_home`, `home_changed`, `apps_running`, the
   example files. Tests:
   - a view never displaces the desktop and never counts for readiness;
   - a hello with the view token is a view whatever its `role` says, and a mismatch is refused;
   - a view's hello leaves the window rules, the returns and the status pipe alone;
   - a busy view cannot fill the desktop's journal;
   - a view's request ID never returns a launch of the game's;
   - `app_state` reaches only the client that asked;
   - an unknown ID in `publish_home` drops that app only.
2. **The mod publishes its home** (`publish_home`) after hello and on every change.
3. **The window program and the page**, against a stand-in helper.
   - The town from section 3 (houses from places, gaps, the sliding street), the finder with generic names and
     keywords, the hotbar, opening, the lit houses, reconnecting with opening off in between.
   - Tests carried over from the study's checks (`tools/shots.sh check`, including Night street's own check).
   - Pictures from a headless compositor, as the study's tool takes them.
   - Night and day (section 11), if both are kept: the pictures and the checks for each look, and a check that at
     rest no animation runs and nothing in the page changes but the clock (and, at night, the one star).
   - The layer library through `LD_PRELOAD`, the `aresos-home:` scheme registered as secure and CORS-enabled with
     the right MIME types, the token and `LD_PRELOAD` removed from the environment before the web view starts.
   - The image gets `gtk4-layer-shell` and JetBrains Mono, and a check that WebKitGTK 6.0 and its Python binding are
     there.
4. **The supervisor makes the view token and starts and stops the laptop home** with package 23c's screens, in its
   scope, with the restart rule, and keeps the token out of what it starts (`PRIVATE_ENVIRONMENT`). This is package
   23c's side (`linux-aresos`, the PLAN-GAP of section 5).
5. **The laptop trial** with the monitor:
   - the keyboard on a click, Alt+Tab, an app maximized over it, plugging and unplugging;
   - the way from the world (Esc, and the reserved key if he chose it);
   - a game restart while the laptop home runs;
   - which graphics chip GTK and labwc draw on, and the processor cost of motion;
   - the memory in the real session.

Steps 1 and 2 are data and rules; step 3 is how a screen looks.

---

## 10. For the owner

These are the report's JUDGMENT-CALLs 1 to 6, in the same order, each with the study's recommendation.

1. **Which direction, and by night or by day?**
   - **The direction:** the street (his town from the side), Map table or Console. *Recommended: the street.* It
     shows his whole town with names, and the companions can move into it.
   - **The street's light:** night or day. Compare
     [night](../../reviews/44-laptop-home/pictures/street-1-home.png) with
     [day](../../reviews/44-laptop-home/pictures/day-1-home.png), and the forty-app town
     [at night](../../reviews/44-laptop-home/pictures/street-6-forty-apps.png) with
     [by day](../../reviews/44-laptop-home/pictures/day-6-forty-apps.png). *Recommended: day.* His world is always
     at noon, so by day both screens show one place. Night is calmer and shows what is open a little more strongly.
     Section 11 has the reasons and what each look costs.
2. **One look, or a choice of looks?** *Recommended: one look first, the one he picks in question 1.* Night and day
   are one page with two sets of colours (section 11), so the other one stays ready; a way to choose can follow
   once he has lived with the first. Map table would be a second folder of web files.
3. **Slightly dimmed houses, or every logo in full colour?** Compare
   [street-1](../../reviews/44-laptop-home/pictures/street-1-home.png) (slightly dimmed: open apps are brighter and
   their doors lit) with [street-10](../../reviews/44-laptop-home/pictures/street-10-full-colour.png) (full colour:
   only the door light shows what is open). *Recommended: slightly dimmed*, so what is running shows at a glance and
   the screen stays calm beside the world. It is one number to change. By day the same question stands: there
   "dimmed" is paler instead of darker (section 11).
4. **Only the time, the date and the battery besides the apps?** *Recommended: yes for version 1.* Notifications,
   volume or a view into the world can each be added when he asks.
5. **A reserved key (Super) that jumps to the laptop home's typing line** from anywhere, the world included? It is
   the only way from inside the world to the laptop without Esc (section 6), and it makes the laptop home the
   launcher of the whole session while the monitor is in. *Recommended: yes.* A reserved key changes how AresOS
   feels, so it is his call.
6. **Pins change in the world only** in version 1? The laptop shows the hotbar and opens from it but does not
   re-order it. *Recommended: yes.*

---

## 11. Day or night

The owner (2026-11-16), after seeing Night street: "why was night chosen, is it the best theme? Because the
superflat world isn't dark so do you think it fits as a homescreen? However, generally the app menu makes sense and
so does the search menu easy access. The apps don't necessarily have to be Minecraft houses but dimmed and light up
when used makes sense."

So the same town was drawn by day. The pictures, each beside its night twin:

| | Night | Day |
|---|---|---|
| Home, two apps open | [street-1](../../reviews/44-laptop-home/pictures/street-1-home.png) | [day-1](../../reviews/44-laptop-home/pictures/day-1-home.png) |
| He typed `tool` | [street-2](../../reviews/44-laptop-home/pictures/street-2-finding.png) | [day-2](../../reviews/44-laptop-home/pictures/day-2-finding.png) |
| An app opened | [street-4](../../reviews/44-laptop-home/pictures/street-4-opened.png) | [day-4](../../reviews/44-laptop-home/pictures/day-4-opened.png) |
| Forty apps | [street-6](../../reviews/44-laptop-home/pictures/street-6-forty-apps.png) | [day-6](../../reviews/44-laptop-home/pictures/day-6-forty-apps.png) |

It is one prototype: `?look=day` after the address shows the day, without it the night.

### 11.1 Why night was chosen first

The study's reasons, from its report:
- **Calm.** "A dark screen beside the world, and nothing on it moves unless he does something."
- **The house style.** The town "drawn in the crown language: near-black, gold only for the home block, the short
  names and what is selected". It carries on the laptop's dark background and the dark app windows.
- **"Lit means open" is a night idea.** A light in a doorway needs the dark around it.
- **Not a copy of the game.** The study wanted a drawing of the town, not a picture of the game.

What the study did not do:
- It never drew the town by day, and it never weighed night against day. Section 8 lists ten rejected ideas; a day
  look is not among them.
- Its report says the world shows the town "from inside at noon" and the laptop "from the side at night", and
  counts that as fitting. It did not ask whether two times of day on two screens feel like one place.

His question is fair. HUB.md 1 says of his world: "it never gets dark".

### 11.2 The world's time

Checked in the mod (`FlatHome.java`): **the flat home is always at noon.**
- `applyRules` switches the day cycle and the weather cycle off (`ADVANCE_TIME`, `ADVANCE_WEATHER`).
- `initialize` sets the clock to noon (6000) and the weather to clear once, when the world is made, and never
  again, "so a change he makes later is kept".
- HUB.md 2.3: "There is no night in version 1."

So there is no world time to follow today. Following the world means day, always.

If he ever switches the day cycle on, the laptop can follow it:
- The mod adds the world's time of day to `publish_home` (section 5). It is not sent today.
- The page changes its look in one step at dusk and at dawn. That costs what a change of the clock's minute costs.

Not needed in version 1.

### 11.3 What the day look changes

**The town is the same.** Every number of section 3, the hotbar, the typing line, the keys, the list of other
programs and the windows are unchanged. `tools/shots.sh check` passes on the day look as on the night (10 of 10,
and Night street's own 9 of 9). The ten night pictures did not change by a pixel when the day was added.

**No game texture is used.** The sky, the grass and the road are flat colours. The logos are drawn as before.

| What | Night | Day |
|---|---|---|
| Behind the town | The session's `#0d0d10`, two faint glows, 90 stars. | The world's noon: a clear sky, `#6f9df0` at the top to `#aecbf8` at the horizon, and flat grass below it, `#668845` to `#537236`. The horizon lies 292 pixels down, behind the first street, so that street's logos stand against the sky as they do in the world. No sun (at noon it is overhead) and no clouds. |
| The road | A dark strip with the group's colour as its top line. | Dark paving (`#2b2832`) with the group's colour as a line down its middle, as in the world. The doormat reaches from the door to that line. |
| The names | Bare text. | On dark plates, as in the world (`HubLayout.NAME_BACKGROUND`). White and gold cannot be read on sky or grass without them. The group's name has its plate too. |
| A house whose app is not open | Darker: 62 % brightness, 82 % saturation. | Sun-bleached: 45 % saturation, 80 % contrast, 93 % brightness, and its name plate at half strength. Nothing can be made brighter than daylight, so the others step back by losing colour. |
| A house whose app is open | Full brightness, and its doorway lit gold with a glow. | Full colour. The door is gold in a dark frame, a gold mat lies across the whole road, and the sign is solid with a gold line under it (the hotbar's mark). A glow does not show in sunlight; gold on the dark paving does. |
| While he types | The others drop to 13 %. | The others drop to 16 % and fade into the sky and the grass. |
| The gold frame | 2 pixels of gold. | 3 pixels of gold with a dark outline, so it holds on sky and on grass. |
| Time, date, battery, hint, hotbar numbers | Ink on the dark wall. | White with a hard dark shadow, as the game writes over its world. |
| The typing line | A dark bar while he types. | A dark bar at rest too, as the chat's line. |
| Home | A line with one gold block. | The dark stone pad with its gold block. |
| The hotbar, the list of other programs, app windows | Dark, Ares-Crown. | The same. |
| The ends of a street past 16 | Fade into the wall. | Fade into the sky and the grass. |
| At rest | One star changes every four seconds; the clock once a minute. | The clock once a minute, nothing else. |

**Another form for the apps.** He said the apps need not be houses. I looked for a form that reads clearly better
by day and did not find one, so there is no picture of one:
- The laptop gets each logo as the mod built it, doorway included (`cells`, section 5). A flat tile would be that
  same front without its thin top and side. By day those few pixels of light top and dark side help: they keep a
  pale logo apart from a pale sky.
- The doorway is where "open" shows, at night and by day. Without it that mark needs a new place.
- A tile without the doorway would need the program's own icon in place of the block logo. Then the laptop no
  longer shows the logos of his world, and the screen is a grid of icons: close to the launcher list the Console
  direction was rejected for (section 8).
- What does change by day: with sky and grass around them they read less as houses in a street and more as his
  logos standing in the world, which is what they are.

### 11.4 Recommendation: day

What the pictures show, side by side:
- **Day is the same place as the monitor.** Sky, grass, dark roads with the coloured line, names on plates: the
  laptop shows the world from a step back. At night it is his town in a light his world never has. He saw that at
  first sight, and "it should fit" was his first wish for this screen.
- **Both show what is open.** In day-1 and day-6 the two open apps are the two in full colour. Night shows it a
  little more strongly, because the lit door is the only light on a dark screen. By day a white, grey or black logo
  has little colour to lose, so for those the gold door and the sign carry it alone.
- **Night is calmer.** It is a dark screen with small lights. Day is a bright screen with a small dark plate over
  every logo (forty of them in day-6). Beside a monitor that shows a noon world that is no more light than the
  monitor gives. In a dark room it is a second bright screen.
- **Day pales his logos until they are open; night darkens them.** They stay recognisable either way (day-6).
- **A window stands out better by day** (day-4): the dark Ares-Crown window lies on sky and grass. At night it is
  dark on dark.
- **Finding works the same** (day-2).

**I recommend day.** The fit with the world is what night cannot give. What day loses, some calm and a slightly
weaker sign for "open", is small in the pictures.

**Night stays as the second look.** Both are one page: the day is one block of colours and about thirty rules on
top of the night's. The build keeps both and takes its pictures and runs its checks for both; which one shows is
one setting. If he later lets his world have a night, that setting can follow the world (11.2).

**Not recommended: following the real clock** (day by day, night in the evening). The world on the monitor is at
noon at every hour, so each evening the two screens would disagree again.

If he prefers night after seeing both, nothing is lost: it is the look sections 1 and 2 describe.

### 11.5 What it costs

**Section 2.4's rule holds: at rest nothing moves.**
- The day look adds no animation and no timer. Sky and grass are one still background, the plates and the road
  line are still, and there are no clouds and no sun.
- It takes one thing away: by day the 90 stars and their timer are not made at all. Only the clock changes.

**Measured** (`tools/shots.sh measure`, the 40-app town with two apps open, at rest for 100 seconds, in the same
headless compositor as section 4's first numbers; other builders' programs were running on the laptop meanwhile):

| Look | Processor at rest | of that the page's own process | Working memory |
|---|---|---|---|
| Night | 1.4 % of one core | 0.1 % | 128 to 136 MiB |
| Day | 0.3 % (two runs: 0.33 and 0.35) | under 0.1 % | 128 MiB |

- **Day costs a little less than night at rest.** Cut into 10-second slices, the window program used 1 to 2 % in
  every slice at night and 0.1 to 0.6 % by day. At night each change of a star is a new picture on the screen; by
  day nothing changes between two minutes of the clock.
- **Nothing redraws by day.** A check with a fixed clock watched the day page for 13 seconds: no animation was
  running, and nothing in the page changed. On the night page the same check saw three changes, the stars.
- **Working memory is no higher:** 128 MiB by day, 128 to 136 MiB at night. That is the part that is the page's
  own.
- **Memory in all (PSS)** was 255 to 322 MiB over five day runs and 307 to 342 MiB over four night runs. The
  difference is all in the share of library files (127 to 206 MiB), and that share also moved between runs of the
  same look. I do not count it as a saving, and I did not find out what moves it.
- **One thing seen and not explained.** In two shorter day runs (30 and 60 seconds) the page's process used about
  0.7 seconds of processor time that the other runs did not show. Both 100-second day runs were cut into 10-second
  slices to look for it: every slice was between 0.0 and 0.2 %. So it is not a steady cost, but I do not know what
  it was.

The laptop trial (section 9) measures the look he chose in his own session, as it does for the night.
