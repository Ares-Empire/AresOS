# Package 51: setup text

## Scope and reading

- Read the whole brief, AGENTS.md, CLAUDE.md, docs/design/DESIGN.md,
  docs/WORKFLOW.md, docs/REVIEW.md, and package 48's report, including
  "For linux-aresos". Read the supervisor's message and forget_hub paths and
  their tests before editing.
- Confirmed branch `pkg/51-setup-text`; the worktree started clean.
- No commits, pushes, PR, workflow dispatches, mod changes or owner-tool
  changes: the lead commits this work.

## Done

- SETUP step 3 says `Making your home… (the first start takes a moment)`.
  One indented conditional line describes the title-screen fallback.
  Steps 1 and 2 and the saved-world line stay unchanged.
- `setup_closed` still fits: an automatic first creation can also end before
  the hub is created. Its lead stays unchanged.
- `forget_hub()` says the next start makes a fresh flat home by itself,
  followed by `Type retry.`. The `world_missing` instruction stays unchanged.
- Updated the first-start test's name and expectation. Added a regression
  covering all four SETUP reasons: automatic creation is the numbered path,
  clicks appear only in the conditional fallback, steps 1 and 2 and the
  saved-world line stay, and `setup_closed` keeps its lead. The recovery test
  now pins the forget-hub reply and the unchanged world-missing instruction.

## Owner-facing lines (os/config/usr/libexec/aresos-desktop)

| Place | Old | New |
| --- | --- | --- |
| SETUP step 3 | `3. On the title screen click AresOS, keep or change the seed, and click Create.` | `3. Making your home… (the first start takes a moment)` |
| SETUP fallback | No separate line | `   If creation fails and the title screen shows, click AresOS, then Create.` |
| forget_hub reply | `The next start makes a new hub (title screen, AresOS button). Type retry.` | `The next start makes a fresh flat home by itself. Type retry.` |

## Guide audit and bindings

- Guide audit: `rg -n -i 'click AresOS|click Create' docs/` found no matches
  (exit 1). Broader searches covering markup between `click` and the button
  names, title screens, seeds and first starts found no obsolete guide
  instruction. `docs/design/HUB.md:69-72` already describes package 48's
  automatic first start and its title-screen fallback; its Create action is
  for New home. The final search below, allowing Markdown markup and line
  breaks, also found no matches (exit 1). **Guide changes: none.**

  ```sh
  rg -n -i -U '\bclick(?:\s|[*`])*AresOS\b|\bclick(?:\s|[*`])*Create\b' docs/
  ```
- Checked the active source-binding tables through
  `checkout_sources.merge(checkout_sources.active_tables(...))`:
  `os/config/usr/libexec/aresos-desktop` and
  `os/tests/test_aresos_desktop.py` both have `bound=False`. No rebind is
  required for these changes.

## Verification

- Full touched module, run once:

  ```sh
  PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p 'test_aresos_desktop.py'
  ```

  Printed `Ran 189 tests in 78.521s` and `FAILED (errors=42)`; exit 1.
  **147 passed, 0 assertion failures, 42 setup errors.** All errors are
  `PermissionError: [Errno 1] Operation not permitted` at Unix socket bind:
  24 in `LoopTest.setUp` through `desktop.Loop.listen`, and 18 in
  `WrapperTest.setUp`. ResourceWarnings for unclosed sockets followed some
  setup errors. The sandbox prevents those integration fixtures from
  starting; no tests were weakened or skipped.
- Explicit rerun of the relevant cases in the same module:

  ```sh
  PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p 'test_aresos_desktop.py' -k FirstStartTest -k MessagesTest -k RecoveryReasonsTest -v
  ```

  Printed `Ran 11 tests in 0.018s` and `OK`; exit 0. All three first-start
  tests, both message tests (including the new four-reason regression),
  and all six recovery-reason tests passed.
- Loaded the supervisor through `SourceFileLoader` without starting it and
  printed its SETUP message: all three steps, the conditional fallback,
  saved-world line and closing hint appeared as intended. Printed
  `Longest SETUP line: 75 characters; window width: 104`; exit 0.
- `git diff --check`: exit 0, no output. Inspected the diff: production
  changes are the three owner-facing lines listed above, with no behavior
  changes; the other edits are tests and these notes.
- Closing `.work/` inventory (Python pathlib scan, threshold 500,000,000
  bytes): printed `.work files over 500 MB:` followed by `none`; exit 0.
  No downloads were made.

## Not verified / handoff

- The full desktop module is **not green** in this sandbox. The lead should
  rerun the full-module command where Unix socket binding is permitted.
- No real Prism sign-in, Minecraft first start, failed home creation or
  keeper window was driven. No screenshots; the text was checked through
  the actual message renderer and its width test. No mod builds/client
  tests or hosted checks were run for this text-only OS package; the brief
  forbids workflow dispatch and changes under mod/.
- No commits or changes to this worktree's git metadata. The lead can review and commit the
  three changed files. No judgment calls, plan gaps or open questions.
