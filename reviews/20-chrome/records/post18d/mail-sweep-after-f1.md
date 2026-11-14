# Mail sweep and per-call times after final fixes F1 (2026-11-14)

Follow-up to [mail-sweep-growth.md](mail-sweep-growth.md), measured with the same harness
([mail-sweep/](mail-sweep/), unchanged) on the same Mac. CPython 3.14.6 with jsonschema 4.26.0. Detached worktrees at
main `b2b51107`, the F1-only head `b72c81fa` and the final step-1 head `2e5eb35e`. No browser, mail server or container.
Data: [mail-sweep-after-f1.json](mail-sweep-after-f1.json).

**Cases** (local, `discover.py --singles`, cases = 2 × primaries + pairs):
- main 28,321;
- F1 only 105,335;
- final 35,058 (×1.24 main).

The main count equals the analyst's exactly. F1 brings single and persistent cases back to main's 6,259. The
production journal stamp, with `cancel` kept at a fresh stamp per stat, brings the pairs from 92,817 to 22,540.

**Coverage:**
- final against F1: 47 distinct primary and 81 cleanup sites in both, none missing in any flow;
- final against main: every main site is covered (main's `iter_items` sites are `iter_operations` on the branch).

**Mail per-call times** (ABBA plain, 50 calls):
- With 1,000 and 4,000 retained operations every call is at or below main (0.19×–0.90×), expiry included
  (46 → 11.5 and 189 → 37 ms).
- In a fresh store read is +0.095, search +0.115 and file +0.05 ms. That is the per-result Chrome warning check
  (`f3cfd5b1`), unchanged from the analyst's pre-F1 measurement (+0.07, +0.09, +0.10).

**Per sweep case** (`case_cost.py`, median ms, main → final):
- maintenance 11.5 → 12.9;
- restart_index 9.2 → 9.4;
- status 37.1 → 42.8;
- cancel 18.0 → 23.6 (the kept cache-miss flow).

**Full disk** (`fulldisk_read.py`): read and search answer on both heads at every history from 0 to 4,000.
