# 13f: Let the physical typer type its own commands, then finish the qualification

Follow-up on branch `pkg/13-keyboard-layout` (PR #12, draft). Read the 13e section of the REPORT. Briefs 13 to 13e still apply, plus the changes below.

## Where 13e stopped

The product repair passed on the real two-entry stock:
- the actual installer value, injected `de` and injected `us` were all repaired with the whole-list identity check
- the pin changed only the booted entry's pin flag
- the corrected stock booted with German loaded and no override
- tty3 physical login and password sudo passed, with a layout-sensitive password

Then the host fixture failed. `physical_keys('.', 'de')` raised `AssertionError: .` while typing its own setup command `python3 /run/aresos-physical.py`. The switch, AresOS, foot, the layout round trip and rollback were not reached. Every audit stayed clean.

## Integrator decision

1. **Fix the typer's coverage, not its strictness.**
   - Add `.` and every other character the qualification will ever type through physical input. Use the real QMP key and modifiers for each layout, verified from the pinned xkeyboard-config/kbd source.
   - Unknown characters must still raise.
   - Add a test that collects **every** string the harness types physically (setup commands, public text, the password's character set, layout-change commands) and checks that each one can be typed on both `de` and `us`.
   - Add regression tests for the existing layout-sensitive keys.
2. **Walk the unreached path before dispatch.** 229 passing tests didn't cover a string the run needed. Before any dispatch, list every host-side code path the qualification would run after the 13e stop point and that has never executed in a real run:
   - corrected-stock tty3 public text and Homebrew
   - verify and switch
   - AresOS boots, policy and foot typing
   - the `us` change and back
   - rollback and the rendered rollback greeter
   - the final entry-list assertions
   Run each one locally against the retained 13e evidence or source-derived inputs where it can run on the host, and record which ones can't. This is the zero-cost gate. Fix only fixture or harness defects it finds. A product or owner-script change stops and reports.
3. **Budget: the package cap goes from 380 to 460 minutes.**
   - The Ares-Empire Actions spending limit is $0 with usage blocked when the free quota runs out, so no money can be spent.
   - The October billing report shows about 1,255 of 2,000 free minutes used.
   - Allow **one fresh probe** (the harness changes) and then **one full qualification** on the same head, plus the closing privacy pushes. No second qualification, image dispatch or publication.
   - Before each dispatch, a fresh guard must show the reservation fits under 460. It must also show the reservation fits in the org's remaining free minutes (billing usage API, read-only) with at least 150 minutes left for other repos. If either check fails, stop and report.
4. **Entry-title JUDGMENT-CALL.** If the qualification shows the real list after the switch (AresOS plus the corrected pinned stock, old serial gone), make INSTALL and EMERGENCY name the real entries from that evidence. Then report whether the 13e "F12 → Windows before the pair is confirmed" step is still needed.

Everything else from 13e stays.

## Acceptance

13e's acceptance, reached in full in one qualification:
- the corrected stock boots with tty3 public text and Homebrew checked
- the signed switch works
- AresOS boots with an exact final entry list, physical typing on tty3 and in foot, and policy and Homebrew checks
- the layout changes to `us` and back to `de`
- rollback reaches the corrected pinned stock with its rendered greeter
- every audit passes

Also required: the coverage test and the unreached-path walk.

Push fast-forward only. Mark PR #12 ready for review if acceptance is met. Don't merge, and never make anything public.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
