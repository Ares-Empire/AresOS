READY

1. Resolved. Coverage uses the clipped union of placed, non-minimized windows on the known world output (`docs/design/COMPONENTS.md:819`). Section 8 tests duplicate slots and partial overlaps that leave a gap (`docs/design/COMPONENTS.md:1749`).
2. Resolved. The compositor reports the action target's handle, output and placed rectangle on the shell's Wayland connection (`docs/design/COMPONENTS.md:800`). Section 8 tests delayed handling after focus changes and checks both windows in a share (`docs/design/COMPONENTS.md:1749`, detailed at `docs/design/COMPONENTS.md:867`).
3. Resolved. The overview releases its exclusive layer and waits for a Wayland round trip before the shell requests activation (`docs/design/COMPONENTS.md:1204`). Section 8 tests picking Home from a covering app and cancelling over the partly visible, focused world (`docs/design/COMPONENTS.md:1750`).
4. Resolved. Failed validation invalidates the active cache, withdraws managed theme and icon overrides and reloads labwc. Visible surfaces redraw in A and the chosen setting stays put (`docs/design/COMPONENTS.md:1558`). Section 8 starts with working B/C overrides and checks both a missing and an invalid jar (`docs/design/COMPONENTS.md:1748`).
6. Resolved. The checks require a just-requested prompt outside the game and a fingerprint comparison against `main` via the saved phone bookmark. The design rejects prompt-time links and limits the stylesheet protection to styling and label changes through Qt properties (`docs/design/COMPONENTS.md:1347`, `docs/design/COMPONENTS.md:1367`). Section 8 tests those checks and gives no trust to appearance or position (`docs/design/COMPONENTS.md:1752`).

No new findings. B remains the default among A, B and C, the indicator's place and size default to top centre and medium (3x), and window frames follow the chosen look (`docs/design/COMPONENTS.md:607`, `docs/design/COMPONENTS.md:1443`).

Ran the requested `git diff` and `git diff --check` (clean), checked the design against REVIEW-1, the brief, the install guide, the shell and the installed labwc manuals and documentation, and confirmed `labwc --version` reports 0.9.6. No runtime tests were run.
