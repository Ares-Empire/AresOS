Reviewed `67a05483`, limited to the four fixes and their affected paths.

1. **CLOSED — Gradle daemon switches.** The shared guard rejects all eight requested spellings, and all three scripts check forwarded arguments through it. [env.sh:99](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/env.sh:99)

2. **CLOSED — failed systemd queries.** Cleanup checks query status separately, retries stops and queries, and exits non-zero with unit names after 30 seconds without confirmation. It skips folder cleanup on that failure. Stale-folder deletion also requires a successful listing. [env.sh:167](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/env.sh:167), [run-hub.sh:86](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/run-hub.sh:86)

3. **CLOSED — unbounded startup cancellation.** Startup has a 15-second deadline. Timeout kills and reaps the pending launcher before exit cleanup stops the registered unit; a deferred signal supplies the exit status. [env.sh:128](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/env.sh:128)

4. **CLOSED — scope-name ownership.** Existing names cause another suffix to be selected. A launcher failure before observed activation removes the candidate from cleanup ownership and propagates failure. The remaining name-creation race is an accepted, documented limit. [env.sh:130](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/env.sh:130)

The [README’s known limits](/var/home/ares/AresOS-29-linux-dev-rig/mod/README.md:73) honestly describe the signal-only terminal checks, stand-in hanging probe, hanging manager calls, and name race. No remaining or new finding meets the specified bar.

Read-only syntax checks on all four scripts and scoped `git diff --check` passed with no output. No files changed; no Gradle, Minecraft, compositor, or runtime stand-ins were run.

SAFE