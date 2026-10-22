Reviewed commit `ef07dbc`. The retained evidence supports the published digest, Homebrew denial, tty3 authentication, partition comparison, and exact stock rollback. I found these gaps:

1. **Should-fix — Reboot blocks bypass their inspection checkpoint.**  
   [docs/INSTALL.md:175](/C:/Users/pab/AresOS-06-image-release/docs/INSTALL.md:175), also line 193. Both blocks contain the transaction, status output, and unconditional reboot. Pasting a block into the instructed interactive root shell reboots even if `bootc switch` or `bootc rollback` fails. It also prevents inspecting the staged digest as instructed immediately afterward.  
   **Fix:** separate transaction/status from reboot, put the required checks between them, and make transaction failure stop execution. Qualify the owner-facing sequence.

2. **Should-fix — GRUB recovery omits making stock the persistent default.**  
   [docs/INSTALL.md:201](/C:/Users/pab/AresOS-06-image-release/docs/INSTALL.md:201). Selecting the previous deployment recovers that boot; it does not complete rollback. The next unattended boot can return to broken AresOS. [Bazzite explicitly requires a subsequent step to make the recovered deployment primary](https://docs.bazzite.gg/Installing_and_Managing_Software/Updates_Rollbacks_and_Rebasing/rolling_back_system_updates/).  
   **Fix:** document and qualify an identity-checked operation that makes the recovered stock deployment default, followed by another reboot confirming it stays selected. Account for already being booted into stock.

3. **Should-fix — Several negative checks silently fail to enforce their assertions.**  
   [os/release/switch.sh:4](/C:/Users/pab/AresOS-06-image-release/os/release/switch.sh:4), [os/ci/switch_vm.py:347](/C:/Users/pab/AresOS-06-image-release/os/ci/switch_vm.py:347), and the reused checks in [os/tests/guest.sh:16](/C:/Users/pab/AresOS-06-image-release/os/tests/guest.sh:16). Bash exempts commands prefixed with `!` from `set -e`. For example, an existing `ares` at another UID does not stop `switch.sh` when UID 1001 is free. The competing-desktop process checks likewise continue when their prohibited processes exist. I reproduced this behavior with `set -e; ! true; echo …`, which continued successfully.  
   **Fix:** use explicit `if …; then …; exit 1; fi` assertions and regressions that inject each prohibited condition.

4. **Should-fix — Rollback graphical evidence is still missing.**  
   [os/ci/switch_vm.py:406](/C:/Users/pab/AresOS-06-image-release/os/ci/switch_vm.py:406). The rollback check requires an active display-manager service, then immediately captures the framebuffer. The retained [rollback screenshot](/C:/Users/pab/AresOS-06-image-release/reviews/06-image-release/screenshots/06c-full-2-rollback-bazzite.png) is black apart from the cursor. The backend rollback is supported, but brief 06’s screenshot requirement is unmet; an active service alone does not prove a usable greeter. The report acknowledges this limitation.  
   **Fix:** wait for graphical readiness, capture and inspect the stock greeter, and require that evidence before marking this acceptance item complete.

5. **Should-fix — Returning to the daily desktop leaves recovery administration logged in.**  
   [docs/INSTALL.md:183](/C:/Users/pab/AresOS-06-image-release/docs/INSTALL.md:183). The owner authenticates on tty3, primes sudo, and is then told how to return to labwc without logging out. Switching back to tty3 exposes the authenticated administrator session; maintenance may also leave a root shell there.  
   **Fix:** instruct the owner to exit any root shell, log out of `ares-recovery`, confirm the login prompt, and only then return to tty1.

6. **Nit — Current documentation contradicts the qualification result.**  
   [docs/design/OS-BASE.md:140](/C:/Users/pab/AresOS-06-image-release/docs/design/OS-BASE.md:140) still says recovery and rollback are untested; [os/README.md:77](/C:/Users/pab/AresOS-06-image-release/os/README.md:77) says the final run never reached tty3 assertions.  
   **Fix:** update these statements to the 06c result while preserving the separate physical-install gates.

No VM or hardware tests were rerun. The single-disk evidence does not establish zero writes to Micron; that qualification correctly remains an open release gate.

CHANGES-NEEDED