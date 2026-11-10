# 19b stage 2, fixes round 3 (the last for stage 2)

**Against** the scoped re-checks of fix round 2 (`3486bec8..e43ea57c`):
[`REVIEW-S2-3.md`](../reviews/19b-owner-state/REVIEW-S2-3.md) (sol: SAFE),
[`REVIEW-S2-ASTRA-3.md`](../reviews/19b-owner-state/REVIEW-S2-ASTRA-3.md) (astra: one should-fix) and
[`REVIEW-S2-ORACLE-3.md`](../reviews/19b-owner-state/REVIEW-S2-ORACLE-3.md) (Claude oracle: one blocking, one
should-fix, one nit). Read both non-SAFE reviews in full, plus `briefs/19b-owner-state.md`, `briefs/19b-on-mail.md`
(the note wins) and every `briefs/19b-s*.md`; all earlier rules hold. Fix only what is listed. Do not start stage 3.

## 1. Normal use must be quiet in every flow, by test (ORACLE-3, blocking)

Round 2 fixed the four fault-free flows N1 named, but three more point-0 groups still carry **oracle-side**
differences: `onboarding` (44 keys: the self-probe send's RCPT and internal Sent repair can't be linked to an
operation because the only scripted call is `mail_account_add`), `folder_review` (20 keys: the setup call's intent
removal, which happened before the run started, is called unjustified) and `testapp_delete` (1 key: no account is
read from the testapp reference's scope; the second fact there is a structural fence check, classify it). Fix each
in the oracle.

Then close the class: add a test that runs **every** flow's fault-free point-0 case and fails on any difference
that isn't a listed production gap. A listed production gap needs its own entry naming the production behaviour
and the closing stage (for example `settlement`'s one key, where public stages disagree with committed stages, if
that is production-side). Put every flow in the quiet contracts, not only the four from round 2. Re-pin, and list
every point-0 group that changed and why.

## 2. Filing result state under `filing_claims` (ORACLE-3, should-fix)

With `filing_claims` removed, a coherent change of a filing or rename result's `state` slips in move, copy and
rename (for rename, `partial` → `started` makes the oracle silently expect recovery). Make another validator catch
it, or document it beside the row-removal slip as caught only by `filing_claims`, with the control showing that.
Also fix the nit: `test_baseline_alone_cannot_satisfy_a_plant_assertion` compares a recording with itself and can't
fail; compare against an independent plant-free recording.

## 3. Mail arriving during a scan (ASTRA-3, should-fix)

A complete filing scan is rejected when unrelated mail arrives between the LIST snapshot and SELECT
(`effects.py:54`, `model.py:659`). Validate SEARCH against the independently recorded inventory at that SEARCH,
then require matching body evidence for every returned UID; LIST establishes the folder catalogue, not frozen
message contents. Add the arrival regression and keep the empty-FETCH, wrong-UID and missing-literal negatives.

## 4. Mail CI headroom

The `alterations (9)` job reached 40m05s / 39m26s against the 45-minute cap. Rebalance the alteration shards (by
measured cost, not count) so every Mail job is under about 35 minutes in both passes, without dropping cases or
raising the cap. Stage 3 will add work, so leave room.

## Verification and report

- Local first; then the Linux capture once, the strict re-pin, and Control base, Control Mail and Control boundary
  each passing twice on the finished head. Rerun the STORAGE-S2 table (zero growth).
- **Waiting on CI:** one blocking shell call per run (`gh run watch <id> --exit-status --interval 60`, or one loop
  over the named runs). Never poll run status one turn at a time.
- Do not run your own review; the package lead reruns the scoped re-checks.
- Add a "Stage 2, fixes round 3" section to `REPORT.md` (per item the change and its test; the point-0 table for
  every flow; the validator table; ledger counts and size; Mail job durations; run count). Mark claims run, read or
  assumed.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/19b-owner-state`. Commit in small steps and push this branch; draft PR
  #26 targets `pkg/19-mail`. Never merge, never push to `main` or `pkg/19-mail`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- No real accounts, addresses, personal names or mail-provider names; tests use synthetic accounts only.
- Never commit the full gap list; the committed ledger stays compact (format 3, under about 1 MB).
- No change to what any tool asks or does, its approval input, `question` text or binding.
- Never rewrite immutable history; stop and report if a fix would need it, or if journal growth per operation
  would exceed about 1 KB.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.
- Stop after this round. Do not start stage 3.
