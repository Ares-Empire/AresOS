**Three FIX findings remain at `8f48c7bc`.**

1. **FIX — A-3 still escapes when the wrapped listener is registered before insertion.**  
   [page.js:103](../../control/chrome/extension/page.js:103), [page.js:119](../../control/chrome/extension/page.js:119).

   The listener wrapper watches an existing shadow root, but gives a detached receiver no capture. During Claude’s Continue handler:

   ```js
   const donor = opener;
   const root = donor.Element.prototype.attachShadow.call(host, {mode:"closed"});
   const button = donor.Document.prototype.createElement.call(document, "button");
   button.textContent = "Delete";
   EventTarget.prototype.addEventListener.call(button, "click", () => fetch("/delete"));
   donor.Node.prototype.appendChild.call(root, button);
   donor.EventTarget.prototype.dispatchEvent.call(
     button, new MouseEvent("click", {bubbles:true, composed:false, cancelable:true})
   );
   ```

   The listener registration explicitly uses the controlled realm’s **wrapped** method. This therefore falls outside the decided all-native exception.

   My production-code DOM-double probe recorded **one Delete handler and zero held steps**, in both open and closed roots. Registering the listener after insertion correctly produced zero handlers and one held step.

   **Fix:** install capture on the detached receiver before wrapped listener registration; add both ordering variants to the Linux receiver tests.

2. **FIX — non-cancellable image-map and SVG links remain active while reported as stopped.**  
   [guard.js:34](../../control/chrome/extension/guard.js:34), [background.js:321](../../control/chrome/extension/background.js:321).

   `stopDefault()` handles uppercase HTML `A` and `FORM`, then returns success for other elements without neutralizing them. That includes HTML `AREA` and SVG `a`. The DNR rule blocks only the quarantine address, leaving their original destinations reachable.

   **Reproduction:** use a connected `<area alt="Delete" href="/delete" target="_blank">`, or SVG `<a aria-label="Delete" href="/delete">`. From Continue, dispatch a borrowed-native `MouseEvent("click", {bubbles:true, cancelable:false})`.

   The probe preserved `/delete` and returned `activation`—meaning stopped—for both elements. HTML `A` correctly lost its destination. Chromium’s matching-version [anchor implementation](https://github.com/chromium/chromium/blob/157.0.8103.78/third_party/blink/renderer/core/html/html_anchor_element.cc) and [SVG implementation](https://github.com/chromium/chromium/blob/157.0.8103.78/third_party/blink/renderer/core/svg/svg_a_element.cc) confirm these elements have navigation defaults. A destructive request can therefore escape without its question, followed by a false stopped report.

   **Fix:** neutralize every supported native hyperlink type, including SVG’s applicable href attributes, and test navigation, new contexts, ping and downloads. Do not return “stopped” merely because the element is unrecognized.

3. **FIX — compose binding discards meaningful visible whitespace.**  
   [reader.js:253](../../control/chrome/extension/reader.js:253).

   Collapsing all whitespace makes different read-only previews share an approval binding.

   **Reproduction:** place a `<pre>` beside the editor and Send, with Send posting its `textContent`. Prepare this preview:

   ```python
   if approved:
       send()
   audit()
   ```

   While approval waits, indent `audit()` into the conditional. Approve the original question.

   My reader probe produced identical compose text for both versions. Passing both snapshots through the production Python binding also produced **identical complete send bindings**. Consequently, the changed code can be sent without re-asking; the question itself has already lost the indentation.

   **Fix:** preserve visible line breaks and significant whitespace in the password-safe compose representation. Test whitespace-only changes through preparation, re-asking and final dispatch.

**KNOWN LIMIT — the explicitly decided all-native path and click activation are accurately documented.**  
[KNOWN-LIMITS.md:4](./KNOWN-LIMITS.md:4), [KNOWN-LIMITS.md:5](./KNOWN-LIMITS.md:5).

Reproduction is the retained `all-native-limit` fixture using an ordinary same-origin donor for every step. Its result reports the original click as dispatched with delivery unproven; it does not claim nothing happened. The activation measurements support the popup/clipboard statements and explicitly establish nothing about real payment sheets. The rejected fixes and their reasons are recorded.

One-line limit: “All-borrowed-native page actions remain undetected; Claude clicks grant ordinary user activation, and borrowed-native clipboard writes bypass reporting.”

The clipboard implementation otherwise meets this round’s requirements: `write`, `writeText` and trusted `copy` observations contain no clipboard text or hash, request no `clipboardRead` permission, and carry the required instruction against pasting or running page-requested clipboard contents. Ordinary compose changes re-ask once and then stop; outside text stays excluded. I found no additional harmful regression in rule cleanup, password exclusion or tab isolation.

Verification: **244 Node tests and 18 Python tests passed**, and generated artifacts match. GitHub confirms [43319232281](https://github.com/Ares-Empire/AresOS/actions/runs/43319232281) and [43319941241](https://github.com/Ares-Empire/AresOS/actions/runs/43319941241) succeeded in both install modes; their runtime matches this head. Those passing fixtures omit the three cases above. The new reproductions were browser-free probes, not new Linux browser runs.

No files edited, Mac browsers/profiles accessed, containers run, or GitHub state changed.

CHANGES-NEEDED