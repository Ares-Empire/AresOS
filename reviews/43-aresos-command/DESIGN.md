# 43 design note: the `aresos` command

Empire brief 296. Written 2026-11-15 on main `4d23b408` by a Claude agent on Fable 5.2 (the lead's choice: a new design for a tool that decides which installed system is replaced). Revised 2026-11-16 after review 1 (`REVIEW-1.md`, READY WITH CHANGES) by a fresh Claude agent on Fable 5.2 that wrote neither the note nor the review; the last section maps each finding to what changed. A design note only: it changes no tool, test, guide or workflow.

Made by reading code. No owner tool, `sudo`, ostree, bootc or rpm-ostree command ran, and no window was opened. The revision ran one Python check as `ares` in an empty scratch folder (fact 10).

**References.** No prefix is main. `22d:` is package 22d's tree, on main since `634e1237`; its line numbers were checked again on main at `937a1868`, where the tools, the guides and 22d's files are the bytes the note was written against. `18c:` is `origin/pkg/18c-image` (PR #58), checked again at `986192c3`. `owner.py` is `os/owner-tools/owner.py` throughout.

**Words.** *Inner word*: a word of `/var/lib/ares/at`. **N**: the newest installed AresOS (`newest()`, `owner.py:756`). **T**: the release the installed tools carry (`owner.py:1790`); it is last in their history, so when T is installed, T is N. *Runs* and *starts next* are the title's words: the booted deployment and the first one in the list. *Announcement*: a first line of `newest` that starts with `Update:` and says what the run is about to change.

## The decisions in short

| | Decision |
|---|---|
| D1 | The choice lives in the tools: an 18th inner word, `newest`, in one root process under the one lock. |
| D2 | Its rule is a table of eleven rows (0 to 10) over one read of the system (section 1). A run does one thing: it continues an interrupted update, installs T, goes forward to N, or changes nothing and says why. A change that waits for the restart is a PASS that says what waits. |
| D3 | Staging through `newest` carries a guard inside `update`'s own two checks: it never stages unless the running AresOS is N. The inner `update`, typed by its own name, stays as built (#263). |
| D4 | `newest` says which thing it does only after the chosen word's read-only checks have passed and before its first change. An announcement is never followed by a refusal. The inner word's lines, journal and refusals are unchanged. |
| D5 | `aresos update` runs `newest` and nothing else. The dispatcher has no row that reaches the inner `update` or `forward`, and prints no line that names them. |
| D6 | Nine words work from the desktop: `update`, `previous`, `rollback`, `check`, `title`, `records`, `logs`, `export`, `reboot`. Nine are refused with one line that names where they work. |
| D7 | One password window per `aresos` word, by 22d's mechanism unchanged. No sudoers rule, polkit action or service. |
| D8 | The window's line is `AresOS: <fixed phrase>`, without a fingerprint. His rule has three conditions; the 8-character compare stays for new tools only. |
| D9 | A root-owned helper closes an unanswered window after 10 minutes. The dispatcher becomes `sudo` (exec), so nothing sits between Claude and it. |
| D10 | The dispatcher is one Python file, `os/config/usr/bin/aresos`: a pure `plan()` and an exec. It is not a security boundary. |
| D11 | It starts `sudo` with an environment built from nothing: fixed values, his account's own name and home, and the variables that say where the screen is. |
| D12 | Control's wrapper moves unchanged to `/usr/libexec/aresos-control/cli`; every first word that is not a tools word goes there unchanged. `newest` joins Control's reserved words, and a test holds the three word sets equal. |
| D13 | "Nothing to do" and "newer tools would bring a newer release" are one state to the tools: one message, which prints the tools' version line. A different line on GitHub is not a go: Claude tells him and waits for the announcement. |
| D14 | The guides gain one box in front of the console boxes, which do not change; the emergency card gains four sentences. |
| D15 | Proof: unit tests; the model with the new word and four new judgments; one check build for the image files; one VM run of 43's own for the tools; the dispatcher's stages ride R29's release rehearsal. |
| D16 | In the image: two `os/config` files and Control's moved wrapper, explained by the release diff's existing rules; the helper's package version is pinned. |
| D17 | The seam for the online update is the dispatcher's `update` row and the "nothing to do" message. Nothing of it is built. |
| D18 | No root step of the tools depends on the directory it was started from: `at` changes to `/`, every child starts in `/`, and the steps' own Python starts isolated. |
| D19 | `check` asks for the program the running release's session starts (the desktop keeper from release 28, `foot` before), not for a terminal. |

## 0. Facts the design rests on

1. **The inner `update` installs T by staging and nothing else** (`owner.py:1778-1850`). It refuses with `RELEASE_INSTALLED` when T is installed but not both running and first (`:1798-1802`, text `:61-62`), and with `FORWARD_FIRST` unless the running system is an AresOS and first (`may_stage`, `:1635-1641`, text `:65-66`). When it stages, ostree's shutdown step removes the other AresOS, whichever it is (`:1816-1817`, `:1843-1849`).
2. **The danger state** (#263): an older AresOS runs and starts next (after `previous` and a restart), a newer one is installed, and the tools carry a T that is not installed. There the inner `update` passes every check, stages T and removes the newer AresOS. It says so; it is the owner's decision 5 and stays reachable by the full path.
3. **The inner `forward`** makes N the next start by one reorder and never stages (`:1953-1961`); where N already starts next it changes nothing and reads no further check (`select`, `:1683-1688`).
4. **An interrupted staging** in the same boot is `update`'s to continue; every other word stops and names it (`outcome`, `:1287-1341`).
5. **What needs a terminal or the console in code:** `login` (a hidden prompt, `:1714`), `layout` (`Tools.session()`: the physical tty3/tty4 login of `ares-recovery`, `:2078-2110`), the tools update on the stick route (`:2593`) and the first install (`:2761`). Every other word requires only root (`:2888`); the guides alone route them to the console (22d's N10, `briefs/22d-tools-without-stick.md`).
6. **The tools are root-only** (`/var/lib/ares`, 0700, `owner.py:2918-2919`). A program of `ares` cannot read what is installed, which toolset is current or its fingerprint.
7. **`/usr/bin/aresos` is an image file.** Plain Bazzite and every AresOS before R29 have no dispatcher, and plain Bazzite has no `ares` account at all (`os/release/stock-session.sh:3`). There the full path at the console is the only route, as today.
8. **The password window proves that he approved a root command now, not which** (`22d:reviews/22d-tools-without-stick/DESIGN.md`, section 1). The caller sets the line inside; the title bar is the helper's own, "Enter SSH Credentials" (`22d:reviews/22d-tools-without-stick/STEP-0.md`). `ares` has `timestamp_timeout=0` (`os/config/etc/sudoers.d/aresos-everyday:5`, required by `os/ci/image-checks.sh:31`).
9. **What 22c's reviews found** with both jobs in one word: the guide's "follow it" led from a return into a staging that nobody had announced (`reviews/22c-ways-back-after-update/REVIEW-4.md:8-9`). The cure there was one word per meaning, held by the model on every edge (`os/tests/test_ways_back_model.py:266-279`).
10. **A root step reads Python modules from the directory it was started in.** `at` starts `owner.py` with `-I` but never changes directory (`os/owner-tools/at:10`). Each release step is a `bash -seu` with the inherited directory (`owner.py:377-379`). The steps' own Python starts as `python3 - <<'…'` without `-I` (`os/release/update.sh:4`, `start-next.sh:6`, five more starts in the payload's scripts, and `owner.py:1426`), and for a script on stdin Python puts the current directory first on its module path. `sudo` keeps the caller's directory (22d's step 0: `PWD=` of the caller in its journal line). Tried on the laptop's Python 3.14.8 as `ares`, in an empty scratch folder holding a marker-writing `json.py`: `import json, subprocess` from `bash -seu -c 'python3 -'` ran that file; with `python3 -I -` it did not.
11. **From release 28 the session starts no terminal.** labwc's autostart runs the desktop keeper (`os/config/usr/share/aresos/labwc/autostart:5`), and the supervisor shows a `foot` only in SETUP, AUTH_REQUIRED and RECOVERY (`os/config/usr/libexec/aresos-desktop:35`). `check` requires a `foot` of `ares` (`owner.py:2016-2017`).
12. **Every result block of the tools starts with `PASS <word>`** and the lines follow it; lines printed with `say` (`:512`) come at once, before it. What the survey resolved (`was not applied`, `it is recorded now`) is printed with the result, after `PASS` (`:2933`). Every STOP ends with a fixed line that says "do not reboot" (`:2959-2960`).

## 1. Where the choice lives (D1 to D4)

| | Option | Window | Journal and resume | Refusals | Model |
|---|---|---|---|---|---|
| A | A read-only inner word names the word that applies; image code under one `sudo` runs it | One, but two tools processes: the lock is released between the answer and the act | Unchanged | Image code must read the tools' answer; any default other than "stop" is the wrong guess again | Cheap for the read-only word; the composition the owner types is outside the model |
| B | One inner word decides and runs exactly one inner command in the same process | One process, one lock | Unchanged: the journal's word stays `update` or `forward` (`owner.py:763`, `:1345-1359`) | The two refusals that point from one word to the other cannot occur; all others pass through | A new state-changing word: it must be in the ledger and the driver |
| C | Image code runs `forward`, reads its lines, then perhaps `update` | Two changes possible in one run | | Parses guide text | Rejected: it breaks "one of the two per run" |

**D1: option B, the inner word `newest`.** Reasons:
- The decision and the act run in one process under one lock. Each inner word reads the system again before it acts, as built (`owner.py:1788`, `:1958`); the guard and the announcement use that second read, so what is said and what is done come from the same read. With A that holds only by an argument over cases.
- The dispatcher stays a table with no logic: it never reads a tools answer, so it cannot guess.
- The one word then also works at the console with the full path, on plain Bazzite and on older releases, wherever these tools are installed. With A it would exist only where the dispatcher is.
- The lead's decision holds as written: `forward` and `update` stay separate inner commands, unchanged for whoever types them. `newest` is a third entry in front of them. What made one word unsafe in 22c was a second job following the first without an announcement; D2's "one thing per run" and D4's announcement, both checked by the model on every edge, are the answer to that, not the number of words.

**D2: the rule.** `newest` reads the system once, with `survey(retry='update')` (`owner.py:1600-1606`), and takes the first row that fits. "Another system" is an older AresOS or plain Bazzite.

| Row | What the read shows | What `newest` does | First line (section 5) | Ends |
|---|---|---|---|---|
| 0 | The survey itself stops (a list outside the reviewed set, a journal that fits neither list, a Bazzite update waiting) | Nothing | None; the STOP as it is | STOP |
| 1 | No AresOS is installed | Nothing | None | STOP `NOT_INSTALLED`, as `forward` says today |
| 2 | The survey has just closed an update's journal as **not applied** (an update that did not finish at shutdown; `:1327-1330`) | Nothing more in this run | The survey's line, at once; then `Nothing changed: the last update did not finish …` | PASS |
| 3 | An interrupted staging stands open in this boot and **is staged already** (`complete`); only its record is missing | Records it with the inner `update`. This run stages nothing | `Update: the interrupted update … is staged already; recording it`, then what it removes at shutdown | The inner word's |
| 4 | An interrupted staging stands open in this boot, **nothing is staged yet** (`retry`), and N runs | Stages it again with the inner `update`, under the guard | `Update: continuing the interrupted update …` | The inner word's |
| 5 | The same as row 4, but an older AresOS runs (the staging was begun there with the inner `update`, #263) | Nothing | None | STOP, a line of its own |
| 6 | **A change waits for the restart** (`pending`: an update is staged, or a `previous`, `rollback`, `keep-stock` or `forward` of this boot is in place and its target does not run yet) | Nothing | `Nothing to do now: …`, which says what waits | PASS |
| 7 | N runs and starts next; T is not installed | Installs T with the inner `update`, under the guard | `Update: installing the new AresOS release …` | The inner word's |
| 8 | N runs and starts next; T is installed (it is N) | Nothing | `Nothing to update: …` | PASS |
| 9 | **N starts next and another system runs** (a boot-menu start, or a forward whose restart landed elsewhere) | Nothing | `forward`'s own two lines: `… already starts next; nothing changed`, `It does not run yet: it starts at the next restart` | PASS |
| 10 | **N does not start next**: another system runs, or N itself runs while another system starts next | Goes forward with the inner `forward` | `Update: …`, worded by what runs (three wordings) | The inner word's |

- The table is complete: the survey either stops (row 0) or returns a journal state; `retry` and `complete` are rows 3 to 5, `pending` is row 6, and every other state (none, `applied`, `done`, `elsewhere`) falls into exactly one of rows 7 to 10 by where N stands.
- No row does two things. After a forward and its restart, the next run may install T; rows 9 and 10 say so in one more line when T is not installed (section 5).
- Rows 2, 6, 8 and 9 run no inner word, read no further check and write no journal, like the inner words where their destination starts next already (`:1685-1686`). They end with `PASS newest`, never with a STOP: a STOP's fixed last line says "do not reboot" beside a message whose point is that the restart is what comes next, and it would send Claude into the export routine.
- **Row 6 comes before rows 8 to 10** on purpose. It is the state right after every update, when the word is most likely run again; as first written, the rule fell through to "go forward" there, announced a newer AresOS that does not exist and then refused (review 1, B1). No word can undo a queued return before its restart (`may_change`, `:1628-1631`); row 6 says so and what the word does after the restart.
- **Row 2: a failed update is not repeated in the run that finds it.** The survey closes the journal and notes one line that shows only once. Staging again in the same run would repeat the update without anyone deciding, against the card ("Help decides each repeat", `docs/EMERGENCY.md:23`, `:27`), and its `was not applied` line would appear under `PASS newest` above the new staging's lines, as if it were about the new attempt. So this run only says it; the repeat is a second, deliberate run. A reorder's journal closed as not applied (a cut `forward`) does not stop the run: its line is printed first, then the table goes on.
- **Row 3 on an older AresOS** (the inner `update` at the console staged T there and was cut before its record): recording changes nothing on the disk and lets every other word work again, so `newest` records it. It prints the removal line for the newer AresOS, which this path of the inner word does not print (`:1791-1795`).
- **Row 5:** `newest` never stages from an older AresOS, also not to continue what the inner `update` began there. Its line: `The update to <reference> was begun on an older AresOS and interrupted; this command does not continue it; nothing changed; do not reboot; get help: EMERGENCY Failed or bad update`. It names no restart and no command.

**D3: the guard.** `update()` gains one optional argument that only `newest` passes. It switches the guard on and carries the function that prints the announcement (D4).
- After each of `update`'s two `may_stage` calls the guard requires that the running AresOS is N. After the first (`owner.py:1803`) it comes at once. After the second (`:1809`) it comes behind the comparison of `:1810`, so a list that changed during verification gets that line's own text, "Deployments changed during verification".
- Its refusal: `A newer AresOS than the running one is installed, and this command installs a release only from the newest; nothing changed`. It names no restart and no other command: every other word says "do not reboot" in the states where it can fire.
- `newest` has already decided from its own read (rows 4, 5 and 7), so the guard fires only when the list changed outside the tools between two reads. It stays because it is checked on the read that staging acts on, also after the minutes verification takes: I1 below then holds by where the check sits, not by an argument about `newest`'s table.
- Row 3 stages nothing (`:1791-1795` only records), so it needs no guard.

**D4: saying which, and when.** `update()` (through D3's argument) and `forward()` (through one optional argument handed down to `select` and `start_next`) call the function once their read-only checks have passed and before their first change:
- install and row 4: after `may_stage`, the guard, the stored login (`:1804`) and the `cosign` check (`:1805`), before the signature check, which takes minutes;
- row 3: after the check that the staged release is T (`:1793`), before the record is written;
- forward: inside `start_next`, after `may_change` and the target check (`:1647-1650`), before the journal's intent (`:1651`).

The function gets the read the inner word acts on, builds the line from it and prints it with `say` (`:512`), at once. So a refusal is never preceded by an announcement: a missing login, a layout trial, a busy deployment tool or a staged row stops the run before anything was said. After the announcement a run makes its change, is cut, or fails in the act itself (a signature that does not verify, a list that changed during verification).

**The survey's lines come first.** `newest` prints what its survey resolved at once, before any first line of its own, so the screen reads in the order things happened; `main()` then does not print them again.

**Records.** The saved record (`…-newest.json`, and the STOP record) gains `chosen` (`update`, `forward` or none) and `said` (the lines printed before the result block: the survey's lines and the announcement). The journal is the chosen word's own: its word stays `update` or `forward`, and a row that runs no inner word writes no journal. `main()` changes in three places: the word in `known` (`:2890-2891`), its entry in the method table (`:2927-2931`), and the two record fields on the PASS and the STOP path. The result block starts with `PASS newest`. Older tools answer `newest` with "Choose a documented owner command" and change nothing (`:2910`).

**Refusals.** Every refusal of the chosen inner word passes through as it is, with its "nothing changed".
- `RELEASE_INSTALLED` and `FORWARD_FIRST` cannot come out of `newest`: rows 7, 8 and 10 are exactly their conditions. A test and the model hold that.
- The STOP for an interrupted staging that fits neither list (`:1323-1324`) names the word that continues it. When `newest` asked, that is `typed('newest')`; for every other word it stays `typed('update')`, as built.
- Every line `newest` itself adds spells a command with `typed()` (`:50-52`): the full path works everywhere, and the tools cannot know whether the running system, or the next one, has a dispatcher (fact 7). None of them contains `typed('update')` or `typed('forward')`.

**The model** (`os/tests/ways_back_ledger.py`, `os/tests/test_ways_back_model.py`):
- The ledger gets its own `choose(s)`, written from D2's table and not from the tools, with one result per row. For rows 3, 4, 7 and 10, `transition(s, ('newest', phase))` is the chosen word's transition; rows 2, 5, 6, 8 and 9 are results of their own (row 2 archives `not-applied`, as `check` does there; row 5 stops; the others change nothing beyond what every survey resolves).
- `newest` goes last in both loops of `steps()` (`ways_back_ledger.py:308`, `:311`), after every existing word. Each of its successors is one an earlier word already reaches, so no new state appears, the breadth-first order and the slice's pinned state count stay, and only the edge counts move. It joins the driver's method table (`test_ways_back_model.py:257-259`). `WORDS` (`:444`) is the list the 22c rehearsal typed, used by its replay; 43's run gets no replay (it adds no new primitive: every change `newest` makes is `update`'s or `forward`'s, which 22c's replay holds against the VM), so `WORDS` stays.
- The builder measures the full model's time before and after and reports it.
- Four judgments on every executed `newest` edge, by the fake's state and output before and after, like "one word per meaning" (`:266-279`):
  - **I1:** if anything was staged, the running system was N and started next before the command.
  - **I2:** no STOP out of a `newest` run, and no line `newest` itself adds, contains `typed('update')` or `typed('forward')`. (The bare word in "then update again", `owner.py:1641`, and the title's own lines are not meant.)
  - **I3:** the announcement was printed before the journal's intent and before the first mutation. The fake host notes the output at both.
  - **I4:** an announcement is followed by its change or a cut, never by a refusal. No forward announcement is printed where the ledger's N runs and starts next or a change waits, and no line that begins `Nothing` follows an announcement.
- Any change under `os/owner-tools/` selects the full model in the hosted run (`os/ci/model_scope.py:30`).

## 1a. Two repairs in the tools that ride in step 1 (D18, D19)

**D18: no root step depends on the directory it was started from** (fact 10).
- **Why now.** `aresos previous`, `aresos rollback` and `aresos update` are the first route that starts `start-next.sh` and `update.sh` as root from the directory Claude happens to work in. By accident, a file there with the name of a standard module (this repository has one: `control/aresos_control/warnings.py`) fails a reorder after its journal intent was written. On purpose, a folder from someone else (a cloned project, a download) gets root on the laptop without a wrong window or a wrong command: the honest line and his real password are enough. That is below the line this note draws for the window.
- **What is not exposed today:**
  - the console: `sudo -i`, directory `/root`;
  - 22d's install line: it changes into its root-only copy under `/run` before `at` runs (`os/owner-tools/commands.json`, `tools-routine`: `umask 077`, `p=$(mktemp -d /run/ares-bootstrap.XXXXXX)`, `cd "$p"`, `cd ares-tools`), so its `install`, `check` and `title` run there;
  - 22d's export line: it runs from the caller's directory, but `export` starts no Python step (`owner.py:2031-2045`; `media.py` runs system tools only).
  So no route the guides name is open, and the fix rides in 43's tools, the next version whose code changes. The full path typed in a desktop terminal has the same hole, which is why the fix is in the tools and not in the dispatcher.
- **The fix,** in step 1:
  1. `at` changes to `/` after it has resolved its own path and before it starts Python.
  2. `Step` and `Host.read`/`Host.mutate` pass `cwd='/'` (`owner.py:377`, `:312`, `:326`).
  3. Every Python a payload step starts on stdin starts as `python3 -I -`: the seven starts in `update.sh`, `start-next.sh`, `switch.sh`, `system-keyboard.sh`, `pause-stock-updates.sh` and `pin-stock.sh` (two), and `owner.py:1426`. They import standard modules only. `previous.sh`, `rollback.sh` and `default-stock.sh` left the payload in 22c and stay byte-identical for the older CI modes (`os/owner-tools/bundle.py:14-16`).
  4. Tests, in a module that starts no real tools entry (so it also runs on the laptop):
     - a real `Step` started from a folder that holds a marker-writing `json.py` and `subprocess.py` runs a script of the release steps' shape (`python3 -I - <<'X'`, `import json, subprocess`): neither file ran, and the step's directory is `/`. The same script without `-I` writes the marker, so the test can fail;
     - the real `at` beside a stand-in `owner.py`, started from that folder: the stand-in sees `/`;
     - `Host.read` and `Host.mutate` start their program in `/`;
     - no file of the payload starts Python on stdin or with `-c` without `-I` (read from the files, so a later script cannot bring it back).
- **What walks it.** `at`, `owner.py` and the changed scripts except `update.sh` are bound files, so they wait on the list until 43's VM run. That run executes `update.sh` and `start-next.sh` in their new form, each once from a folder that holds the two marker files (section 7). `switch.sh`, `pin-stock.sh`, `pause-stock-updates.sh` and `system-keyboard.sh` run only on plain Bazzite before the first switch, which 43's walk reaches with older tools: for them the proof is the unit tests that run their steps and the last test above. The laptop never runs those four again.

**D19: `check` asks for the program the running release's session starts, not for a terminal** (fact 11; review 1, S2).
- **Why `foot` is there.** The pair came with package 14 (`79a67d2f`), and no brief gives it a reason of its own (searched: briefs 14 to 16 and 22, `docs/design/OS-BASE.md`). Read from the code and the guide: `check` proves on a running AresOS what `stock-session.sh` proves on plain Bazzite, that the daily session is the one this system should have (`docs/INSTALL.md:191`: "daily `ares` UID1001/no wheel and running labwc/foot"). For AresOS that was `labwc` of `ares` (the compositor) and `foot` of `ares`: the one program the session's autostart started in releases 13 and 27, and the terminal of the typing proof. `os/tests/guest.sh:6-7` holds the same pair for the image. So `foot` stands for "the session got past the compositor to its own program", not for "a terminal is open".
- **What goes wrong.** Release 28's autostart starts the desktop keeper instead. In the hub no `foot` runs unless he has the Terminal app open, so `check` STOPs with `Read failed: pgrep -u ares -x foot`, from Claude's terminal and at the console alike, on the word the emergency card puts first. No rehearsal shows it: a VM without a Minecraft account sits in SETUP, which shows a `foot`.
- **Decision.** On a running AresOS `check` keeps `labwc` of `ares` and requires the session's own program of that release:
  - where the running system has `/usr/libexec/aresos-desktop` (release 28 and later): a process of `ares` with that name. The keeper and the supervisor both carry it and live as long as the session;
  - where it has not (releases 13 and 27): `foot`, as today.
  Exactly one of the two is asked, by what the running image holds, never either. The protection stays: a session that never reached its own program still fails.
- **Why by the image's file and not by a field in the release record** (the review's first option): the file is part of the signed image whose digest `check` has just matched against the history, so it says what a record would say, and `stock-session.sh:8` already reads a session file this way. A new field would change the history's strict form (`owner.py:163`), with which every installed bundle's history is read (`:175-184`), for one fact the image states itself.
- **Why not "open a terminal first" in the guide** (the review's second option): `check` must not depend on something the hub never shows.
- **Proof.** Unit rows for both kinds of image, each with and without its program; a test that the name `check` asks for is the program labwc's autostart starts (read from `os/config`); in 43's VM run one `at check` on release 28 whose saved record shows the read of `aresos-desktop` passing and no read of `foot` (section 7).
- **Not known from reading:** that `pgrep -x aresos-desktop` finds a script started through its `#!` line under the script's own name. The VM stage shows it; if it does not hold, the builder reports it and the check matches the keeper's full command line instead.
- **For the lead:** with tools version 4, `at check` on release 28 passes only while a `foot` of `ares` runs, also at the console. Until 43's tools are on the laptop, R28's guide and any session there need "open the Terminal app first" before `check` (package 42).

## 2. The words (D5, D6)

`aresos update` is the only word whose inner word differs. The inner `update` is deliberately not reachable through the dispatcher: it is the word that can replace a newer AresOS (fact 2).

| Tools word | `aresos <word>` | Why |
|---|---|---|
| `newest` | as `aresos update` | D1 |
| `update` | not reachable | fact 2; from the console by the full path, as built |
| `forward` | refused, points to `aresos update` | `aresos update` goes forward in every state where `forward` would change anything (D2, row 10); one word (#262) |
| `previous` | yes | the way back after a bad update while the desktop works; no console check (`owner.py:1963-1969`) |
| `rollback` | yes | the way back to plain Bazzite; valid only on a running AresOS (`:1763-1767`), which is where the dispatcher is. After its restart he is on plain Bazzite, without Claude and without `aresos` (fact 7; JUDGMENT-CALL 8) |
| `keep-stock` | refused | valid only on running plain Bazzite (`:1763-1767`), which has no `aresos` |
| `check` | yes | reads the system and writes only the private records; needs no open terminal (D19) |
| `title`, `records`, `logs` | yes | they read the system and write only the private records |
| `export` | yes | 22d's folder export; from R29 it replaces 22d's `export-routine` line |
| `reboot` | yes | the restart, after his go; refuses a stale title, an attached stick and a layout trial (`:1971-1983`) |
| `layout` | refused | needs the physical recovery login (fact 5) |
| `login` | refused | his registry token at a hidden terminal prompt, typed by him and never through Claude (fact 5) |
| `install` | refused | only a bundle's start block runs it |
| `prepare`, `verify`, `switch` | refused | first-switch words: they run on plain Bazzite before any AresOS (`before_switch`, `:1574-1586`) |

**A refused word** opens no window and runs nothing: one line on stderr, exit status 2. Three shapes (wording: JUDGMENT-CALL 3):
- `aresos forward: use aresos update here, it goes forward by itself when a newer AresOS is installed; nothing ran` (also for `newest`)
- `aresos layout: this works only at the recovery console, typed by you: sudo /var/lib/ares/at layout; nothing ran` (also for `login`)
- `aresos switch: this belongs to installing AresOS from plain Bazzite, at the recovery console; see docs/INSTALL.md; nothing ran` (`install`, `prepare`, `verify`, `switch`, `keep-stock`)

An offered word followed by anything else is refused the same way ("takes no further words"), so no stray argument reaches `sudo` or the tools' records (`owner.py:2893-2894`).

Run as root, or with no desktop session (neither `WAYLAND_DISPLAY` nor `DISPLAY`), an offered word is refused with the full-path command for the console: `sudo /var/lib/ares/at <inner word>`, which for `update` is `sudo /var/lib/ares/at newest`. `aresos update` and the inner `update` differ in exactly the danger state, so **no line the dispatcher can print or exec contains `at update` or `at forward`**; a test holds that over the whole table.

## 3. The password window (D7 to D9)

**D7: 22d's mechanism, unchanged.** `SUDO_ASKPASS=<helper> SSH_ASKPASS_PROMPT= /usr/bin/sudo -k -A -p '<label>' /usr/bin/bash -c '/var/lib/ares/at <inner word>'` (`os/owner-tools/bootstrap.py:106-116`). The root command keeps 22d's form (`export-routine`, `bootstrap.py:128-130`), the one rehearsed behind this window. A direct `/var/lib/ares/at …` works as well: the guide's `sudo -k; sudo /var/lib/ares/at layout proof` is typed from the non-root tty4 login and has passed in the VM since qualification 21 (`docs/INSTALL-PROCEDURES.md:18`). It would only be tidier in `sudo`'s journal, and with D18 the directory no longer matters for either, so the rehearsed form stays. One window per `aresos` word. `update`'s and `forward`'s results already end in the title's lines (`owner.py:1850`, `:1688`), so an update needs no second window for the title; the restart is its own word and its own go.

**D8: the label is `AresOS: <fixed phrase>`, with no fingerprint.**
- In 22d the 8 characters name what is about to be installed from Claude's hands, and he compares them once with a public line. An `aresos` word installs nothing from Claude's hands: the command behind the window is fixed in the image, and the tools it runs went in under that earlier compare.
- To show a fingerprint, root would have to publish it where `ares` can read it, and then any program can show it too. It would add a compare to every command and prove nothing.
- So the honest answer to "how does he know the window is AresOS's own": from the window alone he cannot (fact 8). **His rule** for these windows: type the password only when (1) he told Claude to go just now, (2) the title bar says **Enter SSH Credentials**, and (3) the line inside starts with **AresOS:** and is the line for what he asked for, as the guide lists them. Otherwise Cancel. The guide repeats 22d's limit in the same words: the window stops accidents and a Claude that acts without asking, not a Claude that was tricked.
- What the image adds over 22d: the root command is a fixed short line, so `sudo`'s journal entry names exactly what each window approved (seen in `STEP-0.md`).

Proposed lines (wording: JUDGMENT-CALL 1). Each matches 22d's rule `[A-Za-z0-9 ,]+: [A-Za-z0-9 ,]+` (`bootstrap.py:91-104`), matches none of the helper's 16 remembered-prompt patterns (each needs a quote or a trailing ": "; `os/tests/test_owner_bootstrap.py:220`), and is shorter than the 70 characters 22d's walk shows wrapped:

| Word | Line in the window |
|---|---|
| `update` | `AresOS: update to the newest AresOS` |
| `previous` | `AresOS: go back to the previous AresOS at the next start` |
| `rollback` | `AresOS: go back to plain Bazzite at the next start` |
| `check` | `AresOS: check this system` |
| `title` | `AresOS: read what starts next and the boot menu rows` |
| `records` | `AresOS: read the disk records` |
| `logs` | `AresOS: save the log of the last start` |
| `export` | `AresOS: export the records` |
| `reboot` | `AresOS: restart the laptop now` |

The `update` line cannot say which row of D2 will run: that is known only as root (fact 6). The tools say it right after the password and before any change (D4), and Claude tells him.

**D9: the window closes by itself.** `SUDO_ASKPASS` is a root-owned two-line helper, `/usr/libexec/aresos-askpass`, which runs `/usr/bin/timeout --foreground -k 10 600 /usr/bin/ksshaskpass "$@"`. After 10 minutes without an answer the window closes and `sudo` ends as after Cancel (`sudo: no password was provided`, exit 1): the helper's end without output is the path review 4 of 22d read in `sudo`'s source (`22d:reviews/22d-tools-without-stick/REVIEW-4.md:26`). `-k 10` ends a helper that ignores the first signal. The helper with `timeout` in front has not been run; step 0's try and the check build show it (section 7). Why build it in: 22d's rule has Claude find and stop the right process by hand, and review 2 showed what the wrong one costs (`REVIEW-2.md`, R1). If he has answered, the helper is gone and `timeout` has nothing to stop. The dispatcher execs `sudo`, so the process Claude started is `sudo` itself. Claude still starts an `aresos` word in the background and waits: an update may take about 70 minutes at the most (verification and staging have 30 minutes each, `owner.py:82`, and the stop routine about 11, `:523-526`). 22d's own two lines keep their rule; they are generated in the bundle and cannot use an image file.

## 4. The dispatcher (D10 to D12)

**D10: one file, `os/config/usr/bin/aresos`,** root-owned 0755, `#!/usr/bin/python3 -ISB` (one argument, as the kernel passes it). Python because the whole behaviour is then one table and one pure function that tests call directly, as they load the other extension-less helpers (`os/tests/test_aresos_shell.py:21`):
- `TABLE`: for each of the 18 tools words either (inner word, label) or a refusal line.
- `plan(argv, environ, account)` returns either an exec (path, argv, environment) or a refusal (line, status). `account` is the caller's entry in the account database (user id, name, home). It reads nothing else.
- `main()` looks up the account, then execs the plan or prints the refusal. No subprocess, no parsing of any output, no file read or written.

**It is not a security boundary.** It runs as `ares`, and everything it does `ares` can do by hand; the boundary is `sudo` asking for the password every time, and D18 in the tools. The fixed paths and environment are there so that every run is the same, not to stop a hostile caller.

**D11: the environment for `sudo`** is built from nothing:
- fixed: `PATH=/usr/bin:/bin`, `LANG=C.UTF-8` (so the title bar reads as the guide quotes it), `SUDO_ASKPASS=/usr/libexec/aresos-askpass`, `SSH_ASKPASS_PROMPT=` (22d's review 2, N5);
- from the account database, not from the caller: `HOME`, `USER`, `LOGNAME`. Without `HOME` the helper's toolkit takes `/` as his home and the window may look different from 22d's;
- from the caller when set, because they say where his screen is: `XDG_RUNTIME_DIR`, `WAYLAND_DISPLAY`, `DISPLAY`, `XDG_SESSION_TYPE`, `DBUS_SESSION_BUS_ADDRESS`.

The dispatcher does not change directory: `sudo`'s journal line keeps saying where a word was started (`PWD=`), and the protection must not sit in a file that is no boundary. With D18 the tools run every step from `/` whoever starts them: what reaches a root step is `sudo`'s own reset environment and the directory `/`, and no directory of the caller.

**Step 0's try on the laptop** (JUDGMENT-CALL 6; it shows D9 and D11 before anything is built). The helper is a copy in his home with 60 in place of 600; the command behind the window is `/usr/bin/true`:
1. `/usr/bin/env -i` with exactly D11's values, then `/usr/bin/sudo -k -A -p 'AresOS: test' /usr/bin/true`. He types his password. Expected: the window of 22d's step 0 (the title bar, the line inside, no keyring question), exit 0, `sudo -n true` refused afterwards, `COMMAND=/usr/sbin/true` in `sudo`'s journal.
2. The same line once more; he leaves the window alone. Expected: it closes after one minute, `sudo: no password was provided`, exit 1, nothing ran.
3. Only if the first window does not open or looks different: the same with the caller's whole environment and the fixed values set, to learn which variable is missing (LEAD 5).

**D12: Control.**
- Control's wrapper (`18c:control/packaging/aresos`, three lines) is installed unchanged as `/usr/libexec/aresos-control/cli`: one changed entry in the install map (`18c:os/build.sh:92`) and its pin (`18c:os/tests/test_control_image.py:25`). The file is then inside the folder the launcher already requires to be root-owned and not writable (`18c:control/launch.py:16-20`, `:31-35`) and stays recorded in `control.json`.
- A first word that is not one of the 18, no word at all, and `--help` are handed on by exec with the arguments, the environment, the directory and the terminal exactly as given, as `ares` and as root alike: Control's owner commands are typed as `sudo aresos admin …`, and `aresos admin mail account add` reads a password from the terminal (`18c:control/aresos_control/cli.py`). The dispatcher knows none of Control's words, so Control can add apps without an OS change, and an unknown word gets Control's own error.
- If the image has no Control, the same cases print the nine offered words and exit 2.
- **Who calls `/usr/bin/aresos` on Control's side** (review 1, S7; step 0 tells `linux-tools`):
  - `18c:os/build.sh:270` runs `aresos --help` during the image build. The order is already right: the Containerfile copies `os/config` first and runs `build.sh control` after it (`18c:os/Containerfile:32`), so the dispatcher is in place. The map entry must move in the same commit as the dispatcher arrives, or the map writes Control's wrapper over it.
  - `18c:os/ci/image-checks.sh:821-823` compares `aresos --help` as root and as `ares`; it passes unchanged and proves the hand-over.
  - `18c:os/ci/control/actions.py:100` and `18c:control/ci/image/mail_flows.py:56` run in the image and keep working through the hand-over; the second needs the terminal passed through.
  - `18c:control/tests/test_integration.py:359` runs in a tree that holds the install map alone (`build.sh control-tree`), which has no dispatcher. It calls `/usr/libexec/aresos-control/cli` from then on; that change is `linux-tools`'s.
- `newest` joins Control's `RESERVED` (`18c:control/tests/test_reserved_words.py:13-14`), a one-line change for `linux-tools`. A new OS-side test reads three sets and requires them equal: the tools' `known` (`owner.py:2890-2891`), Control's `RESERVED`, and the dispatcher's offered plus refused words. So a new tools word fails a test until all three know it.
- Control drops its top-level `log` shortcut and keeps `aresos control log`, so `aresos logs` (the tools' word) is the only word of that shape (agreed with `linux-tools` on 2026-11-13, board #199, and confirmed 2026-11-15). That change is on Control's side and lands with this package.

**Tests** (`os/tests/test_aresos_command.py`, no root, no fakes of `sudo`):
- for each offered word, the exact argv and environment; `update` maps to `newest`;
- no string the dispatcher can print or exec contains `at update` or `at forward` (every row, every refusal, the root and no-session lines);
- the three word sets; the labels against 22d's character rule and its pattern list (imported, not copied), their length, and that they differ;
- every refusal: its line, status 2 and no exec; extra words; root; no desktop session;
- hand-over: argv and environment unchanged for other words, none and `--help`, as `ares` and as root; the usage when Control's file is missing;
- one test runs `main()` in a child process on a pseudo-terminal, with the hand-over target pointed at a stand-in: the stand-in sees a terminal on stdin and the arguments unchanged;
- `main()` execs and the module imports no `subprocess`; the helper's two lines are pinned;
- the guide's table of words and window lines equals `TABLE` (lands with the guide, step 4).

**D16: in the image.**
- Two new `os/config` files (the dispatcher, the helper), both committed executable, and Control's moved wrapper. No new package: `ksshaskpass`, `timeout` and Python are in the image already.
- `os/ci/image-checks.sh`: owner, mode and no link for both files; a refused word's line and status as `ares`; an offered word without a desktop session refuses without calling `sudo`; the helper and `timeout` exist; and `ksshaskpass`'s package version equals the one whose patterns were read (6.7.5), so a new version fails the build until someone reads its patterns again (asked for in `22d:reviews/22d-tools-without-stick/REVIEW-1.md:130`).
- These checks run only where an image is built: `os/ci/check-image.sh:13` is their one caller, in a check build or a release build. The checks-only job runs the unit tests alone (`.github/workflows/os-image.yml:93`, `:207`). So step 3 ends with a check build (section 7).
- The release diff for R29 needs no new rule if step 3 gets it right: both `os/config` files are explained by `config_rule` (bytes equal the source, 0755, root; `os/ci/release_diff.py:212-229`), and `/usr/bin/aresos` leaves `control.json` while `cli` enters it. Step 3 adds a test that feeds these three paths to the diff's rules, so R29's release package does not meet an unexplained file.

## 5. What `aresos update` says (D13)

Every line below is the tools' (wording: JUDGMENT-CALL 2). `<name>` is the title's name for a system (`owner.py:752`); `<newest>` stands for `sudo /var/lib/ares/at newest`, spelled by `typed()`.

| Row of D2 | Lines, in the order they appear |
|---|---|
| 2, not applied | `Update to <reference> was not applied: the deployments are as before it, and nothing is waiting` (the survey's own line, at once); `Nothing changed: the last update did not finish at shutdown. Before repeating it see EMERGENCY, Failed or bad update; <newest> then repeats it` |
| 3, record | `Update: the interrupted update to <reference> is staged already; recording it`; for every other installed AresOS `<Role> <reference> is removed when the update finishes at shutdown` (the inner word's sentence, `:1845-1846`); then the inner word's lines |
| 4, continue | `Update: continuing the interrupted update to <reference>`; then the inner word's lines |
| 5 | the STOP of section 1 |
| 6, an update waits | `Nothing to do now: the update to <reference> is staged and starts at the next restart` |
| 6, a forward waits | `Nothing to do now: the forward to <reference> waits for the restart` |
| 6, a return waits | `Nothing to do now: the <return to / rollback to / change to> <reference> waits for the restart, and this command changes nothing before it. After the restart, <newest> goes forward again` (the middle words are the journal's own, `Tools.change`, `:1274-1278`) |
| 7, install | `Update: installing the new AresOS release <reference>. This downloads it; it starts at the next restart`; then the inner word's lines |
| 8, nothing to update | `Nothing to update: <name> runs and starts next, and it is the newest AresOS these tools know; nothing changed`; `Owner tools version <N>: <8 characters>`; `A newer AresOS comes with newer owner tools, after the maintainer's announcement; docs/OWNER-TOOLS.md on GitHub names the current ones` |
| 9, already | `<Name> already starts next; nothing changed`; `It does not run yet: it starts at the next restart` |
| 10, an older AresOS runs | `Update: a newer AresOS is installed already, <name>; going forward to it. Nothing is downloaded and nothing is removed` |
| 10, plain Bazzite runs | `Update: plain Bazzite runs here and <name> is installed; going back to it. Nothing is downloaded and nothing is removed` |
| 10, N runs | `Update: this is the newest installed AresOS, but <name> starts next; making this one the next start again. Nothing is downloaded and nothing is removed` |

After rows 9 and 10, when T is not installed, one more line: `These tools also carry a newer release; after the restart, <newest> installs it`. It informs; the guide does not tell him to follow it without the release's announcement (fact 9).

**"Nothing to do" and "newer tools would bring a newer release" are one state to the tools** (row 8): N runs and starts next, and T is N. The tools work offline and know no release after T. So row 8 prints the tools' own version line in the form of line 1 of `docs/OWNER-TOOLS.md`, and Claude compares it with that file on GitHub's main:
- equal: there is nothing newer; done;
- different: main carries other tools. That is not an announcement and not a go. Claude tells him, and waits for the maintainer's board note with the announced commit and for his go, as 22d's box says (`docs/INSTALL.md:224`: "Claude installs only that commit, never the newest one on GitHub by itself").

**The order after an announcement of a new release:** the new tools first (22d's route: his 8-character compare, one window), then `aresos update`, which installs their release. So the "Nothing to update" window is not spent just to learn the version. Row 8 still costs one window, because only root can read the tools; the guide therefore has Claude run `aresos update` after an announcement or after `previous`, not as a daily habit.

## 6. The guides (D14)

- **`docs/INSTALL.md`, "Update AresOS to a new release":** one new box after 22d's routine box (`docs/INSTALL.md:228`), "From Claude's terminal, on AresOS 29 or later":
  - the nine words with their window lines (the table of section 3, held equal to the dispatcher by a test);
  - his three-condition rule and the limit sentence;
  - that the window closes by itself after 10 minutes;
  - what `aresos update` prints in each row of section 5, with a pointer to the console box whose lines then follow ("Stage the new release", `:325`, or "Forward again", `:381`);
  - **one rule for reading the tools' messages:** a line that names `sudo /var/lib/ares/at <word>` means `aresos <word>` from Claude's terminal; for `newest`, `update` and `forward` it always means `aresos update`; a word the table refuses (`login`, `layout`) stays at the console, typed by him;
  - the order after an announcement (tools first, then `aresos update`), and that a different line in `OWNER-TOOLS.md` is not a go (section 5);
  - after an update that did not finish: `aresos check` first, as the card says; the first `aresos update` after it only says `was not applied`, and a second one repeats the update, with Help;
  - `aresos update` again before the restart answers `Nothing to do now`; that is a PASS, not a problem;
  - before `aresos reboot` after a run that changed nothing (`Nothing to update`, `already starts next`, `Nothing to do now`): `aresos title` first if `reboot` says the title is stale. Those runs save no title (`owner.py:1977-1978`);
  - `aresos rollback`: after its restart he is on plain Bazzite, where there is no Claude and no `aresos`; the way back is `sudo /var/lib/ares/at forward`, typed by him at the console. "Roll back the update" in his words usually means `aresos previous`; Claude says which of the two it is about to run and where he lands, and waits for his go;
  - `Registry login missing, expired or unreachable`: check the network first; a new login is typed by him at the console (`login` is refused here);
  - `Another owner command is running`: like Cancel, nothing ran. Let the first one finish and run the word again; no export routine;
  - that Claude posts the title's lines to the board after every word that changes what starts next (22d's decision 8);
  - after any other STOP: every STOP line word for word, his go, then `aresos export`, nothing else.
- 22d's box loses "every other owner command stays at the console … until a later release brings it here" in favour of "from AresOS 29 the next box".
- **The console boxes do not change**, rule for rule. They are the way that always works and the only way on plain Bazzite, on a release before 29 and when the desktop is down. They keep `update` and `forward`; `sudo /var/lib/ares/at newest` is named once, as what `aresos update` runs and as usable there. (An owner command in a guide is written in full: `test_owner_equality`'s inline-command rule refuses a bare tools word in code type once `commands.json` knows it.)
- **`docs/EMERGENCY.md`:**
  - "Failed or bad update" (`:18`) gains two sentences: if the desktop works, Claude runs `aresos check` and then, only as that card already says, `aresos previous`; and `aresos update` after an update that did not finish only says so the first time.
  - "A routine tools command stopped" (`:64`) also covers `aresos` words, with `aresos export`.
  - One line near the top: `aresos` exists only on AresOS 29 and later; everywhere else use the full path at the console.
  - The card stays one page.
- `docs/INSTALL.md:191` describes `check`'s proof as "running labwc/foot"; with D19 it names the session's own program.
- `docs/INSTALL-STATUS.md`: a row for the `aresos` route, open until R29's rehearsal; after 43's VM run a row for its tools (section 8). `docs/OWNER-TOOLS.md`: the new fingerprint, same form. `os/owner-tools/commands.json`: one entry, `newest`. `os/README.md`: one paragraph.

## 7. Proof and budget (D15)

**Unit tests.** Section 4's for the dispatcher, D18's and D19's for the two repairs. For `newest`, one row per row of D2 and per wording of section 5, each giving the first line, the chosen word, what changed and how it ends:
- rows 0 and 1; row 2 for a staging journal (stops there) and for a reorder's journal (its line first, then the table goes on);
- row 3 on N and on an older AresOS (the removal line names the newer one); rows 4 and 5;
- row 6 after `update`, `previous`, `rollback`, `keep-stock` and `forward` without a restart: a PASS, no inner word, no journal change, nothing announced;
- rows 7 and 8; row 9 with an older AresOS and with plain Bazzite running; row 10 in its three wordings; the extra line after rows 9 and 10;
- every read-only refusal of the chosen word (no login, no network, a layout trial, a busy deployment tool, a staged row without a journal) with **no announcement before it**;
- the guard after each `may_stage`, behind `:1810` the second time, with its text; `:1323-1324` naming `typed('newest')` for `newest` and `typed('update')` for every other word;
- the survey's lines printed once, before the first line; `chosen` and `said` in the PASS record and the STOP record; that older tools refuse `newest`.

**The model:** section 1.

**One check build, at the end of step 3** (`check_build=build` on the branch: a throwaway image, never published, no owner OK needed). It is the first run of step 3's image checks, and it boots the image once in a VM. If 22d's window driver (`os/ci/tools_local.py`) can be used in that VM pass without a harness of its own, the pass drives one window with the made-up `ares` password the image checks already use: the helper's argument equals the label, Cancel runs nothing, `sudo -n true` is refused afterwards. If it cannot, the builder says so in `PROGRESS.md`, and D9 and D11 rest on step 0's try until R29's rehearsal.

**A VM run of 43's own, before merge, for the tools at the console.** Why its own: the tools change is what can replace a system, the lead asked for a rehearsal (`STATE.md:14`), and the fingerprint must not reach the laptop unrehearsed. Why at the console: R28 has no dispatcher (fact 7). It reuses release 28's rehearsal mode (`briefs/42-release-28.md`, B) with 43's bundle:

| Stage | What | Proves |
|---|---|---|
| 1 | On R27 (runs, starts next): `at newest` instead of `at update`, typed from a folder that holds a marker-writing `json.py` and `subprocess.py` | It announces the install and stages R28; no marker was written (D18, `update.sh`) |
| 1b | `at newest` again, before the restart | `PASS newest`, `Nothing to do now: the update to … is staged …`; nothing announced, nothing changed (row 6; review 1, B1) |
| 2 | On R28 after the restart: `at newest` | "Nothing to update", the tools' version line, no change |
| 2b | On R28: `at check`, with no `foot` of `ares` running if the harness can end it | `PASS check`; its saved record shows the read of `aresos-desktop` passing and no read of `foot` (D19) |
| 3 | `at previous`, typed from the marker folder; `at newest` before the restart; restart; on R27: `at newest`; restart; `at check` | No marker (D18, `start-next.sh`); `Nothing to do now: the return to … waits …`; then it announces forward; nothing staged; "Forward to … confirmed" |
| 4 | `at previous`, restart: R27 runs, R28 is installed. Then a harness-built next bundle whose release is a made-up one that is not installed (installed as in 22d's "stick with a next version" stage), then `at newest` | The danger state: forward, no login asked, no network, R28 still in the list |
| 5 | The same `at newest` once more, with a hard reset between the journal's intent and its record | After the restart it resolves as a cut `forward` does |

Every stage keeps package 11's audits. Row 2 gets no stage: an update that does not finish at shutdown is in the model (a power-off with a staged release) and in the unit rows, and `newest` adds no change of its own there.

**The dispatcher rides R29's release rehearsal,** because only that image has it and only there do the real image, the real tools and a real update meet. Stages for R29's release brief, on R29 after the update:

1. `aresos --help` equals Control's help; `aresos layout` refuses with no window.
2. `aresos check`: the helper's argument equals the label, a screenshot, no keyring process; Cancel runs nothing; then the password and `PASS check`; `sudo -n true` is refused afterwards (22d's driver, `os/ci/tools_local.py:488`).
3. `aresos update`: "Nothing to update".
4. A window left unanswered closes after 10 minutes; `sudo: no password was provided`; nothing ran.
5. `aresos previous`, started from a folder that holds the two marker files: no marker. `aresos update` before the restart: `Nothing to do now`. `aresos reboot`; on R28 at the console `at newest` goes forward; back on R29 `aresos check` shows the confirmation.

**Staging through the dispatcher** first happens in R30's rehearsal (R29 to R30 by `aresos update`), before any laptop session does it. Until then its staging branch is proven at the console (stage 1) and its mapping by the unit tests.

**Budget for 43's ledger entry:** 15 checks-only runs, 2 check builds, 4 VM dispatches, 2400 minutes. 22c and 22d both began at 1200 and were raised to 2400, because one VM dispatch reserves 345 minutes (`os/ci/rehearsal-packages.json`); the caps stop runaway loops, the runners cost nothing for this public repository.

## 8. Build steps

One fresh builder each, gpt-6.1-sol at xhigh against a tight brief, about 250k tokens; each commits, pushes and keeps `reviews/43-aresos-command/PROGRESS.md`. Reviews on gpt-6-astra. If the model step resists two rounds, it goes to Fable. (The lead picks the model again per step; Codex ends 2026-11-21. Step 1 changes what can replace a system and closes a root hole: LEAD 10.)

| Step | What | Needs |
|---|---|---|
| 0 | The lead: `linux-tools` is told (D12, with its list of callers); with the owner's OK, the laptop try (section 4) | this note READY |
| 1 | Tools: D18 and D19 with their tests; `newest` with D2's table, D3's guard, D4's function, the lines, `chosen` and `said`; their unit tests. The payload and every pin of the fingerprint; the `commands.json` entry with its guide sentence; the waiting rows | main merged into the branch (it stands on `4d23b408`, before 22d); **no row of `docs/INSTALL-STATUS.md` says "VM REHEARSAL PASSED; NOT ON THE LAPTOP"** (below) |
| 2 | The model: the ledger's `choose`, the driver, I1 to I4; the hosted full model; its time before and after | step 1 |
| 3 | The dispatcher, the helper, their tests, the image checks, Control's moved wrapper with its pin, the three-set test, the diff test; then one check build | 18c Part A on main, or the lead's word that Control does not ride. Not held by the status rows (no tool, release script or guide changes) |
| 4 | The guides and the card, the equality tests, the owner's wording; the payload and its pins once more if a tools line changed | steps 1 to 3 and the owner's wording; no status row says the phrase |
| 5 | Review of steps 1 to 4 | |
| 6 | The harness variant, its ledger entry, the workflow's entries, 43's host-walk receipt and local walk, hosted checks with the full model on the same head, the VM run, the record step | R28 published and its rehearsal mode on main |
| 7 | Hand-over: the five rehearsal stages and D16's diff note into R29's release brief | |

**The binding rules the steps meet** (review 1, S4; 22d's steps are the pattern, `reviews/22d-tools-without-stick/REPORT.md`):

1. **The payload equals its sources.** `bundle.check` fails as soon as `owner.py`, `at` or a release script differs from `os/owner-tools/payload/` (`os/owner-tools/bundle.py:50-58`, `os/tests/test_owner_equality.py:48`). So step 1 cannot leave "payload and pins" for later. In the commit that changes a payload source it runs `python3 os/owner-tools/bundle.py --refresh` and moves every pin of the fingerprint:
   - `os/owner-tools/history.json`: the next tools version (an install refuses the same version, `owner.py:2651-2652`). If main's version moves before 43 merges (R28's bundle), 43's moves above it at the next merge of main;
   - `docs/OWNER-TOOLS.md` (lines 1 and 3), `docs/INSTALL.md` (the blocks and the fingerprint), `docs/EMERGENCY.md` (the export window's 8 characters), `os/owner-tools/commands.json` (the generated lines);
   - 22d's status row keeps its fingerprint as 8 characters once the payload moves (`check_fingerprints` refuses a full fingerprint that is not the payload's; 22c's row shows the form).
   The payload is regenerated, never merged by hand: after every merge of main, refresh and pin again. The pins move once more in step 4 if a tools line changes with the owner's wording.
2. **Every changed bound file has its row on the waiting list.** After the last change to a bound file in a commit: `python3 reviews/27-first-update-release/rebind.py pending "<note>"`; `test_checkout_sources` compares the list with what that tool finds (`os/tests/test_checkout_sources.py:188-191`). The tool decides what is bound, not this note. In the active bindings (`os/manifest/ci/22d/source-bindings.json`, 263 paths) are `owner.py`, `at`, the payload, `commands.json`, `history.json`, every release script this package changes except `update.sh`, `docs/INSTALL.md`, `docs/EMERGENCY.md`, the workflow, the budget ledger and several tests; not in them are the model's two files, `docs/INSTALL-PROCEDURES.md`, the image checks and the two new `os/config` files.
3. **While any status row says "VM REHEARSAL PASSED; NOT ON THE LAPTOP", nothing under `os/owner-tools/`, `os/release/` or `docs/` may wait,** and the payload must be the newest rehearsal's tools (`:25-31`, `:107-149`). Two rows say it on main at `937a1868`: 22c's and 22d's.
   - 22d's row moves to "ON THE LAPTOP" when the laptop has run version 4's install (expected 2026-11-16). That frees the payload: the payload rule binds only the newest rehearsal's row.
   - 22c's row says the phrase for version 3, which never goes on the laptop (board #265); version 4 carries its ways back. The waiting rule looks at every row, so **steps 1 and 4 need 22c's row moved as well**, in the same commit as 22d's or in one of its own; its words are the lead's, and its pin in `os/tests/test_owner_path.py:1769-1772` follows.
   - Steps 1 and 4 check before their first change that `grep -c 'VM REHEARSAL PASSED; NOT ON THE LAPTOP' docs/INSTALL-STATUS.md` prints 0 on the merged base, and stop with a note to the lead if it does not.
   - Steps 2 and 3 are not held: test, harness, workflow and image files may wait while a row stands. If steps 1 and 4 must wait for the rows, step 3 may be built first; the three-set test then lands with step 1.
   - Release 28's row will probably say the phrase between its rehearsal and the laptop's update. If main gains such a row while 43 is open, `test_a_row_that_says_vm_rehearsal_passed_holds_only_what_the_rehearsal_ran` is red on the merged branch until that release is on the laptop or until step 6's record step, whichever comes first. The builder names it in `PROGRESS.md` and never weakens it; the lead decides whether 43 waits (LEAD 11).
4. **`newest` is a command no rehearsal has walked.** Its `commands.json` entry (`"newest": "sudo /var/lib/ares/at newest"`) lands in step 1 with two things `test_owner_equality` asks for in the same commit: the one guide sentence that quotes it (section 6, the console boxes), and its name in `unwalked_commands` of `os/manifest/ci/16/pending-rebind.json` (`os/tests/test_owner_equality.py:233-256`). It leaves that list in step 6, when 43's walk types it.
5. **Tests that stay red until step 6:** none are expected. If one can pass only after 43's own walk (a host-walk receipt, a status pin), the builder names it in `PROGRESS.md` with the reason.
6. **Step 6's entries:**
   - `os/ci/rehearsal-packages.json`: an entry `43` (branch, caps of section 7, job bounds, titles);
   - `.github/workflows/os-image.yml`: `pkg/43-aresos-command` in `REHEARSAL_PACKAGE` (`:46`) and in each condition that names 22d's branch for the tools-local shape (time limits, apt retries, the walk and evidence steps);
   - 43's route in the local walk (`os/tests/test_owner_walk.py`), which types `sudo /var/lib/ares/at newest`, and its host-walk receipt (`reviews/43-aresos-command/walk-host.py`, `os/manifest/ci/43/host-walk.json`);
   - a checks-only run on the same head whose full-model job passed, before the VM dispatch (`rehearsal_guard.model_gate`);
   - the record step: `rebind.py rebind 43 <43-bound-sources.json> <run id>` (it writes `os/manifest/ci/43/source-bindings.json` and empties the waiting list and `unwalked_commands`); 43's row in `docs/INSTALL-STATUS.md` with "(package 43)", one `[rehearsal run <id>]` link and "Tools fingerprint"; `REHEARSED_TOOLS['43']` with the field of 43's result that names its tools (`os/tests/test_checkout_sources.py:31`).
   From that record step until 43's tools are on the laptop, no tool, release script or guide may change without a new VM run. So the owner's wording is settled before step 6.

## 9. The seam for the online update (D17)

- **Carries over:** the dispatcher's table (the online package changes the `update` row's root command and nothing else); the labels and the helper; `newest` as the tools' rule for "one thing per run"; the guide's box; the rehearsal's window stages.
- **The one message that changes:** "Nothing to update … the newest AresOS these tools know" becomes an answer from the registry.
- **Deliberately not built:** a registry query, a signature check outside the tools, tools inside the image, a sudoers or polkit rule, a service, a timer, a helper with its own window.

## JUDGMENT-CALL (for the owner)

What he sees, types or decides; each with a recommendation. Everything else in this note is decided and recorded with its reason. He settles the words before step 6: after 43's VM run, a changed line inside the tools needs a new VM run. After review 1: calls 7 and 8 are new, call 2 covers more lines, and call 6 asks for two windows instead of one.

1. **The nine lines in the password window** (section 3's table). Recommended as proposed.
2. **What `aresos update` prints** (section 5's table), and that its result begins with `PASS newest`. After review 1 it has more lines: when he runs it a second time before the restart it says `Nothing to do now: the update … is staged and starts at the next restart` and ends with PASS, not with a STOP; going forward has three wordings, by what runs. Recommended as proposed.
3. **What a refused word says** (section 2's three shapes). Recommended as proposed.
4. **The title bar stays "Enter SSH Credentials".** A window titled "AresOS" needs a small helper of our own; it would look better and prove nothing more. Recommended: keep it until the online update, so that every AresOS password window looks the same.
5. **The restart stays its own word and its own window** (`aresos reboot`); an update never restarts by itself. Recommended.
6. **His OK for one harmless try on the laptop** (section 4): two password windows with the line `AresOS: test`, in front of a command that does nothing. He types his password into the first and leaves the second alone for a minute, to see it close by itself. Recommended: yes, before step 3 is built.
7. **After an update that did not finish, the first `aresos update` only tells him.** It prints that the update was not applied, changes nothing and points to the card; running it a second time repeats the update. The other way (repeat at once) saves one window and repeats a failed update without anyone deciding. Recommended: tell first, as proposed.
8. **`aresos rollback` from Claude's terminal.** It works, but after the restart he is on plain Bazzite, where there is no Claude and no `aresos`: he types the way back himself at the console (`sudo /var/lib/ares/at forward`). The other way is to keep `rollback` at the console only. Recommended: offer it, with two rules for Claude: "roll back the update" means `aresos previous` unless he says plain Bazzite, and before `aresos rollback` Claude says in one sentence where he lands and waits for his go.

## Open points for the lead

1. **The inner word's name,** `newest`. It shows in `PASS newest` and in the records.
2. **`forward` refused** (section 2). Offering it too is defensible; `rollback` is JUDGMENT-CALL 8.
3. **D9's helper** against keeping 22d's hand rule for every word.
4. **`bash -c` against a direct root command** (D7): answered by review 1 (N2). Both work; the rehearsed form stays.
5. **D11's variable list.** Step 0's try shows whether the window opens with it. If not, pass the caller's whole environment with the fixed values set, as 22d's lines in effect do.
6. **Routine lines for R28.** Without them the update to R29 is still typed at the console, and the first update Claude can run is R29 to R30. 43's bundle could carry three more of 22d's generated lines (`newest`, `reboot`, `check`, each with the tools' 8 characters) so that the update to R29 already runs from Claude's terminal. Recommended: yes, as a last separable step with its own window stage in the VM run, if the lead wants that update without the console; they go when R29 is on the laptop.
7. **With `linux-tools`:** `newest` in `RESERVED`; the wrapper's move and its header comment; the callers of D12; whether Control's help gains one line that names the nine words (today `aresos --help` shows Control's words only).
8. **`check` on release 28 before 43's tools** (D19, last point): R28's guide needs "open the Terminal app first", or 43's tools go on before the next `check` in the hub.
9. **The model's time** after step 2: if it outgrows the hosted job, split the job, never the exploration.
10. **Who builds step 1.** It changes what can replace a system and closes a root hole; by the owner's rule for high-stakes work it may go to Fable, and its review is a high-stakes review either way.
11. **The status rows** (section 8, rule 3): 22c's row moves with 22d's, or step 1 waits; and what 43 does if release 28's row says the phrase while it is open.
12. **D18 sooner.** No route the guides name is open before 43's tools. If the lead wants the hole closed earlier, D18's three points are separable from `newest` as a tools change of their own, with its own fingerprint.

## Changes after review 1

Review 1 (`REVIEW-1.md`, a fresh Fable reviewer, 2026-11-16): READY WITH CHANGES. Each finding was checked against main at `937a1868` and `origin/pkg/18c-image` at `986192c3` before anything changed. All held; none is rejected. Two are settled differently from the review's proposal (S2, N4), with a dated line.

| Finding | What changed |
|---|---|
| **B1** false "going forward", then a refusal, after a staged update or a queued return | D2 is a table of eleven rows, 0 to 10 (section 1): row 6 for a change that waits (a PASS that says what waits), row 9 for N starting next while another system runs, row 10 with a wording of its own for N running while another starts next. D4: the announcement is printed only after the chosen word's read-only checks. A fourth judgment, I4. Unit rows; VM stages 1b and 3. JUDGMENT-CALL 2 |
| **B2** root steps import modules from the caller's directory | D18 (section 1a): `at` to `/`, `cwd='/'`, `python3 -I -`, four tests with planted `json.py` and `subprocess.py`. Checked: reproduced on Python 3.14.8; the console and 22d's two lines are not exposed (`commands.json`). D11 says what reaches a root step. VM stages 1, 3 and R29's 5 run from a marker folder |
| **S1** a failed update repeated without a decision | D2 row 2: the run that finds it only says so; the survey's lines are printed first. Ledger branch, unit rows, guide and card sentences. JUDGMENT-CALL 7 |
| **S2** `check` needs a running `foot` | D19: decided now, in step 1. 2026-11-16: neither of the review's two fixes as written. The release record is not changed (the running image's own file says the same, and the history's strict form stays); a guide precondition would leave `check` depending on a terminal. VM stage 2b; LEAD 8 for release 28 |
| **S3** image checks do not run in the hosted checks | D16 says where they run; step 3 ends with one check build, which drives one window if 22d's driver fits; the budget gains it; step 0's try is written out (section 4) |
| **S4** the steps and the binding rules | Section 8: the payload and pins in step 1 and again in step 4, waiting rows, the status-row rule with what 22d's and 22c's rows each need, `unwalked_commands`, `REHEARSED_TOOLS`, the workflow's and ledger's entries, the red test to name |
| **S5** no text from `aresos update` to the inner `update` | Section 2: the root and no-session line for `update` names `at newest`, with a test over every string. Section 5: the tools' lines use `typed('newest')`. The guide's reading rule. I2 defined by `typed()`; `:1323-1324` names `newest` when `newest` asked |
| **S6** case 1 and the guard | Rows 3 to 5: the decision comes before any announcement; row 5's STOP and the guard's text name no restart; row 3 prints the removal line; the second guard sits behind `:1810` |
| **S7** more callers of `/usr/bin/aresos` | D12 lists them, checked at `986192c3`; the build order is already right (`Containerfile:32`) if the map entry moves in the dispatcher's commit; a pseudo-terminal test for the hand-over; step 0 |
| **S8** a different line is not an announcement | Section 5: reworded, with the order after an announcement; the tools' third line no longer reads as a task for Claude |
| **N1** | D1: each inner word reads again, as built; guard and announcement use that read |
| **N2** | D7 corrected; LEAD 4 answered |
| **N3** | D9: about 70 minutes; `timeout -k 10` |
| **N4** | D11: `HOME`, `USER`, `LOGNAME` from the account database. 2026-11-16: the variant without `HOME` is not tried in step 0, because it is not what is built; a second variant runs only if the first window fails |
| **N5**, **N6**, **N9**, **N10** | Section 6: four sentences for the box (the wording is step 4's); N6 is also JUDGMENT-CALL 8 |
| **N7** | Section 1, "Records": `chosen` and `said` in both records; `main()` changes in three places; "no journal" is said of the journal only |
| **N8** | Section 1, "The model": the references; `newest` last in both loops; `WORDS` stays, with the reason |

Also corrected while checking: the result block starts with `PASS newest` (it was called the last line; fact 12); the references for 22d, which is on main; the budget (2400 minutes, as 22c and 22d ended).

Left for the builder: the guide's sentences for N5, N6, N9 and N10 and the box's layout (step 4); how `newest` learns that the survey closed a staging journal and how the two functions are handed down (step 1; the behaviour is fixed above); whether the check build can drive a window (step 3).
