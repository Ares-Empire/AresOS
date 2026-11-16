"""The fixtures hold their own qualification record, whatever the shipped copy holds (#79)."""
import ast
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

import test_engine  # Installs the fixture runtime for this process.
import test_qualification_service
import test_state_fixes
import qualification_fixture as fixture
from aresos_control.chrome import adapter
from aresos_control.chrome import qualification as q
from aresos_control.chrome.bridge import Bridge
from aresos_control.chrome.qualification import validate_record
from aresos_control.engine import Engine
from test_policy import entry

ROOT = Path(__file__).resolve().parents[2]
# Fixture tests that write their own held record, act, restart, refresh or
# expect conservative mode for a Chrome major, so a shipped copy with history
# for this build would upset each of them.
SAMPLE = [
    'test_engine.Operations.test_group1_approval_first_exact_and_dispatch_once',
    'test_engine.Operations.test_review1_password_failure_refuses_before_any_binding_read',
    'test_qualification_service.Service.test_failed_patch_stays_off_on_unrecorded_patch_then_passing_patch_restores',
    'test_qualification_service.Service.test_failed_forced_refresh_for_an_uncovered_version_is_attempted_once_per_connection',
    'test_state_fixes.StateFixes.test_s1_restore_reconciles_revocation_readonly_and_qualification_offline',
]


def run(names, runtime):
    """Run the named tests with every Chrome they start reading runtime; returns the result."""
    result = unittest.TestResult()
    with patch.object(adapter, 'RUNTIME', runtime):
        unittest.defaultTestLoader.loadTestsFromNames(names).run(result)
    return result


# Constructing one of these starts a Chrome, which reads adapter.RUNTIME.
STARTS_CHROME = {'Engine', 'Chrome', 'Daemon'}


def starts_chrome(tree):
    """Whether a module's code calls Engine(, Chrome( or Daemon(, by name or as an attribute."""
    return any(isinstance(node, ast.Call) and (getattr(node.func, 'id', None) in STARTS_CHROME or
                                               getattr(node.func, 'attr', None) in STARTS_CHROME)
               for node in ast.walk(tree))


def imports_test_engine(tree):
    """Whether a module imports test_engine itself (import test_engine [as x], or from test_engine import ...)."""
    return any(isinstance(node, ast.Import) and any(alias.name == 'test_engine' for alias in node.names) or
               isinstance(node, ast.ImportFrom) and node.module == 'test_engine' and not node.level
               for node in ast.walk(tree))


class ShippedHistory(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=test_engine.WORK)
        self.root = Path(self.temporary.name)
        self.build = fixture.build_identity(fixture.SOURCE)
        # History an image might ship: another build, then this build's own
        # Chrome pair with every group failed (the key the fixtures write
        # themselves), then a passing beta of the next major.
        failed = entry(build=self.build, run='shipped')
        for category in ['core', 'adapters']:
            failed[category] = dict.fromkeys(failed[category], False)
        self.shipped = {'format': 1, 'entries': [entry(build='b'*64, run='shipped'), failed,
                                                 entry(build=self.build, version='158.0.1.0', channel='beta', run='shipped')]}
        validate_record(self.shipped)
        self.image = fixture.fixture_runtime(self.root/'image', baseline=self.shipped)

    def tearDown(self):
        self.temporary.cleanup()

    def test_fixture_records_meet_the_rollback_refusal_on_a_shipped_copy_with_history(self):
        # Without the fixture runtime, Chrome starts from the image's shipped
        # copy, and the unchanged service refuses each fixture's held record.
        result = run(SAMPLE, self.image)
        self.assertEqual(result.testsRun, len(SAMPLE))
        # A refused call reports the code; a raised refusal shows its message.
        refused = [test.id() for test, text in result.failures + result.errors
                   if 'qualification_rollback' in text or 'changed or removed held history' in text]
        self.assertEqual(sorted(refused), sorted(SAMPLE), result.failures + result.errors)

    def test_the_same_fixtures_pass_from_the_fixture_runtime_over_that_image(self):
        runtime = fixture.fixture_runtime(self.root/'fixture', source=self.image)
        self.assertEqual(json.loads((runtime/'chrome/qualification.json').read_text()), fixture.BASELINE)
        self.assertEqual(json.loads((runtime/'chrome/build-id.json').read_text()), {'build': self.build})
        result = run(SAMPLE, runtime)
        self.assertEqual(result.testsRun, len(SAMPLE))
        self.assertTrue(result.wasSuccessful(), result.failures + result.errors)

    def test_this_process_starts_chrome_from_the_fixture_runtime(self):
        # test_engine installed it on import; every Chrome test imports test_engine.
        self.assertNotEqual(adapter.RUNTIME, fixture.SOURCE)
        self.assertEqual(json.loads((adapter.RUNTIME/'chrome/qualification.json').read_text()), fixture.BASELINE)
        self.assertEqual(json.loads((adapter.RUNTIME/'chrome/build-id.json').read_text()), {'build': self.build})

    def test_a_fixture_runtime_is_shared_by_build_and_rewritten_only_when_it_differs(self):
        # A rewrite is os.replace of a new file, so it always shows as a new
        # inode, even where coarse timestamps keep the same mtime (#79 N2).
        def files(runtime):
            return {path: (info.st_ino, info.st_mtime_ns) for path in (runtime/'chrome').iterdir() for info in [path.stat()]}
        first = fixture.fixture_runtime(self.root/'shared')
        written = files(first)
        self.assertEqual(fixture.fixture_runtime(self.root/'shared'), first)
        self.assertEqual(files(first), written)
        (first/'chrome/qualification.json').write_text(json.dumps(self.shipped))
        fixture.fixture_runtime(self.root/'shared')
        self.assertEqual(json.loads((first/'chrome/qualification.json').read_text()), fixture.BASELINE)
        self.assertEqual(sorted(path.name for path in (first/'chrome').iterdir()), ['build-id.json', 'qualification.json'])

    def test_the_real_shipped_copy_is_a_valid_record_chrome_trusts(self):
        # The fixtures no longer read it, so this test does: a malformed or
        # reordered shipped copy would stop the installed service.
        shipped = json.loads((fixture.SOURCE/'chrome/qualification.json').read_text())
        validate_record(shipped)
        with patch('aresos_control.engine.Boundary'), patch.object(adapter, 'RUNTIME', fixture.SOURCE):
            engine = Engine(self.root/'state', self.root/'evidence')
        try:
            chrome = engine.adapters['chrome']
            self.assertEqual(chrome.qualification.build, self.build)
            self.assertEqual(chrome.qualification.shipped, shipped)
            self.assertEqual(chrome.qualification.record(), shipped)
        finally:
            engine.close()

    def test_the_browser_harness_installs_the_fixture_runtime_before_its_first_engine(self):
        source = (ROOT/'control/chrome/ci/service.py').read_text()
        self.assertIn("qualification_fixture.install(tempfile.mkdtemp(prefix='fixture-runtime-'),baseline=shipped)", source)
        self.assertIn('shipped=qualification_fixture.harness_shipped(os.environ)', source)
        self.assertLess(source.index('qualification_fixture.install('), source.index('Engine(config'))

    def test_a_held_record_extending_shipped_history_acts_and_an_uncovered_major_stays_conservative(self):
        # The laptop's state once the shipped copy holds history (#83, #79 N1):
        # the held record extends it with a later patch of this Chrome that
        # passes, after the shipped pair failed every group.
        held = {'format': 1, 'entries': [*self.shipped['entries'], entry(build=self.build, version='157.0.1.1', run='fetched')]}
        operations = test_engine.Operations('test_group1_approval_first_exact_and_dispatch_once')
        with patch.object(adapter, 'RUNTIME', self.image):
            operations.setUp()
        self.addCleanup(operations.tearDown)
        chrome = operations.chrome
        self.assertEqual(chrome.qualification.shipped, self.shipped)
        operations.engine.store.write({'chrome:qualification': held}, 'chrome_test_setup', 'Synthetic held record extending the shipped copy')
        operations.browser.version = '157.0.1.1'
        self.assertEqual(chrome.qualification.record(), held)
        mode = chrome.mode(acting=True)
        self.assertFalse(mode['conservative']); self.assertTrue(all(mode['core'].values())); self.assertTrue(all(mode['adapters'].values()))
        approval = operations.prepare(); self.assertEqual(operations.browser.dispatched, [])
        sent = operations.call('submit', approval); self.assertTrue(sent['ok'], sent)
        self.assertEqual(sent['data']['operation']['state'], 'done'); self.assertEqual(len(operations.browser.dispatched), 1)
        # A major neither history covers stays conservative, and a connection
        # forces one refresh for it; the daily gate holds the rest.
        bridge = Bridge(); bridge.session = 'connection-1'; bridge.version = '160.0.1.0'
        bridge.call = lambda name, **arguments: {'configured': True}
        chrome.bridge = bridge
        offline = urllib.error.URLError('offline fixture')
        with patch('aresos_control.chrome.uploads.prune'), patch.object(q.urllib.request, 'urlopen', side_effect=offline) as transport:
            for _ in range(3):
                self.assertTrue(chrome.mode()['conservative'])
        self.assertEqual(transport.call_count, 1)
        self.assertEqual(chrome.qualification.record(), held)
        self.assertIn('held record retained', operations.engine.store.get('chrome:qualification_fetch')['result'])

    def test_every_chrome_test_module_that_starts_a_chrome_imports_test_engine(self):
        # A module gets the fixture runtime only by importing test_engine; one
        # that starts a Chrome without it would trust the real shipped copy (#79 N3).
        self.assertTrue(starts_chrome(ast.parse('engine = aresos_control.engine.Engine(state, evidence)')))
        self.assertTrue(starts_chrome(ast.parse('chrome = Chrome(engine, record=shipped)')))
        self.assertFalse(starts_chrome(ast.parse('engine = make_engine()')))
        for code in ['import test_engine', 'import test_engine as fixture', 'from test_engine import Browser']:
            self.assertTrue(imports_test_engine(ast.parse(code)), code)
        self.assertFalse(imports_test_engine(ast.parse('import test_engine_helpers')))
        starting, missing = [], []
        for path in sorted((ROOT/'control/chrome_tests').glob('test_*.py')):
            tree = ast.parse(path.read_text(), str(path))
            if path.stem != 'test_engine' and starts_chrome(tree):
                starting.append(path.stem)
                if not imports_test_engine(tree):
                    missing.append(path.stem)
        self.assertIn('test_storage', starting)
        self.assertEqual(missing, [])


if __name__ == '__main__':
    unittest.main()
