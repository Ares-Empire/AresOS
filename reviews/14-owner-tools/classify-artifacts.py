"""14s/14v/14zz evidence review only; never changes scanner rules or ignores."""
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
KERNEL = re.compile(r"\[[ \t]*[0-9]+\.[0-9]+\] Loaded X\.509 cert '(?P<label>[^'\r\n]+): (?P<fingerprint>[0-9a-fA-F]{40})'")
COSIGN_COMMIT = '398d4b0eeef1380460a10c8013a76f728fb906ac'
COSIGN_SHA256 = 'bbd7f51b170057ad223c140c8fb4dd781010d7265416bb94651c64c1bee30f37'
LOG_TIME = r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,9})?Z '
COSIGN_LINE = re.compile('(?:'+LOG_TIME+r')?(?P<color>\x1b\[36;1m)?[ \t]*'
    r"RELEASE_COSIGN_PUB_KEY_SHA='(?P<sha256>[0-9a-f]{64})'(?P<reset>\x1b\[0m)?")


def cosign_source():
    folder = ROOT/'os/manifest/ci/14/14zz-cosign'
    source = json.loads((folder/'source.json').read_text())
    assert source['commit'] == COSIGN_COMMIT and source['sha256'] == COSIGN_SHA256, 'STOP: cosign source pin changed'
    raw = (folder/'action.yml.template').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == source['template_sha256'], 'STOP: cosign source template changed'
    for index, value in enumerate(source['checksums']):
        assert re.fullmatch('[0-9a-f]{64}',value), 'STOP: invalid public checksum pin'
        raw = raw.replace(('@SHA'+str(index)+'@').encode(), value.encode())
    assert hashlib.sha256(raw).hexdigest() == COSIGN_SHA256, 'STOP: reconstructed cosign source differs from fetched commit'
    values = re.findall(rb"(?m)^\s+RELEASE_COSIGN_PUB_KEY_SHA='([0-9a-f]{64})'$", raw)
    assert len(values) == len(set(values)) == 2, 'STOP: pinned source checksum assignments differ'
    return {v.decode() for v in values}


def cosign_line(line, values):
    match = COSIGN_LINE.fullmatch(line)
    assert match and bool(match['color']) == bool(match['reset']), 'STOP: finding is not an exact cosign checksum assignment'
    assert match['sha256'] in values, 'STOP: checksum does not appear verbatim in the pinned action'
    return dict(sha256=match['sha256'], line_sha256=hashlib.sha256(line.encode()).hexdigest())


def log_lines(path, normalized=False):
    # Only UTF-8 BOM and the actual LF/CRLF log framing are removed. In block
    # comparisons, timestamps and SGR renderings differ between GitHub's copies.
    lines = path.read_bytes().decode('utf-8-sig').split('\n')
    if lines[-1] == '': lines.pop()
    lines = [s.removesuffix('\r') for s in lines]
    if normalized:
        lines = [re.sub(r'\x1b\[[0-9;]*m','',re.sub('^'+LOG_TIME,'',s)) for s in lines]
    return lines


def classify_logs(run, scan, folder, jobs, head):
    folder = pathlib.Path(folder).resolve()
    assert jobs['total_count'] == len(jobs['jobs']), 'STOP: incomplete log job metadata'
    job, = [j for j in jobs['jobs'] if j['name']=='Pinned live ISO inspection and two-disk rehearsal']
    assert job['run_id'] == int(run) and job['head_sha'] == head, 'STOP: log job identity differs'
    step_name = 'Run sigstore/cosign-installer@'+COSIGN_COMMIT
    steps = [s for s in job['steps'] if s['name']==step_name]
    rows = json.loads(pathlib.Path(scan).read_text())
    assert isinstance(rows,list)
    if not rows:
        return dict(status='passed',run=int(run),head=head,findings=0,cosign_checksum_findings=[],ignore_changes=False)
    assert len(steps)==1 and steps[0]['status']=='completed', 'STOP: pinned cosign step was not completed'
    step = folder/job['name']/(str(steps[0]['number'])+'_'+step_name.replace('/','_')+'.txt')
    combined = folder/('0_'+job['name']+'.txt')
    assert step.is_file() and combined.is_file(), 'STOP: missing full cosign log context'
    a, b = log_lines(step,True), log_lines(combined,True)
    assert a and a[0]=='##[group]'+step_name, 'STOP: step log is not from the pinned action'
    starts = [i for i,s in enumerate(b) if s==a[0] and b[i:i+len(a)]==a]
    assert len(starts)==1, 'STOP: combined log has missing or ambiguous pinned-action block'
    values, approved = cosign_source(), []
    for row in rows:
        assert row['RuleID']=='generic-api-key', 'STOP: unapproved full-log finding rule'
        path = (ROOT/row['File'].replace('\\','/')).resolve()
        assert path.is_relative_to(folder), 'STOP: log finding outside this archive'
        number = row['StartLine']
        assert type(number) is int and number==row['EndLine'], 'STOP: multiline log finding'
        lines = log_lines(path)
        assert 1 <= number <= len(lines), 'STOP: log finding line is out of bounds'
        if path==combined.resolve():
            assert starts[0] <= number-1 < starts[0]+len(a), 'STOP: checksum outside the pinned action section'
        else:
            assert path==step.resolve(), 'STOP: checksum in an unrelated step log'
        proof = cosign_line(lines[number-1],values)
        approved.append(dict(**proof,path=path.relative_to(folder).as_posix(),line=number,
            rule=row['RuleID'],classification='14zz public RELEASE_COSIGN_PUB_KEY_SHA from pinned sigstore action'))
    return dict(status='passed',run=int(run),head=head,findings=len(rows),cosign_checksum_findings=approved,
        source=dict(sha256=COSIGN_SHA256,url='https://raw.githubusercontent.com/sigstore/cosign-installer/'+COSIGN_COMMIT+'/action.yml'),
        combined_block_first_line=starts[0]+1,combined_block_lines=len(a),ignore_changes=False,workflow_changes=False)


def kernel_line(line):
    match = KERNEL.fullmatch(line)
    assert match is not None, 'STOP: finding is not a complete kernel X.509 certificate boot message'
    return dict(sha256=hashlib.sha256(line.encode()).hexdigest(),
        certificate_label=match['label'], fingerprint_hex_length=40)


def classify(run, scan):
    base = ROOT/'.work/14'/('run-'+str(run))
    rows = json.loads(pathlib.Path(scan).read_text())
    assert isinstance(rows, list)
    listing, captured = base/'evidence/installer/squashfs-files.txt', base/'evidence/two-disk'
    certificates, iso = [], []
    for row in rows:
        assert row['RuleID'] == 'generic-api-key', 'STOP: unclassified artifact finding rule'
        path = (ROOT/row['File'].replace('\\', '/')).resolve()
        assert path.is_relative_to(base.resolve()), 'STOP: finding path outside current run'
        if path == listing.resolve():
            iso.append(row)
            continue
        assert path.parent == captured.resolve() and re.fullmatch(r'[a-z0-9-]+-boot-console\.txt', path.name), 'STOP: finding outside captured boot console'
        number = row['StartLine']
        assert type(number) is int and number == row['EndLine'], 'STOP: multiline or malformed finding'
        # Gitleaks counts LF-delimited source lines. Do not treat arbitrary
        # control characters as line breaks or strip them into a valid message.
        lines = path.read_bytes().split(b'\n')
        assert 1 <= number <= len(lines)
        line = lines[number-1].removesuffix(b'\r').decode('utf-8')
        proof = kernel_line(line)
        assert re.fullmatch(r"key: REDACTED'", row['Match']), 'STOP: unexpected redacted finding match'
        certificates.append(dict(**proof, path=path.relative_to(base).as_posix(), line=number,
            rule=row['RuleID'], classification='14v public kernel X.509 certificate fingerprint'))
    assert len(iso) == 507, 'STOP: public ISO listing count differs from reviewed 507'
    return dict(status='passed', run=int(run), head=json.loads((base/'receipt.json').read_text())['head'],
        scan=dict(sha256=hashlib.sha256(pathlib.Path(scan).read_bytes()).hexdigest(),
            path=pathlib.Path(scan).resolve().relative_to(ROOT).as_posix()),
        findings=len(rows), iso_listing_findings=len(iso), kernel_certificate_findings=certificates,
        policy='briefs/14s-loop-node-race.md and briefs/14v-efibootmgr-format.md; exact whole source line in captured boot console only',
        ignore_changes=False, workflow_changes=False, raw_consoles_committed=False)


if __name__ == '__main__':
    if sys.argv[1]=='--logs':
        run, scan, folder, jobs, target = sys.argv[2:]
        head=json.loads((ROOT/'.work/14'/('run-'+run)/'receipt.json').read_text())['head']
        result=classify_logs(run,scan,folder,json.loads(pathlib.Path(jobs).read_text()),head)
        target=pathlib.Path(target)
    else:
        result = classify(sys.argv[1], sys.argv[2])
        target = pathlib.Path(sys.argv[3])
    target.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print('PASS', result['findings'], 'classified findings; no ignore/rule changes')
