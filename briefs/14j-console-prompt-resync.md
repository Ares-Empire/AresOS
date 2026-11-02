# 14j: Resync the tty prompt after kernel messages, like the owner would; second qualification

Follow-up on branch `pkg/14-owner-tools` (PR #13, draft). Read "14i: Same-head qualification and new tty3 readiness STOP" in `reviews/14-owner-tools/REPORT.md`. Briefs 14 to 14i still apply, with the change below.

## Integrator decision

Stopping was right. Probe 5 passed. The qualification installed offline, finished hardware setup and passed the Windows round trip, with every protected-disk, NVRAM and BootNext check clean.

**What happened:** the failure screenshot shows `root@bazzite:~#` followed by about 20 kernel lines from the USB attach. The cursor is left on an empty line, so `wait_tty` (which looks only at the cursor line) never sees `#`. The shell was idle and ready; only the screen was cluttered. On the laptop the owner may see the same thing at tty3, and would just press Enter.

So:
1. **Prompt resync, the way the owner does it.** When a readiness wait finds no prompt on the cursor line, the console may press Enter once (via the same key path as physical typing), then wait for a prompt again. Rules:
   - **Only when the shell is known idle:** the last typed command's completion was observed, and nothing has been typed since. Typically this follows a host-side event: hotplug attach or detach, first network, or anything else that can print kernel messages.
   - **At most 2 resyncs per wait,** then fail as now.
   - **Record every resync** in the evidence: stage, time, and the cursor line before and after.
   - **Never** suppress kernel messages, change the guest's console log level, or loosen the prompt predicate.
2. **Keep the raw evidence:** on any readiness timeout, retain the raw `/dev/vcsa*` bytes, so the cursor position is provable next time.
3. **Local tests:**
   - Replay this exact screen as a VCSA fixture: the prompt, then kernel lines, then the cursor on an empty line. The resync must recover with one Enter.
   - A busy shell (completion not observed) must never get an Enter.
   - Three cluttered screens in a row must fail after 2 resyncs.
4. **Owner route:** add one line to the guide's tools-stick step: "If text appears over the prompt after you plug in or remove the stick, press Enter to get the prompt back." Add it to the "For package 15" list too.
5. **Budget: no dispatch in this run.**
   - The same-commit probe rule stays: the qualification needs a passing probe on its exact head. So the new head needs probe 6 (about 25 minutes) and then the second qualification (hard timeout 130).
   - That doesn't fit October's remaining org minutes with the 150 reserve.
   - Whether to run them now with a smaller reserve, or on 1 November with fresh minutes, is the owner's call (it affects the other repos' CI). I'll tell you which in the next resume.
   - **Stop after pushing.** Don't dispatch anything.

## Then

Pinned local gitleaks before every push. The local replay as in 14e and 14f, plus the strict composed-command checks from 14i. Push the fix with a fresh ledger snapshot, and record the cost of probe 6 plus the qualification under both options. Then stop before any dispatch. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
