# 14zzc: Package review fixes: trusted bootstrap, abandoned layout trials, resumable setup, persistent diagnostics, status lines; probe 32, qualification 21

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zzb still apply, with the changes below.

## Integrator decisions on `reviews/14-owner-tools/REVIEW.md` (CHANGES-NEEDED at `f13ac8e`)

All five findings are accepted. Fix them, then re-qualify, because the owner tools change.

### 1. Blocking: verify before executing anything from the stick

The first bootstrap command must run **no code from the stick** until every payload file is verified using system tools only.

- **Copy first.** Copy the read-only-mounted `ares-tools` into a fresh root-only private directory, such as `mktemp -d` under `/run`. This also closes the check-then-use gap.
- **Check the manifest:** its SHA-256 against the full documented fingerprint, written literally into the command the owner types.
- **Check the payload:** every payload file against the manifest with `sha256sum -c --strict`. Unlisted files and missing files are refusals.
- **Only then** run `at install` from the private copy. Keep `checked_bundle()` as a second layer.
- **Typing:** the command is still typed once, exactly as the guide shows it. Keep it as short as it can be while staying correct, and make it one copyable block. If a manifest format change is needed for `sha256sum -c`, make it, and update the Windows copy helper and the fingerprint everywhere.
- **Test the real bootstrap command** with a modified `at`, a modified `owner.py`, an extra file and a missing file. Each must give zero payload execution, which a marker file proves, and a clear refusal.

### 2. Blocking: an abandoned layout trial must never lock the owner out

- **Rule:** a layout trial that isn't finished is never the login layout of the next boot. After any unplanned reboot during a trial (crash, power loss, reset), every console and the greeter use the **last finished layout**.
  - If `layout begin` currently persists the trial layout into boot configuration, change that, so only `layout finish` persists it.
  - If it can't be done that way, add a fail-safe that restores the finished layout before any login prompt. Explain which one you chose.
- **Add `layout abandon`.** It runs from a fresh, authenticated, physical administrator session (the same session checks as other actions) on any boot, including retained stock. It restores the previous layout, clears `layout-pending.json`, and records it. After that, guarded reboot and keep-stock work again.
  - **On retained stock,** it must not change stock's keyboard settings beyond restoring the finished layout.
  - Add it to the guide and the emergency card in one line each, with its exact first result line.
- **Tests:**
  - **Local:** session loss, a closed original login, and stock-side recovery.
  - **In qualification:** during a pending `us` trial, reset the VM with QMP `system_reset`. Then prove the next boot's consoles use German, that the owner's German-typed password logs in, and that `layout abandon` passes, followed by a guarded reboot.

### 3. Should-fix: resumable setup

- **`install`:** stage into a private directory, then publish it atomically. A partial earlier attempt is detected exactly and either resumed or cleaned, never silently accepted.
- **`prepare`:** journal its intent before the first mutation. A re-run resumes only an exactly matching interrupted operation; any other state STOPs.
- **Tests:** inject a failure after each mutation and after each record write.

### 4. Should-fix: diagnostics survive to the owner's export

- Persist STOP diagnostics root-only under `/var/lib/ares`.
- Include them in `export` through the same checked route as the records.
- **Test:** a failure, then export, then a reboot. The failure record must exist on the stick afterwards.

### 5. Should-fix: status lines

- Update INSTALL.md (around 492) and EMERGENCY.md (around 9) to the completed VM qualification scope, with the qualification that actually passes in this round.
- Keep **NOT RELEASED** and every outstanding physical gate.

### Round

- **Locally:**
  - all affected regressions
  - the full stand-in walk, which must include the new bootstrap, the abandoned-trial reset and `layout abandon`
  - the pinned gitleaks
- **Then:** one push through the privacy hook, then **probe 32 and qualification 21 on that same head**, then STOP and report as in 14zzb.
- **Caps:** these are the last allowances (32/21). The minute cap 2750 fits: 2301 + 72 + 220 = 2593. If the new reset stage pushes the qualification projection past the 180-minute VM step, size it from real timings with 25% margin, up to a VM step of 200 and a bound of 240, and say so.
- **Afterwards:** the reviewer re-checks only these fixes and what they touched.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
