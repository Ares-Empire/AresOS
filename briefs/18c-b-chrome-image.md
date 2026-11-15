# 18c-b: Chrome's browser side in the image

Board #223, #224, #285, #200 and the Chrome lines of #150. A frozen task for one builder, in steps. Parent:
`briefs/18c-image-test.md` (its Part C, which this brief replaces; that text stays as history) and
`briefs/18c-image-start.md` (the amendment that moved `gh` here; on `pkg/18c-image` until PR #58 merges).

**Base.** This package builds on the image part of 18c (branch `pkg/18c-image`, draft PR #58), which merges first.
Steps 1a, 1b and 2 change only `control/` (and add two small workflows) and start on `main`. Nothing under `os/`
starts before PR #58 is on `main` **and** the lead has told `linux-aresos` the changes after review 1 (the
placeholder's `format` 0, the release manifest's `control` key). "Agree with `linux-aresos`" holds its answers of
2026-11-15; where older text in this brief differs, that section wins.

## Goal

The AresOS image carries everything Chrome needs for Claude's Chrome tools: our extension, installed by Chrome's own
policy from a file inside the image; the native-messaging host that connects it to the tool service; the polkit
action behind "Allow editing" and "don't ask again"; the owner's excluded-sites list, made at first boot as a
placeholder that holds every Chrome tool back until he has written his list; and `gh`, which checks the
qualification records. After an update or a rollback the browser side belongs to the booted image again without
anyone touching it. A throwaway CI image proves all of it in the CI virtual machine, on the Chrome the image ships.

**What the owner will see once a release carries it:** Chrome opens with a pinned "AresOS Chrome" button he can't
remove, and Chrome's menu says the browser is managed. Claude's Chrome tools answer "not set up yet" until he writes
his never-list once with `sudo` in the live sitting (an empty list if he has no site to exclude; "For his guide"
below). After that they work, and keep working after an update or going back a version without another step.
"Allow editing" asks for his password in the usual dialog.

## Why now

The Chrome tool is on `main` (PR #27, 2026-11-14), and 18c's image part ships the service with Chrome's two startup
files but nothing of the browser side: `aresos chrome tabs` answers `chrome_unavailable` in every image. No release
with the tools can reach the laptop, and his live test (Mail, then Chrome) can't start, until this is in the image.
The design was settled on 2026-11-14 (`docs/control/TOOLS-HANDOFF.md`, row "Brief 18c-b";
`reviews/18c-b-chrome-image/RESEARCH.md`).

## Model

- **Builder:** a Claude agent. **Fable 5.2** for steps 1a, 2, 3a and 3b (the signing key and the packer, the install
  proof on a real Chrome, and the image install with the signature-checked download): security-sensitive install
  work whose design is settled only in outline, where a wrong first cut costs review rounds. **Opus 5.5** for step 1b
  (`record_build.py`, a small tool against a tight rule) and steps 4 to 6 (VM checks against this brief's lists, the
  kind of work Opus did in one go in 18c's B2). Move a step to Fable when it has resisted two rounds; the likely one
  is driving the password dialog in step 5.
- **Reviews (the lead's job):** a package review and a high-stakes security review by fresh reviewers
  (`docs/REVIEW.md`, "Tools for Claude"): the package force-installs an extension that can drive every page, adds a
  native host, a polkit action and a downloaded binary, and makes a key in CI.

## Read first

- `AGENTS.md`, `docs/WORKFLOW.md`, and `CLAUDE.md`'s "Builders work in steps".
- `reviews/18c-b-chrome-image/RESEARCH.md`: the install routes, what the signing key means, updates and rollback.
- `control/chrome/packaging/README.md` and every file beside it; `control/chrome/build.py`;
  `control/chrome/native_host.py`; `control/checks/17-chrome/install.mjs` (`pack`, `idFor`: the CRX3 container CI
  uses today); `control/chrome/ci/prepare.mjs`, `browser.mjs` and `Dockerfile` (how CI installs and starts Chrome).
- `control/aresos_control/chrome/`: `adapter.py` (`__init__`, `mode`, `maintenance`, `sites`), `qualification.py`
  (`verify`, `refresh`), `exclusions.py`, `confirm.py`, `policy.py` (`FIXED_HOSTS`), `bridge.py` (`accept`);
  `control/aresos_control/boundary.py` (`Boundary.read`); `control/packaging/aresos-toold.service`.
- `docs/design/CONTROL.md` section 6 ("How the tool reaches Chrome", "Where Claude may go"; on
  `origin/briefs/28-chrome-capability` until PR #48 merges, where the lead wrote this brief's install text and gate);
  `docs/control/TOOLS-HANDOFF.md` ("Chrome merged", "For `linux-aresos`"); `reviews/20-chrome/KNOWN-LIMITS.md` (the
  three residuals about a process posing as the native host); `reviews/20-chrome/QUALIFICATION.md` (the
  `builds.json` row format).
- From 18c (on `main` once PR #58 merges; until then `git show origin/pkg/18c-image:<path>`):
  `reviews/18c-image-test/PROGRESS.md` ("Chrome follow-up", "For 18c-b", "The `os/` diff for `linux-aresos`"),
  `os/build.sh` (modes `packages`, `control`, `control-tree`), `os/ci/image-checks.sh`, `os/ci/check-image.sh`,
  `os/ci/control/` (all of it), `os/ci/check-build.sh`, the `check-build` job in `.github/workflows/os-image.yml`.
- `os/config/usr/libexec/aresos-shell` (`command()`: how an app is started) and
  `os/config/usr/share/aresos/apps/browser.json`.

## Facts this brief rests on

Read on 2026-11-15: `main` at `62e1abb3`, `pkg/18c-image` at `84f45c28`; the laptop runs release 27 on the image's
pinned base, so its `/usr` shows what the base has. Check each one in the tree before you rely on it.

- **The image ships Google Chrome stable**, `google-chrome-stable-157.0.8103.50-1.x86_64`
  (`os/google-chrome.lock.json`): Google's RPM by pinned URL, SHA-256 and signing key, installed under
  `/usr/lib/opt/google/chrome` with `/opt/google` linked to it at boot, no repository and no updater of its own. It
  is the branded build, so it reads machine policy from `/etc/opt/chrome/policies/managed/*.json` and system native
  hosts from `/etc/opt/chrome/native-messaging-hosts/`. Package 21's image check makes the policy folder and removes
  it again with `rmdir` (`image-checks.sh` on `pkg/18c-image`, about line 281, "/etc/opt/chrome/policies can be
  created for the control layer"); with our link inside, that `rmdir` fails. Step 3a replaces that check with the
  policy-folder check of "Proof", which pins more (not a weakened test). The base ships `native-messaging-hosts/`
  with one file of KDE's; ours goes beside it.
- **The base has** `/usr/bin/pkcheck` (polkit 127), `rpmkeys`, `rpm2cpio` and `cpio` (rpm 6.0.2), OpenSSL 3.5.9
  and Python's `cryptography` 50.0.0. It has **no** `node` and no `gh`. The session starts KDE's polkit agent
  (`labwc/autostart`; an image check pins it).
- **18c installs** the service tree, `chrome/qualification.json` and `chrome/build-id.json` (from
  `control/chrome/build.py` over the commit's `control/`), all through one install map in `os/build.sh` (`TREES`,
  `FILES`, `DERIVED`) recorded in `/usr/share/aresos/manifest/control.json`. `check-image.sh` rebuilds that record
  from the checkout (`build.sh control-tree`) and requires the image's to be equal. Everything is `root:root`; the
  map has no way to set a group.
- **`build.py` hashes** `control/chrome/packaging/` and `control/chrome/extension/` with the rest of the runtime
  inputs. `builds.json` and `qualification.json` are not inputs. On 18c's head with 18e merged it prints
  `ccd0fd79190f492dbb0ca9889a288c0c004e0d46da3458e0f4446c80b5f5ce15`; any later change under those folders, this
  package's included, changes it.
- **The service calls `gh` by name** with `PATH=/usr/bin:/bin` and refuses a version below 2.102.0
  (`qualification.py`, `verify`). A refresh runs only after a native host has connected and named Chrome's version
  (`adapter.py`, `maintenance`). Fedora 44 has `gh` 2.97.0. GitHub's release RPM `gh_2.103.3_linux_amd64.rpm`
  (15672051 bytes, SHA-256 `65d55875faa3281959676d91da15a9380583281586ac31bbd3d32b7924a9f4d2`, header signed with
  key ID `5612b36462313325`, no scripts) requires `git`, which the base lacks (18c step 1). Its file list showed no
  licence file.
- **The excluded-sites file is the owner's list only.** The built-in never-list is code: `FIXED_HOSTS` in
  `policy.py` (`claude.ai`, `console.anthropic.com`, `platform.claude.com`). `exclusions.py` reads its path from the
  constant `SETTING` (line 8, `/etc/aresos/control/chrome-excluded-sites.json`; no configuration value) through
  `Boundary.read`: every folder and the file root-owned, not group- or world-writable, **a regular file, never a
  link**. A missing or unsafe file, or one that isn't `format` 1, refuses every Chrome read and action with
  `chrome_settings_unavailable` (line 23; while Chrome isn't connected, `mode` answers `chrome_unavailable` first).
  The service reads it on every call. **`chrome_sites` doesn't manage this list:** its `list`, `readonly`, `allow`
  and `revoke` keep his read-only sites and "don't ask again" entries in the service's store. Only root changes the
  list. The unit writes only `/run/aresos-tools`, `/var/lib/aresos-tools` and
  `/var/lib/aresos-operation-evidence` (`ReadWritePaths` under `ProtectSystem=strict`).
- **The shell starts Chrome** with `systemd-run --user --scope --slice=app.slice -- /usr/bin/google-chrome`. Chrome
  and the native host it starts therefore run under his user manager, not inside the login session's own scope. The
  polkit action allows only an active local session (`allow_active=auth_admin`, the others `no`). Whether polkit
  counts such a process as his active session is unproven (`control-chrome-polkit.yml` used a CI-only rule instead
  and left this to 18c-b).
- **The extension keeps nothing in the browser:** no `chrome.storage`, IndexedDB, `localStorage` or
  `sessionStorage` in `control/chrome/extension/`. A new extension identity therefore loses nothing.
- **Test group 12** (the managed ask on `chrome_submit`) already runs in 18d's container harness on `main` (job
  `native-precedence` in `control-chrome.yml`). It is not part of this package.

## The design, as settled

- **Installed by policy from a file.** Chrome force-installs the extension from an update manifest at a `file:`
  address under `/usr`. Nothing is published, no web store, no listener, no certificate.
- **A fresh signing key per image build, thrown away.** Each image build makes a new RSA key, signs the package and
  forgets the key. The extension's ID is the hash of the public key, so every image has its own ID; the policy, the
  update manifest and the native host's allowed origin are generated together from it. No secret is stored anywhere.
- **`/etc` holds only links.** The two files Chrome looks for in `/etc` are links to files under `/usr`. The links
  never change, so `/etc`'s per-deployment merge has nothing to get wrong, and an update or rollback swaps the real
  files with the image.
- **Accepted with it:** after an update Chrome removes the old extension and installs the new one; anything the
  extension stored in the browser would be lost (it stores nothing, and item 1 pins that).
- **Not reproducible, on purpose.** Two builds of one commit give different `extension.crx`, ID and generated files
  (a fresh key each time). What is compared instead: the packed files (`payload`, names and SHA-256) equal the
  commit's extension files, the generated files equal the templates rendered with the recorded ID, and
  `chrome_build`, `gh` and `links` equal the checkout's; everything else in `control.json` stays reproducible.
- **His never-list starts refused.** The image can't carry his hosts (the repo is public), so tmpfiles makes the
  list at first boot as a placeholder the existing validator refuses. Until he writes a `format` 1 list as root (an
  empty one counts), every Chrome read and action answers `chrome_settings_unavailable`. The list lives in `/var`,
  shared by all deployments, so updates and `previous` keep it; the service can never write it.

## The work

### 1. The packer and the templates (`control/` only)

- **`control/chrome/packaging/pack.py`** (new): builds the signed package and the three generated files in one
  call, with no browser and no `node`. It packs in two places: the image build (the pinned base) and item 2's
  container, where its unit tests and the `node` cross-check also run (files under `control/chrome/ci/install/`, so
  no existing suite picks them up). Use what the base image has (`cryptography`, or OpenSSL through anonymous pipes)
  and check what the container has before you choose; item 2's workflow may install a distribution package for it,
  but no pip dependency is added. Rendering the templates and listing the payload need only the standard library,
  because `check-image.sh` uses them on the runner. It
  - makes an RSA 2048 key from the system's random source, **inside its own process** (or in a child it talks to
    only through anonymous pipes);
  - writes a CRX3 package of `control/chrome/extension/` in the container format of `install.mjs`'s `pack` (one RSA
    proof, the signed header carrying the 16-byte ID), with the files in sorted order and fixed timestamps; it
    refuses a link or anything but a regular file or folder there, as `build.sh`'s `TREES` loop does;
  - derives the ID as `idFor` does and renders the templates with it;
  - returns the files' bytes and a public record: `id`, `version` (from `manifest.json`), `public_key_sha256`,
    `crx_sha256` and `payload` (each packed file's name and SHA-256).

  The private key is never returned, written to a named file, printed, logged, put into the environment or a
  command line, or passed in as a build argument or secret. There is no "use this key" input.
- **Templates** in `control/chrome/packaging/`:
  - `policy.json` becomes `{"ExtensionSettings":{"EXTENSION_ID":{"installation_mode":"force_installed",
    "update_url":"UPDATE_URL","override_update_url":true,"toolbar_pin":"force_pinned"}}}` and nothing else: no `*`
    entry, no other policy key. If the pinned Chrome doesn't install from this form, the allowed fallback is
    `ExtensionInstallForcelist` with the same address plus `ExtensionSettings` for the pin and the override; record
    it as a JUDGMENT-CALL.
  - `update.xml` takes its version from the extension's `manifest.json` instead of a literal.
  - `native-host.json` keeps exactly one allowed origin, `chrome-extension://EXTENSION_ID/`, and the fixed launcher
    path. No wildcard, no second origin.
  - Fixed values for the image: `UPDATE_URL` is `file:///usr/share/aresos/chrome/update.xml`, `CRX_URL` is
    `file:///usr/share/aresos/chrome/extension.crx`.
- **Pin "stores nothing":** a test that fails when the extension's sources start using `chrome.storage`, IndexedDB,
  `localStorage` or `sessionStorage`, with a message that points here: a per-image identity drops such data at
  every update, so that change needs the owner's decision first.
- **The excluded-sites list moves to `/var` and starts refused** (the only change to the service, and to its tests
  and CI, that this package makes):
  - `control/aresos_control/chrome/exclusions.py`: `SETTING` (line 8) becomes
    `/var/lib/aresos-control/chrome-excluded-sites.json`, and the refusal's message (line 23) becomes exactly
    `Chrome refuses reads and actions: its owner-only excluded-sites setting is not set up yet, or is missing,
    unreadable or unsafe; ask the owner to set it up.` Today's text ("… missing, unreadable or unsafe; ask the owner
    to install it.") would send him looking for a broken install in the normal first-use state. The code, the
    error code and every other line stay.
  - `control/chrome/ci/prepare.mjs` lines 32 to 34 and `control/chrome_tests/test_exclusions.py` line 13: the new
    path, nothing else.
  - New `control/chrome/packaging/aresos-control-chrome.tmpfiles`, exactly the two agreed lines ("Agree", answer 2)
    with a comment. Step 3a installs it through `FILES`.
  - New `control/chrome_tests/test_excluded_sites_placeholder.py`: the `f` line's path equals `SETTING`; its
    argument (the placeholder) is refused with `chrome_settings_unavailable` and the new message;
    `{"format":1,"hosts":[]}` gives `[]`; the `d` line is `root root 0755` and the `f` line `0640 root aresos-tools`;
    no `ReadWritePaths` entry or `StateDirectory` of `control/packaging/aresos-toold.service` is
    `/var/lib/aresos-control` or above or below it. Fails on today's code.
  - If the gate needs more than these lines in the service, stop and report.
- `control/chrome/packaging/README.md`: replace the HTTPS-endpoint and production-key paragraphs, the "Copy all …
  into the installed service tree" paragraph (the installed tree holds no template copy; say what 18c's install map
  and this package install), the excluded-sites paragraph (new path, the placeholder, root writes a `format` 1 list,
  an empty one counts) and the "manual handoff" sentence (now `record_build.py`) with what this package builds.
  `pack.mjs` and CI's own install stay as they are.

### 2. The install proof on a real Chrome, in a container first

The VM costs about 50 minutes a run, so the Chrome side is developed where a run takes minutes and stays there as
the check on every pull request that touches `control/chrome/packaging/` or `control/chrome/extension/`.

- A small workflow of its own, `.github/workflows/control-chrome-install.yml` (read-only, no secrets), on the
  container of `control/chrome/ci/Dockerfile` with Chrome at the image's pinned version if Google still serves that
  package (pin its URL and SHA-256; otherwise current stable of the same major, recorded). New files only, under
  `control/chrome/ci/install/`. Chrome starts as `browser.mjs` starts it: never `--no-sandbox`,
  `--remote-debugging-*`, `--load-extension` or `--disable-extensions-except`.
- The layout is the image's: the four files under `/usr/share/aresos/chrome/`, the two links in `/etc`, the host and
  `native_host.py` in `/usr/libexec/aresos-control/chrome/`, CI's service on `chrome.sock`
  (`control/chrome/ci/service.py`, used as it is), and a valid made-up list at the excluded-sites path.
  `pack.py`'s unit tests and the `node` cross-check run in this workflow (`control/chrome/ci/install/`).
- **A probe extension** (test only): a second extension with its own key, `nativeMessaging` and `management`
  permissions and its own test-only native host that writes down what the probe reports. It gives the checks a way
  to ask Chrome questions without a debugging port. It is installed by `ExtensionInstallForcelist` in a policy file
  of its own, from a `file:` address of its own, and that file sets no other key: Chrome takes each policy key from
  one file only (the last in name order wins, nothing is merged; `config_dir_policy_loader.cc`), so a second
  `ExtensionSettings` would remove ours or be ignored. Its manifest's `update_url` is a `localhost` address the
  test serves, so its update checks show in the network log (case 5).
- Cases:
  1. **Install.** A fresh profile, no network: Chrome installs our extension from the `file:` address through the
     links, enabled and pinned. The probe's `management.get` reports it as installed by policy and not disableable;
     its `setEnabled(false)` and `uninstall` are refused.
  2. **The host trusts one origin.** Our extension reaches the stand-in service through the host. The probe's
     `connectNative('org.aresos.chrome')` is refused by Chrome, and the service sees no connection from it.
  3. **Update and back, same profile.** Bundle A, then bundle B (same sources, a second key) at the same paths, then
     A again, Chrome restarted each time. After each switch: only the current ID is installed, the previous one is
     gone from the profile, the current extension connects, the probe is still refused, and with B's files in place
     an origin of A's would not match (assert from the manifest's bytes).
  4. **A broken package.** On a fresh profile (one that never held this ID; Chrome reads the package of an
     installed extension only for a higher version): with one byte of `extension.crx` changed, and separately with
     the file missing, Chrome doesn't install the extension, ordinary browsing still works, and the tools' answer
     is `chrome_unavailable`. With the file restored the next start installs it. Then the other half, on a profile
     with the extension installed: a changed or missing package leaves the installed copy running and connected.
  5. **Nothing asks the web store about us.** One run with Chrome's network log on
     (`--log-net-log`, `--extensions-update-frequency` short) across at least two update checks: no request to
     anything but a `file:` address names our extension's ID. Positive control in the same log and window: the
     probe's ID appears in at least two update requests (to its `localhost` address), so two checks ran and the
     log would have shown ours.
- Record for the report what case 3 looks like in time: how long after a start the old extension is gone and the new
  one is connected.

### 3. The image install (`os/`, as agreed with `linux-aresos`)

Extend 18c's install map; don't build a second one.

- **Ordering rule** (from `mac-aresos-control`): `build.py` runs on the untouched source tree **before** anything
  is generated, and generated files go only into the destination, never back into the source tree. The installed
  tree holds no template copy. That keeps `chrome/build-id.json` equal to what CI qualifies for the same commit.
- **Deterministic files** (in `FILES`, recorded and compared like every other): the host launcher and
  `native_host.py`; the polkit action; the excluded-sites tmpfiles file. The two `/etc` links join the record's
  `links`.
- **The per-build bundle** (image build only): one call of `pack.py` writes the four files of
  `/usr/share/aresos/chrome/`. `control.json` gains `chrome_build` (the hash, as a value) and `chrome_extension`
  (the packer's public record plus each generated file's mode and SHA-256). The build prints
  `CONTROL_CHROME_EXTENSION <id> <crx sha256>`.
- **The excluded-sites list:** the image ships no file at `/var/lib/aresos-control/` (nor at the old `/etc` path);
  tmpfiles makes the folder and the refused placeholder at boot ("Agree", answer 2). The owner's hosts never appear
  in the repo, a test, a fixture or evidence; he writes his list with `sudo` in his live sitting (board #200; "For
  his guide").
- **`gh`** in `build.sh packages`, beside Chrome's RPM and with the same care:
  - `os/gh.lock.json` ("Agree", answer 4): `os/google-chrome.lock.json`'s field names and order, plus
    `binary_sha256` (`/usr/bin/gh` inside the RPM) and `license_sha256`. Start from 2.103.3 (18c step 1); take a
    newer patch release only for a security fix, and say so.
  - **The key: exactly one.** GitHub's published key file holds two keys: the 2022 key (`2C61 0620 … 7571 6059`,
    expired 2026-09-05) and the 2026 key `7F38 BBB5 9D06 4DBC B3D8 4D72 5612 B364 6231 3325`, which signs 2.103.3
    (key ID `5612b36462313325`). Fetch the published file over HTTPS, compare both fingerprints, and commit only the
    2026 key as `os/keys/github-cli-rpm.pub` (exported with `gpg` in a temporary home, no network). The lock records
    the published file's URL and SHA-256, the committed file's SHA-256, the one accepted fingerprint, and how you
    confirmed it is theirs (answer 8). An `os/tests` test requires that the committed file holds exactly one key
    with that fingerprint.
  - Download over HTTPS; require the pinned bytes and NEVRA; require that the RPM has no scripts; **check the
    signature** with `rpmkeys --checksig` after importing the committed key, requiring the header's signature by
    that fingerprint and every line OK; then delete **every key the import added**: the RPM keyring's key list
    after the step equals the list before it. The verifier is `rpmkeys` of the digest-pinned base image.
  - Take **only** `/usr/bin/gh` out of the RPM (`rpm2cpio`, `cpio`), 0755 `root:root`, and require its SHA-256 to
    equal the lock's. No `rpm -i`, no `--nodeps`, no Fedora `git`, no repository, no completions or man pages.
  - The licence text: the tag's `LICENSE`, committed as `os/config/usr/share/licenses/gh/LICENSE` (the config copy
    installs it at `/usr/share/licenses/gh/LICENSE`), its SHA-256 in the lock; no second download.
  - The resolve check (`check_build=resolve`) prints the newest `gh` release beside the pin as an info line, never
    failing, also when the lookup fails (answer 4).
  - The lock is copied to `/usr/share/aresos/manifest/gh.lock.json`; `control.json` gains `gh` (version and the
    binary's SHA-256, checked against `/usr/bin/gh` at build).
- **Image checks** (`image-checks.sh`): the list under "Proof", including the replacement for 18c's
  make-and-remove check of the policy folder. **`check-image.sh`**: the image's `gh.lock.json` equals the reviewed
  one; `chrome_build`, `gh` and `links` equal the checkout's; `chrome_extension` is consistent with the checkout
  (its `payload` equals the checkout's extension files, and the three generated files equal the templates rendered
  with the recorded ID), so only the key, the signature and the ID differ between two builds.
- `os/README.md`: the Control paragraph says what the browser side adds and why the bundle differs per build.

### 4. `builds.json` is recorded by a tool, not by hand

Today the lead writes each shipped image's row (`commit`, `build`, `shipped_at`) into `control/chrome/builds.json`.

- **`control/chrome/record_build.py`** (new; not one of `build.py`'s inputs):
  - `add --commit <full commit> --shipped-at <UTC time, Z> [--expect <hash>]` computes the hash with **that
    commit's own** `build.py` over that commit's tree (`git archive` into a temporary folder), refuses if it differs
    from `--expect` or from an existing row for the commit, adds the row and keeps the newest three by
    `shipped_at`.
  - `check` reads the release manifests. A manifest carries the Control build as a top-level object
    `"control": {"source_revision": "<40 hex>", "chrome_build": "<64 hex>"}`, copied from the image's
    `control.json`. `os/manifest/release.json` with that object needs a row with `commit` equal to its
    `source_revision` and `build` equal to its `chrome_build`. In `os/manifest/releases/*.json` a row for the same
    commit, if one exists, must be equal (only three rows are kept, so a missing one is fine). A manifest without
    the object (every one today) passes with an info line. A malformed object fails.
- The image already says which build it carries (`CONTROL_CHROME_BUILD` in the build log, `chrome_build` in
  `control.json` after item 3). What the **release** does with it is `linux-aresos`'s part and is not built here
  (see "Agree"): the release job writes that `control` object into its release manifest and runs `add`; the pull
  request that pins the release carries the row; `check` fails that pull request without it.
- `builds.json` stays `{"format":1,"builds":[]}` in this package: no image with the tool has shipped.
- **Tests** (`control/chrome/ci/records/`, not in `control/chrome_tests/`, whose runs have no history and no `os/`):
  `add` on a synthetic repository the test makes (commits with a small `control/` tree and the checkout's
  `build.py`; the expected hash computed by that `build.py` over the archived tree), a wrong `--expect`, a
  repeated commit, pruning to three; `check` with a row, without one, with an unequal one, with no `control`
  object, and on `releases/**`. Once, recorded as **run** in `PROGRESS.md` and not as a unit test, into a scratch
  copy of `builds.json`: `add --commit 84f45c28fc20a21bf4882de8eb9fe83b94414798 --expect ccd0fd79…ce15` (18c's
  head; if it is no longer reachable, say so).
- **Where it runs:** a small new workflow `.github/workflows/control-chrome-records.yml` (read-only, no secrets, on
  the runner) for pull requests touching `os/manifest/release.json`, `os/manifest/releases/**`,
  `control/chrome/builds.json`, `record_build.py` or its tests: the tests, then `check` on the checkout.

### 5. The VM checks (`check_build=control`)

A second pass after 18c's, on the same disk with a fresh overlay: its own step in the `check-build` job, its own
action file in the Control test layer, its own evidence folder `evidence/control/chrome/`. The layer also carries
the probe extension (its own policy file, item 2), its test-only host, a second and a third bundle (B, C) made by
`pack.py`, and a small page server from the standard library (a form page, a receiver that counts what arrives,
and the probe's update address), serving on `localhost` in the guest.

**How Chrome runs in the guest.** As `ares`, in his session, started the way the shell starts it (the shell's own
launch request if the guest's session runs the shell, otherwise the same `systemd-run --user --scope` line with the
session's environment). Record the cgroup of Chrome and of the native host, and `loginctl`'s view of his session.
CI-only additions are limited to `--no-first-run`, `--no-default-browser-check`, `--password-store=basic` and, for
check C9 alone, the two network-log flags; never the four forbidden flags of item 2. The password dialog is answered
through the VM's keyboard (QMP), with a per-run password for `ares` that never reaches the evidence. 18c's SELinux
scan runs again at the end of this pass: a denial naming Chrome's host, the service, `gh` or `pkcheck` fails it.

**The polkit probe comes first in step 4.** A process started in his session with the shell's `systemd-run --user
--scope --slice=app.slice` line is the subject of `pkcheck --action-id org.aresos.control.chrome-loosen --process
… --allow-user-interaction`, run as the service runs it (`aresos-tools`, the unit's sandbox properties). Record
the exit code, the journal and a screenshot; cancel the dialog, don't drive it yet. If polkit answers without
asking his agent, or no dialog comes, stop (see "Stop and report"). C7 drives the dialog in step 5.

| Check | What it shows | PASS line |
|---|---|---|
| C1 files | Every path of "Agree" in the booted guest with its owner, mode and content; the two links are links, equal to `/usr/etc`'s; `/etc/opt/chrome/policies/managed/` holds only ours (plus the probe's file, named, with `ExtensionInstallForcelist` alone); the placeholder after boot: `/var/lib/aresos-control/` `root:root` 0755, the list `root:aresos-tools` 0640 with exactly the tmpfiles argument; nothing at `/etc/aresos/control/chrome-excluded-sites.json` | `CONTROL_CHROME_FILES_PASS` |
| C2 install | Item 2's case 1 on the shipped Chrome in his session; a screenshot of the pinned button and of Chrome's "managed" note for the owner's picture | `CONTROL_CHROME_INSTALL_PASS` |
| C3 host | The extension connects through the installed host to the real service as `ares` (peer UID 1001); `aresos chrome tabs` lists his tabs; one page of the page server is read; the probe is refused; `chrome.sock` shows exactly one host | `CONTROL_CHROME_NATIVE_HOST_PASS` |
| C4 update | Item 2's case 3 in the guest with the same profile: bundle B bind-mounted over `/usr/share/aresos/chrome` (CI only), then removed again. After each switch the host's manifest names the current ID, the current extension connects and reads, the previous ID is gone, the probe is refused | `CONTROL_CHROME_UPDATE_PASS` |
| C5 broken package | Item 2's case 4 in the guest. The fresh half on bundle C, an ID his profile never held (bind-mounted like B): changed, then missing, C isn't installed, browsing works, the tools answer `chrome_unavailable`, Chrome and the service stay up; restored, C installs. The other half on the installed extension: a changed or missing package leaves it running and connected | `CONTROL_CHROME_PACKAGE_FAULT_PASS` |
| C6 sites | **First use, right after C2** (extension connected, nothing else read yet): with the placeholder, `aresos chrome tabs` answers `chrome_settings_unavailable` with the new message; root writes `{"format":1,"hosts":[]}` the owner's way ("For his guide"; owner, group and mode unchanged) and the same command lists his tabs. **Later:** `ares` can neither read nor write the list; as `aresos-tools` under the unit's sandbox properties (`systemd-run`, as C10), writing the list and creating a file in `/var/lib/aresos-control/` both fail; opening each `FIXED_HOSTS` address is refused. With one test host added by root: that host and a subdomain are refused. With the list group-writable, then missing, then the placeholder again: every read refuses `chrome_settings_unavailable`. Restored each time, its hash equal to the one before | `CONTROL_CHROME_SITES_PASS` |
| C7 password | On the details page, "Allow editing" for a test site: the dialog of his real agent appears, a screenshot shows it naming the site; cancelled, the site stays read-only; with the password, it is editable; a second change asks again. From the journal: the action, a one-time authorization, and the subject being the native host's process | `CONTROL_CHROME_POLKIT_PASS` |
| C8 ask | One asking action end to end through 18c's interactive driver: Claude Code as `ares` fills the form page and submits; the prompt shows the service's question; "Yes" gives one arrival at the receiver, "No" none | `CONTROL_CHROME_ASK_PASS` |
| C9 no store | Item 2's case 5 in the guest, with its positive control (the probe's ID in at least two update requests to the page server) | `CONTROL_CHROME_NO_STORE_PASS` |
| C10 `gh` | `/usr/bin/gh --version` equals the lock, as `ares` and as `aresos-tools` under the unit's own sandbox properties (`systemd-run`); the binary's hash equals `control.json`; no login or token in the verifier's folders | `CONTROL_GH_PASS` |
| C11 records | Chrome's record refresh under the real `aresos-toold.service`: with the extension connected, the service fetches once and writes its result line (`aresos log`); the service stays active, no AVC denial, the verifier's cache is under `/var/lib/aresos-tools`. If an attested record is published by then: "Verified record accepted." Otherwise: "refused …; held record retained", plus `verify` run under the unit's sandbox against a public attestation of this repository if one exists (accepted) and against a wrong signer (refused) | `CONTROL_CHROME_RECORDS_PASS` |

C11 is the one check that reads the real network (the public repository and the verifier's trust data); it records
which path it took. The lead's note also names a record refresh of Mail's: `main` has none (the lead's answer 1).

**For the release rehearsal** (it has no test layer and no browser): add checks to `os/ci/control/release_checks.py`
in 18c's style: the two links exist, are links and equal `/usr/etc`'s; the ID in the policy, the update manifest,
the host's manifest and `control.json` is one ID, and the package's signature verifies with its own key (the image's
`openssl`); no other ID under `/etc/opt/chrome`; the excluded-sites list present with its owner, group and mode,
and its SHA-256 printed as `CONTROL_CHROME_SITES_SHA256 <hash>`, which the rehearsal requires to be equal before
the update, after it and after `previous` (the list lives in `/var`; `linux-aresos` wires the comparison in its
release brief); `gh`'s version and hash; the polkit action equal to the record.

### 6. Records and the report

Keep `reviews/18c-b-chrome-image/PROGRESS.md` current after every step (done, left in order, what the code doesn't
show, run IDs). The last step leaves the full report text there under "For the report" (a Claude builder can't
create `REPORT.md`) in `AGENTS.md`'s format, every claim marked **run** (run ID and log line), **read** (file and
version) or **assumed**, with the measured times of the VM pass.

### For his guide (the report carries these lines; the lead puts them in the live-sitting guide)

- **His never-list, once, before Claude's first session in his Chrome.** Until then every Chrome tool answers that
  the excluded-sites setting is not set up yet. With sites to exclude (lowercase host names, no `https://`, no port
  or path; each covers its subdomains; at most 128):
  `echo '{"format":1,"hosts":["first.example","second.example"]}' | sudo tee /var/lib/aresos-control/chrome-excluded-sites.json`
  With no site to exclude, the empty list, which opens the tools just the same:
  `echo '{"format":1,"hosts":[]}' | sudo tee /var/lib/aresos-control/chrome-excluded-sites.json`
  `sudo tee` writes into the existing file, so it keeps its owner, group and mode; the tools read it on their next
  call. Later changes go the same way. Updates and going back a version keep the list.
- A Chrome policy file that sets `ExtensionSettings` and sorts after `aresos.json` in
  `/etc/opt/chrome/policies/managed/` replaces ours, and Chrome removes our extension (it fails closed: the tools
  say Chrome isn't connected).

## Agree with `linux-aresos` (agreed 2026-11-15; changes after review 1 relayed by the lead)

**What:** the image gains Chrome's browser side for the Control tools and `gh`. Built only as throwaway CI images;
whether a release carries it is the release's decision with the owner's OK.

**In the image:**

| Path | Owner, mode | What |
|---|---|---|
| `/usr/share/aresos/chrome/` | `root:root` 0755 | new folder, per build |
| `…/chrome/extension.crx` | `root:root` 0644 | the signed package of the commit's `control/chrome/extension/` |
| `…/chrome/update.xml`, `policy.json`, `native-host.json` | `root:root` 0644 | generated from the templates with the build's ID |
| `/etc/opt/chrome/policies/managed/aresos.json` | link, `root:root`; folders 0755 | → `/usr/share/aresos/chrome/policy.json` |
| `/etc/opt/chrome/native-messaging-hosts/org.aresos.chrome.json` | link, `root:root` | → `/usr/share/aresos/chrome/native-host.json`, beside KDE's file |
| `/usr/libexec/aresos-control/chrome/host` | `root:root` 0755 | `control/chrome/packaging/host` |
| `/usr/libexec/aresos-control/chrome/native_host.py` | `root:root` 0644 | `control/chrome/native_host.py` |
| `/usr/share/polkit-1/actions/org.aresos.control.chrome-loosen.policy` | `root:root` 0644 | `control/chrome/packaging/`; `auth_admin` for an active session, never kept |
| `/usr/lib/tmpfiles.d/aresos-control-chrome.conf` | `root:root` 0644 | `control/chrome/packaging/aresos-control-chrome.tmpfiles` (answer 2) |
| `/var/lib/aresos-control/` | `root:root` 0755 | made at boot by that file; not in the image |
| `/var/lib/aresos-control/chrome-excluded-sites.json` | `root:aresos-tools` 0640 | made at boot when missing, as the placeholder `{"format":0,"hosts":[]}`; a regular file; not in the image |
| `/usr/bin/gh` | `root:root` 0755 | from GitHub's pinned, signature-checked RPM |
| `/usr/share/licenses/gh/LICENSE` | `root:root` 0644 | from `os/config/usr/share/licenses/gh/LICENSE` |
| `/usr/share/aresos/manifest/gh.lock.json` | `root:root` 0644 | copy of `os/gh.lock.json` |
| `/usr/share/aresos/manifest/control.json` | `root:root` 0644, as today | gains `chrome_build`, `chrome_extension`, `gh`, two `links` |

**Paths under `os/` that change:**

1. `os/build.sh`: `packages` gains the `gh` step; `control` and `control-tree` gain the entries above.
2. New: `os/gh.lock.json`, `os/keys/github-cli-rpm.pub` (one key), `os/config/usr/share/licenses/gh/LICENSE`.
3. `os/Containerfile`: no change expected (the `packages` stage already copies `os/`, and `control` already runs
   before `configure`).
4. `os/ci/image-checks.sh`, `os/ci/check-image.sh`: the checks of "Proof". 18c's check that makes and removes
   `/etc/opt/chrome/policies/managed` (its `rmdir` would fail on our link) is replaced by the policy-folder check.
5. `os/ci/control/`: a Chrome action file, the probe extension with its policy file and host, the page server, the
   bundles B and C in `Containerfile`, a Chrome sequence in `control_vm.py`, new checks in `release_checks.py`.
6. `os/ci/check-build.sh`: a `control-chrome-pass` mode beside `control-pass`.
7. `os/tests/test_control_image.py`, `os/tests/test_control_vm.py`; `os/README.md`.
8. The resolve check's script (`check_build=resolve`): the `gh` info line (answer 4).

**`.github/workflows/os-image.yml`** (`check-build` job only; no new permission, secret, input or job):
- one step "Control Chrome VM pass (check_build=control only)" running `check-build.sh control-chrome-pass`, with
  its own `timeout-minutes` (25 to start; then about 1.5 times the slowest green);
- the job's limit for `control` raised by that step's limit (127 to 152);
- the evidence upload unchanged (the new folder is inside it).
Each change is its own commit, recorded with `rebind.py pending` in `os/manifest/ci/16/pending-rebind.json`. **Tell
`linux-aresos` (through the lead) before the first `os-image.yml` commit.**

**Must not change:** the base digest, `packages.lock.json`, the Chrome pin, accounts, sudo, the existing polkit rule
file, unit masks, the session, PATH, repositories, `os/release/`, `os/owner-tools/`, the release manifests and every
other job. No new enabled unit, no listener, no repository, no key left in the RPM keyring, no `node`, nothing in
his home, no Chrome policy beyond installing and pinning our one extension.

**For your next release, not built here:** the release diff explains `/usr/share/aresos/chrome/` as per-build (from
`control.json`), `gh` from its lock, and the new action, links and files (for the list, only the tmpfiles line);
the release manifest gains the top-level object `"control": {"source_revision": …, "chrome_build": …}` from the
image's `control.json` (item 4; new after review 1); the release job runs `record_build.py add` and the pinning
pull request carries the row; the rehearsal runs the new `release_checks.py` checks after the update and after
`previous`, and requires the never-list's hash to be unchanged across both. The bundle is not reproducible on
purpose: a step that builds twice and expects equal bytes leaves out `/usr/share/aresos/chrome/` and
`chrome_extension`'s key-derived values, and compares what "The design" lists.

**Answers (2026-11-15), as agreed text:**

1. **The bundle's folder** is `/usr/share/aresos/chrome/`, outside the folders `check-image.sh` compares file by
   file; `control.json`'s per-build record binds it.
2. **The excluded-sites list** is made by tmpfiles, `/usr/lib/tmpfiles.d/aresos-control-chrome.conf`:
   `d /var/lib/aresos-control 0755 root root -` and
   `f /var/lib/aresos-control/chrome-excluded-sites.json 0640 root aresos-tools - {"format":0,"hosts":[]}`.
   tmpfiles runs after sysusers, so the group is set by name. `/var` is shared by all deployments: updates and
   `previous` keep his list, and an update never touches his edits. The folder stays apart from the service's own
   state (`/var/lib/aresos-tools`): the list restricts the service, so the service must never be able to write it
   (root-owned folder outside the unit's `ReadWritePaths`; checked by item 1's test, the image check and C6). The
   image ships no file there; C1 asserts the placeholder after boot. (Agreed first with `{"format":1,"hosts":[]}`
   in `/etc`; the lead tells `linux-aresos` of the placeholder's `format` 0, and the move to `/var` is its own.)
3. **`gh`'s licence:** the tag's `LICENSE`, committed as `os/config/usr/share/licenses/gh/LICENSE` (the config copy
   installs it), its SHA-256 in the lock. No second download.
4. **The lock** mirrors `os/google-chrome.lock.json`'s field names and order and adds `binary_sha256` and
   `license_sha256`. The key file is `os/keys/github-cli-rpm.pub`, beside `google-linux-signing-key.pub`; the lock
   records where it was published and how it was confirmed. The OS lead renews the pin with each release package;
   `check_build=resolve` reports the newest `gh` against the pin as information, never failing; a security
   advisory triggers a renewal out of cycle, said in the commit.
5. **The second VM pass:** its own step, 25 minutes to start, then about 1.5 times the slowest green; the
   `control` limit 127 to 152; one commit per workflow change, each recorded with `rebind.py pending`.
6. **C4's bind-mounted second bundle is enough.** The real switch is the next release's rehearsal, running
   `release_checks.py` after the update and after `previous` (`linux-aresos` puts it in its release brief).
7. **polkit:** `polkit-check.js` and the rehearsal sweep (`owner_vm.py`, about lines 1483 to 1506) review only
   passwordless actions, so no `polkit-review.json` entry. Required: `allow_any=no`, `allow_inactive=no`,
   `allow_active=auth_admin`, never `auth_admin_keep`; no rule in `/usr/share/polkit-1/rules.d` returning yes for
   it; an image check pinning those three defaults. If `polkit-check.js` flags it, tell `linux-aresos` before
   adding a review entry.

## Proof

**Unit tests, failing on today's code** (they run on GitHub: `pack.py`'s in item 2's workflow, `record_build.py`'s
in its records workflow, the others with the Control suites and `checks_only`; locally only the quick ones):
- `pack.py`: the package parses as CRX3, its signature verifies with its own key, the ID equals `idFor`'s for that
  key, the packed files equal the sources byte for byte; two calls give two IDs; the rendered policy has exactly the
  four keys for one ID, the host manifest exactly one origin, the update manifest the manifest's version; a link or
  a special file in the extension folder is refused; no private key in any returned value, in the output folder or
  in a temporary folder afterwards (the key scan below); a `node` test verifies a `pack.py` package with
  `node:crypto`, so the two packers agree on the format. All under `control/chrome/ci/install/`.
- The storage pin and the placeholder test of item 1 (`control/chrome_tests/`).
- `record_build.py`: item 4's tests.
- `os/tests`: `control-tree` leaves `control/` byte-identical and its `build-id.json` equals `build.py` on the
  checkout (the ordering rule); no installed file contains `EXTENSION_ID`, `UPDATE_URL` or `CRX_URL`; the `/etc`
  entries are links into `/usr/share/aresos/chrome/`; the `gh` step refuses a wrong RPM hash, a wrong binary hash, a
  bad signature line, a signature by another key and an RPM with scripts (the step's checks run on fixtures);
  `gh.lock.json` is complete; `os/keys/github-cli-rpm.pub` holds exactly one key, the pinned fingerprint.

**What the image check pins** (`image-checks.sh`, in the built image, no network):
- every path of "Agree" with its owner, mode and recorded content, parents root-owned, nothing else in
  `/usr/share/aresos/chrome/`; `/etc/opt/chrome/policies/managed/` exists, `root:root` 0755 with its parents, and
  holds exactly `aresos.json`, our link (this replaces 18c's make-and-remove check);
- the package: one RSA proof, the signature valid, the ID derived from its key equal to the ID in the policy, the
  update manifest, the host manifest and `control.json`; the zip inside `extension.crx` holds exactly `payload`'s
  names with their SHA-256s; the policy and the host manifest equal to their pinned shapes; both addresses are the
  fixed `file:` ones;
- no private key anywhere: no PEM private-key marker, and the package's public modulus (raw, hex, and base64 and
  base64url in all three alignments) found exactly once in the image's own additions (inside `extension.crx`) and
  nowhere in the build's temporary folders or its log. Every stored form of the private key holds the modulus;
- the polkit action: `pkaction` shows `allow_any=no`, `allow_inactive=no`, `allow_active=auth_admin` (never
  `auth_admin_keep`) and the owner annotation naming the unit's user; no rule file under
  `/usr/share/polkit-1/rules.d` or `/etc/polkit-1/rules.d` names the action; `/usr/bin/pkcheck` and the session's
  agent exist; the existing "nothing kept" check still passes;
- the excluded-sites list: the tmpfiles file equals the agreed lines; the image has nothing under
  `/var/lib/aresos-control/` and no `/etc/aresos/control/chrome-excluded-sites.json`; the installed `owner_hosts()`
  refuses the line's placeholder with `chrome_settings_unavailable` and gives `[]` for `{"format":1,"hosts":[]}`
  (both written to a scratch file in a `root:root` 0755 folder the check makes and removes; `Boundary.read` refuses
  a world-writable parent such as `/tmp`); no `ReadWritePaths` or `StateDirectory` of the installed unit reaches
  `/var/lib/aresos-control`;
- `gh`: `--version` equals the lock and is at least 2.102.0, as root and as `ares`; the binary's SHA-256 equals the
  lock and `control.json`; `rpm -q gh` says not installed; no repository of GitHub's; the RPM keyring's key list
  equals the base's;
- negative: without the test layer the image has no probe extension or its policy file, no test-only host and no
  second or third bundle.

**In the VM:** C1 to C11 with their PASS lines and evidence, then `CHECK_BUILD_CONTROL_CHROME_PASSED`. Evidence
never holds a key, a password, the owner's hosts, or anything from a real profile.

**What runs when:** on every pull request touching `control/`: the Control suites and item 2's workflow (on its
paths); the records workflow on its paths. On demand: `checks_only`, `check_build=build` (once at the end of step
3b, once on the final head) and `check_build=control` (**twice green on the final head**, by rerunning the same
run). Budget: 12 `check_build=control`, 3 `check_build=build`, 6 `checks_only`, 40 runs of item 2's workflow.
Watch with `gh run watch <id> --exit-status --interval 300`.

## Security: what this adds, and what the brief requires against it

| Risk | Required |
|---|---|
| **A force-installed extension** that can drive every page. Whoever controls the policy or the package controls his browser. | Policy, update manifest and package are root-owned under `/usr` (the signed image); `/etc` has only root-owned links; the policy is exactly one entry for one ID; both addresses are fixed `file:` paths under `/usr`; image checks and C1 pin all of it. The package's signature is checked at first install (case 4 and C5, on an ID the profile never held, show a tampered package is not installed); after that the copy in his profile is what runs, and it is user-writable (`KNOWN-LIMITS.md` line 21). |
| **The signing key, made in CI.** A kept key could sign a package Chrome accepts under the same ID. | Made inside one process, never written or exported, no key input; image and log scans; the unit test for leftovers. The ID is unique to the build and nothing trusts the key after it. |
| **The native host** is a door from Chrome to the service. | One allowed origin, generated with the package; fixed root-owned launcher with an empty environment; C3 and C4 show another extension is refused, also after an update; the service's own checks (peer UID, one host, the password for loosening) are unchanged. A same-named host in his home and a same-user process posing as the host stay the accepted residuals of `KNOWN-LIMITS.md`: don't add Chrome policies against them here. |
| **The polkit action** turns a password into looser rules. | The shipped file byte for byte; never kept; C7 with his real agent in a session started the real way, including cancel and "asks again". |
| **A downloaded binary** (`gh`) that decides whether qualification records are genuine. | Pinned RPM bytes, signature by a pinned key, pinned binary hash, only the one file taken, no scripts run, no repository; image check and C10; it runs as `aresos-tools` in the unit's sandbox with no login. |
| **A stale or foreign identity after update or rollback.** | Links instead of files in `/etc`; C4; the rehearsal checks. A mismatch fails closed: the tools say Chrome isn't connected. |
| **Chrome's tools before his never-list is in.** His own sites (his dashboard first) would be ordinary sites to the tool. | The list starts as a placeholder the validator refuses; every Chrome read and action answers `chrome_settings_unavailable` until root writes a `format` 1 list (item 1's test, the image check, C6's first use). The gate needs no host of his. |
| **His never-list across update and rollback.** A list kept per deployment would come back older after `previous`, silently. | The list lives in `/var/lib/aresos-control/`, shared by all deployments; tmpfiles only makes it when missing; the rehearsal requires its hash unchanged after the update and after `previous`. An image from before this package reads the old `/etc` path, which no image ships, and refuses (fails closed). |
| **The service loosening its own limits.** The list restricts the service. | Root-owned folder and file, the service's group may only read; the folder is outside the unit's `ReadWritePaths` and apart from `/var/lib/aresos-tools`; item 1's test, the image check and C6 (write and create refused under the unit's sandbox). |
| **The owner's hosts leaking** into a public repo or evidence. | The image ships no list, only a hostless placeholder made at boot; tests use made-up hosts under `.invalid` or `localhost`; the privacy check runs on every push. |
| **Test-only pieces reaching a release** (the probe, its host, the second bundle). | They live in the test layer only; the negative image check. |
| **Chrome telling a store about our extension.** | Item 2's case 5 and C9, each with the probe as a positive control. |

## Steps (one fresh agent each, about 250k tokens; PROGRESS.md after each)

- **1a. Packer, templates, pins** (item 1: `pack.py` and its tests, the templates, the storage pin, the
  excluded-sites path, message, tmpfiles file and their test, the README). Starts at once.
- **1b. `record_build.py`** (item 4, its tests, the records workflow, the one recorded run). After 1a.
- **2. Install proof in the container** (item 2). After 1a; one builder on the branch at a time.
- **3a. Image install, Chrome's files** (item 3 without `gh`: the install map, the bundle, the tmpfiles file, the
  links, the polkit action, their image checks, `check-image.sh`, `os/tests`; `checks_only` green). Needs PR #58 on
  `main`, the lead's go (it has told `linux-aresos` the changes after review 1) and the lead's answer 5.
- **3b. `gh`** (item 3's `gh` part: lock, key, licence, the step, the resolve line, their checks and `os/tests`),
  then `check_build=build` green once. Its own stop conditions are `gh`'s line under "Stop and report".
- **4. VM, first half:** the polkit probe first; the second pass and its layer; C1, C2, C6's first use, C3, the
  rest of C6, C10, C11.
- **5. VM, second half:** C4, C5, C9, then C7 and C8.
- **6. Close:** the rehearsal checks, the two greens on the final head, README lines, the report text.

## Done

Every item built as agreed with `linux-aresos`; the unit tests, item 2's workflow and the records workflow green; `check_build=build`
green once and `check_build=control` green twice on the final head with every PASS line of 18c and of this brief;
the report text in `PROGRESS.md` with **run/read/assumed** marks, the JUDGMENT-CALLs (at least: what the owner sees
in Chrome, the policy form, the `gh` version, the placeholder gate and its message, the imitation in C4, any CI-only
Chrome flag), PLAN-GAPs, "Not verified" (at least: a real deployment switch with Chrome open; his real sites; the
laptop's own polkit agent), the lines "For his guide", and a proposal for `docs/design/CONTROL.md` section 6 only
where what was built differs from the install text the lead wrote there (PR #48). A draft pull request against
`main`. Stop there.

## Out of scope, and paths not to touch

- Publishing or pinning a release; anything on the laptop; the owner's excluded hosts; real accounts, real sites,
  a real model; Chrome packages 28, 28a and 28b; a persistent extension identity or a web-store listing.
- `control/aresos_control/` (except the two lines of `exclusions.py` in item 1), `control/chrome/extension/`,
  `control/chrome/native_host.py`, `control/chrome/build.py`, `qualify.py`, `qualification.json`, the contents of
  `builds.json`, `control/chrome/packaging/host` and the polkit action file, `control/packaging/`,
  `control/generated/`, `control/settings/`, the existing files under `control/chrome/ci/` and
  `control/chrome_tests/` (add new files; the only edits are item 1's path lines in `prepare.mjs` and
  `test_exclusions.py`; CI's own install in `prepare.mjs` keeps its loopback address and its key),
  `control-chrome.yml` and the qualification workflow. `mod/`, `docs/design/` (the lead changed section 6 on PR #48),
  `docs/control/`, `STATE.md`, `HANDOFF.md`. Under `os/` everything outside "Agree".
- If the extension or the service seems to need a change to pass a check, that is a finding: stop and report.

## Stop and report

- The pinned Chrome doesn't follow the `/etc` links, refuses a `file:` update address, or won't force-install an
  extension from outside its store on this machine. (If the image shipped no Chrome, that would be a PLAN-GAP and a
  stop; it ships one.)
- A request naming our extension's ID goes to anything but a `file:` address and the policy can't stop it.
- polkit refuses, or shows no dialog, for a process started the way the shell starts Chrome (step 4's probe, then
  C7). Don't change the action's defaults or the way Chrome is started to get green.
- `gh`'s RPM can't be verified with a key you can show is GitHub CLI's, carries scripts, or the binary needs
  something the image lacks.
- The key would have to be kept, passed in or written down for anything to work.
- The service needs a sandbox line loosened for `gh`, `pkcheck` or the excluded-sites file.
- The image needs anything outside "Agree": a package, a repository, an enabled unit, a listener, a sudo or polkit
  rule, a workflow permission or secret, a base change.
- PR #58 isn't on `main`, or the lead hasn't given the go, when step 3a would start.
- A pinned download that has nothing to do with this branch has vanished: one line for `linux-aresos`, go on with
  what doesn't need the build.

## Rules

`AGENTS.md` hard rules 1, 4, 5, 6 and 7 apply. You are on the owner's laptop: no containers, virtual machines or
root locally, quick unit tests only (never `discover -s os/tests` without a pattern, never `test_owner_update`);
images, containers and VMs run on GitHub. Never start Chrome on the laptop and never touch his profile. Work in your
own worktree on branch `pkg/18c-b-chrome-image`; commit in small steps with a model trailer; push; open a draft pull
request; never merge, never push to `main`, never force-push, never `--no-verify`. The repo is public: no personal
data, real addresses, host names of his, or provider names, in code, tests, fixtures and evidence alike. Check
`gh api rate_limit` before a burst of `gh` calls; on HTTP 403 wait for the reset and try once.

**If unsure:** take the option that fails closed (the tools say Chrome isn't connected), keeps every key and
password out of files, and changes the image least; say so in the report.

## The lead's answers (2026-11-15, `linux-tools`)

1. **Mail's record refresh:** Chrome only. Mail has no record refresh on `main`; Mail already runs under the real
   unit in 18c's VM pass (checks 8 and 9 with the fixture servers), which is what #150 asked for Mail.
2. **`builds.json`:** keep it empty and use the hash as a test value. A row lands only with the commit that pins a
   shipped image, as `QUALIFICATION.md` says; #285 is answered by `record_build.py` and its check.
3. **The update test:** enough, split as written: C4 proves Chrome's behaviour across A→B→A in one guest, and the
   rehearsal proves the files after a real deployment switch. The rehearsal's checks must include that the policy,
   the update manifest and the host manifest all name the new build's ID and the links resolve into the new `/usr`.
   `linux-aresos` agreed: the bind-mounted bundle is enough ("Agree", answer 6).
4. **The release job:** `linux-aresos`, in its next release package, as written. This brief delivers the tool, its
   check and the instructions for that package.
5. **What he sees:** the lead asks the owner (board), with C2's screenshot of "managed by your organization" when the
   build has one. Steps 1 and 2 don't depend on the answer; step 3 waits for it.
6. **His hosts before first use** (changed after review 1): a gate without a service change. The list itself is the
   mark: tmpfiles makes it as a placeholder the validator refuses, and every Chrome read and action answers
   `chrome_settings_unavailable` until the owner, as root with `sudo` in the live sitting, writes a `format` 1
   list (an empty one counts). `chrome_sites` has no part in it. Item 1 (path, message, test), C1 and C6. This
   replaces "by agreement" in #200.
7. **The policy form:** `ExtensionSettings` alone is fine. The builder doesn't edit `docs/design/` (changed after
   review 1): the lead wrote the install text into `docs/design/CONTROL.md` section 6 on PR #48's branch, and this
   brief notes 18c's Part C as replaced.
8. **GitHub CLI's key:** as written: the builder shows the key is GitHub's from GitHub's own published key file
   (fetched over HTTPS, fingerprint compared, both recorded in the lock), or step 3 stops.
9. **The polkit risk** (Chrome started with `systemd-run --user --scope`, outside the login session's scope): step 4
   starts with the polkit probe (item 5), with a stop condition if the dialog doesn't come; C7 drives the dialog in
   step 5.

## Changes after review 1

`reviews/18c-b-chrome-image/BRIEF-REVIEW-1.md` (NOT READY); the lead decided each finding, `linux-aresos` answered.

- **B1** (the guard rested on `chrome_sites`, which saves no list): the placeholder gate, no service change beyond
  two lines. "The design" (never-list starts refused); "Facts" (the excluded-sites bullet); item 1 (path, message,
  tmpfiles file, placeholder test, README); item 3; C1, C6 (first use after C2); "Proof"; the security table;
  "Agree", answer 2; "For his guide"; lead's answer 6. Brief 28b item 9 (and its two lines on the never-list) and
  `CONTROL.md` section 6 describe this gate on PR #48's branch. The message changed because the old one sent him
  looking for a broken install.
- **S1** (a rollback brings back an older never-list): `linux-aresos`'s answer moves the list to
  `/var/lib/aresos-control/`, shared by all deployments, so the known limit goes away. A risk row; the rehearsal
  check (`CONTROL_CHROME_SITES_SHA256`, unchanged after the update and after `previous`); "For your next release".
  The service can never write the folder: a requirement with checks (item 1's test, image check, C6, risk row).
  `exclusions.py`'s path is a hard-coded constant, so the move is that one line plus CI's writer and one test line.
  "For his guide" has the exact owner step, the "no sites to exclude" case (the empty `format` 1 list) included.
  The lead tells `linux-aresos` of the placeholder's `format` 0 and the manifest's `control` object.
- **S2:** (a) the builder doesn't edit `docs/design/`; the install text is in `CONTROL.md` section 6 on PR #48;
  18c's Part C is noted as replaced (header). (b) Step 4 starts with the polkit probe (item 5, "Steps", "Stop and
  report", answer 9). (c) `linux-aresos`'s seven answers are written into "Agree" as agreed text, with the
  placeholder and `/var` changes and "tell `linux-aresos` before the first `os-image.yml` commit".
- **S3:** "Facts" (Chrome bullet), "Agree" path 4 and "Proof" name the policy-folder check that replaces 18c's
  `rmdir` check.
- **S4:** item 2 case 4 and C5 on a fresh profile or a never-held ID (bundle C), plus the installed-copy half; the
  first security row reworded.
- **S5:** item 2, the probe installs through `ExtensionInstallForcelist` in its own file; C1; "For his guide".
- **S6:** item 2 case 5 and C9 carry the probe as a positive control; the security row.
- **S7:** item 3, one committed key, the pinned fingerprint, every imported key deleted; `os/tests`; "Proof".
- **S8:** item 1 (`pack.py`'s tests under `control/chrome/ci/install/`); item 4 (`check`'s rule, the manifest's
  `control` object, tests on a synthetic repository under `control/chrome/ci/records/`, the `ccd0fd79…` value as a
  recorded run, a records workflow); "Proof"; "For your next release".
- **S9:** "Proof": the image check opens the zip in `extension.crx`; the key scan looks for the public modulus.
- **S10:** steps 1a, 1b, 2, 3a, 3b, 4 to 6; the doc edit and the guard are out of step 1; "Model".
- **Notes:** README's "Copy all" paragraph (item 1); `pack.py` refuses links (item 1); where
  `briefs/18c-image-start.md` lives (header); building twice: not reproducible on purpose ("The design", "For your
  next release"). The polkit fallback, question 1's alternative and the native host's residuals need no change.
