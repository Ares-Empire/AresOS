# 07b: Real apps, review fixes

Follow-up on branch `pkg/07-real-apps` (PR #6). Read `reviews/07-real-apps/REVIEW.md` and `REPORT.md` first.

**Goal:** fix all five review findings. Rules: **an app is never silently duplicated or dropped**, and **`pinned: true` always ends up in the hotbar when there's room.**

**In scope:**
1. **No permanent duplicates (blocking).** Reconcile full launch identities (target, arguments, working directory, AUMID) against existing config entries **before** choosing shortcut representatives or wrapping launches. Prefer existing ids, preserve owner argv, diagnose ambiguous matches. Tests: adding an earlier-sorted alias shortcut to an already-known app, and configured commands with arguments.
2. **No silent drops (blocking).** Launch equivalence includes the working directory. Collapse shortcuts only when their launch behavior really is equivalent. Fixture: identical target and arguments with different working directories → two apps.
3. **Pins through any container.** Track hotbar membership changes in applicable container menus (chest and so on), with the existing Live/desktop/host guards. Test pin and unpin through a chest.
4. **Overflow pins move into freed slots.** During population, move an existing pinned item from the main inventory into a free hotbar slot, without duplicating it or overwriting ordinary items. Test: full hotbar → overflow → free a slot → rejoin → the app is in the hotbar.
5. **Failed icon refresh falls back.** Invalidate owned generated files and merge an empty icon result when extraction fails, so the `look` fallback shows. Keep custom icon paths. Test: successful extraction followed by an unreadable or missing source.

**Acceptance:** each new test fails before its fix (show it) and passes after. Run the full `build runClientGameTest` twice, green both times. Add a "07b" section to `REPORT.md`, and stop your Gradle daemons.

**If unsure:** keep every config entry and the owner's choices; never guess an identity.

**Model:** gpt-6.1-sol, xhigh.
