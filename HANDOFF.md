# Handoff

Baton from `linux-aresos`, 2026-11-23. Read after [STATE.md](STATE.md) and overwrite when handing the session on.

## Resume B331 on `pkg/331-release-29` (draft PR #144)

- Steps 1–5 and the late-package slice are reviewed SAFE. The latest slice covers 18c-b, B329, B330 and mod packages 327, 328a and 328. [Branch progress](https://github.com/Ares-Empire/AresOS/blob/pkg/331-release-29/reviews/331-release-29/PROGRESS.md) · [Release brief](https://github.com/Ares-Empire/AresOS/blob/pkg/331-release-29/briefs/331-release-29.md)
- Hosted checks run 45070065335 passed (2,642 tests and the full ways-back model). Historical baseline preflight run 45073317069 passed on the same head, `1ac63562`. Three of the 73 baseline inputs changed in the late slice, so rerun the preflight on the cut before upload and check its receipt with `release29_walk.py check-receipt`.
- Send the cut line to all sessions about a day ahead, around 27 Nov. Confirm which already-merged late packages ride. B334a may merge ahead of B321 and B331 after its review and checks. Keep the bench and Deskflow dispatch modes when reconciling the shared workflow and account for B334a's changes in the cut review. Package 43 rides only if reviewed and merged before the cut.
- B321 gates the cut on four conditions. Get the final reviewed handoff and the OS lead's clean `os/` read, a green Deskflow VM on B321's final head, the reviewed NEVRA and SHA-256 resolved from Fedora stable `updates`, and observed monitor unplug/replug evidence in the VM or the separately owner-approved laptop proof. Recheck all four before uploading a cut with B321. If B321 is still off main and a condition is missing when R29 is otherwise ready, defer it to R30 and keep main's reviewed `aresos1` labwc pin in R29. If B321 merged and a condition then fails, the lead chooses whether to wait or revert and requalify.
- At the cut, renew the mod jar pin from the reproducible build. Settle the late-package rules, resolve, run the cut checks and dry run, rerun the baseline preflight, then review the upload gate. Keep both guardian VM proofs, save and timeout. Only the lead dispatches B331 workflows and opens the publish caps after the cut evidence is reviewed. Both publish caps are still zero.
- T480 permits a private candidate upload before rehearsal. Record the signed digest, rehearse that exact candidate, get the final review, then pin. The owner runs the `CLAUDE.md` line edit because the lead's permission check refuses changes to its own rules files.
- R29's first boot must show Chrome refusing with the placeholder (C6, including zero requests), before putting the synthetic list in place and checking it survives. Use R29's eleven Control checks. Keep the real gate closed until the owner's T298 sitting.
- For R29's known limits, Alt+Tab then Escape can leave the world's pointer locked and its keyboard input missing. Switching away and back restores the keys. The late slice saw it with both frame configurations.
- Ask `mac-capacity` for the API promo route for Fable reviews. It expires 29 Nov at 01:00. The owner renews the repo's rehearsal/release read token before it expires around 7 Dec.

## Open on the board

- **T462:** Keep Alt+F4 first in the update into R29. The guardian in package 25 lets R30 drop it.
- **T492:** Still open. Read the board item when resuming.

After the cut, pick up 23c's brief and package 43's next step from [STATE.md](STATE.md#next-in-order).
