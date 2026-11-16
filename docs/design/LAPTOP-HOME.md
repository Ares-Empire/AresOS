# The laptop-screen home: Night street

**Draft, waiting for the owner's choice.** Design study of package 44 (2026-11-16, a Fable design agent). Nothing
here is built. It describes the direction the study recommends; the other two directions, the pictures and the
measurements are in [the study's report](../../reviews/44-laptop-home/PROGRESS.md). If he chooses another direction,
sections 1 to 3 change and sections 4 to 8 stay.

The owner (2026-11-15): "the laptop needs to get a proper "monitor connected" homescreen so its not boring and still
unique and functional. Probably most useful will be to have apps easily accessible via it or a companions room or
similar. ... it doesnt need to be like a picture of the town or smth but it should fit."

Pictures (test apps, generated logos):
[home](../../reviews/44-laptop-home/pictures/street-1-home.png),
[finding](../../reviews/44-laptop-home/pictures/street-2-finding.png),
[an app opened](../../reviews/44-laptop-home/pictures/street-4-opened.png),
[day one](../../reviews/44-laptop-home/pictures/street-5-day-one.png),
[forty apps](../../reviews/44-laptop-home/pictures/street-6-forty-apps.png),
[where companions can stand](../../reviews/44-laptop-home/pictures/street-7-ledges.png).
The clickable prototype is `reviews/44-laptop-home/prototypes/street/index.html`.

---

## 1. What he will see

He plugs the monitor in. The world moves onto it (package 23c). The laptop's own screen, dark until now, shows his
town from the side, at night.

Four streets lie one above the other: Internet, Games, Work & Media, System & Tools. Each has its colour as a line
along its road. On each street his apps stand as their block logos, the same ones as in the world, each with its
dark doorway and its doormat. Over every logo is its sign: the name in white, the short name in gold. In the middle
of each street, between its two front logos, hangs the group's name, as it hangs over the avenue in the world.

The houses are a little dark. The ones whose app is open are bright, with warm light in the doorway.

Under the town runs a thin line with one gold block in its middle: his home block. Below it is the hotbar with his
nine pinned apps. Top left the time and the date, top right the battery.

**Opening Notepad, three ways.**
1. **A click** on its house. A purple puff in the doorway, Notepad opens on the laptop screen, the house lights up.
2. **A hotbar key.** Notepad is the third pinned app: he presses 3.
3. **Typing.** He types `note`. Every other house goes dark, Notepad gets a gold frame, Enter.

**Finding one he forgot.** He types `pdf`. No house fits, so a small list over the typing line shows the programs
outside My apps that do. Enter opens the first.

**Later.** He installs a program. In the world a new logo is built; on the laptop a new house stands at the end of
its street. Nothing else has moved.

He unplugs the monitor. The world is back on the laptop screen and the street is gone.

---

## 2. The decisions

### 2.1 The town from the side

| What | Decision |
|---|---|
| Streets | Four, top to bottom in the order of HUB.md 2.2: Internet (north), Games (east), Work & Media (west), System & Tools (south). |
| Where a house stands | Left and right of the street's middle, nearest first: left, right, left, right. This is the order of the world's places (HUB.md 3.3) laid out in one line: an app's first place in the world is its first place here. |
| The group's name | In the middle of the street, where the avenue would be: the name in the group's colour, under it the direction and the count ("north · 7"). |
| The road | A dark strip with the group's colour as its top line, paved from the leftmost to the rightmost house. A group without apps has the middle piece only. |
| The house | The logo's 12 x 12 front as the mod built it, drawn as solid blocks with a top and a right side (3 blocks deep, as in the world). The doorway is columns 5 and 6, three high, black. The doormat is the road's top line under the door, in the group's bright colour. |
| The sign | Over the house: the name (white), under it the main short name with its slash (gold, JetBrains Mono). |
| Night | The background is the session's `#0d0d10` with a faint Mars-red glow bottom left and a steel-blue one top right (the crown language). Houses are drawn at 62 % brightness. |
| Open apps | A house whose app has a window is at full brightness and its doorway is lit gold. Its hotbar slot has a gold mark. |
| Home | A one-pixel line under the lowest street with one gold block in its middle. It is the only gold thing that is not text or a selection. |

### 2.2 Getting to an app

- **Click.** The whole house is the target, sign included. The pointer's house is at full brightness.
- **Hotbar.** Nine slots under the home line, the same apps in the same order as the world's hotbar. A click opens;
  the keys 1 to 9 open while nothing is typed.
- **Typing.** Any letter starts it, as in the chat; a leading slash is allowed and ignored. Order of hits: the exact
  short name, a short name that starts so, a name that starts so, a word of the name that starts so, a name that
  holds it; My apps before other programs. Houses that do not fit drop to 13 % brightness, the best hit gets a gold
  frame and the line says "Enter opens Notepad". Programs outside My apps are listed over the line, five at most,
  with their group. Backspace deletes, Escape clears.
- **Arrow keys** move the gold frame to the nearest house in that direction; Enter opens it.
- **Opening** asks the helper, as the world does. While the app starts, its doorway is purple and a few purple
  squares rise from it (0.6 s), the world's own sign for walking in. If the helper says it failed, the typing line
  shows the helper's words for five seconds ("Couldn't open Notepad: it failed to start").
- **Version 1 does not change anything.** No pinning, no moving, no removing from the laptop. Those stay in the
  world.

### 2.3 What else it shows

The time (large, JetBrains Mono), the date, the battery. Nothing else in version 1: no notifications, no volume, no
picture of the world. A thing is added only when he asks for it.

### 2.4 Motion

**At rest nothing moves, so nothing is drawn again.** The study measured why: ten small stars that twinkled without
end kept two processor cores busy.
- No animation that runs without end. No blinking, no drifting, no video.
- One star changes its brightness every four seconds, in one step.
- The clock changes once a minute.
- A house changes when its app opens or closes.
- Everything else is an answer to him and ends within a second.

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

- **`CELL`:** `floor((960 - GAP/2 - EDGE) / (ceil(most / 2) x 14.6))`, kept between 7 and 10, where `most` is the
  largest group's count. Up to 10 apps in a group a house is 120 wide, 12: 108, 14: 96, 16: 84.
- **House number `i` of a group** (0 is nearest): `k = floor(i / 2)`. Even `i` stands left, its right edge at
  `960 - GAP/2 - k x PITCH`. Odd `i` stands right, its left edge at `960 + GAP/2 + k x PITCH`. Its foot is on the
  road's top.
- **Order within a group:** by the world's place, nearest first (row, then `k`, then left before right, HUB.md
  3.3). An app without a place yet comes last, in the order of the apps file.
- **More than 16 apps in one group** is not designed (open).

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
- The page is served under an address scheme of its own (`aresos-home:`), from the page's folder only. Loose files
  would not let the page load modules or fetch data, which the companions' runtime needs.
- Every other address is refused. The network session is ephemeral. No developer tools, no context menu, no
  downloads, no new windows.
- App pictures of programs outside My apps (the finder's list) are served as `aresos-home://icon/<app id>`, read
  only from the path the helper gave for that ID.
- It runs in a systemd scope of its own with `MemoryHigh=640M`.

**What the page gets** (`window.aresosHome`):

| Call or event | Meaning |
|---|---|
| `home()` | his apps as the mod published them: ID, name, short name, group, place, hotbar slot, the logo's cells and colours |
| `programs()` | every program the helper lists: ID, name, group, whether it has a picture |
| `open(id)` | asks the helper to open it; resolves with the launch's state or the helper's failure words |
| `status()` | battery level and whether it charges |
| event `home` | the town changed: read `home()` again |
| event `programs` | the program list changed |
| event `running` | the IDs of the apps that have a window now |
| event `status` | the battery changed |

The page never gets a command, a path, the socket or the launch nonce.

**Memory** (measured in the study, 40 test apps, WebKitGTK 2.54.1): 333 MiB in all at rest, 126 MiB of it the
program's own and the rest shared library code; under 2 % of one processor core at rest. The bare engine is 256 MiB
of that.

---

## 5. The interface additions (`aresos-shell/1.2`)

Everything in 1.1 stays. A 1.2 helper offers the capabilities `views`, `home_state` and `apps_running`. A mod or a
helper that does not know them works as today.

- **A view.** `hello` may carry `"role": "view"` and `"view": "<name>"` (`[a-z0-9-]{1,32}`, here `laptop-home`).
  Without `role`, or with `"role": "desktop"`, hello means what it means today.
  - A view presents the same `instance` and `nonce` as the desktop; the supervisor starts both.
  - A view never becomes the desktop: it does not close the desktop's connection, and a desktop's hello does not
    close a view's. A second view with the same name closes the first. At most four views.
  - A view may send `list_apps`, `open_app` and `get_home`. `world_ready`, `heartbeat` and `publish_home` are
    refused (`invalid_state`). A view never counts for readiness.
  - A view gets `apps_changed`, `home_changed`, `apps_running` and `app_state` for its own launches. It never gets
    `shell_focus` or `shell_covered`.
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
  - The helper checks shapes and bounds only (at most 200 apps, IDs it lists, strings as in 1.1) and keeps the last
    complete home in memory. It does not read meaning into it.
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
got in a file of its own state folder and shows that, with open apps still lit from `apps_running`. Opening still
works: it only needs the helper.

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
- **Fallback without `gtk4-layer-shell`:** a normal window `aresos.laptop-home` with a rule beside the world's:
  `serverDecoration="no"`, `skipTaskbar="yes"`, `skipWindowSwitcher="yes"`, then `MoveToOutput`, `Maximize`,
  `ToggleAlwaysOnBottom`. The helper must then leave that app-id out of covering, of the return of focus and of the
  list of unknown windows, as it does for `aresos.cover`, and the window program must refuse to close.
- **Start.** The desktop supervisor (`/usr/libexec/aresos-desktop`) starts it when package 23c's rule says the world
  is on the monitor and an `eDP` output is on: after the world has moved, in its own scope, with the helper's
  socket, the instance and the nonce. The start-up cover (23b) lies over every screen until the world is ready; the
  laptop home starts under it.
- **Stop.** When the monitor goes, or the laptop's screen is switched off (lid closed), the supervisor stops it
  (SIGTERM), before the world moves back.
- **It is never needed.** It is no part of readiness. If it ends by itself it is started again after 2, 10 and 30
  seconds, then no more in this session: the laptop screen is then the plain background of today.
- **Apps** open on the screen the pointer is on (23c), so an app opened from the laptop home opens over it.

---

## 7. The companions later

The owner's plan: "the alternative laptop homescreen gets like a room or a city custom made where companions can
walk around in and do activities with a menu for opening apps".

The town is that city. What their runtime needs from a host (`~/companions/runtime/README.md`) is already here:

| The runtime asks for | The laptop home gives |
|---|---|
| a canvas it may draw on | a see-through canvas over the town, under the typing line and the hotbar |
| a world: floor, ledges, boxes | the home line as the floor; each street and each roof as a ledge with its free height; each house as a box (the prototype's `laptopHome.world.snapshot()`) |
| input | the page's own pointer |
| storage | a small file kept by the window program, given to the page at its start |
| its files as modules over an address | the `aresos-home:` scheme (section 4) |

The menu for opening apps stays what it is: houses, hotbar, typing.

Left to the companions package: how much room they get above the roofs (60 pixels under the next street at `CELL`
10; a street less or smaller houses would give more), what they do in the town, their memory, and whether they
follow the rule of section 2.4 or get a budget of their own (they move without being asked; that costs what the
study measured).

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
- **Stars that twinkle, clouds that drift, a live view of the world.** Anything that moves without end costs a
  processor core or more, on a screen he is mostly not looking at.

---

## 9. Build order

1. **`aresos-shell/1.2` in the helper:** views, `get_home`, `home_changed`, `apps_running`, the example files. With
   tests that a view never displaces the desktop and never counts for readiness.
2. **The mod publishes its home** (`publish_home`) after hello and on every change.
3. **The window program and the page**, against a stand-in helper: the town from section 3, the finder, the hotbar,
   opening, the lit houses. Pictures from a headless compositor, as the study's tool takes them. The image gets
   `gtk4-layer-shell` and JetBrains Mono, and a check that WebKitGTK 6.0 and its Python binding are there.
4. **The supervisor starts and stops it** with package 23c's screens, in its scope, with the restart rule.
5. **The laptop trial** with the monitor: the keyboard on a click, Alt+Tab, an app maximized over it, plugging and
   unplugging, the memory in the real session.

Steps 1 and 2 are data and rules; step 3 is how a screen looks.

---

## 10. For the owner

1. **Is Night street the one?** Or Map table, or Console, or two of them with a choice.
2. **Dark houses that light up when their app is open**, or every logo in full colour all the time?
3. **Only time, date and battery** besides the apps. Is anything missing that he wants to see there?
4. **A key that jumps to the laptop home's typing line** from anywhere, so it is the launcher of the whole session
   while the monitor is in?
