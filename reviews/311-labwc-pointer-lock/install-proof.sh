#!/usr/bin/bash
# Brief 311b, acceptance 3: the real swap in a throwaway container of the pinned base, and each guard made to fire.
# The fault injection (rpm -e --nodeps, moving a library) happens only here, in that container.
#   /proof/ours, /proof/fedora, /proof/guard2: one RPM each. /os: the repository's os/ folder, read-only.
set -uo pipefail
stop() { echo "PROOF_FAILED $*"; exit 1; }
ours=labwc-0.9.6-1.fc44.aresos1.x86_64 fedora=labwc-0.9.6-1.fc44.x86_64
mkdir -p /tmp/aresos /usr/share/aresos/manifest /tmp/rpm /tmp/g2
cp -a /os/labwc /tmp/aresos/labwc
cp /os/packages.lock.json /tmp/aresos/packages.lock.json
cp /proof/ours/$ours.rpm /tmp/rpm/
cp /proof/guard2/$ours.rpm /tmp/g2/

echo '=== Fedora labwc and the locked wlroots go in, as the packages stage does'
rpm -qa --qf '%{NEVRA}\n' | sort > /tmp/before.txt
dnf5 -q -y --disable-repo='*' --enable-repo=fedora --enable-repo=updates --setopt=install_weak_deps=False \
    install /proof/fedora/$fedora.rpm wlroots0.19-0.19.3-1.fc44.x86_64 >/dev/null || stop 'Fedora labwc did not install'
test "$(rpm -q labwc)" = "$fedora" || stop 'Fedora labwc is not installed'
rpm -q wlroots0.19

echo '=== Guard 2 fires: an RPM with an unmet Requires must not go in'
python3 -I /tmp/aresos/labwc/stage.py install /tmp/g2 /tmp/aresos/labwc 2>&1 | tail -3
status=${PIPESTATUS[0]}
[[ $status == 1 ]] || stop "guard 2: stage.py exit $status"
test "$(rpm -q labwc)" = "$fedora" || stop 'guard 2: labwc changed'
echo "GUARD_2_FIRED exit=$status, labwc is still $(rpm -q labwc)"

echo '=== Guard 1 fires: headers of another wlroots build'
mkdir -p /tmp/g1 && cp -a /tmp/aresos/labwc /tmp/g1/labwc
sed -i 's/wlroots0\.19-devel-0\.19\.3-1\.fc44/wlroots0.19-devel-0.19.4-1.fc44/g' /tmp/g1/labwc/labwc.lock.json
output=$(python3 -I /tmp/aresos/labwc/stage.py install /tmp/rpm /tmp/g1/labwc 2>&1); status=$?
echo "$output"
[[ $status == 1 && $output == *'is not the same build'* ]] || stop "guard 1: exit $status"
echo "GUARD_1_FIRED exit=$status"

echo '=== The real swap'
python3 -I /tmp/aresos/labwc/stage.py install /tmp/rpm /tmp/aresos/labwc 2>&1 | tail -4
status=${PIPESTATUS[0]}
[[ $status == 0 ]] || stop "stage.py install exit $status"
test "$(rpm -q labwc)" = "$ours" || stop 'labwc is not ours'
verify=$(rpm -V labwc); [[ $? == 0 && -z $verify ]] || stop "rpm -V labwc: $verify"
echo "RPM_V_CLEAN $(rpm -q labwc)"
ldd /usr/bin/labwc | grep -c 'not found'

echo '=== The image checks of package 311, as written in os/ci/image-checks.sh'
sed -n '/^# --- Package 311/,/^# --- Package 23: Minecraft/p' /os/ci/image-checks.sh | sed '$d' > /tmp/section.sh
sed -n "/<<'LABWC_RUNTIME'\$/,/^LABWC_RUNTIME\$/p" /tmp/section.sh | sed '1d;$d' > /tmp/runtime.py
bash -c 'set -euo pipefail; pass() { echo "PASS $*"; }; source /tmp/section.sh' 2>&1 | tail -6
[[ ${PIPESTATUS[0]} == 0 ]] || stop 'the image checks failed on the real swap'

echo '=== Guard 3 fires: a library is missing'
library=$(rpm -ql wlroots0.19 | grep 'libwlroots-0.19.so' | head -1)
mv "$library" /tmp/moved-library
output=$(python3 -I /tmp/runtime.py 2>&1); status=$?
mv /tmp/moved-library "$library"
echo "$output"
[[ $status == 1 && $output == *'LABWC_RUNTIME_FAILED ldd'* ]] || stop "guard 3: exit $status"
echo "GUARD_3_FIRED exit=$status"
python3 -I /tmp/runtime.py || stop 'the check does not pass again after the library came back'

echo '=== Guard 4 fires: the files stay, but no package provides the library'
rpm -e --nodeps --justdb wlroots0.19 || stop 'could not take wlroots0.19 out of the package database'
output=$(python3 -I /tmp/runtime.py 2>&1); status=$?
echo "$output"
[[ $status == 1 && $output == *'no package of this image provides'* ]] || stop "guard 4: exit $status"
echo "GUARD_4_FIRED exit=$status"
echo INSTALL_PROOF_PASSED
