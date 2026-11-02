# 14zz: Never undercount a job with bad timestamps; cosign-installer key checksums are public; probe 30, qualification 19

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zy still apply, with the changes below.

## Integrator decisions on the 14zy STOPs

Cancelling was the right call. The counter fix is accepted: the real-kernel proof showed 0/1 for the old getter and 1/1 for the separate client.

### 1. Accounting: fail safe, never clamp

`job_minutes` must never turn an inconsistent interval into one minute.

- **Normal case:** if the job's `started_at` ≤ `completed_at` and every step lies inside that interval, use it as now.
- **Otherwise,** charge the widest ordered span the response supports. It runs from the earliest start that isn't after completion (the job's `started_at` or the first step's `started_at`) to the latest completion (the job's or the last step's).
- **If no ordered span exists** (missing or unordered steps), charge that dispatch's full bound: probe 72, qualification 160. Never charge less.
- **Record the rule used for each job.** Base the test on the retained probe 29 responses, not invented ones: that job must come out at 26 minutes, which matches the organization's +26.
- **Recompute the whole package history** with the new rule. Report every job whose charge changes, and restore a trusted `consumed_minutes`.
- **Safety net, before every dispatch:** compare the package ledger's increase since the previous dispatch with the organization usage increase over the same time. STOP if the ledger increase is more than 5 minutes lower.

### 2. Privacy: a third approved artifact class

I checked the four full-log findings myself.

- **What they are:** two lines, each appearing in both the step log and the combined log. Each reads `RELEASE_COSIGN_PUB_KEY_SHA='<64 hex>'`, in the script that `sigstore/cosign-installer@398d4b0eeef1380460a10c8013a76f728fb906ac` echoes.
- **Where the values come from:** both appear verbatim in that pinned commit's public `action.yml`. They are published checksums of cosign's public key, not secrets.
- **The rule:** approve exactly that line shape, in that pinned action's step output (step log and combined log), when the value appears verbatim in the pinned commit's `action.yml`. Fetch the file by commit and record its SHA-256.
- Any other full-log finding still STOPs. Don't add a gitleaks ignore or rule for it.

### 3. Allowances and the round

- `dispatch_caps`: probe 30 → **32**, owner-tools 19 → **21**. The minute cap of 2750 stays.
- Run the local checks, then one push through the privacy hook, then **probe 30 and qualification 19 on that same head**, then STOP and report as in 14zy.
- If qualification 19 stops on console typing, add the serial-run plan for the stages still left, and don't build it until I answer.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
