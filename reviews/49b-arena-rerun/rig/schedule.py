"""The frozen 18-run schedule, with retained/repeated interference and no silent exclusions."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
WORK=HERE.parents[2]/'.work/pkg49b'


def fingerprint(base):
    digest=hashlib.sha256();size=0;count=0
    for path in sorted(base.rglob('*')):
        if not path.is_file(): continue
        data=path.read_bytes();size+=len(data);count+=1
        digest.update(path.relative_to(base).as_posix().encode()+b'\0'+hashlib.sha256(data).hexdigest().encode()+b'\n')
    return {'aggregate_tree_sha256':digest.hexdigest(),'files':count,'bytes':size,'manifest':(base/'aresos-home.properties').read_text()}


def run(slot, settings, utility=False):
    attempt=1
    while True:
        name=slot if attempt==1 else f'{slot}-repeat-{attempt}'
        out=ROOT/'runs'/name
        failure=ROOT/'failures'/name
        if (failure/'attempt.json').exists():
            print('Retained earlier failure:',name,flush=True)
            attempt+=1
            continue
        if not (out/'summary.json').exists():
            print(time.strftime('%Y-%m-%dT%H:%M:%S'), 'START', name, flush=True)
            with (WORK/(name+'.txt')).open('a') as log:
                result=subprocess.run([str(HERE/'retry.sh'),str(HERE/'run.sh'),name,'COVER=300','SHOTS=0',*settings],stdout=log,stderr=subprocess.STDOUT)
            if result.returncode:
                failure.mkdir(parents=True,exist_ok=True)
                partial=WORK/'rigs'/name
                for path in partial.glob('*'):
                    if path.is_file() and (path.name in ('settings.txt','marks.txt','samples.csv','host-start.json','host-end.json','health-failure.json','host-watch.jsonl','provenance.json','gc.txt') or path.name.startswith('snap-')):
                        text=path.read_text().replace(str(HERE.parents[2]),'<worktree>').replace(str(Path.home()),'<home>')
                        (failure/path.name).write_text(text)
                (failure/'attempt.json').write_text(json.dumps({'slot':slot,'attempt':name,'utility':utility,'accepted':False,'exit':result.returncode,'reason':'non-zero rig exit; stopped for diagnosis'},indent=2)+'\n')
                raise SystemExit(f'{name}: exit {result.returncode}; schedule stopped, no later slot started')
        watch=[json.loads(line) for line in (out/'host-watch.jsonl').read_text().splitlines()]
        external=[{'monotonic_ns':row['monotonic_ns'],'external_java':row['external_java']} for row in watch if any(p['kind'] in ('gradle','game') for p in row['external_java'])]
        entry={'slot':slot,'attempt':name,'utility':utility,'contaminated':bool(external),'interference_samples':external,'accepted':not bool(external)}
        (out/'attempt.json').write_text(json.dumps(entry,indent=1)+'\n')
        print(time.strftime('%Y-%m-%dT%H:%M:%S'),'DONE',name,'CONTAMINATED: repeat required' if external else 'accepted',flush=True)
        time.sleep(30)
        if not external:return name
        attempt+=1


def fixtures():
    flat=WORK/'AresHub-base'
    if not flat.exists():
        name=run('setup-flat',['MODE=create','CREATE_FLOW=automatic','QUIT=1','COVER=0'],True)
        shutil.copytree(WORK/'rigs'/name/'world',flat)
    path=ROOT/'fixture-hashes.json'
    facts=json.loads(path.read_text()) if path.exists() else {}
    facts.setdefault('flat',fingerprint(flat));path.write_text(json.dumps(facts,indent=2)+'\n')


def main():
    fixtures()
    accepted={}
    for index,order in enumerate(('AB','BA','BA','AB','AB','BA'),1):
        for kind in order:
            slot=f'flat-{index}-'+('control' if kind=='A' else 'arena')
            accepted[slot]=run(slot,[] if kind=='A' else ['ENV=MALLOC_ARENA_MAX=2'])
    for index,order in enumerate(('AB','BA'),1):
        for kind in order:
            slot=f'create-{index}-'+('control' if kind=='A' else 'arena')
            accepted[slot]=run(slot,['MODE=create','CREATE_FLOW=automatic',*([] if kind=='A' else ['ENV=MALLOC_ARENA_MAX=2'])])
    nether=WORK/'AresHub-nether-base'
    if not nether.exists():
        name=run('setup-nether',['MODE=create','HOMEKIND=nether','CREATE_FLOW=menu','FLIGHT=none','QUIT=1','COVER=0'],True)
        shutil.copytree(WORK/'rigs'/name/'world',nether)
        subprocess.run([sys.executable,'-I',str(HERE/'prepare-glide.py'),str(nether)],check=True)
    path=ROOT/'fixture-hashes.json';facts=json.loads(path.read_text());facts.setdefault('nether',fingerprint(nether))
    path.write_text(json.dumps(facts,indent=2)+'\n')
    for kind in 'AB':
        slot='nether-'+('control' if kind=='A' else 'arena')
        accepted[slot]=run(slot,['BASE=AresHub-nether-base','HOMEKIND=nether','FLIGHT=glide',*([] if kind=='A' else ['ENV=MALLOC_ARENA_MAX=2'])])
    (ROOT/'accepted.json').write_text(json.dumps(accepted,indent=2)+'\n')
    for kind,base in [('flat',WORK/'AresHub-base'),('nether',nether)]:
        assert fingerprint(base)==facts[kind], f'{kind} fixture changed'
    print('COMPLETE: 18 accepted measurements; fixtures unchanged',flush=True)


if __name__=='__main__':main()
