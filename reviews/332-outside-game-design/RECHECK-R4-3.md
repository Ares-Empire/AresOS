# Recheck 3 of HOME-OUTSIDE.md revision 4

I couldn't open the commit itself: I only had a file reader, and `.git` here is a worktree link file. So I checked the three fixed passages as they read now: lines 461-468, 506-511, the `view_alive` row at 402, and Super's route 1 at 1038-1042. I compared them with every mention of `view_focus`, `view_alive`, `view_ping`, `aresos-settings` and `hub_seen`, and with `os/config/usr/libexec/aresos-settings`. Fixes 1 and 3 agree with the rest of the note. Fix 2 leaves one contradiction.

1. **Blocking (fix 2): only the supervisor knows the session's Minecraft style.**
   - **The conflict.** Lines 464-466 say that when the settings file can't be read, or has a format this release doesn't know, the supervisor uses the Minecraft style for that session. But everyone else gets the style from the file:
     - the settings row in section 5 (322);
     - the native home, which "applies the picture and the icons" and watches the file (260, 283);
     - the "to or from `minecraft`" trigger (430).
   - **What they would read.** For such a file, `aresos-settings` hands out its defaults (`:71-76`). From package 12 that means `home = picture`.
   - **What goes wrong.** In that session the world runs, but the native home treats the style as Picture. Its home menu marks Picture, and from 3b2 it also draws icons on the second screen. If he picks Picture, the old and new values are both `picture`, so the pick can look like no change: the world stays on and nothing says why.
   - **What to add.** Say how the session's style reaches the helper and the native home, for example a supervisor packet or a field in `screens`. Say that a style pick in that session always goes to the supervisor. Also say that his first `set_setting` or `aresos-settings set` of any value still replaces the untouched file (`aresos-settings:110-115`). "No setting of his is lost" holds only for the supervisor's own rule.
2. **Non-blocking (fix 2): the no-home boot rule can still write.** Line 492 "sets the style back to Picture" whatever the setting says. Add "only after a clean read that found `minecraft`", so that "a read that failed never leads to a write" (466) also holds on a laptop with no home.
3. **Non-blocking (fix 2): "read cleanly" is undefined.** `aresos-settings`' `chosen` also reports a problem for a single unknown name or value (`:61-67`). The builder must know whether such a file counts as clean or as unreadable:
   - **If clean:** the write drops the stray entry.
   - **If unreadable:** the laptop gets the Minecraft style and a notice at every boot, and the file is never mended.
4. **Non-blocking (fix 2): two nearby passages lag behind.**
   - The section 12 harm row (1362) still says a laptop that has had a home "is set to `minecraft` … at every supervisor start". Read alone, that overwrites his Picture choice. It should match section 6.
   - Package 12's test row (1185) has no case for an unreadable file or a file of another version. The test should show the file unchanged byte for byte, the world running, and the notice shown.
5. **Non-blocking (fix 3): `view_ping` is missing from the interface tables.**
   - In the protocol table, `view_ping` appears only in the text of the `view_alive` row. The row's Message and Direction cells list only `view_alive` from a view.
   - The status-socket rows (426-427) have no supervisor request to ping the view and no helper answer. Package 7 needs both, because `world off` can also come from the command line.
6. **Non-blocking (fix 3): the liveness check needs three more details.**
   - "A silent or hung view counts as absent" (508) holds only if the view answers `view_ping` from its drawing loop, as the keyboard beat does. Row 402 says "at once" but not from where.
   - In the same row, say that the three-second end applies only to the keyboard beat. A missed ping refuses the switch; it does not kill the native home.
   - Package 7's test row (1180) checks only refusals. Add the case this fix exists for: a live native home without the keyboard, where the switch goes through.
7. **Non-blocking (fix 1): `view_focus`'s `surface` field is defined in one place only.** It appears only in Super's route 1 (1039-1040). Neither the protocol table nor the search's close order at 417 ("reports `view_focus` false") names it. Add the field to the `search_view` row, and write "`view_focus` false for `search`" at 417.
8. **Non-blocking (status text): the change log still lists fixed points as open.** Lines 66-78 still list review 3's findings 4 (the keep rule for an unreadable file) and 5 (`view_focus` and `view_alive`) as waiting for the lead. Line 11 doesn't name the three points the lead fixed.

NOT READY
