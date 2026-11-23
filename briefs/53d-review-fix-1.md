# 53d review fix 1

Fixes for `reviews/53d-world-search/REVIEW-1.md` (fresh Codex `gpt-6.2-sol` `high` review of PR #121, CHANGES-NEEDED).
**Builder:** a Claude Opus agent, on the same branch. Read AGENTS.md, `briefs/53d-world-search.md`,
`reviews/53d-world-search/REPORT.md` and REVIEW-1 first. The rebase onto package 56 (`briefs/53d-rebase-on-56.md`) is a
later, separate step: do not do it here.

## Fix

1. **The bar opens only once the world really has the keyboard** (REVIEW-1 blocking 1), so typing and Enter can never
   reach the app that had it.
   - **The helper** sends `shell_search` only after the compositor reports the world's window **activated**
     (`follow_windows` sees it), not when it writes the request. If that does not happen within 1 s, it sends nothing
     and logs it.
   - **The mod** opens the bar only while the game window has input focus (`client.isWindowActive()` or the
     equivalent). If the event arrives before focus, it waits up to 500 ms for focus, then opens or drops.
   - **Tests:** the helper does not emit while another window is still reported active, and emits once the world's
     activation arrives; the mod does not open the bar without window focus. Record in the report that typing in the
     instant between focus arriving and the bar opening is a Known limit, and that the laptop trial checks immediate
     typing and Enter from a terminal.
2. **No draft is ever discarded** (blocking 2). Treat every editing screen as typing, whatever widget has focus:
   - `BookSignScreen`, `BookEditScreen`, `SignEditScreen` (and the hanging-sign variant), `AnvilScreen`, the command
     block screens, and `ChatScreen`;
   - plus any screen with a focused text box.
   
   Client regression test: write pages, Sign, type a title, Tab to "Sign and Close", fire `shell_search`, and check
   the signing screen and its draft are still there.
3. **Current readiness only** (should-fix 1): the helper acts only when the latest heartbeat said ready, and it
   uncovers only on the current compositor activation, never on a stale last-active handle.
4. **A Wayland write never ends the helper** (should-fix 2). An activation or minimize write that raises
   `BlockingIOError` is queued with partial-write tracking, or retried on the next writable event. A disconnected
   socket takes the existing compositor-loss path. Test with a mocked write.
5. **Super works again after a quick reload of the same world** (should-fix 3): a `ready: false` heartbeat updates
   the writer's reported readiness, so the next ready sends `world_ready` again. Test ready → unready → same save.
6. **The best hit stays visible** (should-fix 4): the framed best hit and its "Enter" label stay on screen while the
   rest of the list scrolls (pin it at the top of the list).

## Verify

- `mod/dev/build.sh`, then `mod/dev/client-test.sh` **twice**. It takes the client-test lock, and on exit 75 wait and
  retry, never `--force`. Commit before a suite run; afterwards restore only the rewritten tracked screenshots, and
  delete untracked ones written for other packages.
- The touched helper modules pass, each run by name, in-process (never the whole `os/tests`, never
  `test_owner_update`).
- Add a "Review fix round 1" section to REPORT.md.
- After the last push, start one hosted run (`gh workflow run "OS image" --ref pkg/53d-world-search -f
  checks_only=true`) and put its ID in the report.
- Push, then stop: never wait for or watch CI. Do not merge.
