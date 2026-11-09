"""Qualification planning and append-only publishing. No browser is started here."""
import argparse
import gzip
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.chrome.qualification import REPOSITORY, WORKFLOW, append_only, validate_record, verify
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
                match = re.fullmatch(r'(\d+\.\d+\.\d+\.\d+)-\d+', fields['Version'])
                if not match:
                    raise ValueError('Chrome package must name a complete version')
                found[channel] = {'version':match[1], 'package_version':fields['Version']}
    if set(found) != {'stable','beta'}:
        raise ValueError('Stable and beta must both be present in Google package metadata')
    return found


def plan(registry, versions, record, head, build):
    if registry.get('format') != 1 or type(registry.get('builds')) is not list:
        raise ValueError('Invalid shipped build registry')
    shipped = sorted(registry['builds'], key=lambda item:item['shipped_at'], reverse=True)[:3]
    builds = [{'commit':head,'build':build}, *shipped]
    matrix, seen = [], set()
    for item in builds:
        if not re.fullmatch('[0-9a-f]{40}',item['commit']) or not re.fullmatch('[0-9a-f]{64}',item['build']):
            raise ValueError('Registry requires a full commit and runtime build hash')
        for channel, package in versions.items():
            key = item['build'],package['version'],channel
            if key in seen or any((entry['build'],entry['version'],entry['channel']) == key for entry in validate_record(record)['entries']):
                continue
            seen.add(key)
            for repeat in [1,2]:
                matrix.append({**item,**package,'channel':channel,'repeat':repeat})
    return {'include':matrix}


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
        existing=indexed.get((item['build'],item['version'],item['channel']))
        if existing:
            if existing['core']!=item['core'] or existing['adapters']!=item['adapters']:
                raise ValueError('Conflicting repeat for an immutable qualification pair; publish nothing')
            continue
        added.append(item)
    candidate = {'format':1,'entries':[*current['entries'],*added]}
    append_only(current,candidate)
    return candidate


def aggregate(root, run):
    grouped = {}
    for path in Path(root).rglob('pair.json'):
        pair = json.loads(path.read_text())
        key = pair['build'],pair['version'],pair['channel']
        grouped.setdefault(key,[]).append(pair)
    entries=[]
    for (build,version,channel),pairs in sorted(grouped.items()):
        complete = len(pairs)==2 and {item['repeat'] for item in pairs}=={1,2}
        entries.append({'build':build,'version':version,'channel':channel,'run':str(run),
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


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['plan','pair','prepare','publish','notify'])
    parser.add_argument('--root',default='.')
    parser.add_argument('--artifacts')
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
        identity.update(core=result.get('core',{}),adapters=result.get('adapters',{}))
        Path(args.artifacts).mkdir(parents=True,exist_ok=True)
        (Path(args.artifacts)/'pair.json').write_text(json.dumps(identity));return
    # A branch/test invocation cannot publish, open issues or create a pull request.
    if os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY')!=REPOSITORY:
        raise SystemExit('Qualification publication is restricted to this repository on main')
    candidate=Path(args.candidate)
    if args.command=='notify':
        notify(candidate,os.environ.get('PUBLISH_STATE')=='success');return
    if args.command=='prepare':
        entries=aggregate(args.artifacts,os.environ['GITHUB_RUN_ID'])
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
    verify(candidate)
    # This local-only worktree is on the Linux publisher runner, never an owner's checkout.
    with tempfile.TemporaryDirectory(dir=root/'.work') as temporary:
        repository=Path(temporary)
        git(repository,'init');git(repository,'remote','add','origin','https://github.com/'+REPOSITORY+'.git')
        exists=git(repository,'-c','credential.helper=!gh auth git-credential','ls-remote','--heads','origin','refs/heads/'+DATA_BRANCH)
        git(repository,'-c','credential.helper=!gh auth git-credential','fetch','origin',DATA_BRANCH if exists else 'main')
        git(repository,'checkout','-b',DATA_BRANCH,'FETCH_HEAD')
        if exists:verify(repository/RECORD)
        held=json.loads((repository/RECORD).read_text());append_only(held,json.loads(candidate.read_text()))
        (repository/RECORD).write_bytes(candidate.read_bytes())
        git(repository,'add',RECORD)
        if subprocess.run(['git','-C',str(repository),'diff','--cached','--quiet']).returncode==0:
            print('Verified record already published; no change.');return
        git(repository,'-c','user.name=Chrome qualification','-c','user.email=qualification@users.noreply.github.com','commit','-m','Append attested Chrome qualification results')
        git(repository,'-c','credential.helper=!gh auth git-credential','push','origin','HEAD:refs/heads/'+DATA_BRANCH)


if __name__=='__main__':main()
