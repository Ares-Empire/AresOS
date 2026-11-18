# 53c laptop home

## Done

- **Run A.** `aresos-laptop-home` opens a GTK 4 WebKitGTK 6.0 background surface on the eDP output with
  on-demand keyboard focus. Its fallback is a fullscreen `aresos.laptop-home` window that refuses to close.
  The program removes the view token and `LD_PRELOAD` before creating WebKit, retains the Mesa/Intel vendor
  pins, and serves packaged resources and validated PNG icons from a restricted, ephemeral view.
- The 1.2 view reads every page of the town and catalogue, joins display names, and atomically saves complete
  towns. It replays the initial running apps and power state to the page. A helper restart keeps the last
  complete town, disables opening while disconnected, and reenables it on a null-revision reconnect with fresh
  running IDs. A published empty town clears the saved town. The [bridge contract](../../os/config/usr/share/aresos/laptop-home/BRIDGE.md)
  describes the fields, events and geometry.
- The shell helper excludes the fallback window from covering, focus returns and unknown windows. Desktop
  launches still cancel pending returns. View launches leave them in place.
- **Run B.** The packaged HTML, CSS and JavaScript draw the four day terraces and the night street from the
  same bridge. Houses use published blocks and places, including holes. The page implements the finder, arrow
  navigation, the nine-slot hotbar, launch feedback, running lights, clock, date and battery. Street-end signs
  count hidden matches while typing. The geometry snapshot reads the current transform as houses and roofs
  slide. Day roads stay fixed.
- The paged stand-in and headless harness drive both looks of the packaged page and record the actual
  `open_app` requests. The image script adds the WebKitGTK 6.0 Python import check for R29.
- **Review 1 fixes.** Review 1 introduced a timed focus handoff, superseded in Review 3. The laptop home reads
  and writes a cache sized for 200 houses with maximum-width names and sends authenticated running IDs to the
  page while the initial catalogue read is pending. The day grid test now checks painted slabs and turf and
  compares the rendered house bounds across all four streets after a slide.
- **Review 2 fix.** The laptop home sends `view_focus` when GTK reports keyboard focus entering or leaving
  its window and immediately after each authenticated hello. The helper stores the report on the view
  connection. Losing focus, disconnecting or being replaced releases that view’s claim.

### Review 3 fix

Closing an app returns focus to the world as on `main` unless a connected view currently has the keyboard.
Both the immediate return for a registry app and the delayed return for a discovered app consult the latest
report in `return_to_desktop`. When a view holds focus, the helper clears the foreground app and handoff,
writes one debug line and leaves the keyboard with the view. Releasing focus later does not replay the close.

The diff against `origin/main` at `7d55b220` contains the `aresos.laptop-home` window exclusions,
desktop-only cancellation on `open_app`, the `view_focus` operation and its connection field, and the check in
`return_to_desktop`. Both callers, the discovered-app grace period and section 5’s separate-output rule match
main byte for byte.

<details>
<summary><code>git diff origin/main -- os/config/usr/libexec/aresos-shell</code></summary>

```diff
diff --git a/os/config/usr/libexec/aresos-shell b/os/config/usr/libexec/aresos-shell
index 55148112..d37a8744 100755
--- a/os/config/usr/libexec/aresos-shell
+++ b/os/config/usr/libexec/aresos-shell
@@ -27,7 +27,7 @@ covers the desktop's window on its screen: {"covered": true|false}. A connection
 starts uncovered on both sides; the helper sends the value whenever it changes
 and once after hello when it is true. The game pauses the world while covered.

-Minor 2 adds views, home_state and apps_running (LAPTOP-HOME.md section 5).
+Minor 2 adds views, view_focus, home_state and apps_running (LAPTOP-HOME.md section 5).
 The desktop can publish_home in parts, and views can get_home in pages. Up to
 four named views authenticate with the session instance and ARESOS_VIEW_TOKEN.
 Views can list and open apps and see their own launch states, catalogue changes,
@@ -134,10 +134,11 @@ DESKTOP_APP_IDS = frozenset({'aresos-desktop'})
 # over the game's own loading screens until world_ready. It never counts as covering the world and is never minimized:
 # labwc activates the game's window under it, and minimizing it then would show those loading screens after all.
 STARTUP_COVER_APP_ID = 'aresos.cover'
+LAPTOP_HOME_APP_ID = 'aresos.laptop-home'
 BASE_CAPABILITIES = frozenset({'list_apps', 'open_app', 'app_state', 'world_ready', 'heartbeat'})
 DETAIL_CAPABILITIES = frozenset({'app_details', 'apps_changed', 'list_paging'})
 VIEW_CAPABILITIES = frozenset({'views', 'home_state', 'apps_running'})
-VIEW_OPERATIONS = frozenset({'hello', 'list_apps', 'open_app', 'get_home'})
+VIEW_OPERATIONS = frozenset({'hello', 'list_apps', 'open_app', 'get_home', 'view_focus'})
 VIEW_EVENTS = frozenset({'app_state', 'apps_changed', 'home_changed', 'apps_running'})
 MAX_HOME_PARTS = 16
 MAX_HOME_APPS = 200
@@ -2584,6 +2585,8 @@ class Windows:
             self.closed.append(toplevel)

     def _owner(self, toplevel, seen):
+        if toplevel.app_id == LAPTOP_HOME_APP_ID:
+            return None
         if toplevel.app_id in DESKTOP_APP_IDS:
             return self.SHELL
         if toplevel.app_id in self.owners:
@@ -2622,7 +2625,8 @@ class Windows:
         return opened, closed

     def active(self):
-        return next((t for t in self.toplevels.values() if t.ready and t.activated), None)
+        return next((t for t in self.toplevels.values()
+                     if t.ready and t.activated and t.app_id != LAPTOP_HOME_APP_ID), None)

     def of(self, owner):
         return [t for t in self.toplevels.values() if t.ready and t.owner == owner]
@@ -2638,7 +2642,7 @@ class Windows:
         An output list the compositor has not sent yet counts as the same screen, as with a single screen: for the
         pause that errs toward pausing. With known_screen only windows on a screen known to be the desktop's count:
         the ones uncovering minimizes, because hiding a window that may be on the other screen is not harmless
-        (package 40, review 1, finding 4). Package 23b's start-up cover never counts.
+        (package 40, review 1, finding 4). The start-up cover and laptop home never count.
         """
         desktop = self.of(self.SHELL)
         if not desktop:
@@ -2651,7 +2655,8 @@ class Windows:
             return not screens or not toplevel.outputs or bool(toplevel.outputs & screens)

         return [t for t in self.toplevels.values()
-                if t.ready and t.owner != self.SHELL and t.app_id != STARTUP_COVER_APP_ID and not t.minimized
+                if t.ready and t.owner != self.SHELL
+                and t.app_id not in (STARTUP_COVER_APP_ID, LAPTOP_HOME_APP_ID) and not t.minimized
                 and (t.maximized or t.fullscreen) and on_its_screen(t)]


@@ -3093,6 +3098,7 @@ class Helper:
         conn.client = None
         conn.event_number = 0
         conn.running_apps = None
+        conn.focused = False
         # What this connection was last told about covering; both sides start a connection uncovered.
         conn.covered = False
         conn.capabilities = frozenset()
@@ -3165,7 +3171,8 @@ class Helper:
                 raise Failure('unknown_operation', f'unknown operation {operation!r}')
             handler = {'hello': self.hello, 'list_apps': self.list_apps, 'open_app': self.open_app,
                        'world_ready': self.world_ready, 'heartbeat': self.heartbeat,
-                       'publish_home': self.publish_home, 'get_home': self.get_home}.get(operation)
+                       'publish_home': self.publish_home, 'get_home': self.get_home,
+                       'view_focus': self.view_focus}.get(operation)
             if handler is None:
                 raise Failure('unknown_operation', f'unknown operation {operation[:64]!r}')
             if not conn.authenticated and operation != 'hello':
@@ -3360,6 +3367,15 @@ class Helper:
                     if self.home_awaits_catalogue or key in self.catalogue_apps]
         return self.page(conn, request_id, message, rows, fields, stream='home:')

+    def view_focus(self, conn, request_id, message):
+        if self.views.get(conn.client) is not conn:
+            raise Failure('invalid_state', 'only views can report view focus')
+        focused = message.get('focused')
+        if type(focused) is not bool:
+            raise Failure('malformed', 'focused must be a boolean')
+        conn.focused = focused
+        return {}
+
     def publish_home(self, conn, request_id, message):
         pending, self.publishing = self.publishing, None
         home = Home.receive(pending, message)
@@ -3552,7 +3568,8 @@ class Helper:
         self.journal.save()
         self.processes[key] = process
         # A deliberate launch says where he wants to be: an earlier close's pending return is dropped (finding 4).
-        self.cancel_returns()
+        if key[0] == DESKTOP:
+            self.cancel_returns()
         if app.discovered:
             self.discovered_scopes[unit] = dict(app_id=app_id, state=ACTIVE, started=entry['started'],
                                                launch_key=key, process=process)
@@ -4016,14 +4033,19 @@ class Helper:
                 if key not in self.view_only_apps and (self.window_minor >= 1 or not app.discovered)}

     def unowned_windows(self):
-        return [toplevel for toplevel in self.windows.toplevels.values() if toplevel.ready and toplevel.owner is None]
+        return [t for t in self.windows.toplevels.values()
+                if t.ready and t.owner is None and t.app_id != LAPTOP_HOME_APP_ID]

     def return_to_desktop(self, app):
         """The foreground app's last relevant window closed: give the hub its focus back."""
-        desktop = self.windows.of(Windows.SHELL)
-        activated = bool(desktop) and self.activate_window is not None and bool(self.activate_window(desktop[-1].handle))
         self.foreground_app = None
         self.handoff = None
+        if any(view.focused for view in self.views.values()):
+            self.returning_until = None
+            LOG.debug('keeping keyboard focus on the view after %s closed its last window', app)
+            return
+        desktop = self.windows.of(Windows.SHELL)
+        activated = bool(desktop) and self.activate_window is not None and bool(self.activate_window(desktop[-1].handle))
         self.shell = 'foreground'
         self.returning_until = self.clock() + HANDOFF if activated else None
         LOG.info('%s closed its last window; returning to the desktop', app)
```

</details>

## Verified

Each OS test module ran by name. The tests ran one engine at a time in a private home, state, runtime directory
and D-Bus session. The environment set `TMPDIR="$PWD/.work/tmp"`. The following commands are from the worktree
root.

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_shell_views.py'` | 26 tests, `OK` |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home.py'` | 9 tests, `OK` |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home_webkit.py'` | 2 tests, `OK` in the fullscreen fallback |
| `LAPTOP_HOME_TEST_LAYER_DIR=.work/layer-test/extracted/usr/lib64 LAPTOP_HOME_TEST_PSS=1 python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home_webkit.py'` | 2 tests, `OK` on the background layer |
| `LAPTOP_HOME_TEST_LAYER_DIR=.work/layer-test/extracted/usr/lib64 LAPTOP_HOME_TEST_PSS=1 LAPTOP_HOME_TEST_PICTURES=1 python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home_page.py' -v` | 3 tests, `OK` on the background layer in two runs |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home_page.py' -v` | 3 tests, `OK` in the fullscreen fallback |
| `bash -n os/ci/image-checks.sh` | Exit 0 |
| WebKit import block from `os/ci/image-checks.sh`, run locally with `env -i HOME="$PWD/.work/tmp" PATH=/usr/bin /usr/bin/python3 -` | `LAPTOP_HOME_WEBKIT 2 54 1` |
| `git diff --check origin/main...HEAD` | Exit 0 |
| Repo privacy workflow's shell check, run locally | `No file holds a home path with a real user name.` |

The bridge checks cover startup replay, the kept town and null/empty revisions, the fallback window and real
layer properties, resource policy, and seeded environment variables. Python and libc lose the token and
`LD_PRELOAD`. WebKit child environments contain the vendor pins. The program and engine process maps showed
zero NVIDIA libraries. The layer library and typelib were extracted inside `.work/` from Fedora's
`gtk4-layer-shell-1.3.0-1.fc44.x86_64.rpm`. `rpm -K` printed `digests signatures OK`.

The page checks cover click, hotbar keys and clicks, finder ranking and catalogue pictures, arrow navigation,
failure feedback, running lights and offline launches. Both looks preserve places around a removal, reveal a far
house, report the hidden counts, and expose intermediate slide geometry. The day grid checks 1, 24 and 45 houses,
verifies each side's exact plot count, and samples all four terraces' road, turf and bank pixels. At rest over
13 seconds, the page checks observed zero animation starts, canvas draws, frame callbacks or unexpected DOM
changes. Night changes one star every four seconds. The clock can tick once a minute in either look.

### Review 1 verification

The modules ran one at a time with `TMPDIR="$PWD/.work/tmp"`. The page tests used private headless labwc and the
fullscreen fallback. The helper tests cover the layer surface's lack of a foreign toplevel and the filtered fallback
window. Closing the foreground editor returned to the world. Closing the editor after either home focus transition
left the keyboard at home, and a later app activation did not renew an expired handoff.

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home_page.py' -v` | 4 tests, `OK` |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home.py'` | 11 tests, `OK` |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_shell_views.py'` | 27 tests, `OK` |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_shell.py'` | 75 tests, `OK`. Python 3.14 emitted unclosed-socket `ResourceWarning`s in the shell test module. |
| `git diff --check` | Exit 0 |

The maximum-width UTF-8 fixture round-tripped at 181,615 bytes. The 161,904-byte headless fixture kept all 200
houses on screen after a null revision. Its running house was lit on the first draw with the final catalogue page
held back. The bridge refused an open during that read and enabled opening when the last page arrived.

For the negative grid check, I removed the `.day .plots` background declaration from a temporary copy of `home.css`
and ran `LaptopHomePageTest.test_day` with that copy in headless WebKit. It exited 1 with `FAILED (failures=1)` at
the first `empty plot slab` sample. The pixel at `(1170, 309)` was turf `(138, 178, 84)` and the test expected the
slab's `(185, 199, 162)`.

### Review 2 verification

The helper tests use the real protocol and a fake clock. They cover a close two seconds after deactivation,
background closes 100 ms and 60 seconds after a focus report, blur, disconnection, same-name replacement,
and another toplevel taking over. They exercise both reviewed and discovered apps, the separate-output rule,
and the cancellation of a discovered return already in its handoff. The protocol tests check the wire examples,
invalid desktop requests and malformed focus fields.

The WebKit focus test uses labwc's virtual pointer on the private test display. A click focuses the home, a
second GTK window takes focus, and dismissing that window and clicking the home gives focus back. The test
checks the actual socket requests, including the focus snapshot after reconnect. The layer run used a verified
Fedora 44 layer-shell RPM extracted inside `.work/`.

The modules ran one at a time with `TMPDIR="$PWD/.work/tmp"`.

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_shell_views.py'` | 29 tests, `OK` |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_shell.py'` | 75 tests, `OK`, with existing unclosed-socket `ResourceWarning`s |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home.py'` | 11 tests, `OK` |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home_webkit.py' -v` | 3 tests, `OK` in the fullscreen fallback |
| `LAPTOP_HOME_TEST_LAYER_DIR=.work/layer-test/extracted/usr/lib64 python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home_webkit.py' -v` | 3 tests, `OK` on the background layer |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home_page.py' -v` | 4 tests, `OK` in the fullscreen fallback |
| `git diff --check` | Exit 0 |

An intermediate helper run reported 24 failing split-read subtests. Applying same-batch suppression only after
an explicit view focus report restored the existing results across all compositor message splits.

### Review 3 verification

Before applying the fix, the new Wayland replay test reported `FAILED (failures=45)` across 80 subtests.
These included a 1.0 and a 1.1 desktop with no view and three separate reads, and a released view with the
next activation and close in the same read. All 80 now pass. They cover every split of deactivation,
activation and close into one, two or three reads, for a registry editor on 1.0–1.2 and a discovered app on
1.1–1.2. Each case checks the activation request and the desktop’s focus events with the view absent,
released, disconnected or still focused.

Other cases close the editor immediately, 100 ms and 60 s after the home takes the keyboard, with an active
fallback window and with the editor still marked active behind a layer surface. Two connected views change
focus during a discovered app’s grace period. The tests verify one debug line for a suppressed return and
that a later focus release leaves it consumed. The earlier branch tests for a handoff after a gap and for a
return after a view loses focus now assert the policy in fix 3.

Each row ran separately with `python3 -m unittest discover -s os/tests -p '<module>'` and the flags shown.
The runs used a private temporary home, state, runtime, config and session bus under `.work/`. The two
WebKit runs used private headless labwc and verified focus reports after real keyboard transitions and reconnect.

| Module | Flags or environment | Result |
| --- | --- | --- |
| `test_aresos_shell.py` | | 75 tests, `OK` |
| `test_aresos_shell_views.py` | | 30 tests, `OK` |
| `test_aresos_shell_windows.py` | | 33 tests, `OK` |
| `test_aresos_shell_home.py` | | 13 tests, `OK` |
| `test_aresos_shell_protocol.py` | | 21 tests, `OK` |
| `test_aresos_shell_review_fixes.py` | | 31 tests, `OK` |
| `test_aresos_shell_review_fixes_2.py` | | 16 tests, `OK` |
| `test_aresos_shell_review_fixes_3.py` | | 12 tests, `OK` |
| `test_aresos_cover.py` | | 9 tests, `OK` |
| `test_window_frame.py` | | 1 test, `OK` |
| `test_aresos_desktop.py` | `-k CoverTest` | 22 tests, `OK` |
| `test_aresos_laptop_home.py` | | 11 tests, `OK` |
| `test_aresos_laptop_home_page.py` | | 4 tests, `OK` in the fullscreen fallback |
| `test_aresos_laptop_home_webkit.py` | `-v` | 3 tests, `OK` in the fullscreen fallback |
| `test_aresos_laptop_home_webkit.py` | `-v`, `LAPTOP_HOME_TEST_LAYER_DIR=.work/layer-test/extracted/usr/lib64` | 3 tests, `OK` on the layer |

I also ran the original `test_aresos_shell.py` and `test_aresos_shell_views.py` from `origin/main` against
this branch’s helper. A `git archive` supplied those two modules and main’s original 1.2 wire examples.
Using `python3 -m unittest discover -s .work/fix3/main/os/tests -p '<module>'`, they reported 74 tests,
`OK`, and 23 tests, `OK`, respectively. Python printed existing unclosed-socket `ResourceWarning` messages
in both versions of `test_aresos_shell.py`. The remaining main helper focus and window modules listed above
are byte-identical to the ones on this branch.

`git diff --check` exited 0. `find .work -type f -size +500000000c -print` produced no paths.

### Pinned memory at rest

These are summed PSS from `/proc/<pid>/smaps_rollup` for the GTK program and WebKit's web and network processes.
The second packaged-page pass measured after the 13-second idle check, with 44 houses in the 45-place town and
47 catalogue entries. The earlier pass measured 319 MiB by day and 314 MiB by night on the same setup.

| View | GTK program (KiB) | Network (KiB) | Web (KiB) | Total (MiB) |
| --- | ---: | ---: | ---: | ---: |
| Run A bridge fixture, repeated in Run B | 155,859 | 22,817 | 72,413 | 245 |
| Packaged day page | 187,708 | 22,068 | 124,365 | 326 |
| Packaged night page | 187,698 | 22,416 | 118,374 | 321 |

Run A originally measured 244 MiB after eight idle seconds with 43 houses and 44 catalogue entries.
Both runs used headless labwc 0.9.6 with pixman, GTK with Cairo, WebKitGTK 2.54.1, `LIBGL_ALWAYS_SOFTWARE=1`,
`WEBKIT_DISABLE_DMABUF_RENDERER=1`, and the Mesa EGL/Intel Vulkan vendor files named in the design.
The finished page ran at 1920 × 1080 with the layer-shell library loaded. The totals exceed the design's
150–180 MiB estimate and exclude the compositor and GPU allocations. These are memory samples. The motion
checks counted browser activity and did not measure CPU load.

### Pictures

I inspected all ten 1920 × 1080 WebKit snapshots from the headless compositor. The day page keeps the
study's shared grid, horizon at the top tread, equal full-width roads, turf, banks and spacing.
The generated logos and counts come from the test town. The page uses the live clock and the stand-in's
68% charging battery, and the opened pictures show the running door, sign and hotbar mark with the whole town
visible. The typing pictures use `tool19` to show the frame after a slide. The helper-away pictures show the
retained town and running light with the offline message. The day end fade is narrower so the framed house
stays clear. The night captures keep the stars, short roads, gaps between houses and glowing open doors.
The capture home had the study's fonts, including a Space Grotesk file identical to the image's.

| State | Day | Night |
| --- | --- | --- |
| Home | [Day](pictures/day-home.png) | [Night](pictures/night-home.png) |
| Forty-five houses | [Day](pictures/day-forty-five.png) | [Night](pictures/night-forty-five.png) |
| Typing | [Day](pictures/day-typing.png) | [Night](pictures/night-typing.png) |
| Running app lit | [Day](pictures/day-opened.png) | [Night](pictures/night-opened.png) |
| Helper away | [Day](pictures/day-helper-away.png) | [Night](pictures/night-helper-away.png) |

The comparison used the study’s [day home](../44-laptop-home/pictures/day2-1-home.png),
[day grid with 45 houses](../44-laptop-home/pictures/day2-8-forty-five-apps.png),
[day finder](../44-laptop-home/pictures/day2-2-finding.png),
[day opened](../44-laptop-home/pictures/day2-4-opened.png) and
[night far house](../44-laptop-home/pictures/street-9-far-house.png).

No files over 500 MB remained in `.work/`.

## Not verified

- The laptop trial with the game and external monitor still needs to check which chips GTK and labwc draw on,
  a click from the world and keyboard focus, Alt+Tab, a maximized app over the home, plugging and unplugging,
  a game restart, and memory and motion cost in the real session.
- The WebKit import block ran on the local machine. The image-level check is pending R29.
- The checks-only workflow was dispatched for `74ec9b3f`. The lead will collect the result.
  [OS image run 44362345145](https://github.com/Ares-Empire/AresOS/actions/runs/44362345145)
- The Review 1 fixes dispatched checks-only at `4098b4a5`. The result is for the lead to collect.
  [OS image run 44365447042](https://github.com/Ares-Empire/AresOS/actions/runs/44365447042)
- The Review 2 fixes dispatched checks-only at `3efe522d`. The result is for the lead to collect.
  [OS image run 44368010857](https://github.com/Ares-Empire/AresOS/actions/runs/44368010857)

## Known limits

- Mapping the fullscreen fallback can take focus from the world during an unattended start. Package 23c's restart rule must account for this.
- A launch that fails after the helper reports `starting` leaves the page without a reason for the failure.

## JUDGMENT-CALL

- The packaged page selects day in its entry point and keeps night in the same modules. A theme picker would add
  a visible control before the laptop trial. A later preference can select the existing look with one startup setting.
- When a cut end hides houses but none match, the sign shows zero and still lets the owner pan. Hiding the sign
  would remove that route through the street during search. Changing this later is limited to the end-sign rendering.
- The first draw waits for the bridge replay and gives the initial lookup up to 500 ms after the resource filter is
  ready. A longer wait would also hold back the kept town when the helper is away. Changing the wait costs one
  startup policy change.

## PLAN-GAP

- The study's 150–180 MiB estimate needs a real-session measurement. The pinned, software-rendered totals above
  are the current headless measurements.
- Package 23c provides the supervisor's token, environment, start/stop and screen moves. R29 provides layer-shell,
  JetBrains Mono and their image checks. The page resolves system fonts by name and has a monospace fallback.

## Open questions

- Does real-session PSS leave enough room alongside Minecraft during the dual-monitor trial?
