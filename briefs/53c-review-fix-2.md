# 53c review fix 2: the laptop home says when it has the keyboard

Fix for `reviews/53c-laptop-home/REVIEW-2.md` finding 1 (the targeted recheck of fix 1, Codex `gpt-6.2-sol` `high`).
**Builder:** Codex `gpt-6.2-sol` `xhigh`, on the same branch. Read AGENTS.md, `briefs/53c-laptop-home.md`,
`briefs/53c-review-fix-1.md`, REVIEW-1 and REVIEW-2 first.

## Why the timing rule fails

Fix 1 decides by time: an app deactivated with no active toplevel is cleared after the 500 ms handoff. But the helper
cannot see the laptop home's layer surface, so "deactivated, nothing active" means either "the owner clicked the
laptop home" or "the app is closing". Time cannot tell them apart: a background close within 500 ms of a click on the
home still pulls the keyboard to the world, and a genuine close that arrives after 500 ms no longer returns it.

## The rule (the lead's design call)

Decide by **who has the keyboard**, not by time.

1. **The view reports its keyboard focus.** A new 1.2 view op, `view_focus` (`{"op": "view_focus", "focused":
   true|false}`), offered with the `views` capability. The window program sends `true` when its surface gets the
   keyboard (layer surface or fallback window) and `false` when it loses it, and sends its current state again after
   each hello. Only a view may send it; the desktop gets `invalid_state`. Add example messages under
   `mod/src/test/resources/shell-1.2/` and a line in `docs/design/LAPTOP-HOME.md` section 5.
2. **The helper clears the foreground record** when a view reports `focused: true`, or when another toplevel becomes
   active. Nothing else clears it: **remove fix 1's 500 ms expiry**, so a genuine close returns focus to the world
   however late its notification arrives, as before fix 1. Keep the short handoff only where it existed before fix 1.
3. **An app's last window closing returns to the world** as today, unless a view has reported `focused: true` since
   that app was deactivated, or another toplevel is active, or section 5's screen rule (53a, D) holds. A view that
   disconnects counts as `focused: false`.

## Tests

- A foreground editor closes: the world gets the focus back, also when the close arrives 2 s after deactivation.
- The owner clicks the laptop home (`view_focus true`), then a background editor closes 100 ms and 60 s later: the
  focus stays on the home, no `shell_focus`, no activation.
- `view_focus true`, then `false` (the owner clicked elsewhere), then the editor closes: today's return.
- The view disconnects while it holds the keyboard, then the editor closes: today's return.
- The desktop sending `view_focus` gets `invalid_state`; a malformed one is `malformed`.
- The window program sends `view_focus` on its surface's real focus changes in the headless WebKit test (layer and
  fallback), and again after a reconnect.

## Verify

Run the touched test modules by name (never the whole `os/tests`, never `test_owner_update`). Update REPORT.md (what
changed since review 2). After your last push start one hosted run (`gh workflow run "OS image" --ref
pkg/53c-laptop-home -f checks_only=true`) and put its ID in the report. Push, then stop: never wait for or watch CI.
Do not merge.
