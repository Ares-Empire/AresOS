Codex gpt-6-astra, 2026-11-18. Reviewed `a896fd08`, with code head `659e7164`. I read AGENTS.md, the full brief, REPORT, KNOWN-LIMITS, HARNESS-MAP, PROGRESS’s lead decisions, relevant design text, and the implementation/test diff.

I ran:

- REPORT’s eight Python modules: **150 tests; 140 passed, 10 socket-related `EPERM` errors**.
- Additional renderer, address, budget and deadline modules: **123 tests; 113 passed, 10 failures/errors caused by restricted socket operations**.
- The Node suite, then individual modules after the suite stalled: **433 completed tests; 422 passed, 11 `EPERM` failures**. `page` and `native-unicode` did not complete; a separate native-wire probe passed the actual Python strict decoder.
- Generator, instruction-size, merge, inventory, targeted probes and mutations below.

Generated artifacts match. Chrome instructions are **4,093/4,096 characters**. Scratch `git merge-tree` merges cleanly with today’s main, `7417c19a`. #98 is already incorporated; its qualification implementation remains unchanged. I found no conflict with #106’s deferred 28a/28b requirements.

The retained final CI logs contain all **36 new mandatory names exactly once per core execution**, across both attempts of both workflows. I found no duplicated verdict credit. The recorded latency comparison is 40.9 ms versus 69.8 ms, below its 126.8 ms ceiling. Browser evidence was inspected, not rerun locally.

1. **SHOULD-FIX — File selection can change without changing the state token.**  
   [reader.js:498](../../control/chrome/extension/reader.js#L498) hashes only `files.length`, although [reader.js:408](../../control/chrome/extension/reader.js#L408) exposes filenames.

   Replacing `first.txt` with `second.txt` produced different outlines and identical reader state. Consequently, `until` can miss the new filename. A continuation whose earlier text is unchanged can also accept the changed suffix: my paging probe did exactly that. Add same-count file-replacement coverage for the token, waiting and cursor invalidation. This limitation is missing from KNOWN-LIMITS.

2. **SHOULD-FIX — `full` does not read all select options.**  
   [adapter.py:524](../../control/aresos_control/chrome/adapter.py#L524), [view.py:505](../../control/aresos_control/chrome/view.py#L505).

   Using F4 through the actual adapter with its test bridge, both page-wide `full` and form-reference `full` returned **50 Country options, `… 150 more`, and `cursor: null`**. Neither requested the remaining options. Reading the Country field itself returned all 200.

   This contradicts the brief’s “no fold and no cut” contract. The existing options test exercises the field-reference path only. Add page/subtree-full coverage and retrieve their remaining options within the deadline.

3. **SHOULD-FIX — Ordinary option lines bypass the 200-character cut.**  
   [view.py:495](../../control/aresos_control/chrome/view.py#L495).

   A two-option select with an unselected 10,000-character label produces a **10,011-character option line**, with no cut marker, during a normal folded read. The envelope still bounds the response, but the supposedly compact outline now requires pagination for this label.

   Apply the normal quoted-text budget and provide a reference-based route to the complete label. Existing hostile-option cases do not prove this cap.

4. **NIT — The brief’s fixed sentences are not all exact.**  
   [adapter.py:64](../../control/aresos_control/chrome/adapter.py#L64) retains “This form holds unread typed text; send it yourself…” rather than the specified “this form holds a field the tool may not read…”.  
   [view.py:900](../../control/aresos_control/chrome/view.py#L900) returns “The page changed; read again without the cursor.” rather than “page changed, read again without the cursor”.

   The `not_read` sentence is exact. Document the inherited wording as an explicit specification exception, rather than claiming literal compliance.

5. **NIT — The native-size limit is described incorrectly.**  
   [KNOWN-LIMITS.md:293](../../reviews/28-chrome-read/KNOWN-LIMITS.md#L293) describes a whole-reply 1 MiB bound. Replies are chunked above 512 KiB, and assembled responses allow **32 MiB**: [background.js:365](../../control/chrome/extension/background.js#L365), [bridge.py:171](../../control/aresos_control/chrome/bridge.py#L171).

   Distinguish the per-message limit from the assembled-response limit. The compact capacity fixture still does not prove every verbose 20,000-node page.

6. **NIT — The reported AST comparison names nonexistent functions.**  
   [REPORT.md:112](../../reviews/28-chrome-read/REPORT.md#L112) claims eleven named functions were identical. `prepare_read_typed_fields` and `read_typed_fields` are dispatched branches, not functions in this module. The nine existing named functions compare identically; describe the two branches separately.

The accepted probabilistic references, late-root withholding, editable-area disclosure and address heuristics remain consistent with the documented decisions. Duplicate-label human descriptions are explicitly assigned to #106. Findings 1–3 are additional acceptance gaps, not established accepted limits.

Mutations used scratch source copies or in-memory changes; none modified tracked code.

| Mutation | Result |
|---|---|
| Remove cross-tab reference check | **Killed:** 5 failures |
| Reset reference counter on reconnect | **Killed:** 1 failure |
| Ignore reader-instance identity | **Killed:** 1 failure |
| Omit closed-tab reference-index cleanup | **Killed:** 3 failures |
| Ignore cursor state token | **Killed:** 1 failure |
| Count characters instead of JSON wire bytes | **Killed:** 9 failures |
| Remove native Unicode repair | **Killed:** strict decoder rejected 6 outputs; baseline accepted all 26 |
| Remove fresh-side repair at each of seven comparison sites | **All killed:** 30/30/5/3/2/1/1 failures |
| Bypass expected-state comparison | **Killed:** 5 failures |
| Bypass final action-binding comparison | **Killed:** 15 failures |
| Accept first ambiguous repaired option | **Killed:** 1 failure |
| Restore direct `form.hidden` lookup | **Killed:** 1 failure |
| Replace select-state digest with a constant | **Survived:** all 11 outline tests passed |

The surviving mutation exposes missing selected-option state coverage alongside finding 1. Final `git status` shows no tracked changes; the two pre-existing untracked reviews remain untouched. Nothing was committed, pushed or dispatched.

CHANGES-NEEDED