# Security re-check 3: step 5 (5bc7e4aa to bf0bf6e4, Claude Fable, 2026-11-15)

**Verdict: SAFE (no FIX open)**

Scope: `git diff 5bc7e4aa..bf0bf6e4` in the review worktree (detached at `bf0bf6e4`, code `496018a5`). `control/aresos_control/` and both workflows are unchanged in this range; the changes are in `control/chrome/ci/attestation.py`, `control/chrome/qualify.py` and tests.

## (a) My NOTE on the named refusals — closed

`control/chrome/ci/attestation.py:42-58`: `expected_refusal` accepts exactly two outcomes, a `subprocess.CalledProcessError` whose stderr contains gh's named reason, or a `Refused` whose `code` equals the reason; a `Refused` with another code re-raises, any other exception propagates, and success is `AssertionError('accepted')`. `refused()` then asserts the held record is unchanged.

- Wrong failure accepted? The two matchers cannot cross: `Refused.code` values are identifiers (`qualification_rollback`, `qualification_invalid`, …) and never equal a gh sentence, and gh's stderr never contains `qualification_rollback`. A `Refused('qualification_invalid')` (malformed record) in a rollback case now fails the job instead of passing as a refusal. A gh failure for a different reason (timeout, TUF, missing binary) fails the case with gh's text.
- Intended failure missed? Rollback cases (`:230-243`): the real verifier passes, then `append_only` raises `Refused('qualification_rollback')` → matched. "Unsigned inserted entry" (`:258-259`): bytes change, so `verify` fails with gh's policy text → matched. "Non-append-only shipped baseline" (`:259`): the signed `original` bytes verify, then `append_only(baseline, current)` raises `qualification_rollback` → matched; before this change the case could have passed on a signature failure, now only the baseline check can refuse it. Run 43687610978's log shows all five cases refused for exactly these reasons, for the PR bundle and the retained fixture.

Probes `mainfix-sec-rollback-any-exception`, `-refusal-code-unchecked`, `-publisher-any-exception`, `-publisher-baseline-case-unsigned-bytes` cover the four relaxations.

## (b) F3 trust — holds

`qualify.py:210-253`: `prepare(..., on_main=True)` keeps the strict rule by default and the CLI passes the run's real `on_main` (`:423`), the same `GITHUB_REF == refs/heads/main` the publication guard uses. On main any conflicting repeat raises (`:243-244`), as before. Off main: `compared()` (`:210-216`) covers `core` and `adapters`; any group the held entry passes and the repeat fails raises (`:245-246`; mixed better/worse raises too, since `worse` is checked first), and a better-or-equal repeat only prints a warning and `continue`s, so the held entry is never replaced (`:247-248`). The candidate is `current + added` with `append_only(current, candidate)` enforced (`:252-253`).

What a PR run can influence: nothing main publishes or verifies. Off-main candidates are indented bytes, attested on `refs/pull/N/merge`, pushed only to `.work/publish-remote.git`; `publish` to origin and `notify` still require `on_main` (`:426-427`, `:410`), `--ref`/`--held-bundle` are still refused for origin (`:428-429`), and main's `publish` verifies the fresh bundle under main's policy and the held record via `verify_held` (main policy). Confirmed at `bf0bf6e4` by run 43687610978: 34/34, `pull_request`, main-only steps `skipped`, PR-mode publish `success`, "production main rejects a bundle attested on refs/pull/68/merge (expected SourceRepositoryRef to be refs/heads/main)" PASS, and `refs/heads/chrome-qualification` still absent on origin. Tests `test_off_main_a_worse_repeat_…`, `_a_mixed_repeat_…`, `_a_better_repeat_warns_keeps_the_held_entry_…`, `test_on_main_any_conflicting_repeat_raises` pass locally (75 tests OK) with eight `mainfix-f3-*` probes.

## (c) The first-record path without the repeat check — safe as a note

`qualify.py:411-414`: with no data branch on origin the candidate is `baseline['entries'] + entries` passed through `append_only`, whose `validate_record` raises `Refused('qualification_invalid', 'Repeated qualification key')` on any duplicate key. So a repeat on that path can never be merged, overwritten or relaxed; it fails closed before any attestation. It is reachable only when the shipped baseline is non-empty and the data branch is missing, i.e. after a deletion of the data branch, and today the baseline is `{"format":1,"entries":[]}`. On main the plan already excludes held (baseline) keys, so main would re-create the branch cleanly; off main with `requalify_head` a PR would fail visibly on the duplicate. No trust effect; worth a line in the handover so the failure is recognised if the branch is ever deleted.

### NOTE (optional)
- `qualify.py:248`: the `::warning::` goes to stdout; harmless for `prepare` (its output is the candidate file), but if `prepare` were ever piped like `plan`, the line would corrupt the stream. Printing it to stderr would remove that dependency.

## Checked
Read: the full diff of `control/chrome/qualify.py` and `control/chrome/ci/attestation.py`; the new `test_publisher.py` F3 tests and the `mutation-audit.py` probes; confirmed no change under `control/aresos_control/` or `.github/workflows/` in the range; shipped baseline `control/chrome/qualification.json`. Ran (no browser, writes only under `.work`): `PYTHONPATH=control:control/chrome_tests python3 -m unittest test_build test_publisher test_qualification test_qualification_service` → 75 tests OK. Read-only GitHub reads: run 43687610978 (34/34 success, head `bf0bf6e4`), the `delivery-attestation` log lines for the rollback, publisher and main-policy cases, the `qualification-publish` step conclusions, `git ls-remote` for the data branch. No CI run started, nothing edited, committed or pushed.
