# 52: Prism's metadata pinned by commit (image builds broke on Prism's weekly update)

Empire board brief 305. Written 2026-11-17 by `linux-aresos`, who also built it (a two-line lock change and a test,
cheaper to make than to brief). A fresh reviewer checks it.

## Why

`os/build.sh` fetches Prism's metadata for Minecraft and LWJGL (`os/minecraft/desktop.lock.json`, `components`) and
accepts each file only with its pinned SHA-256 and size. The URLs pointed at `meta.prismlauncher.org/v1/…`, which
Prism regenerates every week from its repository `PrismLauncher/meta-launcher` (commits "Update <date>").

On 2026-11-17 at 16:04 UTC (their commit `e5a979dd`) `net.minecraft/26.2.json` changed: only Mojang's asset-index
entry (`sha1`, `totalSize`, `url`). Our pin (`9c23199a…`, their 2026-11-10 bytes) no longer matched, so every image
build failed in the packages stage with "net.minecraft.json differs from its pin" (`linux-tools`, seen on #58's
build run 44129709609). A re-pin would break again next week.

## What changed

- Each component's URL names one commit of `PrismLauncher/meta-launcher` on `raw.githubusercontent.com`, so its bytes
  never change:
  - `net.minecraft/26.2.json` at `b8e2a3e1ba241414f8b861f13c9a6fd6bc5d922d` ("Update 2026-11-10"), the bytes we pinned;
  - `org.lwjgl3/3.4.1.json` at `1977d95e9aa980361f9976cf502a7f584facae0e` (its last change, 2026-10-17).
- SHA-256 and size are unchanged (checked 2026-11-17: the raw files are `9c23199a…`, 24493 bytes, and `4108a1aa…`,
  73685 bytes). So the image's files are the same bytes; only the lock's URLs differ.
- The asset index the pinned file names (`piston-meta.mojang.com/v1/packages/941b1ea6…/32.json`) is still served
  (HTTP 200, 586566 bytes). Prism checks it by its SHA-1 when it downloads the game.
- `os/tests/test_aresos_desktop.py`: a test requires every component URL to be a commit-pinned raw URL whose path is
  `<uid>/<version>.json`, so a re-pin to the moving URL fails locally.

## Not changed

`build.sh`'s fetch and check, the Prism tarball, Fabric's libraries and mods. Release 28's rules (branch
`pkg/42-release-28`, `os/ci/release_diff.py`'s `minecraft_pins`, not on `main` yet) read the components' SHA-256,
which is unchanged; the lock's URL change rides from `main` like any other change there.
