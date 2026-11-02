"""Exercise unmocked text/JSON parsers against pinned upstream-shaped output."""
import contextlib
import hashlib
import json
import pathlib
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import test_owner_tools as common

ROOT, owner = common.ROOT, common.owner
SOURCE = ROOT/'os/manifest/ci/14/parser-sources'


class FormatAuditTest(unittest.TestCase):
    def test_pinned_sources_versions_and_formatter_rules_are_bound(self):
        index = json.loads((SOURCE/'index.json').read_text())
        rows = index['sources']
        self.assertEqual(len(rows), 40)
        archive = ROOT/index['archive']['path']
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), index['archive']['sha256'])
        with zipfile.ZipFile(archive) as sources:
            self.assertEqual(len(sources.namelist()),len(set(sources.namelist())))
            self.assertEqual(set(sources.namelist()), {r['member'] for r in rows})
            for row in rows:
                self.assertEqual(list(row)[:2], ['sha256', 'member'])
                self.assertEqual(hashlib.sha256(sources.read(row['member'])).hexdigest(), row['sha256'])
                self.assertIn(row['commit'], row['url'])
            media = sources.read('rhboot_efivar__src_dp-media.c').decode()
            formatter = sources.read('rhboot_efibootmgr__src_efibootmgr.c').decode()
        packages = {p['name']:(p['version'],p['release']) for p in json.loads((SOURCE/'packages.json').read_text())['packages']}
        self.assertEqual(packages['efibootmgr'], ('18','11.fc44'))
        self.assertEqual(packages['efivar-libs'], ('39','12.fc44'))
        self.assertEqual(packages['systemd'], ('259.9','1.fc44'))
        self.assertEqual(packages['util-linux'], ('2.41.5','1.fc44'))
        self.assertIn('format_ucs2(buf, size, off, "File", dp->file.name, limit);', media)
        self.assertIn('printf("\\t%s", text_path);', formatter)
        self.assertIn('printf("%s", text_path);', formatter)
        self.assertIn('printf("      dp: ");', formatter)

    def test_systemd_three_column_list_and_property_rows_reach_real_pause_parser(self):
        class Host:
            def read(self, *command, **kw):
                if 'list-unit-files' in command:
                    return 'uupd.service masked -\nuupd.timer disabled enabled\n'
                return 'LoadState=masked\nActiveState=inactive\nSubState=dead\n'
            def mutate(self, *args): raise AssertionError('No mutation permitted')
        glob = pathlib.Path.glob
        with patch.object(pathlib.Path,'glob',lambda p,pattern:iter(()) if str(p)=='/run/user' else glob(p,pattern)):
            value = owner.paused_state(Host(),dict(SYSTEM=['uupd.service','uupd.timer'],USER=[]))
        self.assertEqual(value['system'], {'uupd.service':'masked','uupd.timer':'disabled'})

    def test_localed_variant_json_reaches_real_keyboard_parser(self):
        expected = dict(VConsoleKeymap='de',VConsoleKeymapToggle='',X11Layout='de',X11Model='pc105',X11Variant='',X11Options='')
        class Host:
            def json(self, *args):
                return dict(type='a{sv}',data=[{k:dict(type='s',data=v) for k,v in expected.items()}])
            def mutate(self, *args): raise AssertionError('No mutation permitted')
        tools = object.__new__(owner.Tools); tools.host=Host()
        self.assertEqual(tools.keyboard(), expected)

    def test_real_login_session_parser_accepts_decimal_monotonic_and_refuses_foreign_login(self):
        class Host:
            remote = 'no'
            def json(self, *args):
                return [dict(session='7',uid=1000,user='ares-recovery',seat='seat0',leader=1234,
                    **{'class':'user'},tty='tty4',idle=False,since=None)]
            def read(self, *args):
                fields = dict(Id='7', TTY='tty4', Audit='7', Scope='session-7.scope',
                    Service='login', Type='tty', Remote=self.remote, Name='ares-recovery',
                    User='1000', TimestampMonotonic='123456789')
                selectors = [arg.removeprefix('--property=') for arg in args[3:]]
                order = ('Id','User','Name','TimestampMonotonic','TTY','Remote','Service','Scope','Audit','Type')
                return ''.join(k+'='+fields[k]+'\n' for k in order if k in selectors)
            def mutate(self, *args): raise AssertionError('No mutation permitted')
        host=Host();tools=object.__new__(owner.Tools);tools.host=host
        original=pathlib.Path.read_text
        def read(path,*a,**kw):
            if str(path)=='/proc/self/loginuid':return '1000\n'
            if str(path)=='/proc/self/cgroup':return '0::/user.slice/user-1000.slice/session-7.scope\n'
            if str(path)=='/proc/self/sessionid':return '7\n'
            if str(path)=='/proc/sys/kernel/random/boot_id':return '11111111-1111-4111-8111-111111111111\n'
            return original(path,*a,**kw)
        with patch.object(owner.sys.stdin,'isatty',return_value=True), patch.object(owner.os,'ttyname',return_value='/dev/tty4'), \
             patch.object(owner,'terminal_number',return_value=1028), patch.object(owner,'process_terminal',return_value=dict(tty=1028)), \
             patch.object(pathlib.Path,'read_text',read):
            self.assertEqual(tools.session()['started_us'],123456789)
            host.remote='yes'
            with self.assertRaisesRegex(owner.Stop,'local physical recovery login'): tools.session()


if __name__=='__main__': unittest.main()
