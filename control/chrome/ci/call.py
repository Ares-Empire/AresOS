"""Exercise caller-side transfer as the synthetic owner, inside the runner only.

`call.py <verb> <json>` calls through the MCP proxy and prints its result.
`--command` goes through the `aresos` command instead (brief 28, group 14's
time cases), and `--timed` prints {"result", "seconds"}, the seconds of the call
alone, without this process's start.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import time
if sys.platform!='linux' or os.environ.get('GITHUB_ACTIONS')!='true' or not Path('/.dockerenv').exists():
    raise SystemExit('Synthetic caller runs only in GitHub Linux containers')
sys.path.insert(0,'/workspace/control')
from aresos_control import cli
from aresos_control.proxy import Proxy
config={'act_socket':'/run/aresos-tools/act.sock','admin_socket':'/run/aresos-tools/admin.sock',
        'home':'/home/owner','folders':['/home/owner/Downloads']}
arguments=sys.argv[1:]
command=timed=False
while arguments and arguments[0].startswith('--'):
    flag=arguments.pop(0)
    if flag=='--command':command=True
    elif flag=='--timed':timed=True
    else:raise SystemExit('Unknown flag '+flag)
verb,text=arguments
verb=verb.removeprefix('chrome_')
start=time.monotonic()
if command:
    printed=io.StringIO()
    with contextlib.redirect_stdout(printed):
        cli.main(config,['chrome',verb,'--input',text])
    result=json.loads(printed.getvalue())
else:
    result=Proxy('chrome',config).call(verb,json.loads(text))
seconds=time.monotonic()-start
print(json.dumps({'result':result,'seconds':seconds} if timed else result))
