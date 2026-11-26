"""Synthetic Linux-container bootstrap; never imported by the installed runtime."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

if sys.platform != 'linux' or os.environ.get('GITHUB_ACTIONS') != 'true' or not Path('/.dockerenv').exists():
    raise SystemExit('Browser fixtures run only in a GitHub Linux container')
from aresos_control.engine import Engine
from aresos_control.daemon import Daemon
from aresos_control.chrome.policy import CORE_GROUPS, HOSTS
sys.path.append(str(Path(__file__).resolve().parents[2]/'chrome_tests'))
import qualification_fixture

# The held record below is synthetic, so this service starts Chrome from a
# fixture runtime: the tree's build identity beside a shipped copy of the
# fixture's own, whatever control/chrome/qualification.json holds (#79). That
# copy is empty, except in the latency leg that measures a record of realistic
# size: there it holds several hundred entries of earlier builds (#79 O2).
shipped=qualification_fixture.harness_shipped(os.environ)
qualification_fixture.install(tempfile.mkdtemp(prefix='fixture-runtime-'),baseline=shipped)
config={'owner_uid':1000,'state_dir':'/var/lib/aresos-tools','evidence_dir':'/var/lib/aresos-operation-evidence','socket_dir':'/run/aresos-tools'}
engine=Engine(config['state_dir'],config['evidence_dir'])
version=subprocess.check_output(['qualification-chrome','--version'],text=True).split()[2]
build=engine.adapters['chrome'].qualification.build
# This store is disposable test input. No qualification pass is shipped by this bootstrap.
record=qualification_fixture.harness_record(shipped,build,version)
print('FIXTURE_QUALIFICATION',json.dumps({'shipped_entries':len(shipped['entries']),'held_entries':len(record['entries'])}),flush=True)
if not engine.store.get('chrome:qualification'):
    engine.store.write({'chrome:qualification':record},'chrome_test_setup','Synthetic qualification input for fixture tests')
engine.close()
daemon=Daemon(config)
original_background_error=daemon.engine.background_error
def background_error(error):
    import traceback
    print('FIXTURE_BACKGROUND_ERROR',repr(error),flush=True)
    traceback.print_exception(type(error),error,error.__traceback__)
    return original_background_error(error)
daemon.engine.background_error=background_error
Path('/run/aresos-tools/fixture-service.pid').write_text(str(os.getpid()))
def checkpoint(point):
    cut=Path('/run/aresos-tools/fixture-cut.json')
    if cut.exists() and json.loads(cut.read_text()).get('point')==point:
        Path('/out/checkpoint-ready.json').write_text(json.dumps({'point':point}))
        import time
        release=Path('/out/checkpoint-release')
        while not release.exists():time.sleep(.005)
        release.unlink();cut.unlink(missing_ok=True)
daemon.engine.store.checkpoint=checkpoint
from aresos_control.chrome.sites import KINDS
original_kind_scope=KINDS['gmail_send']['scope']
original_request=daemon.engine.request
def request(value,admin=False):
    if admin and value.get('method')=='fixture_observe':
        observation=value.get('observe')
        if observation=='audit':
            rows=[{key:row[key] for key in ('seq','action','summary','operation_id')}
                  for row in daemon.engine.store.iter_audit() if row['action']=='chrome_take_tab']
            return {'ok':True,'data':rows}
        if observation in {'tabs','page'}:
            arguments={'tab':value['tab']} if observation=='page' else {}
            return {'ok':True,'data':bridge.call('fixture_observe_'+observation,**arguments)}
    kind=Path('/run/aresos-tools/fixture-kind')
    if kind.exists():
        mode=kind.read_text();kind.unlink()
        KINDS['gmail_send']['scope']=original_kind_scope+(' and widened synthetic recipients' if mode=='widen' else '')
    qualification=Path('/run/aresos-tools/fixture-qualification')
    if qualification.exists():
        mode=qualification.read_text();qualification.unlink()
        # The modes rewrite the one synthetic entry over the empty baseline.
        if shipped['entries']:raise ValueError('Synthetic qualification modes need the empty shipped copy')
        candidate=json.loads(json.dumps(record))
        if mode=='conservative':candidate['entries']=[]
        elif mode in CORE_GROUPS:candidate['entries'][0]['core'][mode]=False
        elif mode!='qualified':raise ValueError('Unknown synthetic qualification mode')
        daemon.engine.store.write({'chrome:qualification':candidate},'chrome_test_qualification','Synthetic qualification mode')
    expiry=Path('/run/aresos-tools/fixture-expire')
    if expiry.exists():
        identifier=expiry.read_text();expiry.unlink()
        operation=daemon.engine.operation(identifier,'chrome');operation['expires']=0
        daemon.engine.store.write({'op:'+identifier:operation},'chrome_test_expire','Fixture deadline passed',identifier)
    popup=Path('/run/aresos-tools/fixture-popup')
    if popup.exists():
        popup.unlink();daemon.engine.adapters['chrome'].bridge.call('stop_popup')
    status=Path('/run/aresos-tools/fixture-control_status')
    if status.exists():
        status.unlink();Path('/out/control-status.json').write_text(json.dumps(daemon.engine.adapters['chrome'].bridge.call('control_status')))
    restart=Path('/run/aresos-tools/fixture-network_restart')
    if restart.exists():
        arguments=json.loads(restart.read_text());restart.unlink()
        Path('/out/network-restart.json').write_text(json.dumps(daemon.engine.adapters['chrome'].bridge.call('fixture_network_restart',tab=arguments['tab'])))
    stop=Path('/run/aresos-tools/fixture-stop')
    if stop.exists():
        stop.unlink();Path('/out/stop-result.json').write_text(json.dumps(daemon.engine.adapters['chrome'].bridge.call('stop')))
    result=original_request(value,admin)
    # Brief 28, group 14's time cases: the test build holds a tab's reader
    # replies, or its own reply to one command, back (prepare.mjs). Set after
    # this request, so that its own looks at pending aren't held.
    hold=Path('/run/aresos-tools/fixture-hold')
    if hold.exists():
        arguments=json.loads(hold.read_text());hold.unlink()
        Path('/out/fixture-hold.json').write_text(json.dumps(daemon.engine.adapters['chrome'].bridge.call(arguments['command'],**arguments['arguments'])))
    return result
daemon.engine.request=request
daemon.engine.adapters['chrome'].refresh_qualification=False
bridge=daemon.engine.adapters['chrome'].bridge
original_event=bridge.on_event
original_accept=bridge.accept
# The daemon passes the connected peer (final F7) on this branch and nothing on
# the latency pair's historical runtime; forward whatever it gives.
def accept(connection,*peer):
    original_accept(connection,*peer)
    bridge.call('audit',enabled=os.environ.get('LATENCY_PROBE')!='true' or os.environ.get('LATENCY_PRIVACY')=='audit')
bridge.accept=accept
# The latency pair writes this harness stream to a tmpfs (main fix H5), so its
# flushes do not share the store's disk journal with the product's fsyncs.
boundary=open(os.environ.get('FIXTURE_LOG_DIR','/out')+'/browser-boundary.jsonl','a',buffering=1)
bridge.audit_sink=lambda data:boundary.write(json.dumps(data)+'\n')
original_call=bridge.call
def call(name,**arguments):
    arm_delay=Path('/run/aresos-tools/fixture-arm-delay')
    if name=='input' and arm_delay.exists():
        arguments['fixture_arm_delay']=int(arm_delay.read_text());arm_delay.unlink()
    cut=Path('/run/aresos-tools/fixture-cut.json')
    if name in {'input','resume','dialog'} and cut.exists() and json.loads(cut.read_text()).get('point')=='after-input':
        arguments['fixture_cut']='after-input';cut.unlink()
    return original_call(name,**arguments)
bridge.call=call
def event(value):
    print('CHROME_EVENT',json.dumps(value),flush=True)
    if value.get('event')=='fixture_arm_wait':Path('/out/arm-ready.json').write_text(json.dumps({'operation':value['operation']}))
    if value.get('event')=='fixture_after_input':Path('/out/checkpoint-ready.json').write_text(json.dumps({'point':'after-input','operation':value['operation']}))
    return original_event(value)
bridge.on_event=event
daemon.engine.adapters['chrome'].hosts={name:[name+'.test'] for name in HOSTS}
from sites.qualification import install; install(daemon)
if os.environ.get('LATENCY_PROBE')=='true':
    import importlib.util
    spec=importlib.util.spec_from_file_location('latency_profile',Path(__file__).with_name('latency-profile.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.install(daemon)
try:
    daemon.serve()
finally:
    daemon.close()
