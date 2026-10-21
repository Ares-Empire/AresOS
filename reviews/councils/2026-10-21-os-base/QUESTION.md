# Council: OS base design (2026-10-21)

**Under review:** `docs/design/OS-BASE.md` (PR #2, branch `pkg/02-os-base-design`).

**Also read:** `README.md` (vision and design), `AGENTS.md` (project rules), `briefs/02-os-base-design.md` (what the design was asked to answer). Check external claims against sources where it matters.

**Context:**
- AresOS is a one-person hobby project by a student, built mostly by Codex agents with Claude orchestrating.
- The goal is a real OS on the owner's Lenovo LOQ 15IRH8 that boots straight into their Minecraft world, with the Fabric shell mod as the whole desktop.
- Windows must stay safe on its own SSD.
- Codex budget is generous until 2026-11-21. The owner's own time is limited.

**Decision that depends on this:**
- The owner picks the Linux base and approves the phase 2 package order (P1–P12).
- The owner answers the five "Owner decisions" in the document.

**Questions for the council:**
1. **Base choice.** The design picks Ubuntu 26.04 with an install recipe, mainly to keep Secure Boot working with no new keys. It gives up atomic whole-OS updates and rollback.
   - Is that the right trade?
   - How do Fedora Atomic / bootc images (including community images that ship signed NVIDIA drivers with a one-time MOK key enrollment) or NixOS compare for this owner? Their main appeal: the whole OS is code, with rollback.
   - Does a one-time MOK enrollment actually risk Windows or BitLocker? Verify rather than assume.
2. **Silent failures.** What in this design would look fine but be wrong in practice: tests green, the owner surprised later?
3. **Proportionality.** Is the plan right-sized for a hobby project?
   - What is the shortest safe path to the first "I pressed F12 and spawned in my Nether world" moment?
   - What can be cut, merged or deferred without risking Windows or the world save?
4. **Safety.** Anything that could touch the Windows SSD, trigger a BitLocker recovery prompt, lose the world save, or lock the owner out of their laptop?
5. **Experience.** Will labwc + Prism + the session helper deliver "Minecraft is the desktop": opening an app on top, closing it, and being back in the world? What will annoy the owner daily?

**Output:** follow `docs/REVIEW.md` (councils). For every finding give the gap in one line, a concrete scenario, the impact, the fix, and the check that would catch it. Most severe first.
