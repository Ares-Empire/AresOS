# AresOS shell mod

Minecraft Java 26.2, Java 25, Fabric Loader 0.19.5, Fabric API 0.161.0+26.2.
Based on the official [Fabric example mod, 26.2 branch](https://github.com/FabricMC/fabric-example-mod/tree/26.2).
Loom 1.19.2 requires the included Gradle 9.8.0 wrapper.

## The same jar everywhere

Build with **Temurin 25.0.5+8** and the SHA-256-checked **Gradle 9.8.0** wrapper;
Loom **1.19.2**, Minecraft **26.2**, Loader **0.19.5** and Fabric API
**0.161.0+26.2** are pinned in `gradle.properties`. Archives use fixed order,
timestamps and permissions, compilation/resource filtering use UTF-8, and the
Gradle JVM uses English/US and UTC. A small final jar action sorts Loom's
client-entry manifest list and manifest attributes, preserving their values.
Run `dev/build.sh` on the laptop, then `sha256sum build/libs/aresos-0.1.0.jar`
(PowerShell: `Get-FileHash build/libs/aresos-0.1.0.jar -Algorithm SHA256`).
Compare with the **Mod** workflow's summary for the same commit. That workflow
uses the image's exact digest-pinned Temurin container, builds/tests two clean
checkouts in different paths, checks equal bytes and uploads the jar and hashes.

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

## On Linux (AresOS)

On the AresOS laptop, use the scripts in `dev/` (from any directory). They need
no system install and change no shell setup:

- **Java:** Eclipse Temurin JDK 25.0.5+8 in the home folder:
  `~/.local/opt/jdk-25.0.5+8`, linked as `~/.local/opt/jdk-25`, unpacked from
  [OpenJDK25U-jdk_x64_linux_hotspot_25.0.5_8.tar.gz](https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25.0.5%2B8/OpenJDK25U-jdk_x64_linux_hotspot_25.0.5_8.tar.gz)
  (SHA-256 `68982529869257d0ee6b824ec5aa270ff8b118bb438670da0b97ebdab178d7fb`,
  as Adoptium publishes it). The scripts use `JAVA_HOME` if it is a Java 25 JDK,
  otherwise that link (`dev/env.sh`).
- **`dev/build.sh`** runs `./gradlew build` (unit tests and server game tests).
  Six Windows catalogue unit tests (PowerShell discovery, Windows paths) skip on
  Linux and say why.
- **`dev/client-test.sh`** runs `./gradlew runClientGameTest` in its own headless
  compositor (`cage`, `WLR_BACKENDS=headless`) and that compositor's Xwayland, so
  no window appears on the screen and the game cannot reach the real display.
  It renders on the RTX 4060 (PRIME offload) when that works headless, else on
  the Intel GPU, else in software (`--gpu` picks one), and says which at the end.
  Sound goes to OpenAL's null device. `--keep-screenshots <dir>` copies the
  screenshots the run wrote (the folder is created and checked before the run,
  and a failed copy makes an otherwise green run exit 1); then
  `git checkout -- ../reviews/` undoes the rewritten tracked ones.
- **`dev/run-hub.sh`** (a development aid; package 23's session supervisor replaces
  it) starts an app helper of its own (`/usr/libexec/aresos-shell`) with a fresh
  desktop instance and launch nonce on a private socket in
  `$XDG_RUNTIME_DIR/aresos-dev/run-hub-<pid>/`, then `./gradlew runClient` on the
  real screen on the RTX 4060 with that socket, so walking into a logo opens the
  app. It never uses the session's `$XDG_RUNTIME_DIR/aresos/shell.sock` and never
  reuses a helper; when the game exits, its helper stops and the folder is
  removed. `--helper <path>` starts another helper (for example one from a
  worktree) and `--registry <dir>` passes its app folder to the helper's
  `--registry`.

Extra arguments go to Gradle; its daemon switches `--daemon`, `--foreground`,
`--stop` and `--status`, including their single-dash forms, are refused (exit
code 2). Only one client test runs at a time on the laptop: `client-test.sh` waits for
`~/.cache/aresos-dev/client-test.lock` and says so. All three refuse
(exit code 75) while the Lunar Client game (Lunar's own Java) runs or less than
6 GB of memory is available, and `client-test.sh` and `run-hub.sh` check again
right before Gradle starts; `--force` skips those checks. Everything a script
starts (Gradle without a lasting daemon, the game, a compositor, a GPU probe, the
app helper, the wait for the lock) runs in a systemd user scope of that script's
own, named `aresos-dev-…`, and every exit, Ctrl+C included, stops those scopes
with everything in them.

Scope startup has a 15-second deadline, including deferred signals. Cleanup
retries stops and state queries for up to 30 seconds; if absence cannot be
confirmed, it names the units, exits non-zero and keeps private run folders.
Existing scope names are avoided, and a failed creation is never stopped.

**Known limits of the dev scripts:**

- A real Ctrl+C and a really closed terminal were tested as signals only.
- A hanging GPU probe was tested with a stand-in, rather than a wedged compositor.
- The user systemd manager must respond to commands. A broken manager that hangs
  a query, or another process deliberately taking a just-checked random scope
  name, is outside these scripts' guarantees.

Click **AresOS** above Singleplayer on the title screen to reopen **AresHub**,
or to create it if it does not exist. The create screen has one choice,
**Home: Flat** or **Home: Nether** (click it to switch). Flat is chosen first.

**The flat home** is a flat Overworld: bedrock at y -64, stone up to y 59,
three layers of dirt and grass at y 63, plains everywhere, no structures,
nothing generated on the grass, seed 0. It is survival, normal difficulty,
cheats off. You stand in block **(0, 64, 0)** on a gold block in a 5 x 5 pad of
polished blackstone bricks and look north. It is noon and clear and stays so,
and no mob spawns. Four roads, 5 blocks wide, lead from the pad to 24 blocks
out, each with a centre line in its group's colour and the group's name 9
blocks up over it, 20 blocks out: north light blue (INTERNET), east red
(GAMES), south yellow (SYSTEM & TOOLS), west purple (WORK & MEDIA). The world
spawn is the home block. The numbers and the group table are data in
`hub/HubLayout.java`; the design is `docs/design/HUB.md`. The logos along the
roads are the town ("The town" below).

The pad, the first 24 blocks of each road and the names are built once, with
the new world. After that the town paves a road on when its group grows and
writes the number of apps on each name ("The town" below); nothing else of
them is built again. The mod paves only untouched grass with air above it; anything else
stays. What it placed is saved as `data/aresos/hub.dat`: every block as
`{pos, block}`, the IDs of the four names (text displays), the layout's name
`flat-1`, its numbers and the home block. In Live mode a recorded block that is
still the block the mod placed cannot be broken by hand or by an explosion, and
the names cannot be hit. In Build mode you can change anything, explosions
included. A block you changed is yours: the mod no longer protects it and never
puts its own block back. The rules (the Nether home's, plus the day cycle and
the weather cycle off), noon and clear weather are set once at creation, so a
rule you change later stays changed.

**The Nether home** shows its seed settings when it is chosen. Seed **49** is
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

To start over, with either home or another seed, click **New AresOS world…**
beside AresOS and confirm.
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

The save keeps `aresos-home.properties` (provisioning version and seed/site;
`home=flat` in it names a flat home, and without that key it is a Nether home),
`aresos-home.provisioned` (a permanent provisioning claim, marked complete after
saving provisioning), `data/aresos/nether_home.dat` (initial site and optional
exact home; despite its name the flat home's too), for a flat home
`data/aresos/hub.dat`, and the existing desktop marker. Keep the whole world
directory with backups. All of this holds for both homes.
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
AresOS desktop; cheats are not needed. This does not build a Nether hub, a home
pad or roads, and does not change that world's gamerules. Notepad appears in the first empty hotbar
slot. Right-click it to launch, including when looking at a door, chest or
villager; the target stays untouched. Holding right-click or switching slots
while holding does not launch repeatedly. Each release and new press launches
again, even between client ticks.

In an AresOS world, press **G** to switch between Build (creative) and Live
(protected survival). Each mode keeps its own inventory, hotbar, armor, offhand
and selected hotbar slot. The first switch from Live to Build starts empty.
Both survive rejoining and restarting; a home arrival restores Live while keeping
your Build items for the next **G**. Close menus and finish cursor/crafting moves
before switching; an open menu refuses **G** with a message. The binding is under
**AresOS** in Controls.
`/aresos give notepad` works there without cheats. Desktop commands and mode
switching accept only the singleplayer host, including when open to LAN.
In normal worlds, **G** just shows "Not an AresOS world", and `/aresos give`
does not place anything.

`/aresos desktop off` disables Live protection, hub arrival and automatic app
pinning immediately, keeping existing items and the player's current game mode.
The new home's gamerules remain saved world settings. The marker is saved as
`data/aresos/desktop.dat` in this world save and covers all its dimensions.

## App configuration

The first start creates schema 3 at `config/aresos/apps.json` inside the dev
client's game directory. On Windows, AresOS reads user/common Start Menu `.lnk`
files and the current user's AppsFolder/Store entries. Discovered apps are added
without pins and are not in My apps (see "My apps" below). Existing IDs, names, looks, pins and Windows command argv stay intact;
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
  "schemaVersion": 4,
  "baseline": "2026-11-13",
  "apps": [
    {
      "id": "notepad",
      "name": "Notepad",
      "type": "command",
      "command": ["notepad.exe"],
      "look": "minecraft:writable_book",
      "pinned": true,
      "mine": true
    },
    {
      "id": "moodle",
      "name": "TUM Moodle",
      "type": "url",
      "url": "https://www.moodle.tum.de/",
      "look": "minecraft:book",
      "pinned": false,
      "mine": true
    }
  ]
}
```

`mine` says the app is one of My apps. An entry you write by hand without `mine`
counts as yours. A pinned app is always yours. `baseline` is the day the first
full program list from the system was taken (AresOS only; see "My apps"). An
entry may also carry `system`: what the system last said about the program
(where it came from, its categories, its icon path and so on). The mod writes
it; leave it alone.

Restart after edits. A URL must use HTTP or HTTPS; Windows opens it through the
default browser. Commands remain argument lists passed directly to `ProcessBuilder`.
Each entry needs a unique lowercase `id`, nonempty `name`, vanilla item `look`, and
boolean `pinned`. `command` entries need a nonempty argv; `url` entries need `url`.
An optional `icon` path can supply a local PNG. Missing/unreadable icons use `look`;
a missing vanilla item uses a book. Websites use their configured vanilla look
unless a local icon is supplied; AresOS does not fetch favicons.

Older files move over on startup, package-01 arrays (schema 1), schema 2
and schema 3 alike: the entire file is validated first, copied byte for byte to
`apps.json.schema-<1, 2 or 3>-<unique id>.bak`, then replaced atomically by schema 4.
An app that was pinned, and the starters `browser`, `terminal` and `notepad`,
start as yours when moving from schema 1 or 2; schema 3 keeps its My apps choices.
Nothing else in an entry changes. The move runs once. Invalid
entries, duplicate IDs, unsupported schemas or an I/O error stop with a
diagnostic and preserve the original file. No defaults replace a broken file.
Pin, My-apps and merge edits also preserve unknown optional fields.

An older mod that finds a schema-4 file refuses it ("Unsupported schemaVersion"), leaves the file untouched, starts without apps and says
"AresOS apps disabled: ..." in the chat.

Before downgrading to an older mod, close Minecraft and run the explicit recovery
command from `mod/` (substitute the paths to your dev config and its migration backup):

```powershell
.\gradlew.bat restoreLegacyApps '-PappsConfig=run/config/aresos/apps.json' '-PappsBackup=run/config/aresos/apps.json.schema-1-<id>.bak'
```

It takes a schema-1 or a schema-2 backup, validates it, keeps your current
schema-4 file as `apps.json.schema-4-before-downgrade-<id>.bak`, prints a warning
about later edits, and restores the backup's bytes atomically. **The old backup
excludes later apps, edits, pins and My apps.** Compare both retained versions
before using the older mod. Starting the new mod again moves the file to schema 4.

On Linux (AresOS) the program list and every launch come from the OS app helper
over `aresos-shell` (this mod speaks 1.1 and works with a 1.0 helper as before);
the mod never runs a command itself. Legacy migration imports appearance/pins and
removes command argv from schema 2 (the original remains in its backup).
Unknown/custom IDs stay visible. While the helper is away, every launch,
including URLs, fails with a message that says so.

Generated icons live only in `aresos-runtime/` under the game directory, in a
required runtime resource pack. Each source becomes a 16×16 texture, fitted within
14×14 pixels, with binary alpha and at most 15 visible colors. Sources and converter
version are hashed; unchanged converted textures are reused. Windows re-reads
shortcut/resource/UWP icons on startup to detect changes. The `IconConverter`
interface isolates the style. No installed app list or extracted icon belongs in Git.

On AresOS the system names a picture for each program (`icon` in
`aresos-shell/1.1`). Your own `icon` path in `apps.json` wins; without one, the
system's file is used, but only if it is a regular file of at most 1 MiB that is
a PNG of at most 512 x 512 pixels. Anything else means the app has no picture and
shows its `look`. When the program list or a picture changes while the game
runs, the pack is made again in the background and the game reloads its resource
packs once: not when nothing changed, and at most once every five seconds
(changes in between share one reload). The items you already hold then get the
new picture.

## My apps

One list decides what is in your inventory: **My apps**. Everything else the
system lists is still there to pick from ("All programs"), but has no item.

- **Day one (AresOS).** When the first full program list arrives from the app
  helper (`aresos-shell/1.1`), My apps gets the starters (`browser`, `terminal`,
  `notepad`) and what you installed yourself (programs from your own folder and
  Flatpaks installed for your user). That day is saved as `baseline`.
- **Later.** A program that newly appears and did not come with the system joins
  My apps by itself, and the chat says so: "Spotify is new and joined My apps."
  (In a flat home the town says it instead, with the place of the new logo.)
  Programs that come with a new AresOS image, or whose origin the system does not
  say, never join by themselves.
- **Windows, or an older helper (1.0).** Nothing joins by itself: yours are the
  pinned apps, the starters and what you add.
- Only a complete list counts. While the helper is away or its list will not hold
  still, My apps stays as it is.

### The Apps screen

**E → Apps…** (Live mode, in an AresOS world) opens one list that scrolls: a
search box on top, then **My apps**, then **All programs**, both by name. Each
row shows the program's icon and name and, in gray, what kind of program the
system says it is. Under All programs a check mark marks the ones that are yours.

| You do | What happens |
|---|---|
| Click a program that is not yours | It becomes yours: its item lands in the first free inventory slot beside the hotbar. The screen stays open, so you can add more. |
| Click one of yours | You pick up its item and are back in the inventory, to put it in the hotbar (that pins it). An app without an item, because the inventory was full, gets one this way. |
| Right-click one of yours | It leaves My apps, as with `/aresos app remove`. It stays under All programs. |
| Type | The letters go to the search box, wherever you clicked last. The search looks in the name, the generic name and the keywords the system gives, so "mail" or "pdf" finds the right program. Every word you type must be found; upper and lower case are the same. |
| Enter | A click on the program, if the search found exactly one. The search text is then selected, so typing starts the next search. |
| The wheel, the scroll bar, Up, Down, Page Up, Page Down | Scroll the list (three rows for each notch of the wheel). |
| Escape, or Done | Back to the inventory. |

The line above Done says what a click does and, for five seconds, what just
happened ("Added Steam to My apps."). The chat gets the same line, but it is
hidden behind the screen. When the list changes, the row under the pointer stays
where it is if scrolling permits it. The second click of a double-click is ignored,
so a row that moves under the pointer cannot add a neighbour.

### Commands

For the singleplayer host in an AresOS world (Tab completes the ID):

| Command | What it does |
|---|---|
| `/aresos app add <app>` | Makes a program yours. Its item lands in the first free inventory slot beside the hotbar. With no free slot the app is yours without an item, and the chat says so; the next safe Live tick with a free slot supplies it. |
| `/aresos app remove <app>` | Takes it out of My apps and unpins it. Its item leaves your Live inventory and your saved Build inventory. It stays in All programs with everything saved about it. |
| `/aresos app list` | Your apps, one line each. |

`/aresos give <app>` also makes the program yours. Pinning (moving an item into
the hotbar) makes an app yours too; unpinning changes nothing else.
`give` moves an existing item in your active inventory instead of making a copy.
Finish moving cursor and crafting-grid items before picking up an app through Apps or `give`.

**Known limit: containers.** Chests and other containers, including nested storage,
are yours to use. The mod searches only your player inventory when supplying a
missing app item. Storing one elsewhere can therefore leave another copy in your
inventory, and breaking its container can drop the stored copy into the world.
App items are not globally unique; the Q rule covers player drops only.

Your inventories are never edited at a risky moment. A change is done at once
when that is safe, and otherwise on the first tick on which no mode switch is
under way, no container is open, and nothing is on the cursor or in the crafting
grid. Added in Build mode, an app's item waits in Live. No other item is ever
moved, replaced or lost. An item of an app the file does not know is left alone.

**Q never removes an app.** Dropping an app's item does nothing: Q and Ctrl+Q in
the world, Q over it in the inventory, and a click outside the inventory window
with it on the cursor (put it in a slot, or close the inventory). An app's item
is kept out of player drops; stored copies can reach the ground through containers.

A program the system no longer lists keeps its entry and its item; using it says
that it is unavailable, with the helper's reason.

In marked AresOS worlds in Live mode, pinned apps fill empty hotbar slots and the
rest of My apps fill empty inventory slots. Existing items are never overwritten.
When a hotbar slot becomes available, initial population on rejoin moves an
existing pinned app from inventory into it instead of creating another item.
Switching modes restores the exact saved layout instead of repopulating it;
home arrival from Build also restores Live exactly, and My apps is then brought
in step on the first safe tick (only app items are added or taken out). Ordinary
joins already in Live keep catalogue population. An app of yours that did not
fit can be picked up in the Apps screen (above) and placed with normal inventory input.
Moving an item into/out of the hotbar updates its `pinned` value once the cursor
is empty, including through chest and other container menus; reordering within the
hotbar does not change pins. A failed save displays
a diagnostic. More than nine pins remain configured; overflow stays in the
inventory. Build mode and normal worlds get no Apps screen and no pin edits.

Only survival players in marked AresOS worlds receive Live protection. Void
recovery uses their personal bed/anchor spawn, or the world's default spawn if
the personal spawn is missing; it does not consume respawn-anchor charges.
Normal worlds never receive apps or an Apps button. Existing app items can still
launch there, preserving package-01 behavior.

Separate inventories use the versioned `aresos_mode_inventories` tag inside each
player's vanilla save data, alongside the active inventory and game mode. There
is no separate inventory file that could save a different half of a switch.
The optional `build_active` field records which inventory owns the equipped items,
independently of vanilla game mode. Older version-1 data adopts its saved mode on
first use. Commands, F3+F4/the mode switcher, and mods using vanilla's mode setters
use the same transaction as G. Unsupported modes and unsafe open-menu changes
are refused with a message in marked worlds.

G locks item input immediately. A server-initiated change locks input before sending
the destination inventory. Drops, use, attacks, hand swaps, menu/hotbar moves,
creative edits and further toggles stay blocked until the full inventory, selected
slot and mode have reached the client. Its acknowledgement follows all older input
packets on the same connection, so the server discards those stale actions before
unlocking. Failure synchronizes the retained state and uses the same acknowledgement.
Connected switches require the client's inventory-switch state receiver; older
AresOS and vanilla clients receive a refusal message without changing their items,
mode or transaction state. A missing acknowledgement times out after 200 server ticks
(10 seconds at 20 TPS). Item and XP-orb pickups (including mending), inventory
insertions and hopper-style transfers wait while acknowledgement is pending.
Uncollected items and orbs stay in the world; returned stacks and `/give` overflow
drop there instead. If a command or other direct setter changes the destination
anyway, recovery retains that changed inventory as the inactive snapshot. A refused
switch keeps external changes in its still-active inventory. The server restores
the original inventory owner, mode and flight, then disconnects with a recovery
message. Reconnect to continue.
Closing that connection prevents stale destination actions from touching the restored
inventory; a timer never unlocks an unconfirmed destination. Player replacement
retains the original rollback state and deadline. A confirmed switch cancels recovery.
Unreadable snapshots block switching and stay intact for backup recovery. Older
saves first opened in creative keep their current items as Build and initialize
Live with the app catalogue. Disabling the desktop marker keeps stored snapshots
for when the marker is enabled again; normal worlds create no inventory tags.

After an app launch, AresOS watches for the first focus loss within 30 seconds.
On return, it closes only the pause screen created by that focus loss. An Esc
menu, a replacement screen, and focus loss without a launch stay untouched.
Each launch owns its focus tracking, so an older launch failing cannot cancel a
newer launch's return.

## The town

In a flat home every app of My apps that the system lists as installed has a
logo along the road of its group. The mod builds them by itself; you place
nothing. A logo is the gate described under "The gate" below: 12 blocks wide,
12 tall and 3 thick, a doorway at the bottom middle that opens the app, and
above it the app's name in white and its main short name (`/chrome`) in gold.

**What you see.** On day one Chrome and Discord stand left and right of the
north road, 20 blocks from the pad; Lunar Client stands on the east road,
Notepad and Terminal on the south road. Every logo faces the pad. Over each
road hangs the group's name with the number of its apps: `INTERNET · 2`,
`WORK & MEDIA · 0`. With more apps a group grows in rows: row 0 has one place
on each side of its road, row 1 two, row 2 three, 14 blocks from row to row.
A place has a name such as `N1R0`: north, row 1, right of the road as you look
outward from the pad, first from the road. From the pad you see the front row;
the rows behind it show when you walk past the row in front.

**Which group.** The first that fits the program's categories: `Game` is Games
(east), `Network` is Internet (north), office, development, education, science,
graphics, audio and video are Work & Media (west), everything else is System &
Tools (south).

**Which place.** A new app takes the nearest free place of its group (by row,
then by distance from the road, left before right). The place is saved with the
app (`place` in `config/aresos/apps.json`) and kept when the app leaves My
apps, so it comes back where it stood if the place is still free, and a new
AresOS world builds the same town. Nothing that stands moves by itself. On the
first build pinned apps go first (on a fresh AresOS that is Notepad).

**When it changes.** The town is brought in step when you enter the world, when
the system's program list changes, after `/aresos app add` and
`/aresos app remove` (the Apps screen included), and when a short name changes
(`/aresos app name`, `unname`). The chat says what changed:

| What happened | The line |
|---|---|
| A program was installed, or you added one | "Spotify is new. It stands in Work & Media, west. /spotify opens it." |
| You removed one from My apps | "Spotify left My apps. Its logo came down." |
| The system no longer lists one | "Chrome is no longer installed. Its logo came down; its place is kept for its return." |
| One is back, or the world is new | "Chrome stands in Internet, north." |
| Its icon, its name or its main short name changed | "The logo of Chrome was renewed." |
| Something of yours is in its place | "N1L0 is blocked by something of yours, so Mail stands at N1R0." |
| Every place of its group is blocked | "Mail has no free place in Internet: every place there is blocked." |
| Something of yours hangs on a logo that should come down | "The logo of Chrome stays: … The town tries again later." |
| The first logos of a town (day one) | One line, however many: "The town is built: 5 logos. /apps lists them." |
| More than five changes at once | One line: "The town changed: 7 logos built, 2 moved, 1 renewed, 3 taken down. /apps lists where your apps stand." |
| A logo's doorway was removed (by an older AresOS) and a zone of yours is in its place | "The logo of Spotify opens nothing: its doorway's zone is gone and a zone of yours is in its place." |

In a flat home this is the only line about a new program; My apps' own line
("… is new and joined My apps.") is for AresOS worlds without a town.

**Roads** are paved on to 4 blocks past the farthest row in use. A road is
never taken up again when its group shrinks.

**What you can and cannot change.**

- In Live mode the town's blocks cannot be broken, like the pad and the roads:
  "The logo of Discord is part of the town and protected. Press G for Build
  mode." Explosions never break a logo, in either mode. Signs and group names
  cannot be hit.
- In Build mode you can change any block. A block you change is yours from
  then on: the town never puts its own block back and never removes yours,
  also when the logo around it comes down or is built again.
- The town builds only where nothing is. A place counts as blocked when its
  space is not air or its ground is neither untouched grass nor the mod's own
  paving: the app stands one place on and the chat names the blocked place. So
  you can build between the rows or in a free place, and the town grows around
  it. A road is paved around your blocks in the same way.
- A logo that something of yours hangs on (a torch on its doormat) is not
  taken down until that is gone. A light you changed (its level, water in it)
  is yours from that moment, also if you change it back, and does not hold it
  up.
- A logo's sign you edited (`/data`), and an entity or zone of yours that has
  the ID the town recorded for a sign or zone, are yours: the town leaves them
  when the logo comes down.
- You cannot move a logo, choose its place or edit a group's name; moving and
  swapping come with a later package. `/aresos zone remove` and
  `/aresos logo remove` leave the town's logos alone and say that
  `/aresos app remove <app>` takes one down. Logos and zones you made by hand
  stay yours.

**`/aresos hub rebuild`** (the host, in a flat home) takes every logo down and
builds it again from the rules, each app in its saved place, and says one
line: "The town was rebuilt from the rules: 5 logos built again." What you
changed or built stays; where a block of yours is in the way of its logo, the
app moves one place on and a line says so. The pad, the roads and the names
are not built again.

**What it needs.** The system's complete program list of this game session:
while the AresOS app helper is away nothing is built and nothing is taken
down, and `hub rebuild` refuses. On Windows, where no helper lists the
programs, there is no town. The town works only while you are in the world. A
place or a stretch of road whose ground is not loaded waits and is tried again
every five seconds; no chunk is loaded for it.

**What is saved.** The standing logos are in the world's
`data/aresos/town.dat`: for each its app, its place, the hash of its 12 x 12
blocks, the converter's version, the name and short name on its sign, its
zone, and every block placed for it. The pad, the roads and the names stay in
`data/aresos/hub.dat` in the shape package 32 gave it, so an older mod that
writes `hub.dat` again loses nothing of the town. A logo's doorway and exit
are a zone in `zones.dat`, like a hand-built gate's. An older AresOS sees that
zone as a plain one and can remove it; the town puts a missing doorway back,
unless a zone of yours is in its place.

**When the town is not sure its records are its own.** Each time the game
saves the world, this mod writes `data/aresos/town-seal.dat` right after
`level.dat`: the moment `level.dat` was saved, the world's seed and a
fingerprint of `town.dat`. When the world opens and the seal does not fit, the
town's records may no longer match the world: an older AresOS (packages 32 to
35) or plain Minecraft saved the world since, `town.dat` came from a backup or
from another world, or the game stopped between the two writes (a false alarm,
on the safe side). Then the town freezes its logos: they stay protected and
their doorways work, but the town takes nothing of them down and builds
nothing over them, not when an app leaves, not on a new picture or name, not
on `hub rebuild`; new apps get logos on free ground as usual. The chat says
so once as you enter: "This world was saved without the town's records since
the town last saw it, so the town leaves its 5 logos as they are. Look them
over, then type /aresos hub trust." Change back what you want kept as yours
(a block you change is yours from then on), then type
**`/aresos hub trust`** (the host): the town takes its logos as its own again
and the seal is renewed at the next save. Nothing else ends a freeze. A world
copied or renamed as a whole stays sealed.

**When `town.dat` does not fit the world.** A `town.dat` that cannot be read,
that was saved for another home than `hub.dat`'s, or whose records overlap
(two logos of one app, in one place, on one block, with one sign or one zone,
or a logo whose blocks lie outside its place) is never used and never
replaced: the file stays as it is, the town builds nothing, takes nothing down
and paves no road in that world, and the chat says so with the file's full
path as you enter. To start the town afresh, close the world and move
`data/aresos/town.dat` out of the world's folder (or rename it); its old logos
are then plain blocks of yours, and the town builds anew on free ground.

**Known limits.** A group name's count is written at scale 2.5 so that
"SYSTEM & TOOLS · 14" fits between the two front logos. Closer than about 14
blocks to a logo its sign is above the top of the screen unless you look up.

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

### The gate: `/aresos logo <app id>`

Stand on solid ground, look where the logo should stand, and run
`/aresos logo <app id>`. The mod builds the app's icon as a **gate**: 12 blocks
wide, 12 tall and 3 thick, standing on the ground you stand on, its front six
blocks ahead and facing you, with a doorway (2 wide, 3 high, 2 deep) at the
bottom middle and the app's name floating above it. The doorway's middle is on
the block edge nearest to you. Stepping into the doorway opens the app; walking
past the gate or along its front does nothing. Closing the app puts you back
where you stood when you built it, 5.5 blocks in front of the door, looking at it.
The icon is read and turned into blocks away from the game's server thread, so
the gate stands a moment after the command; stand still meanwhile. If you moved
or left the world before it was read, the chat says so and nothing is built.

How the icon becomes blocks (`docs/design/HUB.md`, section 3.6):
- The icon is cut to what is visible and scaled to 12 × 12 cells; a cell is
  built when at least half of it is covered. A round icon gives a round gate. A
  picture that is not square stands in the middle, on the ground.
- A small figure on a plain plate (a face on a disc, a moon on a tile) is
  enlarged, and the plate's colour fills the whole 12 × 12.
- Each cell is one kind of block, three blocks deep, picked from 60 blocks: the
  wall's 48 plus red mushroom block, emerald, lapis, amethyst, snow, iron,
  polished diorite, smooth stone, smooth sandstone, honeycomb, prismarine bricks
  and blue ice. The nearest block is found in the Oklab colour space with
  lightness counted half, so a bright red stays red. The colours are averages
  measured from the game's own textures (`./gradlew measureBlockColours` prints
  them); only the numbers are in this repo.
- The doorway is cut out. Its back is black concrete, and so are the posts
  beside it and the bar above it wherever the icon has no block there.
- An app without a readable icon gets a plain front in its group's colour.

With the gate come a **doormat** (the two floor blocks under the doorway and
the two rows in front, in concrete), two invisible `light` blocks in front of
the face, and the **sign** (a text display, readable from 160 blocks, as bright
at night as by day). The doormat is light blue, red, yellow or purple by the
app's group (`browser` is Internet; `terminal` and `notepad` are System & Tools)
and light grey for any other app until the mod is told an app's categories. It
is only laid where the floor at the door is one kind of untouched natural
ground (grass, dirt, stone and the like); a paved floor is yours and stays.

A gate needs free air: its own 12 × 12 × 3 blocks, one layer in front of the
face, and a way in four blocks wide and three high out to where you stand. The
ground from you to the door must be solid. Everything is checked before the
first block changes; a refusal names the reason and changes nothing. The place
must be loaded, so build where you are.

`/aresos logo remove <app id>` takes down every gate of that app;
`/aresos logo remove here` the one you stand at (anywhere between its door and
its exit point). A removal takes each block the gate placed **only if it is
still that block**, puts the ground under the doormat back, and removes the
sign and the zone. A block you changed, replaced or mined stays as you left it.
For an older wall or floor logo the command only removes the zone and says that
the blocks stay. `/aresos zone remove` leaves gates alone.

### The older forms: `/aresos logo <app id> wall|floor`

`/aresos logo <app id> wall` and `floor` build flat pixel art as before. The nearest horizontal
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
through a solid neighbor. Only air, plain inert full blocks, natural ground (grass,
dirt, stone and the like) and the blocks the mod itself builds logos from are
accepted in that margin; this avoids firing support updates, drops or redstone before a build
can be refused. The error names the neighboring block and its position. A gate's
light blocks are checked four steps around, because their light would melt ice and snow.
**There is no overwrite command:** clear the required
space yourself in Build mode and retry. A floor logo usually needs its footprint
excavated one block deep first. The builder saves a matching zone: two blocks in
front of a wall, or two blocks of feet space above a floor. It saves your standing
position as the exit. Auto-built blocks, a gate's doormat included, resist player
breaking in Live mode and explosions in both modes; press **G** for Build mode to
mine and edit them. A gate's sign cannot be hit in any mode.

Only the singleplayer host in Live mode launches on entering from outside, once
per entry, with portal particles and a short teleport sound. A gate's zone is
exactly its doorway; a wall's is the two blocks in front of its whole face. Entry uses the
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

Zones and exact auto-built block positions persist in `data/aresos/zones.dat`;
a gate's zone also holds every block it placed with the block's ID, the ground
its doormat replaced and its sign's ID. Zones files written before gates existed
load unchanged. Keep the whole world save with backups. Client tests use original geometric icons
and save gate pictures under `../reviews/33-gate-logo/screenshots/` and wall/floor
evidence under `../reviews/08-walk-in-logos/screenshots/`.
The lime glass frames in those screenshots are test fixtures around the saved
trigger boxes; they are not placed by the logo command.


## Short app commands

In a marked AresOS world, the singleplayer host can type `/chrome`, `/browser`,
`/discord`, `/dc` or `/lunar` to open those apps from My apps. Tab completes every
saved name. Commands work in Live and Build mode; closing the program leaves you
where you stood. The request is the same as using its hotbar item, including when
the program is already open. Remote servers cannot launch local programs.

`/apps` lists My apps with their commands and group; click any line to open it.
`/open <name>` searches every listed program, including ones outside My apps, by
its short name, squeezed full name (letters and digits without spaces), or a unique
prefix. Tab completes program names. An exact name wins over longer prefixes;
several matches give clickable choices. An app ID is not a search key. Clicked
lines run `/aresos app open <app id>` (host only), so two programs with identical
names stay apart and another mod's `/open` never receives a click.

`/aresos app name <app id> <new name>` adds a name and makes it the main name.
`/aresos app unname <name>` removes one; add another first to remove the last name.
Use 2–16 lower-case letters or digits, starting with a letter. A refusal explains
invalid or reserved names and says which app holds a conflicting name. Minecraft's
commands and `aresos`, `home`, `go`, `open`, `apps` are always reserved (`home` and
`go` are reserved for later packages). Other mods' existing commands win too.

Names are saved in schema 4 of `config/aresos/apps.json`, in `names`, main first.
The migration keeps an untouched sibling backup of older schemas. Names survive
program renames and removal from My apps; an app outside My apps has no short
command, and keeps its names for its return. A program that the AresOS app helper's
latest complete list no longer names is saved with `"absent": true`: it keeps its
names and its place in My apps, but has no command, `/open` neither finds nor
completes it, and `/apps` shows it as not installed, without a click. The next
complete list that names it again brings it all back. While the helper is down,
the last complete list stays in force, also across a restart. Windows discovery
marks nothing absent. A newly reserved real command forces
an alternative app name. Apps… shows the main name beside each of My apps and
searches all saved names. Newly built gates show `/mainname` on the second sign
line; standing gates keep the text they were built with. The town's logos follow:
a changed main name renews the logo in place.
