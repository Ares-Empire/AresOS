# 27c: the hosted checks run the owner tools' namespace tests

Empire board brief 284. Follow-up to 27b.

**Goal:** the hosted regression run (`OS image` workflow, `checks_only`) runs the 136 tests it skips today, so the owner tools' self-update is tested somewhere again.

**Why:** `test_owner_update.ToolsUpdateTest` runs the tools' update in a private user namespace. GitHub's runner refuses unprivileged user namespaces (`unshare: write failed /proc/self/uid_map: Operation not permitted`), so the hosted run skips all 136 (run 43468641559: 969 tests, 136 skipped). They used to run in WSL on the Windows laptop, which is retired. On the AresOS laptop this module must not run at all (it reaches the real `rpm-ostree`). So since 2026-11-13 these tests run nowhere.

**In scope:**
- `.github/workflows/os-image.yml`, the checks-only job (`regressions`) only: one step before the tests that lets the runner create unprivileged user namespaces (on Ubuntu 24.04 the restriction is `kernel.apparmor_restrict_unprivileged_userns`), with a comment saying why. No other job, no permission, trigger or condition changes.
- The tests that pin the workflow's steps, made true again without weakening them.
- The workflow is bound by package 27's rehearsal: record its new bytes with `python3 reviews/27-first-update-release/rebind.py pending "<note>"`.
- A short `reviews/27c-hosted-namespace-tests/REPORT.md` in the AGENTS format.

**Out of scope:** the owner tools, the tests' logic, any other job, anything under `os/manifest/ci/27/`.

**Acceptance:**
- A hosted `checks_only` run on the branch with 0 skipped namespace tests; the report gives the run ID, the totals, and how many of the 136 pass.
- If some of the 136 fail once they run, do not fix them here: list each failing test with its message in the report and stop. That is a finding about code that has not been tested since WSL, and the integrator decides.
- `git diff main --stat` shows only the files named above.

**If unsure:** change less and report.

**Model:** a Claude agent on Opus. Review: a fresh Codex context.
