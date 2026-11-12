# Independent package review — initial implementation

Reviewer: fresh `gpt-6.1-sol`, high. Reviewed head `f874bd79737a9f2c1f3fc10871a2bafa2775739a`;
implementation diff from `59de0b15`. Verdict: **CHANGES-NEEDED**.

**Read:** brief 18d and parallel-start note; authoritative `origin/main` section 7,
rule 4.10 and decision 24/follow-ups; policy generation, protected path reader,
trusted-send guard, UID guard, proxy instructions, native precedence, optional
sandbox, workflows and affected tests. No additional concrete safety defect found.

1. **P1:** `control/boundary/fixtures.json` retained the removed managed MCP file and
   launcher as write targets; the positive controls read originals unconditionally,
   causing FileNotFoundError before native/precedence checks.
2. **P1:** `control/tests/test_integration.py` retained the old exact assistant-user
   diagnostic; the owner real/effective-UID diagnostic broke its assertion.
3. **P1:** `control/mail_tests/test_review_fixes_9.py` read the removed
   `managed-mcp.json` instead of the flat `user-mcp.json` map.

**Run:** generated-artifact check printed `Generated artifacts match definitions`;
`git diff --check 59de0b15..f874bd79` passed. **Not run by reviewer:** Linux/native
container checks (local Docker unavailable). No files changed by the reviewer.

All three findings were corrected in `8d1cd411`; final re-review follows separately.
