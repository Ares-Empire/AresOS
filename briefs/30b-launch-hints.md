# 30b: A hint says how a program must be started

Empire board brief 288. OS helper package, a follow-up to package 30 (PR #55) on its own branch, which starts from package 30's last code commit `0156d727`.

**Builder:** a Claude agent (Opus 5.5), one step; Codex's week is kept for reviews. **Review:** two fresh read-only reviewers that aren't the builder (package and security), then the OS lead's read of the `os/` diff.

## Why

The owner (2026-11-13): "discord, lunar, chrome are all installed so these are the best first candidates."

The OS lead (2026-11-14): on this desktop Lunar Client's game needs two things that the owner's `lunar` command sets and Lunar's own desktop entry does not.

- The NVIDIA card: the entry has no `PrefersNonDefaultGPU`, so the helper starts Lunar on the Intel card.
- `SDL_VIDEO_DRIVER=wayland`: Minecraft 26.3 opens its window with SDL. Under labwc SDL picks XWayland (labwc lacks the fifo-v1 protocol), and there the game's OpenGL does not start on the NVIDIA card.

The helper starts a discovered program from its desktop entry, so Lunar Client opened from the hub starts without both. The cause is this desktop, not Lunar and not the owner's files, and the launcher may rewrite its own desktop entry. So the fix belongs where AresOS keeps what it knows about a program: the reviewed hint files that ship in the image (`/usr/share/aresos/apps/hints/`), which today can only say which windows belong to a program.

**Goal:** he walks into Lunar Client's logo, or clicks it in My apps. Lunar starts as it does from his `lunar` command: the game runs on the RTX 4060 in a native Wayland window. No other program's start changes.

## Read first

`AGENTS.md`; `reviews/30-installed-programs/REPORT.md`: "Hints file format", "Review fixes 2" and "Open after this package"; in `os/config/usr/libexec/aresos-shell`: `parse_hint`, `load_hints`, `apply_hints`, the launcher's `environment` and `spawn`, and how a registry app's `gpu` is read and used; `os/ci/image-checks.sh`'s hint check; `os/tests/test_aresos_shell_review_fixes*.py` for how hints are tested.

## What to build

1. **Two optional keys in a hint file.**
   - `"gpu": "discrete"`: the same meaning, and the same check for an NVIDIA card, as a registry app's `gpu`. No other value.
   - `"environment"`: an object of at most 8 entries. A name must match an allowlist that is one pattern in one place: `SDL_[A-Z0-9_]{1,60}` and nothing else (the OS lead's call: a list of what is allowed stays narrow by itself). A value is a string of 1 to 128 printable ASCII characters. Values are passed as they are, never expanded.
   - A hint may consist of start settings alone: it must have at least one window identity, `gpu` or `environment`.
   - `schema` stays 1: hint files ship in the same image as the helper that reads them, and a helper that does not know a key skips that file with a log line, as today. Say so in the report.
   - Anything else (another key, another `gpu` value, a name outside the allowlist, a value that is not such a string, too many entries) refuses the whole file with a log line, as today.
2. **Applied to the program the hint names**, as today only to a discovered program:
   - `gpu` from the hint counts like the entry's own wish; a hint can ask for the NVIDIA card, never take the entry's wish away;
   - the hint's `environment` is added to that program's start, after the session's environment is filtered and before the NVIDIA values, for every way the program is started (a `Terminal=true` entry included);
   - no other program's environment changes, and nothing new appears on the socket: `list_apps` and `app_details` answer as before, and the example messages under `mod/src/test/resources/shell-1.1/` stay unchanged.
3. **Lunar's hint** (`os/config/usr/share/aresos/apps/hints/lunarclient.json`) gets `"gpu": "discrete"` and `"environment": {"SDL_VIDEO_DRIVER": "wayland"}`, beside its window identity. Steam's stays as it is.
4. **`os/ci/image-checks.sh`**: the hint check expects the new Lunar hint. Change nothing else there.

## Verification

- Unit tests in a new `os/tests/test_aresos_shell_launch_hints.py`: each accepted form; each refusal above; a hint with start settings only; Lunar's shipped file loads with both settings; the environment a start gets with and without an NVIDIA card (the SDL value is set in both; the NVIDIA values only with the card); another program started next gets neither; a registry app and a 1.0 client are untouched. Say for each test whether it fails without the change or is a control.
- The real start route, with a stand-in only: extend `os/tests/check_aresos_shell_launch.py` (real `systemd-run --user --scope`) with a stand-in desktop entry and hint in the test's own folders whose program writes its environment to a file; assert the SDL value arrived and, on this laptop, the three NVIDIA values. **Never start Lunar Client, and never read or touch `~/.lunarclient`.**
- On the laptop only the helper's modules: `python3 -m unittest discover -s os/tests -p 'test_aresos_shell*.py'`, `-p 'check_aresos_shell_launch.py'`, `-p 'check_aresos_shell_icons.py'`, each with `TMPDIR="$PWD/.work/30b-launch-hints/tmp"`. **Never the whole `os/tests` suite** (AGENTS.md: `test_owner_update` starts the real owner tools).
- Push, then one hosted run: `gh workflow run "OS image" --ref pkg/30b-launch-hints -f checks_only=true`, awaited with one blocking `gh run watch <id> --exit-status`. The check build (`check_build=build`) is started by the orchestrator after the review.
- The full report text, with the hint format's new part, what ran and what it printed, what is not verified (a real Lunar start: the owner's "try this") and a "try this" note. If your file tool refuses `REPORT.md`, leave the text in `reviews/30b-launch-hints/PROGRESS.md` and say so.

## Out of scope

A session-wide SDL setting (the OS lead decided against it: SDL picks XWayland on purpose where fifo-v1 is missing, and the failure is this game's). A labwc with fifo-v1 (on the next image's list; when it lands, the hint's `environment` line can go). Environment values for registry apps. Anything under `mod/`.

## Already decided

- The allowlist starts with `SDL_` names only. A wider list is a reviewed change to one pattern.
- Hints stay image-only and root-owned; nothing in his home folder can add or change one.
- Package 30's known limits stand; don't reopen them.

## If unsure

Refuse the hint file and log why, rather than start a program with a setting nobody reviewed.

## Rules

- `AGENTS.md` applies. Worktree `~/AresOS-30b-launch-hints`, branch `pkg/30b-launch-hints`. Never merge, never push to `main`, never `--no-verify`. Don't change `.gitattributes` or any bound file.
- Never open a window in the owner's session, never send input to it, never start his programs. No sudo, nothing installed.
- The repo is public: no personal data.
- Don't touch other worktrees or `~/AresOS` itself.
- Commit as you go. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
