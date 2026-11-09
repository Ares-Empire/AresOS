"""Owner-channel fixture, only root in the disposable Linux runner container."""
import json
import os
from pathlib import Path
import socket
import sys
if sys.platform!='linux' or os.getuid()!=0 or os.environ.get('GITHUB_ACTIONS')!='true' or not Path('/.dockerenv').exists():
    raise SystemExit('Synthetic owner admin runs only as root in GitHub Linux containers')
request=json.loads(sys.argv[1])
if request.get('fixture'):
    import signal
    import subprocess
    command=request['fixture']
    if command in {'popup','stop'}:
        Path('/run/aresos-tools/fixture-'+command).write_text('open')
        request={'action':'chrome_sites','arguments':{'command':'list'}}
        with socket.socket(socket.AF_UNIX) as connection:
            connection.connect('/run/aresos-tools/admin.sock');connection.sendall((json.dumps({'v':1,'method':'call',**request})+'\n').encode());print(connection.makefile().readline(),end='')
        raise SystemExit(0)
    if command=='cut':
        Path('/out/checkpoint-ready.json').unlink(missing_ok=True)
        Path('/out/checkpoint-release').unlink(missing_ok=True)
        Path('/run/aresos-tools/fixture-cut.json').write_text(json.dumps({'point':request['point']}))
    elif command in {'expire','qualification','kind','arm_delay'}:
        if command=='expire':Path('/run/aresos-tools/fixture-expire').write_text(request['operation_id'])
        elif command=='qualification':Path('/run/aresos-tools/fixture-qualification').write_text(request['mode'])
        elif command=='kind':Path('/run/aresos-tools/fixture-kind').write_text(request['mode'])
        else:
            Path('/out/arm-ready.json').unlink(missing_ok=True)
            Path('/run/aresos-tools/fixture-arm-delay').write_text(str(request['milliseconds']))
        request={'action':'chrome_sites','arguments':{'command':'list'}}
        with socket.socket(socket.AF_UNIX) as connection:
            connection.connect('/run/aresos-tools/admin.sock');connection.sendall((json.dumps({'v':1,'method':'call',**request})+'\n').encode());print(connection.makefile().readline(),end='')
        raise SystemExit(0)
    elif command=='kill_service':os.kill(int(Path('/run/aresos-tools/fixture-service.pid').read_text()),signal.SIGKILL)
    elif command=='start_service':
        Path('/run/aresos-tools/fixture-cut.json').unlink(missing_ok=True)
        log=open('/out/service.txt','a')
        subprocess.Popen(['runuser','-u','aresos-tools','--','env','PYTHONPATH=/workspace/control','PYTHONDONTWRITEBYTECODE=1','GITHUB_ACTIONS=true','python3','control/chrome/ci/service.py'],stdout=log,stderr=log,start_new_session=True)
    else:raise SystemExit('Unknown fixture lifecycle command')
    print(json.dumps({'ok':True,'data':{'fixture':command}}));raise SystemExit(0)
with socket.socket(socket.AF_UNIX) as connection:
    connection.connect('/run/aresos-tools/admin.sock')
    connection.sendall((json.dumps({'v':1,'method':'call',**request})+'\n').encode())
    print(connection.makefile().readline(),end='')
