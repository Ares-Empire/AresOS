At **e051dd59**, I found **no blocking, should-fix or nit findings** in the requested diff. Both review-2 fixes hold.

1. **Pre-change refusal closes the intent safely.** In [start-next.sh](/var/home/ares/AresOS-22c-review/os/release/start-next.sh:9), all calls that exit 3 precede `set-default`. There are no traps or later paths that produce 3. Failures of the status reads, `set-default` or `sync` raise uncaught Python exceptions—even if the subprocess itself returns 3. Postcondition failures also remain ordinary failures. Kills produce signal-related statuses; `set -e` does not convert these to 3.

   [The caller](/var/home/ares/AresOS-22c-review/os/owner-tools/owner.py:1583) archives only `Failed.code == 3`; other failures retain the intent. The archive is file-fsynced, renamed and directory-fsynced before the open intent is unlinked and the directory synced again. Only then is the final STOP raised and printed. The script’s earlier stderr is captured.

   I replayed `[R27*, R13, S]`, the outside reorder to `[R13, R27*, S]`, and the refusal. No owner reorder occurs. Recovery works immediately and after booting **each of the three choices**, including selecting stock, restarting and confirming it. The acknowledged interruption window before archival completes can still leave an unresolved intent; that fails safe and is within the stated bar.

2. **Restoration excludes renewed finish.** The [guard](/var/home/ares/AresOS-22c-review/os/owner-tools/owner.py:2155) runs before any finish write and names `layout abandon`, including from the original login.

   I replayed German → US proof, finish cut after its console write, second-login abandon cut after its console write, then original-login finish. Finish refuses without changing settings; abandon after restart completes, and a subsequent new trial succeeds.

   Other commands do not bypass this:
   - `begin` refuses while the trial or applicable repair note exists.
   - `proof` changes evidence only.
   - `revert` changes the runtime console map and evidence, preserving `restoring`.
   - Another fresh-login `abandon` can resume the authorized restoration. It preserves and durably republishes the intent before persistent writes. The command lock prevents concurrent owner commands from interleaving.

Both [revert proofs](/var/home/ares/AresOS-22c-review/os/tests/test_ways_back_reverts.py:123) test the actual missing behavior: disabling refusal closure leaves the journal open; removing the restoration guard lets finish proceed. They reject unrelated exceptions as evidence.

Verification: **12 focused tests passed (`0.750s; OK`)**, including both replays and revert proofs, plus **12 additional restoration cases** covering begin/proof/revert/second abandon at three interruption points. Records used an in-memory filesystem adapter. Shell syntax, source/payload equality, payload hashes and both changed hash manifests passed. No prohibited tests, owner commands or deployment binaries ran; no repository files were changed. Real power-loss durability and exhaustive model exploration were not rerun.

The [workflow diff](/var/home/ares/AresOS-22c-review/.github/workflows/os-image.yml:53) changes only the checks-only timeout **25 → 40**, plus two comments. No other job, permission or trigger changed. There are no unrelated production-tool changes.

**Next-stage advice:** yes, charging roughly 20 extra minutes to every hosted checks-only invocation is a practical problem once this reaches main. Keep focused regressions and a deterministic bounded model slice in every run. Run the full model when its dependencies change—including owner tools, release scripts, model/host/ledger/memo code, relevant fixtures and test infrastructure—and provide explicit full runs plus periodic coverage. Treat uncertain dependency classification conservatively. This is advice, not a finding against these fixes.

SAFE