No findings in the 07d-only diff, `6a640fb..d798f6f`.

The fix restricts executable aliases to the three normalized Windows Notepad paths while retaining the Store identity and launch-modifier guards. I found no new duplicate, drop, or ID-change path in the touched logic.

The regression’s [before-fix XML](reviews/07-real-apps/07d-before-fix.xml) records the Tools executable being swallowed: expected two entries, got one. The same test [passes afterward](reviews/07-real-apps/07d-after-fix.xml), checking both discovery orders, owner fields, unknown JSON fields, and stable IDs after reload and rediscovery.

Both raw full-run logs show successful `build runClientGameTest` runs: 40 unit tests, 16 server tests, and six client entrypoints. Existing assertions remain intact; the native fixture now targets an allowed Windows path. HEAD’s `mod/` files match tested commit `0926389`.

Tests were not rerun during this read-only review.

SAFE