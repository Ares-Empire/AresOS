# 14zze: Bind host-walk sources to the bytes Git checks out; probe 34, qualification 21

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zzd still apply, with the changes below.

## Integrator decision on the probe 33 STOP

Your diagnosis is accepted. The host walk recorded a PowerShell test source as its LF blob, but `.gitattributes` makes the runner's checkout CRLF, so the runner's working-tree hash differed. I recomputed all 195 sources from the `dda72ed` blobs and they all match. It's purely an end-of-line binding bug.

1. **Record the bytes the runner will actually execute.** Replay Git's checkout filters with the repository's `.gitattributes` (for example, `git checkout-index` into a temporary directory with `core.autocrlf=false`) and record those bytes.
   - The CI check stays as it is: the working tree must equal the record.
   - Optionally, record the blob hash next to it, but never compare one against the other.
2. **Find every other source binding** that hashes repository files (the walk, the preparation and preflight records, the probe and qualification bindings) and apply the same rule. List them in the report.
3. **Regression:** a local test replays the checkout filter for every recorded source and requires a match. It must fail on the `dda72ed` record, and must cover at least one CRLF-declared file.
4. **Allowances:** probe 34 is the last probe allowed and qualification 21 the last qualification. The minute cap of 2750 fits: 2326 + 72 + 240 = 2638.
5. **Then:** the local checks as in 14zzd, one push through the privacy hook, then **probe 34 and qualification 21 on that same head**, then STOP and report.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
