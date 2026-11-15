# Control-layer tools: the baton

Written 2026-11-14 by `linux-tools`, the AresOS-side session that leads the tools since 2026-11-13. It replaces the
handover `mac-aresos-control` wrote on 2026-11-12. A fresh session that takes over reads this, then `STATE.md`
(item 6, the control layer), then the board (`board`, topic `tools`). Docs are claims: check `git log`, `gh pr list`
and `git worktree list` first.

## Who does what

- **`linux-tools`** (this baton): the tools. `control/`, `docs/control/`, `docs/design/CONTROL.md`, the `control-*`
  workflows, briefs 18c, 18c-b, 28, 28a, 28b.
- **`mac-aresos-control`** (Mac):
  - Merged the Chrome tool, PR #27, on 2026-11-14 (merge commit `09cedc84`), and the main fix, PR #68, on
    2026-11-15 (squash `bdc16064`). Chrome is now `linux-tools`' own; its notes are in "Chrome merged" and "Main fix
    merged" below.
  - Merged brief 20-popup-race, PR #77, on 2026-11-15 (squash `635872e2`); notes in "Popup races merged" below.
  - Finishing brief 20-restore-lock (`pkg/20-restore-lock`): two restore-lock regressions from PR #27 and board
    #185, the optional owner oracle's re-pin. It changes `engine.py` and the oracle. It hands over when merged.
- **`linux-aresos`**: `os/`, the accounts and the releases. Every `os/` change is agreed with it first, it reads
  the `os/` diff before a merge, and it is told before `.github/workflows/os-image.yml` is touched.
- **`mac-capacity`** (Mac): the owner's coordinator. Ask it for a limit check before starting builders; tell it
  merges and blockers in one line.

## Where things stand

| Work | Where | State | Next |
|---|---|---|---|
| Brief 18c | `briefs/18c-image-test.md`, on main (PR #42) | Final; the `os/` change agreed with `linux-aresos` (sixteen changes, in the brief). | - |
| 18c, container part | on main (PR #43) | The unit may reach the network; 17 interactive Claude Code cases in `control-boundary`. | - |
| 18c, image part | `pkg/18c-image`, `~/AresOS-18c-image`, draft PR #58, start note `briefs/18c-image-start.md` | Green with Chrome's files and 18e's fixes on `9ee1fbdf` (2026-11-15): `check_build=control` twice (run 43687234953, attempts 1 and 2), `check_build=build` once (43691820743), the six control workflows green. Check 6 shows "quiet unless used" under the real systemd; idle 1 wake-up in 60 s. Results, check 6's numbers, JUDGMENT-CALLs 1-22 and the report texts in `reviews/18c-image-test/PROGRESS.md`. Merging main conflicts only in `os/manifest/ci/16/pending-rebind.json` (regenerate with `rebind.py pending`). | Tue 2026-11-17: Codex package and security review (board #287). After 18e merges: merge main, `check_build=control` twice and `build` once, the lead assembles `REPORT.md` from PROGRESS.md, `linux-aresos` reads the `os/` diff, the owner said yes on 2026-11-15 (#286), so it merges once the reviews pass. |
| Service fixes, brief 18e | `briefs/18e-service-fixes.md`, `pkg/18e-service-fixes`, `~/AresOS-18e`, PR #69 | Built on head `13e9e1e4`, the six control workflows green. Proven under systemd by 18c's VM pass (failed state after 10.2 s with `Result=exit-code`, one notice per outage, hooks 0.12-0.18 s with the service down). Report text in `reviews/18e-service-fixes/PROGRESS.md`. | Tue 2026-11-17: Codex package and security review, fix round, merge. A change after `13e9e1e4` means 18c merges it again and reruns. |
| Chrome briefs 28, 28a, 28b | `briefs/28-chrome-capability`, draft PR #48 | Aligned with merged #27; review 4 NOT READY, fix round done (`reviews/28-chrome-capability/ALIGNMENT.md`). | Tue 2026-11-17: Codex review of the changes since `42aa0370`, `chrome_take_reload` as a whole (board #284). READY, then merge. |
| Package 28 | `pkg/28-chrome`, `~/AresOS-28-chrome-read` (old `pkg/28-chrome-read` kept as record) | Steps 1/1b (view module) on main's base; step 2 (efficiency fixtures and probe) committed, progress in `reviews/28-chrome-read/PROGRESS.md`. | PR #68 is on main (`bdc16064`): merge main, wire the probe into `latency-pair.sh`, upload, commit the baseline, draft PR. Then the reader, adapter, deadlines, browser groups; then 28a, then 28b after PR #48 merges. |
| Brief 18c-b | `briefs/18c-b-chrome-image.md`, on main (PR #73, `a7b5cf52`) | Two Fable brief reviews (NOT READY, then READY with six should-fixes, folded in); `linux-aresos` agreed the `os/` part (owner's list in `/var/lib/aresos-control`, refused placeholder). Owner's answer #297: Chrome's managed notice is fine. Build: `pkg/18c-b-chrome`, `~/AresOS-18c-b-build`, draft PR #76; steps 1a (Fable), 1b (Opus), 2 and 2b (Fable) built: the install proof passes all five cases on the pinned Chrome (run 43729218613, head `c4514015`). The lead's decisions after 2b are on top of `reviews/18c-b-chrome-image/PROGRESS.md` (a DevTools pipe only in the proof's own Chrome starts, also for C9 and C2 in the VM). | Step 3a, after PR #58 is on main; tell `linux-aresos` before the first `os-image.yml` commit. |
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
- **Excluded sites:** moving with brief 18c-b (PR #73) to `/var/lib/aresos-control/chrome-excluded-sites.json`, so
  an update or `previous` keeps his list. tmpfiles creates it as a placeholder the validator refuses
  (`{"format":0,"hosts":[]}`), so Chrome's tools refuse until he writes a format-1 list with sudo in the live test
  (#200; an empty list if he excludes nothing). Root-owned, mode 0640, in the service's group; the service can't
  write the folder. His own hosts never go in the repo.
- **Build marker:** the build hash goes into `chrome/build-id.json`.
- **`gh`:** version 2.102 or newer.
- **Service unit:** `aresos-toold.service` is byte-identical to `8b7e799c`.

## Main fix merged (2026-11-15, notes from `mac-aresos-control`)

PR #68 (brief 20-main-fix) is on main as squash `bdc16064`; report in `reviews/20-main-fix/REPORT.md`.

**What changed for Chrome CI.**
- No job of either Chrome workflow is main-only. Only the two steps that write to GitHub are, and
  `control/chrome_tests/workflow_steps.py` with `test_qualification.py` allows exactly those.
- Pull requests run every other step:
  - publishing goes to a local bare remote;
  - attestation is on `refs/pull/N/merge`, and CI shows main's policy refuses that bundle;
  - off main the plan runs only the stable channel.
- `qualify.py` refuses to publish to origin or notify off main.

**First record.** Main's run 43696892949 published the first attested record to the data branch
`chrome-qualification`.
- **Stable 157.0.8103.78:** every group passes.
- **Beta 159.0.8154.6:** recorded all-false, wrongly. Every beta test passed, but `qualify.py pair` read the
  version as the last word of `chrome --version`, which is `beta` on that channel (issue #74).
  - Why it matters: `switches()` lets beta evidence cover the first stable of a major. So that entry would turn
    every group off on a laptop with build `4c1eccb9…` and stable 159, until a later passing 159 entry for that
    build overrides it.
  - Fixed by P4 of brief 20-popup-race (PR #77). Main's run 43726046022 on `635872e2` qualified the new build
    `e08ec851…` on stable 157 and beta 159 with every group passing. #74 stays open: see "Popup races merged".
  - **Design question for you:** an identity mismatch (measured version or build differs from the plan) is not
    evidence about the browser, yet it is recorded all-false forever. I'd make it refuse publication and turn the
    run red, and keep all-false for an incomplete suite. That changes the trust model, so it needs its own brief.
- **Notify.** Notify's pull request failed: the repository doesn't let workflows create pull requests
  (`can_approve_pull_request_reviews: false`). After P4:
  - notify writes issues only, one open issue per title;
  - the shipped-copy update becomes an issue whose body has the `gh pr create --head chrome-qualification`
    command for a session to run.

**Latency gate and the runner's disk: it now fails often.**
- **The evidence.** Six latency jobs failed on p95 tails alone, with medians normal and no reference regression:
  - main's `latency (audit)` 43647781438;
  - PR #68's `latency (plain)` 43687610984, attempt 1;
  - PR #77's `latency (plain)` and `latency (audit)` 43712049957, attempt 1;
  - main's `latency (plain)` and `latency (audit)` 43726046014 on `635872e2` (PR #77's merge): audit
    history-4000 `asking_click` p95 129 ms against 100 (median 27); plain `navigate` p95 169 ms at history-1000 and
    160 ms at history-4000 against 150 (medians 44 and 59). The slowest samples spent 92 to 250 ms in
    `store_write`, the bridge 6 ms or 26 to 31 ms as usual. Not re-run: main's Chrome workflow stays red on that
    commit for this reason alone.

  In every slow sample, H5's stages put the extra time in `store_write`: up to 940 ms, against a median of 10 to
  50 ms. `bridge_round_trip` and `extension_total` stayed normal. The re-runs were clean.
- **What it means.** The gate is measuring the shared runner's disk sync, not the product. Main's Chrome run, the
  daily one included, and every Chrome pull request can go red without a code cause.
- **My suggestion** (your call, since you own the gate). In `latency-pair.sh`:
  - keep the service's store on a tmpfs for the timed phases. Its sync cost is then near the laptop's NVMe (about
    0.03 ms per fsync in H5's measurement), not the runner's;
  - gate the **number** of fsyncs per call: `journal_fsync`'s `count`, plus SQLite's commits. Those counts are
    deterministic, so a change that adds disk syncs is still caught exactly.

  The ceilings and sample counts would stay as they are.

**Two CI facts.**
- **Path filters:** a pull request's path filters see the whole PR's diff. Every push to an open Chrome PR starts
  both Chrome workflows again, even a docs-only push. Use `[skip ci]` for those.
- **Daily schedule:** both Chrome workflows also run daily at 04:19 UTC on main.

## Popup races merged (2026-11-15, notes from `mac-aresos-control`)

PR #77 (brief 20-popup-race) is on main as squash `635872e2`; report in `reviews/20-popup-race/REPORT.md`.
- **P1, P2** are in `background.js`: a duplicate-breakpoint refusal re-arms once, and the slow-load fallback says
  whether the page is still loading. **P3** (naming an uncontrolled popup) is yours in brief 28a, together with the
  accepted ordering residual (security NOTE 1: a possible "pause still live" check before installing).
- **P4**, the publisher: `pair` reads the version after the browser's name; notify writes issues only, one open
  issue per title, and counts only `github-actions[bot]`'s own issues and comments.
- **Issue #79, the shipped copy.** Notify opened it on the first run after the merge: the data branch holds four
  entries that `control/chrome/qualification.json` on main lacks. Not urgent, since runtime delivery uses the
  attested record. When you run its `gh pr create` command, **merge that PR with a merge commit, not a squash**. The
  file is one JSON line, and the data branch forks from main at `4214526f`. After a squash the merge base stays
  there, so the next update conflicts on that line. A merge commit moves the base to the data branch's head. Never
  merge main into the data branch: it is the publisher's append-only record.
- **Notify reports old builds' failures forever.** `notify` lists failing groups over the whole record, so the old
  build `4c1eccb9…`'s all-false beta entry is reported on every run. That is why #74 is open again: closed, the
  next daily run would open a duplicate. My suggestion: report only the entries this run published. Small, in
  `qualify.py notify` plus `test_publisher.py`; the trust path doesn't change. Close #74 once it is in.

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
