"""Read labwc's toplevels for the Deskflow check's focus and dialog assertions."""
import json
import runpy

shell = runpy.run_path('/usr/libexec/aresos-shell')


class Toplevels(shell['ForeignToplevels']):
    def dispatch(self, object_id, opcode, payload):
        if self.kinds.get(object_id) == 'toplevel' and opcode == 0:
            title, _ = self._string(payload, 0)
            self.windows.toplevels[object_id].title = title
        super().dispatch(object_id, opcode, payload)


windows = shell['Windows']()
client = Toplevels.connect(windows)
try:
    print(json.dumps(sorted((item.app_id, getattr(item, 'title', '') or '', item.activated,
                             item.maximized, item.minimized, item.fullscreen)
                            for item in windows.toplevels.values() if item.ready)))
finally:
    client.sock.close()
