# Workflow: how a change gets built

This is the same shape as nametbd's Codex-era workflow, scaled down: Claude plans and integrates, Codex builds, and fresh Codex contexts review. Roles and owner decisions are in `CLAUDE.md`. Codex's rules are in `AGENTS.md`.

## The loop

Work one package at a time. Run up to about three at once only when they touch different files.

1. **Plan (Claude).** Pick the next small package from the README phases and write `briefs/NN-slug.md` (template below). A package is one sitting for Codex, roughly one feature you can see in the game.
2. **Check the brief (Claude).** Read it against itself with two questions:
   - Does anything it asks for contradict anything it forbids?
   - Can what it hands Codex actually produce the result it promises?

   For risky or foundational packages, run a council on the brief first (`docs/REVIEW.md`).
3. **Launch (Claude).** Commit the brief to `main`, create the worktree, and start Codex in the background (`run_in_background`, so the harness reports when it exits):
   ```bash
   git -C /c/Users/pab/AresOS worktree add -b pkg/NN-slug ../AresOS-NN-slug main
   cd /c/Users/pab/AresOS-NN-slug && codex exec -m "$BUILD_MODEL" -c model_reasoning_effort="xhigh" \
     -s danger-full-access --json -o ../AresOS-NN-slug.last.md \
     "Read AGENTS.md and briefs/NN-slug.md, then execute the brief fully. Push the branch and open a PR. Do not merge." \
     > ../AresOS-NN-slug.log 2>&1
   ```
   `$BUILD_MODEL` and the other model names are the current picks in `CLAUDE.md`.
4. **Review (fresh Codex).** A reviewer that didn't write the code checks the PR against the brief. See "Package review" in `docs/REVIEW.md`.
5. **Integrate (Claude).** This is not a second full review. Claude:
   - confirms the PR head is the commit that was reviewed
   - reruns the build and tests on it
   - reads the diff for scope creep
   - looks at the screenshots, and opens the dev client when it's visual

   Every `JUDGMENT-CALL` goes to the owner. Fixes go back to Codex as a short follow-up brief on the same branch, and the reviewer then checks only those fixes.
6. **Merge (Claude)** with `gh pr merge --squash`, once checks pass and the owner has answered any judgment calls. Remove the worktree, and update the README if the design moved.
7. **Owner test.** Anything that matters in the game gets a short "try this" note for the owner. Their feedback becomes the next brief.

## Brief template

```markdown
# NN: <title>

**Goal:** what the owner will see or do when this is done (one or two sentences).
**In scope:**
**Out of scope:**
**Acceptance:** concrete checks, including which tests and screenshots.
**Already decided:** design decisions and constraints Codex must follow.
**If unsure:** the safe default to take.
**Model:** current build model (see CLAUDE.md), xhigh.
```

## Branches and files

- `main` is always green. Package branches are `pkg/NN-slug`, with worktrees at `C:\Users\pab\AresOS-NN-slug`.
- `briefs/`: frozen briefs. A changed plan is a new brief, not an edit to one Codex already ran.
- `reviews/NN-slug/`: the Codex report, reviews and screenshots.
- `reviews/councils/<date>-<topic>/`: council question, member reports and the chair's verdict.
- `codex exec` logs stay outside the repo, next to the worktree.

## Budget

- ChatGPT Pro runs until 2026-11-21.
- Builds use the build model. The frontier model is for councils and hard design questions. Current names are in `CLAUDE.md`.
- On a rate limit, wait and resume. Never retry in a loop.
