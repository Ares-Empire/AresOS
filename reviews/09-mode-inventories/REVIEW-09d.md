No findings in 09d through `d160b64`.

- The original pickup-loss finding is fixed. Tests committed before the fix failed with **12 emeralds becoming 5**, including after timeout/reconnect; both now pass.
- Checked ordinary/indexed insertion, returned stacks, hopper transfers, XP/mending, commands, equipment setters and in-place edits. Transfers preserve their source, drop safely, or retain the changed destination through rollback. No remaining loss, duplication or permanent-lock regression found within scope.
- Local logs corroborate two full `build runClientGameTest --rerun-tasks` passes on unchanged final sources: 38 server tests, 45 unit tests and all client entrypoints. Existing assertions remain intact.

I did not rerun Gradle in this read-only review.

SAFE