# AresOS control layer: the plan

Updated 2026-11-07. Led by the Claude session `mac-aresos-control`. The owner's picture is
[`OWNER-SCOPE.md`](../../reviews/councils/2026-11-07-control-layer/OWNER-SCOPE.md); it wins over the council's
VERDICT wherever they differ. This file is the plan and where it stands; keep it true.

## What we are building

A central Claude Code session, part of AresOS, runs the owner's apps through clean tools. Each app gets one tool set,
offered both as a terminal command (CLI) and as an MCP server, built from one definition. Every app with all of its
features. Screenshots and mouse moves are a last resort, never the main path.

The first two apps are Mail and Chrome. Those two are made to work really well before any other app starts.

- **Mail:** read, search, threads, write, reply, forward, send, attachments (download and attach), folders, flags,
  move, delete.
- **Chrome:** in the owner's own signed-in tabs. Claude sees the page as structure (fields with their labels and
  values, buttons, links, text, and where each one is on the page), navigates, fills and clicks without screenshots.
  A separate browser profile is only a test fixture.

## Decisions (owner, 2026-11-07)

1. **Approval is Claude Code's own permission prompt.** At the laptop he answers it in the session; when away,
   through Claude Code remote control on his phone (he approves pushes there). No separate approval screen in Aresus.
2. **What asks:** sending, deleting and submitting. Reading, searching, scrolling, following links and typing into
   fields are free. In Chrome, anything that submits data to a site asks, except on sites in a list the owner keeps.
3. **The exact permission settings are written once the tools exist** and we know more. The tools must be shaped so
   that settings can name each kind of action.
4. **Mail and Chrome first**, made to work really well; other apps after that.
5. **Questions for the owner go out as a push** (board ask plus a phone push), not only in a transcript.

## How sending stays under the owner's control

Three places, each with one job:

| Place | Its job | Why there |
|---|---|---|
| **The tools** | Know what each action really does, and give each kind its own tool: reading (`mail_search`, `chrome_read`), changing (`mail_move`), sending (`mail_send`, `chrome_submit`), deleting (`mail_delete`). In Chrome, a click or key press that would send data to the site is held and becomes a separate `chrome_submit` step. | Only the tool can see that a click sends something. |
| **Claude Code's settings** (a system-wide file in the image that only the admin account can change) | Decide which tools ask first and which are free. | Claude Code enforces them: Claude can't answer its own prompt and can't edit that file. Checked 2026-11-07: an "ask" rule still asks in skip-permissions mode, and the prompt shows the whole input ([check](../../reviews/control-checks/2026-11-07-permission-prompt.md)). |
| **CLAUDE.md** | Habits: how the owner writes mails, where things get filed. | These are requests to Claude. They are never what keeps sending under control. |

**Rules for every tool, so the prompt tells the truth:**

- An action that asks carries everything needed to judge it in its own input: the account, all recipients including
  Bcc, subject, the full text, attachment paths with their hashes; for Chrome the site, the address, the method and
  the data being sent. The tool refuses when the input doesn't match what would really happen (for example a file
  that changed after its hash was taken).
- Results are honest: sent, not sent, or "unknown, don't retry" (for example when the mail server's answer was lost).
  A tool never repeats a send by itself.
- Reading never changes anything: mail stays unread, nothing is saved on a site.
- Each result names exactly what it refers to (account, folder, message; tab, page, field), so Claude never acts on
  the wrong thing after the owner switched tabs or a folder changed.

**No way around the tools** (set up once in the image; the exact values come with the settings):

- Passwords and sign-in data belong to a separate system user. Only the tool service uses them; Claude's account
  can't read them.
- Claude's own terminal commands run in Claude Code's sandbox, which can't reach the tool service, the mail server or
  Chrome's control channel. Only the MCP tools can.
- The rules on asking, the allowed MCP servers and hooks, and the sandbox live in the system-wide file. Other ways to
  control the browser (Claude in Chrome, debugging ports) are off.
- Each of these gets a hostile test: a test Claude session tries every other route and must fail.

## Order of work

0. **Checks before building.**
   - **S1, Claude Code's prompt:** done 2026-11-07 ([check](../../reviews/control-checks/2026-11-07-permission-prompt.md)).
   - **S2, Chrome (brief 17):** done 2026-11-07 ([report](../../reviews/17-chrome-check/REPORT.md), PR #3). Our own
     extension attaches to an already-open, signed-in tab with no debugging port; pages read as structure with
     positions; filling and clicking work; form posts, fetches, beacons and autosave are held until approved. Not
     held: a service worker's own requests and WebSocket messages; and a disconnect let a held request go.
   - **S2b, Chrome (brief 17b):** done 2026-11-07 ([report](../../reviews/17b-chrome-holds/REPORT.md), PR #4). A
     request paused inside Chrome leaks when the extension is reloaded, updated, disabled or detached, so sends are
     failed at once and repeated exactly once after approval ("fail, then repeat"). Service workers are held by
     attaching to them. Installed by policy, the extension can't be switched off, but Chrome hides its debugging
     bar, so the extension shows its own sign and Stop button.
   - **S2c, Chrome (brief 17c):** done 2026-11-07 ([report](../../reviews/17c-chrome-pages/REPORT.md), PR #7). Sends
     can wait inside the page on honest pages (nothing leaks when control ends), so that is the normal path, with
     fail-then-repeat as the catch-all. Not a wall against a hostile page: one that keeps a live connection's own
     send function away from the wrap gets a message out. New shared and service workers start too fast to catch,
     so they aren't let start while Claude works on a site. The owner's own clicks that empty Claude's queue are
     held and his genuine notification answers work. On ten public sites: GitHub, Wikipedia and news smooth; Amazon
     and Google search hold telemetry; Notion and Google Docs need adapters.
   - **S2d, Chrome (brief 17d, before brief 20):** the frontier re-check of draft 8 found four blocking points (a
     paused request can slip out in the instant before the tool fails it; Chrome updates service workers by itself;
     a guard could end while an offline app still holds Claude's work; uploads can't be compared byte for byte).
     Draft 9 puts Chrome's own blocking rules under every hold; 17d checks the Chrome facts that rests on: the rules
     act before the request stage, at browser start, for every worker, and an allowance can't outlive control;
     which storage writes Chrome reports; what the tool sees of a blocked request's body.
     **Done 2026-11-07 (PR #8, CI green twice on `bf4ff66`): the floor does not hold.** Chrome's rules block every
     non-reading request before the request stage, also at browser start and from workers; but WebSockets opened by
     shared and service workers bypass every extension rule (Chrome 157 doesn't show them to extensions), and a
     different send matching an approved send's allowance escapes when control ends while it is paused (24 of 24
     trials). The frontier re-check 7 weighs a fail-closed boundary outside Chrome before brief 20.
   - **S2e, Chrome (brief 17e, before brief 20):** re-check 7 recommends a local checkpoint owned by the tool service
     (an intercepting proxy set by Chrome policy, with routing enforced by the OS) that holds each complete send from
     a guarded site and forwards exactly the approved one, once; if it fails, nothing goes out. 17e answers its
     eleven questions (bypass, connections opened before a guard, attribution, complete bytes, races, crash points,
     cancellation, other transports, TLS, guard end, and the owner's cost: robot checks, speed, prompts). The owner
     decides (#70) whether he accepts a checkpoint that decrypts his browser traffic on his machine.
     **Done 2026-11-07 (PR #10, CI green twice on `64ed6ed`): it holds**; costs and open points in its report.
1. **Design** (`docs/design/CONTROL.md`): done 2026-11-07. Draft 6 after the frontier review (8 blocking) and five
   re-checks (7, 4, 1, 1, then none: ready for brief 18). The feature list ([`FEATURES.md`](FEATURES.md)) goes to the owner
   with it.
2. **Base and boundary (briefs 18 and 18b):** the operation log, the generic MCP proxy and terminal command, a fake app with a
   send and a delete, file transfer on the caller's side, the managed settings draft, the sandbox boundary on Linux
   with the fixed hostile programs in CI, and the `Stop` hook. The owner checks a fake send prompt on his phone.
3. **Early image test (brief 18c):** a minimal, unpublished AresOS build in the CI virtual machine runs the fake app
   end to end. `laptop-aresos` agrees the `os/ci/` change first.
4. **Mail and Chrome (briefs 19 and 20)**, side by side on the base, once 18 and the Chrome checks have settled the
   contracts.
5. **Tool-user rounds** after each first version; fixes and site adapters become follow-up briefs.
6. **Security review** of the whole stack (fresh Codex, frontier), then **qualification in the real AresOS image**.
7. **After the first boot on the laptop:** the real mail account, the owner's own Chrome, the system-wide settings,
   and the first weeks of real use.

Codex (ChatGPT Pro) ends 2026-11-21. That is when Codex stops, not a promise: "completely right" wins over the date,
and whatever is left after it is built by Claude agents, more slowly.

## Who does what

| Who | Does | Reports to |
|---|---|---|
| `mac-aresos-control` (Claude, lead) | the plan, the design, the tool lists (what Claude will read), briefs, checking results, merges after the owner's "merge", the owner's questions | the owner |
| Codex workhorse (`gpt-6.1-sol`, xhigh) | checks (S2) and builds: one run per package in its own worktree, tested on GitHub's Linux machines | its package lead; for S2 the lead |
| Codex workhorse, fresh (`gpt-6.1-sol`, high, read-only) | package reviews | its package lead |
| Codex frontier, fresh (`gpt-6-astra`, xhigh) | the design review and the final security review: the base for every later app, and the security boundary | the lead |
| Claude package leads (background agents, one per running package) | run build, CI, review and fix rounds; report only when a package is ready for merge (summary and review result), on a JUDGMENT-CALL, or when blocked | the lead |
| Claude tool users (fresh agents that know nothing about the code) | do the everyday tasks below with the tools against a test mailbox and test sites; report where they got stuck, misread a result or needed too many calls | the lead: this is the check that the tools do what we need |
| `mac-capacity` | checks every few hours that the work matches OWNER-SCOPE | the owner |
| `laptop-aresos` | the install work, `os/`, `mod/` and the install docs | the owner |

Why this split: Codex has the capacity for building and reviewing until 2026-11-21, and every review is a fresh
context. Claude judges the tools from the user's side because Claude is the one who will use them. Package leads
keep build logs and review rounds out of the lead's context, so the lead keeps the overview and the owner gets short
answers. Briefs live on their package branch and reach `main` with the package; nothing is pushed to `main` without
the owner's "merge".

## Everyday tasks the tools must handle

The tool users run these against the test mailbox and test sites. A version is good when a fresh Claude finishes them
without screenshots, without guessing, and without asking the owner anything except the approvals. The owner can add
tasks at any time.

**Mail**

1. List the mails that need an answer this week, without marking anything as read.
2. Find a mail by sender and topic, show its thread, and download the attached PDF.
3. Reply to a thread with a short text and one file attached: recipients, subject and quoted text right.
4. Forward an invoice mail to a given address.
5. Move a month's invoices into a folder; flag one mail.
6. Delete a fixed set of newsletters to the Trash; the approval shows exactly which.
7. Write a new mail with two attachments to two people, one of them in Bcc.

**Chrome** (test sites)

8. In an open, signed-in tab: say what the page shows and which fields are still empty.
9. Fill a multi-page form (text, dropdowns, checkboxes, a date, a file upload) and stop before sending it.
10. Send that form: one asking step that shows the site, the address and the data.
11. Search a site and open the third result.
12. A page that saves while you type: typing there counts as sending and is held, unless the site is on the free
    list.
13. A chat page that sends messages over a WebSocket: typing the message and pressing Enter become one asking
    step that shows the text.
14. Two similar tabs, and the owner switches tabs while Claude works: Claude stays on its own tab and doesn't touch
    the other.

## Open

- The exact system-wide settings: once the tools exist (decision 3). Draft in `control/settings/` (briefs 18, 18b).
  One value to settle there: brief 18b's draft sets `sandbox.autoAllowBashIfSandboxed: false`, which hands sandboxed
  terminal commands to the ordinary permission rules instead of allowing them outright; what those do depends on the
  permission mode (in 18b's run an unapproved `sleep 2` still ran). Recommended: keep Claude Code's default (true). The
  sandbox holds without a prompt (18b), and extra prompts wear down attention for the send and delete prompts that
  matter.
- Language and libraries: decided in the design, after S2.
- How the CI virtual machine gets the AresOS image for step 5 (the private image needs read access the owner
  restores, or a fresh unpublished build in the job): decided in the design.
- The mail provider and account details stay out of this public repo.
- **Owner questions (2026-11-07), details in `CONTROL.md` section 10:** data leaving (anything that could carry
  something Claude wrote asks first; searches on his usual sites free or not), the central session kept apart from
  coding work, his usual Chrome sites, and a look at a test prompt on his phone.

## Where it stands

- **2026-11-07:** owner decisions above. S1 done. S2 (brief 17) running (Codex `gpt-6.1-sol`, branch
  `pkg/17-chrome-check`). Design draft for the shared base and Mail: [`docs/design/CONTROL.md`](../design/CONTROL.md);
  its Chrome part waits for S2, then the whole design goes to the frontier review.
- **2026-11-07, later:** S2 done; Chrome part of the design written from it. S2b (brief 17b) running.
- **2026-11-07, morning:** frontier review: CHANGES-NEEDED, 8 blocking (Linux sandbox can't single out one socket;
  routes to running code outside the sandbox; "known sites" doesn't stop data leaving; Chrome holding must be the
  default, not a guess; deleting through a free move; files through the service; truthful descriptions; partial
  outcomes). Design draft 2 answers all of them; feature list written; order of work changed (boundary and an early
  image test before the apps). Re-check of the fixes next.
- **2026-11-07, 07:30:** design ready (draft 6, five re-checks). Briefs 18 (base) and 18b (boundary) running, each
  with a Claude package lead. 17b running; 17c after it.
- **2026-11-07, 08:25:** 17b done (PR #4; design draft 7 takes its results). Brief 18 ready for merge (PR #6: final
  review SAFE after two fix rounds, CI green twice on `46c19ae`). 18b in its second fix round. 17c started.
- **2026-11-07, 08:55:** brief 18b ready for merge (PR #5: Claude Code's own sandbox blocked 127 of 127 routes
  around the tools; final review SAFE after three fix rounds). Briefs 18 and 18b and the checks 17 and 17b wait for
  the owner's "merge". 17c running.
- **2026-11-07, 10:05:** 17c done (PR #7, CI green twice on `8f1f196`). Design draft 8 takes its results into
  section 6 (holding inside the page as the normal path; the site guard settled: short and rare, and strict while
  on). Frontier re-check of section 6 next, then brief 20 (Chrome) after the owner's "merge" and brief 19 (Mail).
- **2026-11-07, 10:50:** brief 19 (Mail) running with a Claude package lead, on brief 18's branch (before the
  owner's "merge", to use this week's Codex allowance). Re-check 6 of section 6: CHANGES-NEEDED, four blocking;
  design draft 9 answers them (Chrome's own blocking rules as the floor under every hold, a guard that ends by itself
  only on evidence). Brief 17d (check of that floor) running; one more frontier re-check after it, then brief 20.
  Owner asked (#67): the strict guard.
- **2026-11-07, 11:40:** 17d done (PR #8, CI green twice on `bf4ff66`): Chrome's own rules don't make a floor that
  holds (worker WebSockets bypass them; an allowance lets a different send out when control ends at that instant).
  Brief 20 waits. Frontier re-check 7 (options: a local checkpoint outside Chrome that every browser request passes
  through, or a narrower Chrome) running; the owner decides with its result.
- **2026-11-07, 12:20:** re-check 7 recommends the local checkpoint (narrower Chrome rejected: an allowance can't tell
  competing bodies apart; a patched Chromium is a maintained browser fork). Owner asked (#68). Brief 17e (check of the
  checkpoint and its cost) running meanwhile, so the answer comes with numbers.
- **2026-11-07, 12:45:** brief 19 (Mail, PR #9): 26 tools, 57 base and 75 Mail tests green twice, 89 crash cases.
  Three fix rounds closed every finding except one area: an attached mail can still carry the owner's Bcc through
  odd MIME (a whitespace-only header line, a digest), and forwarded binary attachments got corrupted. A fourth round
  rebuilds attached mails from a short list of allowed headers, adds an independent final scan before sending, and
  keeps binary parts byte-exact. Re-check question #68 replaced by #69 (three options, after 17e's numbers).
- **2026-11-07, 14:40:** 17e done (PR #10, CI green twice on `64ed6ed`): the checkpoint held every tested send,
  including WebSockets of shared and service workers opened before the guard; an approval releases exactly one
  captured send; no crash point lets one out or repeats it. Costs: pages about 0.1 s slower (small sample), no extra
  robot checks seen, about 100 to 260 MB memory; browser calls and WebTransport refused while it holds; some of
  Chrome's own services fail its certificate (to fix in brief 20 without exemptions); uncertain attribution holds the
  whole browser. Owner asked (#70, replaces #68 and #69), recommendation: the checkpoint, calls allowed while no guard
  is on, and an owner switch to turn it off (which also turns off Claude's Chrome tools). Mail round 5 running.
