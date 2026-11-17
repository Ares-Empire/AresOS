No blocking, should-fix, or nit findings in the requested scope at `e4c59533`.

- **Review fix 2 closes REVIEW-2:** the shared `Supplier` overload observes entity and POI writes once. Terrain retains its separate observer without double counting. Failure accounting completes before the barrier releases, and failed empty-entity deletions latch `error` until reopening. The regression exercises the real `WorldSaves` path, checks two refusals and stale disk data, then success after reopening.
- **Write-path re-audit:** the cached 26.2 bytecode supports the report’s POI delegation, region deletion and flush coverage, and its exclusion of offline recreation.
- **Home switching:** admission, queued/joined requests, execution and answer handling enforce `no_world`; revision tracking invalidates saves crossing switch start. Staging and recovery remain guarded.
- **Shared gate and display:** both callers use the same helper-independent session/desktop predicate. HUD suppression covers the entire busy interval, and package 48’s screen replacements remain.
- **Readiness and tests:** `readyWorld` retains the busy guard and uses `DesktopWorld.saveName`. The save test now checks the non-pausing AresOS menu while retaining paused Settings and covered-world cases.
- **Merge preservation:** both parents’ initialization, mixin registrations, test entries and Gradle settings survive. Package 48’s screenshot numbering remains intact, with package 46 appended.

Reviewed files, cached bytecode and the specified git diffs only. No builds, Gradle, tests or game processes ran; no files changed.

SAFE