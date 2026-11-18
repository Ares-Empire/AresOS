# 312: the Minecraft-look component study (draft, not launched)

**Status:** input notes collected on 2026-11-18 and 2026-11-19. Launch after the R28 cut (Thursday 2026-11-19, 12:00), on one Fable agent (`mac-capacity`, 2026-11-18). Finish the brief before launching, and check these notes against the code then.

**Goal:** one written and drawn design for how AresOS's normal desktop pieces look and behave, so each piece can be built from it: brightness and volume indicators, window buttons and frame, minimize, split screen and window layouts, app switching, an app overview, and the password window.

**Output:** a design document and sample art only. No image, `rc.xml` or mod changes.

## The owner's direction

- The Minecraft look comes first across AresOS, matching the hub. An Ares-apps-style version 2 comes later.
- Study existing operating systems and lean on Windows: buttons top right, easy layout management from the top of the window.
- In his words, not "just replicate windows in a different color but actually make a unique, useful OS". Propose good features of our own.
- Design questions go to him with `board ask`, each explaining what it is about.

## Order

The brightness and volume indicator comes first (`linux-aresos`, 2026-11-18).

## Fixed limits

**Art**
- Our own pixel art only. No Mojang textures or font, not even traced. The repo is public.
- No pixel font or Minecraft-look palette exists yet. The study proposes them, and any font must have a licence we can ship.
- Draw on an integer pixel grid that maps to Minecraft's GUI scale (1 GUI unit = 1 art pixel × scale), with button height 20 and 9-slice sprites, so the mod can later ship the same sprites as its widget textures.
- It must be readable at 1920×1080 and at the laptop's GUI scale.

**Password window**
- It may change colours, font and frame.
- It keeps its label text and the title he checks, "Enter SSH Credentials".
- It sits on the owner tools' checked path and gets its own review.

**Focus and keys**
- Indicators and overlays never take keyboard focus, so the world doesn't lose the mouse or keys mid-move (package 40's focus rules).
- Never bind Super alone: it is reserved for the search over the world (boards #333 and #334, package 53d). Super plus another key is fine.
- Leave the `aresos.cover` and `aresos.laptop-home` exclusions from window tracking alone, and the focus-return rules (`return_to_desktop`, the screen rule, the `view_focus` gate).

**The world and window layouts**
- The world is always the maximized bottom window and is the desktop. It never takes part in a window layout.
- A layout covers the world only when the windows on the world's output together cover that output's usable area. This is decided per output: with 23c the world can be on the external monitor, and the laptop screen's layout then doesn't matter.
- A partial layout, such as one app on half the screen, doesn't cover, so the world stays visible and keeps running.
- The split-screen package writes this rule into `Windows.covering`'s docstring and tests. Today it counts only maximized or fullscreen windows. The hub's board item #373 carries the rule for the sleeping world (#364).
- Alt+Tab reaches every app, and activating a covered world minimizes what covers it (HUB.md section 1).
- The overview must not rely on a live world thumbnail, because the world may later sleep as a still image (#364).

**Ownership**
- `os/config/usr/share/themes/Ares-Crown/` is ours to replace or reskin. `os/ci/image-checks.sh` pins its checksum, so a theme change moves that pin in the same commit. Also check what else the theme drives: `gschemas.compiled`, the title font through the font cache, and package 31's report.
- Every `rc.xml` change and `os/` diff goes to `linux-aresos` first.
- Leave alone: `mod/`, `/usr/libexec/aresos-laptop-home`, `/usr/share/aresos/laptop-home/`.
- An app overview can reuse the view interface from `aresos-shell` 1.2: a hello with the view token (from 23c), `list_apps`, `open_app`, `apps_running`. Up to four views (LAPTOP-HOME.md section 5).

## What exists today

**The look around it**
- In the game the world is always at noon with the weather off (HUB.md 2.1), so the home is a bright day look. Patrik chose day over night for the laptop home too, because "the superflat world isn't dark" (LAPTOP-HOME.md section 11).
- Ares-Crown colours (`os/config/usr/share/themes/Ares-Crown/labwc/themerc`, LAPTOP-HOME.md around line 178): wall `#0d0d10`, ink `#f3f1ea`, quiet ink `#a6a39a` and `#6f6b62`, gold `#cfa24f` and `#edca77`.
- App group colours (`AppGroup`): `#3AB3DA`, `#FF6257`, `#C774F2`, `#FED83D`.
- The window frame is described in `docs/design/WINDOWS.md`.
- Fonts in `os/config/usr/share/fonts/aresos/`: Space Grotesk, and JetBrains Mono from R29 through package 53 (both OFL).

**How the mod draws its interface**
- Vanilla widgets only: `Button.builder` (200 wide, 20 high in GUI units) in `mod/src/client/java/dev/aresos/client/AresOsMenuScreen.java`, `EditBox` for the Apps search in `AppsScreen.java`, and vanilla's header, footer and menu background blur.
- Its own drawing is flat translucent white: `0x50FFFFFF` for dividers, `0x30FFFFFF` for row hover.
- Textures and font come from the game at runtime and are never committed.

**The desktop today**
- labwc's title bar has the standard buttons (`menu:iconify,max,close`), and Alt+Tab goes through `NextWindow`.
- The image has no indicators, overview or layout menu.

**Earlier choices of Patrik's to respect**
- Package 48 kept vanilla buttons on purpose ("an AresOS look of its own can follow once you've tried it").
- Apps are "dimmed until used, lit when open".
- "Apps don't necessarily have to be Minecraft houses".
- No Speed effect, because it widens the field of view.

## What the next hub session checks

- No Mojang textures or font, not even traced.
- Sprites sit on the GUI grid, so the mod can adopt them.
- It sits next to the noon world and the laptop home's day street without clashing.
- Readable at 1920×1080 and at the laptop's GUI scale.
- The password window keeps its label and "Enter SSH Credentials".
- Indicators and overlays never take keyboard focus.
- Super stays free for the search over the world.

## Read before designing

`~/ares-empire/EMPIRE.md`, `CLAUDE.md`, `STATE.md`, `HANDOFF.md`, `docs/design/HUB.md`, `docs/design/LAPTOP-HOME.md`, `docs/design/WINDOWS.md`.

**Model:** Fable 5.2: design work, per the repo's rule and `mac-capacity`'s confirmation.
