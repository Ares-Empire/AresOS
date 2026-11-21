Reviewed PR #120 at `ff28bf0153d41ae36047df080d07a260ce161b3d` against `origin/pkg/53c-laptop-home...HEAD`. I compared all ten screenshot pairs and ran 13 read-only model and unit checks. All 13 passed. Separate probes reproduced the click, finder, and worker issues below. I changed no files, launched no compositor, and left CI alone.

## Blocking

1. **The PNG decoder can reach the owner’s credentials and session.** `os/config/usr/libexec/aresos-laptop-home:195`  
   The child gets only `PATH`, `LC_ALL`, and its standard streams. It still runs as the owner with the host filesystem, `/proc`, and named Unix sockets visible. That leaves the helper socket and the supervisor’s mode-0600 token file accessible to the process parsing the PNG. Clearing Python and libc’s environment works for inheritance, but leaves the parent’s original exec environment in procfs. I found no direct token transmission or decoder exploit. **Fix:** follow the helper’s icon-worker sandbox at `os/config/usr/libexec/aresos-shell:1859`. Expose only the decoder runtime and its pipes, hide the host runtime directory and process view, and enforce the output cap before buffering the reply.

## Known limits

2. **Clicks can launch a house behind the finder or outside the painted town.** **Should-fix.** `os/config/usr/libexec/aresos-laptop-home:889`, `:943`, `:2144`  
   In the 45-house fixture, clicking the five-result finder header opened `test-tool-17`. In a 2304×1080 window, clicking the black left margin opened `test-tool-19`. The finder’s rows receive hits, but its header and padding pass them through. The painter clips to the stage, while hit testing accepts coordinates outside it. The day group sign also has a 200 px hit box regardless of its painted width. **Fix:** use the painted bounds and stacking order for both click and hover, reject points outside the stage, and let finder chrome consume clicks.

3. **Finder icon work accumulates while typing.** **Should-fix.** `os/config/usr/libexec/aresos-laptop-home:2159`  
   The lock serializes decoding, but each newly visible icon starts its own thread. A probe with ten result changes scheduled 50 threads. Stale rows can hold up current results, and failed jobs remain recorded indefinitely at the same path. **Fix:** use one worker with a bounded queue for the current rows, discard obsolete results, and invalidate failures when the catalogue changes.

4. **Logo memory grows across town changes.** **Should-fix.** `os/config/usr/libexec/aresos-laptop-home:1502`, `:1516`  
   Both logo caches retain IDs after houses are removed or slots are unpinned. Repeated redraws of a fixed town reuse the entries, but the current-town cap does not bound retained surfaces across catalogue changes. **Fix:** prune against current house and slot IDs, and add a memory check that types, slides, rotates finder results, clears the query, and samples again at rest.

5. **Valid desktop-entry text can break finder ranking or paint outside the list.** **Should-fix.** `os/config/usr/libexec/aresos-laptop-home:694`, `:1966`  
   A program named `2²` raised `ValueError` when I searched for `2`. Python accepts `²` in `isdigit()` and rejects it in `int()`. The sort also differs from 53c’s numeric English collation for accented names, which can change what Enter opens on a tie. Separately, a valid 64-character generic name painted from x = −184 in a row starting at x = 59. 53c ellipsized both columns. **Fix:** use numeric collation compatible with 53c, allocate bounded widths to both labels, and test accented ties, Unicode numbers, and long generic names.

6. **Tab and focused-button activation disappeared.** **Should-fix.** `os/config/usr/libexec/aresos-laptop-home:2098`, `:2188`  
   53c used focusable buttons and deliberately preserved Enter and Space activation on a focused button. The drawing area has no equivalent focus targets, so the keyboard cannot reach end signs or group signs through that route. **Fix:** restore focus traversal, a visible focus indicator, and activation through the same handlers as pointer input.

7. **Night slides can visibly stutter.** **Should-fix.** `os/config/usr/libexec/aresos-laptop-home:1587`  
   With 45 houses and the `tool19` query, the model and offscreen paint took a median of 64.9 ms per frame at night and 14.5 ms by day. This measures software painting, before compositor overhead. The night painter repaints two full-stage radial gradients on every glide frame. **Fix:** clip the gradients to their visible bounds and remeasure frame intervals through labwc.

8. **Several checks can pass with the behavior they claim to cover broken.** **Should-fix.** `os/tests/test_aresos_laptop_home_native.py:67`, `:451`, `:522`, `:599`, `:703`; `os/tests/laptop_home_headless.py:387`  
   The grid check can skip a missing plot side. The idle-color assertion uses the production color function as its oracle. The rest counter records `after-paint`, so it does not directly count tick callbacks. The real pointer click lands on the sky and can still focus the layer if the app’s click handler is disconnected. The focus test selects whichever surface the environment provides. **Fix:** require both plot sides, use independent reference pixels, count tick callbacks, assert the helper receives the ID from a real house click, and run focus and reconnect explicitly in both surface modes. The earlier paint-break results are in commit `a58b608a`; carry them into the final report.

9. **The headless harness still exposes host pathname sockets.** **Should-fix.** `os/tests/laptop_home_headless.py:145`, `:223`  
   The current input driver explicitly connects to the private Wayland socket, and `/dev` is masked before labwc starts. The read-only bind of `/` still exposes host `/run`, including the owner’s Wayland and D-Bus sockets. Network isolation covers abstract sockets. **Fix:** mask host `/run` before labwc starts, bind back only the fixture paths, and verify that the private display and stand-in helper remain reachable.

The shipped entry point has no test-channel hook. The channel lives in the harness and renders screenshots from its own Cairo surface. The lead’s 64,000 KiB software guard stands, and the 60 MiB target remains for the Intel laptop trial.

CHANGES-NEEDED