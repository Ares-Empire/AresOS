**A-3 is PARTLY fixed; B-6 is FIXED. Owner Enter can close. `KNOWN-LIMITS.md` still includes outcomes that meet your FIX definition.**

Reviewed `8627e65e` and `65aca3e6..8627e65e`. No files edited, browsers/profiles accessed, containers run, or GitHub state changed.

**FIX — A-3: PARTLY fixed.** [page.js:90](../../control/chrome/extension/page.js:90), [review-fixtures.mjs:63](../../control/chrome/ci/review-fixtures.mjs:63).

Composed events now acquire capture. Non-composed events still escape when insertion also uses the borrowed native function. The Linux fixture uses native insertion only when `composed` is true, leaving this combination uncovered.

Reproduce inside Claude’s Continue handler, with a labelled Delete link whose handler sends the deletion:

```js
const root = opener.Element.prototype.attachShadow.call(host, {mode:"closed"});
opener.Node.prototype.appendChild.call(root, link);
opener.EventTarget.prototype.dispatchEvent.call(
  link, new MouseEvent("click", {
    bubbles:true, composed:false, cancelable:true
  })
);
```

My in-memory probe ran production guard/page code with the repository’s shadow-aware double:

| Insertion / event | Delete handlers | Held steps |
|---|---:|---:|
| Wrapped / non-composed | 0 | 1 |
| Native / composed | 0 | 1 |
| Native / non-composed | **1** | **0** |

Both open and closed roots reproduced it. This permits a clearly labelled deletion without its question or uncertainty report. These are simulated handler counters; I did not run this additional variant in a browser.

**Fix:** establish synchronous capture for this native-insertion route and add the missing non-composed variants. The current insertion hooks do not establish complete coverage.

**FIX — B-6: FIXED.** [adapter.py:33](../../control/aresos_control/chrome/adapter.py:33), [background.js:648](../../control/chrome/extension/background.js:648), [policy.py:140](../../control/aresos_control/chrome/policy.py:140).

Preparing a form-contained confirmation, changing its outside draft, and approving now refuses before input. My Python probe covered OK/Send and button/submit variants; all bound the draft and refused incomplete frame coverage. The JavaScript regression passed; removing the fix in memory made it fail.

Linux evidence also covers all three form variants: stale approval has zero arrivals, fresh approval sends `Different draft` once, and repeat adds nothing. I checked the [external job log](https://github.com/Ares-Empire/AresOS/actions/runs/43166895797/job/131010747871), lines 3812–3814, and retained receiver records.

**Owner Enter: can close the requested evidence condition.** The previous KNOWN LIMIT was an evidence gap.

The [fixture:47](../../control/chrome/ci/review-fixtures.mjs:47) starts a real timer from Claude’s click. Observation instrumentation does not extend mark lifetime. GitHub job-log line 3742 and the [independent receiver record:404](./records/recheck/closing/receiver-audit.json:404) show:

- Enter keyup mark: `1794464248090.1–1794464248093.5`.
- Timer fired: `1794464248091`, inside that interval.
- Owner submission arrived once, `9.4 ms` after page submission.
- Timer submission stayed at zero until its own approval; then **0/1/1**.

The overlapping mark is the subsequent **keyup/Enter** mark; the immediate submission consumed Chrome’s trusted submitter-click mark. I independently reran all four removal probes—form, submitter, trust and clearing. Each baseline passed; each removal failed with one unauthorized simulated arrival.

**FIX — the known-limits list is not low-harm-only.**

- **[KNOWN-LIMITS.md:5](./KNOWN-LIMITS.md:5): non-cancellable default activation.** Reproduce with the existing labelled Delete-link fixture and borrowed native dispatch, `cancelable:false`. The [retained case:506](./records/recheck/closing/fixed-case-audit.json:506) records **one default request and no approval sequence**. A destructive destination therefore acts without its question. **Fix:** prevent the harmful default action; reporting `unknown` afterwards does not authorize it.

- **[KNOWN-LIMITS.md:6](./KNOWN-LIMITS.md:6): changed outgoing preview text.** Prepare Send, change the read-only preview, approve. The existing [test:340](../../control/chrome/ci/matrices.mjs:340) explicitly requires the receiver to receive `Changed read-only preview`; both inspected Linux logs report PASS. This sends content absent from the approved binding. **Fix:** bind the outgoing preview through supported page recognition, or refuse that send when its complete content cannot be established.

These are inherited residuals, not newly introduced runtime regressions. Their classification follows your current harm definition despite the older specification accepting them.

I found no additional harmful regression in the fix diff. Local verification passed **204 selected Node tests and 17 Python policy tests**, plus the in-memory probes above. Linux browser evidence was inspected, not rerun.

CHANGES-NEEDED