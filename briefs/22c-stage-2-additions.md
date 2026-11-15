# 22c, stage 2: what changed since section E was written

Stage 2 is section E of `briefs/22c-ways-back-after-update.md` (the VM rehearsal). Stages 0, 1a, 1b and the follow-up "one word per meaning" are closed: `REVIEW-7.md` (gpt-6-astra high on `d32171ca`) says SAFE. What changed for E:

- **`forward`** (`briefs/22c-forward-command.md`): every step of E that returned to an installed AresOS with `update` uses `forward` now: step 3's forward again after `previous`, step 4's return from stock, step 5, and step 6's return after the boot menu. Walk `update` only where it installs a release. Add one step where `update` refuses on the older AresOS and names `forward` (nothing changed), then `forward`. `forward` leaves `unwalked_commands` when the walk types it.
- **The tools install from the stick** (version 2 to 3, the bootstrap block of `docs/INSTALL.md`), as the decision after stage 1b's step 1 says. The folder block stays unrouted (package 22d).
- **The guides changed** in review fixes 3 and 4 (`check` before `previous` after any boot-menu choice; a return that changes nothing completes with `PASS check`). The walk types what the guides say, in their order.
- **The full model gate:** `rehearsal_guard.model_gate` stops a dispatch unless a checks-only run on the same head passed the full model. Dispatch that first.
- **The budget ledger** allows 30 checks-only runs and three VM dispatches remain of four; 1200 minutes in all. Report before using the fourth.
- **The record step:** this package's rehearsal is the next one after package 27's, so its record step moves the waiting rows into `rebound`, empties the list, and writes `os/manifest/ci/22c/source-bindings.json` (`rebind.py record` was package 27's one-time step: give it a form that takes the package key, or write 22c's own, and say which).
- **The host walk** gets E's route beside the probe's (`reviews/22c-ways-back-after-update/walk-host.py`).

**Model:** a Claude agent on Fable 5.2 (rehearsal harness work cost package 27 many rounds; updates, rollback and the boot order are the high-stakes class), in steps: (1) the harness route, its local walk and host walk, the record step, the checks-only run with the full model, then the first dispatch and its watch, then stop and report; (2) fixes and further dispatches with a fresh builder if needed. Watch runs with `--interval 60`.
