**Why the Mail fault sweep grew (analysis, 2026-11-14).** Main `b2b51107` runs 28,519 sweep
cases (6,302 single, 6,302 persistent, 15,915 cleanup pairs). The branch runs 110,065
(6,574 + 6,574 + 96,917), ×3.86, with an unchanged sweep harness. A browser-free local
reproduction matches CI exactly in 19 of 23 flows; the export and archive flows differ by
Mac-only steps on both commits. [Record](mail-sweep-growth.json), [harness](mail-sweep/).
**More cases, from Chrome's journal reads in every result.** 99.3% of the extra pairs close
the read-only journal that Chrome's committed projection opens while each result builds its
warning list (`engine.py` lines 78, 101, 189; `f3cfd5b1`, `3bf1b0d2`). The projection caches
on the journal's inode, size and mtime. Main's sweep scripts (`15880c62`) give the journal a
new mtime on every stat, so the sweep re-reads it 26 times per Mail request. Each close after
a fault is a cleanup site, paired with every earlier write. With the real stat, as in production,
local cases fall from 109,519 to 35,819 (main 28,321). The 272 extra single and persistent
cases are one SQLite page per changed `op:` row (`operation_headers` index, `bc738001`).
**Slower cases, mostly test-only.** CI time per case is 76–100 ms on main and 94–128 ms on
the branch (×1.15 median); maintenance, which has identical cases, goes 44→68 ms. On one Mac,
maintenance 11.5→20.2 ms: 5.5–6.2 ms is a source checkout hashing 92 Chrome files at each
Engine start (`414eb1df`, 2–3 starts per case), and up to 5.4 ms is the forced journal re-reads.
**Mail's own calls: no slowdown** (Chrome's method: 50 calls per type, ABBA, plain and
instrumented). In a fresh store a read takes 0.55→0.61 ms, for the Chrome warning check
(`f3cfd5b1`). At 1,000 / 4,000 operations the branch is faster: read 113→90 / 443→357 ms,
file 162→105 / 611→373, prepare_send 165→110 / 660→414, expiry 48→3.7 / 202→5.4.
**FIX:** `Store.iter_operations` forces `INDEXED BY operation_headers` with `ORDER BY k`
(`storage.py` 831–833, `bc738001`), so the sort spills to temporary files. From ~700 retained
operations, every Mail read and search writes there (5,400 pages at 1,000). On a full disk both
return `storage_limit`, where main answers. The index is no faster here and buys no safety.
