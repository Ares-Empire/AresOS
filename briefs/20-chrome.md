# 20: Chrome, the light tool

**Goal:** Claude works in the owner's own, normal Chrome through clean tools, exactly as `docs/design/CONTROL.md`
**section 6** specifies (decision 25): it reads pages as text, clicks, types and scrolls in his tabs, and asks before
anything that clearly sends. Chrome stays completely normal: no proxy, no certificate, no debugging port. Every
feature marked *first* in the Chrome part of `docs/control/FEATURES.md` gets its tool and a test, and all 13 test
groups of section 6 pass in containers on synthetic fixture sites. After this package a fresh Claude can do Chrome
tasks 8 to 14 in `docs/control/PLAN.md` with these tools alone, and every send is put to the owner as the page shows
it, checked right before it runs.

## Background (read first)

This branch starts from `main` **after brief 18d has merged**, not in parallel: test group 12 runs in 18d's
precedence harness, and both packages change the settings generator, the generated managed settings and the
generated `user-mcp.json`. Read on `main`:

- `docs/design/CONTROL.md` **section 6 is this package's specification**, every subsection: how the tool reaches
  Chrome, what the extension can and can't do, where Claude may go, which tabs, reading a page, what is free and
  what asks, how an asking action runs (binding, resume, outcomes), confirmations, site adapters, "don't ask again",
  the actions table, project work, what remains, and **Tests (brief 20)**. Sections 3 and 4 are the rules every
  action follows; section 7 the managed ask rules.
- `docs/control/FEATURES.md` (Chrome part) and `docs/control/PLAN.md` (decision 25, "What decision 25 changes", Chrome
  tasks 8 to 14).
- `reviews/control-design/2026-11-08-RECHECK-29.md` to `-34.md`: the design re-checks of section 6. Their
  counterexamples (activation paths, mutable events, compose binding, password extraction) are why it reads as it
  does; each one is a test below.
- Briefs 17 to 17c and their reports (`reviews/17-chrome-check/`, `17b-chrome-holds/`, `17c-chrome-pages/`) and
  `control/checks/17-chrome/README.md`: the harness, the attach, the policy install, the Stop button and the in-page
  hold this package builds on. 17d and 17e (the checkpoint) are history; don't port their code.
- `reviews/18-control-base/REPORT.md`, `reviews/19-mail/REPORT.md`, `reviews/18d-base-slim/REPORT.md` and
  `control/README.md` ("Adding Mail or Chrome"): use the base's `Adapter`, `Engine`, operations, file transfer and
  generated artifacts, the way Mail does. Change the base only where Chrome needs it, and say why in the report.

## What to build

1. **The extension** (Manifest V3, JavaScript), section 6 "How the tool reaches Chrome" and "What the extension can
   and can't do": `chrome.debugger` for input, navigation and file fields only, through a fixed list of DevTools
   methods (no DOM snapshots, DOM tree with attributes, accessibility tree, cookies, storage, network interception or
   script evaluation); no `cookies`, `management` or `externally_connectable`; the Claude tab group, badge, pinned
   toolbar button and popup **Stop** button; the extension's own session `declarativeNetRequest` rules for Claude's
   tabs; the details page for "don't ask again". A packaging script builds a signed CRX3 with a stable ID from a key
   it is given (CI uses an ephemeral key, as brief 17 did).
2. **The content-script reader**, in the extension's isolated world in every frame (cross-site frames included, the
   fixed list excluded): roles, accessible names, states and boxes computed the way Playwright's injected script
   does, closed shadow roots through the extension API; password fields excluded before any value is read, with the
   check repeated before every read (section 6's four kinds, and a field once seen as one of them stays excluded);
   paged views bound to a revision; `chrome_find`; `chrome_read_form`. Measure view sizes again (brief 17's numbers
   came from DOM snapshots).
3. **The page script** (main world, before the page's own scripts): saves the browser's own `submit()`,
   `requestSubmit()`, `click()` and `dispatchEvent()`; stops the three kinds of section 6 while the page handles
   Claude's input (a `submit()` call; a submission at the `submit` event, by a capture listener registered first; a
   script's activation of an asking control, before delivery); resumes submissions only as the same kind with the
   saved functions, with the one-use mark and the one further same-form submission, both staying consumed in nested
   handling; never resumes a stopped activation; and reports an activation that got around the wrappers as stopped
   (cancellable) or `unknown` (not cancellable), never resuming either.
4. **The native host** (a small Python relay, root-owned, system-wide manifest allowing only the extension's ID) and
   **`chrome.sock`** in the service: change it from brief 18's placeholder to accepting only his user, one host per
   running Chrome. Section 6 states the same-named user-level host as the accepted decision-24 level; don't add a
   policy against it.
5. **The Chrome adapter in the service** (Python): every action of section 6's actions table, with schemas and
   descriptions written for Claude, generated like Mail's into the MCP tool list, the `aresos` command,
   `docs/control/TOOLS.md`, the ask rules (`chrome_submit` asks; `chrome_submit_trusted` is free the way Mail's free
   send is) and the `chrome` server in `user-mcp.json`. The service holds the rules (section 6, "The service
   decides, the extension carries out"):
   - the rules shared by every Chrome action (errors, untrusted page text, the notice on unqualified versions) go
     once into the server's MCP `instructions`, generated from the definitions, and each description keeps only
     what is specific to its action: the pattern brief 18d sets for Mail (its item 7), including its check that
     Claude Code passes the instructions on unshortened;
   - **classification** of every input by what it would activate, before dispatch (the free cases and the six
     asking cases, the English and German word list in the definitions, versioned, whole-word matching);
   - **where Claude may go:** `https:`, `http:` and `about:blank` only; the fixed list of approval and settings pages
     checked before every read and action, on the top document and the target's frame, across taking a tab,
     redirects, popups, history and frames;
   - **operations:** prepared, asked through `chrome_submit` with the `question` first, checked by the extension
     against the expected state right before the input, run once; the recorded state exactly as section 6 lists it
     (form destination, all fields, every editable field in the document and its frames for a send outside a form
     without an adapter, the smallest item for delete and buy, adapter readings, confirmations); refusals as section
     6 states them; outcomes `checked`, `dispatched`, then what the page showed, `unknown` after a cut-off;
   - **confirmations:** covered only when an adapter named exactly that dialog in advance;
   - **uploads** through the caller's side into a copy the service owns and his user can read but not change;
   - **"don't ask again"** in the owner-only list, set through `sudo aresos admin chrome allow …` or the details page,
     revocable, never for deleting or paying, suspended when an adapter update widens a kind;
   - **read-only sites** in an owner-only list.
6. **Site adapters** (section 6, "Site adapters"), each matching its site by a host list in its definition:
   **Gmail** (compose: account, To, Cc, Bcc, subject, text, attachments; Send and Ctrl+Enter; shortcuts that delete or
   send; exact-recipient "don't ask again"), **WhatsApp Web** (per message, chat and text as the page shows them;
   opening a chat and typing free), **GitHub** (comments, reviews, merges, closing, deleting branches, tags and
   repositories, settings changes, its confirmations named in advance), **his bank, read-only** (reading, scrolling
   and links only), **Gemini** ("ask a question" named with its text, eligible for "don't ask again"; deleting or
   sharing a chat asks) and **Deezer** (playback and library additions free; removing, deleting, posting, sharing or
   paying asks). An adapter that doesn't recognise a page falls back to the generic rules.
7. **Image-side templates, not the image:** the Chrome policy entry (`ExtensionInstallForcelist` with a local update
   manifest), the native host's system manifest and the update manifest, as files under `control/chrome/packaging/`
   with a README for `laptop-aresos`, who puts them into the image. Don't change `os/`.

## Tests (containers on GitHub's Linux runners, no model, no real account)

- **Harness:** brief 17's: Google's branded Chrome stable on GitHub's Ubuntu runner, headed on Xvfb with Openbox, no
  `--no-sandbox`, no debugging port or pipe; the extension installed as a signed CRX (through the Linux
  external-extension descriptor as in 17, and once through the policy and local update manifest as in 17b). Print the
  Chrome version and keep the run identifiers as artifacts.
- **Fixture sites only:** synthetic local origins (at least two, for cross-site frames) with a receiver that logs
  every arrival independently of the tool; synthetic pages modelled on each adapter's site, served under fixture
  hosts that the adapters' host lists point to through a test configuration; a static test checks the shipped host
  lists and the shipped fixed list. **Never load a real site or use a real account.**
- **Section 6's 13 test groups, each by name in the report:** 1 what asks; 2 stopped page steps (both resume kinds,
  the loop case, script activations stopped and never resumed, acting on the control directly asking and running
  once, the wrapper fallback reported truthfully, nested handling); 3 the binding (with the re-check 30 and 32
  counterexamples and the read-only preview shown as the stated residual); 4 confirmations; 5 the question matches
  the page; 6 where Claude may go; 7 isolation, with the password test that records everything the browser returns
  to the extension, across shadow roots and cross-site frames; 8 control and cancelling; 9 crashes and restarts; 10
  adapters (all six); 11 "don't ask again"; 12 the managed ask rule on `chrome_submit` in normal and in
  skip-permissions mode, in 18d's precedence harness; 13 the residual shown honestly, listed in the report as not
  held.
- **Repeated runs:** the whole set runs twice on the final head.
- **Qualifying each new Chrome stable** (section 6). `control/chrome/qualification.json` records, per full Chrome
  version (major and patch, for example `158.0.7340.52`), which adapters and which core rule groups (the
  classification, the page script, the binding, the reader's password exclusion) passed.
  - *Trigger:* a scheduled workflow runs daily, reads the current full versions of Chrome stable **and Chrome beta**
    from Google's Linux package repository (`google-chrome-stable`, `google-chrome-beta`) and, for each version that
    isn't in the record yet (a new major or a new patch), runs the whole set on it twice. Beta is about four weeks
    ahead of stable, so a new major is normally qualified before his Chrome reaches it. Every push runs the set on
    the current stable as well.
  - *Result:* the workflow records the full version and channel with each adapter's and group's pass or fail, and
    an issue names any failing group. It publishes the new record itself, as its own small update not tied to an
    image or package build: it appends the entries to `qualification.json` on the data branch `chrome-qualification`
    (never `main`: the workflow needs `contents: write`, `id-token: write` and `attestations: write`, and pushes
    only that branch) with a GitHub artifact attestation for that file, and opens a pull request bringing
    the shipped copy in `control/chrome/qualification.json` up to date (it never merges it; the lead does, whenever
    convenient: the laptop doesn't wait for it).
  - *Delivery to the laptop:* the service fetches the published record over HTTPS once a day and whenever the
    extension connects with a version the held record doesn't cover. It accepts a fetched record only when:
    - its attestation verifies as made by this repository's qualification workflow on `main`, checked with a
      well-tried verifier (Sigstore's own library or `gh attestation verify`), never hand-written crypto;
    - it is append-only against the record held: every entry of the held record appears unchanged in it, so a
      fetched record can add passes and failures but never drop a failure or roll back.
    Otherwise, and when offline, it keeps the record it holds (shipped or fetched before) and logs why.
  - *Gating by major version:* the extension reports the running Chrome version when it connects, and the service
    reads the newest record it holds. A patch of a major that has a passing record runs normally; a passing beta
    entry counts for its major, so a new stable whose beta passed runs normally from its first day, and the daily
    stable run then records it too (a stable failure disables what failed, as below).
  - *Disabling:* a failure recorded for a version disables what failed, on that version and on later patches of its
    major until one of them is recorded as passing. A failed adapter is off and its site falls back to the generic
    rules. Where a core rule group failed, the actions that rely on it refuse with the reason ("Chrome 158: the page
    check failed qualification; acting is off until it is fixed"). A fix ships as a new record entry.
  - *Conservative mode, on a major version not yet recorded* (the rare fallback: his Chrome reached a new major before
    a passing record for it reached the laptop, for example when that major's beta failed and isn't fixed yet, or the
    laptop was offline for weeks). The tool asks more, never less:
    - adapters are off;
    - "don't ask again" is suspended;
    - every input that could activate something asks: any click or tap (links and ticks included), Enter or Space
      on a control, choosing from a list, and any form submission;
    - only reading, scrolling, typing into fields and navigating by address stay free, except that his read-only
      sites stay read-only: that restriction is his own and holds independently of adapters, so filling fields,
      clicking buttons and uploading there remain refused;
    - the password exclusion still runs, and a field it can't confirm is safe isn't read;
    - every result says plainly that this Chrome version isn't qualified yet.
  - *Tests:* the service against a record with a failed adapter, a failed core group, a failure on one patch with a
    later unrecorded patch of the same major (still off), and a later patch of a qualified major (runs normally). The
    conservative mode on an unrecorded major: a Gmail send goes through the generic rules; a "don't ask again" entry
    asks; a link click, a tick, a choice from a list, Enter or Space on a control and a form submission each ask and
    reach the receiver only after approval; reading, scrolling, typing and navigating by address don't ask; a field
    whose safety the reader can't confirm isn't read; on a read-only site (his bank fixture), filling a field, a
    button click and an upload are still refused; every result carries the notice. The delivery: a newer valid
    record is used; a record with a missing or altered attestation, from another workflow or branch, or dropping or
    changing a held entry is refused and the held record kept; offline keeps the held record; a passing beta entry
    for a major lets that major's stable run normally. Use an attestation from one of this package's own workflow
    runs and altered copies of it as fixtures (the accepted branch is a setting; shipped, it is `main`).
- Brief 18's, 18d's and Mail's suites still pass; the generated artifacts are in sync.

`.github/workflows/control-chrome.yml` runs them on pushes to this branch (path filter) and on its pull request; the
existing check workflow for 17 to 17e stays as it is.

## Out of scope

- Any real site or account, the provider of any account, and real addresses.
- The image itself: putting the policy, the native host manifest and the update manifest into `os/`, hosting the
  update manifest, and the production signing key (that is `laptop-aresos`'s work with the lead; this package uses
  an ephemeral key in CI and documents how the ID follows from the key).
- The Chrome rows marked *later*, *owner* or *never* in `FEATURES.md` (drag and drop, hover menus, canvas editors,
  PDF export, adding bookmarks, moving tabs between windows, screenshots as the main path).
- Anything under `os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, and the design and
  plan files (proposals go in the report). Running Claude Code with a model, or anything on this Mac outside this
  worktree.

## Acceptance

- Every *first* row of the Chrome part of `FEATURES.md` has its tool and at least one test; the report maps row →
  tool → test. Anything not built is a **PLAN-GAP** with the reason.
- All 13 test groups pass, by name, twice on the final head.
- No secrets, real addresses, account names, provider names or real sites.

## Report (`reviews/20-chrome/REPORT.md`)

What was built; the feature → tool → test mapping; the 13 groups with test names, run IDs and log lines; the
measured view sizes; the tool descriptions as Claude will read them (with anything you are unsure reads well pointed
out); the residuals of section 6 as observed on the fixtures; deviations as **PLAN-GAP**s; **JUDGMENT-CALL**s
(anything that changes how Chrome feels for the owner, for example a harmless control the word list makes ask); what
isn't done and why. Mark claims **run** (workflow run ID and log line), **read** (source and version) or **assumed**.

## Already decided

Decisions 24 and 25 and section 6 as merged: Chrome stays normal; what asks and what is free; the binding, the
resume kinds and the refusals; the fixed list; the six first adapters; "don't ask again" only for kinds an adapter
names, never for deleting or paying, never for WhatsApp messages. Brief 18's limits (15-minute approval, 16 KiB
asking input, 25 MiB files). Nothing is retried by itself; nothing resumes by itself after a restart.

## If unsure

Take the option that keeps a send from going without its approval or going twice, and that never claims something
was stopped or bound when it wasn't, and say so in the report.

## Stop rules

- Stop and report, rather than weaken the design, if a guarantee of section 6 can't be met on the fixtures: for
  example the page script can't stop a submission before the page's handlers, the reader can't avoid password values,
  or the attach needs a debugging port.
- Stop if any test would need a real site or a real account.
- Keep it to about 25 workflow runs.

## Owner decides

- Anything that needs his real accounts or real sites, including each adapter's check on the real site (Gmail,
  WhatsApp Web, GitHub, his bank, Gemini, Deezer) after the first boot on the laptop. The lead brings these to him;
  this package doesn't do them.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/20-chrome`, from `main` after 18d's merge. Commit in small steps, push
  this branch, open a draft PR against `main` with `gh pr create --draft`. Never merge, never push to `main`, never
  force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh, then a fresh `gpt-6.1-sol` high review and a `gpt-6-astra` security review: a large
build across an extension, a page script and the service, where each design counterexample needs its test.
