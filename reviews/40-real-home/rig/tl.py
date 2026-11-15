#!/usr/bin/python3
"""Rig tool: list the rig compositor's toplevels, or act on one. usage: tl.py <rig> [list | activate|close|min|unmin|max|unmax|full|unfull <app_id>]"""
import importlib.machinery, importlib.util, os, struct, sys, time
rig = sys.argv[1]
env = dict(line.strip().split('=', 1) for line in open(os.path.join(rig, 'env')) if '=' in line)
assert env['WAYLAND_DISPLAY'] != 'wayland-0'
loader = importlib.machinery.SourceFileLoader('shell', os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../os/config/usr/libexec/aresos-shell'))
spec = importlib.util.spec_from_loader('shell', loader); shell = importlib.util.module_from_spec(spec); sys.modules['shell'] = shell; loader.exec_module(shell)
NAMES = {0: 'maximized', 1: 'minimized', 2: 'activated', 3: 'fullscreen'}
info = {}
class Client(shell.ForeignToplevels):
    def dispatch(self, object_id, opcode, payload):
        if self.kinds.get(object_id) == 'toplevel':
            if opcode == 0:
                info.setdefault(object_id, {})['title'] = self._string(payload, 0)[0]
            elif opcode == 4:
                (length,) = struct.unpack_from('=I', payload)
                info.setdefault(object_id, {})['states'] = [NAMES.get(v, v) for v in struct.unpack_from(f'={length // 4}I', payload, 4)]
        super().dispatch(object_id, opcode, payload)
windows = shell.Windows()
client = Client.connect(windows, {'WAYLAND_DISPLAY': env['WAYLAND_DISPLAY'], 'XDG_RUNTIME_DIR': os.environ['XDG_RUNTIME_DIR']})
action = sys.argv[2] if len(sys.argv) > 2 else 'list'
if action != 'list':
    target = [t for t in windows.toplevels.values() if t.app_id == sys.argv[3]]
    if not target: sys.exit('no such window')
    handle = target[-1].handle
    op = {'activate': 4, 'close': 5, 'min': 2, 'unmin': 3, 'max': 0, 'unmax': 1, 'full': 8, 'unfull': 9}[action]
    client.sock.setblocking(True)
    client._send(handle, op, struct.pack('=I', client.seat) if op == 4 else struct.pack('=I', 0) if op == 8 else b'')
    client.roundtrip(); time.sleep(0.3)
    client.sock.setblocking(False); client.readable() if False else None
    client.sock.setblocking(True); client.roundtrip()
for t in windows.toplevels.values():
    print(f"{t.app_id!r:28} {info.get(t.handle, {}).get('states')} outputs={sorted(t.outputs)} title={info.get(t.handle, {}).get('title')!r}")
