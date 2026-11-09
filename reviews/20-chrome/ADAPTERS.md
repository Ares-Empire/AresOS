# Brief 20 adapter requirement map

Specification **read** from `origin/main` after `git fetch origin main` on 2026-11-09:
`briefs/20-chrome.md` items 5–6, `docs/design/CONTROL.md` sections 3/4/6/7,
`docs/control/FEATURES.md` Chrome rows, PLAN and re-checks 29–34. Run-specific precedence:
`20-adapters`, `20-continue-2`, `20-continue`, `20-parallel-start`, brief 20.

This map is committed before implementation. **Read** means source inspection, not a test run.
The starting report records passing group 10 evidence (42664895844/42664908151 and later
cc17235f jobs); that is prior evidence, not acceptance of the additional rows below.

| Requirement (brief 20 / CONTROL §6 / FEATURES) | Starting code | Starting fixture/test evidence, or **missing** |
|---|---|---|
| Six host lists; bank empty and owner supplied; fixed approval list | `policy.HOSTS`, `FIXED_HOSTS`; `sites.recognize` | **Missing** exact static assertion of all shipped lists (existing `Policy.test_group6_schemes_and_shipped_fixed_hosts` iterates the current fixed list). |
| Versioned semantic adapters | `sites.VERSIONS`, `KINDS` | **Missing** independent tests of recognized kinds and incomplete readings. |
| Unrecognised page → generic rules | `recognize` returns None; `Chrome.payload`, `policy.classify` | **Missing** per-site incomplete/unrecognised fixture cases. |
| Qualification-disabled adapter → generic | `recognize(enabled)`, `Chrome.payload`, `trusted` | **Missing** per-adapter failed qualification fixtures; conservative mode tested in existing `QUALIFICATION conservative activations ask and core failures gate before reads`. |
| Conservative mode turns every adapter/trusted kind off | `qualification.switches`, `recognize(enabled)`, `Chrome.trusted` | Existing QUALIFICATION matrix; **missing** six-site assertion. |
| Gmail account, To, Cc, Bcc, subject, full text | `reader.adapterRead`, `sites.recognize`, `Chrome.binding/question` | Existing `GROUP 10 adapter gmail`, shortcuts; group 3 account/recipient mutations. **Missing** separate exact assertions and mutation of every field. |
| Gmail attachments as shown, bound with compose | `reader.adapterRead.attachments`, binding raw adapter reading | Existing fixture has attachment; **missing** exact attachment assertions/mutation. |
| Gmail Send asks | `gmail_send`, `policy.classify` | Existing `GROUP 10 adapter gmail`, receiver 0/1/1 helper. |
| Gmail Ctrl+Enter / Cmd+Enter asks | `gmail_send`, editable key rule | Existing `GROUP 10 adapter shortcuts and account-specific questions`. |
| Gmail shortcuts deleting/sending (including #) ask | `gmail_delete.shortcut`, `gmail_send` | Existing shortcuts matrix; **missing** destructive effect/kind assertion and non-compose # coverage. |
| Gmail exact-recipient don't-ask-again by To/Cc/Bcc and account/site | `gmail_send.parameters`, `Chrome.allow_id/trusted/sites` | Existing group 11 and `OwnerRules.test_group11_owner_only_exact_parameters_revocation_and_widened_kind`; **missing** Cc/Bcc/role transfer, site, ordering, and display-name comma counterexamples. |
| Two Gmail compose windows stay separate | reader scope selects closest dialog/form; binding includes scope | **Missing** fixture, independent receiver and cross-compose mutation tests. |
| WhatsApp per-message Enter and Send, chat/full text/attachments as shown | `whatsapp_message`, raw reading binding | Existing group 10 Send/Enter and group 3 chat change; **missing** attachment/text exactness/mutation and consecutive-message approval. |
| WhatsApp opening chat and typing free | generic free rules | Existing fixture exposes Open chat, but **missing** free-action assertions. |
| WhatsApp never eligible for don't-ask-again | no KINDS entry; `Chrome.sites/trusted` | **Missing** owner allow refusal and trusted-submit refusal with receiver log. |
| GitHub comments | `github_action` word classification | Existing group 10 Comment. **Missing** semantic kind exactness and bound review text/preview. |
| GitHub reviews (submit/approve/request changes) | `github_action` substring review | Existing group 10 Submit review; **missing** other review labels. |
| GitHub merge | `github_action` substring merge | Existing group 10 Merge pull request; **missing** named confirmation. |
| GitHub closing issues and pull requests | `github_action` substring close | Existing group 10 Close issue; **missing** Close pull request and named confirmations where shown. |
| GitHub deleting branches | `github_action`, exact native confirm plan | Existing group 10 Delete branch and group 4 exact/native mismatch matrix. |
| GitHub deleting tags/repositories | `github_action` | Existing group 10; **missing** named confirmation fixtures. |
| GitHub settings changes | `github_action` substring settings | Existing group 10 Save settings; **missing** exact action families/confirmation fixture. |
| GitHub confirmations named before input; exact kind/frame/site/text/button; consumed once | sites has only Delete branch plan; `Chrome.prepare`, `background` confirmationPlans | Existing group 4 tests text, prompt, frame, site, twice. **Missing** button mismatch and every newly named confirmation. |
| Other/new confirmations classify independently; no inherited permission | `Chrome.dialog`, `policy.classify` | Existing group 4 page/native/new/free/dialog-handler tests. **Missing** additional adapter-specific plans matrix. |
| GitHub star eligible by exact site/account/repository, unstar always asks | `github_star`, KINDS, trusted effect gate | **Missing** receiver-backed allow/revoke/exact repository tests. |
| Bank reading, scrolling and web links only | owner-only readonly list, `policy.classify`, `Chrome.execute` live recheck | Existing group 10 checks fill/button/upload refused. **Missing** positive read/scroll/link and all other acting verbs. Bank recognition itself intentionally does not grant read-only policy. |
| Bank restriction independent of qualification | `readonly` before adapter/generic classification | Existing conservative bank cases; **missing** full restricted action matrix. |
| Gemini question called “Gemini: ask a question”, with full text/files | `gemini_question`; raw adapter reading in binding/question | Existing Send/Enter fixture. **Missing** required question name: `Chrome.question` uses raw reader target “Send”, not semantic kind. Shared service change needed; do not mutate reader facts as a workaround. |
| Gemini per-site/account don't-ask-again | KINDS, `Chrome.allow_id/trusted` | **Missing** receiver-backed account/site/revoke tests. |
| Gemini deleting/sharing chat always asks | `gemini_chat`; delete/share label checks | Existing group 10 actions; **missing** allow/trusted refusal and changed preview/attachments. |
| Deezer playback play/pause/skip/seek/volume/queue free | `deezer_library` free label set | Existing group 10. **Missing** next/previous and actual select/volume controls. |
| Deezer like/follow/add to playlist/library free | free label set | Existing group 10 except Add to library; **missing** explicit row coverage. |
| Deezer remove favourites/playlist and delete playlist ask | listed delete words | Existing Remove from playlist/Delete playlist; **missing** Unlike/Unfollow (no listed word), favourites variants. |
| Deezer posting/sharing/paying asks | listed words/share substring | Existing Share track/Subscribe; **missing** posting/payment exact content and never-trust tests. |
| Adapter sends bind all adapter facts including read-only previews | `binding` stores raw frame.adapter; extension rechecks | Existing group 3 and group 13 generic residual; **missing** per-field/per-site strict adapter mutations. |
| Question and content describe action/account/targets/files as shown | `Chrome.prepare/question`, shared approval rules | Existing group 5; **missing** mail-shaped attachment/length question and semantic Gemini/action names. Shared service owns sentence generation. |
| Every asking path prepares without input, submit checks state once, repeat never sends | `Chrome.payload/execute`, Engine, extension input | Existing approval helper 0/1/1; new rows need independent receiver evidence too. |
| Trusted sends check current binding on every use | `Chrome.execute/trusted`, extension binding | Existing group 11; **missing** trusted changed text/attachment/account tests on new fixtures. |
| Allow/revoke only owner channels, exact kind parameters; generic/deleting/paying excluded | `Chrome.sites`, admin socket, `Chrome.trusted` | Existing engine owner denial/group 11; **missing** explicit per-kind negative matrix. |
| Widened adapter kind suspends entries | KINDS digest comparison in trusted | Existing group 11 widening and engine test; new definitions must change kind hash for widening. |
| FEATURES action/tools: click/fill/press/select/check/scroll/read/dialog/submit/trusted/sites | shared definitions/Chrome service; sites only semantic recognition | Existing feature/group 4/10/11 matrices; additional fixtures exercise these public tools, no substitute browser/approval path. |

Remaining changes in shared files will be specified exactly in ADAPTERS-REPORT.md. No
local browser or browser profile may be read or started. Only plain Python/Node locally;
browser evidence comes from `control-chrome.yml` Linux containers, capped at about 25 runs
for this branch. No core owner-input/injection/reload stand-in will be built.
