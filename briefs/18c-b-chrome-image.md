# 18c-b: Chrome's browser side in the image

Board #223, #224, #285, #200 and the Chrome lines of #150. A frozen task for one builder, in steps. Parent:
`briefs/18c-image-test.md` (its Part C) and `briefs/18c-image-start.md` (the amendment that moved `gh` here).

**Base.** This package builds on the image part of 18c (branch `pkg/18c-image`, draft PR #58), which merges first.
Steps 1 and 2 change only `control/` (and add one small workflow) and start at once on `main`. Nothing under `os/`
starts before PR #58 is on `main` **and** the lead has passed on `linux-aresos`'s answer to "Agree with
`linux-aresos`" below; where its answer differs from this brief, the answer wins.

## Goal

The AresOS image carries everything Chrome needs for Claude's Chrome tools: our extension, installed by Chrome's own
policy from a file inside the image; the native-messaging host that connects it to the tool service; the polkit
action behind "Allow editing" and "don't ask again"; the owner's excluded-sites file; and `gh`, which checks the
qualification records. After an update or a rollback the browser side belongs to the booted image again without
anyone touching it. A throwaway CI image proves all of it in the CI virtual machine, on the Chrome the image ships.

**What the owner will see once a release carries it:** Chrome opens with a pinned "AresOS Chrome" button he can't
remove, Chrome's menu says the browser is managed, and Claude's Chrome tools work after an update without a setup
step. "Allow editing" asks for his password in the usual dialog.

## Why now

The Chrome tool is on `main` (PR #27, 2026-11-14), and 18c's image part ships the service with Chrome's two startup
files but nothing of the browser side: `aresos chrome tabs` answers `chrome_unavailable` in every image. No release
with the tools can reach the laptop, and his live test (Mail, then Chrome) can't start, until this is in the image.
The design was settled on 2026-11-14 (`docs/control/TOOLS-HANDOFF.md`, row "Brief 18c-b";
`reviews/18c-b-chrome-image/RESEARCH.md`).

## Model

- **Builder:** a Claude agent. **Fable 5.2** for steps 1 to 3 (the signing key and the packer, the install proof on
  a real Chrome, and the image install with the signature-checked download): security-sensitive install work whose
  design is settled only in outline, where a wrong first cut costs review rounds. **Opus 5.5** for steps 4 to 6 (VM
  checks against this brief's lists, the kind of work Opus did in one go in 18c's B2). Move a step to Fable when it
  has resisted two rounds; the likely one is driving the password dialog in step 5.
- **Reviews (the lead's job):** a package review and a high-stakes security review by fresh reviewers
  (`docs/REVIEW.md`, "Tools for Claude"): the package force-installs an extension that can drive every page, adds a
  native host, a polkit action and a downloaded binary, and makes a key in CI.

## Read first

- `AGENTS.md`, `docs/WORKFLOW.md`, and `CLAUDE.md`'s "Builders work in steps".
- `reviews/18c-b-chrome-image/RESEARCH.md`: the install routes, what the signing key means, updates and rollback.
- `control/chrome/packaging/README.md` and every file beside it; `control/chrome/build.py`;
  `control/chrome/native_host.py`; `control/checks/17-chrome/install.mjs` (`pack`, `idFor`: the CRX3 container CI
  uses today); `control/chrome/ci/prepare.mjs`, `browser.mjs` and `Dockerfile` (how CI installs and starts Chrome).
- `control/aresos_control/chrome/`: `adapter.py` (`__init__`, `maintenance`), `qualification.py` (`verify`,
  `refresh`), `exclusions.py`, `confirm.py`, `policy.py` (`FIXED_HOSTS`), `bridge.py` (`accept`); and
  `control/aresos_control/boundary.py` (`Boundary.read`).
- `docs/design/CONTROL.md` section 6 ("How the tool reaches Chrome", "Where Claude may go");
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
  hosts from `/etc/opt/chrome/native-messaging-hosts/`. Package 21's image check already creates the policy folder.
  The base ships `native-messaging-hosts/` with one file of KDE's; ours goes beside it.
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
  `policy.py` (`claude.ai`, `console.anthropic.com`, `platform.claude.com`). `exclusions.py` reads
  `/etc/aresos/control/chrome-excluded-sites.json` through `Boundary.read`: every folder and the file root-owned,
  not group- or world-writable, **a regular file, never a link**. A missing or unsafe file refuses every Chrome
  read and action.
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

## The work

### 1. The packer and the templates (`control/` only)

- **`control/chrome/packaging/pack.py`** (new): builds the signed package and the three generated files in one
  call, with no browser and no `node`. It runs in three places: the image build (the pinned base), item 2's
  container and the runner that runs its unit tests. Use what the base image has (`cryptography`, or OpenSSL through
  anonymous pipes) and check what the other two have before you choose; item 2's workflow may install a
  distribution package for it, but no pip dependency is added. Rendering the templates and listing the payload need
  only the standard library, because `check-image.sh` uses them on the runner. It
  - makes an RSA 2048 key from the system's random source, **inside its own process** (or in a child it talks to
    only through anonymous pipes);
  - writes a CRX3 package of `control/chrome/extension/` in the container format of `install.mjs`'s `pack` (one RSA
    proof, the signed header carrying the 16-byte ID), with the files in sorted order and fixed timestamps;
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
- `control/chrome/packaging/README.md`: replace the HTTPS-endpoint and production-key paragraphs and the "manual
  handoff" sentence with what this package builds. `pack.mjs` and CI's own install stay as they are.

### 2. The install proof on a real Chrome, in a container first

The VM costs about 50 minutes a run, so the Chrome side is developed where a run takes minutes and stays there as
the check on every pull request that touches `control/chrome/packaging/` or `control/chrome/extension/`.

- A small workflow of its own, `.github/workflows/control-chrome-install.yml` (read-only, no secrets), on the
  container of `control/chrome/ci/Dockerfile` with Chrome at the image's pinned version if Google still serves that
  package (pin its URL and SHA-256; otherwise current stable of the same major, recorded). New files only, under
  `control/chrome/ci/install/`. Chrome starts as `browser.mjs` starts it: never `--no-sandbox`,
  `--remote-debugging-*`, `--load-extension` or `--disable-extensions-except`.
- The layout is the image's: the four files under `/usr/share/aresos/chrome/`, the two links in `/etc`, the host and
  `native_host.py` in `/usr/libexec/aresos-control/chrome/`, and CI's service on `chrome.sock`
  (`control/chrome/ci/service.py`, used as it is). `pack.py`'s unit tests run in this workflow too.
- **A probe extension** (test only): a second extension with its own key, `nativeMessaging` and `management`
  permissions and its own test-only native host that writes down what the probe reports. It gives the checks a way
  to ask Chrome questions without a debugging port.
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
  4. **A broken package.** With one byte of `extension.crx` changed, and separately with the file missing, Chrome
     doesn't install the extension, ordinary browsing still works, and the tools' answer is `chrome_unavailable`.
     With the file restored the next start installs it.
  5. **Nothing asks the web store about us.** One run with Chrome's network log on
     (`--log-net-log`, `--extensions-update-frequency` short) across at least two update checks: no request to
     anything but a `file:` address names our extension's ID.
- Record for the report what case 3 looks like in time: how long after a start the old extension is gone and the new
  one is connected.

### 3. The image install (`os/`, as agreed with `linux-aresos`)

Extend 18c's install map; don't build a second one.

- **Ordering rule** (from `mac-aresos-control`): `build.py` runs on the untouched source tree **before** anything
  is generated, and generated files go only into the destination, never back into the source tree. The installed
  tree holds no template copy. That keeps `chrome/build-id.json` equal to what CI qualifies for the same commit.
- **Deterministic files** (in `FILES`, recorded and compared like every other): the host launcher and
  `native_host.py`; the polkit action. The two `/etc` links join the record's `links`.
- **The per-build bundle** (image build only): one call of `pack.py` writes the four files of
  `/usr/share/aresos/chrome/`. `control.json` gains `chrome_build` (the hash, as a value) and `chrome_extension`
  (the packer's public record plus each generated file's mode and SHA-256). The build prints
  `CONTROL_CHROME_EXTENSION <id> <crx sha256>`.
- **The excluded-sites file** with `{"format":1,"hosts":[]}`: mode, group and how it is made as agreed below. The
  owner's hosts never appear in the repo, a test, a fixture or evidence; he fills the list in his live sitting
  (board #200).
- **`gh`** in `build.sh packages`, beside Chrome's RPM and with the same care:
  - `os/gh.lock.json`: version, URL, the RPM's SHA-256, size and NEVRA, the signing key (file, where it was
    published, SHA-256, fingerprint), the SHA-256 of `/usr/bin/gh` inside it, and the licence text's SHA-256.
    Start from 2.103.3 (18c step 1); take a newer patch release only for a security fix, and say so.
  - Download over HTTPS; require the pinned bytes and NEVRA; require that the RPM has no scripts; **check the
    signature** with `rpmkeys --checksig` after importing the pinned key, requiring the header's signature by that
    fingerprint and every line OK; then delete the key again, as Chrome's step does. The verifier is `rpmkeys` of
    the digest-pinned base image; the key is GitHub CLI's package key, committed under `os/keys/` and pinned in the
    lock. Record where the key came from and how you confirmed it is theirs.
  - Take **only** `/usr/bin/gh` out of the RPM (`rpm2cpio`, `cpio`), 0755 `root:root`, and require its SHA-256 to
    equal the lock's. No `rpm -i`, no `--nodeps`, no Fedora `git`, no repository, no completions or man pages.
  - The licence text at `/usr/share/licenses/gh/LICENSE`, from the source agreed below, with its hash in the lock.
  - The lock is copied to `/usr/share/aresos/manifest/gh.lock.json`; `control.json` gains `gh` (version and the
    binary's SHA-256, checked against `/usr/bin/gh` at build).
- **Image checks** (`image-checks.sh`): the list under "Proof". **`check-image.sh`**: the image's `gh.lock.json`
  equals the reviewed one; `chrome_build`, `gh` and `links` equal the checkout's; `chrome_extension` is consistent
  with the checkout (its `payload` equals the checkout's extension files, and the three generated files equal the
  templates rendered with the recorded ID), so only the key, the signature and the ID differ between two builds.
- `os/README.md`: the Control paragraph says what the browser side adds and why the bundle differs per build.

### 4. `builds.json` is recorded by a tool, not by hand

Today the lead writes each shipped image's row (`commit`, `build`, `shipped_at`) into `control/chrome/builds.json`.

- **`control/chrome/record_build.py`** (new; not one of `build.py`'s inputs):
  - `add --commit <full commit> --shipped-at <UTC time, Z> [--expect <hash>]` computes the hash with **that
    commit's own** `build.py` over that commit's tree (`git archive` into a temporary folder), refuses if it differs
    from `--expect` or from an existing row for the commit, adds the row and keeps the newest three by
    `shipped_at`.
  - `check <release manifests>` fails when a release manifest names a Control build (see below) that has no equal
    row, unless three newer rows exist.
- The image already says which build it carries (`CONTROL_CHROME_BUILD` in the build log, `chrome_build` in
  `control.json` after item 3). What the **release** does with it is `linux-aresos`'s part and is not built here
  (see "Agree"): the release job copies `source_revision` and `chrome_build` from the image's `control.json` into
  its release manifest and runs `add`; the pull request that pins the release carries the row; `check` fails that
  pull request without it.
- `builds.json` stays `{"format":1,"builds":[]}` in this package: no image with the tool has shipped. Use
  `ccd0fd79…ce15` only as a test value: `add` for a commit whose `control/` is 18c's head must compute it.
- Run `check` where a pinning pull request can't miss it: in a `control/chrome_tests` test and through one path
  filter on a cheap Control workflow (`os/manifest/release.json`, `os/manifest/releases/**`).

### 5. The VM checks (`check_build=control`)

A second pass after 18c's, on the same disk with a fresh overlay: its own step in the `check-build` job, its own
action file in the Control test layer, its own evidence folder `evidence/control/chrome/`. The layer also carries
the probe extension, its test-only host, a second bundle (B) made by `pack.py`, and a small page server from the
standard library (a form page and a receiver that counts what arrives), serving on `localhost` in the guest.

**How Chrome runs in the guest.** As `ares`, in his session, started the way the shell starts it (the shell's own
launch request if the guest's session runs the shell, otherwise the same `systemd-run --user --scope` line with the
session's environment). Record the cgroup of Chrome and of the native host, and `loginctl`'s view of his session.
CI-only additions are limited to `--no-first-run`, `--no-default-browser-check`, `--password-store=basic` and, for
check C9 alone, the two network-log flags; never the four forbidden flags of item 2. The password dialog is answered
through the VM's keyboard (QMP), with a per-run password for `ares` that never reaches the evidence. 18c's SELinux
scan runs again at the end of this pass: a denial naming Chrome's host, the service, `gh` or `pkcheck` fails it.

| Check | What it shows | PASS line |
|---|---|---|
| C1 files | Every path of "Agree" in the booted guest with its owner, mode and content; the two links are links, equal to `/usr/etc`'s; `/etc/opt/chrome/policies/managed/` holds only ours (plus the test layer's, named) | `CONTROL_CHROME_FILES_PASS` |
| C2 install | Item 2's case 1 on the shipped Chrome in his session; a screenshot of the pinned button and of Chrome's "managed" note for the owner's picture | `CONTROL_CHROME_INSTALL_PASS` |
| C3 host | The extension connects through the installed host to the real service as `ares` (peer UID 1001); `aresos chrome tabs` lists his tabs; one page of the page server is read; the probe is refused; `chrome.sock` shows exactly one host | `CONTROL_CHROME_NATIVE_HOST_PASS` |
| C4 update | Item 2's case 3 in the guest with the same profile: bundle B bind-mounted over `/usr/share/aresos/chrome` (CI only), then removed again. After each switch the host's manifest names the current ID, the current extension connects and reads, the previous ID is gone, the probe is refused | `CONTROL_CHROME_UPDATE_PASS` |
| C5 broken package | Item 2's case 4 in the guest; Chrome and the service stay up; restored, it installs again | `CONTROL_CHROME_PACKAGE_FAULT_PASS` |
| C6 sites | As shipped: `ares` can neither read nor write the file; reads work; opening each `FIXED_HOSTS` address is refused. With one test host added by root: that host and a subdomain are refused. With the file group-writable, then missing: every read refuses `chrome_settings_unavailable`. Restored each time, its hash equal to the shipped one | `CONTROL_CHROME_SITES_PASS` |
| C7 password | On the details page, "Allow editing" for a test site: the dialog of his real agent appears, a screenshot shows it naming the site; cancelled, the site stays read-only; with the password, it is editable; a second change asks again. From the journal: the action, a one-time authorization, and the subject being the native host's process | `CONTROL_CHROME_POLKIT_PASS` |
| C8 ask | One asking action end to end through 18c's interactive driver: Claude Code as `ares` fills the form page and submits; the prompt shows the service's question; "Yes" gives one arrival at the receiver, "No" none | `CONTROL_CHROME_ASK_PASS` |
| C9 no store | Item 2's case 5 in the guest | `CONTROL_CHROME_NO_STORE_PASS` |
| C10 `gh` | `/usr/bin/gh --version` equals the lock, as `ares` and as `aresos-tools` under the unit's own sandbox properties (`systemd-run`); the binary's hash equals `control.json`; no login or token in the verifier's folders | `CONTROL_GH_PASS` |
| C11 records | Chrome's record refresh under the real `aresos-toold.service`: with the extension connected, the service fetches once and writes its result line (`aresos log`); the service stays active, no AVC denial, the verifier's cache is under `/var/lib/aresos-tools`. If an attested record is published by then: "Verified record accepted." Otherwise: "refused …; held record retained", plus `verify` run under the unit's sandbox against a public attestation of this repository if one exists (accepted) and against a wrong signer (refused) | `CONTROL_CHROME_RECORDS_PASS` |

C11 is the one check that reads the real network (the public repository and the verifier's trust data); it records
which path it took. The lead's note also names a record refresh of Mail's: `main` has none (see "Open questions").

**For the release rehearsal** (it has no test layer and no browser): add checks to `os/ci/control/release_checks.py`
in 18c's style: the two links exist, are links and equal `/usr/etc`'s; the ID in the policy, the update manifest,
the host's manifest and `control.json` is one ID, and the package's signature verifies with its own key (the image's
`openssl`); no other ID under `/etc/opt/chrome`; the excluded-sites file as agreed; `gh`'s version and hash; the
polkit action equal to the record.

### 6. Records and the report

Keep `reviews/18c-b-chrome-image/PROGRESS.md` current after every step (done, left in order, what the code doesn't
show, run IDs). The last step leaves the full report text there under "For the report" (a Claude builder can't
create `REPORT.md`) in `AGENTS.md`'s format, every claim marked **run** (run ID and log line), **read** (file and
version) or **assumed**, with the measured times of the VM pass.

## Agree with `linux-aresos` (the lead relays this section before the brief is final)

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
| `/etc/aresos/control/chrome-excluded-sites.json` | `root:aresos-tools` 0640; folders `root:root` 0755 | `{"format":1,"hosts":[]}`, a regular file |
| `/usr/lib/tmpfiles.d/aresos-control-chrome.conf` | `root:root` 0644 | only if the file above is made at boot (question 2) |
| `/usr/bin/gh` | `root:root` 0755 | from GitHub's pinned, signature-checked RPM |
| `/usr/share/licenses/gh/LICENSE` | `root:root` 0644 | gh's licence text |
| `/usr/share/aresos/manifest/gh.lock.json` | `root:root` 0644 | copy of `os/gh.lock.json` |
| `/usr/share/aresos/manifest/control.json` | `root:root` 0644, as today | gains `chrome_build`, `chrome_extension`, `gh`, two `links` |

**Paths under `os/` that change:**

1. `os/build.sh`: `packages` gains the `gh` step; `control` and `control-tree` gain the entries above.
2. New: `os/gh.lock.json`, GitHub CLI's public key under `os/keys/`, and the licence text if it is committed.
3. `os/Containerfile`: no change expected (the `packages` stage already copies `os/`, and `control` already runs
   before `configure`).
4. `os/ci/image-checks.sh`, `os/ci/check-image.sh`: the checks of "Proof".
5. `os/ci/control/`: a Chrome action file, the probe extension and its host, the page server, the second bundle in
   `Containerfile`, a Chrome sequence in `control_vm.py`, new checks in `release_checks.py`.
6. `os/ci/check-build.sh`: a `control-chrome-pass` mode beside `control-pass`.
7. `os/tests/test_control_image.py`, `os/tests/test_control_vm.py`; `os/README.md`.
8. `os/ci/polkit-review.json`: only if `polkit-check.js` asks for the new action (it isn't passwordless).

**`.github/workflows/os-image.yml`** (`check-build` job only; no new permission, secret, input or job):
- one step "Control Chrome VM pass (check_build=control only)" running `check-build.sh control-chrome-pass`, with
  its own `timeout-minutes` (25 to start; then about 1.5 times the slowest green);
- the job's limit for `control` raised by that step's limit (127 to 152);
- the evidence upload unchanged (the new folder is inside it).
Each change is its own commit, recorded with `rebind.py pending` in `os/manifest/ci/16/pending-rebind.json`, and the
lead hears before the first one.

**Must not change:** the base digest, `packages.lock.json`, the Chrome pin, accounts, sudo, the existing polkit rule
file, unit masks, the session, PATH, repositories, `os/release/`, `os/owner-tools/`, the release manifests and every
other job. No new enabled unit, no listener, no repository, no key left in the RPM keyring, no `node`, nothing in
his home, no Chrome policy beyond installing and pinning our one extension.

**For your next release, not built here:** the release diff explains `/usr/share/aresos/chrome/` as per-build (from
`control.json`), `gh` from its lock, and the new action, links and files; the release manifest records
`source_revision` and `chrome_build`; the release job runs `record_build.py add` and the pinning pull request
carries the row; the rehearsal runs the new `release_checks.py` checks after the update and after `previous`.

**Questions:**

1. The bundle's folder: `/usr/share/aresos/chrome/`, or would you rather have it under `/usr/share/aresos/control/`?
   (It must stay outside the folders `check-image.sh` compares file by file.)
2. The excluded-sites file. Proposed: tmpfiles makes it at boot when missing (`f`, with the empty list as content,
   `root:aresos-tools` 0640, the folder `d` 0755), so the group is set by name after sysusers and his later edits
   are never touched by an update. Alternative: ship it in the image's `/etc` as `0:250`, where a taken 250 would
   hand the group to someone else. Which?
3. `gh`'s licence text: committed under `os/` from the tag's `LICENSE` with its hash in the lock (no second
   download), or taken from the release tarball at build?
4. The `gh` lock's shape and the key file's name; and who renews the pin, with which signal (the resolve check
   could report the newest release).
5. The second VM pass as its own step with the limits above: agreed?
6. C4 imitates the update inside one guest by bind-mounting a second bundle over `/usr/share/aresos/chrome`, because
   a real second deployment needs a second image in the guest. The real switch is left to your rehearsal with the
   checks above. Enough, or do you want a real `bootc switch` in this pass?
7. The new polkit action and package 21's polkit checks: anything they need beyond the file itself?

## Proof

**Unit tests, failing on today's code** (they run on GitHub: `pack.py`'s in item 2's workflow, the others with the
Control suites and `checks_only`; locally only the quick ones):
- `pack.py`: the package parses as CRX3, its signature verifies with its own key, the ID equals `idFor`'s for that
  key, the packed files equal the sources byte for byte; two calls give two IDs; the rendered policy has exactly the
  four keys for one ID, the host manifest exactly one origin, the update manifest the manifest's version; no private
  key in any returned value, in the output folder or in a temporary folder afterwards; a `node` test verifies a
  `pack.py` package with `node:crypto`, so the two packers agree on the format.
- The storage pin of item 1.
- `record_build.py`: `add` on a fixture repository (an archived commit hashed with its own `build.py`, a wrong
  `--expect`, a repeated commit, pruning to three); `check` with a manifest that has no row; the `ccd0fd79…` value.
- `os/tests`: `control-tree` leaves `control/` byte-identical and its `build-id.json` equals `build.py` on the
  checkout (the ordering rule); no installed file contains `EXTENSION_ID`, `UPDATE_URL` or `CRX_URL`; the `/etc`
  entries are links into `/usr/share/aresos/chrome/`; the `gh` step refuses a wrong RPM hash, a wrong binary hash, a
  bad signature line and an RPM with scripts (the step's checks run on fixtures); `gh.lock.json` is complete.

**What the image check pins** (`image-checks.sh`, in the built image, no network):
- every path of "Agree" with its owner, mode and recorded content, parents root-owned, nothing else in
  `/usr/share/aresos/chrome/` or `/etc/opt/chrome/policies/managed/`;
- the package: one RSA proof, the signature valid, the ID derived from its key equal to the ID in the policy, the
  update manifest, the host manifest and `control.json`; the policy and the host manifest equal to their pinned
  shapes; both addresses are the fixed `file:` ones;
- no private key anywhere in the image (a scan for PEM and DER private-key markers over the image's own additions
  and its temporary folders), and none in the build log;
- the polkit action: `pkaction` shows `no`/`no`/`auth_admin` and the owner annotation naming the unit's user;
  `/usr/bin/pkcheck` and the session's agent exist; the existing "nothing kept" check still passes;
- the excluded-sites file as agreed, readable through the installed `owner_hosts()` as the service's user and
  giving an empty list;
- `gh`: `--version` equals the lock and is at least 2.102.0, as root and as `ares`; the binary's SHA-256 equals the
  lock and `control.json`; `rpm -q gh` says not installed; no repository or key of GitHub's;
- negative: without the test layer the image has no probe extension, no test-only host and no second bundle.

**In the VM:** C1 to C11 with their PASS lines and evidence, then `CHECK_BUILD_CONTROL_CHROME_PASSED`. Evidence
never holds a key, a password, the owner's hosts, or anything from a real profile.

**What runs when:** on every pull request touching `control/`: the Control suites and item 2's workflow. On demand:
`checks_only`, `check_build=build` (once with item 3, once on the final head) and `check_build=control` (**twice
green on the final head**, by rerunning the same run). Budget: 12 `check_build=control`, 3 `check_build=build`, 6
`checks_only`, 40 runs of item 2's workflow. Watch with `gh run watch <id> --exit-status --interval 300`.

## Security: what this adds, and what the brief requires against it

| Risk | Required |
|---|---|
| **A force-installed extension** that can drive every page. Whoever controls the policy or the package controls his browser. | Policy, update manifest and package are root-owned under `/usr` (the signed image); `/etc` has only root-owned links; the policy is exactly one entry for one ID; both addresses are fixed `file:` paths under `/usr`; image checks and C1 pin all of it; C5 shows a tampered package is not installed. |
| **The signing key, made in CI.** A kept key could sign a package Chrome accepts under the same ID. | Made inside one process, never written or exported, no key input; image and log scans; the unit test for leftovers. The ID is unique to the build and nothing trusts the key after it. |
| **The native host** is a door from Chrome to the service. | One allowed origin, generated with the package; fixed root-owned launcher with an empty environment; C3 and C4 show another extension is refused, also after an update; the service's own checks (peer UID, one host, the password for loosening) are unchanged. A same-named host in his home and a same-user process posing as the host stay the accepted residuals of `KNOWN-LIMITS.md`: don't add Chrome policies against them here. |
| **The polkit action** turns a password into looser rules. | The shipped file byte for byte; never kept; C7 with his real agent in a session started the real way, including cancel and "asks again". |
| **A downloaded binary** (`gh`) that decides whether qualification records are genuine. | Pinned RPM bytes, signature by a pinned key, pinned binary hash, only the one file taken, no scripts run, no repository; image check and C10; it runs as `aresos-tools` in the unit's sandbox with no login. |
| **A stale or foreign identity after update or rollback.** | Links instead of files in `/etc`; C4; the rehearsal checks. A mismatch fails closed: the tools say Chrome isn't connected. |
| **The owner's hosts leaking** into a public repo or evidence. | The image ships an empty list; tests use made-up hosts under `.invalid` or `localhost`; the privacy check runs on every push. |
| **Test-only pieces reaching a release** (the probe, its host, the second bundle). | They live in the test layer only; the negative image check. |
| **Chrome telling a store about our extension.** | Item 2's case 5 and C9. |

## Steps (one fresh agent each, about 250k tokens; PROGRESS.md after each)

1. **Packer, templates, pins** (item 1 and its unit tests; `record_build.py` and its tests, item 4). Starts at once.
2. **Install proof in the container** (item 2). Starts after step 1.
3. **Image install** (item 3 with the image checks and `os/tests`; `checks_only`; `check_build=build` green once).
   Needs PR #58 on `main` and `linux-aresos`'s answer.
4. **VM, first half:** the second pass and its layer; C1, C2, C3, C6, C10, C11.
5. **VM, second half:** C4, C5, C9, then C7 and C8.
6. **Close:** the rehearsal checks, the two greens on the final head, README lines, the report text.

## Done

Every item built as agreed with `linux-aresos`; the unit tests and item 2's workflow green; `check_build=build`
green once and `check_build=control` green twice on the final head with every PASS line of 18c and of this brief;
the report text in `PROGRESS.md` with **run/read/assumed** marks, the JUDGMENT-CALLs (at least: what the owner sees
in Chrome, the policy form, the `gh` version, how the excluded-sites file is made, the imitation in C4, any CI-only
Chrome flag), PLAN-GAPs, "Not verified" (at least: a real deployment switch with Chrome open; his real sites; the
laptop's own polkit agent) and proposals for `docs/design/CONTROL.md`, which still names
`ExtensionInstallForcelist`. A draft pull request against `main`. Stop there.

## Out of scope, and paths not to touch

- Publishing or pinning a release; anything on the laptop; the owner's excluded hosts; real accounts, real sites,
  a real model; Chrome packages 28, 28a and 28b; a persistent extension identity or a web-store listing.
- `control/aresos_control/`, `control/chrome/extension/`, `control/chrome/native_host.py`,
  `control/chrome/build.py`, `qualify.py`, `qualification.json`, the contents of `builds.json`,
  `control/chrome/packaging/host` and the polkit action file, `control/packaging/`, `control/generated/`,
  `control/settings/`, the existing files under `control/chrome/ci/` and `control/chrome_tests/` (add new files;
  CI's own install in `prepare.mjs` keeps its loopback address and its key),
  `control-chrome.yml` and the qualification workflow. `mod/`, `docs/design/`, `docs/control/`, `STATE.md`,
  `HANDOFF.md`. Under `os/` everything outside "Agree".
- If the extension or the service seems to need a change to pass a check, that is a finding: stop and report.

## Stop and report

- The pinned Chrome doesn't follow the `/etc` links, refuses a `file:` update address, or won't force-install an
  extension from outside its store on this machine. (If the image shipped no Chrome, that would be a PLAN-GAP and a
  stop; it ships one.)
- A request naming our extension's ID goes to anything but a `file:` address and the policy can't stop it.
- polkit refuses, or shows no dialog, for a Chrome started the way the shell starts it. Don't change the action's
  defaults or the way Chrome is started to get green.
- `gh`'s RPM can't be verified with a key you can show is GitHub CLI's, carries scripts, or the binary needs
  something the image lacks.
- The key would have to be kept, passed in or written down for anything to work.
- The service needs a sandbox line loosened for `gh`, `pkcheck` or the excluded-sites file.
- The image needs anything outside "Agree": a package, a repository, an enabled unit, a listener, a sudo or polkit
  rule, a workflow permission or secret, a base change.
- PR #58 isn't on `main`, or `linux-aresos` hasn't answered, when step 3 would start.
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

## Open questions for the lead

1. **Mail's record refresh.** Your note asks for Mail's and Chrome's record refresh under the real unit. On `main`
   only Chrome fetches records (`Qualification.refresh`); Mail has no refresh I could find. What did #150 mean for
   Mail? Until answered, C11 covers Chrome only.
2. **`ccd0fd79…ce15` in `builds.json`.** `QUALIFICATION.md` says a row is added only when an image ships, and none
   with the tool has. The brief keeps the file empty and uses the hash as a test value. Do you want the row anyway
   (#285)?
3. **The update test's form.** C4 imitates the update in one guest; the real deployment switch is checked without a
   browser in the rehearsal. Is that enough for "after an image update the host matches the new id"?
4. **Who extends the release job** for `record_build.py` and the manifest's `chrome_build`: `linux-aresos` in its
   next release package (as written), or a follow-up of ours?
5. **What he sees.** A machine policy makes Chrome say it is managed by an organization, and the button can't be
   removed. `CONTROL.md` already decided the policy route; does he get this as a "try this" note with C2's
   screenshots before the release, or as a question?
6. **His hosts before first use.** The release arrives with an empty list, so his own pages (Aresus among them) are
   not excluded until the live sitting fills it (#200). Should the tools stay unused until then by agreement, or do
   you want a guard?
7. **The policy form.** The brief uses `ExtensionSettings` alone (the research's recommendation) where `CONTROL.md`
   and 18c's Part C name `ExtensionInstallForcelist`. Fine, with the design text updated after the merge?
8. **GitHub CLI's key.** 18c read key ID `5612b36462313325` from the RPM. I couldn't confirm from the sources here
   which published key that is; the builder records it, and step 3 stops if it can't be shown to be theirs.
