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
