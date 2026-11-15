# 20 adapters — final report

**Not green; draft only.** All **12 functional adapter matrices pass in both Linux install
modes** on source `fe7dd2fb`. Three strict question-wording assertions fail in both modes
and need the core build's shared sentence builder. The shared qualification inventory also
needs the new case names. Do not merge or ship on this evidence.

Draft [PR #29](https://github.com/Ares-Empire/AresOS/pull/29) targets `pkg/20-chrome`.
The requirement map is [ADAPTERS.md](ADAPTERS.md), committed before code as `cf8f5d41`.

## Done

**Read:** fetched main and read the requested briefs/specifications with `git show`,
main `e8657edc3bb55b6939f3bab434bf2d12a6800fb0`: AGENTS, brief 20, brief 19b,
CONTROL §§3/4/6/7, FEATURES, PLAN and re-checks 29–34. Read the local four briefs in the
specified order first, then the existing code and REPORT. No other branch was merged.

**Read — sites.py:** complete/scoped recognition, exact host matching (including an
explicit empty override), versioned semantics and generic fallback. The reader reports an
implicit `<main>` as `generic`; recognition accepts it only with a nonempty known
scope. Typing cannot inherit a playback exemption; a Deezer submit button cannot become
free because it says Play.

**Read — Gmail:** complete account/To/Cc/Bcc/subject/text/attachment reading; Send,
Ctrl/Cmd+Enter and deletion shortcuts, including inbox #; quote-aware recipient sets with
To/Cc/Bcc roles kept separate. Ambiguous/group/semicolon notation is ineligible for trust.
The full raw compose remains bound. Kind version 2 suspends old Gmail allowances.

**Read — WhatsApp/Gemini:** full per-message WhatsApp chat/text/files, free opening/typing
and no trusted messages. Gemini questions are eligible by exact account/site; chat
deletion/sharing never becomes trusted. Clear alternate sharing labels stay guarded.

**Read — GitHub/Deezer/bank:** comments/reviews/merges/closing/deleting/settings, exact
known confirmation plans, and guarded alternate merge/close/review/settings labels.
Deezer playback/library additions stay free; removal/posting/sharing/payment labels ask,
including Unlike/Unfollow variants. Bank restriction remains the existing independent
owner-only read-only rule; the shipped bank host list stays empty. No new trusted kind,
global action, definition field or global word-list entry was added.

**Read — fixtures/tests:** new files under `control/chrome/ci/sites/`,
`control/chrome_tests/test_sites.py` and `sites.test.mjs`. Browser tests use public
tools and the existing independent HTTP receiver. They save actual arrivals (body, host,
method/time) in `adapters-receiver.jsonl`, beside the independent `receiver.jsonl`.
They check 0 before approval, 1 after, 1 after repeat; changed original/repeated approvals
leave 0 and only fresh work may reach 1. Unlisted confirmations require a separate explicit
free dialog input; listed confirmations require a new approval.

**Run/read:** all work stayed in this worktree/branch. No local Chrome, Chromium or browser
profile was started, read or touched. No browser-control tool, real site/account, system
installation, Gradle or Java daemon was used. Local tests were plain Python/Node. Every
browser test ran through control-chrome in GitHub's Linux containers.

## Verified

**Run — final source fe7dd2fb:**
[42699095582](https://github.com/Ares-Empire/AresOS/actions/runs/42699095582),
Google Chrome **157.0.8103.38**, policy and external installations.

Each mode passed all 12 functional matrices and all **42** named-confirmation mismatch
variants. An additional check over the independent raw receiver records verified, per mode:

- **135** complete 0/1/1 approval sequences, including **15** alternate-label cases;
- every before/refusal snapshot was zero and matched the independent raw records;
- **20** unlisted-dialog cases stayed at zero after the original approval, then reached
  one only after a separate explicit free dialog input, still one after repeat;
- **173** adapter arrivals in total, including the intentionally free activity;
- all three failing wording cases had **zero** arrivals.

Artifacts: `control-chrome-42699095582-1-policy` and
`control-chrome-42699095582-1-external`; files `adapters.json`,
`adapters-receiver.jsonl`, `receiver.jsonl`, `browser.txt`, `python.txt`,
`node.txt`, `chrome-version.txt`. Exact lines in both browser logs:

```text
ADAPTER RECEIVER adapters-gmail-11:Delete shortcut:main 0 before, 1 after, 1 after repeat
ADAPTER RECEIVER adapters-github-59:Squash and merge:main 0 before, 1 after, 1 after repeat
ADAPTER RECEIVER adapters-deezer-69:Share album:main 0 before, 1 after, 1 after repeat
ADAPTER RECEIVER adapters-deezer-72:Unlike track:main 0 before, 1 after, 1 after repeat
```

**Run — final container support suites:** Python `Ran 115 tests in 518.835s`, `OK`
(policy), and `Ran 115 tests in 581.382s`, `OK` (external). Node `tests 81`,
`pass 81`, `fail 0`, 6218.650495ms / 6271.849466ms. Commands are the workflow's
`python3 -m unittest discover -s control/chrome_tests -v` and
`node --test control/chrome_tests/*.test.mjs`.

**Run — local:** complete Python suites passed 110 tests in 219.063s, then 113 in 214.538s
before the final additions. Latest focused command:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_sites test_engine test_policy -v`:
55 tests, OK. Complete local Node suite: 81/81 in 6005.459958ms; latest fixture/actual-handler
VM tests also passed after the additions. Generated scripts compile without executing a
browser. `python3 control/generate.py --check` prints
`Generated artifacts match definitions`; `git diff --check` passes.
The mock-engine binding test models the extension's documented check; it is not presented
as independent browser proof.

**Run — runtime identity:** `python3 control/chrome/build.py` computed
`22244f7e61b8a51e36980ccf8f129cd5e6d62c8694b2e570816fc188301e1166`
locally. This is not claimed as a literal hash printed by the runner. Review-only changes
do not alter its runtime inputs.

## Named fixture results

**Run:** all rows below executed in both modes of 42699095582.

| Exact test name | Policy | External |
|---|---|---|
| GROUP 10 ADAPTER Gmail full compose and every bound field | PASS | PASS |
| GROUP 10 ADAPTER two Gmail compose windows and inbox shortcut | PASS | PASS |
| GROUP 11 ADAPTER Gmail exact To Cc Bcc roles account revocation and widening | PASS | PASS |
| GROUP 10 ADAPTER WhatsApp every message chat text attachments and free activity | PASS | PASS |
| GROUP 10 ADAPTER GitHub actions and all named confirmations | PASS | PASS |
| GROUP 10 ADAPTER clear merge settings and sharing variants stay guarded | PASS | PASS |
| GROUP 4 ADAPTER every named GitHub confirmation mismatch | PASS | PASS |
| GROUP 10 ADAPTER Gemini question content and always asking chat changes | PASS | PASS |
| GROUP 11 ADAPTER Gemini exact account owner entry and revocation | PASS | PASS |
| GROUP 10 ADAPTER Deezer playback additions removals posts shares and payments | PASS | PASS |
| GROUP 10 ADAPTER bank owner restriction all inputs and positive reads links scroll | PASS | PASS |
| GROUP 10 ADAPTER unfamiliar pages and qualification fallback on all sites | PASS | PASS |
| GROUP 10 ADAPTER Gemini question uses its required semantic name | FAIL | FAIL |
| GROUP 10 ADAPTER Gmail question names its attachments | FAIL | FAIL |
| GROUP 10 ADAPTER Gmail deletion shortcut question names the deletion | FAIL | FAIL |

## Shared-file integration required / PLAN-GAP

**Read/run — not edited here, per file ownership:**

1. `control/aresos_control/chrome/adapter.py`, `Chrome.prepare/question`: carry the
   recognized semantic action into sentence generation. Gemini must say **“Gemini: ask a
   question”**; Gmail inbox # must say **delete**, rather than “activate Selected message”.
   The semantic kind is private in the payload today; the sentence sees only raw reader
   targets. Two strict FAIL rows above prove this.
2. Same builder: name Gmail's attachment count/names/sizes with the account, To/Cc/hidden
   Bcc, subject and text length. The content/binding already includes attachments, but the
   sentence lacks an attachment count; a filename appearing incidentally in dialog text
   is insufficient. The third strict FAIL row proves this.
3. `control/chrome/ci/verdicts.mjs`: register all new group 4/10/11 case names from
   `sites/matrices.mjs` in REQUIRED and its exact support inventory. Unknown names
   conservatively make support false. The side build did not change that shared manifest.

Actual failing question fragments: `activate 'Send' ('Send') as 'Synthetic account' with
23 characters` for Gemini; `activate 'Selected message' ('Selected message') for
'Selected synthetic message'` for Gmail #. The mail sentence mentions
`fixture.txt 3 bytes` only inside its dialog description and never says one attachment.

**Read — harness hooks:** exactly one registration line in each of `ci/fixture.mjs`
(load new pages), `ci/matrices.mjs` (run new cases), `ci/service.py` (install test-only
failed-adapter qualification input). All substantive harness additions live in new owned
files. No extension/shared runtime other than sites.py, definition, generated artifact,
setting, base, protected document, image or mod file changed. No owner-input, reload or
Claude-tabs-only injection stand-in was built.

The strict adapter suite writes every result and throws on a failure; later core matrices
therefore are not reached. No full-core or twice-green acceptance/qualification is claimed.
Core's owner-input PLAN-GAP, tab-opening failure and integration work remain with the
parallel core build.

## Earlier failures and corrections

**Run/read:** these remain failures, not evidence of green.

- 42687470130 / 652c0a80: canceled superseded run, no browser acceptance.
- 42688294269 / 270e1fe2: completed policy job exposed the scope gate's actual-reader
  mismatch. The receiver recorded an unapproved inbox # POST and an Unlike POST. Fixed
  in f00ad0db, with the actual implicit-main regression; the strict 0/1/1 checks now pass
  in both final modes. External job canceled when superseded.
- 42690905440 / 13c7127d: policy 10/13 passed, including 94 complete receiver sequences.
  Two shared wording failures remained; one test incorrectly expected an unlisted Merge
  dialog to ask. Corrected to CONTROL §6's separate free-input rule while retaining zero
  before that input and no repeat. External job canceled when superseded.
- 42693628190 / 11c85cc3: both modes passed all 11 then-existing functional cases, 120
  approval sequences and 20 free-dialog cases each; same three wording failures. Final
  fe7dd2fb adds/restores 15 clear variants that the exact-name table had narrowed.
- Test development also corrected an Engine helper call, a permissive mock browser used
  to assert a browser check, and an API failed-operation response mistaken for a transport
  error. The display now asserts the specified escaped newline while the independent
  receiver asserts the original raw newline. No required arrival/count assertion was
  weakened or waived.

## Not verified

**Read/assumed:** live signed-in selector/layout compatibility and the fixed GitHub native
confirmation templates remain unverified on real sites/accounts, as brief 20 explicitly
defers until the owner's post-boot check. No synthetic pass is claimed as live-site proof.

**Run/read:** the browser button-mismatch variant is a new page dialog, so it also changes
kind. Native dialogs always report OK in this implementation; the button-only comparison
and private opener-document mismatch are proved separately by a plain Node VM test of the
actual extension handler, not misrepresented as isolated browser receiver experiments.

## JUDGMENT-CALL

**Read:** exact displayed recipient spellings remain distinct, with To/Cc/Bcc roles kept
separate; no guessed mailbox normalization. Ambiguous notation cannot be trusted. The
alternative simple comma split conflates quoted names/sets. Gmail kind version 2 suspends
old allowances; changing this later costs a new kind definition/hash and recipient tests.

**Read/assumed:** known confirmations use fixed adapter data for the modeled action/context,
never dialog text learned after approval. Alternate labels without a known plan get no
automatic acceptance; later dialogs classify independently. Live templates need the
deferred owner check.

## Run count and closing state

**Run:** five source-batch control-chrome workflows ran on this branch; the report-only
push starts the sixth (same runtime/test files, not used as new evidence). Budget about
25; no superseded run was left running. No main/core/data-branch push, merge, force push,
privacy-hook bypass, real issue or unrequested message occurred.

**Run:** closing `.work` inventory: **253569158 bytes**, no file over **500 MB**.
Only local test products/logs and downloaded CI artifacts remain; no ISO, image layer,
extracted image or partial large download. No Gradle/Java daemon was started.

**Open questions:** no new owner decision is requested. The package lead must integrate
the two shared files above and rerun the combined core/qualification suites; usual-site
checks remain deferred as designed.
