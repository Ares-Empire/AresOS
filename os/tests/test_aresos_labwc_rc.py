"""Package 329's labwc settings, including the rows the release diff will see."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
RC = ROOT / 'os/config/usr/share/aresos/labwc/rc.xml'
FIXTURES = ROOT / 'os/tests/fixtures/329-window-frame'
sys.path.insert(0, str(ROOT / 'os/ci'))
from release_diff import rc_xml_changes, rc_xml_settings


ADDED_BINDINGS = rc_xml_settings('''<labwc_config>
  <keyboard><keybind key="A-S-Tab"><action name="PreviousWindow" /></keybind></keyboard>
  <mouse>
    <default />
    <context name="TitleBar">
      <mousebind direction="Up" action="Scroll"><action name="None" /></mousebind>
      <mousebind direction="Down" action="Scroll"><action name="None" /></mousebind>
    </context>
    <context name="Root">
      <mousebind button="Left" action="Press"><action name="None" /></mousebind>
      <mousebind button="Right" action="Press"><action name="None" /></mousebind>
      <mousebind button="Middle" action="Press"><action name="None" /></mousebind>
    </context>
  </mouse>
</labwc_config>''')
REPLACED_SECTIONS = ('theme: ', 'windowSwitcher: ')
PACKAGE_ROWS = (*REPLACED_SECTIONS, 'keyboard: <keybind key="A-S-Tab"',
                'mouse: <default', 'mouse: <context name="TitleBar"', 'mouse: <context name="Root"')


class LabwcRcTest(unittest.TestCase):
    def test_release_diff_replaces_two_rows_and_adds_four(self):
        before = (FIXTURES / 'rc-pre-329.xml').read_bytes()
        after = (FIXTURES / 'rc-expected-329.xml').read_bytes()
        removed = [row for row in rc_xml_settings(before) if row.startswith(REPLACED_SECTIONS)]
        replaced = [row for row in rc_xml_settings(after) if row.startswith(REPLACED_SECTIONS)]
        self.assertEqual(len(removed), 2)
        self.assertEqual(len(replaced), 2)
        self.assertEqual(rc_xml_changes(before, after),
                         {'removed': sorted(removed), 'added': sorted(replaced + ADDED_BINDINGS)})

    def test_live_config_keeps_all_six_package_settings(self):
        expected = [row for row in rc_xml_settings((FIXTURES / 'rc-expected-329.xml').read_bytes())
                    if row.startswith(PACKAGE_ROWS)]
        live = [row for row in rc_xml_settings(RC.read_bytes()) if row.startswith(PACKAGE_ROWS)]
        self.assertEqual(len(expected), 6)
        self.assertEqual(sorted(live), sorted(expected))
