# Package 22d: the owner tools without the stick, from Claude's terminal

Brief: `briefs/22d-tools-without-stick.md` (empire brief 291). PR #66, branch `pkg/22d-tools-without-stick`. Builders:
Claude agents (step 1 on Fable 5.2, the other steps on Opus 5.5). Reviews 1 and 2 on Fable, 3 and 4 on Opus; the final
review before the laptop (review 5, Fable) found it SAFE, and step 8 closed its findings (main merged in, this text).

## Done

**What 22d gives the owner.** New owner tools no longer need the USB stick, Windows or the black console. Claude runs
two lines in its own terminal. The first (as `ares`, no window) fetches GitHub's main, checks that the commit announced
on the board is on it and holds exactly the tools with the published fingerprint, and puts those tools in a folder. The
second opens a small password window on the laptop's screen. When he types his password there, the tools install,
then check and title run, all from that one password. Before typing, he compares the 8 characters in the window with
line 1 of `docs/OWNER-TOOLS.md`, opened on his phone from his own bookmark. Records can be exported the same way; without
a stick they go to `/run/ares-records`, on this laptop only. The stick and the console stay as the emergency route,
and the very first installation stays on the stick. Installing from the stick keeps every rule; beside it two things
are new: `export` to the stick also takes a stick holding tools this laptop installed before (with a line saying so),
and an update begun from the folder may be finished from a stick. The window stops accidents and a Claude acting
unasked, not a tricked Claude; the guide says so in plain words.

- **The tools** (`os/owner-tools/owner.py`, `media.py`, tools version 4): the start block that ran decides the route
  (stick: every old rule; folder: no console, no stick); the journal keeps its schema and adds `source`; a folder-begun
  update resumes from either route, a stick-begun one only from that stick; the receipt names the source and the caller
  (login uid, terminal or not); export without a stick copies to `/run/ares-records` (root's, readable by his uid), and
  a stick holding tools this laptop installed before is accepted with a line saying so. Review 8's findings 2 and 5: a
  cleanly stopped update closes its record, and a layout trial from before a restart names `layout abandon`.
- **The lines** (`bootstrap.py`, `commands.json`): Claude's folder line, the tools-only routine line and the routine
  export line, generated, pinned and tested; the routine line is taken from the announced commit itself.
- **The guides:** `docs/OWNER-TOOLS.md` (new), the routine box first in `docs/INSTALL.md`'s update route, a routine STOP
  card in `docs/EMERGENCY.md`, the 22d row in `docs/INSTALL-STATUS.md`.
- **The rehearsal** (`os/ci/tools_local.py`, mode `tools-local`, ledger `22d`): the owner's route in a VM, with a
  stand-in caller in his desktop session and no terminal, a dialog driver that checks the window before typing.

## Verified

**The VM runs** (mode `tools-local`, from the laptop's state: R27 by tools version 2, R13 and the pinned stock):

| Run | Head | What happened | Fix |
|---|---|---|---|
| [43690565301](https://github.com/Ares-Empire/AresOS/actions/runs/43690565301) | `cb2a1eec` | Stopped before the VM: release 27's check compared its image sources with this checkout, which holds unreleased image changes from main | Step 6c: in this mode release 27's facts are read from its own source commit `b216f28f`; the switch job gets the mode as step env (`7889ba5e`) |
| [43699785728](https://github.com/Ares-Empire/AresOS/actions/runs/43699785728) | | Stopped at the stand-in origin's setup: the bundle carried `main` but no `HEAD`, so the clone had nothing to check out | `1b733a4f`: the stand-in names `main` as `HEAD`; the checkout clones `--branch main`. Then step 6d (a read-only preflight): the password or Escape could reach foot before the window existed; now the driver waits until the window has settled and a picture shows it, and the launcher is retried once |
| [43714310216](https://github.com/Ares-Empire/AresOS/actions/runs/43714310216) | `fca1d2a1` | Passed almost all of the walk; stopped at the second stick removal in one boot (`repeated tools-stick disconnect`): the USB health check excused one removal per boot | Step 6e: each requested removal excuses one disconnect of its own port after it; VM dispatch cap 4 to 6 (integrator) |
| [43737933979](https://github.com/Ares-Empire/AresOS/actions/runs/43737933979) | `89bc0658` | **Passed** | |

Run 4, stage by stage (captures in `reviews/22d-tools-without-stick/runs/tools-local-43737933979/`):
- **Version 3 refuses:** its window (label `2084c786`, wrapped onto two lines), password typed, then `STOP: Tools update
  runs only from the physical recovery console` and `STOP bootstrap: verification or install refused`; nothing changed.
- **Cancel:** Escape in the window; `sudo: no password was provided`, exit 1; nothing changed.
- **Unanswered:** the caller closed the window after 30 s (standing in for the 10 minutes) by stopping only the password
  helper; the same line and exit; nothing changed.
- **Cut:** password typed, the install frozen between the copy and the switch, hard reset; after the restart the old
  tools' `check` passed and the record still named the new tools.
- **Install:** the next window resumed it: `PASS install` (version 2 to 4), `PASS check`, `PASS title`; the receipt
  names `source: folder`, login uid 1001, no terminal; `sudo -n true` refused afterwards (no password kept).
- **Tamper:** one changed byte in the tools folder: `STOP bootstrap: verification or install refused` before any tools
  code ran; nothing changed.
- **Stick with a next version:** a test bundle, version 5 (`4125f556…`, never published), installed from the stick at
  the console by version 4's own stick route.
- **Export:** without a stick through the window: `PASS export`, 42 files under `/run/ares-records`, `ares` reads them,
  another account cannot; to a stick holding version 2: accepted with `The stick holds tools this laptop installed
  before (SHA256 851eb742…), not the installed ones`.
- **End:** restart, check and title passed; both Windows starts (unattended and detached) reached the Windows marker.
- In every window: title bar **Enter SSH Credentials**, the helper's argument equal to the label, the window settled
  (3.0 to 4.6 s) and visible (25 to 28 % of the screen's centre changed), no keyring process started; the caller had
  no terminal. Every protected-disk audit equalled the baseline over 15 starts.
- The announced commits were a stand-in GitHub inside the VM whose `os/owner-tools` tree equals the real commit's
  (`89bc0658` ↔ stand-in `7e018ac5`, tree `73fb5929`; version 3's `58738e5e` ↔ `49de19e8`, tree `b322a88e`).

**Hosted checks:** checks-only run [43729592775](https://github.com/Ares-Empire/AresOS/actions/runs/43729592775) on
`89bc0658`: green, 1613 tests, full model, nothing skipped. Budget at run 4's dispatch: 776 of 2400 minutes, 11 of 20
checks runs, 4 of 6 VM dispatches. Step 8 merged main into the branch: that head (and the commit announced on the
board) needs its own green checks-only run with the full model; run 43755153393 tested `7ef03022`, before the merge.

**Locally** (Python 3.14, one module at a time, slice model): every step's modules, listed in each step's section of
`PROGRESS.md`; after the record step `test_checkout_sources`, `test_tools_local_wiring`, `test_owner_path`,
`test_owner_step_limits`, `test_owner_bootstrap`, `test_owner_equality`, `test_owner_sources`, `test_ways_back` and
`test_ways_back_probe`; after step 7b `test_checkout_sources`, `test_owner_equality`, `test_owner_path`,
`test_tools_local_wiring`, `test_ways_back_probe` and `test_owner_sources`; after step 8 (the merge) those six
and `test_owner_bootstrap`, and main's `test_ways_back_model` and `test_aresos_desktop` (they read the workflow and
the ledger) and `test_journal_ready` (it reads `os/ci/vm.py`). `test_owner_update` runs hosted only.

**The fingerprint:** tools version 4 is `dcbc375faa4b269bacaf316c5ddc24503b9773b2538bcd017065ce8e312597be` (SHA-256 of
the payload's `SHA256SUMS`). It is pinned, and tests hold equal: `docs/OWNER-TOOLS.md` (line 1 `Owner tools version 4:
dcbc375f`, then the full value), `os/owner-tools/commands.json` (= `bootstrap.command` and `bootstrap.lines`), the stick
blocks, Claude's folder line, both window labels and the PASS lines in `docs/INSTALL.md`, `docs/EMERGENCY.md` and the
22d row of `docs/INSTALL-STATUS.md`. Run 4's result names the same value. The record step rebound 263 sources to
`os/manifest/ci/22d/source-bindings.json`; six bound files changed since wait on the list: five test files (three by
the record step, two by step 7b) and `os/ci/vm.py`, which main's package 23b changed (merged in by step 8). A test now
holds this chain (package 22c's review 8, finding 3): while a status row says **VM REHEARSAL PASSED; NOT ON THE
LAPTOP**, nothing under `os/owner-tools/`, `os/release/` or `docs/` may wait (what the laptop gets; a harness, workflow
or test file may wait for the next rehearsal), each such row names the tools its run rehearsed, and the newest
rehearsal's tools (run 4's) equal the payload's. 22d's three lines (folder, routine,
export) count as walked: the run's caller ran them, and they left the list of unwalked commands.

## Not verified

- **The laptop.** Nothing of 22d has run there; the owner's session comes after merge ("Try this" below).
- In the VM: the real 10 minutes (30 s there), the real GitHub (a stand-in origin with the same tools tree), a run with
  stdin closed (not walked), and a keyring only as processes (none started).
- **No uninterrupted install from version 2 to 4.** In run 4 the copy ran before the cut and the rest after it, so
  every phase ran on a real system, but never in one run. The uninterrupted folder install runs on fakes
  (`test_owner_sources`), and in the VM only by the stick route (version 4 to 5). Enough, but not the same run.
- **Claude's Bash tool as the caller.** In the VM a program read the line and ran it; on the laptop Claude does that by
  the recipe in "Try this", whose hashes are the lines run 4's caller ran.

## JUDGMENT-CALL (for the owner: the words only)

He decides wording; everything else is settled. Changing any of the ten wordings before the laptop session means a new
VM rehearsal (one of the two VM runs left, then its record step), because all ten live in the tools, `commands.json` or
the guides, which may not change while 22d's row says the VM rehearsal passed. The reviewer advises keeping all ten
for this install; wishes ride with the next tools version, which release 28 needs anyway. (The owner answered on board
#307, 2026-11-15: "Keep as written"; all ten stand, so no new rehearsal.) After the laptop session,
changing a line inside the tools costs a new tools version; changing a line outside them costs new generated lines,
their tests and the guide's quotes, but no tools version.

Inside the tools (what the tools print):
1. Export without the stick, three lines: `Tools stick absent: records copied to /run/ares-records with SHA256
   readback`; `This copy is on this laptop, not off it; uid 1001 can read it, and a restart deletes it`; `For a copy
   off the laptop plug in the tools stick and run export again`. If his account cannot be let in: `This copy is on
   this laptop, not off it; only root can read it, since uid 1001 could not be let in (<reason>), and a restart deletes
   it`.
2. Export to a stick with older tools: `The stick holds tools this laptop installed before (SHA256 …), not the installed
   ones`.
3. First installation tried without the stick: `The first installation runs only from the tools USB at the recovery
   console; nothing changed`.
4. A stick-begun update finished without the stick: `Interrupted tools update began from the tools USB; finish it from
   that stick at the recovery console`.
5. An unfinished layout trial: in the same start `Layout trial is unfinished; prove it or revert first; if the console
   that began it is closed, from a fresh physical administrator login run sudo /var/lib/ares/at layout abandon`; after a
   restart `Layout trial is unfinished and began before the last restart: from a fresh physical administrator login run
   sudo /var/lib/ares/at layout abandon, then run this command again`.

Outside the tools (the window and Claude's lines):
6. The window's two labels: `AresOS owner tools dcbc375f: install these tools, then check and title` and `AresOS owner
   tools dcbc375f: export the records`.
7. The new STOP lines: `STOP after install: check or title refused`, and Claude's folder line's `STOP tools folder: …`
   (`give the full commit hash`, `<commit> is not on origin/main`, `this checkout differs from <commit> in
   os/owner-tools`, `<commit> holds other tools than dcbc375f`, `refused, nothing was installed`).

In the guides:
8. The routine box in `INSTALL.md` and the card **A routine tools command stopped** in `EMERGENCY.md`, including: after
   10 minutes without an answer Claude closes the window and nothing runs; after a STOP Claude copies every STOP line
   word for word and runs the export only on his go; his phone bookmark of `OWNER-TOOLS.md` on `main`, never a link
   Claude sends then; the console's "Keep the current administrator session open" does not apply on this route; after
   a routine install the stick holds older tools until Claude writes it again ("for now from Windows", not a package
   name); Claude updates its copy only by a fast-forward pull, and no other Claude session runs an owner command
   meanwhile; only the install and export lines run this way for now.
9. The sentence about a stopped update: "If the update STOPs with **was stopped safely**, nothing changed and every
   command works: run update again later, or get Help."
10. After every install from Claude's terminal (not only after a change of what starts next), Claude posts the title's
    lines (which system runs and starts next, the boot menu's rows, no serials) to the board, since he no longer sees
    the title himself.

## PLAN-GAP

None open. The brief's walk ran as written, with the integrator's recorded changes (decision 10 replaced by R1, the
stand-in origin, release 27's facts from its own commit, the dispatch caps).

## Open questions (for the integrator)

- `test_checkout_sources` still checks 22c's receipt as the current one (see the record step's "Not done").
- After merge, any bound tool, release script or guide change (`os/owner-tools/`, `os/release/`, `docs/`) fails
  `test_checkout_sources` while 22c's or 22d's row says **VM REHEARSAL PASSED; NOT ON THE LAPTOP**; a harness, workflow
  or test file may wait. Before release 28's work changes `docs/` and `os/owner-tools/`, both rows move on (22c's too:
  version 4 carries its ways back), or a new rehearsal records its own row (step 7b's "What happens after merge"; its
  first sentence there still names harness files, from before the integrator's decision).
- The test refuses a waiting tool, release script or guide (`os/owner-tools/`, `os/release/`, `docs/`: what the laptop
  gets) while a row says rehearsed, as review 8 proposed (the integrator's decision after step 7b; the builder's first
  version also refused harness files, which would have stopped release 28's harness steps).

Open items for later (from the final review, REVIEW-5; none blocks the laptop session):
- **N1, the next version of the lines** (`os/owner-tools/bootstrap.py:44`, `:150-157`): `FROM_COMMIT` runs `git` by
  PATH and neither line clears `GIT_*` or passes `--no-replace-objects`, so a `GIT_DIR` in the caller's environment or
  a replace ref could make `git show <commit>:…commands.json` return another file. Each needs a program already writing
  as him; the laptop has neither today ("Try this" step 2 checks). Fix: `/usr/bin/git --no-replace-objects` and
  `unset "${!GIT_@}"`. Not now: the change is under `os/owner-tools/`, which may not wait while the row says rehearsed.
- **N2, the next image** (beside `SUDO_ASKPASS`, F18): nothing in `os/config` or the image checks pins sudo's
  `env_reset` (on by sudo's default). The line leans on it little.
- **N6, the next guide change** (`docs/INSTALL.md:276`, the routine box): it names neither a wrong password nor a power
  cut. The guides are pinned while 22d's row says rehearsed; until then "Try this" step 8 carries both.

## Try this (the laptop session, after merge)

Claude runs every line below in its own terminal as `ares` (its Bash tool, not through a second shell, a
here-document or `eval`). Shell variables do not survive between the Bash tool's calls, so each code block is one
call. `<commit>` stands for the announced commit's full 40-character hash. Nothing in steps 1 to 4 needs a password or
changes the system.

**Before the session (the integrator)**

1. Merge PR #66 into `main`. Before the board note, on the merge commit `<commit>` that is on `origin/main`:
   - a checks-only run is green with the full model (run 43755153393 tested `7ef03022`, before step 8's merge);
   - `git rev-parse <commit>:os/owner-tools` prints `73fb5929cddd36db91662bad7d83e5453b965ca6` (the tree run 4
     walked);
   - `git rev-parse <commit>:docs/INSTALL.md <commit>:docs/EMERGENCY.md <commit>:docs/OWNER-TOOLS.md` prints
     `115e4974255f093e0e7947eb68e47ebaa65020d2`, `7e68584fca121f2d5a9b0a88a35b9f2844c0f780` and
     `53c075c804ab0c2449ac5f11fd2d786e0e900cff`.

   Then post on the board: `<commit>` in full and the fingerprint
   `dcbc375faa4b269bacaf316c5ddc24503b9773b2538bcd017065ce8e312597be`.

**Prechecks (Claude, read-only)**

2. Tell every other running session: from step 4 until the last PASS line, run no `rpm-ostree`, `bootc` or `ostree`
   command (also no read-only one) and no `os/tests` owner module; the tools STOP on any such client of any user.
   Then each of these must hold; if one does not, stop and tell him (nothing has run):
   - `pgrep -u ares -x labwc` and `pgrep -u ares -x foot` each print a PID. If `foot` prints none, he opens an AresOS
     terminal window first, and keeps it open until the three PASS lines. Without it he gets `PASS install`, then a
     STOP from `check` and `STOP after install: check or title refused`: the tools are installed and nothing is lost,
     but his session ends on the STOP card.
   - `pgrep -a -x 'rpm-ostree|bootc|ostree'` prints nothing (`rpm-ostreed`, the daemon, does not count).
   - `lsblk -o NAME,SIZE,MOUNTPOINTS`: every mount point is on the AresOS SSD (the disk that holds `/boot/efi`); no
     partition of the Windows SSD has one. Otherwise the tools STOP with **Protected disk is mounted** (a file manager
     on the desktop can mount it; the console never does).
   - `env | grep '^GIT_'` prints only `GIT_EDITOR=…`; `git -C /var/home/ares/AresOS for-each-ref refs/replace` and
     `git -C /var/home/ares/AresOS config --get-regexp '^url\.'` print nothing; `git -C /var/home/ares/AresOS remote
     get-url origin` prints `https://github.com/Ares-Empire/AresOS.git`.
3. `git -C /var/home/ares/AresOS pull --ff-only`. Then `git -C /var/home/ares/AresOS merge-base --is-ancestor <commit>
   HEAD` must succeed (exit 0).

**The folder line (Claude, as `ares`; no window)**

4. One call:

   ```bash
   c=<commit>
   line=$(/usr/bin/git -C /var/home/ares/AresOS show "$c":os/owner-tools/commands.json | /usr/bin/python3 -I -c 'import json,sys; sys.stdout.write(json.load(sys.stdin)[sys.argv[1]])' tools-folder)
   if [ "$(printf %s "$line" | sha256sum)" = "c1b579be56abe84e24c3be1be6a93edc7ccb39cee607988b493cfe55bc4bdd82  -" ]
   then /usr/bin/bash -c "$line $c" < /dev/null
   else echo "NOT RUN: the folder line differs from the one run 4 ran"; exit 1
   fi
   ```

   Expect `SHA256SUMS: OK` as its last line, and no window. A `STOP tools folder: …` line ends the session there:
   nothing was installed, no window opens and no export follows. `NOT RUN` means the commit holds another line than
   the rehearsed one: stop and tell the integrator.

**His go**

5. Claude prints the routine line's SHA-256 (one call):

   ```bash
   c=<commit>
   line=$(/usr/bin/git -C /var/home/ares/AresOS show "$c":os/owner-tools/commands.json | /usr/bin/python3 -I -c 'import json,sys; sys.stdout.write(json.load(sys.stdin)[sys.argv[1]])' tools-routine)
   printf %s "$line" | sha256sum
   ```

   It must print `0b11cfc562841f58393bdb11f7962556418f851241885ce21d11594a4e13c079  -`: the line run 4's caller ran
   (`line_sha256` in `tl-install-caller-result.json`). Otherwise stop and tell the integrator. Then Claude tells him:
   tools version 4, `dcbc375f`, a password window comes next; and waits for his go.
6. On his go, one **background** call, and Claude notes the time it started:

   ```bash
   c=<commit>
   line=$(/usr/bin/git -C /var/home/ares/AresOS show "$c":os/owner-tools/commands.json | /usr/bin/python3 -I -c 'import json,sys; sys.stdout.write(json.load(sys.stdin)[sys.argv[1]])' tools-routine)
   if [ "$(printf %s "$line" | sha256sum)" = "0b11cfc562841f58393bdb11f7962556418f851241885ce21d11594a4e13c079  -" ]
   then exec /usr/bin/bash -c "$line" < /dev/null
   else echo "NOT RUN: the routine line differs from the one run 4 ran"; exit 1
   fi
   ```

   The line is one argument to `/usr/bin/bash -c`, exactly as the VM's caller ran it (`os/ci/tools_local.py`,
   `CALLER`). If Claude Code asks its own permission for this command first, that is Claude's prompt, not the window.
7. He sees a small window titled **Enter SSH Credentials**, inside **AresOS owner tools dcbc375f: install these tools,
   then check and title**, a Password field, OK and Cancel. On his phone, from his own bookmark, he opens
   `github.com/Ares-Empire/AresOS/blob/main/docs/OWNER-TOOLS.md`, checks it says `main`, and compares line 1
   (`Owner tools version 4: dcbc375f`) with the 8 characters in the window. Same: he types his password and presses OK.
   Different, or anything odd: Cancel (nothing runs).

**While the window is open**

8. What he may see, and what Claude does:
   - **No answer within 10 minutes** of step 6: Claude runs `pgrep -a -u ares -x ksshaskpass`. It lists the helper with
     the label as its argument (`AresOS owner tools dcbc375f: install these tools, then check and title`). If exactly
     that one process is still there, `kill <its PID>`, that one PID and nothing else (never `pkill`, never sudo or
     bash). sudo then ends with `sudo: no password was provided`, exit 1: nothing ran; Claude asks him again. If it
     lists none, he has answered: wait for the result. If it lists more than one, or one with another argument, kill
     nothing and tell him.
   - **No window to be seen** (behind the hub or a full-screen game): he says so, and Claude closes it as above; nothing
     runs.
   - **Cancel:** the window closes; `sudo: no password was provided`, exit 1; nothing changed.
   - **A wrong password:** `Sorry, try again.` and the window comes back with the same label, up to three times. After
     the third, sudo gives up and nothing ran.
   - **A power cut or restart during the install:** after the start the tools work (the old ones before the switch, the
     new ones after). On his go Claude runs step 4 and then step 6 again, and the install resumes; run 4 did exactly
     this (cut, then install).
   - **Any STOP** (Cancel is not one): Claude copies every STOP line to him word for word, asks for his go, and only
     then runs the export (step 10); it tries nothing else.

**The result**

9. What he should see (Claude reads it to him): `PASS install` with `Tools updated from version 2 to 4` and
   `manifest SHA256 dcbc375faa4b269bacaf316c5ddc24503b9773b2538bcd017065ce8e312597be`, then `PASS check`, then
   `PASS title` with these lines (run 4 printed the same; the 12 characters are release 27's, release 13's and the
   pinned stock's image digests):
   - `newer AresOS 5fad242fceac runs and starts next`
   - `Boot menu at the next start: (ostree:0) newer AresOS 5fad242fceac, starts next; (ostree:1) older AresOS
     9b19b7942bc1; (ostree:2) plain Bazzite ed93d2158a1b`
   - `pin yes; transaction idle` and `staged False; rollback queued False`
   - `Previous title INVALID; use this record until the next reorder`

   Claude posts the title's lines (which system runs and starts next, the boot menu's rows, no serials) to the board
   under topic `aresos`. Optional, the integrator's call: `/usr/bin/sudo -n true` must then be refused (no ticket
   kept), as the VM's last step.
10. Optional, or after a STOP on his go: the export, the same way as steps 5 to 8 with entry `export-routine`, hash
    `7e1ffa764c263ef78025cee21c9d7ef2b6959e370765da40ae55046dc45a23d4` and the label **AresOS owner tools dcbc375f:
    export the records**. Expect `Tools stick absent: records copied to /run/ares-records with SHA256 readback`, then
    `This copy is on this laptop, not off it; uid 1001 can read it, and a restart deletes it`.
