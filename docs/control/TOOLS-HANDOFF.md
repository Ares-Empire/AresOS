# Control-layer tools: the baton

Written 2026-11-14 by `linux-tools`, the AresOS-side session that leads the tools since 2026-11-13. It replaces the
handover `mac-aresos-control` wrote on 2026-11-12. A fresh session that takes over reads this, then `STATE.md`
(item 6, the control layer), then the board (`board`, topic `tools`). Docs are claims: check `git log`, `gh pr list`
and `git worktree list` first.

## Resume here (2026-11-19 19:35, `linux-tools` after a clear)

The detail behind every line is in `~/codex-queue/linux-tools/QUEUE.md` (newest entries at the top of the dated
list). Shell watchers started by the old session are gone: start new ones with `gh run watch <id> -R
Ares-Empire/AresOS --interval 300` in a background shell.

1. **R28: cut taken 12:05 (main `fba94b25` with #111 and #122, merged into pkg/42 as `7f896b62`).** #111 and #122 ride R28 if merged by 10:00 and
   Control CI is green **on main's merge commit**; send `linux-aresos` that commit and the results. If either goes
   red, revert it before 11:30 and it rides R29.
   - **Both merged.** #111: main `c496035629e10f84887a01f2923ecedc72fcb48d`. #122 (07:27): main
     `89dc80b186670e447d659024f493c7e62702307e`, which contains #111. On `c4960356` base, boundary and privacy are
     green and Mail 44466979939 was running; its queued Chrome and qualification runs were cancelled because
     `89dc80b1`'s runs cover both PRs: Chrome 44472212759, qualification 44472212767, boundary 44472212816, base
     44472224412, Mail 44472228261, privacy 44472232086: **all green (08:54), sent to `linux-aresos`; both ride R28.**
   - What he sees after #111 (for `linux-aresos`' owner line, sent): after an interrupted save the tools ask him to
     free space and restart `aresos-toold` (a system service: his password, or a reboot) and refuse requests,
     reads included, until then. Board #386 brings reads back (with N8) and re-pins once.
2. **28a** (`pkg/28a-chrome-act`, `~/AresOS-28a-act`, draft PR #116 stacked on `pkg/28-chrome`; its CI is
   dispatched by hand: control-chrome, control-chrome-qualification, control-base, control-mail, repo-privacy).
   - Steps 0a to 1d part 1 built (PROGRESS has each); CI green on `bd86097c` (0b to 1a).
   - On `c579a066` (1b, 1c, old catalogue): everything green except Control Chrome's **latency (plain)** job (run
     44456571350). Likely the fingerprint's outline cost (1a measured 0.3 s → 1.0 s for 20,000 nodes on doubles).
   - 1d part 2's code is at `a2ad7c7d` (groups 14 to 16, the latency run, `REASK_RESULT` as in #122): Chrome
     44463920809 had two failures so far (fixtures external and policy, recheck2), qualification 44463926398 queued.
   - **The stopped agent left an unpushed local commit `e4c06925`** ("the stand-in DOM runs every branch a listed
     node picks") **and an uncommitted one-line edit in `control/chrome/ci/act-matrix.mjs`.** Inspect both first.
     No "Step 1d, part 2" PROGRESS section yet.
   - **10:00: `28a-1d2-fix` done** (`c6b9a2d4`, `790d6151`, PROGRESS "Step 1d, part 2" `efd56521`): the fixture and
     qualification causes repaired; no latency ceiling missed (worst read 19.01/19.64 ms against 35/60). Chrome
     44491713756 and qualification 44491718224 run on `790d6151`; F4's 9,000-byte assertion still fails there.
   - **Lead decisions (10:00):** conservative F4's approval measures 13,348 bytes (form 6,311, `item_fields`
     repeating 5,127) against the brief's 9,000 (ASK_LIMIT 16,384 stays). Accept it: F4 sends in one approval,
     which was the point (main refuses it at about 21,700). The assertion becomes "under ASK_LIMIT, pinned at the
     measured size with a small margin (at most 14,000), and the same facts with whole options are refused".
     Deduplicating `item_fields` against `form` changes the frozen asking path: a later item with its own review
     (known limit: a form about a quarter bigger than F4 refuses with `asking_input_too_large`). The old F4
     comparator's extra `chrome_old_find` stays: brief 20 needs a fresh find after fills.
   - **11:30: Codex Sol `28a-1d2-fix2` done** (`4fb4821b`, `18fadda2`, PROGRESS `d42d1890`): the F4 pin (at most
     14,000, under ASK_LIMIT, whole options refused) and its known limit are in; latency (plain)'s cause was the F3
     find at 218.5/291.4 ms against a 207.3 ms median ceiling, so the fingerprint hashing got cheaper; recheck2's
     empty-owner-page fixture fixed.
   - **19:35 (after a clear): green on `18fadda2`**, Chrome 44505065741 and qualification 44505070907, every job.
     Base 44588323576, Mail 44588330029 and privacy 44588336857 dispatched on `d42d1890`. **Codex gpt-6.2-sol xhigh
     `28a-1d2-gaps-b` running** (prompt `~/codex-queue/linux-tools/28a-1d2-gaps.txt`, log `~/AresOS-28a-1d2-gaps-b.log`):
     the four browser cases part 2 left unproven (an input held back at seconds 11 to 13, through an instrumented
     test build only; the owner typing with real keys during a step; muted playback; an `unknown` outcome with its
     shape). It pushes, dispatches Chrome and qualification once and stops; read those runs. Then step 2
     (HARNESS-MAP), step 3 (removal; CONTROL.md section 6 needs `chrome_show`'s focus exception;
     `response_checks.check_responses` in the Chrome tests, #122's NIT 2), step 4 (full validation twice), the
     package and security reviews. Red: one Codex Sol fix step that pushes, dispatches once and stops.
3. **18c-b** (`pkg/18c-b-chrome`, `~/AresOS-18c-b-build`, draft PR #76; rides R29).
   - Step 4 done (`8bcb9504`; `linux-aresos` read its `os/` diff: OK). Step 4b pushed `3cb3687d` (C3, the rest of
     C6, C10, C11) and `1b263438` (fixes); control runs 44452254488 and 44462912726 red, 44468856359 queued. That is
     7 of the brief's 12 `check_build=control` runs (4b was given 4). No "Step 4b" PROGRESS section yet.
   - **4b green and recorded** (`20eddb77`): C3, the full C6, C10, C11 PASS in 44468856359; `checks_only`
     44488329704 (1820 tests); the managed-note screenshot exists; 7 of 12 control runs used; `linux-aresos` has
     4b's `os/` diff (three CI-only files). Next: step 5 (C4, C5, C9, then C7 and C8), then 6. When main is merged
     in after R28: take main's `pending-rebind.json`, rerun `rebind.py pending` with step 4's five notes word for
     word plus the merge note; keep pkg/42's comment and 156 in `os-image.yml`.
4. **Package 28** (#72): held until right after R29's cut, then merge and retarget #116 to main.
5. **Board:** #386 (N8 and N9 follow-up, one re-pin), #298 (live Chrome setup with him). #337 and #385 done.
6. **Budget (`mac-capacity`, 06:50):** Claude about 2% a day for this lead; one Claude agent at a time; no Claude
   agent waiting on CI (shell watchers do that); Opus by default, Fable only for installs, rollback, credentials
   and security. Codex may take Sol builds again within about 12% a day (meter in `~/.codex/sessions/`). Doc-only
   commits on a PR into main end with `[skip ci]` (every push re-runs Control CI, and Control Chrome never cancels
   a superseded run).

## Who does what

- **`linux-tools`** (this baton): the tools. `control/`, `docs/control/`, `docs/design/CONTROL.md`, the `control-*`
  workflows, briefs 18c, 18c-b, 28, 28a, 28b.
- **`mac-aresos-control`** (Mac):
  - Merged the Chrome tool, PR #27, on 2026-11-14 (merge commit `09cedc84`), and the main fix, PR #68, on
    2026-11-15 (squash `bdc16064`). Chrome is now `linux-tools`' own; its notes are in "Chrome merged" and "Main fix
    merged" below.
  - Merged brief 20-popup-race, PR #77, on 2026-11-15 (squash `635872e2`); notes in "Popup races merged" below.
  - Merged brief 20-restore-lock, PR #80, on 2026-11-15 (squash `b04c7e77`): two restore-lock regressions from
    PR #27, and board #185, the owner oracle's re-pin. Notes in "Restore lock merged" below.
  - **Its control role has ended** (2026-11-15). Everything it held is on main or listed below for you.
- **`linux-aresos`**: `os/`, the accounts and the releases. Every `os/` change is agreed with it first, it reads
  the `os/` diff before a merge, and it is told before `.github/workflows/os-image.yml` is touched.
- **`mac-capacity`** (Mac): the owner's coordinator. Ask it for a limit check before starting builders; tell it
  merges and blockers in one line.

## Where things stand

| Work | Where | State | Next |
|---|---|---|---|
| Brief 18c | `briefs/18c-image-test.md`, on main (PR #42) | Final; the `os/` change agreed with `linux-aresos` (sixteen changes, in the brief). | - |
| 18c, container part | on main (PR #43) | The unit may reach the network; 17 interactive Claude Code cases in `control-boundary`. | - |
| 18c, image part | on main (PR #58, squash `beb42ec8`, 2026-11-18) | Codex astra reviews: SECURITY-REVIEW-X1 SAFE (known limits K1 auto mode, the Stop JSON diagnostic, UID/GID 250 on the rehearsal); REVIEW-X1 and RECHECK-X1..X3 CHANGES-NEEDED, closed by fix rounds X1 (Opus), X2 (Opus), X3 (Fable: check 8 rebuilt around one record per learned path) and X4 (Codex astra); RECHECK-X4 SAFE on `16bcc784` with two NITs as known limits (cached mount paths under coordinated renames; a nested btrfs subvolume without its own mount would fail check 8). All green on `16bcc784`: checks_only 44180217274, control 44184266040 and 44195810105, build 44199832455. Owner's answers #286, #254, #203, #349. `linux-aresos` read the `os/` diff after every round. Report: `reviews/18c-image-test/REPORT.md`. `CONTROL_CHROME_BUILD` `7854f4a2…cfbbfb` at merge (follows main at the cut). | R28 step 2 and 43 step 3 (`linux-aresos`) start from it. Next on our side: 18c-b step 3a. |
| Service fixes, brief 18e | on main (PR #69, merge commit `9324224a`, 2026-11-16) | Reviews: package CHANGES-NEEDED → two fix rounds → RECHECK-2 SAFE twice; security SAFE; astra cross-review SAFE (its nit fixed by #89). Pending reminders and notices reach only a session that used the tools; reminder says don't complete, cancel, resend or acknowledge on your own; sockets bound then renamed. Known limits in `reviews/18e-service-fixes/PROGRESS.md`. Chrome's server instructions are at 4,093 of 4,096 characters. Queue item 16 merged as PR #97 (`4737bb69`, 2026-11-17): the IdleLoop tests use a stopped wall clock with independent lateness bounds (they no longer measure real reaction time); #96's nits; Control base under `--init`. Known limit: the idle checks' 1 s real budget fails at about 0.5 s per fsync. | - |
| Chrome briefs 28, 28a, 28b | on main (PR #48, merge commit `75f7d80e`, 2026-11-16) | Review 6 READY and its recheck READY (Claude Opus); lead's decisions in `reviews/28-chrome-capability/ALIGNMENT.md` through "After review 6's recheck". | Codex astra cross-review (Tue; prompt `28-brief-cross-5.txt` written for the merged head); its findings go to the 28a and 28b builds, which must also make room in Chrome's instructions. |
| Package 28 | `pkg/28-chrome`, `~/AresOS-28-chrome-read`, draft PR #72 | Steps 1-14 built; green twice. Codex astra package and security reviews (2026-11-18) CHANGES-NEEDED (security: presentational textarea roles and a slash in a fragment bypassed withholding); fix round X1 (astra, code `52891587`, green twice) closed every finding and two siblings; RECHECK-X1 SAFE (`cd2ce599`). Reports: `reviews/28-chrome-read/` (REPORT, KNOWN-LIMITS, HARNESS-MAP). | **Held unmerged until right after R29's cut** (owner via mac-capacity, 2026-11-18: R29 ships 18c-b with PR #27's tools; 28, 28a and 28b reach the laptop together). 28a builds stacked on `pkg/28-chrome` (Claude Opus agents from Thu). |
| Brief 18c-b | `briefs/18c-b-chrome-image.md`, on main (PR #73; revised by #106: the profile pin's restore contract, no profile password dialog) | Build `pkg/18c-b-chrome`, `~/AresOS-18c-b-build`, draft PR #76: steps 1a-2b, 3a and its fix (green: build 44288748140; `linux-aresos` read the `os/` diff) and 3b (`gh`: RPM, signature, keyring and install PASS; build 44339552024 red on a name-based docs/completions check; resolve 44344811923 green). | Step 4 done (`8bcb9504`), 4b in CI; then 5, 6. See "Resume here", item 3. Rides R29 with PR #27's tools. |
| Shipped qualification copy | on main (PR #83, merge commit `68dde093`, 2026-11-16; fix PR #87, squash `52d13cb7`) | Tests and harness start Chrome from a fixture runtime with an empty shipped copy; the shipped copy holds 8 attested entries (runs up to 43856179386). #83's six checks green on `0a285b24`; the two later entries checked locally (valid, append-only). | Queue item 9 done in PR #93 (below). |
| Qualification follow-ups | on main (PR #93, squash `23424f07`, 2026-11-16; read cost PR #98, squash `3a5eea14`, 2026-11-17) | #87's nits N1-N4; the pending-row projection goes through `record()` (O1); `mode()` reads the record once per call (O2). A refresh that fails after `verified()` says the held record may have changed, and `maintenance()` re-reads it. Brief 79-read-cost (empire 301): one slot per Qualification keyed by the journal offset and the line's exact bytes, compared on every cached read; `shipped` a deep copy; `_hold()`; the 300-entry latency leg is back (history-4000 read 20.1/21.4 ms against 35/60). Codex astra xhigh REVIEW-1 SAFE: all 26 mutation variants killed. | - |
| Control follow-ups | on main (PR #89, `e9fd8ffc`, 2026-11-16) | 20-ci-noise's nits 1-6 and #69's socket-mode pin (queue items 3 and 10). | - |
| Stop hook | on main (PR #91, `91487807`, 2026-11-16) | The managed Stop hook runs under `/bin/sh` and always exits 0; only JSON `{"decision":"block"}` blocks. Quiet for a session that never used the tools; an unreadable mark counts as not used. Marks live in `/run/user/<uid>/aresos-control/used/`; the walk from a hook to its session is four levels and never PID 1 (`usage.py`). | - |
| Owner channel test | on main (PR #96, `d0b91522`, 2026-11-16) | The channel test marks the session its hooks resolve; the owner-oracle workflow runs its containers with `--init` (a test process at PID 1 was the ledger job's failure) and has a `ledger_only` input (about 20 min instead of 2.5 h). | Its nits 1 and 2 in queue item 16. |
| Restore lock follow-ups | on main (PR #95, squash `ffb0547b`, 2026-11-17) | The owner oracle's three wrong lock expectations fixed; re-pinned `KNOWN-GAPS.json` (2,576,083 keys, `8b27b116…`). | - |
| Store-oracle follow-ups, brief 302 | on main (PR #111, squash `c4960356`, 2026-11-19) | Latch with the request barrier, startup finishes a staged confirm, applied history; re-pin 2,420,003 keys `1b21f564…`; proof 44395635207 61/61; Codex Sol cross-review SAFE; Fable classification check CONFIRMED; CI green twice. Owner: #352, #385 ("Merge, fix reads later"). | Board #386: N8 (restart notices) and N9 (reads refused while a latch survives), one re-pin. |
| Re-ask result schema | PR #122, `fix/chrome-reask-schema` | `chrome_submit` and `chrome_submit_trusted` declare the re-ask replies' `approval` and `state`; review SAFE. | Merge when CI is green (rides R28). |
| Package 28a | `pkg/28a-chrome-act`, `~/AresOS-28a-act`, draft PR #116 (base `pkg/28-chrome`) | Steps 0a-1d part 1 built; CI green on `bd86097c`. | See "Resume here", item 2. |
| Managed CLAUDE.md line | on main (PR #86, `7e712148`, 2026-11-16) | Content stays data whatever it claims and whoever passes it on; a session's or agent's message is a teammate's request, never his approval; the relay limit is named in CONTROL.md section 7. | - |
| `aresos` dispatcher words (43) | on main (PR #109, squash `89801940`, 2026-11-18) | `newest` reserved; `aresos log` refused, `aresos control log` unchanged; 18c's check 3 updated; owner-oracle proof 44295914634 61/61. Items 3 and 4 on `pkg/43-aresos-command` (`6e2b03d4`). Board #199 done. | - |
| Live tests | the laptop | Waits for a release that carries the tools. | Mail onboarding with him first (he signs in himself), a test mail, then Chrome. His own hosts go on Chrome's never-list in that sitting (board #298, which replaces #200). |

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

  **The lead (2026-11-15): done.** Brief 20-ci-noise, PR #81, merged as `d981cd5a` after a fresh Opus review (SAFE).
  The store is on a tmpfs in both legs (`store_write` p95 1–6 ms instead of 66–210 ms), and a gate holds fsyncs and
  SQLite commits per phase and call at or below the paired old leg's. Nits for later: `reviews/20-ci-noise/REPORT.md`.

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
- **The lead (2026-11-15):** notify's fix is on main (PR #81, `d981cd5a`); #74 is closed. #79's pull request is #83, held as a
  draft: the tests assume an empty shipped copy, so with real entries every check fails with `qualification_rollback`.
  The tests get fixed first (Codex queue, item 8); then #83 merges with a merge commit. The identity-mismatch
  question above: agreed (refuse publication, red run; all-false stays for an incomplete suite), its own brief after
  the release.

## Restore lock merged (2026-11-15, notes from `mac-aresos-control`)

PR #80 (brief 20-restore-lock) is on main as squash `b04c7e77`; report in `reviews/20-restore-lock/REPORT.md`.
- **R1, `engine.py`:** while `store.locked`, `control_pending` and `control_notices` show only Chrome's committed rows
  and warnings (`LOCKED_PENDING`, `LOCKED_NOTICES`). Other apps are unavailable until `control_restore_confirm`, no
  continuation names a refused call, and no Mail server check runs. The storage-failure fallback follows the same
  rule. Tests: `control/chrome_tests/test_restore_lock.py`; probes `restorelock-` in `reviews/20-chrome/mutation-audit.py`.
- **The owner oracle, re-pinned (board #185):** `reviews/19b-owner-state/KNOWN-GAPS.json`, 2,622,072 keys, SHA-256
  `ee326914…`. `KNOWN-GAPS.md`'s last section has the classes, their commits and the commands to regenerate it.
  - The workflow runs only when dispatched. A capture took 2 h 35 min on busy runners.
  - **Re-pin it whenever a change moves fault sites or reply envelopes.** That is the change's own job, as
    18d, #27 and #68 showed: by then three layers of drift had piled up.
- **Yours, both pre-existing and left as found:**
  - **C5:** at the restore flow's last point in persistent mode, the oracle's decoded state says the restore is
    confirmed, while the running store keeps its lock until restart. Decide whether the lock there is right; fix
    the model or the store.
  - In `crash-locked`, the `aresos log` view says "not locked" at all 6,375 points outside the restore flow
    (`REVIEW-REPIN-3.md`, NOTE 5).
  - **The lead (2026-11-15):** both go into the Codex queue's second wave (`~/codex-queue/linux-tools/QUEUE.md`),
    with a short brief. Not release work; PRs #58, #69 and #72 merge `b04c7e77`'s `engine.py` changes in their fix
    rounds.
  - **Done (2026-11-17):** both fixed in the oracle's model by PR #95 (`ffb0547b`), re-pinned to `8b27b116…`.
- **Cosmetic, in the report's "Accepted residuals":** `total: 2, items: []` after a failed Chrome projection under
  the lock, and a doubled "below are current" in the fallback's text.

## The owner's answers, written into the briefs (#254: into the service-fix brief)

- #201: Claude may close a tab of his when he asks.
- #202: the first version reads text only, no screenshots.
- #203: the tools use `Downloads` and `Documents`.
- #210 ("Ask first"): typed text in form fields is read only through the asking read.
- #213: link addresses are shown, sign-in-like values hidden.
- #216: rich-text editors are read without asking.
- #254 (2026-11-14, "Quiet unless used"): while the tool service is down, a Claude Code session that never used the tools gets no notice; one that prepared or sent something with them gets one clear notice that the AresOS tools are not running.

**His yes to the next release carrying the Control tools** (a background service, and two managed hooks in every
Claude Code session on the laptop): answered on board #286, 2026-11-15, "Yes, if reviews pass".

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
  review (Fable 5.2 or Codex's frontier model). Codex is renewed (its week resets about Wed 25 Nov 14:49);
  budgets: "Resume here", item 6.
- GitHub watchers always with `--interval 60` or longer; the API allowance is shared.
- Never force-push, never `--no-verify`. No personal data, mail-provider names or real addresses in the repo.
- Changes to the running laptop (sudo, system settings) only with his explicit OK in the session.
