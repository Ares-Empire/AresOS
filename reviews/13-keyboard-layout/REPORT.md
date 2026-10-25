# 13: keyboard layout — 13d installed-system qualification

**Current status: 13d preparation; PR #12 stays draft pending acceptance.** The privileged-tool path fix,
private release/signature/two-file image comparison and 217 native tests passed.
The 13c probe failed at live KDE German-layout selection; no installation or
qualification was performed then. Brief 13d now moves that live-desktop step to
the laptop gate and authorizes one fresh probe, then installed-system qualification.
See the final 13d section for current results.
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
