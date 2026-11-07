from email.message import EmailMessage
from pathlib import Path
from unittest.mock import patch

from support import MailCase
from aresos_control.common import ASK_LIMIT, canonical, digest, sha256
from aresos_control.mail import codec


class Composing(MailCase):
    def test_new_send_exactly_once_bcc_bytes_encoding_sent_and_no_receipts(self):
        payloads = [('résumé.pdf', b'%PDF-\x00\xff', 'application/pdf'), ('image.png', b'\x89PNG\x00\xff', 'image/png'), ('update.exe', b'not executable\x00', 'application/octet-stream')]
        ref = self.fixture(attachments=payloads)
        read = self.data('read', {'reference':ref})
        attachments = [{'reference':ref, 'part':a['part']} for a in read['untrusted_content']['attachments']]
        approval = self.approval(to=['One <one@mail.invalid>'], cc=['two@mail.invalid'], bcc=['hidden@mail.invalid'],
                                 subject='Résumé 日本語', text='Line one\nCafé **literal**', attachments=attachments)
        result = self.send(approval)
        self.assertEqual(result['state'], 'done', result)
        self.assertEqual(result['stages']['sent_copy'], 'done')
        self.assertEqual(result['stages']['answered_flag'], 'not_needed')
        mid = result['stages']['message_id']
        for recipient in ('one@mail.invalid','two@mail.invalid','hidden@mail.invalid'):
            incoming = self.arrivals(recipient, mid)
            self.assertEqual(len(incoming), 1)
            raw = incoming[0]
            parsed = codec.parse(raw)
            self.assertIsNone(parsed.get('Bcc'))
            self.assertIsNone(parsed.get('Disposition-Notification-To'))
            self.assertEqual(str(parsed['Subject']), 'Résumé 日本語')
            self.assertEqual([codec.decoded(p) for p in parsed.iter_attachments()], [p[1] for p in payloads])
            self.assertEqual([p.get_filename() for p in parsed.iter_attachments()], [p[0] for p in payloads])
            self.assertIn(b'=?utf-8?', raw.lower())
            self.assertNotIn(b'\n', raw.replace(b'\r\n', b''))
        self.assertEqual(self.send(approval)['state'], 'done')
        self.assertEqual(len(self.arrivals('one@mail.invalid', mid)), 1)
        sent_refs = self.data('operation_status', {'operation_id':result['id']})['evidence']['sent']
        self.assertEqual(len(sent_refs),1)
        self.assertEqual(str(self.mail.message(sent_refs[0])['msg']['Bcc']),'hidden@mail.invalid')

    def test_reply_to_list_aliases_threading_own_sent_and_answered(self):
        ref = self.fixture(sender='List <list@mail.invalid>', to=self.owner,
            headers={'Reply-To':'Team <team@mail.invalid>', 'Cc':self.account['addresses'][1] + ', Member <member@mail.invalid>', 'References':'<ancestor@mail.invalid>'})
        result = self.data('compose', {'account':'box', 'mode':'reply_all', 'reference':ref, 'text':'Thanks'})
        mail = result['mail']
        self.assertEqual([codec.mailbox(x) for x in mail['to']], ['team@mail.invalid'])
        self.assertEqual([codec.mailbox(x) for x in mail['cc']], ['member@mail.invalid'])
        self.assertEqual(mail['in_reply_to'], ref['message_id'])
        self.assertEqual(mail['references'], ['<ancestor@mail.invalid>', ref['message_id']])
        approval = self.data('prepare_send', {k:result[k] for k in ('composition_id','composition_hash')})['approval']
        sent = self.send(approval)
        self.assertEqual(sent['state'], 'done', sent)
        self.assertIn('\\Answered', self.mail.message(ref)['flags'])
        own = self.fixture(self.account['special']['sent'], sender=self.owner, to='Original <original@mail.invalid>', headers={'Cc':'copy@mail.invalid, ' + self.account['addresses'][1]})
        reply = self.data('compose', {'account':'box', 'mode':'reply', 'reference':own, 'text':'Follow up'})['mail']
        self.assertEqual([codec.mailbox(x) for x in reply['to']], ['original@mail.invalid'])
        self.assertEqual(reply['cc'], ['copy@mail.invalid'])

    def test_long_quotes_by_reference_and_asking_size_never_cut_escaped(self):
        ref = self.fixture(text='Untrusted long thread\n' * 3000, attachments=[('odd-é.pdf', b'pdf bytes', 'application/pdf')])
        result = self.data('compose', {'account':'box', 'mode':'reply', 'reference':ref, 'text':'Full\ntext\u202e with controls', 'bcc':['hidden@mail.invalid'], 'attachments':[{'reference':ref, 'part':'1.2'}]})
        approval = self.data('prepare_send', {k:result[k] for k in ('composition_id','composition_hash')})['approval']
        description = approval['description']
        self.assertEqual(description['text'], 'Full\\u000atext\\u202e with controls')
        self.assertGreater(description['generated_parts'][0]['size'], 50000)
        self.assertIn('sha256', description['generated_parts'][0])
        self.assertEqual(description['bcc'], ['hidden@mail.invalid'])
        self.assertLessEqual(len(canonical(approval).encode()), ASK_LIMIT)
        huge = self.compose(text='x' * 18000)
        failure = self.call('prepare_send', {k:huge[k] for k in ('composition_id','composition_hash')})
        self.assertFalse(failure['ok'])
        self.assertEqual(failure['error']['code'], 'asking_input_too_large')
        altered = {**approval, 'description':{**description, 'bcc':[]}}
        self.assertEqual(self.call('send', altered)['error']['code'], 'stale_approval')

    def test_composition_and_attachment_corruption_refused(self):
        ref = self.fixture(attachments=[('file.pdf', b'original', 'application/pdf')])
        approval = self.approval(attachments=[{'reference':ref,'part':'1.2'}])
        op = self.engine.operation(approval['operation_id'])
        comp = op['payload']['composition']
        changed = {**comp, 'mail':{**comp['mail'], 'text':'tampered'}}
        self.engine.store.write({'mail:composition:' + comp['id']:changed}, 'fixture', 'tamper composition')
        self.assertEqual(self.call('send', approval)['error']['code'], 'stale_approval')
        approval = self.approval(attachments=[{'reference':ref,'part':'1.2'}])
        key = approval['description']['attachments'][0]['sha256']
        path = self.engine.blobs.directory / key
        path.chmod(0o600)
        path.write_bytes(b'changed')
        self.assertEqual(self.call('send', approval)['error']['code'], 'stale_reference')

    def test_formatted_defaults_signature_no_raw_html_and_invalid_links(self):
        account = {**self.account, 'format':'formatted', 'signature':'Owner signature'}
        self.engine.store.write({'mail:account:box':account}, 'fixture','signature')
        result = self.compose(text='**Bold** and *italic*\n- First\n- [Link](https://site.invalid)\n> Quoted\n<script>literal</script>')
        comp = self.mail.composition(result)
        parsed = codec.parse(self.mail.mime(comp, '<format@mail.invalid>'))
        plain = codec.body(parsed)
        html = parsed.get_body(preferencelist=('html',)).get_content()
        self.assertIn('Bold and italic', plain)
        self.assertIn('https://site.invalid', plain)
        self.assertIn('Owner signature', plain)
        self.assertIn('<strong>Bold</strong>', html)
        self.assertIn('<em>italic</em>', html)
        self.assertIn('<ul>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertFalse(self.call('compose', {'account':'box','text':'[bad](javascript:alert)', 'format':'formatted'})['ok'])

    def test_forward_inline_and_as_attachment_preserve_original_bytes(self):
        ref = self.fixture(attachments=[('invoice.pdf', b'PDF invoice bytes', 'application/pdf')])
        raw = self.mail.message(ref)['raw']
        for style in ('inline','attachment'):
            result = self.data('compose', {'account':'box', 'mode':'forward','forward_as':style,'reference':ref,'to':['one@mail.invalid'],'text':'Please review'})
            comp = self.mail.composition(result)
            msg = codec.parse(self.mail.mime(comp, '<forward-' + style + '@mail.invalid>'))
            attached = list(msg.iter_attachments())
            self.assertEqual(codec.decoded(attached[0]), raw if style == 'attachment' else b'PDF invoice bytes')
            if style == 'inline':
                self.assertIn('Forwarded mail', codec.body(msg))
                self.assertIn('Please review', codec.body(msg))

    def test_save_edit_send_and_delete_draft_with_explicit_approval(self):
        comp = self.compose(bcc=['hidden@mail.invalid'])
        args = {k:comp[k] for k in ('composition_id','composition_hash')}
        first = self.data('draft_save', args)['reference']
        read = self.data('read', {'reference':first})
        self.assertIn('\\Draft', read['flags'])
        unchanged = self.data('compose',{'account':'box','mode':'draft','reference':first})
        kept = codec.parse(self.mail.mime(self.mail.composition(unchanged),'<kept-draft@mail.invalid>'))
        self.assertIn('Full authored text',codec.body(kept))
        self.assertEqual(unchanged['mail']['text'],'')
        self.assertEqual(unchanged['mail']['generated_parts'][0]['kind'],'draft_body')
        edited = self.data('compose', {'account':'box','mode':'draft','reference':first,'text':'Updated body'})
        second = self.data('draft_save', {k:edited[k] for k in ('composition_id','composition_hash')} | {'previous':first})
        self.assertEqual(second['previous_retained'], first)
        self.assertEqual(self.data('read', {'reference':first})['reference'], first)
        approval = self.data('prepare_send', {k:edited[k] for k in ('composition_id','composition_hash')})['approval']
        sent = self.send(approval)
        self.assertEqual(sent['state'], 'done', sent)
        delete = self.delete_approval([first], 'permanent')
        self.assertEqual(self.data('delete', delete)['operation']['state'], 'done')
        self.assertEqual(self.data('read', {'reference':second['reference']})['reference'], second['reference'])

    def test_smtputf8_refused_and_idna_domains_converted(self):
        account = {**self.account, 'smtp_capabilities':[]}
        self.engine.store.write({'mail:account:box':account}, 'fixture', 'no SMTPUTF8')
        failure = self.call('compose', {'account':'box','to':['üser@mail.invalid'],'text':'hello'})
        self.assertEqual(failure['error']['code'], 'smtputf8_required')
        result = self.compose(to=['user@bücher.invalid'])
        self.assertEqual(result['mail']['to'], ['user@xn--bcher-kva.invalid'])

    def test_large_encoded_mail_keeps_per_attachment_cap_and_search_retains_only_summaries(self):
        # Raw MIME may exceed the per-file transfer cap while each attachment is valid.
        ref = self.fixture(attachments=[('large.bin', b'x' * (20 * 1024 * 1024), 'application/octet-stream')])
        self.assertGreater(len(self.mail.message(ref)['raw']),self.engine.blobs.limit)
        summary = self.data('search',{'account':'box','subject':'café'})['items'][0]
        self.assertEqual(summary['reference'],ref)
        self.assertEqual(summary['untrusted_content']['attachment_names'],['large.bin'])
        read = self.data('read',{'reference':ref})
        self.assertEqual(read['untrusted_content']['attachments'][0]['size'],20 * 1024 * 1024)
        contacts = self.data('contacts',{'account':'box'})
        self.assertEqual(contacts['total'],1)
