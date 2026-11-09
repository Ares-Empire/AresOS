"""Synthetic Linux-container bootstrap; never imported by the installed runtime."""
import json
import os
from pathlib import Path
import subprocess
import sys

if sys.platform != 'linux' or os.environ.get('GITHUB_ACTIONS') != 'true' or not Path('/.dockerenv').exists():
    raise SystemExit('Browser fixtures run only in a GitHub Linux container')
from aresos_control.engine import Engine
from aresos_control.daemon import Daemon
from aresos_control.chrome.policy import CORE_GROUPS, HOSTS

config={'owner_uid':1000,'state_dir':'/var/lib/aresos-tools','evidence_dir':'/var/lib/aresos-operation-evidence','socket_dir':'/run/aresos-tools'}
engine=Engine(config['state_dir'],config['evidence_dir'])
version=subprocess.check_output(['qualification-chrome','--version'],text=True).split()[2]
build=engine.adapters['chrome'].qualification.build
# This store is disposable test input. No qualification pass is shipped by this bootstrap.
record={'format':1,'entries':[{'build':build,'version':version,'channel':'stable','run':'synthetic-fixture-setup',
                              'core':dict.fromkeys(CORE_GROUPS,True),'adapters':dict.fromkeys(HOSTS,True)}]}
engine.store.write({'chrome:qualification':record},'chrome_test_setup','Synthetic qualification input for fixture tests')
engine.close()
daemon=Daemon(config)
daemon.engine.adapters['chrome'].refresh_qualification=False
bridge=daemon.engine.adapters['chrome'].bridge
original_event=bridge.on_event
original_accept=bridge.accept
def accept(connection):
    original_accept(connection)
    bridge.call('audit',enabled=True)
bridge.accept=accept
boundary=open('/out/browser-boundary.jsonl','a',buffering=1)
bridge.audit_sink=lambda data:boundary.write(json.dumps(data)+'\n')
bridge.on_event=lambda event:(print('CHROME_EVENT',json.dumps(event),flush=True),original_event(event))[-1]
daemon.engine.adapters['chrome'].hosts={name:[name+'.test'] for name in HOSTS}
try:
    daemon.serve()
finally:
    daemon.close()
