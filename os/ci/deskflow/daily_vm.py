"""Drive package 321's real Deskflow server and client through the check VM."""
import concurrent.futures
import json
import threading
import time
import xml.etree.ElementTree as ET

PASSWORD = 'fixture321'
BINDINGS = {
    'A-F4': (('alt', 'f4'), 'F4'),
    'A-Tab': (('alt', 'tab'), 'Tab'),
    'A-S-Tab': (('alt', 'shift', 'tab'), 'ISO_Left_Tab'),
    'XF86MonBrightnessUp': (225, 'XF86MonBrightnessUp'),
    'XF86MonBrightnessDown': (224, 'XF86MonBrightnessDown'),
    'XF86AudioRaiseVolume': (115, 'XF86AudioRaiseVolume'),
    'XF86AudioLowerVolume': (114, 'XF86AudioLowerVolume'),
    'XF86AudioMute': (113, 'XF86AudioMute'),
    'XF86AudioMicMute': (248, 'XF86AudioMicMute'),
    'C-A-Escape': (('ctrl', 'alt', 'esc'), 'Escape'),
    'Super': (('meta_l',), 'Super_L'),
}
RELEASE = ('meta_l', 'shift', 'esc')
RECOVERY = ('meta_l', 'ctrl', 'esc')


class Checks:
    def __init__(self, guest, evidence):
        self.guest = guest
        self.evidence = evidence
        self.failures = []
        self.last_diagnosed_error = None

    def ask(self, action, **kwargs):
        try:
            result = self.guest.request('daily-' + action, **kwargs)
        except Exception as error:
            self.diagnose(error)
            raise
        return {key: value for key, value in result.items() if key not in ('id', 'returncode')}

    def diagnose(self, error):
        if error is self.last_diagnosed_error:
            return
        self.last_diagnosed_error = error
        try:
            self.guest.request('diagnostics')
        except Exception as diagnostic_error:
            print(f'DESKFLOW_DAILY diagnostics unavailable: {type(diagnostic_error).__name__}', flush=True)

    def check(self, case, check, **details):
        self.record(case, check, 'passed', **details)

    def record(self, case, check, status, **details):
        result = dict(case=case, check=check, status=status, **details)
        with (self.evidence / 'daily-checks.jsonl').open('a') as log:
            print(json.dumps(result), file=log)
        print('DESKFLOW_DAILY ' + json.dumps(result), flush=True)

    def attempt(self, case, label, operation):
        try:
            operation()
        except Exception as error:
            self.diagnose(error)
            self.failures.append(label)
            self.record(case, label, 'failed', detail=str(error)[-1800:])
            return False
        return True

    def keys(self, *names):
        self.guest.qmp.command('send-key', {
            'keys': [{'type': 'qcode', 'data': name} for name in names], 'hold-time': 75,
        })
        time.sleep(0.12)

    def type(self, text):
        for key in text:
            self.keys({' ': 'spc', '\n': 'ret'}.get(key, key))

    def key_state(self, keys, down):
        self.guest.qmp.command('input-send-event', {'events': [
            {'type': 'key', 'data': {'down': down, 'key': {'type': 'qcode', 'data': key}}} for key in keys
        ]})

    def server(self, op):
        return self.ask('server', op=op)

    def peer(self, op, **kwargs):
        return self.ask('peer', op=op, **kwargs)

    def input(self, op, **kwargs):
        return self.ask('input', op=op, **kwargs)

    def clip(self, op, **kwargs):
        return self.ask('clip', op=op, **kwargs)

    def proof(self, op):
        return self.ask('proof', op=op)

    def dialog(self, name, **kwargs):
        return self.ask('dialog', name=name, **kwargs)

    def switch(self, *args, approve=None, status=None):
        self.ask('switch', op='start', args=args)
        if approve is not None:
            self.ask('switch', op='auth-window')
            if approve:
                self.type(PASSWORD + '\n')
            else:
                self.keys('esc')
        result = self.ask('switch', op='read')
        assert (result['code'] == 0) is (status is not None), result
        if status is not None:
            assert result['switch'] == status, result
        return result

    def switch_checks(self):
        first = self.ask('prepare', mode='initial')
        assert first['switch'] == 'off' and not first['backend_connections']
        self.check(2, 'first boot was Off, login hook left no Deskflow process or Wayland worker', **first)
        self.proof('off-launch')
        self.dialog('sharing')
        self.keys('esc')
        self.dialog('sharing', absent=True)
        self.proof('off-launch')
        self.dialog('sharing', absent=True)
        self.input('prepare')
        self.input('off-cross')
        self.check(2, 'real scoped core refused twice, one sharing window, crossing stayed local')
        self.ask('switch', op='policy', active=True)
        self.check(2, 'polkit in the active local session requires admin for On and allows Off')
        assert self.switch('on', approve=False)['switch'] == 'off'
        self.check(2, 'canceling the On password prompt left the switch Off')
        self.ask('switch', op='bad-root-args')
        for args in ([], ['ON'], ['on', 'x'], ['/tmp/deskflow-ci-not-a-switch']):
            self.ask('switch', op='bad-pkexec-args', args=args)
        self.check(2, 'invalid verbs and extra arguments refused both directly and through pkexec')
        extra_arg = self.switch('on', 'x', approve=True)
        assert extra_arg['code'] == 2 and extra_arg['switch'] == 'off', extra_arg
        self.check(2, 'pkexec authenticated the On verb but the helper refused its extra argument')
        for kind in ('link', 'writable-directory'):
            self.ask('switch', op='unsafe', kind=kind)
            self.check(2, 'unsafe switch refused by the helper and backend', fixture=kind)
        self.attempt(2, 'inactive local polkit decisions', self.inactive)
        self.attempt(2, 'nonlocal polkit decisions', self.remote)
        self.switch('on', approve=True, status='on')
        self.server('hook')
        initial = self.server('armed')
        time.sleep(1)
        assert self.server('armed') == initial, 'Deskflow did not keep one armed session'
        self.dialog('pair', absent=True)
        self.check(2, 'password turned On, one scoped Deskflow session stayed armed', **initial)

    def inactive(self):
        self.guest.keys('f3')
        try:
            self.guest.request('vt', expected='tty3')
            self.ask('switch', op='policy', active=False)
            assert self.switch('on')['switch'] == 'off'
        finally:
            self.guest.keys('f1')
            self.guest.request('vt', expected='tty1')
        self.check(2, 'inactive local On denied and Off requires authentication')

    def remote(self):
        remote = self.ask('switch', op='outside-seat')
        self.check(2, 'nonlocal On denied without a prompt', **remote)

    def pairing(self):
        self.peer('prepare')
        for name, key in (('enter', 'ret'), ('stranger', 'esc'), ('approved', 'm')):
            self.peer('start', peer=name)
            self.dialog('pair')
            self.keys('alt', key) if name == 'approved' else self.keys(key)
            self.dialog('pair', absent=True)
            self.peer('trusted', peer='approved' if name == 'approved' else None)
            self.peer('stop')
            self.check(9, {'enter': 'default Enter rejected real TLS peer',
                           'stranger': 'explicit rejection left trust empty',
                           'approved': 'deliberate confirmation saved the one approved certificate'}[name])
        self.peer('start', peer='approved', connected=True)
        self.input('prepare')

    def capture(self):
        self.input('cross')

    def release(self, *, modifiers=False, local=True):
        self.input('mark')
        if modifiers:
            self.key_state(RELEASE, True)
            try:
                self.input('released', modifiers=True)
            finally:
                self.key_state(reversed(RELEASE), False)
        else:
            self.keys(*RELEASE)
            self.input('released')
        if local:
            self.input('focus')
            self.keys('b')
            self.input('local-key')

    def inputs_and_bindings(self):
        self.capture()
        self.input('mark')
        self.input('inward')
        self.keys('a')
        self.input('forwarded')
        self.input('mark')
        self.type('aresosinput321')
        self.input('typed-marker')
        self.check(3, 'crossing, motion, button, scroll and keyboard reached only the real Deskflow client')
        for binding, (keys, symbol) in BINDINGS.items():
            self.input('mark')
            if isinstance(keys, int):
                self.input('virtual-key', code=keys)
            else:
                self.keys(*keys)
            self.keys('b')
            options = {'mic_mute_limit': True} if binding == 'XF86AudioMicMute' else {'key': symbol}
            self.attempt(8, binding, lambda: self.check(8, binding, **self.input('binding', **options)))
        for binding, mouse, pattern in (
            ('Left button', ['btn 272 1', 'btn 272 0'], '1'),
            ('Right button', ['btn 273 1', 'btn 273 0'], '3'),
            ('Middle button', ['btn 274 1', 'btn 274 0'], '2'),
            ('Scroll up', ['axis -1'], '4'),
            ('Scroll down', ['axis 1'], '5'),
            ('Alt+left drag', ['btn 272 1', 'rel 15 13', 'btn 272 0'], '1'),
            ('Alt+right drag', ['btn 273 1', 'rel 15 13', 'btn 273 0'], '3'),
            ('Alt+middle', ['btn 274 1', 'btn 274 0'], '2'),
            ('Alt+scroll', ['axis -1'], '4'),
        ):
            self.input('mark')
            alt = binding.startswith('Alt+')
            if alt:
                self.key_state(('alt',), True)
            try:
                self.input('virtual-mouse', commands=mouse)
            finally:
                if alt:
                    self.key_state(('alt',), False)
            self.keys('b')
            self.attempt(8, binding, lambda: self.check(8, binding, **self.input('binding', mouse=pattern)))
        self.release(modifiers=True)
        self.check(4, 'Super+Shift+Escape released the pointer and both modifiers were balanced')
        self.check(8, 'W-S-Escape', laptop='pointer and keyboard returned', capture='ended', next_key='local')
        self.capture()
        self.input('mark')
        self.keys(*RECOVERY)
        self.input('released')
        self.dialog('recovery', new=True)
        self.type('touch deskflowrecovered\n')
        self.proof('recovery-key')
        self.keys('alt', 'f4')
        self.input('focus')
        self.check(8, 'W-C-Escape', laptop='recovery terminal opened', capture='ended', next_key='terminal')

    def clipboard(self):
        def exchange():
            self.clip('host')
            self.capture()
            self.clip('read-client')
            self.clip('client')
            self.clip('release')
            self.clip('read-host')

        exchange()  # Warm the clipboard path and its persistent descriptors.
        self.clip('baseline')
        for _ in range(20):
            exchange()
        result = self.clip('counts')
        self.check(3, '20 clipboard transfers each way reached the client through the portal with stable frontend fd count',
                   **result)

    def reject_peer(self, name):
        self.peer('stop')
        try:
            self.peer('start', peer=name)
            refusal = self.peer('refused', peer=name)
            self.input('mark')
            self.input('untrusted-cross')
            self.keys('b')
            self.input('local-key')
            self.clip('host')
            self.clip('no-read', side='client')
            client = self.peer('no-data', peer=name)
            self.check(9, 'same screen name refused; input and clipboard stayed local', peer=name, **refusal, **client)
        finally:
            self.peer('stop')

    def approved_after_refusal(self):
        self.peer('start', peer='approved', connected=True)
        self.clip('host')
        self.capture()
        self.input('mark')
        self.keys('b')
        self.input('still')
        self.clip('read-client')
        self.release()

    def privacy_and_trust(self):
        def flatpak():
            self.check(8, 'real frontend supplied the unlisted sandbox ID and backend refused it',
                       **self.proof('flatpak'))
        self.attempt(8, 'Flatpak identity refusal', flatpak)
        for name in ('stranger', 'plain'):
            self.attempt(9, f'{name} refusal', lambda: self.reject_peer(name))
        self.approved_after_refusal()
        self.check(9, 'approved peer still received input and clipboard after both negative controls')
        self.peer('stop')
        self.server('stop')
        self.peer('settings', stale=True)
        for path in ('hub', 'hook'):
            self.server(path)
            self.dialog('invalid-profile')
            self.keys('ret')
            self.server('off')
            self.check(9, 'stale plus approved fingerprint prevented launch', path=path)
        self.peer('settings', stale=False)
        for path in ('hub', 'hook'):
            self.server(path)
            self.server('armed')
            self.peer('protected')
            self.attempt(9, f'{path} stranger refusal with unsafe settings', lambda: self.reject_peer('stranger'))
            self.approved_after_refusal()
            self.check(9, 'TLS and fingerprint checks still effective with both user checks disabled', path=path)
            if path == 'hub':
                self.peer('stop')
                self.server('stop')

    def log_privacy(self):
        self.check(8, 'journal, helper output and all Deskflow logs omit input and clipboard markers',
                   **self.proof('log'))

    def restart_pair(self):
        self.peer('stop')
        self.server('stop')
        self.server('hook')
        self.server('armed')
        self.peer('start', peer='approved', connected=True)
        self.input('prepare')

    def idle_and_restart(self):
        self.capture()
        self.input('mark')
        time.sleep(60)
        self.keys('b')
        self.input('still')
        self.check(5, 'capture still held and next key reached the client after 60 seconds idle')
        self.server('freeze')
        self.keys(*RELEASE)
        stopped = self.server('frozen-exited')
        self.input('focus')
        self.input('mark')
        self.keys('b')
        self.input('local-key')
        self.check(5, 'QMP release chord stopped the frozen backend and guarded Deskflow; next key was local', **stopped)
        self.peer('stop')
        self.server('hub')
        initial = self.server('armed')
        self.peer('start', peer='approved', connected=True)
        self.capture()
        self.release()
        self.check(5, 'explicit hub launch resumed sharing after the fallback', **initial)
        self.server('kill-backend')
        current = self.server('armed')
        assert current['backend'] != initial['backend'] and current['owner'] != initial['owner']
        assert current['pid'] == initial['pid'], 'the same guarded core should re-arm after an ordinary backend exit'
        self.capture()
        self.release()
        self.check(6, 'fresh D-Bus backend with the right Wayland socket captured after the original was killed', **current)
        self.peer('stop')
        previous = self.server('kill-frontend')['previous']
        self.server('stop')
        self.server('hub')
        self.server('armed')
        assert self.server('frontend')['owner'] != previous
        self.peer('start', peer='approved', connected=True)
        self.capture()
        self.release()
        self.check(6, 'fresh frontend and new Deskflow session captured after frontend restart')
        self.peer('stop')
        self.proof('restart-login')
        assert self.ask('prepare', mode='relogin')['switch'] == 'on'
        proof = self.ask('server', op='armed', monitor=False)
        self.peer('start', peer='approved', connected=True)
        self.input('prepare')
        self.capture()
        self.release()
        self.check(6, 'logout and login started Deskflow through the real autostart hook', **proof)

    def disable(self):
        for manual in (False, True):
            self.capture()
            self.input('mark')
            # Send more keys on the QEMU keyboard while the separate guest channel changes the switch.
            started = threading.Event()

            def typing():
                for _ in range(12):
                    self.keys('b')
                    started.set()

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                incoming = pool.submit(typing)
                assert started.wait(4)
                self.input('still')
                if manual:
                    elapsed = self.proof('off-time')
                else:
                    self.switch('off', status='off')
                    elapsed = {}
                incoming.result()
            self.input('closed')
            assert not self.server('off')['connections']
            self.input('focus')
            self.input('mark')
            self.keys('b')
            self.input('local-key')
            for origin, destination in (('host', 'client'), ('client', 'host')):
                self.clip(origin)
                self.clip('no-read', side=destination)
            self.check(7, 'capture ended, client closed, subsequent input and clipboard stayed local',
                       change='file removal without revoke' if manual else 'passwordless pkexec Off', **elapsed)
            self.peer('stop')
            self.switch('on', approve=False)
            assert self.ask('switch', op='status')['switch'] == 'off'
            if not manual:
                self.switch('on', approve=True, status='on')
                self.server('hook')
                self.server('armed')
                self.peer('start', peer='approved', connected=True)
        self.switch('on', approve=True, status='on')
        self.check(7, 'On required the password again')


def bindings_match_image(path):
    configured = {bind.get('key') for bind in ET.parse(path).getroot().iter('keybind')}
    expected = set(BINDINGS) | {'W-S-Escape', 'W-C-Escape'}
    missing = configured - expected - {'W', 'Super_L'}
    assert not missing, f'add a Deskflow capture check for each installed binding: {sorted(missing)}'


def run(guest, evidence):
    checks = Checks(guest, evidence)
    for case, label, operation in ((2, 'first boot and switch', checks.switch_checks),
                                   (9, 'live pairing', checks.pairing)):
        if not checks.attempt(case, label, operation):
            break
    else:
        for case, label, operation in (
            ('3/4/8', 'input forwarding, recovery and bindings', checks.inputs_and_bindings),
            (3, '20 clipboard transfers each way', checks.clipboard),
            (9, 'TLS negative controls', checks.privacy_and_trust),
            (8, 'log privacy', checks.log_privacy),
            ('5/6', 'idle, stopped backend and session restarts', checks.idle_and_restart),
            (7, 'Off during typing', checks.disable),
        ):
            if not checks.attempt(case, label, operation) and label != 'log privacy':
                if not checks.attempt(case, f'fixture restart after {label}', checks.restart_pair):
                    break
    if checks.ask('switch', op='status')['switch'] == 'off':
        checks.ask('switch', op='seed-on')
        checks.record(7, 'persistence control was seeded by the fixture', 'fixture')
    checks.proof('poweroff')
    return checks.failures
