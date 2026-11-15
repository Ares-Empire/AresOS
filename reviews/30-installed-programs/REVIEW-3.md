Reviewed commit `0156d72719111652c0a4e3f6de34142b14e3b7c7`; read-only review of `1467f68f..HEAD` and the uncommitted report update. No files changed; no helper, tests or builds run.

| Point | Status | Reason |
|---|---|---|
| 1. Discovered returns under 1.0 | CLOSED | Downgrade cancels pending return intent; expiry additionally requires minor 1. Registry-only ownership prevents new discovered closures from forcing returns under 1.0. |
| 2. Current activation before expiry | CLOSED | Activation-based cancellation now precedes discovered-return expiry. The new test covers a switch received after the deadline, before execution. |
| 3. Ownership precedence | CLOSED | Desktop and registry identities precede reviewed exact hints, prefixes, and discovered candidates. `apply_hints` removes competing candidates covered by another program’s prefix. Tests include Steam’s launcher/game closure consequences. |
| 4. Registry unowned-window protection | CLOSED | The common registry closure path checks unowned windows under 1.1. Minor 0 retains the old immediate-return condition. |
| 5. Previous report nits | CLOSED | The blanket mutation claim is removed, regression tests and controls are distinguished, and both the permanently closed late Lunar launch and another launcher’s Minecraft attribution are explained. Additional documentation nits follow. |
| 6. Image-check cleanup | OK | The sole change adds `rm -rf /tmp/pkg31-home` immediately after package 31’s `gsettings` call. |
| 7. Compatibility and mod scope | OK | Legacy response shapes, discovered-ID refusal/replay and registry window behavior remain intact. The brief intentionally introduces cached availability and bounded launch-check failures, so availability timing is not literally identical. No `mod/` files changed; contract examples are unchanged. |
| 8. Other helper regressions | OK | No additional FIX or SHOULD finding established under this round’s bar. Availability checks move off-loop, SVG parsing runs under the child’s limits, and launch arguments and journal-before-spawn ordering remain intact. Two accepted-limit scenarios need documentation. |

These conclusions are from source inspection, not confirmation of the reported test or mutation runs. `HOSTED-RESULTS` is not a finding.

1. **NIT — document a rapid new launch whose check outlasts the pending return.**

   **Where:** [aresos-shell:2759](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:2759), [aresos-shell:2822](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:2822); [REPORT.md:514](/var/home/ares/AresOS-30-installed-programs/reviews/30-installed-programs/REPORT.md:514).

   **Scenario:** Lunar closes at `t=0`, leaving Terminal active and a return pending. At `t=0.1`, the owner chooses another program whose executable check takes one second. The request enters `checking`, but cancellation happens only after the program starts. A tick after `t=0.5`, before that check completes, can therefore pull the hub over Terminal; the requested program starts afterwards.

   This needs a new program choice inside the half-second interval, so it belongs to the accepted timing limits rather than another fix round. The report describes delayed checks and cancellation at launch start separately, but does not state this visible consequence under **“Known limits (review fixes 2), with what he would see.”** Add it there.

2. **NIT — document cumulative serving-loop waits from an authenticated request flood.**

   **Where:** [aresos-shell:2757](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:2757), [aresos-shell:2519](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:2519); [REPORT.md:514](/var/home/ares/AresOS-30-installed-programs/reviews/30-installed-programs/REPORT.md:514).

   **Scenario:** An already-running hostile owner process authenticates and sends 100 `open_app` requests with distinct IDs for one program whose check is stuck. They share one check thread, but each request still waits `CHECK_WAIT` on the serving loop. Processing that batch takes roughly 20 seconds before returning to timer, heartbeat and compositor processing; the three-second check deadline is not enforced during the batch.

   The owner would see an unresponsive launcher and delayed focus handling. Because this requires the already-running hostile owner process explicitly excluded by the round’s bar, it is a documentation NIT, not a FIX. Record that the four-thread limit does not bound cumulative waits per incoming batch.

VERDICT: SAFE with documented known limits