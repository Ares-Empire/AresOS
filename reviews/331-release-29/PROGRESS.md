# 331 Release 29 progress

## Done · step 1 · 2026-11-21

Added the R29 profile, exact RPM delta, file and unit reasons, and main-source stop in
`os/ci/release_diff.py`. The gate checks the R28 record's source trees and the checked-out
build inputs against the branch's merge base with main. R29 adds `os/labwc/` to the source
list and permits the reviewed jar-pin-only change on the release branch. The historical R27
and R28 profiles keep their own rules.

| Current main change | Image and evidence |
| --- | --- |
| B323 · `6fe289e4` | The x86_64 package lock adds `gtk4-layer-shell-1.3.0-1.fc44.x86_64`. The diff checks the RPM's non-ghost payload against its file records and requires clean RPM verification. The shared library and its GObject typelib are used by the indicator and laptop home. The JetBrains Mono font and licence ship under `/usr/share/fonts/aresos`. Both fontconfig cache formats are rebuilt. The image checks exercise the typelib with its preload and check font selection. The Mesa EGL and Intel Vulkan checks cover existing graphics RPM files and their libraries. |
| 311 and B323 · `67e1e60c`, `6fe289e4` | The package layer installs Fedora's `labwc-0.9.6-1.fc44.x86_64`, then replaces it in the same layer with `labwc-0.9.6-1.fc44.aresos1.x86_64`. The download lock still pins Fedora's RPM as input. The final `packages.txt` records the rebuilt NEVRA, and `labwc.lock.json` records the build inputs. Keeping the swap in one layer preserves the replacement binary when size, mode and mtime coincide. The classifier currently stops pending the independent payload comparison. |
| B320 · `06883a3d` | Six labwc key rows route brightness up and down, volume up and down, speaker mute and microphone mute through executable `aresos-level`. Volume up also unmutes. Brightness down stops at 1% of the backlight's maximum. Executable `aresos-indicator` and `aresos-settings` use the look JSON and 17 sprites. Jersey 10 and its licence ship with the font cache refresh. |
| 25 and PR136 · `61a66d78`, `5e8f90f9` | The supervisor, Java wrapper, cover and shell coordinate planned-stop saves. The desktop message window adds `restart`. The borderless `aresos.black` window stays on top during a save. The guardian unit, login-scope ordering drop-in and exact graphical-target enable link each have a reason. The guardian asks the game to save and waits within a deadline. The offline updater audit gains the guardian's exact enabled row and commands. Its unit-specific drop-in scan leaves existing rows intact. PR136 adds half a second of slack to the hosted lid timestamp check. The cut still needs both guardian VM receipts. |
| 56, 53c, 53d, 53f and PR134 · `da441546`, `e01cd6a1`, `c576818b`, `3048b221`, `182005e6` | The rebuilt mod jar includes the mouse and hotbar changes, faster flight and world-search support. The installed desktop lock and mod record bind the jar's pin and build revision. The shell helper handles focus and desktop views, invalidates stale home cursors and caps view launch checks. The image carries the native GTK 4 and Cairo laptop-home executable. Laptop-home and Super search launch wiring awaits 23c. B316's portal source is present on main and its image integration belongs to B321. |
| T475, Chrome and Control | T475 records the laptop on R28 with R27 as rollback, corrected stock pinned, R13 retired and owner tools v5 `df89ac33…`. Chrome, Control Part A and its `aresos` CLI already ship in R28. The two images must match the validated Control install and vendor inventory, with only the source revision changing in `control.json`. The existing Control UID and GID are 250. The dispatcher from package 43 remains subject to its cut decision. |

The full bound source delta from the recorded R28 commit to this branch's main base covers
`mod/`, `os/Containerfile`, `os/build.sh`, 34 paths under `os/config/`, six paths under
`os/labwc/` and `os/packages.lock.json`. The named generated paths cover the RPM database,
dnf5 history and repository markers, ldconfig caches and the fontconfig rebuild. The
classifier also checks completeness for unchanged required links, typed Prism inventory,
the pinned Prism list, deterministic compiled schemas and the locked Java alternatives chains.

## Verified locally

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s os/tests -p test_release29.py` | `Ran 12 tests in 5.400s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_release28.py` | `Ran 94 tests in 31.710s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_release27.py` | `Ran 41 tests in 6.836s`, `OK` |
| `git diff --check` | Exit 0 with no output |

The R29 tests used fixture images and stand-ins for image commands. The fixture diff
classified every change except the labwc payload and wrote a stopped result. Regressions
cover missing files and RPM records, incorrect metadata, missing alternatives links and
groups, a missing unit audit, unmasking, source omissions and a changed merge resolution.

## Sources and runs

- Approved starting head `1b2b27c790bcd402926dff3a659ee071f3ad5dfa`. Main base
  `a9863055b2987127cd1cd684182deed9ece24ce0`. Step 1 code and test head
  `b17b4daca5eca6f7f0a82f4c2e9047fd7070fb66`.
- R28 from `os/manifest/releases/28.json`, source
  `7d5fbbf2c7f7c5b4d41dd707a9407e6401a4d062`, signed digest
  `sha256:aa97b2d506a4b48e24869902d78adb7700482a068d9bb5dc371e886a76e5f15d`, base
  `sha256:ed93d2158a1bcba16b226bfb3ab6391446d11466646188c800b982d709435151`.
  [Recorded R28 publish run 44590446680](https://github.com/Ares-Empire/AresOS/actions/runs/44590446680)
- R29 hosted run and run SHA pending. Ledger use is zero dispatches and zero uploads.
  R29's effective `dispatch_caps.publish-29` and `publish_cap` are both zero.
  The hosted ledger wiring belongs to step 5.

## Left in order

1. Lead review of the step 1 classifier at the draft PR head.
2. Step 2 compares both labwc RPM inventories and the normalized and loaded bytes.
3. Steps 3–5 add the walk, guest and Control checks, and hosted wiring.
4. Step 6 takes the named main cut and the reviewed handoffs for 18c-b, B330, B329
   and B321 as applicable. The lead settles package 43 under the brief.
5. Steps 7–12 handle resolve and dry run, publish approval, release record,
   candidate tools and guides, qualifying rehearsal and the final pin.

## Limits

Step 1 proves the rules with local fixtures. Full image evidence, the release jar pin, the
guardian VM save and timeout receipts, and the R29 rehearsal remain open. The pointer-lock
hardware check follows the owner's update. The explicit step 2 stop keeps an incomplete labwc
comparison from passing even if both fixture inventories lack the affected paths. There are no
downloads over 500 MB in `.work/`.

## Paused 2026-11-21 evening (the lead)

- **Why:** mac-capacity asked all leads to slow Codex down until Monday. R29's cut waits for Deskflow (c) anyway, about 28 Nov.
- **Step 1's review:** REVIEW-1 (fresh Codex `gpt-6.2-sol` high, at `1767cf17`) is CHANGES-NEEDED.
  - Must-fix 1: the guardian audit row is compared as raw JSON bytes, in a different key order than the audit writer emits. Compare canonical JSON, keep fields, types and row order exact, and add a fixture from the audit writer.
  - Should-fix 2: the source guard skips Git-ignored files that the build copies from `os/config`.
  - Fix both in a fresh turn before step 2, then run a targeted recheck.
- **Step 2:** stopped partway, with nothing committed. The partial diff is kept outside the repo at `~/AresOS-331-step2-partial.patch` (764 lines); a fresh step 2 turn may read it or start over.
- **Next, in order:** step 1's fixes and recheck; step 2; steps 3 to 5.
- **Late-package notes (2026-11-21):**
  - B329 (PR143): the lead's os/ read is clean. Its image-difference list is in its PROGRESS.md under "For linux-aresos". R29's guest walk expects the AresOS theme.
  - For R29's Known limits: after Alt+Tab then Escape, the world keeps its pointer lock but gets no keys until you switch away and back. Main's rc.xml does the same; the frame isn't the cause (linux-desktop).
