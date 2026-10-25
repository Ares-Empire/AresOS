import pathlib
import sys
import unittest
import types
from unittest.mock import Mock, patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'ci'))
from keyboard_vm import physical_keys
from keyboard_diagnostic import localization_values
from live_keyboard_ui import ACCESSIBLE


class KeyboardVMTest(unittest.TestCase):
    def test_accessibility_selects_controls_instead_of_same_named_static_text(self):
        namespace={}
        with patch.dict(sys.modules,pyatspi=types.SimpleNamespace()):
            exec(ACCESSIBLE.split('phase=sys.argv[1]')[0],namespace)
        static=Mock(); static.queryAction.side_effect=NotImplementedError
        label=Mock(); label.queryAction.return_value.nActions=0
        button=Mock(); button.queryAction.return_value.nActions=1
        namespace['candidates']=lambda pattern:[static,button,label]
        self.assertEqual(namespace['actionable']('German'),[(button,button.queryAction.return_value)])

    def test_physical_positions_distinguish_layouts_and_password_characters(self):
        for char in 'yz-/':
            self.assertNotEqual(physical_keys(char,'de'),physical_keys(char,'us'))
        self.assertEqual(physical_keys('y','de'),['z'])
        self.assertEqual(physical_keys('/','de'),['shift','7'])
        self.assertEqual(physical_keys('!','de'),['shift','1'])
        for char in ('Ä', '"', ';'):
            with self.assertRaises(AssertionError): physical_keys(char,'de')

    def test_diagnostic_exports_only_allowlisted_localization_get_reply_pairs(self):
        call=dict(type='method_call',interface='org.freedesktop.DBus.Properties',member='Get',sender=':1.5',cookie=20,
                  payload=dict(data=['org.fedoraproject.Anaconda.Modules.Localization','VirtualConsoleKeymap']))
        reply=dict(type='method_return',destination=':1.5',reply_cookie=20,payload=dict(data=[dict(type='s',data='us')]))
        self.assertEqual(localization_values([call,reply])[0]['value'],[dict(type='s',data='us')])
        wrong=dict(call,payload=dict(data=['org.fedoraproject.Anaconda.Modules.Users','Password']))
        self.assertEqual(localization_values([wrong,reply]),[])
        self.assertEqual(localization_values([call,dict(reply,reply_cookie=21)]),[])
