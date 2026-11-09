"""Qualification planning and append-only publishing. No browser is started here."""
import argparse
from datetime import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.chrome.qualification import REPOSITORY, WORKFLOW, append_only, validate_record, verify, version
from aresos_control.chrome.policy import CORE_GROUPS, HOSTS
from build import build_hash

RECORD = 'control/chrome/qualification.json'
DATA_BRANCH = 'chrome-qualification'
PACKAGES = 'https://dl.google.com/linux/chrome/deb/dists/stable/main/binary-amd64/Packages.gz'


def packages(data):
    found = {}
    for paragraph in data.split('\n\n'):
        fields = dict(line.split(': ', 1) for line in paragraph.splitlines() if ': ' in line and not line.startswith(' '))
        for channel in ['stable', 'beta']:
            if fields.get('Package') == 'google-chrome-' + channel:
                if channel in found:
                    raise ValueError('Duplicate Chrome channel metadata')
                match = re.fullmatch(r'(\d+\.\d+\.\d+\.\d+)-\d+', fields.get('Version', ''))
                if not match:
                    raise ValueError('Chrome package must name a complete version')
                filename=fields.get('Filename','');checksum=fields.get('SHA256','')
                expected='pool/main/g/google-chrome-'+channel+'/google-chrome-'+channel+'_'+fields['Version']+'_amd64.deb'
                if filename!=expected or not re.fullmatch('[0-9a-f]{64}',checksum):
                    raise ValueError('Chrome metadata must include the exact package filename and SHA256')
                found[channel] = {'version':match[1], 'package_version':fields['Version'],
                    'package_url':'https://dl.google.com/linux/chrome/deb/'+filename,'package_sha256':checksum}
    if set(found) != {'stable','beta'}:
        raise ValueError('Stable and beta must both be present in Google package metadata')
    return found


def plan(registry, versions, record, head, build):
    if type(registry) is not dict or set(registry) != {'format', 'builds'} or type(registry['format']) is not int or registry['format'] != 1 or type(registry['builds']) is not list:
        raise ValueError('Invalid shipped build registry')
    identities = set()
    dated = []
    for item in registry['builds']:
        if type(item) is not dict or set(item) != {'commit', 'build', 'shipped_at'}:
            raise ValueError('Invalid shipped build entry')
        validate_identity(item)
        date = datetime.fromisoformat(item['shipped_at'].replace('Z', '+00:00'))
        if date.tzinfo is None or item['build'] in identities:
            raise ValueError('Ship dates need a timezone and build identities must be unique')
        identities.add(item['build'])
        dated.append((date, item))
    shipped = [item for _, item in sorted(dated, key=lambda row: row[0], reverse=True)[:3]]
    builds = [{'commit':head,'build':build}, *shipped]
    validate_record(record)
    matrix, seen = [], set()
    for item in builds:
        validate_identity(item)
        for channel, package in versions.items():
            key = item['build'],package['version'],channel
            if key in seen or any((entry['build'],entry['version'],entry['channel']) == key for entry in validate_record(record)['entries']):
                continue
            seen.add(key)
            for repeat in [1,2]:
                matrix.append({**item,**package,'channel':channel,'repeat':repeat})
    return {'include':matrix}


def validate_identity(item):
    if any(type(item.get(key)) is not str or not re.fullmatch(pattern, item[key])
           for key, pattern in [('commit', '[0-9a-f]{40}'), ('build', '[0-9a-f]{64}')]):
        raise ValueError('Registry requires a full commit and runtime build hash')


def runtime_identity(root):
    # Shipped builds retain the hasher they shipped with. Using today's input
    # inventory for an archived build would silently relabel that installed code.
    measured = subprocess.run([sys.executable, str(Path(root)/'control/chrome/build.py')],
                              check=True, capture_output=True, text=True, timeout=30).stdout.strip()
    if not re.fullmatch('[0-9a-f]{64}', measured):
        raise ValueError('Invalid measured runtime identity')
    return measured


def completed(root, identity, outcome):
    marker = Path(root)/'qualification-complete.json'
    if not marker.exists() or outcome not in {'success', 'failure'}:
        return False
    completion = json.loads(marker.read_text())
    if completion.get('format') != 1 or completion.get('identity') != identity or completion.get('outcome') != outcome:
        return False
    return completion.get('digests') == {name: hashlib.sha256((Path(root)/name).read_bytes()).hexdigest()
                                         for name in ['qualification-result.json', 'matrices.json']}


def git(repo, *arguments, check=True):
    return subprocess.run(['git','-C',str(repo),*arguments],check=check,capture_output=True,text=True).stdout.strip()


def prepare(repo, entries, baseline, verifier=verify):
    # Fetching/verification precede any write to the publication branch.
    path = Path(repo)/RECORD
    current = json.loads(path.read_text())
    verifier(path)
    append_only(baseline,current)
    indexed={(item['build'],item['version'],item['channel']):item for item in current['entries']}
    added=[]
    for item in entries:
        validate_record({'format': 1, 'entries': [item]})
        existing=indexed.get((item['build'],item['version'],item['channel']))
        if existing:
            if existing['core']!=item['core'] or existing['adapters']!=item['adapters']:
                raise ValueError('Conflicting repeat for an immutable qualification pair; publish nothing')
            continue
        added.append(item)
        indexed[item['build'], item['version'], item['channel']] = item
    candidate = {'format':1,'entries':[*current['entries'],*added]}
    append_only(current,candidate)
    return candidate


def aggregate(root, run, expected=None):
    grouped = {}
    for path in Path(root).rglob('pair.json'):
        pair = json.loads(path.read_text())
        validate_record({'format': 1, 'entries': [{key: pair[key] for key in ['build', 'version', 'channel', 'core', 'adapters']} | {'run': str(run)}]})
        if type(pair.get('repeat')) is not int or pair['repeat'] not in {1, 2}:
            raise ValueError('Invalid repeat identity')
        key = pair['build'],pair['version'],pair['channel']
        grouped.setdefault(key,[]).append(pair)
    if expected is not None:
        planned = {}
        for item in expected['include']:
            key = item['build'], item['version'], item['channel']
            planned.setdefault(key, set()).add(item['repeat'])
        if any(repeats != {1, 2} for repeats in planned.values()) or set(grouped) - set(planned):
            raise ValueError('Unexpected or incomplete qualification plan')
        for key in planned:
            grouped.setdefault(key, [])
    entries=[]
    for (build,chrome_version,channel),pairs in sorted(grouped.items(), key=lambda row:(row[0][0], version(row[0][1]), row[0][2])):
        complete = len(pairs)==2 and {item['repeat'] for item in pairs}=={1,2}
        entries.append({'build':build,'version':chrome_version,'channel':channel,'run':str(run),
            'core':{name:complete and all(item.get('core',{}).get(name) is True for item in pairs) for name in CORE_GROUPS},
            'adapters':{name:complete and all(item.get('adapters',{}).get(name) is True for item in pairs) for name in HOSTS}})
    validate_record({'format':1,'entries':entries})
    if not entries: raise ValueError('No pair results; publish nothing')
    return entries


def notify(candidate, published, runner=subprocess.run):
    """Only the main-only CLI invokes this; tests inject a recording subprocess runner."""
    def gh(arguments):
        return runner(['gh',*arguments],check=True,capture_output=True,text=True)
    if not published:
        gh(['issue','create','--repo',REPOSITORY,'--title','Chrome qualification publication refused',
            '--body','Record or attestation verification failed, or a workflow job was interrupted. Nothing new is trusted. Inspect this qualification run.'])
        return
    record=validate_record(json.loads(Path(candidate).read_text()))
    failures=[]
    for entry in record['entries']:
        names=[name for name,passed in {**entry['core'],**entry['adapters']}.items() if not passed]
        if names:failures.append(entry['build']+' '+entry['channel']+' '+entry['version']+': '+', '.join(names))
    if failures:
        gh(['issue','create','--repo',REPOSITORY,'--title','Chrome qualification has failing groups',
            '--body','Failed groups stay disabled for their installed build and version.\n\n'+'\n'.join(failures)])
    existing=gh(['pr','list','--repo',REPOSITORY,'--head',DATA_BRANCH,'--base','main','--json','number'])
    if not json.loads(existing.stdout):
        gh(['pr','create','--repo',REPOSITORY,'--head',DATA_BRANCH,'--base','main',
            '--title','Update shipped Chrome qualification record',
            '--body','Bring the shipped baseline up to date with the verified append-only data branch. Runtime delivery already uses the attested record. Review before merging.'])


def publish(root, candidate, baseline, *, remote=None, verifier=verify):
    """Only the main-only CLI uses the real remote; tests supply a local bare repo."""
    verifier(candidate)
    candidate_record = append_only(baseline, json.loads(candidate.read_text()))
    with tempfile.TemporaryDirectory(dir=root/'.work') as temporary:
        repository = Path(temporary)
        git(repository, 'init')
        git(repository, 'remote', 'add', 'origin', remote or 'https://github.com/'+REPOSITORY+'.git')
        credentials = ('-c', 'credential.helper=!gh auth git-credential') if remote is None else ()
        exists = git(repository, *credentials, 'ls-remote', '--heads', 'origin', 'refs/heads/'+DATA_BRANCH)
        git(repository, *credentials, 'fetch', 'origin', DATA_BRANCH if exists else 'main')
        git(repository, 'checkout', '-b', DATA_BRANCH, 'FETCH_HEAD')
        if exists:
            verifier(repository/RECORD)
        held = json.loads((repository/RECORD).read_text())
        append_only(baseline, held)
        append_only(held, candidate_record)
        (repository/RECORD).write_bytes(candidate.read_bytes())
        git(repository, 'add', RECORD)
        if subprocess.run(['git', '-C', str(repository), 'diff', '--cached', '--quiet']).returncode == 0:
            print('Verified record already published; no change.')
            return
        git(repository, '-c', 'user.name=Chrome qualification', '-c', 'user.email=qualification@users.noreply.github.com',
            'commit', '-m', 'Append attested Chrome qualification results')
        git(repository, *credentials, 'push', 'origin', 'HEAD:refs/heads/'+DATA_BRANCH)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['plan','pair','prepare','publish','notify'])
    parser.add_argument('--root',default='.')
    parser.add_argument('--artifacts')
    parser.add_argument('--plan')
    parser.add_argument('--runtime-root')
    parser.add_argument('--candidate',default='.work/qualification-candidate.json')
    args=parser.parse_args();root=Path(args.root)
    if args.command=='plan':
        with urllib.request.urlopen(PACKAGES,timeout=30) as response:data=gzip.decompress(response.read(8*1024*1024)).decode()
        held=json.loads((root/RECORD).read_text())
        exists=git(root,'ls-remote','--heads','origin','refs/heads/'+DATA_BRANCH)
        if exists:
            git(root,'fetch','origin',DATA_BRANCH)
            content=git(root,'show','FETCH_HEAD:'+RECORD)
            with tempfile.NamedTemporaryFile(dir=root,suffix='.json',mode='w') as temporary:
                temporary.write(content+'\n');temporary.flush();verify(temporary.name)
                held=append_only(held,json.loads(content))
        matrix=plan(json.loads((root/'control/chrome/builds.json').read_text()),packages(data),held,git(root,'rev-parse','HEAD'),build_hash(root.resolve()))
        print(json.dumps(matrix));return
    if args.command=='pair':
        identity=json.loads(os.environ['QUALIFICATION_PAIR'])
        # A result file is emitted only by the complete browser suite. Missing/crashed runs fail every group.
        result_path=Path(args.artifacts)/'qualification-result.json'
        result=json.loads(result_path.read_text()) if result_path.exists() else {}
        actual = (Path(args.artifacts)/'chrome-version.txt')
        measured_version = actual.read_text().strip().split()[-1] if actual.exists() else None
        measured_build = runtime_identity(Path(args.runtime_root).resolve()) if args.runtime_root else None
        valid = (measured_version == identity['version'] and measured_build == identity['build']
                 and completed(args.artifacts, identity, os.environ.get('QUALIFICATION_OUTCOME'))
                 and result.get('groups', {}).get('12') is True)
        identity.update(core={key: valid and result.get('core', {}).get(key) is True for key in CORE_GROUPS},
                        adapters={key: valid and result.get('adapters', {}).get(key) is True for key in HOSTS})
        Path(args.artifacts).mkdir(parents=True,exist_ok=True)
        (Path(args.artifacts)/'pair.json').write_text(json.dumps(identity));return
    # A branch/test invocation cannot publish, open issues or create a pull request.
    if os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY')!=REPOSITORY:
        raise SystemExit('Qualification publication is restricted to this repository on main')
    candidate=Path(args.candidate)
    if args.command=='notify':
        notify(candidate,os.environ.get('PUBLISH_STATE')=='success');return
    if args.command=='prepare':
        if not args.plan:
            raise ValueError('Publication requires the complete expected qualification plan')
        entries=aggregate(args.artifacts,os.environ['GITHUB_RUN_ID'],json.loads(Path(args.plan).read_text()))
        baseline=json.loads(git(root,'show','origin/main:'+RECORD))
        exists=git(root,'ls-remote','--heads','origin','refs/heads/'+DATA_BRANCH)
        if not exists:
            candidate.parent.mkdir(parents=True,exist_ok=True)
            candidate.write_text(json.dumps(append_only(baseline,{'format':1,'entries':baseline['entries']+entries}),separators=(',',':'))+'\n');return
        git(root,'fetch','origin',DATA_BRANCH)
        current=git(root,'show','FETCH_HEAD:'+RECORD)
        with tempfile.TemporaryDirectory(dir=root/'.work') as temporary:
            publication=Path(temporary);(publication/RECORD).parent.mkdir(parents=True)
            (publication/RECORD).write_text(current+'\n')
            result=prepare(publication,entries,baseline)
        candidate.parent.mkdir(parents=True,exist_ok=True);candidate.write_text(json.dumps(result,separators=(',',':'))+'\n');return
    baseline=json.loads(git(root,'show','origin/main:'+RECORD))
    publish(root,candidate,baseline)


if __name__=='__main__':main()
