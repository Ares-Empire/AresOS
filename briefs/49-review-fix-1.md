# 49, review fix 1: say what the rig wrote, how it can hang, and keep the decisive frame

`reviews/49-memory-cuts/REVIEW-1.md` (Codex `gpt-6-astra` `high`, head `b670d57b`) checked the study against its data.
- **Confirmed:**
  - the scope: only `reviews/49-memory-cuts/` and the brief;
  - the numbers, sampled against `TABLES.md`;
  - the recommendation: keep the current settings, arena cap 2 only as a follow-up, no FerriteCore, no forced action on cover;
  - nothing private in the public record;
  - a size that is reasonable for the evidence.
- **Found:** three things to settle.

**Builder:** Codex `gpt-6.1-sol` `high`. This is report text and a small data extract, with no product code and no client test, so `high` is enough. **Review:** a fresh Codex `gpt-6-astra` `high` context that checks only this fix.

## Lead decisions (2026-11-18)

1. **Finding 1, the `/sys/fs/cgroup` writes, needs no rig change.**
   - **Why:** `briefs/49-memory-cuts.md` (step 1) asked for `memory.reclaim` and `cgroup.freeze` on the rig's own game scope. The review prompt's blanket "nothing under `/sys`" was the lead's wording and was too broad.
   - **What to add:** a short section in `REPORT.md`, "Writes outside the repo", listing exactly what the rig wrote:
     - which files;
     - in which runs;
     - how the scope check makes sure each write reaches only the scope this run created, under the user's delegated cgroup, without root;
     - that nothing else under `/sys`, `/proc` or `/etc` was written.
2. **Finding 2, the blocking FIFO open, is documented and not fixed in the committed rig.**
   - **Why:** the rig stays exactly as it was when it produced the data.
   - **What to add:** a section in `REPORT.md`, "Before the rig is reused", that describes the hang. If `vinput.py` dies, `measure.sh:149`'s FIFO open can block, the cleanup trap never runs and the client lock stays held. It also gives the required fix: a bounded input helper for every command, a failure on reader or compositor loss, and an exit through the owned-process cleanup.
   - **For the follow-up:** any follow-up that reruns the rig (the arena-cap repeat in Open questions) must apply this fix first. Say so in Open questions.
3. **Finding 3, the decisive frame: keep its evidence.**
   - **The flight outlier:** if the raw frame logs are still in the ignored `.work/`, add to `verification/` a small excerpt with the two timestamps behind the 19.948 ms flight frame and the comparison window around it. Do the same for the first-creation startup-tail difference the JUDGMENT-CALL names. Include only frame timestamps and run identifiers, never paths, host or user details.
   - **If they are gone:** say so in "Not verified".
   - **The tool:** extend `rig/analyze.py` only if that is the cleanest way to produce the excerpt. Running it must not change any existing table.
4. **Optional size cleanup from the review.**
   - **Duplicates:** keep one copy of each byte-identical FerriteCore screenshot and point the report's links at it.
   - **The interrupted Nether control:** drop its screenshot, but keep its failure data.

## Rules

- **What may change:** only files under `reviews/49-memory-cuts/` and this brief. No product code.
- **Nothing that touches the game:** no client test, no game and no Gradle are needed, and none of the rig's scripts run.
- **Checks:**
  - run `bash -n` on any changed shell script;
  - parse any changed JSON;
  - run the repo's whitespace check;
  - run the privacy script the hosted "Repo privacy" job runs.
- **Commits:** end each commit with the trailer line `Codex-Model: gpt-6.1-sol high`.
- **Where it goes:** commit, push to `pkg/49-memory-cuts` and comment on PR #107 with what changed per finding. Never merge, never push to main, never `--no-verify`.
