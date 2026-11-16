Reviewed PR #66 at `4cdd7b28` (22d steps 1 and 2).

Reviewer: a fresh Claude agent on Fable 5.2, read-only. No owner tool, sudo, password helper or generated line ran, and no ostree, bootc or rpm-ostree command. Committed by the integrator from the reviewer's final message.

**The branch moved while I read.** Step 4's commits (`3706ad33` to `aff05fa1`) arrived in the same worktree during the review. Everything below is about `4cdd7b28` only, read from that commit's objects and tested on a copy of it in my scratch folder. The fingerprint here is `673803dc…`. Nothing after `4cdd7b28` is covered.

**In short:** the tools are right. I found nothing above a nit in `owner.py`, `media.py`, the generated lines or the payload. The route decision, the journal, the export and the quoting hold, and the tests that claim this do load the old code. What needs changing is in the guides and in two of the brief's own decisions:
- **R1, blocking for step 6:** the 10-minute rule stops the wrong process. On the laptop's sudo the window stays open, and a late stop can end the root shell while the install runs on unseen.
- **R2 to R6, should-fix:** guide wording. None touches the payload.

Step 4 is not blocked.

## What I ran

- **Read:** `AGENTS.md`, the brief, `DESIGN.md`, `REVIEW-1.md`, `STEP-0.md`, `PROGRESS.md`, and `git diff origin/main...4cdd7b28` for every tool, guide, workflow and test file.
- **Tests,** on the copy, Python 3.14, one module at a time, `ARESOS_MODEL_SCOPE=slice`:
  - `test_owner_bootstrap`: 12 OK.
  - `test_owner_equality`: 11 OK.
  - `test_owner_sources`: 12 OK (21 or 22 cuts per case, 8 cases).
  - `test_owner_path`: 48 run. The routine-box and status-row tests pass. Three link-check tests fail only on my copy, which links the large evidence folders instead of holding them (`Missing local target` under `os/manifest/ci/13`).
  - `test_owner_export`: 6 run, 3 pass. The two new `media` tests pass; the other three hit the Python 3.14 fixture issue `PROGRESS.md` names.
  - `test_owner_update`: not run, by the rule.
- **Hosted run 43673689888:** success on `4cdd7b28`, both the checks job and the full model job (read with `gh`).
- **Own checks:**
  - Version 2's and 3's `settle_tools`, loaded from `41b06513` and `58738e5e`, over a version 4 journal from both blocks. They accept it, and refuse a changed schema, phase or directory, so the old check is live.
  - `git archive 4cdd7b28:os/owner-tools/payload` gives `673803dc…`; every file checks and the file list is exact.
  - The three generated lines are byte-equal in `bootstrap.py`, `commands.json` and `docs/INSTALL.md`.
  - ksshaskpass `src/main.cpp` at `v6.7.5` from KDE's mirror (SHA-256 `e088570c…`, as in `PROGRESS.md`), compared pattern by pattern with the test's list. The laptop has `ksshaskpass-6.7.5-1.fc44`.
  - KPasswordDialog's source at the laptop's version (kwidgetsaddons 6.31.0), for how the label is shown.
  - sudo's source at `v1.9.17p2` (the laptop has `sudo-1.9.17-10.p2.fc44`; Fedora's patches not read), for the helper and signals.
  - The `setfacl` flags on a scratch folder on tmpfs.
  - The tools' own "is an owner command running" path logic over the one-window line's arguments.
- **Housekeeping:** one early run of `test_owner_bootstrap` happened in the worktree itself, before I saw it had moved (bytecode off; it left nothing). I removed my scratch files at the end.

## Findings

### R1, blocking for step 6 and one guide sentence: stopping sudo does not close the window

- **Where:** `docs/INSTALL.md:275` ("Claude stops that sudo by the process number it started: the window closes, nothing runs"); brief decision 10 (`briefs/22d-tools-without-stick.md:64`) and the walk stage "an unanswered window closed by the caller" (`:90`).
- **What the laptop's sudo does** (read in the source, not run):
  - While it waits for the helper, sudo only notes a stop signal and keeps waiting (`src/signal.c`, `init_signals`: a handler that marks the signal, with `SA_RESTART`; `src/tgetpass.c`, `sudo_askpass`: a blocking read, then a wait for the helper). The helper gets no signal, so the window stays open.
  - With SIGKILL sudo dies and the helper stays behind with its window.
  - If he then types his password, sudo checks it and does not start the command, because a stop was noted (`src/exec.c`, `sudo_terminated`). "Nothing runs" holds; "the window closes" does not.
  - sudo has no timeout for the helper: `alarm()` is set only on the terminal path (`tgetpass.c:230`). That confirms F15's guess.
- **Why it matters for him:**
  - He types his password into a window Claude said was closed. A second try puts two identical windows on his screen.
  - The case the rule does not see: he answers just before the ten minutes end. A stop then goes to the running root shell (`src/exec_nopty.c` passes the signal to the command). The shell ends, `at install` runs on alone, check and title never run, and Claude reports "nothing ran" about an install that happened.
  - The planned walk tests only the unanswered case. Its window assertion would fail and cost one of four VM runs; the late case would not be caught at all.
- **Fix:**
  - Claude stops the **helper** (the `ksshaskpass` that is the child of the sudo it started; it runs as `ares`), never the sudo.
  - sudo then ends as after Cancel, which step 0 saw: `sudo: no password was provided`, exit 1. That line is how Claude knows nothing ran.
  - If the helper is already gone, he has answered: Claude waits for the line's result and stops nothing.
  - Change the guide sentence, decision 10 and the walk stage together. The harness asserts the helper is gone, sudo's message and exit, and nothing changed.

### R2, should-fix: the export window after a STOP opens without a "go"

- **Where:** `docs/INSTALL.md:277`, `docs/EMERGENCY.md:66`; brief decision 9.
- **Why:** his rule's first condition is "you told Claude to go just now". After a STOP Claude "runs only the export line", so a second window appears that he did not say go for. By his rule he must cancel it, while "the same rule holds" expects him to type. That is the habit F2 warned about, at the moment he is least sure.
- **Fix:** "Claude copies the STOP line to you, asks for your go, and on your go runs only the export line." The same in the card.

### R3, should-fix: the root line is read from the working tree, after a check, not from the commit

- **Where:** `docs/INSTALL.md:248` ("copied from `os/owner-tools/commands.json` in that copy"); `os/owner-tools/bootstrap.py:136`. Brief decision 5 says: "The root line comes from that commit, never from the working tree."
- **What holds:** when the folder line runs, the checkout's `os/owner-tools` equals the commit (tested: checkout behind, dirty `commands.json`, dirty payload).
- **What does not:** Claude reads the file later, after his go. `/var/home/ares/AresOS` is the main checkout that other sessions pull and commit in. If it moves in between:
  - with another fingerprint, the block refuses the folder and nothing changes;
  - with the same fingerprint and a changed line outside the payload, the other line runs and nobody notices.
- **Fix:** one sentence. Claude takes the line from the commit: `git -C /var/home/ares/AresOS show <commit>:os/owner-tools/commands.json`, entry `tools-routine` (and `export-routine`). Keep the checkout check and pin the sentence in `test_owner_path`. Or record the present way as a JUDGMENT-CALL against decision 5.

### R4, should-fix: his phone check has no address

- **Where:** `docs/INSTALL.md:271`.
- **Why:** "OWNER-TOOLS.md, which you open on GitHub on your phone" is a relative link. The easy way to open it is a link Claude sends him, which is the source F3 wanted to exclude. A confused Claude that installs from a branch sends that branch's page, and the 8 characters match.
- **Fix:** print the address in the box (`github.com/Ares-Empire/AresOS/blob/main/docs/OWNER-TOOLS.md`). Tell him to keep it as a bookmark, to look for `main` in it, and never to use a link Claude gives him in that moment.

### R5, should-fix: the routine card says nothing about what Claude does with the copy, and asks for a window where none is needed

- **Where:** `docs/EMERGENCY.md:66-67`.
- **The copy:** `/run/ares-records` exists so Claude can read the records. They hold disk serials and firmware entries, and the repository is public. The design note's rule (section 3, point 2: never into the repository, a pull request or the board) is in no guide.
- **The window:** the card runs the export line after every STOP. A **STOP tools folder** comes from Claude's own line; no root command ran and no record was written. The box (`INSTALL.md:246`) rightly says Claude stops there, and the card should say the same.
- **The tools' last line:** a STOP ends with "Keep the current administrator session open" (`owner.py:2922`). On this route there is none. One clause in the card: that line is for the console, and nothing is lost here.

### R6, should-fix: nobody tells him the stick falls behind

- **Where:** `docs/INSTALL.md:283`, `docs/EMERGENCY.md:62`.
- **Why:** after the routine box the stick in the drawer holds version 2.
  - It still takes records, and export then prints a line no guide names: `The stick holds tools this laptop installed before (SHA256 …), not the installed ones` (`media.py:171`).
  - It cannot install the current tools until it is written again.
  - Decision 12's "Claude asks for the stick about once per release" exists only in the brief.
- **Fix:** one sentence in the routine box and one in "A tools command stopped".

### Nits

- **N1, `bootstrap.py:103`:** `bash` after sudo is not absolute, though the brief's reason for `/usr/bin/sudo` applies to it too. Today sudo's `secure_path` covers it (step 0's journal shows `COMMAND=/usr/sbin/true`, which only that order explains), but nothing in `os/config` or the image checks pins it. `/usr/bin/bash` costs a re-pin, no payload change.
- **N2, `bootstrap.py:137-139`, docstring `:123`, `INSTALL.md:246`, `EMERGENCY.md:67`:** "changed nothing" is not exact. A failed `git archive` or a wrong pinned fingerprint comes after the folder was emptied and refilled. No root line accepts a half-written folder (it checks the list and every hash itself). Either check the commit's `SHA256SUMS` before `rm -rf`, or say "nothing was installed".
- **N3, `owner.py:206`:** with stdin closed (not `/dev/null`) Python has no `sys.stdin`, and `caller()` raises an error `main` does not catch. On the folder route that happens when the receipt is written, after publication: a traceback, no record, and the line prints "STOP bootstrap … refused" over tools that are published. The next install finishes it. Fix: `sys.stdin is not None and sys.stdin.isatty()`. Changes the payload.
- **N4, `media.py:106`:** if `setfacl` is missing or fails, export STOPs after the copy is complete with `Operation failed: setfacl; do not reboot` (`owner.py:312-318`). The copy stays root-only, which is safe, but "do not reboot" is wrong advice there. Better: answer the "only root can read it" line with the reason. Changes the payload.
- **N5:** the helper reads `SSH_ASKPASS_PROMPT`. With `confirm` it shows Accept and Cancel with no password field and sends "yes"; with `none` only Cancel. sudo refuses either way. Clearing it in the prefix would make the window independent of the caller.
- **N6, `docs/OWNER-TOOLS.md:1-2`:** GitHub shows lines 1 and 2 as one paragraph, so on his phone "line 1" is not a line. A blank line between them fixes it (brief and test change together).
- **N7, `INSTALL.md:230`:** "brings its copy of the repository to the announced commit" is the shared main checkout. Say how: a fast-forward pull, never a reset or a checkout over other sessions' work.
- **N8, `INSTALL.md:228`:** review 1's nit is still open: other sessions run no owner command meanwhile, or the install STOPs.
- **N9, `INSTALL.md:277`:** a STOP prints two STOP lines (the tools' and the block's). "The STOP line" should be "every STOP line".
- **N10, `bootstrap.py:41-42`:** only two routine lines exist. Decision 3 says the other owner commands keep one line each. Fine if 22d is tools-only; say so in the report.

## The seven questions

**1. The route.** Nothing I tried crosses it.
- `bundle_source` (`owner.py:183-193`) is read once, in `main` (`:2876`). The stick block makes `m` before the mount and keeps it through install. The folder block's private folder is a fresh root-only `mktemp -d`, so nothing else can put an `m` there.
- A folder named `m` inside the bundle or in his home is not beside the private copy. A linked tools folder is refused by the block. Anything named `m`, also a dangling link, gets the stick's rules.
- A plugged-in stick is never queried on the folder route (the test fails on any label query).
- `at install` through the installed entry follows the folder rules: "already installed" for the same bundle, the refusal for a first-install shape, and the stick-only refusal for a stick-begun update.
- Resume: all four pairs at each of the 30 events. Stick to folder refuses with nothing changed; folder to stick completes; a journal without `source` counts as stick.
- The stick route's lines are unchanged. Two loosenings are the brief's: a folder-begun update finishes from any stick holding this bundle, and export accepts retired bundles.
- The one-window line names `/var/lib/ares/at` in its script, but its own sudo and shell do not count as a running owner command, so install does not refuse its caller.

**2. Journal and older tools.** Yes to both.
- Versions 2 and 3 read only schema, phase, previous, manifest and previous_directory.
- Before publication version 4 writes the journal's `source` and nothing else new (names and record bytes compared at every cut).
- The tests load the old code from its commits; my negative controls confirm the old check is live.

**3. Export.**
- The folder is root's, 0700, files 0600, each read back.
- The grant, seen on tmpfs: folder `r-x`, files `r--` for the one uid, nothing for group and others.
- An unset or root login uid makes no grant and prints "only root". A missing or failing `setfacl`: N4.
- The three lines never say `SAFE TO REMOVE` or `ARESTOOLS`.
- On a stick a foreign bundle is refused (fingerprint not accepted). A tampered one fails its own hashes. A retired folder counts only if its bytes verify to its name.

**4. The generated lines.**
- Quoting holds. The label is held to letters, digits, spaces, commas and one colon by a full match, the fingerprint to 64 hex, the script to no single quote; all pass through `shlex.quote`. The commit hash is checked before use and always quoted.
- The folder line refuses a commit not on `origin/main`, a short or missing hash, a checkout that is behind or dirty, an unreachable origin and a wrong fingerprint (ran).
- The root line from the commit: R3.
- `-k`, `-A` and the fixed `SUDO_ASKPASS` hold against the caller's environment. What the environment can change is the window's look (N5, the display, the language of the title bar), and each case fails closed.

**5. The labels.**
- The test's 16 patterns equal the source at `v6.7.5`. The 16th writes `\n` as a regex escape where the source has a real newline; it matches the same.
- No label can match: every pattern needs a quote or a trailing ": ".
- The labels are 70 and 47 characters; step 0's was 42. The window wraps its text and does not cut it (KPasswordDialog: word wrap on). I could not look at a window; step 6's screenshot should show the 70-character one.
- The window reads the label as rich text, so `<` or `&` would be markup. The label rule already excludes them; say so in its comment.

**6. The guides.**
- His rule is clear as three points. The limit is said honestly and in plain words, with the stick as his way out.
- The quoted lines equal what the tools print (uid 1001 is this laptop's `ares`).
- The emergency route is intact; the stick card gains one true sentence.
- Open: R1, R2, R4, R5, R6.

**7. Review 1's should-fixes.**
- **Covered:** F2 (one line, one window), F3 (the page and its test), F4, F7 (generated, pinned, tested), F8, F9, F10, F12 (the card exists), F17.
- **Not fully:** F15 (R1), F7's "from the commit" (R3), F2 for the export window (R2).
- **For step 6:**
  - The folder line cannot pass against GitHub's main for a commit that is not merged, so the VM needs a stand-in origin whose main holds it.
  - Assert that `ares` can read `/run/ares-records` and another account cannot.
- **For step 4:** the guide fixes ride without another fingerprint. N3 and N4 would change the payload.

CHANGES-NEEDED
