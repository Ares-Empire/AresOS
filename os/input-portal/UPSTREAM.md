# Where this code comes from

`os/input-portal/` is AresOS's copy of **niri-input-portal**, being changed to serve labwc (package 316,
`briefs/316-input-portal.md`).

| | |
|---|---|
| Upstream | https://github.com/Qingswe/niri-input-portal |
| Commit | `49f82a63ca53b0137ad4eea08f4cd9d72642a22b` ("Merge pull request #2 from Qingswe/fix/eis-region-bounds") |
| Date | 2026-10-20 16:19 UTC |
| License | MIT. `LICENSE` is upstream's file, unchanged, and ships with the binary. |
| Vendored in | commit `009b840c`, which changes nothing |

## Checking the copy

The vendor commit's folder is upstream's commit, file for file, name for name and mode for mode: both are the
same git tree.

```sh
git rev-parse 009b840c:os/input-portal     # 0b0106d81218dc0fe744812310c48f4245b522b0
git rev-parse '49f82a63^{tree}'            # the same, in a clone of upstream
```

What AresOS changed since then:

```sh
git diff 009b840c -- os/input-portal
```

If the vendor commit is ever missing from this repo's history (a squash merge drops it), the same comparison works
against upstream itself:

```sh
git fetch https://github.com/Qingswe/niri-input-portal 49f82a63ca53b0137ad4eea08f4cd9d72642a22b
git diff 'FETCH_HEAD^{tree}' HEAD:os/input-portal
```

## Our changes

Every change to this folder gets a row here, with the commit that made it.

| Commit | Change |
|---|---|
| `bb596239` | Deleted `install.sh` and `uninstall.sh`. They call `sudo`, write to `/usr` and `~/.config/xdg-desktop-portal`, and restart the user's portal. AresOS installs the backend from its image (package (c)). |
| `baf97613` | Names. The package and binary are `aresos-input-portal` (`Cargo.toml`; in `Cargo.lock` only the package's own entry changes: new name, moved to its place in name order). D-Bus name `org.freedesktop.impl.portal.desktop.aresos-input` (`src/main.rs`). Variables `ARESOS_INPUT_PORTAL_IDLE_TIMEOUT` (`src/wayland/mod.rs`) and `ARESOS_INPUT_PORTAL_LOG` (`src/main.rs`). `data/`: the three files renamed to `aresos-input.portal`, `aresos-input-portal.service` and `org.freedesktop.impl.portal.desktop.aresos-input.service`, pointing at `/usr/libexec/aresos-input-portal`; the portal file gains `UseIn=AresOS`. |
| `1db141b3` | Added, no upstream file touched: `build.sh`, `toolchain.env` (the pinned builder image, compiler, Debian packages, cargo-audit and advisory database) and `dev/container.sh`. |
| (the commit after `1db141b3`) | Added this file. |

## Still upstream's wording

`README.md` is upstream's text, unchanged. It explains how the capture and the clipboard work, which still holds.
It also describes niri, `install.sh`, `/usr/lib/niri-input-portal`, the `NIRI_INPUT_PORTAL_*` variables and the
`--clip-*` commands: none of those apply to AresOS's copy. The names above are the ones that count here.
