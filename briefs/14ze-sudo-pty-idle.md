# 14ze: The new idle check doesn't recognise an idle root shell behind sudo's pty; fix it, then probe 16 and qualification 6

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zd still apply, with the change below.

## Diagnosis (integrator, from the code)

`os/ci/owner_console.py` `foreground_is_shell` finds the physical tty's foreground process group and accepts only a bare interactive `bash`. After the harness's `sudo -i`, a current sudo with **`use_pty`** (default on since sudo 1.9.14) keeps **sudo itself** in the foreground of tty3 and runs the root shell on its own `/dev/pts/N`. So the observer saw `sudo`, never `bash`, and waited 840 seconds with `ready=false` while a root prompt was on screen.

Qualification 4 didn't have this check (14zb added it), which is why it got further. This is a harness regression, not an owner-tool defect.

## Do

1. **Verify from the pinned image** (unsquashfs read-only, as before): the sudo version, and whether `use_pty` is on (the compiled default plus `/etc/sudoers` and `/etc/sudoers.d`). Record both.
2. **Accept a sudo relay only when it is provably idle at a root prompt:**
   - The physical tty's foreground group leader is `sudo` with exactly the harness's expected arguments.
   - Its descendant chain, sudo's monitor then the command, leads to an interactive `bash`.
   - That bash runs on a pts whose foreground group (the `tpgid` in `/proc/<pid>/stat`) is that bash's own process group.
   - A bash running a child command, an unknown process, several candidates, or a broken chain: not idle.
   - Keep the plain-bash case as it is.
3. **On a refusal, export the non-secret foreground chain** (PIDs, `comm`, argv) for diagnostics. The harness never puts secrets in argv; check that this holds for every typed command, and redact anything after a hidden prompt. Also give the account-login and sudo observations **separate** readiness files, so they no longer overwrite each other.
4. **Local tests** with modelled `/proc` trees:
   - plain idle bash: ready
   - sudo `use_pty` relay with idle root bash: ready
   - the same relay with bash running a child: not ready
   - an unknown foreground process: not ready
   - two candidates: not ready
   - a broken chain: not ready
   - the exact qualification 5 situation reproduced from its retained evidence

## Budget (owner's $6 cap; about $2.20 billed)

One push, probe 16, then qualification 6, within the existing allowances (cap 1100, probe 16, owner-tools 6). Recheck the ledger, billing and the budget before each dispatch.

## Then

1. Pinned local gitleaks, the replay and strict checks. A local Windows retry is allowed, as in 14zd. Exactly **one** push.
2. Fresh exact-head privacy. **Probe 16**; only if it passes, **qualification 6 on the same head**.
3. Any CI stop: report it with the exported diagnostics, no rerun.
4. When acceptance is met, restore closing 12 and reserve 150 in a final commit, push once, mark PR #13 ready for review, and say the run is over so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
