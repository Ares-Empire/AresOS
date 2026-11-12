Reviewed **79ae5de11707d94a5c5a9a8d43328baa5c6e87b7** on `pkg/19b-owner-state`, including the combined Mail/shared-base implementation and `d3babf1f...79ae5de1`.

**No blocking security finding under the owner’s November 12 review bar.** I found one nonblocking should-fix in the optional oracle and its reported results. The remaining documented limits concern disclosure, availability, or explicitly accepted races; I found no route from them to approval bypass, credential exposure, another recipient delivery, or system-operator damage.

No files were edited and no containers were run.

**Should-fix: the optional oracle misreads an escaped Trash label as “ordinary.”**

Location: [compare.py:58](/Users/pab/AresOS-19b-state/control/owner_state_oracle/compare.py:58), especially lines 65–67. The resulting inaccurate claim appears in [owner_state_quiet_gaps.json:50](/Users/pab/AresOS-19b-state/control/mail_tests/owner_state_quiet_gaps.json:50) and [REPORT.md:2942](/Users/pab/AresOS-19b-state/reviews/19b-owner-state/REPORT.md:2942).

The production warning escapes the backslash in the IMAP role `\Trash`, producing two literal backslashes in the public string. The oracle’s expression accepts only zero or one before the role name. It therefore classifies a warning that names Trash as ordinary.

Minimal reproduction, run with `PYTHONPATH=control .work/venv/bin/python -B`:

```python
from types import SimpleNamespace
from aresos_control.common import visible
from owner_state_oracle.records import Record
from owner_state_oracle.compare import notice_facts

source = "mail:rename:example"
notice = {
    "operation_id": "example",
    "app": "mail",
    "state": "partial",
    "untrusted_content": {
        "reason": visible(
            r"Nothing was deleted. It is now Renamed, inside \Trash."
        ),
        "intent_key": source,
        "filing_id": "example",
    },
}
record = Record(rows={
    "notice:example": {
        "source_key": source,
        "check_kind": "rename",
    },
})
oracle = SimpleNamespace(
    detected=[],
    warning_contexts={source: {"target": "Renamed"}},
)
print(next(
    fact.detail
    for fact in notice_facts(notice, record, oracle)
    if fact.kind == "rename"
))
```

Actual output:

```text
{"role":"ordinary"}
```

I also reproduced this through production RENAME/warning logic with synthetic IMAP: the public warning named Trash, all seven messages remained, and only one RENAME occurred. The incorrect classification happens in the oracle.

**Harm:** misleading review evidence and a pinned false positive. It does not change mailbox contents or conceal Trash in that production response.

**Fix:** make the oracle understand the escaped public representation, add regressions for direct and ancestor special roles, and regenerate the affected ledger/report entries. Preserve production escaping and the separate `G22-rename` regression. That latter case remains real when unresolved Drafts causes the live result to fall back to “an unverified role.”

**Security properties checked**

| Area | Result |
|---|---|
| Whole, bound approval | Send, message delete, folder delete, and both unsubscribe routes use service-written approval content. Submission checks the action, generation, exact input and stored approval. Changed, missing, extra, reordered and repeated approval fields refuse. Oversize approval refuses rather than truncating. |
| Who answers approval | The installed, verified Claude Code managed policy enforces asking. Owner-only account/configuration actions are unavailable through the public MCP surface. This is a host-enforced approval boundary; the service API does not independently attest that a human saw a UI prompt. |
| Replay and interrupted writes | A submission is durably marked before the remote effect. Reusing its approval returns its existing state without executing it again. Uncertain outcomes do not trigger automatic resubmission. The probes found no repeated SMTP delivery, unsubscribe POST, APPEND or deletion from replaying the same operation. |
| Approved content versus delivery | The wire/envelope checks bind the composed message to approval. Altering sender, recipients, subject, Bcc or envelope recipients refused. Bcc did not appear in transmitted message headers. |
| Free actions | Attempts to file into Trash or its descendants, move/copy from protected Drafts, inject deletion flags, or rename protected folders refused. Reads did not mutate messages. No inspected free action intentionally sends mail or deletes it. |
| Deletion scope | Message deletion uses exact references and UID-scoped expunge. Folder deletion requires the qualified nonempty-folder refusal guard. I found no broad expunge/CLOSE path substituted for the approved deletion. |
| Credentials and untrusted content | Credentials stay in private service storage and transport paths. Synthetic credential-bearing server errors were suppressed/redacted. Mail-derived content remains escaped and marked untrusted, including repeated notices and derived content. |
| Inputs and least access | Typed schemas, strict JSON decoding, size/depth limits, exact references, path restrictions and no-overwrite publication remain enforced. TLS precedes credential authentication. Unsubscribe does not follow redirects or accept arbitrary caller-authored request bodies. |
| System operator | I found no Mail tool path to package installation, shell execution, service configuration, disks, boot settings or execution of downloaded attachments. Local publication remains constrained to allowed files and directories. |

The 19b production changes add mutation context to existing durable records and check source UIDVALIDITY on the RENAME connection. I found no approval or replay regression from those changes. Production `warnings.py` and `paging.py` are unchanged in the requested diff.

**Judgment on every listed re-scope limit**

These judgments apply to the documented behavior at this head, with database recovery beyond no-double-send excluded as requested.

| Listed limit | Judgment and reason |
|---|---|
| Shared committed-record read path / durable owner-state projection absent | **Low harm; accept.** Some disclosures can disappear after failure or restart. This does not itself restore executable approval or replay a remote operation. |
| SQLite-read fallback, persistent exhaustion and failed rollback | **Low harm; accept within scope.** Views can become unavailable or incomplete. Failed storage does not authorize another delivery. |
| Restore reconciliation of free-change checks, warnings and acknowledgements | **Low harm; accept.** Warnings may disappear or return. Earlier-generation approvals remain invalidated. |
| General warning lifecycle across checks, acknowledgement, archive, expiry and restart | **Low harm; accept.** Stale, duplicate or incomplete notices are possible. They do not authorize cleanup or additional remote mutation. |
| Current refusal recomputation / `G22-latch` | **Low harm; accept.** Reproduced a zero-byte ENOSPC leaving subsequent healthy writes refused until simulated restart. This is an availability failure, not an unsafe retry. |
| `G22-rename` | **Low harm under the accepted filing-race policy; accept.** Reproduced the generic “unverified role” result when Target was Trash and Drafts unresolved. The action remains partial and directs inspection; the lost detail does not introduce another move or deletion. |
| `G22-evidence` | **Low harm; accept.** Reproduced loss of transient Trash evidence after a refused result write and subsequent role change. The recovery checks performed zero remote mutations. |
| First-write full-disk background warning | **Low harm; accept.** A diagnostic can disappear when no warning bytes persisted. This is not lost submission fencing. |
| Open evidence checks and failed result writes | **Low harm; accept.** Inspection state or evidence may be incomplete after exhaustion/restart. Recovery does not replay the original mutation to reconstruct it. |
| Admission/holds, unfinished export publication, rollback/manifests and ordinary disclosures | **Low harm; accept.** Views may disagree about unfinished local work. File confinement and no-overwrite behavior remain separate enforcement. |
| Qualification/protected roles and legacy context-free unfinished work | **Low harm; accept.** Historical warnings can lack context or require another check. Current role protection and account qualification still gate mutations. |
| Point-zero attachment export, export rollback and test-app export | **Low harm; accept.** Missing publication notices concern constrained local copies; no execution or overwrite bypass was established. |
| Point-zero cancellation and expiry | **Low harm; accept.** Passive views can omit the notice, but cancelled/expired work is not thereby executable. |
| Point-zero rename | **Incorrectly characterized.** The escaped-role oracle bug above explains the reproduced “ordinary” claim. Correct the oracle and report; it is not an additional production security defect. |
| Point-zero failed password publication | **Low harm; accept.** Incomplete setup can leave a private password-publication intent undisclosed. I found no resulting credential return, logging channel or public administrative capability. |
| Point-zero restore | **Low harm within the dropped stage-3 scope; accept.** Passive history may be incomplete. That does not imply old approval generations become usable. |
| Point-zero settlement | **Low harm; accept.** Public duplicate-copy warning stage can differ from the saved parent stage. It does not cause another recipient delivery. |
| Installed test-app passive cursor | **Low harm; accept.** Continuation can restart or change scope. The test app is not exposed as an installed Mail MCP capability, and this does not grant a mutation. |

I also accept the previously settled limits, with these precise boundaries:

- **Late Sent APPEND:** after the 15-minute quiet period, an explicit new repair can create a second identical Sent copy if the first appears late. I reproduced this with one SMTP delivery and two identical Sent copies. Therefore, an absolute “never two APPENDs across separate repair attempts” guarantee would be inaccurate. This is the documented, low-harm owner-accepted exception; replay of the same operation must still remain inert.
- **Filing-role races:** the owner explicitly accepted leaving messages/folders where a move, copy or rename placed them, without automatic rollback or deletion. A role that changes and changes back between checks can escape detection.
- **Empty-folder replacement race:** the approved empty name can refer to a replacement empty folder at deletion time. Acceptance depends on the server’s nonempty-folder guard actually being qualified.
- **Local attachments:** approval displays metadata and hash, not attachment text. Claude-written text in an ordinary local attachment is accepted behavior.
- **Draft retention and conservative refusals:** retained revisions and rejected oversized/unsupported content are usability limits, not permission bypasses.

**Evidence run**

The repository tests executed were:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests \
.work/venv/bin/python -B -m unittest \
test_ingress_bounds.IngressBounds.test_strict_and_error_classification_decoders_share_all_bounds \
test_ingress_bounds.IngressBounds.test_socket_raw_bounds_refuse_before_engine_dispatch \
test_ingress_bounds.IngressBounds.test_cli_raw_bounds_refuse_before_proxy_or_admin_password_prompt \
test_ingress_bounds.IngressBounds.test_hook_raw_bounds_refuse_before_pending_read \
test_ingress_bounds.IngressBounds.test_hook_explicit_payload_schema_refuses_wrong_types_and_unknown_fields \
test_owner_state_fixes_s2
```

Result: **31 tests, OK**.

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests \
.work/venv/bin/python -B -m unittest test_dkim
```

Result: **2 tests, OK**.

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests \
.work/venv/bin/python -B -m unittest test_mail_ci_selection
```

Result: **6 tests, OK**.

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control \
.work/venv/bin/python -B control/generate.py --check
```

Result: **“Generated artifacts match definitions.”**

Additional in-memory probes exercised production engine, adapter and storage methods with synthetic transports:

- **60** altered-approval refusals across the five asking paths.
- **208** checkpoint interruptions and **234** zero-byte, short-write or ENOSPC journal faults, checking recovery/replay for repeated remote effects.
- **21** interrupted repair cases.
- **11** mutation-context write refusals, verifying the corresponding remote command did not run.
- **20** forbidden free-action cases, **52** managed-policy alterations and **13** unsafe file-path/name cases.
- Credential-error redaction, exact approval-size boundaries, MIME/header binding, untrusted read behavior, and the named `G22` reproductions.

These used in-memory SQLite/journals and simulated recovery. They are **not evidence of actual process crashes, filesystem durability, live-provider behavior or terminal/phone prompt rendering**. I did not run containers, the complete filesystem fault suites, or fresh required CI runs.

**Other observations**

The review-22 pagination-description issue is corrected: the description now distinguishes `page_changed` from invalid-cursor `stale_reference`. The earlier review-20/21 protections remain represented in the implementation and retained regressions.

`git diff --check` reported trailing whitespace in historical review Markdown and the saved stage-3 patch; no security consequence. No files over 500 MB were found under `.work/`. An untracked `reviews/19b-owner-state/REVIEW-FINAL.md` appeared during the review; I did not create, read or modify it.

SAFE