Reviewed PR #66 at `7ef03022` (package 22d, every step): the final review before the owner's laptop.

Reviewer: a fresh Claude agent on Fable 5.2, read-only. I built none of this. No owner tool, sudo, password helper or routine line ran, and no ostree, bootc or rpm-ostree command; no workflow was started. I wrote only this file.

**In short:** the tools, the three generated lines and the guides are safe to take to the laptop. I found nothing wrong in `owner.py`, `media.py`, `bootstrap.py`, the payload or the guides, and the findings of reviews 1 to 4 are closed or handed on by decision (F6 to the council, F11 to package 22e, F18's image part to the next image). Every interruption I could think of leaves working tools and every way back. What is left lies around them, and none of it changes a file the rehearsal bound:
- **F1, before the board note:** this head is not the commit the laptop installs from. The branch conflicts with main, and the merge commit needs its own checks.
- **F2 and F3, the "Try this" text:** how Claude runs the routine line on the laptop is written nowhere, and the session's prechecks are missing.
- **F4, the report text:** it does not say what a wording change costs now, and one sentence about step 7b's rule is out of date.

## Findings

### F1, should-fix before the commit is announced: the laptop installs from a merge commit that nothing has tested

- **Where:** the branch against `origin/main` (`3961eeb7` today); `os/ci/rehearsal-packages.json`, `os/manifest/ci/16/pending-rebind.json`.
- **What happens:**
  - Main is 460 commits ahead of the branch's base `44ddfd16`. A trial merge (`git merge-tree`, nothing checked out) conflicts in the two files above; `.github/workflows/os-image.yml` and `os/tests/test_ways_back_model.py` merge by themselves.
  - After the merge three more bound files differ from 22d's bindings and have to wait on the list: `.github/workflows/os-image.yml`, `os/ci/rehearsal-packages.json`, `os/ci/vm.py`.
  - Checks-only run 43755153393 tests `7ef03022`, not the merge.
- **Why it matters:** "Try this" step 1 announces the merge commit. "The commit is on `origin/main`" is worth exactly what that commit's own checks are worth: the tests that hold the routine line, its label, the payload and `docs/OWNER-TOOLS.md` equal must be green on it. Main has no branch protection, so nothing else enforces that.
- **What I checked:** none of main's 460 commits touches `os/owner-tools`, `os/release`, `docs/INSTALL.md`, `docs/EMERGENCY.md` or `docs/INSTALL-STATUS.md`. So a correct merge changes neither the fingerprint nor a line, and no waiting file falls under step 7b's rule.
- **Fix:**
  1. Merge main into the branch (or resolve at the merge) and run `rebind.py pending` once on the result.
  2. A checks-only run on that head, green with the full model.
  3. Before the board note: `git rev-parse <commit>:os/owner-tools` gives `73fb5929cddd36db91662bad7d83e5453b965ca6` (the tree run 4 walked), and the blobs of `docs/INSTALL.md`, `docs/EMERGENCY.md` and `docs/OWNER-TOOLS.md` are `115e4974…`, `7e68584f…` and `53c075c8…` as at this head.

  My SAFE carries over to the merge commit only if these three hold.

### F2, should-fix ("Try this" only): how Claude runs the routine line is not written down

- **Where:** `reviews/22d-tools-without-stick/PROGRESS.md:1270` and `:1277` ("Try this", steps 3 and 5). `docs/INSTALL.md:249` and `:276` say what Claude does, not how. In the VM it is a program: `os/ci/tools_local.py:157-198` (`CALLER`).
- **What happens:** the VM's caller reads the entry with `json.loads`, hands it to `/usr/bin/bash -c` as one argument, knows the process it started and finds the helper among that sudo's children. On the laptop Claude does all of this by hand in its Bash tool. The entry is a JSON string holding 15 lines with escaped newlines, quotes and backslashes.
- **Why it matters:** this is the one step of his route that the laptop will run differently from the rehearsal.
  - A slip in decoding or quoting (the line through a second shell, an unquoted here-document) lets Claude's own shell expand `$p` and `$(mktemp …)` first, as `ares`. Root then runs a text nobody reviewed, behind the right label. Most slips fail closed; I cannot show that all do.
  - For the 10-minute rule an improvised `pkill` can stop the wrong process, which is what R1 was about.
- **Fix** (report text, no bound file). "Try this" names one recipe:
  - Before his go, print the line's SHA-256:

    ```bash
    c=<announced hash>
    line=$(/usr/bin/git -C /var/home/ares/AresOS show "$c":os/owner-tools/commands.json | /usr/bin/python3 -I -c 'import json,sys; sys.stdout.write(json.load(sys.stdin)[sys.argv[1]])' tools-routine)
    printf %s "$line" | sha256sum
    ```

    It must be `0b11cfc562841f58393bdb11f7962556418f851241885ce21d11594a4e13c079`: the line run 4's caller ran (`tl-install-caller-result.json`, `line_sha256`). The folder line is `c1b579be56abe84e24c3be1be6a93edc7ccb39cee607988b493cfe55bc4bdd82`, the export line `7e1ffa764c263ef78025cee21c9d7ef2b6959e370765da40ae55046dc45a23d4`. I ran this recipe against this head: all three hashes agree.
  - On his go, as one background command of the Bash tool (variables do not survive between its calls): the same two lines, then `[ "$(printf %s "$line" | sha256sum)" = "0b11cfc5…c079  -" ] && exec /usr/bin/bash -c "$line" < /dev/null`.
  - The helper: `pgrep -a -u ares -x ksshaskpass` lists it with the label as its argument. After 10 minutes, if that process is still there, `kill` that one PID and nothing else. If it is gone, he has answered: wait for the result.

### F3, should-fix ("Try this" only): the session's prechecks and what he may see are missing

All read-only, before step 3, beside the integrator's `foot` and `labwc` check:
- **`foot` and `labwc` must still run when `check` starts,** right after the install. He keeps the AresOS terminal window open until the three PASS lines. Today both run (one `foot`). Without them he gets `PASS install`, then a STOP from `check` and `STOP after install: check or title refused`: the tools are installed, nothing is lost, but his first run ends on the STOP card.
- **No other session runs rpm-ostree, bootc or ostree** (also not read-only), or an `os/tests` owner module, from the folder line to the last PASS: `owner.py:593` STOPs on any such client of any user. The box names only owner commands. Tell the running sessions.
- **The Windows disk is not mounted** (`owner.py:1152`, **Protected disk is mounted**). Today it is not. A file manager on the desktop could mount it; the console never does.
- **Claude's shell holds no `GIT_*` variable but `GIT_EDITOR`, the checkout has no `refs/replace`, and `origin` is GitHub's address with no `url.*.insteadOf`.** All true today (see Trust).
- **A wrong password:** `Sorry, try again.` and the window comes back with the same label, up to three times (step 0 saw one on the laptop). After the third, nothing ran.
- **A power cut or restart during the install:** after the start the tools work (the old ones before the switch, the new ones after). On his go Claude runs the same two lines again and the install resumes; run 4 did exactly this (cut, then install).
- **Optional, the integrator's call:** after the PASS lines `/usr/bin/sudo -n true` must be refused, as the VM's last step. The laptop's sudoers file cannot be read as `ares`, so this is the only check there that no ticket is kept.

### F4, should-fix (report text): what a wording change costs now, and one stale sentence

- **Where:** `PROGRESS.md:1206` ("Changing a line inside the tools later costs a new tools version; changing a line outside them costs new generated lines, their tests and the guide's quotes"); `:1194`.
- **The cost.** Since step 7b, any change under `os/owner-tools/` or `docs/` fails `test_checkout_sources` while 22d's row says **VM REHEARSAL PASSED; NOT ON THE LAPTOP**. All ten calls live in those two folders (the tools, `commands.json`, `INSTALL.md`, `EMERGENCY.md`). So before the laptop session each one costs a new VM run (the report counts two dispatches left) or the row moved on. The owner should hear that with the calls. My advice: accept all ten for this install; wishes ride with the next tools version, which release 28 needs anyway.
- **The stale sentence.** `:1194` says "only test files and the CI workflow may wait". Since `7ef03022` the rule is "no tool, release script or guide may wait". The same old sentence stands in `os/manifest/ci/16/pending-rebind.json` (`status` and `decision`, lines 2 and 4) and in the docstring at `os/tests/test_checkout_sources.py:109`. Fix them with the merge: the list conflicts there anyway.

### Nits

- **N1, `os/owner-tools/bootstrap.py:44`, `:150-157`:** `FROM_COMMIT` uses `git` by PATH (`~/.local/bin` is first on his), and neither line clears `GIT_*` or passes `--no-replace-objects`. A `GIT_DIR` in the caller's environment wins over `-C`, and a replace ref for the announced commit makes `git show <commit>:…commands.json` return another commit's file (both tried in a scratch repository). Each needs a program writing in his home, which is the limit he was told; neither happens by accident and the laptop has neither today. For the next version of the lines: `/usr/bin/git --no-replace-objects` and `unset "${!GIT_@}"`. Not now: the change is under `os/owner-tools/`.
- **N2:** nothing in `os/config` or the image checks pins sudo's `env_reset` (on by sudo's default, and I assume in the image's sudoers, which I cannot read). The line leans on it little: the script sets PATH and umask itself and `at` runs `python3 -I -B`. With it on, what root's shell inherits from the caller is the locale. A next-image item beside `SUDO_ASKPASS` (F18).
- **N3, report "Not verified":** the VM never ran version 2 to 4 in one uninterrupted run. The copy ran before the cut and the rest after it, so every phase ran on a real system; the uninterrupted folder install runs on fakes (`test_owner_sources`) and by the stick route in the VM (version 4 to 5). Enough, but say so.
- **N4, `PROGRESS.md:1120`, `:1126`:** "the commit Claude announced" should be "the commit announced on the board". "Every rule unchanged" holds for installing from the stick; `export` to the stick now also takes a bundle this laptop installed before, and a folder-begun update may finish from a stick.
- **N5, "Try this" step 5:** the tools print `newer AresOS 5fad242fceac runs and starts next` and `(ostree:1) older AresOS 9b19b7942bc1`, not "R27" and "R13". Give him the words he will hear.
- **N6, `docs/INSTALL.md:276`:** the box names neither a wrong password nor a power cut. For the next guide change; until then F3 carries both.

## The questions

### 1. Safety on his laptop, version 2 to 4

Nothing I found leaves him worse off than today. All of version 2's records stay; before the switch the old tools are current, after it the new ones; the stick route's install rules are unchanged.

| Case | What he sees (through Claude) | What changed | Ways back |
|---|---|---|---|
| Cancel, or the window refused | The window closes; `sudo: no password was provided`, exit 1 | Nothing (run 4: tools, entry, journal, records and `/run` equal) | All; again on his go |
| No answer in 10 minutes | Claude stops the helper; the same line and exit | Nothing (run 4, 30 s) | All. If Claude never closes it, a late password runs the reviewed line: still safe |
| A refusal before the journal (another client, a mounted Windows disk, a layout trial, older or foreign tools) | `STOP: …`, the tools' last line, `STOP bootstrap: …` | One diagnostics record | All; version 2 stays current |
| A STOP or a kill during copy or switch | The same, or no line at all | The journal is open; `settle_tools` puts version 2 back | Version 2's commands work (run 4: `check` after the cut); the same line resumes |
| A STOP after the switch | `STOP bootstrap: …` although version 4 is current | The journal at retire | Version 4's commands work; the same line finishes |
| `check` or `title` refuses after `PASS install` | `STOP after install: check or title refused` | Version 4 installed | All of version 4's |
| A power cut | Nothing; the laptop restarts | As a kill at that point; `/run` copies gone, the folder in his home kept | As above (run 4's cut; versions 2's and 3's recovery over every cut in `test_owner_sources`) |
| A dirty or stale checkout | `STOP tools folder: this checkout differs from <commit> in os/owner-tools`, no window | Nothing; the tools folder as it was | All |
| A commit not on `origin/main` | `STOP tools folder: <commit> is not on origin/main`, no window | Nothing | All |
| Another session changes the checkout between the lines | Nothing, or `STOP bootstrap` | Nothing: the root line comes from the commit by hash, and root checks its private copy against the pinned fingerprint | All |
| Another session runs rpm-ostree, bootc or ostree | `STOP: rpm-ostree/bootc/ostree client active` | As the refusal or STOP rows above | As above |
| Another session runs an owner command | It cannot without his password; with it, one of the two STOPs with **Another owner command is running** | Nothing lost | All |

Two things are new for him and accepted by decision: after an export without a stick any program of his can read `/run/ares-records` until the restart, and the stick falls behind (it still takes records; run 4 showed both).

### 2. Trust

- **What his 8 characters bind:** the tools. Root checks its private copy of the folder against the full fingerprint written in the line, and the label's 8 characters are that fingerprint's (tests hold line, label, payload and `OWNER-TOOLS.md` equal). His phone is the one check that does not pass through Claude. It catches a stale checkout, a wrong `origin` and an old announced commit, each of which "on `origin/main`" alone lets through.
- **What it does not bind:** the routine line itself (the script around the tools, and the label). That rests on Claude's own `git show <commit>:…` and on "the commit is on `origin/main`", which only Claude's folder line checks. No second channel covers it. That is inside the limit he was told, and it is why F1 and F2 matter.
- **What cannot change what root runs:**
  - the working tree (the root line is read from git objects by hash);
  - the tools folder (root copies it to a fresh root-only folder and checks list and hashes there before any bundle code);
  - git's textconv, filters and pager (`git show` of a file ignores them; a filter that changed `git archive`'s output ends in a fingerprint refusal: both tried in a scratch repository);
  - hooks (the laptop has only `pre-push`; none runs for these commands);
  - PATH, `SUDO_ASKPASS` and `SSH_ASKPASS_PROMPT` for sudo, the helper and bash (absolute paths, fixed assignments).
- **What can,** each only with a program already writing as him: a `git` earlier on PATH for `FROM_COMMIT`, a `GIT_DIR` in Claude's environment, a replace ref or other write into the checkout's `.git`, a changed `origin` address (N1), and how Claude passes the line to bash (F2). On the laptop today: `git` is `/usr/bin/git`, the only `GIT_*` variable is `GIT_EDITOR`, no replace refs, grafts or `info/attributes`, `origin` is `https://github.com/Ares-Empire/AresOS.git`, no `url.*.insteadOf`, no `core.autocrlf`.
- **The environment sudo and bash see** is clean enough for this threat model: sudo is setuid and ignores the loader's variables, `-k -A` and the fixed helper hold, the script sets its own PATH and umask, and `at` starts Python isolated. What root inherits from the caller is the locale; nothing in the block's checks or in the tools' reads depends on it (the tools read JSON and unlocalised output). Claude's shell has `LANG=en_US.UTF-8`.
- **On this laptop** `git archive` of this head's payload gives `dcbc375f…`, every file checks and the file list is exact, with his git and its configuration.

### 3. Does the rehearsal prove the route he walks?

Yes, for everything a VM can show. Run 4 passed on `89bc0658`; since then only the status row, the bindings, the list and five test files changed. `os/owner-tools`, the guides and the harness are byte-equal to what it ran (tree `73fb5929…`).

What the laptop does that run 4 did not:
- **Claude's Bash tool as the caller** (a program stood in): F2.
- **The real GitHub** (a stand-in origin with the same `os/owner-tools` trees), and a merge commit as the announced commit: F1.
- **One uninterrupted install** (N3).
- **The real 10 minutes** (30 s), **a wrong password** (step 0 only) and **his phone compare**.
- **The window over the hub or a full-screen game.** If he sees no window, he says so and Claude closes it by the helper; nothing runs.
- **Claude Code's own permission prompt** for a sudo command, if his settings ask.

The driver itself is sound: nothing is typed before the helper has settled and a picture shows the window, the helper's argument equals the label in all seven windows, no keyring process started, and the cut was taken between copy and switch (`phases: copy, publish`, the entry still on version 2).

### 4. Step 7 and 7b

- **The rebind is right.** The six tables in `os/manifest/ci/22d/source-bindings.json` equal the run's `22d-bound-sources.json`. All 263 bound paths equal their bytes at `89bc0658`. The bound files that differ in the worktree are exactly the five waiting test files. The receipt test passes frozen.
- **The narrowed rule (`7ef03022`) is the right choice, and the merge needs it.** With the builder's version ("only tests and the workflow may wait") the merge with main would be red at once: `os/ci/rehearsal-packages.json` and `os/ci/vm.py` wait after it.
  - What it gives up: a harness file may wait while a row says rehearsed. That changes how a later rehearsal runs, not what the laptop gets.
  - What still holds: the payload check is unconditional (run 4's `tools` equals `sha256(SHA256SUMS)`); `commands.json`, `bootstrap.py`, the release scripts and both bound guides fall under the three folders; `docs/OWNER-TOOLS.md` is not bound, but `test_owner_equality` holds it to the payload.
  - Its price is F4: no guide or tools fix before the laptop session without a VM run.
  - The old sentences left behind: F4.
- **`unwalked_commands`:** counting the caller-run lines as walked is honest. The local walk reads the entry names from the program the harness sends, the same standard as "typed" on the other routes, and the run's captured `line_sha256` values are the SHA-256 of today's three entries (checked). Keeping walked lines on a list of unwalked ones would have been the worse record.

### 5. `check` and `title` from the desktop session

Besides `foot` and `labwc` (`owner.py:2016-2017`):
- **`idle`** (`:593`, in `check`, in `title` and three times in the install): no rpm-ostree, bootc or ostree client of any user, and no transaction. A busy desktop with other sessions is where this differs from the console.
- **`disk_record`** (`:1152`, in `check` and the install): the Windows disk has no mount.
- **`dumpkeys -C /dev/tty3`** (`:1992`) reads the kernel's console map as root; it works with tty3 logged out (run 4's `PASS check` came from the desktop).
- **Nothing else.** Neither command reads the terminal, the session or the login (`Tools.session()` is for the layout commands only). The keyboard read goes over the system bus, the account check through `id`.
- **`title`** saves a new title and makes the old one invalid, as at the console: Claude's board note replaces his saved copy.
- The routine route exists only on a release whose record says `ares` is an administrator, and `check` requires exactly that answer; R27 is one.

### 6. The report text and the ten wording calls

- **True to the code.** Calls 1 to 7 are the strings in `media.py`, `owner.py` and `bootstrap.py` word for word (compared by reading); 8 to 10 are what `INSTALL.md` and `EMERGENCY.md` say. Run 4's stage list matches the captures (15 audits, all equal to the baseline; 42 exported files; the receipt's source and caller).
- **Plain enough,** given that Claude reads the lines to him. The least plain are call 1's `uid 1001` (his account `ares`) and `SHA256 readback`; a wish for the next tools version, not a reason to spend a VM run.
- **Not true or not complete:** F4 (the cost, the stale sentence), N3, N4, N5.
- **"Try this"** is right as far as it goes; F2 and F3 are what it lacks.

## What I ran

- **Read:** `AGENTS.md`, the brief, `DESIGN.md`, `STEP-0.md`, reviews 1 to 4, `PROGRESS.md` (steps 1, 2, the fix step, 7, 7b and the report in full; step 4 and step 6's parts by their headings only), `git diff origin/main...HEAD` for `os/owner-tools`, `docs/OWNER-TOOLS.md`, the routine box, both stop cards and the 22d status row, `os/ci/tools_local.py` (whole), `owner_vm.py`, `owner_xhci.py`, `owner_media.py`, `verify_release.py`, `checkout_sources.py`, `test_checkout_sources.py` and `test_owner_equality.py`. The other test files I ran but did not read line by line.
- **Tests,** Python 3.14.8, one module at a time, `ARESOS_MODEL_SCOPE=slice`, in the worktree with bytecode off:
  - `test_owner_bootstrap`: 13 OK.
  - `test_checkout_sources`: 8 OK.
  - `test_owner_equality`: 11 OK.
  - `test_owner_sources`: 13 OK.
  - `test_tools_local_wiring`: 42 OK.
  - `test_owner_path`: 48 OK.
  - Not run: `test_owner_update` (the rule), `test_owner_export`, `test_ways_back*`, `test_owner_walk`.
- **Own checks:**
  - `git archive HEAD:os/owner-tools/payload` into a scratch folder: fingerprint, every hash, the exact file list.
  - Labels, literals and `OWNER-TOOLS.md` against the payload; the three entries' SHA-256 against run 4's caller results; F2's recipe.
  - The bindings against the run's capture, against `89bc0658` and against the waiting list.
  - `git merge-tree --write-tree HEAD origin/main`, and which bound files main changed.
  - A scratch repository for `git show` with textconv and a filter configured, `git archive` with a smudge filter, a replace ref, and `GIT_DIR` against `-C`.
  - Run 4's captures: `index.json`, the result, every caller result, the cut watcher, the export access, the receipt fields, and the install window's picture (title bar **Enter SSH Credentials**, the 70-character label whole on one line, Password, OK, Cancel).
- **GitHub, read-only:** run 43737933979 (success on `89bc0658`), run 43729592775 (success, both jobs), run 43755153393 (still running on `7ef03022`; not waited for), PR #66 (draft; mergeable not yet computed).
- **The laptop, read-only:** `pgrep` for `labwc`, `foot` and keyring processes; my shell's environment, login uid and terminal (none; stdin `/dev/null`; not sandboxed); where `git`, `sudo` and `bash` resolve; the main checkout's branch (main, clean, at `origin/main`), `origin`, hooks, replace refs and git configuration; `lsblk` for mount points only.
- **Side effects:** `git fetch origin` in the worktree moved the shared remote-tracking refs. `git merge-tree` left unreferenced objects in the object store. The scratch folder is deleted and the worktree is clean but for this file.

## What I could not check

- The laptop's sudoers (`timestamp_timeout=0`, `env_reset`) and everything under `/var/lib/ares`: closed to `ares`. So also whether version 4's `check` accepts today's laptop; if it does not, the install refuses first with nothing changed, or `check` STOPs after it.
- The window over the hub or a full-screen game.
- The checks-only run on this head (running), and any run on the merge commit (F1).
- sudo's and ksshaskpass's sources: I relied on reviews 2 and 4 and on run 4's behaviour.
- The workflow file's diff and the harness tests' sources beyond their names and results.
- The budget figures and the count of 1613 tests in the report.

SAFE
