# Council: the AI-native control layer, before its first brief (2026-11-07)

A **planning** council: nothing is built yet. It must be free to say "don't build it" or "wait". Subject frozen at
`main` `4690074`. Method: `docs/REVIEW.md` → Councils, plus a cross-check round (each member reads the others'
answers before the chair merges them).

## The idea

`STATE.md` → Next 6 (owner idea, 2026-11-05): commands and an MCP server so that the always-on Claude session drives
the owner's apps **without screenshots or mouse moves**, the way git has a CLI.

- **Order of methods, cleanest first:**
  1. the service's own API (mail through the mail server: read, send, delete, attachments)
  2. the app's own remote control (Chrome DevTools protocol, D-Bus, our own mod)
  3. the accessibility tree (AT-SPI: one command lists an app's layout and fields, one fills them)
  4. screenshots only as a last resort
- **Rules:** reading is free; sending or deleting asks the owner first. Discord forbids automating personal accounts, so
  Discord is the owner's call.
- **Start:** mail and Chrome as the first two apps, tested in the VM. Prior art noted: HKUDS/CLI-Anything generates CLIs
  from open-source apps' source code (not closed apps).

**New since then (owner, 2026-11-07):** start now, before the first boot on the laptop. The laptop is busy with the
install (stages B and C), and Codex capacity is available until 2026-11-21. So the first briefs must be buildable and
testable **without the laptop**: in Linux containers on GitHub's standard runners (free for this public repo) and in
the CI virtual machine that boots the real image (`os/ci/vm.py`, `.github/workflows/os-image.yml`).

## What depends on this council

The first briefs: what the shared base is, which adapters come first, how they are tested, and what waits for the
first boot. Also anything that must be decided by the owner before the first brief.

## Read

- `README.md` ("Desktop and companion", "Open"), `STATE.md` (Next, owner decisions), `CLAUDE.md`, `AGENTS.md`
- `docs/design/OS-BASE.md`: only the sections on the session, users, apps and updates that you need
- `os/Containerfile`, `os/config/` (greetd, `aresos-session`, labwc), `os/packages.lock.json`, `os/manifest/`
- `os/ci/vm.py` and `.github/workflows/os-image.yml` (what the CI VM boots and checks today)
- the mod's app launching on Linux (`mod/`, e.g. `LinuxAppCatalogue`, still a stub)
- `HANDOFF.md`, top section (two GitHub settings currently missing)

## Facts and constraints

- **Session today:** greetd auto-login → labwc (Wayland) → the session script → Minecraft. **labwc or KWin is still
  open:** labwc does not tell other programs where windows are; KWin (already in Bazzite) is the main alternative. Say
  which parts of your proposal depend on that choice.
- **The always-on Claude session** is Claude Code running on AresOS (see the "help command" idea in README). It would
  reach the tools as an MCP server and/or a CLI. How the owner confirms a send or delete is open (the companion's chat
  bar, a phone push through the owner's existing push service, a terminal prompt, something else).
- **Unknown until the owner answers. Do not guess, and say where the answer changes the plan:**
  - which mail provider and protocol the real account uses (IMAP/SMTP, JMAP, a provider API, OAuth or password)
  - which apps beyond mail and Chrome matter most
- **Tests never use real accounts.** Mail tests run against a mail server inside the container.
- **Public repo:** no real addresses, hostnames, account names, tokens or captured traffic in code or fixtures.
  Reverse-engineering notes about closed apps go to a private repo. The local pre-push privacy check runs.
- **CI:** `GHCR_READ_TOKEN` and the package write access are missing until the owner restores them. Say which of your
  proposed tests would need either.
- **Workflow rules:** Codex builds on branches and opens PRs; the owner says "merge" for every merge; image rebuilds and
  publication need the owner. Files under `os/`, `mod/` and the install docs are shared with the install work in
  progress: say when a proposal must touch them.
- Claude Code already has an official Chrome extension (Claude in Chrome), and there are existing MCP servers for
  browsers, mail and accessibility. Check what exists before proposing to build it.

## Members (one question each)

1. **System:** What is the right shape? Process model, CLI and MCP (one, the other, or both, and why), the adapter
   interface, where it runs and how it is installed (in the image or per user), how Flatpak sandboxing and the session
   D-Bus affect it, how it is tested in containers and the CI VM now, what waits for the first boot, and what depends
   on labwc versus KWin. Should a macOS backend be possible later without building it now?
2. **Security and privacy:** How is "reading is free, sending asks first" enforced in the tool layer so that neither a
   prompt nor the agent itself can skip it? What counts as a send or a delete per adapter? Which confirmation channel
   can the agent not fake? How are prompt injections in read content (a mail, a web page asking the agent to send
   something) contained? **Chrome:** verify the current behaviour of remote debugging with sources (reportedly Chrome
   136+ ignores `--remote-debugging-port` on the default profile, and an open port gives any local process control of
   the signed-in browser), then choose between a separate profile, an extension bridge and a pipe-only transport.
   Where do credentials live? What could a malicious local process or a misled Claude session do?
3. **Skeptic:** What already exists that covers most of this (for example Chrome DevTools MCP, Playwright MCP, Claude in
   Chrome, mail MCP servers, AT-SPI tools or MCP servers, CLI-Anything, wtype or ydotool)? What is the cheapest path to
   most of the value: adopt, wrap, or build? What would be maintenance burden for one owner? Use web search and cite.
4. **Daily use:** In which concrete moments would the owner use this in AresOS (the companion taking over inside an app,
   the help command, mail, forms, the browser), and how often? Where would confirmations get annoying? What is the
   smallest first version the owner would notice in week one?

## Answer format (every member)

- Findings, most severe first. Each: the point in one line · a concrete scenario · the impact · the fix · the test or
  check that would catch it.
- **General case:** is this one instance of a wider problem? One sentence.
- **Smallest useful version:** the first two or three briefs, in order, each testable without the laptop.
- **Waits for the first boot:** what, and why.
- **Questions only the owner can answer.**
- Last line: `BUILD`, `WAIT (<trigger>)` or `DON'T BUILD`.

Read only; do not edit any files. Mark each claim as checked (with the file or source) or assumed.
