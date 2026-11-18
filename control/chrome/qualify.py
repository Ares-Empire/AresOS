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
from aresos_control.chrome.qualification import DELIVERY_LIMIT, REPOSITORY, WORKFLOW, append_only, validate_record, verify, version
from aresos_control.common import Refused
from aresos_control.chrome.policy import CORE_GROUPS, HOSTS
from build import build_hash

RECORD = 'control/chrome/qualification.json'
DATA_BRANCH = 'chrome-qualification'
# The account GITHUB_TOKEN writes issues and comments as.
WORKFLOW_BOT = 'github-actions[bot]'
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


def plan(registry, versions, record, head, build, *, requalify_head=False):
    """The (build, version, channel) pairs to qualify, each twice.

    A pair the held record covers is skipped. requalify_head (pull requests and
    branch runs, never main) qualifies the head build again even when the held
    record covers it: build.py hashes only the installed runtime, so a change to
    the test driver, ci/, qualify.py or the workflows keeps main's build hash and
    would otherwise first run in the runtime/driver layout on main (main fix F1).
    prepare then skips an identical repeat and refuses a conflicting one.
    """
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
    for index, item in enumerate(builds):
        validate_identity(item)
        for channel, package in versions.items():
            key = item['build'],package['version'],channel
            held = any((entry['build'],entry['version'],entry['channel']) == key for entry in validate_record(record)['entries'])
            if key in seen or (held and not (requalify_head and index == 0)):
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


NOT_LISTED = 'No attestation is listed for the held qualification record.'


def bundle_from_api(path, runner=subprocess.run):
    """Fetch the held record's attestation list with the job's gh login.

    The installed service fetches the same list anonymously; CI runs share
    GitHub's anonymous quota with other tenants, so the workflow uses its own
    token for the transport. The response is never evidence: gh attestation
    verify checks the signatures, the workflow identity and the source ref.
    The API answers 404 for a digest it lists no attestation for (gh: "Not
    Found (HTTP 404)"), the same condition as an empty list; any other gh
    failure propagates.
    """
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        result = runner(['gh', 'api', f'repos/{REPOSITORY}/attestations/sha256:{digest}?per_page=100'],
                        check=True, capture_output=True, text=True, timeout=60)
    except subprocess.CalledProcessError as error:
        if '(HTTP 404)' in (error.stderr or ''):
            raise Refused('qualification_invalid', NOT_LISTED) from error
        raise
    attestations = json.loads(result.stdout).get('attestations')
    if not isinstance(attestations, list) or not attestations:
        raise Refused('qualification_invalid', NOT_LISTED)
    serialized = ''.join(json.dumps(attestation['bundle'], ensure_ascii=False, separators=(',', ':')) + '\n'
                         for attestation in attestations).encode('utf-8')
    if len(serialized) > DELIVERY_LIMIT:
        raise Refused('qualification_invalid', 'Serialized qualification attestations exceed the delivery bound.')
    bundle = path.with_name(path.name + '.bundles.jsonl')
    bundle.write_bytes(serialized)
    return bundle


def verify_held(path):
    """Verify a held data-branch record from a token-fetched bundle list; main policy."""
    bundle = bundle_from_api(path)
    try:
        verify(path, bundle=bundle)
    finally:
        bundle.unlink()


def held_bundles(root, output, runner=subprocess.run):
    """Pull-request mode, read-only: the held record's bundle list, fetched with the job's token.

    The record is the data branch that prepare extended (its remote-tracking
    ref), which the pull-request publish step seeds into its local bare remote.
    That step holds no token and verifies the record from this file under the
    unchanged main policy (held_from_file). Without a data branch nothing is
    written: the publish takes the first-record path.
    """
    tracking = 'refs/remotes/origin/'+DATA_BRANCH
    if not git(root, 'rev-parse', '--verify', '--quiet', tracking, check=False):
        print('No data branch on origin: the pull-request publish takes the first-record path.')
        return None
    content = subprocess.run(['git', '-C', str(root), 'show', tracking+':'+RECORD], check=True, capture_output=True).stdout
    (root/'.work').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root/'.work') as temporary:
        held = Path(temporary)/'qualification.json'
        held.write_bytes(content)
        bundle = bundle_from_api(held, runner)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(bundle.read_bytes())
    print(f'Held record {hashlib.sha256(content).hexdigest()}: bundle list written to {output}')
    return output


def held_from_file(bundles):
    """The held verifier of the token-free pull-request publish: main policy, bundles from held_bundles."""
    def check(path):
        if not bundles.is_file():
            raise Refused('qualification_invalid', 'The data branch exists but no bundle list was fetched for its record.')
        verify(path, bundle=bundles)
    return check


def serialized(record, on_main):
    """Main writes the compact bytes the data branch holds, exactly as before.

    Off main the candidate is indented: same content, never the same bytes as a
    record main publishes, so a pull request's attestation never joins the
    listing the laptop and main read for the real record (one page of 100, at
    most DELIVERY_LIMIT bytes) even when its repeat is identical (main fix F1).
    """
    if on_main:
        return json.dumps(record, separators=(',', ':'))+'\n'
    return json.dumps(record, indent=1)+'\n'


def compared(held, repeat):
    """The groups a repeat fails that the held entry passes (worse), and those it passes that the held entry fails (better)."""
    groups = lambda item: {kind+'.'+name: value for kind in ['core', 'adapters'] for name, value in item[kind].items()}
    before, after = groups(held), groups(repeat)
    worse = [name for name in before if before[name] and not after[name]]
    better = [name for name in before if after[name] and not before[name]]
    return worse, better


def prepare(repo, entries, baseline, verifier=verify_held, *, on_main=True):
    """The candidate: the verified held record plus this run's new pairs.

    A held pair is immutable, so a repeat of it adds nothing. On main a repeat
    with another verdict raises. Off main (main fix F3) only a repeat worse
    than the held entry raises: main records a whole pair all-false when one of
    its shards fails, and a two-way check would then fail every later pull
    request on that build, the record-update pull request included. A better
    repeat keeps the held entry and warns.
    """
    # Fetching/verification precede any write to the publication branch.
    path = Path(repo)/RECORD
    current = json.loads(path.read_text())
    verifier(path)
    append_only(baseline,current)
    indexed={(item['build'],item['version'],item['channel']):item for item in current['entries']}
    added=[]
    for item in entries:
        validate_record({'format': 1, 'entries': [item]})
        key=item['build'],item['version'],item['channel']
        existing=indexed.get(key)
        if existing:
            if existing['core']!=item['core'] or existing['adapters']!=item['adapters']:
                worse,better=compared(existing,item)
                if on_main:
                    raise ValueError('Conflicting repeat for an immutable qualification pair; publish nothing')
                if worse:
                    raise ValueError('Conflicting repeat for an immutable qualification pair: this run fails '+', '.join(worse)+', which the held record passes; publish nothing')
                print('::warning::This run passes '+', '.join(better)+' for build '+key[0][:12]+', Chrome '+key[2]+' '+key[1]+', which the held record fails. The record is immutable: the held entry stays, so those groups stay disabled for this build and Chrome version.', flush=True)
            continue
        added.append(item)
        indexed[key] = item
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


def measured_chrome_version(text):
    """The full version from `chrome --version`, or None.

    Stable prints 'Google Chrome 157.0.8103.78 ' and beta 'Google Chrome
    159.0.8154.6 beta'. The version is the token after the name, never the
    last word: reading the last word turned every beta pair into 'beta' and
    so into an all-false entry (main run 43696892949).
    """
    match=re.fullmatch(r'Google Chrome (\d+(?:\.\d+){3})(?: [a-z]+)?',text.strip())
    return match[1] if match else None


def notify(candidate, published, runner=subprocess.run):
    """Only the main-only CLI invokes this; tests inject a recording subprocess runner.

    The failing-groups issue lists only this run's entries (GITHUB_RUN_ID);
    the shipped-copy issue lists every entry on the data branch.

    Every GitHub write is an issue. The repository doesn't let workflows
    create pull requests, so the shipped-copy update is an issue a session
    acts on. Each title keeps one open issue: a run comments on it only when
    its text is new, so the daily runs don't pile up duplicates. Only the
    workflow's own issues and comments count: the repository is public, and
    anyone can open an issue or write a comment with the same title or text.
    """
    def gh(arguments):
        try:return runner(['gh',*arguments],check=True,capture_output=True,text=True)
        except subprocess.CalledProcessError as error:
            raise SystemExit('gh '+' '.join(arguments[:2])+' failed: '+(error.stderr or '').strip()) from None
    def rows(arguments):
        return [json.loads(line) for line in gh(arguments).stdout.splitlines() if line.strip()]
    def own(row):
        return row['user']==WORKFLOW_BOT and row['type']=='Bot'
    def report(title, body):
        listed=rows(['api','--paginate','repos/'+REPOSITORY+'/issues?state=open&creator='+WORKFLOW_BOT.replace('[','%5B').replace(']','%5D')+'&per_page=100',
                     '--jq','.[] | {number, title, body, user: .user.login, type: .user.type, pull: (.pull_request != null)}'])
        mine=sorted((issue for issue in listed if own(issue) and not issue['pull'] and issue['title']==title),key=lambda issue:issue['number'])
        if not mine:
            gh(['issue','create','--repo',REPOSITORY,'--title',title,'--body',body]);return
        comments=rows(['api','--paginate','repos/'+REPOSITORY+'/issues/'+str(mine[0]['number'])+'/comments',
                       '--jq','.[] | {body, user: .user.login, type: .user.type}'])
        if body!=mine[0]['body'] and body not in [comment['body'] for comment in comments if own(comment)]:
            gh(['issue','comment',str(mine[0]['number']),'--repo',REPOSITORY,'--body',body])
    # Notify runs only on main, where GitHub always sets the run ID. Without
    # one it refuses before any GitHub call, on both paths: the failing-groups
    # issue couldn't tell this run's entries apart (it would fall back to the
    # whole record, issue #74), and the refused-publication issue would link
    # to no run.
    this_run=os.environ.get('GITHUB_RUN_ID','')
    if not this_run:raise SystemExit('Qualification notify needs GITHUB_RUN_ID to name this run')
    if not published:
        run=os.environ.get('GITHUB_SERVER_URL','https://github.com')+'/'+REPOSITORY+'/actions/runs/'+this_run
        report('Chrome qualification publication refused',
               'Record or attestation verification failed, or a workflow job was interrupted. Nothing new is trusted. Inspect this qualification run: '+run)
        return
    # The failing-groups issue names only the entries this run published. The
    # record is append-only, so over the whole of it an old build's failure
    # would be reported on every run for good (issue #74).
    record=validate_record(json.loads(Path(candidate).read_text()))
    failures=[]
    for entry in record['entries']:
        if entry['run']!=this_run:continue
        names=[name for name,passed in {**entry['core'],**entry['adapters']}.items() if not passed]
        if names:failures.append(entry['build']+' '+entry['channel']+' '+entry['version']+': '+', '.join(names))
    if failures:
        report('Chrome qualification has failing groups',
               'Failed groups stay disabled for their installed build and version.\n\n'+'\n'.join(failures))
    entries='\n'.join(entry['build'][:12]+' '+entry['channel']+' '+entry['version'] for entry in record['entries'])
    report('Update shipped Chrome qualification record',
           'The data branch `'+DATA_BRANCH+'` holds attested entries that the shipped copy (`control/chrome/qualification.json` on main) may lack. '
           'Runtime delivery already uses the attested record. A session opens the pull request and reviews it before merging:\n\n'
           '`gh pr create --repo '+REPOSITORY+' --head '+DATA_BRANCH+' --base main --title "Update shipped Chrome qualification record"`\n\n'
           'Entries on the data branch:\n'+entries)


def publish(root, candidate, baseline, *, remote=None, verifier=verify, bundle=None, held_verifier=verify_held, ref=None):
    """Only the main-only CLI uses the real remote; pull-request runs and tests supply a local bare repo.

    The candidate is verified against the bundle the attest step just made,
    so a fresh publication depends on no API listing. A held data-branch
    record (second and later runs) is verified by held_verifier. ref is the
    pull-request mode's own source ref for the fresh bundle; main's policy
    stays the default and the CLI allows ref only with a local remote.
    """
    if bundle is None:
        verifier(candidate)
    elif ref is None:
        verifier(candidate, bundle=bundle)
    else:
        verifier(candidate, bundle=bundle, ref=ref)
    candidate_record = append_only(baseline, json.loads(candidate.read_text()))
    with tempfile.TemporaryDirectory(dir=root/'.work') as temporary:
        repository = Path(temporary)
        git(repository, 'init')
        git(repository, 'remote', 'add', 'origin', remote or 'https://github.com/'+REPOSITORY+'.git')
        credentials = ('-c', 'credential.helper=!gh auth git-credential') if remote is None else ()
        exists = git(repository, *credentials, 'ls-remote', '--heads', 'origin', 'refs/heads/'+DATA_BRANCH)
        # First publication: the data branch is cut from main, whose shipped
        # record is the reviewed baseline; the candidate must extend it.
        git(repository, *credentials, 'fetch', 'origin', DATA_BRANCH if exists else 'main')
        git(repository, 'checkout', '-b', DATA_BRANCH, 'FETCH_HEAD')
        if exists:
            held_verifier(repository/RECORD)
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
    parser.add_argument('command',choices=['plan','pair','prepare','publish','notify','held-bundles'])
    parser.add_argument('--root',default='.')
    parser.add_argument('--artifacts')
    parser.add_argument('--plan')
    parser.add_argument('--runtime-root')
    parser.add_argument('--candidate',default='.work/qualification-candidate.json')
    parser.add_argument('--channels',default='stable,beta',help='plan: Chrome channels to qualify; pull-request runs take one')
    parser.add_argument('--bundle',help='publish: the Sigstore bundle the attest step made for the candidate')
    parser.add_argument('--remote',help='publish: an existing local bare repository instead of origin (pull-request mode)')
    parser.add_argument('--ref',help='publish --remote only: the full ref this run attested the candidate on')
    parser.add_argument('--held-bundle',help='publish --remote only: the held record\'s bundle list from held-bundles')
    parser.add_argument('--output',help='held-bundles: where to write the held record\'s bundle list')
    args=parser.parse_args();root=Path(args.root)
    on_main=os.environ.get('GITHUB_REF')=='refs/heads/main'
    if args.command=='plan':
        channels=args.channels.split(',')
        if not channels or set(channels)-{'stable','beta'} or len(set(channels))!=len(channels):
            raise ValueError('--channels takes stable, beta or stable,beta')
        with urllib.request.urlopen(PACKAGES,timeout=30) as response:data=gzip.decompress(response.read(8*1024*1024)).decode()
        held=json.loads((root/RECORD).read_text())
        exists=git(root,'ls-remote','--heads','origin','refs/heads/'+DATA_BRANCH)
        if exists:
            git(root,'fetch','origin',DATA_BRANCH)
            content=git(root,'show','FETCH_HEAD:'+RECORD)
            with tempfile.NamedTemporaryFile(dir=root,suffix='.json',mode='w') as temporary:
                temporary.write(content+'\n');temporary.flush();verify_held(temporary.name)
                held=append_only(held,json.loads(content))
        versions={channel:package for channel,package in packages(data).items() if channel in channels}
        matrix=plan(json.loads((root/'control/chrome/builds.json').read_text()),versions,held,git(root,'rev-parse','HEAD'),build_hash(root.resolve()),requalify_head=not on_main)
        print(json.dumps(matrix));return
    if args.command=='held-bundles':
        if not args.output:raise ValueError('held-bundles requires --output')
        held_bundles(root,Path(args.output));return
    if args.command=='pair':
        identity=json.loads(os.environ['QUALIFICATION_PAIR'])
        # A result file is emitted only by the complete browser suite. Missing/crashed runs fail every group.
        result_path=Path(args.artifacts)/'qualification-result.json'
        result=json.loads(result_path.read_text()) if result_path.exists() else {}
        actual = (Path(args.artifacts)/'chrome-version.txt')
        measured_version = measured_chrome_version(actual.read_text()) if actual.exists() else None
        measured_build = runtime_identity(Path(args.runtime_root).resolve()) if args.runtime_root else None
        valid = (measured_version == identity['version'] and measured_build == identity['build']
                 and completed(args.artifacts, identity, os.environ.get('QUALIFICATION_OUTCOME'))
                 and result.get('groups', {}).get('12') is True)
        identity.update(core={key: valid and result.get('core', {}).get(key) is True for key in CORE_GROUPS},
                        adapters={key: valid and result.get('adapters', {}).get(key) is True for key in HOSTS})
        Path(args.artifacts).mkdir(parents=True,exist_ok=True)
        (Path(args.artifacts)/'pair.json').write_text(json.dumps(identity));return
    # Only this repository prepares or publishes. Writes that reach GitHub (the
    # push to origin's data branch and issues) happen on main
    # only; a pull request or branch run prepares, attests and publishes to a
    # local bare repository so that every step runs before the merge.
    if os.environ.get('GITHUB_REPOSITORY')!=REPOSITORY:
        raise SystemExit('Qualification publication is restricted to this repository')
    candidate=Path(args.candidate)
    if args.command=='notify':
        if not on_main:raise SystemExit('Qualification notifications are restricted to main')
        notify(candidate,os.environ.get('PUBLISH_STATE')=='success');return
    if args.command=='prepare':
        if not args.plan:
            raise ValueError('Publication requires the complete expected qualification plan')
        entries=aggregate(args.artifacts,os.environ['GITHUB_RUN_ID'],json.loads(Path(args.plan).read_text()))
        baseline=json.loads(git(root,'show','origin/main:'+RECORD))
        exists=git(root,'ls-remote','--heads','origin','refs/heads/'+DATA_BRANCH)
        if not exists:
            candidate.parent.mkdir(parents=True,exist_ok=True)
            candidate.write_text(serialized(append_only(baseline,{'format':1,'entries':baseline['entries']+entries}),on_main));return
        git(root,'fetch','origin',DATA_BRANCH)
        current=git(root,'show','FETCH_HEAD:'+RECORD)
        with tempfile.TemporaryDirectory(dir=root/'.work') as temporary:
            publication=Path(temporary);(publication/RECORD).parent.mkdir(parents=True)
            (publication/RECORD).write_text(current+'\n')
            result=prepare(publication,entries,baseline,on_main=on_main)
        candidate.parent.mkdir(parents=True,exist_ok=True);candidate.write_text(serialized(result,on_main));return
    if args.remote is None:
        if not on_main:raise SystemExit('Qualification publication to origin is restricted to main')
        if args.ref:raise SystemExit('Publication to origin verifies the candidate under the main policy only; --ref is for --remote')
        if args.held_bundle:raise SystemExit('Publication to origin fetches the held bundles itself; --held-bundle is for --remote')
        remote=None
    else:
        remote=Path(args.remote)
        if '://' in args.remote or not remote.is_dir():
            raise SystemExit('--remote must be an existing local directory, never a URL')
        remote=str(remote.resolve())
    if not args.bundle:
        raise ValueError('publish requires the bundle the attest step made for this candidate')
    baseline=json.loads(git(root,'show','origin/main:'+RECORD))
    if args.held_bundle:
        # The token-free pull-request step: the held record is verified from
        # the bundle list a read-only step fetched, under main's policy.
        publish(root,candidate,baseline,remote=remote,bundle=Path(args.bundle),ref=args.ref,held_verifier=held_from_file(Path(args.held_bundle)))
    else:
        publish(root,candidate,baseline,remote=remote,bundle=Path(args.bundle),ref=args.ref)


if __name__=='__main__':main()
