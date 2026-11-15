# 30 review fixes 1: the helper stays up, and windows have real owners

Follow-up to `briefs/30-installed-programs.md` on the same branch (`pkg/30-installed-programs`, PR #55). Two fresh reviews on `08753aeb`, both CHANGES-NEEDED:

- `reviews/30-installed-programs/SECURITY-1.md` (gpt-6-astra): five FIX findings, one known limit;
- `reviews/30-installed-programs/REVIEW-1.md` (gpt-6-astra): one blocking and six should-fix.

All twelve are accepted. Read both reviews, the first brief, `reviews/30-installed-programs/REPORT.md`, `docs/design/HUB.md` 3.8 and the helper before changing anything.

**Builders:** Claude agents (Opus 5.5) in two steps, one fresh builder each, because Codex's weekly allowance is nearly used. **Review:** the same two reviews check only these fixes.

## Step A: the security review's five fixes

1. **Discovery can't stall or exhaust the helper** (FIX 1). Reading the application folders happens off the serving loop, in a worker with hard bounds that count every entry looked at, not only the accepted ones: folders and files visited, bytes read per file and in total, and time per scan. While a scan runs, fails or hits a bound, the last good catalogue stays in force and the helper keeps answering; a scan that hit a bound says so once in the log. Tests: ten thousand hidden entries, many hard links to one large malformed entry, a folder that keeps changing.
2. **The icon converter has a real memory ceiling** (FIX 2). The converter's process and everything it starts get an operating-system limit on memory (an address-space limit set before it starts, or a memory-limited scope; say which and why), and an SVG that refers to any picture inside or outside itself (an `image` element, a `data:` or external reference, `foreignObject`, an external `use`) is refused before conversion: app icons are drawn shapes. Tests with a small SVG that embeds a large compressed picture, and one per refused construct.
3. **The icon cache has a budget** (FIX 3): a total limit in bytes and files; pictures of programs that are no longer listed, and older generations of a program's picture, are removed; when the budget is used up a new picture is simply not cached and the program keeps its fallback look. A test that changes one icon's time a thousand times and counts the files.
4. **systemd changes no argument** (FIX 4): the launch command passes `--expand-environment=no` before `--`. A test through the real `systemd-run` route (no window needed): a stand-in program that writes its arguments to a file receives a literal `${HOME}` unchanged, from `Exec`, from `%c` and from `%i`.
5. **Links are checked before anything is read** (FIX 5). A desktop file that is a link must resolve inside the application folders or inside a Flatpak deployment (`/var/lib/flatpak/`, `~/.local/share/flatpak/`); anything else is skipped with one log line. Icon theme folders are checked the same way before they are listed, and a Flatpak export's icon link into its deployment is allowed (this also settles the package review's finding 5: Flatpak programs get their pictures). Reads use descriptors opened after the check, so the file read is the file checked. An explicit absolute `Icon` path stays allowed as today. Tests: a link to a file outside, a link into a Flatpak deployment, a theme folder that is a link out, a realistic Flatpak export layout.

## Step B: the package review's findings

1. **Windows belong to a program by a reviewed identity, never by a guess** (finding 1, blocking). Remove the rule that the only live discovered program owns windows nobody claims. Instead:
   - reviewed, image-shipped **hints**: `/usr/share/aresos/apps/hints/<name>.json`, each naming a desktop file ID and extra window identities for it, exact (`app_ids`) or by prefix (`app_id_prefixes`); validated as strictly as registry entries; a hint never beats a registry entry's identity. Ship two: Lunar Client (`lunarclient.desktop`, game window `com.mojang.minecraft`; seen on the laptop on 2026-11-13: the launcher's window is `lunarclient`, the game's is `com.mojang.minecraft`) and Steam (`steam.desktop`, prefix `steam_app_`, the identity Steam gives its games; say in the report that this one was not seen on the laptop);
   - a window nobody owns is nobody's: it never confirms a launch, never keeps a program "open", and its closing never sends him to the hub by force. The hub gets the focus then only when the compositor gives it;
   - when a program's last owned window closes while a window nobody owns is open, the helper does not pull the hub in front of it.
   Tests, all with their closing consequences and with time moving: Lunar with Chrome open; Lunar's launcher closed before, with and after the game window appears; Discord resident without a window while an unrelated window opens; Steam with a game window.
2. **A 1.0 client sees today's behaviour, windows included** (finding 2): with a 1.0 client only the registry's identities own windows and trigger returns, also after a reconnect. A test that builds the catalogue the way production does, with a 1.0 connection.
3. **A 1.0 client asking for a discovered ID** gets exactly the old failed-launch answer (the fields and the journal entry), and a repeated request ID behaves as before (finding 3). Compare whole answers with the old helper's.
4. **A return that is no longer wanted is dropped** (finding 4): after app A closed and the compositor moved to B, a deliberate switch or launch to C cancels A's pending return. A test for A closes, B takes focus, C is chosen, without the hub in between.
5. **Flatpak's markers only for Flatpak** (finding 6): the file-forwarding markers are removed only in a recognised `flatpak run … --file-forwarding` command; in any other command `@@` is an ordinary argument. Tests both ways.
6. **A Flatpak's app ID comes from its command** when the entry has no `X-Flatpak` key (finding 7), for the details sent to the game and for its window identities; if it can't be worked out, the detail is left out, not invented.

## Verification

- A test for each fix that fails without it. Run only the helper's tests on the laptop (`python3 -m unittest discover -s os/tests -p 'test_aresos_shell*.py'` and your new modules); never the whole `os/tests` suite (AGENTS.md).
- The headless end-to-end check of the first brief once more at the end of step B (kcalc and btop), plus the real-route test of fix A4.
- At the end of step B: push, then both hosted runs (`gh workflow run "OS image" --ref pkg/30-installed-programs -f checks_only=true`, and with `-f check_build=build`), each awaited with one blocking `gh run watch`.
- `reviews/30-installed-programs/REPORT.md` gets a section "Review fixes 1": per finding what changed, what you ran, what it printed; the hints file format; known limits (windows nobody owns; Steam's prefix unseen).
- Update `docs/design/OS-BASE.md` B1 where the behaviour described there changed (hints).

## Rules

- As in the first brief. Worktree `/var/home/ares/AresOS-30-installed-programs`; push; never merge; never `--no-verify`. Files you may touch under `os/`: the helper, `config/usr/share/aresos/apps/` (the three entries and the new `hints/` folder), the helper's tests and fixtures, and `ci/image-checks.sh` to add checks. The example messages under `mod/src/test/resources/shell-1.1/` stay unchanged.
- The real session is the owner's: never open a window there, never send input. The owner may be playing: before a headless compositor with programs in it, check that no Java process runs from `~/.lunarclient/` and that 4 GB are available; otherwise wait with a blocking sleep of several minutes. The helper's unit tests may run at any time.
- Each step ends with commits, a push and `reviews/30-installed-programs/PROGRESS.md` (done, left, decisions); step B deletes it.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
