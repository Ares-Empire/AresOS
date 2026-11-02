# 14zo: Prove the owner-length hidden token path; chunked typing and key-event counts for the long CI token; probe 22 and qualification 11

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zn still apply, with the change below.

## What we know

Qualification 10's diagnostics:
- tty3 active, K_UNICODE, LEDs clear
- tty3 and pts1 raw, pts2 canonical with ECHO off and ICRNL on
- every queue empty
- both sudo relays and monitors in `ppoll`, root bash in `wait4`, Python in `read` (`wait_woken`)
- the harness sent 377 characters as 378 chords (1,108 key events), the last being Return

**Integrator reproductions in WSL** (real sudo 1.9.15 with `use_pty`, nested, `input()` then `getpass`, a pty driven per byte): dummy tokens of **17 and 377** characters both return, with one relay and with two. Python 3.14.8's getpass behaves the same. The VM types through a **QEMU `usb-kbd`** (`two_disk_vm.py:92`), whose HID event queue is small. A dropped event, including the final Return, would leave the reader exactly like this. That is unproven.

The owner's real token is a classic PAT of about 40 characters. The CI job token is 377 characters, so it is not representative of the owner's case.

## Do

1. **Count the key events the guest receives:**
   - During each hidden-token typing, run a guest-side counter over serial that reads the keyboard's `/dev/input/event*` device for the typing window.
   - Record **only counts**: EV_KEY press, release and repeat events, plus SYN_DROPPED. Never record key codes or values.
   - Compare them with the events the harness sent. Also record the guest's input autorepeat settings.
2. **Owner-length proof first.** In the private-login stage, before the real login:
   - run `login`
   - type the username
   - at the token prompt, type a **40-character dummy** shaped like a classic PAT: `ghp_` plus 36 random `[A-Za-z0-9]`, generated per run and never stored

   The tool must return within 180 s with its normal registry-refusal STOP. Record the outcome, the key-event counts and the 14zn diagnostics. If this stalls too, that's an owner-facing STOP: report it and don't continue to the real token.
3. **Real CI token in chunks:** type it in chunks of 16 characters with a 1 s pause, wait 1 s, then press Return.
   - Collect the same counts and diagnostics.
   - Never retype the secret, and never add a second Return automatically.
4. **Fix the wchan collector** that rejected four sudo `wchan` names: allow normal kernel symbol characters, with the same no-arguments rule.
5. **Local tests** for the counter (modelled input events, including SYN_DROPPED), for the chunked typing schedule, and for the dummy-token stage wiring.

## Budget (owner's $10 cap; about $5.30 billed)

One push, plus probe 22, plus a qualification of at most 160 is about $1.43 at worst, which fits. Settings for package `14` only:
- `minute_cap`: **1500** (1208 + 238 = 1446)
- `dispatch_caps.probe`: **23**
- `owner-tools`: **12**

## Then

1. Pinned local gitleaks, the replay and strict checks; a local Windows retry is allowed. Exactly **one** push.
2. Fresh exact-head privacy, the ledger, billing and the budget.
3. **Probe 22**. Only if it passes, **qualification 11 on the same head**.
4. Any CI stop: report it with the counts and diagnostics, no rerun.
5. When acceptance is met, restore closing 12 and reserve 150 in a final commit, push once, mark PR #13 ready for review, and say the run is over so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
