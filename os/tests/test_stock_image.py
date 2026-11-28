"""The stock rewind (package 42, step 6): the host's fetch and checks, the live session's commands,
the harness wiring, and what the first stock boot must be."""
import contextlib
import copy
import hashlib
import json
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import stock_image
import two_disk_vm as td
import owner_vm
from guest_shell import syntax

BASE = 'sha256:ed93d2158a1bcba16b226bfb3ab6391446d11466646188c800b982d709435151'
# The pinned ISO's own image, read from its store on 2026-11-26.
ISO_IMAGE = 'sha256:98a6a6a31670cbfa005866c6d6de2e768409dd7cb9db25f324b20cc55294fb89'
ISO_INDEX = [dict(id='b69d47e20c1ea5a924ecb5cf3b345ac9e727927a68ec218b906738e65a0e3a23', digest=ISO_IMAGE,
                  names=['ghcr.io/ublue-os/bazzite-nvidia-open:stable'],
                  layer='9420e433a95bb31f537f6b5ec8231b0011b978c39223f9d25e3f751c64eef870')]
# R28 rehearsal 3 (44644689353) printed an OSC 3008 sequence directly before the payload digest.
PAYLOAD = ('\x1b[?2004hARESOS_ROOT> \x1b[?2004l\r\r\n\x1b]3008;start=00000000-0000-0000-0000-000000000000;type=command;'
           'user=root;hostname=localhost-live;pid=2960;cwd=/root\x1b\\{}\r\n\r\nARESOS_CMD_DONE:0\r\n')


def live():
    return next(item for item in json.loads((ROOT / 'os/manifest/installer-isos.json').read_text()) if item['kind'] == 'live')


def first_stock():
    """A real first stock boot after the previous ISO's installer: two serials of the laptop's commit."""
    folder = ROOT / 'os/tests/fixtures/keyboard'
    return dict(rpm=json.loads((folder / 'stock-two-rpm.json').read_text()),
                bootc=json.loads((folder / 'stock-two-bootc.json').read_text()))


def layout(directory, layers=(b'layer one', b'layer two'), config=b'{"architecture":"amd64"}'):
    """A small OCI layout as `skopeo copy ... oci:<directory>:stock` writes one."""
    directory = pathlib.Path(directory)
    blobs = directory / 'blobs/sha256'
    blobs.mkdir(parents=True)
    def blob(raw):
        name = hashlib.sha256(raw).hexdigest()
        (blobs / name).write_bytes(raw)
        return dict(digest='sha256:' + name, size=len(raw))
    manifest = json.dumps(dict(schemaVersion=2, config=dict(mediaType='application/vnd.oci.image.config.v1+json', **blob(config)),
        layers=[dict(mediaType='application/vnd.oci.image.layer.v1.tar+gzip', **blob(raw)) for raw in layers])).encode()
    described = blob(manifest)
    (directory / 'oci-layout').write_text('{"imageLayoutVersion": "1.0.0"}')
    (directory / 'index.json').write_text(json.dumps(dict(schemaVersion=2, manifests=[dict(
        mediaType='application/vnd.oci.image.manifest.v1+json', annotations={'org.opencontainers.image.ref.name': 'stock'}, **described)])))
    return described['digest']


class HostImageTest(unittest.TestCase):
    def setUp(self):
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        self.directory = pathlib.Path(stack.enter_context(tempfile.TemporaryDirectory(dir=ROOT / 'os/tests')))

    def test_base_is_the_digest_the_owner_tools_require_and_the_origin_they_accept(self):
        owner = (ROOT / 'os/owner-tools/owner.py').read_text()
        tools_base, = re.findall(r"^BASE = '(sha256:[0-9a-f]{64})'$", owner, re.M)
        upstream, = re.findall(r"^UPSTREAM = r'(.+)'$", owner, re.M)
        reference = stock_image.base()
        self.assertEqual(reference['digest'], tools_base)
        self.assertEqual(reference['digest'], BASE)
        self.assertEqual(reference['reference'], stock_image.NAME + '@' + BASE)
        self.assertTrue(re.fullmatch(upstream, stock_image.ORIGIN))
        self.assertEqual(stock_image.ORIGIN, 'ostree-image-signed:docker://ghcr.io/ublue-os/bazzite-nvidia-open:stable')
        # The laptop's own first stock boot is this origin and this commit.
        booted = next(d for d in first_stock()['rpm']['deployments'] if d['booted'])
        self.assertEqual((booted['container-image-reference'], booted['checksum']), (stock_image.ORIGIN, stock_image.RECORDED_COMMIT))
        recorded = json.loads((ROOT / 'os/manifest/ci/06e/full-1/switch/result.json').read_text())
        self.assertEqual(recorded['retained_stock_checksum'], stock_image.RECORDED_COMMIT)

    def test_base_refuses_a_tag_or_another_image(self):
        for reference in (stock_image.NAME + ':stable', stock_image.NAME + '@sha256:abc', 'ghcr.io/ublue-os/bazzite@' + BASE):
            path = self.directory / 'base.json'
            path.write_text(json.dumps(dict(reference=reference)))
            with self.subTest(reference=reference), self.assertRaisesRegex(AssertionError, 'by digest'):
                stock_image.base(path)

    def test_fetch_is_by_digest_without_credentials_and_never_by_tag(self):
        reference = stock_image.base()
        command = stock_image.fetch_command(reference, self.directory / 'image')
        self.assertEqual(command, ['skopeo', 'copy', '--src-no-creds', '--preserve-digests', '--retry-times', '3',
                                   'docker://ghcr.io/ublue-os/bazzite-nvidia-open@' + BASE, 'oci:' + str(self.directory / 'image') + ':stock'])
        self.assertNotIn(':stable', ' '.join(command))
        self.assertFalse(any('authfile' in part or 'creds=' in part for part in command))
        with self.assertRaises(AssertionError):
            stock_image.fetch_command(dict(reference, reference=stock_image.NAME + ':stable'), self.directory / 'image')
        with self.assertRaisesRegex(AssertionError, 'unexpected stock image path'):
            stock_image.fetch_command(reference, 'a:b')
        with patch.object(stock_image.subprocess, 'run', return_value=Mock(returncode=1, stderr='manifest unknown')) as run, \
                self.assertRaisesRegex(AssertionError, 'could not be fetched: manifest unknown'):
            stock_image.fetch(reference, self.directory / 'image')
        self.assertEqual(run.call_args.kwargs['timeout'], stock_image.FETCH_TIMEOUT)

    def test_every_blob_is_checked_against_the_one_pinned_manifest(self):
        digest = layout(self.directory / 'image')
        record = stock_image.verify(self.directory / 'image', digest)
        self.assertEqual((record['digest'], record['layers'], record['blobs']), (digest, 2, 4))
        blobs = self.directory / 'image/blobs/sha256'
        self.assertEqual(record['bytes'], sum(path.stat().st_size for path in blobs.iterdir()))

        def broken(name, change, message):
            target = self.directory / name
            digest = layout(target)
            change(target, digest)
            with self.subTest(case=name), self.assertRaisesRegex(AssertionError, message):
                stock_image.verify(target, digest)

        def layer(target):
            manifest = json.loads(next(p for p in (target / 'blobs/sha256').iterdir() if b'schemaVersion' in p.read_bytes()).read_bytes())
            return target / 'blobs/sha256' / manifest['layers'][0]['digest'].removeprefix('sha256:')

        def other_manifest(target, digest):
            index = json.loads((target / 'index.json').read_text())
            index['manifests'][0]['digest'] = 'sha256:' + '0' * 64
            (target / 'index.json').write_text(json.dumps(index))
        def second_manifest(target, digest):
            index = json.loads((target / 'index.json').read_text())
            index['manifests'].append(dict(index['manifests'][0]))
            (target / 'index.json').write_text(json.dumps(index))
        def changed_manifest(target, digest):
            path = target / 'blobs/sha256' / digest.removeprefix('sha256:')
            path.write_bytes(path.read_bytes().replace(b'layer.v1', b'layer.v2'))
        def flipped(target, digest):
            layer(target).write_bytes(b'layer 0ne')
        def truncated(target, digest):
            layer(target).write_bytes(b'layer')
        def linked(target, digest):
            path = layer(target)
            copy_ = target / 'elsewhere'
            copy_.write_bytes(path.read_bytes())
            path.unlink()
            path.symlink_to(copy_)
        broken('other-manifest', other_manifest, 'exactly the pinned manifest')
        broken('second-manifest', second_manifest, 'exactly the pinned manifest')
        broken('changed-manifest', changed_manifest, 'not the pinned one')
        broken('extra-blob', lambda target, digest: (target / 'blobs/sha256' / ('f' * 64)).write_bytes(b'extra'), 'missing or extra blobs')
        broken('missing-blob', lambda target, digest: layer(target).unlink(), 'missing or extra blobs')
        broken('flipped-bytes', flipped, 'differs from its digest')
        broken('truncated', truncated, 'wrong size')
        broken('symlink', linked, 'wrong size')
        broken('no-layout', lambda target, digest: (target / 'oci-layout').write_text('{}'), 'not an OCI layout')

    def test_prepare_fetches_checks_and_leaves_an_empty_sparse_store(self):
        share = self.directory / stock_image.SHARE
        digest = layout(self.directory / 'expected')
        pinned = dict(reference=stock_image.NAME + '@' + digest, name=stock_image.NAME, digest=digest)
        asked = []
        def fetch(reference, directory):
            asked.append((reference, directory))
            layout(directory)
        # Exactly the required room is enough; the test never depends on this machine's free space.
        with patch.object(stock_image, 'base', return_value=pinned), \
                patch.object(stock_image.shutil, 'disk_usage', return_value=Mock(free=stock_image.FREE_BYTES)):
            # The fetched bytes are not the pinned image: no store, nothing to share.
            with self.assertRaisesRegex(AssertionError, 'exactly the pinned manifest'):
                stock_image.prepare(share, fetch=lambda reference, directory: layout(directory, layers=(b'another image',)))
            self.assertFalse((share / 'store.raw').exists())
            record = stock_image.prepare(share, fetch=fetch)
            self.assertEqual(asked, [(pinned, share / 'image')])
            self.assertEqual((record['status'], record['digest'], record['credentials'], record['tag_trusted'], record['every_blob_checked']),
                             ('prepared', digest, 'none', False, True))
            self.assertEqual(record['source'], 'docker://' + stock_image.NAME + '@' + digest)
            self.assertEqual(record['free_bytes_before'], stock_image.FREE_BYTES)
            store = share / 'store.raw'
            self.assertEqual(store.stat().st_size, stock_image.STORE_BYTES)
            self.assertLess(store.stat().st_blocks * 512, 1024 * 1024)
            self.assertEqual(share.stat().st_mode & 0o777, 0o700)
            # A second live boot starts from nothing again.
            (share / 'stale').write_text('left over')
            stock_image.prepare(share, fetch=fetch)
            self.assertFalse((share / 'stale').exists())
        stock_image.drop_image(share)
        self.assertEqual([path.name for path in share.iterdir()], ['store.raw'])
        stock_image.discard(share)
        self.assertFalse(share.exists())

    def test_prepare_refuses_a_full_runner_before_fetching_and_other_paths(self):
        share = self.directory / stock_image.SHARE
        fetch = Mock()
        with patch.object(stock_image.shutil, 'disk_usage', return_value=Mock(free=stock_image.FREE_BYTES - 1)), \
                self.assertRaisesRegex(AssertionError, 'bytes free on the runner'):
            stock_image.prepare(share, fetch=fetch)
        fetch.assert_not_called()
        self.assertFalse(share.exists())
        for call in (stock_image.discard, stock_image.drop_image, stock_image.prepare):
            with self.subTest(call=call.__name__), self.assertRaisesRegex(AssertionError, 'unexpected stock share path'):
                call(self.directory / 'target.raw')
        link = self.directory / 'elsewhere' / stock_image.SHARE
        link.parent.mkdir()
        link.symlink_to(self.directory)
        with self.assertRaisesRegex(AssertionError, 'unexpected stock share path'):
            stock_image.discard(link)
        self.assertTrue(self.directory.exists())

    def test_the_iso_record_pins_its_own_image_and_any_other_stops(self):
        record = live()
        self.assertEqual(stock_image.embedded(record), dict(reference='ghcr.io/ublue-os/bazzite-nvidia-open:stable', digest=ISO_IMAGE))
        self.assertNotEqual(record['embedded_stock']['digest'], BASE)
        rows = stock_image.embedded_rows(ISO_INDEX)
        self.assertEqual(stock_image.check_embedded(rows, record), record['embedded_stock'])
        for name, other in (('base image', [dict(rows[0], digest=BASE)]), ('second image', rows * 2), ('none', []),
                            ('other name', [dict(rows[0], names=['ghcr.io/ublue-os/bazzite:stable'])]),
                            ('second name', [dict(rows[0], names=rows[0]['names'] + ['localhost/x:latest'])])):
            with self.subTest(case=name), self.assertRaisesRegex(AssertionError, 'requalify the ISO'):
                stock_image.check_embedded(other, record)
        for name, broken in (('missing', {k: v for k, v in record.items() if k != 'embedded_stock'}),
                             ('tag only', dict(record, embedded_stock=dict(reference=stock_image.INSTALLED))),
                             ('other name', dict(record, embedded_stock=dict(reference='x:stable', digest=ISO_IMAGE))),
                             ('no digest', dict(record, embedded_stock=dict(reference=stock_image.INSTALLED, digest='stable')))):
            with self.subTest(case=name), self.assertRaisesRegex(AssertionError, 'embedded stock'):
                stock_image.check_embedded(rows, broken)

    def test_the_embedded_reader_runs_as_one_command_on_the_real_index_shape(self):
        store = self.directory / 'storage'
        (store / 'overlay-images').mkdir(parents=True)
        (store / 'overlay-images/images.json').write_text(json.dumps(ISO_INDEX))
        command = stock_image.embedded_command(str(store))
        self.assertEqual(len(shlex.split(command)), 3)
        self.assertEqual(json.loads(subprocess.check_output(shlex.split(command), text=True)), stock_image.embedded_rows(ISO_INDEX))
        self.assertIn('/var/lib/containers/storage/overlay-images/images.json', stock_image.embedded_command())
        syntax('stock-embedded', td.sw.framed(stock_image.embedded_command()))


class GuestCommandTest(unittest.TestCase):
    COMMANDS = dict(share=stock_image.share_command, store=stock_image.store_command,
                    copy=stock_image.copy_command, release=stock_image.release_command)

    def test_commands_parse_and_never_reach_a_network_a_disk_or_a_deployment(self):
        for name, command in self.COMMANDS.items():
            source = command()
            with self.subTest(command=name):
                syntax('stock-' + name, source)
                for word in ('docker://', 'registry', 'curl', 'nmcli', 'ip link', '/dev/vd', '/dev/sd', '/dev/nvme', 'bootc', 'ostree',
                             'anaconda', 'liveinst', '/mnt/sys', 'authfile', 'auth.json'):
                    self.assertNotIn(word, source)
                # `! command` never stops a `set -e` script; every refusal here is an explicit exit.
                self.assertFalse(re.search(r'^\s*!', source, re.M))
                # Evidence lines never stop the run; the checks (test, mount, mkfs, skopeo) always can.
                for line in source.splitlines():
                    if line.endswith('|| true'):
                        self.assertTrue(line.startswith(('findmnt ', 'losetup --list ', 'df ', 'grep -c ')), line)
                    self.assertFalse(line.startswith(('test ', 'mount ', 'mkfs', 'modprobe ')) and '||' in line, line)

    def test_share_is_the_virtio_9p_tag_and_must_hold_the_image_and_the_empty_store(self):
        source = stock_image.share_command()
        self.assertTrue(source.startswith('set -e\n'))
        self.assertIn('mount -t 9p -o trans=virtio,version=9p2000.L,cache=none,msize=262144 aresos-stock /run/aresos-stock\n', source)
        self.assertIn('test -s /run/aresos-stock/image/index.json', source)
        self.assertIn(f'test "$(stat -c %s /run/aresos-stock/store.raw)" = {32 * 1024 ** 3}', source)
        arguments = stock_image.qemu_args(pathlib.Path('/runner/.work/installer/stock-share'))
        self.assertEqual(arguments, ['-fsdev', 'local,id=stock-image,path=/runner/.work/installer/stock-share,security_model=none',
                                     '-device', 'virtio-9p-pci,id=stock-image-device,fsdev=stock-image,mount_tag=aresos-stock,addr=0x8'])
        self.assertFalse(any(word in ' '.join(arguments) for word in ('-drive', 'blk', 'scsi', 'usb', 'ide')))
        with self.assertRaisesRegex(AssertionError, 'unexpected stock share path'):
            stock_image.qemu_args('/runner/a,readonly=off')

    def test_store_is_a_file_on_the_share_never_memory_and_replaces_the_isos_own(self):
        source = stock_image.store_command()
        lines = source.splitlines()
        self.assertEqual(lines[0], 'set -e')
        order = [next(i for i, line in enumerate(lines) if line.startswith(start)) for start in (
            'if mountpoint -q /var/lib/containers/storage', 'test -s /var/lib/containers/storage/overlay-images/images.json',
            'mkfs.ext4 -q -F -E nodiscard,lazy_itable_init=1,lazy_journal_init=1 /run/aresos-stock/store.raw', 'mount -o loop /run/aresos-stock/store.raw /var/lib/containers/storage',
            'test "$(findmnt -n -o FSTYPE /var/lib/containers/storage)" = ext4', 'test "$(lsblk -ndo TYPE "$device")" = loop',
            'test ! -e /var/lib/containers/storage/overlay-images',
            'install -d -m 1777 /var/lib/containers/storage/rehearsal-tmp',
            'mount --bind /var/lib/containers/storage/rehearsal-tmp /var/tmp',
            'test "$(stat -c %d:%i /var/tmp)"',
            'test "$storage" = \'/var/lib/containers/storage /run/containers/storage overlay\'')]
        self.assertEqual(order, sorted(order))
        self.assertNotIn('tmpfs', source)

    def test_copy_uses_the_local_layout_and_the_name_the_kickstart_installs(self):
        source = stock_image.copy_command()
        self.assertIn('TMPDIR="$scratch" skopeo --tmpdir "$scratch" --insecure-policy copy oci:/run/aresos-stock/image:stock '
                      'containers-storage:ghcr.io/ublue-os/bazzite-nvidia-open:stable > "$log" 2>&1', source)
        self.assertTrue(source.rstrip().endswith('echo STOCK_IMAGE_COPIED'))
        kickstart = 'ostreecontainer --url=ghcr.io/ublue-os/bazzite-nvidia-open:stable --transport=containers-storage'
        self.assertIn(stock_image.INSTALLED, kickstart)
        self.assertEqual(stock_image.fetch_command(stock_image.base(), '/w/image')[-1], 'oci:/w/image:stock')

    def test_copy_removes_runner_scratch_on_success_and_failure(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as scratch, \
                patch.object(stock_image, 'GUEST_SHARE', shlex.quote(scratch)):
            log_path = pathlib.Path(scratch) / 'copy.log'
            source = stock_image.copy_command().replace('/run/aresos-stock-copy.log', shlex.quote(str(log_path)))
            for expected in (0, 1):
                with self.subTest(exit_status=expected):
                    shell = f'''findmnt() {{ echo 9p; }}
df() {{ :; }}
skopeo() {{
    test "$1" = --tmpdir && test "$2" = "$TMPDIR" && test -d "$2" || return 2
    printf 'Copying blob fixture\\n' > "$2/blob"
    cat "$2/blob"
    printf '%s\\n' "$2"
    return {expected}
}}
'''
                    result = subprocess.run(['bash', '-c', shell + source], capture_output=True, text=True)
                    log = log_path.read_text().splitlines()
                    self.assertEqual(result.returncode, expected, result.stderr)
                    self.assertEqual(log[0], 'Copying blob fixture')
                    self.assertEqual(pathlib.Path(log[1]).parent, pathlib.Path(scratch))
                    self.assertFalse(pathlib.Path(log[1]).exists())

    def test_release_never_stops_the_run_and_reports_a_lazy_unmount(self):
        source = stock_image.release_command()
        self.assertNotIn('set -e', source)
        self.assertNotIn('exit', source)
        self.assertIn('for mount in /var/tmp /var/lib/containers/storage /run/aresos-stock;', source)
        self.assertTrue(source.rstrip().endswith('echo STOCK_SHARE_RELEASED'))
        guest = Mock()
        for output, lazy in (('STOCK_SHARE_RELEASED', False), ('STOCK_LAZY_UNMOUNT /run/aresos-stock\nSTOCK_SHARE_RELEASED', True)):
            guest.command.return_value = output
            with patch.object(td, 'save') as save:
                td.release_stock(guest, 'protected-second-install')
            save.assert_called_once_with('protected-second-install-stock-release', dict(status='released', lazy=lazy))
        self.assertEqual(guest.command.call_args.args[0], 'protected-second-install-stock-release')

    def test_the_printed_digest_survives_the_live_shells_terminal_sequences(self):
        self.assertEqual(stock_image.printed_digest(PAYLOAD.format(BASE)), BASE)
        self.assertEqual(stock_image.printed_digest(PAYLOAD.format(ISO_IMAGE)), ISO_IMAGE)
        for output in (PAYLOAD.format(''), PAYLOAD.format(BASE + '\r\n' + ISO_IMAGE), PAYLOAD.format(BASE[:-1]), PAYLOAD.format(BASE + '0')):
            with self.subTest(output=output[-90:]), self.assertRaisesRegex(AssertionError, 'missing or ambiguous'):
                stock_image.printed_digest(output)


class HarnessTest(unittest.TestCase):
    def setUp(self):
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        self.directory = pathlib.Path(stack.enter_context(tempfile.TemporaryDirectory(dir=ROOT / 'os/tests')))
        stack.enter_context(patch.object(td, 'EVIDENCE', self.directory))
        stack.enter_context(patch.object(td, 'WORK', self.directory))
        self.host = dict(status='prepared', source='docker://' + stock_image.NAME + '@' + BASE, credentials='none',
                         tag_trusted=False, every_blob_checked=True, digest=BASE, layers=128, blobs=130, bytes=5634826157)

    def test_only_a_live_boot_with_a_prepared_image_gets_the_share(self):
        share = self.directory / stock_image.SHARE
        for kind in (td.Guest, owner_vm.Guest):
            guest = object.__new__(kind)
            guest.owner_auth_directory = self.directory / 'auth'
            for mode in ('live', 'installed', 'marker', 'marker-baseline', 'marker-detached'):
                guest.mode = mode
                with self.subTest(kind=kind.__module__, mode=mode):
                    with patch.object(kind, 'stock_share', None):
                        self.assertEqual(guest.stock_args(), [])
                        self.assertNotIn('stock', ' '.join(guest.peripheral_args()))
                    with patch.object(kind, 'stock_share', share):
                        joined = ' '.join(guest.peripheral_args())
                        self.assertEqual('mount_tag=aresos-stock' in joined, mode == 'live')
                        self.assertEqual(joined.count('addr=0x8'), mode == 'live')
        # The owner's route still has no credential share, in any mode.
        guest = object.__new__(owner_vm.Guest)
        guest.mode = 'live'
        with patch.object(owner_vm.Guest, 'stock_share', share):
            joined = ' '.join(guest.peripheral_args())
        self.assertNotIn('owner-auth', joined)
        self.assertEqual(joined.count('-fsdev'), 1)
        self.assertIn('addr=0x7', joined)

    def test_the_share_is_recorded_as_a_pci_device_at_its_slot_and_never_a_block_device(self):
        for name in ('protected.raw', 'target.raw', td.LIVE['filename']):
            (self.directory / name).write_bytes(b'fixture')
        guest = object.__new__(td.Guest)
        guest.mode, guest.order, guest.boot_number = 'live', 'protected-second', 2
        def hardware(slot=8, block=False):
            pci = [dict(bus=0, devices=[dict(slot=2, function=0, qdev_id='target-device'), dict(slot=3, function=0, qdev_id='protected-device'),
                                        dict(slot=slot, function=0, qdev_id='stock-image-device'),
                                        dict(slot=31, function=2, qdev_id='', class_info={'class': 0x0106})])]
            blocks = [dict(device='target', inserted=dict(file=str(self.directory / 'target.raw'))),
                      dict(device='protected', inserted=dict(file=str(self.directory / 'protected.raw'))),
                      dict(device='installer-cd', qdev='installer-cd-device', inserted=dict(file=str(self.directory / td.LIVE['filename'])))]
            if block:
                blocks.append(dict(device='stock-image', inserted=dict(file=str(self.directory / 'store.raw'))))
            return [pci, blocks]
        guest.monitor = Mock()
        with patch.object(td.Guest, 'stock_share', self.directory / stock_image.SHARE):
            guest.monitor.command.side_effect = hardware()
            observed = guest.device_inventory()
            self.assertIn(dict(key='pci:00:08.0', qdev_id='stock-image-device', evidence='QMP query-pci'), observed['attached'])
            guest.monitor.command.side_effect = hardware(slot=9)
            with self.assertRaisesRegex(AssertionError, 'stock share PCI address differs'):
                guest.device_inventory()
            guest.monitor.command.side_effect = hardware(block=True)
            with self.assertRaisesRegex(AssertionError, 'must not be a block device'):
                guest.device_inventory()

    def test_the_host_share_lasts_exactly_one_live_boot_also_when_it_fails(self):
        with patch.object(stock_image, 'prepare', return_value=self.host) as prepare, patch.object(stock_image, 'discard') as discard:
            with self.assertRaisesRegex(RuntimeError, 'live boot failed'):
                with td.stock_share():
                    self.assertEqual(td.Guest.stock_share, self.directory / stock_image.SHARE)
                    self.assertEqual(json.loads((self.directory / 'stock-image-host.json').read_text()), self.host)
                    raise RuntimeError('live boot failed')
            self.assertIsNone(td.Guest.stock_share)
            prepare.assert_called_once_with(self.directory / stock_image.SHARE)
            discard.assert_called_once_with(self.directory / stock_image.SHARE)
        # A failed fetch can leave a partial layout. Discard it without constructing a guest.
        share = self.directory / stock_image.SHARE
        share.mkdir()
        (share / 'partial').touch()
        with patch.object(stock_image, 'prepare', side_effect=AssertionError('STOP: a fetched blob differs from its digest')), \
                patch.object(td, 'Guest') as guest, self.assertRaisesRegex(AssertionError, 'differs from its digest'):
            td.install(Mock(), 'password', 'hash')
        guest.assert_not_called()
        self.assertFalse(share.exists())

    def guest(self, rows=None):
        guest = Mock()
        guest.mode, guest.stock_share = 'live', self.directory / stock_image.SHARE
        guest.capture_json.return_value = stock_image.embedded_rows(ISO_INDEX) if rows is None else rows
        return guest

    def test_substitution_checks_the_isos_own_image_first_then_share_store_copy(self):
        (self.directory / 'stock-image-host.json').write_text(json.dumps(self.host))
        guest = self.guest()
        self.assertEqual(td.substitute_stock(guest, 'protected-second-install'), self.host)
        self.assertEqual(guest.capture_json.call_args.args[0], 'protected-second-install-stock-embedded')
        self.assertEqual([(call.args[0], call.args[1]) for call in guest.command.call_args_list], [
            ('protected-second-install-stock-share', stock_image.share_command()),
            ('protected-second-install-stock-store', stock_image.store_command()),
            ('protected-second-install-stock-copy', stock_image.copy_command())])
        self.assertEqual(guest.command.call_args_list[-1].kwargs, dict(timeout=stock_image.COPY_TIMEOUT))
        # Another ISO image than the recorded one: nothing is mounted or copied.
        guest = self.guest([dict(names=[stock_image.INSTALLED], digest=BASE)])
        with self.assertRaisesRegex(AssertionError, 'requalify the ISO'):
            td.substitute_stock(guest, 'live')
        guest.command.assert_not_called()
        for mode, share in (('installed', self.directory), ('live', None)):
            guest = self.guest()
            guest.mode, guest.stock_share = mode, share
            with self.subTest(mode=mode), self.assertRaisesRegex(AssertionError, 'no host-prepared stock image'):
                td.substitute_stock(guest, 'live')
            guest.capture_json.assert_not_called()

    def test_the_installer_only_runs_on_the_base_image_and_the_record_says_what_changed(self):
        record = stock_image.rewind(live(), self.host, BASE)
        self.assertEqual(record['iso']['embedded']['digest'], ISO_IMAGE)
        self.assertEqual(record['iso']['sha256'], live()['sha256'])
        self.assertEqual((record['substituted']['reference'], record['substituted']['digest']), (stock_image.INSTALLED, BASE))
        self.assertTrue(record['design'].startswith('a: '))
        self.assertEqual((record['installer_files_changed'], record['installed_system_online']), (False, False))
        for observed, host in ((ISO_IMAGE, self.host), (BASE, dict(self.host, digest=ISO_IMAGE))):
            with self.assertRaisesRegex(AssertionError, 'not the base image'):
                stock_image.rewind(live(), host, observed)
        # In live_inventory the substitution comes before the disks are read and the payload is checked,
        # and the fetched layout is dropped only after the store proved the image.
        source = pathlib.Path(td.__file__).read_text()
        body = source[source.index('def live_inventory(guest, stage):'):source.index('@contextlib.contextmanager\ndef stock_share')]
        marks = [body.index(text) for text in ('substitute_stock(guest, stage)', "stage + '-disks'", "stage + '-payload'",
                 'test "$digest" = \'{digest}\'', "save('stock-rewind', stock_image.rewind(LIVE, host, stock_image.printed_digest(output)))",
                 'stock_image.drop_image(guest.stock_share)', "stage + '-cli'")]
        self.assertEqual(marks, sorted(marks))

    def test_live_inventory_substitutes_first_and_fails_closed_on_any_other_payload(self):
        gib = 1024 ** 3
        disks = dict(blockdevices=[dict(name='loop1', type='loop', size=32 * gib, serial=None, mountpoints=['/var/lib/containers/storage']),
                                   dict(name='vda', type='disk', size=49 * gib, serial='CRUCIAL-TARGET', mountpoints=[]),
                                   dict(name='vdb', type='disk', size=50 * gib, serial='MICRON-KEEP', mountpoints=[])])
        help_text = 'usage: anaconda\n  --kickstart KICKSTART\n      Not supported for live installations.\n  --help\n'
        share = self.directory / stock_image.SHARE

        def run(payload):
            (self.directory / 'stock-rewind.json').unlink(missing_ok=True)
            stock_image.discard(share)
            layout(share / 'image')
            (self.directory / 'stock-image-host.json').write_text(json.dumps(self.host))
            calls = []
            guest = Mock()
            guest.mode, guest.stock_share = 'live', share
            def capture(name, command):
                calls.append(name)
                return (stock_image.embedded_rows(ISO_INDEX) if name.endswith('-stock-embedded') else disks if name.endswith('-disks') else [])
            def command(name, script, timeout=900):
                calls.append(name)
                if name.endswith('-payload'):
                    self.assertIn("test \"$digest\" = '" + BASE + "'", script)
                    if isinstance(payload, Exception):
                        raise payload
                    return PAYLOAD.format(payload)
                return help_text if name.endswith('-cli') else ''
            guest.capture_json.side_effect, guest.command.side_effect = capture, command
            # Outside the owner packages the signature is read in the guest; the rest is the same.
            environment = {k: v for k, v in td.os.environ.items() if k != 'REHEARSAL_PACKAGE'}
            with patch.dict(td.os.environ, environment, clear=True):
                try:
                    return calls, td.live_inventory(guest, 'live')
                except AssertionError as error:
                    return calls, error

        calls, result = run(BASE)
        self.assertEqual(result, ('vdb', 'vda'))
        self.assertEqual(calls, ['live-release-signature', 'live-stock-embedded', 'live-stock-share', 'live-stock-store', 'live-stock-copy',
                                 'live-disks', 'live-payload', 'live-cli', 'live-bls-export-preflight'])
        record = json.loads((self.directory / 'stock-rewind.json').read_text())
        self.assertEqual((record['status'], record['substituted']['digest'], record['iso']['embedded']['digest']),
                         ('substituted; first stock boot pending', BASE, ISO_IMAGE))
        # The fetched layout goes once the store has proven the image; the store stays for the installer.
        self.assertFalse((share / 'image').exists())
        for name, payload in (('guest check failed', AssertionError('Guest command failed: live-payload, exit 1')), ('iso image printed', ISO_IMAGE)):
            calls, result = run(payload)
            with self.subTest(case=name):
                self.assertIsInstance(result, AssertionError)
                self.assertEqual(calls[-1], 'live-payload')
                self.assertFalse((self.directory / 'stock-rewind.json').exists())
                self.assertTrue((share / 'image').exists())

    def test_a_loop_file_is_no_disk_for_the_harness(self):
        # Rehearsal 3's live lsblk, plus the store as the live session shows it.
        gib = 1024 ** 3
        layout = dict(blockdevices=[
            dict(name='loop0', type='loop', size=8658407424, serial=None, fstype='squashfs', mountpoints=['/run/rootfsbase']),
            dict(name='loop1', type='loop', size=32 * gib, serial=None, fstype='ext4', mountpoints=['/var/lib/containers/storage']),
            dict(name='sr0', type='rom', size=9088845824, serial='QM00001', fstype='iso9660', mountpoints=['/run/initramfs/live']),
            dict(name='zram0', type='disk', size=3094347776, serial=None, fstype='swap', mountpoints=['[SWAP]']),
            dict(name='vda', type='disk', size=49 * gib, serial='CRUCIAL-TARGET', fstype=None, mountpoints=[]),
            dict(name='vdb', type='disk', size=50 * gib, serial='MICRON-KEEP', fstype=None, mountpoints=[]),
            dict(name='vdb1', type='part', size=272629760, serial=None, fstype='vfat', mountpoints=[])])
        self.assertEqual(td.disk_names(layout), ('vdb', 'vda'))

    def booted(self, change=lambda snapshot: None):
        (self.directory / 'stock-rewind.json').write_text(json.dumps(stock_image.rewind(live(), self.host, BASE)))
        snapshot = copy.deepcopy(first_stock())
        change(snapshot)
        return td.stock_rewind_booted(snapshot)

    def test_first_stock_boot_is_the_base_image_with_the_laptops_origin_and_nothing_else(self):
        result = self.booted()
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['booted'], dict(digest=BASE, origin=stock_image.ORIGIN, checksum=stock_image.RECORDED_COMMIT, serial=1))
        self.assertEqual([(d['serial'], d['booted'], d['pinned'], d['digest']) for d in result['deployments']],
                         [(1, True, False, BASE), (0, False, False, BASE)])
        self.assertEqual(result['stock_commit'], dict(observed=stock_image.RECORDED_COMMIT, recorded=stock_image.RECORDED_COMMIT, equal=True))
        self.assertEqual(json.loads((self.directory / 'stock-rewind.json').read_text()), result)
        self.assertEqual(result['iso']['embedded']['digest'], ISO_IMAGE)
        single = self.booted(lambda s: (s['rpm'].update(deployments=s['rpm']['deployments'][:1]), s['bootc']['status'].update(rollback=None)))
        self.assertEqual(len(single['deployments']), 1)

        def rows(snapshot):
            return snapshot['rpm']['deployments']
        cases = dict(
            iso_image=(lambda s: s['bootc']['status']['booted']['image'].update(imageDigest=ISO_IMAGE), 'not the base image'),
            row_of_iso_image=(lambda s: rows(s)[1].update({'container-image-reference-digest': ISO_IMAGE}), 'not the base image'),
            other_commit_row=(lambda s: rows(s)[1].update(checksum='c' * 64), 'not the base image'),
            digest_origin=(lambda s: [d.update({'container-image-reference': 'ostree-unverified-registry:' + stock_image.NAME + '@' + BASE})
                                      for d in rows(s)], "not the laptop's"),
            installer_origin=(lambda s: rows(s)[0].update({'container-image-reference': 'ostree-unverified-image:containers-storage:'
                                                           + stock_image.INSTALLED}), "not the laptop's"),
            pinned=(lambda s: rows(s)[0].update(pinned=True), 'staged or pinned'),
            staged_row=(lambda s: rows(s)[1].update(staged=True), 'staged or pinned'),
            staged=(lambda s: s['bootc']['status'].update(staged=dict(image=None)), 'transaction, a staged deployment or a queued rollback'),
            queued=(lambda s: s['bootc']['status'].update(rollbackQueued=True), 'transaction, a staged deployment or a queued rollback'),
            transaction=(lambda s: s['rpm'].update(transaction=['upgrade', 'client', '/path']), 'transaction, a staged deployment or a queued rollback'),
            third=(lambda s: rows(s).append(dict(rows(s)[1], serial=2)), 'other deployments'))
        for name, (change, message) in cases.items():
            with self.subTest(case=name), self.assertRaisesRegex(AssertionError, message):
                self.booted(change)

    def test_another_commit_of_the_base_image_is_recorded_loudly_but_does_not_stop(self):
        def other(snapshot):
            for row in snapshot['rpm']['deployments']:
                row['checksum'] = 'b' * 64
            for name in ('booted', 'rollback'):
                snapshot['bootc']['status'][name]['ostree']['checksum'] = 'b' * 64
        with patch('builtins.print') as shown:
            result = self.booted(other)
        self.assertEqual(result['stock_commit'], dict(observed='b' * 64, recorded=stock_image.RECORDED_COMMIT, equal=False))
        self.assertIn('STOCK COMMIT DIFFERS FROM THE RECORDED ONE', shown.call_args.args[0])

    def test_first_stock_boot_refuses_disagreement_between_the_status_tools(self):
        for name in ('booted', 'rollback'):
            changes = (
                lambda slot: slot['ostree'].update(checksum='b' * 64),
                lambda slot: slot['ostree'].update(deploySerial=3),
                lambda slot: slot['ostree'].update(stateroot='other'),
                lambda slot: slot['image']['image'].update(image=stock_image.NAME + ':other'),
                lambda slot: slot.update(pinned=True),
            )
            for i, change in enumerate(changes):
                with self.subTest(slot=name, case=i), self.assertRaisesRegex(AssertionError, f'{name} disagreement'):
                    self.booted(lambda s: change(s['bootc']['status'][name]))
        with self.assertRaisesRegex(AssertionError, 'rollback disagreement'):
            self.booted(lambda s: s['bootc']['status'].update(rollback=None))
        with self.assertRaisesRegex(AssertionError, 'rollback disagreement'):
            self.booted(lambda s: s['bootc']['status']['rollback']['image'].update(imageDigest=ISO_IMAGE))

    def test_a_first_boot_without_the_live_sessions_record_stops(self):
        with self.assertRaisesRegex(AssertionError, 'no stock rewind record'):
            td.stock_rewind_booted(first_stock())
        (self.directory / 'stock-rewind.json').write_text(json.dumps(dict(self.booted())))
        with self.assertRaises(AssertionError):
            td.stock_rewind_booted(first_stock())

    def test_the_owner_route_checks_the_first_stock_boot_before_anything_else_happens(self):
        source = pathlib.Path(owner_vm.__file__).read_text()
        body = source[source.index('def prepare_and_switch('):source.index('def qualification(')]
        marks = [body.index(text) for text in ('td.install(audit, password, hashed)', "kb.deployment_snapshot(guest, 'offline-first-stock')",
                 'td.stock_rewind_booted(raw)', "guest.assert_offline('offline-first-stock-link')", "td.restore_windows_order('offline-tools-roundtrip')",
                 "media.attach(guest, 'tools-stock')", "guest.monitor.command('set_link', {'name': 'owner-net', 'up': True})")]
        self.assertEqual(marks, sorted(marks))
        # No harness step raises the installed guest's link before the route's own network step.
        self.assertEqual(source.count("'up': True}"), 1)
        self.assertEqual(body.count('Guest.network_up = True'), 1)


class InspectionTest(unittest.TestCase):
    def test_inspection_pins_the_isos_image_and_frees_the_extracted_squashfs(self):
        source = (ROOT / 'os/ci/installer_inspect.py').read_text()
        marks = [source.index(text) for text in (
            "embedded = stock_image.check_embedded(stock_image.embedded_rows(json.loads(raw)), live)",
            "assert embedded, 'STOP: the live ISO carries no stock image index'", "'embedded-stock.json'", 'squash.unlink()')]
        self.assertEqual(marks, sorted(marks))
        self.assertIn("'var/lib/containers/storage/overlay-images/images.json')", source)
        # Nothing else reads the extracted image.
        users = [path.name for path in (ROOT / 'os/ci').glob('*.py') if 'squashfs.img' in path.read_text()]
        self.assertEqual(users, ['installer_inspect.py'])

    def test_the_cached_stock_probe_reads_the_substituted_store(self):
        probe = (ROOT / 'os/ci/stock_probe.py').read_text()
        self.assertIn("/var/lib/containers/storage/overlay-images/images.json", probe)
        self.assertIn("'--pull=never', '--network=none'", probe)
        source = pathlib.Path(td.__file__).read_text()
        body = source[source.index('def live_probe(audit):'):source.index('\ndef main():')]
        marks = [body.index(text) for text in ('with stock_share():', "live_inventory(guest, 'live')", 'stock_recipe_probe(guest)',
                                                "release_stock(guest, 'live')", "guest.poweroff('live-ui-probe')")]
        self.assertEqual(marks, sorted(marks))


if __name__ == '__main__':
    unittest.main()
