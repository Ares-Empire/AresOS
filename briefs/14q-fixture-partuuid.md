# 14q: The native loop fixture read an empty EFI GUID; fix the fixture, probe 9 and the qualification

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14p still apply, with the change below.

## Diagnosis (integrator, from the code; the run didn't export the values)

Probe 8 passed all 333 native tests. Then `owner.disk_record` refused with "Linux firmware entry does not uniquely map to target EFI". **The tool is right; the fixture is wrong:**
- `os/ci/owner_devices.py` gets the fixture's EFI GUID with `blkid --probe --output value --match-tag PARTUUID <loop>p1`.
- In low-level probe mode (`-p`), blkid reports the partition GUID as **`PART_ENTRY_UUID`**, not `PARTUUID`. So `guid` was empty, and the synthetic firmware line said `HD(1,GPT,,…)`.
- Meanwhile `disk_record` read the real GUID from `lsblk` and correctly found no matching entry.
- The local stand-ins supplied a non-empty GUID, so they couldn't see this.

If your evidence contradicts this, say so and stop. Don't guess another cause.

## Fix (fixture only; the owner tools stay unchanged)

1. Read the fixture's expected GUID independently of `lsblk`: `blkid -p -s PART_ENTRY_UUID -o value <loop>p1`. Cross-check it against the GPT entry that `sgdisk -i 1 <image>` reports ("Partition unique GUID", compared case-insensitively). Require a valid non-empty GUID before using it. An empty GUID or a mismatch is a STOP with both values shown.
2. Record the observed values before every assertion, in an evidence file that is written even on failure: the raw lsblk trees, the findmnt rows, the expected GUID and its source, the synthetic firmware line, and the GUID `disk_record` resolved. Then a stop explains itself next time.
3. Add a local unit test of the fixture's GUID parsing, using real low-level `blkid -p` output that contains `PART_ENTRY_UUID` and no `PARTUUID`. It must produce the GUID, and an empty result must stop.

## Budget (owner: use October's minutes now)

Fresh billing at your stop reported 190 free. One push (about 6), probe 9 (bound 42), the qualification (130) and closing privacy (12) total about 190. Set for package `14` only:
- `minute_cap`: **480**
- `dispatch_caps.probe`: **9**; `owner-tools` stays **2**
- reserve stays **0**

If the guard refuses because there are too few minutes, stop: the rest waits for November.

## Then

Commit your local probe 8 STOP report with the fix. Pinned local gitleaks, the replay and strict checks, then exactly **one** push. Fresh exact-head privacy, the ledger and billing. **Probe 9**; only if it passes, the **second qualification on the same head**. Any stop: report it, no rerun. No other push until the qualification finishes. When acceptance is met, put the reserve back to 150 in a final commit and mark PR #13 ready for review. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
