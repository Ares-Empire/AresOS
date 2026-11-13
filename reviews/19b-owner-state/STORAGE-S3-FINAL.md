# Final fixed-storage round: measurement stop

**STOP; stage 3 is incomplete.** Candidate code is preserved in
[STORAGE-S3-FINAL.patch](STORAGE-S3-FINAL.patch), not installed in the final tree.
The candidate source head was `3c8958ed` (preceded by `db95ef2b`, `da104c8f`).
The final withdrawal restores the production code, oracle, tests and generated
catalogue to `50d14a07` / the accepted stage-2 implementation. No history is
rewritten and no further redesign is proposed.

The single-recipient reference send passes, but a three-recipient send adds
**1,334.22 permanent-source bytes per operation** against `7b0e9a05`. The base
record test already includes a typical three-recipient send; the additional
measurement uses three synthetic To recipients, the same workload on both
versions. It is not a pathological maximum-recipient case. This exceeds the
about-1-KB permanent-source budget, so the run stops under the storage rule.

## Measured bytes

Run: the supplied [harness](STORAGE-S3-FINAL-HARNESS.py), using only synthetic
accounts and policy files under this worktree. The frozen baseline's 37 tracked
`control/aresos_control` files were compared byte-for-byte with `git show
7b0e9a05:PATH`: **37 compared, zero differences**. Captures are summarized with
all kept file inventories in [STORAGE-S3-FINAL.json](STORAGE-S3-FINAL.json).

Amounts below are **extra bytes against `7b0e9a05`, per operation**, measured
across 100 operations and exactly one archive run. Permanent sources include
`operations.jsonl`, the active projection, tombstones, and every retained
archive/export/history copy. The separate all-files column additionally counts
the working SQLite database, its sidecars, the disposable index, receiver data,
blobs, wires and origin files. Negative all-files figures are actual measured
savings; they are not used to offset additional permanent-source bytes.

| Workload | While open: extra all kept files | Permanent: extra sources | Permanent: extra all kept files |
| --- | ---: | ---: | ---: |
| Send, one recipient | 9,115.10 | 952.22 | -8,386.66 |
| Send, three recipients | 13,076.06 | **1,334.22** | -8,660.02 |
| MOVE | 6,899.57 | 940.51 | 940.51 |
| Permanent delete | 3,306.70 | 624.51 | 624.51 |
| Free change: CREATE | 543.15 | 278.51 | 278.51 |
| 25 MiB send workload, average (*) | 9,115.19 | 952.22 | -8,427.62 |

(*) The large-send batch contains one 25 MiB attachment send and 99 ordinary
sends. All 100 retire together. Its complete inventories are retained, alongside
independent one-operation measurements of each of the five reference workloads.
The marginal large send, allocating one hundredth of the shared run, is
`mixed batch total - 99 × ordinary batch average`: extra open bytes **9,124.10**,
extra permanent sources **952.22**. No 100-copy, multi-gigabyte attachment batch
was needed or left behind.

For completeness, the full-file growth from each fixture's pre-operation
inventory, before subtracting baseline, is:

| Workload | Open baseline | Open candidate | After archive baseline | After archive candidate |
| --- | ---: | ---: | ---: | ---: |
| One-recipient send | 73,851.11 | 82,966.21 | 78,796.56 | 70,409.90 |
| Three-recipient send | 102,126.83 | 115,202.89 | 102,944.82 | 94,284.80 |
| MOVE | 17,158.35 | 24,057.92 | 14,333.97 | 15,274.48 |
| Permanent delete | 30,196.67 | 33,503.37 | 26,247.04 | 26,871.55 |
| CREATE | 2,945.87 | 3,489.02 | 2,499.93 | 2,778.44 |
| Large-send batch average | 432,660.10 | 441,775.29 | 437,661.32 | 429,233.70 |

The exact extra permanent-source decomposition is:

| Workload | Journal | Existing exports | Live projection | Tombstone file | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| One-recipient send | -686.23 | 1,565.58 | 0 | 72.87 | 952.22 |
| Three-recipient send | -530.23 | 1,791.58 | 0 | 72.87 | **1,334.22** |
| MOVE | 330.55 | 498.10 | 0 | 111.86 | 940.51 |
| Permanent delete | 275.55 | 276.10 | 0 | 72.86 | 624.51 |
| CREATE | 110.55 | 111.10 | 0 | 56.86 | 278.51 |
| Large-send batch average | -686.23 | 1,565.58 | 0 | 72.87 | 952.22 |

There is no `owner-source.bin`, `owner-history/`, duplicate full-event stream or
unlisted retained storage. The large SQLite reduction for sends comes from
replacing per-operation archive rechecks with the archive's own shared check;
the old post-cutoff check events otherwise remain in the working database.
SQLite page allocation also explains the larger all-files open MOVE figure.
These working-view savings do not make the added immutable commitments vanish.

## What each record buys

- Active frames contain only **context, resolution, check-open, check-result or
  acknowledgement**. Tombstones are the sixth kind. They retain native
  identities, folders, roles, recipient count/hashes, states, warning occurrence
  metadata and qualification codes. Authored text, approval inputs, arguments
  and audit prose are excluded. Wording is generated; matching SQLite data may
  enrich it. Framing is 12 bytes plus one 32-byte chain hash.
- A selected publication adds one **55-byte `owner` commitment** to an existing
  immutable fence. It binds both kind and facts, detects a completely removed
  committed suffix, and prevents a rechained false acknowledgement. The same
  fence is already present in the full owner export, so both kept copies are
  counted. It creates no transaction. A three-recipient send has 17 selected
  frames instead of 13; these per-stage commitments remain after compaction.
- Context lands before the associated mutation. Resolution/stage facts retain
  the outcome the owner must inspect. Check-open reserves result space before
  warning-producing evidence is read. Check-result records evidence without
  acknowledging its occurrence. Acknowledgement identifies that occurrence.
  Interrupted checks can materialize a generic occurrence before a later check
  replaces them; a subsequent clean result does not acknowledge it.
- The archive checks Sent in its **own** open/result records, commits both
  before its cutoff, then exports and re-reads the export. It never creates a
  new result record on an operation being retired. Every measured send/delete
  batch retired all 100 operations in **one** run; the harness asserts this.
- A clean send/delete tombstone is **71 bytes including framing**. The measured
  two-Sent-warning tombstone is **89 bytes**, below 128. It contains the compact
  operation ID, final-state byte, acknowledgement IDs and one chain hash bound
  to the hash of the exact full archive entry. No full owner history is moved
  to a new kept file. MOVE has two retired source identities; CREATE one.
- The compact shared archive resolution is **179 bytes per send run**, **178
  per other run**, plus an eight-byte file header. It includes the export name,
  SHA-256 and publication sequence. These figures are not the whole archive
  cost: the two send verification events are **9,294 + 28,032 full-event bytes**
  per 100-operation run, **37,348 bytes including JSONL wrappers**, plus **822
  journal bytes including commit markers**. Those copies are included above.
  The final archive publication is also inventoried (send: 52,509 full-event
  bytes and 35,310 journal bytes); it contains the existing retirement markers.

## Section 5 checks actually run

Candidate tests: **134 tests passed** with
`PYTHONPATH=control:control/tests:control/mail_tests .work/venv/bin/python -m
unittest -v test_owner_state_oracle test_owner_tombstones
test_owner_projection_decoder`. Separately, **two tests passed** with
`-m unittest -v test_owner_stage3_facts`. Exact local logs remain under
`.work/19b-s3-final/` (`unit-final.txt`, `stage3-facts.txt`).

The 14 tombstone tests cover re-read-before-retire, missing/tampered/substituted
exports, refusal of uncovered history, publication failure, removal of a fully
committed projection suffix, one-run retirement beside a new duplicate warning,
acknowledged-warning/finished-work rollback protection, free-change checks and
acknowledgements across rollback, the allowed kinds/no full-event copy, and
preservation of unacknowledged warnings/open checks/unresolved work. They compare
1 and 1,001 archived synthetic sends: the live projection is identical within
each test run (133–134 bytes across separate runs). The measured real batches
also leave **zero additional live projection bytes**.

The SQLite/index failure test reads all its selected fixture facts without those
readers, then checks restart. The two additional tests retain interrupted
specific evidence as an unacknowledged generic occurrence through a later clean
check, acknowledgement and restart, and retain qualification codes without
SQLite prose. These focused tests do **not** establish every-flow/every-mode
fallback agreement.

[STORAGE-S3-QUIET.py](STORAGE-S3-QUIET.py) passed all **34 point-zero flows**:
`PASS: 34 fault-free flows; no owner-state differences`. The restore point-zero
flow, including its formerly failing comparisons, has zero differences.
[STORAGE-S3-QUIET.json](STORAGE-S3-QUIET.json) records each result.

A diagnostic sample of the first and last SQLite main write in each flow, for
single/persistent failure and live/crash recovery, still has differences:
settlement 19, expiry 118, maintenance 106, archive 3, duplicate send 11,
onboarding 5; the other 28 flows have zero in that sample. This is **not a full
sweep**. Only counts are committed in [STORAGE-S3-SAMPLES.json](STORAGE-S3-SAMPLES.json);
no full gap list is committed.

The complete restore fault/cleanup sweep and 1,000/10,000 restore batch regression
were started locally, then interrupted at the storage stop. They are **not
passes**. Three focused base record tests printed `ok` before the latter long
case; it produced no completed suite result. An earlier broad native-macOS run
also had Linux policy/environment failures and was interrupted; it is not
verification. No assertions were weakened to certify these incomplete runs.

## Additional observed functional gap

[STORAGE-S3-FIRST-WRITE.py](STORAGE-S3-FIRST-WRITE.py) reproduces the background
first-cause requirement from `briefs/19b-s1-fixes.md` section 74–78, without
changing the oracle. The first maintenance journal write fails with ENOSPC, and
its cleanup truncate fails too. Inventorying every state/evidence file gives
**identical bytes and hashes before and after**. The warning exists only in the
deferred map. Reopening exactly those crash bytes gives an empty pending view;
nine sampled comparison keys still require the background warning.
[STORAGE-S3-FIRST-WRITE.json](STORAGE-S3-FIRST-WRITE.json) contains the full small
before/after inventory and result. There is no committed fact distinguishing
that failure from no attempt in this case. This requirement remains unmet; its
oracle assertion is retained. No alternative design is proposed.

## Not verified / stop status

Full every-mode equality, all six restore comparisons throughout the complete
fault sweep, D3/D4 across all sites, all alteration controls, an empty gap ledger,
and two passing Control base/Mail/boundary workflow passes are **not achieved**.
The unchanged compact ledger remains 2,011 groups / 1,968,467 keys / 924,737
bytes; it is the accepted stage-2 pin, not a refreshed stage-3 success claim.

No candidate CI run was started: the measured storage stop withdraws the
candidate, and the closing documentation commit explicitly skips CI. No CI
status polling, own stage review, tool-approval change, merge, force push,
Gradle run, system installation or real account was involved. Candidate changes
to `warnings.py` (generic occurrence kind/episode ID) and the additional log
`restore_required` field are preserved only in the patch; `paging.py` is
unchanged. Chrome inherits no active behavior change from this stop.

Remaining `.work/` files over 500,000,000 bytes at closing inventory: **[]**.
