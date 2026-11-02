# 14zq: Exclude ostree's post-staging hold helper from the idle gate; probe 24 and qualification 13

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zp still apply, with the change below.

## What qualification 12 proved

- **Hidden input is now reliable:** the 377-character token arrived as 1,110 of 1,110 key events, with 0 repeats and 0 drops, and the real `login` authenticated.
- `verify` passed, and `switch` staged AresOS (`Deploying...done`).
- Then `title`'s `idle()` gate refused with `rpm-ostree/bootc/ostree client active`.

## Diagnosis (integrator; confirm it from the retained STOP diagnostics)

`deployment_processes()` (in `pin-stock.sh` and `pause-stock-updates.sh` in the payload) counts every `bootc`, `rpm-ostree` or `ostree` executable as a client, except the `rpm-ostree start-daemon` in `rpm-ostreed.service`.

The pinned image ships **`ostree-finalize-staged-hold.service`**. The retained squashfs listing has `usr/lib/systemd/system/ostree-finalize-staged-hold.service`, and also `ostree-finalize-staged.service` and `bootc-finalize-staged.service`. Upstream, staging a deployment starts it, and it runs **`ostree admin finalize-staged --hold`** until shutdown.

So after **any** staging, `title`, and every other idle-gated command, refuses until reboot. That would also happen on the owner's laptop, where the guide requires the refreshed title before rebooting. This is a real owner-tool bug.

## Fix (owner tools)

1. **Verify from the pinned image, read-only** (`unsquashfs -cat` on the cached ISO, as before): the exact contents of `ostree-finalize-staged-hold.service`, `ostree-finalize-staged.service` and `bootc-finalize-staged.service`, and their path/trigger units. Record the `ExecStart` lines and the cgroups.
2. **Exclude exactly the system helper(s) those units start,** matching all three of:
   - the executable `ostree` (or `bootc`, where its unit says so)
   - the **exact argv** from the unit, for example `admin finalize-staged --hold`
   - the **exact cgroup** `/system.slice/ostree-finalize-staged-hold.service` (or the verified unit's)

   Mark them `excluded_as_system_helper` and record them in diagnostics. Anything else stays a client. A helper with unexpected argv or cgroup is a client.
3. **Same classifier everywhere:** apply it in both payload scripts' `deployment_processes` and wherever the tool calls `idle()`. Keep `transaction is None` mandatory.
4. **Tests:**
   - the retained qualification 12 process list must pass `idle()`
   - the hold helper in the wrong cgroup, or with different argv, still blocks
   - a real `bootc`/`rpm-ostree` client still blocks
   - an active transaction still blocks
5. **Look for other gaps of this kind:** check every other idle- or postcondition gate that can run while a deployment is staged (title, records, verify, layout, rollback, keep-stock, reboot) for the same assumption.
6. Regenerate the payload and fingerprint everywhere. Package 15 takes the new fingerprint later.

## Budget (owner's $10 cap; about $6.88 billed)

One push, plus probe 24, plus a qualification of at most 160 is about $1.43 at worst, which fits. Settings for package `14` only:
- `minute_cap`: **1700** (1412 + 238 = 1650)
- `dispatch_caps.probe`: **25**
- `owner-tools`: **14**

## Then

1. Pinned local gitleaks, the replay and strict checks; a local Windows retry is allowed. Exactly **one** push.
2. Fresh exact-head privacy, the ledger, billing and the budget.
3. **Probe 24**. Only if it passes, **qualification 13 on the same head**.
4. Any CI stop: report it with diagnostics, no rerun.
5. When acceptance is met, restore closing 12 and reserve 150 in a final commit, push once, mark PR #13 ready for review, and say the run is over so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
