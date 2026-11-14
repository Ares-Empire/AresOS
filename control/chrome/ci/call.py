"""Exercise caller-side transfer as the synthetic owner, inside the runner only."""
import json
import os
from pathlib import Path
import sys
if sys.platform!='linux' or os.environ.get('GITHUB_ACTIONS')!='true' or not Path('/.dockerenv').exists():
    raise SystemExit('Synthetic caller runs only in GitHub Linux containers')
sys.path.insert(0,'/workspace/control')
from aresos_control.proxy import Proxy
config={'act_socket':'/run/aresos-tools/act.sock','admin_socket':'/run/aresos-tools/admin.sock',
        'home':'/home/owner','folders':['/home/owner/Downloads']}
print(json.dumps(Proxy('chrome',config).call(sys.argv[1],json.loads(sys.argv[2]))))
