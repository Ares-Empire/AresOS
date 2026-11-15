# 18c-b progress

Brief: `briefs/18c-b-chrome-image.md` (on `main` since PR #73).
Branch `pkg/18c-b-chrome`, one builder at a time. Each step is a fresh agent; this file is the handoff.

## Where it stands

**Steps 1a, 1b and 2 are built and green.** (1a, 2 and 2b: Claude Fable 5.2; 1b: Claude Opus 5.5, as the brief
recommends.) Item 2's workflow passes all five cases on the image's pinned Chrome on head `c4514015`
(run 43729218613, `CONTROL_CHROME_INSTALL_PROOF_PASSED`). Next: 3a, which waits for PR #58 on `main` and the
lead's go.

## The lead's decisions after step 2b (2026-11-15)

1. **JUDGMENT-CALL 1 (the DevTools pipe) is accepted**, for the proof's own Chrome starts only. The image's Chrome
   start and policy never carry a `--remote-debugging-*` flag; step 4's image check asserts that (keep or add it).
2. **JUDGMENT-CALLs 2 to 5 are accepted** as written.
3. **JUDGMENT-CALL 6 changes:** on the pinned Chrome, a hand-loaded extension that could not be asked fails case 1
   instead of passing with `asked: false`. A check that quietly stops running must not look green; if a later
   Chrome can't load one, that is a finding for the lead. The next step that touches `proof.py` makes the change.
4. **C9 in the VM (step 5) may use case 5's trigger:** one test-only Chrome start in the guest with
   `--remote-debugging-pipe` and `cdp.py`, its own throw-away profile, run by the test; it checks that nothing
   listens, and the positive control (the probe's requests, log count equal to the server's count) is required.
   `cdp.py` goes into the guest with the test's files, never into the image. This amends the brief's C9.
5. **C2 in the VM (step 4)** asks an extension loaded by hand over the pipe, as `case_ordinary` does.
6. **PLAN-GAP 2:** both of the brief's assertions stay. The brief's sentence that the IDs go in a body the log
   doesn't record is outdated for Chrome 157; the header makes the ID assertion a real one.
7. **PLAN-GAP 3:** nothing to change; case 5 compares against the probe alone, so Chrome's own start-up requests
   cancel out.
8. **The three known-limit lines are accepted**; step 6 places them in `KNOWN-LIMITS.md` and the report.
9. **3a waits for PR #58 on `main`** (Codex reviews on 2026-11-17 at the earliest), then the lead's go.

## Step 2b (2026-11-15, Claude Fable 5.2)

### The lead's decisions on step 2's findings

1. **`setEnabled(false)` from another policy-installed extension** is accepted as Chrome's behaviour. Case 1 as
   step 2 changed it stands (the `uninstall` refusal; ours enabled and connected again at the next start).
2. **Chrome's own update-service requests** for its own extensions are accepted. Case 5's rule is the brief's
   fallback: against a run of the probe alone, ours adds no address and no ID.
3. **Case 5's trigger:** make the update check deterministic instead of waiting for the schedule; first try
   `chrome.developerPrivate.autoUpdate()` in `chrome://extensions` over the DevTools protocol.
4. **Case 3's record of the previous ID:** look at what it holds; a check if it grants the old ID anything,
   otherwise a line under "what the code doesn't show".

### Done

- **`cdp.py`** (new, standard library, 4 tests in `test_cdp.py`): the DevTools protocol over
  `--remote-debugging-pipe`. Only the Chrome starts that name it get the pipe (case 5's three, and the one below);
  every other start still refuses the `NEVER` flags. A pipe, not a port: each of those starts checks that Chrome
  listens on nothing.
- **Case 5** asks Chrome for each update check. Per run (ours; the probe alone; the policy without
  `override_update_url`): Chrome starts with the network log, `--disable-component-update` and the pipe; once the
  extensions are in, `chrome://extensions` is opened and `chrome.developerPrivate.autoUpdate()` is called twice,
  3 s apart (what the page's "Update" button calls: `ExtensionUpdater::CheckNow` with no IDs, so every extension;
  read in Chrome 157's `developer_private_functions.cc` and `extension_updater.cc`). After each call the proof waits
  for the probe's request at the test's own server. Required of every run: the probe's ID is in two update requests
  in the log, **and the log holds exactly as many as the server answered**.
- **`netlog.py`** (11 tests): a request's start is the event the log's own constants call `URL_REQUEST_START_JOB`
  (a log without constants is read as before); `added` counts a mention of the update service that the events
  don't account for (a line cut off mid-write) as added, also when the baseline has one.
- **Case 3** writes what the preference files keep under the previous ID to
  `case3-<n>-previous-record.json` and requires that it holds none of `manifest`, `path`, `location`,
  `active_permissions`, `granted_permissions`, `runtime_granted_permissions`.
- **Case 1, an extension loaded by hand** (`case_ordinary`, counted in case 1's verdict): a Chrome start of its own
  (own profile, the pipe, `--enable-unsafe-extension-debugging`), developer mode on, `Extensions.loadUnpacked` of a
  two-file extension with the `management` permission, then its page calls `management.setEnabled(<ours>, false)`.
  Chrome must refuse, and ours must still be enabled and connected. If this Chrome won't load one that way, the
  result says `asked: false` with the reason and case 1 doesn't fail for it.

### Runs

| Run | Head | Result |
|---|---|---|
| 43729218613 | `c4514015` | `pack` green (`Ran 25 tests`, `OK`, `# pass 1`). Proof: `CONTROL_CHROME_INSTALL_CASE_1_PASS` to `_5_PASS`, `CONTROL_CHROME_INSTALL_PROOF_PASSED`. The job took 3 minutes, after 56 in the queue |

Three of the 40 runs of this workflow are used. Cases 1 to 4 repeat step 2's numbers (install 0.8 s, pin 0 and
819 pixels, both switches of case 3 done 0.89 s after Chrome's start, case 4 held 20 s).

**Other runs, looked at once and not waited for.** On `c4514015`: records 43729218607, base 43729218627 and
boundary 43729218628 green; Control Chrome 43729218606, Mail 43729218574 and qualification 43729218660 still
queued. **Control Chrome 43726164356 on `9ac6c8cb` never started** (queued since 14:46 UTC, at both looks); that
head's Mail and qualification runs were cancelled by this step's push. So the whole matrix has no result on any
head of this branch since step 2: read 43729218606.

### Case 5 on run 43729218613 (all **run**)

| Run of Chrome | Update checks asked (s after start) | Probe's requests: log / server | Update-service addresses and IDs | Our ID outside a `file:` address |
|---|---|---|---|---|
| ours | 1.1, 4.3 | 2 / 2 | `https://clients2.google.com/service/update2/crx`, Chrome's own two IDs | none |
| the probe alone | 1.07, 4.27 | 2 / 2 | the same | none (it doesn't have it) |
| without `override_update_url` | 1.12, 4.32 | 2 / 2 | the same, **plus `POST https://update.googleapis.com/service/update2/json`** at each of the two checks | **`X-Goog-Update-AppId: <our ID>`**, twice |

- **Ours adds nothing:** `added_by_our_policy` is empty, and the two runs name the same five hosts.
- **The negative control fails the scan both ways:** an added address, and our ID named. The POSTs are in the log
  at the same instant as the probe's two requests (+0.71 s and +3.91 s), so each asked check did take ours in, and
  with `override_update_url` the same two checks leave nothing.
- What Chrome asks by itself in every run, all ending in `ERR_INTERNET_DISCONNECTED`: its time service
  (`clients2.google.com/time/1/current`), a spelling dictionary (`redirector.gvt1.com`), `www.google.com/async/…`,
  a key list at `www.gstatic.com`, and the store's update address for its own two extensions at 0.2, 2.2 and 6.1 s.
- Each run lasts about 7 s. `autoUpdate()`'s own answer never came within it (`checks_ended` 0): the check ends
  only when Chrome gives up on its own store requests.

### Case 3's record of the previous ID (**run**)

After A to B and after B to A, `Default/Preferences` keeps **an empty object, `{}`**, under the previous ID;
`Secure Preferences` has no entry for it. Nothing Chrome could load, no permission, no host access: bookkeeping
only. The check above stays as a guard, and the files are in the artifact.

### Case 1, who can switch ours off (**run**)

- An extension installed by policy can (step 2; `after_it`: `enabled` false, the tools `chrome_unavailable`; back
  0.61 s after the next start).
- **An extension loaded by hand can't:** `installType` `development`; `setEnabled(false)` answers
  "Extension … cannot be modified by user."; ours stays enabled and connected. This was read in step 2 and is run
  now. Chrome's rule: `AdminPolicyIsModifiable` in `standard_management_policy_provider.cc`.
- He himself in Chrome's own pages: `mayDisable` false (run); the switch on `chrome://extensions` was not clicked.

### Known-limit lines (for the report and `KNOWN-LIMITS.md`; the lead places them)

- An extension installed by policy can switch ours off until the next start of Chrome. Adding one needs root, so
  that is he himself or whoever has his password. While it is off the tools answer `chrome_unavailable` (fails
  closed). An extension he loads by hand can't do it.
- On a fresh profile Chrome asks Google's update service about two extensions of its own, whatever our policy
  says. Ours adds no address and no ID to that.
- After an update the profile's `Preferences` keeps an empty record under the previous ID.

### Left, in order

1. **3a**, when PR #58 is on `main` and the lead says go. Then 3b, 4 (4b), 5, 6 as before.
2. **For step 5 (C9 in the VM):** no scheduled update check comes within a VM run either. C9 needs case 5's
   trigger in the guest: a Chrome start with `--remote-debugging-pipe` and `cdp.py` (standard library, like
   `netlog.py`), which the brief's C9 doesn't allow yet. The lead decides; the other way, a policy change (below),
   is read and not run.
3. **For step 4 (C2):** the probe can't be refused `setEnabled` (it is policy-installed). With the pipe, C2 can ask
   an extension loaded by hand, as `case_ordinary` does.

### What the code doesn't show (2b)

- With `override_update_url` the update check of ours leaves **no line in the network log**: Chrome doesn't load a
  `file:` address through its network stack. That ours is in each check is shown by the negative control (the same
  two calls give two POSTs) and by Chrome's log having no "can not be updated" line (`chrome_could_not_update`
  empty in all three runs).
- Chrome doesn't close the log's JSON on SIGTERM: all three logs end mid-list. The constants are read from the
  file's first line.
- The pipe's ends: Chrome's two are passed as descriptors 10 and up and moved to 3 and 4 by a one-line `bash`
  `exec`, so Chrome keeps its PID. Our reading end is closed by its own thread at the pipe's end.
- Developer mode is switched on in the profile `ordinary` alone. No other profile sees the pipe except case 5's
  three.
- The network logs in the artifact hold Chrome's own built-in API key and request keys in Chrome's addresses.
  They are Chrome's, the same in every copy; nothing of ours or of the owner's.
- Step 2's two other ideas (a run with a network; a policy change adding a pending forced ID) were not tried:
  the first one worked. Read only: a changed policy with at least one `update_url` extension ends in
  `CheckNow` for every extension (`external_provider_manager.cc`).

### JUDGMENT-CALL (2b)

1. **A DevTools pipe in four Chrome starts**, against the brief's "never `--remote-debugging-*`", on the lead's
   decision 3. The pipe instead of a port, so nothing listens; cases 1 to 4's own starts are unchanged.
2. **`--extensions-update-frequency` is no longer passed.** Chrome 157 has no such switch: `extension_service.cc`
   gives the updater a fixed `kDefaultUpdateFrequency` and `extensions/common/switches.cc` doesn't list it.
3. **The proof doesn't wait for `autoUpdate()`'s answer**; it waits for the probe's request (the positive
   control) after each call. Two checks, 3 s apart.
4. **The positive control is stricter than the brief:** the log's count of the probe's update requests must equal
   what the test's server answered, not only be at least two.
5. **Case 3's check names what must not be there** instead of requiring an empty record, so a timestamp Chrome
   might add later doesn't fail it. Today's record is empty.
6. **The hand-loaded extension is asked where Chrome can load one**, and reported as not asked otherwise, because
   the brief requires the question of the probe alone. On the pinned Chrome it was asked.

### PLAN-GAP (2b)

- **No short update schedule exists** in Chrome 157 (JUDGMENT-CALL 2), so "across at least two update checks" can
  only be had by asking for them. The same holds for C9.
- **The log does show the IDs sent to the update service.** The brief says they go in a body the log doesn't
  record; Chrome 157's log has the request's headers (`CORS_REQUEST`), among them `X-Goog-Update-AppId` with every
  ID asked about. So both of the brief's assertions see the leak, not only the address.
- **Chrome asks more than the update service by itself** (the four addresses above). They are the same with and
  without ours and name no extension of ours.
- Step 2's three points stand.

## Step 2 (2026-11-15, Claude Fable 5.2)

### Done: the install proof in a container (item 2)

- `.github/workflows/control-chrome-install.yml` ("Control Chrome install"): pull requests touching
  `control/chrome/packaging/**`, `control/chrome/extension/**`, `control/chrome/ci/install/**`, the container's
  `Dockerfile`, `service.py`, `native_host.py` or the workflow. `contents: read`, no secrets. It builds the container
  of `control/chrome/ci/Dockerfile` with the pinned Chrome, adds `python3-cryptography` in a layer of its own
  (`control/chrome/ci/install/Dockerfile`), runs `run.sh pack` and then `run.sh proof`, both with `--network none`.
- `control/chrome/ci/install/chrome.lock.json`: Chrome **157.0.8103.50**, the image's pinned version, as Google's
  `.deb` by URL and SHA-256 (`92148bd1…3f79`, 147674220 bytes; Google still serves it). A workflow step compares it
  with `os/google-chrome.lock.json`: another major fails, another patch version warns.
- `proof.py` (root, in the container only): the image's layout (four files in `/usr/share/aresos/chrome/`, the two
  links in `/etc`, `packaging/host` 0755 and `native_host.py` in `/usr/libexec/aresos-control/chrome/`), a made-up
  `format` 1 list at `exclusions.SETTING`, CI's `service.py` as it is, one Xvfb session, Chrome with `browser.mjs`'s
  flags. Bundles A, B and C each come from one call of `pack.py -I -B`. Evidence in the artifact
  `control-chrome-install-<run>-<attempt>` (`result.json`, Chrome's logs, `probe.jsonl`, `tool.jsonl`, screenshots,
  network logs).
- The probe: `probe/` (extension: `management`, `nativeMessaging`; its manifest's `update_url` is
  `http://localhost:18766/probe/update.xml`), `probe_host.py` (its test-only host: writes down every message and
  relays it to the check's socket). Installed by `ExtensionInstallForcelist` alone, in `aresos-install-probe.json`,
  from its own `file:` address, packed with `pack.pack` under its own key.
- `netlog.py` with `test_netlog.py` (9 tests): the scan of `--log-net-log` for case 5, standard library only, so
  the VM pass can use it in the guest. `tool_call.py`: one tool call as the owner over `act.sock`.

### Runs

| Run | Head | Result |
|---|---|---|
| 43724239061 | `faa7e340` | `pack` green: Python 3.11.2, `cryptography` 38.0.4, `Ran 17 tests`, `OK`; node v22.23.5, `pack-crosscheck.test.mjs` `# pass 1` (**its first run ever**). Proof: case 4 PASS; 1, 2, 3, 5 FAIL (the three findings below) |
| 43726164336 | `9ac6c8cb` | `pack` green (`Ran 19 tests`, `OK`, `# pass 1`). Proof: `CONTROL_CHROME_INSTALL_CASE_1_PASS` to `_4_PASS`, `_5_FAIL` |

Two of the 40 runs of this workflow are used. Every push also started Control Chrome, base, Mail, boundary,
qualification and records (their paths); nobody waited for them: on `9ac6c8cb` base 43726164318, boundary
43726164304 and records 43726164298 are green, Control Chrome 43726164356, Mail 43726164371 and qualification
43726164312 were still queued. The lead's rerun of 43716630045: `fixtures (external, word-1)` passed on attempt 2;
the run's conclusion still read `failure` when looked at once.

### What run 43726164336 shows, case by case (all **run**)

1. **Install: PASS.** Fresh profile, no address but loopback's, no default route. Chrome installs ours from
   `file:///usr/share/aresos/chrome/update.xml` through the two links: installed 0.6 s and connected 0.64 s after
   Chrome's start. `management.get`: `installType` `admin`, `enabled` true, `mayDisable` false. `uninstall` is
   refused: "Extension … cannot be modified by user." No forbidden flag in any Chrome process, no listening port.
   **The pin:** in the right half of the top strip, 0 pixels differ between two pinned starts and 819 between
   pinned and the same policy without `toolbar_pin`. `setEnabled(false)`: see "wrong against real Chrome", 1.
2. **One origin: PASS.** The host manifest behind the link equals the rendered template; the host runs as the
   owner, started by Chrome, with exactly `PATH=/usr/bin:/bin` and `LANG=C.UTF-8`. The probe's
   `connectNative('org.aresos.chrome')` answers "Access to the specified native messaging host is forbidden."; over
   28 samples while it tried there was one host process and one connection on `chrome.sock`; ours still answered.
3. **Update and back: PASS.** A to B, then B to A, one profile, Chrome restarted. Both times, after Chrome's
   start: old ID gone 0.41 s, new installed 0.41 s, new connected 0.67 s, old folder gone from
   `Default/Extensions` 0.67 s. Only the current ID is listed beside the probe; the probe is refused again; the
   manifest's bytes hold the current origin and not the previous ID.
4. **A broken package: PASS (both runs).** On a profile that never held C: with one byte of the signed archive
   changed (Chrome logs `Package is invalid: 'CRX_SIGNATURE_VERIFICATION_FAILED'`) and with the file missing, C
   is not installed over 20 s (20 samples each), the tools answer `chrome_unavailable`, Chrome and the service stay
   up, the start page and a typed address both load. Restored: installed 0.41 s, connected 0.44 s. Installed, then
   changed or missing: still enabled and connected after 8 s.
5. **Nothing asks the store: FAIL, unfinished.** See "Left".

### The brief against real Chrome (157.0.8103.50)

1. **`setEnabled(false)` is not refused to the probe.** Chrome lets one policy-installed extension switch another
   off, and the brief requires the probe to be policy-installed. Run 43724239061: the call answered `ok`, ours showed
   `enabled: false`, the tools `chrome_unavailable`, for the 120 s watched. Case 1 now requires the `uninstall`
   refusal and that **the next start of Chrome has ours enabled and connected again** (run 43726164336: 0.4 s and
   0.43 s), and records what Chrome answered. Not exercised: an extension that is not policy-installed (read, not
   run: Chrome refuses those as it refuses the user). Whoever can add a policy file can already replace ours, so
   this adds no new party; it does mean C2 in the VM can't require the refusal either.
2. **"No request at all to the update service" doesn't hold for Chrome itself.** On a fresh profile, with
   `--disable-component-update` and no network, Chrome asks
   `https://clients2.google.com/service/update2/crx` for two extensions of its own
   (`ghbmnnjooekpmoecnnnilnnbdlolhkhi`, `nmmhkkegccagdldgiimedpiccmgmieda`, both `v=0.0.0.0`), retrying at 0, 2, 6,
   13, 29, 60, 120 and 236 s (run 43724239061's log). **Neither our ID nor the probe's appears anywhere in that
   236 s log.** So the brief's fallback is the rule now: case 5 always runs the probe alone as the baseline, and ours
   must add no address and no ID (`netlog.added`); the control without `override_update_url` must add one.
3. **`--extensions-update-frequency` gave no scheduled check.** With `=30`, no update check of the probe reached
   the test's server in 240 s (run 1) or 600 s (run 2). The probe's own `chrome.runtime.requestUpdateCheck()` then
   answered `no_update` and its request did arrive at `localhost`, so the address works and the schedule doesn't.
   Not a "Stop and report" case: nothing names our ID.

### Left, in order

(1 and 2 are closed in step 2b, above.)

1. **Case 5.** The baseline, the comparison and the negative control are written but have never run: the case
   stops at "two scheduled update checks". Find what makes Chrome 157 check all extensions. Untried ideas: the
   two store installs that never finish without a network may hold the schedule back (a run with a network, or a
   longer one); a policy change that adds a pending forced ID starts a check of everything (read, not run). The
   probe's `requestUpdateCheck` is ready as a positive control for the probe alone, but it doesn't check ours.
   Chrome doesn't close the log's JSON on SIGTERM; `netlog.events` reads the cut-off file line by line.
2. **Case 3's preference record.** After each switch the profile's preference files still list the previous ID
   (`"previous": true`, 7 entries) although the management API and the folder say it is gone. Recorded, not
   required; look at what the entry holds before turning it into a check.
3. Then 3a, 3b, 4 (4b), 5, 6 as before.

### What the code doesn't show (2)

- The artifact's files are public by design (`bundles.json` holds IDs and hashes only). No key is written; the
  probe's key is made in `proof.py`'s own process by `pack.pack` and dropped.
- `proof.py` runs as root because it swaps files under `/usr/share`; Chrome, the tool calls and the session run as
  `owner`, the service as `aresos-tools`. Chrome is ended with SIGTERM by its PID.
- The "one host" check reads the kernel's view (`ss -x`) and the process list, sampled every 50 ms, plus Chrome's
  own refusal text. `service.py` has no line for an accepted or refused host.
- Cases are independent where they can be: each has its own profile except 1 and 3, which share one on purpose.

### JUDGMENT-CALL (2)

1. **The policy form stays `ExtensionSettings` alone**: the pinned Chrome installs from it. The fallback isn't needed.
2. **Case 1's `setEnabled` check changed** as described above instead of installing a second, non-policy probe.
3. **The pin is asserted by pixels** (pinned twice against pinned and unpinned), since nothing but our own
   extension can ask Chrome about its pin. Thresholds: at least 150 pixels and four times the same-start difference.
4. **The harness is Python, not node**, so steps 4 and 5 can reuse `netlog.py`, the probe and its host in the guest.
5. **The Chrome pin is a file** (`chrome.lock.json`) whose hash has no second source; a patch-level difference to
   the image's lock warns instead of failing, as the brief allows the same major.
6. **Case 5 runs without a network** like the other cases; `--extensions-update-frequency=30` because release
   builds are said to enforce 30 s (read, not confirmed: no check ran at all).

### PLAN-GAP (2)

- The three points under "The brief against real Chrome".
- A change of `os/google-chrome.lock.json` doesn't start this workflow (its paths are the brief's plus its own
  files); the version step only speaks on the next run.
- Every push to this branch starts the whole Control Chrome matrix, because the new files live under `control/`.

## Step 1b

### Part A: the latency pair after 1a (run 43705955018)

**Cause (read from the run, not assumed).** Every job of `Control Chrome` on `265caa52` was green except
`latency (plain)` and `latency (audit)`, both in "Paired current and historical measurements on the same runner"
(`control/chrome/ci/latency-pair.sh`). The pair runs two legs: `current`, then `ab7aba92` (main's older runtime,
with the current `control/chrome/ci/` and `control/chrome_tests/` copied over it). The `current` leg finished and
printed its results (`"runtime": "current"`, build `2acd63cb…`); the `ab7aba92` leg failed in `browser.mjs` line 40
with `extension native connection: undefined`. Its artifact (`chrome-latency-43705955018-1-ab7aba92-plain`,
`tool.jsonl`) holds 296 `tabs` answers: 5 `chrome_unavailable` (before the extension connected), then 291
`chrome_settings_unavailable`. So the extension did connect; the tools refused because the list wasn't where that
runtime reads it. `ab7aba92`'s `exclusions.py` has `SETTING = '/etc/aresos/control/chrome-excluded-sites.json'`,
and the current `prepare.mjs` (copied into that leg) wrote only `/var/lib/aresos-control/…`. `rpc('tabs')` answers
`ok: false` without throwing, which is why the message says `undefined`. The lead's guess was right.

**Fix** (`32f1126c`): `prepare.mjs` no longer names a path for the list. It asks the tree under test,
`python3 -B -c 'from aresos_control.chrome.exclusions import SETTING;print(SETTING)'` with
`PYTHONPATH=/workspace/control`, refuses an answer that isn't an absolute path ending in
`/chrome-excluded-sites.json`, and writes the same content, mode (0640) and owner (`root:1001`) there. The
`current` leg and every other Control Chrome job get `/var/lib/aresos-control/…` as before; the `ab7aba92` leg
gets `/etc/aresos/control/…`, as main's harness gave it. Ceilings, sample counts, `latency-targets.json`,
`latency-reference.json`, `latency-pair.sh` and the comparison are unchanged. Checked locally: the command prints
the old path over `git archive ab7aba92 control/aresos_control` and the new one over the checkout.

**Its test:** `CiInstall` in `control/chrome_tests/test_excluded_sites_placeholder.py` (3 tests): `prepare.mjs`
holds neither path nor the file name as a literal, and writes and chowns `excludedSites`; the exact command taken
from `prepare.mjs` prints `exclusions.SETTING` over the checkout and the old path over a copy of
`aresos_control` whose `SETTING` is the old one; the guard accepts both and refuses others. All three fail on
`prepare.mjs` before the fix.

### 1b done: `record_build.py` (item 4)

- `control/chrome/record_build.py` (stdlib only; not one of `build.py`'s inputs, the hash stays `2acd63cb…`):
  - `add --commit <40 hex> --shipped-at <YYYY-MM-DDTHH:MM:SSZ> [--expect <64 hex>] [--registry PATH] [--repo PATH]`:
    `git archive <commit> -- control` into a temporary folder (extracted with tarfile's `data` filter), runs that
    commit's `control/chrome/build.py` with `-I -B`, refuses a wrong `--expect` or an existing row for the commit
    with another hash, adds the row, keeps the newest three by `shipped_at` and writes atomically. `--registry`
    defaults to the repository's `builds.json`; the recorded run below used a scratch copy.
  - `check [--root PATH]`: validates `builds.json` (the planner's rules plus unique commits), then
    `os/manifest/release.json` and every `os/manifest/releases/**/*.json`. No `control` object: an info line. A
    `control` object must be exactly `{"source_revision": <40 hex>, "chrome_build": <64 hex>}` with
    `source_revision` equal to the manifest's `source_commit`; `release.json` needs an equal row; a release under
    `releases/` needs an equal row only if one is kept. Exit 1 with `FAIL:` lines, else `record_build check passed`.
- `control/chrome/ci/records/test_record_build.py` (21 tests, synthetic repositories and checkouts in temporary
  folders): `add` records what that commit's own `build.py` prints over its archived tree (the test archives and
  runs it itself); a commit with another `build.py` keeps its own algorithm, not the checkout's, and uncommitted
  changes don't count; wrong `--expect`; a repeated commit (unchanged file) and a conflicting row (refused); pruning
  to three, added out of order; a later commit with the same build; bad commits, times, `--expect`, a commit
  without `control/`; invalid registries; what `add` writes passes `qualify.plan`; the command line. `check`: with
  a row, without one, with an unequal one, no `control` object, malformed objects (in `release.json` and in
  `releases/`), `source_revision` against `source_commit`, `releases/**` (kept equal, kept unequal, missing,
  a subfolder), an invalid registry, a missing or non-object `release.json`, exit codes, and this checkout.
- `.github/workflows/control-chrome-records.yml`: pull requests touching `os/manifest/release.json`,
  `os/manifest/releases/**`, `control/chrome/builds.json`, `record_build.py`, `control/chrome/ci/records/**` or the
  workflow itself; `contents: read`, no secrets, `persist-credentials: false`, ubuntu-24.04's own `python3`; the
  tests, then `record_build.py check` on the checkout.
- `builds.json` is unchanged (`{"format":1,"builds":[]}`).

**The recorded run (run, on the laptop, into a scratch copy of `builds.json`):** 18c's head is reachable
(`origin/pkg/18c-image`).
```
$ python3 control/chrome/record_build.py add --commit 84f45c28fc20a21bf4882de8eb9fe83b94414798 \
    --shipped-at 2026-11-15T12:00:00Z --expect ccd0fd79190f492dbb0ca9889a288c0c004e0d46da3458e0f4446c80b5f5ce15 \
    --registry <scratch>/builds.json
{"commit":"84f45c28fc20a21bf4882de8eb9fe83b94414798","build":"ccd0fd79190f492dbb0ca9889a288c0c004e0d46da3458e0f4446c80b5f5ce15","shipped_at":"2026-11-15T12:00:00Z"}
record_build: recorded
```
exit 0. The same commit again: `already recorded; builds.json unchanged`, exit 0; with `--expect aaaa…`:
`refused: commit 84f45c28… hashes to ccd0fd79…, not the expected aaaa…`, exit 1. `qualify.plan` accepts the
scratch file. `check` on the checkout prints an info line for `release.json` and `releases/06.json`, `13.json`,
`27.json` (none has a `control` object yet) and `record_build check passed`.

### Local tests (laptop, Python 3.14.8)

- `python3 -B -m unittest discover -s control/chrome/ci/records -p 'test_*.py'`: `Ran 21 tests`, `OK`.
- `PYTHONPATH=control:control/chrome_tests python3 -B -m unittest test_excluded_sites_placeholder test_exclusions
  test_build test_extension_stores_nothing test_unit`: `Ran 19 tests`, `OK`.
- `CiInstall` on the `prepare.mjs` before the fix: `FAILED (failures=3)`.
- Three mutants of `record_build.py` (the checkout's `build.py` instead of the commit's; no pruning; `check` not
  comparing the build) each fail tests; not committed.
- `python3 -B control/chrome/build.py`: `2acd63cbc4ae0ec273e82f700a4a8afdfa7288f191706a848c9091b64636c6ec`
  (unchanged by 1b).
- **Not run locally:** `prepare.mjs` itself (no node, no container): the Control Chrome run below is its proof.

### CI runs (started by the push of `9302528d`; nobody waited for them)

1a's other runs on `265caa52` were green: Control Chrome qualification 43705955046, Control base 43705955015,
Control Mail 43705954960, Control boundary 43705954998.

| Run | Workflow | What to look for |
|---|---|---|
| 43716630045 | Control Chrome | `latency (plain)` and `latency (audit)` green (Part A); the 3 `CiInstall` tests in the python shards |
| 43716630095 | Control Chrome records | first run of the 21 tests and `check` on GitHub |
| 43716630048 | Control Chrome qualification | |
| 43716630066 | Control base | |
| 43716630101 | Control Mail | |
| 43716630097 | Control boundary | |

### What the code doesn't show (1b)

- `record_build.py` needs Python 3.12 or later (tarfile's `data` filter) and `git` on `PATH`. The commit must be
  in the clone: a release job with `actions/checkout`'s default depth of 1 has its own commit, so
  `add --commit "$GITHUB_SHA"` works there without fetching history.
- `add` runs the archived `build.py` as a script with `-I -B` in a temporary folder that is removed afterwards;
  nothing is written into the repository but `--registry`.
- The python shards of `Control Chrome` pick up `CiInstall` (every `control/chrome_tests/test_*.py`); nothing but the
  records workflow runs `control/chrome/ci/records/`.

### Left, in order

1. **Read the runs above.** If a latency leg still fails, its `tool.jsonl` artifact names the refusal.
2. **2** the install proof in the container. First thing: run `test_pack.py` and `pack-crosscheck.test.mjs` there.
   They have run nowhere on GitHub yet, and the node test has never run at all.
3. **3a, 3b, 4 (4b), 5, 6** as the brief's "Steps" lists them. 3a waits for PR #58 on `main`, the lead's go and
   the owner's answer to question 5.

### JUDGMENT-CALL (1b)

1. **Part A asks the runtime for its path** instead of writing the list at both paths. Two paths would leave a
   list at the old `/etc` path in every container of current code, so a `SETTING` moved back to `/etc` would
   still pass every browser run. Cost: `prepare.mjs` (an existing file under `control/chrome/ci/`, which the brief
   lets this package change only on item 1's path lines) changed on those three lines plus two imports, on the
   lead's instruction. The test went into this package's new `test_excluded_sites_placeholder.py`, not the existing
   `test_latency.py`, for the same rule.
2. **`add` archives `control/` only**, not the whole tree (about 980 MB at HEAD). Every version of `build.py` so
   far hashes only paths under `control/` (`ROOT/'control'`). A later `build.py` that reads outside `control/`
   would need the archived paths widened (one line).
3. **A repeated commit with an equal hash is a no-op** (exit 0, the first `shipped_at` stays), so a rerun release
   job passes; with another hash it is refused.
4. **A later commit with the same build takes over that build's row** (with its own commit and time). The planner
   (`qualify.plan`) refuses a build named twice, and a release that changed nothing under `control/` hashes the
   same as the one before. Refusing would fail every such release; two rows would break qualification. The older
   release then has no row, which `check` allows for `releases/`.
5. **A row older than the three newest is refused**, not added and pruned at once in silence.
6. **`--shipped-at` is strictly `YYYY-MM-DDTHH:MM:SSZ`** (no fractions, no offsets), and must be a real time.
7. **`check` is a little wider than item 4:** `source_revision` must equal `source_commit` in `releases/` too; it
   reads `releases/` recursively; a missing or non-object `release.json` and an invalid `builds.json` fail.
8. **The workflow** runs on pull requests against any base (no branch filter) and on its own path too;
   `pull_request` only, as item 4 says.
9. **`builds.json` layout:** one row per line, newest first, so the pinning pull request shows its row as one
   line; the empty file stays byte for byte as it is.

### PLAN-GAP (1b)

- **The latency pair wasn't in the brief's picture.** It runs the current harness over main's runtime
  (`ab7aba92`), so a path the harness writes and the runtime reads can't simply move in the harness. 1a moved the
  list as the brief said and the historical leg broke. Any later change of that kind (the policy or host paths in
  steps 2 and 3a, if CI's install follows them) meets the same.
- **"That commit's tree"** in item 4 would be about a gigabyte per `add`; see JUDGMENT-CALL 2.
- **Item 4 leaves open** a repeated commit and the same build under a new commit; decided in JUDGMENT-CALLs 3 and 4.
  `linux-aresos`'s release job should run `add` once per release and may rerun it.

## Step 1a

### Done

**1a. Packer, templates, pins** (item 1; `control/` only, nothing under `os/` or `docs/design/`)

- `control/chrome/packaging/pack.py`: `python3 pack.py EXTENSION_FOLDER OUTPUT_FOLDER` writes `extension.crx`,
  `update.xml`, `policy.json`, `native-host.json` (each 0644) and prints the public record as one JSON line
  (`id`, `version`, `public_key_sha256`, `crx_sha256`, `payload`). As a module: `pack.pack(folder)` returns
  `(files, record)`, `pack.write(folder, output)` returns the record; `pack.payload(folder)`,
  `pack.version(folder)` and `pack.render(id, version)` need only the standard library (for `check-image.sh`).
- Templates: `policy.json` is `ExtensionSettings` alone with the four keys; `update.xml` has the placeholder
  `EXTENSION_VERSION`; `native-host.json` is unchanged (it already had one origin and the fixed launcher).
- `control/chrome/ci/install/test_pack.py` (10 tests) and `pack-crosscheck.test.mjs` (the node cross-check).
- `control/chrome_tests/test_extension_stores_nothing.py`: the storage pin.
- `exclusions.py`: `SETTING` is `/var/lib/aresos-control/chrome-excluded-sites.json`, and the refusal has the
  brief's exact text. `prepare.mjs` lines 32 to 34 and `test_exclusions.py` line 13 follow the path. Nothing
  else in the service changed.
- `control/chrome/packaging/aresos-control-chrome.tmpfiles`: the two agreed lines with a comment.
- `control/chrome_tests/test_excluded_sites_placeholder.py`: the tmpfiles lines, the placeholder refused, the
  empty list accepted, the unit unable to write the folder, and the sweep over the 31 Chrome tools.
- `control/chrome/packaging/README.md`: the paragraphs item 1 names.

`python3 control/chrome/build.py` prints `2acd63cbc4ae0ec273e82f700a4a8afdfa7288f191706a848c9091b64636c6ec` at
`0fc242e7` (the brief expected it to change: `packaging/` and `exclusions.py` are hashed).

### What the code doesn't show

- **Signing uses Python's `cryptography`**, imported inside `_sign_with_fresh_key` only. The container of
  `control/chrome/ci/Dockerfile` (Debian bookworm) has `python3` without it: step 2's workflow installs the
  distribution package `python3-cryptography` (no pip). The calls used exist since `cryptography` 3.1.
- **Run `pack.py` without `-S`**: `-S` hides site-packages and with it `cryptography`. 18c's `os/build.sh` runs
  `build.py` with `-I -B`, which is fine for `pack.py` too.
- **`pack.py` never overwrites.** It refuses an output folder that already holds one of the four files. Bundles
  A, B and C each go into a folder of their own and are copied from there.
- **The image check needs a reader of its own** for `extension.crx` (the installed tree has no `pack.py`, and a
  packer shouldn't be checked with itself). `test_pack.py` has one (`fields`, `read_crx`) and the key-scan forms
  (`forms`: raw, hex, base64 and base64url at three alignments) for whoever writes the modulus scan in step 3a.
- **`os/tests` in step 3a** ("no installed file contains `EXTENSION_ID`, `UPDATE_URL` or `CRX_URL`") should also
  name `EXTENSION_VERSION`. `pack.render` already refuses to return a file with any of the four left in it.
- **How the key test works:** it wraps `rsa.generate_private_key` to see the keys the packer makes, then looks
  for p, q, d and the CRT numbers in everything returned, written or left behind. No key is a fixture anywhere.
- **The sweep's prepared operations** are written through the engine's own `reserve`, with the adapter's
  `prepare` replaced (it reads the page, which the gate never allows). The record has the engine's shape that way.
- In today's code the swept tools make **no** bridge call at all; the test allows `ack_steps` and `queued_steps`
  as the brief says and fails on any other, `configure` included.

### Local tests (laptop, 2026-11-15, Python 3.14.8, `cryptography` 50.0.0)

- `python3 -m unittest discover -s control/chrome/ci/install -p 'test_*.py'`: `Ran 10 tests`, `OK`.
- `PYTHONPATH=control:control/chrome_tests python3 -m unittest test_extension_stores_nothing
  test_excluded_sites_placeholder test_exclusions test_build test_unit`: `Ran 16 tests`, `OK`.
- `… -m unittest test_owner_confirm.Policy` (it reads the README): `Ran 7 tests`, `OK`.
- `test_excluded_sites_placeholder` on the code before the change: `FAILED (failures=29)`, as required.
- A packer changed to leave its key as a file in the temporary folder fails
  `test_no_private_key_in_what_is_returned_written_or_left_behind` (tried once, not committed).
- **Not run:** `pack-crosscheck.test.mjs` and every other `*.mjs` (no node on the laptop); the container; the
  full Chrome and Control suites (GitHub runs them). `test_committed`, `test_fault_surface`, `test_sites` and
  `control/tests`' `test_policy_sources`, `test_slim_policy`, `test_unit` were started locally and stopped
  unfinished (slow suites; the laptop is shared): take their result from the GitHub runs below.

### CI runs

Draft pull request **#76**. Started by its first push, on head `265caa52` (queued when this was written; nobody
waited for them, so the next agent reads the results first):

| Run | Workflow |
|---|---|
| 43705955018 | Control Chrome (runs the two new `control/chrome_tests` files and CI's install with the list at its new path) |
| 43705955046 | Control Chrome qualification |
| 43705955015 | Control base |
| 43705954960 | Control Mail |
| 43705954998 | Control boundary |

Nothing on GitHub runs `control/chrome/ci/install/` yet (step 2).

### JUDGMENT-CALL

1. **`cryptography` in the process, not OpenSSL through pipes.** The key lives only in the crypto library's
   memory, is never serialized and is freed after one signature. The pipe route would carry the key's PEM
   through a pipe and into Python bytes that can't be wiped. Cost: the container needs a distribution package
   (above). Changing it later touches one function and changes the build hash.
2. **The policy form** is `ExtensionSettings` alone, as the brief and the lead's answer 7 say. Whether the
   pinned Chrome installs from it is step 2's first case; the fallback in the brief stays open until then.
3. **The placeholder gate and its message** are the brief's, word for word.
4. **The named tools are called too.** The brief only names them. The test also requires each to answer `ok`
   and to reach no page, and requires the two tables to cover the tool list and `chrome_sites`' commands
   exactly, so the list can't go stale in either direction. Stricter than asked; easy to loosen.
5. **The storage pin is a little wider** than the four names: it also catches `navigator.storage`,
   `chrome['storage']` and a `storage` permission in the manifest.
6. **`pack.py`'s refusals beyond the brief:** an output folder that already holds a bundle file; a manifest
   version that isn't one to four numbers (it goes into `update.xml` as it stands); a file name that isn't
   UTF-8. The command also sets the core-file limit to zero, so a crash can't write the key to disk.
7. **The zip** is deflated as `install.mjs`'s is (what CI's Chrome has unpacked since package 17), with the
   time fixed at 1980-01-01 and mode 0644.

### PLAN-GAP

- **Branch name.** The brief's "Rules" say `pkg/18c-b-chrome-image`; the lead's handoff gave
  `pkg/18c-b-chrome`, which is what exists.
- **No runner for `control/chrome/ci/install/` until step 2.** The brief places the tests there so no existing
  suite picks them up, so on GitHub they first run in step 2's workflow.
- **The README names `record_build.py`** one step before it exists (item 1 asks for the sentence now).
- **Other texts still name the old `/etc` path:** `docs/control/TOOLS-HANDOFF.md`, `STATE.md`,
  `briefs/18c-image-test.md`, `reviews/20-chrome/` (history). All outside this package's paths; the lead's.
- **CI's list in the container** now goes to `/var/lib/aresos-control/`, which `prepare.mjs` makes as root
  (0755 by default). `Boundary.read` needs that; only the `control-chrome.yml` run shows it.

### The brief against the code

Nothing in item 1 turned out wrong. Checked: `exclusions.py` lines 8 and 23, `prepare.mjs` lines 32 to 34,
`test_exclusions.py` line 13 and `background.js` lines 869 to 875 are where the brief says; the extension uses
no browser storage; `python-shard.py` picks up every `control/chrome_tests/test_*.py`, so the two new test
files run in `control-chrome.yml` without a workflow change.
