# AresOS

AresOS is an operating system being built around Minecraft Java: Linux, based on Bazzite, that starts straight into a
Minecraft world instead of a normal desktop. A Fabric mod turns that world into the app launcher. Apps open over the
game, and closing one puts you back where you stood.

## Status (2026-11-12)

AresOS is installed on the owner's laptop, on its own SSD next to Windows. It starts into a minimal desktop with a
terminal; the game and the apps aren't in it yet.

- **The mod** works in Minecraft's development client on Windows. Right-click an app item and the installed Windows app
  or website opens. Walk into a block logo and its app opens. The Nether home, Live mode (you can't die) and Build mode
  (creative), each with its own inventory, work. Unit tests, server game tests and client game tests cover it; they
  run on Windows, not in CI.
- **The OS image** is a Bazzite derivative (`bazzite-nvidia-open`) that starts into a minimal labwc session with a
  terminal. GitHub Actions builds it, boots it in virtual machines, and tests the recovery login, the switch from stock
  Bazzite and the rollback. A signed release exists; it is private for now.
- **The install** onto a second SSD, next to a Windows drive that is never written, was rehearsed in CI virtual
  machines with the real Bazzite installer, then done on the owner's laptop on 2026-11-08/09 with the install guide,
  the emergency card and the install tools. Graphics, the network, sound and the touchpad work there; brightness and
  the power button don't yet.
- **The control layer** (apps as tools for a Claude Code session): the base service is merged and tested with a
  made-up test app. Mail is merged: Claude can read, search, sort and send mail, and every send, delete and
  unsubscribe asks first. It is tested against test mail servers, not yet with a real account. The Chrome tool is
  built and in review.

Not done yet: Minecraft inside the image, opening apps on Linux (the mod waits for a helper in the OS), and the first
update of the installed laptop to a new release, which is the next step.

## How it works

- **The game is real Minecraft Java.** Nothing is rebuilt. A Fabric mod changes how the AresOS world behaves.
- **Apps are items.** Pinned apps sit in the hotbar and all others in the inventory, each with a pixel icon made from
  the app's real icon, or a plain Minecraft item when there is none. Right-click one to open it. Big block logos in
  the world open their app when you walk into them.
- **Home is the Nether.** Every start puts you at your home spot. In Live mode you can't die. G switches to Build mode
  (creative) for building, and the app hotbar comes back when you switch back.
- **Only the AresOS world follows these rules.** Every other world plays like normal Minecraft, and normal Minecraft
  will be an app you open from AresOS.
- **Underneath is Linux.** The image is defined in this repository on top of Bazzite, a gaming-focused Fedora with
  NVIDIA drivers. The previous version stays on disk, so a bad update can be rolled back.
- **Apps as tools for Claude Code** (being built). A Claude Code session on AresOS uses Mail, Chrome and later apps
  through command-line and MCP tools. The tools ask before an explicit send, delete or submit; in Chrome, a send that
  a page itself starts after an ordinary click is not held back.

## What's in the repository

| Path | What it holds |
|---|---|
| `mod/` | The Fabric mod for Minecraft Java 26.2 (Java 25), with its tests. |
| `os/` | The AresOS image: Containerfile, build script, policy, install tools and the CI test harness. |
| `control/` | The control layer: the tool service, its command-line and MCP side, and its checks. |
| `docs/` | The design, the install guide, the emergency card, the control-layer plan and the workflow. |
| `briefs/` | One task per change, as handed to Codex. Frozen once it has run. |
| `reviews/` | Reports, reviews, screenshots and test evidence for each change, and council decisions. |
| `.github/workflows/` | CI: the OS image build and VM tests, and the control-layer tests. |
| `STATE.md`, `HANDOFF.md`, `CLAUDE.md`, `AGENTS.md` | Where the work stands, and the working rules for Claude and Codex. |

## Build and try it

The mod needs Java 25; the Gradle wrapper is included. From `mod/`:

```sh
./gradlew build               # unit tests and server game tests
./gradlew runClientGameTest   # client game tests; opens a Minecraft window
./gradlew runClient           # the development client
```

On Windows in PowerShell, use `.\gradlew.bat`. The client game tests write their screenshots into `reviews/`;
`git checkout -- ../reviews/` (from `mod/`) puts the committed ones back. In the development client, click **AresOS** above
Singleplayer to create the Nether home. Opening apps works on Windows only for now. More in
[mod/README.md](mod/README.md).

The OS image is built and tested by `.github/workflows/os-image.yml` on GitHub Actions, started by hand. Details are
in [os/README.md](os/README.md), the install in [docs/INSTALL.md](docs/INSTALL.md), and the ways back if something
goes wrong in [docs/EMERGENCY.md](docs/EMERGENCY.md). The control layer's tests run in a disposable Fedora container
on GitHub Actions (`control/ci/test.sh`); the script installs packages, so run it only inside a container. More in
[control/README.md](control/README.md).

## How it's built

Each change starts as a brief in `briefs/`. Codex builds it in its own git worktree and opens a pull request, a
separate Codex run reviews it against the brief, and Claude checks the result and merges it. Reports, reviews and
screenshots are kept in `reviews/`. The full loop is in [docs/WORKFLOW.md](docs/WORKFLOW.md).

## Design

- [docs/design/DESIGN.md](docs/design/DESIGN.md): the full design. How Minecraft maps to the OS, the Nether home,
  game rules, shaders, desktop and companion ideas, phases, open questions and safety rules.
- [docs/design/OS-BASE.md](docs/design/OS-BASE.md): the Linux layer.
- The control layer: its [plan](docs/control/PLAN.md) and its [design](docs/design/CONTROL.md).

## Minecraft

NOT AN OFFICIAL MINECRAFT PRODUCT. NOT APPROVED BY OR ASSOCIATED WITH MOJANG OR MICROSOFT.

No Mojang code or assets are in this repository. Textures load at runtime from the player's own copy of the game.

## License

Free to use, change and share for non-commercial purposes, such as study, research, hobby projects, schools and
charities, under the [PolyForm Noncommercial License 1.0.0](LICENSE.md). Commercial use, also inside a company, needs
permission: [ares-empire.de/contact](https://www.ares-empire.de/contact). Until 2026-11-08 the mod in `mod/` was under
CC0; copies taken before then keep that licence.

The licence covers the code. It does not cover the Ares names or the screenshots. Parts from others keep their own
licences:

- The Gradle wrapper (`mod/gradlew`, `mod/gradlew.bat`, `mod/gradle/wrapper/`): Apache-2.0.
- Everything kept as test evidence under `os/manifest/ci/`: files and source archives copied from other projects,
  including the Bazzite and Fedora installers, the Linux kernel, QEMU, systemd, util-linux, coreutils, glibc, OSTree,
  EDK II and the cosign installer (`os/manifest/ci/14/14zz-cosign/`, Apache-2.0, its `LICENSE` beside it). Each keeps
  its project's own licence and notices, such as GPL-2.0-only for the kernel's files and BSD-2-Clause-Patent for
  EDK II.
