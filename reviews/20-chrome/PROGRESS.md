# Package 20, final fixes: progress

Brief: [`briefs/20-final-fixes.md`](../../briefs/20-final-fixes.md). Claude agents build it in five steps, one fresh
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

## Left, in order

1. **Step 5: one batched browser run**, `gh workflow run control-chrome.yml --ref pkg/20-chrome` (budget: 255 of
   about 280 used; steps 1 to 4 started none). Every row below must pass; the whole suite runs in it.
   - **F2:** 14 credential fields and two ordinary ones (`Distanz`, `Tank`) on the late-reader page
     (`control/chrome/ci/late-reader-fixtures.mjs`), checked by `GROUP 7 POST18D credentials and revealed passwords
     stay unreadable before take reload` and `GROUP 7 POST18D typed field reads require exact one-call approval`.
     The withheld-form text check in `control/chrome/ci/late-binding-matrix.mjs` matches the refusal text.
   - **F3:** 30 rows in `GROUP 3 POST18D absolute destinations inherited bases targets and form owners`
     (`control/chrome/ci/destination-fixtures.mjs`, `finalTargetRows`; 96 rows in all, audited by
     `destination-evidence.mjs`): `post18d-destination-{area,svg-href,svg-xlink}-{top,blank,srcdoc}-target`,
     `post18d-destination-form-action-{top,blank,srcdoc}-owner`, and in the top document `…-owner-target`,
     `…-decoy-target`, `…-sanitize-newline-target`, `…-sanitize-bracket-target`, `…-xlink-show`, `…-empty-target`.
   - **The four `*-top-empty-target` rows: follow what Chrome does** (the lead). If Chrome treats an empty target as
     missing (the base target), keep the code and record that. If it follows the spec literally (the current
     navigable), apply the one-line fix the probe `final-f3-empty-target` marks in `browsingTarget` (an explicit
     empty string is `_self`), flip the row expectation in `destinationExpectation`, and record what was observed.
   - **F6 and discard_unsaved,** all in `GROUP 8 REVIEW iframe drafts and detached or Web Audio report before reload`
     (`control/chrome/ci/review-matrices.mjs`):
     - `final-navigate-reload-{dirty,web-audio,clean}` (now with `discard_unsaved` and the new report text);
     - `final-discard-navigate-url-{dirty,web-audio,clean}` (a taken tab; the report names `field "Draft"`, the page
       stays, the flag moves on);
     - `final-discard-close-tab-{dirty,web-audio,clean}` (a tab Claude opened; Claude's click starts the Web Audio;
       the tab stays controlled until the flag closes it).
   - **F7:** `test_owner_confirm.py`'s Linux-only case (a real spoofing process on a real socket) in the CI Python
     shards; it is skipped on the Mac. F7 has no browser row.
   - **Latency:** Chrome's latency at the 1,000 and 4,000 histories against the ceilings, now without the
     `operation_headers` index and with F4's rule (median or p95). The measured navigate now runs the unsaved
     report (one reader query per frame).
   - If a row fails, fix the cause, not the assertion; every new browser rule (F3's target rules, the report text)
     comes from Chromium's source or the Node fixtures, not yet from a browser.
2. **Records:** the run's receipts, REPORT's Handover, KNOWN-LIMITS for anything the run shows; then delete this
   file. Then the lead's scoped re-check, and only after it the final pair and every Control workflow twice.

## What the code doesn't show

- **F7, for linux-aresos at merge:** install the policy file root-owned at
  `/usr/share/polkit-1/actions/org.aresos.control.chrome-loosen.policy`; the image needs `/usr/bin/pkcheck` and a
  polkit agent in the owner's session. linux-tools' 18c-b image test should press "Allow editing" once with his real
  agent: the dialog must name the site, and a cancelled dialog must leave the site read-only.
- **F7, what CI can't show:** `allow_active` from the policy's defaults on seat0 (CI uses a stand-in rule), and
  polkit's session lookup for Chrome's native host, which runs in a systemd user scope (polkit falls back to the
  user's display session). Both are 18c-b.
- **F7, the new workflow:** `control-chrome-polkit.yml` can be dispatched only once it is on main; until then
  `gh workflow run control-chrome-check.yml --ref pkg/20-chrome -f polkit=true`. The `polkit` input and the gated
  job in `control-chrome-check.yml` can go after the merge.
- **F7, the refactor:** the chrome branch of `Daemon.serve` moved into `Daemon.accept_chrome` unchanged, apart
  from reading the pid; `Bridge.accept` takes the peer.

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
- **`target=""` deviates from the brief (F3, security NOTE 1), for the lead.** The brief asks for HTML's reading
  (current navigable). Chromium's anchor and form code (`GetEffectiveTarget`, `FormSubmission`) treats an empty
  target like a missing one and uses the base target, and the earlier code and its `formtarget=""` test already
  followed that. Binding `_self` would let a named-frame or new-window navigation look like `_self`, the unsafe
  direction, so step 2 kept Chromium's rule. The four `…-top-empty-target` rows decide it on the installed Chrome:
  if they fail with the navigation staying in the top document, change `const target=explicit||documentBaseTarget()`
  to treat an explicit empty string as `_self` (the `final-f3-empty-target` probe is that line) and flip the row
  expectation in `destinationExpectation`.
- **The other F3 rules also come from Chromium's source, not yet from a browser:** SVG links skip the sanitising
  rule and use `xlink:show="new"` only for an empty own target; an iframe name keeps a newline. Step 4's rows check
  them; the `xlink-show` rows check removing `xlink:show` (the `_blank` binding before it is checked only by the
  reader tests), so no extra tab opens during the suite.
- **discard_unsaved, for the lead** (none of these blocks step 5):
  - The error code stays `reload_required` for all four acts, so the code and the report stay one pattern. The
    name doesn't fit navigating to an address or closing; the report text names the act. A rename (for example
    `unsaved_changes`) is a small separate change if wanted.
  - **Back and forward** still drop a document without the report: the brief lists reload, an address and close.
    They are the last members of the class; adding them is one `requireDiscard` call each, plus browser rows.
  - The report uses the existing predicate, so in a Claude tab it also lists text Claude typed itself, and it
    always lists a rich-text editor (there is no native default to compare). Claude repeats with the flag for its
    own typing; for an editor it can't tell apart, the instructions send it to the owner. Telling his typing from
    Claude's would need a per-field record of what Claude's input left, which is a new design.
  - `chrome_close_tab` while a native dialog is open can't query the frame, so it counts as not inspected and needs
    the flag.
  - CI harness: `nav()`, two direct navigations in `matrices.mjs` and every cleanup `close_tab` pass the flag; the
    latency fixture's Send clears its draft after sending (both runtimes see the same page).
- **Credential false positives:** a control named only by a short credential word (a "PIN" or "Secret" button) is
  withheld and refused for input, as "PIN" already was. KNOWN-LIMITS says so.
- **Generated files changed:** `control/generated/chrome-tools.json`, `chrome-instructions.txt` and
  `docs/control/TOOLS.md` (navigate schema and shared text). The extension's runtime hash changes with `reader.js`
  and `background.js`, so step 4's run measures a new build.
