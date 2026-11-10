# 19b stage 2, fixes round 1

**Against** three parallel reviews of stage 2 at `31eeb030` (diff `9eb193f2..31eeb030`), all CHANGES-NEEDED:
[`REVIEW-S2-ORACLE.md`](../reviews/19b-owner-state/REVIEW-S2-ORACLE.md) (Claude, oracle independence),
[`REVIEW-S2.md`](../reviews/19b-owner-state/REVIEW-S2.md) (sol high, stage) and
[`REVIEW-S2-ASTRA.md`](../reviews/19b-owner-state/REVIEW-S2-ASTRA.md) (astra xhigh, storage faults and owner
state). Read all three in full: they carry the reproductions and probe outputs. Read `briefs/19b-owner-state.md`,
`briefs/19b-on-mail.md` (the note wins), and every `briefs/19b-s*.md` first; D1–D3, L1, the field-audit rule,
structure S, the stage-2 start rules and the fold rules all hold (R2 stays exact and folded; no journal growth).
The lead's rule: the oracle reviewer's findings come first. Below, duplicates are merged; each item names its
sources. Fix every item. Do not start stage 3.

## 1. The alteration test needs teeth (ORACLE B5, S5) — do this first

As built, every planted fault is caught only by structural consistency checks between copies of the same value
(`changed-decoded-projection` and similar), which real production can't trigger, and an oracle with a whole
validator removed (`script_differences`, `stage_claims`, `completion_errors`, `payload_claims`, `filing_claims`,
the transition gate) still passes. Rebuild it so it proves what it claims:

- **Coherent lies.** For each alteration, also write the lie coherently into every copy production would write:
  the event, the projection, the matching compact fence operation, and every later `committed_before`,
  `created_before`, `check_sources` and `commit_observations` copy in the server log. For coherent variants, count
  only non-structural differences as caught. Add nested key deletion (`context`, `stages.<name>`, `approval`, ...).
- **Real production plants.** Replace the fixture-row plants with real production regressions run through the
  unmodified `Driver` and `Driver.compare`, one or more per field kind, each required to produce a difference.
  The oracle reviewer's P1–P7 (and its probes under the scratchpad path it names) are ready-made starting points.
- **Validator-specific broken oracles.** Each broken-oracle control disables exactly one validator (the list
  above, plus `local.errors`) and the alteration test must then fail. A control that replaces the whole
  comparison doesn't count.
- **Field audit (S5).** Add the production rows the driver copies into the server log (`committed_before` row
  content, `created_before`, LIST `check_sources`) to the field-audit table and to the perturbation set, each with
  its validation.
- Report per validator: alterations that change the expected set, how many each validator's own check catches,
  and that disabling it makes the test fail.

## 2. Oracle findings (the comparison accepts a broken rule)

- **2a. A send's approved local stages are not required effects** (ORACLE B1). Derive the send's full effect plan
  from the approval plus the independently observed Sent policy (Sent copy as an exact APPEND to the observed
  Sent role or a correlated read-only match; the answered flag when approved); completion and `stage_claims`
  require every planned stage. Regression: P1.
- **2b. No script authority for Sent-copy APPEND, draft APPEND and the answered STORE** (ORACLE B2). Derive their
  destination and flags from the script plus the pre-command LIST (Sent role, Drafts role, exactly
  `+FLAGS.SILENT (\Answered)` on the approved reference); check command and context; `stage_claims` uses the same
  derived command. Also compare the Sent-copy APPEND bytes with the DATA wire bytes (or its Bcc variant)
  (ORACLE, outside angle). Regressions: P2, P6, P7.
- **2c. Permanent delete complete without the `\Deleted` STORE; `marked:` justifies itself** (ORACLE B3). Require
  per target an accepted, delivered `UID STORE uid +FLAGS.SILENT (\Deleted)` before its `UID EXPUNGE uid`;
  validate `marked:*` against it. Make the sweep fixture's EXPUNGE honour `\Deleted`. Regression: P4.
- **2d. Free-change recovery ends on "some delivered effect"; the omitted-branch check switches off under any
  fault** (ORACLE B4) **and a second APPEND under one intent is accepted** (ASTRA #3). Require the complete
  scripted effect plan (every reference × every requested flag branch; the exact folder for create/rename/delete)
  accepted and delivered before the completion commit, and enforce multiplicity per scripted attempt and intent
  whatever the terminal state. When a fault interrupts the batch, keep the obligation instead of skipping the
  check. Regressions: both `flag_branch` variants; a planted APPEND retry after a failed result write through
  persistent exhaustion, cleanup pairs, restart and space restored; a separately scripted new attempt stays
  distinguishable.
- **2e. A LIST that isn't this check's result closes a filing or rename check** (SOL #1: an ordinary
  `mail_accounts` LIST via `check_sources`; ASTRA #2: a healthy-roles LIST without the rename destination).
  Record actual check correlation in the recorder; close a check only on the evidence that completes that check
  (destination present where needed, scan complete where it scans). Add both to the corpus with later
  acknowledgement, repeated reads, expiry and archive.
- **2f. R2 ignores the receiver's actual recipient** (SOL #2). Validate each attempted recipient against the
  approval and the committed context independently; test a wrong and an extra recipient before any completion
  commit.
- **2g. The rename message count comes from production** (ORACLE S2 = SOL #4). Expected count = identities in the
  source folder in the RENAME server event; compare committed and public counts. Regression: P5 and the coherent
  `message_count` lie.
- **2h. `unknown`/`partial` reasons are production's choice from a whitelist** (ORACLE S1). Derive the expected
  state and reason family from RCPT/DATA replies, local-stage results and the fault trace; replace a wrong reason
  in the retained projection. Regression: P3.
- **2i. A `context_version: 1` row without `context` passes R2** (ORACLE S3). Use the legacy decoder only for rows
  without `context_version` from the frozen legacy fixture; for version-1 rows require `context` and report its
  absence as R2.
- **2j. A runtime event labelled `fixture` skips reason validation** (ORACLE S4). Exempt only seed events and
  events inside a scripted `fixture_input` interval; any other post-seed `fixture` event is a lifecycle
  difference.
- **2k. `LOCAL_FLAG` has no independent model and no sweep coverage** (ASTRA #4; ORACLE outside angle). Model it
  (reference, revision, requested value, prior committed context; completion by the matching committed item
  change); regressions for missing context (must fail) and the valid atomic change (must pass); add the flow to
  the full owner-state sweep.
- **2l. The AST import test** (ORACLE, imports): also ban `builtins.__import__`/`getattr`-style dynamic imports,
  and resolve relative imports so a same-named top-level module can't pass.

## 3. Production regression: RENAME must not read message bodies (SOL #3 = ASTRA #1)

Stage 2's RENAME context preparation fetches and parses every message, so an ordinary folder rename now refuses on
a healthy disk (`mail_too_large`, `mime_limit`) and costs two FETCHes and full-body processing per message. That
changes what the tool does. Build the identity context from the existing UID/UIDVALIDITY enumeration (bounded
header-only reads only if a Message-ID is genuinely needed), with no body-size or MIME limits. Tests: healthy-disk
RENAME succeeds with an oversized, a deeply nested and an excessive-part message, beside the context-commit
failure/crash tests; RENAME's server reads are no more than before stage 2, or each new read is named with its R2
reason. The fold's zero journal growth must hold (rerun the STORAGE-S2 table).

## 4. Fixtures

- The sweep fixture's APPEND writes two copies, so the clean `send` baseline always carries a duplicate-Sent
  warning (ORACLE, outside angle). Normal use must be quiet: make the clean baseline produce one Sent copy and no
  warning, and keep a separate, deliberate duplicate case if the inherited sweep needs one. Show the clean send,
  move and delete add no warning.

## Verification and report

- Local first; then the Linux capture once, the strict re-pin, and Control base, Control Mail (every job under 45
  minutes, aim about 35) and Control boundary each passing twice on the finished head.
- Do not run your own review; the package lead reruns the three reviewers on the fix diff.
- Add a "Stage 2, fixes round 1" section to `REPORT.md`: per item what changed and its test or plant; the new
  alteration-test figures per validator; the updated field-audit and resolution tables; the storage table; the
  ledger counts and size; the run count. Mark claims run, read or assumed. List every change to `warnings.py` and
  `paging.py` (none expected).

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
