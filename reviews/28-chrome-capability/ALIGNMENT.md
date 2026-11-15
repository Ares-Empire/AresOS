# Briefs 28, 28a, 28b and section 6 against merged PR #27

Checked on 2026-11-15 against `main` after PR #27 merged (`09cedc84`, final head `d25ccbd3`), with
`docs/control/TOOLS-HANDOFF.md`, "Chrome merged". The briefs were written against `8b7e799c`. Every backticked
name, path and function in the three briefs and section 6 was looked up in main's tree; the ones below changed or
were added. The design itself is unchanged; the open points are listed at the end for the lead.

## What changed on main since `8b7e799c`, and where it went

| Fact on main | Where |
|---|---|
| 30 Chrome tools, not 29: the asking read is two tools, `chrome_prepare_read_typed_fields` (change, input `tab`) and `chrome_read_typed_fields` (read, input: the approval) | 28 (counts, item 5, reading list), 28a (goal line), section 6 ("Actions", efficiency table) |
| The latency harness and gate exist: `control/chrome/ci/latency-*.{sh,mjs,py}`, `latency-targets.json` (ceilings in ms, median / p95: read 35/60, navigate 100/150, click and fill 650/750, asking click 60/100, approval to done 700/850; 60 samples, the old runtime 20) | 28 ("Latency": the "if they aren't" branch dropped), 28 and 28a acceptance rows, section 6 latency bullet |
| The hold: guard window 500 ms (`HOLD_MS`, `holdMs`), the wait after each input 525 ms (`holdMs+25` in `collectSteps`), unchanged | 28 and 28a "What must not change", 28a "Why 20 steps" |
| Claude Code 2.1.319 passes only 4,096 characters of a server's instructions; `test_questions.py` checks every app; Chrome's are 4,052 on main | 28 ("What must not change": 28 adds none), 28a item 7, 28b item 8, section 6 "What every server pays once" |
| `reload_taken_tab` is now `discard_unsaved`, and it also covers navigate (every direction and an address) and `close_tab` on any Claude tab; the report names fields by label, marks whose typing it is, and counts playing media and uninspected frames | 28a item 6 (`chrome_take`), section 6 ("Until brief 28b merges") |
| Brief 20's reload check (`requireDiscard`, `reloadState`, the guard's `typedBy`): in a document the reader didn't watch, every text field counts; in a watched one, a field that differs from its default or got typing since the load | 28a item 6, 28b item 4a and reading list, section 6 ("Which tabs Claude works in") |
| `chrome_tabs` rows carry `audible` and `muted` | 28a item 6 (`sound` is `audible`), section 6 ("His open tabs") |
| The details page asks his password in a polkit dialog for "Don't ask again" and read-only off | section 6 ("Don't ask again") |
| The KNOWN-LIMITS sentence on a tab taken from another window, word for word | 28 ("Report", "Known limits"), section 6 "Known limits"; 28b item 4b says its own group answers it |
| Follow-ups from #27's final reviews: Hardening (`embedderName`) | 28, new item 8 |
| Follow-ups: Retry advice (`requireTab`'s late-reader retry), `control_status`'s `installs` rows | 28b, new item 10 |
| A full `control-chrome.yml` run is about 40 to 60 minutes in 28 jobs (runs 43641834739, 43641839672), not three to four hours | 28 and 28a stop rules |

## Open for the lead (not decided here)

1. **The asking read's prepare tool has no place in the new list.** 28a keeps `chrome_read_typed_fields` "with its
   name, input and behaviour unchanged" as the eighteenth tool, but its input on main is the approval that
   `chrome_prepare_read_typed_fields` returns. 28a's removal list (item 8, step 3) doesn't name the prepare tool,
   so as written it stays and the list has 19 tools; the 18-tool size budgets don't count it. 28b adds `seen` to
   `chrome_read_typed_fields`, which on main takes no `tab`.
2. **`discard_unsaved` has no home in 28a's tools.** On main, navigate (all directions and an address), `close_tab`
   and a taken tab's first input report unsaved work and need `discard_unsaved: true` to go on. 28a's `chrome_go`
   and `chrome_close` have no such input, and 28a item 7's list of instruction rules doesn't carry main's discard
   rule (ask him before discarding his typing, playing media or uninspected frames). 28b assumes the flag stays for
   Claude's tabs.
3. **4,096 characters.** Main's Chrome instructions use 4,052; 28a's rule list and 28b's 920-character block won't
   fit without taking text out of the instructions or out of them into descriptions.
4. **A `muted` mark.** The new `chrome_tabs` line shows `sound` (Chrome's `audible`, set also while muted) but not
   `muted`, which main's rows now carry.
5. **28b's "known clean" rule versus main's check.** Main counts every text field in a document the reader didn't
   watch from its start; 28b calls an unused tab with an untouched text field known clean. It rests on the "used"
   mark; worth a line in 28b's security review.
6. **Inside 28b, from the lead's 2026-11-14 change (not from #27):** item 8's instruction text still says "pass
   reload only when he agrees", and "the tool list stays at eighteen", while item 4 replaced `reload` by the asking
   tool `chrome_take_reload`.
