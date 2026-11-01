"""14zza local evidence review: whole source first; redaction only cross-checks."""
import hashlib,importlib.util,json,pathlib,re,sys
ROOT=pathlib.Path.cwd().resolve()
PIN='6d0467153f768f2e714d26d4bc465c653a2450ec44990f76de1bcb465386ec61'
ISO_PIN='29ca18709f430342120192ad4b5fab9b7136c257eb30bb436d3dfd45cee81a98'
ISO_SCAN_PIN='84e366dfd748b8c3798d7aabbc58f10298499ca75c81b1317c7503207b355498'
source=ROOT/'reviews/14-owner-tools/classify-artifacts.py'
assert hashlib.sha256(source.read_bytes()).hexdigest()==PIN,'STOP: pushed reviewer library differs'
spec=importlib.util.spec_from_file_location('pinned_review',source);pinned=importlib.util.module_from_spec(spec);spec.loader.exec_module(pinned)
ISO_LINE=re.compile(r'lrwxrwxrwx root/root +[0-9]+ [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2} squashfs-root/[^\s]+ -> (?P<token>[^\s]+)')

def read_json(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def sha(raw):return hashlib.sha256(raw).hexdigest()

class Sources:
 def __init__(self):self.cache={}
 def line(self,path,row):
  path=pathlib.Path(path).resolve()
  n=row.get('StartLine');assert type(n) is int and n==row.get('EndLine'),'STOP: multiline or malformed finding'
  if path not in self.cache:
   assert path.is_file(),'STOP: finding source cannot be read'
   try:raw=path.read_bytes()
   except OSError as error:raise AssertionError('STOP: finding source cannot be read') from error
   lines=raw.split(b'\n');offsets=[];offset=0
   for value in lines:offsets.append(offset);offset+=len(value)+1
   self.cache[path]=(raw,lines,offsets)
  raw,lines,offsets=self.cache[path];assert 1<=n<=len(lines),'STOP: finding source line cannot be read'
  try:line=lines[n-1].removesuffix(b'\r').decode('utf-8')
  except UnicodeDecodeError as error:raise AssertionError('STOP: finding source line is not UTF-8') from error
  # Gitleaks recognizes a UTF-8 BOM only at the start of the file.
  if n==1:line=line.removeprefix('\ufeff')
  return line
 def cross(self,path,row,line,span):
  raw,lines,offsets=self.cache[pathlib.Path(path).resolve()];n=row['StartLine']-1
  start=offsets[n];content=start+(3 if n==0 and lines[n].startswith(b'\xef\xbb\xbf') else 0)
  return cross_check(line,row,span,(raw,start,content,start+len(lines[n])))

def cross_check(line,row,token_span,location):
 """Replay v8.21.2 detect/location.go coordinates in its 10,000-byte chunks."""
 assert row.get('Secret')=='REDACTED','STOP: expected fully redacted secret metadata'
 match=row.get('Match');assert isinstance(match,str) and match.count('REDACTED')==1,'STOP: malformed redacted excerpt'
 first,last=row.get('StartColumn'),row.get('EndColumn')
 assert type(first) is int and type(last) is int and 1<=first<=last,'STOP: invalid source columns'
 before,after=(x.encode('utf-8') for x in match.split('REDACTED'))
 raw,line_start,content_start,line_end=location
 start,end=(content_start+len(line[:n].encode('utf-8')) for n in token_span)
 candidates=[]
 # location.go retains the previous LF byte as its anchor; the first line of
 # a chunk instead uses zero. directory.go independently scans fixed chunks.
 for chunk in range(line_start//10000*10000,(line_end//10000+1)*10000,10000):
  anchor=line_start-1 if line_start>chunk else chunk
  a0,b0=anchor+first-1,anchor+last
  if not (max(chunk,line_start)<=a0<b0<=min(chunk+10000,line_end)):continue
  fragment=raw[a0:b0]
  if not (fragment.startswith(before) and fragment.endswith(after)):continue
  a,b=a0+len(before),b0-len(after)
  if start<=a<b<=end:candidates.append((a,b,chunk))
 assert len(candidates)==1,'STOP: redacted excerpt/source columns do not uniquely locate a secret inside the approved token'
 a,b,chunk=candidates[0]
 return dict(status='passed',match_start_column=first,match_end_column=last,source_secret_start_column=a-content_start+1,source_secret_end_column=b-content_start,approved_token_start_column=start-content_start+1,approved_token_end_column=end-content_start,scanner_chunk_start=chunk,redacted_excerpt_used_for_classification=False)

def iso_reference():
 base=ROOT/'.work/14/run-41290621860/evidence/installer/squashfs-files.txt'
 raw=base.read_bytes();assert sha(raw)==ISO_PIN,'STOP: public ISO listing reference differs from retained approved bytes'
 scan=ROOT/'.work/14/gitleaks/14zy-probe-artifact.json'
 assert sha(scan.read_bytes())==ISO_SCAN_PIN,'STOP: approved filename scan reference changed'
 rows=read_json(scan)
 rows=[x for x in rows if x['File'].replace('\\','/').endswith('/installer/squashfs-files.txt')]
 assert len(rows)==507 and len({x['StartLine'] for x in rows})==507,'STOP: approved public filename reference is incomplete'
 lines=raw.split(b'\n');result={}
 for row in rows:
  assert row['RuleID']=='generic-api-key' and row['StartLine']==row['EndLine']
  line=lines[row['StartLine']-1].removesuffix(b'\r').decode('utf-8')
  match=ISO_LINE.fullmatch(line);assert match,'STOP: reference is not a complete public ISO filename line'
  result[row['StartLine']]=line
 return result

def iso_line(line,number,reference):
 assert reference.get(number)==line,'STOP: filename line is not one of the 507 approved public ISO names'
 match=ISO_LINE.fullmatch(line);assert match,'STOP: malformed public ISO filename source line'
 return match.span('token')

def classify(run,scan):
 run=int(run);base=ROOT/'.work/14'/f'run-{run}';evidence=(base/'evidence').resolve();captured=evidence/'two-disk';listing=evidence/'installer/squashfs-files.txt'
 rows=read_json(scan);assert isinstance(rows,list),'STOP: malformed artifact scan'
 sources=Sources();reference=iso_reference();certs=[];iso=[];seen=set()
 assert sha(listing.read_bytes())==ISO_PIN,'STOP: artifact listing differs from approved pinned ISO listing'
 for row in rows:
  assert row['RuleID']=='generic-api-key','STOP: unapproved artifact rule'
  path=(ROOT/row['File'].replace('\\','/')).resolve();assert path.is_relative_to(evidence),'STOP: finding path outside current artifact'
  line=sources.line(path,row);key=(path,row['StartLine'],row.get('StartColumn'),row.get('EndColumn'));assert key not in seen,'STOP: duplicate finding';seen.add(key)
  item=dict(line_sha256=sha(line.encode()),path=path.relative_to(evidence).as_posix(),line=row['StartLine'],rule=row['RuleID'])
  if path==listing:
   span=iso_line(line,row['StartLine'],reference);item.update(classification='14s one of the 507 exact public ISO symlink name lines',cross_check=sources.cross(path,row,line,span));iso.append(item)
  else:
   assert path.parent==captured and re.fullmatch(r'[a-z0-9-]+-boot-console\.txt',path.name),'STOP: finding outside captured boot console'
   match=pinned.KERNEL.fullmatch(line);assert match,'STOP: source is not a complete kernel X.509 boot message'
   item.update(classification='14v exact complete public kernel X.509 certificate message',certificate_label=match['label'],fingerprint_hex_length=40,cross_check=sources.cross(path,row,line,match.span('fingerprint')));certs.append(item)
 assert len(iso)==507 and len({x['line'] for x in iso})==507,'STOP: public ISO filename finding count differs'
 return dict(status='passed',run=run,head=read_json(base/'receipt.json')['head'],scan=dict(sha256=sha(pathlib.Path(scan).read_bytes()),path=pathlib.Path(scan).resolve().relative_to(ROOT).as_posix()),findings=len(rows),iso_listing_findings=507,iso_listing_source_sha256=ISO_PIN,iso_filename_findings=iso,kernel_certificate_findings=certs,policy='14zza whole source line; existing 14s and 14v classes; redacted metadata only locates the secret inside the approved token',ignore_changes=False,workflow_changes=False,raw_consoles_committed=False)

def classify_logs(run,scan,folder,jobs,head):
 folder=pathlib.Path(folder).resolve();sources=Sources();rows=read_json(scan)
 assert jobs['total_count']==len(jobs['jobs']),'STOP: incomplete log job metadata'
 job,=[j for j in jobs['jobs'] if j['name']=='Pinned live ISO inspection and two-disk rehearsal']
 assert job['run_id']==int(run) and job['head_sha']==head,'STOP: log job identity differs'
 assert isinstance(rows,list),'STOP: malformed full-log scan'
 if not rows:return dict(status='passed',run=int(run),head=head,findings=0,cosign_checksum_findings=[],ignore_changes=False)
 name='Run sigstore/cosign-installer@'+pinned.COSIGN_COMMIT
 steps=[s for s in job['steps'] if s['name']==name]
 assert len(steps)==1 and steps[0]['status']=='completed','STOP: pinned cosign step was not completed'
 step=folder/job['name']/(str(steps[0]['number'])+'_'+name.replace('/','_')+'.txt')
 combineds=[p for p in folder.iterdir() if p.is_file() and re.fullmatch('[0-9]+_'+re.escape(job['name'])+r'\.txt',p.name)]
 assert step.is_file() and len(combineds)==1,'STOP: missing or ambiguous full cosign log context'
 combined=combineds[0];a,b=pinned.log_lines(step,True),pinned.log_lines(combined,True)
 assert a and a[0]=='##[group]'+name,'STOP: step log is not from the pinned action'
 starts=[i for i,x in enumerate(b) if x==a[0] and b[i:i+len(a)]==a]
 assert len(starts)==1,'STOP: combined log has missing or ambiguous pinned-action block'
 values=pinned.cosign_source();approved=[];seen=set()
 for row in rows:
  assert row['RuleID']=='generic-api-key','STOP: unapproved full-log finding rule'
  path=(ROOT/row['File'].replace('\\','/')).resolve();assert path.is_relative_to(folder),'STOP: source outside logs'
  line=sources.line(path,row);number=row['StartLine']
  if path==combined.resolve():assert starts[0]<=number-1<starts[0]+len(a),'STOP: checksum outside pinned action section'
  else:assert path==step.resolve(),'STOP: checksum in unrelated step log'
  key=(path,number,row.get('StartColumn'),row.get('EndColumn'));assert key not in seen,'STOP: duplicate full-log finding';seen.add(key)
  item=dict(**pinned.cosign_line(line,values),path=path.relative_to(folder).as_posix(),line=number,rule=row['RuleID'],classification='14zz public checksum in exact pinned-action whole-line block')
  match=pinned.COSIGN_LINE.fullmatch(line)
  item['cross_check']=sources.cross(path,row,line,match.span('sha256'))
  approved.append(item)
 return dict(status='passed',run=int(run),head=head,findings=len(rows),cosign_checksum_findings=approved,source=dict(sha256=pinned.COSIGN_SHA256,url='https://raw.githubusercontent.com/sigstore/cosign-installer/'+pinned.COSIGN_COMMIT+'/action.yml'),combined_log=combined.name,combined_block_first_line=starts[0]+1,combined_block_lines=len(a),policy='14zza whole source line plus unique pinned-action block; redacted metadata cross-check only',ignore_changes=False,workflow_changes=False)

if __name__=='__main__':
 if sys.argv[1]=='--logs':
  run,scan,folder,jobs,target=sys.argv[2:];head=read_json(ROOT/'.work/14'/f'run-{run}'/'receipt.json')['head'];value=classify_logs(run,scan,folder,read_json(jobs),head)
 else:
  run,scan,target=sys.argv[1:];value=classify(run,scan)
 pathlib.Path(target).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
 print('PASS whole-source classification',value['findings'],'findings; all redacted secret positions inside approved tokens')
