# 11g: Handle stock Bazzite's own updater, keep failure evidence, then finish A and B

Follow-up on branch `pkg/11-two-disk-rehearsal` (draft PR #11). Read the "11f" section of `reviews/11-two-disk-rehearsal/REPORT.md`. Briefs 11c–11f still apply, except the changes below.

## What stopped 11f, and why it matters beyond CI

On the first installed stock boot, stock's updater (`uupd.timer` / `uupd.service`) staged a newer upstream Bazzite (`44.20261023`, digest `sha256:d0e5…cdd4`) before the guide's pin step. `pin-stock.sh` correctly refused. The ISO's kickstart points stock's origin at the mutable `:stable` tag, so this will happen on the real laptop too, probably earlier.

It's worse on hardware. The guide has the owner reboot into Windows (§5) **before** pinning. That reboot finalizes any staged update, so stock would boot a newer, untested deployment and the guide's digest check would stop the install. The recipe needs a deterministic answer, not a timing bet.

## Integrator decision: pause stock's updater first, discard a staged update, refuse a booted one

1. **Pause stock's OS updaters at the first stock login, before §5.**
   - From the pinned image, list every unit that can stage an OS deployment (at least `uupd.timer`/`uupd.service`). Reuse the existing updater audit's view of stock; don't guess names.
   - Add an owner block, also a script under `os/release/`, that stops them, disables their timers persistently, and waits until no updater or bootc/rpm-ostree transaction is active. It must be idempotent.
   - The guide runs it at the very first `ares-recovery` login, before the §5 Windows comparison.
   - Write one plain line in INSTALL saying how to re-enable stock updates if the owner ever goes back to stock for good (Part B's promoted stock).
2. **`pin-stock.sh` runs that pause again first, then handles three states:**
   - **Booted digest equals the recorded ISO digest, nothing staged:** pin, as today.
   - **Booted digest equals the ISO digest, plus exactly one staged deployment:** the staged one must reference `ghcr.io/ublue-os/bazzite-nvidia-open`. Print and record its reference, digest, checksum and version, then discard it (`rpm-ostree cleanup -p` or the bootc equivalent you verify). Re-read status and require one booted deployment, nothing staged, and the booted checksum unchanged. Then pin.
   - **Anything else** (booted digest differs from the ISO digest, more than one staged, or a staged deployment that isn't upstream Bazzite): stop. Print a plain message pointing to EMERGENCY/help. Don't roll back or repin automatically.
3. **Unchanged:**
   - the frozen ISO, base and release digests
   - signature policy
   - the "no staged deployment" requirement at the moment of pinning and before `bootc switch`
   - every later identity check

   No image rebuild. If the new step would require one, or conflicts with the AresOS updater policy checks after the switch, stop and report a PLAN-GAP.
4. **Regressions:**
   - Replay 11f's real `rpm-ostree status` (staged `d0e5…`) through the new logic with mocked subprocesses. It must discard exactly that staged deployment and then pin the unchanged booted one.
   - Each of these must stop without pinning:
     - booted digest differs from the ISO
     - two staged deployments
     - a non-Bazzite staged reference
     - the booted checksum changing after cleanup
   - The pause script must be idempotent (running it twice is harmless).
5. **CI follows the guide:** the full run executes the pause at the first stock login, then the new pin step. Record whether a staged update actually appeared and was discarded. If none appeared, say so; the replay still covers the path.

## Failure path: keep the write counter

11f's failure close host-killed QEMU before the final `query-blockstats`, so one session lacks its zero-write record.

- On every failure path, read the protected disk's QMP blockstats **before** terminating QEMU and save them as that session's final record, marked as failure-path.
- If QMP doesn't answer, record that explicitly. The verifier keeps that session unqualified, as now.
- Add a regression that simulates a failing guest command and checks that the counter record exists.

Don't change the offline audit, and don't relabel 11f's missing record. It stays unqualified.

## Budget

Same ledger and start. The **cap becomes 750 rounded minutes and 4 full runs in total**. 11f used about 243 minutes and 2 full runs. That leaves room for the probe, one complete full run, and one more attempt.

The org had used 248 of its 2,000 October minutes on 2026-10-24 (integrator-reported), and it resets on 1 November. Update the guard constants and the budget regression.

## Then

1. Update the zero-cost stage walk-through for the new first-login and pin steps, before any dispatch. Stop on a foreseeable conflict.
2. Run a fresh probe on the new commit.
3. Run one complete full run: **Part A** in both orders, then **Part B**, as 11c/11f say.

All stop rules hold.

## Acceptance

11c's acceptance, plus an "11g" REPORT section with:
- the updater inventory and the pause/pin logic
- the replay and negative regressions
- whether CI saw and discarded a staged update
- the failure-path counter regression
- per-stage events, the gate → evidence table and the minute ledger

INSTALL and EMERGENCY must match the new steps in plain language.

Push (fast-forward only). Mark PR #11 ready for review if acceptance is met. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
