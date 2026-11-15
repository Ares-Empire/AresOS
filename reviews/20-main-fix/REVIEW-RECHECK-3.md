# Package re-check 3: step 5 (5bc7e4aa to bf0bf6e4, Claude Opus, 2026-11-15)

**Verdict: SAFE (no FIX open)**

F3 is fixed: `prepare` implements exactly the four cases you scoped. The new tests fail on the old code, and every new or re-pointed probe fails when applied, each for its stated reason. Nothing in the step 5 diff undoes my earlier findings.

### Your four questions
1. **`prepare` implements the four cases** (`control/chrome/qualify.py:210-251`).
   - **How "worse" is decided:** `compared()` (`:210-216`) looks at every core and adapter group of the held entry. A group is worse when the held entry has it true and this run has it false, and better the other way round. Both entries pass `validate_record` first, so they have exactly the same groups and every value is a boolean; adapter-only differences count the same as core ones.
   - **On main:** any difference raises, with the old message (`:243`).
   - **Off main, worse or mixed:** the run raises, the error names the worse groups, and no candidate is written (`:245`).
   - **Off main, better:** one `::warning::` naming only the improved groups; the held entry stays and nothing is added for that pair (`:247`). Equal entries take the old skip.
   - **A better pull request can't reach main:** the candidate keeps the held entry and is published only to the local bare remote, and its attestation is on the pull-request ref, which main's policy refuses. Main calls `prepare` with `on_main=True` (`:420`), and that keyword defaults to `True` (strict).
2. **Tests and probes:**
   - With step 4's `qualify.py` put back into a copy of `bf0bf6e4`, the worse, better and mixed tests fail (5 failures). The identical and on-main tests pass there, as they should, because that behaviour didn't change.
   - All 8 F3 probes (the re-pointed `mainfix-f1-conflicting-repeat-relaxed` plus the 7 new `mainfix-f3-*`, `better-repeat-overwrites-held` included) and the 4 new `mainfix-sec-*` probes fail when applied, each in the test and for the reason it names. Two earlier `mainfix-sec-*` probes still fail too (14 run in all).
   - Examples: `adapter-regression-ignored` fails in the `adapters.github` subtest; `better-repeat-kept-on-main` fails in the `[better]` subtest of the on-main test; `publisher-baseline-case-unsigned-bytes` fails with "gh refused for another reason than qualification_rollback".
3. **First-record path: yes, safe to leave as a note.** On main the plan already skips every pair in the shipped baseline, so no duplicate can reach that path. Off main, a duplicate needs the head pair in main's `qualification.json` while there's no data branch. The baseline only changes through the PR that copies the data branch's record into it, so that requires someone to delete the data branch. Even then `validate_record` refuses with "Repeated qualification key", nothing is written, and only that pull request goes red. It can't pass wrongly.
4. **The rest of the step 5 diff:** `expected_refusal` accepts only gh's named failure, or `Refused` with the exact code (`qualification_rollback`); any other `Refused` propagates. The "non-append-only shipped baseline" case now uses the genuine bytes, so only the append-only check can refuse it; before, it could pass because the signature check failed.

### NOTE
None new. My earlier (d) (fork pull requests) and the expired link still in commit `14e81352` stand as before.

### Checked
- `test_qualification`, `test_publisher`, `test_qualification_service` and `test_build` all pass in a copy of `bf0bf6e4` in my scratch directory.
- **Runs (via `gh`):**
  - Qualification 43687610978: pull_request on `bf0bf6e4`, 34/34 green.
  - Control Chrome 43687610984: on attempt 2, 27 jobs green and `latency (plain)` re-running. As you said, the failed attempt isn't a finding.
- **Scope:** nothing under `os/`, `mod/` or `docs/design`, and no STATE.md, HANDOFF.md, CONTROL.md, extension, `aresos_control` or service unit changes. No personal data.
- The review worktree is still clean at `bf0bf6e4`.
