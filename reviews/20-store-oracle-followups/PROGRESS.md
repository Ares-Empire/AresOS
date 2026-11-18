# Empire brief 302 — progress

## Build part 7 (the re-pin)

Status: **Re-pinned; proof 44395635207 dispatched**.

Started at `f8d77702` on `pkg/302-store-oracle`, existing draft PR #111. This run changes only the executable pin, its summary and this classification. Capture source is `6a818646`; `git diff 6a818646 HEAD -- control .github/workflows` was empty before the re-pin. No code, assertion, allowed set, workflow or format changed.

### Capture gate: every job

Capture [44375098965](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965), attempt 1: **48 failures, 13 successes**. All **61 artifacts**, the paginated artifact inventory, run metadata and full job/step logs are under `.work/302/capture-44375098965/`. The downloaded artifact directory names exactly match the API inventory.

All 48 failed jobs have **one failure, zero errors**: `test_all_flows_all_storage_modes_independent_views` reaches `gaps.py:229`, `assert not errors, errors`, after writing its actual list. No other failed test/step, error annotation (apart from that step's exit 1), timeout or recovered setup timeout was found. The ledger passes its two tests. All alteration jobs pass four tests, run their candidates, and report `slipped=0` on every scenario and aggregate line. Part 5's closed-database errors and `3 not greater than 3` corpus assertion are both absent from every full log.

**P** below is that strict old-pin failure; each line reference is to the downloaded top-level full job log, including timestamps. Passed jobs have N/A in the pin-only column. Alteration cells give scenario partitions / candidates; all seven alteration kinds occur on each shard.

| Job | Result | Failed only on pin, no other error/timeout? | Full-log evidence |
|---|---|---|---|
| [ledger](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052042565) | success | N/A — passed | `60_ledger.txt`: 2 tests OK |
| [sweep (0, 0)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043753) | failure | Yes | `2_sweep (0, 0).txt`: P at 503; 1 failure / 0 errors |
| [sweep (0, 1)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043355) | failure | Yes | `53_sweep (0, 1).txt`: P at 414; 1 failure / 0 errors |
| [sweep (0, 2)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043430) | failure | Yes | `32_sweep (0, 2).txt`: P at 408; 1 failure / 0 errors |
| [sweep (0, 3)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043867) | failure | Yes | `4_sweep (0, 3).txt`: P at 452; 1 failure / 0 errors |
| [sweep (0, 4)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043315) | failure | Yes | `57_sweep (0, 4).txt`: P at 407; 1 failure / 0 errors |
| [sweep (0, 5)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043362) | failure | Yes | `50_sweep (0, 5).txt`: P at 411; 1 failure / 0 errors |
| [sweep (0, 6)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043444) | failure | Yes | `47_sweep (0, 6).txt`: P at 427; 1 failure / 0 errors |
| [sweep (0, 7)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052044078) | failure | Yes | `10_sweep (0, 7).txt`: P at 463; 1 failure / 0 errors |
| [sweep (0, 8)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052044031) | failure | Yes | `1_sweep (0, 8).txt`: P at 415; 1 failure / 0 errors |
| [sweep (0, 9)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052045112) | failure | Yes | `0_sweep (0, 9).txt`: P at 405; 1 failure / 0 errors |
| [sweep (0, 10)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043408) | failure | Yes | `39_sweep (0, 10).txt`: P at 425; 1 failure / 0 errors |
| [sweep (0, 11)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043506) | failure | Yes | `44_sweep (0, 11).txt`: P at 394; 1 failure / 0 errors |
| [sweep (1, 0)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043461) | failure | Yes | `45_sweep (1, 0).txt`: P at 407; 1 failure / 0 errors |
| [sweep (1, 1)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043530) | failure | Yes | `9_sweep (1, 1).txt`: P at 424; 1 failure / 0 errors |
| [sweep (1, 2)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043566) | failure | Yes | `26_sweep (1, 2).txt`: P at 408; 1 failure / 0 errors |
| [sweep (1, 3)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043374) | failure | Yes | `51_sweep (1, 3).txt`: P at 406; 1 failure / 0 errors |
| [sweep (1, 4)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043499) | failure | Yes | `24_sweep (1, 4).txt`: P at 428; 1 failure / 0 errors |
| [sweep (1, 5)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043505) | failure | Yes | `18_sweep (1, 5).txt`: P at 437; 1 failure / 0 errors |
| [sweep (1, 6)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043581) | failure | Yes | `41_sweep (1, 6).txt`: P at 404; 1 failure / 0 errors |
| [sweep (1, 7)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052044172) | failure | Yes | `16_sweep (1, 7).txt`: P at 417; 1 failure / 0 errors |
| [sweep (1, 8)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043983) | failure | Yes | `5_sweep (1, 8).txt`: P at 419; 1 failure / 0 errors |
| [sweep (1, 9)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043450) | failure | Yes | `40_sweep (1, 9).txt`: P at 420; 1 failure / 0 errors |
| [sweep (1, 10)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043330) | failure | Yes | `59_sweep (1, 10).txt`: P at 415; 1 failure / 0 errors |
| [sweep (1, 11)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043670) | failure | Yes | `13_sweep (1, 11).txt`: P at 427; 1 failure / 0 errors |
| [onboarding (0)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043479) | failure | Yes | `46_onboarding (0).txt`: P at 363; 1 failure / 0 errors |
| [onboarding (1)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043608) | failure | Yes | `30_onboarding (1).txt`: P at 365; 1 failure / 0 errors |
| [onboarding (2)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043719) | failure | Yes | `22_onboarding (2).txt`: P at 365; 1 failure / 0 errors |
| [onboarding (3)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052044055) | failure | Yes | `3_onboarding (3).txt`: P at 363; 1 failure / 0 errors |
| [onboarding (4)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043638) | failure | Yes | `11_onboarding (4).txt`: P at 362; 1 failure / 0 errors |
| [onboarding (5)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043611) | failure | Yes | `28_onboarding (5).txt`: P at 361; 1 failure / 0 errors |
| [onboarding (6)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043342) | failure | Yes | `52_onboarding (6).txt`: P at 365; 1 failure / 0 errors |
| [onboarding (7)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052044187) | failure | Yes | `7_onboarding (7).txt`: P at 362; 1 failure / 0 errors |
| [onboarding (8)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052044206) | failure | Yes | `8_onboarding (8).txt`: P at 363; 1 failure / 0 errors |
| [onboarding (9)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043628) | failure | Yes | `35_onboarding (9).txt`: P at 377; 1 failure / 0 errors |
| [onboarding (10)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043397) | failure | Yes | `55_onboarding (10).txt`: P at 363; 1 failure / 0 errors |
| [onboarding (11)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043532) | failure | Yes | `21_onboarding (11).txt`: P at 381; 1 failure / 0 errors |
| [onboarding (12)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043359) | failure | Yes | `43_onboarding (12).txt`: P at 364; 1 failure / 0 errors |
| [onboarding (13)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043366) | failure | Yes | `58_onboarding (13).txt`: P at 361; 1 failure / 0 errors |
| [onboarding (14)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043813) | failure | Yes | `19_onboarding (14).txt`: P at 363; 1 failure / 0 errors |
| [onboarding (15)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043600) | failure | Yes | `36_onboarding (15).txt`: P at 363; 1 failure / 0 errors |
| [onboarding (16)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043824) | failure | Yes | `15_onboarding (16).txt`: P at 362; 1 failure / 0 errors |
| [onboarding (17)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043410) | failure | Yes | `54_onboarding (17).txt`: P at 363; 1 failure / 0 errors |
| [onboarding (18)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043542) | failure | Yes | `49_onboarding (18).txt`: P at 363; 1 failure / 0 errors |
| [onboarding (19)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043452) | failure | Yes | `48_onboarding (19).txt`: P at 377; 1 failure / 0 errors |
| [onboarding (20)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043551) | failure | Yes | `25_onboarding (20).txt`: P at 365; 1 failure / 0 errors |
| [onboarding (21)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043441) | failure | Yes | `17_onboarding (21).txt`: P at 380; 1 failure / 0 errors |
| [onboarding (22)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043546) | failure | Yes | `6_onboarding (22).txt`: P at 363; 1 failure / 0 errors |
| [onboarding (23)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043609) | failure | Yes | `33_onboarding (23).txt`: P at 361; 1 failure / 0 errors |
| [alterations (0)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043700) | success | N/A — passed | `27_alterations (0).txt`:385: 10 / 228,154; `slipped=0`; 4 tests OK |
| [alterations (1)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043363) | success | N/A — passed | `12_alterations (1).txt`:371: 8 / 127,812; `slipped=0`; 4 tests OK |
| [alterations (2)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043713) | success | N/A — passed | `34_alterations (2).txt`:370: 9 / 129,349; `slipped=0`; 4 tests OK |
| [alterations (3)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043854) | success | N/A — passed | `31_alterations (3).txt`:373: 10 / 187,689; `slipped=0`; 4 tests OK |
| [alterations (4)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043660) | success | N/A — passed | `29_alterations (4).txt`:373: 10 / 133,537; `slipped=0`; 4 tests OK |
| [alterations (5)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043598) | success | N/A — passed | `56_alterations (5).txt`:389: 11 / 227,582; `slipped=0`; 4 tests OK |
| [alterations (6)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043621) | success | N/A — passed | `37_alterations (6).txt`:370: 12 / 182,536; `slipped=0`; 4 tests OK |
| [alterations (7)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043864) | success | N/A — passed | `23_alterations (7).txt`:388: 9 / 200,826; `slipped=0`; 4 tests OK |
| [alterations (8)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043593) | success | N/A — passed | `42_alterations (8).txt`:367: 10 / 203,117; `slipped=0`; 4 tests OK |
| [alterations (9)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043787) | success | N/A — passed | `14_alterations (9).txt`:369: 10 / 176,389; `slipped=0`; 4 tests OK |
| [alterations (10)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043743) | success | N/A — passed | `20_alterations (10).txt`:371: 9 / 151,630; `slipped=0`; 4 tests OK |
| [alterations (11)](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965/job/135052043570) | success | N/A — passed | `38_alterations (11).txt`:366: 6 / 147,420; `slipped=0`; 4 tests OK |

Alteration totals: **114 scenario partitions, 2,096,041 candidates, zero slipped**. The discovered recovery corpus runs on the hosted trace; no local numeric offset was substituted. Per-shard totals above include applied-tail and staged-restore recordings.

### Historical reproduction, assembly and new pin

The **53 lists of historical proof 43972005458** merge without conflict, with **495 identical shared occurrences**, and reproduce the old pin **byte for byte**: **2,576,083 keys / 1,930 groups / 892,234 bytes**, format 3, SHA-256 `8b27b1161505ac19eeaa41a6f1a69c95886de5da338249801963a96a083b74b1`. This reproduction preceded comparison with the new lists.

For the exact historical H/N7 membership, also downloaded all artifacts of **43722918063**. Its 53 lists regenerate the earlier committed `b04c7e77` pin byte for byte: **2,622,072 keys / 1,997 groups / 921,711 bytes**, SHA-256 `ee326914fff6ccddcb78afbf3c346207148471f3e8b1dd0f96868a776291e68d`. H is the original 1,386-case set; N7 is exactly the 6,224 beyond-alias row/notice changes plus 725 additions in the subsequent historical pin.

The new capture has **52 actual lists**, not 53: 48 sweep/onboarding lists plus contract, G22-rename, G22-evidence and channel. G22-latch no longer writes a list because it is a direct passing regression (`sweep (0, 0)`, `mail.txt:39`). This is the deliberate inventory change recorded in parts 5/6, not missing evidence; no artificial empty list was added. All 52 merge without conflict, again with 495 identical shared occurrences.

Regenerated with the documented `owner_state_oracle.gaps` full-list → compact conversion, then sorted indent-1 JSON. New pin: **2,420,003 keys / 1,860 groups / 860,653 bytes**, all stage 3, format 3, SHA-256 **`1b21f564533df6cdc1c99a5c4068d87538047f54a5243b6d0ed930d378ca2295`**. Format and strict exact-delta verification are unchanged.

### Complete classification against the expected shape

Every key in the union has a receipt in `.work/302/repin/classification.jsonl.gz`: exact key, status, item(s), phase, comparison family and cause. No key falls through the classifier. Full deltas remain in the downloaded lists and generated full ledgers. Counts below distinguish semantic changes from identity aliases. Alias-only entries preserve row, stage, calls, pages and facts and pass a consistent **one-to-one alias mapping**, including ordering changes in fact arrays.

| Outcome | Keys |
|---|---:|
| Closed | 303,001 |
| Changed semantically | 108,155 |
| Changed only by aliases | 8,159 |
| New | 146,921 |
| Byte-identical | 2,156,768 |

The net reduction is 156,080; the large post-start changes are explicitly included below. They are not all N7 and are not an extra store fix. Item 3 changed producing-call ranges from marked to staged sequence, so validation now attributes an interrupted ordinary event to its original call when startup finishes it. This affects staged writes outside historical H too: false lifecycle/hold and pending projections close, while retained public recovery notices and saved-envelope omissions can become visible as new deltas. Item 1's fully rolled-back fence exception also admits later explicit reads/checks which the old latch refused; those can change audit pages, notices and counts. Joint buckets retain both causes instead of assigning every interaction to N7.

| Comparison/cause | Closed | Semantic change | New |
|---|---:|---:|---:|
| Item 1: G22 healthy next write | 1 | 0 | 0 |
| Item 1: latch/status and first-error rules | 92,820 | 522 | 18 |
| Part 4 / item 3: unchecked live-check component and residuals | 9,047 | 7,661 | 3,205 |
| Items 1/3: lifecycle, operation, completion and holds | 21,783 | 5,061 | 959 |
| Items 1/3: applied/staged rows, pending pages/envelopes | 61,663 | 31,526 | 1,174 |
| Items 1/3: recovery, filing, unchecked notices and counts | 113,306 | 60,908 | 134,385 |
| Items 1/3: visible audit history / admitted checks | 4,365 | 231 | 7,140 |
| Items 1/3: filing locations and refused-read paging | 16 | 2,246 | 24 |
| Item 3: applied account qualification in saved refusal | 0 | 0 | 16 |

These buckets classify the affected comparison, not a claim that every independent residual in that comparison is fixed. In particular the live-check bucket removes an `unchecked` component (or is its matching count/page); its remaining/new other deltas keep their own matrix labels. All 293 phase/fact-change signatures are retained in `.work/302/repin/analyze.json`.

- **Item 1 / G22:** `G22-latch/assertion` closes by the passing unchanged healthy-retry assertion. The other **376 fixed contract/G22/channel keys are byte-identical**. Of status changes, 92,820 keys close, 522 change and 18 appear; these include read-only `stale_reference` residuals and call/page changes, rather than treating every later read as latched. The 18 additions are `stale_reference` against expected `allowed`, not new accepted `journal_incomplete` permissions.

- **Item 2:** **zero `startup-replay` failures**, zero `crash-startup` keys and still **zero `.restore-lock` keys**. The new check adds coverage without adding a pinned startup obligation.

- **Item 3 / H:** the original H set remains 1,386 cases. Its old 63,379 keys become **37,328**: **32,478 closed, 7,025 semantically changed, 545 alias-only, 6,427 new, 23,331 identical**. This includes other defects at H; it does not erase the entire set.

- **N7, all 6,949:** **4,100 closed; 928 semantically changed; 365 alias-only; 1,556 identical**. The false marked-versus-applied component is gone. Remaining pending-row deltas are omissions from cached/refused envelopes or pending pages, not model/store state pairs: the retained N7 deltas have **zero same-operation differing pending-state pairs**. There are 1,134 identical and 356 changed pending-row keys; 182 identical, 269 changed and 187 alias-only count keys; 240 identical, 303 changed and 178 alias-only notice keys. The latter retain independent unchecked/Sent-copy, recovery and disclosure/continuation obligations; a count can keep the same mismatch after its underlying membership changes. No N7 key is relabelled as a restore-lock failure.

- **All 544 saved pre-crash envelopes:** **440 close, 32 change, 72 remain identical**, with no alias-only entries. The 32 are 16 count and 16 recovery-head residuals for account-add/repair envelopes; the 72 are 36 count and 36 unchecked/recovery-head residuals (including the archive failure's still-public unchecked warning). They remain tied to the original captured record; these are not newly read post-start rows.

- **Part 4 / M07/C01:** all **84** target sample keys are absent in the fresh full capture (42 repair, 42 send at its hosted final marker 877/878; local marker 873/874). **76** existed in the historical pin and close; the eight count keys first exposed by item 3 are avoided additions. More unchecked components close/change in the complete live-check bucket above. This is distinct from decoder row visibility and from safe first-fence retry.

- **Broader residuals, kept visible:** the 16 new `qualification.mail_account_add` keys expect the independently derived qualification of an applied account in its failed producer's saved envelope; the refusal has no account projection. The history-proof bucket includes 959 new keys, including newly visible applied check reopen/close, stage and missing-notice-source validation. Existing gates still reject those claims; they were not loosened to make a row agree. Representative raw-record probes reproduce archive sequence 15 applied above marker 14 (`unjustified-check-reopen`), filing check-close/notice-source failures and the background-notice source after a safe rollback. These remain lifecycle/response gaps, not additional startup or store fixes.

- **Unrelated classes:** all **544,801 `crash-locked` keys** retain their semantic deltas: **544,273 identical, 528 bijective alias-only**; no key is added/closed there. The R2 failing-key set is empty before and after, and the existing context-before-command checks introduce no failure in any capture sweep case. G22-rename, G22-evidence and channels remain exact. There are **2,572 computed row-label changes**, all accompanied by semantic fact changes in the affected comparison; **zero label-only changes and zero closing-stage changes**. Examples: removing a filing/account recovery component leaves generic M14 or M06; adding a background-storage/source obligation produces M08 or M06/M09/M14. No manual relabelling occurred. The transition counts follow.

| Old computed row | New computed row | Keys |
|---|---|---:|
| M14 | M06/M09/M14 | 462 |
| M14 | M08 | 18 |
| M02/C02/C04/M14 | M14 | 414 |
| M02/C02/C04/M14 | M06 | 122 |
| M02/C02/C04/M14 | M02/C04 | 18 |
| M06 | M02/C02/C04/M14 | 24 |
| M03/C03/M14 | M06 | 158 |
| M03/C03/M14 | M14 | 194 |
| M06 | M03/C03/M14 | 12 |
| M12/C05/M14 | M06 | 106 |
| M14 | M06 | 936 |
| M06 | M14 | 72 |
| M07/C01 | M14 | 36 |

Phase totals over the full union (fixed includes the named suites):

| Phase | Closed | Semantic change | Alias-only | New | Identical |
|---|---:|---:|---:|---:|---:|
| fixed | 1 | 0 | 0 | 0 | 376 |
| exhausted | 5,236 | 5,349 | 61 | 2,981 | 225,060 |
| live-restored | 113,755 | 43,757 | 6,492 | 19,175 | 955,143 |
| crash-locked | 0 | 0 | 528 | 0 | 544,273 |
| crash-restart | 184,009 | 59,049 | 1,078 | 124,765 | 431,916 |

### Drift and flow-point counts

Compared historical proof `305ebcbd` to pre-302 baseline `4a6acc2e`: no oracle implementation or optional-workflow change. The intervening changes are Chrome qualification/committed-read/cache work (#98), the CLI shortcut/help wording, installed daemon config default and sweep comment wording. The Engine difference is only the Chrome qualification cache call, inactive in the Mail/Testapp sweep fixtures. Part 4's main merge `947606b8` changes no `control/` or workflow file; part 6 changes only the two diagnosed harness paths. No concurrent main merge was performed after capture. Protected deltas and all hosted point counts below agree; no unrelated drift was folded into this pin.

Every repeated `Owner oracle flow=… points=…` observation agrees in all three hosted runs: historical 43972005458, rejected 44352598226 and accepted 44375098965. These are **point counts**, not a claim that the artifacts contain complete clean traces. The seven local clean traces were already byte-identical in parts 4/6. No count/site move is observed or silently remapped; the documented native/hosted onboarding (2,570/2,610) and send (875/879) differences are not new moves.

| Flow | Historical proof | Accepted capture |
|---|---:|---:|
| `archive` | 373 | 373 |
| `attachment_export` | 280 | 280 |
| `cancel` | 70 | 70 |
| `delete_permanent` | 420 | 420 |
| `delete_trash` | 282 | 282 |
| `draft_append` | 173 | 173 |
| `expiry` | 69 | 69 |
| `export_rollback` | 280 | 280 |
| `filing_copy` | 353 | 353 |
| `filing_move` | 352 | 352 |
| `filing_rename` | 229 | 229 |
| `flag` | 120 | 120 |
| `folder_create` | 118 | 118 |
| `folder_delete` | 213 | 213 |
| `folder_review` | 173 | 173 |
| `local_flag` | 118 | 118 |
| `maintenance` | 62 | 62 |
| `onboarding` | 2,610 | 2,610 |
| `password` | 131 | 131 |
| `repair` | 366 | 366 |
| `restart_index` | 32 | 32 |
| `restart_tail` | 34 | 34 |
| `restore` | 76 | 76 |
| `send` | 879 | 879 |
| `send_duplicate` | 965 | 965 |
| `settings` | 174 | 174 |
| `settlement` | 157 | 157 |
| `status` | 156 | 156 |
| `testapp_config` | 134 | 134 |
| `testapp_delete` | 282 | 282 |
| `testapp_export` | 147 | 147 |
| `testapp_send` | 391 | 391 |
| `unsubscribe_https` | 350 | 350 |
| `unsubscribe_mailto` | 881 | 881 |

### Commands and evidence

Read-only downloads, all exit 0: `gh run view 44375098965 --json databaseId,headSha,status,conclusion,jobs`; paginated `gh api .../actions/runs/44375098965/artifacts?per_page=100`; `gh run download 44375098965 -D .work/302/capture-44375098965/artifacts`; `gh api .../actions/runs/44375098965/logs`; and `gh run download 43722918063 -D .work/302/historical-43722918063/artifacts`. The complete 43972005458 download was retained from part 5 and reused. The GitHub connector was used to inspect capture artifact metadata; `gh` supplied local bulk downloads and the complete inventory.

For each historical/accepted list set, `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control python3 -m owner_state_oracle.gaps <all sorted owner-gaps-*.json.gz paths> --full --output .work/302/repin/{old,new}-full.json`, then the same module over that full file with `--output .../{old,new}-compact.json`, then `json.dumps(..., sort_keys=True, indent=1) + "\n"`. Converter output: old **2,576,083 / 1,930**, new **2,420,003 / 1,860**, stage 2 **0** in both. Both merges reject conflicting shared keys. The ancestor lists were converted directly to compact and compared to `git show b04c7e77:reviews/19b-owner-state/KNOWN-GAPS.json`.

Offline commands under `.work/302/repin/`: `audit7.py` checks every log/inventory; `detail.py` derives exact H/N7 and separates array-order aliases; `analyze.py` records every fact-change signature; `classify.py` checks every union key, bijective aliases, protected sets, row labels and part-4 targets. All final invocations exit 0. These are hosted-evidence analysis, not local full-matrix test runs. The small `probes.py ... repin302 mail ignored` diagnostic executes eight synthetic flow/mode/phase cases with the documented managed-settings stand-in and records **35 comparisons**; it exits 0. Its first scratch version omitted the required `iter_items` prefix and was corrected; no assertion/test was changed. The classifier's initial draft lacked the qualification-envelope bucket; the 16 actual deltas above were inspected and added explicitly before acceptance.

Per-list paths/bytes/SHA-256: `.work/302/repin/list-manifest.json`. Per-job frames/line numbers/log hashes: `part7-audit.json`. Per-key classification SHA-256: `940dcaa7d3b05c0a7ed77c7ab7d9f2ee483f650fc78cb088bbfe271cc3623834`. The independent checker can regenerate all evidence from these run IDs and full lists; scratch scripts are not part of the executable pin.

### Proof dispatch and Left, in order

Pin/classification commit **`b2d50247`** was pushed normally from `f8d77702`. Then exactly one `gh workflow run control-owner-oracle.yml --ref pkg/302-store-oracle -f ledger_only=false` was dispatched on that committed pin. The command exited 0 and returned **[44395635207](https://github.com/Ares-Empire/AresOS/actions/runs/44395635207)** (receipt: `.work/302/repin/proof-dispatch.txt`). This progress-only commit records the ID and is pushed normally. No other workflow was dispatched, rerun or watched. The lead, **linux-tools**, owns watching; this build run stops here.

1. **Proof green**: all 61 jobs, its **52** fresh actual lists reproduce the new pin byte for byte, all 12 alteration shards `slipped=0`; linux-tools watches it.
2. **Control CI green twice**.
3. A fresh **package review**, **security review** and **independent full classification check**.

**Not verified:** the dispatched proof and subsequent CI/reviews, or real installed owner-service recovery. No local installed/root test, OS owner module, boot/update command, mount, sudo, live-service action, mod/Gradle build or process termination. **JUDGMENT-CALL:** none beyond the already approved brief; no store behaviour is changed here. **PLAN-GAP:** 52 fresh lists after G22-latch becomes a passing assertion, as recorded above. **Open:** proof/CI/review gates only.

Closing local checks: `git diff --check` passes; running the exact Repo privacy workflow script locally prints `No file holds a home path with a real user name.` No files over 500 MB remain under `.work/`. All `.work/302/` evidence, including downloaded lists and intermediate ledgers, totals about 552 MB (below 2 GB). No Gradle daemon was started.

---
## Build part 6 (capture fixes)

Status: **Capture fixes pushed; capture 44375098965 dispatched; next: the re-pin**.

Started at `793387035a5f0d460745d54c65723124cf2847c5`, branch
`pkg/302-store-oracle`, existing draft PR #111. Scope is the oracle harness,
its tests and this progress record. No product, workflow, pin, allowed set or
existing assertion was changed. The lead authorized exactly one replacement
capture because 44352598226 was rejected.

### Causes and fixes

1. **Closed old database in restart flows.** The inherited Scenario constructor
   closes its fixture engine *before* `restart_index`/`restart_tail` attempts
   startup. When that startup fails, `bind` never replaces the closed engine.
   Step 3's `6f12f561` added the unconditional generation query in
   `Driver.restarted`; it consequently queries a closed handle during the
   crash phase. This is locally reproducible at the hosted point numbers. The
   compact sample has seven flows and includes neither restart flow; the small
   sweep suite also did not run their full matrix. Native restart traces are
   28/30 points versus 32/34 hosted, so numerical parity is not assumed. It was a coverage gap, not
   a runner-only close-ordering change. `Scenario` is unchanged since the
   pre-302 baseline, and part 1 did not change `Store.close`.

   `Driver.restarted` still reads the original live connection before closing,
   including its unfinished transaction's view. Only the exact closed-handle
   `ProgrammingError` falls back to the same SQL through a freshly opened
   `mode=ro` connection to the same file, under `outside_faults`, closed before
   crash-byte copying. Other programming/storage errors still propagate. The
   generation, crash snapshot, startup obligation, saved envelopes and restart
   cases retain their meanings.

2. **Applied-tail corpus tied to local offsets.** `recovery_recordings` selected
   cancel 69/onboarding 61 (and staged restore 26) numerically. Those local
   offsets are not portable: the hosted trace has 2,610 onboarding points versus
   2,570 locally. Hosted setup reports Python 3.15.2; this laptop has Python
   3.14.8 / SQLite 3.51.2. The failure was corpus construction before any
   candidates, not an alteration slip or pin comparison. Exact new hosted
   marker numbers are left to the replacement capture's discovery output.

   The corpus now identifies the intended cancellation/account event at its
   commit-marker append and arms the next raw site using the current trace's
   length. It asserts that the event was found, the fault fired and that site
   was `journal.write`. The original `tail['seq'] > max(record.committed)` and
   exact account/cancellation row assertions remain. Final restore similarly
   arms at application after its full generation-changing event is staged;
   intermediate restore keeps its existing application-boundary discovery.
   No numeric corpus offsets remain. All four recording names/order and the
   measured-cost manifest remain unchanged. Missing boundaries fail loudly.

### Regressions and baseline failures

New `control/mail_tests/test_owner_state_capture.py` adds:

- `test_failed_startup_can_be_crashed_with_the_old_engine_already_closed`:
  hosted points `restart_index/27`, `restart_tail/29`, both fault modes, through
  crash startup and post-restart comparison, with empty startup/lock gaps.
- `test_recovery_corpus_discovers_boundaries_after_trace_points_move`: inserts
  eight synthetic VFS trace sites before onboarding's real call. The old 61
  then hits an earlier transaction and reproduces **`3 not greater than 3`**;
  discovery instead finds marker-write 69, sequence 4 above marker 3. It still
  builds all four recovery recordings and asserts the applied account tail.
  This reproduces the hosted *condition*, not the entire hosted runtime.
- `test_restart_preserves_the_live_connections_generation_view`: a live,
  uncommitted generation must reach the startup obligation unchanged. This
  guards the original observation while adding the closed-handle fallback.

An executable export of **79338703**, with only the final new test module
copied in, ran `python3 .work/302/run.py control/test-work/302-exports/part6old mail test_owner_state_capture`:
**3 tests, FAILED (failures=1, errors=4)**, 1.334 s
(`.work/302/part6/baseline-final-tests.log`). The four errors are exactly
`Cannot operate on a closed database`; the failure is exactly
`3 not greater than 3`. The live-view control passes. These are harness
failures, not import, fixture or pin failures.

### Local verification

Final executable export: `control/test-work/302-exports/part6fix/`, no
dot-prefixed ancestor, same path length as part 4's export. One worker;
synthetic fixtures, the documented managed-settings stand-in, ordered base/Mail
imports, exported PYTHONPATH, local TMPDIR, bytecode disabled. Commands below
use `PYTHONDONTWRITEBYTECODE=1`; logs are under `.work/302/part6/`.

- `python3 .work/302/run.py control/test-work/302-exports/part6fix mail test_owner_state_capture`:
  **3 tests OK**, 4.126 s (`regressions.log`). Shifted account marker is 69;
  cancellation marker is 68. All original applied-tail assertions hold.
- `python3 .work/302/base-only.py control/test-work/302-exports/part6fix base test_owner_state_oracle test_owner_state_fixes_s2 test_mail_ci_selection`:
  **174 tests OK**, 1.689 s (`base-final.log`), without Mail helper imports.
- `python3 .work/302/run.py control/test-work/302-exports/part6fix mail sweep-units`:
  **16 tests OK**, 274.741 s (`sweep-units-final.log`). Includes 48 applied-tail
  cases / 76 cleanup phase runs, 47 discovered restore points / 137 cleanup
  pairs, 154 latch view runs / 275 phases and 77 retry/restart cases.
- `python3 .work/302/sample.py control/test-work/302-exports/part6fix mail .work/302/part6/sample`:
  **104 runs, 187 checked phases, 1,444 keys** (`sample.log`).
  `python3 .work/302/part4-delta.py .work/302/part4-after-main .work/302/part6/sample .work/302/part6/sample-delta.json same`:
  **0 closed, 0 changed, 0 new, 1,444 identical; all seven clean traces
  byte-identical** (`sample-delta.log`). No startup-replay/restore-lock keys.
- `python3 .work/302/part6/restart-native.py control/test-work/302-exports/part6fix mail ignored`:
  **1 test OK**, 87.195 s (`restart-native.log`): the existing full-matrix
  test, restricted to the two restart flows in recording mode. **2 clean,
  42 single, 42 persistent, 84 crash, 130 cleanup-pair cases** (pairs run live
  and crash); **686 checked phases, zero gap entries**. All discovered sites
  and cleanup pairs run under the same close-site policy as the hosted suite.
- `OWNER_PERTURB_SHARD=6 OWNER_PERTURB_SHARDS=12 python3 .work/302/run.py control/test-work/302-exports/part6fix mail test_owner_state_perturb.SystematicPerturbations.test_recorded_scenarios_have_no_silent_owner_state_change`:
  **1 test OK**, 716.001 s (`alteration-shard6.log`): **12 recordings,
  183,894 alterations, 21,052 coherent changes, slipped=0**. All seven
  alteration kinds ran. Includes discovered onboarding 1789 and the repaired
  applied-tail cancellation's **2,631 alterations, slipped=0**.

Earlier attempts remain recorded: `baseline-regressions.log` is the initial
baseline failure; `fixed-regressions.log` caught an initially incorrect trailing
slash in the new phase-presence assertion, corrected to the actual case name.
An initial always-read-only implementation ran 16 sweep tests in 169.140 s,
**FAILED (errors=6)** with `attempt to write a readonly database` at active
restore transactions (`sweep-readonly-trial.log`). The final implementation
preserves the live handle and uses read-only access only after it is closed;
the live-view regression and final sweep run cover this correction. No test
was weakened to accommodate that attempt. The first restart diagnostic
(`restart-cases.py`, `restart-cases.log`) completed both native matrices but
then failed an extra, incorrect assumption that all 214 hosted numeric case
labels must exist locally. It is retained unchanged. Local traces are 28/30,
hosted 32/34; 74 numeric case labels differ, including sites/cleanup numbers
which move across close boundaries. This is not a failed restart case. The
unmodified matrix rerun above verifies all native cases; the new regression
separately reproduces both hosted closed-handle conditions. No numerical
remapping or hosted full-matrix reproduction is claimed locally.

### Capture handoff and Left

Harness fixes: `6a818646ebd138180fb211ae37dfd4a0b205cb6d`, pushed normally to
`pkg/302-store-oracle` (from `79338703`), with the required Built-by trailer.
Dispatched exactly one full capture after the successful local runs and push:

```sh
gh workflow run control-owner-oracle.yml --ref pkg/302-store-oracle -f ledger_only=false
```

The command exited 0 and returned
**[44375098965](https://github.com/Ares-Empire/AresOS/actions/runs/44375098965)**.
This is the lead-authorized replacement for rejected capture 44352598226.
No other workflow was dispatched, rerun or watched. The capture was not watched,
awaited or downloaded; `linux-tools` owns that shell. This progress-only commit
records its ID, is pushed normally, and ends the build run.

Left, for `linux-tools` and the subsequent re-pin run:

1. Validate the new capture, download/reconcile its **52** fresh actual lists
   (part 5 explains the removed G22-latch artifact), reproduce the old pin from
   historical full lists, classify every delta and re-pin once.
2. Full proof on that pin: all 61 jobs green; lists reproduce it byte for byte;
   all 12 alteration shards report `slipped=0`.
3. Required Control CI green twice.
4. Fresh package/security reviews and the independent full classification check.

No full-pin, whole-matrix, hosted-boundary or CI-green claim is made by these
local runs. No OS/owner module, installed/root/channel, mod/Gradle, boot,
mount, sudo or live-service action was run. No process was stopped.
`git diff --check` and the repository privacy script pass. Closing scan of
`.work/` and `control/test-work/`: **no files over 500 MB**; the downloaded
rejected capture is 23 MB (below 2 GB).

**JUDGMENT-CALL:** none. **PLAN-GAP:** the compact sample omitted failed startup
with an already-closed engine, and the recovery corpus retained local offsets
although the brief required discovery. Both are now covered explicitly.

---

## Build part 5 (the re-pin)

Status: **Stopped before re-pin; capture 44352598226 has non-pin failures; no proof dispatched**.

### Capture rejected at step 1

Started at `99a5176e`, branch `pkg/302-store-oracle`, existing draft PR #111.
Capture [44352598226](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226),
attempt 1, completed on `e52ae87b4469e6f794dc01aee0f8c19ecc2b4851`:
**60 failed jobs, 1 successful ledger job**. Downloaded all **61 artifacts**
and the complete run log archive under `.work/302/capture-44352598226/`.
The artifact directory names match the paginated API inventory exactly.

The required stop condition is met. Among the failed jobs:

- **22 sweep jobs have 214 additional subtest errors**: 102 in `restart_index`,
  112 in `restart_tail`, all `sqlite3.ProgrammingError: Cannot operate on a
  closed database.` The traceback is `test_owner_state_sweep.py:247` →
  `Driver.restarted`, `control/owner_state_oracle/driver.py:118`, which queries
  the old engine's `store.db` for `generation`. Those jobs also reach the final
  strict old-pin failure; reaching it does not make their incomplete cases valid.
- **All 12 alteration shards fail corpus construction**, before partitioning
  or running alteration candidates. `test_owner_state_perturb.py:198` calls
  `recovery_recordings`; line 39's `assertGreater(tail['seq'],
  max(record.committed))` raises **`AssertionError: 3 not greater than 3`**.
  Each shard reports `Ran 4 tests` / `FAILED (failures=1)`; the three plant tests
  pass. There are **zero candidate/scenario total lines and zero `slipped=`
  lines** in every shard. This supplies no `slipped=0` evidence; it is not a
  strict-pin failure. The corpus hardcodes local cancel/onboarding offsets
  69/61; the hosted traceback itself does not identify which iteration fails,
  so the failing flow and replacement discovered boundary remain unverified.
- **26 jobs have only a strict-pin unittest failure**: the other two sweep
  jobs and all 24 onboarding jobs. Of these, `onboarding (15)` also logs a
  recovered setup `ReadTimeoutError` from pip fetching `annotated-types`;
  installation then succeeds and the tests finish. It is marked **No** below
  under the request's literal no-timeout condition. No Actions job timed out.
  Thus **25 failed jobs meet the complete pin-only/no-timeout condition**.

No new pin, classification acceptance or proof can follow this capture.
No product, oracle, test, assertion, allowed set or workflow was changed.
No fix, replacement capture, rerun, or extra dispatch was attempted.

### Every capture job

Each job link opens that job's logs. Evidence refers to the downloaded full job
log under `.work/302/capture-44352598226/logs/`; line numbers include timestamps.
**P** = the final `test_all_flows_all_storage_modes_independent_views` failure,
with the traceback through `gaps.py:229`, `assert not errors, errors`, and the
old-pin count/digest diagnostics. **D** = the closed-database subtest error above;
**A** = the alteration corpus assertion above; **T** = the recovered pip timeout.
Each P job has exactly one failure; D counts below are additional errors.
The audit found no other failing Actions step besides the test step, no other
Actions error annotation besides its exit code 1, and no nonzero `slipped` line.
The absence of alteration output is explicitly a blocker, not a passing result.

| Job | Result | Failed only on pin, with no other error/timeout? | Log evidence |
|---|---|---|---|
| [ledger](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017257) | success | N/A — passed | `60_ledger.txt`: 2 tests OK |
| [sweep (0, 0)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017801) | failure | No | `10_sweep (0, 0).txt`: P at 699; D × 12 from 519 |
| [sweep (0, 1)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972020758) | failure | Yes | `2_sweep (0, 1).txt`: P at 416 |
| [sweep (0, 2)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017815) | failure | No | `40_sweep (0, 2).txt`: P at 613; D × 13 from 418 |
| [sweep (0, 3)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972020260) | failure | No | `3_sweep (0, 3).txt`: P at 530; D × 5 from 455 |
| [sweep (0, 4)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018318) | failure | No | `47_sweep (0, 4).txt`: P at 588; D × 11 from 423 |
| [sweep (0, 5)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018382) | failure | No | `44_sweep (0, 5).txt`: P at 553; D × 10 from 403 |
| [sweep (0, 6)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017993) | failure | No | `25_sweep (0, 6).txt`: P at 591; D × 10 from 441 |
| [sweep (0, 7)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017931) | failure | No | `56_sweep (0, 7).txt`: P at 524; D × 5 from 449 |
| [sweep (0, 8)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017697) | failure | No | `24_sweep (0, 8).txt`: P at 512; D × 6 from 422 |
| [sweep (0, 9)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017890) | failure | No | `54_sweep (0, 9).txt`: P at 503; D × 6 from 413 |
| [sweep (0, 10)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017720) | failure | No | `27_sweep (0, 10).txt`: P at 647; D × 14 from 437 |
| [sweep (0, 11)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018343) | failure | No | `6_sweep (0, 11).txt`: P at 557; D × 10 from 407 |
| [sweep (1, 0)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017834) | failure | No | `52_sweep (1, 0).txt`: P at 653; D × 15 from 428 |
| [sweep (1, 1)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017920) | failure | Yes | `33_sweep (1, 1).txt`: P at 424 |
| [sweep (1, 2)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017964) | failure | No | `49_sweep (1, 2).txt`: P at 665; D × 16 from 425 |
| [sweep (1, 3)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017823) | failure | No | `19_sweep (1, 3).txt`: P at 505; D × 5 from 430 |
| [sweep (1, 4)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018002) | failure | No | `0_sweep (1, 4).txt`: P at 602; D × 10 from 452 |
| [sweep (1, 5)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017914) | failure | No | `39_sweep (1, 5).txt`: P at 613; D × 11 from 448 |
| [sweep (1, 6)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017854) | failure | No | `35_sweep (1, 6).txt`: P at 484; D × 5 from 409 |
| [sweep (1, 7)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018347) | failure | No | `13_sweep (1, 7).txt`: P at 755; D × 21 from 440 |
| [sweep (1, 8)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018087) | failure | No | `38_sweep (1, 8).txt`: P at 483; D × 4 from 423 |
| [sweep (1, 9)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017967) | failure | No | `18_sweep (1, 9).txt`: P at 544; D × 8 from 424 |
| [sweep (1, 10)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018243) | failure | No | `9_sweep (1, 10).txt`: P at 511; D × 6 from 421 |
| [sweep (1, 11)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017793) | failure | No | `59_sweep (1, 11).txt`: P at 589; D × 11 from 424 |
| [onboarding (0)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017694) | failure | Yes | `45_onboarding (0).txt`: P at 362 |
| [onboarding (1)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018816) | failure | Yes | `5_onboarding (1).txt`: P at 364 |
| [onboarding (2)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017745) | failure | Yes | `57_onboarding (2).txt`: P at 363 |
| [onboarding (3)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017798) | failure | Yes | `26_onboarding (3).txt`: P at 367 |
| [onboarding (4)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017649) | failure | Yes | `21_onboarding (4).txt`: P at 363 |
| [onboarding (5)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017817) | failure | Yes | `41_onboarding (5).txt`: P at 362 |
| [onboarding (6)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017746) | failure | Yes | `17_onboarding (6).txt`: P at 364 |
| [onboarding (7)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018354) | failure | Yes | `34_onboarding (7).txt`: P at 380 |
| [onboarding (8)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017976) | failure | Yes | `22_onboarding (8).txt`: P at 364 |
| [onboarding (9)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018303) | failure | Yes | `48_onboarding (9).txt`: P at 362 |
| [onboarding (10)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018944) | failure | Yes | `12_onboarding (10).txt`: P at 365 |
| [onboarding (11)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017608) | failure | Yes | `16_onboarding (11).txt`: P at 364 |
| [onboarding (12)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018056) | failure | Yes | `31_onboarding (12).txt`: P at 365 |
| [onboarding (13)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017783) | failure | Yes | `14_onboarding (13).txt`: P at 380 |
| [onboarding (14)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017765) | failure | Yes | `8_onboarding (14).txt`: P at 360 |
| [onboarding (15)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017955) | failure | No | `32_onboarding (15).txt`: P at 376; T at 236 (recovered) |
| [onboarding (16)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018228) | failure | Yes | `11_onboarding (16).txt`: P at 365 |
| [onboarding (17)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018271) | failure | Yes | `29_onboarding (17).txt`: P at 365 |
| [onboarding (18)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017863) | failure | Yes | `51_onboarding (18).txt`: P at 383 |
| [onboarding (19)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017722) | failure | Yes | `36_onboarding (19).txt`: P at 363 |
| [onboarding (20)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018350) | failure | Yes | `46_onboarding (20).txt`: P at 364 |
| [onboarding (21)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017702) | failure | Yes | `1_onboarding (21).txt`: P at 365 |
| [onboarding (22)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017826) | failure | Yes | `30_onboarding (22).txt`: P at 361 |
| [onboarding (23)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017741) | failure | Yes | `58_onboarding (23).txt`: P at 360 |
| [alterations (0)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018151) | failure | No | `7_alterations (0).txt`: A at 399; no alteration totals |
| [alterations (1)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018257) | failure | No | `50_alterations (1).txt`: A at 377; no alteration totals |
| [alterations (2)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018268) | failure | No | `43_alterations (2).txt`: A at 379; no alteration totals |
| [alterations (3)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018401) | failure | No | `23_alterations (3).txt`: A at 380; no alteration totals |
| [alterations (4)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972017752) | failure | No | `55_alterations (4).txt`: A at 380; no alteration totals |
| [alterations (5)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018417) | failure | No | `15_alterations (5).txt`: A at 378; no alteration totals |
| [alterations (6)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018588) | failure | No | `42_alterations (6).txt`: A at 380; no alteration totals |
| [alterations (7)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018785) | failure | No | `4_alterations (7).txt`: A at 381; no alteration totals |
| [alterations (8)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018596) | failure | No | `37_alterations (8).txt`: A at 397; no alteration totals |
| [alterations (9)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018394) | failure | No | `28_alterations (9).txt`: A at 379; no alteration totals |
| [alterations (10)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018050) | failure | No | `53_alterations (10).txt`: A at 382; no alteration totals |
| [alterations (11)](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226/job/134972018477) | failure | No | `20_alterations (11).txt`: A at 378; no alteration totals |

### Lists, old pin, and classification stop

There are **52 fresh actual-list files**, not 53: 48 sweep/onboarding lists,
`contract`, `G22-rename`, `G22-evidence`, and `channel`. The old `G22-latch`
file is absent because that regression now asserts the healthy retry directly
and no longer calls `known_gap`; the regression is **OK** in the capture's
`sweep (0, 0)` in-process five-test run. A subsequent valid capture's inventory
must account for that deliberate artifact-count change instead of inventing
an empty list. These are downloaded individual lists; they have **not** been
accepted as a complete reproduction or merged into a new pin.

Historical proof **43972005458** was downloaded concurrently, before discovery
of the blockers: its 61 artifact directories, 53 full lists, and log archive
are under `.work/302/historical-43972005458/`. **Old-list reproduction was not
run**: the requested step-1 stop precedes assembly and classification. The
existing file itself still has **2,576,083 keys / 1,930 groups / 892,234 bytes**,
format 3, SHA-256
`8b27b1161505ac19eeaa41a6f1a69c95886de5da338249801963a96a083b74b1`.
That file/hash check is not claimed as historical-list reproduction.

**New pin:** not generated; no new keys/groups/bytes/hash exist.
**Classification:** stopped before full key-by-key comparison. N7's 6,949 keys,
the 544 saved envelopes, alias-only changes, the other 376 fixed keys,
M07/C01's whole-pin closures, startup-replay, restore-lock absence, and unrelated
class preservation are **not verified by this run**. The passing G22 regression
and equal point counts do not waive the failed capture gate. Format 3 and strict
exact-delta checking remain unchanged.

### Flow-point counts

Read the `Owner oracle flow=… points=…` lines in every downloaded capture job
and historical proof log; repeated observations of each flow agree. All **34
hosted clean-run counts are identical** between 43972005458 and 44352598226.
This checks counts, not equality of full clean-run traces or all fault sites.
There is no observed count move to explain. The previously recorded local/
hosted onboarding difference remains: 2,570 locally, 2,610 in both hosted runs;
local send is 875, both hosted runs 879. No offset was remapped in this run.

| Flow | Historical proof 43972005458 | Capture 44352598226 |
|---|---:|---:|
| `archive` | 373 | 373 |
| `attachment_export` | 280 | 280 |
| `cancel` | 70 | 70 |
| `delete_permanent` | 420 | 420 |
| `delete_trash` | 282 | 282 |
| `draft_append` | 173 | 173 |
| `expiry` | 69 | 69 |
| `export_rollback` | 280 | 280 |
| `filing_copy` | 353 | 353 |
| `filing_move` | 352 | 352 |
| `filing_rename` | 229 | 229 |
| `flag` | 120 | 120 |
| `folder_create` | 118 | 118 |
| `folder_delete` | 213 | 213 |
| `folder_review` | 173 | 173 |
| `local_flag` | 118 | 118 |
| `maintenance` | 62 | 62 |
| `onboarding` | 2,610 | 2,610 |
| `password` | 131 | 131 |
| `repair` | 366 | 366 |
| `restart_index` | 32 | 32 |
| `restart_tail` | 34 | 34 |
| `restore` | 76 | 76 |
| `send` | 879 | 879 |
| `send_duplicate` | 965 | 965 |
| `settings` | 174 | 174 |
| `settlement` | 157 | 157 |
| `status` | 156 | 156 |
| `testapp_config` | 134 | 134 |
| `testapp_delete` | 282 | 282 |
| `testapp_export` | 147 | 147 |
| `testapp_send` | 391 | 391 |
| `unsubscribe_https` | 350 | 350 |
| `unsubscribe_mailto` | 881 | 881 |

### Commands, verification and handoff

Read-only GitHub commands (all exit 0):

```sh
gh run view 44352598226 --json databaseId,headSha,status,conclusion,jobs
gh api --paginate --slurp repos/Ares-Empire/AresOS/actions/runs/44352598226/artifacts
gh run download 44352598226 -D .work/302/capture-44352598226/artifacts
gh api repos/Ares-Empire/AresOS/actions/runs/44352598226/logs
gh run download 43972005458 -D .work/302/historical-43972005458/artifacts
gh api repos/Ares-Empire/AresOS/actions/runs/43972005458/logs
```

API/log output was saved under those run directories, not printed wholesale.
`python3 .work/302/repin/audit.py` reads every full job log and inventory:
`artifacts=61`, `lists=52`, `pin_only=25`, `blocked_jobs=35`,
`nonpin_errors=226` (214 database errors + 12 corpus assertion failures).
Its one timeout detection is the recovered pip warning described above.
Full per-incident frames and log hashes: `.work/302/repin/capture-audit.json`;
point-count comparison against the historical log was saved there separately.
This is analysis of hosted evidence; **no tests were executed locally**.

**Proof run ID: none.** No workflow was dispatched or watched in this run.
The requested successful status text cannot be set truthfully: re-pin and
proof dispatch were stopped at the explicit non-pin-failure gate.
The lead (`linux-tools`) must settle the two capture blockers and authorize
any replacement capture before re-pin work resumes. The same historical
reproduction, complete delta classification and single-pin gate still apply.

### Left, in order

Before the proof sequence: resolve the rejected capture, obtain complete valid
capture evidence, reproduce the old pin, classify all changes and re-pin.
Then:

1. **Full proof green**, all 61 jobs, fresh lists reproduce the new pin byte
   for byte and every alteration shard reports `slipped=0`; the lead watches it.
2. **Control CI green twice**.
3. Fresh **package and security reviews**, then an independent **classification
   check** against the full historical and fresh lists.

**JUDGMENT-CALL:** none. **PLAN-GAP:** capture inventory falls from 53 to 52
files when the G22-latch gap is replaced by its direct passing regression;
this must be accounted for explicitly when resuming. **Open:** the closed-db
startup capture and hosted applied-tail corpus boundaries above.

Closing checks: `git diff --check` passes; the repository privacy script prints
`No file holds a home path with a real user name.` No files over 500 MB remain
under `.work/`; downloaded capture and historical evidence together are below
2 GB. No Gradle process was started. No OS, installed/root test, boot, mount,
sudo, live-service action, process termination, or additional workflow dispatch.

---

## Build part 4

Status: **Build part 4 done; capture 44352598226 dispatched; next: the re-pin**.

### Three PLAN-GAPs closed

Started at `680e85ea`, branch `pkg/302-store-oracle`, existing draft PR #111.
The lead's part-3 decisions are implemented; production service code is unchanged.

- **M07/C01, `13839137`:** `Oracle.expected.failed_recheck` now uses the same
  independent `latch_refusal_first` rule as status/request-state checks, in
  addition to fresh physical faults. A live recheck refused without a fresh
  fault still expects the conservative Sent-copy unchecked notice. It uses the
  physical transaction record during alterations, never the returned error or
  Store's latch flag. New test
  `WriteLatch302.test_live_sent_copy_recheck_refused_by_latch_without_a_fresh_fault_is_unchecked`
  pins that case and passive/read-only/healthy controls (four subcases).
- **m17, `1546da20`:** the applied-tail sweep selects the outer Driver call
  independently of the nested Engine request and requires its start/end range
  to include the applied event. Later status reads cannot stand in for the
  producing call. The named mutation now fails with **`5 not greater than or
  equal to 6 : Outer producing call must include its applied event`**.
- **m15, `1546da20`:** the latch status sweep now rejects returned operation-row
  differences in approval, stages and state. Refused reads' absent rows remain
  covered by the existing status checker; they are not returned row values.
  Promoting all prepared events now fails **`Returned status rows must match
  applied history`**, starting at `cancel/single/24/0/live-restored/operation-state`.

### Verification and mutation reruns

Disposable tracked-source exports remain under `control/test-work/302-exports/`,
with no dot-prefixed ancestor. Logs and exact patches are under `.work/302/`.
The existing runner supplies the documented managed-settings stand-in, an
exported absolute PYTHONPATH, separate base/Mail import order, repo-local TMPDIR
and disabled bytecode. FilePolicy is unchanged. Python commands below all used
`PYTHONDONTWRITEBYTECODE=1`.

- Before merge: `python3 .work/302/base-only.py control/test-work/302-exports/part4 base test_owner_state_oracle test_owner_state_fixes_s2 test_mail_ci_selection`:
  **174 tests OK**, 1.556 s (`part4-base.log`), without Mail helper imports.
- Initial `run.py ... part4 mail sweep-units`: **16 tests, one failure**, 271.085 s
  (`part4-sweep-initial.log`). My first outer-call selector also selected a later
  same-action status read. It now requires a call starting before the event;
  the end-bound assertion stays independent. Focused rerun of
  `OwnerStateSweep.test_applied_tail_views_keep_the_producing_call_and_restart_never_resubmits`:
  **1 test OK**, 77.302 s (`part4-tail-final.log`): 48 cases, 76 cleanup runs,
  56 live applied records, 62 preserved restart envelopes, six discovered flows.
  The full final suite below reruns all 16 sweep unit tests successfully.
- `OWNER_MUTATION_ROUND=part4 python3 reviews/20-store-oracle-followups/mutations.py m04 m07 m14 m15 m17 m18 m25 m27`:
  exit 0; **8 patches, 13 passing baseline invocations, 13 assertion kills**.
  Includes both survivors and every probe affecting the changed model rule or
  named sweep assertions, plus the new rule's direct removal (m27). There are
  no import, fixture, pin or other invalid failures. Exports are restored and
  patch SHA-256 values match. Part 3's receipts/logs are preserved separately.

| ID | Mutation | Baselines passed / assertion kills |
|---|---|---:|
| m04 | Replay old storage cause on later latched request | 3 / 3 |
| m07 | Infer latch from any call fault, including read/admission faults | 2 / 2 |
| m14 | Ignore applied tail and project marked rows only | 2 / 2 |
| m15 | Promote every prepared event without application proof | 2 / 2 |
| m17 | End producing call at marked sequence, leaving applied event to later reads | 1 / 1 |
| m18 | Accept unscripted cancellation and acknowledgement | 1 / 1 |
| m25 | Use marked boundary for all call attribution, moving applied event to later capture | 1 / 1 |
| m27 | Ignore live recheck latch refusal without a fresh physical fault | 1 / 1 |

Exact child commands, failure lines, source commit, log paths and patch hashes:
[mutations-part4.json](mutations-part4.json). Evidence commit: `52255786`.
Parent log: `.work/302/part4-mutations.log`; patches/logs: `.work/302/part4/`.

### Compact sample: eight keys closed; additional closures explained

`python3 .work/302/sample.py control/test-work/302-exports/part4pre mail .work/302/part4-before-main`:
**104 runs, 187 checked phases, 1,444 keys** (`part4-sample-before-main.log`).
Against part 3's 1,528 keys: **84 closed, 0 changed, 0 new, 1,444 identical**.
All eight keys in [new-key-classification.json](new-key-classification.json) close.
All seven complete clean traces are byte-identical.

The other **76 closures have the same M07/C01 cause**, not unrelated drift or
another row-visibility fix. The complete 84 are 42 repair and 42 send keys, at
364/365 and 873/874 respectively, in six live/exhausted phases per flow. There
are 36 count discrepancies (model 0 / public 1) and 48 extra unchecked notice
fact discrepancies across log heads, pending heads and catalogue pages/completeness.
The eight identified in part 3 were the keys newly exposed by item 3; existing
instances of this expectation omission also close when the shared rule is fixed.

The first delta diagnostic assumed only eight closures and rejected 84. Before
settling the sample, `python3 .work/302/part4-closures.py control/test-work/302-exports/part4pre mail ignored`
replayed all affected live cases and asserted **every formerly failing page**:
expected equals actual, fresh fault trace empty, write attempted, latch check
recorded, independent latch rule true, and checked Sent-copy rows still in the
Store. Exit 0: `84 closed keys: every former failing page now agrees; each has a
write attempt, a latch refusal and no fresh fault; checked Sent-copy rows retained`.
Full per-key evidence: `.work/302/part4-closure-evidence.json`.

`python3 .work/302/part4-delta.py .work/302/after-item3-final .work/302/part4-before-main .work/302/part4-sample-delta.json eight`
then verifies the target eight are a subset, the exact closed set equals the
independently traced set, no other delta, and all clean traces match. This is
sample classification, not a broadened pin or a whole-pin M07/C01 total. Keep
these additional closures separate from N7 in the full classification.

### Main merge and drift gate

- `git fetch origin`: exit 0. Fetched main `fef66186`; normal merge `947606b8`
  (`git merge --no-ff origin/main`), no conflicts. The five commits since part 1's
  baseline `4a6acc2e` change shell/laptop-home docs, OS shell code/tests and mod
  fixtures. Diff under **all `control/` and `.github/workflows/` is empty**;
  production, oracle, tests and capture workflow therefore retain the same code.
  The branch's production service code is also unchanged from part 3.
- Inspected #109 (`89801940`) and #97 (`4737bb69`), already in the part-1
  baseline. #109's channel caller uses `['cli', 'control', 'log', ...]`; CLI and
  help reserve `newest`. The oracle still compares the historical **`aresos log`**
  label by directly calling `control_log`. #97's stopped-clock idle checks,
  independent timing bounds and CI `--init` are retained. Installed-channel
  execution belongs to the hosted ledger; it was not run on the laptop.
- After merge: `python3 .work/302/base-only.py control/test-work/302-exports/part4end base test_owner_state_oracle test_owner_state_fixes_s2 test_mail_ci_selection test_cli test_reserved_words test_service_fixes.IdleLoop`:
  **187 tests OK**, 3.806 s (`part4-post-main-base.log`).
- `python3 control/generate.py --check`: exit 0, **`Generated artifacts match definitions`**
  (`part4-generated.log`).
- `python3 .work/302/final-mail.py control/test-work/302-exports/part4end mail`:
  **42 tests OK**, 403.982 s (`part4-post-main-mail.log`): ordinary owner
  contracts, quiet, G22/regressions, S2 effects, plants, and every sweep unit
  test (only the full matrix is left to the capture). Includes the strengthened
  m15/m17 checks, startup replay, failed-cleanup pairs and immutable envelopes.
- `python3 .work/302/sample.py control/test-work/302-exports/part4end mail .work/302/part4-after-main`:
  **104 runs, 187 checked phases, 1,444 keys** (`part4-sample-after-main.log`).
  `python3 .work/302/part4-delta.py .work/302/part4-before-main .work/302/part4-after-main .work/302/part4-main-drift.json same`:
  **0 closed, 0 changed, 0 new, 1,444 identical**; seven clean traces byte-identical.
  No unrelated key or point drift. No startup-replay or restore-lock keys.

Tracked sample deltas, all 84 closure keys and trace hashes:
[sample-part4.json](sample-part4.json). Clean point counts remain restore 76,
cancel 70, onboarding 2,570, repair 366, status 156, archive 373, send 875.
The known hosted/local onboarding difference remains for the same-runtime full
capture comparison; no local point was remapped or skipped.

### Capture handoff

Baseline settled. Dispatched exactly one full capture on pushed commit
`e52ae87b4469e6f794dc01aee0f8c19ecc2b4851`:

```sh
gh workflow run control-owner-oracle.yml --ref pkg/302-store-oracle -f ledger_only=false
```

Capture run ID: **[44352598226](https://github.com/Ares-Empire/AresOS/actions/runs/44352598226)**.
The dispatch exited 0 and returned that URL. There was no earlier dispatch on
this branch; no other workflow was dispatched. The builder records and pushes
this ID, then stops without watching, waiting for, or downloading the capture.
`linux-tools` watches it. The strict old-pin failure is expected capture
evidence; no full-pin or CI-green claim is made here.

### Left, in order

1. Download the capture's **53 fresh lists**, reassemble without conflicting
   shared keys, verify the historical lists reproduce the old pin, and classify
   every closed/changed/new/unchanged delta (including the 544 saved envelopes,
   aliases, point counts and these M07/C01 closures).
2. **Re-pin once** with the gap tool; commit the new pin and exact classification.
3. Dispatch and watch the **full proof** on that pin: all 61 jobs pass, fresh 53
   lists reproduce it byte for byte, every alteration shard has `slipped=0`.
4. Required **Control CI twice**.
5. Fresh **package and security reviews**, then the independent **classification
   check** against the full historical/fresh lists.

No new product judgment call; the lead's three cheap contract fixes are complete.
No FilePolicy, approval, storage/schema, restore-lock policy or service change.
The pin is unchanged: SHA-256 `8b27b1161505ac19eeaa41a6f1a69c95886de5da338249801963a96a083b74b1`.
Final `git diff --check` and repository privacy check pass. Closing scan of
`.work/` and `control/test-work/`: **no files over 500 MB**. No large downloads.
No mod/Gradle, installed-channel/root, OS owner-module, boot, mount, sudo or
live-service work; no other workflow dispatch. Capture/proof watching is left
to the lead and subsequent run as requested.

---

## Build part 3 (step 5)

Status: **Build part 3 done; next: step 6**.

### Scope and result

- Started at `5716bb2a` on `pkg/302-store-oracle`, existing draft PR #111.
  `git fetch origin` exited 0; main is `fef66186`. Its changes since this
  branch's base are in unrelated STATE, laptop-home/shell, OS and mod fixture
  files. The intersection with this branch's changed paths is empty. No merge.
- Ran all 14 reviewer-mutation purposes, expanding the independent alternatives
  and decoded-lock terms to **26 patches**. **37 baseline invocations passed**;
  **35 mutant invocations failed named assertions**, and **2 passed**. By patch,
  **25 were killed and 1 survived**; m15 was killed by the decoder but survived
  its additional status sweep. The surviving checks are findings below. No
  product, oracle, test, FilePolicy or pin was changed to kill them.
- Added `mutations.py` and `mutations.json` here for replay and exact receipts.
  Each patch has its command, baseline, result, failure excerpt, local full-log
  path, SHA-256 and restoration check. Each test ran on unchanged source first,
  then one mutant. Every mutated export source was restored and byte-compared.
  Exports are under `control/test-work/302-exports/step5-*`; their resolved
  paths have no dot-prefixed ancestor. Patches/logs stay in `.work/302/step5/`.
  The runner uses the documented managed-settings stand-in, ordered base/Mail
  paths, exported absolute PYTHONPATH, no bytecode and local TMPDIR. One worker.
- Mutation evidence commit: `32f1353c`; the closing documentation commit adds
  the eight-key classification and this handoff. All executable AresOS sources
  still match the tested starting head.

### Every mutation

Full test IDs and exact commands are also in [mutations.json](mutations.json).
Failure cells quote the first assertion line (long envelopes abbreviated); full
outputs remain at the receipt's log path. `OK` means a surviving named check.

| ID | Patch, in one line | Named test | Killed or survived | Failure line |
|---|---|---|---|---|
| m01 | First-fence catch: `write_failed = False` → `True` | `test_owner_state_regressions.ReviewRegressions.test_review22_zero_byte_journal_enospc_recovers_without_restart_M10_M13`<br>`test_owner_state_sweep.WriteLatchSweep302.test_latch_phases_cleanup_pairs_and_restart` | killed<br>killed | `AssertionError: False is not true : {'ok': False, 'error': {'code': 'journal_incomplete', 'message': 'A storage write did not finish. Fix the storage problem, then ask the owner to restar…`<br>`AssertionError: False is not true : {'ok': False, 'error': {'code': 'journal_incomplete', 'message': 'A storage write did not finish. Fix the storage problem, then ask the owner to restar…` |
| m02 | `Observations.require_writable()` → `return` | `test_review_fixes_24.Filing24.test_failed_predispatch_flush_blocks_effect_until_next_request` | killed | `AssertionError: 1 != 0 : Failed flush must cause zero SMTP DATA` |
| m03 | `_append` failure: `write_failed = True` → `False` | `test_review22_storage.Journal22.test_first_fence_fsync_rollback_and_later_phase_failures`<br>`test_restore_batches.RestoreBatches.test_confirm_whose_marker_stays_after_a_failed_sync_keeps_the_lock_until_a_restart` | killed<br>killed | `AssertionError: False != True`<br>`AssertionError: 0 != 1` |
| m04 | Later refusal: raise `storage_cause` before `journal_incomplete` | `test_review22_storage.Journal22.test_first_fence_fsync_rollback_and_later_phase_failures`<br>`test_restore_batches.RestoreBatches.test_confirm_whose_last_marker_sync_fails_keeps_the_lock_until_a_restart`<br>`test_owner_state_sweep.WriteLatchSweep302.test_latch_cases_use_the_same_status_checker_in_every_phase` | killed<br>killed<br>killed | `AssertionError: 'storage_limit' != 'journal_incomplete'`<br>`AssertionError: {'code': 'storage_limit', 'message': 'Disk full or [291 chars]ge.'} != {'code': 'journal_incomplete', 'message': 'A storag[184 chars]ge.'}`<br>`AssertionError: Lists differ: ['cancel/persistent/1/0/exhausted/response[9933 chars]tus'] != []` |
| m05 | Disable the `finish` restart-advice guard with `False and` | `test_review22_storage.Journal22.test_first_fence_fsync_rollback_and_later_phase_failures`<br>`test_review23_results.ResponseSchemas23.test_first_storage_error_notes_and_restart_advice_survive_bounding` | killed<br>killed | `AssertionError: False != True`<br>`AssertionError: 0 != 1` |
| m06 | `finish` first error code → `'journal_incomplete'` | `test_review22_storage.Journal22.test_first_fence_fsync_rollback_and_later_phase_failures`<br>`test_review23_results.ResponseSchemas23.test_first_storage_error_notes_and_restart_advice_survive_bounding` | killed<br>killed | `AssertionError: 'journal_incomplete' != 'storage_limit'`<br>`AssertionError: 'journal_incomplete' != 'storage_error'` |
| m07 | `latch_refusal_first`: any nonempty call faults → `True` | `test_owner_state_oracle.WriteLatch302.test_fault_count_read_only_and_admission_failures_are_not_latch_evidence`<br>`test_owner_state_oracle.WriteLatch302.test_journal_phases_and_actual_cleanup_determine_the_latch` | killed<br>killed | `AssertionError: 'journal_incomplete' unexpectedly found in {'journal_incomplete'}`<br>`AssertionError: Items in the first set but not the second:` |
| m08 | Remove `journal_scopes = {}` from `Driver.restarted` | `test_owner_state_sweep.WriteLatchSweep302.test_latch_phases_cleanup_pairs_and_restart` | killed | `AssertionError: Tuples differ: (JournalAttempt(phase='fence', sequence=6,[521 chars]lse)) != ()` |
| m09 | Special staged-restore startup condition → `False and …` | `test_owner_state_sweep.OwnerStateSweep.test_startup_replay_proof_precedes_any_automatic_confirm` | killed | `AssertionError: Lists differ: [{Fact(source='op:4d9298963f0d492190981daa[8545 chars]e')}] != []` |
| m10 | Special startup: replace `_replay(prepared)` with `locked = False` | `test_restore_batches.RestoreBatches.test_startup_finishes_staged_final_confirm_without_another_confirmation`<br>`test_owner_state_sweep.OwnerStateSweep.test_startup_replay_proof_precedes_any_automatic_confirm` | killed<br>killed | `AssertionError: 2 not greater than or equal to 4`<br>`AssertionError: Lists differ: [{Fact(source='op:4d9298963f0d492190981daa[8053 chars]"')}] != []` |
| m11 | Special startup: append commit marker and advance committed, omit apply | `test_restore_batches.RestoreBatches.test_startup_finishes_staged_final_confirm_without_another_confirmation`<br>`test_owner_state_sweep.OwnerStateSweep.test_startup_replay_proof_precedes_any_automatic_confirm` | killed<br>killed | `AssertionError: 2 not greater than or equal to 4`<br>`AssertionError: Lists differ: [{Fact(source='generation', kind='wrong-st[7051 chars]}')}] != []` |
| m12 | After intermediate replay: delete pending, change generation, unlock | `test_restore_batches.RestoreBatches.test_startup_finishes_only_the_staged_intermediate_batch` | killed | `AssertionError: None != True : restore_pending` |
| m13 | Remove clearing `startup_obligation` after its check | `test_owner_state_oracle.StartupObligations.test_driver_checks_before_requests_consumes_once_and_second_restart_has_no_old_obligation` | killed | `AssertionError: StartupReplay(event='{"action":"control_restore_confirm","record":{"format":2,"hash":"2f7bdb72784d2269830343ca2298108c07ad70de99138865d75ee026b8bcad8e","operations":[],"pr…` |
| m14 | `visible_history` → marked `record.events` only | `test_owner_state_oracle.AppliedHistory.test_decoder_applied_tail_matrix_and_missing_projection_row`<br>`test_owner_state_sweep.OwnerStateSweep.test_applied_tail_views_keep_the_producing_call_and_restart_never_resubmits` | killed<br>killed | `AssertionError: False != True`<br>`AssertionError: Items in the second set but not the first:` |
| m15 | `visible_history` → all `events + prepared`, unconditionally | `test_owner_state_oracle.AppliedHistory.test_decoder_applied_tail_matrix_and_missing_projection_row`<br>`test_owner_state_sweep.WriteLatchSweep302.test_latch_cases_use_the_same_status_checker_in_every_phase` | killed<br>survived | `AssertionError: True != False`<br>`OK (mutant survived)` |
| m16 | Applied-tail head check: compare sequence only, omit hash | `test_owner_state_oracle.AppliedHistory.test_decoder_applied_tail_matrix_and_missing_projection_row` | killed | `AssertionError: True != False` |
| m17 | Outer `Driver.observe.end_seq` → maximum marked sequence | `test_owner_state_sweep.OwnerStateSweep.test_applied_tail_views_keep_the_producing_call_and_restart_never_resubmits` | survived | `OK (mutant survived)` |
| m18 | `scripted_transition` → `True` for cancellation/ack suffixes | `test_owner_state_oracle.AppliedHistory.test_applied_cancellation_and_acknowledgement_still_require_exact_script_identity` | killed | `AssertionError: False is not true : set()` |
| m19 | `precommit` uses applied rows and applied `before_seq` | `test_owner_state_oracle.AppliedHistory.test_applied_context_cannot_authorize_a_remote_command_before_its_marker` | killed | `AssertionError: 2 != 1` |
| m20 | Recompute → `changed.locked = record.locked` | `test_owner_state_oracle.StartupObligations.test_every_decoded_lock_term_and_wrong_input_recompute` | killed | `AssertionError: False is not True` |
| m21 | Disable `restore_pending` decoded-lock term | `test_owner_state_oracle.StartupObligations.test_every_decoded_lock_term_and_wrong_input_recompute` | killed | `AssertionError: False is not True` |
| m22 | Missing-head decoded-lock result → `False` | `test_owner_state_oracle.StartupObligations.test_every_decoded_lock_term_and_wrong_input_recompute` | killed | `AssertionError: False is not True` |
| m23 | Remove head-hash comparison from decoded lock | `test_owner_state_oracle.StartupObligations.test_every_decoded_lock_term_and_wrong_input_recompute` | killed | `AssertionError: False is not True` |
| m24 | Remove behind-marker comparison from decoded lock | `test_owner_state_oracle.StartupObligations.test_every_decoded_lock_term_and_wrong_input_recompute` | killed | `AssertionError: False is not True` |
| m25 | Shared `staged_sequence` → maximum marked sequence | `test_owner_state_sweep.OwnerStateSweep.test_applied_tail_views_keep_the_producing_call_and_restart_never_resubmits` | killed | `AssertionError: False is not true : (6, [])` |
| m26 | Remove empty-fence decoded-lock guard | `test_owner_state_oracle.StartupObligations.test_every_decoded_lock_term_and_wrong_input_recompute` | killed | `AssertionError: True is not False` |

### Findings and verification details

- **m17 survived** `OwnerStateSweep.test_applied_tail_views_keep_the_producing_call_and_restart_never_resubmits`:
  the outer Driver call ends at the marked sequence, but the nested recorded
  Engine request still ends at the staged sequence. The assertion only requires
  *any* same-action call to own the event, so the inner call masks the wrong outer
  range. That named ordering test should independently check the outer producing
  call as well. The broader m25 changes the shared boundary used by both records
  and is killed by `AssertionError: False is not true : (6, [])`. m17's pass is
  retained as a coverage finding, not counted as a kill by m25.
- **m15 survived the additional**
  `WriteLatchSweep302.test_latch_cases_use_the_same_status_checker_in_every_phase`.
  Both runs check 154 runs / 275 phases and report OK. Other recorded gaps grow
  from **3,598 to 3,943**; only status and restore-lock lists are asserted empty.
  That test needs an explicit staged-but-unapplied row expectation if it is to
  serve as the brief's sweep control for this mutation. The independent decoder
  matrix does kill m15 at its visibility assertion. No allowed set was broadened.
- The broad-clear m03's first extra latch-phase sweep stopped at `KeyError:
  'error'` when an invalid retry succeeded, then Chrome rejected the corrupted
  history. That is **invalid assertion evidence**, not a surviving mutant or a
  semantic kill. It is retained as `invalid-m03-2-{baseline,mutant}.log` and
  `invalid-m03-sweep-receipt.json`. The runner now rejects non-assertion failures.
  The final m03 receipt reruns a fresh baseline and the named failed-marker-
  rollback confirm test; both it and the store phase table kill m03 on assertions.
  This did not require editing a test or the product.
- Barrier m02 fails all **six** zero-DATA variants (before dispatch/after
  admission × zero/short/fence-sync): `1 != 0 : Failed flush must cause zero SMTP
  DATA`. Its baseline passes the healthy next request without restart.
- Skipped startup m09 fails the pre-confirm proof at **26, 40 and 73 in both
  modes**. Its output ends `startup-replay must finish before any automatic
  confirm`, with missing marker/head/effects/generation/lock facts. m10 and m11
  independently fail the exact applied-head Store assertion and that startup
  proof. m12 fails the retained intermediate `restore_pending` assertion.
- Baseline applied-tail sweeps discover cancel 68, onboarding 61, repair 364,
  status 154, archive 231 and send 873: **48 cases, 76 cleanup phase runs,
  56 live applied records, 62 preserved restart envelopes**. m14 removes all six
  flows' applied-record coverage and fails the final set equality. The decoder
  separately rejects marked-only, every-prepared and missing-head-hash mutants.

Commands from the worktree root (the receipts list every child command):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 reviews/20-store-oracle-followups/mutations.py
PYTHONDONTWRITEBYTECODE=1 python3 reviews/20-store-oracle-followups/mutations.py m03 m25 m26
PYTHONDONTWRITEBYTECODE=1 python3 .work/302/classify-new.py control/test-work/302-exports/step5-classify mail ignored
PYTHONDONTWRITEBYTECODE=1 python3 .work/302/restart-count-controls.py control/test-work/302-exports/step5-classify mail ignored
PYTHONDONTWRITEBYTECODE=1 python3 .work/302/run.py control/test-work/302-exports/step5-classify base test_owner_state_oracle.AppliedHistory.test_coherent_applied_identity_outcome_and_missing_effect_are_rejected test_owner_state_oracle.AppliedHistory.test_coherent_applied_identity_deletion_reaches_semantic_checker test_owner_state_oracle.OwnerOracle.test_r2_command_before_context_is_caught
```

- Mutation parent commands: exit 0; final outcomes are the table above, **not an
  all-mutants-killed claim**. Parent logs: `step5-run.log`, `step5-followup.log`.
- Classification: exit 0, `diagnostic records 8 all eight exact sample deltas
  reproduced` (`step5-new-key-classification.log`). Raw rows, calls and replies:
  `step5-new-key-diagnostics.json`; independent repeated deltas:
  `step5-new-key-gaps.json`. These are synthetic recordings.
- Three corresponding healthy-restart controls: exit 0, `3 healthy-restart
  controls: zero count, startup-replay or restore-lock gaps; other keys: 0`
  (`step5-restart-count-controls.log`).
- Coherent applied identity/outcome/effect, identity deletion and existing R2
  command-before-context controls on restored source: **3 tests OK**, 0.009 s
  (`step5-coherent-context-controls.log`). These are additional passing controls,
  not mutant kills.

### The eight new sample keys: classification for step 6

All eight are **real residual oracle-expectation gaps exposed by item 3**, in
**M07/C01 (Sent-copy checks and their live recheck refusal)**, not sample or alias
artifacts. This is a classification of the compact sample's **825 closed /
147 changed / 8 new** delta; it does not establish the whole pin's new total or
membership. Each repeated delta is **model count 0, public count 1**.

| New key | Classification |
|---|---|
| `send/persistent/873/0/exhausted/control_pending.notice-count` | M07/C01; real oracle gap, no sample artifact |
| `send/persistent/873/0/exhausted/mail catalogue.total` | M07/C01; real oracle gap, no sample artifact |
| `send/persistent/873/0/live-restored/control_pending.notice-count` | M07/C01; real oracle gap, no sample artifact |
| `send/persistent/873/0/live-restored/mail catalogue.total` | M07/C01; real oracle gap, no sample artifact |
| `send/single/873/0/live-restored/control_pending.notice-count` | M07/C01; real oracle gap, no sample artifact |
| `send/single/873/0/live-restored/mail catalogue.total` | M07/C01; real oracle gap, no sample artifact |
| `send/single/874/0/live-restored/control_pending.notice-count` | M07/C01; real oracle gap, no sample artifact |
| `send/single/874/0/live-restored/mail catalogue.total` | M07/C01; real oracle gap, no sample artifact |

At each key, the last ordinary event is `mail_send`, sequence **17**, SQLite's
head is **17**, and the last marker is **16**. The corrected model and raw SQLite
both show **done**, `sent_copy_check = {state: checked, clean: true}`. Part 1's
sample still projected **submitting** at that boundary. Item 3 correctly removes
that false N7 row discrepancy.

A later `control_pending` or `mail_filing_notices` request tries to open a fresh
Sent-copy check. Its trace records a write attempt and latch check **0**, an
empty fresh fault trace, and `journal_incomplete`. The service conservatively
returns the `sent_copies` unchecked notice because the new check cannot be
registered/committed. `Oracle.expected`'s `failed_recheck` only considers a fresh
physical fault trace; with the now-visible checked row and no such trace, it
expects no notice. The old incorrect submitting row made its count happen to
match. This exposes an independent live-check expectation gap; it does not show
that the applied row should be hidden again.

Keep it separate from item 1's newly permitted safe-rollback writes, startup
obligations, and N7's false marked-versus-applied row discrepancy. The generated
count-only matrix row is still **M14** because `gaps.checker` sees only catalogue
count facts. That fallback label is not evidence of M14's hidden rows under a
restore lock: these records are unlocked, and no startup/restore-lock key is
new. Do not silently relabel unrelated whole-pin keys. Step 6 and its independent
checker must match fresh full lists to this semantic cause; a key can retain
another defect after the N7 component closes, as the brief explicitly allows.

Machine-readable per-key evidence and exact deltas:
[new-key-classification.json](new-key-classification.json). All eight reproduce
in a fresh, unmutated tracked-source export; all three corresponding healthy
restart controls converge with no recorded gaps. No classification code, pin or
product was changed to erase these eight keys.

### Left, in order

1. **Step 6:** fetch/integrate current main as required, settle any runtime/point
   drift with linux-tools, re-pin once from the full capture, classify exact
   deltas (including these residuals and saved envelopes), and run the full proof
   plus required Control CI green twice. The part-1 hosted/local onboarding
   difference remains for that same-runtime capture. No capture/proof dispatch
   or CI wait was performed here.
2. A **fresh package review and fresh security review** of the resulting build,
   including the surviving checks and invalid sweep evidence above.
3. An **independent classification check** against the full historical/fresh
   lists. This run supplies the eight sample classifications, not that review.

### JUDGMENT-CALLs

No new product decision. Applied rows, owner approvals, restart policy, schema,
journal format and FilePolicy remain as built in parts 1/2. Keeping survivors
visible and deferring fixes follows this run's explicit scope.

### PLAN-GAPs

- The named H ordering sweep permits the correct nested request to mask an
  incorrect outer call boundary (m17). Its assertion does not fully pin the
  producing-call distinction the brief describes.
- The latch status sweep records row differences rather than asserting their
  absence (m15); it cannot supply staged-only visibility rejection on its own.
  Its direct error indexing also prevents the broad-clear mutant from reaching
  a clean sweep assertion. The decoder/Store kills remain valid; do not promote
  those auxiliary runs into evidence they did not produce.
- Applied clean rows expose a remaining M07/C01 expectation omission for a
  latch-refused live recheck without a fresh physical fault. The generic M14
  count label cannot classify the cause; the eight keys need the separate
  semantic classification above during step 6.

Closing checks: `git diff --check` passes; all export mutations are restored and
all patch hashes match their receipts. No files over 500 MB remain under
`.work/` or `control/test-work/`. No Gradle daemon, mod build, installed-channel
or root test, OS owner module, boot tool, mount, sudo, workflow dispatch or
live-service action was run. The repository's privacy script prints `No file
holds a home path with a real user name.` No CI result is claimed for this run;
CI is left to the lead.

---

## Build part 2 (steps 3 and 4)

Status: **Build part 2 done; next: step 5**.

### Done (commits per step)

- `git fetch origin` succeeded at the start. The fetched main tip `dddc8d58`
  differs from part 1 only in `STATE.md`. No file changed here overlaps, so
  no merge was needed. Branch `pkg/302-store-oracle`, existing draft PR #111.
- Step 3: `6f12f561` (pushed). A canonical immutable before-start restore
  obligation is saved from the full matching event, restore plan and scripted
  confirm precondition. `Driver.started` sends `startup-replay` to the shared
  checker immediately after binding, before views, flushes or another confirm.
  It requires the matching marker, valid applied head, exact event and SQLite
  effects, generation, pending flag and service lock. Intermediate batches finish
  only their saved work and retain generation/lock. Failed starts cannot claim
  readiness; healthy subsequent starts finish the saved event. Obligations end
  after checking, and later restarts cannot inherit an old confirm. Captured
  failed envelopes remain immutable. No production Store change.
- Base-container fixture follow-up: `d425882e` (pushed), after the CI finding
  described below; it changes only two mock tests, not Driver or the real VFS.
- Step 4: `efa70045` (pushed). `records.visible_history` keeps `events` and
  `committed` exact and extends local rows only with an ordinary validated tail
  matching the last fence and applied SQLite head. The event remains prepared.
  Lifecycle, current notices/catalogues, paging, qualification and audit use the
  same history and the same identity/effect/transition proof gates. Archive
  discovery still starts from marked hash-qualified manifests. Restore batches
  retain their separate rule; Chrome's committed projection is unchanged.
- Call ranges use staged sequence; local read evidence uses applied sequence;
  pre-command snapshots/permission and unfinished space plans use marked history.
  An applied event stays with its producing call through its failed envelope and
  restart. Visibility neither authorizes another app command nor releases a
  recovery hold before its marker. This required changing part 1's driver range
  and trace inputs, but not its Store/barrier/advice implementation.
- Alterations mutate applied rows, event versions and coherent row/event/fence
  claims while preserving markers/startup inputs. The corpus appends applied
  cancellation/account tails and staged final/intermediate restores; its four
  new cost entries are measured locally. Rejected prepared candidates still get
  independent fence checks. Identity errors reach semantic comparison before
  malformed encodings interrupt replay; generation/input hash are immutable.
  Fence hashes are checked even when restore lost their working events. These
  redundant encoding checks cannot count as semantic catches of coherent lies.
- Took RECHECK-1's two nits: recompute receives the opposite input lock, and
  the full decoded-lock table covers pending, absent head, hash, behind/equal/ahead
  and empty records. Recompute handles absent heads and preserves a bad head
  hash unless a matching original fence was actually re-encoded.

### Tests and mutation

All execution uses tracked-source exports under
`control/test-work/302-exports/` with no dot-prefixed ancestor. Logs, patches,
scripts and recordings are under `.work/302/`. The runner applies the prior
package's managed-settings `Boundary.read` stand-in, exports absolute PYTHONPATH,
disables bytecode, sets TMPDIR to `.work/302/tmp`, and orders base `tests` before
`mail_tests`; Mail runs separately. No FilePolicy change.

- Step 3 export `step302a`: `PYTHONDONTWRITEBYTECODE=1 python3 .work/302/run.py control/test-work/302-exports/step302a base test_owner_state_oracle test_restore_batches test_review22_storage`:
  **148 tests OK**, 46.613 s (`step3-base-final.log`: 131 oracle, 9 restore,
  8 storage). Driver-only final recheck: **131 OK**, 1.136 s
  (`step3-oracle-final.log`). Restore 1k/10k retained/peak bytes:
  13,785/217,066 and 13,785/217,069.
- Step 3 runner `mail test_owner_state_sweep.OwnerStateSweep.test_startup_replay_proof_precedes_any_automatic_confirm test_owner_state_sweep.OwnerStateSweep.test_discovered_staged_restore_interval_and_cleanup_pairs_replay_at_startup`:
  **2 tests OK**, 97.370 s (`step3-sweep-final.log`). The six named 26/40/73
  cases cover both modes. Discovery examines all 76 clean points: 47 staged-final
  points, endpoints 26/73; 100 single/persistent cases including 25/74/75 controls,
  plus 137 cleanup pairs. All startup proofs empty; no restore-lock gaps.
- Skipped-startup mutation: disposable `skip302a`, only the special startup
  branch condition bypassed (`skipped-startup.patch`). Same named pre-confirm
  test: **1 test FAILED (failures=1)**, 2.569 s
  (`step3-skipped-startup-final.log`). All six cases fail the assertion
  `startup-replay must finish before any automatic confirm`, with missing
  marker/head/effects/generation/lock proof. It is not an import, fixture or pin
  failure. The baseline immediately above passes. Its first attempt passed
  unexpectedly because the new checker had not called `finish()`; added that
  call and a direct raw-proof assertion, then reran both baseline and mutant.
- Step 4 export `step302c`, before the last coherent-input regression: runner `base test_owner_state_oracle test_owner_state_fixes_s2 test_review22_storage test_restore_batches test_mail_ci_selection`:
  **190 tests OK**, 47.453 s (`step4-base-final2.log`: oracle 140, S2 26,
  storage 9, restore 9, CI selection 6). Store coverage includes cancellation,
  acknowledgement and account-like rows at marker failures, single/persistent
  write faults and failed rollback, refused retry without byte changes, visible
  applied rows, staged-only controls, same rows after restart and zero receiver
  arrivals. Decoder/model negatives include head/hash/fence/staging/restore,
  missing rows, unmarked archive manifests, exact cancellation/ack identity,
  coherent identity deletion/generation/input hash/outcome/effect claims, and
  applied context unable to authorize a command before its marker.
- After the final coherent-input fix, runner `base test_owner_state_oracle test_owner_state_fixes_s2 test_mail_ci_selection`: **173 tests OK**, 1.597 s (`step4-oracle-final3.log`: oracle 141, S2 26, CI selection 6). Includes completed/failed marker controls: coherent re-encoding preserves the raw journal history and marker set, and both status/request-state checks retain the original physical latch expectation.
- `PYTHONDONTWRITEBYTECODE=1 python3 .work/302/final-mail.py control/test-work/302-exports/step302c mail`: **42 tests OK**, 433.488 s (`step4-mail-sweep-final.log`): ordinary owner contracts, quiet, regressions, S2 effects and plants (26), plus all sweep unit tests (16), excluding only the full matrix. Final latch coverage: 154 view runs / 275 checked phases, 3,598 other recorded gap keys, and 77 phase/retry/restart variants including 41 cleanup pairs. No status/restore-lock disagreements in those latch assertions. The other gaps are recordings, not a full-pin pass.
- With `mail_tests` removed from both sys.path and exported PYTHONPATH, and an assertion that `storage_faults` cannot be imported, `.work/302/base-only.py` runs `base test_owner_state_oracle test_owner_state_fixes_s2 test_mail_ci_selection`: **173 tests OK**, 1.636 s (`step4-base-only-verified.log`). The startup SQL mock explicitly uses an empty fault scope; the pre-command mock supplies only `ACTIVE=None`. Every assertion remains. Real Mail/VFS tests remain unchanged.
- The new applied-tail sweep discovers marker writes at cancel 68, onboarding
  61, repair 364, status 154, archive 231 and send 873, then exercises each write
  and sync in both modes and live/crash phases: **48 cases + 76 cleanup phase
  runs**. Checks include every view/page/count/envelope, 56 live applied records
  with correct producing-call identity, and 62 restarts with immutable saved
  envelopes and no repeated remote action. Staged-but-unapplied controls remain
  in the latch sweep. Startup coverage still has zero proof/lock gaps.
- `OWNER_PERTURB_SHARD=6 OWNER_PERTURB_SHARDS=12 PYTHONDONTWRITEBYTECODE=1 python3 .work/302/run.py control/test-work/302-exports/step302c mail test_owner_state_perturb.SystematicPerturbations.test_recorded_scenarios_have_no_silent_owner_state_change`: **1 test OK**, 720.004 s (`step4-alteration-shard6-verified.log`): **12 recordings, 183,894 alterations, 21,052 coherent changes, slipped=0**. All seven required alteration kinds occur; the previously failing large onboarding contract passes all 23,070 candidates in its selected part. Includes the applied-tail cancellation recording and all intact/disabled validator controls.
- Focused four-record corpus: `PYTHONDONTWRITEBYTECODE=1 python3 .work/302/new-alterations.py control/test-work/302-exports/step302c mail ignored`:
  **12,284 alterations, slipped=0** (`step4-new-alterations-final4.log`):
  cancel 2,211, onboarding 1,234, staged final 1,264, staged intermediate 7,575.
  Both row-only and coherent claims are checked (202 coherent candidates in the
  two applied-tail recordings). New costs record measured seconds/counts for this focused vocabulary, not
  invented hosted timing. The full shard uses the whole-corpus vocabulary and
  therefore has different candidate counts (cancel 2,631 there). Existing cost weights retain their hosted provenance.

Earlier non-green logs are retained. The initial decoder assertion still expected
an applied unmarked generation to be invisible; changed it to require visibility
while keeping marked/prepared sets separate and adding unapplied controls.
A direct Store application fault raises the raw OSError, unlike Engine's bounded
reply; the store test now checks its mapped original refusal. The new corpus found
silent generation/identity-deletion/lost-fence alterations; the independent and
semantic checks above fix them without weakening an assertion or allowed set.
Its intermediate fixture originally reused one composition and correctly got one
idempotent preparation; distinct synthetic subjects now make 35 operations. An
interim sample exposed eight premature hold releases; fixed by retaining marked
space-plan authority. The first shard attempt was interrupted by its exact PID
(exit 130) before rerunning the final source; it is not evidence of a pass.
The next full shard exposed a phantom latch after coherent hash re-encoding
(`step4-alteration-shard6-final.log`, 1 test failed after 346.524 s). A coherent
writer now preserves the original physical transaction record as independent
input to the existing latch rule, for status and request-state checks. It changes
no raw trace, marker or startup input, and does not weaken the live hash/phase
checks. The focused regression and the final full rerun cover this distinction.

### Compact sample delta against part 1

`PYTHONDONTWRITEBYTECODE=1 python3 .work/302/sample.py control/test-work/302-exports/step302c mail .work/302/after-item3-final`:
**104 runs, 187 checked phases, 1,528 keys** (`step4-sample-final.log`). The 52
additional phases are the new immediate startup checks, all empty. Against
part 1's final `after-item1/sample.json` (2,345 keys): **825 closed, 147 changed,
8 new, 1,373 identical** (`step4-sample-delta-final.json`). Twelve changed keys
are alias-only. Against the original 2,498-key baseline: 978 closed, 151 changed,
8 new, 1,369 identical. All seven complete clean trace files are byte-identical.

| Flow | Closed | Changed | New |
|---|---:|---:|---:|
| archive | 31 | 0 | 0 |
| cancel | 118 | 26 | 0 |
| onboarding | 132 | 18 | 0 |
| repair | 263 | 28 | 0 |
| restore | 54 | 27 | 0 |
| send | 175 | 20 | 8 |
| status | 52 | 28 | 0 |

- Applied rows now agree at H: cancel 69 is `failed` in both store and model;
  onboarding 61/62 includes the saved account. The staged/unapplied controls do
  not become visible. The historical 1439 case still is not the local first
  account boundary, and remains explicitly exercised.
- Restore's 54 closures and 27 changes are after-start lifecycle/row-reason
  corrections from assigning the replayed batch to its original staged confirm.
  The old marked end range excluded that event. No store, restore-lock formula,
  restore-row projection or captured pre-crash record was changed to force it.
- The eight new keys are `control_pending.notice-count` and `mail catalogue.total`
  at send marker 873/874: model 0, store 1, in live/exhausted phases. They expose
  count disagreements after correcting the applied row, not startup/lock gaps.
  No new recovery-hold keys remain. Their whole-pin classification belongs to
  step 6; this sample does not promise N7's historical total or erase other gaps.
- No key ends in `.restore-lock` or `/startup-replay`. The standalone startup
  proof adds coverage rather than an accepted baseline gap. No pin change.

### Push checks

Latest observed push (`d425882e`):

| Workflow | Run | Observed |
|---|---:|---|
| Control boundary | 44339324452 | pending |
| Control Chrome | 44339324376 | queued |
| Control Chrome qualification | 44339324396 | pending |
| Control base | 44339324334 | pending |
| Repo privacy | 44339324446 | pending |
| Control Mail | 44339324269 | queued |

Step 3 (`6f12f561`): Repo privacy **44327232557 passed** and Control boundary
**44327232070 passed**. Control base **44327233131 failed**: 407 tests, one
`ModuleNotFoundError: storage_faults` in the new base-only startup mock. The
local two-path runner had included Mail helpers, masking that missing dependency.
Reading the failed log also led to checking the new applied-context mock without
Mail imports; it had the same dependency. `d425882e` gives only those mocks their
explicit empty inputs. The isolated 173-test recheck above passes. The hosted
retry is pending, not claimed green (`step3-base-ci-failure.log`).

At the same observation, `efa70045` Base/Mail/boundary/privacy/qualification
runs were cancelled and Chrome was queued. Step 3 Mail/qualification were
cancelled and Chrome was queued. Raw observations: `step3-push-checks.json`,
`step4-push-checks.json`, `part2-push-checks-final.json`. No workflow was
dispatched, rerun or awaited past this work; the closing documentation push
changes no executable source.

### Left, in order

1. Step 5: every reviewer mutation on the final build, with passing baselines and exact
   patches/failures in disposable executable exports. The skipped-startup probe
   above is completed; it does not waive the full final-build matrix gate.
2. Step 6: integrate current main, settle drift, re-pin once, full capture,
   pin classification and proof, and required Control CI green twice.
3. The assigned package/security and independent classification reviews.

### What the code doesn't show

Local exports and synthetic fixtures prove no installed/root/channel behaviour,
real owner account/service restart, full sweep/alteration matrix, hosted point
portability or whole-pin classification. Required pushed workflows are reported
only as observed above; no dispatch, rerun or wait past this work. No production
Store/Engine, OS, boot, mount or live-service change, and no mod test is needed.

### JUDGMENT-CALLs

No new product choice; board #352 already approved keeping applied rows visible
and the restart advice. Reversible oracle choices: derive applied history via a
helper rather than another mutable Record projection; keep the canonical startup
obligation on Driver, separate from decoded state; keep permission and space plans
marked while local rows are applied. No schema/journal format or Record exclusion
was added. Changing these later costs test/oracle work, not data migration.

### PLAN-GAPs

- Intermediate restore batches fill their byte limit as well as their row limit:
  the 70-change store fixture's first batch has 30 operations. The test asserts
  the saved batch exactly, retained generation/lock and no invented remaining work.
  Discovery finds 47 staged-final points within 26..73, rather than treating every
  syscall in that interval as identical staged bytes.
- The new alteration corpus exposed validation blind spots in rejected prepared
  claims, coherent missing identity and old fences without working events. These
  needed shared proof checks; copying rows into the final projection or counting
  a format exception as a semantic catch was not sufficient.
- Local visible rows do not finish a space plan. The brief did not name
  `hold_facts`; it must retain marked rights until the marker to avoid introducing
  eight false hold discrepancies. No live reservation or Store code was changed.
- Item 1's raw marker hashes also need independence from item 3's coherent
  fence re-encoding. Otherwise a healthy completed physical write appears latched
  merely because an alteration re-encoded its claim. The original immutable
  transaction record now supplies those inputs; no cached latch flag or returned
  error is used.
- The brief's local base path includes Mail helpers, while the hosted base
  container omits them. That hid two new mock fixtures' imports of the Mail VFS
  module. Explicit empty mock inputs and a no-Mail-path recheck close the gap;
  production fault injection is unchanged.
- Part 1's hosted/local onboarding difference (2,610 versus 2,570 points) remains
  unresolved and explicitly deferred to same-runtime capture/classification.
  All seven local clean traces match part 1 exactly; no point was silently skipped.

Closing scratch scan: no files over 500 MB under `.work/` or `control/test-work/`.
No Gradle daemon was started. No installed/root/channel test, workflow dispatch,
OS owner module, boot tool, mount or live-service action was run.

---

## Build part 1 (steps 1 and 2)

Status: **Build part 1 done; next: step 3**.

### Done

- Step 1: baseline at `4a6acc2e`. `git fetch origin` returned exit 0;
  `HEAD` and `origin/main` both resolve to `4a6acc2e`, so no merge was needed.
  The branch is `pkg/302-store-oracle`. Baseline commit: `2de6da86` (pushed).
- Step 2: `b64eb8f4` (pushed): `_append` reports actual rollback completion; only
  `Store.write`'s first fence can clear the persistent latch. Fresh observations
  hold the request barrier before dispatch and at later writable checks, through
  reply finishing. Failed writes/flushes retain the first cause and queued notice.
  Surviving latches refuse later writes with `journal_incomplete`; restart advice
  is appended once after first-error selection and survives bounded replies.
- The independent oracle records raw fence/marker write, sync and cleanup
  completion, plus the position of a storage check whose decoded inputs were
  already latched. Frozen `JournalAttempt` tuples survive unchanged bytes and
  captured envelopes; restart ends running history. One shared rule supplies
  status and request-state expectations. No store latch flag, returned error or
  fault count supplies the expected latch. Reads need an actual write/check
  attempt to permit a latch refusal. G22 is now an ordinary passing assertion;
  its pin stays untouched until step 6. README/FORMAT document item 1 only.

### The baseline and the sample

Executable tracked-file exports are under ignored
`control/test-work/302-exports/` (no dot-prefixed ancestor). Logs, scripts and
recordings are in `.work/302/`. Tests use the documented managed-settings
`Boundary.read` stand-in, bytecode disabled, absolute `PYTHONPATH` exported for
subprocesses, and `TMPDIR` resolved to `.work/302/tmp`. Base imports put
`control/tests` before `control/mail_tests`; Mail uses the reverse order. The
export needs an empty `.work/` for existing decoder fixtures. FilePolicy is
unchanged. These local exports are test fixtures, not an installed service.

Commands from the worktree root:

- `git archive HEAD control reviews/19b-owner-state | tar -x -C control/test-work/302-exports/baseline`
- `PYTHONDONTWRITEBYTECODE=1 python3 .work/302/run.py control/test-work/302-exports/baseline base test_owner_state_oracle test_review22_storage test_restore_batches`:
  **134 tests OK** (124 + 6 + 4), 42.374 s, `baseline-base-rerun.log`.
  Restore verification printed `(13785, 217066)` / `(13785, 217069)` retained/peak bytes.
  The first attempt ran 134 with 5 fixture errors (export lacked `.work/`);
  `baseline-base.log` retains that failure. No test was changed to fix it.
- `PYTHONDONTWRITEBYTECODE=1 python3 .work/302/run.py control/test-work/302-exports/baseline mail sweep-units`:
  **11 tests OK**, 9.847 s, `baseline-sweep.log`; excludes only the full matrix.
- `PYTHONDONTWRITEBYTECODE=1 python3 .work/302/sample.py control/test-work/302-exports/baseline mail .work/302/baseline`:
  **104 sampled runs, 135 checked phases, 2,498 recorded keys**,
  `baseline-sample-rerun.log`, `baseline/sample.json`, and seven clean traces.
  No key ends in `.restore-lock`. This is a recording, not a strict pin proof.
  The first sample attempt failed because its diagnostic row reads were inside
  injected faults; those diagnostics now use `outside_faults`, without changing
  the sweep's observations or faults.
- `PYTHONDONTWRITEBYTECODE=1 python3 .work/302/baseline-values.py`:
  `Expected baseline row and lock assertions: OK` (`baseline-values-final.log`).
  Direct pre/post-start probes assert the staged final generation without a
  second confirm. Points 26/40/73/74/75 finish unlocked; 25 stays locked.
  Startup can append a recovery event after sequence 6 (head 7), so the probe
  checks completion and the exact staged generation, not an assumed head of 6.
  Earlier probe logs retain its overstrict head/count assertions and corrections.

Clean points and resolved sample boundaries:

| Flow | Clean points | Sample points (write/sync for the selected marker) |
|---|---:|---|
| restore | 76 | 25, 26, 40, 73, 74, 75; cleanup pair 75:76 |
| cancel | 70 | 1, 2, 10, 24, 30, 67, 68, 69; cleanup pair 2:3 |
| onboarding | 2,570 | first account marker 61/62; historical 1439 also exercised |
| repair | 366 | last marker 364/365 |
| status | 156 | last marker 154/155 |
| archive | 373 | last marker 231/232 (later points are export/cleanup) |
| send | 875 | last marker 873/874 |

Every listed non-pair point ran in single/persistent mode and live/crash phases;
cleanup pairs ran in single mode and both phases. Cancel 69/single/live has
head 6, marker 5, prepared event 6: the store shows `failed`, the model
`reserved`, both unlocked. Onboarding 61 in either mode and 62/single shows
one more account than the model (raw fixture totals 2/1; the new-account
catalogue is 1/0). At 62/persistent the marker survives failed cleanup, so both
count 2. Historical 1439 is now in a later transaction, with head/marker 24 and
prepared 25; it does not reproduce the historical account key. Nothing was
silently skipped. Local onboarding still has 2,570 rather than hosted 2,610
points; attribution remains for the later capture on the same runtime.

### Item 1 tests and the barrier mutation

Final executable export: `control/test-work/302-exports/build302/`, whose path
has the same length as the baseline export. Commands use `run.py`'s stand-in and
import ordering described above. Every full matrix is excluded.

- `python3 .work/302/run.py control/test-work/302-exports/build302 base test_owner_state_oracle test_review22_storage test_restore_batches test_review23_results test_journal_closed`:
  **148 tests OK**, 45.782 s (`final-base.log`). The source at that run included
  the store/barrier/advice changes; later oracle-only refinements were rechecked
  with **127 tests OK**, 1.037 s, using the same runner with
  `base test_owner_state_oracle` (`oracle-verified.log`). Restore peaks remain
  217,066 / 217,069 bytes.
- `python3 .work/302/run.py control/test-work/302-exports/build302 mail test_review_fixes_22 test_review_fixes_23 test_review_fixes_24 test_owner_state_regressions.ReviewRegressions.test_review22_zero_byte_journal_enospc_recovers_without_restart_M10_M13`:
  **18 tests OK**, 11.699 s (`final-mail.log`). Includes G22 and the named
  failed-pre-dispatch-flush regression. Its final strengthened test records the
  caught pre-command refusal and asserts it outside Engine's exception handler.
- `python3 .work/302/run.py control/test-work/302-exports/build302 mail test_review24_io test_review_fixes_24.Filing24.test_failed_predispatch_flush_blocks_effect_until_next_request`:
  **3 tests OK**, 3.307 s (`raw-and-barrier-verified.log`): two raw-I/O tests and
  the final named barrier regression (six variants: before dispatch / after
  admission, each zero / short / fence-sync). Each failed request causes zero
  DATA; the next explicit request succeeds without restart, exactly one DATA
  and one APPEND in total. Separate coverage blocks reads and cancellation in
  the failed request and permits their healthy retry.
- `python3 .work/302/run.py control/test-work/302-exports/build302 mail sweep-units`:
  **13 tests OK**, 93.305 s (`sweep-verified.log`). New tests execute **154 view
  runs** (plus clean/discovery helpers), **198 unique checked phase identifiers**,
  **3,994 other recorded gap keys**, and separately **77 phase/retry/restart
  variants including 41 cleanup pairs**. Zero status and restore-lock gaps in
  these cases. Covers both modes, live/exhausted/restarted phases, first fence,
  index, staging, application, H and final confirm. Successful later confirm
  ends the interrupted-confirm flag after safe first-fence rollback.
- Store tests cover zero/short writes, fence fsync, truncate and rollback-sync
  failure, index/staging/application and marker write/sync, ENOSPC/EDQUOT/EIO and
  SQLite FULL/IOERR. They retain failed-write assertions, require healthy explicit
  retry after proven rollback, preserve notes/advice/first error, refuse later
  writes without changing bytes, and verify restart recovery. Both final-confirm
  marker rollback outcomes retain the lock and staged generation; the second
  confirm is `journal_incomplete` with no new write/generation, and restart
  finishes the same generation without another owner confirmation.
- Oracle table: 18 phase/completion/cleanup combinations, read-only/admission
  controls, marker/fence identity, immutable entries, restart bounds, and both
  first-error orderings. Raw read-handle SQLite close faults demonstrably return
  no Python exception; they cannot displace the first propagated refusal.

**Barrier removal mutation:** disposable `mutate02` export; exact patch in
`.work/302/barrier-removal-final.patch`. Changed only the body of
`Observations.require_writable` to `return`, disabling both request gates while
retaining narrow latch clearing and the original final error envelope.

`python3 .work/302/run.py control/test-work/302-exports/mutate02 mail test_review_fixes_24.Filing24.test_failed_predispatch_flush_blocks_effect_until_next_request`:
**1 test, FAILED (failures=6)**, 3.032 s (`barrier-mutation-final.log`). Every
variant fails `1 != 0 : Failed flush must cause zero SMTP DATA`, not an import,
fixture or pin error. The same named baseline passed immediately beforehand in
the 3-test run above. An earlier narrower mutation also failed the three
pre-dispatch zero-DATA assertions (`barrier-mutant.log`); final evidence removes
both gates and catches all six variants.

**Compact sample after item 1:**
`python3 .work/302/sample.py control/test-work/302-exports/build302 mail .work/302/after-item1`:
104 runs / 135 checked phases, **2,345 keys** (`sample-verified.log`,
`after-item1/sample.json`). Compared with baseline: **153 closed, 8 changed,
0 new, 2,337 identical** (`sample-delta-final.json`). All seven full clean traces
are byte-identical, not just equal point counts. Still zero `.restore-lock` keys.

- The 153 closed keys are statuses: cancel 75, onboarding 6, repair 24, status 24,
  send 24. They concern later latch refusals and the new independent expectations.
- Four changed archive status deltas remove `journal_incomplete` from the expected
  set for a read that attempted no write; the existing `stale_reference` defect
  remains. Four cancel 1/2 envelope deltas retain the exact same missing reserved
  row/count mismatch, now repeated on four log pages instead of two. A direct
  before/after audit probe is saved as `audit-delta-{baseline,item1}.log`; live
  checks can now write after safe first-fence rollback, extending the audit log.
- H's row discrepancy remains a control: cancel 69 still shows model `reserved`
  versus store `failed`. Item 2's startup proof and item 3's row correction have
  not been built. No pin change or full-pin classification is claimed.

Earlier non-green logs are retained, not represented as passes: the first oracle
run exposed a hand-built Driver fixture without new trace state and an overly
broad restore-lock status exception; the initial bounds test incorrectly assumed
an already-shortened message needed fragment storage; the first retry sweep
mistook a later read-only close failure for failed journal cleanup. Expanded
samples then found first-error ordering and ignored SQLite-close issues. Those
causes were fixed and tested; no assertion, FilePolicy rule or allowed set was
weakened to hide a pin failure. `git diff --check` passes.

Push checks so far: baseline commit's Repo privacy run **44319148928 passed**.
Control workflows are path-filtered for that documentation-only push.

Draft PR: [#111](https://github.com/Ares-Empire/AresOS/pull/111), against `main`.
After the normal implementation push, the closing read-only Actions query showed:

| Workflow | Run | Observed result |
|---|---:|---|
| Control base | 44324138098 | queued |
| Control boundary | 44324138060 | queued |
| Control Chrome | 44324138069 | queued |
| Control Chrome qualification | 44324138105 | queued |
| Repo privacy | 44324138082 | queued |

Control Mail had not yet appeared in that query; no result is claimed for it.
Raw snapshots are `push-checks-{implementation,closing}.json`. These are
observations, not CI passes. No workflow was dispatched, rerun or awaited past
this work. The closing documentation commit records these results and the
implementation hash; it changes no product or tests.

### Left, in order

1. Step 3: item 2, independent startup obligation and pre-confirm proof.
2. Step 4: item 3, applied history, lifecycle ordering and alterations.
3. Step 5: all remaining mutations.
4. Step 6: merge current main, re-pin once, full capture and proof.
5. Final package/security reviews and independent classification review.

### What the code doesn't show

Local checks use synthetic fixtures and the managed-settings stand-in. They
prove no installed-channel/root behaviour, hosted point portability, whole-pin
classification, full sweep or alteration matrix. No workflow was dispatched.
No OS, boot, mounted-disk, owner-module or mod tests belong to this run.

### JUDGMENT-CALLs

The owner approved the brief's restart advice and continued visibility of saved
rows on board #352. No new product judgment call. Technical choices are reversible:
the rollback fact is an attribute of the raised refusal, consumed only at the
first fence; immutable raw history is stored on Record with an audited exclusion,
and storage-check order on the script. No on-disk format changes.

### PLAN-GAPs

- Existing decoder tests require an export-local `.work/`; added that fixture
  directory. No policy change. Startup's post-replay head can advance beyond
  the final confirm due to normal recovery, so the baseline assertion checks
  the staged generation and matching event instead of head equality.
- Historical onboarding 1439 does not represent the local first account marker;
  exercised it and 61/62 separately. The 40-point hosted difference remains
  unresolved, as the brief anticipated; no pin or point list was rewritten.
- Adjacent `test_journal_closed` and Mail `test_review_fixes_22` also pinned the
  old latch behaviour beyond the named modules. Updated only those expectations
  to the new contract and ran both modules, adding a healthy explicit status retry.
- The brief requires first-error preservation but does not spell out the ignored
  raw SQLite read-close case. Recorded storage-check order, scoped raw faults to
  each request and added an executable raw-I/O control rather than treating every
  fault site as a propagated storage error. Intermediate sample regressions are
  recorded above, with zero new keys after the correction.

Closing scratch scan: no files over 500 MB under `.work/` or `control/test-work/`.
No Gradle daemon was started. No installed/root/channel test, workflow dispatch,
OS owner module, boot tool, mount or live-service action was run.

---

**READY (BRIEF-RECHECK-1); owner answered board #352 "Yes (recommended)"; merged by the lead; next: the build (Codex gpt-6.1-sol xhigh, in the brief's steps)**. Lead: `linux-tools`.
Source baseline: main `4737bb69`, after `git fetch origin` and
`git merge --ff-only origin/main` (from `67bf1909`). Only the brief and this file
are committed. No product code, workflow dispatch or running-service change.

## Revision 1 — 2026-11-18

- **1. The write latch / Decision and exact change / Tests and oracle change:**
  kept the narrow durability predicate, including actual truncate-and-fsync
  success before indexing or SQLite. Added a request-local barrier before
  dispatch and at subsequent writable checks, including caught deferred-flush
  failures. Added the named zero-effects/next-explicit-request regression.
  **Build order and gates / Reviewer mutations** now require its baseline and
  barrier-removal mutation; all earlier mutations remain.
- **What must not change; overlapping work:** named package 43's canonical
  `['cli', 'control', 'log', ...]` channel-test dependency, which `linux-tools`
  lands with 43's Control change. Kept the historical `aresos log` oracle label
  and the re-pin's independence from 43. Updated #98, #97 and #58 (`beb42ec8`)
  to merged, and #72 to `f282553ba631`, retaining its whole-request `call_time`.
  Fetched main was `87d86471`; no merge was made in this brief revision.
- **Build order and gates:** executable exports go under ignored
  `control/test-work/302-exports/`, without dot-prefixed ancestors; logs remain
  under `.work/`. FilePolicy stays unchanged.
- **Question for the owner:** says “the failed save was completely undone,”
  includes the saved-cancellation example and freeing storage/fixing the disk
  followed by restarting the tool service, which resends nothing. “Yes” remains
  recommended because the barrier stops the failed request even after latch
  clearing. Items 2 and 3, the re-pin plan/expected shape and the “What must not
  change” rules are unchanged. No disagreement with `BRIEF-REVIEW-1`.

Checks for this revision (scratch: `.work/revision-302/`; bytecode disabled,
`TMPDIR` resolved inside its `tmp/`; the unit runner also has `PYTHONPATH`
resolved to `control`, `control/tests`, `control/mail_tests` in that order):

- `python3 .work/review-302/probe.py latch`: reproduced `latch-exact.log`:
  baseline zero DATA; narrow latch clear alone one DATA in the failed request.
  `python3 .work/revision-302/barrier-probe.py latch` against this worktree:
  adding the request barrier gave `storage_limit`, zero effects, unchanged
  journal, reserved operation and queued notice; the new healthy request gave
  `ok`, one DATA and one APPEND. Removing the barrier gave one DATA again.
  These are runtime scratch patches, not an implementation of the brief.
- `python3 .work/review-302/cli-probe.py`: removing the shortcut gave exit 2
  and zero proxy calls for `log`; `control log` gave exit 0 and one proxy call.
- `python3 .work/302/unit.py . base tests.test_owner_state_oracle tests.test_review22_storage tests.test_restore_batches`:
  **134 tests OK**, 41.669 s (`units.log`); restore peak bytes 217,066 / 217,069.
- Exported tracked Control and the existing pin with `git archive HEAD` into
  `control/test-work/302-revision-export/`, an ignored path without dot ancestors.
  With `REVIEW302_TREE` pointing there, `python3 .work/review-302/run.py mail test_owner_state_sweep.OwnerStateSweep.test_export_repeated_fault_uses_same_caller_path_and_exact_delta`:
  **1 test OK**, 0.522 s (`export.log`).
- Checked the cited production/test/oracle code, the current #72 engine diff
  and merged-commit ancestry. `git diff --check` passed. Full workflows, new
  implementation tests and the full mutation matrix remain the builder's work;
  none was dispatched or claimed here. No installed-channel, OS or mod tests.
- A structural comparison confirmed items 2/3, the complete re-pin section and
  the “What must not change” rules are unchanged; all 13 earlier mutation rows
  remain, with one barrier mutation added. No files over 500 MB remain under
  `.work/` or `control/test-work/`.

## Original brief evidence

Local evidence, 2026-11-17. Scratch output: `.work/302/current/`.
The unit runner uses the repo's managed-settings stand-in, as the prior package
documents. `TMPDIR` was set to `.work/302/current/tmp` and bytecode was disabled.

- `python3 .work/302/unit.py . base tests.test_owner_state_oracle tests.test_review22_storage tests.test_restore_batches`:
  134 tests, one subprocess import error because `PYTHONPATH` was not exported.
  The 10 storage/restore tests passed. The 1k/10k restore test printed peak bytes
  217,066 / 217,069. `base.log` holds the failure, not a green claim.
- With `PYTHONPATH` containing absolute paths to `control`, `control/tests` and
  `control/mail_tests`, `python3 .work/302/unit.py . base tests.test_owner_state_oracle`:
  **124 tests OK**, 1.093 s (`oracle.log`).
- `python3 .work/302/current/checks.py units`: all 11 unit tests of
  `test_owner_state_sweep` (excluding the full matrix), **OK**, 7.565 s.
- `python3 reviews/20-restore-lock-followups/repro.py` and
  `python3 .work/302/latch.py .`: second requests repeat `storage_limit` after
  faults end; restart clears the latch. The confirm remains locked before restart.
  First-append, fence-only, staged and applied cases were exercised.
- `python3 .work/302/current/checks.py startup`: a targeted test mutation bypasses
  only the staged-restore selection during initialization. At 26, 40 and 73 the
  real store unlocks; the mutant and decoder stay locked with no lock-view gap.
  The final run is `startup-final.log`. Earlier probes were too broad: skipping
  replay alone still cleared the lock and was detected; hiding pending events
  from reservation loading also broke replay at 74. Neither is the final probe.
- `python3 .work/302/current/checks.py h`: cancel at 69 gave head 6 / marker 5,
  store `failed`, model `reserved`, unlocked, write latch set (`h.log`).
- `python3 .work/302/sample.py . .work/302/current/sample.json restore/single/26/0/crash restore/single/73/0/crash restore/persistent/75/0/live restore/single/75/76/crash cancel/single/69/0/live cancel/persistent/68/0/live cancel/single/69/0/crash onboarding/persistent/1439/0/live`:
  8 sampled runs, 205 recorded keys. This is a recording of existing gaps,
  not a green full-sweep result. `python3 .work/302/points.py . restore cancel`
  recorded clean traces: restore 76 points, cancel 70. No sampled key ends in
  `.restore-lock`.
- The historical onboarding 1439 key was absent locally. `python3
  .work/302/current/checks.py onboarding-points` found 2,570 clean points (the
  published proof recorded 2,610). It identified the first account marker at
  61/62. `python3 .work/302/sample.py . .work/302/current/onboarding-h.json
  onboarding/persistent/61/0/live onboarding/single/62/0/live` recorded 64 keys.
  Both show the model counting zero catalogue rows while the store shows one.
  The local/hosted point-count difference has not been attributed to a cause;
  the builder must compare baseline and fixes on the same runtime.
- Both requested three-dot branch diff stats and their shared-file hunks were
  inspected. #98 and #97 were inspected with `git show`. Overlaps are in the brief.
- The current pin's SHA-256 matches `KNOWN-GAPS.md`. N7's historical full-matrix
  counts are attributed to its classification/recheck, not to this small sample.

Not run: full oracle workflow, full alteration matrix, installed-channel tests,
OS or mod tests. No boot tools, mounts, sudo or process-name kills. No file over
500 MB was found under `.work/` during the closing check.
