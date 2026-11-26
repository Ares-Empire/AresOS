import unittest

from aresos_control.definitions import BY_NAME
from response_checks import Draft202012Validator, ResponseValidationError, StandardResponseValidator, VALIDATORS


class ResponseChecks(unittest.TestCase):
    def check_reply(self, action, reply, expected):
        schema = BY_NAME[action].tool()['outputSchema']
        fallback = StandardResponseValidator(schema)
        errors = [(error.validator, tuple(error.absolute_path)) for error in fallback.iter_errors(reply)]
        self.assertEqual(errors, expected)
        if errors:
            with self.assertRaises(ResponseValidationError) as raised:
                fallback.validate(reply)
            self.assertEqual((raised.exception.validator, raised.exception.absolute_path), errors[0])
        else:
            fallback.validate(reply)

        if Draft202012Validator is not None:
            validator = VALIDATORS[action]
            self.assertIsInstance(validator, Draft202012Validator)
            self.assertEqual([(error.validator, tuple(error.absolute_path)) for error in validator.iter_errors(reply)], errors)
        else:
            self.assertIsInstance(VALIDATORS[action], StandardResponseValidator)

    def test_chrome_replies_have_the_same_failures_with_and_without_jsonschema(self):
        step = {'do': 'click', 'outcome': 'done', 'popups': [
            {'tab': 2, 'controlled': 'pending', 'no': True, 'untrusted_content': {'url': 'about:blank'}},
        ]}
        reply = {'ok': True, 'pending': {'items': [], 'total': 0, 'cursor': None}, 'data': {
            'tab': 1, 'steps': [step], 'not_run': 0, 'deadline': False, 'prepared': [],
            'unknown': [], 'loaded': True, 'version_notice': None, 'untrusted_content': {
                'url': 'about:blank', 'title': None, 'changed': '', 'more_changes': 0,
                'outline': None, 'dialog': None, 'clipboard': None, 'stopped': [], 'now': None,
            },
        }}
        self.check_reply('chrome_do', reply, [])
        for valid in (True, False):
            step['popups'][0]['controlled'] = valid
            self.check_reply('chrome_do', reply, [])
        for invalid in (0, 1):
            step['popups'][0]['controlled'] = invalid
            self.check_reply('chrome_do', reply, [('enum', ('data', 'steps', 0, 'popups', 0, 'controlled'))])
        step['popups'][0]['controlled'] = False
        step['outcome'] = 'sent'
        step['ref'] = 'x' * 33
        reply['data'].update(tab=-1, loaded=0, unknown=['g:input'] * 21, unexpected=True)
        del reply['pending']
        self.check_reply('chrome_do', reply, [
            ('minimum', ('data', 'tab')), ('maxLength', ('data', 'steps', 0, 'ref')),
            ('enum', ('data', 'steps', 0, 'outcome')), ('maxItems', ('data', 'unknown')),
            ('anyOf', ('data', 'loaded')), ('additionalProperties', ('data',)), ('required', ()),
        ])

    def test_chrome_refusals_require_the_error_fields(self):
        reply = {'ok': False, 'pending': {}, 'error': {'code': 'refused', 'message': 'Read the tab again.'}}
        self.check_reply('chrome_go', reply, [])
        reply['error'] = {'code': False}
        self.check_reply('chrome_go', reply, [
            ('type', ('error', 'code')), ('required', ('error',)),
        ])
