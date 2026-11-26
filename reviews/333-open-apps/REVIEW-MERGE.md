# Review of the merge of main into PR150 (merge commit 84a268b2)

A fresh Claude Opus agent, read-only, on 2026-11-23. The lead resolved three conflict blocks by hand when main gained package 328 (PR166): `PointerRules.click`, `HomePointer.button`, and the client test list.

**Verdict: SAFE.**

- **The combined click rule** gives exactly 333's results when `worldActs` is false, and exactly 328c's when `secondary` and `canActivate` are false. When both apply, the order is: not free gives VANILLA; a primary click on an app slot opens the app; a secondary click on an app slot with `canActivate` opens a new window, also in edge mode; otherwise `worldActs` gives VANILLA, and false gives ENTER_WORLD.
- **`HomePointer.button`:** no press is swallowed twice or lost. A VANILLA press and its release reach Minecraft. OPEN_APP and NEW_WINDOW launch with the right new-window flag. ENTER_WORLD calls `enterWorld(client, true)`.
- **Nothing from either side was lost:** every other `mod/` file is a clean union.
- **The test list** holds 33 client tests, each once. 333's test is last.
- **The one failed native ClickToLook run** (the camera turned 0° while the mouse was captured, with no focus events) is very unlikely to come from the merge, which doesn't touch that path. It points to the rig's timing; the test's own comment records an earlier flake at the same step. The rerun passed.

**Known limits / nits, for a follow-up:**
- No unit test calls the 6-argument rule with `worldActs` true and a secondary click (expect NEW_WINDOW with `canActivate`, VANILLA without it), and no game test right-clicks an app slot under `look = edge`.
- Three comments describe only the primary click: `EdgeLook.java:23-25`, `HomePointer.java:38`, `PointerRules.java:24-27`.
- Four `click` versions (3, 4, 5 and 6 booleans) are easy to call wrongly. Tests could use the 6-argument form, and the 4- and 5-argument versions could go.
- Pre-existing in 328c: in edge mode, a right click on an app slot with a helper that can't activate apps goes to Minecraft's "use" at the crosshair.
