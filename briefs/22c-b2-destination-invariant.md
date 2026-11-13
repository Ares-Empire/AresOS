# 22c, follow-up: the model's destination invariant when a newer release waits to be installed

Follow-up to `briefs/22c-ways-back-after-update.md`, on the same branch. The builder of stage 1a's step 2 stopped where the brief told it to: two of its rules contradict each other in one state.

**The state.** The older AresOS runs and is first, a newer AresOS is installed beside it, and the tools' bundle names a release that is not installed yet: `[R13*, R27, S]` with a bundle for R28.

**The conflict.** Rules A4 and A6 make `update` stage R28 there. B2's invariant demands that each installed system can be made the next start by one command, and no command selects R27 in that state.

**Decision (integrator, 2026-11-13). A4 and A6 stand; B2's invariant is narrowed.**

- With a newer bundle on the laptop, `update` means the bundle's release. The owner went back to the older AresOS because the newer one misbehaved, and he installs a new bundle to get past it. Sending him through the release he left first would be the surprising thing. This is owner decision 5 and the council's advice (VERDICT, section 4, point 5).
- The newer installed AresOS stays reachable in two steps: choose its row in the boot menu, then `update` there, which reorders to the newest installed AresOS (rule A4, "on a system chosen in the boot menu").

**What changes in B2.** In states with nothing staged or waiting and no active layout trial:

1. If the bundle's release is installed: each installed system can be made the next start by one command, as written.
2. If the bundle's release is not installed and an AresOS runs first: the same holds for every installed system except an installed AresOS newer than the running one. For that one the model walks the two-step path (a boot-menu choice of its row, then `update`) and asserts that it ends with that system first and confirmed after the restart.
3. In that state the model also asserts what `update` does instead: it stages the bundle's release, and the two lines of rule A6 name the release that is removed at shutdown and the system whose settings the new release starts from.

Nothing else in the brief changes. The report lists this state among the ones where a system is reachable only through the boot menu.
