Reviewed head `08753aeb` against `origin/main`, including the contracts, tests, report and headless evidence. Read-only: I ran no tests and opened no application windows.

1. **Blocking — Lunar’s window ownership fails during ordinary multitasking.**  
   [aresos-shell:2182](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:2182) permits unknown-window association only when one discovered program remains and **no unresolved registry launch exists**. “Unresolved” includes a successfully opened Chrome or Terminal window. A resident Discord scope also blocks association.

   Consequently, Lunar’s already-visible Java window can remain unowned. Closing its launcher shortly after game activation schedules a hub return while the game remains open. If the handoff interval has elapsed, closing the unowned game later cannot trigger Lunar’s return instead.

   The inverse also fails: a sole resident Discord scope can claim an unrelated, newly opened window indefinitely—even after Discord’s launch is marked closed.

   **Fix:** establish ownership using trustworthy window/process association, or a verified application-specific identity rule; global scope count is insufficient. Add tests combining Lunar with an open registry app, a closed-but-resident discovered app, and unrelated windows. The existing ambiguity tests stop before checking closure consequences; the byte-split tests keep time fixed. I disagree that the report’s provenance/timing PLAN-GAP is resolved by the grace period.

2. **Should-fix — discovery changes window behavior for 1.0 clients.**  
   [aresos-shell:1618](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1618), [2234](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:2234).

   Window ownership always uses the complete catalogue, regardless of negotiated minor. With a 1.0 client, launch Firefox manually from Terminal, then close Firefox while Terminal remains open. Previously Firefox was unowned and the helper preserved the compositor’s choice; now it is a discovered app and can force a return to the hub.

   **Fix:** preserve registry-only ownership/return behavior for 1.0 sessions, including reconnect handling. Test production catalogue construction with a 1.0 connection; the original lifecycle fixtures inject only the registry and therefore miss this regression.

3. **Should-fix — the 1.0 discovered-ID refusal changes the response and replay semantics.**  
   [aresos-shell:1926](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1926).

   Previously an unknown `open_app` produced a journaled failed launch response containing `request_id`, `launch_id: null`, `app_id` and `state: failed`. A discovered ID requested by a 1.0 client now raises a generic `Failure`, omitting those fields and bypassing journaling. The compatibility tests check only `error == unknown_app`.

   **Fix:** preserve the old failed-launch response and duplicate-request behavior while refusing discovery access. Compare complete responses and replay behavior against the baseline.

4. **Should-fix — delayed closure can still steal focus after a deliberate switch.**  
   [aresos-shell:2262](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:2262).

   Pending `should_return` survives every activation except the desktop. Close discovered app A, let the compositor activate B, then deliberately switch to C during the grace period: expiry activates the hub over C. The added regression test explicitly visits the desktop first, which clears the flag and avoids this remaining case.

   **Fix:** cancel obsolete return intent after a subsequent deliberate launch/switch, while retaining the immediate compositor handoff behavior. Add the A-close → B-refocus → C-switch sequence without an intervening desktop activation.

5. **Should-fix — valid Flatpak export icons are deliberately discarded.**  
   [aresos-shell:777](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:777).

   Lookup resolves symlinks and requires the target to remain beneath `exports/share/icons`. Normal Flatpak export links point into the application deployment outside that directory, so installed pictures can remain absent forever. The report acknowledges this; it is a functional omission for a major supported source, rather than merely a corrupt-image fallback.

   **Fix:** support validated Flatpak export-to-deployment links, retain bounded regular-file reads and sandboxed conversion, and test a realistic export layout. I disagree with this part of the sandbox judgment call; requiring the sandbox itself is reasonable.

6. **Should-fix — Flatpak marker handling also rewrites ordinary programs’ arguments.**  
   [aresos-shell:402](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:402), [578](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:578).

   Every discovered command enables forwarding parsing. A valid ordinary command such as `Exec=/usr/bin/tool @@` is rejected, while `tool @@ %f @@` loses its literal arguments. `@` has no special meaning in the [Desktop Entry Exec grammar](https://specifications.freedesktop.org/desktop-entry/latest/exec-variables.html).

   **Fix:** apply marker removal only to a recognized Flatpak file-forwarding invocation. Add non-Flatpak literal-marker tests alongside the real exported fixtures.

7. **Should-fix — missing `X-Flatpak` produces invented application metadata.**  
   [aresos-shell:597](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:597).

   Without `X-Flatpak`, `exec_name` becomes the desktop filename stem, not the application ID in `flatpak run`. For `my-firefox.desktop` running `org.mozilla.firefox`, the helper reports `my-firefox` and omits `org.mozilla.firefox` from candidate identities. The test uses matching filename/application IDs, masking both errors.

   **Fix:** extract the application ID from a recognized Flatpak invocation and use it consistently for metadata and identity candidates. If it cannot be determined, omit the optional metadata instead of inventing it.

The original test-file diff changes only the future-minor negotiation assertions: envelope, selected minor and advertised capabilities. Those changes are justified and do not weaken existing lifecycle assertions. The three shipped launch definitions retain their commands and window policies; the mandated GPU-variable removal is implemented, and the NVIDIA constants and driver check match the supervisor.

I found no additional discrepancy in directory precedence, visibility filtering, ID normalization, starter replacement metadata, capability negotiation, paging byte accounting, revision handling or event gating. The shared examples are exercised, although the gaps above show why matching their shapes is insufficient.

The headless screenshots and transcript support native KCalc and Foot/btop launching, matching and closure. They do **not** establish normal Flatpak launching, resident reopening or Lunar handover. The report states those limits accurately. The additive image checks establish converter/coder presence, not successful sandboxed conversion inside the built image; the separate local converter checks provide that narrower evidence.

For the remaining report decisions: deterministic collision ordering, icon precedence, conversion limits, polling/cursors, version-assertion updates and HUB 3.8 authority are reasonable. The hosted-suite restriction and isolated KCalc workaround are also reasonable, with the stated evidence limits. Footclient remaining distinct, locale/action exclusions, unavailable identities, bounded handover waits, cache retention and same-user impersonation limits are disclosed; I found no separate blocker in those choices. The unknown-window rule, close-delay claim and legitimate-icon rejection need the changes above.

CHANGES-NEEDED