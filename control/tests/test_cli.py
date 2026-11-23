"""Command routing without an installed service or root-owned test prefix."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import unittest
from unittest.mock import patch

from aresos_control import cli


class LogCommand(unittest.TestCase):
    def test_top_level_log_is_refused_before_contacting_the_service(self):
        for word in ('log', 'not-a-command'):
            with self.subTest(word=word), patch.object(cli, 'Proxy') as proxy, redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit) as refused:
                    cli.main({}, [word, '--json'])
                self.assertEqual(refused.exception.code, 2)
                proxy.assert_not_called()

    def test_control_log_preserves_arguments_and_result(self):
        reply = {'ok': True, 'data': {'items': [], 'total': 0, 'cursor': None}, 'pending': {}}
        output = StringIO()
        config = {'act_socket': 'fixture.sock'}
        with patch.object(cli, 'Proxy') as proxy, redirect_stdout(output):
            proxy.return_value.call.return_value = reply
            self.assertEqual(cli.main(config, ['control', 'log', '--input', '{"limit":1}', '--json']), 0)
        proxy.assert_called_once_with('control', config, False)
        proxy.return_value.call.assert_called_once_with('log', {'limit': 1})
        self.assertEqual(json.loads(output.getvalue()), reply)
