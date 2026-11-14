Five original findings are **CLOSED**; **#2 and #4 remain OPEN**. The original blocking Lunar/Discord ownership bug is fixed, but two additional ownership issues remain.

Reviewed `ab58d12f`, restricted to the requested diff and its affected behavior. I read the old helper at `5fbe6d20~12`. No tests, applications, or mutation checks were run.

| Original finding | Status | Reason |
|---|---|---|
| 1. Global ownership guess | **CLOSED** | The guess is removed. Lunar’s game has an explicit hint; a resident Discord scope cannot claim unrelated windows. The original Chrome/Lunar failure is fixed. Separate ownership issues are below. |
| 2. Preserve 1.0 window behavior | **OPEN** | Registry-only ownership works, including clearing inherited dialog ownership. However, a pending discovered-app return survives a downgrade to 1.0. |
| 3. Discovered-ID refusal/replay | **CLOSED** | Fresh 1.0 requests use the old journaled unknown-app path. Response fields, duplicate replay, restart replay, and `request_id_reused` behavior match the old helper. Replaying an existing 1.1 launch hides its result without relaunching or overwriting it. |
| 4. Drop obsolete returns | **OPEN** | Switching or launching during the tested interval cancels the return, but expiry runs before processing the current activation. A switch already received can therefore lose to an overdue return. |
| 5. Flatpak export icons | **CLOSED** | Deployment links are admitted, then the actual file is checked through a pinned descriptor before reading. The realistic export-icon fixture exercises the formerly rejected layout. |
| 6. Flatpak markers | **CLOSED** | Ordinary commands retain literal markers. Removal requires recognized `flatpak run` syntax with `--file-forwarding` before the application ID. |
| 7. Flatpak application ID | **CLOSED** | Without `X-Flatpak`, recognized commands supply the ID for metadata and ownership candidates. Ambiguous commands omit `exec_name`; the desktop filename is no longer invented as the Flatpak ID. |

Remaining and new findings:

1. **Should-fix — a pending return survives a 1.0 reconnect.**  
   [hello](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:2436) changes ownership but leaves `discovered_closing` intact.

   At `t=0`, Lunar closes and the compositor activates Terminal, leaving a pending return. At `t=0.1`, a 1.0 client connects. After `t=0.5`, [expiry](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:2863) still activates the hub over Terminal. No unowned window remains to suppress it. The old helper cannot produce this Lunar-triggered return.

   **Fix:** invalidate discovered return intent when downgrading, and ensure discovered closures cannot force returns under minor 0. Add the reconnect-during-pending-return sequence; existing reconnect tests change versions while the discovered window is still open.

2. **Should-fix — expiry precedes cancellation by the current switch.**  
   [Pending-return expiry](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:2863) executes before [activation-based cancellation](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:2886).

   A closes at `t=0`; B takes focus. A tick at `t=0.4` leaves the return pending. At `t=0.55`, C’s activation arrives before the next timer tick. `windows_changed()` already sees C, but activates the hub before considering that switch. The owner briefly chooses C and gets pulled back.

   **Fix:** reconcile the current activation and cancel obsolete intent before executing expired returns. Test an activation arriving after the nominal deadline but before the pending return has executed. The existing tests switch at `HANDOFF / 5`, which misses this ordering.

3. **Should-fix — discovered exact candidates defeat Steam’s reviewed prefix.**  
   [apply_hints](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:884) removes competing candidates only for exact hints. [Windows._owner](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1971) then checks every exact candidate before prefixes.

   A valid discovered entry with `StartupWMClass=steam_app_1086940` owns that window instead of `steam.desktop`. If Steam’s launcher closes shortly after the game activates, its handoff record can still cause a hub return over the game. Steam also loses its open state despite its hinted game remaining.

   **Fix:** distinguish registry identities from discovered candidates. Registry and desktop identities must win; reviewed prefixes must beat competing discovered candidates. Add a Steam-prefix collision test with launcher and game closure consequences. The current precedence test covers an **exact** hint beating a discovered candidate, not this case.

4. **Should-fix — the unowned-window protection excludes registry apps in 1.1.**  
   The [registry closure path](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:2853) returns immediately without checking unowned windows.

   With an unowned window open, closing foreground Chrome, Terminal, or KWrite can still pull the hub in front. The report explicitly records this exception, and the new test asserts it, but it contradicts the universal protection requested here.

   **Fix:** apply that protection to registry closures for 1.1. Preserve the old immediate behavior for 1.0, where comparison with the old helper confirms it is required.

5. **Nit — mutation evidence overstates individual test sensitivity.**  
   [REPORT.md:169](/var/home/ares/AresOS-30-installed-programs/reviews/30-installed-programs/REPORT.md:169) says every new test failed without its fix. Several are deliberately unchanged-behavior controls. In particular, [the ordinary-program metadata test](/var/home/ares/AresOS-30-installed-programs/os/tests/test_aresos_shell_review_fixes.py:84) also passes the original implementation, contradicting the later claim that all four `FlatpakAppIdTest` tests detect its removal.

   **Fix:** report which behavioral assertions fail for each precise mutation, distinguishing controls and avoiding counting missing-method/signature errors as regression detection.

6. **Nit — finish documenting the owner-visible limits.**  
   The report describes the brief hub return after a long Lunar handoff and acknowledges that every `com.mojang.minecraft` window is attributed to Lunar. It does not explicitly explain that the late game leaves the original launch permanently `closed`, or that another launcher’s Minecraft window can confirm/keep open a Lunar launch and trigger Lunar’s return.

   **Fix:** state those visible consequences alongside the limitations. These are provenance/timing limits, not reasons to restore inference.

The requested sequences, with time advancing, resolve as follows:

| Sequence | 1.1 owner experience | 1.0 owner experience, compared with the old helper |
|---|---|---|
| Lunar launcher → Play → game → launcher closes → play → game closes | Both windows belong to Lunar. Launcher closure does nothing while the game remains. On final game closure, Lunar closes after the 0.5-second grace. If the compositor already chose the hub, no forced activation is needed. | Launcher and game are unowned. Their opening/closing changes no launch and forces no return; the compositor chooses focus. Discovery cannot be launched through 1.0. This matches the old helper. |
| Same, with Chrome behind | Chrome remains owned by `browser`. It does not prevent Lunar ownership. On game closure, Chrome may appear briefly before the pending return activates the hub, unless a subsequent choice cancels it. | Closing the game leaves Chrome or whichever window the compositor chooses. No Lunar return. Chrome’s own eventual closure retains its old registry return. |
| Launcher closes two seconds before game appears | The grace expires first: hub return and launch `closed`. At two seconds, the hinted game is owned by Lunar and can take focus, but the completed launch stays `closed`. Closing the game can still return to the hub. Chrome does not change that ownership. | Both windows remain unowned throughout. Any interim hub appearance or later Chrome focus is the compositor’s choice. |
| Discord closes but stays resident; unrelated window opens | Discord closes after the grace despite its resident scope. The unrelated window stays unowned, cannot confirm a second Discord launch, and its closure forces no return. If it is already open at Discord’s expiry, it suppresses that return. | Discord and the unrelated window are unowned; neither produces discovered ownership or forced returns. |
| Dialog of an owned program | An otherwise unclaimed dialog inherits its parent. A discovered dialog retains that owner after the parent closes and keeps the program open until the dialog closes. An explicit recognized identity takes precedence. | Registry-parent dialogs retain the old parent-based behavior. Discovered parents/dialogs are unowned; downgrade clears their cached discovered inheritance. |
| Hint also names a registry identity | The registry wins. Closing that window follows the registry program’s policy, not Lunar/Steam’s. | Only the registry ownership exists, as before. |
| Hint names or prefixes `aresos-desktop` | Validation rejects the hint; ownership also checks the desktop first. It cannot confirm an application launch or keep it open. | The desktop remains the desktop, matching the old helper. |
| Steam launcher and `steam_app_<id>` game | Works as intended absent the competing discovered exact candidate described above. The game keeps Steam open after launcher closure. | Both are unowned unless an identity independently belongs to a registry entry. |

The report adequately discloses unowned-window behavior, indefinitely waiting launches with live scopes, permanently open unowned windows suppressing discovered returns, and Steam’s prefix being unobserved on the laptop. The missing process association also prevents distinguishing different launchers using the same Minecraft identity. That limitation is acknowledged, but its lifecycle consequences need the clarification above.

For the new tests, this is a **read-based sensitivity assessment**, not confirmation of the reported mutation runs:

| Tests | Assessment |
|---|---|
| Marker tests | Ordinary-marker and non-forwarding cases detect the old bug. Recognized forwarding is a preservation control. |
| Flatpak-ID tests | Command-derived ID, excluded `flatpak` identity, and ambiguous-ID omission detect the old behavior. Ordinary-program metadata is a preservation control. |
| Legacy refusal tests | Both exercise failures caused by restoring the generic refusal; the complete expected unknown-app response matches the old helper. |
| Hint tests | Shipped files, validation, conflicts, exact precedence, and revision changes have relevant assertions. The absent-program case is a control. Prefix-versus-discovered-exact precedence is missing. |
| Ownership tests | Lunar timings/Chrome, resident Discord, Steam prefix, and unowned-window suppression target the respective fixes. Registry return beside an unowned window is a control asserting the exception above. |
| Legacy window tests | They exercise production catalogue construction and inherited-dialog clearing. None tests downgrade with an already-pending return. |
| Dropped-return tests | Two detect switch-cancellation removal; one detects launch-cancellation removal. The no-choice case is a control. None covers expiry before current-activation cancellation. |
| Step-A hardening tests | Bounds, off-loop scans, descriptor confinement, memory limits, SVG rejection, cache budgets, and Flatpak icon lookup have relevant regression assertions. Internal desktop links, accepted desktop exports, allowed SVG shapes, and the flagless systemd route include positive controls that need not fail when their corresponding restriction is removed. |

SAFE cannot be established while the four implementation issues remain.

CHANGES-NEEDED