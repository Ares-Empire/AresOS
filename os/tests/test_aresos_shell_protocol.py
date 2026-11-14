"""Package 30: the unchanged package-34 messages and the helper's 1.1/1.0 boundary."""
import dataclasses
import json
import os
import pathlib
import shutil
import subprocess
import sys
from unittest import mock

from test_aresos_shell import shell, Base, Conn, ROOT, REGISTRY, INSTANCE, NONCE, ALL

EXAMPLES = ROOT / 'mod/src/test/resources/shell-1.1'


def example(name):
    return json.loads((EXAMPLES / (name + '.json')).read_text())


class Protocol11Test(Base):
    def setUp(self):
        super().setUp()
        self.root = pathlib.Path(self.folder.name)
        self.registry = self.root / 'registry'
        shutil.copytree(REGISTRY, self.registry)
        self.entries = [self.root / str(n) for n in range(5)]
        for folder in self.entries:
            folder.mkdir()
        self.icons = mock.Mock()
        self.icons.take.side_effect = lambda apps, revision: (apps, shell.icons_revision(apps, revision))

    def desktop(self, name='app.desktop', folder=0, **fields):
        values = dict(Type='Application', Name='Application', Exec='/usr/bin/tool')
        values.update(fields)
        path = self.entries[folder] / name
        path.write_text('[Desktop Entry]\n' + ''.join(f'{k}={v}\n' for k, v in values.items()))
        return path

    def start(self, minor=1, capabilities=None, tracked=True):
        catalogue = shell.Catalogue(str(self.registry), entry_dirs=self.entries, executable=lambda p: True)
        catalogue.refresh(self.clock())
        self.windows = shell.Windows(clock=self.clock) if tracked else None
        self.current = shell.Helper(str(self.registry), INSTANCE, NONCE, self.journal,
                                    registry=(catalogue.apps, catalogue.revision), catalogue=catalogue,
                                    icons=self.icons, windows=self.windows, clock=self.clock,
                                    executable=lambda p: True, launcher=self.launcher(), activate=self.activate)
        self.addCleanup(self.current.watcher.stop)
        self.conn = self.negotiate(minor, capabilities)
        return self.current

    def negotiate(self, minor, capabilities=None):
        conn = Conn()
        self.current.connected(conn)
        message = example('hello-request')
        message.update(instance=INSTANCE, nonce=NONCE, minor=minor)
        if capabilities is not None:
            message['capabilities'] = capabilities
        self.current.receive(conn, json.dumps(message).encode() + b'\n')
        self.assertTrue(conn.sent[-1]['ok'], conn.sent[-1])
        return conn

    def listing(self, **fields):
        return self.request(self.current, self.conn, 'list_apps', **fields)

    def test_example_hello_request_and_exact_reply_shape(self):
        self.start()
        expected = example('hello-reply')
        self.assertEqual(self.conn.sent[-1], expected)

    def test_example_pages_and_full_entry_are_produced_from_desktop_entries(self):
        expected = example('list-apps-reply-first-page')['apps'] + example('list-apps-reply-last-page')['apps']
        for row in expected:
            if 'desktop_id' not in row:
                continue
            fields = dict(Name=row['name'], Exec='/usr/bin/' + row.get('exec_name', 'tool'),
                          Categories=';'.join(row['categories']), Icon=row['id'],
                          GenericName=row.get('generic_name', ''), Keywords=';'.join(row.get('keywords', [])))
            if row['source'].startswith('flatpak'):
                fields.update(Exec='/usr/bin/flatpak run ' + row['exec_name'], **{'X-Flatpak': row['exec_name']})
            self.desktop(row['desktop_id'], folder={'user': 0, 'flatpak-user': 1, 'flatpak-system': 2,
                                                  'system': 3, 'image': 4}[row['source']], **fields)
        self.start()
        self.current.catalogue_apps = {key: dataclasses.replace(app, icon=next(
            (row.get('icon') for row in expected if row['id'] == key), None))
            for key, app in self.current.catalogue_apps.items()}
        self.current.apps = dict(self.current.catalogue_apps)
        reply = self.listing()
        self.assertEqual(reply['apps'], expected)
        self.assertIn(example('entry-full'), reply['apps'])
        # The page boundary is a byte budget, not the illustrative three entries. Exercise both example requests.
        first_request = example('list-apps-request-first')
        next_request = example('list-apps-request-next')
        self.assertNotIn('cursor', first_request)
        with mock.patch.object(shell, 'MAX_MESSAGE', 1800):
            self.current.receive(self.conn, json.dumps(first_request).encode() + b'\n')
            first = self.conn.sent[-1]
            self.assertEqual(set(first), set(example('list-apps-reply-first-page')))
            next_request['cursor'] = first['next']  # The example token is explicitly made up.
            self.current.receive(self.conn, json.dumps(next_request).encode() + b'\n')
            second = self.conn.sent[-1]
            while 'next' in second:
                second = self.listing(cursor=second['next'])
            self.assertEqual(set(second), set(example('list-apps-reply-last-page')))
            self.assertEqual(first['revision'], second['revision'])

    def test_minimal_example_is_a_valid_entry_without_known_details(self):
        self.start()
        self.assertEqual(self.current.app_row(shell.App('terminal', 'Terminal', argv=('/usr/bin/foot',)), True),
                         example('entry-minimal'))

    def test_five_sources_and_terminal_exec_name(self):
        for n in range(5):
            self.desktop(f'app{n}.desktop', folder=n, Terminal='true')
        self.start()
        rows = {row['id']: row for row in self.listing()['apps']}
        self.assertEqual([rows[f'app{n}']['source'] for n in range(5)],
                         ['user', 'flatpak-user', 'flatpak-system', 'system', 'system'])
        self.assertTrue(rows['app0']['terminal'])
        self.assertEqual(rows['app0']['exec_name'], 'tool')

    def test_optional_metadata_is_bounded_filtered_and_never_contains_launch_data(self):
        self.desktop(Categories='bad/name;;' + ';'.join('Cat' + str(n) for n in range(30)),
                     GenericName='g' * 90 + '\t', Keywords=';' + ';'.join('k' * 40 + str(n) for n in range(30)),
                     **{'X-Flatpak': '/secret/path'})
        self.start()
        row = self.listing()['apps'][0]
        self.assertEqual(len(row['categories']), 16)
        self.assertEqual(len(row['generic_name']), 64)
        self.assertTrue(all(len(word) <= 32 for word in row['keywords']))
        self.assertNotIn('exec_name', row)
        self.assertFalse({'argv', 'environment', 'working_directory', 'icon_name', 'app_ids'} & row.keys())
        self.assertFalse(any(isinstance(value, str) and '/' in value for key, value in row.items() if key != 'icon'))

    def test_replacement_order_details_and_launch_policy_are_separate(self):
        self.desktop('com.google.Chrome.desktop', folder=0, Icon='flatpak', GenericName='Second')
        first = self.desktop('google-chrome.desktop', folder=4, Icon='native', GenericName='First',
                             Exec='/usr/bin/evil', StartupWMClass='evil', Terminal='true')
        self.start()
        app = self.current.apps['browser']
        original = shell.load_registry(str(self.registry))[0]['browser']
        self.assertEqual((app.generic_name, app.icon_name), ('First', 'native'))
        self.assertEqual((app.argv, app.app_ids, app.instance, app.terminal),
                         (original.argv, original.app_ids, original.instance, original.terminal))
        first.unlink()
        self.now[0] += shell.CATALOGUE_CHECK
        self.current.tick()
        self.assertEqual(self.current.apps['browser'].generic_name, 'Second')
        self.assertEqual(len(self.listing()['apps']), 3)

    def test_many_unicode_entries_page_with_real_wire_byte_limit_and_long_request_id(self):
        for n in range(253):
            self.desktop(f'app{n:03}.desktop', Name='😀' * 64, GenericName='界' * 64,
                         Keywords=';'.join('😀' * 30 + str(i) for i in range(16)),
                         Categories=';'.join('C' + str(i) for i in range(16)))
        self.start()
        rows, cursor, pages = [], None, 0
        while True:
            reply = self.request(self.current, self.conn, 'list_apps', 'r' * 128,
                                 **({'cursor': cursor} if cursor else {}))
            wire = json.dumps(reply, separators=(',', ':'), ensure_ascii=False).encode() + b'\n'
            self.assertLessEqual(len(wire), 65536)
            self.assertTrue(reply['apps'])
            rows += reply['apps']
            pages += 1
            if not (cursor := reply.get('next')):
                break
        self.assertGreater(pages, 1)
        self.assertEqual(len(rows), 256)
        self.assertEqual([r['id'] for r in rows], sorted(set(r['id'] for r in rows)))

    def test_invalid_cursors_are_refused_without_crashing_or_launching(self):
        self.start()
        for cursor in (None, False, 1, [], '', 'x' * 65, 'p3-forged', example('list-apps-request-next')['cursor']):
            self.assertFalse(self.listing(cursor=cursor)['ok'])
        self.assertTrue(self.listing()['ok'])
        self.popen.assert_not_called()

    def test_revision_changes_mid_paging_and_old_cursor_gets_new_revision(self):
        for n in range(10):
            self.desktop(f'app{n}.desktop', GenericName='g' * 64)
        self.start()
        with mock.patch.object(shell, 'MAX_MESSAGE', 1200):
            first = self.listing()
            self.desktop('aaa.desktop')
            self.now[0] += 3
            second = self.listing(cursor=first['next'])
        self.assertTrue(second['ok'])
        self.assertNotEqual(first['revision'], second['revision'])

    def test_refresh_throttles_stats_and_parsing_then_detects_edits_additions_and_removal(self):
        path = self.desktop(Name='Before')
        self.start()
        # The first pass also learns executable dependencies; subsequent stable passes parse nothing.
        self.now[0] += 3
        self.current.tick()
        with mock.patch.object(shell, 'load_catalogue', wraps=shell.load_catalogue) as load:
            for _ in range(5):
                self.listing()
                self.current.tick()
            load.assert_not_called()
            self.now[0] += 3
            self.current.tick()
            load.assert_not_called()
            path.write_text(path.read_text().replace('Before', 'After!'))
            self.now[0] += 3
            self.assertEqual(self.listing()['apps'][0]['name'], 'After!')
            self.assertEqual(load.call_count, 1)
            path.unlink()
            self.desktop('new.desktop')
            self.now[0] += 3
            self.current.tick()
            self.assertEqual({row['id'] for row in self.listing()['apps']}, {'browser', 'notepad', 'terminal', 'new'})

    def test_apps_changed_example_shape_after_list_change(self):
        self.start()
        self.desktop()
        self.now[0] += 3
        self.current.tick()
        event = self.conn.events('apps_changed')[-1]
        expected = example('apps-changed-event')
        self.assertEqual(set(event), set(expected))
        self.assertEqual((event['protocol'], event['event']), (expected['protocol'], expected['event']))
        self.assertEqual(event['revision'], self.listing()['revision'])

    def test_picture_arrival_and_replacement_changes_revision_preserves_icons_on_rescan(self):
        path = self.desktop(Icon='original')
        self.start()
        initial = self.listing()['revision']
        def picture(apps, revision):
            apps = {k: dataclasses.replace(a, icon='/cache/one.png') if k == 'app' else a for k, a in apps.items()}
            return apps, shell.icons_revision(apps, revision)
        self.icons.take.side_effect = picture
        self.current.tick()
        revision = self.listing()['revision']
        self.assertNotEqual(initial, revision)
        self.assertEqual(len(self.conn.events('apps_changed')), 1)
        self.icons.take.side_effect = lambda apps, revision: (apps, shell.icons_revision(apps, revision))
        self.desktop('new.desktop')
        self.now[0] += 3
        self.current.tick()
        self.assertEqual(self.current.apps['app'].icon, '/cache/one.png')
        path.write_text(path.read_text().replace('original', 'different'))
        self.now[0] += 3
        self.current.tick()
        self.assertIsNone(self.current.apps['app'].icon)

    def test_events_require_both_minor_one_and_offered_capability(self):
        for minor, capabilities in ((0, ALL + ['apps_changed']), (1, ALL)):
            if not hasattr(self, 'current'):
                self.start(minor=minor, capabilities=capabilities)
            else:
                self.conn = self.negotiate(minor, capabilities)
            self.desktop('new' + str(minor) + '.desktop')
            self.now[0] += 3
            self.current.tick()
            self.assertEqual(self.conn.events('apps_changed'), [])

    def test_old_client_exact_hello_list_revision_and_discovery_launch_refusal(self):
        self.desktop('lunarclient.desktop')
        self.start(minor=0)
        self.assertEqual(self.conn.sent[-1]['protocol'], 'aresos-shell/1.0')
        self.assertEqual(set(self.conn.sent[-1]['capabilities']), set(ALL))
        legacy_apps, legacy_revision = shell.load_registry(str(self.registry))
        listing = self.listing()
        self.assertEqual(listing, dict(protocol='aresos-shell/1.0', id='r-1', ok=True, revision=legacy_revision,
                                      apps=[self.current.app_row(a) for a in sorted(legacy_apps.values(), key=lambda a: a.id)]))
        result = self.request(self.current, self.conn, 'open_app', 'o-1', app_id='lunarclient')
        self.assertEqual(result['error'], 'unknown_app')
        self.popen.assert_not_called()
        self.desktop('other.desktop')
        self.now[0] += 3
        self.current.tick()
        self.assertEqual(self.listing(), listing)

    def test_new_client_requires_no_new_capabilities_and_accepts_future_envelopes(self):
        self.start(capabilities=ALL)
        self.assertEqual(self.conn.sent[0]['minor'], 1)
        self.current.receive(self.conn, json.dumps(dict(protocol='aresos-shell/1.99', id='future',
                                                       op='list_apps', unknown={'anything': True})).encode() + b'\n')
        self.assertTrue(self.conn.sent[-1]['ok'])
        self.assertEqual(self.conn.sent[-1]['protocol'], 'aresos-shell/1.1')

    def test_removed_live_entry_still_matches_window_and_returns_but_cannot_relaunch(self):
        path = self.desktop(StartupWMClass='tracked')
        self.start()
        self.request(self.current, self.conn, 'open_app', 'o-1', app_id='app')
        self.windows.new(1)
        self.windows.app_id(1, 'tracked')
        self.windows.state(1, True)
        self.windows.done(1)
        self.current.windows_changed()
        scopes = dict(self.current.discovered_scopes)
        path.unlink()
        self.now[0] += 3
        self.current.tick()
        self.assertEqual(self.windows.toplevels[1].owner, 'app')
        self.assertEqual(self.current.discovered_scopes, scopes)
        self.assertNotIn('app', {row['id'] for row in self.listing()['apps']})
        self.assertEqual(self.request(self.current, self.conn, 'open_app', 'o-2', app_id='app')['error'], 'unknown_app')
        self.windows.gone(1)
        self.current.windows_changed()
        self.now[0] += shell.HANDOFF + 0.1
        self.current.tick()
        self.assertTrue(any(e.get('reason') == 'app_closed' for e in self.conn.events('shell_focus')))

    def test_catalogue_digest_is_stable_across_python_hash_seeds(self):
        self.desktop()
        script = ("import sys; sys.path.insert(0, 'os/tests'); from test_aresos_shell import shell; "
                  f"print(shell.load_catalogue({str(self.registry)!r}, entry_dirs={[str(p) for p in self.entries]!r}, "
                  "executable=lambda p: True)[1])")
        revisions = [subprocess.check_output([sys.executable, '-c', script], cwd=ROOT,
                                             env=dict(os.environ, PYTHONHASHSEED=str(seed))) for seed in (1, 42)]
        self.assertEqual(*revisions)

    def test_executable_install_removal_and_permission_changes_are_detected_without_entry_edits(self):
        tool = self.root / 'tool'
        tool.write_text('#!/bin/sh\nexit 0\n')
        self.desktop(Exec=str(tool))
        catalogue = shell.Catalogue(str(self.registry), entry_dirs=self.entries)
        catalogue.refresh(self.clock())
        self.assertNotIn('app', catalogue.apps)
        tool.chmod(0o700)
        self.now[0] += 3
        catalogue.refresh(self.clock())
        self.assertIn('app', catalogue.apps)
        tool.chmod(0o600)
        self.now[0] += 3
        catalogue.refresh(self.clock())
        self.assertNotIn('app', catalogue.apps)
        tool.unlink()
        self.now[0] += 3
        catalogue.refresh(self.clock())
        tool.write_text('#!/bin/sh\nexit 0\n')
        tool.chmod(0o700)
        self.now[0] += 3
        catalogue.refresh(self.clock())
        self.assertIn('app', catalogue.apps)

    def test_starter_availability_changes_revision_without_changing_legacy_digest(self):
        tool = self.root / 'tool'
        tool.write_text('fixture')
        data = json.loads((self.registry / 'browser.json').read_text())
        data['argv'] = [str(tool)]
        (self.registry / 'browser.json').write_text(json.dumps(data))
        catalogue = shell.Catalogue(str(self.registry), entry_dirs=self.entries)
        catalogue.refresh(self.clock())
        revision, legacy = catalogue.revision, catalogue.legacy[1]
        tool.chmod(0o700)
        self.now[0] += 3
        catalogue.refresh(self.clock())
        self.assertNotEqual(catalogue.revision, revision)
        self.assertEqual(catalogue.legacy[1], legacy)

    def test_flatpak_exec_name_uses_app_id_when_export_omits_x_flatpak(self):
        self.desktop('org.example.App.desktop', folder=1, Exec='/usr/bin/flatpak run org.example.App')
        self.start()
        row = next(row for row in self.listing()['apps'] if row['id'] == 'org-example-app')
        self.assertEqual(row['exec_name'], 'org.example.App')

    def test_list_diagnostic_retains_its_reviewed_registry_contract(self):
        self.desktop('extra.desktop')
        output = subprocess.check_output([sys.executable, str(ROOT / 'os/config/usr/libexec/aresos-shell'),
                                          '--registry', str(self.registry), '--list'],
                                         env=dict(os.environ, HOME=str(self.root), XDG_DATA_HOME=str(self.root / '0')))
        listing = json.loads(output)
        self.assertEqual({row['id'] for row in listing['apps']}, {'browser', 'terminal', 'notepad'})
        self.assertTrue(all(set(row) == {'id', 'name', 'available', 'reason'} for row in listing['apps']))
        self.assertEqual(listing['revision'], shell.load_registry(str(self.registry))[1])
