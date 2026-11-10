# Part P — decided preexisting-dialog asking path

In progress; no acceptance green. The current direction is the lead's
2026-11-10 decision, with the owner's board #138 precedent, “Yes, ask in that
rare case.” A native modal already open when the tab is taken **asks**. This
supersedes the earlier fallback-refusal tracking for that case. It is a decided
rule, not a JUDGMENT-CALL. The allowance is now approximately 175 Chrome runs.

The extension authenticates this condition during admission and keeps the tab
available while the modal blocks debugger/page setup. The service always
reserves an asking action, binding the tab/control identity, native dialog
type/text and chosen accept/dismiss answer, including prompt text. Its fixed
question says the page was not guarded when the dialog opened, so its
continuation is not held, and the next Claude act requires the normal guarded
reload. Approval is required in the extension and consumed before the native
answer call. A failed response cannot replay it. Changed dialogs or answers
refuse before dispatch. A dropped question does not answer; the owner may still
answer in Chrome at any time. This kind never inherits a “don't ask again” entry.
Deferred setup resumes after the owner or approved tool answer; the next input
still requires the ordinary reload-on-take path.

Browser-free tests cover the warning, answer binding, mandatory question, exact
one dispatch, uncertainty without replay, no trusted exemption, drop with no
native call, owner closure, native metadata tagging, and admission while setup
is blocked. A mandatory group 4 browser case exercises alert/confirm/prompt,
changed answer, owner replacement of the dialog, drop/owner handoff, receiver
0/1/1 on approved answers, and the first-act guarded reload. Missing this case
cannot qualify. The actual container run is still required.

**Linux feedback, source `02f523d3`:** policy job of **42839244624** passed
both new-shadow-root matrices, including native/event/click paths and borrowed
native dispatch with noncomposed/noncancellable variants. It also passed the
review binding, owner mark, media/dirty reload, POST and focus matrices before
failing the frozen-wrapper Stop fixture's owner-navigation helper. The helper
waited for restoration before allowing the owner to navigate, while that
navigation is required to end the frozen document. A specific native-driver
option now allows this owner action during pending cleanup; production cleanup
is unchanged. Its new regression still selects the exact tab and window.
[Raw shadow receiver rows and completed/failing case list](records/review-fixes-02f5-shadow.json)
are retained. This is partial evidence, not a complete green run.

No local browser/profile was accessed. The Part S worktree and branch remain
untouched. No owner/lead workflow run was cancelled. Ledger: **150 Chrome IDs
before the next push**, expected **152 after**, allowance approximately 175.
