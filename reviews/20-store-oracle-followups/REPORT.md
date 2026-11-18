# Build part 1 — brief 302, steps 1 and 2

**Done:** Established the local baseline and compact sample; implemented narrow
first-fence latch recovery, the request barrier, precise later refusals and restart
advice. Added independent raw journal phase/cleanup and request-order expectations.
Details and commands: [PROGRESS.md](PROGRESS.md), “Build part 1 (steps 1 and 2)”.

**Verified:** Baseline 134 base tests and 11 sweep units. Implementation: 148 base,
18 Mail, final oracle 127, raw/barrier 3 and sweep units 13 passed. Sweep coverage:
154 view runs and 77 retry/restart variants (41 cleanup pairs). Barrier-removal
mutation failed all six zero-SMTP-DATA assertions. Compact sample: 104 runs,
153 closed keys, 8 changed, 0 new; all clean traces identical to baseline.

**Not verified:** Full matrix, alterations, re-pin/proof, installed/root/channel
behaviour and actual owner-service recovery. No human game check applies.

**JUDGMENT-CALL:** No new product decision; follows board #352. Technical trace
placement is reversible and changes no journal/schema format.

**PLAN-GAP:** Export-local scratch setup, moved onboarding point, adjacent old
latch assertions, and ignored SQLite read-close fault ordering are recorded in
PROGRESS with their handling. The hosted onboarding point-count difference remains
for the later capture; no pin was changed.

**Open questions / left:** Step 3 item 2; step 4 item 3; step 5 mutations; step 6
re-pin and full proof; then final reviews. Stop here. PR remains a draft.

Draft PR: [#111](https://github.com/Ares-Empire/AresOS/pull/111). Commits:
`2de6da86` (step 1), `b64eb8f4` (step 2), followed by the closing documentation
commit. Observed implementation CI is queued; see PROGRESS for run IDs.
