# 01c: Launch the right app when switching slot and clicking in the same tick

Follow-up on branch `pkg/01-first-app` (PR #1). Read `reviews/01-first-app/REVIEW-01b.md`.

**Goal:** pressing a hotbar number key and right-clicking before the next client tick launches the app in the **newly selected** slot, exactly once. It never launches nothing, and never launches the previously selected app.

**In scope:**
- Keep the press/release edge tracking from 01b.
- Resolve which item is activated **after** vanilla has processed pending hotbar selection, and before block/entity interaction.
- Scroll-wheel selection follows the same rule.

**Acceptance:**
- `./gradlew build runClientGameTest` passes.
- New fake-launcher client tests deliver the number-key press and the use press/release with **no tick in between**, covering:
  - empty slot → app: one launch of that app
  - app A → app B: one launch of B, none of A
  - app → empty slot: no launch
- All 01/01b tests still pass.
- Add a short "01c" section to `REPORT.md`. Stop your Gradle daemons when done.

**Out of scope:** everything else.

**If unsure:** behave like vanilla. Whatever vanilla would use on that click is what gets activated.

**Model:** gpt-6.1-sol, xhigh.
