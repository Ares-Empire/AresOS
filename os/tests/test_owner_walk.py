"""Zero-cost host walk. Real driver/control flow, synthetic command responses.

Retained 13f deployment/BLS states are observations, not evidence that package
14 ran in a VM. Every guest command is captured, never executed here.
"""
import contextlib
import base64
import copy
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import shlex
import string
import subprocess
import sys
import tarfile
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import owner_vm as vm
import owner_media
import test_owner_tools as common
from owner_fuse_shim import Volume
from guest_shell import syntax
from owner_console_shim import execute_idle, execute_hidden, execute_screen, InstalledTools, model_clock
from test_owner_hidden import vcsa

FIXTURES = ROOT / 'os/tests/fixtures/owner-tools'
R27_RECORD = ROOT / 'os/manifest/releases/27.json'


def retained(name):
    return json.loads((FIXTURES / (name + '-deployments.json')).read_text())


UPDATE_STAGES = ['stock', 'tools-stock', 'corrected-stock', 'release-13', 'release-27', 'previous-13']
# Package 22c's probe: package 27's route up to release 27 confirmed, the six orders, one menu choice.
PROBE_STAGES = UPDATE_STAGES[:5] + [f'walk-{n}-booted' for n in range(1, 7)] + ['menu-stock', 'after-menu-booted']
# Package 22c's rehearsal (brief E): package 27's route up to release 27 confirmed, tools version 3,
# the layout trials, then every way between the three systems (two rows from the boot menu, one cut).
WAYS_BACK_STAGES = UPDATE_STAGES[:5] + ['intl-27', 'trial-27', 'abandon-27', 'back-13', 'forward-27', 'stock-1', 'forward-27b',
                                        'back-13b', 'forward-27c', 'menu-27', 'forward-27d', 'menu-stock', 'stock-2',
                                        'forward-27e', 'cut-stock', 'final-27']
# Package 22d's rehearsal (os/ci/tools_local.py): package 27's route up to release 27 confirmed, the
# dialog stages up to the cut, the restart after it (install, tamper, the next version, exports), the end.
TOOLS_LOCAL_STAGES = UPDATE_STAGES[:5] + ['cut-27', 'final-27']
# Package 42's rehearsal (os/ci/release28_walk.py): package 27's route up to release 27 confirmed, tools version 4
# and then 5 from the window, the update to release 28, previous to release 27, forward to release 28.
RELEASE28_STAGES = UPDATE_STAGES[:5] + ['release-28', 'previous-27', 'final-28']
QUALIFICATION_STAGES = ['stock','tools-stock','corrected-stock','layout-reset-trial','layout-reset-recovery','aresos','aresos-intl','aresos-back-de','rollback-stock','default-stock']


def laptop_rows(pair, reference=None):
    """The laptop's three deployments (newer AresOS, older AresOS, stock), built from the retained
    release 13 pair, and the builder of rpm-ostree's and bootc's status for a list of them."""
    old = next(d for d in pair['rpm']['deployments'] if d['booted'])
    stock = next(d for d in pair['rpm']['deployments'] if d['pinned'])
    reference = reference or json.loads(R27_RECORD.read_text())['reference']
    new = copy.deepcopy(old)
    new.update(checksum='c2' * 32, serial=0, **{'container-image-reference': 'ostree-unverified-registry:' + reference,
                                               'container-image-reference-digest': reference.split('@')[1]})
    def slot(row):
        return dict(ostree=dict(checksum=row['checksum'], deploySerial=row['serial'], stateroot=row['osname']),
            pinned=row['pinned'], image=dict(image=dict(image=row['container-image-reference'].split(':', 1)[1],
            transport='registry'), imageDigest=row['container-image-reference-digest']))
    def machine(*rows):
        rows = [copy.deepcopy(r) for r in rows]
        booted = next(i for i, r in enumerate(rows) if r['booted'])
        staged = [r for r in rows if r.get('staged')]
        others = [i for i, r in enumerate(rows) if not r.get('staged') and i != booted]
        bootc = copy.deepcopy(pair['bootc'])
        bootc['status'].update(booted=slot(rows[booted]), staged=slot(staged[0]) if staged else None,
            rollback=slot(rows[others[0]]), rollbackQueued=others[0] < booted)
        return dict(rpm=dict(copy.deepcopy(pair['rpm']), deployments=rows), bootc=bootc, bls=[])
    return new, old, stock, machine


def update_states(pair, reference=None):
    """Package 22's three-deployment shapes."""
    new, old, stock, machine = laptop_rows(pair, reference)
    up = lambda row, **kw: dict(copy.deepcopy(row), **kw)
    return {'owner-update-staged': machine(up(new, booted=False, staged=True), up(old, booted=True), stock),
            'release-27': machine(up(new, booted=True), up(old, booted=False), stock),
            'owner-previous-queued': machine(up(old, booted=False), up(new, booted=True), stock),
            'previous-13': machine(up(old, booted=True), up(new, booted=False), stock)}


class LaptopDisk:
    """The probe route's modelled disk: three deployments, the boot entries and the boot menu.

    Written from what the brief expects of ostree 2026.4 and bootc 1.16.13 (set-default removes the
    row and inserts it first; the rollback slot is the first other row, queued when it comes before
    the running one; the first row starts; entry files count down from the first row), and then held
    to the VM probe's captures (run 43470161858; test_ways_back_probe.CapturesTest): the three rows
    share one boot checksum, so a reorder swaps only the links under /ostree/boot.0 ("bootconfig
    swap: no"), the entry files stay, and the kernel's `ostree=` link, named by the place the running
    row had at its start, resolves to whichever row holds that place now.
    """
    ENTRY = ('title Bazzite (ostree:{place})\nversion {number}\noptions ostree=/ostree/boot.0/default/{boot}/{place} '
             'console=tty0 console=ttyS0,115200n8 root=UUID=00000000-0000-4000-8000-000000000000 rootflags=subvol=root rw\n'
             'linux /ostree/default-{boot}/vmlinuz\ninitrd /ostree/default-{boot}/initramfs.img\n')

    def __init__(self, pair):
        new, old, stock, self.machine = laptop_rows(pair)
        self.rows = dict(R27=new, R13=old, S=stock)
        self.order, self.running, self.boot_number = ['R27', 'R13', 'S'], 'R27', 1
        self.journal, self.grubenv, self.cursor, self.sets = [], {}, None, []
        self.on_restart = []  # told which row starts (the rehearsal's modelled tools follow the disk)
        self.started_at, self.links = 0, 1  # the running row's place at its start; /ostree/boot.0 -> boot.0.<links>

    def path(self, role):
        row = self.rows[role]
        return f"/sysroot/ostree/deploy/{row['osname']}/deploy/{row['checksum']}.{row['serial']}"

    def entries(self):
        count = len(self.order)
        return [dict(file=f'/boot/loader/entries/ostree-{count - place}.conf', deployment=self.path(role),
                     content=self.ENTRY.format(place=place, number=count - place, boot='b' * 64))
                for place, role in enumerate(self.order)]

    def snapshot(self):
        state = self.machine(*[dict(copy.deepcopy(self.rows[role]), booted=role == self.running, staged=False)
                               for role in self.order])
        state['bls'] = self.entries()
        # bootc 1.16.13: the order reads "rollback" whenever the running row is not first.
        state['bootc']['spec']['bootOrder'] = 'default' if self.order[0] == self.running else 'rollback'
        return state

    def inventory(self):
        """two_disk_vm.bls_inventory_command's export."""
        return [dict(id=pathlib.PurePosixPath(e['file']).stem, title=e['content'].split('\n')[0].removeprefix('title '),
                     deployment=e['deployment'], content=e['content']) for e in self.entries()]

    def layout(self):
        link = f"/ostree/boot.0/default/{'b' * 64}/{self.started_at}"
        return dict(boot_id=f'boot-{self.boot_number}', cmdline='ostree=' + link + ' rw', running_link=link,
                    running=self.path(self.order[self.started_at]), loader_link='loader.0',
                    loader_directories={'loader': [], 'loader.0': []}, ostree_boot_links={'boot.0': f'boot.0.{self.links}'},
                    ostree_boot_targets={}, grubenv=dict(argv=[], returncode=0, stdout='', stderr=''),
                    origins={f"{row['checksum']}.{row['serial']}.origin": '[origin]\ncontainer-image-reference=' + row['container-image-reference']
                             + ('\n\n[libostree-transient]\npinned=true\n' if row['pinned'] else '\n') for row in self.rows.values()},
                    admin_status=dict(argv=[], returncode=0, stdout='', stderr=''),
                    packages=dict(argv=[], returncode=0, stdout='', stderr=''))

    def set_default(self, index):
        assert 0 < index < len(self.order)
        self.order.insert(0, self.order.pop(index))
        return self.wrote(index)

    def wrote(self, index):
        """ostree's report of a list write, printed and logged."""
        self.sets.append(index)
        self.links = 1 - self.links
        message = f'Transaction complete; bootconfig swap: no; bootversion: boot.0.{self.links}, deployment count change: 0'
        self.journal.append(dict(MESSAGE=message, SYSLOG_IDENTIFIER='ostree', _COMM='ostree'))
        return dict(argv=['ostree', 'admin', 'set-default', str(index)], returncode=0, stdout=message + '\n', stderr='')

    def screen(self):
        """What the screen reads while the menu waits: its rows, top to bottom (nothing unless it is shown)."""
        if 'menu_show_once' not in self.grubenv:
            return ''
        return 'GNU GRUB version 2.12\n' + ''.join(' ' + e['title'] + '\n' for e in self.inventory()) + 'Use the arrow keys\n'

    def key(self, keys):
        if keys == ['home']: self.cursor = 0
        elif keys == ['down']: self.cursor += 1
        elif keys == ['ret']:
            self.restart(self.cursor)
            return True
        return False

    def restart(self, choice=None):
        once = self.grubenv.pop('next_entry', None)
        self.grubenv.pop('menu_show_once', None)
        ids = [pathlib.PurePosixPath(e['file']).stem for e in self.entries()]
        place = choice if choice is not None else ids.index(once) if once else 0
        self.running, self.boot_number, self.journal, self.cursor = self.order[place], self.boot_number + 1, [], None
        self.started_at = place
        for told in self.on_restart:
            told(place)


class Oracle:
    """The rehearsal route's answers: the owner tools themselves (this checkout's owner.py, version 3)
    over test_ways_back's modelled machine, holding the disk's three deployments. Every way-back
    command the walk types is run here, so the lines the harness requires are the lines the tools
    print for that state, and a restart the tools would refuse fails the walk. The disk follows the
    machine. check is title with check's own lines around it (its keyboard reads are not modelled);
    the layout commands and export stay synthetic."""
    WORDS = ('check', 'title', 'forward', 'previous', 'rollback', 'keep-stock', 'update')

    def __init__(self, stack, disk, old_reference, new_reference):
        import test_ways_back as model
        base = model.base
        rows = [dict(copy.deepcopy(disk.rows[role]), booted=role == disk.running, staged=False) for role in disk.order]
        known = [base.record(old_reference, False), base.record(new_reference, True)]
        self.model, self.disk, self.active = model, disk, False
        self.tools, self.host, self.store = stack.enter_context(model.laptop(base.machine(rows), known))
        self.roles = {(row['checksum'], row['serial']): role for role, row in disk.rows.items()}
        disk.on_restart.append(lambda place: model.restart(self.tools, self.host, choice=place))

    def synced(self):
        rows = self.host.state['rpm']['deployments']
        assert not any(row.get('staged') for row in rows), 'The rehearsal route staged a deployment'
        order = [self.roles[row['checksum'], row['serial']] for row in rows]
        if order != self.disk.order:
            assert order[1:] == [role for role in self.disk.order if role != order[0]]
            self.disk.set_default(self.disk.order.index(order[0]))
        running, = [self.roles[row['checksum'], row['serial']] for row in rows if row['booted']]
        assert (self.disk.order, self.disk.running) == (order, running), 'The modelled tools and the disk disagree'

    def command(self, name):
        tools, offset = self.tools, len(self.host.trace)
        tools.notes = []
        call = {'check': tools.title, 'title': tools.title, 'forward': tools.forward, 'previous': tools.previous,
                'rollback': tools.recover, 'keep-stock': lambda: tools.recover(True), 'update': tools.update}[name]
        try:
            lines = call()
        except self.model.owner.Stop as stop:
            self.synced()
            return dict(status='stopped', trace=self.host.trace[offset:], error=str(stop))
        if name == 'check':
            lines = ['System console de; X11 de variant ', 'Loaded y/z map, cmdline and all retained BLS maps passed', *lines,
                     'Also prove yz-/!ü by physical typing in the console and labwc terminal']
        self.synced()
        return dict(status='passed', trace=self.host.trace[offset:], result=[*tools.notes, *lines])

    def reboot(self):
        """The tools' own reboot checks (a stale title refuses) on the modelled machine."""
        self.tools.notes = []
        self.tools.reboot()

    def cut(self):
        """rollback, ended after its reorder and before its record (test_ways_back's cut point `after`)."""
        self.tools.notes = []
        self.host.interrupt = ('start-next', 'after')
        try:
            self.tools.recover()
        except self.model.owner.Stop:
            self.synced()
            return self.model.journal(self.store)
        raise AssertionError('The modelled rollback was not cut')


class ToolsLocal:
    """Package 22d's guest as the walk models it: the caller each stage writes (its parameters read back from
    the program the harness sends), the window of the sudo it starts, the keys and the password the harness
    gives that window, and what the line then does to the installed tools. Nothing here comes from what the
    harness expects: the label is read from the line the caller would run, the outcome from the answer the
    walk saw typed or pressed, so a harness that answers the wrong window or reads the wrong line fails.
    A caller starts only once its launcher line reached foot (`lost` drops a stage's first lines), and its
    window shows on the screenshots only once it is open (`hidden` keeps a stage's window off the screen)."""
    LOCAL = ('-keyrings', '-keyrings-after', '-state', '-dialog', '-caller-result', '-launched', '-launched-retry',
             'tl-cut-armed', 'tl-cut-frozen', 'tl-install-records', 'tl-install-receipt', 'tl-export-access',
             'tools-next-install-owner-result', 'export-version-2-stick-owner-result')

    def __init__(self, typed, media, ares_password, source=ROOT):
        self.typed, self.media, self.ares_password = typed, media, ares_password
        self.commands = json.loads((source / 'os/owner-tools/commands.json').read_text())
        self.head = hashlib.sha256((source / 'os/owner-tools/payload/SHA256SUMS').read_bytes()).hexdigest()
        self.version = json.loads((source / 'os/owner-tools/payload/history.json').read_text())['tools_version']
        self.callers, self.windows, self.escaped, self.tampered = {}, {}, False, False
        self.signalled = []
        self.prepared, self.lost, self.hidden, self.shots = {}, {}, set(), []
        self.machine = dict(tools=vm.TOOLS_V2, entry='tools-' + vm.TOOLS_V2 + '/at', journal=None, records=[], bootstrap=[], folder=None)

    def next_tools(self):
        import tools_local
        return hashlib.sha256((vm.td.WORK / 'tools-next' / 'SHA256SUMS').read_bytes()).hexdigest()

    def command(self, name, source):
        if name.endswith('-caller-prepare'):
            stage = name.removesuffix('-caller-prepare')
            encoded = re.findall(r"printf %s '?([A-Za-z0-9+/=]+)'? \| base64 -d > /run/aresos-caller-[a-z0-9-]+\.py", source)
            program = base64.b64decode(encoded[0]).decode()
            params, = re.findall(r'^P=json.loads\((.*)\)$', program, re.M)
            self.callers[stage] = json.loads(ast_literal(params))
            self.prepared[stage] = len(self.typed)
        if name == 'tl-tamper':
            self.tampered = True

    def answers(self, name):
        return name in self.LOCAL or name.endswith(self.LOCAL)

    def started(self, stage):
        """Whether the stage's launcher ran: typed in foot more often than its lines were lost."""
        line = 'bash /run/aresos-caller-' + stage + '.sh\n'
        return sum(text == line for text, _ in self.typed[self.prepared[stage]:]) > self.lost.get(stage, 0)

    def screenshot(self, name):
        """foot's screen (its typed lines at the top) and, on a stage's window picture, its open dialog."""
        from PIL import Image, ImageDraw
        picture = Image.new('RGB', (320, 200), (36, 36, 36))
        draw = ImageDraw.Draw(picture)
        draw.rectangle((4, 4, 4 + (7 * len(self.typed)) % 300, 12), fill=(220, 220, 204))
        stage = name.removesuffix('-window')
        if name.endswith('-window') and stage in self.windows and stage not in self.hidden:
            draw.rectangle((100, 60, 220, 140), fill=(239, 240, 241))
        picture.save(vm.sw.EVIDENCE / (name + '.png'))
        self.shots.append(name)

    def lines(self, stage):
        params = self.callers[stage]
        return dict(params['lines'], **{step: self.commands[entry] for step, entry in params['entries'].items()})

    def answer(self, guest, name):
        machine = self.machine
        if name.endswith(('-keyrings', '-keyrings-after')):
            return []
        if name.endswith('-state'):
            return dict(copy.deepcopy(machine), toolsets=sorted({machine['entry'].split('/')[0]} | (
                {'tools-' + machine['journal']['manifest']} if machine['journal'] else set())))
        if name.endswith(('-launched', '-launched-retry')):
            return dict(found=self.started(name.removesuffix('-retry').removesuffix('-launched')))
        if name.endswith('-dialog'):
            stage = name.removesuffix('-dialog')
            if not self.started(stage):
                return dict(status='no window')
            words = shlex.split(self.lines(stage)['routine'])
            pid = 900 + 10 * len(self.windows)
            self.windows[stage] = dict(helper=pid + 1, sudo=pid, typed=len(self.typed))
            self.escaped = False
            return dict(status='window', sudo=pid, helper=pid + 1, parent=pid, uid=1001,
                        argv=['/usr/bin/ksshaskpass', words[words.index('-p') + 1]], keyrings=[],
                        settled=True, gone=False, settle_seconds=3.2)
        if name.endswith('-caller-result'):
            return self.run(name.removesuffix('-caller-result'))
        if name == 'tl-cut-armed':
            return dict(status='watching', entry_before=machine['entry'])
        if name == 'tl-cut-frozen':
            # The tools stopped with the copy complete and the entry still on the old tools.
            machine['journal'] = dict(phase='publish', manifest=self.head, source='folder', previous=vm.TOOLS_V2,
                                      tools_version=self.version)
            return dict(status='frozen', pid=4243, state='T', phases=['copy', 'publish'], phase_after='publish',
                        entry_before=machine['entry'], entry_after=machine['entry'],
                        toolsets=sorted([machine['entry'].split('/')[0], 'tools-' + self.head]))
        if name == 'tl-install-records':
            return list(machine['records'])
        if name == 'tl-install-receipt':
            receipt = machine['records'][-1]
            assert receipt.endswith('-tools-update.json')
            return dict(status='passed', command=['install'], manifest=self.head, previous_manifest=vm.TOOLS_V2,
                        previous_version=2, tools_version=self.version, source='folder', finished_from='folder',
                        caller=dict(login_uid=1001, terminal=False), trace=[])
        if name == 'tl-export-access':
            return dict(files=3, ares_read=True, other_refused=True)
        if name == 'tools-next-install-owner-result':
            assert machine['tools'] == self.head and self.media.fingerprint == self.next_tools()
            machine['tools'] = self.media.fingerprint
            return dict(status='passed', trace=[], manifest=self.media.fingerprint, previous_manifest=self.head,
                        previous_version=self.version, tools_version=self.version + 1, source='stick')
        if name == 'export-version-2-stick-owner-result':
            stale = ([] if self.media.fingerprint == machine['tools'] else
                     ['The stick holds tools this laptop installed before (SHA256 ' + self.media.fingerprint + '), not the installed ones'])
            return dict(status='passed', trace=[], result=['Records copied with SHA256 readback', *stale,
                                                           'SAFE TO REMOVE ARESTOOLS; unplug before every shutdown/restart'])
        raise AssertionError('Unwalked tools-local response: ' + name)

    def run(self, stage):
        """The caller's result: its lines, then what the line does with the answer the window got."""
        params, lines, machine = self.callers[stage], self.lines(stage), self.machine
        done = dict(uid=1001, loginuid='1001', stdin_terminal=False, terminal=False, tty_errno=6, wayland=True,
                    runtime='/run/user/1001', line_sha256={step: hashlib.sha256(line.encode()).hexdigest() for step, line in lines.items()})
        if 'folder' in params['steps']:
            done['folder'] = dict(status=0, stdout='', stderr='')
            machine['folder'] = params['commit']
        window = self.windows[stage]
        answered = any(text == self.ares_password + '\n' for text, _ in self.typed[window['typed']:])
        routine = dict(signalled=[], helper=window['helper'], helper_gone=True)
        words = shlex.split(lines['routine'])
        label = words[words.index('-p') + 1]
        if self.escaped or not answered:
            assert self.escaped or params['unanswered'], 'A window nobody answers and no caller closes'
            if not self.escaped:
                routine['signalled'] = [window['helper']]
                self.signalled.append(window['helper'])
            routine.update(status=1, stdout='', stderr='sudo: no password was provided\n')
        elif ': export the records' in label:
            routine.update(status=0, stdout='Records exported\nPASS export\n', stderr='')
        else:
            machine['bootstrap'].append('/run/ares-bootstrap.' + str(len(machine['bootstrap'])))
            refusal = 'STOP bootstrap: verification or install refused\n'
            if label.startswith('AresOS owner tools ' + tools_local_v3()[:8]):
                routine.update(status=1, stderr='', stdout='STOP: Tools update runs only from the physical recovery console\n' + refusal)
            elif self.tampered:
                routine.update(status=1, stderr='sha256sum: WARNING: 1 computed checksum did NOT match\n', stdout=refusal)
            else:
                assert machine['journal'] and machine['journal']['phase'] == 'publish', 'The walk installs only after the cut'
                machine.update(tools=self.head, entry='tools-' + self.head + '/at', journal=dict(machine['journal'], phase='complete'))
                machine['records'].append('records/20261115T120000.000000Z-tools-update.json')
                routine.update(status=0, stderr='', stdout='Tools updated\nPASS install\nPASS check\nPASS title\n')
        done['routine'] = routine
        if 'no-ticket' in params['steps'] and routine['status'] == 0:
            done['no_ticket'] = dict(status=1, stderr='sudo: a password is required\n')
        return done


def release28_states(pair, r27, r28):
    """Package 42's shapes: release 28 staged over the laptop's three, then release 28 beside release 27 and stock
    (release 13 went at the update's shutdown), in the order each start and each queued change leaves."""
    new, old, stock, machine = laptop_rows(pair, r27)
    up = lambda row, **kw: dict(copy.deepcopy(row), **kw)
    next_ = up(new, checksum='c8' * 32, **{'container-image-reference': 'ostree-unverified-registry:' + r28,
                                           'container-image-reference-digest': r28.split('@')[1]})
    return {'r28-update-staged': machine(up(next_, booted=False, staged=True), up(new, booted=True), up(old, booted=False), stock),
            'release-28': machine(up(next_, booted=True), up(new, booted=False), stock),
            'r28-previous-queued': machine(up(new, booted=False), up(next_, booted=True), stock),
            'previous-27': machine(up(new, booted=True), up(next_, booted=False), stock),
            'r28-forward-queued': machine(up(next_, booted=False), up(new, booted=True), stock),
            'final-28': machine(up(next_, booted=True), up(new, booted=False), stock)}


def release28_record():
    """A stand-in for release 28's record (step 5 writes the real one): release 27's, with another digest and
    package 42's signature identity."""
    import release28_walk
    actual = ROOT / release28_walk.RECORD
    if actual.is_file(): return actual.read_bytes()
    record = json.loads((ROOT / 'os/manifest/releases/27.json').read_text())
    record.update(reference='ghcr.io/ares-empire/aresos@sha256:' + '28' * 32, tag='28-' + 'b' * 40, source_commit='b' * 40)
    record['signature'] = dict(record['signature'], identity=release28_walk.IDENTITY)
    return (json.dumps(record, indent=2) + '\n').encode()


class Release28Local(ToolsLocal):
    """Package 42's guest in its dialogs: each caller's lines read from the stand-in commit it names (as the
    caller reads them in the VM), and what the routine line does with the installed tools by the tools' own rule:
    a bundle installs only over a lower tools version (owner.update_tools), else it STOPs and nothing changes."""
    LOCAL = ToolsLocal.LOCAL + ('r28-v4-records', 'r28-tools-receipt')

    def __init__(self, typed, media, ares_password, work):
        super().__init__(typed, media, ares_password)
        self.work, self.versions, self.installs = work, {vm.TOOLS_V2: 2}, []
        self.ran = {}

    def known(self, fingerprint, version):
        self.versions[fingerprint] = version

    def lines(self, stage):
        params = self.callers[stage]
        commands = json.loads(subprocess.check_output(['git', '-C', str(self.work / 'stand-in-28' / 'stand-in.git'), 'show',
                                                        params['commit'] + ':os/owner-tools/commands.json']))
        return dict(params['lines'], **{step: commands[entry] for step, entry in params['entries'].items()})

    def answer(self, guest, name):
        if name == 'r28-v4-records':
            return list(self.machine['records'])
        if name == 'r28-tools-receipt':
            receipt = self.installs[-1]
            return dict(status='passed', command=['install'], trace=[], source='folder', finished_from='folder',
                        caller=dict(login_uid=1001, terminal=False), **receipt)
        return super().answer(guest, name)

    def run(self, stage):
        params, lines, machine = self.callers[stage], self.lines(stage), self.machine
        self.ran[stage] = lines
        done = dict(uid=1001, loginuid='1001', stdin_terminal=False, terminal=False, tty_errno=6, wayland=True,
                    runtime='/run/user/1001', line_sha256={step: hashlib.sha256(line.encode()).hexdigest() for step, line in lines.items()})
        if 'folder' in params['steps']:
            done['folder'] = dict(status=0, stdout='', stderr='')
            machine['folder'] = params['commit']
        window = self.windows[stage]
        answered = any(text == self.ares_password + '\n' for text, _ in self.typed[window['typed']:])
        new, = [fingerprint for fingerprint in self.versions if fingerprint in lines['routine']]
        old = machine['tools']
        routine = dict(signalled=[], helper=window['helper'], helper_gone=True)
        if not answered:
            routine.update(status=1, stdout='', stderr='sudo: no password was provided\n')
        elif new == old:
            routine.update(status=0, stderr='', stdout='Tools already installed; nothing changed\nmanifest SHA256 '+new+'\nPASS install\nPASS check\nPASS title\n')
        elif self.versions[new] <= self.versions[old]:
            routine.update(status=1, stderr='', stdout='STOP: Installed tools are version ' + str(self.versions[old]) + '; refusing version '
                           + str(self.versions[new]) + ' (downgrade or same version)\nSTOP bootstrap: verification or install refused\n')
        else:
            machine.update(tools=new, entry='tools-' + new + '/at', journal=dict(phase='complete', manifest=new, source='folder',
                                                                                 previous=old, tools_version=self.versions[new]))
            machine['records'].append('records/2026111' + str(len(self.installs)) + 'T120000.000000Z-tools-update.json')
            self.installs.append(dict(manifest=new, previous_manifest=old, previous_version=self.versions[old],
                                      tools_version=self.versions[new]))
            routine.update(status=0, stderr='', stdout='Tools updated from version ' + str(self.versions[old]) + ' to '
                           + str(self.versions[new]) + '\nPASS install\nPASS check\nPASS title\n')
        done['routine'] = routine
        if 'no-ticket' in params['steps'] and routine['status'] == 0:
            done['no_ticket'] = dict(status=1, stderr='sudo: a password is required\n')
        return done


class Release28Session:
    """Execute the submitted Python probes with controlled filesystem and process interfaces.

    Absolute paths map to a temporary guest root. Imports and process execution are closed over these fixtures;
    an unmodelled command fails rather than reaching the laptop. Faults change observations, never probe answers.
    """

    def __init__(self, control, faults=()):
        import importlib.machinery
        import types
        import release28_walk
        self.walk, self.control, self.faults = release28_walk, control, set(faults)
        self.foot, self.events, self.executed, self.boots = 1, [], [], []
        self.folder = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.folder.name)
        self.owners, self.modes, self.jvm, self.wrapper = {}, {}, False, None
        session = self

        class Path(type(self.root)):
            @staticmethod
            def mapped(parts):
                p = pathlib.Path(*parts)
                if p.is_absolute() and not p.is_relative_to(session.root):
                    p = session.root / str(p).lstrip('/')
                return p

            def __new__(cls, *parts):
                return super().__new__(cls, cls.mapped(parts))

            def __init__(self, *parts):
                super().__init__(self.mapped(parts))

            def stat(self, *, follow_symlinks=True):
                found = super().stat(follow_symlinks=follow_symlinks)
                uid, gid = session.owners.get(str(self), (1001, 1001))
                mode = (found.st_mode & ~0o7777) | session.modes.get(str(self), found.st_mode & 0o7777)
                return SimpleNamespace(st_uid=uid, st_gid=gid, st_mode=mode, st_size=found.st_size)

            def lstat(self):
                return self.stat(follow_symlinks=False)

        self.Path = Path
        self.Path('/tmp').mkdir()
        self.write('/proc/42/cmdline', '/usr/bin/labwc\0--config-dir\0/usr/share/aresos/labwc\0')
        self.write('/proc/42/environ', 'HOME=/var/home/ares\0WAYLAND_DISPLAY=wayland-0\0XDG_RUNTIME_DIR=/run/user/1001\0')
        self.write('/proc/42/cgroup', '0::/user.slice/user-1001.slice/session-3.scope\n')
        self.write('/usr/share/aresos/labwc/rc.xml', '<labwc_config><theme><name>Ares-Crown</name></theme></labwc_config>')
        self.write('/usr/share/themes/Ares-Crown/labwc/themerc', 'fixture')
        self.write('/usr/share/aresos/minecraft/desktop.lock.json', json.dumps(dict(instance='AresDesktop', java=dict(path='/java'))))
        self.write('/run/user/1001/aresos/desktop-runtime.json', json.dumps(dict(launch='fixture')))
        group = '/user.slice/user-1001.slice/user@1001.service/aresos.slice/aresos-game-fixture.scope'
        self.write('/proc/4242/cgroup', '0::' + group + '\n')
        self.write('/sys/fs/cgroup' + group + '/memory.high', release28_walk.MEMORY_HIGH)
        for name, data in {'.aresos-managed.json': '{"schema":1}', 'instance.cfg': '[General]\nname=AresDesktop\nlastLaunchTime=1\n',
                           'mmc-pack.json': '{"formatVersion":1}', 'minecraft/options.txt': 'fullscreen:false\n'}.items():
            self.write(release28_walk.INSTANCE + '/' + name, data)
        # The real provisioner owns this layout; a copied dictionary previously hid a VM blocker.
        loader = importlib.machinery.SourceFileLoader('release28_desktop_fixture',
            str(ROOT / 'os/config/usr/libexec/aresos-desktop'))
        desktop = types.ModuleType(loader.name)
        with patch.dict(sys.modules, {loader.name: desktop}):
            loader.exec_module(desktop)
        paths = desktop.Paths('/var/home/ares', '/run/user/1001')
        self.links = desktop.expected_links(paths, {})
        self.share = self.Path(paths.share)
        self.absent_share = self.root / 'release-28-share'
        for name, target in self.links.items():
            self.Path(target).mkdir(parents=True, exist_ok=True)
            self.Path(release28_walk.INSTANCE + '/' + name).symlink_to(self.Path(target))

    def control_fixture(self):
        record = {'files': {}}
        for file in ('CLAUDE.md', 'managed-settings.json'):
            content = '# managed fixture\n' if file.endswith('.md') else '{}\n'
            for top in ('/etc/claude-code', '/usr/etc/claude-code'):
                path = top + '/' + file
                self.write(path, content)
                self.owners[str(self.Path(path))] = (0, 0)
                self.Path(path).chmod(0o644)
            record['files']['/etc/claude-code/' + file] = dict(mode='0644', sha256=hashlib.sha256(content.encode()).hexdigest())
        self.write('/usr/share/aresos/manifest/control.json', json.dumps(record))
        self.write('/usr/share/aresos/control/service.json', json.dumps(dict(owner_uid=1001)))
        self.write('/usr/share/aresos/control/proxy.json', json.dumps(dict(folders=['/var/home/ares/Downloads', '/var/home/ares/Documents'])))
        for path, mode in {'/var/lib/aresos-tools': 0o700, '/var/lib/aresos-operation-evidence': 0o700, '/run/aresos-tools': 0o711,
                           '/var/home/ares/Downloads': 0o700, '/var/home/ares/Documents': 0o700}.items():
            self.Path(path).mkdir(parents=True, exist_ok=True)
            self.Path(path).chmod(mode)
            if not path.startswith('/var/home/'):
                self.owners[str(self.Path(path))] = (250, 250)
        self.write('/proc/4243/status', 'Uid:\t250\t250\t250\t250\nGid:\t250\t250\t250\t250\n')

    def boot(self, stage):
        """Switch the model's image payload, leaving home and its symlink text alone."""
        if stage in ('release-28', 'final-28'):
            if self.absent_share.exists(): self.absent_share.rename(self.share)
        elif self.share.exists():
            self.share.rename(self.absent_share)
        if self.control and stage in ('release-28', 'final-28') and not self.Path('/run/aresos-tools').exists():
            self.control_fixture()
        self.boots.append(dict(stage=stage, targets={
            name: self.Path(self.walk.INSTANCE + '/' + name).exists() for name in self.links}))

    def readlink(self, path):
        target = os.readlink(path)
        return '/' + str(pathlib.Path(target).relative_to(self.root)) if pathlib.Path(target).is_relative_to(self.root) else target

    def close(self):
        self.folder.cleanup()

    def write(self, path, data):
        p = self.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(data)

    def execute(self, script, *, uid=0, argv=(), allow_exit=False):
        import builtins, io, subprocess, xml.etree.ElementTree as ET

        def access(path, mode):
            p = self.Path(path)
            if not p.exists(): return False
            s = p.stat()
            shift = 6 if uid == s.st_uid else 3 if s.st_gid == 1001 else 0
            return uid == 0 or ((s.st_mode >> shift) & mode) == mode

        modules = dict(pathlib=SimpleNamespace(Path=self.Path, PurePath=pathlib.PurePath),
            os=SimpleNamespace(walk=os.walk, chown=lambda p,u,g: self.owners.__setitem__(str(p), (u,g)),
                readlink=self.readlink, access=access, R_OK=os.R_OK, W_OK=os.W_OK, X_OK=os.X_OK,
                getuid=lambda: uid, environ=dict(PATH='/usr/bin' if 'bad_path' in self.faults else vm.DAILY_PATH)),
            subprocess=SimpleNamespace(run=self.run, check_output=self.check_output, Popen=self.popen,
                DEVNULL=subprocess.DEVNULL, PIPE=subprocess.PIPE, STDOUT=subprocess.STDOUT, TimeoutExpired=subprocess.TimeoutExpired),
            time=SimpleNamespace(sleep=lambda _: None, monotonic=lambda: 0),
            sys=SimpleNamespace(argv=['probe', *argv], exit=lambda code: (_ for _ in ()).throw(SystemExit(code))),
            pwd=SimpleNamespace(getpwnam=lambda _: SimpleNamespace(pw_uid=250,pw_gid=250,pw_dir='/var/lib/aresos-tools',pw_shell='/usr/sbin/nologin'),
                getpwall=lambda: [SimpleNamespace(pw_name='aresos-tools',pw_uid=250)]),
            grp=SimpleNamespace(getgrnam=lambda _: SimpleNamespace(gr_gid=250),getgrall=lambda: [SimpleNamespace(gr_name='aresos-tools',gr_gid=250)]),
            xml=SimpleNamespace(etree=SimpleNamespace(ElementTree=SimpleNamespace(
                parse=lambda p: ET.ElementTree(ET.fromstring(p.read_text()))))))
        allowed = {'hashlib', 'json', 'stat', 're'}

        def imports(name, globals=None, locals=None, fromlist=(), level=0):
            key = 'xml' if name == 'xml.etree.ElementTree' else name
            if key in modules: return modules[key]
            assert name in allowed, 'Uncontrolled probe import: ' + name
            return builtins.__import__(name, globals, locals, fromlist, level)

        output = io.StringIO()
        status = 0
        with contextlib.redirect_stdout(output):
            try:
                exec(compile(script, '<submitted-release28-probe>', 'exec'),
                     dict(__name__='__main__', __builtins__=dict(vars(builtins), __import__=imports,
                          open=lambda p,*a,**kw: self.Path(p).open(*a,**kw))))
            except SystemExit as error:
                if not allow_exit: raise
                status = error.code
        return (status, output.getvalue()) if allow_exit else output.getvalue()

    def check_output(self, argv, **kw):
        done = self.run(argv, **kw)
        assert done.returncode == 0, (argv, done.stderr)
        return done.stdout

    def run(self, argv, **kw):
        import subprocess
        words, uid = list(argv), 0
        if words[:4] == ['runuser', '-u', 'ares', '--']:
            uid, words = 1001, words[4:]
        if words[0] in ('env', '/usr/bin/env'):
            words = words[1:]
            if words[0] == '-i': words = words[1:]
            while words and '=' in words[0]: words = words[1:]
        code, stdout, stderr = 0, '', ''
        if words[0] == 'pgrep':
            stdout = '42\n' if words[-1] == 'labwc' else ''.join(str(50+i)+'\n' for i in range(self.foot))
            code = 0 if stdout else 1
        elif words[0] == 'pkill':
            self.events.append('foot ended')
            if 'retained_foot' not in self.faults: self.foot = 0
        elif words[0] == 'setsid':
            assert words[1:] == ['-f', *vm.HUB_TERMINAL], 'Wrong Terminal argv'
            self.foot += 1
            self.events.append('terminal opened')
        elif words[0] == '/usr/bin/fc-match': stdout = self.walk.SPACE_GROTESK
        elif words == ['/usr/bin/python3', '-I', '-']:
            assert kw.get('input') == (ROOT / self.walk.CONTROL_CHECKER).read_text(), 'Not the bound checker on stdin'
            code, stdout = self.execute(kw['input'], allow_exit=True)
        elif words[:2] == ['systemctl', 'show']:
            if words[2] == 'aresos-toold.service':
                stdout = 'ActiveState=active\nSubState=running\nMainPID=4243\nNRestarts=0\nUnitFileState=enabled\n'
            else:
                name = words[-1]
                after = 'basic.target' if name == 'greetd.service' else ''
                if 'control_delays_login' in self.faults and name == 'basic.target': after = 'aresos-toold.service'
                requires = 'aresos-toold.service' if 'control_required_login' in self.faults and name == 'greetd.service' else ''
                state = 'loaded'
                if 'optional_login_unit' in self.faults:
                    if name == 'greetd.service': after += ' optional.service'
                    if name == 'optional.service': state, code = 'not-found', 1
                if 'missing_login_root' in self.faults and name == 'greetd.service': state, code = 'not-found', 1
                if 'failed_login_query' in self.faults and name == 'basic.target': code = 1
                stdout = f'Id={name}\nLoadState={state}\nAfter={after}\nRequires={requires}\nRequisite=\nBindsTo=\n'
        elif words[0] == 'python3' and words[1] == '-c':
            try: stdout = self.execute(words[2], uid=uid, argv=words[3:])
            except (AssertionError, OSError) as error: code, stderr = 1, str(error)
        elif words[:2] == ['/usr/libexec/aresos-desktop', 'status']:
            stdout = json.dumps(dict(state='SETUP', jvm_pid=4242) if self.jvm else dict(state='RECOVERY', latched=True))
        elif words[:2] == ['/usr/bin/systemctl', '--user']:
            assert words[2:] == ['kill', '--signal=SIGKILL', 'aresos-game-fixture.scope']
            self.jvm, self.wrapper.returncode = False, 137
        elif words[:2] == ['loginctl', 'list-sessions']: stdout = '3 1001 ares seat0 tty1\n'
        elif words[:2] == ['loginctl', 'show-session']: stdout = 'Active=yes\nRemote=no\n'
        elif words[0] == 'pkaction': stdout = '\n'.join(self.actions)
        elif words[0] == 'pkcheck': code = 0 if words[2] in self.passwordless else 2
        else: raise AssertionError('Uncontrolled probe command: ' + repr(words))
        done = subprocess.CompletedProcess(argv, code, stdout, stderr)
        if kw.get('check'): done.check_returncode()
        return done

    def popen(self, argv, **kw):
        assert '/usr/libexec/aresos-desktop-java' in argv and '-XX:+PauseAtStartup' in argv
        self.events.append('game scope')
        self.jvm = True
        self.wrapper = SimpleNamespace(returncode=None, poll=lambda: None, communicate=lambda **_: (b'', None))
        return self.wrapper

    def command(self, name, source):
        if name.endswith('-sites'):
            assert 'tee ' + self.walk.SITES in source and self.control
            words = shlex.split(source.splitlines()[-1])
            assert words[:2] == ['printf', '%s\\n']
            self.write(words[words.index('tee')+1], words[2] + '\n')
        if name.endswith('-sites-hash'):
            path = source.split('sha256sum < ', 1)[1].split()[0]
            if 'changed_sites' in self.faults and name.startswith('final-28'):
                self.write(path, 'changed\n')
            return hashlib.sha256(self.Path(path).read_bytes()).hexdigest() + '\n'
        if name == 'release-28-path-prepare':
            words = shlex.split(source)
            self.write('/run/aresos-path.py', base64.b64decode(words[words.index('printf')+2]).decode())
        return None

    def capture(self, name, source):
        if not name.startswith(('release-28-', 'previous-27-', 'final-28-')): return None
        suffixes = ('-session', '-end-foot', '-terminal', '-home', '-game-scope', '-polkit', '-path-result', '-control')
        if not name.endswith(suffixes): return None
        if name.endswith('-path-result'):
            # Execute the program prepared for, and typed into, the reopened terminal, then its reader.
            self.execute(self.Path('/run/aresos-path.py').read_text(), uid=1001)
            script = source.split("python3 - <<'PY'\n", 1)[1].split('\nPY', 1)[0]
        else:
            words = shlex.split(source)
            script = words[words.index('python3')+2]
        if name == 'final-28-control':
            if 'bad_control_state' in self.faults: self.modes[str(self.Path('/var/lib/aresos-tools'))] = 0o755
            if 'bad_control_folder' in self.faults: self.modes[str(self.Path('/var/home/ares/Downloads'))] = 0o755
            if 'bad_control_owner' in self.faults: self.owners[str(self.Path('/run/aresos-tools'))] = (0, 0)
        if name == 'final-28-home':
            if 'wrong_owner' in self.faults: self.owners[str(self.Path(self.walk.APPS))] = (0, 0)
            if 'missing_instance' in self.faults: self.Path(self.walk.INSTANCE + '/mmc-pack.json').unlink()
            # Root must still read the snapshot; only the controlled ares process loses access.
            if 'bad_permissions' in self.faults: self.modes[str(self.Path(self.walk.APPS))] = 0
            if 'stable_changed' in self.faults: self.write(self.walk.INSTANCE + '/minecraft/options.txt', 'changed')
            if 'bad_instance_mode' in self.faults: self.Path(self.walk.INSTANCE).chmod(0o700)
            if 'prism_mutable' in self.faults:
                self.write(self.walk.INSTANCE + '/instance.cfg', '[General]\nname=AresDesktop\nlastLaunchTime=2\n')
                self.write(self.walk.INSTANCE + '/minecraft/logs/latest.log', 'new log')
            world = (self.Path(self.walk.INSTANCE + '/minecraft/saves') / self.walk.WORLD).resolve()
            if 'deleted_world' in self.faults: (world / 'level.dat').unlink()
            if 'corrupt_world' in self.faults: (world / 'region/r.0.0.mca').write_bytes(b'corrupt')
            if 'denied_world' in self.faults: self.modes[str(world)] = 0
        if name.endswith('-game-scope') and 'bad_memory' in self.faults:
            self.write('/sys/fs/cgroup/user.slice/user-1001.slice/user@1001.service/aresos.slice/aresos-game-fixture.scope/memory.high', 'max')
        if name.endswith('-polkit'):
            reviewed = json.loads((ROOT / 'os/ci/polkit-review.json').read_text())['passwordless']
            self.actions = [*reviewed, 'unexpected.permission']
            self.passwordless = self.actions if 'extra_polkit' in self.faults else reviewed
        self.executed.append((name, script))
        return json.loads(self.execute(script))

    def owner(self, name, r27, r28):
        """The tools' lines on this route, by the command's stage name."""
        if name.endswith('-check-owner-result') and self.foot == 0:
            # Tools version 4's check reads his foot (owner.py:2016-2017).
            return dict(status='stopped', trace=[], error='Read failed: pgrep -u ares -x foot')
        lines = {'r28-update-owner-result': ['At shutdown, this update removes older AresOS', 'Signed exact release staged ' + r28],
                 'release-28-title-owner-result': ['Update to ' + r28 + ' confirmed after the restart'],
                 'r28-previous-owner-result': ['Previous AresOS queued for the next start ' + r27],
                 'previous-27-title-owner-result': ['Return to ' + r27 + ' confirmed after the restart'],
                 'r28-forward-owner-result': ['Newest installed AresOS starts next ' + r28],
                 'final-28-title-owner-result': ['Forward to ' + r28 + ' confirmed after the restart']}
        return dict(status='passed', trace=[], result=lines[name]) if name in lines else None


def tools_local_v3():
    import tools_local
    return tools_local.TOOLS_V3


def ast_literal(text):
    import ast
    return ast.literal_eval(text)


def historical_checkout(folder, commit):
    """Give the historical drivers the tool sources that went with their R27 rehearsal."""
    sources = subprocess.check_output(['git', '-C', str(ROOT), 'archive', commit, 'os/owner-tools', 'os/release'])
    with tarfile.open(fileobj=io.BytesIO(sources)) as archive:
        archive.extractall(folder, filter='data')
    for name in ('ci', 'tests', 'manifest/base.json', 'manifest/releases'):
        link = folder / 'os' / name
        link.parent.mkdir(exist_ok=True)
        link.symlink_to(ROOT / 'os' / name)
    # The driver expects the checkout target here. Use the fixed R27 record.
    (folder / 'os/manifest/release.json').write_bytes(R27_RECORD.read_bytes())
    return json.loads((folder / 'os/owner-tools/commands.json').read_text())


def walk(ps2=False, route='qualification', control=False, faults=()):
    assert route in ('qualification', 'update', 'reorder-probe', 'ways-back', 'tools-local', 'release-28')
    laptop = route in ('update', 'reorder-probe', 'ways-back', 'tools-local', 'release-28')
    dialogs = route in ('tools-local', 'release-28')
    stages = dict(qualification=QUALIFICATION_STAGES, update=UPDATE_STAGES)
    stages['reorder-probe'] = PROBE_STAGES
    stages['ways-back'] = WAYS_BACK_STAGES
    stages['tools-local'] = TOOLS_LOCAL_STAGES
    stages['release-28'] = RELEASE28_STAGES
    owner_words = {command: name for name, command in vm.COMMANDS.items()}
    oracle = [None]
    # The walk's own /var/lib/ares entry (InstalledTools): which toolset is installed, and the
    # process its entry starts. The harness's expected reader is judged against it, never copied.
    installed, tool_readers = [None], []
    def typed_owner():
        """The owner command typed last: its sudo words, and the tools' process the entry starts for it."""
        line = next((text.rstrip('\n') for text, profile in reversed(visible_blocks)
                     if '\n' not in text.rstrip('\n') and ' /var/lib/ares/at ' in text), None)
        if line is None:
            return None
        words = shlex.split(line.rsplit(';', 1)[-1])
        assert words[:2] == ['sudo', '/var/lib/ares/at'], line
        return dict(sudo=words, owner=installed[0].reader(words[2:]))
    visits, commands, typed, checks, markers = [], [], [], [], []
    visible_blocks = []
    physical_cases = []
    prompt_waits, idle_answers, hidden_reads = {}, [], []
    hidden_shapes, wait_shapes = [], []
    pinned, pair, staged, queued, rolled = (retained(n) for n in ('after-pin', 'aresos', 'after-switch-staged', 'after-rollback-queued', 'rollback'))
    old_reference = json.loads((ROOT / 'os/manifest/releases/13.json').read_text())['reference']
    new_reference = json.loads(R27_RECORD.read_text())['reference']
    if route == 'release-28':
        record_28 = release28_record()
    updates = update_states(pair, new_reference)
    if route == 'release-28':
        updates.update(release28_states(pair, new_reference, json.loads(record_28)['reference']))
        r28_session = Release28Session(control, faults)
    stock = copy.deepcopy(pinned['rpm']['deployments'][0])
    historical = None
    first = common.stock()
    first['bls'] = copy.deepcopy(pinned['bls'])
    disk = LaptopDisk(pair) if route in ('reorder-probe', 'ways-back') else None
    class Guest:
        def __init__(self, stage, menu=False):
            self.stage, self.owner_layout = stage, 'de'
            if route == 'release-28': r28_session.boot(stage)
            # A probe start: the first row, unless the menu is shown and waits for its choice.
            self.menu = menu
            if disk is not None and stage not in UPDATE_STAGES and not menu:
                disk.restart()
            self.owner_signed_in = True
            self.owner_physical_signed_in = False
            self.owner_media = None
            self.mode = 'installed'
            self.idle_models, self.idle_shapes = {}, {}
            self.screenshot_safe = True
            self.secrets = []
            self.key_counts = None
            self.process = Mock(); self.process.poll.return_value = None
            self.monitor = SimpleNamespace(command=self.qmp)
            self.physical_case = None
            self.last_typing_frame = None
            self.last_visible_frame = None
            self.typing_case = None
            self.boot_number = len(visits) + 1
            self.events = []
            self.monitor = SimpleNamespace(command=self.qmp,events=self.events)
            if ps2:
                from test_owner_ps2 import context
                self.xhci_context=context(needed=stage=='tools-stock')
                self.xhci_context['stage']=stage
            visits.append(stage)

        def command(self, name, source, **kw):
            syntax(name, source)
            commands.append((name, source))
            if dialogs:
                local.command(name, source)
            if route == 'release-28':
                said = r28_session.command(name, source)
                if said is not None:
                    return said
            if name.endswith('-prepare-input'):
                self.physical_case = name.removesuffix('-prepare-input')
            if name.endswith('-input-result'):
                self.physical_case = None
            if source.startswith('python3 -B /run/ares-login-'):
                from owner_login_shim import command
                return command(self,source)
            if name.endswith('-login-observers-prepare'):
                import ast,base64
                body=source.split("<<'ARES_LOGIN_PREPARE'\n",1)[1].split('\nARES_LOGIN_PREPARE',1)[0]
                tree=ast.parse(body)
                encoded,=[ast.literal_eval(n.args[0]) for n in ast.walk(tree) if isinstance(n,ast.Call)
                    and isinstance(n.func,ast.Attribute) and n.func.attr=='b64decode']
                compile(base64.b64decode(encoded),'prepared-observer-model','exec')
            if name.endswith('-homebrew'): return 'f' * 64 + '  /home/linuxbrew/.linuxbrew/bin/brew\n'
            if name.endswith('-show-menu-once'): disk.grubenv['menu_show_once'] = '1'
            if name.endswith('-one-time-entry'):
                disk.grubenv['next_entry'], = re.findall(r'grub2-reboot (ostree-[0-9]+);', source)
            if name.endswith('-policy'): return 'ARESOS_ACTIVE_SESSION_POLKIT_PASSED\nARESOS_GUEST_CHECKS_PASSED\n'
            return ''

        def capture_json(self, name, source):
            syntax(name, source)
            commands.append((name, source))
            if ps2 and name.endswith('-xhci-health'):
                import io,contextlib
                script=shlex.split(source)[shlex.split(source).index('python3')+2]
                output=io.StringIO()
                with contextlib.redirect_stdout(output):exec(script,{})
                result=json.loads(output.getvalue());assert not result['stop']
                checks.append(name)
                return result
            if '# hidden-key-counter' in source:
                if '-start' in name:
                    self.key_counts = dict(press=0,release=0,repeat=0,syn_dropped=0)
                    return dict(status='ready',path='/run/ares-input-fixture1',pid=77,device='/dev/input/event5',autorepeat=dict(delay_ms=250,period_ms=33),counts_only=True)
                result=dict(status='passed',counts_only=True,complete=True,keys_released=True,counts=dict(self.key_counts),
                    autorepeat=dict(delay_ms=250,period_ms=33),codes_recorded=False,values_recorded=False)
                if name.endswith('-stop'):self.key_counts=None
                return result
            if '# hidden-input-guard' in source:
                from test_owner_reliable_typing import execute_guard
                words=shlex.split(source);script=words[words.index('python3')+2]
                result=execute_guard(script)
                assert result['ready'], 'Modelled canonical reader refused'
                checks.append(name+'-canonical-blocked-reader')
                return result
            if '# visible-echo' in source:
                import ast
                words=shlex.split(source);script=words[words.index('python3')+2]
                value,=[ast.literal_eval(n.args[0]) for n in ast.walk(ast.parse(script)) if isinstance(n,ast.Call)
                    and isinstance(n.func,ast.Attribute) and n.func.attr=='endswith']
                result=execute_screen(script,vcsa('root# '+value))
                assert result['ready'];checks.append(name+'-cursor-echo-verified')
                return result
            if '# hidden-read-diagnostics' in source:
                from test_owner_read_diagnostics import execute_diagnostics
                words = shlex.split(source)
                return execute_diagnostics(words[words.index('python3') + 2])
            if '# hidden-phase:' in source:
                words = shlex.split(source)
                script = words[words.index('python3') + 2]
                phase = 'handoff' if '# hidden-phase: handoff' in script else 'left' if '# hidden-phase: left' in script else 'ready'
                rejected = phase == 'left' and 'layout-plain-us' in name
                actual = typed_owner()
                with model_clock():
                    result, rows, shape = execute_hidden(script, rejected=rejected, facts=True, actual=actual)
                if shape in ('nested-owner-getpass', 'sudo-owner-public-handoff'):
                    # The tools' own process was in front: which one, from the walk's entry.
                    reader = dict(boot=self.stage, argv=actual['owner'])
                    if reader not in tool_readers:
                        tool_readers.append(reader)
                # The harness stops on the same answer; the observer's reason says why (in run
                # 43581458429: Unexpected foreground reader).
                assert ((result.get('handoff_ready') and not result['ready']) if phase == 'handoff'
                        else (result.get('rejected') and not result['ready']) if rejected else result['ready']), \
                    'The modelled console does not show the reader the harness expects at ' + name + ': ' + str(
                        (result.get('observation') or {}).get('reason') or result.get('reason'))
                tty, = re.findall(r"(?:hidden_observation|hidden_left|hidden_handoff)\('(?P<tty>tty[34])'", script)
                if phase == 'left':
                    self.idle_models[tty] = rows
                    self.idle_shapes[tty] = shape
                hidden_reads.append((name, phase))
                hidden_shapes.append(dict(boot=self.stage, tty=tty, stage=name, phase=phase, shape=shape, completion=result['ready'] if phase=='left' else None,
                    expected_rejection=rejected, completion_uses_echo=False if phase!='ready' else None))
                return result
            if 'ready=shell' in source:
                words = shlex.split(source)
                script = words[words.index('python3') + 2]
                # Execute the real read-only observer on the pinned sudo relay
                # model at every wait, not a pre-granted Boolean authority.
                tty, = re.findall(r"os.open\('/dev/(tty[34])'", script)
                # Guest time moves here too: an idle observer that never sees its shell ends at its deadline.
                with model_clock(0):
                    value = execute_idle(script, (ROOT / 'os/tests/fixtures/owner-console/14zg-title-completed.vcsa').read_bytes(), rows=self.idle_models.get(tty))
                idle_answers.append(name)
                return value
            if 'base64.b64encode(data)' in source or 'base64.b64encode(raw)' in source:
                words=shlex.split(source);script=words[words.index('python3')+2]
                tty,=re.findall(r"pathlib.Path\('/dev/(vcsa[34])'",script)
                tty='tty'+tty[-1]
                predicate,=re.findall(r'^    if \((.*)\):$',script,re.M)
                if "'updated successfully' in full" in predicate or "'a password is required' in full" in predicate:
                    text=('passwd: all authentication tokens updated successfully.\nroot@bazzite:~#' if 'updated' in predicate
                          else 'sudo: a password is required\n[ares@bazzite ~]$')
                    raw=vcsa(text);kind='owner-output';shape='root-console-output'
                elif "bool(re.search(r'" in predicate:
                    wait=name.rsplit('-sample-',1)[0]
                    prompt_waits[wait]=prompt_waits.get(wait,0)+1
                    if ps2 and self.stage not in ('stock','tools-stock'):
                        from test_owner_records_prompt import retained_shape
                        clutter=retained_shape()
                    else:clutter=(ROOT/'os/tests/fixtures/owner-console/14zg-title-completed.vcsa').read_bytes()
                    raw=clutter if prompt_waits[wait]==1 else vcsa('ares-recovery@bazzite:~$')
                    kind='shell-prompt';shape=self.idle_shapes.get(tty,'sudo-i-readline')
                elif "line.endswith('login:')" in predicate:
                    raw=vcsa(('Login incorrect\n' if 'Login incorrect' in predicate else '')+'localhost login:')
                    kind='rejected-login' if 'Login incorrect' in predicate else 'getty-login-prompt';shape='getty-login-reader'
                elif predicate.startswith('line.endswith('):
                    import ast
                    prompt=ast.literal_eval(ast.parse(predicate,mode='eval').body.args[0])
                    assert prompt in ('Photographed Crucial serial:', 'Windows baseline Micron serial:', 'GitHub username:'), ('Uncovered public prompt',prompt)
                    raw=vcsa(prompt);kind='public-owner-input';shape='nested-owner-reader'
                else:
                    raise AssertionError('Uncovered cursor wait: '+name)
                result=execute_screen(script,raw)
                wait_shapes.append(dict(boot=self.stage,tty=tty,stage=name,kind=kind,shape=shape,predicate_executed=True))
                return result
            if name in ('offline-first-stock-link', 'stock-offline-login', 'live-offline-before-webui'):
                return dict(status='passed', physical_link_down=True)
            if name == 'owner-record-list': return []
            if name.endswith('-toolset'):
                # The harness resolves the installed entry in the guest: its program runs on the walk's own entry.
                words = shlex.split(source)
                return installed[0].resolve(words[words.index('python3') + 2])
            if disk is not None and name.endswith('-layout'): return disk.layout()
            if disk is not None and name.endswith(('-journal-before', '-journal-after')): return list(disk.journal)
            if disk is not None and name.endswith('-set-default'):
                words = shlex.split(source); script = words[words.index('python3') + 2]
                index, = re.findall(r"^argv=\['ostree', 'admin', 'set-default', '([0-9]+)'\]$", script, re.M)
                return disk.set_default(int(index))
            if disk is not None and name.endswith('-bls-entries'): return disk.inventory()
            if dialogs and local.answers(name):
                return local.answer(self, name)
            if route == 'release-28':
                seen = r28_session.capture(name, source)
                if seen is not None:
                    return seen
                if name.endswith('-owner-result') and self.stage in RELEASE28_STAGES[4:]:
                    said = r28_session.owner(name, new_reference, json.loads(record_28)['reference'])
                    if said is not None:
                        return said
            if route == 'ways-back':
                # The rehearsal's own captures; from tools version 3 on, the tools themselves answer.
                if name == 'tools-3-install-owner-result':
                    oracle[0].active = True
                    installed[0].install(media.fingerprint)
                    return dict(status='passed', trace=[], manifest=media.fingerprint, previous_manifest=vm.TOOLS_V2,
                        previous_version=2, tools_version=3, releases=[dict(reference=old_reference), dict(reference=new_reference)])
                if name.endswith('-owner-result') and oracle[0].active:
                    word = next(owner_words[text.rstrip('\n')] for text, profile in reversed(visible_blocks)
                                if text.rstrip('\n') in owner_words)
                    return oracle[0].command(word) if word in Oracle.WORDS else dict(status='passed', trace=[], result=[])
                if name.endswith('-updaters'):
                    units = ('uupd.service', 'uupd.timer', 'rpm-ostreed-automatic.timer')
                    return dict(files={unit: 'disabled' for unit in units}, active={unit: 'inactive' for unit in units})
                if name.endswith('-armed'): return dict(status='watching')
                if name.endswith('-frozen'):
                    cut[0] = oracle[0].cut()
                    return dict(status='frozen', pid=4242, state='T', release_step_ended=True, stop_after_swap_ms=1.0)
                if name.endswith('-intent'):
                    return {field: cut[0].get(field) for field in ('schema', 'word', 'status', 'mode', 'reference', 'digest',
                                                                   'target', 'before', 'intended', 'running')}
            if name == 'tools-install-owner-result':
                installed[0].install()  # the first install: tools/
            if name == 'update-tools-install-owner-result':
                installed[0].install(media.fingerprint)  # a tools update: tools-<fingerprint>/
                return dict(status='passed', trace=[], manifest=media.fingerprint, previous_manifest=vm.LAPTOP_TOOLS,
                    previous_version=1, tools_version=2, releases=[dict(reference=old_reference), dict(reference=new_reference)])
            if name.endswith('-owner-result') and laptop:
                lines = {'owner-update-owner-result': ['Signed exact release staged ' + new_reference],
                         'release-27-title-owner-result': ['Update to ' + new_reference + ' confirmed after the restart'],
                         'owner-previous-owner-result': ['Previous AresOS queued for the next start ' + old_reference],
                         'previous-13-title-owner-result': ['Return to ' + old_reference + ' confirmed after the restart']}
                if name == 'previous-13-update-refused-owner-result':
                    return dict(status='stopped', trace=[], error='Target release is already deployed; get help')
                if 'refus' in name or '-dummy-' in name:
                    return dict(status='stopped', trace=[],
                        error='Private release read failed; check read:packages permission/expiry and network; no credential was written')
                return dict(status='passed', trace=[], result=lines.get(name, []))
            if name.endswith('-owner-result'):
                return dict(status='stopped' if 'refus' in name or '-dummy-' in name else 'passed', trace=[],
                    error='Private release read failed; check read:packages permission/expiry and network; no credential was written')
            if name.endswith('-path-result'):
                return dict(found=True, uid=1001, owner_uid=1001, path=vm.DAILY_PATH + ':/home/linuxbrew/.linuxbrew/bin')
            if name.endswith('-polkit'):
                reviewed = sorted(json.loads((ROOT / 'os/ci/polkit-review.json').read_text())['passwordless'])
                return dict(session_active='yes', session_remote='no', session_scope=True, actions=len(reviewed) + 2,
                            answers={'0': len(reviewed) - 1, '1': 1, '2': 2}, passwordless=reviewed[1:])
            if name.endswith('-rules'):
                return dict(ares_in_wheel=True, sudo_all_with_password=True, sudo_keeps_no_ticket=True, sudo_n_refused=True,
                    ares_password_set=True, chrome_started=True, chrome_stderr_tail='', chrome_version='Google Chrome 157.0.8103.50',
                    session_path=vm.SYSTEM_PATH, hub_terminal_argv=vm.HUB_TERMINAL,
                    aresos_shell=dict(browser=True, notepad=True, terminal=True), aresos_shell_executable=True)
            if name == 'owner-prepared': return dict(stock=stock,state=dict(rpm=pinned['rpm'],bootc=pinned['bootc']))
            if name == 'owner-switch-pending': return staged['bootc']
            if name == 'owner-rollback-pending': return queued['bootc']
            if name.endswith('-labwc-environment'):
                # XKB separates its base layout from its variant.
                layout, variant = {'de': ('de', ''), 'us': ('us', ''), 'us-intl': ('us', 'intl')}[self.owner_layout]
                return dict(XKB_DEFAULT_LAYOUT=layout, XKB_DEFAULT_VARIANT=variant)
            if name.endswith('-loaded-keyboard'):
                profile = 'de' if self.stage in ('layout-reset-trial', 'trial-27') and '-pending-' in name else self.owner_layout
                layout, variant = {'de': ('de', ''), 'us': ('us', ''), 'us-intl': ('us', 'intl')}[profile]
                props = dict(VConsoleKeymap=profile, X11Layout=layout, X11Variant=variant)
                return dict(localed=dict(data=[{k:dict(data=v) for k,v in props.items()}]),
                    console='KEYMAP='+profile, x11='X11='+profile,
                    loaded_map=json.loads((FIXTURES/('dumpkeys-'+self.owner_layout+'.json')).read_text()),
                    cmdline='quiet ostree=/ostree/fixture', bls={e['file']:e['content'] for e in (pinned if self.stage=='corrected-stock' else pair)['bls']})
            if name.endswith('-all-console-maps'):
                return {str(n):json.loads((FIXTURES/'dumpkeys-de.json').read_text()) for n in range(1,7)}
            raise AssertionError('Unwalked response: ' + name)

        def qmp(self, command, args=None):
            if command == 'system_reset':
                self.events.append(dict(event='SHUTDOWN',data=dict(guest=False,reason='host-qmp-system-reset')))
                checks.append(self.stage+'-QMP-system-reset')
            if command != 'send-key': return
            assert args['hold-time'] == 30
            assert all(k['type'] == 'qcode' for k in args['keys'])
            keys = [k['data'] for k in args['keys']]
            if dialogs and keys == ['esc']:
                local.escaped = True
            if self.menu:
                # The boot menu takes the keys; Enter starts the row under the cursor.
                self.menu = not disk.key(keys)
                checks.append(self.stage + '-menu-' + '+'.join(keys))
                return
            # Observe the real call, without replacing any typing helper.
            frame = sys._getframe(1)
            while frame is not None and frame.f_code is not vm.type_text.__code__:
                frame = frame.f_back
            if frame is not None:
                visible=frame
                while visible is not None and visible.f_code is not vm.Console.visible.__code__: visible=visible.f_back
                if visible is not None and visible is not self.last_visible_frame:
                    self.last_visible_frame=visible
                    visible_blocks.append((visible.f_locals['text'],self.owner_layout))
                if frame is not self.last_typing_frame:
                    self.last_typing_frame = frame
                    text, layout = frame.f_locals['text'], frame.f_locals['layout']
                    profile = self.owner_layout if layout is None else layout
                    typed.append((text, profile))
                    self.typing_case = None
                    if self.physical_case and text == vm.TEXT + '\n':
                        self.typing_case = dict(stage=self.physical_case, boot=self.stage, profile=profile,
                            text=text, key_events=[], hold_ms=30, minimum_gap_ms=120)
                        physical_cases.append(self.typing_case)
                if self.typing_case is not None:
                    self.typing_case['key_events'].append(list(keys))
            if self.key_counts is not None:
                # Synthetic EV_KEY stream; the real parser computes the aggregate.
                import struct,owner_key_counter
                data=b''.join(struct.pack('@llHHi',0,0,1,30,value) for key in keys for value in (1,0))
                owner_key_counter.count_events(data,self.key_counts)
        keys = vm.Guest.keys
        def resync_after_hidden(self, stage):
            checks.append(stage + '-serial-idle-resync')
            return dict(status='passed', prior_completion_observed=True,
                raw_output_retained=False, serial_input_flushed=True, physical_enter_sent=False)
        def screenshot(self, stage):
            assert self.screenshot_safe
            if dialogs:
                local.screenshot(stage)
        def assert_offline(self, stage):
            vm.Guest.assert_offline(self, stage)
            checks.append(stage)
        def media_absent(self, stage):
            assert self.owner_media is None, 'Stick crossed a reboot'
            checks.append(stage + '-tools-absent')
        def finish_shutdown(self, stage, event):
            assert event in ('guest-reset','host-qmp-system-reset')
            if event=='host-qmp-system-reset':
                assert self.events==[dict(event='SHUTDOWN',data=dict(guest=False,reason=event))]
                self.stopped_events=list(self.events)
            elif oracle[0] is not None and oracle[0].active:
                # A typed reboot: the tools themselves must allow it (a fresh title, nothing unfinished).
                oracle[0].reboot()
            self.media_absent(stage)
            self.stopped_events_verified = True
        hard_reset=vm.Guest.hard_reset
        def poweroff(self, stage): self.media_absent(stage)
        def reboot(self, stage):
            # Plain `systemctl reboot` in the serial root shell (two_disk_vm.Guest.reboot).
            checks.append(stage + '-plain-reboot')
            self.finish_shutdown(stage, 'guest-reset')
        def login(self):
            assert not self.menu, 'Login before the boot menu was left'
        def close(self, stage):
            self.last_typing_frame = None
            self.last_visible_frame = None

    class Media:
        fingerprint = vm.LAPTOP_TOOLS if laptop else '0' * 64
        def replace(self, stage, source=None):
            assert guest_media[0] is None
            if stage == 'tools-3':
                # The historical rehearsal's second copy: version 3 over version 2.
                assert route == 'ways-back' and source is None and self.fingerprint == vm.TOOLS_V2
            elif route == 'tools-local' and stage in ('tools-next', 'export-version-2'):
                # Package 22d: the harness-built next version over version 2, then version 2 again.
                assert source is not None and self.fingerprint == (vm.TOOLS_V2 if stage == 'tools-next' else local.next_tools())
                self.fingerprint = local.next_tools() if stage == 'tools-next' else vm.TOOLS_V2
                checks.append(stage + '-windows-copy')
                return
            else:
                # Package 22c's and 22d's routes copy version 2 from history; the update rehearsal copied its checkout's payload.
                assert self.fingerprint == vm.LAPTOP_TOOLS and (source is not None) == (route in ('reorder-probe', 'ways-back', 'tools-local', 'release-28'))
            if source is None:
                self.fingerprint = vm.bundle_module('bundle').check(pathlib.Path('os/owner-tools/payload'))
            else:
                self.fingerprint = vm.bundle_module('owner').checked_bundle(source)
            checks.append(stage + '-windows-copy')
        def attach(self, guest, stage):
            assert guest.owner_signed_in and guest.owner_physical_signed_in
            guest.owner_media = self
            guest_media[0] = self
            if ps2:vm.owner_xhci.checkpoint(guest,stage+'-model-after-hotplug',attached=True)
            checks.append(stage + '-hotplug')
        def detach(self, guest, stage):
            assert guest.owner_media is self
            guest.owner_media = None
            guest_media[0] = None
            if ps2:vm.owner_xhci.checkpoint(guest,stage+'-model-after-detach',attached=False,needed=False)
            checks.append(stage + '-detach')

    guest_media = [None]
    cut = [None]
    media = Media()
    local = None

    def snapshot(guest, stage):
        if route == 'ways-back' and guest.stage not in UPDATE_STAGES[:4]:
            return disk.snapshot()
        if disk is not None and (stage == 'release-27' or guest.stage not in UPDATE_STAGES[:4] and stage.startswith(('walk-', 'menu-', 'after-menu-'))):
            return disk.snapshot()
        if laptop and stage in updates: return updates[stage]
        if route == 'update' and stage == 'previous-13-after-refusal': return updates['previous-13']
        if stage == 'offline-first-stock': return first
        if stage == 'owner-switch-staged': return staged
        if stage == 'owner-rollback-queued': return queued
        if guest.stage.startswith(('tools-stock', 'corrected-stock')): return pinned
        if guest.stage in ('rollback-stock', 'default-stock'): return rolled
        return pair

    with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary, contextlib.ExitStack() as stack:
        if route == 'release-28': stack.callback(r28_session.close)
        if ps2:
            from test_owner_ps2 import kernel_result,journal
            original_run=subprocess.run
            def run(argv,*args,**kwargs):
                if argv[0]=='journalctl':return kernel_result(journal())
                return original_run(argv,*args,**kwargs)
            stack.enter_context(patch.object(subprocess,'run',side_effect=run))
        # The walk models guest time; deadline boundaries have dedicated tests.
        stack.enter_context(patch.object(vm.owner_login.time,'monotonic',return_value=10.0))
        save=vm.td.save
        def record(name,value):
            if re.search(r'-read-wait-[0-9]+$',name) and value.get('reader') and value.get('ready'):
                tty='tty'+str(value['reader']['physical']-1024)
                hidden_reads.append((name,'ready'))
                hidden_shapes.append(dict(boot='prepared-login',tty=tty,stage=name,phase='ready',
                    shape='getty-login-reader',completion=None,expected_rejection=False,completion_uses_echo=None))
            return save(name,value)
        stack.enter_context(patch.object(vm.td,'save',side_effect=record))
        stack.enter_context(patch.object(vm.Guest, 'network_up', False))
        for module in (vm.td, vm.sw):
            stack.enter_context(patch.object(module, 'EVIDENCE', pathlib.Path(temporary)))
        for name in ('install', 'restore_windows_order'):
            stack.enter_context(patch.object(vm.td, name))
        # The host-side boot entry edit after the install (SerialConsolePinTest covers it).
        stack.enter_context(patch.object(vm, 'pin_serial_console', side_effect=lambda: checks.append('stock-serial-console')))
        stack.enter_context(patch.object(vm.td, 'marker', side_effect=lambda audit,name,**kw: markers.append(name)))
        stack.enter_context(patch.object(vm.td, 'start_installed', side_effect=lambda p,h,s,**kw: Guest(s)))
        stack.enter_context(patch.object(vm.kb, 'deployment_snapshot', side_effect=snapshot))
        stack.enter_context(patch.object(vm.kb, 'capture_stock_greeter'))
        # public_typing/physical_input/type_text/physical_keys/Guest.keys are
        # unpatched. The QMP recorder above observes their actual key events.
        stack.enter_context(patch.object(vm.time, 'sleep'))
        stack.enter_context(patch.dict(os.environ, GITHUB_ACTOR='synthetic-user', GH_TOKEN='synthetic_only_0123', GITHUB_SHA='a'*40))
        audit = Mock()
        installed[0] = InstalledTools(temporary)
        if disk is not None:
            stack.enter_context(patch.object(vm.rp, 'start_at_menu', side_effect=lambda p, h, s: Guest(s, menu=True)))
            stack.enter_context(patch.object(vm.rp, 'read_screen', side_effect=lambda guest, name: disk.screen()))
        if route in ('update', 'reorder-probe', 'ways-back', 'tools-local'):
            import release28_walk, tools_local
            head = {'ways-back': tools_local.V3_COMMIT, 'tools-local': release28_walk.V4_COMMIT}.get(route, vm.TOOLS_V2_COMMIT)
            historical = pathlib.Path(temporary) / 'historical'
            historical_commands = historical_checkout(historical, head)
            version_2 = vm.laptop_payload(pathlib.Path(temporary) / 'tools-version-2', vm.TOOLS_V2_COMMIT, vm.TOOLS_V2)
            stack.enter_context(contextlib.chdir(historical))
            stack.enter_context(patch.object(vm, 'COMMANDS', historical_commands))
        if route == 'tools-local':
            local = ToolsLocal(typed, media, 'abcdefghijklmnopqrstuvwx', historical)
            stack.enter_context(patch.dict(os.environ, GITHUB_SHA=head))
            stack.enter_context(patch.object(vm.td, 'WORK', pathlib.Path(temporary)))
            tools_local.rehearsal(vm, audit, media, 'yz-/!ü0123456789abcdef', 'SYNTHETIC-HASH', 'abcdefghijklmnopqrstuvwx',
                                  version_2)
            result = json.loads((pathlib.Path(temporary) / 'tools-local-rehearsal-result.json').read_text())
        elif route == 'release-28':
            import release28_walk
            head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
            stack.enter_context(patch.dict(os.environ, GITHUB_SHA=head))
            stack.enter_context(patch.object(vm.td, 'WORK', pathlib.Path(temporary)))
            stack.enter_context(patch.object(release28_walk, 'CONTROL_RIDES', control))
            local = Release28Local(typed, media, 'abcdefghijklmnopqrstuvwx', pathlib.Path(temporary))
            local.known(release28_walk.TOOLS_V4, 4)
            local.known(release28_walk.announced(record_28)['fingerprint'], release28_walk.TOOLS_VERSION)
            version_2 = vm.laptop_payload(pathlib.Path(temporary) / 'tools-version-2', vm.TOOLS_V2_COMMIT, vm.TOOLS_V2)
            release28_walk.rehearsal(vm, audit, media, 'yz-/!ü0123456789abcdef', 'SYNTHETIC-HASH', 'abcdefghijklmnopqrstuvwx',
                                     version_2, record_28, allow_deferred=True)
            result = json.loads((pathlib.Path(temporary) / 'release-28-rehearsal-result.json').read_text())
        elif route == 'ways-back':
            oracle[0] = Oracle(stack, disk, old_reference, new_reference)
            vm.ways_back_rehearsal(audit, media, 'yz-/!ü0123456789abcdef', 'SYNTHETIC-HASH', 'abcdefghijklmnopqrstuvwx',
                                   version_2)
            result = json.loads((pathlib.Path(temporary) / 'ways-back-rehearsal-result.json').read_text())
        elif route == 'reorder-probe':
            vm.reorder_probe(audit, media, 'yz-/!ü0123456789abcdef', 'SYNTHETIC-HASH', version_2)
            result = json.loads((pathlib.Path(temporary) / 'reorder-probe-result.json').read_text())
        elif route == 'update':
            vm.update_rehearsal(audit, media, 'yz-/!ü0123456789abcdef', 'SYNTHETIC-HASH', 'abcdefghijklmnopqrstuvwx')
            result = json.loads((pathlib.Path(temporary) / 'update-rehearsal-result.json').read_text())
        else:
            # The retained switch fixtures are release 13's first switch.
            vm.qualification(audit, media, 'yz-/!ü0123456789abcdef', 'SYNTHETIC-HASH', release=old_reference)
            result = json.loads((pathlib.Path(temporary) / 'owner-tools-result.json').read_text())
        assert result['status'] == 'passed'
        assert audit.check.call_count == len(stages[route])
        events = [json.loads(p.read_text()) for p in pathlib.Path(temporary).glob('*-resync-1.json')]
        assert len(events) == len(prompt_waits) and all(n == 2 for n in prompt_waits.values())
        assert all(e['enter_sent'] and e['ready'] and e['observer']['ready'] and
                   e['observer']['observation']['foreground_chain'] for e in events)
        assert all(wait + '-idle-1' in idle_answers for wait in prompt_waits)
        # passwd's first value completes when the same reader asks again (-repeat).
        ready_names = [name for name, phase in hidden_reads if phase == 'ready' and not name.endswith('-repeat')]
        left_names = [name.removesuffix('-left') for name, phase in hidden_reads if phase == 'left']
        left_names += [name.removesuffix('-repeat') for name, phase in hidden_reads if phase == 'ready' and name.endswith('-repeat')]
        assert ready_names and len(set(ready_names)) == len(ready_names) and set(ready_names) == set(left_names)
    assert visits == stages[route]
    assert {'prepared-unattended-windows','offline-roundtrip-unattended-windows','offline-roundtrip-detached-windows','final-unattended-windows','final-detached-windows'} <= set(markers)
    assert checks.index('tools-stock-hotplug') < checks.index('tools-stock-detach') < checks.index('tools-stock-reboot-tools-absent')
    return dict(stages=visits, commands=commands, typed=typed, visible_blocks=visible_blocks, checks=checks, markers=markers,
        physical_cases=physical_cases, result=result, disk=disk, tool_readers=tool_readers, local=local,
        session=r28_session if route == 'release-28' else None,
        prompt_waits=sorted(prompt_waits), fresh_idle_answers=idle_answers, resyncs=events,
        hidden_reads=hidden_reads, hidden_shapes=hidden_shapes, wait_shapes=wait_shapes)


class Release28ProbeTest(unittest.TestCase):
    def test_injected_guest_failures_stop_the_route(self):
        cases = {'retained_foot': 'still running', 'bad_control_state': 'Control release checker failed',
                 'bad_control_folder': 'Control daily folder metadata differs', 'bad_control_owner': 'Control release checker failed',
                 'control_delays_login': 'Control service delays login', 'control_required_login': 'Control service delays login',
                 'failed_login_query': 'login dependency query failed', 'missing_login_root': 'login dependency query failed',
                 'wrong_owner': 'ownership changed', 'missing_instance': 'inaccessible as ares',
                 'bad_permissions': 'inaccessible as ares', 'stable_changed': 'stable instance',
                 'bad_instance_mode': 'stable instance', 'bad_memory': 'memory.high',
                 'extra_polkit': 'beyond the reviewed list', 'bad_path': 'terminal lacks his PATH',
                 'deleted_world': 'missing saved-world', 'corrupt_world': 'saved-world contents',
                 'denied_world': 'inaccessible as ares'}
        for fault, error in cases.items():
            with self.subTest(fault=fault), self.assertRaisesRegex(AssertionError, error):
                walk(route='release-28', control=fault.startswith(('bad_control', 'control_')) or fault in ('failed_login_query', 'missing_login_root'), faults=[fault])

    def test_removing_the_submitted_kill_no_longer_gets_a_canned_success(self):
        import release28_walk
        source = release28_walk.END_FOOT.replace("subprocess.run(['pkill','-u','ares','-x','foot'])", 'pass')
        self.assertNotEqual(source, release28_walk.END_FOOT)
        with patch.object(release28_walk, 'END_FOOT', source), self.assertRaisesRegex(AssertionError, 'still running'):
            walk(route='release-28')

    def test_explicit_prism_allowances_preserve_stable_files(self):
        result = walk(route='release-28', faults=['prism_mutable'])
        self.assertNotEqual(result['result']['home']['instance_tree'], result['result']['home']['after_forward_tree'])
        self.assertEqual([name for name, _ in result['session'].executed if name.endswith('-home')],
                         ['release-28-home', 'previous-27-home', 'final-28-home'])


class Release28InstallerTest(unittest.TestCase):
    def attempt(self, old_version, new_version, identical=False):
        old, new = '11'*32, '11'*32 if identical else '22'*32
        model = object.__new__(Release28Local)
        model.versions = {old: old_version, new: new_version}
        model.installs, model.ares_password = [], 'synthetic-password'
        model.ran = {}
        model.typed = [(model.ares_password+'\n', 'de')]
        model.windows = dict(retry=dict(typed=0, helper='helper'))
        model.callers = dict(retry=dict(steps=('folder', 'routine', 'no-ticket'), commit='fixture'))
        model.machine = dict(tools=old, entry='tools-'+old+'/at', journal=None, records=[], folder='fixture')
        before = copy.deepcopy(model.machine)
        with patch.object(model, 'lines', return_value=dict(folder='folder', routine='routine '+new)):
            done = model.run('retry')
        return model, before, done

    def test_identical_fingerprint_is_a_no_op_before_the_version_check(self):
        model, before, done = self.attempt(5, 5, identical=True)
        self.assertEqual(done['routine']['status'], 0)
        self.assertIn('Tools already installed; nothing changed', done['routine']['stdout'])
        self.assertEqual(model.machine, before)
        self.assertEqual(model.installs, [])

    def test_same_version_different_fingerprint_refuses_without_writes(self):
        model, before, done = self.attempt(5, 5)
        self.assertEqual(done['routine']['status'], 1)
        self.assertIn('refusing version 5 (downgrade or same version)', done['routine']['stdout'])
        self.assertEqual(model.machine, before)
        self.assertEqual(model.installs, [])

    def test_downgrade_refuses_without_writes(self):
        model, before, done = self.attempt(5, 4)
        self.assertEqual(done['routine']['status'], 1)
        self.assertIn('refusing version 4 (downgrade or same version)', done['routine']['stdout'])
        self.assertEqual(model.machine, before)
        self.assertEqual(model.installs, [])

    def test_newer_fingerprint_installs_and_records_the_previous_bundle(self):
        model, before, done = self.attempt(4, 5)
        self.assertEqual(done['routine']['status'], 0)
        self.assertIn('Tools updated from version 4 to 5', done['routine']['stdout'])
        self.assertEqual(model.machine['tools'], '22'*32)
        self.assertEqual(model.installs, [dict(manifest='22'*32, previous_manifest='11'*32, previous_version=4, tools_version=5)])


class OwnerWalkTest(unittest.TestCase):
    def test_real_typing_chain_emits_exact_keys_through_every_remaining_stage(self):
        result = walk(ps2=True)
        german = [['z'], ['y'], ['slash'], ['shift', '7'], ['shift', '1'], ['bracket_left'], ['ret']]
        international = [['y'], ['z'], ['minus'], ['slash'], ['shift', '1'], ['alt_r', 'y'], ['ret']]
        expected = {
            'corrected-stock-console': 'de', 'aresos-console': 'de', 'aresos-foot': 'de',
            'layout-reset-trial-console':'de','layout-reset-trial-foot':'de',
            'layout-reset-recovery-console':'de','layout-reset-recovery-foot':'de',
            'aresos-intl-console': 'us-intl', 'aresos-intl-foot': 'us-intl',
            'aresos-back-de-console': 'de', 'aresos-back-de-foot': 'de',
            'rollback-stock-console': 'de', 'default-stock-console': 'de',
        }
        self.assertEqual({row['stage']: row['profile'] for row in result['physical_cases']}, expected)
        self.assertEqual(len(result['physical_cases']), len(expected))
        for row in result['physical_cases']:
            self.assertEqual(row['text'], 'yz-/!ü\n')
            self.assertEqual(row['key_events'], international if row['profile'] == 'us-intl' else german)
            self.assertEqual((row['hold_ms'], row['minimum_gap_ms']), (30, 120))
        # These firmware-default marker boots have no typed text or layout.
        self.assertEqual(result['markers'][-2:], ['final-unattended-windows', 'final-detached-windows'])
        self.assertFalse(any(row['boot'].startswith('final-') for row in result['physical_cases']))

    def test_ps2_health_and_q15_clutter_walk_all_remaining_stages(self):
        result=walk(ps2=True)
        self.assertIn('final-unattended-windows',result['markers'])
        self.assertIn('final-detached-windows',result['markers'])
        names=[name for name,source in result['commands']]
        self.assertTrue(any(name.endswith('-xhci-health') for name in names))
        for stage in ('aresos','aresos-intl','aresos-back-de','rollback-stock','default-stock'):
            self.assertTrue(any(name.startswith(stage) and name.endswith('-xhci-health') for name in names),stage)

    def test_update_route_walks_the_laptop_tools_update_password_and_previous(self):
        commands = json.loads(vm.git_blob(vm.TOOLS_V2_COMMIT, 'os/owner-tools/commands.json'))
        for ps2 in (False, True):
            with self.subTest(ps2=ps2):
                result = walk(ps2=ps2, route='update')
                typed = [text for text, profile in result['visible_blocks']]
                # Steps 4 to 6 with the laptop's 15f bootstrap, step 8 with this guide's.
                self.assertEqual(sum(t.rstrip('\n') == vm.laptop_commands()['install'] for t in typed), 1)
                self.assertEqual(sum(t.rstrip('\n') == commands['install'] for t in typed), 1)
                self.assertNotEqual(vm.laptop_commands()['install'], commands['install'])
                for name in ('prepare', 'login', 'verify', 'switch', 'update', 'previous', 'check', 'title', 'records', 'export', 'reboot'):
                    self.assertIn(commands[name] + '\n', typed, name)
                order = [typed.index(commands['install'] + '\n'), typed.index(commands['update'] + '\n'),
                         typed.index('sudo passwd ares\n'), typed.index('sudo -v\n'), typed.index(commands['previous'] + '\n')]
                self.assertEqual(order, sorted(order))
                self.assertIn('ares\n', typed)
                self.assertIn('sudo -n true\n', typed)
                self.assertIn('sudo-passwd-reader', {s['shape'] for s in result['hidden_shapes']})
                # polkit is asked while his desktop is in front: after the terminal PATH
                # probe (which leaves tty1 active) and guest.sh, before the console returns.
                names = [name for name, source in result['commands']]
                self.assertEqual(names.count('release-27-polkit'), 1)
                self.assertLess(names.index('release-27-path-result'), names.index('release-27-policy'))
                self.assertLess(names.index('release-27-policy'), names.index('release-27-polkit'))
                self.assertLess(names.index('release-27-polkit'), names.index('release-27-rules'))
                checks = result['checks']
                self.assertLess(checks.index('update-windows-copy-windows-copy'), checks.index('update-tools-hotplug'))
                self.assertLess(checks.index('update-tools-hotplug'), checks.index('update-tools-detach'))
                self.assertIn('owner-update-reboot-tools-absent', checks)
                self.assertEqual(result['markers'][-2:], ['final-unattended-windows', 'final-detached-windows'])

    def test_live_offline_command_is_composed_and_checked(self):
        guest = object.__new__(vm.Guest)
        checked = []
        def capture(name, source):
            syntax(name, source)
            checked.append(source)
            return dict(physical_link_down=True)
        guest.capture_json = capture
        guest.assert_offline('live-offline-before-webui')
        self.assertEqual(len(checked), 1)
        self.assertIn("\nPY\n} >", checked[0])

    def test_real_guest_boot_and_marker_shutdown_adapters_preserve_parent_api(self):
        monitor=Mock()
        def initialize(guest,*args,**kw):guest.monitor=monitor;guest.boot_number=1
        with patch.object(vm.td.Guest,'__init__',initialize),patch.object(vm.td,'save'),patch.object(vm.Guest,'network_up',False):
            guest=vm.Guest('SYNTHETIC-DISK','SYNTHETIC-PASSWORD',[])
        self.assertEqual(monitor.command.call_args_list[0].args,('set_link',{'name':'owner-net','up':False}))
        self.assertEqual(monitor.command.call_args_list[1].args,('cont',))
        guest.media_absent=Mock()
        with patch.object(vm.td.Guest,'finish_shutdown',return_value='stopped') as finish:
            self.assertEqual(guest.finish_shutdown('marker','guest-shutdown',timeout=30),'stopped')
            finish.assert_called_once_with('marker','guest-shutdown',timeout=30)
        guest.media_absent.assert_called_once_with('marker')
        with patch.object(vm.td.Guest,'boot_args',return_value=['EXISTING']):
            self.assertEqual(guest.boot_args(),['EXISTING','-S'])
        guest.mode='marker-windows'
        self.assertNotIn('usb-storage',' '.join(guest.peripheral_args()))
        self.assertNotIn('fsdev',' '.join(guest.peripheral_args()))
        self.assertNotIn('hostfwd',guest.network_args())

    def test_file_image_creation_windows_copy_and_export_inspection_host_paths(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as directory, contextlib.ExitStack() as stack:
            root=pathlib.Path(directory).resolve()
            evidence=root/'evidence';evidence.mkdir()
            stack.enter_context(patch.object(owner_media.td,'WORK',root))
            stack.enter_context(patch.object(owner_media.td,'EVIDENCE',evidence))
            stack.enter_context(patch.dict(os.environ,GITHUB_ACTIONS='true',GITHUB_REPOSITORY='Ares-Empire/AresOS',
                GITHUB_REF_NAME='pkg/14-owner-tools',REHEARSAL_PACKAGE='14'))
            media=owner_media.Media()
            fake=Volume(root,media.mount)
            volume=fake.volume;calls=fake.calls
            stack.enter_context(patch.object(owner_media.subprocess,'run',side_effect=fake.run))
            stack.enter_context(patch.object(owner_media.subprocess,'check_output',side_effect=fake.output))
            fake.patch_nodes(stack)
            verify=stack.enter_context(patch.object(owner_media,'verify_loop',wraps=owner_media.verify_loop))
            media.create()
            self.assertEqual(media.path.stat().st_size,128*1024**2)
            self.assertEqual(media.fingerprint,common.bundle.check(volume/'ares-tools'))
            records=volume/'ares-records';records.mkdir();(records/'diagnostic.json').write_text('{"synthetic":true}')
            media.verify('standin')
            self.assertEqual((evidence/'owner-records/diagnostic.json').read_bytes(),(records/'diagnostic.json').read_bytes())
            self.assertEqual(verify.call_count,3)
            self.assertTrue(any(c[0]=='mount.exfat-fuse' and 'ro,nodev,nosuid,noexec' in c for c in calls))
            self.assertFalse(media.attached)

    def test_all_remaining_host_paths_and_all_typed_characters(self):
        with patch(__name__ + '.syntax', wraps=syntax) as checked:
            result = walk()
        self.assertEqual(checked.call_count, len(result['commands']))
        names = {name for name, source in result['commands']}
        self.assertTrue(result['prompt_waits'])
        for fragment in ('export', 'corrected-stock', 'login', 'signature', 'switch', 'aresos',
                         'layout-us-begin', 'layout-intl-proof', 'layout-us-revert',
                         'layout-intl-finish', 'rollback', 'keep-stock'):
            self.assertTrue(any(fragment in n for n in result['prompt_waits']), fragment)
        for fragment in ('layout-us-begin','layout-plain-us-rejected','layout-us-revert','layout-intl-proof',
                         'layout-back-de-proof','rollback-from-stock-refused','owner-keep-stock'):
            self.assertTrue(any(fragment in n for n in names), fragment)
        self.assertEqual({s['shape'] for s in result['hidden_shapes']}, {'getty-login-reader',
            'persistent-login-readline','sudo-password-reader','sudo-i-readline',
            'nested-owner-getpass','sudo-owner-public-handoff','login-rejected'})
        left=[s for s in result['hidden_shapes'] if s['phase']=='left']
        self.assertEqual(len(left),27)
        self.assertEqual(sum(s['expected_rejection'] and not s['completion'] for s in left),1)
        self.assertTrue(all(not s['completion_uses_echo'] for s in left))
        self.assertEqual(sum(s['phase']=='handoff' for s in result['hidden_shapes']),3)
        self.assertEqual({s['boot'] for s in left},set(result['stages'])-{'stock'})
        self.assertTrue(all(s['predicate_executed'] for s in result['wait_shapes']))
        for text, profile in result['typed']:
            # Deliberately wrong positions in the plain-US failure use de.
            for char in text: vm.physical_keys(char, profile)
        for profile in ('de','us-intl'):
            for char in string.ascii_letters + string.digits + '_-\n': vm.physical_keys(char, profile)
        with self.assertRaises(AssertionError): vm.physical_keys('☃', 'de')
        with self.assertRaises(AssertionError): vm.physical_keys('ü', 'us')

    def test_retained_full_states_agree_and_keep_saved_serial(self):
        index=json.loads((FIXTURES/'sources.json').read_text())
        saved=retained('after-pin')
        stock=saved['rpm']['deployments'][0]
        prepared=dict(stock_identity=list(common.owner.key(stock)), stock=stock, state=dict(rpm=saved['rpm'],bootc=saved['bootc']))
        # The retained 13f states are release 13's.
        release=json.loads((ROOT/'os/manifest/releases/13.json').read_text())['reference']
        for row in index['files']:
            self.assertEqual(hashlib.sha256((FIXTURES/row['file']).read_bytes()).hexdigest(),row['sha256'])
            state=json.loads((FIXTURES/row['file']).read_text())
            common.owner.qualified_state(dict(rpm=state['rpm'], bootc=state['bootc']), prepared, release)

    def test_qmp_hotplug_identity_removal_and_bad_hash_refuse_before_qmp(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as temporary:
            media=object.__new__(owner_media.Media)
            media.path=pathlib.Path(temporary)/'stick.raw';media.path.write_bytes(b'SYNTHETIC-IMAGE')
            media.expected=owner_media.digest(media.path);media.attached=False;media.fingerprint='f'*64
            class Monitor:
                events=[]
                def __init__(self): self.calls=[]
                def command(self, command, args=None):
                    self.calls.append((command,args))
                    if command=='query-block':return [dict(inserted={'node-name':'owner-tools','file':str(media.path)})]
                    if command=='device_del': self.events.append(dict(event='DEVICE_DELETED',data=dict(device='owner-tools-usb')))
            guest=Mock(mode='installed',owner_signed_in=True,owner_physical_signed_in=True,boot_number=1)
            guest.monitor=Monitor();guest.capture_json.return_value=dict(label='ARESTOOLS')
            with patch.object(owner_media.td,'save'),patch.object(media,'verify'),patch.object(owner_media.time,'sleep'):
                media.attach(guest,'fixture');media.detach(guest,'fixture')
                self.assertFalse(media.attached)
                self.assertEqual([c for c,a in guest.monitor.calls],['blockdev-add','blockdev-add','device_add','query-block','device_del','blockdev-del','blockdev-del'])
                offset=len(guest.monitor.calls);media.path.write_bytes(b'ALTERED')
                with self.assertRaises(AssertionError):media.attach(guest,'bad')
                self.assertEqual(len(guest.monitor.calls),offset)

    def test_only_the_exact_untouched_old_entry_is_temporarily_exempt(self):
        from keyboard_entries import entry_identity
        state=retained('after-pin')
        bls=[dict(identity=list(entry_identity(e['deployment'])),content=e['content']) for e in state['bls']]
        stock=state['rpm']['deployments'][0]
        prepared=dict(stock_identity=list(common.owner.key(stock)),stock=stock,before_bls=copy.deepcopy(bls),
                      state=dict(rpm=state['rpm'],bootc=state['bootc']))
        checked=common.owner.keyboard_entries(prepared['state'],prepared,bls)
        self.assertEqual([e['identity'] for e in checked],[prepared['stock_identity']])
        old=next(e for e in bls if e['identity']!=prepared['stock_identity'])
        old['content']+='\noptions evil=changed\n'
        with self.assertRaises(common.owner.Stop):common.owner.keyboard_entries(prepared['state'],prepared,bls)


class SerialConsolePinTest(unittest.TestCase):
    """Runs 6 and 12 hung in systemd's size probe of the VM's serial console; these args skip the probes."""
    ENTRY = ('title Fedora Linux 44.20261012.1 (Bazzite) (ostree:0)\nversion 1\n'
             'linux /ostree/default-a2/vmlinuz-7.2.9\ninitrd /ostree/default-a2/initramfs-7.2.9.img\n'
             'options console=tty0 console=ttyS0,115200n8 root=UUID=fixture vconsole.keymap=de rootflags=subvol=root rw '
             'ostree=/ostree/boot.0/default/a2/0\n')

    def test_the_six_args_are_the_ones_systemd_reads_for_the_console_and_ttys0(self):
        self.assertEqual(vm.TTY_ARGS, ('systemd.tty.term.console=vt220', 'systemd.tty.rows.console=24',
                                       'systemd.tty.columns.console=80', 'systemd.tty.term.ttyS0=vt220',
                                       'systemd.tty.rows.ttyS0=24', 'systemd.tty.columns.ttyS0=80'))

    def test_appended_once_to_the_options_line_and_nothing_else_changes(self):
        after = vm.with_tty_args(self.ENTRY)
        before_lines, after_lines = self.ENTRY.split('\n'), after.split('\n')
        self.assertEqual(len(before_lines), len(after_lines))
        for old, new in zip(before_lines, after_lines):
            if old.startswith('options '):
                self.assertEqual(new, old + ' ' + ' '.join(vm.TTY_ARGS))
            else:
                self.assertEqual(new, old)
        self.assertEqual(vm.with_tty_args(after), after)  # idempotent
        partial = self.ENTRY.replace(' rw ', ' rw systemd.tty.rows.console=24 ')
        options = next(l for l in vm.with_tty_args(partial).split('\n') if l.startswith('options '))
        self.assertEqual(options.split().count('systemd.tty.rows.console=24'), 1)
        self.assertTrue(all(options.split().count(arg) == 1 for arg in vm.TTY_ARGS))

    def test_an_entry_without_exactly_one_options_line_stops(self):
        for entry in (self.ENTRY.replace('options ', 'optionsx '), self.ENTRY + 'options quiet\n'):
            with self.subTest(entry=entry[-30:]), self.assertRaisesRegex(AssertionError, 'STOP: the installed boot entry has'):
                vm.with_tty_args(entry)

    def boot(self, root, names):
        (root / 'loader/entries').mkdir(parents=True)
        for name in names:
            (root / 'loader/entries' / name).write_text(self.ENTRY)

    def test_the_only_entry_is_edited_and_read_back_and_a_second_pass_changes_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            self.boot(root, ['ostree-1.conf'])
            first = vm.edit_boot_entries(root)
            self.assertEqual((first['entry'], first['added']), ('ostree-1.conf', list(vm.TTY_ARGS)))
            self.assertEqual((root / 'loader/entries/ostree-1.conf').read_text(), vm.with_tty_args(self.ENTRY))
            second = vm.edit_boot_entries(root)
            self.assertEqual(second['added'], [])
            self.assertEqual(second['before'], second['after'])
        for names in ([], ['ostree-1.conf', 'ostree-2.conf']):
            with self.subTest(entries=names), tempfile.TemporaryDirectory() as folder:
                self.boot(pathlib.Path(folder), names)
                with self.assertRaisesRegex(AssertionError, 'STOP: expected exactly one installed boot entry'):
                    vm.edit_boot_entries(folder)

    def run_pin(self, types, entries=('ostree-1.conf',), mount_fails=False):
        calls, saved, mounts = [], {}, []
        with tempfile.TemporaryDirectory() as folder:
            work = pathlib.Path(folder)
            (work / 'target.raw').write_bytes(b'')
            (work / 'protected.raw').write_bytes(b'')

            def check_output(argv, **kw):
                calls.append(list(argv))
                return '/dev/loop7\n'

            def wait(loop, image):
                calls.append(['wait_loop_partitions', loop, str(image)])
                return dict(status='passed', loop=loop, expected=[dict(number=int(part.rsplit('p', 1)[1]))
                                                                  for part in types])

            def run(argv, **kw):
                calls.append(list(argv))
                if argv[0] == 'blkid':
                    return SimpleNamespace(stdout=types[argv[-1]] + '\n', returncode=0)
                if argv[0] == 'mount':
                    mounts.append(argv[-1])
                    if mount_fails:
                        raise vm.subprocess.CalledProcessError(32, argv)
                    self.boot(pathlib.Path(argv[-1]), entries)
                if argv[0] == 'umount':
                    shutil.rmtree(pathlib.Path(argv[-1]) / 'loader')  # an unmounted mount point is empty again
                return SimpleNamespace(stdout='', returncode=0)
            with patch.object(vm.td, 'WORK', work), patch.object(vm.subprocess, 'check_output', side_effect=check_output), \
                    patch.object(vm.subprocess, 'run', side_effect=run), patch.object(vm, 'wait_loop_partitions', side_effect=wait), \
                    patch.object(vm.td, 'save', side_effect=lambda name, value: saved.__setitem__(name, value)):
                try:
                    result = vm.pin_serial_console()
                except (AssertionError, vm.subprocess.CalledProcessError) as error:
                    result = error
            self.assertFalse(any(os.path.exists(mount) for mount in mounts))  # every mount point removed
            return result, calls, saved, work

    def test_the_host_attaches_only_the_target_edits_its_ext4_boot_and_cleans_up(self):
        types = {'/dev/loop7p1': 'vfat', '/dev/loop7p2': 'ext4', '/dev/loop7p3': 'btrfs'}
        result, calls, saved, work = self.run_pin(types)
        self.assertNotIsInstance(result, Exception)
        self.assertEqual(calls[0], ['losetup', '--find', '--show', '--partscan', str(work / 'target.raw')])
        self.assertEqual(calls[1], ['wait_loop_partitions', '/dev/loop7', str(work / 'target.raw')])  # before any node is read
        self.assertEqual([call[-1] for call in calls if call[0] == 'blkid'], sorted(types))
        self.assertFalse(any('protected.raw' in ' '.join(call) for call in calls))
        mount, = [call for call in calls if call[0] == 'mount']
        self.assertEqual(mount[:5], ['mount', '-t', 'ext4', '-o', 'nosuid,nodev,noexec'])
        self.assertEqual(mount[5], '/dev/loop7p2')
        self.assertEqual([call[0] for call in calls[-2:]], ['umount', 'losetup'])
        self.assertEqual(calls[-1], ['losetup', '--detach', '/dev/loop7'])
        self.assertEqual(saved['stock-serial-console']['added'], list(vm.TTY_ARGS))
        self.assertEqual(saved['stock-serial-console']['partition'], 'p2')

    def test_an_unexpected_target_layout_stops_and_still_detaches(self):
        for name, types, entries in (
                ('two ext4', {'/dev/loop7p1': 'ext4', '/dev/loop7p2': 'ext4'}, ('ostree-1.conf',)),
                ('no ext4', {'/dev/loop7p1': 'vfat', '/dev/loop7p2': 'btrfs'}, ('ostree-1.conf',)),
                ('two entries', {'/dev/loop7p1': 'vfat', '/dev/loop7p2': 'ext4'}, ('ostree-1.conf', 'ostree-2.conf'))):
            with self.subTest(name):
                result, calls, saved, work = self.run_pin(types, entries)
                self.assertIsInstance(result, AssertionError)
                self.assertIn('STOP:', str(result))
                self.assertEqual(calls[-1], ['losetup', '--detach', '/dev/loop7'])
                self.assertEqual('umount' in [call[0] for call in calls], 'mount' in [call[0] for call in calls])
                self.assertNotIn('stock-serial-console', saved)

    def test_a_failed_mount_is_not_unmounted_and_still_detaches_the_loop(self):
        """Review 5: a mount that fails must not end in a failing umount that skips the detach."""
        types = {'/dev/loop7p1': 'vfat', '/dev/loop7p2': 'ext4', '/dev/loop7p3': 'btrfs'}
        result, calls, saved, work = self.run_pin(types, mount_fails=True)
        self.assertIsInstance(result, vm.subprocess.CalledProcessError)
        self.assertEqual([call[0] for call in calls[-2:]], ['mount', 'losetup'])
        self.assertNotIn('umount', [call[0] for call in calls])
        self.assertEqual(calls[-1], ['losetup', '--detach', '/dev/loop7'])
        self.assertNotIn('stock-serial-console', saved)


class ReleaseRulesTest(unittest.TestCase):
    """Package 21's rules on the updated system read the password hash itself (rehearsal run 9)."""

    def password_set(self):
        source = vm.RULES.split('def password_set(entry):', 1)[1].split('\nout[', 1)[0]
        namespace = {}
        exec('def password_set(entry):' + source, namespace)
        return namespace['password_set']

    def test_the_rules_compile_and_read_the_shadow_hash_not_a_passwd_status(self):
        compile(vm.RULES, 'release-rules', 'exec')
        self.assertIn("['getent','shadow','ares']", vm.RULES)
        self.assertNotIn("'passwd','-S'", vm.RULES)

    def test_only_a_crypt_hash_counts_as_a_set_password(self):
        password_set = self.password_set()
        for entry, expected in (('ares:$y$j9T$fixture$fixture:20404:0:99999:7:::\n', True),
                                ('ares:$6$fixture$fixture:20404:0:99999:7:::\n', True),
                                ('ares:!*:20404:0:99999:7:::\n', False),       # the image's locked account
                                ('ares:!$y$j9T$fixture:20404:0:99999:7:::\n', False),  # locked again later
                                ('ares:*:20404:0:99999:7:::\n', False),
                                ('ares::20404:0:99999:7:::\n', False)):
            with self.subTest(entry=entry):
                self.assertIs(password_set(entry), expected)


class TerminalPathTest(unittest.TestCase):
    """Rehearsal run 5 (43120759117) typed the PATH probe right after Ctrl+Alt+F1 and it never ran."""
    PATH = vm.DAILY_PATH + ':/home/linuxbrew/.linuxbrew/bin'

    def run_path(self, answers):
        events, saved = [], {}

        class Guest:
            owner_layout = 'de'
            def keys(self, names): events.append(('keys', tuple(names)))
            def command(self, name, source, **kw):
                syntax(name, source); events.append(('command', name, source)); return ''
            def capture_json(self, name, source):
                syntax(name, source); events.append(('capture', name, source))
                answer = answers.pop(0)
                if isinstance(answer, BaseException): raise answer
                return answer
            def screenshot(self, name): events.append(('screenshot', name))
        real_sleep = vm.time.sleep

        def sleep(seconds):
            # time.sleep is the time module's. Only terminal_path's own sleep belongs to the order;
            # subprocess waits (the guest syntax check's bash -n, other tests' threads) keep the
            # real one. On rehearsal run 8's runner and under load such waits slept 1 ms here.
            if sys._getframe(1).f_code is vm.terminal_path.__code__:
                events.append(('sleep', seconds))
            else:
                real_sleep(seconds)
        with patch.object(vm.time, 'sleep', new=sleep), \
                patch.object(vm.td, 'save', side_effect=lambda name, value: saved.__setitem__(name, value)):
            try: result = vm.terminal_path(Guest(), 'release-27')
            except AssertionError as error: result = error
        return events, saved, result

    def typed(self, events):
        """The text typed in foot, read back from its physical German keys."""
        german = {tuple(vm.physical_keys(c, 'de')): c for c in set('python3 /run/aresos-path.py\n')}
        return ''.join(german[e[1]] for e in events if e[0] == 'keys' and e[1] not in (('ctrl', 'alt', 'f1'), ('ctrl', 'u')))

    def test_types_only_after_switch_foot_round_trip_active_session_and_settle(self):
        events, saved, result = self.run_path([dict(found=True, uid=1001, owner_uid=1001, path=self.PATH)])
        self.assertNotIsInstance(result, AssertionError)
        steps = [e[:2] for e in events if e[0] != 'keys']
        first_key = next(i for i, e in enumerate(events) if e[0] == 'keys' and e[1] != ('ctrl', 'alt', 'f1'))
        self.assertEqual(events[0], ('keys', ('ctrl', 'alt', 'f1')))
        self.assertEqual([e[:2] for e in events[1:first_key]],
                         [('command', 'release-27-path-foot'), ('command', 'release-27-path-prepare'),
                          ('command', 'release-27-path-session'), ('sleep', 1)])
        self.assertEqual(steps[-2:], [('capture', 'release-27-path-result'), ('screenshot', 'release-27-path')])
        self.assertEqual(self.typed(events), 'python3 /run/aresos-path.py\n')
        session = dict((e[1], e[2]) for e in events if e[0] == 'command')['release-27-path-session']
        self.assertEqual(session, vm.ACTIVE_DESKTOP)
        for needle in ('$3 == "ares" && $4 == "seat0"', '-p Active --value)" = yes', '-p State --value)" = active'):
            self.assertIn(needle, session)
        self.assertFalse(saved['release-27-terminal-path']['retried'])
        self.assertNotIn(('screenshot', 'release-27-path-miss'), [e[:2] for e in events])

    def test_one_miss_is_retried_once_after_a_screenshot_and_line_clear(self):
        events, saved, result = self.run_path([dict(found=False),
                                               dict(found=True, uid=1001, owner_uid=1001, path=self.PATH)])
        self.assertNotIsInstance(result, AssertionError)
        names = [e[:2] for e in events if e[0] != 'keys' or e[1] == ('ctrl', 'u')]
        miss = names.index(('capture', 'release-27-path-result'))
        self.assertEqual(names[miss + 1:], [('screenshot', 'release-27-path-miss'), ('keys', ('ctrl', 'u')),
                                            ('capture', 'release-27-path-retry-result'), ('screenshot', 'release-27-path')])
        self.assertEqual(self.typed(events), 'python3 /run/aresos-path.py\n' * 2)
        self.assertTrue(saved['release-27-terminal-path']['retried'])
        sources = {e[1]: e[2] for e in events if e[0] == 'capture'}
        self.assertIn('range(20)', sources['release-27-path-result'])
        self.assertNotIn('SystemExit', sources['release-27-path-result'])
        self.assertIn('range(60)', sources['release-27-path-retry-result'])
        self.assertIn("raise SystemExit('No terminal PATH probe')", sources['release-27-path-retry-result'])

    def test_a_second_miss_stops_without_a_third_attempt(self):
        failed = AssertionError('Guest command failed: release-27-path-retry-result, exit 1')
        events, saved, result = self.run_path([dict(found=False), failed])
        self.assertIs(result, failed)
        self.assertEqual(self.typed(events), 'python3 /run/aresos-path.py\n' * 2)
        self.assertNotIn('release-27-terminal-path', saved)
        self.assertNotIn(('screenshot', 'release-27-path'), [e[:2] for e in events])

    def test_the_guest_probe_reports_a_first_miss_and_reads_a_hit(self):
        import subprocess
        with tempfile.TemporaryDirectory() as folder:
            target = str(pathlib.Path(folder) / 'probe')
            def program(required):
                source = vm.path_probe(target, 1, required)
                return source.split("python3 - <<'PY'\n", 1)[1].split('\nPY', 1)[0]
            miss = subprocess.run([sys.executable, '-c', program(False)], capture_output=True, text=True)
            self.assertEqual((miss.returncode, json.loads(miss.stdout)), (0, dict(found=False)))
            stop = subprocess.run([sys.executable, '-c', program(True)], capture_output=True, text=True)
            self.assertNotEqual(stop.returncode, 0)
            self.assertIn('No terminal PATH probe', stop.stderr)
            pathlib.Path(target).write_text(json.dumps(dict(uid=1001, path=self.PATH)))
            hit = subprocess.run([sys.executable, '-c', program(False)], capture_output=True, text=True)
            value = json.loads(hit.stdout)
            self.assertEqual((value['found'], value['uid'], value['path']), (True, 1001, self.PATH))
            self.assertEqual(value['owner_uid'], os.stat(target).st_uid)


class BootStallTest(unittest.TestCase):
    """Rehearsal run 6 (43136407300): release 27's boot never showed `login:` and both consoles froze."""

    @staticmethod
    def stat(tid, utime, stime):
        # A command name with a space and a parenthesis, as /proc allows.
        return f'{tid} (CPU 0/KVM) x) S 1 1 1 0 -1 4194624 0 0 0 0 {utime} {stime} 0 0 20 0 1 0 100 0 0\n'

    def monitor(self, folder, status=None):
        calls = []
        def command(name, arguments=None):
            calls.append((name, arguments))
            if name == 'query-status':
                if isinstance(status, BaseException): raise status
                return status or dict(running=True, status='running')
            if name == 'query-cpus-fast': return [{'cpu-index': 0, 'thread-id': 101}, {'cpu-index': 1, 'thread-id': 102}]
            if name == 'send-key': return {}
            raise AssertionError(name)
        return SimpleNamespace(command=command), calls

    def test_vcpu_ticks_read_utime_and_stime_after_the_command_name(self):
        with tempfile.TemporaryDirectory() as folder:
            proc = pathlib.Path(folder)
            for tid, (u, s) in ((101, (700, 50)), (102, (3, 4))):
                (proc / str(tid)).mkdir(); (proc / str(tid) / 'stat').write_text(self.stat(tid, u, s))
            monitor, _ = self.monitor(folder)
            self.assertEqual(vm.vcpu_ticks(monitor, proc), {0: dict(thread_id=101, ticks=750), 1: dict(thread_id=102, ticks=7)})

    def run_stall(self, status=None):
        saved, events = {}, []
        with tempfile.TemporaryDirectory() as folder:
            proc = pathlib.Path(folder)
            def write(ticks):
                for tid, value in ticks.items():
                    (proc / str(tid)).mkdir(exist_ok=True)
                    (proc / str(tid) / 'stat').write_text(self.stat(tid, value, 0))
            write({101: 100, 102: 200})
            monitor, calls = self.monitor(folder, status)
            def wait(pattern, timeout):
                events.append(('wait', pattern, timeout))
                raise TimeoutError('Guest console did not reach ' + pattern)
            guest = SimpleNamespace(monitor=monitor, boot_number=11, wait=wait,
                                    screenshot=lambda name: events.append(('screenshot', name)))
            original = vm.vcpu_ticks
            with patch.object(vm, 'vcpu_ticks', side_effect=lambda m: original(m, proc)), \
                    patch.object(vm.time, 'sleep', side_effect=lambda s: (events.append(('sleep', s)), write({101: 100, 102: 690}))), \
                    patch.object(vm.td, 'save', side_effect=lambda name, value: saved.__setitem__(name, value)):
                value = vm.boot_stall(guest, 'release-27')
        return value, saved, calls, events

    def test_records_state_vcpu_time_and_a_sysrq_w_dump_then_a_screenshot(self):
        value, saved, calls, events = self.run_stall()
        self.assertIs(saved['release-27-boot-stall'], value)
        self.assertEqual(value['status'], dict(running=True, status='running'))
        self.assertEqual([(row['cpu'], row['thread_id'], row['ticks_used']) for row in value['vcpus']], [(0, 101, 0), (1, 102, 490)])
        self.assertEqual([name for name, _ in calls], ['query-status', 'query-cpus-fast', 'query-cpus-fast', 'send-key'])
        self.assertEqual([k['data'] for k in calls[-1][1]['keys']], ['alt', 'sysrq', 'w'])
        self.assertTrue(value['sysrq_w_sent'])
        self.assertEqual(events, [('sleep', 5), ('wait', '(?!)', 10), ('screenshot', 'release-27-boot-stall')])

    def test_a_failed_probe_is_recorded_and_the_others_still_run(self):
        value, saved, calls, events = self.run_stall(status=RuntimeError('QMP gone'))
        self.assertIn('QMP gone', value['status_error'])
        self.assertIn('vcpus', value)
        self.assertTrue(value['sysrq_w_sent'])
        self.assertIn(('screenshot', 'release-27-boot-stall'), events)

    def test_login_runs_the_diagnostics_only_for_a_boot_that_never_showed_login(self):
        timeout = TimeoutError('Guest console did not reach \\blogin: *')
        for started, expected in ((False, 1), (True, 0)):
            with self.subTest(authentication_started=started):
                guest = object.__new__(vm.Guest)
                guest.authentication_started, guest.mode, guest.boot_purpose = started, 'installed', 'release-27'
                with patch.object(vm.td.Guest, 'login', side_effect=timeout), \
                        patch.object(vm, 'boot_stall') as stall, self.assertRaises(TimeoutError) as raised:
                    guest.login()
                self.assertIs(raised.exception, timeout)
                self.assertEqual(stall.call_count, expected)
                if expected:
                    stall.assert_called_once_with(guest, 'release-27')


if __name__=='__main__': unittest.main()
