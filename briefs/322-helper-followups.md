# 322: 53a's three helper follow-ups

**Goal:** close the three low-harm should-fixes that 53a's second review left as follow-ups (board T358) in the
helper `os/config/usr/libexec/aresos-shell`. Nothing changes for the owner today: views connect only once package 23c
starts the laptop home. After this, a restarted helper never reports another window's focus as a view's launch, a
view paging the home never silently skips a house, and stalled view opens can't block opening an app from the world.

Read first: `AGENTS.md`, `reviews/53a-shell-views/REVIEW-2.md` (Known limits rows 2, 3 and 5; the row numbers below
are that table's), `docs/design/LAPTOP-HOME.md` section 5 (the view protocol), then the code this brief names.

## In scope

1. **Restart attribution (REVIEW-2 row 2; `adopt_windows`, about line 3183).** After a restart, `adopt_windows` gives
   every restored launch of an app all of that app's current windows ("share them"), and the focus loop (about line
   4090, `for key, handles in self.handles.items()`) then reports `focused` for every launch holding the active
   window. The review's case: two Notepad windows, one opened from the game and one from a view; after a restart,
   closing the view's window and focusing the game's window made the view's launch report `focused`.
   - An adopted launch is **ambiguous** when, at adoption, its app has more than one window, or more than one open
     launch of that app (from any client, desktop or view) is adopted.
   - An ambiguous adopted launch never reports `focused`. It reports `background` while any of its shared windows
     is open and `closed` once none is, as today. App-wide presence stays with `apps_running`.
   - An unambiguous adoption (one open launch, one window) keeps today's behaviour, focus included. A launch started
     after the restart is unaffected.
   - Discovered apps keep their own rule: all of a discovered app's windows belong to its launches
     (`match_discovered`, `follow_view_launches`). Don't change that.
2. **Home cursor (REVIEW-2 row 3; `get_home` and `page`, about lines 3449–3484).** A `get_home` cursor authenticates
   only an offset, while each page filters the home against the current catalogue. Uninstalling a first-page app
   before page two silently skipped a different, still-installed house, and both pages said revision `17`.
   - Bind each `get_home` cursor to the visible home snapshot it came from: the home's revision and the exact list
     of visible app IDs after the catalogue filter. When either changed, the next page answers `invalid_cursor`,
     so the view starts again at page one. `aresos-laptop-home` already does that (`pages()` returns `None` on
     `invalid_cursor`, and `sync()` reads again); check this still holds and don't change that program.
   - Keep the cursor's wire shape (`p<offset>-<24 hex>`, at most 64 characters), for example by putting the
     revision and a digest of the visible IDs into the HMAC input. A clearer message for this case is welcome
     (for example "the home changed while paging; get the home again without a cursor"); the code stays
     `invalid_cursor`.
   - `list_apps` cursors stay as they are: a catalogue change there bumps `revision`, which views compare per page.
   - In `docs/design/LAPTOP-HOME.md` section 5's `get_home` item, say that a cursor is valid only for the home
     snapshot it came from and that a changed snapshot answers `invalid_cursor`.
3. **Desktop check reserve (REVIEW-2 row 5; `LaunchChecks`, about line 2318, and `open_app`, about line 3626).** All
   clients share `MAX_CHECKS` (4) outstanding launch checks. Four view opens stalled on a dead mount make a healthy
   desktop open fail with `checks_busy` for as long as they stay stuck.
   - Views together may hold at most `MAX_CHECKS - 1` outstanding checks. The last slot stays free for the desktop,
     which may use any free slot. The global bound of `MAX_CHECKS` threads stays.
   - A check counts for whoever started it. Any launch of a program that already has an outstanding check still
     joins that check, as today (same program, same answer).
   - A view refused for this reason gets today's `checks_busy` launch result.

## Out of scope

- The mod, `aresos-laptop-home`, the supervisor, the image (`os/Containerfile`, units), and any other package.
- REVIEW-2's other rows: rows 1 and 4 went into 53c, and the nit (checks.py's failed assertions) belongs to 23c.
- REPORT.md's existing known limit for overlapping starts of the same app (no restart involved).
- `STATE.md` and `HANDOFF.md` (the lead updates them).

## Already decided

- **Wire compatible:** no new message, event, state, field, error code or capability. The protocol stays
  `aresos-shell/1.2`, and 1.0 and 1.1 clients see no change.
- **The bar (decision 24, `docs/design/CONTROL.md`, "The bar"):** fix these three findings. Anything new and low-harm
  you notice goes under Known limits in the REPORT, not into more scope.
- In anything committed, write "the owner", never a name, and use repo-relative paths in links.

## Acceptance

- Tests in a new `os/tests/test_aresos_shell_followups.py`, built with the helpers and fakes the existing
  `test_aresos_shell_*.py` files use:
  1. The review's restart case: two launches of one reviewed app (one desktop, one view), each with its own window,
     then a helper restart. The view's launch never reports `focused`, whichever window has the focus, and both
     launches report `closed` once both windows are gone. Also one launch and one window across a restart: focus
     is still reported as before.
  2. A 200-house home paged by a view: uninstalling a first-page app between pages answers `invalid_cursor` on the
     next page, and a fresh read from page one returns every still-installed house. A new home revision between
     pages also answers `invalid_cursor`. With nothing changed, paging returns the same pages as before.
  3. Four view opens of four programs with checks that block: the fourth view open gets `checks_busy`, a desktop
     open of a fifth program still gets a check and opens, and the desktop can fill all four slots itself. No more
     than `MAX_CHECKS` check threads at any time. Release the blocked checks at the end so no thread leaks.
- All helper and laptop-home unit tests pass:
  `python3 -m unittest discover -s os/tests -p 'test_aresos_shell*.py'` and
  `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home*.py'`. Don't run tests that call `sudo`
  (`test_inherited_homebrew`, `test_sysusers`). No client tests and no image build are needed.
- `reviews/322-helper-followups/REPORT.md`: each fix mapped to its REVIEW-2 row, what changed and why, the tests run
  with their results, and Known limits.
- Push `pkg/322-helper-followups` and open a PR into `main` (not a draft). Wait for its checks with
  `gh run watch <id> --exit-status --interval 60` (never the default interval) and fix failures this change
  caused. Never merge.

## If unsure

Take the choice that reports less: `background` rather than `focused`, `invalid_cursor` rather than a page that may
skip a house, and `checks_busy` for a view rather than for the desktop.

**Model:** Codex `gpt-6.2-sol`, `high`. Three small, well-described fixes against an existing test suite, so the
workhorse model fits and keeps to the Codex allowance the coordinator gave this package.
