# Stage 1 known gaps

The current executable pin is the round-2 pin described below; earlier sections retain their historical conversion and verification evidence.

The list starts with Mail review 22's three blocking cases. They remain failures in production; stage 1 exposes them without changing their assertions.

| Named assertion | Matrix row | Closing stage | Expected / observed |
| --- | --- | --- | --- |
| `G22-rename/assertion` | M03/C03 | 3 | LIST observed Trash at the renamed target while Drafts was unresolved; the response instead says unverified. |
| `G22-evidence/assertion` | M03/C03 | 3 | A refused recovery-result write must retain the observed Trash occurrence after remote evidence changes; the later catalogue omits it. |
| `G22-latch/assertion` | M08/M10/M13 | 3 | A zero-byte ENOSPC with successful cleanup must allow a healthy next write; it still returns storage_limit. |

`KNOWN-GAPS.json` is the compact format-3 executable ledger. Each group fixes its suite, ownership bucket, matrix row, closing stage, exact assertion count, three sample keys and SHA-256. The digest covers the sorted newline-delimited canonical JSON list of `[key, {row, stage, delta}]`; `delta` includes calls, missing/extra facts and page numbers. No full assertion list is committed. The twelve fixed buckets match four shards × three workers; point-zero cases are shared by every worker. Each suite verifies every owned group, including absent groups. A changed count, digest, row/stage, group or sample fails. Diagnostics distinguish unexpected passes/removals, unlisted additions and changed deltas where the committed summary permits.

Each worker writes its complete actual format-2 list to `.work/mail-ci/owner-gaps-*.json.gz`, including when strict verification fails; installed-channel cases write under `.work/control-ci/`. Existing artifact steps upload those files. After downloading all artifacts into `.work/19b-fixes/capture/`, regenerate the full list on demand with:

```sh
PYTHONPATH=control python3 -m owner_state_oracle.gaps .work/19b-fixes/capture/*/owner-gaps-*.json.gz --full --output .work/19b-fixes/actual-full.json
PYTHONPATH=control python3 -m owner_state_oracle.gaps .work/19b-fixes/actual-full.json --output .work/19b-fixes/actual-compact.json
diff -u reviews/19b-owner-state/KNOWN-GAPS.json .work/19b-fixes/actual-compact.json
```

The converter rejects conflicting shared keys. Before expectation fixes, the 52 MB format-2 ledger converted to 804,042 bytes / 1,623 ownership groups, preserving all 675,562 exact failures (stage 2: 44,856; stage 3: 630,706). `LEDGER-CONVERSION.json` pins the original and converted file hashes. Independent rehashing of the original full list matched every committed digest and count. Compact-ledger self-tests cover unchanged input, flipped delta, removed/added keys, unexpected passes, regrouping and every group's ownership. The AST import check includes `gaps.py`.

All sweep entries were recollected from Linux diagnostic run [42628677586](https://github.com/Ares-Empire/AresOS/actions/runs/42628677586), source `198b9ef1`, with the reproducible UUID stream and effective-calendar/nanosecond clock. Each of four artifacts contains two isolated workers, all 32 flows and every fault/mode/pair/crash case. All eight workers deliberately failed only after emitting the complete capture; it is not green verification. Capture parsing checks worker ownership, every flow, identical shared clean keys and lossless format-2 round-trip. The assertion-key set stayed identical; 9,894 exact deltas changed and the group count fell from 1,559 to 1,513.

The later strict pair at `ec2fe843` exposed an oracle-only ordering tie: recovery and unchecked notices for one operation shared the same source/time key. Fresh hash-seed processes reproduced different page membership with identical fault traces. Expectations now derive the documented public notice IDs, use saved creation times when committed, and group/sort by creation time and public ID. No hash seed is pinned in normal CI.

The corrected pin replaces full local repair, settlement, filing move/copy/rename and focused-contract captures. Their real descriptor-walk fixtures have the same discovered boundary counts as Linux; full repair replays under hash seeds 1 and 4 produce exactly the same 35,830 assertion entries. Four disjoint complete onboarding replays match all 145,018 prior Linux entries exactly. The other 26 sweep prefixes and named/installed-channel entries remain from Linux. No assertion keys were added or removed; 8,486 deltas changed (1,805 repair, 1,737 settlement, 1,724 each filing move/copy, 1,495 rename, one focused contract). These are oracle corrections, not production gap closures. The complete strict Linux repetitions in REPORT.md verify the final list, including every retained entry.

The original 115 non-sweep entries came from diagnostic Mail run [42613046233](https://github.com/Ares-Empire/AresOS/actions/runs/42613046233) and installed-channel base run [42613046019](https://github.com/Ares-Empire/AresOS/actions/runs/42613046019); the single corrected contract entry is identified above. HTTPS POST context failures remain assigned M04. Diagnostics never count as passing verification.

## Stage 1, fixes round 1 pin

**Run:** the completed Linux capture is Mail [42657094358](https://github.com/Ares-Empire/AresOS/actions/runs/42657094358), attempt 1, source `0b6cfec6`; installed-channel data is from base [42657093657](https://github.com/Ares-Empire/AresOS/actions/runs/42657093657), attempt 1. All twelve workers ran all 32 flows. Each worker's only failing test was its final comparison to the superseded pin; the inherited sweeps passed. The suite's 316 tests and the base's 207 tests passed. This is capture evidence, not strict green verification.

The merged full lists agree on every shared clean key. Every nonshared key belongs to exactly its worker; all twelve owners and all five dedicated suite/named prefixes are present. `LEDGER-CAPTURE.json` records artifact hashes, counts and the committed ledger hash. The pin contains **1,648,920 exact assertion failures**, **44,857 for stage 2** and **1,604,063 for stage 3**, in **1,697 groups / 858,685 bytes**. Relative to the original full list, 1,012,928 keys were added, 39,570 removed and 544,176 retained keys changed their exact row/stage/delta. The many added keys primarily come from per-response envelopes and read-status checks; corrected background, lifecycle, binding, qualification and audit expectations also change or remove earlier incorrect deltas. These are changes in oracle coverage and correctness, not production gap closure.

| Flow / suite owner | Stage 2 assertions | Stage 3 assertions |
| --- | ---: | ---: |
| `G22-evidence` | 0 | 1 |
| `G22-latch` | 0 | 1 |
| `G22-rename` | 0 | 1 |
| `archive` | 0 | 58,409 |
| `attachment_export` | 0 | 74,755 |
| `cancel` | 0 | 10,149 |
| `channel` | 0 | 2 |
| `contract` | 16 | 348 |
| `delete_permanent` | 3,131 | 65,571 |
| `delete_trash` | 1,879 | 42,519 |
| `draft_append` | 629 | 8,061 |
| `expiry` | 0 | 11,508 |
| `export_rollback` | 0 | 84,481 |
| `filing_copy` | 0 | 67,373 |
| `filing_move` | 0 | 67,373 |
| `filing_rename` | 1,134 | 32,296 |
| `flag` | 594 | 7,656 |
| `folder_create` | 594 | 7,656 |
| `folder_delete` | 1,234 | 30,850 |
| `folder_review` | 889 | 16,512 |
| `maintenance` | 0 | 6,303 |
| `onboarding` | 19,883 | 334,740 |
| `password` | 1 | 1,896 |
| `repair` | 1,908 | 82,005 |
| `restore` | 0 | 17,110 |
| `send` | 4,865 | 159,407 |
| `settings` | 924 | 14,140 |
| `settlement` | 0 | 31,622 |
| `status` | 0 | 22,587 |
| `testapp_config` | 721 | 7,779 |
| `testapp_delete` | 0 | 38,962 |
| `testapp_export` | 0 | 24,021 |
| `testapp_send` | 0 | 57,842 |
| `unsubscribe_https` | 1,253 | 54,045 |
| `unsubscribe_mailto` | 5,202 | 166,082 |

Every exact assertion's row, closing stage, calls and missing/extra/page delta is covered by its group's digest. The full lists are generated only under `.work/` and uploaded as artifacts. Nothing is skipped; a changed digest/count/group, unexpected pass, unlisted failure or unexecuted owned group fails. Remaining stage-2 gaps concern pre-command context; stage-3 gaps concern durable disclosure, lifecycle and current refusals. The list intentionally remains nonempty at this stage-1 stopping point.

**Run — deterministic caller input:** the first strict repetition at `92f587de` exposed random temporary-directory components in full audit deltas. `CALLER-REPLAY.json` proves that the two complete Linux captures agree exactly after replaying only the now-deterministic caller input in 2,380 assertions. `caller_name` preserves the original directory-name width, and `flock` isolates shared cases. The pin above has been replayed to those literal deterministic paths; counts, rows/stages, calls and pages are unchanged. The runtime comparator performs no path normalization and still rejects a wrong target. `caller_capture.py` is only an offline historical-capture converter; REPORT.md gives its replay command. Fresh CI artifacts already contain deterministic paths and use the ordinary regenerate/diff command above.

**Run — strict verification:** base [42669403736](https://github.com/Ares-Empire/AresOS/actions/runs/42669403736), Mail [42669403515](https://github.com/Ares-Empire/AresOS/actions/runs/42669403515) and boundary [42669647155](https://github.com/Ares-Empire/AresOS/actions/runs/42669647155) passed base/boundary attempts 1 and 2 and Mail attempts 1 and 3 on `25dfdd63714bf80ef55ec4b106eac359f344a82b`. Every compact group matched both times; details and exact log lines are in REPORT.md.

## Stage 1, fixes round 2 pin

**Run:** merged all 17 full-list artifacts from Mail [42687523943](https://github.com/Ares-Empire/AresOS/actions/runs/42687523943), attempt 1, and base [42687524469](https://github.com/Ares-Empire/AresOS/actions/runs/42687524469), attempt 1, at `72d3ac77375594f867f0127a7939388c63121159`. Every worker completed all 32 flows and failed only at the superseded compact pin. This is a diagnostic capture. `LEDGER-CAPTURE-R2.json` pins its artifact hashes and resulting compact bytes.

Current pin: **1,629,889 exact keys**, **44,857 stage 2 / 1,585,032 stage 3**, **1,716 groups / 868,337 bytes**. Compared with round 1: 48,348 added keys, 67,379 removed, 1,320,217 retained keys with changed deltas. Required recovery obligations replace incorrect old expectations of an empty catalogue; additional expiry, probe, metadata and final-response proofs expose new gaps. Archive clock input is corrected (353 discovered points versus 356), with no other flow's point count changed. REPORT.md explains these changes and the validation-only app/action guard added after capture. No production gap is claimed closed, and no comparison is skipped or weakened.

| Flow / suite | Stage 2 | Stage 3 |
| --- | ---: | ---: |
| `G22-evidence` | 0 | 1 |
| `G22-latch` | 0 | 1 |
| `G22-rename` | 0 | 1 |
| `archive` | 0 | 56,152 |
| `attachment_export` | 0 | 67,394 |
| `cancel` | 0 | 10,224 |
| `channel` | 0 | 2 |
| `contract` | 16 | 356 |
| `delete_permanent` | 3,131 | 65,766 |
| `delete_trash` | 1,879 | 42,564 |
| `draft_append` | 629 | 8,137 |
| `expiry` | 0 | 12,211 |
| `export_rollback` | 0 | 75,238 |
| `filing_copy` | 0 | 67,721 |
| `filing_move` | 0 | 67,721 |
| `filing_rename` | 1,134 | 32,508 |
| `flag` | 594 | 7,721 |
| `folder_create` | 594 | 7,721 |
| `folder_delete` | 1,234 | 30,819 |
| `folder_review` | 889 | 14,281 |
| `maintenance` | 0 | 6,303 |
| `onboarding` | 19,883 | 334,922 |
| `password` | 1 | 1,961 |
| `repair` | 1,908 | 82,460 |
| `restore` | 0 | 17,287 |
| `send` | 4,865 | 160,393 |
| `settings` | 924 | 14,281 |
| `settlement` | 0 | 31,777 |
| `status` | 0 | 22,587 |
| `testapp_config` | 721 | 7,844 |
| `testapp_delete` | 0 | 39,100 |
| `testapp_export` | 0 | 20,227 |
| `testapp_send` | 0 | 58,118 |
| `unsubscribe_https` | 1,253 | 54,165 |
| `unsubscribe_mailto` | 5,202 | 167,068 |

Regenerate the complete actual list and compact pin from the downloaded artifacts:

```sh
PYTHONPATH=control python3 -m owner_state_oracle.gaps .work/19b-round2/capture/*/*/owner-gaps-*.json.gz --full --output .work/19b-round2/actual-full.json
PYTHONPATH=control python3 -m owner_state_oracle.gaps .work/19b-round2/actual-full.json --output .work/19b-round2/actual-compact.json
diff -u reviews/19b-owner-state/KNOWN-GAPS.json .work/19b-round2/actual-compact.json
```

The compact checker still covers every exact key, row, stage, call, missing/extra fact and page position. Final strict workflow evidence is in REPORT.md; captures and the earlier cancelled snapshots are not green verification.
