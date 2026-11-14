"""The Mail tests' build-id.json fixture, and the missing-file path it skips."""
import importlib.util
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import support
from aresos_control.chrome import adapter
from aresos_control.engine import Engine


def source_build_hash():
    spec = importlib.util.spec_from_file_location('aresos_chrome_build_check', support.SOURCE_RUNTIME / 'chrome' / 'build.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_hash()


class BuildIdentity(unittest.TestCase):
    def engine(self, root):
        engine = Engine(root / 'state', root / 'independent')
        self.addCleanup(engine.close)
        return engine

    def test_fixture_is_an_installed_build_id_with_the_source_hash(self):
        installed = adapter.RUNTIME / 'chrome' / 'build-id.json'
        self.assertNotEqual(adapter.RUNTIME, support.SOURCE_RUNTIME)
        self.assertEqual(json.loads(installed.read_text()), {'build': source_build_hash()})
        with tempfile.TemporaryDirectory(dir=support.WORK) as temporary:
            with patch.object(adapter.Path, 'read_bytes', side_effect=AssertionError('Engine start hashed runtime files')):
                engine = self.engine(Path(temporary))
            self.assertEqual(engine.adapters['chrome'].qualification.build, source_build_hash())

    def test_missing_build_id_hashes_the_source_tree(self):
        self.assertFalse((support.SOURCE_RUNTIME / 'chrome' / 'build-id.json').exists())
        with tempfile.TemporaryDirectory(dir=support.WORK) as temporary, \
                patch.object(adapter, 'RUNTIME', support.SOURCE_RUNTIME):
            engine = self.engine(Path(temporary))
            self.assertEqual(engine.adapters['chrome'].qualification.build, source_build_hash())


if __name__ == '__main__':
    unittest.main()
