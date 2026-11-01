"""Exact public-checksum lines in retained, pinned-action log sections only."""
import copy
import hashlib
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('artifact_review',ROOT/'reviews/14-owner-tools/classify-artifacts.py')
review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)
FIX=ROOT/'os/tests/fixtures/owner-tools'


class CosignLogClassTest(unittest.TestCase):
    def materialize(self,folder):
        source=json.loads((ROOT/'os/manifest/ci/14/14zz-cosign/source.json').read_text())
        binding=json.loads((FIX/'14zz-cosign-log-sources.json').read_text())
        job=json.loads((FIX/'14zy-probe29-job.json').read_text())
        targets=[folder/job['name']/('12_Run sigstore_cosign-installer@'+review.COSIGN_COMMIT+'.txt'),
                 folder/('0_'+job['name']+'.txt')]
        findings=[]
        for row,target in zip(binding['fixtures'],targets):
            raw=(ROOT/row['path']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256'])
            for i,value in enumerate(source['checksums']):raw=raw.replace(('@SHA'+str(i)+'@').encode(),value.encode())
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            for n,line in enumerate(review.log_lines(target),1):
                if 'RELEASE_COSIGN_PUB_KEY_SHA=' in line:
                    findings.append(dict(File=str(target),RuleID='generic-api-key',StartLine=n,EndLine=n))
        scan=folder/'scan.json';scan.write_text(json.dumps(findings))
        return job,scan,findings,targets

    def test_exact_four_retained_findings_pass_in_step_and_combined(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as directory:
            folder=pathlib.Path(directory);job,scan,rows,_=self.materialize(folder)
            result=review.classify_logs(job['run_id'],scan,folder,dict(total_count=1,jobs=[job]),job['head_sha'])
            self.assertEqual(result['findings'],4)
            self.assertEqual(len({r['sha256'] for r in result['cosign_checksum_findings']}),2)
            self.assertEqual(result['source']['sha256'],review.COSIGN_SHA256)

    def test_line_shape_unknown_checksum_prefix_suffix_color_or_quotes_refuse(self):
        values=review.cosign_source();value=next(iter(values));line="RELEASE_COSIGN_PUB_KEY_SHA='"+value+"'"
        review.cosign_line(line,values)
        for bad in (line.replace(value,'0'*64),'echo '+line,line+'; true',line.replace("'",'"'),
                    '\x1b[31m'+line+'\x1b[0m',line+'\x1b[0m',line+'\nextra'):
            with self.subTest(shape=bad[:20]),self.assertRaises(AssertionError):review.cosign_line(bad,values)

    def test_copy_outside_pinned_section_wrong_file_rule_or_identity_refuses(self):
        for defect in ('outside','file','rule','identity','multiline','unmatched-block'):
            with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as directory:
                folder=pathlib.Path(directory);job,scan,rows,targets=self.materialize(folder)
                if defect=='outside':
                    raw=targets[1].read_text();line=review.log_lines(targets[1])[rows[-1]['StartLine']-1]
                    targets[1].write_text(raw+'\n'+line+'\n');n=len(review.log_lines(targets[1]));rows=[dict(rows[-1],StartLine=n,EndLine=n)]
                elif defect=='file':
                    wrong=folder/'unrelated.txt';wrong.write_bytes(targets[0].read_bytes());rows=[dict(rows[0],File=str(wrong))]
                elif defect=='rule':rows[0]['RuleID']='other'
                elif defect=='identity':job['head_sha']='b'*40
                elif defect=='multiline':rows[0]['EndLine']+=1
                else:targets[1].write_text(targets[1].read_text().replace('##[group]Run sigstore','##[group]Run another',1))
                scan.write_text(json.dumps(rows))
                with self.subTest(defect=defect),self.assertRaises(AssertionError):
                    review.classify_logs(41290621860,scan,folder,dict(total_count=1,jobs=[job]),'cbaa985ed81eaea268d6f261cb212048da69d9cc')

    def test_wrong_pinned_action_name_is_not_an_approved_step(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as directory:
            folder=pathlib.Path(directory);job,scan,_,_=self.materialize(folder)
            for s in job['steps']:
                if 'sigstore/cosign-installer@' in s['name']:s['name']=s['name'].replace(review.COSIGN_COMMIT,'0'*40)
            with self.assertRaisesRegex(AssertionError,'pinned cosign step'):
                review.classify_logs(job['run_id'],scan,folder,dict(total_count=1,jobs=[job]),job['head_sha'])


if __name__=='__main__':unittest.main()
