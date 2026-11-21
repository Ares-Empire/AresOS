# 327: the home's first try-out fixes: tutorial off, nothing breaks in Live, Build mode in the Esc menu, a clear New home, the Terminal's logo

Board brief 327. These are five of the owner's findings from his first try-out of R28 on the laptop (2026-11-21), and he agreed to this plan in the session. The full list and his answers are in `docs/HUB-HANDOFF.md`, "The owner's first try-out of R28". This package takes only the small hub-side items; the pointer, the windows and the bar come later.

**Builder:** Codex `gpt-6.2-sol`, `xhigh` (a small, well-scoped hub package; the frontier model isn't needed). **Review:** a fresh Codex `gpt-6.2-astra` `high` context.

## What changes

1. **Minecraft's tutorial and onboarding messages are off in the home.**
   - **What he saw:** "minecraft sends me in game instructions and stuff ... rn it was 'punch a tree'". They don't fit a home screen.
   - **In a session's desktop world:** the tutorial hints (the "punch a tree", "move", "open your inventory" toasts), the recipe-unlocked toasts and the advancement toasts never show. The tutorial step is set to none for the AresOS game, so it stays off after a restart too.
   - **Toasts that stay:** the game's own system toasts (for example a failed save or world upload) and any the mod shows itself. His idea for later is to use toasts for AresOS news, so the mod's own toast path must keep working; add nothing for it now.
   - **Outside desktop worlds,** and in a game the session didn't start, the game behaves like vanilla.
2. **In Live mode no block of a desktop world can be broken.**
   - **What he saw:** "of the set blocks of the environment I dont think I should be able to break them. like the apps and grass etc. or maybe just if I enter build mode but not per default."
   - **Today:** in Live mode the logos, the home pad and the roads refuse to break (`WalkInZones`, `HubData.protection`), but the ground and the other blocks don't.
   - **Afterwards:** in Live mode in a desktop world, every block refuses to break, with one refusal line in the action bar. Logos and pad keep their own wording; any other block says "The home is protected. Press G or use Build mode in the menu to change it."
   - **Build mode** (G) stays the way to change the world, and works exactly as today.
   - **Scope: his own breaking only** (mining, through `PlayerBlockBreakEvents.BEFORE`). Explosions and other damage keep today's rules (`HubData.protectsFromExplosions`); he has no TNT in Live. Put that under Known limits. Don't add a blanket block-write veto: the town keeper must still be able to rebuild and refresh its blocks.
   - **Existing tests:** update the old Live-mining assertions (`FlatHomeGameTests` and `FlatHomeClientGameTest`) to the new rule, and keep their ownership and restart checks.
   - **Placing blocks** is unchanged.
   - **Outside desktop worlds,** nothing changes.
3. **Build mode in the Esc menu.**
   - **What he saw:** he didn't know Build mode exists. He suggested editing only in a build mode.
   - **The AresOS menu** (`AresOsMenuScreen`) gets a button that shows the current mode ("Build mode: Off" / "Build mode: On") and switches it exactly as G does, through the same code path. Its tooltip says: "In Build mode you can change the home's blocks. G switches it too."
   - **The switch** uses `ModeSwitchClient.requestToggle()` with the same network and pending checks as G, and its label follows the synced mode.
   - **Order:** place it with the existing buttons so the layout stays tidy at 1920×1080 and at the smallest supported window size.
4. **New home says what it does.**
   - **What he said:** "I actually like the menu. I am just not sure what new home does."
   - **The button** becomes "Start a new home…", with the tooltip "Builds a fresh home world and switches to it. Your current home is kept."
   - **The confirm screen** says the same in its own words. Package 48 saves and keeps the current home, then stages, checks and opens a fresh one (`HomeSwitch`, `HomeSwap`). The text follows the code; don't change the behaviour.
5. **The Terminal looks like the Terminal.**
   - **What he saw:** "the minecraft terminal app build is brown, terminal is black. also doesnt need white edges."
   - **Which one he means isn't certain.** It's most likely the Terminal's hotbar item: `LinuxAppCatalogue` falls back to a command block, which is brown with light edges. It may also be the Terminal's gate in the town. Check both with the resolved icon pixels (`terminal.json` → `foot.desktop`'s icon → the helper's cached PNG → `GatePicture`/`GatePalette`), and write in the report what each looked like and why.
   - **Afterwards:** both the hotbar item and the gate read as the Terminal: black or near-black, with its light symbol on the gate, and without white edges. For the hotbar, pick a vanilla item that looks like that and show it in a picture.
   - **A mod-owned Terminal picture is allowed** (under `mod/`) if the source icon itself causes the colours. Never change `os/` for it.
   - **If the cause is general** (the colour matching or border handling would do the same to other dark icons), fix it in general, and show before-and-after pictures of every starter app's logo, so a change to another logo is seen, not found later. If it's specific to the Terminal's icon, fix it there.
   - **Logos already built** in his world: say in the report whether they rebuild by themselves after the update, and if not, what he does to rebuild one.

## Docs

- **HUB.md:** the protection rule in Live mode, Build mode in the menu, the tutorial rule, and the logo cause if it was general.
- **HUB.md section 7** (the owner's notes): one line each for Build mode in the menu and the new New home wording.

## Tests

- **Unit tests** for the protection rule (Live and Build, desktop world and normal world, logo, pad, ground) and for the toast filter (which kinds are hidden, in and outside desktop worlds).
- **Client game tests** in the headless session:
  - In Live mode, breaking a ground block is refused with the line above, and the block stays. In Build mode it breaks.
  - The menu's Build mode button switches the mode both ways, and its label follows G pressed in between.
  - In a desktop world no tutorial toast appears after joining; in a normal world the vanilla tutorial still runs.
- **Pictures**, saved as test-game screenshots under `reviews/327-tryout-fixes-1/screenshots/`:
  - the AresOS menu with Build mode and "Start a new home…", and the New home confirm screen;
  - the Terminal's logo before and after, and, if the logo fix is general, every starter logo before and after.
- **The builds:** two full passes of build and client tests through the dev scripts, as `AGENTS.md` requires. Add the new client test at the end of the list so the screenshot numbering stays. Put other packages' pictures back as before.
- **Note:** `Tutorial.setStep(NONE)` writes the instance's `options.txt`. The AresOS Prism instance serves only the home, so that's fine; in the dev client it's the dev profile's, which is fine too.

## Rules

- **AGENTS.md** applies, including rule 6: write "the owner" in anything committed.
- **The safety bar** (decision 24): fix real harm, and list low-harm edge cases under the report's Known limits.
- **Headless only,** never `WAYLAND_DISPLAY=wayland-0`. The owner's real home is running on the laptop. Never touch it, its Prism instance (`~/.local/share/PrismLauncher`), `~/.local/state/aresos`, or the `aresos-desktop` processes.
- **Owner's files:** never touch `~/.minecraft`, `~/.lunarclient`, Lunar Client or `~/AresOS-try`.
- **Bound files:** this package changes only `mod/` and docs. If a change turns out to need a file under `os/`, stop and say so in the report instead.
- **The lock:** one client test at a time through the scripts. On exit 75, wait about five minutes and retry, at most six times.
- **The report:** write `reviews/327-tryout-fixes-1/REPORT.md` with the Terminal logo's cause, the changes, the tests and Known limits.
- **Commits:** end each commit with the trailer line `Codex-Model: gpt-6.2-sol xhigh`.
- **The PR:** push `pkg/327-tryout-fixes-1` and open a PR titled "Package 327: the home's first try-out fixes (tutorial off, nothing breaks in Live, Build mode in the menu, New home, the Terminal's logo)". End its body with:

  ```
  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  https://claude.ai/code/session_015ffFyQnMDXVxFaVyNCKSXH
  ```

- **Never** merge, push to main or use `--no-verify`.
