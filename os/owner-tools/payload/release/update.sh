#!/usr/bin/bash
set -euo pipefail
test -r /etc/ostree/auth.json
python3 - <<'UPDATE'
import json, subprocess
status = json.loads(subprocess.check_output(['bootc', 'status', '--json']))['status']
assert not status.get('staged') and not status.get('rollbackQueued'), 'STOP: pending deployment before update; see EMERGENCY.md / get help'
running = status['booted']['image']
assert running['image']['image'] == '@CURRENT@' and running['imageDigest'] == '@CURRENT_DIGEST@', 'STOP: running release changed before update'
assert '@REFERENCE@' != '@CURRENT@', 'STOP: target equals the running release'
print('Staging the verified release over the running one:', '@REFERENCE@')
UPDATE
# Every AresOS image so far masks ostree's and bootc's staging finalizers
# (os/policy/masked-system-units.txt), and bootc cannot stage a release while
# they are masked (package 27, rehearsal run 42940741765). Unmask exactly those
# two, as stock Bazzite has them: each must be the image's own /dev/null mask,
# or already unmasked by an earlier update, and every other updater the image
# masks must still be masked. If anything fails before the release is staged,
# both masks are restored. The removal reaches the new release's /etc through
# ostree's merge, so its next update finds them unmasked.
policy=/usr/share/aresos/policy
units=/etc/systemd/system
finalizers=(ostree-finalize-staged.service bootc-finalize-staged.service)
unmask=()
for unit in "${finalizers[@]}"; do
    state=$(systemctl is-enabled "$unit" 2>/dev/null || true)
    if target=$(readlink -- "$units/$unit") && [[ $target == /dev/null && $state == masked ]]; then
        unmask+=("$unit")
    elif [[ -e $units/$unit || -L $units/$unit || $state != static ]]; then
        echo "STOP: $unit is neither the image's mask nor unmasked by an earlier update ($state); nothing was changed" >&2
        exit 1
    fi
done
while read -r unit; do
    if [[ " ${finalizers[*]} " != *" $unit "* && $(systemctl is-enabled "$unit" 2>/dev/null || true) != masked ]]; then
        echo "STOP: updater $unit is not masked; nothing was changed" >&2
        exit 1
    fi
done < "$policy/masked-system-units.txt"
while read -r unit; do
    if [[ $(systemctl --global is-enabled "$unit" 2>/dev/null || true) != masked ]]; then
        echo "STOP: user updater $unit is not masked; nothing was changed" >&2
        exit 1
    fi
done < "$policy/masked-user-units.txt"
unmasked=()
restore() {
    local status=$?
    trap - EXIT
    if ((status != 0 && ${#unmasked[@]} > 0)); then
        for unit in "${unmasked[@]}"; do ln -sfn /dev/null "$units/$unit" || true; done
        systemctl daemon-reload || true
        for unit in "${unmasked[@]}"; do
            if [[ $(systemctl is-enabled "$unit" 2>/dev/null || true) == masked ]]; then
                echo "Staging failed; restored the image's mask of $unit" >&2
            else
                echo "STOP: the mask of $unit could not be restored; get help" >&2
            fi
        done
    fi
    exit "$status"
}
trap restore EXIT
for unit in "${unmask[@]}"; do
    rm -- "$units/$unit"
    unmasked+=("$unit")
done
systemctl daemon-reload
for unit in "${finalizers[@]}"; do
    test "$(systemctl is-enabled "$unit" 2>/dev/null || true)" = static
done
bootc switch --retain @REFERENCE@
