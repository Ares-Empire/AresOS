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
        if (device / 'name').read_text().strip() != 'QEMU QEMU USB Keyboard': continue
        ident = tuple(int((device / 'id' / name).read_text(), 16) for name in ('bustype','vendor','product'))
        if ident != (3, 0x0627, 1): continue
        bits = 0
        for word in (device / 'capabilities/key').read_text().split(): bits = (bits << 64) | int(word, 16)
        assert all(bits & (1 << code) for code in (28,30,42,44)), 'Unexpected keyboard capabilities'
        matches.append('/dev/input/' + event.name)
    assert len(matches) == 1, 'No unique qualified QEMU USB keyboard'
    return matches[0]


def settings(fd):
    import array, fcntl
    ident = array.array('H', [0]*4)
    fcntl.ioctl(fd, 0x80084502, ident, True)  # EVIOCGID, linux/input.h
    assert tuple(ident[:3]) == (3,0x0627,1), 'Opened input device changed'
    repeat = array.array('I', [0,0])
    fcntl.ioctl(fd, 0x80084503, repeat, True)  # EVIOCGREP: read, never set.
    pressed = bytearray(96)  # EVIOCGKEY, KEY_MAX=0x2ff; count only, never retain the bitmap.
    fcntl.ioctl(fd, 0x80604518, pressed, True)
    assert not any(pressed), 'Keyboard still has pressed keys before typing window'
    return dict(delay_ms=repeat[0], period_ms=repeat[1])


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


def observe(fd, path, repeat, max_seconds=180):
    import select
    counts = dict(press=0,release=0,repeat=0,syn_dropped=0)
    result = dict(status='stopped', counts_only=True, autorepeat=repeat, counts=counts,
        codes_recorded=False, values_recorded=False)
    start = time.monotonic(); stopped = None; quiet = start; dropping = False
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
            if stopped is not None and (time.monotonic()-quiet >= .5 or time.monotonic()-stopped >= 2):
                result['status'] = 'passed'; break
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
    fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY)
    assert stat.S_ISCHR(os.fstat(fd).st_mode)
    try: repeat = settings(fd)
    except BaseException: os.close(fd); raise
    path = pathlib.Path(tempfile.mkdtemp(prefix='ares-input-',dir='/run')); private_root(path)
    pid = os.fork()
    if pid == 0:
        try:
            os.setsid()
            null = os.open('/dev/null',os.O_RDWR)
            for target in (0,1,2): os.dup2(null,target)
            os.closerange(3,fd); os.closerange(fd+1,65536)
            observe(fd,path,repeat)
        finally: os._exit(0)
    os.close(fd)
    deadline = time.monotonic()+5
    while not (path/'ready.json').exists() and time.monotonic()<deadline:
        assert not (path/'result.json').exists(), 'Keyboard counter failed before ready'
        time.sleep(.05)
    assert (path/'ready.json').exists(), 'Keyboard counter readiness deadline'
    return dict(status='ready',path=str(path),pid=pid,device=device,autorepeat=repeat,counts_only=True)


def finish(ticket):
    path = pathlib.Path(ticket['path']); private_root(path)
    (path/'stop').touch(mode=0o600,exist_ok=False)
    deadline = time.monotonic()+5
    while not (path/'result.json').exists() and time.monotonic()<deadline: time.sleep(.05)
    assert (path/'result.json').exists(), 'Keyboard counter finish deadline'
    result = json.loads((path/'result.json').read_text())
    result.update(device=ticket['device'],pid=ticket['pid'])
    assert {p.name for p in path.iterdir()} == {'ready.json','stop','result.json'}, 'Unexpected counter files'
    for name in ('ready.json','stop','result.json'): (path/name).unlink()
    path.rmdir()
    return result


def source(ticket=None):
    functions = (keyboard,settings,count_events,private_root,publish,observe,start,finish)
    return ('import json,os,pathlib,re,time\n# hidden-key-counter\n' + ''.join(inspect.getsource(f) for f in functions)
        + '\nprint(json.dumps(' + ('start()' if ticket is None else 'finish('+repr(ticket)+')') + '))\n')


def compare(received, sent):
    counts = received['counts']
    return dict(sent_events=sent['key_event_count'],received_events=counts['press']+counts['release'],
        press=counts['press'],release=counts['release'],repeat=counts['repeat'],syn_dropped=counts['syn_dropped'],
        matches=received['complete'] and counts['repeat']==0 and counts['press']==counts['release']
            and counts['press']*2==sent['key_event_count'])
