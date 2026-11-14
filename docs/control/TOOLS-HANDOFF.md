# Control-layer tools: the baton

Written 2026-11-14 by `linux-tools`, the AresOS-side session that leads the tools since 2026-11-13. It replaces the
handover `mac-aresos-control` wrote on 2026-11-12. A fresh session that takes over reads this, then `STATE.md`
(item 6, the control layer), then the board (`board`, topic `tools`). Docs are claims: check `git log`, `gh pr list`
and `git worktree list` first.

## Who does what

- **`linux-tools`** (this baton): the tools. `control/`, `docs/control/`, `docs/design/CONTROL.md`, the `control-*`
  workflows, briefs 18c, 18c-b, 28, 28a, 28b.
- **`mac-aresos-control`** (Mac): the Chrome tool, PR #27, until it merges (planned 2026-11-16, with a merge commit,
  not a squash). Never push to `pkg/20-chrome`.
- **`linux-aresos`**: `os/`, the accounts and the releases. Every `os/` change is agreed with it first, it reads
  the `os/` diff before a merge, and it is told before `.github/workflows/os-image.yml` is touched.
- **`mac-capacity`** (Mac): the owner's coordinator. Ask it for a limit check before starting builders; tell it
  merges and blockers in one line.

## Where things stand

| Work | Where | State | Next |
|---|---|---|---|
| Brief 18c | `briefs/18c-image-test.md`, on main (PR #42) | Final; the `os/` change agreed with `linux-aresos` (sixteen changes, in the brief). | - |
| 18c, container part | on main (PR #43) | The unit may reach the network; 17 interactive Claude Code cases in `control-boundary`. | - |
| 18c, image part | `pkg/18c-image`, `~/AresOS-18c-image`, draft PR #58, start note `briefs/18c-image-start.md` | Green without Chrome (2026-11-14): `check_build=control` twice on `2d1ad22f` (run 43577034725 and its rerun), `check_build=build` once (43581194306); 5 of 5 control runs used. Results, check 6's numbers and the report text in `reviews/18c-image-test/PROGRESS.md`. Its first run found the hook bug fixed by PR #61. | After PR #27: Chrome's two startup files, `SOCKET_MODES` from the merged `daemon.py`, one more VM run (new budget). Then the lead assembles `REPORT.md`, updates the `os/` diff summary, and runs the reviews (Codex from 2026-11-17: package review and high-stakes security review). Then `linux-aresos` reads the `os/` diff, then the owner's yes. |
| Service fixes | not written | Found by 18c's VM runs: active before its sockets exist (Type=notify), `aresos admin` as `ares` without a sudo hint, 10 idle wake-ups/s, endless restart without a start limit, the outside-folder refusal naming Desktop, and the owner's #254 for the service-down notice. Board #233, #235, #237, #255. | A small brief after PR #27 merges (daemon.py overlaps). |
| Chrome briefs 28, 28a, 28b | `briefs/28-chrome-capability`, draft PR #48 | Ready to build: three review rounds each, the final package check worked in, the security confirmation READY (`reviews/28-chrome-capability/`). | Merge after PR #27 is on main, checking section 6 against its final names and `KNOWN-LIMITS.md`. |
| Package 28, step 1 | `pkg/28-chrome-read`, `~/AresOS-28-chrome-read`, cut from `pkg/20-chrome` | The view module (pure Python) on a Fable builder, new files only, no pull request; progress in `reviews/28-chrome-read/PROGRESS.md`. | After PR #27 merges: move the commits onto main, then the next steps of 28 (the reader, the wiring, the baseline), then 28a, then 28b. |
| Brief 18c-b | not written | Design settled: force-install by policy from a `file:` address inside the image, a fresh signing key per image build that is thrown away, symlinks in `/etc` to files in `/usr`. Research with sources: `~/AresOS-18c-b-extension-research.md` on the laptop (put it into the brief's folder). `mac-aresos-control` has no objection. | Write the brief after PR #27 merges; agree the paths with `linux-aresos`; prove it in the CI VM on the shipped Chrome. Board #223, #224. |
| Live tests | the laptop | Waits for a release that carries the tools. | Mail onboarding with him first (he signs in himself), a test mail, then Chrome. His own hosts go on Chrome's never-list in that sitting (board #200). |

## The owner's answers, written into the briefs (#254: into the service-fix brief)

- #201: Claude may close a tab of his when he asks.
- #202: the first version reads text only, no screenshots.
- #203: the tools use `Downloads` and `Documents`.
- #210 ("Ask first"): typed text in form fields is read only through the asking read.
- #213: link addresses are shown, sign-in-like values hidden.
- #216: rich-text editors are read without asking.
- #254 (2026-11-14, "Quiet unless used"): while the tool service is down, a Claude Code session that never used the tools gets no notice; one that prepared or sent something with them gets one clear notice that the AresOS tools are not running.

**Still his, later:** his yes to "the next release carries the Control tools: a background service, and two
managed hooks in every Claude Code session on the laptop" before the image part of 18c merges. Ask it with the
numbers of the ordinary-session check (what a session sees while the service is stopped or failed), in words he
can picture.

## Decisions of the lead worth knowing

- The image part of 18c is built before PR #27 merges; it is not merged before PR #27 is on main and Chrome's
  startup files are added.
- Brief 28 was split in three (reading, acting, his tabs). None reaches the laptop before all three are merged.
- A shorter hold after each input (about half of a click's 590 ms) is a possible later package with its own
  security review, weighed after his live test (`briefs/28a-chrome-act.md`, "Out of scope").
- When `linux-aresos` puts its dispatcher at `/usr/bin/aresos`, Control's wrapper moves to
  `/usr/libexec/aresos-control/cli` and Control drops its top-level `log` shortcut (board #199).

## How the work runs

- Builders work in steps (`CLAUDE.md`): one fresh agent per step, a `PROGRESS.md` in the package's review folder,
  restart from the commits. Claude builders can't write `REPORT.md`; the lead folds their progress file into it.
- Reviews per `docs/REVIEW.md`, "Tools for Claude": a package review and a security review by fresh reviewers, one
  fix round, a re-check, CI twice. The three Chrome packages and the image part of 18c get a high-stakes security
  review (Fable 5.2 or Codex's frontier model). Codex's shared allowance is empty until 2026-11-17 10:53 and ends
  on 2026-11-21.
- GitHub watchers always with `--interval 60` or longer; the API allowance is shared.
- Never force-push, never `--no-verify`. No personal data, mail-provider names or real addresses in the repo.
- Changes to the running laptop (sudo, system settings) only with his explicit OK in the session.
