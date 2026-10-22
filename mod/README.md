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
completion, and save regression screenshots in `build/review/01-first-app/`.
Nether-home and seed screenshots go in `../reviews/04-nether-home/`.
The client test task has a ten-minute timeout for a stuck game startup.

Click **AresOS** above Singleplayer on the title screen to reopen **AresHub**,
or choose a seed on the create screen if it does not exist. Seed **49** is
prefilled; **49**, **50** and **26** have quick-pick buttons. Seed entry follows
vanilla Minecraft: numbers use that exact seed, text is hashed, and an empty
field chooses a random seed. Changing the seed resets the placeholder toggle:
on for 49, off otherwise. You can then toggle it yourself.

The optional placeholder is a blackstone/gold floor with a lava pool, four
lanterns, an anchor and a glass enclosure. Seed 49 with the placeholder uses
the surveyed floor at **(-64, 56, 32)** and arrival at **(-63.5, 57, 37.5)**.
Other choices score nearby terrain for solid ground, clear air and a lava view,
then verify safety in the fully generated Nether. With the placeholder off,
arrival uses natural ground and provisioning places or removes **no blocks**.
If no safe location is found, the incomplete save is kept for recovery rather
than carved or retried. A placeholder is built only for an explicitly new
creation; later edits always persist.

To try another seed, click **New AresOS world…** beside AresOS and confirm.
The entire current save is renamed to **AresHub-<date-time>** before the create
screen opens. No save is deleted or replaced. Canceling confirmation keeps
AresHub as it was; canceling creation after confirmation keeps the dated save.
Open dated saves through normal **Singleplayer**. A rename failure leaves the
existing save alone and displays an error.

Press **G** for Build mode, fly around and build wherever you choose. Stand on
solid ground with clear feet and head, away from lava or fire, and run
**`/aresos home set`**. It saves your exact position, dimension and facing
without editing blocks, and makes that spot the arrival on every join and
the respawn point. **`/aresos home`** teleports there while keeping your current
mode; **`/aresos home info`** prints the seed, position, dimension and facing.
These commands need no cheats and accept only the singleplayer host in an
enabled AresOS desktop. Ordinary desktops marked with `/aresos desktop on`
can also set a home without constructing a hub. Joining always enters Live.

The save keeps `aresos-home.properties` (provisioning version and seed/site),
`aresos-home.provisioned` (a permanent provisioning claim, marked complete after
saving provisioning), `data/aresos/nether_home.dat` (initial site and optional exact home), and
the existing desktop marker. Keep the whole world directory with backups.
Only a new creation through the AresOS button can build a hub. If an existing
home loses its home data, it opens without rebuilding, changing gamerules or
enabling the desktop marker, and chat explains how to restore a backup. This
also protects older saves without the separate provisioning claim.
Saved mounts stay at their original location and dimension; home arrivals
always dismount the player.
The button refuses an existing
unrecognized or incomplete `AresHub` instead of replacing it. After a failed
creation, restore the save or use **New AresOS world…** to keep it under a dated name.
Normal Singleplayer and Quick Play (`--world AresHub`) also use the saved hub.
See [seed scoring and alternatives](../reviews/04-nether-home/seeds/README.md).
To repeat the offline generator survey, run `.\gradlew.bat searchNetherSeeds`.

`runClient` uses the isolated `run/` game directory. Worlds created through normal
Singleplayer play like normal Minecraft. In singleplayer, run `/aresos desktop on` to mark the world as an
AresOS desktop; cheats are not needed. This does not build a Nether hub or change
that world's gamerules. Notepad appears in the first empty hotbar
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

`/aresos desktop off` disables Live protection, hub arrival and automatic app
pinning immediately, keeping existing items and the player's current game mode.
The new home's gamerules remain saved world settings. The marker is saved as
`data/aresos/desktop.dat` in this world save and covers all its dimensions.

## App configuration

The first start creates schema 2 at `config/aresos/apps.json` inside the dev
client's game directory. On Windows, AresOS reads user/common Start Menu `.lnk`
files and the current user's AppsFolder/Store entries. Discovered apps are added
without pins. Existing IDs, names, looks, pins and Windows command argv stay intact;
Notepad keeps `notepad`. Shortcut launches go through Explorer so their arguments
and working directory remain Windows' responsibility. Disappearing apps are kept
in the configuration; discovery never removes an owner entry.

Discovery matches complete Windows launch identities before choosing aliases:
target, raw shortcut arguments, parsed argument list, working directory and AUMID.
Different raw quoting or working directories remain separate apps, even with
identical executables and parsed arguments. Configured argv matches only one
unambiguous candidate; shell arguments and older metadata lacking raw arguments
are retained separately when equivalence cannot be proved, with a diagnostic.
Known Notepad shortcuts and its Store alias reconcile to `notepad` while that
entry still launches Notepad without document arguments. Repurposed entries keep
their owner fields and IDs. Generated
shortcut entries retain optional `launchIdentity` metadata in schema 2, so adding
an earlier-sorted alias (or later removing the original alias) keeps the existing
ID. This metadata does not change the owner's command. Multiple existing matches
are all retained and logged as ambiguous; discovery never chooses between them.

```json
{
  "schemaVersion": 2,
  "apps": [
    {
      "id": "notepad",
      "name": "Notepad",
      "type": "command",
      "command": ["notepad.exe"],
      "look": "minecraft:writable_book",
      "pinned": true
    },
    {
      "id": "moodle",
      "name": "TUM Moodle",
      "type": "url",
      "url": "https://www.moodle.tum.de/",
      "look": "minecraft:book",
      "pinned": false
    }
  ]
}
```

Restart after edits. A URL must use HTTP or HTTPS; Windows opens it through the
default browser. Commands remain argument lists passed directly to `ProcessBuilder`.
Each entry needs a unique lowercase `id`, nonempty `name`, vanilla item `look`, and
boolean `pinned`. `command` entries need a nonempty argv; `url` entries need `url`.
An optional `icon` path can supply a local PNG. Missing/unreadable icons use `look`;
a missing vanilla item uses a book. Websites use their configured vanilla look
unless a local icon is supplied; AresOS does not fetch favicons.

Package-01 arrays migrate on startup: the entire file is validated first, copied
byte for byte to `apps.json.schema-1-<unique id>.bak`, then replaced atomically by
schema 2. Migration runs once. Invalid entries, duplicate IDs, unsupported schemas
or an I/O error stop with a diagnostic and preserve the original file. No defaults
replace a broken file. Pin/merge edits also preserve unknown optional fields.

Before downgrading to package 01, close Minecraft and run the explicit recovery
command from `mod/` (substitute the paths to your dev config and its migration backup):

```powershell
.\gradlew.bat restoreLegacyApps '-PappsConfig=run/config/aresos/apps.json' '-PappsBackup=run/config/aresos/apps.json.schema-1-<id>.bak'
```

It validates the backup, keeps your current schema-2 file as
`apps.json.schema-2-before-downgrade-<id>.bak`, prints a warning about later edits,
and restores the original schema-1 bytes atomically. **The old backup excludes
later apps, edits and pins.** Compare both retained versions before using the older
mod. Starting the new mod again migrates back to schema 2.

On Linux, `aresos-shell/1.0` is a stub until the OS helper arrives. Legacy migration
imports appearance/pins and removes command argv from schema 2 (the original
remains in its backup). Unknown/custom IDs stay visible. All Linux launches,
including URLs, fail with an unavailable-helper diagnostic; no commands execute.

Generated icons live only in `aresos-runtime/` under the game directory, in a
required runtime resource pack. Each source becomes a 16×16 texture, fitted within
14×14 pixels, with binary alpha and at most 15 visible colors. Sources and converter
version are hashed; unchanged converted textures are reused. Windows re-reads
shortcut/resource/UWP icons on startup to detect changes. The `IconConverter`
interface isolates the style. No installed app list or extracted icon belongs in Git.

In marked AresOS worlds in Live mode, pinned apps fill empty hotbar slots and the
remaining apps fill empty inventory slots. Existing items are never overwritten.
When a hotbar slot becomes available, population on rejoin/Live entry moves an
existing pinned app from inventory into it instead of creating another item.
**E → Apps…** opens a paged catalogue, including apps that did not fit. Pick an app
to put its item on the inventory cursor, then place it with normal inventory input.
Moving an item into/out of the hotbar updates its `pinned` value once the cursor
is empty, including through chest and other container menus; reordering within the
hotbar does not change pins. A failed save displays
a diagnostic. More than nine pins remain configured; overflow stays in the
inventory/catalogue. Build mode and normal worlds get no catalogue or pin edits.

Only survival players in marked AresOS worlds receive Live protection. Void
recovery uses their personal bed/anchor spawn, or the world's default spawn if
the personal spawn is missing; it does not consume respawn-anchor charges.
Normal worlds never receive apps or an Apps button. Existing app items can still
launch there, preserving package-01 behavior.

After an app launch, AresOS watches for the first focus loss within 30 seconds.
On return, it closes only the pause screen created by that focus loss. An Esc
menu, a replacement screen, and focus loss without a launch stay untouched.
Each launch owns its focus tracking, so an older launch failing cannot cancel a
newer launch's return.

## Walk-in app logos

In an AresOS world, the singleplayer host can bind an owner-built logo to an app
without cheats. Stand at one corner of its walk-in space and run
`/aresos zone pos1`, then stand at the opposite corner and run `/aresos zone pos2`.
Both corners are inclusive **feet blocks** in the same dimension, up to 64 blocks
per axis. Stand just outside on safe solid ground and run
`/aresos zone set <app id>`. This saves your current position as the return exit,
with facing aimed at the zone. Leave its feet space clear enough to walk into.

`/aresos zone list` prints all zones, dimensions, bounds and exits.
`/aresos zone remove here` removes the zone touching your player;
`/aresos zone remove <app id>` removes **all** zones for that app across the save.
Removing a zone leaves its logo blocks in place and removes their protection.
Zones cannot overlap or cover each other's return exits. Multiple separate zones
can launch the same app.

For automatic pixel art, stand on safe ground, face the intended logo, and run
`/aresos logo <app id> [wall|floor]` (default: `wall`). The nearest horizontal
direction determines the orientation. The near edge starts four blocks ahead;
the wall rises from your feet, while the floor is one block below your feet.
The original source icon is fitted within 32×32 without upscaling, and visible
pixels choose the nearest RGB color from a fixed 48-block concrete/wool/terracotta
palette. Transparent pixels place nothing; mostly transparent downsampled cells
also stay empty. Missing or unreadable source icons are refused with instructions
to supply a local PNG in `apps.json`. No vendor icons or block textures are shipped.

The whole face, including transparent holes, and its approach must be air.
Occupied space, entities in placement cells, out-of-bounds placement and overlap
are refused before building. Logo blocks must also clear every saved exit's full
standing body. The builder conservatively refuses plants, circuits, fluids and
blocks with special behavior within two face-adjacent steps of a pixel, including
through a solid neighbor. Only air and plain inert full blocks are accepted in
that margin; this avoids firing support updates, drops or redstone before a build
can be refused. The error names the neighboring block and its position.
**There is no overwrite command:** clear the required
space yourself in Build mode and retry. A floor logo usually needs its footprint
excavated one block deep first. The builder saves a matching zone: two blocks in
front of a wall, or two blocks of feet space above a floor. It saves your standing
position as the exit. Auto-built blocks resist player breaking in Live mode and
explosions in both modes; press **G** for Build mode to mine and edit them.

Only the singleplayer host in Live mode launches on entering from outside, once
per entry, with portal particles and a short teleport sound. Entry uses the
player's body touching the box, including over transparent floor pixels. Entry
membership is tracked independently for each zone, so touching a
neighboring zone cannot rearm one you still occupy. Simultaneous entry into two
zones is refused with a message; step out and enter one at a time. Exits
must leave the whole body clear of every zone. Standing inside,
switching to Live inside, or rejoining inside never launches. Normal worlds stay
inactive. Program and URL zones use the existing launcher and its 30-second
focus-loss tracking. Returning focus teleports you to the saved exit and faces
the logo, including when pause-on-focus-loss is disabled or a screen was opened
before the app took focus. An already-open screen stays open. A failed launch does not
retry while you stand inside. If an exit has since become unsafe, AresOS reports
the obstruction and leaves you in place. Clear that exit in Build mode.

Zones and exact auto-built block positions persist in `data/aresos/zones.dat`.
Keep the whole world save with backups. Client tests use original geometric icons
and save wall/floor evidence under `../reviews/08-walk-in-logos/screenshots/`.
The lime glass frames in those screenshots are test fixtures around the saved
trigger boxes; they are not placed by the logo command.
