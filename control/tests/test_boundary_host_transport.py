"""Transport failures never stand in for an enforced AF_VSOCK denial."""
import ast
import errno
import json
from pathlib import Path
import unittest


class HostTransport(unittest.TestCase):
    def probe(self,name,error=None):
        source=Path(__file__).resolve().parents[1]/'boundary/hostile.py'
        function=next(node for node in ast.parse(source.read_text()).body if isinstance(node,ast.FunctionDef) and node.name=='attempt')
        scope={'errno':errno,'json':json,'results':[],'print':lambda *args,**kwargs:None}
        exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),scope)
        def operation():
            if error is not None:raise OSError(error,'Synthetic transport result')
        scope['attempt'](name,operation)
        return scope['results'][0]

    def test_reset_and_timeout_are_unqualified_not_policy_denials(self):
        for error in [errno.ECONNRESET,errno.ETIMEDOUT]:
            with self.subTest(error=error):
                row=self.probe('connect:vsock',error)
                self.assertFalse(row['blocked']);self.assertTrue(row.get('unqualified'))
                self.assertEqual(row['classification'],'no-qualified-host-endpoint')

    def test_a_successful_vsock_connect_remains_an_open_route(self):
        row=self.probe('connect:vsock')
        self.assertFalse(row['blocked']);self.assertFalse(row.get('unqualified'))

    def test_policy_denials_remain_blocked_without_transport_excuses(self):
        for error in [errno.EPERM,errno.EACCES]:
            row=self.probe('connect:vsock',error)
            self.assertTrue(row['blocked']);self.assertFalse(row.get('unqualified'))

    def test_another_socket_cannot_use_the_vsock_transport_classification(self):
        row=self.probe('connect:act',errno.ECONNRESET)
        self.assertFalse(row['blocked']);self.assertFalse(row.get('unqualified'))
