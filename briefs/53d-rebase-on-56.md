# 53d: rebase onto package 56 (PR #117)

`linux-hub`'s package 56 merges right after the R28 cut (2026-11-19) and overlaps five of PR #121's files. Once it is
on main, rebase `pkg/53d-world-search` onto main with these resolutions (from `linux-hub`'s trial merge):
- `mod/build.gradle`: keep both sets of `systemProperty` lines.
- `aresos.client.mixins.json`: the list ends `"SavingIndicatorMixin", "HotbarPointerMixin", "SearchCrosshairMixin"`.
- gametest `fabric.mod.json`: both `FreePointerClientGameTest` and `WorldSearchClientGameTest` (ours stays last).
- `ShellFocusClient.java`: keep both overrides, 56's `status()` (clears `appInFront` and `HomePointer` when the
  helper drops) and 53d's `search()`.
- `AresOsClient.launch`: one `launch(id, visit, worldScreen, opened)`. The pointer path (`launchFromPointer`) passes
  `worldScreen=false`; the search path passes `opened=null`.

Then check, as a client test where possible, otherwise as a Known limit: with a small app in front (56 makes the
world ignore the mouse then), `shell_search` opens the bar, and Escape closing it does not turn the view. Rerun
`mod/dev/build.sh` and the client suite twice.
