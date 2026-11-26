Codex gpt-6-astra, 2026-11-18. Fresh security reviewer of PR #72 at `a896fd08`, code head `659e7164`.

I read `AGENTS.md`, `briefs/28-chrome-read.md`, `docs/design/DESIGN.md`, `docs/design/CONTROL.md` section 6, `REPORT.md`, `KNOWN-LIMITS.md`, and reviewed the implementation changes against `origin/main...659e7164`, including the reader, renderer, references, bridge, approval comparisons and packaging boundary.

I ran:

- The report’s Node command, then individual unchanged test files in a scratch copy because the sandbox blocked parts of the runner. **452 tests passed; 11 failed with `EPERM`; three files timed out.** The reader, outline, background and service-comparison suites completed: **319/319 passed**.
- `python3 -m unittest test_outline_action test_view_references test_view_paging test_view_hostile test_questions test_efficiency test_credentials test_bridge`: **150 tests, 140 passed, 10 socket-permission errors**.
- `python3 -m unittest test_view_address test_view_nodes test_view_outline test_view_budgets test_efficiency`: **104 passed**.
- `python3 control/generate.py --check`: **Generated artifacts match definitions**.
- Scratch reader/service probes for withheld text, credential fragments, reference retention, Unicode repair and hostile text. A 116,000-character hostile value remained escaped and reconstructed exactly across 127 pages.

Python ran with bytecode disabled. Scratch test sources remained identical to the reviewed sources. I did not rerun browser CI; the supplied double-green runs are separate evidence.

1. **BLOCKER — Presentational textarea roles bypass withholding.**

   [reader.js:360](../../control/chrome/extension/reader.js#L360), [reader.js:447](../../control/chrome/extension/reader.js#L447)

   `role="none"` or `role="presentation"` makes a textarea’s outline role null. The walker then skips `describe()` and its `safeValue()` check, traversing the textarea’s child text directly.

   **Attack scenario:** a textarea contains a secret in its default text, was unmasked before the reader arrived, and has an ordinary label such as “Notes.” Normally its unknown history requires approval. Adding either presentational role exposes that text without approval.

   My throwing-value-getter fixture reproduced this in an unwatched document and a late-met shadow root. Through `Engine.request`, ordinary `chrome_outline`, `full` and `find` returned the secret; the result also incorrectly reported `typed_fields: 0`. Removing the role restored withholding.

   Apply field withholding independently of presentation roles and prevent textarea default text from entering the generic text walker. This is outside the accepted editable-area exception.

   Evidence: `pkg28-reader-probe.log` (the reviewer's scratch folder `.work/security-28/`, not committed), `pkg28-service-probe.log` (the reviewer's scratch folder `.work/security-28/`, not committed), `pkg28-late-root-probe.log` (the reviewer's scratch folder `.work/security-28/`, not committed).

2. **BLOCKER — A slash in a fragment bypasses credential-parameter redaction.**

   [address.py:127](../../control/aresos_control/chrome/address.py#L127)

   `_fragment()` chooses path handling whenever the fragment contains `/`, before checking for `=`. Consequently, a slash in another parameter can prevent credential values from reaching `_parameter()`.

   **Attack scenario:** a sign-in redirect contains:

   ```text
   https://fixture.test/#otp=739281&next=/home
   ```

   The service returned:

   ```text
   fixture.test/#otp=739281&next=/…
   ```

   The complete credential-named code reaches Claude. Similarly, `#access_token=<part1>/<part2>` (a made-up value) exposes the token’s initial portion.

   The owner accepted short codes under **ordinary names**; this example explicitly names `otp`. Distinguish parameter fragments from route fragments without letting a slash in a parameter value disable credential filtering.

   Evidence: `pkg28-service-probe.log` (the reviewer's scratch folder `.work/security-28/`, not committed), including the actual `Engine.request` result.

3. **SHOULD-FIX — Failed reads bypass the 5,000-reference retention limit.**

   [adapter.py:525](../../control/aresos_control/chrome/adapter.py#L525), [view.py:910](../../control/aresos_control/chrome/view.py#L910), [view.py:949](../../control/aresos_control/chrome/view.py#L949)

   Rendering issues references before cursor validation and envelope fitting. A stale cursor fails afterward; an oversized header fails before `references.returned()`. Neither path trims the newly issued references.

   **Attack scenario:** one controlled tab repeatedly replaces its controls while retaining a 100,000-character title. Reads fail because the header cannot fit, but their references remain allocated. With 6,000 controls, three calls through `Engine.request` retained **6,001 → 12,002 → 18,003** entries in that one tab. Stale-cursor refusals reproduced the same growth.

   Repeated refused reads can therefore grow service memory beyond the advertised per-tab bound. Enforce cleanup on every exit after reference allocation, including cursor and envelope failures. The documented lost-close-event limit does not cover this case: no event or connection was lost.

   Evidence: `pkg28-service-probe.log` (the reviewer's scratch folder `.work/security-28/`, not committed).

4. **NIT — The documented native reply ceiling conflates messages and snapshots.**

   [KNOWN-LIMITS.md:293](../../reviews/28-chrome-read/KNOWN-LIMITS.md#L293)

   The native host limits individual messages to 1 MiB, but `respond()` fragments larger replies and the bridge assembles up to 32 MiB. The strict JSON decoder subsequently imposes its 6 MiB limit. Document these separate limits instead of describing 1 MiB as the complete reply ceiling.

**Known limits:** I accept the explicitly chosen unmasked-editor and ordinary-name short-code exceptions, conservative field/address withholding, oversized/deep-document refusals, probabilistic reference prefixes, and repaired-surrogate equivalence with ambiguous options refused. The completed comparison tests support the stated distinction between identical repaired text and visible changes.

I also accept the documented page-owned network effects, narrow check/input race and residual model susceptibility within the chosen browser-tool threat model. Marking content untrusted is not a guarantee against persuasion; the tested escaping did preserve the output boundary.

Profile pinning, owner-tab behavior and clearer duplicate-label descriptions remain deferred work, acceptable only under the stated requirement that these packages are not deployed separately. None of those accepted limits excuses findings 1–3.

Final `git diff` and staged diff were empty. `git status` showed only the two pre-existing untracked review files. No commits, pushes or workflow dispatches occurred; no `.work/` file exceeded 500 MiB.

CHANGES-NEEDED