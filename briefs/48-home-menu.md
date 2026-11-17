# 48: The Esc menu and the first start

Board #282 (its first point) and #289's leftover nit. Empire brief 299.

The owner, 2026-11-15: "Its genuinely a homescreen. technically its a minecraft world but it doesnt "behave" like one. I dont start it via a launcher or game, I dont esc to close it. its the actual homescreen of this OS, like the homescreen of windows."

Two places still behave like a game:

- **Esc** in the home screen opens Minecraft's own game menu. It has Save and Quit (which leaves the home screen for a title screen), Open to LAN, Advancements, Statistics, and the feedback and bug-report links.
- **The first start.** When AresHub is missing, package 23's supervisor starts the game without a world (its `setup` mode). He then makes his home on the title screen with the AresOS button. That was his answer on board #168, before he said the home screen should simply be there.

**Builder:** a Claude agent on Opus. The work is screens made from the game's own widgets, in the Apps screen's style, plus flows with tests. Codex's allowance is kept for 45 and 47 (`mac-capacity`, 2026-11-16). **Review:** a fresh reviewer that isn't the builder (Codex `gpt-6-astra` `high` from Tuesday, otherwise Opus). The world switch in A.5 is the part to check hardest.

## A. The AresOS menu replaces the game menu in the home screen

**Where:** in a game the session started (`HomeScreen.session()`: the supervisor or `run-hub.sh`), in a desktop world (`DesktopWorld`), whether or not the app helper is connected right now, because a helper that dropped must not bring Save and Quit back. Elsewhere Esc opens Minecraft's game menu as before:
- a normal world;
- the plain development client;
- a game the session didn't start.

Catch every way the game opens its menu there (the Esc key, F3+Esc, anything else you find), not only the key. Say in the report how.

**What's in it**, top to bottom, as a centred column like the game menu:

1. The title "AresOS".
2. **Back to the world.** Esc does the same.
3. **Apps…**: the Apps screen. Its Done comes back to this menu.
4. **Settings…**: Minecraft's own options screen (video, sound, controls, language, accessibility). Its Done comes back to this menu. The session's rules for fullscreen and F11 stay as package 40 made them.
5. **New home…**: the home choice, the existing `HomeCreateScreen`: Flat first; Nether with the seed field and the quick picks 49, 50 and 26. Create asks once:

   > "Keep this home under a dated name and make the new one? Nothing is deleted: the old home stays in your saves."

   Then:
   - the world closes with no title screen in between (a short "Making your new home…" screen);
   - the current AresHub is saved and moved to `AresHub-<date>` (`HomeButton.archive`);
   - the new one is created with the same settings and manifest as today's create flow;
   - he arrives in it in Live mode.

   **When it fails:** whatever fails, he ends up in a home and never on the title screen or without a world. That is the old home if the new one can't be made (move it back if needed), with a chat line saying why. Keep the moment with no AresHub on disk as short as you can. If the game dies in that moment, the supervisor's next start finds the hub missing and says so (its `world_missing` reason). Write down in the report how short that moment is.
6. **One hint line** with the keys as they are bound, for example "G switches Live and Build · E opens the inventory and Apps…".

**Not in it:** Save and Quit, Disconnect, Open to LAN, Advancements, Statistics, Give Feedback, Report Bugs, server links, player reporting.

**How it behaves:**
- **It doesn't pause the world.** Like the Apps screen and like a desktop's start menu, the world keeps moving behind it. The Settings screen may pause as it does in the game.
- **Its look is the Apps screen's:** the game's buttons, the same background over the world, 200-wide buttons as in the game menu. It must fit the smallest GUI the game allows (240 high).
- **G while it's open** says "Close the menu before switching AresOS mode", as `AresOsClient.modeKeyInMenu` does for the game menu.
- **Focus loss** still opens nothing in the home screen (package 40). `FOCUS_RETURN`'s handling of the game menu outside the home screen stays.

## B. The first start: the home is just there

- **Creating it:** a game the session started that reaches the title screen while no `AresHub` folder exists creates the flat home at once. It takes `HomeButton.createFlat`'s path, with the same settings and manifest. The title screen doesn't show (one frame at most; the game's own loading screens are fine), and he arrives in Live mode in the flat home. The Nether home and the seed choice are one Esc away (A.5).
- **Only then:** this happens once per game start, and only when the folder doesn't exist at all. An existing AresHub, damaged or not, and every other save are never touched. If creating fails, the error screen stays as today, and its OK leads to the title screen with the AresOS button, so the supervisor's first-start text still works as the fallback.
- **Outside a session** (the plain development client, any other launcher), the title screen and its AresOS button stay as today.
- **The supervisor's window text in `setup` mode** ("On the title screen click AresOS…") and `forget_hub`'s message are `linux-aresos`'s (`os/`). Don't change them. Write the new behaviour in the report in a form `linux-aresos` can take over.

## C. What the supervisor sees during a new home (read only)

Read `os/config/usr/libexec/aresos-desktop` (`on_helper_status`, `ready`, `check_world`, the start timeout of 120 s, package 23b's start-up cover) and package 46's brief (`save_world` answers `no_world` with no world open). Confirm the switch in A.5 trips nothing:
- leaving the world sends heartbeats with `ready:false`, which moves the supervisor from IN_WORLD to STARTING;
- the new world's `world_ready` brings it back;
- `check_world` must never see a half-made AresHub as damaged.

If something on the supervisor's side should change, describe it in the report for `linux-aresos`. Nothing under `os/` changes in this package.

## D. Package 40's leftover nit

The Apps screen's `pressed` (REVIEW-3 nit 1 in `reviews/40-real-home/REVIEW-3.md`): clear it in `init()` and on every left press that doesn't land on a row, so a release swallowed by the loading screen can't pick an app up later.

## E. Docs

- `docs/design/HUB.md`:
  - add a short section on the AresOS menu and the first start;
  - fix the line "Esc still opens the game menu" in package 40's corrections;
  - replace "the package for the Esc menu that follows looks at Live's rules again" with: Live's rules wait for his try-out (#282).
- `mod/README.md`: fix whatever describes the title screen as the way in.

## Not in this package

- **Power** (sleep, restart, shut down) in the menu: it needs package 25's clean stop.
- **Opening an older home** from the menu.
- **Live's rules**, which wait for his try-out.
- **The supervisor's texts**, which are `linux-aresos`'s.
- **The monitor** (23c) and **the laptop home** (44).

## Tests

**Client game tests** (a new class, plus updates to the existing ones that expect the game menu on Esc in a home, such as `HomeScreenClientGameTest`):
- In a session's desktop world:
  - Esc opens the AresOS menu, never `PauseScreen`, and it has exactly the items above;
  - Back and Esc return to the world;
  - the game time moves on while the menu is open.
- In a normal world, and with the session flag off, Esc opens `PauseScreen` as before.
- Apps… and Settings… open and come back to the menu.
- **New home:**
  - From a flat home with a block placed just before: a Nether home with seed 50. Then check: a new AresHub is open, `AresHub-<date>` exists and holds the block, and no `TitleScreen` was set anywhere in between (record every screen set).
  - Cancel changes nothing.
  - A failure you inject in the middle brings him back to the old home with the chat line.
- **First start:**
  - Session on and no AresHub: the flat home is created and open, with no `TitleScreen` shown past one frame.
  - With an AresHub present, nothing is created automatically.
  - With the session off, the title screen with the AresOS button shows as today.

**Unit tests** for any logic you can pull out of the screens: the gate, and what the first start decides to do.

**Screenshots:** the menu over the flat home at 1280×720 and at the smallest GUI, in `reviews/48-home-menu/screenshots/`.

## Rules

- **Setup:** `AGENTS.md` applies. Worktree `~/AresOS-48-home-menu`, branch `pkg/48-home-menu`, from main. Merge `origin/main` into the branch before the hosted checks.
- **What changes:** only `mod/`, `docs/design/HUB.md`, and your files under `reviews/48-home-menu/`. Nothing under `os/`.
- **Game runs:**
  - Only through `mod/dev/client-test.sh` (the lock, one game at a time, 6 GiB free); another builder may hold the lock, so let it wait.
  - Never `./gradlew` yourself, never `--force`. Never the whole `os/tests` suite on the laptop.
  - Client tests rewrite tracked screenshots, so run `git checkout -- reviews/` afterwards and keep your own files.
- **Headless only**, never `WAYLAND_DISPLAY=wayland-0`.
- **Off limits:** never touch `~/.minecraft`, `~/.lunarclient`, Lunar Client or `~/AresOS-try`. Stop only processes you started, by PID.
- **The repo is public:** no personal data, no Mojang assets (game screenshots from the tests are fine, as in earlier packages).
- **Anything that changes how the home screen feels**, beyond what this brief decides, is a `JUDGMENT-CALL` in the report and the PR.
- **Report** in `reviews/48-home-menu/REPORT.md` (a Claude builder writes it into `PROGRESS.md`; the lead commits it as `REPORT.md`).
- **Finish:** open a PR "Package 48: the Esc menu and the first start". Never merge, never push to main, never `--no-verify`.
