# Security review 8 of brief 19 (Mail): round 15 and a whole-path sweep

Reviewer: Codex `gpt-6-astra`, xhigh, read-only, fresh context, 2026-11-08. Reviewed `9e4b1375` (round diff `6a2e0e36..9e4b1375` plus a sweep of the whole approval path). Run by the lead; saved by the lead.

Reviewed `9e4b1375`. One blocking finding remains.

1. **Blocking — The boundary verifier accepts settings that permit promptless CLI submission.** In [boundary.py:55](/Users/pab/AresOS-19-mail/control/aresos_control/boundary.py:55), start with the supplied managed settings and set:

   - `sandbox.excludedCommands` to `["aresos *"]`
   - `permissions.allow` to `["Bash(aresos *)"]`

   Keep every mandatory MCP ask rule and the unchanged managed MCP file. `Boundary.require()` accepts this configuration.

   Claude Code documents that excluded commands run outside the sandbox even with `allowUnsandboxedCommands: false`; their execution follows ordinary permission rules, which the Bash grant satisfies. The MCP ask rules therefore never intercept `aresos mail send --input <prepared approval>`. [Claude Code settings reference](https://code.claude.com/docs/en/settings-reference#sandbox-allowunsandboxedcommands)

   I reproduced acceptance and followed the actual CLI → Proxy → Engine → Mail path with storage and SMTP substituted in memory: exit status **0**, operation **done**, **one SMTP DATA call**, no prompt mechanism involved. This establishes an installation-check bypass; I did not establish an escape from the unchanged supplied configuration.

   Reject command exclusions and validate the complete confinement-critical configuration. The verifier also accepts `sandbox.filesystem.disabled: true`, despite requiring a filesystem denial.

**Should-fix:**

- **Strengthen the filesystem installation proof.** [boundary.py:37](/Users/pab/AresOS-19-mail/control/aresos_control/boundary.py:37) checks the opened file, but never its ancestors. `O_NOFOLLOW` protects only the final component: symlinked or writable parent directories can let the checked inode differ from the file subsequently loaded by Claude. Require protected ancestors and pin production paths; fixture-path overrides currently reach production through service configuration. I found no request-level injection into that protected configuration. Hard links are accepted, but a hard link alone does not grant permission to modify a root-owned file.

- **A small hostile email can crash the service.** [codec.py:20](/Users/pab/AresOS-19-mail/control/aresos_control/mail/codec.py:20) invokes Python’s recursive MIME parser without a depth bound. Reproduction: an ordinary outer message containing 1,200 nested `Content-Type: message/rfc822` entities, approximately **38.5 KB**, followed by a plain-text body. Calling `mail_read` on it raised `RecursionError` through `Engine.request`; the daemon’s exception handler also excludes that exception. Repeated reads reproduce the crash. Bound incoming MIME parsing and return a controlled refusal. This is an availability finding from the broader sweep, separate from the repaired JSON decoder.

- **The assistant can deliberately exhaust storage and force recovery.** Repeated free `mail_compose` calls with 200,000-character bodies each persist another composition, even though the response is `result_too_large`. Three calls retained approximately **1.2 MB** across event and current-state JSON. There is no aggregate quota. With SQLite capacity constrained in memory, the same request reached `journal_incomplete`; after restoring capacity and restarting, the store required owner restore confirmation. This is a **medium-severity persistent denial of service across the control layer**, not an approval bypass. Keep fail-closed behavior; add storage admission limits and reject oversized composition results before persistence.

The other closure checks passed:

- The folder-rename reproduction now returns `partial`, preserves all three messages, and creates a persistent warning under the owner-approved policy.
- Overflow, invalid `saved` payloads, and JSON depth/size/UTF-8 cases are refused before journal damage. I found no malformed-input shortcut to the journal latch.
- Preparations and submissions, including replay and onboarding probes, check the boundary. Admin access remains restricted; repair performs only qualified local stages without resending.

**Verification:** 43 selected Python tests passed using in-memory storage/blob substitutes where needed; generated artifacts matched. Native Claude Code, Linux confinement, real providers, and containers were not exercised. No files were edited.

CHANGES-NEEDED
