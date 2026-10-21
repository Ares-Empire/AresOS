No findings in the 04d delta (`64879bd..ffdb5fc`).

- **Source fix:** `HomeSites.find` completes FEATURES in fixed x/z order with a one-chunk halo, then loads the entire scoring footprint to FULL before reading blocks. Scoring, tie-breaking and fallback traversal have stable order.
- **Assertion preserved:** the original exact site-equality check is unchanged; only its failure message expanded. Safety checks remain intact.
- **Regression test:** covers three seeds, three distinct fresh worlds each, repeated searches, different load states, arrival ticks and rejoin. Recorded old-code runs demonstrate both the actual load-state mismatch and the final test rejecting incomplete terrain.
- **Existing behavior:** saved-home and one-use provisioning guards remain unchanged, preventing existing hubs from rebuilding. Desktop-marker checks and world-rule boundaries remain intact.

I independently checked all five successful full-run logs and matched the four changed files against their recorded hashes. Each run completed all client suites and 15 server tests. Gradle was not rerun during this read-only review.

SAFE