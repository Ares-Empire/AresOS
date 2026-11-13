# Desktop-entry fixtures for package 30

Copied from the AresOS laptop on 2026-11-13, without starting any program:

- `lunarclient.desktop`: `$HOME/.local/share/applications/`. Every home path is replaced by `@HOME@`; tests substitute their temporary folder. No AppImage or icon is copied.
- `com.discordapp.Discord.desktop`: the user's Flatpak export, `$HOME/.local/share/flatpak/exports/share/applications/`.
- `org.mozilla.firefox.desktop`: `/var/lib/flatpak/exports/share/applications/`.
- `steam.desktop`, `btop.desktop`, `foot.desktop`: `/usr/share/applications/`.

Localized keys were removed to keep the fixtures small. Plain keys and desktop action groups are preserved. In particular, the real btop entry has `Hidden=true`; the terminal-launch test explicitly changes that in its private copy. Invalid text, oversized input, hidden overrides, ID collisions and 500-entry catalogues are generated in each test's temporary folder.

These files are text-only launch definitions. The tests mock all launches and executable lookup; they never run these programs or read their icons.
