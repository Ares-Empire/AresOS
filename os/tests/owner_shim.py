"""Executable stand-ins: only the supplied ordinary JSON fixture is writable.

Unknown commands fail closed. This file is never imported by owner/runtime code.
"""
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
command = sys.argv[2:]
state = json.loads((root / 'machine.json').read_text())
tool, *args = command
mutation = False
result = ''
if tool == 'rpm-ostree' and args == ['status', '--json']:
    result = json.dumps(state['rpm'])
elif tool == 'bootc' and args == ['status', '--json']:
    result = json.dumps(state['bootc'])
elif tool == 'rpm-ostree' and args == ['kargs']:
    result = state['kargs']
elif tool == 'rpm-ostree' and args == ['cancel']:
    state['rpm']['transaction'] = None
    mutation = True
elif tool == 'rpm-ostree' and args == ['cleanup', '-p']:
    state['rpm']['deployments'] = [d for d in state['rpm']['deployments'] if not d.get('staged')]
    state['bootc']['status']['staged'] = None
    mutation = True
elif tool == 'rpm-ostree' and args == ['reload']:
    mutation = True
elif tool == 'ostree' and args[:3] == ['admin', 'instutil', 'set-kargs']:
    state['kargs'] = ' '.join(args[3:])
    mutation = True
elif tool == 'ostree' and args[:2] == ['admin', 'pin']:
    d = state['rpm']['deployments'][int(args[2])]
    d['pinned'] = True
    for slot in state['bootc']['status'].values():
        if isinstance(slot, dict) and slot.get('ostree', {}).get('deploySerial') == d['serial']:
            slot['pinned'] = True
    mutation = True
elif tool == 'systemctl':
    if 'list-unit-files' in args:
        # systemd259 output_unit_file_list has UNIT FILE / STATE / PRESET.
        result = ('uupd.service ' + ('masked -' if state.get('paused') else 'enabled enabled')
            + '\nuupd.timer ' + ('disabled enabled' if state.get('paused') else 'enabled enabled'))
    elif 'show' in args:
        result = 'LoadState=loaded\nActiveState=inactive\nSubState=dead\n'
    elif 'mask' in args or 'disable' in args:
        state['paused'] = True
        mutation = True
    else:
        raise SystemExit('Unknown systemctl shim operation')
elif tool == 'id' and args == ['-u', 'ares-recovery']:
    result = '1000'
elif tool == 'id' and args == ['-nG', 'ares-recovery']:
    result = 'ares-recovery wheel'
elif tool == 'getent' and args[0] == 'passwd':
    result = ''
elif tool == 'localectl':
    mutation = True
    if args[1] == 'set-keymap':
        state['keyboard']['VConsoleKeymap'], state['keyboard']['VConsoleKeymapToggle'] = args[2:]
    elif args[1] == 'set-x11-keymap':
        if state.pop('fail_x11_once', False):
            (root / 'machine.json').write_text(json.dumps(state))
            raise SystemExit(42)
        for key, value in zip(('X11Layout', 'X11Model', 'X11Variant', 'X11Options'), args[2:]):
            state['keyboard'][key] = value
    else:
        raise SystemExit('Unknown localectl operation')
elif tool == 'dumpkeys':
    profile = state['keyboard']['VConsoleKeymap']
    if profile not in ('de', 'us', 'us-intl'):
        raise SystemExit('Unknown physical layout profile in dumpkeys shim')
    result = json.loads((pathlib.Path(__file__).parent/'fixtures/owner-tools'/('dumpkeys-'+profile+'.json')).read_text())
else:
    raise SystemExit('Unknown command in owner shim: ' + tool)
with (root / 'calls.jsonl').open('a') as log:
    log.write(json.dumps(dict(command=command, mutation=mutation)) + '\n')
if mutation:
    (root / 'machine.json').write_text(json.dumps(state))
print(result)
