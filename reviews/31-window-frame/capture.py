#!/usr/bin/python3
"""Reproduce package 31's screenshots without reaching the owner's display.

Run from this worktree: python3 reviews/31-window-frame/capture.py
Needs the laptop's existing bwrap, labwc, foot, kwrite, Chrome, grim, wlr-randr,
Python GI/GTK4 and GLib tools. Writes only this worktree's .work/ and reviews/.
Each case runs the real aresos-session inside its own PID namespace and D-Bus,
with the real rc.xml and recovery command; only autostart becomes this fixture.
"""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
WORK = ROOT / '.work/31-window-frame'
CONFIG = ROOT / 'os/config'


def room():
    memory = subprocess.check_output(['free', '-g'], text=True)
    print(memory, flush=True)
    available = int(next(line for line in memory.splitlines() if line.startswith('Mem:')).split()[-1])
    games = []
    for process in Path('/proc').glob('[0-9]*'):
        try:
            exe = (process / 'exe').readlink()
            if '/.lunarclient/' in str(exe) and exe.name == 'java':
                games.append(process.name)
        except OSError:
            pass
    if available < 4 or games:
        print(f'Wait before retrying; available={available} GB, owner game PIDs={games}', flush=True)
        raise SystemExit(75)


def private_display():
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', '/')).resolve()
    if not runtime.is_relative_to(WORK.resolve()) or not os.environ.get('WAYLAND_DISPLAY'):
        raise SystemExit("Refusing display access outside this worktree's private runtime")


def gtk_window():
    private_display()
    import gi
    gi.require_version('Gtk', '4.0')
    from gi.repository import Gtk
    app = Gtk.Application(application_id='org.aresos.FrameHeaderTest')

    def activate(app):
        window = Gtk.ApplicationWindow(application=app, title='GTK4 header bar')
        window.set_default_size(740, 400)
        bar = Gtk.HeaderBar()
        bar.set_show_title_buttons(True)
        window.set_titlebar(bar)
        window.set_child(Gtk.Label(label='A program with its own header bar\n\nMinimize, maximize and close follow the AresOS desktop default.'))
        window.present()
    app.connect('activate', activate)
    app.run([])


def inside(case):
    private_display()
    from wayland_input import Input
    work = WORK / case
    os.chdir(work)
    log = open(work / 'apps.log', 'w')
    children = []

    def start(argv):
        child = subprocess.Popen(argv, stdout=log, stderr=log)
        children.append(child)
        return child

    def shot(name):
        time.sleep(1)
        subprocess.run(['/usr/bin/grim', '-o', 'HEADLESS-1', str(HERE / name)], check=True)

    try:
        subprocess.run(['/usr/bin/wlr-randr', '--output', 'HEADLESS-1', '--custom-mode', '1920x1080@60Hz'], check=True)
        inputs = Input()
        layout = subprocess.check_output(['/usr/bin/gsettings', 'get', 'org.gnome.desktop.wm.preferences', 'button-layout'], text=True).strip()
        print('XDG_CURRENT_DESKTOP=' + os.environ['XDG_CURRENT_DESKTOP'], 'button-layout=' + layout, flush=True)
        assert layout == "'appmenu:minimize,maximize,close'"
        font = subprocess.check_output(['/usr/bin/fc-match', 'Space Grotesk', '-f', '%{family}\n'], text=True).strip()
        print('FONT_MATCH=' + font, flush=True)
        assert ('Space Grotesk' in font) == (case != 'no-font')
        (work / 'sample.txt').write_text('AresOS window frame\n\nA sample note for the frame check.\nThe active window has a gold dot and a bright title.\nThe inactive window has a ring and a dim title.\n')
        start(['/usr/bin/kwrite', str(work / 'sample.txt')])
        time.sleep(3)
        start(['/usr/bin/foot', '--app-id=aresos.frame-test', '--title=AresOS frame check', '--window-size-pixels=740x380', '--font=monospace:size=14',
               '/usr/bin/bash', '--noprofile', '--norc', '-c', 'printf "AresOS frame check\\n\\nA private headless Wayland session at 1920x1080.\\nOnly sample text is shown here.\\n"; exec /usr/bin/bash --noprofile --norc'])
        time.sleep(3)
        inputs.roundtrip()
        print('WINDOWS=' + json.dumps(inputs.windows), flush=True)
        if case == 'normal':
            # Default placement is centered. Spread the two test windows so
            # both titles and both sets of sample text can be inspected.
            inputs.drag(900, 360, 1310, 520)
            inputs.drag(900, 300, 460, 200)
            inputs.activate('aresos.frame-test')
            shot('01-frame.png')
            inputs.modifiers(8)
            inputs.key(15)
            shot('02-alt-tab.png')
            inputs.modifiers(0)
            for child in children:
                child.terminate()
                child.wait(timeout=10)
            children.clear()
            (work / 'page.html').write_text('<!doctype html><title>AresOS browser check</title><style>body{font:24px sans-serif;padding:50px;background:#efede6;color:#1a1813}h1{font-size:38px}</style><h1>Chrome keeps its own bar</h1><p>Tabs and all three window buttons. No extra title bar.</p><p>A local sample page; no account or browsing history.</p>')
            start(['/usr/bin/google-chrome', '--user-data-dir=' + str(work / 'chrome'), '--ozone-platform=wayland', '--no-first-run', '--no-default-browser-check', '--disable-background-networking', '--disable-component-update', '--disable-sync', '--disable-gpu', '--window-size=1050,670', (work / 'page.html').as_uri()])
            time.sleep(8)
            shot('03-chrome.png')
            start(['/usr/bin/python3', str(__file__), '--gtk'])
            time.sleep(3)
            shot('04-gtk-header.png')
        else:
            # Use the unchanged binding, which executes the worktree's real
            # /usr/bin/aresos-terminal --recovery under the private namespace.
            inputs.modifiers(64 | 4)
            inputs.key(1)
            inputs.modifiers(0)
            time.sleep(3)
            inputs.roundtrip()
            assert any(w.get('title') == 'AresOS' for w in inputs.windows.values()), inputs.windows
            # Type a harmless command into that terminal as proof the shell runs.
            # US/German common keys: echo recovered (use no punctuation).
            for code in (18, 46, 35, 24, 57, 19, 18, 46, 24, 47, 18, 19, 18, 32, 28):
                inputs.key(code)
            shot('05-no-theme-recovery.png' if case == 'no-theme' else '06-no-font-recovery.png')
            print('RECOVERY_SHORTCUT_PASSED=' + case, flush=True)
        (work / 'passed').write_text('passed\n')
    except BaseException:
        import traceback
        traceback.print_exc()
        sys.stderr.flush()
        raise
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
        # All remaining descendants are removed when this case's PID namespace ends.
        subprocess.run(['/usr/bin/labwc', '--exit'], check=False)
        log.close()


def outside(case):
    room()
    work = WORK / case
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)
    (work / 'passed').unlink(missing_ok=True)
    for folder in ('runtime', 'home', 'config', 'cache', 'data', 'labwc', 'fonts'):
        (work / folder).mkdir(exist_ok=True)
    (work / 'runtime').chmod(0o700)
    shutil.copyfile(CONFIG / 'usr/share/aresos/labwc/rc.xml', work / 'labwc/rc.xml')
    (work / 'labwc/autostart').write_text(f'/usr/bin/python3 {__file__} --inside {case} &\n')
    data = work / 'data'
    if case != 'no-theme':
        shutil.copytree(CONFIG / 'usr/share/themes', data / 'themes', dirs_exist_ok=True)
    if case != 'no-font':
        shutil.copytree(CONFIG / 'usr/share/fonts/aresos', work / 'fonts', dirs_exist_ok=True)
    schemas = data / 'glib-2.0/schemas'
    schemas.mkdir(parents=True, exist_ok=True)
    for path in Path('/usr/share/glib-2.0/schemas').glob('*.xml'):
        shutil.copyfile(path, schemas / path.name)
    shutil.copyfile(CONFIG / 'usr/share/glib-2.0/schemas/zz-aresos.gschema.override', schemas / 'zz-aresos.gschema.override')
    subprocess.run(['/usr/bin/glib-compile-schemas', '--strict', str(schemas)], check=True)
    (work / 'fonts.conf').write_text(f'<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd"><fontconfig><dir>/usr/share/fonts</dir><dir>{work}/fonts</dir><cachedir>{work}/cache/fontconfig</cachedir></fontconfig>')
    env = {key: value for key, value in os.environ.items() if key not in ('DISPLAY', 'WAYLAND_DISPLAY', 'WAYLAND_SOCKET', 'DBUS_SESSION_BUS_ADDRESS', 'GSETTINGS_SCHEMA_DIR') and not key.startswith(('ARESOS_', 'XKB_DEFAULT_'))}
    env.update(PYTHONUNBUFFERED='1', HOME=str(work / 'home'), XDG_CONFIG_HOME=str(work / 'config'), XDG_DATA_HOME=str(data), XDG_CACHE_HOME=str(work / 'cache'),
               XDG_RUNTIME_DIR=str(work / 'runtime'), XDG_DATA_DIRS=str(data) + ':/usr/share', WLR_BACKENDS='headless', WLR_RENDERER='pixman', WLR_HEADLESS_OUTPUTS='1',
               FONTCONFIG_FILE=str(work / 'fonts.conf'), GDK_BACKEND='wayland', QT_QPA_PLATFORM='wayland', GTK_USE_PORTAL='0', NO_AT_BRIDGE='1', GSETTINGS_BACKEND='memory')
    command = ['/usr/bin/bwrap', '--ro-bind', '/', '/', '--bind', str(ROOT), str(ROOT), '--unshare-pid', '--unshare-net', '--die-with-parent', '--new-session', '--proc', '/proc', '--dev', '/dev',
               '--tmpfs', '/tmp', '--tmpfs', '/run/user/1001', '--ro-bind', str(work / 'labwc'), '/usr/share/aresos/labwc']
    for path in ('usr/bin/aresos-session', 'usr/bin/aresos-terminal', 'usr/libexec/aresos-keyboard', 'usr/share/aresos/bashrc'):
        installed = work / 'installed' / path
        installed.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CONFIG / path, installed)
        # The image's configure step makes these scripts executable too.
        installed.chmod(0o755 if path != 'usr/share/aresos/bashrc' else 0o644)
        command += ['--ro-bind', str(installed), '/' + path]
    command += ['/usr/bin/aresos-session']
    with open(work / 'session.log', 'w') as log:
        process = subprocess.Popen(command, env=env, stdout=log, stderr=log, start_new_session=True)
        try:
            process.wait(timeout=100)
            assert process.returncode == 0, (case, process.returncode)
            assert (work / 'passed').exists(), f'{case} failed: see {work}/session.log'
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
    print('CAPTURE_PASSED=' + case, flush=True)


if __name__ == '__main__':
    if sys.argv[1:2] == ['--gtk']:
        gtk_window()
    elif sys.argv[1:2] == ['--inside']:
        inside(sys.argv[2])
    else:
        for case in sys.argv[1:] or ('normal', 'no-theme', 'no-font'):
            outside(case)
