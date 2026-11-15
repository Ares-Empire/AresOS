Reviewed commit `a215c15ec2d231eb1fe963b1db6a30d058ec4ba5`, read-only: only file reads and read-only git commands; no helper, tests, builds or other programs run; no files changed.

Scope: `85be2dbb..HEAD` in the requested helper, tests and report section. Findings and test assessments below are from static inspection; the reported execution results were not independently reproduced.

| Point | Status | Reason |
|---|---|---|
| 1 | OPEN | The idle check runs on the worker, but rejected links can make its signature invalidate itself indefinitely. Missing dependencies also prevent some pictures from recovering. A dead mount can still block the sole icon worker; it does not block serving. |
| 2 | OPEN | Index content reads use the checked, pinned descriptor and bounded reads; directory counts and listings are bounded. New readable opens retain confinement. However, an empty or structurally invalid index can silently disable the fixed-layout fallback. |
| 3 | OK | PNGs rank by Size regardless of Type, including Scalable folders. SVG and oversized-PNG ordering implements the stated choices. Picture-loss cases below concern lookup invalidation and fallback, rather than ranking. |
| 4 | OK | Construction emits one WARNING identifying missing tools. Per-picture conversion failures remain DEBUG. |
| 5 | OK | `StartupTest` supplies a temporary HOME, patches application directories and the icon cache, and registers discovery-thread cleanup. |
| 6 | OK | The Flatpak case uses the private display and non-activating session bus, checks for existing KCalc, and stops exact scopes attributed to its own launch. No new route to the owner’s compositor or session bus was found. |
| 7 | OK | The new tests model an immediately absent scope, a live launch process, window appearance and closure, and eventual process exit. The unchanged helper correctly lets the window determine closure and keeps waiting while the process lives. |
| 8 | OK | Fixtures and executable stand-ins avoid dependence on installed Breeze or the registry’s three programs. The report identifies preservation controls and explicitly says StartupTest and FlatpakScopeTest pass without helper changes. Exact mutation-test counts were not reproduced. |
| 9 | OPEN | Completing a pass after pruning a full cache can leave pictures permanently missing. Converter isolation and limits, catalogue/launch behavior and 1.0 answers are otherwise unchanged by this diff. The `shell-1.1` example messages have no diff. |
| 10 | OPEN | Most judgment calls are sound. Following rejected link targets in the signature is unsafe for session-long processor use; the individual decisions are assessed below. |

1. **FIX — A rejected index link can make every picture pass invalidate itself.**

   **Where:** [aresos-shell:1374](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1374), [aresos-shell:1263](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1263), [aresos-shell:1670](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1670), [aresos-shell:1714](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1714).

   **Scenario:** `~/.local/share/icons/hicolor/index.theme` is a symlink to the helper’s existing `~/.cache/aresos/icons` directory. Ordinary valid pictures also exist in the fixed layout.

   `layout()` records the link target’s stat **before** `read_icon_index()` rejects it as outside the icon root. The fallback then converts the ordinary pictures. Every `convert()`, including a cache hit, calls `prepare()`, which chmods the cache directory and changes its ctime. The saved signature therefore already differs when the pass finishes. Every subsequent three-second request runs another full pass, repeats the warning and changes that ctime again.

   This requires only a static input link, not an already-running hostile process. It meets the explicit bar for processor work recurring throughout the session. A rejected link onto a continuously changing external file creates the same problem.

   **Fix:** distinguish accepted dependencies from rejected paths. For rejected links, track enough confined link/component metadata to detect their replacement without subscribing to the rejected target’s metadata. Apply this to folder listings as well as indexes, and add a regression test proving repeated requests settle despite the cache-directory link.

2. **SHOULD — A dangling icon link becoming valid is invisible to the signature.**

   **Where:** [aresos-shell:1419](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1419).

   **Scenario:** an indexed application folder contains `app.svg`, a symlink to a missing file in an existing, permitted folder elsewhere beneath the same icon root. That destination folder is not itself part of the lookup layout.

   The first pass sees the link but `candidate()` records it only when `isfile(real)` succeeds. Later, an installation completes by creating the destination file. The application folder, root and index remain unchanged; only the unrecorded destination and its immediate parent change. No new pass occurs, so the program keeps its fallback picture indefinitely.

   **Fix:** retain confined candidate dependencies even when their current answer is “missing.” Test creation of a dangling link’s destination without modifying the link’s parent.

   This is a persistent picture defect, below the mandatory-fix harm bar.

3. **SHOULD — Pruning can free the cache without allowing refused pictures another pass.**

   **Where:** [aresos-shell:1697](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1697), [aresos-shell:1820](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1820).

   **Scenario:** the cache starts at its file or byte quota with old, unreferenced generations, while the current catalogue needs different pictures.

   `room()` refuses those conversions. At the end, `prune(pictures)` removes the old generations and makes room, but `step()` marks the pass finished. No successfully produced target exists to record for the refused pictures, and the input signature remains unchanged. Later requests skip conversion permanently. The previous periodic implementation recovered on its next pass.

   **Fix:** prune stale entries before quota-dependent conversion, or schedule a bounded follow-up when pruning frees space after quota refusals. Do not turn persistent quota exhaustion into unconditional retries.

   This loses pictures rather than owner data, so it is SHOULD under the stated bar.

4. **SHOULD — Missing index structure silently suppresses the fixed layout.**

   **Where:** [aresos-shell:1296](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1296), [aresos-shell:1383](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1383).

   **Scenario:** a theme has valid fixed-layout PNGs, but its first `index.theme` is empty, contains ordinary garbage text, or lacks `[Icon Theme]`/`Directories`.

   The parser returns `[]` without raising. Because that is different from `None`, indexed roots take the index branch and never use their fixed layout. Previously available pictures disappear, with no warning.

   **Fix:** reject missing required index structure so these cases take the existing one-warning fallback. Preserve the deliberate handling of individual directories with unusable Size or Scale. Add empty-file and missing-header/key cases to the malformed-index tests.

   This violates the requested fallback behavior but remains a picture-only defect.

The private session bus is the right choice for the Flatpak check. Its configuration has no service directories, so the launched Flatpak receives neither the owner’s bus address nor a route to activate portals on that private bus. Combined with the private Wayland runtime, unset DISPLAY and removal of inherited Wayland socket variables, it is sufficient for the intended KCalc session separation. It is not a separate-UID sandbox; the explicitly permitted user-manager connection remains available. The cleanup selects the Flatpak scope through the helper child’s parentage and cgroup, not merely its application name.

For the twelve judgment calls at [REPORT.md:769](/var/home/ares/AresOS-30-installed-programs/reviews/30-installed-programs/REPORT.md:769):

| Judgment call | Assessment |
|---|---|
| First index governs indexed roots; unindexed roots retain fixed layout | Agree. This follows the brief. Finding 4 concerns recognizing a broken index. |
| Reject unsafe relative paths; skip unusable Size/Scale | Agree with the policy. Required index structure also needs validation. |
| Rank PNGs by Size regardless of Type | Agree. This preserves hicolor’s large PNG preference. |
| Preserve fixed-layout `scalable/` behavior | Agree. It retains existing compatibility. |
| Put oversized PNGs after SVGs | Agree with the documented interpretation of “nothing of 256 or less.” |
| Complete with fallback when the listing budget is exhausted | Agree. This bounds work without creating automatic retry loops. |
| Request every three seconds; let the worker decide | Agree. Filesystem checks stay off serving. |
| Follow links in signature stats | **Disagree as implemented.** Accepted Flatpak targets need tracking, but rejected targets must not drive invalidation. Finding 1 gives a session-long feedback loop. A stalled accepted mount also remains capable of freezing picture updates on the sole worker. |
| Include produced pictures in the signature | Agree. Cache deletion should recover. This does not cover the quota/pruning case in finding 3. |
| Warn in `IconCache.__init__`, retain quiet individual failures | Agree. |
| Give the headless check its own non-activating session bus | Agree, for the reasons above. |
| Add Flatpak lifecycle tests despite finding no helper defect | Agree. These are useful preservation tests for behavior exercised only manually otherwise. |

VERDICT: CHANGES-NEEDED