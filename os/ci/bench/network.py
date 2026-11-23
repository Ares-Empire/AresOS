"""Network choices shared by bench scripts and launchers."""
from enum import StrEnum
import re
from socket import if_nameindex


class Level(StrEnum):
    NONE = 'none'
    FAKE = 'fake'
    INTERNET = 'internet'


HOST = 'bench-stub.invalid'
STUB_PORT = 18443
NIC = 'bench-nic'
GUEST_RELAY = '10.0.2.2'
UID = '65534:65534'
PODMAN = '/usr/bin/podman'
IMAGE_ID = re.compile(r'sha256:[a-f0-9]{64}')


def level(value):
    try:
        return Level(value)
    except (TypeError, ValueError):
        raise ValueError('Invalid bench network level') from None


def require_loopback():
    # /sys can show a stale view after unshare. Query this process's namespace.
    if {name for _, name in if_nameindex()} != {'lo'}:
        raise ValueError('Bench requires an isolated loopback-only network namespace')


def qemu_nic(network):
    if network == Level.NONE:
        return ['-nic', 'none']
    options = f'user,model=virtio-net-pci,id={NIC}'
    if network == Level.FAKE:
        options += ',ipv6=off,ipv4=on'
    elif network != Level.INTERNET:
        raise ValueError('Unknown guest network')
    return ['-nic', options]


def offline_desk_command(network, image, argv):
    """Fixed offline desk options. The caller must submit the command to Bench.run."""
    if network not in (Level.NONE, Level.FAKE) or not IMAGE_ID.fullmatch(image) or not argv:
        raise ValueError('Desk requires an offline level, local image ID and fixed entrypoint')
    command = [
        PODMAN, 'run', '--rm', '--pull=never', '--network=none', '--http-proxy=false',
        '--dns=none', '--hosts-file=none', '--hostname=bench',
        '--user', UID, '--cap-drop=all', '--security-opt=no-new-privileges',
        '--read-only', '--read-only-tmpfs=false', '--image-volume=ignore',
        '--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=64m,mode=1777',
        '--cgroups=disabled', '--log-driver=none', '--timeout=120', '--systemd=false',
    ]
    if network == Level.FAKE:
        command += ['--add-host', f'{HOST}:127.0.0.1']
    return [*command, '--entrypoint=/usr/bin/env', image, '-i', 'PATH=/usr/bin:/bin', 'LC_ALL=C', *argv]
