# 44: The laptop-screen home (a design study)

Empire brief 297, board #283.

When an external monitor is plugged in, the world (the home screen) goes onto the monitor (package 23c, `linux-aresos`, the release after next). The laptop's own screen then shows a plain dark background. The owner wants that screen to become a home of its own.

His words (2026-11-15): "I think the laptop needs to get a proper "monitor connected" homescreen so its not boring and still unique and functional. Probably most useful will be to have apps easily accessible via it or a companions room or similar. Or we build multiple options and then enable choosing. ... for now, v1 we focus on just the homescreen, then comes a unique and functional monitor connected homescreen for the laptop (with access to apps) and once we do the companions, the alternative laptop homescreen gets like a room or a city custom made where companions can walk around in and do activities with a menu for opening apps. Maybe, we can decide specifics later. ... The agent that works on the monitor connected homescreen can be creative with the design and functionality, what I just sketched is an idea, not a set decision. The only thing: the alternative laptop homescreen (v1) needs to fit to AresOS and the actual homescreen. it doesnt need to be like a picture of the town or smth but it should fit."

This package designs it. It builds no product code. The owner chooses from what it shows. A build package follows.

**Builder:** one Claude agent on Fable 5.2: a new design that isn't scoped yet, and it sets how AresOS feels on a second screen. **Review:** a fresh Claude reviewer on Opus 5.5 (READY or CHANGES-NEEDED).

## What it must be

- **Functional first:** his apps are easy to reach from the laptop screen: find, open, see what's pinned. Anything else it shows (time, battery, what's running, a glance at the world) is your call, if it earns its place.
- **Fits AresOS and the world:** the block logos, the four group colours, the short names and "My apps" from `docs/design/HUB.md`, and the crown language in `~/ares-empire/EMPIRE.md` ("The crown language"): near-black, gold used sparingly, Space Grotesk. It should feel like the same home seen from another angle. It doesn't have to picture the town.
- **Unique:** not a generic launcher grid.
- **Light:** no second Minecraft and no second JVM. Name the memory it needs, and measure a prototype if you can.
- **Ready for the companions:** later a version comes where companions walk around a room or a small city and do things, with a menu for apps. Pick tech the companions can move into without being rebuilt. They already run on a shared web runtime (`~/companions`, `runtime/README.md`: a host made from a canvas, a world provider, input and storage). A web-based screen (the system's web engine, full-screen, no browser around it) is the starting idea; choose something else only for a better reason, and say why.
- **Reads the same apps as the world:** the app helper (`os/config/usr/libexec/aresos-shell`, protocol `aresos-shell/1.1`, HUB.md 3.8) already gives the mod the app list, pictures, pins and launching. The laptop home should be a second client of it, not a second app catalogue. Say what the protocol would need.
- **Lives in the session:** the laptop screen while the monitor is in; gone when unplugged (the world comes back). Apps open on the screen the pointer is on (23c's spec). Say how it starts, stays below apps and stays out of Alt+Tab, as the world does today (`os/config/usr/share/aresos/labwc/rc.xml`).

## Deliverables

In `reviews/44-laptop-home/`:
1. **Two or three directions** as clickable HTML prototypes (`prototypes/<name>/index.html`, no build step, no network) at 1920 x 1080, with a town of test apps (names like "Test Web 1", generated pictures, as the hub's rigs use). One of them may be the companions-ready room in its v1 form (the room without companions yet).
2. A **picture of each** at 1920 x 1080 (a headless browser with its own temporary profile, or WebKit in a headless compositor), plus pictures of the key moments (finding an app, opening one).
3. `PROGRESS.md`, which the orchestrator commits as the report: each direction in plain words (what he sees, what he does), the one you recommend and why, the tech choice with the memory estimate, how it talks to the helper, how it lives in the labwc session, how the companions version grows from it, what stays open, and JUDGMENT-CALLs for the owner (how it feels is his call).

And `docs/design/LAPTOP-HOME.md`: the recommended direction as a design draft that a build package can follow, marked "draft, waiting for the owner's choice".

## Rules

- Worktree `~/AresOS-44-laptop-home`, branch `pkg/44-laptop-home`, from main `e33ffc46`. Push with `git push origin pkg/44-laptop-home`. Never merge, never push to main, never `--no-verify`.
- No product code: nothing under `os/` or `mod/` changes. Prototypes and scripts stay in `reviews/44-laptop-home/`, each labelled as a development aid.
- Never open a window on the owner's screen: never `WAYLAND_DISPLAY=wayland-0`, never his `DISPLAY`. Headless only. Stop only processes you started, by PID. A headless browser gets its own temporary profile, never his.
- No Minecraft client is needed. If you want one, take `~/.cache/aresos-dev/client-test.lock`, check `free -g` (6 GiB available) and use the dev scripts. Never touch `~/.minecraft`, `~/.lunarclient` or Lunar Client.
- The repo is public: no personal data, no names of his installed programs, no real app icons or logos, no Mojang textures, no pictures of his screen. Fonts: Space Grotesk and JetBrains Mono (both under the OFL) may be used from the system or a CDN-free local copy; say their licence.
- Read `~/companions` for its runtime only. Copy nothing from it into this repo.
- Commit and push after each part that works. Commits end with `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`.
- `gh` only for `gh pr create` at the end: title "Package 44: the laptop-screen home (design study)", body ending with the two attribution lines the orchestrator gives.
