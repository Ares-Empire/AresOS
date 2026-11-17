#!/usr/bin/python3
"""Run a named, reviewable schedule sequentially, giving other builders a lock opportunity between games.

usage: batch.py step0|factors|covered|winners [winners.json]
The winners file must be a JSON object with a `settings` array of literal KEY=value strings, selected after
reading the factor/cover evidence. No shell evaluation. A failure stops; resuming skips only completed summaries.
"""
import json, os, pathlib, shutil, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent
WT = ROOT.parents[2]
WORK = WT / '.work/pkg49'
OUT = ROOT.parent / 'runs'
BASE_GC = '-XX:MaxHeapFreeRatio=30,-XX:MinHeapFreeRatio=10'
MOD = str(WORK / 'downloads/ferritecore-9.0.0-fabric.jar')


def run(name, *settings):
    if (OUT / name / 'summary.json').exists():
        print('Already completed:', name, flush=True)
        return
    command = [str(ROOT/'retry.sh'), str(ROOT/'run.sh'), name, 'COVER=300', *settings]
    print(time.strftime('%Y-%m-%d %H:%M:%S'), name, settings, flush=True)
    with (WORK/(name+'.txt')).open('a') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise SystemExit(f'{name} stopped with exit {result.returncode}; see its local log. No later runs started.')
    print('Completed:', name, flush=True)
    # Release the shared game lock and leave time for another waiting builder to enter.
    time.sleep(30)


def matrix(stage, winners=None):
    if stage == 'step0':
        base = WORK/'AresHub-base'
        if not base.exists():
            shutil.copytree(WORK/'rigs/setup-flat/world', base)
        run('s0-probe', 'PROBE=1')
        run('s0-long', 'LONG=20', 'FLIGHT=none', 'COVER=0')
    elif stage == 'factors':
        print('Waiting for the step-0 measurement audit (factors-ready marker).', flush=True)
        while not (WORK/'factors-ready').exists(): time.sleep(5)
        snaps = json.loads((OUT/'s0-probe/summary.json').read_text())['snapshots']
        # Use the larger observed return from either direct trim or the post-GC trim, at every snapshot.
        skip_native = all(max(v['probe_trim_rss_delta_mib'], v['probe_gc_trim_rss_delta_mib']) < 30 for v in snaps.values())
        (ROOT.parent/'native-gate.json').write_text(json.dumps({'threshold_mib':30,'skip_native_factors':skip_native,
            'snapshots':{k:{f:v[f] for f in ('probe_trim_rss_delta_mib','probe_gc_trim_rss_delta_mib')} for k,v in snaps.items()}},indent=2)+'\n')
        factors = [('coh', ['GC='+BASE_GC+',-XX:+UseCompactObjectHeaders']),
                   ('dedup', ['GC='+BASE_GC+',-XX:+UseCompactObjectHeaders,-XX:+UseStringDeduplication'])]
        if not skip_native:
            factors += [('trim', ['GC='+BASE_GC+',-XX:TrimNativeHeapInterval=60000']),
                        ('system', ['GC='+BASE_GC+',-XX:TrimNativeHeapInterval=60000,-Dorg.lwjgl.system.allocator=system']),
                        ('arenas', ['ENV=MALLOC_ARENA_MAX=2'])]
        factors += [('threads', ['GC='+BASE_GC+',-XX:ParallelGCThreads=4,-XX:ConcGCThreads=1,-Dmax.bg.threads=4']),
                    ('ferrite', ['MODS='+MOD])]
        # A/B, B/A order in the two rounds, each factor against a new unmodified v1 run.
        # Baseline drift and each adjacent comparison remain inspectable, rather than pooled invisibly.
        for repeat in (1,2):
            for name, flags in factors:
                pair=[('v1-'+name+'-'+str(repeat), []), (name+'-'+str(repeat), flags)]
                for label, settings in (pair if repeat==1 else reversed(pair)):
                    run(label, *settings)
    elif stage == 'covered':
        variants=[('none',[]), ('gc',['COVER_ACTION=gc-trim']), ('r300',['RECLAIM=300M']),
                  ('r600',['RECLAIM=600M']), ('freeze',['RECLAIM=600M','FREEZE=1'])]
        for repeat in (1,2):
            for name, flags in (variants if repeat==1 else reversed(variants)):
                run('cover-'+name+'-'+str(repeat), *flags)
    elif stage == 'winners':
        settings=json.loads(pathlib.Path(winners).read_text())['settings']
        # Verify the refreshed automatic/menu creation observations before the longer flat matrix.
        run('v1-create', 'MODE=create', 'HOMEKIND=flat', 'CREATE_FLOW=automatic', 'QUIT=1')
        run('winner-create', *settings, 'MODE=create', 'HOMEKIND=flat', 'CREATE_FLOW=automatic', 'QUIT=1')
        run('setup-nether', *settings, 'MODE=create', 'HOMEKIND=nether', 'CREATE_FLOW=menu', 'FLIGHT=none', 'QUIT=1')
        base=WORK/'AresHub-nether-base'
        if not base.exists():
            shutil.copytree(WORK/'rigs/setup-nether/world', base)
            subprocess.run([sys.executable,'-I',str(ROOT/'prepare-glide.py'),str(base)],check=True)
        # Main moved during the long factor matrix. Qualify the combination against fresh controls
        # from the merged mod tree, rather than pooling the earlier revision's controls invisibly.
        for repeat in (1,2,3):
            pair=[('v1-flat-'+str(repeat), []), ('winner-flat-'+str(repeat), settings)]
            for name, flags in (reversed(pair) if repeat == 2 else pair): run(name, *flags)
        # A current v1 control verifies frames/TPS on the same untouched Nether base, not an older mod revision.
        run('v1-nether', 'BASE=AresHub-nether-base', 'HOMEKIND=nether', 'FLIGHT=glide')
        run('winner-nether', *settings, 'BASE=AresHub-nether-base', 'HOMEKIND=nether', 'FLIGHT=glide')
        run('winner-long', *settings, 'LONG=20', 'COVER=0', 'FLIGHT=none')
        run('winner-nmt0', *settings, 'NMT=0')
    else: raise SystemExit(__doc__)


if __name__ == '__main__': matrix(*sys.argv[1:])
