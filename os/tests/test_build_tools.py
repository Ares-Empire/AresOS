import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'os/ci'))
import build_tools
import image_diff
import rehearsal_auth


class BuildToolsTest(unittest.TestCase):
    def fixture(self, root):
        tools={}
        for name in build_tools.NAMES:
            file=root/name
            file.write_text('#!'+sys.executable+'\nprint("ABSOLUTE_TOOL_EXECUTED")\n')
            file.chmod(0o755)
            tools[name]=str(file.resolve())
        tools['python3']=str(pathlib.Path(sys.executable).resolve())
        tools['bash']=str(pathlib.Path(shutil.which('bash')).resolve())
        return tools

    def test_wrapper_validates_resolved_tools_and_diff_executes_without_path(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as directory:
            root=pathlib.Path(directory).resolve()
            tools=self.fixture(root)
            with patch.object(build_tools.shutil,'which',side_effect=lambda name:tools[name]):
                resolved=build_tools.resolve()
            manifest=root/'tools.json';manifest.write_text(json.dumps(resolved))
            environment=dict(os.environ,PATH='/no-host-tool-search',RUNNER_TEMP=str(root/'credentials-must-not-exist'))
            result=subprocess.run([resolved['bash'],str(ROOT/'os/ci/build-keyboard-release.sh'),resolved['python3'],str(manifest),'--check-tools'],
                                  cwd=ROOT,env=environment,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('BUILD_TOOLS_VALIDATED_WITHOUT_CREDENTIALS',result.stdout)
            self.assertFalse((root/'credentials-must-not-exist').exists())
            with patch.dict(os.environ,environment,clear=True),patch.object(image_diff,'TOOLS',resolved):
                self.assertEqual(image_diff.command('podman','--version'),'ABSOLUTE_TOOL_EXECUTED')
                self.assertEqual(image_diff.command('skopeo','--version'),'ABSOLUTE_TOOL_EXECUTED')

    def test_bad_paths_missing_keys_and_nonexecutables_stop_before_auth(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as directory:
            root=pathlib.Path(directory).resolve();tools=self.fixture(root)
            for name in build_tools.NAMES:
                for value in ('',name,str(root/'absent'),str(root)):
                    with self.subTest(name=name,value=value),patch.object(rehearsal_auth,'auth_file') as auth:
                        with self.assertRaisesRegex(RuntimeError,'STOP:'):
                            build_tools.build(dict(tools,**{name:value}))
                        auth.assert_not_called()
            with patch.object(build_tools.os,'access',return_value=False),patch.object(rehearsal_auth,'auth_file') as auth:
                with self.assertRaisesRegex(RuntimeError,'non-executable'):
                    build_tools.build(tools)
                auth.assert_not_called()
            with self.assertRaisesRegex(RuntimeError,'exactly'):
                build_tools.validate({})
            with patch.object(build_tools.shutil,'which',return_value=None),self.assertRaisesRegex(RuntimeError,'before credentials'):
                build_tools.resolve()
            for python in ('python3',str(root/'missing-python')):
                result=subprocess.run([tools['bash'],str(ROOT/'os/ci/build-keyboard-release.sh'),python,str(root/'absent.json')],
                                      cwd=ROOT,env=dict(os.environ,PATH='/no-host-tool-search'),capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('before credentials',result.stderr)

    def test_paths_are_explicit_at_sudo_and_resolution_precedes_secret_creation(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as directory:
            root=pathlib.Path(directory).resolve();tools=self.fixture(root)
            manifest=root/'tools.json';manifest.write_text(json.dumps(tools))
            with patch.object(sys,'argv',['build_tools','launch',str(manifest)]),patch.object(build_tools.subprocess,'run') as run:
                build_tools.main()
            argv=run.call_args.args[0]
            self.assertEqual(argv[:3],[tools['sudo'],'-E',tools['bash']])
            self.assertEqual(argv[-2:],[tools['python3'],str(manifest)])
        workflow=yaml.load((ROOT/'.github/workflows/os-image.yml').read_text(),Loader=yaml.BaseLoader)
        steps=workflow['jobs']['image']['steps']
        resolve,= [i for i,s in enumerate(steps) if s.get('run')=='python3 os/ci/build_tools.py resolve evidence/build-tools.json']
        auth,=[i for i,s in enumerate(steps) if s.get('run')=='sudo -E python3 os/ci/rehearsal_auth.py create']
        self.assertLess(resolve,auth)


if __name__=='__main__':
    unittest.main()
