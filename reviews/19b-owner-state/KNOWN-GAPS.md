# Stage 1 known gaps

The list starts with Mail review 22's three blocking cases. They remain failures in production; stage 1 exposes them without changing their assertions.

| Named assertion | Matrix row | Closing stage | Expected / observed |
| --- | --- | --- | --- |
| `G22-rename/assertion` | M03/C03 | 3 | LIST observed Trash at the renamed target while Drafts was unresolved; the response instead says unverified. |
| `G22-evidence/assertion` | M03/C03 | 3 | A refused recovery-result write must retain the observed Trash occurrence after remote evidence changes; the later catalogue omits it. |
| `G22-latch/assertion` | M08/M10/M13 | 3 | A zero-byte ENOSPC with successful cleanup must allow a healthy next write; it still returns storage_limit. |

`KNOWN-GAPS.json` is the executable list. Format 2 groups identical `{row, stage, delta}` values for storage only. Every `cases` entry is one exact assertion key: flow/mode/fault/cleanup/phase/view (or a focused/named contract). `delta.calls` fixes the number of comparisons; each failure fixes its missing and extra facts and every page number. There are no wildcards, skipped tests or accepted exception types. Exact aliasing hides only opaque random IDs; identities and occurrence distinctions remain compared.

A pass for a listed assertion fails with `Unexpected pass`; a changed delta, unlisted failure, omitted per-case view or unexecuted suite entry also fails. A base self-test checks every ledger key has an executed suite owner and valid nonempty failure pages. Setup, positive triggers, mutation attempts during reads, corrupt exports and nonadvancing cursors remain hard assertions outside the ledger.

The data was collected from Linux diagnostic run [42613046233](https://github.com/Ares-Empire/AresOS/actions/runs/42613046233), all four sweep artifacts (two isolated workers each) plus the focused/named suite, and the installed-channel case in base run [42613046019](https://github.com/Ares-Empire/AresOS/actions/runs/42613046019). Diagnostics capture failures; the subsequent strict runs in REPORT.md verify this pinned list. HTTPS POST context failures are explicitly assigned M04.

There are **675,775 assertion-specific failures**, stored in **1,559 exact delta groups**: **44,856 for stage 2**, **630,919 for stage 3**. These counts include repeated fault sites and independent public views; they are not counts of distinct root causes.

Stage 2 failures concern exact context committed before each attempted mutation. Stage 3 failures concern disclosure from durable records during SQLite failure, current holds/generation/refusals, retained evidence and warning lifecycle, and each view's own continuation. The list deliberately stays nonempty at this stopping point. Stages 2 and 3 must remove entries as their exact assertions begin passing.

| Flow / suite owner | Stage 2 assertions | Stage 3 assertions |
| --- | ---: | ---: |
| `G22-rename` | 0 | 1 |
| `G22-evidence` | 0 | 1 |
| `G22-latch` | 0 | 1 |
| `send` | 4,865 | 59,495 |
| `repair` | 1,908 | 33,922 |
| `delete_trash` | 1,879 | 16,551 |
| `delete_permanent` | 3,131 | 25,421 |
| `unsubscribe_mailto` | 5,202 | 61,716 |
| `unsubscribe_https` | 1,253 | 20,986 |
| `status` | 0 | 8,141 |
| `settlement` | 0 | 14,013 |
| `cancel` | 0 | 1,922 |
| `restore` | 0 | 7,518 |
| `attachment_export` | 0 | 34,630 |
| `testapp_export` | 0 | 8,291 |
| `password` | 1 | 1,504 |
| `filing_move` | 0 | 28,942 |
| `filing_copy` | 0 | 28,942 |
| `filing_rename` | 1,134 | 14,812 |
| `expiry` | 0 | 4,396 |
| `maintenance` | 0 | 2,914 |
| `restart_index` | 0 | 0 |
| `restart_tail` | 0 | 0 |
| `export_rollback` | 0 | 37,356 |
| `archive` | 0 | 13,201 |
| `draft_append` | 629 | 5,621 |
| `folder_create` | 594 | 5,364 |
| `folder_delete` | 1,234 | 12,041 |
| `onboarding` | 19,883 | 125,135 |
| `flag` | 594 | 5,364 |
| `settings` | 924 | 8,792 |
| `folder_review` | 889 | 8,792 |
| `testapp_send` | 0 | 18,116 |
| `testapp_delete` | 0 | 12,673 |
| `testapp_config` | 721 | 4,248 |
| `contract` | 15 | 95 |
| `channel` | 0 | 2 |

Every key names its matrix row and closing stage in JSON. COVERAGE.md maps every row to its executable cases, including rows whose focused cases currently pass. No production gap is claimed closed in stage 1.
