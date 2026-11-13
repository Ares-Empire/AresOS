**One FIX finding at `56f93c89`.**

**FIX — relative hyperlink destinations are bound incorrectly.**  
[reader.js:278](../../control/chrome/extension/reader.js:278)

The new `hyperlinkAddress()` resolves addresses against `location.href`, ignoring the document’s effective base URL. This replaces the previous native HTML-anchor `.href` reading.

Reproduction on `https://fixture.test/`:

```html
<base href="/invoice-1/">
<a href="delete">Delete invoice</a>
```

Prepare Delete, change the base to `/invoice-2/` while approval waits, then approve. The reader reports `https://fixture.test/delete` both times, although the native destination changes from `/invoice-1/delete` to `/invoice-2/delete`. Neither approval binding detects that change. The code therefore permits deletion at a different destination without a fresh question.

Browser-free production-code probes confirmed:

- At `8f48c7bc`, the reader reports both correct destinations and the bindings differ.
- At `56f93c89`, both reader destinations are wrong and the complete Python and extension bindings remain identical.

**Fix:** use native resolved URL getters for HTML links and the effective native base URI for SVG links. Add base-URL mutation tests for `a`, `area`, and SVG `a`, including inherited bases in inline frames, with stale approval producing zero receiver arrivals.

The three requested fix classes otherwise pass this scoped check:

- **Wrapped/native matrix:** all 128 combinations are generated, including both listener orderings. All **384** production-code probes passed across same-document, foreign-wrapper and adoption cases. Every non-all-native row was held. The browser subset includes every single-wrapped-step combination.
- **Default neutralisation:** the listed hyperlinks, submitters, image inputs and external `form=` buttons have tests. Unsupported non-cancellable defaults return `activation_unknown`. The Linux matrix contains **33** cases.
- **Whitespace:** all **14** reader → Python binding → initial/replacement question probes passed. Significant indentation and line breaks remain distinct; `pre-line` correctly collapses insignificant indentation. Tests cover final-dispatch rejection and the bounded second-change stop.

Five focused Node suites passed; generated artifacts match. `git diff --check` reported trailing whitespace in review/evidence files only. I found no additional harmful regression in the scoped password, isolation or cleanup changes.

The retained timeout-run evidence records all **107** new receiver sequences passing, but does not establish final acceptance. Runtime, tests and workflow files match `63c81414`; its pending pair must establish two complete runs in both installation modes, including native activation, cross-world routing, privacy and owner-browsing checks. Its existing cases cannot detect the base-URL finding above.

No files edited, browsers/profiles accessed, containers run, or GitHub state changed.

CHANGES-NEEDED