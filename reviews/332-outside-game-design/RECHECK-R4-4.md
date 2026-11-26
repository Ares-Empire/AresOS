# Recheck 4 of HOME-OUTSIDE.md revision 4

I couldn't open the commit: I only had a file reader. So I checked the passages as they read now: the keep rule (463-475), the no-home boot rule (498-501), the harm row (1370) and the brief list (1462-1470). I compared them with every mention of `aresos-settings`, `minecraft`, "read cleanly", `view_ping` and `view_focus`, and with `os/config/usr/libexec/aresos-settings`.

**What holds:**
- **Check 1:** when the file can't be read, `aresos-settings` reports `minecraft` to every reader and nobody writes the file. His pick replaces it. "Read cleanly" is defined, including the case of one unknown entry.
- **Check 2:** the boot rule writes only after a clean read that found `minecraft`, and the harm row matches section 6.
- **Check 3:** packages 6, 7 and 12 are listed. Package 7's lines agree with row 404 and the switch check (514-517).
- **Check 4:** every `view_ping` and `view_focus` mention agrees.

One gap in check 1 brings back the blocking failure from recheck 3 by another route.

1. **Blocking: if he changes any other setting, `minecraft` is lost for the rest of the session.**
   - **The rule.** Lines 471-472 say his first pick of "a style or a setting" replaces the file, as any `aresos-settings set` does today. Today `set_value` keeps only the values `chosen` could read, and from an unreadable file it can read none (`:50-59`, `:110-115`). So after `set look C` the file holds only `look`.
   - **The result.** The file now reads cleanly and has no `home`, so from package 12 on every reader gets the default, `picture`. The native home watches the file (285) and switches to Picture while the world runs.
   - **The supervisor.** Nobody set `home`, so one of two things happens. Either no request reaches the supervisor, and this is recheck 3's failure again: Picture is marked, and if he then picks Picture nothing happens and nothing says why. Or row 432 counts the changed value as a change of `home`, and a change of look closes his world.
   - **The conflict.** Either way it contradicts "every part of the session agrees on the style" (470). It lasts until the next supervisor start writes `minecraft` back.
   - **Fix.** When `set` replaces a file it couldn't read cleanly, it also writes `home = minecraft`, unless the setting being changed is `home`. On a laptop with no home, the next boot then sets Picture, as 499-500 already say.
2. **Non-blocking: "read cleanly" leaves out a missing file.**
   - **The gap.** Neither "parses in a format this release knows" (466) nor "can't be parsed" (468) covers a file that doesn't exist. `chosen` reports no problem for a missing file (`:48-49`).
   - **Why it matters.** If a missing file counts as a failed read, every fresh AresOS gets `minecraft`. If it counts as neither, the rule never writes on a laptop that has had a home but has no file. That is the very harm the rule exists to prevent.
   - **What to add.** A missing file is a clean read with no values. Any problem with the whole file makes the read fail: the file can't be opened, is over 64 KiB, isn't JSON, or isn't a version 1 object (`:50-59`). A problem with a single entry still counts as clean (`:61-67`). Package 12's test should also cover a laptop that has had a home and has no settings file.
3. **Non-blocking: after a failed read on a laptop with no home, the boot doesn't show "the picture home" (499).**
   - **What it shows.** Every reader gets `minecraft`, so the native home shows the Minecraft style with the world closed:
     - the picture and the bar;
     - no icons and no starter pins, because the helper makes its own document only in a normal style (360-362);
     - "Start the Minecraft world" as the first row (954, 1038-1039).
   - **What to add.** Say this at 499, and say which OFF the supervisor is in, since OFF (`off`) means "a normal style" (824, 838).
   - **The harm row.** "An unreadable file is never written" (1370) should say "never written by this rule", because his own pick replaces it (471).
4. **Non-blocking: two slips in the brief list.**
   - Package 6 (1464): the search's close order is in section 5 (418-419), not section 4.
   - Package 12 (1470): "the Minecraft style runs" holds only on a laptop that has had a home. On a fresh one the boot starts no world (498-501). Say which laptop each test case uses.

NOT READY
