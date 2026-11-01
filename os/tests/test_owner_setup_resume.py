"""Failure injection at every real setup mutation and record publication."""
import contextlib
import copy
import io
import json
import pathlib
import shutil
import tempfile
import sys
import os
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_owner_tools as common
import test_owner_commands as commands
from test_owner_devices import FixtureHost, fixture
owner=common.owner


@contextlib.contextmanager
def preparation():
    f=commands.CommandTest()
    try:
        f.setUp()
        # Execute the exact same executable shim in-process for the large
        # failure matrix. Existing CommandTest retains real subprocess tests.
        # Host adapters, script bodies, machine files and mutation log are real.
        source=common.ROOT/'os/tests/owner_shim.py'
        code=compile(source.read_text(),str(source),'exec')
        def invoke(command):
            output=io.StringIO()
            with patch.object(sys,'argv',[str(source),str(f.root),*command]),contextlib.redirect_stdout(output):
                exec(code,{'__name__':'__main__','__file__':str(source)})
            return output.getvalue()
        f.host.invoke=invoke
        yield f
    finally: f.doCleanups()


class PrepareResumeTest(unittest.TestCase):
    def test_resume_after_every_real_mutation(self):
        with preparation() as f:
            f.tools.prepare(); count=sum(c['mutation'] for c in f.calls())
        self.assertGreaterEqual(count,6)
        for stop in range(1,count+1):
            with self.subTest(mutation=stop),preparation() as f:
                original=f.host.invoke; seen=0
                def invoke(command):
                    nonlocal seen
                    answer=original(command)
                    if f.calls()[-1]['mutation']:
                        seen+=1
                        if seen==stop: raise owner.Stop('injected after mutation')
                    return answer
                with patch.object(f.host,'invoke',side_effect=invoke),self.assertRaises((owner.Stop,SystemExit)):
                    f.tools.prepare()
                f.tools.prepare()
                self.assertTrue(f.tools.load('prepared')['stock']['pinned'])
                self.assertEqual(f.tools.load('prepare-intent')['phase'],'complete')
                offset=len(f.calls());f.tools.prepare()
                self.assertFalse(any(c['mutation'] for c in f.calls()[offset:]))

    def test_resume_after_every_record_write(self):
        with preparation() as f:
            original=f.tools.save; names=[]
            def save(name,value): names.append(name);return original(name,value)
            with patch.object(f.tools,'save',side_effect=save): f.tools.prepare()
        self.assertGreaterEqual(len(names),7)
        for stop in range(1,len(names)+1):
            with self.subTest(write=stop),preparation() as f:
                original=f.tools.save;seen=0
                def save(name,value):
                    nonlocal seen
                    original(name,value);seen+=1
                    if seen==stop: raise owner.Stop('injected after record write')
                with patch.object(f.tools,'save',side_effect=save),self.assertRaises(owner.Stop):f.tools.prepare()
                f.tools.prepare()
                self.assertEqual(f.tools.load('prepare-intent')['phase'],'complete')

    def test_changed_interrupted_identity_or_arguments_refuses_without_mutation(self):
        for change in ('serial','arguments','manifest','bootlink'):
            with self.subTest(change=change),preparation() as f:
                with patch.object(f.tools,'script',side_effect=owner.Stop('interrupt')),self.assertRaises(owner.Stop):f.tools.prepare()
                bls=copy.deepcopy(f.entries())
                if change=='serial':
                    state=f.read();state['rpm']['deployments'][1]['serial']+=7;f.state=state;f.write()
                elif change=='arguments':
                    state=f.read();state['kargs']+=' unexpected=1';f.state=state;f.write()
                elif change=='bootlink':
                    state=f.read();state['kargs']=state['kargs'].replace('ostree=/ostree/boot.1/stock/0','ostree=/different');f.state=state;f.write()
                else:
                    value=f.tools.load('prepare-intent');value['manifest']='0'*64;f.tools.save('prepare-intent',value)
                records={p.name:p.read_bytes() for p in f.store.iterdir()}
                with patch.object(owner,'resolved_bls',return_value=bls) if change=='bootlink' else contextlib.nullcontext():
                    f.refuse(f.tools.prepare)
                self.assertEqual(records,{p.name:p.read_bytes() for p in f.store.iterdir()})


class InstallResumeTest(unittest.TestCase):
    def test_private_setup_directory_rejects_owner_mode_type_or_link(self):
        p=pathlib.Path('/SYNTHETIC-NEVER-OPENED')
        for uid,mode in ((os.geteuid()+1,stat.S_IFDIR|0o700),(os.geteuid(),stat.S_IFDIR|0o755),
                         (os.geteuid(),stat.S_IFREG|0o600),(os.geteuid(),stat.S_IFLNK|0o700)):
            with self.subTest(uid=uid,mode=mode),patch.object(pathlib.Path,'lstat',return_value=SimpleNamespace(st_uid=uid,st_mode=mode)),self.assertRaises(owner.Stop):
                owner.owned_directory(p)

    @contextlib.contextmanager
    def installation(self):
        with tempfile.TemporaryDirectory(dir=common.ROOT/'os/tests') as temporary:
            root=pathlib.Path(temporary); usb=root/'usb';usb.mkdir()
            payload=usb/'ares-tools'; fingerprint=common.bundle.build(payload)
            home=root/'home';host=FixtureHost(fixture(),usb)
            def run():
                with patch('builtins.input',side_effect=['TARGET','KEEP']):return owner.install(payload,host)
            with patch.object(owner,'HOME',home),patch.object(owner.sys.stdin,'isatty',return_value=True),common.private_metadata(home):
                yield root,payload,home,run,fingerprint

    def check(self,home,fingerprint):
        self.assertEqual(owner.checked_bundle(home/'tools'),fingerprint)
        self.assertEqual(json.loads((home/'install-intent.json').read_text())['phase'],'complete')
        self.assertTrue((home/'at').is_symlink())
        self.assertEqual(json.loads((home/'records/disks.json').read_text()),dict(target='TARGET',protected='KEEP'))
        self.assertFalse((home/'.install-tools').exists())

    def test_resume_after_each_payload_file_copy(self):
        count=len(common.bundle.PAYLOAD)+2
        for stop in range(1,count+1):
            with self.subTest(copy=stop),self.installation() as (root,payload,home,run,fingerprint):
                original=shutil.copy2;seen=0
                def copy_file(*args,**kw):
                    nonlocal seen
                    answer=original(*args,**kw);seen+=1
                    if seen==stop:raise OSError('injected after copy')
                    return answer
                with patch('shutil.copy2',side_effect=copy_file),self.assertRaises(OSError):run()
                run();self.check(home,fingerprint)

    def test_resume_after_each_record_write(self):
        with self.installation() as (root,payload,home,run,fingerprint):
            original=owner.Tools.save;names=[]
            def save(obj,name,value):names.append(name);return original(obj,name,value)
            with patch.object(owner.Tools,'save',new=save):run()
        self.assertGreaterEqual(len(names),7)
        for stop in range(1,len(names)+1):
            with self.subTest(write=stop),self.installation() as (root,payload,home,run,fingerprint):
                original=owner.Tools.save;seen=0
                def save(obj,name,value):
                    nonlocal seen
                    original(obj,name,value);seen+=1
                    if seen==stop:raise OSError('injected after record write')
                with patch.object(owner.Tools,'save',new=save),self.assertRaises(OSError):run()
                run();self.check(home,fingerprint)

    def test_resume_after_atomic_payload_publication(self):
        with self.installation() as (root,payload,home,run,fingerprint):
            original=pathlib.Path.replace
            def replace(path,target):
                result=original(path,target)
                if path==home/'.install-tools':raise OSError('injected after atomic publish')
                return result
            with patch.object(pathlib.Path,'replace',new=replace),self.assertRaises(OSError):run()
            run();self.check(home,fingerprint)

    def test_resume_after_entry_publication(self):
        with self.installation() as (root,payload,home,run,fingerprint):
            original=pathlib.Path.symlink_to
            def link(path,*args,**kw):
                result=original(path,*args,**kw)
                if path==home/'at':raise OSError('injected after entry publish')
                return result
            with patch.object(pathlib.Path,'symlink_to',new=link),self.assertRaises(OSError):run()
            run();self.check(home,fingerprint)

    def test_unjournalled_or_unrecognized_partial_copy_is_never_deleted(self):
        for journal in (False,True):
            with self.subTest(journal=journal),self.installation() as (root,payload,home,run,fingerprint):
                if journal:
                    with patch('shutil.copytree',side_effect=OSError('interrupt')),self.assertRaises(OSError):run()
                    stage=home/'.install-tools';stage.mkdir(mode=0o700);(stage/'unknown').write_text('preserve')
                else:
                    home.mkdir(mode=0o700);(home/'unknown').write_text('preserve')
                before={p.relative_to(home).as_posix():p.read_bytes() for p in home.rglob('*') if p.is_file()}
                with self.assertRaises(owner.Stop):run()
                self.assertEqual(before,{p.relative_to(home).as_posix():p.read_bytes() for p in home.rglob('*') if p.is_file()})

if __name__=='__main__':unittest.main()
