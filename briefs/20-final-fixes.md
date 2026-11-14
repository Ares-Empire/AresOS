# 20, final fixes: one combined round after the final reviews

The last fix round for package 20 (draft PR #27). Two fresh reviewers read code head `a4143586`:
- the package review, [REVIEW-FINAL.md](../reviews/20-chrome/REVIEW-FINAL.md) (Opus), 5 FIX;
- the security review, [SECURITY-FINAL.md](../reviews/20-chrome/SECURITY-FINAL.md) (Fable), 3 FIX.

One FIX is in both reviews (F1), so this round has seven fixes, F1 to F7.

The lead (mac-aresos-control) set the positions below on 2026-11-14. The earlier briefs (`20-chrome.md`,
`20-post-18d.md` and its addenda `-b` to `-g`) stand; where they differ, this brief wins. The builder is now a Claude
agent (owner, board #222: "Claude finishes it"), because Codex's allowance has run out.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

## The fixes

### F1. Mail reads fail on a full disk (both reviews; analyst `mail-sweep-growth.md`)

`Store.iter_operations` (`control/aresos_control/storage.py` about 831–833, from `bc738001`) forces
`INDEXED BY operation_headers` together with `ORDER BY k`. `k` isn't in that index, so every variant sorts in a
temporary B-tree. From about 300–700 retained operations the sort spills to a temporary file. It runs on every
request (pending notices, `engine.py` about 180, 727, 811), so on a full disk Mail read, search and
`control_pending` return `storage_limit` where main answers.

- **Fix (verified by the security sub-review, matches the lead's spec):**
  - use the key range `k>='op:' AND k<'op;'` as `iter_items` does;
  - put a unary `+` before each `json_extract` filter so the planner can't pick `operation_headers`;
  - drop the `INDEXED BY` switch, and drop the `operation_headers` index itself (`storage.py` about 268–283) once
    nothing reads it;
  - keep the filtering in SQL;
  - if a query shape still needs a sort, prefer an index whose order matches `ORDER BY k`. `temp_store=MEMORY` is a
    last resort, and only with a stated bound on the sort size.
- **Tests:**
  - an `EXPLAIN QUERY PLAN` test for every `iter_operations` shape, before and after `ANALYZE`, pinned to show no
    `USE TEMP B-TREE FOR ORDER BY`;
  - a full-disk test with 1,000 or more retained operations, where Mail read and search (and `control_pending`)
    still answer as on main;
  - a removal probe that puts the forced index back and shows those tests fail.
- **Re-measure Mail's per-call time** with the analyst's harness
  (`reviews/20-chrome/records/post18d/mail-sweep/`, same method, same machine, against `b2b51107`). It must stay
  at or below main. Record the result next to `mail-sweep-growth.json`.

### F2. Credential detection misses common names (package FIX-2; security KNOWN LIMIT 1)

`credentialLike` in `control/chrome/extension/reader.js` (about 73–94):
- **Add the reported names:**
  - CVC, CVV, CSC, card security code, `autocomplete="cc-csc"`;
  - TAN, mTAN, SMS-TAN;
  - Geheimzahl, Kartenprüfnummer, pincode, `pwd`, `passwd`, `pw` (as a whole token), passphrase, secret;
  - verification code, Verifizierungscode, Authentifizierungscode, Bestätigungscode.
- **In the same pass, look for other common English and German variants:** one-time PIN, OTP forms,
  Sicherheitscode, PUK, PINs next to an IBAN, and similar.
- **Match label text split inside a word** (`P<b>a</b>sswort`) as well as label text split between words.
- **Tests:** one test row per added name or token, each in the label, `name`, `id` and `autocomplete` forms where
  they apply, and a removal probe.
- **KNOWN-LIMITS.md:** add the line REPORT.md already claims exists (REPORT.md about 64–65). Credential detection is
  a word heuristic, so a revealed secret with no recognised signal is read in a watched tab, and after an approved
  asking read in an unwatched one. The harm is one owner-typed secret exposed. It is accepted because the word list
  is a heuristic by design: masked and `type=password` history always protect, and the asking read shows the
  labels.

### F3. The browsing target is resolved in script (package FIX-3, `-b` class; security NOTE 1)

`browsingTarget` (`reader.js` about 33–39) and the routes that feed it:
- **Fix the reported routes:**
  - a decoy `<base>` that isn't HTML;
  - sanitising broader than the HTML rule;
  - SVG `xlink:show="new"`;
  - an explicit `target=""` means the current navigable, as HTML defines it (security NOTE 1).
- **Correct REPORT.md about 52–53,** which says the extension uses "native browsing targets"; it doesn't.
- **Residual:** if anything remains that only Chrome itself could decide, write it into KNOWN-LIMITS.md plainly:
  what it is, the harm, and that it is accepted because the address and the request stay bound.
- **Tests:** browser rows for each route (one batched run, see "Runs"), plus the missing rows the package review
  names: a target change on `area`, a plain SVG `target` change, and form-owner rows beyond formaction controls.
  Make REPORT.md about 280–282 say only what the rows cover.

### F4. The latency check passes a median-only breach (package FIX-4)

`control/chrome/ci/latency-check.py` (about 93–94) fails a call only when both median and p95 cross. The lead did
not accept that for the ceilings:
- **Ceilings:** a call fails if its median **or** its p95 is over the ceiling (with the runner-noise allowance as
  now).
- **Comparison with the old measurement:** keep "both must cross" there, against runner noise.
- **Removal probe:** a median-only breach (for example a read at 50/55 ms against 35/60) must fail.
- **Records:** update the `policy` string and REPORT.md.

### F5. Absolute user paths in three record files (package FIX-5)

- `reviews/20-chrome/records/integrate3/f25-strict-audit.txt:6`;
- `reviews/20-chrome/records/integrate3/popup-regressions-before.txt` (lines 23, 40, 57, 58, 75, 76);
- `reviews/20-chrome/records/integration-verdict-subsets-red.txt:28`.

Make them repo-relative. This is tidiness only; leave the branch's history alone.

### F6. `chrome_navigate(direction='reload')` drops the unsaved-typing report (security FIX 1)

`background.js` about 923–932 reloads a taken tab through `reloadChecked(tab)` with `requireClean=false`. That skips
the report on unsaved typing and playing audio that `prepare_control` gives (about 912–921), so the owner's draft in
a taken tab is lost silently.
- **Fix:** route it through the same report as the first act. Pass `reload_taken_tab !== true` as `requireClean`,
  and add `reload_taken_tab` to the `navigate` schema (`control/aresos_control/chrome/definitions.py` about 47–48).
  Keep "never reload a POST".
- **Tests:** a browser row for the report and one for an explicit `reload_taken_tab=true`, plus a removal probe.

### F7. Owner authority over chrome.sock needs polkit (security FIX 2): decided as (a)

**The problem.** Any process of the owner's user can pose as the native host while Chrome is closed, including a
shell command Claude runs. It can send `owner_sites allow` or `readonly off`. The service then writes an allow
entry without sudo (`adapter.py` about 109–116 runs it with `admin=True`; `chrome.sock` is `0o666` and checks only
the peer's user id, `daemon.py` about 38 and 70–73). After that, `chrome_submit_trusted` sends without a question.

**The decision.** The lead chose **polkit confirmation** on 2026-11-14, which keeps every button of the details page
and needs the same authority as sudo. Conditions:

1. **A polkit action**, for example `org.aresos.control.chrome-loosen`:
   - `allow_any=no`, `allow_inactive=no`, `allow_active=auth_admin`;
   - **never `auth_admin_keep`**: a cached authorization would let a spoofed request inside the cache window pass
     silently;
   - one confirmation per change.
2. **The subject** is the process that actually connected: its pid plus start time from `SO_PEERCRED`. User
   interaction is allowed, so the dialog appears in the owner's session.
3. **The dialog names the change:** the site, the action kind and the account, or "read-only off for <site>", if
   polkit can carry the details. If it can't, the details page shows exactly the pending change while the dialog is
   up, and the service binds the confirmation to that one change.
4. **Refusal:** if the request is denied, no agent answers, it times out, or polkit is unavailable, the service
   refuses with the reason and writes nothing.
5. **Close the class, not the case.**
   - List every message the service accepts over `chrome.sock`.
   - Mark each as owner authority (it loosens, approves, or marks something as the owner's own act, such as his
     Enter mark or his clicks) or not.
   - Each one with owner authority goes behind the same confirmation, unless you show it can't loosen anything when
     spoofed.
   - Put the table in REPORT.md.
   - Listing, revoking and turning read-only on stay without a prompt.
6. **Tests in CI, with a polkit stub:**
   - a spoofed host (a plain process as the owner's user id) sending `allow` and `readonly off` writes nothing
     without a success;
   - a success writes exactly the confirmed change;
   - a cached or replayed success is refused;
   - removal probes for each.

   Real polkit with a real agent is linux-tools' 18c-b image test. Name the policy file and its install path
   (`/usr/share/polkit-1/actions/`) in REPORT.md and in `control/chrome/packaging/README.md`, so the lead can hand
   it to linux-aresos at merge.

7. **The service must be allowed to ask.** polkit lets a caller check authorization for another identity's
   process only if the caller is root, or if the action names the caller with the
   `org.freedesktop.policykit.owner` annotation (for example `unix-user:<the service's user>`). `aresos-toold`
   doesn't run as the owner. Without the annotation the check fails with "Only trusted callers…", and the buttons
   would always refuse. A stub won't show this.
   - The policy file carries `org.freedesktop.policykit.owner` for the service's actual user, taken from the
     unit. If it isn't needed, show why.
   - The service reaches the system bus under the unit's sandboxing. `AF_UNIX` is allowed; check that nothing
     else blocks `/run/dbus/system_bus_socket`. Don't touch the pinned network lines. If the unit would need a
     change, stop and tell the lead.
   - Where feasible, one CI case runs real `polkitd` in a container with a test agent (`pkttyagent`). It calls
     the check as the service's user against a process of another user id: allowed with the right password,
     denied with a wrong one or none. If that isn't feasible in this round, say so in REPORT.md and leave it to
     linux-tools' 18c-b image test, named explicitly.

The final security re-check of F7 goes to a fresh Fable reviewer.

### Notes to fold in (both reviews)

- **Withheld-form refusal:**
  - After it refuses, the instructions name the working retry route, `chrome_navigate direction=reload`, now with the
    F6 report.
  - It runs before the reload path. That ordering is fine, but say so in the tool text.
- **The typed-read question** (`adapter.py` about 298): quote each field label and cap its length, so one hostile
  label can't look like several fields. Show each frame's site next to its Chrome id.
- **Remove the dead code** from `-f`'s dropped provision (`reader.js` about 229–231 and 253).
- **Extension error strings:** wrap `reply['error']` in `visible()` before it reaches Claude (`bridge.py` about
  102–106).
- **Stale text after the 18d merge:**
  - `control/settings/managed-settings.draft.comments.md` about 28–31 says six rules, but there are eight, including
    `mcp__chrome__read_typed_fields`.
  - `control/README.md:31` says `chrome.sock` always refuses, but it accepts the owner's user id.
- **Stale receipt:** in `reviews/20-chrome/records/post18d/mail-eight-shard-inventory.json`, set
  `job_timeout_minutes` to 120 to match `096c3088`.
- **The service-unit pin tests** (`control/tests/test_unit.py:10`, `control/chrome_tests/test_unit.py:10`) also pin
  the comment lines. The unit itself must stay byte-identical to `8b7e799c`.
- **Optional, only if cheap and safe:** one shape for the untrusted marker (security NOTE 2). If it changes a result
  shape Claude relies on, leave it and say so.

### Mail's fault sweep (lead; test changes, not blockers)

- **Production cache key.** Bring the sweep back to production behaviour, using the real cache key instead of a new
  journal timestamp per stat, only if every distinct fault site stays covered, including the cache-miss path once.
  If the new timestamp per stat was a deliberate cache-miss test, keep one such case and drop the identical repeats.
  Record the case counts before and after: main 28,519, branch 110,065 today. Dropping `operation_headers` (F1) also
  removes the 272 extra single and persistent cases.
- **`build-id.json` fixture.** It may be added, so tests don't hash 92 runtime files at every engine start, as long as
  one test still covers the missing-file path.
- **REPORT.md** gets the Mail sweep paragraph from `records/post18d/mail-sweep-growth.md`, with all three numbers:
  - cases 28,519 → 110,065, with the causes;
  - time per case 1.15×;
  - Mail's own calls equal or faster, with the one +0.06 ms read cost and the safety property it buys.

  Then the counts and per-call times after F1 and the sweep change.

## Rules

- **Builders work in steps:** one fresh agent per step, about 80 tool calls. Keep `reviews/20-chrome/PROGRESS.md`
  current (done, left in order, what the code doesn't show), and keep the Handover at the top of `REPORT.md` current.
  If your file tool refuses to edit `REPORT.md`, edit it with a short script, or leave the text in `PROGRESS.md` for
  the package lead to commit.
- **Commits:**
  - Commit and push `pkg/20-chrome` at every finished step, with `[skip ci]` in the subject. Never force-push, never
    use `--no-verify`, never push to main, never merge the PR.
  - Don't merge main in this round. `origin/main` has moved without `control/` changes, and a trial merge is clean.
  - If the privacy check blocks, fix the content.
  - The trailers name the model that did the work, for example `Co-Authored-By: Claude Opus 5.5
    <noreply@anthropic.com>`.
- **Runs:** browser evidence goes in single runs (`gh workflow run control-chrome.yml --ref pkg/20-chrome`). Batch
  every browser row of F2, F3, F6 and F7 into as few runs as possible; at most about 280 `control-chrome.yml` runs on
  `pkg/20-chrome` in all (255 used). The final pair and every Control workflow twice come **after** the scoped
  re-check, not in this round.
- **GitHub API:** the shared allowance (5,000 calls an hour) ran out once. Watch runs only with
  `gh run watch --interval 60` or longer, and sleep at least 60 s in any gh loop. On a rate-limit error, wait for the
  reset (`gh api rate_limit`); never retry in a loop.
- **Don't change:**
  - the service unit's network lines (linux-tools pins them from `8b7e799c`);
  - `docs/control/CONTROL.md`;
  - tab-group handling;
  - the 525 ms hold window;
  - the asking bindings, except as F2, F3 and the typed-read note say;
  - `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`, `README.md`, `os/`, `mod/`, `docs/INSTALL*`,
    `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`.
- **linux-tools builds on this branch.** Its `pkg/28-chrome-read` was cut from `pkg/20-chrome` at `524173c4` and
  adds new files only.
  - Don't rename or move `control/aresos_control/chrome/` or its test folders without telling the lead first.
  - #27 will merge with a merge commit, so keep the branch history exactly as it is: no rewrites, no squashing.
- **No persistent extension storage:** no chrome.storage, IndexedDB, localStorage or sessionStorage in the extension,
  no `storage` or `unlimitedStorage` permission, no `key` in `manifest.json`. linux-tools' image gives the extension
  a fresh key per image. Tell the lead before adding any.
  - `control/chrome/build.py` keeps hashing the source tree.
  - The packaging templates keep `EXTENSION_ID`, `UPDATE_URL` and `CRX_URL`.
- **Never name or guess the owner's mail provider.** No personal data; write paths repo-relative.
- **Stop and report** (in `PROGRESS.md` and your last message) when:
  - a fix would remove a feature;
  - a fix needs a decision these briefs don't make;
  - a test can't be made to fail without its fix.

## Done when

- F1 to F7 and the notes are built with their tests and removal probes.
- The full local preflight passes (`.work/post18d/final-local.py` or its successor), with the counts in the Handover.
- One batched browser run passes the new rows.
- REPORT.md, KNOWN-LIMITS.md and the Handover are true.

Then the package lead runs the scoped re-check.
