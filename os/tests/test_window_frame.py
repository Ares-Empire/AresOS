"""Package 31: exercise the compiled desktop default, including its scope."""
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
OVERRIDE = ROOT / 'os/config/usr/share/glib-2.0/schemas/zz-aresos.gschema.override'


@unittest.skipUnless(shutil.which('glib-compile-schemas') and shutil.which('gsettings'),
                     'GLib schema tools are needed')
class WindowButtonDefaultTest(unittest.TestCase):
    def test_compiled_override_applies_only_to_aresos(self):
        with tempfile.TemporaryDirectory() as directory:
            schemas = pathlib.Path(directory)
            # The real schema ID, key type and upstream default, in isolation
            # from the host's saved settings and distribution overrides.
            (schemas / 'org.gnome.desktop.wm.preferences.gschema.xml').write_text('''
<schemalist>
  <schema id="org.gnome.desktop.wm.preferences" path="/org/gnome/desktop/wm/preferences/">
    <key name="button-layout" type="s"><default>'appmenu:close'</default></key>
  </schema>
</schemalist>
''')
            shutil.copyfile(OVERRIDE, schemas / OVERRIDE.name)
            subprocess.run(['glib-compile-schemas', '--strict', str(schemas)], check=True,
                           capture_output=True)
            for desktop, expected in (('AresOS', 'appmenu:minimize,maximize,close'),
                                      ('GNOME', 'appmenu:close'), ('', 'appmenu:close')):
                with self.subTest(desktop=desktop):
                    env = dict(os.environ, GSETTINGS_SCHEMA_DIR=str(schemas),
                               XDG_CURRENT_DESKTOP=desktop, GSETTINGS_BACKEND='memory')
                    result = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.wm.preferences',
                                             'button-layout'], env=env, check=True,
                                            capture_output=True, text=True)
                    self.assertEqual(result.stdout.strip(), repr(expected))


if __name__ == '__main__':
    unittest.main()
