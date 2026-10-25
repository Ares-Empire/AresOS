"""Normal KDE keyboard KCM via accessibility actions; QMP types into KWrite."""
import base64
import pathlib
import shlex
import time

ACCESSIBLE = '''import json,re,sys,time,pyatspi
def nodes(root,depth=0):
    if depth>35: return
    yield root
    for i in range(root.childCount):
        child=root.getChildAtIndex(i)
        if child is not None: yield from nodes(child,depth+1)
def candidates(pattern):
    return [n for n in nodes(pyatspi.Registry.getDesktop(0)) if re.fullmatch(pattern,n.name or '',re.I) and n.getState().contains(pyatspi.STATE_SHOWING)]
def action(pattern,checked=False):
    deadline=time.monotonic()+40
    while time.monotonic()<deadline:
        found=candidates(pattern)
        for n in found:
            if checked and n.getState().contains(pyatspi.STATE_CHECKED): return
            try:
                a=n.queryAction()
                if a.nActions and a.doAction(0): return
            except NotImplementedError: pass
        time.sleep(.5)
    print(json.dumps([(n.name,n.getRoleName()) for n in nodes(pyatspi.Registry.getDesktop(0))]))
    raise AssertionError('KDE normal settings control unavailable: '+pattern)
phase=sys.argv[1]
if phase=='enable':
    action('Configure Layouts',True); action('Add layout')
elif phase=='search':
    edits=[n for n in nodes(pyatspi.Registry.getDesktop(0)) if n.getRoleName() in ('text','entry') and n.getState().contains(pyatspi.STATE_EDITABLE) and n.getState().contains(pyatspi.STATE_SHOWING)]
    assert len(edits)>=1
    search=next((n for n in edits if 'search' in (n.name or '').lower()),edits[0])
    search.queryEditableText().setTextContents('German'); search.queryComponent().grabFocus()
elif phase=='select':
    action('German'); time.sleep(.5)
    # Both list columns expose German; select the default, unqualified variant.
    found=candidates('German')
    if len(found)>1:
        a=found[-1].queryAction(); assert a.doAction(0)
    action('OK')
    for n in candidates('Remove layout (English.*|.*US.*)'):
        a=n.queryAction(); assert a.doAction(0)
    action('Apply')
elif phase=='save':
    action('Save')
print('KDE_KEYBOARD_UI_'+phase.upper()+'_PASSED')
'''


def user_command(program):
    return '''set -e
uid=$(id -u liveuser)
runuser -u liveuser -- env XDG_RUNTIME_DIR="/run/user/$uid" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus" bash -c '
while IFS= read -r entry; do export "$entry"; done < <(systemctl --user show-environment)
''' + program + "'"


def run(guest, stage):
    guest.command(stage+'-live-kcm',user_command('QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1 kcmshell6 kcm_keyboard >/tmp/aresos-live-kcm.log 2>&1 </dev/null &'))
    encoded=base64.b64encode(ACCESSIBLE.encode()).decode()
    guest.command(stage+'-accessibility-script','set -e; printf %s '+shlex.quote(encoded)+' | base64 -d > /run/aresos-live-accessibility.py; chmod 0644 /run/aresos-live-accessibility.py')
    for phase in ('enable','search','select'):
        guest.command(stage+'-kde-'+phase,user_command('python3 /run/aresos-live-accessibility.py '+phase),timeout=60)
        if phase=='search':
            guest.keys(['ret']); time.sleep(1)
        guest.screenshot(stage+'-kde-'+phase)
    guest.command(stage+'-live-layout',user_command('kreadconfig6 --file kxkbrc --group Layout --key LayoutList | grep -x de'))
    guest.command(stage+'-global-switching',user_command('value=$(kreadconfig6 --file kxkbrc --group Layout --key SwitchMode); test -z "$value" || test "$value" = Global'))
    guest.command(stage+'-live-editor',user_command('QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1 kwrite /tmp/aresos-live-physical.txt >/tmp/aresos-live-editor.log 2>&1 </dev/null &'))
    time.sleep(3)
    # This is the guide's editor check, before any terminal commands or install.
    for keys in (['z'],['spc'],['y'],['spc'],['shift','7'],['spc'],['slash'],['spc'],['shift','2'],['spc'],['shift','4'],['spc'],['apostrophe'],['spc'],['semicolon'],['spc'],['bracketleft']):
        guest.keys(keys); time.sleep(.12)
    guest.keys(['ctrl','s'])
    guest.command(stage+'-live-editor-result',"python3 - <<'PY'\nimport pathlib\np=pathlib.Path('/tmp/aresos-live-physical.txt')\nassert p.read_text()=='y z / - \" $ ä ö ü', repr(p.read_text())\nprint('LIVE_GERMAN_PHYSICAL_KEYS_PASSED')\nPY")
    guest.screenshot(stage+'-live-physical')
    # Close only our normal settings/editor windows, with their application quit action.
    guest.keys(['ctrl','q'])
