# 17b Chrome holds check — not product code

Run only through `control-chrome-check.yml` on `pkg/17b-chrome-holds`.
The entry point refuses non-GitHub/non-Linux execution. It never launches a browser on the Mac.
Uses the pinned dependencies and CRX3 packer from brief 17. No Playwright browser or consent route is run.

The runner installs its ephemeral signed CRX through a local update server and Linux managed policy;
the native relay has both system and user manifests. Everything is disposable runner state.
`LONG_HOLD=true` adds the one ten-minute hold; keep it for one of the two final-head verifications.

`summary.json` and `check.log` record observations (including negative results and unsupported APIs).
`server.jsonl` is the independent delivery record. `delivery-audit.json` checks for late/duplicate
arrivals after Chrome exits. A passing check means the observations reproduced, not that Chrome
provides a universal fail-closed send boundary. Uncontrolled detach probes deliberately measure leaks.
The extension's raw check RPC is not suitable for exposure to an agent.
