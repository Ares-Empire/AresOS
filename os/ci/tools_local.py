"""Package 22d, step 6: the owner tools from the desktop's password window, rehearsed in the VM.

The walk (briefs/22d-tools-without-stick.md, "The walk", changed by its section "Decisions after review 2"
and by REVIEW-4's N-d and N-e) runs in package 22c's harness (os/ci/owner_vm.py) after package 27's route:

  1. Package 27's route to release 27 with tools version 2 (owner_vm.laptop_update with version 2 from
     history, then owner_vm.confirmed_update), his one-time administrator password and his sudo, as 22c's
     rehearsal begins.
  2. v3 refuses: this checkout's folder line for version 3's fingerprint with the checkout at the stand-in
     commit that holds version 3's tools (N-e), then this checkout's routine line for that fingerprint. The
     stand-in caller (a shell in his desktop session without a controlling terminal) types the password into
     the window; version 3 has no folder block and stops at its terminal test. The STOP; nothing changed.
  3. Cancel: the routine line for this head's tools; the window, then Escape. sudo ends with
     "sudo: no password was provided" and exit 1; nothing changed.
  4. An unanswered window closed by the caller (R1): the line again; after the (shortened) wait the caller
     stops only the ksshaskpass process whose parent is the sudo it started (it runs as uid 1001). Assert the
     helper is gone, sudo's message and exit status 1, nothing changed, and that the only signalled PID is
     the helper's.
  5. Cut: the line again, the password typed, a hard reset between copy and publication (22c's cut watcher
     idea, here on the tools' publication); after the restart the old tools' check passes.
  6. Install: the line once more; it resumes. PASS install, PASS check, PASS title in one window; the receipt
     names the folder, uid 1001 and no terminal; `sudo -n true` is refused.
  7. Tamper: one byte changed in the folder; STOP before any bundle code.
  8. Stick with a next version: a harness-built version 4 + 1 bundle on the stick, installed at tty3 through
     the guide's stick block, so version 4's stick route runs its own code (F13).
  9. Export to the folder (`ares` can read /run/ares-records, another account cannot) and to a stick
     holding version 2 (accepted as a bundle this laptop installed before).
 10. End: restart, check, title; every protected-disk audit unchanged.

In every dialog: the helper's argument equals the label, a screenshot shows the 70-character label wrapped
and not cut, and no keyring process starts. The N3 closed-stdin stage is dropped (N-d: sudo reopens a
closed stdin as /dev/null before anything runs).

GitHub is not reachable from the VM, and the real commits' trees are 910 MB. The lines read only
`os/owner-tools` of the announced commit, so the guest gets a stand-in origin (standin_origin): a small
repository whose `main` holds version 3's `os/owner-tools` and then this head's, each tree byte-identical to
the real commit's (git names a tree by its content, and the walk asserts the hashes are equal).
"""
import base64
import hashlib
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import time

# Version 3 of the tools (package 22c, merged as 58738e5e); it never goes on the laptop (board #265).
V3_COMMIT = '58738e5ee4d05641c9f188aef9984fe50a9a7990'
TOOLS_V3 = '2084c786c29d691a0d8c6ca450c59ef524751e5f6c475de0491f200a80765a3a'
# Where the stand-in origin lives in the guest; his checkout's `origin` points there.
GUEST_ORIGIN = '/var/home/ares/aresos-origin.git'
# Fixed identity and dates, so the stand-in commits depend only on the trees they hold.
STANDIN_ENV = dict(GIT_AUTHOR_NAME='AresOS rehearsal', GIT_AUTHOR_EMAIL='rehearsal@aresos.invalid',
                   GIT_COMMITTER_NAME='AresOS rehearsal', GIT_COMMITTER_EMAIL='rehearsal@aresos.invalid',
                   GIT_AUTHOR_DATE='2026-11-15T00:00:00Z', GIT_COMMITTER_DATE='2026-11-15T00:00:00Z')


def git(repo, *args, data=None, env=None):
    # owner_vm runs as root in the runner's checkout; trust only the repositories named here.
    return subprocess.run(['git', '-c', 'safe.directory=' + str(pathlib.Path(repo).resolve()), '-C', str(repo), *args],
                          input=data, capture_output=True, check=True, env=dict(os.environ, **(env or {}))).stdout


def standin_origin(destination, head, source='.'):
    """A git bundle for the guest's stand-in origin, and its commits.

    Two commits on `main`: first one holding exactly version 3's os/owner-tools (the tag `version-3` names
    it), then one holding exactly `head`'s. Each tree under os/owner-tools has the real commit's tree hash,
    so the folder line's checks (on origin/main, the checkout equals the commit, the commit's SHA256SUMS)
    and FROM_COMMIT read the same bytes as on GitHub. Returns dict(bundle, commits={real: stand-in}, trees).
    """
    destination = pathlib.Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    trees = {commit: git(source, 'rev-parse', commit + '^{commit}:os/owner-tools').decode().strip()
             for commit in (V3_COMMIT, head)}
    repo = destination / 'stand-in.git'
    subprocess.run(['git', 'init', '--quiet', '--bare', str(repo)], check=True)
    # Every object of the two os/owner-tools trees, packed from the source and indexed in the stand-in.
    listing = git(source, 'rev-list', '--objects', *trees.values())
    pack = git(source, 'pack-objects', '--stdout', data=b''.join(line.split(b' ')[0] + b'\n' for line in listing.splitlines()))
    git(repo, 'index-pack', '--stdin', data=pack)
    commits, parent = {}, None
    for commit in (V3_COMMIT, head):
        os_tree = git(repo, 'mktree', data=('040000 tree ' + trees[commit] + '\towner-tools\n').encode()).decode().strip()
        root = git(repo, 'mktree', data=('040000 tree ' + os_tree + '\tos\n').encode()).decode().strip()
        message = 'Stand-in for ' + commit + ': its os/owner-tools only'
        made = git(repo, 'commit-tree', root, *(['-p', parent] if parent else []), '-m', message, env=STANDIN_ENV).decode().strip()
        commits[commit], parent = made, made
    git(repo, 'update-ref', 'refs/heads/main', commits[head])
    git(repo, 'tag', 'version-3', commits[V3_COMMIT])
    bundle = destination / 'stand-in.bundle'
    git(repo, 'bundle', 'create', str(bundle.resolve()), 'main', 'version-3')
    for commit, made in commits.items():
        assert git(repo, 'rev-parse', made + ':os/owner-tools').decode().strip() == trees[commit], 'STOP: stand-in tree differs'
    fingerprint = hashlib.sha256(git(repo, 'show', commits[V3_COMMIT] + ':os/owner-tools/payload/SHA256SUMS')).hexdigest()
    assert fingerprint == TOOLS_V3, 'STOP: the stand-in does not hold version 3'
    return dict(bundle=bundle, commits=commits, trees=trees)




def next_version(destination, payload=pathlib.Path('os/owner-tools/payload')):
    """This payload with its tools version one higher and its manifests made again: a test bundle the
    installed version 4 accepts as newer from the stick, so the stick route runs version 4's own code (F13).
    Returns (tools version, fingerprint)."""
    destination = pathlib.Path(destination)
    shutil.copytree(payload, destination)
    history = json.loads((destination / 'history.json').read_text())
    history['tools_version'] += 1
    (destination / 'history.json').write_text(json.dumps(history, indent=2) + '\n')
    # The manifests as bundle.manifests writes them, over the same files in the same order.
    rows = [dict(sha256=hashlib.sha256((destination / row['path']).read_bytes()).hexdigest(), path=row['path'])
            for row in json.loads((payload / 'SHA256.json').read_text())]
    raw = (json.dumps(rows, indent=2) + '\n').encode()
    sums = (''.join(row['sha256'] + '  ' + row['path'] + '\n' for row in rows)
            + hashlib.sha256(raw).hexdigest() + '  SHA256.json\n').encode()
    (destination / 'SHA256.json').write_bytes(raw)
    (destination / 'SHA256SUMS').write_bytes(sums)
    return history['tools_version'], hashlib.sha256(sums).hexdigest()


# /proc readers shared by the caller (as ares) and the harness's dialog reader (as root).
PROC = r'''def rows():
    found={}
    for p in pathlib.Path('/proc').iterdir():
        if p.name.isdigit():
            try:
                fields=(p/'stat').read_text().rsplit(')',1)[1].split()
                found[int(p.name)]=dict(state=fields[0],parent=int(fields[1]),argv=(p/'cmdline').read_bytes().split(b'\0')[:-1])
            except (OSError,ValueError,IndexError): pass
    return found
def sudo_of(root,found):
    # The first sudo at or below the line's own process: the one this caller started.
    todo=[root]
    while todo:
        pid=todo.pop(0)
        if pid in found and found[pid]['argv'][:1]==[b'/usr/bin/sudo']: return pid
        todo+=[child for child,row in found.items() if row['parent']==pid]
    return None
def helpers_of(sudo,found):
    return [child for child,row in found.items() if row['parent']==sudo and row['argv'][:1]==[b'/usr/bin/ksshaskpass']]
KEYRINGS={b'kwalletd5',b'kwalletd6',b'ksecretd',b'gnome-keyring-daemon'}
def keyrings(found):
    return sorted([pid,row['argv'][0].rsplit(b'/',1)[-1].decode()] for pid,row in found.items()
                  if row['argv'] and row['argv'][0].rsplit(b'/',1)[-1] in KEYRINGS)
'''

# The stand-in for Claude's Bash tool: a process in his desktop session with no controlling terminal and
# stdin from /dev/null. It reads each routine line from the announced commit (R3, FROM_COMMIT), runs the
# folder line as ares, then the routine line, and writes what happened into its own folder. With
# `unanswered` it stops, after that many seconds, only the password helper whose parent is the sudo it
# started (R1), and records every PID it signalled.
CALLER = r'''import hashlib,json,os,pathlib,signal,subprocess,time
P=json.loads(@PARAMS@)
out=pathlib.Path(P['out'])
def save(name,value):
    temporary=out/(name+'.new'); temporary.write_text(json.dumps(value)); temporary.replace(out/(name+'.json'))
''' + PROC + r'''result=dict(uid=os.getuid(),loginuid=pathlib.Path('/proc/self/loginuid').read_text().strip(),stdin_terminal=os.isatty(0),
    wayland=bool(os.environ.get('WAYLAND_DISPLAY')),runtime=os.environ.get('XDG_RUNTIME_DIR'))
try:
    os.close(os.open('/dev/tty',os.O_RDWR)); result['terminal']=True
except OSError as error:
    result['terminal'],result['tty_errno']=False,error.errno
lines=dict(P['lines'])
if P['entries'] and not result['terminal']:
    entries=json.loads(subprocess.check_output(['git','-C',P['checkout'],'show',P['commit']+':os/owner-tools/commands.json']))
    lines.update({step:entries[name] for step,name in P['entries'].items()})
result['line_sha256']={step:hashlib.sha256(line.encode()).hexdigest() for step,line in lines.items()}
for step in ([] if result['terminal'] else P['steps']):
    if step=='folder':
        done=subprocess.run(['/usr/bin/bash','-c',lines['folder']+' '+P['commit']],stdin=subprocess.DEVNULL,capture_output=True,text=True)
        result['folder']=dict(status=done.returncode,stdout=done.stdout,stderr=done.stderr)
        if done.returncode: break
    elif step=='routine':
        with open(out/'routine.out','wb') as stdout, open(out/'routine.err','wb') as stderr:
            line=subprocess.Popen(['/usr/bin/bash','-c',lines['routine']],stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
            save('started',dict(pid=line.pid))
            seen,signalled,first=None,[],None
            while line.poll() is None:
                if P['unanswered'] and not signalled:
                    found=rows(); sudo=sudo_of(line.pid,found); helpers=helpers_of(sudo,found) if sudo else []
                    if len(helpers)==1 and first is None:
                        first,seen=time.monotonic(),helpers[0]
                    elif len(helpers)==1 and helpers[0]==seen and time.monotonic()-first>=P['unanswered']:
                        os.kill(seen,signal.SIGTERM); signalled.append(seen)
                time.sleep(.2)
        result['routine']=dict(status=line.returncode,stdout=(out/'routine.out').read_text(errors='replace'),
            stderr=(out/'routine.err').read_text(errors='replace'),signalled=signalled,helper=seen,
            helper_gone=seen is None or not pathlib.Path('/proc/'+str(seen)).exists())
        if line.returncode: break
    elif step=='no-ticket':
        done=subprocess.run(['/usr/bin/sudo','-n','true'],stdin=subprocess.DEVNULL,capture_output=True,text=True)
        result['no_ticket']=dict(status=done.returncode,stderr=done.stderr)
save('done',result)
'''

# The harness side, as root on the serial console: wait for the window of the sudo the caller started.
DIALOG = r'''import json,os,pathlib,time
out=pathlib.Path(@OUT@)
''' + PROC + r'''deadline=time.monotonic()+@SECONDS@
while time.monotonic()<deadline:
    if (out/'done.json').exists():
        print(json.dumps(dict(status='the caller ended before a window',done=json.loads((out/'done.json').read_text())))); break
    if (out/'started.json').exists():
        found=rows(); sudo=sudo_of(json.loads((out/'started.json').read_text())['pid'],found)
        helpers=helpers_of(sudo,found) if sudo else []
        if len(helpers)==1:
            helper,=helpers
            status=dict(l.split(':',1) for l in pathlib.Path('/proc/'+str(helper)+'/status').read_text().splitlines() if ':' in l)
            print(json.dumps(dict(status='window',sudo=sudo,helper=helper,parent=found[helper]['parent'],uid=int(status['Uid'].split()[0]),
                argv=[word.decode() for word in found[helper]['argv']],keyrings=keyrings(found)))); break
    time.sleep(.2)
else: print(json.dumps(dict(status='no window')))
'''

WAIT = r'''import json,pathlib,time
p=pathlib.Path(@PATH@)
deadline=time.monotonic()+@SECONDS@
while time.monotonic()<deadline:
    if p.exists():
        print(p.read_text()); break
    time.sleep(.5)
else: raise SystemExit('The caller did not finish')
'''

KEYRINGS = 'import json,pathlib\n' + PROC + 'print(json.dumps(keyrings(rows())))\n'

# What a refused or cancelled line must leave as it was: the installed tools (everything under
# /var/lib/ares but its records), the records' names, the bootstrap copies, the tools folder.
STATE = r'''import hashlib,json,os,pathlib,stat
def tree(root,skip=()):
    found={}
    for folder,dirs,files in os.walk(root):
        for name in sorted(dirs+files):
            path=os.path.join(folder,name); relative=os.path.relpath(path,root)
            if relative.split('/')[0] in skip: continue
            info=os.lstat(path)
            kind=('link:'+os.readlink(path) if stat.S_ISLNK(info.st_mode) else
                  hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest() if stat.S_ISREG(info.st_mode) else 'directory')
            found[relative]=[kind,stat.S_IMODE(info.st_mode),info.st_uid]
    return found
home=pathlib.Path('/var/lib/ares')
digest=lambda value: hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
journal=home/'tools-update-intent.json'
value=json.loads(journal.read_text()) if journal.exists() else None
print(json.dumps(dict(tools=digest(tree(home,('records','diagnostics'))),entry=os.readlink(home/'at'),
    toolsets=sorted(p.name for p in home.iterdir() if p.name.startswith('tools')),
    journal=None if value is None else {k:value.get(k) for k in ('phase','manifest','source','previous','tools_version')},
    records=sorted(p.parent.name+'/'+p.name for d in ('records','diagnostics') if (home/d).is_dir() for p in (home/d).iterdir()),
    bootstrap=sorted(str(p) for p in pathlib.Path('/run').glob('ares-bootstrap.*')),
    folder=digest(tree('/var/home/ares/ares-tools')) if os.path.isdir('/var/home/ares/ares-tools') else None)))
'''

# Cut: the tools update stopped once its journal says the copy is complete and before the entry moves
# to the new tools (owner.update_tools, phase "publish"), then one hard reset (as 22c's CUT_WATCH).
TOOLS_CUT = r'''import json,os,pathlib,signal,time
home=pathlib.Path('/var/lib/ares'); journal=home/'tools-update-intent.json'; out=pathlib.Path('/run/aresos-tools-cut.json')
MANIFEST=@MANIFEST@
def write(value):
    temporary=out.with_suffix('.new'); temporary.write_text(json.dumps(value)); temporary.replace(out)
def phase():
    try: value=json.loads(journal.read_text())
    except (OSError,ValueError): return None
    return value.get('phase') if value.get('manifest')==MANIFEST else None
''' + PROC + r'''def tools(found):
    return [pid for pid,row in found.items() if len(row['argv'])>=2 and row['argv'][-1]==b'install' and row['argv'][-2].endswith(b'/owner.py')]
def below(found,pid):
    seen,todo=[],[pid]
    while todo:
        parent=todo.pop()
        for child,row in found.items():
            if row['parent']==parent and child not in seen: seen.append(child); todo.append(child)
    return seen
entry=os.readlink(home/'at')
write(dict(status='watching',entry_before=entry))
deadline=time.monotonic()+900
pid,scanned,phases=None,0.0,[]
while True:
    now=phase()
    if now is not None and (not phases or phases[-1]!=now): phases.append(now)
    if now=='publish': break
    if now is not None and now!='copy':
        write(dict(status='missed the window',phases=phases)); raise SystemExit(1)
    if time.monotonic()>deadline:
        write(dict(status='no copy seen',phases=phases)); raise SystemExit(1)
    if pid is None and time.monotonic()-scanned>.05:
        scanned=time.monotonic(); found=tools(rows()); pid=found[0] if len(found)==1 else None
    time.sleep(.002)
if pid is None:
    found=tools(rows()); pid=found[0] if len(found)==1 else None
if pid is None:
    write(dict(status='copy seen without the tools process',phases=phases)); raise SystemExit(1)
os.kill(pid,signal.SIGSTOP)
while time.monotonic()<deadline:
    found=rows()
    if pid in found and found[pid]['state'] in 'Tt' and not [c for c in below(found,pid) if found[c]['state']!='Z']: break
    time.sleep(.05)
else:
    write(dict(status='the tools did not stop',pid=pid)); raise SystemExit(1)
write(dict(status='frozen',pid=pid,state=found[pid]['state'],phases=phases,phase_after=phase(),entry_before=entry,
    entry_after=os.readlink(home/'at'),toolsets=sorted(p.name for p in home.iterdir() if p.name.startswith('tools'))))
'''

# After export: ares reads /run/ares-records, another account cannot (review 2, "For step 6").
EXPORT_ACCESS = r'''import json,pathlib,subprocess
files=sorted(str(p) for p in pathlib.Path('/run/ares-records').glob('*.json'))
assert files, 'no exported records'
ares=[subprocess.run(['runuser','-u','ares','--','/usr/bin/cat','--',f],capture_output=True).returncode for f in files]
other=[subprocess.run(['runuser','-u','nobody','--','/usr/bin/cat','--',f],capture_output=True).returncode for f in files]
print(json.dumps(dict(files=len(files),ares_read=all(code==0 for code in ares),other_refused=all(code!=0 for code in other))))
'''


# git as ares from the root serial shell: his home, so root's configuration is never read.
AS_ARES = 'runuser -u ares -- env HOME=/var/home/ares '


def program(source, **values):
    for key, value in values.items():
        source = source.replace('@' + key.upper() + '@', repr(value))
    return source


class Walk:
    """The tools-local walk's stages in his desktop session, over package 22c's harness (vm: owner_vm)."""
    R1_SECONDS = 30  # The guide's 10 minutes, shortened: what is tested is who is signalled, not the wait.

    def __init__(self, vm, guest, ares_password, standin, head, head_tools):
        self.vm, self.guest, self.ares_password = vm, guest, ares_password
        self.standin, self.head_commit, self.head_tools = standin, head, head_tools
        self.bootstrap = vm.bundle_module('bootstrap')
        self.dialogs, self.stages = [], []
        self.keyrings = None

    def capture(self, name, source):
        return self.guest.capture_json(name, self.vm.sw.framed('python3 -c ' + shlex.quote(source)))

    def state(self, name):
        return self.capture(name + '-state', STATE)

    def setup(self, stage):
        """The stand-in origin and his checkout, as ares, with origin's main at version 3's stand-in."""
        guest, data = self.guest, base64.b64encode(self.standin['bundle'].read_bytes()).decode()
        guest.command(stage + '-bundle-begin', 'set -e; rm -f /run/aresos-standin.b64; : > /run/aresos-standin.b64')
        size = 48000
        for index in range(0, len(data), size):
            guest.command(stage + '-bundle-' + str(index // size), 'set -e; printf %s ' + data[index:index + size] + ' >> /run/aresos-standin.b64')
        digest = hashlib.sha256(self.standin['bundle'].read_bytes()).hexdigest()
        commits = self.standin['commits']
        guest.command(stage + '-origin', '\n'.join([
            'set -e', 'cd /var/home/ares', 'base64 -d /run/aresos-standin.b64 > /run/aresos-standin.bundle; rm /run/aresos-standin.b64',
            'test "$(sha256sum < /run/aresos-standin.bundle)" = ' + shlex.quote(digest + '  -'),
            'chmod 0644 /run/aresos-standin.bundle',
            AS_ARES + 'git clone --quiet --bare /run/aresos-standin.bundle ' + GUEST_ORIGIN,
            AS_ARES + 'git -C ' + GUEST_ORIGIN + ' update-ref refs/heads/main ' + commits[V3_COMMIT],
            AS_ARES + 'git clone --quiet ' + GUEST_ORIGIN + ' ' + self.bootstrap.CHECKOUT,
            'test "$(' + AS_ARES + 'git -C ' + self.bootstrap.CHECKOUT + ' rev-parse HEAD)" = ' + commits[V3_COMMIT],
            # The tree the guest's lines read is the real commit's (git names a tree by its content).
            'test "$(' + AS_ARES + 'git -C ' + self.bootstrap.CHECKOUT + ' rev-parse HEAD:os/owner-tools)" = '
            + self.standin['trees'][V3_COMMIT]]))
        self.keyrings = self.capture(stage + '-keyrings', KEYRINGS)

    def advance_origin(self, stage):
        """Claude's checkout follows main by a fast-forward pull only (the guide's rule N7)."""
        head = self.standin['commits'][self.head_commit]
        self.guest.command(stage + '-advance', '\n'.join([
            'set -e', 'cd /var/home/ares', AS_ARES + 'git -C ' + GUEST_ORIGIN + ' update-ref refs/heads/main ' + head,
            AS_ARES + 'git -C ' + self.bootstrap.CHECKOUT + ' pull --quiet --ff-only origin main',
            'test "$(' + AS_ARES + 'git -C ' + self.bootstrap.CHECKOUT + ' rev-parse HEAD)" = ' + head,
            'test "$(' + AS_ARES + 'git -C ' + self.bootstrap.CHECKOUT + ' rev-parse HEAD:os/owner-tools)" = '
            + self.standin['trees'][self.head_commit]]))

    def caller(self, stage, steps, commit, entries=None, lines=None, unanswered=0):
        """Write the caller for this stage, start it from foot in his session, and return its folder."""
        out = '/run/aresos-caller-' + stage
        params = dict(out=out, steps=list(steps), commit=commit, checkout=self.bootstrap.CHECKOUT,
                      entries=entries or {}, lines=lines or {}, unanswered=unanswered)
        script = program(CALLER, params=json.dumps(params))
        launcher = ('#!/bin/bash\nexec setsid -f /usr/bin/python3 ' + out + '.py < /dev/null > ' + out + '/log 2>&1\n')
        guest = self.guest
        guest.command(stage + '-caller-prepare', '\n'.join([
            'set -e', 'rm -rf ' + out + ' ' + out + '.py ' + out + '.sh', 'install -d -m 0700 -o ares -g ares ' + out,
            'printf %s ' + shlex.quote(base64.b64encode(script.encode()).decode()) + ' | base64 -d > ' + out + '.py',
            'printf %s ' + shlex.quote(base64.b64encode(launcher.encode()).decode()) + ' | base64 -d > ' + out + '.sh',
            'chmod 0644 ' + out + '.py ' + out + '.sh']))
        # Typed in foot like any command: the caller runs in his session, with its display and bus.
        guest.keys(['ctrl', 'alt', 'f1'])
        guest.command(stage + '-foot-ready', 'set -e; for n in {1..120}; do if test "$(cat /sys/class/tty/tty0/active)" = tty1 '
                      '&& pgrep -u ares -x foot; then exit 0; fi; sleep 1; done; exit 1')
        guest.command(stage + '-session', self.vm.ACTIVE_DESKTOP)
        time.sleep(1)
        self.vm.type_text(guest, 'bash ' + out + '.sh\n', 'de')
        return out

    def window(self, stage, out, fingerprint, action, answer):
        """The dialog: the helper of the caller's sudo, its label, no keyring; then the answer.

        answer: 'password', 'escape', or None (the caller closes it, R1)."""
        seen = self.capture(stage + '-dialog', program(DIALOG, out=out, seconds=180))
        td_save(self.vm, stage + '-dialog', seen)
        assert seen['status'] == 'window', 'STOP: no password window at ' + stage + ': ' + seen['status']
        label = self.bootstrap.label(fingerprint, action)
        assert seen['argv'] == [self.bootstrap.ASKPASS, label], 'STOP: the window does not show the label at ' + stage
        assert seen['parent'] == seen['sudo'] and seen['uid'] == 1001, 'STOP: the helper is not the sudo\'s, as ares'
        assert set(map(tuple, seen['keyrings'])) <= set(map(tuple, self.keyrings)), 'STOP: a keyring process started'
        # The 70-character label must show wrapped, not cut (review 2): the picture is the evidence.
        self.guest.screenshot(stage + '-window')
        if answer == 'password':
            self.vm.type_text(self.guest, self.ares_password + '\n', 'de')
        elif answer == 'escape':
            self.guest.keys(['esc'])
        self.dialogs.append(dict(stage=stage, label=label, label_length=len(label), helper=seen['helper'], sudo=seen['sudo'],
                                 screenshot=stage + '-window', answer=answer or 'none: closed by the caller'))
        return seen

    def result(self, stage, out, seconds=600):
        done = self.capture(stage + '-caller-result', program(WAIT, path=out + '/done.json', seconds=seconds))
        td_save(self.vm, stage + '-caller', done)
        assert done['uid'] == 1001 and done['loginuid'] == '1001', 'STOP: the caller is not ares in his session'
        assert done['terminal'] is False and done['stdin_terminal'] is False, 'STOP: the caller has a terminal'
        assert done['wayland'] and done['runtime'] == '/run/user/1001', 'STOP: the caller is not in his desktop session'
        after = self.capture(stage + '-keyrings-after', KEYRINGS)
        assert set(map(tuple, after)) <= set(map(tuple, self.keyrings)), 'STOP: a keyring process started at ' + stage
        return done

    def lines_are(self, done, expected):
        assert done['line_sha256'] == {step: hashlib.sha256(line.encode()).hexdigest() for step, line in expected.items()}, \
            'STOP: the caller did not run the expected lines'

    def record(self, stage, **facts):
        self.stages.append(dict(stage=stage, **facts))
        td_save(self.vm, stage + '-stage', self.stages[-1])


def td_save(vm, name, value):
    vm.td.save(name, value)


def rehearsal(vm, audit, media, password, hashed, ares_password, version_2):
    """The walk in the module docstring. vm: the running owner_vm module (it runs as __main__ in CI)."""
    td, Console, bootstrap = vm.td, vm.Console, vm.bundle_module('bootstrap')
    head = os.environ['GITHUB_SHA']
    head_tools = hashlib.sha256(vm.git_blob(head, 'os/owner-tools/payload/SHA256SUMS')).hexdigest()
    assert vm.COMMANDS['tools-routine'] == bootstrap.tools_routine(head_tools), 'STOP: commands.json is not this head\'s'
    version = json.loads(pathlib.Path('os/owner-tools/payload/history.json').read_text())['tools_version']
    route = vm.laptop_update(audit, media, password, hashed, bundle=(version_2, vm.TOOLS_V2))
    standin = standin_origin(td.WORK / 'stand-in', head)
    # The integrator's decision (2026-11-15): for each announced commit, the stand-in's hash, the real
    # commit's and the tree hash, and the stand-in's tree equal to the real one.
    announced = []
    for real in (V3_COMMIT, head):
        tree = git(standin['bundle'].parent / 'stand-in.git', 'rev-parse', standin['commits'][real] + ':os/owner-tools').decode().strip()
        assert tree == standin['trees'][real] == git('.', 'rev-parse', real + ':os/owner-tools').decode().strip(), \
            'STOP: a stand-in tree differs from the real commit\'s'
        announced.append(dict(standin=standin['commits'][real], real=real, tree=tree, trees_equal=True))
    stand_head, stand_v3 = standin['commits'][head], standin['commits'][V3_COMMIT]
    v3_lines = dict(folder=bootstrap.tools_folder(TOOLS_V3), routine=bootstrap.tools_routine(TOOLS_V3))
    head_lines = dict(folder=vm.COMMANDS['tools-folder'], routine=vm.COMMANDS['tools-routine'])
    routine_action, export_action = bootstrap.ACTIONS['tools-routine'], bootstrap.ACTIONS['export-routine']
    no_password = 'sudo: no password was provided'
    guest = td.start_installed(password, hashed, 'release-27')
    try:
        console, _ = vm.confirmed_update(guest, password, route)
        console.passwd(ares_password, 'release-27-ares-password')
        Console(guest, 'tty4').ares_sudo(ares_password, 'release-27-ares-sudo')
        walk = Walk(vm, guest, ares_password, standin, head, head_tools)
        walk.setup('tl-setup')
        start = walk.state('tl-start')
        assert start['journal'] is None or start['journal']['phase'] == 'complete', 'STOP: a tools update is open before the walk'

        # v3 refuses (N-e): this checkout's lines for version 3, the checkout at version 3's stand-in.
        out = walk.caller('tl-v3', ('folder', 'routine'), stand_v3, lines=v3_lines)
        walk.window('tl-v3', out, TOOLS_V3, routine_action, 'password')
        done = walk.result('tl-v3', out)
        walk.lines_are(done, v3_lines)
        after = walk.state('tl-v3')
        assert done['folder']['status'] == 0 and done['routine']['status'] != 0, 'STOP: version 3 did not refuse'
        assert 'STOP' in done['routine']['stdout'] + done['routine']['stderr'], 'STOP: version 3 refused without a STOP line'
        assert 'Tools update runs only from the physical recovery console' in done['routine']['stdout'] + done['routine']['stderr'], \
            'STOP: version 3 did not stop at its terminal test'
        assert (after['tools'], after['entry'], after['journal']) == (start['tools'], start['entry'], start['journal']), \
            'STOP: version 3 changed the installed tools'
        walk.record('tl-v3', lines='this checkout\'s, for version 3 (N-e)', commit=stand_v3, real_commit=V3_COMMIT,
                    tree=standin['trees'][V3_COMMIT], stop=done['routine']['stdout'].strip().splitlines()[-3:], nothing_changed=True)

        # Cancel: the routine line of the announced commit, from that commit's commands.json (R3).
        walk.advance_origin('tl-origin')
        entries = dict(folder='tools-folder', routine='tools-routine')
        before = walk.state('tl-cancel-before')
        out = walk.caller('tl-cancel', ('folder', 'routine'), stand_head, entries=entries)
        walk.window('tl-cancel', out, head_tools, routine_action, 'escape')
        done = walk.result('tl-cancel', out)
        walk.lines_are(done, head_lines)
        after = walk.state('tl-cancel')
        assert done['routine']['status'] == 1 and no_password in done['routine']['stderr'], 'STOP: Cancel did not end the line'
        assert {k: after[k] for k in ('tools', 'entry', 'journal', 'records')} == \
            {k: before[k] for k in ('tools', 'entry', 'journal', 'records')} and after['bootstrap'] == before['bootstrap'], \
            'STOP: Cancel changed something'
        walk.record('tl-cancel', status=1, stderr=no_password, nothing_changed=True)

        # R1: the window left unanswered; the caller stops only the helper.
        before = after
        out = walk.caller('tl-unanswered', ('folder', 'routine'), stand_head, entries=entries, unanswered=Walk.R1_SECONDS)
        seen = walk.window('tl-unanswered', out, head_tools, routine_action, None)
        done = walk.result('tl-unanswered', out)
        after = walk.state('tl-unanswered')
        routine = done['routine']
        assert routine['signalled'] == [seen['helper']] and routine['helper'] == seen['helper'], \
            'STOP: the caller signalled another process than the helper'
        assert routine['helper_gone'] and routine['status'] == 1 and no_password in routine['stderr'], \
            'STOP: the unanswered window did not end as after Cancel'
        assert {k: after[k] for k in ('tools', 'entry', 'journal', 'records', 'bootstrap')} == \
            {k: before[k] for k in ('tools', 'entry', 'journal', 'records', 'bootstrap')}, 'STOP: the closed window changed something'
        walk.record('tl-unanswered', wait_seconds=Walk.R1_SECONDS, signalled=routine['signalled'], helper=seen['helper'],
                    sudo=seen['sudo'], status=1, stderr=no_password, nothing_changed=True)

        # Cut: the line with the password, one hard reset between the copy and the publication.
        watcher = base64.b64encode(program(TOOLS_CUT, manifest=head_tools).encode()).decode()
        guest.command('tl-cut-watch', 'set -e; rm -f /run/aresos-tools-cut.json; printf %s ' + shlex.quote(watcher) +
                      ' | base64 -d > /run/aresos-tools-cut.py\npython3 /run/aresos-tools-cut.py > /run/aresos-tools-cut.log 2>&1 < /dev/null &')
        walk.capture('tl-cut-armed', vm.cut_wait("value['status']=='watching'", 30).replace('aresos-cut.json', 'aresos-tools-cut.json'))
        out = walk.caller('tl-cut', ('folder', 'routine'), stand_head, entries=entries)
        walk.window('tl-cut', out, head_tools, routine_action, 'password')
        frozen = walk.capture('tl-cut-frozen', vm.cut_wait("value['status']!='watching'", 600).replace('aresos-cut.json', 'aresos-tools-cut.json'))
        td.save('tl-cut-watcher', frozen)
        assert frozen['status'] == 'frozen' and frozen['state'] in ('T', 't'), 'STOP: the tools update was not stopped: ' + frozen['status']
        assert frozen['phase_after'] == 'publish' and frozen['entry_after'] == frozen['entry_before'] == start['entry'] \
            and 'tools-' + head_tools in frozen['toolsets'], 'STOP: the cut is not between the copy and the publication; repeat it'
        walk.record('tl-cut', watcher=frozen, reset='QMP system_reset')
        guest.hard_reset('tl-cut')
    finally:
        vm.finish(guest, audit, 'release-27')

    guest = td.start_installed(password, hashed, 'cut-27')
    try:
        vm.keyboard(guest, 'cut-27', 'de')
        console = Console(guest)
        console.login(password, 'cut-27')
        console.become_root(password, 'cut-27')
        walk.guest = guest
        # Keyring processes are compared within one start: a new start has new PIDs.
        walk.keyrings = walk.capture('tl-boot-keyrings', KEYRINGS)
        # The old tools after the cut: their check passes, and the journal still names the new tools.
        console.run('check', 'cut-27-old-check')
        cut = walk.state('tl-after-cut')
        assert cut['entry'] == start['entry'] and cut['journal'] and cut['journal']['manifest'] == head_tools \
            and cut['journal']['source'] == 'folder', 'STOP: the cut update is not open after the restart'

        # Install: the same line resumes it. PASS install, check and title from one window.
        records = walk.capture('tl-install-records', vm.diagnostic_reader())
        out = walk.caller('tl-install', ('folder', 'routine', 'no-ticket'), stand_head, entries=entries)
        walk.window('tl-install', out, head_tools, routine_action, 'password')
        done = walk.result('tl-install', out)
        walk.lines_are(done, head_lines)
        passes = [line for line in done['routine']['stdout'].splitlines() if line.startswith('PASS ')]
        assert done['routine']['status'] == 0 and passes == ['PASS install', 'PASS check', 'PASS title'], \
            'STOP: the routine did not pass install, check and title in one window'
        assert done['no_ticket']['status'] != 0, 'STOP: sudo kept a ticket after the window'
        receipt = walk.capture('tl-install-receipt', vm.diagnostic_reader(records, 'tools-update'))
        td.save('tl-install-receipt', receipt)
        assert (receipt['status'], receipt['manifest'], receipt['previous_manifest']) == ('passed', head_tools, vm.TOOLS_V2)
        assert (receipt['previous_version'], receipt['tools_version']) == (2, version)
        assert (receipt['source'], receipt['finished_from']) == ('folder', 'folder'), 'STOP: the receipt does not name the folder'
        assert receipt['caller'] == dict(login_uid=1001, terminal=False), 'STOP: the receipt does not name uid 1001 without a terminal'
        installed = walk.state('tl-install')
        assert installed['entry'] == 'tools-' + head_tools + '/at' and installed['journal'] in (None, dict(
            installed['journal'] or {}, phase='complete')), 'STOP: the tools update did not complete'
        walk.record('tl-install', resumed_phase=cut['journal']['phase'], passes=passes, receipt=dict(source=receipt['source'],
                    caller=receipt['caller'], manifest=head_tools), sudo_n_true=done['no_ticket'])

        # Tamper: one byte of the folder; the line STOPs before any bundle code.
        guest.command('tl-tamper', 'set -e; python3 -c ' + shlex.quote(
            "import pathlib\np=pathlib.Path('/var/home/ares/ares-tools/owner.py'); b=bytearray(p.read_bytes()); b[100]^=1; p.write_bytes(b)"))
        out = walk.caller('tl-tamper', ('routine',), stand_head, entries=dict(routine='tools-routine'))
        walk.window('tl-tamper', out, head_tools, routine_action, 'password')
        done = walk.result('tl-tamper', out)
        after = walk.state('tl-tamper')
        assert done['routine']['status'] != 0 and 'STOP bootstrap: verification or install refused' in done['routine']['stdout'], \
            'STOP: the tampered folder was not refused'
        assert not [line for line in done['routine']['stdout'].splitlines() if line.startswith('PASS ')]
        assert {k: after[k] for k in ('tools', 'entry', 'journal', 'records')} == \
            {k: installed[k] for k in ('tools', 'entry', 'journal', 'records')}, 'STOP: the tampered folder changed the tools'
        walk.record('tl-tamper', stop='STOP bootstrap: verification or install refused', nothing_changed=True)

        # The stick with a next version at tty3: version 4's own stick route (F13).
        next_number, next_tools = next_version(td.WORK / 'tools-next')
        media.replace('tools-next', source=td.WORK / 'tools-next')
        replaced = time.strftime('%Y%m%d-%H%M', time.gmtime())
        assert media.fingerprint == next_tools and next_number == version + 1
        media.attach(guest, 'tools-next')
        console.commands = dict(vm.COMMANDS, install=bootstrap.command(next_tools))
        stick = console.run('install', 'tools-next-install', record='tools-update')
        assert (stick['manifest'], stick['previous_manifest']) == (next_tools, head_tools)
        assert (stick['previous_version'], stick['tools_version'], stick['source']) == (version, next_number, 'stick')
        media.detach(guest, 'tools-next')
        console.commands = vm.COMMANDS
        console.run('check', 'tools-next-check')
        walk.record('tl-stick-next', tools_version=next_number, fingerprint=next_tools, source='stick', console='tty3')

        # Export to the folder: the window, then /run/ares-records for ares and nobody else.
        out = walk.caller('tl-export', ('routine',), stand_head, entries=dict(routine='export-routine'))
        walk.window('tl-export', out, head_tools, export_action, 'password')
        done = walk.result('tl-export', out)
        walk.lines_are(done, dict(routine=vm.COMMANDS['export-routine']))
        assert done['routine']['status'] == 0 and 'PASS export' in done['routine']['stdout'].splitlines(), 'STOP: export failed'
        access = walk.capture('tl-export-access', EXPORT_ACCESS)
        assert access['ares_read'] and access['other_refused'], 'STOP: /run/ares-records is not for ares alone'
        walk.record('tl-export', access=access)

        # Export to a stick that still holds version 2: taken, with the retired bundle's line.
        # media.replace keeps the old bundle under a name by the minute: never twice in one minute.
        if time.strftime('%Y%m%d-%H%M', time.gmtime()) == replaced:
            time.sleep(61 - time.gmtime().tm_sec)
        media.replace('export-version-2', source=version_2)
        assert media.fingerprint == vm.TOOLS_V2
        media.attach(guest, 'export-version-2')
        exported = console.run('export', 'export-version-2-stick')
        stale = 'The stick holds tools this laptop installed before (SHA256 ' + vm.TOOLS_V2 + '), not the installed ones'
        assert stale in vm.result_lines(exported), 'STOP: the version 2 stick was not taken with its line'
        media.detach(guest, 'export-version-2')
        walk.record('tl-export-stick', line=stale)
        console.run('reboot', 'cut-27-reboot')
    finally:
        vm.finish(guest, audit, 'cut-27')

    # End: restart, check, title; the protected disks as before.
    guest = td.start_installed(password, hashed, 'final-27')
    try:
        vm.keyboard(guest, 'final-27', 'de')
        console = Console(guest)
        console.login(password, 'final-27')
        console.become_root(password, 'final-27')
        console.run('check', 'final-27-check')
        console.run('title', 'final-27-title')
        console.logout('final-27-logout')
    finally:
        vm.finish(guest, audit, 'final-27')
    td.marker(audit, 'final-unattended-windows')
    td.marker(audit, 'final-detached-windows', detached=True)
    result = dict(status='passed', commit=os.environ['GITHUB_SHA'], order='protected-second',
        starting_state="package 27's route: corrected pinned stock, release 13 by the laptop tools (15f), release 27 by tools version 2",
        tools_version_2=vm.TOOLS_V2, tools_version_3=TOOLS_V3, tools=head_tools, tools_version=version,
        next_version=dict(tools_version=next_number, fingerprint=next_tools),
        announced=announced, dialogs=walk.dialogs, stages=walk.stages, caller_terminal=False,
        keyrings_started=False, closed_stdin_stage=False, protected_disk_audits=True)
    td.save('tools-local-rehearsal-result', result)
