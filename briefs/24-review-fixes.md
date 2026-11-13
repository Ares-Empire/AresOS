# 24: review fixes

Follow-up on branch `pkg/24-interface-v1` (PR #33). Brief 24 still applies. Read `reviews/24-interface-v1/REVIEW.md` (CHANGES-NEEDED at `e25c429`, gpt-6-astra high).

Fix every point as the review proposes:

1. **Blocker: malformed requests crash the helper.**
   - Validate types and encodings before any use: a non-string `op`, object/array values where strings are expected, and lone surrogates in strings such as `nonce`.
   - Tests: each malformed case gets a clean error reply, and a valid request on the same connection still works afterwards.
2. **Blocker: restart reconciliation.**
   - Install ownership before enumerating windows.
   - Reconcile every non-terminal launch, including persisted `focused` and `background` ones, against the current windows and scopes, so a launch whose app has closed ends as closed.
   - Test the **production** startup order.
3. **Blocker: focus return across reads.**
   - Keep the foreground/closure transition state across socket reads; a `recv` is not a compositor batch.
   - Test the same activation-and-closure event stream split at **every** byte boundary, and require the same focus result each time.
4. **Should-fix: journal eviction.**
   - Never lose replay protection for a request ID that may be replayed, and never evict a pending entry. At capacity, reject a new launch with a clear error instead.
   - Test replay after eviction pressure, including across a restart.
5. **Should-fix: blocking writes in the mod.**
   - Writes must not block the timeout/reconnect watchdog: use bounded non-blocking writes or an independent watchdog.
   - Test a peer that stops reading.
6. **Should-fix: degraded tracking hides failures.** Keep tracking a launch after `starting`, so a later `launch_failed` (e.g. `systemd-run` failing) still reaches the player.
7. **Verification:**
   - Two passing full `build runClientGameTest` runs on the final head.
   - The owner is playing Minecraft in Lunar Client: **never** start a client test while Lunar is running (check its `javaw` command line for `lunarclient`), and keep the 6 GB free-RAM check. If Lunar is still running when everything else is done, push and report the client runs as pending; the integrator runs them later.
   - Full WSL suite plain and `-B` at the final head, one full suite at a time, with at least 4 GB free.

Add a "Review fixes" section to the REPORT, then push.
