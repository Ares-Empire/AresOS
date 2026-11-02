# 14zzf: A real STOP → export → reboot test for diagnostics; correct the report claim; no payload change, no dispatch

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zze still apply, with the changes below.

## Integrator decision on `reviews/14-owner-tools/REVIEW-2.md`

Findings 1, 2, 3 and 5 are CLOSED. Finding 4 is not closed: the implementation is there, but its test doesn't prove that diagnostics survive a reboot, and the REPORT claims the qualification covers it, which it doesn't.

I'm not adding a VM stage for this. The VM already proves the parts this path relies on: the checked export route (used for records) and `/var/lib/ares` persisting across reboots. What's missing is an honest test of this exact sequence.

1. **Replace the "reboot model" in `test_owner_export.py`** with a real sequence:
   - In a subprocess, use the real owner entry point to cause a controlled STOP. Map only the filesystem root prefix into a temporary root, the same mapping the records tests use; no other path override.
   - Prove that the diagnostic was written under the persistent `var/lib/ares/diagnostics`, not only under the `/run` equivalent.
   - **Reboot:** delete the whole `/run`-equivalent directory and any in-memory state, then start a fresh process.
   - Run the real `export` to a fixture stick, built from the manifest, and verify that the exported diagnostic's bytes equal the original's.
   - The test must fail on the pre-14zzc code, where diagnostics lived only in `/run`. Show that failure.
2. **Correct the REPORT claim.** The qualification does **not** exercise STOP → export → reboot. Say what proves each part: this local test for the sequence, and the VM for the export route and `/var` persistence.
3. **No payload change.** The payload fingerprint must stay `3e2c78ebedf7789b0616e7a4f21ad791d76784667344e76e97a1fbd95115a6fd`. If the new test exposes a payload bug, STOP and report it. Don't fix it in this round, because a payload change needs a new qualification.
4. **Local checks:** the affected modules with and without `-B`, and the pinned gitleaks. Commit, then push once through the privacy hook. **No dispatch.** Then stop with a short summary.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
