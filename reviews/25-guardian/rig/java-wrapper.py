#!/usr/bin/python3
# DEVELOPMENT AID of package 25 (the real-game check), headless use only.
"""check.sh installs this as bin/java of a folder that otherwise links to the real JDK, so Gradle takes the folder
for a JDK (package 49b's java-wrapper.sh, in Python). Anything but the game (Gradle's probe) runs plainly.

For the game (Loom's dev launcher) it stands in for Prism's wrapper, os/config/usr/libexec/aresos-desktop-java,
which cannot run here (it starts only through a supervisor that started Prism):

  - the game's JVM runs in a systemd user scope of the run's own, with MemoryHigh, as the supervisor starts it;
  - only the JVM's own command line gets XDG_RUNTIME_DIR set to the run's temporary runtime folder, and, for a run
    that checks the close, the gate ARESOS_DESKTOP_LIFECYCLE=1 (brief, Acceptance). The session's XDG_RUNTIME_DIR
    never reaches the JVM, so the mod can only ever dial the test supervisor's socket;
  - it holds the desktop lock of that runtime folder as the real wrapper does (flock, inherited by Java);
  - it stays Java's parent, so Java's real exit status is known, and writes it down with the real wrapper's own
    functions: the exit record (write_exit, end_report) and the report to the supervisor (report_again).

What it needs comes from ../../private/wrapper.json (check.py prepare), never from the environment."""
import fcntl
import importlib.machinery
import json
import os
import signal
import subprocess
import sys
import time
import types

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
RIG = os.path.dirname(os.path.dirname(HERE))
SCOPE_WAIT = 15.0


def is_game(arguments):
    for argument in arguments:
        if 'devlaunchinjector' in argument:
            return True
        if argument.startswith('@') and os.access(argument[1:], os.R_OK):
            with open(argument[1:], encoding='utf-8', errors='replace') as source:
                if 'devlaunchinjector' in source.read():
                    return True
    return False


def real_wrapper(path):
    loader = importlib.machinery.SourceFileLoader('aresos_desktop_java', path)
    module = types.ModuleType(loader.name)
    loader.exec_module(module)
    return module


def note(name, data):
    """A small file for check.py, written whole."""
    path = os.path.join(RIG, 'private', name)
    with open(path + '.new', 'w', encoding='utf-8') as output:
        json.dump(data, output)
    os.replace(path + '.new', path)


def main(arguments):
    with open(os.path.join(RIG, 'private', 'wrapper.json'), encoding='utf-8') as source:
        config = json.load(source)
    java = config['java']
    if not is_game(arguments):
        os.execv(java, [java, *arguments])
    wrapper = real_wrapper(config['wrapper'])
    runtime = config['runtime']
    folder = os.path.join(runtime, 'aresos')
    os.makedirs(folder, mode=0o700, exist_ok=True)
    lock = os.open(os.path.join(folder, 'desktop.lock'), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print('java-wrapper.py: this run\'s desktop lock is held already', file=sys.stderr)
        return wrapper.BUSY
    settings = [f'--setenv=XDG_RUNTIME_DIR={runtime}']
    if config['gate']:
        settings.append('--setenv=ARESOS_DESKTOP_LIFECYCLE=1')
    unit = config['unit']
    child = subprocess.Popen(['/usr/bin/systemd-run', '--user', '--scope', '--collect', '--quiet', f'--unit={unit}',
                              f'--property=MemoryHigh={config["memory_high"]}', *settings, '--', java, *arguments],
                             pass_fds=(lock,))
    sent = []
    for signum in wrapper.FORWARDED:
        signal.signal(signum, lambda number, frame: wrapper.send(child, number, sent))
    # systemd-run creates the scope, then becomes Java in it: the PID is the JVM's once it is there.
    deadline = time.monotonic() + SCOPE_WAIT
    while not wrapper.in_unit(child.pid, unit) and child.poll() is None and time.monotonic() < deadline:
        time.sleep(0.05)
    ticks = wrapper.start_ticks(child.pid)
    if child.poll() is None and wrapper.in_unit(child.pid, unit):
        note('jvm.json', {'pid': child.pid, 'ticks': ticks})
    status = child.wait()
    ended = time.monotonic_ns()
    # The facts, as the real wrapper records and reports them: Java's real status, bound to the launch and process.
    facts, message = wrapper.end_report(config['launch'], config['instance'], None, status, child.pid, ticks, sent)
    try:
        wrapper.write_exit(config['record'], facts)
    except OSError as error:
        print(f'java-wrapper.py: could not record how Java ended ({error})', file=sys.stderr)
    note('exit.json', {'pid': child.pid, 'status': status, 'ended_monotonic_ns': ended, 'sent': sent})
    wrapper.report_again(os.path.join(folder, 'desktop.sock'), message)
    return status if status >= 0 else 128 - status


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
