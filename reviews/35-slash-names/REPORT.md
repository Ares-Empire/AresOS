# 35: Slash names

**Status: verification in progress.** PR #56 is draft. The final build and two client runs are pending the laptop's owner-game guard. Do not read the earlier-stage green build as verification of the final code.

## Done

- `names/NameRules`: pure HUB.md 4.1–4.4 rules, with the maker/filler/wrapper words and nickname table together. Unit coverage includes all 27 rows of 4.6, the seven additional examples and three weak-name examples after it, validity, reserved commands, app/owner-name clashes, starter priority, cleaning and number fallback. **Worked-list differences: none.** Examples after the table do not provide all their metadata; fixtures supply explicit executable/desktop IDs and record them in the parameterized cases.
- `config/AppDefinition`, `AppsConfig`: schema 4 saves `names`, main first; migrations keep an untouched backup and unknown fields. Missing names are assigned against the actual command tree before exposing commands. Saved names survive helper updates, program renames, removal and return. A real command can displace a saved name; its replacement follows the rules, including reusing an alias of the same app. Atomic owner-name edits explain invalid, reserved, held, unknown and last-name refusals.
- `names/SlashCommands`, `item/AppCommands`, `AresOs`: register real commands only when free, reconcile additions/removals/name edits and resend Minecraft's command list without a rejoin. All launch paths check the singleplayer host and desktop marker. A visit-zero doorway payload reaches the existing launcher in both Live and Build mode; it owns no return teleport. Brigadier has no public removal operation, so one accessor removes only owned nodes from its three indexes.
- `names/OpenPrograms`, `ProgramCommands`: `/open` resolves exact and prefix matches across every listed program and completes names. Ambiguous results and `/apps` have clickable rows. `/apps` shows My apps with saved commands and the category-based group. Clicks identify the exact program by ID, including duplicate display names.
- `config/AppSearch`, `client/AppsScreen`, `zone/GateBuilder`: search includes all saved aliases; the Apps screen reserves room for the main slash name beside the display name; newly planned signs carry the saved main name. Existing sign entities are not rewritten. `NameRules.mainName` is shared with future hub work.
- `mod/README.md`: commands, ownership, matching, recovery and schema 4. `mod/build.gradle`: client limit 20 minutes and package screenshot destination.
- `SlashNamesGameTests`: isolated batch, with an explicit temporary singleplayer profile and test-only GameTestServer host adapter. Covers vanilla commands, membership changes, actual host/guest command packets, name refusals, `/open` and clickable listings.
- `SlashNamesClientGameTest`: appended last, preserving earlier screenshot numbers. Tests real chat completion, a typed `/dc`, fake launcher counts and unchanged position, the chat click handler, `/apps`, `/open`, Apps alias search, Build launches, live command refresh, new/unchanged sign text and normal-world payload rejection. Five screenshots are requested. No real app is launched.

## Verified

All commands ran from this worktree. Every build used `mod/dev/build.sh`, preceded by `free -g`. No force or direct Gradle invocation was used.

- Initial rules build: `All 73 required tests passed :)`, then `162 tests completed, 1 failed, 6 skipped`, `BUILD FAILED in 1m 44s`. The new two-part desktop-ID test incorrectly expected `orgtest`; step 3 takes `org.test` whole and step 2 strips `org.`, so the correct specified answer is `test`. Corrected the expectation with an explanation.
- First persistence build: failed the existing hand-written-entry assertion during schema-3 migration. Fixed migration to preserve schema 3's missing-`mine` semantics, instead of reapplying schema-1/2 defaults.
- Rules/persistence rerun: `mod/dev/build.sh` printed `All 73 required tests passed :)` and `BUILD SUCCESSFUL in 1m 3s`; XML totals: 165 unit cases, 0 failures, 0 errors, 6 existing Windows skips.
- Subsequent compilation attempts found an obsolete `getDayTime()` test call, an unavailable `ChatFormatting.getColor()`, and missing client-context/screenshot imports. These are fixed; sign text is checked through saved data because TextDisplay's getter is private in 26.2. Final compilation is still pending.
- Several later attempts exited 75 with `The owner's Minecraft (Lunar Client, PID ...) is running; try again once it has closed, or pass --force.` Waited in blocking sleeps of several minutes between retries. No guard was bypassed. A guarded retry continues every three minutes.
- Hosted CI at `49e57050` ([job log](https://github.com/Ares-Empire/AresOS/actions/runs/43518209980/job/132205514877)): both clean checkout builds passed all 77 required server tests and their unit suites; printed `BUILD SUCCESSFUL in 1m 4s` and `BUILD SUCCESSFUL in 59s`, then matched the jar hashes. The overall job was cancelled during post-cache cleanup by the later documentation push, after every build/test/reproduction step succeeded. This verifies final-source compilation and server behavior, not the pending local client suite. Retrieved with `~/.local/bin/gh run view --job 132205514877 --log`.
- `git diff --check`: no output, exit 0. `git push -u origin pkg/35-slash-names`: exit 0 through the privacy hook. `~/.local/bin/gh pr create --base main --head pkg/35-slash-names --draft ... --body-file .work/35-pr-body.md`: created https://github.com/Ares-Empire/AresOS/pull/56.

## Not verified

- Final build, final server tests and the full headless client suite twice: pending the laptop guard. No screenshot has yet been captured or inspected for package 35.
- Real Chrome/Discord/Lunar window behavior and the owner's feel for the chosen names require a human. Automated launches use a fake launcher only.

## JUDGMENT-CALL

- Apps outside My apps retain ownership of saved names, as well as retaining the names themselves. Rejected lending those names to another app: that could prevent restoring the remembered commands on return. Changing this later needs an explicit reclaim/conflict policy, with no block-world migration.
- If every candidate is invalid (for example a purely numeric/non-Latin name without usable metadata), use `app2`, then the first free numbered variant. The design does not define a valid first candidate in that case. Rejected unusable commands or refusing to add the app. It can be renamed with one command later; existing saved names otherwise stay stable.
- `/open` additionally accepts an exact stable app ID. Rejected using a display-name prefix in clickable choices, since two identical display names cannot be distinguished that way. This adds a documented lookup form; removing it would require another unambiguous click target.

## PLAN-GAP

- No 4.6 row gives a different answer under the written rules. The extra examples omit their executable/desktop metadata, so their fixtures make those inputs explicit.
- The nickname rule mentions StartupWMClass, but HUB.md 3.8's shell/1.1 entry does not supply it. The pure rule accepts and tests that field; the running mod matches the available name, desktop and program identities. No new wire field was invented.
- The numeric/non-Latin fallback is undefined when no valid first candidate exists; the reversible `app2` choice above covers it.

## Open questions

- None requiring an answer during this run. PR stays draft until final verification and screenshots finish.

## Try this

In an AresOS world, press T, type `/d`, and check completion offers `dc` and `discord`. Run `/dc`, close Discord and check you stand in the same place. Try `/apps` and click Chrome, then `/open` with a program outside My apps. Run `/aresos app name discord chat`, use `/chat` in Live and Build, and find Discord by `chat` in E → Apps…. Build a fresh Discord gate and check its second line; rename again and confirm the standing sign keeps its old text. `/aresos app unname chat` removes the alias once another remains.

## Local artifacts

`find .work -type f -size +500M -print` printed nothing. No large downloads were made. Only small ignored logs/PR text are kept locally; there are no extracted images or duplicate downloads.
