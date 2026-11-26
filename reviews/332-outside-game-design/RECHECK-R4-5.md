# Recheck 5 of HOME-OUTSIDE.md revision 4

Codex `gpt-6.2-sol` `high`, read-only, on `b9febd1b` (the lead's fix for recheck 4).

`b9febd1b` closes R4-4’s original single-write failure. A future `chosen` can distinguish a whole-file failure from a missing file or an invalid entry. `set_value` can then save `look` and `home = minecraft` in the same atomic `write`. Readers see Minecraft before and after that write. The failed-read boot display and the harm row’s preservation rule also agree with section 6. [aresos-settings:42](os/config/usr/libexec/aresos-settings:42) [HOME-OUTSIDE.md:463](docs/design/HOME-OUTSIDE.md:463)

- **Blocking — [HOME-OUTSIDE.md:473](docs/design/HOME-OUTSIDE.md:473).** Overlapping writes can still split the session. `set look C` can read the failed file, pause, then overwrite a completed switch to Picture with `home = minecraft`. The native home sees Minecraft while the supervisor stays in OFF (`off`). Serialize the settings read, merge and write with the style commit so the fallback is added only if the file still fails at commit time.
- **Blocking — [HOME-OUTSIDE.md:563](docs/design/HOME-OUTSIDE.md:563).** On a fresh failed-read boot, `world on` can enter SETUP while the file is still unreadable. If SETUP fails, the note requires Picture and OFF (`off`), while readers still get Minecraft. Specify that this case preserves the file and returns to OFF (`quit`) with a notice. Add that transition to the table. [HOME-OUTSIDE.md:844](docs/design/HOME-OUTSIDE.md:844)
- **Should-fix — [HOME-OUTSIDE.md:1475](docs/design/HOME-OUTSIDE.md:1475).** Package 12 still leaves the failed-read fixture implicit. Test both an existing home that boots into the world and a fresh laptop that stays in OFF (`quit`), with unchanged bytes before an explicit `set`. Verify that `set look C` leaves the visible style unchanged.
- **Nit — [HOME-OUTSIDE.md:505](docs/design/HOME-OUTSIDE.md:505) and [HOME-OUTSIDE.md:1469](docs/design/HOME-OUTSIDE.md:1469).** The OFF table is in section 6 and the search close order is in section 5. Fix both references.

NOT READY