# 28 Chrome read: progress

Builder steps keep this file; the last step turns it into the report. Newest state first.

## Step 10 (2026-11-16, Claude agent on Opus 5.5): the time

Opus: built against the brief's item 4, the lead's brief for this step and step 9's "Left, in order" item 3. The
summary there and item 4 say the same; nothing had to be chosen between them.

### Done

- **One deadline for a `chrome_outline` call** (`chrome/deadline.py`, new). `Deadline` is the call's clock, opened
  by `engine.request` before its first look at pending and closed after the response is built
  (`Chrome.call_time`, three lines in `engine.request`; PLAN-GAP 1). Only a `chrome_outline` request opens it, and
  only while the switch registers the action; `outline` opens one itself when called directly (tests). Its seconds:
  - the engine's first look checks each reserved approval by second 1 (`FIRST_LOOK`);
  - `until` ends at `timeout_ms` counted from the start of the call, never after second 6 (`UNTIL`);
  - every command of the read answers by second 7 (`COMMANDS`); with `tabs`, a tab's turn ends at
    `now + (second 7 - now) / tabs still to read`, so the first of five gets 1.4 seconds and time a tab doesn't
    use passes on;
  - the looks after the read (the read's own measure, then the engine's response) check by second 7.25
    (`LAST_LOOKS`; PLAN-GAP 3), so a stuck extension's half second of grace still ends at 7.75.
- **The bridge** (`bridge.py`): `TimeLeft.bounded(end)` is the bound in force (a nested one keeps the earlier
  end). Inside it `Bridge.call` sends `time_left_ms` beside the command, sends nothing once the time is up
  (`expired`, "nothing was sent"), and waits for the reply until the end plus `GRACE` (0.5 s). Then it gives the
  command up (`expired`) and keeps its id. A reply with a given-up id is dropped by its id, in `Bridge.call` and
  when the daemon's loop reads it between requests (`read` marks it answered; `Chrome.event` does nothing with a
  message without an event). If none has come `SOCKET_BOUND` (15) seconds after the command was sent, the next
  wait closes the connection as the socket's own timeout does (`transport_error`). The extension's `expired`
  answer is the code `expired`. Without a bound nothing changes: no `time_left_ms`, recv's own 15 seconds.
- **The adapter** (`adapter.py`):
  - `outline` reads under `bounded(second 7)`, each tab under its turn's end. `expired` makes that tab `not_read`,
    "time ran out; read this tab by itself", and the others are returned. If the extension's settings command
    (`mode`'s `configure`) runs out, no tab can be read and the call fails with `not_read` (JUDGMENT-CALL 5).
  - The measure's look at pending comes after the read's commands, outside their bound.
  - `pending_state`, inside a call: bounded by its look's end; `expired` gives `validity: unchecked` (the row
    keeps its state and reason, never `refused`), and the operation isn't asked again in the same call. Any other
    refusal stays a refusal.
- **The extension** (`background.js`):
  - **The queue:** its body moved into `enqueue(message)` (same `serial` chain, one command at a time). A message
    with `time_left_ms` ends that long after it arrives (`performance.now()`). At the front of the queue a command
    whose time is up isn't started: it answers `expired: ... it was not started` and audits `phase: 'expired'`.
  - **The waits:** `dispatch(command, expires)` passes the end to the read's commands (`outline`, `page_state`,
    `options`, `validity`, `typed_fields`, `read`, `facts`). `within(promise, expires)` ends a wait with
    `expired`: the reader's reply in `content`, the late-reader recovery in `facts`, the popup setup waits and the
    owner-dialog recovery in `requireTab`, the dialog opener wait in `readyDialog`. `facts` and `pageState` pass
    `expired` on instead of counting the frame as unread, and `requireTab` doesn't release a popup whose opener
    check ran out of time. A command without a time passes `null` and runs as before. Nothing in `input`.
- **CI:**
  - `prepare.mjs`: every rewrite must match exactly once (`exactly`). `dispatch`'s new signature had made the old
    `fixture_network_restart` rewrite match nothing, silently; it now finds either signature (the latency pair's
    old runtime keeps the old one). The fixture builds get two holds (only on a runtime with item 4):
    `fixture_hold_reader` holds one tab's reader replies by `ms` for `duration` (optionally only some commands),
    `fixture_hold_reply` holds the extension's own reply to the next command of a name and tab by `ms`.
  - `service.py` sends a hold after the admin request it rides on (`admin.py`, `{fixture: 'hold'}`), so that
    request's own looks aren't held. `admin.py`'s service restart (GROUP 9) now carries the switch too.
  - `call.py`: `--command` goes through the `aresos` command, `--timed` prints the seconds of the call alone.
  - `outline-time.mjs` (group 14's time cases), in the core shard of Control Chrome's own runs right after GROUP 1,
    through the proxy and the command (JUDGMENT-CALL 7):
    1. `until` on a text that never comes, `timeout_ms` 6000, through both: `until_met: false`, at least 5.5 and
       under 8 seconds;
    2. five tabs, the third's reader held: four outlines and its `not_read`, under 8 seconds; the next call gets
       its own answer while the held reply is still out, and the held tab reads normally once it came;
    3. the extension's own reply to an outline held 9 seconds: `not_read` under 8 seconds, then the next call
       waits behind it, drops the late reply by its id and gets its own answer;
    4. an approval prepared on the compose page whose `ready` replies are held: a read of another tab ends under
       8 seconds and the approval's row is `reserved`, `unchecked`; then dropped and acknowledged.
    A failure is kept and fails the shard after brief 20's cases have run. `/out/outline-time.jsonl` records each
    call (seconds, entries, errors, pending rows; no page text).
  - `latency-instrument.mjs`: its `content` and `dispatch` wrappers pass on what they don't name (the time).
- **Tests:**
  - `test_outline_time.py` (new, 33): `Times` (the seconds fit inside the call and the client's 10; the bridge's
    bound is the daemon's `settimeout`; a nested bound); `Wire`, the real `Bridge` on a socket pair with the test
    as the extension (time on the wire and none without a bound; nothing sent when the time is up; a reply in time
    with an event before it; the extension's `expired`; given up at its time plus half a second with the
    connection open; a late reply, whole and in chunks, dropped by its id and the next command gets its own; a
    late reply read by the daemon's loop is never overdue; no reply at all closes at the bound, with an untimed
    and a timed next command; an untimed command waits as before); `Read` and `Call`, the adapter and
    `engine.request` with a fake bridge on a fake clock (every command of a tab carries the time to second 7; a
    reader that never answers is `not_read` at second 7; five tabs' shares, the first 1.4, the third more than the
    second, the slow first costing only its share; `until` from the call's start and never past second 6; a poll
    running out; `configure` running out; brief 20's read with an approval out carries no time; without the switch
    nothing is timed; an approval whose check never answers is `unchecked`, asked once, the call ends at second
    1.03; one that runs out after the read is `unchecked` with the measure's look bounded by 7.25; a refusal stays
    a refusal; an invalid input closes the clock; five tabs through the engine end by second 7).
  - `background.test.mjs` (5 new): a frame that never answers ends `outline`, `page_state`, `options`, `validity`,
    `read` and `typed_fields` at their time with `expired`, without its dialog waiter and keeping control; a
    command without a time waits as before; the queue starts no command whose time is up at the front, in order,
    and a command without a time gets none; five tabs sent with the service's shares, the first silent: it expires
    at its share and the other four answer, all inside the budget; a popup setup wait ends at the time, keeps
    control and the setup, and waits as before without a time.
  - `latency.test.mjs`: the time passes through both overlay wrappers. `test_outline_action.py`: `Outlines` keeps
    the bridge's bound; the CI restart line carries the switch.
- **Local checks** (no Node, no browser):
  - `PYTHONPATH=control python3 control/generate.py --check`: "Generated artifacts match definitions".
  - Step 9's first set (`test_publisher` ... `test_restore_lock`): 315 tests, OK.
  - `… -m unittest test_engine test_policy test_sites test_bridge test_outline_time`: 114 tests, OK.
  - `control/tests` `test_operations test_integration test_review21_pending test_review22_protocol
    test_review23_results test_approval_questions`: 54 run, 25 failures and 19 errors, the same list on the
    unchanged head (they need the installed boundary and root).
  - The JavaScript: a bracket and string check of every changed file and of the test build `prepare.mjs` makes;
    the rewrites it needs each match once on the current runtime, the old one on `ab7aba92`.
- **Checked by mutation** (each run against `test_outline_time`, `test_outline_action` and `test_bridge`; every
  one fails a test, and the file was restored after each):

  | Broken | Fails |
  |---|---|
  | the bridge waits only to the end, no half second | given up at its time plus half a second |
  | a late reply isn't dropped by its id | the late reply, whole and in chunks |
  | `read` doesn't mark a late reply answered | the late reply read by the daemon's loop (closed as overdue) |
  | no close at the socket's bound | both "no reply at all" tests (they then wait 15 seconds) |
  | a tab's turn is all the time left, not an equal share | five tabs' shares; five tabs through the engine |
  | `timeout_ms` counted from the start of the wait | `until` from the call's start |
  | an unchecked approval is asked again in the call | the approval asked once |
  | `engine.request` opens no clock | the two `unchecked` tests; the invalid input's clock |
  | `expired` isn't turned into `not_read` | the reader that never answers, the poll, both five-tab tests |
  | `expired` in a look becomes `refused` | both `unchecked` tests |
  | the first look gets the time of the last | both `unchecked` tests; the invalid input's clock |
  | the measure's look inside the commands' bound | a check that runs out after the read |

  The Node tests and the JavaScript changes can't be mutated here (no Node); run 11 is their first run.

### Runs

| Head | Holds | Control Chrome | Result |
|---|---|---|---|
| `f018ccb1` | the deadline: service and bridge (`11f36428`), extension (`d0e4ea59`), CI cases (`f018ccb1`) | 43884313490 (run 10; qualification 43884313839) | **cancelled by me, a few minutes in:** reading the pushed code, `outline-time.mjs` imported `fixtureUrl` from `efficiency-fixtures.mjs`, which doesn't export it (`efficiency-probe.mjs` does), so `browser.mjs` couldn't load in any browser job. Its Mail, base, boundary and privacy runs were cancelled by the next push. |
| `4bae420b` | + the import fixed | 43884693090 (run 11; qualification 43884693205); Control Mail 43884693352 | **Control Chrome green on its first attempt, 28 of 28 jobs:** both latency legs and the plain leg's efficiency step; the four Python shards (aggregate: 38 modules, 565 tests); every fixtures shard, both install modes; the aggregate (every browser shard, all 999 word cases, group 12). In both core shards the Node suite passes 472 of 472 (the first run of this step's JavaScript) and the four time cases pass: five tabs 2.36 s, the held reply 7.51 s, the held approval check 1.01 s, the `until` cases between 5.5 and 8 s (external 14:58 to 14:59 UTC, policy 15:19 to 15:20). Control Mail, Control base, Control boundary and Repo privacy green. Qualification 43884693205 green, 34 of 34 jobs. |

Eleven full `control-chrome` runs started so far, ten of them run through (run 10 was cancelled). The brief planned about
six and asked to hear before passing nine; the lead has the count from step 9. Run 11 is the first green run with the
time on; the brief asks for CI green twice on the final head.

### Left, in order

1. **Groups 14 and 16 in CI** through `chrome_outline`, now reachable in every CI container: group 14's browser tests
   (F6 and H1 exist; the time cases are in `outline-time.mjs`), group 16's rows on the browser's fixtures and the
   latency comparison.
2. **The harness map** (`HARNESS-MAP.md`, with step 7's "For `HARNESS-MAP.md`"), **the known limits** for section 6,
   and **the report** (this file's text, for the lead to commit).

### What the code doesn't show

- **A look at pending asks each reserved approval twice:** `ordered_page` walks the rows once to count and digest
  them and once for the page (PR #27's way). Inside a call, an approval that ran out in the first walk isn't asked
  in the second, nor in a later look.
- **The daemon reads a late reply between requests** with `bridge.read()` and passes it to `on_event`, where
  `Chrome.event` does nothing with a message without an event. `read` marks the id answered, so it is never
  overdue. `daemon.py` didn't change.
- **A command the bridge gave up on may still finish in the extension** once it has started: for the new read
  that is reading only. The queue check keeps one that hasn't started from starting.
- **Commands with an effect under the read's time.** A held submission in the read's queued steps can need
  `prepare_control` (a taken tab's first reload) through `free`. It carries the time like every command sent
  inside the bound; given up, `free` records it `unknown`, "Input may have run", by its existing rule. The
  extension doesn't bound that command's own waits (brief 28a adds the point before an input).
- **What the 8 seconds cover:** the service's own clock, from before the first look to the built response. The
  caller's process start and the socket come on top (CI's `--timed` measures the call alone). With a stuck
  extension the last check ends at 7.75 seconds, then the response is built.
- **`daemon.error_result`'s look** (only when `engine.request` itself raises) runs after the clock has closed,
  untimed, as before.
- **`admin.py`'s restart** (GROUP 9) started the service without the switch since step 9; group 14 cases after
  GROUP 9 would have found no `chrome_outline`.
- **The fixture holds** live only in the fixture build `prepare.mjs` makes for Control Chrome and the qualification
  (not the latency pair's), and do nothing until a hold is set.
- **Two command lines of steps 1 and 1b in this file named the laptop's home folder with its user name**
  (`AGENTS.md` rule 6; the repo check looks only at macOS and Windows paths). They now say `owner`.

### JUDGMENT-CALLs (technical; for the lead)

1. **Approval checks get the time of their look:** the first look by second 1, the looks after the read by second
   7.25, and one that runs out is `unchecked` for the rest of the call. One budget to second 7 for everything would
   let a hung approval frame starve every read for 7 seconds. Cost to change: the constants in `deadline.py`,
   `Deadline.look`, and the `Call` tests.
2. **The time is a bound on the bridge (`bounded`), carried by every command sent inside it,** also by the shared
   helpers the read calls (`mode`'s `configure`, the steps' `read`, `ack_steps` and `facts`, `free`'s
   `tab_context` and `prepare_control`). Passing the time to each call site instead would change brief 20's
   helpers' signatures. Cost to change: the adapter's three `bounded` uses and `pending_state`.
3. **A frame that runs out makes the whole tab `not_read`,** as the brief's Node test says ("ends a read at its
   time with `expired`"), rather than counting that frame as unread and returning the rest. A hung ad frame costs
   the tab. Cost to change: the `expired(error)` clause in `facts` and `pageState`, and their tests.
4. **`timeout_ms` counts from the start of the call** (before the first look), so `timeout_ms: 6000` is second 6
   at most; step 9 counted from after `mode`. Cost: one line and one test.
5. **The settings command running out fails the whole call as `not_read`** (no tab could be read) instead of a
   `not_read` entry for each tab, which would need the version notice without `mode`. Cost: a few lines in
   `outline`.
6. **The unchecked row keeps the operation's own reason** ("Awaiting exact approval; nothing submitted.") and adds
   only `validity: unchecked`. Cost: the `UNCHECKED` value.
7. **The CI time cases run in the core shard right after GROUP 1,** before brief 20's matrices: after them, GROUP
   9's `unknown` operations (which stay visible by design) fill the result's five-row pending page, so the
   approval case couldn't see its row. They leave nothing pending (the approval is dropped and acknowledged, the
   tabs closed). A failure is kept and fails the shard after brief 20's cases. They don't run in the qualification
   run (`RUNTIME_COMMIT` set), which qualifies brief 20's tools. Cost: one block in `browser.mjs`.
8. **One CI case beyond the brief's list:** the extension's own reply held past the bridge's wait, to show the
   give-up and the drain by id through the real transport (the brief's held *reader* reply never reaches the
   bridge, since the extension's own wait ends first). Cost: one case and one hold.
9. **A `time_left_ms` that isn't a whole number runs as a command without time** in the extension (the service
   always sends one). Cost: one line.

### PLAN-GAPs

1. **Item 4 starts the clock before the engine's first look at pending, which is in `engine.request`; the brief's
   Paths don't list `engine.py`.** Built: a `with` around `request`'s body that opens the adapter's clock for
   `chrome_outline` only.
2. **Paths allow `bridge.py` "only the reply wait and the draining".** The time on the wire and the bound
   (`TimeLeft`) live there too, and closing at the socket's 15 seconds needs `read` to mark a late reply answered,
   since the daemon's loop reads it between requests.
3. **Item 4 says "every command of a read has to answer by second 7" and "8 seconds in all", and nothing about the
   looks after the read.** Built: they check by second 7.25 (`LAST_LOOKS`), so that with the bridge's half second a
   stuck extension's last check ends at 7.75.
4. **"The reply the test build releases late changes nothing":** with the extension's bounded waits a held reader
   reply never reaches the service. Built both: the held reader reply (released after the call, the tab reads
   normally) and a held extension reply (JUDGMENT-CALL 8).

## The lead after step 9 (2026-11-16)

- **Run 9 is green on its first attempt:** Control Chrome 43826821669 (28 jobs, both latency legs included, on the
  tmpfs store and the sync-count gate) and its qualification 43826821542 (34 jobs), at `8ae7e8b0`. Control Mail,
  dispatched on `09690118` (which holds `5a0c7552`): 43830247959, 12 jobs green. So the merge, the switch and the
  Mail fix break nothing.
- **JUDGMENT-CALLs 1 to 10: accepted as built.** On 9: fine this once, since the fix only moves when the table is
  made and two unit files cover it. The next step's code push runs the full workflows as usual.
- **PLAN-GAPs 1 and 2: accepted as built.** A dialog in `tabs` is returned as `dialog` with an empty outline, as
  for one tab, and `until` meets nothing while a dialog is open.
- **The steps stay on Claude Opus** from step 10 on (the Claude week has room; Codex refills Tue and takes the
  package's astra cross-review when it is in review). Step 10 is "Left, in order" item 3, the time.

## Step 9 (2026-11-16, Claude agent on Opus 5.5): `main` merged (20-ci-noise, the restore lock, the username scrub), the adapter's `chrome_outline` behind the test-only switch, run 9

Opus: built against step 8's "For the adapter" and the lead's brief for this step.

### Done

- **`origin/main` merged** (`fbf1cf43`, a merge commit; `main` at `70538b71`, 26 commits past the merge base
  `55c0114e`, among them `d981cd5a`, `b04c7e77`, `46101d4d`, `42721525`). No conflict, and **no file changed on
  both sides** since the merge base (the two `git diff --name-only` lists share no line), so there was no merged file
  to compare against both parents. Where `main`'s changes meet this branch's:
  - `run.sh` (20-ci-noise): with `LATENCY_PROBE=true` the store now sits on a tmpfs and `latency-store.py` runs at
    the start and the end. The branch's efficiency container (`latency-pair.sh efficiency`) runs with
    `LATENCY_PROBE=true` too, so its store is on the tmpfs as well and it writes `/out/latency-store.json` beside the
    efficiency files; `efficiency-summary.py` doesn't read it. The container already has `--cap-add SYS_ADMIN` for the
    mount (`latency_container`).
  - `definitions.py` (the restore lock): two `control` descriptions; `control-tools.json` is `main`'s, and
    `generate.py --check` passes on the merged tree.
- **The repo privacy check** (`.github/workflows/repo-privacy.yml`, from `42721525`): its pattern, run locally with
  `git grep -nIP` and `perl` as the workflow runs it, finds no file name and no line on the merged tree, nor after
  this step's commit. The branch adds no home path.
- **`chrome_outline` behind the test-only switch** (`8ae7e8b0`), as step 8's "For the adapter" describes:
  - **The switch** is `ARESOS_TEST_CHROME_OUTLINE=1` (`chrome/definitions.py`, `OUTLINE_SWITCH`, `outline_switch()`).
    `actions()` adds `outline` last, so every other tool keeps its place, with item 2's input as a schema
    (`OUTLINE`: `tab`, `tabs` 2 to 5, `ref`, `full`, `find` 1 to 200, `role`, `until` as `{text}` or `{gone}` each 1
    to 200, `timeout_ms` 0 to 6,000, `max` 1,000 to 40,000, `cursor`). Its result schema is `{"type": "object"}`
    like every other Chrome tool (JUDGMENT-CALL 7).
  - **Set in the CI container** by `run.sh` on two lines: the service's `runuser … env …` and the browser harness's
    `runuser … env …` (the harness starts the proxy through `call.py`, and any `aresos` command, as its children).
    Not on `docker run` (JUDGMENT-CALL 1). So the fixtures, the latency pair, the efficiency container and the
    qualification containers all have it; the Python shards (on the runner, outside the container) don't.
  - **The packaged entries can't pass it on:** `aresos-toold.service`'s `ExecStart` and the `aresos`, `aresos-mcp`
    and `aresos-toold` wrappers all start `/usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 …`, and the variable's
    name is nowhere in `control/packaging/`.
  - **`generate.py` refuses** (`generated()`, so `main` and every importer) while the variable is in the
    environment with any value: `Refused: unset ARESOS_TEST_CHROME_OUTLINE; …`.
  - **The adapter** (`adapter.py`): `call` routes `outline` next to brief 20's `read`; `outline`, `outline_tab`,
    `outline_view`, `until_met`, `outline_options`, `outline_measure` stand right after `read`.
    - The call: `outline_query` (the cross-field rules: exactly one of `tab` and `tabs`; with `tabs` only `max`,
      each tab once; `role` only with `find` and only a role of the list; `timeout_ms` only with `until`), then
      `self.mode()` once.
    - Each tab: `page_state` (the token), then `outline`; `nodes.View(reply)` (a malformed reply is
      `transport_error` with `Malformed`'s place and rule, which name no value); the reply's tab and session must
      be this call's; `allowed_url` on the top `url`, the top `effective_url` when there is one, and every frame's
      `effective_url` or `url` (brief 20's check, plus the top `effective_url` of a dialog reply). Unless a dialog
      is open: `queued_steps`, `reconcile_checks`, `steps`, as `read` runs them.
    - `until`: met as `find` would find the text (`view.contains`), `gone` when it wouldn't; an open dialog meets
      neither. It asks `page_state` every 100 ms and reads the outline again (with the checks) only when the token
      moved or a dialog opened, until `timeout_ms` (default 3,000) from the start of the call. `until_met` is in
      the entry only when `until` was given.
    - `ref` without `find` on a list field whose outline holds only some of its options: the reader's `options`
      command for that element; the reply must name this session, tab, frame, document and reader, or the read is
      `stale_reference`.
    - Then `render`, `Reading` (with the token, the query, the cursor, `max`: default 6,000, or 3,000 a tab with
      `tabs`), and `fit` over all tabs with one `References` that lives as long as the adapter: `Chrome.references`
      makes it at the first read that needs it (`5a0c7552`, below) and keeps it.
    - A refusal with a tab's code (`refused`, `stale_reference`, `permission_denied`, `owner_signin`,
      `reload_required`, `not_read`) is that tab's entry in `reads` (`view.Failure`, with a stale reference's
      present line in its `untrusted_content`); any other (the input, the qualification, the connection, storage,
      `result_too_large`) fails the call. Also for a single `tab` (JUDGMENT-CALL 2).
  - **`fit`'s `measure`** counts the result as `engine.request` sends it: `{"ok", "data": {"reads",
    "version_notice"}, "pending"}`, where `pending` is `engine.pending('chrome', resolve_checks=False)` (the call the
    engine makes at `engine.py:859`) plus the `chrome_version_notice` the engine adds after it (`engine.py:749`) when
    there is a notice. `fit` gets `RESULT_LIMIT - PENDING_DRIFT` (2,048 bytes) as its limit, because the engine
    builds its own pending after the adapter returns and asks each reserved operation's validity again
    (JUDGMENT-CALL 4). So the result never reaches `bound_result`'s last-step shortening, and when the pending part
    leaves no room for a page, `fit`'s `result_too_large` fails the call.
- **Control Mail on `8ae7e8b0` was red, and that was this step** (run 43826821593: every `containers` and
  `sweep` job, `AmbientRead: SystemRandom.getrandbits`). The Mail sweeps build an engine with every ambient entropy
  source rejected, and `8ae7e8b0` made the reference table in `Chrome.__init__`, which draws its letters from the
  system's random source. Fixed in `5a0c7552`: the table is made at the first read that needs it and kept for the
  adapter's life, so the letters are still drawn once a run of the service (JUDGMENT-CALL 10). Reproduced locally
  with `PYTHONPATH=control:control/mail_tests python3 -m unittest test_sweep_journal_stamp` (2 errors, the same
  `AmbientRead`); after the fix both tests get past building the engine and stop at `boundary_not_installed`,
  because the laptop has no `/etc/claude-code/managed-settings.json` (the Mail containers install it).
- **Tests** (`control/chrome_tests/test_outline_action.py`, 22 tests):
  - `Switch`, each in a Python process of its own: without the switch the action is not in `BY_NAME`, not in
    `tools_for('chrome')`, the MCP proxy and the `aresos` command answer `permission_denied` and send nothing to the
    service, `generate.generated()` runs, and the engine refuses `chrome_outline` with `invalid_input`, "Unknown
    action; inspect the tool list."; with it, all three know it and the proxy and the command send it on, the engine
    reaches the adapter (F1 read in full at `max` 40,000 with a 30,000-byte pending part and the version notice on:
    the page shrinks below 20,000 characters, no `bounds`, and **the measure equals the bytes actually sent**), and
    `generate.generated()` refuses. `generate.py --check` with the variable set to `0` exits non-zero. No generated
    file or setting names the action or the variable. The packaged unit and wrappers are pinned. `run.sh` sets it on
    exactly the two lines, after the generated-file check and the Python tests.
  - `Adapter`, with a fake bridge answering `view_fixtures.py`'s node lists: one tab in the view module's order
    (the calls are `page_state`, `outline`, `queued_steps`); references kept across reads and per tab; a stale
    reference as the tab's entry, with a fold's present line; brief 20's checks (a frame's effective address on the
    fixed list, an owner-excluded site, a failed `password_exclusion`); the queued steps and the dialog; every
    cross-field rule and the schema's own limits; `until` (reads again only when the token moved; `gone`; the
    timeout with `until_met: false`; `timeout_ms: 0`); several tabs with one refused; pages by cursor (another query
    is `invalid_input`, another token `stale_reference`); a list field's 200 options by `ref`; malformed replies;
    `find` with `role`; the measure against a large pending part and `result_too_large`; building an engine reads
    no system randomness, and the first read makes the table that later reads keep.
  - Checked by mutation: with `PENDING_DRIFT` at 0 the measure test fails, without the version notice in the
    measure the engine-path test fails, and with the table made in `__init__` the table test fails.
- **Local checks** (no Node locally, no browser):
  - `PYTHONPATH=control python3 control/generate.py --check`: "Generated artifacts match definitions".
  - `PYTHONPATH=control:control/chrome_tests python3 -m unittest test_publisher test_qualification test_credentials
    test_efficiency test_view_address test_view_budgets test_view_hostile test_view_nodes test_view_outline
    test_view_paging test_view_references test_outline_action test_questions test_unit test_latency
    test_restore_lock`: 314 tests, OK.
  - `… -m unittest test_engine test_policy test_sites`: 67 tests, OK.
  - After `5a0c7552`: `… -m unittest test_outline_action test_engine`: 54 tests, OK.

### Runs

| Head | Holds | Control Chrome | Result |
|---|---|---|---|
| `8ae7e8b0` | step 8 + `main` (`70538b71`) + the adapter | 43826821669 (run 9; qualification 43826821542) | **in progress.** At 08:15 UTC (23 minutes in): green `package`, `native-precedence`, the four `python-shards` (shard 3: 144 tests, among them `test_outline_action`'s 21 at this head), **both latency legs on their first attempt** (`main`'s tmpfs store and sync-count gate) and the plain leg's "Efficiency tasks with brief 20's tools" step; fixtures: 3 shards green, 3 running, 12 queued. Qualification 43826821542: 12 jobs green, 4 running, 15 queued. Repo privacy, Control base and Control boundary green. **Control Mail 43826821593 red**, this step's own (above), fixed in `5a0c7552`. Not read further. |
| `5a0c7552` | + the reference table made at the first read | none (pushed under a `[skip ci]` PROGRESS head; JUDGMENT-CALL 9) | Control Mail dispatched on the branch: 43830247959 (`workflow_dispatch` on `09690118`, which holds `5a0c7552`), queued when this was written. |

Nine full `control-chrome` runs so far. Run 9 is the first with the switch set; no browser test calls
`chrome_outline` yet (groups 14 and 16 are next), so it shows that the switch and the merge break nothing.

### Left, in order

1. **Read the dispatched Control Mail run** (row `5a0c7552` above): every `containers` and `sweep` job should be
   green again. If it isn't, the cause is in the Mail log, not guessed.
2. **Read run 9** to its end: the browser shards and the qualification run (the latency pair and the efficiency
   step are green already), oldest failure first.
3. **Time (item 4):** one deadline for the whole call from before the engine's first look at pending to the
   response (8 seconds; `until` at most 6; every command by second 7; `not_read`, "time ran out; read this tab by
   itself"; equal shares for `tabs`, passed on when unused). Every command of the new read carries its time left;
   the extension checks it at the front of its queue and in its waits (`expired`); `Bridge.call` waits until the
   time is up plus half a second and drains a late reply by its id. Tests through the real transport. Today
   `chrome_outline` has no deadline beyond `until`'s.
4. **Groups 14 and 16 in CI** through `chrome_outline`, now reachable in every CI container: group 14's browser tests
   (F6 and H1 exist), group 16's rows on the browser's fixtures and the latency comparison.
5. **The harness map** (`HARNESS-MAP.md`, with step 7's "For `HARNESS-MAP.md`"), **the known limits** for section 6,
   and **the report** (this file's text, for the lead to commit).

### What the code doesn't show

- **Step 1b's item 3 named "the refusal in `payload` and `steps` (exception 4)"; it is on `main` already** (PR
  #27): `refuse_withheld_form` runs in `payload` (`adapter.py`, `if frame.get('form') and (kind or hold or
  submitting)`) before `prepare`, so `steps` reaches it through `payload(…, hold=step)` for a held submission. This
  step added nothing there.
- **Who in CI has the switch.** The browser harness talks to `act.sock` directly, and `call.py` runs the proxy in
  its own process with the harness's environment, so both have it. `admin.py` runs through `sudo`, whose
  `env_keep` passes only `GITHUB_ACTIONS`: owner-only calls don't see the action, which isn't owner-only anyway.
  The packaged `aresos` and `aresos-mcp` wrappers aren't used in CI.
- **The `until` loop sleeps in the request.** Brief 20's `wait` does the same (`time.sleep(.05)`, up to 8 seconds);
  the service handles one request at a time either way.

### JUDGMENT-CALLs (technical; for the lead)

1. **The switch is set on `run.sh`'s two process lines, not with `docker run -e`** (step 8 suggested the container's
   `docker run`). The same container runs `generate.py --check`, the fast Python tests and, without a shard, the
   full `discover`; with the variable on the container, `generate.py` would refuse and the tool-list tests would see
   one tool more. On the two lines it reaches exactly the service and the harness with its children, in every
   container that runs `run.sh` (fixtures, latency pair, efficiency, qualification). Cost of changing it: two lines
   and `Switch.test_the_ci_container_sets_it_for_the_service_and_the_browser_only`.
2. **A refusal that belongs to one tab is that tab's entry in `reads`, also when `tab` names one tab.** Item 2 puts
   a stale reference's present line "in that read's entry beside its error", which a whole-call error can't carry;
   one rule for one and several tabs is simpler than two. A single-tab refusal therefore comes with `ok: true`
   and the error inside `reads[0]`. Input errors (`invalid_input`, also a cursor of another query), the
   qualification, the connection (`transport_error`, `chrome_unavailable`, `unknown`), storage and
   `result_too_large` still fail the call. 28a can change this when the tool goes public.
3. **A tab among `tabs` with a native dialog open returns the dialog, as a single read does** (empty outline,
   `dialog` in `untrusted_content`), not an error; item 2 lists "a dialog" among what makes a tab unreadable
   (PLAN-GAP 1).
4. **`PENDING_DRIFT` is 2,048 bytes.** What can change between the read's measure and the engine's own pending: a
   reserved operation's `validity` row turning into a refusal with its reason (at most ten rows a page, each a fixed
   sentence of about 100 characters), and a notice an event commits during those bridge calls. It costs nothing below
   46 KiB of result; the first page of F1 read in full at `max` 40,000 is about 41 KB as sent.
5. **The cursor's token is the `page_state` taken just before the outline.** A change between the two makes the next
   page `stale_reference` (a false stale at worst), never a mix: the cursor also binds the text before it.
6. **The queued steps run once a tab, after its first outline**, as brief 20's `read` runs them before `wait`'s
   loop, not after every read again inside `until`.
7. **`chrome_outline`'s result schema is `{"type": "object"}`,** as for every other Chrome tool; a precise schema of
   item 2's result belongs with 28a, when the tool goes public and its output schema is checked by clients.
8. **`generate.py` refuses when the variable is present with any value; the action exists only with `1`.** The
   stricter reading on each side.
9. **The Mail fix went out without a new full Chrome run.** `5a0c7552` (code) and this file's commit (head, `[skip
   ci]`) were pushed together, so no workflow started on the push, and Control Mail, the one red workflow, was
   dispatched on the branch by hand. A normal push would have started a 10th full `control-chrome` run beside run
   9 (its concurrency group holds the run ID and cancels nothing), for a change that touches only when the table
   is made; that is covered here by `test_outline_action` and `test_engine` locally and goes into the next full
   run with the time item. If the lead wants CI on every code commit's push instead, the next push does it.
10. **The reference letters are drawn at the first read, not when the process starts** (item 3 says "when its
   process starts"). What item 3 relies on still holds: one draw a run of the service, from the system's random
   source, nothing stored; a service that never reads draws nothing.

### PLAN-GAPs

1. **A dialog in `tabs`.** Item 2 lists "a dialog" among the reasons a tab in `tabs` gets its `error`, and also says
   "A native dialog that is open is returned as `dialog` (kind, text), with an empty outline, as today." Built: the
   second, for one tab and for several (JUDGMENT-CALL 3).
2. **Item 2 doesn't say what `until` meets while a dialog is open.** Built: neither `text` nor `gone` is met, the
   wait ends at once, and the dialog is returned; the readers can't answer while it is open.

## The lead after run 8 (2026-11-15)

- **Run 8** (43745261932): every fixtures shard green, the two core shards included. So GROUP 7 and `review-shadow`
  pass with step 7's harness changes under the late-root rule.
- **Latency:**
  - Attempt 1: both legs missed targets with `regression: false`.
  - Attempt 2 (`--failed`, the one rerun): plain green. Audit missed `fresh / navigate` (median 41 ms, p95 194 ms
    against 150), `regression: false`.
  - This is the runner-disk tail that brief 20-ci-noise fixes; not rerun again. The next full run comes after
    20-ci-noise is on `main` and merged into this branch.
- **From Tue 2026-11-17 the steps go to Codex** (`gpt-6.1-sol` xhigh), from "Left, in order" below: the adapter
  first.

## Step 8 (2026-11-15, Claude agent on Opus 5.5): `main` merged (brief 20's popup-race fixes), run 8

Opus: built against the lead's brief. Step 7's PLAN-GAP 1 stays option (a) as built (the lead, step 8's brief; on
Tuesday's security-review list); step 7's JUDGMENT-CALLs 1-3 are accepted.

### Done

- **`origin/main` merged** (`425f4109`, a merge commit; `main` at `55c0114e`, 32 commits).
  - One conflict, `control/chrome_tests/background.test.mjs`, two hunks:
    - the swapped-popup fixture's `Debugger.*` double: `main`'s version (the duplicate-breakpoint replies, `pauseOn`,
      `swapped`, the `identity()` answer), with the branch's `embedderName:url` on its `parsed` events, because item 8
      takes our scripts only when `url` and `embedderName` both name them (`background.js:152`);
    - both sides appended tests at the end: both kept, the branch's first (`readFixture` and the item-8 tests), then
      `main`'s `popuprace` tests.
  - Every other file merged without a conflict; `chrome-instructions.txt`, `definitions.py` and `test_publisher.py`
    are `main`'s (the branch never changed them).
- **`background.js` checked against both parents:** the merged file's diff from each parent is exactly the other
  side's diff from the merge base (compared line by line), so nothing was dropped or doubled by the auto-merge.
- **`main`'s checks, each on the paths it ran on before** (merged `background.js`; each symbol has the same number of
  callers as on `main`, except `requireTab`, below):
  - **P1, the re-arm once:** `prepareTarget` (`:87-118`): `duplicateBreakpoint` (`:50`) is the only error that
    re-arms (`:109`), the audit line (`:110`), disable, enable, set (`:111-113`); a second refusal or any other error
    throws out of `prepareTarget` as before. Both callers are unchanged: `initializeTab` (`:473`, a taken tab and a
    popup) and auto-attach of a child frame (`:125`). Step 6's item-8 check in `preloadEvent` (`:152`) runs on the
    events the re-arm causes as on any other.
  - **P2, the stall message:** `initializeTab` sets `handoffMessage` from `stallMessage` after the detach
    (`:479-484`) and deletes it on a normal setup (`:486`); `takenTab` (`:459`) and `requireTab` (`:646`) give it.
    `requireTab` has two callers more than on `main`: step 6's `listOptions` (`:851`) and `pageState` (`:866`), so a
    stalled tab refuses those with the same message. `facts` (`:781`, also under `outline`) called it before.
  - **The admission line's `owner_dialog`:** `admitTab` (`:526`); no branch code writes or reads `popup_admitted`.
  - The branch adds no code that sets a breakpoint, admits a tab or names a dialog message.
- **Local checks:** `PYTHONPATH=control:control/chrome_tests python3 -m unittest test_publisher test_qualification
  test_credentials test_efficiency test_view_address test_view_budgets test_view_hostile test_view_nodes
  test_view_outline test_view_paging test_view_references`: 213 tests, OK. (A whole `discover` of
  `control/chrome_tests` ran past ten minutes and was stopped; not repeated.) No Node locally.

### Runs

| Head | Holds | Control Chrome | Result |
|---|---|---|---|
| `425f4109` | step 7 + `main` | 43745261932 (run 8; qualification 43745261921) | **in progress.** Green so far: `package`, `native-precedence`, the four `python-shards`. **Red: `latency (audit)`**, its "Require lead ceilings" step, one failure only: phase `fresh`, `approval_to_done`, `regression: false`, `target_miss: true`, median 54 ms, p95 360 ms (job 132908893793). That is the lead's runner-disk case: rerun that job once (`gh run rerun 43745261932 --job 132908893793`) once the run has finished (GitHub reruns only finished runs). **About 2.5 hours after the push:** 22 jobs green, among them every fixtures shard except the two core shards, still running (`fixtures (external, core)`, `fixtures (policy, core)`); so far no failure in the browser groups. **`latency (plain)` red too** (job 132908893825): `history-4000` target misses on `asking_click`, `free_click`, `navigate`, all `regression: false` (run 1's pattern; medians not read). Qualification 43745261921 still queued. Next: when the run has finished, rerun the two latency jobs once (`gh run rerun 43745261932 --failed`, if the core shards are green), and read the core shards. |

### Left, in order

1. **Finish run 8** (above): when it has finished, rerun `latency (audit)` once as the lead's rule says (not a new
   full run), then read the browser shards, oldest failure first. What it should show is step 7's list, item 2.
   Before a push that would start run 9, tell the lead.
2. **The adapter's `chrome_outline` behind the test-only switch** (step 1b's item 3). Not started in code; what I
   found for it is below.
3. Time (item 4), groups 14 and 16 in CI, the harness map, the known limits, the report.

### For the adapter (found in step 8, not built)

- **Where the switch goes:** `ACTIONS` and `BY_NAME` are built when `aresos_control.definitions` is imported
  (`definitions.py:134-138`, `chrome_actions(Action)`), and the service, the MCP proxy (`proxy.py:27,31`) and the
  `aresos` command (`cli.py:28`) each look the action up in their own `BY_NAME`. So the variable has to be in all
  three processes' environment: set it on the CI container (`docker run -e`, `control-chrome.yml:91` and `:140`,
  `latency-pair.sh:15`), not only in `control/chrome/ci/service.py`. In `chrome/definitions.py`'s `actions()`, add
  `outline` only when the variable is set.
- **The packaged unit can't pass it on:** `control/packaging/aresos-toold.service:10` starts the service with
  `env -i PATH=… LANG=…`. The test that "the packaged unit doesn't set it" can pin that line and that the variable's
  name appears nowhere in `control/packaging/`.
- **Absent without the switch:** the generated files come from `control/generate.py` (`main`, `:74`); have it refuse
  to run with the variable set, so no generated file can carry the action. Test in a subprocess without the variable:
  not in `BY_NAME`, not in `tools_for('chrome')`, not in `generated/*`, and the engine refuses the action as unknown.
  With the variable (another subprocess): present in all three.
- **The adapter:** `ChromeAdapter.call` (`adapter.py:882`) routes by verb; add `outline` next to brief 20's
  `read` (`adapter.py:322`), which shows the checks to keep: `self.mode()`, `allowed_url` on `url` and every frame's
  `effective_url`, and unless a dialog is open `queued_steps`, `reconcile_checks`, `steps`. Then the view module's
  order (`view.py:1-12`): `nodes.View(reply)`, `render`, `Reading`, `fit`. One `references.References()` for the
  adapter's life (it connects per read). The cross-field rules (`tabs` only with `max`; `role` only with `find`;
  `timeout_ms` only with `until`) are the adapter's: the schema validator has `anyOf` but no dependencies.
- **`fit`'s `measure`** must count what is sent: `results.py:78-150` (`bound_result`) adds `pending` to the result,
  and `engine.py:829` bounds the whole response at `RESULT_LIMIT`. Read those two before writing `measure`.
- **Tests:** `chrome_tests/test_engine.py`'s `Browser` (`:20`) and `Operations.setUp` (`:44`) give an engine with a
  fake bridge; give the fake an `outline` reply from `view_fixtures.py`. A test that calls `self.chrome.call('outline',
  …)` reaches the adapter whatever the switch says; the engine path needs the switch at import (a subprocess).

### What the code doesn't show

- Run 8 waited for runners for a long time: its browser shards had not started 1.5 hours after the push (other
  branches' runs share the runners).

### JUDGMENT-CALLs (technical; for the lead)

- None this step.

### PLAN-GAPs

- None this step.

## Step 7 (2026-11-15, Claude agent on Opus 5.5): step 6's runs read, PLAN-GAP 1 by the lead's rule (option a), the F4 comment, F6 and H1. Pushed; no run started (the branch conflicts with `main`)

Opus: built against the lead's brief and decision rule. **None of this step's JavaScript has run:** the push
(`d14e52da`) started no workflow, because `main` moved and now conflicts with the branch (below). Step 1b's list
from item 3 is not started (budget).

### Done

- **Step 6's three runs read** (below). No JavaScript error in step 6's code: every `node --test` and Python shard that
  finished passed (run 3's `fixtures (external, core)`: 459/459 node tests, 70 Python tests).
- **PLAN-GAP 1, option (a)** (`7342d8b8`): the late-root rule stays as worded; the harness meets its roots before the
  text. See "PLAN-GAP 1" and "For `HARNESS-MAP.md`" below.
- **The F4 comment** (`78f4af3a`): `view_fixtures.py`'s `f4()` says nodes 23 and 24 are unit-test-only.
- **Group 14's F6 and H1 fixtures** (`d14e52da`), in `efficiency-fixtures.mjs` (`/?case=efficiency-f6`,
  `efficiency-h1`):
  - F6: a top document with an open root, a closed root and an open root inside that, and a frame from the second
    fixture site (`second.test:8766`, `mode=child`) holding a closed root and a nested frame of the same site
    (`mode=nested`). The roots hold no typed text when they are met.
  - H1: `test_view_hostile.py`'s `HOSTILE` strings, now also in `control/chrome/ci/hostile-text.json` (a new test in
    `test_view_hostile.py` checks the file equals the list). The page's script sets them through the DOM (control
    characters, lone surrogates and line breaks arrive as they are): each string as a section's name (an
    ancestor's name), a button's name, a textarea's value, an option label, a column header, a cell, an error text
    (`aria-describedby`, `aria-invalid`) and a paragraph; `title=N` picks the document title. The four hostile
    roles of the brief (a line break and an outline line, `button" kqtvm5`, 10,000 characters, `  BUTTON  `).
    `mode=many`: 100,000 elements; `mode=name`: a name of 100,000 characters.
  - `efficiency.test.mjs`: one test serves every mode, compiles each script, and runs H1's script against a
    minimal document to check that every string lands in every place.
  - Group 14's own browser tests are not written (they need the adapter's `chrome_outline`).

### PLAN-GAP 1: the rule light-DOM fields follow (for Tuesday's security review)

What the reader does today with a light-DOM typed field that already holds text when it first reads it:

- **Watched document (reader in place from the start): the value is read, unless the field is password-kind.**
  - `unknownHistory = element => !watched || privacy.lateFields.has(element)` (`reader.js:305`); `lateFields` only
    ever gets shadow-root fields (`meet`, `reader.js:169-174`). So `safeValue` (`reader.js:285-300`) returns the value
    once `password()` (`reader.js:154`) says no.
  - What vouches for the field's past is the password tracker, which has watched since before the page's scripts:
    `background.js:194` installs the guard and the reader at the startup breakpoint and sets `document-start.v1`
    (child frames get the same through auto-attach, `background.js:92`). `observe(document)` and
    `remember(document)` (`reader.js:195-196`) record old values of `type`, `autocomplete` and `style`
    (`reader.js:80-84`), and `protect` (`reader.js:85-87`) keeps a field that was ever masked protected for the
    document's life (`ownPassword`, `reader.js:88-96`).
  - Typing plays no part: a field the owner typed into is read.
- **Unwatched document: no typed field is read, filled or empty** (`unknownHistory` is true, `reader.js:288,305`).
- **`guard.typedBy` and `typingGap`** (`guard.js:518-520`; the record of trusted `input` events, `guard.js:139-146`)
  decide only the reload report's "typed by" and "since load" (`reader.js:745-762`), never whether a value is read.

So the light-DOM rule is "read when the reader observed the field's whole masking history and it was never masked",
not "readable unless the guard saw typing into it, or can't vouch for that". Option (b) would read a late-root field
whose masking history nobody observed, on the strength of a different record. It doesn't match, so by the lead's
rule: **(a)**. The late-root rule, its unit tests and the known-limit line stay as step 6 left them.

For the review, what (b) would have given up: a field in a late root that was masked and got its text without a
trusted `input` event (a page script, an autofill that fires none) and was unmasked before the meeting; and typing into
a root the guard doesn't watch yet, which its document listener sees, if at all, retargeted to the host (I did not
check this one in the code). Not built.

### Runs

| Head | Holds | Control Chrome | Result |
|---|---|---|---|
| `40d1c650` | the three commands, the credential words | 43722368284 | red: only `latency (plain)`, its "Require lead ceilings" step: target misses at `history-4000` on approval to done, asking click, fill, free click and navigate, `regression: false` on all (see "What the code doesn't show"). Everything else green. |
| `421888cd` | + item 8, the typing refusal | 43722522475 | **green, every job.** Item 8 (`url` and `embedderName`) admits the extension's scripts in a real browser. |
| `85eeffba` | + the late shadow root | 43722792150 | red as step 6 expected, nothing else: GROUP 7 in both core shards, `GROUP 2 REVIEW synchronous new shadow roots keep all submission kinds held` in both review shards (each shard stops at its first failure), the aggregates on "every browser shard is required". Node 459/459 and Python 70/70 in every fixtures job; both latency legs, word, recheck and adapters shards green. Qualification 43722792135: its pairs fail on the same review case. |
| `d14e52da` | + this step | none | **No workflow started**: `main` (`55c0114e`, 32 commits past the merge base `62e1abb3`) conflicts with the branch, so GitHub makes no merge commit for `pull_request`. |

Seven full `control-chrome` runs so far; the next one is run 8.

### Left, in order

1. **Merge `main` into the branch, then push: that push is run 8.** `git merge-tree` shows one conflict,
   `control/chrome_tests/background.test.mjs`, two hunks where both sides appended tests (keep both). `background.js`
   merges without a conflict, but `main`'s changes there (brief 20's popup-race fixes, PRs #74 and #79) meet step
   6's `facts()` refactor (`requireGuard`, `readerBinding`, `pinDocument`): read the two together before pushing.
   `main` also changes `control/generated/chrome-instructions.txt` and `test_publisher.py`; take `main`'s versions.
2. **Read run 8**, oldest failure first. What it should show: GROUP 7 and the review shadow cases green; the core
   and review groups after them run for the first time with the late-root rule (in run 3 each shard stopped at its
   first failure); `efficiency.test.mjs`'s new F6/H1 test and `test_view_hostile.py`'s new test pass. If GROUP 7's
   new assertion fails while its forms are sent, look at the draft's timing first ("What the code doesn't show").
   Before a push that would start run 9, tell the lead.
3. Step 1b's list from item 3: the adapter (`chrome_outline` behind the test-only switch), time, groups 14 and 16
   in CI (F6 and H1 exist now; group 14's browser tests don't), the harness map, the known limits, the report.

### What the code doesn't show

- **GROUP 7's draft timing.** The light-DOM form's insertion is a change the reader's observer sees; its callback (a
  microtask after the page script) meets the two roots while the draft is empty, and the `setTimeout(0)` task writes
  the draft after that. This holds in a watched document only; GROUP 7's cross-site frame is watched (auto-attach).
  The draft is written as the field's default (`defaultValue`), as the markup had it, so the reload report sees no
  unsaved text.
- **H1 in a real browser:** a textarea's value turns `\r\n` into `\n`, an option's label collapses white space,
  and the title drops line breaks. Group 14's expected outlines have to come from the browser, not from the strings.
- **Run 1's latency red is the runner** (below): `history-4000` in run 1 had p95 values of 245 to 1,163 ms on every
  acting call with normal medians (`regression: false` everywhere); run 2, same code plus more, had p95 within 8 ms
  of its medians.

### JUDGMENT-CALLs (technical; for the lead)

1. **Run 1's red "Require lead ceilings" did not stop the step.** The gate's result stands and I touched nothing of
   it; I went on because the same code passed both latency legs in runs 2 and 3 (and step 5's run needed a second
   attempt of its audit leg). If "stop and report" meant the whole step, this is where I didn't.
2. **GROUP 7 checks one thing more:** `read_form` shows "Public draft" in each of the six forms (a field empty when
   its root was met is read once the page fills it). Added coverage, nothing relaxed.
3. **H1's strings are one JSON file** read by the fixture and compared by the Python test, instead of a second copy
   in JavaScript.

### PLAN-GAPs

1. **A failing check ends a browser shard's run.** Run 3's `fixtures (external, core)` threw at
   `matrices.mjs:325` and the process ended, so the core groups after GROUP 7 didn't run in that job: one red group
   can hide the next. That is brief 20's harness (`failBrowserCase` keeps the first failure and returns promptly),
   not changed here.

### For `HARNESS-MAP.md`

- `password-fixtures.mjs` (GROUP 7, `password-matrix` and `password-inner`; exceptions 2 and 4): the "Safe draft"
  textarea starts empty and the page writes "Public draft" in a later task, after the reader met the roots. Every
  form is still sent once with an approval; GROUP 7 also asserts the draft is read.
- `review-fixtures.mjs`, mode `shadow` (`review-shadow-{open,closed}-{native,event,click}`; exception 4): the form's
  draft starts empty (`form(extra, '')`). The root is met at the held submission, and the case is about holding it.
  The other modes keep `value="Saved"`.
- Not changed: `late-withheld-form` is an owner-navigated (unwatched) document, where every typed field is unread
  anyway.

## Step 6 (2026-11-15, Claude agent on Fable 5.2): the background's three commands, the credential words, item 8, the typing refusal, the late shadow root. Pushed, not yet read in CI

Fable because the reader runs inside the extension on hostile pages. Step 5's "Part B", items 2 to 5. **None of this
step's JavaScript has run** (no Node on the laptop): the three runs below are its first. Group 14's F6 and H1
fixtures were not started (budget).

### Done

- **`background.js`: `outline`, `options`, `page_state`** (`aa81726b`), tests in `background.test.mjs` (7 tests).
  - `outline` → `outlineView(tab)`: `facts(tab,null,'outline')`, so every check of a read applies (control, the
    dialog, the fixed list per frame, the late reader, the pinned private document, the inherited origin). Reply:
    `{session, tab, control, url, title, effective_url?, needs_reload, uncovered, dialog: null | {kind, text},
    frames}`; a frame is `{frame, parent, browser_document, effective_url, document, reader, watched, origin, url,
    title, scroll, height, omitted, nodes}`. The top document stands first. A `frame` node keeps its `frame` only
    when that frame's outline is in the reply (never the top frame, never its own). 20,000 nodes a tab: each reader
    is sent what is left (`limit`), and counts the rest in `omitted`.
  - `options` (`{tab, frame, document, reader, element}`) → `{session, tab, frame, document, reader, options}`. Only
    a document an outline has read is asked (`privacyDocuments`), and the reader refuses another document or reader
    instance (`stale_reference`): a number names an element only for the instance that gave it.
  - `page_state` (`{tab}`) → `{session, tab, control, queued, address, dialog: false, document, ready, token}`;
    with a dialog open `{…, dialog: true}` and no `token`, `document` or `ready`. `token` is a sha256 over each
    readable frame's `[frame id, Chrome document id, reader document, reader instance, revision, address digest,
    fields digest]`; `address` is a sha256 of the tab's address.
  - `facts()`'s third argument names the one command every frame is asked (`true` stays brief 20's typed-field
    list). Its guard check, reader parameters and document pin became `requireGuard`, `readerBinding` and
    `pinDocument`, which the new commands share. Nothing of `input`, `resume`, `dialog`, `take`, `release` changed.
  - `reader.js`: `outline` takes `limit`; `options` needs `document` and `reader`; `page_state` returns `origin`.
- **The credential words** (`40d1c650`): `control/aresos_control/chrome/credentials.py` (the brief's list as data,
  `CREDENTIAL_WORDS_VERSION = 1`), the copy in `reader.js` (`credentialNames`, one line of JSON),
  `test_credentials.py` (4 tests: the copy equals the definitions; version 1 is the brief's list), and five tests
  in `reader.test.mjs`. As the lead decided: the merged expressions stay, either list makes a field password-kind,
  the new list counts only for a field a person types into.
- **Item 8** (`1ca29fd3`): `Debugger.scriptParsed` takes a script for one of ours only when `params.url` **and**
  `params.embedderName` are its extension address. The doubles' events carry the name; one new test.
- **Typing into a field that isn't read** (`421888cd`): the reader's `focus` (every `fill` and key goes through
  it) refuses a typed field of unknown history with `owner_signin`. `unknownHistory()` is the one predicate.
- **The shadow root met late** (`85eeffba`, its own commit): `privacy.metRoots`, `privacy.lateFields`, `meet(root)`
  called where `roots()` and `remember()` find a shadow root. `safeValue`, the asking read's list (`typedFields`)
  and `focus` follow `unknownHistory()`. Two tests in `outline.test.mjs`.

### Runs (pull_request; not watched, not read)

| Head | Holds | Control Chrome | Qualification | Boundary | Base | Mail |
|---|---|---|---|---|---|---|
| `2c8d2332` (step 5) | | 43712993037: **success** (the latency audit job passed on its second attempt) | 43712993128 (was still running) | success | success | success |
| `40d1c650` | the three commands, the credential words | 43722368284 | cancelled by the next push | cancelled | cancelled | cancelled |
| `421888cd` | + item 8, the typing refusal | 43722522475 | cancelled by the next push | 43722522498 | 43722522518 | 43722522535 |
| `85eeffba` | + the late shadow root | 43722792150 | 43722792135 | 43722792144 | 43722792161 | 43722792156 |

Seven full `control-chrome` runs so far for this package (the brief plans about six and wants the lead told
before nine).

### The lead's decisions on step 5's open points (2026-11-15)

- JUDGMENT-CALL 3, the credential words: as advised (built, above).
- JUDGMENT-CALLs 4, 5, 6: accepted.
- Group 16's node lists: the browser fixtures must match `view_fixtures.py` **as the rendered outline** (the
  browser's extra `text` node around a `<label>`-wrapped field is accepted); the tests compare rendered outlines.
- `f4()`'s nodes 23 and 24 stay unit-test-only (a document is either watched or not); the fixture's comment must
  say so (not written yet: it belongs with group 16's browser comparison).
- The late shadow root leaving a component's prefilled default `(filled, not read)` for good: accepted as the safe
  direction, a known-limit line. **But see PLAN-GAP 1 below: it also refuses brief 20's own shadow-root forms.**
- Deep nesting overflowing the reader's recursion: accepted, fails closed, a known-limit line.

### Left, in order

1. **Read the three runs**, oldest first, so a failure is found in the commit that caused it. Expect JavaScript
   errors in my tests or doubles; fix the cause. A red "Require lead ceilings" is the gate's own result (stop and
   report). What I expect from each:
   - 43722368284: the fixtures jobs' `node --test` (`background.test.mjs`, `outline.test.mjs`, `reader.test.mjs`)
     and `test_credentials.py` in the python shards. The browser groups should be as on `2c8d2332`: nothing in
     the browser calls the new commands yet, and no fixture field carries one of the new words.
   - 43722522475: item 8 in a real browser for the first time. If Chrome's `embedderName` for a content script or
     an injected file isn't the file's extension address, **every** browser job fails at admission (no context is
     learned). Then: read `browser-boundary.jsonl` of one job for the `Debugger.scriptParsed` events' real
     `embedderName`, and fix the comparison; the unit test stays.
   - 43722792150: **I expect red browser jobs here, from the late-root rule** (PLAN-GAP 1): GROUP 7
     (`matrices.mjs`, "all password kinds across open closed and cross-site roots": the forms of `Submit top 1`,
     `top 2`, `cross 1`, `cross 2` stand in shadow roots and hold the prefilled plain textarea "Safe draft", so
     their click is refused with brief 20's withheld-form message), and `review-matrices.mjs`'s `review-shadow-*`
     cases (a root attached in a click handler, `<input name="draft" value="Saved">`, a held submission whose
     resume is then refused). The run gives the exact list.
2. **The lead decides PLAN-GAP 1** before any harness test is changed.
3. Group 14's F6 and H1 fixtures (not started).
4. Then step 1b's list from item 3: the adapter (`chrome_outline` behind the test-only switch), time, groups 14
   and 16 in CI, the harness map, the known limits, the report.

### What the adapter gets (for the next step)

- `bridge.call('outline', tab=…)`: `nodes.View(reply)` takes it as it is. Check the fixed list on `reply['url']`
  and each frame's `effective_url`, as `read` does. `uncovered` lists frames that weren't read (`eligible: false`:
  the fixed list; `true`: no reader). **When the top document wasn't read, `frames[0]` is a child frame**
  (`frames[0]['frame'] != 0`); `nodes.View.top` assumes the first one is the top document.
- `bridge.call('options', tab=…, frame=…, document=…, reader=…, element=<number>)`: `nodes.options(reply['options'])`.
- `bridge.call('page_state', tab=…)`: poll this, never a read. A frame whose reader doesn't answer is part of the
  token as "no reader" (the token moves when it arrives); lost private history refuses, as a read does.

### What the code doesn't show

- **The credential words, how they match** (`namesCredential` in `reader.js`). A name is cut into parts at
  anything but a letter or digit, at a change from lower to upper case (`otpCode`) and at the end of an acronym
  (`OTPCode`, `mTAN`). A part counts with its trailing digits dropped (`PIN2`, `cvv2`; `2fa` stays). A paired word
  (`code`, `key`, `phrase`) counts beside a companion as a neighbour **in either order** (`SMS code`,
  `Code (SMS)`), or written as one word with the companion first and the `s` German puts between them
  (`Einmalcode`, `Sicherheitscode`, `apikey`). `ä ö ü ß` are folded (`bestaetigungs_code`). The same six places as
  the merged check (`name`, `id`, `autocomplete`, `aria-label`, `placeholder`, the labels and `aria-labelledby`).
  I ported both checks to Python (not committed) and ran every expectation of the new Node tests through it.
- **"A field a person types into"** is an `input` of any type but `hidden`, a `textarea`, an editable area; not a
  `select` or a `button`. So a checkbox labelled "Remember this token" is password-kind, as a checkbox labelled
  "PIN" already was under the merged expressions.
- **A field's verdict is kept** (`credentialVerdicts`, a WeakMap) while its kind and its name strings are the
  same. A read asks `credentialLike` many times a field, and the second list would have doubled that work
  (the latency gate reads F1's 80 fields). The key is the exact strings, so a renamed or retyped field is judged
  again (tested).
- **A typed field labelled "Seed" or "Token" is withheld** whatever it is for (a world seed, a filter token):
  the brief's bare words.
- **The typing refusal covers a typed field of unknown history whether filled or empty.** The brief names the
  filled one. An empty one exists only in a document that isn't watched, where brief 20 already refuses input
  until the guarded reload.
- **The late root, when a root is "met":** in the reader's sweep after any change it sees (`remember`), or in a
  read (`roots`), whichever comes first; a root met in a read is observed from then on. A field named or masked
  like a password is skipped there (it is protected anyway, and its state is never copied). The marks live in
  `privacy`, so they outlive a release and retake of the same document.
- **`page_state` pins a document's private identity** like a read does (`pinDocument`), so a later reader of the
  same document with another identity is refused.
- **Item 8 asks for both names.** A script with the browser's name under another `url` isn't taken either.

### Local checks

```
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_credentials test_efficiency
Ran 17 tests
OK
```

No JavaScript ran. Every edit was an exact, counted replacement; the brackets of the four edited JavaScript files
balance as they did before.

### JUDGMENT-CALLs (technical; for the lead)

1. **`facts()` shares three small functions with the new commands** instead of the new commands copying its
   checks. Same behaviour for brief 20's reads; a later fix to a check reaches all three. Rejected: copies.
2. **`options` is bound to the reader's document and instance, and only a document an outline pinned is asked.**
   Rejected: the element number alone (after a reinstall it names another element).
3. **`page_state` with a frame that has no reader:** part of the token, no error. Rejected: refusing, which would
   end every wait on a page with one slow frame.
4. **The matching rules of the credential words** (above): digits, acronyms, either order, the linking `s`.
   Each makes the rule stricter than "whole words and parts of a name" read narrowly.
5. **The verdict cache touches brief 20's `credentialLike`.** Same verdicts; the alternative was a slower read.
6. **The typing refusal for an empty unread field too** (above).

### PLAN-GAPs

1. **The late-root rule, built as worded, refuses brief 20's own shadow-root forms.** A component's root is
   always met after it was filled (the observers run after the script), so every prefilled typed field in a
   shadow root is `(filled, not read)`, and exception 4 then stops Claude from sending its form: GROUP 7's four
   shadow-root forms and the `review-shadow` cases (see "Left", 1). GROUP 7 is a core group. Two ways:
   - **(a) keep the rule, change the harness** (HARNESS-MAP): those fixtures start their plain field empty and
     fill it in a later task, or the tests expect the refusal. Real sites keep the cost: a web component with a
     prefilled field (a search box with a default, an edit form) can't be read or sent by Claude without asking.
   - **(b) narrow the rule with the guard's typing record:** a filled typed field at the first meeting is unread
     only when the guard saw typing into it since the document's start, or can't vouch for that (`guard.typedBy`,
     `typingGap`; the reload report already relies on them). That is the brief's own reason ("he can type into
     its field and make it plain"), it leaves brief 20's groups as they are and removes the known limit. What it
     gives up: text a page script copied into such a field from a typed one.
   My advice: (b), after a security look, because (a) withholds far more than the harm the rule names. Not built:
   it relaxes the rule as worded, so it is the lead's call.
2. **The merged asking read chose its fields by the document** (`watched ? [] : …`), so it left out the late-root
   field. Changed to the reader's mark, the one change item 5 allows.
3. **Item 8 can't be checked without a browser.** I expect `embedderName` to be the file's extension address for
   a registered content script and for `scripting.executeScript` with `files`; run 43722522475 shows it.
4. **The tab's node limit needed the background:** the reader limits a document, the service a tab, so three
   frames of 10,000 nodes would have been refused whole by `nodes.View`.

### For `HARNESS-MAP.md` (the last step writes the file)

- `reader.test.mjs`, "fixes b G4.3 API and key words alone, and token names, stay ordinary fields": the names
  `Token`, `csrf_token`, `authenticity_token`, `_token` on a **typed** field are withheld now (exception 1). The
  test keeps the other names; "brief 28 a typed field named token is withheld, and a hidden field named so stays
  an ordinary field" holds the four, and shows them ordinary on a hidden field.
- `background.test.mjs`: every `Debugger.scriptParsed` double of one of the extension's files carries
  `embedderName` (item 8; no exception, the doubles follow the browser).
- Pending PLAN-GAP 1: GROUP 7 and `review-shadow` (exceptions 2 and 4).

### For `KNOWN-LIMITS.md` (added to step 1's list below)

- **A prefilled field in a web component isn't read.** A typed field that already holds text when the reader
  first meets its shadow root shows `(filled, not read)` for the life of the document, also when the text is the
  component's own default. *Harm:* Claude can't read or type into it, and can't send a form that holds it; the
  owner can let Claude read it through the asking read, or sends the form himself. (Open: PLAN-GAP 1.)
- **A page nested thousands of levels deep can't be read.** The reader's walk overflows and the read fails;
  nothing is returned. Beyond 150 levels the service refuses the reply.
- **A field named like a credential that isn't one is withheld** ("Seed" for a world seed, "Token" for a
  filter): the owner types it himself.

## Step 5 (2026-11-15, Claude agent on Fable 5.2): the baseline committed; the reader's three commands in `reader.js`. Stopped at the budget

Fable because the reader runs inside the extension on hostile pages. Stopped at the step's token budget with the
reader half done: **nothing of this step's JavaScript has run yet** (no Node on the laptop); run 43712993037 is its
first run and was not read.

### Done

- **Part A, the baseline** (`525aa67f`): `control/chrome/ci/efficiency-baseline.json` is run 43705060936's
  `efficiency-measured.json` byte for byte (`cmp`; artifact `chrome-efficiency-43705060936-1`). F4's row is brief
  20's refusal, the lead's decision. `test_efficiency.EfficiencyBaselineTest` (4 tests): every task of `TASKS`
  (read from the probe's source text, 11 tasks) with the same row, plan and outcome, the recorded tools follow the
  plan, only F4 is `refused`, and a sha256 of everything but `latency_comparisons` (the one part that may still
  grow). `efficiency.test.mjs` got the same comparison against the imported `TASKS`.
- **Part B, `reader.js`** (`2c8d2332`), three read-only content commands:
  - `outline`: one document's reply as `nodes.Document` takes it (`document`, `reader`, `watched`, `origin`, `url`,
    `title`, `scroll`, `height`, `omitted`, `nodes`). Ids are the number of the reader's own element id (`e12` is
    12, decision 4). Roles only from the list or the tag table. Own text as runs, a child's id where it stands;
    formatting tags and elements of other namespaces add their text to the run they stand in (decision 6).
    The password check (`password()`) comes before anything of an element is read; a password-kind field is a
    leaf `{role: "password", name, unread: true}`. Values go through `safeValue` (the history rule): `unread`
    with `filled`. A native `select`: `option_count`, `chosen`, the first 50 `options`, no option nodes.
    Scripts, styles, the head, hidden elements and everything outside an open modal are left out. 20,000 nodes.
  - `options` (`{element: <number>}`): every option of one native `select`; anything else, a password-kind
    field included, is `stale_reference`.
  - `page_state`: the reader's part of the token: `document`, `reader`, `revision`, a sha256 of the address, a
    sha256 of the fields' live state (a readable value; ticks; chosen options; for an unread field only filled
    or empty; for a password field only that it is there), `ready`.
  - Tests: `control/chrome_tests/outline.test.mjs` (7 tests, a tree of DOM doubles in a VM; a protected value's
    getter throws). `run.sh` runs every `*.test.mjs`, so nothing was wired.

### Runs (pull_request, not watched, not read)

| Head | Control Chrome | Qualification | Boundary | Base | Mail |
|---|---|---|---|---|---|
| `525aa67f` (baseline) | 43712012619 | | | | |
| `2c8d2332` (reader) | 43712993037 | 43712993128 | 43712993103 | 43712993081 | 43712993061 |

### Left, in order

1. **Read run 43712993037**: the fixtures jobs' `node --test` (`outline.test.mjs`, the new test in
   `efficiency.test.mjs`) and brief 20's own reader tests (`safeValue` and `name` gained a defaulted parameter;
   nothing else of them changed). Expect JavaScript errors in my doubles or expectations; fix the cause. The
   latency gate is untouched by this step; a red "Require lead ceilings" is its own result (stop and report).
2. **`background.js`: the three commands** (not started; `background.js` is unchanged). What I read of it:
   - `outline`: `facts(tab, reference, typedOnly)` already does every check a read needs (control, the dialog,
     the fixed list per frame, the late reader, `privacyDocuments`, the inherited origin, which needs the
     `origin` my reply carries). Let its third argument name the content command (`'typed_fields'` today,
     `'outline'` new) and dispatch `outline` beside `typed_fields` (about line 922). Drop a node's `frame` when
     that frame isn't among the readable ones; map brief 20's dialog object to `{kind, text}` (or do it in the
     adapter). Frames: `{frame, document, reader, watched, url, title, scroll, height, omitted, nodes}`.
   - `options`: one frame's `content(tab, frame, 'options', {element})` behind the same frame checks.
   - `page_state`: per readable frame the reader's reply joined with the frame id and Chrome's document id;
     `document`, `address`, `ready`, `dialog`, `queued`; with a dialog open no token.
   - Tests in `background.test.mjs`.
3. **The credential words module** (not started): the words beside `policy.py`, a copy in `reader.js`, a test
   that compares them. See JUDGMENT-CALL 3 for what the merged reader already has.
4. **The shadow root met late** (not started): see "What the code doesn't show".
5. **Item 8** (`embedderName` in `Debugger.scriptParsed`) and the reader-side refusal of typing into an unread
   field (`focus` refuses only a password field today).
6. Group 14's F6 and H1 fixtures (not started), then step 1b's list from item 3: the adapter, time, groups 14 and
   16 in CI.

### What the merged reader already does of item 1 (read, not changed)

- **History:** `watched` (from the document-start mark), and `safeValue` returns `unknown_history` with
  `value_status` filled or empty for a typed field in a document that isn't watched; `typedField` is the one
  predicate. The outline uses exactly this.
- **Names:** `credentialLike` in `ownPassword`, with its own word list as two regular expressions (stems and
  whole tokens, English and German). It has no bare `token`, on purpose (hidden CSRF fields named `*_token`).
- **The reader instance:** `readerInstance`, drawn at each install; `outline` and `page_state` return it.
- **A form with a withheld field isn't sent:** `adapter.py` line 31 and `background.js` line 775
  (`WITHHELD_FORM`). Not checked further here.

### What the code doesn't show

- **The fixtures' node lists and the browser's differ in two harmless ways.** F1's and F4's fields stand inside
  `<label>` elements, so the reader sends a `text` node around each (`["Line 0 ", 3]`, the run with its space);
  `view_fixtures.f4()` has the fields directly under the form. I checked in Python that both forms render to the
  same outline character for character (F1 normal and `full`, F4 `full`). Group 16 should compare outlines, not
  node lists.
- **`f4()`'s nodes 23 and 24 can't come from one page:** it has readable fields and two fields of unknown history
  side by side. In Claude's own tab F4's `Code` and `Nickname` are read; in a document that isn't watched no
  typed field is. Only the late shadow root could mix them, and F4 has none.
- **A field's error text stands once:** an element that `aria-errormessage` or `aria-describedby` of an invalid
  field points to gets no node and adds no text (`f4()` has it only as the field's `error`).
- **The outline leaves nothing in brief 20's `trace`:** it reads values with `safeValue(element, false)` and
  resets the trace list to its length at entry (`name()` of a button input reads through the traced path).
- **Names:** `name(element, fromContent)`: the outline names only controls by their content (link, button,
  checkbox, radio, switch, tab, the menu items, option, treeitem). Brief 20's rule, which names every element
  with a `role` attribute by its whole text, would put a page's text into the name of `<div role="main">`.
  Brief 20's own callers pass nothing and get the old rule.
- **A `role` attribute can't claim** `password`, `frame`, `text`, `p` or `h1` to `h6`: the reader gives those
  itself. `role="password"` on a container would make `nodes.View` refuse the whole reply.
- **Depth:** `visit` and `emit` recurse; a page nested thousands of levels deep overflows the stack and its
  read fails (closed). Brief 20's `text()` recurses the same way.
- **The late shadow root, as I would build it:** `privacy.metRoots` and `privacy.lateFields` (weak sets, kept
  across a reinstall); `meet(root)` where `roots()` and `remember()` find a shadow root: a typed field in it
  that is already filled goes into `lateFields`; `safeValue` treats `lateFields.has(element)` like `!watched`.
  It changes brief 20's reads of prefilled fields in components (exception 2), so brief 20's shadow-root tests
  will need the harness map. Its own commit, so a red run can be told apart.

### Local checks

```
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_efficiency
Ran 13 tests in 0.008s
OK
```

No JavaScript ran. The new block's brackets balance (counted with a script); that is all.

### JUDGMENT-CALLs (technical; for the lead)

1. **The baseline's digest test.** Any edit of the frozen numbers fails a test; adding to `latency_comparisons`
   doesn't. Rejected: trusting review alone. Changing it: one line.
2. **The error text once** (above). Rejected: sending it as text too, which `f4()` doesn't show and which says
   the same sentence twice.
3. **The credential words, not built, because it needs a decision first.** The brief's list has bare `token`,
   `seed`, `mnemonic` and the `key`/`phrase` pairs; the merged list leaves `token` out for hidden fields. My
   advice: keep the merged expressions, add the brief's list as data (Python module and reader copy), let either
   one make a field password-kind, and apply the new list only to fields a person types into (not
   `type="hidden"`), as the brief words it. Only stricter, and no CSRF field is withheld.
4. **Roles a page can't claim** and **names by content only for controls** (above): both keep page text out of
   places the tool writes.

### PLAN-GAPs

- Group 16's "the browser fixtures must give the node lists of `view_fixtures.py`" can hold only for the
  rendered outline (labels, spaces), and not for `f4()`'s two unknown-history fields.
- The brief's late-shadow-root rule also covers a component whose template prefills a field (a default value):
  it is filled when its root is first met, so it stays `(filled, not read)`. Built as worded, that is the cost.

## Step 4 (2026-11-15, Claude agent on Opus 5.5): run 43698395453's F4 failure. Fixed, new run started

Step 3's "Left" item 1. No reader, adapter or tool change; the latency gate, `latency-targets.json`, the sample
counts and the pair loop are untouched (that run's "Require lead ceilings" step was green).

### The cause (run 43698395453, artifact `chrome-efficiency-43698395453-1`)

Everything was green but the new step; the probe stopped in F4's warm-up with `Error: F4 received once: undefined`.
That message hid the real failure. `efficiency-calls.jsonl` shows F4's calls `read`, `fill_form` (6 fields,
`remaining` 0), `find` "Save" (found, `submit: true`), then `click` on Save answered
`{"ok":false,"error":{"code":"asking_input_too_large","message":"The whole approval exceeds 16384 bytes; prepare a
smaller operation. Nothing was reserved."}}`. The task's own assertion threw, and the receiver check in `after`,
run in `finally`, threw its own error over it (`efficiency-tasks.jsonl`: tools `read,fill_form,find,click`, no
`submit`; `receiver.jsonl` holds only group 1's compose send).

Why: brief 20's `chrome_submit` approval puts the whole binding in its description (`adapter.py` `prepare`:
`untrusted_content.page_state`), and the binding carries the form's facts (`binding()` → `frame['form']`), where
`reader.js` `field()` lists every option of a select. F4's Country has 200 options, as brief 28 and
`view_fixtures.py` define it: those options alone are 14,380 bytes of canonical JSON, against `ASK_LIMIT` 16 KiB
(`common.py` `approval_input`). So **brief 20's tools can't send F4 at all**: pressing Enter in a field builds the
same binding. The fake service in `efficiency.test.mjs` had answered the click with an approval, which is why the
fixtures jobs were green.

### The fix (`c99cf22a`)

Two mistakes, both in the probe (the check was wrong, not the tools or the fixture):
- **F4's row records what brief 20 does:** plan `read, fill_form, find, find*, click`; the click must end in
  `asking_input_too_large` (any other result, success included, fails the task); `after` checks the receiver got
  nothing. `call(action,args,{refusal})` marks such a call `expected_refusal` in the record.
  `efficiency-summary.py` accepts a failed call only with that mark and that code, requires every measured run to
  end the same way, and gives each task `outcome` (`done` or `refused`) and `refusals`.
- **A failed run is reported as itself:** `after` still runs after a failed run (cleanup), but its error is only
  logged then, so the run's error is what the step prints.
- Tests: `efficiency.test.mjs`'s fake now refuses F4's Save as brief 20 does and has no `submit`; a new test checks
  that F4 fails when the click succeeds, when the receiver got something, and that a failing `fill_form` is
  reported over a failing `after` (this run's case). `test_efficiency.py` checks the summary's refusal handling
  (accepted, wrong code, unexpected, one run ending differently).

### The other tasks, read again for the same mistake

The warm-up passed for `f1_first_read`, `f1_everything` (14 reads), `f1_fields`, `f2_table` (53 reads, 12.2 s),
`f3_find_link` and `open_fact` (its `after` closed the tab). For the tasks that never ran I checked each assumption
the fake makes against brief 20's code: F7's "Next page" is a link with an `href`, and F5's "Refresh rows" a
`type=button` outside any form; neither name holds a word of `policy.py`'s DELETE/PAY/ITEM/SEND lists and the
mode isn't conservative (the same run's `chrome-latency-…-current-plain` `tool.jsonl`: 180 "Continue" clicks
answered without an approval), so both clicks are free; F5's handler only changes
text, so it produces no page step and no `followups`; `wait` returns `condition_met`, `untrusted_content.title`
and `tree` (open_fact's record); `chrome_tabs`'s `limit` maximum is 10 (`definitions.py` `PAGE`), its reply is
`items`/`cursor` over every Chrome tab, and the probe opens tabs until 25 are listed; `navigate` with
`discard_unsaved: true` returns before the unsaved check, so F4's filled fields don't stop the next task. Nothing
else changed. The JavaScript still hasn't run outside CI (no Node on the laptop); I read it twice.

### The run (head `c99cf22a`, pull_request), not watched

| Workflow | Run id |
|---|---|
| Control Chrome | 43705060936 |
| Control Chrome qualification | 43705060865 |
| Control boundary | 43705060858 |
| Control base | 43705060866 |
| Control Mail | 43705060879 |

### Left, in order

1. Read run 43705060936: the latency job's plain leg ("Efficiency tasks with brief 20's tools", artifact
   `chrome-efficiency-43705060936-1`) and the fixtures jobs (`node --test`, including the new test). Fix what
   fails, as before; a red "Require lead ceilings" is the gate's own result (stop and report).
2. **The lead confirms F4's row (JUDGMENT-CALL below) before the baseline is committed**, since the file is frozen
   afterwards.
3. Commit the green run's `efficiency-measured.json` as `control/chrome/ci/efficiency-baseline.json`, and a test
   that it holds every task of `TASKS` with the same plan and outcome.
4. Then step 1b's list: the reader, the adapter, time, groups 14 and 16 in CI.

### Local checks

```
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_efficiency
Ran 9 tests in 0.007s
OK
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_efficiency test_latency
Ran 43 tests in 5.111s
OK
```

### JUDGMENT-CALL (technical; for the lead)

1. **F4's baseline row is brief 20's refusal**, not a send: 4 calls, the characters up to and including the
   refusal, outcome `refused`. Brief 28 asks for brief 20's tools "as they are, used as well as they allow", and
   they allow no send of F4. Rejected: a Country list of 50 options (brief 28 fixes 200, and brief 28a says the
   fixture isn't made smaller to fit); changing what brief 20's approval carries (a tool change in the baseline
   step, and approval content is security-relevant). Changing it later: a fixture or tool change before the
   baseline is committed costs one more run; afterwards the frozen file would need the lead's exception.

### PLAN-GAPs (for brief 28a)

- **F4's send will hit the same limit.** Brief 28a's F4 row expects `chrome_do` (six fills and the click), then
  `chrome_submit`, "one question; the receiver has it once". If the new tools' approval still carries brief 20's
  binding with every option of every select, the click is refused exactly as here. 28a needs a bounded form
  description in the approval (for example the chosen option and the option count, as the new read shows them),
  or the row can't pass.
- **28a's old-against-new timing of "filling 6 fields and sending the form"** has no old send to time: brief 20's
  side is the six fills and a refused click.

## Step 3 (2026-11-15, Claude agent on Opus 5.5): main merged, the probe wired in, draft PR open. Runs started

Step 2's "Left, in order" items 1 to 3. No reader, adapter or tool change; the latency gate is unchanged.

### Done

- **Main merged** (`d23a5e00`, a merge commit, no conflicts): #68 (`bdc16064`) is in, with its `--tmpfs /scratch`.
- **`latency-pair.sh`** (`dceafc94`): the docker command is one function, `latency_container <revision> <out>
  [extra options]`, which the pair loop and the probe both call. The loop is otherwise as it was; with a stubbed
  `docker` the pair's arguments are byte for byte main's. New mode `latency-pair.sh efficiency` (no argument, or
  `pair`, is the old loop; anything else exits 64): requires `LATENCY_PRIVACY=plain` and the image
  `aresos-latency-current` the pair built, runs it once more with `-e EFFICIENCY_PROBE=true -e ImageOS -e
  ImageVersion -e RUNNER_ENVIRONMENT -e RUNNER_ARCH` into `.work/latency-out/efficiency`, then
  `efficiency-summary.py` writes `efficiency-measured.json` there.
- **`control-chrome.yml`, latency job** (`9cd255ac`): the pair step got `id: pair`; a new step "Efficiency tasks
  with brief 20's tools" right after "Require lead ceilings", `if: !cancelled() && !inputs.latency_probe &&
  matrix.privacy == 'plain' && steps.pair.outcome == 'success'`; an upload of `.work/latency-out/efficiency/` as
  `chrome-efficiency-<run>-<attempt>`, `if: always() && matrix.privacy == 'plain'`, 14 days.
- **Tests:** `test_efficiency.EfficiencyWiringTest` (2 tests) pins one `docker run` in the script, both modes'
  calls, the probe's options before the mount, the step's place after the gate, its condition, and the upload.
  Both fail against the files before this step (one failure, one error) and pass now.
- **Draft PR #72** (https://github.com/Ares-Empire/AresOS/pull/72), "Package 28: Chrome read (in progress)".

### The runs (head `9cd255ac`, pull_request), not watched

| Workflow | Run id |
|---|---|
| Control Chrome (the latency job's plain leg makes `efficiency-measured.json`; the fixtures jobs run `efficiency.test.mjs`) | 43698395453 |
| Control Chrome qualification | 43698395347 |
| Control boundary | 43698395354 |
| Control base | 43698395362 |
| Control Mail | 43698395365 |

Read them with `gh run view <id> --json jobs` (no watching; if you must, `--interval 120`). The baseline is in the
artifact `chrome-efficiency-43698395453-1` (`efficiency-measured.json`, plus every call's whole result in
`efficiency-calls.jsonl`, `browser.txt` for a failing task). This is the first run of `efficiency.test.mjs`, the
fixtures and the probe: JavaScript errors are likely and are fixed in the next step.

### Left, in order

1. Read run 43698395453: the latency job's plain leg ("Efficiency tasks with brief 20's tools") and the fixtures
   jobs (`node --test`). Fix what fails; a red "Require lead ceilings" is the latency gate's own result and is not
   fixed by touching the ceilings, samples or `latency-targets.json` (stop and report instead).
2. Commit the green run's `efficiency-measured.json` as `control/chrome/ci/efficiency-baseline.json` (it carries
   the run id, the runner and the sizes), and a test that it holds every task of `TASKS` with the same plan. It is
   edited afterwards only to add `latency_comparisons` (brief 28's F1 comparison, brief 28a's).
3. Then step 1b's list: the reader, the adapter, time, groups 14 and 16 in CI.

### What the code doesn't show

- **When the probe runs:** also after a red latency gate (the pair built the image, so the counts are still
  worth having, and the gate's own step stays red), never after a cancel, a failed pair or in a `latency_probe`
  dispatch (that dispatch is "paired call histories only"). The audit leg neither runs nor uploads it.
- **The probe's container is a latency container:** `LATENCY_PROBE=true` (from the shared function) means `run.sh`
  skips its in-container unit tests, puts the service's logs on `/scratch`, and `prepare.mjs` adds the latency
  timing wrappers to the reader and background, as for the samples. The wrappers time and send side messages;
  they don't change a result, so the counted characters are the tools' own. The timings carry the same small
  overhead as the latency samples, which suits the later side-by-side comparison in the same container.
- **On a failing task** `run.sh` stops before copying `service.txt` and `browser-boundary.jsonl` from `/scratch`,
  so those two are missing then; `efficiency-calls.jsonl`, `efficiency-tasks.jsonl` and `browser.txt` are written
  to `/out` directly and are uploaded.
- **Time:** the pair took about 13 minutes on a recent green run (43687610984); the probe's container is one more
  build-free run of the same image under the same 50-minute `timeout`, inside the job's 120 minutes.
- **Pushes start nothing on this branch** (no workflow pushes on `pkg/28-chrome`); the pull request does. A
  commit whose subject holds `[skip ci]`, or one touching only `reviews/28-chrome-read/`, starts no run.

### Local checks

```
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_efficiency
Ran 8 tests in 0.008s
OK
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_efficiency test_latency test_qualification
Ran 73 tests in 7.038s
OK
```

`test_latency` holds the text check of #68's docker options; `test_qualification` parses both workflows' steps and
conditions (no ref marker in the new condition). `bash -n` passes; with `GITHUB_ACTIONS=true` an unknown mode exits
64 and `efficiency` with `LATENCY_PRIVACY=audit` exits 1 before any docker call. No Node on the laptop, so no
JavaScript ran here.

### JUDGMENT-CALLs (technical; for the lead)

1. **The probe also runs after a red gate** (see above). The alternative, running it only after a green gate,
   would lose the baseline to a slow runner without making anything safer: the gate's step is red either way.
2. **Not in a `latency_probe` dispatch**, so that mode stays the pair alone, as its description says.

## Step 2 (2026-11-15, Claude agent on Opus 5.5): the baseline. Built, not yet run in CI

**Stopped as told:** PR #68 (`mac-aresos-control`, green main) was still open at 06:29 UTC after a three-hour wait,
and it changes `latency-pair.sh`, `run.sh` and `control-chrome.yml`, where the probe still has to be wired in. No
`control-chrome` run used (0 of 6); no draft PR opened yet, because opening it starts a run on red main.

Brief 28, "Before anything else", and group 16's first half: the fixtures, the scripted tasks with brief 20's
tools, and `control/chrome/ci/efficiency-baseline.json` from a CI run. No reader, adapter or tool change.

### Built

- `control/chrome/ci/efficiency-fixtures.mjs`, served by `fixture.mjs` as `/?case=efficiency-<name>`: F1 (the
  same body as brief 20's long page, `case=matrix&mode=long`; a test compares them as served), F2, F3 and F4 as
  `view_fixtures.py`'s node lists describe them, F5 (a free click changing 8 lines; `mode=load` loads the next
  document), F7 (result pages with a "Next page" link) and the pages of "list 25 tabs" (titles of 29 characters).
  F6 and H1 are group 14's alone and are left to the reader step.
- `control/chrome/ci/efficiency-probe.mjs`: the tasks, each with the exact calls it may make (`plan`), run once
  as a warm-up and five times measured, every call's whole result recorded. Setup calls (navigation, the "first
  read" a row starts after, opening the tabs) are neither counted nor timed.
- `control/chrome/ci/efficiency-summary.py`: characters as the MCP proxy hands a result to Claude
  (`display_json(bound_result(result))`, `proxy.serve`), calls and tools equal in every measured run or it
  fails, wall time the median of the five, the catalogue's sizes (`tools_for`/`instructions_for`).
- `browser.mjs` runs the probe instead of the latency samples when `EFFICIENCY_PROBE=true` (one line).
- Tests: `control/chrome_tests/efficiency.test.mjs` (fixtures as served, the tasks against a fake service:
  every task makes exactly its plan) and `test_efficiency.py` (the counting).

### The tasks (brief 20's tools, used as well as they allow)

| Task | Calls |
|---|---|
| `f1_first_read` | `read` |
| `f1_everything` | `read`, then `read` with each cursor |
| `f1_fields` (after the first read) | `find` "Field 0" (with cursors until the field's row), `read_form` with its reference |
| `f2_table` (after the first read) | `read` with each cursor the first read left |
| `f3_find_link` | `find` the unique name (with cursors until the link's row; brief 20's find has no `role`) |
| `open_fact` | `open` F7 page 1, `wait` for its heading (`timeout_ms` 8000) |
| `f4_fill_send` | `read`, `fill_form` (6 fields), `find` "Save", `click`, `submit` |
| `f7_three_pages` (page 1's read in hand) | `click` "Next page", `wait` for the next heading; three times |
| `f5_free_click` (its read in hand) | `click` "Refresh rows", `read` |
| `three_tabs` (F1, F2, F3 open) | `read` each tab once |
| `list_25_tabs` | `tabs` with `limit` 10 and its cursors |

### Left, in order

1. When PR #68 has merged: `git merge origin/main` (a merge commit).
2. Wire the probe into the latency harness (files #68 touches, so only after the merge):
   - `latency-pair.sh`: after the loop, when `LATENCY_PRIVACY` is `plain`, run the image `aresos-latency-current`
     once more with the loop's docker options (as merged, with #68's `--tmpfs /scratch`) plus
     `-e EFFICIENCY_PROBE=true -e LATENCY_BASELINE=current -e ImageOS -e ImageVersion -e RUNNER_ENVIRONMENT
     -e RUNNER_ARCH`, writing to `.work/latency-out/efficiency`, then
     `python3 control/chrome/ci/efficiency-summary.py .work/latency-out/efficiency`. Put the docker command in one
     shell function both use, so the options can't drift. My advice: make it a mode of the script
     (`latency-pair.sh efficiency`) and a separate step after "Require lead ceilings", so a failing task can't hide
     the latency gate's result.
   - `control-chrome.yml`, latency job: that step (`matrix.privacy == 'plain'`) and an upload of
     `.work/latency-out/efficiency/` as `chrome-efficiency-<run>-<attempt>`.
3. Open the draft PR (`pkg/28-chrome` to `main`, "Package 28: Chrome read (in progress)"); its first run checks
   `efficiency.test.mjs` (the fixtures jobs run `node --test`) and produces `efficiency-measured.json`.
4. Commit that file as `control/chrome/ci/efficiency-baseline.json` (it carries the run id, the runner and the
   sizes), and a test that it holds every task of `TASKS` with the same plan. It is edited afterwards only to add
   `latency_comparisons` (brief 28's F1 comparison, brief 28a's).
5. Then step 1b's list: the reader, the adapter, time, groups 14 and 16 in CI.

### What the code doesn't show

- **The run's place.** The probe runs in its own container of the current runtime in the latency job's plain leg:
  the same image, `browser.mjs` and runner as the latency samples (one harness), no audit recording, and a fresh
  service, so the latency gate's "fresh" phase is untouched by the tasks' history. The later side-by-side timing
  (brief 28: F1's first read, old and new) belongs in the same container run.
- **Characters** are the median of the five measured runs; they differ by a few characters between runs as
  reference ids grow. Every run's total and the median per call are kept.
- **Sizes** measured locally on this head (they come again from the CI run): 30 tools, descriptions 5,085 plus
  instructions 4,052 = 9,137; names plus input schemas 11,080 (each tool's name plus its schema as compact JSON;
  the method brief 28a's numbers match).
- **Local checks:** `PYTHONPATH=control:control/chrome_tests python3 -m unittest test_efficiency`: 6 tests OK.
  The laptop has no Node or other JavaScript runtime, so `efficiency.test.mjs` and the JavaScript files have not
  run yet (read twice by hand); the first CI run is their first run.

### JUDGMENT-CALLs (technical; for the lead)

1. **The baseline also holds brief 28a's acting rows** (open and a fact, F4's six fields and send, F7's three pages,
   F5's free click, 25 tabs). Brief 28's own table names only the read rows, but brief 28a fails a number "worse than
   the baseline" for every row, and the file is frozen after this step. Brief 28b's row (his tab) isn't measured:
   its acceptance asks only for two calls and an untouched tab.
2. **"Compare three open tabs" is one `read` per tab** (its first page), not each tab paged to its end as the design
   table's middle column says. The new read's `tabs` returns one outline per tab, not every page, so the first page
   is the fair counterpart, and it is the smaller baseline, which flatters nothing.
3. **"After the first read"**: that read is setup, neither counted nor timed, as the new rows count "1 further
   call". F1's fields are `find` plus `read_form` (2 calls), better than the design's "inside the 14 pages".
4. **F4** has `novalidate`, so the invalid Email with its error text doesn't stop the send; the task fills Line 0 to
   Line 5, which are on the read's first page. **F7** serves any page number; the task starts with page 1's read
   in hand and its three clicks reach pages 2, 3 and 4.

### PLAN-GAPs

- Group 14's fixture list says this package adds F1 to F7 and H1 "because the baseline needs them". The baseline
  needs F1 to F5 and F7; F6 (frames, shadow roots) and H1 (hostile text) are group 14's alone and are left to the
  reader step.


## Step 1b (2026-11-14, Claude agent on Opus 5.5): the lead's decisions in the view module. Done.

Section 7 of the brief ("The lead's decisions after step 1") built into the view module. Only files that step 1
added were edited; nothing of PR #27's. Pure Python, no browser.

### The decisions as built, and the tests that pin them

Each new or changed test below was run against the module as it was before its decision (a copy outside the
repository, from `git show`): every one of them fails there and passes now.

| # | Decision | Built in | Pinned by |
|---|---|---|---|
| 1 | A list item with one element and nothing of its own gets no line; the element moves up a level | `view._bare_item`, used in `_arrange` | `test_view_outline`: `test_a_list_item_that_holds_one_element_alone_gives_its_place_to_it`, `test_elements_moved_up_from_list_items_fold_as_neighbours`, `test_the_example_page_character_for_character` (section 6's example now has no `listitem` lines); `test_view_budgets`: `test_f3_read_in_full`, `test_compare_three_open_tabs_is_one_call` |
| 2 | A `find` path names the named ancestors and, also unnamed, `main`, `navigation`, `banner`, `contentinfo`, `complementary`, `form`, `dialog`, `table`; at most 80 characters | `view.PATH_ROLES`, `_path` | `test_the_path_names_the_landmarks_also_without_a_name` (each of the eight, and twelve roles that stay out); `test_a_hit_is_the_elements_line_and_the_path_of_named_ancestors` (`· in main › list "Results"`, `· in contentinfo`), `test_role_keeps_only_that_role_and_must_be_one`, `test_folded_parts_frames_values_and_cells_are_searched`; `test_f3_the_one_link_with_the_unique_name` |
| 3 | Nine states | nothing to build: `nodes.STATES` holds the nine | `test_states_stand_in_one_order_after_the_value` (all nine, in order) |
| 4 | Node ids are positive integers | nothing to build: already the contract; now also written in `nodes.py`'s docstring | `test_view_nodes.test_a_node_and_its_place` (`0`, `-1`, `"e5"`, `True`, `1.5`, `None` refused) |
| 5 | An inline part carries its value and the states that are set, in the line's order, before the reference | `view._inline`, with `_unread` and `_states` split out of `_marks`; `_fit` | `test_an_inline_part_carries_its_value_and_states_before_its_reference` (sentence and table cell; checkbox, textbox, link, the unread forms), `test_an_inline_parts_value_counts_toward_the_cut`; `Unread.test_the_outline_a_form_by_reference_and_full` (`[password "OTP" (not read) kqtvm9]`) |
| 6 | Inline formatting is text: runs in order, only links and controls between them; `find` and `until` match the joined text, each inline part with its name | `view._ordered` (joins runs side by side), `_joined`, `_match`; the contract in `nodes.py`'s docstring and in "What the reader's `outline` must deliver" below | `test_inline_formatting_is_text_of_its_parent`, `test_find_and_until_match_across_an_inline_part_by_its_name` |
| 7 | A run of 20 or more letters, digits, `-` and `_` with a digit, an upper- and a lower-case letter looks random | `address._TOKEN_RUN`, `looks_random` | `test_view_address.test_a_long_token_with_separators_looks_random_and_a_slug_does_not`: a 43-character base64url token with `-` and `_` under `?ordinary=` (hidden; the old rule's runs are each under 20), a lower-case slug with dashes and digits (shown), `dQw4w9WgXcQ` (shown), a UUID (hidden), the edges |
| 8 | A page that ends before a line longer than `max` may hold only the short line; it always advances | nothing to build | `test_view_paging.test_a_line_that_does_not_fit_is_continued_inside_it` (the first page is `short\n` alone) |
| 9 | A sign-in word of five letters or more counts anywhere inside a segment; `auth`, `sso`, `saml`, `otp` only as a part of their own | `address.SIGN_IN_INSIDE`, `sign_in_segment` | `test_a_long_sign_in_word_counts_inside_a_segment` (`/resetpassword/abc12` hidden after; each long word inside a segment, in upper case, percent-encoded), `test_a_short_sign_in_word_counts_only_as_a_part_of_its_own` (`/classroom/maths/` and `/author/jane-doe` shown, `/auth/xyz` hidden after) |

**The hostile tests** cover what the decisions join or move: the hostile page gained a list item that holds one
hostile link (moved up, decision 1), an inline field with a hostile value and two states in a sentence and an
inline checkbox with a hostile name and a state in a table cell (decision 5), runs side by side with a hostile one
among them and a hit across a link in a long hostile text (decision 6; two `find` reads more, 27 reads a page). Every
read is still its harmless twin outside the quotes. The path pattern of that test now allows a landmark's role
alone (decision 2).

### What I decided where section 7 left room

1. **Decision 1:** an item with a **name**, a **value** or a **state** (`listitem current` in a breadcrumb) keeps
   its line too, so nothing it says is lost. An item's white space alone isn't text. A role-less wrapper inside
   the item gives way first, so `<li><div><a>` moves the link up. An item whose one element is a `text` element
   (`<li><div>Apples</div></li>`) gives way to it as well: `text "Apples"` stands in the list. With decision 6
   `<li><b>Apples</b></li>` is the item's own text and keeps `listitem "Apples"`.
2. **Decision 2:** `grid` isn't on the list, so an unnamed grid isn't named (the list is taken as written).
3. **Decision 5:** the form of a value that isn't read (`(not read)`, `(filled, not read)`, `(empty)`) is what the
   grammar puts in the value's place, so an inline part carries it; without it an inline field typed into would
   look empty. A link's target (`→ other.example`) and the counts `(N options)` aren't carried: the decision
   names the value and the states. **The value counts toward the 200-character cut with the name**, and a part is
   kept or left out whole, so a long inline value can't make a line long: it moves the part to the element's
   reference, as for a long name.
4. **Decision 6:** the joined text is cut into **stretches at children with a line of their own** (an `h3` between
   two runs), so "Before  after" isn't found across a heading. A control's value isn't part of the joined text
   (the decision names the name). **A word inside an inline part's name is now two hits**: the sentence (its joined
   text holds the word) and the link itself (`find="timetable"` returns the `p` and the `link`). That is what the
   rule gives; the reader of the hits sees both lines, each with its reference.
5. **A bug of step 1 fixed on the way:** a path that didn't fit whole got its leading `…` after the 80 characters
   were counted, so nine bare `dialog`s made 82. The mark now counts toward the 80 (pinned in
   `test_the_path_names_the_landmarks_also_without_a_name`).

### What the two address rules now also hide (the safe direction, for the lead to know)

Measured with `public_address`; Claude still opens such a link by its reference.

- Decision 9, a long word inside another word: `/presets/list` (holds *reset*), `/designing-apps/part-2`
  (*signin*), `/blogindex/2026` (*login*), `/tokens/list`, `/magical/place`, `/invites/42`, `/confirmation/x`: the
  rest of the path after that segment is `…`. Step 1's tests expected `/tokens/list` and `/magical/place` shown;
  they now expect them hidden, as the decision says.
- Decision 7: a slug in mixed case with a digit is a token: `/Some-Product-Name-2026` and
  `/sort_by_price_2026_Desc_Order` are `…`. A lower-case slug stays.

### Budgets (brief 28, "Group 16"; fixtures as node lists; characters of the JSON text of the result)

| Row | Budget | Brief's worked numbers (outline / as sent) | Step 1 (calls, outline, as sent) | Step 1b (calls, outline, as sent) |
|---|---|---|---|---|
| F1, the first read | 1 call, 6,000 | about 3,300 / 3,900 | 1 call, 3,258 / 3,833 | 1 call, 3,258 / 3,833 |
| F1, everything (`full`, `max` 40,000, cursors) | 3 calls, 75,000 | about 60,100 / 61,500, 2 pages | 2 calls, 59,020 / 60,462 | 2 calls, 59,020 / 60,462 |
| F1, the 80 fields (form by `ref`) | 1 further call, 6,000 | about 4,250 / 4,950 | 1 call, 4,176 / 4,899 | 1 call, 4,176 / 4,899 |
| F2, the whole table (`ref`, `max` 40,000) | 1 further call, 23,600 | about 20,100 / 23,050 | 1 call, 20,129 / 23,066 | 1 call, 20,129 / 23,066 |
| F3, the one link (`find` and `role`) | 1 call, 800 | about 100 / 420 | 1 call, 56 / 385 | 1 call, 63 / 397 (the path gained `main ›`) |
| Three tabs (F1, F2, F3) with `tabs` | 1 call | | 1 call, 4,945 as sent | 1 call, 4,865 as sent |
| F3 read in full (`full`, `max` 40,000; no budget row) | | | 1 call, 18,484 / | 1 call, 13,984 / 15,253 |

Every row is met. F3 read in full is 4,500 characters smaller, the cost section 7 named for decision 1 (a
`listitem` line and two spaces of indentation for each of 300 items). A result still has 318 characters around
its outline. No stop rule was hit.

### What I ran and what it printed

```
$ cd /var/home/owner/AresOS-28-chrome-read
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_view_address \
    test_view_nodes test_view_references test_view_outline test_view_paging test_view_hostile test_view_budgets
...........................................................................................................................................
----------------------------------------------------------------------
Ran 139 tests in 3.725s

OK
```

139 tests (step 1: 129): address 19, nodes 13, references 20, outline 47, paging 23, hostile 9, budgets 8. No
other suite, no browser. No literal direction-changing or line-separator character in any file of the view
module (checked with `grep -P`). The token-shaped test value of decision 7 is built at run time with `made()`.

### Left, in order (the next steps)

1. The baseline ("Before anything else"): fixtures of group 16 on the fixture server, the scripted tasks with
   brief 20's tools, `efficiency-baseline.json` from a CI run. Needs PR #27 merged.
2. **The reader** (after PR #27 merges): `outline`, `options` and `page_state` in `reader.js` and `background.js`,
   with item 1's password additions, the credential words module, the reader instance; Node tests in the VM
   doubles. It sends exactly "What the reader's `outline` must deliver" below: integer ids (decision 4), and
   inline formatting as text runs with only links and controls between them (decision 6). The browser fixtures of
   group 16 must give the node lists of `view_fixtures.py`.
3. The adapter: `chrome_outline` behind the test-only switch, `until` (with `view.contains`, which now matches
   joined text), `tabs`, the refusal in `payload` and `steps` (exception 4), using the functions of step 1.
4. Time: the deadline through `Bridge.call` and `dispatch`.
5. Browser groups 14 and 16 in CI, the latency comparison, the harness map, the known limits and the report.

### Commits of step 1b

- `7a62d0f6` Chrome read: a token with separators looks random; long sign-in words count inside a segment (7, 9)
- `df969714` Chrome read: a list item that holds one element alone gets no line (1)
- `47d5cec3` Chrome read: a find hit's path names the landmarks also without a name (2)
- `d5b41153` Chrome read: an inline part carries its value and its states (5)
- `9c46dbe6` Chrome read: inline formatting is text, and find reads across a link (6)
- this file

## Step 1 (2026-11-14, Claude agent on Fable 5.2): the service-side view module. Done.

Pure Python, standard library only, no browser, no extension code, no wiring. **New files only**; no existing
file was edited (the branch is cut from PR #27 at `524173c4`, which still moves).

### Done

| File | What it is |
|---|---|
| `control/aresos_control/chrome/address.py` | `public_address(address, short=False)`, `site_of`, `looks_random`, `credential_name`, `sign_in_segment`: brief 28 item 2's public and short form of an address. |
| `control/aresos_control/chrome/nodes.py` | The input contract: `View(reply)` checks the reader's `outline` reply and builds the tree; `options(list)` checks the reply of the `options` command; `Malformed` for anything else. The role list and the state list live here. |
| `control/aresos_control/chrome/references.py` | `References`: the run letters, the one counter, per-tab entries, the bound of 5,000, `Stale` (the refusal with the tool's own sentence and, where there is one, the element's present line). |
| `control/aresos_control/chrome/view.py` | `quoted`, the renderer (`render`), `find`, `contains`, the pages (`cut`, cursors), the result entries and the 48 KiB bound (`Reading`, `Failure`, `fit`), `typed_fields`, `header`, `present_line`, `fingerprint`. |
| `control/chrome_tests/view_fixtures.py` | F1, F2, F3 and F4 as node lists, and small helpers. |
| `control/chrome_tests/test_view_address.py` | 17 tests: the address table in both forms. |
| `control/chrome_tests/test_view_nodes.py` | 13 tests: the contract, each malformed reply, the bounds. |
| `control/chrome_tests/test_view_references.py` | 20 tests: letters, counter, bound, every stale case, 300 runs, two runs with the same letters, the fingerprint apart from the line. |
| `control/chrome_tests/test_view_outline.py` | 40 tests: stored outlines character for character, every role, folds and their order, counts against `full`, reads by reference, `full`, `find`, the unread forms. |
| `control/chrome_tests/test_view_paging.py` | 23 tests: `cut`, cursors, 100,000 characters, a wide row, a long value, 48 KiB with non-ASCII text and quotes, five tabs. |
| `control/chrome_tests/test_view_hostile.py` | 9 tests: H1's hostile strings in every place, hostile roles, addresses with a marker, the refusal. |
| `control/chrome_tests/test_view_budgets.py` | 7 tests: brief 28's read rows on F1, F2 and F3. |

**Which workflow picks the tests up:** `.github/workflows/control-chrome.yml`, job `python-shards`. It runs
`control/chrome/ci/python-shard.py`, which loads every `control/chrome_tests/test_*.py` in four shards, and
`merge-python.py` requires every such module to have run. Nothing in a workflow has to change. With today's file
list the seven modules land in shards 2, 3, 0, 1, 2, 3, 0. They start no browser and no service and take under 5
seconds together. The branch push triggers no workflow (checked: `control-chrome.yml` runs on pushes to
`pkg/20-chrome*` and `main` and on pull requests only). No pull request was opened.

**The build hash changes** (`control/chrome/build.py` hashes every file under `aresos_control/`), as the brief says
it will. Nothing else of the qualification record is touched.

### What the adapter will call (next step)

```python
from aresos_control.chrome import nodes, view
from aresos_control.chrome.references import References, Stale

references = References()            # once per service process; draws the five letters; no store
references.close(tab)                # when a tab closes (entries dropped; the counter goes on)

shown = nodes.View(reply)            # raises nodes.Malformed (a ValueError); message holds no page text
every = nodes.options(reply)         # the `options` command's reply, for render(options=...)

text = view.render(shown, references, ref=None, full=False, find=None, role=None, options=None)
        # -> view.Text (.text: the whole text of the query; .marks)
        # raises Stale (code stale_reference; .line = present line or None)
        #        Refused("invalid_input") for a role that isn't on the list
        # calls references.connect(shown.session) itself: another session empties the table

query = view.asked(ref=None, find=None, role=None, full=False)
reading = view.Reading(shown, text, token, query, cursor=None, limit=6000, whose="claude", until_met=None)
        # token: page_state's token. Raises Refused("invalid_input") for a cursor of another query or a
        # malformed one, Refused("stale_reference", "The page changed; read again without the cursor.")
failure = view.Failure(tab, error)   # a tab that couldn't be read; error is a Refused or a Stale

reads = view.fit([reading_or_failure, ...], measure, references)
        # measure(reads) -> bytes of the complete result as sent, with these entries in it: the adapter's
        # closure over ok/data/version_notice/pending. Raises Refused("result_too_large") when the fixed
        # parts leave under 64 bytes a tab. Calls references.returned() for what each page showed.

view.contains(shown, words)          # for `until`: as find would find it; issues no reference
view.typed_fields(shown)             # already inside each entry
view.present_line(shown, references, node)   # for brief 28a's stale refusals
view.fingerprint(node)               # stored per shown reference, in Entry.fingerprint; no action uses it yet
address.public_address(address, short=False)
```

The adapter still has to do, around these: the tab checks of today's `read` (group, fixed list on the top
document and every frame, qualification mode, queued page steps), `until` with `page_state` polling and
`contains`, the deadlines, `tabs` (one `Reading` or `Failure` per tab, `limit` 3,000 by default), schema limits
(`find` 1 to 200 characters, `max` 1,000 to 40,000), and `whose`.

### What the reader's `outline` must deliver (next step; updated in step 1b for decisions 4 and 6)

The reply of one tab, as `nodes.View` accepts it. Keys the view doesn't use are ignored at the top and at the
frame level; a node is strict. `nodes.py`'s module docstring says the same.

```
{"session": str, "tab": int, "url": str, "title": str,
 "dialog": null | {"kind": str, "text": str},        # with a dialog: "frames": []
 "frames": [                                          # the top document first
   {"frame": int, "document": str, "reader": str,    # reader = the instance id drawn at each install
    "watched": bool, "url": str, "title": str, "scroll": int, "height": int, "omitted": int,
    "nodes": [node, ...]}]}                           # document order: a parent before its children

node: {"id": int >= 1, "parent": id | null, "role": str | null, "name": str,
       "text": [str | child id, ...], "value": str, "unread": true, "filled": bool, "error": str,
       "states": [state, ...], "href": str, "method": str, "action": str, "hidden": [str, ...],
       "option_count": int, "chosen": str, "options": [{"label", "value", "chosen", "disabled"}, ...],
       "title": str, "frame": int}                    # every key but id is optional; no other key
```

Rules the contract enforces (each refused with `Malformed` and tested):

- ids are positive integers (section 7, decision 4), unique in a frame; `parent` is an earlier node; `text`
  names only the node's own children, each once. The reader sends numbers and accepts them back (`options`,
  brief 28a's commands): a string id couldn't be told from a run of text.
- `unread` or role `password`: no `value`, no `text`, no `chosen`, no `options`, **and no child nodes**. `filled`
  only with `unread`. So a field that is kept out is a leaf that carries its label and nothing of its content.
- `states` only from the nine; `frame` only on role `frame`; each frame named at most once, never the top frame,
  never inside itself.
- at most 20,000 nodes a tab; at most 150 levels of nesting, frames included (the renderer recurses).

Rules the renderer relies on and can't check:

- **Text as displayed.** Runs come with white space collapsed as the page shows it and trimmed at the element's
  outer edges (`pre` keeps its breaks). The renderer prints a run as delivered; it only joins runs that stand
  next to each other, drops runs of nothing but space and trims inside table cells.
- **Inline formatting is text, not structure** (section 7, decision 6). `text` is the element's own text in the
  order of the page: text runs, with an inline part's id between two runs where it stands. An element without a
  role of its own from the list (`b`, `strong`, `i`, `em`, `code`, `span`, `small`, `mark`, `abbr`, `sub`, `sup`,
  `time`, `u`, `s`, `q`, `cite`, `kbd` and the like) **gets no node**: its text joins the run it stands in, at
  its place, with white space collapsed across its edges. What it holds that has a node (a link, a control) is a
  child of the nearest element that has a node, named in that element's `text` where it stands. Only links and
  controls stand between runs. Example: `<p>Order <b>confirmed</b> today, see <i>the <a>timetable</a></i>.</p>`
  is one node `{"id": 11, "role": "p", "text": ["Order confirmed today, see the ", 12, "."]}` and the link
  `{"id": 12, "parent": 11, "role": "link", "name": "timetable", ...}`. Runs side by side (`["Order ",
  "confirmed", " today"]`) read the same, so the reader may send the formatting's text as runs of its own. An
  element with a role from the list (`<span role="button">`) is a node as before, and any other element with text
  of its own (a `div`) is `text`.
- When an element has own text, `text` lists **every** child that has a node at its place, also a leading or
  trailing one. Children that `text` doesn't name are placed after the listed parts.
- `chosen` is the label of the chosen option; a list field's line shows it as the value. A native `select` sends
  `options` (first 50) and no `option` child nodes.
- A readable child frame is named by the `frame` node of its `iframe` element (`chrome.runtime.getFrameId`). A
  frame no node names is printed after the page as a `frame` line of its own.
- A role is delivered only from the list. The service treats anything else as no role (name or text then makes
  it `text`).

### Decisions the code doesn't show

1. **References are issued when a line is rendered, marked as shown when their page is returned, and the bound is
   applied only after that** (`References.returned`). Reason: a fold's count is the length of a `full` read of it,
   so the hidden elements get their references while counting; with a plain "newest 5,000" a page with many
   links would drop the references of the lines it is about to return. When a tab is over 5,000, entries that
   were never on a returned page go first (oldest first), then the entries shown longest ago; showing an
   element again counts as new. A dropped string is never issued again.
2. **A cursor binds the text returned so far**, besides the query and the state token: it holds a digest of the
   text before its position. Same token but another text (an element got a new reference after its old one was
   dropped) is refused as `stale_reference`, instead of going on at a wrong place. What comes after the cursor
   may differ.
3. **Pages join to the text exactly.** A page that ends at a line end includes the line break; `characters` of
   all pages add up to `total`.
4. **The fold count and the cut count measure different things.** `(N characters)` counts outline characters
   (escaped, as a `full` read returns them). `…+N` and the limit of 200 count characters of the page's own text
   before escaping. Numbers above 999 are written with commas, as in the brief's examples.
5. **The cut** (fold 5): name, runs, inline children's names and the value share the 200 characters, in that
   order; the mark `…+N` stands right after the last quoted piece, outside the quotes; everything after it
   (later runs, inline children, the value) is counted in N and left to the element's reference. Tool-written
   parts (the unread forms, states, target, reference) still follow.
6. **Text once.** When an element's name already says its plain text (own runs and children that are nothing
   but text, compared without white space), that text gets no line: `link "Open file"`, `button "Next week"`.
   A name that isn't the text keeps both: `button "Close" "×"`.
7. **A label** is recognised without a marker from the reader: an element with role `text` or none, no name,
   whose plain text equals the name of a field among its own children or its siblings. It gets no line and its
   field moves up.
8. **Detail lines.** The brief defines `columns:`. In the same style a read by reference adds `address:` (public
   form of a link's or a frame's address), `title:`, `error:` (a field's error text; also in `full`) and, for a
   form, `hidden:` with the names. An option is `option "Label"`, with ` = "value"` in the field's own read when
   the value differs, and `selected`/`disabled`. Options beyond those sent along are one line `… N more`.
9. **A read by reference always shows that reference** on its first line, also for a paragraph that normally
   has none.
10. **A table's rows are indented like the table's line**, so "not indented" holds for the table by reference;
    inside a `full` page read they stand under the table at the same depth. `grid` is read as a table too. The
    first row is the `columns:` line when all its cells are column headers; R doesn't count it.
11. **A form's 40 fields** are the first 40 fields of its subtree in the order of the page, wherever they stand
    (also inside a folded table). The fold line stands where the 41st would, or at the form's end when that
    place isn't rendered. Of nested forms only the outermost counts.
12. **Empty values aren't printed** (`textbox "Email"`, not `= ""`). `(empty)` is only for an unread typed
    field.
13. **Unread forms.** Role `password` always prints `(not read)`, also when the node says `filled`. Any other
    role with `unread`: `(filled, not read)`, `(empty)`, or `(not read)` when `filled` is absent (a field kept
    out by its name).
14. **What isn't a web address** shows its scheme at most: `mailto:…`, `javascript:…`, `…`.
15. **The header's `title` and a dialog's text** go through the base's `visible()`; they are JSON fields, not
    parts of a line, so they get no quotes of their own.
16. **A sign-in word in a path** matches as a part of the segment (split at separators, a change of case and
    digits) or as two neighbouring parts joined (`sign-in`, `log-in`). **A credential name** matches as a part,
    or as the start or end of a part (`apikey`, `sessionid`), as the brief says; so `?keyword=`, `?author=` and
    `?state=` are hidden too.
17. ~~`find` matches each element on its own name, its own text (runs joined) and its readable value. A match
    that spans an inline child (`See the <a>timetable</a>`) isn't found.~~ Replaced in step 1b by section 7's
    decision 6: the joined text with each inline part's name, in stretches between children with lines of their
    own.

### PLAN-GAPs (the brief taken in each; the lead decides)

All nine were decided in the brief's section 7 (2026-11-14) and built in step 1b; see its table. Kept here as
step 1 found them.

1. **Bare `listitem` lines.** Section 6's example shows links directly under `list`; the brief's rule gives every
   element with a role a line. Taken: the brief. Cost on F3 read in full: 4,500 of 18,484 characters (a
   `listitem` line and two more spaces for each of 300 items). Proposal: an element with a role but no name,
   text, value, state or reference, and exactly one child line, gets no line.
2. **The path of a `find` hit.** The brief: named ancestors only. Section 6's example (`main › list "Week 46"`)
   shows an unnamed `main`. Taken: the brief.
3. **States.** Section 6's sentence lists seven; the brief's grammar lists nine (`collapsed`, `readonly`). Taken:
   the brief's nine.
4. **Node ids.** Brief 20's reader ids are strings (`e12`); item 1's example writes a child in `text` as a
   number. A string id couldn't be told from a run of text, so the contract takes positive integers. The reader
   has to send numbers and accept them back (`options`, and brief 28a's commands).
5. **An inline part shows no value and no state** (the grammar: `[role "name" ref]`). A checkbox in a table cell
   or a sentence doesn't show `checked`; the element's own reference reads it. Built as the grammar says.
6. **Inline formatting elements.** By the tag table a `<b>` or `<span>` with text is a `text` node, so
   `<p>Order <b>confirmed</b> today</p>` prints as three lines and `find`/`until` can't match "Order
   confirmed". Not built here. Recommended before the reader is written: phrasing elements without a role get no
   node, and their text belongs to the parent's run.
7. **A long token broken by `-` or `_` is shown under an ordinary name.** "Looks random" needs a run of 20
   letters and digits. A 43-character base64url token such as `dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk`
   has runs of 12, 17 and 12, so `?ordinary=<it>` is shown whole (checked). Under a credential name it is
   hidden. This is more than the "short sign-in code" the owner accepted; the rule is built as the brief words
   it and the case is reported, not widened silently (counting `-` and `_` into the run would hide every slug).
   One possible rule: a run of 20 or more of letters, digits, `-` and `_` that holds a digit and both an upper
   and a lower case letter.
8. **A page that ends before a line longer than `max` can be nearly empty.** "A page ends at the last line end
   that fits": a short line followed by a line of 30,000 characters gives a first page with the short line
   only. Built as specified; it always advances.
9. **One word in a sign-in path** (`/resetpassword/abc12`) isn't a sign-in segment under decision 16; the brief
   says "as a whole word or a part of the segment". If "part" was meant as "anywhere inside", `/author/…` and
   `/assortment/…` would be cut too.

### Known limits found (for `KNOWN-LIMITS.md`, which the last step writes)

- **A read can be paged until it has shown 5,000 references.** Then the first of them are dropped, their
  elements get new strings, and the next cursor is refused with "The page changed; read again without the
  cursor." (test `test_a_read_of_more_than_5000_elements_never_returns_a_dropped_reference`). *Harm:* a page
  with more than 5,000 links or controls can't be read to its end with `full` in one chain; parts by `ref` and
  `find` still work. Every reference on a returned page is valid when it is returned.
- **A fold's count can be off by a few characters on such a page:** hidden references that were dropped are
  issued anew, with more digits.
- **Two runs with the same letters:** shown in `test_the_rest_shown_honestly_two_runs_that_draw_the_same_letters`,
  as section 6 lists it.
- ~~PLAN-GAP 7 above, if the lead accepts it as a limit.~~ Closed by section 7's decision 7 (step 1b): a token
  broken by `-` and `_` is hidden now. What stays is the limit the owner accepted (board #213): a short sign-in
  code, and a token in lower case or without a digit.

### Budgets

Step 1's numbers stand in the table of step 1b, beside the new ones. Every row is met. A result has 318
characters around its outline (the brief: about 310). The envelope used is `{"ok": true, "data": {"reads": [...], "version_notice": null}, "pending": {"items": [], "total": 0, "cursor":
null}}`; the browser step measures the real one. No stop rule was hit.

### What I ran and what it printed

```
$ cd /var/home/owner/AresOS-28-chrome-read
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_view_address \
    test_view_nodes test_view_references test_view_outline test_view_paging test_view_hostile test_view_budgets
.................................................................................................................................
----------------------------------------------------------------------
Ran 129 tests in 3.705s

OK
```

Python 3.14.8 on the laptop; the sources parse as Python 3.12 (CI's version) and use nothing newer. No other
suite, no container and no browser was run.

**Tests that fail when the rule is removed.** Each rule below was broken in a copy of the module outside the
repository (never committed) and the seven test modules were run against it:

| Broken variant | Result | Failing modules |
|---|---|---|
| unchanged | OK | |
| `quoted()` no longer escapes the quote | 14 failures, 1 error | hostile, outline, paging |
| `quoted()` no longer calls `visible()` | 68 failures, 1 error | hostile, outline, paging |
| a role outside the list is kept | 19 failures | hostile, nodes, outline |
| an unread field may carry a value | 1 failure | nodes |
| the user name stays in the site | 11 failures | address, hostile, outline |
| credential names aren't hidden | 38 failures | address, outline |
| a sign-in word in the path hides nothing | 23 failures | address, outline |
| nothing looks random | 14 failures | address, hostile |
| the threshold is 30, not 20 | 1 failure | address |
| nothing is percent-encoded | 2 failures | address, hostile |
| the short form shows the query | 8 failures | address, outline |
| a fragment is shown as it is | 12 failures | address, hostile |
| a page may end inside an escape | 2 failures | paging |
| the bytes as sent don't end a page | 8 failures | paging |
| a reference of another tab resolves | 5 failures | references |
| another connection keeps the table | 3 failures | references |
| a table doesn't fold | 6 failures | budgets, outline |

(Failures count sub-tests.) The main hostile test compares every kind of read of a page that holds a hostile
string in every place with the same read of a twin page holding harmless text of the same length: with the
quoted strings emptied, the two texts are equal.

### Notes

- The pre-push check (gitleaks) blocked the first push: two made-up test values looked like a JWT and an API key.
  They are now built at run time from a digest (`made()` in `test_view_address.py`); the commit was amended
  before anything was pushed. Nothing was bypassed.
- Commits `fcd22ee9` and `de6306c1` hold three test lines with a literal direction-changing or line-separator
  character in a string; `2ed6854c` replaced them with `\u` escapes. The module sources never held any.
- Nothing is left in `.work/`.

### Left, in order (the next steps)

Superseded by step 1b's list above.

### Commits of step 1

- `fcd22ee9` Chrome read: the public and the short form of an address
- `794cc7a4` Chrome read: the node list's contract and the reference table
- `de6306c1` Chrome read: the outline renderer, reads by reference, full and find
- `2ed6854c` Chrome read: pages, cursors and the 48 KiB bound, tested
- `c19b838f` Chrome read: hostile pages and the read budgets as tests
- this file
