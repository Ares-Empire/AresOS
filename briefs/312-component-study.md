# 312: the Minecraft-look component study

**Status:** launched Thursday 2026-11-19 after the R28 cut, on one Fable agent per step (`mac-capacity`, 2026-11-18 and 2026-11-19: design work that isn't fully scoped yet). Brief reviewed once by Codex (gpt-6.2-sol, `reviews/312-component-study/BRIEF-REVIEW.md`: two blocking findings on keeping Mojang pixels private, fixed; its should-fixes folded in). No Claude review, since Claude's allowance is tight (the lead's rule for brief reviews).

**Goal:** one written and drawn design for how AresOS's normal desktop pieces look and behave, so each piece can be built from it in its own package: brightness and volume indicators, window buttons and frame, minimize, split screen and window layouts, app switching, an app overview, and the password window.

## Public and private: the rule that matters most

The repo is public, and nothing from Mojang may enter it (repo hard rule 2). The study has two looks (below), and B is made of Mojang's pixels. So:

- **Public** (committed, in the PR, its description and commit messages): text, version A's own art, and mockups made only of A's art on plain backgrounds or backdrops you draw yourself. B is described in words and referred to by mockup IDs (`B-01`, `B-02`, …), never shown.
- **Private** (never committed or attached anywhere): every image that contains a single pixel or glyph from the game. That includes B's mockups, any A-and-B comparison sheet, anything drawn over the game's world, and crops or composites of the game screenshots already in `reviews/`. These go only into `~/.local/state/aresos-dev/312-look-b/`, named `B-NN-<piece>.png` with a `B-INDEX.md` listing each ID, what it shows and the A mockup it pairs with. The lead (`linux-desktop`) authorizes this folder for the study, reads it after each step, and puts the images on a private artifact page for Patrik.
- **Before every push:** run `git diff --cached --stat` and `git status`, and confirm that nothing staged came from the game jar, the extracted files, or the private folder. Say in `PROGRESS.md` that you checked.

## Output

- The document: `docs/design/COMPONENTS.md`.
- Version A's sprites and mockups: `docs/design/components/` (PNG on the pixel grid below; the whole folder under about 3 MB).
- Version B's mockups: the private folder above.
- Progress: `reviews/312-component-study/PROGRESS.md` (see "Steps").
- Branch `pkg/312-component-study`, worktree `~/AresOS-312-component-study`, draft PR into `main`. Never merge or push to `main`.
- No image, `rc.xml`, theme, owner-tools or mod changes.

## The owner's direction

- The Minecraft look comes first across AresOS, matching the hub. An Ares-apps-style version 2 comes later.
- Study existing operating systems and lean on Windows: buttons top right, easy layout management from the top of the window.
- In his words, not "just replicate windows in a different color but actually make a unique, useful OS". Propose good features of our own.
- He answers best when a question is about something he will see or do. Technical calls that can change later are yours: decide them with a reason and record them.

## Two looks, side by side, for Patrik to choose

Patrik isn't sure our own pixel art is the right call: "currently its just my private OS … maybe we decide when we know what the look difference is" (relayed by `linux-hub`, 2026-11-19). The study shows both versions on the same pieces, says what each costs, and recommends one. He chooses.

- **A: our own pixel art,** committed to the repo. A starting point exists: package 31's unshipped "Ares-Block" study (`docs/design/WINDOWS.md`, "Ares-Block", and `reviews/window-design-v1/03-block.png`): flat greys, a 2×2 pixel grid, sunken button slots, and the OFL pixel font Jersey 10 (its tested file and checksum are in WINDOWS.md). Build on it or say why not.
- **B: Minecraft's real textures and font, loaded at runtime** from the game the AresOS desktop installs through Prism (the managed instance `AresDesktop`, created by `os/config/usr/libexec/aresos-desktop`; its version is pinned in `os/minecraft/desktop.lock.json`).
  - Copied at first start into a cache in his home folder, never into the repo or the image.
  - If the game isn't there, B falls back to A, so A's art has to exist either way.

**B's runtime contract,** which the document must spell out:
- where Prism keeps the pinned version's client jar and its asset objects, resolved from the managed instance (not by searching the disk), and which paths inside them B reads;
- when it copies them, how the cache notices a game update, and what happens when a file moves or disappears (fall back to A for that piece);
- which program draws each piece (labwc's theme, a layer-shell program, the mod) and how each one would use B's art. Minecraft's font is a bitmap font inside the jar, not an installed font that labwc or Qt can select by name: say how each renderer would get it, and its glyph coverage (German umlauts, at least);
- that at runtime it reads only the AresOS Prism instance's game files, read-only, and never `~/.minecraft` or `~/.lunarclient` (repo hard rule 3);
- that B works only on a machine with the game installed, and what that means if AresOS is ever shared with anyone else.

**Drawing B's mockups during the study:** this laptop has no `AresDesktop` instance yet. Read B's textures and font read-only from the mod's development copy of the game: `~/.gradle/caches/fabric-loom/26.2/minecraft-client.jar` and the asset index and objects under `~/.gradle/caches/fabric-loom/assets/`. Extract only into the private folder. If those files aren't there, draw no B mockups: describe B in words and tell the lead. Never fall back to `~/.minecraft`, `~/.lunarclient`, another checkout, or a download of the game.

## Function and look stay separate

Patrik: "at some point we wanna add the completely diff look in ares app style (not necessarily prio but just a thing once functionality is there)" (relayed by `mac-capacity`, 2026-11-18).

- Design every piece so its function is separate from its look. Colours, shapes, pixel art and fonts live in a replaceable theme layer, so the Ares-style look can come later without rebuilding the pieces.
- Keep it simple: one theme today and no theme switcher. Do not design or build the Ares-style look now.
- A and B should both fit this layer, as two sets of art for the same pieces.
- Say what this separation costs, and where the theme layer lives for each kind of piece.

## What each renderer can draw

Design within what exists, and name anything that needs new work:
- **labwc** draws only server-side frames (title bar, buttons, border) and its own window switcher, with the limits in `docs/design/WINDOWS.md` (button sizes and states, borders, the switcher's styling). Ares-Crown's buttons today are 44×36 (`themerc`).
- **Apps that draw their own bar** (Chrome, GTK header bars, libadwaita) keep their own controls; WINDOWS.md describes what we set for them.
- **Anything new** (indicators, a layout picker, an overview) is a layer-shell program or lives in the mod. Say which, and roughly how big its build is.
- For every sprite that more than one renderer uses: the source grid, the 9-slice insets, and the sizes and states (normal, hover, pressed, inactive) each renderer needs.

## Scales

Distinguish source pixels (the art), GUI units (Minecraft's: 1 unit = 1 source pixel × scale; buttons are 20 units high) and screen pixels. The laptop's screen is 1920×1080 (WINDOWS.md). Show each mockup at stated integer scales (for example 2× and 3×) and say which you'd ship. Patrik's effective game GUI scale isn't recorded; list it as something the lead confirms, not a question for him.

## Fixed limits

**Art**
- Version A's art is drawn from scratch, not traced from Mojang's.
- No Minecraft-look palette exists yet; propose one for A. Any font must have a licence we can ship (OFL or similar): give the licence, the official source and a SHA-256, and check that it isn't derived from Minecraft's font. Candidate fonts may be downloaded into a scratch folder outside the repo; don't commit a font in this package.
- Sprites sit on an integer grid that maps to Minecraft's GUI scale, with 9-slice buttons 20 GUI units high, so the mod can later ship the same sprites as its widget textures.

**Focus and input.** Two kinds of surface, with different rules:
- **Passive** (indicators, previews, hints): never take keyboard focus and never disturb the world's pointer capture, so the world doesn't lose the mouse or keys mid-move (package 40's focus rules).
- **Interactive** (the layout picker, app switching, the overview): for each, say who owns the keyboard while it is open, how Escape and cancel work, how selection works, and where focus returns afterwards. If one must leave the world's keyboard focus alone, name the route it needs (a compositor action, or input inside the game).

**Keys**
- Never bind Super alone. Today `rc.xml` has no lone-Super binding; package 23c will add `<keybind key="Super_L" onRelease="yes">` for the search over the world (LAPTOP-HOME.md around line 625; boards #333 and #334, package 53d). A new chord with Super must not open that search when Super is released. Super plus another key is otherwise fine.
- Check each proposed key against today's `os/config/usr/share/aresos/labwc/rc.xml` (lines 17 to 40: Super+Ctrl+Escape is the recovery terminal; Alt+Tab, Alt+F4; brightness and volume keys) and against 23c's Super binding.

**What the shell does today, and what is planned** (`os/config/usr/libexec/aresos-shell`)
- Today: `return_to_desktop`, the start-up cover (`aresos.cover`) excluded from covering, and the screen rule `closed_on_other_screen`, which applies only while a view is connected (`self.views`).
- Planned: the laptop home (`aresos.laptop-home`) will be excluded from window tracking once it exists (LAPTOP-HOME.md section 6). Preserve it then.
- Leave all of these alone.

**The world and window layouts**
- The world is always the maximized bottom window and is the desktop. It never takes part in a window layout or any of its slots.
- A layout covers the world only when the windows on the world's output together cover that output's usable area, decided per output (with 23c the world can be on the external monitor, and the laptop screen's layout then doesn't matter). A partial layout, such as one app on half the screen, doesn't cover, so the world stays visible and keeps running. Board #373 holds this rule for the hub.
- `Windows.covering` (`aresos-shell`, about line 2636) today counts only maximized or fullscreen windows, from flags and output membership, with no window geometry. Its list is also what gets minimized when the world is activated (about line 3800). The design must say where the geometry for the new rule comes from (labwc itself, or the layout feature's own state), which windows of a full layout are minimized when he returns to the world, and keep the known-output guard on minimizing. List the cases the build must test: full coverage, a gap, another output, an output not known yet.
- Alt+Tab reaches every app, and activating a covered world minimizes what covers it (HUB.md section 1).
- The overview must not rely on a live world image, because the world may later sleep as a still image (#364); use an original static picture of our own.

**The app overview.** The `aresos-shell` 1.2 view interface (LAPTOP-HOME.md section 5: a hello with the view token from 23c, `list_apps`, `open_app`, `apps_running`, up to four views) knows catalogue apps and which have windows, but has no per-window identity, thumbnail, minimized state, output, or activate-this-window call. Choose: an app catalogue with running status, or a window overview. For anything window-specific, name its source and how a window gets activated. Alt+Tab stays.

**The brightness and volume indicator** (first, `linux-aresos`, 2026-11-18). The keys are already bound in `rc.xml` (lines 23 to 29: brightness up and down, volume up and down, speaker mute, microphone mute). Define: which of these actions show it, the level and mute states it shows (speaker and microphone separately), what holding a key does, when it disappears, which screen it appears on (brightness belongs to the laptop panel, which may not be the screen he is looking at), and what it shows when there is no device to control. Use made-up values in mockups.

**Password window** (the owner tools' check, `docs/INSTALL.md` around line 269, `docs/OWNER-TOOLS.md`)
- Its title bar is ksshaskpass's fixed **Enter SSH Credentials**. Inside: the full label **AresOS owner tools `<8 hex>`: `<action>`** (for example `AresOS owner tools dcbc375f: install these tools, then check and title`), then **Password:**, **OK** and **Cancel**. Patrik compares the 8 characters against his phone.
- Show all of it in both looks, with a long action, and prove nothing is cut off or hard to read at the planned scales.
- labwc styles only its frame; the body is a Qt dialog. Say what styling the body would take, and mark its build as needing its own review on the owner tools' checked path.

**Ownership**
- `os/config/usr/share/themes/Ares-Crown/` is ours to replace or reskin later. `os/ci/image-checks.sh` (about line 770) pins its checksum and its 37 files; the package that changes the theme moves that pin in the same commit. Also say what else the theme touches: the GTK decoration override `zz-aresos.gschema.override` and its `gschemas.compiled` (checked in `os/ci/image-checks.sh` around line 781), the installed fonts through the font cache, and package 31's report (`reviews/31-window-frame/`).
- Every later `rc.xml` change and `os/` diff goes to `linux-aresos` first.
- Leave alone: `mod/`, `/usr/libexec/aresos-laptop-home`, `/usr/share/aresos/laptop-home/`.

## What exists today (checked against main on 2026-11-19)

- **The world:** the flat home is set to noon with the weather off when it is made (`mod/src/main/java/dev/aresos/world/FlatHome.java` around line 76; HUB.md 2.1), so the home looks like a bright day. Patrik chose day over night for the laptop home too, because "the superflat world isn't dark" (LAPTOP-HOME.md section 11).
- **Colours:** the Ares-Crown frame (`os/config/usr/share/themes/Ares-Crown/labwc/themerc`): wall `#0d0d10`, ink `#f3f1ea`, quiet ink `#a6a39a`, gold `#edca77` (hover). The laptop home's palette (LAPTOP-HOME.md 2.5) adds quiet ink `#6f6b62` and gold `#cfa24f`. App group colours (`mod/src/main/java/dev/aresos/catalogue/AppGroup.java`): `#3AB3DA`, `#FF6257`, `#C774F2`, `#FED83D`.
- **The window frame:** `docs/design/WINDOWS.md`; package 31's screenshots in `reviews/31-window-frame/`, and the earlier design options in `reviews/window-design-v1/`.
- **Fonts** in `os/config/usr/share/fonts/aresos/`: Space Grotesk (OFL). R29's image package adds JetBrains Mono (OFL), agreed for package 53.
- **The mod's interface:** vanilla widgets (`Button.builder`, 200 by 20 GUI units, in `AresOsMenuScreen.java`; `EditBox` for the Apps search; vanilla's header, footer and menu blur) with its own list drawing in `AppsScreen.java`: translucent white dividers (`0x50FFFFFF`) and row hover (`0x30FFFFFF`), item icons, and a check sprite. Its textures and font come from the game at runtime.
- **The desktop:** labwc's title bar has the standard buttons (`menu:iconify,max,close`), and Alt+Tab goes through `NextWindow`. No indicators, overview or layout menu.
- **Patrik's earlier choices to respect:** package 48 kept vanilla buttons on purpose; apps are "dimmed until used, lit when open"; "apps don't necessarily have to be Minecraft houses"; no Speed effect, because it widens the field of view.

## What the document contains

1. **The theme layer:** function and look for each piece, where the look lives, and its cost.
2. **Version A's palette and pixel font**, with licences, on the grid.
3. **Each piece, in order:** what he sees and does (keys, clicks, where and on which screen), how it behaves with the world (focus, covering, the external monitor), A's mockups, and B's mockup IDs. Lean on Windows where it helps; say where we do something better of our own.
4. **For each piece, what it is built from:** which renderer, which existing interface, what new work it needs, and roughly how big its build package is.
5. **B's runtime contract** (above).
6. **A against B:** what he would notice, what each costs to build and keep, the risks (B on game updates, B if AresOS is shared), and a recommendation.
7. **Questions for Patrik:** only things he can judge from what he will see, each as a choice between pictures or behaviours, one short sentence each, with a recommendation and the mockup IDs to look at. The lead posts them; you never run `board`.
8. **What the next hub session checks** (below), with the answer for each.

## What the next hub session checks

- No Mojang textures or font in any committed file, the PR or the image, and A's art is not traced from them.
- Sprites sit on the GUI grid, so the mod can adopt them.
- It sits next to the noon world and the laptop home's day street without clashing.
- Readable at 1920×1080 and at the stated scales.
- The password window shows its full label and "Enter SSH Credentials".
- Passive surfaces never take keyboard focus; interactive ones say who owns input.
- Super stays free for the search over the world.

## Steps

One fresh agent per step. Each step commits, pushes, and keeps `reviews/312-component-study/PROGRESS.md` up to date: what is done, what is left in order, what the files don't show, and which public sections and private mockup IDs are finished. Stop after your step's work, even if there is room for more.

1. **Foundations and the indicator:** read; the theme layer; A's palette and font (starting from Ares-Block); the grid and scales; B's runtime contract; the brightness and volume indicator in full, A and B. Open the draft PR.
2. **The window frame:** buttons and frame states in A and B, minimize and restore, what labwc can draw and what apps draw themselves.
3. **Layouts and switching:** split screen and window layouts with the covering rule's cases, and app switching.
4. **The overview, the password window, and the decision:** the overview, the password window, A against B with the recommendation, the questions, and the checks list. Delete `PROGRESS.md` and put its last state into the PR's description.

## Tools and limits on what you run

- Draw with Python's PIL (12.3) or ImageMagick (`magick`). Keep pixel art crisp: integer scales, nearest-neighbour scaling. If you need HTML, render it with headless Chrome using a fresh throwaway profile (`--user-data-dir=` a new folder under `/tmp`), never Patrik's.
- Work only from files and static mock values. Don't build the mod, run Gradle, start the game or a client test, take screenshots of Patrik's screen, or press or run the brightness, volume or password commands. Don't edit or reload the running session, the image, the theme, `rc.xml` or the mod. Run nothing with `sudo`.
- Committed screenshots in `reviews/` may be looked at for reference; any crop or composite of them is private (above).

## Read before designing

`~/ares-empire/EMPIRE.md` (the design language; readable on this machine), `CLAUDE.md`, `AGENTS.md`, `docs/design/WINDOWS.md`, `docs/design/HUB.md` (sections 1 and 2), `docs/design/LAPTOP-HOME.md` (sections 2, 5, 6 and 11), and `STATE.md` around lines 160 to 230 (R29, 23c, 53 and 311). Read only the sections you need; these files are long.

**Model:** Fable 5.2 for every step: unscoped design work, per the repo's rule and `mac-capacity`'s confirmation.
