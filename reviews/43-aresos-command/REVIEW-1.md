# Review 1 of the design note for package 43, the `aresos` command

Reviewed `reviews/43-aresos-command/DESIGN.md` at `38d9d724` (draft PR #82).

Reviewer: a fresh Claude agent on Fable 5.2 that did not write the note. Review only: no code, guide or test changed, nothing committed or pushed.

**How it was checked.** Read `AGENTS.md`, `CLAUDE.md`, `STATE.md`, the note, then the code it cites. Code references below are to main at `937a1868`. The owner tools, the guides and 22d's files there are byte-identical to the note's `89bc0658` (compared with `git diff`), so the note's `owner.py` line numbers still hold. No owner tool, `sudo`, rpm-ostree, bootc or ostree command ran, and no `os/tests/test_owner_*` module. Two harmless Python checks ran as `ares` (finding B2); one of them ran from a folder of this worktree with bytecode off and left nothing behind.

## Verdict

**READY WITH CHANGES.**

The main decisions hold: the choice lives in the tools (option B), the guard sits inside `update`'s own checks, the dispatcher is a table that never reads a tools answer, and the model gets a judgment (I1) that states the one thing that must never happen. Almost every cited line is right.

Two things must be fixed in the note before step 1 is briefed, because both change what step 1 builds:

- **B1:** the rule has no case for "a change waits for the restart", so the most likely second run prints a false announcement and then refuses.
- **B2:** the tools' root steps import Python modules from the caller's working directory, and this package is the first route that starts them from Claude's working directory.

S1 to S8 should be settled before the step they touch (named in each finding). The nits need no decision.

## BLOCKING

### B1. `aresos update` after a staged update (or a queued return) announces a forward that is false, then refuses

- **Where in the note:** D2 (lines 59-67), D4 (line 71), the announcement table (lines 178-183), I1 to I3 (lines 78-81).
- **Where in the code:** `os/owner-tools/owner.py:756-758` (`newest()` reads only installed rows), `:1325-1326` and `:1341` (the journal state `pending`), `:1628-1631` (`may_change` refuses while a change waits), `:2959-2960` (the last line of every STOP).
- **What happens.** After `aresos update` has staged T and before the restart, a second `aresos update` meets this state: N runs, the staged row is first in the list, the journal says `pending`. Rule 1 does not apply (`pending` is neither `retry` nor `complete`). Rule 2 does not apply (by the note's own words, line 9, N does not start next). So rule 3 applies. The run prints:
  - `Update: a newer AresOS is installed already, <the running AresOS>; going forward to it. Nothing is downloaded and nothing is removed`
  - then `STOP: The update to … waits for the restart: restart first (sudo /var/lib/ares/at reboot), then run this command again; nothing changed`
  - then the tools' last line, which says `do not reboot`.
- **The same happens after `aresos previous` or `aresos rollback` without a restart:** a forward is announced, then refused with "waits for the restart".
- **Two more states get a wrong first line** from the one forward wording:
  - N starts next but another system runs (a boot-menu start): "going forward to it", then `… already starts next; nothing changed` (`owner.py:1685-1686`).
  - N runs but another system starts next: "a newer AresOS is installed already" names the system that is running.
- **Why it matters.** Nothing changes on disk. But this is the state right after every update, when Claude or the owner is most likely to run the word again, and the owner's intent (#195, #262) is that the command says which of the two it does. Here it names a newer AresOS that does not exist, says it goes forward, does not, and ends with "restart first" beside "do not reboot". The model would not catch it: nothing is staged (I1), the stop names `reboot` (I2), and there is no change to come before (I3).
- **Fix.**
  1. Give D2 a complete table, decided from the one survey, in this order:
     - a survey STOP passes through with no announcement, as now;
     - `retry` or `complete`: continue (see S6);
     - a change waits for the restart (`settled == 'pending'`, staged or reorder): nothing to do now. One line that says what waits (for example `Nothing to do now: the update to <reference> is staged and starts at the next restart`), no inner word, a PASS, no STOP;
     - N runs and starts next: install T, or "Nothing to update";
     - N starts next and another system runs: nothing to change, with forward's two "already starts next" lines;
     - N does not start next: forward, with a first line that fits what runs: an older AresOS or plain Bazzite ("a newer AresOS is installed"), or N itself ("this AresOS runs, but <name> starts next; making it the next start again").
  2. Print the announcement after the chosen word's read-only checks have passed (`may_change`, or `may_stage`, the guard and the stored login) and before its first change (for the install: before the signature check, which takes minutes). Then a refusal is never preceded by "going forward" or "installing". A small hook passed into `update()` and `select()` does it; their lines and journal stay as they are.
  3. Add a fourth judgment to the model: on every `newest` edge, an announcement is followed by its change (or a cut), never by a refusal; and no forward announcement is printed where the ledger's N runs and starts next or a change waits.
  4. Add the rows to the unit table, and one stage to 43's VM run: `at newest` a second time after stage 1's staging, before the restart.

### B2. The tools' root steps import Python modules from the caller's working directory

- **Where in the note:** D7 (line 113), D10 (line 146: "everything it does `ares` can do by hand"), D11 (line 148).
- **Where in the code:**
  - `os/owner-tools/at:10` starts `owner.py` with `-I` and never changes directory;
  - `os/owner-tools/owner.py:377-379` starts each release step as `/usr/bin/bash -seu` with the inherited directory;
  - `os/release/start-next.sh:6` and `os/release/update.sh:4` run `python3 - <<'…'` without `-I` and import `json` and `subprocess`.
- **What happens.** For a script read from stdin, Python puts the current directory first on its module path. `sudo` keeps the caller's directory (22d's step 0 shows `PWD=` of the caller in sudo's journal line). So with `aresos update`, `aresos previous` or `aresos rollback`, root imports any file in Claude's working directory that has the name of a standard module these steps load after startup. On the laptop's Python 3.14.8 those are about twenty, among them `json`, `subprocess`, `signal`, `enum`, `re`, `locale`, `warnings`, `threading`, `select` and `math`.
- **Checked** (as `ares`, no root):
  - in an empty scratch folder with a `signal.py`, `printf 'import json, subprocess' | bash -seu -c 'python3 -'` ran that file; with `python3 -I -` it did not;
  - this repository has such a file: `control/aresos_control/warnings.py`. From that folder the same two imports fail with `ImportError` out of the repo's `warnings.py`.
- **Why it is new with 43.** The console route runs in a `sudo -i` shell (directory `/root`). 22d's install line changes into its root-only copy before `at` runs (`os/owner-tools/bootstrap.py:58-59`), and its export line runs no such step. This package is the first to start `start-next.sh` and `update.sh` as root from the directory Claude happens to work in.
- **Why it matters.**
  - By accident: a reorder or an update fails after its journal intent was written, with `Shared step failed: …; preserve diagnostics and do not reboot`, because of a file in the project Claude had open.
  - On purpose: a folder from someone else (a cloned project, a download) gets root on the laptop without Claude showing a wrong window or running a wrong command. The honest window "AresOS: go back to the previous AresOS at the next start" and the owner's real password are enough. That is below the line the note draws for the window ("stops accidents and a Claude that acts without asking").
- **Fix,** in step 1, in the tools (the dispatcher is not the boundary, and the full path at a desktop terminal has the same hole):
  1. `at` changes to `/` before it starts Python; `Step` and `Host.read`/`Host.mutate` pass `cwd='/'` (`owner.py:312`, `:326`, `:377`).
  2. The stdin scripts in `os/release/*.sh` and `owner.py:1426` start as `python3 -I -`. They are bound, rehearsed files, so they go on the waiting list, and 43's own VM run walks them again.
  3. A test that runs a real step from a folder holding a marker-writing `json.py` and `subprocess.py`, and requires that neither ran.
  4. D11 gains one sentence: the environment is built from nothing and the tools run from `/`, so no directory or variable of the caller reaches a root step.

## SHOULD

### S1. A failed update is repeated without anyone deciding, and its one-time line prints after the new staging

- **Where:** note D2 rule 2 (lines 62-64); `owner.py:1327-1330` (the survey archives the journal as not applied and only notes the line), `:2933` (notes are printed with the result, after the command); `docs/EMERGENCY.md:23` and `:27` ("Help decides each repeat", "Never repeat the update without Help").
- **What happens.** An update that did not finish at shutdown leaves the old release running, with the list as before. If `aresos update` is the first word afterwards, its survey closes the journal, rule 2 applies (N runs and starts next, T is not installed) and it stages T again in the same run. `Update to … was not applied` then appears after `PASS newest`, above `Signed exact release staged`, where it reads as if it were about the new attempt. The card's check-first rule is skipped by the word the guide tells Claude to run "after an announcement".
- **Fix.** When the survey of `newest` has just closed a staging journal as not applied: print that line at once, change nothing, end with a PASS and a line such as `Nothing changed: the last update did not finish at shutdown. See EMERGENCY, Failed or bad update; aresos update repeats it`. The repeat is then a second, deliberate run. More generally `newest` prints the survey's notes before its own announcement, so the screen reads in the order things happened. One ledger branch, one unit row.
- **Before:** step 1.

### S2. `aresos check` needs a running `foot`; decide that now, not at R29's rehearsal (LEAD 8)

- **Where:** note line 96 (`check`: "yes") and LEAD 8 (line 276); `owner.py:2016-2017`; `os/config/usr/share/aresos/labwc/autostart:5`; `os/config/usr/libexec/aresos-desktop:35`; `os/ci/tools_local.py:486`.
- **What is true.** From release 28 the session starts the Minecraft desktop, not a terminal. The supervisor shows a `foot` only in SETUP, AUTH_REQUIRED and RECOVERY. On the laptop, in the hub, no `foot` runs unless the Terminal app is open, so `aresos check` STOPs with `Read failed: pgrep -u ares -x foot`. That STOP sends Claude into the export routine, on the word the emergency card's new sentence puts first.
- **Why R29's stage 2 will not show it.** The harness types its caller line into `foot`, and a VM without a Minecraft account sits in SETUP, which shows a `foot`. Every rehearsal has one. Only the laptop does not.
- **Fix.** Step 1 changes the tools anyway, so decide there: either `check` stops requiring `foot` on releases whose session is the Minecraft desktop (the release record can say so, as it does for `daily_wheel`), or the guide box makes an open Terminal app a precondition and the dispatcher's table says so. With the first, 43's VM run does one `at check` with no `foot` open.
- **Before:** step 1.

### S3. "The image checks run in the hosted checks" is not so; step 3 needs a check build

- **Where:** note line 233 and D16 (lines 166-168); `os/ci/check-image.sh:13` (the only caller of `os/ci/image-checks.sh`); `.github/workflows/os-image.yml:207` (the `check-build` job) against `:93` (the checks-only job runs the unit tests only).
- **Why it matters.** As planned, step 3's new image checks (owner and mode of both files, the refused word as `ares`, the `ksshaskpass` version pin) would run for the first time inside R29's release build. The dispatcher, the helper with `timeout`, and D11's variable list would first meet a real `sudo -A` in R29's rehearsal.
- **Fix.** Step 3 ends with one `check_build=build` run on the branch (throwaway, needs no owner OK) and the budget gains it. That run boots the image once in a VM; if it is cheap there, drive one window with the made-up `ares` password the image checks already use: the label, Cancel, and `sudo -n true` refused afterwards. Then D9 and D11 are shown before merge. Say exactly what the laptop try of step 0 runs: the D11 environment (`env -i` plus the listed variables), a copy of the two-line helper, a short timeout, and `/usr/bin/true` behind it.
- **Before:** step 3.

### S4. The build steps do not say how they stay green under the binding rules

- **Where:** note section 8 (lines 239-248); `os/owner-tools/bundle.py:50-58` with `os/tests/test_owner_equality.py:48` (the payload must equal the sources); `os/tests/test_checkout_sources.py:25-31`, `:107-148`; `os/manifest/ci/16/pending-rebind.json` ("decision"); `docs/INSTALL-STATUS.md:27-28`; `.github/workflows/os-image.yml:46`.
- **What the steps will meet:**
  - Step 1 says "no payload or pin yet", but the equality tests fail as soon as `owner.py` differs from the payload. 22d refreshed payload and pins in its first step and again later.
  - `owner.py`, `at`, the release scripts and the guides are bound files. Each change needs its row on the waiting list (`rebind.py pending`).
  - While any status row says **VM REHEARSAL PASSED; NOT ON THE LAPTOP**, no file under `os/owner-tools/`, `os/release/` or `docs/` may wait, and the payload must be the newest rehearsal's tools. Two rows say that today, and release 28's row will after its rehearsal. So steps 1 and 4 cannot be green before the laptop has run what the standing rows promise, or before the lead moves those rows on.
  - `newest` joins `unwalked_commands` until 43's run walks it; `REHEARSED_TOOLS` needs 43's result field; the workflow maps branch names to rehearsal packages and modes, so `pkg/43-aresos-command` needs its entries.
- **Fix.** Add a "Needs" entry and one sentence per step: step 1 refreshes the payload and its pins (they move again in step 4), records the waiting rows, and names the tests that stay red until step 6, if any; steps 1 and 4 start only when no row says the phrase above (after the laptop sessions, or after the lead's decision on those rows); step 6 lists the workflow and ledger entries.
- **Before:** step 1's brief.

### S5. No text may route the owner from `aresos update` to the inner `update`

- **Where:** note line 109 (root or no desktop session: "refused with the full-path command for the console"), line 73 (messages keep the full path), line 185 (a tools line that says `aresos update`), tests at lines 158-160.
- **Why.** `aresos update` and `sudo /var/lib/ares/at update` differ in exactly the danger state of #263. The note does not say which full path the refusal for `update` prints; `at update` would be the natural mistake.
- **Fix.**
  - The root and no-desktop refusal for `update` prints `sudo /var/lib/ares/at newest`. A test requires that no string the dispatcher can print or exec contains `at update` or `at forward`.
  - Line 185's sentence is built with `typed('newest')`, like every other tools line. The tools cannot know whether the next start has a dispatcher (the note's own fact 7), and the forward may run on plain Bazzite.
  - The guide's box gets one rule for Claude: a tools message that names `sudo /var/lib/ares/at <word>` means `aresos <word>` from Claude's terminal, and for `update` and `forward` always `aresos update`.
  - Define I2 by `typed('update')` and `typed('forward')`. As worded it also meets `owner.py:1323-1324` (reachable from `newest`'s own survey when an intent matches neither list) and "then update again" at `:1641`.
- **Before:** steps 1 and 3.

### S6. Case 1 and the guard: "restart" against "do not reboot", and a removal that is not named

- **Where:** note D3 (line 69) and the "Continue" row (line 182); `owner.py:1323-1324`, `:1791-1795`, `:1809-1810`, `:1911-1912`.
- **What.**
  - In `retry` on an older AresOS the run prints `Update: continuing the interrupted update …` and then the guard's refusal. Decide before announcing (B1, point 2).
  - The guard says "restart, then run it again". Every other word says, in that same state, "do not reboot; run … update to continue it", and a stop routine that did not finish has said "Do not reboot; export records and get help". Do not tell him to restart: say that this command does not continue an update begun on the older AresOS, that nothing changed, and point to the card.
  - In `complete` on an older AresOS, `newest` records a staging that removes the newer AresOS at shutdown. Nothing is staged by this run, so I1 holds, but the removal lines of `:1842-1849` are not printed on this path. Print them in the "Continue" case.
  - After the second `may_stage` the guard comes before `:1810`. If the list changed during verification, he gets the guard's text, not "Deployments changed during verification". Put the guard after that line.
- **Before:** step 1.

### S7. Control: more callers of `/usr/bin/aresos` than "one entry and its pin"

- **Where:** note D12 (line 151); on `origin/pkg/18c-image`: `os/build.sh:270` (the build runs `aresos --help`), `os/ci/control/actions.py:100`, `control/ci/image/mail_flows.py:56`, `control/tests/test_integration.py:359`, `os/ci/image-checks.sh:821-823`.
- **Why.** In the image these keep working through the hand-over. The build-time call needs the dispatcher in place before it runs, and Control's own integration test installs the wrapper at `/usr/bin/aresos` in an environment that has no dispatcher. The branch has also moved since the note's `84f45c28`.
- **Fix.** Step 0's note to `linux-tools` lists these five places; step 3 names the build order. `aresos admin mail account add` needs the terminal on stdin (`control/aresos_control/cli.py`), so one dispatcher test passes a terminal through the hand-over.
- **Before:** step 3.

### S8. D13: a different line on main is not an announcement

- **Where:** note lines 172-174; `docs/INSTALL.md:224` ("Claude installs only that commit, never the newest one on GitHub by itself").
- **What.** "Different: newer tools are announced. Claude installs them by 22d's route" reads as if the difference were the go. 22d's route needs the announced commit from the lead's board note and the owner's go.
- **Fix.** Reword: a different line means main carries other tools; Claude tells him and waits for the announcement and his go. State the order after an announcement of a new release: tools first, then `aresos update`, so the "Nothing to update" window is not spent just to learn the version.
- **Before:** step 4 (guide wording).

## NIT

- **N1, D1 (line 54):** "the decision and the act share one survey" holds only if `newest` hands its survey to the inner word. As built, `update()` and `forward()` each read again (`owner.py:1788`, `:1958`). Say which; the guard covers the staging side either way.
- **N2, D7 (line 113):** "which nobody has run" is not so. `sudo -k; sudo /var/lib/ares/at layout proof` is typed from the non-root tty4 login (`docs/INSTALL-PROCEDURES.md:18`) and has passed in the VM since qualification 21. LEAD 4 can be answered now: either form works; with B2's change of directory the `bash -c` form is as good.
- **N3, D9 (line 137):** an update can take about 70 minutes, not 30: verification and staging each have the 30-minute limit, plus the stop routine. Give `timeout` a `-k` so a helper that ignores TERM still goes.
- **N4, D11 (line 148):** the list has no `HOME`. Qt then takes `/` as the home folder, and the window may look different from step 0's. Take `HOME`, `USER` and `LOGNAME` from the account database, not from the caller, and try both variants in step 0.
- **N5, no-change runs and `aresos reboot`:** "Nothing to update" and "already starts next" save no title, and `reboot` refuses a stale one (`owner.py:1977-1978`). The guide box should say that `aresos title` (one more window) may be needed first.
- **N6, `rollback` from the desktop (LEAD 2):** plain Bazzite has no `ares` account, so after `aresos rollback` and the restart there is no Claude and no `aresos`; the way back is typed by the owner at the console. The box should say so, and that "roll back the update" in his words usually means `previous`.
- **N7, lines 71 and 64:** "nothing else in `main()` changes" and "the saved record gains `chosen`" do not both hold; `chosen` belongs in the STOP record too. "Nothing is journalled" is right for the journal, but a `…-newest.json` record is saved.
- **N8, references:** on main the ledger's `steps()` is now `os/tests/ways_back_ledger.py:306-318` (22d moved it by six lines). `test_ways_back_model.py:444` is the list of words the 22c rehearsal typed, used by its replay; `newest` belongs there only if 43's run gets a replay. Put `newest` after `update` and `forward` in both loops of `steps()`, so the slice's breadth-first order and its pinned state count stay and only the edge counts move.
- **N9, offline:** a missing network or a vanished release comes out of `aresos update` as "Registry login missing, expired or unreachable: run … login" (`owner.py:1001-1004`), and `login` is refused from Claude's terminal. One sentence in the box: check the network first; a new login is typed by him at the console.
- **N10, two runs at once:** the second gets "Another owner command is running" with the STOP ending. The box should class it with Cancel, so it does not start the export routine.

## What was checked and holds

- **Facts 1 to 9** against `owner.py`, `bootstrap.py`, the sudoers file and its image check, 22c's review 4, 22d's step 0 and reviews 2 and 4: correct, apart from the points above.
- **The danger state** is reachable in the model as it stands (`previous`, restart, a bundle for 28), so I1 is judged on real edges.
- **`RELEASE_INSTALLED` and `FORWARD_FIRST`** cannot come out of `newest` under D2.
- **Older tools** answer `newest` with "Choose a documented owner command" (`owner.py:2910`). On release 29 the tools always know the word, because the tools that install release 29 are built after this package.
- **The lock** covers two runs at once (`owner.py:97-110`, `:2904`); a second password window only costs a refusal.
- **The nine labels** fit 22d's character rule and are under 70 characters. The laptop has `ksshaskpass` 6.7.5, as D16 pins.
- **D9's reading of `sudo`** matches 22d's review 4 (a helper that ends without output is the Cancel path).
- **The release diff** explains the two `os/config` files if they are executable in git (`os/ci/release_diff.py:212-229`).
- **Signature and digest checks** are untouched: `newest` reaches staging only through `update()`, which verifies as before.
- **Step 6's plan** (R28 published, its rehearsal mode on main, a made-up next release for stage 4) fits the harness 22d and brief 42 leave behind.
