# Owner-state known gaps

The current executable pin is the stage-2 fold pin described in the final section; earlier sections retain their historical conversion and verification evidence.

The list starts with Mail review 22's three blocking cases. They remain failures in production; stage 1 exposes them without changing their assertions.

| Named assertion | Matrix row | Closing stage | Expected / observed |
| --- | --- | --- | --- |
| `G22-rename/assertion` | M03/C03 | 3 | LIST observed Trash at the renamed target while Drafts was unresolved; the response instead says unverified. |
| `G22-evidence/assertion` | M03/C03 | 3 | A refused recovery-result write must retain the observed Trash occurrence after remote evidence changes; the later catalogue omits it. |
| `G22-latch/assertion` | M08/M10/M13 | 3 | A zero-byte ENOSPC with successful cleanup must allow a healthy next write; it still returns storage_limit. |

`KNOWN-GAPS.json` is the compact format-3 executable ledger. Each group fixes its suite, ownership bucket, matrix row, closing stage, exact assertion count, three sample keys and SHA-256. The digest covers the sorted newline-delimited canonical JSON list of `[key, {row, stage, delta}]`; `delta` includes calls, missing/extra facts and page numbers. No full assertion list is committed. The twelve fixed buckets match four shards × three workers; point-zero cases are shared by every worker. Each suite verifies every owned group, including absent groups. A changed count, digest, row/stage, group or sample fails. Diagnostics distinguish unexpected passes/removals, unlisted additions and changed deltas where the committed summary permits.

Each worker writes its complete actual format-2 list to `.work/mail-ci/owner-gaps-*.json.gz`, including when strict verification fails; installed-channel cases write under `.work/control-ci/`. Existing artifact steps upload those files. After downloading all artifacts into `.work/19b-round3/capture/`, regenerate the full list on demand with:

```sh
PYTHONPATH=control python3 -m owner_state_oracle.gaps .work/19b-round3/capture/*/*/owner-gaps-*.json.gz --full --output .work/19b-round3/actual-full.json
PYTHONPATH=control python3 -m owner_state_oracle.gaps .work/19b-round3/actual-full.json --output .work/19b-round3/actual-compact.json
python3 - <<'PY'
import json
from pathlib import Path
p = Path('.work/19b-round3/actual-compact.json')
p.write_text(json.dumps(json.loads(p.read_text()), sort_keys=True, indent=1) + '\n')
PY
diff -u reviews/19b-owner-state/KNOWN-GAPS.json .work/19b-round3/actual-compact.json
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

**Run — final round-2 strict verification:** base [42693447617](https://github.com/Ares-Empire/AresOS/actions/runs/42693447617), Mail [42693447616](https://github.com/Ares-Empire/AresOS/actions/runs/42693447616) and boundary [42693452764](https://github.com/Ares-Empire/AresOS/actions/runs/42693452764) each passed attempts 1 and 2 on `24706dafee41ec8473d71a54aa4c09e434b4e802`. Every Mail job finished below 45 minutes (maximum 36m 11s). Both complete strict artifact sets independently reproduce the committed compact file byte-for-byte; `LEDGER-STRICT-R2.json` pins all 34 artifact hashes. REPORT.md contains exact log lines, per-worker counts and durations. Stage 2 was not started.

## Stage 1, fixes round 3 pin

**Run:** complete Linux capture Mail [42728213029](https://github.com/Ares-Empire/AresOS/actions/runs/42728213029), base [42728213032](https://github.com/Ares-Empire/AresOS/actions/runs/42728213032), both attempt 1, source `745e9d11f97f591d37e8ffb98253ba9ccc8117b1`. All twelve workers completed all 32 flows, with no runtime errors and only final superseded-pin failures. The suite's 317 tests had only the final old contract-pin failure; the 251-test base passed. Every Mail job finished in 30m20s–37m31s. Capture is diagnostic evidence, not strict acceptance.

`LEDGER-CAPTURE-R3.json` pins all 17 artifact hashes, ownership-checked merge, exact counts and compact hash. The current pin contains **1,810,440 exact keys**, **44,857 stage 2 / 1,765,583 stage 3**, in **2,115 groups / 976,806 bytes**, SHA-256 `a5cd7a55288aeb958e4f8420c1ca68e62f62c7c883197fb0fc239ec045809759`. One-space JSON indentation keeps format 3 under 1 MB without removing samples or digest inputs. Strict verification still compares every key, row, closing stage and delta.

Compared with round 2: **194,530 added keys, 13,979 removed keys, 108,328 changed retained deltas**. Retained obligations add missing work/recovery/hold/account comparisons; bounded history and full-effect validation add lifecycle/completion differences. Correct clean-result epochs and notice grouping remove earlier incorrect differences. Row assignments now identify M06/M09/M14 history/retention and M12/C05/M14 account defects explicitly. These are oracle changes; no production gap was closed. D3 remains assigned to stage 3.

| Flow / suite | Stage 2 | Stage 3 |
| --- | ---: | ---: |
| `G22-evidence` | 0 | 1 |
| `G22-latch` | 0 | 1 |
| `G22-rename` | 0 | 1 |
| `archive` | 0 | 56,152 |
| `attachment_export` | 0 | 67,394 |
| `cancel` | 0 | 9,909 |
| `channel` | 0 | 2 |
| `contract` | 16 | 485 |
| `delete_permanent` | 3,131 | 77,001 |
| `delete_trash` | 1,879 | 51,433 |
| `draft_append` | 629 | 8,137 |
| `expiry` | 0 | 11,998 |
| `export_rollback` | 0 | 75,238 |
| `filing_copy` | 0 | 66,495 |
| `filing_move` | 0 | 66,495 |
| `filing_rename` | 1,134 | 32,508 |
| `flag` | 594 | 7,721 |
| `folder_create` | 594 | 7,721 |
| `folder_delete` | 1,234 | 38,645 |
| `folder_review` | 889 | 34,653 |
| `maintenance` | 0 | 6,303 |
| `onboarding` | 19,883 | 394,589 |
| `password` | 1 | 1,961 |
| `repair` | 1,908 | 95,567 |
| `restore` | 0 | 18,822 |
| `send` | 4,865 | 175,195 |
| `settings` | 924 | 14,281 |
| `settlement` | 0 | 34,216 |
| `status` | 0 | 22,587 |
| `testapp_config` | 721 | 7,844 |
| `testapp_delete` | 0 | 48,279 |
| `testapp_export` | 0 | 20,227 |
| `testapp_send` | 0 | 67,287 |
| `unsubscribe_https` | 1,253 | 64,217 |
| `unsubscribe_mailto` | 5,202 | 182,218 |


**Run — strict proof:** Control base [42733231891](https://github.com/Ares-Empire/AresOS/actions/runs/42733231891) / [42733232348](https://github.com/Ares-Empire/AresOS/actions/runs/42733232348), Mail [42733235634](https://github.com/Ares-Empire/AresOS/actions/runs/42733235634) / [42733232393](https://github.com/Ares-Empire/AresOS/actions/runs/42733232393), all attempt 1, and boundary [42733240406](https://github.com/Ares-Empire/AresOS/actions/runs/42733240406), attempts 1 and 2, passed on source `e8d269ad1aa848b0de74392edfb14d817dd0c0ca`. Every Mail job finished below 45 minutes (maximum 43m34s). Each repetition's full 17-list merge reproduces the committed pin byte-for-byte, including all 1,810,440 keys and exact row/stage/delta digests. `LEDGER-STRICT-R3.json` pins all 34 actual-list hashes, run attempts and identical source trees. REPORT.md records exact output lines and job durations. The closing documentation-only commit leaves this code, test and ledger source unchanged.

## Stage 2, part A pin

**Run:** `LEDGER-S2-A.json` records the local refresh of filing move/copy/rename,
HTTPS unsubscribe, focused contracts and named regressions. Unaffected full
entries retain the twice-verified round-3 Linux source. The pin has **1,810,601
exact keys**, **44,857 stage 2 / 1,765,744 stage 3**, **2,115 groups / 976,806
bytes**. Its SHA-256 is
`341e4b3c31d1deb30deff1394514b003f4bdd88bf24fb3b5155c06bd54ca0a42`.
Relative to round 3: 161 added keys, none removed, 1,253 changed deltas. These
expose unsupported filing closure and correct exact HTTPS body evidence; no
production gap is closed in part A. Every digest still covers the complete
key/row/stage/calls/missing/extra/pages data. The final stage-2 Linux repetitions
will replace this intermediate local evidence; see REPORT.md for its scope.

## Stage 2 pin (R2 closed)

**Run:** `LEDGER-S2.json` records all twelve complete local 32-flow captures,
fresh focused/named lists and the previously strict installed-channel prefix.
Every capture was then verified with the strict checker. The pin contains
**2,200,009 stage-3 keys and zero stage-2 keys**, **1,952 groups / 898,329 bytes**,
SHA-256 `36335d9f705794079937fdac48633273c3f4f986d7ee5ea45ad8726b32107055`.
All 44,857 part-A R2 assertions passed; none was reassigned to stage 3. Additional
context transactions introduce further fault sites and exact stage-3 deltas.
D3 and all three G22 cases remain assigned to stage 3.

Format 3 now explicitly declares `suite_buckets: {"onboarding": 24}`. Other
flows retain twelve buckets. Each group is still verified wholly by one Linux
job (shared clean groups by every worker for that suite). The twelve local
workers each cover two complete onboarding buckets; the 24 Linux onboarding
jobs each cover one. Two other flow groups have twelve jobs each. Tests prove
the actual flow/bucket/case partitions and the unchanged inherited sweep.

To regenerate the complete list and compact pin from these local artifacts:

```sh
PYTHONPATH=control python3 -m owner_state_oracle.gaps .work/19b-s2/capture-b/lists/owner-gaps-*.json.gz --full --output .work/19b-s2/full.json
PYTHONPATH=control python3 -m owner_state_oracle.gaps .work/19b-s2/full.json --output .work/19b-s2/compact.json
python3 - <<'PY'
import json
from pathlib import Path
p = Path('.work/19b-s2/compact.json')
p.write_text(json.dumps(json.loads(p.read_text()), sort_keys=True, indent=1) + '\n')
PY
diff -u reviews/19b-owner-state/KNOWN-GAPS.json .work/19b-s2/compact.json
```

This historical local pin predates the authorized fold. The corrected complete
Linux pin below supersedes it. Its original storage stop and diagnostic limits
remain documented in REPORT.md; stage 3 is still outside this run.


## Stage 2 fold: complete Linux pin

**Run:** `LEDGER-CAPTURE-S2-FOLD.json` pins Mail **42760159138 / attempt 1** and
fresh base **42760159041 / attempt 1**, source
`a1859a6969911e3d38866807e0812e6088d4fa7c`. All 48 sweep/onboarding jobs completed
their owned flows and six-test worker runs. All **53 actual lists** agree on
shared keys, have correct unique ownership, and strictly verify against the
packed pin. No earlier partial or local list is borrowed.

The compact format-3 pin contains **1,849,228 exact stage-3 keys / zero stage-2
keys**, **1,936 groups / 890,087 bytes**, SHA-256
`ff3de0ad2c95e7892ad09f46878ee9ba77e5aad7d6490ac369c3bc66297ad988`.
There are 350,781 fewer exact failures than the part-B pin because the fold
removes context transactions and their fault sites; Linux trace numbering and
exact changed deltas are captured rather than normalized away. No R2 assertion
is reassigned to stage 3. D3 and the G22 cases remain stage 3.

The standalone HTTPS receiver and inherited direct archive sweep needed test
recorder/determinism corrections after capture. Neither is an input to these
53 owner-state lists; production, decoder, expectations and owner-sweep scripts
remain identical. Final strict repetitions must validate both fixes and this
entire pin. REPORT.md records all diagnostic failures instead of treating the
capture workflow as green.

To reproduce from the downloaded Mail artifact tree, which includes the copied
fresh base-channel list under `fresh-base/` (full lists stay under `.work/`):

```sh
PYTHONPATH=control python3 - <<'PY'
from pathlib import Path
import json, subprocess, sys
root = Path('.work/19b-fold/ci/42760159138-1')
inputs = sorted(root.rglob('owner-gaps-*.json.gz'))
assert len(inputs) == 53
subprocess.run([sys.executable, '-m', 'owner_state_oracle.gaps',
                *map(str, inputs), '--full', '--output', '.work/19b-fold/full.json'], check=True)
subprocess.run([sys.executable, '-m', 'owner_state_oracle.gaps',
                '.work/19b-fold/full.json', '--output', '.work/19b-fold/compact.json'], check=True)
p = Path('.work/19b-fold/compact.json')
p.write_text(json.dumps(json.loads(p.read_text()), sort_keys=True, indent=1) + '\n')
assert p.read_bytes() == Path('reviews/19b-owner-state/KNOWN-GAPS.json').read_bytes()
PY
```


**Run — final strict pair:** base **42764959121**, Mail **42764959165** and
boundary **42764999307**, attempts **1 and 2**, all passed on
`be8ea4ca20064d403702e81e323a9a2bd731f6dd`. Every Mail job is below 35 minutes
and the unchanged 45-minute cap. Both 53-list full merges reproduce this exact
pin byte-for-byte; `LEDGER-STRICT-S2-FOLD.json` pins all 106 actual-list hashes,
source, output evidence and timings. Zero R2 gaps remain. Stage 3 remains open.

## Stage 2 fixes round 1: complete Linux pin

**Run:** [LEDGER-CAPTURE-S2-FIXES.json](LEDGER-CAPTURE-S2-FIXES.json) supersedes
the fold pin above. It records Mail **42811270001 / attempt 1** and fresh base
**42811270027 / attempt 1**, source
`ad9d6d5903bc7519d271d46dbaffed2091675fb1`. All 48 sweep/onboarding workers
completed their complete owned suites. All **53 fresh full actual lists** have
correct ownership and equal shared values; each strictly verifies against the
packed pin. The capture's expected old-pin failures and standalone mailto
recorder failure are reported in REPORT.md, not counted as strict acceptance.

The format-3 pin contains **2,057,880 exact stage-3 keys / zero stage-2 keys**,
**2,024 groups / 928,878 bytes**, SHA-256
`abaf79487708e750813a25f337633f05bf1b20857cc6cc1aa9f9fd3c1c573277`.
LOCAL_FLAG and the deliberate duplicate-Sent flow expand the full sweep to 34
flows; independent retained-result/effect checks change the exact stage-3
deltas. No R2 assertion is reclassified. D3 and G22 remain stage 3.

Only the standalone real-server mailto test recorder and SMTP receiver gain
missing evidence after this capture. They do not generate any of these 53
lists; production, Driver, expectations, sweep scripts and gap inputs are
identical. Both final strict repetitions exercise that correction too.

To reproduce from the downloaded artifact paths recorded in the manifest,
without writing a full list outside `.work/`:

```sh
PYTHONPATH=control python3 - <<'PY'
from pathlib import Path
import gzip, hashlib, json
from owner_state_oracle.gaps import Gaps, pack, unpack
manifest = json.loads(Path('reviews/19b-owner-state/LEDGER-CAPTURE-S2-FIXES.json').read_text())
assert len(manifest['artifacts']) == 53
entries = {}
for item in manifest['artifacts']:
    path = Path(item['file'])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
    with gzip.open(path, 'rt') as stream:
        actual = unpack(json.load(stream))
    assert len(actual) == item['assertions']
    registry = Gaps()
    registry.entries = actual
    registry.verify(set(item['suites']), item['shard'], item['shards'], 0, 1, artifact=False)
    for key, value in actual.items():
        assert value['stage'] == 3
        assert key not in entries or entries[key] == value
        entries[key] = value
payload = pack(entries)
raw = (json.dumps(payload, sort_keys=True, indent=1) + '\n').encode()
assert len(entries) == 2057880 and len(raw) == 928878
assert hashlib.sha256(raw).hexdigest() == manifest['sha256']
assert raw == Path('reviews/19b-owner-state/KNOWN-GAPS.json').read_bytes()
print('53 strict inputs; 2,057,880 stage-3 keys; zero R2; byte-identical pin')
PY
```

**Run — final strict pair:** base **42818236541**, Mail **42818236590** and
boundary **42818278484** each passed attempts **1 and 2** on
`08644540c415d5f4bbbcb7efe8b1cb105dc161df`. Every one of the 128 Mail jobs is
below 35 minutes (maximum **28m30s / 27m59s**) and the unchanged 45-minute cap.
Both complete fresh 53-list merges reproduce this exact pin byte-for-byte,
with zero R2 gaps. [LEDGER-STRICT-S2-FIXES.json](LEDGER-STRICT-S2-FIXES.json)
records all 106 fresh actual-list hashes, ownership, exact output evidence,
durations and run counts. Stage 3 remains open.


## Stage 2 fixes round 2 pin

The new pin supersedes round 1: **2,043,332 exact keys**, all stage 3, **zero R2**,
**2,018 groups / 926,382 bytes**, SHA-256
`4d370725e0e9caeb46d1a5b79d60083a82bc1bd8d8baff18d756c97c5227e70e`.
[LEDGER-CAPTURE-S2-FIXES-2.json](LEDGER-CAPTURE-S2-FIXES-2.json) names all 53
fresh Linux inputs from Mail 42852031436 / base 42852025144, attempt 1. Every
input is strictly verified after packing, with complete ownership and exact
shared-key agreement. This capture had old-pin failures and one alteration
job timeout; it is not green verification. The timeout's pure join-cost fix
changes no recorded inputs or expectations. Final strict repetitions must
reproduce this pin and complete all alterations.

The report lists all seven changed shared point-zero groups: test-app send
35 to 0, repair 41 to 0, settlement 41 to 1 and status 2 to 0. The remaining
settlement key is its deliberately seeded duplicate-case stage-warning mismatch.
New one-copy quiet contracts require no differing views and cannot enter the pin.

From the artifact paths in the manifest, reproduce the pin without committing
any full list:

```sh
PYTHONPATH=control python3 - <<'PY'
from pathlib import Path
import gzip, hashlib, json
from owner_state_oracle.gaps import Gaps, pack, unpack
manifest = json.loads(Path('reviews/19b-owner-state/LEDGER-CAPTURE-S2-FIXES-2.json').read_text())
assert len(manifest['artifacts']) == 53
entries = {}
for item in manifest['artifacts']:
    path = Path(item['file'])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
    with gzip.open(path, 'rt') as stream:
        actual = unpack(json.load(stream))
    assert len(actual) == item['assertions']
    registry = Gaps()
    registry.entries = actual
    registry.verify(set(item['suites']), item['shard'], item['shards'], 0, 1, artifact=False)
    for key, value in actual.items():
        assert value['stage'] == 3
        assert key not in entries or entries[key] == value
        entries[key] = value
raw = (json.dumps(pack(entries), sort_keys=True, indent=1) + '\n').encode()
assert len(entries) == 2043332 and len(raw) == 926382
assert hashlib.sha256(raw).hexdigest() == manifest['sha256']
assert raw == Path('reviews/19b-owner-state/KNOWN-GAPS.json').read_bytes()
print('53 strict inputs; 2,043,332 stage-3 keys; zero R2; byte-identical pin')
PY
```
