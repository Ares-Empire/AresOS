"""Round 9 regressions: protocol-boundary roles, namespace roots and export origins."""
from contextlib import contextmanager
from email.utils import getaddresses
import json
from pathlib import Path
import socket
import threading
import unittest
from unittest.mock import patch

from support import MailCase
from smtp_fixture import SMTPFixture
from imap_guard_fixture import GuardedIMAPFixture
from aresos_control.blobs import Blobs
from aresos_control.common import Refused, sha256
from aresos_control.engine import Engine
from aresos_control.mail import codec
from aresos_control.mail.roles import resolve
from aresos_control.mail.transport import folders, select, uids, fetch, ok, quote
from aresos_control.protocol import receive, send
from aresos_control.proxy import Proxy


class BlobOrigins9(unittest.TestCase):
    def test_review9_all_internal_origins_refuse_download_across_apps_and_restart(self):
        import tempfile
        root = Path(__file__).resolve().parents[2] / '.work'
        with tempfile.TemporaryDirectory(dir=root) as directory:
            engine = Engine(Path(directory) / 'state', Path(directory) / 'evidence')
            keys = []
            for origin in ('internal', 'composition_part', 'draft_body', 'draft_html', 'quoted_mail', 'wire', 'caller_import'):
                key = engine.blobs.put(origin.encode(), origin=origin)
                keys.append(key)
                for app in ('mail', 'testapp'):
                    result = engine.request({'v': 1, 'method': 'download', 'app': app, 'sha256': key})
                    self.assertFalse(result['ok'], result)
                    self.assertEqual(result['error']['code'], 'file_refused')
            settings = json.loads((root.parent / 'control/settings/managed-mcp.json').read_text())
            self.assertNotIn('testapp', settings['mcpServers'])
            self.assertIn('mail', settings['mcpServers'])
            export = engine.blobs.put(b'owner export', origin='export')
            with self.assertRaises(Refused):
                engine.blobs.require_origin(export, 'caller_import')
            self.assertTrue(engine.request({'v': 1, 'method': 'download', 'app': 'testapp', 'sha256': export})['ok'])
            engine.close()
            engine = Engine(Path(directory) / 'state', Path(directory) / 'evidence')
            try:
                for key in keys:
                    self.assertFalse(engine.request({'v': 1, 'method': 'download', 'app': 'testapp', 'sha256': key})['ok'])
                self.assertEqual(engine.blobs.require_origin(export, 'export'), b'owner export')
                # A pre-migration blob with no metadata has no download rights.
                (engine.blobs.directory / ('.origins-' + export)).unlink()
                self.assertFalse(engine.request({'v': 1, 'method': 'download', 'app': 'testapp', 'sha256': export})['ok'])
            finally:
                engine.close()


class ReviewFixes9(MailCase):
    @staticmethod
    def keys(comp):
        return {k: comp[k] for k in ('composition_id', 'composition_hash')}

    def role_map(self):
        return {name: ['\\' + role.title()] for role, name in self.account['special'].items() if role != 'inbox' and name}

    @contextmanager
    def frontend(self):
        original = dict(self.account)
        with GuardedIMAPFixture(host='dovecot', port=993, mode='unsafe') as fixture:
            fixture.role_map = self.role_map()
            self.account.update(imap_host='localhost', imap_port=fixture.port)
            self.engine.store.write({'mail:account:box': self.account}, 'fixture', 'scripted LIST frontend over real storage')
            try:
                yield fixture, original
            finally:
                self.account = original
                self.engine.store.write({'mail:account:box': original}, 'fixture', 'restore backend endpoint')

    def raw_state(self, names):
        result = {}
        with self.mail.transport.imap(self.account) as client:
            for name in names:
                validity = select(client, name)
                result[name] = [(uid, *fetch(client, uid, self.mail.wires.limit)) for uid in uids(client)]
        return result

    def reassign(self, fixture, role, target):
        fixture.role_map = {name: [flag for flag in flags if flag.casefold() != ('\\' + role).casefold()]
                            for name, flags in fixture.role_map.items()}
        fixture.role_map.setdefault(target, []).append('\\' + role.title())

    def test_review9_role_races_undo_move_and_copy_for_trash_drafts_archive(self):
        with self.frontend() as (fixture, _):
            stable = self.role_map()
            for role in ('trash', 'drafts', 'archive'):
                for verb in ('move', 'copy'):
                    for moment in ('before', 'after'):
                        with self.subTest(role=role, verb=verb, moment=moment):
                            fixture.role_map = {k: list(v) for k, v in stable.items()}
                            target = 'Race-' + role + '-' + verb + '-' + moment
                            self.data('folder_create', {'account': 'box', 'name': target})
                            source = self.fixture(text=target)
                            unrelated = self.fixture(target, text='Unrelated Deleted survives', flags='(\\Deleted)')
                            original = self.mail.message(source)['raw']
                            fired = False
                            def change(command, args):
                                nonlocal fired
                                if not fired and command == b'UID' and args.startswith(verb.upper().encode() + b' '):
                                    fired = True
                                    self.reassign(fixture, role, target)
                            fixture.before_command = change if moment == 'before' else lambda *_: None
                            fixture.after_command = change if moment == 'after' else lambda *_: None
                            result = self.data(verb, {'references': [source], 'target': target})
                            self.assertTrue(fired)
                            self.assertEqual(result['state'], 'partial', result)
                            self.assertIn('The special folders changed while Claude was ' + ('moving' if verb == 'move' else 'copying'), result['reason'])
                            self.assertIn('Nothing was deleted.', result['reason'])
                            state = self.raw_state(['INBOX', target])
                            self.assertEqual(sum(raw == original for _, raw, _ in state['INBOX']), 0 if verb == 'move' else 1)
                            self.assertIn(unrelated['uid'], [uid for uid, _, _ in state[target]])
                            self.assertEqual(sum(raw == original for _, raw, _ in state[target]), 1)
                            self.assertEqual(len(state[target]), 2)
                            observed = result['untrusted_content']['locations'][0]['observed_locations']
                            self.assertEqual(len(observed), 1 if verb == 'move' else 2)
                            self.assertEqual(sorted(v['folder'] for v in observed), sorted([target] if verb == 'move' else [source['folder'], target]))
                            for reference in observed:
                                self.assertEqual(self.mail.message(reference)['raw'], original)
                            self.assertIn('which is now ' + role.title(), result['reason'])
                            intent = self.engine.store.get('mail:filing:' + result['untrusted_content']['filing_id'])
                            self.assertEqual(intent['state'], 'partial')
                            self.assertEqual(intent['sources'], [source])
                            self.assertEqual(intent['target'], target)
                            self.assertEqual(list(self.engine.store.items('op:')), [])
                            following = self.call('accounts')
                            notice = next(n for n in following['pending']['notices'] if n['operation_id'] == intent['id'])
                            self.assertEqual(notice['untrusted_content']['reason'], result['reason'])
                            fixture.before_command = fixture.after_command = lambda *_: None

    def test_review9_failed_undo_and_missing_copyuid_are_partial_with_exact_observed_locations(self):
        for fault in ('move_undo', 'copy_undo', 'copyuid', 'source_gone', 'destination_gone'):
            with self.subTest(fault=fault), self.frontend() as (fixture, backend):
                source_folder, target = 'Source-' + fault, 'Target-' + fault
                for name in (source_folder, target):
                    self.data('folder_create', {'account': 'box', 'name': name})
                source = self.fixture(source_folder, text=fault)
                raw = self.mail.message(source)['raw']
                verb = 'copy' if fault == 'copy_undo' else 'move'
                acted = False
                def before(command, args):
                    if acted and command == b'UID' and (args.startswith(b'MOVE ') or args.startswith(b'EXPUNGE ')) and fault in ('move_undo', 'copy_undo'):
                        return b'[UNAVAILABLE] Scripted exact undo refusal'
                def after(command, args):
                    nonlocal acted
                    if not acted and command == b'UID' and args.startswith(verb.upper().encode() + b' '):
                        acted = True
                        self.reassign(fixture, 'trash', target)
                        if fault in ('source_gone', 'destination_gone'):
                            with self.mail.transport.imap(backend) as client:
                                ok(client.delete(quote(source_folder if fault == 'source_gone' else target)), 'Fixture removes empty source or moved destination')
                fixture.before_command, fixture.after_command = before, after
                fixture.hide_copyuid = fault == 'copyuid'
                result = self.data(verb, {'references': [source], 'target': target})
                self.assertEqual(result['state'], 'partial', result)
                locations = result['untrusted_content']['locations'][0]
                self.assertTrue(locations['scan_complete'])
                expected = [] if fault == 'destination_gone' else ([source_folder, target] if verb == 'copy' else [target])
                self.assertEqual(sorted(v['folder'] for v in locations['observed_locations']), sorted(expected))
                for reference in locations['observed_locations']:
                    self.assertGreater(reference['uid'], 0)
                    self.assertEqual(self.mail.message(reference)['raw'], raw)

    def test_review9_stable_roles_complete_and_uidplus_is_required_before_mutation(self):
        self.data('folder_create', {'account': 'box', 'name': 'Stable'})
        source = self.fixture()
        for verb in ('copy', 'move'):
            result = self.data(verb, {'references': [source], 'target': 'Stable'})
            self.assertEqual(result['state'], 'done')
            self.assertEqual(self.mail.message(result['items'][0])['raw'], self.mail.message(source)['raw'] if verb == 'copy' else raw)
            if verb == 'copy':
                raw = self.mail.message(source)['raw']
        # Suppress capability only in the frontend's server greeting/capability view.
        with self.frontend() as (fixture, _):
            from aresos_control.mail.transport import Transport
            original = Transport.imap
            @contextmanager
            def without_uidplus(transport, account):
                with original(transport, account) as client:
                    client.capabilities = tuple(v for v in client.capabilities if v != 'UIDPLUS')
                    yield client
            fresh = self.fixture()
            before = self.raw_state(['INBOX', 'Stable'])
            with patch.object(Transport, 'imap', without_uidplus):
                for verb in ('move', 'copy'):
                    result = self.call(verb, {'references': [fresh], 'target': 'Stable'})
                    self.assertFalse(result['ok'], result)
                    self.assertIn('UIDPLUS', result['error']['message'])
            self.assertEqual(self.raw_state(['INBOX', 'Stable']), before)

    def test_review9_filing_crash_leaves_visible_intent_and_restart_never_repeats_or_undoes(self):
        import imaplib
        class Crash(BaseException):
            pass
        self.data('folder_create', {'account': 'box', 'name': 'CrashTarget'})
        source = self.fixture(text='Remote move happens exactly once')
        original = imaplib.IMAP4.uid
        def crash_after_move(client, command, *args):
            result = original(client, command, *args)
            if command.upper() == 'MOVE':
                raise Crash()
            return result
        with patch.object(imaplib.IMAP4, 'uid', crash_after_move), self.assertRaises(Crash):
            self.call('move', {'references': [source], 'target': 'CrashTarget'})
        intents = self.engine.store.items('mail:filing:')
        self.assertEqual(len(intents), 1)
        self.assertEqual(intents[0][1]['state'], 'started')
        self.assertEqual(intents[0][1]['sources'], [source])
        self.assertEqual(intents[0][1]['target'], 'CrashTarget')
        before = self.raw_state(['INBOX', 'CrashTarget'])
        self.assertEqual(len(before['CrashTarget']), 1)
        self.engine.close()
        self.engine = Engine(self.root / 'state', self.root / 'independent')
        self.mail = self.engine.adapters['mail']
        self.assertEqual(self.raw_state(['INBOX', 'CrashTarget']), before)
        self.assertEqual(self.engine.store.items('mail:filing:')[0][1]['state'], 'started')
        log = self.engine.request({'v': 1, 'method': 'call', 'action': 'control_log', 'arguments': {'limit': 10}})
        self.assertTrue(log['ok'], log)
        events = [e for e in self.engine.store.audit() if e['action'] == 'mail_move']
        self.assertEqual(events[-1]['outcome'], 'started')
        self.assertIn('filing', events[-1]['untrusted_content'])

    def record_roles(self):
        proposal = self.data('account_folders', {'id': 'box'}, admin=True)
        self.data('account_folders', {'id': 'box', 'roles_hash': proposal['roles_hash']}, admin=True)
        self.account = self.mail.account('box')

    def test_review9_per_root_separators_protect_trash_and_unmarked_draft_children_after_refresh(self):
        with self.frontend() as (fixture, _):
            # LIST uses a separate '.' namespace for these roots; storage remains real Dovecot.
            for name in ('Trash', 'Trash.Child', 'Drafts', 'Drafts.Child', 'NewTrash', 'NewDrafts'):
                with self.mail.transport.imap(self.account) as client:
                    ok(client.create(quote(name)), 'Fixture namespace folder')
            fixture.separators = {name: '.' for name in ('Trash', 'Drafts', 'NewTrash', 'NewDrafts')}
            self.reassign(fixture, 'trash', 'Trash')
            self.reassign(fixture, 'drafts', 'Drafts')
            # Round-eight remembered roots carried INBOX's separator. The owner
            # refresh must recover those legacy entries from their own LIST rows.
            self.account.pop('roots')
            self.account['protected_special'] = {role: [{'folder': role.title(), 'delimiter': '/'}]
                                                  for role in ('trash', 'drafts')}
            self.engine.store.write({'mail:account:box': self.account}, 'fixture', 'legacy remembered roots')
            self.record_roles()
            for role in ('trash', 'drafts'):
                self.assertIn({'folder': role.title(), 'delimiter': '.'}, self.account['protected_special'][role])
                self.assertNotIn({'folder': role.title(), 'delimiter': '/'}, self.account['protected_special'][role])
            self.assertEqual(self.account['roots']['inbox']['delimiter'], '/')
            self.assertEqual(self.account['roots']['drafts']['delimiter'], '.')
            draft = self.fixture('Drafts.Child', text='Unmarked owner draft', attachments=[('part.bin', b'private', 'application/octet-stream')])
            ordinary = self.fixture()
            for refreshed in (False, True):
                with self.subTest(refreshed=refreshed):
                    if refreshed:
                        self.reassign(fixture, 'trash', 'NewTrash')
                        self.reassign(fixture, 'drafts', 'NewDrafts')
                        self.record_roles()
                    before = self.raw_state(['INBOX', 'Trash.Child', 'Drafts.Child'])
                    for verb in ('move', 'copy'):
                        self.assertFalse(self.call(verb, {'references': [ordinary], 'target': 'Trash.Child'})['ok'])
                        self.assertFalse(self.call(verb, {'references': [draft], 'target': 'INBOX'})['ok'])
                    for part in ('source', '1', '1.1', '1.2'):
                        self.assertFalse(self.call('attachment_save', {'reference': draft, 'part': part})['ok'])
                        self.assertFalse(self.call('compose', {'account': 'box', 'attachments': [{'reference': draft, 'part': part}]})['ok'])
                    self.assertFalse(self.call('compose', {'account': 'box', 'mode': 'forward', 'reference': draft, 'forward_as': 'attachment'})['ok'])
                    self.assertEqual(self.raw_state(['INBOX', 'Trash.Child', 'Drafts.Child']), before)
            self.assertTrue(self.mail.authored(self.mail.message(draft)))
            # Required separators themselves are bound to setup, not just the names.
            fixture.separators['NewDrafts'] = ':'
            self.assertFalse(self.call('move', {'references': [ordinary], 'target': 'INBOX'})['ok'])

    @contextmanager
    def local_proxy(self):
        # Exercise the actual Proxy, Client framing and Engine transfer on a private
        # socket. Distinct-user/installed-daemon qualification remains in the base suite.
        import tempfile
        work = Path(__file__).resolve().parents[1] / 'test-work'
        work.mkdir(exist_ok=True)
        home_temp = tempfile.TemporaryDirectory(dir=work)
        home = Path(home_temp.name)
        (home / 'Downloads').mkdir()
        path = self.root / 'fixture.sock'
        listener = socket.socket(socket.AF_UNIX)
        listener.bind(str(path))
        listener.listen()
        stop = threading.Event()
        self.engine.close()
        def serve():
            service = Engine(self.root / "state", self.root / "independent")
            try:
                serve_connections(service)
            finally:
                service.close()
        def serve_connections(service):
            while not stop.is_set():
                connection, _ = listener.accept()
                with connection:
                    if stop.is_set():
                        return
                    request = receive(connection)
                    if request is None:
                        return
                    if request['method'] in ('upload', 'download'):
                        service.transfer(connection, request)
                    else:
                        send(connection, service.request(request))
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        config = {'act_socket': str(path), 'home': str(home), 'folders': [str(home / 'Downloads')]}
        try:
            yield Proxy('testapp', config), Proxy('mail', config), home
        finally:
            stop.set()
            with socket.socket(socket.AF_UNIX) as wake:
                wake.connect(str(path))
                wake.shutdown(socket.SHUT_WR)
            thread.join(timeout=5)
            listener.close()
            self.assertFalse(thread.is_alive())
            self.engine = Engine(self.root / "state", self.root / "independent")
            self.mail = self.engine.adapters["mail"]
            home_temp.cleanup()

    def test_review9_long_draft_hash_cannot_be_saved_by_testapp_and_ordinary_export_is_exact(self):
        with SMTPFixture(self.root) as smtp:
            self.account.update(smtp_host='localhost', smtp_port=smtp.port)
            self.engine.store.write({'mail:account:box': self.account}, 'fixture', 'isolated SMTP sink')
            comp = self.compose(text='Long private draft text ' * 1000)
            draft = self.data('draft_save', self.keys(comp))['reference']
            resumed = self.data('compose', {'account': 'box', 'mode': 'draft', 'reference': draft})
            key = resumed['mail']['generated_parts'][0]['sha256']
            received = self.fixture(attachments=[('ordinary.bin', b'original\x00\xffbytes', 'application/octet-stream')])
            with self.local_proxy() as (testapp, mail, home):
                refused = testapp.call('file_save', {'sha256': key, 'folder': str(home / 'Downloads'), 'name': 'notes.txt'})
                self.assertFalse(refused['ok'], refused)
                self.assertEqual(refused['error']['code'], 'file_refused')
                self.assertFalse((home / 'Downloads/notes.txt').exists())
                # The test fixture's explicit export also cannot promote an internal hash.
                fake = {'sha256': key, 'size': len(self.engine.blobs.read(key)), 'name': 'notes.txt', 'real_path': str(home / 'Downloads/notes.txt')}
                self.assertFalse(testapp.call('export_file', fake)['ok'])
                saved = mail.call('attachment_save', {'reference': received, 'part': '1.2', 'name': 'ordinary.bin'})
                self.assertTrue(saved['ok'], saved)
                self.assertEqual(Path(saved['data']['path']).read_bytes(), b'original\x00\xffbytes')
            self.assertEqual(smtp.arrivals(), [])

    def test_review9_operation_status_retains_approval_and_stages_when_trash_role_is_removed(self):
        with SMTPFixture(self.root) as smtp, self.frontend() as (fixture, _):
            self.account.update(smtp_host='localhost', smtp_port=smtp.port)
            self.engine.store.write({'mail:account:box': self.account}, 'fixture', 'isolated SMTP sink')
            approval = self.approval()
            operation = self.send(approval)
            self.assertEqual(operation['state'], 'done')
            fixture.role_map[self.account['special']['trash']] = []
            status = self.data('operation_status', {'operation_id': operation['id']})
            self.assertEqual(status['operation']['approval'], approval)
            self.assertEqual(status['operation']['stages'], operation['stages'])
            self.assertEqual(status['operation']['state'], 'done')
            self.assertEqual(status['evidence_error']['code'], 'special_folders_changed')
            self.assertEqual(len(smtp.arrivals()), 1)

    def test_review9_header_whitespace_normalizes_before_approval_and_long_folded_subject_sends(self):
        with SMTPFixture(self.root) as smtp:
            self.account.update(smtp_host='localhost', smtp_port=smtp.port)
            self.engine.store.write({'mail:account:box': self.account}, 'fixture', 'isolated SMTP sink')
            for subject in (' invoice', 'invoice ', '\t invoice \t', 'invoice ' * 80):
                with self.subTest(subject=repr(subject)):
                    comp = self.compose(subject=subject, to=[' \t"  Alice  " <one@mail.invalid> \t'])
                    normalized = subject.strip(' \t')
                    self.assertEqual(comp['mail']['subject'], normalized)
                    self.assertEqual(getaddresses(comp['mail']['to'])[0][0], 'Alice')
                    approval = self.data('prepare_send', self.keys(comp))['approval']
                    self.assertIn(normalized, str(approval))
                    sent = self.send(approval)
                    self.assertEqual(sent['state'], 'done', sent)
                    received = codec.parse(smtp.arrivals()[-1][1])
                    self.assertEqual(str(received['Subject']), normalized)
                    self.assertEqual(received['To'].addresses[0].display_name, 'Alice')
