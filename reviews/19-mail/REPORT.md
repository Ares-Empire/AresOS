# 19 — Mail tools

Builds on draft PR #6. No merge, force push, real account or model run.

## Done

- **read — implementation:** `control/aresos_control/mail/` contains the catalogue,
  MIME/HTML/Markdown codec, verifying TLS transports, owner onboarding, DKIM gate and
  shared `Adapter` implementation. All design §5 actions are present, with base-style
  preparation, cancel and notice actions. MCP, CLI help, tool reference and ask rules
  are generated from these definitions. The draft managed MCP file includes `mail`.
- **read — base changes:** `Engine` registers Mail, routes private admin password
  onboarding and sanitizes transport failures. The proxy adds only Mail's caller-side
  path import/save plumbing; CLI reads setup passwords from the terminal. The common
  public outcome schema now includes design's `refused`. Compact restore descriptions
  retain folder and unsubscribe targets. The base operation/approval/file contracts
  are otherwise reused. No lock or new runtime package was added: RFC 8058 verification
  uses already pinned `cryptography` **50.0.2**, because stdlib cannot verify DKIM keys.
- **read — tests:** `control/mail_tests/` covers synthetic real-server reads, writes,
  MIME, sending, stages, files, onboarding, TLS, explicit guard qualification and
  kill-9/restore recovery. `.github/workflows/control-mail.yml` runs the base suite
  plus these tests. `control/README.md` documents setup, recovery and concrete limits.

## Feature → tool → test

Tests below are in `control/mail_tests`; short class/method names are exact. All use
Dovecot IMAP and GreenMail SMTP unless a different fixture is stated.

| Mail *first* feature | Tool(s) | Test(s) |
| --- | --- | --- |
| Accounts, addresses, capabilities, special folders | `mail_accounts` | `Reading.test_multiple_accounts_contacts_and_special_use_names`; `AccountAdmin.test_owner_only_admin_setup_tls_special_use_private_password_and_sent_confirmation` |
| Folders and counts | `mail_folders` | `Reading.test_multiple_accounts_contacts_and_special_use_names`; `test_every_read_action_preserves_flags` |
| Create/rename folders | `mail_folder_create`, `mail_folder_rename` | `Changes.test_move_copy_flags_junk_folder_create_rename` |
| Delete empty leaf, conditional on safe server | `mail_prepare_folder_delete`, `mail_folder_delete` | `Changes.test_greenmail_nonempty_guard_and_delivery_during_folder_approval` (explicit guarded GreenMail); `test_both_upstream_servers_allow_nonempty_delete_and_are_not_qualified` (both upstreams) |
| Search sender/recipient/subject/text/dates/flags/attachments | `mail_search` | `Reading.test_filters_and_large_folder_cursors_bind_full_state_and_query`; `test_no_condstore_or_qresync_fallback_rereads_flags_and_references` |
| Read headers/body/HTML/attachment list | `mail_read` | `Reading.test_html_plain_non_utf8_calendar_and_nested_forward_fixtures`; `test_every_read_action_preserves_flags` |
| Raw source | `mail_read part=source` | `Reading.test_long_body_source_and_parts_are_paged_and_state_bound`; `CallerTransfers.test_real_proxy_caller_import_save_permissions_immutable_bytes_and_full_cli_flow` |
| Conversation across folders | `mail_thread` | `Reading.test_thread_across_folders_missing_duplicate_ids_no_subject_guess` |
| Save attachment / whole mail | `mail_attachment_save` | `CallerTransfers.test_real_proxy_caller_import_save_permissions_immutable_bytes_and_full_cli_flow` (real sockets, distinct Linux uids, actual file policy) |
| New/reply/reply-all/forward inline/attached | `mail_compose`, `mail_prepare_send`, `mail_send` | `Composing.test_new_send_exactly_once_bcc_bytes_encoding_sent_and_no_receipts`; `test_reply_to_list_aliases_threading_own_sent_and_answered`; `test_forward_inline_and_as_attachment_preserve_original_bytes` |
| Plain/formatted mail | `mail_compose` | `Composing.test_formatted_defaults_signature_no_raw_html_and_invalid_links` |
| Signature and default habit | `mail_compose` from owner config | Same test; owner settings covered by `AccountAdmin.test_owner_only_admin_setup_tls_special_use_private_password_and_sent_confirmation` |
| Local / other-mail attachments | `mail_compose` | `CallerTransfers.test_real_proxy_caller_import_save_permissions_immutable_bytes_and_full_cli_flow`; `Composing.test_new_send_exactly_once_bcc_bytes_encoding_sent_and_no_receipts` |
| Save/edit/delete/send draft | `mail_draft_save`, `mail_compose mode=draft`, send/delete pairs | `Composing.test_save_edit_send_and_delete_draft_with_explicit_approval` |
| Move/copy | `mail_move`, `mail_copy` | `Changes.test_move_copy_flags_junk_folder_create_rename` |
| Read/unread/flag/answered/custom keyword | `mail_flag` | Same test; `Reading.test_filters_and_large_folder_cursors_bind_full_state_and_query` |
| Trash/permanent/empty Trash (named pages) | `mail_prepare_delete`, `mail_delete` | `Changes.test_trash_and_permanent_only_named_uids_others_deleted_survive`; `test_delete_without_uidplus_refused_and_all_items_checked_before_any` |
| Junk/not junk | `mail_move` | `Changes.test_move_copy_flags_junk_folder_create_rename` |
| Send status / repair | `mail_operation_status`, `mail_operation_repair` | `Outcomes.test_failure_at_each_later_stage_repairs_without_smtp`; `test_dropped_final_answer_is_unknown_and_never_retried` (scripted TLS SMTP + Dovecot) |
| Header unsubscribe | `mail_prepare_unsubscribe`, `mail_unsubscribe` | `Unsubscribe.test_header_mailto_exact_address_body_and_approval`; `test_https_one_click_post_exact_no_cookies_no_redirect_no_get` (scripted SMTP/HTTPS + Dovecot); both `DKIM` tests |
| Several accounts | account configuration / all tools | `Reading.test_multiple_accounts_contacts_and_special_use_names` |
| Contacts from history | `mail_contacts` | Same test |
| Read calendar invitation (answering deferred) | `mail_read` | `Reading.test_html_plain_non_utf8_calendar_and_nested_forward_fixtures` |

Owner rows are excluded from feature acceptance, except the explicit onboarding
requirement. CardDAV, calendar responses, scheduled sends, notices, filters, PDF and
read receipts were not added. Normal reads never send receipts.

## Tool descriptions for Claude

**read:** the exact generated [reference](../../docs/control/TOOLS.md) and
[Mail MCP tool list](../../control/generated/mail-tools.json) contain every description,
input and result schema. No hand-written duplicate list is maintained. Descriptions
state effects, PEEK/no receipt behavior, exact approval transfer, immutable sources,
per-recipient/stage outcomes, stale/error recovery and no retries. Mail-derived data
remain explicitly untrusted when repeated in composition/approval descriptions.

**assumed / tool-user review:** the extra preparation call, `operation_id` versus the
design's `request_id`, omitting `text` to keep a draft body, literal backslash IMAP
flags, thread summaries followed by individual reads, and path/blob/MIME-part attachment
alternatives are the parts most likely to need wording changes after fresh Claude use.
They have protocol tests; their usability has not been measured with a model.

## Design §5 fixtures and checks

| Required fixture/check | Exact evidence test |
| --- | --- |
| Thread with archived part; missing/duplicate ids | `Reading.test_thread_across_folders_missing_duplicate_ids_no_subject_guess` |
| List Reply-To, own sent reply, aliases, threading headers | `Composing.test_reply_to_list_aliases_threading_own_sent_and_answered` |
| HTML/plain, nested forwarded mail, non-UTF-8 | `Reading.test_html_plain_non_utf8_calendar_and_nested_forward_fixtures` |
| PDF/image/program-like/non-ASCII attachment names | `Composing.test_new_send_exactly_once_bcc_bytes_encoding_sent_and_no_receipts`; `CallerTransfers.test_real_proxy_caller_import_save_permissions_immutable_bytes_and_full_cli_flow` |
| Large folder cursor/query invalidation | `Reading.test_filters_and_large_folder_cursors_bind_full_state_and_query` (240 items, twelve pages); production scan bound documented below |
| Folder recreated with new UIDVALIDITY | `Reading.test_stale_uidvalidity_after_folder_recreated_never_hits_replacement` |
| Every read leaves flags unchanged | `Reading.test_every_read_action_preserves_flags` (accounts/folders/search/read body/source/part/thread/contacts/status; compares full flags) |
| Exactly one arrival, recipients, no Bcc, exact bytes, Sent, answered | `Composing.test_new_send_exactly_once_bcc_bytes_encoding_sent_and_no_receipts`; `test_reply_to_list_aliases_threading_own_sent_and_answered` |
| Client saves Sent / server saves Sent | New-send test (client); `Outcomes.test_server_saves_sent_client_never_appends_duplicate` (scripted SMTP server saves into real Dovecot) |
| Refused recipient is partial | `Outcomes.test_refused_recipient_is_partial_not_done_and_replay_does_not_submit` |
| Failure at each later stage; repair without SMTP | `Outcomes.test_failure_at_each_later_stage_repairs_without_smtp` (Sent, answered; pre-stage injection, real protocol repair) |
| Dropped final SMTP answer is unknown | `Outcomes.test_dropped_final_answer_is_unknown_and_never_retried` |
| Send/delete crash at every log write; never repeat | `MailCrashes.test_kill_every_send_log_write_and_every_remote_stage_never_sends_twice`; `test_kill_every_delete_log_write_and_each_uid_stage_preserves_unnamed` |
| Trash MOVE / answered flag remote boundaries | `MailCrashes.test_trash_move_and_answered_flag_crashes_never_repeat_remote_work` |
| Reservation / every repair log write | `MailCrashes.test_reservation_and_every_repair_write_crashes_never_submit_again` |
| Restore remains locked until owner confirms; old ids refused | `MailCrashes.test_restore_older_sqlite_keeps_lock_until_owner_confirms_and_rejects_old_approval`; whole base crash/restore suite |
| Changed composition/attachment refused | `Composing.test_composition_and_attachment_corruption_refused`; real caller source replacement in `CallerTransfers` |
| Moving to Trash not free | `Changes.test_move_copy_flags_junk_folder_create_rename` (move and copy refused) |
| Explicit per-item refusal is partial; remaining targets untouched | `Changes.test_explicit_per_item_refusal_reports_partial_and_does_not_touch_later_targets` |
| Mandatory STARTTLS, no password before verification / no plaintext fallback | `Outcomes.test_required_starttls_success_and_no_plaintext_auth_fallback` |
| Astral Unicode body fits serialized result cap | `Reading.test_astral_unicode_body_pages_fit_the_actual_result_byte_cap` |
| New mail during folder approval / final boundary | `Changes.test_greenmail_nonempty_guard_and_delivery_during_folder_approval` (test-only guard; upstream gap below) |
| Unnamed Deleted survives / no CLOSE | `Changes.test_trash_and_permanent_only_named_uids_others_deleted_survive`; `test_unsafe_folder_delete_refused_subfolders_and_close_never_called` |
| Certificate mismatch before password | `Outcomes.test_tls_hostname_or_untrusted_certificate_fails_before_password_sent` (actual IMAP and scripted SMTP TLS; password access assertion, no AUTH received) |
| Long quote, Bcc, attachments, odd characters, 16 KiB/no truncation | `Composing.test_long_quotes_by_reference_and_asking_size_never_cut_escaped`; `Changes.test_delete_prompt_metadata_escaped_bounded_and_cannot_be_forged` |
| Encoded mail above per-file cap; summaries/header-only history work | `Composing.test_large_encoded_mail_keeps_per_attachment_cap_and_search_retains_only_summaries` |
| Encoded words/names, CRLF, decoded hashes, SMTPUTF8/IDNA | `Composing.test_new_send_exactly_once_bcc_bytes_encoding_sent_and_no_receipts`; `test_smtputf8_refused_and_idna_domains_converted` |
| Generated catalogue/settings in sync; base intact | `python3 control/generate.py --check`; all 57 original base tests unchanged |

## Verified

**run — product head `9f4dbbd5dc7664e2f5696432fff3e3cc770c1933`:** both
[42361618095](https://github.com/Ares-Empire/AresOS/actions/runs/42361618095)
(push) and [42361622331](https://github.com/Ares-Empire/AresOS/actions/runs/42361622331)
(PR) succeeded. Each executes `bash control/ci/mail/run.sh`, which runs:

```sh
docker exec mail-tests bash control/ci/test.sh
# after disconnecting external bridge and connecting only the internal fixture network:
docker exec -e PYTHONPATH=/workspace/control:/usr/lib/aresos-control/vendor -e PYTHONDONTWRITEBYTECODE=1 -e MAIL_CERT_DIR=/workspace/.work/mail-ci/certs mail-tests python3 control/ci/mail/ready.py
docker exec -e PYTHONPATH=/workspace/control:/usr/lib/aresos-control/vendor -e PYTHONDONTWRITEBYTECODE=1 -e MAIL_CERT_DIR=/workspace/.work/mail-ci/certs mail-tests python3 -m unittest discover -s control/mail_tests -v
```

The full Docker invocations, synthetic TLS generation, cleanup and pinned images are
in `control/ci/mail/run.sh`; the workflow's artifacts retain exact base/Mail output
and upstream logs. Important output, verbatim:

| Output | Push run 42361618095 | PR run 42361622331 |
| --- | --- | --- |
| Runtime | `Python 3.15.0`; `Fedora release 45 (Forty Five)` | same |
| Catalogue | `Generated artifacts match definitions` | same |
| Existing base | `Ran 57 tests in 40.250s`; `OK`; `Control base suite PASS` | `Ran 57 tests in 58.490s`; `OK`; `Control base suite PASS` |
| Mail | `Ran 48 tests in 72.040s`; `OK`; `Control Mail suite PASS` | `Ran 48 tests in 85.174s`; `OK`; `Control Mail suite PASS` |
| Send crashes | `Mail send kill-9 cases: 45; no repeated SMTP DATA` | same |
| Delete crashes | `Mail delete kill-9 cases: 26; unnamed Deleted messages survive` | same |
| Reservation/repair crashes | `Mail reservation/repair kill-9 cases: 16; no SMTP during repair/restart` | same |

**run:** two additional remote boundary kills (Trash MOVE and answered flag) passed
in their named test, making **89 Mail kill-9 cases** per full Mail suite. Every
required check in the tables above passed in both runs. The independent existing
base workflow [42361622291](https://github.com/Ares-Empire/AresOS/actions/runs/42361622291)
also succeeded on this head. No original base tests were changed, skipped or deleted.
No failing assertion was weakened: invalid fixture assumptions/setup were corrected,
and implementation/schema defects were fixed.

**read — server versions:** GreenMail **2.1.15**, manifest
`sha256:309ba544ea482e5d4265d09921cdab07c8dad2cc4481d715c9b8ff5d3f0a149f`;
Dovecot **2.3.21.1**, manifest
`sha256:547d28f9a893c93a1d2f6dc164880cd7bfa74009106dfa46b36a6a2ee636d921`;
Fedora **45 x86_64**, manifest
`sha256:79dd6556b8fe1a559051fad5159d4987ead218f1914e7a5bd20350d9ea0f9e52`.
Digests were resolved from the registry before pinning. Dovecot supplies real
SPECIAL-USE/UIDPLUS/MOVE, GreenMail supplies real SMTP delivery and independent
recipient mailboxes. Failures use a non-relaying scripted TLS SMTP server with a
SQLite arrival log that does not deduplicate. The guarded IMAP frontend is separately
identified in PLAN-GAP; it is not represented as upstream server behavior.

**run — earlier iterations, all retained for audit:**

| Workflow ids | Result and correction |
| --- | --- |
| [42359465452](https://github.com/Ares-Empire/AresOS/actions/runs/42359465452) | Initial 57 base + 15 Mail tests passed. |
| [42359769672](https://github.com/Ares-Empire/AresOS/actions/runs/42359769672) | `Ran 30 tests`; `FAILED (failures=1)`: upstream GreenMail accepted nonempty DELETE. Added an explicit guard fixture and real upstream refusal-of-qualification checks; retained the positive guard assertion. |
| [42360229227](https://github.com/Ares-Empire/AresOS/actions/runs/42360229227) | `Ran 36 tests`; `FAILED (errors=1)`: base schema omitted `refused`. Extended the schema to the design's outcome. |
| [42360489687](https://github.com/Ares-Empire/AresOS/actions/runs/42360489687) | `Ran 41 tests`; `FAILED (errors=39)`: capability bytes broke stdlib ENABLE. Restored stdlib string capability types and consistent checks. |
| [42360763279](https://github.com/Ares-Empire/AresOS/actions/runs/42360763279), [42360879730](https://github.com/Ares-Empire/AresOS/actions/runs/42360879730) | `Ran 43 tests` / `Ran 44 tests`; both `FAILED (failures=2)`: reservation fixture created an unrelated earlier reservation invalidated by restore, and the distinct-user daemon lacked a writable socket directory. Removed the unrelated fixture reservation and pre-created the service-owned directory; assertions preserved. |
| [42361010616](https://github.com/Ares-Empire/AresOS/actions/runs/42361010616) | All 57 base + 44 Mail tests passed. |
| [42361308196](https://github.com/Ares-Empire/AresOS/actions/runs/42361308196) | All 57 base + 46 Mail tests passed, including partial targets and STARTTLS. |
| [42361409975](https://github.com/Ares-Empire/AresOS/actions/runs/42361409975), [42361466528](https://github.com/Ares-Empire/AresOS/actions/runs/42361466528) | Both 57 base + 47 Mail tests passed, including 240-item paging and Unicode byte bounds. |

**run — local read-only checks:** `python3 control/generate.py --check` printed
`Generated artifacts match definitions`; AST parsing every `control/**/*.py` printed
`Python syntax OK`; `git diff --check` printed nothing. The scope check printed no
changes under `os/`, `mod/`, the excluded owner/install files, or `control/tests/`.
The worktree size scan printed `Remaining .work files over 500 MB: []`.
All pushes used normal verification, no `--no-verify` or force push.
Local Docker was unavailable; no container/build installation was attempted on this Mac.

The report-inclusive commit additionally clarifies untrusted-data wording in the
generated descriptions and asserts actual Docker internal-network/no-published-port
configuration before Mail tests. It changes no Mail transport/operation code. Its
**two completed Mail workflow executions and exact final head** are recorded in
[draft PR #9](https://github.com/Ares-Empire/AresOS/pull/9)'s validation section after
this commit is pushed, avoiding an endless report/head update cycle. Both final
executions include the whole base suite; the independent base workflow also runs.
Fourteen workflow executions preceded this final report push; the final push adds
three (push Mail, PR Mail, PR base), within the brief's approximate twenty-run budget.

## JUDGMENT-CALL

- **read — draft updates:** new revisions retain old drafts, and sending retains the
  source draft. Silent replacement/removal would be a delete through a change tool.
  Exact old-draft deletion asks separately. Replacing in one free call was rejected;
  changing this later needs an explicitly approved deletion operation.
- **read — asking shape:** reuse brief 18's `{operation_id, description}` envelope
  instead of a second incompatible root schema. `operation_id` is design's service-
  issued `request_id`; description repeats the composition id/hash and all approval
  facts. Preparation is a separate change action. Altering any displayed field is
  refused. Changing the shape later affects both base callers and managed ask tests.
- **read — Sent detection:** missing evidence in a bounded window cannot prove the
  server will never save a delayed copy. Negative probes leave onboarding unready
  until owner-only `account_settings` confirms client/server policy. No probe retries.
  The alternative was silently treating absence as proof. Owner confirmation is a
  one-time setup cost; later automatic detection needs a provider-qualified bound.
- **read — repairs:** require the durable final DATA acceptance before repairing a
  local stage. A Sent copy alone does not identify all accepted/refused recipients.
  Unknown without that proof remains for owner inspection; no new SMTP path exists
  in repair. Relaxing this requires qualified per-recipient server evidence.
- **read — exact forward bytes:** forwarded `.eml` files use explicit octet-stream
  attachment MIME while preserving the original bytes/hash. Re-parsing as nested
  `message/rfc822` could alter folding/bytes. Most clients open `.eml` by its filename;
  specialized presentation remains an owner qualification item.
- **read — bounds:** 25 MiB per transferred file, 64 MiB per encoded source/outgoing mail,
  6,000-character body pages, 20 summary items/page maximum and a 10,000-message full
  history scan bound. Search retains summaries rather than all fetched bodies;
  contact/thread indexing uses headers only. The first implementation deliberately rereads authoritative
  state even with synchronization extensions. A durable incremental history index
  and large-account tuning are follow-up work; unbounded memory/time was rejected.

## PLAN-GAP

- **run/read — positive folder guard:** GreenMail 2.1.15's store rejects nonempty
  deletion, but its IMAP host first removes the messages. Dovecot 2.3.21.1 also allows
  nonempty deletion. Both are truthfully left unqualified by onboarding. The positive
  race check uses an explicit test-only serialized IMAP frontend over real GreenMail:
  STATUS+DELETE and all frontend writers share one command lock. It covers adapter
  behavior, not an upstream feature or the real provider's atomicity. No production
  shim was added. A genuinely qualifying provider remains an owner onboarding gate;
  elsewhere the owner deletes empty folders in his mail program, as design requires.
- **read — updates versus delete approval:** design calls replacing drafts a change
  while also requiring every deletion to ask. This implementation keeps both
  revisions until a separate named delete, as described above.
- **read — aggregation and performance:** the brief gives a per-file cap but no whole
  encoded-mail/history-work cap. The explicit limits above avoid unbounded service
  memory/work. Accounts beyond the scan bound need smaller selected folders or later
  incremental indexing; only the stated synthetic folder size is claimed tested.

## Protocol references read

**read — 2026-11-07:** official Python
[imaplib](https://docs.python.org/3/library/imaplib.html) and
[smtplib](https://docs.python.org/3/library/smtplib.html) contracts; IMAP
[RFC 9051](https://www.rfc-editor.org/rfc/rfc9051.html); one-click
[RFC 8058 §§3–4](https://www.rfc-editor.org/rfc/rfc8058.html#section-3.2) and DKIM
[RFC 6376](https://www.rfc-editor.org/rfc/rfc6376.html). These informed PEEK/UID use,
explicit verifying contexts, SMTP answer handling, consent/no-context POST and the
DKIM coverage check. Executed compatibility is the pinned Python/server versions
above, rather than an assumption about all versions or providers.

## Not verified / open questions

- **assumed / owner gate:** the real account's aliases, TLS roots, authentication,
  special roles, delayed Sent behavior and server-enforced folder guard; no endpoint
  or provider details were used. No real delivery, account or inbox was accessed.
- **assumed / owner gate:** real mail-client presentation of formatted mail/attached
  `.eml`, terminal/phone approval rendering and the seven fresh Claude tool-user
  rounds. No model or Claude Code ran in CI. The fixed test workflows prove protocol
  behavior, not a usability/model judgment or deployment boundary qualification.
- **read / unrun:** public DNS DKIM interoperability, physical power loss and storage
  controller durability. DKIM tests use independently signed synthetic mail and TXT
  fixtures; unknown/unsupported signatures refuse POST. The base's existing image,
  sandbox and backup integration gates remain.
- No mid-run answer requested. Final workflow ids for the report-inclusive head are
  recorded in the draft PR validation section after the final push, so this report
  need not be changed after the final head passes twice.
