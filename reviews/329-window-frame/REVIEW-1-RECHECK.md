# Package 329: REVIEW-1 recheck (Codex gpt-6.2-sol high, read-only, fresh context, at 7b27c1b9, 2026-11-21)

SAFE

1. **RESOLVED — Escape.** The harness injects unbound `A` after Escape in both private sessions. Neither world receives the key, both retain locked relative motion, and switching away and back restores key delivery. The inherited behavior is documented in `reviews/329-window-frame/KNOWN-LIMITS.md`.
2. **RESOLVED — Focused output.** The harness confirms the pointer is on the left while the right window stays focused, then verifies the picker on the right and unchanged pixels in the picker’s panel region on the left. The recorded `output="cursor"` run fails this check.
3. **RESOLVED — Log filter.** `os/tests/indicator-harness/frame.py` fails on `[ERROR]` from `theme.c`, `img/`, and `ssd/`. The recorded negative run exits 1 on real labwc 0.9.6 theme and PNG errors. I also checked the matcher against the installed build’s SSD source path.
4. **RESOLVED — Build gate.** Run `44953934586` passed `check_build=build`, including the image and UEFI guest checks, on `67287246`, the last commit touching anything outside `reviews/`. `7b27c1b9` only records the run.

**`2dbcb560` passes.** The installed `labwc-config(5)` and `labwc-actions(5)` confirm that `<default />` loads the defaults and a sole `None` clears the matching binding. The commit clears exactly Root Left, Right, and Middle presses and preserves the rest of the mouse configuration, including the existing title-bar scroll overrides. Both XML tests passed in this read-only recheck. The two saved compositor runs show all three bare-desktop presses and releases leave the menu closed, the title bar moves the window, the close button closes it cleanly, and the bottom-right edge resizes it.
Lead: all four resolved and the root-menu no-op checked. linux-aresos read the os/ diff clean at this head. Ready to merge.
