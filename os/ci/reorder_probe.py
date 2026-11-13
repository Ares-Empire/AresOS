"""Package 22c, stage 0: plain `ostree admin set-default` over three deployments, observed.

The owner tools build their one reorder on this primitive (brief 22c, rule A3). Package 11 ran it
over a pair only. This probe walks all six orders of the newer AresOS (R27), the older one (R13)
and the pinned stock (S) in a VM, starts every order once with no choice, and takes one other row
in the boot menu. It changes nothing but the order. Every capture is saved as the guest gave it,
every expectation of the brief (P6) is recorded as met or contradicted, and the caller fails the
run at the end when one was contradicted, so that one run shows all of them.
"""
import pathlib
import re
import shlex
import subprocess
import time

import two_disk_vm as td
import switch_vm as sw
import keyboard_vm as kb
import keyboard_entries as ke
from grub_bls import stock_bls_entry, StockSelectionError

START = ('R27', 'R13', 'S')
# Moving these rows to the front in turn visits all six orders and ends at the start.
MOVES = ('S', 'R27', 'R13', 'S', 'R13', 'R27')
ORDERS = (('S', 'R27', 'R13'), ('R27', 'S', 'R13'), ('R13', 'R27', 'S'),
          ('S', 'R13', 'R27'), ('R13', 'S', 'R27'), ('R27', 'R13', 'S'))
# What a reorder must never change in a deployment (rpm-ostree's own fields).
STABLE = ('checksum', 'serial', 'osname', 'container-image-reference', 'container-image-reference-digest',
          'pinned', 'unlocked', 'version', 'timestamp')
MENU_DEADLINE = 50  # GRUB's shown-once menu waits 60 seconds for a key

# Read-only, as root: how /boot and the deployment links stand, which row the kernel was started
# with, where ostree keeps the pin (the origin files), and ostree's own list.
LAYOUT = r'''import json,os,pathlib,subprocess
root=pathlib.Path('/')
def run(*argv):
    done=subprocess.run(argv,capture_output=True,text=True)
    return dict(argv=list(argv),returncode=done.returncode,stdout=done.stdout,stderr=done.stderr)
boot,ostree=root/'boot',root/'sysroot/ostree'
args=(root/'proc/cmdline').read_text().split()
target,=[a.split('=',1)[1] for a in args if a.startswith('ostree=')]
print(json.dumps(dict(
    boot_id=(root/'proc/sys/kernel/random/boot_id').read_text().strip(),
    cmdline=' '.join(args),running_link=target,
    running='/'+str((root/'sysroot'/target.lstrip('/')).resolve(strict=True).relative_to(root.resolve())),
    loader_link=os.readlink(boot/'loader') if (boot/'loader').is_symlink() else None,
    loader_directories={p.name:sorted(e.name for e in (p/'entries').iterdir())
        for p in sorted(boot.glob('loader*')) if (p/'entries').is_dir()},
    ostree_boot_links={p.name:os.readlink(p) for p in sorted(ostree.glob('boot.*')) if p.is_symlink()},
    ostree_boot_targets={str(p.relative_to(ostree)):os.readlink(p)
        for p in sorted(ostree.glob('boot.*/*/*/*')) if p.is_symlink()},
    origins={p.name:p.read_text() for p in sorted(ostree.glob('deploy/*/deploy/*.origin'))},
    admin_status=run('ostree','admin','status'),
    grubenv=run('grub2-editenv','-','list'),
    packages=run('rpm','-q','ostree','rpm-ostree','bootc','grub2-common'))))
'''

# ostree's own journal lines of this boot about a deployment list write.
JOURNAL = r'''import json,subprocess
FIELDS=('MESSAGE','MESSAGE_ID','SYSLOG_IDENTIFIER','_COMM','_PID','_UID','PRIORITY','__REALTIME_TIMESTAMP','__MONOTONIC_TIMESTAMP')
rows=[]
reader=subprocess.Popen(['journalctl','-b','-o','json','--no-pager'],stdout=subprocess.PIPE,text=True,errors='replace')
for line in reader.stdout:
    if 'bootconfig swap' not in line: continue
    entry=json.loads(line)
    if isinstance(entry.get('MESSAGE'),str) and 'bootconfig swap' in entry['MESSAGE']:
        rows.append({k:v for k,v in entry.items() if k in FIELDS or k.startswith('OSTREE_')})
assert reader.wait()==0
print(json.dumps(rows))
'''


def set_default_program(index):
    """The one changing command, plain and as root; its output and exit status come back as JSON."""
    assert type(index) is int and index > 0, 'STOP: the target is already first or the index is invalid'
    argv = ['ostree', 'admin', 'set-default', str(index)]
    return ('import json,subprocess\nargv=' + repr(argv) + '\ndone=subprocess.run(argv,capture_output=True,text=True)\n'
            'print(json.dumps(dict(argv=argv,returncode=done.returncode,stdout=done.stdout,stderr=done.stderr)))\n')


def moved(order, role):
    """Rule 3's postcondition: the target first, the others in their old relative order."""
    assert role in order
    return [role] + [other for other in order if other != role]


def swap_lines(text):
    return re.findall(r'bootconfig swap: (yes|no)', text)


def without_link(options):
    return [word for word in shlex.split(options) if not word.startswith('ostree=')]


def observe(roles, snapshot, layout):
    """One stage's facts by role (R27, R13, S), read from the raw captures."""
    rows = snapshot['rpm']['deployments']
    identities = [ke.key(row) for row in rows]
    assert all(identity in roles for identity in identities) and len(set(identities)) == len(identities), \
        'STOP: a deployment is none of the three installed systems, or is listed twice'
    order = [roles[identity] for identity in identities]
    running = [roles[ke.key(row)] for row in rows if row['booted']]
    assert len(running) == 1, 'STOP: not exactly one running deployment'
    status = snapshot['bootc']['status']

    def slot(value):
        if not value:
            return None
        tree = value['ostree']
        return roles.get((tree['checksum'], tree['deploySerial'], tree['stateroot']), 'unknown')
    entries = []
    for entry in snapshot['bls']:
        text = entry['content']
        titles, options = re.findall(r'^title (.+)$', text, re.M), re.findall(r'^options (.+)$', text, re.M)
        versions = re.findall(r'^version (.+)$', text, re.M)
        assert len(titles) == 1 and len(options) == 1, 'STOP: a boot entry without exactly one title and options line'
        number = re.fullmatch(r'.*\(ostree:([0-9]+)\)', titles[0])
        file = pathlib.PurePosixPath(entry['file']).name
        position = re.fullmatch(r'ostree-([0-9]+)\.conf', file)
        entries.append(dict(file=file, file_number=int(position[1]) if position else None,
                            role=roles.get(ke.entry_identity(entry['deployment']), 'unknown'),
                            title=titles[0], title_index=int(number[1]) if number else None,
                            version=versions[0] if len(versions) == 1 else None, options=options[0],
                            kernel=re.findall(r'^linux (.+)$', text, re.M), initrd=re.findall(r'^initrd (.+)$', text, re.M)))
    # GRUB's blscfg lists the entries by file name, numerically descending (package 11l's rule).
    numbered = all(entry['file_number'] is not None for entry in entries)
    menu = sorted(entries, key=lambda entry: entry['file_number'], reverse=True) if numbered else entries
    origins = {}
    for name, text in layout['origins'].items():
        match = re.fullmatch(r'([0-9a-f]{64})\.([0-9]+)\.origin', name)
        role = next((role for identity, role in roles.items() if match and identity[:2] == (match[1], int(match[2]))), name)
        origins[role] = bool(re.search(r'^pinned\s*=\s*true$', text, re.M))
    return dict(
        order=order, running=running[0], pinned=[roles[ke.key(row)] for row in rows if row['pinned']],
        staged=[roles[ke.key(row)] for row in rows if row.get('staged')], transaction=snapshot['rpm']['transaction'],
        stable={roles[ke.key(row)]: {field: row.get(field) for field in STABLE} for row in rows},
        bootc=dict(booted=slot(status.get('booted')), rollback=slot(status.get('rollback')), staged=slot(status.get('staged')),
                   rollback_queued=status.get('rollbackQueued'),
                   boot_order=(snapshot['bootc'].get('spec') or {}).get('bootOrder')),
        entries=menu, entries_numbered=numbered, menu_order=[entry['role'] for entry in menu],
        title_indexes={entry['role']: entry['title_index'] for entry in menu},
        titles_name_the_place=all(entry['title_index'] == order.index(entry['role']) for entry in menu if entry['role'] in order),
        options={entry['role']: without_link(entry['options']) for entry in menu},
        running_link=layout['running_link'],
        running_by_kernel_argument=next((role for identity, role in roles.items()
                                         if layout['running'].endswith('/' + identity[2] + '/deploy/' + identity[0] + '.' + str(identity[1]))), 'unknown'),
        origin_pins=origins, boot_id=layout['boot_id'], loader_link=layout['loader_link'],
        ostree_boot_links=layout['ostree_boot_links'])


class Probe:
    """The walk's record: one row per stage, and every expectation as met or contradicted."""

    def __init__(self, rows):
        # rows: role -> (checksum, serial, stateroot), from package 27's route.
        assert sorted(rows) == sorted(START) and len(set(rows.values())) == 3, 'STOP: the three systems are not distinct'
        self.roles = {tuple(identity): role for role, identity in rows.items()}
        self.stages, self.expectations = [], []
        self.reference = None
        self.last = None
        self.swaps = []

    def expect(self, stage, point, met, detail=None):
        self.expectations.append(dict(stage=stage, point=point, met=bool(met), detail=detail))
        if not met:
            print(f'REORDER PROBE CONTRADICTION at {stage}: {point}: {detail}', flush=True)
        return bool(met)

    def contradicted(self):
        return [row for row in self.expectations if not row['met']]

    def capture(self, guest, stage, reached, running=None, order=None):
        """Capture a stage; `running` and `order` are what the brief expects there (roles), when it says."""
        snapshot = kb.deployment_snapshot(guest, stage)
        layout = guest.capture_json(stage + '-layout', sw.framed('python3 -c ' + shlex.quote(LAYOUT)))
        facts = observe(self.roles, snapshot, layout)
        facts.update(stage=stage, reached=reached)
        if self.reference is None:
            self.reference = facts
        first = self.reference
        self.expect(stage, 'nothing is created, removed or staged, and no transaction is open',
                    sorted(facts['order']) == sorted(START) and not facts['staged'] and facts['transaction'] is None
                    and facts['bootc']['staged'] is None, dict(order=facts['order'], staged=facts['staged']))
        self.expect(stage, 'every deployment keeps its identity, reference, digest and flags', facts['stable'] == first['stable'],
                    {role: value for role, value in facts['stable'].items() if value != first['stable'].get(role)})
        self.expect(stage, 'only the stock is pinned', facts['pinned'] == ['S'], facts['pinned'])
        self.expect(stage, 'one boot entry per deployment', sorted(facts['menu_order']) == sorted(START), facts['menu_order'])
        self.expect(stage, "the stock's boot options stay the same", facts['options'].get('S') == first['options'].get('S'),
                    dict(now=facts['options'].get('S'), first=first['options'].get('S')))
        self.expect(stage, 'rpm-ostree, bootc and the kernel argument name the same running row',
                    facts['running'] == facts['bootc']['booted'] == facts['running_by_kernel_argument'],
                    dict(rpm=facts['running'], bootc=facts['bootc']['booted'], kernel=facts['running_by_kernel_argument']))
        others = [role for role in facts['order'] if role != facts['running']]
        self.expect(stage, "bootc's rollback slot is the first other deployment", facts['bootc']['rollback'] == others[0],
                    dict(rollback=facts['bootc']['rollback'], order=facts['order'], running=facts['running']))
        slot = facts['bootc']['rollback']
        queued = slot in facts['order'] and facts['order'].index(slot) < facts['order'].index(facts['running'])
        self.expect(stage, "rollbackQueued is true exactly when bootc's rollback slot comes before the running row",
                    facts['bootc']['rollback_queued'] is queued, dict(rollbackQueued=facts['bootc']['rollback_queued'],
                    rollback=slot, order=facts['order'], running=facts['running']))
        if order is not None:
            self.expect(stage, 'the order is the one the walk names', facts['order'] == list(order),
                        dict(order=facts['order'], named=list(order)))
        if running is not None:
            self.expect(stage, 'the expected row runs', facts['running'] == running, dict(running=facts['running'], expected=running))
        # Reported, not judged (P6: "report also"): the titles' numbers, the menu order, the other rows' options.
        facts['other_options_unchanged'] = {role: facts['options'].get(role) == first['options'].get(role) for role in ('R27', 'R13')}
        facts['menu_order_is_list_order'] = facts['menu_order'] == facts['order']
        self.stages.append(facts)
        self.last = facts
        td.save(stage + '-observed', facts)
        return facts, snapshot

    def restarted(self, guest, stage, reached, running):
        """After a restart: the list is as it was left, and the named row runs."""
        before = self.last
        facts, snapshot = self.capture(guest, stage, reached, running=running)
        self.expect(stage, 'a restart leaves the order as it was', facts['order'] == before['order'],
                    dict(before=before['order'], after=facts['order']))
        self.expect(stage, 'the restart is a new boot', facts['boot_id'] != before['boot_id'], None)
        return facts, snapshot

    def move(self, guest, stage, role, snapshot):
        """Plain `ostree admin set-default <index>`; the index is found by checksum and serial in the
        list this boot's capture just read (`snapshot`)."""
        before = self.last
        assert before is not None and [self.roles[ke.key(row)] for row in snapshot['rpm']['deployments']] == before['order']
        identity = next(identity for identity, name in self.roles.items() if name == role)
        index, = [number for number, row in enumerate(snapshot['rpm']['deployments']) if ke.key(row) == identity]
        journal = lambda name: guest.capture_json(name, sw.framed('python3 -c ' + shlex.quote(JOURNAL)))
        earlier = journal(stage + '-journal-before')
        done = guest.capture_json(stage + '-set-default', sw.framed('python3 -c ' + shlex.quote(set_default_program(index))))
        later = journal(stage + '-journal-after')
        after, _ = self.capture(guest, stage, f'ostree admin set-default {index} ({role} to the front)')
        self.expect(stage, 'set-default exits 0', done['returncode'] == 0, dict(returncode=done['returncode'], stderr=done['stderr'][-400:]))
        self.expect(stage, 'set-default puts the target first and keeps the others in their old relative order',
                    after['order'] == moved(before['order'], role), dict(before=before['order'], after=after['order'], target=role))
        self.expect(stage, 'a reorder leaves the running row running', after['running'] == before['running'],
                    dict(before=before['running'], after=after['running']))
        self.expect(stage, 'a reorder is not a new boot', after['boot_id'] == before['boot_id'], None)
        printed, logged = swap_lines(done['stdout']), [line for row in later[len(earlier):] for line in swap_lines(row['MESSAGE'])]
        self.expect(stage, 'ostree prints and logs one bootconfig swap line for the move',
                    len(printed) == 1 and logged == printed and later[:len(earlier)] == earlier,
                    dict(printed=printed, logged=logged, lines_before=len(earlier), lines_after=len(later)))
        swap = dict(stage=stage, target=role, index=index, before=before['order'], after=after['order'],
                    bootconfig_swap=printed[0] if len(printed) == 1 else None, stdout=done['stdout'].strip(),
                    journal=[row['MESSAGE'] for row in later[len(earlier):]],
                    loader_link=dict(before=before['loader_link'], after=after['loader_link']),
                    ostree_boot_links=dict(before=before['ostree_boot_links'], after=after['ostree_boot_links']),
                    entry_files_changed={e['file']: (e['title'], e['options']) for e in after['entries']}
                    != {e['file']: (e['title'], e['options']) for e in before['entries']})
        after['swap'] = swap
        self.swaps.append(swap)
        td.save(stage + '-swap', swap)
        return after

    def result(self, **more):
        table = [dict(stage=row['stage'], reached=row['reached'], order=row['order'], running=row['running'],
                      bootc_booted=row['bootc']['booted'], bootc_rollback=row['bootc']['rollback'],
                      rollback_queued=row['bootc']['rollback_queued'], boot_order=row['bootc']['boot_order'],
                      pinned=row['pinned'], origin_pins=row['origin_pins'],
                      titles=[dict(file=entry['file'], title=entry['title'], role=entry['role']) for entry in row['entries']],
                      titles_name_the_place=row['titles_name_the_place'], menu_order_is_list_order=row['menu_order_is_list_order'],
                      other_options_unchanged=row['other_options_unchanged'],
                      bootconfig_swap=(row.get('swap') or {}).get('bootconfig_swap')) for row in self.stages]
        contradicted = self.contradicted()
        return dict(status='contradicted' if contradicted else 'passed', stages=table, swaps=self.swaps,
                    expectations=dict(checked=len(self.expectations), contradicted=contradicted),
                    orders_seen=[row['order'] for row in self.stages if row.get('swap')], **more)


def start_at_menu(password, hashed, stage):
    """The next start, stopped before any login: the boot menu comes first."""
    td.Guest.mode, td.Guest.boot_purpose = 'installed', stage
    return td.Guest(td.WORK / 'target.raw', password, [password, hashed])


def recorded_stock_entry(guest, stage, snapshot, stock_checksum):
    """The stock row's place in the menu, found through its boot entry (package 11's rule, any number of rows)."""
    entries = guest.capture_json(stage + '-bls-entries', sw.framed(td.bls_inventory_command()))
    try:
        backup = stock_bls_entry(entries, stock_checksum, snapshot['rpm']['deployments'])
    except StockSelectionError as error:
        td.save(stage + '-recorded-stock-entry', dict(status='blocked', reason=str(error), entries=entries))
        return None, str(error), entries
    td.save(stage + '-recorded-stock-entry', backup)
    return backup, None, entries


def show_menu_once(guest, stage):
    # Fedora's menu_show_once shows the menu at the next start only (package 11, verified there).
    guest.command(stage + '-show-menu-once', 'set -e; grub2-editenv - set menu_show_once=1; grub2-editenv - list')


def read_screen(guest, name):
    """The screen as text (package 11's OCR of a QMP screenshot)."""
    guest.screenshot(name)
    ocr = subprocess.check_output(['tesseract', str(td.EVIDENCE / (name + '.png')), 'stdout', '--psm', '6'],
                                  stderr=subprocess.DEVNULL).decode()
    (td.EVIDENCE / (name + '-ocr.txt')).write_text(ocr)
    return ocr


def menu_choice(guest, backup, stage):
    """Read the menu from the screen and take the stock row only when its rows read as recorded."""
    deadline, attempt, last = time.monotonic() + MENU_DEADLINE, 0, None
    while time.monotonic() < deadline:
        attempt += 1
        name = f'{stage}-attempt-{attempt:02}'
        ocr = read_screen(guest, name)
        lines = [re.sub(r'\s+', ' ', line.strip()) for line in ocr.splitlines() if re.search(r'Bazzite.*ostree', line, re.I)]
        if not lines:
            time.sleep(1)
            continue
        if lines != last:
            # The same rows twice: the menu is drawn completely.
            last = lines
            time.sleep(0.3)
            continue
        try:
            td.select_grub_menu(guest, backup, ocr)
        except StockSelectionError as error:
            return dict(selected=False, frame=name, lines=lines, reason=str(error))
        return dict(selected=True, frame=name, lines=lines, keys=['home'] + ['down'] * backup['menu_index'] + ['ret'])
    return dict(selected=False, reason='no boot menu was read before the deadline', frames=attempt)


def one_time_entry(guest, stage, entry):
    """Package 11's permitted fallback when the menu cannot be driven: start one entry once, by its id."""
    assert re.fullmatch(r'ostree-[1-9][0-9]*', entry), 'STOP: unexpected boot entry id'
    guest.command(stage + '-one-time-entry', 'set -e; grub2-reboot ' + shlex.quote(entry) + '; grub2-editenv - list')
