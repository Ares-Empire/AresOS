# 35 review fixes 1: a name is ours only while it is what we put there

Follow-up to `briefs/35-slash-names.md` on the same branch (`pkg/35-slash-names`, PR #56). The review is `reviews/35-slash-names/REVIEW-1.md` (gpt-6.1-sol, high): CHANGES-NEEDED, one blocking, five should-fix, and the missing client verification. All are accepted. Read the review, the first brief, `reviews/35-slash-names/REPORT.md`, `docs/design/HUB.md` 2.7 and 4, and the code under `mod/src/main/java/dev/aresos/names/` and `item/AppCommands.java` before changing anything.

**Builder:** a Claude agent (Opus 5.5), because Codex's weekly allowance is nearly used. **Review:** a fresh reviewer checks only these fixes.

## Fixes

1. **Ownership by content, not by identity** (finding 1, blocking). Brigadier merges a later registration of the same name into the existing node. So before the mod removes, replaces or counts a node as its own, it checks that the node is still exactly what it installed (its own executor, its own requirement, no children it did not add). A node that has changed is foreign from then on: the mod leaves it alone, treats the name as reserved, and gives the app its next-best name by the rules. The same for `/open` and `/apps`. Tests: another command registered under an already installed app name, with children and another permission, then a refresh and a removal of the app (the foreign command and its children survive and keep their own permission); the same for `/open`; a dispatcher rebuild (`/reload`) and a rejoin (vanilla commands win again, the app names come back).
2. **`name` and `unname` are host-only where they are parsed** (finding 2): the same requirement as the other `/aresos app` branches, checked against the source that typed the command, not the entity `execute as` selects. Tests with a guest and with `execute as <host> run …` from another source.
3. **Clicks open by ID through AresOS's own command** (finding 3): the rows of `/apps` and of `/open`'s list call a command under `/aresos` that takes the stable ID (for example `/aresos app open <id>`), host-only like the rest. Typed `/open <name>` follows HUB.md 4.4 only: an ID gets no precedence over names. Tests: two programs with one display name where one's ID equals the query (both are listed); an ID that equals another app's saved name; a foreign `/open` that existed before (the rows still open the right app).
4. **Only what the system lists has commands** (finding 4): a program that the latest complete list no longer contains keeps its saved names and its place in My apps for its return, but has no slash command, is not offered by `/open` or its completion, and is not listed by `/apps` (or is listed as not installed; choose one and say so). While the helper is down or a list is incomplete, the last complete list stays in force. Tests for disappearing and returning.
5. **A one-letter name gets its number** (finding 5): `A` gives `a2`, as HUB.md 4.2's last rule says; `app2` only when no numbered form of a candidate is valid. Tests including taken numbers.
6. **A failed save doesn't freeze the commands** (finding 6): removals that are safe happen even when saving names failed, and the failed work stays pending and is tried again with a growing pause, without another change being needed. A test: fail, recover, no other edit.

Also correct the report: the apps file is at schema 4 since this package (say what an older mod does with it, as package 34's report does for schema 3), and package 36 must be told in the report's PLAN-GAP section.

## Verification

- Each fix has a test that fails without it.
- The owner may be playing: `mod/dev/build.sh` and `mod/dev/client-test.sh` refuse with exit 75 while his game runs. Do not wait for hours: for the build and the unit and server tests use GitHub while the laptop refuses: push the branch, then `~/.local/bin/gh workflow run Mod --ref pkg/35-slash-names`, find the run with `gh run list --workflow Mod --branch pkg/35-slash-names --limit 1`, and wait with one blocking `gh run watch <id> --exit-status`; read failures with `gh run view <id> --log-failed`. Say in the report which results come from GitHub.
- The client tests and the screenshots need the laptop. Try `mod/dev/client-test.sh` at the end; if it still refuses, say so in your last message and leave them to the orchestrator, who runs them when the laptop is free. Do not use `--force`.
- `reviews/35-slash-names/REPORT.md` gets a section "Review fixes 1": per finding what changed, what you ran and where, what it printed.

## Rules

- As in the first brief. Worktree `/var/home/ares/AresOS-35-slash-names`; push; never merge; never `--no-verify`. Stay inside `names/`, `item/AppCommands.java`, the files the first build touched, their tests and the report.
- Never run `./gradlew` directly, never open a window in the real session.
- Commit after each fix. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
