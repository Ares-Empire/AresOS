# 20, parallel start: how brief 20 runs alongside Mail, 18d and 19b

**Owner's decision, 2026-11-09:** start Chrome now, alongside Mail, instead of after Mail, 18d and 19b ("if chrome
starts now it's done sooner"). This note changes only **where brief 20 starts, in what order it builds, and which
state rules it follows**. Everything else in `briefs/20-chrome.md` stands. Where they differ, this note wins.

## Where it starts

- Branch `pkg/20-chrome` starts from the head of the Mail branch `pkg/19-mail` (`d3babf1f`), not from `main` after 18d.
  Mail's review rounds 19 to 29 rebuilt much of the shared base (`results.py` response bounds, `paging.py`,
  `warnings.py`, `recovery.py`, `space.py`, `storage.py`), and Chrome uses the base as it is there.
- Files the brief says to read "on `main`" are read on this branch. `reviews/18d-base-slim/REPORT.md` doesn't exist yet.
- Don't merge other branches yourself. When Mail, 18d or 19b merges, the lead tells you to merge `main` in.

## Build order

**Now:** everything that doesn't need 18d.
- The extension, the native host and the page script.
- The reader, the classification and word list, the binding and the resume kinds.
- The six adapters and the fixture sites.
- The Chrome adapter on the base's `Adapter` and `Engine`, its definitions and generated artifacts.
- Test groups 1 to 11 and 13.
- The qualification workflow and record.
- Chrome's ask rules go into the **current** settings generator, the same way Mail's are there today.

**After 18d merges:** the slim generator, `user-mcp.json`, and the shared rules in the MCP `instructions` (18d's item 7
pattern). Until then, write each description so that its shared block can be lifted out unchanged. Test group 12 runs
in 18d's precedence harness.

When the "now" part is built, reviewed and green, report to the lead and wait for 18d. Don't build a stand-in for
18d's parts.

## State rules from the start

Mail's review rounds kept finding owner-visible state kept beside the committed record. Chrome's service-side state
follows from the start the rules Mail ended with, and the rules of brief 19b (`briefs/19b-owner-state.md`):
- **R1:** every fact the owner must learn (pending items, warnings, refusals) is computed when read, from committed
  records plus live checks, never only from memory.
- **R2:** before every dispatch to a page, commit enough to warn the owner if the outcome is never recorded: tab, site,
  the bound content and what was approved.
- **R3:** refusals are recomputed on every call; only a possibly-started transaction latches.
- **Round 27's rule:** a check that can produce an owner warning stays open until its result is committed.
- **The warning lifecycle:** check, occurrence with an evidence fingerprint, acknowledgement per occurrence, and the
  action's own resolution, kept separate. Use Mail round 29's `warnings.py` and `paging.py`; don't write a second
  version.
- Responses go through `results.bound_result`.
- Chrome's tests include the storage fault modes of Mail's sweep (single fault, persistent exhaustion, cleanup pairs,
  crash and restart, space restored) for Chrome's own durable writes.

When 19b lands, Chrome moves to its shared read path and projection. Report what that will take.

## Order of merging

Mail first, then whichever of 18d, 19b and 20 is ready. The package that merges later merges `main` in, regenerates
every generated file, reruns every Control workflow twice, and has its reviews cover the combined head.
