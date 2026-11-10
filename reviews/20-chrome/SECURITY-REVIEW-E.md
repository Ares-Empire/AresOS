I found **five should-fix issues** at `60b94384`. No confirmed blocking finding in angle E.

**1. should-fix — The reload guard can discard typing entered during its final document check.**

Location: [background.js:585](../../control/chrome/extension/background.js:585), [background.js:373](../../control/chrome/extension/background.js:373).

The extension checks unsaved content and playback, then performs another asynchronous document-identity query before reloading. That final query checks navigation identity only. Typing or playback started during it does not invalidate the earlier clean result.

**Probe run:** using the existing background VM fixture and actual `dispatch()`, I made `reload_state` return clean, then changed the simulated field to unsaved during the second `Page.getFrameTree` call. Without `reload_taken_tab=true`, the result was:

```text
unsaved: true
reloads: 1
stateChecks: 1
result.reloaded: true
```

This applies to taken tabs and popups. It is an avoidable asynchronous gap beyond the final content check, rather than merely the unavoidable instant between checking and dispatch.

**Fix:** finish the navigation-identity preparation before the final dirty/media check. Invalidate the clean result when owner input arrives during preparation, and return `reload_required` if the content or playback state changed. Add the delayed-final-query regression.

**2. should-fix — Playing audio outside the document tree does not trigger the reload warning.**

Location: [reader.js:211](../../control/chrome/extension/reader.js:211), [background.js:584](../../control/chrome/extension/background.js:584).

Playback detection searches only attached `AUDIO` and `VIDEO` elements. A detached `new Audio()` or Web Audio playback can make the tab audible while this check returns false. The extension never consults `Tab.audible`, so the first act can silently interrupt that playback.

**Probes run:** the actual reader returned `playing:false` for a document without media elements. The actual background reload path, supplied with an audible tab and that reader result, performed one reload without an explicit repeat.

**Container reproduction:** an owner gesture starts a looping `new Audio('/tone.wav')` without appending it. Wait until Chrome reports the tab audible, take/read the tab, then attempt the first click. It should report first; the current path reloads.

**Fix:** include current browser-level audible state in the final playback check, alongside DOM media state. Add detached-audio and Web Audio fixtures for taken tabs and popups.

**3. should-fix — An already-satisfied checkbox request changes the owner’s selected tab.**

Location: [background.js:622](../../control/chrome/extension/background.js:622), [background.js:654](../../control/chrome/extension/background.js:654).

Every `input` command activates its tab before determining whether native input is needed. Consequently, `chrome_check(checked=true)` on an already-checked checkbox selects that tab despite dispatching no checkbox input. The same activation also precedes operations performed entirely through isolated-world code, such as selection and file installation.

This changes what the owner sees and can run visibility/focus handlers unnecessarily. The report’s rationale about selecting a tab for headed native input does not justify activating a tab for a no-op.

**Probe run:** actual `dispatch()` with an inactive controlled tab and an already-checked checkbox produced:

```text
effects: [{tab:7, change:{active:true}}]
```

No checkbox input was dispatched.

**Fix:** return without activation for an already-satisfied check, after validating its reference/state. Restrict tab activation to branches that actually require selected-tab native input. Test with an ordinary owner tab selected in the same window.

**4. should-fix — The wrappers expose an avoidable native-function fingerprint that the compatibility comparison misses.**

Location: [page.js:72](../../control/chrome/extension/page.js:72), [compatibility.mjs:13](../../control/chrome/ci/compatibility.mjs:13).

The replacements are ordinary function expressions. They acquire an own `prototype` property absent from the methods they replace. The compatibility fixture compares their strings using the `Function.prototype.toString` replacement installed by the same script, so its passing result does not cover this observable difference.

**Probe run:** executing the actual page script through the existing VM fixture changed the four methods’ shapes from:

```text
own properties: ["length","name"]
```

to:

```text
own properties: ["length","name","prototype"]
```

A pristine-realm stringifier also exposed the wrapper source while the patched stringifier returned the saved method’s string.

This matters for the requested bot-check visibility review: a site can detect the changed function shape without activating an asking control.

**Fix:** use nonconstructible wrappers, such as concise methods, and preserve native own-property descriptors. Extend the baseline/outside/controlled comparison to function shape and construction behaviour. Explicitly disclose the remaining pristine-realm detection residual; the current string comparison cannot establish general bot-check compatibility.

**5. should-fix — Stop retains browsing restrictions indefinitely when native restoration cannot finish.**

Location: [background.js:220](../../control/chrome/extension/background.js:220), [background.js:402](../../control/chrome/extension/background.js:402), [page.js:109](../../control/chrome/extension/page.js:109).

A site can freeze a patched prototype after startup. The wrapper can be deactivated, but its property cannot be restored. Release then waits for document destruction. Meanwhile, `rules()` includes every `releasing` tab, retaining the extension’s navigation blocks after input authority has ended.

The report discloses deferred cleanup, but continued network blocking is a separate everyday-browsing consequence: after Stop, the owner can still be prevented from navigating that tab to an excluded approval/settings fixture.

**Probe run:** actual release/rule orchestration with persistent restoration failure returned:

```text
stopped: true
cleanup_pending: 1
controlled: false
releasing: true
blockedTabIds: [7]
```

Recomputing the rules retained tab 7. Only simulated document destruction removed it.

**Container reproduction:** freeze `HTMLElement.prototype` after the controlled startup script runs, press Stop, then navigate manually to `approval.test`. Check that no extension DNR block remains.

**Fix:** separate revoking input authority and navigation restrictions from deferred native cleanup. Remove stopped tabs from session blocking rules promptly; retain cleanup handles and truthful pending status independently. Keep the popup open and preserve its document.

The principal scope boundary passes inspection: the manifest installs no page scripts, dynamic registration installs only inert isolated `context.js`, and MAIN-world hooks are installed through controlled-tab setup. The retained popup evidence supports unchanged windows, opener flow, Stop document preservation, POST refusal, and untouched ordinary openers for the recorded cases.

I ran the relevant **115 browser-free Node tests: 115 passed**, audited all four retained receiver datasets from runs `42773242428` and `42773249076`, and independently compared their native baseline/outside/controlled JSON results: all matched. Runtime and workflow files at the reviewed head match verified source `ab7aba92`.

Outside E, I confirmed no additional new defect. Group 12 remains explicitly false pending 18d; that is the stated Now-stage boundary. Real extension coexistence and live-site compatibility remain unverified as reported.

No files changed, no browser or container was started, and nothing was pushed or posted to GitHub.

CHANGES-NEEDED