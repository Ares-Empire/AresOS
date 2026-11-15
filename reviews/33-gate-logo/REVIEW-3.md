Finding **11 is CLOSED**: dry slabs, quartz pillars and ordinary stairs now pass removal preflight and remain intact. The added regression checks their exact states. Placement’s stricter check is unchanged.

**New finding 12 — blocking: permitted wall updates can escape the inspection radius.**

Where: [Neighbors.java:51](/var/home/ares/AresOS-33-gate-logo/mod/src/main/java/dev/aresos/zone/Neighbors.java:51) permits wall shape updates, but [Neighbors.java:82](/var/home/ares/AresOS-33-gate-logo/mod/src/main/java/dev/aresos/zone/Neighbors.java:82) still inspects only two face-steps from the original removal set.

A concrete arrangement beside a gate built on stone:

- Place two dry walls vertically at `plan.at(1, -1, 0)` and `plan.at(1, -1, -1)`.
- Make both connect straight across the column axis: the upper wall connects between the gate and an owner-placed stone block; the lower connects between the stone floor and another stone block. Keep their other horizontal sides clear.
- Put an upward-facing observer beneath the lower wall, at `plan.at(1, -1, -2)`.

Initially both walls have no central post. Removing the gate connection makes the upper wall raise its post; the lower wall then raises its post too. That update reaches the observer, which is three face-steps from the nearest removed block and therefore escapes preflight. It schedules a pulse and changes its powered state, potentially activating the owner’s circuit.

This follows the cached 26.2 implementations of `WallBlock.shouldRaisePost`, recursive neighbour-shape updates and `ObserverBlock.updateShape`; it was **not executed**. The allowed cosmetic wall changes are fine, but the resulting observer activation violates the preservation rule.

**Fix:** extend removal preflight through potentially changing connection chains and inspect their affected neighbours, with corresponding loaded-area and entity checks. Refuse before mutation when that propagation cannot be established safely. Simply increasing the fixed radius is insufficient because stacked walls can propagate farther. Add a regression for this arrangement that requires refusal and unchanged blocks, sign and record, including after scheduled ticks.

The other requested checks hold locally: torch, sign, button, vine and rail attachments remain refused; falling blocks, hanging entities, fluids and unknown/reactive callbacks remain guarded. The new decision uses inherited game callbacks and explicitly verified implementations, rather than block-name lists. However, that local classification does not cover the propagation above.

Reviewed only the specified diff and affected behaviour at `ce43d863`. No files changed; no Gradle or game run.

CHANGES-NEEDED