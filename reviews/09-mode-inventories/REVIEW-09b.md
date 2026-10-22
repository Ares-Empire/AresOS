Reviewed `c9a7159..d52ce12`, excluding binary images. One blocking regression remains.

1. **Blocking — a client without the new receiver can remain locked indefinitely.**  
   **Where:** [ModeInventories.java:133](C:/Users/pab/AresOS-09-mode-inventories/mod/src/main/java/dev/aresos/mode/ModeInventories.java:133), reached through [ExternalModeMixin.java:28](C:/Users/pab/AresOS-09-mode-inventories/mod/src/main/java/dev/aresos/mixin/ExternalModeMixin.java:28).  
   **Why:** external changes route every connected player into `begin()` without checking support for `ModeSwitchStatePayload`. A LAN guest running pre-09b AresOS can receive `/gamemode creative Guest`, have its inventory swapped and `pending` set, but cannot acknowledge the new protocol. The server then rejects its item actions and further switches for the rest of that connection. The tests use the current client or manually acknowledge server fixtures, so they miss this.  
   **Fix:** verify protocol support before beginning or mutating anything; otherwise refuse with a message. Add a regression with an unregistered state channel, asserting unchanged inventory/mode and `pending == false`. Keep the acknowledgement requirement for supported clients.

Both original blockers are otherwise fixed at their source: independent ownership plus setter interception prevents the command overwrite; immediate client locking and server packet guards protect the acknowledged destination. The regression commit and recorded red logs demonstrate both original failures. Delayed synchronization, rollback/retry, replacement, rejoin/restart and retained pin assertions are covered afterward.

I found no additional loss/duplication path in the traced transactions. Local logs corroborate two complete green runs, and `git diff --check c9a7159..HEAD` passed. I did not rerun Gradle in this read-only review.

CHANGES-NEEDED