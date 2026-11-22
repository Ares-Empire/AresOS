# Indicator and window frame headless harness

From the worktree, check available memory with `free -g` and run one container at a time.

```sh
os/tests/indicator-harness/run.sh image
os/tests/indicator-harness/run.sh run .work/320/evidence
os/tests/indicator-harness/run.sh frame .work/329/evidence
```

The image command uses `localhost/aresos-labwc:311e` by default. When the lock changes, rebuild the `labwc` stage
of `os/Containerfile` and set `LABWC_IMAGE` to that image. The harness rebuilds the two package 316 clients and
installs GTK and the pinned GTK layer-shell RPM. Its build and each run verify the installed labwc against
`os/labwc/labwc.lock.json`. Set `HARNESS_IMAGE_TAG` for both the image and run commands to use a separate tag.

The run takes an empty evidence directory. It streams the specific checkout files to a disposable rootless Podman
container. Container networking is disabled and there are no host-folder, session-socket or hardware-device mounts.
The isolation checks run before the first private socket is made. The driver and its headless labwc processes
inherit one private D-Bus address from `dbus-run-session`. The system paths
for `brightnessctl`, `wpctl` and `pw-dump` hold file-backed fixtures inside the container. The Wayland client from
package 316 provides virtual devices and a fullscreen stand-in, with the pointer lock from package 311's probe.

`results.txt` records the check counts and the timings. The numbered PNGs are output-sized `grim` captures of the
stand-in, an empty headless output and the public Look A plate. The placement check exits immediately when the
compositor puts a plate on an unexpected output. The public evidence directory lives under
`reviews/320-indicator/evidence/`.

Frame mode uses two 1920 × 1080 outputs at scale 1. It installs the branch's Look A theme, font and pack at
their image paths and stages the Crown theme, Space Grotesk and config from the merge base with `origin/main`
for the binding and pointer-lock comparison. Keep `origin/main` current when reproducing the comparison.
The separate toggle session adds two workspaces and enables the shade and all-desktops buttons. The evidence
includes labelled Look A screenshots and contact sheets, client and labwc logs, and machine-readable
binding and switcher comparisons. The published run lives under `reviews/329-window-frame/evidence/`.
