Reviewed commit `154035d`. Two findings:

1. **Blocking — Vanilla mode changes can overwrite the saved Live inventory.**  
   Where: [ModeInventories.java:118](/C:/Users/pab/AresOS-09-mode-inventories/mod/src/main/java/dev/aresos/mode/ModeInventories.java:118).

   Snapshot ownership is inferred solely from the current vanilla game mode. Reproduction: enter Build with G, collect blocks, run `/gamemode survival`, then press G. The command leaves Build’s items equipped; G subsequently saves those items over `before.live`, destroying the original Live inventory. Vanilla commands/F3+F4 bypass the transaction entirely.

   **Fix:** route survival/creative changes through the inventory transaction, or refuse external mode changes in marked worlds. Track which inventory is active independently of vanilla game mode. Add a regression covering this sequence and rejoin.

2. **Blocking — Actions sent before the client receives the swap can affect the newly restored inventory.**  
   Where: [AresOsClient.java:61](/C:/Users/pab/AresOS-09-mode-inventories/mod/src/client/java/dev/aresos/client/AresOsClient.java:61), [ModeInventories.java:132](/C:/Users/pab/AresOS-09-mode-inventories/mod/src/main/java/dev/aresos/mode/ModeInventories.java:132).

   G sends a request without blocking further item interactions or awaiting completion. With delayed server/client processing, press G from Build, then Q while the old Build hotbar is still displayed. The server processes G first, restores Live, then vanilla’s drop handler removes **Live’s selected item**, potentially dropping it into lava. Menu clicks and hand swaps have the same stale-input problem. Running synchronously on the server does not prevent later packets from targeting the replacement inventory.

   **Fix:** introduce an acknowledged switching state that blocks item interactions and additional toggles until the complete destination state—or failure—is received. Add a client test that delays synchronization and attempts drops/clicks during the transition; the existing direct server switch loops miss this.

Build/game tests were not rerun in the read-only review environment.

CHANGES-NEEDED