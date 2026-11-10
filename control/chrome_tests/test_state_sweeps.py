"""Parallel sweep completion and worker failures must reach the parent test."""
import os
import unittest

from state_sweeps import isolated_flows


class Probe:
    def __init__(self,methodName='runTest'):pass
    def setUp(self):pass
    def tearDown(self):pass
    def sweep_flow(self,flow):
        if flow=='failure':raise AssertionError('injected worker assertion')
        assert os.getpid()!=int(flow.split(':')[0]), 'Fault sweep ran in the parent process'
        return {'single':1,'persistent':1,'pairs':2}


class SweepWorkers(unittest.TestCase):
    def test_all_independent_flows_run_in_separate_processes(self):
        counts=isolated_flows(Probe(),[f'{os.getpid()}:first',f'{os.getpid()}:second'])
        self.assertEqual(counts,{'single':2,'persistent':2,'pairs':4})

    def test_child_assertion_fails_the_parent(self):
        with self.assertRaisesRegex(AssertionError,'injected worker assertion'):
            isolated_flows(Probe(),[f'{os.getpid()}:first','failure'])
