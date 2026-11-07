# 17d Chrome floor — check only

Every browser run is confined to GitHub Actions Linux, headed branded Google Chrome with its sandbox on and no debugging listener. Local checks parse source only. Reuses 17c's signed policy installation, native bridge, X display helpers and independent receiver audit, plus 17b's HTTP/3 receiver.

Phases: `floor`, `workers`, `allowances`, `storage`, `public`. `summary.json`, `extension-events.jsonl`, `server.jsonl`, `delivery-audit.json` and screenshots are the evidence. Each count is checked again after Chrome exits. `expected` audit entries assert a blocking/positive control; `observed` entries are explicitly diagnostic counterexamples/ordering experiments and freeze their count until final shutdown. An observational pass is not proof of the design's hypotheses.

Raw RPC, exposed native functions, fixture-only host partitioning, intentional Fetch pauses, script reports, short public visits and synthetic account fingerprints are experimental shortcuts. Nothing here is product code or a general hostile-site security boundary. No notification or raw page message can approve production work through this harness.
