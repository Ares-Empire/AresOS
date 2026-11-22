# 332: design note: the home's parts outside the game

Board brief 332. A design note for AresOS, written by one headless Claude Fable job with read-only tools (Read, Grep, Glob) in a checkout of the AresOS repo (the current directory). **Your whole answer is the note itself, in Markdown, starting with its `# ` title line.** The lead saves it as `docs/design/HOME-OUTSIDE.md`, commits it, and has it reviewed. Write nothing else before or after the note.

## Why this note

AresOS is a Linux OS (Bazzite-based, labwc compositor) whose home screen is a Minecraft world: the AresOS mod (`mod/`, Fabric, Minecraft 26.2) turns a flat world into a desktop, with app "gates" (logos built from blocks) and the hotbar as a taskbar. Release 28 put it on the owner's laptop, and his first try-out on 2026-11-21 asked for things that the current structure can't give, because the bar, search and app launching live **inside** the game:

1. **A switch to turn the home world off.** The home becomes a picture: a default one, black, or any picture of his. He wants it "especially when we are building, so Minecraft doesn't draw that much memory". The game takes about 1 GiB and its launcher Prism about 418 MiB while it runs, on a 16 GB laptop.
2. **A bar over full-screen apps.** A full-screen app hides the bar, which he likes. Moving the cursor to the bottom edge should slide the bar up, as on macOS. The world isn't drawn under a maximized app (the mod pauses it while covered), so the hotbar can't do this.
3. **Two screens.** With a monitor plugged in, the world goes to the monitor, and the laptop screen shows a picture behind its apps. Today a monitor plugged in after the start stays black, and the world holds the mouse.
4. **The taskbar behaves like one:** open apps are shown, open and active ones are marked, and a left click opens or brings back an app (today it starts a new instance). A right click gives the app's options (new window and so on).
5. **The sleeping world** (board T364, a priority after the fixes): when the world isn't needed, it becomes a still image and is frozen, or its memory goes to swap, and wakes early from signals. Its still image is the same picture as in 1 and 3.

His other answers that bind this note: he rejected holding the right mouse button to look around, and two look-around prototypes are being built (brief 328, `briefs/328-look-around.md` on branch `pkg/328-look-around` may not be in your checkout; the idea is "click to look" or "edge turning", with a free cursor that crosses screens). A click on the world must not hide a part-screen app; the world stays below the windows. The look of everything is already decided in `docs/design/COMPONENTS.md`: the game's own textures by default (look B, loaded at run time from the AresOS Prism instance, never committed), with our own art (A, also the fallback) or the game's buttons (C) as a setting.

The full try-out list and his answers: `docs/HUB-HANDOFF.md`, section "The owner's first try-out of R28".

## Who owns what (agreed 2026-11-21)

- **`linux-desktop`** owns the OS surfaces: labwc and its rules, the per-output covering rule (T372/T373: the world counts as covered only when windows on its output fill that output's usable area), the picture behind the windows, the bar's layer-shell surface in the look, the window frame (WINDOWS.md), the brightness and volume indicator (brief 320), and the status icons.
- **The hub (`linux-hub`)** owns the content: what the bar shows and does, search, launching, the app helper `aresos-shell` and its protocol with the mod, the mod itself, and the world-off switch's behaviour.
- **`linux-aresos`** owns the image and the supervisor `aresos-desktop` (with the hub for its home-screen parts).

The note decides the structure for both sides; `linux-desktop` adds its OS details after you.

## Read before writing

- `docs/design/HUB.md` (the home screen's design, the shell protocol `aresos-shell/1.x` in section 3.8 and later additions), `docs/design/COMPONENTS.md`, `docs/design/WINDOWS.md`, `docs/design/LAPTOP-HOME.md` (a native GTK home already exists for the laptop: learn what it is and whether it is the natural host for the picture, bar or search), `docs/design/OS-BASE.md` section 4 (the session, labwc rules).
- `STATE.md` (current state; read the hub, desktop and 53/23c entries), `docs/HUB-HANDOFF.md`.
- Code, as needed: `os/config/usr/libexec/aresos-shell` (the helper: windows, focus, covered, launch), `os/config/usr/libexec/aresos-desktop` (the supervisor: states, the game's start and stop, freeze), `os/labwc/` or `os/config/usr/share/aresos/labwc/` (rules), `mod/src/client/java/dev/aresos/client/` (HomeScreen, ShellFocusClient, HomePointer, WorldSearchScreen, AresOsClient), `briefs/320-indicator.md` (how a layer-shell surface in the look gets built), `briefs/53-laptop-home-build.md`, `briefs/318-*` and `reviews/318-thaw-watchdog/FINDINGS.md` (freezing the game).

## What the note must decide

1. **Where each part lives:** the bar (content and surface), search, launching, the open-app list with its marks, the app options menu, the picture behind the windows, notifications and toasts, and the world-off switch. For each: inside the game, in a native program (which one: the laptop home, a new one, the helper), or split, with the reason.
2. **One source of truth for apps and windows** that both the world (gates, hotbar) and the outside parts use, so nothing is kept twice. Name the protocol messages to add or change, with version bumps.
3. **The world-off switch:** what happens to the game and Prism (closed, frozen, or swapped), how the picture is chosen and shown, how the world comes back, and what the supervisor's states become. Memory numbers in both states.
4. **Two screens:** where the world goes on hotplug, what each output shows, how the free cursor crosses, and how covering and the bar work per output.
5. **The bar over full-screen apps:** reveal at the bottom edge, hide again, which output, and how it stays in the look (A/B/C) without the game running.
6. **The sleeping world:** how the still image, freezing and waking fit this structure (the note doesn't design swap or prefetch; it gives them their place).
7. **Migration in steps that keep things working:** the current in-game hotbar and search keep working until each replacement is ready. Cut it into packages with an owner each (hub, desktop, aresos), in order, with a rough size.
8. **Open questions for the owner**, each with a recommendation: only what he can judge from what he'll see or do. Technical calls you decide and justify.
9. **Risks and known limits,** including what happens on a 16 GB laptop when memory is full at wake time (his worry: the home must never kill his work).

## Rules for the note

- **Write "the owner"**, never a person's name; the repo is public. Use repo-relative paths, never home-directory paths.
- **Never plan to commit Mojang or Supercell assets.** Game textures are loaded at run time from the game's own files.
- **Plain, short sentences.** Prefer a table or a short list where it helps. State decisions as decisions, not menus. Mark anything you assume but couldn't verify in the code as an assumption.
- **The safety bar** (the project's decision 24): design against real harm (lost work, a dead session, a home that can't come back). Low-harm edge cases go under "Known limits".
- **Length:** as long as the decisions need and no longer; about 400 to 700 lines is the expected range.
