#!/usr/bin/bash
# Deferred diagnostic prototype; see briefs/03-followup-activation-audit.md.
set -euo pipefail
container=aresos-parser-preflight
image=localhost/aresos:ci
mounts=(--volume "$PWD/os/ci/activation_audit.py:/usr/libexec/aresos-audit:ro")
if [[ ${1:-} == --base ]]; then
    image=$(jq -r .reference os/manifest/base.json)
    # Exercise the deferred graph prototype without building an image or disk.
fi
cleanup() {
    # Preserve the failing manager's diagnostics before removing the container.
    sudo podman exec "$container" systemctl status dbus.service user@1001.service --no-pager > evidence/fedora-container-status.txt 2>&1 || true
    sudo podman exec "$container" journalctl --no-pager -b -u user@1001.service > evidence/fedora-container-user-journal.txt 2>&1 || true
    sudo podman logs "$container" > evidence/fedora-container-console.txt 2>&1
    sudo podman rm --force "$container" > /dev/null
}
trap cleanup EXIT
sudo podman run --detach --name "$container" --privileged --cgroupns=private --systemd=always --network=none \
    --volume "$PWD/evidence:/evidence" \
    --volume "$PWD/os/ci/parser_preflight.py:/usr/libexec/aresos-parser-preflight.py:ro" \
    "${mounts[@]}" --entrypoint /usr/lib/systemd/systemd "$image" --unit=basic.target
for attempt in {1..60}; do
    if sudo podman exec "$container" systemctl show basic.target --property=ActiveState --value | grep -qx active; then
        break
    fi
    sleep 1
done
test "$(sudo podman exec "$container" systemctl show basic.target --property=ActiveState --value)" = active
if [[ ${1:-} == --base ]]; then
    sudo podman exec "$container" useradd --uid 1001 --user-group --no-create-home --home-dir /var/home/ares --shell /bin/bash ares
fi
sudo podman exec "$container" systemctl start dbus.service user@1001.service
sudo podman exec "$container" python3 /usr/libexec/aresos-parser-preflight.py
