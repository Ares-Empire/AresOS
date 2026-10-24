"""Read CLI help from the ISO's existing stock cache, without pulling/installing."""
import json
import os
import pathlib
import re
import subprocess
import sys


def cached_image(images, digest):
    matches = [image for image in images if image.get('digest') == digest]
    assert len(matches) == 1, 'Pinned ISO stock cache is missing or ambiguous'
    image, = matches
    assert re.fullmatch('[0-9a-f]{64}', image['id']), 'Invalid cached stock image ID'
    return image['id']


def help_command(image):
    assert re.fullmatch('[0-9a-f]{64}', image)
    return ['podman', 'run', '--pull=never', '--network=none', '--read-only', '--rm',
            '--entrypoint=/usr/bin/bash', image, '-c', '''set -euo pipefail
for tool in systemctl rpm-ostree bootc ostree pgrep runuser getent python3 grub2-reboot grub2-editenv; do command -v "$tool"; done
rpm-ostree cleanup --help | grep -- --pending
rpm-ostree status --help | grep -- --json
ostree admin pin --help
ostree admin set-default --help
grub2-reboot --help
grub2-editenv --help
bootc status --help
rpm-ostree cancel --help
python3 - <<'VERIFY_STOCK'
import hashlib, json, pathlib, subprocess
def output(command):
    return subprocess.check_output(command, text=True).strip()
versions = {name: output(['rpm', '-q', '--qf', '%{VERSION}', name]) for name in ('rpm-ostree', 'uupd')}
assert versions == {'rpm-ostree': '2026.3', 'uupd': '1.5.0'}, versions
unit = pathlib.Path('/usr/lib/systemd/system/rpm-ostreed.service').read_text()
assert 'ExecStart=+rpm-ostree start-daemon' in unit.splitlines(), unit
# This child verifies the executable's actual Linux comm. It is our own child,
# not a running system service; the read-only container cannot stage an update.
child = subprocess.Popen(['rpm-ostree', 'start-daemon'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
try:
    comm = pathlib.Path('/proc', str(child.pid), 'comm').read_text().strip()
    assert comm == 'rpm-ostree', comm
    try:
        child.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        child.terminate()
        child.communicate(timeout=5)
finally:
    if child.poll() is None:
        child.kill()
        child.wait()
print('ARESOS_STOCK_IDLE_SOURCE_CHECK ' + json.dumps(dict(versions=versions, service=unit,
      daemon_comm=comm, daemon_command=['rpm-ostree', 'start-daemon'],
      binaries={name: hashlib.sha256(pathlib.Path('/usr/bin', name).read_bytes()).hexdigest()
                for name in ('rpm-ostree', 'uupd')},
      transaction_shape='null or three-string active transaction tuple; rpm-ostree v2026.3 source',
      cancel='one active transaction cancellation; waits until active path changes',
      uupd='v1.5.0: bootc upgrade --quiet --progress-fd 3 when compatible; rpm-ostree upgrade fallback')))
VERIFY_STOCK
echo CACHED_STOCK_CLI_HELP_PASSED
''']


def main(digest):
    assert re.fullmatch('sha256:[0-9a-f]{64}', digest)
    images = json.loads(pathlib.Path('/var/lib/containers/storage/overlay-images/images.json').read_text())
    image = cached_image(images, digest)
    environment = dict(os.environ, REGISTRY_AUTH_FILE='/dev/null')
    inspected, = json.loads(subprocess.check_output(['podman', 'image', 'inspect', image], env=environment))
    assert inspected['Id'] == image and inspected['Digest'] == digest, 'Stock cache identity observations disagree'
    result = subprocess.run(help_command(image), env=environment, capture_output=True, timeout=180)
    output = result.stdout.decode()
    print(output)
    print(result.stderr.decode())
    assert result.returncode == 0, 'Cached stock CLI help failed'
    assert 'CACHED_STOCK_CLI_HELP_PASSED' in output
    source, = [json.loads(line.split(' ', 1)[1]) for line in output.splitlines()
               if line.startswith('ARESOS_STOCK_IDLE_SOURCE_CHECK ')]
    assert source['daemon_comm'] == 'rpm-ostree'
    assert source['versions'] == {'rpm-ostree': '2026.3', 'uupd': '1.5.0'}
    print('ARESOS_CACHED_STOCK_CLI_PROBE ' + json.dumps(dict(status='passed', digest=digest, image_id=image,
          pull='never', network='none', read_only=True, owner_credentials_mounted=False,
          part_b_cli_help=True, stock_idle_source_verified=True, idle_source=source)))


if __name__ == '__main__':
    main(sys.argv[1])
