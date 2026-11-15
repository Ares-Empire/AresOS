# Username scrub (2026-11-15, board #306)

Board #306 asked the owner: "Your Mac username appears in 241 files on public AresOS main (old logs and docs).
Treat it as private?" His answer: **"Scrub current files"**. The lead `mac-aresos-control` carried it out on
branch `lead/306-username-scrub`, from main at `3e13fc22`.

## What changed

- **372 text files, 1,841 replacements: the owner's machine username became `owner`.** Nothing else in those
  files changed. The word diff is exactly 1,841 times the name → `owner`, no file mode changed, and every changed
  JSON, JSONL and Python file still parses.
- The 241 in the question counted only macOS home paths. The full count covers every form:
  - home paths: macOS `/Users/owner/`, Windows `C:\Users\owner\` (also JSON-escaped), Git Bash `/c/Users/owner/`,
    WSL `/mnt/c/Users/owner/`, `file:/C:/Users/owner/`;
  - Claude Code's scratch and project folder form, `-Users-owner`;
  - the author and committer name in the GitHub run records under `os/manifest/ci/`. The capture scripts had
    written the name there in place of the real authors, next to `admin@example.com`. The capture scripts
    themselves (`reviews/11-two-disk-rehearsal/capture-11*-evidence.py`) now write `owner`.
- Where:
  - 247 files under `reviews/` and 121 under `os/manifest/ci/`;
  - `docs/WORKFLOW.md`, `docs/REVIEW.md`, `briefs/14zw-local-privacy.md` and `HANDOFF.md`.
- `changed-files.json` lists each file with its sha256 before and after.

## What stays as it was

- **Git history.** Older commits still hold the name. Removing it there needs a history rewrite and a force-push,
  which this repo never does.
- **Recorded hashes.** 50 records cite the old sha256 or git blob id of 41 of the changed files:
  - the `source-bindings.json` and `host-walk.json` of packages 16, 22c, 27 and 22d (22d's are the active bindings),
    and `reviews/22d-tools-without-stick/runs/tools-local-43737933979/22d-bound-sources.json`;
  - under `os/manifest/ci/14/`:
    - `files.json` in `14p-`, `14r-`, `14t-`, `14ze-` to `14zj-`, `14zq-`, `14zw-` to `14zze-preflight`;
    - `files.json` in `14zg-` and `14zp-qualification-stop`;
    - `files.json` in `14zzb-` to `14zze-round`;
    - `preparation.json` in `14zq-` and `14zw-` to `14zze-preflight`;
    - `review-tools.json` (`14zzb-round`), `closing-tools.json` (`14zzc-` to `14zze-round`),
      `14zy-round/local-and-native-checks.json` and `local-verification/result.json`;
  - `os/manifest/ci/11k/full-analysis.json` and `os/manifest/ci/11j/stop-analysis.json`.

  These records describe the bytes a run actually used, so they keep the old hashes. Rewriting them would falsify run
  evidence. No test or tool compares them with current bytes, apart from the active bindings and the pending list
  below. The original bytes are at `3e13fc22`, and `changed-files.json` maps each old hash to the new one. The cost is
  that the archived tools no longer reproduce their runs byte for byte (they now name `owner`'s home). They are
  archives and are never run again.
- **The bound files.** Three changed files are in the active source bindings: the archived preflight tools
  `os/manifest/ci/14/14zze-preflight/commit-preflight.py`, `final-local.py` and `local-privacy.py`.
  - As `linux-aresos` asked, no binding table or host walk was edited.
  - `python3 reviews/27-first-update-release/rebind.py pending` put the three files on
    `os/manifest/ci/16/pending-rebind.json`, and the next rehearsal rebinds them.
  - Nothing under `os/owner-tools/`, `os/release/` or the owner guides changed.
- **Archives and images.**
  - None of the 224 zip, gz and jar files, nor the three gzip `.dat` test fixtures under
    `os/tests/fixtures/desktop-world/`, has the name in a member (scanned recursively, decompressed). The only byte
    matches are chance ones inside compressed data: PNG images, deflate streams and gzip members.
  - OCR (tesseract 5.5.2) of all 1,940 tracked images and the 960 images inside the zips found the name in none.

## Keeping it out

- `.github/workflows/repo-privacy.yml` runs on every pull request. It fails when a file's text or name puts anyone
  other than `owner`, `...` or a built-in account in a home path:
  - macOS `/Users/<name>`;
  - Windows `C:\Users\<name>` (also JSON-escaped, any case) and `c:/users/<name>`;
  - Claude Code's `-Users-<name>` folder form.

  It prints only file and line for text and only a count for file names, never the text, because the run log is
  public. On the base `3e13fc22` it flags 257 files (1,293 lines); on this branch none.
- What it can't see: a lowercase `/users/<name>` with no drive letter (ordinary code folders are called `users`),
  URL-encoded paths, and the bare name outside a path. A public check can't look for the name itself without
  publishing it.
- `AGENTS.md` hard rule 6 tells builders to write `owner`, also in made-up examples, or repo-relative paths.
- Direct pushes to main skip the check, so leads keep the same rule by hand.
- Review: `REVIEW-1.md` (FIX: the check failed on every pull request, and this list of citing records was incomplete;
  both fixed).
