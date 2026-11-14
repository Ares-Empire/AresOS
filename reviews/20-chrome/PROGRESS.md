# Package 20, final fixes: progress

Brief: [`briefs/20-final-fixes.md`](../../briefs/20-final-fixes.md). Claude agents build it in four steps, one fresh
agent each. The last step deletes this file.

## Done

### Step 1 (Mail and storage), Claude Opus 5.5, 2026-11-14

- **F1, Mail full-disk sort** (`b72c81fa`). `Store.iter_operations` walks the primary-key range
  `k>='op:' AND k<'op;'` in key order. The header filters stay in SQL behind a unary `+`, and the `substr` prefix
  test stays for UTF-16 databases. The `INDEXED BY` switch, `_index_operation_headers` and the
  `operation_headers` index are gone.
  - Tests (`control/chrome_tests/test_full_disk_reads.py`):
    - an `EXPLAIN QUERY PLAN` check of all 16 shapes in four states: fresh, with the old index left behind,
      the same after `ANALYZE`, and `ANALYZE` without it. Each is pinned to no `TEMP B-TREE` and to a read
      through `sqlite_autoindex_kv_1`;
    - Mail read, Mail search and `control_pending` with 1,200 retained operations of 3–4 KB. On a full disk
      (every allocating file or SQLite write fails) each still answers with the same data and needs no write;
    - the store creates no header index.
  - The three index tests in `test_latency.py` now check that a reopen under low or tight space keeps committed
    reads and reservations and adds no index. Their index lines are gone.
  - `mutation-audit.py`:
    - drops `post18d-latency-recovery-space`, because the code it guarded is gone;
    - adds `final-f1-*`: the forced index put back, once for each test, and the unary `+` dropped. All four
      are rejected.
- **Mail sweep** (`2e5eb35e`).
  - `sweep_scripts.timestamps` gives `operations.jsonl` a new stamp only when its inode or size changes, as
    production's `(inode, size, mtime)` key would see it.
  - The database stamps stay fresh on every stat, so the independent Driver still decodes every snapshot.
  - `cancel` (`PER_STAT_JOURNAL_FLOWS`) keeps a fresh journal stamp on every stat. That is the one kept
    cache-miss case; it reaches every Chrome journal-read call site.
  - A clean discovery of all 23 flows keeps every distinct fault site in every flow, and the primaries are
    unchanged.
  - `support.install_build_identity()` gives every Mail test an installed `chrome/build-id.json`. It holds the
    same hash, computed once per process.
  - New tests, each shown to fail without its change:
    - `test_sweep_journal_stamp.py`;
    - `test_build_identity.py`, which also keeps the missing-file (hashing) path covered.
  - The sweep test itself passes locally for `cancel`, `status` and `restore`, and replay determinism holds for
    all flows.
- **F5** and **the stale receipt** (`b7f58bc6`).
  - The three record files say `file://<worktree>/`.
  - `local-popup-summary.json` keeps each recorded hash beside the current one.
  - `mail-eight-shard-inventory.json` says `job_timeout_minutes: 120`.
- **Measurements.**
  - Cases, local: main 28,321, F1 only 105,335, final 35,058.
  - Mail calls: at or below main with history. In a fresh store a constant 0.1 ms per result remains, the same
    Chrome warning check as before this step; it is flagged in REPORT for the lead.
  - Full local preflight on `2e5eb35e`: 271 Python, 373 Node and 319 mutations, plus the generator, diff and
    unit-pin checks, all green.
- **REPORT**: see "Final fixes round" at the top of `REPORT.md`, and
  `records/post18d/mail-sweep-after-f1.json` and `.md`.

## Left, in order

1. **Step 2:** F2 (credential names), F3 (browsing target), F6 (reload report), and the reader and adapter notes
   (typed-read question labels and frame sites, dead `-f` code, `visible()` on extension errors, stale
   managed-settings and `control/README.md` text, the withheld-form tool text).
2. **Step 3:** F7 (polkit confirmation for owner authority over `chrome.sock`).
3. **Step 4:**
   - F4 (latency ceilings fail on median or p95);
   - the remaining doc notes;
   - one batched browser run for the rows of F2, F3, F6 and F7;
   - the final preflight;
   - the records, the Handover and KNOWN-LIMITS;
   - deleting this file.

## What the code doesn't show

- A database that an earlier build of this branch created may still carry the old `operation_headers` index.
  Nothing reads it: the unary `+` keeps every filter off it, and the plan test checks that. It still costs one page
  per changed `op:` row. No released build ever created it, so there is no migration that drops it.
- Dropping the index means the selective `states` and `legacy_open` scans (expiry, recovery) read every retained
  operation's header in SQL instead of an index range. The measured expiry time is in the record and still beats
  main. Chrome's own latency profiles at 1,000 and 4,000 operations are re-measured only in step 4's browser run.
- In the CI Mail sweep, `cancel` stays at its forced-miss size. Every other flow drops the repeated journal
  re-reads, and with them most cleanup pairs. The CI Mail workflow measures the real per-job times in the final pair.
- Local measurement used CPython 3.14.6 with the worktree's `.work/20-chrome/python-deps` (jsonschema 4.26.0), the
  analyst's harness unchanged, and detached worktrees at `b2b51107`, `b72c81fa` and the measured head. The worktrees
  were removed afterwards.
