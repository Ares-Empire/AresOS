# 53c review fix 3: main's focus logic, gated by the laptop home's keyboard

Fix for `reviews/53c-laptop-home/REVIEW-3.md` (the recheck of fix 2, Codex `gpt-6.2-sol` `high`: two focus
regressions). **Builder:** Codex `gpt-6.2-astra` `xhigh`. Two fix rounds on this focus logic failed review, each
finding edge cases one level deeper, so the builder changes (the handoff's rule; Claude is tight until Thu 00:00).
Read AGENTS.md, `briefs/53c-laptop-home.md`, `briefs/53c-review-fix-1.md`, `briefs/53c-review-fix-2.md` and
REVIEW-1 to REVIEW-3 first.

## Why the last two rounds failed

Fix 1 (the lead's brief) changed the helper's foreground bookkeeping: clearing the foreground record when focus
leaves an app, with a timed handoff. Fix 2 replaced the timing with `view_focus` but kept rewiring the same state
machine. Each change broke one of the event orderings the existing logic handled (deactivation, the compositor's
next-window activation and the close arriving in one, two or three reads). The bookkeeping was not the problem.

## The rule (the lead's design call)

1. **Restore the helper's focus bookkeeping exactly as on `origin/main`**: the foreground record, the handoff, the
   discovered-app close path and `return_to_desktop`'s callers, byte for byte where possible. Undo fix 1's and fix
   2's changes to them. Main's own focus tests must pass unchanged.
2. **Keep `view_focus`** as fix 2 built it (the op, the window program's reports, a disconnect counting as
   `false`, `invalid_state` from the desktop, the example files and section 5's line).
3. **One gate, at the point of return.** Where the helper would return to the world because an app's last window
   closed (every caller of `return_to_desktop` for `app_closed`, the discovered-app path included), it does not
   return (no activation, no `shell_focus`) **while any connected view's latest `view_focus` is `true`**. Otherwise
   it returns exactly as main does. Nothing else changes. 53a's screen rule (section 5, D) stays as it is.
4. When the gate holds a return back, log one debug line. The foreground record then follows main's logic as if
   the return had happened (no stale record keeps a later return pending).

## Tests

- REVIEW-3's two sequences, and the same close with deactivation, next-window activation and close in one, two and
  three reads, for a 1.0, a 1.1 and a 1.2 desktop with no view: the world gets the focus back, as on main.
- The same sequences after `view_focus false` and after a view disconnect: as on main.
- `view_focus true`, then a background editor closes 100 ms and 60 s later: no return, the home keeps the keyboard.
- `view_focus true`, then the foreground editor closes: no return (the owner is on the home).
- Every existing focus and window test module on main passes unchanged (name them in the report).

## Verify

Run the touched test modules by name, plus `test_aresos_shell_windows.py` and the other existing focus modules
(never the whole `os/tests`, never `test_owner_update`). Show `git diff origin/main -- os/config/usr/libexec/aresos-shell`
in the report's summary: only 53c's intended helper changes may remain (the `aresos.laptop-home` exclusions, a
view's `open_app` not cancelling returns, `view_focus` and the gate). After your last push start one hosted run
(`gh workflow run "OS image" --ref pkg/53c-laptop-home -f checks_only=true`) and put its ID in the report. Push,
then stop: never wait for or watch CI. Do not merge.
