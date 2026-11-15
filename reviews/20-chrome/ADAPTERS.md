# Brief 20 adapter requirement map

The initial audit was committed before code as `cf8f5d41`. This is its final
map. Specification **read** with `git show origin/main:<path>` after fetching main
(`e8657edc`): brief 20 items 5–6, CONTROL §§3/4/6/7, FEATURES Chrome rows, PLAN,
re-checks 29–34. The adapters brief takes precedence over the continuation briefs.

**Evidence labels:** **run** means an executed command, **read** means inspected code,
**run (CI)** means both Linux install modes executed the assertion in run 42699095582.
Final runtime/test source fe7dd2fb: 12 functional matrices PASS, three strict shared-sentence rows FAIL in both modes. The final per-case run IDs/results are in [ADAPTERS-REPORT](ADAPTERS-REPORT.md).
No live-site compatibility is assumed from a synthetic fixture pass.

All new browser tests are in `control/chrome/ci/sites/matrices.mjs`; pages are in
`sites/fixture.mjs`. They use the existing independent `/receive` handler and save its
actual arrivals as `adapters-receiver.jsonl`, with cases in `adapters.json`.
“Asks” below includes 0 before approval, 1 after and 1 after repeat. A changed binding
must leave 0 on both original attempts; only newly prepared work may reach 1.

| Requirement | Code that implements it (**read**) | Strict test / status |
|---|---|---|
| Six definition host lists, shipped bank empty; fixed vendor list | `policy.HOSTS/FIXED_HOSTS`; exact host matching in `sites.recognize` | **run** `SiteSemantics.test_shipped_host_lists_and_fixed_list_exactly`; fixture hosts supplied only by CI service. |
| Versioned adapters; unknown hosts/pages and empty override fall back | `sites.VERSIONS`, complete/scoped recognition, None fallback; `Chrome.payload`, generic `classify` | **run** `test_hosts_exact_empty_override_and_disabled_adapters`; **run (CI)** `GROUP 10 ADAPTER unfamiliar pages and qualification fallback on all sites`. |
| Failed adapter uses generic rules; conservative mode turns all off | qualification switches + enabled map in recognition; owner restriction independent | **run** `SiteOwnerRules.test_failed_adapter_and_conservative_qualification_use_generic_rules`; **run (CI)** unfamiliar/fallback matrix and bank case. |
| Gmail account, To, Cc, hidden Bcc, subject, full text | `reader.adapterRead`, complete Gmail recognition, raw reading in shared binding | **run (CI)** `GROUP 10 ADAPTER Gmail full compose and every bound field`: exact values and one mutation per field. |
| Gmail attachments and read-only quoted preview bound exactly | raw adapter `attachments/preview` stored/rechecked by binding | Same fixture matrix compares received text/attachments/preview and refuses each changed fact. |
| Gmail Send, focused Enter/Space, Ctrl+Enter, Cmd+Enter ask | `gmail_send`, generic activation rules | **run** `test_gmail_compose_complete_and_not_a_typing_exemption`; **run (CI)** `GROUP 10 ADAPTER two Gmail compose windows and inbox shortcut` for Send clicks and compose shortcuts; the named unit covers focused Enter/Space. |
| Gmail shortcuts deleting or sending, including # outside compose | `gmail_delete.shortcut` on recognized selected inbox message and compose; send keys on editable compose | **run (CI)** two-window/inbox matrix: # on selected message, #/Ctrl/Cmd+Enter in compose, receiver 0/1/1. Delete is ineligible for trust. |
| Gmail two compose windows remain separate | reader selects closest dialog/form; binding stores scope and that scope's complete reading | **run (CI)** two-window matrix: mutate second body, first still sends its own fields; prepare/send second separately; neither sends twice. |
| Gmail exact-recipient owner rules preserve To/Cc/Bcc roles | quote-aware `recipients`; `gmail_send.parameters`; `Chrome.allow_id/trusted` | **run** recipient-set, quote-comma, ambiguous-notation and role-transfer unit cases; **run (CI)** `GROUP 11 ADAPTER Gmail exact To Cc Bcc roles account revocation and widening`. |
| Gmail recipient/account change at send time refuses; text/files still bound under trust | unchanged `Chrome.execute` and extension atomic binding compare | Same group 11 matrix mutates every account/recipient/content/attachment/preview fact after preparation and before trusted send. Engine contract test is **run**, not independent browser proof. |
| Gmail question reads like mail: account, recipients/Bcc, subject, text length, attachments | shared `Chrome.question` currently includes all except attachment summary | **MISSING shared change; run (CI), FAIL** `GROUP 10 ADAPTER Gmail question names its attachments` requires the attachment count and filename in the sentence. Full attachment fields already bound. |
| Gmail inbox # question explicitly names the deletion | shared `Chrome.question` currently says “activate Selected message” | **MISSING shared change**; **run (CI), FAIL** `GROUP 10 ADAPTER Gmail deletion shortcut question names the deletion`. The separate inbox receiver test passes 0/1/1. |
| WhatsApp per-message Send/Enter with chat, text, files as shown | `whatsapp_message`, raw adapter binding | **run** `test_whatsapp_message_shortcuts_and_no_trusted_kind`; **run (CI)** `GROUP 10 ADAPTER WhatsApp every message chat text attachments and free activity`. Consecutive messages require different approvals. |
| WhatsApp opening chat/read receipts and typing free | no semantic asking kind for these; generic free inputs | Same matrix: Open chat's independent receipt is free; fill inserts newline text without sending; Enter prepares. |
| WhatsApp never eligible for don't-ask-again | no trusted KINDS entry; owner allow rejects; trusted refuses | Same matrix tests both ordinary/admin owner channels and trusted-submit denial; **run** `test_ineligible_actions_cannot_be_allowed`. |
| GitHub comments; full text, preview, account/context bound | exact `github_comment` semantic kind | **run (CI)** `GROUP 10 ADAPTER GitHub actions and all named confirmations`, Comment and account/context/text/preview/attachment mutations. |
| GitHub submit/approve/request-changes reviews | exact `github_review` action labels | Same matrix, each review action asks and sends once; **run** independent expectation table in `test_github_actions_and_known_confirmations_are_specific`. |
| GitHub merge; closing issues and PRs | `github_merge/github_close`, exact context and action | Same matrix: Merge pull request, Close issue, Close pull request, named confirmation in question and confirmation stage recorded. |
| GitHub deleting branch/tag/repository | `github_delete`, delete effect and fixed exact confirmation templates | Same matrix: all three ask, never trusted, run once with confirmation stage. |
| GitHub settings changes | exact Save settings semantic kind and context | Same matrix: Save settings asks and confirms its named dialog once. Unrecognized settings help falls back (**run** unit assertion). |
| Alternate clear merge/close/settings/share/removal labels also ask | Whole-word adapter recognition retains merge/review/settings variants and share/unlike/unfollow/unstar labels; fixed plans are used only for the exact known action pairs | **run** local `test_clear_merge_close_settings_and_share_variants_remain_guarded`; **run (CI)** `GROUP 10 ADAPTER clear merge settings and sharing variants stay guarded`, 15 receiver-backed variants. |
| GitHub confirmations named in advance and matched exactly | fixed `GITHUB_ACTIONS` plans; shared `Chrome.prepare`; extension private `confirmationPlans` | **run (CI)** `GROUP 4 ADAPTER every named GitHub confirmation mismatch`: 7 actions × kind/text/frame/site/button/second-dialog variants. |
| Confirmation button/private opener mismatch independently checked | extension compares kind/text/frame_url/button/frame and private document | **run** Node `actual extension confirmation handler compares each field and consumes a match once`. Browser button variant uses a page dialog and also changes kind; no isolated native-button receiver claim. |
| New/different confirmation asks on its own; approval not inherited; match consumed once | shared generic dialog rules and private expected plan consumption | Mismatch matrix keeps receiver 0 after the original approval; listed dialogs require a new approval (0/1/1), unlisted dialogs require a separate explicit free input (1 and no repeat). Existing group 4 fixtures also cover native-handler submissions. |
| GitHub star free/eligible by repository; unstar deletes | `github_star`, exact repository/account parameters, effect eligibility gate | **run** semantic test asserts exact kind; **run (CI)** GitHub matrix: Star free, Unstar asking. Star is already free, so no fabricated approval is used to create an owner entry. |
| Bank owner supplies host; every non-read/scroll/link page input refused | owner `chrome_sites readonly`, `policy.classify`, service live recheck; bank adapter never grants policy | **run (CI)** `GROUP 10 ADAPTER bank owner restriction all inputs and positive reads links scroll`: fill/click/upload/check/select/press/fill_form, positive read/scroll/link, native dialog accept/dismiss refusal. |
| Bank remains restricted without adapters or in conservative mode | readonly checks precede semantics, including prepared execution | **run** existing conservative engine/policy cases; **run (CI)** fallback matrix bank restriction. Fixture input/change/keydown receivers detect accidental input. |
| Gemini question named “Gemini: ask a question” | semantic kind exists, but shared sentence builder currently uses raw “Send” target | **MISSING shared change; run (CI), FAIL** `GROUP 10 ADAPTER Gemini question uses its required semantic name`. |
| Gemini question full text and attachments bound; Enter and Send ask | `gemini_question`, complete reading and raw binding | **run (CI)** `GROUP 10 ADAPTER Gemini question content and always asking chat changes`, every relevant mutation; Enter also in group 11 case. |
| Gemini don't-ask-again exact site/account; revoked entry asks | KINDS plus shared owner entry/trusted checks | **run** `test_gemini_exact_account_owner_parameter`, `test_owner_entry_does_not_cross_site_origin`; **run (CI)** `GROUP 11 ADAPTER Gemini exact account owner entry and revocation`. |
| Gemini deleting/sharing chat always asks, even with question entry | ineligible `gemini_chat` effect delete/send | Same matrices check trusted refusal, owner allow refusal and 0/1/1 for both chat actions. |
| Deezer play/pause/skip/next/previous/seek/volume/queue free | exact free semantics; ordinary select/check remain free | **run** semantic table; **run (CI)** `GROUP 10 ADAPTER Deezer playback additions removals posts shares and payments`, including real choice/tick controls. |
| Deezer like/follow/add playlist/library free | `DEEZER_FREE` | Same matrix, each free action has a receiver arrival and no prepared approval. |
| Deezer unlike/unfollow/remove favourites or playlist/delete playlist asks | `DEEZER_REMOVE`, delete effects | Same matrix, all aliases 0/1/1 and no trusted route; **run** semantic tests. |
| Deezer posting/sharing/paying/subscription asks | listed send/pay semantics and explicit shares | Same matrix, Post comment/Share track/Share playlist/Pay/Subscribe 0/1/1, none trusted. |
| Deezer free label cannot bypass actual form submit | `target.submit` excludes free semantics | **run** unit test plus **run (CI)** Deezer form-playback fixture: Play submit button falls back to form asking. |
| All asking operations prepare without dispatch; bind; run once on submit; repeat does nothing | shared Chrome payload/prepare/execute, Engine and extension | Every positive asking matrix uses the independent receiver 0/1/1 helper; changes require fresh approval. New tests do not implement a replacement approval/reader. |
| Exact kind/account/site/parameters; generic, deleting/paying/WhatsApp never trusted; owner-only list | KINDS definitions; `Chrome.trusted/sites`; owner-only action definition | **run** SiteOwnerRules tests; **run (CI)** group 11 matrices plus generic/disabled/conservative trust denial; original owner-channel tests retained. |
| Widened adapter kind suspends owner entries; revocation takes effect | kind hash comparison in trusted, owner revocation | **run** unit widening/revocation; **run (CI)** Gmail group 11 fixture widens/restores kind via existing CI hook and checks receiver 0. |
| FEATURES/actions table maps site behavior through click/fill/press/select/check/scroll/read/dialog/submit/trusted/sites | unchanged shared action definitions plus semantic recognition | All matrices use these public tools. Native/page dialog, readonly and playback controls extend the existing group 4/10/11/feature tests. |

**Shared integration still required:** sentence generation in `chrome/adapter.py` and
registration of added case names in `ci/verdicts.mjs`. The three harness changes are
one-line registrations in fixture.mjs, matrices.mjs and service.py. The adapter suite
writes all its results and fails before running later core matrices if any required
adapter assertion fails. No new qualification pass or twice-green claim is implied.
