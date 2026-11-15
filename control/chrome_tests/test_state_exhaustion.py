"""A failed read-only close must not hide committed owner facts."""
from pathlib import Path
import sys
import unittest

import test_engine as fixture
from aresos_control.common import Refused
from state_views import StateViews
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mail_tests'))
from storage_faults import OSWrites


class Exhaustion(StateViews,unittest.TestCase):
    setUp=fixture.Operations.setUp
    tearDown=fixture.Operations.tearDown
    call=fixture.Operations.call
    target=fixture.Operations.target
    prepare=fixture.Operations.prepare

    def test_s11_persistent_write_exhaustion_retains_exact_committed_disclosure(self):
        self.begin_views('persistent_exhaustion')
        approval=self.prepare();operation=self.engine.operation(approval['operation_id'])
        operation['state']='submitting'
        self.engine.store.write({'op:'+operation['id']:operation},'chrome_submit','Synthetic committed input context',operation['id'])
        expected={'recovery-'+operation['id']}
        injector=OSWrites(1,'persistent')
        with injector.wrap(self.engine.store):
            with self.assertRaises((Refused,OSError)):
                self.engine.store.write({},'chrome_fixture','Synthetic failed write')
            self.assertTrue(injector.failed)
            current=self.engine.pending(resolve_checks=False)
            self.assertEqual({item['operation_id'] for item in current['notices'] if item['app']=='chrome'},expected)
            self.compare_views('persistent')
        self.compare_views('space_restored')
        self.assertEqual(self.browser.dispatched,[])
