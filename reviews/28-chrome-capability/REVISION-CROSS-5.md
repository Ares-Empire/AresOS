# Revision after BRIEF-CROSS-5

Documentation revision for `linux-tools`, 2026-11-18. Branch `briefs/28ab-cross-5`, from `main` at `918fba67`.
No product code. All six findings are accepted; the two owner choices below remain open. This is a proposed
build contract, not browser-test evidence or permission to implement an unresolved owner choice.

## What changed per finding

1. **Profile pinning — 28b “1. What Claude sees”; 18c-b “CROSS-5 identity handoff”; CONTROL “How the tool reaches
   Chrome” / “Which tabs Claude works in”.** Separate a durable logical service pin from the disposable extension
   installation id. Recommend owner-confirmed relinking after replacement, with automatic reconnection only for
   the current exact pair. A → B → A keeps the logical pin, accepts each replacement after that confirmation,
   and refuses another profile or a retired pair. No automatic migration based on the image or extension id.
   The sole proposed IndexedDB exception stores that installation id; the storage test stays and forbids other
   data/APIs. Owner question 1 explicitly covers the interruption after updates. Tests/mutations cover both the
   persistent pin and the refusal before relinking; a stand-in hello is not the combined browser proof.

   **Code checked:** main `control/aresos_control/chrome/bridge.py:49` accepts only session/version and remembers
   no profile. `control/chrome/extension/background.js:1137` sends that hello. The original 18c-b “The design,
   as settled” and item 1 require a fresh key and ban storage. Its branch's actual
   `control/chrome_tests/test_extension_stores_nothing.py` confirms that conflict. The branch progress records
   steps 1a–2b as built, including A/B/A installation; that is not evidence of a future service pin.

2. **Held submission loss — 28b “4c. A held submission checks the work its resumption could discard”, item 4's
   exception, frozen-path list and build order; CONTROL “How an asking action runs”, owner-delayed input and
   “Known limits”; ALIGNMENT “After BRIEF-CROSS-5”.** The earlier held-resumption exception is withdrawn. Check
   all forms and frames before preparing and immediately before resuming. Recommend one managed send/loss
   question, with private freshness evidence; no discard flag, no trusted-send bypass and no preliminary reload.
   Changed work fails the old operation and requires a fresh combined question under the original expiry.
   Board #138 stays in taken-tab tests: the same held native submission resumes once after approval, without
   repeating the input that caused it. The two-form test names the unrelated draft's loss; mutations skip the
   preparation/recheck, narrow the check to the submitted form, exempt delayed owner input or reload first.

   **Code checked:** main `adapter.py:788` prepares queued submissions through `payload(hold=…)` and reserves
   them; `adapter.py:659` builds the form payload. `background.js:1039` shares input/resume setup and compares
   bindings at `1043` and `1076`, but has no unrelated-work check on resumption. `adapter.py:833` also needs the
   explicit exclusion of possible-loss operations from trusted sends. `docs/REVIEW.md:40` treats data loss as a
   fix; the prior ALIGNMENT exception was a lead decision, not an owner override of this finding.

3. **Recognised link actions — 28a “4. chrome_open and chrome_go”; 28b “2. Looking in place”; CONTROL “Going to
   pages and acting” / “What is free and what asks”.** A link reference is checked and classified as a click
   before opening anything. If it would ask, opening refuses and names the asking action path. Arbitrary supplied
   URLs, tab-address copies and library entries keep their accepted policy; a refused reference can't fall back
   to it. Delete/Unsubscribe GET fixtures assert zero requests from click and reference-open before approval.
   Removing classification must fail that receiver test.

   **Code checked:** main `adapter.py:659` already classifies a selected target through `recognize`/`classify`;
   `adapter.py:716` free-open creates a tab then navigates it. There is no new `chrome_open(ref=…)` on main yet:
   the gap is in 28a's contract connecting those paths, not an allegation that the unbuilt tool already exists.

4. **Reload freshness — 28b “4d. Private freshness for every loss approval”, item 4 and Paths; CONTROL “Which
   tabs Claude works in”.** Bind actual field/frame/document/reader identities and monotonic edit generations.
   Later typing, a further canvas stroke or continuation of one already in progress invalidates approval even
   if every displayed loss label stays identical. Frame removal retains evidence; final queries catch delayed
   reports. An unwatched document can ask only with observation proven from before preparation through dispatch;
   missing evidence refuses without approval. Tests record that unread values stay unread. Mutations retain only
   first-use state, compare labels, accept a missing watcher or trust delayed reports.

   **Code checked:** main `reader.js:525` reports labels, typing ownership and media, not an owner-edit
   generation. The old 28b item 4 only required first-use reporting and sticky use. Its general “page changed”
   wording did not define evidence for continued edits. The proposed watcher is additional allowed work, not a
   claim that main already supplies it.

5. **Untrusted loss text — 28a “5b. Loss refusals carry page text only as untrusted content”, inherited reload
   policy, frozen-path exceptions and Paths; 28b item 0 and loss questions; CONTROL loss-report contract.** Keep
   a fixed service-written `reload_required` code/message and carry labels in `untrusted_content.loss`; approvals
   use `description.untrusted_content.loss`. Apply this to bare errors, batched steps, kept tabs, operation status,
   stages and notices. Schemas and transport must preserve the envelope. Hostile labels with instructions and
   serialization delimiters test each surface; interpolation/flattening mutations must fail.

   **Code checked:** main `background.js:671` (`requireDiscard`) interpolates labels into the exception at
   `685`; `reader.js:527` creates those strings. `bridge.py:106` turns the extension error into `Refused` text;
   escaping there supplies no untrusted envelope. The revision explicitly permits the necessary narrow shared
   error-serialization support instead of leaving a frozen-path contradiction.

6. **Section 6 parity — CONTROL “Reading a page” and “Known limits”; 28a item 0 / “CROSS-5 regression
   contracts”.** Copy the mixed-case/digit random-token rule allowing `_` and `-`, and defer to brief 28's full
   address algorithm. State the 5,000-reference cursor ceiling and usable alternatives, including the small
   fold-count effect. Retain separator-token and >5,000-reference tests; removing that token branch or cursor
   reference-text binding must fail them.

   **Checked against the normative brief:** `briefs/28-chrome-read.md:650` adds the separator rule and `:662`
   names the ceiling for section 6. Main still has the old reader; this is synchronization with package 28's
   specified/implemented successor, not a new main-code fix.

## Package 28 changes carried forward

28a item 0, 28b item 0 and CONTROL's “Unicode at the native boundary” require every fresh-side comparison with
service-held page facts to use `wellFormed()` repair. This includes fingerprints, fields/descriptions, both
approved-input comparisons, dialogs and loss bindings. Full private facts still bind. Selecting by a repaired
option value resolves to exactly one native option; collisions refuse. End of control drops tab references,
keeps the counter increasing and ignores old-session cleanup events.

Read `git show origin/pkg/28-chrome:reviews/28-chrome-read/PROGRESS.md` after fetching. At fetched head
`e07a88eb`, that file has steps 13b and 13c, but **no separately headed 13d yet**. The follow-up is already in
code: `42163e2c` repairs fresh comparison facts; `978536d7` resolves repaired select values to native values.
The inspected `background.js` lines are `340` (helper), `1050` (dialog), `1080` (typed read), `1157`/`1190`
(two binding comparisons), `1162` (expected target), `1231` (option resolution), and `1422` (confirmation).
These are branch-specific line numbers. No claim is made that its pending browser runs are green.

**Distinct fields:** 28a “3b. Every field in an asking question is distinguishable” owns the frozen-path change
for step 13b's PLAN-GAP; 28b inherits it. Label plus ordinal and frame context must distinguish every field after
repair/shortening. Identity/order remains bound and values remain unread. Main `adapter.py:381` joins the labels
alone, although `reader.js:266` supplies distinct element ids. The new test asserts the **question sentence**, not
just the ids: two same-labelled fields are distinguishable, and swapping/replacing/reordering refuses. Rendering
labels alone must fail it. F4/approval ceilings are not increased to pay for the descriptions.

**Instructions:** measured on this main: 30 tools, instructions **4,093**, descriptions **5,085**, combined
**9,178** characters. 28a item 7/step 0 moves single-tool rules into descriptions and compacts shared Chrome text
before adding anything, pinning 2,800; 28b item 8 verifies that headroom, then pins 3,800. Existing total budgets
and common instructions remain. No server instruction text was added here.

## Questions for the owner

1. **After an update or rollback replaces Chrome's helper, should the tools ask for your password once to keep
   using your chosen Chrome profile?**
   **What you do:** open the helper in that Chrome profile, check its name and choose **Keep using this profile**.
   The system password dialog asks whether Claude should keep using that named profile. You type your password,
   never an ID, and run no administrator command. At first setup, enter the name Chrome shows in its profile
   picker; correct it in the helper if you rename it. Normal Chrome/service restarts need no confirmation.
   **Why it matters:** the tools wait for you after a replacement. No, cancel or timeout leaves the pin as it
   was and this helper's tools refused. Your yes authorizes the new helper; it is not technical proof against
   someone copying a profile's local files.
   **Options:** confirm with your password after each replacement; or make reconnection automatic, which needs
   a separate reviewed design and delays this part of the build.
   **Recommendation:** confirm with your password. It keeps the tested update/rollback behavior and needs no
   permanent signing secret. The same profile pin survives. 28b builds the helper's confirmation flow using
   the password dialog that Chrome's rule changes already use. This changes 18c-b's “without another step”.

2. **If a delayed form send could discard another draft or drawing on the page, should one question let you
   approve both the send and that loss?**
   **Why it matters:** approving a form send alone doesn't tell you that another draft will disappear.
   **Options:** one question naming the send and possible loss; or always stop when other work may be lost,
   leaving you to save the work or send the form yourself.
   **Recommendation:** one combined question. It preserves your delayed submissions (board #138). No reload
   happens first. Refusal sends nothing, and further work while the question waits requires a fresh question.

Neither answer is inferred from this revision or from the earlier READY. `linux-tools` records the choices
before their dependent implementation steps; unrelated image/read work can continue.

## What 18c-b must now do differently

The new handoff names every remaining step. At `91ad33d6`, steps 1a–2b and **3a are built**; 3a stopped after its
two allowed image-build rounds, with the image proof not green. Next is **3a fix**: the PEM scanner assumes
`<scan-root>/root` resolves to a folder, but the image's `root` is a link to `var/roothome`, made at boot. The
lead supplied that layout detail; the branch progress itself proves only that the scan path did not resolve.
Do not repeat the installation, ignore read failures or follow a link outside the image view. **The lead decides
before any further image run or 3b**; the stop/run allowance is not reset. Keep the pending identity dependency
and storage ban until the approved narrow exception lands. **3b** otherwise stays unchanged.
**4/4b** uses a synthetic real pin when 28b is available, without bypassing first-use gates.
**5** extends case 3/C4 to pin continuity, refusal before relink, owner-confirmed acceptance, retired pairs and
another profile; if 28b merges later, its PR owns the combined container proof and `linux-tools` assigns the
VM/release confirmation to the image builder before shipping. C7 adds the named-profile F7 password flow,
including refusal, cancel, timeout and stale/cached confirmation; its integration has the same ownership rule.
**6** separates installation evidence
from pin evidence and adds the chosen owner step to the guide/release handoff. No permanent signing key,
profile-file installation or automatic enrollment is added to the image.

## Revision 2

2026-11-18, after `RECHECK-CROSS-5.md`, starting at `d175acdd` on the same branch/draft PR #106.
The blocker and should-fix are accepted. Findings 2–6 remain closed as specifications; owner question 2 above
is unchanged, and neither owner answer is inferred. This revision adds no product code.
Contract commit: `83a1f64b`; this report and the ALIGNMENT decisions follow in a separate documentation commit.

### Changed sections and decisions

- **28b “1. What Claude sees” — Restore contract; “Tests” — Restore pin regression and profile mutation table;
  “Build order”, “Paths”, “What must not change”.** Committed `store.chrome_state` alone authorizes the pin;
  the disposable database never does. Define the locked hello, connection retirement before reopening and
  missing-state refusal. Step 2 owns the narrow daemon/engine hooks, reusing the store without changing its
  semantics. The P → backup → switch Q → restore-P-backup regression tries both before/after confirmation;
  it must independently catch disposable lookup and omitted recovery closure/revalidation. It also checks
  Q's mandatory fresh handshake, so the latter mutation cannot survive just because P was correctly refused.
- **28b “JUDGMENT-CALLs”, item 1 — lifecycle / Profile name and what must be built; “Tests”, “Build order” and
  “Paths”; 18c-b “CROSS-5 identity handoff”; CONTROL §6 “How the tool reaches Chrome” / “Which tabs Claude works
  in”; this report “Questions for the owner”.** Replace typed-ID administrator relinking with helper buttons
  and the existing F7 password dialog. The candidate's exact pair is supplied internally. A no, cancel or
  timeout leaves the old pin unchanged and that candidate refused; stale/cached success cannot authorize it.
  The displayed Chrome name is an owner-supplied label, not identity evidence. 28b step 2 builds the missing
  candidate channel/UI and binding; 18c-b already installs the action and owns the real-session probe/C7 proof.
- **18c-b “CROSS-5 identity handoff”, “Steps”, “Stop and report”; this report “What 18c-b must now do differently”.**
  Correct the next step to **3a fix**, record head `91ad33d6`, the root-home symlink/boot-created-target defect
  and the two-round stop. The lead decides before another image run or 3b. Later step order stays unchanged.
- **28a opening dependency note; ALIGNMENT “After BRIEF-CROSS-5”.** Assign the new profile work to 28b step 2
  and add the one-line decisions. 28a's mutation table is unchanged; 28b's new table and 18c-b's mutation list
  name the matching regressions. All earlier mutation requirements remain. Repaired Unicode, reference
  cleanup, distinguishable descriptions, the 2,800/3,800 instruction caps and build order are unchanged.

### Restore contract in five lines

1. The pin, accepted pair and enrollment status come only from committed `store.chrome_state`, never ordinary `get()` or SQLite.
2. Under the restore lock the current committed pair gets a quarantined `restore_required` hello; other pairs refuse, and no browser command or pairing runs.
3. Before confirmation reopens the app gate, close every admitted connection and pending candidate/dialog, drop queued messages and invalidate refs, lists and approvals.
4. After confirmation a fresh handshake checks committed evidence in the new generation; restored P never serves requests authorized for Q.
5. Missing, unreadable or corrupt restored evidence stays refused and never becomes first-connect enrollment.

### Dialog feasibility and evidence checked

**Read:** `control/aresos_control/chrome/confirm.py:52` builds the action call for PID/start-time/UID with
`change` text; `:75` refuses timeout/cached authorization. The installed action's message interpolates that
text, with uncached `auth_admin` and the service-owner annotation
(`control/chrome/packaging/org.aresos.control.chrome-loosen.policy:23`).
`control/aresos_control/chrome/adapter.py:142` starts F7 only on the admitted bridge; `:173` cancels on connection
change and checks the password result before writing. These pieces support the proposed dialog, but **do not
yet implement profile confirmation**. 28b step 2 must give pending candidates only its restricted pairing
channel and bind the answer to candidate, peer, displayed name, committed pin revision and restore generation.
18c-b's “The polkit probe comes first in step 4” and C7 still decide whether its real session can show the dialog;
the existing stop on failure stands. No action-default or service-sandbox change is authorized.

**Name gap, handled explicitly:** `control/aresos_control/chrome/bridge.py:49`'s hello contains session/version,
not a Chrome profile name, and `control/chrome/native_host.py:14` only relays. The documented
[`getProfileUserInfo`](https://developer.chrome.com/docs/extensions/reference/api/identity#method-getProfileUserInfo)
returns account information, not the picker name. This revision adds no account permission or profile-file
reader. At setup he enters Chrome's picker name in the helper; the service retains it privately and the helper
asks him to check/correct it before the password prompt. This modest setup/rename step is stated in question 1;
there is no claim of automatic name discovery or technical proof against a copied profile.

**Read:** `control/aresos_control/daemon.py:238` admits native peers separately from
`control/aresos_control/engine.py:575`'s restore gate. The confirm branch at `engine.py:577` calls the store
directly, with no connection retirement. `control/aresos_control/storage.py:820` reads disposable SQLite;
`control/aresos_control/chrome/committed.py:154` reads committed evidence; `storage.py:506` reconstructs Chrome
rows and `:942` releases the restore lock. These support the recheck's blocker; the future pin must connect the
two lifecycles. The recheck correctly describes a specification gap, not a demonstrated bypass in built 28b.

**Read:** `git show origin/pkg/18c-b-chrome:reviews/18c-b-chrome-image/PROGRESS.md`, branch head `91ad33d6`,
records the stop at lines 6–12 and the unresolved scan at lines 173–177. Its checker
`os/ci/control/chrome_image.py:237` traverses the root-home entry as a directory. The symlink target/boot timing
comes from the lead's instruction in this revision; no local image was inspected. No disagreement with the
recheck's findings or its two owner-question assessments. The new dialog replaces the command it accurately
described; it is not claimed to exist already.

### Verification of Revision 2

- **Run:** `git fetch origin` first: exit 0, no output. Starting branch `briefs/28ab-cross-5`, clean at `d175acdd`.
- **Run:** `PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/.work/cross5-revision2/tmp" PYTHONPATH=control:control/chrome_tests python3 -B -m unittest test_owner_confirm test_bridge test_restore_lock`:
  `Ran 34 tests in 16.739s`, `OK`. These test existing F7/bridge/restore behavior, not the future pin/dialog.
- **Run:** `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control python3 -B .work/recheck-28ab/restore_pin_probe.py`:
  `PASS: restore lock; ordinary read returns retired pair; committed read returns current pair`, then
  `PASS: restore confirmation restores current pair; handshake must not cache the retired pair`.
- **Run:** `git diff --check`: exit 0, no output.
- **Run:** `PYTHONDONTWRITEBYTECODE=1 python3 -B .work/cross5-revision2/check_docs.py`: exit 0, printed:

  ```text
  PASS: exactly six requested Markdown files; no product or untracked changes
  PASS: CONTROL changes confined to section 6
  PASS: 28a changes only its dependency note; descriptions, budget and mutation table unchanged
  PASS: 28b findings 2-6, Unicode/cleanup, instruction cap, later steps and existing mutation cases unchanged
  PASS: both restore mutations mapped independently to the P/Q regression and Q reconnect assertion
  PASS: owner question 2 unchanged word for word; ALIGNMENT history retained
  PASS: 18c-b handoff is 3a fix and preserves the lead gate and exhausted allowance
  PASS: no personal home paths or accidental replacement characters; .work files over 500 MB: none
  ```

- **Large artifacts left:** no file over 500 MB in `.work/`; no download or extracted image created.
- **Not run:** future pin tests/mutations, browser/VM/image tests, workflows or mod builds. The two new restore
  mutations are requirements checked for test coverage in the text, not executed implementation evidence.
- **JUDGMENT-CALL:** close every admitted connection on restore confirmation, rather than keep one after an
  in-place revalidation; this requires a reconnect but gives recovery a single clear boundary. Changing later
  needs equivalent peer/generation checks and tests. The profile dialog remains conditional on owner question 1;
  its display-name entry/check is explicit because the existing handshake has no name source.
- **PLAN-GAP:** the old pin text did not select the committed view or define recovery connection handling;
  the old handoff omitted completed 3a and its stop. Both are amended above. No other finding is reopened.
- **Open questions:** owner questions 1 and 2; the lead's disposition of 3a fix. No owner choice or additional
  image-run permission follows from this documentation revision.

## Disagreements and limits of this revision

No disagreement with any CROSS-5 finding. The earlier review 6 acceptance of held-resumption loss is superseded
because that operation is now controlled. The remaining unheld script-effect policy is not widened or reopened.

The identity recommendation deliberately requires human authorization of continuity; it does **not** claim an
automatic technical proof across a destroyed extension store. If the owner chooses automatic continuity, that
option needs a new concrete design and tests before implementation; simply accepting replacement ids or keeping
a signing key without proving rollback is not an alternative implementation of this brief.

## Verified / not verified

- **Run:** `git fetch origin` first, exit 0 with no output; starting branch `briefs/28ab-cross-5`, clean, main
  `918fba67`. Read the requested briefs, cross-review, alignment (including review 6's recheck), design and review
  bar; compared their claims with main code and the two in-flight branch records above.
- **Run:** `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control python3` importing `instructions_for` and `tools_for`:
  printed `Chrome instructions: 4093`, `Descriptions: 5085`, `Descriptions plus instructions: 9178`, `Tools: 30`.
- **Run:** `git diff --check`: exit 0, no output.
- **Run:** `PYTHONDONTWRITEBYTECODE=1 python3 .work/cross5/check_docs.py`: exit 0, printed:

  ```text
  PASS: exactly six requested Markdown files; no product changes
  PASS: CONTROL changes confined to section 6
  PASS: existing server instruction block unchanged
  PASS: ALIGNMENT adds one section; prior decision history retained
  PASS: no accidental replacement characters or personal home paths
  PASS: .work files over 500 MB: none
  ```

  The scratch check compares the diff's paths with the six requested files, CONTROL outside section 6 and the
  existing instruction quote with `918fba67`, verifies the append-only alignment and scans the worktree's `.work/`.
- **Large artifacts left:** none over 500 MB in `.work/`; no downloads or extracted images made.
- **Not run:** product unit suites, reviewer mutations, browser/VM tests, mod builds or workflows. These edits
  specify future tests; they cannot establish implementation correctness. No product source or generated file
  changes. No owner browser/profile, desktop input, system installation, mount or boot command used.
- **Open questions:** the two owner choices above; final implementation proofs belong to the package builders.

## Owner answers

- **Question 2** (board #353, 2026-11-18): "One question (recommended)".
- **Question 1:** asked after the recheck of revision 2.
