# 53a: the helper speaks `aresos-shell/1.2` (views, the home, running apps)

Board #335, brief 306, step 1 of `docs/design/LAPTOP-HOME.md` section 9. OS helper package. The lead's handoff for
the whole build is `briefs/53-laptop-home-build.md` (it rides this PR).

**Builder:** Codex `gpt-6.2-sol` `xhigh`: data and rules against a tight design, which Sol builds well. The handoff
named `gpt-6.1-sol`; 6.2 is the current generation of the same workhorse (models list, 2026-11-18).
**Review:** a fresh Codex `gpt-6.2-astra` `high`, read-only, with one focused security pass on the view token.

## Why

The laptop home (a window program on the laptop's own screen while the world runs on the monitor) needs to read the
owner's town and open apps through the same helper the game uses, without ever being able to act as the game. This
step gives the helper that second kind of client, a **view**, and the three things a view needs: the town the mod
publishes (`publish_home` / `get_home` / `home_changed`) and which apps have windows (`apps_running`). Nothing on the
screen changes yet; the mod's side is 53b, the window program 53c, the supervisor's side package 23c.

## Read first

`docs/design/LAPTOP-HOME.md` section 5 (the whole interface, this package's contract), section 6 ("Living in the
session") and section 9 step 1. `docs/design/HUB.md` 3.8 (what 1.1 is). Then `os/config/usr/libexec/aresos-shell`
(hello, capabilities, `PRIVATE_ENVIRONMENT`, the journal and `JOURNAL_LIMIT`, `Windows.covering`,
`return_to_desktop`, `emit`) and its tests `os/tests/test_aresos_shell_*.py`, and the 1.1 example messages under
`mod/src/test/resources/shell-1.1/`.

## Build

### A. Views (section 5, "A view")

1. **1.2 and its capabilities.** The helper answers `aresos-shell/1.2` and offers `views`, `home_state` and
   `apps_running` to a client that asks for minor 2. A 1.0 or 1.1 client sees exactly what it sees today.
2. **Who a hello is.** The helper reads the view token from `ARESOS_VIEW_TOKEN` at start and adds that name to its
   `PRIVATE_ENVIRONMENT`, so no app it launches inherits it.
   - A hello holding the nonce is the desktop; a hello holding `instance` and the view token is a view. The role
     comes from what the hello holds. A `role` that does not match it, a hello holding both, or a view without a
     valid `view` name (`[a-z0-9-]{1,32}`) is refused with `not_authorized` (bad name: `malformed`).
   - Compare tokens and nonces with `hmac.compare_digest`. Never log a token or put it in a reply.
   - With no `ARESOS_VIEW_TOKEN` (or an empty one) every view hello is refused. Until package 23c the supervisor
     sets none, so on a real session nothing changes.
3. **A view never touches the desktop's state.** Its hello does not close the desktop's connection (nor a desktop's
   hello a view's), does not set `window_minor`, does not call `cancel_returns()`, does not set `windows_pending`,
   writes nothing to the status pipe, and never counts for readiness. A second view with the same name closes the
   first; a fifth distinct view is refused (`busy` or the closest existing code; say which).
4. **What a view may send:** `hello`, `list_apps`, `open_app`, `get_home`. Every other op is `invalid_state`, in
   particular `world_ready`, `heartbeat` and `publish_home`.
5. **What a view gets:** `apps_changed`, `home_changed`, `apps_running`, and `app_state` for its own launches. Never
   `shell_focus`, `shell_covered`, or any later desktop-only event.
6. **Launches per client.** Journal entries are keyed by client (`desktop` or `view:<name>`) and request ID; the
   duplicate rule holds within one client only. The desktop keeps its `JOURNAL_LIMIT` (256); each view has 32 of its
   own, so a view can never make the world's opens fail with `journal_full`. Each entry remembers who asked and
   survives a helper restart as entries do today; `app_state` goes to that client only, or to a view that comes back
   with the same name. An entry from a journal written before this package counts as the desktop's.

### B. The home (section 5, `publish_home`, `get_home`, `home_changed`)

1. **`publish_home`** from the desktop (minor 2): validate shapes and bounds only, as section 5 gives them
   (`revision` a 1.1-style string, `part` from 0 counting up by one, `last`, `palette` of single-character keys to
   `#rrggbb`, at most 200 apps across all parts, `cells` exactly 144 characters of `.` or a palette key, `slot`
   0–8 or missing, `place` and `short` and `group` strings as in 1.1). Bound the parts too: at most 16 per
   revision, and a part of another revision, a gap or a repeat drops the half-built home and keeps the last complete
   one. The home is taken over only when the part with `"last": true` arrives. Keep it in memory only.
2. **Unknown apps.** An app whose ID the helper does not list is left out, logged once per publish, and the rest of
   the town stands. Apply this when serving `get_home` too, against the current list, so an uninstall after a
   publish never shows a dead house and never empties the town.
3. **`get_home`** from a view, paged like `list_apps` (cursor, `next`, the same page size rules). Before any
   complete publish: `"revision": null` and no apps.
4. **`home_changed`** to every view when a new complete home arrives.

### C. Running apps (section 5, `apps_running`)

`apps_running` to each view once after its hello and then at each change: the sorted IDs of the apps that have at
least one window, from the helper's window tracking. Coalesce bursts (one event per loop turn is enough). Without
window tracking, send an empty list once and nothing after.

### D. The focus return, decided by screen (REVIEW-2 should-fix 1 of package 44; this replaces section 5's "a
launch a view asked for is not the desktop's")

When an app's last window closes on a screen that is **known** not to be the world's (its outputs are known and
none is one of the desktop window's outputs, as `Windows.covering(known_screen=True)` decides), the helper does not
return to the world: no activation and no `shell_focus`. Whoever opened the app does not matter, and an app moved
between screens follows where its window was. With unknown outputs or one screen, today's behaviour stays. Update
section 5's sentence in `LAPTOP-HOME.md` to this rule and add a line for `linux-aresos` beside the PLAN-GAP there,
since it touches 23c's screens.

### E. The example messages

Commit them under `mod/src/test/resources/shell-1.2/` beside 1.1's: a view's hello and its refusals, `publish_home`
(one part, and a town in two parts), `get_home` before and after a publish and over two pages, `home_changed`,
`apps_running`. The mod's step (53b) tests against the same files, so they are the contract. Add new files only;
change nothing else under `mod/`.

## Acceptance

- A new test module `os/tests/test_aresos_shell_views.py` (more modules if it grows), covering section 9's list:
  - a view never displaces the desktop and never counts for readiness;
  - a hello with the view token is a view whatever its `role` says, and a mismatch is refused; both secrets in one
    hello, a wrong token, no token configured, and the nonce in a view's hello are refused;
  - a view's hello leaves the window rules, the returns and the status pipe alone;
  - a busy view cannot fill the desktop's journal (33 view launches, then the desktop still opens);
  - a view's request ID never returns a launch of the game's (same ID from both);
  - `app_state` reaches only the client that asked, also after a helper restart and a view's reconnect;
  - an unknown ID in `publish_home` drops that app only; an uninstall after a publish drops it from `get_home`;
  - parts: two-part town, a gap, a repeat, a new revision mid-way, 17 parts, 201 apps, bad cells and palette;
  - a fifth view, a second view with the same name, a view sending `world_ready`, `heartbeat`, `publish_home`;
  - views never receive `shell_focus` or `shell_covered`; `apps_running` after hello and on change;
  - D: an app closing on the other screen sends no `shell_focus` and activates nothing; on the world's screen and
    with unknown outputs it returns as today;
  - an app launched by the helper does not see `ARESOS_VIEW_TOKEN` in its environment;
  - each example file under `shell-1.2/` is read and checked by the tests.
- Run only the modules you touch, one at a time (`python3 -m unittest discover -s os/tests -p
  'test_aresos_shell_views.py'`, then each existing `test_aresos_shell*.py` module by name). Never the whole
  `os/tests`, never `test_owner_update` (AGENTS.md). For the full count, one hosted run: `gh workflow run "OS image"
  --ref pkg/53a-shell-views -f checks_only=true`, then `gh run watch <id> --exit-status --interval 60`.
- The helper's docstring describes 1.2. `LAPTOP-HOME.md` section 5 matches what was built (D, and any PLAN-GAP).
- `reviews/53a-shell-views/REPORT.md` in the AGENTS.md format, with the limits you picked and every error code a
  view can get.

## Out of scope

The supervisor (`aresos-desktop`: making and handing over the token, starting the laptop home; package 23c,
`linux-aresos`). The mod (53b). The window program (53c). Super and `shell_search` (53d). The image. Nothing under
`mod/` except the new example files. No game tests and no Gradle: this step needs neither.
