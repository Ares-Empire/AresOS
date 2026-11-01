import copy,hashlib,importlib.util,json,pathlib,re,unittest
from unittest.mock import patch
R=pathlib.Path.cwd();W=R/'.work/14';spec=importlib.util.spec_from_file_location('review',W/'14zzb-classify.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
ROWS=c.read_json(W/'gitleaks/14zz-probe-artifact.json')
BAD=next(x for x in ROWS if x['File'].endswith('live-ui-probe-boot-console.txt') and x['StartLine']==554)

class WholeSourceTest(unittest.TestCase):
 def context(self,row=None):
  row=copy.deepcopy(BAD if row is None else row);s=c.Sources();p=R/row['File'];line=s.line(p,row);span=c.pinned.KERNEL.fullmatch(line).span('fingerprint');return row,s,p,line,span
 def test_refused_probe30_and_earlier_accepted_509_findings(self):
  for run,scan in ((41301148135,'14zz-probe-artifact.json'),(41290621860,'14zy-probe-artifact.json')):
   v=c.classify(run,W/'gitleaks'/scan);self.assertEqual(v['findings'],509);self.assertEqual(len(v['iso_filename_findings']),507);self.assertEqual(len(v['kernel_certificate_findings']),2)
   self.assertTrue(all(x['line_sha256'] for x in v['iso_filename_findings']+v['kernel_certificate_findings']))
 def test_exact_refused_partial_fingerprint_passes_without_a_quote(self):
  row,s,p,line,span=self.context();self.assertEqual(row['Match'],'key: REDACTED');self.assertIsNone(re.fullmatch(r"key: REDACTED'",row['Match']))
  proof=s.cross(p,row,line,span);self.assertLess(proof['source_secret_end_column']-proof['source_secret_start_column']+1,40);self.assertFalse(proof['redacted_excerpt_used_for_classification'])
 def test_full_logs_current_and_earlier_real_four_findings(self):
  for run,scan,folder,basic in ((41301148135,'14zz-41301148135-full-logs.json','14zz/basic-41301148135/full-logs','14zz/basic-41301148135'),(41290621860,'14zy-41290621860-all-logs.json','14zy/logs-41290621860','14zy/basic-41290621860'),(41305049425,'14zz-41305049425-full-logs.json','14zz/basic-41305049425/full-logs','14zz/basic-41305049425')):
   jobs=c.read_json(W/basic/'jobs.json');head=c.read_json(W/basic/'receipt.json')['head'];v=c.classify_logs(run,W/'gitleaks'/scan,W/folder,jobs,head)
   self.assertEqual(v['findings'],4);self.assertTrue(all(x['cross_check']['status']=='passed' for x in v['cosign_checksum_findings']))
   if run==41305049425:self.assertEqual(v['combined_log'],'1_Pinned live ISO inspection and two-disk rehearsal.txt')
 def test_missing_combined_log_refuses(self):
  folder=W/'14zz/basic-41305049425/full-logs';basic=folder.parent;jobs=c.read_json(basic/'jobs.json');head=c.read_json(basic/'receipt.json')['head'];original=pathlib.Path.iterdir
  def files(p):return iter(x for x in original(p) if x.name!='1_Pinned live ISO inspection and two-disk rehearsal.txt') if p==folder else original(p)
  with patch.object(pathlib.Path,'iterdir',files),self.assertRaisesRegex(AssertionError,'missing or ambiguous'):c.classify_logs(41305049425,W/'gitleaks/14zz-41305049425-full-logs.json',folder,jobs,head)
 def test_ambiguous_combined_log_refuses(self):
  folder=W/'14zz/basic-41305049425/full-logs';basic=folder.parent;jobs=c.read_json(basic/'jobs.json');head=c.read_json(basic/'receipt.json')['head'];ghost=folder/'0_Pinned live ISO inspection and two-disk rehearsal.txt';old_iter=pathlib.Path.iterdir;old_file=pathlib.Path.is_file
  def files(p):return iter([*old_iter(p),ghost]) if p==folder else old_iter(p)
  with patch.object(pathlib.Path,'iterdir',files),patch.object(pathlib.Path,'is_file',lambda p:True if p==ghost else old_file(p)),self.assertRaisesRegex(AssertionError,'missing or ambiguous'):c.classify_logs(41305049425,W/'gitleaks/14zz-41305049425-full-logs.json',folder,jobs,head)
 def test_unknown_or_extended_source_line_refuses_despite_old_valid_excerpt(self):
  for prefix,suffix in (('unexpected ',''),('',' extra')):
   old=c.Sources.line
   def altered(s,path,row):
    line=old(s,path,row)
    return prefix+line+suffix if row['StartLine']==554 else line
   with self.subTest(prefix=prefix),patch.object(c.Sources,'line',altered),self.assertRaisesRegex(AssertionError,'complete kernel'):
    c.classify(41301148135,W/'gitleaks/14zz-probe-artifact.json')
 def test_secret_outside_certificate_token_refuses(self):
  row,s,p,line,span=self.context();row.update(StartColumn=58,EndColumn=61,Match='REDACTED')
  with self.assertRaisesRegex(AssertionError,'inside the approved token'):s.cross(p,row,line,span)
 def test_redacted_excerpt_wrong_prefix_suffix_or_missing_marker_refuses(self):
  for text in ('wrong: REDACTED','key: REDACTEDwrong','REDACTEDREDACTED','nothing'):
   row,s,p,line,span=self.context();row['Match']=text
   with self.subTest(shape=text),self.assertRaises(AssertionError):s.cross(p,row,line,span)
 def test_unredacted_or_missing_secret_refuses(self):
  for value in ('WRONG',None,''):
   row,s,p,line,span=self.context();row['Secret']=value
   with self.subTest(value=value),self.assertRaisesRegex(AssertionError,'fully redacted'):s.cross(p,row,line,span)
 def test_invalid_columns_refuse(self):
  for first,last in ((0,4),(-1,4),(9,3),(True,4),(1,1000000)):
   row,s,p,line,span=self.context();row.update(StartColumn=first,EndColumn=last)
   with self.subTest(cols=(first,last)),self.assertRaises(AssertionError):s.cross(p,row,line,span)
 def test_missing_or_out_of_bounds_or_multiline_source_refuses(self):
  for n,end in ((0,0),(100000000,100000000),(554,555)):
   row=copy.deepcopy(BAD);row.update(StartLine=n,EndLine=end)
   with self.subTest(line=n),self.assertRaises(AssertionError):c.Sources().line(R/row['File'],row)
  with self.assertRaisesRegex(AssertionError,'cannot be read'):c.Sources().line(W/'14zza/no-such-source.txt',BAD)
 def test_unreadable_and_non_utf8_source_stop_clearly(self):
  with patch.object(pathlib.Path,'read_bytes',side_effect=PermissionError('fixture refusal')),self.assertRaisesRegex(AssertionError,'cannot be read'):c.Sources().line(R/BAD['File'],BAD)
  row=dict(BAD,StartLine=1,EndLine=1)
  with patch.object(pathlib.Path,'read_bytes',return_value=b'\xff\n'),self.assertRaisesRegex(AssertionError,'not UTF-8'):c.Sources().line(R/BAD['File'],row)
 def test_iso_reference_line_is_exact_and_target_is_the_only_approved_token(self):
  ref=c.iso_reference();row=next(x for x in ROWS if x['File'].endswith('squashfs-files.txt'));s=c.Sources();p=R/row['File'];line=s.line(p,row);span=c.iso_line(line,row['StartLine'],ref)
  s.cross(p,row,line,span)
  with self.assertRaisesRegex(AssertionError,'507 approved'):c.iso_line(line+' extra',row['StartLine'],ref)
  wrong=dict(row,StartColumn=2,EndColumn=5,Match='REDACTED')
  with self.assertRaisesRegex(AssertionError,'inside the approved token'):s.cross(p,wrong,line,span)
 def test_iso_reference_source_hash_must_match(self):
  target=W/'run-41290621860/evidence/installer/squashfs-files.txt';old=pathlib.Path.read_bytes
  with patch.object(pathlib.Path,'read_bytes',lambda p:b'changed' if p==target else old(p)),self.assertRaisesRegex(AssertionError,'reference differs'):c.iso_reference()
 def test_wrong_pinned_cosign_step_still_refuses(self):
  folder=W/'14zz/basic-41301148135';jobs=c.read_json(folder/'jobs.json');head=c.read_json(folder/'receipt.json')['head']
  for job in jobs['jobs']:
   for step in job['steps']:
    if 'sigstore/cosign-installer@' in step['name']:step['name']=step['name'].replace(c.pinned.COSIGN_COMMIT,'0'*40)
  with self.assertRaisesRegex(AssertionError,'pinned cosign step'):c.classify_logs(41301148135,W/'gitleaks/14zz-41301148135-full-logs.json',folder/'full-logs',jobs,head)
 def test_cosign_unknown_value_and_non_whole_line_refuse(self):
  values=c.pinned.cosign_source();line="RELEASE_COSIGN_PUB_KEY_SHA='"+next(iter(values))+"'"
  for invalid in (line.replace(next(iter(values)),'0'*64),'echo '+line,line+'; true'):
   with self.subTest(shape=invalid[:20]),self.assertRaises(AssertionError):c.pinned.cosign_line(invalid,values)

if __name__=='__main__':unittest.main(verbosity=2)
