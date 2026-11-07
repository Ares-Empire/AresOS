"""Runner-side control of disposable Dovecot configuration, never production.

The isolated tests request a fixed configuration through the shared work volume.
Only this runner process can reload the real server; no control port is exposed.
"""
import json
from pathlib import Path
import re
import subprocess
import sys
import time


def configuration(base, mode):
    if mode == 'default':
        return base
    roles = {'trash':('Cestino','NewTrash','Trash'), 'drafts':('Bozze','NewDrafts','Drafts'),
             'sent':('Posta','NewSent','Sent'), 'missing':('Cestino',None,'Trash'),
             'ambiguous':(None,'DuplicateTrash','Trash')}
    old, new, flag = roles[mode]
    if old:
        pattern = r'(mailbox "' + old + r'" \{\s+auto = create\s+special_use = )\\' + flag
        base, count = re.subn(pattern, r'\g<1>', base)
        if count != 1:
            raise ValueError('Fixture mailbox configuration not found')
    if new:
        anchor = '}\nservice imap-login'
        if base.count(anchor) != 1:
            raise ValueError('Fixture namespace configuration not found')
        block = '  mailbox "' + new + '" {\n    auto = create\n    special_use = \\' + flag + '\n  }\n'
        base = base.replace(anchor, block + anchor)
    return base


def serve(work):
    base = (work / 'dovecot.conf').read_text()
    request = work / 'role-request.json'
    while True:
        if not request.exists():
            time.sleep(0.05)
            continue
        args = json.loads(request.read_text())
        request.unlink()
        response = {'id':args['id'], 'ok':False}
        try:
            (work / 'dovecot.conf').write_text(configuration(base, args['mode']))
            subprocess.run(['docker','exec','dovecot','doveadm','reload'], capture_output=True, check=True, timeout=15)
            response['ok'] = True
        except Exception:
            response['error'] = 'Disposable Dovecot role reconfiguration failed'
        target = work / 'role-response.json'
        temporary = work / 'role-response-next.json'
        temporary.write_text(json.dumps(response))
        temporary.replace(target)


if __name__ == '__main__':
    serve(Path(sys.argv[1]))
