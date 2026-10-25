# 13b: A new release for the session layout, and a keymap fix that doesn't depend on the installer

Follow-up on branch `pkg/13-keyboard-layout` (PR #12, draft). Read the 13 REPORT. Brief 13 still applies, plus the changes below.

## Where 13 stopped

The zero-cost check found the writer of the kernel argument: Anaconda 44.30's `ConfigureBootloader._set_kargs()`, from the localization module's console keymap. But the value differed between our runs: 11k wrote `de`, 11n wrote `us`. The retained evidence can't show why. Stopping was correct, because brief 13 asked for that explanation first.

## Integrator decisions

1. **The cause is not a gate any more.** Treat whatever the installer writes as untrusted, since both values have been seen. The fix must give the right result after an install that wrote `de`, `us`, another value or none. Still record the localization module's values at the argument-writing boundary in the VM run, credential-safe, as a diagnostic. If that shows the cause, report it, but don't gate on it.
2. **The kernel argument fix.** Use brief 13's rules: the normal system setting decides, there's no conflicting `vconsole.keymap` on any entry the owner can boot, and the identity checks stay intact.
   - Verify `ostree admin instutil set-kargs` / `deployment_set_kargs` on the pinned versions before relying on it. It looks like it changes a deployment's arguments without adding a deployment with the same checksum.
   - If the fix is an owner step, it's one script in `os/release/`, with the INSTALL block equal to it (like `switch.sh`), run before the pin so the backup inherits it.
   - Test it against both starting states, `de` and `us`, with an injected `us` if the real install happens to write `de`.
3. **New release (owner OK, 2026-10-25).** The session fix changes the image, so build and publish a new **private** release.
   - **Where:** from this org repo to `ghcr.io/ares-empire/aresos`, keyless-signed by this repo's workflow. The owner already accepted the public Sigstore record for signing; it now names the org repo.
   - **Same base:** the same pinned base digest (`ed93d215…`) and locked packages. The only intended image change is the keyboard layout. Diff the new image against the current release (packages, files, units) and report every other difference. An unexplained one stops the release.
   - **Owner-facing updates:** the new release reference in `switch.sh`/INSTALL, the signature identity check, the frozen-release verifier and the release manifest. Keep the old release's records as history and delete nothing from GHCR.
   - **Token:** check whether CI can read the org package with the job token. If so, rehearsal jobs stop needing `GHCR_READ_TOKEN`. Report it and keep the secret until the owner removes it. The laptop install still uses the owner's own read token.
   - **Session fix:** the session reads the system's X11 layout, variant and options and gives them to labwc, never a hardcoded layout. Test it with at least `de` and one other layout.
4. **Qualification.** Run brief 13's plan on the new release, in protected-second order:
   - install with the §4 keyboard steps, then the first stock boot
   - the fix, then pause/pin
   - the signed switch to the **new** release
   - on AresOS: tty3 login and sudo with a layout-sensitive password, physical-key typing in foot, and `/proc/cmdline`
   - the layout change and back
   - rollback to the backup, checked the same way

   All of package 11's audits apply at every stage. The new image must also pass the existing image checks: policy, inherited Homebrew, power events, the recovery login, and a rendered greeter after rollback.
5. **Budget.** Package 13 ledger (starts at the first dispatch).
   - Cap: **380 minutes**.
   - Allowed runs: one image build/publish, one checks-only native suite, one probe and two qualification runs.
   - The org had about 1,000 of its 2,000 October minutes left on 2026-10-25, resetting 1 Nov.
   - If the guard can't fit a run, stop and report.

## Acceptance

Brief 13's acceptance, plus:
- the new release's digest, signature and identity proof
- the image diff against the current release
- the diagnostic values
- both starting states fixed
- every stage's typing and cmdline evidence
- the budget table

Push (fast-forward only). Mark PR #12 ready for review if acceptance is met. Don't merge. Never make anything public.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
