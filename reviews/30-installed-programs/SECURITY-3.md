Reviewed commit `0156d72719111652c0a4e3f6de34142b14e3b7c7`, read-only: only file reads and read-only git commands; no helper, tests or builds run; no files changed.

Scope: `1467f68f..HEAD` in the requested helper, tests and image-check paths, plus the uncommitted report update. Test results below are assessed from their source, not independently reproduced. `HOSTED-RESULTS` is not a finding.

| Finding | Status | Reason |
|---|---|---|
| SECURITY-2 #1: filesystem availability checks block serving | CLOSED | Listing uses published `App.unavailable` values. Launch validation, including the working-directory probe, runs on worker threads; pending requests receive timeout failures. At most four checks remain outstanding. Scan deadlines are checked during parsing, before availability checks and before catalogue publication. |
| SECURITY-2 #2: SVG pre-check exhausts helper memory | CLOSED | Production parsing runs in a separate `python3 -I -S` process under `prlimit --as=268435456` and the converter’s timeout/cleanup machinery. Namespace lengths, names, elements, attributes and nesting are bounded. Conversion receives the same private input copy. |
| Window fix: downgrade cancels pending returns | CLOSED | A 1.0 takeover cancels existing return intent; discovered closure expiry also requires 1.1 before forcing a return. |
| Window fix: current switch precedes expiry | CLOSED | Current activation cancels obsolete return intent before expired discovered closures execute. |
| Window fix: reviewed prefix beats discovered identity | CLOSED | Catalogue filtering removes conflicting candidates; ownership independently ranks registry identities, exact hints, prefixes, then discovered candidates. |
| Window fix: registry apps respect unowned windows | CLOSED | Under 1.1, registry closures suppress forced returns when unowned windows remain. The 1.0 behavior is preserved. |

No new **FIX** or **SHOULD** findings meet this round’s bar. Two accepted-limit scenarios need documentation:

1. **NIT — a rapid switch can be mistaken for the compositor’s choice.**  
   **Where:** [os/config/usr/libexec/aresos-shell:3084](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:3084), [3116](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:3116).

   Lunar closes; the compositor activates Terminal; the owner immediately switches to Notepad. If those changes are processed together, only Notepad’s final activation is considered. It becomes the recorded compositor choice, so the pending return survives and later pulls the hub over Notepad.

   This requires the rapid-switch timing explicitly excluded from blocking findings. Add this visible consequence under “Known limits (review fixes 2), with what he would see”; that section currently omits it.

2. **NIT — authenticated request batches can accumulate the per-request wait.**  
   **Where:** [os/config/usr/libexec/aresos-shell:2757](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:2757), [2519](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:2519).

   An already-running hostile owner process authenticates and sends one batch of 100 distinct `open_app` request IDs for an app whose check remains stalled. They share one worker, but each request waits 0.2 seconds. Processing that batch can therefore delay heartbeats, listings and timeout handling for about 20 seconds.

   This affects responsiveness but requires the hostile owner process explicitly excluded by this round’s bar. Document the visible pause in the known-limits section. The four-worker limit does not describe this separate effect.

Known limits checked against the report:

- Split CSS references: documented, including converter containment and fallback/odd icons.
- Icon replacement races: documented, including temporarily missing or inconsistent pictures.
- Permanently blocked discovery: documented, including stale listings and restart recovery.
- Claimed window identities: documented, including Lunar/Steam misattribution, incorrect open state and unexpected returns.
- Check-to-start mount race and stuck-check lifetime: recorded in the known-limits section. Four-check exhaustion and delayed launch replies are separately recorded under judgment calls.
- The two scenarios above are missing from the requested known-limits section.

The changed tests cover the requested failure scenarios and preservation controls. The image-check change removes the dedicated `/tmp/pkg31-home` fixture immediately after its use; I found no new owner-data or command-execution issue there.

VERDICT: SAFE with documented known limits