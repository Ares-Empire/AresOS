# 332: inputs for revision 3 (home styles)

From the owner (relayed by `mac-capacity`, answered on the board) and `linux-desktop`, Sun 2026-11-22 evening.

- Idea: "AresOS should offer completely normal homescreen customization with pictures and videos as backgrounds and app icons on top of that, with the minecraft home being one option."
- T493 (answered ~20:5x): a fresh AresOS starts with a **"Normal picture home"**; the Minecraft world is the special option.
- Consequences for HOME-OUTSIDE (a revision after T494): home styles Picture / Video / Minecraft world replace "world off" as the framing; desktop icons on the background; video backgrounds (looped, silent, paused when covered); the default can flip only after the native home has picture, bar, search and the style switch (packages 3, 4, 6, 7 and gate 2); the supervisor's boot (linux-aresos) starts the game only in the Minecraft style; first-start Prism sign-in moves to when he picks the Minecraft home.
- linux-desktop's OS points (Sun evening):
  - Video vs the Cairo-only renderer: either the video surface gets GL with hardware decoding (VA-API on the Intel chip), or video is capped (resolution, frame rate) and stops on battery. Package 3's brief measures both.
  - Section 12 should say "paused when covered, and on battery below some level", as an open setting.
  - Icons sit on the same background-layer surface as the picture, so clicks and drags stay the home's; labwc's Root context is already off (B329). Icons take keyboard focus only by a click, never by default.
  - Memory: one video costs more than the laptop home's 60 MiB. Package 3 reports the measured figure on the Intel chip before the owner picks Video.
- T494 (answered Sun evening), desktop icons: "Free dragging for sure but easy alignment and stuff. On Mac OS it's hard to get them in one clean line so that should be easy like a setting that if activated automatically recognizes lines, grids etc and straightens them". So: free placement by drag, plus an alignment setting. When it's on, the home recognizes the lines and grids he's making and straightens them (snaps rows and columns to shared lines and even spacing). When it's off, positions stay where he drops them.

- **To weigh, not yet a recorded decision** (the owner via `mac-capacity`, ~21:05): every AresOS-specific piece should be switchable. A normal taskbar or the AresOS one, a normal picture home or the Minecraft home, and so on, so AresOS can run as a completely normal OS or with any AresOS piece turned on. `mac-capacity` is confirming it with him.
