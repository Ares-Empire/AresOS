"""Unmodified owner parsers on real retained package13/14 command values.

Only host reads, absolute filesystem spellings and process observations are
adapters. These tests neither execute a privileged command nor access a disk.
"""
import contextlib
import hashlib
import json
import pathlib
import re
import tempfile
import unittest
from unittest.mock import patch
import test_owner_tools as common

ROOT,owner=common.ROOT,common.owner
FIXTURES=ROOT/'os/tests/fixtures/owner-tools'
ROWS=json.loads((FIXTURES/'retained-parsers.json').read_text())
VALUES={r['kind']:r['value'] for r in ROWS}
# The retained parsers are release 13's machine (package 13 qualification).
REFERENCE=json.loads((ROOT/'os/manifest/releases/13.json').read_text())['reference']


def state(stage):
    return dict(rpm=VALUES[stage+' rpm-ostree-status'],bootc=VALUES[stage+' bootc-status'])


class ReadHost:
    def __init__(self,stage):self.stage,self.trace=stage,[]
    def json(self,*args):
        self.trace.append(dict(command=args,mutation=False))
        if args[0]=='rpm-ostree':return VALUES[self.stage+' rpm-ostree-status']
        if args[0]=='bootc':return VALUES[self.stage+' bootc-status']
        if args[0]=='busctl':return VALUES[self.stage+' keyboard']['localed']
        raise AssertionError(args)
    def read(self,*args,**kw):
        self.trace.append(dict(command=args,mutation=False))
        if args == ('systemctl','--no-pager','--no-legend','list-unit-files'):
            return 'uupd.service masked -\nuupd.timer disabled enabled\n'
        if args == ('systemctl','--global','--no-pager','--no-legend','list-unit-files'):
            return ''
        if args[:3] == ('systemctl','--no-pager','show') and args[3] in ('uupd.service','uupd.timer'):
            return 'LoadState=loaded\nActiveState=inactive\nSubState=dead\n'
        raise AssertionError(args)
    def mutate(self,*args):raise AssertionError('Forbidden mutation: '+repr(args))


@contextlib.contextmanager
def bls_files(stage):
    """Map the captured BLS files/symlink destinations to ordinary read values."""
    rows=VALUES[stage+' resolved-bls'];original_glob=pathlib.Path.glob
    original_read=pathlib.Path.read_text;original_resolve=pathlib.Path.resolve
    byfile={r['file']:r for r in rows};targets={}
    for row in rows:
        options=re.findall(r'^options (.+)$',row['content'],re.M)[0]
        target=next(x[7:] for x in options.split() if x.startswith('ostree='))
        targets['/sysroot'+target]=row['deployment']
    def glob(path,pattern):
        if str(path)=='/run/user':return iter(()) # No user-manager bus is part of these retained fixtures.
        return iter(pathlib.Path(p) for p in byfile) if str(path)=='/boot/loader/entries' else original_glob(path,pattern)
    def read(path,*a,**kw):return byfile[str(path)]['content'] if str(path) in byfile else original_read(path,*a,**kw)
    def resolve(path,*a,**kw):return pathlib.Path(targets[str(path)]) if str(path) in targets else original_resolve(path,*a,**kw)
    with patch.object(pathlib.Path,'glob',glob),patch.object(pathlib.Path,'read_text',read),patch.object(pathlib.Path,'resolve',resolve):yield


class RetainedTest(unittest.TestCase):
    def prepared(self):
        value=state('after-pin');stock=owner.agree(value)
        with bls_files('after-pin'):bls=owner.resolved_bls()
        return dict(state=value,stock=stock,stock_identity=list(owner.key(stock)),bls=bls)

    def test_committed_source_hashes_and_projection_identity(self):
        for row in ROWS:
            self.assertEqual(list(row)[:2],['sha256','path'])
            p=ROOT/row['path']
            if str(row['path']).startswith('.work/'):
                # Private source is not required on a fresh native checkout;
                # the verbatim fixture/projection is committed and reviewed.
                if p.exists():self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),row['sha256'])
            else:
                self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),row['sha256'])
                source=json.loads(p.read_text())
                if row['kind'].endswith('rpm-ostree-status'):
                    source=dict(source,deployments=[{k:v for k,v in d.items() if k!='base-commit-meta'} for d in source['deployments']])
                elif row['kind'].endswith('keyboard'):
                    source={k:source[k] for k in ('localed','loaded_map','cmdline')}
                    source['loaded_map']='\n'.join(l for l in source['loaded_map'].splitlines() if re.match(r'^keycode\s+(21|44)\s*=',l))+'\n'
                self.assertEqual(source,row['value'])

    def test_prepare_real_offline_stock_and_repair_input(self):
        for stage in ('first-stock-before-repair','qualification3 before-prepare'):
            host=ReadHost(stage);value=owner.observations(host)
            self.assertEqual(owner.preflight_prepare(value,[]),owner.agree(value))
            with bls_files(stage):
                bls=owner.resolved_bls();owner.validate_bls(value,bls)
                for b in bls:self.assertTrue(any(a.startswith('ostree=') for a in owner.bls_arguments(b)))
            self.assertFalse(any(x['mutation'] for x in host.trace))

    def test_title_switch_and_recovery_real_pairs_and_bls(self):
        saved=self.prepared()
        for stage in ('after-pin','after-switch-staged','aresos','aresos-us','aresos-back-de','after-rollback-queued','rollback'):
            host=ReadHost(stage);value=owner.observations(host)
            owner.qualified_state(value,saved,REFERENCE);owner.idle(value,[])
            with bls_files(stage),tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as tmp,patch.object(owner,'runtime_state',return_value={'observed':False,'reason':'not retained in package13; opaque diagnostic only'}):
                tools=owner.Tools(common.release13_bundle(pathlib.Path(tmp)/'payload'),host,pathlib.Path(tmp))
                tools.save('prepared',saved);tools.save('network-verified',{})
                tools.processes=lambda:[]
                output=tools.title()
                self.assertTrue(any(line.startswith('title Bazzite') for line in output))
                result=tools.load('title');owner.validate_bls(value,result['bls'])
                self.assertEqual(result['title']['identity'],saved['stock_identity'])
            if stage in ('aresos','aresos-us','aresos-back-de'):
                self.assertEqual(owner.key(owner.preflight_recovery(value,[],saved,REFERENCE)),tuple(saved['stock_identity']))
            if stage=='rollback':owner.preflight_recovery(value,[],saved,REFERENCE,keep=True)
            self.assertFalse(any(x['mutation'] for x in host.trace))

    def test_layout_keyboard_values_and_loaded_maps_are_real(self):
        for stage in ('first-stock-diagnostic','aresos','aresos-us','aresos-back-de','rollback'):
            host=ReadHost(stage);tools=object.__new__(owner.Tools);tools.host=host
            settings=tools.keyboard();v=VALUES[stage+' keyboard']
            self.assertEqual(set(settings),{'VConsoleKeymap','VConsoleKeymapToggle','X11Layout','X11Model','X11Variant','X11Options'})
            letters=('z','y') if settings['VConsoleKeymap']=='de' else ('y','z')
            for code,letter in zip((21,44),letters):
                symbol,=re.findall(r'^keycode\s+'+str(code)+r'\s*=\s*([^\s]+)',v['loaded_map'],re.M)
                self.assertIn(symbol,(letter,'+'+letter,'U+'+format(ord(letter),'04x'),'+U+'+format(ord(letter),'04x')))

    def test_real_install_tree_findmnt_and_binary_firmware_reach_disk_record(self):
        trace=VALUES['qualification3 install read-only trace']
        class Host:
            def read(self,*args,**kw):
                rows=[x for x in trace if x['command']==list(args)]
                if rows:return rows[0]['stdout']
                raise AssertionError(args)
            def json(self,*args):
                if args[0]=='sfdisk':return {} # Opaque diagnostics; not classified.
                return json.loads(self.read(*args))
            def mutate(self,*args):raise AssertionError(args)
        disks=json.loads(next(x['stdout'] for x in trace if x['command'][0]=='lsblk' and '--bytes' in x['command']))['blockdevices']
        expected=dict(target='CRUCIAL-TARGET',protected='MICRON-KEEP')
        self.assertTrue(all(any(d.get('serial')==serial for d in disks) for serial in expected.values()))
        result=owner.disk_record(Host(),expected)
        self.assertEqual(result['esp_guid'],'88420aef-f1fd-4814-8381-339d03f60a65')


if __name__=='__main__':unittest.main()
