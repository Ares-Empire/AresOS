"""Read-only localization-only D-Bus observation; no installer modifications."""
import json


def localization_values(messages):
    pending = {}
    values = []
    allowed = {'XLayouts', 'VirtualConsoleKeymap', 'LayoutSwitchOptions', 'Keyboard', 'Language'}
    for message in messages:
        payload = message.get('payload', {})
        data = payload.get('data', [])
        if (message.get('type') == 'method_call' and message.get('interface') == 'org.freedesktop.DBus.Properties'
                and message.get('member') == 'Get' and len(data) == 2
                and data[0] == 'org.fedoraproject.Anaconda.Modules.Localization' and data[1] in allowed):
            pending[(message['sender'], message['cookie'])] = (data[1], message.get('timestamp-realtime'))
        elif message.get('type') == 'method_return':
            request = pending.get((message.get('destination'), message.get('reply_cookie')))
            if request:
                values.append(dict(property=request[0], client=message.get('destination'), request_cookie=message.get('reply_cookie'), request_realtime=request[1],
                    reply_realtime=message.get('timestamp-realtime'), value=data))
    return values


def start(guest, stage):
    guest.command(stage + '-localization-monitor', '''set -e
address=$(cat /run/anaconda/bus.address)
busctl --address="$address" --json=short monitor org.fedoraproject.Anaconda.Modules.Localization > /run/aresos-localization.jsonl 2>/run/aresos-localization-monitor.log < /dev/null &
echo "$!" > /run/aresos-localization-monitor.pid
sleep 1
kill -0 "$(cat /run/aresos-localization-monitor.pid)"
''')


def collect(guest, stage):
    import inspect
    import shlex
    from switch_vm import framed
    program = 'import json,pathlib\n' + inspect.getsource(localization_values)
    program += '''
path=pathlib.Path('/run/aresos-localization.jsonl')
assert path.stat().st_size < 3000000, 'Localization diagnostic unexpectedly large'
messages=[json.loads(line) for line in path.read_text().splitlines() if line.startswith('{')]
values=localization_values(messages)
print(json.dumps(dict(diagnostic_only=True, installer_unmodified=True,
    service='org.fedoraproject.Anaconda.Modules.Localization',
    message_count=len(messages), values=values,
    note='Chronological Get/reply pairs with client/cookie; final VirtualConsoleKeymap read is the candidate pinned _set_kargs boundary. Interpret against retained source; cause is not an acceptance gate.')))
'''
    return guest.capture_json(stage + '-localization-diagnostic', framed('python3 -c ' + shlex.quote(program)))
