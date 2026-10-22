# 07 — Real apps and generated icons

PR: [#6](https://github.com/carlsenares/AresOS/pull/6) against `main`; not merged.

## Done

- `config/`: schema-2 app documents, HTTP(S) URL entries, strict whole-file validation,
  schema-1 byte-for-byte versioned backups before atomic migration, idempotence,
  and atomic pin/merge writes that preserve unknown optional fields. Windows argv,
  IDs, names, looks and pins survive migration. Invalid config disables loading
  with a log/chat diagnostic and never replaces it with defaults.
- `catalogue/` and `resources/aresos/windows-discovery.ps1`: one catalogue interface,
  user/common Start Menu shortcut discovery and AppsFolder AUMIDs with current-user
  package logos. Windows launches shortcuts via Explorer to retain shortcut
  arguments/working directory; existing configured argv stays untouched. Stable
  hashed IDs, known Notepad aliases and exact direct-target matches retain owner IDs.
  Existing entries are never removed; newly found apps are never auto-pinned.
- `client/launch/`: URLs use the default browser through the launcher and existing
  click-edge/focus-token handling. Linux list/open adapters are helper stubs for
  `aresos-shell/1.0`; commands and URLs fail closed without starting a process.
- `icon/`, `RuntimeIconPack`, `IconPackMixin`, `AppItems`: real shortcut/resource/UWP
  images become content-hashed 16×16 textures in the game-local required runtime
  pack. Source bytes and converter version invalidate the cache. Owned cache paths
  refresh after moving the game folder; custom PNG paths are preserved. Missing/unreadable
  images use the configured vanilla look. The converter is one replaceable interface.
  Saved app items refresh their configured model/name on Live entry without changing IDs.
- `AppInventory`, `AppInventoryMixin`, `AppsScreen`, `TakeAppPayload`: Live desktop
  inventories fill empty slots without overwriting ordinary items. E → Apps… offers
  27 items per page, including overflow. Selecting an app moves its existing item
  (or creates a missing one) to the vanilla cursor. Completed inventory moves save
  hotbar membership as pins. Host/Live/desktop guards protect the new write/pickup
  paths. Normal worlds and Build mode receive no catalogue UI or automatic placement.
- `restoreLegacyApps` explicitly restores an original schema-1 backup after keeping
  a versioned schema-2 copy and printing a later-edits warning. It does not run on
  startup/build. `mod/README.md` documents configuration, URLs, migration, recovery,
  caches and inventory use; `.gitignore` excludes local app lists and icon caches.
- Tests use handmade geometric PNG/ICO fixtures, fixture shortcuts and fixture UWP
  records. No installed owner app list, app icon, Mojang or vendor source asset was added.

Windows API references checked for this implementation: [AUMIDs/AppsFolder](https://learn.microsoft.com/en-us/windows/configuration/store/find-aumid),
[shortcut icon locations](https://learn.microsoft.com/en-us/windows/win32/shell/links),
[ExtractIconEx handle/index contract](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-extracticonexw),
and [UWP logo variants](https://learn.microsoft.com/en-us/windows/apps/design/style/iconography/app-icon-construction).

## Verified

Final runtime implementation is `0f59a5e`; `95d172e` only corrects README encoding
and restores the original Unicode fixture label. No runtime code changed between
the two final complete passes. The corrected Unicode case also passed an additional
unit rerun between them. All runs used the Java 25 / Minecraft 26.2 dev client on Windows.

| Command in `mod/` | Observed output/result |
| --- | --- |
| `.\gradlew.bat build runClientGameTest --rerun-tasks` (final pass 1, `build/final-pass-2.log`) | `BUILD SUCCESSFUL in 5m 42s`; `19 actionable tasks: 19 executed`; 22 unit tests, `All 16 required tests passed :)`, all five client entrypoints completed. |
| `.\gradlew.bat build runClientGameTest --rerun-tasks` (final pass 2, `build/final-pass-3.log`) | `BUILD SUCCESSFUL in 5m 43s`; `19 actionable tasks: 19 executed`; the same 22 unit tests, 16 server tests and five client entrypoints completed. |

JUnit XML: 5 suites, 22 tests, 0 failures, 0 errors, 0 skipped. The new client checks
printed `07 client checks passed: fixture textures and mounted models, normal/Build
gating, inventory and page 2, vanilla drag pin/unpin persisted across config reload
and rejoin, overflow item pickup, URL one launch per click`. This checks mounted
resources AND non-missing baked models, vanilla inventory clicks sent to the server,
both pin and unpin, a disk-config reload before rejoin, overflow pickup, and separate
held/new URL presses through the fake launcher. [Selected exact console output](verification.txt).

`.\gradlew.bat --stop` after verification/PR creation printed `Stopping Daemon(s)`
and `1 Daemon stopped`. Only the included Gradle 9.8.0 wrapper was used; no other
Gradle version was started. A final stop is repeated after the report push.


Additional development commands and observed results:

- In `mod/`, `.\gradlew.bat build` before changes: `BUILD SUCCESSFUL in 30s`,
  `All 15 required tests passed :)`, 13 unit tests passed.
- `.\gradlew.bat genSources`: `BUILD SUCCESSFUL in 8s` (used local APIs to inspect
  Minecraft 26.2 resource-pack and inventory hooks; no decompiled sources committed).
- From the repo, `.\mod\gradlew.bat -p mod compileJava compileClientJava`:
  `BUILD SUCCESSFUL in 9s`.
- `.\mod\gradlew.bat -p mod test`: `BUILD SUCCESSFUL in 7s`, 19 unit tests passed.
- `.\mod\gradlew.bat -p mod compileGametestJava test`: `BUILD SUCCESSFUL in 12s`,
  20 unit tests passed after adding the Linux launcher check.
- An initial `.\gradlew.bat runClientGameTest` failed during bootstrap because
  `AppMenuPins` was a normal interface inside the reserved Mixin package. Moved it
  into `item/`; the next full client run printed `BUILD SUCCESSFUL in 5m 14s`.
  No assertion was weakened or skipped to fix that failure.
- `.\gradlew.bat build runClientGameTest --rerun-tasks` before the cache-path
  follow-up: `BUILD SUCCESSFUL in 5m 42s`, all 19 tasks executed, 21 unit tests,
  16 server tests and all five client entrypoints passed.
- `.\gradlew.bat build runClientGameTest` before the final downgrade-recovery
  addition: `BUILD SUCCESSFUL in 5m 41s`; 20 unit tests, 16 server tests and all client
  entrypoints, including the new 07 checks, passed.
- Fixture PNG/ICO inputs were created with Python geometry; the two goldens were
  generated explicitly with `javac -cp mod/build/classes/java/main .work/GenerateGolden.java`
  and `java -cp '.work;mod/build/classes/java/main' GenerateGolden` (both exit 0,
  no stdout), then visually reviewed in the actual client screenshots. Tests compare
  all golden pixels and never regenerate them automatically.
- `.\gradlew.bat test --rerun-tasks` after restoring the intended Unicode fixture
  label and correcting README encoding: `BUILD SUCCESSFUL in 5s`, all 22 unit tests
  passed, all seven tasks executed. This text cleanup changed no runtime code.
- From the repo, `.\mod\gradlew.bat -p mod restoreLegacyApps
  '-PappsConfig=C:\Users\pab\AresOS-07-real-apps\.work\downgrade\apps.json'
  '-PappsBackup=C:\Users\pab\AresOS-07-real-apps\.work\downgrade\apps.json.schema-1-fixture.bak'`:
  `BUILD SUCCESSFUL in 1s`; printed `WARNING: restoring the schema-1 backup. Later
  apps, names and pins remain ONLY in ...` and `Restored original schema-1 apps.json.`
  A Python byte/JSON check printed `Recovery smoke: exact schema-1 bytes restored;
  later schema-2 edits retained.` Only repo-local fixture files were used.
- `git diff --check`: exit 0, no whitespace errors.

Config tests that previously expected broken files to be replaced with defaults
were updated to assert the brief's preserve-and-stop behavior, including repeated
invalid files, duplicate IDs and byte-for-byte preservation. Other earlier checks remain.
Offline client runs print profile-key HTTP 401/Realms warnings, the existing
anisotropic-filtering warning, occasional world-generation “Can't keep up” messages
and Gradle deprecation notices; these did not fail the suites.

### Screenshots and icon appearance

- [Inventory of fixture apps](screenshots/0000_07-inventory-fixtures.png)
- [Apps page 2, including overflow](screenshots/0001_07-apps-page-2.png)
- [Pins after config reload and rejoin](screenshots/0002_07-pins-after-rejoin.png)

Inspected all three. The teal/yellow compass and pink/navy sunset keep their
recognizable silhouettes in inventory and hotbar slots, with crisp edges and no
missing-texture checkerboards. The fixture URL intentionally has the configured
vanilla paper look. These screenshots contain fixture apps only. Earlier package
screenshots generated by the regression suite are not part of this change.

## Not verified

- Actual installed owner app discovery, arbitrary Store package/shortcut icon
  variants, and real application/default-browser/UWP launch/focus/close behavior.
  Test runs disable real discovery and use the fake launcher; nothing was opened
  in the owner's Minecraft or Lunar folders. The catalogue's fixture test invokes
  the real Windows shortcut/icon APIs but injects UWP records at the enumeration boundary.
- Full suites ran on Windows/Java 25. The native shortcut fixture test requires
  Windows PowerShell; no Linux-host build/test run was performed.
- Linux OS-helper transport, handshake, real catalogue, availability/lifecycle and
  window association: deliberately still a stub, never a direct-command fallback.
- Human preference for generated icons across a large real catalogue and practical
  startup cost. To try: use the dev client, mark/open an AresOS world, open E → Apps…,
  pick an overflow item, pin/unpin it, leave/rejoin, then launch a harmless app/URL.

## JUDGMENT-CALL

- **Pixel style:** area-average into a 14×14 fit inside a 16×16 item, binary alpha,
  six-level channel quantization and at most 15 visible colors. This keeps a small
  transparent margin and recognizable shapes. Rejected smoothing/full-color output
  and AI styling for this package. A later style costs a converter version bump,
  fresh cache/goldens and visual review; saved item IDs do not change.
- **Website look:** no network favicon requests; URLs use `look` unless the owner
  supplies a local icon path. This takes the brief's generic-look fallback. Adding a
  fetcher later needs cache/network policy but no schema or saved-ID migration.
- **Windows identity:** shortcut IDs hash normalized relative Start Menu paths;
  Store IDs hash AUMIDs. User shortcuts take precedence over the same common path;
  identical executable/argument targets collapse. Known Notepad aliases and exact
  configured direct targets retain existing IDs. Rejected display-order IDs.
  Renaming a shortcut path can add a new discovered ID; the old config/door/item ID
  remains intact. A richer future alias table could unify those without renumbering.
- **Inventory feel:** preserve ordinary items and only fill empty slots. Configured
  pins that cannot fit remain configured, with overflow in inventory/the Apps page.
  Moves commit when the cursor is empty; moving between hotbar slots keeps the pin.
  The Apps screen picks up an item for placement instead of launching directly.
  Replacing the whole survival inventory or saving hotbar positions would cost a
  separate inventory-state design and is not included here.

## PLAN-GAP

- B1's future Linux `list_apps` wire response lists IDs/names/availability/reasons
  but no icon data/reference. Real Linux discovery/icons will need a reviewed helper
  capability or asset contract; the present stub makes no claim to implement that helper.
- A package-01 mod cannot know about schema 2. Downgrade recovery therefore needs
  the explicit documented restore command while the client is closed; it retains
  later edits and warns before restoring, rather than trusting the older parser.

## Open questions

None block this package. The owner can tune the icon style after trying real apps;
real Windows app/window behavior and the future Linux helper still need their own checks.

## 07b — Real apps review fixes

This section supersedes package 07's launch-identity and overflow behavior above.
Runtime/test commits: `564ff12` (discovery/icons), `b4e712b` (pins/overflow).
PR #6 remains against `main`; no merge was performed.

### Done

- `WindowsAppCatalogue`, `windows-discovery.ps1`: reconcile every existing command
  against all complete launch identities before choosing aliases or Explorer
  wrappers. Windows supplies parsed argv, working directory and shortcut AUMID;
  configured executable names resolve through Windows' application search without
  altering owner argv. Existing shortcut wrappers are matched before an earlier
  alias can replace their representative. Different directories/AUMIDs remain
  distinct, including same-named user/common menu entries. Ambiguous existing
  matches keep every owner entry and log all matching IDs.
- `WindowsLaunchIdentity`, `AppDefinition`, `AppsConfig`: optional schema-2
  `launchIdentity` metadata survives config reload and alias removal. Commands,
  names, looks, pins, custom icons and unknown owner fields remain intact. Merge
  uses reconciled IDs rather than discarding another entry solely for equal argv.
  Repurposed IDs receive no automatic overwrite. Existing entries are never deleted.
- Icon refresh: a failed configured extraction returns an explicit empty icon
  result and removes the owned source PNG. Missing files are not passed to Windows
  for a generic file-type icon. `IconPack` then removes its old generated model,
  texture and fingerprint, allowing `look` to show. Custom icon paths are preserved.
- `AppInventoryMixin`: observe server-side container clicks beyond `InventoryMenu`,
  keeping Live/desktop/host guards and completing saves only when the cursor is
  empty. Chest pin/unpin now reaches `apps.json`.
- `AppItems`: move the existing configured pin into the first free hotbar slot,
  preserving the stack and clearing its old inventory/offhand slot. Full hotbars
  keep overflow; ordinary stacks are never overwritten or duplicated.
- Tests: eight new catalogue regressions (including real Windows shortcut/icon
  fixtures), one new client entrypoint for chest moves and overflow/rejoin, and
  stronger existing server assertions for moving rather than duplicating pins.
  The chest test also checks normal-world/Build guards and pickup-before-placement.
  `mod/README.md` documents metadata, container pinning and promotion of overflow.

### Verified

All commands below ran in `mod/` with the included Gradle 9.8.0 wrapper, Java 25,
Windows and the isolated dev client. Raw logs remain in ignored `mod/build/`;
[selected exact output](verification-07b.txt) is committed with this report.

**Failure before fixes:** `.\gradlew.bat test --tests dev.aresos.catalogue.WindowsCatalogueFixesTest --rerun-tasks`
first printed `4 tests completed, 4 failed` / `BUILD FAILED in 10s`. The initial client
regression printed both chest pin failures and the overflow/rejoin failure /
`BUILD FAILED in 28s`.

After adding native and ambiguity coverage, repeated the proof with the final
tests: temporarily restored `cf62b88`'s catalogue/PowerShell adapter, retaining
only constructor/decoder/diagnostic test seams in that class so the tests compile.
The surrounding metadata plumbing and ID-only config merge remained enabled;
the discovery behavior itself was original. Restored the fixed files byte-for-byte
in `finally`. Separately restored
only the original pin mixin/item placement for the final client regression, again
restoring fixes in `finally`. No assertions were weakened or skipped.

| Command | Observed output/result |
| --- | --- |
| `.\gradlew.bat test --tests 'dev.aresos.catalogue.WindowsCatalogue*' --rerun-tasks` with original discovery behavior | `10 tests completed, 8 failed`; `BUILD FAILED in 7s`. Every new catalogue test failed. Alias: 2 IDs instead of 1; configured argv: 2 apps instead of 1; cwd/AUMID: 1 app instead of 2; failed icons retained generated paths. |
| `.\gradlew.bat runClientGameTest` with original pin behavior | `BUILD FAILED in 30s`; `07b chest pin: apps.json stayed unpinned`, `07b chest unpin: apps.json stayed pinned`, `07b overflow rejoin: pinned app did not enter freed hotbar slot`. The final test verifies the actual item moves through vanilla mouse input/server packets before checking persistence. |
| `.\gradlew.bat test --rerun-tasks` with all fixes restored | `BUILD SUCCESSFUL in 7s`; 30 tests passed, including both native fixtures and all six decoder regressions. |
| `.\gradlew.bat build runClientGameTest --rerun-tasks` (final pass 1, `build/07b-final-pass-1.log`) | `BUILD SUCCESSFUL in 5m 54s`; `19 actionable tasks: 19 executed`; 30 unit tests, 16 required server tests and all six client entrypoints passed. |
| `.\gradlew.bat build runClientGameTest --rerun-tasks` (final pass 2, `build/07b-final-pass-2.log`) | `BUILD SUCCESSFUL in 5m 51s`; `19 actionable tasks: 19 executed`; the same 30 unit tests, 16 server tests and six client entrypoints passed. |

Both final passes use exactly `b4e712b`'s runtime and test sources. Each ran
all 30 unit tests (6 suites, 0 failures/errors/skips), all 16 required server tests,
and all six client entrypoints, including the existing deterministic Nether search.

Other development verification:

- `.\gradlew.bat test --rerun-tasks` after the first fixes: `BUILD SUCCESSFUL in 5s`,
  all 26 then-current unit tests passed.
- Earlier `.\gradlew.bat build runClientGameTest --rerun-tasks` development pass:
  `BUILD SUCCESSFUL in 5m 52s`; `19 actionable tasks: 19 executed`, 26 unit tests,
  16 server tests and six client entrypoints passed. Native/guard coverage and the
  final offhand assertion were added afterward; this is not a final pass.
- The first `.\gradlew.bat runClientGameTest` attempt printed
  `compileGametestJava FAILED` / `BUILD FAILED in 1s` because 26.2 has no
  `handleInventoryMouseClick` method with the attempted signature. Replaced that
  test helper with real screen mouse events, then obtained the expected runtime
  assertion failures above. No product assertion changed to address compilation.
- `git diff --check`: exit 0, no whitespace errors (Git emits CRLF-to-LF notices).
- `.\gradlew.bat --stop` after the second final pass: `Stopping Daemon(s)` / `1 Daemon stopped`. Only the included wrapper was used. A final stop is repeated after the report push.

Offline client runs retain the existing profile-key HTTP 401/Realms messages,
anisotropic-filtering warning and Gradle deprecation notices; none fail the suites.

Screenshots (fixture apps only), visually inspected:

- [Chest after unpin](screenshots/0000_07b-chest-unpinned.png): the app is in the
  player inventory; the chest and hotbar are empty.
- [Overflow after rejoin](screenshots/0001_07b-overflow-after-rejoin.png): the one
  book app occupies the freed fifth hotbar slot, its old inventory slot is empty,
  and all eight surrounding stone stacks still contain 12 items.

### Not verified

- Actual installed owner apps, arbitrary shortcut/UWP/icon variants, real app
  launch/focus/close and Linux helper behavior remain the manual checks listed in
  package 07. Native tests enumerate only repository-local fixture roots with
  injected UWP records; no owner app catalogue/icon or real Minecraft/Lunar folder
  was used. The full suites ran on Windows, not a Linux host.
- To try manually in the dev client: pin/unpin through a chest; fill the hotbar,
  configure another pin, free a slot and rejoin; confirm the same app moves there.

### JUDGMENT-CALL

- Save optional launch metadata in the existing schema-2 entry. Rejected a separate
  disposable cache (identity would disappear when caches are cleared) and rewriting
  owner argv to another shortcut. This preserves aliases after the original is
  removed while keeping launch instructions intact. Removing the optional metadata
  later needs no schema migration, but loses reconciliation when the old shortcut
  is absent. Ambiguous pre-existing IDs are retained and diagnosed rather than
  guessed, merged or renumbered, as required by 07b.
- `pinned: true` takes priority during population even when the existing item is
  in the offhand. It moves the same stack into a free hotbar slot; normal UI moves
  out of the hotbar already save `pinned: false`. Rejected leaving a configured
  offhand pin stranded, following the brief's hotbar rule. Changing this later is
  a placement conditional and corresponding test, not a save migration.

### PLAN-GAP

- A package-07 shortcut entry whose original shortcut has already disappeared and
  which has never saved identity metadata has insufficient evidence for matching
  an alias. It is retained and diagnosed; no identity is guessed. This fix saves
  metadata whenever the original can still be resolved. Already-duplicated owner
  entries are also retained. Automatic deletion/repair would conflict with the
  brief's preserve-every-entry instruction.

### Open questions

None block this follow-up. The manual installed-app checks remain as above.

## 07c — Notepad and raw-argument identity regressions

Runtime and regression-test commit: `585f357`. PR #6 stays on `pkg/07-real-apps`
against `main`; no merge was performed.
This section supersedes the earlier launch-identity discussion.

### Done

- `WindowsAppCatalogue`: deliberately reconcile argument-free Notepad shortcuts
  and `Microsoft.WindowsNotepad_*` Store records to the existing `notepad` entry.
  Check the current owner command before using that alias: a document command,
  another executable, a URL or a changed shortcut cannot absorb Notepad discovery,
  even when stale Notepad metadata remains. Preserve every existing owner ID.
- `WindowsLaunchIdentity`, `AppsConfig`: retain the exact raw shortcut argument
  string as optional schema-2 `launchIdentity.rawArguments`. Do not normalize
  quotes, case or whitespace. Older metadata remains readable. Exact shortcut
  commands and complete saved raw identities reconcile before representative
  selection. Different raw command lines remain separate discovery groups.
- Configured argv reconciliation considers all candidate groups. Multiple raw
  variants, shell arguments, shell metacharacters and older shortcut metadata
  without recoverable raw arguments are kept separate and diagnosed rather than
  guessed. Preserve 07b's unique ordinary argv matches, working directories,
  AUMIDs, icon-failure handling and all owner fields.
- `WindowsCatalogueIdentityTest`: seven regressions covering migration plus Store
  discovery (and both shortcut/Store orders), native COM-created `cmd.exe` shortcuts
  with equal parsed argv but distinct raw quoting, raw metadata reload, repurposed
  Notepad entries, ambiguous configured argv, legacy metadata, shell ambiguity and
  matching the correct alias after the original shortcut disappears.
  The native fixtures retain both `cmd.exe /d /c echo "one&ver"` and
  `cmd.exe /d /c echo one&ver` as distinct apps across a config reload.
  `mod/README.md` documents the reconciliation rules. Existing 07b tests are unchanged.

### Verified

All Gradle commands below ran in `mod/` with the included Gradle 9.8.0 wrapper,
Java 25 on Windows. Native discovery used only repository-local fixture roots and
injected Store records; it did not enumerate the owner's installed apps.
Selected exact output is in [verification-07c.txt](verification-07c.txt).

**Failure before the fix:** with `c158fb5`'s runtime unchanged and only the two new
acceptance tests added, `.\gradlew.bat test --tests dev.aresos.catalogue.WindowsCatalogueIdentityTest --rerun-tasks`
printed `2 tests completed, 2 failed` / `BUILD FAILED in 11s`. The migration/Store
test found 2 entries instead of 1. The native raw-quoting test found 1 app instead
of 2. No production file was edited to manufacture either failure.

| Command | Observed output/result |
| --- | --- |
| `.\gradlew.bat test --rerun-tasks` after the initial fix (`build/07c-unit.log`) | `BUILD SUCCESSFUL in 10s`; 36 unit tests passed. |
| `.\gradlew.bat test --rerun-tasks` with the final sources (`build/07c-unit-final.log`) | `BUILD SUCCESSFUL in 10s`; all 37 unit tests passed; `7 actionable tasks: 7 executed`. |
| `.\gradlew.bat build runClientGameTest --rerun-tasks` (pass 1, `build/07c-final-pass-1.log`) | `BUILD SUCCESSFUL in 5m 58s`; `19 actionable tasks: 19 executed`; 37 unit tests, all 16 required server tests and all six client entrypoints passed. |
| `.\gradlew.bat build runClientGameTest --rerun-tasks` (pass 2, `build/07c-final-pass-2.log`) | `BUILD SUCCESSFUL in 5m 54s`; `19 actionable tasks: 19 executed`; the same 37 unit tests, 16 required server tests and six client entrypoints passed. |

Both full passes used exactly `585f357`'s runtime/test sources, with no changes
between them. Each JUnit result contains 7 suites, 37 tests, 0 failures, 0 errors
and 0 skipped tests. The 07b alias/argv/directory/icon tests and chest/overflow
client regressions all passed twice. `git diff --check` exited 0 with no whitespace
errors (Git emits CRLF-to-LF notices).

`.\gradlew.bat --stop` after verification printed `Stopping Daemon(s)` /
`1 Daemon stopped`. Only the included wrapper was used. A final stop is repeated
after pushing the report.

Screenshots from the first full pass, saved under `screenshots/07c/` and visually
inspected:

- [Chest after unpin](screenshots/07c/chest-unpinned.png): the one app is in player
  inventory; the chest and hotbar are empty.
- [Overflow after rejoin](screenshots/07c/overflow-after-rejoin.png): the one app
  occupies the freed fifth hotbar slot; its former slot is empty and all eight
  surrounding stone stacks still contain 12 items.
- [Fixture inventory](screenshots/07c/inventory-fixtures.png): compass/sunset
  textures render in inventory and hotbar, with no missing-texture checkerboards.

The full runs retain the existing offline profile-key HTTP 401/Realms messages,
anisotropic-filtering warning and Gradle deprecation notices. Those messages did
not fail either full pass. No assertion or existing test was weakened or skipped.

### Not verified

- Actual installed Notepad/Store enumeration, real app launching and arbitrary
  application-specific command-line parsers remain human checks in the dev client.
  The native fixtures create and inspect shortcuts; they do not execute the two
  `cmd.exe` command lines. Real Minecraft/Lunar folders were not used.
- No Linux-host rerun or change to the Linux helper stub. Existing manual checks
  for arbitrary app icons, launch/focus/close and catalogue appearance still apply.

### JUDGMENT-CALL

- Keep raw arguments in the existing optional identity metadata, without a schema
  bump or rewriting owner commands. Reject quote normalization and inferring raw
  text from parsed argv. Legacy metadata is refreshed when its original shortcut
  is available; without that evidence, a possible alias can remain a separate app.
  This follows the brief's preserve-over-merge rule. Changing it later needs a
  stronger equivalence rule and regression coverage; existing IDs need no migration.
- Treat default Notepad argv, Windows' Notepad executable paths, a Notepad Store
  command or a currently resolvable Notepad shortcut as evidence that the owner
  has not repurposed `notepad`. Stale metadata alone is insufficient. Reject
  treating every entry named/id'd Notepad as the default. Narrowing or extending
  these guards later changes discovery matching only, with no saved-ID rewrite.

### PLAN-GAP

- 07b metadata discarded the raw argument text. If the original shortcut has
  disappeared, that text cannot be recovered from the saved parsed argv. The old
  owner entry stays intact, a possible new alias stays separate and discovery
  diagnoses the uncertainty. Automatic deletion or repair would require evidence
  and owner policy outside this brief.

### Open questions

None block this follow-up. The installed-app checks above remain manual.

## 07d — Narrow the Notepad alias

Runtime/test commit: `0926389`. PR #6 remains against `main`; no merge was performed.

### Done

- `WindowsAppCatalogue`: replace the executable-name suffix match with exact,
  normalized full-path comparisons for `%WINDIR%\notepad.exe`,
  `%WINDIR%\System32\notepad.exe` and `%WINDIR%\SysWOW64\notepad.exe`.
  Expand environment variables without case sensitivity, normalize separators,
  case and dot segments, and refuse relative or invalid executable paths as
  aliases. Keep the known `Microsoft.WindowsNotepad_*` Store identity and the
  existing argument/working-directory guards. The owner-entry eligibility check
  uses the same Windows-path predicate; owner commands are never rewritten.
- `WindowsNotepadAliasTest`: default configured Notepad plus its Store record and
  an unrelated `C:\Tools\notepad.exe` shortcut must produce exactly two entries,
  preserve all owner fields (including custom icon and unknown JSON fields), leave
  the new app unpinned, and preserve both entries and IDs after disk reload and
  rediscovery. Cover both initial discovery orders, all three allowed locations,
  environment variables, mixed case, dot segments, other directories, relative
  paths, unresolved variables, invalid paths and launch modifiers.
- `WindowsCatalogueTest`: point the existing native Notepad shortcut fixture at
  `%WINDIR%\System32\notepad.exe` while retaining its handmade icon. Its old
  repo-local executable target depended on the broad suffix match that this brief
  removes. Every existing assertion remains intact; no test was weakened,
  deleted or skipped. The fixture only creates/inspects a shortcut; it never
  launches Notepad or writes outside this worktree.

### Verified

All Gradle commands below ran in `mod/` with the included Gradle 9.8.0 wrapper,
Java 25 and the isolated Windows dev client. Exact selected console output is in
[verification-07d.txt](verification-07d.txt); raw logs remain in ignored `mod/build/`.

**Failure before the fix:** added the final three tests before editing production
code, then ran `.\gradlew.bat test --tests dev.aresos.catalogue.WindowsNotepadAliasTest --rerun-tasks`.
It printed `3 tests completed, 3 failed`, `BUILD FAILED in 10s` and
`7 actionable tasks: 7 executed`. The requested regression reported
`Unrelated C:\Tools\notepad.exe was swallowed by the Notepad alias` /
`expected: <2> but was: <1>`. [Original failing JUnit XML](07d-before-fix.xml).
No production behavior was temporarily restored or modified to manufacture this failure.

| Command | Observed output/result |
| --- | --- |
| `.\gradlew.bat test --rerun-tasks` after the fix (`build/07d-unit.log`) | `BUILD SUCCESSFUL in 10s`; `7 actionable tasks: 7 executed`; all 40 unit tests passed. |
| `.\gradlew.bat build runClientGameTest --rerun-tasks` (pass 1, `build/07d-final-pass-1.log`) | `BUILD SUCCESSFUL in 5m 56s`; `19 actionable tasks: 19 executed`; 40 unit tests, all 16 required server tests and all six client entrypoints passed. |
| `.\gradlew.bat build runClientGameTest --rerun-tasks` (pass 2, `build/07d-final-pass-2.log`) | `BUILD SUCCESSFUL in 5m 56s`; `19 actionable tasks: 19 executed`; the same 40 unit tests, 16 required server tests and six client entrypoints passed. |

Both full runs used exactly `0926389`'s runtime/test sources, with no changes
between them. Each run's JUnit XML contains 8 suites, 40 tests, 0 failures,
0 errors and 0 skipped tests.
[Passing new regression XML](07d-after-fix.xml). The earlier 07/07b/07c tests remain
present, including native raw quoting, launch identity, icon fallback,
chest pinning, overflow/rejoin and deterministic Nether-site searches.

`git show --check 0926389` and `git diff --check` exited 0 (Git emits
CRLF-to-LF notices). `.\gradlew.bat --stop` after verification printed
`Stopping Daemon(s)` / `1 Daemon stopped`. Only the included wrapper was used;
no other Gradle version was started. A final stop is repeated after the push.

Screenshots from the first full run, saved under `screenshots/07d/` and visually
inspected:

- [Chest after unpin](screenshots/07d/chest-unpinned.png): one app in player
  inventory; empty chest and hotbar.
- [Overflow after rejoin](screenshots/07d/overflow-after-rejoin.png): one app in
  the freed fifth hotbar slot; the old inventory slot is empty, and eight
  surrounding stone stacks still contain 12 items each.
- [Fixture inventory](screenshots/07d/inventory-fixtures.png): handmade compass
  and sunset icons render clearly in inventory/hotbar without missing textures.

The runs retain the earlier offline profile-key HTTP 401/Realms warnings,
anisotropic-filtering warning and Gradle deprecation notices; these did not fail
either pass. Generated baseline screenshots for earlier packages are archived in
ignored `mod/build/07d-generated/`; the selected 07d evidence is committed here.

### Not verified

- Actual installed Notepad/Store enumeration and real application launching remain
  manual dev-client checks. The requested regression injects discovery records;
  the existing native fixture checks shortcut APIs without launching applications.
  No owner's Minecraft or Lunar directory was used.
- No Linux-host rerun. This change only affects the Windows catalogue; the existing
  Linux-helper and real app/window/icon limitations recorded above still apply.

### JUDGMENT-CALL

None beyond the brief's explicit identity policy. Paths are compared lexically
without requiring their files to exist; other same-named executables stay separate.
No schema, owner command or existing saved-ID migration is introduced.

### PLAN-GAP

None new. The older native fixture's target was corrected to a listed Windows
identity while preserving its original assertions and handmade icon checks.

### Open questions

None block this follow-up. Real installed-app checks remain manual.
