Reviewed commit `505bc17130b8284c70746e0ca17a0f292162ab61`; read-only review of `aeb82bec..HEAD`. No files changed; no builds, tests or project programs run.

| Point | Status | Reason |
|---|---|---|
| 1. All `/aresos app` branches host-only | CLOSED | `AppCommands.java:31` puts `allowed` on the `app` literal; execution-time checks remain. Console and command-block sources fail before `execute as` changes the executing entity. Tests cover console impersonation, guests, unchanged membership/pins/names/nodes, and successful host commands. Function compilation is covered below. |
| 2. Merge hook respects its installation parent | CLOSED | `OwnedNodes.java:122` checks parent identity before removal. The shared-parent test preserves root `/open` and verifies `/open discord` still launches. Bare `/open` acquiring the other command is the documented unusual-mod limit, not another FIX under the stated bar. |
| 3. Downgrade instructions | CLOSED | `REPORT.md:104` explicitly says restoration undoes **everything since migration**, including My apps and pins, and instructs preserving the current file first. |
| 4. Permission probe and function sources | CLOSED | `functionsCannotHoldHostCommands` uses the server’s compilation permissions, integrated `GAMEMASTER`, and dedicated levels 0–4 through `deserializePermission`, then `createCompilationContext`. It exercises plain compilation and macro instantiation, with positive controls. The comment/report distinguish the predicate from the game’s callers and disclose that actual integrated datapack loading was not tested. No real alternative serverless `NO_PERMISSIONS` path was identified. |
| 5. Ownership cleanup | CLOSED | `forget` selects records by recorded root identity. Refresh forgets the previous dispatcher after replacement; stopping forgets that server’s tracked/current trees. Normal reload creates a distinct tree, whose records remain intact. Live roots keep their nodes reachable; weak references do not prematurely erase ownership. The reload test checks both old-record removal and new ownership. |
| 6. Round-one regressions | OK | Recursive snapshots still check command, requirement, child identity and descendants. Clicks still use IDs; absence filtering and failed-save reconciliation/retry remain intact. No regression found in the scoped changes. There are no `mod/` changes after the report’s tested `68b2869e`. |

**New finding — NIT: the report overstates checks completed during the deliberately failing run.**

`reviews/35-slash-names/REPORT.md:134`, referring to `mod/src/gametest/java/dev/aresos/test/SlashNamesGameTests.java:503`.

With the `app` requirement removed, the first permission context’s first command, `aresos app remove discord`, compiles. The assertion throws immediately. Its macro check, subsequent command lines, subsequent permission contexts and final probe controls are therefore not reached. The statement that “Point 4’s other lines and all controls passed in that run” cannot follow from this test.

Attribute those later checks to the reported successful fixed-code run instead. This affects evidence accuracy; it demonstrates no command or data harm and does not meet the FIX bar.

**Known limits and verification boundaries**

- **Shared-node mutation — documented at `REPORT.md:128`.** A mod deliberately sharing AresOS’s `/open` node and registering into it can change bare `/open`; the original host requirement remains, and `/open <name>` still works in the tested scenario. Content ownership then treats the changed node as foreign until a fresh registration on reload/world start. This fits the expressly accepted unusual-mod limit.
- **Probe exception — documented at `REPORT.md:120–126`.** The predicate accepts any serverless source holding the exact `NO_PERMISSIONS` singleton; it does not authenticate probe provenance. The report’s vanilla caller inventory comes from the builder’s bytecode inspection, which this review did not independently repeat.
- **Verification gaps — documented at `REPORT.md:140–141`.** Garbage collection, server-stop cleanup and actual integrated-server datapack loading were not tested. The reported passing build/client runs are builder evidence, not reviewer reruns.

VERDICT: SAFE with documented known limits