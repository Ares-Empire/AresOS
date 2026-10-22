# 06d: Fix the PR #10 review findings

Follow-up on branch `pkg/06-image-release` (PR #10). Read `reviews/06-image-release/REVIEW.md` (the package review of `ef07dbc`, CHANGES-NEEDED) and the 06c section of `reviews/06-image-release/REPORT.md`.

**Claude's integrator decision:** fix all six review findings on this branch before merge. The physical install stays gated; this package only makes the tested recipe and its checks trustworthy.

## Findings and pre-decided handling

1. **Reboot blocks skip their checkpoint** (`docs/INSTALL.md` §6, switch and rollback blocks). Split each into: the transaction (stopping on failure), then the status check the owner must read, then the reboot as its own separate step. Say plainly: if the transaction prints an error, stop and don't reboot. The CI switch path must exercise the same order: the transaction, then an inspection of the staged/rollback identity, then the reboot.
2. **GRUB recovery doesn't make stock the persistent default** (§6). Document an identity-checked step that makes the recovered stock deployment the default after booting it from the GRUB menu. Then document a second reboot that confirms stock stays selected. Cover the case where the owner is already booted into stock. Check the exact semantics against bootc/ostree docs or source, not memory. Qualify it in CI with the most faithful automated equivalent you can build within the run budget (for example, booting the previous deployment once, then making it default and rebooting with no selection). If you can't qualify it faithfully, the guide must mark this step as **untested** and list it in the open release gates. Never claim it as tested.
3. **`!`-negated commands are exempt from `set -e`**, so negative checks never failed (`os/release/switch.sh`, `os/ci/switch_vm.py` guest snippets, `os/tests/guest.sh` and any other script). Audit **every** Bash script and embedded shell snippet under `os/`, including the ones merged in PR #3, for checks written as `! cmd` (and similar, e.g. `cmd && false`) that rely on `set -e`. Rewrite each one as an explicit `if ...; then echo <reason>; exit 1; fi`. Add:
   - regressions that inject each prohibited condition (for example, an `ares` account at another UID with 1001 free, a running competing desktop process) and require a non-zero exit
   - a static regression that fails if a `set -e` script or snippet uses a bare `!` command as an assertion

   List every rewritten check in the report. If a corrected check now **fails** on evidence from earlier runs, that is a product failure: stop and report.
4. **Rollback graphical evidence is missing** (`os/ci/switch_vm.py`, rollback stage). Before capturing, wait (bounded) for real graphical readiness of the stock greeter, then capture a framebuffer that shows it, inspect it visually and keep it. An active display-manager service alone doesn't count. Brief 06's "screenshots of both states" acceptance needs this.
5. **The administrator stays logged in after maintenance** (§6). Tell the owner to exit any root shell, log out of `ares-recovery`, confirm the tty3 login prompt is back, and only then press Ctrl+Alt+F1.
6. **Stale docs**: `docs/design/OS-BASE.md` (around line 140, "untested") and `os/README.md` (around line 77, "never reached tty3"). Update both to the 06c/06d results, keeping the separate physical-install gates open.

A harness flaw gets fixed with a regression. Any other product failure means stop and report.

## Constraints

- **No mod changes, and no Gradle or Minecraft client tests in this package.** The owner is using the laptop to play Minecraft and memory is short. Starting test clients would steal their game's focus. If a fix seems to need a mod change, stop and report.
- Prefer not to change the image payload. If the audit in finding 3 touches a script that ships in the image, rebuild and publish **once**, then update the digest everywhere it appears (§6, `os/manifest/release.json`, `os/README.md`).
- **Budget:** at most **2 full CI runs**, plus checks-only runs as needed. About 1,230 of 2,000 monthly minutes are used.
- No physical installation, no owner token, and no change to repo or package visibility.

## Acceptance

- All six findings are closed, each with a regression where code changed.
- A green full run: switch, policy, tty3 recovery, partition equality, rollback with a **rendered stock greeter screenshot**, and the persistent-default step (qualified, or marked untested as above).
- A "06d" section in `REPORT.md` with a findings → fix → evidence table.
- Push the branch and keep the PR open. Do not merge.

**Model:** gpt-6.1-sol, xhigh.
