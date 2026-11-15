# 18c: CI image test with the Control tools inside

Board #137 and #150. A frozen task for one builder. Part C (the browser side of Chrome) becomes its own brief, 18c-b.

**Order.** B1 (the interactive driver in the container) and the unit's network lines start at once, on `main` as it
is. Part A and B2 are built on a `main` that has the Chrome tool (PR #27, planned for 2026-11-16), because from that
merge on the service doesn't start without Chrome's startup files (see Part A), and that has package 23 (PR #36),
which changes the same image files first. If either hasn't merged when B1 is green, stop and report; the lead
decides whether to wait or to build without it.

**Builder:** a Claude agent (Opus 5.5); move it to Fable 5.2 if the interactive Claude Code driver resists normal
attempts. **Reviews:** the package review and a security review at the same time (`docs/REVIEW.md`, "Tools for
Claude"). The security review gets the extra care of item 5 there: this package puts a system service, a system user
and the app passwords' storage into the image.

## Goal

AresOS's image gains the Control tools: the tool service `aresos-toold` running under its real systemd sandbox as its
own user, the `aresos` and `aresos-mcp` commands, Claude Code's managed files under `/etc/claude-code/`, the
user-scope MCP file and `gh` 2.102 or newer. A throwaway CI image (never pushed, signed or pinned) boots in the CI
virtual machine and proves, inside the guest, that the service works for the daily user `ares`, that Mail runs
against fixture mail servers under the real unit, that the app passwords stay with the service, and that the fake
send asks through the managed ask rule in **interactive** Claude Code, with the `PermissionRequest` result recorded.

**Done means:** the `os/` change agreed by `linux-aresos` and built; `check_build=build` green once and the new
`check_build=control` green twice on the final head; every check below has its PASS line and evidence; the report
states the interactive `PermissionRequest` result plainly.

## Background (read first)

- `docs/control/PLAN.md`: decision 24, "Order of work" item 3 and "What decision 24 changes for the open briefs"
  (the 18c item), and the 2026-11-12 entry. `docs/design/CONTROL.md` section 7 and section 8 item 5.
- `docs/control/TOOLS-HANDOFF.md`, "New work" item 2. `STATE.md`, "Next image package".
- `control/README.md`: "Caller file policy and launch chain" (the installed layout), "Slim Claude Code setup" (the
  managed files, `user-mcp.json` and its install step), "Mail" (owner setup).
- `control/boundary/README.md` and `reviews/18d-base-slim/REPORT.md`: brief 18d's native harness.
- `os/README.md`, `os/Containerfile`, `os/build.sh`, `os/ci/check-build.sh`, `os/ci/vm.py`, `os/ci/overlay/`, and the
  `check-build` job in `.github/workflows/os-image.yml`.

Facts this brief rests on (read in the repo on 2026-11-13, `main` at `b7c9c843`):

- **The unit blocks Mail on main.** `control/packaging/aresos-toold.service` has `RestrictAddressFamilies=AF_UNIX`
  and `IPAddressDeny=any`, so under the real unit Mail can't resolve or reach any server. The lead decided the narrow
  fix for Chrome on 2026-11-09 (H1 in brief `20-integrate` on PR #27's branch):
  `RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6`, no `IPAddressDeny`, everything else unchanged, pinned by a
  static test. It is on PR #27 (`8b7e799c`, `control/chrome_tests/test_unit.py`), not on main. H1 and H2 were
  recorded there as "unit fixed here, live check in brief 18c".
- **The installed layout is fixed by the launcher** (`control/launch.py`): code in `/usr/libexec/aresos-control`,
  dependencies in `/usr/lib/aresos-control/vendor`, config in `/etc/aresos-control`. Every file and every parent must
  be root-owned, not group- or world-writable and no symlink, or nothing starts.
- **Python dependencies** reach a system only one way today: `control/ci/setup.sh` runs `python3 -m pip install
  --require-hashes --only-binary=:all: --target /usr/lib/aresos-control/vendor -r control/requirements.lock` (the MCP
  SDK 2.3.0 and its complete pinned closure, wheels for CPython 3.14 and 3.15). The image's Python is 3.14.8, and
  `python3-pip`, `tmux` and `curl` are in the base (`os/manifest/ci/packages.txt`). The CI containers use Fedora 45's
  Python 3.15, so 18c is the service's first run on 3.14.
- **The drafts don't start as shipped.** `control/settings/service.json` has `owner_uid: 0`, which the daemon refuses
  (`daemon.py`); `proxy.json` names `/home/OWNER`. On AresOS the owner is `ares`, UID 1001, home `/var/home/ares`
  (`os/config/usr/lib/sysusers.d/aresos.conf`). `/home` is a symlink on Fedora Atomic and the file policy opens every
  component without following links, so the home must be written as `/var/home/ares`.
- **Managed hooks need a running service.** If the service is down, the managed `Stop` hook blocks once per turn with
  "service unavailable" (`aresos_control/hooks.py`). The managed files and an enabled, starting service ship together.
- **`gh` is not in the base image** (not in the recorded package list). Chrome's daily record refresh runs inside the
  service with `PATH=/usr/bin:/bin` and refuses `gh` older than 2.102.0 (PR #27,
  `aresos_control/chrome/qualification.py`), so it must be `/usr/bin/gh`.
- **`control/` is outside the image's build context** (`podman build ... --file os/Containerfile os`). Package 23
  (PR #36, not merged) adds a `source` stage that fetches the exact commit from `codeload.github.com` and keeps `mod/`.
- **Mail's tests can't target an installed service.** `control/mail_tests/support.py` builds an in-process `Engine`
  on temporary folders and writes the password into its own transport. Production accounts use the system trust store:
  `mail_account_add` has no CA field (`ACCOUNT_CONFIG`).
- **18d's native harness** (`control/boundary/`, workflow `control-boundary.yml`, Docker on `ubuntu-24.04`, 3 to 4
  minutes a run): native Claude Code **2.1.319** from `package-lock.json` (sha512 integrity), the model faked by
  `native.py`'s loopback streaming Messages double on `127.0.0.1:18081` (a synthetic API key and base URL put into the
  managed settings' `env`), a fixture MCP server (`mcp-fixture.py`, not the real service) and the `stub.py` receiver.
  It runs **print mode only** (`-p --output-format stream-json`). Observed on run 42582079690: user and managed
  `PermissionRequest` allow hooks approve the managed ask in normal and skip-permissions print mode, pinned in
  `permission-request-expected.json`.
- **The CI virtual machine** (`os/ci/vm.py`): QEMU q35, OVMF, 6 GiB, up to 4 vCPUs, KVM when available, a user-mode
  NIC (the host is `10.0.2.2` from the guest), a virtio-serial channel to the CI-only `aresos-ci.service`
  (`os/ci/overlay/checks.py`) that runs fixed actions as root. `check_build=build` builds the image, runs
  `check-image.sh`, builds the CI layer and a raw disk, and boots one pass. Green runs took 36 to 46 minutes
  (42792865417, 42809824712, 42865819198). The job is read-only: no secrets, no `packages` or `id-token` permission.

## Part A: the image change (`os/`)

### os/ change proposal (send as-is to `linux-aresos`; build nothing under `os/` before its answer)

**What:** the image carries the Control tool service (`aresos-toold`), its `aresos` and `aresos-mcp` commands,
Claude Code's managed files and `gh` 2.102 or newer. Nothing else in the image changes. Brief 18c builds this only as
throwaway CI images (never pushed, signed or pinned). Whether a release carries it is the release's decision, with
the owner's OK.

**Paths under `os/` that change, and why:**

1. `os/Containerfile`: a stage that takes `control/` from the exact build commit, the way package 23's `source`
   stage takes `mod/` (fetch `codeload.github.com/Ares-Empire/AresOS/tar.gz/<full commit>`, keep `control/`). The
   `aresos` stage copies it to `/tmp/aresos/control`. The `FROM` digest and the other stages stay. Why: `control/` is
   outside the `os/` build context, and one way of taking repo sources keeps provenance simple.
2. `os/build.sh`: a new `control` mode, run in the `aresos` stage **before** `configure` (which runs the updater
   audit and removes `/tmp/aresos`). It installs, all root-owned, with no group or world write and no symlinks:
   - `/usr/libexec/aresos-control/` with `launch.py`, `aresos_control/` and `generated/` from `control/` (files 0644,
     folders 0755), and under `chrome/` the files the service loads when it starts once the Chrome tool is merged
     (on PR #27's `8b7e799c`: `build-id.json`, made by `control/chrome/build.py` at image build, and
     `qualification.json`);
   - `/usr/lib/aresos-control/vendor/` from `python3 -m pip install --no-cache-dir --require-hashes
     --only-binary=:all: --target` with `control/requirements.lock` (pip refuses any wheel whose SHA-256 isn't pinned);
   - `/etc/aresos-control/service.json` and `proxy.json` from `control/settings/`, 0644, with the AresOS values
     `owner_uid: 1001` and home `/var/home/ares` (folders `Downloads` and `Documents`, item 8); the build checks them
     against `ares` in `aresos.conf`;
   - `/usr/bin/aresos`, `/usr/bin/aresos-mcp`, `/usr/bin/aresos-toold` from `control/packaging/`, 0755;
   - `/usr/lib/systemd/system/aresos-toold.service`, `/usr/lib/sysusers.d/aresos-tools.conf` and
     `/usr/lib/tmpfiles.d/aresos-tools.conf` from `control/packaging/`, 0644, with the unit **enabled**
     (`multi-user.target.wants`), because the managed `Stop` hook reports "service unavailable" whenever it is down;
   - `/etc/claude-code/managed-settings.json` (from `control/settings/managed-settings.draft.json`) and
     `/etc/claude-code/CLAUDE.md`, 0644, folder 0755, and no `managed-mcp.json`;
   - `/usr/share/aresos/control/user-mcp.json` from `control/settings/user-mcp.json`, 0644, which he installs at user
     scope with the step in `control/README.md`;
   - `/usr/share/aresos/manifest/control.json`: the source commit, the SHA-256 of every installed Control file and
     the installed wheel list, for image diffs.
3. `gh` 2.102.0 or newer at `/usr/bin/gh`, because the service calls `gh` with `PATH=/usr/bin:/bin`: Fedora's RPM
   through `os/packages.lock.json` if Fedora 44 `updates` carries 2.102.0 or newer at `check_build=resolve`; otherwise
   GitHub's release RPM pinned like Chrome (`os/gh.lock.json` with version, URL and SHA-256, checked before install,
   no repository added). His own `gh` in `~/.local/bin` stays first on his PATH. For this, `os/ci/check-resolve.sh`
   gains one narrow step: it reports Fedora's `gh` version and resolves it into the candidate lock, leaving every
   other locked package as it is (today the script never looks at `gh`).
4. `os/ci/image-checks.sh`: checks in the built image for every path above (owner, mode, no symlinks, content equal
   to the commit's files), the unit enabled, `gh --version` at least 2.102.0, no `managed-mcp.json`, and
   `aresos --help` through the installed launcher.
5. `os/ci/check-build.sh` and `.github/workflows/os-image.yml`: a third `check_build` choice, `control`, in the
   existing read-only `check-build` job (no secrets, no new permissions): build, image checks, then one VM pass with
   the Control test layer. No other job changes.
6. CI-only files that never reach a release: `os/ci/overlay/checks.py` gains fixed `control-*` actions and their
   exports; a new `os/ci/control/` holds the Control test layer (`FROM localhost/aresos:vm`: the pinned Claude Code
   binary, the per-run fixture mail CA in the guest's trust store, `/etc/hosts` names for the fixture servers at
   `10.0.2.2`, a fixture MCP server standing for one of his own) and `control_vm.py`, which boots it like `vm.py` and
   runs the actions. `vm.py`'s own sequence stays as it is.
7. `os/tests/`: static tests for the `control` mode and its install map. `os/README.md`: one paragraph on Control in
   the image.
8. The folders the tools may take files from and save files to (mail attachments). The config names
   `/var/home/ares/Downloads` and `/var/home/ares/Documents`. Neither exists on the laptop today (checked
   2026-11-13: `ares` has no `Downloads`, `Documents` or `Desktop`, and no `user-dirs.dirs`), and the file policy
   neither creates folders nor follows other names. Proposed: one tmpfiles line each in the image that creates the
   two folders for `ares` if they are missing (0700, `ares`), and nothing else in his home. Which folders these are
   was the owner's choice: "Downloads and Documents" (board #203, 2026-11-13). The mechanism is `linux-aresos`'s
   (question 11).

**Must not change:** the base digest, the other locked packages and the Chrome pin, the accounts (`ares` stays 1001;
`aresos-tools` is a new system user with no login and no password), sudo, polkit, the unit masks, the session, PATH,
repositories, `os/release/`, `os/owner-tools/`, `os/manifest/release.json` and `os/manifest/releases/`, and the
release, switch and rehearsal jobs. No new enabled unit besides `aresos-toold.service`, no network listener (the
service has Unix sockets only), nothing in Python's system site-packages, nothing in `/var/home/ares` beyond the two
empty folders of item 8. Claude Code itself is not in the image; he installs it in his home as on any OS.

**One change outside `os/` that this needs:** the unit's network lines as decided for Chrome (PR #27, H1):
`RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6` and no `IPAddressDeny=any`. Without it Mail can't reach a server
under the real unit.

**Later, with 18c-b:** Chrome's extension policy, its native host manifest and launcher, and the excluded-sites file
(Part C). Until then the service starts with Chrome's adapter and no browser connected.

### Agreed with `linux-aresos` on 2026-11-13 (these win over the proposal text above)

`linux-aresos` agreed the proposal with these changes. Build Part A as amended here.

1. **Sources:** through package 23's `source` stage: one fetch of the build commit, keeping `mod/` and `control/`.
2. **Base:** cut Part A from a `main` that has package 23 (PR #36) and the Chrome tool (PR #27). Package 23 also
   changes `os/ci/overlay/checks.py` and `os/ci/image-checks.sh`.
3. **`build.sh control` before `configure`:** yes. Update, in the same PR, whatever list pins the enabled units, so
   the updater audit, the unit policy and the polkit checks see the new unit and user.
4. **`gh`:** as proposed, with the one extra step in `check-resolve.sh`.
5. **The service user gets fixed numbers.** `aresos-tools` is still created at boot by sysusers, but with a fixed
   UID and GID in its sysusers line. Each deployment has its own `/etc` while `/var` is shared: after `at previous`
   and a later update, a user created anew with a dynamic number could stop matching the owner of the state folders,
   or another system user could get the old number and read the stored passwords. Pick one number for both, below
   1000, that Fedora's static list (`/usr/share/doc/setup/uidgid`) and the image's own sysusers and passwd files don't
   use, and record the evidence. This is the one allowed change to `control/packaging/aresos-tools.sysusers`, with a
   pin test; the CI containers keep working with it.
6. **The unit is enabled, and a broken service never costs him his session.** Enabling it through
   `multi-user.target` is the normal way and stays (the target wants it, with systemd's usual ordering). What may
   not exist: a login, session, display or recovery unit that requires `aresos-toold.service` or orders itself after
   it. The unit keeps `Type=simple`, so a slow or failing start never holds the target. Check 6 of B2 also runs with
   the service **failed**, not only stopped: a CI-only drop-in under `/run/systemd/system` makes it fail (the config
   in `/usr/share` can't be edited), armed before a fresh session starts. Then the desktop session comes up as
   usual, Claude Code starts and does ordinary work, and our tools refuse clearly. Claude Code on the laptop is his
   help channel.
7. **The config follows the image.** `owner_uid` and the home are derived at build from `aresos.conf`, not written
   as a second literal. `service.json` and `proxy.json` move from `/etc/aresos-control/` to
   `/usr/share/aresos/control/`: `/etc` is merged per deployment, and a file changed there once silently stops
   following the image, while the image owns these values. That means changing the two path constants (`CONFIG` in
   `control/launch.py`, the `--config` default in `aresos_control/daemon.py`) with their tests, `control/ci/setup.sh`
   and the README, and nothing else of the launch chain; its root-owned, no-symlink rule applies to the new folder
   unchanged. `/etc/claude-code/` stays, since Claude Code fixes that path: add an image check, and a check action in
   the booted guest, that its two files equal the image's.
8. **`checks.py`:** prefer one small generic hook that loads the Control layer's own actions file from
   `os/ci/control/`, so later Control changes stay in that folder. If the hook costs more than a few lines, fixed
   `control-*` actions are acceptable. `vm.py`'s sequence stays untouched.
9. **Fixture servers on the runner:** acceptable, with a negative check in `image-checks.sh`: the image without the
   CI layer has no fixture CA in its trust store and no fixture names in `/etc/hosts`.
10. **One image, no build switch, but his yes first.** Part A merges to `main` only after the owner has said yes to
    "the next release carries the Control tools: a background service, and two managed hooks in every Claude Code
    session on the laptop". The lead asks him with check 6's numbers; the report states them for that.
11. **The folders:** tmpfiles, two lines, fixed names, 0700 `ares`. No `xdg-user-dirs-update`.
12. **The update from release 27** is covered by the next release's rehearsal. For it, provide check actions that
    need no Claude Code binary: the service user exists with the fixed numbers, the unit is active, the
    `/etc/claude-code` files equal the image's, the two folders exist, and the state folders belong to the service
    user. Put them where the rehearsal can call them and say where in the report.
13. **The command name `aresos` is shared.** The owner asked (board #195) for `aresos update` instead of the long
    owner-tools command, so a later OS package puts a small dispatcher of its own at `/usr/bin/aresos`, in front of
    Control's command. These words are reserved for the owner tools and never become an app name or a top-level word
    of Control's CLI: `update`, `previous`, `rollback`, `keep-stock`, `check`, `title`, `records`, `export`, `login`,
    `verify`, `switch`, `install`, `prepare`, `layout`, `reboot`, `logs`. Add a test under `control/tests/` that
    fails if a served app or top-level word of the CLI (today `admin`, `log` and the app names) equals one of them.
    18c still installs Control's command as `/usr/bin/aresos`.
14. **The idle footprint** goes in the report: the service's memory and wake-ups while nothing uses it, measured in
    the guest. He plays on this laptop.
15. **`.github/workflows/os-image.yml`** is also changed by package 22c and the next release. Keep the `control`
    choice purely additive, and tell the lead before the first change to that file so `linux-aresos` hears it first.
16. **Before merge:** when the reviews say SAFE, `linux-aresos` reads the `os/` diff.

### Details for the builder

- **The unit's network lines.** If PR #27 hasn't merged when you start, make the same change on this branch, byte for
  byte as on `8b7e799c`: the comment line and `RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6` replacing the two
  lines, plus a static test that pins every `[Service]` line (the same list as `control/chrome_tests/test_unit.py`,
  under `control/tests/`). Identical lines merge cleanly with Chrome's. No other packaging change.
- **`aresos-tools` is created at boot** by `systemd-sysusers` from the image's file, the same path an installed laptop
  takes after an update (its `/etc/passwd` is local). Don't create it at build unless `linux-aresos` answers otherwise
  (question 5). tmpfiles creates `/run/aresos-tools` and both state folders at boot, owned by it.
- **Chrome's startup files.** Read in the merged tree what the service loads when it starts (`Engine` builds every
  adapter; on `8b7e799c`, `Chrome.__init__` in `aresos_control/chrome/adapter.py` reads `chrome/build-id.json`, or
  runs `chrome/build.py`, and reads `chrome/qualification.json`). Install exactly those, with `build-id.json` made at
  image build. Nothing of the browser side: no policy, no native host manifest, no extension. Ship the generated
  files as they are, also where they now name Chrome (`user-mcp.json`, the ask rules), and record what
  `aresos-mcp chrome` answers with no browser connected: a clear refusal, never a hang.
- **The two config files** come from the drafts with only `owner_uid`, `home` and `folders` changed, and without
  the drafts' `_comment` (it calls the file a draft; no code reads that key). `folders` is
  `/var/home/ares/Downloads` and `/var/home/ares/Documents`, as the owner chose (board #203).
- **`gh`.** Extend `os/ci/check-resolve.sh` by the one step of item 3, then run `check_build=resolve` once. If
  Fedora's `gh` is 2.102.0 or newer, add it to `packages.lock.json` from that resolution. If not, add `os/gh.lock.json` and the install step beside Chrome's in `build.sh packages`, with the
  same checks (bytes, name, version). Record which route and why as a JUDGMENT-CALL.
- **Self-check at build:** after the install, run the installed launcher once as root (`aresos --help`) so a broken
  tree fails the build, and run `control/generate.py --check` with the vendored dependencies if it runs without
  network; otherwise rely on `control-base` and say so.
- `bootc container lint` must still pass. `check_build=build` must pass once with Part A: the existing policy VM pass,
  the updater audit, polkit and image checks all see the new unit and user.

## Part B: the CI test

A throwaway image, booted in the CI virtual machine, with fixed checks inside the guest. Nothing is pushed, signed
or pinned. Develop the interactive driver in the cheap container first (B1), then run everything in the VM (B2).

### B1. The interactive driver, first in the boundary container

Interactive Claude Code needs a terminal and a scripted answer. Build one driver for both places:

- **Terminal:** run `claude` inside `tmux` (in the base image; add it to `control/boundary/Dockerfile` for the
  container) at a fixed size such as 120x40. Read the rendered screen with `tmux capture-pane -p`, never raw escape
  codes. Wait for named text with deadlines, never fixed sleeps as proof, and save every screen you act on.
- **Model:** a new module beside `native.py` that speaks its streaming Messages format over several turns (leave
  `native.py` itself as it is), driven by a script per case, not one fixed sequence. A script is a list of steps;
  the usual one is: call `mcp__testapp__prepare_send` with the fixed message of `control/tests/support.py`
  (`message()`), read that tool result, call `mcp__testapp__send` with the `approval` copied unchanged, then end
  the turn with plain text. The double tells two kinds of further request apart: a continuation the managed `Stop`
  hook caused (answer with plain text, and record that it came) and the next owner prompt the driver typed (run the
  script's next send, which the "don't ask again" case needs for send 2 in the same session). In the container,
  where `mcp-fixture.py` has no preparation, use a fixed approval as 18d does.
- **First-run dialogs:** pre-seed `~/.claude.json` as 18d's `precedence.py` does (onboarding done, the synthetic key
  approved, the work folder trusted). 18d never ran interactive skip-permissions mode, so nothing there seeds its
  warning. Find out first, on the pinned binary, how that warning is accepted (a setting, or the driver answering the
  dialog once) and record it. After that setup is fixed, any dialog the driver doesn't expect fails the case with
  its screen saved.
- **Answers:** "Yes", "Yes, and don't ask again" (if Claude Code offers it) and "No", chosen by the option text on
  screen, not by position alone.
- Keep `-p` cases, `precedence.py` and `permission-request-expected.json` exactly as they are. Add the interactive
  cases beside them, and run them in `control-boundary.yml` on every pull request touching `control/`.
- Use the same pinned Claude Code 2.1.319 as 18d, so the print and interactive results compare on one version.

**The whole table runs here, in the container.** Which rule or hook wins is Claude Code's own behavior and doesn't
depend on the image, so the cheap harness carries all of it and the VM (B2, check 9) repeats only four cases against
the installed files and the real service. Each case is a fresh `claude`, the generated managed settings unless the
case says otherwise, and a user allow rule for `mcp__testapp__prepare_send` in every case. Count arrivals at the
`stub.py` receiver, as 18d does.

| Case | Normal | Skip-permissions | Expected |
|---|---|---|---|
| No extra rule, answer "Yes" | yes | no | prompt with the `question` first; one arrival |
| No extra rule, answer "No" | yes | yes | prompt; no arrival |
| User, project, local allow rule for `mcp__testapp__send` | yes | yes | prompt; no arrival |
| User `PreToolUse` hook returning allow | yes | yes | prompt; no arrival; the hook ran once |
| "Yes, and don't ask again" (DAA), then sends 2 and 3 | yes | yes | prompts 2 and 3 shown; arrivals only for "Yes" |
| `PermissionRequest` allow hook, user level | yes | yes | **record**: prompt shown or not, hook calls, arrivals |
| `PermissionRequest` allow hook, managed level | yes | yes | **record**, as above |

In the DAA case, send 2 runs in the same session and send 3 in a new one; record whether Claude Code offers the
option at all and what it wrote to which settings file. Pin the four `PermissionRequest` outcomes in an
`interactive-permission-request-expected.json` beside 18d's, so a later change fails.

### B2. The VM test (`check_build=control`)

On the runner: generate the per-run fixture certificate and a random synthetic Dovecot password; start the pinned
GreenMail 2.1.15 and Dovecot 2.3.21.1 images from `control/ci/mail/run.sh` (same digests, a copy of `dovecot.conf`
with that password) with their ports bound to `127.0.0.1` only; fetch Claude Code 2.1.319's Linux x64 package and
check it against `control/boundary/package-lock.json`'s integrity; build the image, the CI layer, the Control test
layer and the disk; boot one pass. The private key never enters the guest. Seeding mail and reading what arrived run
on the runner against the fixtures, never through the service.

In the guest, as root through the CI channel; the owner's steps run as `ares` through `runuser -u ares`, and root
stands in for his `sudo` (`ares` has no password in CI):

1. **Files.** Every path of Part A has the owner, mode and content of the commit; no symlinks; no `managed-mcp.json`.
2. **The service.** `aresos-toold.service` is active after boot without anyone starting it, `NRestarts=0`, its main
   process runs as `aresos-tools` with `NoNewPrivs: 1` and no effective capabilities; `systemctl show` gives the
   unit's sandbox values; `/run/aresos-tools` and its sockets have the modes the merged `daemon.py` sets (read them
   from the code; on `8b7e799c`: `act.sock` and `chrome.sock` 0666, `admin.sock` 0600), owned by the service user. Save `systemd-analyze security aresos-toold` (recorded, not asserted). Record SELinux's mode and
   any AVC denial naming the service, its files or its sockets; a denial fails.
3. **Entry points for the daily user.** As `ares`: `aresos testapp list --input '{"limit":3}'` and `aresos log`
   answer; `aresos-mcp mail` and `aresos-mcp control` answer MCP `initialize` and `tools/list` with exactly the tools
   and instructions in `control/generated/`. A throwaway second user (created in this VM only) is refused by
   `act.sock` and by the proxy; `ares` is refused by `admin.sock`.
4. **The precondition check.** As `ares`, `aresos testapp prepare_send` succeeds. With `managed-settings.json` made
   group-writable, then with one ask rule removed, it refuses with `boundary_not_installed`; after each, restore the
   file and prove its hash equals the shipped one. Then clear the successful preparation (see "A clean baseline"
   below).
5. **The user-scope install step.** As `ares`: put Claude Code where its installer would
   (`~/.local/share/claude/versions/2.1.319`, linked from `~/.local/bin/claude`); add a fixture server of "his own" at
   user scope; run the install step from `control/README.md` word for word, twice. `~/.claude.json` then holds
   `control` and `mail` exactly as in `/usr/share/aresos/control/user-mcp.json`, his own entry unchanged, nothing
   duplicated; `claude mcp list` shows them connected. The harness then adds `testapp` the same way (`proxy testapp`).
6. **An ordinary session stays ordinary.** The managed hooks run in every Claude Code session he starts, also ones
   that never touch our tools. With B1's driver, as `ares`, with a notification hook of "his own" (`Stop` and
   `UserPromptSubmit`, each writing a line to a file) beside ours: a session whose model only calls his own fixture
   MCP tool and answers.
   - Service healthy and nothing pending: the tool call runs without a prompt of ours, his hooks ran, the turn ends
     with no extra model request, and nothing of ours appears on screen.
   - Service stopped (`systemctl stop`): his prompt still reaches the model, his tool call still runs, and the turn
     ends within a fixed deadline. Record exactly what he sees and what it costs: the text on screen, and how many
     extra model requests the `Stop` hook's "service unavailable" reminder causes per turn. Start the service again
     and show the next turn is clean.

   Report the stopped-service result as a JUDGMENT-CALL with the numbers: whether a session that never used our
   tools should get that reminder at all.
7. **Mail under the real unit.** Through the installed entry points only:
   - onboarding: `aresos admin mail account add --input JSON` in a terminal (tmux), the password typed at the
     prompt, Dovecot for IMAP and GreenMail for SMTP, then `account_settings` with `sent_policy: client`; the account
     is ready;
   - read: a mail seeded into INBOX is found with `search` and read with `read`, marked `untrusted_content`, and its
     flags are unchanged;
   - send: `compose`, `prepare_send`, `send` with the approval; GreenMail holds exactly one arrival, the operation is
     `done` and the Sent copy is in the Sent folder;
   - delete: `prepare_delete` and `delete` move the message to Trash;
   - files: a file `ares` put in the first configured folder goes out as an attachment and arrives byte for byte,
     and a received attachment is saved into that folder, owned by `ares`. A file outside the configured folders is
     refused. The folders exist because the image created them (Part A item 8), never because the test did;
   - one Mail send through Claude Code: the prompt shows, "Yes" sends it once.

   The existing Mail tests are not reused as tests (they drive an in-process engine); their fixtures and flows are:
   the server images, `dovecot.conf`, the certificate steps, `ready.py`, and the flows of `test_admin.py`,
   `test_read.py`, `test_compose.py`, `test_outcomes.py` and `test_changes.py`. Put the new flows in
   `control/ci/image/`. The container suites keep proving Mail's details on every pull request.
8. **The app passwords.** As `ares`, `/var/lib/aresos-tools` and the password files can't be listed or read. As root:
   the password folder is 0700 and its file 0600, both `aresos-tools`; the synthetic password occurs in exactly that
   one file, and not in the journal, `~ares` (including Claude Code's transcripts), `/tmp`, the evidence folder or
   `operations.jsonl`. Evidence records its hash and the counts, never the password.
9. **The ask, interactive, against the installed files** (B1's driver against the real service and testapp's real
   receiver). Four cases, each a fresh `claude` as `ares` with the managed files exactly as the image shipped them
   and a user allow rule for `mcp__testapp__prepare_send`. Count arrivals from `aresos testapp operation_status` and
   from the receiver's SQLite, read by root. Every case starts from a clean baseline (below).

   | Case | Mode | Expected |
   |---|---|---|
   | No extra rule, answer "Yes" | normal | prompt with the service's `question` first; one arrival |
   | No extra rule, answer "No" | skip-permissions | prompt; no arrival; the `Stop` hook's reminder reaches the model's next request |
   | User allow rule for `mcp__testapp__send`, answer "No" | skip-permissions | prompt; no arrival |
   | `PermissionRequest` allow hook, user level | normal | the same outcome as the container's pin for this case |

   The managed files aren't edited in the VM; the managed-level hook cases stay in the container. If a VM case
   differs from the same case in the container, that is a finding: stop and report it.
10. **`gh`.** `/usr/bin/gh --version` is at least 2.102.0, also when run as `aresos-tools` under the unit's sandbox
    (`systemd-run` with the unit's properties).

**A clean baseline.** Cancelling an operation doesn't clear it: the engine keeps it in the pending list with its
notice set until the notice is acknowledged (`notice_ack`; `test_operations.py` pins this). So after every case or
check that prepared something: save the evidence first (the reminder text, the operation's state), then cancel what
is still reserved, acknowledge the expected notice, and assert that nothing is pending before the next case starts.
A leftover notice would show up in a later case's hook output and spoil it.

Finally restart the service and check it comes back with the Mail account still ready and nothing pending, then
power the guest off cleanly.

### Evidence and PASS lines

Each check prints one fixed line into the run log and writes its evidence through the CI channel (bounded frames,
the uploaded `check-build-evidence` artifact, under 180 MB, never the image, the disk, keys or passwords):

| Line | Evidence |
|---|---|
| `CONTROL_IMAGE_FILES_PASS` | `control/files.json`: path, owner, mode, SHA-256, commit hash |
| `CONTROL_SERVICE_SANDBOX_PASS` | `control/unit.json`, `security.txt`, `journal-aresos-toold.txt`, `selinux.txt` |
| `CONTROL_ENTRY_POINTS_PASS` | `control/entry-points.json` with every refusal's error code |
| `CONTROL_PRECONDITION_PASS` | `control/precondition.json`: each refusal and each restored hash |
| `CONTROL_USER_MCP_INSTALL_PASS` | `control/user-mcp-install.json`: the MCP entries before and after each run |
| `CONTROL_ORDINARY_SESSION_PASS` | `control/ordinary/<case>/`: screens, his hooks' lines, the model requests counted |
| `CONTROL_MAIL_FLOWS_PASS` | `control/mail-flows.json` (with the attachment hashes), plus the runner's fixture logs |
| `CONTROL_PASSWORDS_PRIVATE_PASS` | `control/passwords.json`: refusals, modes, hit counts, the password's hash |
| `CONTROL_INTERACTIVE_ASK_PASS` | `control/interactive/<case>/`: screens, hook events, arrivals, transcript |
| `CONTROL_PERMISSION_REQUEST_RECORDED {json}` | `control/permission-request.json` |
| `CONTROL_GH_PASS` | `control/gh.txt` |
| `CHECK_BUILD_CONTROL_PASSED` | the run itself |

### What runs when

- **Every pull request touching `control/`** (unchanged workflows plus B1): `control-base` (with the unit pin test),
  `control-mail`, and `control-boundary` with the interactive container cases (a few minutes more).
- **On demand only:** `os-image.yml` with `checks_only` (the static `os/tests`, under 10 minutes), `check_build=resolve`
  (once, for `gh`), `check_build=build` (once, with Part A) and `check_build=control` (the VM test, about 50 minutes;
  twice on the final head, by rerunning the same run). The `os-image` workflow stays manual dispatch only.
- **Budget:** at most 10 `check_build` runs in all and 5 `checks_only` runs. When the Ubuntu snapshot mirror fails
  (packages 23 and 27 lost runs to it), wait for it; don't retry in a loop.

## Part C: Chrome (brief 18c-b, after PR #27 merges)

Not built in this run. Write the reusable pieces of Parts A and B so that Chrome adds files and cases, not a new
harness. 18c-b will add:

- **Image:** the extension policy (`ExtensionInstallForcelist` and the toolbar pin) under
  `/etc/opt/chrome/policies/managed/` (package 21's image check already proves that folder can be created); the
  native host manifest `org.aresos.chrome` under `/etc/opt/chrome/native-messaging-hosts/`, its launcher
  `/usr/libexec/aresos-control/chrome/host` (0755) and `native_host.py` (0644);
  `/etc/aresos/control/chrome-excluded-sites.json` with `{"format":1,"hosts":[]}`, 0640, root and the service's
  group. All as described in PR #27's `control/chrome/packaging/README.md`. (The service's own startup files and the
  generated `chrome` entries already ship with Part A.)
- **Settled before 18c-b:** where the signed extension and its update manifest are served from (the packaging README
  names "the image's local HTTPS update endpoint", which doesn't exist yet), and where the production extension key
  lives (outside the repo; a key is a credential).
- **Tests:** test group 12 runs in 18d's container harness as PR #27 plans. In the VM: Chrome's asking tools ask
  through B's interactive driver; the native host reaches `chrome.sock` as `ares` and is refused for another user;
  the daily record refresh runs once under the real unit as `aresos-tools`, `gh attestation verify` working inside
  the sandbox with its cache under `/var/lib/aresos-tools`, and its result line in the log. Until an attested record
  is published on the `chrome-qualification` branch, check the "refused, held record retained" path and an offline
  bundle verification; that fetch is the only check that reads the real network (the public repository).

## Out of scope

- Publishing or pinning a release, or changing what the laptop installs. Anything on the owner's laptop: no
  installs, no `sudo`, no services, containers or VMs there. Image, container and VM work runs on GitHub's runners.
- Changes to Mail's or the base's behavior (`control/aresos_control/`), the generated files, `mod/`, the install
  docs and `docs/EMERGENCY.md`, and the design and plan files (`docs/design/`, `docs/control/`). Proposals for those
  go in the report.
- Remote Control and the phone, real accounts, a real model, Claude Code's optional sandbox.
- The update path from release 27 (an existing local `/etc`, `aresos-tools` added to a local `/etc/passwd`): that
  belongs to the next release's rehearsal. Name it under "Not verified".

## Paths the builder must not touch

`mod/`; `docs/INSTALL*.md`, `docs/EMERGENCY.md`, `docs/design/`, `docs/control/`, `STATE.md`, `HANDOFF.md`,
`README.md`; `os/release/`, `os/owner-tools/`, `os/manifest/base.json`, `os/manifest/release.json`,
`os/manifest/releases/`, `os/keys/bazzite.pub`, `os/policy/`, the existing files under `os/config/`, and the `FROM`
digest; in `os-image.yml` every job except `check-build`, and no new permission anywhere; `control/aresos_control/`
(but for the one constant named below), `control/generated/`, `control/settings/`, `control/requirements.lock`, `control/mail_tests/`, `control/ci/mail/`,
the existing files under `control/tests/`, and 18d's `precedence.py`, `native.py`'s behavior and
`permission-request-expected.json`; in `control/packaging/` everything except the unit's two network lines and the
sysusers line's fixed numbers; in `control/launch.py` and `control/aresos_control/daemon.py` everything except the
two config path constants (agreed change 7). For that same change, and only for it, the old config path may be
replaced by the new one where existing tests and CI files name it (`control/tests/test_integration.py` in five
places, `control/ci/setup.sh`, the README, and the folder Chrome's CI Dockerfile creates), with no assertion
changed. Other worktrees. Anything under `os/` beyond the agreed proposal needs `linux-aresos`'s OK through the lead first: stop
and report instead.

## Acceptance

- Part A as agreed with `linux-aresos`; `check_build=build` green once on it.
- `check_build=control` green twice on the final head, every PASS line present, the evidence uploaded.
- The container interactive cases green twice in `control-boundary`.
- The interactive `PermissionRequest` result stated plainly in the report, with run IDs and log lines, and pinned.
- No secrets, real addresses, account names or mail-provider names anywhere, evidence included.

## Report (`reviews/18c-image-test/REPORT.md`)

AGENTS.md's format: **Done**, **Verified** (each PASS line with run ID and log line), **Not verified**,
**JUDGMENT-CALL**, **PLAN-GAP**, **Open questions**. Put the `PermissionRequest` result first, in plain words: does
an allow hook approve the managed ask interactively, at user and at managed level, in each mode, and does that match
18d's print mode. Mark every claim **run** (run ID and log line), **read** (file and version) or **assumed**. Add
the measured times of the VM steps.

- **JUDGMENT-CALL:** anything hard to undo or that changes how AresOS behaves for him once released: the unit enabled
  by default, the owner values baked into the config, the two folders the tools may use and that the image creates
  them, what an ordinary session shows while the service is down (check 6), the `gh` route, anything you chose where
  this brief or `linux-aresos`'s answers left a choice. Give what you chose, the alternatives, why, and what changing it later
  costs. These go to the owner before merge.
- **PLAN-GAP:** anything this brief, the design or the plan gets wrong or misses, for example a check that can't be
  done the way it is written here.

## If unsure

Take the option that keeps every asking tool asking, changes the image least and leaves his own Claude Code setup
alone, and say so in the report.

## Stop rules

- **Stop and report** if a managed ask can be shown **not** to ask interactively with an allow rule at any level,
  after "Yes, and don't ask again", with a `PreToolUse` allow hook, or in skip-permissions mode. That breaks section
  7's guarantee; the lead takes it to the owner. A `PermissionRequest` hook approving is **not** a stop: it is the
  accepted residual; record it.
- Stop if the image needs anything outside the agreed proposal: another package, a policy, polkit or sudo change,
  another enabled unit, a repository, a base change, a credential, or a write permission in a workflow.
- Stop if Mail under the real unit needs any sandbox line loosened beyond H1's.
- If a pinned download has vanished upstream (Chrome's RPM, a Fedora package), renew only that pin and record it as a
  JUDGMENT-CALL, as package 27 did.

## Owner decides

Throwaway CI images need no OK (`CLAUDE.md`). Already his: the folders the tools may use, "Downloads and Documents"
(board #203, 2026-11-13). His before merge: the report's JUDGMENT-CALLs, and his yes to a release carrying Control
(agreed change 10). The live tests on his laptop are later and his.

## Open questions for `linux-aresos` (the lead sends them with the proposal)

1. Does Control enter the image through package 23's `source` stage (fetch the commit, keep `mod/` and `control/`),
   or would you rather pass a second build context (`--build-context control=control`)?
2. Package 23 also changes `Containerfile` and `build.sh`. Which lands first, and should 18c rebase onto 23 if it
   merges meanwhile?
3. Is `build.sh control` before `configure` in the `aresos` stage the right place?
4. `gh`: Fedora's RPM through `packages.lock.json` if it is 2.102.0 or newer, otherwise GitHub's release RPM pinned
   like Chrome, with `check-resolve.sh` extended by the one step that reports and resolves Fedora's `gh`. Agreed?
5. `aresos-tools`: created only at boot by `systemd-sysusers` (as on the laptop after an update), or also at build
   like `ares`?
6. The unit enabled by default in the image: agreed?
7. The image sets `owner_uid: 1001` and home `/var/home/ares` in `/etc/aresos-control/`: agreed that the image owns
   these two values?
8. CI: a `control` choice in the existing read-only `check-build` job, the Control test layer in `os/ci/control/`
   on top of `localhost/aresos:vm`, and `checks.py` gaining `control-*` actions. Agreed, or would you rather keep
   `checks.py` untouched and give the layer its own channel service?
9. Fixture mail servers on the runner, reached from the guest through QEMU's user network at `10.0.2.2`, ports bound
   to the runner's loopback only, with `/etc/hosts` names and the fixture CA in the CI layer only. Acceptable?
10. Once Part A is on main, the next release built from main carries Control. Fine, with Control named in that
    release's image diff and the owner's release OK, or should it stay out of releases until he approves it
    separately?
11. `ares` has no `Downloads` or `Documents` on the laptop. Is one tmpfiles line each (create if missing, 0700,
    `ares`) the right way for the image to provide them, or do you want the session to run `xdg-user-dirs-update`
    instead?
12. The update from release 27 (a local `/etc`, `aresos-tools` added by sysusers at the first boot, the new folders)
    isn't tested by 18c. Will the next release's rehearsal cover it?

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5, 6 and 7 apply; its Minecraft, Gradle and Windows parts don't. Keep the laptop's
  load light: no containers, VMs or root on it; run only static tests locally that need neither.
- B1 and the unit's network lines may start at once; nothing under `os/` starts before the lead has passed on
  `linux-aresos`'s answers, and where an answer differs from Part A, the answer wins.
- Work in your own worktree on branch `pkg/18c-image-test`, from `main`. Commit in small steps, push the branch, open
  a draft PR against `main` with `gh pr create --draft`. Never merge, never push to `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Name the model in a trailer on your commits, for example `Claude-Model: opus-5.5`.

**Model:** a Claude agent on Opus 5.5. The work is integration across the image build, the CI virtual machine and a
terminal driver for Claude Code, with about 50-minute VM runs over several days; Codex is unavailable from
2026-11-14 to 2026-11-17 and its plan ends on 2026-11-21, which a multi-day VM loop would straddle. Package 27, the
nearest kind of work, was built by an Opus agent. Fable 5.2 if the interactive driver resists. Reviews: a fresh
`gpt-6.1-sol` (high) package review while Codex is available, otherwise a fresh Claude agent on Opus; a security
review by `gpt-6-astra` or Fable 5.2, because the package installs a service, a system user and the password store.
