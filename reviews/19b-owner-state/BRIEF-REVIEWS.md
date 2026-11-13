# Reviews of brief 19b

Reviewer: Codex `gpt-6.1-sol`, high, read-only, fresh context, 2026-11-09, on the brief draft against the Mail branch at `8724c0b6`. Run by the lead; saved by the lead.

## Review 1

- **Blocking — Stage 1, lines 48–55:** “From that log alone” is impossible. Servers cannot observe local completion commits, acknowledgements, expiry, restore, caller publication or scan completion; IMAP commands also lack operation IDs. Define independent scenario inputs, clock, fault/check outcomes and a committed-record decoder. Extend fixtures with request correlation, selected account/folder, exact message identities, role history, attempted/accepted commands and delivered/lost replies; include HTTPS unsubscribe. Keep fixture logs outside injected storage failures.

- **Blocking — Stage 3, lines 63–68:** Removing pending fallbacks lacks an explicit replacement when SQLite SELECT itself fails under persistent exhaustion. Round 26b identifies this; the independent journal currently omits generic free changes. Require a durable owner-state projection readable without SQLite or its disposable index, committed before effects, with bounded fallback reads tested during failed rollback and restart.

- **Blocking — Compatibility, lines 61–68, 78–79, 123:** “No committed record rewritten” needs a precise definition. Working rows already change during acknowledgement, restore and expiry. Preserve immutable historical records while allowing appended projections, resolutions and tombstones plus working-view updates. Specify legacy handling when context is irretrievable, without warning on every finished old operation. Test rollback, archive, expiry and restart so resolved warnings neither disappear early nor resurrect.

- **Blocking — Warning lifecycle, lines 64–68:** “Owner has seen it” is not an acknowledgement protocol, and a later clean check must not silently erase an unacknowledged detected warning. Define separate check, warning, acknowledgement and action-resolution states, including new warning occurrences after acknowledgement. Preserve unresolved approved work, repair identity/quiet periods and the prohibition on automatic remote replay.

- **Should-fix — Coverage, lines 51–56, 75–82, 95–96:** The warning list does not operationalize all fourteen round-26b rows. Require a pre-build coverage matrix including admission/holds, export publication/rollback/manifests, restore generation, expiry/cancellation, qualification/protected roles, refusal families and ordinary read disclosures. A final report table alone cannot establish coverage.

- **Should-fix — Stage gates/tests, lines 45–58, 75–81:** Known gaps could become blanket skips, and equality could pass with empty expectations or one healthy view masking another. Require assertion-specific expected failures that reject unexpected passes; independent checks of every public view and all pages; positive warning triggers before status reads; and mutations breaking R1, R2 and R3. Stage 2 must prove context committed before commands and failed commitment prevents effects.

- **Should-fix — Remote-action wording, lines 35–41, 59, 118–123:** “Every remote action” includes reads, while “without a new remote action” forbids the live checks explicitly required elsewhere. Distinguish mutations, warning-producing evidence checks and passive disclosures. Preserve passive rejection/offline behavior; keep context internal so approval inputs and questions remain unchanged.

- **Should-fix — Concurrent 18d, lines 86–87:** Both packages touch definitions, proxy/hooks, fixtures and tests; preserving generated descriptions verbatim is insufficient. Define integration responsibility in either merge order, regenerate from combined definitions/instructions, and review/test the combined head. Explicitly preserve decision 24’s relaxed boundary and managed asking guarantees.

CHANGES-NEEDED
## Review 2

- **Oracle inputs — FIXED.** Stage 1 adds independent scenario inputs, clock/fault outcomes, correlated server logs, HTTPS unsubscribe and a committed-record decoder; logs sit outside injected failures.
- **SQLite-read failure — FIXED.** Stage 3 requires a durable projection readable without SQLite or its index, with bounded fallback tests during failed rollback and restart.
- **Compatibility/history — FIXED.** Immutable history is distinguished from mutable working views; appended resolutions/tombstones, legacy handling and lifecycle regression tests are explicit.
- **Warning lifecycle — FIXED.** Checks, occurrences, acknowledgements and action resolutions are separate; clean checks cannot erase unacknowledged warnings, and unresolved approved work remains visible.
- **Coverage — FIXED.** A committed pre-code matrix must cover all fourteen round-26b rows and round-27 inventory C.
- **Stage gates/tests — FIXED.** Assertion-specific expected failures reject unexpected passes; comparisons cover separate views/pages, positive triggers, breaking mutations and commitment before effects.
- **Remote-action wording — FIXED.** Mutations, evidence checks and passive disclosures are distinguished; approval inputs, questions and offline behavior remain protected.
- **Concurrent 18d — FIXED.** The second merger owns integration, regeneration, twice-run workflows and combined-head review; decision 24 remains protected.

**New — should-fix: occurrence identity is underspecified (draft lines 67–69).** “Each detection” creates a new occurrence, but pending/catalogue reads repeatedly check the same evidence. Literally implemented, unchanged duplicate Sent copies generate endless warnings, invalidate pagination and immediately warn again after acknowledgement. Current `mail/adapter.py:719` suppresses unchanged counts. Define when observations belong to the same occurrence and what constitutes a new detection after acknowledgement. Require repeated reads and paging to preserve occurrence IDs, and test unchanged evidence versus changed evidence and clean-then-recurrence.

CHANGES-NEEDED
## Review 3

The occurrence-identity finding is fixed. The revised lifecycle gives unchanged evidence a stable occurrence ID across reads, pages and restarts, preserves acknowledgement, and defines new occurrences for changed evidence or recurrence after a committed clean result.

This preserves `mail/adapter.py:719`’s suppression of unchanged duplicate counts while strengthening identity to the matching-copy set, so replacing a copy without changing the count is distinguishable.

The required lifecycle tests cover repeated reads/paging, acknowledgement silence, changed evidence, clean-then-recurrence, and persistence through rollback, archive, expiry, restore and restart. No new contradiction or regression found within this scope. This was a source review; no tests were run.

READY