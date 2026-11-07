# 19-review-fixes-7: fresh special folders, no draft export, approved headers are sent headers

**Goal:** close the final security review of head `ec4a8bba`, findings 1, 2, 3 and 5, and record finding 4 for the
owner. The full review is `reviews/19-mail/SECURITY-REVIEW.md`; its findings are summarised below. Approved by the
lead on 2026-11-07. Briefs
19 and `19-review-fixes` to `-6` still apply where this brief doesn't change them; where in doubt, their "If unsure"
rule decides.

## The security review (verbatim summary of its findings)

1. **Blocking: a free move can put mail into Trash after its designation changes.** `adapter.py` (around line 911)
   checks the Trash name cached at onboarding; the fresh listing (around line 918) only checks that the target is
   selectable. If another client or the server moves `\Trash` from `Trash` to `NewTrash`, `mail_move(target=
   "NewTrash")` issues `UID MOVE` with no approval, although the current LIST marks it `\Trash`. The same stale
   mapping affects Drafts protection.
2. **Blocking: exporting a draft's decoded body bypasses full-text approval.** `mail_attachment_save` (around line
   239) exports a selected part's decoded bytes; draft protection applies only to outgoing compositions. Route:
   compose a long plain-text draft, `mail_draft_save`, `mail_attachment_save(part="1", name="notes.txt")`, compose
   another mail attaching that path, prepare, send. 23,002 bytes of draft body reached the SMTP sink under a
   781-byte approval that showed none of it.
3. **Blocking: encoded words hide the real outgoing subject and bypass control-character disclosure.** `codec.py`
   (around line 45) checks the supplied header string before decoding; the approval stores that string, but the
   MIME message interprets encoded words. A Base64 encoded-word subject showed the token in the approval and was
   delivered as "I authorize the transfer."; both final checks passed and the operation ended `done`. Encoded CR,
   LF and a right-to-left override also passed without being shown escaped. The same applies to display names.
4. **Blocking: folder deletion can delete a replacement folder.** Between the final check and `DELETE`, another
   client renames the approved empty folder and creates a new empty one with the same name; the new one is deleted.
5. **Should-fix: mail-derived values lose their untrusted marking in the audit log.** References, including the
   sender-controlled Message-ID, go into free-text summaries (`adapter.py` around line 821) that `control_log`
   returns (`engine.py` around line 182) without an `untrusted_content` marker.

## What to build

1. **Special folders resolved fresh before every change** (finding 1). Before any `mail_move`, `mail_copy`,
   `mail_delete`, `mail_draft_save`, `mail_folder_create`/`rename`/`delete`, every draft-protection decision (compose,
   attach, `mail_attachment_save`), and a send's preflight (the Sent evidence check and the Sent copy depend on the
   Sent role), read the current SPECIAL-USE roles from the server and compare them with the ones recorded at
   onboarding. Refuse, before anything changes, if a role is missing, ambiguous (two folders with one role) or
   different, and name the owner's setup step that fixes it: the existing owner-only command that re-reads the
   roles, or, if none can do it without re-adding the account, the smallest new owner-only step over `admin.sock`
   that records the current roles after showing them to the owner. A folder protected as Trash or Drafts is one that
   holds the role now **or** held it at onboarding.
   - Tests: on Dovecot, `\Trash` moved from `Trash` to a new `NewTrash`; `mail_move` and `mail_copy` into `NewTrash`
     and into the old `Trash` are refused with nothing moved, checked on the server; the same for Drafts (`\Drafts`
     moved, moving or copying out of either folder refused, attaching a message from either refused). After the
     owner's setup step records the new roles, ordinary moves work again and `NewTrash` is reachable only through
     `mail_delete`.

2. **Draft parts never leave through `mail_attachment_save`** (finding 2). Every part of a draft, its source
   included, is refused by `mail_attachment_save`, with the same draft rule as attaching (marked, in Drafts by the
   fresh roles of point 1, or flagged `\Draft`). The refusal says the owner saves draft attachments in his mail
   program, or Claude sends the draft itself with `mode=draft`. No file is written.
   - Test with the security review's exact route through the real proxy: compose a long draft, save it,
     `mail_attachment_save(part="1", name="notes.txt")` is refused and writes no file; attaching that path then fails
     because nothing exists; nothing reaches the SMTP sink. The same for the source, an HTML part, a PDF part, and a
     `\Draft`-flagged message outside Drafts. Saving a part of an ordinary received mail still works.

3. **What the owner approves is what recipients see** (finding 3).
   - Every header value in a composition is stored as decoded Unicode, and the service alone encodes it for the
     wire. Refuse encoded-word syntax (`=?…?=`) in what Claude writes: subject and display names. Values the service
     derives from an original mail (a reply's subject and recipients) are decoded before they are stored and shown.
   - Refuse C0 and C1 control characters, CR and LF in any header value. Refuse bidi and invisible formatting
     characters (U+200B–U+200F, U+202A–U+202E, U+2060–U+2064, U+2066–U+2069, U+061C, U+FEFF) in what Claude writes;
     in values derived from an original mail, show them escaped in the approval.
   - Display names are shown exactly as written, next to their address, so a lookalike name can be checked against
     the address.
   - The independent final check (`guard.py`, still sharing nothing with `codec.py`) decodes the outgoing `Subject`,
     `From`, `To` and `Cc` (display names and addresses) from the exact bytes, compares them with the approved values,
     and checks that the SMTP envelope recipients are exactly the approved To, Cc and Bcc addresses. Any difference
     refuses at compose and, before `DATA`, ends the operation `failed` with nothing sent and no submission on replay.
   - Tests: the security review's Base64 encoded-word subject, an encoded CR/LF in a subject and in a display name, an
     RLO in a display name (refused when Claude writes it, shown escaped when it comes from an original mail's
     sender in a reply), and a homoglyph display name (shown as written, with its address). One test feeds the final
     check a message whose decoded Subject differs from the approval, bypassing the builder, and checks `failed`
     without `DATA`.

4. **Audit log** (finding 5). Values derived from mail (Message-IDs, subjects, addresses, folder and file names) go
   into `control_log` and every audit summary only as structured fields inside an `untrusted_content` block, never
   into the service's free-text summary. This touches brief 18's `engine.py`; keep it minimal, keep the base suite
   green and say why in the report.
   - Test: a mail with a hostile Message-ID (instruction text, control and bidi characters) is flagged with
     `mail_flag`; the `control_log` result and the CLI log show it only inside the marked untrusted field, escaped,
     and the free-text summary doesn't contain it.

5. **Finding 4 is not a code change this round.** Record it as a **JUDGMENT-CALL** for the owner, in plain words,
   in the round-7 section and in "For the owner: decisions before merge": folder deletion only runs where the server
   refuses to delete a folder that holds mail, so no mail can be lost. If another mail program renames the approved
   empty folder and creates a new empty one with the same name in the same instant, the new empty one is deleted
   instead. The alternative is to remove folder deletion from the tools.

Then add a short "Review fixes, round 7" section to `reviews/19-mail/REPORT.md`: each finding, what changed, the
tests that prove it by name, and the new JUDGMENT-CALLs (finding 4, and that draft attachments can't be saved by
Claude). Link `reviews/19-mail/SECURITY-REVIEW.md` from `REPORT.md` next to the `REVIEW*.md` files. Update "For the
owner: decisions before merge" in `REPORT.md` and the PR body to match, in plain words.
Regenerate the tool descriptions and `docs/control/TOOLS.md` where behavior changed. Run IDs as in round 6: in
`REPORT.md`, the runs of the last commit that changes code or tests (both workflows, both passes) and the statement
that any later commit changes only files under `reviews/`; in the PR body, the runs on the final head.

## Out of scope

Everything else, including a fresh hunt for other issues and the deferred class of ordinary local files Claude
writes itself. Don't edit `reviews/19-mail/REVIEW*.md`. The same paths as brief 19 stay untouched: `os/`, `mod/`,
`docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`,
`docs/control/FEATURES.md`, and `control/tests/`.

## Acceptance

- Each point has regression tests that would fail on `ec4a8bba` (or are new behavior) and pass now; the report names
  them. No earlier test is weakened, skipped or deleted; a setup change forced by the new rules keeps its
  assertions and is named in the report.
- The Mail workflow and the base workflow both pass twice on the final head; brief 18's whole suite still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Refuse. Take the option that keeps a mail from being sent twice, sent without its approval or differently from what
the approval showed, or deleted without being named, and say so in the report.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/19-mail`, on top of its current head. Never rebase, never merge
  another branch in. Commit in small steps and push this branch; draft PR #9 already exists, so don't open another.
  Never merge, never push to `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Keep it to about 10 workflow runs.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: careful protocol and header work with server-side tests, on code it wrote.
