# Later owner procedures

These are separate from initial installation. Use the [current gate/status table](INSTALL-STATUS.md#current-gates); no physical action is released by this page. Keep the private record and the step number you came from. Any missing check → **STOP → [Help](INSTALL-REFERENCE.md#help)**. Nothing here authorizes authentication/switching; that always returns through [step 5](INSTALL.md#5-prove-windows-and-corrected-stock).

## Later layout

Backup Bazzite keeps the installer’s **German** layout. AresOS's later settings affect only its own deployment, not stock. Record old and proven new profiles before invoking finish. **Begin and revert change only the running console map. Only finish persists the console/greeter setting.** A restart during begin/revert reloads the last confirmed layout. An interrupted finish may already have persisted the proven new console map; use [abandoned-trial recovery](#abandoned-layout-trial), not an assumed old map. Qualification 21 includes a reset during a pending begin trial; direct US-to-stock rollback remains outside the stated runtime scope (see status table). After an AresOS update (three deployments) a layout trial refuses before any change; get [Help](INSTALL-REFERENCE.md#help).

Use the [console entry/exit reference](INSTALL-REFERENCE.md#console). **Return to this procedure** after entry. Keep the original **tty3 ares-recovery → sudo -i** session **OPEN** throughout; do not reboot or change the password to bypass failed typing. The unchanged password, made only of lowercase a–x and top-row digits 0–9, stays typeable in German, US International and plain US. The public `yz-/!ü` proof exercises the layout difference. In AresOS, begin US International:

```bash
sudo /var/lib/ares/at layout begin us-intl
```

Require `PASS layout begin us-intl`. Go to **Ctrl+Alt+F4 (Ctrl = Strg)** or **Ctrl+Alt+Fn+F4 (Ctrl = Strg)** → expect **login:** → fresh `ares-recovery` password login in US International. No inherited login/sudo cache:

```bash
sudo -k; sudo /var/lib/ares/at layout proof
```

Enter the unchanged password for sudo; physically type `yz-/!ü` when prompted (**AltGr+y** for ü in US International). Require `PASS layout proof`. Exit tty4 entirely to **login:**; return **Ctrl+Alt+F3 (Ctrl = Strg)** or **Ctrl+Alt+Fn+F3 (Ctrl = Strg)** to original root session:

```bash
sudo /var/lib/ares/at layout finish
```

Require `PASS layout finish` and refreshed title. For returning to German repeat that exact second-console proof/finish sequence starting with:

```bash
sudo /var/lib/ares/at layout begin de
```

Require `PASS layout begin de`, then complete that proof/finish sequence.

The plain-US failure/revert trial uses the same session precautions, beginning with:

```bash
sudo /var/lib/ares/at layout begin us
```

Require `PASS layout begin us` before the second-console trial. Do this deliberate failure only in the supervised layout gate: the unchanged password stays typeable, but plain US cannot type the ü in the public `yz-/!ü` proof. Keep the original tty3 root session open; on login/typing failure, use [Layout revert](#layout-revert) below. Reboot must refuse unfinished proof; never test refusal by forcing a restart.

### Layout revert

Any second login/typing error → return to original **open tty3 root session**, then:

```bash
sudo /var/lib/ares/at layout revert
```

Require `PASS layout revert` and the old running console map restored; the saved console/greeter setting has stayed unchanged. If begin fails and reports the old map restored, use this same revert/proof route; retain the first session. After `PASS layout revert`, continue to [fresh-login proof and finish](#layout-recovery-proof). Missing original session → [abandoned-trial recovery](#abandoned-layout-trial); failed restoration → **STOP → [Help](INSTALL-REFERENCE.md#help)**, no restart; password symptom is on the [card](EMERGENCY.md#password-not-accepted).

### Layout recovery proof

**On AresOS after `PASS layout revert`:** keep original tty3 root open. Log tty4 out completely; make a **fresh tty4 ares-recovery password login using the old layout**, then:

```bash
sudo -k; sudo /var/lib/ares/at layout proof
```

Enter the unchanged password for sudo and physically type `yz-/!ü` when prompted; require `PASS layout proof`. Log tty4 out to **login:**. Return to original tty3 root with **Ctrl+Alt+F3 (Ctrl = Strg)** or **Ctrl+Alt+Fn+F3 (Ctrl = Strg)**:

```bash
sudo /var/lib/ares/at layout finish
```

Require `PASS layout finish` and refreshed title. Only after both PASS results, [continue to layout completion](#layout-completion), then Return to step 8. Any failure → **STOP → [Help](INSTALL-REFERENCE.md#help)** with the original session retained; no restart, stock-proof detour or password change.

### Layout completion

After successful finish only:

```bash
sudo /var/lib/ares/at title
sudo /var/lib/ares/at reboot
```

Require `PASS title` and `PASS reboot` / `Reboot requested; Windows stays default; F12 then Linux for one Linux start` (screen may disappear); save title/state/time and invalidate earlier titles before the restart. Sticks absent → **F12** (or **Fn+F12**) → Linux → fresh recovery login using the completed layout → `sudo /var/lib/ares/at check` (expect `PASS check`), physical console/password sudo and foot typing. For the rollback trial restore German using the same fresh-second-login proof/finish sequence; then use `sudo /var/lib/ares/at title` (expect `PASS title`) and `sudo /var/lib/ares/at reboot` (expect `PASS reboot` / `Reboot requested; Windows stays default; F12 then Linux for one Linux start`) **before the rollback trial**. Keep stock German; never edit the frozen backup to follow AresOS. Export/unplug before restarting.

**Record:** old/new maps, both fresh password/text proofs, finish/revert result, title and post-boot check. **STOP → [Help](INSTALL-REFERENCE.md#help)**. **Return to step 8:** [everyday use](INSTALL.md#8-everyday-boot-and-recovery).

## Abandoned layout trial

**Already cleared:** if you recorded `PASS layout abandon`, go directly to [abandon completion](#abandon-completion), without another invocation. If you accidentally repeated it and received `Missing private layout-pending record`, that same route applies **only with the prior recorded PASS**. Every other refusal, or no evidence of that PASS, → **STOP → [Help](INSTALL-REFERENCE.md#help)**.

For a still-pending trial, identify the interrupted action and booted OS from your record:

- **Begin/revert interrupted by a restart:** try the **last confirmed layout once**; a failed login → Help. These actions did not persist the trial map.
- **Finish invoked, but no `PASS layout finish`:** the console may already use the recorded, proven new map. Try the last confirmed layout **once**. Only if that login fails, try the proven new layout **once**. Two failed logins → **STOP → [Help](INSTALL-REFERENCE.md#help)**, no third attempt.
- **Retained stock:** use its own installer German; never apply AresOS's new profile to stock.
- **Original session lost without restart:** the running console may still use the trial map. If its current map is uncertain, stop at Help instead of guessing.

This is a **two-failed-login total limit for the incident**, not per tty or restart. Any earlier failures before starting this route, unknown old/new profile, changed/unknown authentication policy or lockout warning → Help before attempting. [Lockout settings and counting precautions](INSTALL-REFERENCE.md#layout-recovery-login-limit). No forced restart, password change or counter-reset command.

Use the bounded route above for a **fresh physical tty3 ares-recovery password login**, following [TTY entry/exit](INSTALL-REFERENCE.md#console) only as far as the login prompt before choosing the map; **Return to this procedure** for the password attempt. Once that login succeeds, run `sudo -i` in that same session using the successful map. If sudo rejects the password, stop at Help without a retry. The old inherited administrator session cannot abandon its own trial. On either AresOS or retained stock, invoke once:

```bash
sudo /var/lib/ares/at layout abandon
```

Require `PASS layout abandon`, `Last finished console layout restored; abandoned trial cleared` and `Last finished persistent layout verified; stock settings preserved`. Save the refreshed title/state/time and invalidate old titles. This clears the shared pending trial after identity checks; stock retains its own confirmed setting.

### Abandon completion

Enter here after the recorded `PASS layout abandon`, including an already-cleared trial or an accidental repeat's `Missing private layout-pending record` **only after that PASS**. Do not invoke abandon again: the successful command deleted the pending record. No prior PASS or any other refusal → **STOP → [Help](INSTALL-REFERENCE.md#help)**; preserve the screen/session and [export diagnostics](EMERGENCY.md#a-tools-command-stopped), no guessed retry.

**Return by booted OS:** on **AresOS**, run `sudo /var/lib/ares/at check` (require `PASS check`), prove confirmed-layout password/text typing, then [Return to step 8](INSTALL.md#8-everyday-boot-and-recovery). On **retained stock**, [return to keep-stock](#keep-stock), complete its guarded restart/second stock boot and records, then Return to step 8. Do not go through layout proof/finish for an abandoned trial, or through the initial switch steps. **Record:** booted OS, confirmed map, fresh login, abandon result/title and completion route.

## Recovery menu

A failed **first** switch boot or stale/missing title always means **F12** (or **Fn+F12**) → **Windows → Help**. Do not use the provisional switch title for recovery. After an [update](INSTALL.md#update-aresos-to-a-new-release) there are three deployments and the rollback and keep-stock commands refuse, so do not use this menu; use that route's previous box or **F12 → Windows → Help**.

For a later failure only, with your own first successful AresOS boot/final-pair check and a fresh record after the latest reorder: **F12** (or **Fn+F12**) → recorded Linux entry → GRUB. If hidden, **Esc** once, then **↓**. Match the **entire current stock title**, resolved by saved checksum **and serial and stateroot**; both rows may say Bazzite. Never guess by position/example digits. Missing, duplicate, truncated or different title → **STOP → [Help](INSTALL-REFERENCE.md#help)** via Windows. Do not select another row to experiment.

Select only the exact stock title. Expect rendered stock greeter → `ares-recovery`, **installer German** password → [tty3 administrator entry](INSTALL-REFERENCE.md#console). **Return to this recovery procedure**. Run keep-stock below, never rollback from booted stock. **Return to step 8** ([everyday use](INSTALL.md#8-everyday-boot-and-recovery)) after its second Linux default boot passes.

## Rollback from running AresOS

On booted AresOS, tty3 **ares-recovery with current AresOS layout → sudo -i**:

```bash
sudo /var/lib/ares/at rollback
sudo /var/lib/ares/at title
```

Require `PASS rollback`, `PASS title`: idle before queueing, exact saved stock checksum/serial/stateroot, origin/digest/pin and rollback queued. Invalidate all old titles immediately, including before reboot; save the resolved new title/state/time. Wrong booted image, pending work or changed identity means STOP; the tool refuses from stock with zero deployment mutations.

```bash
sudo /var/lib/ares/at reboot
```

Require `PASS reboot` / `Reboot requested; Windows stays default; F12 then Linux for one Linux start` (screen may disappear); all sticks absent → **F12** (or **Fn+F12**) → Linux → let stock start, no GRUB selection. Rendered greeter → `ares-recovery` **installer German** → fresh tty3 password login/`sudo -i`:

```bash
sudo /var/lib/ares/at check
sudo /var/lib/ares/at title
```

Require PASS, corrected pinned stock booted, AresOS retained, loaded German, full current record. Windows remains firmware default; do not enable stock automatic updates during the trial. **Record:** queued/booted identity/title and typing/login results. **STOP → [Help](INSTALL-REFERENCE.md#help)**. **Return to step 8:** [everyday use](INSTALL.md#8-everyday-boot-and-recovery).

## Keep stock

After GRUB recovery/normal rollback, on **booted corrected stock**, `ares-recovery` German → tty3 → `sudo -i`:

```bash
sudo /var/lib/ares/at keep-stock
sudo /var/lib/ares/at title
```

Require `PASS keep-stock`, `PASS title`, exact saved corrected identity/pin, no pending work and stock first. Mark old title INVALID; save new resolved title/state/time before:

```bash
sudo /var/lib/ares/at reboot
```

Require `PASS reboot` / `Reboot requested; Windows stays default; F12 then Linux for one Linux start` (screen may disappear). All sticks absent → **F12** (or **Fn+F12**) → Linux; **no GRUB selection**. Require stock again (second Linux default boot), rendered greeter → `ares-recovery` installer German → fresh tty3 password login → `sudo -i` → `sudo /var/lib/ares/at check` and `sudo /var/lib/ares/at title`, expecting `PASS check` and `PASS title`. Prove physical typing/password sudo as step 5. Leave stock updaters paused until the owner chooses stock permanently and that second default boot passes.

For diagnostics, insert ARESTOOLS only after Linux sign-in; `sudo /var/lib/ares/at export` must print `PASS export` and **SAFE TO REMOVE ARESTOOLS**. Unplug. To compare Windows afterward, use `sudo /var/lib/ares/at reboot`, expecting `PASS reboot` / `Reboot requested; Windows stays default; F12 then Linux for one Linux start` (screen may disappear); press nothing for Windows. Run [record B](INSTALL-RECORD.md#b-compare-windows-after-each-stage), stage **after-aresos**, but write **calling procedure: keep-stock** beside it. The stage is a filename label; the selected Linux default is stock. If C/D is separately required while this caller is retained, keep that same caller for its return too. After records, [return to keep-stock completion](#keep-stock-records-complete).

### Keep-stock records complete

Require the Windows-unchanged PASS and the recorded keep-stock second Linux default boot. Keep diagnostics private. **Record:** persistent stock selection/second default boot/title and Windows PASS. **STOP → [Help](INSTALL-REFERENCE.md#help)**; resume at this completion checkpoint after resolution. **Return to step 8:** [everyday use](INSTALL.md#8-everyday-boot-and-recovery). Permanent abandonment still requires [step 9 token retirement](INSTALL.md#9-retire-access-and-return-to-windows).

## Optional removal or erasure

Default undo needs neither: leave Crucial installed. First complete [step 9 token retirement and independent Windows proof](INSTALL.md#9-retire-access-and-return-to-windows), even when Linux cannot boot. Export Linux data and verify independent copies. Immediately before removal/reuse repeat direct Windows and record B **before-undo**: original Micron EFI/Microsoft target mandatory; login alone is insufficient. Changed/unreadable boot target → **STOP → [Help](INSTALL-REFERENCE.md#help)**, remove/erase nothing. No C: expansion or Micron changes.

**Removal:** repeat the [full fitting/safety checkpoint](INSTALL-REFERENCE.md#fitting), including external battery inspection and immediate inspection after lifting cover. **Return to this removal procedure** after reading it; do only Lenovo Figure 9's Crucial removal after safe battery disconnection. Any battery warning → stop before connector work, no handling/reconnection/power, Lenovo/qualified repairer. Retain Crucial's screw, reconnect only if safe, close and boot Windows; repeat B **after-undo**. Removal preserves recoverable data; store the SSD safely.

**Erasure for reuse:** pinned [GParted Live 1.8.1-6 amd64 ISO](https://downloads.sourceforge.net/project/gparted/gparted-live-stable/1.8.1-6/gparted-live-1.8.1-6-amd64.iso), SHA-256 `d789c38779f0d6f7026c12f44c2c52a04f66e28a1aea7d51f3045ad1bbf28411`. Require full downloaded file and fresh [official checksum](https://gparted.org/gparted-live/stable/CHECKSUMS.TXT) to match the pin in [media-tools.json](../os/manifest/media-tools.json); missing/mutable version → STOP for maintainer qualification. Write only **ARESOS INSTALLER — ERASE OK** with [the pinned ISO-file writer route](INSTALL-REFERENCE.md#writer-labels), never recovery. This overwrites tools/exports: preserve their independent copies first. **Return to this erasure procedure** after writer success.

**F12** (or **Fn+F12**) → GParted USB; choose German keyboard/English interface. Physically test `y z / - " $` in text editor before Terminal. Repeat [record C](INSTALL-RECORD.md#c-identify-both-drives-in-live-linux) and [record D](INSTALL-RECORD.md#d-before-erasing-crucial-from-live-media); **Return to this erasure procedure** only with PASS, same-session identity/GUID/bounds map, neither internal drive mounted, every Crucial partition disposable and original Windows target proved. In GParted match Crucial in selector → **Device → Create Partition Table → gpt**. Immediately before **Apply**, recheck whole-disk path and all checks. Apply **writes immediately**, not a queued action ([manual](https://gparted.org/display-doc.php?name=help-manual)). This clears layout; **it does not securely sanitise data**. Any Micron action/unknown partition/unclear identity → cancel, help.

Shut down, remove USB, Windows → record B **after-undo**. Cancel Windows initialise/format prompts until separately choosing reuse. Leave stale Linux firmware entries for reviewed cleanup; never delete one to hide a difference.

**Record:** retired token, backups, before/after Windows proof, optional procedure performed. **STOP → [Help](INSTALL-REFERENCE.md#help)**; **Return to step 9:** [final Windows confirmation](INSTALL.md#9-retire-access-and-return-to-windows). Starting over is [Return to step 1](INSTALL.md#1-backups-recovery-and-windows-preparation).
