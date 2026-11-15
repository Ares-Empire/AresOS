**Two FIX findings remain at `65aca3e6`: A-3 and B-6 are only PARTLY fixed.** The owner-Enter case also cannot close against your exact requirement: the new browser cases exercise synchronous submissions while his mark is set, but not a timer firing while that mark remains set.

I read the requested briefs, reports, reviews, specification from `origin/main`, and `60b94384..65aca3e6`. The installed code, tests and workflows match the recorded acceptance source `0ae4ac41`. I made no edits and started no browser or container.

**FIX — B-6, PARTLY: a confirmation inside a form still omits the outside draft.**

Locations: [adapter.py:40](../../control/aresos_control/chrome/adapter.py:40), [background.js:653](../../control/chrome/extension/background.js:653).

Both binding implementations add the complete editable-field set only when `!frame.form`. Consequently, placing the confirmation’s OK button inside its own form disables the fix—even though the message being confirmed remains outside that form.

Concrete reproduction:

```html
<textarea id="draft">Approved text</textarea>
<dialog open>
  <form method="dialog">
    <p>Send this message?</p>
    <button type="button" id="ok">OK</button>
  </form>
</dialog>
```

Have OK send `draft.value`. Prepare OK, change the textarea to `Different text`, then approve.

I ran production Python classification/binding and production JavaScript dispatch with browser-free fixtures:

```text
Without confirmation form:
  kind=confirmation
  outside draft bound
  stale_approval; arrivals=[]

With confirmation form:
  kind=confirmation
  editable=null
  dispatched=true; arrivals=["Different text"]
```

The arrival above is the fixture’s simulated receiver, not a newly run browser request. It establishes that the production dispatch comparison accepts the changed draft.

This is a send with content omitted from the question and binding, not a harmless page disguise.

**Fix:** bind the complete generic draft set for send confirmations independently of whether the confirmation button belongs to a form. Preserve send-confirmation semantics for submit buttons too. Add this form-containing variant to the existing changed-draft Linux test, requiring zero arrivals on the stale approval.

**FIX — A-3, PARTLY: native-created shadow roots still escape the activation fallback.**

Locations: [page.js:86](../../control/chrome/extension/page.js:86), [guard.js:138](../../control/chrome/extension/guard.js:138).

The fix registers capture synchronously through the installed `attachShadow` wrapper. A root created through a borrowed native `attachShadow` never takes that path. Window capture still skips shadow-root events, assuming root capture already exists.

Concrete reproduction: use the existing `shadow-fallback` fixture’s ordinary same-origin opener, changing root creation to:

```js
const root = opener.Element.prototype.attachShadow.call(host, {
  mode: "closed"
});
root.append(deleteLink);

opener.EventTarget.prototype.dispatchEvent.call(
  deleteLink,
  new MouseEvent("click", {
    bubbles: true,
    composed: true,
    cancelable: true
  })
);
```

Give the clearly labelled Delete link a handler that sends the deletion request. Execute this inside Claude’s Continue handler.

My production guard/page probe used the shadow-aware, retargeting fixture:

| Root creation | Event composed | Delete handler executions | Held steps |
|---|---:|---:|---:|
| Wrapped | false | 0 | 1 |
| Wrapped | true | 0 | 1 |
| Saved native | false | 1 | 0 |
| Saved native | true | 1 | 0 |

These are browser-free handler counters. The existing Linux fixture borrows event dispatch, but still creates its root through the wrapped `attachShadow`.

This leaves a concrete unasked deletion path within the earlier finding’s fallback behavior.

**Fix:** stop assuming every encountered shadow root already has capture installed. Handle composed events on previously unregistered roots, and establish coverage for native-created roots before non-composed activation can run. Add both variants to Linux CI; neither handler execution nor a missing uncertainty report should pass.

**Earlier-finding disposition**

The classifications below describe the issue being re-checked. `FIXED` closes that issue; it does not request another change. Low-impact diagnostic, compatibility and test-evidence issues are classified `KNOWN LIMIT`, rather than elevated into unproved harmful vulnerabilities.

For page fixes, **P-number evidence** refers to the retained [removal-mutation results](./records/integrate3/page-mutations-popup.json): each named mutation records a passing baseline and a failing test after removal. Browser lines refer to run **42989465778, attempt 1, external**, indexed in the [closing evidence](./records/integrate3/closing/INDEX.md). The other three acceptance artifacts contain the same named cases.

| Earlier finding | Status / classification | Reproduction, correction and evidence |
|---|---|---|
| A-1: foreign controlled-document wrapper bypass | **FIXED — FIX** | Borrow the parent wrapper to submit another controlled document’s form. [guard.js:156](../../control/chrome/extension/guard.js:156) routes through its guard. P4 removal fails; browser line 44 passes controlled-tab and ordinary-document cases. |
| A-2: inline/new/replaced frames escape holds | **FIXED — FIX** | Create a frame during input, or submit from blank/srcdoc. [background.js:170](../../control/chrome/extension/background.js:170) inherits the hold without allowance; final coverage is checked at line 865. P2/P3 mutations fail; browser lines 37 and 43 pass. |
| A-3: new-shadow fallback | **PARTLY — FIX** | Wrapped root creation is fixed; native root creation remains exploitable as detailed above. |
| A-4: refusal leaves permanent in-flight state | **FIXED — FIX** | Change binding after arming. [background.js:907](../../control/chrome/extension/background.js:907) finishes armed frames in `finally`. P28 removal fails; the cleanup regression passed locally. |
| B-1: equivalent key spellings | **FIXED — FIX** | `Shift+Delete`, modified Backspace and `Shift+#` now classify the dispatched tuple. [policy.py:74](../../control/aresos_control/chrome/policy.py:74). P6/P6-adapter removals fail; Python tests and browser line 68 pass. |
| B-2: malformed URL decoding disagreement | **FIXED — FIX** | `%73end?bad=%ZZ`, invalid UTF-8 and incomplete sequences retain asking semantics. [guard.js:67](../../control/chrome/extension/guard.js:67). P7 removal fails; local guard/policy tests and browser line 68 pass. |
| B-3: decomposed German words | **FIXED — FIX** | Decomposed “löschen” and “veröffentlichen” normalize before matching. [policy.py:37](../../control/aresos_control/chrome/policy.py:37). P8/P8-guard removals fail; local tests and browser line 68 pass. |
| B-4: native-dialog continuation unheld | **FIXED — FIX** | Ordinary answers establish the private return hold at [background.js:417](../../control/chrome/extension/background.js:417). Browser lines 33–36 cover ordinary/inline dialogs and the decided handoff/borrowed-native rules. P1 removal tests fail. |
| B-5, C-5: inline drafts omitted | **FIXED — FIX** | Change a blank/srcdoc editor after preparation. [background.js:620](../../control/chrome/extension/background.js:620) reads authenticated inherited documents; incomplete eligible coverage refuses. P2 removals fail; browser line 37 passes. |
| B-6: confirmation omits outside draft | **PARTLY — FIX** | Fixed without a form; still broken with a confirmation form, as demonstrated above. |
| B-7: same-metadata file replacement | **FIXED — FIX** | Replace selected bytes while preserving metadata. [reader.js:128](../../control/chrome/extension/reader.js:128) freshly hashes bytes and checks selection stability. P12 hash/rehash/race/binding removals fail; browser line 38 passes. |
| B-8: rich-text distinctions collapse | **FIXED — FIX** | Replace two paragraphs with one line. [reader.js:97](../../control/chrome/extension/reader.js:97) preserves breaks and binds safe structure. P13 removal fails; reader tests and browser line 80 pass. |
| B-9: ARIA affected items omitted | **FIXED — FIX** | Rename an ARIA listitem/row/article while retaining Delete. [reader.js:216](../../control/chrome/extension/reader.js:216) includes those containers and named sections. P10 removal fails; browser line 80 passes. |
| B-10: unsubscribe binds unrelated draft | **FIXED — FIX** | Change the subscription item after preparation. [policy.py:106](../../control/aresos_control/chrome/policy.py:106) assigns item semantics. P14 removal fails; both language variants pass browser line 80. |
| B-11: ordinary GET-search Enter asks | **FIXED — KNOWN LIMIT** | GET-search exemption now precedes compose Enter at [policy.py:139](../../control/aresos_control/chrome/policy.py:139). P21 removal fails; Python test passed. Limit: word-based classification can still produce harmless extra questions. |
| B-12: vague deletion question/title absent | **FIXED — FIX** | Delete on “Quarterly report” now names deletion/key and binds the title. [adapter.py:283](../../control/aresos_control/chrome/adapter.py:283). P22 action/title removals fail; changed-title browser case passes line 80. |
| B-13: stock page outcome | **FIXED — KNOWN LIMIT** | An input that shows an error now records the actual bounded observation. [background.js:677](../../control/chrome/extension/background.js:677). P23 removal fails; local test and browser line 89 pass. Limit: page observations do not prove network delivery. |
| C-1: raw srcdoc password collection | **FIXED — FIX** | Password-containing srcdoc getter is no longer read; only attribute presence is tested. [reader.js:228](../../control/chrome/extension/reader.js:228). P16 removal fails; throwing-getter regression passed locally. |
| C-2: release/retake resets protection | **FIXED — FIX** | Show password, release, retake, read. [reader.js:7](../../control/chrome/extension/reader.js:7) retains document privacy state; lost identity refuses before collection. P17 removals fail; reinjection tests passed locally. |
| C-3: protected descendants/former editors leak | **FIXED — FIX** | Read a protected editor’s span, or remove its editable state. [reader.js:38](../../control/chrome/extension/reader.js:38) checks sticky membership first and protected ancestors. P18 removals fail; throwing-getter tests passed locally. |
| C-4: Runtime console/exception ingress | **FIXED — FIX** | Log/throw a password before and after control. [background.js:46](../../control/chrome/extension/background.js:46) no longer enables Runtime reporting. P19 removal fails; all four closing ingress audits record zero forbidden Runtime value events. |
| C-6, D-12: unmarked page text | **FIXED — KNOWN LIMIT** | Inject sentinel text into dialogs, followups, stages and old audit summaries. [engine.py:261](../../control/aresos_control/engine.py:261) and adapter result paths preserve untrusted marking. S12 mutations fail, retained Python lines 196, 238–239. Limit: marked page text remains untrusted data. |
| C-7: incomplete password evidence | **FIXED — FIX** | The expanded forms/root/transition matrix exercises read, form read, preparation and final binding. [password-fixtures.mjs:1](../../control/chrome/ci/password-fixtures.mjs:1). P30 getter/scanner removals fail; closing audits record 3,481–3,483 getter observations per artifact and no sentinel. |
| C-8: title hides visible Delete | **FIXED — FIX** | `<button title="More information">Delete</button>` now retains content before title fallback. [reader.js:89](../../control/chrome/extension/reader.js:89). P15 removal fails; local reader test and browser line 68 pass. |

State evidence below comes from the retained [final-source Python log](./records/integrate3/local-python-popup-frozen.txt). I inspected the regression implementations and removal results; I did not rerun these disk-writing suites.

| Earlier finding | Status / classification | Reproduction, correction and evidence |
|---|---|---|
| D-1: restore resurrects revoked policy | **FIXED — FIX** | Restore older SQLite after revocation/read-only/failure. [storage.py:445](../../control/aresos_control/storage.py:445) reconciles committed state before unlock. Tests lines 197–199; S1 removals fail at 216–218. |
| D-2: readable SQLite overrides committed status | **FIXED — KNOWN LIMIT** | Roll back SQLite or fail the completion marker. [engine.py:58](../../control/aresos_control/engine.py:58) uses committed Chrome authority. Tests 200–201; removals 219–220. The misleading-status case is closed. |
| D-3: acknowledged cancellation resurrected | **FIXED — KNOWN LIMIT** | Restore before acknowledgement. [committed.py:145](../../control/aresos_control/chrome/committed.py:145) preserves operation acknowledgements and terminal outcomes. Test 202; removal 221. The false-warning case is closed. |
| D-4: finished checks exhaust shared quota | **FIXED — FIX** | Process over 512 completed checks. [retention.py:69](../../control/aresos_control/retention.py:69) retires resolved checks while retaining receipts. Tests 203–205; removals 222–224. |
| D-5: normal submission creates interruption warning | **FIXED — KNOWN LIMIT** | Complete a normal held submission. [recovery.py:59](../../control/aresos_control/recovery.py:59) distinguishes live checks from interruptions. Test 206; removals 225–226. The spurious warning is closed. |
| D-6: lost queue leaves permanent checks | **FIXED — KNOWN LIMIT** | Restart Chrome with an empty queue. [adapter.py:542](../../control/aresos_control/chrome/adapter.py:542) commits stale, non-resumable results independently of page reads. Tests 207–210; removals 227–230. The unresolved-check case is closed. |
| D-7: drop blocked by ordinary admission | **FIXED — FIX** | Drop at history and physical-space boundaries. [storage.py:545](../../control/aresos_control/storage.py:545) and engine admission recognize cancellation. Test 211; removal 231. |
| D-8: index bound blocks archive recovery | **FIXED — KNOWN LIMIT** | Exceed the index bound, then call public archive. [engine.py:96](../../control/aresos_control/engine.py:96) returns bounded unavailable disclosure while allowing recovery. Tests 212–213; removals 232–233. The recovery dead end is closed. |
| D-9: Mail continuation lost | **FIXED — KNOWN LIMIT** | Fail live reads with Mail-only/mixed cached warnings. [engine.py:135](../../control/aresos_control/engine.py:135) preserves counts/routes. Tests 214–215; removal 234. The lost-continuation case is closed. |
| D-10: timestamp-unit ordering | **FIXED — KNOWN LIMIT** | Mix old Mail warnings with new Chrome warnings. [adapter.py:157](../../control/aresos_control/chrome/adapter.py:157) normalizes nanoseconds. Test 195; removal 235. The ordering defect is closed. |
| D-11: incomplete fault/oracle coverage | **FIXED — KNOWN LIMIT** | Compare public views during persistent faults, after space returns and after process cuts. [test_state_crashes.py](../../control/chrome_tests/test_state_crashes.py:1) and scenario/receiver oracle add those checks. Retained lines 191–194, 236–245. Limit: these remain synthetic fault scenarios. |

| Earlier finding | Status / classification | Reproduction, correction and evidence |
|---|---|---|
| E-1: typing during final identity query lost | **FIXED — FIX** | Type during the last identity query. [background.js:528](../../control/chrome/extension/background.js:528) performs the final dirty check afterwards. P24-last-check removal fails; local regression passed. |
| E-2: detached/Web Audio interrupted | **FIXED — FIX** | Start detached or Web Audio before first act. [background.js:532](../../control/chrome/extension/background.js:532) includes native tab audibility. P24-audible removal fails; browser line 85 passes. |
| E-3: no-op/isolated action steals selection | **FIXED — FIX** | Check an already-checked box in an inactive tab. [background.js:858](../../control/chrome/extension/background.js:858) activates only when native input needs it. P25 removals fail; browser line 87 passes. |
| E-4: native wrapper fingerprint | **FIXED — KNOWN LIMIT** | Inspect own properties/constructibility. [page.js:83](../../control/chrome/extension/page.js:83) uses nonconstructible wrappers. P26 removal fails. Limit: a pristine-realm stringifier can still detect controlled-tab wrappers. |
| E-5: Stop retains navigation blocks | **FIXED — FIX** | Freeze a wrapper and Stop. [background.js:310](../../control/chrome/extension/background.js:310) excludes releasing tabs from blocking rules. P27 removal fails; browser line 88 passes. |
| CL-F1: exact owner form/submitter unpinned | **PARTLY — KNOWN LIMIT** | Independent removal probes now fail, but the requested browser timer/mark overlap is absent. [review-fixtures.mjs:32](../../control/chrome/ci/review-fixtures.mjs:32). This is an evidence gap, not another demonstrated unauthorized send. |
| CL-F2: outside compatibility cannot detect wrappers | **FIXED — KNOWN LIMIT** | Compare pristine-realm strings inside/outside control. [compatibility.mjs:74](../../control/chrome/ci/compatibility.mjs:74) requires a difference inside and equality outside. Browser line 101 passes. Limit: fixture compatibility does not establish every live-site bot check. |
| CL-F3: incomplete dirty/media coverage | **FIXED — FIX** | Blank-frame drafts, unreadable frames and detached audio now report before reload. [background.js:811](../../control/chrome/extension/background.js:811). P24 coverage/designMode removals fail; browser line 85 passes. |
| CL-F4: composed-root protection unproven | **FIXED — KNOWN LIMIT** | The double honors `composed`; P5-composed removal fails, and browser lines 52/61 exercise shadow controls. [page.test.mjs:536](../../control/chrome_tests/page.test.mjs:536). This closes that evidence defect, not the native-created-root FIX above. |
| CL-F5: missing named case leaves CI green | **FIXED — KNOWN LIMIT** | Remove/duplicate a runtime result. [verdicts.mjs:53](../../control/chrome/ci/verdicts.mjs:53) requires exact inventory and verdicts. P29 removal fails; local regression passed. The false-green case is closed. |
| CL-F6: trust/clearing assertions masked | **FIXED — KNOWN LIMIT** | Untrusted Enter and an unconsumed mark now have independent probes. [page.test.mjs:514](../../control/chrome_tests/page.test.mjs:514). My in-memory removals each changed zero arrivals to one. The masked-assertion defect is closed. |
| CL-F7: preloaded popup reload unpinned | **FIXED — KNOWN LIMIT** | Admit a popup already marked preloaded. [background.test.mjs:735](../../control/chrome_tests/background.test.mjs:735). P31-popup removal fails; local regression passed. |
| CL-F8: script-started POST untested | **FIXED — KNOWN LIMIT** | Timer-submit POST into a tab/popup. [review-fixtures.mjs:24](../../control/chrome/ci/review-fixtures.mjs:24). Browser line 86 records refusal without resubmission. |
| CL-F9: excluded-popup test vacuous | **FIXED — KNOWN LIMIT** | The helper now requires the matching tab to exist and handles catalogue paging. [tabs.mjs](../../control/chrome/ci/tabs.mjs:1). P31-http removal fails. |
| CL-F10: fragmented password scan | **FIXED — FIX** | Split a sentinel across audit fragments. [ingress-scan.mjs](../../control/chrome/ci/ingress-scan.mjs:1) reconstructs fragments. P30 scanner removals fail; local scanner tests passed. |
| CL-F11: first script too late | **FIXED — KNOWN LIMIT** | Native capture now runs in the initial head script. [fixture.mjs](../../control/chrome/ci/fixture.mjs:47). P31-head removal fails; browser line 17 passes. |
| CL-F12: GET receiver identity lost | **FIXED — KNOWN LIMIT** | GET form now carries its case identity as a field. [fixture.mjs](../../control/chrome/ci/fixture.mjs:1). P31-get-case removal fails. The vacuous receiver assertion is closed. |

**Owner Enter: not yet closable under the exact requested evidence.**

The immediate-owner/held-scheduled behavior has passing browser evidence. I also independently removed each private check in memory:

| Removed check | Current code arrivals | Mutated code arrivals |
|---|---:|---:|
| Exact form | 0 | 1 |
| Exact submitter | 0 | 1 |
| Trusted input | 0 | 1 |
| Mark clearing | 0 | 1 |

However, the new browser variants call the wrong form/submitter **synchronously inside the owner’s keydown handler**. Their only timer variant is delayed-unconsumed work. The older timers are correctly renamed “after his mark.” Neither establishes a timer firing while his mark is set. Add that browser variant with independent evidence of the overlap before closing this specific condition.

**Verification and regression conclusion**

- Ran the selected browser-free Node batch: **217 passed; three fixture-server tests failed with sandbox `listen EPERM`**. No browser ran.
- Ran browser-free Python policy/exclusion tests: **19 passed**.
- Ran the confirmation, shadow-root and four owner-check removal probes described above, entirely in memory.
- Inspected the retained four-artifact acceptance and mutation evidence. Disk-writing state suites and Linux browser suites were not rerun.
- The fix diff’s catalogue cap, Runtime-subscription removal, state restoration and ordinary-tab compatibility changes have regression evidence. I established no additional harmful regression beyond the two incomplete fixes above.
- Group 12 remains the decided 18d boundary. Working in the owner’s ordinary open tabs was not treated as missing functionality.

CHANGES-NEEDED