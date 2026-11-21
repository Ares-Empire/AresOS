# The home's parts outside the game

**Status.** Design note for board brief 332, written 2026-11-21 by one Fable design agent with read-only tools.
Revised twice the same day. First after review 1 (`reviews/332-outside-game-design/REVIEW-1.md`, NOT READY), with
`linux-desktop`'s OS part and the owner's answers (`reviews/332-outside-game-design/INPUTS-1.md`). Then after
review 2 (`reviews/332-outside-game-design/REVIEW-2.md`, NOT READY, five blocking points), with the lead's scope
decision below and `linux-desktop`'s new point on the bar (the last section of `INPUTS-1.md`). The lead then fixed
the targeted recheck's wording points by hand (`reviews/332-outside-game-design/RECHECK-1.md`). Nothing here is
built. It decides the structure for the hub (`linux-hub`), the desktop (`linux-desktop`) and the supervisor
(`linux-aresos`).

**The lead's scope decision (2026-11-21).** The brief says this note gives the sleeping world its place and does
not design swap or prefetch. Two reviews pushed the sleeping world and memory pressure into full mechanism design.
That is the work of its own study (board T364). So this note keeps the structural decisions: the states exist, the
supervisor owns stop and admission, and the world is the one to give way. Review 2's blocking points 1, 2 and 3 are
now three gates (section 13). Each says what must be true, how a test shows it, and which package waits for it.

**What this revision changed**

- Section 13 is new: the three gates. Section 9 and the memory part of section 12 are shorter. The mechanisms the
  reviews found incomplete are the gates' work now.
- The bar has one rule, the same in sections 1, 8, 11 and 12 (review 2's point 4), with `linux-desktop`'s point
  about the home output.
- Section 10 states each package's real needs and what must still work after it (review 2's point 5).
- Super has one route in every state. Sections 5, 8, 9 and 12 disagreed about it.
- Section 3 corrects five claims about today's code (review 2's finding 7).
- Sections 1 to 12 keep their numbers.

**Sources.** The documents and code the brief names, as they are in this checkout. Nothing was run and nothing was
measured; every number names where it comes from. labwc's own behaviour, the image's effective systemd-oomd settings
and `briefs/328-look-around.md` could not be read here. What rests on them is marked.

**Words used below**

| Word | Meaning |
|---|---|
| The world | The Minecraft home: the game, its window (`aresos-desktop`) and the mod. |
| The helper | `os/config/usr/libexec/aresos-shell`. "Helper `:N`" is line N of that file. |
| The supervisor | `os/config/usr/libexec/aresos-desktop`. "Supervisor `:N`" is line N of that file. |
| The native home | One program that draws the picture, the bar, the search and toasts without the game. It grows out of `os/config/usr/libexec/aresos-laptop-home` ("laptop home `:N`"). Working name: `aresos-home`. |
| Home output | The screen the world shows on, or would show on (package 23c's rule). |
| Covered | A window fills the output: one on it is maximized or full-screen and not minimized. That is today's rule, applied per output. A full layout counts once the covering package ships (T372/T373). The world's own window, the start-up cover and the black screen never count. |
| Still | A picture of the world's last frame, made by the mod, kept in his cache folder. |
| Pending start | His own request to start the world that waits for memory. One durable record of the supervisor's, never a timer (section 6). |
| Gate | A condition that a test must show before a package starts (section 13). |

---

## 1. The decisions in short

1. **The home has three layers.** The helper holds the facts. The native home shows what must show without the game.
   The world is the third layer, and it is optional.
2. **One native program, always running.** It draws the picture, the bar, the search and toasts. A GTK program costs
   about 50 MiB each, so these are surfaces of one program.
3. **It is the laptop home, grown.** That file is split into modules first. `linux-desktop` leads the program and
   the hub leads its content modules.
4. **The helper lives as long as the supervisor.** Today it is started for each game launch. It must run with no
   game at all, its restarts must never stop for good, and every new helper gets the running launch's nonce.
5. **The helper is the one source** for programs, My apps and pins, windows and outputs. `aresos-shell/1.3` adds
   `apps_state`, `activate_app`, `screens`, the window list, and search for a view.
6. **A left click means "open or bring back" everywhere**: bar, hotbar, gate, `/name`, search. "New window" is a
   right click on the world's hotbar slot and a row in the outside bar's menu.
7. **Both bars stay** (the owner, T483). In the world: the game's own hotbar, with open and active marks. Wherever
   the awake world is not in view: the bar outside.
8. **A bar on every screen, by one rule** (the owner, T484 and T485; section 8). It is `shown` on a screen nothing
   fills, also one with part-screen windows, and reserves its height there. It waits at the bottom `edge`, reserving
   nothing, while a window fills the screen. On the home output it reserves nothing while `world` is not `off`, and the awake world's own hotbar is the bar there.
9. **Search is outside the game.** Super opens it over anything, on the home output. Nothing is minimized for it.
10. **The picture is a background surface** on every output where the awake world is not showing. The default is a
    plain picture in the look (the owner, T482). Black, a picture of his and the town are the other kinds.
11. **World off closes the game and Prism.** It is a setting and holds across restarts. In OFF only his own request
    starts the world. Off is refused while there is no launcher outside the game.
12. **A sleeping world is never a frozen window on screen.** Its still is on the picture and its window is
    minimized before anything is frozen.
13. **The supervisor owns stop and admission.** It alone starts, stops, freezes and thaws the world. A stop of a
    sleeping world needs no thaw and is not a crash. A start out of OFF and every wake is admitted, not forced.
14. **The world is the one to give way** when memory is full, and by the supervisor's own hand. Today nothing makes
    that true. It is an aim until gate 3 shows it.
15. **Three gates** stand before the two packages that could hurt him (section 13). Package 7, the switch, waits for
    gate 2. Package 9, the sleeping world, waits for gates 1 and 3. Packages 1 to 6 and 8 wait for none.
16. **There is always a way back.** Section 12 has the chain. Its last link is a message window, never a start.

---

## 2. What he will see

- **Working in a full-screen app.** The bar is hidden. He moves the pointer to the bottom edge and rests there for
  a third of a second. The bar slides up over the app. Chrome's slot is marked open and lit as active. He clicks
  Terminal: its window comes back. The pointer leaves the bar and the bar slides away.
- **Building with the world off.** He turns the world off. The world is saved and closed. The screen shows a plain
  picture in the look, or black, or his own picture. Super's search, the bar and every app work as before. About
  1.4 GiB is free again. The world stays off until he turns it on.
- **With the monitor plugged in** (package 23c's plan). The world moves to the monitor. The laptop's screen shows
  the picture behind its apps, with its own bar. Windows there stop above the bar.
- **The world asleep** (package 9, after its gates). Its last view stays on screen, and the bar stands where the
  hotbar stood. A click on the view brings the world back to life. On a full laptop a line says the world is waiting
  for memory, and his apps stay.

---

## 3. Today, from the code

Facts read in this checkout. They are why the three wishes cannot be met by settings alone, and what the new
states must fit into.

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
| The home the mod publishes is kept in memory only. | helper `:3094`, `:3514-3526` |
| The supervisor's states are SETUP, STARTING, IN_WORLD, AUTH_REQUIRED, RECOVERY and STOPPING. Its command list has no `search`, no world switch, no freeze. Its private environment list has no view token. | supervisor `:328-329`, `:4783-4785`, `:182-184` |
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
| The world's window is maximized, frameless and always below. Alt+Tab lists it. `rc.xml` binds no lone Super; its one Super chord is Super+Ctrl+Escape. It has no `<mouse>` section, and nothing sets a background colour. | `os/config/usr/share/aresos/labwc/rc.xml:20`, `:22`, `:34-38`; `os/config/usr/share/aresos/labwc/autostart` |
| A left click on a hotbar slot with the free pointer ends in `open_app`. Any other click there, a right click too, enters the world. The search's Enter ends in `open_app`. The search is a game screen and needs a ready world. A 1.2 mod frees the mouse on any `background`. | `mod/src/client/java/dev/aresos/client/HomePointer.java:36-53`, `mod/src/main/java/dev/aresos/focus/PointerRules.java:20-22`, `WorldSearchScreen.java:125-127`, `ShellFocusClient.java:61-65` |
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

- **One program, in a scope of its own** (`aresos-home.scope`), started by the supervisor at the session's start,
  from package 3a on. It runs in every state of the world and is never part of readiness. It outlives a supervisor
  restart; the new supervisor finds it by its unit name and starts no second one.
- **Its restarts never stop for good.** After it ends: 2, 10 and 30 seconds, then every 60. LAPTOP-HOME.md's "then
  no more in this session" ends, because with the world off this program holds the bar and the search.
- **Why one program.** The laptop home measured 52 MiB with one picture and 61 MiB after a redraw
  (`docs/design/LAPTOP-HOME.md:327-328`). Five such programs would be about 250 MiB at rest. The owner called
  300 MB "crazy much" for a home screen.
- **Why the laptop home.** It already has the view connection with its token, reconnecting, a sandbox for decoding,
  a model with hotbar slots and a finder with seven kinds of hits.
- **What changes in it.**
  - More than one output; a bar surface apart from the picture; the finder as an overlay; static pictures.
  - Its own hotbar, typing line, clock and battery leave, each in the package that ships its replacement: the
    typing line with the search (package 6), the rest with the bar (package 4). Until then the old view keeps them.
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
- **Output names.** The helper reads each output's name, so it and the views mean the same screen.
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
| `screens` | 3a | event `screens` | to the desktop and to views | `{"world": "awake", "screens": [{"name": "HDMI-A-1", "home": true, "world": true, "covered": false, "bar": "none", "reserve": false}, {"name": "eDP-1", "home": false, "world": false, "covered": false, "bar": "shown", "reserve": true}]}`. `world` is `awake`, `starting` or `off`, and from package 9 `asleep`. `off` is every state with no game, also a session that waits for him in the supervisor's window. `"waits": "memory"` is there while a pending start or a wake waits. Per screen: `home` is the home output; `world` is true while the awake world's window is on it and not minimized; `covered` is today's rule; `bar` and `reserve` are section 8's rule. A reader takes a `world` value it does not know as "not awake". |
| `search_view` | 6 | event `search_requested` | to the view `home` | Super, on route 1 of section 8. Sent only to a view that negotiated it. The helper activates nothing and minimizes nothing. |
| `search_view` | 6 | `"screen": "world"` on `open_app` and `activate_app` | from a view | Allowed from a view in 1.3. It means the home output. Until 23c places windows it is only recorded. |
| (existing `shell_focus`) | 6 | reasons `view` and `view_closed` | to the desktop | The search took the keyboard while the world had it, or gave it back. |
| `notices` | 6 | event `notice` | to views | `{"text": "The world stays on: your home could not be saved."}`. One line for a toast. |
| `view_alive` | 6 | request `view_alive` | from a view | A view that holds the keyboard sends it once a second, from its drawing loop. After three silent seconds the helper tells the supervisor, which ends the native home's scope. |
| `settings` | 7 | request `set_setting` | desktop and views | The helper starts `aresos-settings set` off its loop and replies `accepted` at once. Turning the world off can take a minute; the outcome shows in `screens`, and a refusal comes as a `notice`. |
| `world_power` | 7, 9 | request `wake_world` | views | `{"reason": "anyway"}` from package 7: his "Start anyway" for a pending start. From package 9 also `click`, `pointer` and `home`: a wake. The helper passes it to the supervisor, which decides. |
| `window_list` | 4 | `list_windows`, `windows_changed`, `activate_window`, `close_window`, `go_home` | views | As COMPONENTS.md 4.5 planned them for the overview. The app menu uses the first four. |
| `still` | 8 | event `still_changed`; request `still_shown` | to and from the view `home` | `{"id": 7}`. The view shows that still on the home output's picture and says so with the same number. |

- **Left over from earlier notes.** COMPONENTS.md 4.2 proposed "a field that says which apps have a minimized window"
  and "bring back this app's window". Those are `apps_state` and `activate_app`. `world_clicked` (4.3) is unchanged.
- **Views in 1.3** may also send `activate_app`, the window requests, `set_setting`, `wake_world`, `still_shown` and
  `view_alive`.
- **From the search, in COMPONENTS.md 4.5's order** (`docs/design/COMPONENTS.md:1204-1208`): the search closes its
  surface, waits for one round trip to labwc, reports `view_focus` false, and only then sends `activate_app`.
- **Never sent to the game or a view:** a command, arguments, an environment, a path other than `icon`. As today.

### Other interfaces

| Interface | Change |
|---|---|
| Lifecycle channel (mod and supervisor), 1.0 to 1.1 | Capability `still` (package 8): `{"op": "still", "id": n}`, answered `still_saved`. The mod writes one frame without its interface to a fixed file, `aresos/home/still.png` in his cache folder, whole or not at all. The supervisor never takes a path from the mod. Capability `sleep` (package 9): `sleep`, `wake` and `resume`, in outline in section 9. Gate 1 fixes their exact form. A mod without `sleep` never sleeps. |
| Supervisor to helper (status socket) | Packets beside today's `windows`: the live launch's nonce with its keep-foreground flag, and the world's state (package 1); a notice (package 6); a still's number (package 8). Each is acknowledged, and the first two are sent again to every new helper. Super stays SIGUSR1, as 23c plans it. |
| Helper to supervisor (status socket) | Lines beside today's: `ack`; the outputs with the home output; whether the view `home` is connected and what it negotiated; a view that stopped answering; his "Start anyway"; from package 8 `still_shown`; from package 9 a wake request with its reason. |
| Supervisor commands | `aresos-desktop world on`, `world off` and `world on --anyway` (package 7), `wake` (package 9), beside 23c's `search`. |
| Settings (`aresos-settings`) | Three names: `world` = `on` or `off` (default `on`); `picture` = `plain`, `black`, `file` or `town` (default `plain`); `picture-file`, the program's first value that is not one of a list: an absolute path to a file he can read, checked when set. Setting `world` ends in one supervisor request. In which order the file is written and the supervisor is asked, and what a crash between the two leaves, is gate 2's row 4. |
| `publish_home` | The wire is unchanged. |

---

## 6. The world-off switch

**What it is.** The setting `world`. Off means the home is the picture, the search and the bar. It holds until he
turns it on again, across restarts of the laptop.

**Where he flips it.** In the world: a row in the AresOS menu (Esc). Outside: Super's search shows "Turn the world
on" as its first row while the world is off, and from package 4 the Home slot's menu has both directions. By
command: `aresos-settings set world off`, which Claude can run for him. All end in the same supervisor request.

**Off needs a launcher outside.** The supervisor refuses to turn the world off unless a view `home` is connected
that negotiated the search and answered its alive beat within the last few seconds. A silent or hung view counts as
absent. A notice says why. So he never trades the hotbar for nothing. Package 7 needs package 6
and 23c's Super key for the same reason (section 10).

**What happens to the game and Prism: both are closed.** Not frozen, not swapped.

- His goal is memory while building. A frozen game keeps its memory until something pushes it to swap. Only a closed
  game gives all of it back for certain.
- Turning off is the supervisor's planned stop (package 25): the stop record, a confirmed save, SIGTERM, the wait for
  Java's real exit and the lock.
- **If the save is not confirmed, the world stays on.** The stop is called off as today (supervisor `:3370-3378`).
  The setting stays on, and a notice says why.
- **Off shows the chosen picture.** No still is made for it. Stills arrive with package 8.
- **A sleeping world is closed without a thaw** (package 9; gate 1).
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
| `town` | His town from the side, by day, as LAPTOP-HOME.md designs it. Kept as a kind, not the default. It costs nothing extra: its model and painter are on main, and package 3a only places that drawing on the picture surface. It takes no clicks and has no bar, clock or battery of its own. If placing it shows a cost beyond that, the kind is left out. |

A click on a picture does nothing. From package 9 a click on a still wakes the world (section 9).

**How the world comes back.** He turns the switch on. The supervisor admits the start and then starts the game as
it does today.

- Admission is the supervisor's, at two doors: before Prism is spawned, and again at the gate every JVM passes
  (section 12 has the test).
- On a full laptop the start is not refused and not forced. It becomes a pending start. `screens` says `waits`, and
  a toast says: "Memory is nearly full. The world starts when there is room."
- "Start anyway" is his own call: the search's first row while a start is pending, later the Home slot's menu, and
  `aresos-desktop world on --anyway`.
- With no app window open, today's start-up cover hides the loading screens.
- With an app window open there is no cover: it must never hide his apps. Until package 8 the loading screens show
  behind his windows. From package 8 the world's window stays minimized until the world is ready.
- A start takes as long as a start at boot. Board T362 measures that.

**The supervisor's states**

| State | Game and Prism | The home output shows | New with |
|---|---|---|---|
| SETUP, AUTH_REQUIRED, RECOVERY | none, or waiting for him | the message window over the picture | |
| STARTING | starting | the cover; from package 8 the still | |
| IN_WORLD | running | the world | |
| OFF (`off`) | none | the chosen picture | package 7 |
| OFF (`quit`) | none, until he starts it or logs in again | the chosen picture | package 7 |
| ASLEEP | frozen, saved | the still | package 9 |
| WAKING | thawed, still paused | the still | package 9 |
| OFF (`asleep`) | none: a sleeping world was closed | the still | package 9 |
| STOPPING | being stopped | black, or his apps | |

**How OFF is entered and left** (package 7). The sleeping states' steps are in outline in section 9.

| From | Event | To |
|---|---|---|
| any state with a running game | the world is turned off, and the save is confirmed | STOPPING, then OFF (`off`) |
| the same | the save is not confirmed | back where it was; the setting stays on |
| any state with a running game | his own quit, or a plain `stop` | OFF (`quit`), for this session |
| a boot with `world` off | | OFF (`off`): helper and native home, no Prism |
| OFF (`off`), OFF (`quit`) | his request (the switch, a menu row, `world on`), admitted | STARTING |
| the same | his request, not admitted | OFF, with a pending start |
| OFF with a pending start | a later sample admits it | STARTING |
| OFF with a pending start | world off, `stop`, `logout`, a shutdown, the session's end | OFF, and the pending start is gone |

**OFF starts nothing by itself.**

- Only his own request starts a world in OFF. No timer is armed: no backoff restart, no wake. A wake request that
  reaches the supervisor in OFF (`off`) or OFF (`quit`) is logged and dropped.
- The gate every JVM passes (supervisor `:2182-2236`) refuses in OFF, also for Prism's own launch button.
- `restart` and `retry` in OFF (`off`) start nothing and answer with one line that names the switch.
- If the native home keeps failing in OFF, the supervisor opens its message window. It does not start the world
  (section 12).
- The first start ever (SETUP, the sign-in) needs the world on. The default is on.
- **What makes these rules hold across a crash, a new supervisor and an old restart deadline is gate 2.** Package 7
  does not start before it passes.

**Memory in both states**

| State | The game | Prism | The native home | Source |
|---|---|---|---|---|
| World on, today | about 1,019 MiB (its scope's anonymous memory; soft limit 2,560 MiB) | about 418 MiB while the game runs | not running | The laptop on R28, 2026-11-21 (`docs/HUB-HANDOFF.md:46`) |
| World on, this design | the same | the same | about 60 MiB with no picture surface | 53f's measurement of the laptop home; an estimate for the new program |
| World off | 0 | 0 | about 60 to 80 MiB | estimate from the same measurement |

- Turning the world off frees about 1.4 GiB of the laptop's 16.
- These are single readings of a settled world, not of a start. What a start needs at its peak is not measured;
  gate 3 measures it.
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

**What each output shows.** The bar's state on each is section 8's rule.

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
rectangles. The start-up cover and the black screen never cover. Two things read it. The world pauses only while
the home output is covered (`shell_covered`, unchanged for the mod). And an output's bar waits at the edge while
that output is covered (section 8).

**Where apps open, and where focus goes**

- An app opens on the screen the pointer is on (23c). A click in the laptop screen's bar opens the app there.
- The search opens on the home output, and its app opens there, as the owner chose on board #334. With two screens
  that needs 23c's placement (Known limits).
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
| Home | First slot. World awake: a click goes home, and what covers the world goes down by today's rule. Asleep: it wakes the world. Off: it opens the slot's menu, whose first row is "Turn the world on". The menu also has the picture and, while a start is pending, "Start anyway". |
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
- **In the world** a right click on a hotbar slot with the free pointer opens a new window (`open_app`). That
  gesture is new in package 2: today any click there but the left one enters the world
  (`mod/src/main/java/dev/aresos/focus/PointerRules.java:20-22`). Using an app item he holds, with the pointer in
  the world, is a different path and is left as it is.
- **A failed launch** shows the helper's words as a toast above the bar for five seconds.
- **The picture in a slot** is the app's logo as the mod published it (laptop home `:1751-1758` draws slots from the
  published cells). An open app outside My apps shows its catalogue picture.

### Where it shows: one rule

One bar on every output, the same content on each (the owner, T484). The helper works the rule out and says it in
`screens`, as `bar` and `reserve`. The native home only follows it. For each output, the first row that holds:

| # | On the output | `bar` | The bar | `reserve` |
|---|---|---|---|---|
| 1 | A start-up cover or the black screen is up. | `none` | Hidden, and no strip. | no |
| 2 | A window fills it (covered). | `edge` | Hidden. A strip at the bottom edge waits for the pointer. | no |
| 3 | The awake world's window shows on it. | `none` | Hidden, and no strip. The world's own hotbar is the bar there (the owner, T483). | no |
| 4 | Anything else: the picture, a still or a starting world, with or without part-screen windows. | `shown` | Visible, on the top layer. | yes, except on the home output while `world` is not `off` |

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
  `off`. That one phrase is the rule wherever this note mentions the zone.
- **No resize loop.** `edge` follows covering, and covering follows the maximized and full-screen states, not
  sizes. A maximized window covers its output whatever the zone is.
- **A full layout** counts as filling once the covering package ships. That is one condition in the helper.

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
(`STATE.md:204`). Super must pass in every state, and also when only a view is connected.

---

## 9. The sleeping world

This note gives board T364 its place. It does not design swap, prefetch or when the world should sleep. After the
lead's scope decision it also does not fix the crash-safe mechanism or the memory rules. Those are gates 1 and 3
(section 13), and package 9 starts after them.

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
from the first version of this note, so the desktop's packages are still 3, 4 and 5.

| # | Package | He sees | Lead | Needs | Size |
|---|---|---|---|---|---|
| 1 | **The helper for the session.** Started once per supervisor. The launch's nonce and keep-foreground flag handed over, acknowledged, and sent again to every new helper. Launches made at the JVM gate covered. Restarts that never stop. The home kept on disk. Output names. 23c's view token. | Nothing. Opening no longer breaks when the helper or the game restarts. | aresos (supervisor) with hub (helper) | Nothing. It reads 23c's plan first. | L |
| 2 | **Open apps and "bring back".** `apps_state` and `activate_app`, with `open_app` kept as the fallback. The mod marks hotbar slots, sends `activate_app` from a left click, gates and `/name`, and adds the right click on a slot. | Open and active marks on the hotbar. A left click brings Chrome back with its tab. A right click opens a new window. | hub | Nothing. Beside 1. | M |
| 3a | **The picture, one screen.** First the laptop home split into modules: no change in what it does, nothing removed. Then the program started by the supervisor, the view `home`, `aresos-picture` with `plain`, `black` and `file`, the converter, the picture settings, `screens` from the helper, and Root clicks that do nothing. | The plain picture wherever no world shows, for example behind the sign-in window. | desktop, with hub for `screens` and aresos for the start | 1 | M |
| 6 | **Search outside.** The finder as `aresos-search`. Super's one route. The alive beat. The recovery key's third action. `notice`, and a first `aresos-toast` in look A. | Super works over any app and minimizes nothing. | hub, with desktop for the surfaces | 2, 3a, 23c's Super step | M |
| G2 | **Gate 2's step.** OFF, its records and the two doors in the supervisor, reachable by command only and only in the test rig. The image's command refuses OFF until package 7 ships. | Nothing. | aresos | 1 | S |
| 7 | **The world-off switch.** The setting, the row in the AresOS menu, the search's first row, Prism's scopes, the memory check on the laptop. Off shows the chosen picture; no still yet. | The switch. | aresos with hub | 6 (so 1, 2 and 3a), gate 2 | M |
| 4 | **The bar outside.** `aresos-bar` in look A, slots and marks, the app menu, the window requests, and section 8's rule with its zone. | A bar on the picture. Windows stop above it where it reserves its height (section 8's rule; not on the world's screen). The Home slot's menu. | desktop (surface) with hub (content) | 2, 3a, 6 (toasts) | L |
| 5 | **The bar at the bottom edge.** The strip, reveal and hide, tested against B321's barrier. | The pointer at the bottom edge brings the bar up over an app. | desktop | 4 | M |
| 3b | **The second screen.** The picture and the bar on the output without the world, and the hotplug rules. | With the monitor in, the laptop screen shows the picture and a bar. | desktop with aresos | 3a, 4, 23c | S |
| 8 | **Stills and the quiet start.** The lifecycle channel's `still`. A still before every planned stop. The boot path. The world's window minimized until ready. | Boot shows his home at once; it comes alive when ready. | hub (mod) with aresos | 3a, 4 | L |
| T364 | **The study: gates 1 and 3.** Its rigs and its measurements on the image. | Nothing. | hub with aresos | Nothing. Package 8's stills help its rig. | L |
| 9 | **The sleeping world.** `sleep`, `wake`, `resume`, the sleeping states, the wake signals. | The world sleeps and wakes. | hub with aresos | 7, 8, gates 1 and 3 | L |

**Packages 1, 2, 3a, 3b, 4, 5 and 6 depend on no gate. Package 8 depends on none either:** it adds stills and a
hidden start, and no sleep, freeze, wake or new start. If its brief grows one of those, gates 1 and 3 apply to it.

**What must still work after each package**

| After | Must still work | Shown by |
|---|---|---|
| 1 | The world's hotbar, gates, `/name`, the mod's search and Super's route to it, with any helper that replaces the first. | Under a running world: kill the helper; replace the supervisor; start the game from Prism's own window. Each time the mod's next hello is accepted and a hotbar click opens an app. A restart after a crash still waits below the app in front. |
| 2 | Opening from the world against a helper without `activate_app`. The laptop home's 1.2 view. | The mod against a 1.2 helper sends `open_app`. The 1.2 example messages pass unchanged. |
| 3a | All that the laptop home does today. | Its tests pass unchanged after the split. No surface, slot or typing line is removed. |
| 6 | Super over an awake world when the native search is absent, silent or hung. | Kill the native home: Super reaches the mod's search. Stop it mid-search: the alive beat ends it within seconds, and then Super does. The recovery key ends it with the supervisor stopped. |
| 7 | A launcher at every moment, and the way back. | With the native home killed, and again with it stopped (hung), turning the world off is refused with one line. In OFF, `world on` from the recovery terminal starts the world. |
| 4 | The world's own hotbar, untouched. | The mod's tests. The old view's slots, clock and battery leave only in this package. |
| 8 | The start-up cover when there is no still, and every recovery window in view. | A first boot shows the cover. A slow start shows `slow_start` over the still. |

**Dropped:** package 10, "One bar". The owner keeps both bars (T483). Both look alike in look B, so one bar stays
possible later as a setting if he changes his mind.

**Later, each its own package:** system notifications in the toast surface (desktop); a program's own actions in its
menu, such as a private window (hub: the helper parses no action groups today); pinning while the world is off (hub);
look B for the bar, with the desktop's look work; a full layout that counts as filling, with the covering package.

**Order notes**

- Package 2 is the try-out's fixes 7 and 10 on the final protocol. It can start now, beside package 1.
- **The switch comes before the bar.** The owner asked for it first, and the search alone is a launcher. Between
  packages 7 and 4 an off world has Super's search, Alt+Tab and the picture, and no bar. Until package 5 there is no
  bar over a maximized app.
- **What the switch needs from the bar's package has moved forward.** `screens` comes with 3a, and `notice` with a
  first toast comes with 6. So package 7 can say that the world is off, that a start waits, and why a request was
  refused.
- **Gate 2's step comes first, and alone.** It builds OFF in the supervisor with no setting, no menu row and no
  caller. Nothing of the switch that he can reach is built before its tests pass.
- **Only 3b waits for the monitor work.** The search needs 23c's Super step alone: the key binding and
  `aresos-desktop search`. If 23c is later, `linux-aresos` pulls that step forward. With two screens the search's
  app opens on the home output only once 23c places windows.
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
- **Windows stop above a visible bar.** On a screen with the bar showing, a maximized window first fits above the
  bar and then takes the whole screen as the bar slides away.

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
sleeping world wakes on a click, that turning the world on never covers his apps, and that an off world stays off.
The desktop will show him the bar's look in its own component pictures. The T364 study will ask how soon the world
should sleep, with measured wake times.

---

## 12. Risks, known limits, assumptions

### Real harm, and how the structure answers it

| Harm | Answer |
|---|---|
| **Lost building work when the world is turned off or put to sleep.** | Both go through a confirmed save. Without it, off is called off and sleep does not happen. |
| **A stop or shutdown that hangs on a sleeping world; a sleeping world taken for a crash; a paused world nobody resumes.** | Gate 1. Package 9 does not start before a rig shows that none of the three can happen. |
| **Memory is full when the world should start or wake** (the owner's worry). | See below, and gate 3. Until it passes, nothing thaws or starts a world by itself beyond what does so today. |
| **The world starting by itself after he turned it off.** | In OFF only his own request starts it (section 6). Gate 2 shows that this holds across a crash, a new supervisor, an old restart deadline and Prism's own button. |
| **An off world with no way to open an app.** | Off is refused while no view `home` with the search is connected (section 6). |
| **A home that cannot come back.** | A chain, each link independent of the one before: (1) the native home is restarted when it ends, for as long as the session lasts; (2) the world's own hotbar and the mod's search never depend on the native home; (3) in OFF, after the native home's third failed start, and whenever Super finds no view and no awake world, the supervisor opens its message window. It says how to try the bar again (`retry`) and how to start the world (`world on`), and it starts nothing; (4) the same commands work from the recovery terminal; (5) if the world cannot start either, today's recovery window says why. His open apps stay reachable by Alt+Tab throughout. |
| **A hung search that holds the keyboard.** | Three ways out. The search sends an alive beat from its drawing loop; after three silent seconds the supervisor ends the native home's scope. The recovery key gets a third action, first in line, that kills `aresos-home.scope` through the user manager. It needs no supervisor and no helper, and it is what lets the terminal get the keyboard (`docs/design/COMPONENTS.md:1204-1208`). And Escape or a click outside closes a search that still answers. The program keeps no state of its own, so ending it loses nothing. |
| **A dead session because a new piece fails.** | The native home is never part of readiness. Its restarts are spaced and never end the session. From package 3a a click on a bare desktop does nothing: labwc's built-in root menu may hold Exit. |
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
   one way: he can turn the world off.

What he notices on a full laptop once all of it is built: his apps stay, the home stays usable, and the world comes
back later.

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
- **A window maximized on a screen with a visible bar** resizes once more as the bar leaves.
- **A toast is on the top layer,** so a true full-screen window hides it. A launch that fails meanwhile is in the
  helper's log.
- **Between packages 7 and 4** an off world has no bar, and until package 5 none over a maximized app. Super's
  search covers that time.
- **Until 23c places windows,** the search's app opens where labwc puts it when two screens are on. The `screen`
  hint is only recorded.
- **After Super woke a sleeping world** because no native search was there, the search does not open by itself. He
  presses Super again.
- **With the world off:** no gates, no `/name`, no pin changes. A program installed meanwhile joins My apps when the
  world next runs. The search finds it at once anyway.
- **A window nobody owns** has no slot in the bar, and its app starts a new instance on every left click. Ownership
  needs a reviewed identity; a hint fixes a known program.
- **Two rankers** for the search, one in the mod and one outside, kept in step by shared test cases.
- **The still can be old** after a crash, since it was made at the last sleep or planned stop. After a hotplug it is
  scaled to the new screen until the world wakes.
- **At sleep in view** the world's hotbar gives way to the bar outside at the same place. They look alike in look B,
  not in A. The bar's slots show the 12 × 12 logo, the hotbar the item icon.
- **Turning the world on with apps open** shows Prism's own window for a moment, and it may take the focus. Package 8
  hides only the game's window.
- **A helper or supervisor restart** leaves the bar on its last state for a few seconds.
- **A shutdown while no supervisor answers** waits the guard's own times, up to 72 s, also with a sleeping world.
  Gate 1 only keeps a false `unsaved` latch from following it.
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
- That labwc 0.9.6 honours an exclusive zone that changes on a live layer surface, and what it does to windows that
  are already maximized then.
- That labwc 0.9.6 offers `wl_output` version 4.
- That activating a minimized window brings it back, and that `unset_minimized` does not take the focus.
  COMPONENTS.md lists both as open.
- That an overlay surface with exclusive keyboard gets the keyboard while the game holds a pointer lock, and that a
  window gets the keyboard back when that surface's program is killed.
- What labwc's built-in root menu holds.
- That minimizing the world's X11 window from outside hides it without the game's help.
- That Minecraft loads normally while its window is minimized (package 8), and that the mod can ask for its own
  window back.

In package 1: that the mod tries its hello again after a refusal.

Release checks (review 2, finding 6):

- The recovery key ends a hung search that holds the keyboard, with the supervisor stopped.
- Prism stays open after the game exits, and keeps its sign-in through SIGTERM.

The sleeping world's and the memory checks are rows of gates 1 and 3 now.

Not read or not there:

- The image has no notification service today.
- The laptop's swap set-up and the image's effective systemd-oomd settings were not read; the T364 study and
  `linux-aresos` own them.
- 23c's move of the world is a plan. Brief 328 was not in the checkout.
- For this revision these were read again: the supervisor's start, adoption, JVM gate, stop end and guard command;
  the helper's hello, `open_app`, `windows` report and Super route; the mod's pointer rules; the image's memory
  drop-ins. The helper's discovery and picture parts were read only in passing.

### The OS part, from `linux-desktop`

Written by `linux-desktop` on 2026-11-21 (`reviews/332-outside-game-design/INPUTS-1.md`) and folded in here, with
its point for revision 2 about the zone on the home output. The sections above use these names and rules.

**Layers** (wlr-layer-shell on labwc 0.9.6)

| Surface | Namespace | Layer | Keyboard | Details |
|---|---|---|---|---|
| Picture | `aresos-picture` | background | none | Anchored on all four edges, exclusive zone -1. Its input region is the whole output, so a click on it never reaches labwc's Root context. |
| Bar | `aresos-bar` | top while `shown`: above windows, below a true full-screen window. Overlay while revealed, by `set_layer` (layer-shell version 2 or later), and back to top when it hides. | none | Anchored bottom, left and right. Exclusive zone: the bar's height while `shown` with `reserve` yes; 0 in every other case. So it is 0 at `edge`, at `none`, while revealed, and on the home output while `world` is not `off` (awake, asleep or starting). So it is the bar's height only while `shown`, on every output except the home output while `world` is not `off`. Its menus are popups on it, pointer only. |
| Strip | `aresos-bar-edge` | overlay | none | It exists only while that output's bar is `edge`. 1 logical pixel high, full width, exclusive zone -1, a transparent buffer with an input region. |
| Search | `aresos-search` | overlay | exclusive while open | Esc, a click outside, or the recovery key ends it. |
| Toast | `aresos-toast` | top | none | An empty input region, so clicks pass through, as with the indicator. Not over a full-screen video. |
| Indicator | as package 320 built it | overlay | none | It stays above all of these. |

- No surface uses the namespace `aresos-input-barrier`. B321's labwc patch treats that one as the capture surface.
- **Why 0 on the home output:** a zone also re-fits the world's own maximized window. Every switch between `none`
  and `shown` would resize the game, with a new layout and a still that no longer fits.

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
- The picture covers that from package 3a on. Package 3a also makes the Root context's clicks do nothing, for when
  no picture is up.
- Nothing else in `rc.xml` for packages 3 to 5. The bar takes no keys, and Super stays 23c's.
- The recovery key's third action is package 6's, not the desktop's.

**Packages.** 3, 4 and 5 are `linux-desktop`'s. Each gets its own brief from `linux-desktop` once this note is
reviewed. Package 5 also tests the 1-pixel strip against B321's barrier in its harness.

---

## 13. Gates for the world-off switch and the sleeping world

A gate is passed by a test, not by an argument. Until it passes, the package it blocks gets no brief. This note
decides what each gate rests on. The mechanism that passes it is the gate's own work.

| Package | Waits for |
|---|---|
| 1, 2, 3a, 3b, 4, 5, 6 | no gate |
| 7, the world-off switch | gate 2 |
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
   (`os/config/usr/share/aresos/labwc/rc.xml:22`). The still stays or the world is woken, and he is told if it
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

**Blocks:** package 7. Package 9 builds on it for OFF (`asleep`). **Passed by:** `linux-aresos`, with a short
design step for the supervisor and the step G2 of section 10. **Rests on:** section 6's rule that only his request
starts a world in OFF, and section 12's rule 2. **From:** review 2, point 2.

What must be true:

1. **Only his request starts a world in OFF.** Not a timer. Not a restart deadline kept from before (supervisor
   `:1786-1812`). Not a wake signal. Not a new supervisor that reads the setting. Not Prism's own launch button.
2. **Two doors.** The decision is applied before Prism is spawned (supervisor `:1982-1995`) and again at the gate
   every JVM passes (supervisor `:2182-2236`).
3. **OFF survives a new supervisor, in the same kind.** OFF (`quit`) is kept for the session, as today's quit is
   (supervisor `:1779-1784`, `:1796-1812`).
4. **Off and on are all or nothing.** A crash between the stop's end and the setting's write, or between the
   setting's write and the start, is settled by the next supervisor: either the world is closed and the setting is
   off, or the setting is on and the start goes through the doors. The design step fixes the order of the write and
   the request.
5. **A waiting start is one record.** His request that is not admitted is kept in the supervisor's durable state.
   It survives a new supervisor. It is tested again only on the sampler's schedule. It starts the world once. These
   end it: world off, `stop`, `logout`, a shutdown, the session's end. Nothing but his request creates it.
   `screens` shows it as `waits`.
6. **Admission fails closed.** A sample that cannot be read, or an old one, admits nothing. "Start anyway" is his
   act at that moment and is never stored.
7. **A latch still holds.** Turning the world on does not clear what only `retry` may clear.

How a test shows it. The supervisor takes its runner and its clock from outside, so each row is a plain test:

- **Replacement.** In each kind of OFF: a new supervisor on the same files, and the clock moved past every old
  deadline. No Prism is spawned, and the kind is the same.
- **Doors.** A wrapper's `jvm_start` in each kind of OFF is refused, with a line that names the switch. So are
  `retry`, `restart` and every wake signal in OFF (`off`).
- **Crash points.** The two of row 4. Each ends in one of its two settled states.
- **The pending start.** It is made only by his request, survives a replacement, starts once on the first clear
  sample, and is gone after each event of row 5. An old or unreadable sample never admits it.
- **On a test image,** one pass in a VM (never the owner's laptop before package 7): world off, a reboot, and neither Prism nor Java runs. Then `world on`
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
