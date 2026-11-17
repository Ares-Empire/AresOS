Verdict: CHANGES-NEEDED

# Package 44, the laptop-screen home: review 1

Reviewer: a fresh Claude agent on Opus 5.5 that did not build it, 2026-11-16. Read-only. Head 603d966b (PR #88).
Read: the brief, `PROGRESS.md`, `docs/design/LAPTOP-HOME.md`, all three prototypes and both tools, 9 of the 14
pictures (street 1 to 7, map 1, console 1). Checked against HUB.md (1, 2, 3.1 to 3.8, 5), OS-BASE B1, the app
helper, the supervisor's nonce handling, `rc.xml`, `AppGroup.java`, EMPIRE.md "The crown language" and the
companions runtime README. Nothing was started: no browser, no WebKit, no compositor.

The owner can choose from this study now. Night street is a good, well-argued direction, and the pictures show it
clearly. The draft is not yet something a build package can follow without building bugs. Two rules in it are wrong
against the real code and the world (findings 1 and 2). Several things a build will meet are not decided (3 to 6).
All of them are changes to the text of the draft. None changes the recommendation.

## Findings

### 1. Blocking: a house's side comes from its position in a compacted list, so one empty place flips a whole street

**Where:** LAPTOP-HOME.md section 3 ("House number `i` … Even `i` stands left", "Order within a group"). The prototype
does the same thing: `street/index.html`, `list.forEach((app, i) => … i % 2 …)`.

**What's wrong:** In the world, places have holes:
- a removed app keeps its place free (HUB 2.5);
- a place with something of his on it is skipped (2.5, 3.3);
- `/aresos app move` and `swap` move apps between places (2.5).

Section 3 numbers the apps one after another, nearest first, and the number decides the side (even means left). So
when one place empties, every house after it changes sides. Take the app at `N0L0` away: `N0R0` jumps to the left,
`N1L0` to the right, and so on along the whole street. This breaks the draft's own promise, "Nothing else has moved"
(section 1, and the report's "nothing else moves, as in the world"). It also puts an app on a different side from
where it stands in the world. The test towns have no holes, so the pictures don't show it.

**Fix:** Work out the house from its place, not from a running count:
- the side is the place's L or R;
- the slot on that side is the place's rank among that side's places in HUB 3.3's order (`N0L0`→0, `N1L0`→1,
  `N1L1`→2, `N2L0`→3 …, so slot = r(r+1)/2 + k).

A free place either stays a gap, as it does in the world, or that side alone closes up. Pick one and write it down.
Work out `CELL` from the farthest slot used on any side, not from `ceil(most / 2)`. Add a check, or a picture, of a
town with one hole.

### 2. Blocking: the laptop home's way of proving who it is stops working whenever the game restarts

**Where:** LAPTOP-HOME.md section 5 ("A view presents the same `instance` and `nonce` as the desktop") and the end of
section 5 ("Opening still works: it only needs the helper"). Section 6 "Start".

**What's wrong:** The nonce is not fixed for the whole session. Each start of the game gets a new one. In
`aresos-desktop`, `ensure_helper()` stops the app helper and starts it again with the new nonce. After any game
restart (a crash, a relaunch) the laptop home therefore:
- loses its connection;
- still holds the old nonce, so its next `hello` is refused with `not_authorized` and the connection is closed;
- can't open apps until something restarts it.

Section 6 also allows only three restarts before it gives up for the session. Ordinary game restarts could use those
up.

**Fix:** Pick one and write it down:
- **(a) Recommended:** the supervisor makes one token for the whole session (for example `ARESOS_VIEW_TOKEN`) and
  gives it to both the helper and the laptop home. The helper accepts it for `"role": "view"` only. The helper then
  knows a view by what it holds, not by what it says it is. A view can never be taken for the desktop or throw the
  game off.
- **(b)** The supervisor restarts the laptop home with each new game start. Those restarts don't count against its
  restart limit.

Either way, say what the laptop shows in between: the last town it had, with opening switched off for those few
seconds.

### 3. Should-fix: the helper keeps more one-client state than section 5 lists

**Where:** LAPTOP-HOME.md section 5, "A view". Checked against `os/config/usr/libexec/aresos-shell`.

**What's wrong:** The draft says a view doesn't replace the desktop and never counts for readiness. The code shares
more than that:
- **`hello` changes things for the whole helper** (lines ~3007 to 3046):
  - it sets `window_minor`, the rules for which windows belong to which program, from the client's version;
  - it calls `cancel_returns()` for a 1.0 client;
  - it sets `windows_pending`;
  - it writes `desktop_connected` to the supervisor's status pipe.

  A view's hello must do none of these.
- **One launch journal for everyone.** Launches are recorded by request ID alone (`journal.entries[request_id]`,
  `checking[request_id]`), and the journal holds at most 256 (`JOURNAL_LIMIT`).
  - B1's duplicate rule means a view that reuses a request ID the game already used gets the game's earlier launch
    back. Nothing opens.
  - A busy view can fill the journal, and then the world's opens fail with `journal_full`.

  The game's IDs carry a random session part (`ShellClient`: prefix, session, counter). Nothing in the draft makes a
  view do the same.
- **`app_state` reaches only the desktop.** `emit()` sends to `self.desktop` only. "`app_state` for its own launches"
  needs each journal entry to remember which client opened it. The journal is saved, so that has to survive a helper
  restart too.
- **An ID in `publish_home` that the helper no longer lists:** the draft doesn't say what happens to it.

**Fix:** Add these rules to section 5:
- a view's hello leaves the desktop's state alone (window rules, returns, status line);
- journal entries are keyed by client role and request ID, and views get a share of the limit of their own;
- each launch remembers who opened it, and only that client gets its `app_state`;
- an unknown ID in `publish_home` drops that one app, not the whole town, so an uninstall that happens during a
  publish can't empty the laptop screen.

### 4. Should-fix: past 16 apps in one group, Night street has no answer, and the report says every app is on screen

**Where:** LAPTOP-HOME.md section 3 ("More than 16 apps in one group is not designed"). PROGRESS.md
"Recommendation" ("Every app of his is on the screen") and "Open questions".

**What's wrong:** Checked against section 3's formula:
- houses are 120 / 108 / 96 / 84 pixels wide at 10 / 12 / 14 / 16 apps in the biggest group (as stated);
- at 17 or 18 apps in one group, the outer houses are cut off at both screen edges (by about 54 pixels at 18);
- from 19 on they are entirely off screen and can only be reached by typing.

How likely that is:
- HUB.md's planning mixes put 14 of 40 apps and 34 of 100 apps in the biggest group. System & Tools is always the
  biggest, and 42 of the laptop's 61 programs are System & Tools (HUB 5).
- My apps has no upper limit. The inventory's 27 slots plus the hotbar make 36 items, but apps past that keep their
  logos (HUB 2.4).

So Night street holds about 45 apps in HUB's own mixes, and fewer when one group grows faster. A build that follows
the draft will meet this, and the owner is told every app is always on screen.

**Fix:**
- State the limit in the recommendation: all apps visible up to 16 in a group, about 45 apps in a typical mix.
- Give section 3 one fallback the build can follow. For example:
  - shrink to `CELL` 5 (22 per group), with names shown under the pointer only;
  - or make the outermost slot a "+N" sign that opens the typing line filtered to that group.

### 5. Should-fix: while he is in the world, the game holds the pointer, and the draft doesn't say how he gets to the laptop

**Where:** PROGRESS.md "What he does" ("He moves the pointer down to the laptop and clicks a house"). LAPTOP-HOME.md
sections 1 and 6, and question 4 in section 10 (JUDGMENT-CALL 5 in the report).

**What's wrong:** In the world, Minecraft captures the mouse. HUB.md (package 40): "The game lets go of the mouse while
an app is in front and captures it again when the world has the focus back." With the world on the monitor and in
focus, he can't move the pointer to the laptop. He first has to press Esc (or E, or T), or be in an app already. The
main way of using the laptop home works well while he is working in apps on the laptop. From inside the world it needs
an extra step, and the draft never mentions it.

**Fix:** Describe the way from the world to the laptop home in sections 1 and 6. Then look at JUDGMENT-CALL 5 again:
the Super key would be the only way across without Esc. That is a stronger reason for it than "launcher of the whole
session", and the question should say so.

### 6. Should-fix: typing can't find the program in the draft's own example, and the group shown for other programs has no source

**Where:** LAPTOP-HOME.md section 2.2 (the order of hits), section 1 ("He types `pdf`"), and section 4 (`programs()`).

**What's wrong:**
- **The search.** Section 2.2 matches names and short names only. A real PDF reader is usually found by `pdf` only
  through its `GenericName` or `Keywords`. HUB 2.4's Apps screen searches those for exactly this reason ("so 'mail' or
  'pdf' finds the right program"), and the helper already lists them (`generic_name`, `keywords`). The test program
  happens to be called "Test PDF Viewer", so the prototype hides the gap.
- **The group.** `programs()` promises each program's group, and the finder list shows it (picture street-3). But the
  groups are worked out by the mod (`AppGroup`), and `publish_home` carries My apps only. As written, the window
  program would have to classify programs itself, which is the second classifier the draft is trying to avoid.

**Fix:**
- Add generic name and keywords to the search, ranked after names, and to `programs()`.
- For the group, either have the mod publish every program's group or show no group in that list.

### 7. Should-fix: the cost of the companions' motion is left vague, yet the recommendation rests on them

**Where:** PROGRESS.md "Recommendation" ("The companions fit as they are"), "Tech and memory" (the 220 % row) and
"Open questions". LAPTOP-HOME.md section 7 ("they move without being asked; that costs what the study measured").

**What's wrong:** The study's only measurement of motion is ten stars that never stopped twinkling. They made the
engine redraw the page 60 times a second and kept two processor cores busy. Companions move without stopping. Section
7 reads as "companions will cost two cores", yet nothing was measured for them. A small see-through canvas being
redrawn is a very different load from a full page with 24 to 40 dimmed logo canvases. The owner can't tell whether the
web choice holds for the companions version. That version is the reason for choosing a web engine at all.

**Fix:** Pick one:
- measure it: one companion-sized sprite moving on a see-through canvas over the town, with
  `tools/shots.sh measure`;
- or say plainly in "Open questions" and in section 7 that the processor cost of the companions version on this
  engine is unknown. It is the main risk of the web choice. Give the reasons it may be much lower: only their canvas
  is redrawn.

### 8. Should-fix: JUDGMENT-CALL 3 shows one side only, and section 10 doesn't match the report

**Where:** PROGRESS.md JUDGMENT-CALL 3, LAPTOP-HOME.md section 10, and the pictures.

**What's wrong:**
- **One side only.** He is asked "dark houses that light up when open, or every logo in full colour". Every picture
  shows only the first. The dimming is gentle: 62 % brightness and 82 % saturation, and the 82 % is not mentioned in
  section 2.1. In street-1, open and closed houses differ mostly by the light in the doorway, so "dark houses" says
  more than the pictures show. He can't answer from what he sees.
- **Two lists that don't match.** Section 10 asks 4 questions with no recommendations. The report has 6
  JUDGMENT-CALLs, each with a recommendation.

**Fix:**
- Add one picture: the 24-app town in full colour. It is one CSS number, for example a `?bright=1` option.
- Word the question the way the pictures look ("slightly dimmed" against "full colour").
- Give section 10 the report's recommendation for each question, and make the two lists match (or have section 10
  point to the report).

### 9. Nit: the memory split is explained more confidently than it was measured

**Where:** PROGRESS.md "In short" and "Tech and memory" ("about 125 MiB is its own and the rest is library code
shared with other programs"). LAPTOP-HOME.md section 4.

**What's wrong:** PSS already divides memory that is shared with other programs among them. The other ~207 MiB is
memory charged to this program: its program files and its shared buffers. Few other programs in his session load
WebKitGTK. The tool records only `Pss`, `Rss` and `Pss_Anon`, so how much of that is library code was never measured.

**Fix:** Either:
- record `Pss_File` and `Pss_Shmem` too (`smaps_rollup` has both);
- or reword: "333 MiB in all; 126 MiB of it is working memory, the rest mostly the engine's program files and
  graphics buffers".

The headline 333 MiB and the `MemoryHigh=640M` suggestion stand.

### 10. Nit: the "nothing moves" rule isn't fully kept

**Where:** LAPTOP-HOME.md section 2.4 and the prototype.

**What's wrong:**
- The typing caret blinks without end for as long as typed text stays in the line (`home.css`:
  `animation: caret 1.1s steps(1) infinite`), against "No blinking".
- The clock checks every 10 seconds rather than once a minute (`setInterval(tick, 10000)`).

**Fix:** In section 2.4, say that the caret stops blinking after a few seconds and the typed text clears when the
laptop home loses the keyboard.

### 11. Nit: the test logos change with the size of the town

**Where:** `shared/home.js` (`logoCells(index * 3 + gi)`; `index` counts across the whole mix).

**What's wrong:** "Test Game 1" has a different logo in the 5-, 24- and 40-app pictures. Anyone comparing day one
with forty apps sees houses change, which works against "nothing else has moved".

**Fix:** Pick each logo from the app's ID.

### 12. Nit: long names are never shown

**Where:** the pictures and `street/index.html` (`name.style.maxWidth = pitch - 6`).

**What's wrong:** The test names are at most 12 characters. With 13 to 16 apps in a group, a name gets about 96 to
111 pixels before it is cut off with "…". In the world, the signs wrap onto a second line instead.

**Fix:** Add one test app with a 20-letter name, so he sees the cut-off, or let the signs wrap to two lines.

### 13. Nit: things the build will need, worth a line each in sections 4, 6 and 9

- **The layer library from Python.** `gtk4-layer-shell` must be loaded before `libwayland-client`. Its own notes
  give `LD_PRELOAD` for Python. Without that, the layer surface silently doesn't happen.
- **The page's own address scheme.** The `aresos-home:` scheme must be registered as secure and CORS-enabled, and
  JavaScript must be served as `text/javascript`. Otherwise module imports and `fetch` fail, which is the very reason
  for having the scheme.
- **The fallback window rule.** `MoveToOutput` needs the output's name (`eDP-1` or `eDP-2`), which a fixed `rc.xml`
  can't know. The program can place itself full-screen on the `eDP` monitor instead.
- **The secret in the environment.** The window program should take the token or nonce out of its environment before
  WebKit starts its own processes, which inherit it. The page never sees it either way; this keeps it out of the
  engine's processes too.

## What I checked and found right

- **The brief is covered.**
  - Three directions, clickable, at 1920 x 1080, with no network and no build step.
  - Test apps only, and 14 pictures from WebKit in a headless compositor.
  - PROGRESS.md covers every part the brief asks for.
  - LAPTOP-HOME.md is marked "draft, waiting for the owner's choice".
  - The recommendation fits his words: functional first, not a launcher grid, light, and it fits the town without
    being a picture of it.
- **HUB.md facts are used correctly.**
  - **Groups, directions and order:** Internet north, Games east, Work & Media west, System & Tools south, as in HUB
    2.2 and the `AppGroup` enum.
  - **Name colours:** exactly `AppGroup`'s `0x3AB3DA`, `0xFF6257`, `0xC774F2`, `0xFED83D`.
  - **Signs:** the group name hangs between the two front logos, with direction and count. On each house the name is
    white and the short name gold.
  - **Logos:** the doorway is columns 5 and 6, three high, with posts and a bar over it (3.6, step 6), and the logos
    are 12 x 12.
  - **Place order:** `place()` in `home.js` gives HUB 3.3's order (`N0L0`, `N0R0`, `N1L0`, `N1R0`, `N1L1` …).
  - **The map:** it places logos with HUB 3.2's numbers (`FIRST` 4, `PITCH` 14, `ROW0` 20, `STEP` 14). Its 84 and
    72 pixel logo sizes at 24 and 40 apps follow from its own formula.
  - **The crown language:** near-black wall, the Mars-red and steel-blue glow, Space Grotesk and JetBrains Mono, gold
    as an accent (EMPIRE.md).
- **The technical claims hold.**
  - The image's package list (06c) has `webkitgtk6.0` 2.54.1, `gtk4` and `python3-gobject`. `gtk4-layer-shell` is
    neither in the image nor on the laptop. The start-up cover is already GTK 4 in Python.
  - The helper's real limits are stated rightly:
    - one desktop connection, and the newest authenticated hello wins;
    - the helper knows nothing of My apps, short names, places or pins;
    - it never sends a command or path other than `icon`.
  - A second client doesn't weaken the helper's checks. The socket is mode 0600, the peer's user is checked
    (`SO_PEERCRED`), and the helper's own notes say the nonce is "not a security boundary against other programs of
    the same user". The page never sees the socket, a command, a path or the nonce. A picture is served only from the
    path the helper gave for that app ID.
  - The PLAN-GAP is correct: `rc.xml` has no `skipWindowSwitcher` for `aresos-desktop`.
  - The layer-surface reasoning is right: such a surface is not in Alt+Tab, Alt+F4 can't close it, and the helper's
    window tracking never sees it. Keyboard focus on a click is honestly listed as untried.
- **The measurements were made the way the report says.**
  - The memory is the sum of PSS and anonymous PSS from `smaps_rollup`, over the program and its child processes.
  - The engine used a throw-away network session.
  - The compositor was a headless `cage` with his display variables removed, and the tool refuses to start without
    its own marker or on `wayland-0`.
  - The idle processor figure is processor time over the time watched.
  - At rest the page changes only one star every 4 seconds and the clock. Motion is otherwise an answer to him (a
    0.6-second puff, 0.15-second hover fades), except for the caret (finding 10).
- **The companions' shape fits.** The prototype's `laptopHome.world.snapshot()` gives what the runtime README's
  "World provider" asks for: surfaces with id, owner, kind, x1, x2, y and room, plus occluders and a floor.
- **The repo stays clean.**
  - Nothing under `os/` or `mod/` changed.
  - No names of his installed programs appear in the new files. The only mention is the brief's own rule line.
  - The logos are drawn from 16 hand-made signs, with no app icons and no game textures. The pictures are page
    renders, not his screen.
  - Both fonts are under the OFL with their licence texts. The Space Grotesk file is byte-identical to the image's
    (same sha256).
  - The pages load nothing over a network, and every prototype and tool is labelled as a development aid.
- **The JUDGMENT-CALLs are his calls.** They are about how it feels, one look or several, what else is on the
  screen, and a reserved key. Each has a recommendation in the report. Findings 5 and 8 are about how two of them are
  put to him.
