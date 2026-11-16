# Review 2 of the design note for package 43, the `aresos` command

Reviewed `reviews/43-aresos-command/DESIGN.md` at `fe9371a7` (draft PR #82): the revision after review 1, `git diff 6a4383ad..fe9371a7`.

Reviewer: a fresh Claude agent on Fable 5.2 that wrote neither the note, its revision nor review 1. Review only: no code, guide or test changed, nothing committed or pushed. This file is the one thing written.

**Scope.** Review 2 checks the fixes and what they touched (`docs/REVIEW.md`). The new text was read as a whole: D18, D19, rows 0 to 10, I4, VM stage 1b, section 8's binding rules and the eight JUDGMENT-CALLs.

**How it was checked.**
- Read `AGENTS.md`, `CLAUDE.md`, `STATE.md` (line 14, package 43's entry), `docs/REVIEW.md`, `REVIEW-1.md`, the revised note and the diff.
- **Main at `52d13cb7`.** Every main line the note cites was read there. `os/`, the guides (`docs/INSTALL*.md`, `docs/EMERGENCY.md`, `docs/OWNER-TOOLS.md`) and the workflow are byte-identical between `937a1868`, where the revision checked them, and `52d13cb7` (`git diff --quiet`). So no cited main line moved, and each cited behaviour holds. The owner tools are also identical from `634e1237` (22d's merge) to `52d13cb7`.
- **The branch's own files** stand on `4d23b408`, before 22d. Its `owner.py` has 2858 lines (main: 2961); `update()` is at 1724 there and at 1778 on main. The note's numbers are main's. They fit the branch only after step 1 merges main, as section 8 says.
- **Control, `origin/pkg/18c-image`.** The local ref is now `dada7a9b`, not the note's `986192c3` (nothing was fetched). Two cited lines moved (nit N4); the behaviour holds.
- **Releases 13 and 27** were read at their source commits (`775be05b`, `b216f28f`) for D19.
- **Three checks ran as `ares`**, in a scratch folder outside the repository, with bytecode off:
  1. Fact 10 again, on Python 3.14.8: `python3 -` from a folder with a planted `json.py` ran it; `python3 -I -` did not; and a step started with the directory `/` and **without** `-I` did not either (finding S3).
  2. A script started through its `#!` line: `pgrep -x <the script's name>` finds it, and `pgrep -x python3` does not (D19).
  3. Main's `owner.py`, copied to the scratch folder and imported as a library: `Tools.outcome` on made-up deployment lists, with the records folder in the scratch folder (findings S1 and S4). No tools entry ran.
- No `sudo`, no owner tool, no rpm-ostree, bootc or ostree command, no `os/tests/test_owner_*` module.

## Verdict

**READY WITH CHANGES.**

Both blocking findings of review 1 are fixed, and the fixes are sound where it matters most:
- **The state table is complete.** I walked every result of the journal code (`owner.py:1287-1341`) against rows 0 to 10: no journal, `retry`, `complete`, `pending`, `applied`, `done`, `elsewhere`, a journal just closed as not applied, and every STOP. Each lands in exactly one row. A staged update and a queued return are row 6. A power cut during staging, or after it and before the shutdown, is row 2. A cut reorder resolves and the table goes on. `newest` stages nothing unless the running AresOS is the newest and starts next.
- **D18 closes B2 for every root step,** not only the first (details under "What was checked and holds").
- **D19 can be read reliably.**

Nothing found is blocking. Four things should be settled in the note before step 1's brief, because each changes a tools line, a test or a unit row that step 1 builds. One of them (S1) also changes what the owner is told in JUDGMENT-CALL 7, so it comes before the calls go to him.

## Review 1's findings

| Finding | Status | Why |
|---|---|---|
| **B1** false "going forward", then a refusal | **Fixed** | Row 6 comes before rows 7 to 10 and is a PASS that says what waits. Row 9 covers "N starts next, another system runs". Row 10 has three wordings. The announcement is printed after `may_change` or `may_stage`, the guard, the stored login and the `cosign` check, so the refusals review 1 named can no longer follow it. I4, the unit rows and VM stages 1b and 3 hold it. Two leftovers: S4 (keep-stock) and N1 (the wording of D4 and I4). |
| **B2** root steps import from the caller's directory | **Fixed** | D18. Checked for every child the tools start. The first test cannot fail as written: S3. |
| **S1** a failed update repeated without a decision | **Partly fixed** | Row 2 holds only when `newest` is the first owner word after the failed update. After `check`, which the card puts first, the next `aresos update` stages again at once. The guide sentences and JUDGMENT-CALL 7 say otherwise: new finding S1. |
| **S2** `check` needs a running `foot` | **Fixed** | D19, decided differently from both of the review's options, with good reasons. Checked against releases 13, 27 and main: N3. |
| **S3** image checks do not run in the hosted checks | **Fixed** | D16 says where they run (`os/ci/check-image.sh:13`, workflow `:93`, `:207`: read, true). Step 3 ends with a check build; step 0's try is written out. |
| **S4** the steps and the binding rules | **Fixed** | Section 8. Its claims were checked on main: `bundle.py --refresh` exists; `rebind.py pending` and `rebind` exist; the active bindings hold 263 paths, with `owner.py`, `at`, the payload and every changed release script except `update.sh` in them, and the model's two files, `INSTALL-PROCEDURES.md` and the image checks not in them; two status rows say the phrase; `unwalked_commands` is empty today; `REHEARSED_TOOLS` and `model_gate` are where the note says. |
| **S5** no text from `aresos update` to the inner `update` | **Fixed** | The root and no-session line names `at newest`; the tools' new lines use `typed('newest')`; the guide's reading rule; I2 by `typed()`. One edge: N8. |
| **S6** case 1 and the guard | **Fixed** | Rows 3 to 5 decide before anything is announced. Row 5 and the guard name no restart and no command. Row 3 prints the removal line. The second guard sits behind `:1810`, where it can no longer fire: N2. |
| **S7** more callers of `/usr/bin/aresos` | **Fixed** | D12 lists the five places; the build order is right (`18c:os/Containerfile:32`); a pseudo-terminal test. Control's wrapper itself wipes the environment and starts `python3 -I -S`, so the hand-over as root is safe from the directory too. Two line numbers moved since: N4. |
| **S8** a different line is not an announcement | **Fixed** | Section 5 is reworded; the order after an announcement is stated. |
| **N1, N2, N3, N5, N6, N7, N9, N10** | **Fixed** | As the note's last table says. N7: `main()` changes in four places, not three (N6 below). |
| **N4** `HOME` | **Fixed**, settled differently | `HOME`, `USER`, `LOGNAME` from the account database; the variant without `HOME` is not tried because it is not built. Accepted. |
| **N8** the model's references | **Fixed** | `steps()` is at `ways_back_ledger.py:306-318`, its loops at `:308` and `:311`; the method table at `test_ways_back_model.py:257-259`; `WORDS` at `:444`. Read on main; right. |

## New findings

### BLOCKING

None.

### SHOULD-FIX

#### S1. "The first `aresos update` only tells him" holds only if nothing else ran first

- **Where in the note:** D2 row 2 and its bullet; section 6 ("`aresos check` first, as the card says; the first `aresos update` after it only says `was not applied`, and a second one repeats the update"); the emergency card's new sentence ("only says so the first time"); JUDGMENT-CALL 7.
- **Where in the code:** `owner.py:1327-1330` (the survey archives the journal and notes the line once). Every word that reads the list makes that survey: `check` (`:1989`), `title` (`:1532`), `records` (`:1568`), `reboot` (`:1976`).
- **What happens.** An update does not finish at shutdown. The card says check first, and the usual step after any restart is `check`. `check` prints `Update to … was not applied` and closes the journal. The next `aresos update` finds no journal. Row 2 does not apply. N runs and starts next, T is not installed: row 7. It announces the install and stages the release again in that run.
- **Checked:** `Tools.outcome` from main, on a made-up list with a staging journal from an earlier boot. The first survey returns nothing, notes the line and archives the journal as `not-applied`. The next survey, with `retry='update'`, returns nothing and has no note.
- **Why it matters.** The guide would tell Claude that this run "only says" something. Claude runs it to see, and it downloads and stages a release that failed once, with no decision by Help ("Never repeat the update without Help", `docs/EMERGENCY.md:27`). No owner word takes a staged update back. And the owner would answer JUDGMENT-CALL 7 from a picture that is true only when `aresos update` happens to be the first word.
- **Fix,** one of two; the lead picks before step 1:
  1. **Recommended: keep row 2 as it is and make the texts true.** Whichever owner word runs first after the failed update prints the line once. If that word is `aresos update`, it changes nothing. After any word has shown `was not applied`, the next `aresos update` repeats the update at once, so Claude runs it only when Help has decided. Reword the two guide sentences, the card sentence and call 7 that way. Add one unit row: `check`, then `newest`, gives row 7. Then the behaviour is pinned and nobody assumes more later.
  2. `newest` also holds once when the newest archived journal is a `not-applied` staging that no `newest` run has shown yet. That is a new durable state the model does not have. Not recommended.

#### S2. Two lines say what the next run does, and it is not always so

- **Where in the note:** section 5, row 2's second line and the extra line after rows 9 and 10.
- **Row 2:** `…; <newest> then repeats it`. True when N runs and starts next. Not true when the failed update was begun on an older AresOS with the inner `update` (#263, at the console) and did not finish: after the restart the older AresOS runs and starts next and the newer one is still installed. Row 2 prints "then repeats it"; the next run is row 10 and goes forward. That run announces itself truthfully and does the safer thing, so the harm is a wrong forecast, not a wrong change.
- **The extra line:** `These tools also carry a newer release; after the restart, <newest> installs it`. After row 10's third wording (N runs, another system starts next) no restart is waiting: the title says "runs and now starts next; no restart is waiting" (`owner.py:1507`), and the next run installs at once.
- **Why it matters.** These are tools lines. After 43's VM run a changed line needs a new VM run, and call 2 asks the owner to approve them.
- **Fix.** Row 2: drop the forecast (`Before repeating it see EMERGENCY, Failed or bad update; <newest> then says what it does before it changes anything`), or choose the ending by where N stands. Extra line: after row 10's third wording say `run <newest> again to install it`. A unit row for each.

#### S3. D18's first test cannot fail as written

- **Where in the note:** section 1a, the fix's point 4, first test: "a real `Step` started from a folder that holds a marker-writing `json.py` … The same script without `-I` writes the marker, so the test can fail."
- **What happens.** With point 2 of the same fix, a real `Step` starts in `/`. A script without `-I` then looks for `json` in `/`, not in the marker folder, and writes no marker. Checked: `bash -seu` started with `cwd='/'` from the planted folder, `python3 -` inside it, `import json, subprocess`: imported the real modules, directory `/`, no marker.
- **Why it matters.** The two layers hide each other. As written the control cannot be built on the fixed `Step`. A builder who may not weaken a test is stuck, or builds a test that stays green when either layer is removed later. This is the test for a root hole.
- **Fix.** One test per layer, each without the other:
  - `-I` alone: the test itself starts `bash -seu` **in the marker folder** (not through `Step`) with a script of the release steps' shape. `python3 -I -`: no marker. `python3 -`: marker. That is the control.
  - the directory alone: a real `Step`, started while the test's directory is the marker folder, with a script **without** `-I` that imports `json` and prints its directory: `/`, no marker. It fails as soon as `cwd='/'` is taken out of `Step`.
  - The `at` test, the `Host.read`/`Host.mutate` test and the scan of the payload stay as they are.
- The VM stages that run from a marker folder prove the two layers together; that is right for the VM.

#### S4. Row 6 lists keep-stock, which can never wait; after keep-stock `newest` goes forward

- **Where in the note:** D2 row 6 ("a `previous`, `rollback`, `keep-stock` or `forward` of this boot … its target does not run yet"); section 5's "change to" wording; section 7's unit row ("row 6 after `update`, `previous`, `rollback`, `keep-stock` and `forward` without a restart: a PASS, no inner word").
- **Where in the code:** `owner.py:1763-1776` (keep-stock is valid only on running plain Bazzite and its target is that Bazzite), `:1339-1341` (a target that runs is `applied`, never `pending`).
- **What happens.** After `keep-stock` the journal state is `applied` (checked with `Tools.outcome`; after `previous` it is `pending`). So row 6 does not apply. Plain Bazzite runs and starts next, N does not: row 10. `at newest` right after `at keep-stock` announces "plain Bazzite runs here and … is installed; going back to it" and undoes the keep-stock in the same boot. That is what `forward` does today and is defensible, but nobody decided it, and the unit row as listed cannot pass.
- **Why it matters.** The ledger's `choose` is written from this table, not from the tools. A builder who follows the unit list either writes a row that fails or bends the code to make it pass.
- **Fix.** Take keep-stock out of row 6 and out of its unit row, and drop the "change to" wording. One sentence in D2: after keep-stock in the same boot `newest` is row 10 and goes back to AresOS, as `forward` does. One unit row for it.

### NIT

- **N1. D4's headline and I4 say more than D4's body.** "An announcement is never followed by a refusal" (the decisions table, I4). But after the install's announcement come the signature check, the second `may_stage` (`owner.py:1809`: a deployment tool that became busy during the minutes of verification, a changed disk record), `:1810` and the second guard. D4's body names two of these as "fails in the act itself". Say in the headline and in I4 what is meant: no refusal by a check that could run before the announcement. Then the builder knows that the unit row "list changed during verification" may show an announcement and then a refusal.
- **N2. The second guard cannot fire.** It sits behind `:1810`, as review 1 asked. If the list equals the first read's, the running system and N are the same as at the first guard. So the unit row "the guard after each `may_stage` … with its text" cannot be built for the second one. Keep the guard as a backstop if `:1810` ever changes, say so, and make the unit row "a list that changed during verification gets `:1810`'s text".
- **N3. D19, three facts.**
  - "Not known from reading" can be read: the kernel names a process started through `#!` after the script, and the local check above shows it. The name must stay under 16 characters for `pgrep -x`; `aresos-desktop` has 14. The test that reads the autostart's program name can hold that too.
  - "The keeper and the supervisor … live as long as the session" has one exception: after five supervisor failures in ten minutes the keeper shows a terminal and ends (`os/config/usr/libexec/aresos-desktop:2465-2479`). `check` then stops with `Read failed: pgrep -u ares -x aresos-desktop`. That is a true result, in the state where a bad update is most likely. Give that read a line of its own that says the desktop's own program is not running, so Claude does not read it as a tools fault.
  - Releases 13 and 27 have no `/usr/libexec/aresos-desktop` and their autostart starts `/usr/bin/aresos-terminal` (read at `775be05b` and `b216f28f`). So the rule asks for `foot` there and for the keeper from 28. Right.
- **N4. Two 18c line numbers moved.** At `dada7a9b`: `os/ci/image-checks.sh:863-865` (was `:821-823`) and `control/tests/test_integration.py:374` (was `:359`). `os/build.sh:92` and `:270`, `os/Containerfile:32`, `os/ci/control/actions.py:100`, `control/ci/image/mail_flows.py:56`, `os/tests/test_control_image.py:25`, `control/tests/test_reserved_words.py:13-14` and `control/launch.py:16-20`, `:31-35` hold. The branch moves; step 0's note to `linux-tools` should name the places by what they do.
- **N5. VM stage 5 cannot start where stage 4 ends.** After stage 4's forward the state is row 6 (same boot) or row 9, so "the same `at newest` once more" writes no intent to cut. Either take the hard reset inside stage 4's own forward (the next `at newest` then shows `was not applied` and goes forward again, which also walks row 2's reorder branch), or say how the harness gets back to row 10.
- **N6. `main()` changes in four places.** The fourth: the survey's lines that `newest` printed at once are not printed again (`owner.py:2933`, `:2938-2939`).
- **N7. Row 3 on an older AresOS** prints the removal line but not the next one of the inner word, "The new release starts with this system's settings …" (`owner.py:1847-1849`). Add it or say why not.
- **N8. I2 has one edge.** If the list changes outside the tools between `newest`'s read and the inner word's read, `FORWARD_FIRST` or `RELEASE_INSTALLED` (both name `at forward`) fire inside `may_stage` and `update()` before the guard does. With the guard's argument set, `update()` could give the guard's text there. Rare; one sentence is enough.
- **N9. "The table is complete"** should name one more state: a staged row with no journal. It falls into row 10 by the letter and is refused by `may_change` before anything is announced (`owner.py:1631`). The unit list has it; the completeness sentence does not.

## The JUDGMENT-CALLs

The test: can he judge it from what he will see or do? If not, the design decides and reports.

1. **The nine window lines: keep.** He must recognise them to type his password; it is condition 3 of his rule.
2. **What `aresos update` prints: keep, after S2.** They are bound to the rehearsal, so one look before step 6 is worth it. Ask about the words only. That a waiting change ends with PASS and not STOP is the design's own decision; D2 has made it, with its reason.
3. **What a refused word says: turn into a design decision.** Claude reads these lines; he sees one only if he types a refused word himself. They sit in an image file and can change in any release. Report them with call 2.
4. **The title bar stays "Enter SSH Credentials": keep.** He sees it every time and it is about how AresOS looks.
5. **The restart is its own word and window: keep, short.** It is what he does: two passwords per update. Say that a "no" is a new design step, not a switch: row 6, the saved title and "one thing per run" rest on it.
6. **The try on the laptop: keep.** It needs his hands and his password.
7. **Tell first after a failed update: turn into a design decision.** The card already decides it ("Help decides each repeat"). He cannot weigh it from what he sees beyond one more window. Report it in one sentence, and make that sentence true first (S1).
8. **`aresos rollback` from Claude's terminal: keep.** He lands on plain Bazzite without Claude and types the way back himself. That is his to decide.

## What was checked and holds

- **The state table against the journal code** (`owner.py:1287-1341`, `:673-737`, `:1622-1641`, `:1683-1688`, `:1778-1850`, `:1953-1961`):
  - a staged update, same boot: `pending`, row 6, the line is true;
  - a queued `previous`, `rollback` or `forward`, same boot: `pending`, row 6; every reorder is refused there (`:1628-1631`), so "this command changes nothing before it" is true;
  - a power cut before staging, or after it and before the shutdown, or a failed shutdown step: the list is as before, row 2;
  - a finished update whose record was cut: the survey records it, then row 8 or 9;
  - a failed retry: a refusal before verification, or a failed signature check, leaves the intent open and the next run is row 4 again; a failed staging step is closed by the stop routine when that finishes, and the next run is row 7 (if it does not finish, the intent stays open: row 3, 4 or 0); after a restart it is row 2;
  - a cut reorder: closed as not applied or recorded as in place, then rows 6 to 10;
  - `retry` always has the running AresOS first (the intent was written after `may_stage`), so rows 4 and 5 are the whole of it; the tools cannot be replaced while a staging intent of this boot is open (`:2613-2627`), so row 4's reference is T;
  - a Bazzite update waiting, an unknown list, an unknown journal schema, a journal that fits neither list: row 0;
  - the first switch staged: no shape, row 1.
- **D18, the whole chain.** `sudo`, then `bash -c`, then `at` (bash, one `readlink` by full path) run in the caller's directory and read nothing from it. `at` then changes to `/` before Python starts, so every later process inherits `/`: the tools' four child starts (`owner.py:312`, `:326`, `:377`, `:1730`) and everything `media.py` runs through them. `cwd='/'` and `-I` are second and third layers. All seven stdin starts in the payload and `:1426` import standard modules only. Where the tools cut a step's Python out of its script (`:297-302`, `:1424`), they split at the marker name, so the changed start line does not touch that. Of the steps, an installed system runs only `start-next`, `update`, `verify` and `stock-session`; the last two start no Python. On release 29 the installed tools are always 43's or later (an install refuses an older or equal version), so the dispatcher never meets tools without D18. `at`'s change of directory does not disturb 22d's install line: `at` resolves its own path first and the tools find their bundle by that path.
- **"What is not exposed today"** matches `commands.json`: the install line changes into its root-only copy first, and `export` starts no step.
- **D3 and D4's places** in `update()` and `start_next()` are the lines the note names.
- **D9:** the update's 70 minutes (`:82`, `:523-526`: about 10.5 for the stop routine) and review 4 of 22d on a helper that ends without output (`reviews/22d-tools-without-stick/REVIEW-4.md:26`). Step 0's expected `COMMAND=/usr/sbin/true` is what 22d's step 0 saw.
- **The model** (read, not run): `newest` last in both loops of `steps()` gives no new state. Each of its results is a self-loop, a survey's own resolution, or the successor of `update` or `forward` from the same state.
- **VM stages 1, 1b, 2, 2b, 3 and 4** lead to the rows they name. Stage 2b proves D19 from the saved record even if the harness cannot end the `foot`.
- **Section 8** as listed under S4 in the table above.

READY WITH CHANGES
