# Reviews and councils

There are two kinds of review. Both use a **fresh reviewer that isn't the builder**: a fresh Codex context while Codex is available, otherwise a fresh Claude agent (owner, 2026-11-11). Independence comes from the fresh context, not from a different vendor. Nobody reviews their own work.

A Claude reviewer runs on Opus by default, and on Fable 5.2 only for high-stakes reviews (`CLAUDE.md`, "Reviews"). It gets the same prompt as below, a read-only instruction (never modify files), and writes its answer to the same `REVIEW-N.md`.

A review covers exactly the commit it looked at. Anything pushed later isn't covered.

`$REVIEW_MODEL` and `COUNCIL_MODEL` are the models picked for this review (`CLAUDE.md`, "Codex models").

## Package review (every package)

After Codex opens a PR, one fresh reviewer checks it. It runs in a read-only sandbox, and `-o` saves its answer:

```bash
codex exec -m "$REVIEW_MODEL" -c model_reasoning_effort="high" -s read-only \
  -C /c/Users/pab/AresOS-NN-slug -o /c/Users/pab/AresOS-NN-slug/reviews/NN-slug/REVIEW.md \
  "You review PR #N of AresOS. Read AGENTS.md, briefs/NN-slug.md and reviews/NN-slug/REPORT.md, then the diff (git diff main...HEAD). Find what is wrong, missing compared to the brief, or will break in the game. Look hardest for things that fail silently: tests pass, but the game behaves wrong. For each finding give severity (blocking / should-fix / nit), where it is, why it matters, and the fix. End with one line: SAFE or CHANGES-NEEDED."
```

- Blocking findings become a short follow-up brief, and Codex fixes them on the same branch.
- The reviewer then checks only those fixes plus anything they touched. It doesn't start a fresh hunt.
- Claude commits `REVIEW.md` on the branch (the reviewer can't, since it's read-only), so it reaches `main` with the package.

## Tools for Claude (control layer)

Every tool package (Mail, Chrome and the ones to come) uses the owner's bar from 2026-11-11
(`docs/control/PLAN.md`): safe the way a good MCP or CLI is, not "nothing could ever go wrong". "If it takes long
to get it right, it takes long", but a round needs findings worth a round.

1. A brief, then one build.
2. Two fresh reviewers at the same time, both read-only: the package review above, and a security review. The
   security review's prompt states the bar:
   - every send, delete, payment and unsubscribe the tool recognises asks, with the exact content shown and bound,
     and Claude can't answer or replay the question;
   - inputs are checked, and each tool has the least access it needs;
   - the app passwords and sign-in data the tool service holds never reach Claude;
   - untrusted content is marked.
   It sorts each finding as **fix** or **known limit**:
   - **fix:** real harm, such as an action without its question, credentials, installs or system changes, data
     loss, or breaking the owner's normal use;
   - **known limit:** a hostile page or message making a step look ordinary, with low harm.
3. One fix round for the "fix" findings. The same reviewers then check only those fixes, and CI passes twice.
4. The tool's design keeps a list of its known limits: what it is, the harm, and why it is accepted.
5. More care where the tool acts as the system's operator: updates and rollback, disks, software installs,
   credentials and system settings, and the final review before something reaches his laptop. Use a Fable reviewer
   or an extra angle there.

## Councils (every now and again)

A council is several fresh Codex reviewers. Each has a different role, and they review the **plan or design** (not a diff) without seeing each other's answers. A chair then merges their findings into one ranked list. It's the only review allowed to say "the plan itself is wrong".

### When to convene one

- Before a new phase starts (for example, before the phase 2 OS work).
- Before anything hard to undo: installing onto a drive, boot setup, or the world/save format that builds will depend on.
- When Codex reports a `PLAN-GAP`, or the same kind of bug shows up twice.
- Every few packages as a health check, or whenever the owner asks.

### Roles (pick 3–5 that fit the question)

- **Player feel:** is it fun and fast to use as a desktop every day? Where will it get annoying?
- **OS reliability:** what happens on a crash, a freeze, no internet, a Minecraft update or a failed boot? Can the owner always get out?
- **Safety:** can anything touch the Windows drive, lose the world save, or lock the owner out?
- **Performance and battery:** shaders, frame rate in the background, RAM with apps open, heat.
- **Architecture:** is the split between mod and OS clean? Will a Minecraft version bump or a second theme (Brawl Stars) be cheap, or a rewrite?

### How Claude runs one

1. Write `reviews/councils/<date>-<topic>/QUESTION.md`: what is being reviewed, which files to read, and what decision depends on it.
2. Launch one `codex exec` per role, in parallel (`COUNCIL_MODEL`, xhigh, read-only, `-o <folder>/<role>.md`), with this prompt:
   > You are the <ROLE> member of an AresOS design council. Read QUESTION.md in <folder> and the files it lists. Review independently; you will not see the other members' answers. Report only real gaps, most severe first. For each: the gap in one line, a concrete scenario where it breaks, the impact, the fix, and the test or check that would catch it. Do not edit any files.
3. When all members are done, launch the chair (`COUNCIL_MODEL`, xhigh, `-o <folder>/VERDICT.md`):
   > You chair an AresOS design council. Read QUESTION.md and every member file in <folder>. Merge duplicates, drop anything without a concrete scenario, settle disagreements by the evidence rather than by counting votes, and rank by severity. End with one line: GAPS-FOUND (n) or CLEAN.
4. Bring the verdict to the owner in plain language.

### What findings bind

Blocking findings get fixed in the plan before anything is built, unless the owner explicitly overrules them. Claude never quietly drops one.
