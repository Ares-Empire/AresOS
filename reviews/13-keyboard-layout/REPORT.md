# 13: keyboard layout — stopped at the zero-cost prerequisite

**STOP / PLAN-GAP. No implementation or VM qualification is claimed.** The
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
