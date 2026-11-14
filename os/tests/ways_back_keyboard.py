"""In-memory localed and console, with one persistent /etc per deployment.

Every host operation is intercepted; no keyboard command reaches the laptop.
PowerCut bypasses the tools' exception cleanup, as loss of power would.
"""
import copy
import contextlib
from unittest.mock import patch

import test_owner_update as base


class PowerCut(BaseException):
    pass


def identity(row):
    return (row['checksum'], row['serial'], row['osname'])


PROFILES = {
    'de': dict(base.DE),
    'us': dict(base.DE, VConsoleKeymap='us', X11Layout='us'),
    'us-intl': dict(base.DE, VConsoleKeymap='us-intl', X11Layout='us', X11Variant='intl'),
}


class KeyboardMachine(base.Machine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = {identity(r): dict(base.DE) for r in self.state['rpm']['deployments']}
        self.loaded = 'de'
        self.cut_keyboard = False

    def running(self):
        return next(r for r in self.state['rpm']['deployments'] if r['booted'])

    def keyboard(self):
        return copy.deepcopy(self.settings[identity(self.running())])

    def json(self, *command):
        if command[0] == 'busctl':
            return dict(data=[{k: dict(data=v) for k, v in self.keyboard().items()}])
        return super().json(*command)

    def read(self, *command, **kwargs):
        if command[0] == 'dumpkeys':
            a, b = ('z', 'y') if self.loaded == 'de' else ('y', 'z')
            return f'keycode 21 = {a}\nkeycode 44 = {b}\n'
        if command == ('id', '-nG', 'ares'):
            return 'ares\n' if self.running()['container-image-reference-digest'] == base.R13.split('@')[1] else 'ares wheel\n'
        return super().read(*command, **kwargs)

    def mutate(self, *command, **kwargs):
        super().mutate(*command, **kwargs)
        if command[0] == 'loadkeys':
            self.loaded = command[-1]
        elif command[:3] == ('localectl', '--no-convert', 'set-keymap'):
            self.settings[identity(self.running())].update(VConsoleKeymap=command[3], VConsoleKeymapToggle=command[4])
            if self.cut_keyboard:
                self.cut_keyboard = False
                raise PowerCut('between console and X11 persistence')
        elif command[:3] == ('localectl', '--no-convert', 'set-x11-keymap'):
            self.settings[identity(self.running())].update(zip(('X11Layout', 'X11Model', 'X11Variant', 'X11Options'), command[3:]))


@contextlib.contextmanager
def keyboard_sessions(tools, host):
    """Synthetic physical sessions; still execute the real layout and localed code."""
    current = [dict(tty='tty3', session='original', boot=tools.boot[0], started_us=1)]
    with patch.object(tools, 'keyboard', side_effect=host.keyboard), \
            patch.object(tools, 'session', side_effect=lambda: copy.deepcopy(current[0])), \
            patch('builtins.input', return_value='yz-/!ü'):
        yield current
