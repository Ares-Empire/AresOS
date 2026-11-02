# 14zj: Make the staged-transport ACKs tolerate kernel lines; probe 19 and qualification 8

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zi still apply, with the change below.

## Diagnosis (from the 14zi report)

The syntax-phase ACK `:10:0` was immediately followed by `[   58.604886] async_tx: api initialized (async)` before its newline. The exact predicate `:10:(status)\r?\n` never matched, and the transport correctly stopped after 10 seconds.

The kernel prints to the same serial console at any byte boundary of a userspace write. The checksum-framed export already copes with that. The 14zb ACKs don't.

## Fix (harness only)

1. **Self-delimiting ACKs:** use something like `ARESOS_ACK:<nonce>:<phase>:<index>:<status>:END`, with a per-transfer random nonce, so neither a newline nor a missing newline matters.
2. **Strip kernel lines first:** before matching any ACK (or any other serial marker), remove complete kernel lines `\[\s*\d+\.\d+\] [^\r\n]*\r?\n` wherever they appear, mid-line included. Reuse the same function the export decoder uses, or move both onto one shared function.
3. **Keep the rest:** keep the per-ACK bounded waits, the exact match on nonce, phase, index and status, the STOP on a mismatched or duplicate ACK, and the verified-SHA requirement. No retry of a transfer without a recorded reason; one bounded re-send of the same chunk after a timeout is allowed only if the receiver confirms it didn't store it.
4. **Local tests:**
   - the exact 14zi transcript must now parse
   - a kernel line inserted at every byte position of an ACK must parse
   - a truncated kernel line must STOP, not mis-parse
   - a duplicate or out-of-order ACK must STOP
   - the export decoder must still pass its existing tests
5. **Scan every other serial-marker match** in the harness (`ARESOS_CMD_DONE`, readiness markers, hidden-resync receipts) for the same assumption, and fix them the same way.

## Budget (owner's $6 cap; about $4.00 billed)

One push, plus a probe of at most 72, plus a qualification of at most 160 is about $1.43 at worst, which fits. Settings for package `14` only:
- `minute_cap`: 1200 (941 + 238 = 1179)
- `dispatch_caps.probe`: **19**
- `owner-tools`: **8** (qualification 8 not yet used)

## Then

1. Pinned local gitleaks, the replay and strict checks; a local Windows retry is allowed. Exactly **one** push.
2. Fresh exact-head privacy, the ledger, billing and the budget.
3. **Probe 19**. Only if it passes, **qualification 8 on the same head**.
4. Any CI stop: report it with the exported diagnostics, no rerun.
5. When acceptance is met, restore closing 12 and reserve 150 in a final commit, push once, mark PR #13 ready for review, and say the run is over so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
