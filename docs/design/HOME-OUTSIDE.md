# The home's parts outside the game

**Status.** Design note for board brief 332, written 2026-11-21 by one Fable design agent with read-only tools.
Nothing here is built. It decides the structure for the hub (`linux-hub`), the desktop (`linux-desktop`) and the
supervisor (`linux-aresos`). `linux-desktop` adds its OS details afterwards; section 12 lists the slots left for it.

**Sources.** The documents and code the brief names, as they are in this checkout. `briefs/328-look-around.md` was
not in the checkout, so only what brief 332 says of it is used. No measurement was made for this note; every number
names where it comes from.

**Words used below**

| Word | Meaning |
|---|---|
| The world | The Minecraft home: the game, its window (`aresos-desktop`) and the mod. |
| The helper | `os/config/usr/libexec/aresos-shell`. |
| The supervisor | `os/config/usr/libexec/aresos-desktop`. |
| The native home | One program that draws the picture, the bar and the search without the game. It grows out of `os/config/usr/libexec/aresos-laptop-home`. Working name: `aresos-home`. |
| Home output | The screen the world shows on, or would show on: the monitor when one is on, else the laptop's panel (package 23c's rule). |
| Covered | An output whose usable area is filled by windows (board T372/T373). |
| Still | A picture of the world's last frame, made by the mod, kept in the owner's cache folder. |

---

## 1. The decisions in short

1. **The home has three layers.** The helper holds the facts. The native home shows what must show without the game.
   The world is the third layer, and it is optional.
2. **One native program, always running.** `aresos-home` draws the picture, the bar, the search, the app menu and
   toasts. A GTK program costs about 50 MiB each, so these are surfaces of one program, not five programs.
3. **It is the laptop home, grown.** That program already has the helper connection, the town, a hotbar, a finder,
   Cairo-only drawing and its tests. It gets more outputs and more surfaces, and a new name.
4. **The helper lives for the session.** Today it is started for each game launch. It must run with no game at all.
5. **The helper is the one source** for programs, My apps and pins, windows and outputs. `aresos-shell/1.3` adds
   `apps_state`, `activate_app`, `screens`, the window list, and search for a view.
6. **A left click means "open or bring back" everywhere**: bar, hotbar, gate, `/name`, search. It is one request,
   `activate_app`. "New window" is a row in the app's menu and uses today's `open_app`.
7. **The bar is outside the game.** One per output, in the look. It reserves no screen space. It shows while its
   output is not covered and waits at the bottom edge while it is.
8. **The in-game hotbar stays for now.** It keeps working until the outside bar can stand on the world's screen,
   which needs the free cursor of brief 328. After that it is the fallback when the native home is gone.
9. **Search is outside the game.** Super opens it over anything, on the home output. Nothing is minimized for it.
10. **The picture is a background surface** on every output where the awake world is not showing. Its kinds: the town
    (default), black, a picture of his. A world that sleeps or starts shows its still there.
11. **World off closes the game and Prism.** It is a setting, applied by the supervisor's planned stop, and it holds
    across restarts of the laptop.
12. **A sleeping world is never a frozen window on screen.** The still goes onto the picture, the world's window is
    minimized, and only then is the game frozen.
13. **The world gives way first.** Sleep needs a confirmed save. A wake is admitted only when memory allows. If the
    system must kill something, it is the world, which has lost nothing.
14. **There is always a way back.** Section 12 has the chain: hotbar fallback, the world turned on by itself, the
    recovery key.

---

## 2. What he will see

- **Working in a full-screen app.** The bar is hidden. He moves the pointer to the bottom edge and rests there. The
  bar slides up over the app. Chrome's slot is marked open and lit as active. He clicks Terminal: its window comes
  back. The pointer leaves the bar and the bar slides away.
- **Building with the world off.** He opens the Home slot's menu in the bar and picks "Turn the world off". The world
  is saved and closed. The screen shows his town from the side, or black, or his own picture. The bar, Super's search
  and every app work as before. About 1.4 GiB is free again.
- **With the monitor plugged in.** The world moves to the monitor. The laptop's screen shows the picture behind its
  apps, with its own bar. The cursor crosses between the screens.
- **The world asleep.** Nothing changes on screen: the world's last view stays. A click on it, or closing the app that
  covered it, brings it back to life.

---

## 3. Today, from the code

Facts read in this checkout. They are why the three wishes cannot be met by settings alone.

| Fact | Where |
|---|---|
| The helper is started for each game launch, with that launch's nonce. Without a launch it is not started. | `ensure_helper` and `start_launch` in the supervisor |
| `open_app` always starts a launch. No request brings an app's window back. | `open_app` and `launch` in the helper |
| The helper's window client can activate and minimize a window. It cannot bring one back or close one, ignores titles, and binds outputs without reading their names. | `ForeignToplevels` |
| Which apps have windows goes to views only (`apps_running`). The mod hears only about its own launches (`app_state`). | `report_running`, `set_state` |
| Covering is judged only for the world's outputs, and only while the world's window exists. | `Windows.covering` |
| The home the mod publishes is kept in memory only. | `Helper.home` |
| The supervisor's states are SETUP, STARTING, IN_WORLD, AUTH_REQUIRED, RECOVERY and STOPPING. Its command list has no `search`, no world switch, no freeze. Its private environment list has no view token. | the supervisor |
| The instance keeps Prism open: `CloseAfterLaunch=false`, `QuitAfterGameStop=false`. | `instance_config` |
| The world's window is maximized, frameless and always below. `rc.xml` binds no Super key yet. | `os/config/usr/share/aresos/labwc/rc.xml` |
| A hotbar click and the search's Enter end in `open_app`. The search is a game screen and needs a ready world. | `HomePointer`, `WorldSearchScreen`, `AresOsClient` |
| The game is an X11 window under Xwayland (the comment in `HomeScreen` says so). | `mod/src/client/java/dev/aresos/client/HomeScreen.java` |
| The laptop home is on main: GTK 4 and Cairo, view `laptop-home`, a town model with hotbar slots, a finder and the keys 1 to 9. Nothing starts it yet (STATE.md: step 4 waits for 23c). | `os/config/usr/libexec/aresos-laptop-home` |
| A layer-shell piece in the look already exists: the indicator, with the look pack and `aresos-settings`. | `briefs/320-indicator.md` |

---

## 4. Where each part lives

| Part | Lives in | Content by | Surface and look by | Why |
|---|---|---|---|---|
| The bar's content: slots, marks, what a click does | The helper (the facts) and the native home's bar model | hub | | One model for every bar. |
| The bar's surface | The native home: a layer surface per output | | desktop | It must show with the world off, asleep or covered. |
| The in-game hotbar | The mod | hub | the game | Kept until the outside bar stands on the world's screen. Then the fallback. |
| Search | The native home: an overlay surface, opened by Super | hub | desktop | It must work over a full-screen app and with the world off. |
| Launching | The helper | hub | | It is there already and stays the only place that starts a program. |
| The open-app list and its marks | The helper works them out. The bar draws them; for now the hotbar does too. | hub | | One answer to "what is open". |
| The app options menu | The native home | hub | desktop | One menu. The game gets none of its own. |
| The picture behind the windows | The native home: a background surface per output | desktop; the town is the hub's | desktop | Needed in three cases: world off, world asleep, second screen. |
| The still | The mod makes it; the native home shows it | hub | | Only the game can draw its own frame without windows on top. |
| Toasts and notifications | The native home: a passive overlay, like the indicator | hub for AresOS's lines; desktop for system notifications later | desktop | They must show over apps and with the world off. |
| Status icons (Wi-Fi, battery, sound, clock) | The native home, as part of the bar | desktop | desktop | The bar is on every screen and reachable over every app. |
| The world-off switch | A setting. The supervisor applies it. | hub (behaviour), aresos (supervisor) | | The supervisor alone may stop and start the game. |
| The indicator, the overview | As COMPONENTS.md says | desktop | desktop | Unchanged. The overview may become one more surface of the native home; that is the desktop's call. |

### The native home

- **One program, started by the supervisor at the session's start.** It runs in every state of the world. It is
  never part of readiness.
- **Why one program.** The laptop home measured 52 MiB with one picture and 61 MiB after a redraw
  (LAPTOP-HOME.md section 4). Five such programs would be about 250 MiB at rest. The owner called 300 MB "crazy much"
  for a home screen.
- **Why the laptop home.** It is the natural host. It already has the view connection with its token, reconnecting,
  a sandboxed picture decoder, a town model with hotbar slots and a finder with seven kinds of hits. What is new:
  more than one output, a bar surface apart from the picture, the finder as an overlay, and static pictures.
- **What changes in it.** Its own hotbar and typing line leave the town: the bar and the search replace them on every
  screen. Its own copy of the last home leaves too: the helper keeps the home on disk (section 5).
- **Who owns which code.** The surfaces are the desktop's: layers, outputs, the reveal, the look kit, status icons,
  static pictures. The content is the hub's: the helper connection, the bar model, the finder, menu rows, the town.
  The two halves meet at one small interface inside the program. The content never names a colour or a layer.
- **No fallback window.** Without the layer library the program draws nothing and exits, as the indicator does. The
  supervisor then keeps the world on (section 12).
- **The keyboard.** The bar and the picture never take it. The search and an open menu take it and always give it
  back on Escape.

---

## 5. One source of truth

| Fact | Who makes it | Who keeps it for everyone | Who reads it |
|---|---|---|---|
| Installed programs, their pictures | the helper (desktop entries) | the helper | the mod, the native home |
| My apps, short names, groups, places, pins, logo cells | the mod (`publish_home`) | the helper, **now also on disk** | the native home (bar, town, search), the overview |
| Windows: whose, active, minimized, on which output, title | labwc | the helper | the mod, the native home, the overview, the supervisor |
| Outputs: names, which is the home output, covered or not | labwc | the helper | the mod, the native home, the supervisor |
| The world's state: awake, asleep, starting, off | the supervisor | the helper passes it on in `screens` | the native home |
| Settings: look, world, picture | `aresos-settings` | its file | everyone |

**What this removes.** The laptop home's own file of the last home. A second rule for the home output. A second
covering rule for the bar. A second way to start a program.

**What stays double, on purpose.** The mod's Apps screen and the native search each rank hits in their own language.
One shared file of queries and expected hits, read by both sides' tests, keeps them in step, as the protocol's
example files do today.

### Changes to the helper that are not on the wire

- **Session life.** The supervisor starts the helper once, with the instance and the view token, and with no nonce.
  A new launch's nonce and its keep-foreground flag reach the running helper over the supervisor's status socket.
  A game start no longer restarts the helper, so views stay connected and opening never pauses. Until a nonce
  arrives, a desktop hello is refused.
- **The home on disk.** The helper writes each complete `publish_home` to `aresos/home.json` in the state folder
  (`$XDG_STATE_HOME`), whole or not at all, readable by him only. It loads it at start. `get_home` then answers
  with no game running.
- **Output names.** The helper reads each output's name, so it and the views mean the same screen.
  *To verify:* that labwc 0.9.6 offers `wl_output` version 4.
- **More window requests.** Bring back (`unset_minimized`) and close, beside activate and minimize. Titles are kept.
  The time each window was last active is kept, per app.

### `aresos-shell/1.3`

Everything in 1.2 stays. Each line below is a capability under minor 3 and ships with its package (section 10). A
side that did not offer a capability gets none of it. Example messages go to `mod/src/test/resources/shell-1.3/`.

| Capability | Message | Direction | What it does |
|---|---|---|---|
| `apps_state` | event `apps_state` | to the desktop and to views | `{"apps": [{"id": "chrome", "windows": 2, "active": true, "hidden": false}]}`. Every catalogue app with a window. `active`: one of its windows has the keyboard. `hidden`: all of them are minimized. Sent once after hello and on each change, coalesced as `apps_running` is. `apps_running` stays for 1.2 views. |
| `activate_app` | request `activate_app` | desktop and views | `{"app_id": "chrome"}`. With a window: the helper brings back and activates the app's most recently active window; a layout that went down together comes back whole (COMPONENTS.md 4.3). No launch. Reply `{"state": "activated"}`. Without a window: exactly `open_app` with this request ID, with the same journal and the same rule for duplicates. |
| `screens` | event `screens` | to the desktop and to views | `{"world": "awake", "screens": [{"name": "HDMI-A-1", "home": true, "covered": false, "bar": "shown"}]}`. `world` is `awake`, `asleep`, `starting` or `off`. `covered` is the per-output rule of T372/T373, for every output. `bar` is `shown`, `edge` (hidden, waits at the bottom edge) or `none`. |
| `window_list` | `list_windows`, `windows_changed`, `activate_window`, `close_window`, `go_home` | views | As COMPONENTS.md 4.5 planned them for the overview. The app menu uses the first four. |
| `search_view` | event `search_requested` | to the view named `home` | Super. Sent instead of `shell_search` when that view is connected. The helper activates nothing and minimizes nothing. Without the view, today's route to the mod stays. |
| `search_view` | `"screen": "world"` on `open_app` and `activate_app` | from a view | Allowed from a view in 1.3. It means the home output. |
| (existing `shell_focus`) | reasons `view` and `view_closed` | to the desktop | A view took the keyboard (search, a menu) while the world had it, or gave it back. A 1.2 mod already lets go of the mouse on any `background`. |
| `settings` | request `set_setting` | desktop and views | As COMPONENTS.md 4.7 planned: the helper runs `aresos-settings set`. New names below. |
| `world_power` | request `wake_world` | views | `{"reason": "click"}`. The helper passes it to the supervisor, which decides. The answer shows as a `screens` change. |
| `outside_bar` | event `bar`; request `world_mode` | to and from the desktop | `{"outside": true}`: a bar outside is connected, so the mod hides its Live hotbar; `false` brings it back. `world_mode` says `live` or `build`. Package 10 only. |

- **Left over from earlier notes.** COMPONENTS.md 4.2 proposed "a field that says which apps have a minimized window"
  and "bring back this app's window". Those are `apps_state` and `activate_app`. `world_clicked` (4.3) is unchanged.
- **Views in 1.3** may also send `activate_app`, the window requests, `set_setting` and `wake_world`.
- **While the world sleeps** the helper sends the desktop nothing. On waking, the mod gets one fresh snapshot of
  focus, covering, `screens` and `apps_state`, never a backlog.
- **Never sent to the game or a view:** a command, arguments, an environment, a path other than `icon`. As today.

### Other interfaces

| Interface | Change |
|---|---|
| Lifecycle channel (mod and supervisor), 1.0 to 1.1 | Capability `still`: `{"op": "still", "id": n}`, answered `{"op": "still_saved", "id": n, "ok": true}`. The mod writes one frame without its interface to a fixed file, `aresos/home/still.png` in the cache folder (`$XDG_CACHE_HOME`), whole or not at all. The supervisor never takes a path from the mod. Capability `awake`: after a thaw the supervisor asks, and the mod answers once it has drawn two new frames. `save_world` gets the reason `sleep`. |
| Supervisor to helper (status socket) | Two short packets beside today's `windows` request: the launch's nonce with its keep-foreground flag, and the world's state. On `asleep` the helper minimizes the world's window; on `awake` it brings it back. |
| Helper to supervisor (status pipe) | Two more lines: the outputs with the home output, and a wake request with its reason. |
| Settings (`aresos-settings`) | Three names: `world` = `on` or `off` (default `on`); `picture` = `town`, `black` or `file` (default `town`, see question 1); `picture-file`. Setting `world` asks the supervisor. |
| `publish_home` | The wire is unchanged. |

---

## 6. The world-off switch

**What it is.** The setting `world`. Off means the home is the picture, the bar and the search. It holds until he
turns it on again, across restarts of the laptop.

**Where he flips it.** In the bar: the Home slot's menu. In the world: a row in the AresOS menu (Esc). By command:
`aresos-settings set world off`, which Claude can run for him. All three end in the same supervisor request.

**What happens to the game and Prism: both are closed.** Not frozen, not swapped.

- His goal is memory while building. A frozen game keeps its memory until something pushes it to swap. Only a closed
  game gives all of it back for certain.
- A closed game cannot be killed for memory later, so nothing can go wrong with it while he works.
- Turning off is the supervisor's planned stop (package 25): the stop record, a confirmed save, SIGTERM, the wait for
  Java's real exit and the lock. It is a stop that can be called off.
- **If the save is not confirmed, the world stays on.** The setting goes back to `on` and a line says why. This is
  today's rule for `stop`.
- After Java has exited and the lock is free, the supervisor ends Prism's scope.
  *Assumption:* Prism stays open after the game exits, as its instance settings say; the package checks it.
- Before the stop the mod writes a still, so the next start has a picture of the home as it was.

**How the picture is chosen and shown.** The setting `picture`. The native home shows it on a background surface on
every output.

| Kind | What |
|---|---|
| `town` | His town from the side, by day, as LAPTOP-HOME.md designs it. It is drawn from the home the helper keeps, so it needs no game. Houses of open apps are lit, and a click on a house opens its app. It is the default (question 1). |
| `black` | Plain `#0d0d10`, the session's own background. No surface and no picture memory. |
| `file` | A picture of his. It is converted once to a PNG of the screen's size in a sandbox of the same kind as the helper's icon converter. The native home reads only that copy. |

**How the world comes back.** He turns the switch on. The supervisor starts the game as it does today.

- With no app window open, today's start-up cover hides the loading screens.
- With an app window open there is no cover: it must never hide his apps. Until package 8 the loading screens show
  behind his windows. From package 8 the world's window stays minimized until the world is ready (section 9).
- A start takes as long as a start at boot. Board T362 measures that.

**The supervisor's states**

| State | Game and Prism | The home output shows | New |
|---|---|---|---|
| SETUP, AUTH_REQUIRED, RECOVERY | none, or waiting for him | the message window over the picture | |
| STARTING | starting | the cover; from package 8 the still | |
| IN_WORLD | running | the world | |
| ASLEEP | frozen | the still | yes (package 9) |
| WAKING | thawed, not yet drawing | the still | yes (package 9) |
| OFF | none | the chosen picture | yes (package 7) |
| STOPPING | being stopped | black, or his apps | |

- OFF is not a latch and not a failure. Nothing restarts by itself in OFF. A boot with `world` off goes straight to
  OFF: helper and native home, no Prism.
- The first start ever (SETUP, the sign-in) needs the world on. The default is on.
- The helper and the native home are started in every state.

**Memory in both states**

| State | The game | Prism | The native home | Source |
|---|---|---|---|---|
| World on, today | about 1,019 MiB (its scope's anonymous memory; soft limit 2,560 MiB) | about 418 MiB while the game runs | not running | The laptop on R28, 2026-11-21 (STATE.md, HUB-HANDOFF.md) |
| World on, this design | the same | the same | about 60 MiB, plus about 8 MiB for each further screen-sized picture | 53f's measurement of the laptop home; the sum is an estimate |
| World off | 0 | 0 | about 60 to 70 MiB | estimate from the same measurement |

- Turning the world off frees about 1.4 GiB of the laptop's 16.
- The helper and the supervisor are two small Python programs that run in both states. They were not measured.
  Package 7 measures all four on the laptop.
- The owner's own reading for the visible game is 1.2 to 1.3 GB.

---

## 7. Two screens

**Where the world goes.** To the home output. Package 23c's rule stands: any enabled screen that is not the laptop's
panel, the larger of two, the first connected on a tie; a closed lid counts as monitor only. At boot the world opens
there. Plugged in later, it moves there within seconds. Unplugged, it returns to the laptop's panel.

**One place for the rule.** The helper works out the home output, because it already binds every output and needs
the answer for covering, focus and placement. It tells the supervisor, which moves the world (23c's mechanism), and
the views. With the world off there is no window to ask, so the rule cannot hang on the world's window as it does
today.

**What each output shows**

| The world is | Home output | Other output |
|---|---|---|
| awake | the world, and the bar | the picture, and the bar |
| asleep or starting | the still, and the bar | the picture, and the bar |
| off | the picture, and the bar | the picture, and the bar |

- The picture surface exists on an output only while the awake world is not showing there. So with one screen and the
  world on, it costs no picture memory.
- This also ends "a monitor plugged in later stays black": every output has a picture from the moment it appears.

**How the cursor crosses.** The pointer is free unless he is in a look gesture (brief 328). labwc moves it between
the screens along their shared edge. Two rules for the look-around prototypes follow from this note:

- An edge shared with another screen belongs to crossing, never to turning. The mod learns the screens from `screens`.
- The bottom strip where the bar stands belongs to the bar.

Until 328 lands, the world still holds the pointer after a click on it, and he crosses with Esc first. That is
today's fault, not a new one.

**Covering, per output.** Every output has its own covered state by the T372/T373 rule. Two things read it:

- The world pauses only while the home output is covered (`shell_covered`, unchanged for the mod).
- Each output's bar hides while that output is covered (section 8).

**Where apps open, and where focus goes**

- An app opens on the screen the pointer is on (23c). A click in the laptop screen's bar opens the app there.
- The search opens on the home output, and its app opens there, as the owner chose on board #334.
- `activate_app` focuses a window where it is. It never moves a window to another screen.
- When the last window of the app in front closes, the world gets the focus only if that window was on the home
  output and the world is awake. On the other output the focus stays there. A sleeping world gets a wake request
  instead (section 9).
- A click on the world or on the picture never hides a part-screen app. The world stays below every window and the
  picture is below the world.

---

## 8. The bar, and the bar over full-screen apps

### What the bar holds

| Slot | Content |
|---|---|
| Home | First slot. A click goes home: it shows the world, or wakes it. Its menu has the world switch, the picture and the settings. |
| His nine pins | The Live hotbar's nine slots in its order, as `publish_home` gives them. An empty pin is an empty slot. |
| Other open apps | After a gap: every open app that is not pinned, in the order they opened. A slot leaves when its last window closes. |
| Status icons | The desktop's component. They sit in the bar. |

- **Marks**, from `apps_state`: open, active, and "all its windows are minimized". How a mark looks is the desktop's.
- **Hover** shows the app's name.
- **Left click:** `activate_app`. It opens the app or brings its last window back.
- **Right click:** the app's menu: its windows by title, New window (`open_app`), Close all windows. Close goes
  through the window's own close, so an app still asks about unsaved work.
- **A failed launch** shows the helper's words as a toast above the bar for five seconds.
- **The picture in a slot** is the app's picture as the mod published it. An open app outside My apps shows its
  catalogue picture. *Assumption:* the laptop home's slots already draw from the published cells; the build confirms.

### Where it shows

- **One bar on every output**, the same content on each (question 3).
- **It reserves no screen space.** A maximized window fills the whole screen and hides the bar, which the owner likes.
- **The helper says what each bar does**, in `screens`:

| `bar` | When | The bar |
|---|---|---|
| `shown` | The output is not covered. | Visible, above part-screen windows. |
| `edge` | The output is covered: a maximized or full-screen window, or a full layout. | Hidden. A thin strip at the bottom edge waits for the pointer. |
| `none` | A start-up cover or the black screen is up. Also on the home output while the awake world is in view with its own hotbar (until package 10). | Hidden, and no strip. |

### Reveal and hide

- **Reveal.** The pointer rests on the bottom edge of an output whose bar is at `edge`. After a short rest the bar
  slides up, above the app and above a true full-screen window.
- **Not revealed** while a mouse button is held (a drag to the bottom), and never while an app holds the pointer,
  because a locked pointer does not reach the edge. A full-screen game keeps its screen. Alt+Tab and Super still work
  there.
- **Hide.** Half a second after the pointer leaves the bar. At once after a click that opened or brought back an app.
  It stays while one of its menus is open.
- **Which output.** The one whose edge he touched.
- **The world stays as it is.** A reveal over a maximized app does not wake or unpause the world.
- **No keyboard.** The bar never takes it. The keyboard's way to an app is Super.
- The strip's height, the rest time and the layers are the desktop's details (section 12).

### In the look, without the game

- The bar is drawn from the look pack, as the indicator is. Look A ships in the image.
- Look B reads the game's own bar sprites from the cache that COMPONENTS.md section 5 builds from the installed
  game's files. That cache is made from the jar on disk, so it does not need the game to run.
- No game installed, or a file that fails its check: the bar is drawn in A, as a whole piece.
- Nothing of Mojang's is committed. The bar's rows in the look-B map are names and numbers only. Every public picture
  of the bar is look A.

### Search

- Super opens the search on the home output, over whatever is there. The world, a full-screen app and the picture are
  all the same to it.
- It finds as the laptop home's typing line does (LAPTOP-HOME.md 2.2). Enter opens the best hit or brings it back.
  Escape closes it and the keyboard returns to where it was.
- The app opens on the home output.
- The mod's search over the world stays as the fallback while no native home is connected. It is removed once
  package 6 has run on the laptop for a release.

---

## 9. The sleeping world

This note gives board T364 its place. It does not design swap, prefetch or the timing of sleep.

**One rule for the screen.** A sleeping world is never shown as a frozen window. A frozen X11 window under the
pointer would queue input it cannot read. So the order is:

1. The supervisor decides to sleep, from the signals below.
2. It asks for a save (`save_world`, reason `sleep`) and waits for `saved`. **No confirmed save, no sleep.**
3. It asks for a still. The native home puts the still on the home output's picture.
4. It tells the helper `asleep`. The helper minimizes the world's window. The still is now what he sees.
5. It freezes the game's scope and checks that it is frozen.
6. It demotes the game's realtime threads, picked by policy, and checks again before any thaw (package 318). On the
   laptop the game uses PipeWire and has no such thread; this is the safety net for the fallback backends.
7. Here the T364 study adds its steps: memory to swap, Prism's memory, prefetch.

**Waking** runs the other way: the admission check (section 12), the realtime check, the thaw, the mod's `awake`
after two new frames, then the helper brings the window back. The still and the first new frame show the same view,
and the bar is outside the game, so there is no jump.

**Where the signals come from**

| Signal | From |
|---|---|
| The home output is covered, or no longer | the helper (`screens`) |
| The app in front closed and the world would get the focus; Home picked in Alt+Tab | the helper |
| A click or a key on the still; the pointer coming onto it (the owner's "predicted from the pointer") | the native home (`wake_world`) |
| Idle time, the lid, battery | the supervisor |

The supervisor alone decides, because it alone freezes and thaws.

**Two depths of sleep.** Light sleep is the frozen game: a fast wake, but it keeps memory and may keep the NVIDIA
card awake. Deep sleep is the world closed with its still left on screen: it is OFF, except that a click starts the
world again. Both use parts this note already has. The study decides when each applies.

**The same path at boot (package 8).** A starting world can look like a waking one: the last still and the bar show
at once, he can open apps, and the world comes alive when it is ready. The start-up cover is then needed only when
there is no still yet.

**Numbers so far, from the rig only.** Package 318's frozen games held 421 to 510 MiB in memory with 598 to 682 MiB
in swap. These are not product numbers. The study measures the real session.

---

## 10. Migration

The in-game hotbar and the in-game search keep working until the step that replaces them has shipped.
Sizes: S is one builder step, M two or three, L four or more with a two-output test compositor.

| # | Package | He sees | Lead | Needs | Size |
|---|---|---|---|---|---|
| 1 | **The helper for the session.** Started once, nonce handed over, the home kept on disk, output names. Carries 23c's view token and the start of the native program. | Nothing. Opening no longer pauses when the game restarts. | aresos (supervisor) with hub (helper) | | M |
| 2 | **Open apps and "bring back".** `apps_state`, `activate_app`. The mod marks hotbar slots and sends `activate_app` from the hotbar, gates and `/name`. | Open and active marks on the hotbar. A left click brings Chrome back with its tab. | hub | | M |
| 3 | **The picture.** The laptop home gets one background surface per output without the world; kinds `town`, `black`, `file`; the settings. | With the monitor in, the laptop screen shows the picture. | desktop (surface), hub (town) | 1, 23c | M |
| 4 | **The bar outside.** The bar surface in look A, slots and marks, the app menu, the window requests, `screens`, the launch toast. Shown wherever the awake world is not in view. | A bar on the laptop screen beside the monitor. | desktop (surface) with hub (content) | 2, 3 | L |
| 5 | **The bar at the bottom edge.** The strip, reveal and hide on covered outputs, the home output included. | The pointer at the bottom edge brings the bar up over a full-screen app. | desktop | 4, T372/T373 | M |
| 6 | **Search outside.** The finder as an overlay; the helper routes Super to it; the two focus reasons. | Super works over any app and minimizes nothing. | hub | 3, 23c's key binding | M |
| 7 | **The world-off switch.** The setting, the supervisor's OFF, the Home slot's menu, the row in the AresOS menu, the memory check on the laptop. | The switch. | aresos with hub | 4, 6 | M |
| 8 | **Stills and the quiet start.** The lifecycle channel's `still` and `awake`; the world's window minimized until ready. | Boot shows his home at once; it comes alive when ready. | hub (mod) with aresos | 7 | M |
| 9 | **The sleeping world.** ASLEEP and WAKING on this structure. Its own study first (T364). | The world sleeps and wakes. | hub with aresos | 8 | L |
| 10 | **One bar.** The mod hides its Live hotbar while a bar outside is connected, and the keys 1 to 9 send `activate_app`. | The same bar everywhere (question 2). | hub with desktop | 4, brief 328 | S to M |

**Later, each its own package:** system notifications in the toast surface (desktop); a program's own actions in its
menu, such as a private window (hub: the helper parses no action groups today); pinning while the world is off (hub);
look B for the bar, with the desktop's look work.

**Order notes**

- Package 2 is the try-out's fixes 7 and 10 on the final protocol. It can start now.
- The switch (7) comes after the bar (4) and the search (6): without them an off world would leave him no launcher.
- Package 1 changes when the helper starts, so it touches 23c's plan. `linux-aresos` reads it first.
- Every `rc.xml` change goes to `linux-aresos` first, as always.

---

## 11. Questions for the owner

1. **What is "the default picture"?**
   On 2026-11-16 he chose the town from the side, by day, for the laptop screen, and it is built
   ([picture](../../reviews/44-laptop-home/pictures/day2-1-home.png)). On 2026-11-21 he said the laptop screen "shows a
   picture behind its apps", and that with the world off the home is "a default one, black, or any picture of his".
   *Recommendation: the town is the default picture, on the laptop screen and when the world is off.* It is his own
   home, it shows which apps are open, a click on a house opens the app, and it costs nothing more than a plain
   picture. Black and his own picture are one setting away. If he wants a plain default instead, the desktop draws
   one in look A.

2. **One bar instead of the hotbar, once the bar outside is ready and the cursor is free?**
   In Live mode the world's own hotbar would go, and the bar outside would stand in its place in the same look. The
   keys 1 to 9 would open or bring back an app instead of selecting a slot. In Build mode the game's block hotbar
   shows as today and the bar waits at the bottom edge.
   *Recommendation: yes.* It gives one bar with the same marks and the same menu everywhere, and it shows open apps
   beyond nine. He should try both for a day first; one setting flips it. If the native home ever stops, the world's
   hotbar comes back by itself.

3. **A bar on every screen, or only on one?**
   *Recommendation: every screen*, as Windows does. Each bar hides and comes up by its own screen's state.

Not asked, because the note decides it or he has already answered: where the search opens (board #334), that a
sleeping world wakes on a click, and that turning the world on never covers his apps. The desktop will show him the
bar's look in its own component pictures. The T364 study will ask how soon the world should sleep, with measured wake
times.

---

## 12. Risks, known limits, assumptions

### Real harm, and how the structure answers it

| Harm | Answer |
|---|---|
| **Lost building work when the world is turned off or put to sleep.** | Both go through a confirmed save. Without it, off is called off and sleep does not happen. The world stays as it was and a line says why. |
| **Memory is full when the world should wake** (the owner's worry). | See below. |
| **A home that cannot come back.** | A chain, each link independent of the one before: (1) the native home is restarted when it ends; (2) while no bar outside is connected, the world's own hotbar shows; (3) if the native home keeps failing while the world is off, the supervisor turns the world on; (4) `aresos-settings set world on` works from the recovery terminal; (5) if the world cannot start either, today's recovery window says why. |
| **A hung search or menu that holds the keyboard.** | The recovery key (Super+Ctrl+Escape) ends every AresOS surface that holds the keyboard before it opens the terminal. The supervisor also ends a native home that holds the keyboard and stops answering. The program keeps no state of its own, so ending it loses nothing. |
| **A dead session because a new piece fails.** | The native home is never part of readiness. Its restarts are spaced out and never end the session. The world's start does not wait for it. |
| **Input piling up in a frozen game.** | A sleeping world's window is minimized before the freeze, and the helper sends the sleeping mod nothing. |
| **The helper is needed more than before.** | With the world off it is the only launcher. Its restart must not stop for good after five failures, as it does today until the next launch. It slows down instead. While it is away the bar shows its last state and "Opening is back in a moment", as the laptop home does. |
| **Mojang's files in the repo.** | The still and look B's cache stay in his cache folder. They never go into the repo, an image, a backup or a report. Public pictures are look A. |

### When memory is full at wake time

The home must never kill his work. Four rules, in this order:

1. **The picture and the bar need nothing new.** They are already in memory. They show whatever happens to the world.
2. **A wake is admitted, not forced.** Before a thaw the supervisor checks memory pressure and free memory, with the
   test it already uses after a memory kill (pressure clear, now also enough room for what the game had in swap). If
   there is not enough, it does not thaw. The still stays, and a line says the world is waiting for memory. It wakes
   when there is room.
3. **The world is the one that goes.** The game's scope carries the worst kill preference in the session. Apps and
   the recovery terminal are never chosen because of the world. A sleeping world was saved before it slept and has
   not run since, so a kill costs no work. The next wake is then a normal start.
4. **Under lasting pressure a sleeping world may be dropped** to give its memory back. This is allowed only for a
   world whose save was confirmed at sleep. How it is dropped is the T364 study's call.

What he notices on a full laptop: his apps stay, the home stays usable, and the world comes back later.

### Known limits (low harm)

- **Until brief 328 lands,** the world holds the pointer after a click on it. The bar on the world's screen and the
  crossing to the other screen need Esc first. The in-game hotbar covers that time.
- **A full-screen app that locks the pointer** (a game) cannot reveal the bar. Alt+Tab and Super work.
- **The last pixel row** of a covered screen belongs to the strip. A click there brings the bar up instead of reaching
  the app.
- **Screens stacked one above the other:** the upper screen's bottom edge is shared, so the pointer does not stop
  there. He rests on the boundary to reveal that bar.
- **With the world off:** no gates, no `/name`, no pin changes. A program installed meanwhile joins My apps when the
  world next runs. The search finds it at once anyway.
- **A window nobody owns** has no slot in the bar. It is in Alt+Tab and in the overview.
- **Two rankers** for the search, one in the mod and one outside, kept in step by shared test cases.
- **The still can be old** after a crash, since it was made at the last sleep, off or stop.
- **Prism's 418 MiB** stay while the world is on. Whether Prism can leave after the launch is the memory study's
  question.
- **Light sleep may keep the NVIDIA card awake** on battery. Not known. If it does, the study uses deep sleep there.
- **A click on the active app's slot** does nothing more. Minimizing it on a second click, as Windows does, is a
  small later change.

### Assumptions and things to verify in a private labwc

- labwc draws an always-below window above the background layer, so the picture needs no hiding logic.
- Minimizing the world's X11 window from outside hides it without the game's help, and activating it brings it back.
  COMPONENTS.md lists the second half as open as well.
- A layer surface can take the keyboard while the game holds a pointer lock (also open in COMPONENTS.md 4.5).
- Minecraft loads normally while its window is minimized.
- The image has no notification service today.
- The laptop's swap set-up was not read; the T364 study and `linux-aresos` own it.
- The supervisor was read in its states, start, stop, helper and command parts. Its middle part was not read line
  by line.

### For `linux-desktop` to add

- The layers of the picture, the bar, the strip, the search and the toast, and the bar's layer while revealed.
- The strip's height and width, the rest time, the slide.
- The bar's look in A, B and C, its marks, where the status icons sit, and the rows of the look-B map.
- The per-output covering computation (T372/T373) that feeds `screens`.
- Scaling of pictures and the town on screens that are not 1920 × 1080.
- The static default picture, if the owner prefers one (question 1).
- Any `rc.xml` rule or key these surfaces need, sent to `linux-aresos` first.
