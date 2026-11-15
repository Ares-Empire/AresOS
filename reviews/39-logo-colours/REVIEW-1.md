Reviewed commit `c6eb90689dec114eb6aec4457dbcef7908af6cb3` (branch `pkg/39-logo-colours`, PR #64). The review was read-only: I only read files and pictures and ran `git log`, `git diff`, `git show` and `git ls-tree`. I built nothing and ran no tests or other programs.

| Point | State | Reason |
|---|---|---|
| 1. Rules match HUB.md 3.6 | OK | Every number in 3.6 is the code's constant: `FINE` = 8 (96 × 96 samples), colours in steps of 8, `JOIN` 0.10, three rounds, `NEARLY` 0.07 (nearest pair first), `MAIN_SHARE` 1%, `BLEND_OFF` 0.06 / `BLEND_SMALLER` 0.5, `MAIN_MOST` 6, `SAME_BLOCK` 0.15, `LINE_FAR` 3, speck under 8 × 8, `LINE_SHARE` 10%, `PATTERN` 0.06, the plain list and the seven stand-ins. The centring is to the half pixel. The above-six rule is the step-2 rule (the average of the main colour that covers most of the cell, 2-2), in both code and docs. I checked one stand-in number by hand (red wool ↔ red mushroom: 0.050 with lightness halved). Two wording NITs: N2 and N3. |
| 2. Determinism and robustness | OK | Nothing iterates a hash map or set: colours go into a `TreeMap`; lists sort with stable sorts (`List.sort`, ordered `Stream.sorted`); ties use a strict `<`, so the earlier or larger one wins. The functions are pure and every static is fixed once loaded. All loops are bounded: the merge loop removes one group or stops, `line()` drops at most one candidate per sweep, and `connected()` looks at at most 8 cells. Extra memory is about 96² samples whatever the icon's size, and a large icon costs one more read of every pixel than before. Inputs I traced by reading: empty, 1 × 1, very wide or tall, grey only, faint edges, palette PNG, more than six colours. None of them throws or hangs. One theoretical exception path (N1) is caught and gives a plain front. |
| 3. Off the server thread | OK | `GatePicture.of` is called only from `GateBuilder.icon`/`picture`. Those run only inside `PictureReader.read` (`TownKeeper.java:282`, `ZoneCommands.java:151`). The server thread uses only `GatePicture.plain`, `hash()` and `CONVERTER`; the palette's new setup when the class loads takes microseconds. `ofBlocks` is called only by `GateGameTests.stripes`, and nothing in `main/` calls it. |
| 4. Renewal | OK | `changed()` (`TownKeeper.java:670-672`) sees converter 1, and `Town.build` records `CONVERTER` (`Town.java:123`), so each logo is renewed once. The test's "A second visit renewed again" check confirms this. Conversion is deterministic, so the full re-read on every `ask()` does not set off renewals again. A frozen town does nothing (`TownKeeper.java:374`), and the seal test now asserts the record stays at `CONVERTER - 1`. Hand-built gates carry no converter, and only `Town.java:123` and `TownKeeper.java:671` read it. Outside `zone/`, the only main-code change is a comment, so what the town may take down is unchanged. One documentation gap: N4. |
| 5. Palette change and old worlds | OK | A take-down compares the block in the world with the record's block ID (`Placing.still`, `GateBuilder.undoing`); nothing in production compares against the palette. `GatePalette.built`, `plain` and `nearestFirst` are used only by the converter. `GateGameTests` still builds and removes a red mushroom gate through `ofBlocks`. A mushroom block's faces count as the same block (`Placing.java:56-64`, `HubBlockChangeMixin`). |
| 6. Tests and pictures | OK | The rules are pinned (see below), except two (N5). The drawn icons are generic shapes. The pictures are correct: no stray copies, and the client test is last. One SHOULD: the flaky build (S1). |
| 7. Docs | OK | `README.md` changes the mod bullet only, and both statements are now true (the `Mod` workflow runs `build`: unit and server game tests). The new wording is at `TownKeeper.java:322` and `HUB.md:52`; no "next tick" or "a tick later" is left in HUB.md or `hub/`. `mod/README.md:723-743` matches the code, apart from N3 and N4. |

**Tests that would fail without their rule, judged by reading**
- **Converter renewal** (`TownGameTests`): holds. `older()` keeps the picture hash and the blocks, so only the converter comparison sets off the renewal.
- **Frozen town:** holds. The new `converter == CONVERTER - 1` condition would fail if a frozen pass renewed the logo.
- **Speck** (`aSpeckBesideAThinLineIsNotShown`): holds. The star is about 6 samples across, under 8, and lies one cell row above the bottom line's end. Without the speck rule its cell has well over 7 thin samples and touches a line cell, so it would be shown and break the "u == 1 or v == 3" check.
- **Plain blocks first** (`GatePaletteTest`): holds. The stand-in map and `PATTERN == 0.06` fix the cut-off between 0.054 (emerald) and 0.068 (prismarine).
- **Smoothed-edge colours dropped:** pinned by the two-main-colour asserts on thin lines and the pale figure. Their 4-pixel lines and soft edges make grey or mid groups well over 1%.
- **Same block only when nearly the same** (`twoMainColours…`): pins that the rule exists, not the number 0.15.
- **Above six colours** (`sevenStripes`, many colours, photo): holds. The enlarged stripes straddle cells, so averaging a whole cell would create in-between blocks.
- **The "Version 1 …" comments** (greys, amethyst and blue ice on the bubble's edge, spotted red, the sun's edge cells) match the committed "before" pictures.

**Pictures**
- I looked at all four of this package's pictures and at 37's `0076` and `0080`.
- `0083`/`0084` "after" show the old rules' flaws gone: the thin lines are white on black one block wide, the bubble has no edge blocks, the wheel's ring is one block, the heart is plain red wool, and the sun is three blocks. The "before" pictures show greys, amethyst and blue ice edges, a spotted mushroom red and honeycomb cells.
- The tree at HEAD holds exactly 37's `0076`–`0082` and this package's four. `aaedcaaf` renamed the "before" files and deleted the old-numbered `0076`/`0077` copies. No picture of packages 33 to 36 changed.
- The ten icons used for the "before" pictures have not changed since they were taken (`84fc8801`); later commits only added two unit-test icons.
- `LogoIcons` draws generic shapes only. The wheel and the bubble echo the layout the brief asked for, but neither copies a real logo's colours or shapes.
- Real icons are read only from `ARESOS_LOGO_LOOK`, outside the repo.
- `LogoColoursClientGameTest` is last in `fabric.mod.json`.

## Findings

**S1 (SHOULD): a flaky server game test on this branch.**
- Where: `reviews/39-logo-colours/REPORT.md:157,170`; `mod/src/gametest/java/dev/aresos/test/TownGameTests.java:165` (`inTown`'s chunk wait; `LOAD_TICKS` at `:70`).
- What happened: one of three `build.sh` runs failed `the_town_trusts_its_records_only_while_the_world_was_saved_with_them` with "The town's chunks are not loaded yet on tick 400002". The same code then passed.
- Why it matters: the next build (the `Mod` workflow on this PR or a later package) can fail the same way.
- Why it is not a FIX: it fails in the chunk wait, before the body this package edited runs, so this diff is not the cause. But AGENTS.md treats a flake as a failure.
- Fix: check whether it flakes on `main` and put it on the board for the town topic, rather than leaving it only under "Not verified".

**N1 (NIT): an icon whose colours all fall under 1% gives a plain front.**
- Where: `mod/src/main/java/dev/aresos/zone/GatePicture.java:373-374`, then `:230`/`:405-414` and `:257`.
- How: if the 1% filter removes every group, `mains` is empty. `nearestMain` then returns 0, `blocksFor` returns an empty array, and `blocks[main[i]]` throws `ArrayIndexOutOfBoundsException`. `GateBuilder.icon` (`GateBuilder.java:96`) catches it, so the logo becomes a plain front in the group's colour and nothing is logged.
- When: this needs more than 100 groups of near-equal size, for example a full-gamut noise picture of 96 pixels or less. With groups at least 0.10 apart, a real icon has at most about 100, so one of them reaches 1%.
- Why it is not a FIX: no crash, no hang, and practically unreachable.
- Fix (one line): if the filter empties the list, keep the groups and take the many-coloured path.

**N2 (NIT): HUB.md 3.6 states the distance as a squared value.**
- Where: `docs/design/HUB.md:415`.
- The doc defines the distance as `(0.5 × ΔL)² + Δa² + Δb²` and then says "within 0.06". The code compares the square root (`GatePalette.java:107-110`, `away`).
- The listed numbers are square-root values. By hand: red wool ↔ red mushroom is 0.050 with lightness halved and 0.085 in plain Oklab.
- Taken literally, the formula would allow stand-ins up to 0.245 away. Write "the square root of …".

**N3 (NIT): "a speck smaller than a cell is left out" says more than the code does.**
- Where: `docs/design/HUB.md:188`, `mod/README.md:726`, and "is left out" at `HUB.md:413`.
- The speck rule (`GatePicture.java:475`) only stops a speck from being promoted to a line. A dot that covers more than half of one cell still shows, because the cell takes the colour that covers most of it.
- Suggested wording: "is not drawn as a line; it shows only where it covers most of a cell".

**N4 (NIT): "drawn again where it stands, in one pass" has two exceptions the docs don't mention.**
- Where: `docs/design/HUB.md:44`, `mod/README.md:740-742`.
- Exception 1: a logo whose place is not loaded is renewed later, when he comes near, with its own line then.
- Exception 2: a logo with a block of his in it comes down around his block. It cannot stand there again, so it moves one place on ("came down to be renewed but cannot stand at … again", `TownKeeper.java:487-499`), exactly as with `hub rebuild`. The converter bump now does this to every such logo on the first visit, without him asking.
- Why it is not a FIX: the town still takes down only blocks it recorded, and his block stays.
- Also: apps without an icon are counted as "renewed" although their plain front looks the same.
- One sentence in 2.5 would stop the move from surprising him.

**N5 (NIT): two rules are not pinned by a test, and one report claim is untested.**
- Centring the enlarged square to the half pixel (`GatePicture.java:187-189`, call 1-4): no unit test fails without it. The mirror test in `GatePictureTest` uses a ring that is not enlarged.
- The 1% drop (`GatePicture.java:373-374`): no test fails without it either.
- `REPORT.md:117` says "After `/aresos hub trust` the next pass renews it". No test checks this. It holds by reading: `trust` → `ask()` → the pictures are read again → `changed()`.

VERDICT: SAFE
