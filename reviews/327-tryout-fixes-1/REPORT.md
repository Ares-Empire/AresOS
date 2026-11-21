# Package 327 — first home try-out fixes

## Done

- Session desktop worlds hide Minecraft tutorial, recipe-unlock and advancement toasts and save `tutorialStep:none`. System and mod toasts can still appear.
- Live refuses every player mining attempt that would break a block in a desktop world. Logos, the pad and the roads keep their specific action-bar messages. Ordinary blocks point to G and the menu.
- Esc shows the synced Build mode. The button switches through the same request as G. **Start a new home…** and its confirmation explain that the current world stays in the saves.
- The built-in Terminal has a black concrete hotbar item and a gate with a light `>_` prompt on a black face. Other dark neutral icons also get more neutral blocks from the shared gate palette. The design is in [HUB.md](../../docs/design/HUB.md).
- The town keeper checks the desktop marker before changing the world. While desktop mode is off, gates and records stay as saved and pending automatic work waits for the marker to be enabled.

## Terminal appearance and refresh

I resolved the three image starter entries against the installed system desktop files and icon directories, using the repo's helper code with a worktree-local cache. `terminal.json` gets its icon from `foot.desktop`, which specifies `Icon=foot`. The helper chose the hicolor 48 × 48 Foot PNG and wrote a normalized 128 × 128 PNG. The center was `#282828`. A sampled rim pixel was `#C8C7C4` at 72% opacity, and a sampled glyph pixel was `#ECE2BC`. The original PNG supplies the rim. The old gate palette also chose brown-looking gray terracotta for the neutral face. Converter 2 drew 78 gray terracotta cells and 34 white concrete cells. The brown hotbar block and its pale trim came from the command-block fallback. A generated hotbar icon used Foot's dark face and pale rim instead.

The shared matcher gives lightness less weight for dark neutral input. Foot's charcoal now maps to gray concrete when converted through the shared path. The Terminal gate uses an original block drawing to remove the source rim and keep the prompt legible. It has 129 black concrete cells and nine white concrete cells, plus the six doorway cells. The starter's saved command-block look refreshes to black concrete in its existing hotbar slot. Explicit icon paths still take precedence.

The town keeper renews older converter versions when desktop mode is enabled, it gets a complete app list and the site is loaded. The client test rebuilt the old Terminal gate in its original place. If a town gate still needs a refresh, `/aresos hub rebuild` runs the existing rebuild checks. A manually placed Terminal gate can be rebuilt by standing at its doorway, using `/aresos logo remove here`, then running `/aresos logo terminal` from the intended gate entrance. The town's usual ownership and obstruction checks still apply.

## Verified

- `mod/dev/build.sh --console=plain` passed the initial build in 3m 2s. It reported all 106 required server game tests passed. The unit XML had 337 tests, six existing Windows-only skips and zero failures or errors.
- The first full client attempt, `mod/dev/client-test.sh --keep-screenshots .work/327-tests/client-1-pictures --console=plain`, stopped after 11m 46s with exit 1. The town-arrival fixture still clicked `New home…`. I updated the selector to the new label and kept its arrival, save-switch and expiry assertions.
- The focused package run used `mod/dev/client-test.sh --keep-screenshots .work/327-tests/focus-pictures --console=plain --init-script "$PWD/.work/327-tests/focus.init.gradle"`. It printed `327 checks passed` and returned exit 0 after 49s. The local init script selected only package 327 in the generated test manifest and restored the full list on exit.
- The same focused command with `ARESOS_STARTER_ICONS="$PWD/.work/327-icon/starters"` and `--keep-screenshots .work/327-tests/starter-before-pictures` captured the converter-2 starter gates and printed `327 checks passed`. It returned exit 0 after 50s.
- Both pre-review passes ran the complete build and client suite on the headless NVIDIA RTX 4060.

```bash
ARESOS_STARTER_ICONS="$PWD/.work/327-icon/starters" mod/dev/client-test.sh --keep-screenshots .work/327-tests/final-1-pictures --console=plain build --rerun-tasks
ARESOS_STARTER_ICONS="$PWD/.work/327-icon/starters" mod/dev/client-test.sh --keep-screenshots .work/327-tests/final-2-pictures --console=plain build --rerun-tasks
```

- Pass 1 printed `BUILD SUCCESSFUL in 16m 49s` and returned exit 0 after 16m 50s.
- Pass 2 printed `BUILD SUCCESSFUL in 16m 51s` and returned exit 0 after 16m 52s.
- Both executed 19 Gradle tasks, reached all 29 client entrypoints, printed `327 checks passed` and reported all 106 required server game tests passed. Each unit XML set contained 338 tests with 332 passed, six existing Windows-only skips and zero failures or errors. The toast unit test covers tutorial, recipe, advancement, system and custom toast kinds.

The package's client check waits for the vanilla tutorial in an ordinary world and in a desktop world outside the session. In a session home it checks for the absence of tutorial toasts, reads the saved tutorial setting and confirms a system toast still queues. It tries mining the same grass block in Live and Build with the attack input, checks the action-bar text, switches both ways in the menu and checks the label after G. It also checks the old gate and pinned item refresh in place. The existing home-switch tests still exercise cancel, save retention and recovery.

### Review 1 regression

The server test `theTownTrustsItsRecordsOnlyWhileTheWorldWasSavedWithThem` reloads a saved converter-2 gate record while the desktop marker is off. It verifies that a complete-list keeper pass preserves the gate record and blocks, including a missing panel. It then enables desktop mode and verifies that the keeper renews the gate in place, updates the converter stamp and fills the opening.

The first `mod/dev/build.sh --console=plain --rerun-tasks` exited 1 with `Fixture: the saved version-2 gate did not load as an active town record`. Mining updates the gate's ownership record, so the regression now snapshots the record after mining and compares it with the loaded record and the record after the disabled pass.

The next build exited 1 with `A fresh home: []`. The fixture crash had left town records in the generated server test world, so I set that world aside within the worktree and moved the regression into the existing save-and-reload fixture, which cleans up saved town records on failure.

The two full verification passes used these commands from the worktree root.

```bash
export ARESOS_STARTER_ICONS="$PWD/.work/327-icon/starters"
for pass in 1 2; do
    mod/dev/build.sh --console=plain --rerun-tasks
    mod/dev/client-test.sh --keep-screenshots "$PWD/.work/327-review-1/client-$pass-pictures" --console=plain --rerun-tasks
done
```

| Pass | Build | Headless client |
| --- | --- | --- |
| 1 | `BUILD SUCCESSFUL in 2m 53s` | `BUILD SUCCESSFUL in 14m 16s`, script exit 0 after 14m 17s |
| 2 | `BUILD SUCCESSFUL in 2m 57s` | `BUILD SUCCESSFUL in 14m 15s`, script exit 0 after 14m 16s |

Both builds exited 0 and printed `All 106 required tests passed :)`. Each unit run had 338 tests, with 332 passed, six existing Windows-only skips and zero failures or errors. Both client runs loaded the full list of 29 entrypoints on the headless NVIDIA RTX 4060 and printed `327 checks passed`. The runs copied their screenshots into `.work/327-review-1/`. The committed screenshots below are the original package captures.

### Test-game screenshots

- [Esc menu at 1920 × 1080](screenshots/0100_327-menu-1920x1080.png)
- [Esc menu at the minimum GUI height](screenshots/0101_327-menu-smallest-gui.png)
- [New home confirmation](screenshots/0102_327-new-home-confirm.png)

| Starter | Before | After |
| --- | --- | --- |
| Terminal | [Foot through converter 2 and the command-block hotbar fallback](screenshots/0103_327-terminal-before.png) | [Black prompt gate and hotbar item](screenshots/0104_327-terminal-after.png) |
| Chrome | [Converter 2](screenshots/0107_327-browser-before.png) | [Converter 3](screenshots/0105_327-browser.png) |
| Notepad | [Converter 2](screenshots/0108_327-notepad-before.png) | [Converter 3](screenshots/0106_327-notepad.png) |

The Chrome and Notepad comparisons used normalized PNGs resolved from `google-chrome.desktop` and `org.kde.kwrite.desktop`. Their gate hashes matched before and after. Both Notepad captures show the updated Terminal in the background. The Foot fixture and historical block layout are credited in [the fixture notes](../../mod/src/gametest/resources/fixtures/terminal/README.md).

No files over 500 MB remained in `.work/`.

## Not verified

The owner's running Prism instance, home save and actual hotbar were outside the test scope. The before evidence reproduces the installed default icons, the old palette and the command-block fallback in the headless client.

## Known limits

- The mining rule uses the player block-break event. Ordinary terrain can still take explosion damage. Hub-owned explosion protection, other block damage and placing retain their existing rules.
- The dedicated AresOS profile keeps the tutorial setting at `none`. A normal world manually opened in that same profile uses its saved tutorial setting and vanilla toast rules.
- A town gate can wait for its chunks or an obstruction to clear. The keeper preserves blocks it no longer owns.
- The Terminal client fixture uses the old picture with the current converter stamp. It covers picture-driven renewal and the pinned item refresh. The server tests cover renewal of an older converter stamp and the desktop marker.
- Owned roads still use the shared pad-and-roads mining refusal. The brief calls for special wording for logos and the pad.

## JUDGMENT-CALL

I used vanilla black concrete for the Terminal hotbar item and drew a `>_` prompt for the gate. Reusing Foot's footprint after masking the rim would retain the small, busy symbol visible in the 12-block before capture. The glyph can be changed in the mod's gate drawing. The resulting picture hash will drive the same town refresh.

## PLAN-GAP

None beyond the appearance ambiguity covered by the before captures.

## Open questions

None.
