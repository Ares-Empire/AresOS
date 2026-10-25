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
