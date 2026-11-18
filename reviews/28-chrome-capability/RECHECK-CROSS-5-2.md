Codex gpt-6-astra, 2026-11-18. Read AGENTS.md, the prior recheck, Revision 2, `git diff d175acdd..426000c5`, all three briefs, CONTROL §6 and ALIGNMENT; checked the specified store/daemon/engine code, main and 18c-b’s F7 flow, and PR #72’s adapter.

Ran scratch-isolated unit tests: **34 tests, 24 sandbox socket errors and one consequent call-count failure**. The restore-store probe, document comparisons and diff check passed. Instruction measurement remains **4,093 + 5,085 = 9,178 characters**. No tracked changes; pre-existing untracked review untouched. No workflows or privileged commands ran.

“Closed” means the build contract is sufficient, not that its future implementation has passed.

| RECHECK-CROSS-5 item | Status | Where |
|---|---|---|
| Profile pinning / restore blocker | **Closed** | [28b:198](../../briefs/28b-chrome-his-tabs.md#L198), [28b:246](../../briefs/28b-chrome-his-tabs.md#L246): committed evidence alone; quarantine, serialized connection retirement, fresh handshake and missing-state refusal. |
| Restore tests and mutations | **Closed** | [28b:1099](../../briefs/28b-chrome-his-tabs.md#L1099): P’s refusal catches disposable lookup; Q’s mandatory reconnect independently catches omitted retirement. Dialogs, queued messages, references, lists and approvals are covered. |
| Held-submission loss | **Closed** | [28b:759](../../briefs/28b-chrome-his-tabs.md#L759): combined question selected; connection-bound loss checks remain. |
| Reference-open recognition | **Closed** | [28a:357](../../briefs/28a-chrome-act.md#L357). Unchanged. |
| Reload freshness | **Closed** | [28b:809](../../briefs/28b-chrome-his-tabs.md#L809). Unchanged. |
| Untrusted loss text | **Closed** | [28a:613](../../briefs/28a-chrome-act.md#L613). Unchanged. |
| CONTROL parity and inherited rules | **Closed** | [28a:70](../../briefs/28a-chrome-act.md#L70), [28a:956](../../briefs/28a-chrome-act.md#L956): Unicode, cleanup, distinct descriptions, budgets, order and existing mutation mappings preserved. |
| 18c-b handoff | **Closed** | [18c-b:202](../../briefs/18c-b-chrome-image.md#L202): **3a fix**, exhausted allowance and lead decision before another image run or 3b. |
| “Confirm once” meant administrator command | **Closed** | [28b:204](../../briefs/28b-chrome-his-tabs.md#L204), [28b:1111](../../briefs/28b-chrome-his-tabs.md#L1111): password dialog replaces typed IDs; candidate/name/pin/generation binding and negative cases specified. |

1. **NIT — Remaining question-2 wording is stale.** [28b:74](../../briefs/28b-chrome-his-tabs.md#L74) still calls both recommendations unaccepted, and [CONTROL:653](../../docs/design/CONTROL.md#L653) still describes a recommended path. Update these to board #353’s decision. The explicit acceptance in 28b item 4c/build step 5 and [ALIGNMENT:373](../../reviews/28-chrome-capability/ALIGNMENT.md#L373) already settles the behavior.

Question 1 is plain, faithful and sound: it explains the password, manually supplied profile name, replacement interruption and copied-state limitation. The specified helper/page/extension/tool paths cannot authorize replacement without F7 success; stale or replayed success cannot transfer candidates. This is buildable using the existing action, with 28b step 2 owning the missing flow and 18c-b owning real-session proof. Owner acceptance remains pending.

READY