#!/bin/bash
# Disposable Fedora container ONLY. Never run this installer on the owner's host.
set -euo pipefail
test -f /run/.containerenv -o -f /.dockerenv
test "$(id -u)" = 0
dnf install -y python3 python3-pip util-linux findutils
python3 --version
cat /etc/fedora-release
mkdir -p /usr/libexec/aresos-control /usr/lib/aresos-control/vendor /etc/aresos-control
cp -r control/aresos_control control/generated control/launch.py /usr/libexec/aresos-control/
cp control/settings/proxy.json control/settings/service.json /etc/aresos-control/
install -m 0755 control/packaging/aresos control/packaging/aresos-mcp control/packaging/aresos-toold /usr/bin/
python3 -m pip install --no-cache-dir --require-hashes --only-binary=:all: --target /usr/lib/aresos-control/vendor -r control/requirements.lock
chmod -R go-w /usr/libexec/aresos-control /usr/lib/aresos-control/vendor /etc/aresos-control
export PYTHONPATH="$PWD/control:/usr/lib/aresos-control/vendor"
export PYTHONDONTWRITEBYTECODE=1
python3 control/generate.py --check
python3 -m unittest discover -s control/tests -v
printf 'Control base suite PASS\n'
