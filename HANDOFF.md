# Handoff

Baton from `linux-aresos`, 2026-11-26. Read after [STATE.md](STATE.md) and overwrite when handing the session on.

## Resumed (the owner via mac-capacity, 2026-11-26)

- **Budget:** Claude gets about 70% of the week for all three AresOS leads, starting slowly: one agent per lead at a time, fresh agents with short handoffs, about 2–3% of the week per day for this lead until mac-capacity says more. Ask mac-capacity before any Fable agent. Codex is plentiful (raw `codex exec`).
- **R29 with Deskflow comes first.** `deskflow-1.27.0-1.fc44` is in F44 testing and moves to stable on its own around Sat 28 Nov (Bodhi FEDORA-2026-614dafa1ba). Then linux-desktop runs B321's stable `updates` re-resolve and dispatch 16 and merges, and the lead names the cut. The owner also wants B333 (PR150, open apps and bring back) and T528 (edge look can't look back down) in R29 if they are SAFE and merged before the cut (linux-hub). Renew the jar pin at the cut. If Fedora is late, R29 ships without B321 and R30 follows.
- **Cut line sent** to linux-desktop and linux-hub on 2026-11-26: what rides, their handoffs, os/ reads first, the jar pin from main's Mod run.
- **B321's os/:** clean through `111ea084`. Codex read 2 covered `52c99893`. The lead read the clipboard fix 2 delta after it (separate lookup connection, 250 ms timeout, new portal pin; a failed lookup still refuses). Any os/ change after `bc4c1034` comes back to the lead.
- **T527 closed** (check on `docs/t527-prism-check`): keep the rehearsal. The walk saves explain, desktop.log, the user journal and the Prism log before stopping on RECOVERY (any reason but quit). There is no automatic retry; the lead decides any rerun.
- **T547 closed:** user ares already has the remote-control settings. A per-user line for the install guide follows after R29.
- **Running:** B331 step 6b (Codex `gpt-6.2-sol` xhigh, log `../AresOS-331-step6b.log`): merge main (B334a/b, Chrome 28/28a), classify Chrome 28/28a, C6's refusal set with `take`, the guest's static hostname, the T527 diagnostics. Next: a fresh Codex Astra review, then commit allowances for one same-head check and one baseline preflight and dispatch them in that order.
- **The owner's own steps, still open:** his T497 commands. One copies aresync's global-CLAUDE.md to ~/.claude/CLAUDE.md (T548). The other adds the T480 line in ~/AresOS-t480/CLAUDE.md, a prepared branch `docs/t480-owner-decides`, which the lead then commits and merges. Also the PUBLIC_TERMS secret for aresync's public-terms check.

## Resume B331 on `pkg/331-release-29` (draft PR #144)

- Steps 1–5 and the late-package slice are reviewed SAFE. The latest slice covers 18c-b, B329, B330 and mod packages 327, 328a and 328. [Branch progress](https://github.com/Ares-Empire/AresOS/blob/pkg/331-release-29/reviews/331-release-29/PROGRESS.md) · [Release brief](https://github.com/Ares-Empire/AresOS/blob/pkg/331-release-29/briefs/331-release-29.md)
- Hosted checks run 45070065335 passed (2,642 tests and the full ways-back model). Historical baseline preflight run 45073317069 passed on the same head, `1ac63562`. Three of the 73 baseline inputs changed in the late slice, so rerun the preflight on the cut before upload and check its receipt with `release29_walk.py check-receipt`.
- The existing checks (2 of 2) and baseline (1 of 1) allowances are spent. The lead gets reviewed allowances for the cut reruns before dispatching them.
- Send the cut line to all sessions about a day ahead, around 27 Nov. Confirm which already-merged late packages ride. B334a may merge ahead of B321 and B331 after its review and checks. Keep the bench and Deskflow dispatch modes when reconciling the shared workflow and account for B334a's changes in the cut review. Package 43 rides only if reviewed and merged before the cut.
- B321 gates the cut on four conditions. Get the final reviewed handoff and the OS lead's clean `os/` read, a green Deskflow VM on B321's final head, the reviewed NEVRA and SHA-256 resolved from Fedora stable `updates`, and observed monitor unplug/replug evidence in the VM or the separately owner-approved laptop proof. Recheck all four before uploading a cut with B321. If B321 is still off main and a condition is missing when R29 is otherwise ready, defer it to R30 and keep main's reviewed `aresos1` labwc pin in R29. If B321 merged and a condition then fails, the lead chooses whether to wait or revert and requalify.
- At the cut, renew the mod jar pin from the reproducible build. Settle the late-package rules, resolve, run the cut checks and dry run, rerun the baseline preflight, then review the upload gate. Keep both guardian VM proofs, save and timeout.
- Only the lead dispatches B331 workflows. Both publish caps are zero. After fresh review of the passing cut evidence, the lead opens both caps for one private T480 upload on the reviewed head. Close both caps after dispatch.
- Record the signed digest and prepare the exact candidate tools and bound guides. Pass hosted checks, the full model and native preflight on that head.
- The lead then dispatches the qualifying rehearsal under its reviewed allowance. Rehearse that exact signed digest, get final review, then pin.
- The owner runs the `CLAUDE.md` line edit because the lead's permission check refuses changes to its own rules files.
- R29's first boot must show Chrome refusing with the placeholder (C6, including zero requests), before putting the synthetic list in place and checking it survives. Use R29's eleven Control checks. Keep the real gate closed until the owner's T298 sitting.
- For R29's known limits, Alt+Tab then Escape can leave the world's pointer locked and its keyboard input missing. Switching away and back restores the keys. The late slice saw it with both frame configurations.
- Ask `mac-capacity` for the API promo route for Fable reviews. It expires 29 Nov at 01:00. The owner renews the repo's rehearsal/release read token before it expires around 7 Dec.

## Open on the board

- **T462.** Check if the world is open on every route out of R28, including the first update, forward and failed-update recovery.
  - If it is open, focus Minecraft and press Alt+F4 or Alt+Fn+F4. Wait for “Minecraft was closed. Nothing is wrong.” Go to Help before restarting if the message is missing.
  - The guardian in package 25 lets R30 drop the manual gate.
- Where the shipped tools require foot, open the Terminal app before `at check` and keep it open through PASS.
  - This covers startup on R28, the first R29 confirmation and checks after `previous` and `forward`.
- **T492:** Still open. Read the board item when resuming.

After the cut, pick up 23c's brief and package 43's next step from [STATE.md](STATE.md#next-in-order).
