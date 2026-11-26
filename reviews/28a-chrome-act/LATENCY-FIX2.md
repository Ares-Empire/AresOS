# Step 1d, part 2, fix 2: latency evidence

## Hosted failure on 790d6151

**Run:** [44491713756](https://github.com/Ares-Empire/AresOS/actions/runs/44491713756),
[latency (plain), job 135448895527](https://github.com/Ares-Empire/AresOS/actions/runs/44491713756/job/135448895527).
Read with `gh run view 44491713756 -R Ares-Empire/AresOS --log-failed` and
`gh api repos/Ares-Empire/AresOS/actions/jobs/135448895527/logs --allow-escape-sequences`.
The efficiency and current/plain artifacts supply the samples below; local copies are in
`.work/28a-fix2/efficiency/` and `.work/28a-fix2/latency-plain/`.

The failing call is `chrome_read {tab, find: "Quarterly zebra report", role: "link"}`
(`outline_f3_find_link`). Its median **218.5 ms** exceeds **207.3 ms** by **11.2 ms**.
The ceiling is `1.10 × 143.0 + 50`, from `chrome_old_find` in the same run.
Five measured runs follow one warm-up. At this sample count p95 is the maximum;
only the median has a ceiling in this comparison.

| F3 find | Samples, ms | Median | p95 |
|---|---|---:|---:|
| Brief 20 | 73.9, 93.3, 143.0, 179.8, 198.1 | 143.0 | 198.1 |
| New read | 99.2, 134.3, 218.5, 244.2, 291.4 | 218.5 | 291.4 |

The three expressly named 28a comparisons pass in that run:

| Task | Brief 20 median / p95, ms | New median / p95, ms | New median ceiling, ms |
|---|---:|---:|---:|
| F1 first read | 143.6 / 195.3 | 181.5 / 277.5 | 208.0 |
| F5 click plus report | 740.1 / 858.9 | 659.7 / 720.8 | 864.1 |
| F4 fills up to question | 4,686.0 / 4,889.7 | 4,329.6 / 4,439.7 | 5,204.6 |

**Lead decision, 2026-11-19 (`linux-tools`):** F4's old side retains
`chrome_old_fill_form`, `chrome_old_find`, `chrome_old_click`. The fills invalidate
brief 20's view, so a fresh find is its honest path to Save. The new side uses one
`chrome_do`; both return prepared and neither sends. The recorded comparator is
accepted as it stands; its find is timed, with no call or sample removed.

PR #27's gate itself passed: `passed: true`, no failures or sync failures, all
18 `target_miss` values false. Plain maxima across the three history phases
(the maximum median and p95 may come from different phases):

| Call | Median / p95, ms | Ceiling median / p95, ms |
|---|---:|---:|
| read | 19.89 / 20.92 | 35 / 60 |
| navigate | 44.97 / 49.22 | 100 / 150 |
| free_click | 572.04 / 584.13 | 650 / 750 |
| fill | 563.71 / 579.17 | 650 / 750 |
| asking_click | 27.52 / 29.67 | 60 / 100 |
| approval_to_done | 575.08 / 589.90 | 700 / 850 |

## Repair and local measurement

**Read/profile:** the outline computes a fingerprint for each element; F3 has
hundreds of repeated container meanings. SHA-256's rounds allocated and unpacked
64 temporary arrays per block. The repair uses scalar rounds and, within one
synchronous outline only, hashes each distinct serialized meaning once. Every
element's complete meaning is still read freshly; facts and observe use the same
fingerprint function. No digest, field, safety check or comparison is dropped.

**Run:** paired browser-free VM measurement of a synthetic 603-node F3-shaped
page, three warm-ups and 15 samples per implementation, alternating order:
old median/p95 **25.25 / 30.07 ms**, repaired **20.46 / 22.87 ms**. The whole
reply, including all 603 fingerprints, is identical. Script and raw samples:
`.work/28a-fix2/profile-pair.mjs`, `.work/28a-fix2/reader-pair.json`.
This measures local reader CPU work, not the hosted call or its ceiling.

No latency ceiling, sample count, reference or efficiency-baseline file changed.
The newly dispatched hosted runs and remaining work are in [PROGRESS.md](PROGRESS.md).
