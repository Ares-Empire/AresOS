# 43 design note: the `aresos` command

Empire brief 296. Written 2026-11-15 on main `4d23b408` by a Claude agent on Fable 5.2 (the lead's choice: a new design for a tool that decides which installed system is replaced). A design note only: it changes no tool, test, guide or workflow.

Made by reading code. No owner tool, `sudo`, ostree, bootc or rpm-ostree command ran, and no window was opened.

**References.** `22d:` is `origin/pkg/22d-tools-without-stick` at `89bc0658` (tools version 4, which 43 builds on once 22d is merged). `18c:` is `origin/pkg/18c-image` at `84f45c28` (PR #58). No prefix is main at `4d23b408`. `owner.py` is `22d:os/owner-tools/owner.py` throughout.

**Words.** *Inner word*: a word of `/var/lib/ares/at`. **N**: the newest installed AresOS (`newest()`, `owner.py:756`). **T**: the release the installed tools carry (`owner.py:1790`); it is last in their history, so when T is installed, T is N. *Runs* and *starts next* are the title's words: the booted deployment and the first one in the list.

## The decisions in short

| | Decision |
|---|---|
| D1 | The choice lives in the tools: an 18th inner word, `newest`, in one root process under the one lock. |
| D2 | Its rule: continue an interrupted update; else, when N runs and starts next, install T (or say there is nothing to do); else go forward to N. One of these per run. |
| D3 | Staging through `newest` carries a guard inside `update`'s own two checks: it never stages unless the running AresOS is N. The inner `update`, typed by its own name, stays as built (#263). |
| D4 | `newest` says which of the two it does before it calls the inner word; that word's lines, journal and refusals are unchanged. |
| D5 | `aresos update` runs `newest` and nothing else. The dispatcher has no row that reaches the inner `update` or `forward`. |
| D6 | Nine words work from the desktop: `update`, `previous`, `rollback`, `check`, `title`, `records`, `logs`, `export`, `reboot`. Nine are refused with one line that names where they work. |
| D7 | One password window per `aresos` word, by 22d's mechanism unchanged. No sudoers rule, polkit action or service. |
| D8 | The window's line is `AresOS: <fixed phrase>`, without a fingerprint. His rule has three conditions; the 8-character compare stays for new tools only. |
| D9 | A root-owned helper closes an unanswered window after 10 minutes. The dispatcher becomes `sudo` (exec), so nothing sits between Claude and it. |
| D10 | The dispatcher is one Python file, `os/config/usr/bin/aresos`: a pure `plan()` and an exec. It is not a security boundary. |
| D11 | It starts `sudo` with a fixed environment plus the variables that say where the screen is. |
| D12 | Control's wrapper moves unchanged to `/usr/libexec/aresos-control/cli`; every first word that is not a tools word goes there unchanged. `newest` joins Control's reserved words, and a test holds the three word sets equal. |
| D13 | "Nothing to do" and "newer tools would bring a newer release" are one state to the tools: one message, which prints the tools' version line for Claude to compare. |
| D14 | The guides gain one box in front of the console boxes, which do not change; the emergency card gains three sentences. |
| D15 | Proof: unit tests; the model with the new word and three new invariants; one VM run of 43's own for the tools; the dispatcher's stages ride R29's release rehearsal. |
| D16 | In the image: two `os/config` files and Control's moved wrapper, explained by the release diff's existing rules; the helper's package version is pinned. |
| D17 | The seam for the online update is the dispatcher's `update` row and the "nothing to do" message. Nothing of it is built. |

## 0. Facts the design rests on

1. **The inner `update` installs T by staging and nothing else** (`owner.py:1778-1850`). It refuses with `RELEASE_INSTALLED` when T is installed but not both running and first (`:1798-1802`, text `:61-62`), and with `FORWARD_FIRST` unless the running system is an AresOS and first (`may_stage`, `:1635-1641`, text `:65-66`). When it stages, ostree's shutdown step removes the other AresOS, whichever it is (`:1816-1817`, `:1843-1849`).
2. **The danger state** (#263): an older AresOS runs and starts next (after `previous` and a restart), a newer one is installed, and the tools carry a T that is not installed. There the inner `update` passes every check, stages T and removes the newer AresOS. It says so; it is the owner's decision 5 and stays reachable by the full path.
3. **The inner `forward`** makes N the next start by one reorder and never stages (`:1953-1961`); where N already starts next it changes nothing (`:1677-1688`).
4. **An interrupted staging** in the same boot is `update`'s to continue; every other word stops and names it (`outcome`, `:1287-1341`).
5. **What needs a terminal or the console in code:** `login` (a hidden prompt, `:1714`), `layout` (`Tools.session()`: the physical tty3/tty4 login of `ares-recovery`, `:2078-2110`), the tools update on the stick route (`:2593`) and the first install (`:2761`). Every other word requires only root (`:2888`); the guides alone route them to the console (22d's N10, `22d:briefs/22d-tools-without-stick.md`).
6. **The tools are root-only** (`/var/lib/ares`, 0700, `owner.py:2918-2919`). A program of `ares` cannot read what is installed, which toolset is current or its fingerprint.
7. **`/usr/bin/aresos` is an image file.** Plain Bazzite and every AresOS before R29 have no dispatcher, and plain Bazzite has no `ares` administrator. There the full path at the console is the only route, as today.
8. **The password window proves that he approved a root command now, not which** (`22d:reviews/22d-tools-without-stick/DESIGN.md`, section 1). The caller sets the line inside; the title bar is the helper's own, "Enter SSH Credentials" (`22d:reviews/22d-tools-without-stick/STEP-0.md`). `ares` has `timestamp_timeout=0` (`os/config/etc/sudoers.d/aresos-everyday:5`, required by `os/ci/image-checks.sh:31`).
9. **What 22c's reviews found** with both jobs in one word: the guide's "follow it" led from a return into a staging that nobody had announced (`reviews/22c-ways-back-after-update/REVIEW-4.md:8-9`). The cure there was one word per meaning, held by the model on every edge (`os/tests/test_ways_back_model.py:266-279`).

## 1. Where the choice lives (D1 to D4)

| | Option | Window | Journal and resume | Refusals | Model |
|---|---|---|---|---|---|
| A | A read-only inner word names the word that applies; image code under one `sudo` runs it | One, but two tools processes: the lock is released between the answer and the act | Unchanged | Image code must read the tools' answer; any default other than "stop" is the wrong guess again | Cheap for the read-only word; the composition the owner types is outside the model |
| B | One inner word decides and runs exactly one inner command in the same process | One process, one lock | Unchanged: the journal's word stays `update` or `forward` (`owner.py:763`, `:1345-1359`) | The two refusals that point from one word to the other cannot occur; all others pass through | A new state-changing word: it must be in the ledger and the driver |
| C | Image code runs `forward`, reads its lines, then perhaps `update` | Two changes possible in one run | | Parses guide text | Rejected: it breaks "one of the two per run" |

**D1: option B, the inner word `newest`.** Reasons:
- The decision and the act share one survey and one lock, so they cannot disagree. With A that holds only by an argument over cases.
- The dispatcher stays a table with no logic: it never reads a tools answer, so it cannot guess.
- The one word then also works at the console with the full path, on plain Bazzite and on older releases, wherever these tools are installed. With A it would exist only where the dispatcher is.
- The lead's decision holds as written: `forward` and `update` stay separate inner commands, unchanged for whoever types them. `newest` is a third entry in front of them. What made one word unsafe in 22c was a second job following the first without an announcement; D2's "one per run" and D4's announcement, both checked by the model on every edge, are the answer to that, not the number of words.

**D2: the rule,** read from `survey(retry='update')` (`owner.py:1600-1606`), in this order:

1. An interrupted staging stands open in this boot (`outcome` is `retry` or `complete`): **continue it** with the inner `update`, as every other word already tells him to.
2. N runs and starts next:
   - T is not installed: **install T** with the inner `update`.
   - T is installed (it is N): **nothing to do** (section 5); no inner word runs and nothing is journalled.
3. Anything else (an older AresOS or plain Bazzite runs, or N runs but does not start next): **go forward** with the inner `forward`.

No AresOS installed: `NOT_INSTALLED`, as `forward` says today. A run never does two of these. After a forward and its restart, the next run may install T; the forward run's last line says so when T is not installed (section 5).

**D3: the guard.** `update()` gains one optional argument that only `newest` passes. With it, right after each of its two `may_stage` calls (`owner.py:1803`, `:1809`), it requires that the running AresOS is N, else: "A newer AresOS than the running one is installed; this command installs nothing from here: restart, then run it again; nothing changed". So the rule that matters is checked on the survey that staging acts on, also after the minutes that verification takes, and in case 1 (`retry`) as well. In case 1 `complete` nothing is staged, only recorded (`:1791-1795`), so no guard is needed. The guard fires only when the list changed between two reads or in case 1 after a console `update` from an older AresOS; after the restart the stale intent is archived as not applied (`:1327-1330`) and case 3 goes forward.

**D4: saying which.** Before it calls the inner word, `newest` prints one line with `say` (`owner.py:512`), which is printed at once, not with the result. Then the inner word's own lines follow unchanged (`Signed exact release staged …`, the removal lines, `Newest installed AresOS starts next …`, the title). The saved record gains `chosen` (`update`, `forward` or none). `main()` adds the word to `known` and to its method table (`:2890-2891`, `:2927-2931`); nothing else in it changes, so the last line reads `PASS newest`. Older tools answer `newest` with "Choose a documented owner command" and change nothing (`:2910`).

**Refusals.** Every refusal of the chosen inner word passes through as it is, with its "nothing changed". `RELEASE_INSTALLED` and `FORWARD_FIRST` cannot come out of `newest`, because rule 2 and rule 3 are exactly their conditions; a test and the model hold that. Messages keep spelling commands with the full path (`typed()`, `:50-52`): it works everywhere, and the tools cannot know whether the running system has a dispatcher (fact 7).

**The model** (`os/tests/ways_back_ledger.py`, `os/tests/test_ways_back_model.py`):
- The ledger gets its own `choose(s)`, written from D2 and not from the tools, and `transition(s, ('newest', phase))` equals the chosen word's transition, with the guard's stop in case 1. `newest` joins both loops of `steps()` (`ways_back_ledger.py:300-305`), the driver's method table (`test_ways_back_model.py:257-259`) and `WORDS` (`:444`).
- Its successors are the chosen word's, so no new state appears; the edges grow by about one word in ten. The builder measures the full model's time before and after and reports it.
- Three new judgments on every executed `newest` edge, by the fake's state before and after, like "one word per meaning" (`:266-279`):
  - **I1:** if anything was staged, the running system was N and started next before the command.
  - **I2:** no stop of `newest` names `forward` or `update` as the next step.
  - **I3:** the announcement was printed before the first change. The fake host notes the output at its first mutation.
- Any change under `os/owner-tools/` selects the full model in the hosted run (`os/ci/model_scope.py:30`).

## 2. The words (D5, D6)

`aresos update` is the only word whose inner word differs. The inner `update` is deliberately not reachable through the dispatcher: it is the word that can replace a newer AresOS (fact 2).

| Tools word | `aresos <word>` | Why |
|---|---|---|
| `newest` | as `aresos update` | D1 |
| `update` | not reachable | fact 2; from the console by the full path, as built |
| `forward` | refused, points to `aresos update` | `aresos update` goes forward in every state where `forward` would change anything (D2, case 3); one word (#262) |
| `previous` | yes | the way back after a bad update while the desktop works; no console check (`owner.py:1963-1969`) |
| `rollback` | yes | the way back to plain Bazzite; valid only on a running AresOS (`:1763-1767`), which is where the dispatcher is |
| `keep-stock` | refused | valid only on running plain Bazzite (`:1763-1767`), which has no `aresos` |
| `check`, `title`, `records`, `logs` | yes | they read the system and write only the private records |
| `export` | yes | 22d's folder export; from R29 it replaces 22d's `export-routine` line |
| `reboot` | yes | the restart, after his go; refuses a stale title, an attached stick and a layout trial (`:1971-1983`) |
| `layout` | refused | needs the physical recovery login (fact 5) |
| `login` | refused | his registry token at a hidden terminal prompt, typed by him and never through Claude (fact 5) |
| `install` | refused | only a bundle's start block runs it |
| `prepare`, `verify`, `switch` | refused | first-switch words: they run on plain Bazzite before any AresOS (`before_switch`, `:1574-1586`) |

**A refused word** opens no window and runs nothing: one line on stderr, exit status 2. Three shapes (wording: OWNER 3):
- `aresos forward: use aresos update here, it goes forward by itself when a newer AresOS is installed; nothing ran` (also for `newest`)
- `aresos layout: this works only at the recovery console, typed by you: sudo /var/lib/ares/at layout; nothing ran` (also for `login`)
- `aresos switch: this belongs to installing AresOS from plain Bazzite, at the recovery console; see docs/INSTALL.md; nothing ran` (`install`, `prepare`, `verify`, `switch`, `keep-stock`)

An offered word followed by anything else is refused the same way ("takes no further words"), so no stray argument reaches `sudo` or the tools' records (`owner.py:2893-2894`). Run as root, or with no desktop session (neither `WAYLAND_DISPLAY` nor `DISPLAY`), an offered word is refused with the full-path command for the console.

## 3. The password window (D7 to D9)

**D7: 22d's mechanism, unchanged.** `SUDO_ASKPASS=<helper> SSH_ASKPASS_PROMPT= /usr/bin/sudo -k -A -p '<label>' /usr/bin/bash -c '/var/lib/ares/at <inner word>'` (`22d:os/owner-tools/bootstrap.py:106-116`). The root command is 22d's rehearsed form (`export-routine`, `bootstrap.py:128-130`); a direct `/var/lib/ares/at …` would depend on how `sudo` looks up a command in a folder the caller cannot enter, which nobody has run. One window per `aresos` word. `update`'s and `forward`'s results already end in the title's lines (`owner.py:1850`, `:1688`), so an update needs no second window for the title; the restart is its own word and its own go.

**D8: the label is `AresOS: <fixed phrase>`, with no fingerprint.**
- In 22d the 8 characters name what is about to be installed from Claude's hands, and he compares them once with a public line. An `aresos` word installs nothing from Claude's hands: the command behind the window is fixed in the image, and the tools it runs went in under that earlier compare.
- To show a fingerprint, root would have to publish it where `ares` can read it, and then any program can show it too. It would add a compare to every command and prove nothing.
- So the honest answer to "how does he know the window is AresOS's own": from the window alone he cannot (fact 8). **His rule** for these windows: type the password only when (1) he told Claude to go just now, (2) the title bar says **Enter SSH Credentials**, and (3) the line inside starts with **AresOS:** and is the line for what he asked for, as the guide lists them. Otherwise Cancel. The guide repeats 22d's limit in the same words: the window stops accidents and a Claude that acts without asking, not a Claude that was tricked.
- What the image adds over 22d: the root command is a fixed short line, so `sudo`'s journal entry names exactly what each window approved (seen in `STEP-0.md`).

Proposed lines (wording: OWNER 1). Each matches 22d's rule `[A-Za-z0-9 ,]+: [A-Za-z0-9 ,]+` (`bootstrap.py:91-104`), matches none of the helper's 16 remembered-prompt patterns (each needs a quote or a trailing ": "; `22d:os/tests/test_owner_bootstrap.py:220`), and is shorter than the 70 characters 22d's walk shows wrapped:

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

The `update` line cannot say which of the two jobs will run: that is known only as root (fact 6). The tools say it right after the password and before any change (D4), and Claude tells him.

**D9: the window closes by itself.** `SUDO_ASKPASS` is a root-owned two-line helper, `/usr/libexec/aresos-askpass`, which runs `/usr/bin/timeout --foreground 600 /usr/bin/ksshaskpass "$@"`. After 10 minutes without an answer the window closes and `sudo` ends as after Cancel (`sudo: no password was provided`, exit 1): the helper's end without output is the path review 4 of 22d read in `sudo`'s source (`22d:reviews/22d-tools-without-stick/REVIEW-4.md:26`). The helper with `timeout` in front has not been run; R29's stage 4 shows it. Why build it in: 22d's rule has Claude find and stop the right process by hand, and review 2 showed what the wrong one costs (`REVIEW-2.md`, R1). If he has answered, the helper is gone and `timeout` has nothing to stop. The dispatcher execs `sudo`, so the process Claude started is `sudo` itself. Claude still starts an `aresos` word in the background and waits: `update` may take 30 minutes (`owner.py:82`). 22d's own two lines keep their rule; they are generated in the bundle and cannot use an image file.

## 4. The dispatcher (D10 to D12)

**D10: one file, `os/config/usr/bin/aresos`,** root-owned 0755, `#!/usr/bin/python3 -ISB` (one argument, as the kernel passes it). Python because the whole behaviour is then one table and one pure function that tests call directly, as they load the other extension-less helpers (`os/tests/test_aresos_shell.py:21`):
- `TABLE`: for each of the 18 tools words either (inner word, label) or a refusal line.
- `plan(argv, environ, uid)` returns either an exec (path, argv, environment) or a refusal (line, status). It reads nothing else.
- `main()` execs the plan or prints the refusal. No subprocess, no parsing of any output, no file read or written.

**It is not a security boundary.** It runs as `ares`, and everything it does `ares` can do by hand; the boundary is `sudo` asking for the password every time. The fixed paths and environment are there so that every run is the same, not to stop a hostile caller.

**D11: the environment for `sudo`** is built from nothing: `PATH=/usr/bin:/bin`, `LANG=C.UTF-8` (so the title bar reads as the guide quotes it), `SUDO_ASKPASS=/usr/libexec/aresos-askpass`, `SSH_ASKPASS_PROMPT=` (22d's review 2, N5), plus these from the caller when set, because they say where his screen is: `XDG_RUNTIME_DIR`, `WAYLAND_DISPLAY`, `DISPLAY`, `XDG_SESSION_TYPE`, `DBUS_SESSION_BUS_ADDRESS`. Whether that list is enough for the window to open is not known from reading (LEAD 5).

**D12: Control.**
- Control's wrapper (`18c:control/packaging/aresos`, three lines) is installed unchanged as `/usr/libexec/aresos-control/cli`: one changed entry in the install map (`18c:os/build.sh:92`) and its pin (`18c:os/tests/test_control_image.py:25`). The file is then inside the folder the launcher already requires to be root-owned and not writable (`18c:control/launch.py:16-20`, `:34`) and stays recorded in `control.json`.
- A first word that is not one of the 18, no word at all, and `--help` are handed on by exec with the arguments exactly as given. The dispatcher knows none of Control's words, so Control can add apps without an OS change, and an unknown word gets Control's own error. The image check that compares `aresos --help` as root and as `ares` (`18c:os/ci/image-checks.sh:821-823`) passes unchanged and proves the hand-over.
- If the image has no Control, the same cases print the nine offered words and exit 2.
- `newest` joins Control's `RESERVED` (`18c:control/tests/test_reserved_words.py:13-14`), a one-line change for `linux-tools`. A new OS-side test reads three sets and requires them equal: the tools' `known` (`owner.py:2890-2891`), Control's `RESERVED`, and the dispatcher's offered plus refused words. So a new tools word fails a test until all three know it.

**Tests** (`os/tests/test_aresos_command.py`, no root, no fakes of `sudo`):
- for each offered word, the exact argv and environment; `update` maps to `newest`, and no row holds `at update` or `at forward`;
- the three word sets; the labels against 22d's character rule and its pattern list (imported, not copied), their length, and that they differ;
- every refusal: its line, status 2 and no exec; extra words; root; no desktop session;
- hand-over: argv unchanged for other words, none and `--help`; the usage when Control's file is missing;
- `main()` execs and the module imports no `subprocess`; the helper's two lines are pinned;
- the guide's table of words and window lines equals `TABLE`.

**D16: in the image.**
- Two new `os/config` files (the dispatcher, the helper) and Control's moved wrapper. No new package: `ksshaskpass`, `timeout` and Python are in the image already.
- `os/ci/image-checks.sh`: owner, mode and no link for both files; a refused word's line and status as `ares`; an offered word without a desktop session refuses without calling `sudo`; the helper and `timeout` exist; and `ksshaskpass`'s package version equals the one whose patterns were read (6.7.5), so a new version fails the build until someone reads its patterns again (asked for in `22d:reviews/22d-tools-without-stick/REVIEW-1.md:130`).
- The release diff for R29 needs no new rule if step 3 gets it right: both `os/config` files are explained by `config_rule` (bytes equal the source, 0755, root; `os/ci/release_diff.py:212-229`), and `/usr/bin/aresos` leaves `control.json` while `cli` enters it. Step 3 adds a test that feeds these three paths to the diff's rules, so R29's release package does not meet an unexplained file.

## 5. What `aresos update` says (D13)

To the tools, "nothing to do" and "only newer tools would bring a newer release" are the same state: N runs and starts next, and T is N. The tools work offline and know no release after T. So there is one message, and it prints the tools' own version line in the form of line 1 of `docs/OWNER-TOOLS.md`, which Claude compares with that file on GitHub's main:
- equal: there is nothing newer; done;
- different: newer tools are announced. Claude installs them by 22d's route (his 8-character compare, one window), then runs `aresos update` again, which installs their release.

The lines (wording: OWNER 2; `<name>` is the title's name for a system, `owner.py:752`):

| Case | First line, printed before anything changes |
|---|---|
| Go forward | `Update: a newer AresOS is installed already, <name>; going forward to it. Nothing is downloaded and nothing is removed` |
| Install | `Update: installing the new AresOS release <reference>. This downloads it; it starts at the next restart` |
| Continue | `Update: continuing the interrupted update to <reference>` |
| Nothing to do | `Nothing to update: <name> runs and starts next, and it is the newest AresOS these tools know; nothing changed`, then `Owner tools version <N>: <8 characters>`, then `A newer AresOS comes with newer owner tools; Claude compares the line above with docs/OWNER-TOOLS.md` |

After a forward, when T is not installed, one more line: `These tools also carry a newer release; after the restart, aresos update installs it`. It informs; the guide does not tell him to follow it without the release's announcement (fact 9).

Nothing to do still costs one window, because only root can read the tools. The guide therefore has Claude run `aresos update` after an announcement or after `previous`, not as a daily habit.

## 6. The guides (D14)

- **`docs/INSTALL.md`, "Update AresOS to a new release":** one new box after 22d's routine box (`22d:docs/INSTALL.md:228`), "From Claude's terminal, on AresOS 29 or later":
  - the nine words with their window lines (the table of section 3, held equal to the dispatcher by a test);
  - his three-condition rule and the limit sentence;
  - that the window closes by itself after 10 minutes;
  - what `aresos update` prints in each case, with a pointer to the console box whose lines then follow ("Stage the new release", `:325`, or "Forward again", `:381`);
  - that Claude posts the title's lines to the board after every word that changes what starts next (22d's decision 8);
  - after a STOP: every STOP line word for word, his go, then `aresos export`, nothing else.
- 22d's box loses "every other owner command stays at the console … until a later release brings it here" in favour of "from AresOS 29 the next box".
- **The console boxes do not change**, rule for rule. They are the way that always works and the only way on plain Bazzite, on a release before 29 and when the desktop is down. They keep `update` and `forward`; `newest` is named once, as what `aresos update` runs and as usable there.
- **`docs/EMERGENCY.md`** (lines as on `22d:`):
  - "Failed or bad update" (`:18`) gains one sentence: if the desktop works, Claude runs `aresos check` and then, only as that card already says, `aresos previous`.
  - "A routine tools command stopped" (`:64`) also covers `aresos` words, with `aresos export`.
  - One line near the top: `aresos` exists only on AresOS 29 and later; everywhere else use the full path at the console.
  - The card stays one page.
- `docs/INSTALL-STATUS.md`: a row for the `aresos` route, open until R29's rehearsal. `docs/OWNER-TOOLS.md`: the new fingerprint, same form. `os/owner-tools/commands.json`: one entry, `newest`. `os/README.md`: one paragraph.

## 7. Proof and budget (D15)

**Unit tests:** section 4's for the dispatcher. For the tools: a table over what runs, what starts next, whether T is installed and the journal's state, giving the chosen word; the guard on both surveys; the announcement before the first change; the "nothing to do" lines; `chosen` in the record; that older tools refuse `newest`. **The model:** section 1.

**A VM run of 43's own, before merge, for the tools at the console.** Why its own: the tools change is what can replace a system, the lead asked for a rehearsal (`STATE.md:14`), and the fingerprint must not reach the laptop unrehearsed. Why at the console: R28 has no dispatcher (fact 7). It reuses release 28's rehearsal mode (`briefs/42-release-28.md`, B) with 43's bundle:

| Stage | What | Proves |
|---|---|---|
| 1 | On R27 (runs, starts next): `at newest` instead of `at update` | It announces the install and stages R28 |
| 2 | On R28 after the restart: `at newest` | "Nothing to update", the tools' version line, no change |
| 3 | `at previous`, restart, on R27: `at newest`; restart; `at check` | It announces forward; nothing staged; "Forward to … confirmed" |
| 4 | `at previous`, restart: R27 runs, R28 is installed. Then a harness-built next bundle whose release is a made-up one that is not installed (installed as in 22d's "stick with a next version" stage), then `at newest` | The danger state: forward, no login asked, no network, R28 still in the list |
| 5 | The same `at newest` once more, with a hard reset between the journal's intent and its record | After the restart it resolves as a cut `forward` does |

Every stage keeps package 11's audits.

**The dispatcher rides R29's release rehearsal,** because only that image has it and only there do the real image, the real tools and a real update meet. Stages for R29's release brief, on R29 after the update:

1. `aresos --help` equals Control's help; `aresos layout` refuses with no window.
2. `aresos check`: the helper's argument equals the label, a screenshot, no keyring process; Cancel runs nothing; then the password and `PASS check`; `sudo -n true` is refused afterwards (22d's driver, `22d:os/ci/tools_local.py:488`).
3. `aresos update`: "Nothing to update".
4. A window left unanswered closes after 10 minutes; `sudo: no password was provided`; nothing ran.
5. `aresos previous`, `aresos reboot`; on R28 at the console `at newest` goes forward; back on R29 `aresos check` shows the confirmation.

**Staging through the dispatcher** first happens in R30's rehearsal (R29 to R30 by `aresos update`), before any laptop session does it. Until then its staging branch is proven at the console (stage 1) and its mapping by the unit tests.

**Budget for 43's ledger entry:** 15 checks-only runs, 4 VM dispatches, 1500 minutes. The image checks run in the hosted checks; no build of its own is needed before R29's.

## 8. Build steps

One fresh builder each, gpt-6.1-sol at xhigh against a tight brief, about 250k tokens; each commits, pushes and keeps `reviews/43-aresos-command/PROGRESS.md`. Reviews on gpt-6-astra. If the model step resists two rounds, it goes to Fable.

| Step | What | Needs |
|---|---|---|
| 0 | The lead: `linux-tools` is told (D12); with the owner's OK, the laptop try of LEAD 5 | this note reviewed |
| 1 | Tools: `newest`, the guard, the lines, `chosen`; their unit tests. No payload or pin yet | 22d on main |
| 2 | The model: the ledger's `choose`, the driver, I1 to I3; the hosted full model; its time before and after | step 1 |
| 3 | The dispatcher, the helper, their tests, the image checks, Control's moved wrapper with its pin, the three-set test, the diff test | 18c Part A on main, or the lead's word that Control does not ride |
| 4 | The payload and its pins (fingerprint, `OWNER-TOOLS.md`, `commands.json`), the guides and the card, the equality tests | steps 1 to 3 and the owner's wording |
| 5 | Review of steps 1 to 4 | |
| 6 | The harness variant, its ledger entry, the VM run, the record step | R28 published and its rehearsal mode on main |
| 7 | Hand-over: the five rehearsal stages and D16's diff note into R29's release brief | |

## 9. The seam for the online update (D17)

- **Carries over:** the dispatcher's table (the online package changes the `update` row's root command and nothing else); the labels and the helper; `newest` as the tools' rule for "one of the two"; the guide's box; the rehearsal's window stages.
- **The one message that changes:** "Nothing to update … the newest AresOS these tools know" becomes an answer from the registry.
- **Deliberately not built:** a registry query, a signature check outside the tools, tools inside the image, a sudoers or polkit rule, a service, a timer, a helper with its own window.

## Open points

**OWNER** (what he sees or types; each with a recommendation):

1. **The nine lines in the password window** (section 3's table). Recommended as proposed.
2. **What `aresos update` prints** in its four cases, and that the last line reads `PASS newest` (section 5). Recommended as proposed.
3. **What a refused word says** (section 2's three shapes). Recommended as proposed.
4. **The title bar stays "Enter SSH Credentials".** A window titled "AresOS" needs a small helper of our own; it would look better and prove nothing more. Recommended: keep it until the online update, so that every AresOS password window looks the same.
5. **The restart stays its own word and its own window** (`aresos reboot`); an update never restarts by itself. Recommended.
6. **His OK for one harmless try on the laptop** (LEAD 5): a window with the line `AresOS: test` in front of a command that does nothing, as in 22d's step 0.

**LEAD:**

1. **The inner word's name,** `newest`. It shows in `PASS newest` and in the records.
2. **`rollback` offered, `forward` refused** (section 2). The other way round is defensible for both.
3. **D9's helper** against keeping 22d's hand rule for every word.
4. **`bash -c` against a direct root command** (D7). Direct is tidier in the journal; it needs one VM look at `sudo`'s lookup first.
5. **D11's variable list.** One try on the laptop, or R29's stage 2, shows whether the window opens with it. If not, pass the caller's whole environment with the four fixed values set, as 22d's lines in effect do.
6. **Routine lines for R28.** Without them the update to R29 is still typed at the console, and the first update Claude can run is R29 to R30. 43's bundle could carry three more of 22d's generated lines (`newest`, `reboot`, `check`, each with the tools' 8 characters) so that the update to R29 already runs from Claude's terminal. Recommended: yes, as a last separable step with its own window stage in the VM run, if the lead wants that update without the console; they go when R29 is on the laptop.
7. **With `linux-tools`:** `newest` in `RESERVED`; the wrapper's move and its header comment; whether Control's help gains one line that names the nine words (today `aresos --help` shows Control's words only).
8. **`check` requires a running `foot` of `ares`** (`owner.py:2017`). From Claude's terminal that holds only while one runs. R29's stage 2 shows it; a failure there is a tools finding, not the dispatcher's.
9. **The model's time** after step 2: if it outgrows the hosted job, split the job, never the exploration.
