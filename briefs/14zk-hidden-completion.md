# 14zk: Fix the hidden-input completion proof (Readline ECHO-off, persistent login parent); local only

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zj still apply, with the change below.

**Stop:** qualification 8 stopped at the first installed-system physical login. The 14zi "reader left its read" proof waited for ECHO to come back on. That is wrong in two ways:
- Readline keeps ECHO **off** at an idle bash prompt.
- `login` stays alive as the parent of the user's shell, and the chain walk didn't expect it.

## Fix (harness only)

1. **Completion after a hidden input is a state transition, not an ECHO value:**
   - the expected reader (getty/login, sudo, or the owner tool's getpass) is no longer the foreground reader, **and**
   - either an interactive shell is idle at its prompt (the 14ze/14zg observer: account login, `sudo -i`), **or** the owner tool printed its result line (`PASS …` or `STOP …`) on the physical cursor line, for the tool's own hidden reads.

   Don't use ECHO as the completion signal anywhere.
2. **Expected parents:** accept the persistent `login` parent (getty → login → bash on the physical tty) and any other parent the pinned Bazzite 44 image normally has. Verify it from the image (util-linux login, systemd getty units) and from the retained qualification 8 chain.
3. **Every hidden input in every stage** uses the same proof.
4. **Local tests:**
   - the retained qualification 8 chain and screen must pass
   - a real pty test (`login`-like parent, bash with Readline idle, ECHO off) must pass
   - a getpass reader still waiting must not pass
   - a wrong reader must STOP
5. **Before any push, walk every remaining stage** (login, verify, switch, the AresOS boot, layout begin/proof/revert/finish, rollback, keep-stock) through the stand-in walk with the real chain shapes:
   - a getty login on tty3 or tty4
   - `sudo -i` relays
   - nested sudo
   - getpass
   - Readline ECHO-off at idle

   List any stage whose waits or hidden inputs aren't covered.

## Rules

Commit locally only, with the pinned local gitleaks. **No push and no dispatch:** the owner decides on budget next. Update the REPORT with a short 14zk section.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
