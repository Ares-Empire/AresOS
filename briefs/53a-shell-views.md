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
   `PRIVATE_ENVIRONMENT`. **No child the helper starts inherits `PRIVATE_ENVIRONMENT`**: not the apps it launches,
   and not its own tools either (today `query_scopes()` runs `systemctl` with the helper's full environment, nonce
   included; give it the filtered environment too).
   - Both roles must carry the matching `instance`, as the desktop's hello does today. A hello with `instance` and
     the nonce (field `nonce`), and `role` missing or `"desktop"`, is the desktop. A hello with `instance`, the view
     token (field `token`) and `"role": "view"` is a view. Everything else is refused with `not_authorized`: a wrong
     instance with either secret, a role that does not match the secret, both secrets in one hello, a token without
     `"role": "view"`. A view without a valid `view` name (`[a-z0-9-]{1,32}`) is `malformed`. The nonce keeps its
     current accepted range (`NONCE`).
   - Compare tokens and nonces with `hmac.compare_digest`. Never log a token or put it in a reply.
   - With no `ARESOS_VIEW_TOKEN` (or an empty one) every view hello is refused. Until package 23c the supervisor
     sets none, so on a real session nothing changes.
   - **The token's contract** (the lead's call; `linux-aresos` builds 23c's side from it, so write it into
     `LAPTOP-HOME.md` section 5 word for word as built):
     - **Format:** `secrets.token_urlsafe(32)`, 43 characters of `[A-Za-z0-9_-]` (256 bits). The helper accepts
       exactly that shape; it differs from the nonce's 32 characters, so a mix-up shows.
     - **Made:** once per session, by the session's first supervisor, at the moment it makes `instance` (its runtime
       file does not exist yet). A restarted supervisor reads it back. Never new for a game start, a retry or a
       helper restart.
     - **A restarted supervisor without a valid token** (missing, malformed, or the file of another instance) makes a
       new one with that instance and restarts the helper and the laptop home, so no process keeps an old token. The
       game is never restarted for this: it keeps its launch and nonce.
     - **Kept:** as `view_token` in the supervisor's runtime file under `$XDG_RUNTIME_DIR` (written atomically, mode
       0600), never in a file under `HOME`, so it ends with the session.
     - **Given:** as `ARESOS_VIEW_TOKEN` to every helper the supervisor starts and to the laptop home, never to the
       game; both the supervisor and the helper list it in `PRIVATE_ENVIRONMENT`.
     - **In the helper:** read once at start, and compared with `hmac.compare_digest`, never `==`. A malformed value
       counts as none and is logged once, without the value. A wrong token and no token configured both get `not_authorized` with the same text and close the
       connection, so a client cannot tell them apart; only the helper's log says which, never with a value.
3. **A view never touches the desktop's state.** Its hello does not close the desktop's connection (nor a desktop's
   hello a view's), does not set `window_minor`, does not call `cancel_returns()`, does not set `windows_pending`,
   writes nothing to the status pipe, and never counts for readiness. A second view with the same name closes the
   first; a fifth distinct view is refused (`busy` or the closest existing code; say which).
4. **What a view may send:** `hello`, `list_apps`, `open_app`, `get_home`. Every other op is `invalid_state`, in
   particular `world_ready`, `heartbeat` and `publish_home`.
5. **What a view gets:** `apps_changed`, `home_changed`, `apps_running`, and `app_state` for its own launches. Never
   `shell_focus`, `shell_covered`, or any later desktop-only event.
6. **Launches per client.** Every piece of state a request ID keys is keyed by client (`desktop` or
   `view:<name>`) and request ID: the pending checks `open_app` looks up before the journal, the journal, process and
   window tracking, and restart reconciliation. The original ID stays on the wire. The duplicate rule holds within
   one client only. A launch a view asked for never changes the desktop's window rules (`window_minor`), also when
   it is reconciled after a helper restart. The journal keeps entries for at most four view names; when a fifth
   name appears, the entries of the view name used longest ago go. The desktop keeps its `JOURNAL_LIMIT` (256); each view has 32 of its
   own, so a view can never make the world's opens fail with `journal_full`. Each entry remembers who asked and
   survives a helper restart as entries do today; `app_state` goes to that client only, or to a view that comes back
   with the same name. An entry from a journal written before this package counts as the desktop's.

### B. The home (section 5, `publish_home`, `get_home`, `home_changed`)

1. **`publish_home`** from the desktop (minor 2): validate shapes and bounds only. These bounds are the contract
   for the mod (53b) and the window program (53c) too; write them into section 5:
   - `revision`: as 1.1's revision strings. `part`: an integer from 0, counting up by one, at most 16 parts per
     revision. `last`: a boolean.
   - `palette`: **only in part 0**, required there, absent from later parts. At most 64 keys, each one character
     of `[A-Za-z0-9]`, each value `#rrggbb`.
   - `apps`: at most 200 across all parts; IDs as 1.1's app IDs, unique across the whole revision.
     - `short`: required, 1–64 characters, no control characters.
     - `group`: required, `[a-z0-9_]{1,64}`.
     - `place`: optional (missing while the app has none), `[A-Za-z0-9_-]{1,32}`.
     - `slot`: optional, an integer 0–8.
     - `cells`: required, exactly 144 characters, each `.` or a key of the revision's palette.
   - A part of another revision, a gap, a repeat, a palette outside part 0, a duplicate ID or a cell without a
     palette key drops the half-built home and keeps the last complete one. The home is taken over only when the
     part with `"last": true` arrives. Keep it in memory only.
2. **Unknown apps.** An app whose ID the helper does not list is left out, logged once per publish, and the rest of
   the town stands. Apply this when serving `get_home` too, against the current list, so an uninstall after a
   publish never shows a dead house. Filter only against a **complete** catalogue: while the first discovery scan
   has not finished (the starter-only list), serve the home as published, so a slow scan never empties the town.
3. **`get_home`** from a view, paged like `list_apps` (cursor, `next`, the same page size rules). Every page carries
   `revision` and the whole `palette`, so each page decodes alone. Before any complete publish: `"revision": null`
   and no apps.
4. **`home_changed`** to every view when a new complete home arrives.

### C. Running apps (section 5, `apps_running`)

`apps_running` to each view once after its hello and then at each change: the sorted IDs of the apps that have at
least one window, from the helper's window tracking, identified against the **whole catalogue** (discovered apps
included), whatever desktop is connected, if any (none, 1.0, 1.1 or 1.2). This must not change what the desktop's
window rules see or own. Coalesce bursts (one event per loop turn is enough). Without window tracking, send an empty
list once and nothing after.

### D. The focus return, decided by screen (REVIEW-2 should-fix 1 of package 44; this replaces section 5's "a
launch a view asked for is not the desktop's")

**Only while at least one view is connected** (the laptop home runs; without it the other screen holds nothing
and today's return is right): when an app's last window closes on a screen that is **known** not to be the
world's, the helper does not return to the world, so no activation and no `shell_focus` with `reason: app_closed`.
"Known": the closing window's last recorded outputs are known and none is one of the desktop window's outputs
(compare them directly, as `Windows.covering` does for its screens; record them before the window is forgotten, and
carry the decision through the discovered-app delay). Whoever opened the app does not matter, and an app moved
between screens follows where its window was. With unknown outputs, one screen or no view, today's behaviour stays.
Only the helper's own return is suppressed: a real activation of the world by the compositor still reaches the game
as today. Update
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
    hello, a wrong token, no token configured, a token without `"role": "view"`, a wrong instance with each
    otherwise-correct secret, and the nonce in a view's hello are refused;
  - a view's hello leaves the window rules, the returns and the status pipe alone;
  - a busy view cannot fill the desktop's journal (33 view launches, then the desktop still opens);
  - a view's request ID never returns a launch of the game's (same ID from both), also while the first launch's
    check is still pending; a view's launch reconciled after a restart leaves `window_minor` alone; a fifth view
    name's launches push out the oldest name's journal entries;
  - `app_state` reaches only the client that asked, also after a helper restart and a view's reconnect;
  - an unknown ID in `publish_home` drops that app only; an uninstall after a publish drops it from `get_home`;
  - parts: two-part town, a gap, a repeat, a new revision mid-way, 17 parts, 201 apps, bad cells and palette, a
    palette outside part 0, a duplicate ID; every `get_home` page carries the palette; a home served before the
    first discovery scan finishes keeps its discovered houses;
  - a fifth view, a second view with the same name, a view sending `world_ready`, `heartbeat`, `publish_home`;
  - views never receive `shell_focus` or `shell_covered`; `apps_running` after hello and on change, and it lists a
    discovered app's window with the view connected first, with a 1.0 desktop and after a helper restart;
  - D: with a view connected, an app closing on the other screen sends no `shell_focus` and activates nothing; on
    the world's screen, with unknown outputs, and with no view connected it returns as today; a compositor
    activation of the world still reaches the game;
  - neither an app launched by the helper nor the `systemctl` of `query_scopes()` sees `ARESOS_VIEW_TOKEN` or the
    nonce in its environment;
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
