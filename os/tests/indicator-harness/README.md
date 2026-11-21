# Package 320 headless harness

From the worktree, check available memory with `free -g` and run one container at a time.

```sh
os/tests/indicator-harness/run.sh image
os/tests/indicator-harness/run.sh run .work/320/evidence
```

The first command needs `localhost/aresos-labwc:311e`, the image from the `labwc` stage of `os/Containerfile`.
It rebuilds the two package 316 clients and verifies the installed labwc against `os/labwc/labwc.lock.json`.
It then installs the pinned GTK layer-shell RPM and the other test dependencies in the indicator image.

The run takes an empty evidence directory. It streams the specific checkout files to a disposable rootless Podman
container. Container networking is disabled and there are no host-folder, session-socket or hardware-device mounts.
The isolation checks run before the first private socket is made. The driver and its headless labwc processes
inherit one private D-Bus address from `dbus-run-session`. Every labwc uses the checkout's `rc.xml`. The system paths
for `brightnessctl`, `wpctl` and `pw-dump` hold file-backed fixtures inside the container. The Wayland client from
package 316 provides virtual devices and a fullscreen stand-in, with the pointer lock from package 311's probe.

`results.txt` records the check counts and the timings. The numbered PNGs are output-sized `grim` captures of the
stand-in, an empty headless output and the public Look A plate. The placement check exits immediately when the
compositor puts a plate on an unexpected output. The public evidence directory lives under
`reviews/320-indicator/evidence/`.
