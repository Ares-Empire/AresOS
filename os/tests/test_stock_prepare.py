import ast
import contextlib
import copy
import io
import json
import pathlib
import re
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAUSE = ROOT / 'os/release/pause-stock-updates.sh'
PIN = ROOT / 'os/release/pin-stock.sh'

def program(path, marker):
    return path.read_text().split("<<'" + marker + "'\n", 1)[1].split('\n' + marker, 1)[0]

def real_status():
    raw=(ROOT/'os/manifest/ci/11f/full-2/two-disk/pin-stock.txt').read_text(encoding='utf-8')
    clean=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', raw)
    return ast.literal_eval(clean.split('AssertionError:',1)[1].splitlines()[0].strip())

class StockPinTest(unittest.TestCase):
    def run_pin(self, mutate=None, change_after_cleanup=False, no_staged=False):
        state=real_status()
        if no_staged:
            state['deployments']=[d for d in state['deployments'] if not d.get('staged')]
        if mutate:
            mutate(state)
        calls=[]
        def output(command, **kwargs):
            if command[0]=='rpm-ostree':
                return json.dumps(state)
            booted=next(d for d in state['deployments'] if d.get('booted'))
            staged=next((d for d in state['deployments'] if d.get('staged')),None)
            def slot(d):
                return dict(ostree=dict(checksum=d['checksum']),pinned=d.get('pinned',False),
                            image=dict(imageDigest=d['container-image-reference-digest']))
            return json.dumps(dict(status=dict(booted=slot(booted),staged=slot(staged) if staged else None,rollbackQueued=False)))
        def run(command,**kwargs):
            calls.append(command)
            if command==['rpm-ostree','cleanup','-p']:
                state['deployments']=[d for d in state['deployments'] if not d.get('staged')]
                if change_after_cleanup:
                    next(d for d in state['deployments'] if d.get('booted'))['checksum']='a'*64
            elif command[:3]==['ostree','admin','pin']:
                state['deployments'][int(command[3])]['pinned']=True
            else:
                raise AssertionError('Unexpected mutating command')
        log=io.StringIO()
        self.calls=calls
        with patch('subprocess.check_output',side_effect=output),patch('subprocess.run',side_effect=run),contextlib.redirect_stdout(log):
            exec(compile(program(PIN,'PIN_STOCK'),'pin-stock.sh','exec'),{})
        result=json.loads(next(l.split(' ',1)[1] for l in log.getvalue().splitlines() if l.startswith('ARESOS_STOCK_PIN_RESULT ')))
        return result

    def test_replays_real_staged_update_then_pins_unchanged_booted_checksum(self):
        result=self.run_pin()
        self.assertEqual(self.calls,[['rpm-ostree','cleanup','-p'],['ostree','admin','pin','0']])
        self.assertTrue(result['staged_discarded'])
        self.assertEqual(result['discarded']['digest'],'sha256:d0e5e105ebf43c7ddbe3c4a5dfecac1628b0e0dcf152bbd2aee0eda3e4b4cdd4')
        self.assertEqual(result['booted_checksum'],'aa669eff4ea5c1f97c6c816c8d5d2abb5314e9afa3b966c0100e3e65f8040c71')

    def test_clean_stock_pins_without_cleanup(self):
        result=self.run_pin(no_staged=True)
        self.assertFalse(result['staged_discarded'])
        self.assertEqual(self.calls,[['ostree','admin','pin','0']])

    def test_wrong_booted_digest_two_stages_and_other_origins_stop_before_cleanup_or_pin(self):
        def wrong_booted(s):
            next(d for d in s['deployments'] if d.get('booted'))['container-image-reference-digest']='sha256:'+'a'*64
        def two_staged(s):
            s['deployments'].insert(0,copy.deepcopy(s['deployments'][0]))
        for mutate in (wrong_booted,two_staged,
                       lambda s:s['deployments'][0].update({'container-image-reference':'ostree-image-signed:docker://ghcr.io/other/not-bazzite:stable'}),
                       lambda s:s['deployments'][0].update({'container-image-reference':'ostree-image-signed:docker://ghcr.io/ublue-os/bazzite-nvidia-open-evil:stable'})):
            with self.subTest(mutate=mutate),self.assertRaisesRegex(SystemExit,'STOP:.*EMERGENCY'):
                self.run_pin(mutate)
            self.assertEqual(self.calls,[])

    def test_booted_checksum_change_after_cleanup_never_pins(self):
        with self.assertRaisesRegex(SystemExit,'checksum changed after pending cleanup'):
            self.run_pin(change_after_cleanup=True)
        self.assertEqual(self.calls,[['rpm-ostree','cleanup','-p']])

    def test_pin_always_runs_exact_pause_prefix_and_docs_use_the_same_recipe(self):
        self.assertTrue(PIN.read_text().startswith(PAUSE.read_text()))
        docs=(ROOT/'docs/INSTALL.md').read_text(encoding='utf-8')
        self.assertIn(PIN.read_text().strip(),docs)
        self.assertLess(docs.index(PIN.read_text().strip()),docs.index('## 5.'))

class StockPauseTest(unittest.TestCase):
    def environment(self,busy=False):
        scope={}
        exec(compile(program(PAUSE,'PAUSE_STOCK'),'pause-stock-updates.sh','exec'),scope)
        units={'uupd.service':'enabled','uupd.timer':'enabled','rpm-ostreed-automatic.service':'static','rpm-ostreed-automatic.timer':'disabled'}
        active={n:'active' if n=='uupd.service' else 'inactive' for n in units}
        calls=[]
        ticks=[dict(transaction=['upgrade'])] if busy else []
        def output(command,**kwargs):
            if command[0]=='rpm-ostree':
                return json.dumps(ticks.pop(0) if ticks else dict(transaction=None))
            if 'list-unit-files' in command:
                return '' if '--global' in command else '\n'.join(n+' '+s for n,s in units.items())
            if 'show' in command:
                name=command[command.index('show')+1]
                return 'LoadState=loaded\nActiveState='+active[name]+'\nSubState=dead\n'
            raise AssertionError('Unexpected read command')
        def run(command,**kwargs):
            calls.append(command)
            if command[0]=='pgrep':
                return Mock(returncode=1)
            operation='mask' if 'mask' in command else 'disable'
            for name in [x for x in command if x in units]:
                active[name]='inactive'
                units[name]='masked-runtime' if operation=='mask' else 'disabled'
            return Mock(returncode=0)
        return scope,units,active,calls,output,run

    def test_pause_twice_is_idempotent_and_services_idle_timers_persistently_disabled(self):
        scope,units,active,calls,output,run=self.environment()
        with patch('subprocess.check_output',side_effect=output),patch('subprocess.run',side_effect=run),contextlib.redirect_stdout(io.StringIO()):
            scope['pause_stock']()
            once=copy.deepcopy((units,active))
            scope['pause_stock']()
        self.assertEqual((units,active),once)
        self.assertEqual(units['uupd.timer'],'disabled')
        self.assertEqual(units['uupd.service'],'masked-runtime')
        self.assertTrue(all(s=='inactive' for s in active.values()))
        self.assertFalse(any('finalize-staged' in arg or 'hardware-setup' in arg for c in calls for arg in c))

    def test_waits_for_active_deployment_transaction(self):
        scope,units,active,calls,output,run=self.environment(busy=True)
        with patch('subprocess.check_output',side_effect=output),patch('subprocess.run',side_effect=run),patch('time.sleep') as sleep,contextlib.redirect_stdout(io.StringIO()):
            scope['pause_stock']()
        sleep.assert_called_once_with(2)

if __name__=='__main__': unittest.main()
