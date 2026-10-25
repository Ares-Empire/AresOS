# 13: keyboard layout — 13g recovery guide fixes

**Current: 13g guide-only review fixes completed; 13f VM acceptance retained.**
The owner approved keeping backup Bazzite on the installer's layout; a direct
US-in-AresOS → rollback run was **not performed**. The guides now refresh stock's
identity-resolved title before every reboot after a reorder, invalidate stale
titles, and spell out recovery-account commands and F12 → Linux while Windows
stays the firmware default after §5. No harness, owner script, image or VM changed.
PR #12 stays ready, subject to privacy passing on this pushed head; closing
privacy receipts and the actual closed ledger are recorded in the PR body.
Owner review before merge and physical/live-desktop/laptop followability gates
remain open. Physical installation remains **NOT RELEASED**. No merge or new
publication occurred. See the [13g section](#13g--review-fixes-for-recovery-steps-2026-10-25).

**Historical 13e: STOP / PLAN-GAP.** 13e’s fresh probe passed.
Real two-entry stock repair passed for both de/us starting states, pin and the
corrected German stock boot/login/password-sudo passed. Qualification then stopped
at an unsupported `.` in the physical-input setup command. No signed switch,
AresOS/foot, layout round trip or rollback ran. Physical installation and live
KDE/laptop followability remain NOT RELEASED. See the final 13e execution below.

**Historical 13d status: STOP / PLAN-GAP; PR #12 stayed draft.** The privileged-tool path fix
and private release/signature/two-file image comparison passed. The latest native
suites passed all 223 tests.
The 13c probe failed at live KDE German-layout selection; no installation or
qualification was performed then. Brief 13d now moves that live-desktop step to
the laptop gate and authorizes one fresh probe, then installed-system qualification.
13d’s fresh probe passed, but qualification stopped before the repair write at
the one-stock-deployment identity guard. The installed stock has two BLS entries.
No second qualification or further dispatch followed. See the final 13d section.
Physical installation remains **NOT RELEASED**. Earlier sections are dated
history, including the original source-verification stop and the 13b wrapper stop.

## Original brief 13 — historical zero-cost stop

**Historical STOP / PLAN-GAP. No implementation or VM qualification was claimed.** The
argument-emitting code is identified, but the required explanation of the **US
value** is not established by the retained evidence and pinned source. The brief
requires this verification before any dispatch. No dispatch was made to guess at
the missing state. Physical installation remains **NOT RELEASED**.

## Done

Fetched first; verified a clean `pkg/13-keyboard-layout` at `3459111`. Read
AGENTS, README, brief 13, the 11n report and second review, INSTALL's keyboard,
switch and release-gate steps, EMERGENCY, the session/labwc files and relevant
installer, deployment, identity, budget and credential code. Worked only in the
new worktree. The retired package-11 worktree was never accessed.

Retained [source files, source URLs, versions and input hashes](../../os/manifest/ci/13/zero-cost/verification.json)
and an [offline evidence replay](verify-zero-cost.py). Product code, image payload,
owner blocks, workflows, audits, pins and existing tests remain unchanged.

## Verified

Downloaded the **complete pinned ISO locally**, using the repository inspector's
HTTP User-Agent, and hashed all **9,068,650,496 bytes**. Result:
`776b76f3417723440ee1823d79ec02a2c22860df196d219024edb062ad00d8e6`.
The fresh official checksum matched. An initial request using Python's default
User-Agent returned HTTP403; the existing inspector's request format succeeded.
No substitute ISO, system-software installation, elevation, mount or boot was used.
Existing WSL `unsquashfs` read the ordinary ISO file at offset314167296. The large
ISO and extracted RPM database stay in ignored worktree scratch, outside Git.

Read the ISO's RPM database as data, without installing packages:

| Component | Pinned installed version / source |
|---|---|
| Anaconda | **44.30-2.fc44**, including its generated `version.py`; [44.30 payload source](https://github.com/rhinstaller/anaconda/blob/anaconda-44.30/pyanaconda/modules/payloads/payload/rpm_ostree/installation.py) |
| systemd | **259.9-1.fc44**; [v259.9 console setup](https://github.com/systemd/systemd/blob/v259.9/src/vconsole/vconsole-setup.c) |
| OSTree | **2026.4-1.fc44**; [v2026.4 deployment code](https://github.com/ostreedev/ostree/blob/v2026.4/src/libostree/ostree-sysroot-deploy.c) |
| bootc | **1.16.13-1.fc44**; [v1.16.13 argument inheritance](https://github.com/bootc-dev/bootc/blob/v1.16.13/crates/lib/src/bootc_kargs.rs) |
| rpm-ostree | **2026.3-2.fc44**; [v2026.3](https://github.com/coreos/rpm-ostree/tree/v2026.3) |
| libxkbcommon | **1.13.1-2.fc44**, both architectures in the ISO; [1.13.1 defaults](https://github.com/xkbcommon/libxkbcommon/blob/xkbcommon-1.13.1/src/context-priv.c) |
| labwc | **0.9.6-1.fc44**, from the retained image package inventory and package lock; [0.9.6 keyboard code](https://github.com/labwc/labwc/blob/0.9.6/src/input/keyboard.c) |

Extracted the actual ISO's payload, boss, localization and runtime Python source.
Payload SHA256 is `614ac3f3061d959144e0a2e80919012c7254d44b1fab04daea35b2bef52f3f86`;
boss SHA256 is `e13a19312256866c54455620f894e99d6e92104b856939632c7f1cbc46fb5721`.
Both match the44.30 tag. The localization installation/localed/utils files also
match the originals retained in11n byte for byte. Public Fedora source RPMs for
these components were inspected as archives; their URLs/hashes and build specs
are retained, without committing RPM binaries or installing them.

The established source facts:

1. **The live boot arguments contain no keymap override.** Both the retained ISO
   GRUB configuration and actual live `/proc/cmdline` capture lack it. The retained
   bootloader preserved-arguments configuration does not name `vconsole.keymap`.
2. **Anaconda has an explicit emitter.** `ConfigureBootloader._set_kargs()` adds
   `vconsole.keymap=` from the localization module's `VirtualConsoleKeymap`, using
   `ostree admin instutil set-kargs --merge`. This identifies a writer, not the
   observed module value when that writer executed.
3. **The prerequisite state transition is missing.** The pinned boss queues
   `PopulateMissingKeyboardConfigurationWithTask` before payload/bootloader work.
   Its success callback stores the resolver's result in the module. The installed
   keyboard task separately captures settings and resolves missing values before
   writing `vconsole.conf`. See the retained [boss](../../os/manifest/ci/13/zero-cost/anaconda-modules_boss_installation.py),
   [localization module](../../os/manifest/ci/13/zero-cost/anaconda-modules_localization_localization.py)
   and [file-writing task](../../os/manifest/ci/13/zero-cost/anaconda-modules_localization_installation.py).
4. **The conflict is real; the loaded11n map is unknown.** The11n pre-install
   module has XLayouts`['de']`, empty console keymap, live localed console`us`,
   and live X11`de`. The installed files say`de`; both later BLS entries contain
   exactly one keymap argument, `us`. The missing value is the module/bootconfig
   state at the argument-writing boundary. The retained success artifacts do not
   contain the original installation program/module trace that would establish it.
5. **Do not invent a counterexample from11k.** Its real German-position tty3
   login/sudo and loaded German map passed, but its actual AresOS kernel command
   line says **`vconsole.keymap=de`**. It cannot prove how11n's US-argument boot typed.
   An initial comparison wrongly described11k as using US; the replay caught this
   before commit/dispatch, and the conclusion was corrected.
6. **Existing typing is partly sensitive already.** The German typer swaps y/z
   and maps hyphen/slash positions. `ares-recovery` contains both `y` and `-`;
   the typed sudo path contains `/`. Those login/command checks can distinguish
   layouts. The generated `token_hex(24)` password itself cannot. No current
   evidence substitutes for the requested new symbol-bearing password and foot test.

Systemd259.9 explicitly reads the configuration file before the higher-priority
kernel arguments. No contradiction of that precedence was found. The problem is
an **unresolved causal prerequisite**, not evidence that the goal is wrong or that
US can safely be left in place. In particular, I have not asserted that the GUI
always generates US, that conversion raced, or that an image default caused it.

Deployment/session facts checked for the eventual fix:

- Pinning changes pin state, without correcting arguments. Bootc starts new
  arguments from the merge deployment and applies the image `kargs.d` difference;
  rollback reorders the existing deployments. Neither operation repairs a retained
  stock entry automatically. [Pin source](https://github.com/ostreedev/ostree/blob/v2026.4/src/ostree/ot-admin-builtin-pin.c),
  [rollback source](https://github.com/bootc-dev/bootc/blob/v1.16.13/crates/lib/src/deploy.rs).
- The verified OSTree installer utility uses `deployment_set_kargs`, which clones
  the deployment object into a replacement list rather than appending another
  deployment. This is a candidate way to avoid duplicate checksum matches, requiring
  real qualification before use. No identity check was changed.
- Labwc passes empty rule names to libxkbcommon and reads session environment
  files. Libxkbcommon uses `XKB_DEFAULT_*` or compiled defaults; its default layout
  is US. Fedora's inspected source specs do not override that layout or add labwc
  patches. The current session/profile/labwc configuration supplies no system-layout
  reader. The compositor source supports the brief's concern; actual foot typing
  remains unverified. [Session environment source](https://github.com/labwc/labwc/blob/0.9.6/src/config/session.c),
  [compiled defaults](https://github.com/xkbcommon/libxkbcommon/blob/xkbcommon-1.13.1/meson_options.txt).
- The frozen-release verifier rejects changes to `os/config`. A future solution
  must explicitly reconcile its session change or owner provisioning with that
  unchanged signed-image check; it must not silently test a replacement runtime
  as the frozen image.

Ran `python reviews/13-keyboard-layout/verify-zero-cost.py` successfully:

```text
ZERO_COST_EVIDENCE_REPLAY_PASSED: 26 source files, 16 retained inputs; runtime/audits/pins unchanged
STOP-PLAN-GAP: the historical console value at the argument-writing boundary is not retained; no dispatch authorized
```

This replays source/input hashes, the actual differing11k/11n arguments, retained
German keycodes and tty3 success, source ordering and unchanged runtime/audits/pins.
It does **not** claim to replay the absent historical localization state.

Python compilation passed. The authored-file staged whitespace check passed;
the full check reports one original blank line at EOF in the byte-preserved
Fedora `libxkbcommon.spec`. That source evidence was not rewritten to hide it.
No functional or privacy check was excluded or changed.

## Budget and dispatch gate

The package ledger starts at the **first dispatch**, which has not occurred.
Before push, the branch's Actions history returned `total_count:0`, `runs:[]`.
The old11c ledger and guard are untouched; no guard for package13 is claimed built.

| Package13 allowance | Used | Cap |
|---|---:|---:|
| Ledger start | Not started | First `workflow_dispatch` |
| Rounded ledger minutes | **0** | **250** |
| Probe dispatches | **0** | **1** |
| Qualification dispatches | **0** | **2** |

Local downloads/source inspection consume no Actions minutes. Automatic push/PR
privacy checks occur before any package dispatch; their actual outcomes/cost are
recorded on the PR after push. No checks-only/native, probe, qualification, Part B,
image build, publish, owner-token read or visibility change was dispatched.

## Not verified / remaining work

The zero-cost origin/value explanation is incomplete, so no fix was selected.
The normal-setting/session fix, owner-block equality and later-layout command,
regressions/whole-suite native gate, per-package guard refactor, fresh probe,
protected-second qualification, physical-key tty3/sudo/foot results, layout change
and rollback proof, INSTALL/EMERGENCY updates and release-gate update remain undone.
No complete unit suite, Gradle or Minecraft run was made in this stopped package.
No Gradle daemon was started. All physical gates stay open.

## JUDGMENT-CALL

Stopped at the explicit pre-dispatch verification prerequisite rather than label
an inferred sequence as a proved cause. No product behavior or owner-system setting
was changed. This is a draft evidence/report PR, not an acceptance pass.

## PLAN-GAP

The required **zero-cost explanation of the US value** cannot presently be
established from the retained boundary state. Static source identifies the writer
and independent configuration paths, but does not prove which value it read or
why the two outputs diverged in11n. The earlier successful typing run uses a
different argument and does not fill that gap. Continuing would turn an unproved
causal assumption into dispatch authorization.

## Open questions

What revised verification plan may observe the localization/module and bootconfig
values at the real argument-writing boundary in a disposable VM, with credential-safe
logging and all existing disk/NVRAM/BootNext audits? That observation would need a
revised prerequisite; no exception or extra dispatch is assumed here. The simpler
identity-preserving argument update and a frozen-image-compatible session provision
can then be evaluated against the observed cause. Never merge this incomplete PR.


## 13b — system setting, private org release and qualification (2026-10-25)

**Status: STOP — image tooling integration failure; no new image built or published.** This
section supersedes the cause gate in the original 13 report. The historical
zero-cost receipts above are unchanged. Owner brief 13b explicitly makes the
localization value diagnostic, approves one new private org release, and raises
the package ledger to 380 minutes. PR #12 stays draft until all acceptance passes.

### Done and source decisions

- `system-keyboard.sh` removes all console keymap/toggle overrides, of any value,
  before pause/pin. INSTALL contains its exact bytes. It restricts the operation
  to the pinned base, one booted unmodified deployment, no active/staged/queued
  transaction, and rechecks checksum/serial/count/pin identity and unrelated args.
  It uses `ostree admin instutil set-kargs`, then `rpm-ostree reload`.
- Verified pinned [OSTree v2026.4 CLI](https://github.com/ostreedev/ostree/blob/v2026.4/src/ostree/ot-admin-instutil-builtin-set-kargs.c)
  and [deployment implementation](https://github.com/ostreedev/ostree/blob/v2026.4/src/libostree/ostree-sysroot-deploy.c):
  `deployment_set_kargs` clones/replaces the deployment in the list; it does not
  add a second checksum/serial. Bootlink regeneration is allowed; all other
  unrelated arguments and identity fields must remain equal. The existing
  checksum uniqueness checks in pin/rollback/GRUB remain unchanged.
- `aresos-keyboard` reads one localed GetAll snapshot and passes the system X11
  layout/model/variant/options to labwc, clearing inherited XKB defaults. No
  chosen layout is in the release. German and US are test/guide choices only.
  JSON shapes checked against pinned systemd v259.9 `bus-dump-json.c`.
- `keyboard_vm.py` reuses package 11's Guest/Audit/BootNext/protected-disk code.
  The password includes `yz-/!` plus random hex. Public physical input `yz-/!`
  distinguishes US/German at all four sensitive positions. Serial observes
  results; QMP USB key positions supply login, sudo and foot text. No password
  screenshot or raw interactive transcript is exported.
- Read-only D-Bus monitoring is restricted to Anaconda Localization. Only
  allowlisted property Get/reply pairs are retained, not account/user data.
  The installer source and choices remain unmodified. The console model is
  untrusted regardless of `de`, `us`, another value or none.
- The ISO RPMDB identifies plasma-desktop/workspace 6.7.5. Its normal KCM uses
  Enable/Configure Layouts and Add layout rather than the guide's old tab label;
  guide updated from [pinned KDE UI source](https://github.com/KDE/plasma-desktop/blob/v6.7.5/kcms/keyboard/ui/main.qml).
  Probe will exercise accessible controls in the actual KCM and German physical
  typing into KWrite before the unmodified installer UI. This is not yet VM evidence.

**JUDGMENT-CALL — image construction:** derive the release from the exact frozen
private qualified image, instead of repeating DNF against mutable repositories.
The complete merged files, ownership/modes/xattrs, actual RPM NEVRAs, package
lock, systemd units, OCI runtime configuration and base layer ancestry are
compared. Only `usr/bin/aresos-session` and `usr/libexec/aresos-keyboard` may
differ. Explained OCI label changes: org source URL, source revision and the
actual builder version, if changed. OCI creation/history/layer IDs describe this
build; mtimes/inodes are storage metadata excluded from semantic file equality.
An unexplained difference stops before publish. This retains precisely the same
pinned base and packages; changing the recipe later needs another qualification.

**Token boundary:** old classic read-only secret is used only to pull/verify the
historical private input for the approved comparison. It is not used for API
requests or publishing. The org job token publishes/signs and must prove private
manifest reads. New-release rehearsals use only the job token, with no fallback.
Both credential files are root-owned 0600 under RUNNER_TEMP outside checkout,
always removed before upload. Secret retained for the owner to remove later.
[GitHub registry documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
supports initial private visibility and linked-repo job-token access. Laptop
instructions continue to require the owner's own read token. No visibility change.

### Zero-cost stage walk-through before any dispatch

1. Run complete local suite and syntax checks; list host limits. Commit/push FF,
   require all three privacy checks including executed personal-term scan.
   Fresh complete-history guard reserves 90 image minutes (all dispatches and
   later privacy jobs count from first dispatch). One image dispatch only.
2. Image job runs every regression natively before building. Verify old signature,
   pinned upstream signature, exact base ancestry, locked/actual packages, full
   files/units/config diff. Any unexplained difference stops. Run existing image
   policy/session/Homebrew/power/recovery checks twice on disposable overlay,
   whose ordinary system X11/console settings explicitly choose US. Exclude all
   CI configuration/credentials from release. Publish PRIVATE org digest, sign
   with org workflow identity, verify signature/private metadata/job-token read.
3. Retain old release manifest as `releases/06.json`; record new exact digest,
   signature, run/source, diff and job-token proof. Update frozen verifier and
   owner references/equality checks. Commit/push; require privacy again. No
   runtime payload change after image source.
4. Fresh guard, one native checks-only run on final head (15-minute reservation),
   then one fresh probe (42). Same head for probe and qualification. Probe retains
   every inherited predicate: both disk mappings, real installer through review,
   cached exact stock CLI help, update pause idempotence, failure counters, OCR,
   installed-file reader, private layer pull, Windows detached marker, target
   reset, complete protected/NVRAM/BootNext checks. Also qualify normal KDE
   physical editor input, set-kargs/reload help and live localed reader shape.
5. Only passing probe/native/privacy authorize qualification (130 reserved),
   protected disk second. Baseline marker → exact §4 live normal settings/editor
   and unmodified installer pages → first stock firmware-default boot (normal
   hardware initialization reset only, if source-verified) → installed keyboard
   files and initial cmdline/loaded-map diagnostic → repair actual value → inject
   `de`, repair → inject `us`, repair → pause/pin exact stock → power off/audit.
   Require one stock checksum/serial throughout, no extra deployment.
6. Restore Windows-first exactly; unattended attached/detached Windows markers.
   Corrected stock boot: every BLS/cmdline clean, loaded German map, tty3 real
   login/password sudo and physical text; inherited Homebrew. Signed switch to
   new exact release, inspect staged identity. Offline audit at shutdown.
7. AresOS German boot: all args/maps, tty3/sudo/text, actual labwc environment,
   foot physical text, policy and inherited Homebrew. Use normal localectl
   console+X11 US setting; reboot/audit. US boot repeats both physical screens;
   change normally back to German; reboot/audit. German boot repeats, then exact
   rollback and queued identity check.
8. Backup boot: exact stock checksum/digest, every entry free of overrides,
   loaded German map and tty3/password sudo/text, Homebrew and rendered Plasma
   greeter. Final attached/detached Windows markers and all offline audits.
   No Part B/menu rerun. Stop on any product/protected-disk/firmware gap.
9. Retain credential-safe bounded evidence and budget, require final privacy.
   Mark PR #12 ready only if all acceptance is met. Physical laptop stays
   NOT RELEASED; never merge, force-push, delete old packages or make public.

### Budget plan (package 13, 380-minute cap)

| Item | Allowed | Reservation |
| --- | ---: | ---: |
| Image build/publish including two image VM passes | 1 | 90 |
| Checks-only native suite on qualification head | 1 | 15 |
| Fresh probe | 1 | 42 |
| Qualification | up to 2, subject to remaining budget/stop rules | 130 for first |
| Closing/privacy allowance | counted by actual job rounding | 16 |
| Planned total | | **293** |

Pre-dispatch plan (historical): no dispatch had started when this walk-through was committed. A second qualification is not preauthorized to evade a stop;
it must independently fit the remaining ledger. Historical pre-dispatch push/PR
privacy jobs are outside the first-dispatch interval, retained above.

### Verification in progress / not verified

Targeted Windows keyboard/session/release tests: 15 passed. First whole Windows
run: 190 tests, 8 failures/10 errors (Linux-only imports/privileges/sockets plus
workflow expectations subsequently updated). Whole WSL run: 209 tests,
2 failures/9 errors, representing eight unique environment-limited cases:
three Pillow framebuffer tests (Pillow absent in WSL; Windows equivalents pass),
three privileged inherited-Homebrew tests (sudo deliberately rejected locally),
one privileged sysusers test, one 0600 auth-permission test on DrvFS (reports0777).
The WSL suite has no other failures. Full rerun after final edits still required.
All remain mandatory in native CI; no skip/assertion weakening. Initial Windows
run used default temporary-file placement; subsequent runs explicitly confine
temporary fixtures to this worktree. No local privileged operation permitted.

New image, diagnostic, real de/us starting-state repair, typing, layout change,
rollback and budget remain **NOT VERIFIED** until the actual runs below.
No mod/Gradle/Minecraft work, no daemon started, no retired-worktree access.

**PLAN-GAP:** no additional product gap established yet; old cause gap was
explicitly superseded by 13b. **Open questions:** actual VM/registry results and
all unchanged physical laptop/media/firmware/followability gates.

Final pre-dispatch local run: python3 -m unittest discover -s os/tests -v in WSL: **211 tests / 144.806s; 2 failures, 9 errors, exactly the same eight environment-limited cases listed above; all other cases passed**. Windows 	est_greeter.py: all 3 passed. Full Bash/Python syntax and git diff --check: passed. Fresh complete-history guard: four unique runs / total_count four, zero dispatches, ledger start null, 0 + 293 reserved ≤ 380. Repo visibility independently queried: PRIVATE.


### 13b actual execution and required stop

[Image attempt 40152936417](https://github.com/Ares-Empire/AresOS/actions/runs/40152936417)
ran once at source `b140fafc106826db904d9100b046a1304e21a828`. Its own guard
proved complete history: nine unique IDs against total_count nine, one page,
current release dispatch counted once; 90 minutes reserved within 380.

**Verified natively:** `python3 -m unittest discover -s os/tests -v` printed
`Ran 211 tests in 4.385s` then `OK`. All local environment-limited cases passed;
no tests were skipped. Python/Bash syntax passed. The pinned toolchain/EDK2
contract and upstream Bazzite signature/digest verification passed. Both source
privacy runs passed all three rules with the personal-term scan not skipped:
push [40152704371](https://github.com/Ares-Empire/AresOS/actions/runs/40152704371)
and PR [40152707578](https://github.com/Ares-Empire/AresOS/actions/runs/40152707578).
The final whole WSL rerun before dispatch again ran 211 tests in 152.199s and
had only the same eight environment-limited cases. Four Windows greeter tests
passed (the earlier prose saying three referred to the three Pillow-dependent
cases, not the total module count).

**Failure, not acceptance:** the next wrapper ran as
`sudo -E bash os/ci/build-keyboard-release.sh`. At line 12 it printed
`cosign: command not found`, exit 127. The action-installed cosign had already
worked in the unprivileged upstream verification step. The privileged wrapper
did not inherit a usable cosign executable search path. This is an implementation
integration error, not evidence of a changed image or a contradiction in the brief.
The source fix must resolve and explicitly pass the verified executable path
across the privilege boundary; do not broaden credential visibility or bypass
old-image signature verification. No source workaround or second run was attempted
after the stop. A follow-up must explicitly authorize another image attempt.

**What did not run:** old-image signature verification/pull, image build, complete
image diff, isolated overlay/VM image passes, publish/sign, org job-token read,
checks-only final-head dispatch, probe, installation/diagnostic, real de/us
starting-state repair, tty3/foot typing, layout change/back and rollback. The
one image dispatch allowance is consumed even though it stopped before building.
Zero probes and zero qualifications were dispatched. The old release manifest,
owner reference and signature identity remain current; assigning a new digest
without a successful publish would be false. PR #12 remains draft; all acceptance
and physical laptop gates remain open. Nothing was made public or merged.

**Credentials/privacy:** the owner read-only token was scoped only to the
runner-temporary old-package auth file; its creation step passed. Cosign failed
before a registry read; no owner-token API request/publish occurred. The always
cleanup passed and retained `removed:true`, `outside_workspace:true`. The temporary
cosign config symlink was removed by the wrapper trap. Auth/password/config
files are absent from the artifact member list. Raw credential files and VM
disks were never uploaded or copied into this repo. A laptop-session Packages API
query returned 404; it is not used as proof of package absence or job-token access.
Job-token access to the new org package is explicitly **NOT VERIFIED**.

### Actual package ledger and retained evidence

Ledger begins at first dispatch, `2026-10-25T02:02:34Z`; the guard receipt is the
authority for its exact API timestamp. All earlier push/PR privacy runs are
outside that interval. Current image job ran 02:02:37–02:06:24 UTC: ceil(227/60)
= **4 minutes**. Three skipped jobs cost zero.

| Item | Dispatches used / allowed | Minutes |
| --- | ---: | ---: |
| Image attempt 40152936417 | 1 / 1 | 4 actual |
| Checks-only native dispatch | 0 / 1 | 0 |
| Probe | 0 / 1 | 0 |
| Qualification | 0 / 2 | 0 |
| Closing push/PR privacy | automatic; verified after this report push | 4 reserved |
| Before closing / including reservation | | **4 / 8 of 380** |

The remaining minutes do not authorize another image attempt. Closing checks
and the exact final ledger are also recorded in PR #12 after this commit, avoiding
an endless sequence of report-only pushes. No rerun, force-push or merge.

- [Run/jobs/budget/privacy receipts](../../os/manifest/ci/13/release-1/)
- [Complete retained log](logs/release-1.txt)
- [Unmodified evidence ZIP](artifacts/13b-release-1-os-image-evidence.zip),
  121,791 bytes, SHA-256
  `16b3ca6930074081f2a26a6f5b6ad6e657a4e2e930e2e4a5673b2dffb3605758`;
  verified against GitHub artifact digest (ID 12582769224).
- Downloaded raw log ZIP SHA-256
  `68ac18ef829ddb6ca6e2c6c79317ad87fc5a64f4151f621e010d631de4549415`.

**PLAN-GAP:** none newly established in product/source verification; the blocking
item is the build-wrapper PATH error above. **Not verified/open:** every new-image
and VM acceptance item listed above, and the unchanged physical install gates.
No Gradle daemon was started. Work stayed in package 13; no retired worktree access.


## 13c — absolute privileged tool paths and continued qualification (2026-10-25)

**Status at pre-dispatch planning: implementation/local verification. Final status: STOP after probe 40159515328 failed; see the execution record below.** The earlier
13b stop and its four-minute failed image attempt remain historical. Brief 13c
authorizes at most two additional image dispatches on the same ledger, publishing
at most once. The ledger start remains 2026-10-25T02:02:34Z, cap 380 minutes.

**Done:** `build_tools.py` resolves every directly invoked host executable before
the credential-creation step: Bash, Python, sudo, cosign, podman and skopeo. The
privileged shell receives the absolute Python/manifest paths through an argv
list; Python validates the exact tool set and absolute/existing/executable paths
again before importing/calling credential access. The build and full image diff,
including cleanup, call only the validated absolute paths. JSON/files/directories,
symlinks, hashes and manifest copying use Python standard-library operations;
the wrapper no longer invokes jq, mkdir, ln, rm, rmdir or sha256sum. No buildah or
oras process is invoked. Container commands use `/usr/bin/python3`/`rpm` from
the exact pinned image, a separate namespace from the host sudo boundary.
The old-image signature check and root-only temporary credential share remain
mandatory; owner-token scope/visibility is unchanged.

**Guard:** settings permit three total image dispatches (old 13b + two 13c),
with the same first-dispatch start, privacy accounting, pagination and bounded
read retries. Every completed image job must expose exactly one publish step.
Entering that step, even if failed/cancelled, conservatively consumes the single
publish allowance because a registry write may have happened. A fresh guard
immediately before publish refuses a prior publish boundary; no subsequent image
dispatch is allowed either. Immutable tag/private visibility checks remain.

**Verified so far:** stripped-PATH wrapper/diff tests passed (3 / 1.208s), including
missing/relative/non-executable paths rejected before auth, the unprivileged
resolution-before-secret ordering and explicit sudo argv. Five release/guard
tests passed, including second/third image allowance, fourth refusal, publish
success/failure/cancellation accounting and prior-publish refusal. Full Bash/Python
syntax and `git diff --check` passed. Whole suite is running; its exact result
must be recorded before dispatch. All native tests remain mandatory in image CI.

**JUDGMENT-CALL:** deriving from the exact frozen qualified image is now accepted
by the integrator in 13c; it still requires owner review before merge. The strict
two-file diff, exact packages/units/config/base ancestry checks are unchanged.
No unexplained difference is authorized by the added attempt allowance.

### Updated zero-cost walk-through before dispatch

1. Finish the complete local suite, keeping the same eight documented local host
   limitations; run those and all new tests natively before image work. Push FF,
   require all three source privacy checks with personal terms not skipped, then
   a fresh complete-history guard. Current observed ledger is 12 minutes,
   including the owner's 13c brief push/PR checks; 12 + 293 planned = 305 ≤ 380.
2. Image attempt 2 overall: own guard → pinned tools + all native regressions →
   cosign install/upstream verification → resolve all host tools unprivileged →
   only then create root-only old-image auth → absolute-path wrapper validates
   every executable before auth access → old signature/pull → exact frozen-image
   derivation → unchanged full semantic image diff. No unexplained difference
   may proceed to publish or be excused by another attempt.
3. Existing isolated overlay/release separation and both image VM passes remain
   required. Only their success permits a fresh single-publish guard, private
   immutable org push, keyless signing/verification and job-token read proof.
   Credential cleanup and evidence bounds apply on every path.
4. If this attempt stops before publishing for a covered tooling/infrastructure
   issue, inspect/record/fix it without weakening a check; at most one final image
   attempt remains and must fit a fresh guard plus the remaining plan. If both
   stop, or any unexplained diff/product/protected-disk/firmware stop occurs,
   stop and report. Any attempt reaching publish prevents another publication.
5. After a successful private release, continue 13b stages 3–9 unchanged: new
   exact digest/identity/frozen verifier/owner references; source privacy; final
   head checks-only native (15), one fresh probe (42), then protected-second
   qualification (130) on the exact same head. All de/us repairs, live editor,
   tty3 login/password sudo, foot physical keys, layout change/back, cmdline/maps,
   rollback and Windows/disk/NVRAM/BootNext audits remain mandatory. No Part B.
6. Budget plan for the next attempt is 90 + 15 + 42 + 130 + 16 closing/privacy =
   293 reserved, plus actual consumed minutes. A final additional image attempt
   is conditional on remaining rounded minutes; the extra attempt allowance
   does not enlarge the 380-minute cap. Report every attempt. PR #12 stays draft
   until all acceptance is met; never merge, force-push, delete old releases or
   make anything public. Physical installation remains NOT RELEASED.

**Not verified/open:** all new image/VM acceptance remains pending. No new
PLAN-GAP established. No mod/Gradle/Minecraft or local privileged operations.

13c complete local suite before source push: **216 tests in 143.422s; 2 failures/9 errors, exactly the same eight host-limited cases recorded in 13b; all other cases passed**. Native CI must pass all 216, including the new stripped-PATH and publish-boundary tests. After adding the explicit skipped-image-job case to that boundary test, its five-test module passed again; the complete final rerun is running before dispatch.


### 13c image attempt 2 — passed, private publication used once

[Run 40154642447](https://github.com/Ares-Empire/AresOS/actions/runs/40154642447)
at `2abc12e8aa6089f7576143d1fbccb6648a3291bd` passed. The image job ran
02:29:39–03:34:20 UTC: **64m41s, rounded to 65 minutes**. This is the first
successful publication, second image dispatch overall. The final unused image
attempt may not publish again; the guard now rejects any new image dispatch.

Native suite: **216 tests in 5.183s, OK**, including stripped-PATH regressions;
no skips. Final local pre-dispatch rerun: **216 tests / 127.642s**, only the same
eight host limitations. Source push/PR privacy checks 40154503307/40154507842
passed all three rules; personal terms were not skipped. Their rounded cost was
2 + 1 minutes, already in the 15-minute ledger before this run.

Resolved host tools: `/usr/bin/bash`, `/usr/bin/python3.12`, `/usr/bin/sudo`,
`/home/runner/.cosign/cosign`, `/usr/bin/podman`, `/usr/bin/skopeo`. Old private
signature verification, exact pull and strict diff all passed. Root-only old
credentials were always removed before upload; the cosign symlink was removed.
No credential scope/permissions were widened.

**Image diff:** 2,801 actual package entries equal, lock equal; 690,388 old paths
and 690,389 new paths compared, including modes, UID/GID, types and xattrs.
Only `usr/bin/aresos-session` (229→258 bytes) and the added
`usr/libexec/aresos-keyboard` (1,618 bytes) differ. Both are root:root 0755.
All systemd units and OCI runtime configuration are equal; exact pinned base
ancestry and the old layer prefix are preserved. The only changed labels are
source URL (personal repo→org) and source revision (original 5578ab2→2abc12e).
Buildah version did not change. Creation/history/layer identities describe the
new build, as declared in the accepted construction plan. No unexplained
semantic difference was found. Full compressed path inventories are in the ZIP.

**New release:**
`ghcr.io/ares-empire/aresos@sha256:9b19b7942bc131934eac3733a7f8a1c1de488659075897f60c006bc88c77f3eb`,
immutable tag `13-2abc12e8aa6089f7576143d1fbccb6648a3291bd`, **PRIVATE**.
Keyless signature subject:
`https://github.com/Ares-Empire/AresOS/.github/workflows/os-image.yml@refs/heads/pkg/13-keyboard-layout`;
issuer `https://token.actions.githubusercontent.com`. Retained cosign payload
matches that exact digest, subject and issuer. Job-token authenticated manifest
read and private metadata checks passed; owner token was not used to publish or
read the new manifest. The old release is preserved in `releases/06.json`; the
new current manifest and owner guide reference this digest. Secret removal is
left to the owner. Rehearsal job-token layer reads remain to be proved.

**Both image VM passes passed:** locked daily account/session, 1,084-unit updater
audit, recovery getty/PAM correct and wrong password cases, terminal shortcut,
lid/sleep policy and offline poweroff journal ordering. Both offline checks say
`status:passed`; no hardware-only exception was needed. The CI-only overlay
sets ordinary US console/X11 settings; release isolation passed. The second
labwc screenshot was visually inspected: rendered AresOS foot terminal/prompt.
These do not substitute for the upcoming installed sensitive-password typing
and inherited-Homebrew/rollback qualification.

**Evidence:** [receipts](../../os/manifest/ci/13/release-2/),
[complete log](logs/release-2.txt),
[original ZIP](artifacts/13c-release-2-os-image-evidence.zip), 60,406,461 bytes,
SHA-256 `c2b95dea3db16c092e45fbb765b5ae28d7c13ae26b96994b63d2d7027aa87d0b`
(GitHub artifact 12585308939). Raw log ZIP SHA-256
`c28f0b71b7e0c44bfb55958b69646d065939d9453302bad36bcd4373d3760ee6`.
Peak runner usage 72,349,507,584 bytes; minimum free 4,520,869,888; release
uncompressed size 13,428,543,841 bytes. All evidence bounds passed.

### Final-head preparation before native/probe dispatch

The rehearsal checkout now fetches complete history so the frozen-release
verifier can prove source ancestry; a depth-one HEAD is an explicit ancestry
boundary even when a separately fetched source object exists. The image payload
remains frozen at 2abc12e. The accessibility selector now ignores same-named
static text when choosing actionable KDE controls; the editor fixture creates
an empty destination file and waits boundedly for Ctrl-S to finish. Expected
physical text is unchanged and still supplied only through QMP. No installer
source or choice is changed. Whole local suite must pass except the documented
host limits before dispatch; all tests are mandatory in native CI.

Budget after publication: **80 / 380 minutes**, 2/3 image dispatches, 1/1 publish,
0/1 checks-only native, 0/1 probe, 0/2 qualifications. Fresh guard reserves the
remaining 15 + 42 + 130 + 16 = **203**, total **283 ≤ 380**, before final source
privacy. The next source push adds its actual privacy job rounding. Continue
the previously committed walk-through unchanged: native on final head → fresh
probe → protected-second qualification on the exact same head. No image rebuild
or publication. All diagnostic/typing/layout-change/rollback acceptance is still
pending, and PR #12 stays draft. Construction still needs owner review before
merge. No new PLAN-GAP; physical installation stays NOT RELEASED.

Final-head local suite: **217 tests / 148.291s**, exactly the same eight documented host-limited cases (2 failures / 9 errors); all others passed. Complete Bash/Python syntax and diff checks passed. The new frozen org-release verifier ran locally against run 40154642447 and passed source/run/signature metadata plus unchanged-runtime checks; git diff of every frozen runtime path against 2abc12e was empty. Image pass 1 tty3 screenshot was also visually checked: rendered getty prompt on tty3. Artifact text was checked for unmasked GitHub token forms, SHA-512 password hashes and private-key headers; none found.


### 13c final-head native checks and fresh probe — required stop

**STOP. Acceptance is not met; PR #12 stays draft.** On the unchanged head
`777b78202580e19ed1ec0b5fc838931e2609f77e`, the checks-only native run passed,
then the single fresh probe failed. No qualification, additional probe, image
attempt, publication or source workaround followed that failure. Remaining
minutes and the two unused qualification slots do not authorize bypassing the
passing-probe gate. Nothing was merged, force-pushed or made public.

**Verified:** [native 40159399419](https://github.com/Ares-Empire/AresOS/actions/runs/40159399419)
ran `python3 -m unittest discover -s os/tests -v`: **217 tests in 5.078s, OK**,
with no skips, including every case that cannot run on the local host. Bash and
Python syntax passed. The read-only job token checked that the new org package
is private. No VM or image build ran in this checks-only job. Its running job
was 03:45:45–03:46:34 UTC, **1 rounded minute**.

[Probe 40159515328](https://github.com/Ares-Empire/AresOS/actions/runs/40159515328)
ran once on exactly the same head. Its fresh complete-history guard, source
ancestry/frozen-release verifier, toolchain/OVMF contract, upstream signature,
full pinned ISO hash and native suite (**217 / 5.127s, OK**, no skips) passed.
The read-only job token verified private visibility and pulled the exact new
release layers with its digest preserved. `owner_token_used:false`,
`owner_token_api_calls:0`, `credential_file_copied:false`; always cleanup passed
with `removed:true`, `outside_workspace:true`. CI therefore needs no owner
read-token fallback for this org release. The existing secret stays until the
owner removes it; laptop installation still uses the owner's own token.

**Failure:** in the first, protected-first live-desktop probe,
`live-kde-enable` and `live-kde-search` completed. The next guest command failed:
`Guest command failed: live-kde-select, exit 1`. The retained guest traceback is
`AssertionError: KDE normal settings control unavailable: German`, from
`action('German')` after its bounded 40-second wait. The accessibility tree
contains German **list items** and multiple Add Layout dialog subtrees, but the
fixture could not invoke an accepted action on one. The dump does not include
state/action/selection-interface details, so it does not prove which interface
or dialog caused the failure. This is an uncovered UI-fixture integration
failure, not evidence that the new image types correctly or incorrectly.

The [search-phase screenshot](screenshots/probe-1-live-kde-search.png) was
visually inspected: the Bazzite Portal is in front, with no visible German
selection confirmation. It supplies no passing keyboard evidence. The full
[guest selector trace](../../os/manifest/ci/13/probe-1/evidence/two-disk/live-kde-select.txt)
and source script are retained. A future authorized repair should inspect the
active dialog and its state/action/selection interfaces, preserve the guide's
normal-settings interaction, and retain the expected physical text unchanged.
No such repair or rerun is claimed in this stop.

The harness did not reach the live editor's physical-key test or its installer
UI preview. Failure diagnostics show that the ISO had started Anaconda/browser
processes; this is not a claim that no installer process existed. No install
was performed, no localization argument-writing boundary was reached, and no
diagnostic values from that boundary exist. The reverse-order probe was not
reached. No successful `probe-result.json` exists or may authorize a full run.

**Failure-path safety:** both reached offline protected captures match the
baseline exactly, including the entire 50-GiB image hash
`db11ae0b975673c820f57cf12c8ea239215184b671b25a2785f9aa54e99a8a00`,
GPT/partition metadata and EFI-file evidence. The retained final paused-VM
failure counter reports zero protected write bytes/operations and zero unmap
bytes/operations; target counters are also zero. BootNext audit passed (absent,
not consumed), BootOrder is identical, and the audited boot-entry/firmware
changes are empty. The full-variable diff records only `MTC` under
`eb704011-1402-11d3-8e77-00a0c969723b`; it is retained rather than described as
bit-identical NVRAM. No unrecorded boot change or disk exception is used.

**Not verified:** real installed `de` and injected `us` starting-state repair;
localization writer-boundary diagnostic; stock/AresOS/backup cmdlines and loaded
console maps; layout-sensitive tty3 login and password sudo; physical typing in
foot; US change and German restoration; pin/signed switch; inherited Homebrew
and rendered rollback greeter on this new release. The two successful image
VM passes do not fill these installed-system acceptance items. All laptop,
media, physical keyboard and followability gates remain open. INSTALL's loaded
keyboard gate and both new-release manifests now explicitly record the block.

**Evidence/privacy:** retained [native receipts](../../os/manifest/ci/13/native-1/),
[probe receipts and failure audits](../../os/manifest/ci/13/probe-1/), complete
[native log](logs/native-1.txt) and [probe log](logs/probe-1.txt). Original ZIPs:

| Artifact | Bytes / ID | SHA-256 |
| --- | --- | --- |
| [Native release inputs](artifacts/13c-native-1-release-inputs.zip) | 33,511 / 12584859391 | `0b87c304782e14f988eab007df1501d8ce0e3b36be91d639fb5dd0017d1a22f7` |
| [Probe evidence](artifacts/13c-probe-1-two-disk-evidence.zip) | 4,042,193 / 12585957073 | `f21ced3c8fec023d6daaac595afa8beecae3352eb9839cc90c7af34203aa32ed` |

Both match GitHub's artifact digests. Downloaded raw log ZIP SHA-256 values:
native `93c2cfa936e6ff2889fc48bdb5efb80e4449b88a0cae475a47d57be24ffe0bd6`;
probe `d2726ab8c10c86aace5998d03a6c3cd9382dd27bc4c75f3c7f8b19ac10a9d2a8`.
Those original [native log ZIP](artifacts/13c-native-1-logs.zip) and
[probe log ZIP](artifacts/13c-probe-1-logs.zip) are retained unchanged. Expanded
text copies normalize line endings and trailing whitespace; original artifact
ZIPs preserve all guest output bytes.
All 139 text members and both expanded logs were checked for unmasked GitHub
token forms, SHA-512 password hashes and private-key headers: none found.
Safe member-path and credential-file exclusion checks passed. No sensitive
test password was entered in this probe. The original ZIP includes disposable
firmware snapshots, not VM disk images or owner credentials.

Final dispatched-head source privacy runs
[40159241920](https://github.com/Ares-Empire/AresOS/actions/runs/40159241920) (push)
and [40159246354](https://github.com/Ares-Empire/AresOS/actions/runs/40159246354)
(PR) passed gitleaks, private commit emails and personal terms; the personal-term
check was **not skipped**. Their log hashes and executed-step proof are retained
with each receipt. The closing evidence commit is checked again after its
fast-forward push; exact closing run IDs/results and final rounding go in
[PR #12](https://github.com/Ares-Empire/AresOS/pull/12), avoiding endless
report-only pushes.

### 13c actual package budget and open decisions

Same first-dispatch ledger, **2026-10-25T02:02:34Z**, cap **380 minutes**.
Probe job: 03:47:40–04:01:41 UTC = **14m01s, rounded to 15 minutes**.
The final read-only guard proved all **20 unique history IDs / total_count 20**
in one complete snapshot; eight pre-first-dispatch privacy runs are retained
in history and excluded from this ledger. No active jobs remained.

| Run(s) / item | Result | Rounded minutes |
| --- | --- | ---: |
| 40152936417, image attempt 1 | cosign PATH failure before build/publish | 4 |
| 40153703131 / 40153706252, 13b closing privacy | passed | 2 + 2 |
| 40153916476 / 40153919146, owner 13c brief privacy | passed | 2 + 2 |
| 40154503307 / 40154507842, image-source privacy | passed | 2 + 1 |
| 40154642447, image attempt 2 | passed; single private publication | 65 |
| 40159241920 / 40159246354, dispatched-head privacy | passed | 2 + 2 |
| 40159399419, checks-only native | passed | 1 |
| 40159515328, fresh probe | failed at German list-item activation | 15 |
| Qualifications | not dispatched | 0 |
| **Observed total before closing evidence push** | | **100** |
| Closing push/PR privacy | automatic; actuals recorded in PR after completion | **4 reserved** |
| **Observed + closing reservation** | within 380 cap | **104** |

[Complete budget receipt](../../os/manifest/ci/13/probe-1/budget-before-closing.json).
Dispatch counts: images **2/3**, native **1/1**, probe **1/1**, qualifications
**0/2**, publish **1/1**. Image attempt 3 was not used; after publication the
guard rejects another image dispatch. No Part B or package-11 budget was used.
An exhausted probe allowance and missing passing proof stop qualification even
though minutes remain.

**JUDGMENT-CALL:** the integrator-approved exact frozen-image derivation, with
only the two keyboard files differing, still requires owner review before merge.
No additional product decision was made to work around the failed UI check.
**PLAN-GAP:** no new contradiction in pinned source is established; the concrete
blocker is the fixture's inability to activate the real KDE German list item.
**Open questions:** which active-dialog/interface handling is required, and all
unreached installed-system/hardware results above. A follow-up must authorize
any new probe; no additional CI is dispatched in this run. No Gradle daemon was
started. Work stayed in package 13; no retired worktree access.

Closing documentation/metadata checks: both exact owner-block equality tests
passed locally in WSL (**2 / 0.030s, OK**). The first test selection misspelled
the GRUB test class and failed to load it; the corrected selection above passed.
WSL Git cannot resolve this Windows worktree's absolute Git pointer, so the
frozen-runtime comparison and `git diff --check` ran with host Git and passed.
Both current/history-13 manifests match and record private/blocked/zero
qualification runs. Runtime payload still equals the published 2abc12e source.

## 13d — installed-system qualification; live desktop stays a laptop gate (2026-10-25)

**Status before dispatch: preparation and local whole-suite verification.**
Fetched and pulled `--ff-only` first; clean branch at owner brief `10cf1e9`.
The complete 13c result, published private digest, image comparison, signature,
217 native successes and failed probe remain historical evidence above.

**Done:** neither `two_disk_vm.install()` nor `live_probe()` invokes
`live_keyboard_ui.run()` now. That fixture file and its unit test are retained,
unchanged, but no qualification entry point uses it. Its KDE settings/KWrite
physical typing is explicitly **not VM-qualified**; it belongs to the real
laptop/followability checklist. INSTALL §4 step 1 remains the owner's exact
normal-settings/text-editor instruction. The release gate states that successful
installed-system CI cannot close this physical gate. The installer Web UI's
German choice, saved localization confirmation and all installed-system checks
are unchanged. Probe evidence records `live_desktop_keyboard:
laptop-followability-only`; it no longer claims live German physical typing.

**Native gate / allowance:** the single checks-only dispatch was already used.
No additional one is dispatched. Each fresh probe already runs the complete
native suite and syntax/source verification before any VM. Its initial guard now
reserves the budget with **pending** native status; after that existing native
step passes, a second fresh guard reads GitHub's completed step on this exact
head and writes passed authorization before registry credentials/VM preparation.
The VM entry point refuses pending, failed or different-head native proof.
Qualification requires the passing same-head probe and its completed native
step; full probe artifact/signature/disk/firmware predicates still apply.
This preserves native-before-VM without an unapproved checks-only dispatch.
Regression cases cover failed/skipped/pending native steps, incomplete/ambiguous
job listings, wrong source/event/attempt, pending VM rejection and a third probe
refused. The probe cap becomes two total (13c's failed one + this one); all other
dispatch caps, the ledger start, minute cap and publication boundary stay intact.

**Verified before whole-suite completion:** 18 focused tests / 0.055s, OK. The
new tests exercise the actual install/probe entry points with a fixture that
fails if the unused KDE code is called, and validate the native authorization
protocol. Existing package-11 budget assertions still cover unchanged probe/job
timeouts and full/B caps. The complete local suite and syntax checks must finish
before source push/dispatch; every local host-limited case remains mandatory in
the probe's native preflight.

### Zero-cost stage walk-through before any 13d dispatch

1. Finish complete local discovery, syntax and frozen-runtime comparison.
   Source push must pass gitleaks/private emails/personal terms with no skipped
   personal-term scan. Fresh complete-history guard must fit the whole plan.
   At owner head, all 24 unique history IDs matched total_count 24, and the
   ledger is **108/380**: 104 from 13c plus owner-brief privacy 2 + 2. No jobs
   were active. Reserve probe 42 + one qualification 130 + closing/privacy 14 =
   **186**; 108 + 186 = **294**, plus actual source privacy rounding (plan 4).
   No image build, publication or extra standalone native dispatch.
2. One fresh probe on the final harness head: initial budget reservation →
   pinned toolchain and full native/syntax/frozen-image verification → GitHub
   completed-native-step guard → read-only job-token private metadata/signature
   and exact layer pull → full pinned ISO hash/source inspection → both live
   disk mappings and unmodified installer UI through review, saved German choice,
   read-only keyboard/reader checks, localed session-reader transport, stock
   pause/kargs-help recipe and failure counter/OCR preflight → detached Windows
   marker/target reset → reverse mapping. Every reached protected-disk, NVRAM,
   BootNext and final counter remains required. No KDE/KWrite action or live
   physical typing is attempted or asserted. Stop if any probe predicate fails.
3. Only passing probe/privacy/native on that exact head permit a fresh guard
   and one **protected-second** qualification (130 reserved). No Part B.
   Baseline marker → real installer English/German choice/removal of US/save
   and Berlin settings → credential-safe boundary localization diagnostic →
   installation → first stock firmware-default start without BootNext, with
   the pinned-source-authorized hardware initialization reset only if observed.
4. Read installed console/X11/options plus initial cmdline and loaded map before
   pause. Run the exact owner repair on the actual installer value; inject `de`
   then repair, inject `us` then repair. Require the same stock checksum/serial,
   one deployment and unchanged unrelated arguments. Pause then pin exact stock;
   shutdown/audit. Restore Windows-first, then unattended attached and detached
   Windows markers with BootNext absent.
5. Corrected stock boot: every BLS entry and cmdline free of console overrides,
   loaded German map, physical-key tty3 login with `yz-/!` sensitive password,
   password sudo, public `yz-/!` text and inherited Homebrew audit. Verify the
   existing signed private release, run the exact owner switch and inspect the
   pending deployment before shutdown/audit.
6. AresOS German boot: cmdline/maps, tty3/password sudo/text, policy, Homebrew,
   actual labwc XKB environment and physical QMP typing in foot. Change normal
   console/X11 settings to US, reboot/audit, repeat both physical screens/maps;
   change back to German, reboot/audit and repeat. Then run exact rollback and
   require the queued stock identity before shutdown/audit.
7. Backup stock boot: exact retained checksum/digest, every entry/cmdline clean,
   loaded German map, real tty3/password sudo/text and unchanged Homebrew marker;
   rendered Plasma rollback greeter. Final unattended attached/detached Windows
   markers, all offline disk/firmware/BootNext checks. Only complete evidence may
   pass the installed-system acceptance items. No physical laptop work.
8. A second qualification is conditional on a fresh guard fitting its full
   130-minute reservation plus closing costs; no failed product/audit can be
   excused by unused slots. Preserve the same passing-probe head. No additional
   probe, image or publish is authorized. Retain bounded credential-safe evidence,
   update this REPORT/manifest/gates, fast-forward push and require final privacy.
   PR #12 becomes ready only if package acceptance is met; never merge.

Qualification stage estimate within the 130-minute job: setup/pull/ISO 20–24;
install/first stock 25–30; repair/pause/pin/Windows 8–12; corrected stock/signed
switch 10–15; three AresOS layout boots 12–18; rollback/greeter/final Windows
8–12; shutdown/evidence/guard margin 10–19. The VM step retains 106 minutes and
the job 130; probe reservation remains 42 with its 40-minute job limit.

**Not verified / laptop gate:** setting KDE live German and physically entering
`y z / - " $ ä ö ü` in a text editor on the real laptop, physical media/hardware,
menu interaction and unaided followability remain OPEN. The unused fixture is
not evidence for these. All installed-system results above remain pending until
their actual run. **JUDGMENT-CALL:** moving only the live-desktop fixture is the
integrator's explicit 13d decision; no additional product change. The accepted
two-file image derivation still needs owner review before merge. **PLAN-GAP:**
none established by the zero-cost stage walk-through. No Gradle/Minecraft or
local privileged operation is needed; the retired worktree is never accessed.

**Complete local verification before source push:**
`python3 -m unittest discover -s os/tests -v` under existing WSL, with TMPDIR
inside this worktree and sudo replaced by a rejecting shim, printed **223 tests
in 78.671s; FAILED (failures=2, errors=9)**. Exactly the same eight host-limited
cases as 13b/13c account for these; every other case, including all six new
cases, passed. No skip or assertion change:

- Three `test_greeter` image cases need Pillow, absent in WSL (no local install).
- Three `test_inherited_homebrew` cases need privileged ownership/tmpfiles/ACL
  setup and cleanup; the local shim returns `LOCAL_ADMIN_OPERATION_FORBIDDEN`,
  exit 126. Cleanup errors add to the error count for the same test cases.
- `test_sysusers` requires privileged isolated-root sysusers setup; also denied
  by that shim with exit 126.
- The owner-auth mode test expects 0600; DrvFS reports 0777 (`511 != 384`).

All eight remain mandatory and must pass in this fresh probe's native preflight
before VM authorization. Full Bash/Python syntax printed
`ALL_SYNTAX_CHECKS_PASSED`; `git diff --check` passed. Host Git found no difference
from published 2abc12e in every frozen runtime/package/base/policy/key/audit path,
and no difference in the retained unused KDE fixture. No Gradle was run because
this is OS harness/documentation work, with no mod change or green game claim.


### 13d execution — fresh probe passed; qualification stopped

**STOP / PLAN-GAP. Acceptance is not met; PR #12 stays draft.** Both dispatches
used exactly `25f58cf6dbf819493f810e5bcdcde94f439cd91f`. The source remained
unchanged between probe and qualification. No image dispatch or publication,
second qualification, new probe, source repair or weakened identity check
followed the failure. This is an unsupported product/recipe precondition, not a
covered transient retry. A second reservation could fit the minutes; that does
not override the stop rule or make an unchanged rerun useful.

**Fresh probe passed:** [40168412078](https://github.com/Ares-Empire/AresOS/actions/runs/40168412078).
Complete native discovery printed **223 tests / 5.367s, OK**, no skips; all eight
host-limited cases passed natively. The completed-native-step guard passed on
this exact head, with no read retry. Pinned tools/ISO/source/frozen-image checks,
private metadata/layer read, both real installer review paths and saved German
choice, reader/stock-pause/CLI/failure-counter/OCR probes, target reset and
detached Windows-like markers all passed. No installation was performed by the
probe. The protected-second [saved `de` summary](screenshots/13d-probe-2-protected-second--keyboard-save-committed.png)
was visually inspected. It is the installer's choice, not live KDE automation.

Local read-only evidence replay passed: **6** offline protected captures equal
the full baseline/GPT/EFI records, SHA-256
`176063934d8c6fa2d5bba01d002d86ca21820df0d01bd449af70a6f1aa3c9305`;
**8** zero-write/unmap counter records; **6** passing BootNext audits; **4**
NVRAM comparisons re-evaluated with the unchanged 11f rules and matched their
recorded results. [Replay receipt](../../os/manifest/ci/13/probe-2/local-replay.json).
The proof says `live_desktop_keyboard:laptop-followability-only` and contains
no passing live-German-physical assertion. The unused fixture was not invoked.

**Qualification failed:** [40170232822](https://github.com/Ares-Empire/AresOS/actions/runs/40170232822),
protected disk second. Complete native suite **223 / 4.112s, OK**, no skips;
initial guard, exact same-head passing-probe artifact/native proof, frozen
release checks and private access passed. The unmodified installer completed
with target `vda` and protected `vdb`, saved German choice and Berlin settings.
The retained boundary diagnostic ran. The first stock firmware-default boot
performed **one** source-authorized orderly hardware-setup reset, then reached
the installed stock root shell. Installed files read `de`, X11 model `pc105`,
empty options; initial `/proc/cmdline` contained **`vconsole.keymap=de`**. The
loaded map records literal keycode 21 = `+z` and keycode 44 = `+y`. These initial readings
do not substitute for corrected arguments or physical login/sudo/foot typing.

The next command, `repair-installer-value`, printed:

```text
Traceback (most recent call last):
  File "<stdin>", line 59, in <module>
  File "<stdin>", line 38, in fix
  File "<stdin>", line 12, in identity
AssertionError: STOP: fix the keyboard before pin/switch; expected one stock deployment
ARESOS_CMD_DONE:1
```

The **initial** `before = identity(state)` is line 38 of the script's Python
heredoc. It runs before reading/changing kargs and before `ostree ... set-kargs`
or `rpm-ostree reload`; neither repair write ran. The exact owner script was
not changed. Earlier digest/no-staged/no-queued/no-active-transaction assertions
had passed. The raw deployment JSON is not exported by this failing command,
so the exact deployment list/count/checksums cannot be reconstructed from it.
The initial BLS capture independently contains **two entries**:

| BLS file | Title / version | Observed argument |
| --- | --- | --- |
| `ostree-1.conf` | `Bazzite (ostree:1)` / `1` | `vconsole.keymap=de` |
| `ostree-2.conf` | `Bazzite (ostree:0)` / `2` | `vconsole.keymap=de`, plus `bluetooth.disable_ertm=1` |

Their boot targets have different `/0` and `/1` suffixes under the same boot
checksum path. A BLS boot checksum is not used as a substitute for the missing
checksum-resolved deployment identity. The authorized hardware-setup reboot
preceded this state; the Bluetooth argument is consistent with hardware setup
having changed deployment arguments, but that exact cause is **an inference**,
not an exported rpm-ostree transaction/deployment proof.

The cleanup stage is statically named `first-stock-fixed-pinned`; that label
does **not** mean repair or pin succeeded. Neither injected `de`/`us` repair,
pause, pin, Windows-first restoration, corrected-stock boot, signed switch,
AresOS boot/typing/layout changes nor rollback was reached. No
`keyboard-result.json` exists. The [failure screenshot](screenshots/13d-qualification-1-failure-first-stock-fixed-pinned.png)
was visually inspected: a stock clock/splash, not a qualified rollback greeter.

### Diagnostic values and failure-path safety

The read-only localization monitor retained **976** messages and allowlisted
Get/reply pairs only. Diagnostic summary:

| Property | Observed reply pairs | Last observed value |
| --- | ---: | --- |
| Language | 1 | `en_US.UTF-8` |
| XLayouts | 17 | `["de"]` |
| VirtualConsoleKeymap | 6 | `de` (earlier replies were empty) |
| LayoutSwitchOptions | 4 | `[]` |

Final keymap Get/reply: client `:1.7`, cookie **6692**, request
`1792912310789333`, reply `1792912310802697` microseconds since epoch
(2026-10-25 07:11:50 UTC). It is consistent with the pinned `_set_kargs` boundary
and observed `vconsole.keymap=de`; the monitor does not independently map that
client to a process. This run records `de` and does not explain the historical
`us` runs. These values remain diagnostic only; no cause gate was reinstated.
[Summary and raw trace](../../os/manifest/ci/13/qualification-1/diagnostic-summary.json).

All **4** reached offline protected captures match baseline/GPT/EFI records,
full SHA-256
`869efd1fc4094017211c837d869b16140c46fcfde49fc106fdebcf4344ecbb2f`.
All **5** retained protected counters show zero write bytes/operations and zero
unmap bytes/operations, including the final paused-VM failure counter (boot 4).
All **4** BootNext audits passed, including absent BootNext at the first stock
firmware-default start. All **3** reached NVRAM comparisons were replayed with
the unchanged 11f rules, target ESP and actual device records and matched.
The expected Linux EFI installation is not described as identical NVRAM.
[Failure-safety replay](../../os/manifest/ci/13/qualification-1/local-replay.json).
No protected-disk, unrecorded firmware or BootNext exemption was added.

Both runs verified private visibility and exact layer reads using only the
read-only job token, with no owner-token fallback/API use. Both always-cleanup
records say `removed:true`, `outside_workspace:true`, `owner_token_used:false`.
Only read-only auth-file mount paths cross the guest console; registry-client
commands use private diagnostics. No credential file or VM disk image was
retained. Sensitive-password typing on tty3 was not reached.

### PLAN-GAP and remaining acceptance

**PLAN-GAP:** the repair assumes exactly one stock deployment before pause/pin.
The real post-initialization stock state violates that precondition. The
zero-cost OSTree verification established that the chosen primitive does not
append a deployment; it did not establish that the first stock start already
has exactly one. Unit fixtures supplied one and therefore did not expose this
initial-state gap. This failure does not contradict the primitive's source
behavior: it stopped before that primitive ran.

A follow-up needs actual bootc/rpm-ostree JSON and checksum-resolved BLS targets
after hardware setup, then an identity-safe plan for every legitimate bootable
stock entry. Do not select by menu/file digits, silently remove deployments or
relax the one-match/identity guards. Any changed harness needs a fresh same-head
probe; 13d's single fresh-probe allowance is consumed. No such change is made in
this stop.

**Additional unreached verification gap:** the retained `dumpkeys` rows contain
`+z` / `+y`, while `keyboard_state()` currently requires bare `z` / `y` in its
post-repair regexes. Applying those regexes to this actual initial capture does
not match. The diagnostic call returned before those assertions by design, so
this was not the run's thrown failure. The follow-up must verify the pinned
tool's notation and test the parser against these retained rows, preserving the
layout-sensitive key-value assertions. No parser/assertion change is made here.

**Not verified:** real starting-state `de` and injected `us` repair; corrected
stock/AresOS/backup cmdlines without overrides and loaded maps; physical-key
tty3 login/password sudo and foot; layout change/back; pause/pin/signed switch;
inherited Homebrew on the new switched system; rollback and rendered backup
greeter. The initial German map reading and passed image VM tests cannot close
these items. The explicit laptop live KDE/text-editor/followability, physical
media/menu/hardware gates remain OPEN and physical installation NOT RELEASED.
Both new-release manifests now record this latest failed qualification and
preserve the prior failed-probe attempt as history. The owner guide's current
status and loaded-keyboard gate name this stop.
EMERGENCY no longer calls the unreached change-layout command “tested.”

**JUDGMENT-CALL:** only the explicit 13d scope movement was implemented. The
integrator-approved exact frozen-image/two-file derivation still requires owner
review before merge. **Open questions:** the actual initial deployment list and
the safe multi-entry repair/identity plan, plus all unreached results above.

### 13d evidence, privacy and actual budget

[Probe receipts](../../os/manifest/ci/13/probe-2/),
[qualification receipts](../../os/manifest/ci/13/qualification-1/),
[probe log](logs/probe-2.txt), [qualification log](logs/qualification-1.txt).
Original ZIPs match GitHub's artifact digests:

| Run artifact | Bytes / artifact ID | SHA-256 |
| --- | --- | --- |
| [Probe evidence](artifacts/13d-probe-2-two-disk-evidence.zip) | 6,420,671 / 12589828692 | `2f16515acaed95418617d214c524bafdfc8f56e38c34ffb612cf967a0945f7ff` |
| [Qualification evidence](artifacts/13d-qualification-1-two-disk-evidence.zip) | 5,775,253 / 12590966135 | `e9bccbaa26aac875b2456165e859e03b3311377a49287f5f3180b0ed76071083` |

Original [probe log ZIP](artifacts/13d-probe-2-logs.zip) SHA-256
`61b4763b2f1348056a4ded7d485435b4b2e19732510ae063451defda104ba1bc`;
[qualification log ZIP](artifacts/13d-qualification-1-logs.zip)
`81f8b2533b8b48f77d791d07fcdd041e5b6b1539a6ce7199b013f51ac2035774`.
Expanded text normalizes line endings/trailing whitespace; originals remain
unchanged. Safe ZIP paths and credential-file exclusion passed. All **352**
probe and **234** qualification text members plus both logs were checked for
unmasked GitHub token forms, SHA-512 password hashes, private-key headers and
the generated sensitive-password form; none found.

Dispatched-head push privacy
[40168272698](https://github.com/Ares-Empire/AresOS/actions/runs/40168272698)
and PR privacy [40168276342](https://github.com/Ares-Empire/AresOS/actions/runs/40168276342)
passed all three checks with personal terms **not skipped**. Their raw-log
hashes/executed-check proof are retained with both run receipts. Closing evidence
privacy and exact final rounded totals are recorded in PR #12 after this push,
avoiding endless report-only pushes. Repository and package remain private;
there was no new signing/publication/visibility change in 13d.

Same ledger start **2026-10-25T02:02:34Z**, cap **380**. Fresh final read proved
**28 unique IDs / total_count 28**, one complete page, no active jobs. Probe:
06:14:48–06:42:51 UTC = **28m03s → 29 minutes**. Qualification:
06:45:28–07:20:19 UTC = **34m51s → 35 minutes**.

| Item | Rounded minutes |
| --- | ---: |
| 13c final ledger, including its closing privacy | 104 |
| Owner 13d brief privacy 40167715241 / 40167718420 | 2 + 2 |
| 13d source privacy 40168272698 / 40168276342 | 2 + 2 |
| Fresh probe 40168412078 | 29 |
| Qualification 40170232822 | 35 |
| **Observed before closing evidence push** | **176** |
| Closing push/PR privacy | **4 reserved** |
| **Observed + closing plan** | **180 / 380** |

The guard also fit the broader 14-minute closing reservation, 176 + 14 = 190.
A second 130-minute qualification plus that closing reserve would fit 320,
but it is not dispatched because the product/identity precondition stop holds.
Counts: images **2/3** (none in 13d; publication blocks another), publish **1/1**
(none in 13d), checks-only **1/1**, probes **2/2**, qualifications **1/2**.
No Part B or package-11 ledger use, force-push, merge or retired-worktree access.
No local elevation/software installation/physical disk operation or Gradle daemon.

Closing verification: exact keyboard-repair/INSTALL and switch/INSTALL block
equality tests passed locally (**2 / 0.131s, OK**). Host Git confirmed the harness
still equals 25f58cf and every frozen runtime path still equals the published
2abc12e source; blocked current/history-13 manifests match. `git diff --check`
passed. The qualification review screenshot was also visually inspected: the
synthetic recovery account, Berlin and target-only `vda` storage summary are
visible, with no credential value. No additional test or VM run was needed for
the final evidence/status documentation.

## 13e — two stock entries and dumpkeys notation (2026-10-25)

### Done and zero-cost verification

Confirmed retained 11f `full-2/two-disk/stock-status.json`: booted stock serial 1
and rollback serial 0 share `aa669eff…0c71`, the qualified digest and upstream
origin. **That raw record also contains a newer staged update**; it is not an
accepted repair starting state. The synthetic two-entry fixtures project only
its booted/rollback identities and explicitly remove the staged slot; the
unmodified staged record is a negative test. 13d retained two BLS entries and
`+z`/`+y`; neither observation is rewritten as captured rpm-ostree JSON.

Pinned source retained in [13e-zero-cost](../../os/manifest/ci/13/13e-zero-cost):

- [Bazzite hardware setup](https://github.com/ublue-os/bazzite/blob/2fab72cbc9a3257d80c607e173f22527aea3b39b/system_files/desktop/shared/usr/libexec/bazzite-hardware-setup)
  adds missing Bluetooth args with rpm-ostree and reboots once. This agrees with
  the recorded real duplicate-stock state.
- [OSTree v2026.4 CLI](https://github.com/ostreedev/ostree/blob/v2026.4/src/ostree/ot-admin-instutil-builtin-set-kargs.c)
  selects **deployment index 0, not a booted lookup**. The repair therefore
  requires that index 0 is the uniquely booted stock before invoking it. The
  [set-kargs implementation](https://github.com/ostreedev/ostree/blob/v2026.4/src/libostree/ostree-sysroot-deploy.c)
  replaces that deployment's bootconfig in the existing list; it creates no new
  serial. Whole-list checksum/serial/osname/booted/pinned equality is mandatory.
- [rpm-ostree v2026.3 JSON serializer](https://github.com/coreos/rpm-ostree/blob/v2026.3/rust/src/daemon.rs)
  supplies serial/booted/staged/pinned; its deployment-utils supplies origin and
  container digest. Every one/two entry must be the same unmodified stock
  checksum/origin/digest, with exactly one booted, nothing staged/pinned/active.
- [bootc v1.16.13 deploy/rollback](https://github.com/bootc-dev/bootc/blob/v1.16.13/crates/lib/src/deploy.rs)
  stages the signed switch using the merge deployment's args. Pin changes only
  booted pin state: the unpinned old serial remains until switch finalization.
  OSTree finalization calls simple-write with NO_CLEAN, without RETAIN flags;
  [simple-write](https://github.com/ostreedev/ostree/blob/v2026.4/src/libostree/ostree-sysroot.c)
  keeps pinned/booted/merge, dropping the other unpinned same-stateroot serial.
  Thus staged switch can temporarily have three deployments, but after its
  reboot exactly AresOS + corrected pinned stock must remain. Rollback reorders
  this pair. Any surviving old serial in that final state stops qualification;
  no manual deletion is authorized or implemented.
- [kbd v2.9.0 dump.c](https://github.com/legionus/kbd/blob/v2.9.0/src/libkeymap/dump.c)
  prints `+` for KT_LETTER; [keymaps(5)](https://github.com/legionus/kbd/blob/v2.9.0/docs/man/man5/keymaps.5)
  describes CapsLock-sensitive letters. The parser accepts bare or single-plus
  letters while requiring de 21=z/44=y, us 21=y/44=z. US fixture derives from
  us.map's qwerty-layout include, and is explicitly synthetic.

`system-keyboard.sh` and the exact INSTALL block now compare the whole list;
the VM checks count 1/2, exports raw rpm-ostree and bootc status before deciding,
resolves BLS entries through actual ostree symlinks to checksum+serial+stateroot,
and proves the non-booted stock args unchanged. The audit of new package-13
single-entry assumptions found the script, its result assertion and test setup,
plus `keyboard_state`'s premature all-entry check. Corrected stock checks its
own entry while the exact old serial remains temporarily untouched; after
switch finalization **every** BLS entry and cmdline must be override-free.
No menu/file digits select a deployment. All inherited disk/firmware audits
and frozen release payload paths remain unchanged. Live KDE/KWrite fixture
stays unused; the owner laptop/followability step and physical release gate stay open.

### Zero-cost stage walk-through, before any dispatch

1. Fetch/pull were fast-forward only, starting at owner brief `0d3ba91`.
   Complete local suite, owner block equality, syntax, frozen-payload diff and
   privacy checks must complete before dispatch. No image/native-only dispatch.
2. Current complete-history guard: **184/380** (180 at 13d close + owner 13e
   privacy 2+2), 32 unique run IDs / total_count 32, no active jobs. Reserve
   probe **42**, full qualification **130**, closing **14** = **186**;
   current 184+186=370, with planned source privacy 4 → **374 ≤ 380**.
   Refresh guard after source privacy and again before qualification. Probe cap
   becomes three total; qualification stays two total (one old + one new).
3. One fresh probe on new final head: scheduling guard → full native regressions
   and pinned tools/source/frozen verifier → completed native-step proof guard
   → read-only private job-token pull → both live mappings and original installer
   through saved-German review → reader/pause/failure-counter/BootNext/protected
   predicates → reset/detached Windows-like markers. No live KDE or KWrite.
   Require every predicate; stop on any failure, with no replacement probe.
4. If probe passes and fresh guard fits 130+14, one qualification on **the same
   head** in protected-second order. Actual installer/German choice/boundary
   diagnostic → orderly hardware-setup reboot if source-authorized → export
   raw rpm/bootc status and resolved BLS **before repair** → installed de files.
5. Repair actual value, inject de/repair, inject us/repair. Each repair compares
   whole-list identities and unchanged non-booted arguments. Pause/pin exact
   booted stock, export/assert full list (only its pin changes) → poweroff/audit
   → Windows-first restoration and attached/detached unattended checks.
6. Corrected stock boot: own args/cmdline/map de, physical tty3 login/password
   sudo and `yz-/!`, inherited Homebrew; signed switch/inspect staged identities
   and full list. Old stock can still be present here without being booted.
7. AresOS reboot: full list must be exactly new AresOS plus corrected pinned
   stock; old serial absent. All entries/cmdline clean; loaded de, tty3 physical
   login/password sudo, policy/Homebrew and real labwc/foot physical text. Change
   normal settings to us → reboot/prove both screens → change back de → reboot
   and repeat → rollback transaction and full list export/assert.
8. Rollback boot: exact corrected pinned stock checksum/serial, only final pair,
   no overrides, de loaded map/physical tty3/password sudo, Homebrew and rendered
   stock greeter. All reached audits mandatory, final attached/detached Windows
   checks. Retain original privacy-safe artifacts/logs, replay audits, update
   truthful gates/REPORT/manifests; FF push and closing privacy/ledger. Ready only
   if acceptance is met. Never merge/force/public; never print or store tokens.

### Verified / not verified / decisions

This was the pre-dispatch status; actual local and Actions results follow below. The source facts and
new fixture/parser tests above do not claim VM success. No frozen path changes,
image dispatch or publication. **JUDGMENT-CALL:** the first-entry-is-booted guard
is necessary to use the pinned CLI safely; a different booted/default ordering
stops rather than selecting or reordering anything. **PLAN-GAP:** none established
against the real duplicate-stock cause; the raw 11f staged update and the CLI's
index-zero selection are explicitly accounted for. Open owner decisions remain
the 13c frozen-image construction review before merge and physical followability.


**13e local verification before source push:** complete discovery
`python3 -m unittest discover -s os/tests -v` under WSL, worktree TMPDIR and
rejecting sudo stand-in: **229 tests / 79.149s; 2 failures / 9 errors**, exactly
the same eight unique host-limited cases as 13d, no skips. Three greeter cases
need Pillow; three inherited-Homebrew cases and sysusers need native Linux root
filesystem/ACL operations (local sudo rejected with 126); auth mode test sees
DrvFS 0777 instead of 0600. Every other case passed, including the six added
tests covering real duplicate-stock identities, retained staged rejection,
whole-list mutations, old-entry preservation/final pair, pre-decision raw export
and retained/source-derived layout-sensitive maps. All 229 remain mandatory in
native probe preflight before a VM. [Full local output](logs/13e-local-suite.txt).

Final Bash/Python syntax: `ALL_SYNTAX_CHECKS_PASSED`. Exact keyboard and switch
owner-block equality rerun: **2 / 0.014s OK**. Source hash/frozen-payload replay:
`13E_SOURCE_HASHES_AND_FROZEN_PAYLOAD_PASSED 11`; runtime diff against published
source 2abc12e is empty. Repository API still PRIVATE. No Gradle/Minecraft files
changed and no Gradle daemon started. The earlier Windows targeted run hit its
default cp1252 decoding limit reading INSTALL; the final WSL equality run passed.


### 13e execution — repair passed; physical setup requires a stop

Both dispatches used exactly **`314bca3c596abbd54bc6505b6ecee6fb835d63f0`**.
No source commit/push occurred between them. No further probe, qualification,
image dispatch, publication, workaround or weakened assertion followed the stop.

**Fresh probe:** [40175267914](https://github.com/Ares-Empire/AresOS/actions/runs/40175267914),
08:05:37–08:31:03 UTC, **25m26s → 26 rounded minutes**. All **229 native tests /
4.746s, OK**, no skips; all eight local host-limited cases passed natively.
The completed-native-step guard, private manifest/layer pull, signature, pinned
ISO inspection and every inherited both-order probe predicate passed. The
saved-German [protected-second summary](screenshots/13e-probe-3-protected-second--keyboard-save-committed.png)
was visually checked. The proof explicitly says `live_desktop_keyboard:
laptop-followability-only`; no live KDE/KWrite proof is claimed.
Local replay passed **6 protected captures, 8 zero-write/unmap counters,
6 BootNext audits and 4 NVRAM transitions**; protected SHA-256
`b2140dd71cd540ec5537749b7197074068709a942762802366325059379a0495`.

**Qualification:** [40177141104](https://github.com/Ares-Empire/AresOS/actions/runs/40177141104),
08:34:16–09:22:30 UTC, **48m14s → 49 rounded minutes**. Explicit passing probe
40175267914, protected disk second (`vdb`), Linux target `vda`. Native discovery
passed **229 / 5.311s, OK**, no skips. Pinned tools/source/frozen release and
private manifest/layer/signature preflight passed. The actual unmodified
installer finished with German keyboard, Europe/Berlin and synthetic
`ares-recovery`; its [review](screenshots/13e-qualification-2-review-full.png)
was visually checked. One source-authorized orderly hardware-setup reboot ran.

#### Real deployment identities and both starting states

Raw [rpm-ostree status](../../os/manifest/ci/13/qualification-2/evidence/two-disk/first-stock-before-repair-rpm-ostree-status.json)
and [bootc status](../../os/manifest/ci/13/qualification-2/evidence/two-disk/first-stock-before-repair-bootc-status.json)
were exported **before** the repair. They agree on qualified stock checksum
`aa669eff4ea5c1f97c6c816c8d5d2abb5314e9afa3b966c0100e3e65f8040c71`,
qualified `ed93…5151` payload and stateroot `default`:

| Observation | First deployment | Second deployment | Count / pending state |
|---|---|---|---|
| Before any repair | serial1, booted, unpinned | serial0, not booted, unpinned | 2; no staged/queued/transaction |
| Actual installer de repaired | identical identities | identical identity and args | 2; booted override removed |
| Injected de repaired | identical identities | identical identity and args | 2; booted override removed |
| Injected us repaired | identical identities | identical identity and args | 2; booted override removed |
| After pin | serial1, booted, **pinned** | serial0, not booted, unpinned | 2; only booted pin flag changes |
| Corrected stock boot | serial1, booted, pinned | serial0, not booted, unpinned | 2; no extra deployment |
| Switch / final AresOS / rollback | **unreached** | **unreached** | no runtime lifecycle claim |

All three [repair proofs](../../os/manifest/ci/13/qualification-2/evidence/two-disk/repair-starting-us.json)
passed; their before/after snapshots compare the **whole ordered identity list**.
The old serial0's arguments remained unchanged across every repair and the pin.
Resolved BLS paths independently identify `aa669eff…0c71.1` and `.0`; the kernel
boot checksum `a25775…` is **not** used as a deployment identity.
The corrected serial1's entry and running cmdline have no keymap override;
`bluetooth.disable_ertm=1` and unrelated args remain. The deliberately untouched
old serial0 still has its original `vconsole.keymap=de` during preparation.
No old entry was removed manually. Pin reported no staged discard; the pause
needed no transaction cancellation. Actual cancellation/discard stays unexercised.

After pin, exact Windows-first order restoration, attached unattended Windows-like
boot, detached Windows-like boot and the corrected-stock BootNext selection/
consumption all passed. [Corrected stock keyboard](../../os/manifest/ci/13/qualification-2/evidence/two-disk/corrected-stock-keyboard.json)
has console/X11 `de`, no cmdline override and loaded rows **`keycode 21 = +z`** /
**`keycode 44 = +y`**. The fixed parser accepted them. Its temporary old-entry
exception is identity-resolved and limited to pre-switch stock; the final-pair
and all-entry checks remain mandatory after switch finalization.

#### Exact failure and limits of the typing evidence

Physical QMP tty3 username/password login reached UID1000 bash. Login echo-off
was verified, password sudo produced the required root-owned marker, and all
four readiness/result commands exited 0. The password contained the sensitive
layout positions `y`, `z`, `-`, `/`, `!`; its value is absent from retained/shared evidence.
Then the public-text test tried to type **its setup command**, not `yz-/!` yet:

```text
tty() → physical_input() → type_text('python3 /run/aresos-physical.py\n')
physical_keys('.', 'de')
AssertionError: .
```

`physical_keys` accepts letters/digits and a small explicit punctuation set;
`.` is absent, although the harness types a `.py` filename. This pre-existing
package-13 fixture path was previously unreached. I missed its command-character
coverage in preflight: all 229 native tests passed but did not test this setup
string. A zero-cost check during the run reproduced the exact assertion on the
unchanged head; the real job then confirmed the same stack at line58.
[Local reproduction output](logs/13e-physical-command-repro.txt).

**Do not claim a passing public-text tty3 test or complete login/sudo/logout
flow:** `corrected-stock-tty-physical.json`, its input-ready result and safe tty3
screenshot were never reached. The failure happened while screenshots were
disabled for the password-sensitive phase, so no unsafe failure image was made.
Corrected-stock Homebrew check, release verification/switch, AresOS boots/policy/
foot, US change/back, rollback and rendered rollback greeter were all unreached.
There is no `keyboard-result.json`. No image/runtime failure is inferred from
this host fixture assertion, and no completion is inferred from earlier gates.

**Safety replay:** all **7 protected captures, 8 zero-write/unmap counters,
7 BootNext audits and 6 NVRAM transitions** passed unchanged inherited rules.
Qualification protected SHA-256
`7b04da245c69cd551e7f150225f67a2cfb36d31115fdaab15a066e1cf6bf95b0`.
The corrected-stock failure-path counter is recorded with `probe_only:false`,
`vm_paused:true`, boot7; final protected writes/unmaps are zero. BootNext was
consumed and absent, with Windows still default. Initial Linux EFI creation and
reviewed BootOrder changes were audited, not falsely called identical NVRAM.
Local replay also rechecked pin-only identity changes, unchanged old-entry args
and successful tty login/sudo result markers.

#### Diagnostic only; guide and remaining acceptance

Boundary observer retained 978 messages, allowlisted Get/reply pairs: Language
1 (last `en_US.UTF-8`), XLayouts17 (last `[de]`), VirtualConsoleKeymap6 (last `de`),
LayoutSwitchOptions4 (last empty). Final console Get client `:1.7`, cookie9049;
request/reply times are in [stop-summary.json](../../os/manifest/ci/13/qualification-2/stop-summary.json).
These agree with this install's `de` argument; they remain diagnostic only,
with no independently exported client-to-process identity and no explanation
of historical `us`. Repair success does not depend on this value.

INSTALL and EMERGENCY now distinguish the **observed** two entries through pin/
corrected-stock boot from the **source-verified, runtime-unverified** switch
finalization (AresOS + corrected pinned stock only) and rollback reordering.
A surviving old serial in a final state must stop; it has not been observed
because no switch ran. The stale abbreviated old-release digest in INSTALL's
inspection prose is corrected to `9b19…f3eb`; full reference/owner switch block
already selected that exact existing private release. No frozen path changes.

**JUDGMENT-CALL:** the guide records the final unique stock menu title only after
a successful AresOS boot confirms the pair. Before that, duplicated stock
checksums make a guessed title unsafe, so an initial failed switch boot uses
F12 → Windows/get help. An automatic checksum+serial recovery selector would
need a separately authorized plan and qualification; it is not added here.
Owner review of 13c's exact-frozen-image construction still precedes merge.

**PLAN-GAP / required stop:** the physical typer must cover every character in
its own setup commands (including the dot's real QMP key position), with de/us
regressions preserving the layout-sensitive assertions. It is not changed
after the passing probe: that would require a fresh same-head probe and full
qualification. This follow-up's one fresh probe is consumed, and a fresh guard
also refuses another full+closing reservation: **263 + 144 = 407 > 380**.
No retry, workaround, deleted assertion or extra dispatch follows. This is an
unresolved fixture coverage gap, not green acceptance. PR #12 stays draft;
physical installation, live KDE/KWrite, hardware/media and followability stay
**OPEN / NOT RELEASED**. The post-switch real entry list, foot, layout round
trip and rollback are explicit unverified acceptance items.

### 13e evidence, privacy and package budget

Original immutable artifacts and logs are retained; expanded JSON/TXT mirrors
are under [probe-3](../../os/manifest/ci/13/probe-3) and
[qualification-2](../../os/manifest/ci/13/qualification-2). Expanded text only
normalizes line endings/trailing whitespace; original ZIP bytes are unchanged.

| Artifact | Bytes / ID | SHA-256 |
|---|---:|---|
| [Probe](artifacts/13e-probe-3-two-disk-evidence.zip) | 6,419,010 / 12593210665 | `769fd134690f87cf6936878020609a08f140a996975d8e281d4f42e8e32078e6` |
| [Qualification](artifacts/13e-qualification-2-two-disk-evidence.zip) | 7,265,559 / 12594221308 | `20e7fc82cf62d17a79acc27009c8181ca93c64d75024c3cc576fcd59499d401f` |

[Probe log ZIP](artifacts/13e-probe-3-logs.zip) SHA-256
`13f7cfbec8dd84071ce51e2be3e1fde80ba89b705b1d26887a341c05f3d0b4eb`;
[qualification log ZIP](artifacts/13e-qualification-2-logs.zip)
`009206b02b93a594f3e3dfc123196ac5910c726fd43d7fd1b508628a59f82438`.
Expanded logs: [probe](logs/probe-3.txt), [qualification](logs/qualification-2.txt).
352 probe and 374 qualification text members plus logs passed credential-pattern
checks; artifact digests/member paths verified, forbidden auth/credential files
absent. Both jobs' preflight reports PRIVATE, read-only **GITHUB_TOKEN**, no owner
token use/API calls; credential cleanup passed outside the checkout. No new
signing, publication, visibility change or token output/storage occurred.

Source push/PR privacy **40175080660 / 40175083403** passed gitleaks/private
commit emails/personal terms, **personal terms not skipped**, 2+2 rounded minutes.
Their log ZIP hashes are in each run folder's source-privacy.json. Closing
evidence privacy and final actual rounding will be recorded on PR #12 after
the closing FF push, avoiding a self-referential report-only push loop.

| Package-13 ledger item | Rounded minutes |
|---|---:|
| Final 13d total | 180 |
| Owner 13e brief privacy 40173924648 / 40173927826 | 2 + 2 |
| 13e source privacy 40175080660 / 40175083403 | 2 + 2 |
| Fresh probe 40175267914 | 26 |
| Qualification 40177141104 | 49 |
| **Actual subtotal before closing** | **263 / 380** |
| Closing reserved by fresh guard | **14** (4 expected; actual to be verified) |

Fresh complete history proves **36 unique IDs / total_count36**, one complete
page, no active jobs. First dispatch remains 2026-10-25T02:02:34Z. Counts:
images2/3, publish1/1, checks-only1/1, probes3/3, qualifications2/2. No image or
publication occurred in 13e. Another full+closing guard explicitly refused
`263 + 144 reserved exceeds 380 minutes`; the retained refusal records the
complete history. Remaining wall/billed minutes do not authorize an extra probe
or cure the failed fixture. No further dispatch is planned.

**Open questions:** authorization and budget for a separately tested physical
command-key fix and fresh probe/qualification; then runtime confirmation of the
source-verified final entry lifecycle and every unverified gate above. No
mid-run owner answer is requested. The owner still reviews the frozen-image
construction before merge; this run never merges or makes anything public.


**Closing local checks:** exact keyboard and switch owner-block equality:
**2 tests / 0.162s, OK**. `git diff --check` passed. Harness/release/test source
diff against dispatched head 314bca3 is empty; frozen payload diff against the
published 2abc12e is empty. Both blocked release manifests match; raw artifact
ZIP digests rechecked. No new code change requires or authorizes another VM run.


## 13f — physical typer coverage and one final qualification

### Done before dispatch

Fetched, then pulled with `--ff-only` first, on `pkg/13-keyboard-layout` in the
package 13 worktree only. Read 13f with 13–13e and the retained 13e stop. No
retired package 11 worktree was accessed. No product, owner-script, image,
publication, workflow timeout or audit change is authorized or made by 13f.

`os/ci/keyboard_vm.py` now covers period, semicolon and apostrophe using actual
per-layout QMP positions. Unknown characters still raise; empty and multi-character
inputs now also fail explicitly. Existing `y`, `z`, `-`, `/`, `!` distinctions
are unchanged. `test_keyboard_walk.py` collects every actual physical typing call
from the real qualification main, adds the whole generated password alphabet,
and includes both layout-change command strings. Their serial-root transport is
unchanged. All collected strings must be typable on **both** layouts.

Pinned source verification precedes dispatch: installed xkeyboard-config
**2.47-1.fc44**, kbd **2.9.0-4.fc44**, runner QEMU
**1:8.2.2+ds-0ubuntu1.18**. The retained
[source copies, hashes and key table](../../os/manifest/ci/13/13f-zero-cost/README.md)
link to the exact [XKB 2.47 German source](https://gitlab.freedesktop.org/xkeyboard-config/xkeyboard-config/-/raw/xkeyboard-config-2.47/symbols/de),
[US source](https://gitlab.freedesktop.org/xkeyboard-config/xkeyboard-config/-/raw/xkeyboard-config-2.47/symbols/us),
[kbd 2.9.0 German map](https://raw.githubusercontent.com/legionus/kbd/v2.9.0/data/keymaps/i386/qwertz/de.map),
[QEMU 8.2.2 QMP schema](https://raw.githubusercontent.com/qemu/qemu/v8.2.2/qapi/ui.json)
and its pinned keycodemapdb revision `f5772a62ec52591ff6870b7e8ef32482371f22c6`.
Period is `dot` on both. Semicolon is German Shift+comma versus US semicolon;
apostrophe is German Shift+backslash versus US apostrophe. Letter/digit/space/Return
positions and the existing layout-sensitive symbols were checked in the same
sources, including German's inherited Latin definitions and console QWERTZ map.

### Zero-cost stage walk-through, completed before any dispatch

The [host walk receipt](../../os/manifest/ci/13/13f-zero-cost/host-walk.json)
is explicitly **stand-in execution, not VM evidence**. It executes the actual
`keyboard_vm.main`, tty/foot/input functions and host assertions. The stock
prefix comes from retained 13e observations. Future AresOS, staged and rollback
states are explicitly source-derived synthetic inputs (new checksum `b` ×64).
No guest command, owner script, sudo, QEMU or credential operation runs locally.

| Previously unreached path after the 13e stop | Local execution before dispatch | Still requires the real VM |
| --- | --- | --- |
| Corrected-stock tty3 public text | Real `physical_input`, every `physical_keys` call, UID/result checks dispatched to safe stand-in; public proof emitted | Actual tty3 keystrokes and guest UID/output |
| Corrected-stock Homebrew | Actual command construction and single SHA parser; same SHA enforced through all five boots | Real inherited brew ownership, access, execution and bytes |
| Verify and signed switch | Exact existing verify/switch script text collected; transaction and staged whole-list assertions executed | Network/signature verification and real bootc transaction |
| AresOS boots and policy | All three AresOS host branches, exact release reference/digest, loaded-map and final-pair checks executed | Real new image boot, guest policy and kernel maps |
| Foot typing | Actual compositor-layout assertion, physical input and UID1001 proof path executed for de/us/de | Actual labwc environment and terminal input |
| US change and back | Both actual localectl command strings collected, shell syntax checked and all their characters covered for both layouts; next-boot map assertions run | Guest localectl changes and persistence across reboots |
| Rollback | Exact rollback script collected; queued transaction, checksum and retained-pair checks executed | Real rollback and corrected pinned stock boot |
| Rendered rollback greeter | Real readiness/capture loop and thresholds; Windows Pillow metrics on retained real 06c greeter PNG | New guest greeter readiness and newly drawn framebuffer |
| Final entry lists | Actual BLS-to-(checksum,serial,stateroot) bijection and pair assertions at AresOS and rollback; negative surviving-old-entry case stops | Real old serial removal and final menu titles |

The walk collected **41 physical typing calls**, covering all five tty3 stages
and three foot stages, plus the complete password domain and both layout commands.
Generated shell commands passed `bash -n` with LF bytes. No product or owner-script
defect was found. The first whole-suite run caught a new test-fixture class leak;
the stand-in now restores `switch_vm.Guest`, and the whole suite was rerun.

### Verified locally before dispatch

- `python -X utf8 -m unittest discover -s os/tests -p test_keyboard_walk.py -v`:
  **3 tests, OK** (0.226s); complete walk, surviving-old negative and source-based
  punctuation/layout regressions. The complete suite rerun includes the fixture
  restoration fix.
- `python -X utf8 -m unittest discover -s os/tests -p test_organization_budget.py -v`:
  **5 tests, OK** (0.005s). Includes exact 150-minute boundary, 149 rejection,
  stale/malformed/duplicate/unknown billing rows, paid usage, unreadable billing,
  scheduling denial before receipt, and CI requiring no new billing credential.
- `python -X utf8 -m unittest discover -s os/tests -p test_probe_native.py -v`:
  **4 tests, OK** (0.002s); new cumulative allowance is four probes and three
  qualifications, admitting only the one additional pair. A fifth probe fails.
- `.work/13/13f-zero-cost.py`: completed all host stages, **1,140 QMP key events**
  sent only to a stand-in; real retained-frame Pillow path passed.
- `wsl bash .work/13/13f-walk-syntax.sh`: **ALL_WALK_COMMANDS_SYNTAX_PASSED**.
- `wsl bash .work/13/syntax.sh`: **ALL_SYNTAX_CHECKS_PASSED**.
- `wsl bash .work/13/local-suite.sh`: **237 tests in 80.670s**,
  **FAILED (failures=2, errors=9), no skips**. The only eight affected cases are
  the inherited, explicitly local host limits: three greeter tests lack WSL
  Pillow; three inherited Homebrew tests need forbidden local root/ACL/tmpfiles
  operations (rejecting sudo shim returns126, including cleanup duplicates);
  sysusers needs forbidden root; registry-auth mode0600 is reported0777 on DrvFS.
  Every other test passed. All 237 must pass natively before any VM starts.
  The full exact output is retained in `logs/13f-local-wsl-suite.txt`.
- `git diff --exit-code 2abc12e8aa6089f7576143d1fbccb6648a3291bd --`
  the frozen Containerfile/context/locks/config/policy/base/keys/audit paths:
  **exit0**. `git diff --exit-code dc586f4 -- os/release`: **exit0**.
  No Gradle/mod code changed, no daemon started, and no Minecraft test was claimed.

### Budget and dispatch gate

Same ledger, first dispatch **2026-10-25T02:02:34Z**. The fresh read before source
push showed **271/460 minutes**, **40 unique run IDs / total_count40**, complete
one-page history, no active run, image attempts2, publication1, checks1, probes3,
qualifications2. Owner brief privacy runs 40181565867 and 40181571264 add four
minutes to the closed 13e total267.

| Reservation before the one fresh probe | Minutes |
| --- | ---: |
| Completed package work before source push | 271 |
| Expected source push + PR privacy checks | 4 |
| Fresh probe (unchanged full reservation) | 42 |
| One full qualification (unchanged full reservation) | 130 |
| Closing privacy reserve | 12 |
| Planned ceiling | **459 / 460** |

**JUDGMENT-CALL:** closing reserve12 comprises four expected privacy minutes and
eight contingency. Earlier14 was an agent contingency, not a required timeout.
Probe42, full130 and every VM/job timeout remain unchanged. No second
qualification, image dispatch, publication or rerun is allowed. Fresh scheduling
guards before **each** POST must reserve the remaining whole plan:184 before
probe,142 before qualification. If actual privacy costs or fresh usage break
either cap, stop rather than shorten a run or weaken a gate.

The scheduling guard also performs the read-only current-month org
[billing summary GET](https://docs.github.com/en/rest/billing/usage?apiVersion=2022-11-28#get-billing-usage-summary-for-an-organization)
using the existing local gh login. It stores aggregate SKU quantities and a
response hash, no credentials or other-repository names. It requires the exact
organization/period, known standard-Linux minutes and storage units, complete
nonempty usage, finite nonnegative values and zero paid net usage. Unknown units,
SKUs, malformed data or access errors fail closed. Storage GB-hours do not become
minutes. Used minutes conservatively round up the larger gross/discount quantity;
`netQuantity=0` is never treated as zero free minutes consumed. The source check
at09:54UTC reported **1,261 used / 2,000 included**,739 remaining; reserving184
leaves555, above the required **150 for other repos**. The owner states the
spending limit is$0 with usage blocked at exhaustion; no paid fallback is used.
The CI job token gains no billing scope or secret: the fresh local scheduling
receipt is made immediately before dispatch; native CI retains its package,
probe, private-auth and every audit gate. Token scopes and cleanup are unchanged.

### Pending at the pre-dispatch source push (superseded by the execution below)

Real QMP typing, guest commands, new-image boots, loaded maps, policy, signatures,
Homebrew, bootc finalization, entry titles and a new rendered rollback greeter
remain pending the single authorized qualification. Local stand-ins cannot
satisfy acceptance. INSTALL/EMERGENCY and the physical/laptop followability gate
remain open. PR #12 stays draft until all acceptance is reached. The 13e
F12→Windows caution remains pending real pair evidence. No new PLAN-GAP is
inferred from the local environment limits; native preflight is mandatory.


### 13f execution and retained evidence — 2026-10-25

**VM acceptance PASSED.** Exactly one new probe and one new qualification ran,
both on **`1a95433cc2c25015a61376aa2abe9de83a02b29f`**, after the complete
zero-cost gate above. No second qualification, rerun, image dispatch or
publication occurred. No product or owner-script change was needed or made.
The closing commit changes only guides, this report, evidence/source metadata
and release qualification metadata; harness/tests/owner scripts still equal
the probed/qualified head and all frozen runtime paths still equal 2abc12e.

| Run | Result and exact completed job interval (UTC) | Rounded ledger cost |
| --- | --- | ---: |
| [Fresh probe 40182972546](https://github.com/Ares-Empire/AresOS/actions/runs/40182972546) | PASS; 10:00:27–10:26:24,25m57s | 26 |
| [Qualification 40184846815](https://github.com/Ares-Empire/AresOS/actions/runs/40184846815) | PASS; 10:27:30–11:35:49,68m19s | 69 |

Native discovery passed **237 tests  / 5.681s** in the probe and **237  / 5.400s**
in qualification, **no skips**. This includes all eight cases unavailable on
the local WSL host. Native success was required before VM startup in both jobs;
qualification additionally verified the exact-head passing probe and its
artifact digest. Native tests were not rerun on a changed harness afterward.

**Actual scheduling proofs:**

- Probe: **275 consumed +184 reserved =459 / 460**, complete 42 unique IDs  / total 42,
  no other active workflow on this branch. Org GET at 10:00:22UTC: 1,265 used, 735 free;
  whole-plan 184 reservation leaves 551, exceeding the 150 margin.
- Qualification: **301 consumed +142 reserved =443 / 460**, complete 43 unique
  IDs  / total 43. Org GET at 10:27:24UTC: 1,291 used, 709 free; reservation 142
  leaves 567. Its receipt names passing probe 40182972546 and the same exact head.
- Both raw scheduling receipts, with aggregate billing proof/hash and complete
  package history, are in `probe-4/host-dispatch-authorization.json` and
  `qualification-3/host-dispatch-authorization.json` under `os/manifest/ci/13/`.
- Source push privacy 40182804966 and PR privacy 40182808712 passed all three
  rules, with personal terms **executed, not skipped**, two minutes each.
  Source privacy log ZIP SHA-256 values are
  `b473e0855e945d9350190efc3d752114c17b9f90e27af6c6113b73ee1b16e032`
  and `1507f7c1b6af77e599f760bdbb76b2dd383525ac30fbb3d91cbb01c6d2d1f48e`.

**Probe evidence:** both inherited disk orders, installer-through-review only,
exact target/EFI review, no install commit, target reset, detached Windows-like
boot, pinned ISO/tools, private digest/signature, read-only auth mount and cleanup
passed. The protected-second review screenshot was inspected: only vda is the
install target, with its new EFI/boot/root partitions. Every inherited probe
predicate remains true; live KDE/KWrite remains `laptop-followability-only`.

- Original artifact ZIP `artifacts/13f-probe-4-two-disk-evidence.zip`:
  **6,433,195 bytes**, artifact12595945856, SHA-256
  `5fae2f56010006f5950a97d5fa35f138faf686274fa0dd7292383d2eabf8136b`.
- Original log ZIP SHA-256
  `449152f1fccc885507a95a6a3ddf7575ac0923349b2f4609d1bc6a38713eb63b`.
- Credential-pattern scan: 352 artifact text members plus job logs passed before
  persistence. Artifact digest and safe member paths verified.
- Independent replay passed **6 protected captures, 8 zero-write/unmap counters,
  6 BootNext checks,4 NVRAM transitions**. Protected SHA-256
  `995af842f3f78a779dec212169dccf86823d4c8a0c8f39c6d4043d399fd6441b`.

**Qualification evidence:** original artifact
`artifacts/13f-qualification-3-two-disk-evidence.zip`, **9,965,361 bytes**,
artifact12596724884, SHA-256
`262f259b105b8b0fe940925f72e3e62cb65bcbf715d0956a09c9052c541adc4f`.
Original log ZIP SHA-256
`4d0f2028e11fef69e69e1a0f4293204518d45c396a4dd1f40d71fde4076d24bf`.
Credential-pattern scan passed **616 text members plus logs**, and the original
ZIP digest and member paths were checked before persistence. Expanded raw
rpm-ostree/bootc/BLS/keyboard/physical records, logs and the observation index are
in [qualification-3](../../os/manifest/ci/13/qualification-3/observed-summary.json).
The original ZIP preserves unnormalized bytes.

| Actual stage | Layout/map and physical result | Other required result |
| --- | --- | --- |
| Installer and first stock | Installer chose de; diagnostic retained before repair; raw rpm-ostree and bootc exported before deciding | Protected-second real install; one authorized hardware-setup reboot; same-checksum serial1 booted +serial0 old |
| Actual installer de, injected de, injected us | All three repairs passed; complete ordered identity lists equal before/after | Only booted arguments repaired; old serial0 arguments unchanged; only serial1 pin flag changed |
| Corrected stock | No booted keymap override;21=+z,44=+y; physical tty3 login, password sudo and `yz-/!` at UID1000 passed | Homebrew owner check; Windows-first restored after pause/pin; unattended and detached Windows-like markers; signed verify/switch succeeded |
| AresOS de | No override in booted command line or either final BLS entry; German loaded map; tty3 UID1000 and foot UID1001 both read `yz-/!` | Exact new release booted; final pair asserted; policy/Homebrew passed |
| AresOS us | No override;21=+y,44=+z; tty3/password sudo/public text and foot all passed with US physical positions | Actual compositor XKB layout us; policy/Homebrew passed |
| AresOS back to de | German rows and all tty3/foot checks passed again | Compositor de; policy/Homebrew; rollback transaction and queued pair checked before reboot |
| Rollback corrected stock | Same saved checksum/serial1/pin; no override in command line or final pair; German tty3 login/password sudo/public text passed | Same inherited Homebrew bytes, actual stock session and rendered greeter, final unattended/detached Windows-like markers |

All five Homebrew observations retained the same SHA-256
`c9a27029eb72dab04f4595041f7670bb03b4cb467297abba817883afb23e0bf3`.
The daily denial/owner-working check passed on AresOS. Actual labwc environments
were **de,us,de**, model pc105, empty variant/options. Physical result records
include the layout-dependent QMP positions, exact public text and UID; root
only observed the results. Neither tty3 nor foot text was substituted through
serial. Both starting-state repairs and every complete final list were replayed.

Screenshots inspected: all five `13f-qualification-3-*-tty3.png`, all three
`*-foot.png`, and `rollback-greeter.png`. The three foot PNGs are byte-identical
1280×800 frames, as expected when each correctly maps different physical keys
to the same public text; the environment/map/QMP records distinguish layouts.
The real rollback greeter frame passed readiness plus pixel metrics:
nonblack 0.833875, bright 0.044875, spread 46.26684. The screenshot visibly shows
the drawn stock greeter, not an empty framebuffer. No fresh Part B/GRUB-menu
interaction is claimed.

**Fixture observation, not hidden:** the tty login banner consumed initial
characters of the preliminary `sudo -k` line (`udo -k`, and `do -k` on one
boot); its exit status is not asserted. AresOS's inherited profile also printed
the existing flatpak permission denial. Each following `sudo touch` command
visibly prompted for a password, accepted the physically typed layout-sensitive
password, and passed the root-owned marker check. All public readbacks and
logout/getty/no-UID1000-process checks passed. Thus the required real password
sudo and public-text assertions were exercised; this is not evidence that every
preliminary setup line arrived cleanly. The coverage test proves supported
characters, not login-prompt synchronization. No harness change or retry was
made after the source head was fixed. A future fixture improvement can wait
for a real ready shell before typing that redundant cache-clear line.

**All safety replays passed:** **13 protected captures,14 zero-write/unmap
counters,13 BootNext checks,12 NVRAM transitions**; protected SHA-256
`cc13e0c68c85ebfab98f8dd14e8bd19474e1f56b216207cb45ddf7f606064cc2`.
The full protected image/GPT/FAT/ESP comparisons match throughout; protected
write and unmap bytes/operations are zero. Windows remains the saved firmware
default after the first-login pause/pin. BootNext authorizations are checked
before each one-time Linux boot and consumed afterward. Private package reads
used GITHUB_TOKEN, no owner token; immutable digest/signature checks and
outside-workspace auth cleanup passed in both jobs. No audit was loosened.

### Actual entries and the F12 JUDGMENT-CALL

The full saved stock identity is checksum
`aa669eff4ea5c1f97c6c816c8d5d2abb5314e9afa3b966c0100e3e65f8040c71`,
serial1, stateroot `default`, pinned. The new AresOS identity is checksum
`42e5aea14cb87080fb9a96990b56968578a4a10a79c453c51630c01676d8017c`,
serial0, same stateroot, unpinned. They are distinct from the shared kernel/boot
checksum and from BLS file/version numbers.

| Real exported state | Ordered rpm-ostree identities | Corrected stock BLS title/version | AresOS BLS title/version |
| --- | --- | --- | --- |
| After pin | stock.1 booted/pinned; old stock.0 unpinned | Bazzite (ostree:0)/2 | absent |
| After switch staged | AresOS.0 staged; stock.1 booted/pinned; old stock.0 | Bazzite (ostree:0)/2; old stock remains Bazzite (ostree:1)/1 | staged, not yet a BLS entry |
| Each AresOS boot | AresOS.0 booted; stock.1 pinned; old stock.0 absent | **Bazzite (ostree:1)/1** | **Bazzite (ostree:0)/2** |
| Rollback queued | stock.1 pinned first; AresOS.0 still booted second | Bazzite (ostree:0)/2 | Bazzite (ostree:1)/1 |
| Rollback boot | stock.1 booted/pinned;AresOS.0 unpinned | **Bazzite (ostree:0)/2** | **Bazzite (ostree:1)/1** |

The exact labels include a space: **`Bazzite (ostree:0)`** and
**`Bazzite (ostree:1)`**, even for the AresOS image. INSTALL and EMERGENCY now
name both real labels and their reversal, while retaining checksum-resolved
identity and saved-title checks. No menu-position selector or owner script was
changed. Finalization naturally removed the older unpinned stock serial; no
manual deletion occurred. Its override never survives into the final pair.

**Decision: retain the conditional 13e F12→Windows step until the owner's own
successful AresOS boot confirms the pair/title.** The actual staged snapshot
still contains both stock serials, while the first AresOS snapshot contains only
the correct pair. The successful VM establishes the normal transition, not
every interrupted first-switch failure window. After the pair is confirmed,
the recorded corrected-stock title and identity guide recovery. Removing this
caution would encourage guessing between same-checksum stock entries before
finalization; no evidence supports that. This is a guide decision for owner
review, with no change to the qualified scripts or selectors.

### Diagnostic only, budget closure and remaining gates

The retained localization observer recorded 980 messages. Last values were
Language `en_US.UTF-8`, XLayouts `[de]`, VirtualConsoleKeymap `de`, empty layout
options. The last console-keymap Get used client `:1.7`, cookie 9074, request
1792925811252278/reply1792925811269359 microseconds. No separate client-to-process
PID mapping was exported. This is credential-safe diagnostic evidence and does
not explain historical us values; it is not an acceptance gate.

| Actual package ledger before closing push | Minutes |
| --- | ---: |
| Closed 13e history | 267 |
| Owner 13f brief privacy | 4 |
| 13f source push/PR privacy | 4 |
| Fresh probe | 26 |
| One complete qualification | 69 |
| **Completed subtotal** | **370  / 460** |
| Closing privacy reservation | 12 |
| **Conservative total before closing** | **382  / 460** |

Fresh closing reservation proof has **44 unique IDs /total_count 44**, complete
one-page history, no active job, dispatch totals images 2/3, publish 1/1,
checks 1/1, probes 4/4, qualifications 3/3. A further qualification or probe is
not authorized. The read-only org summary after qualification reports
**1,360 used /2,000**,640 free; reserving 12 leaves 628, above 150. Final actual
closing privacy minutes, log hashes and zero-reserve ledger are recorded in
PR #12's body after this closing commit, avoiding a self-referential report
push. No final cost is invented in this pre-push report.

Final local guide checks: the exact system-keyboard block and exact switch
block each still equal their scripts, **2 tests /0.168s, OK**. `git diff --check`
passed. `git diff --exit-code 1a95433 -- os/ci os/tests os/release` and the full
frozen-runtime comparison against 2abc12e both returned 0. Release manifests
preserve every previous attempt and record this passing qualification; the
private digest, signature identity, source commit and image-diff proof are
unchanged. The duplicate identical source-hash row was deduplicated only as
metadata after the run.

**Not verified / open gates:** physical media/laptop hardware, real Windows
and firmware interaction, manual GRUB, live KDE settings/KWrite and laptop
followability remain open; physical installation is **NOT RELEASED**. The
live automation code remains unused. Owner review of 13c's exact-frozen-image
construction and this guide JUDGMENT-CALL is still required before merge.
The preliminary tty cache-clear timing observation above is recorded for
future fixture work; no clean-command assertion is claimed. No product change
or extra run was made to address it. VM acceptance in 13f was reached in full;
PR readiness additionally requires the closing privacy check. Never merge.

## 13g — review fixes for recovery steps (2026-10-25)

### Done

Fetched and pulled `--ff-only` first; the branch was already up to date at
`25475975ceda68afbed6c49dcb3fdc956dd0c321`. Read the owner review of `1c4a249`
and brief 13g. This follow-up changes only INSTALL, EMERGENCY, INSTALL-RECORD
and this REPORT. The retired worktree was not accessed.

- **INSTALL:** documents the approved recovery-layout exception and the full
  `ares-recovery` login → command → reboot → F12 → recorded Linux entry sequence
  for layout changes, switch, rollback, stock-default promotion and subsequent
  hardware/recovery checks. Windows stays the firmware default after §5; the
  initial installer/hardware-setup Linux-default phase is unchanged. Daily
  `ares` cannot run the maintenance commands. Current AresOS layout is used for
  its administrator login; installer layout is used after booting backup stock.
- **INSTALL's title checkpoint:** reads rpm-ostree/bootc status and actual BLS
  title/options, resolves each `ostree=` target with readlink, and matches stock's
  complete saved checksum, serial and stateroot. Requires exactly one matching
  BLS target and records its exact title/state/time. Repeat after every reorder
  before reboot, including pending-update cleanup, staged switch, queued
  rollback and set-default, then confirm again after boot. Neither staged JSON
  row counts nor BLS filenames identify menu rows. The first-switch staged
  record remains provisional because shutdown finalization can change it again.
  A failed first switch boot still requires **F12 → Windows and help**.
- **EMERGENCY / INSTALL-RECORD:** any reorder immediately invalidates old titles,
  even when familiar labels remain visible. A stale/missing record requires
  Windows/help. The blank private record now captures stock checksum/serial/
  stateroot, installer layout and title history with invalidation checkpoints.
  No actual machine identifiers or credentials were collected into this form.
- **Release gate:** records the owner's 2026-10-25 decision and distinguishes
  source verification from historical VM coverage. Physical installation and
  novice/laptop followability remain **NOT RELEASED**.

### Verified

Commands ran locally, without elevation, real boot/disk queries or execution of
the guide's maintenance commands:

| Command / check | Actual result |
| --- | --- |
| `wsl bash .work/13/13d-closing-checks.sh` | `test_system_keyboard.SystemKeyboardTest.test_owner_block_equals_script` and `test_grub_bls.GrubSelectionTest.test_owner_switch_block_is_exact_release_script`: **2 tests in 0.040s, OK**. Both owner blocks remain exactly equal to their scripts. |
| `python -X utf8 .work/13/13g-verify.py` | All five retained BLS/whole-identity checks passed; confirmed historical `de, us, de` sequence before rollback. Exported 18 guide Bash blocks for syntax checking only. |
| `wsl bash .work/13/13g-guide-syntax.sh` | `GUIDE_BASH_SYNTAX_PASSED_NO_COMMAND_EXECUTED`; all 18 blocks passed `bash -n`. |
| `git diff --check` | Exit 0; no whitespace errors. |
| `git diff --exit-code 1c4a2495b503b9342af06360f0bfd18a5366fa2d -- os/ci os/tests os/release os/Containerfile.keyboard os/.containerignore os/packages.lock.json os/config os/policy os/manifest/base.json os/keys` | Exit 0; harness, tests, owner scripts and runtime paths unchanged from the reviewed head. |
| `git diff --exit-code 2abc12e8aa6089f7576143d1fbccb6648a3291bd -- os/Containerfile.keyboard os/.containerignore os/packages.lock.json os/config os/policy os/manifest/base.json os/keys os/tests/audit.py` | Exit 0; frozen runtime paths and audit still match the published image source. Earlier 13d–13f harness/test changes are retained; this guide follow-up changes none. |
| `git diff --name-only` | Exactly the four documentation files listed above. |

The read-only title procedure was checked against the actual retained
[13f deployment/BLS exports](../../os/manifest/ci/13/qualification-3/evidence/two-disk/).
The same pinned corrected stock checksum/serial1/stateroot was selected in every
snapshot; the untouched old stock serial0 was not mistaken for it:

| Snapshot | Corrected stock's actual title |
| --- | --- |
| After pin | `Bazzite (ostree:0)` |
| Switch staged, before shutdown finalization | `Bazzite (ostree:0)` — provisional |
| Successful AresOS boot, final pair | `Bazzite (ostree:1)` |
| Rollback queued, **before reboot** | `Bazzite (ostree:0)` |
| Stock booted after rollback | `Bazzite (ostree:0)` |

The staged rpm-ostree JSON includes the new image before it has a BLS entry;
this is why the guide resolves actual BLS targets instead of deriving a title
from JSON position. These are retained-evidence checks, not a new VM execution
or a physical readlink test. Root commands in the guide were syntax-checked,
never run against the owner's system.

The [bootc filesystem documentation](https://bootc.dev/bootc/bootc-filesystem.7.html#etc)
describes deployment-specific `/etc` and staged finalization. Together with the
retained pinned sources and historical layout sequence, this supports the
recovery-layout exception. A later localectl setting in AresOS does not update
the retained stock deployment's earlier configuration.

### JUDGMENT-CALL — owner-approved recovery layout and title validity

**Owner decision in brief 13g, 2026-10-25:** backup Bazzite keeps the installer
layout (German for this laptop), matching the frozen-backup decision. Later
AresOS layout changes apply to AresOS; recovery passwords must be typed using
the installer layout. No mechanism writes later settings into stock. This
narrows the earlier “one setting everywhere” requirement. Propagating layout
changes into the retained deployment was rejected by the owner; changing that
decision later would require a separately authorized mechanism and new runtime
qualification, rather than a guide edit.

Keep the existing failed-first-switch F12 → Windows rule. A staged switch can
still contain both stock serials, and its current BLS title can change during
finalization. Recording that provisional title does not authorize using it for
recovery. Once the first successful AresOS boot confirms the final pair, the
latest checksum/serial-resolved title is usable only until the next reorder.

### Not verified / PLAN-GAP / open questions

**A run leaving AresOS on US and then rolling back was not performed.** 13f
restored German before rollback. Installer-layout recovery after a later US
change is source-verified, not runtime-verified. This limitation is now explicit
in INSTALL, EMERGENCY, the release gate and this report; it is not claimed as
new VM coverage. The owner-approved exception resolves the review's requirement
gap without changing or writing into stock.

No new VM, image build/publication, native/full suite or Actions dispatch was
run for this guide-only brief. The two exact-block tests above are the requested
local regressions. No Gradle build/client test ran because mod/product code is
unchanged; no Gradle daemon was started. Historical 13f acceptance remains the
qualification evidence. Physical media, laptop keyboard/firmware/GRUB and live
KDE/KWrite/unaided followability remain open release gates. Owner review before
merge remains required; PR #12 stays ready. No merge or visibility change.

### Package ledger and closing privacy

Read-only `python -X utf8 .work/13/13d-ledger.py 8` returned complete history:
**50 unique IDs / total_count 50**, one page, no active job. Completed package
cost is **384 / 460 minutes** (the previous 374 plus 10 for the owner's 13g brief
and review privacy jobs). Reserving **8** for this closing push/PR privacy gives
**392 / 460**. Existing dispatch totals stay images 2/3, publish 1/1, checks 1/1,
probes 4/4 and qualifications 3/3; no further dispatch is authorized or needed.

Only the normal push/pull-request privacy workflows may run on this closing
head. Their actual job minutes, all three executed checks, log hashes and final
zero-reserve ledger will be recorded in PR #12's body after the push, avoiding
a report-only push loop. This pre-push report does not invent their results.
No tokens were printed or stored; no harness, owner-script, frozen runtime,
image, VM, protected-disk or audit change was made.
