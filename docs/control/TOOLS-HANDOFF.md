# Control-layer tools: the baton

Written 2026-11-14 by `linux-tools`, the AresOS-side session that leads the tools since 2026-11-13. It replaces the
handover `mac-aresos-control` wrote on 2026-11-12. A fresh session that takes over reads this, then `STATE.md`
(item 6, the control layer), then the board (`board`, topic `tools`). Docs are claims: check `git log`, `gh pr list`
and `git worktree list` first.

## Who does what

- **`linux-tools`** (this baton): the tools. `control/`, `docs/control/`, `docs/design/CONTROL.md`, the `control-*`
  workflows, briefs 18c, 18c-b, 28, 28a, 28b.
- **`mac-aresos-control`** (Mac): merged the Chrome tool, PR #27, on 2026-11-14 (merge commit `09cedc84`). Chrome is
  now `linux-tools`' own; the notes it left at the merge are in "Chrome merged" below. It keeps board #185 (the
  optional owner oracle's re-pin) until it says otherwise.
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

## Chrome merged (2026-11-14, notes from `mac-aresos-control`)

PR #27 is on main as a merge commit (`09cedc84`, final head `d25ccbd3`), so `pkg/20-chrome`'s history is intact and
`pkg/28-chrome-read` (cut at `524173c4`) can move onto main. Final pair: Control Chrome 43641834739 (push) and
43641839672 (pull request), 28/28 jobs each; base, boundary, qualification, Mail and polkit twice each (full
reruns). Reviews: rounds 4 and 5 SAFE, package (Opus) and security (Fable), in `reviews/20-chrome/`.

**Latency.**
- **Report:** `reviews/20-chrome/REPORT.md`, sections "Latency gate: 60 samples (2026-11-14)", "Step 4" and
  "Step 6", with receipts in `reviews/20-chrome/records/`.
- **Gate:** `control/chrome/ci/latency-targets.json`.
  - Ceilings in ms (median / p95): read 35/60, navigate 100/150, click 650/750, fill 650/750, asking click 60/100,
    approval to done 700/850.
  - A median or p95 over its ceiling fails.
  - Sample counts: `samples_per_call` 60; `old_runtime_samples_per_call` 20, which must match the frozen
    `latency-reference.json`.
- **Harness:** in `control/chrome/ci/`, `latency-pair.sh`, `latency-probe.mjs`, `latency-instrument.mjs`,
  `latency-profile.py`, `latency-summary.py` and `latency-check.py`; plus `control/chrome_tests/latency.test.mjs`.
- **The 525 ms hold window is unchanged.** A shorter hold is the later package named above.

**Rules from now on.**
- **4,096 characters.** Claude Code 2.1.319 passes only the first 4,096 characters of an MCP server's instructions.
  `control/chrome_tests/test_questions.py` (about line 456) checks every app, `control` included. Brief 28's reader
  text will press on it.
- **Partial index.** `operation_open` is built from one definition, `OPEN_OPERATIONS` in `storage.py`. Its plan and
  timing tests (`test_full_disk_reads`, `test_open_index_timing`) passed on SQLite 3.45.1 (CI) and 3.50.4 (Mac). They
  must also pass on AresOS's own SQLite, so run the normal Python suite in 18c's image.
- **Run budget.** The ~280 `control-chrome` runs were `mac-aresos-control`'s guard for #27; about 271 are used,
  main's run included. Package 28 sets its own.

**For `pkg/28-chrome-read`'s `KNOWN-LIMITS.md`, word for word** (both round-4 reviewers recorded it):
"Taking a tab from another normal window while a Claude tab group already exists moves the tab into that group's
window, because Chrome keeps a tab group in one window; the extension records the tab's original window and position
and moves it back on release. The harm is that the owner's tab sits in another window while Claude holds it; it is
accepted with the single-group design, and one group per window is a design question for brief 28b."

**Follow-ups for 28 or 28b, none blocking.**
- **Retry advice.** On `requireTab`'s retry for a tab that is already controlled (`background.js`, about line 609,
  `pending.retry??=lateReader(tab)`), the refusal's "take the tab again" doesn't help: `take_tab` returns early, and
  the rejected retry stays cached. Say "release and take the tab again", or release on a rejected retry. It's narrow:
  a dialog or the 5 s timer beat admission.
- **Hardening.** Match `embedderName` as well as `url` for the injected scripts (`background.js:126`). Pages are
  already shut out by `isDefault===false`.
- **`control_status`.** If it ever reaches Claude, review its `installs` rows again.
- **New fields.** `chrome_tabs` rows now carry Chrome's `audible` and `muted` flags. That's new since the 28 briefs;
  check section 6 against it.

**For `linux-aresos`, through 18c and 18c-b** (full text in `control/chrome/packaging/README.md`):
- **Polkit policy:** `org.aresos.control.chrome-loosen.policy`, installed root-owned with mode 0644 at
  `/usr/share/polkit-1/actions/`.
  - The image needs `/usr/bin/pkcheck` and a polkit agent in his session.
  - 18c-b presses "Allow editing" once with his real agent. The dialog names the site, and a cancelled dialog leaves
    the site read-only.
- **Chrome policy:** `policy.json`, in `/etc/opt/chrome/policies/managed/`.
- **Native host:** `native-host.json`, in `/etc/opt/chrome/native-messaging-hosts/`.
  - The host launcher is installed with mode 0755, and `native_host.py` beside it with mode 0644.
- **Excluded sites:** `/etc/aresos/control/chrome-excluded-sites.json`, containing `{"format":1,"hosts":[]}`.
  - Root-owned, mode 0640, in the service's group.
  - His own hosts are added in the live test (#200), never in the repo.
- **Build marker:** the build hash goes into `chrome/build-id.json`.
- **`gh`:** version 2.102 or newer.
- **Service unit:** `aresos-toold.service` is byte-identical to `8b7e799c`.

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
