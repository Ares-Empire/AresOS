Codex gpt-6-astra, 2026-11-18.

Reviewed `1dfe3e49`: `AGENTS.md`, `BRIEF-CROSS-5.md`, `REVISION-CROSS-5.md`, `git diff 918fba67..1dfe3e49`, the revised briefs, CONTROL §6 and ALIGNMENT. Checked the relevant code against available `origin/main`, PR #72’s `origin/pkg/28-chrome`, and 18c-b’s branch progress and storage test.

Ran, with test copies and generated files confined to `.work/recheck-28ab/`:

- `python3 -m unittest test_bridge test_questions test_restore_lock`: **53 tests, 10 errors**; all ten were sandbox `PermissionError` failures on socket sends.
- PR #72’s `python3 -m unittest test_view_references`: **20 tests, OK**.
- A scratch probe of the real Control store’s restore behavior: **passed**, demonstrating the distinction described below.
- Instruction measurement: **4,093 instructions + 5,085 descriptions = 9,178 characters; 30 tools**.
- `git diff --check 918fba67..1dfe3e49`: passed. Attempted the branch’s `service-comparisons.test.mjs`; it could not run because `node` was unavailable.

No browser, workflow or privileged command ran. Final tracked and staged diffs are empty. The pre-existing untracked `reviews/28-chrome-capability/RECHECK-CROSS-5.md` remains untouched.

“Closed” below means the brief specifies the behavior, tests and reviewer mutations; it does not mean implementation evidence exists. The two owner decisions remain pending.

| BRIEF-CROSS-5 finding | Closed? | Where and assessment |
|---|---|---|
| 1. Profile pinning across image updates | **Not fully** | [28b:182](../../briefs/28b-chrome-his-tabs.md#L182), [28b:1035](../../briefs/28b-chrome-his-tabs.md#L1035), [18c-b:147](../../briefs/18c-b-chrome-image.md#L147). Replacement, second-profile-first, retired-pair refusal and owner-confirmed A → B → A are specified, with mutations. Restored service state is not covered; finding 1 below. |
| 2. Held submissions discard unrelated work | **Closed, conditional on owner choice** | [28b:708](../../briefs/28b-chrome-his-tabs.md#L708). Whole-tab checks occur before reservation and immediately before resumption, including formerly clean reports. Combined send/loss approval, fresh replacement approval, original expiry, trusted-send refusal and no preliminary reload are explicit. Two-form tests and mutations cover both native kinds. Board #138 stays in taken tabs. |
| 3. `chrome_open(ref=…)` bypasses recognition | **Closed** | [28a:353](../../briefs/28a-chrome-act.md#L353), [28b:272](../../briefs/28b-chrome-his-tabs.md#L272). Fresh classification precedes opening; asking or missing facts refuse without tab creation or requests. His-tab references inherit it. Delete/Unsubscribe receiver tests and classification-removal mutation are specified. Explicit URL, tab-address and library policies remain separate. |
| 4. Reload approval freshness | **Closed** | [28b:760](../../briefs/28b-chrome-his-tabs.md#L760). Private identities, subsequent edit generations, ongoing drawing, removed frames, continuous observation and final live queries are defined. Tests and mutations distinguish these from sticky first-use reporting. |
| 5. Page text in reload errors | **Closed** | [28a:611](../../briefs/28a-chrome-act.md#L611), [28b:170](../../briefs/28b-chrome-his-tabs.md#L170). Fixed messages and structured untrusted loss data cover bare, batched, kept-tab and stored results. Shared transport changes are expressly permitted. Hostile-label tests and interpolation/flattening mutations address main’s actual error path. |
| 6. CONTROL §6 parity | **Closed** | [CONTROL:842](../../docs/design/CONTROL.md#L842), [CONTROL:1531](../../docs/design/CONTROL.md#L1531), [28a:955](../../briefs/28a-chrome-act.md#L955). Separator-containing tokens and the 5,000-reference ceiling are incorporated, with normative delegation and retained regression/mutation requirements. |

1. **BLOCKER — Profile authorization needs an explicit restore contract.**

   **Where:** [28b:192](../../briefs/28b-chrome-his-tabs.md#L192), [28b:207](../../briefs/28b-chrome-his-tabs.md#L207), [28b:1042](../../briefs/28b-chrome-his-tabs.md#L1042).

   The brief requires a durable record through the existing store API, but does not say which store view authorizes a handshake or what happens to an admitted connection across restore confirmation.

   **Concrete failure:** profile P is pinned; a backup is taken; the owner switches to Q, revoking P; the older database is restored. During the restore lock, ordinary `store.get()` returns P while `store.chrome_state.get()` correctly returns Q from committed evidence. A builder could use the ordinary read when admitting P’s handshake. Restore confirmation restores Q’s record, but does not itself close or revalidate that cached browser connection. Once the application gate reopens, P could serve Q’s requests.

   The scratch probe demonstrated the stale/current record distinction and subsequent restoration. This is a specification gap for the future handshake, **not a demonstrated bypass in an implemented 28b**. Main admits native connections separately from the application restore gate: [daemon.py:238](../../control/aresos_control/daemon.py#L238), [engine.py:575](../../control/aresos_control/engine.py#L575). Restore reconstructs Chrome records through [storage.py:506](../../control/aresos_control/storage.py#L506).

   **Required amendment:** make committed Chrome evidence authoritative for the pin; define admission during restore and connection invalidation/revalidation across recovery. Missing restored state must not become first-connect enrollment. Add a P → Q → restore-P-backup test, including connection attempts before and after confirmation. Mutate the authoritative lookup to the disposable database and omit recovery revalidation; the test must catch both.

   Ordinary replacement and supported A → B → A otherwise have a coherent contract: only the current pair reconnects automatically, and each newly authorized replacement retains the logical pin. Copying the current installation identity into another profile remains within the explicitly retained local-state-copy/impersonation limitation; it is not cryptographic proof of browser-profile identity.

2. **SHOULD-FIX — 18c-b’s remaining-step handoff is behind its actual build state.**

   **Where:** [18c-b:182](../../briefs/18c-b-chrome-image.md#L182), [18c-b:720](../../briefs/18c-b-chrome-image.md#L720), [REVISION-CROSS-5:131](../../reviews/28-chrome-capability/REVISION-CROSS-5.md#L131).

   The handoff calls 3a the next installation step. At available branch head `91ad33d6`, [PROGRESS.md:6](../../reviews/18c-b-chrome-image/PROGRESS.md#L6) records 3a already implemented but stopped after its two allowed image-build rounds. The remaining defect is the PEM scanner’s assumption that `<scan-root>/root` resolves to a directory; 3b explicitly waits for the lead’s disposition.

   **Concrete failure:** a fresh builder following this handoff could repeat completed installation work or launch another image build without respecting the exhausted run allowance, instead of fixing the recorded checker defect.

   Update the list to **3a fix**, preserve that stop condition, and require the lead’s disposition before further image runs or 3b. The changes assigned to 3b, 4/4b, 5 and 6 are otherwise clear, including ownership of the combined pin proof when 28b merges later.

The new package-28 requirements are consistent and testable. PR #72 now has a headed step 13d; its code repairs fresh comparison operands and resolves repaired option values back to a unique native option. Reference cleanup checks the current session and preserves the counter. The briefs carry these rules into the new paths. Distinguishable field descriptions correctly belong to 28a, and the tests inspect the actual question sentence, including repaired-label collisions, rather than merely checking distinct IDs.

I found no unintended reopening of the settled list projections, approval ceilings, placeholder sweep, late-shadow-root rules or popup/dialog policy. The instruction budget is handled explicitly: 28a compacts before additions and pins 2,800; 28b verifies that headroom and pins 3,800. Their dependency order is workable for the named builder, subject to the owner gates and corrections above. The storage exception is appropriately limited in purpose to one installation-ID record in one module, with no general storage permission or page-data allowance.

**Owner question 1:** The recommendation is sound as an explicit change from automatic reconnection, after the restore gap is fixed. Explain that “confirm once” currently means opening the chosen profile’s helper details and running an administrator command with its two IDs—not a specified one-click prompt. Also retain the distinction between owner-authorized continuity and technical proof against copied profile state.

**Owner question 2:** The question accurately presents the design choice, and I support the combined-question recommendation. It names both sending and possible loss, preserves delayed owner submissions without destroying the held form first, and requires a fresh question after further work. Refusal remains a valid alternative; neither answer should be inferred.

NOT READY