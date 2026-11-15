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
- **Recorded hashes.** Other records cite the sha256 of 41 of the changed files:
  - `files.json`, `preparation.json`, `review-tools.json`, `closing-tools.json` and `result.json` under
    `os/manifest/ci/14/`;
  - `os/manifest/ci/16/host-walk.json` and `source-bindings.json`;
  - `os/manifest/ci/11k/full-analysis.json` and `os/manifest/ci/11j/stop-analysis.json`.

  These records describe the bytes a run actually used, so they keep the old hashes. The original bytes are at
  `3e13fc22`, and `changed-files.json` maps each old hash to the new one.
- **The bound files.** Three changed files are in the active source bindings: the archived preflight tools
  `os/manifest/ci/14/14zze-preflight/commit-preflight.py`, `final-local.py` and `local-privacy.py`.
  - As `linux-aresos` asked, no binding table or host walk was edited.
  - `python3 reviews/27-first-update-release/rebind.py pending` put the three files on
    `os/manifest/ci/16/pending-rebind.json`, and the next rehearsal rebinds them.
  - Nothing under `os/owner-tools/`, `os/release/` or the owner guides changed.
- **Archives and images.**
  - None of the 224 zip, gz and jar files has the name in a text member (scanned recursively). The only byte
    matches are inside compressed PNG data.
  - OCR (tesseract 5.5.2) of all 1,940 tracked images and the 960 images inside the zips found the name in none.

## Keeping it out

- `.github/workflows/repo-privacy.yml` runs on every pull request. It fails when a macOS or Windows home path, or
  the `-Users-` folder form, names anyone other than `owner` or GitHub's runner accounts. It prints only the file
  and line, never the text, because the run log is public.
- `AGENTS.md` hard rule 6 tells builders to write `owner` or repo-relative paths.
- Direct pushes to main skip the check, so leads keep the same rule by hand.
