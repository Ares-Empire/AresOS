"""All action results and each presentation exit share the same final bound."""
import copy
import json
import unittest
from unittest.mock import patch

from aresos_control.common import RESULT_LIMIT, WIRE_LIMIT, canonical, display_json, validate, Refused
from aresos_control.definitions import BY_NAME
from aresos_control import results as result_api
from response_checks import transport_response
import test_review_fixes_23 as prior


def maximal(schema):
    if 'anyOf' in schema:
        return max((maximal(s) for s in schema['anyOf']), key=lambda v: len(canonical(v)))
    if 'enum' in schema:
        return max(schema['enum'], key=lambda v: len(canonical(v)))
    kind = schema.get('type')
    if kind == 'object':
        if 'properties' not in schema:
            return {'untrusted': '\t' * 200000}
        return {k: maximal(v) for k, v in schema['properties'].items()}
    if kind == 'array':
        return [maximal(schema['items']) for _ in range(schema.get('maxItems', 1))]
    if kind == 'string':
        return '\t' * schema.get('maxLength', 4096)
    if kind in {'integer', 'number'}:
        return schema.get('maximum', 2**63 - 1)
    if kind == 'boolean':
        return True
    return None


class Results26(unittest.TestCase):
    setUp = prior.Results23.setUp
    call = prior.Results23.call
    data = prior.Results23.data

    def notice(self):
        notice = {'id': 'pending-fixture', 'app': 'mail', 'state': 'partial', 'ack': False,
                  'untrusted_content': {'reason': 'Filing changed to Trash. Check your mail program.'}}
        self.engine.store.write({'notice:pending-fixture': notice}, 'fixture', 'Synthetic warning')
        return self.engine.pending()['notices']

    def test_review26_ten_malformed_messages_oversize_ids_refuse_with_warning(self):
        notices = self.notice()
        ref = {'account': 'box', 'folder': 'Source', 'uidvalidity': self.imap.validities['Source'],
               'uid': 1, 'message_id': self.imap.mid + '\t' * 100000}
        raw = ('From: broken\r\nSubject: Synthetic\r\nMessage-ID: ' + ref['message_id'] + '\r\n\r\nSynthetic').encode()
        self.imap.boxes['Source'].update({i: raw for i in range(1, 11)})
        items = [{'reference': {**ref, 'uid': i}, 'from': 'broken', 'subject': 'Synthetic', 'date': ''}
                 for i in range(1, 11)]
        result = self.call('prepare_delete', {'items': items, 'mode': 'trash'})
        self.assertEqual(result['error']['code'], 'invalid_input')
        self.assertEqual(result['pending']['notices'], notices)
        transport_response(result)
        self.assertLess(len(display_json(result)), RESULT_LIMIT)
        # The builder is also bounded independently of schema validation (old refs).
        from email.message import EmailMessage
        msg = EmailMessage(); msg['From'] = 'broken'; msg['Subject'] = 'Synthetic'
        with patch.object(self.mail, 'message', return_value={'msg': msg}), self.assertRaises(Refused) as caught:
            self.mail.check_items(items)
        self.assertLess(len(str(caught.exception)), 4096)
        self.assertIn('characters omitted', str(caught.exception))

    def test_review26_every_definition_maximal_request_and_oversize_mail(self):
        notices = self.notice()
        self.imap.boxes['Source'][1] = (b'From: broken\r\nSubject: ' + b'x' * 100000 +
                                        b'\r\nMessage-ID: <synthetic@mail.invalid>' + b'\t' * 100000 + b'\r\n\r\nSynthetic')
        for name, action in BY_NAME.items():
            with self.subTest(action=name):
                args = maximal(action.input)
                validate(args, action.input)
                result = self.engine.request({'v': 1, 'method': 'call', 'action': name, 'arguments': args}, admin=True)
                transport_response(result)
                self.assertLess(len(display_json(result)), WIRE_LIMIT)
                self.assertEqual(result['pending']['notices'], notices)
                # Force the largest mail-derived response through every action's
                # shared finish, including errors with no observations at all.
                for ok in (True, False):
                    reply = {'ok': ok, 'pending': {'notices': notices},
                             'error': {'code': 'refused', 'message': 'Cannot use the selected messages.',
                                       'details': '\t' * 1000000},
                             'data': {'untrusted_content': {'headers': '\t' * 1000000}}}
                    result = self.engine.store.observations.finish(reply, self.engine.store)
                    transport_response(result)
                    self.assertLessEqual(len(canonical(result)), RESULT_LIMIT)
                    self.assertEqual(result['error']['code'], 'refused')
                    self.assertEqual(result['error']['message'], reply['error']['message'])
                    self.assertEqual(result['pending']['notices'], notices)
                    self.assertGreater(result['bounds']['omitted_characters'], 0)

    def test_review26_final_serializer_bounds_proxy_cli_socket_and_mcp(self):
        warning = 'Check filing in Trash.'
        for ok in (False, True):
            reply = {'ok': ok, 'error': {'code': 'refused', 'message': 'Cannot process these messages.',
                                       'details': '\t' * 4000000},
                     'pending': {'notices': [{'reason': warning}]}}
            encoded = display_json(reply)
            self.assertLess(len(encoded), WIRE_LIMIT)
            self.assertEqual(json.loads(encoded)['pending'], reply['pending'])
            bounded = result_api.bound_result(reply)
            mcp = {'content': [{'type': 'text', 'text': display_json(bounded)}], 'structuredContent': bounded}
            self.assertLess(len(canonical(mcp)), WIRE_LIMIT)
