import pathlib,json,re,hashlib
r=pathlib.Path.cwd();b=r/'.work/14/run-40866713472';e=b/'evidence/two-disk';d=r/'os/manifest/ci/14/14zr-qualification-stop'
def read(p):return json.loads(p.read_text())
def ref(p):return dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),path=p.relative_to(b).as_posix())
rows=[]
for p in sorted(e.glob('*-read-wait-*.json')):
 if not re.search(r'-read-wait-[0-9]+\.json$',p.name):continue
 v=read(p);assert v['ready'] and v['prompt_at_cursor'] and v['reader_echo_enabled'] is False
 assert all(x['argv_redacted'] and x['argv']==['[redacted]'] for x in v['observation']['foreground_chain'])
 left=p.with_name(p.stem+'-left.json');row=dict(**ref(p),ready=True,echo_off=True,value_recorded=False)
 if left.exists():
  value=read(left)
  if value.get('rejected'):assert not value['ready'];row['transition']='expected plain-US rejection'
  else:
   if not value['ready']:
    assert value['reader_left'] and value['shell_idle'] and not value['prompt_at_cursor']
    left=p.with_name(p.stem+'-left-after-resync.json');value=read(left)
   assert value['ready'] and value['reader_left'] and value['completion_uses_echo'] is False
   row['transition']='completed';row['completion_uses_echo']=False
  row['left']=ref(left)
 else:
  assert p.name=='layout-reverted-login-password-prompt-read-wait-112.json'
  row['transition']='STOP before Enter; no completion'
 rows.append(row)
assert len(rows)==10 and sum(x['transition']=='completed' for x in rows)==8 and sum(x['transition']=='expected plain-US rejection' for x in rows)==1
(d/'hidden-transitions.json').write_text(json.dumps(dict(status='read-only transition review',run=40866713472,rows=rows,completed=8,expected_rejection=1,pre_enter_stop=1),indent=2)+'\n',newline='\n')
print('PASS actual10 hidden windows:8 completed,1 expected rejection,1 pre-Enter STOP')
