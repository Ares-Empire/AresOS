# Security review, final: package 20 (Chrome tools for Claude), PR #27

**Verdict: FIX NEEDED (3 FIX findings).**

Reviewed: `git diff b2b51107 a4143586` (the whole package on top of main), with the weight on
`56f93c89..a4143586` and the conflict resolutions in merges `77cad19a`, `4a4c531d`, `1628be4b`, `e2ee3a52`.
Review copy at `650ec21d` (detached), read-only; no browser was started; no workflow was dispatched; no GitHub
API call was made. Bar: `docs/REVIEW.md`, "Tools for Claude" (owner, 2026-11-11). Decided limits in
`reviews/20-chrome/KNOWN-LIMITS.md` are not re-raised unless the code is worse than the entry says.

None of the three FIXes is in the guard, reader or binding logic. They sit at the edges of the tool: one reload
path skips the "unsaved typing" report, one owner-only command is reachable without sudo, and one shared-storage
query added by this branch makes Mail's reads fail on a full disk where main still answers.

## Findings

### FIX 1: `chrome_navigate(direction='reload')` reloads a taken tab without the unsaved-typing report

- `control/chrome/extension/background.js:923-932` (`navigate` branch: `reloadChecked(tab)` with the default
  `requireClean=false`), versus `background.js:912-921` (`prepare_control`) and `background.js:586-596`
  (`reloadChecked`, where the unsaved/playing check lives only when `requireClean` is true).
  `control/aresos_control/chrome/adapter.py:843-846` passes `navigate` straight to `free()` with no
  `needs_reload`/`reload_state` check; `control/aresos_control/chrome/definitions.py:47-48` exposes
  `direction: reload` and has no `reload_taken_tab` on `navigate`.
- Scenario: the owner has a half-written post in a tab. Claude takes the tab (`chrome_take_tab` keeps the
  document), then calls `chrome_navigate(tab, direction='reload')` as its first act, "to refresh". The tab reloads.
  The draft is gone. No `reload_required` was returned, so Claude never told the owner.
- Harm: the owner's unsaved text or playing media is lost silently. This is exactly the case the first-act reload
  rule (`briefs/20-post-18d.md`, decision of 2026-11-13; `SHARED` text in `chrome/definitions.py:17-19`) exists
  to prevent. The GET-only rule is kept (`reloadIdentity` still runs); only the report is skipped.
- Classification: **FIX** (data loss; breaking the owner's normal use).
- Smallest fix that closes the class: in the `navigate` branch call
  `reloadChecked(tab, null, command.reload_taken_tab !== true)` and add `reload_taken_tab` to the `navigate`
  schema (`definitions.py`, as `RELOAD` already does for the input verbs), so the same `reload_required`
  refusal with the same message applies. One fixture: a taken tab with a dirty textarea, `navigate reload`
  refuses; with `reload_taken_tab=true` it reloads.
- Related, for the lead to decide (not counted as FIX): `chrome_navigate(url)` and `chrome_close_tab` on a taken
  tab before its first reload destroy the same unsaved text with the same silence
  (`background.js:922,924`). They are navigations rather than reloads, and `close_tab` is described as "Close only
  a Claude tab", so I leave them as a question: either extend the unsaved check to both for tabs that still carry
  `popupNeedsReload`/not-preloaded documents, or record the choice in `KNOWN-LIMITS.md`.

### FIX 2: owner-only `chrome_sites allow` / `readonly off` are reachable over `chrome.sock` without sudo

- `control/chrome/extension/background.js:1073-1080` forwards the details page's `sites` request as an
  `owner_sites` event over the native port. `control/aresos_control/chrome/adapter.py:109-116` runs it with
  `self.engine.request({... 'action':'chrome_sites' ...}, admin=True)`, which skips the owner-only check in
  `control/aresos_control/engine.py:518-519`. `chrome.sock` is `0o666` and authenticated by peer uid only
  (`control/aresos_control/daemon.py:38,70-73`); the bridge handshake is a plain JSON `hello`
  (`control/aresos_control/chrome/bridge.py:44-57`). Claude Code runs as that uid.
- Scenario: Chrome is closed (or the real host is not connected; `bridge.accept` admits one live host). A process
  of the owner's user, for example a shell command Claude runs, connects to `/run/aresos-tools/chrome.sock`,
  sends `{"event":"hello","session":"x","version":"142.0.0.0"}` and then
  `{"event":"owner_sites","request_id":"r","arguments":{"command":"allow","operation_id":"<a done trusted-adapter
  send>"}}`. The service writes `chrome:allow:<id>`. From then on `chrome_submit_trusted` for that exact
  kind/account/parameters sends without a question (`adapter.py:748-759`). `{"command":"readonly","site":"https://x.test/","enabled":false}`
  lifts an owner read-only mark the same way.
- Harm: a standing "don't ask again" entry, which the design reserves for the owner behind sudo
  (`briefs/20-chrome.md:81`, tool text "Requires sudo on admin.sock", `chrome/definitions.py:76-78`), can be
  created by the owner's uid alone. That is a tool-created authority that later silences a send question. The
  KNOWN-LIMITS entry on imitating the native host says imitation adds nothing beyond "the user's existing
  capabilities"; here it adds a persistent service-side permission that the user's capabilities without sudo do not
  give, so the code is worse than the entry says. `owner_sites` is named nowhere in docs, briefs or earlier reviews.
- Classification: **FIX**, with the fix shape being the owner's decision because one option removes part of a
  specified feature (the details page's "don't ask again" buttons, `briefs/20-chrome.md:81`).
- Smallest fix that closes the class: in `adapter.event` serve only commands that tighten or read through the
  bridge (`list`, `revoke`, `readonly` with `enabled=true`) and refuse `allow` and `readonly enabled=false` with
  "use `sudo aresos admin chrome sites`". The details page keeps listing, revoking and marking read-only; only
  loosening moves to the terminal. Alternative that keeps every button: accept it, add the KNOWN-LIMITS line
  ("a same-uid process can create an allow entry while Chrome is closed"), and write an unacknowledged notice
  row for every allow/readonly-off that arrives over the bridge so the owner sees it in `chrome_notices`.

### KNOWN LIMIT 1: credential word list misses common identifiers

- `control/chrome/extension/reader.js:79-94` (`credentialLike`). The regex covers password/Passwort/Kennwort,
  passcode, PIN, OTP, one-time/security/Sicherheits-/Einmal-/Bestätigungs-/Zugangs-code and
  `-webkit-text-security`. Not covered: `passwd`, `pwd`, `pw` (very common `name`/`id` values), `passphrase`,
  `TAN`/`mTAN`/`SMS-TAN` (the German banking one-time code), `CVV`/`CVC`/`Kartenprüfnummer`,
  `autocomplete="cc-csc"`/`cc-number`, `Verifizierungscode`/`verification code`/`Authentifizierungscode`,
  `Geheimzahl`, `secret`. Label text is joined with spaces between child nodes (`reader.js:80-83`), so a label
  split by elements inside one word (`P<b>a</b>sswort`) does not match either.
- Harm: in an unwatched document every such `type=text` field is still withheld as a typed field and listed by
  its label in the `chrome_read_typed_fields` question, so the owner sees "TAN" or "CVV" before approving. In a
  watched document its value is whatever was typed after the reload, by Claude or by the owner typing into
  Claude's tab (board #138 case). Low harm, owner in the loop; the word list is a heuristic by design.
- Why acceptable: the asking read keeps the owner in control; the fix is a one-line regex extension (add
  `passwd|pwd|\bpw\b|passphrase|\btan\b|m-?tan|cvv|cvc|kartenprüfnummer|cc-csc|verifizierungs|verification|
  authentifizierungs|geheimzahl|secret`) plus joining label children with `''` for the match. Recommended in the
  next small round, not blocking.

### NOTE 1: `browsingTarget` treats an explicit empty `target=""` as absent

- `control/chrome/extension/reader.js:33-39`. Per HTML, `target=""` means the current navigable; the reader falls
  back to `<base target>`. Direction of error: the owner may be told "_blank" (or a named frame) while the
  navigation stays in the current tab. Cannot make a new-window navigation look like `_self`. Cosmetic; align
  with the spec (`explicit !== null` only).

### NOTE 2: untrusted marker has two shapes

- `control/aresos_control/chrome/adapter.py:776,827`: `tabs/downloads/bookmarks/history` and `sites list` put
  page-sourced titles and URLs at the top level with a boolean `untrusted_content: True`, where every other
  result nests them under `untrusted_content: {...}`. Content is `visible()`-escaped either way. Consistency only.

### NOTE 3: extension error strings reach Claude unescaped

- `control/aresos_control/chrome/bridge.py:102-106` turns `reply['error']` into `Refused(message)`; `engine.py`
  and `proxy.py` render `str(exc)` without `visible()`. Every `Error(...)` in the four extension files is a
  literal or a join of literals today, so nothing page-derived can ride along. A future page-derived message
  would bypass the escape; wrap `reply['error']` in `visible()` when convenient.

### NOTE 4: stale text after the 18d merge

- `control/settings/managed-settings.draft.comments.md:28-31` still says six rules and "only control and mail";
  there are eight (with `mcp__chrome__read_typed_fields`) and `chrome` is in `user-mcp.json`.
  `control/README.md:31` still says `chrome.sock` always refuses; it accepts the owner uid (`daemon.py:70-73`).

### NOTE 5: service-unit pin test ignores the comment line

- `control/tests/test_unit.py:10` and `control/chrome_tests/test_unit.py:10` drop `#` lines before comparing, so
  the comment above `RestrictAddressFamilies` is not pinned. The unit itself is byte-identical to `8b7e799c`
  (empty `git diff`), so nothing is wrong today.

### NOTE 6: hash and package traverse the tree the same way

- `control/chrome/build.py:14-15` and `control/checks/17-chrome/install.mjs:12` both use `rglob('*')` with
  `is_file()`; a file shipped in the CRX is always in the hash. Only `__pycache__` differs (hash excludes, pack
  includes), irrelevant for a JS tree. `builds.json` is still the empty format-1 list.

### FIX 3: `Store.iter_operations` forces `INDEXED BY operation_headers` with `ORDER BY k`, so Mail's reads fail on a full disk

- `control/aresos_control/storage.py:831-832` (`table='kv INDEXED BY operation_headers' if self.operation_headers
  else 'kv'`, then `ORDER BY k`), index defined at `storage.py:268-283` (branch commit `bc738001`). `k` is not in
  that index, so SQLite cannot return rows in key order from it and sorts in a temporary B-tree. No `PRAGMA
  temp_store` is set (grep: none), so above the page-cache threshold (a few hundred 3 KB operations) the sort
  spills to an unlinked temp file. `SQLITE_FULL` is classified as `storage_limit`
  (`control/aresos_control/common.py:38-40`).
- The query runs on the ordinary request path: `engine._pending` (`engine.py:180`, `exclude_app='chrome'`) feeds
  the pending notices that every result composes (`engine.py:50`), and `mail/adapter.py:785,818` use it for Mail's
  own listing. Confirmed with `EXPLAIN QUERY PLAN` on the package's index definition (SQLite 3.50.4): with
  `INDEXED BY operation_headers` the plan is `SEARCH kv USING INDEX operation_headers (<expr>=?)` plus
  `USE TEMP B-TREE FOR ORDER BY`; the same query on plain `kv` (main's shape) is `SCAN kv USING INDEX
  sqlite_autoindex_kv_1`, in key order, no temp B-tree; with the key range `k>='op:' AND k<'op;'` and a unary `+` on
  the `json_extract` filters it is `SEARCH kv USING INDEX sqlite_autoindex_kv_1 (k>? AND k<?)`.
- Scenario: the owner has a few hundred completed Mail and Chrome operations and the disk fills up (downloads,
  the image build, a log). Every tool call that composes pending notices, including `mail_read`, `mail_search`
  and `control_pending`, returns `storage_limit`. On main the same calls answer, because main's query sorts
  through the primary-key index without a temp file. Reads are the thing the owner most needs when the disk is
  full.
- Harm: Mail's read and search stop working under a condition that main survives; a regression this package adds
  to the shared base. Classification: **FIX** (breaking the owner's normal use). Owner state itself is not at
  risk: the committed-journal read path still shows open checks (below).
- Smallest fix that closes the class: in `iter_operations` select by the key range `k>='op:' AND k<'op;'` as
  `iter_items` does, prefix each `json_extract(...)` filter with unary `+` so the planner cannot choose
  `operation_headers`, drop the `INDEXED BY` switch and the now readerless index (`storage.py:268-283`,
  `_index_operation_headers`). Keep the SQL-side filters. Add an `EXPLAIN QUERY PLAN` regression test per variant
  asserting no `USE TEMP B-TREE`. (The analysis on `analysis/20-mail-sweep` at `36fb818e` reaches the same
  conclusion; confirmed, not refuted.)

### NOTE 7: merge `77cad19a` dropped two filters that are no-ops today

- The resolution of `77cad19a` removed an `a.asks` filter and the `'intent:chrome:'` prefix in the shared code
  path. At `a4143586` both are no-ops (every path that reaches them already filters the same way), so no
  behaviour from main or from Chrome was lost. Recorded so the next merge does not re-introduce them by accident.

### NOTE 8: no test exercises a sort spill at read time

- The Mail fault sweeps and the storage tests stay under the temp B-tree threshold, which is why FIX 3 was not
  caught by CI. The regression test in FIX 3 covers it by plan shape rather than by disk size.

## Mail interaction and owner state (items 4 and 7)

- **Mail integration changes** (`mail/adapter.py`, `mail/filing.py`, `notice_page`'s `extras`/`exclude_apps`):
  traced end to end. `exclude_apps` only keeps Chrome's rows out of Mail's page so they appear once, under
  Chrome's own `chrome_notices` (`adapter.py:183-212`); open checks (`intent:chrome:` in `started`/`unknown`) and
  unknown-outcome operations are yielded there as `check_only`/`unknown` rows and are never acknowledgeable while
  unresolved (`engine.py:620-642`). No path hides a pending question, drops a notice or lets a send go through
  without its bound content; Mail's send binding is unchanged from main.
- **R1 to R3 and the committed-journal read path** (`f3cfd5b1`, `3bf1b0d2`, `engine.py`, `chrome/committed.py`):
  every free Chrome input commits its context before dispatch (`adapter.py:620-629`, R2), approvals and stages are
  written before the bridge call and checkpointed (`engine.py:238-262,286-335`), and owner-state reads go through
  the committed projection (`Projection.sync`, `notice_rows`, `pending_rows`), so a failed or locked SQLite write
  leaves open checks and unknown inputs visible rather than marked done. `expire()` is skipped while the store
  is locked or a write failed (`engine.py:227-229`). Recovery resolves lost steps only to `stale` without any
  dispatch (`adapter.py:669-701`, `recovery.py`); `repair` is refused for Chrome (`adapter.py:497-498`); nothing
  is replayed automatically. Conflict resolutions in `77cad19a`, `4a4c531d`, `1628be4b`, `e2ee3a52` for
  `engine.py`, `recovery.py`, `storage.py`, `boundary_policy.py` were diffed against both parents: no main
  behaviour lost apart from NOTE 7's no-ops; Chrome's base changes (native socket, committed read path, owner-state
  reads) are present.

## Verified

Checked by reading the code at `a4143586` and running only browser-free tests. Paths relative to the repo.

1. **Base-URL class (`-b`).** Every destination source resolves against the document's effective base at action
   time, through native getters: `a`/`area` via `HTMLAnchorElement.prototype.href`/`HTMLAreaElement.prototype.href`
   (`reader.js:27,339-345`); SVG `a` via `SVGAnimatedString.animVal` of the native `href` (covers `xlink:href` and
   animated values) resolved with native `Node.baseURI` (`reader.js:31-32,343-344`); form `action` via the native
   `HTMLFormElement.action` getter and `formaction` via `button.formAction` (`reader.js:272`); `target`,
   `formtarget` and the first `<base target>` via `browsingTarget` (`reader.js:33-39,275-276,322`). The binding
   carries `href`, `browsing_target`, `form.action`, `form.target`, `form.browsing_target` and `form.element`
   (`adapter.py:41-58`, `background.js:725-733`); `destination()` is compared at revalidate and again on
   `stale_approval` (`adapter.py:439-440,538-541`), and the extension compares the whole binding immediately
   before input and again after arming (`background.js:938,971`). The guard's allowance re-reads
   action/method/encoding/target at submit time (`guard.js:246`) and the form owner through `mark.form !== form`
   and `step.button.form !== step.node` (`guard.js:196,492`), so a `form=` change re-asks.
   Search for other resolution sites: `grep -n "location\.|baseURI|new URL(|\.href\b|formAction|\.action\b"` over
   the five extension files. Results: `reader.js:452,539,544` report `location.href` as the current page address
   (informational, isolated world, not a destination); `guard.js:231` and `background.js:286,294,990` parse
   already-absolute values; `background.js:231,545,681,691,880` parse browser-side frame URLs from
   `webNavigation`. In `git diff 8f48c7bc a4143586 -- control/aresos_control control/chrome/native_host.py` no
   added line resolves a URL. No remaining place lets a `<base>` change rebind a destination. The round-3 fixture
   `control/chrome/ci/destination-fixtures.mjs` covers base, attribute, target, owner and animation changes per
   source, in the top frame and an inherited inline frame.
2. **Approval binding.** Question, operation id and description must be passed back in that exact order and
   equal the stored approval (`common.py:256-259`, `engine.py:286-293`); one use through the operation state
   machine and the extension's `used` set (`engine.py:294-295`, `background.js:938-944,863-864`); the guard's
   `resume` consumes the operation and checks form/submitter identity (`guard.js:490-498`). Bound: destination
   and target (above), form fields with values (`reader.js:263-278`), compose text with significant whitespace
   through a composed-tree walk (`reader.js:350-403`, bounded re-ask `adapter.py:458-469`), file SHA-256 computed
   from the live `File` and re-checked on install (`reader.js:170-212,509-518`, `background.js:883-909`), item
   text across shadow hosts and slots (`reader.js:328-338`). The session DNR block (rule 1: excluded hosts for
   controlled tabs; rule 2: `https://aresos-hold.invalid/` for held tabs, main/sub frame, ping, other;
   `background.js:363-371`) and the synchronous neutralisation (`guard.js:63-110`) cover `a`, `area`, SVG `a`
   (href, `xlink:href`, animated href and target), `form` (action, target), submit/image/reset buttons and inputs
   (disabled); remaining activation behaviours (checkbox/radio/summary/file/color/label/invoker commands) are
   harmless or dispatch a new click the capture sees. Composed-root passthrough: `foreignGuard` routes to the
   other controlled document's `route`, holds on `unknown`, and only an outside realm reaches the native fallback
   (`guard.js:311-325,445-447`, the accepted A-3 limit).
3. **Late reader (`-c` to `-f`).** `password()` runs before every value read and walks ancestors
   (`reader.js:95-102,213-215`); `credentialLike` checks name, id, autocomplete, aria-label, placeholder,
   `aria-labelledby` and `labels` text, English and German (`reader.js:79-94`); `-webkit-text-security` and
   `type`/`autocomplete` history through the document-lifetime observer (`reader.js:62-67,73-74`). A password
   revealed before take: the field is excluded by its credential signals or, failing those, withheld as a typed
   field in the unwatched document and only readable after the owner approves the label list. In an unwatched
   document every text-capable `input` (any current type outside the fixed list) and every `textarea` returns
   `filled`/`empty` only (`reader.js:216,228-241`), including through `renderedCompose`, `adapterRead` and
   `observe`; `filledStatus` imports the live control into an inert document and reads only validity. The asking
   read binds document id, reader instance, exact element ids, labels and types per frame, prepared by the service
   (`adapter.py:295-301,322-329`, `background.js:704-712,862-875`), is re-compared at `pending_state`,
   `revalidate`, before each frame and again after (`adapter.py:169-172,420-423`, `background.js:866-874`), and
   the reader refuses a changed list or a field that became credential-like (`reader.js:245-255`). A form with a
   withheld field is refused at prepare, revalidate and in the extension before input and after arming
   (`adapter.py:25-27,303,434,438,593`, `background.js:713-718,936,970`). Editors stay readable only through
   `isContentEditable` (`reader.js:223,232,243`), nothing broader; `typedField()` is the single predicate.
4. **Owner state.** See "Mail interaction and owner state" above; verified by reading the engine, storage,
   recovery and committed-projection code and the storage-fault tests under `control/tests/` and
   `control/mail_tests/` (plain Python, no browser).
5. **Taking a tab and reloading.** Take preserves the document (`admitTab`, `background.js:420-451`); the reload
   runs from `prepare_control`, which the service calls only when an input is prepared on a document that needs it
   (`adapter.py:594-596`, `background.js:912-921`), checks GET-only identity per frame (`reloadIdentity`,
   `background.js:578-585`; form-loaded or unknown-method documents refuse) and reports unsaved text, password
   fields, editors and playing media unless `reload_taken_tab=true`. Input in an unwatched document is refused
   until that reload (`background.js:937`). History steps refuse `form_submit` entries (`background.js:930`).
   Popups and new tabs join through `onCreatedNavigationTarget` with their opener's epoch and
   `popupNeedsReload` (`background.js:452-456,420-431`); a popup without a controlled opener refuses. Injection:
   the registered content script is only the inert `context.js` (`background.js:378-381`); `guard.js`/`reader.js`
   run only through the Debugger breakpoint on `context.js` in a prepared target of a controlled tab
   (`prepareTarget`, `assertTarget`, `background.js:78-88,171-219`) or `scripting.executeScript` under
   `controlled.get(tab)` (`lateReader`, `background.js:238-248`); `page.js` only through `Runtime.callFunctionOn`
   there. Exception to the rule: FIX 1 above.
6. **Least access and secrets.** Manifest permissions all used, no `storage`/`unlimitedStorage`/`key`/
   `update_url`/`externally_connectable`/`cookies`; grep for `chrome.storage|indexedDB|localStorage|sessionStorage|
   caches|openDatabase|cookieStore|document.cookie` in the extension: zero hits. Native host runs under
   `env -i`, `python3 -I -S`, relays length-framed messages up to 1 MiB only (`control/chrome/native_host.py`,
   `control/chrome/packaging/host`). `build.py` hashes every file under the runtime tree (`control/chrome/build.py`);
   `python3 -E -s control/generate.py --check` reports generated artifacts matching. Placeholders `EXTENSION_ID`,
   `UPDATE_URL`, `CRX_URL` present in `control/chrome/packaging/{native-host.json,policy.json,update.xml}`; no
   32-letter extension id anywhere. `git diff 8b7e799c a4143586 -- control/packaging/aresos-toold.service` is
   empty; both pin tests pass locally. What reaches Claude: results nest page content under `untrusted_content`
   and pass through `visible()`; no cookie, header or password value path exists (no `cookies` permission, no
   `Network.*` CDP method in `POLICY.cdpMethods`); mail app passwords stay in `mail/transport.py` with scrubbed
   outcomes and never enter a result. Settings: since `56f93c89` only `mcp__chrome__read_typed_fields` was added
   to `ask-rules.json` and `managed-settings.draft.json`, `managed-mcp.json` removed and `chrome` added to
   `user-mcp.json`, matching `briefs/18d-base-slim.md`; ask rules are generated from `ACTIONS`
   (`boundary_policy.py:20-24`), `submit` and `read_typed_fields` ask, `submit_trusted` is the trusted send with
   `require_trusted_send`; no `allow`/`deny`/bypass keys anywhere in `control/settings/`.
7. **Mail interaction.** FIX 3 confirmed with `EXPLAIN QUERY PLAN` against the package's own index definition
   (plans quoted there); integration changes traced as described above.
8. **Local runs.** `node --test` over the 25 of 27 `control/chrome_tests/*.test.mjs` files that need no `.work/`
   directory: 364 tests, 364 pass, 0 fail (output in the scratchpad, not in the tree). The two skipped files are
   CI-record tests (`qualification-completion`, packing), not guard logic. `git status --porcelain` empty before
   and after. Plain-Python: `test_unit.py` (both copies), `test_bridge.py`, `test_policy.py`, `test_questions.py`
   pass; `background.test.mjs` 124/124.
