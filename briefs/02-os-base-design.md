# 02: OS base design (research, no code)

**Goal:** a design document, `docs/design/OS-BASE.md`, that decides how the Linux layer of AresOS works. The laptop boots from its own drive, shows a Mojang-style splash, and drops the owner straight into their Minecraft world, where the shell mod is the whole desktop. The owner should be able to read the main part in about 15 minutes and make the decisions it asks for. Evidence and details go in appendices.

**Questions to answer.** For each: the realistic options, a comparison, sources (links, with the date you checked), and a recommendation. Mark every fact as **verified** (you saw it in a source) or **assumed**.

1. **Base and "OS as code":** which Linux base (for example NixOS, Arch with archiso, Fedora Atomic / bootc images, Debian live-build). How is the whole OS defined in this repo, and where does the image get built? The owner's laptop runs Windows, so consider WSL2, Docker and GitHub Actions (private repo, free minutes).
2. **Graphics and power:** RTX 4060 plus Intel Iris Xe (hybrid / Optimus). Minecraft must run on the NVIDIA GPU. Cover suspend/resume, battery life and the driver approach.
3. **Secure Boot:** can AresOS boot without the owner changing BIOS settings? What does that mean for NVIDIA kernel modules (for example MOK enrollment)? Also, Windows may have device encryption (BitLocker), and the boot flow must not trigger a recovery-key prompt.
4. **The session:** what runs as the "desktop"? Compare compositor options (for example cage, labwc, sway, gamescope, or our own later). Apps launched by the mod must appear on top, and closing them must return to Minecraft. Cover apps without their own close button, switching between open apps, auto-restarting Minecraft if it crashes, and a hidden escape hatch to a plain terminal.
5. **Starting Minecraft:** which launcher (the official launcher, Prism Launcher's command line, or a small custom launcher). Cover Microsoft account login and token refresh, playing offline, launching straight into a specific world (Quick Play), pinning the Minecraft, Fabric and mod versions, and where the world save lives and how it's backed up.
6. **Boot look:** a Plymouth splash with a Mojang-style logo, auto-login, and expected boot-to-world time. Logo files are supplied locally at build time and never committed (Mojang assets).
7. **Everyday OS needs without a normal desktop:** Wi-Fi setup, volume, Bluetooth, brightness, battery, notifications, file access, updates, sleep and shutdown. Say which need an in-game UI from the mod and which get a fallback, and what the minimum for a first bootable version is.
8. **Install targets:** an external USB SSD for testing, later the second internal NVMe slot (M.2 2280). The Windows SSD (Micron 512 GB) must never be touched, and the installer needs safeguards against it. How is the OS picked at boot (F12 one-time menu, boot menu entry)?
9. **Updates:** how AresOS updates itself from this GitHub repo.
10. **Testing:** what can be tested in a VM (QEMU or similar) on the Windows laptop, and what only on real hardware.

**Also deliver:**
- The recommended stack in one table.
- The top risks and how to reduce each.
- Phase 2 cut into small packages in build order, each in one or two lines.
- A short list of **owner decisions**, each with your recommendation.

**Out of scope:** writing OS code or configs; downloading ISOs or installing anything; touching disks, partitions or boot settings. Web research and reading only.

**Acceptance:**
- `docs/design/OS-BASE.md` exists, answers all ten questions, and contains the deliverables above.
- Every external fact has a source link.
- It is committed on the branch with a PR opened.

There's no separate package review. A design council reviews this document next (`docs/REVIEW.md`), so write it to be challenged: state assumptions plainly.

**Already decided (from `README.md`):**
- Linux base plus the Fabric shell mod as the desktop.
- Minecraft 26.2 with Fabric, and shaders via Iris and Sodium.
- AresOS lives on its own drive, chosen with F12 on the Lenovo LOQ 15IRH8.

**If unsure:** prefer the option that keeps Windows untouched and is easiest to undo. Say what would change your recommendation.

**Model:** gpt-6-astra (frontier), xhigh.
