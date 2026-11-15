# 35 review fixes 2: the last three ways his commands can be lost

Follow-up on the same branch (`pkg/35-slash-names`, PR #56). The fix check of `ce8b45dc` is `reviews/35-slash-names/REVIEW-2.md` (gpt-6-astra, high): CHANGES-NEEDED. Findings 2 to 6 of the first review are closed; three FIX and two SHOULD remain. All five are accepted.

Read `REVIEW-2.md`, the section "Review fixes 1" of `reviews/35-slash-names/REPORT.md`, and `names/OwnedNodes.java`, its mixin and `item/AppCommands.java` before changing anything.

**Builder:** a Claude agent (Opus 5.5), one step. **Review:** a fresh reviewer checks only these five, with this bar: it must be fixed if a command of his can be lost, taken over or opened by someone or something that is not him typing it, if another mod's or the game's command is changed, if his saved apps or names can be lost, or if the commands stop following his apps.

## Fixes

1. **All of `/aresos app` is host-only where it is parsed** (FIX 1). `execute as <host> run aresos app remove discord` from a command block or a function still removes his app, because `add`, `remove` and `list` are only checked when they run. Put the requirement on the `app` parent so it covers every branch, and keep the checks at execution. Tests: `execute as <host>` from the console for `add`, `remove` and `list`, asserting that membership, pins and his commands are unchanged.
2. **The merge hook steps aside only for its own parent** (FIX 2). `OwnedNodes.beforeAdd(parent, incoming)` finds a node of ours under `parent` but removes it from the parent recorded at installation, without checking that the two are the same. So a registration somewhere else (another mod hanging our `/open` node under its own namespace and registering there) removes his `/open` from the root. Step aside only when the intercepted parent is the recorded installation parent; anything else is not our business and is left alone. A test with the review's scenario: our node shared under another parent, a registration there, and `/open` at the root still his and still working.
3. **The downgrade note is honest** (FIX 3). In the report's "What an older mod does with the schema-4 apps file": copying the schema-3 backup over `apps.json` rolls back everything since the move to schema 4 (apps added or removed, pins, My apps), not only names and absent marks. Say so, and say to keep the current file first (copy it aside). No conversion tool in this package.
4. **The permission probe is proven against the real function loader** (SHOULD 4). `AppCommands.allowed` lets through a source without a server that holds no permissions, which is what the game uses to decide whether a clicked command needs the "elevated permissions" question. Find in the game's code which source the function loader compiles with on this server (the permission set it really constructs, here and on a dedicated server at each allowed `function-permission-level`), write that down in the code comment and in the report, and replace the test's hand-picked constant by that real construction: a function and a macro function that contain an `/aresos app …` line must fail to compile, and nothing of his changes. If any real path can produce a serverless source without permissions, that is a finding of yours: narrow the exception until it can't, and say how. Correct the report's claim "exactly that probe" to what is shown.
5. **Old command trees are let go** (SHOULD 5). `OwnedNodes` keeps a record per node whose values hold the node itself and its parent, so the weak keys never clear and every `/reload` or world rejoin keeps another whole command tree alive. Drop the records of a dispatcher when it is replaced (or keep the values from holding their keys); a test that after a reload nothing of the old tree is recorded.

## Verification

- A test for each code fix that fails without it; say which checks are controls.
- `mod/dev/build.sh` once after the last code change, `mod/dev/client-test.sh` once (the client tests' own code does not change; it shows nothing else broke). If the laptop refuses with exit 75, use GitHub for the build and tests (`gh workflow run Mod --ref pkg/35-slash-names`, then one blocking `gh run watch <id> --exit-status`) and leave the client run to the orchestrator. Never `--force`. Put the tracked screenshots of other packages back afterwards (`git checkout -- reviews/`, and remove untracked renumbered pictures), as in round 1.
- The report gets a section "Review fixes 2": per finding what changed, what you ran and where, what it printed.

## Rules

- As in the first brief. Worktree `/var/home/ares/AresOS-35-slash-names`; push; never merge; never `--no-verify`. Stay inside `names/`, `item/AppCommands.java`, the mixin, their tests and the report.
- Never run `./gradlew` directly, never open a window in the real session.
- Commit after each fix. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
