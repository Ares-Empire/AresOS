# AresOS control layer: the plan

Updated 2026-11-08. Led by the Claude session `mac-aresos-control`. The owner's picture is
[`OWNER-SCOPE.md`](../../reviews/councils/2026-11-07-control-layer/OWNER-SCOPE.md); it wins over the council's
VERDICT wherever they differ. This file is the plan and where it stands; keep it true.

## What we are building

A central Claude Code session, part of AresOS, runs the owner's apps through clean tools. Each app gets one tool set,
offered both as a terminal command (CLI) and as an MCP server, built from one definition. Every app with all of its
features. Screenshots and mouse moves are a last resort, never the main path. It is normal Claude Code, as on any OS,
plus these tools (decision 24): one session does it all, coding and commands included (decision 23), as his own user
with his own `gh` login, MCP servers, skills and plugins.

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

**Answers of 2026-11-07, afternoon** (given to mac-capacity, relayed; #56 and #57 confirmed with him directly before
acting):

6. **Chrome checkpoint: yes (#70)**, "if that's not a security risk". Hard requirements: it runs as its own user;
   nothing it sees leaves the machine; no bodies, cookies or secrets in logs; full upstream TLS checks; a key that
   rotates and can issue nothing while the checkpoint is stopped (a fresh root per start, the key only in the
   checkpoint's memory). The five conditions under S2e apply before it becomes his everyday browser.
7. **Chrome asks, and he can say "don't ask again" for an action (#52):** offered only for kinds of action a site
   adapter recognises, set by him at approval through a channel Claude can't answer, kept in the owner-only list,
   visible and revocable. Unrecognised sends always ask once. Searches on his usual sites are free. (Scope settled
   by decision 15. Never on WhatsApp Web: the checkpoint can't read its encrypted messages.)
8. **Assistant apart from coding (#53):** the session holding mail and Chrome runs apart from coding sessions; they
   coordinate only through messages that go via the tool service, and a message from the assistant asks like a
   send. (His folders: decision 17. Replaced on 2026-11-08 by decision 23: one session for everything.)
9. **His usual signed-in sites (#50), so far:** WhatsApp Web, Gemini, Gmail, Deezer (more to come). They are the
   first adapter targets. (How Claude sends on WhatsApp Web: decision 16.)
10. **Claude in Chrome stays for his own use (#58); AresOS's Claude Code rules apply machine-wide and change only
    with his admin password (#59).**
12. **The site guard is strict (#67):** it ends by itself only once the tool can see the site stored nothing of
    Claude's; otherwise it stays on until he ends it with one click. His words: "strict".
13. **Throwaway test images need no OK** (rule change, his words "change rule as you said", 2026-11-07): CI test images
    that are never published and leave the install pin untouched (such as brief 18c's) run without asking him;
    publishing a release and changing what his laptop installs still need him. laptop-aresos writes it into the
    image rules.
11. **Approval on the phone must read like a mail (#71):** the first phone test showed the raw tool call ("code
    basically, not a clean email"). Phone test 2 compares the tool asking him itself (MCP elicitation) with a
    readable summary in Claude Code's prompt; decision 1 changes with its result. (Settled by decision 21: decision 1
    stands, with a `question` sentence first in every asking input.)

**Answers of 2026-11-07, evening** (relayed by the lead, his words in quotes):

14. **Unlabelled local-only deletion: "a)".** Clicks on controls that don't say they delete stay free; labelled
    destructive controls and Delete or Backspace outside plain text editing ask; the gap (an unlabelled control can
    delete something kept only in the browser) is accepted as stated.
15. **"Don't ask again": "yes".** Offered for mail bound to an exact set of recipients, in the Mail tools and in Gmail.
    Deleting and paying always ask.
16. **WhatsApp Web: "a)".** Claude asks per message, as one approval of the bounded set of encrypted frames,
    described "as the page shows it".
17. **His folders: "pretty much everything no? like running claude with dangerously skip permissions just like I do
    now".** The assistant may change everything in his home folders except hidden settings and start-up places
    (dotfiles, autostart, shell start-up files, symlinks). Code lives in the coding user's own home, so coding
    sessions keep reading their repositories and never read his folders. Inside its sandbox the assistant works
    without permission prompts, as in his bypass sessions now; only sends and deletes ask (overwriting asks as a
    delete). This settles `sandbox.autoAllowBashIfSandboxed`: true. (Refined by the lead after re-check 15: a change
    to an existing file, a whole replacement included, is free because its previous version is first kept for 30 days
    in a store Claude can't write, which he restores from; deleting asks. Decision 23 drops the coding user's home:
    code lives in his project folders, which the sandbox may write. Decision 24 carries this further: Claude Code
    works in his home and projects as his own user, as on any OS; the version store and the sandbox as a requirement
    go with the containment.)
18. **`WebFetch` and `WebSearch`: "a)".** Searches are free, as on his usual sites in Chrome; fetching an address
    Claude composed asks; an address from him or from a page is free.
19. **The checkpoint's certificate limits: "okay",** accepted as stated (client certificates, no "continue anyway",
    a pause when Chrome's lists are out of date, a visible notice if Chrome is ever newer than its checkpoint).
20. **Merging, a new rule: "A safe merge shouldnt need permission should it?"** From now on the lead merges a PR
    without asking once its review says SAFE (or READY for a design), CI is green twice, and he has answered its
    judgment calls. Anything under "Owner decides" in `CLAUDE.md` still asks.
21. **The approval surface (#78): "okay we will use it as is, no need for a request",** after six phone tests.
    Approvals stay Claude Code's own permission prompt, in the terminal and through Remote Control on his phone. The
    phone shows an MCP tool's input as fields and values, there is no supported way to give it a header and text of
    its own, and MCP elicitation doesn't reach the phone. So every asking input starts with a `question` field: one
    plain sentence the tool service writes (for a mail the recipients with the hidden Bcc, the subject, the length
    and the attachments; for a deletion which messages; for Chrome the site, the action and what is sent), passed
    through unchanged and verified, followed by the full content fields. An approval screen in Aresus is not planned;
    a possible later improvement only if he asks.

**Decisions of 2026-11-08** (relayed by the lead, his words in quotes):

22. **Adding tools: "AresOS cant install any tools? that sounds incredibly terrible. we need it to be a regular OS
    like windows but we make it custom yk with tools etc. I think theres no way we cannot install gh, gh repo tools,
    mcps etc."; then "claude code can install tools on my normal OS so I think it should be possible in aresos too".**
    The central session can gain tools: other apps' MCP servers, claude.ai connectors, skills and plugins. Tools that
    only run inside Claude's sandbox (project packages, CLIs like `gh` used from the terminal) install freely. A tool
    that runs outside the sandbox (an MCP server, a program Claude Code starts) is added only through the tool layer
    as an asking operation: Claude prepares it, the question names what, the pinned version and the source, he
    approves in Claude Code's prompt, and the service installs it root-owned with a fixed interpreter and
    environment, like `aresos-mcp`. He can also add one himself with an owner command. Each added tool is classified
    read, change, send or delete; send and delete go into the managed ask list, and a tool that can't be classified
    asks on every call. The generated managed settings include these vetted additions, so the exact installed-settings
    check compares against generated plus vetted additions. Skills that are only instructions come from a root-owned
    folder. (Replaced by decision 24: he and Claude add tools as in normal Claude Code; the install-asking path is
    dropped.)
23. **One session for everything, replacing decision 8: "often times things are project work and intertwined.
    especially with chrome or once we add more apps. like a project might require a chrome test or check in chrome and
    so the coding session needs to be able to do it and the mail / app sessions sometimes need to execute commands and
    do things. I dont think the central split is that smart and also dont know how possible it is if I just start
    claude code with skip permissions"; after the lead's proposal: "yes that makes more sense. … the risk you describe
    exists on my normal laptops too. I think to some extend its unavoidable. its a trade off between I have to check
    every single action and having a small risk. And I think the risk is small. and usually claude asks for
    permissions and recognizes faulty things, especially once we make clear that prompts from me have basically only
    one way which is the session, not mail or sites etc".** One Claude session does coding, commands, mail, Chrome and
    later apps; the coding user is dropped. He may start it with skip-permissions: `disableBypassPermissionsMode` goes
    once the hostile tests show the asks, the sandbox, the file-tool limits, the network list and the managed hooks
    hold in that mode. Protection: sends, deletes and submits through the tools, asking; passwords and his signed-in
    browser only through the tools; commands and project code in the sandbox, which reaches neither the tool service
    nor his browser, only a list of developer sites, with pushes narrowed to his own repositories. Instructions come
    only from him in the session (a managed, root-owned `CLAUDE.md`). Accepted residual risk, his call: content from a
    mail or page could trick Claude into copying data out through an allowed developer site. (One session and
    skip-permissions stay. Decision 24 replaces the rest: the sandbox as protection, the developer-site list and the
    narrowed GitHub credential go.)
24. **Normal Claude Code plus the tools, replacing the containment parts of decisions 22 and 23: "Fundamentally I
    envision aresos as basically normal Claude code but with more tools. Now Claude code can basically just work in my
    projects and asks for permission certain things and I can allow it. Gh is used very smoothly. Is it necessary to
    change that?"; then "Essentially it's as we already discussed: Normal Claude code like in any OS + the tools we
    make. They add very little risk because even now Claude in chrome could read a malicious prompt for example and
    then have Claude push smth to git. Our tools, as long as they are safe, don't make it worse than that."** AresOS
    runs normal Claude Code, as on any OS, plus our tools. The tools must be safe in themselves and must not make
    things worse than normal Claude Code; a Claude tricked by content can do on AresOS what it could do on any OS, and
    that is accepted. Claude Code runs as his normal user in his home and projects, with his own `gh` login and his own
    MCP servers, skills and plugins, added as in normal Claude Code. The tools: send, delete and submit ask in Claude
    Code's prompt through managed ask rules (which no user allow rule, hook, mod or mode turns off, so the switches
    that locked everything else go); passwords with the tool service's own user; the `question`, approval binding and
    untrusted-content marking as built; the instruction-source line in the managed `CLAUDE.md`. Gone: the SELinux
    domains, set-group-id relays and registration, the program allowlist and the gates as hard switches, project
    snapshots, the GitHub App, rulesets and mirror, the git wrapper and project-folder ownership, the separate
    assistant user, the coding/assistant split, the exact managed-settings equality as a deployment requirement, and
    decision 22's install-asking path. Residual, said plainly: without a mandatory sandbox, a tricked Claude could call
    the tool service directly and skip the question; Claude Code's own sandbox stays available as an option he can turn
    on. (`CONTROL.md` sections 1, 2, 4.4, 7 and 10; section 6 to be re-examined against this bar before brief 20.)

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

**What the tools guarantee, and what they don't** (decision 24; set up once in the image, the exact values come with
the settings):

- Passwords and sign-in data belong to a separate system user. Only the tool service uses them; his account, and so
  Claude, can't read them.
- The ask rules for every asking tool live in a system-wide file only the admin account can change. A user or project
  allow rule, a hook, a mod or skip-permissions mode doesn't turn a managed ask off. The managed `CLAUDE.md` says
  instructions come only from him in the session.
- Everything else is normal Claude Code: it runs as his user with his own `gh` login, MCP servers, skills and plugins.
  Chrome is reached through the tools as in `CONTROL.md` section 6, which is re-examined against decision 24 before
  brief 20.
- Not guaranteed, said plainly: without Claude Code's sandbox (an option he can turn on), Claude's terminal commands
  run as his user and a tricked Claude could call the tool service directly with a prepared approval, skipping the
  question. That is the same level as normal Claude Code on any OS.
- The tests check the tools themselves: the asks hold in normal and in skip-permissions mode and against user allow
  rules, the question and the approval binding match what really happens, untrusted content is marked, and the
  passwords stay with the tool service's user.

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
     **Conditions before Chrome with the checkpoint becomes the owner's everyday browser** (mac-capacity's scope
     check, 2026-11-07; brief 20 and the tool-user rounds must meet them, otherwise the fallback is "Claude fills
     in, the owner sends"):
     1. *Unrelated tabs:* how often his other tabs stall while Claude works on one site (uncertain attribution holds
        the whole browser) is measured on his usual sites (#50); target zero. A call in his own tab when a guard
        starts is named in the design, and he knows before answering #70 that calls in Chrome stop while Claude acts.
     2. *Chrome's own protection:* brief 20 shows Safe Browsing (with a positive control) and component updates
        working through the checkpoint, not only "trust fixed".
     3. *A way out of a fault:* an owner-only switch turns the checkpoint to pass-through when no guard holds
        leftovers, with Claude's Chrome tools off until it is repaired; where leftovers exist, they are shown first.
     4. *Prompts:* adapters and grouping for his usual sites bring the 18 separate decisions of 17e's fixture down to
        about one per real action.
     5. *His real sites:* after the first boot, a short check on his signed-in sites (for example Google, GitHub, his
        bank), browsing them himself, for robot checks and breakage; 17e's sample was anonymous.
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

   **What decision 24 changes for the open briefs (2026-11-08):**
   - *Brief 18c* (early image test): Claude Code as his own user with his own MCP servers alongside ours; the fake send
     asking through the managed ask rule in normal and in skip-permissions mode, also with a user allow rule for it and
     after "Yes, and don't ask again"; no separate session or coding user, no launcher containment.
   - *The next base brief:* the managed settings reduced to the ask rules for every asking tool (generated) and the
     managed `CLAUDE.md`; the lock-everything switches and the forced sandbox dropped from the draft in
     `control/settings/`, with its tests; our app servers installed for his user like any MCP server; the tests that a
     managed ask beats user and project allow rules, "don't ask again", a hook returning "allow" and skip-permissions.
   - *Mail's boundary follow-up* (after Mail merges): the check of rounds 15 to 17, which refuses asking actions unless
     the managed files match exactly, becomes a check that every asking tool's ask rule is present in the managed
     settings, so his own MCP servers and settings are never blocked. Not a change to Mail now.
   - *Brief 20* (Chrome): waits for the checkpoint design to be re-examined against decision 24's bar
     (`CONTROL.md` section 10).
   - *The add-tool brief* is dropped: he and Claude add tools as in normal Claude Code.
   - `laptop-aresos` owns `os/` and the accounts: the separate assistant and coder accounts aren't needed, and his own
     account installs software normally (board #102 and #103).
6. **Security review** of the whole stack (fresh Codex, frontier), then **qualification in the real AresOS image**.
7. **After the first boot on the laptop:** the real mail account, the owner's own Chrome, the system-wide settings,
   and the first weeks of real use.

Codex (ChatGPT Pro) ends 2026-11-21. That is when Codex stops, not a promise: "completely right" wins over the date,
and whatever is left after it is built by Claude agents, more slowly.

## Who does what

| Who | Does | Reports to |
|---|---|---|
| `mac-aresos-control` (Claude, lead) | the plan, the design, the tool lists (what Claude will read), briefs, checking results, merges (without asking once the review says SAFE or READY, CI is green twice and the owner has answered the judgment calls: decision 20), the owner's questions | the owner |
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
answers. Briefs live on their package branch and reach `main` with the package; nothing reaches `main` except by a
merge under decision 20 (or the owner's "merge" where it doesn't apply).

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
  Under decision 24 the managed settings hold the ask rules for every asking tool and the managed `CLAUDE.md`; the
  lock-everything switches, the forced sandbox and `disableBypassPermissionsMode` go, in the next base brief with
  their tests. Claude Code's sandbox stays an option he can turn on (`sandbox.autoAllowBashIfSandboxed` true if he
  does, decision 17).
- Language and libraries: decided in the design, after S2.
- How the CI virtual machine gets the AresOS image for step 5 (the private image needs read access the owner
  restores, or a fresh unpublished build in the job): decided in the design.
- The mail provider and account details stay out of this public repo.
- **Owner questions still open:** none. Decision 24 removed the five choices of drafts 19 to 23. Open for the lead
  and the owner: the Chrome checkpoint re-examined against decision 24's bar before brief 20 (`CONTROL.md` section
  10).

**Follow-ups** (from the 18b merge-fix review, `gpt-6.1-sol` high, SAFE; for the next base or boundary brief):

- `control/launch.py`: the MCP proxy's identity guard checks only the real user id; it should check both the real and
  the effective user id, with a regression test for a mismatch. Under decision 24 the configured user is his own.
- `control/boundary/isolation.py`: the coding-user check should also plant rogue user and project MCP servers. Under
  decision 24 there is no coding user and his own MCP servers are wanted, so this follow-up is dropped; what stays is
  the check that a user other than his can't use the tools.

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
- **2026-11-07, 10:15:** brief 19 (Mail) running with a Claude package lead, on brief 18's branch (before the
  owner's "merge", to use this week's Codex allowance). Re-check 6 of section 6: CHANGES-NEEDED, four blocking;
  design draft 9 answers them (Chrome's own blocking rules as the floor under every hold, a guard that ends by itself
  only on evidence). Brief 17d (check of that floor) running; one more frontier re-check after it, then brief 20.
  Owner asked (#67): the strict guard.
- **2026-11-07, 11:30:** 17d done (PR #8, CI green twice on `bf4ff66`): Chrome's own rules don't make a floor that
  holds (worker WebSockets bypass them; an allowance lets a different send out when control ends at that instant).
  Brief 20 waits. Frontier re-check 7 (options: a local checkpoint outside Chrome that every browser request passes
  through, or a narrower Chrome) running; the owner decides with its result.
- **2026-11-07, 11:40:** re-check 7 recommends the local checkpoint (narrower Chrome rejected: an allowance can't tell
  competing bodies apart; a patched Chromium is a maintained browser fork). Owner asked (#68). Brief 17e (check of the
  checkpoint and its cost) running meanwhile, so the answer comes with numbers.
- **2026-11-07, 12:40:** brief 19 (Mail, PR #9): 26 tools, 57 base and 75 Mail tests green twice, 89 crash cases.
  Three fix rounds closed every finding except one area: an attached mail can still carry the owner's Bcc through
  odd MIME (a whitespace-only header line, a digest), and forwarded binary attachments got corrupted. A fourth round
  rebuilds attached mails from a short list of allowed headers, adds an independent final scan before sending, and
  keeps binary parts byte-exact. Re-check question #68 replaced by #69 (three options, after 17e's numbers).
- **2026-11-07, 14:00:** 17e done (PR #10, CI green twice on `64ed6ed`): the checkpoint held every tested send,
  including WebSockets of shared and service workers opened before the guard; an approval releases exactly one
  captured send; no crash point lets one out or repeats it. Costs: pages about 0.1 s slower (small sample), no extra
  robot checks seen, about 100 to 260 MB memory; browser calls and WebTransport refused while it holds; some of
  Chrome's own services fail its certificate (to fix in brief 20 without exemptions); uncertain attribution holds the
  whole browser. Owner asked (#70, replaces #68 and #69), recommendation: the checkpoint, calls allowed while no guard
  is on, and an owner switch to turn it off (which also turns off Claude's Chrome tools). Mail round 5 running.
- **2026-11-07, 14:55:** brief 19 (Mail, PR #9) passed its package review (SAFE after six fix rounds; 57 base and
  103 Mail tests green twice on `ec4a8bba`). Drafts now never leave as attachments and can't be moved out of Drafts;
  nothing Claude sends carries an AresOS header. Final security review by the frontier model running; then the
  owner's choices (11, listed in plain words in its report) and his "merge".
- **2026-11-07, 16:20:** Mail's final security review (frontier model) found four blocking points the package reviews
  missed: an encoded subject could show one text in the approval and another to recipients; a renamed Trash allowed a
  free move into it; a draft's text could leave through a saved file; and a folder-delete race (empty folders only,
  no mail can be lost: an owner choice). Round 7 fixed the first three (114 Mail tests green twice); round 8 makes
  Junk and Archive optional so onboarding works on servers that don't mark them. Frontier re-review after round 8.
  Phone check of the prompt timed out unanswered; restarted for 48 hours (#71 replaces #51).
- **2026-11-07, 17:17:** brief 18b merged (PR #5, `6b2667f`); two follow-ups from its merge-fix review under Open.
  Design draft 10 written (branch `control/design-draft-10`): section 6 rebuilt on the local checkpoint of 17e (no
  Chrome blocking rules, no URL allowances); the owner's five hard requirements for it (decision 6) as design
  requirements with their tests, including a fresh root per start (Chrome re-reads its trust policy while running, so
  the launcher restarts Chrome with the checkpoint); Chrome's own services trusted without exemptions; the strict
  guard; "don't ask again" for recognised kinds only; his four usual sites as the first adapters; the residuals in
  plain words; the five conditions before everyday use, and calls only while no guard is on. Section 7 adds the
  assistant apart from coding sessions, and the approval surface: the phone tests are done (on the phone, Claude
  Code's prompt reads as code in every shape tried; the tool's own question never arrived), and the proposal (an
  approval screen in Aresus, end-to-end encrypted and signed on the phone, with a local approval window at the laptop;
  alternative: approving only at the laptop) is open for the owner. Frontier re-check 8 of the diff next, then brief
  20.
- **2026-11-07, 17:38:** frontier re-check 8 of draft 10: CHANGES-NEEDED, six blocking points
  ([RECHECK-8](../../reviews/control-design/2026-11-07-RECHECK-8.md)). Design draft 11 answers them on the same
  branch: everything, GET and HEAD included, held at every checkpoint start until the guards and Claude's entered text
  (kept encrypted) are restored, then an uncertain GET or HEAD passes only when the entered-text check clears it;
  clicks on controls labelled as destructive (English and German) ask before the click, with the unlabelled ones
  named as a gap; "recognised" means the complete operation validates against a qualified adapter contract, so a
  GraphQL query is not reading by itself and WhatsApp Web's sends always ask; three users (owner, assistant, coding
  user `coder`) with nothing the assistant writes readable by coding sessions; every place the root is installed,
  reconciled at each start and removed at stop, with Chrome restarted whenever the root changes; the exact upstream
  TLS checks, with what is lost (Chrome's urgent revocation list, updates between images, client certificates) as an
  owner question before everyday use. Should-fixes too: attribution before anything reaches Claude, sign-in data
  redacted, the Aresus approval protocol in full, ending a call only on his answer, and brief 20's added tests.
  Re-check 9 next.
- **2026-11-07, 17:49:** frontier re-check 9 of draft 11
  ([RECHECK-9](../../reviews/control-design/2026-11-07-RECHECK-9.md)): three of the six points closed (recognised
  actions, the shared-file route, root removal), three partly, one new. Design draft 12 on the same branch: every
  acting input is recorded and acknowledged by the checkpoint before it reaches Chrome; an unlabelled control that may
  delete data kept only in the browser is a new owner question (recommended: such clicks stay free); the upstream
  checks use Chrome's own current revocation list, root list, CT log list and pins from its component folders, with
  age limits, and match Chrome 157 on stapling; a destructive action approved in advance is one bounded advance
  operation, used once; plus the should-fixes (safe-field descriptions, unattributed sends to his approval surface,
  `chrome_end_call` for all calls as one set, real firewall tests, the Aresus adversarial tests). Re-check 10 next.
- **2026-11-07, 17:57:** frontier re-check 10 of draft 12
  ([RECHECK-10](../../reviews/control-design/2026-11-07-RECHECK-10.md)): the input barrier and the advance approval
  closed; unlabelled local-only deletion and Chrome's security data still open. Design draft 13: both deletion options
  stated truthfully for the owner (option (a) also leaves drafts kept in storage on ordinary online sites; (b) asks on
  every site without an adapter), with objects inside editable areas counting as destructive; Chrome's security data
  read from its user-data directory, trusted on Chrome's verified installation and the folder's protection, Chrome and
  checkpoint pinned together with a visible notice if they ever differ, freshness from the data's own fields, and an
  exact recovery contract when it is out of date. Re-check 11 next.
- **2026-11-07, 18:05:** frontier re-check 11 of draft 13
  ([RECHECK-11](../../reviews/control-design/2026-11-07-RECHECK-11.md)): two points partly closed. Design draft 14:
  option (b) for unlabelled deletion discloses that links stay free; freshness of Chrome's security data counts only
  evidence for the version held (no evidence means out of date); recovery from out-of-date data runs only while the
  extension's tag coverage is verified; path segments get placeholders. Three points that mac-capacity found settled
  more narrowly than the owner asked are now owner questions in `CONTROL.md` section 10, with recommendations: which
  of his folders the assistant may change (recommended: he picks some, coding sessions lose read access to them),
  "don't ask again" for mail bound to exact recipients (recommended: offer), deleting and paying (recommended: always
  ask) and WhatsApp Web (recommended: not at all), and how Claude sends on WhatsApp Web (recommended: asking per
  message, the default). Re-check 12 next.
- **2026-11-07, 18:11:** frontier re-check 12 of draft 14
  ([RECHECK-12](../../reviews/control-design/2026-11-07-RECHECK-12.md)): every re-check 11 point closed; the WhatsApp
  approval shape open. Design draft 15: on WhatsApp Web each message is one page-trusting approval of a bounded set of
  encrypted frames captured from the start of Claude's composing to Enter, forwarded in order at most once or dropped
  whole, said plainly to be weaker than a verified send; "don't ask again" is never offered there (a technical limit).
  Folder option (b) separates saving new files from approved replacement and removes the coding user's access first;
  "Claude fills in, he sends" says his Send is still held while the site is guarded. Re-check 13 next.
- **2026-11-07, 18:15:** frontier re-check 13 of draft 15
  ([RECHECK-13](../../reviews/control-design/2026-11-07-RECHECK-13.md)): one WhatsApp timing point open. Design draft
  16: after Send, a short collection phase gathers the message the page produces a little later, then the set freezes
  and he is asked; late frames form a separate set with its own question; frames held before composing never go with
  a set's release. Opening a chat has its own collection deadline and approval expiry. Folder option (b) says plainly
  that coding programs holding files open are ended at the switch. Re-check 14 next.
- **2026-11-07, 19:27:** design drafts 10 to 16 merged (PR #11, `c7ba7a71`). The owner answered every open question but
  the approval surface (decisions 14 to 20): unlabelled local-only deletion "a)"; "don't ask again" "yes" for mail
  bound to exact recipients, with deleting and paying always asking; WhatsApp "a)"; his folders "pretty much
  everything", the assistant working without prompts inside its sandbox and only sends and deletes asking;
  `WebFetch` and `WebSearch` "a)"; the certificate limits "okay"; and a new rule that safe merges need no
  permission. Built into the design on branch `control/owner-answers-1107`. Open: the approval surface (#78).
- **2026-11-07, 19:33:** frontier re-check 15 of the owner's answers: recorded faithfully, four enforcement gaps. Fixed
  on the same branch: a fetch is free only for an address recorded with its origin (his message, or a link in a page
  or mail a reading tool returned), never one from terminal output, a file Claude wrote or an echoed argument; every
  change to an existing file in his folders is free because its previous version is first kept for 30 days in the
  tool service's version store (refused if that fails), and only deleting asks; every gating hook blocks when it
  fails; coding programs holding his files open are ended before the assistant's writes are switched on; the
  terminal's own folders are disposable scratch.
- **2026-11-07, 19:42:** PR #12 (the owner's answers and re-check 15's fixes) merged as `b84833c`. The owner decided
  the approval surface after six phone tests (decision 21, #78): Claude Code's own prompt, at the laptop and through
  Remote Control, with every asking input starting with the tool service's `question` sentence, verified. Written
  into the design on branch `control/approval-surface`; the Aresus approval screen is not planned. No owner question
  is open.
- **2026-11-07, 19:46:** frontier re-check 17 of decision 21: recorded faithfully, two leftovers fixed. Approval
  descriptions reach his phone through Claude Code and Remote Control, with no extra encryption promised; the
  approval deadline is 15 minutes from the service's reservation at prepare time, and a later call is refused; the
  `question` field is checked on the original arguments, escaped and bounded with exact counts; the laptop-only
  handling of his own unattributed sends is marked as the writer's judgment call, to confirm with him.
- **2026-11-07, 21:02:** a gap from mac-capacity's scope check, fixed in the design on branch `control/path-startup`:
  `~/bin` was neither hidden nor a named start-up place, yet Fedora's `.bashrc` (kept in AresOS's `/etc/skel`) puts it
  first on his PATH, so a `~/bin/git` the assistant wrote would run as him. Now every non-hidden folder on his login
  PATH, read from his real login shell and refreshed when it changes, is a start-up place the assistant can't write
  into; nothing the assistant writes has an execute bit; changing or moving one of his runnable files to another
  folder asks. A hostile test tries `~/bin/git` and a runnable file through every write path.
- **2026-11-08, 03:40:** two owner decisions rework the design (branch `control/one-session-tools`, design draft
  17): the central session can gain tools, the ones that run outside its sandbox only through the tool layer, asking,
  pinned and installed root-owned as their own users (decision 22); and one session does coding, commands, mail,
  Chrome and later apps, possibly in skip-permissions mode, with the coding user dropped, the sandbox reaching a list
  of developer sites with pushes only to his repositories, instructions only from him through a managed `CLAUDE.md`,
  and the risk of data leaving through those sites accepted by him (decision 23, replacing decision 8). Consequences
  for briefs 18c and 20, Mail's boundary check and a new add-tool brief are listed under "Order of work". Frontier
  re-check next.
- **2026-11-08, 03:53:** frontier re-check 18 of draft 17: both decisions and the accepted risk recorded faithfully,
  five blocking points. Draft 18 on the same branch: project deletions recoverable through snapshots of the project
  folders before every command and file write (his choice between that and asking for each deletion is open);
  planted repository settings contained (his git refuses Claude's repositories; Claude Code's own git runs in a
  sandbox with git's command-level settings); GitHub rulesets against branch deletion and force-push plus a
  service-side mirror of every branch; add-tool preparation fetching only from listed registries, building in a
  sandbox, installing by copying; added tools free only on reviewed evidence or an enforcing adapter, connectors
  asking per call, changed tools hidden, activation only with the regenerated settings in force. Each case is
  assigned to a workstream under "Order of work". Re-check 19 next.
- **2026-11-08, 04:03:** frontier re-check 19 of draft 18: four blocking points, the same pattern of gaps left by
  fixes one route at a time. Draft 19 contains whole classes instead: one traced set of programs the session's user
  may start outside the sandbox, git itself sandboxed for that user, the tool service accepting asking actions only
  from the registered `aresos-mcp`, GitHub refusing every deletion and rewrite by the session on all branches and
  tags, added tools free only on an independent review or an adapter. Where no full guarantee exists, the exact bound
  is one of four owner choices at the top of `CONTROL.md` section 10, with the lead's advice. Re-check 20 next.
- **2026-11-08, 04:10:** frontier re-check 20 of draft 19: two blocking points left. Draft 20: Claude Code and the
  relay start set-group-id into their own groups, which keeps them non-dumpable, so a process of the same user can't
  inject through their `/proc` descriptors; the service knows the relay by its group and its registered parent; an
  added server that holds his account access becomes the fifth owner choice. Re-check 21 next.
- **2026-11-08, 04:16:** frontier re-check 21 of draft 20: one blocking point (a direct child of Claude Code could
  start the genuine relay with its own pipes); choice 5 closed at the design level. Draft 21: the service accepts one
  relay per app per session, checks before every asking action that only Claude Code and the relay hold its pipes,
  and no pipe ends or sockets leak to other children; a relay restart means restarting the session. Re-check 22 next.
- **2026-11-08, 04:29:** frontier re-check 22 of draft 21: checks inside the same user's space can't tell a hostile
  program's requests from Claude Code's. Draft 22 changes the structure: an SELinux domain for the session refuses
  every program outside a fixed allowed set when it starts (chosen over a `fanotify` guard), with a blocking
  qualification gate and fail-closed refusals; the asking tools stay off on an installation until qualification shows
  nothing Claude can steer reaches Claude Code's sign-in; the relay checks are hardening, bound to the trusted start.
  Re-check 23 next.
- **2026-11-08, 04:41:** frontier re-check 23 of draft 22: the structure accepted, precision left. Draft 23: Claude
  Code's process is trusted code and nothing Claude wrote is loaded into it (each route a qualification item), the
  sandbox transition has a contract, both gates are hard switches for every asking action, registration closes at an
  acknowledged hook barrier, `rg` runs only through a fixed wrapper; the qualification items lost in an earlier
  reflow (his git clients, GitHub rulesets, the token refusal, the mirror) are back in the workstream list. Re-check
  24 next.
- **2026-11-08, 04:59:** owner decision 24: AresOS runs normal Claude Code, as on any OS, plus our tools, which must
  be safe in themselves and not make things worse than normal Claude Code. Design draft 24 on the same branch drops
  the containment of drafts 17 to 23 (SELinux domains, set-group-id relays, the program allowlist and gates, project
  snapshots, the GitHub App, rulesets and mirror, the git wrapper, the separate assistant and coding users, the
  add-tool path) and keeps managed ask rules for every asking tool, passwords with the tool service's user, the
  `question`, approval binding and untrusted marking. The residual (a tricked Claude calling the tool service
  directly without the optional sandbox) is stated plainly. The Chrome checkpoint is to be re-examined against the new
  bar before brief 20. Re-check against the new bar next.
