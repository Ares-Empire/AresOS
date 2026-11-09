"""Owner-channel fixture, only root in the disposable Linux runner container."""
import json
import os
from pathlib import Path
import socket
import sys
if sys.platform!='linux' or os.getuid()!=0 or os.environ.get('GITHUB_ACTIONS')!='true' or not Path('/.dockerenv').exists():
    raise SystemExit('Synthetic owner admin runs only as root in GitHub Linux containers')
request=json.loads(sys.argv[1])
with socket.socket(socket.AF_UNIX) as connection:
    connection.connect('/run/aresos-tools/admin.sock')
    connection.sendall((json.dumps({'v':1,'method':'call',**request})+'\n').encode())
    print(connection.makefile().readline(),end='')
