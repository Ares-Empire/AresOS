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
    print('ARESOS_CACHED_STOCK_CLI_PROBE ' + json.dumps(dict(status='passed', digest=digest, image_id=image,
          pull='never', network='none', read_only=True, owner_credentials_mounted=False, part_b_cli_help=True)))


if __name__ == '__main__':
    main(sys.argv[1])
