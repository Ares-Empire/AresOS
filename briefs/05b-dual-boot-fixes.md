# 05b: Dual-boot guide, council fixes

Follow-up on branch `pkg/05-dual-boot` (PR #5). Read `reviews/councils/2026-10-21-dual-boot/VERDICT.md` and both member files first.

**Goal:** resolve all 4 blocking and 3 non-blocking council findings, and make the guide the council's **minimal safe version**: safe, and something a non-expert actually follows without skipping steps.

**In scope:**
1. **Undo verifies Windows' real boot target (blocking 1).** Before deleting anything, map the Windows boot entry that was actually tested to the original Windows ESP's partition GUID and Microsoft loader path. Stop if it points at AresOS storage or can't be established.
2. **Partition identification that a novice can complete (blocking 2).**
   - The inventory is mandatory.
   - Give exact read-only commands for Windows and for the Linux side.
   - Provide one comparison sheet (disk identity, `Guid` ↔ `PARTUUID`, device paths, boundaries) with endpoints computed for the owner.
   - Explain why Disk Management doesn't show the MSR.
3. **Two USB sticks (blocking 3).** A labelled Windows recovery USB that is preserved and never overwritten, made with a concrete German procedure (Wiederherstellungslaufwerk), plus a separate expendable installer USB. Say what size each needs, and how to confirm the recovery USB boots before shrinking.
4. **Correct installer partition and subvolume steps (blocking 4).** Separate creating the partitions from creating the Btrfs subvolumes. Show the expected resulting tree, mount points and pending operations. Say which installer language and keyboard settings make the labels match the guide.
5. **Evaluate the simpler route.** If Bazzite's current (non-legacy) installer can install automatically into free space alongside Windows, compare it honestly with manual partitioning:
   - Does it create its own ESP or share Windows' ESP?
   - What does undo look like?
   - Which steps disappear for the owner?

   Recommend one route. If shared-ESP is the simpler route, say exactly what it writes to the Windows ESP and how undo removes it. It must never modify `\EFI\Microsoft`.
6. **Non-blocking 5–7:**
   - One rehearsed ISO-writing method, with no GParted batch-file route.
   - Lenovo LOQ firmware steps to restore Windows as the default.
   - One primary path for Fast Startup and hibernation, with the GUI as optional.
7. **Followability:** move maintainer research out of the owner's action sequence. Where upstream docs have screenshots of the installer screens, link them at the exact step. Keep the guide as short as safety allows.

**Out of scope:** doing any of it, touching disks, and the image/rebase handoff (that's the OS image package).

**Acceptance:**
- Updated `docs/INSTALL.md` and design, plus `reviews/councils/2026-10-21-dual-boot/CHANGES.md` mapping each of the 7 findings to its fix.
- New external facts have dated sources.
- Pushed on the branch.

**If unsure:** pick the option that leaves Windows' partitions and `\EFI\Microsoft` untouched and is easiest for a novice to undo.

**Model:** gpt-6-astra, xhigh.
