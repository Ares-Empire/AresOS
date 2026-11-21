# Reviewer: Codex gpt-6.2-sol high, read-only, at 8c8a5a4b, 2026-11-21

BLOCKED

1. **NOT RESOLVED — Colours.** `briefs/329-window-frame.md:26,31` now specifies shadows and list order. `LookA` returns opaque palette colours as RGBA tuples, so encoding by tuple length adds `ff` and fails the exact theme table check. Emit `#rrggbb` for alpha 255 and `#rrggbbaa` for non-opaque colours.
2. **RESOLVED — Comparison and test placement.** The unit test uses the fixed pre-329 fixture, the headless comparison uses the merge base, and untouched modules run in hosted CI.
3. **NOT RESOLVED — World fixture.** `briefs/329-window-frame.md:62,68` fixes configure, close and lock observation. Every `wl-harness` client paints the same colour. Use a contrasting app fixture and assert its client pixels in the overlap after the world takes focus. `os/input-portal/harness/clients/wl-harness.c:248`
4. **RESOLVED — All 36 images and deferred checks.** The private layout exercises `shade` and `desk` in both toggle positions and all focus and hover states. Live reconfigure and foreign-toplevel activation have explicit owners.
5. **RESOLVED — Bindings.** The scrolls start from states that expose the old actions, and the baseline table includes side snapping and Super+right-drag resize. The expectations match labwc 0.9.6’s defaults.
6. **RESOLVED — Final build and private hashes.** Step 2 waits for the build on the final pushed commit. The lead provides the hash list for both steps, and the check covers outgoing committed blobs and intermediate versions.
7. **NOT RESOLVED — B321 recovery.** `briefs/329-window-frame.md:67,85–86` assigns R29 ownership and gates the baseline, but shows double quotes where B321’s XML uses single quotes inside `command`. Reference the exact XML in `reviews/321-deskflow-image/PROGRESS.md:412–421`. Have B321 use an absolute shell path and update the old direct-command assertions before 329 accepts that baseline. `os/tests/test_everyday_account.py:112,232`, `os/tests/test_aresos_desktop.py:3495`, `os/ci/image-checks.sh:579,908`

- **New — Baseline assets.** `briefs/329-window-frame.md:61,67` stages the new theme and font only. Install the merge-base theme and font in the private harness too, so the move and resize comparisons use the shipped frame geometry. `os/tests/indicator-harness/in-container.sh:68–73`
- **New — The next binding.** `briefs/329-window-frame.md:59` exempts only B321, so the exact live delta will fail when 23c adds `Super_L`. Pin both ends of the historical delta and assert 329’s settings against the live XML. `STATE.md:204`

Read-only review. No files changed and no build or harness ran.

Lead: the five remaining points are small spec fixes, folded in without a further recheck.
