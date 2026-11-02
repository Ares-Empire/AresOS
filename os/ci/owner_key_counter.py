"""Guest evdev observer: aggregate counts only; never grab, log or replay keys."""
import inspect
import json
import os
import pathlib
import re
import time


def keyboard(sysroot=pathlib.Path('/sys/class/input')):
    matches = []
    for event in sysroot.glob('event[0-9]*'):
        device = event / 'device'
        if (device / 'name').read_text().strip() != 'AT Translated Set 2 keyboard': continue
        ident = tuple(int((device / 'id' / name).read_text(), 16) for name in ('bustype','vendor','product'))
        if ident != (0x11, 1, 1): continue  # BUS_I8042, atkbd translated set 2.
        bits = 0
        for word in (device / 'capabilities/key').read_text().split(): bits = (bits << 64) | int(word, 16)
        assert all(bits & (1 << code) for code in (28,30,42,44)), 'Unexpected keyboard capabilities'
        matches.append('/dev/input/' + event.name)
    assert len(matches) == 1, 'No unique qualified i8042 AT keyboard'
    return matches[0]


def settings(fd, device):
    import array, fcntl
    ident = array.array('H', [0]*4)
    fcntl.ioctl(fd, 0x80084502, ident, True)  # EVIOCGID, linux/input.h
    assert tuple(ident[:3]) == (0x11,1,1), 'Opened input device changed'
    repeat = array.array('I', [0,0])
    fcntl.ioctl(fd, 0x80084503, repeat, True)  # EVIOCGREP: read, never set.
    assert released(device), 'Keyboard still has pressed keys before typing window'
    return dict(delay_ms=repeat[0], period_ms=repeat[1])


def released(device):
    import fcntl
    pressed = bytearray(96)  # EVIOCGKEY getter; discard the bitmap, export only a Boolean.
    # A fresh open is a different evdev client. EVIOCGKEY flushes the queried
    # client's queued EV_KEY events, so never issue it on an event-reading fd.
    fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY)
    try: fcntl.ioctl(fd, 0x80604518, pressed, True)
    finally: os.close(fd)
    return not any(pressed)


def at_mapping(fd, expected):
    import array, fcntl
    for index, code in expected.items():
        pair = array.array('I', [index, 0])
        fcntl.ioctl(fd, 0x80084504, pair, True)  # EVIOCGKEYCODE: static mapping getter.
        assert tuple(pair) == (index, code), 'STOP: AT keyboard keycode mapping differs'
    return len(expected)


def count_events(data, counts, dropping=False):
    import struct
    event = struct.Struct('@llHHi')
    assert event.size == 24 and len(data) % event.size == 0, 'Malformed x86-64 input events'
    for _, _, kind, code, value in event.iter_unpack(data):
        if kind == 0 and code == 3:  # SYN_DROPPED: counts cannot establish completeness.
            counts['syn_dropped'] += 1; dropping = True
        elif dropping:
            if kind == 0 and code == 0: dropping = False
        elif kind == 1:
            assert value in (0,1,2), 'Unexpected EV_KEY state'
            counts[('release','press','repeat')[value]] += 1
    return dropping


def private_root(path):
    import stat
    assert re.fullmatch(r'/run/ares-input-[a-z0-9_]{8}', str(path)), 'Unexpected counter path'
    info = path.lstat()
    assert not path.is_symlink() and stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o700


def publish(path, value):
    # Every byte written is schema-controlled aggregate data, never input events.
    temporary = path.with_name(path.name + '.part')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream: json.dump(value, stream)
    temporary.replace(path)


def observe(fd, path, repeat, max_seconds=180, *, device):
    import select
    counts = dict(press=0,release=0,repeat=0,syn_dropped=0)
    result = dict(status='stopped', counts_only=True, autorepeat=repeat, counts=counts,
        codes_recorded=False, values_recorded=False)
    start = time.monotonic(); stopped = None; quiet = start; dropping = False
    sample = None; requested = None; sequence = 0
    try:
        # A new evdev client starts empty. Drain only pre-window events, then ACK.
        drain_deadline = time.monotonic()+2
        while select.select([fd], [], [], 0)[0]:
            assert os.read(fd,24*256), 'Input device closed before counter window'
            assert time.monotonic()<drain_deadline, 'Pre-window event drain deadline'
        publish(path/'ready.json', dict(status='ready',counts_only=True))
        while time.monotonic()-start < max_seconds:
            now = time.monotonic()
            if (path/'stop').exists() and stopped is None: stopped = now
            if select.select([fd], [], [], .05)[0]:
                data = os.read(fd, 24*256)
                assert data, 'Input device closed'
                dropping = count_events(data, counts, dropping); quiet = time.monotonic()
            requests = list(path.glob('sample-*.request'))
            assert len(requests) <= 1, 'Concurrent counter checkpoints refused'
            if requests and requested is None:
                match = re.fullmatch(r'sample-([1-9][0-9]?)\.request', requests[0].name)
                assert match and int(match[1]) == sequence+1 <= 64, 'Counter checkpoint sequence refused'
                sample = requests[0]; requested = now
            quiet_now = time.monotonic()-quiet >= .5
            keys_up = quiet_now and released(device)
            if requested is not None and (keys_up or now-requested >= 5):
                sequence += 1
                publish(path/('sample-'+str(sequence)+'.json'), dict(status='passed' if keys_up else 'stopped',
                    sequence=sequence, counts_only=True, counts=dict(counts), keys_released=keys_up,
                    complete=keys_up and counts['syn_dropped']==0, codes_recorded=False, values_recorded=False))
                sample.unlink(); sample = requested = None
            if stopped is not None and (keys_up or now-stopped >= 2):
                result.update(status='passed' if keys_up else 'stopped',keys_released=keys_up)
                break
        else: result['error'] = 'Counter typing-window deadline'
    except (OSError,AssertionError) as error:
        result['error'] = type(error).__name__  # Never include event data/exception text.
    finally:
        os.close(fd)
        result['seconds'] = round(time.monotonic()-start, 3)
        result['complete'] = result['status']=='passed' and counts['syn_dropped']==0
        publish(path/'result.json', result)


def start():
    import tempfile, stat
    assert os.geteuid() == 0
    device = keyboard()
    query = os.open(device, os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY)
    try:
        assert stat.S_ISCHR(os.fstat(query).st_mode)
        repeat = settings(query, device)
    finally: os.close(query)
    # The counting client has no ioctl/getter calls during its entire lifetime.
    fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY)
    assert stat.S_ISCHR(os.fstat(fd).st_mode)
    path = pathlib.Path(tempfile.mkdtemp(prefix='ares-input-',dir='/run')); private_root(path)
    pid = os.fork()
    if pid == 0:
        try:
            os.setsid()
            null = os.open('/dev/null',os.O_RDWR)
            for target in (0,1,2): os.dup2(null,target)
            os.closerange(3,fd); os.closerange(fd+1,65536)
            observe(fd,path,repeat,device=device)
        finally: os._exit(0)
    os.close(fd)
    deadline = time.monotonic()+5
    while not (path/'ready.json').exists() and time.monotonic()<deadline:
        assert not (path/'result.json').exists(), 'Keyboard counter failed before ready'
        time.sleep(.05)
    assert (path/'ready.json').exists(), 'Keyboard counter readiness deadline'
    return dict(status='ready',path=str(path),pid=pid,device=device,autorepeat=repeat,counts_only=True)


def checkpoint(ticket, sequence):
    path = pathlib.Path(ticket['path']); private_root(path)
    assert type(sequence) is int and 1 <= sequence <= 64
    target = path/('sample-'+str(sequence)+'.json')
    assert not target.exists(), 'Counter checkpoint already consumed'
    (path/('sample-'+str(sequence)+'.request')).touch(mode=0o600,exist_ok=False)
    deadline = time.monotonic()+7
    while not target.exists() and time.monotonic()<deadline:
        assert not (path/'result.json').exists(), 'Counter ended before checkpoint'
        time.sleep(.05)
    assert target.exists(), 'Counter checkpoint deadline'
    result = json.loads(target.read_text())
    assert result['sequence']==sequence, 'Counter checkpoint identity changed'
    return result


def finish(ticket):
    path = pathlib.Path(ticket['path']); private_root(path)
    (path/'stop').touch(mode=0o600,exist_ok=False)
    deadline = time.monotonic()+5
    while not (path/'result.json').exists() and time.monotonic()<deadline: time.sleep(.05)
    assert (path/'result.json').exists(), 'Keyboard counter finish deadline'
    result = json.loads((path/'result.json').read_text())
    result.update(device=ticket['device'],pid=ticket['pid'])
    names = {p.name for p in path.iterdir()}
    assert {'ready.json','stop','result.json'} <= names
    assert all(name in ('ready.json','stop','result.json') or re.fullmatch(r'sample-[1-9][0-9]?\.(?:json|request)',name)
        for name in names), 'Unexpected counter files'
    if any(name.endswith('.request') for name in names): result.update(status='stopped',complete=False,unfinished_checkpoint=True)
    for name in names: (path/name).unlink()
    path.rmdir()
    return result


def source(ticket=None, sequence=None):
    functions = (keyboard,settings,released,count_events,private_root,publish,observe,start,checkpoint,finish)
    call = ('start()' if ticket is None else 'checkpoint('+repr(ticket)+','+repr(sequence)+')'
        if sequence is not None else 'finish('+repr(ticket)+')')
    return ('import json,os,pathlib,re,time\n# hidden-key-counter\n' + ''.join(inspect.getsource(f) for f in functions)
        + '\nprint(json.dumps(' + call + '))\n')


def compare(received, sent):
    counts = received['counts']
    return dict(sent_events=sent['key_event_count'],received_events=counts['press']+counts['release'],
        press=counts['press'],release=counts['release'],repeat=counts['repeat'],syn_dropped=counts['syn_dropped'],
        matches=received['complete'] and counts['repeat']==0 and counts['press']==counts['release']
            and counts['press']*2==sent['key_event_count'])


def delta(received, before):
    counts = {key:received['counts'][key]-before.get(key,0) for key in ('press','release','repeat','syn_dropped')}
    assert all(type(v) is int and v>=0 for v in counts.values()), 'Counter moved backwards'
    return dict(received,counts=counts)
