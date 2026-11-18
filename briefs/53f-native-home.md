# 53f: the laptop home, drawn natively

Board #335, package 53. Starts from 53c's branch (PR #114, the window program and the web page); the lead rebases it
onto main once 53c is merged after the R28 cut. The lead's handoff for the whole build is
`briefs/53-laptop-home-build.md`.

**Builder:** a Claude Opus agent, in **two steps** (CLAUDE.md, "Builders work in steps"): step A the drawing and its
checks, step B typing, motion, memory and the clean-up. Each step commits, pushes and keeps
`reviews/53f-native-home/PROGRESS.md` true; step B deletes it and leaves the report text there for the lead (a Claude
agent cannot write a file named `REPORT.md`). It is a port against existing pictures and checks with clear rules, not
new design. **Review:** a fresh Codex `gpt-6.2-sol` `high`.

## Why

The owner chose a native laptop home on board #375 (2026-11-19, "yea sounds good"). 53e measured, five-run medians in
software rendering (`reviews/53e-home-memory/REPORT.md` on branch `pkg/53e-home-memory`, PR #118 closed): the WebKit
page 418 MiB at rest at best with smooth motion, a native GTK 4 and Cairo drawing of the same 45-house town 47 MiB. He
had said 300 MB for a home screen "seems crazy much … thats not a good OS is it?".

**Goal:** the same laptop home, the same look and behaviour as 53c's page, drawn by the window program itself, with
no web engine. **Target: at most 60 MiB PSS at rest** in 53e's software set-up S.

## Read first

`docs/design/LAPTOP-HOME.md` sections 1 to 3, 6 and 11 (the look and the rules), section 4 (to be changed), 53c's
REPORT and pictures (`reviews/53c-laptop-home/pictures/`, the reference), 53c's page
(`os/config/usr/share/aresos/laptop-home/`: `street.js`, `home.js`, `logo.js`, `home.css`) for every number and rule
it encodes, `os/config/usr/libexec/aresos-laptop-home`, and `os/tests/test_aresos_laptop_home*.py`. From branch
`pkg/53e-home-memory`: `os/tests/laptop_home_memory.py` (the sampler), `os/tests/laptop_home_native.py` (the
47 MiB prototype), `os/tests/test_aresos_laptop_home_memory.py`, and its REPORT's "Method".

## What stays

Everything in the window program that is not the web view: the layer surface and the fallback window, reading and
removing the token and `LD_PRELOAD`, the 1.2 view connection, reconnecting with opening off, the kept town (its
bounds and the `null`-revision rule), the starting-state rule (open apps lit from the first frame), `view_focus`
reports, the battery source, the vendor pin. The helper changes from 53c stay as they are. Their tests keep passing.

## Step A: the drawing

1. **Replace the web view with a native drawing** in `aresos-laptop-home`: GTK 4, one drawing widget, Cairo (and
   Pango for text), `GSK_RENDERER=cairo` as 53e found best. Split it into a layout model (pure Python: where every
   street, terrace, house, gap, sign, label, hotbar slot and text goes, from the home, the running apps and the
   screen size) and a painter that only draws the model. The model is what the tests check.
2. **Port the look exactly** from 53c's page: the day street on terraces, night as the second look, houses from
   places with their gaps, the cut ends and their fade (`EDGE/2` to `EDGE`), the street and group signs, names and
   short names, dimmed houses and lit ones (by day paler, section 11.3), the clock, date and battery, the typing line,
   the hotbar with its numbers, "Opening is back in a moment". Every colour, size and spacing comes from 53c's
   CSS and JavaScript, not from eyeballing. Logos from the home's cells and palette, as 53c's `logo.js` does.
   Fonts: Space Grotesk and JetBrains Mono through Pango, with the same fallback as 53c when JetBrains Mono is
   missing.
3. **Port 53c's checks to the layout model**, so each still can fail: the study's checks including Night street's,
   the day grid check with REVIEW-3 finding 6's two breaks (plot counts per street, terraces on their streets by
   sampling the picture's pixels), the fade, and the rest check (at rest nothing is drawn again except the clock once
   a minute and, at night, the one star: count draw calls and frame callbacks).
4. **Pictures** in a headless compositor as 53c took them (same fixture, same names) under
   `reviews/53f-native-home/pictures/`, day and night: home, forty-five apps, typing, an open app lit, the helper away.
   Compare each with 53c's picture of the same name and record in the report where they differ and why. Look at every
   picture yourself. Test apps keep generic names and generated pictures.

## Step B: behaviour, memory and the clean-up

1. **Typing and finding:** the finder with names, short names, generic names and keywords as 53c's page finds; end
   signs that count their hidden matching houses while typing (REVIEW-2 nit 7); Enter opens the best hit; Escape
   clears; 1 to 9 open the hotbar; a click on a house opens it. Opening calls the helper as 53c's bridge did.
2. **Motion:** the sliding street (0.3 s glide) and any other motion 53c's page has, driven by GTK's frame clock
   only while something moves; nothing ticks at rest. The street's current offset is available each frame for the
   companions later.
3. **Finder icons** of programs outside My apps: read from the helper's `icon` path with 53c's limits (a regular file,
   not a symlink, at most 1 MiB, PNG of at most 512 × 512), decoded in the program; anything else shows no icon.
4. **Memory:** bring 53e's sampler, the native prototype and the memory test into this branch. Measure set-up S
   exactly as 53e did (fixture, five runs, median and spread), and set-up I only if the NVIDIA card is asleep (53e's
   rule). **At most 60 MiB median** in set-up S; the local guard test pins it as 53e's guard does.
5. **Remove the web engine:** the web view, the `aresos-home:` scheme, the request filter, the bridge's JavaScript side,
   and `os/config/usr/share/aresos/laptop-home/` (keep only what the native program still reads, if anything). Replace
   the WebKitGTK import check in `os/ci/image-checks.sh` with checks for what the program now needs (GTK 4, PyGObject,
   Pango and Cairo bindings). Delete the tests that only tested the web engine; keep every behaviour test, now
   against the native program.
6. **The design:** update `docs/design/LAPTOP-HOME.md` section 4 (native GTK 4 and Cairo, why, the measured numbers,
   the owner's choice on board #375), section 7 (the companions bring their own web view, only while switched on),
   and anything else that names WebKit for the home.

## Acceptance

- Every touched test module passes, run by name (never the whole `os/tests`, never `test_owner_update`). After the last
  push start one hosted run (`gh workflow run "OS image" --ref pkg/53f-native-home -f checks_only=true`) and put its
  ID in the report. Push, then stop: never wait for or watch CI. Do not merge.
- The pictures match 53c's in layout, colour and text; the report lists every difference.
- The memory table: 53e's WebKit numbers beside this package's native numbers, per process, median and spread.
- The report text (AGENTS.md format) in `PROGRESS.md` for the lead, with what only the laptop trial can check.

## Machine rules

53c's and 53e's apply: headless compositors only, every run private (own `HOME`, `XDG_*`, session bus, stand-in
helper; `/dev` masked as 53e did), never the owner's session (`wayland-0`), his `.minecraft`, Lunar Client or
`~/AresOS-try`. Never wake the NVIDIA card. No game, no Gradle, no client-test lock.

## Out of scope

The supervisor (23c). The helper's interface (no 1.2 change is needed). Super's search (53d). The companions.
