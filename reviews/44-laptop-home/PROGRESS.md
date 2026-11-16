# Package 44: the laptop-screen home (design study): report

Builder: one Claude agent on Fable 5.2 (a new design that was not scoped yet), 2026-11-16. The file tool refuses a
file named `REPORT.md`, so the report is here; the orchestrator commits it as the report.

Nothing under `os/` or `mod/` changed. Everything in this folder is a development aid for choosing a design. The
design draft that a build package can follow is `docs/design/LAPTOP-HOME.md`.

## In short

- Three directions, each a page he can click through, with pictures: **Night street**, **Map table**, **Console**.
- I recommend **Night street**: the town seen from the side at night, one street per group, a house lit while its
  app runs. It shows all his apps at once with their names, it is calm beside the bright world, and it is the one
  shape the companions already understand (floors and ledges), so they move in later without a rebuild.
- Tech: the system's web engine (WebKitGTK 6.0) in one small window of its own, no browser around it. Measured with
  40 test apps: **about 330 MiB** in all, of which about 125 MiB is its own and the rest is library code shared with
  other programs. At rest it uses under 2 % of one processor core.
- The app helper needs three small additions before a second client can exist (below). Today a second client throws
  the game off the helper.

## Done

| What | Where |
|---|---|
| Three clickable prototypes at 1920 x 1080, no network, no build step | `prototypes/street/`, `prototypes/map/`, `prototypes/console/` (each an `index.html`; they share `prototypes/shared/`) |
| The test town: 5, 12, 24 or 40 test apps ("Test Web 1" …) with generated block logos, 20 more programs outside My apps | `prototypes/shared/home.js` |
| 14 pictures at 1920 x 1080, drawn by the web engine I recommend | `pictures/` |
| A tool that shows a page in WebKitGTK inside a headless compositor of its own, takes the pictures, measures memory and checks keys and clicks | `tools/shots.sh`, `tools/webkit-shot.py` |
| The design draft of the recommended direction | `docs/design/LAPTOP-HOME.md` |

To look at a prototype, open its `index.html` in any browser. It scales to the window. `?apps=5`, `12`, `24` or `40`
after the address changes the town's size.

The logos are made here from sixteen hand-drawn signs (a ring, a heart, a moon …) and flat colours. No app icon, no
logo of a real program and no game texture is in this folder. Fonts: Space Grotesk and JetBrains Mono, both under
the SIL Open Font License 1.1; the licence texts are beside the font files in `prototypes/shared/fonts/`. Space
Grotesk is the same file the image already ships.

## What all three share

These are the world's own habits, so he has nothing new to learn:
- **The hotbar** at the bottom: his nine pinned apps, in the same order as in the world. The keys 1 to 9 open them.
- **Typing finds.** He just types, as in the chat: a name or a short name (`term`, `/term`). Everything that does not
  fit goes dark, the best hit gets a gold frame, Enter opens it. Programs outside My apps show in a small list
  ("All programs"), so `pa` finds Test Paint although it has no logo. Escape clears.
- **A click opens.** The app opens on the laptop screen, over the home, as on any desktop (package 23c: apps open on
  the screen the pointer is on).
- **Lit means open.** An app that has a window is lit: a warm light in its doorway. He sees what is running without
  a list.
- **The arrow keys** move a gold frame from logo to logo; Enter opens.
- Top left the time and the date, top right the battery. Nothing else.
- **At rest nothing moves** (see "Memory").

## The three directions

### 1. Night street (recommended)

Pictures: [home](pictures/street-1-home.png), [finding "tool"](pictures/street-2-finding.png),
[finding a program outside My apps](pictures/street-3-all-programs.png), [an app opened](pictures/street-4-opened.png),
[day one, five apps](pictures/street-5-day-one.png), [forty apps](pictures/street-6-forty-apps.png),
[where companions can stand](pictures/street-7-ledges.png).

**What he sees.** His town from the side, at night. Four streets, one above the other: Internet, Games, Work & Media,
System & Tools, each with its colour as a line along the road. On each street his apps stand as their block logos,
solid blocks with a top and a side, each with its dark doorway and its doormat in the group's colour. Over each
logo its sign, as in the world: the name in white, the short name in gold. In the middle of each street, between the
two front logos, hangs the group's name with its direction and its count ("INTERNET, north · 7"), exactly where it
hangs in the world. The logos stand left and right of that middle, nearest first, as they stand left and right of
the avenue. A street is paved as far as it has logos; a group without apps is a short piece of road. Houses are a
little dark, as at night; the ones whose app is open are bright and have light in the door. Under the town a thin
line with one gold block in its middle, his home block, and below it the hotbar.

**What he does.** He moves the pointer down to the laptop and clicks a house. Or he types `tool`, the Tools street
stays bright and the rest goes dark, Enter. Or he presses 3 for the third hotbar app.

**How it grows.** Five apps are a hamlet in the middle of the screen. Each new app takes the next free place
outward on its street; nothing else moves, as in the world. The houses are 120 pixels wide until one street has more
than ten apps, then all of them shrink a little (84 pixels at sixteen in one group). Forty apps with fourteen in one
group fit without scrolling.

**Why it fits.** It is the town itself: the same logos, doors, signs, group names, colours and order. The world shows
it from inside at noon, one row at a time. The laptop shows the whole of it from the side at night.

### 2. Map table

Pictures: [home](pictures/map-1-home.png), [finding "tool"](pictures/map-2-finding.png),
[an app opened](pictures/map-3-opened.png), [forty apps](pictures/map-4-forty-apps.png).

**What he sees.** The town from straight above, to scale: the gold home block in the middle, the four avenues with
their coloured lines, and every logo laid flat at the very place where it stands in the world (north is up). A
dashed square shows where each group's next app will stand.

**What he does.** The same clicks and keys. What he knows from walking works here: Games are to the right, Tools are
below.

**Its price.** A true map is a cross, and a laptop screen is wide and low. With 24 apps a logo is 84 pixels, with 40
it is 72 and the names only show under the pointer or for a search. Left and right of the cross the screen stays
empty. It is the most literal "same home from another angle", and the weakest use of the screen.

### 3. Console

Pictures: [home](pictures/console-1-home.png), [finding "tool"](pictures/console-2-finding.png),
[an app opened](pictures/console-3-opened.png).

**What he sees.** No picture. A large clock, a `/` line to type in, a short list "Open now", and his apps as four
columns of names under the group names in their colours.

**What he does.** The same. It is the fastest to read and the least special: close to a launcher list, which the
brief did not want. I built it as the plain one to hold the other two against.

## Recommendation: Night street

- **Functional first.** Every app of his is on the screen with its name and short name, as a target at least 84
  pixels wide. Three ways in, all of them the world's: click, hotbar key, typing.
- **It fits without being a copy.** It is not a picture of the game. It is the town drawn in the crown language:
  near-black, gold only for the home block, the short names and what is selected.
- **Calm.** A dark screen beside the world, and nothing on it moves unless he does something.
- **The companions fit as they are.** Their runtime knows a screen as a floor, ledges and boxes
  (`~/companions/runtime/README.md`, "World provider"). Streets and roofs are ledges, houses are boxes, the line
  over the hotbar is the floor. The prototype already hands out that description (`laptopHome.world.snapshot()`, 28
  ledges in the 24-app town). The map would need companions drawn from above, which do not exist.
- **Other looks stay possible.** A look is one folder of web files on top of the same host and the same data. Map
  table can be added later as a second choice ("or we build multiple options and then enable choosing") without
  touching the system side again.

## Tech and memory

**Choice: WebKitGTK 6.0 (the system's web engine) in a small GTK 4 program of its own, written in Python like the
start-up cover and the app helper.** One window, no browser around it, no network. The laptop's AresOS has
WebKitGTK 2.54.1 and GTK 4 with their Python bindings; the build package checks that the image carries them.

Why: the companions run on a web runtime (a canvas, a world provider, input, storage). A web page is the one place
they can move into unchanged. A native GTK drawing (as the cover does) would be lighter, I estimate 50 to 80 MiB, but
the companions would have to be rebuilt for it. A browser in app mode is heavier and would bring his browser
profile into it. A second Minecraft was never an option.

**Measured** (Night street, 40 test apps, 1920 x 1080, WebKitGTK 2.54.1 in a headless `cage` compositor that drew on
the laptop's NVIDIA chip; `tools/shots.sh measure`, 8 seconds to settle, then 10 to 20 seconds watched):

| Set-up | Memory in all (PSS) | of that its own (anonymous) | Processor at rest |
|---|---|---|---|
| Night street at rest | **333 MiB** | 126 MiB | 1.7 % of one core |
| the same, the engine drawing the page in software | 304 MiB | 96 MiB | 0.7 % |
| the bare engine with an empty page | 256 MiB | 101 MiB | not at rest yet |
| the bare engine, software | 226 MiB | 82 MiB | 0.2 % |
| an earlier version with ten stars twinkling without end | 414 MiB | 197 MiB | **220 %** (two cores) |

- The three processes: the window program 167 MiB, the engine's page process 143 MiB, its network process 23 MiB.
  "In all" counts shared library pages once, split between the programs that use them. Added up the naive way
  (RSS), the three show 572 MiB.
- The engine is most of it: about 255 MiB before any page. The home itself adds about 80 MiB.
- For comparison, the world's game may use 2560 MiB (package 23d). The laptop home is about an eighth of that.
- **The lesson of the last row is a design rule: at rest nothing on this screen moves.** Ten two-pixel stars that
  changed brightness without end made the engine draw 60 pictures a second and kept two cores busy in this set-up.
  Now one star changes every four seconds in one step, and a house lights up or goes dark when an app opens or
  closes. Motion happens only as an answer to him (the purple puff in a doorway, 0.6 seconds).
- I suggest the build runs it in a scope of its own with `MemoryHigh=640M`.

**Verified.**
- `tools/shots.sh all` made the 14 pictures, each 1920 x 1080, in WebKitGTK 2.54.1 inside a headless compositor. No
  window ever opened on his screen: the tool removes his display variables and refuses to start outside its own
  compositor.
- `tools/shots.sh check` sends each page the keys and clicks a person would and compares what the page did: typing
  finds the app, the others go dark, Enter opens it, it shows as running, closing ends that, key 1 opens the first
  hotbar app, a click on a logo opens it, the arrow keys select, typing finds a program outside My apps, Escape
  clears. 10 of 10 on each of the three pages.
- The pictures of the key moments come from page options that call the same functions as the keys and the click.

**Not verified.**
- Nobody used a real mouse or keyboard on the pages; the events of the check are made inside the page.
- The numbers are from a headless compositor, not from his labwc session with two screens. Memory there can differ
  by some tens of MiB.
- Nothing talks to the real app helper: the pages use a stand-in with test apps.
- How it sits in labwc (below) is designed from labwc's and the helper's code, not tried: this laptop has no
  `gtk4-layer-shell`, and package 23c, which moves the world to the monitor, is not built yet.

## How it talks to the helper

The laptop home must read the same apps as the world and must not keep a list of its own. Two facts stand in the
way today (`os/config/usr/libexec/aresos-shell`):
- **The helper serves one client.** Its events go to one connection, "the desktop", and a second `hello` closes the
  first one's connection ("the newest authenticated desktop wins"). A laptop home that said hello would throw the
  game out.
- **The helper does not know My apps.** It knows every program, its picture and how to open it. Which apps are his,
  their short names, groups, places and hotbar slots are the mod's (`config/aresos/apps.json`, HUB.md 3.5), and
  the block logos are made in the mod (HUB.md 3.6).

So the protocol needs three additions, as `aresos-shell/1.2` (the shapes are in LAPTOP-HOME.md section 5):
1. **A second kind of client, a "view".** `hello` with `"role": "view"`. A view never replaces the desktop and is
   not closed by it, cannot say `world_ready` or `heartbeat`, never counts for the supervisor's readiness, may
   `list_apps` and `open_app`, and gets `apps_changed`.
2. **The mod tells the helper what the town holds, and the helper passes it on.** After each change the mod sends
   `publish_home`: for each of his apps the ID, short name, group, place, hotbar slot and the 12 x 12 cells of its
   logo with their colours. The helper checks sizes, keeps the last one and hands it to views (`get_home`,
   `home_changed`). One converter stays the only one: the laptop draws the cells the mod worked out, so a logo can
   never look different on the two screens.
3. **What is open.** `apps_running` to a view: the apps that have a window now. The helper already tracks windows
   per app.

A web page cannot open a Unix socket. The window program holds the connection and gives the page four calls and
four events (LAPTOP-HOME.md section 4). The page never sees a command, a path or the launch nonce.

## How it lives in the session

- **What it is in labwc: a layer surface on the background layer of the laptop's own screen**, not a window. That
  layer is below every app window by definition. A layer surface is never in Alt+Tab, cannot be closed with Alt+F4,
  minimized or moved, and the helper's window tracking never sees it, so it can never count as covering the world
  or be minimized as "what covers the world" (package 40). `rc.xml` needs no new rule. It takes the keyboard when he
  clicks it (keyboard mode "on demand") and gives it back when he clicks elsewhere.
- **It needs one small library in the image:** `gtk4-layer-shell` (not on the laptop today). Without it the fallback
  is a normal window with a rule like the world's (`serverDecoration="no"`, `skipWindowSwitcher="yes"`,
  `MoveToOutput`, `Maximize`, `ToggleAlwaysOnBottom`); then the helper has to leave that window out of its covering
  and focus rules, as it does for the start-up cover.
- **Start and stop: the desktop supervisor**, with package 23c's watching of the screens. When the world has moved to
  the monitor, the supervisor starts the laptop home in a scope of its own on the laptop's screen. When the monitor
  goes, it stops it and the world comes back. With the lid closed there is no laptop screen and no laptop home.
- **It is never needed.** If it crashes it is started again, three times at most, and after that the laptop screen is
  the plain dark background of today. It is no part of "the world is ready".
- **Apps** open over it, on the screen the pointer is on. When an app that was opened from the laptop closes, the
  focus does not jump to the world on the other screen.

## How the companions version grows from it

- The page gets one more layer: a see-through canvas over the town. The companions' runtime draws there. The world
  provider it asks for is the description the prototype already gives: streets and roofs as ledges, houses as boxes,
  the floor over the hotbar. Input is the page's own pointer. Storage is a small file the window program keeps.
- The page is served by the window program under an address scheme of its own, not as loose files, because the
  runtime loads its parts as modules and fetches its designs, which does not work from loose files. The build
  should do this from the start so nothing changes when they arrive.
- The town does not change. The houses, the streets and the menu for opening apps (hotbar, typing, click) stay
  where they are; the companions walk the streets, sit on roofs and stand on the floor.
- What the companions package still has to decide: whether houses shrink or a street is left out to give companions
  more room above the roofs (today 60 pixels under the next street), what they do there, and their own memory.

## JUDGMENT-CALL (for the owner)

1. **Which direction.** I chose Night street. Rejected: Map table (logos too small, half the screen empty,
   companions do not fit) and Console (a launcher list). Changing later costs little on the system side: a look is
   one folder of web files.
2. **One look or a choice.** I would build Night street alone first. A second look and a way to choose can follow
   once he has lived with the first.
3. **Night, and dark houses.** Houses are dimmed until their app is open. It makes "what is running" visible at a
   glance and keeps the screen calm. The other way: every logo in full colour, and only the door light shows what
   is open. One number to change.
4. **What else is on the screen.** Only the time, the date and the battery. No notifications, no volume, no view
   into the world. Each can be added; I left them out so the apps stay the point.
5. **A key that jumps to the laptop home's typing line** from anywhere (for example the Super key): it would make
   the laptop home the launcher of the whole session while the monitor is in. I would add it, but a reserved key
   changes how AresOS feels, so it is his call.
6. **Pins change in the world only** in version 1. The laptop shows the hotbar and opens from it; it does not
   re-order it.

## PLAN-GAP

- The brief says the helper "already gives the mod the app list, pictures, pins and launching". Pins, My apps,
  short names, groups and places are the mod's, and the helper has one client. A "second client" needs the three
  additions above first.
- The brief says the world "stays out of Alt+Tab" today. It does not: `rc.xml` has no such rule for
  `aresos-desktop`, and HUB.md (package 40) describes Alt+Tab to the world. The laptop home stays out because it is
  not a window.
- JetBrains Mono is not in the image (only Space Grotesk is, under `/usr/share/fonts/aresos`). The build adds it
  (OFL) or the numbers and short names fall back to another font.
- `gtk4-layer-shell` is not on the laptop.

## Open questions

- Does labwc 0.9.6 give a background layer surface the keyboard on a click as expected ("on demand")? To try in a
  test compositor once the library is there.
- The real memory in his session with two screens, and with the companions.
- More than sixteen apps in one group: the street would have to scroll sideways or the houses shrink below 84
  pixels. Not designed.
- Opening an app on the monitor from the laptop (for example Shift and click) would need one more field in
  `open_app`. Not in version 1.
- A dot on the Map table showing where he stands in the world would need the mod to say so. Left out.
