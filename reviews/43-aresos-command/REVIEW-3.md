# Fix check of review 2: the design note for package 43, the `aresos` command

Reviewed `reviews/43-aresos-command/DESIGN.md` at `5757cb2d` (draft PR #82): the revision after review 2, `git diff 0225c84e..5757cb2d` (two commits, `11fa66ed` and `5757cb2d`; only `DESIGN.md` changed).

Reviewer: the Claude agent on Fable 5.2 that wrote review 2. It wrote neither the note nor its revisions. Review only: no code, guide or test changed, nothing committed or pushed. This file is the one thing written.

**Scope.** A fix check (`docs/REVIEW.md`): review 2's thirteen findings, what the revision touched, and what it added beyond them. Not a fresh hunt.

**How it was checked.**
- The branch was pulled (already at `5757cb2d`) and the whole diff was read, then each changed place in the note as it now stands.
- **Main at `8c4ee092`.** `os/`, the guides and the workflow are byte-identical to `52d13cb7`, where review 2 read them (`git diff --quiet`). So no cited main line moved. Every line the revision newly cites was read there and holds.
- **Control:** the local `origin/pkg/18c-image` is still `dada7a9b`, the commit the revision now cites.
- **One new check ran as `ares`,** read-only, with nothing written: the syntax tree of main's `owner.py`, for every place that starts a program.
- Read as well: the model's ledger and driver, for I4's new sentence; 22c's cut watcher in `os/ci/owner_vm.py`, for VM stages 4 and 5; release 27's autostart and terminal wrapper at `b216f28f`; the emergency card.
- No `sudo`, no owner tool, no rpm-ostree, bootc or ostree command, no `os/tests/test_owner_*` module.

## Verdict

**READY.**

All thirteen findings of review 2 are fixed. The three that were settled differently from my wording (N5, N6, N8) are settled soundly, and N5 better than I proposed. What the revision added beyond the findings holds against the code. D20 and D21 hold. The six owner calls are things he can judge from what he will see or do, and they are written in plain words.

Seven nits are left. None changes the design, and none needs another review; four are a word or a line in text that goes to the owner or into the guide.

## Review 2's findings

| Finding | Status | Why |
|---|---|---|
| **S1** "tell first" holds only if nothing else ran first | **Fixed** | By the first fix, which the lead chose. Row 2 now says "this run's own survey". Its new bullet names every word that closes the journal (`owner.py:1989`, `:1532`, `:1568`, `:1976`, `:1600-1606`: right). D21 records the decision. The guide sentence, the card sentence and row 2's second line are true now. A unit row pins `check`, then `newest`, as row 7. The card does say "**was not applied** shows only once" (`docs/EMERGENCY.md:20`), as the revision claims. One word left: N4. |
| **S2** two lines forecast the next run wrongly | **Fixed** | Row 2's second line makes no forecast. The extra line has two endings, by whether a restart waits, and a fixed place (last in the result). Both endings are true: after row 10's third wording the state is `applied` and the next run is row 7. Unit rows for each. |
| **S3** D18's first test cannot fail | **Fixed** | Three layers, one test each, with the other two absent: `at` alone; the directory alone (a real `Step` from the marker folder, a script without `-I`); `-I` alone (`bash -seu` in the marker folder, not through `Step`, with `python3 -` as the control). Each fails when its own layer is taken out. This matches what review 2's third check showed. |
| **S4** row 6 lists keep-stock | **Fixed** | Out of row 6, its unit row and section 5. One bullet says what happens instead (row 10, second wording, as `forward` does today) and why that is wanted. A unit row and the ledger's `choose` follow. |
| **N1** D4's headline and I4 | **Fixed** | D4 lists what can still stop an announced run: the signature check (`:1806`), the second read (`:1808-1810`), the step itself, and for a forward the step's own check (`:1656-1666`). I4 says why the model can stay strict. That reason is true: the ledger has full events and cut phases only, no step that refuses and no list that changes inside a command (read in `ways_back_ledger.py`). One sentence could be sharper: N6. |
| **N2** the second guard cannot fire | **Fixed** | Kept as a backstop, and not left untested: the guard is one method, called directly for both answers; a counting stand-in shows two calls through `newest` and none through the inner `update`. A changed list gets `:1810`'s text. |
| **N3** D19, three facts | **Fixed** | How `pgrep -x` finds the script, and the 15 characters, with a test. The keeper's exception with its lines (`aresos-desktop:166`, `:2473-2477`: right). `check` gets a line of its own for that state, a guide sentence and lead point 14. One thing for the lead to weigh there: N7. |
| **N4** two 18c line numbers | **Fixed** | `:863-865` and `:374`, right at `dada7a9b`; each place is now named by what it does. |
| **N5** VM stage 5's start state | **Fixed**, settled differently | Stage 4 is now the cut run in the danger state, and stage 5 resolves it and walks the danger state whole. The revision is right where I was not: 22c's watcher stops the tools after the reorder is on disk (`os/ci/owner_vm.py:1808-1811`, `:2092-2122`), so the next word shows `had made its change; it is recorded now` (`owner.py:1338`), not `was not applied`. Typing `check` and not `newest` on R28 after the reset is right too: with the made-up release, `newest` there would be row 7. |
| **N6** `main()` changes in four places | **Fixed**, settled differently | `newest` moves each line it has printed from `notes` to `said`, so the two places where `main()` prints notes need no change. That works: `main()` reads the list only after the command returns or stops (`:2933`, `:2938-2939`). A unit row holds "once" on both paths. |
| **N7** row 3 leaves out the settings line | **Fixed** | Row 3 prints it, under the inner word's own condition (`:1847`). |
| **N8** I2 has one edge | **Fixed**, one sentence and no code | As review 2 allowed. The edge is named with why it is harmless; I2 is marked as the model's judgment. |
| **N9** a staged row with no journal | **Fixed** | One sub-bullet; both readings end at `:1631`. |

## What the revision added beyond the findings

- **`podman login` gets `cwd='/'`, with a syntax-tree test: holds.** Read from the tree of main's `owner.py`: it calls `subprocess` in exactly four places, `:312`, `:326`, `:377` and `:1730`, and none passes a directory today. `media.py` has none. The step bodies that the tools load into their own process (`:1243`, `:1440`) do call `subprocess` in some of their functions, but the tools call only three of those functions there (`deployment_processes`, `arguments`, `keymap_argument`), and none of the three starts a program. So "four starts" is right. One gap in the test: N5.
- **Lead point 14, the new `check` line: there, and right to list.** It is a tools line, so its words are settled before step 6.
- **D19's description of release 27's autostart: corrected, and true.** Release 27's autostart starts the polkit agent and `/usr/bin/aresos-terminal`, which runs `/usr/bin/foot`; release 13's starts only the terminal.
- **The extra line's fixed place: holds.** Last in the result; in row 10 behind the title's lines.
- **Section 6's failed-update sentence: true now,** and "never to see what it says" closes the run the old text invited.

## New findings

### BLOCKING

None.

### SHOULD-FIX

None.

### NIT

- **N1. D20's third shape does not fit `keep-stock`.** `aresos keep-stock: this belongs to installing AresOS from plain Bazzite …` is not so: keep-stock is a way-back word for a running plain Bazzite with AresOS installed (`owner.py:1763-1776`), not part of installing. The shape also gives no full command although there is one, against D20's own rule ("say where it works, with the full command where there is one"). Give keep-stock `layout`'s shape with "only on plain Bazzite". It is an image file; step 3 can take it.
- **N2. Call 2 shows the failed-update line cut off.** It ends in "…" just before the half that matters: `It waits only this once: run again, it says what it does and does it. First see EMERGENCY, Failed or bad update`. He settles these words before step 6 and cannot judge what he is not shown. Print the line whole. Its middle sentence also reads better as "run it again and it says what it does, then does it".
- **N3. Call 6 says "Nothing on the laptop changes".** The try puts one small helper file in his home folder (section 4: "a copy in his home"). Say so, and that Claude removes it afterwards.
- **N4. "Repeats the update" is not so in one state.** D21's sentence for him, the guide sentence and the card sentence say that after **was not applied** `aresos update` repeats the update at once. Where the failed update was begun on an older AresOS (#263), the next run goes forward and repeats nothing; section 5 says so for the tools' line. The rule beside it ("only when Help has decided") is the safe one in both states, so one clause is enough: "(where an older AresOS runs, it goes forward first)".
- **N5. The syntax-tree test should read `media.py` too.** It runs in the same root process and is in the payload. Today it starts nothing; the test is there for the day something does.
- **N6. D4's closing sentence.** "A refusal of a check that had not yet run" also fits `:1810`'s comparison, which is allowed. Say it as the headline does: a refusal by a check that could have run before the announcement.
- **N7. For lead point 14: the keeper's give-up is the one state where D19 turns a PASS into a STOP.** The keeper's failure terminal is a `foot` (`aresos-desktop:96`, `:2446`), so version 4's `check` passes there while that window is open. With D19 it stops, before the title's lines. That is the state after a bad update, and the card's route to `previous` runs through `check`'s line "confirmed after the restart". The note sends this case to Help and names `aresos title`, which does show that line. That holds. When the line's words are settled, decide as well whether the card names this case, so that Help's answer is on the card and not only in the box.

## The owner calls, D20 and D21

**The six calls.** Each asks for something he can judge, in plain words, with the question first, then why, the advice and the options. Each statement in them was checked against the note and the code.

1. **The line in the password window: good.** The nine lines equal section 3's table. He reads them before he types his password.
2. **What `aresos update` tells you: good, with N2.** It asks about the words only and says what is already decided. The five lines equal section 5's.
4. **The title of the password window: good.** True that a window of our own would look right and be no safer (fact 8).
5. **The restart is a step of its own: good.** It says what he does (two passwords) and that option B is a new design round.
6. **A short try on your laptop: good, with N3.** It needs his hands; the try equals section 4's three points.
8. **`aresos rollback` from Claude's terminal: good.** It says where he lands and what he then types himself.

**D20 holds.** Claude reads these lines, they sit in an image file, and he is shown them and not asked. One of its three shapes needs a word: N1.

**D21 holds.** The tools tell once and remember nothing; the rule that guards the repeat is the card's and the guide's. That is the truth of the code (`owner.py:1327-1330`), the card decided it before this package (`docs/EMERGENCY.md:23`, `:27`), and a second mechanism beside the card's rule would add a durable state the model does not have. The texts now say what happens in every order of words. One clause for one state: N4.

READY
