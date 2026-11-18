# Package 42, review 10: step 2, Control's rules (Codex gpt-6-astra, high, read-only, on b82e8fb3)

No must-fix or should-fix findings in `b82e8fb3`.

- **Note — failure diagnostics can be lost:** [os/ci/release28_walk.py:507](/var/home/ares/AresOS-42-release-28/os/ci/release28_walk.py:507). If a login-graph query times out, the probe exits before exporting the completed checker’s stdout, stderr and status. I reproduced this in memory. It still fails closed; preserving the checker result before traversing the graph would improve diagnostics.

- **Note — provenance relies on the complete pipeline:** [os/ci/release28_record.py:12](/var/home/ares/AresOS-42-release-28/os/ci/release28_record.py:12). `complete()` alone accepts a minimally populated forged manifest with the expected revision. The publication path protects this correctly: preceding image checks validate the install map and independently reconstruct the vendor tree from locked wheels; the diff additionally checks exact metadata, bytes and completeness. The record reads the extracted image manifest, and `verify_release` binds `control/` alongside the other image sources.

- **Note — browser deferral is consistent:** [reviews/42-release-28/PROGRESS.md:137](/var/home/ares/AresOS-42-release-28/reviews/42-release-28/PROGRESS.md:137). Part A installs the adapter and its generated build ID, both covered by the exact install map. It does not install the deferred browser bundle. Deferring top-level `chrome_build`, registration and excluded-sites persistence leaves no corresponding R28 payload unexplained.

The reviewed negative cases cover neighbouring paths, metadata, missing/extra entries, account rows, audit rows and vendor mismatches. The source stop includes `control/`; both R28 boots invoke the bound stdin checker and validate folder metadata and login dependencies. Both N2 guards reject non-branch refs before substantive work.

Five focused tests passed; six additional in-memory guard cases passed; all 269 receipt hashes match. The existing guard fixture encountered only the expected read-only temporary-directory error. Full fixture-dependent suites and real-image/VM runs were not rerun. No files changed.

SAFE