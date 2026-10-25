Reviewed commit `6eb2d0b`. **One safety gap; no files edited.**

1. **SHOULD-FIX — Undo leaves the private-pull token active on the SSD.**  
   Locations: [INSTALL.md:970](../../../docs/INSTALL.md:970), [INSTALL.md:975](../../../docs/INSTALL.md:975), credential creation at [INSTALL.md:652](../../../docs/INSTALL.md:652).

   **Scenario:** The owner authenticates the private pull, later abandons AresOS, and follows removal or partition-table clearing. Neither branch instructs them to revoke the token. The unencrypted SSD can retain credentials in both deployments’ `/etc`; changing its partition table does not securely erase them.

   **Impact:** Someone obtaining the removed or reused SSD can recover a still-valid token and download private packages accessible through its scope. Mode `0600` does not protect against offline access. GitHub confirms that `read:packages` permits downloading images and reading metadata. [GitHub registry documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

   **Fix:** Add an explicit credential-retirement checkpoint when abandoning the trial, and before removal or reuse: revoke the dedicated installation token from Windows or the phone and record completion without recording the secret. Local credential deletion is cleanup, not a substitute for revocation; retained deployments may contain another copy.

   **Check:** Using disposable credentials, authenticate, switch, and exercise each undo branch. Confirm the retired token can no longer authenticate, while existing stock and AresOS deployments remain bootable offline. The novice walkthrough must include this checkpoint.

The evidence labels appropriately distinguish VM results, source reasoning and outstanding physical checks, including the untested US-to-stock rollback case. The three principal owner scripts match the guide and pass Bash syntax checks. I found no additional literal wrong-disk write path in the reviewed commands.

For proportionality, retain the disk/EFI identity checks, recovery credentials and Windows-return checks. A verified helper bundle with short invocations could replace the hundreds of lines of owner-entered source; CI chronology belongs in reports, with concise evidence links in the guide.

I independently checked Lenovo’s [slot specification](https://psref.lenovo.com/syspool/Sys/PDF/LOQ/LOQ_15IRH8/LOQ_15IRH8_Spec.pdf), [firmware boot selection](https://download.lenovo.com/pccbbs/pubs/loq_15_16/html_en/EN/select_boot_devices.html), and Bazzite’s [installer](https://docs.bazzite.gg/General/Installation_Guide/install-guide/) and [GRUB recovery](https://docs.bazzite.gg/Installing_and_Managing_Software/Updates_Rollbacks_and_Rebasing/rolling_back_system_updates/) guidance. Lenovo’s official HMM PDF could not be retrieved, so I do **not** claim independent verification of its connector drawings. No hardware or VM trials were run.

**GAPS-FOUND (1)**