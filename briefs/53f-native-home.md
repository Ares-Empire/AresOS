# 53f: the laptop home, drawn natively

Board #335, package 53. Starts from 53c's branch (PR #114, the window program and the web page); the lead rebases it
onto main once 53c is merged after the R28 cut. The lead's handoff for the whole build is
`briefs/53-laptop-home-build.md`.

**Builder:** a Claude Opus agent, in **two steps** (CLAUDE.md, "Builders work in steps"): step A the model, the
painter, the native test channel and the checks against injected state; step B input, motion, icons, memory and
the clean-up. Each step commits, pushes and keeps `reviews/53f-native-home/PROGRESS.md` true (done, left in order,
what the code doesn't show). At the end, step B replaces PROGRESS.md's content with the report text in the AGENTS.md
format; the lead moves it to `REPORT.md` (a Claude agent cannot create a file of that name). It is a port against
existing pictures and checks, not new design. **Review:** a fresh Codex `gpt-6.2-sol` `high`.

## Why

The owner chose a native laptop home on board #375 (2026-11-18, "yea sounds good"). 53e measured, five-run medians in
software rendering (`reviews/53e-home-memory/REPORT.md` on branch `origin/pkg/53e-home-memory`; PR #118 closed): the
WebKit page at best 418 MiB PSS at rest with smooth motion, against 46.6 MiB for a bare native GTK 4 and Cairo
prototype of 45 flat blocks. He had said 300 MB for a home screen "seems crazy much … thats not a good OS is it?".

**Goal:** the same laptop home, with 53c's look and behaviour, drawn by the window program itself with no web engine.
**Limit: a median of at most 60 MiB (61,440 KiB) PSS at rest** in set-up S below.

## Read first

- `docs/design/LAPTOP-HOME.md` sections 1 to 3 (2.2 and 3 for every key, click and rule), 4, 6, 7 and 11.
- 53c: its REPORT and pictures (`reviews/53c-laptop-home/pictures/`, the reference), its page
  (`os/config/usr/share/aresos/laptop-home/`: `street.js`, `home.js`, `logo.js`, `home.css`) for every number,
  colour and rule, `os/config/usr/libexec/aresos-laptop-home`, and the tests `os/tests/test_aresos_laptop_home*.py`,
  `laptop_home_headless.py`, `laptop_home_helper.py`.
- 53e, from `origin/pkg/53e-home-memory` (`git show`): `os/tests/laptop_home_memory.py`, `laptop_home_native.py`,
  `laptop_home_headless.py` (its `/dev` mask with bubblewrap, private XDG data and cache folders), the memory test,
  and its REPORT's "Method".
- `os/config/usr/libexec/aresos-cover`: the repo's existing GTK 4, Pango and Cairo program, for loading fonts; and
  `os/ci/image-checks.sh` around lines 664–674, where the image check loads its GUI.
- The study's review findings the checks carry: `reviews/44-laptop-home/REVIEW-3.md` finding 6 and
  `reviews/44-laptop-home/REVIEW-2.md` nit 7.

## What stays

Everything in the window program that is not the web view:
- the layer surface and the fallback window;
- reading and removing the token and `LD_PRELOAD`;
- the 1.2 view connection and reconnecting with opening off;
- the kept town, with its bounds and the `null`-revision rule;
- **the starting-state gate:** the kept town is shown with the running IDs as soon as they arrive, opening stays off
  until both paged reads are complete, and the delayed-catalogue regression test keeps passing;
- `view_focus` reports and their replay after hello, in both surface modes;
- the battery source and the vendor pin.

53c's helper changes stay as they are.

## Step A: the model, the painter and the test channel

1. **The renderer, set by the program itself.** Before importing `gi`, the program sets `GDK_DISABLE=gl,vulkan` and
   `GSK_RENDERER=cairo` (an explicit outside choice may override them). It draws with Cairo only, so it must open no
   GPU device. The test harness stops setting either variable. A test checks the running program: it reports
   `GskCairoRenderer`, and it maps no `libEGL`, `libGLX`, `libvulkan`, `libLLVM` or `nvidia` library.
2. **The layout model**, pure Python and without GTK. It takes explicit inputs: the look (day or night), the size, the
   home, the programs, the running apps, whether the helper is online, the typed query, the framed app, each
   street's offset and whether it was slid by hand, hover, the apps being opened, the clock and the battery. It gives
   back where every street, terrace, slab, house, gap, sign, label, hotbar slot and line of text goes, and the hit
   region of everything that can be clicked.
   - 53c's finder ranking, end-sign counting and slide targets (`street.js`: `follow`, `range`, `snap`, and the
     others) become pure functions of the model.
   - The checks set these inputs directly.
3. **The painter** draws only the model, with Cairo and Pango.
   - **The look comes from 53c's CSS and JavaScript**, not from eyeballing: every colour, size and spacing.
   - The day street on terraces, and night as the second look.
   - The fades: by day from `EDGE/2` to `EDGE`; at night 53c's 120 px fade into the wall.
   - Signs, names and short names. Dimmed houses and lit ones with their gold doors (by day paler, section 11.3).
   - The clock, date and battery. The typing line, the hotbar with its numbers, and "Opening is back in a moment".
   - Logos are drawn from the home's cells and palette, as `logo.js` does. Cache one surface per house logo at
     most; **no full-screen offscreen caches** (each costs about 8 MiB).
   - Text goes through Pango with `set_text`, never markup, since names, keywords and the helper's failure words
     are untrusted. Fonts are Space Grotesk and JetBrains Mono, loaded as `aresos-cover` loads its fonts, with 53c's
     fallback when JetBrains Mono is missing.
4. **The native test channel**, replacing 53c's JavaScript channel (`Headless.evaluate`, the `create_view` hook,
   `@snapshot`, `gui.until(READY)`). It is test-only: switched on by the harness, never readable from the session.
   - It dumps the model.
   - It renders a picture **inside the program**, from the painter to an offscreen `cairo.ImageSurface` or from the
     window's own paintable. **Never use a screen-capture tool such as `grim`:** the builder's shell runs in the
     owner's session, and the repo is public.
   - It injects a key or a click through the program's own handlers.
   - It reads counters: draw calls and frame-clock ticks.
   - Bring 53e's harness changes over (the `/dev` mask before labwc starts, private XDG folders), and make
     `headless_available()` stop requiring WebKit. Record the channel in PROGRESS.md for step B.
5. **The checks, against the model and against the painted picture**, so a wrong painter fails as well as a wrong
   layout:
   - **Geometry:**
     - the study's checks, Night street's included;
     - the day grid check with REVIEW-3 finding 6's two breaks: the plot counts per street, and the terraces on
       their streets;
     - the slide targets, a slide by hand, and a framed house beside a cut end;
     - the end-sign counts.
   - **Paint**, by sampling the 1920 × 1080 offscreen picture:
     - the terraces, at 53c's sampled values;
     - an empty slab and the turf between plots;
     - a dimmed house against a lit one and its gold door;
     - the frame around the best hit;
     - the fade at `EDGE/2` and at `EDGE`;
     - an end sign.
     
     Break the painter once for each kind and record in the report that the check failed.
   - **Rest:** over 13 s at rest, count draw calls and ticks. The clock may redraw at most twice, and at night the
     star three or four times. Nothing else draws.
6. **The startup gate and the surfaces:** port 53c's starting-state and delayed-catalogue tests, and keep the real
   GTK focus and reconnect tests for both the layer surface and the fallback window.
7. **Pictures from injected state**, under `reviews/53f-native-home/pictures/`, with 53c's names: day and night, for
   home, forty-five apps, an open app lit, and the helper away. Compare each with 53c's picture of the same name,
   and list every difference and its reason. Look at every picture yourself. Test apps keep generic names and
   generated pictures.
8. **A first memory measurement** of the full drawing (step B.4's method), so step B finishes within the limit
   without redesigning the painter.

## Step B: input, motion, icons, memory and the clean-up

1. **Input**, everything LAPTOP-HOME.md 2.2 and 3 and 53c's page do:
   - typing with an input-method context on the key controller, so dead keys and compose work on his German
     layout;
   - the finder over names, short names, generic names and keywords, ranked as 53c ranks;
   - Backspace, the arrow keys, Enter (opens the best hit), Escape (clears and slides back), and 1 to 9 (the
     hotbar);
   - clicks on a house, an end sign and a group's name, and hover;
   - clearing on focus loss, and the five-second failure line.
   
   Opening calls the helper as 53c's bridge did. Drive at least one key and one click through labwc's virtual
   keyboard and pointer (`laptop_home_headless.py`, around lines 185–221), so the controllers' wiring is tested.
2. **Motion:** the sliding street (the 0.3 s glide) and any other motion 53c's page has, driven by GTK's frame clock
   only while something moves; nothing ticks at rest. The street's current offset is available each frame for the
   companions later. Then rerun step A's checks through real input, and take the "typing" picture after typing
   `tool19`, as 53c did.
3. **Finder icons** of programs outside My apps:
   - Keep 53c's checks on the opened file descriptor: a regular file, not a symlink, at most 1 MiB, a PNG of at most
     512 × 512.
   - **Decode outside the process that holds the view credential:** a short-lived child with an environment of only
     `PATH` and `LC_ALL`, no helper socket and no inherited descriptors but its pipes. It gets the bytes the parent
     read and returns RGBA of at most 512 × 512, with a PNG-only decoder working on bytes, never on a path. The
     helper's icon workers are the pattern.
   - On any failure the program shows no icon.
   - Move 53c's icon-limit tests to this loader.
4. **Memory, set-up S** (software, with the `/dev` mask in place before labwc starts):
   - **Fixture:** the shipped native entry point, a real background layer, the verified Cairo renderer, the study's
     fonts installed and matched with `fc-match`, 45 houses and 47 programs.
   - **Sampling:** five fresh runs, each sampled 15 s after the first complete draw; report the median and spread
     per process. Re-run 53e's prototype in the same session as a control.
   - **The guard:** the opt-in local guard test fails when the median of three runs is above **61,440 KiB**.
   - **Over the limit:** if the median is above 60 MiB, keep the look and the limit, and report the ten largest
     mappings as a PLAN-GAP.
   - **Set-up I** (the Intel chip) is deferred to the laptop trial: the `/dev` mask hides its render node too.
5. **Remove the web engine:**
   - **Delete:** the web view, the `aresos-home:` scheme, the request filter, the bridge's JavaScript side and
     `os/config/usr/share/aresos/laptop-home/`; keep only what the native program still reads, if anything.
   - **The image check:** replace the WebKitGTK check in `os/ci/image-checks.sh` with one that loads the program's
     own `load_gui()`, as the cover's check does.
   - **Tests that only tested the engine:** delete the ephemeral-session, scheme, CSP, foreign-document and loopback
     checks (`test_aresos_laptop_home_webkit.py`), and `ResourcesTest`'s page containment
     (`test_aresos_laptop_home.py`).
   - **Tests kept against the native program:**
     - the token and `LD_PRELOAD` gone from Python and libc;
     - the vendor pins;
     - the app ID and the layer or fallback window;
     - no NVIDIA library mapped;
     - the real-focus `view_focus` reports and their replay;
     - the kept town coming up with opening off.
6. **The design:** update `docs/design/LAPTOP-HOME.md`:
   - section 4: native GTK 4 and Cairo, why, 53e's and this package's numbers, and the owner's choice on board #375
     (2026-11-18);
   - section 7: the companions bring their own web view, only while they are switched on;
   - every other place that names WebKit for the home.

## Acceptance

- **Tests:** every touched test module passes, each run by name (never the whole `os/tests`, never
  `test_owner_update`).
- **CI:** after the last push, start one hosted run (`gh workflow run "OS image" --ref pkg/53f-native-home -f
  checks_only=true`) and put its ID in the report. Push, then stop: never wait for or watch CI. Do not merge.
- **Pictures:** they match 53c's in layout, colour and text, and the report lists every difference.
- **Memory:** a table with 53e's WebKit numbers beside this package's native numbers, per process, median and
  spread, with the prototype as the control.
- **Report:** what only the laptop trial can check (the Intel chip, his session, real input).

## Machine rules

53c's and 53e's rules apply:
- headless compositors only;
- every run private: its own `HOME`, `XDG_*` folders and session bus, the stand-in helper, and `/dev` masked as 53e
  did;
- never the owner's session (`wayland-0`), his `.minecraft`, Lunar Client or `~/AresOS-try`;
- no screen capture;
- never wake the NVIDIA card;
- no game, no Gradle, no client-test lock.

## Out of scope

The supervisor (23c). The helper's interface (no 1.2 change is needed). Super's search (53d). The companions.
