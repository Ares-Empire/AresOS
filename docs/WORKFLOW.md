# Workflow: how a change gets built

Claude plans and integrates. Codex or Claude agents build, and an independent, fresh Codex context or Claude agent reviews. Roles and owner decisions are in `CLAUDE.md`. Codex's rules are in `AGENTS.md`.

## The loop

Work one package at a time. Run up to about three at once only when they touch different files.

1. **Plan (Claude).** Pick the next small package from the phases in `docs/design/DESIGN.md` and write `briefs/NN-slug.md` (template below). A package is one sitting for Codex, roughly one feature you can see in the game.
2. **Check the brief (Claude).** Read it against itself with two questions:
   - Does anything it asks for contradict anything it forbids?
   - Can what it hands Codex actually produce the result it promises?

   For risky or foundational packages, run a council on the brief first (`docs/REVIEW.md`).
3. **Launch (Claude).** Commit the brief to `main`, create the worktree, and start Codex as a `codex-job` in the background (`run_in_background`; `--wait` wakes Claude when the run ends):
   ```bash
   WT=~/AresOS-NN-slug
   git -C ~/AresOS worktree add -b pkg/NN-slug "$WT" main &&
   codex-job start aresos-bNN-build -C "$WT" -m "$BUILD_MODEL" --effort xhigh -s danger-full-access --wait \
     --prompt "Read AGENTS.md and briefs/NN-slug.md, then execute the brief fully. Push the branch and open a PR. Do not merge."
   ```
   `$BUILD_MODEL` is the model picked for this package (`CLAUDE.md`, "Codex models"). Steering, stopping and fix rounds (`codex-job continue`): `~/aresync/TOOLS.md` → codex-job. On the AresOS laptop, use the `codex exec` fallback there until codex-job's Linux test run has passed.
4. **Review (fresh reviewer).** An independent Codex context or Claude agent checks the PR against the brief. See "Package review" in `docs/REVIEW.md`.
5. **Integrate (Claude).** This is not a second full review. Claude:
   - confirms the PR head is the commit that was reviewed
   - reruns the build and tests on it
   - reads the diff for scope creep
   - looks at the screenshots, and opens the dev client when it's visual

   Every `JUDGMENT-CALL` goes to the owner. Fixes go back to Codex as a short follow-up brief on the same branch, and the reviewer then checks only those fixes.
6. **Merge (Claude)** with `gh pr merge --squash`, once checks pass and the owner has answered any judgment calls. Remove the worktree, and update `docs/design/DESIGN.md` if the design moved (and the README's status if what works changed).
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

- `main` is always green. Package branches are `pkg/NN-slug`, with worktrees at `~/AresOS-NN-slug` on the AresOS laptop.
- `briefs/`: frozen briefs. A changed plan is a new brief, not an edit to one Codex already ran.
- `reviews/NN-slug/`: the Codex report, reviews and screenshots.
- `reviews/councils/<date>-<topic>/`: council question, member reports and the chair's verdict.
- Codex job records stay outside the repo (`codex-job status`, `logs`, `report`); fallback `codex exec` logs sit next to the worktree.

## On the AresOS laptop

- Use `mod/dev/build.sh` and `mod/dev/client-test.sh` for mod checks. Run only the affected OS test modules locally, one at a time, and use hosted checks for the full suite. Follow the laptop rules in `AGENTS.md`.
- Coordinate shared Codex and Claude usage with `mac-capacity`.
- On a rate limit, wait and resume. Never retry in a loop.
