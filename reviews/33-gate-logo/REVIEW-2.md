Reviewed only `e5ac84e0..7059daf4` and affected paths, ignoring the later merge. Read the requested review, brief and report; inspected relevant cached 26.2 bytecode. No Gradle or game execution, and no files changed.

| Original finding | Verdict | Assessment |
|---|---|---|
| 1. Removal destroys additions | **CLOSED** | Preflight checks attachments, falling blocks and hanging entities before mutation. Refusal preserves blocks, sign and record. A new excessive-refusal problem is detailed below. |
| 2. Edited light loses water/state | **CLOSED** | Only dry level-15 lights are removed; changed lights remain. |
| 3. External mushroom changes | **CLOSED** | Ownership requires a recorded coordinate and matching block ID. External mushrooms are refused; the palette callback test checks all sixty blocks. |
| 4. Doormat overwrites landscaping | **CLOSED** | Implements the revised grass/dirt-only rule and complete surrounding ring, including the rear row. |
| 5. Terrain remains changed | **CLOSED** | Records footprint grass and restores recorded positions only when currently dirt. Other block kinds remain; missing `grass` fields default to an empty list. |
| 6. Incomplete loaded-area check | **CLOSED** | The guard now covers the neighbour halos, light radius and added inspection areas, using chunk coordinates and non-loading presence checks. |
| 7. Half-opacity threshold | **ACCEPTED-AS-DECIDED** | Retained as instructed; HUB.md contains the orchestrator’s correction. |
| 8. Downgrade loses cleanup records | **ACCEPTED-AS-DECIDED** | The report documents the consequences and manual cleanup for hand-built gates. |
| 9. Unchecked sign space | **CLOSED** | Placement validates sign clearance before mutation. The deliberately conservative height bound is documented. |
| 10. Hard-coded default size | **CLOSED** | Default-dependent assertions and client spacing derive from `SIZE`; explicit size-12 examples remain. |

**New finding 11 — should-fix: harmless edits can indefinitely prevent removal.**

At [Neighbors.java:88](/var/home/ares/AresOS-33-gate-logo/mod/src/main/java/dev/aresos/zone/Neighbors.java:88), called by [GateBuilder.java:241](/var/home/ares/AresOS-33-gate-logo/mod/src/main/java/dev/aresos/zone/GateBuilder.java:241), the removal preflight applies the placement whitelist to blocks that will remain.

A concrete reproduction is to build a gate, replace one middle pixel with a dry stone slab, then remove the gate. The slab is correctly excluded from the removal set, but the neighbouring removed pixels cause it to be inspected. Its non-full collision shape makes `inert` reject it every time. A quartz pillar replacement also fails because its `RotatedPillarBlock` class is outside the whitelist.

Neither requires support or changes state when neighbouring gate blocks disappear. The cached vanilla slab implementation schedules fluid ticks only when waterlogged. Nevertheless, removal requires the owner to dismantle his harmless edit first. Ordinary Build-mode customization is within the promised changed-block behavior; this is not unusual self-sabotage.

**Fix:** recognize verified inert retained states, including dry ordinary slabs and inert pillar blocks, without requiring full-cube geometry. Keep the checks for attachments, gravity, fluids and reactive states. Extend the changed-block regression to require successful removal with these edits preserved, alongside the existing torch/sand/frame refusal cases.

I found no further actionable regression in the requested areas. Two-block gate spacing remains compatible with the checks. Refusal occurs before mutations, and the attachment checks cover the inspected support-loss cases.

The documented inability to distinguish owner-laid grass/dirt, or intentional dirt replacements at recorded grass positions, remains a known limit under the follow-up decision. Likewise, deliberate replacement with an identical recorded block cannot establish new ownership. These do not warrant another fix round.

CHANGES-NEEDED