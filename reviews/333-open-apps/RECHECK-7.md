# Recheck 7 of package 333

Codex `gpt-6.2-sol` `high`, read-only, on `5a6bfb9b` (the native click-to-look test fix after the merge with main). Its two nits are in REPORT.md's Known limits.

The timing diagnosis holds. Labwc locked the pointer before forwarding motion. At the second sample Minecraft had accumulated 152.12 units with yaw unchanged. At the next sample it had consumed that motion and turned 22.82° while still captured. The trace points to an early read. I checked the existing logs and code without rerunning the suite. [REPORT.md](reviews/333-open-apps/REPORT.md:24)

The revised test still requires a yaw change greater than 1° and a captured pointer. Zero turn fails. Stillness is timed from the final injected move, and the original click position, second output, and key-start restore checks still run. The six-argument `PointerRulesTest` expectations match the production call, and all three comment edits describe the implemented routing. [Native test](mod/src/gametest/java/dev/aresos/test/ClickToLookClientGameTest.java:244), [PointerRulesTest.java](mod/src/test/java/dev/aresos/focus/PointerRulesTest.java:36)

- **Nit.** Fresh motion can supply the turn if the original batch refreshes the stillness timer but its camera delta is lost. Poll for the original batch to take effect, sampling yaw and capture in the same client call. [ClickToLookClientGameTest.java](mod/src/gametest/java/dev/aresos/test/ClickToLookClientGameTest.java:244)
- **Nit.** Three seconds limits when a retry can start. An in-flight socket read or client wait can overrun it, and a late turn can pass. Describe it as a retry-start deadline, or bound the calls and check the deadline when accepting the sample. [Retry loop](mod/src/gametest/java/dev/aresos/test/ClickToLookClientGameTest.java:247), [Socket read](mod/src/gametest/java/dev/aresos/test/WorldKeepsPointerClientGameTest.java:748)

SAFE