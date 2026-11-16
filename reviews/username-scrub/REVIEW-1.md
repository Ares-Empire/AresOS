# Review 1: username scrub (0ecdfbef, Claude Opus, 2026-11-15)

Verdict: FIX

The scrub itself is clean and exact, and the evidence chain is handled right. One real bug blocks the merge: the new
Repo privacy check fails on every clean pull request, this one included. One smaller fix: RECORD.md's list of records
that keep old hashes is incomplete.

## Findings

### 1. FIX: the Repo privacy check fails whenever there is nothing to find

`.github/workflows/repo-privacy.yml:23-30`. The step sets no `shell:`, so GitHub runs it as `bash -e {0}` (the run log
says `shell: /usr/bin/bash -e {0}`). `set -uo pipefail` adds pipefail but does not turn off `-e`. On a clean tree
`git grep` exits 1, pipefail makes the whole `git grep | cut > hits.txt` pipeline exit 1, and `-e` ends the script on
line 29, before `status=${PIPESTATUS[0]}` runs. The `1)` branch ("No home path names a real user.") can never be reached.

- Seen: this PR's own run 43764465482, job `home-paths`, failed after 12 s with only "Process completed with exit code 1":
  no `::error::` line and no "No home path" line, so it died on line 29, not in the `0)` branch.
- Reproduced locally: `bash -e -c 'set -uo pipefail; false | cat >/dev/null; status=${PIPESTATUS[0]}; echo reached'`
  prints nothing and exits 1; without `-e` it prints `reached`.
- The same applies to a `git grep` error (exit 128): it also dies silently on line 29, so the `*)` branch is dead too.
- Effect: every pull request gets a red `home-paths` check with no explanation, and the merge rule ("its checks pass")
  can't be met.

Fix: take the status without letting `-e` see it, for example

```bash
set -uo pipefail
status=0
git grep -nIP -e "$pattern" -- . ':!os/tests/test_aresos_shell_hardening.py' > grep.txt || status=$?
cut -d: -f1,2 grep.txt > hits.txt
case "$status" in ... esac
```

I ran that shape under `bash -e` against both commits: it prints "No home path names a real user." and exits 0 on
`0ecdfbef`, and exits 1 with the error on `3e13fc22`. (`grep.txt` holds the matching text but is never printed.) After
the fix, show both branches on the PR: the clean run must be green, and a throwaway commit with a made-up home path must
be red and print only file:line. Then drop that commit.

### 2. FIX: RECORD.md's list of records that keep old hashes leaves out the active binding table

`reviews/username-scrub/RECORD.md:28-33`. The list names files.json, preparation.json, review-tools.json,
closing-tools.json and result.json under `os/manifest/ci/14/`, the `ci/16` host walk and source bindings, and the 11j
and 11k analyses. I searched the whole tree at `0ecdfbef` for the old sha256 of every changed file. The count of 41
cited files is right, but 50 records cite them, and these are missing from the list:

- `os/manifest/ci/22d/source-bindings.json` and `host-walk.json`. These are the **active** bindings, the very reason
  the three 14zze tools went on the pending list.
- `os/manifest/ci/22c/` and `os/manifest/ci/27/` `source-bindings.json` and `host-walk.json`.
- `os/manifest/ci/14/14zy-round/local-and-native-checks.json`.
- `reviews/22d-tools-without-stick/runs/tools-local-43737933979/22d-bound-sources.json`.

Failure scenario: the next rehearsal's reviewer sees the three 14zze hashes change in the 22d → next rebind. They look
the files up in RECORD to learn which records hold the old bytes, and 22d isn't named. It's a short edit, and the PR
needs a second commit for finding 1 anyway. The PR text hedges with "and others"; RECORD reads as a complete list.

### 3. NOTE: smaller inaccuracies in RECORD.md and the PR text

- RECORD.md:43-44, "The only byte matches are inside compressed PNG data": there are also chance byte matches inside
  the zip files' deflate streams. Two gzip members also have them: `image-diff/new-files.json.gz` and `old-files.json.gz`
  inside `reviews/13-keyboard-layout/artifacts/13c-release-2-os-image-evidence.zip`. Decompressed, none of them holds
  the name, so the conclusion stands; only the wording is off.
- RECORD.md:43, "224 zip, gz and jar files": right by file extension. Three more gzip files have no `.gz` extension:
  `os/tests/fixtures/desktop-world/{desktop,level-modified-utf8,nether_home}.dat`. I decompressed and searched them:
  nothing there.
- The PR text says the guard finds "258 files on main". With the workflow's own fixture exclusion it's 257; 258 counts
  the excluded fixture.

### 4. NOTE: what the guard cannot see (no regression; the tree is clean today)

The pattern catches every form that was actually in the tree: on `3e13fc22` it flags all 257 files whose change was a
home path. The 115 changed files it would miss are exactly the `"name"` author fields in the run records and the 11
capture scripts, which hold no path. Gaps for the future:

- lowercase `c:\users\<name>` or `/users/` (Python's `normcase`, some Windows tools). `Users` is matched case-sensitively.
- the `-Users-<name>` folder form without a leading `/`, for example in backticks or quotes.
- URL-encoded paths (`%2FUsers%2F<name>`) and 5 or more escaped backslashes.
- file and folder **names**: `git grep` reads contents only.
- a bare name outside a path, like the old `"name"` fields. This can't be caught without knowing the name, which a
  public workflow must not hold.

`[Uu]sers` and allowing `(?:^|[^A-Za-z0-9])-Users-` would close the first two cheaply. The rest is acceptable as is.

### 5. NOTE: one way the public log could still show the name

`cat hits.txt` prints file:line. If a matching file's **path** itself contains the name (say a scratch folder copied in
as `-Users-<name>-…/log.txt`), the log prints the name. That needs a path the guard doesn't check (finding 4), so it's
unlikely. Checking `git ls-files` against the same pattern and printing only a count for path hits would close it.

### 6. NOTE: false positives are by design, and the exclusion is a whole file

Any other name in a home path fails the check. That includes made-up examples (the macOS home folder of `alice`, the
Windows one of `Administrator`), three dots standing in for the name (`.` is in the name class), and other people's
paths in third-party evidence, such as another CI host's build user or a vendored source map. (I describe these in
words because, written out, they would trip the check on this file.) None is in the tree today (0 hits at
`0ecdfbef`). `os/tests/test_aresos_shell_hardening.py` is excluded as a whole, so a real path added to that file later
would pass. Its only hit today is line 60's made-up Windows icon path, which names no one. Acceptable; a builder who hits a
false positive needs to know to add an exclusion, and AGENTS.md rule 6 doesn't say so.

### 7. NOTE: direct pushes to main are not checked

The check runs only on pull requests (RECORD says so). Leads push handoff commits to main directly. Adding
`push: branches: [main]` would at least turn main red after the fact. Cheap; the owner's call.

### 8. NOTE: leaving the cited hashes stale is the right call

- Those records say which bytes a run hashed. Rewriting them would falsify run evidence, and the original bytes stay
  at `3e13fc22`.
- No test or tool checks them against current bytes:
  - The only code that compares bound files to checkout bytes is `checkout_sources.active_tables` (22d's table) together
    with the pending list. `test_checkout_sources` passes (8 OK), and `rebind.changed()` equals the list.
  - The host-walk receipt tests (`test_tools_local_wiring.ReceiptTest` and the 22c one in `test_ways_back_probe`)
    return early once a `source-bindings.json` exists.
  - Nothing in `os/tests`, `os/ci`, `control/` or `.github/workflows` reads the 14zx–14zze files.json/preparation.json,
    the 11j/11k analyses or `local-verification/result.json`, and no code holds a full or shortened old hash.
- The next rehearsal binds the new bytes (`owner_vm.bound_sources` hashes the checkout), and `rebind.py rebind` then
  clears the pending list.
- The cost is that the archived tools no longer reproduce their runs byte for byte. For example, the 14zze tools now
  point at `C:/Users/owner/...`, which never existed. They are archives and are never re-run, and `changed-files.json`
  maps each old hash to the new one.

## What I checked and how

- **The diff is only the scrub.**
  - For each of the 374 modified files I walked the base bytes occurrence by occurrence (case-insensitive) and required
    the new bytes to equal the base with some occurrences replaced by `owner` and nothing else.
  - Result: 372 files and exactly 1,841 replacements, with every byte around them identical (so line endings, encoding
    and trailing newlines are unchanged). The other two modified files are AGENTS.md (one line, rule 6) and
    `pending-rebind.json`.
  - The replaced occurrences sit between `/…/` (1,518), `"…"` (220), `\…\` (87), `'…'` (11) and `-…/` (5). The 232
    occurrences left alone are all inside longer ordinary words, where replacing them would have been wrong.
  - No file mode changed, and the 3 added files are 100644. The changed JSON (107) and Python (31) files parse (no
    JSONL file changed).
  - `changed-files.json`: 372 rows, exactly the modified set minus the two above. Every before and after sha256 matches
    the blobs, per-file counts sum to 1,841, and there are 247 rows under `reviews/` and 121 under `os/manifest/ci/`.
  - RECORD's 241 macOS-path files and its form list (WSL 35 files, `file:` 42, `-Users-` 5) match the base tree.
- **Nothing is left.**
  - Every tracked file at `0ecdfbef` (19,818), case-insensitive: in text files the letters appear only inside longer
    words and identifiers, random base64 and tokens, a third party's handle and a made-up test string. I read each
    distinct case; none is the owner's name. No `<name>s-MacBook`, `<name>_` or similar. (I don't name these words here,
    because they would hint at the name.)
  - Every other hit is in PNG or zip bytes.
  - Encoded forms over the whole tree and recursively through all 227 gzip and zip containers (by magic bytes): UTF-16
    LE/BE in three cases, JSON `\u00xx`, `%xx`, HTML entities, base64 of `/Users/<name>`, `Users/<name>/`,
    `-Users-<name>`, `\Users\<name>`, `/home/<name>` and `<name>/` at all three alignments (standard and URL-safe), and
    hex of the name. The only hits are 6 chance hex matches inside numbers in machine logs, not the name.
  - Archive members: no member name holds the name. The plain-text hits sit only in PNG members and in compressed gzip
    members, and not in those members decompressed. The 211 UEFI `.fd` members and the 160 other binary files are
    covered by the UTF-16 search.
  - File and folder names: the letters appear only inside one longer ordinary word (7 files), never as the name.
  - Commit author, committer and message, the branch name, and PR #85's title and body (`gh pr view`): no hit.
- **OCR spot check.** `tesseract` on 239 screenshots most likely to show a path or account: the browser and Chrome
  packages, 07, 01, 16, 21, 22d and window-design. The name never appears as a word, and no `Users\`/`Users/` path is
  read anywhere. The 960 zip images match RECORD's count.
- **The evidence chain.**
  - No `source-bindings.json` or `host-walk.json` changed (only `14zh-preflight/initial-host-walk.txt`, a log). Nothing
    under `os/owner-tools/`, `os/release/` or the owner guides (`docs/INSTALL*`, `docs/EMERGENCY.md`) changed.
  - I recomputed `rebind.changed()` without running `rebind.py`: read 22d's tables from each commit, built a scratch
    root from the committed blobs and `.gitattributes`, and ran `checkout_sources.records`. Base gives 6 rows and head
    gives 9, each exactly the committed list, with `removed` empty in both.
  - The three new sha256 values equal the checkout bytes. The file is byte-identical to `rebind.write()`'s output, and
    only `changes` (one appended note) and `files` differ from base.
- **Citations.** I mapped every old sha256 (and git blob id, and 10-character prefix) of the changed files to the
  records that cite it: 41 cited files and 50 citing records (finding 2). I read the code that reads those records
  (finding 8).
- **Tests (macOS, `ARESOS_MODEL_SCOPE=slice`, one module at a time).**
  - Pass: `test_checkout_sources` (8 OK) and `test_rehearsal_retry` (7 OK; it reads the changed 11j `run.json`).
  - Can't run on this Mac: `test_tools_local_wiring` and `test_ways_back_probe` need `yaml`, which isn't installed here.
  - `test_release27` errors only on Linux-only things (`os.listxattr`, `yaml`, bash 3.2), and it reads no changed file.
- **Modules that read folders holding changed files.** I found them by searching test and CI code for the changed
  paths and their folders.
  - OK: `test_two_disk_vm` 29, `test_installer_webui` 9, `test_owner_tools` 13, `test_stock_prepare` 7,
    `test_system_keyboard` 7, `test_stock_probe` 3, `test_grub_bls` 6, `test_owner_path` 48, `test_owner_step_limits` 4,
    and `test_owner_reset` 4 (with `PYTHONPATH=os/ci:os/tests`).
  - Environment errors only:
    - `test_owner_commands`: Python 3.14's glob `case_sensitive` and `/proc`.
    - `test_owner_guard` and `test_owner_staged_release`: `yaml`. They reference `briefs/14zw-local-privacy.md` only
      as a path string.
    - `test_serial_staging`: 19 errors on this Mac, but the only record it reads from a folder with changed files is
      an unchanged 11n proof file.
- **The workflow.**
  - The pattern, run with `git grep -nIP` on both commits: 0 hits at `0ecdfbef` (exit 1) and 1,293 lines in 257 files
    at `3e13fc22` (258 without the exclusion).
  - The workflow file, AGENTS.md and RECORD.md don't match their own pattern. The `actions/checkout` pin
    (`11d5960a…`) is the one the other workflows use. Having no path filter is right, since the name could arrive in
    any file.
  - The exit-code bug is finding 1.
