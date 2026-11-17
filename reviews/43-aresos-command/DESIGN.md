# 43 design note: the `aresos` command

Empire brief 296. Written 2026-11-15 on main `4d23b408` by a Claude agent on Fable 5.2 (the lead's choice: a new design for a tool that decides which installed system is replaced). Revised 2026-11-16 after review 1 (`REVIEW-1.md`, READY WITH CHANGES) by a fresh Claude agent on Fable 5.2 that wrote neither the note nor the review. Revised again 2026-11-16 after review 2 (`REVIEW-2.md`, READY WITH CHANGES) by another fresh Claude agent on Fable 5.2 that wrote neither the note nor the reviews. The change sections map each revision. A design note only: it changes no tool, test, guide or workflow.

Revised 2026-11-17 after review 3 (READY), the owner's answers of 2026-11-16 and the lead's decisions; calls 1 and 2 have new proposals awaiting his OK.

Made by reading code. No owner tool, `sudo`, ostree, bootc or rpm-ostree command ran, and no window was opened. The first revision ran one Python check as `ares` in an empty scratch folder (fact 10). The second ran three, as `ares`, in a scratch folder outside the repository, with bytecode off and nothing left behind: main's `owner.py` imported as a library for `Tools.outcome` on made-up deployment lists (no tools entry ran); D18's directory layer and its `-I` layer, each without the other; and `pgrep -x` on a script started through its `#!` line.

**References.** No prefix is main. `22d:` is package 22d's tree, on main since `634e1237`; its line numbers were checked again on main at `937a1868`, where the tools, the guides and 22d's files are the bytes the note was written against, and for the second revision at `52d13cb7`, where `os/`, the guides and the workflow are byte-identical to `937a1868`. This branch still stands on `4d23b408`; references added or changed on 2026-11-17 were read with `git show origin/main:<path>` at `dcbdabe9`. `18c:` is `origin/pkg/18c-image` (PR #58), checked again at `986192c3` and for the second revision at `dada7a9b`. `owner.py` is `os/owner-tools/owner.py` throughout.

**Words.** *Inner word*: a word of `/var/lib/ares/at`. **N**: the newest installed AresOS (`newest()`, `owner.py:756`). **T**: the release the installed tools carry (`owner.py:1790`); it is last in their history, so when T is installed, T is N. *Runs* and *starts next* are the title's words: the booted deployment and the first one in the list. *Announcement*: a first line of `newest` that starts with `Update:` and says what the run is about to change.

## The decisions in short

| | Decision |
|---|---|
| D1 | The choice lives in the tools: an 18th inner word, `newest`, in one root process under the one lock. |
| D2 | Its rule is a table of eleven rows (0 to 10) over one read of the system (section 1). A run does one thing: it continues an interrupted update, installs T, goes forward to N, or changes nothing and says why. A change that waits for the restart is a PASS that says what waits. |
| D3 | Staging through `newest` carries a guard inside `update`'s own two checks: it never stages unless the running AresOS is N. The inner `update`, typed by its own name, stays as built (#263). |
| D4 | `newest` says which thing it does only after the chosen word's read-only checks have passed and before its first change. No refusal that could have been known beforehand follows an announcement: what can still stop an announced run is the act itself, or a cut. The inner word's lines, journal and refusals are unchanged. |
| D5 | `aresos update` runs `newest` and nothing else. The dispatcher has no row that reaches the inner `update` or `forward`, and prints no line that names them. |
| D6 | Nine words work from the desktop: `update`, `previous`, `rollback`, `check`, `title`, `records`, `logs`, `export`, `reboot`. Nine are refused with one line that names where they work. |
| D7 | One password window per `aresos` word, by 22d's mechanism unchanged. No sudoers rule, polkit action or service. |
| D8 | The window's line is a fixed phrase without a prefix or fingerprint. Its own character rule is in section 3. His rule has three conditions; the 8-character compare stays for new tools only. |
| D9 | A root-owned helper closes an unanswered window after 10 minutes. The dispatcher becomes `sudo` (exec), so nothing sits between Claude and it. |
| D10 | The dispatcher is one Python file, `os/config/usr/bin/aresos`: a pure `plan()` and an exec. It is not a security boundary. |
| D11 | It starts `sudo` with an environment built from nothing: fixed values, his account's own name and home, and the variables that say where the screen is. |
| D12 | Control's wrapper moves unchanged to `/usr/libexec/aresos-control/cli`; every first word that is not a tools word goes there unchanged. `newest` joins Control's reserved words, and a test holds the three word sets equal. |
| D13 | "AresOS is up to date" means the latest version these tools know. Their history and release records carry each release's number, printed as `AresOS <n>`. Row 8 also prints the tools' version line. A different line on GitHub is not a go: Claude tells him and waits for the announcement. |
| D14 | The guides gain one box in front of the console boxes, which do not change; the emergency card gains four sentences. |
| D15 | Proof: unit tests; the model with the new word and four new judgments; one check build for the image files; one VM run of 43's own for the tools; the dispatcher's stages ride R29's release rehearsal. |
| D16 | In the image: two `os/config` files and Control's moved wrapper, explained by the release diff's existing rules; the helper's package version is pinned. |
| D17 | The seam for the online update is the dispatcher's `update` row and the "nothing to do" message. Nothing of it is built. |
| D18 | No root step of the tools depends on the directory it was started from: `at` changes to `/`, every child starts in `/`, and the steps' own Python starts isolated. Three layers, each with a test that fails without it. |
| D19 | `check` asks for the program the running release's session starts (the desktop keeper from release 28, `foot` before), not for a terminal. |
| D20 | What a refused word says is the design's to decide: one line that names the word, where it works, and `nothing ran`. Claude reads these lines, and they sit in an image file that any release can change. |
| D21 | After an update that did not finish, the first owner word that runs says so, once. If that word is `newest`, its run changes nothing. Nothing durable holds the repeat back afterwards: the card's rule does ("Help decides each repeat"), and the guide tells Claude that the next `aresos update` repeats the update at once. |

## 0. Facts the design rests on

1. **The inner `update` installs T by staging and nothing else** (`owner.py:1778-1850`). It refuses with `RELEASE_INSTALLED` when T is installed but not both running and first (`:1798-1802`, text `:61-62`), and with `FORWARD_FIRST` unless the running system is an AresOS and first (`may_stage`, `:1635-1641`, text `:65-66`). When it stages, ostree's shutdown step removes the other AresOS, whichever it is (`:1816-1817`, `:1843-1849`).
2. **The danger state** (#263): an older AresOS runs and starts next (after `previous` and a restart), a newer one is installed, and the tools carry a T that is not installed. There the inner `update` passes every check, stages T and removes the newer AresOS. It says so; it is the owner's decision 5 and stays reachable by the full path.
3. **The inner `forward`** makes N the next start by one reorder and never stages (`:1953-1961`); where N already starts next it changes nothing and reads no further check (`select`, `:1683-1688`).
4. **An interrupted staging** in the same boot is `update`'s to continue; every other word stops and names it (`outcome`, `:1287-1341`).
5. **What needs a terminal or the console in code:** `login` (a hidden prompt, `:1714`), `layout` (`Tools.session()`: the physical tty3/tty4 login of `ares-recovery`, `:2078-2110`), the tools update on the stick route (`:2593`) and the first install (`:2761`). Every other word requires only root (`:2888`); the guides alone route them to the console (22d's N10, `briefs/22d-tools-without-stick.md`).
6. **The tools are root-only** (`/var/lib/ares`, 0700, `owner.py:2918-2919`). A program of `ares` cannot read what is installed, which toolset is current or its fingerprint.
7. **`/usr/bin/aresos` is an image file.** Plain Bazzite and every AresOS before R29 have no dispatcher, and plain Bazzite has no `ares` account at all (`os/release/stock-session.sh:3`). Today the full path at the console is the only route there. Section 4's planned bridge supplies just three words from Claude's terminal before R29, without a dispatcher.
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
| 2 | **This run's own survey** has just closed an update's journal as **not applied** (an update that did not finish at shutdown; `:1327-1330`) | Nothing more in this run | The survey's line, at once; then `The last update did not finish, so nothing changed. See Help before trying again` | PASS |
| 3 | An interrupted staging stands open in this boot and **is staged already** (`complete`); only its record is missing | Records it with the inner `update`. This run stages nothing | `Update: AresOS <T> is already downloaded and ready. Saving the record of the interrupted update. Restart to finish`, then what it removes at shutdown | The inner word's |
| 4 | An interrupted staging stands open in this boot, **nothing is staged yet** (`retry`), and N runs | Stages it again with the inner `update`, under the guard | `Update: continuing the interrupted update to AresOS <T>. Restart to finish` | The inner word's |
| 5 | The same as row 4, but an older AresOS runs (the staging was begun there with the inner `update`, #263) | Nothing | None | STOP, a line of its own |
| 6 | **A change waits for the restart** (`pending`: an update is staged, or a `previous`, `rollback` or `forward` of this boot is in place and its target does not run yet) | Nothing | A line that says what is ready and `Restart to finish` (section 5) | PASS |
| 7 | N runs and starts next; T is not installed | Installs T with the inner `update`, under the guard | `Update: installing the latest version, AresOS <T>. Restart to finish` | The inner word's |
| 8 | N runs and starts next; T is installed (it is N) | Nothing | `AresOS is up to date (AresOS <N>)` | PASS |
| 9 | **N starts next and another system runs** (a boot-menu start, or a forward whose restart landed elsewhere) | Nothing | `AresOS <N> will start next. Nothing changed`; `It is not running yet. Restart to finish` | PASS |
| 10 | **N does not start next**: another system runs, or N itself runs while another system starts next | Goes forward with the inner `forward` | `Update: …`, worded by what runs (three wordings) | The inner word's |

- The table is complete: the survey either stops (row 0) or returns a journal state; `retry` and `complete` are rows 3 to 5, `pending` is row 6, and every other state (none, `applied`, `done`, `elsewhere`) falls into exactly one of rows 7 to 10 by where N stands.
  - **A staged row with no journal** (review 2, N9) has no journal state, and the staged row starts next, not N: by the letter that is row 10. The inner `forward` refuses it in `may_change` before anything is announced (`:1631`, `A staged deployment already exists; do not reboot; get help`). Read as row 7 instead, the inner `update` meets the same line in the same check, so both readings end alike.
  - **After `keep-stock` nothing waits** (review 2, S4). `keep-stock` is valid only on running plain Bazzite, and its target is that Bazzite (`:1763-1776`); a target that runs is `applied`, never `pending` (`:1339-1341`; checked with main's `Tools.outcome`: `applied` after `keep-stock`, `pending` after `previous`, `rollback` and a `forward` from another system). So `newest` in the same boot is row 10 in its second wording: it goes back to AresOS and thereby undoes the keep-stock, as the inner `forward` does there today. That is wanted: `newest` typed on plain Bazzite asks for the newest AresOS, and `keep-stock` stays one word away. A `forward` that made the running N the next start again (row 10, third wording) is `applied` in the same way: no restart waits, and the next run is row 7 or 8.
- No row does two things. After a forward and its restart, the next run may install T; rows 9 and 10 say so in one more line when T is not installed (section 5).
- Rows 2, 6, 8 and 9 run no inner word, read no further check and write no journal, like the inner words where their destination starts next already (`:1685-1686`). They end with `PASS newest`, never with a STOP: a STOP's fixed last line says "do not reboot" beside a message whose point is that the restart is what comes next, and it would send Claude into the export routine.
- **Row 6 comes before rows 8 to 10** on purpose. It is the state right after every update, when the word is most likely run again; as first written, the rule fell through to "go forward" there, announced a newer AresOS that does not exist and then refused (review 1, B1). No word can undo a queued return before its restart (`may_change`, `:1628-1631`); row 6 says so and what the word does after the restart.
- **Row 2: a failed update is not repeated in the run that finds it.** The survey closes the journal and notes one line that shows only once. Staging again in the same run would repeat the update without anyone deciding, against the card ("Help decides each repeat", `docs/EMERGENCY.md:23`, `:27`), and its `was not applied` line would appear under `PASS newest` above the new staging's lines, as if it were about the new attempt. So this run only says it. A reorder's journal closed as not applied (a cut `forward`) does not stop the run: its line is printed first, then the table goes on.
- **Row 2 holds for one run, and only when `newest` is the word that finds the failed update** (review 2, S1). Every word that reads the list makes the same survey and closes the journal: `check` (`:1989`), `title` (`:1532`), `records` (`:1568`), `reboot` (`:1976`) and the reorder words (`survey`, `:1600-1606`). Once any of them has shown `was not applied`, no journal is open, and the next `newest` goes by where N stands: on N with T not installed it is row 7, which announces the install and stages again in that very run. The card puts `check` first, so that is the usual order. Checked with main's `Tools.outcome` on a made-up list with a staging journal from an earlier boot: the first survey returns nothing, notes the line and archives the journal as `not-applied`; the next survey, with `retry='update'`, returns nothing and has no note. After row 2's own run the same holds: the next `newest` acts.
- **Row 3 on an older AresOS** (the inner `update` at the console staged T there and was cut before its record): recording changes nothing on the disk and lets every other word work again, so `newest` records it. It prints the two facts about the newer AresOS that this path of the inner word does not print (`:1791-1795`): that it is removed at shutdown, and that the latest version starts with this system's settings and not the newer one's (`:1845-1849`; review 2, N7). Section 5 gives these added lines plain words and release numbers; the inner word's lines stay as built.
- **Row 5:** `newest` never stages from an older AresOS, also not to continue what the inner `update` began there. Its line: `The update to <reference> was begun on an older AresOS and interrupted; this command does not continue it; nothing changed; do not reboot; get help: EMERGENCY Failed or bad update`. It names no restart and no command.

**D21: after an update that did not finish, the tools tell once and remember nothing; the rule that guards the repeat is Claude's** (was JUDGMENT-CALL 7; the lead's decision after review 2, 2026-11-16).
- **What is decided.**
  1. Row 2 stays as it is: when `newest` is the first owner word after the failed update, it prints `was not applied`, changes nothing and ends with PASS.
  2. Nothing durable holds `newest` back after that run, or after another word has shown the line.
  3. What guards the repeat is the rule in the guide and on the card (section 6): once **was not applied** has shown, from whichever word, `aresos update` repeats the update in that very run, so Claude runs it only when Help has decided the repeat.
- **Why the design decides it and the owner is not asked.** The card decides it already: "Help decides each repeat" and "Never repeat the update without Help" (`docs/EMERGENCY.md:23`, `:27`). From what he sees he could weigh one more password window and nothing else.
- **Why no durable hold** (the review's second fix). `newest` would have to remember "a staging closed as not applied that no `newest` run has shown yet". That is a new durable state: the model does not have it, and it would hold exactly once more and then leave the same question. The card's rule covers every order of words; a second mechanism beside it could only agree with it or contradict it.
- **What he is told,** at "try this", in one sentence that is true in every order of words: after an update that did not finish, the first owner command says `was not applied`, once; if that command is `aresos update`, it changes nothing in that run; from then on `aresos update` repeats the update at once, so Claude runs it only after Help has said so.
- **Pinned** by a unit row: `check`, then `newest`, is row 7 (section 7).

**D3: the guard.** `update()` gains one optional argument that only `newest` passes. It switches the guard on and carries the function that prints the announcement (D4).
- After each of `update`'s two `may_stage` calls the guard requires that the running AresOS is N. After the first (`owner.py:1803`) it comes at once. After the second (`:1809`) it comes behind the comparison of `:1810`, so a list that changed during verification gets that line's own text, "Deployments changed during verification".
- Its refusal: `A newer AresOS than the running one is installed, and this command installs a release only from the newest; nothing changed`. It names no restart and no other command: every other word says "do not reboot" in the states where it can fire.
- `newest` has already decided from its own read (rows 4, 5 and 7), so the first guard fires only when the list changed outside the tools between `newest`'s read and the inner word's. It stays because it is checked on a read of the inner word itself: I1 below then holds by where the check sits, not by an argument about `newest`'s table.
- **The second guard cannot fire today** (review 2, N2). It sits behind `:1810`, and a list equal to the first read's has the same running system and the same N, on which the first guard has passed. It is one line, kept as a backstop for the day `:1810` changes, and it is not left without a test:
  - the guard is one method. A unit test calls it directly on a made-up read: it refuses with its text where an older AresOS runs, and passes where N runs;
  - a counting stand-in for that method shows two calls in a staging run through `newest` and none in a run of the inner `update`. That test fails when either call is taken out;
  - a list that changed during verification gets `:1810`'s text. That unit row shows an announcement and then this refusal, which D4 allows.
- Row 3 stages nothing (`:1791-1795` only records), so it needs no guard.

**D4: saying which, and when.** `update()` (through D3's argument) and `forward()` (through one optional argument handed down to `select` and `start_next`) call the function once their read-only checks have passed and before their first change:
- install and row 4: after `may_stage`, the guard, the stored login (`:1804`) and the `cosign` check (`:1805`), before the signature check, which takes minutes;
- row 3: after the check that the staged release is T (`:1793`), before the record is written;
- forward: inside `start_next`, after `may_change` and the target check (`:1647-1650`), before the journal's intent (`:1651`).

The function gets the read the inner word acts on, builds the line from it and prints it with `say` (`:512`), at once. So no refusal that could have been known beforehand follows an announcement: a missing login, a layout trial, a busy deployment tool or a staged row stops the run before anything was said.

**What can still stop a run after its announcement** (review 2, N1) is the act itself, or a cut:
- for the install and row 4: the signature check (`:1806`), and the second read behind it (`:1808-1810`). Verification takes minutes, so `update()` repeats `may_stage` on a fresh read and compares the list: a deployment tool that became busy meanwhile, a changed disk record or a changed list stops the run there, with nothing staged. Then the staging step itself may fail, which ends in the stop routine as built;
- for a forward: the step itself, whose own check may refuse before the reorder when the list changed outside the tools (`:1656-1666`).

So a unit row may show an announcement and then one of these refusals. What must never show is an announcement followed by a refusal of a check that had not yet run.

**The survey's lines come first.** `newest` prints what its survey resolved at once, before any first line of its own, so the screen reads in the order things happened; `main()` then does not print them again.

**Records.** The saved record (`…-newest.json`, and the STOP record) gains `chosen` (`update`, `forward` or none) and `said` (the lines printed before the result block: the survey's lines and the announcement). The journal is the chosen word's own: its word stays `update` or `forward`, and a row that runs no inner word writes no journal. `main()` changes in three places: the word in `known` (`:2890-2891`), its entry in the method table (`:2927-2931`), and the two record fields on the PASS and the STOP path. **The survey's lines appear once** (review 2, N6): `newest` takes every line it has printed off the list `main()` prints from (`notes`) and keeps it in `said`. The two places where `main()` prints that list (`:2933`, `:2938-2939`) then find nothing to print a second time and need no change of their own; a note that the inner word's own read adds later is still printed there, as built. A unit row holds "once" on the PASS path and on the STOP path. The result block starts with `PASS newest`. Older tools answer `newest` with "Choose a documented owner command" and change nothing (`:2910`).

**Refusals.** Every refusal of the chosen inner word passes through as it is, with its "nothing changed".
- `RELEASE_INSTALLED` and `FORWARD_FIRST` cannot come out of `newest` while the list is as `newest` read it: rows 7, 8 and 10 are exactly their conditions. A test and the model hold that.
- **One edge stays as built** (review 2, N8). The lock keeps other owner words out, not a deployment command typed by hand. If the list changes that way between `newest`'s read and the inner word's, `update()` meets its own two conditions before the guard (`:1798-1802`, `:1639`), and one of those two lines comes out, naming `forward`. Nothing changes; `forward` never stages; the guide's reading rule (section 6) turns the line into `aresos update`; and its "then run this command again" is right. The guard's text in their place would say less about what to do next, so no code is added for it.
- The STOP for an interrupted staging that fits neither list (`:1323-1324`) names the word that continues it. When `newest` asked, that is `typed('newest')`; for every other word it stays `typed('update')`, as built.
- Every line `newest` itself adds spells a command with `typed()` (`:50-52`): the full path works everywhere, and the tools cannot know whether the running system, or the next one, has a dispatcher (fact 7). None of them contains `typed('update')` or `typed('forward')`.

**The model** (`os/tests/ways_back_ledger.py`, `os/tests/test_ways_back_model.py`):
- The ledger gets its own `choose(s)`, written from D2's table and not from the tools, with one result per row. For rows 3, 4, 7 and 10, `transition(s, ('newest', phase))` is the chosen word's transition; rows 2, 5, 6, 8 and 9 are results of their own (row 2 archives `not-applied`, as `check` does there; row 5 stops; the others change nothing beyond what every survey resolves). Row 6 is the ledger's `pending` alone: after `keep-stock` in the same boot `choose` gives row 10, the forward's transition (S4).
- `newest` goes last in both loops of `steps()` (`ways_back_ledger.py:308`, `:311`), after every existing word. Each of its successors is one an earlier word already reaches, so no new state appears, the breadth-first order and the slice's pinned state count stay, and only the edge counts move. It joins the driver's method table (`test_ways_back_model.py:257-259`). `WORDS` (`:444`) is the list the 22c rehearsal typed, used by its replay; 43's run gets no replay (it adds no new primitive: every change `newest` makes is `update`'s or `forward`'s, which 22c's replay holds against the VM), so `WORDS` stays.
- The builder measures the full model's time before and after and reports it.
- Four judgments on every executed `newest` edge, by the fake's state and output before and after, like "one word per meaning" (`:266-279`):
  - **I1:** if anything was staged, the running system was N and started next before the command.
  - **I2:** no STOP out of a `newest` run, and no line `newest` itself adds, contains `typed('update')` or `typed('forward')`. (The bare word in "then update again", `owner.py:1641`, and the title's own lines are not meant. In the model the list never changes inside a command; the one edge outside it is under "Refusals" above.)
  - **I3:** the announcement was printed before the journal's intent and before the first mutation. The fake host notes the output at both.
  - **I4:** an announcement is followed by its change or a cut, never by a refusal. The model can be this strict because nothing in it fails between an announcement and its change: it has no signature that does not verify and no list that changes inside a command (those are D4's unit rows). No forward announcement is printed where the ledger's N runs and starts next or a change waits, and no line that begins `Nothing` follows an announcement.
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
  2. Every child the tools start names its directory: `Step`, `Host.read` and `Host.mutate` pass `cwd='/'` (`owner.py:377`, `:312`, `:326`), and so does the fourth and last start, `podman login` (`:1730`). `media.py` starts nothing of its own; it runs through `Host`.
  3. Every Python a payload step starts on stdin starts as `python3 -I -`: the seven starts in `update.sh`, `start-next.sh`, `switch.sh`, `system-keyboard.sh`, `pause-stock-updates.sh` and `pin-stock.sh` (two), and `owner.py:1426`. They import standard modules only. `previous.sh`, `rollback.sh` and `default-stock.sh` left the payload in 22c and stay byte-identical for the older CI modes (`os/owner-tools/bundle.py:14-16`).
  4. Tests, in a module that starts no real tools entry (so it also runs on the laptop). **Each of the three layers has a test in which the other two are absent, so each test fails when its own layer is taken out** (review 2, S3: as first written, one test ran a real `Step` from the marker folder and named "the same script without `-I`" as its control; but a fixed `Step` starts in `/`, where a script without `-I` finds no planted file either, so that control could not be built and the two layers hid each other. Tried on Python 3.14.8: from the marker folder `python3 -` ran the planted `json.py` and `python3 -I -` did not; with the directory `/` neither did). The marker folder holds a marker-writing `json.py` and `subprocess.py`:
     - **`at` alone:** the real `at` beside a stand-in `owner.py`, started from the marker folder: the stand-in sees `/`. No `Step` and no payload script take part. It fails when `at` no longer changes directory;
     - **the directory alone:** while the test's own directory is the marker folder, a real `Step` runs a script **without** `-I` (`python3 - <<'X'`, `import json, subprocess`, print the directory): it prints `/`, and no marker is written. `Host.read` and `Host.mutate` each start a program that reports its directory: `/`. Each fails when its `cwd='/'` is taken out. For all four starts together, a test reads `owner.py`'s syntax tree and requires `cwd='/'` on every `subprocess` call, so a fifth start cannot come without it;
     - **`-I` alone:** the test itself starts `bash -seu` **in the marker folder**, not through `Step`, once for each Python start line of the payload (the seven, read from the scripts, and the one `pin_step` hands to the host, `:1426`, caught by a recording host), each followed by the body `import json, subprocess`: no marker. The control is the same body behind `python3 - <<'X'`: the marker is written, which shows that the folder is live and the test can fail. It fails when any of the eight starts loses `-I`;
     - no file of the payload starts Python on stdin or with `-c` without `-I` (read from the files, so a later script cannot bring it back).

     The VM stages that run from a marker folder (section 7) prove the three layers together, which is right for the VM.
- **What walks it.** `at`, `owner.py` and the changed scripts except `update.sh` are bound files, so they wait on the list until 43's VM run. That run executes `update.sh` and `start-next.sh` in their new form, each once from a folder that holds the two marker files (section 7). `switch.sh`, `pin-stock.sh`, `pause-stock-updates.sh` and `system-keyboard.sh` run only on plain Bazzite before the first switch, which 43's walk reaches with older tools: for them the proof is the unit tests that run their steps and the last two tests above (each of their start lines run from the marker folder, and the scan). The laptop never runs those four again.

**D19: `check` asks for the program the running release's session starts, not for a terminal** (fact 11; review 1, S2).
- **Why `foot` is there.** The pair came with package 14 (`79a67d2f`), and no brief gives it a reason of its own (searched: briefs 14 to 16 and 22, `docs/design/OS-BASE.md`). Read from the code and the guide: `check` proves on a running AresOS what `stock-session.sh` proves on plain Bazzite, that the daily session is the one this system should have (`docs/INSTALL.md:191`: "daily `ares` UID1001/no wheel and running labwc/foot"). For AresOS that was `labwc` of `ares` (the compositor) and `foot` of `ares`: the terminal the session's autostart started in releases 13 and 27 (`/usr/bin/aresos-terminal`; neither release has `/usr/libexec/aresos-desktop`, read at their source commits `775be05b` and `b216f28f`), and the terminal of the typing proof. `os/tests/guest.sh:6-7` holds the same pair for the image. So `foot` stands for "the session got past the compositor to its own program", not for "a terminal is open".
- **What goes wrong.** Release 28's autostart starts the desktop keeper instead. In the hub no `foot` runs unless he has the Terminal app open, so `check` STOPs with `Read failed: pgrep -u ares -x foot`, from Claude's terminal and at the console alike, on the word the emergency card puts first. No rehearsal shows it: a VM without a Minecraft account sits in SETUP, which shows a `foot`.
- **Decision.** On a running AresOS `check` keeps `labwc` of `ares` and requires the session's own program of that release:
  - where the running system has `/usr/libexec/aresos-desktop` (release 28 and later): a process of `ares` with that name. The keeper and the supervisor both carry it. They live as long as the session, with one exception: after five supervisor failures within ten minutes the keeper shows a terminal with the reason and ends (`os/config/usr/libexec/aresos-desktop:166`, `:2473-2477`);
  - where it has not (releases 13 and 27): `foot`, as today.
  Exactly one of the two is asked, by what the running image holds, never either. The protection stays: a session that never reached its own program still fails.
- **When the keeper has given up, `check` stops, and says so in a line of its own** (review 2, N3). That is a true result, in the state where a bad update is most likely, and `Read failed: pgrep -u ares -x aresos-desktop` would read like a fault of the tools. So this one read accepts "none found" (`pgrep`'s exit 1) and stops with: `The desktop's own program (aresos-desktop) is not running for ares: the session did not start it, or it gave up after repeated failures. This is about the running session, not about the tools; nothing was changed`. The line names no next command, because the routine after a STOP allows none (section 6). The read of `foot` on releases 13 and 27 stays as built. The guide's box says how Claude reads the line.
- **Why by the image's file and not by a field in the release record** (the review's first option): the file is part of the signed image whose digest `check` has just matched against the history, so it says what a record would say, and `stock-session.sh:8` already reads a session file this way. There is no need for a session-program field for a fact the image states itself. D13 now adds a release number for display and changes the history's strict form (`owner.py:163`); its reader must still accept older installed histories (`:175-184`). That separate change does not change D19's choice.
- **Why not "open a terminal first" in the guide** (the review's second option): `check` must not depend on something the hub never shows.
- **Proof.** Unit rows for both kinds of image, each with and without its program, the new line among them; a test that the name `check` asks for is the program labwc's autostart starts (read from `os/config`) and is shorter than 16 characters; in 43's VM run one `at check` on release 28 whose saved record shows the read of `aresos-desktop` passing and no read of `foot` (section 7).
- **How `pgrep -x` finds it** (review 2, N3; the first revision listed this as not known from reading). The kernel names a process started through a `#!` line after the script file, not after the interpreter, and `pgrep -x` compares with that name, of which the kernel keeps 15 characters; `aresos-desktop` has 14. Tried by review 2 and again for this revision, as `ares`: a script of that name with `#!/usr/bin/python3` is found by `pgrep -u ares -x aresos-desktop` and not by `-x python3`. The VM stage still shows it on the image.
- **For the lead:** with tools version 4's code (also R28's version 5), `at check` on release 28 passes only while a `foot` of `ares` runs, also at the console. Until 43's tools are on the laptop, R28's guide and any session there need "open the Terminal app first" before `check` (package 42; lead point 8 is done).

## 2. The words (D5, D6)

`aresos update` is the only word whose inner word differs. The inner `update` is deliberately not reachable through the dispatcher: it is the word that can replace a newer AresOS (fact 2).

| Tools word | `aresos <word>` | Why |
|---|---|---|
| `newest` | as `aresos update` | D1 |
| `update` | not reachable | fact 2; from the console by the full path, as built |
| `forward` | refused, points to `aresos update` | `aresos update` goes forward in every state where `forward` would change anything (D2, row 10); one word (#262) |
| `previous` | yes | the way back after a bad update while the desktop works; no console check (`owner.py:1963-1969`) |
| `rollback` | yes | the way back to plain Bazzite; valid only on a running AresOS (`:1763-1767`), which is where the dispatcher is. After its restart he is on plain Bazzite, without Claude and without `aresos` (fact 7; call 8 answered yes, with its two rules) |
| `keep-stock` | refused | valid only on running plain Bazzite (`:1763-1767`), which has no `aresos` |
| `check` | yes | reads the system and writes only the private records; needs no open terminal (D19) |
| `title`, `records`, `logs` | yes | they read the system and write only the private records |
| `export` | yes | 22d's folder export; from R29 it replaces 22d's `export-routine` line |
| `reboot` | yes | the restart, after his go; refuses a stale title, an attached stick and a layout trial (`:1971-1983`) |
| `layout` | refused | needs the physical recovery login (fact 5) |
| `login` | refused | his registry token at a hidden terminal prompt, typed by him and never through Claude (fact 5) |
| `install` | refused | only a bundle's start block runs it |
| `prepare`, `verify`, `switch` | refused | first-switch words: they run on plain Bazzite before any AresOS (`before_switch`, `:1574-1586`) |

**A refused word** opens no window and runs nothing: one line on stderr, exit status 2. Three shapes (D20):
- `aresos forward: use aresos update here, it goes forward by itself when a newer AresOS is installed; nothing ran` (also for `newest`)
- `aresos layout: this works only at the recovery console, typed by you: sudo /var/lib/ares/at layout; nothing ran` (also for `login`)
- `aresos switch: this belongs to installing AresOS from plain Bazzite, at the recovery console; see docs/INSTALL.md; nothing ran` (`install`, `prepare`, `verify`, `switch`, `keep-stock`)

**D20: what a refused word says is decided here and not asked of the owner** (was JUDGMENT-CALL 3; the lead's decision after review 2, 2026-11-16). The three shapes above are the decision.
- **Who reads them.** Claude does. The owner sees one only if he types a refused word himself, so he has nothing to judge them by; a JUDGMENT-CALL is for what he will see or do.
- **What a wrong word costs.** These lines live in the dispatcher, an image file: any release can change them, with no tools change, no new fingerprint and no VM run of the tools. The tools' lines of JUDGMENT-CALL 2 are the opposite case: after 43's VM run a changed word there needs a new run.
- **What every such line must do,** so that a later release that rewords one keeps to it: name the word as it was typed; say where it works, with the full command where there is one, or which `aresos` word does its job; end with `nothing ran`; and never contain `at update` or `at forward` (the test below).
- **He is shown them,** not asked: at "try this", together with the lines of JUDGMENT-CALL 2.

An offered word followed by anything else is refused the same way ("takes no further words"), so no stray argument reaches `sudo` or the tools' records (`owner.py:2893-2894`).

Run as root, or with no desktop session (neither `WAYLAND_DISPLAY` nor `DISPLAY`), an offered word is refused with the full-path command for the console: `sudo /var/lib/ares/at <inner word>`, which for `update` is `sudo /var/lib/ares/at newest`. `aresos update` and the inner `update` differ in exactly the danger state, so **no line the dispatcher can print or exec contains `at update` or `at forward`**; a test holds that over the whole table.

## 3. The password window (D7 to D9)

**D7: 22d's mechanism, unchanged.** `SUDO_ASKPASS=<helper> SSH_ASKPASS_PROMPT= /usr/bin/sudo -k -A -p '<label>' /usr/bin/bash -c '/var/lib/ares/at <inner word>'` (`os/owner-tools/bootstrap.py:106-116`). The root command keeps 22d's form (`export-routine`, `bootstrap.py:128-130`), the one rehearsed behind this window. A direct `/var/lib/ares/at …` works as well: the guide's `sudo -k; sudo /var/lib/ares/at layout proof` is typed from the non-root tty4 login and has passed in the VM since qualification 21 (`docs/INSTALL-PROCEDURES.md:18`). It would only be tidier in `sudo`'s journal, and with D18 the directory no longer matters for either, so the rehearsed form stays. One window per `aresos` word. `update`'s and `forward`'s results already end in the title's lines (`owner.py:1850`, `:1688`), so an update needs no second window for the title; the restart is its own word and its own go.

**D8: the label is a fixed phrase, with no prefix or fingerprint.**
- In 22d the 8 characters name what is about to be installed from Claude's hands, and he compares them once with a public line. An `aresos` word installs nothing from Claude's hands: the command behind the window is fixed in the image, and the tools it runs went in under that earlier compare.
- To show a fingerprint, root would have to publish it where `ares` can read it, and then any program can show it too. It would add a compare to every command and prove nothing.
- So the honest answer to "how does he know the window is AresOS's own": from the window alone he cannot (fact 8). **His rule** for these windows: type the password only when (1) he told Claude to go just now, (2) the title bar says **Enter SSH Credentials**, and (3) the line is the one for what he asked for, as the guide lists them. Otherwise Cancel. The guide repeats 22d's limit in the same words: the window stops accidents and a Claude that acts without asking, not a Claude that was tricked.
- What the image adds over 22d: the root command is a fixed short line, so `sudo`'s journal entry names exactly what each window approved (seen in `STEP-0.md`).

**Proposed after his answer, awaiting his OK** (JUDGMENT-CALL 1). These labels are image-file strings, not 22d's generated bundle lines. They get their own rule: `[A-Za-z0-9 ,]+`, letters, digits, spaces and commas only. No colon is needed; never `%`, quotes, `<` or `&`, and no trailing `: `. Each must match none of the 16 remembered-prompt patterns and stay under 70 characters. Parentheses are not allowed, so no release number goes into the window. The reasons for excluding those characters are 22d's (`bootstrap.py:91-103`); its generated labels keep their rule and stay unchanged, including the window for new tools. The patterns are in `os/tests/test_owner_bootstrap.py:19-39`, with their live check at `:220-242`; each needs a quote or a trailing `: `.

| Word | Line in the window |
|---|---|
| `update` | `Update to the newest version` |
| `previous` | `Go back to the previous version at the next restart` |
| `rollback` | `Go back to plain Bazzite at the next restart` |
| `check` | `Check the system` |
| `title` | `Show what starts next` |
| `records` | `Read disk records` |
| `logs` | `Save the log of the last start` |
| `export` | `Export records` |
| `reboot` | `Restart` |

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

**Step 0's try on the laptop** (call 6 answered yes, at a time he chooses; it shows D9 and D11 before anything is built). The helper is a copy in his home with 60 in place of 600; the command behind the window is `/usr/bin/true`:
1. `/usr/bin/env -i` with exactly D11's values, then `/usr/bin/sudo -k -A -p 'Test the password window' /usr/bin/true`. He types his password. Expected: the window of 22d's step 0 (the title bar, the line inside, no keyring question), exit 0, `sudo -n true` refused afterwards, `COMMAND=/usr/sbin/true` in `sudo`'s journal.
2. The same line once more; he leaves the window alone. Expected: it closes after one minute, `sudo: no password was provided`, exit 1, nothing ran.
3. Only if the first window does not open or looks different: the same with the caller's whole environment and the fixed values set, to learn which variable is missing (LEAD 5).
4. Afterwards Claude deletes the helper copy from his home; nothing else was written (the lead, fix check N3).

**D12: Control.**
- Control's wrapper (`18c:control/packaging/aresos`, three lines) is installed unchanged as `/usr/libexec/aresos-control/cli`: one changed entry in the install map (`18c:os/build.sh:92`) and its pin (`18c:os/tests/test_control_image.py:25`). The file is then inside the folder the launcher already requires to be root-owned and not writable (`18c:control/launch.py:16-20`, `:31-35`) and stays recorded in `control.json`.
- A first word that is not one of the 18, no word at all, and `--help` are handed on by exec with the arguments, the environment, the directory and the terminal exactly as given, as `ares` and as root alike: Control's owner commands are typed as `sudo aresos admin …`, and `aresos admin mail account add` reads a password from the terminal (`18c:control/aresos_control/cli.py`). The dispatcher knows none of Control's words, so Control can add apps without an OS change, and an unknown word gets Control's own error.
- If the image has no Control, the same cases print the nine offered words and exit 2.
- **Who calls `/usr/bin/aresos` on Control's side** (review 1, S7). The line numbers are those of `dada7a9b`; the branch moves (two of them moved between the two revisions: review 2, N4), so step 0's note to `linux-tools` names each place by what it does, as each point below begins:
  - the image build's self-check runs `aresos --help` (`18c:os/build.sh:270`). The order is already right: the Containerfile copies `os/config` first and runs `build.sh control` after it (`18c:os/Containerfile:32`), so the dispatcher is in place. The map entry must move in the same commit as the dispatcher arrives, or the map writes Control's wrapper over it.
  - the image check that compares `aresos --help` as root and as `ares` (`18c:os/ci/image-checks.sh:863-865`); it passes unchanged and proves the hand-over.
  - the two image-side drivers that call `/usr/bin/aresos` (the `cli` helper, `18c:os/ci/control/actions.py:100`, and the mail onboarding flow, `18c:control/ci/image/mail_flows.py:56`) run in the image and keep working through the hand-over; the second needs the terminal passed through.
  - Control's integration test that runs `aresos testapp list` as the owner (`18c:control/tests/test_integration.py:374`) runs in a tree that holds the install map alone (`build.sh control-tree`), which has no dispatcher. It calls `/usr/libexec/aresos-control/cli` from then on; that change is `linux-tools`'s.
- `newest` joins Control's `RESERVED` (`18c:control/tests/test_reserved_words.py:13-14`), a one-line change for `linux-tools`. A new OS-side test reads three sets and requires them equal: the tools' `known` (`owner.py:2890-2891`), Control's `RESERVED`, and the dispatcher's offered plus refused words. So a new tools word fails a test until all three know it.
- Control drops its top-level `log` shortcut and keeps `aresos control log`, so `aresos logs` (the tools' word) is the only word of that shape (agreed with `linux-tools` on 2026-11-13, board #199, and confirmed 2026-11-15). That change is on Control's side and lands with this package.

**Tests** (`os/tests/test_aresos_command.py`, no root, no fakes of `sudo`):
- for each offered word, the exact argv and environment; `update` maps to `newest`;
- no string the dispatcher can print or exec contains `at update` or `at forward` (every row, every refusal, the root and no-session lines);
- the three word sets; the labels against D8's own character rule and 22d's pattern list (imported, not copied), their length, and that they differ;
- every refusal: its line, status 2 and no exec; extra words; root; no desktop session;
- hand-over: argv and environment unchanged for other words, none and `--help`, as `ares` and as root; the usage when Control's file is missing;
- one test runs `main()` in a child process on a pseudo-terminal, with the hand-over target pointed at a stand-in: the stand-in sees a terminal on stdin and the arguments unchanged;
- `main()` execs and the module imports no `subprocess`; the helper's two lines are pinned;
- the guide's table of words and window lines equals `TABLE` (lands with the guide, step 4).

**The bridge on release 28** (lead decision 6). Yes: 43's bundle carries three more generated routine lines, for `newest`, `reboot` and `check`. They use 22d's generator and window mechanism, with its tools fingerprint and its label rule unchanged, not D8's image labels. Each runs just its one installed inner word; the `newest` line is the bridge's update command. They need neither the dispatcher nor D9's image helper. The guide uses them until R29 is on the laptop, so the update from R28 to R29 can run from Claude's terminal. They are the last separable build step (5a), with their own unit checks, guide and fingerprint pins, review, and window stage in 43's VM run (stage 6). The existing window for installing new tools stays unchanged.

**D16: in the image.**
- Two new `os/config` files (the dispatcher, the helper), both committed executable, and Control's moved wrapper. No new package: `ksshaskpass`, `timeout` and Python are in the image already.
- `os/ci/image-checks.sh`: owner, mode and no link for both files; a refused word's line and status as `ares`; an offered word without a desktop session refuses without calling `sudo`; the helper and `timeout` exist; and `ksshaskpass`'s package version equals the one whose patterns were read (6.7.5), so a new version fails the build until someone reads its patterns again (asked for in `22d:reviews/22d-tools-without-stick/REVIEW-1.md:130`).
- These checks run only where an image is built: `os/ci/check-image.sh:13` is their one caller, in a check build or a release build. The checks-only job runs the unit tests alone (`.github/workflows/os-image.yml:93`, `:207`). So step 3 ends with a check build (section 7).
- The release diff for R29 needs no new rule if step 3 gets it right: both `os/config` files are explained by `config_rule` (bytes equal the source, 0755, root; `os/ci/release_diff.py:212-229`), and `/usr/bin/aresos` leaves `control.json` while `cli` enters it. Step 3 adds a test that feeds these three paths to the diff's rules, so R29's release package does not meet an unexplained file.

## 5. What `aresos update` says (D13)

Every line below is the tools'. The five lines in JUDGMENT-CALL 2 are **proposed after his answer, awaiting his OK**; the other rows follow the same plain style and are settled with them before step 6. `<T>`, `<N>`, `<other>` and `<target>` stand for releases' own numbers, such as 27 and 28, not tools versions. Thus row 7 for release 28 says `Update: installing the latest version, AresOS 28. Restart to finish`. `<newest>` stands for `sudo /var/lib/ares/at newest`, spelled by `typed()`. The inner words' existing lines still follow unchanged, including their references and the title's names (`owner.py:752-753`). These added lines do not change D4's timing or D21's rule.

**Release numbers are new step 1 work.** Today `role()` expressly uses roles instead of release numbers (`owner.py:740-753`), and each history entry has only `reference`, `identity` and `daily_wheel` (`:149-171`). The tools must know the number they print:
- each entry in `os/owner-tools/history.json` carries the release's own integer `number`; each release record carries the same number, including the target `os/manifest/release.json` copied to the bundle as `release.json` (`os/owner-tools/bundle.py:11-13`). The target's number must equal the last history entry's number, as its reference and signature identity already must;
- the numbers belong to exact release references. The existing records for 13 and 27 identify their references and tags (`os/manifest/releases/13.json:2-3`, `os/manifest/releases/27.json:2-3`); step 1 records those numbers explicitly and does the same for R28's published record. A tools version is a separate number. Do not guess a release number from a tools version, an installed label or a digest;
- the history reader and tools-upgrade comparison must accept the older installed histories without numbers (`installed_lineage`, `owner.py:175-189`). Match those entries to the new numbered history by exact reference, preserving the reference, identity, daily-account rule and append-only check. Never rewrite an installed older bundle. New entries must carry valid numbers; an omitted or conflicting number in the new bundle is refused before any change;
- for plain Bazzite print `plain Bazzite`, with no AresOS number. If a deployment has no numbered history entry, print `Unrecognised system <12 digest characters> (version unknown)`, never an invented `AresOS <n>`. This is a naming fallback, not permission to accept a deployment outside the reviewed history: the survey still stops in row 0;
- unit rows cover the numbered records, their agreement, older installed histories and both naming fallbacks. The metadata, readers, fixtures, payload and pins land together in step 1. D19 still reads the image's session file; the new number field does not decide which program `check` requires.

| Row of D2 | Lines, in the order they appear |
|---|---|
| 2, not applied | `Update to <reference> was not applied: the deployments are as before it, and nothing is waiting` (the survey's own line, at once); `The last update did not finish, so nothing changed. See Help before trying again` |
| 3, record | `Update: AresOS <T> is already downloaded and ready. Saving the record of the interrupted update. Restart to finish`; `This run downloads nothing`; for every other installed AresOS `AresOS <other> will be removed when the update finishes at shutdown`, and where that one is newer than the running AresOS also `AresOS <T> will start with this system's settings (Wi-Fi, passwords, layout), not AresOS <other>'s` (the facts of the inner word's two sentences, `:1845-1849`); then the inner word's lines |
| 4, continue | `Update: continuing the interrupted update to AresOS <T>. Restart to finish`; then the inner word's lines |
| 5 | the STOP of section 1 |
| 6, an update waits | `The update to AresOS <T> is ready. Restart to finish` |
| 6, a forward waits | `The switch to AresOS <N> is ready. Restart to finish` |
| 6, a return waits | After `previous`: `The return to the previous version, AresOS <target>, is ready. This command changes nothing before the restart. Restart to finish`. After `rollback`: `The return to plain Bazzite is ready. This command changes nothing before the restart. Restart to finish`. Both then say `After the restart, <newest> switches back to the latest installed version, AresOS <N>` (`keep-stock` never waits, D2) |
| 7, install | `Update: installing the latest version, AresOS <T>. Restart to finish`; `This downloads AresOS <T>`; then the inner word's lines |
| 8, nothing to update | `AresOS is up to date (AresOS <N>)`; `AresOS <N> is running and will start next. It is the latest version these tools know. Nothing changed`; `Owner tools version <tools version>: <8 characters>`; `A newer version comes with newer owner tools after the maintainer announces it. docs/OWNER-TOOLS.md on GitHub lists the current tools` |
| 9, already | `AresOS <N> will start next. Nothing changed`; `It is not running yet. Restart to finish` |
| 10, an older AresOS runs | `Update: switching to the latest installed version, AresOS <N> (already downloaded). Restart to finish`; `This downloads nothing and removes nothing` |
| 10, plain Bazzite runs | `Update: switching from plain Bazzite to the latest installed version, AresOS <N> (already downloaded). Restart to finish`; `This downloads nothing and removes nothing` |
| 10, N runs | `Update: AresOS <N> is the latest installed version and is running. Making it start next again instead of <next system>. No restart is needed for this change`; `This downloads nothing and removes nothing` (`<next system>` is the numbered AresOS or plain Bazzite that starts next before the change) |

After rows 9 and 10, when T is not installed, one more line, the last of the result (in row 10 behind the title's lines). It has two endings, by whether a restart waits (review 2, S2):
- row 9 and row 10 in its first two wordings (another system runs, and N starts at the next restart): `These tools also carry a newer version, AresOS <T>. After the restart, <newest> installs it`;
- row 10 in its third wording (N runs and now starts next again; the title says "no restart is waiting", `:1507`): `These tools also carry a newer version, AresOS <T>. No restart is needed first. The next <newest> installs it`.

Both inform; the guide does not tell him to follow either without the release's announcement (fact 9).

**Row 2's second line makes no forecast** (review 2, S2). As first written it ended "`<newest>` then repeats it". That is true where N runs and starts next. It is not true where the failed update was begun on an older AresOS with the inner `update` (#263): after the restart the older AresOS runs and starts next, the newer one is still installed, and the next run is row 10, which goes forward. The proposed line says only that nothing changed and Help comes before another try. D21 still holds: this pause lasts only for the run that finds the failed update; it is no durable hold.

**"AresOS is up to date" and "newer tools would bring a newer version" are one state to the tools** (row 8): N runs and starts next, and T is N. The tools work offline and know no release after T. So row 8 prints the tools' own version line in the form of line 1 of `docs/OWNER-TOOLS.md` (currently `Owner tools version 4: dcbc375f`), and Claude compares it with that file on GitHub's main:
- equal: there is nothing newer; done;
- different: main carries other tools. That is not an announcement and not a go. Claude tells him, and waits for the maintainer's board note with the announced commit and for his go, as 22d's box says (`docs/INSTALL.md:224`: "Claude installs only that commit, never the newest one on GitHub by itself").

**The order after an announcement of a new release:** the new tools first (22d's route: his 8-character compare, one window), then `aresos update`, which installs their release. So the "AresOS is up to date" window is not spent just to learn the version. Row 8 still costs one window, because only root can read the tools; the guide therefore has Claude run `aresos update` after an announcement or after `previous`, not as a daily habit.

## 6. The guides (D14)

- **`docs/INSTALL.md`, "Update AresOS to a new release":** one new box after 22d's routine box (`docs/INSTALL.md:228`), "From Claude's terminal, on AresOS 29 or later":
  - the nine words with their window lines (the table of section 3, held equal to the dispatcher by a test);
  - his three-condition rule and the limit sentence;
  - that the window closes by itself after 10 minutes;
  - what `aresos update` prints in each row of section 5, with a pointer to the console box whose lines then follow ("Stage the new release", `:325`, or "Forward again", `:381`);
  - **one rule for reading the tools' messages:** a line that names `sudo /var/lib/ares/at <word>` means `aresos <word>` from Claude's terminal; for `newest`, `update` and `forward` it always means `aresos update`; a word the table refuses (`login`, `layout`) stays at the console, typed by him;
  - the order after an announcement (tools first, then `aresos update`), and that a different line in `OWNER-TOOLS.md` is not a go (section 5);
  - after an update that did not finish (D21; review 2, S1): `aresos check` first, as the card says. **was not applied** shows once, from whichever owner word runs first, and that is usually this check. From then on `aresos update` repeats the update in that very run: Claude runs it only when Help has decided the repeat, never to see what it says. Only if `aresos update` happens to be the first word after the failed update does it change nothing: it then prints `was not applied` and `The last update did not finish, so nothing changed. See Help before trying again`, and the same rule holds from there;
  - `aresos update` again before the restart says what is ready and `Restart to finish`; that is a PASS, not a problem;
  - **after an update that waits for a restart, Claude asks "Restart now?" and runs `aresos reboot` only on his yes** (call 5). The update and restart stay two steps with two password windows. This is Claude's behaviour in the guide, not a change to either tool;
  - before `aresos reboot` after a run that changed nothing (`AresOS is up to date`, row 9's `will start next`, row 6's `is ready`): `aresos title` first if `reboot` says the title is stale. Those runs save no title (`owner.py:1977-1978`);
  - **`aresos rollback` is allowed with call 8's two rules.** "Roll back the update" means `aresos previous`, the previous AresOS version, unless he says plain Bazzite. Before `aresos rollback`, Claude says in one sentence where he lands and how he gets back, then waits for his go: after its restart he is on plain Bazzite, without Claude or `aresos`; the way back is `sudo /var/lib/ares/at forward`, typed by him at the console, then a restart;
  - `Registry login missing, expired or unreachable`: check the network first; a new login is typed by him at the console (`login` is refused here);
  - `Another owner command is running`: like Cancel, nothing ran. Let the first one finish and run the word again; no export routine;
  - `aresos check` stopping with `The desktop's own program (aresos-desktop) is not running for ares …` (D19): the desktop gave up or never started. That is a fact about the session, not a fault of the tools, and the tools still work. The routine is the same as after any STOP (the last point of this list); on the card it is "any other result", so Help decides, and `aresos title` shows what runs and what starts next when Help asks for it;
  - that Claude posts the title's lines to the board after every word that changes what starts next (22d's decision 8);
  - after any other STOP: every STOP line word for word, his go, then `aresos export`, nothing else.
- 22d's box loses "every other owner command stays at the console … until a later release brings it here" in favour of "from AresOS 29 the next box".
- On R28, before that next box applies, the bridge's three generated lines (section 4) run the installed `newest`, `reboot` and `check`. The same announcement, Help and "Restart now?" rules apply; Claude runs the generated reboot line only on his yes. This bridge is part of step 5a, with the generated labels shown to him separately from section 3's image labels.
- **The console boxes do not change**, rule for rule. They are the way that always works and the only way on plain Bazzite or when the desktop is down. Before R29 the generated bridge supplies only its three words; the other commands keep their console route. The boxes keep `update` and `forward`; `sudo /var/lib/ares/at newest` is named once, as what `aresos update` runs and as usable there. (An owner command in a guide is written in full: `test_owner_equality`'s inline-command rule refuses a bare tools word in code type once `commands.json` knows it.)
- **`docs/EMERGENCY.md`:**
  - "Failed or bad update" (`:18`) gains two sentences: if the desktop works, Claude runs `aresos check` and then, only as that card already says, `aresos previous`; and once **was not applied** has shown, `aresos update` repeats the update at once, so it runs only when Help has decided the repeat (D21). The card's own sentences stay: "**was not applied** shows only once" already says the first half.
  - "A routine tools command stopped" (`:64`) also covers `aresos` words, with `aresos export`.
  - One line near the top: `aresos` exists only on AresOS 29 and later; everywhere else use the full path at the console.
  - The card stays one page.
- `docs/INSTALL.md:191` describes `check`'s proof as "running labwc/foot"; with D19 it names the session's own program.
- `docs/INSTALL-STATUS.md`: a row for the `aresos` route, open until R29's rehearsal; after 43's VM run a row for its tools (section 8). `docs/OWNER-TOOLS.md`: the new fingerprint, same form. `os/owner-tools/commands.json`: one entry, `newest`. `os/README.md`: one paragraph.

## 7. Proof and budget (D15)

**Unit tests.** Section 4's for the dispatcher, D18's and D19's for the two repairs. For `newest`, one row per row of D2 and per wording of section 5, each giving the first line, the chosen word, what changed and how it ends:
- rows 0 and 1;
- row 2 for a staging journal (it stops there, with its second line) and for a reorder's journal (its line first, then the table goes on); row 2 on an older AresOS (the #263 case: the same second line, and the run after it is row 10, a forward; S2);
- **`check`, then `newest`,** after a staging that was not applied: `check` shows the line and closes the journal, and `newest` is row 7, which announces the install and stages (S1; D21);
- row 3 on N and on an older AresOS (the removal line and the settings line name the newer one); rows 4 and 5;
- row 6 after `update`, `previous`, `rollback`, and a `forward` from another system, without a restart: a PASS, no inner word, no journal change, nothing announced;
- after `keep-stock` in the same boot: row 10 in its second wording, and the inner `forward` runs (S4);
- rows 7 and 8; row 9 with an older AresOS and with plain Bazzite running; row 10 in its three wordings;
- the numbered history and release records, older installed histories without numbers, and the naming fallbacks of section 5; row 8's tools version line has exactly `docs/OWNER-TOOLS.md`'s first-line form;
- the extra line after rows 9 and 10 in its two endings: "After the restart" in row 9 and in row 10's first two wordings, "No restart is needed first" in the third; and after that third one the next run, which is row 7 at once (S2);
- every read-only refusal of the chosen word (no login, no network, a layout trial, a busy deployment tool, a staged row without a journal) with **no announcement before it**;
- what may follow an announcement (D4; N1): a signature that does not verify; a deployment tool that became busy during verification; a list that changed during verification, with `:1810`'s text. Each shows the announcement first and stages nothing;
- the guard (D3; N2): after the first `may_stage`, with its text, by `update()` called with D3's argument in the danger state; the guard's method called directly, for both answers; two calls of it in a staging run through `newest` and none through the inner `update`;
- `:1323-1324` naming `typed('newest')` for `newest` and `typed('update')` for every other word;
- the survey's lines printed once, before the first line, on the PASS path and on the STOP path; `chosen` and `said` in the PASS record and the STOP record; that older tools refuse `newest`.

**The model:** section 1.

**One check build, at the end of step 3** (`check_build=build` on the branch: a throwaway image, never published, no owner OK needed). It is the first run of step 3's image checks, and it boots the image once in a VM. If 22d's window driver (`os/ci/tools_local.py`) can be used in that VM pass without a harness of its own, the pass drives one window with the made-up `ares` password the image checks already use: the helper's argument equals the label, Cancel runs nothing, `sudo -n true` is refused afterwards. If it cannot, the builder says so in `PROGRESS.md`, and D9 and D11 rest on step 0's try until R29's rehearsal.

**A VM run of 43's own, before merge, for the tools.** Why its own: the tools change is what can replace a system, the lead asked for a rehearsal (`STATE.md:20`), and the fingerprint must not reach the laptop unrehearsed. Stages 1 to 5 use the console: R28 has no dispatcher (fact 7). Stage 6 walks the generated bridge lines in the window. The run reuses release 28's rehearsal mode (`briefs/42-release-28.md`, B) with 43's bundle:

| Stage | What | Proves |
|---|---|---|
| 1 | On R27 (runs, starts next): `at newest` instead of `at update`, typed from a folder that holds a marker-writing `json.py` and `subprocess.py` | It announces the install and stages R28; no marker was written (D18, `update.sh`) |
| 1b | `at newest` again, before the restart | `PASS newest`, `The update to AresOS 28 is ready. Restart to finish`; nothing announced, nothing changed (row 6; review 1, B1) |
| 2 | On R28 after the restart: `at newest` | `AresOS is up to date (AresOS 28)`, the tools' version line, no change |
| 2b | On R28: `at check`, with no `foot` of `ares` running if the harness can end it | `PASS check`; its saved record shows the read of `aresos-desktop` passing and no read of `foot` (D19) |
| 3 | `at previous`, typed from the marker folder; `at newest` before the restart; restart; on R27: `at newest`; restart; `at check` | No marker (D18, `start-next.sh`); `The return to the previous version, AresOS 27, is ready …`; then it announces the switch to AresOS 28; nothing staged; "Forward to … confirmed" |
| 4 | `at previous`, restart: R27 runs and starts next, R28 is installed. Then a harness-built next bundle whose release is a made-up one that is not installed (installed as in 22d's "stick with a next version" stage). Then `at newest`, stopped by 22c's cut watcher (`os/ci/owner_vm.py:1812`, `:2092`; here for the word `newest`) after its reorder is on disk and before its record, and one hard reset | The danger state, cut: the announcement says forward and is on the screen when the tools are stopped; the journal holds a `forward` intent for R28; no login asked, no network, nothing staged, R28 still in the list |
| 5 | After the reset R28 starts: `at check`. Then `at previous`, restart, and on R27 `at newest` to its end; then `at newest` once more | The cut resolves as a cut `forward` does: `The interrupted forward to … had made its change; it is recorded now`. Then the danger state whole: `PASS newest`, forward, the extra line with "After the restart", nothing staged, R28 still in the list. The second run says `The switch to AresOS 28 is ready. Restart to finish` |
| 6 | A separate window stage: restore a clean R27 checkpoint from before stage 1, with the real 43 bundle installed, not stage 4's made-up next bundle. Run its three generated routine lines from Claude's terminal: `newest` to install R28, `reboot`, then `check` on R28 | Each window uses 22d's generated label with the bundle's 8 characters; Cancel runs nothing; accepted passwords give the one intended word, no keyring, and `sudo -n true` refuses afterwards. The update waits for his separate restart approval; it boots R28, and the generated check passes. This proves the bridge without a dispatcher or image helper |

**Why stage 4 is the cut one** (review 2, N5). As first written, stage 5 typed `at newest` once more where stage 4 ended. There the forward waits for the restart (row 6), so no intent is written that a reset could cut. Now the first run in the danger state is the cut one, and the whole one follows after one `previous` and one restart; the other order costs one restart more. Three things a builder should know:
- 22c's watcher stops the tools once the reorder is on disk (`os/ci/owner_vm.py:1808-1811`), so the next word finds the change made and records it. It does not show `was not applied`, as the review expected for a cut forward.
- Row 2's reorder branch (a forward cut before its reorder) therefore has no VM stage: 22c's harness has no watcher for a cut between the intent and the reorder. It stays with the unit rows and with the model, whose cut phases cover it.
- On R28 after the reset the walk types `check`, not `newest`: with the made-up release in the tools, `newest` there is row 7 and would try to install it.

Every stage keeps package 11's audits. Row 2 gets no stage: an update that does not finish at shutdown is in the model (a power-off with a staged release) and in the unit rows, and `newest` adds no change of its own there.

**The dispatcher rides R29's release rehearsal,** because only that image has it and only there do the real image, the real tools and a real update meet. Stages for R29's release brief, on R29 after the update:

1. `aresos --help` equals Control's help; `aresos layout` refuses with no window.
2. `aresos check`: the helper's argument equals the label, a screenshot, no keyring process; Cancel runs nothing; then the password and `PASS check`; `sudo -n true` is refused afterwards (22d's driver, `os/ci/tools_local.py:488`).
3. `aresos update`: "AresOS is up to date".
4. A window left unanswered closes after 10 minutes; `sudo: no password was provided`; nothing ran.
5. `aresos previous`, started from a folder that holds the two marker files: no marker. `aresos update` before the restart says the return is ready and `Restart to finish`. `aresos reboot`; on R28 the bridge's generated `newest` line goes forward; its generated `reboot` line restarts after his yes; back on R29 `aresos check` shows the confirmation.

**Staging through the dispatcher** first happens in R30's rehearsal (R29 to R30 by `aresos update`), before any laptop session does it. Until then its staging branch is proven at the console (stage 1) and its mapping by the unit tests.

**Budget for 43's ledger entry:** 15 checks-only runs, 2 check builds, 4 VM dispatches, 2400 minutes. 22c and 22d both began at 1200 and were raised to 2400, because one VM dispatch reserves 345 minutes (`os/ci/rehearsal-packages.json`); the caps stop runaway loops, the runners cost nothing for this public repository.

## 8. Build steps

One fresh builder each, gpt-6.1-sol at xhigh against a tight brief, about 250k tokens; each commits, pushes and keeps `reviews/43-aresos-command/PROGRESS.md`. Reviews on gpt-6-astra. **Step 1 is Codex gpt-6.1-sol xhigh, with an Astra high review** (lead decision 10, 2026-11-17). The Claude week is past its release line and Fable is near its cap. Step 1 goes to Fable only if it resists two rounds and Fable is free. The model step keeps the same two-round fallback, subject to Fable being free.

| Step | What | Needs |
|---|---|---|
| 0 | The lead tells `linux-tools` all of D12's list and lead decision 7; the approved laptop try at the owner's chosen time (section 4), showing D9 and settling D11's variable list | this note READY |
| 1 | Tools: D18 and D19 with their tests; `newest` with D2's table, D3's guard, D4's function, the lines, `chosen` and `said`; D13's numbered history and release records, readers and compatibility tests. The payload and every pin of the fingerprint; the `commands.json` entry with its guide sentence; the waiting rows. The brief carries review 3's nits N1 and N4 to N7; this revision leaves them | main merged into the branch (it stands on `4d23b408`, before 22d); tools version 6 or the next free number at that merge; **no row of `docs/INSTALL-STATUS.md` says "VM REHEARSAL PASSED; NOT ON THE LAPTOP"** (below) |
| 2 | The model: the ledger's `choose`, the driver, I1 to I4; the hosted full model; its time before and after | step 1 |
| 3 | The dispatcher with D20's lines, the helper, their tests, the image checks, Control's moved wrapper with its pin, the three-set test, the diff test; then one check build | 18c Part A on main, or the lead's word that Control does not ride. Not held by the status rows (no tool, release script or guide changes) |
| 4 | The guides and the card (D21's sentences and D19's among them), the equality tests, the owner's wording; the payload and its pins once more if a tools line changed | steps 1 to 3 and the owner's wording; no status row says the phrase |
| 5 | Review of steps 1 to 4 | |
| 5a | Last separable build step: the three generated bridge lines (`newest`, `reboot`, `check`), their tests, guide and pins; review this addition before step 6 | steps 1 to 5; the same status-row gate as steps 1 and 4 |
| 6 | The harness variant, its ledger entry, the workflow's entries, 43's host-walk receipt and local walk, hosted checks with the full model on the same head, the VM run including the bridge's own window stage, the record step | step 5a; R28 published and its rehearsal mode on main; calls 1 and 2 and the new `check` line settled |
| 7 | Hand-over: the five rehearsal stages and D16's diff note into R29's release brief | |

**The binding rules the steps meet** (review 1, S4; 22d's steps are the pattern, `reviews/22d-tools-without-stick/REPORT.md`):

1. **The payload equals its sources.** `bundle.check` fails as soon as `owner.py`, `at` or a release script differs from `os/owner-tools/payload/` (`os/owner-tools/bundle.py:50-58`, `os/tests/test_owner_equality.py:48`). So step 1 cannot leave "payload and pins" for later. In the commit that changes a payload source it runs `python3 os/owner-tools/bundle.py --refresh` and moves every pin of the fingerprint:
   - `os/owner-tools/history.json`: tools version **6 or the next free number at the merge of main** (an install refuses the same version, `owner.py:2651-2652`). R28's tools take version 5: version 4's code with R28's reference (package 42's lead decision, 2026-11-17). A new fingerprint does not make reusing version 4 valid. If main's version moves before 43 merges, 43's moves above it at the next merge of main;
   - `docs/OWNER-TOOLS.md` (lines 1 and 3), `docs/INSTALL.md` (the blocks and the fingerprint), `docs/EMERGENCY.md` (the export window's 8 characters), `os/owner-tools/commands.json` (the generated lines);
   - 22d's status row keeps its fingerprint as 8 characters once the payload moves (`check_fingerprints` refuses a full fingerprint that is not the payload's; 22c's row shows the form).
   The payload is regenerated, never merged by hand: after every merge of main, refresh and pin again. The pins move once more in step 4 if a tools line changes with the owner's wording, and wherever step 5a's generated lines pin them.
2. **Every changed bound file has its row on the waiting list.** After the last change to a bound file in a commit: `python3 reviews/27-first-update-release/rebind.py pending "<note>"`; `test_checkout_sources` compares the list with what that tool finds (`os/tests/test_checkout_sources.py:188-191`). The tool decides what is bound, not this note. In the active bindings (`os/manifest/ci/22d/source-bindings.json`, 263 paths) are `owner.py`, `at`, the payload, `commands.json`, `history.json`, every release script this package changes except `update.sh`, `docs/INSTALL.md`, `docs/EMERGENCY.md`, the workflow, the budget ledger and several tests; not in them are the model's two files, `docs/INSTALL-PROCEDURES.md`, the image checks and the two new `os/config` files.
3. **While any status row says "VM REHEARSAL PASSED; NOT ON THE LAPTOP", nothing under `os/owner-tools/`, `os/release/` or `docs/` may wait,** and the payload must be the newest rehearsal's tools (`:25-31`, `:107-149`). Two rows say it on main at `937a1868`: 22c's and 22d's.
   - 22d's and 22c's rows move after the owner's version 4 install. That frees the payload once neither says the phrase: the payload rule binds only the newest rehearsal's row, but the waiting rule looks at every row.
   - 22c's row says the phrase for version 3, which never goes on the laptop (board #265); version 4 carries its ways back. The waiting rule looks at every row, so **steps 1 and 4 need 22c's row moved as well**, in the same commit as 22d's or in one of its own; its words are the lead's, and its pin in `os/tests/test_owner_path.py:1769-1772` follows.
   - Steps 1 and 4 check before their first change that `grep -c 'VM REHEARSAL PASSED; NOT ON THE LAPTOP' docs/INSTALL-STATUS.md` prints 0 on the merged base, and stop with a note to the lead if it does not.
   - Steps 2 and 3 are not held: test, harness, workflow and image files may wait while a row stands. If steps 1 and 4 must wait for the rows, step 3 may be built first; the three-set test then lands with step 1.
   - Release 28's row will say the phrase between its VM rehearsal and the laptop's update. **Steps 1 and 4 run only while no row says it. If that window is closed when a step is ready, it waits until R28 is on the laptop** (lead decision 11). Step 5a changes tools-generated lines and guides, so the same gate applies. Step 6 is not a way around the gate. The builder records the wait in `PROGRESS.md` and never weakens the test.
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
- **The one message that changes:** "AresOS is up to date … the latest version these tools know" becomes an answer from the registry.
- **Deliberately not built:** a registry query, a signature check outside the tools, tools inside the image, a sudoers or polkit rule, a service, a timer, a helper with its own window.

## JUDGMENT-CALL (for the owner)

The owner answered all six calls on 2026-11-16. Calls 4, 5, 6 and 8 are settled. Calls 1 and 2 are answered with new lists proposed back to him, **awaiting his OK**. Their numbers stay so the reviews' references still fit.

- Calls 3 and 7 of the earlier list remain the lead's design decisions after review 2: D20 and D21. He is shown both at "try this" and is not asked.
- A changed word is cheap until step 6's VM run. After that run a changed tools line needs a new VM run. Calls 1 and 2 and D19's new `check` line are settled before step 6.

**1. The line in the password window — answered; proposed list awaiting his OK**
- **His answer.** "I don't think it needs to say AresOS at every turn ... usually an OS just says update ... id say "newest version" "previous version" and also number versions like other OS do it. So maybe "newest version (AresOS 1.7)". What's check this system? What's read what starts next and boot menu? I'd also say just "Restart", "read disk records", "save log ..." "export records"."
- **Proposed after his answer, awaiting his OK.** These are section 3's nine lines, in the same order:
  1. `Update to the newest version`
  2. `Go back to the previous version at the next restart`
  3. `Go back to plain Bazzite at the next restart`
  4. `Check the system`
  5. `Show what starts next`
  6. `Read disk records`
  7. `Save the log of the last start`
  8. `Export records`
  9. `Restart`
- **Result.** Drop the prefix. The guide's third condition is "the line is the one for what he asked for, as the guide lists them". These image labels have D8's own character rule; parentheses are not allowed, so release numbers go in the tools' answers, not in the window. 22d's generated label for installing new tools stays unchanged. The window alone still cannot prove it is AresOS's own.

**2. What `aresos update` tells you — answered; proposed list awaiting his OK**
- **His answer.** "Update: Installing latest AresOS version", "Updating to latest AresOS version", "AresOS is up to date"; and "The last two msgs I don't understand."
- **Proposed after his answer, awaiting his OK.** The number is the release's own number (27, 28, ...):
  - row 7, install: `Update: installing the latest version, AresOS 28. Restart to finish`
  - row 10, an older AresOS runs: `Update: switching to the latest installed version, AresOS 28 (already downloaded). Restart to finish`
  - row 8, nothing newer: `AresOS is up to date (AresOS 28)`
  - row 6, an update waits: `The update to AresOS 28 is ready. Restart to finish`
  - row 2, the last update failed: `The last update did not finish, so nothing changed. See Help before trying again`
- **Result.** Section 5 gives the other rows the same plain style. It keeps every fact about what runs, what starts next, downloads, removals, settings and a later install. Row 2 makes no forecast; D4's announcement timing, D13's offline limit and D21's Help rule stay. Row 8 still prints the tools' version line in `docs/OWNER-TOOLS.md`'s form. Step 1 adds the numbered release records needed to print these lines.

**4. The title of the password window — answered**
- **His answer.** Keep "Enter SSH Credentials".
- **Result.** Keep that title and the existing window (D7, D8, fact 8). A window of our own is still outside this package.

**5. The restart is a step of its own — answered**
- **His answer.** "Yes this is the common way. Usually installing an update means a window asking if restart now, we could do that too but no must."
- **Result.** Two steps stay, each with its own password window. After an update that waits for a restart, Claude asks "Restart now?" and runs `aresos reboot` only on his yes. This is the guide's Claude behaviour (section 6), not a tools change or a new restart window. D2's one thing per run and `reboot`'s saved-title check stay.

**6. A short try on the laptop — answered**
- **His answer.** Yes, at a time he chooses.
- **Result.** Step 0's three-minute try is approved, with the temporary helper copy in his home and its removal afterwards (section 4). Two windows say `Test the password window`: he answers the first and leaves the second alone for one minute. The command is `/usr/bin/true`. If the first window does not open or looks different, the approved extra window finds why. The try shows D9's helper and decides D11's variable list.

**8. `aresos rollback` from Claude's terminal — answered**
- **His answer.** Yes, with the two rules (A).
- **Result.** `rollback` stays offered. "Roll back the update" means `aresos previous`, the previous AresOS version, unless he says plain Bazzite. Before `aresos rollback`, Claude says in one sentence where he lands and how he gets back, then waits for his go. After the restart he is on plain Bazzite without Claude or `aresos`; he returns by typing `sudo /var/lib/ares/at forward` himself at the console, then restarting. Section 6 carries both rules.

## The lead's decisions (2026-11-17)

The former open points are recorded here under their original numbers. Only the work still awaiting an answer or a try remains in the short list below.

1. **The inner word's name.** Decision: keep `newest`, including `PASS newest` and the records.
2. **`forward` and `rollback`.** Decision: `forward` stays refused. `rollback` works with call 8's two rules.
3. **D9's helper.** Decision: keep it. Step 0's try shows it.
4. **`bash -c` or a direct root command.** Already answered by review 1 (N2): both work; D7 keeps the rehearsed form.
5. **D11's variable list.** Decision: step 0's try settles it, as section 4 says. If the window fails, try the caller's whole environment with the fixed values set.
6. **Routine lines for R28.** Decision: yes. 43's bundle carries the three generated lines (`newest`, `reboot`, `check`), as a last separable step with its own window stage in the VM run. Sections 4, 6, 7 and step 5a carry it.
7. **With `linux-tools`.** Decision: step 0 tells it the listed changes: `newest` in `RESERVED`; the wrapper's move and header comment; D12's callers; the top-level `log` shortcut; and whether Control's help gains a line naming the nine words.
8. **`check` on R28 before 43's tools.** Done: brief 42 carries "open the Terminal app first" (`briefs/42-release-28.md:142`, read on main). D19's repair still rides in 43.
9. **The model's time.** Decision: the rule stands. If it outgrows the hosted job, split the job, never the exploration.
10. **Who builds step 1.** Decision: Codex gpt-6.1-sol xhigh, with an Astra high review. The Claude week is past its release line and Fable is near its cap. It goes to Fable only if it resists two rounds and Fable is free. Section 8 records it.
11. **Version and status rows.** Decision: R28's tools take version 5 (v4's code with R28's reference; package 42's lead decision, 2026-11-17), so 43 takes version 6 or the next free number at its merge of main. Steps 1 and 4 run only while no status row says the phrase. 22d's and 22c's rows move after the owner's v4 install; R28's row says it between its VM rehearsal and the laptop update. If that window is closed when a step is ready, it waits until R28 is on the laptop. Section 8's binding rules carry both decisions; step 5a meets the same gate.
12. **D18 sooner.** Decision: no. D18 rides with 43.
13. **Decisions after review 2.** Recorded: S1 takes the review's first fix (D21); calls 3 and 7 are design decisions (D20, D21). The six remaining owner calls are now answered above, with calls 1 and 2's revised words still awaiting his OK.
14. **D19's new `check` line.** Decision: it follows the same plain style as call 2's lines and is settled with them before step 6. It is not a separate owner call. Review 3's N7 stays for step 1's brief.

## Open points for the lead

- The owner's OK on the two proposed lists (calls 1 and 2); settle the other tools lines and D19's `check` line with them before step 6.
- The owner's chosen time for step 0's approved try, and its result for D9 and D11.
- Step 0's coordination with `linux-tools`, including the help-line choice in decision 7.

## Changes after review 1

This section is the record of the first revision and stands as it was written; where review 2 changed something again (S1's row, D18's tests, JUDGMENT-CALL 7), the next section says so.

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

## Changes after review 2

Review 2 (`REVIEW-2.md`, a fresh Fable reviewer, 2026-11-16): READY WITH CHANGES, nothing blocking; four should-fix findings and nine nits. Revised the same day by a fresh Claude agent on Fable 5.2 that wrote neither the note nor the reviews. Each finding was checked against the code before anything changed: main at `52d13cb7` (`os/`, the guides and the workflow byte-identical to `937a1868`) and `origin/pkg/18c-image` at `dada7a9b`. All thirteen held, and none is rejected. Three nits are settled differently from the review's wording (N5, N6, N8), each with its reason in its row.

| Finding | Checked | What changed |
|---|---|---|
| **S1** "the first `aresos update` only tells him" holds only if nothing else ran first | Main's `Tools.outcome` as a library, on a made-up list with a staging journal from an earlier boot: the first survey returns nothing, notes the line and archives the journal as `not-applied`; the next, with `retry='update'`, returns nothing and has no note. `check`, `title`, `records` and `reboot` make that survey (`:1989`, `:1532`, `:1568`, `:1976`) | The review's first fix, which the lead chose. Row 2 stays; its new bullet says that it holds for one run and only when `newest` is the word that finds the failed update. **D21** records the decision and why there is no durable hold. Section 6: the guide's sentence and the card's sentence now say that `aresos update` repeats the update at once after **was not applied** has shown, and that Claude runs it only when Help has decided. Section 5: row 2's second line says that the command waits only this once. Unit row: `check`, then `newest`, is row 7. JUDGMENT-CALL 7 is gone |
| **S2** two lines forecast the next run wrongly | The #263 order read from the journal code (`:1313-1341`); `:1507` for "no restart is waiting"; a forward that makes the running N first is `applied` (same check as S4) | Section 5: row 2's second line makes no forecast (the review's first option), with the reason beside it. The extra line after rows 9 and 10 has two endings, by whether a restart waits, and its place is fixed: last in the result. Unit rows for row 2 on an older AresOS, for both endings, and for the run after row 10's third wording |
| **S3** D18's first test cannot fail as written | Tried on Python 3.14.8 from a folder with a planted `json.py` and `subprocess.py`: `bash -seu` in that folder with `python3 -` ran the planted file and with `python3 -I -` did not; `bash -seu` with the directory `/` ran it in neither case | Section 1a, point 4: three layers, one test each, with the other two absent: `at` alone; the directory alone (a real `Step` from the marker folder with a script **without** `-I`; `Host.read`, `Host.mutate`); `-I` alone (`bash -seu` in the marker folder, not through `Step`, once per Python start line of the payload, with `python3 -` as the control that writes the marker). The scan of the payload stays. D18's line in the decisions table says so |
| **S4** row 6 lists keep-stock, which can never wait | `Tools.outcome` on made-up lists in one boot: `applied` after `keep-stock`; `pending` after `previous`, `rollback` and a `forward` from another system. `:1763-1776`, `:1339-1341` | Row 6 and its unit row without keep-stock; section 5 without "change to"; one bullet in D2: after keep-stock in the same boot `newest` is row 10 and goes back to AresOS, as `forward` does, and why that is wanted; a unit row for it; the ledger's `choose` likewise |
| **N1** D4's headline and I4 say more than D4's body | `:1803-1810` read: the signature check, the second `may_stage` and `:1810` come after the announcement | D4 in the decisions table and in section 1 now says what can still stop an announced run (the act itself, or a cut) and lists it. I4 says why the model can stay strict. A unit row for each refusal that may follow an announcement |
| **N2** the second guard cannot fire | By reading: `:1810` compares the whole list, running flags included, so the first guard's answer still holds | D3 says so and keeps the guard as a backstop, with tests that fail without it: the guard's method called directly, and a count of two calls in a staging run through `newest`. The unit row for a list that changed during verification expects `:1810`'s text |
| **N3** D19, three facts | A script named `aresos-desktop` with a `#!` line: found by `pgrep -u ares -x aresos-desktop`, not by `-x python3`. The keeper's give-up read (`os/config/usr/libexec/aresos-desktop:166`, `:2473-2477`). Releases 13 and 27 read at `775be05b` and `b216f28f` | D19: "not known from reading" is replaced by how `pgrep -x` finds the script and the 15-character limit, which the autostart test also holds. The keeper's exception is named. `check` gets a line of its own when the desktop's program is not running, with a guide sentence (section 6) and LEAD 14 |
| **N4** two 18c line numbers moved | Read at `dada7a9b`: `image-checks.sh:863-865`, `test_integration.py:374`; the other nine places hold | D12: the two numbers; each place is now named by what it does, and step 0's note to `linux-tools` uses those names |
| **N5** VM stage 5 cannot start where stage 4 ends | By the table: after stage 4's forward the state is row 6. 22c's cut read in `os/ci/owner_vm.py:1808-1812`, `:2092-2122` | Settled by the review's second option, in another order: stage 4 is the cut run in the danger state, stage 5 resolves it and then walks the danger state whole after one `previous` and one restart. **Not as the review's first option expected:** 22c's watcher stops the tools after the reorder is on disk, so the next word shows `had made its change; it is recorded now`, not `was not applied`. Row 2's reorder branch stays with the unit rows and the model, and the note says why |
| **N6** `main()` changes in four places | `:2933`, `:2938-2939` read | **Settled differently:** `newest` moves each line it has printed from `notes` to `said`, so the two places where `main()` prints notes find nothing to print twice and need no change. Three places stay three. A unit row holds "once" on the PASS path and on the STOP path |
| **N7** row 3 on an older AresOS leaves out the settings line | `:1847-1849` read | Row 3 prints it too, in D2's bullet, in section 5 and in the unit row |
| **N8** I2 has one edge | `:1798-1802` and `:1639` come before the guard | **One sentence and no code,** as the review allows: the edge is named under "Refusals" with why the two lines are harmless there (`forward` never stages; the guide's reading rule), and I2 says it is the model's judgment |
| **N9** completeness: a staged row with no journal | `:1631` read; the inner `update` meets the same line | One sub-bullet under "The table is complete" |
| **JUDGMENT-CALL 3** (the lead, with the review's advice) | | **D20**, in section 2: the three shapes are the decision, with who reads them, what a wrong word costs, and what every such line must do |
| **JUDGMENT-CALL 7** (the lead, with the review's advice) | | **D21**, in section 1, after S1 made its sentence true |
| **JUDGMENT-CALLs 1, 2, 4, 5, 6, 8** | | Rewritten to him: the question, why, the advice, the options. Their numbers stay. Call 2 asks about the words only; call 5 says that "one step" is a new design round |

Found while checking, named by neither review:
- **D18, point 2, named three of the tools' four child starts.** The fourth, `podman login` (`:1730`), now gets `cwd='/'` as well, and one test reads `owner.py`'s syntax tree for all of them, so a fifth start cannot come without it. `at`'s change of directory already covered it; this makes the second layer whole.
- **D19 called `foot` "the one program the session's autostart started in releases 13 and 27".** Release 27's autostart also starts the polkit agent. Reworded to the terminal it starts.
- **The extra line after rows 9 and 10 had no place** in the result. It is the last line.
- **Section 6's sentence for a failed update** now also says "never to see what it says": the old text invited exactly that run.

Left for the builder: how `check` reads "none found" for the desktop's program (`pgrep`'s exit 1 through `Host.read`'s `allowed`); how the directory test changes and restores its own directory; where the guard's method lives. The behaviour is fixed above.

## Changes after the owner's answers (2026-11-17)

Review 3 (`REVIEW-3.md`) was READY. This revision folds in the owner's answers of 2026-11-16 and the lead's decisions of 2026-11-17. It changes this note only. The earlier change sections remain a record of their revisions; this section supersedes them where the owner's answers changed the words or added work.

| Change | Where it landed |
|---|---|
| **Call 1: no repeated OS name in the window** | D8, section 3 and call 1: nine prefix-free labels, proposed after his answer and awaiting his OK. The image labels get their own character rule, under 70 characters, with none of the 16 remembered-prompt patterns. Parentheses and release numbers stay out of these windows. His third condition names the line for what he asked for. The window alone still proves no origin. 22d's generated label for new tools stays unchanged; step 0's test label and section 4's label tests follow D8 |
| **Call 2: plain words and numbered versions** | D13, D2's first-line column, section 5, the guide's quoted results and the VM expectations: the five proposed lines, awaiting his OK, and the other rows in the same style. Row 2 forecasts nothing. Download, removal, settings, running and next-start facts stay, as do D4, D13 and D21. The two later-install endings still distinguish whether a restart waits. Row 8 keeps the tools' version line in `docs/OWNER-TOOLS.md`'s form |
| **New work: numbers the tools can print** | Section 5, section 7's unit rows and step 1: each history and release entry carries its release number; the target agrees with the last history entry. Older installed histories remain readable. Plain Bazzite has no AresOS number; an unrecognised deployment has a digest and `version unknown`, with no wider acceptance. D19's reason is updated to distinguish this new display field from a session-program field |
| **Calls 4, 5, 6 and 8 answered** | The JUDGMENT-CALL section records his answers and results. Keep "Enter SSH Credentials". Keep two update/restart steps; section 6 has Claude ask "Restart now?" and run reboot only on his yes. Step 0's try is approved at his chosen time, including the temporary helper and its removal. `rollback` stays offered with both rules in section 6 |
| **Lead points 1 to 5, 7 to 9, 12 and 13** | The dated decision list records each under its old number. Keep `newest`, refuse `forward`, offer `rollback`, keep D9, and let step 0 settle D11. Step 0 tells `linux-tools` the listed changes. Brief 42 already carries the Terminal-app instruction. The model-time rule stands. D18 rides with 43; D20 and D21 stay decided. The remaining open list is three dependencies |
| **Lead point 6: the R28 bridge** | Sections 4 and 6, step 5a and VM stage 6: yes to three generated lines (`newest`, `reboot`, `check`), as the last separable build step with its own review and window stage. Their labels use 22d's generator unchanged. R29's return walk uses the bridge on R28 |
| **Lead point 10: step 1's builder and reviewer** | Section 8 and the decision list: Codex gpt-6.1-sol xhigh, Astra high review; Fable only after two resistant rounds and if free. The Claude week is past its release line and Fable is near its cap |
| **Lead point 11: tools versions and status rows** | Section 8's table and binding rules: R28 takes tools version 5; 43 takes 6 or the next free number at its merge of main. Steps 1 and 4 run only while no row says the phrase; if R28 closes that window, they wait for its laptop update. Step 5a meets the same gate. Both 22c's and 22d's rows move after the owner's v4 install |
| **Lead point 14 and review 3's remaining nits** | The decision list and step 6's needs: D19's new `check` line follows the same plain style and is settled with call 2 before the VM run. N1 and N4 to N7 go to step 1's brief and are left by this revision |
| **Moved reference** | Section 7's rehearsal decision is now `STATE.md:20` on main; the old `:14` is blank |

References added or changed here were checked against main at `dcbdabe9`, read through `git show` because the branch predates 22d. No tool, test, guide or workflow was changed or run. The nine proposed image labels were checked as data against D8's character and length rules and all 16 patterns from main, including with a final newline. Their list equals call 1's list. Calls 1 and 2 still await the owner's OK; the laptop try and VM stages remain future work.

- **Fix check (Codex gpt-6-astra high, 2026-11-17), one should-fix:** "latest version" named two releases when the tools carry a newer one than the newest installed (R27 runs, R28 installed, tools carry R29). Row 10's first wording and call 2's line now say "the latest **installed** version"; the extra line after rows 9 and 10 says "a newer version, AresOS <T>". Step 1 pins that wording in the N≠T unit case. Applied by the lead.
