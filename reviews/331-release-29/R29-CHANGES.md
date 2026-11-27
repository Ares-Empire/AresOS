# What changes from R28 to R29

R29 is waiting for the Deskflow decision. These are the changes lined up for your next update. Signing the final update and trying it on the laptop come later. `B331`

## The desktop and windows

- Windows with a system title bar get a pixel frame and game-style lettering. The window in front is easier to pick out. `B329`
- Hold Alt and tap Tab to see window thumbnails. Add Shift to go backwards. `B329`
- Scrolling on a title bar leaves the window open at its usual size. Clicking the bare desktop no longer opens a menu with an Exit button. `B329`

## Keys, volume and brightness

- The sound, microphone mute and brightness keys show a little game-style panel. By default it appears at the top centre, then gets out of the way while you keep playing. `B320`
- The panel can sit at the top or bottom of the screen, in a size you choose. The first style is the pixel look. `B320`
- Pressing volume up brings the sound back even if you muted it. `B320`
- Holding brightness down stops at 1%, so you can still see the screen. `B320`

## The game, the home screen and looking around

- With an app in front, moving the pointer over the world leaves the camera still. Once you are looking around in the world, clicks and scrolling stay in the game. `B56` `B328a`
- Your pinned apps have a mark when open. It is brighter and longer for the app in front and dimmer when all its windows are minimized. `B333`
- With the pointer free, left-click a hotbar app to open it or bring back its last window. Using its item, walking into its gate or typing its short name brings it back too. `B333`
- Right-click a hotbar app with the pointer free to ask for a new window. Each app decides how to handle that request. `B333`
- You fly faster across town. Try a familiar route and see how the speed feels. `B56`
- The home drops Minecraft's “punch a tree”, recipe and advancement pop-ups. Save warnings can still appear. `B327`
- In Live mode even the grass is protected from mining. Choose Build mode in the Esc menu or press G when you want to edit. `B327`
- The Esc menu says “Start a new home…” and explains that you keep your current home. You can read the confirmation and go back. `B327`
- Terminal has a black hotbar block and a dark gate with a light prompt. The old pale rim is gone. `B327`
- You can try two ways to look without holding a button. In click look, click the world or press a movement key to start looking, then pause briefly to free the pointer. `B328`
- In edge look, move to an outer edge to turn, or cross a shared screen edge with the pointer free. Up and Down tilt the view, so you can look back down even with the pointer at the top. `B328` `B343`
- When Microsoft sign-in sends you back from the browser, the laptop knows to open Prism Launcher. Completing a real sign-in still needs your try. `B330`

## Chrome and Claude's tools

- Chrome comes with the AresOS extension. Look for its **A** in the toolbar and “Managed by your organization” in Chrome's menu. `PR76`
- Once you set up the tools, Claude can read a page as a short outline and do several steps in one request. You get back what changed. `PR72` `PR116`
- Sessions get a copy of GitHub's command-line tool with the system. Your own copy can still be used. `PR76`

## Deskflow

**If it is ready in time: arrives as Fedora stable, otherwise R30.** The release also needs the reviewed build to pass its sharing and display checks. `B321` `B331`

- “Mouse and keyboard sharing” starts off. Turn it on with your password, open Deskflow for this login, and it starts by itself at later logins while sharing is on. `B321`
- Point the Mac's Deskflow client at the laptop and compare the fingerprints at first pairing. Once paired, cross the screen edge to type on the Mac or copy text between the two. `B321`
- While you control the Mac, shortcuts and media keys go there. Super+Shift+Escape brings control home, and Super+Ctrl+Escape also opens a recovery terminal. `B321`

## Safety and under the hood

- Before a planned stop, the guardian asks Minecraft to save your home and waits for its answer. With just the world open you may see a black screen during the save. `B25` `PR136`
- The desktop message window gains a restart command. It saves the home and restarts Minecraft. `B25`
- When R29 is released, you get a signed update on the same base, with R28 kept as your way back. The rehearsal has already checked the route up to R28 with the refreshed installer. `B331`
- The window manager, labwc, can now hold the pointer for input sharing. Deskflow uses that to keep control when you move the mouse. `B311` `B321`
- Your laptop keeps its existing computer name. The update rehearsal now checks that its test computer keeps its name across restarts, so Chrome can reopen its profile. `B331`
- Jersey 10 supplies the game lettering on frames and indicators. JetBrains Mono is available for the laptop home being built. `B320` `B323` `B329`
- If the system is slow to answer when you open an app, the home spends less time waiting. There are also checks ready for the future laptop home to keep track of the right window and refresh its app list. `B343` `PR134`

## From your R28 try-out

| What you found | Where it stands for R29 |
| --- | --- |
| Plugging in the monitor left it black and you needed Esc to cross. | **Partly fixed.** You can try crossing in edge look. Putting the world on the monitor and a picture on the laptop is still with the hub and desktop teams. `B328` `B332` |
| “New home” was unclear. | **Fixed.** The button and confirmation explain what happens to both homes. `B327` |
| Apps opened part-screen with a black view behind the gate. | **Open.** The hub owns the view behind the gate. Opening full the first time and remembering the last size still needs the hub and desktop teams. `HUB-HANDOFF` |
| Clicks landed in Chrome while you steered the world. | **Fixed in the input test.** Try it with a harmless tab on the laptop to confirm. `B328a` |
| Clicking beside an app made it disappear. | **Open for the desktop and hub teams.** A part-screen test window stayed up, but what hid Chrome on your laptop is still unknown. `B328a` |
| Minecraft gave you tutorial hints. | **Fixed.** The home hides them. Your idea for AresOS news pop-ups stays with the hub. `B327` |
| The bar didn't show what was open or in front. | **Partly fixed.** Pinned apps get marks. Showing unpinned running apps belongs to the hub and desktop teams' later bar. `B333` |
| Terminal's block was brown with white edges. | **Fixed.** Look at both its slot and the town gate. `B327` |
| No level pop-ups or Wi-Fi, battery, sound and clock icons. | **Partly fixed.** The keys show their levels. The desktop team still has the row of status icons. `B320` `HUB-HANDOFF` |
| Reopening Chrome lost sight of the window with your tab. | **Partly fixed.** Left-click or type `/chrome` to bring it back. Right-click asks for another window. The hub still has the full options menu. `B333` |
| Files and System Settings were missing. | **Open** for the OS and desktop teams. `HUB-HANDOFF` |
| You could break the home's blocks by mistake. | **Fixed.** Live mode refuses mining. Build mode lets you edit. `B327` |
| The bar stayed hidden at the bottom of a full-screen app. | **Open.** The hub and desktop teams have the bar that will appear over apps. `B332` |
| You wanted to look around without holding a button. | **Partly fixed.** Click and edge look are ready to try. The hub is waiting for your choice by feel. `B328` `B343` |
| You wanted to switch the world off and use a picture to save memory. | **Open** for the hub and desktop teams. You didn't test memory in that sitting. The hub still has the sleeping-world study. `B332` `T364` |

## Not in R29

- Claude's Chrome tools stay off until you write your never-list together. The live account trial and the later combined profile checks have their own sitting. `PR76` `B331`
- The laptop-home program and in-game search are prepared. Starting that home, placing it on the right screen and opening search with Super still need the desktop wiring. `B53c` `B53d` `B53f` `B23c`
- Classic look is still the default. The picture home, world-off switch and bar over full-screen apps are later work. `B328` `B332`
- When leaving R28 with the world open, the update guide still asks you to close Minecraft and wait for “Minecraft was closed. Nothing is wrong.” The guardian arrives with R29. `T462`
- The all-in-one maintenance command is still waiting for its own review and merge. Follow the released owner-tools guide for updates. `B43` `B331`
- Alt+Tab followed by Escape can leave the world without keyboard input. Switching away and back restores the keys. `T486`
- In the conditional Deskflow build, the microphone-mute key does nothing while you control the Mac. Sharing in the opposite direction is later work. `B321`
