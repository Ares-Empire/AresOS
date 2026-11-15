# 20, review fixes: every finding of the panel on 60b94384

Seven reviews of `60b94384` all say CHANGES-NEEDED: `reviews/20-chrome/REVIEW.md` (package, "PKG"),
`SECURITY-REVIEW-A.md` to `-E.md` ("A" to "E") and `REVIEW-CLAUDE.md` (the lead's Claude reviewer, "CL"). This brief
lists every finding once, deduplicated, and splits them between **two builds running at the same time** (owner's
direction, 2026-11-10: parallel where it helps; still one fix round):

- **Part P, the page build**, on `pkg/20-chrome` in `~/AresOS-20-chrome`;
- **Part S, the state build**, on `pkg/20-chrome-state` in `~/AresOS-20-state`, with a draft PR into `pkg/20-chrome`.

Each build reads the review files for the reproductions; the item references name them. The earlier briefs stand;
where they differ, this brief wins. The stop rule is `20-continue-2.md`'s: a bug a test finds is fixed; stop only when
a guarantee can't be met by any design. Every fix gets a test that fails without it (a mutation that removes the fix
must fail at least one test), browser cases with the receiver's log (0 before approval, 1 after, 1 after a repeat).

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

## Part P: page, extension, classification, binding, questions (`pkg/20-chrome`)

Blocking:
- **P1** Answering a native dialog resumes page code with no hold: arm a private hold before answering; if that
  can't be done while the modal is open, refuse and leave the dialog to the owner. (PKG-1, B-4)
- **P2** Inline frames (`about:blank`, `about:srcdoc`, same-origin) are skipped in reading, binding, arming and the
  reload's dirty check. Cover eligible frames by authenticated document and origin; when a relevant frame can't be
  covered, refuse (a generic send) or report (the reload). (PKG-2, A-2, B-5, C-5, CL-F3)
- **P3** A frame created or replaced during the hold starts without it: new guards inherit the active hold (never an
  approval allowance); compare frame coverage again right before input and arm or refuse. (A-2)
- **P4** A wrapper called on an element of **another live controlled document** takes the native path. This is a gap
  in `20-continue-3.md`'s passthrough rule; the lead's decision (2026-11-10): keep native behaviour for non-Nodes,
  detached nodes and documents without a browsing context; route a call on an element of another controlled
  document through **that document's guard**, and hold it when ownership is unclear; never take the native path for
  an element of a controlled document. Tests: an element of a same-tab iframe, an element of another controlled
  tab's document, and an element of a document outside the group (native, untouched). (A-1)
- **P5** A shadow root created and used in the same handler escapes both the wrappers' hold (composed root) and the
  fallback's stop or `unknown`: capture must exist before page code can activate a control in a new root; prove the
  `composed` part with a test double that honours it and a browser fixture. (A-3, CL-F4)
- **P6** Equivalent key spellings bypass classification (`Shift+Delete`, `Ctrl+Backspace`, `Shift+#`): canonicalise
  the key once, classify and dispatch the same tuple. (PKG-3, B-1)
- **P7** Malformed URL escapes make the service and the page guard decode differently: one decoding rule in both,
  malformed escapes and invalid UTF-8 included. (B-2)
- **P8** Decomposed Unicode spellings of list words don't ask: one shared normalisation before folding, in both
  implementations, versioned with the word list. (B-3)
- **P9** An adapter's recognition overrides an explicit pay or delete cue and makes it trusted: explicit
  deletion/payment evidence in any required channel wins, and the trusted-send check independently refuses deleting,
  paying and WhatsApp messages. (PKG-4)
- **P10** The affected item misses ARIA items (`listitem`, `row`, `article`) and named regions. (PKG-5, B-9)
- **P11** A send confirmation ("Send this message?" OK) doesn't bind the draft outside its dialog. (B-6)
- **P12** A selected file is bound by name, size and date only: bind its content identity (the staged hash where it
  exists); refuse when it can't be verified. (B-7)
- **P13** Rich-text drafts lose line breaks in the binding. (B-8)
- **P14** Unsubscribe/Abbestellen is bound as a message send: bind the affected item instead. (B-10)
- **P15** A `title` hides a visible "Delete": button content comes before the title in the accessible name, shared by
  classification and the guard. (C-8)
- **P16** Reading an iframe's `srcdoc` collects raw HTML with password values: never read the attribute's value.
  (C-1)
- **P17** Releasing and retaking a tab resets the sticky password protection: keep it per document across
  reinjection; if it's lost while the document survives, refuse unsafe reads. (C-2)
- **P18** A protected editable field's descendants, and a field that stopped being editable, leak: check sticky
  membership first and exclude the whole field's content. (C-3)
- **P19** `Runtime.enable` delivers console arguments and exceptions (possibly password values) to the extension.
  Lead's direction: first try to avoid `Runtime.enable` entirely (for example `Page.createIsolatedWorld` returns its
  `executionContextId`, and `Runtime.evaluate`/`callFunctionOn` take a `contextId`). Test: in a page that logs a
  password field's value, no `Runtime.consoleAPICalled` or `Runtime.exceptionThrown` event reaches the extension;
  audit every incoming protocol event in the test build. **If `Runtime.enable` truly can't be avoided, stop and report
  the exact event flow to the lead**, who decides. Don't build a workaround that drops the events after delivery.
  (C-4)
- **P20** Owner Enter (the lead's ruling): it stays "passes in CI, panel to confirm" until this exists. Add tests that
  each fail when one check is removed: the exact form, the exact submitter, the trusted-event check, the mark's
  clearing; a browser variant whose timer really fires **while his mark is set** (his Enter handler submits another
  form, and his form with another submitter, synchronously); an unconsumed mark followed by a delayed submission;
  relabel the existing timer variants as "after his mark". (CL-F1, CL-F6)

Should-fix:
- **P21** A GET search form's ordinary input asks on Enter. (B-11)
- **P22** Questions: name the action and the key ("delete 'Quarterly report'"), include and bind the page title;
  recipients and names bounded with exact "and N more" counts and long names described by position and length, the
  full values below. (B-12, PKG-8)
- **P23** Acting results and the `page` stage carry stock text: collect a bounded post-input observation (address,
  notice, dialog, change), or say plainly it's unavailable. (PKG-7, B-13)
- **P24** The reload check: typing during its final identity query isn't noticed; detached or Web Audio playback
  isn't seen (use the tab's `audible` state too); a frame that can't be inspected counts as possibly unsaved. (E-1,
  E-2, CL-F3)
- **P25** A no-op (an already-ticked box) or an isolated-world action activates his tab: activate only for native
  input that needs it. (E-3)
- **P26** The wrappers have an own `prototype` (detectable); the compatibility test can't see our script: use
  non-constructible wrappers with native property shapes, and add a fingerprint that differs in a Claude tab and is
  equal outside. (E-4, CL-F2)
- **P27** After Stop, the tab's navigation blocks stay while native cleanup waits: lift them at once, keep cleanup
  pending separately. (E-5)
- **P28** A refusal after arming leaves the in-flight mark set for good: close every armed dispatch on every path,
  over-covering until the page has handled it. (A-4)
- **P29** CI green must mean every named case ran: fail unless the names equal the inventory and every verdict is
  true (group 12 false until 18d). (CL-F5)
- **P30** The password matrix: every variant in cross-site frames, through `read`, `read_form`, preparation and the
  final binding, with browser ingress and sensitive getters instrumented, and a fragment-safe scan. (PKG-9, C-7,
  CL-F10)
- **P31** Nits: a unit test for the popup's first-act reload (CL-F7); a script-started POST into a tab and a popup
  (CL-F8); the excluded-popup leg asserts the popup exists (CL-F9); the first-script capture in `<head>` (CL-F11); the
  GET excluded form carries its case field (CL-F12).

## Part S: state and storage (`pkg/20-chrome-state`)

Blocking:
- **S1** Restoring SQLite brings back revoked "don't ask again" entries, drops read-only restrictions and older
  qualification records: reconcile them from committed history before the restore lock is released. (D-1)
- **S2** Normal reads of Chrome operations and pending items bypass committed history while SQLite is readable (an
  older restored SQLite; a failed commit-marker append): derive Chrome status and pending from the committed record
  on every read, plus live checks. (D-2)
- **S3** Restore turns an acknowledged cancellation or expiry into new uncertain work: keep committed terminal
  outcomes and acknowledgements. (D-3)
- **S4** Finished Chrome checks fill the shared 512-record unfinished-change limit for good (and can block Mail):
  retire and archive them, keeping history and acknowledgement identities. (D-4)

Should-fix:
- **S5** A normal stopped submission leaves a false "interrupted" warning. (D-5)
- **S6** Open checks never resolve after Chrome loses its queue: reconcile them with the live session; commit a
  non-resumable stale result; never replay. (D-6)
- **S7** `chrome_drop` can't use cancellation's recovery admission. (D-7)
- **S8** Going over the projection's index bound blocks the archive command it recommends. (D-8)
- **S9** The fallback drops Mail's `notices_more`: Mail's behaviour must be unchanged. (D-9)
- **S10** Chrome orders notices in seconds, Mail in nanoseconds: one unit. (D-10)
- **S11** The sweeps and the oracle: every public view compared during persistent exhaustion and after space
  returns without restart; the oracle derives expectations from the scenario and receiver history, not from
  production's rows; add the probes above. (D-11)
- **S12** Page text outside untrusted marking: audit summaries, `read()`'s dialog, stopped-activation follow-ups,
  stages and evidence all carry page text only inside `untrusted_content`. (PKG-6, C-6, D-12)

The lead's conditions on the committed-journal read path stand: it reads only the committed journal, writes nothing
beside the record, and stays in a form 19b's projection can absorb without migrating acknowledgements. Don't build a
second projection.

## Files

- **Part P owns** the extension, the reader, `policy.py`, `sites.py`, `definitions.py`, `unicode_words.json`,
  generated artifacts, the CI harness and fixtures, and in `adapter.py` the classification, binding, question and
  dispatch code.
- **Part S owns** `engine.py`, `storage.py`, `recovery.py`, `retention.py`, `committed.py`, `qualification.py`'s
  stored-state reads, `mail/filing.py`, the state tests and the sweeps, and in `adapter.py` the notice, check,
  recovery, owner-list and `read()` result code.
- Keep `adapter.py` edits to your own functions. Need a change in the other part's files? Make the smallest one and
  name it in your report, so the package lead can merge.

## Reports and runs

- Part P updates `reviews/20-chrome/REPORT.md`; part S writes `reviews/20-chrome/STATE-FIXES-REPORT.md`. Map every item
  to its fix and tests (mutation that fails), with run IDs and log lines. Interim reviews are `BUILD-*.md`.
- Runs of `control-chrome.yml`: part P about 40 more on `pkg/20-chrome` (≈155 in all); part S about 15 on its
  branch. Part S starts its runs by hand, since pushes to its branch start none: `gh workflow run
  control-chrome.yml --ref pkg/20-chrome-state` (and the same for `control-mail.yml` and `control-base.yml`). If a part would pass its count, say so in its report and stop.
- Part P: the whole set green twice on its final head, base, Mail and boundary too. Part S: its suites twice.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in your worktree, on your branch. Don't merge other branches. Commit in small steps and push your branch.
  Never merge, never push to `main` (part S: nor to `pkg/20-chrome`), never force-push.
- Read the specification from `origin/main` with `git show` after `git fetch origin main`.
- Don't edit `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`, `README.md`, anything under `os/` or
  `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md` or `HANDOFF.md`.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- No secrets, real addresses, account names, provider names or real sites; fixture hosts only (`.test`).
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.
