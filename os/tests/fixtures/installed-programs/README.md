# Desktop-entry fixtures for package 30

Copied from the AresOS laptop on 2026-11-13, without starting any program:

- `lunarclient.desktop`: `$HOME/.local/share/applications/`. Every home path is replaced by `@HOME@`; tests substitute their temporary folder. No AppImage or icon is copied.
- `com.discordapp.Discord.desktop`: the user's Flatpak export, `$HOME/.local/share/flatpak/exports/share/applications/`.
- `org.mozilla.firefox.desktop`: `/var/lib/flatpak/exports/share/applications/`.
- `steam.desktop`, `btop.desktop`, `foot.desktop`: `/usr/share/applications/`.

Localized keys were removed to keep the fixtures small. Plain keys and desktop action groups are preserved. In particular, the real btop entry has `Hidden=true`; the terminal-launch test explicitly changes that in its private copy. Invalid text, oversized input, hidden overrides, ID collisions and 500-entry catalogues are generated in each test's temporary folder.

These files are text-only launch definitions. The tests mock all launches and executable lookup; they never run these programs or read their icons.

`drawn.png` and `drawn.svg` are original 8×4 test drawings made for A6, not copied app icons.
The PNG was drawn as RGBA bytes and encoded with Python's `struct` and `zlib`: two red columns,
two half-transparent blue columns, then four transparent columns, repeated over four rows.
The SVG draws two green columns and two half-transparent gold columns on the same transparent canvas.
Both deliberately have a 2:1 aspect and partial alpha so the tests can verify scaling, padding and transparency.
Hostile icons, FIFOs, symlinks, converter scripts and oversized files are generated in private test scratch.

`breeze-index.theme` (review fixes 3) was written for the tests, not copied from KDE: an index.theme in the form of
Breeze's own (`<context>/<size>` folders described by `Size`, `Type` Fixed or Scalable, `Scale`), with a few folders
of each type and one scaled folder listed among the plain ones. The tests copy it into a temporary icon root and put
the drawings above at `breeze/apps/48/` and `breeze/apps/64/`, where Breeze keeps application pictures.

`test_aresos_shell_icons.py` is the portable helper unit module. The real ImageMagick 7/bubblewrap
checks are in `check_aresos_shell_icons.py` (with one read-only lookup in the machine's real icon folders), run explicitly on AresOS with
`python3 -m unittest discover -s os/tests -p 'check_aresos_shell_icons.py' -v`.
They fail if the route is missing; they do not skip. Ubuntu's ordinary regression job has no Fedora
ImageMagick 7/runtime layout and runs the unit module without requiring that conversion route.
