# Package 20, final fixes: progress

Brief: [`briefs/20-final-fixes.md`](../../briefs/20-final-fixes.md). Claude agents build it in six steps, one fresh
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

### Step 2 (reader, target, reload, notes), Claude Opus 5.5, 2026-11-14

Code commits `f177314b` and `831feceb`; details in REPORT.md, "Step 2".
- **F2:** `credentialLike` knows the reported names and tokens plus the brief's English and German variants. Short
  names match only as whole tokens; label text split by markup counts; `cc-csc` history is sticky. KNOWN-LIMITS has
  the word-heuristic line.
- **F3:** first HTML `<base>` only, HTML's sanitising rule (tab/newline **and** `<`), SVG `xlink:show="new"`.
  `target=""` keeps Chromium's base fallback (see below). REPORT's "native browsing targets" and the 60-row coverage
  sentence are corrected; KNOWN-LIMITS names the residual.
- **F6:** `chrome_navigate direction=reload` gives the first input's report; `reload_taken_tab` is in the navigate
  schema; a POST never reloads.
- **Notes:** withheld-form text and tool text, typed-read question (quoted, capped labels, frame site), `visible()`
  on extension errors, dead `-f` code removed. NOTE 2 (marker shape) left as it is: changing it changes catalogue
  result shapes.
- **Removal probes:** 25 new, 6 repointed; all rejected.
- **Full local preflight on `831feceb`:** 274 Python (shards 40/101/53/80), 387 Node and 344 mutations, plus the generator, diff and unit-pin checks, all green.

### Step 3 (F7, polkit), Claude Opus 5.5, 2026-11-14

Commits `f01ef04c` (code, tests, probes) and `5f18ff60` (real-polkit CI case); details in REPORT.md, "Step 3".
- `allow` and read-only off over `chrome.sock` run `pkcheck` against the connected process (pid, start time, uid)
  through `org.aresos.control.chrome-loosen` (`auth_admin`, owner annotation `unix-user:aresos-tools`), beside the
  service loop, one dialog at a time. Only a clear yes from the same connection writes, and only that change.
  Listing, revoking and read-only on need no password.
- The details page says loosening asks for the password and names the pending change while the dialog is up.
- Policy file `control/chrome/packaging/org.aresos.control.chrome-loosen.policy`, to be installed at
  `/usr/share/polkit-1/actions/`; named in REPORT and the packaging README.
- Tests: `test_owner_confirm.py` (stub), `details.test.mjs`; 14 removal probes `final-f7-*`, all rejected.
- Real polkitd (Fedora 45, polkit 127) with `pkttyagent`, under an emulation of the unit's sandboxing: run
  `43556395889` passed all six cases. It ran through `control-chrome-check.yml -f polkit=true`, not the
  `control-chrome.yml` budget.
- **Full local preflight on `5f18ff60`:** 286 Python (shards 50/43/100/93; the Linux-only real-socket case is
  skipped on the Mac), 390 Node and 358 mutations, plus the generator, diff and unit-pin checks, all green.

### Step 4 (latency ceilings, discard_unsaved, doc notes, unit pins), Claude Opus 5.5, 2026-11-14

Commits `90f8f720` (F4) and `6a948248` (the flag, doc notes, unit pins); details in REPORT.md, "Step 4".
- **F4:** a call misses the lead's ceilings when its median or its p95 is over the ceiling; the reference comparison
  keeps "both must cross". Probes `final-f4-*`.
- **discard_unsaved** (the lead's decision) replaces `reload_taken_tab` everywhere. The first act, navigate reload,
  navigate to an address and close_tab on any Claude tab share one report (`requireDiscard`): fields by label,
  never values, frames that couldn't be inspected, playing media. Without the flag nothing happens. One sentence in
  `instructions_for('chrome')`. Probes `final-discard-*` (11) plus eight earlier ones repointed (`f850ec7d` for four of them).
- **Doc notes** (`managed-settings.draft.comments.md`, `control/README.md`) and **unit pins** (whole file,
  comments included; probes `final-notes-unit-*`).
- **Mail paragraph** in REPORT's Step 1 in the lead's words, with the table from `mail-sweep-after-f1.json`.
- **Full local preflight on `f850ec7d`:** 288 Python (shards 50/43/100/95; the Linux-only socket case is skipped on
  the Mac), 392 Node and 373 mutations, plus the generator, diff and unit-pin checks, all green.

### Step 5 (the lead's follow-ups to steps 3 and 4), Claude Opus 5.5, 2026-11-14

Commits `529d5fe8`, `2f633a8d` (F7) and `3a2ec7c4` (back/forward, editors, whose typing); details in REPORT.md,
"Step 5".
- **F7 dialog text:** `polkit-check.py` asserts every prompt is the policy's message naming that case's change (two
  different changes). Run **`43561341511`** passed; polkit carries `$(change)` for this caller, so every claim that
  the dialog names the change stands.
- **F7 CI:** `control-chrome-polkit.yml` runs on pull-request pushes (paths: `confirm.py`, the policy, the check, the
  unit, the workflow); the `polkit` shim is gone and `control-chrome-check.yml` matches `b424f60a` again.
- **F7 install tree:** a test pins that only the real policy is hashed and installed under `/usr/share/polkit-1/`.
- **KNOWN-LIMITS:** the spoofer-first availability line, and the one typing-mark race.
- **Back and forward** get the shared report and the flag.
- **Editors** count only after input since load (a late reader or a gap after release still counts every editor);
  plain inputs and textareas keep their rule.
- **Whose typing: built.** The guard's trusted-event capture already sees every `input` event and knows when Claude's
  dispatch is in flight, so it records per field whether the owner or Claude typed. The report marks each field;
  Claude's own typing may be discarded without asking, the owner's typing, playing media and uninspected frames need
  his OK.
- Probes: 19 new (`final-f7-*` 7, `step5-*` 12), two repointed; all rejected.
- **Full local preflight on `3a2ec7c4`:** 291 Python (shards 53/43/100/95; the Linux-only socket case is skipped on the Mac), 399 Node and 392 mutations, plus the generator, diff and unit-pin checks, all green.

### Step 6 (React fields, two browser runs; STOPPED for the lead), Claude Opus 5.5, 2026-11-14

Commits `8fefbba0` (React fields), `f3853eb1` (CI service wrapper), `a777c178` (audible tail), `aafeffe9` (lists);
details in REPORT.md, "Step 6". Runs `43564715596` and `43566651314`; receipts in `records/final-step6/`.
- **React-controlled plain fields:** a plain field also counts when it got trusted input since load and still holds
  text; the latency page's Send empties value and default. Node tests, four `step6-*` probes, two browser rows (not
  run yet).
- **Run `43564715596`** failed everywhere at "extension native connection": step 3's `bridge.accept(connection,
  peer)` against the CI service's one-argument wrapper. Fixed (`f3853eb1`, `test_bridge.CIServiceWrapper`, probe).
- **Run `43566651314`:** F3's 96 destination rows passed (**Chrome uses the base target for `target=""`; the code
  stays**), F2's credential checks, words, recheck2/3, adapters, precedence and Python shards passed. Three failures:
  1. `final-navigate-reload-clean`: Chrome's ~2 s `audible` tail after the Web Audio row in the same tab. Harness
     premise fixed (`a777c178`); KNOWN-LIMITS names the tail.
  2. **Latency with history misses the ceilings** (read 389 ms at 4,000 against 35): F1's per-request scans. Needs the
     lead's decision; recommendation in REPORT ("Step 6", Failure 2).
  3. GROUP 6: an untouched drop-down whose page marks no option counted as the owner's typing. Fixed (`aafeffe9`,
     HTML's reset state, tests, probe).
- **Full local preflight on `aafeffe9`:** **292 Python, 404 Node and 398 mutations** (Python shards 54/43/100/95; the Linux-only socket case is skipped on the Mac and runs in CI), every baseline passing, plus the generator, diff and exact-unit checks (unit byte-identical to `8b7e799c`).

### Step 7 (the partial index, the retake rule, three browser runs; STOPPED for the lead), Claude Fable 5.2, 2026-11-14

Commits `c5810bb0` (index), `1e9213f7` (retake rule), `87041a57` (probes), `17f402d1` and `c1173b0b` (the one row's
harness), `967ef7e8`, `d12b2c24` and the record commits; details in REPORT.md, "Step 7".
- **Partial index `operation_open`** on `k` alone over the unresolved operations (open states, malformed state headers,
  unacknowledged notices, open sent-copy checks); one definition `OPEN_OPERATIONS` for the index's WHERE and every
  selective query's term (`states` ⊆ OPEN, `legacy_open`, the new `unresolved=True` used by `_pending` and Mail's
  `unresolved_sent_checks`). No shape sorts; a store that can't add the index (full disk) opens and reads through the
  primary key. Tests: 48 plan shapes in four index states, one definition, membership, full-disk open, no broad scan on
  a Chrome request, timing in the normal suite (indexed 0.003 ms against scans of 3–31 ms locally; 0.01 against 6–90
  on the runner, SQLite 3.45.1). 11 probes `step7-*`.
- **Mail re-measure** (`records/final-step7/mail-sweep-after-step7.*`): every call at or below main at every history,
  fresh store included; cases 36,490 (×1.29 main; +268 single and persistent from the index).
- **Retake rule:** after a release and a retake without a reload every non-empty text field counts, marked as the
  owner's unless only Claude was seen typing there before; KNOWN-LIMITS line 27 states the rule and what remains.
  Node test, two probes.
- **Runs `43575571819`, `43580466542`, `43584711126`** (the step's three): latency under every ceiling at fresh, 1,000
  and 4,000 in both profiles, three times; every row passed except `final-discard-close-tab-web-audio` (GROUP 8,
  review shard), whose three attempts each stopped one step later (see REPORT, "Step 7").
- **Full local preflight on `c1173b0b`:** 297 Python (shards 53/56/46/142; the Linux-only socket case is skipped on
  the Mac and ran in CI), 405 Node and 411 mutations, plus the generator, diff and exact-unit checks, all green.

## Left, in order

1. **The lead decides the red row** `final-discard-close-tab-web-audio` (REPORT, "Step 7", the runs and the two
   observations). In run `43584711126` the sound was playing (page report) in a tab Claude had opened, released, the
   owner loaded and played in, and Claude took back; `chrome_close_tab` without `discard_unsaved` closed it with no
   report. Either Chrome's `audible` flag wasn't set for that tab at that moment (a product gap for close_tab on such
   a tab), or the row's premise needs a browser to settle. Options: a fourth run with a diagnostic row (print the
   `tabs` row and the reader's `reload_state` for the tab before the close), or decide the row's premise.
2. **One batched run that passes everything,** including what the red row hides in the review shard:
   `final-discard-close-tab-clean`, `final-discard-history-*`, `-editor-*`, `final-discard-react-typed-by-claude` and
   `-typed-by-owner`, the four review checks after GROUP 8, and the aggregates with their four audits (none has run yet:
   a shard was missing each time). Budget: **260 / about 280** `control-chrome.yml` runs.
   `.work/final-step7/fetch.py` and `save.py` fetch and record a run (metadata only; `save.py` needs a run whose
   aggregates exist).
3. **Records,** REPORT's Handover ("fix round done"), KNOWN-LIMITS; then delete this file. Then the lead's scoped
   re-check, and only after it the final pair and every Control workflow twice.

## What the code doesn't show

Copied to REPORT.md ("Step 6", "What the code doesn't show"), so deleting this file loses nothing; add new items
there too. New in step 6:
- The CI-only Python files (`control/chrome/ci/service.py`, `latency-profile.py`, `sites/qualification.py`) wrap
  service and bridge methods and never run locally; a signature change in `aresos_control` needs a look there
  (`test_bridge.CIServiceWrapper` now covers `accept`).
- A failed browser check ends its shard (`failBrowserCase`), so one failure hides every later row in that shard.
- For the lead: the React rule's release-gap residual (KNOWN-LIMITS) and its stricter alternative.
