import pathlib,json,re,hashlib
r=pathlib.Path.cwd();b=r/'.work/14/run-40844950597';p=b/'evidence/two-disk/owner-logind-diagnostics-owner-diagnostics.json';v=json.loads(p.read_text());rows=[]
for index,t in enumerate(v['trace']):
    if (t.get('command') or [None])[0]!='journalctl':continue
    for number,line in enumerate(t.get('stdout','').splitlines(),1):
        match=re.search(r"Loaded X\.509 cert '([^'\r\n]+): ([0-9a-fA-F]{40})'",line)
        if match:
            rows.append(dict(sha256=hashlib.sha256(line.encode()).hexdigest(),path='evidence/two-disk/owner-logind-diagnostics-owner-diagnostics.json',source_json_line=30,trace_index=index,journal_line=number,command=t['command'],certificate_label=match[1],fingerprint_length=40,redacted_message="Loaded X.509 cert '"+match[1]+": REDACTED'",classification='unclassified candidate only; source is escaped JSON journal stdout, not approved captured boot-console line'))
assert len(rows)==2
(b/'14zq-privacy-candidates.json').write_text(json.dumps(dict(status='STOP remains; no exception inferred',candidates=rows,values_or_source_lines_saved=False),indent=2)+'\n',newline='\n')
print('CANDIDATES',len(rows),'shaped like X.509 messages in decoded journal text; original4 findings remain unclassified')
for row in rows:print(row['path'],row['source_json_line'],row['certificate_label'],row['redacted_message'])
