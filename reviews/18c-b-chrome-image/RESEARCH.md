# 18c-b research: how the image installs our Chrome extension

Written for brief `briefs/18c-b-chrome-image.md` on 2026-11-14, before the brief. It compares the ways Chrome on Linux
can install and update an extension that is not in its web store, and recommends the one the brief builds. Nothing
was built or run for it; the claims rest on the linked documentation and Chromium sources, read on that day. The
brief has every one of them proven again on the Chrome the image ships.

**Recommend image-local `file:` installation through force-install policy, with a fresh random signing key per image, discarded after packaging.** This suits the extension’s current lack of persistent state and avoids keeping a production secret.

Below, **documented** means Google documentation; **source** means current upstream Chromium; **inference** identifies the proposed AresOS behavior. I inspected the requested repository files. No files changed and no browser/VM tests were run.

**1. Force-install policies**

**Documented/source:** Both `ExtensionInstallForcelist` and `ExtensionSettings` with `installation_mode: "force_installed"` accept update-manifest URLs using **HTTPS, HTTP—including loopback HTTP—and `file:`**. HTTP is not restricted to loopback. Chromium’s policy handler applies the same scheme check to both policies. `data:` is excluded. [Policy definition](https://chromium.googlesource.com/chromium/src/+/HEAD/components/policy/resources/templates/policy_definitions/Extensions/ExtensionInstallForcelist.yaml), [policy validation](https://raw.githubusercontent.com/chromium/chromium/main/chrome/browser/extensions/policy_handlers.cc).

Linux permits off-store force-install using local machine policy **without cloud enrollment, MDM or domain membership**. The documented management restrictions concern Windows/macOS; Chromium’s corresponding enforcement returns false on Linux. Force-installed extensions install silently and cannot ordinarily be disabled or removed through Chrome’s UI. [Linux enforcement source](https://raw.githubusercontent.com/chromium/chromium/main/chrome/browser/extensions/extension_management.cc).

The policy URL normally controls initial installation. Subsequent updates use the extension manifest’s URL unless `override_update_url: true` keeps them on the policy URL. The repository extension currently has no manifest `update_url`; production should explicitly configure the override. [ExtensionSettings documentation](https://support.google.com/chrome/a/answer/9867568?hl=en).

**Source/inference:** On an uncached first install, an unreachable endpoint leaves the extension uninstalled/pending; policy does not block ordinary browsing until installation succeeds. Network failures receive retries/backoff, and later checks include pending extensions. After installation, an update failure normally leaves the installed version running. Do not promise a fixed recovery deadline. [Downloader](https://raw.githubusercontent.com/chromium/chromium/main/extensions/browser/updater/extension_downloader.cc), [updater](https://raw.githubusercontent.com/chromium/chromium/main/chrome/browser/extensions/updater/extension_updater.cc).

**2. Linux external extensions**

**Documented:** `<ID>.json` under `/opt/google/chrome/extensions/` or `/usr/share/google-chrome/extensions/` supports `external_crx` plus `external_version`, or `external_update_url`. For local updates, replace the CRX and increase the descriptor version; Chrome scans these entries at startup. Users can remove the extension, after which Chrome remembers that choice and stops reinstalling it. [External-install guide](https://developer.chrome.com/docs/extensions/how-to/distribute/install-extensions).

**Source:** Linux still registers these providers, and external-install confirmation defaults to disabled there: initial installation is normally enabled without a prompt. It remains user-disableable/removable. Current source also explicitly retains an installed version newer than the local descriptor. [Providers](https://raw.githubusercontent.com/chromium/chromium/main/chrome/browser/extensions/external_provider_impl.cc), [prompt default](https://raw.githubusercontent.com/chromium/chromium/main/extensions/common/feature_switch.cc), [version handling](https://raw.githubusercontent.com/chromium/chromium/main/chrome/browser/extensions/external_provider_manager.cc).

The guide contains an old, conflicting FAQ about local preinstallation; current Linux implementation is stronger evidence of continued support, but qualification against the shipped Chrome remains necessary.

**Inference:** Adding a same-ID force-install policy can establish policy control, but then the policy download route must work. There is no separate documented switch that makes an arbitrary external-file installation permanently enabled. `toolbar_pin: "force_pinned"` only pins its icon.

**3. Other routes**

- **Managed launcher with `--load-extension`:** unsuitable; branded Google Chrome removed this flag in Chrome 137. Chromium/Chrome for Testing behavior is different. [Google announcement](https://developer.chrome.com/blog/extension-news-june-2025).
- **System loopback HTTP server:** viable and offline-capable; the repo’s CI already implements this pattern. It adds listener ownership, startup ordering and availability concerns.
- **`file:` manifest and CRX:** viable; Chromium explicitly selects a file loader for both downloads. This avoids a listener and HTTPS certificate management. [Downloader source](https://raw.githubusercontent.com/chromium/chromium/main/extensions/browser/updater/extension_downloader.cc).
- **`data:` manifest:** unsuitable; the downloader explicitly rejects it because update requests require query parameters.

**4. Signing identity**

**Documented/source:** The ID derives from the public key’s hash. CRX3 verifies a developer-key proof binding that identity to the signed archive. It does not establish that the code is trustworthy, authenticate the update XML, or replace runtime filesystem protection. [CRX3 format](https://raw.githubusercontent.com/chromium/chromium/main/components/crx_file/crx3.proto), [verifier](https://raw.githubusercontent.com/chromium/chromium/main/components/crx_file/crx_verifier.cc).

- **Fresh key each image:** creates a new extension, rather than updating the previous identity. Generate policy IDs, XML `appid` and native-host `allowed_origins` together. Old extension storage/settings do not migrate. My repository search found no `chrome.storage`, IndexedDB, localStorage or sessionStorage usage; control state is in memory in `control/chrome/extension/background.js`. Chrome-managed preferences remain identity-specific.
- **One private CI secret:** preserves identity and permits ordinary same-ID updates; protects against outsiders forging accepted packages. It requires backup, restricted CI access and compromise handling.
- **Public deterministic derivation:** anyone can reproduce the private key and forge same-ID CRXs. It can work only when the verified image and immutable local update source provide all authenticity; CRX signing then adds no protection against deliberate forgery. A signed image does not protect Chrome’s writable installed profile copy. This option is unnecessary here.

Native messaging restricts access by extension origin/ID, not by independently attesting its running code. Use exactly one allowed origin, without wildcards. [Native messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging).

**5. Updates and rollback**

**Documented/inference:** Chrome maintains its installed extension in the persistent user profile. Same-ID network or file updates advance versions; restoring an older image does not normally downgrade that profile copy. Local external CRXs have the same limitation. A remote endpoint can also move an extension ahead of the image’s native host. [Update contract](https://developer.chrome.com/docs/extensions/how-to/distribute/host-on-linux).

With a new ID per image, rollback selects the old deployment’s identity and installs its bundled package afresh. Removed force-list entries are automatically uninstalled. This avoids same-ID downgrade semantics, but installation/removal is asynchronous.

**Recommended layout and decisions**

Use `ExtensionSettings` alone: `force_installed`, `override_update_url: true`, `toolbar_pin: "force_pinned"`, and `update_url: "file:///usr/share/aresos/chrome/update.xml"`.

| Path | Ownership/mode |
|---|---|
| `/usr/share/aresos/chrome/{extension.crx,update.xml,policy.json,native-host.json}` | `root:root`, `0644` |
| Parent directories | `root:root`, `0755` |
| `/etc/opt/chrome/policies/managed/aresos.json` | Root-owned symlink to the immutable policy |
| `/etc/opt/chrome/native-messaging-hosts/org.aresos.chrome.json` | Root-owned symlink to the immutable manifest |
| `/usr/libexec/aresos-control/chrome/host` and adjacent `native_host.py` | `root:root`, `0755` and `0644` |

XML `codebase` points to the bundled `file:///…/extension.crx`. Constant `/etc` symlinks keep deployment-specific IDs in `/usr`, avoiding stale regular configuration after `/etc` merging. Generate the random private key in CI memory; retain only the package/public identity.

**Owner decision:** accept identity replacement and image-only releases; reconsider before adding persistent extension settings. No store/public hosting decision is needed.

**Three VM checks:** offline fresh-profile installation with disable/remove refused; deployment A→B→A using the same profile with matching native access and obsolete-ID removal; missing/corrupt package recovery, including rejection of an unrelated native-messaging extension.

**Main risk:** deployment changes are not atomic with Chrome’s persistent profile. Verify symlink discovery and gate AresOS control on successful extension/native readiness. Current documentation/source supports this design; the exact shipped Chrome binary remains unqualified.