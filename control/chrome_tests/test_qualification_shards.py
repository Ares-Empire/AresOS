"""A current driver must be aggregated against that same inventory on older builds."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'.work/post18d/qualification-shard-tests'

class QualificationShards(unittest.TestCase):
    def test_old_runtime_current_driver_merge_preserves_production_and_uses_one_inventory(self):
        WORK.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=WORK) as folder:
            root=Path(folder);runtime=root/'runtime';driver=root/'driver';proofs=root/'proofs';out=root/'out'
            tests=runtime/'control/chrome_tests';tests.mkdir(parents=True)
            (tests/'test_old.py').write_text('# older test\n')
            current=driver/'control/chrome_tests';current.mkdir(parents=True)
            names=['test_old','test_new','test_added','test_other']
            for name in names:(current/(name+'.py')).write_text('# current driver test\n')
            production=runtime/'control/aresos_control/production.py';production.parent.mkdir();production.write_text('# immutable shipped runtime\n')
            original=hashlib.sha256(production.read_bytes()).hexdigest()
            for index,name in enumerate(names):
                folder=proofs/str(index);folder.mkdir(parents=True)
                (folder/f'python-shard-{index}.json').write_text(json.dumps({'index':index,'count':4,'head':'a'*40,'run':'123','modules':[name],'tests':1,'successful':True}))
                (folder/'python.txt').write_text('Ran 1 test\nOK\n')
            command=[sys.executable,'-B',str(ROOT/'control/chrome/ci/merge-python.py'),str(proofs),str(out)]
            # Both workflow identities belong to this synthetic proof; an
            # outer qualification/local run may set a different runtime head.
            env={**os.environ,'GITHUB_SHA':'a'*40,'RUNTIME_COMMIT':'a'*40,'GITHUB_RUN_ID':'123'}
            before=subprocess.run(command,cwd=runtime,env=env,capture_output=True,text=True)
            self.assertNotEqual(before.returncode,0)
            self.assertIn('AssertionError',before.stderr)
            shutil.copytree(current,tests,dirs_exist_ok=True)
            after=subprocess.run(command,cwd=runtime,env=env,capture_output=True,text=True)
            self.assertEqual(after.returncode,0,after.stderr)
            self.assertEqual(json.loads((out/'python-shards.json').read_text())['modules'],sorted(names))
            self.assertEqual(hashlib.sha256(production.read_bytes()).hexdigest(),original)
        workflow=(ROOT/'.github/workflows/control-chrome-qualification.yml').read_text()
        combined=workflow.split('  qualification-combine:')[1].split('  qualification-publish:')[0]
        self.assertLess(combined.index('cp -R ../driver/control/chrome_tests/.'),combined.index('merge-python.py'))

    def test_python_shard_launcher_is_import_safe_for_spawned_workers(self):
        WORK.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=WORK) as folder:
            root=Path(folder);script=root/'control/chrome/ci/python-shard.py';script.parent.mkdir(parents=True)
            shutil.copyfile(ROOT/'control/chrome/ci/python-shard.py',script)
            tests=root/'control/chrome_tests';tests.mkdir(parents=True)
            (tests/'test_spawn_probe.py').write_text("""import multiprocessing
import unittest

def work(queue):
    queue.put('separate worker completed')

class Probe(unittest.TestCase):
    def test_worker_completes_without_reentering_the_suite(self):
        context=multiprocessing.get_context('spawn');queue=context.Queue()
        child=context.Process(target=work,args=(queue,));child.start();child.join(10)
        if child.is_alive():child.terminate();child.join()
        self.assertEqual(child.exitcode,0)
        self.assertEqual(queue.get(timeout=1),'separate worker completed')
""")
            out=root/'out';env={**os.environ,'PYTHON_SHARD':'0','TEST_OUT':str(out)}
            result=subprocess.run([sys.executable,'-B',str(script)],env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            proof=json.loads((out/'python-shard-0.json').read_text())
            self.assertTrue(proof['successful']);self.assertEqual(proof['tests'],1)
            self.assertEqual(proof['modules'],['test_spawn_probe'])

    def test_every_immutable_pair_expands_to_the_complete_partition_under_matrix_limit(self):
        WORK.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=WORK) as folder:
            plan={'include':[{'build':str(build)*64,'channel':channel,'repeat':repeat} for build in range(4) for channel in ['stable','beta'] for repeat in [1,2]]}
            file=Path(folder)/'plan.json';file.write_text(json.dumps(plan))
            result=subprocess.run([sys.executable,'-B',str(ROOT/'control/chrome/ci/qualification-shards.py'),str(file)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr);rows=json.loads(result.stdout)['include']
            self.assertEqual(len(rows),224)
            for pair in plan['include']:
                selected=[row for row in rows if all(row[key]==value for key,value in pair.items())]
                self.assertEqual(len(selected),14);self.assertEqual(len({row['shard'] for row in selected}),14)
                self.assertTrue(all({key:value for key,value in row.items() if key!='shard'}==pair for row in selected))
