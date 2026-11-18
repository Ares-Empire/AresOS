# 47: client-test and the NVIDIA card's power cycling

Board #267. On 2026-11-14 at 05:49, during a `mod/dev/client-test.sh` run (package 36's worktree), the laptop's NVIDIA driver broke. Before that the RTX 4060 had gone into D3cold and back to D0 dozens of times. Afterwards: an `NVRM` GcxSupport error every 5 s, VA space allocation failing, and the HDMI monitor not detected, until a reboot.

The card runs with fine-grained runtime D3 (`/proc/driver/nvidia/gpus/*/power`: "Runtime D3 status: Enabled (fine-grained)"; `/sys/bus/pci/devices/0000:01:00.0/power/control` is `auto`). It suspends whenever nothing uses it. Each `client-test.sh` run probes the GPUs (`--gpu auto`: the RTX 4060 by PRIME render offload, then Intel, then software) and then starts the game, and each of those wakes the card. A day of package work makes many such cycles.

**Builder:** Codex `gpt-6.1-sol`, `xhigh`: an investigation against logs and a small script change. **Review:** a fresh Codex context, `gpt-6-astra`, `high`.

## Find out

1. From the journal (`journalctl -k` and `--list-boots` for the boot of 2026-11-14; read-only), the sequence before 05:49: how many D3cold/D0 cycles, how they line up with client-test's probes and runs (the scripts' own logs and the systemd user scopes' start/stop times), and the first error line. Say what the logs show and what they don't.
2. How many wake-ups one `client-test.sh` run causes today (probes plus the run), measured on the laptop by sampling `power/runtime_status` and `runtime_suspended_time`/`runtime_active_time` during one run.
3. Whether a user-level way exists to keep the card in D0 for a whole lock-held run, without root: for example a small holder that keeps a GPU context open from before the probes until after the game has exited, or reusing the probe's result within a boot so later runs don't probe again. Measure what each one does to the cycle count.

## Change

In `mod/dev/client-test.sh` and `mod/dev/env.sh` only: the change that brings one run down to one wake-up and one suspend at most, if step 3 finds one. The card must be allowed to suspend again after the run, and an aborted run (Ctrl+C, a killed scope) must not leave it held awake. If no user-level way works, change nothing and say so.

Anything that needs root or changes the system (the driver's `NVreg_DynamicPowerManagement`, `power/control`, `nvidia-persistenced`, kernel options) is only described in the report with its cost (battery), for the owner to decide. Never do it.

## Rules

- `AGENTS.md` applies. Worktree `~/AresOS-47-gpu-awake`, branch `pkg/47-gpu-awake`, from main. Merge `origin/main` into the branch before the hosted checks.
- Read-only on the system: no sudo, no writes under `/sys`, `/proc` or `/etc`, no driver or module changes.
- Game runs only through `mod/dev/client-test.sh` (the lock, one game at a time, 6 GiB free). Never `./gradlew` yourself, never `--force`.
- Headless only, never `WAYLAND_DISPLAY=wayland-0`. Never touch `~/.minecraft`, `~/.lunarclient` or Lunar Client. Stop only processes you started, by PID.
- The repo is public: no personal data in the report (log excerpts only for the GPU's lines; no hostnames, serials or user names).
- Report in `reviews/47-gpu-awake/REPORT.md`. Open a PR "Package 47: client-test and the NVIDIA card's power cycling". Never merge, never push to main, never `--no-verify`.
