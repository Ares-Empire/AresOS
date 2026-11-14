"""B3 host, separate from the reference ledger. No operation reaches the host OS.

ostree list writes/finalize and bootc status slots follow the brief's source rules.
B10 replays captures through THIS class, also used by the exhaustive model.
"""
import contextlib
import copy
import io
import json
import re
from functools import lru_cache
from unittest.mock import patch

import test_owner_update as base
from ways_back_keyboard import KeyboardMachine, PowerCut, identity


FIELDS = ('checksum', 'serial', 'osname', 'container-image-reference', 'container-image-reference-digest',
          'pinned', 'booted', 'staged', 'unlocked')


def compact(row):
    return {k: row[k] for k in FIELDS if k in row}


def status(rows):
    """Only the first other non-staged row in the booted stateroot is rollback."""
    running = next(r for r in rows if r['booted'])
    new = next((r for r in rows if r.get('staged')), None)
    rollback = next((r for r in rows if r is not running and not r.get('staged') and r['osname'] == running['osname']), None)

    def slot(row):
        if row is None:
            return None
        reference = row['container-image-reference']
        for prefix in ('ostree-unverified-registry:', 'ostree-image-signed:docker://'):
            if reference.startswith(prefix):
                reference = reference[len(prefix):]
                break
        return dict(ostree=dict(checksum=row['checksum'], deploySerial=row['serial'], stateroot=row['osname']),
                    pinned=row['pinned'], image=dict(image=dict(image=reference, transport='registry'),
                                                      imageDigest=row['container-image-reference-digest']))
    queued = rollback is not None and rows.index(rollback) < rows.index(running)
    return dict(rpm=dict(deployments=copy.deepcopy(rows), transaction=None),
                bootc=dict(spec=dict(bootOrder='rollback' if queued else 'default'),
                           status=dict(booted=slot(running), rollback=slot(rollback), staged=slot(new), rollbackQueued=queued)))


@lru_cache(maxsize=128)
def script_body(text, name):
    marker = text.split("<<'", 1)[1].split("'", 1)[0]
    body, tail = text.split("<<'" + marker + "'\n", 1)[1].split('\n' + marker + '\n', 1)
    return compile(body, name, 'exec'), tail


class Host(KeyboardMachine):
    ENTRY = ('title Bazzite (ostree:{place})\nversion {number}\n'
             'options quiet ostree=/ostree/boot.0/default/{boot}/{place}\n')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.templates = {r: compact(base.release_row(ref)) for r, ref in [('13', base.R13), ('27', base.R21), ('28', base.R30)]}
        self.templates['S'] = compact(base.stock_row())
        self.reset_disk(self.state['rpm']['deployments'])
        self.cut = ''

    def reset_disk(self, rows):
        self.state = status(copy.deepcopy(rows))
        self.links = 1
        self.started_at = next(i for i, r in enumerate(self.entries_rows()) if r['booted'])
        self.boot_checksum = 'b' * 64
        self.entry_files = {}
        self.ostree_journal = []
        self.merge = identity(self.running())

    def entries_rows(self):
        return [r for r in self.state['rpm']['deployments'] if not r.get('staged')]

    def path(self, row):
        return '/sysroot/ostree/deploy/%s/deploy/%s.%d' % (row['osname'], row['checksum'], row['serial'])

    def entries(self):
        rows = self.entries_rows()
        result = []
        for place, row in enumerate(rows):
            file = '/boot/loader/entries/ostree-%d.conf' % (len(rows) - place)
            content = self.entry_files.get(file, self.ENTRY.format(place=place, number=len(rows) - place, boot=self.boot_checksum))
            result.append(dict(file=file, title=content.splitlines()[0].removeprefix('title '), content=content,
                               target=self.path(row), identity=list(identity(row))))
        return result

    def kernel_link_target(self):
        # Intentionally can disagree with running(): a reorder rebinds this positional link.
        return self.path(self.entries_rows()[self.started_at])

    def write_list(self, rows):
        self.state = status([r for i, r in enumerate(rows) if i == 0 or not r.get('staged')])
        self.links = 1 - self.links

    def set_default(self, index):
        rows = self.state['rpm']['deployments'][:]
        selected = rows.pop(index)
        self.write_list([selected, *rows])
        message = f'Transaction complete; bootconfig swap: no; bootversion: boot.0.{self.links}, deployment count change: 0'
        self.ostree_journal.append(message)
        self.changes.append('ostree admin set-default %d' % index)
        return message

    def finalize(self):
        rows = self.state['rpm']['deployments']
        new = next(r for r in rows if r.get('staged'))
        running = self.running()
        self.settings[identity(new)] = self.keyboard()
        # Keep in old order: new, pinned, booted, merge and other stateroots.
        keep = [r for r in rows if r is new or r['pinned'] or r['booted'] or identity(r) == self.merge or r['osname'] != running['osname']]
        self.write_list([dict(r, staged=False) for r in keep])

    def restart(self, choice=None, power_off=False):
        rows = self.state['rpm']['deployments']
        if any(r.get('staged') for r in rows):
            if power_off:
                self.write_list([r for r in rows if not r.get('staged')])
            else:
                self.finalize()
        rows = self.state['rpm']['deployments']
        index = 0 if choice is None else next(i for i, r in enumerate(rows) if identity(r) == choice)
        self.state = status([dict(r, booted=i == index, staged=False) for i, r in enumerate(rows)])
        self.started_at = index
        self.ostree_journal = []
        self.loaded = self.keyboard()['VConsoleKeymap']

    def mutate(self, *command, **kwargs):
        if command == ('rpm-ostree', 'cleanup', '--pending'):
            rows = self.state['rpm']['deployments']
            booted = next(i for i, r in enumerate(rows) if r['booted'])
            self.write_list([r for i, r in enumerate(rows) if not r.get('staged') and (r['pinned'] or i >= booted)])
            self.changes.append(command)
            return
        assert command[0] in ('localectl', 'loadkeys') or command == ('systemctl', 'reboot'), command
        super().mutate(*command, **kwargs)
        if command[:3] == ('localectl', '--no-convert', 'set-x11-keymap') and self.cut == 'persistent':
            raise PowerCut('after both persistent layout writes')

    def script(self, text, name, mutation=True):
        if name == 'verify':
            reference = re.findall(r"'([^']+)'", text.strip().splitlines()[-1])[-1]
            certificate = re.search(r"--certificate-identity '([^']+)'", text)[1]
            assert self.signed.get(reference) == certificate
            return ''
        if name == 'stock-session':
            return ''  # isolated boundary: stock login setup is outside this state machine
        assert name in ('start-next', 'update'), name
        code, tail = script_body(text, name)

        def run(argv, **kw):
            assert kw == {'check': True}
            if argv == ['sync']:
                self.changes.append('sync')
                return
            assert argv[:3] == ['ostree', 'admin', 'set-default'], argv
            self.set_default(int(argv[3]))
            if self.cut == 'primitive':
                raise PowerCut('after set-default')
        def read(argv, **kw):
            assert argv in (['rpm-ostree', 'status', '--json'], ['bootc', 'status', '--json']), argv
            return json.dumps(self.state['rpm' if argv[0] == 'rpm-ostree' else 'bootc'])
        # Real script assertions run before we log any mutation or invoke the primitive.
        with patch('subprocess.check_output', side_effect=read), patch('subprocess.run', side_effect=run), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                exec(code, {})
            except AssertionError as error:
                # python3 ends an uncaught assertion with exit status 1.
                raise base.owner.Failed('Shared step failed: ' + name, 1) from error
            except SystemExit as error:
                # The script's own exit status, as owner.Host.script reports it.
                raise base.owner.Failed('Shared step failed: ' + name, error.code if isinstance(error.code, int) else 1) from error
        if name == 'update':
            line, = [line for line in tail.splitlines() if line.startswith('bootc switch --retain ')]
            reference = line.split()[-1]
            row, = [r for r in self.templates.values() if r['container-image-reference'].endswith(reference)]
            self.merge = identity(self.running())
            self.state = status([dict(row, staged=True, booted=False), *self.state['rpm']['deployments']])
            self.changes.append(line)
            if self.cut == 'primitive':
                raise PowerCut('after staging')
        self.trace.append(dict(script=name, mutation=True))
        return ''
