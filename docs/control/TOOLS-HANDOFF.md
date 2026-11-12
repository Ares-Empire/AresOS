# Control-layer tools: handoff to the AresOS-side session

Written 2026-11-12 by `mac-aresos-control` (the Mac lead) for a fresh session on AresOS that takes over the tools,
for example `linux-tools` with Fable as orchestrator. On AresOS the tools can be tried live, which they can't on the
Mac.

## Read first

1. `docs/control/PLAN.md`: decisions 23 to 25 and the dated entries from 2026-11-11 (decision 24 clarified, and the
   owner's five answers, including the change to decision 25).
2. `docs/design/CONTROL.md` sections 6 (Chrome) and 7 (Claude Code setup).
3. `docs/REVIEW.md`, "Tools for Claude": the review process for every tool.
4. The packages' own reports, listed below.

## Where the packages stand

| Package | Branch, PR | State | Next |
|---|---|---|---|
| Mail (19) | `pkg/19-mail`, #9 to `main` | Reviewed through round 29; waits on 19b. | Merge after 19b. |
| 19b, owner-visible state | `pkg/19b-owner-state`, #26 to `pkg/19-mail` | Stops at stage 2 (owner, 2026-11-11). Its code is restored to the stage-2 head, which all three reviewers called SAFE and CI passed twice. The exhaustive proof becomes an optional check. | One package review and one security review with the new bar, then merge #26, then #9. |
| 18d, slim base | `pkg/18d-base-slim`, #25 | Ready: both reviews SAFE, CI green twice. | After Mail: merge `main` in, regenerate, CI twice, a fresh re-review, merge. Then board #136. |
| Chrome (20) | `pkg/20-chrome`, #27 (draft) | Fix round integrated; head `0ae4ac41` green twice. A short re-check with the new bar is running. | Known limits into section 6; after Mail and 18d, merge `main` in, run test group 12 in 18d's harness, merge. |
| 18c, CI image test | not written | Board #137 and #150. | See "New work". |

`reviews/20-chrome/PAUSE.md`, `reviews/20-chrome/REPORT.md`, `reviews/19b-owner-state/PAUSE.md` and
`reviews/19b-owner-state/REPORT.md` on those branches hold the details.

The Mac keeps the two Claude leads (19b and Chrome) and their Codex runs until Mail, 18d and Chrome have merged;
`mac-aresos-control` merges them. After that, everything here belongs to the AresOS-side session.

## Decisions to write into `CONTROL.md` section 6

These were taken while brief 20 was built and are in its reports, not yet in the design:

- **Network.** The tool service may open outgoing connections (`AF_UNIX AF_INET AF_INET6`; Mail's IMAP and SMTP and
  Chrome's daily record fetch need it). The rest of its sandbox stays. A test pins the unit's sandbox lines.
- **Popups** opened by a Claude tab follow the reload-on-take rule while their opener is in Claude's group. The
  opener's toolbar badge marks them, the action popup lists each one with its own Stop, and no window of ours opens.
- **Dialogs.**
  - Dialogs opened while Claude controls the tab are answered with the hold armed through the debugger.
  - A dialog that was already open when Claude took the tab can't be reached in Chrome 157. Claude asks him to
    answer it himself, and the tool never hangs.
  - Dialogs opened through a function borrowed from another frame ask, saying the next step isn't held.
- **A file he picked himself** is bound by the SHA-256 of its bytes, and the question shows its name, size and hash.
- **Editors in `about:blank` and `srcdoc` frames** are covered by the guard and send after approval.
- **Paging snapshots** of downloads, history and bookmarks expire after 5 minutes without a page request, or 30 minutes
  after they were made.
- **Known limits** from the Chrome re-check: `reviews/20-chrome/KNOWN-LIMITS.md` on the Chrome branch. The re-check
  that writes it is still running; it must exist before the handover.
- **The owner's change to decision 25:** Claude works in his open tabs (below).

## New work (Fable)

1. **Chrome capability brief.** The owner wants "a better tool for AresOS that's more efficient with readings,
   navigation, free tab navigation etc." and not a copy of Claude in Chrome. Candidates:
   - compact, structured reading of a page with stable element references and no screenshots;
   - reading several tabs in one call, find-in-page, and paging through long pages;
   - navigation: open, back, forward, wait until loaded, follow a link by reference;
   - moving freely between tabs, and opening and closing them;
   - batched steps, such as filling a form and sending it with one question;
   - **his own tabs** (decision 25 as changed): Claude sees their titles and addresses and takes the tab his request
     clearly needs, never an unrelated one, and shows which of his tabs it took. The take rules and the questions for
     sends, deletes and payments stay. His words: "Although the permission interpretation on this needs to be good."

   The brief updates section 6 in the same change and is reviewed by the process in `docs/REVIEW.md`.
2. **Brief 18c, the CI image test.**
   - Install the service at `/usr/libexec/aresos-control/`, the `/etc/claude-code` files and
     `/usr/share/aresos/control/user-mcp.json` into a CI image.
   - Run Mail against fixture servers, and Chrome's record refresh, under the real `aresos-toold.service`.
   - The image needs `gh` 2.102 or later.
   - Agree every `os/` change with the image's session (`laptop-aresos` or its successor) before it runs.
3. **Live tests on his laptop**, once the tools are installed there, with him present:
   1. Mail onboarding with his own account. He signs in; the password stays with the tool service.
   2. A test mail to himself.
   3. Chrome: a Claude tab (read, navigate, a test form, Stop), then taking one of his own tabs for a request.

## Rules that stay

- Never force-push and never use `--no-verify`; when the privacy check blocks, fix the content.
- No personal data, mail-provider names or personal addresses in the repo. Tests never use real accounts or real
  sites; live tests are his, on his laptop.
- An image release needs his OK and a rehearsal.
- Reviewers: Codex while it is available, otherwise a fresh Claude agent on Opus; Fable only for high-stakes reviews
  (`CLAUDE.md`, "Reviews"). Codex is available until about Sat 2026-11-14 and again from Tue 2026-11-17 10:53 until
  the plan ends on 2026-11-21.
