# Package 56 independent review

Reviewer: fresh Codex `gpt-6-astra`, `high`, read-only. No builds or game clients were started by the reviewer.

Initial implementation reviewed: `58ad5a7c` against the brief and hub design.

**Should-fix:** `HomePointer.button` could retain a swallowed-release bit when the release went to the newly focused app. After returning to the world, the next ordinary press reached vanilla but its release was swallowed. This could leave attack/use held, including continued breaking in Build.

**Resolution reviewed:** `58ad5a7c..074ffc19`, limited to that finding and the touched code. Every new press clears stale suppression for its button before deciding whether the new click is swallowed. A newly swallowed press still suppresses its own release. The regression omits the old release, returns focus, and verifies a normal press/release for left, right and middle, including action and raw button state. The supplied targeted native-session run passed.

The reviewer found no additional required code changes in the initial review or the scoped fix review. Full final build/client validation remains the builder's responsibility and is recorded in [REPORT.md](REPORT.md).

**Additional fixture correction reviewed:** `074ffc19..3d287df0`, limited to native test coordinates. Both forwarding and pointer targeting query GLFW's current window size, and the fixture restores/asserts desktop maximization before opening apps. The reviewer inspected the compositor screenshot showing the arrow on the highlighted terminal slot, and the targeted run's `BUILD SUCCESSFUL in 56s`. Production code was unchanged. No findings.

**Startup delivery reviewed:** the ordinary preview exposed the helper's missing initial focus and late client subscription/loading gaps. The scoped startup review found a reconnect variant: retry handshakes remained UNAVAILABLE and frames could clear newly delivered focus. The reviewed correction marks every attempt STARTING, queues a reset on genuine loss, preserves ordered handshake focus, and adds a delayed reconnect-list regression. The reviewer marked that fix SAFE. The immediate-release guard refinement was also reviewed: releasing an existing capture before cancelling grab introduces no recursion and leaves normal capture unchanged. No further findings.

These startup fixes and their tests were committed as `81b1018e`; final full validation is recorded in the report.

SAFE
