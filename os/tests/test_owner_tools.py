import copy
import contextlib
import importlib.util
import json
import pathlib
import os
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'os/owner-tools' / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


owner = module('owner')
bundle = module('bundle')


@contextlib.contextmanager
def private_metadata(root):
    """POSIX metadata model for private ordinary-file fixtures on DrvFS.

    Bytes, paths, no-follow behaviour, atomic renames and fsync are real. Only
    the mode/owner returned for this explicitly declared private tree change.
    Permission-refusal tests exercise the production predicate separately.
    """
    root=pathlib.Path(root).absolute(); original=pathlib.Path.stat
    def metadata(path,*args,**kwargs):
        info=original(path,*args,**kwargs)
        if path.is_absolute() and path.is_relative_to(root) and not stat.S_ISLNK(info.st_mode):
            values={name:getattr(info,name) for name in dir(info) if name.startswith('st_')}
            values.update(st_uid=os.geteuid(),st_mode=stat.S_IFMT(info.st_mode) | (0o700 if stat.S_ISDIR(info.st_mode) or path.name=='at' else 0o600))
            return SimpleNamespace(**values)
        return info
    with patch.object(pathlib.Path,'stat',metadata): yield


def stock():
    folder = ROOT / 'os/tests/fixtures/keyboard'
    return dict(rpm=json.loads((folder / 'stock-two-rpm.json').read_text()),
                bootc=json.loads((folder / 'stock-two-bootc.json').read_text()))


class RefusalTest(unittest.TestCase):
    def refuse(self, function, *args):
        # Every subprocess mutation interface is trapped, even if a future
        # preflight accidentally grows a command. No root path is touched.
        with patch('subprocess.run') as run, patch('subprocess.check_call') as call, \
                patch('subprocess.Popen') as popen, self.assertRaises((owner.Stop, KeyError, ValueError)):
            function(*args)
        run.assert_not_called()
        call.assert_not_called()
        popen.assert_not_called()

    def test_prepare_real_two_serial_and_clean_stock(self):
        state = stock()
        self.assertEqual(owner.preflight_prepare(state, [])['serial'], 1)
        state['rpm']['deployments'] = state['rpm']['deployments'][:1]
        state['bootc']['status']['rollback'] = None
        owner.preflight_prepare(state, [])

    def test_prepare_wrong_image_serial_same_checksum_wrong_serial_and_pending(self):
        for change in ('image', 'serial', 'stateroot', 'duplicate', 'transaction', 'queue', 'pin', 'layering', 'reorder'):
            state = stock()
            row = state['rpm']['deployments'][0]
            if change == 'image': row['container-image-reference-digest'] = 'sha256:' + 'b' * 64
            elif change == 'serial': row['serial'] = 8
            elif change == 'stateroot': row['osname'] = 'wrong'
            elif change == 'duplicate': state['rpm']['deployments'][1]['serial'] = row['serial']
            elif change == 'transaction': state['rpm']['transaction'] = ['upgrade', ':1.2', 'socket']
            elif change == 'queue': state['bootc']['status']['rollbackQueued'] = True
            elif change == 'pin': row['pinned'] = True
            elif change == 'layering': row['requested-packages'] = ['wrong']
            else: state['rpm']['deployments'].reverse()
            with self.subTest(change=change): self.refuse(owner.preflight_prepare, state, [])

    def test_retained_staged_fixture_accepts_only_the_same_upstream(self):
        import ast
        import re
        text = (ROOT / 'os/manifest/ci/11f/full-2/two-disk/pin-stock.txt').read_text()
        rpm = ast.literal_eval(re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text).split('AssertionError:', 1)[1].splitlines()[0].strip())
        bootc = json.loads((ROOT / 'os/manifest/ci/11f/full-2/two-disk/stock-status.json').read_text())
        state = dict(rpm=rpm, bootc=bootc)
        owner.preflight_prepare(state, [])
        for origin in ('ghcr.io/other/image:stable', 'ghcr.io/ublue-os/bazzite-nvidia-open-evil:stable'):
            bad = copy.deepcopy(state)
            next(d for d in bad['rpm']['deployments'] if d.get('staged'))['container-image-reference'] = origin
            self.refuse(owner.preflight_prepare, bad, [])

    def test_manual_clients_including_ostree_refuse_without_mutation(self):
        for name in ('bootc', 'rpm-ostree', 'ostree'):
            self.refuse(owner.preflight_prepare, stock(), [dict(exe='/usr/bin/' + name, excluded_as_daemon=False)])

    def test_prepared_rerun_requires_whole_list_identity_pin_and_pending(self):
        state = stock()
        state['rpm']['deployments'][0]['pinned'] = True
        state['bootc']['status']['booted']['pinned'] = True
        row = state['rpm']['deployments'][0]
        saved = dict(stock_identity=list(owner.key(row)), stock=copy.deepcopy(row), state=copy.deepcopy(state))
        owner.preflight_prepare(state, [], saved)
        for change in ('old-serial', 'old-removed', 'pin', 'transaction'):
            bad = copy.deepcopy(state)
            if change == 'old-serial': bad['rpm']['deployments'][1]['serial'] = 42
            elif change == 'old-removed': bad['rpm']['deployments'].pop()
            elif change == 'pin': bad['rpm']['deployments'][0]['pinned'] = False
            else: bad['rpm']['transaction'] = ['x', 'y', 'z']
            with self.subTest(change=change): self.refuse(owner.preflight_prepare, bad, [], saved)

    def test_rollback_on_booted_stock_refuses_before_any_command(self):
        state = stock()
        saved = dict(stock_identity=list(owner.key(state['rpm']['deployments'][0])), stock=state['rpm']['deployments'][0])
        self.refuse(owner.preflight_recovery, state, [], saved, 'ghcr.io/ares-empire/aresos@sha256:' + 'a' * 64)

    def pair(self):
        state = stock()
        retained = copy.deepcopy(state['rpm']['deployments'][0])
        retained.update(booted=False, pinned=True)
        release = json.loads((ROOT / 'os/manifest/release.json').read_text())['reference']
        ares = dict(retained, checksum='b' * 64, serial=0, booted=True, pinned=False,
            **{'container-image-reference': 'ostree-unverified-registry:' + release,
               'container-image-reference-digest': release.split('@')[1]})
        state['rpm']['deployments'] = [ares, retained]
        for name, row in (('booted', ares), ('rollback', retained)):
            state['bootc']['status'][name] = dict(ostree=dict(checksum=row['checksum'], deploySerial=row['serial'], stateroot=row['osname']),
                pinned=row['pinned'], image=dict(image=dict(image=row['container-image-reference'].removeprefix('ostree-unverified-registry:').removeprefix('ostree-image-signed:docker://')),
                imageDigest=row['container-image-reference-digest']))
        saved = dict(stock_identity=list(owner.key(retained)), stock=copy.deepcopy(retained))
        return state, saved, release

    def test_guarded_recovery_and_every_wrong_target_refusal(self):
        state, saved, release = self.pair()
        owner.preflight_recovery(state, [], saved, release)
        for change in ('stock-serial', 'stock-root', 'stock-pin', 'stock-digest', 'stock-ref', 'ares-target', 'pending', 'transaction', 'booted-stock'):
            bad = copy.deepcopy(state)
            d = bad['rpm']['deployments'][1]
            if change == 'stock-serial': d['serial'] = 77
            elif change == 'stock-root': d['osname'] = 'wrong'
            elif change == 'stock-pin': d['pinned'] = False
            elif change == 'stock-digest': d['container-image-reference-digest'] = 'sha256:' + 'd' * 64
            elif change == 'stock-ref': d['container-image-reference'] = 'ghcr.io/other/stock:latest'
            elif change == 'ares-target': bad['rpm']['deployments'][0]['container-image-reference'] = 'ghcr.io/other/ares:wrong'
            elif change == 'pending': bad['bootc']['status']['rollbackQueued'] = True
            elif change == 'transaction': bad['rpm']['transaction'] = ['upgrade', 'manual', 'socket']
            else:
                bad['rpm']['deployments'][0]['booted'] = False
                d['booted'] = True
                bad['bootc']['status']['booted'], bad['bootc']['status']['rollback'] = bad['bootc']['status']['rollback'], bad['bootc']['status']['booted']
            with self.subTest(change=change): self.refuse(owner.preflight_recovery, bad, [], saved, release)

    def test_keep_stock_requires_the_same_saved_pair_booted_stock_only(self):
        state, saved, release = self.pair()
        self.refuse(owner.preflight_recovery, state, [], saved, release, True)
        state['rpm']['deployments'][0]['booted'] = False
        state['rpm']['deployments'][1]['booted'] = True
        state['bootc']['status']['booted'], state['bootc']['status']['rollback'] = state['bootc']['status']['rollback'], state['bootc']['status']['booted']
        owner.preflight_recovery(state, [], saved, release, True)
        saved['stock_identity'][1] += 1
        self.refuse(owner.preflight_recovery, state, [], saved, release, True)

    def test_wrong_disk_and_protected_mount_refuse_without_mutation(self):
        class Reader:
            def __init__(self, tree): self.tree = tree
            def json(self, *command):
                if command[0] != 'lsblk': raise AssertionError('Refusal should precede other reads')
                return self.tree
        for serials, mount in ((('OTHER', 'KEEP'), False), (('TARGET', 'OTHER'), False), (('TARGET', 'KEEP'), True)):
            tree = dict(blockdevices=[dict(path='/dev/SYNTHETIC'+str(i),type='disk', serial=s,
                mountpoints=['/windows'] if mount else [None]) for i,s in enumerate(serials)])
            self.refuse(owner.disk_record, Reader(tree), dict(target='TARGET', protected='KEEP'))

    def test_bundle_tamper_partial_extra_link_and_traversal_refuse(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary:
            path = pathlib.Path(temporary) / 'payload'
            fingerprint = bundle.build(path)
            self.assertEqual(owner.checked_bundle(path), fingerprint)
            (path / 'at').write_text('tampered')
            self.refuse(owner.checked_bundle, path)
            (path / 'at').unlink()
            self.refuse(owner.checked_bundle, path)
            (path / 'at').write_bytes((ROOT / bundle.PAYLOAD['at']).read_bytes())
            (path / 'extra').write_text('extra')
            self.refuse(owner.checked_bundle, path)
            (path / 'extra').unlink()
            entries = json.loads((path / 'SHA256.json').read_text())
            entries.append(dict(sha256='a' * 64, path='../outside'))
            (path / 'SHA256.json').write_text(json.dumps(entries))
            self.refuse(owner.checked_bundle, path)

    def test_manifest_shape_duplicate_paths_fields_and_order_refuse_without_mutation(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary:
            path = pathlib.Path(temporary) / 'payload'
            bundle.build(path)
            entries = bundle.manifest()
            for bad in (entries + entries[:1], {'at': 'a' * 64},
                        [dict(path=row['path'], sha256=row['sha256']) for row in entries],
                        [dict(entries[0], extra='x')] + entries[1:],
                        [dict(entries[0], sha256=None)] + entries[1:]):
                (path / 'SHA256.json').write_text(json.dumps(bad))
                self.refuse(owner.checked_bundle, path)
            raw = json.dumps(entries).replace('"sha256":', '"sha256":"' + 'a' * 64 + '","sha256":', 1)
            (path / 'SHA256.json').write_text(raw)
            self.refuse(owner.checked_bundle, path)

    def test_cleanup_only_uses_shared_pin_validation_without_pinning(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary:
            path = pathlib.Path(temporary) / 'payload'
            bundle.build(path)
            scope = owner.program(path, 'pin-stock', 'PIN_STOCK')
            state = stock()
            def read(command, **kwargs):
                return json.dumps(state['rpm'] if command[0] == 'rpm-ostree' else state['bootc'])
            with patch('subprocess.check_output', side_effect=read), patch('subprocess.run') as run:
                scope['pin_stock'](cleanup_only=True)
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
