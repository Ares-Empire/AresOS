import importlib.util,pathlib,unittest
from unittest.mock import patch
R=pathlib.Path.cwd();s=importlib.util.spec_from_file_location('control',R/'.work/14/14zza/control.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
class ControlBindingTest(unittest.TestCase):
 def test_real_metadata_only_followup_keeps_existing_pushed_head(self):self.assertEqual(c.source_gate(),'10921f81f481bd2b2c7bfb2da9e13deabdb1267f')
 def test_implementation_difference_requires_a_new_round(self):
  original=c.c.out
  def output(*args):return 'os/ci/owner_vm.py' if args==('git','diff','--name-only',c.TARGET,c.LOCAL) else original(*args)
  with patch.object(c.c,'out',side_effect=output),self.assertRaisesRegex(AssertionError,'implementation differs'):c.source_gate()
 def test_changed_local_review_head_refuses(self):
  original=c.c.out
  def output(*args):return '0'*40 if args==('git','rev-parse','HEAD') else original(*args)
  with patch.object(c.c,'out',side_effect=output),self.assertRaisesRegex(AssertionError,'local review commit changed'):c.source_gate()
 def test_changed_classifier_after_tests_refuses(self):
  original=pathlib.Path.read_bytes;target=R/'.work/14/14zza/classify.py'
  with patch.object(pathlib.Path,'read_bytes',lambda p:b'changed' if p==target else original(p)),self.assertRaisesRegex(AssertionError,'new local tool changed'):c.source_gate()
if __name__=='__main__':unittest.main(verbosity=2)
