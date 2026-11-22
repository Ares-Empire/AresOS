# Reviewer: Codex gpt-6.2-sol high, read-only, fresh context, at 8715ac8d, 2026-11-21

CHANGES-NEEDED

- **BLOCKING** `os/tests/indicator-harness/frame.py:745` — The Escape check treats an activated window as proof that keyboard focus returned. Both world logs show `KBD_LEAVE` when the picker opens and no `KBD_ENTER` until switching away and back. Inject an unbound key after Escape in both private runs and record whether the world receives it. Document any inherited keyboard loss alongside the pointer-lock result.
- **BLOCKING** `os/tests/indicator-harness/frame.py:783` — The focused-output check opens the picker with the pointer and keyboard focus on the same output. It would also pass with `output="cursor"`. Move the pointer to the opposite output before opening the picker and check that only the focused output shows it.
- **BLOCKING** `os/tests/indicator-harness/frame.py:103` — The log filter misses real labwc theme errors, including `titlebar.height is no longer supported`, and uses `img/png.c` where labwc logs from `img/img-png.c`. Match `[ERROR]` severity and the actual theme, PNG and decoration source paths.
- **BLOCKING** `reviews/329-window-frame/PROGRESS.md:72` — The recorded green image build covers `0dbd6256`. The current head `8715ac8d` adds only review documentation, but the brief requires a green build on the final head. Run `check_build=build` on the corrected head and record the run in the PR.

`rc.xml` and its tests are together in `abf1fde2`. The image assertions are in the separate `ed203ac1` commit. The indicator fixture change synchronizes JSON access and leaves the assertions intact. The outgoing scan found no cache files, private hash matches, or new owner identifiers. The review was read-only.
Lead: all four are fixed in fix round 1; the root-menu no-op is added in the same round (agreed with linux-aresos).
