# Chrome feasibility experiment — package 17

This directory is a check, **not product code**. It exposes raw CDP and evaluates JavaScript.
It is not an MCP server, an approval mechanism, or a security boundary.
The findings, including negative results and evidence labels, belong in
[`reviews/17-chrome-check/REPORT.md`](../../../reviews/17-chrome-check/REPORT.md).

Run only through `.github/workflows/control-chrome-check.yml` on `pkg/17-chrome-check`.
`run.mjs` refuses other operating systems and environments without `GITHUB_ACTIONS=true`.
Do not run a browser locally for this check. `npm ci --ignore-scripts` and `node --check`
do not launch browsers.

The workflow installs Google's branded stable Debian package, prints its version, and runs
headed on Xvfb/Openbox. No browser launch uses `--no-sandbox`, a debugging port, or a debugging
pipe. The consent route enables Chrome's own debugging listener **after** launch through its UI;
that route must be evaluated separately against the owner's prohibition on debugging ports.

Files:

- `fixture.mjs`: two local HTTP origins, persistent synthetic login cookie, page fixtures,
  receiving HTTP endpoint, service worker and WebSocket receiver. `server.jsonl` records
  arrivals independently of the control code. No real accounts or credentials.
- `extension/`: minimal MV3 tab selector and `chrome.debugger` transport.
- `native-host.py`: Chrome's length-framed native messaging pipe to a Unix socket. Socket mode
  0600 prevents access by other Unix users; it does not authenticate other processes of the same user.
- `protocol.mjs`, `routes.mjs`: transports and attach comparisons, including the pinned
  Playwright Web Store bridge. The Playwright internal attach factory is used as an experiment;
  it is not a supported public API to build the product on.
- `view.mjs`: accessibility tree plus DOM layout and identity-bound references. CSS coordinates
  are relative to each frame's viewport. This prototype does not compute occlusion or parent-frame
  clipping, and its pagination limits element rows, not text bytes.
- `hold.mjs`: request-stage interception and a deliberately limited candidate classifier.
  The synthetic `/receive` endpoint is always held, regardless of the classifier's prediction.
  That makes interception capability and semantic classification separate measurements.
- `checks.mjs`: read, act, stale-target, tab-switch, hold, public-site and WebSocket probes.
- `peer-probe.mjs`: a separate same-user process tests channel reuse/impersonation.
- `ui.mjs`: simulates the owner's installation/selection/consent in CI. It is not the page tool.

Evidence artifacts are under `.work/17-chrome/artifacts/`: exact head/version/run identifiers,
`check.log`, `server.jsonl`, structural views, Playwright aria snapshots, measurements,
hold records, public-site request metadata and report-only screenshots. Browser profiles,
ephemeral keys and dependencies are not uploaded. Each hold record gives a synthetic case ID;
find that ID in `server.jsonl` to check delivery independently. A released request's decision is
consumed before continuing it; neither transport failures nor subsequent calls retry a send.

Public-site experiments use no accounts, synthetic input, and request interception to drop
submissions. A separate guard drops background Fetch/XHR/Ping requests even if the candidate
classifier calls them reads. Site availability or anti-bot failures must be reported as limited
observations, not as successful coverage.

For Linux image installation, investigate a signed CRX with a stable public-key-derived ID,
installed through managed `ExtensionInstallForcelist` plus an update manifest, or a Linux
external-extension JSON file pointing to a packaged CRX. Pair it with a system native-host
manifest allowing only that extension ID and a service-owned relay. CI loading an unpacked
directory is development setup, not a deployment plan. Those production installation paths
are documentation research until qualified in an actual image; this check changes nothing in `os/`.
