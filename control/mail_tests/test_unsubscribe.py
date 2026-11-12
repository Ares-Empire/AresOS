from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ssl
import threading
from unittest.mock import patch

from support import MailCase, CERT
from smtp_fixture import SMTPFixture
from aresos_control.mail import codec
from dkim_fixture import signed
from owner_state_oracle.transcript import TRACE, Transcript
from owner_state_oracle.model import Oracle
from owner_state_oracle.records import decode
from aresos_control.mail.transport import folders


class Unsubscribe(MailCase):
    def test_header_mailto_exact_address_body_and_approval(self):
        target = 'mailto:leave@mail.invalid?subject=Stop%20news&body=Unsubscribe%20this%20address'
        ref = self.fixture(headers={'List-Unsubscribe':'<' + target + '>'})
        read = self.data('read',{'reference':ref})
        self.assertEqual(read['untrusted_content']['unsubscribe'],[target])
        self.assertFalse(self.call('prepare_unsubscribe',{'reference':ref,'target':'mailto:other@mail.invalid'})['ok'])
        trace_start = len(TRACE.events)
        command, append = TRACE.command, self.mail.append
        def recorded_command(*args, **kwargs):
            # The standalone real-server test has no Driver to attach the
            # independent commit prefix at each remote command boundary.
            record = decode(self.root / 'state', self.root / 'independent')
            return command(*args, **kwargs, before_seq=max(record.committed, default=0),
                           committed_before=record.rows)
        def recorded_append(account, folder, raw, flags=None):
            with self.mail.transport.imap(account) as connection:
                roles = {row['name']: row['flags'] for row in folders(connection)}
            event = recorded_command('APPEND', account['id'], folder, roles,
                append_flags=flags, raw_hex=raw.hex())
            event['identities'] = [Transcript.message(raw)]
            result = append(account, folder, raw, flags)
            event.update(accepted=True, reply='delivered')
            return result
        with SMTPFixture(self.root) as smtp, \
             patch.object(TRACE, 'command', side_effect=recorded_command), \
             patch.object(self.mail, 'append', side_effect=recorded_append):
            account = {**self.account,'smtp_host':'localhost','smtp_port':smtp.port}
            self.engine.store.write({'mail:account:box':account},'fixture','SMTP')
            approval = self.data('prepare_unsubscribe',{'reference':ref,'target':target})['approval']
            self.assertEqual(approval['description']['to'],['leave@mail.invalid'])
            self.assertEqual(approval['description']['text'],'Unsubscribe this address')
            result = self.data('unsubscribe',approval)['operation']
            self.assertEqual(result['state'],'done',result)
            msg = codec.parse(smtp.arrivals()[0][1])
            self.assertEqual(str(msg['Subject']),'Stop news')
            self.assertEqual(codec.body(msg).strip(),'Unsubscribe this address')
            self.data('unsubscribe',approval)
            self.assertEqual(len(smtp.arrivals()),1)
            oracle = Oracle()
            oracle.script, oracle.servers = TRACE.script, TRACE.events[trace_start:]
            self.assertFalse(oracle.completion_errors(decode(self.root / 'state', self.root / 'independent')))
            self.assertTrue(any(e['command'] == 'DATA' and e['account'] == 'box' and e['identities'] for e in oracle.servers))
            self.assertTrue(any(e['command'] == 'APPEND' and e['accepted'] and e['before_seq'] for e in oracle.servers))

    def test_https_one_click_post_exact_no_cookies_no_redirect_no_get(self):
        trace_start = len(TRACE.events)
        requests = []
        status = [204]
        state_root = self.root
        def unsubscribe(approval):
            start = max(decode(state_root / 'state', state_root / 'independent').committed, default=0)
            index = len(TRACE.script)
            result = self.data('unsubscribe', approval)['operation']
            TRACE.script[index].update(start_seq=start,
                end_seq=max(decode(state_root / 'state', state_root / 'independent').committed, default=0))
            return result
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):
                pass
            def do_GET(self):
                raise AssertionError('No GET unsubscribe')
            def do_POST(self):
                record = decode(state_root / 'state', state_root / 'independent')
                event = TRACE.command('POST', folder=self.path, url='https://' + self.headers['Host'] + self.path,
                    before_seq=max(record.committed, default=0), committed_before=record.rows)
                requests.append((self.path,dict(self.headers),self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(status[0])
                self.send_header('Location','https://must-not-follow.invalid')
                self.end_headers()
                event.update(accepted=True, reply='delivered', status=status[0], body=requests[-1][2].decode())
        server = ThreadingHTTPServer(('0.0.0.0',0),Handler)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(CERT / 'tls.crt',CERT / 'tls.key')
        server.socket = ctx.wrap_socket(server.socket,server_side=True)
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            target = f'https://localhost:{server.server_port}/leave?token=synthetic'
            ref = self.fixture(headers={'List-Unsubscribe':'<' + target + '>', 'List-Unsubscribe-Post':'List-Unsubscribe=One-Click'})
            raw,key = signed(self.mail.message(ref)['raw'])
            ref = self.mail.append(self.account,'INBOX',raw)
            approval = self.data('prepare_unsubscribe',{'reference':ref,'target':target})['approval']
            self.assertEqual(requests,[])
            with patch('aresos_control.mail.dkim.dns_txt',return_value=[key]):
                result = unsubscribe(approval)
            self.assertEqual(result['state'],'done',result)
            self.assertEqual(requests[0][0],'/leave?token=synthetic')
            self.assertEqual(requests[0][2],b'List-Unsubscribe=One-Click')
            self.assertNotIn('Cookie',requests[0][1])
            oracle = Oracle()
            oracle.script, oracle.servers = TRACE.script, TRACE.events[trace_start:]
            self.assertFalse(oracle.completion_errors(decode(self.root / 'state', self.root / 'independent')))
            self.assertTrue(any(e['command'] == 'POST' and e['reply'] == 'delivered' for e in oracle.servers))
            self.data('unsubscribe',approval)
            self.assertEqual(len(requests),1)
            status[0] = 302
            ref = self.fixture(headers={'List-Unsubscribe':'<' + target + '>', 'List-Unsubscribe-Post':'List-Unsubscribe=One-Click'})
            raw,key = signed(self.mail.message(ref)['raw'])
            ref = self.mail.append(self.account,'INBOX',raw)
            approval = self.data('prepare_unsubscribe',{'reference':ref,'target':target})['approval']
            with patch('aresos_control.mail.dkim.dns_txt',return_value=[key]):
                self.assertEqual(unsubscribe(approval)['state'],'partial')
            self.assertEqual(len(requests),2)
            unsigned = self.fixture(headers={'List-Unsubscribe':'<' + target + '>', 'List-Unsubscribe-Post':'List-Unsubscribe=One-Click'})
            unsigned_approval = self.data('prepare_unsubscribe',{'reference':unsigned,'target':target})['approval']
            self.assertEqual(self.data('unsubscribe',unsigned_approval)['operation']['state'],'failed')
            self.assertEqual(len(requests),2)
            unsupported = self.fixture(headers={'List-Unsubscribe':'<https://site.invalid/leave>'})
            self.assertFalse(self.call('prepare_unsubscribe',{'reference':unsupported,'target':'https://site.invalid/leave'})['ok'])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
