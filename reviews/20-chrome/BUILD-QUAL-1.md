# Qualification implementation reviews

**Read/run:** independent, read-only sol high and astra xhigh reviews, requested by brief20. Reviewers used only this worktree and browser-free tests; neither touched a browser or profile. Initial reviewed implementation: 374974bc. Follow-up: d7ca02c6; anonymous-delivery addition: 5104513d.

| Finding | Resolution / evidence |
|---|---|
| Stored older held history blocks a newer shipped baseline forever | `Qualification.record()` retains the longer comparable trusted prefix; divergent histories still refuse. `test_image_upgrade_reconciles_older_held_history_and_can_fetch_again`. |
| Older stable pass hides newer beta failure | Every applicable failure stays active until a higher patch passes later in immutable publication history. Both beta/stable order counterexamples have strict regressions. |
| Hidden plan artifact excluded by upload action | Visible `qualification-plan.json`; workflow contract test. |
| Current driver hashes an archived build differently | `runtime_identity()` executes the archived build's own hasher; independently tested with a different shipped algorithm. |
| Stale passing result after interruption/cleanup failure | Owned observer watches the real harness without modifying it; completion includes pair identity, outcome and result/matrix digests. Generic failure or interruption creates no marker. Pair generation fails closed. |
| Whole-suite failure masks otherwise healthy groups | Observer recognises only the existing harness's final aggregate assertion, after all matrices and cleanup. Completed selective failure keeps per-group booleans; process failure remains failure. Node subprocess tests preserve exit0, logical1, generic1 and interrupted137. |
| New verifier prerequisite skips schedule/manual jobs | Attestation fixture runs on every non-PR event; publisher requires its success. Workflow contract tests include the schedule/manual condition. |
| `tee` can mask verifier failure | Explicit `set -euo pipefail` in attestation verification step. |
| Qualification lacks group12 evidence | Pair refuses every passing switch unless actual `groups[12]` is true. No 18d stand-in; core integration still required. |
| Installed service cannot reach HTTPS; supported gh missing | H1/H2 integration in QUALIFICATION-REPORT.md. Owned runtime now fetches public bundles anonymously and passes them to gh; no personal login is needed. Actual installed unit remains untested and unchanged. |

**Run:** follow-up sol review reported no new blocking owned-file finding and 45 Python +5 targeted Node tests passing. Follow-up astra review reported no additional owned-code finding after completion observer/daily-event fixes; its existing core network/verifier/group12 handoffs remain. Final anonymous-delivery runner evidence and any follow-up finding are recorded in QUALIFICATION-REPORT.md.

These reviews do not certify the integrated Chrome package or real laptop delivery.

**Read — final focused security review:** astra confirmed the serialized-bundle finding closed: actual UTF-8 bytes are capped before temporary-file creation and admission includes the verifier-cache reserve. No additional concrete issue was found. This focused review did not independently rerun CI.
