# Package 56 headless checks

Run the full client suite from the repository root:

```sh
mod/dev/client-test.sh --session
```

The existing client-test lock, memory checks, NVIDIA holder and owned-scope cleanup apply. There is no `--force`. `--session` starts a private **headless** labwc with the checkout's image `rc.xml`, without its autostart. It passes `-PpointerSession` to Gradle. The game still has no real session/helper credentials: the final Fabric test creates a `FakeHelper` and temporarily makes that the mod's connection.

`FreePointerClientGameTest` opens two `foot` stand-ins with distinct app IDs and requested 480 × 260 content sizes, outside the image's recovery-terminal maximize rule. `pointer.py` puts a virtual keyboard and pointer on that compositor only; it takes the test's `env` file, refuses `wayland-0`, accepts one command per stdin line and answers `done` after a compositor round trip. The test uses package 40's `tl.py` to activate/list/close these windows and checks actual focus, including Alt+Tab and the remaining window after close. It also replays `MouseHandler.onMove` with GLFW's misleading focused state, so a compositor that filters raw motion cannot hide the original defect.

Fabric deliberately disables native input callbacks and mouse grabbing, and uses a virtual render size independent of the maximized compositor window. The final native test temporarily installs only mouse callbacks, queries GLFW's actual window size (the framework's cached size can be stale after fullscreen tests), maps real content coordinates to that virtual size, and restores the previous callbacks before leaving. The ordinary preview is used for the actual GLFW capture behavior.

The game screenshot is captured by Fabric, including the hover border and the game's own item-name line. `grim` is not needed for the automated assertions. Without `--session`, all game-callback, input-gate, launch and flight assertions still run; native windows and seat input require the headless session option.

## Cause reproduction before the fix

The investigation first used `mod/dev/run-hub.sh --session` inside another headless labwc, with its own reviewed test registry and small `foot` apps. Ordinary steady-state app focus, with both the installed helper and the checkout helper, released the pointer correctly. No claim is made that this easy path reproduced the owner's turning.

The failing case used the checkout helper's existing `ARESOS_SHELL_KEEP_FOREGROUND=1` restart behavior, an app already focused when the desktop window appeared, and `--args='--quickPlaySingleplayer AresHub'` against **mod/run**, never the owner's home. The helper restored the app's focus before the player joined. An inspection on the client's thread then showed:

```text
front=false active=true glfwFocused=true grabbed=true yaw=180.0 pitch=-8.0
```

A temporary Java attach agent replayed two `MouseHandler.onMove` calls and `handleAccumulatedMovement` on that same client thread, while foreign-toplevel still reported the small app activated:

```text
front=false active=true glfwFocused=true grabbed=true yaw=200.1 pitch=3.7000017
```

The virtual seat alone did not reliably reproduce raw motion in the captured Xwayland window; callback replay is stated explicitly here. The focus state, erroneous capture and resulting camera change were observed in the real session preview. `HomeScreen.frame` had erased the helper's background state while `active()` was false during loading. Closing the loading screen could then capture the pointer, and neither capture nor turning checked the helper's focus. The final client test covers both the erased-state transition and the unguarded screen-close/capture path, plus real seat movement and native focus transitions.
