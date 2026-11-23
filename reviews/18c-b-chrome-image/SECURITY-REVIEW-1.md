# Security review 1: package 18c-b, Chrome's browser side in the image (PR #76)

**Reviewer:** Claude Fable 5.2, high effort, 2026-11-21. Fresh reviewer; I did not build this.
**Reviewed:** head `b5091f42` (code head `6d610587`), `git diff origin/main...HEAD`.

**Read:** `AGENTS.md`; `docs/REVIEW.md` "Tools for Claude"; `docs/design/CONTROL.md` section 6 (the bar, how the
tool reaches Chrome, what the extension can do, where Claude may go); the brief from `origin/main` (facts, design,
CROSS-5, the work, Agree, Proof, the security table, Stop and report, Out of scope, both "Changes after review");
`REPORT.md`; `PROGRESS.md` "For the report" and step 6b. In full: `pack.py`, the templates, tmpfiles file, launcher,
`native_host.py`, polkit action, `exclusions.py`, `boundary.py` `read`, the adapter's gate, `confirm.py`,
`qualification.py` `verify`, the unit, the diffs of `os/build.sh`, `os/Containerfile`, `image-checks.sh`,
`check-image.sh`, `check-build.sh`, `check-resolve.sh`, `os-image.yml`, `release_checks.py`, `chrome_image.py`,
`chrome_layer.py`, the test layer's `Containerfile`, both new workflows, `record_build.py` (first half),
`test_excluded_sites_placeholder.py`, `proof.py` (setup and case 4).

**Not read in full (say so plainly):** the two brief reviews (only their findings as the brief's change lists carry
them); `os/ci/control/chrome_actions.py` and `control_vm.py` (targeted reads: flags, password, C5, C7);
`os/tests/*`, `cdp.py`, `netlog.py`, the probe. No artifact downloaded, logs only. No `os/tests` module run.

**Ran** (scratch under `.work/security-18cb/` only):
- In a `git archive` copy: `test_excluded_sites_placeholder` + `test_extension_stores_nothing` (12 OK), `test_pack` (10 OK).
- Logs of both green Control runs (44893168374, 44900848938) and the install proof on `6d610587` (44893166810):
  every PASS line below is present once in each Control run; the two builds carry two different extension IDs.
- `chrome_image.py`'s modulus scan over both downloaded logs: it finds the hex form exactly where the public line
  prints it and nowhere else; no private-key marker in any of the three logs.
- GitHub CLI's published key file fetched over HTTPS: its SHA-256 equals the lock's `source_sha256`; it holds the
  2022 and 2026 keys; `os/keys/github-cli-rpm.pub` holds exactly the 2026 key (`7F38…3325`, one subkey).
- The laptop's own `gh` 2.103.3 (installed by another route) has the lock's `binary_sha256`.
- `gh` telemetry probe with `GH_TELEMETRY=log` (prints, sends nothing): finding 1.
- Housekeeping: two probes left a file outside scratch (a bytecode file under `os/ci/control/__pycache__`, and
  `gh`'s device id in the session's working folder outside the repo). Both removed; `git status` shows no change.

## Findings

No BLOCKER and no SHOULD-FIX. Six NITs.

1. **NIT. The service's `gh` sends GitHub's usage telemetry.** `control/aresos_control/chrome/qualification.py:104`
   gives `gh` only `PATH`, `LANG` and two XDG folders. The pinned binary, run that way, emits a
   `command_invocation` event for `gh attestation verify`: command, flag names, OS, architecture, version, a device
   id and the time. No repository, path, account or host. `gh --version` sends none. With no `HOME` or
   `XDG_STATE_HOME`, `gh` writes its device id relative to the working directory; in the unit that is `/`,
   read-only, so nothing lands on disk. Harm: one pseudonymous ping per record refresh, beside the anonymous API
   fetch the service already makes. Low. The file is hashed and outside this package's paths: when it is next
   touched, add `GH_TELEMETRY=false` (and an `XDG_STATE_HOME` under the cache); until then a KNOWN-LIMITS line.
2. **NIT. Case 4 and C5 don't pin why Chrome refused.** `control/chrome/ci/install/proof.py:815`,
   `os/ci/control/chrome_actions.py:1529`: one bit flipped in the middle of the archive, inside compressed data.
   A ZIP checksum would catch that too, so "not installed" alone would also pass on a Chrome that skipped the
   signature. The evidence shows it is the signature: run 44893166810 line 2288,
   `Package is invalid: 'CRX_SIGNATURE_VERIFICATION_FAILED'`. Asserting that string in the container case would
   make it a pinned test. No harm either way: the package is root-owned under `/usr`, so the signature is not
   the trust boundary.
3. **NIT. The negative check doesn't name the test folders.** `os/ci/control/chrome_image.py:293-308` catches the
   probe's policy file, its host manifest and anything extra in the bundle folder, but not
   `/usr/share/aresos-install-test` or `/usr/libexec/aresos-install-test` (bundles B and C, the probe's host).
   They can't reach a release by construction (own Containerfile on `localhost/aresos:vm`; the release build
   refuses `ci`) and are inert without their `/etc` files. Two "does not exist" lines would make the brief's
   "no second or third bundle" literal.
4. **NIT. What the modulus scan doesn't see.** `chrome_image.py:126`: raw, hex, base64 and base64url in all three
   alignments (I checked the arithmetic), each also with whitespace removed. Not colon-separated hex
   (`openssl rsa -text`), decimal integers or compressed containers. Fine for a tripwire: the key is never
   serialized, and `test_pack` checks the private numbers themselves.
5. **NIT. `format` is compared with `!=`.** `control/aresos_control/chrome/exclusions.py:16` accepts `true` and
   `1.0` as format 1. Only root writes the file and the placeholder's 0 is refused. Leave it (hashed file).
6. **NIT. The list's hash is guessable.** `os/ci/control/release_checks.py:283`, `:345`: a SHA-256 of a short host
   list confirms a guessed host. Fine for the rehearsal's made-up list. A line for the guide or release brief:
   never put that hash of the laptop's real list into public evidence.

## The nine areas

1. **Force-installed extension: holds.** The template is one entry with four keys; `bundle_content` in
   `chrome_image.py` requires that exact JSON, one origin and both fixed `file:` addresses; `owned` and
   `owned_link` require root ownership and no group or world write up to `/`; the managed folder holds exactly
   `aresos.json`. Chrome on Linux has no per-user policy path, so only root can add or replace a policy, and
   `/usr` is the signed image. Run 1 lines 4304-4310. What the owner's user can change is the profile's copy:
   accepted.
2. **Signing key: holds.** `pack.py:168` keeps the key in one function, never serialized, no key input; core
   dumps off (`pack.py:235`); the build runs it as a child with captured output (`os/build.sh:259`), no build
   argument or environment. It runs in the image's last `RUN`, so no later layer can hide a leftover from the
   scan. Release jobs go through `check-build.sh build`, so the scans run on the build that would ship. Lines
   4302-4305, 5001.
3. **Native host: holds.** One generated origin; launcher 0755 root with `env -i`; the relay only frames bytes.
   C3 (line 5776): the probe gets "Access to the specified native messaging host is forbidden", peer UID 1001.
4. **polkit: holds.** The file is unchanged from `main` and installed through the map (`os/build.sh:108`); the
   image's record equals the checkout's ("78 files from 6d610587", line 4995); `pkaction` shows no / no /
   `auth_admin` and the owner annotation (3241-3244); no rule file names it. `confirm.py` (`CACHED`) refuses a
   reused or retained authorization on its own. C7 (5797): cancel stays read-only, the password loosens, the next
   change asks again. polkit counts any process of his user as his session; the password is the control.
5. **`gh`: holds.** Pinned URL and bytes, NEVRA, no scripts or triggers, header signature by the pinned
   fingerprint with every line OK, key list equal before and after (`os/build.sh:538`), only `./usr/bin/gh`
   through `cpio` to a pipe, binary hash; not in the RPM database, no repository (2948-2951, 3712). The unit starts
   with `env -i` (`control/packaging/aresos-toold.service:13`), so no token reaches it; C10 (5780): no
   credentials, `auth status` exit 1. `PATH=/usr/bin:/bin`: only root could substitute a binary.
6. **Excluded-sites gate: holds.** `adapter.py:204-209`: the list is read before `configure` and before any
   page call. The sweep's two tables equal the tool list in both directions at this head, so a new tool fails
   it. Folder root 0755 outside `ReadWritePaths`; the unit file is untouched. tmpfiles `f` writes only a missing
   file (image check runs it twice, 4946; C6 reboots). An older image reads the `/etc` path no image ships and
   has no host manifest: closed twice.
7. **Test-only pieces: hold** (finding 3). CI flags live in `chrome_actions.py` only; the daily-profile starts
   assert none of them (`chrome_actions.py:789-791`).
8. **`os/` changes: nothing new that listens or grants.** No unit, listener, sudo or polkit rule, repository or
   kept key; no sandbox line touched. The labwc change moves the same two commands into one `RUN`; the first
   `FROM` is still the pinned base.
9. **Privacy: clean.** All 11,629 added lines scanned: no owner name, hosts only under `.invalid`, `.test`,
   `.example`, `localhost` or public Google and GitHub, home paths only `/home/owner`. The guest password is
   random per run, sent as a hash, typed over QMP, and the evidence is scanned for it.

## Known limits

**Accepted** (as the brief and KNOWN-LIMITS settle them; not re-raised): the profile's installed copy is
user-writable; a same-named host in his home; a same-user process posing as the host, raising a nuisance dialog
or holding the one connection; another policy-installed extension switching ours off until restart; a later
`ExtensionSettings` file from root replacing ours (fails closed); section 7's direct calls, own hooks and relayed
requests; an empty list opening the tools (his dashboard's host is the live sitting's job). Plus findings 1 and 4
as limits until fixed.

**Not accepted:** none.

**Open before a release, not before this merge** (already recorded by the builder and lead):
- The next release's rehearsal must name the Chrome checks itself: `os/ci/release28_walk.py:76` lists only the
  five service checks, and `chrome_other_ids` has only run on synthetic trees.
- A real update and `previous` with Chrome open, and the three list hashes.
- The profile pin of 28b is not in this tree; its combined proof gates any release that carries it.
- The live sitting: his list with the dashboard's host first, his real polkit agent, the question at his
  terminal size.

SAFE
