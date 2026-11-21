# Review 1 of HOME-OUTSIDE.md

Fresh review against brief 332, the code and the design docs in this checkout. Read-only; nothing was run.

**In short.** The three-layer structure is sound, and most claims about today's code are true. Three points are blocking. All three are gaps in the note's text, not in its structure, and one fix round can close them.

**Not checkable here:** labwc's own behaviour (its source is not in the repo), the image's systemd-oomd settings, and brief 328.

## 1. Does the note answer brief 332's nine questions?

| # | Question | Answered | Gap |
|---|---|---|---|
| 1 | Where each part lives | Yes (section 4) | None |
| 2 | One source, messages, versions | Yes (section 5) | Finding 16 |
| 3 | World-off switch, states, memory | Mostly (section 6) | The state table has no transitions (finding 20) |
| 4 | Two screens | Yes (section 7) | Cursor crossing is left to brief 328, and the note says so |
| 5 | Bar over full-screen apps | Yes (section 8) | Part-screen windows are not weighed (finding 17) |
| 6 | Sleeping world | Place given (section 9) | Stop, adoption and kill paths are missing (finding 20) |
| 7 | Migration | Yes (section 10) | Findings 24 to 27 |
| 8 | Owner questions | Yes, three | Findings 28 to 30 |
| 9 | Risks, memory full at wake | Yes (section 12) | Findings 21 and 22 |

It skips none. It answers these only by assertion:

1. "The game's scope carries the worst kill preference" (line 516). No mechanism is named (finding 22).
2. "The recovery key ends every AresOS surface that holds the keyboard" (line 501). No mechanism is named (finding 9).
3. "The supervisor also ends a native home that … stops answering" (line 501). Neither 1.2 nor the 1.3 table has a ping for views.
4. The world "moves there within seconds" (line 275). 23c's mechanism is still a plan that "a design step confirms" (`STATE.md:202`).

## 2. Are the claims about today's code true?

**These hold:**

- **Helper start.** It is started per launch with that launch's nonce, and not without a launch: `os/config/usr/libexec/aresos-desktop:1988`, `:2005-2009`; `os/config/usr/libexec/aresos-shell:4705-4710`.
- **`open_app`.** It always launches: `aresos-shell:3599-3655`, `:3689-3733`.
- **Window client.** It can activate and minimize only, reads no titles, and binds `wl_output` at version 1: `aresos-shell:2847-2850`, `:2866-2876`, `:2942-2962`.
- **Events.** `apps_running` goes to views only, and `app_state` to the asker: `aresos-shell:3354-3364`, `:3816-3821`.
- **Covering.** It needs the world's window: `aresos-shell:2705-2707`.
- **The home.** The helper keeps it in memory only: `aresos-shell:3094`, `:3514-3526`.
- **Supervisor.** States, command list and private environment: `aresos-desktop:328-329`, `:4783-4785`, `:182-184`. Prism is kept open: `:572`.
- **Stop.** A plain stop is called off without a confirmed save: `aresos-desktop:3370-3378`, `:3535-3543`.
- **Helper restarts.** They end after five failures: `aresos-desktop:2036-2048`.
- **Mod.** Hotbar click and search Enter end in `open_app`, and the search needs a ready world: `mod/src/client/java/dev/aresos/client/HomePointer.java:46`, `WorldSearchScreen.java:125-127`, `:320-326`. A 1.2 mod frees the mouse on any `background`: `ShellFocusClient.java:61-65`.
- **Laptop home.** View `laptop-home`, seven kinds of hits, slots, keys 1 to 9: `os/config/usr/libexec/aresos-laptop-home:492-495`, `:773-791`, `:1047-1059`, `:1399-1402`. Its slots draw the published cells (`:1751-1758`), so section 8's "assumption" is true.
- **Numbers and rules.** Memory figures: `docs/HUB-HANDOFF.md:46`, `docs/design/LAPTOP-HOME.md:327-328`. 23c's rule: `STATE.md:202`.

**False or loose:**

5. **Kill preference stated as fact (line 516).** Today the game's scope sets only `MemoryHigh` and `TimeoutStopSec`: `aresos-desktop:1059-1060`. Any SIGKILL end latches `killed` and opens the recovery window: `aresos-desktop:2408-2420`.
6. **"The test it already uses after a memory kill" (line 513).** That test needs a full clear minute and is sampled only while latched `killed`: `aresos-desktop:225-232`, `:2490-2492`, `:2541-2552`, `:2589-2601`. Reused as it is, every wake would wait a minute or more.
7. **Smaller slips.**
   - "`rc.xml` binds no Super key yet" (line 85). It binds Super+Ctrl+Escape: `os/config/usr/share/aresos/labwc/rc.xml:20`. The note means no lone Super.
   - "Package 318's frozen games held 421 to 510 MiB" (line 427). 510 is package 49's run; 318's were 421 to 502: `reviews/318-thaw-watchdog/FINDINGS.md:110`. The swap figures were forced by the rig's `RECLAIM=600M` (`FINDINGS.md:29`).
   - `black` as "the session's own background `#0d0d10`" (line 229). Nothing in `rc.xml` or `os/config/usr/share/aresos/labwc/autostart:1-5` sets a colour. `#0d0d10` is 23c's plan (`STATE.md:202`). Mark it as an assumption.
8. **"A sandboxed picture decoder" (line 119).** True for icons up to 512 × 512 with a 5 s limit, in pure Python: `aresos-laptop-home:36`, `:200`, `:270`. It cannot decode a screen-sized still or picture in time. The note does not say how those are decoded.

## 3. Is the structure sound?

Sound, and I would keep:

- the three layers;
- the helper for the session;
- one `activate_app` for every left click;
- closing the game and Prism for off;
- "never a frozen window on screen".

Flaws, races and single points of failure:

9. **One native program: a hung search holds the keyboard. Should fix.**
   - The search and the menu share a process with the always-on surfaces.
   - Today the recovery key opens a terminal and asks the supervisor to hide the cover (`rc.xml:20`). A terminal that opens under an exclusive layer cannot get the keyboard (`docs/design/COMPONENTS.md:1204-1208`).
   - So the key must end the native home directly, also with a dead supervisor. Name that path.
   - Prefer keyboard mode "on demand" for the search and the menu, so a click elsewhere frees the keyboard.
10. **Helper crash. Should fix.** The helper is the one road for launching, Super, `wake_world` and bringing the world's window back.
    - With the world asleep and the helper gone, a click on the still does nothing and nobody restores the window. Add: the supervisor wakes the world (if admitted) when the helper stays away, and resends the world's state at each helper start.
    - The helper dies with the supervisor (`aresos-desktop:3804-3805`), so "session life" is supervisor life. Say so.
11. **`aresos-home` crash. Should fix.**
    - World asleep: the still vanishes, the screen is bare, and click-to-wake is gone. Add two rules: no still on screen, no sleep; and the native home gone while asleep means wake (if admitted).
    - After package 10: the mod must show its own hotbar by default when it loses the helper, not only on `bar` false.
12. **Sleep order: save, still, minimize, freeze. Should fix.**
    - The game runs between `saved` and the freeze, so "saved and not run since" (line 517) is not strictly true. Order it still, minimize, save, freeze. He cannot touch a minimized world.
    - Nothing confirms that the still is on screen before the minimize. Add an acknowledgement from the native home.
    - Wake waits for two frames while the window is minimized. Minecraft draws 10 frames a second when minimized (`HomeScreen.java:38-39`). Whether a buffer swap completes on an unmapped Xwayland window is unverified. Add a timeout, and add this to the list to verify.
13. **Wake and the keyboard. Should fix.** To today's helper, an activated world means "he wants the world": it takes the keyboard and minimizes what covers it (`aresos-shell:4134-4147`). COMPONENTS.md lists "`unset_minimized` does not take the focus" as unverified (`:1008-1009`).
    - Say which wakes give the world the keyboard: a click, Home, the return after a close.
    - Say which must not: the pointer coming near, an uncovered output.
    - Mark a wake's activation as Super's is marked, so nothing is minimized.
14. **A frozen window can still come on screen. Should fix.**
    - Alt+Tab lists the world (`rc.xml:22`; the world's rules at `:34-38` do not skip the switcher).
    - Super's fallback route activates the world's window (`aresos-shell:4274-4275`).
    - If the wake is then refused for memory, the frozen window keeps the keyboard, and queued clicks replay at thaw.
    - Rule to add: while asleep the helper never activates the world's window, and minimizes it again when labwc shows it and the wake is not admitted.
15. **Two screens. Should fix.**
    - `screens.home` says where the world should be. During the move the monitor has neither world nor picture, though line 292 promises a picture "from the moment it appears". Add where the window is, or keep the picture until it arrives.
    - Hotplug while asleep is not named: the still has the old size, and 23c's move acts on a frozen, minimized window.
16. **`aresos-shell/1.3`. Should fix.**
    - `activate_app` during a launch that is still starting begins a second launch on a double click. Return the starting launch instead.
    - Activation from the search or a menu must follow COMPONENTS 4.5's order: release the keyboard, round trip, then ask (`COMPONENTS.md:1204-1208`).
    - `set_setting world off` can take 60 s. The helper's loop is single-threaded. Reply at once and report through `screens`.
    - The nonce handover needs an acknowledgement. Today the packet is a plain write and a 64-byte read (`aresos-desktop:3809-3816`, `aresos-shell:4602-4615`). A lost packet refuses the mod's hello (`aresos-shell:3391-3394`) and ends in `slow_start` after 120 s.
    - Say that minor 3 arrives with package 2 and later capabilities join it. The laptop home pins minor 2 and keeps working (`aresos-laptop-home:492-495`).
17. **The bar over part-screen windows. Should fix.** "Shown, above part-screen windows" with no reserved space (lines 344 to 349) hides the bottom rows of a half-snapped window for good, for example a terminal's prompt. Either let the bar go to `edge` when a window overlaps it, or ask the owner (finding 29).
18. **Ending Prism. Should fix.** Line 219 says "Prism's scope". After a retry or crash restart the live Prism sits in an earlier launch's scope, because a later `--launch` is handed to it (`aresos-desktop:1053-1055`). Name all `aresos-desktop-*.scope` units. Verify that SIGTERM does not cost Prism its sign-in.
19. **Super's road. Should fix.** It runs labwc, supervisor, helper, native home. 23c's plan does nothing outside IN_WORLD (`STATE.md:204`). Tell 23c that Super must pass in OFF, ASLEEP and STARTING.

## 4. Real harm (decision 24)

20. **Blocking: the sleeping world and the stop routine.** The note adds ASLEEP and WAKING but not what a stop does in them.
    - Today's stop asks the game to save and then sends SIGTERM (`aresos-desktop:3323-3355`, `:3380-3399`). A frozen game does neither.
    - A shutdown with a sleeping world would wait the full 60 s, then the scope's 15 s, behind black. The next boot would latch `unsaved` and not open the home until `retry` (`aresos-desktop:3545-3557`, `:3629-3633`).
    - World off while asleep would need a thaw, on a laptop he is trying to free.
    - A restarted supervisor would adopt the frozen game and show `slow_start` after 120 s (`aresos-desktop:1855-1877`, `:2554-2558`).
    - **Fix in the note:**
      - Say what `stop`, `restart`, `logout`, shutdown, world off, the `save` command and adoption do in ASLEEP and WAKING.
      - Record "asleep, saved" durably.
      - Close a sleeping world without a thaw, as confirmed by the sleep's save.
      - Say plainly that this changes two written rules for a sleeping world only: "never sends SIGKILL to the game" (`aresos-desktop:79`) and the `killed` latch (`:2408-2420`).
      - This needs finding 12's order.
21. **Blocking: the world turns itself on in OFF.** Line 500, link 3, starts the world when the native home keeps failing. Line 251 says nothing restarts by itself in OFF. The start costs about 1.4 GiB at the moment he chose to keep memory free, and it skips rule 2's check. Fix: that start passes rule 2; if it does not, the message window says how to get the bar or the world back.
22. **Blocking: "the world is the one that goes" has no mechanism.**
    - Rule 2 (admit the wake) is the right answer to his worry. It needs its own test (finding 6), sampled while asleep. It must also cover every start: deep sleep, a dropped world, link 3.
    - Rule 3 promises "never". The scope has no preference today (finding 5). As far as I know systemd-oomd has no "kill this first" setting; verify on the image. An `oom_score_adj` only steers the kernel's own killer.
    - "Which has lost nothing" (line 50) holds only for a sleeping world. An awake one loses up to five minutes of building, as today (`docs/design/HUB.md:59`).
    - **Fix:** make rule 4 the mechanism. The supervisor drops the sleeping world itself, below the system's threshold. Write rule 3 as an aim, with the awake-world limit. Note that this changes `docs/design/OS-BASE.md:350-352`.
23. **Verdict on memory full at wake.** With findings 20 to 22 fixed, the wake itself is safe: his apps stay, the bar stays, and the world waits or is dropped. Without them, the paths that hurt are a forced thaw for a stop, the unasked start, and an unbacked promise.

## 5. Is the migration buildable?

24. **Yes, step by step.** Each replacement has a named fallback: the hotbar until package 10, the mod's search until package 6 plus a release. Package 2 can start now.
25. **Order. Should fix.**
    - The switch is seventh, behind the L-sized bar. The owner asked for it first. Search alone is a launcher, so 1, picture, 6, 7 would ship it sooner.
    - Package 7 without 5 leaves no bar over a maximized app in OFF. Say so, or add the need.
26. **23c. Should fix.** Packages 3 to 10 hang on 23c through package 3. The single-screen parts (picture when off, bar, edge) need no monitor. Split package 3.
27. **Sizes and owners.**
    - Package 1 looks L: session life, the handover, the restart policy, the home on disk, `wl_output` names, the token, the native start, and 23c's plan.
    - Package 8 looks L: boot path, cover, loading while minimized.
    - The laptop home belongs to `linux-laptop-home` today (`docs/HUB-HANDOFF.md:112`). Name who takes it over.
    - Two leads in one 2,637-line file is a merge hazard. Split it into modules first.

## 6. Are the owner questions right?

28. **Yes.** All three are things he can see, and each has a recommendation.
29. **Add one:** does the bar stand over a part-screen window's bottom edge (finding 17)? He can judge it by sight.
30. **Tell him, rather than ask.**
    - The native search replaces the Bar look he picked on board #382 (`STATE.md:143`). Say that the look carries over, or show him.
    - Decision 6 changes his board #155 answer for gates and `/name` (`docs/design/HUB.md:299`). It follows his try-out, but between packages 2 and 4 the world has no "New window".
    - Say what a click on Home does in OFF.

## Known limits / nits

- "A key on the still" (line 414) contradicts "the picture never takes the keyboard" (line 128).
- "No fallback window" changes today's code (`aresos-laptop-home:598-603`). List it under "What changes in it".
- The view name `home` and the new program name touch `LAPTOP_HOME_APP_ID` in the helper (`aresos-shell:165`).
- `aresos-settings` holds enumerations only (`os/config/usr/libexec/aresos-settings:19-23`); `picture-file` is a new kind. An older release's `set` drops unknown names (`:60-68`, `:110-115`), so after `previous` the world and picture settings can be forgotten.
- `home.json` is planned in `$XDG_STATE_HOME`; the supervisor uses a fixed `~/.local/state/aresos` (`aresos-desktop:372-373`).
- "Nothing changes on screen" at sleep (line 66) holds only after package 10. Before it, the hotbar swaps for the outside bar.
- Bar slots show the 12 × 12 logo; the game's hotbar shows the item icon.
- A stray click on a house in the town picture opens an app. The town's clock and battery double the status icons.
- "8 MiB per picture" is one 1920 × 1080 buffer. GTK may keep two (`LAPTOP-HOME.md:331-335`), and a larger monitor costs more.
- Turning the world on with apps open shows Prism's own window, which takes the focus for a moment.
- Say whether his own quit of the game (today the `quit` window, `aresos-desktop:2421-2428`) becomes OFF.
- "Close all windows" on a terminal ends running jobs without a question. Ask once when more than one window closes.
- An app whose windows nobody owns starts a new instance on every left click.
- "The content never names a colour" does not fit the town's painter (`aresos-laptop-home:1478-1482`).
- Launches of the mod that end during sleep are not in the wake snapshot.
- Turning the world on by hand at full memory deserves one warning line.

NOT READY: (1) finding 20, the stop routine, adoption and kill handling for a sleeping world are undefined and today's stop cannot act on a frozen game; (2) finding 21, the world starts by itself in OFF without the memory check; (3) finding 22, "the world goes first" has no mechanism and the wake test is undefined.
