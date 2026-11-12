# 19b: Owner-visible state read from the committed record (R1–R3)

**Goal:** what the owner must learn (pending items, warnings, notices, refusals and their reasons) can never be
lost or stuck because of a full disk, a failing write or a crash. Today each such case is closed where it was found
(Mail review rounds 21 to 27). After this package it holds by construction: every owner-visible fact is computed when
it is read, from the committed record plus live checks, and a test oracle that doesn't take its expectations from
production code checks it after every injected fault. The base and Mail get it now; Chrome (brief 20) inherits it.
Empire board brief 259.

The owner approved this as its own package after Mail and before Chrome (board #126, 2026-11-09: "yea makes sense").

## Background (read first)

This branch starts from `main` **after Mail (PR #9) has merged**. Read on `main`:

- `reviews/19-mail/REPORT.md`: the round-21 and round-25 disk bars, round 26's three class tables (A bounded
  responses, B no refusal outlives its cause, C unfinished intents warn after restart), **round 26b's inventory and
  scope note** (the starting point of this brief: fourteen rows of owner-visible facts and their sources), and round
  27's rule and inventory C.
- `reviews/19-mail/SECURITY-REVIEW-16.md` to the last one: what kept being found, and why.
- `docs/design/CONTROL.md` sections 3 to 5 (operations, approvals, the journal, Mail) and 7 (decision 24), and rule
  4.8 (untrusted marking).
- The code: `control/aresos_control/{storage.py, engine.py, recovery.py, results.py, space.py, retention.py,
  archive.py, exports.py, proxy.py, hooks.py}` and `mail/{adapter.py, filing.py, onboarding.py, roles.py}`; the
  sweep in `control/mail_tests/storage_faults.py` and `test_review23_sweep.py`, and the test servers
  (`smtp_fixture.py`, `imap_guard_fixture.py`, the test app's receiver).

In short: rounds 21 to 27 found, one at a time, warnings and refusals kept beside the committed record, in memory or
a cache, so a failed write or a restart lost them or kept them. Round 26 closed three classes at central points and
round 27 added a rule for checks. Still missing: the general rule, a durable source for owner state that doesn't
depend on the working database being readable, and a test oracle that doesn't take its expected warnings from the
production code it checks (today `Scenario.recover` gets them from production `unfinished()`, notice rows and memory).

## Words used here

- **Mutation:** a remote action that changes something: SMTP delivery, APPEND, MOVE, COPY, STORE of flags, EXPUNGE,
  CREATE, DELETE, RENAME, an HTTPS or mail unsubscribe, an onboarding probe, the test app's send and delete.
- **Evidence check:** a read-only remote read whose result can produce an owner warning: Sent searches, LIST and role
  lookups, location scans.
- **Passive disclosure:** what any response envelope shows from committed records without contacting a server.
- **Immutable history:** the independent journal's entries and committed operation, intent and stage history. Never
  rewritten. The independent journal is never trimmed; the owner's existing archive step may move finished operation
  history out under its existing rules (hash-valid export first), as today.
- **Working view:** the SQLite working rows and the disposable index. They may be updated as today.

## The rules (lead decisions, Mail rounds 26 and 27)

- **R1.** Every fact the owner must learn is computed when it is read, from committed records plus live checks
  (current free space, evidence checks). Memory may add detail, such as observation pages or a warning's exact
  wording, but is never the only copy of anything the owner must learn.
- **R2.** Before every mutation, enough is committed to derive the owner's warning if the outcome is never recorded:
  account, message identities, source, destination, the roles at preparation, the recipients. If that commit fails,
  the mutation doesn't happen. An intent left `started` is itself a warning until it is resolved.
- **R3.** A refusal is a function of current state and is recomputed on every call. Only the transaction latch
  persists (a journal write that may have started), and recovery clears it.
- **Round 27's rule stays:** a check that can produce an owner warning stays open until its result, clean or warning,
  is committed.
- **Unchanged:** what each tool asks and does, its approval input, its `question` text and binding, the untrusted
  marking, passive rejection and offline behaviour, repair identity and quiet periods, and the ban on any automatic
  remote replay. The new context is internal and never enters an approval input or question.

## Warning lifecycle (define it in code and in the report)

Four separate things, each committed:

- **Check:** open, clean or warning (round 27).
- **Warning occurrence:** an id, the operation, the check kind and an **evidence fingerprint** (for duplicates the
  set of matching Sent copies; for filing the destination and its role; for scans the locations found). Reading the
  same evidence again matches the existing occurrence and keeps its id, across repeated reads, pages and restarts.
  A new occurrence starts only when the fingerprint changes (another copy appears, a role changes), or when the
  warning condition comes back after a committed clean result. A later clean check never erases an unacknowledged
  occurrence.
- **Acknowledgement:** per occurrence, through the existing acknowledgement action as built (who may call it doesn't
  change in this package).
- **Action resolution:** the operation's own end (done, failed, expired, cancelled, settled), independent of its
  warnings. Unresolved approved work stays visible until resolved.

An occurrence leaves the owner-visible set only when acknowledged. It neither disappears early nor comes back after
acknowledgement, through rollback, archive, expiry, restore or restart.

## What to build, in three stages

Each stage ends with a sol high review of that stage before the next begins (see "Model"). Commit each stage
separately, so the PR reads in three parts.

### Stage 1: coverage matrix and oracle

1. **Coverage matrix first,** committed as `reviews/19b-owner-state/COVERAGE.md` before any code. Take every one of
   round 26b's fourteen rows and every row of round 27's inventory C. For each owner-visible fact give: its source
   today, its source under R1 to R3, its check states, its warning occurrences, how it is acknowledged and resolved,
   and the oracle cases that cover it. It must include admission and holds, export publication, rollback and
   manifests, restore generation, expiry and cancellation, qualification and protected roles, every refusal family,
   and ordinary read disclosures. Stage 1's review checks the matrix against the code.
2. **The oracle.** It lives in test code and never imports production modules to compute expectations. Its inputs:
   - **the scenario's own script:** each call it made, in order, with arguments, a test clock, the faults it injected
     and where, and which replies were delivered or lost;
   - **the test servers' logs, extended:** a correlation id per scenario call, the selected account and folder, exact
     message identities, the folder roles over time, every command attempted and accepted, and every reply delivered
     or lost. Include the HTTPS unsubscribe receiver. These logs are written outside the injected storage faults;
   - **a committed-record decoder in test code,** written from the documented on-disk format, so the oracle can tell
     which local commits happened (completion, acknowledgement, expiry, restore, export publication, scan
     completion), which the servers can't see.

   From these it derives the owner-visible set the scenario must show, by operation id and occurrence.
3. **The comparison.**
   - It checks every public view separately, and every page of each: `control_pending`, each app's notice catalogue,
     `aresos log`, and the passive envelope on ordinary responses. One healthy view never masks another.
   - It requires equality in every sweep mode: single fault, persistent exhaustion, cleanup pairs, crash and restart,
     and space restored without restart. Nothing missing; nothing extra in normal use.
   - It asserts each scenario's positive warning triggers before any status or evidence read that could recreate
     them.
   - It covers all 22 sweep flows plus draft APPEND, folder create and delete, the onboarding probes and unsubscribe.
4. **Known gaps:** each gap the oracle finds today is one assertion-specific expected failure, naming the matrix row
   and the stage that closes it. An unexpected pass fails the run, so a gap can't hide a later regression. No blanket
   skips. The list is empty when the package ends.

### Stage 2: action context (R2)

- Commit the context of R2 before every mutation, for Mail and the test app. Generic free changes get their own
  intent identity and arguments, and onboarding probe identities are committed before the probe.
- Tests show, per mutation kind: the context is committed before the command reaches the server (server log order
  against the commit), and a failed commit prevents the command entirely.
- Old records without the new fields stay readable. An old operation that is unfinished and lacks context shows a
  conservative "not yet checked" notice. A finished old operation shows nothing new.

### Stage 3: one read path and a durable owner-state source (R1, R3)

- **One read path** derives every owner-visible fact from committed records plus live checks. The engine, proxy,
  socket, CLI, MCP and hooks all use it.
- **A durable owner-state projection** that this path can read without SQLite or its index. Committed before
  effects; append-only, with resolutions, acknowledgements and tombstones added as new entries. The independent
  journal or a file beside it, whichever is cleaner; it must include generic free changes, which the independent
  journal omits today. When a SQLite read itself fails (persistent exhaustion, failed rollback), the read path falls
  back to this projection, bounded and paged as in round 26.
- **Remove what this makes redundant:** in-memory pending fallbacks and deferred notices as sole carriers, stored
  refusals used as reasons to refuse, and startup snapshots used to decide what is unfinished. Memory may keep
  wording and detail.
- **Archive, restore and expiry keep working.** Open checks and unacknowledged occurrences can't be archived away; a
  restore re-derives them from the projection.

The read path, the projection, the intent context fields, the acknowledgement record and the oracle's harness live
in the shared layer, with Mail and the test app as the first users, so Chrome inherits them.

## Tests (containers on GitHub's Linux runners, no model, no real account)

- The oracle comparison, in every sweep mode and every flow, with the known-gap list empty at the end.
- Tests of the oracle itself:
  - its expectation code imports no production module (checked by a test);
  - it derives the expected set from a recorded script and server log;
  - each rule has a breaking mutation that the oracle catches: R1 (a warning kept only in memory), R2 (context
    committed after the command), R3 (a cached refusal), and round 27 (a check closed without a committed result). It
    also catches review 19's case and round 21's lost-duplicates case.
- The SQLite-read fallback: persistent exhaustion with a failed rollback, then restart, shows every owner-visible
  fact from the projection.
- The lifecycle:
  - unchanged evidence read many times, and across every page, keeps one occurrence id, and stays quiet after its
    acknowledgement;
  - changed evidence after an acknowledgement is a new occurrence, and so is clean followed by recurrence;
  - a clean check after a warning keeps the unacknowledged occurrence;
  - rollback, archive, expiry, restore and restart neither drop an unacknowledged occurrence nor bring back an
    acknowledged one.
- Old records: a store written by the merged Mail code opens, shows the right warnings (none for finished old
  operations), and accepts new operations.
- Brief 18's base suite and Mail's suite pass. When a test of a removed path is replaced, a table in the report maps
  it to the oracle case that covers it now.
- Normal use is quiet: a clean send, move and delete add no warning.

## Running alongside 18d

Brief 18d (slim base) may run at the same time and touches definitions, generated descriptions and instructions,
the proxy and hooks, fixtures and tests. Whichever of the two merges second must:
- merge `main` into its branch;
- regenerate all generated files from the combined definitions and instructions;
- rerun every Control workflow twice;
- have its reviews cover the combined head.

Decision 24's relaxed boundary and managed ask rules stay exactly as 18d leaves them.

## Out of scope

- Compacting the permanent journal into a checkpoint (the owner may ask for it later).
- New tool actions, or any change to what a tool asks or does, its approval binding or its `question` text.
- Who may acknowledge a warning (stays as built).
- Brief 20 (Chrome), and anything under `os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`,
  `HANDOFF.md`, `README.md`, and the design and plan files.

## Acceptance

- R1 to R3, round 27's rule and the warning lifecycle hold throughout the base and Mail. Every coverage matrix row
  has its oracle cases.
- The oracle runs in CI on every sweep mode, imports no production code for expectations, and its known-gap list is
  empty.
- Storage: report bytes per operation before and after (send, move, delete, a free change, a 25 MiB send), including
  the permanent journal and the projection, and show that finished operations and acknowledged warnings still
  archive out.
- Each Control workflow passes twice on the final head, every Mail job within its 45-minute limit.
- No secrets, real addresses, account names or provider names.

## Report (`reviews/19b-owner-state/REPORT.md`)

Include:
- what was built and removed, per stage;
- the final coverage matrix;
- the oracle's inputs and its imports;
- the known gaps it found and how each closed;
- the lifecycle as built;
- the projection's format and its fallback reads;
- the removed-test mapping;
- the storage figures;
- **PLAN-GAP**s and **JUDGMENT-CALL**s;
- what isn't done and why.

Mark each claim **run** (workflow run ID and log line), **read** (source and version) or **assumed**.

## Already decided

The disk bars of Mail rounds 21 and 25; R1 to R3; round 27's rule; decision 24 and section 7; brief 18's limits; the
`question` field, approval binding and untrusted marking as built.

## If unsure

Take the option that keeps every warning the owner must see derivable after any single fault and restart, without a
new mutation, and say so in the report.

## Stop rules

- Stop and report if a stage needs immutable history rewritten, or a change to what a tool asks or does.
- Stop if the oracle can't be built without importing production code for its expectations.
- Stop and report the figures if storage per operation in the permanent journal or projection grows by more than
  about 1 KB; the lead takes that to the owner.
- Keep it to about 25 workflow runs.

## Owner decides

- Nothing else in this package.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/19b-owner-state`, from `main` after Mail's merge. Commit in small steps,
  push this branch, open a draft PR against `main` with `gh pr create --draft`. Never merge, never push to `main`,
  never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:**
- Building: `gpt-6.1-sol`, xhigh.
- After each stage: a fresh `gpt-6.1-sol` high review.
- At the end: a `gpt-6-astra` xhigh security review of the whole package, against the disk bars, R1 to R3 and the
  lifecycle.

Sol does bulk work well at a third of astra's cost. Astra has found every one of Mail's recovery gaps, so it does the
final check.
