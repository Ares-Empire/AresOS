# AresOS shell mod

Minecraft Java 26.2, Java 25, Fabric Loader 0.19.5, Fabric API 0.161.0+26.2.
Based on the official [Fabric example mod, 26.2 branch](https://github.com/FabricMC/fabric-example-mod/tree/26.2).
Loom 1.19.2 requires the included Gradle 9.8.0 wrapper.

From this directory in PowerShell:

```powershell
.\gradlew.bat build
.\gradlew.bat runClientGameTest
.\gradlew.bat runClient
```

In Git Bash or Linux, use `./gradlew` instead. `build` runs the unit tests and
server game tests; client game tests are a separate task because they open a
Minecraft window. They use a fake app launcher, close the world and client on
completion, and save screenshots in `../reviews/01-first-app/screenshots/`.
The client test task has a five-minute timeout for a stuck game startup.

`runClient` uses the isolated `run/` game directory. New worlds play like normal
Minecraft. In singleplayer, run `/aresos desktop on` to mark the world as an
AresOS desktop; cheats are not needed. Notepad appears in the first empty hotbar
slot. Right-click it to launch, including when looking at a door, chest or
villager; the target stays untouched. Holding right-click or switching slots
while holding does not launch repeatedly. Each release and new press launches
again, even between client ticks.

In an AresOS world, press **G** to switch between Build (creative) and Live
(protected survival). The binding is under **AresOS** in Controls.
`/aresos give notepad` works there without cheats. Desktop commands and mode
switching accept only the singleplayer host, including when open to LAN.
In normal worlds, **G** just shows "Not an AresOS world", and `/aresos give`
does not place anything.

`/aresos desktop off` restores normal rules immediately, keeping existing items
and the player's current game mode. The marker is saved as
`data/aresos/desktop.dat` in this world save and covers all its dimensions.

## App configuration

The first start creates `config/aresos/apps.json` inside the game directory:

```json
[
  {
    "id": "notepad",
    "name": "Notepad",
    "command": ["notepad.exe"],
    "look": "minecraft:writable_book",
    "pinned": true
  }
]
```

Restart the client after edits. Commands are argument lists passed directly to
`ProcessBuilder`, without a shell. Each app needs a unique lowercase id, a name,
a nonempty command, a vanilla item id, and a boolean `pinned`. An empty list
intentionally disables all configured apps. Missing vanilla items fall back to
the book model. Broken JSON or invalid entries produce a byte-for-byte sibling
backup named `apps.json.broken-<unique id>` before defaults replace the file.
An I/O failure is logged and leaves the original file intact.

On Linux the same configuration works with Linux commands; the default
`notepad.exe` must be replaced with an installed executable. The Linux launcher
has no desktop-specific behavior beyond starting a detached process.

Only survival players in marked AresOS worlds receive Live protection. Void
recovery uses their personal bed/anchor spawn, or the world's default spawn if
the personal spawn is missing; it does not consume respawn-anchor charges.
Pinned apps already anywhere in the inventory are left alone. A full hotbar is
left alone, and pinned placement is tried again on the next join or return to
Live mode. Normal worlds never receive pinned apps. Existing app items can still
launch there.

After an app launch, AresOS watches for the first focus loss within 30 seconds.
On return, it closes only the pause screen created by that focus loss. An Esc
menu, a replacement screen, and focus loss without a launch stay untouched.
Each launch owns its focus tracking, so an older launch failing cannot cancel a
newer launch's return.
