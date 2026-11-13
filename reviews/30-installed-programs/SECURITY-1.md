Reviewed PR #55 at `08753aeb4c0839b0b225c016053448ca84856350`, against `origin/main`. This was a static, read-only review; I ran neither the helper nor tests and changed no files. **Five FIX findings remain.**

1. **FIX — High: discovery can stop the entire launcher from serving.**  
   **Where:** [aresos-shell:624](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:624), lines 637–662, [693–724](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:693), and 2122.  
   **Scenario:** the applications folder contains many hidden, invalid, or colliding entries. The helper collects every desktop path before applying `MAX_APPS`; rejected entries do not advance that limit. Every refresh also walks, stores, sorts and stats the whole tree on the serving thread. Many hard links to one large malformed entry amplify parsing work without requiring much source disk space.  
   **Harm:** listing, opening apps, heartbeats and window handling stall together; sufficiently large collections can exhaust helper memory. The report’s “known limit” classification does not meet the stated availability bar.  
   **Fix:** bound visited directories/files, aggregate bytes and retained data independently of accepted-app count. Perform discovery in a bounded worker, retain the last good catalogue, and keep filesystem work off the serving loop.

2. **FIX — High: SVG decoding is not bounded by the advertised memory limit.**  
   **Where:** [aresos-shell:737](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:737), lines 825–831, 925–943 and 1008–1015.  
   **Scenario:** a small outer SVG contains large compressed raster images in `data:` references. The helper checks only the outer file’s signature; embedded images bypass its PNG dimension check. ImageMagick’s memory setting limits its pixel cache, while librsvg has no total-memory limit. The child has neither an address-space limit nor a dedicated memory-limited cgroup. A three-second timeout does not prevent allocation before expiry. [ImageMagick resource documentation](https://imagemagick.org/resources/), [librsvg security documentation](https://gnome.pages.gitlab.gnome.org/librsvg/devel-docs/security.html).  
   **Harm:** automatic icon conversion can cause memory pressure or OOM affecting the helper and desktop. Moreover, librsvg accepts embedded JPEG/GIF/WebP through its own decoders, outside the ImageMagick coder policy; the two-format restriction therefore does not cover nested content. [Supported formats](https://gnome.pages.gitlab.gnome.org/librsvg/devel-docs/features.html), [data-reference rules](https://gnome.pages.gitlab.gnome.org/librsvg/Rsvg-2.0/class.Handle.html).  
   **Fix:** enforce an OS-level memory ceiling for the converter and descendants. Reject external/embedded image references, or validate permitted embedded PNGs with explicit decoded-size and aggregate limits before conversion.

3. **FIX — Medium: icon refresh can fill the owner’s disk.**  
   **Where:** [aresos-shell:983](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:983), lines 1018–1024 and [1911–1914](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1911).  
   **Scenario:** an installed program repeatedly updates its icon, even merely changing its modification time. Each version gets a new permanent hash-named PNG. Repeated refreshes never remove obsolete files, including those belonging to removed apps. Multiple changing icons amplify accumulation.  
   **Harm:** the cache grows without a total byte/count limit and can fill the shared home filesystem. The per-conversion output limit does not bound cumulative storage.  
   **Fix:** impose a total cache quota and remove unreferenced generations with bounded retention. Refuse further cache writes gracefully when the budget is exhausted.

4. **FIX — Medium: systemd expands arguments after `Exec` parsing.**  
   **Where:** [aresos-shell:1160](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:1160); field substitutions at lines 419–427.  
   **Scenario:** a correctly escaped literal `${HOME}` survives desktop-entry parsing, or arrives through `%c`/`%i`. `systemd-run --scope` then expands it because the command omits `--expand-environment=no`. The repository records systemd 259.9, whose documented default enables this expansion. [Recorded version](/var/home/ares/AresOS-30-installed-programs/os/manifest/ci/14/parser-sources/packages.json:37), [systemd 259 documentation](https://www.freedesktop.org/software/systemd/man/259/systemd-run.html#--expand-environment=BOOL).  
   **Harm:** the launched program receives different arguments from the parsed desktop entry. Literal file operands can become different read, overwrite or deletion targets. This is additional interpretation even though `Popen` does not invoke a shell.  
   **Fix:** add `--expand-environment=no` before `--`, and verify literal dollar expressions through the actual systemd launch route.

5. **FIX — Medium: input symlinks are not confined before filesystem access.**  
   **Where:** [aresos-shell:486](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:486), and [790–800](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:790).  
   **Scenario:** an applications-directory `.desktop` symlink points to an arbitrary regular file outside the application/deployment roots. `os.open` follows it without checking its destination. Separately, a `hicolor` theme-directory symlink is traversed by `scandir` before the eventual icon candidate’s containment check.  
   **Harm:** automatic discovery reads outside the intended roots. A desktop-file link onto a stalled mounted filesystem can also block the serving thread: `O_NONBLOCK` does not give regular-file reads a deadline. The later icon check prevents publishing an escaped candidate, but cannot undo directory reads already performed.  
   **Fix:** explicitly permit necessary Flatpak deployment targets while rejecting other escapes; validate directory components before enumeration and use descriptor-based opens to preserve containment. Isolate potentially blocking reads from serving. Explicit absolute `Icon` paths remain the separately authorized input case.

**KNOWN LIMIT — Low: a discovered entry can impersonate another program’s presentation.**  
At [aresos-shell:583](/var/home/ares/AresOS-30-installed-programs/os/config/usr/libexec/aresos-shell:583) and 633, an owner-controlled entry can choose a familiar name/icon or supply replacement presentation metadata. The owner can consequently select a misleading entry. This has ordinary desktop-launcher power and is accepted under your bar; no additional approval mechanism is required.

The remaining requested boundaries were checked:

| Boundary | Static conclusion and location |
|---|---|
| Privilege and writes | No added sudo, polkit or privileged-helper route found. Application scopes use `--user`; helper writes target runtime journal/socket and icon cache locations. See lines 911–1027, 1114–1129, 1161 and 2592–2595. |
| Launch scope and secrets | Independent `app.slice` scope; nonce, desktop instance and helper plumbing are removed, along with inherited GPU selectors. Only the fixed NVIDIA values are added. See lines 121–123 and 1155–1176. |
| Shell/window-text injection | Launch uses an argv list; window titles are ignored and window identities do not supply commands. The additional argument interpretation is finding 4. See lines 370–434, 1174 and 1562–1578. |
| Socket authority | Same-UID check, nonce/instance authentication, bounded messages, operation allowlist and catalogue-only app lookup are present. No socket-supplied command/environment route found. Readiness and heartbeat remain the documented additional operations. See lines 1729–1783, 1805–1844, 1939–1957 and 2477. |
| Converter isolation | Explicit coders, librsvg verification, denied delegates/filters, network namespace isolation, cleared environment, restricted mounts and timeout/output bounds are present. No network or sandbox-escape route identified; finding 2 concerns limits inside that sandbox. See lines 740–747 and 925–1015. |
| Text reaching the game | Names/generic names, keywords, categories, desktop IDs and executable names have character/count bounds; app IDs are sanitized and replies are byte-paged. Launch definitions are excluded. See lines 552–563, 583–611 and 1849–1889. |
| Three reviewed entries | Registry IDs are reserved; discovered identities cannot claim registry or desktop identities. `replaces` comes only from reviewed JSON and borrows presentation fields, never argv, working directory, GPU policy or window policy. See lines 249–257, 615–638 and 657–668. |

CHANGES-NEEDED