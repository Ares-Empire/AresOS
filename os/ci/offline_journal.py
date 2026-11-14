"""Read a stopped guest's retained overlay, never the runner's own journal."""
import hashlib
import json
import os
import pathlib
import re
import stat
import subprocess
import time


POWER_KEY = 'b72ea4a2881545a0b50e200e55b9b071'
SHUTDOWN = '98268866d1d54a499c4e98921d93bc40'
JOURNAL_PATHS = r'^/(|var(|/log(|/journal(|/.*)))|ostree(|/deploy(|/[^/]+(|/var(|/log(|/journal(|/.*)))))))$'
PARTITION_WAIT_SECONDS = 10
PARTITION_POLL_SECONDS = 0.5


class OfflineJournalUnavailable(RuntimeError):
    """An unsupported kernel mount AND explicitly absent userspace tools."""


def check_offline_poweroff(disk, work, evidence, boot_id):
    try:
        summary = read_offline_journal(disk, work, evidence, boot_id)
        result = dict(status='passed', boot_id=boot_id, evidence='offline-poweroff.json')
        assert summary['boot_id'] == boot_id, summary
        label = f'PASS: offline logind power-key path for boot {boot_id}'
    except OfflineJournalUnavailable as error:
        # Only the two demonstrated host-reader limitations permit this gate.
        result = dict(status='REPORTED_NOT_BLOCKING_FIRST_HARDWARE_BOOT_GATE',
                      boot_id=boot_id, reason=str(error), procedure='docs/INSTALL.md section 7')
        label = f'REPORTED, NOT BLOCKING: logind power-key path requires first hardware boot; offline journal unreadable: {error}'
    (evidence / 'offline-poweroff-check.json').write_text(json.dumps(result, indent=2) + '\n')
    print(label, flush=True)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
            stream.write(f'\n**VM {evidence.name}: {label}**\n')
    return result


def assert_power_key_shutdown(records, boot_id):
    assert re.fullmatch(r'[0-9a-f]{32}', boot_id), boot_id
    assert records and all(record.get('_BOOT_ID') == boot_id for record in records), 'Wrong or empty offline boot'

    def find(predicate, after):
        matches = [record for record in records
                   if int(record['__MONOTONIC_TIMESTAMP']) >= after and predicate(record)]
        assert matches, 'Offline journal lacks the next required power-key/shutdown record'
        return min(matches, key=lambda record: int(record['__MONOTONIC_TIMESTAMP']))

    armed = find(lambda r: r.get('SYSLOG_IDENTIFIER') == 'aresos-ci'
                 and r.get('MESSAGE') == 'ARESOS_POWER_KEY_ARMED', 0)
    key = find(lambda r: r.get('_SYSTEMD_UNIT') == 'systemd-logind.service'
               and r.get('MESSAGE_ID') == POWER_KEY
               and r.get('MESSAGE') == 'Power key pressed short.', int(armed['__MONOTONIC_TIMESTAMP']))
    shutdown = find(lambda r: r.get('_SYSTEMD_UNIT') == 'systemd-logind.service'
                    and r.get('MESSAGE_ID') == SHUTDOWN
                    and r.get('SHUTDOWN') == 'power-off', int(key['__MONOTONIC_TIMESTAMP']))
    stopped = find(lambda r: r.get('_PID') == '1'
                   and r.get('UNIT') == 'systemd-logind.service'
                   and r.get('JOB_TYPE') == 'stop' and r.get('JOB_RESULT') == 'done'
                   and r.get('MESSAGE', '').startswith('Stopped systemd-logind.service'),
                   int(shutdown['__MONOTONIC_TIMESTAMP']))
    # The journal may relinquish /var before final poweroff.target. Require
    # orderly logind teardown here, and retain the final console/QMP checks.
    return dict(boot_id=boot_id, armed=armed, power_key=key, shutdown=shutdown, logind_stopped=stopped)


def block_node(path):
    """True once the kernel (devtmpfs, not udev) has created the partition's device node."""
    try:
        return stat.S_ISBLK(os.stat(path).st_mode)
    except FileNotFoundError:
        return False


def find_btrfs_root(nbd, run, commands, evidence):
    """The connected disk's one Btrfs partition, by the signature on the disk itself.

    lsblk's FSTYPE is udev's cached probe, which a runner image may fill late or
    never for nbd devices (run 43548237383: null on every partition after
    udevadm settle). lsblk only lists the partitions here (from sysfs; its FSTYPE
    column stays in the evidence for comparison); blkid -p reads each partition's
    superblock directly, bypassing udev and blkid's cache.
    """
    deadline = time.monotonic() + PARTITION_WAIT_SECONDS
    while True:
        layout = json.loads(run('lsblk', '--json', '--paths', '--output', 'NAME,FSTYPE,RO', nbd,
                                output='offline-disk-layout.json'))
        names = [part['name'] for part in layout['blockdevices'][0].get('children', [])]
        # blkid -p answers "nothing found" (exit 2) for a missing node too, so
        # never probe before every listed node exists.
        missing = [name for name in names if not block_node(name)]
        if names and not missing:
            break
        assert time.monotonic() < deadline, (f'Partition nodes of {nbd} not ready after {PARTITION_WAIT_SECONDS}s: '
                                             f'listed {names}, missing {missing}')
        time.sleep(PARTITION_POLL_SECONDS)
    types = {}
    for name in names:
        output = run('blkid', '-p', '-o', 'value', '-s', 'TYPE', name, required=False)
        # 0: signatures found (an unformatted partition may still print no TYPE);
        # 2 without a message: nothing found. 2 with one (such as "Permission
        # denied") or any other exit, such as 8 (ambivalent), is an error.
        probe = commands[-1]
        assert probe['returncode'] == 0 or (probe['returncode'] == 2 and not probe['stderr'].strip()), probe
        types[name] = output.decode().strip() or None
    (evidence / 'offline-disk-types.json').write_text(json.dumps(types, indent=2) + '\n')
    seen = ', '.join(f'{name}={kind or "none"}' for name, kind in types.items())
    print(f'Offline disk filesystem types (blkid -p): {seen}', flush=True)
    roots = [name for name, kind in types.items() if kind == 'btrfs']
    assert len(roots) == 1, f'Expected exactly one btrfs root on {nbd}; blkid -p saw {seen}'
    return roots[0]


def read_offline_journal(disk, work, evidence, boot_id):
    disk, work = pathlib.Path(disk).resolve(), pathlib.Path(work).resolve()
    assert disk.is_file() and disk.is_relative_to(work), disk
    assert re.fullmatch(r'[0-9a-f]{32}', boot_id), boot_id
    mountpoint = work / 'offline-root'
    mountpoint.mkdir(exist_ok=True)
    assert not mountpoint.is_mount(), 'Previous offline mount still active'
    nbd = '/dev/nbd0'
    assert not pathlib.Path('/sys/block/nbd0/pid').exists(), 'Runner NBD device already in use'
    commands = []

    def run(*args, output=None, required=True):
        try:
            result = subprocess.run(args, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired as error:
            commands.append(dict(argv=list(args), error=str(error), output=output))
            (evidence / 'offline-commands.json').write_text(json.dumps(commands, indent=2) + '\n')
            raise
        commands.append(dict(argv=list(args), returncode=result.returncode,
                             stderr=result.stderr.decode(errors='replace'), output=output))
        if output:
            (evidence / output).write_bytes(result.stdout)
        (evidence / 'offline-commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        if required:
            assert result.returncode == 0, commands[-1]
        if 'restore' in args:
            assert b'trying backup super' not in result.stdout + result.stderr, 'Btrfs primary tree unreadable'
        return result.stdout

    kernel_unsupported = False

    def require_reader(*args, output):
        try:
            run(*args, output=output, required=False)
        except FileNotFoundError as error:
            if kernel_unsupported and error.filename == 'podman':
                raise OfflineJournalUnavailable('Kernel Btrfs mount unsupported; host Podman is absent') from error
            raise
        command = commands[-1]
        # Do not classify timeouts, container startup failures or arbitrary 127
        # exits as absent tools. Require the runtime's missing-entrypoint error.
        absent = re.search(r'(stat /usr/bin/(?:btrfs|journalctl): no such file or directory|'
                           r'executable file [\"\']?/usr/bin/(?:btrfs|journalctl)[\"\']? not found)',
                           command['stderr'], re.I)
        if kernel_unsupported and command['returncode'] != 0 and absent:
            raise OfflineJournalUnavailable(f'Kernel Btrfs mount unsupported; userspace reader absent: {command}')
        assert command['returncode'] == 0, command

    connected = mounted = False
    try:
        run('qemu-nbd', '--read-only', '--format=qcow2', f'--connect={nbd}', str(disk))
        connected = True
        run('udevadm', 'settle')
        root = find_btrfs_root(nbd, run, commands, evidence)
        assert root.startswith(nbd + 'p') and root[len(nbd) + 1:].isdigit(), root
        assert run('blockdev', '--getro', root).strip() == b'1', 'Offline guest disk is writable'
        run('mount', '-t', 'btrfs', '-o', 'ro,nologreplay,subvolid=5', root, str(mountpoint), required=False)
        mount_error = commands[-1]['stderr']
        mounted = mountpoint.is_mount()
        if mounted:
            run('findmnt', '--json', '--mountpoint', str(mountpoint), output='offline-mount.json')
            source = mountpoint
        else:
            diagnostics = run('dmesg', '--color=never', output='offline-mount-dmesg.txt').decode(errors='replace')
            kernel_unsupported = bool(re.search(r"btrfs: Unknown parameter 'nologreplay'", diagnostics)
                                      or re.search(r"unknown filesystem type ['\"]btrfs['\"]", mount_error, re.I))
            # Use the image's Btrfs tools if the runner kernel cannot mount the
            # clone. restore reads the primary tree without modifying the disk;
            # never ignore errors or fall back to an older superblock/tree.
            source = work / f'offline-restore-{boot_id}'
            source.mkdir()
            container = ['podman', 'run', '--rm', '--network=none', '--read-only',
                         '--device', f'{root}:/dev/guest:r', '--volume', f'{source}:/export:rw',
                         '--entrypoint', '/usr/bin/btrfs', 'localhost/aresos:ci']
            require_reader(*container, 'version', output='offline-btrfs-version.txt')
            run(*container, 'check', '--readonly', '/dev/guest', output='offline-btrfs-check.txt')
            roots = run(*container, 'restore', '--list-roots', '/dev/guest', output='offline-btrfs-roots.txt')
            # The pinned builder's root subvolume is 256, also recorded in the
            # guest's clean remount output. A changed layout must fail explicitly.
            assert re.search(rb'tree key \(256 ROOT_ITEM ', roots), roots
            run(*container, 'restore', '--root', '256', '--path-regex', JOURNAL_PATHS,
                '/dev/guest', '/export', output='offline-btrfs-restore.txt')
        # OSTree keeps deployment /var outside its root tree. Search the Btrfs
        # top level without following links or guessing a deployment checksum.
        directories = run('find', str(source), '-type', 'd', '-path', '*/var/log/journal', '-print')
        journals = [pathlib.Path(line) for line in directories.decode().splitlines()
                    if any(pathlib.Path(line).rglob('*.journal'))]
        assert len(journals) == 1, f'Expected one persistent guest journal: {journals}'
        directory = journals[0]
        files = []
        for path in sorted(directory.rglob('*.journal*')):
            if path.is_file():
                with path.open('rb') as stream:
                    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                files.append(dict(path=str(path.relative_to(source)), bytes=path.stat().st_size, sha256=digest))
        (evidence / 'offline-journal-files.json').write_text(json.dumps(files, indent=2) + '\n')
        # Match the journal reader to the guest's systemd, independent of the
        # hosted runner's older journal format support.
        journalctl = ['podman', 'run', '--rm', '--network=none', '--read-only',
                      '--volume', f'{directory}:/guest-journal:ro', '--entrypoint', '/usr/bin/journalctl',
                      'localhost/aresos:ci', '--directory=/guest-journal', '--no-pager']
        require_reader(*journalctl, '--version', output='offline-journalctl-version.txt')
        run(*journalctl, '--verify', output='offline-verify.txt')
        boots = run(*journalctl, '--list-boots', output='offline-boots.txt')
        assert boot_id in boots.decode().split(), f'Expected boot {boot_id} absent from verified journal: {boots!r}'
        boot = [*journalctl, f'--boot={boot_id}', '--all']
        raw = run(*boot, '--output=json', output='offline-boot.jsonl')
        run(*boot, '--output=short-monotonic', output='offline-boot.txt')
        run(*boot, '--unit=systemd-logind.service', '--output=json', output='offline-logind.jsonl')
        summary = assert_power_key_shutdown([json.loads(line) for line in raw.splitlines()], boot_id)
        (evidence / 'offline-poweroff.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(f'Offline journal passed: boot {boot_id}, logind power key -> power-off -> orderly logind stop', flush=True)
        return summary
    finally:
        try:
            if mounted:
                run('umount', str(mountpoint))
        finally:
            if connected:
                run('qemu-nbd', '--disconnect', nbd)
