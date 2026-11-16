# Package 44: the laptop-screen home (design study): report

Builder: one Claude agent on Fable 5.2 (a new design that was not scoped yet), 2026-11-16. The file tool refuses a
file named `REPORT.md`, so the report is here; the orchestrator commits it as the report.

Review fixes 1 (findings 1 to 13 of `REVIEW-1.md`): one Claude agent on Opus 5.5, the same day. What changed is
listed in "Review fixes 1" at the end.

The day look (the owner's question "why was night chosen", the same day): one Claude agent on Fable 5.2, design
work. What it added is in "The day look" at the end.

The day's grid and terraces (the owner chose day and asked for a cleaner layout, the same day): one Claude agent on
Fable 5.2, design work. What it changed is in "The day look on one grid" at the end.

Review fixes 3 (should-fix 1 to 5 of `REVIEW-3.md`, and the owner's answer on the Super key, board #333): one Claude
agent on Opus 5.5, the same day. What changed is in "Review fixes 3" at the end, with the list "For the build
brief".

Nothing under `os/` or `mod/` changed. Everything in this folder is a development aid for choosing a design. The
design draft that a build package can follow is `docs/design/LAPTOP-HOME.md`.

## In short

- Three directions, each a page he can click through, with pictures: **Night street**, **Map table**, **Console**.
- I recommend **Night street**: the town seen from the side at night, one street per group, a house lit while its
  app runs.
  - It shows all his apps at once with their names, up to 16 in a group (about 45 apps); a bigger group's street
    slides.
  - It is calm beside the bright world.
  - It is the one shape the companions already understand (floors and ledges), so they move in later without a
    rebuild.
- The owner chose the street by day, on terraces (JUDGMENT-CALL 1). Night stays as the second look.
- Tech: the system's web engine (WebKitGTK 6.0) in one small window of its own, no browser around it.
  - Measured with 40 test apps: **about 335 MiB** in all. With the drawing libraries pinned to Mesa and Intel,
    research for package 49 measured about 150 to 180 MiB, and the build pins them (LAPTOP-HOME.md section 4,
    "Memory").
  - 127 MiB of it is working memory; the rest is mostly the program files it maps (the engine, GTK, the graphics
    driver).
  - At rest it uses under 2 % of one processor core. One companion-sized figure walking costs about a fifth of
    one core.
- The app helper needs three small additions before a second client can exist (below), and the laptop home needs a
  token of its own. Today a second client throws the game off the helper.

## Done

| What | Where |
|---|---|
| Three clickable prototypes at 1920 x 1080, no network, no build step | `prototypes/street/`, `prototypes/map/`, `prototypes/console/` (each an `index.html`; they share `prototypes/shared/`) |
| The test town: 5, 12, 24, 40 or 45 test apps ("Test Web 1" …) with block logos generated from each app's ID, 20 more programs outside My apps, some with a generic name and keywords | `prototypes/shared/home.js` |
| 28 pictures at 1920 x 1080, drawn by the web engine I recommend: 17 of the three directions, 4 of the day's first form, 7 of the day on its grid | `pictures/` |
| A tool that shows a page in WebKitGTK inside a headless compositor of its own, takes the pictures, measures memory (working memory, files, shared memory) and processor time per process, and checks keys and clicks | `tools/shots.sh`, `tools/webkit-shot.py` |
| The design draft of the recommended direction | `docs/design/LAPTOP-HOME.md` |

To look at a prototype, open its `index.html` in any browser. It scales to the window. `?apps=5`, `12`, `24`, `40`
or `45` after the address changes the town's size; `&hole=test-web-1` takes an app away and leaves its place free;
`&bright=1` shows every logo in full colour.

The logos are made here from sixteen hand-drawn signs (a ring, a heart, a moon …) and flat colours. No app icon, no
logo of a real program and no game texture is in this folder. Fonts: Space Grotesk and JetBrains Mono, both under
the SIL Open Font License 1.1; the licence texts are beside the font files in `prototypes/shared/fonts/`. Space
Grotesk is the same file the image already ships.

## What all three share

These are the world's own habits, so he has nothing new to learn:
- **The hotbar** at the bottom: his nine pinned apps, in the same order as in the world. The keys 1 to 9 open them.
- **Typing finds.** He just types, as in the chat: a name or a short name (`term`, `/term`). Everything that does not
  fit goes dark, the best hit gets a gold frame, Enter opens it. After the names, typing also searches the generic
  names and keywords the helper lists, so `pdf` finds Test Viewer, a "Document Viewer" with the keyword pdf.
  Programs outside My apps show in a small list ("All programs") with their generic name, never a group. Escape
  clears.
- **A click opens.** The app opens on the laptop screen, over the home, as on any desktop (package 23c: apps open on
  the screen the pointer is on).
- **Lit means open.** An app that has a window is lit: a warm light in its doorway. He sees what is running without
  a list.
- **The arrow keys** move a gold frame from logo to logo; Enter opens.
- Top left the time and the date, top right the battery. Nothing else.
- **At rest nothing moves** (see "Tech and memory").

## The three directions

### 1. Night street (recommended)

Pictures: [home](pictures/street-1-home.png), [finding "tool"](pictures/street-2-finding.png),
[finding a program outside My apps](pictures/street-3-all-programs.png), [an app opened](pictures/street-4-opened.png),
[day one, five apps](pictures/street-5-day-one.png), [forty apps](pictures/street-6-forty-apps.png),
[where companions can stand](pictures/street-7-ledges.png),
[forty-five apps, twenty in System & Tools](pictures/street-8-forty-five-apps.png),
[a far house slid into view](pictures/street-9-far-house.png),
[every logo in full colour](pictures/street-10-full-colour.png).

**What he sees.** His town from the side, at night. Four streets, one above the other: Internet, Games, Work & Media,
System & Tools, each with its colour as a line along the road. On each street his apps stand as their block logos,
solid blocks with a top and a side, each with its dark doorway and its doormat in the group's colour. Over each
logo its sign, as in the world: the name in white, the short name in gold. In the middle of each street, between the
two front logos, hangs the group's name with its direction and its count ("INTERNET, north · 7"), exactly where it
hangs in the world. Each logo stands on the side of the street its place is on in the world: the nearer to home,
the nearer to the middle. A street is paved as far as it has logos; a group without apps is a short piece of road.
Houses are slightly dimmed, as at night (62 % brightness, 82 % saturation); the ones whose app is open are bright
and have light in the door. Under the town a thin
line with one gold block in its middle, his home block, and below it the hotbar.

**What he does.** While he works in an app, he moves the pointer down to the laptop and clicks a house. Or he types
`tool`, the Tools street stays bright and the rest goes dark, Enter. Or he presses 3 for the third hotbar app. From
inside the world the game holds the pointer, so he first presses Esc (or E, or T). Super opens a search over the
world instead, without leaving it (JUDGMENT-CALL 5).

**How it grows.**
- Five apps are a hamlet in the middle of the screen.
- Each new app stands at the place it got in the world, usually the next free one outward on its street. A removed
  app leaves its place free, in the world and here. Nothing else moves.
- The houses are 120 pixels wide until a street needs more than five places on a side. Then all of them shrink a
  little: 84 pixels at sixteen in one group. Forty apps with fourteen in one group fit without scrolling.
- Past sixteen in one group, that street is longer than the screen. At rest it stands in the middle, with a sign at
  each end that counts the houses out of sight ("‹ 2", "2 ›"). It slides when he types a name that is out of sight,
  uses the arrow keys or clicks an end sign (pictures 8 and 9).

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
  pixels wide, up to 16 apps in a group: about 45 apps in HUB.md's planning mix. A bigger group's street slides, so
  its far houses are one typed name, arrow key or click away. Three ways in, all of them the world's: click, hotbar
  key, typing.
- **It fits without being a copy.** It is not a picture of the game. It is the town drawn in the crown language:
  near-black, gold only for the home block, the short names and what is selected.
- **Calm.** A dark screen beside the world, and nothing on it moves unless he does something.
- **The companions fit as they are.** Their runtime knows a screen as a floor, ledges and boxes
  (`~/companions/runtime/README.md`, "World provider"). Streets and roofs are ledges, houses are boxes, the line
  over the hotbar is the floor. The prototype already hands out that description (`laptopHome.world.snapshot()`, 28
  ledges in the 24-app town). The map would need companions drawn from above, which do not exist. Measured: one
  companion-sized figure walking costs about a fifth of one processor core on this engine (below).
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

| Set-up | Memory in all (PSS) | of that working memory (anonymous) | Processor at rest |
|---|---|---|---|
| Night street at rest | **333 MiB** | 126 MiB | 1.7 % of one core |
| the same, the engine drawing the page in software | 304 MiB | 96 MiB | 0.7 % |
| the bare engine with an empty page | 256 MiB | 101 MiB | not at rest yet |
| the bare engine, software | 226 MiB | 82 MiB | 0.2 % |
| an earlier version with ten stars twinkling without end | 414 MiB | 197 MiB | **220 %** (two cores) |

In these first measurements GTK drew with its default renderer on the Intel chip while the compositor drew on
NVIDIA. Review fixes 1 found that and measured again (below).

- The three processes: the window program 167 MiB, the engine's page process 143 MiB, its network process 23 MiB.
  "In all" (PSS) splits each shared page between the programs that use it. Added up the naive way (RSS), the three
  show 572 MiB.
- **What the rest is** (measured since, review fix 9).
  - Of about 335 MiB, 127 MiB is working memory and 208 MiB the program and library files it maps: the engine,
    GTK and the graphics driver's libraries.
  - Shared memory is under 1 MiB.
  - Memory the graphics chip holds for it does not show in these numbers.
  - With the compositor and GTK on the Intel chip it measured about 265 MiB. *Corrected in review fixes 3:* that
    this is his session's number does not hold. libglvnd loads NVIDIA's libraries into every process unless the
    EGL and Vulkan vendor is pinned, so unpinned his session is near 335 MiB, and pinned about 150 to 180
    (LAPTOP-HOME.md section 4, "Memory").
- The engine is most of it: about 255 MiB before any page. The home itself adds about 80 MiB.
- For comparison, the world's game may use 2560 MiB (package 23d). The laptop home is about an eighth of that.
- **The last row gave the design rule: at rest nothing on this screen moves.** Ten two-pixel stars that changed
  brightness without end made the engine draw 60 pictures a second.
  - In this set-up that kept two cores busy. Review fixes 1 found why: GTK and the compositor drew on different
    chips, so the processor copied every frame from one to the other.
  - On one chip the same kind of motion costs about a fifth of a core (below).
  - The rule stands: a screen he mostly does not look at should cost nothing. Now one star changes every four
    seconds in one step, and a house lights up or goes dark when an app opens or closes. Motion happens only as an
    answer to him (the purple puff in a doorway, 0.6 seconds).

**Motion, measured** (review fix 7): one figure the size of a companion (80 x 80 pixels) walks along a street. It is
drawn on a see-through canvas over the whole 40-app town that is cleared and drawn again every frame, as the
companions' runtime draws, at 60 frames a second, watched for a minute (`?sprite=1`).

| Set-up | Processor | Memory (PSS) |
|---|---|---|
| Compositor and GTK on the Intel chip, at rest | 0.5 % | 264 MiB |
| Compositor and GTK on the Intel chip, the figure walking | **22 %** (window program 7, page 15) | 268 MiB |
| Compositor and GTK on the NVIDIA chip (GTK's OpenGL renderer), at rest | 0.6 % | 289 MiB |
| the same, the figure walking | 26 % (window program 13, page 13) | 296 MiB |
| Compositor on NVIDIA, GTK's default renderer on Intel, the figure walking | **248 %** (window program 240) | 347 MiB |
| the same, 30 frames a second (30 seconds) | 145 % | 347 MiB |
| the same, the engine drawing the page in software (30 seconds) | 123 % (page 100) | 317 MiB |

What it means for the companions version:
- **On one chip, a moving companion costs about a fifth of one processor core** while it moves, and a few MiB.
  That is affordable beside the world.
- **The web choice holds.** The cost is per frame, not per figure: the runtime redraws one canvas.
- **They need a budget:** fewer frames (the runtime takes its clock from the host), no frames while nobody moves,
  none while the laptop screen is off or covered.
- **The window program must draw on the compositor's chip.** On two chips the same figure costs two and a half
  cores. The laptop trial checks it in his session (LAPTOP-HOME.md sections 4 and 9).
- I suggest the build runs it in a scope of its own with `MemoryHigh=640M`.

**Verified.**
- `tools/shots.sh all` made the 17 pictures, each 1920 x 1080, in WebKitGTK 2.54.1 inside a headless compositor. No
  window ever opened on his screen: the tool removes his display variables and refuses to start outside its own
  compositor.
- `tools/shots.sh check` sends each page the keys and clicks a person would and compares what the page did: typing
  finds the app, the others go dark, Enter opens it, it shows as running, closing ends that, key 1 opens the first
  hotbar app, a click on a logo opens it, the arrow keys select, typing finds a program outside My apps, Escape
  clears. 10 of 10 on each of the three pages.
- Night street's own check, 9 of 9, on a 45-app town with `test-web-1` (place `N0L0`) removed:
  - no other house changes side or slot;
  - a house past the screen's edge slides into view when he types its name and back on Escape;
  - the end signs count the houses out of sight.
- The pictures of the key moments come from page options that call the same functions as the keys and the click.

**Not verified.**
- Nobody used a real mouse or keyboard on the pages; the events of the check are made inside the page.
- The numbers are from a headless compositor, not from his labwc session with two screens. Memory there can differ
  by some tens of MiB.
- Nothing talks to the real app helper: the pages use a stand-in with test apps.
- How it sits in labwc (below) is designed from labwc's and the helper's code, not tried: this laptop has no
  `gtk4-layer-shell`, and package 23c, which moves the world to the monitor, is not built yet.
- The way from the world (Esc), Super's search over the world, and what the game does when the laptop home takes
  the keyboard.
- Which graphics chip GTK and labwc draw on in his session.

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
   - It proves who it is with a token of its own that lasts the session (`ARESOS_VIEW_TOKEN`), not the game's nonce,
     which changes with every game start. The helper knows a view by that token.
   - Its hello leaves the desktop's state alone.
   - Its launches are kept apart from the game's in the helper's journal, and only it hears about them.
   - When the helper restarts (with each game start), the laptop home connects again with the same token. In
     between it shows the last town, with opening off for those seconds.
2. **The mod tells the helper what the town holds, and the helper passes it on.** After each change the mod sends
   `publish_home`: for each of his apps the ID, short name, group, place, hotbar slot and the 12 x 12 cells of its
   logo with their colours. The helper checks sizes, keeps the last one and hands it to views (`get_home`,
   `home_changed`). One converter stays the only one: the laptop draws the cells the mod worked out, so a logo can
   never look different on the two screens.
3. **What is open.** `apps_running` to a view: the apps that have a window now. The helper already tracks windows
   per app.

A web page cannot open a Unix socket. The window program holds the connection and gives the page four calls and
five events (LAPTOP-HOME.md section 4). The page never sees a command, a path, the view token or the launch nonce.

## How it lives in the session

- **What it is in labwc: a layer surface on the background layer of the laptop's own screen**, not a window. That
  layer is below every app window by definition. A layer surface is never in Alt+Tab, cannot be closed with Alt+F4,
  minimized or moved, and the helper's window tracking never sees it, so it can never count as covering the world
  or be minimized as "what covers the world" (package 40). `rc.xml` needs no new rule. It takes the keyboard when he
  clicks it (keyboard mode "on demand") and gives it back when he clicks elsewhere.
- **It needs one small library in the image:** `gtk4-layer-shell` (not on the laptop today), loaded through
  `LD_PRELOAD` from Python.
  - Without it the fallback is a normal window that puts itself full-screen on the laptop's screen. A fixed
    `rc.xml` cannot know that screen's name.
  - It gets a rule like the world's (`serverDecoration="no"`, `skipWindowSwitcher="yes"`, `ToggleAlwaysOnBottom`).
  - The helper then has to leave that window out of its covering and focus rules, as it does for the start-up
    cover.
- **From the world to the laptop.** While the world has the focus, the game holds the pointer. He presses Esc (or
  E, or T), moves the pointer down and clicks.
- **Super** (JUDGMENT-CALL 5, board #333) opens a search bar over the world, on the screen that shows it, and the
  app opens there. It does not lead to the laptop, whose typing line is for when he works on the laptop screen
  (LAPTOP-HOME.md section 6).
- **Start and stop: the desktop supervisor**, with package 23c's watching of the screens. When the world has moved to
  the monitor, the supervisor starts the laptop home in a scope of its own on the laptop's screen. When the monitor
  goes, it stops it and the world comes back. With the lid closed there is no laptop screen and no laptop home.
- **It is never needed.** If it crashes it is started again, three times at most, and after that the laptop screen is
  the plain dark background of today. It is no part of "the world is ready". Losing the helper when the game
  restarts is not a crash: it connects again with its token.
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
  more room above the roofs (today 60 pixels under the next street), what they do there, their own memory, and
  their frame budget (about a fifth of a core while they move at 60 frames a second, measured above).
- A street that slides moves its ledges and boxes with it; the runtime reads the world every frame, so companions
  standing there ride along.

## JUDGMENT-CALL (for the owner)

1. **Which direction, and by night or by day.** Answered by the owner (2026-11-16): the street, by day, on
   terraces (board #332: "Terraces"). He then asked for a cleaner layout ("The day look on one grid" at the end).
   What was asked:
   - The direction: I chose the street. Rejected: Map table (logos too small, half the screen empty, companions do
     not fit) and Console (a launcher list). Changing later costs little on the system side: a look is one folder
     of web files.
   - The street's light: the study drew night. After the owner's question the same town was drawn by day
     ("The day look" below). Compare [street-1](pictures/street-1-home.png) with [day-1](pictures/day-1-home.png)
     and [street-6](pictures/street-6-forty-apps.png) with [day-6](pictures/day-6-forty-apps.png). I recommend day:
     his world is always at noon, so by day both screens show one place. Night is calmer and shows what is open a
     little more strongly.
2. **One look or a choice.** Kept as recommended (2026-11-16, no objection): one look first, day; night stays
   ready in the same page. I would build one look first, the one he picks in 1. Night and day are one page with
   two sets of colours, so the other stays ready; a way to choose can follow once he has lived with the first.
3. **Slightly dimmed houses, or every logo in full colour.** Answered by the owner (2026-11-16): dimmed until
   open ("dimmed and light up when used makes sense"). Compare [street-1](pictures/street-1-home.png) and
   [street-10](pictures/street-10-full-colour.png).
   - Slightly dimmed (62 % brightness, 82 % saturation) until their app is open: what is running shows at a glance,
     and the screen stays calm.
   - Full colour: only the door light shows what is open.
   - One number to change. I recommend slightly dimmed.
4. **What else is on the screen.** Kept as recommended (2026-11-16, no objection). Only the time, the date and
   the battery. No notifications, no volume, no view into the world. Each can be added; I left them out so the
   apps stay the point. I recommend that for version 1.
5. **A reserved key that jumps to the laptop home's typing line** from anywhere, for example the Super key.
   Answered by the owner (2026-11-16, board #333): yes to reserving Super, with a change. Asked "pressing the Super
   key alone jumps to the laptop home's search from anywhere, the world included … Right?", he answered: "Yes but
   the search bar should appear on the homescreen I'd say". (His earlier words on the study, "so does the search
   menu easy access", had been read as yes; board #333 asked him directly.)
   - His change, as the lead reads it: Super opens a search bar on the screen that shows the world, where he is
     looking (with the monitor in, the monitor; without it, the laptop's screen). It is AresOS's own search over
     the world, as the Apps screen's search, and it opens the app on that same screen. LAPTOP-HOME.md section 6
     and section 9, step 5, have how.
   - The laptop home keeps its own typing line for when he works on the laptop screen.
   - Open for the build brief (the lead's reading, to confirm with him at build time): whether Super, pressed while
     the pointer is on the laptop screen, should go to the laptop home's typing line instead.
   - What was asked: while he is in the world, the game holds the pointer, and without the key every way out is Esc
     (or E, or T) first. The key is the one way to search for an app without first freeing the pointer in the
     game, and it makes search the launcher of the whole session. I recommended it, and a reserved key changes how
     AresOS feels, so it was his call.
6. **Pins change in the world only** in version 1. Kept as recommended (2026-11-16, no objection). The laptop shows
   the hotbar and opens from it; it does not re-order it. I recommend so.

LAPTOP-HOME.md section 10 asks the same six questions, in this order.

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
- **The laptop home's view token** (`ARESOS_VIEW_TOKEN`, LAPTOP-HOME.md section 5) is not in any plan yet.
  - The supervisor makes it once per session, keeps it beside the instance, and hands it to every helper it starts
    and to the laptop home.
  - That is the supervisor's side, package 23c (`linux-aresos`).

## Open questions

- Does labwc 0.9.6 give a background layer surface the keyboard on a click as expected ("on demand")? To try in a
  test compositor once the library is there.
- The real memory in his session with two screens, and with the companions.
- Which graphics chip GTK and labwc draw on in his session. They must match (LAPTOP-HOME.md section 4).
- What the game does when the laptop home takes the keyboard on a click: package 40's rule (no pause menu while an
  app is in front) should hold for a layer surface too. The laptop trial checks it.
- Super pressed while the pointer is on the laptop screen: the world's search, or the laptop home's typing line?
  The lead's reading, to confirm with him at build time (JUDGMENT-CALL 5).
- How many frames a second the companions get (their package).
- Opening an app on the monitor from the laptop (for example Shift and click) would need one more field in
  `open_app`. Not in version 1. Super's search needs the same field if it opens over the world while the pointer is
  on the laptop screen.
- A dot on the Map table showing where he stands in the world would need the mod to say so. Left out.

## Review fixes 1

`REVIEW-1.md` (CHANGES-NEEDED) found 13 things. None changed the recommendation. Each is fixed in
`docs/design/LAPTOP-HOME.md`, here, and in the prototypes where it applies.

1. **A house's side came from a running count.** Fixed: side and slot come from the place (`slot = r(r+1)/2 + k`),
   a free place stays a gap, and `CELL` comes from the farthest slot. Night street's own check covers a town with
   one hole.
2. **The nonce changes with each game start.** Fixed: the laptop home gets a token of its own for the session,
   accepted for views only, and connects again after a helper restart. In between: the last town, with opening off.
   Who makes the token is a PLAN-GAP (the supervisor, package 23c, `linux-aresos`).
3. **The helper keeps more one-client state.** Fixed: a view's hello leaves the desktop's state alone, the journal
   is kept per client with a share of its own for views, each launch remembers who asked, and an unknown ID in
   `publish_home` drops one app.
4. **No answer past 16 apps in a group.** Fixed: the street slides, with end signs that count the houses out of
   sight (pictures 8 and 9, 45 apps). The report no longer says every app is always on screen.
5. **The way from the world.** Described: Esc (or E, or T) first. JUDGMENT-CALL 5 now says the key is the only way
   across without Esc.
6. **Typing missed generic names and keywords; the finder's group had no source.** Fixed: both are searched after
   the names, `pdf` finds Test Viewer by its keyword (picture 3), and the list shows the generic name, no group.
7. **The companions' cost was vague.** Measured: one companion-sized figure costs about a fifth of a core on one
   graphics chip. The study's two cores came from GTK and the compositor drawing on different chips.
8. **JUDGMENT-CALL 3 showed one side.** Fixed: picture 10 shows every logo in full colour. The question now says
   "slightly dimmed", and section 10 asks the report's six questions with their recommendations.
9. **The memory split.** Measured: 127 MiB working memory and 208 MiB mapped files, under 1 MiB shared memory.
10. **The caret blinked without end; the clock ticked every 10 seconds.** Fixed in the draft and the prototype.
11. **Test logos changed with the town's size.** Fixed: each logo comes from the app's ID.
12. **Long names never shown.** Fixed: signs wrap to two lines, and "Test Media Workbench" (20 letters) is in the
    24-, 40- and 45-app towns.
13. **Build notes.** Added: `LD_PRELOAD` for the layer library, the scheme's secure, CORS and MIME settings, the
    fallback placing itself on the `eDP` screen, and the token and `LD_PRELOAD` removed before the engine starts.

## The day look

The owner saw Night street and asked (2026-11-16): "why was night chosen, is it the best theme? Because the
superflat world isn't dark so do you think it fits as a homescreen? However, generally the app menu makes sense and
so does the search menu easy access. The apps don't necessarily have to be Minecraft houses but dimmed and light up
when used makes sense."

The answer, the comparison and the recommendation are `docs/design/LAPTOP-HOME.md` section 11. In short: night was
chosen for calm, for the house style and because a lit door needs the dark; the study never drew a day. The world
is fixed at noon (`FlatHome.java`). **I recommend day**, with night kept as the second look.

Pictures: [home](pictures/day-1-home.png), [finding "tool"](pictures/day-2-finding.png),
[an app opened](pictures/day-4-opened.png), [forty apps](pictures/day-6-forty-apps.png). They match `street-1`,
`street-2`, `street-4` and `street-6`.

**Done.**
- `prototypes/street/index.html`: `?look=day` puts the class `day` on the page.
  - What differs between looks became four variables (how a house that is not open is drawn, the two sign colours,
    how far the others fade while he types). Night sets them as before.
  - The day's rules are one block at the end of the style sheet: sky and grass, the road with its line down the
    middle, name plates, the open mark, the frame, the pad, the typing line, the ends of a long street.
  - The stars and their timer are made at night only.
  - The sign's width comes from the street's `--pitch` instead of a number on each sign, so the day can let a plate
    hug its text.
- `tools/shots.sh`: the four day pictures are in `all`; `all day-` makes only the names that start so; `check` runs
  both street checks on the day look too.
- `docs/design/LAPTOP-HOME.md`: section 11 "Day or night"; questions 1 to 3 of section 10 offer night or day.
- No other form for the apps was drawn (no `day-alt-tiles.png`). Section 11.3 says why: the laptop gets each logo
  with its doorway built in, so a flat tile is the same front minus its edge.

**Verified.**
- `tools/shots.sh all street-` after the change: the ten night pictures are the same files as before, byte for
  byte (git shows no change), so night is untouched.
- `tools/shots.sh all day-` made the four day pictures, each 1920 x 1080, in the headless compositor.
- `tools/shots.sh check`: 10 of 10 on each of the three pages and 9 of 9 on Night street's own check, as before;
  on the day look 10 of 10 and 9 of 9.
- A 45-app day town with `tool19` typed was looked at once (the street slides, its end fades into the grass); no
  picture of it was kept.
- The world's time was read in `mod/src/main/java/dev/aresos/world/FlatHome.java`: the day cycle is off and the
  clock is set to noon once, when the world is made.
- **The cost at rest** (`tools/shots.sh measure`, 40 apps, two open, 100 seconds; other builders' programs were
  running on the laptop meanwhile):
  - Day 0.33 % and 0.35 % of one processor core, night 1.37 %. The night's difference is the star that changes
    every four seconds; the day has none.
  - Cut into 10-second slices, the day page's own process used 0.0 to 0.2 % in every slice.
  - Working memory 128 MiB by day, 128 to 136 MiB at night. In all (PSS) 255 to 322 MiB over five day runs and 307
    to 342 MiB over four night runs; the difference is in the share of library files, which also moved between
    runs of the same look.
  - With a fixed clock, a scratch copy of the check watched each page for 13 seconds: by day no animation ran and
    nothing in the page changed; at night three stars changed.
  - In two shorter day runs (30 and 60 seconds) the page's process used about 0.7 seconds of processor time that
    the other runs did not show. The two sliced 100-second day runs did not show it either. Not explained.

**Not verified.**
- How the day look feels beside the real monitor, on the laptop's own panel and in his room. These are pictures.
- Nobody used a real mouse or keyboard on it; the checks make their events inside the page, as before.
- The day colours are chosen by eye against the game's noon in the hub's test pictures (`reviews/36-town/`), not
  against his shader pack.

## The day look on one grid

The owner chose day (2026-11-16) and asked for a cleaner layout: "Yes day but it bothers me that the lines aren't
aligned. I think the all display or background should be slightly different because currently the not standardized
, unequally long app lines that don't line up with the sky / dirt cut line don't look clean or organized. I think
maybe the app logos could integrate more in the background or smth ?"

The rules, the two grounds that were drawn, the choice and what was rejected are `docs/design/LAPTOP-HOME.md`
section 11.6. Its sections 2.1 and 3 now describe this form. In short:
- All four streets stand on one grid. Their columns line up, every street has the same plots (a free place is a
  free plot), and every road runs from edge to edge of the screen.
- The ground is terraces: each street is a step of a hillside, and the line between sky and ground is the first
  street's own ground.
- **I recommended terraces; the owner chose them (board #332)** over the other ground that was drawn, one lawn
  with the sky ending above the first street.

Pictures: [home](pictures/day2-1-home.png), [finding "tool"](pictures/day2-2-finding.png),
[an app opened](pictures/day2-4-opened.png), [day one, five apps](pictures/day2-5-day-one.png),
[forty apps](pictures/day2-6-forty-apps.png),
[forty-five apps, one group of twenty](pictures/day2-8-forty-five-apps.png); the other ground:
[one lawn](pictures/day2-alt-home.png). The four `day-*` pictures show the day's first form and are kept for
comparison; the tool no longer makes them.

**Done.**
- `prototypes/street/index.html`:
  - `grid` gives each look its block size, its step and its middle. The night's are as before. The day's are whole
    blocks (a step of 14, a middle of 30), and a day street's strip is 202 high instead of 196.
  - By day: a row of plots on each side of every street, a still road from edge to edge, the terraces as one still
    background that the script paints, a slide by whole steps, and a mask that fades the houses at an end of a long
    street (the night keeps its fade to the wall).
  - `?look=day&ground=plain` is the other ground.
  - What slides of a street now sits inside a `view` element, which the day's mask needs. In the companions'
    snapshot a day road is one ledge across the screen that does not slide.
- `tools/webkit-shot.py`: the checks `check-grid`, `check-grid-long` and `check-rest`.
- `tools/shots.sh`: `all` makes the seven `day2-` pictures; `check` also runs the grid check on four pages and the
  rest check on the day look.
- `docs/design/LAPTOP-HOME.md`: section 11.6; 2.1's table and section 3 follow the day's new form, with the night's
  numbers at the end of section 3; question 1 of section 10 is answered.

**Verified.**
- `tools/shots.sh check`, eleven lines, all passed:
  - keys and clicks, 10 of 10 on each of the three pages and on the day look;
  - Night street's own check, 9 of 9 by night and by day;
  - the grid check, 9 of 9 on a day town of 1 app, of 24, of 45 with a group of 20 (its street slides and stays on
    the lattice), and on the lawn;
  - the rest check on the day look, 2 of 2: in 13 seconds no animation ran and nothing in the page changed. On the
    night page the same check saw three changes, the stars.
- `tools/shots.sh all street-` after the change: the ten night pictures are the same files as before, byte for
  byte (git shows no change).
- `tools/shots.sh all day2-` made the seven pictures, each 1920 x 1080, in the headless compositor. I looked at
  all of them.
- **The cost at rest** (`tools/shots.sh measure`, 40 apps, two open, 100 seconds; another builder's game test was
  running on the laptop meanwhile). The day's first form was measured again in the same hour:
  - The new form 0.32 % and 0.32 % of one processor core; the first form 0.32 % and 1.32 % (that run had the
    one-off 0.7 seconds in the page's process that "The day look" above describes).
  - One new-form run cut into 10-second slices: the page's own process 0.0 to 0.1 % in every slice, the window
    program 0.2 % (0.6 % in one).
  - Working memory 128 and 137 MiB for the new form, 136 and 128 MiB for the first. In all (PSS) 317 and 323 MiB
    against 324 and 321.
  - The lawn, one run: 0.25 %, 128 MiB of working memory.
  - The share of library files (187 to 214 MiB over the runs of both forms) was lower in runs during which another
    program with the same libraries ran. In the lawn's run it was 161 MiB, and during that run I made seventeen
    pictures with the same engine. PSS divides shared pages, so that is likely the spread the first day study
    could not explain. Not tested further.
  - Seen once, not explained: 1.5 seconds after loading, the terraces page had 184 MiB of working memory (the lawn
    and the night 133). After a measurement's 8 seconds of settling it was 128.

**Not verified.**
- How it looks on the laptop's own panel beside the monitor. These are pictures.
- His apps and their names. The test names are short; a real name will often take two lines, which the step's
  height now allows for.
- A real mouse and keyboard: the checks make their events inside the page, as before.
- The grid check reads where the page put its roads, houses and plots. It does not look at the picture's pixels,
  and I did not see it fail on a broken grid. The rest check I did see fail, on the night page.

## Review fixes 3

`REVIEW-3.md` (READY) asked for should-fix 1 to 5 before merging and sent should-fix 6 to the build brief. Then the
owner answered question 5 directly (board #333). One Claude agent on Opus 5.5 applied both, 2026-11-16.

**Done.**
1. **The gold frame after a slide by hand** (finding 1). In `prototypes/street/index.html`, `follow()` now snaps
   the street by day into the interval of offsets that show the whole house, as the reviewer tried it. Before, it
   rounded away from zero, and after a click on the left end sign `test-tool-14` stayed off the right edge. Night
   is the same expression as before. `tools/webkit-shot.py`: `check-grid-long` gains the case. It clicks the left
   end sign of the street of 20, types `tool14` and expects that house in view and the street on the lattice.
2. **Answered questions no longer read as open** (finding 2). In LAPTOP-HOME.md: the title and status line, 2.1's
   dimmed row, question 3's "the same question stands", section 9's "night if it is kept", and 11.4's pointer to
   the night look. REVIEW-2's nit 8 wording ("without first freeing the pointer in the game") is used where the key
   is described.
3. **Question 5** (finding 3). The owner answered it directly (board #333). Section 10 and JUDGMENT-CALL 5 now quote
   that answer, and they say his earlier words had been read as yes.
4. **His change to the key.** Super opens a search bar over the world, on the screen that shows it, not the
   laptop's typing line. Sections 1, 2.2 and 6 say so. Section 9 has a new step 5, with the labwc keybind, the
   world getting the keyboard and the mod's search, and the trial is step 6. The way an app opened with the key
   appears (REVIEW-2's should-fix 2) is now part of it: on the world's screen, where his pointer is. What was
   planned for the old reading is gone: the typing line on the top layer, and the game losing the keyboard to it.
   Open, as the lead's reading to confirm at build time: Super with the pointer on the laptop screen.
5. **This report** (finding 4): JUDGMENT-CALLs 1 to 6 carry their answers, "In short" has the owner's choice, the
   terraces are his choice on my recommendation, and the pictures are 28.
6. **Memory** (finding 5). Section 4 gives one statement with its sources. It says about 335 MiB unpinned (this
   study) and about 150 to 180 MiB with the EGL and Vulkan vendor pinned. The second number is the research's:
   `reviews/49-memory-cuts/RESEARCH.md` on `pkg/49-memory-cuts`, `fc1d31de`, until package 49 merges. The pin is
   now a rule for the window program: `__EGL_VENDOR_LIBRARY_FILENAMES` names Mesa's file and `VK_DRIVER_FILES`
   names Intel's. The line saying NVIDIA's libraries are not loaded on the Intel chip is gone, and the same claim
   here is marked corrected.

**Verified.**
- The new case fails on the old page: `check-grid-long` passed 9 of 10 in a scratch copy with the previous
  `index.html`, and `typing_after_a_hand_slide_shows_it` was false.
- `tools/shots.sh check`, eleven lines, all passed: keys and clicks 10 of 10 on street, map, console and the day
  look; Night street's own check 9 of 9 by night and by day; the grid check 10 of 10 on the towns of 1, 24 and 45
  apps and on the lawn; the rest check 2 of 2.
- `tools/shots.sh all street-`: the ten night pictures are the same files, byte for byte (git shows no change).
- The seven `day2-` pictures, made again in a scratch copy with the fix, are byte-identical to the committed ones,
  so they were not made again here.

**For the build brief.** Found in the reviews and not fixed in the study. LAPTOP-HOME.md section 9 has the same list.
- **Two breaks the day's grid check does not see** (REVIEW-3, finding 6):
  - one street with an extra plot past `EDGE`: expect each street's plot count to equal `cols`, unless that street
    has a house past `cols`;
  - the terraces drawn off their streets: check the ground against the streets, by deriving the turf and bank stops
    from the same numbers, or by sampling the picture's pixels at each street's turf row and road row.
- **REVIEW-3's nits:**
  - "equally long with 1 app and with 45": a street past 16 runs off the screen, so "equally long on the screen,
    except a street past 16";
  - the rest check does not see a canvas drawn again every frame: for the companions, count frame callbacks too, or
    keep the processor measurement beside it;
  - `shots.sh check` exits 0 when a check fails: the build's tests fail on a non-empty `wrong`;
  - a framed house beside a cut end sits in the day's fade (18 to 120 pixels): fade from `EDGE/2` to `EDGE`
    instead.
- **REVIEW-2's nit 7**, which holds by day too: while typing, an end sign could count how many of its hidden houses
  match; and the companions' ledges and boxes jump by the whole offset while the houses glide for 0.3 s, so the
  snapshot should give the street's current offset each frame.
- **REVIEW-2's should-fix 1 and 3**, which its commit sent to the build brief (`ac466139`): the return of focus
  decided by screen, not by who opened the app, with its test; and each motion set-up's environment with what its
  numbers leave out. Should-fix 3's memory part is closed by LAPTOP-HOME.md section 4's "Memory".
