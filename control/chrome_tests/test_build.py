import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('chrome_build',ROOT/'control/chrome/build.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)


class Build(unittest.TestCase):
    def test_complete_installed_runtime_including_shared_approval_changes_identity(self):
        files=list(build.inputs())
        for name in ['control/aresos_control/engine.py','control/aresos_control/storage.py','control/aresos_control/common.py',
                     'control/chrome/extension/page.js','control/chrome/native_host.py','control/requirements.lock']:
            self.assertIn(ROOT/name,files)
        self.assertNotIn(ROOT/'control/chrome/qualification.json',files)
        with tempfile.TemporaryDirectory(dir=ROOT/'.work/20-chrome') as directory:
            copied=Path(directory)
            for path in files:
                destination=copied/path.relative_to(ROOT);destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,destination)
            before=build.build_hash(copied)
            path=copied/'control/aresos_control/engine.py';path.write_text(path.read_text()+'\n# synthetic qualification change\n')
            self.assertNotEqual(before,build.build_hash(copied))

    def test_runtime_inventory_includes_entrypoints_definitions_settings_and_every_extension_asset(self):
        files = set(build.inputs())
        for relative in ['control/packaging/aresos', 'control/packaging/aresos-mcp', 'control/packaging/aresos-toold',
                         'control/aresos_control/definitions.py', 'control/aresos_control/chrome/definitions.py',
                         'control/aresos_control/chrome/unicode_words.json', 'control/aresos_control/chrome/qualification.py',
                         'control/settings/service.json', 'control/launch.py', 'control/chrome/build.py']:
            self.assertIn(ROOT/relative, files)
        # Match the complete packages installed by ci/setup.sh, independent of
        # the hashing implementation's individual file names.
        for directory in ['aresos_control', 'generated', 'chrome/extension']:
            expected = {path for path in (ROOT/'control'/directory).rglob('*')
                        if path.is_file() and '__pycache__' not in path.parts}
            self.assertTrue(expected <= files)
        self.assertEqual(len(list(build.inputs())), len(files))

    def test_clean_runtime_copy_has_same_identity_and_every_runtime_area_changes_it(self):
        files = list(build.inputs())
        with tempfile.TemporaryDirectory(dir=ROOT/'.work/20-chrome') as directory:
            copied = Path(directory)
            for path in files:
                destination = copied/path.relative_to(ROOT)
                destination.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, destination)
            original = build.build_hash()
            self.assertEqual(build.build_hash(copied), original)
            for relative in ['aresos_control/engine.py', 'aresos_control/storage.py', 'aresos_control/boundary.py',
                             'aresos_control/chrome/unicode_words.json', 'chrome/extension/page.js',
                             'chrome/native_host.py', 'packaging/aresos-mcp', 'requirements.lock']:
                path = copied/'control'/relative
                with self.subTest(path=relative):
                    original_bytes = path.read_bytes()
                    path.write_bytes(original_bytes+b'\nfixture runtime change\n')
                    self.assertNotEqual(build.build_hash(copied), original)
                    path.write_bytes(original_bytes)
            new_asset = copied/'control/chrome/extension/fixture-icon.txt'
            new_asset.write_text('fixture drawn asset')
            self.assertNotEqual(build.build_hash(copied), original)
            new_asset.unlink()
            (copied/'control/chrome/qualification.json').write_text('fixture delivery data')
            (copied/'control/chrome/build-id.json').write_text('fixture generated installed identity')
            self.assertEqual(build.build_hash(copied), original)
            shutil.rmtree(copied/'control/aresos_control')
            with self.assertRaises(ValueError): build.build_hash(copied)
