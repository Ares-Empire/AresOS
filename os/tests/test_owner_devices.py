"""Real disk/media helpers; no device, mount, privilege or credential access."""
import copy
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_owner_tools as common

owner, media, ROOT = common.owner, common.module('media'), common.ROOT
FIXTURES = ROOT/'os/tests/fixtures/owner-tools'
sys.path.insert(0,str(ROOT/'os/ci'))


class FixtureHost(owner.Host):
    def __init__(self, tree, usb_root=None):
        super().__init__()
        self.tree, self.usb_root = tree, usb_root
        if usb_root is not None:
            for disk in tree['blockdevices']:
                for volume in disk.get('children', []):
                    if volume.get('label') == 'ARESTOOLS': volume['mountpoints'] = [str(usb_root)]

    def read(self, *command, **unused):
        self.trace.append(dict(command=list(command), mutation=False))
        if command[0] == 'lsblk':
            assert '--tree' in command, command
            return json.dumps(self.tree)
        if command[0] == 'findmnt':
            assert command[1:3] == ('--json', '--list'), command
            selector, path = command[3:5]
            if selector == '--target':
                row = dict(source='/dev/sdb1', target=str(self.usb_root), fstype='exfat')
            else:
                source = {'/boot/efi':'/dev/nvme0n1p1','/boot':'/dev/nvme0n1p2','/sysroot':'/dev/nvme0n1p3[/root]'}[path]
                row = dict(source=source, target=path, fstype='vfat' if path == '/boot/efi' else 'btrfs')
            return json.dumps(dict(filesystems=[row]))
        if command[0] == 'sfdisk':
            return json.dumps(dict(partitiontable=dict(label='gpt',device=command[-1],partitions=[])))
        if command == ('efibootmgr','-v'):
            from owner_devices import fixture_firmware
            return fixture_firmware('10000001-1111-2222-3333-444444444444',0x12c000)
        raise AssertionError('Unknown fixture query: '+repr(command))

    def mutate(self, *command, **unused):
        raise AssertionError('Mutation prohibited: '+repr(command))


def fixture(name='storage-tree.json'):
    return json.loads((FIXTURES/name).read_text())


class DevicesTest(unittest.TestCase):
    def setUp(self):
        # Match the shipped at launcher's -B flag; imports must not write into
        # the bundle before either a refusal or its checked private copy.
        bytecode=patch.object(sys,'dont_write_bytecode',True)
        bytecode.start(); self.addCleanup(bytecode.stop)

    def checked_refusal(self, host, function, message):
        before = copy.deepcopy(host.tree)
        with patch('subprocess.run') as run, patch('subprocess.Popen') as popen, \
             patch('subprocess.check_call') as call, self.assertRaisesRegex(owner.Stop, message):
            function()
        run.assert_not_called(); popen.assert_not_called(); call.assert_not_called()
        self.assertEqual(host.tree, before)
        self.assertFalse(any(row['mutation'] for row in host.trace))

    def test_real_helpers_accept_partitioned_tree_and_inherit_usb_identity(self):
        host = FixtureHost(fixture())
        result = owner.disk_record(host, dict(target='TARGET',protected='KEEP'))
        self.assertEqual(result['esp_guid'], '10000001-1111-2222-3333-444444444444')
        found = media.find(host, owner.require)
        self.assertEqual(found['disk']['path'], '/dev/sdb')
        self.assertEqual(found['volume']['path'], '/dev/sdb1')
        self.assertIsNone(found['volume']['tran'])
        self.assertFalse(found['volume']['rm'])
        self.assertFalse(any(row['mutation'] for row in host.trace))

    def test_both_real_helpers_refuse_flat_json_clearly(self):
        for reader in (lambda h:owner.disk_record(h,dict(target='TARGET',protected='KEEP')),
                       lambda h:media.find(h,owner.require)):
            host = FixtureHost(fixture('storage-flat.json'))
            self.checked_refusal(host, lambda:reader(host), 'Unexpected lsblk tree shape')

    def test_malformed_and_multiply_parented_nodes_refuse_before_other_reads(self):
        tree = fixture()
        duplicate = copy.deepcopy(tree); duplicate['blockdevices'][1]['children'].append(copy.deepcopy(tree['blockdevices'][0]['children'][0]))
        children = copy.deepcopy(tree); children['blockdevices'][0]['children'] = {}
        mounts = copy.deepcopy(tree); del mounts['blockdevices'][1]['children'][0]['mountpoints']
        for value in ({}, dict(blockdevices={}), dict(blockdevices=[None]), duplicate, children, mounts):
            for reader in (lambda h:owner.disk_record(h,dict(target='TARGET',protected='KEEP')),
                           lambda h:media.find(h,owner.require)):
                host = FixtureHost(value)
                self.checked_refusal(host, lambda:reader(host), 'Unexpected lsblk tree shape')
                self.assertEqual([t['command'][0] for t in host.trace], ['lsblk'])

    def test_protected_mounted_child_and_two_labels_refuse_install_without_writes(self):
        mounted = fixture(); mounted['blockdevices'][1]['children'][0]['mountpoints'] = ['/run/media/Windows']
        labels = fixture(); labels['blockdevices'][0]['children'][2].update(label='ARESTOOLS',fstype='exfat',uuid='second')
        for tree, message in ((mounted,'Protected disk is mounted'),(labels,'Several ARESTOOLS labels'),
                              (fixture('storage-flat.json'),'Unexpected lsblk tree shape')):
            with self.subTest(message=message), tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as temporary:
                root = pathlib.Path(temporary); usb=root/'usb'; usb.mkdir()
                payload = usb/'ares-tools'; common.fixture_bundle(payload)
                home = root/'home'; host=FixtureHost(tree,usb)
                before = {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
                with patch.object(owner,'HOME',home), patch.object(owner,'Host',return_value=host), \
                     patch.object(owner.sys.stdin,'isatty',return_value=True), patch('builtins.input',side_effect=['TARGET','KEEP']):
                    self.checked_refusal(host,lambda:owner.install(payload),message)
                self.assertFalse(home.exists())
                self.assertEqual(before,{p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_install_reaches_private_copy_with_real_tree_and_both_helpers(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as temporary:
            root=pathlib.Path(temporary); usb=root/'usb'; usb.mkdir()
            payload=usb/'ares-tools'; fingerprint=common.fixture_bundle(payload)
            home=root/'home'; host=FixtureHost(fixture(),usb)
            with patch.object(owner,'HOME',home), patch.object(owner,'Host',return_value=host), \
                 patch.object(owner.sys.stdin,'isatty',return_value=True), patch('builtins.input',side_effect=['TARGET','KEEP']),common.private_metadata(home):
                result=owner.install(payload)
            self.assertIn('manifest SHA256 '+fingerprint,result)
            self.assertEqual(owner.checked_bundle(home/'tools'),fingerprint)
            self.assertEqual(json.loads((home/'records/disks.json').read_text()),dict(target='TARGET',protected='KEEP'))

    def test_findmnt_nested_ambiguous_or_wrong_target_refuses_without_mutation(self):
        good=dict(source='/dev/nvme0n1p1',target='/boot/efi',fstype='vfat')
        for value in ({},dict(filesystems=[]),dict(filesystems=[good,good]),
                      dict(filesystems=[dict(good,children=[good])]),dict(filesystems=[dict(good,target='/other')])):
            host=FixtureHost(fixture())
            with patch.object(host,'json',return_value=value):
                self.checked_refusal(host,lambda:owner.mount_record(host,'--mountpoint','/boot/efi'),'Unexpected findmnt list shape')


if __name__ == '__main__': unittest.main()
