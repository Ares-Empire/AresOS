# The home's parts outside the game

**Status.** Design note for board brief 332, written 2026-11-21 by one Fable design agent with read-only tools.
Revised the same day after review 1 (`reviews/332-outside-game-design/REVIEW-1.md`, NOT READY), with
`linux-desktop`'s OS part and the owner's four answers (`reviews/332-outside-game-design/INPUTS-1.md`). Nothing here
is built. It decides the structure for the hub (`linux-hub`), the desktop (`linux-desktop`) and the supervisor
(`linux-aresos`).

**What this revision changed**

- The three blocking findings: what every stop does to a sleeping world (section 9), an off world that nothing
  starts but his own switch (section 6), and how the world gives way when memory is full (section 12).
- Every "should fix" finding, and the false claims about today's code (section 3).
- The owner's answers: a plain default picture, both bars stay, a bar on every screen. The package "One bar" is gone.
- `linux-desktop`'s layers, strip, covering rule and scaling (section 12), and the rest of the note agrees with them.
- The migration order: the switch ships before the bar (section 10).

**Sources.** The documents and code the brief names, as they are in this checkout. Nothing was run and nothing was
measured; every number names where it comes from. labwc's own behaviour, the image's systemd-oomd settings and
`briefs/328-look-around.md` could not be read here. What rests on them is marked.

**Words used below**

| Word | Meaning |
|---|---|
| The world | The Minecraft home: the game, its window (`aresos-desktop`) and the mod. |
| The helper | `os/config/usr/libexec/aresos-shell`. "Helper `:N`" is line N of that file. |
| The supervisor | `os/config/usr/libexec/aresos-desktop`. "Supervisor `:N`" is line N of that file. |
| The native home | One program that draws the picture, the bar, the search and toasts without the game. It grows out of `os/config/usr/libexec/aresos-laptop-home` ("laptop home `:N`"). Working name: `aresos-home`. |
| Home output | The screen the world shows on, or would show on (package 23c's rule). |
| Covered | An output with a maximized or full-screen window that is not minimized: today's rule, applied per output. A full layout counts once the covering package ships (T372/T373). |
| Still | A picture of the world's last frame, made by the mod, kept in his cache folder. |
| Sleep record | The supervisor's durable note that a launch was saved and has not run since (section 9). |
| Drop | Ending a game whose sleep record is open, without a thaw. Nothing is lost by it (section 9). |

---

## 1. The decisions in short

1. **The home has three layers.** The helper holds the facts. The native home shows what must show without the game.
   The world is the third layer, and it is optional.
2. **One native program, always running.** It draws the picture, the bar, the search and toasts. A GTK program costs
   about 50 MiB each, so these are surfaces of one program.
3. **It is the laptop home, grown.** That file is split into modules first. `linux-desktop` leads the program and
   the hub leads its content modules.
4. **The helper lives as long as the supervisor.** Today it is started for each game launch. It must run with no
   game at all, and its restarts must never stop for good.
5. **The helper is the one source** for programs, My apps and pins, windows and outputs. `aresos-shell/1.3` adds
   `apps_state`, `activate_app`, `screens`, the window list, and search for a view.
6. **A left click means "open or bring back" everywhere**: bar, hotbar, gate, `/name`, search. "New window" is a
   right click on the world's hotbar slot and a row in the outside bar's menu.
7. **Both bars stay** (the owner, T483). In the world: the game's own hotbar, with open and active marks. Wherever
   the awake world is not in view: the bar outside.
8. **A bar on every screen** (the owner, T484 and T485). It is visible on a screen where no window shows. It waits
   at the bottom edge while one does. A visible bar never stands over a window (question 4).
9. **Search is outside the game.** Super opens it over anything, on the home output. Nothing is minimized for it.
10. **The picture is a background surface** on every output where the awake world is not showing. The default is a
    plain picture in the look (the owner, T482). Black, a picture of his and the town are the other kinds.
11. **World off closes the game and Prism.** It is a setting and holds across restarts. In OFF nothing starts the
    world but his own switch.
12. **A sleeping world is never a frozen window on screen.** The order is: still, pause, minimize, save, record,
    freeze.
13. **One rule for a sleeping world.** While its sleep record is open, nothing is asked of the game, and every stop
    drops it. A drop is not a crash and is never latched `killed`.
14. **The world gives way first, by the supervisor's own hand.** A wake is admitted only when memory allows. Under
    pressure the supervisor drops a sleeping world before the system has to kill anything.
15. **There is always a way back.** Section 12 has the chain. Its last link is a message window, never a start.

---

## 2. What he will see

- **Working in a full-screen app.** The bar is hidden. He moves the pointer to the bottom edge and rests there for
  a third of a second. The bar slides up over the app. Chrome's slot is marked open and lit as active. He clicks
  Terminal: its window comes back. The pointer leaves the bar and the bar slides away.
- **Building with the world off.** He turns the world off. The world is saved and closed. The screen shows a plain
  picture in the look, or black, or his own picture. Super's search, the bar and every app work as before. About
  1.4 GiB is free again. The world stays off until he turns it on.
- **With the monitor plugged in** (package 23c's plan). The world moves to the monitor. The laptop's screen shows
  the picture behind its apps, with its own bar.
- **The world asleep.** Its last view stays on screen, and the bar stands where the hotbar stood. A click on the
  view brings the world back to life. On a full laptop a line says the world is waiting for memory, and his apps
  stay.

---

## 3. Today, from the code

Facts read in this checkout. They are why the three wishes cannot be met by settings alone, and what the new
states must fit into.

| Fact | Where |
|---|---|
| The helper is started for each game launch, with that launch's nonce in its environment. Without a launch it is not started. | supervisor `:1988`, `:2005-2009`; helper `:4705-4710` |
| The helper dies with the supervisor. Its restarts end after five failures in a minute, until the next launch. | supervisor `:3804-3805`, `:2036-2048` |
| The supervisor's one packet to the helper (`windows`) is a plain write, read 64 bytes at a time, with no acknowledgement. | supervisor `:3809-3816`; helper `:4602-4615` |
| `open_app` always starts a launch. No request brings an app's window back. | helper `:3599-3655`, `:3689-3733` |
| The helper's window client can activate and minimize a window. It cannot bring one back or close one, reads no titles, and binds outputs at version 1, without names. | helper `:2847-2850`, `:2866-2876`, `:2942-2962` |
| Which apps have windows goes to views only (`apps_running`). The mod hears only about its own launches (`app_state`). | helper `:3354-3364`, `:3816-3821` |
| Covering is judged only for the world's outputs, and only while the world's window exists. | helper `:2705-2707` |
| An activated world means "he wants the world": the helper minimizes what covers it. Super's route activates the world's window. | helper `:4134-4147`, `:4274-4275` |
| The home the mod publishes is kept in memory only. | helper `:3094`, `:3514-3526` |
| The supervisor's states are SETUP, STARTING, IN_WORLD, AUTH_REQUIRED, RECOVERY and STOPPING. Its command list has no `search`, no world switch, no freeze. Its private environment list has no view token. | supervisor `:328-329`, `:4783-4785`, `:182-184` |
| A stop asks the game to save and then sends SIGTERM. The supervisor never sends SIGKILL. A plain stop without a confirmed save is called off; a shutdown closes anyway and latches `unsaved`. | supervisor `:3323-3355`, `:3380-3399`, `:79`, `:3370-3378`, `:3629-3633` |
| A launch that ends while an open stop record names it is `stopped`: never counted, restarted or latched. | supervisor `:2388-2391`, `:3638-3659` |
| Any other end by SIGKILL latches `killed` and opens the recovery window. `retry` then waits for a full minute of clear memory pressure, sampled only while that latch holds. | supervisor `:2408-2420`, `:225-232`, `:2490-2492`, `:2589-2601` |
| The game's scope sets `MemoryHigh` and `TimeoutStopSec` and nothing else. It has no kill preference. | supervisor `:1059-1060` |
| A restarted supervisor adopts a running game as STARTING and shows `slow_start` after 120 s without readiness. | supervisor `:1855-1877`, `:2554-2558` |
| The instance keeps Prism open: `CloseAfterLaunch=false`, `QuitAfterGameStop=false`. A later `--launch` is handed to a Prism that already runs. | supervisor `:572`, `:1053-1055` |
| The world's window is maximized, frameless and always below. Alt+Tab lists it. `rc.xml` binds no lone Super; its one Super chord is Super+Ctrl+Escape. It has no `<mouse>` section, and nothing sets a background colour. | `os/config/usr/share/aresos/labwc/rc.xml:20`, `:22`, `:34-38`; `os/config/usr/share/aresos/labwc/autostart` |
| A hotbar click and the search's Enter end in `open_app`. The search is a game screen and needs a ready world. A 1.2 mod frees the mouse on any `background`. | `mod/src/client/java/dev/aresos/client/HomePointer.java:46`, `WorldSearchScreen.java:125-127`, `ShellFocusClient.java:61-65` |
| The laptop home is on main: GTK 4 and Cairo, view `laptop-home` pinned to minor 2, a town model with hotbar slots, a finder. Its picture decoder is pure Python, for icons up to 512 × 512 within 5 s. Without the layer library it falls back to a full-screen window. Nothing starts it yet. | laptop home `:492-495`, `:36`, `:200`, `:270`, `:598-603` |
| `aresos-settings` holds three lists of values. When it writes, it drops names it does not know. | `os/config/usr/libexec/aresos-settings:19-23`, `:60-68`, `:110-115` |
| A layer-shell piece in the look already exists: the indicator, with the look pack and `aresos-settings`. | `briefs/320-indicator.md` |

---

## 4. Where each part lives

| Part | Lives in | Content by | Surface and look by | Why |
|---|---|---|---|---|
| The bar's content: slots, marks, what a click does | The helper (the facts) and the native home's bar model | hub | | One model for every bar. |
| The bar's surface | The native home: `aresos-bar` and its strip `aresos-bar-edge`, per output | | desktop | It must show with the world off, asleep or covered. |
| The in-game hotbar | The mod | hub | the game | It stays (the owner, T483). It gets the marks and the left-click rule. |
| Search | The native home: `aresos-search`, opened by Super | hub | desktop | It must work over a full-screen app and with the world off. |
| Launching | The helper | hub | | It is there already and stays the only place that starts a program. |
| The open-app list and its marks | The helper works them out. Both bars draw them. | hub | | One answer to "what is open". |
| The app options menu | The native home: popups on the bar. In the world a right click on a hotbar slot is "New window". | hub | desktop | One menu. The game gets none of its own. |
| The picture behind the windows | The native home: `aresos-picture`, per output | desktop; the town is the hub's | desktop | Needed in three cases: world off, world asleep, second screen. |
| The still | The mod makes it; the native home shows it on the picture | hub | | Only the game can draw its own frame without windows on top. |
| Toasts | The native home: `aresos-toast` | hub for AresOS's lines; desktop for system notifications later | desktop | They must show over apps and with the world off. |
| Status icons (Wi-Fi, battery, sound, clock) | The native home, as part of the bar | desktop | desktop | The bar is on every screen and reachable over every app. |
| The world-off switch | A setting. The supervisor applies it. | hub (behaviour), aresos (supervisor) | | The supervisor alone may stop and start the game. |
| The indicator, the overview | As COMPONENTS.md says | desktop | desktop | Unchanged. |

### The native home

- **One program, in a scope of its own** (`aresos-home.scope`), started by the supervisor at the session's start. It
  runs in every state of the world and is never part of readiness. It outlives a supervisor restart; the new
  supervisor finds it by its unit name and starts no second one.
- **Its restarts never stop for good.** After it ends: 2, 10 and 30 seconds, then every 60. LAPTOP-HOME.md's "then
  no more in this session" ends, because with the world off this program holds the bar and the search.
- **Why one program.** The laptop home measured 52 MiB with one picture and 61 MiB after a redraw
  (`docs/design/LAPTOP-HOME.md:327-328`). Five such programs would be about 250 MiB at rest. The owner called
  300 MB "crazy much" for a home screen.
- **Why the laptop home.** It already has the view connection with its token, reconnecting, a sandbox for decoding,
  a model with hotbar slots and a finder with seven kinds of hits.
- **What changes in it.**
  - More than one output; a bar surface apart from the picture; the finder as an overlay; static pictures.
  - Its own hotbar, typing line, clock and battery leave: the bar and the search replace them on every screen.
  - Its own copy of the last home leaves: the helper keeps the home on disk (section 5).
  - **No fallback window.** Today it falls back to a full-screen window (laptop home `:598-603`). The new program
    draws nothing and exits without the layer library, as the indicator does.
  - Its view is named `home`. The old `laptop-home` view on minor 2 keeps working until it is replaced. The
    helper's `LAPTOP_HOME_APP_ID` (helper `:165`) then matches no window and goes with the fallback.
- **Big pictures are never decoded in this program.** The icon decoder is too small and too slow for a screen-sized
  picture (laptop home `:36`, `:270`). A still or a picture of his goes through a converter child of the helper's
  kind: ImageMagick in bubblewrap, under an address-space ceiling and a coder policy for PNG, JPEG and WebP. It
  hands back raw pixels at the output's size. The native home only copies pixels. Without the sandbox tools the
  plain picture shows.
- **Who owns which code.** The file is split into modules before anything is added (section 10). Surfaces, outputs,
  the reveal, the look kit, status icons, static pictures and the converter are the desktop's. The helper
  connection, the bar model, the finder, menu rows and the town are the hub's. The bar, the search and the menu name
  no colour and no layer; the town keeps its own painter (laptop home `:1478-1482`).
- **The keyboard.** Only the search takes it, and only while it is open. The picture, the bar, the strip, toasts
  and the bar's menus never take it; the menus are pointer-only popups. Section 12 says how a hung search is ended.

---

## 5. One source of truth

| Fact | Who makes it | Who keeps it for everyone | Who reads it |
|---|---|---|---|
| Installed programs, their pictures | the helper (desktop entries) | the helper | the mod, the native home |
| My apps, short names, groups, places, pins, logo cells | the mod (`publish_home`) | the helper, **now also on disk** | the native home (bar, town, search), the overview |
| Windows: whose, active, minimized, on which output, title | labwc | the helper | the mod, the native home, the overview, the supervisor |
| Outputs: names, the home output, where the world's window is, covered or not, what the bar does | labwc | the helper | the mod, the native home, the supervisor |
| The world's state: awake, asleep, starting, off; waiting for memory | the supervisor | the helper passes it on in `screens` | the native home |
| Settings: look, world, picture | `aresos-settings` | its file | everyone |

**What this removes.** The laptop home's own file of the last home. A second rule for the home output. A second
covering rule for the bar. A second way to start a program.

**What stays double, on purpose.** The mod's searches and the native search each rank hits in their own language.
One shared file of queries and expected hits, read by both sides' tests, keeps them in step.

### Changes to the helper that are not on the wire

- **Its life is the supervisor's.** The supervisor starts it once, with the instance and the view token and no
  nonce. It still dies with the supervisor (supervisor `:3804-3805`). The keeper restarts a failed supervisor after
  2 s (supervisor `:4628`), the new supervisor starts a new helper, and views reconnect with the same token.
- **The nonce is handed over and acknowledged.** A new launch's nonce and its keep-foreground flag go to the running
  helper as a packet on the status socket. The helper answers `ack`. The supervisor sends again each second and
  starts Prism only after the answer. A lost packet would refuse the mod's hello (helper `:3391-3394`) and end in
  `slow_start`. The read grows from 64 bytes. Until a nonce arrives, a desktop hello is refused.
- **The world's state is sent again at every helper start,** also acknowledged.
- **Its restarts never stop for good.** After five failures in a minute it is tried every 30 seconds. Today's
  `helper` recovery window stays for a running world.
- **The home on disk.** The helper writes each complete `publish_home` to `home.json` in the supervisor's state
  folder (supervisor `:372-373`), whole or not at all, readable by him only. It loads it at start, so `get_home`
  answers with no game running.
- **Output names.** The helper reads each output's name, so it and the views mean the same screen.
  *To verify:* that labwc 0.9.6 offers `wl_output` version 4.
- **More window requests.** Bring back (`unset_minimized`) and close, beside activate and minimize. Titles are kept.
  The time each window was last active is kept, per app.
- **While the world sleeps** the helper never activates the world's window and sends the mod nothing (section 9).

### `aresos-shell/1.3`

Everything in 1.2 stays. Minor 3 arrives with package 2, and each later capability joins it with its own package
(section 10). A side that did not offer a capability gets none of it. The laptop home pins minor 2 and keeps
working (laptop home `:492-495`). Example messages go to `mod/src/test/resources/shell-1.3/`.

| Capability | Message | Direction | What it does |
|---|---|---|---|
| `apps_state` | event `apps_state` | to the desktop and to views | `{"apps": [{"id": "chrome", "windows": 2, "active": true, "hidden": false}]}`. Every catalogue app with a window. `active`: one of its windows has the keyboard. `hidden`: all of them are minimized. Sent once after hello and on each change, coalesced as `apps_running` is. `apps_running` stays for 1.2 views. |
| `activate_app` | request `activate_app` | desktop and views | `{"app_id": "chrome"}`. With a window: the helper brings back and activates the app's most recently active window; a layout that went down together comes back whole (COMPONENTS.md 4.3). No launch. Reply `{"state": "activated"}`. While a launch of that app is still starting, from any client: the reply is that launch's, and no second one starts. Otherwise: exactly `open_app` with this request ID. |
| `screens` | event `screens` | to the desktop and to views | `{"world": "asleep", "waits": "memory", "screens": [{"name": "HDMI-A-1", "home": true, "world": false, "covered": false, "bar": "shown"}]}`. `world` is `awake`, `asleep`, `starting` or `off`. `waits` is there while a wake or a start waits for memory. Per screen: `home` is the home output; `world` is true while the awake world's window is on it and not minimized; `covered` is today's rule; `bar` is `shown`, `edge` or `none` (section 8). |
| `window_list` | `list_windows`, `windows_changed`, `activate_window`, `close_window`, `go_home` | views | As COMPONENTS.md 4.5 planned them for the overview. The app menu uses the first four. |
| `search_view` | event `search_requested` | to the view named `home` | Super. Sent instead of `shell_search` when that view is connected. The helper activates nothing and minimizes nothing. Without the view, today's route to the mod stays, except while the world sleeps. |
| `search_view` | `"screen": "world"` on `open_app` and `activate_app` | from a view | Allowed from a view in 1.3. It means the home output. |
| (existing `shell_focus`) | reasons `view` and `view_closed` | to the desktop | The search took the keyboard while the world had it, or gave it back. |
| `settings` | request `set_setting` | desktop and views | The helper starts `aresos-settings set` off its loop and replies `accepted` at once. Turning the world off can take a minute; the outcome shows in `screens`, and a refusal comes as a `notice`. |
| `world_power` | request `wake_world` | views | `{"reason": "click"}`, or `pointer` or `home`. The helper passes it to the supervisor, which decides (section 9). |
| `still` | event `still_changed`; request `still_shown` | to and from the view `home` | `{"id": 7}`. The view shows that still on the home output's picture and says so with the same number. |
| `notices` | event `notice` | to views | `{"text": "The world stays on: your home could not be saved."}`. One line for a toast. |
| `view_alive` | request `view_alive` | from a view | A view that holds the keyboard sends it once a second, from its drawing loop. After three silent seconds the helper tells the supervisor, which ends the native home's scope. |

- **Left over from earlier notes.** COMPONENTS.md 4.2 proposed "a field that says which apps have a minimized window"
  and "bring back this app's window". Those are `apps_state` and `activate_app`. `world_clicked` (4.3) is unchanged.
- **Views in 1.3** may also send `activate_app`, the window requests, `set_setting`, `wake_world`, `still_shown` and
  `view_alive`.
- **From the search, in COMPONENTS.md 4.5's order** (`docs/design/COMPONENTS.md:1204-1208`): the search closes its
  surface, waits for one round trip to labwc, reports `view_focus` false, and only then sends `activate_app`.
- **On waking** the mod gets one fresh snapshot: focus, covering, `screens`, `apps_state`, and the last `app_state`
  of each of its own launches that changed meanwhile. Never a backlog.
- **Never sent to the game or a view:** a command, arguments, an environment, a path other than `icon`. As today.

### Other interfaces

| Interface | Change |
|---|---|
| Lifecycle channel (mod and supervisor), 1.0 to 1.1 | Capability `still`: `{"op": "still", "id": n}`, answered `still_saved`. The mod writes one frame without its interface to a fixed file, `aresos/home/still.png` in his cache folder, whole or not at all. The supervisor never takes a path from the mod. Capability `sleep`: `sleep` (answered `sleeping`), `wake` (answered `awake`) and `resume`, as section 9 uses them. `save_world` gets the reasons `sleep` and `pressure`; the mod only logs a reason. A mod without `sleep` never sleeps. |
| Supervisor to helper (status socket) | Packets beside today's `windows`: the launch's nonce with its keep-foreground flag; the world's state; a still's number; a notice. Each is acknowledged. Super stays SIGUSR1, as 23c plans it. |
| Helper to supervisor (status socket) | Lines beside today's: `ack`; the outputs with the home output; whether the view `home` is connected; a wake request with its reason; `still_shown`; a view that stopped answering. |
| Supervisor commands | `aresos-desktop world on`, `world off`, `wake` and `wake --anyway`, beside 23c's `search`. |
| Settings (`aresos-settings`) | Three names: `world` = `on` or `off` (default `on`); `picture` = `plain`, `black`, `file` or `town` (default `plain`); `picture-file`, the program's first value that is not one of a list: an absolute path to a file he can read, checked when set. `set world off` asks the supervisor first and writes only after the world has closed. `set world on` writes first and then asks. |
| `publish_home` | The wire is unchanged. |

---

## 6. The world-off switch

**What it is.** The setting `world`. Off means the home is the picture, the search and the bar. It holds until he
turns it on again, across restarts of the laptop.

**Where he flips it.** In the world: a row in the AresOS menu (Esc). Outside: Super's search shows "Turn the world
on" as its first row while the world is off, and from package 4 the Home slot's menu has both directions. By
command: `aresos-settings set world off`, which Claude can run for him. All end in the same supervisor request.

**What happens to the game and Prism: both are closed.** Not frozen, not swapped.

- His goal is memory while building. A frozen game keeps its memory until something pushes it to swap. Only a closed
  game gives all of it back for certain.
- Turning off is the supervisor's planned stop (package 25): the stop record, a confirmed save, SIGTERM, the wait for
  Java's real exit and the lock. Before the stop the mod writes a still.
- **If the save is not confirmed, the world stays on.** The stop is called off as today (supervisor `:3370-3378`).
  The setting was never written, and a notice says why.
- **A sleeping world is dropped instead.** No thaw, on a laptop he is trying to free (section 9).
- After Java has exited and the lock is free, the supervisor stops every `aresos-desktop-*.scope` of the session,
  not only this launch's. After a retry or a crash restart the live Prism sits in an earlier launch's scope
  (supervisor `:1053-1055`).
  *To verify in package 7:* that Prism stays open after the game exits, and that SIGTERM does not cost it its
  sign-in. If it does, Prism is left running in OFF, its 418 MiB stay, and the memory study takes it up.
- **His own quit and a plain `stop` end in OFF too,** for this session only. Today they open the `quit` window
  (supervisor `:2421-2428`, `:3590-3591`). The setting is not changed, so the next login starts the world. While no
  view `home` is connected, today's window shows instead.

**How the picture is chosen and shown.** The setting `picture`. The native home shows it on `aresos-picture`, on
every output where the awake world is not showing.

| Kind | What |
|---|---|
| `plain` | A plain picture that `linux-desktop` draws in the look: A until B's files exist. The default (the owner, T482). |
| `black` | One flat colour, `#0d0d10`, look A's outline colour and the colour 23c plans for the laptop screen (`STATE.md:202`). Nothing sets a background colour today. A surface is still there, so a click never reaches labwc's root menu. |
| `file` | A picture of his, through the converter (section 4). It scales smoothly to cover the output, cropped centred. |
| `town` | His town from the side, by day, as LAPTOP-HOME.md designs it. Kept as a kind, not the default. It costs nothing extra: its model and painter are on main, and package 3 only places that drawing on the picture surface. It takes no clicks and has no bar, clock or battery of its own. If placing it shows a cost beyond that, the kind is left out. |

A click on a picture does nothing. A click on a still wakes the world (section 9).

**How the world comes back.** He turns the switch on. The supervisor starts the game as it does today.

- The start passes the admission test of section 12. On a full laptop it waits and says so; "Start anyway" is his
  own call.
- With no app window open, today's start-up cover hides the loading screens.
- With an app window open there is no cover: it must never hide his apps. Until package 8 the loading screens show
  behind his windows. From package 8 the world's window stays minimized until the world is ready.
- A start takes as long as a start at boot. Board T362 measures that.

**The supervisor's states**

| State | Game and Prism | The home output shows | New |
|---|---|---|---|
| SETUP, AUTH_REQUIRED, RECOVERY | none, or waiting for him | the message window over the picture | |
| STARTING | starting | the cover; from package 8 the still | |
| IN_WORLD | running | the world | |
| ASLEEP | frozen, sleep record open | the still | yes (package 9) |
| WAKING | thawed, still paused, sleep record open | the still | yes (package 9) |
| OFF (`off`) | none | the chosen picture | yes (package 7) |
| OFF (`quit`) | none, until he starts it or logs in again | the chosen picture | yes (package 7) |
| OFF (`asleep`) | none: a sleeping world was closed or dropped | the still | yes (package 9) |
| STOPPING | being stopped | black, or his apps | |

**How the new states are entered and left**

| From | Event | To |
|---|---|---|
| IN_WORLD | the supervisor decides to sleep, and every step of section 9 passes | ASLEEP |
| IN_WORLD | a sleep step fails | IN_WORLD: the sleep is called off, with one log line |
| ASLEEP | a wake is wanted and admitted | WAKING |
| ASLEEP | a wake is wanted and not admitted | ASLEEP, with `waits` set; tested again every 5 s |
| ASLEEP, WAKING | the pressure rule, a failed wake, or a kill from outside | OFF (`asleep`) |
| ASLEEP, WAKING | `stop`, `restart`, `logout`, a shutdown, world off | a drop (section 9), then what that request ends in |
| WAKING | `awake` in time | IN_WORLD |
| OFF (`asleep`) | a wake is wanted and admitted | STARTING |
| OFF (`off`), OFF (`quit`) | his switch, the Home slot's menu, `world on` | STARTING |
| any state with a running game | the setting goes to off | STOPPING, then OFF (`off`); back where it was if the save is not confirmed |

**OFF starts nothing by itself.**

- No timer is armed in OFF: no backoff restart, no wake. A wake request that reaches the supervisor in OFF (`off`)
  or OFF (`quit`) is logged and dropped.
- The gate every JVM passes (supervisor `:2182-2236`) refuses while the setting is off.
- `restart` and `retry` in OFF (`off`) start nothing and answer with one line that names the switch.
- A boot with `world` off goes straight to OFF: helper and native home, no Prism.
- If the native home keeps failing in OFF, the supervisor opens its message window. It does not start the world
  (section 12).
- The first start ever (SETUP, the sign-in) needs the world on. The default is on.

**Memory in both states**

| State | The game | Prism | The native home | Source |
|---|---|---|---|---|
| World on, today | about 1,019 MiB (its scope's anonymous memory; soft limit 2,560 MiB) | about 418 MiB while the game runs | not running | The laptop on R28, 2026-11-21 (`docs/HUB-HANDOFF.md:46`) |
| World on, this design | the same | the same | about 60 MiB with no picture surface | 53f's measurement of the laptop home; an estimate for the new program |
| World off | 0 | 0 | about 60 to 80 MiB | estimate from the same measurement |

- Turning the world off frees about 1.4 GiB of the laptop's 16.
- A picture costs about 8 MiB for each 1920 × 1080 output. GTK may keep two (`docs/design/LAPTOP-HOME.md:331-335`),
  and a larger monitor costs more.
- The helper and the supervisor are two small Python programs that run in both states. They were not measured.
  Package 7 measures all four on the laptop.
- The owner's own reading for the visible game is 1.2 to 1.3 GB.

---

## 7. Two screens

**Where the world goes.** To the home output. Package 23c's rule stands: any enabled screen that is not the laptop's
panel, the larger of two, the first connected on a tie; a closed lid counts as monitor only. 23c plans the move
itself: at boot the world opens there, plugged in later it moves there, unplugged it returns. Its mechanism is
still "the lead's first choice, a design step confirms" (`STATE.md:202`). This note relies on the rule, not on the
mechanism.

**One place for the rule.** The helper works out the home output, because it already binds every output and needs
the answer for covering, focus and placement. It tells the supervisor, which moves the world, and the views. With
the world off there is no window to ask, so the rule cannot hang on the world's window as it does today.

**What each output shows**

| The world is | Home output | Other output |
|---|---|---|
| awake | the world with its own hotbar | the picture, and the bar |
| asleep or starting | the still, and the bar | the picture, and the bar |
| off | the picture, and the bar | the picture, and the bar |

- **No screen is ever bare.** An output gets its picture surface the moment it appears. The surface goes away only
  once `screens` says the awake world's window is on that output, and it is back before the world leaves. So during
  a move the monitor shows the picture until the world arrives. This also ends "a monitor plugged in later stays
  black".
- With one screen and the world on, no picture surface exists and no picture memory is spent.
- **A screen plugged in while the world sleeps.** The still moves to the new home output at once, scaled as a
  picture of his is. The frozen window is left alone. At the next wake the supervisor moves the window first, and
  the helper shows it after that.

**How the cursor crosses.** The pointer is free unless he is in a look gesture (brief 328). labwc moves it between
the screens along their shared edge. Two rules for the look-around prototypes follow from this note:

- An edge shared with another screen belongs to crossing, never to turning. The mod learns the screens from `screens`.
- Where a strip exists, the bottom edge belongs to the bar.

Until 328 lands, the world still holds the pointer after a click on it, and he crosses with Esc first. That is
today's fault, not a new one.

**Covering, per output.** Every output has its own covered state: a maximized or full-screen window on it that is
not minimized. That is today's rule, applied per output, until the covering package gives the helper window
rectangles. The start-up cover and the black screen never cover. One thing reads it: the world pauses only while
the home output is covered (`shell_covered`, unchanged for the mod). Each output's bar follows its own rule
(section 8).

**Where apps open, and where focus goes**

- An app opens on the screen the pointer is on (23c). A click in the laptop screen's bar opens the app there.
- The search opens on the home output, and its app opens there, as the owner chose on board #334.
- `activate_app` focuses a window where it is. It never moves a window to another screen.
- When the last window of the app in front closes, the world gets the focus only if that window was on the home
  output and the world is awake. On the other output the focus stays there. A sleeping world gets a wake request
  instead.
- A click on the world or on the picture never hides a part-screen app. The world stays below every window, and the
  picture is below the world. A click on the picture ends on the picture: it never reaches labwc's root menu.

---

## 8. The bar, and the bar over full-screen apps

### What the bar holds

| Slot | Content |
|---|---|
| Home | First slot. World awake: a click goes home, and what covers the world goes down by today's rule. Asleep: it wakes the world. Off: it opens the slot's menu, whose first row is "Turn the world on". The menu also has the picture and, while a start waits for memory, "Start anyway". |
| His nine pins | The Live hotbar's nine slots in its order, as `publish_home` gives them. An empty pin is an empty slot. |
| Other open apps | After a gap: every open app that is not pinned, in the order they opened. A slot leaves when its last window closes. |
| Status icons | The desktop's component. They sit in the bar. |

- **Marks**, from `apps_state`: open, active, and "all its windows are minimized". How a mark looks is the desktop's.
  The world's hotbar draws the same three.
- **Hover** shows the app's name.
- **Left click:** `activate_app`. It opens the app or brings its last window back.
- **Right click:** the app's menu: its windows by title, New window (`open_app`), Close all windows. Close goes
  through the window's own close, so an app still asks about unsaved work. With more than one window it asks once
  first ("Close 3 windows?").
- **In the world** a right click on a hotbar slot stays what it is today: the item's use, which is `open_app`, a new
  window.
- **A failed launch** shows the helper's words as a toast above the bar for five seconds.
- **The picture in a slot** is the app's logo as the mod published it (laptop home `:1751-1758` draws slots from the
  published cells). An open app outside My apps shows its catalogue picture.

### Where it shows

- **One bar on every output**, the same content on each (the owner, T484).
- **It reserves no screen space.** A maximized window fills the whole screen and hides the bar, which the owner likes.
- **The helper says what each bar does**, in `screens`:

| `bar` | When | The bar |
|---|---|---|
| `shown` | The output shows the picture or the still, and no app window shows on it: none is open there, or all are minimized. | Visible, on the top layer. |
| `edge` | An app window shows on the output, of any size. | Hidden. A strip at the bottom edge waits for the pointer. |
| `none` | A start-up cover or the black screen is up. Or the output shows the awake world with no app window on it: the world's own hotbar is the bar there. | Hidden, and no strip. |

**A visible bar never stands over a window** (review finding 17).

- The bar is above windows and reserves nothing. Left visible over a half-screen terminal, it would hide the
  prompt for good.
- The helper cannot tell which windows reach the bar. wlr-foreign-toplevel gives no window geometry, and the
  covering package's rectangles are not there yet.
- So until the covering package any showing window sends that output's bar to the edge. A window whose output labwc
  has not named yet counts for every output.
- From the covering package on, only a window whose rectangle reaches the bar's rows does. That is a later change
  of one condition in the helper.
- On the home output with the awake world and a part-screen app, the world's hotbar may sit behind the window. The
  bottom edge then brings the outside bar up over both.
- This fits his answer T485: visible on a screen nothing fills. Whether it feels right with a small window open is
  question 4.

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
- Look B reads the game's own bar sprites from the cache that COMPONENTS.md section 5 builds from the installed
  game's files. That cache is made from the jar on disk, so it does not need the game to run.
- No game installed, or a file that fails its check: the bar is drawn in A, as a whole piece.
- Nothing of Mojang's is committed. The bar's rows in the look-B map are names and numbers only. Every public picture
  of the bar is look A.

### Search

- Super opens the search on the home output, over whatever is there. The world, a full-screen app and the picture are
  all the same to it. It does not wake a sleeping world.
- It takes the keyboard for itself while it is open, and only then. Escape, a click outside it, or the recovery key
  ends it. It is exclusive, not "on demand", because labwc gives an on-demand surface the keyboard only on a click
  (LAPTOP-HOME.md section 6), and Super must give it at once.
- It finds as the laptop home's typing line does (LAPTOP-HOME.md 2.2). Enter opens the best hit or brings it back, on
  the home output. While the world is off, its first row is "Turn the world on".
- It is drawn in the Bar look the owner chose for the search on board #382 (`STATE.md:143`), from the look pack.
- **The mod's search over the world stays** as the fallback while no view `home` is connected. It is built, costs
  nothing, and keeps Super working if the native home is away.
- **For 23c.** Its plan lets Super do nothing outside IN_WORLD, and signals only a helper whose desktop is connected
  (`STATE.md:204`). Super must pass in OFF, ASLEEP, WAKING and STARTING too: the supervisor signals its live helper
  in every state, and the helper picks the route.

---

## 9. The sleeping world

This note gives board T364 its place. It does not design swap, prefetch or when the world should sleep.

**One rule for the screen.** A sleeping world is never shown as a frozen window. A frozen X11 window under the
pointer would queue input it cannot read.

**Going to sleep.** The supervisor decides, from the signals below. It needs IN_WORLD, a mod with `still` and
`sleep`, a live helper and a connected view `home`.

1. It asks for a still (`still`, answered `still_saved`).
2. The native home shows the still on the home output's picture and says so (`still_shown`). **No still on screen,
   no sleep.**
3. It asks the mod to sleep (`sleep`). The mod pauses the world as it does when covered, frees the pointer, and
   ignores input. It answers `sleeping` and holds that pause until `resume`, also across a reconnect.
4. The helper minimizes the world's window. The still is now what he sees. He cannot touch the world.
5. It asks for a save (`save_world`, reason `sleep`) and waits for `saved`. **No confirmed save, no sleep.**
6. It writes the sleep record, durably, as the stop record is written: the launch, the session, the world, the
   time of the save. It is an optional key of `desktop.json`, like the stop record.
7. It freezes the game's scope with the cgroup freezer and reads back that it is frozen. The record says `frozen`.
8. It demotes the game's realtime threads, picked by policy, and checks again before any thaw (package 318). On the
   laptop the game uses PipeWire and has no such thread; this is the safety net for the fallback backends.
9. Here the T364 study adds its steps: memory to swap, Prism's memory, prefetch.

A step that fails before the freeze calls the sleep off: `resume`, the window back, one log line.

**Why the save comes after the pause and the minimize.** From step 3 on, the world does not tick and gets no input.
So what the save of step 5 writes is everything, and nothing changes after it. That holds until `resume`, and
`resume` is sent only after the record is closed on disk. So for any game whose sleep record is open, what is in
its memory is on the disk. *To verify in package 9:* with the pause held, the mod's write observer (package 46)
sees no write after the sleep's save.

**Waking**

1. A wake is wanted (the table below) and passes the admission test (section 12). If it does not pass, the world
   stays asleep, `screens` says it waits for memory, and one toast says so.
2. The realtime check, then T364's prefetch.
3. The thaw, read back. The state is WAKING. The sleep record stays open.
4. The supervisor sends `wake`. The mod draws, still paused. It ignores every key and click that arrived before it
   answers.
5. The helper shows the window when `awake` arrives, or 2 s after the thaw if it has not. Whether a hidden game can
   finish a frame is not known, so the design does not wait on it. The window gets no keyboard yet.
6. On `awake` the supervisor closes the record on disk, sends `resume`, and is IN_WORLD. The helper gives the world
   the keyboard if this wake should have it. The native home takes the still off the home output once `screens` says
   the world is on it. The still and the first frame show the same view.
7. No `awake` 30 s after the thaw, or the game ends: the game is dropped. The next wake is a normal start. After
   three failed wakes in a session the world no longer sleeps frozen in that session; it closes instead.

### Every stop, in ASLEEP and WAKING

One rule covers both states, because the sleep record is open in both: **nothing is asked of the game, and a stop
drops it.** Today's routine cannot act on a frozen game. It would wait 30 s for a save, send a SIGTERM that is not
read, run out its 60 s, and latch `unsaved` at the next boot (supervisor `:3323-3355`, `:3545-3557`, `:3629-3633`).

**The drop**

1. The supervisor writes a stop record as every stop does, with the save taken from the sleep record: `saved`. The
   record carries a new mark, `sleep`. A drop for memory has the kind `drop`.
2. It sends SIGKILL through the pidfd it already watches, where it sends SIGTERM today (supervisor `:3890-3899`).
   Never a PID from a file. A frozen game reads no SIGTERM, and a thaw would pull its memory back in.
   *To verify in package 9's rig:* that SIGKILL ends a process in a frozen cgroup on the image's kernel without a
   thaw.
3. It waits for the real exit, the wrapper's report and the free lock, as today. That takes about a second, not 60.
4. `conclude()` finds the open stop record and takes today's `stopped` path (supervisor `:2388-2391`,
   `:3638-3659`): never counted, never restarted by backoff, never latched. The record closes with the new close
   `dropped` and the save `saved`, so no `unsaved` latch follows.
5. Prism's scopes end, as for world off. The still stays on screen.

| Request | What it does in ASLEEP and WAKING |
|---|---|
| `stop` | Drop. Ends in OFF (`quit`). The reply is a confirmed stop. |
| `restart` | Drop, then a start through the admission test. Not admitted: OFF (`asleep`), and the reply says it waits for memory. |
| `logout` | Refused while an app window is open, as today. Otherwise drop, then labwc ends as today. |
| Shutdown (the guard, or the session ending) | Drop. No 60 s wait behind black, and no `unsaved` latch at the next boot. |
| World off | Drop, then the setting is written. OFF (`off`). No thaw. |
| The `save` command | Answered `saved` at once, from the sleep record. A backup may read the files: nothing is writing them. |
| `retry` | A wake by hand. |
| A restarted supervisor (adoption) | Sleep record open and the scope frozen: ASLEEP. No start timer and no `slow_start`. Record open and not frozen: WAKING, and the wake is carried on. A drop that was begun is finished. |
| A kill from outside (the system for memory, his own `kill`) | `dropped`, below. |
| The guard's own record, when no supervisor answered at shutdown | An open sleep record for that launch counts as saved (supervisor `:2718-2753`). The frozen game ends with the session, within its scope's 15 s. |

**A kill from outside is `dropped`, not `killed`.** `conclude()` looks at the sleep record right after the stop
record. A launch that ends while its sleep record is open is `dropped`, whatever its status and whoever sent the
signal. It is decided from the supervisor's own record, as `stopped` is. It is never counted as a failure, never
restarted by backoff, never latched `killed` or `unsaved`, and no recovery window opens. The state is OFF
(`asleep`): the still stays, and the next wake is a start.

**In ASLEEP and WAKING the supervisor expects no heartbeat** and runs no healthy-minutes clock. Today a missing
heartbeat would mark the world unready (supervisor `:2499-2500`, `:2560-2566`).

**Three written rules change, for a game whose sleep record is open and for no other:**

- "The supervisor never sends SIGKILL to the game" (supervisor `:79`).
- The `killed` latch for every SIGKILL end (supervisor `:2408-2420`).
- OS-BASE B5's "a killed game is an unclean stop", and its relaunch only after a clear minute and the owner's retry
  (`docs/design/OS-BASE.md:350-352`). A dropped world was saved, and it comes back through the admission test.

Package 9 changes those texts in the same commit as the code.

### Where the signals come from

| Signal | From | The world gets the keyboard |
|---|---|---|
| A click on the still | the native home (`wake_world`) | yes |
| Home: the bar's Home slot; Home picked in Alt+Tab | the native home; the helper | yes |
| The app in front closed on the home output, and the world would get the focus | the helper | yes |
| The pointer comes onto the still (the owner's "predicted from the pointer") | the native home | no |
| The home output is no longer covered | the helper (`screens`) | no |
| To sleep: the home output covered, idle time, the lid, battery | the helper; the supervisor | |

- The supervisor alone decides, because it alone freezes and thaws.
- A wake that had to wait for memory never takes the keyboard when it finally runs. He has moved on.
- **The helper's own window calls for a wake are marked,** as Super's activation is (helper `:4143-4147`). It
  minimizes nothing because of them. For a wake without the keyboard it only brings the window back. If labwc gives
  the window the focus anyway, the helper hands the focus back to the window that had it.
- **A frozen window is put away again.** While the world sleeps the helper never activates its window: Super's
  fallback route and the return after a close send a wake request instead. If labwc shows the window itself, because
  he picked Home in Alt+Tab, the helper minimizes it again at once and asks for a wake.

**Two depths of sleep.** Light sleep is the frozen game: a fast wake, but it keeps memory and may keep the NVIDIA
card awake. Deep sleep is OFF (`asleep`): the world closed, by a planned stop or by a drop, with its still left on
screen. A wake starts it again. The study decides when each applies.

**The same path at boot (package 8).** A starting world can look like a waking one: the last still and the bar show
at once, he can open apps, and the world comes alive when it is ready. The start-up cover is then needed only when
there is no still yet.

**Numbers so far, from the rigs only.** Package 318's three frozen games held 421 to 502 MiB resident with 598 to
682 MiB in swap; package 49's two held 494 and 510 MiB (`reviews/318-thaw-watchdog/FINDINGS.md:110`). The swap
figures were forced by the rigs' own reclaim of 600 MiB (`FINDINGS.md:29`). These are not product numbers. The
study measures the real session.

---

## 10. Migration

The in-game hotbar and the in-game search keep working throughout; neither is removed.
Sizes: S is one builder step, M two or three, L four or more. The rows are in build order. The numbers are kept
from the first version of this note, so the desktop's packages are still 3, 4 and 5.

| # | Package | He sees | Lead | Needs | Size |
|---|---|---|---|---|---|
| 1 | **The helper for the session.** Started once, the nonce handed over and acknowledged, restarts that never stop, the home kept on disk, output names. Carries 23c's view token and the start of the native program in its scope. | Nothing. Opening no longer pauses when the game restarts. | aresos (supervisor) with hub (helper) | | L |
| 2 | **Open apps and "bring back".** `apps_state`, `activate_app`. The mod marks hotbar slots and sends `activate_app` from a left click, gates and `/name`. | Open and active marks on the hotbar. A left click brings Chrome back with its tab. A right click opens a new window. | hub | | M |
| 3a | **The picture, one screen.** First the laptop home split into modules, with no change in what it does. Then `aresos-picture` with `plain`, `black` and `file`, the converter, the settings, and Root clicks that do nothing. | Nothing on one screen until the world is off. | desktop | 1 | M |
| 6 | **Search outside.** The finder as `aresos-search`; the helper routes Super to it; the alive beat; the recovery key's third action. | Super works over any app and minimizes nothing. | hub, with desktop for the surface | 3a, and 23c's Super step only | M |
| 7 | **The world-off switch.** The setting, OFF, the row in the AresOS menu, the search's first row, Prism's scopes, the memory check on the laptop. | The switch. | aresos with hub | 3a, 6 | M |
| 4 | **The bar outside.** `aresos-bar` in look A, slots and marks, the app menu, the window requests, `screens`, toasts. | A bar on the picture and on the still. The Home slot's menu. | desktop (surface) with hub (content) | 2, 3a | L |
| 5 | **The bar at the bottom edge.** The strip, reveal and hide, tested against B321's barrier. | The pointer at the bottom edge brings the bar up over an app. | desktop | 4 | M |
| 3b | **The second screen.** The picture and the bar on the output without the world, and the hotplug rules. | With the monitor in, the laptop screen shows the picture and a bar. | desktop with aresos | 3a, 4, 23c | S |
| 8 | **Stills and the quiet start.** The lifecycle channel's `still`; the boot path; the world's window minimized until ready. | Boot shows his home at once; it comes alive when ready. | hub (mod) with aresos | 7 | L |
| 9 | **The sleeping world.** `sleep`, `wake`, `resume`, the sleep record, the drop, the memory tests. Its own study first (T364). | The world sleeps and wakes. | hub with aresos | 8 | L |

**Dropped:** package 10, "One bar". The owner keeps both bars (T483). Both look alike in look B, so one bar stays
possible later as a setting if he changes his mind.

**Later, each its own package:** system notifications in the toast surface (desktop); a program's own actions in its
menu, such as a private window (hub: the helper parses no action groups today); pinning while the world is off (hub);
look B for the bar, with the desktop's look work; the bar's rule from window rectangles, with the covering package.

**Order notes**

- Package 2 is the try-out's fixes 7 and 10 on the final protocol. It can start now, beside package 1.
- **The switch comes before the bar.** The owner asked for it first, and the search alone is a launcher. Between
  packages 7 and 4 an off world has Super's search, Alt+Tab and the picture, and no bar. Until package 5 there is no
  bar over a maximized app.
- **Only 3b waits for the monitor work.** 3a, 4, 5, 6 and 7 need one screen. The search needs 23c's Super step, the
  key binding and `aresos-desktop search`, and 23c is told that Super passes in every state (section 8).
- **Who takes the laptop home over.** It belongs to `linux-laptop-home` today (`docs/HUB-HANDOFF.md:112`). This
  note's choice: `linux-laptop-home` splits the 2,637-line file into modules as its hand-over step, then
  `linux-desktop` leads the program and the hub leads its content modules. The three leads confirm that before
  package 3a's brief. Two leads in one file would be a merge hazard.
- Package 1 changes when the helper starts, so it touches 23c's plan. `linux-aresos` reads it first.
- Every `rc.xml` change goes to `linux-aresos` first, as always. This note adds two: Root clicks (3a) and the
  recovery key's third action (6).
- The desktop writes its own briefs for 3, 4 and 5 once this note is reviewed.

---

## 11. Questions for the owner

### Answered on 2026-11-21

1. **The default picture** (T482): "A plain picture".
   The default behind apps and with the world off is a plain picture that `linux-desktop` draws in the look. Black
   and his own picture stay settings. The town is no longer the default; it stays a kind, at no extra cost.

2. **One bar instead of the hotbar** (T483): "Ohhh good question. So the Mc hotbar wouldn't exist then? But isn't the
   taskbar design the Minecraft hotbar ? So I think keeping both makes sense".
   Both stay. In the world: the game's own hotbar, with the open and active marks. Wherever the awake world is not
   in view: the bar outside, which looks like the hotbar in look B.

3. **A bar on every screen** (T484): "Yea both makes sense but only when going down right?". And on whether it stays
   visible on a screen nothing fills (T485): "Visible there (recommended)".
   A bar on every screen. It is visible on a screen nothing fills and waits at the bottom edge while a window fills
   it. Each bar goes by its own screen's state.

### To tell him, not to ask

- **The search keeps its look.** The search outside the game replaces the one over the world that he chose the Bar
  look for (board #382). It is drawn in that same look.
- **A typed name and a gate now bring the app back.** On board #155 he chose that each Chrome-logo click opens a new
  window. After the try-out he asked for "left click opens or brings back the app, right click opens its options".
  So `/chrome`, a gate and a left click bring Chrome back. A right click on its hotbar slot opens a new window, from
  package 2 on. The full menu comes with the bar outside.
- **Home in an off world opens a menu.** It does not start the world by surprise. The first row is "Turn the world
  on".

### Decided by the lead (review 1's finding 17)

4. **With a window open that doesn't fill the screen, the bar stays visible and reserves its height** (lead's
   decision after this revision, 2026-11-21). The owner already answered this case: T485 asked about "just the
   picture or small windows", and he chose "Visible there".
   - **While the bar is `shown`,** its layer surface sets an exclusive zone of the bar's height, as the Windows
     taskbar does. labwc then places, snaps and maximizes windows above it, so it covers none of their rows.
   - **While the bar waits at `edge`,** the exclusive zone is 0, so a maximized or full-screen window gets the whole
     output. `edge` follows covering, and covering follows maximize and full-screen (today's rule, per output), so
     there is no resize loop: a maximized window covers the output whatever the zone is.
   - **Known limit:** a part-screen window he drags down over the bar's strip keeps its bottom rows under the bar.
     labwc doesn't move it when the zone appears. The pointer reaches it again with one move.
   - **For `linux-desktop`:** this replaces "exclusive zone 0" for the `shown` state in its layer list above. Its
     package 4 brief checks that labwc 0.9.6 honours a changing exclusive zone on a layer surface, and what it does
     to windows that are already maximized when the zone appears.

Not asked, because the note decides it or he has already answered: where the search opens (board #334), that a
sleeping world wakes on a click, that turning the world on never covers his apps, and that an off world stays off.
The desktop will show him the bar's look in its own component pictures. The T364 study will ask how soon the world
should sleep, with measured wake times.

---

## 12. Risks, known limits, assumptions

### Real harm, and how the structure answers it

| Harm | Answer |
|---|---|
| **Lost building work when the world is turned off or put to sleep.** | Both go through a confirmed save. Without it, off is called off and sleep does not happen. A sleeping world is paused before its save and stays paused until its record is closed. |
| **A stop or a shutdown that hangs on a sleeping world, and an `unsaved` latch after it.** | One rule: while the sleep record is open, every stop drops the game. No thaw, no wait, nothing lost (section 9). |
| **A sleeping world killed for memory shown as a crash.** | It is `dropped`, decided from the sleep record. No count, no latch, no window. |
| **Memory is full when the world should wake** (the owner's worry). | See below. |
| **The world starting by itself after he turned it off.** | In OFF nothing starts it: no timer, no wake, and the JVM gate refuses (section 6). |
| **A home that cannot come back.** | A chain, each link independent of the one before: (1) the native home is restarted when it ends, for as long as the session lasts; (2) the world's own hotbar and the mod's search never depend on the native home; (3) in OFF, after the native home's third failed start, and whenever Super finds no view and no awake world, the supervisor opens its message window. It says how to try the bar again (`retry`) and how to start the world (`world on`), and it starts nothing; (4) the same commands work from the recovery terminal; (5) if the world cannot start either, today's recovery window says why. His open apps stay reachable by Alt+Tab throughout. |
| **A hung search that holds the keyboard.** | Three ways out. The search sends an alive beat from its drawing loop; after three silent seconds the supervisor ends the native home's scope. The recovery key gets a third action, first in line, that kills `aresos-home.scope` through the user manager. It needs no supervisor and no helper, and it is what lets the terminal get the keyboard (`docs/design/COMPONENTS.md:1204-1208`). And Escape or a click outside closes a search that still answers. The program keeps no state of its own, so ending it loses nothing. |
| **A dead session because a new piece fails.** | The native home is never part of readiness. Its restarts are spaced and never end the session. From package 3a a click on a bare desktop does nothing: labwc's built-in root menu may hold Exit. |
| **Input piling up in a frozen game.** | The world's window is minimized before the freeze. The helper never activates it while it sleeps and puts it away again if labwc shows it. The mod ignores what arrived before `awake`. |
| **The helper is needed more than before.** | Its restarts never stop for good. While it is away the bar shows its last state and "Opening is back in a moment". If it stays away 30 s while the world sleeps, the supervisor wakes the world, if admitted, and the mod asks for its own window back. Alt+Tab's Home shows it in any case, since the world is then awake. |
| **The native home gone while the world sleeps.** | No still on screen, no sleep. If the native home is gone for 10 s while the world sleeps, the supervisor wakes the world, if admitted. If not, the message window says the world is waiting for memory. |
| **Mojang's files in the repo.** | The still and look B's cache stay in his cache folder. They never go into the repo, an image, a backup or a report. Public pictures are look A. |

### When memory is full

The home must never kill his work. Four rules, each with its mechanism.

**1. The picture and the bar need nothing new.** They are already in memory. They show whatever happens to the
world.

**2. A start or a wake is admitted, not forced.** The test is new. Today's test after a memory kill needs a full
clear minute and is sampled only while the `killed` latch holds (supervisor `:225-232`, `:2490-2492`); used as it
is, every wake would wait a minute. The new test is sampled every 5 s while a world sleeps or a start waits, so its
answer is there when a wake is wanted.

| Test | Passes when | For |
|---|---|---|
| Wake (a thaw) | the last sample of memory pressure (`some avg10`) is at most 10 % and fresh, and `MemAvailable` is at least what the game has in swap plus 1 GiB | a sleeping world |
| Start | the same pressure rule, and `MemAvailable` is at least 2.5 GiB: the world's 1.4 GiB plus 1 GiB | a dropped or closed world, the backoff restart after a crash, world on, `restart` |

- The numbers are starting values. The T364 study tunes them on the laptop.
- An unreadable pressure file is never "clear", as today.
- It covers every start the supervisor makes after the session's first. At login nothing of his is open yet.
- A start he asks for by hand is tested too. If it fails, one line says so: "Memory is nearly full. The world
  starts when there is room." The Home slot's "Start anyway" and `aresos-desktop wake --anyway` start it regardless.
  That is his call.
- Today's rule after a `killed` latch stays as it is for an awake world that was killed.

**3. Under pressure the supervisor drops a sleeping world itself**, before the system has to choose.

| The drop fires when | Why this line |
|---|---|
| `some avg10` is at least 25 % on three samples in a row (15 s) | Below systemd-oomd's pressure limit. Upstream's default is 60 % for 30 s, by systemd's documentation; the image's values were not read. |
| or swap is more than 75 % used | Below systemd-oomd's swap limit, 90 % upstream. |

- Only a world whose sleep record is open is dropped. It costs no work.
- Package 9 reads the image's real limits and pins a test that these lines stay below them.
- An awake world on a covered home output is put to sleep at once under the same pressure, so it can be dropped
  next.

**4. The world should be the one that goes, also when the system chooses.** This is an aim, not a promise.

- **The kernel's killer.** The wrapper (`os/config/usr/libexec/aresos-desktop-java`) raises Java's `oom_score_adj`
  before Java starts. Raising it needs no privilege. Start value 800. Package 9 reads what his apps carry on the
  laptop and keeps the game above them.
- **systemd-oomd.** As far as known it has no "kill this first" setting; that is verified on the image. The game
  already has a scope of its own, so a kill takes the game alone. Rule 3 is what keeps oomd from having to choose.
- **The awake world is the limit.** A kill of an awake world costs up to five minutes of building, as today
  (`docs/design/HUB.md:59`), and latches `killed` as today. While pressure is above rule 3's line, the supervisor
  asks an awake world to save once a minute (`save_world`, reason `pressure`). A kill then costs about a minute.
- A world he is using is never put to sleep or dropped by force.

What he notices on a full laptop: his apps stay, the home stays usable, and the world comes back later.

### Known limits (low harm)

- **Until brief 328 lands,** the world holds the pointer after a click on it. Crossing to the other screen needs Esc
  first. That is 328's job.
- **A full-screen app that locks the pointer** (a game) cannot reveal the bar. Alt+Tab and Super work.
- **The last pixel row** of a screen with a strip belongs to the strip. A click there brings the bar up.
- **Deskflow:** if the Mac sits below the laptop, that output's bottom edge is the barrier's and gets no strip.
  Apps there are reached by Super's search and Alt+Tab.
- **Screens stacked one above the other:** the upper screen's bottom edge is shared, so the pointer does not stop
  there. He rests on the boundary to reveal that bar.
- **Before the covering package** the bar hides on a screen as soon as any window shows there, also a small one far
  from the bar. The helper has no window rectangles yet (question 4).
- **After the covering package** a window he drags over a visible bar is overlapped. Only placed windows have
  rectangles, and he can drag it away.
- **A toast is on the top layer,** so a true full-screen window hides it. A launch that fails meanwhile is in the
  helper's log.
- **Between packages 7 and 4** an off world has no bar, and until package 5 none over a maximized app. Super's
  search covers that time.
- **With the world off:** no gates, no `/name`, no pin changes. A program installed meanwhile joins My apps when the
  world next runs. The search finds it at once anyway.
- **A window nobody owns** has no slot in the bar, and its app starts a new instance on every left click. Ownership
  needs a reviewed identity; a hint fixes a known program.
- **Two rankers** for the search, one in the mod and one outside, kept in step by shared test cases.
- **The still can be old** after a crash, since it was made at the last sleep, off or stop. After a hotplug it is
  scaled to the new screen until the world wakes.
- **At sleep in view** the world's hotbar gives way to the bar outside at the same place. They look alike in look B,
  not in A. The bar's slots show the 12 × 12 logo, the hotbar the item icon.
- **Turning the world on with apps open** shows Prism's own window for a moment, and it may take the focus. Package 8
  hides only the game's window.
- **A helper or supervisor restart** leaves the bar on its last state for a few seconds.
- **After `previous` to an older release,** its `aresos-settings set` drops the new names
  (`os/config/usr/libexec/aresos-settings:60-68`). The world is then on and the picture plain again. Nothing is lost.
- **Prism's 418 MiB** stay while the world is on. Whether Prism can leave after the launch is the memory study's
  question.
- **Light sleep may keep the NVIDIA card awake** on battery. Not known. If it does, the study uses deep sleep there.
- **A click on the active app's slot** does nothing more. Minimizing it on a second click is a small later change.

### Assumptions and things to verify

In a private labwc:

- The stacking: background, bottom, always-below windows (the world), windows, top, full-screen, overlay. That
  `set_layer` works. That a full-screen window hides the top layer.
- That labwc 0.9.6 offers `wl_output` version 4.
- That activating a minimized window brings it back, and that `unset_minimized` does not take the focus.
  COMPONENTS.md lists both as open.
- That an overlay surface with exclusive keyboard gets the keyboard while the game holds a pointer lock, and that a
  window gets the keyboard back when that surface's program is killed.
- What labwc's built-in root menu holds.
- That minimizing the world's X11 window from outside hides it without the game's help.
- That Minecraft loads normally while its window is minimized (package 8), and that the mod can ask for its own
  window back.

In package 9's rig and on the laptop:

- That SIGKILL ends a process in a frozen cgroup without a thaw. Whether the user manager thaws a frozen scope when
  it stops it; either way the game ends within its scope's 15 s.
- That a paused world writes nothing after a flush save.
- systemd-oomd's limits on the image, and the `oom_score_adj` his apps carry.
- That Prism stays open after the game exits, and keeps its sign-in through SIGTERM.

Not read or not there:

- The image has no notification service today.
- The laptop's swap set-up was not read; the T364 study and `linux-aresos` own it.
- 23c's move of the world is a plan. Brief 328 was not in the checkout.
- For this revision the supervisor was read whole. The helper was read in its window, protocol, focus and server
  parts; its discovery and picture parts only in passing.

### The OS part, from `linux-desktop`

Written by `linux-desktop` on 2026-11-21 (`reviews/332-outside-game-design/INPUTS-1.md`) and folded in here. The
sections above use these names and rules.

**Layers** (wlr-layer-shell on labwc 0.9.6)

| Surface | Namespace | Layer | Keyboard | Details |
|---|---|---|---|---|
| Picture | `aresos-picture` | background | none | Anchored on all four edges, exclusive zone -1. Its input region is the whole output, so a click on it never reaches labwc's Root context. |
| Bar | `aresos-bar` | top while `shown`: above windows, below a true full-screen window. Overlay while revealed, by `set_layer` (layer-shell version 2 or later), and back to top when it hides. | none | Anchored bottom, left and right. Exclusive zone 0: it reserves nothing. Its menus are popups on it, pointer only. |
| Strip | `aresos-bar-edge` | overlay | none | It exists only while that output's bar is `edge`. 1 logical pixel high, full width, exclusive zone -1, a transparent buffer with an input region. |
| Search | `aresos-search` | overlay | exclusive while open | Esc, a click outside, or the recovery key ends it. |
| Toast | `aresos-toast` | top | none | An empty input region, so clicks pass through, as with the indicator. Not over a full-screen video. |
| Indicator | as package 320 built it | overlay | none | It stays above all of these. |

- No surface uses the namespace `aresos-input-barrier`. B321's labwc patch treats that one as the capture surface.

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
- `aresos.cover` and `aresos.black` never cover. They make the bar `none`.

**Scaling**

- The town and every look sprite scale by whole numbers, nearest neighbour. Any leftover is centred on the picture's
  own edge colour.
- A picture of his scales smoothly to cover the output, cropped centred. A still is scaled the same way when the
  output's size differs.
- Each output uses its own scale factor.

**Look**

- The bar is a new COMPONENTS.md piece, with the status icons (try-out item 9). `linux-desktop` writes its A, B and
  C, its marks and its look-B map rows there before package 4's brief.
- The frame package (B329, building now) sets A's colours and button cells, which the bar reuses.
- The plain picture is the desktop's to draw in the look. This note assumes its design goes into COMPONENTS.md
  with the bar's.

**`rc.xml`** (to `linux-aresos` first)

- The image has no `<mouse>` section and no `menu.xml`. So labwc's defaults show its built-in root menu on a click on
  a bare desktop. It may hold Exit; that is still to verify.
- The picture covers that from package 3 on. Package 3 also makes the Root context's clicks do nothing, for when no
  picture is up.
- Nothing else in `rc.xml` for packages 3 to 5. The bar takes no keys, and Super stays 23c's.
- The recovery key's third action is package 6's, not the desktop's.

**Packages.** 3, 4 and 5 are `linux-desktop`'s. Each gets its own brief from `linux-desktop` once this note is
reviewed. Package 5 also tests the 1-pixel strip against B321's barrier in its harness.
