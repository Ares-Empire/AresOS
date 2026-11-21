# 329 window frame in Look A

## Done

- Step 1 generated and installed Look A's frame theme and pack. It selects AresOS in labwc, adds Shift+Alt+Tab and clears title-bar scrolling. The image checks pin the shipped theme and the expanded pack. [Step 1 log and release handoff](PROGRESS.md)
- Step 2 extended the Wayland test client with a floating size, title, app ID and solid colour. Floating windows negotiate decorations, and both client modes log configure states and close cleanly. Existing callers still start fullscreen when they omit a size.
- Frame mode shares package 320's rootless Podman gate, D-Bus and compositor helpers. It runs new and merge-base sessions with the shipped fonts and themes. The published images are private headless Look A captures and composites made with the public Look A study. [Harness instructions](../../os/tests/indicator-harness/README.md)

## Verified

`os/tests/indicator-harness/run.sh image` built both images and compiled the clients with `-Wall -Werror`. The build and run matched both installed binaries to `os/labwc/labwc.lock.json`, using `labwc-0.9.6-1.fc44.aresos1.x86_64` from the existing 311e image. The isolation gate ran before the private D-Bus and Wayland sockets existed. `labwc -V` logged the expected image theme paths in each frame session and emitted no theme errors. The final baseline is `a7fb7cfe0e8ae7797adc2ab5cd3baf88aa09ec56` with Ares-Crown and Space Grotesk. The merge adds package 330, which leaves the labwc lock and baseline XML byte-identical to `f91aad16`. B321 was absent from this baseline. [Build and run versions](evidence/versions.txt) · [Isolation checks](evidence/isolation.txt)

| Check | Observed result | Evidence |
|---|---|---|
| 1. Frames | The plain clients kept 580 × 260 and 620 × 300 areas. The GTK 4 client kept 620 × 300 with a negotiated server frame. Both focus states had the exact 40 px bar and 2 px edge. The long title was cut and both 4× title crops had zero intermediate-colour pixels. | [Sheet](evidence/sheet-01.png) |
| 2. Hover and close | All eight shipped hover cells matched. Close turns red. Pressing close and moving out before release kept the window open. Clicking it logged `CLOSE`, returned zero and removed the window. A separate client holding a pointer lock also closed with exit zero. | [Sheet](evidence/sheet-02.png) |
| 3. Toggles | Button and title double-click maximize put the bar at the top, omitted the edge and restored the exact former client rectangle. A separate two-workspace run used shade and all-desktops. All 36 normal, hover and toggled PNGs matched at 48 × 40 and 1:1. | [Sheet](evidence/sheet-03.png) · [PNG list](evidence/01-03-pngs.txt) |
| 4. Menus | The gold block and title right-click produced eight complete 40 px rows with the 2 px outline and Look A hover colours. Escape kept focus. The root menu used the same colours and its three rows remained readable. | [Sheet](evidence/sheet-04.png) · [Pixel measurements](evidence/04-menu-rows.json) |
| 5. Bindings | Both scroll directions preserved pixels, geometry, shade and focus from both starting states. Title drag, top-edge maximize, left and right snap, border resize, vertical maximize, minimize, Alt+F4 and both Super+drag bindings agreed with the baseline. Both snap previews used the Look A tint and three 2 px lines. | [Sheet](evidence/sheet-05.png) · [Before and after table](evidence/05-bindings.json) |
| 6. Alt+Tab | The world rule produced a maximized, borderless 1920 × 1080 client below the overlapping app. The panel appeared on the focused output with 280 × 208 tiles, a 4 px gold selection and a black, gold and black preview outline. Quick switching, reverse switching, minimized restoration, Escape and tile clicks worked. Pointer events and injected deltas matched the baseline. | [Sheet](evidence/sheet-06.png) · [Event comparison](evidence/06-switcher.json) |
| 7. Look setting | Fresh sessions with A, B and C printed the requested setting and rendered pixel-identical frames. | [Sheet](evidence/sheet-07.png) |
| 8. For review | Eight sheets pair the headless captures with A-09, A-10, A-11 and A-14. The button atlas contains the 36 captured cells. Package 320's indicator suite also ran with the expanded pack. | [Atlas and study](evidence/sheet-08.png) · [Indicator results](evidence/indicator-results.txt) |

The pack, theme and rc.xml unit modules reported `OK` for 1, 3 and 2 tests respectively when run one at a time with `python3 -m unittest discover -s os/tests -p <module>`. Bash syntax, Python compilation and `git diff --check` passed. The rc.xml comparison still shows one new keyboard row and two scroll overrides alongside the theme and switcher changes. `crown_pin()` found exactly one pin and it matched the installed Crown directory. The R28 test and indicator loader match the baseline. The loader reads only the `sprites` key.

Both frame runs completed with 35 scenario checks, 36 exact button images and eight review sheets. The first indicator run failed test 9 at 95% after the mock volume reader encountered partially rewritten JSON. The fixture now uses shared locks for reads and the existing exclusive lock for writes. The unchanged indicator assertions then passed all nine groups and 52 checks twice. The brightness and volume stand-ins hold neither lock during a simulated hang. [Frame results](evidence/results.txt) · [Indicator results](evidence/indicator-results.txt) · [Repeat](evidence/indicator-repeat-results.txt)

The package 320 and 329 Python image-check blocks also passed against the checkout's staged image paths. The hosted run with `check_build=build` passed the image and UEFI guest checks on `0dbd6256276fefbfa8f4d7ac2aaa4f2602a80e12`. The `checks_only=true` workflow on the same commit reported `Ran 2490 tests in 3031.966s` and `OK (skipped=24)` and passed the full ways-back model. Both watches returned zero. [Image build 44942183654](https://github.com/Ares-Empire/AresOS/actions/runs/44942183654) · [Regressions 44945705491](https://github.com/Ares-Empire/AresOS/actions/runs/44945705491)

## Not verified

The real panel and owner app list need a separate test. Live B/C sync and reconfigure, Super+Tab, cover filters and the foreign-toplevel activation request belong to their later packages. The package changes OS files and two private headless clients. No Gradle or Minecraft client run was performed for this proof. [Known limits](KNOWN-LIMITS.md)

## JUDGMENT-CALL

None. The frame proof required no change to the shipped theme, layout, bindings or rules from step 1. Harness fixes added normal xdg-decoration negotiation, avoided unintended double-clicks and waited for the compositor's rendered or protocol state before sampling. The indicator fixture fix wraps its JSON in the same file lock the device stand-ins already use for updates.

## PLAN-GAP

- The baseline's virtual wheel direction that shades is labwc Up (`axis -1`). Down (`axis +1`) unshades and focuses. The test injects each direction from both starting states, including the two prescribed in the brief. On the baseline, Up over an already-shaded window also drops the other window's focus. The branch preserves the starting state in all four cases. [Baseline comparison](evidence/05-bindings.json)
- The built-in root menu includes Terminal ahead of Reconfigure and Exit. The window menu also shows Workspace in the shipped one-workspace config. [Menu captures](evidence/sheet-04.png)

## Open questions

The root menu's Exit row is a lead handoff for the layouts package. The merge gate still needs the fresh review and the release owner read listed in the progress log.
