**FIX NEEDED (5 FIX findings)**

Final package review of PR #27 (`pkg/20-chrome`): the whole diff `b2b51107..a4143586`, with the focus on what changed
since `56f93c89`: the branch's own commits, the conflict resolutions in `77cad19a`, `4a4c531d`, `1628be4b` and
`e2ee3a52`, and addenda `-b` to `-g`. I'm a fresh reviewer and didn't build any of it. I worked read-only:
no browser, no profile, no edits in any worktree. I ran plain Python and Node only, on `git archive` exports.

Most of the package does what the briefs ask, and its records are accurate:
- Chrome is on the slim generator.
- Group 12 is derived natively.
- The 92 round-3 names are all present.
- The runs are sharded.
- The hold window is unchanged.
- The late-reader binding and the withheld-form refusal work.
- The rules hold, except the one in FIX-5.

FIX-1 is the analyst's Mail candidate. I confirmed it at both the SQLite level and the engine level, and it is the one
that needs a round. FIX-2 and FIX-3 are brief items not fully done. FIX-4 and FIX-5 are small and can ride along in the
same round.

## FIX

### FIX-1: Mail read and search fail on a full disk once about 700 operations are retained

**Where:** `control/aresos_control/storage.py:831-833`, from `bc738001`. `Store.iter_operations` runs
`kv INDEXED BY operation_headers … ORDER BY k`. Its broad callers are:
- `control/aresos_control/mail/adapter.py:785` and `:818` (`app='mail'`);
- `control/aresos_control/engine.py:180` (`exclude_app='chrome'`).

Every result's pending/notices envelope runs these. On `main` the same callers used `iter_items('op:')`, which SQLite
plans as `SCAN kv USING INDEX sqlite_autoindex_kv_1` with no sort.

**Evidence:**
- **Query plan:** on the branch it is `SCAN kv USING INDEX operation_headers` + `USE TEMP B-TREE FOR ORDER BY`.
- **My SQLite probe:** I hooked the VFS open and used rows of about 3 KB. At 700 rows the sort opens a temporary file.
  When that open fails with `SQLITE_FULL`, the branch query fails with "database or disk is full". Main's query opens
  no temporary file and succeeds.
- **The analyst's engine probe, rerun by me:** I ran `mail-sweep/fulldisk_read.py` from `36fb818e` on exports of both
  commits, with every allocating write failing (ENOSPC):

  | Retained operations | `main` (`b2b51107`) | Branch (`a4143586`) |
  |---|---|---|
  | 0 | `mail_read` and `mail_search` answer | both answer |
  | 1,000 | both answer | both return `storage_limit`; first failure `sqlite.main.create` |

- **Production:** the unit (`control/packaging/aresos-toold.service`) clears `TMPDIR` and has `PrivateTmp=yes`, so
  SQLite writes its temporary files to the private `/var/tmp`, on the system disk.

**Harm:** this breaks another app's normal use exactly when storage is full, which the Control layer is built to
survive, and it is a regression from `main`. In normal operation it also costs temporary-file writes on every call
that builds an envelope: about 5,400 pages per Mail read at 1,000 operations and 21,200 at 4,000 (analyst's
measurement). The forced index buys no safety. The analyst measured it slower for these two filters, and my rerun
agrees: 22.5 ms forced against 15.4 ms in primary-key order at 1,000 operations.

**Smallest fix that closes the class:**
- Broad `app`/`exclude_app` scans must not sort. Removing `INDEXED BY` alone is not enough: for `app=?` the planner
  still picks `operation_headers` and sorts. Read them in primary-key order instead: the old `iter_items('op:')` plus
  the Python filter, or an explicit primary-key index. Keep the header index for the selective `states`/`legacy_open`
  filters, which carry the expiry speed-up.
- Set `PRAGMA temp_store=MEMORY` on the Store's connections, so that no read-only query ever needs temporary-file
  space.
- Add a regression test: with the sweep's ENOSPC VFS hook and at least 1,000 retained operations, `mail_read` and
  `mail_search` still answer. Assert also that the broad-scan plans contain no `TEMP B-TREE`. Add a removal probe that
  restores the forced index.

### FIX-2: Credential detection misses the standard card-security-code token and common German/abbreviated names (`-c` item 2)

**Where:** `control/chrome/extension/reader.js:73`, which treats only `current-password|new-password|one-time-code`
as credential autocomplete tokens, and `:85-93`, the word regex.

**Evidence:** I ran the shipped regex and token test against common field names.
- **Caught:** `password`, `Passwort`, `PIN`, `PIN-Code`, `pinCode`, `Sicherheitscode`, `security code`,
  `Bestätigungscode`, `Einmalpasswort`, `one-time-code`.
- **Missed:** `cc-csc` (the HTML autocomplete token for the card security code), `CVC`, `CVV`, `Kartenprüfnummer`,
  `TAN`, `mTAN`, `pushTAN`, `TAN-Nummer`, `Geheimzahl`, `PINCode`/`pincode`, `pwd`, `passwd`, `user_pass`,
  `verification code`, `Verifizierungscode`, `TOTP`, `2FA code`.

In a watched tab, a field that never was `type=password` or masked is read by an ordinary `chrome_read` with no
question. Examples are `<input autocomplete=cc-csc placeholder=CVC>` or `<input name=tan aria-label=TAN>`, which banks
and checkouts commonly use with `type=text`/`tel`. In an unwatched tab the same field is included in an approved
`chrome_read_typed_fields`.

**Harm:** credentials reach Claude: card security codes next to a readable card number, and one-time banking codes.
The brief names exactly these classes: "PIN, passcode, one-time code or security code, in English and German".

**Gaps in the tests:** none of the individual words has a test. Removing `zugangs…code`, `otp`, "one-time password"
or the camelCase split leaves every test passing.

**Smallest fix:**
- Treat `cc-csc` like the password/OTP tokens.
- Extend the term list with:
  - `pwd`, `passwd`;
  - `pin` as a prefix (`pin(code|nummer)`), `geheimzahl`;
  - `tan` and its variants, `tan-nummer`;
  - `cvc`, `cvv`, `csc`, `kartenprüf(nummer|ziffer)`, `prüfnummer`;
  - verification/authentication codes in English and German;
  - `totp`, `2fa`.
- Add a table-driven Node test of every term, in both a watched and an unwatched document, with a removal probe for the
  table.
- Add the KNOWN-LIMITS line that the check remains a heuristic (see below).

### FIX-3: The browsing target is resolved in script, so some base-target changes don't ask again (`-b`)

**Where:** `control/chrome/extension/reader.js:33-39` (`browsingTarget`).

**Evidence** (from reading the code; the third point is from memory of Blink and not confirmed in a browser):
1. `document.querySelector('base[target]')` also matches a non-HTML `<base>`, for example an SVG-namespace `<base>` in
   foreign content placed first. Chrome only uses HTML `<base>`. So a decoy fixes the bound target while the real base
   target changes freely, with no new question.
2. `/[\n\r\t<]/` maps any base target that contains a tab, newline or `<` to `_blank`. The HTML rule is tab/newline
   **and** `<`. So `"a\nb"` changing to `"c\nd"` binds as the same `_blank`.
3. An SVG `<a>` with an empty target and `xlink:show="new"` opens `_blank` in Blink, but it binds as `_self`.
   Toggling `xlink:show` while the approval waits moves the click to a new tab without a question.

The address, method and body stay bound, so the harm is low: the approved request runs in a different window or
frame. But `20-post-18d-b.md` names "the target frame or window" with "any change … to the base … re-asks" and asks to
close the class. And `REPORT.md:52-53` claims "native browsing targets", which is false for HTML links and forms.

**Smallest fix:**
- Take the document base target only from the first HTML `<base>` that has a `target` (an `HTMLBaseElement` check
  through saved natives).
- Apply the spec's sanitizing rule.
- Honour `xlink:show="new"` for SVG links with an empty target.
- Correct the REPORT sentence.
- Add one browser row and one removal probe per case.

### FIX-4: The latency gate doesn't enforce the lead's median ceilings on their own (`-g` item 1)

**Where:** `control/chrome/ci/latency-check.py:93-94`. A call fails only when **both** median and p95 exceed the
ceiling (×runner allowance) or the relative threshold.

**Evidence:** I loaded the real gate with the final PR run `43539458133`'s retained plain profile and changed only the
`history-4000` phase:
- `read` at 50/55 ms passes. Its ceiling is 35/60, and the relative threshold there is 40.9/57.1.
- `asking_click` at 65/70 ms passes. Its ceiling is 60/100, and the relative threshold there is 55.0/74.6.

A history-dependent read slowdown of about 2.3×, the same shape as round 3 but smaller, therefore merges green above
the lead's read median ceiling. The round-3 removal probe passes only because round 3's cost was huge.

**Smallest fix:**
- Fail when a median crosses its ceiling×allowance. A shift in the median is systematic, not tail noise.
- Keep the deliberate tolerance for an isolated p95 spike (`test_tail_spike_alone_does_not_fail…`).
- Add a test for a median-only breach in one history phase.

If the lead knowingly accepted "both must cross" when setting the ceilings (it is described in
`REPORT.md:666-670`), move this finding to KNOWN LIMIT and state it in the Handover and in `latency-targets.json`.

### FIX-5: Absolute user paths in three record files the PR adds (rule broken; the fix is mechanical)

**Where:**
- `reviews/20-chrome/records/integrate3/f25-strict-audit.txt:6`;
- `reviews/20-chrome/records/integrate3/popup-regressions-before.txt:23,40,57,58,75,76`;
- `reviews/20-chrome/records/integration-verdict-subsets-red.txt:28`.

All are Node stack traces with `file://` paths to the builder's home-directory worktree. They have been there since
before `56f93c89`.

**Fix:** replace the prefix with `<worktree>/`, as the other records do. Add a preflight grep that rejects home-directory
paths under `reviews/20-chrome/`.

## KNOWN LIMIT (to add to KNOWN-LIMITS.md)

**Credential detection is a word heuristic.** Even after FIX-2, a revealed secret with no recognised signal is read in
a watched tab, and in an unwatched tab after an approved asking read whose question shows only "single-line field N".
Unrecognised signals include an image label, nearby text that isn't a label, another language or an unknown
abbreviation. The harm is that one owner-typed secret is exposed. It is accepted as the brief's chosen rule of thumb:
masked and `type=password` history still always protects. `REPORT.md:64-65` already says "the unlabelled
revealed-secret limit is accepted in KNOWN-LIMITS", but only the editor case is listed (`KNOWN-LIMITS.md:21`).

**Not new:** a link's address is not compared again at the trusted click (`guard.js:305`). Forms are compared at
submit (`guard.js:246`), but on action, method, encoding and the raw `target`, not the resolved browsing target. So a
page's own `pointerdown`/`mousedown` handler can change the base after the final check deterministically, not only as
a race. `KNOWN-LIMITS.md:8` covers this ("a page can change between the final binding check and input"). Its wording
could name the input's own handlers. Comparing the expected `href` and browsing target in the guard's mark would
narrow the gap.

## NOTE

- **Link wrapped around a button:** in `<a href><button>Delete</button></a>`, `control()` picks the button, so `href`
  is null. The question honestly says the destination isn't visible (`adapter.py:400`), but a base change then doesn't
  ask again. XHTML `tagName` checks (`reader.js:341,347`) behave the same way.
- **Missing test rows:**
  - no target-change row for `area`, and no plain SVG `target` attribute change;
  - form-owner rows exist only for formaction controls.

  `REPORT.md:280-282` ("each URL source, base/attribute/target mutations and form-owner changes") overstates this. The
  Node destination probes run on a fake DOM. Ignoring the form's own `target` survives all of them (only the browser
  rows would catch it).
- **Withheld-form refusal:**
  - It runs before the reload path (`adapter.py:593` before `:594`; `background.js:936` before `:937`), so repeating
    the click with `reload_taken_tab=true` is refused again. The working route, `chrome_navigate direction=reload`, is
    not named in the instructions.
  - Hidden inputs count as withheld (`reader.js:217`), so almost every real form in an unwatched tab takes this path.
  - `post18df-withheld-form-final` dies on the reason text. The binding check at `background.js:938` would stop the
    input anyway.
- **Typed-read question:** labels are neither quoted nor capped (`adapter.py:298`), so one hostile label can look like
  several fields. Frames show by Chrome id, without their site.
  - `read_typed_fields` carries `idempotentHint: true`.
  - Dead code from the dropped `-f` provision: `reader.js:229-231` and `:253`.
- **Handover is out of date** (expected): push run `43539449510` has finished; see Verified. Mail `43539458146`
  attempt 1 passed on `a4143586`, with sweep 6 at 60.8 min and sweep 4 at 51.0. Attempt 2 was running at 02:24 UTC.
  Mail has passed once, not yet twice.
- **Stale receipt:** `records/post18d/mail-eight-shard-inventory.json:45` still says `job_timeout_minutes: 60`, but
  the workflow now uses 120 (`096c3088`).
- **Main has moved:** `origin/main` is now `d0d1974c`, past `b2b51107`. It changes nothing under `control/` or in the
  Control workflows, and a trial merge is clean.
- **Main test changed:** `control/tests/test_review22_protocol.py` (a main test) now injects the lost final
  acknowledgement directly instead of shortening the timeout. That is stricter (it asserts the loss happened), not
  weaker.

## Mail fault-sweep growth (analysis `36fb818e`, unpushed)

**The counts hold:**
- 110,065 / 28,519 = 3.859.
- The extra single and persistent cases: 6,574 − 6,302 = 272, one header-index page per changed `op:` row. This matches
  the `operation_headers` creation in `storage.py`.
- Local extra pairs: 109,519 − 28,321 − 2×272 = 80,654. Of these, 80,054 (99.3%) are at the Chrome journal reader.
- The time per case (76–100 ms on main, 94–128 ms on the branch, median ×1.15) multiplies with the case count to the
  observed ×5 wall time.

**The causes hold in the code:**
- `committed.py` `sync()` caches on `(st_ino, st_size, st_mtime_ns)`.
- Main's `sweep_scripts.timestamps` (`15880c62`) returns a fresh stamp for `operations.jsonl` on every `stat`. The
  sweep harness, `storage_faults.py` and `control/ci/mail` are unchanged by the branch.
- The envelope calls the projection at `engine.py:78, 101, 189` and `mail/filing.py:275-276`.
- `Chrome.__init__` hashes the runtime tree on every Engine start when `build-id.json` is absent (`adapter.py:86-94`):
  88 files plus 4 named ones = 92.

**The FIX holds:** see FIX-1.

**Does the defeated cache make the sweep test something production never does, or miss something production does?**
- **Nothing production never does.** Re-syncing the projection (open the journal, read from the offset, close) is
  production's path after every journal append. The sweep repeats it about 26 times per request instead of 1 to 3, so
  most extra cases are redundant repetitions of the same cleanup site. With the real stat, local cases are 35,819,
  against 28,321 on main.
- **It misses two things:**
  - **The cache-hit path**, which is production's common path. It has no fault site (only `stat`). Its correctness rests
    on the append-only journal growing with every commit. I found no production sequence where a hit hides a committed
    record, but the sweep could not detect one.
  - **Retained-history size.** The sweep's fixtures hold only a handful of operations, so storage behaviour that
    depends on history size, such as FIX-1's spill to temporary files, is invisible to it. That is a real production
    gap.

**Suggested test-only change:** stamp the journal by `(inode, size)` so the projection's cache behaves as in
production, and add a full-disk read with a large history (FIX-1's test).

## Verified

**Brief items:**
- `python3 control/generate.py --check` on an export of `a4143586` prints "Generated artifacts match definitions"
  (this includes `policy.js`, `ask-rules.json`, `user-mcp.json` and `managed-settings.draft.json`).
- The ask rules are exactly testapp/mail plus `mcp__chrome__read_typed_fields` and `mcp__chrome__submit`.
- `submit_trusted` is a trusted send: `require_trusted_send` calls `trusted()` against the committed owner entry.
- The clipboard and typed-field sentences appear once each in `instructions_for('chrome')`.
- Group 12 is derived in `precedence-evidence.mjs` from 10 native normal/skip cases inside 18d's `precedence_checks`.
  It is not set by hand.
- `latency-targets.json` matches the lead's table, is `lead-approved` and names run `43502970342` and `ab7aba92`.
- `HOLD_MS` is 500 plus the 25 ms wait, unchanged. The early-end idea appears only as an open idea.
- Chrome containers 120 min, jobs 130, latency 120. No 350- or 360-minute limit remains.

**Late reader** (a second reader checked these, and I sampled them):
- The unwatched scope (`typedField`), filled/empty, the prepared binding, one-call use, the withheld-form refusal text
  and the editors owner line are done as written.
- Tab-group lines are unchanged since `56f93c89` (one global group id).

**Base-URL sources:** all seven resolve through native getters or the native `baseURI`, and both service and extension
bind and re-check them. In each audit, 66/66 destination cases give zero arrivals for stale approvals.

**Final-head CI** (one fetch per run; receipts kept outside the repo):

| Run | Workflow | Result on `a4143586` |
|---|---|---|
| `43539458133` | Chrome PR | success; longest job 29.0 min |
| `43539449510` | Chrome push | success; longest job 31.0 min |
| `43539457993` | base | attempts 1 and 2 success |
| `43539458152` | boundary | attempts 1 and 2 success |
| `43539458040` | qualification | attempts 1 and 2 success |
| `43539458146` | Mail | attempt 1 success; attempt 2 running |

- The receipt counts match: 309 tests; 17 interactive cases and 20 unit tests; 47 Python and 368 Node tests.
- The run count is 255 on the branch, as `REPORT.md` says.
- **My own audit of push run `43539449510`:** I downloaded only its two aggregate and four latency artifacts. They are
  flat metadata with no profile directories. `reviews/20-chrome/audit-review-evidence.mjs` passes both installs:
  - 98 named cases, all 92 round-3 names present;
  - group 12 true, 999 word cases, 268 Python tests.

  The latency gate passes both profiles at runtime hash `b9de9a97…`. The highest client/ceiling ratio is 0.90 (free
  click median).
- I recomputed the 92 names against the PR run's retained audits: none missing in either install.
- Runtime inputs are unchanged since `e0cc9846`, and `build.py` on the export gives `b9de9a97d18c…`.

**Local, on exports:**
- 373/373 Node tests (including `audit-streams.test.mjs`).
- All four Python shards (95/54/63/56 = 268).
- Six removal probes rerun with `mutation-audit.py`, each rejected: `post18d-target`, `post18d-read-credential-scope`,
  `post18df-element-identity`, `post18df-withheld-form-wait`, `post18d-latency-recovery-space`,
  `post18dg-round3-latency-cost`. The other reader killed further base-URL and credential probes.
- The round-3 cost-restoration test fails the real CI command for all six calls.

**Rules:**
- `git diff 8b7e799c a4143586 -- control/packaging/aresos-toold.service` is empty.
- `docs/control/CONTROL.md` and every protected path are untouched through `650ec21d`.
- The extension has no `chrome.storage`, IndexedDB, localStorage or sessionStorage, no storage permission and no
  `key` in `manifest.json`.
- `build.py` hashes the installed source tree.
- The packaging templates keep `EXTENSION_ID`, `UPDATE_URL` and `CRX_URL`.
- I found no secrets. Addresses are fixture-only (`.test`, `.invalid`). The only rule break is FIX-5.

**Merges:** I read the `--remerge-diff` of the four merges. The resolutions keep main's Mail/18d code and re-apply
Chrome's base changes on top: the native socket, the committed projection, the owner-state reads, and recovery skipping
`intent:chrome:`. `1628be4b` and `e2ee3a52` needed no conflict resolution.

**KNOWN-LIMITS.md:** it contains all seven decided limits the lead listed, each with what it is, the harm and why it is
accepted. Missing: the credential-heuristic line above.
