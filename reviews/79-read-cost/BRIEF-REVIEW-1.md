Codex gpt-6-astra, 2026-11-17. Reviewed draft PR #98 at `bbbabdc679a082203e360f52123aebacbe240620`.

I read `AGENTS.md` and `docs/REVIEW.md` first, then the brief, its PROGRESS, the supplied background reviews, `docs/design/DESIGN.md`, and the relevant qualification, adapter, projection, storage, archive, engine, daemon, test and latency code. I inspected `e2e4eedc` and `git diff origin/main...origin/pkg/28-chrome`; the available #72 head is `0ed7eed2`.

I ran:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_policy`: **18 tests, OK**.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control python3 control/generate.py --check`: **Generated artifacts match definitions**.
- An instruction-length check: **4,093 characters**.
- An entirely in-memory journal probe using the real `Projection` and `Qualification`, described below.
- Git status and diff checks: no tracked changes; the pre-existing untracked review file remained untouched.

I did not run the store-backed suites, whose fixtures write under `.work/`, CI, browser latency measurements or implementation mutations. No files were modified.

1. **BLOCKER — The unchanged-signature shortcut weakens existing rollback detection.**  
   [briefs/79-read-cost.md:100](../../briefs/79-read-cost.md#L100), [briefs/79-read-cost.md:151](../../briefs/79-read-cost.md#L151); existing behavior at [control/aresos_control/chrome/committed.py:158](../../control/aresos_control/chrome/committed.py#L158).

   The brief acknowledges today’s cache eviction but incorrectly concludes that this is “not a new gap.”

   Concrete scenario: warm the qualification cache, then rewrite the journal in place with a same-length qualification record that diverges from shipped history, recomputing the hashes and restoring mtime. Read five other committed records without another write. Today those reads evict the qualification parse; the next `record()` rereads the journal and raises `qualification_rollback`. The proposed slot still passes the offset/signature shortcut and serves its old passing record.

   My in-memory probe produced:

   ```text
   Same signature, before cache eviction: True
   Same signature, after five other cached records: qualification_rollback
   Proposed holds short circuit: True
   ```

   This requires an external rewrite, not an ordinary `_hold()`, but preserving rollback behavior is an explicit requirement. Calling the existing reread accidental does not preserve it. Records above `get()`’s 4 MiB cache threshold also reread today.

   The signature misses content changes that preserve inode, size and mtime; it ignores ctime, which an ordinary rewrite followed by mtime restoration changes. Today’s cache initially misses such changes too, but its reuse is less durable.

   **Fix:** compare the pinned bytes on every cached use, or specify and test an alternative that preserves at least the existing reread behavior. My preference is the byte comparison. Revise test 3 and the unchanged-sweep-surface requirement accordingly: extra fault-injection cases are verification work, not evidence that the stronger check is wrong. Add the unchanged-signature eviction regression; test 9 currently waits for another write and therefore misses it.

2. **SHOULD-FIX — Explicitly protect the object returned by `shipped`, and test that protection.**  
   [briefs/79-read-cost.md:123](../../briefs/79-read-cost.md#L123), [briefs/79-read-cost.md:264](../../briefs/79-read-cost.md#L264).

   A read-only property prevents assignment, but does not prevent mutation of its returned dictionary. A builder can deep-copy the constructor argument, implement `return self._shipped`, and pass both assertions in test 13.

   Concrete failure: after warming the slot, a caller mutates `qualification.shipped['entries']`. The journal pin still holds, so cached answers use the old reconciliation; after invalidation, reconciliation uses the changed baseline. Cache behavior now depends on whether an unrelated invalidation occurred.

   **Fix:** specify that the public getter returns a deep copy, while internal code uses the private baseline. Extend test 13 to mutate nested values obtained through the getter, then verify unchanged results both before and after cache invalidation. Add a mutation that exposes `_shipped` directly.

3. **NIT — Narrow the constant-time claim.**  
   [briefs/79-read-cost.md:10](../../briefs/79-read-cost.md#L10), [briefs/79-read-cost.md:161](../../briefs/79-read-cost.md#L161).

   The design removes repeated whole-history parsing, hashing, copying and validation from hot callers. It does not make every request independent of record size: byte comparisons scale with the journal line, `record()` copies the full record, and switches still process this build’s entries. Describe the improvement in those terms. The 300-entry fixture deliberately adds other builds’ history, so it does not prove constant cost as this build’s own history grows.

The remaining security design is sound against today’s supported writer model:

- `hold()` is the only product writer of this key; [storage.py:508](../../control/aresos_control/storage.py#L508) explicitly skips it during restore. Both callers verify first. Renaming it `_hold()` accurately signals the intended boundary.
- The service uses one selector thread, and the store’s `flock` excludes another cooperating store on the same journal inode. This is not protection against arbitrary external replacement or writers ignoring the lock.
- Reading switches **after** maintenance handles JC3 correctly. A committed update changes the indexed offset even if its write subsequently raises. A pre-commit refusal leaves the old committed record authoritative. Keeping `refresh()`’s `written` flag and texts unchanged is correct.
- Calling `sync()` before reuse preserves truncation and appended-chain refusals. Exact-byte comparison catches changed held lines when the signature changes. Existing `sync()` does not revalidate the entire consumed prefix after arbitrary replacement; the brief should not imply stronger guarantees.
- Current archival compacts SQLite and retains the journal, so it does not relocate the pinned line. Per-object slots also correctly isolate different shipped copies and start empty after restart.
- Filling the slot only after successful validation and reconciliation is essential. The repeated-refusal tests and their premature-fill mutation appropriately guard it.

The build sequence is otherwise practical for a gpt-6.1-sol builder. The mutation table targets meaningful failures, particularly stale reuse, missing reconciliation, accepting an unverified fetch and reading switches before maintenance. Findings 1 and 2 need additional regression cases.

The performance proof is honest: restore the larger record only in the current plain leg, retain the old runtime’s original workload for the runner adjustment, and preserve the 60 current/20 baseline samples and existing gate. Report both median and p95, the runner factor, and all history phases. Passing proves the specified workload meets the existing gate; it does not prove cold-refresh or arbitrary-history performance. Replacing O2’s `record()` call count with full-validation counts is justified, provided the new-record check and the existing behavioral regressions remain.

The PR #72 overlap description still matches the inspected diff. I found no additional direct qualification reader or touched-file overlap omitted from the table. The pending-state and engine conflicts need the prescribed resolutions; the efficiency exclusion and shell-variable regex address the two harness interactions. The `PRAGMA locking_mode` query uses the correct connection. No instruction text is needed, and the current generated-artifact check passes.

**Judgment calls:** this draft contains **six**, not seven; its PROGRESS also says six.

1. **When bytes are compared:** choose every cached read, for finding 1. Do not approve the current equivalence claim.
2. **Maintenance returns nothing; replace O2:** agree. Reading switches afterwards avoids carrying a stale record across refresh.
3. **`record()` returns a private copy:** agree. Apply the same ownership discipline to `shipped`.
4. **Build before #72 merges:** agree. The overlap is manageable and explicitly identified; verify the combined result after resolution.
5. **Builder and review:** agree with gpt-6.1-sol after these corrections. Require an independent reviewer to exercise the rollback mutations, including the new unchanged-signature case.
6. **Build on this branch:** agree. Keeping brief, implementation and proof in one PR is straightforward.
7. **No seventh call appears in the supplied draft.** There is no additional numbered decision to assess.

NOT READY