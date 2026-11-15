Reviewed `a07a3852` read-only. No builds, windows or real input were started.

1. **Blocking — helper guards do not guarantee session isolation.**  
   [capture.py:42](/var/home/ares/AresOS-31-window-frame/reviews/31-window-frame/capture.py:42), [capture.py:149](/var/home/ares/AresOS-31-window-frame/reviews/31-window-frame/capture.py:149), [wayland_input.py:27](/var/home/ares/AresOS-31-window-frame/reviews/31-window-frame/wayland_input.py:27).  
   Both guards validate `XDG_RUNTIME_DIR` but accept an absolute `WAYLAND_DISPLAY`. A mocked connection confirmed that a private runtime plus `/run/user/1001/wayland-0` reaches the owner’s socket. More seriously, directly invoking `--inside` with a private runtime and inherited owner `LABWC_PID` can reach cleanup after a display failure: `labwc --exit` signals that PID, independently of the display socket. This follows [labwc 0.9.6’s implementation](https://github.com/labwc/labwc/blob/0.9.6/src/main.c#L100). The normal bwrap entry is isolated; the exposed internal entries lack that guarantee.  
   **Fix:** verify the resolved socket and its compositor belong to the created namespace, reject inherited socket descriptors, use explicit checks rather than `assert`, and let the outer harness terminate only the process namespace it started.

2. **Should-fix — unchecked case arguments can delete outside the worktree.**  
   [capture.py:153](/var/home/ares/AresOS-31-window-frame/reviews/31-window-frame/capture.py:153).  
   Every positional argument becomes `WORK / case`, followed by `shutil.rmtree`. Absolute paths replace `WORK`; `..` components can escape it. Deletion happens before bwrap isolation.  
   **Fix:** allow only `normal`, `no-theme` and `no-font`, and verify containment before deletion.

3. **Should-fix — image checks can pass a broken-looking theme.**  
   [image-checks.sh:632](/var/home/ares/AresOS-31-window-frame/os/ci/image-checks.sh:632).  
   `themerc` is checked only for existence. An empty file passes. Each SVG needs only an SVG root and dimensions; empty, invisible buttons pass too. The success message therefore overstates what was validated.  
   **Fix:** verify the expected theme contents and button artwork against the reviewed assets, or validate their actual rendering.

4. **Blocking acceptance gap — this head lacks completed required hosted verification.**  
   [REPORT.md:214](/var/home/ares/AresOS-31-window-frame/reviews/31-window-frame/REPORT.md:214).  
   At review time, the [check build/VM run](https://github.com/Ares-Empire/AresOS/actions/runs/43519267255) was pending and the [regression run](https://github.com/Ares-Empire/AresOS/actions/runs/43519262929) was in progress. The successful build recorded in the report tested `fe6db50f`.  
   **Fix:** require both runs to finish green for the reviewed head and replace the report’s verification and cleanup placeholders with final results.

The remaining requested checks passed inspection:

- `rc.xml` parses; removing only the new theme block and switcher line reproduces main **byte for byte**, including package 23’s rules and recovery binding. The everyday-account test is unchanged.
- The `zz-` override name and AresOS scope are appropriate. The session exports `XDG_CURRENT_DESKTOP=AresOS`; strict schema compilation runs after config installation and propagates failure.
- Compilation rebuilds the **whole** schema cache. The one-key image query does not prove preservation of unrelated schemas/defaults; the release review must inspect those semantic changes before allowing the cache diff.
- Every theme key matches the [0.9.6 parser](https://github.com/labwc/labwc/blob/0.9.6/src/theme.c), and all 36 expected button files reproduce exactly.
- The font matches the specified SHA-256. The complete OFL and README attribution are present. Restoring `.gitattributes` to main and normalizing **only CRLF to LF** in the licence are correct.
- No Chrome preference, policy or rule was added. Only Crown ships. All changed `os/` files appear in the report.
- All 14 committed pictures contain test material. Both recovery pictures visibly show `recovered`. No caches, profiles or compiled schemas are committed; `.work/` contains no file over 500 MB.

CHANGES-NEEDED