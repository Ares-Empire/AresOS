Codex gpt-6-astra, 2026-11-18. Rechecked `faccddf7` / code `52891587`. Read both reviews, the brief/design and “The bar,” X1’s progress table, and `git diff e5493c1e..52891587`.

Ran reviewer probes, baseline regressions, mutations and targeted suites: **288 Node tests passed**, including 18 using scratch-only stdin→argv transport; **261/281 Python tests passed**, with 20 socket-restriction failures/errors; focused X1/address tests **27/27 passed**. Initial Node runners stalled under the sandbox. Additional probes passed **840 withholding combinations** and **22,080 credential URL shapes**.

| Original finding | Closed? Test/evidence |
|---|---|
| Security 1: presentational textarea leaks | **Yes.** [fix-x1.test.mjs:14](../../control/chrome_tests/fix-x1.test.mjs#L14); six history cases fail on baseline. |
| Security 2: fragment slash exposes credentials | **Yes.** [test_fix_x1.py:17](../../control/chrome_tests/test_fix_x1.py#L17); baseline fails. |
| Security 3: failed reads retain references | **Yes.** [test_fix_x1.py:60](../../control/chrome_tests/test_fix_x1.py#L60); baseline grows, fixed service stays ≤5,000. |
| Review 1: filename/select state coverage | **Yes.** [fix-x1.test.mjs:41](../../control/chrome_tests/fix-x1.test.mjs#L41); three filename cases fail baseline. Selection already worked; constant-digest mutation now fails all three tests. |
| Review 2: `full` folds options | **Yes.** [test_fix_x1.py:116](../../control/chrome_tests/test_fix_x1.py#L116), including form, scope and deadline cases; baseline fails. |
| Review 3: option labels bypass cut | **Yes.** [test_fix_x1.py:160](../../control/chrome_tests/test_fix_x1.py#L160); baseline fails. |
| Review 4: fixed sentences | **Yes.** [test_view_paging.py:114](../../control/chrome_tests/test_view_paging.py#L114) fails baseline; inherited form wording is an explicit [exception](../../reviews/28-chrome-read/REPORT.md#L34). |
| Security 4 / Review 5: native-size documentation | **Yes.** [Separate limits documented](../../reviews/28-chrome-read/KNOWN-LIMITS.md#L292); inspection, not a runtime regression. |
| Review 6: nonexistent AST function names | **Yes.** [Report corrected](../../reviews/28-chrome-read/REPORT.md#L180); independently compared adapter methods. |
| X1 sibling: legacy generic-role name copy | **Yes.** [reader.test.mjs:929](../../control/chrome_tests/reader.test.mjs#L929); baseline fails. |
| X1 sibling: later `?` switches parsing | **Yes.** [test_fix_x1.py:41](../../control/chrome_tests/test_fix_x1.py#L41); baseline fails. |

**No new findings under the stated bar.** Both credential BLOCKERs are closed. Tested roles, labels and attributes—including late-met roots—did not bypass withholding; no further credential-routing bypass was reproduced.

Approvals and asking paths are unchanged. Reply changes stay within the findings. Chrome instructions remain **4,093/4,096 characters**, and generated artifacts match. Tracked status is clean; the pre-existing untracked review remains untouched. Nothing committed, pushed or dispatched.

SAFE