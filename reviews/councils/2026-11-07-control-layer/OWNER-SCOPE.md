# What the owner means by the control layer (2026-11-07, after the verdict)

The owner read the outcome and corrected its scope. **This note wins over VERDICT.md wherever they differ.**

**The picture:** a central Claude Code session runs the whole AresOS desktop efficiently through clean tools: CLIs and
MCP servers, as clean as the GitHub or Teams MCP servers. Not the usual way of driving a desktop with screenshots and
cursor moves. Each app gets a real, native integration.

**Every app, every feature.** The aim is that each app, with all of its features, is available to Claude Code as a
clean tool, so everything can be driven cleanly. Mail and Chrome are the first two apps, and the operations below are
examples, not a limit.

**What that means for the first apps:**

- **Mail:** commands to read, search, write, reply, send, and download attachments. A complete mail client for Claude,
  not only "read and prepare a reply that the owner sends".
- **Chrome:** Claude works **in the owner's own tab**, signed in as he is. It navigates without screenshots, because it
  knows which fields are where and which text is where on the page, and it can fill fields and click. A separate
  throwaway profile is not the goal; at most it is a test fixture.

**Where the verdict was narrower than this:**

- It made the first versions read-only ("leaves sending and deletion to the owner", "keep send/delete unavailable",
  "manual-send handoff"). Sending, writing and downloading attachments are part of the goal. The owner's earlier rule
  still stands: reading is free, and sending or deleting asks him first. That gate is built into the tool layer (gaps 1
  and 2 of the verdict), so sending is in scope from the start; it is not left out.
- It started Chrome in "a separate disposable profile" and framed the use as "explain this selected page". The goal is
  driving the owner's real tabs (the extension-bridge route the verdict already found: Playwright's extension can
  attach to an open tab), with page structure, fields and text, plus navigation and filling.
- It called the whole thing "a small assistant". It is the base for every later app integration, in the order of
  methods in `STATE.md` → Next 6 (the app's own API, then its own remote control, then the accessibility tree,
  screenshots last).

**What stays from the council:** the tool research (Playwright and its extension, Himalaya's JSON CLI, GreenMail for
tests), testing without the laptop, the 13 ranked gaps (they are the security checklist for doing this properly), the
deployment blockers (Flatpak for the daily account, session wiring, image qualification) and the open questions about
the mail provider and confirmation channel.

**The owner's rule for this project:** do it completely right, or leave it.
