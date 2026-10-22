# 08b: Walk-in logos, review fixes

Follow-up on branch `pkg/08-walk-in-logos` (PR #7). Read `reviews/08-walk-in-logos/REVIEW.md` and `REPORT.md` first.

**Goal:** fix all five findings. Rules: **an app opens once per real entry**, and **the builder never destroys or obstructs anything.**

**In scope:**
1. **Per-zone membership (blocking).** Track membership and launch state per zone. A zone can launch again only after the player has actually left that zone, no matter what neighboring zones do. Regression: two adjacent zones sharing a boundary, moving along the seam → each launches at most once per real entry.
2. **No neighbor destruction (blocking).** Before writing, check that the planned placement doesn't invalidate existing neighboring blocks (cactus, torches, plants, redstone, anything with survival or support rules). Refuse if it would. Game test: a cactus directly behind a proposed wall remains unchanged and the build is refused (or proceeds only with the existing explicit confirmation, which then also covers neighbors).
3. **Don't block saved exits.** Reject proposed logo blocks that intersect any saved exit's standing body, and keep the existing trigger/exit checks. Test: disjoint trigger boxes where the new wall would obstruct an existing exit → refused.
4. **Return token survives open screens.** Separate return-token ownership from permission to close the pause screen. The zone-return teleport still happens when the player opened a screen before the app took focus, and that screen stays open. Client test for this delayed-focus case.
5. **Explosion protection.** Auto-built logo blocks are immune to explosion destruction (TNT, beds, respawn anchors, creepers if present). Build-mode players can still mine and edit them. Test real explosions next to a logo, in Live and in Build.

**Acceptance:**
- Each new test fails before its fix (show it) and passes after.
- Full `build runClientGameTest` twice, green.
- An "08b" section in `REPORT.md`. Stop your Gradle daemons.

**If unsure:** refuse and explain, rather than build or launch.

**Model:** gpt-6.1-sol, xhigh.
