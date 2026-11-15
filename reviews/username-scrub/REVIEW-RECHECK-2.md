# Re-check 2: username scrub fix (0ecdfbef..81c0e144, Claude Opus, 2026-11-15)

Verdict: SAFE

Both FIXes from review 1 are closed. The Repo privacy check now passes a clean tree and fails a dirty one, on
GitHub's ubuntu-24.04 runner and locally. It prints only `file:line` for text hits and only a count for matching file
names. Every git, git grep and perl error stops the step non-zero. RECORD.md's list of records that keep old hashes is
now exact: I recounted 50 records citing 41 files, and the folder ranges in the list expand to exactly those 50. What's
left are notes: one fail-open case that can't happen on a GitHub runner, and RECORD.md wording that claims a little more
than the pattern does.

## Findings

### 1. NOTE: if the output file can't be written, the check passes

`.github/workflows/repo-privacy.yml:40-41`. `git grep ... > "$RUNNER_TEMP/grep.txt" || status=$?` reads exit 1 as
"nothing found". But if the shell can't open the output file, the redirection fails before git grep starts, and that
also gives exit 1. Then the `1)` branch prints "No file holds a home path with a real user name." and the step passes.

- Reproduced: in a probe repo with 34 flagged files, setting `RUNNER_TEMP` to a folder that doesn't exist gives exit 0 and the
  "No file holds" line. The same happens on macOS bash 3.2 when `RUNNER_TEMP` is unset: `set -u` reports "unbound
  variable" but doesn't stop the `||` list. I couldn't try bash 5.2 for the unset case (Docker isn't running here). The
  missing-folder case doesn't depend on the bash version.
- On GitHub this can't happen: the runner always sets `RUNNER_TEMP` to its existing `_temp` folder, which also holds
  the step's own script. Both CI runs below show the step working.
- Cheap hardening, if wanted: run `: > "$RUNNER_TEMP/grep.txt"` before the `git grep` line. Under `-e` that stops
  the step when the file can't be created.

### 2. NOTE: RECORD.md describes the allowed names and the "any case" match a little too broadly

- `RECORD.md:62` says the Windows form is matched in "any case". The pattern accepts `Users` and `users` and a drive
  letter in either case. It does not match `USERS` in capitals (`C:\USERS\<name>`, `/USERS/<name>`). There were none
  at `3e13fc22`, and Windows shows the folder as `Users`, so the risk is small.
- `RECORD.md:59-60` and the workflow comment at line 4 say home paths may use `owner`, `...` or a built-in account. That
  holds for the `/Users/` and `\Users\` forms. In the `-Users-` folder form, only `owner` in lower case passes.
  Three dots, the runner account or `Owner` with a capital O after `-Users-` all fail the check. A builder who writes a
  Claude Code folder with three dots in place of the name, as the comment allows, gets a red check. That is the safe
  direction, but the wording should say so. A command-line flag like a double dash, `Users`, a dash and a word also
  fails, because a dash in front doesn't stop a match.

### 3. NOTE: RECORD.md's "What it can't see" list is honest but not complete

`RECORD.md:67-69` names three gaps. All three are true. I ran probes for other forms, and these also pass the check
(written with `<name>` here so this file doesn't trip it):

- five or more backslashes around `Users`, for example JSON escaped twice;
- JSON's escaped slash, `\/Users\/<name>`;
- mixed separators, `C:\Users/<name>` and `C:/Users\<name>`;
- Git Bash in lower case, `/c/users/<name>`: it has a drive letter, so "with no drive letter" doesn't cover it;
- capital `USERS` (finding 2);
- `/Users/./<name>` and a doubled slash after `Users`;
- a name whose first letter is not ASCII;
- every file git counts as binary (`-I`): the 1,940 PNGs, the zip, gz and jar archives, the `.fd` firmware files and
  the gzip `.dat` fixtures. The scrub covered these with OCR and archive scans; the check can't see them. This is the
  biggest of these gaps;
- Linux homes (`/home/<name>`), which are outside the stated macOS and Windows scope.

None of these forms holds the name at `3e13fc22` or now. The only effect is that a reader may take the list as
complete. A short fix: add "binary files (images, archives)" and "unusual escapes and separators" to that line, or
write "for example" in front of the list.

### 4. NOTE (unchanged from review 1, finding 7): direct pushes to main aren't checked

The workflow still runs only on `pull_request` and `workflow_dispatch`. `RECORD.md:71` says so and gives the
rule to leads. That's the owner's call; nothing new.

## What I checked

- **The range.** `0ecdfbef..81c0e144` changes only `.github/workflows/repo-privacy.yml`, `AGENTS.md` (rule 6, one
  line), `reviews/username-scrub/RECORD.md` and the new `REVIEW-1.md`. The probe `868a5ecf` and its revert `e3f0601e`
  leave a tree identical to `81c0e144` (same tree id).
- **The step locally.** I took the `run:` block out of the workflow and ran it with
  `env -i PATH=/usr/bin:/bin RUNNER_TEMP=<tmp> /bin/bash --noprofile --norc -eo pipefail` (macOS bash 3.2, Apple git
  2.54 with PCRE, perl 5.34).
  - Branch worktree: exit 0, "No file holds a home path with a real user name."
  - Base checkout `3e13fc22`: exit 1. It prints the error line and 1,293 `file:line` lines in 257 files, and every line
    after the error line is a path, a colon and digits. No file name matches there. The name doesn't appear in the
    printed output, while the raw `grep.txt` (never printed) holds it on all 1,293 lines.
  - The 257 flagged files are all in `changed-files.json`. The 115 changed files it doesn't flag are the author-name
    records and capture scripts, as review 1 found.
- **The step on GitHub (ubuntu-24.04, `git 2.56.1`).**
  - Both runs show `shell: /usr/bin/bash --noprofile --norc -e -o pipefail {0}`.
  - Run 43766800117 on `e3f0601e` (the fix's tree): success, "No file holds a home path with a real user name."
  - Run 43766699832 on the probe `868a5ecf`: failure. It printed the count "1 file or folder names hold ...
    (names withheld)", the error line and `reviews/username-scrub/guard-probe.txt:1`, then exit code 1.
  - The probe's made-up name appears nowhere in that log, and the owner's name appears in neither log.
- **File names.** In a probe repo with three matching paths (a `-Users-` folder, a `Users/<name>` folder, and a file
  name with backslashes and a colon, which git prints quoted), the step printed the count 3. It left out the text hits
  of the two matching files that had them and printed only the hit in a clean-named file. A repo whose only problem is a
  file name gives the count, "No file holds ...", and exit 1.
- **Errors.** Each of these stopped the step with a non-zero exit, and none printed file text:
  - not a git repository: exit 128 from `git ls-files`;
  - an invalid pattern: perl exit 255, whose message shows only the pattern; in an empty repo, git grep exit 128 and
    the `*)` branch;
  - a wrapper making `git grep` exit 128 or 2: the `*)` branch with the same code;
  - perl missing: exit 127.

  The only fail-open case is finding 1. Nothing in the step can print the matching text:
  - `grep.txt` is only cut to its first two fields and filtered;
  - `$names` is perl's count;
  - git's and perl's error messages name only paths or the pattern.
- **Pattern probes** (67 one-line files with a made-up name; every decided case right):
  - Flagged:
    - macOS, Windows, JSON-escaped (2 and 4 backslashes), lowercase Windows, `c:/users/` and `C:/Users/`, `file:`
      URLs in both cases, Git Bash `/c/Users/`, WSL;
    - the `-Users-` form after a slash, a backtick, a quote, a space or at the start of a line, and the Windows
      Claude Code form with two dashes;
    - names in capitals or with a space;
    - names that begin with an allowed word followed by more name characters (owner joined directly, or with a dot or a
      dash; runneradmin; Public; icon.svg; owner in the dash form);
    - dots followed by a name, a leading dot.
  - Passed:
    - `End-Users-guide` and another word joined to `-Users-` in the same way;
    - owner in every form and case, three dots, two dots;
    - runner, runneradmin, Shared, Public, Default;
    - the icon fixture's `icon.svg`;
    - GitHub API `/users/<login>` URLs.
  - No allowed word can let a real name through: each must be followed by a character outside the name class, and a
    real account name can't be only dots. The allowed words are case-insensitive in the slash forms.
  - Current tree: no hits. `git grep -I` skips no text file that matters: the 40 skipped `.txt` files are all empty,
    and `.gitattributes` marks only png, jpg, jar and zip as binary.
- **RECORD.md counts.**
  - Citing records: for every changed file I took the old sha256 (checked against the base blob), the old git blob id
    and, for `.ps1/.bat/.cmd` files, the CRLF variants. I searched every tracked file at the branch head, except
    `changed-files.json`, for hex runs of 10 or more characters that start or equal one of them. Result: 50 records
    citing 41 files, through 121 full sha256 values; no blob id and no short prefix is cited. The folder ranges on lines
    29-38 (with `14zza-preflight` not existing) expand to exactly these 50.
  - The 257 files and 1,293 lines on line 66 match my base run.
  - Archive and image counts by extension: 202 zip + 21 gz + 1 jar = 224, plus the three `.dat` fixtures; 1,940 PNGs.
  - The stated gaps are true (finding 3 lists what's missing).
- **AGENTS.md rule 6.** It now says to use `owner` also in made-up examples. That fits the new design, which has no
  per-file exclusion. "Refuses any other name" leaves out the dots and the built-in accounts, which is fine for a rule.
  No other file mentions the check.
- **The workflow, RECORD.md, REVIEW-1.md and this file don't trip the check.** The first three are covered by the
  branch run. I checked this file with the same pattern.
- **The username.** `git grep -IiwP` for it finds nothing in any tracked text file at the branch head. These have no
  hit either:
  - its macOS, Windows, `-Users-`, `/home/` and `~` path forms;
  - the added lines of the range;
  - the commit authors, committers and messages from `0ecdfbef` to `e3f0601e`.

  The letters appear in 7 file names only inside one longer ordinary word, as review 1 found.
