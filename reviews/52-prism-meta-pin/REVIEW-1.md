# Package 52, review 1 (Codex gpt-6-astra, high, read-only, on ea9136cd)

Astra, because a fresh reviewer must not be the builder (linux-aresos built it) and Codex is the reviewer until 2026-11-21. The builder fetched both pinned URLs on the laptop (SHA-256 and size equal the lock's; Mojang's old asset index served, HTTP 200), since the sandbox had no network. The brief's note on release_diff is fixed in the next commit.

No must-fix or should-fix findings.

- **Note — `os/build.sh:136–145,170–171`:** Each component is fetched from its lock URL and accepted only after SHA-256 and size checks. Both pins remain unchanged. Runtime provisioning and image checks use local filenames and hashes; I found no dependency on the old hostname or component URL format.
- **Note — `os/minecraft/desktop.lock.json:11,19`:** Both URLs specify full 40-hex commits of `PrismLauncher/meta-launcher` and the correct `<uid>/<version>.json` paths. Fetches failed with DNS errors; the web fallback also failed. I could not independently verify downloaded hashes, sizes, or asset-index availability.
- **Note — `os/tests/test_aresos_desktop.py:307–310`:** The changed test passed. Running that same test with in-memory mutations rejected the old moving URL, an eight-character commit, a `main` ref, and an incorrect path for each component: eight expected failures. The full module remains for the builder.
- **Note — `os/config/usr/libexec/aresos-desktop:318–321`:** These remain the same pinned local patches, so no runtime content change is introduced. Prism 11.1.1 downloads the asset index specified by the metadata and validates its SHA-1 ([upstream implementation, lines 22–31](https://github.com/PrismLauncher/PrismLauncher/blob/11.1.1/launcher/minecraft/update/AssetUpdateTask.cpp#L22-L31)). A frozen index excludes later asset updates; unavailable or mismatched downloads can prevent launch. That existing dependency is unchanged here.
- **Note — `briefs/52-prism-meta-pin.md:33`:** The claimed `release_diff.minecraft_pins` function does not exist in this checkout. `os/ci/release_diff.py` contains the older release-27 classifier and no component-URL dependency; the brief’s specific claim is unsupported.

No files edited. `git diff --check origin/main...HEAD` passed.

SAFE