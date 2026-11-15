Reviewed PR #55 at `ab58d12f80cbb5633246da2c78f2b2c6dfcc200e`, restricted to `5fbe6d20..ab58d12f` and the affected paths. This was read-only: **no helper or tests run, no files changed. Two FIX findings remain open.**

| First-review finding | Status | Reason |
|---|---|---|
| 1. Discovery can stop the launcher | **OPEN** | Enumeration is bounded and asynchronous, but listing still performs blocking executable checks on the serving thread. |
| 2. SVG memory consumption | **OPEN** | The converter ceiling works, but the new SVG pre-check introduces memory amplification inside the helper, outside that ceiling. |
| 3. Unbounded icon cache | **CLOSED** | File/byte quotas and pruning prevent the original accumulation. Deletion races remain a low-harm limit below. |
| 4. systemd argument expansion | **CLOSED** | The common launch command includes `--expand-environment=no` before `--`, covering registry, discovered and terminal launches. |
| 5. Input-link confinement | **CLOSED** | Content reads and theme enumeration use checked, pinned descriptors. Named icons are checked again when opened. Flatpak’s two `app/` deployment roots are allowed; explicit absolute icons retain their documented exception. |

1. **FIX — High: listing can still block the entire serving loop.**

   **Where:** [list_apps/app_row](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:2467), [availability](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:2450), [resolve](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:398).

   **Scenario:** discovery successfully lists an executable on a mounted filesystem. That filesystem subsequently stalls. Every `list_apps` builds rows for the whole catalogue, calling `resolve()` and therefore `isfile()`/`access()` on each executable, synchronously. Requesting a page containing other programs still reaches that executable.

   **Harm:** listing, heartbeats, launches and window processing stop together. No hostile program needs to be running; an ordinary failed mount suffices. The last good catalogue does not protect this path.

   **Fix:** publish availability with the worker’s completed catalogue and serve those cached values. Perform launch-time filesystem validation asynchronously too, with bounded outstanding work.

   The worker itself improves substantially: enumeration counts rejected entries, byte accounting includes hard links, publication uses a lock, and frozen `App` objects are replaced rather than mutated across threads. One permanently blocked scan creates no replacement-thread accumulation. However, the advertised two-second deadline is checked during enumeration/stat collection, **not during subsequent parsing or immediately before publication**; add those checks as part of finishing this fix.

2. **FIX — High: the new SVG pre-check can exhaust the helper’s memory.**

   **Where:** [drawn_svg parser creation](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1267), [its invocation before conversion](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1494).

   **Scenario:** an otherwise small SVG declares a long namespace URI and contains many distinct short names in that namespace—for example, a 256 KiB URI and 50,000 empty elements named `p:n0`, `p:n1`, etc. This fits below the 8 MiB input cap and needs neither a DTD nor an entity declaration.

   Namespace processing expands every name to include the URI. Python’s default Expat wrapper retains distinct expanded names in its intern dictionary. Static analysis therefore predicts roughly **12 GiB of retained name text** if this example finishes parsing. These allocations occur in the helper, before the memory-limited subprocess starts. [Python parser documentation](https://docs.python.org/3.14/library/pyexpat.html#xml.parsers.expat.ParserCreate), [CPython implementation](https://raw.githubusercontent.com/python/cpython/3.14/Modules/pyexpat.c).

   **Harm:** merely discovering the icon can cause memory pressure or OOM affecting the launcher and desktop. A background thread provides no memory isolation.

   **Fix:** move the complete pre-check into a process with memory and time limits. Also bound namespace/name lengths, element/attribute counts and nesting, and avoid retaining unbounded expanded names. The existing tests do not cover this amplification.

   The converter’s own `prlimit --as=268435456` is correctly placed before `bwrap`: it sets both limits, inherited through fork/exec by ImageMagick and descendants. This is a **per-process** ceiling, not a combined process-tree quota. Large legitimate icons can fail and use the fallback; that alone is acceptable under the launcher bar. [prlimit documentation](https://man7.org/linux/man-pages/man1/prlimit.1.html), [Linux resource-limit semantics](https://man7.org/linux/man-pages/man2/getrlimit.2.html).

The following are **KNOWN LIMITS**, not additional blockers under the requested harm-based bar:

- **Low — CSS references can bypass the new pre-check.**  
  **Where:** [per-callback CSS checking](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1300). A `<style>` containing `u&#114;l(...)` or `@im&#112;ort "..."` splits the forbidden token across character-data callbacks. Each fragment passes, while the renderer receives the reconstructed CSS. CDATA boundaries provide another split. This is a static finding; I did not execute a reproducer. [Expat callback buffering](https://docs.python.org/3.14/library/pyexpat.html#xmlparser.buffer_text), [librsvg CSS imports](https://gnome.pages.gitlab.gnome.org/librsvg/doc/src/rsvg/css.rs.html).  
  **Harm:** the claimed reference ban is incomplete; embedded styles/resources can reach the renderer. The independent sandbox, timeout and address-space ceiling still contain that work, so this does not establish host-file disclosure or unbounded converter memory. **Fix:** accumulate bounded complete style text and validate it with CSS tokenization before conversion. Ordinary encoded attribute values, alternate xlink prefixes, prohibited element namespaces and DTD/entity declarations are otherwise handled defensively.

- **Low — cache pruning can invalidate paths still being used.**  
  **Where:** [generation deletion](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1552), [pruning](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1589). During a normal icon update, the old PNG is unlinked before its replacement is published. A game holding the old pathname can fail to open it. Two listed programs sharing one source can also receive different generations if that source changes between their conversions; processing the second deletes the first’s file.  
  **Harm:** missing/fallback icons, including for a still-listed program; no owner data loss. **Fix:** protect published references, reuse one source snapshot per pass, and retire generations after publication with bounded retention within the quota.

- **Low — a scan that never returns freezes future discovery.**  
  **Where:** [Discovery.refresh/loop](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1083). A permanently blocked filesystem call occupies the sole worker indefinitely. The completed catalogue remains available, but later installations cannot appear.  
  **Harm:** stale discovery until recovery/restart, separate from the serving-thread blocker above. **Fix:** if automatic recovery is required, isolate scans in a supervised process with bounded replacement attempts.

- **Low — window identities remain presentation claims.**  
  **Where:** [hint application](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:872), [window matching](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1968), and the shipped hint JSON files. Another Minecraft launcher’s `com.mojang.minecraft` window can be attributed to Lunar; an otherwise unclaimed `steam_app_*` window can be attributed to Steam. An already-running hostile owner process can spoof identities more generally.  
  **Harm:** incorrect open/focus state or return timing, not command execution or privilege gain. **Fix:** narrower reviewed identities where available; stronger attribution would require compositor-provided process information. The original name/icon impersonation limit also remains accepted.

Hints are validated at least as strictly as registry entries for the relevant fields, with bounded identity lists and conflict rejection. Discovered candidates cannot take registry identities; exact/reserved matches precede prefixes; `aresos-desktop` is explicitly rejected in hints and checked first during matching. I found no new hint-based override of those protected identities.

CHANGES-NEEDED