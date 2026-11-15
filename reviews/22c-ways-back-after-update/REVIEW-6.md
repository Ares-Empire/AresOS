Reviewed PR #46 at `1e0f67da`, limited to `git diff 3bfdfbcd..HEAD`. **No blocking, should-fix or nit findings remain in these fixes.**

1. **The connected forward-again sequence is fixed.** With R28 tools but only R27, R13 and stock installed, returning from stock selects R27; subsequent `previous` selects R13. The [forward-again box](/var/home/ares/AresOS-22c-review/docs/INSTALL.md:323) then requires boot-menu R27 before running `update`. R27 runs while R13 remains default, so [the code](/var/home/ares/AresOS-22c-review/os/owner-tools/owner.py:1708) takes the installed-system reorder branch. After the final restart, R27 runs and starts next; R28 was never staged and R27 was never removed.

   Other entries are safe: stock and nondefault starts use the reorder branch; already-default newer AresOS completes without updating; unnamed states and refusals lead to Help. An independent trace across all 750 destination states found 547 completing on the newest installed system without staging, 63 already there, and 140 stopping at Help.

2. **Both failed-update-card entry paths are fixed.** [The card](/var/home/ares/AresOS-22c-review/docs/EMERGENCY.md:20) preserves the result when entered immediately after a check. Otherwise it runs check once. This matches [the code](/var/home/ares/AresOS-22c-review/os/owner-tools/owner.py:1270), which archives the unapplied operation when reporting it. In review 5’s failed-finalization case, R13 returns to default R27 without `previous`. If that evidence was already consumed, the unnamed-result branch stops at Help.

**The extra restart is an acceptable judgment call within this brief.** Neither check nor title identifies the tools’ target release, so their output cannot justify the shorter path reliably. Booting the newer installed system first establishes a condition under which update cannot stage.

**The boot-menu choice is unambiguous.** The box uses the current check’s `Boot menu at the next start:` map and the `(ostree:N)` associated with newer AresOS. In the connected sequence that is `(ostree:1)`. It does not ask the owner to distinguish three otherwise identical Bazzite labels. The changed output patterns agree with the code at this head.

**These fixes settle the two reported sequences, but the underlying recovery interface remains fragile.** `update` still means either install the tools’ release or select the newest installed system, depending on state. That will keep creating opportunities for similar guide mistakes. A dedicated installed-only return command, guaranteed never to stage, with staging reserved for a separate explicit operation, would remove this class. Merely displaying the tools’ release would improve the guide’s gate without removing the overloaded behavior.

Verification: four selected regression tests passed; a fifth stopped during temporary-directory creation on the read-only filesystem, before owner dispatch. The independent 750-state trace passed; all 255 host-walk and 35 pending-rebind hashes matched; diff whitespace checks passed. No files changed, no prohibited commands ran, and no VM or physical boot validation was performed.

SAFE