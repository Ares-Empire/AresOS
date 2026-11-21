BLOCKED

Rechecked `354f1b61eaf6f345411773d5c411d0223fa1a365`. No files changed.

**Prior Codex blockers**

1. **False “nothing to save” — Resolved.** Loading, adoption, a dead helper, and `server_stopping` followed by `no_world` no longer establish a successful save. `briefs/25-guardian.md:103–111,251–255`
2. **Flush mistaken for a clean close — Resolved.** Save confirmation and JVM exit are separate outcomes. Three real-game SIGTERM-only trials are a merge gate. `briefs/25-guardian.md:112–121,274–279`
3. **Guard ordering — Resolved in the design.** The guard must be active before JVM authorization, and the VM must prove the installed teardown order. The final-commit verification gap is below. `briefs/25-guardian.md:146–155,280–296`
4. **Missing supervisor can erase the warning — Still blocking.** A request can spend 70 seconds waiting before a further 10-second recovery attempt, while systemd allows 75 seconds total. An explicit record-write failure also bypasses the no-answer fallback. The current lock probe returns false on open errors, so it cannot establish that no writer exists. Reserve fallback time, cover explicit write failures, and require positive evidence of no writer or hand-off before returning success. `briefs/25-guardian.md:96–102,156–163` `os/config/usr/libexec/aresos-desktop:2006–2018`
5. **Deadline and launch admission — Partly resolved, still blocking.** Replies, cleanup and joined requests are bounded. The launch record can close when Java exits, before labwc exits. A replacement supervisor can then miss the logout and start another launch. Keep a session-bound admission block through teardown, including a logout with no JVM. `briefs/25-guardian.md:86–100,129–142` `os/config/usr/libexec/aresos-desktop:1199–1217`
6. **Logout compositor identity — Resolved.** Logout uses the validated pidfd and waits for labwc to exit within the deadline. `briefs/25-guardian.md:166–182`
7. **Unsaved app work behind black — Partly resolved.** The brief gates logout and restores visibility on failure. Native power-off can still discard app work, an existing exposure the brief explicitly defers. The new stale-count issue is below. `briefs/25-guardian.md:179–200,308–316`
8. **World identity and folder moves — Resolved.** Replies are bound to the validated active world and connection. Moves require recorded provenance, the desktop lock and a no-clobber rename. `briefs/25-guardian.md:67–74,204–220`
9. **VM latch and credential exposure — Resolved in the brief.** It requires recovery through `retry`, an accepted lifecycle hello, allowlisted evidence, and view-token isolation. `briefs/25-guardian.md:280–286,334–339`

**Prior Claude blockers**

- **B1 — Resolved.** Tests use a clean environment and private runtime, and logout checks the compositor’s runtime before signalling. `briefs/25-guardian.md:166–182,320–328`
- **B2 — Resolved.** The rig gives the JVM the private runtime and checks the process environment before issuing `save`. `briefs/25-guardian.md:268–273`
- **B3 — Resolved.** Adoption gets the same bounded hello retry and unconfirmed-save handling as any other launch. `briefs/25-guardian.md:103–111,251–255`
- **B4 — Resolved.** An arriving op joins the stop, shutdown intent makes it uncancellable, and callers get the shared result. `briefs/25-guardian.md:129–136`

**New blockers introduced by the revision**

- **Logout can succeed without logging out.** With no JVM, there is no status 143 to satisfy the new `exited` condition, yet the command allows exit 0 when nothing is running. Explicitly let a confirmed no-writer logout proceed to signal labwc and verify its exit. `briefs/25-guardian.md:103–116,174–182`
- **The logout app check can go stale.** An app can open during the save, or the helper can die after reporting zero. The brief only checks at entry, so logout can still close an app with unsaved work behind black. Invalidate the count on tracking loss, remove black when apps appear, and require a fresh zero before signalling labwc. `briefs/25-guardian.md:179–197` `os/config/usr/libexec/aresos-desktop:1390–1405`
- **The VM fixture can skip saving entirely.** Provisioning creates an empty worlds directory, and the specified JVM stand-in creates no world. Section 2.4 then takes the “nothing to save” path in both boots. Seed a disposable world folder and assert that each fixture received the save request. `briefs/25-guardian.md:103–105,280–296` `os/config/usr/libexec/aresos-desktop:435–445`
- **The hung-shutdown gate can pass with the old scope timeout.** Section 3.1 still allows about 165 seconds, while the final instruction requires a 15-second game-scope timeout and only prints it. Assert the effective timeout and give Boot 2 a consistent power-off bound. `briefs/25-guardian.md:161–163,294–296,344–346`
- **Step 8 can leave the release gate proved on stale code.** It can change the guard or VM after the lead’s run and ends with `checks_only`, which boots no VM. Require a passing check build on the final relevant sources after any such fix. `briefs/25-guardian.md:243–247,280,297–298` `.github/workflows/os-image.yml:20–23`