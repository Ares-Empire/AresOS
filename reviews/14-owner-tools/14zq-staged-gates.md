# 14zq: staged deployment gates

The pinned ISO contains ostree 2026.4, bootc 1.16.13 and systemd 259.9.
The extracted units and their hashes are in
[`14zq-finalize-sources`](../../os/manifest/ci/14/14zq-finalize-sources/index.json).
The only long-running `ExecStart` among these units is
`+/usr/bin/ostree admin finalize-staged --hold`. It holds `/boot` open and waits
for SIGTERM. The finalize services have `ExecStop` commands that perform work
at shutdown. They remain deployment clients.

The helper exception requires `/usr/bin/ostree`, the full exact argv from that
unit, and exactly `0::/system.slice/ostree-finalize-staged-hold.service` in cgroup
v2. A different executable, argv, unit, nested cgroup or additional hierarchy
does not get the exception. The existing rpm-ostreed daemon exception is
unchanged. Both pause-script bodies are identical; owner `idle()` and prepare's
client selection use the same filter. A missing or non-null transaction always
refuses. `Tools.processes()` records classifications before returning them to
the gate, including on a subsequent refusal.

| Gate | Existing staged-state behavior retained | Verification |
|---|---|---|
| `prepare` | Only the qualified upstream stock state; foreign staged AresOS still refuses | Existing prepare refusals plus shared classifier regression |
| `title` | Allows the exact staged switch while validating saved pinned stock and the complete non-staged BLS identity set | Retained Q12 staged/prepared states, with explicitly modelled BLS reuse and unit-derived hold |
| `records` | Audits disks, then calls `title` | Full handler test with the staged-state fixture |
| `verify` | Requires the unchanged prepared state before switching; staged state refuses | Full handler refusal, before authentication or script execution |
| `switch` | Requires prepared state before the script; validates exact staged image afterward, then calls `title` | Classifier and title tests; actual VM acceptance still required |
| `layout begin` | Requires the booted AresOS recovery pair with no staged deployment or queued rollback | Full handler staged-state refusal; existing layout tests |
| `layout proof/revert` | Preserve their same-boot, physical-session and typing/settings checks | Existing layout tests; neither has a deployment-process exception to update |
| `layout finish` | Requires completed proof in the original session and calls `title` | Existing layout tests; same `title` classifier |
| `rollback` / `keep-stock` | Require the exact recovery pair and no staged deployment; pending-state refusal retained | Full handler refusals with the staged fixture and allowed hold |
| `reboot` | Allows qualified staging only with an exact fresh title/state/BLS, no pending layout, no tools stick and verified disks | Stale-title refusal followed by title refresh and mocked reboot; no host reboot |

No transaction check, updater pause, deployment identity, disk, BLS, firmware,
media or physical-session predicate is relaxed.

The Q12 artifact contains the earlier real rpm-ostreed process observation and
the post-switch staged state/refusal. It does **not** retain the detected
post-staging client's PID/argv/cgroup. The hold fixture is derived from the
verified unit, not presented as an observed Q12 process. The new diagnostics
and qualification acceptance require an actual post-staging hold classification.
