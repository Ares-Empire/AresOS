# 14d: The five flagged values are file hashes; exact ignore entries, then continue

Follow-up on branch `pkg/14-owner-tools` (PR #13, draft). Read "14c privacy stop" in `reviews/14-owner-tools/REPORT.md`. Briefs 14, 14b and 14c still apply, with the change below.

## Integrator decision

The gate was right to stop, and right not to exempt anything itself.

**What I checked:**
- I recomputed all five values from commit `54337da`. Each one is the SHA-256 of the file it is listed against, so none of them is a credential.
- The generic rule fires only because the file names contain `key`, `auth` or `api` and sit right before a hash.
- Package 11 handled the same case the same way: one exact fingerprint in `.gitleaksignore`, plus a forward format fix.

So:
1. **I added the five exact fingerprints** (commit, file, rule, line) to `.gitleaksignore`, in the same commit as this brief.
   - `.gitleaks.toml`, the rules and the privacy workflow are unchanged.
   - Locally, the pinned gitleaks 8.21.2 over the full history now reports 0 findings.
   - Don't add or change any ignore entry or allowlist yourself. If a new finding appears, stop and report it.
2. **Forward fix: hash before path.**
   - Every manifest you write from now on that pairs files with hashes puts the hash before the path, for example a list of `{"sha256": "...", "path": "..."}` objects. That way a file name never sits right before a hash.
   - Rewrite the current `host-walk/result.json` (and any other manifest in this package with the old shape) in the new format.
   - Update its readers and verifiers.
   - The old lines stay in history, covered by the five entries. Lines removed by a later commit aren't scanned.
3. **Scan before every push.** Before each push, run the pinned, checksum-verified gitleaks 8.21.2 locally over the full history, with the same flags as CI plus `--redact`. Push only on 0 findings, and record that it was clean in the ledger.
4. **The other two privacy steps** (private commit emails, personal terms) were skipped when gitleaks failed. They must pass in the next CI privacy run before any VM dispatch.

## Then

Continue exactly where 14c stopped:
- the native suite
- the ledger checks
- the fresh probe gate, then the qualification

Everything else in briefs 14, 14b and 14c stands. The final package review covers this `.gitleaksignore` change too. Mark PR #13 ready for review when acceptance is met. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
