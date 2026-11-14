# Mail sweep and per-call times after final fixes step 7 (2026-11-14)

Follow-up to [mail-sweep-after-f1.md](../post18d/mail-sweep-after-f1.md) (step 1) and the analyst's
[mail-sweep-growth.md](../post18d/mail-sweep-growth.md), measured with the same harness
([mail-sweep/](../post18d/mail-sweep/), unchanged) on the same Mac. CPython 3.14.6 with jsonschema 4.26.0. Detached
worktrees at main `b2b51107`, the F1-only head `b72c81fa` and the step-7 storage head `c5810bb0` (the partial index
`operation_open`). No browser, mail server or container. Data: [mail-sweep-after-step7.json](mail-sweep-after-step7.json).

**Cases** (local, `discover.py --singles`, cases = 2 × primaries + pairs):
- main 28,321;
- F1 only 105,335;
- step 1 (`2e5eb35e`) 35,058;
- **step 7 (`c5810bb0`) 36,490 (×1.29 main)**: single and persistent 6,259 → 6,527 (+268 each, one index page per
  changed unresolved operation row, as the lead expected), pairs 22,540 → 23,436.

**Coverage:**
- step 7 against F1: 47 distinct primary and 81 cleanup sites in both, none missing in any flow;
- step 7 against main: every main site is covered (as in step 1, main's seven `iter_items` cleanup sites are
  `iter_operations` on the branch).

**Mail per-call times** (ABBA plain, 50 calls, median ms, main `b2b51107` → `c5810bb0`):

| Retained ops | read | search | file | compose | prepare_send | expiry |
|---|---|---|---|---|---|---|
| 0 | 0.51 → 0.51 | 3.88 → 3.87 | 7.92 → 7.76 | 4.21 → 3.70 | 7.57 → 6.78 | 3.38 → 2.57 |
| 1,000 | 105 → 4.60 | 108 → 8.00 | 149 → 17.9 | 195 → 11.1 | 159 → 23.8 | 46.9 → 3.76 |
| 4,000 | 408 → 8.45 | 414 → 11.9 | 568 → 27.3 | 768 → 18.2 | 611 → 65.1 | 191 → 4.97 |

- **Every call is at or below main at every history, the fresh store included.** The step-1 fresh-store constant
  (read +0.095, search +0.115, file +0.05 ms) is no longer measurable: read 0.513 → 0.508, search 3.88 → 3.87,
  file 7.92 → 7.76. The per-request operation queries (`_pending`, recovery's notices, `unresolved_sent_checks`)
  now read the index in a fresh store too, which is of the same order as that constant.
- With history the branch is far below main: at 4,000 operations read 408 → 8.5 ms, search 414 → 11.9, compose
  768 → 18.2, expiry 191 → 5.0. Main's own Mail calls scan every retained operation.

**Per sweep case** (`case_cost.py`, median ms, main → step 7):
- maintenance 11.0 → 13.16;
- restart_index 8.27 → 10.0;
- status 35.99 → 42.25;
- cancel 16.89 → 23.88 (the kept cache-miss flow).

**Full disk** (`fulldisk_read.py`): read and search answer on both heads at every history from 0 to 4,000.
