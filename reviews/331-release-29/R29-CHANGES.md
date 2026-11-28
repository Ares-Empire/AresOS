# What changes from R28 to R29

R29 is waiting for the reviewed version of Deskflow to reach Fedora’s stable updates, expected around Saturday 28 November. If it arrives late, R29 ships without it and Deskflow follows in R30. If it arrives in time, the final build still has to pass review and the sharing and display checks.

## The desktop and keys

- Windows with a system title bar get a pixel frame and game-style lettering. The window in front stands out. The title-bar menu and the outline you see when dragging a window to a screen edge use the same style.
- Hold Alt and tap Tab to choose a window by its thumbnail. Add Shift to go backwards.
- Scrolling on a title bar keeps the window at its usual size. Clicking the bare desktop no longer opens an Exit menu.
- Sound, microphone mute and brightness keys show a small pixel panel that fades while you play. You can choose its size and put it at the top or bottom.
- Volume up brings muted sound back. Holding brightness down stops at 1% so the screen stays lit.

## The game and your home

- With an app in front, moving the pointer over the world leaves the camera still. While the world holds the pointer in classic or click look, clicks and scrolling stay in the game.
- Pinned apps get a mark when open. The mark is longest and brightest for the app in front and dim when all its windows are minimized.
- With the pointer free, left-click a pinned app to open it or bring back its last window. Its item, gate, short name and world search (where available) do the same. Right-click asks the app for a new window.
- You fly faster across town.
- The home hides Minecraft’s tutorial, recipe and advancement pop-ups. Save warnings can still appear.
- Live mode protects even the grass from mining. Choose Build mode in Esc or press G to edit.
- “Start a new home…” explains that you keep your current home. You can open the confirmation and go back.
- Terminal has a black hotbar block and a dark gate with a light prompt.
- Classic look stays the default. You can try click or edge look in the installed game the next time Minecraft starts. In click look, click the world or press a movement key to steer. Pause briefly to free the pointer.
- Edge look keeps the pointer free. An outer edge turns the camera and a shared display edge lets you cross without turning. Up and Down tilt the view even at the top edge.
- When Microsoft sign-in sends you back from the browser, the laptop opens Prism Launcher. Completing a real sign-in still needs your try.

## Chrome and Claude’s tools

- Chrome comes with the AresOS extension. Look for its **A** in the toolbar and “Managed by your organization” in the menu.
- Once you and Claude set up the list of sites Claude must never touch, Claude can read a page as a short outline, do several steps and tell you what changed.
- Sessions get GitHub’s command-line tool with the system. Your own copy still works.

## Deskflow, if it ships in R29

- “Mouse and keyboard sharing” starts off. Turn it on with your password and open Deskflow for this login. It starts itself at later logins while sharing is on.
- Pair the Mac with the laptop by comparing the fingerprints shown on the two screens. Cross the edge to type on the Mac or copy text either way. Turning sharing off needs no password and stops new transfers. A copy already under way can finish.
- While you control the Mac, shortcuts and media keys go there, except that microphone mute does nothing on either computer. Super+Shift+Escape brings control home. Super+Ctrl+Escape also opens a recovery terminal.

Only the laptop can share its keyboard and mouse with the Mac for now. With sharing active, switching a screen off and back on in a custom display mode can crash the desktop.

## Saving, updates and opening apps

- On a planned shutdown, AresOS asks Minecraft to save and waits for confirmation. It tries to hold off lid-triggered sleep during the save. With only the world open, the screen may go black. If time runs out, shutdown can continue and the log records that the save was unconfirmed.
- The recovery window’s `restart` command waits for a confirmed save before closing and restarting Minecraft.
- For building, a Claude session can switch the world off to free memory and back on: `aresos-desktop stop` saves and closes Minecraft, and `aresos-desktop retry` brings your home back. While it is off the screen is black with a small “Minecraft was closed” window, and you open apps from Terminal or Alt+Tab. The world comes back at your next login. A proper switch with a menu of your apps is planned for after R29.
- When released, the signed update will keep the same base system and leave R28 available to go back to. The installer rehearsal has already reached R28.
- The desktop can hold the pointer for sharing in either build. Sending shortcuts to the Mac comes with the Deskflow build.
- The laptop keeps its computer name. The update rehearsal checks that it survives restarts so Chrome can reopen its profile.
- Window frames and level panels use game-style lettering. The font for the future laptop home is ready too.
- When you open an app, the system gives its check for running apps one second. A slow check can make a separate home view ask you to try again. That view can also refresh an old app list and check which window came back after a restart.

## From your R28 try-out

| What you noticed | What to expect |
| --- | --- |
| The monitor stayed black and you needed Esc to cross. | Edge look lets you cross. Putting the world on the monitor and a picture on the laptop is still open. |
| “New home” was unclear. | The button and confirmation explain what happens to both homes. |
| Apps opened part-screen with black behind the gate. | The backdrop, opening full-size and remembering the last size are still open. |
| Clicks landed in Chrome while you steered. | Fixed in the input test. Try it with a harmless tab on the laptop. |
| Clicking beside Chrome made it disappear. | Still open. A test window stayed up, but the cause on the laptop is unknown. |
| Minecraft showed tutorial hints. | Hidden. Your idea for AresOS news pop-ups is still open. |
| The bar didn’t show what was open or in front. | Pinned apps get marks. Showing unpinned running apps comes later. |
| Terminal’s block was brown with white edges. | Check its dark block and gate. |
| Levels and status icons were missing. | The keys show their levels. The row of Wi-Fi, battery, sound and clock icons comes later. |
| Reopening Chrome lost sight of your tab. | Left-click or type `/chrome` to bring its window back. The full options menu comes later. |
| Files and System Settings were missing. | Still open. |
| You could break the home’s blocks by mistake. | Live mode protects them. |
| The bar stayed hidden behind a full-screen app. | The bar over apps comes later. |
| You wanted to look around without holding a button. | Try click and edge look and see which feels better. |
| You wanted a picture instead of the world to save memory. | **Partly.** For building, a session can switch the world off and on (see above). The picture home and a proper switch with a menu of your apps are still open. The test pass measures the memory it frees. |

## For a later sitting

Chrome’s tools stay off until you write your never-list together. Trying a live account and checking the profiles together have their own sitting. The laptop home and in-game search are prepared, but starting that home, placing it on the right screen and opening search with Super still need work.

When leaving R28 with the world open, follow the released update guide. Close Minecraft and wait for “Minecraft was closed. Nothing is wrong.” The new save protection starts with R29. The all-in-one maintenance command is still in review.

Alt+Tab followed by Escape can leave the world without keyboard input. Switching away and back restores the keys.
