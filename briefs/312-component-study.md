# 312: the Minecraft-look component study

**Status:** launched Thursday 2026-11-19 after the R28 cut, on one Fable agent per step (`mac-capacity`, 2026-11-18 and 2026-11-19: design work that isn't fully scoped yet). Brief reviewed once by Codex (Claude allowance was tight, so no Claude review; the lead's rule for brief reviews).

**Goal:** one written and drawn design for how AresOS's normal desktop pieces look and behave, so each piece can be built from it in its own package: brightness and volume indicators, window buttons and frame, minimize, split screen and window layouts, app switching, an app overview, and the password window.

**Output:** a design document, sample art, and mockups. No image, `rc.xml`, theme or mod changes.

- The document: `docs/design/COMPONENTS.md`.
- Version A's sprites and mockups: `docs/design/components/` (PNG, each on the pixel grid below; keep the whole folder under about 3 MB).
- Version B's mockups: only in `~/.local/state/aresos-dev/312-look-b/`, outside every repo. The lead puts them on a private artifact page for Patrik. They never go into the repo, the pull request, a commit message or an issue.
- Progress: `reviews/312-component-study/PROGRESS.md` (see "Steps").
- Branch `pkg/312-component-study`, worktree `~/AresOS-312-component-study`, draft PR into `main`. Never merge or push to `main`.

## The owner's direction

- The Minecraft look comes first across AresOS, matching the hub. An Ares-apps-style version 2 comes later.
- Study existing operating systems and lean on Windows: buttons top right, easy layout management from the top of the window.
- In his words, not "just replicate windows in a different color but actually make a unique, useful OS". Propose good features of our own.
- He answers best when a question is about something he will see or do. Technical calls that can change later are yours: decide them with a reason and record them.

## Order

The brightness and volume indicator comes first (`linux-aresos`, 2026-11-18). It is designed in full, in both looks, before the other pieces.

## Two looks, side by side, for Patrik to choose

Patrik isn't sure our own pixel art is the right call: "currently its just my private OS … maybe we decide when we know what the look difference is" (relayed by `linux-hub`, 2026-11-19). The study shows both versions on the same pieces, says what each costs, and recommends one. He chooses.

- **A: our own pixel art,** committed to the repo.
- **B: Minecraft's real textures and font, loaded at runtime** from the Minecraft that the AresOS desktop installs through Prism (the managed instance `AresDesktop` under `~/.local/share/PrismLauncher/instances/`, created by `os/config/usr/libexec/aresos-desktop`).
  - They are copied at first start into a cache in his home folder, never into the repo or the image.
  - If the game isn't there, B falls back to A, so A's art has to exist either way.

For B, the design must say:
- which files it reads from the version's jar (paths inside the jar), and when it copies them;
- what happens when Minecraft updates, or when a file moves or disappears;
- that at runtime it reads only the AresOS Prism instance's game files, read-only, and never `~/.minecraft` or `~/.lunarclient` (repo hard rule 3);
- that B works only on a machine with the game installed, and what that means if AresOS is ever shared with anyone else.

**Drawing B's mockups during the study:** this laptop has no `AresDesktop` instance yet. Read B's textures and font read-only from the mod's development copy of the game, `~/.gradle/caches/fabric-loom/26.2/minecraft-client.jar` (and its assets under `~/.gradle/caches/fabric-loom/assets/` if the font needs them). Extract what you need into `~/.local/state/aresos-dev/312-look-b/` only. Never read `~/.minecraft` or `~/.lunarclient`.

## Function and look stay separate

Patrik: "at some point we wanna add the completely diff look in ares app style (not necessarily prio but just a thing once functionality is there)" (relayed by `mac-capacity`, 2026-11-18).

- Design every piece so its function is separate from its look. Colours, shapes, pixel art and fonts live in a replaceable theme layer, so the Ares-style look can come later without rebuilding the pieces.
- Keep it simple: one theme today and no theme switcher. Do not design or build the Ares-style look now.
- Versions A and B should both fit this layer, as two sets of art for the same pieces.
- Say what this separation costs, and where the theme layer lives for each kind of piece: labwc's theme (`themerc` and its button images), the GTK/layer-shell programs the pieces need, and the mod's widgets.

## Fixed limits

**Art**
- Nothing from Mojang is ever committed or built into the image (repo hard rule 2; the repo is public). Version A's art is not traced from Mojang's, and B's extracted files never enter the repo.
- No pixel font or Minecraft-look palette exists yet. Propose them for version A. Any font must have a licence we can ship (OFL or similar): say the licence and the official source, and check that the font isn't derived from Minecraft's. Candidate fonts may be downloaded into a scratch folder outside the repo; don't commit a font in this package.
- Draw on an integer pixel grid that maps to Minecraft's GUI scale (1 GUI unit = 1 art pixel × scale), with button height 20 and 9-slice sprites, so the mod can later ship the same sprites as its widget textures.
- It must be readable at 1920×1080 and at the laptop's own screen size and GUI scale. Find both (the dev client's `options.txt` has `guiScale:0`, which means automatic) and say which scale you assumed.

**Password window**
- It may change colours, font and frame.
- It keeps its label text and the title he checks, "Enter SSH Credentials" (ksshaskpass's own title).
- It sits on the owner tools' checked path: design it, but mark its build as needing its own review.

**Focus and keys**
- Indicators and overlays never take keyboard focus, so the world doesn't lose the mouse or keys mid-move (package 40's focus rules).
- Never bind Super alone: it is reserved for the search over the world (boards #333 and #334, package 53d). Super plus another key is fine. Say which existing bindings in `os/config/usr/share/aresos/labwc/rc.xml` each new key would meet.
- Leave the `aresos.cover` and `aresos.laptop-home` exclusions from window tracking alone, and the focus-return rules (`return_to_desktop`, the screen rule, the `view_focus` gate).

**The world and window layouts**
- The world is always the maximized bottom window and is the desktop. It never takes part in a window layout.
- A layout covers the world only when the windows on the world's output together cover that output's usable area. This is decided per output: with 23c the world can be on the external monitor, and the laptop screen's layout then doesn't matter.
- A partial layout, such as one app on half the screen, doesn't cover, so the world stays visible and keeps running.
- The split-screen package writes this rule into `Windows.covering`'s docstring and tests (`os/config/usr/libexec/aresos-shell`, about line 2636). Today it counts only maximized or fullscreen windows. The hub's board item #373 carries the rule for the sleeping world (#364).
- Alt+Tab reaches every app, and activating a covered world minimizes what covers it (HUB.md section 1).
- The overview must not rely on a live world thumbnail, because the world may later sleep as a still image (#364).

**Ownership**
- `os/config/usr/share/themes/Ares-Crown/` is ours to replace or reskin later. `os/ci/image-checks.sh` (about line 770) pins its checksum and its 37 files, so the package that changes the theme moves that pin in the same commit. Say what else the theme drives: `gschemas.compiled`, the title font through the font cache, and package 31's report (`reviews/31-window-frame/`).
- Every later `rc.xml` change and `os/` diff goes to `linux-aresos` first.
- Leave alone: `mod/`, `/usr/libexec/aresos-laptop-home`, `/usr/share/aresos/laptop-home/`.
- An app overview can reuse the view interface from `aresos-shell` 1.2: a hello with the view token (from 23c), `list_apps`, `open_app`, `apps_running`. Up to four views (LAPTOP-HOME.md section 5).

## What exists today (checked against main on 2026-11-19)

**The look around it**
- In the game the world is always at noon with the weather off (HUB.md 2.1), so the home is a bright day look. Patrik chose day over night for the laptop home too, because "the superflat world isn't dark" (LAPTOP-HOME.md section 11).
- Ares-Crown colours (`os/config/usr/share/themes/Ares-Crown/labwc/themerc`, LAPTOP-HOME.md 2.5): wall `#0d0d10`, ink `#f3f1ea`, quiet ink `#a6a39a` and `#6f6b62`, gold `#cfa24f` and `#edca77`.
- App group colours (`mod/src/main/java/dev/aresos/catalogue/AppGroup.java`): `#3AB3DA`, `#FF6257`, `#C774F2`, `#FED83D`.
- The window frame is described in `docs/design/WINDOWS.md`; package 31's screenshots are in `reviews/31-window-frame/`.
- Fonts in `os/config/usr/share/fonts/aresos/`: Space Grotesk (OFL). R29's image package adds JetBrains Mono (OFL), agreed for package 53.

**How the mod draws its interface**
- Vanilla widgets only: `Button.builder` (200 wide, 20 high in GUI units) in `mod/src/client/java/dev/aresos/client/AresOsMenuScreen.java`, `EditBox` for the Apps search in `AppsScreen.java`, and vanilla's header, footer and menu background blur.
- Its own drawing is flat translucent white: `0x50FFFFFF` for dividers, `0x30FFFFFF` for row hover (`AppsScreen.java`).
- Textures and font come from the game at runtime and are never committed.

**The desktop today**
- labwc's title bar has the standard buttons (`menu:iconify,max,close`), and Alt+Tab goes through `NextWindow` (`rc.xml`).
- The image has no indicators, overview or layout menu.

**Earlier choices of Patrik's to respect**
- Package 48 kept vanilla buttons on purpose ("an AresOS look of its own can follow once you've tried it").
- Apps are "dimmed until used, lit when open".
- "Apps don't necessarily have to be Minecraft houses".
- No Speed effect, because it widens the field of view.

## What the document contains

1. **The theme layer:** what is function and what is look for each piece, where the look lives, and its cost.
2. **Version A's palette and pixel font**, with licences, on the grid above.
3. **Each piece, in the order above:** what he sees and does (keys, clicks, where it appears on which screen), how it behaves with the world (focus, covering, the external monitor), and mockups in A and B. Lean on Windows where it helps; say where we do something better of our own.
4. **For each piece, what it is built from:** which program draws it (labwc theme, a layer-shell program, the mod), which existing interface it uses, and roughly how big its build package is.
5. **A against B:** what he would notice, what each costs to build and keep, the risks (B on game updates, B if AresOS is shared), and a recommendation.
6. **Questions for Patrik:** only things he can judge from what he will see, each as a choice between pictures or behaviours, one short sentence each, with a recommendation. The lead posts them; you never run `board`.
7. **What the next hub session checks** (below), with the answer for each.

## What the next hub session checks

- No Mojang textures or font in any committed file or in the image, and version A's art is not traced from them.
- Sprites sit on the GUI grid, so the mod can adopt them.
- It sits next to the noon world and the laptop home's day street without clashing.
- Readable at 1920×1080 and at the laptop's GUI scale.
- The password window keeps its label and "Enter SSH Credentials".
- Indicators and overlays never take keyboard focus.
- Super stays free for the search over the world.

## Steps

One fresh agent per step. Each step commits and pushes, and keeps `reviews/312-component-study/PROGRESS.md` up to date: what is done, what is left in order, and what the files don't show. Stop after your step's work, even if there is room for more.

1. **Foundations and the first piece:** read, then the theme layer, version A's palette and font, the grid and the assumed scales, and the brightness and volume indicator in full in A and B. Open the draft PR.
2. **Windows:** window buttons and frame, minimize, split screen and window layouts, app switching.
3. **The rest and the decision:** the app overview, the password window, A against B with the recommendation, the questions for Patrik, and the checks list. Delete `PROGRESS.md` and put its last state into the PR's description.

## Tools

- Draw with Python's PIL (12.3), ImageMagick (`magick`), or HTML rendered by headless Chrome (`/usr/bin/google-chrome-stable --headless --screenshot`). Keep pixel art crisp: integer scales only, nearest-neighbour scaling.
- Committed screenshots in `reviews/` (for example `reviews/31-window-frame/`, `reviews/32-flat-home/`, `reviews/48-home-menu/`) show the world and the menus today. Don't start the game or a client test, and don't take screenshots of Patrik's screen.
- Run nothing with `sudo`.

## Read before designing

`~/ares-empire/EMPIRE.md` (design language), `CLAUDE.md`, `AGENTS.md`, `STATE.md` (the sections on 23c, 53 and 311), `docs/design/HUB.md` (sections 1 and 2), `docs/design/LAPTOP-HOME.md` (sections 2, 5 and 11), `docs/design/WINDOWS.md`. Read only the sections you need; these files are long.

**Model:** Fable 5.2 for every step: unscoped design work, per the repo's rule and `mac-capacity`'s confirmation.
