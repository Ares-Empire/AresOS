# 06: Release the AresOS image and a tested Bazzite → AresOS switch

**Goal:** deliver the image part of the install guide's maintainer release gate (`docs/INSTALL.md` → "Maintainer release gate", first bullet). Afterwards, a freshly installed Bazzite on the laptop can be switched to AresOS with a tested, documented recipe, and switched back.

**Decisions since this brief was first written (2026-10-22):**
- The image stays **private** (owner decision); no public option needed.
- AresOS installs onto its **own SSD**: see the current `docs/INSTALL.md` §5–§7, where §6 is the NOT RELEASED placeholder to fill in.
- The 03 image is merged (PR #3): `os/` with the static strict updater audit, the Cockpit mask, two-VM CI and offline logind proof. Keep all of it green.

**Read first:**
- `docs/design/OS-BASE.md` §8 and A1/A2
- `docs/INSTALL.md` §5–§7 and the release gate
- the `os/` code and `reviews/03-os-image/REPORT.md` (merged from PR #3)

**In scope:**
1. **Right base for the RTX 4060.** Switch the base from `bazzite-nvidia` to **`bazzite-nvidia-open`** (KDE, no Steam Gaming Mode), pinned by digest with verified signature. Re-run all package-03 checks.
2. **Publish the image** to the GitHub container registry under `carlsenares`, **private** by default.
   - Before pushing, confirm against GitHub's current billing docs that private container storage is still free. If it isn't, stop and report.
   - Tag immutably and record the digest.
   - Sign it if that needs no long-lived secret. Otherwise record why not and rely on digest pinning.
   - Document how the laptop pulls a private image: a fine-grained read-only token and where it's stored on the laptop, never in Git.
   - Also describe in a few lines what changes if the owner makes the image public instead. That's an owner decision, so don't do it.
3. **Exact installer ISO.** Name the official Bazzite legacy ISO for `bazzite-nvidia-open` KDE, with its SHA-256 from Bazzite's official source.
4. **Tested switch recipe, in a CI VM:**
   - Boot a stand-in for a freshly installed stock `bazzite-nvidia-open` (a VM disk built from the upstream image).
   - Run the exact rebase commands to the published AresOS digest and reboot.
   - Assert: our labwc session comes up for the `ares` user, the updaters stay masked, and no partition changed.
   - Then roll back to the previous deployment and assert stock Bazzite boots.
   - Screenshots of both states.
5. **Accounts.** Define the recipe:
   - a password-protected recovery administrator, created in the Bazzite installer, with exact username and UID guidance
   - the locked, auto-login daily `ares` user that comes with our image
   - how the owner gets admin rights for maintenance

   The CI test must cover the recovery admin logging in on a TTY.
6. **Update `docs/INSTALL.md` §6:** replace the NOT RELEASED placeholder with the tested recipe (digest, commands, rollback, account steps). Keep every other release-gate item marked as still open.

**Out of scope:**
- Physical media and the laptop.
- The installer VM walkthrough and Windows/UEFI helper trials (separate package).
- Minecraft, Prism and the mod.

**Constraints:**
- Free GitHub quotas only. Budget: at most 6 full CI runs or about 400 minutes (about 750 of 2,000 monthly minutes are already used). Use checks-only runs before full runs. Never enable paid features or change billing.
- No secrets in Git or logs. If a token is needed for CI publishing, use the built-in `GITHUB_TOKEN`.
- Nothing runs on the owner's laptop except git and gh.

**Acceptance:**
- CI is green.
- The image is published, with its digest recorded in `os/manifest/`.
- The switch and rollback test passes with screenshots.
- `docs/INSTALL.md` §6 is filled in.
- `reviews/06-image-release/REPORT.md` has measured numbers, judgment calls and what's still open in the release gate.

**If unsure:** keep the image private, change the least of Bazzite's boot, kernel and driver stack, and never touch partitions.

**Model:** gpt-6.1-sol, xhigh.
