# Chrome read: harness map

**read:** Map of [brief 28's tests](../../briefs/28-chrome-read.md#tests), including every handoff in
[PROGRESS.md](PROGRESS.md). **run:** final run/attempt results are in [REPORT.md](REPORT.md#verified).
A source mapping alone is not a passing execution. Tests use synthetic fixtures and disposable hosted
profiles; no owner profile or real account was exercised.

## Fix round X1 regression coverage

These additions run in the existing full Node/Python suites; no browser verdict name, group or previous
assertion is removed. The DOM-double helper moved from `outline.test.mjs` to `outline-dom.mjs`, preserving
its existing tests. `x1_service_probe.py` passes the actual reader replies/state through `Engine.request`;
it does not synthesize the expected withholding or state digest. Baseline results are in REPORT.

| Requirement | New regression | Execution |
|---|---|---|
| Presentation roles cannot bypass native withholding; outline/full/find and typed count | `fix-x1.test.mjs:14`, 12 combinations of both roles, three histories, and history/credential protection; all typed kinds plus protected nontext controls/select/button/editor | full Node + Python service probe |
| Legacy `role=generic` cannot use native child text as its name | `reader.test.mjs:929`, textarea first, then six typed input kinds; throwing getter, no marker, filled/asking metadata retained | full Node |
| File names and selected options affect token/wait/cursor | `fix-x1.test.mjs:41`, six separate tests; constant selected-state mutation fails all three selection tests | full Node + Python service probe |
| Slash position and later question marks never disable credential filtering; route preservation | `test_fix_x1.Addresses`, `:17` and `:41`; independent brief word list, review examples and sign-in-route regression | Python partition |
| Every failed call retains at most 5,000 references | `test_fix_x1.Adapter.test_failing_reads_keep_6000_control_reference_table_bounded:60`; actual Engine.request; three repetitions of oversized header, stale cursor, wrong query and failed measurement | Python partition |
| Page/form full gets F4's 200 options, paging, deadline, subtree scope | `test_fix_x1.py:116`, `:119`, `:122`, `:141` | Python partition |
| 10,000-character option uses ordinary cut and whole-label reference route | `test_fix_x1.py:160` | Python partition |
| Brief-exact cursor sentence | `test_view_paging.py:121`, `test_view_references.py:205`; only expected wording changes | Python partition |

The inherited form-refusal sentence remains because main's shared-path tests pin it; REPORT records the
explicit specification exception. Nine named asking-path functions and two dispatch branches compare unchanged.
The above tests add no claims about owner-profile behavior or new mandatory browser verdict cases.

## Verdict and execution inventory

[verdicts.mjs](../../control/chrome/ci/verdicts.mjs#L3) is the exact named inventory: `REQUIRED[1..11,13]`, `SUPPORT`,
`ADAPTER_REQUIRED`, `verdicts` and `assertComplete`. Group 12 comes from `precedenceVerdict`, not a new
browser group. Each registered browser name must appear exactly once and pass; an omitted, duplicated,
unknown or failing name fails completeness. `verdicts.test.mjs` independently spells out the support names
and source inventory. [shards.mjs](../../control/chrome/ci/shards.mjs#L12)'s `caseInventories` identifies each case's source and nine browser shards;
`shards.test.mjs`, `site-results.test.mjs` and `qualification-completion.test.mjs` prevent incomplete evidence
from qualifying. `merge-shards.mjs` requires all nine shards. No group or record format was added for 28.

- New password cases join `REQUIRED[7]` → `password_exclusion`.
- The unread-form case joins `REQUIRED[3]` → `binding`.
- Every `READ BRIEF28 ...` name below joins `SUPPORT`, gating all four core verdicts and all adapters.
- The four time cases are mandatory Control Chrome core-shard checks, outside the named qualification
  inventory, recorded in `outline-time.jsonl`. Qualification does not execute these time-only cases.
- Group 16 gates CI independently; its counts and latency do not enter qualification verdicts.

Control Chrome runs each browser shard with both `external` and `policy` installation. Qualification runs
the same named inventory in its two independent stable pairs. Final whole-run reruns repeat every job.

## Group 14: named browser cases

These are exact `check` names and their source locations. Each row describes its acceptance coverage;
details such as getter recordings and byte measurement are mandatory assertions, not human inference.

| Named case | Source | Verdict group |
|---|---|---|
| `READ BRIEF28 a service restart refuses old references after the new counter passes them` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L117) | SUPPORT → all core / adapters |
| `READ BRIEF28 Chrome restart and extension reconnect each refuse every old reference without reissuing strings` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L128) | SUPPORT → all core / adapters |
| `READ BRIEF28 more than 5000 elements drop an old reference and never issue its string again` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L145) | SUPPORT → all core / adapters |
| `READ BRIEF28 release and retake refuse an old reference with the same document and element id` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L175) | SUPPORT → all core / adapters |
| `GROUP 7 BRIEF28 the new read holds no password in any form of read` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L185) | 7 → password_exclusion |
| `READ BRIEF28 two tabs of one page share no reference and find with role returns its one link` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L197) | SUPPORT → all core / adapters |
| `READ BRIEF28 paging joins whole and a cursor keeps its query` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L220) | SUPPORT → all core / adapters |
| `READ BRIEF28 typing moves the state token and until meets a value` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L239) | SUPPORT → all core / adapters |
| `READ BRIEF28 frames of a second site and shadow roots are read` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L254) | SUPPORT → all core / adapters |
| `READ BRIEF28 addresses hold no sign-in and show an ordinary query` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L265) | SUPPORT → all core / adapters |
| `READ BRIEF28 100000 characters by ref advance at max 1000 without splitting escapes` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L284) | SUPPORT → all core / adapters |
| `READ BRIEF28 a wide table row is returned whole across pages` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L298) | SUPPORT → all core / adapters |
| `READ BRIEF28 a 20000 character value is returned in full across pages` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L306) | SUPPORT → all core / adapters |
| `READ BRIEF28 non ASCII and quote pages fit with a pending operation and the notice` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L316) | SUPPORT → all core / adapters |
| `READ BRIEF28 five tabs each keep their byte share and continue with their own cursor` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L333) | SUPPORT → all core / adapters |
| `READ BRIEF28 a change inside a frame moves the state token` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L358) | SUPPORT → all core / adapters |
| `READ BRIEF28 an unchanged page keeps its state token over 100 polls` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L366) | SUPPORT → all core / adapters |
| `READ BRIEF28 until meets text on a page that never goes quiet` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L371) | SUPPORT → all core / adapters |
| `READ BRIEF28 H1 hostile roles stay on the fixed role list` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L379) | SUPPORT → all core / adapters |
| `READ BRIEF28 H1 names values options tables forms paths stale lines titles and dialogs stay quoted` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L388) | SUPPORT → all core / adapters |
| `READ BRIEF28 H1 a 100000 character name is cut once and read whole by ref` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L434) | SUPPORT → all core / adapters |
| `READ BRIEF28 H1 100000 elements report the 20000 node cap` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L441) | SUPPORT → all core / adapters |
| `READ BRIEF28 small fixture outlines match the stored green browser results character for character` | [outline-read.mjs](../../control/chrome/ci/outline-read.mjs#L447) | SUPPORT → all core / adapters |
| `GROUP 7 BRIEF28 fields made plain before the reader came stay unread in every root and frame` | [unread-matrix.mjs](../../control/chrome/ci/unread-matrix.mjs#L101) | 7 → password_exclusion |
| `GROUP 7 BRIEF28 a shadow root met late and the name rule keep secrets unread in a watched document` | [unread-matrix.mjs](../../control/chrome/ci/unread-matrix.mjs#L183) | 7 → password_exclusion |
| `GROUP 3 BRIEF28 a form holding an unread field is refused unasked for a click Enter and a page submission` | [unread-matrix.mjs](../../control/chrome/ci/unread-matrix.mjs#L214) | 3 → binding |
| `READ BRIEF28 taken typed fields stay unread until exact one call approval and credentials stay excluded` | [outline-asking.mjs](../../control/chrome/ci/outline-asking.mjs#L53) | SUPPORT → all core / adapters |
| `READ BRIEF28 a field added after the asking question reasks without reading` | [outline-asking.mjs](../../control/chrome/ci/outline-asking.mjs#L82) | SUPPORT → all core / adapters |
| `READ BRIEF28 a same label replacement refuses the asking read before values` | [outline-asking.mjs](../../control/chrome/ci/outline-asking.mjs#L83) | SUPPORT → all core / adapters |
| `READ BRIEF28 a changed field label refuses the asking read before values` | [outline-asking.mjs](../../control/chrome/ci/outline-asking.mjs#L84) | SUPPORT → all core / adapters |
| `READ BRIEF28 swapping duplicate labelled fields refuses the asking read before values` | [outline-asking.mjs](../../control/chrome/ci/outline-asking.mjs#L85) | SUPPORT → all core / adapters |
| `READ BRIEF28 swapping unlabelled fields refuses the asking read before values` | [outline-asking.mjs](../../control/chrome/ci/outline-asking.mjs#L86) | SUPPORT → all core / adapters |
| `READ BRIEF28 a listed frame navigation refuses the asking read before values` | [outline-asking.mjs](../../control/chrome/ci/outline-asking.mjs#L87) | SUPPORT → all core / adapters |
| `READ BRIEF28 a listed field made password refuses the asking read before values` | [outline-asking.mjs](../../control/chrome/ci/outline-asking.mjs#L88) | SUPPORT → all core / adapters |
| `READ BRIEF28 a listed field masked refuses the asking read before values` | [outline-asking.mjs](../../control/chrome/ci/outline-asking.mjs#L89) | SUPPORT → all core / adapters |
| `READ BRIEF28 altered asking questions and field lists read no value` | [outline-asking.mjs](../../control/chrome/ci/outline-asking.mjs#L90) | SUPPORT → all core / adapters |

The cases above cover these brief requirements, including the cases that earlier steps could not reach:

| Brief requirement / fixture | Named-case coverage above; additional evidence |
|---|---|
| F1: 120 paragraphs / 80 fields, folded and complete | `paging joins whole...`, stored outlines, and all three F1 group 16 rows; `full` joins at two page sizes, no cuts or folds |
| F2: 200 × 6 cells and small table controls | `a wide table row...`, hostile table `ref`, group 16 `outline_f2_table`; `test_view_outline.Detail.test_a_cell_keeps_its_text_and_controls_in_order_and_an_empty_cell_stays` |
| F3: 300 links and unique name | `two tabs of one page...`, stored F3, service-counter advance, group 16 `outline_f3_find_link` |
| F4: 25 fields, 200 options, error, hidden names and password kinds | `efficiency-fixtures.mjs`'s F4; `outline.test.mjs`'s `a form: labels, hidden names, states, an error text once, a list field, and password fields as leaves`; `test_view_outline.Detail.test_a_form_by_reference`; old acting baseline row `f4_fill_send` ends in the recorded refusal |
| F5: partial change and new document | `efficiency-fixtures.mjs` and old baseline `f5_free_click`; new acting/change-report budgets belong to 28a |
| F6: second-site frames, nested frame and open/closed roots | `frames of a second site...`, `a change inside a frame...`, and stored F6; `until` finds nested-frame text |
| F7: small result pages and Next link | stored F7, restart/retake lifecycle cases, time cases, old baseline `f7_three_pages`; new navigation/acting is 28a |
| H1: hostile role spellings and tag fallbacks | `H1 hostile roles...`; fixed role set checked against every hostile attribute |
| H1: all hostile text surfaces | `H1 names values options...`; all fourteen strings reach names, values, options, cells, headers, title, error, ancestor path, table/list/form refs, stale present line, native title/dialog |
| H1: 100,000-character name | `H1 a 100000 character name...`; one cut, exact whole name through max-1,000 pages |
| H1: 100,000 elements and omissions | `H1 100000 elements...`; bridge record has 20,000 nodes and 80,001 omissions; compact reference-bearing `mode=many` |
| Stored expected outlines | one mandatory case compares F1, F3, F7 page 1, F6 and address outlines, all characters exact after reference identity normalization |
| 100,000-character text, wide row, 20,000-character value | three separate paging cases; joined text, stable total, progress and complete escapes on every page |
| ASCII JSON 48 KiB bound with pending and version notice | `non ASCII and quote pages...` and `five tabs each keep...`; `rpc-result.mjs` captures exact socket JSON bytes before parsing; every result rejects base shortening; each tab continues its own cursor in an ordinary single-tab call |
| Cursor query and state | `paging joins whole...` rejects changed full/find query; `typing moves...` rejects a cursor after value change; unit cases also change `ref` and `role` |
| State token / waiting | typed value without DOM mutation, frame mutation, 100 identical polls, nested-frame text, value-only text, and a never-quiet page are separate checks above |
| References / nonempty fresh tables | restart, reconnect, retake, eviction and cross-tab cases first issue fresh refs; service-restart case advances its counter past every old number; none reissues an old string |
| All plain-before-reader input kinds and textarea histories | group 7 `fields made plain...`: type changes to text/search/email/url, removed autocomplete/style/class masks, top/open/closed/cross-site roots; watched and unwatched; all read surfaces and brief 20 tools |
| Known-history-safe nontext kinds / editable areas | the same group 7 case keeps date, ticked checkbox/radio, range, colour, chosen option and draft editor; intentional unmasked-editor limit uses a harmless marker |
| Name rule, present mask and late-root typed fields | group 7 `a shadow root met late...`: real owner keys before meeting, typed textarea, unread fill refusal, initially empty field later filled/read, named fields excluded in either history mode |
| Unknown-history form cannot send | group 3 case: Send click, Enter, page requestSubmit, approved read, changed unread draft, field moved into waiting approval; no question / no receiver arrival; known-password replacement still asks and arrives once; later read and step leave the same document stopped |
| Taken-tab asking read | first `taken typed fields...` case: outline/ref/full/find and old read withhold values; approved result contains exactly ten listed fields including empty; refused/replayed/fresh call paths; credential marker never appears |
| Asking identity and description binding | eight page mutations (addition, replacement, relabel, duplicate swap, unlabelled swap, child-frame navigation, password type, mask), then altered question/list; recording verifies no value read before refusal |
| Duplicate labels | swap proves distinct element identities and changed-list refusal; distinct human descriptions in the question itself remain the explicit PR #106 handoff; unlabelled descriptions are distinct |
| Late-root asking read | existing `GROUP 7 POST18DF prepared typed reads bind exact elements frames readers questions and one call` in `late-binding-matrix.mjs`; group 3 later approved read still cannot send |
| Managed ask cannot be skipped | group 12 native precedence evidence covers allow-rule and skip-permissions paths; inherited asking-read rule still applies; `precedence-evidence.mjs`, boundary harness, and generated-rule tests |
| Address marker on page/link/form/frame and ordinary query | `addresses hold no sign-in...`; public URL and detail/find checks, credential/opaque/fragment/userinfo/reset path markers absent; ordinary v/q/page query stays; other public tool surfaces await 28a |

Expected outlines live in `control/chrome/ci/outline-expected/`. `source.json` records green browser run
44106253829 attempt 1, artifact `control-chrome-44106253829-1-policy-core`, code `7d352d7b`, and exact call
names. `stableReferences` changes only each short reference identity by first appearance. Page text, spaces,
escaping, folds and syntax are unchanged. They are browser-derived, not invented renderer snapshots.
F4's `view_fixtures.py` nodes 23/24 are unit-only: one browser document cannot be watched and unwatched at once;
the fixture comment explicitly says this. Browser extra label wrappers are accepted only as equivalent rendered
outline, as decided after step 5. F2's complete table and F4 details have dedicated checks, rather than stored
small-outline files.

The envelope fixtures execute early in `browser.mjs` while the pending page is fresh, and their original late
`check` calls require the saved result exactly once (`deferredOutlineCheck`). New failures do not move or skip
brief 20 cases. Asking tests scan complete chunked reader ingress through `completeIngress`, the whole boundary
record, tool results and service log. A public marker proves recording coverage; zero marker findings without
coverage is not evidence.

## Group 14: time through real transports

`control/chrome/ci/outline-time.mjs`, called by `browser.mjs` after group 1, writes these named log records:

| Named log check | What proves the brief | Verdict |
|---|---|---|
| `GROUP 14 TIME until on a text that never comes PASS` | proxy and command, false until_met, 5.5–8 seconds | mandatory Control Chrome core check |
| `GROUP 14 TIME five tabs with one held reader PASS` | four correct pages, third not_read, next same-connection answer correct, held tab correct after release, under 8 seconds | same |
| `GROUP 14 TIME a reply held past the bridge is given up and drained PASS` | actual extension reply exceeds bridge wait; own next replies, no cross-id answer, under 8 seconds | same |
| `GROUP 14 TIME an approval whose frame does not answer is unchecked PASS` | reserved approval retains unchecked validity, read and pending work finish under 8 seconds | same |

The test build adds bounded hold hooks through `prepare.mjs`; shipped runtime packaging excludes them. These
cases leave no pending work. The qualification inventory intentionally has no time-only group; the package
and security reviews still check switch/packaging exclusion.

## Browser-free requirements

These are named unittest methods or Node test names in `control/chrome_tests/`. They gate Python partitions
or the full Node job, not a browser qualification verdict of their own. The complete modules remain the test
inventory; the selected names below identify every distinct brief requirement.

| Brief requirement | File and named cases / classes | Verdict |
|---|---|---|
| Node/frame contract, integer ids, role/tag/state lists, depth and 20,000 nodes | [test_view_nodes.py](../../control/chrome_tests/test_view_nodes.py): `test_a_node_and_its_place`, `test_the_role_list_and_the_states_are_the_briefs`, `test_the_bounds_a_page_must_not_choose` | Python partition |
| Every fold, order and exact count | [test_view_outline.py](../../control/chrome_tests/test_view_outline.py): `test_more_than_eight_neighbours_of_one_role_show_five`, `test_long_text_is_cut_at_200_characters_and_its_reference_reads_it_whole`, `test_a_table_folds_whole_and_says_its_size`, `test_more_than_twelve_options_are_a_count`, `test_a_form_shows_its_first_40_fields_and_counts_its_hidden_ones`, `test_the_order_of_folding`, `test_every_folds_count_is_the_length_of_a_full_read_of_it` | Python partition |
| Order, inline links/formatting, roles, states, depths, ref forms, find/until | [test_view_outline.py](../../control/chrome_tests/test_view_outline.py): `test_text_stands_once_in_its_order_and_wrappers_get_no_line`, `test_an_inline_part_carries_its_value_and_states_before_its_reference`, `test_every_role_of_the_list_is_shown_and_nothing_else_is_a_role`, `test_two_spaces_for_each_level`, `test_a_table_by_reference`, `test_a_form_by_reference`, `test_a_text_a_link_and_a_list_field_by_reference`, `test_find_and_until_match_across_an_inline_part_by_its_name`, `test_the_path_has_at_most_80_characters` | Python partition |
| Escaping every surface and stale refusal; hostile twin rejects forged quote | [test_view_hostile.py](../../control/chrome_tests/test_view_hostile.py): `test_every_read_of_a_hostile_page_is_its_harmless_twin_outside_the_quotes`, `test_the_twin_check_itself_fails_for_a_text_that_leaves_its_quotes`, `test_a_refusal_holds_no_page_text_and_the_present_line_is_escaped`, `test_step13d_repaired_stale_present_line_keeps_the_same_escaping` | Python partition |
| Paging, whole text/value/row, max, escape boundary, 48 KiB and five tabs | [test_view_paging.py](../../control/chrome_tests/test_view_paging.py): `test_a_page_never_ends_inside_an_escape`, `test_a_text_of_100000_characters_comes_back_whole`, `test_a_table_row_wider_than_max_comes_back_whole`, `test_a_value_of_20000_characters_read_in_full_comes_back_whole`, `test_text_outside_ascii_stays_inside_48_kib_and_advances`, `test_a_text_made_of_quotes_stays_inside_48_kib_and_advances`, `test_five_tabs_each_get_their_share_and_their_cursor`, `test_another_query_is_invalid_input`, `test_another_state_token_is_a_stale_reference` | Python partition |
| Same identity/counter, dropped refs, all stale cases, reader reinstall | [test_view_references.py](../../control/chrome_tests/test_view_references.py): `test_the_same_element_keeps_its_reference_and_another_gets_another`, `test_one_counter_for_all_tabs`, `test_the_newest_5000_of_a_tab_stay_and_a_dropped_string_is_never_issued_again`, `test_every_stale_case_of_a_read_by_reference`, `test_a_new_reader_instance_in_the_same_document_gets_new_references` | Python partition |
| Five consonants, once/process, no store, 300 deterministic runs and forced collision | [test_view_references.py](../../control/chrome_tests/test_view_references.py): `test_five_consonants_from_the_systems_random_source`, `test_drawn_once_and_nothing_is_read_from_or_written_to_the_store`, `test_300_runs_in_a_row_and_no_reference_of_an_earlier_run_resolves_in_a_later_one`, `test_the_rest_shown_honestly_two_runs_that_draw_the_same_letters` | Python partition |
| Closed-tab reference cleanup and lost-event safety | [test_outline_action.py](../../control/chrome_tests/test_outline_action.py): `test_tool_close_and_release_forget_entries_without_an_event`, `test_extension_release_forgets_entries_and_ignores_old_sessions`, `test_release_before_the_first_outline_creates_no_reference_table`, `test_failed_close_does_not_forget_a_live_tabs_entries` | Python partition |
| Both address forms: userinfo, host/port/http, all words/tokens, fragments, ordinary values, percent encoding and bound | [test_view_address.py](../../control/chrome_tests/test_view_address.py): `test_the_site_never_holds_a_user_name_or_a_password`, `test_ports_http_and_the_host_in_lower_case_ascii`, `test_each_sign_in_word_in_a_path_hides_what_follows`, `test_each_credential_name_hides_its_value`, `test_a_long_token_with_separators_looks_random_and_a_slug_does_not`, `test_a_fragment_is_a_query_a_route_or_a_plain_word`, `test_a_parameter_without_equals_and_a_name_that_looks_random`, `test_at_most_300_characters_and_the_rest_counted`, `test_nothing_but_the_allowed_characters`, `test_the_short_form_of_every_address_holds_nothing_of_query_or_fragment` | Python partition |
| Bridge time, drain, no reply socket close and five-tab share | [test_outline_time.py](../../control/chrome_tests/test_outline_time.py): `test_a_late_reply_is_dropped_by_its_id_and_the_next_command_gets_its_own`, `test_a_late_reply_read_between_requests_is_dropped_and_never_overdue`, `test_no_reply_at_all_closes_the_connection_at_the_socket_bound`, `test_five_tabs_share_the_time_left_and_a_slow_first_costs_only_its_share`, `test_an_approval_whose_check_never_answers_is_unchecked_and_the_call_ends_in_time` | Python partition |
| Internal action switch absent from public tools / command / generated files and packaged unit | [test_outline_action.py](../../control/chrome_tests/test_outline_action.py): `test_without_the_switch_the_action_exists_nowhere`, `test_generate_refuses_to_run_with_the_switch_set`, `test_no_generated_file_names_the_action`, `test_the_packaged_entries_cannot_pass_it_on`, `test_the_ci_container_sets_it_for_the_service_and_the_browser_only` | Python partition |
| Six exact read budgets against recorded node fixtures | [test_view_budgets.py](../../control/chrome_tests/test_view_budgets.py): `test_f1_the_first_read`, `test_f1_everything`, `test_f1_the_80_fields_with_their_values`, `test_f2_the_whole_table`, `test_f3_the_one_link_with_the_unique_name`, `test_compare_three_open_tabs_is_one_call` | Python partition |
| Versioned credentials copy and unchanged send-word policy | [test_credentials.py](../../control/chrome_tests/test_credentials.py): `test_the_readers_copy_is_the_definitions`, `test_version_1_is_the_briefs_list`, `test_the_send_words_are_another_list` | Python partition |
| Refusal before payload/steps prepare; known-password substitution unchanged | [test_questions.py](../../control/chrome_tests/test_questions.py): `test_post18df_form_with_withheld_values_refuses_before_reload_or_preparation`, `test_post18df_form_added_withheld_field_and_changed_value_cannot_use_waiting_approval`, `test_step13d_repaired_question_and_field_description_still_require_exact_echo` | Python partition |

Node modules complete the browser-free map:

| Requirement | Named tests / source | Verdict |
|---|---|---|
| Reader nodes, own text/order, no box/style/descendant text, fixed roles/tag fallback, safe fields/options/errors/modal, cap/state/late root | `outline.test.mjs`: `inline formatting is text of its element, and only the link stands between the runs`, `a role comes from the list or the tag, never from a page's own string`, `a form: labels, hidden names, states, an error text once, a list field, and password fields as leaves`, `in a document the reader has not watched, a typed field says only filled or empty`, `beyond 20,000 nodes the reply says how many were left out`, `page_state moves with a typed value and a tick, and carries no value`, both `a shadow root...` tests | full Node |
| Credential words in all six places, whole/parts, paired words/digits/acronyms, ordinary shipping/postal code/pinned, editable/textarea exclusions | `reader.test.mjs`: `brief 28 every credential word withholds a typed field, whole and as a part of a name, in each of the six places`, `brief 28 a pair counts in either order, as one word and with a number; the rule holds in every document and for every typed element`, `brief 28 a credential word inside another word, and a paired word alone, withhold nothing` | full Node |
| Reader asking raw private verification before value getters | `reader.test.mjs`: `step13d reader field verification uses fresh raw private metadata` | full Node |
| Command queue deadline, expired wait, malformed time refusal, untimed compatibility and share | `background.test.mjs`: `brief 28 item 4 a frame that never answers ends each read command at its time with expired`, `brief 28 item 4 a command without a time waits for its frame as before`, `brief 28 item 4 the queue starts no command whose time is up when it reaches the front`, `brief 28 item 4 a malformed time is refused unrun in its turn and never runs without a time`, `brief 28 item 4 the malformed-time test fails without the refusal`, `brief 28 item 4 with five tabs a slow first one costs only its share`; `test_outline_time.py` tests above | full Node / Python |
| Script identity hardening | `background.test.mjs`: `brief 28 item 8 a script is one of ours only when the browser names it so, never by its url alone`: matching URL with wrong embedder is not ours; every extension-script double supplies both URL and embedderName | full Node |
| Native UTF-16 repair before direct/chunked/events/audit/errors/keys; valid pairs retained | `native-unicode.test.mjs`: four `native Unicode boundary: ...` cases, `native Unicode boundary covers events, audit data, errors and object keys`, `audit fragments keep valid pairs whole and repair text before inner JSON serialization`, `every native postMessage belongs to the common repair boundary` | full Node; `NATIVE_UNICODE_MUTATION=remove-boundary` must fail |
| Native hidden getter versus a control named hidden | `outline.test.mjs`: `a visible form stays readable when a named control shadows hidden, while a hidden form stays excluded`; step 13c's property-restoring mutation fails | full Node |
| Fresh/service repaired equality with visible/identity mismatch still refused | `service-comparisons.test.mjs`: `repaired action binding 1/2: <15 paths>; visible changes still refuse`, five `repaired command.expected: <key>...`, `repaired asking list: <change>...`, `repaired asking list is accepted once without reading values during preparation`, `asking list is rechecked after values are read`, two `repaired dialog answer: ...`, `repaired anticipated confirmation accepts raw text and refuses a visible change`, `repaired select value resolves one raw option; visible changes and repaired collisions refuse`, `select without native option facts keeps the reader refusal before comparing or setting values` | full Node; seven removal mutations below |
| Fixture change stream keeps parent mutation callable | `outline-fixtures.test.mjs`: `asking child cannot replace its parent mutation stream; the parent applies and acknowledges the added field`; pre-fix throws missing reviewChange, fixed parent adds and acknowledges exact nonce | full Node |
| Frozen baseline, actual proxy JSON count, five-run max, timing miss and refusal evidence | `test_efficiency.py`: `test_characters_are_the_text_claude_receives_and_time_is_the_median_after_the_warm_up`, `test_only_the_refusal_a_task_expected_may_fail_a_call`, `test_it_is_one_green_runs_record_and_stays_as_committed`, `test_rows_that_hold_give_no_miss_and_the_comparison_entry`, `test_each_miss_fails_the_rows`, `test_the_step_fails_after_writing_the_record`; `efficiency.test.mjs`; `efficiency-summary.py` `summarize` / `read_rows` | full Node / Python / hosted group 16 |
| Generated public tools/ask rules unchanged and instruction length | `control/tests/test_operations.py` `Generated.test_artifact_drift_effects_ask_rules_and_owner_only_absent`, `test_questions.py` instruction-limit case, `test_outline_action.Switch`, `PYTHONPATH=control python3 control/generate.py --check` | Python / generator |

Step 13d ran the ordinary comparison module (50 pass) and seven independent source-removal mutations:
`remove-initial-binding` (20 pass / 30 fail), `remove-final-binding` (20/30), `remove-expected` (45/5),
`remove-typed-binding` (47/3), `remove-dialog-binding` (48/2), `remove-confirmation` (49/1) and
`remove-option-value` (49/1). Each exits 1 with no skips. These are historical mutation results, carried from
PROGRESS; step 14 reruns the unchanged ordinary suites. The confirmation mutation was corrected to load the
same mutated source, rather than an unmutated isolated listener. It then fails its intended acceptance check.

## Group 16: task identifiers and gates

All tasks are implemented in `efficiency-probe.mjs` with fixtures from `efficiency-fixtures.mjs`, served by
`fixture.mjs`. One warm-up precedes five measured runs. `efficiency-summary.py` counts each complete result
as `display_json(bound_result(result))` and checks exact tool sequence and expected refusals.

| Brief task | Old task / tools | New internal-read task | Gate |
|---|---|---|---|
| F1 first read | `f1_first_read` / read | `outline_f1_first_read` | 1 call / 6,000 chars; same-run median ≤ 1.10 × old + 50 ms |
| F1 whole page | `f1_everything` / read cursors | `outline_f1_everything` | ≤ 3 calls / 75,000 chars |
| F1 80 fields after first read | `f1_fields` / find + read_form | `outline_f1_fields` | 1 further call / 6,000 chars |
| F2 whole table after first read | `f2_table` / read cursors | `outline_f2_table` | 1 further call / 23,600 chars |
| F3 unique link | `f3_find_link` / find | `outline_f3_find_link` | 1 call / 800 chars |
| Three first-page outlines | `three_tabs` / three reads | `outline_three_tabs` | 1 call |
| Open page / return fact | `open_fact` / open + wait | 28a acting row | baseline frozen |
| F4 six fills / send | `f4_fill_send` / read + fill_form + find + click | 28a acting row | old outcome refused, asking_input_too_large; no old send timing claimed |
| F7 three pages | `f7_three_pages` / click + wait three times | 28a acting row | baseline frozen |
| F5 partial change | `f5_free_click` / click + read | 28a acting row | baseline frozen |
| List 25 tabs | `list_25_tabs` / tabs cursors | 28a acting row | baseline frozen |

Each new read row also stays at/below frozen calls and characters (largest of five runs) and at/below
1.10 × brief 20's same-row median in the same run + 50 ms. Only F1's first-read comparison is appended once
to the frozen baseline. The existing paired latency gate remains in `latency-check.py`,
`latency-targets.json` and `latency-reference.json`; `latency.test.mjs` / `test_latency.py` pin it.
No latency allowance or sample count changes here. Final measured rows and the comparison's exact origin
are in REPORT. Group 16 remains a CI gate, never a qualification group.

## Brief 20 groups 1–13 carried forward

These source inventories remain authoritative; group-specific names are exactly those in `REQUIRED[n]`.
The per-site names are linked through the inventory rather than copied into this document.

| Group / purpose | Named inventory and source | Verdict |
|---|---|---|
| 1 classification and word/label/key matrix | `REQUIRED[1]`; `matrices.mjs`, word shards, `review-matrices.mjs` | classification |
| 2 held page-script/native activations | `REQUIRED[2]`; `matrices.mjs`, `animated-default-matrix.mjs`, review/recheck2/recheck3 matrices | page_script + owner baseline |
| 3 form/draft/item binding | `REQUIRED[3]`; `matrices.mjs`, `late-binding-matrix.mjs`, `destination-matrix.mjs`, review/recheck matrices, `unread-matrix.mjs` | binding |
| 4 native and page dialog binding | `REQUIRED[4]`; `matrices.mjs`, `review-matrices.mjs`, `sites/matrices.mjs` | shared binding / named adapter checks |
| 5 question content and clipboard notice | `REQUIRED[5]`; `matrices.mjs`, `review-matrices.mjs`, recheck2 matrices | binding |
| 6 exclusions and schemes | `REQUIRED[6]`; `matrices.mjs` | gates every core verdict |
| 7 password rule / compatibility | `REQUIRED[7]`; `matrices.mjs`, late-reader/late-binding matrices, outline-read/unread matrices; complete ingress scan | password_exclusion + forgery/isolation baseline |
| 8 control/release/popups/reload | `REQUIRED[8]`; `matrices.mjs`, `review-matrices.mjs`, `popups.mjs`, recheck2 matrices | page_script |
| 9 crash cutpoints | `REQUIRED[9]`; `matrices.mjs` | page_script |
| 10 named site adapter behaviors | `REQUIRED[10]`, `ADAPTER_REQUIRED`; `sites/matrices.mjs`, `matrices.mjs` | each named adapter plus shared core |
| 11 exact trusted owner entries | `REQUIRED[11]`; `matrices.mjs`, review and site matrices | shared/named adapter trust checks |
| 12 managed asking precedence | `precedence-evidence.mjs` → `precedenceVerdict`; `control/boundary/`, actual native precedence jobs | all required precedence evidence true |
| 13 native activation/residual limits | `REQUIRED[13]`; `matrices.mjs`, recheck2 matrices | page_script + residual baseline |

The base, boundary/18d and Mail regression workflows also trigger from the PR's control changes. Their
results are recorded separately in REPORT; their old group evidence is not replaced by a new-read test.

## Existing harness changes: old and new intent

| Step / rule | Before | After / exact affected evidence |
|---|---|---|
| 6, exception 1 | `reader.test.mjs` `fixes b G4.3 API and key words alone, and token names, stay ordinary fields` included typed Token/csrf_token/authenticity_token/_token | ordinary API/key names remain in renamed original test; new `brief 28 a typed field named token is withheld, and a hidden field named so stays an ordinary field` withholds typed four but preserves hidden tokens. No other old assertion changes. |
| 6, item 8 | extension-file scriptParsed doubles supplied only url | all relevant `background.test.mjs` doubles also supply embedderName; wrong embedder regression refuses it. Browser identity contract, no password exception. |
| 7, exceptions 2/4 | GROUP 7 password-matrix/password-inner Safe draft textarea starts with Public draft before root meeting | `password-fixtures.mjs` starts it empty, sets defaultValue in a later task; `GROUP 7 all password kinds across open closed and cross-site roots` now also checks it is read. All six form questions, approvals and one arrival each remain. |
| 7, exception 4 | review-shadow-{open,closed}-{native,event,click} starts draft Saved | `review-fixtures.mjs` starts the shadow draft empty; original `GROUP 2 REVIEW synchronous new shadow roots keep all submission kinds held` assertions still require holding, asking and receiver behavior. Other modes retain Saved. `late-withheld-form` remains unwatched and unchanged. |
| 12, inventory placement | step 11 read cases ran before matrices and outside named inventory | `matrices.mjs` registers password in group 7, other reads in SUPPORT; unread cases in groups 7/3; core source inventory and independent tests grow together. No old case moves. |
| 12, browser mutation only | shipped history rule always on | `prepare.mjs` test build can disable history only on the password-free probe; ordinary/reloaded/named-field assertions remain. Reviews must verify build.py and packaging cannot ship or honour this switch. |
| 13a, observed reload race | `GROUP 2 REVIEW borrowed wrappers respect another controlled tab and an ordinary document` reread child before guarded reload committed | `guardedOtherTabClick` in `review-matrices.mjs` waits for changed document before the original second click; no assertion changed, same review shard/group 2. |
| 13a, capacity fixture and later stopped calls | formatting-only H1 many page did not exceed reference count; page-requestSubmit case stopped after first result | many page now has 6,000 controls + 94,000 empty images; group 3 case adds later read and step, same document/zero receiver. No production bound changed. |
| 13b, new read/asking evidence | pending cursors/name-path cuts and transport bytes not modeled by new cases | follow full pending pagination, actual 24-character ancestor cuts, raw preparse bytes, early envelope deferred checks and complete getter fragments; old cases unchanged. |
| 13c, Unicode representation | H1 original lone-surrogate expectation could not pass strict wire | H1 still inserts that original code unit, now expects U+FFFD on each surface including native title/dialog. Every other escape/assertion and strict decoder stays. Native hidden getter regression covers shadowed form.hidden. |
| 13d, comparison fixtures | isolated listener omitted actual wellFormed helper; select doubles omitted successful native option facts | real helper loaded; three background selection doubles gain actual options/value. Original mismatch/activation/notice/new-frame assertions stay. Repaired comparisons preserve strict visible/identity checks. |
| 13d, synthetic stream collision | asking child replaced parent SSE mutation stream | child omits only unused stream; frame reporting/navigation/strings/assertions/deadlines unchanged. Parent mutation regression acknowledges nonce. |
| 14, merge and reporting | main ahead; final evidence not frozen | clean merge; no authored runtime/test change, no instruction addition, one comparison + review documents only. |

**read / limitation:** these are the only mapped behavior changes to old assertions or fixture setup. A first
failing browser case can end its shard and hide later cases; final green completeness and two full attempts
are therefore required. Historical red/blocked cases are kept in PROGRESS, not counted as passing evidence.
The duplicate-label human-description requirement is explicitly transferred to PR #106, the optional early-root
refinement is unbuilt, and acting/owner-tab features stay with 28a/28b. One literal mapping remains narrower
than the brief's wording: `test_every_role_of_the_list_is_shown_and_nothing_else_is_a_role` exhausts renderer
roles, while `outline.test.mjs` checks representative DOM tag/attribute fallbacks. No dedicated exhaustive
one-case-per-DOM-tag sweep was found for every entry in the brief's tag table. This is a coverage limitation
for the package review, not a claimed passing test or an accepted product defect. Step 14 changes no tests.
