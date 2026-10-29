"""Read-only guest kernel health. Only counts/classes cross the serial channel."""
import ast
import inspect
import json
import re


def context(guest):
    value = getattr(guest, 'xhci_context', None)
    return value if isinstance(value, dict) else None


def classify(rows, since, boot, expected_disconnect=None):
    counts = dict(endpoint_timeout=0, controller_dead=0, usb_disconnect=0, expected_disconnect=0)
    checked = 0
    for row in rows:
        assert row['_TRANSPORT'] == 'kernel' and row['_BOOT_ID'] == boot, 'STOP: kernel journal identity changed'
        stamp = int(row['__MONOTONIC_TIMESTAMP'])
        assert stamp >= 0 and isinstance(row['MESSAGE'], str), 'STOP: invalid kernel journal shape'
        if stamp < since: continue
        checked += 1
        text = row['MESSAGE']
        if re.search(r'xhci_hcd .*xHCI host not responding to stop endpoint command', text):
            counts['endpoint_timeout'] += 1
        elif re.search(r'xhci_hcd .*(?:host controller not responding, assume dead|HC died; cleaning up)', text):
            counts['controller_dead'] += 1
        elif re.search(r'^usb [0-9]+-[0-9.]+: USB disconnect, device number [0-9]+$', text):
            port = text.split(':', 1)[0].removeprefix('usb ')
            if expected_disconnect and port == expected_disconnect: counts['expected_disconnect'] += 1
            else: counts['usb_disconnect'] += 1
    # Only one independently requested removal of the identified tools device.
    assert counts['expected_disconnect'] <= 1, 'STOP: repeated tools-stick disconnect'
    return dict(counts=counts, checked_kernel_messages=checked, counts_only=True)


def kernel_health(context):
    import subprocess
    result = subprocess.run(['journalctl', '--dmesg', '--boot=0', '--output=json', '--no-pager', '--quiet'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
    assert result.returncode == 0 and not result.stderr, 'STOP: kernel health journal unavailable'
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert rows, 'STOP: empty kernel health journal'
    boot = rows[0]['_BOOT_ID']  # journalctl --boot=0 selects this guest boot.
    assert re.fullmatch('[0-9a-f]{32}', boot), 'STOP: invalid guest boot identity'
    value = classify(rows, context['since_usec'], boot, context.get('expected_disconnect'))
    value.update(stage=context['stage'], tools_attached=context['attached'], tools_needed=context['needed'])
    value['stop'] = bool((context['attached'] or context['needed']) and any(
        value['counts'][name] for name in ('controller_dead', 'usb_disconnect')))
    return value


def preamble(context):
    assert set(context) == {'stage', 'since_usec', 'attached', 'needed', 'expected_disconnect'}
    assert type(context['since_usec']) is int and context['since_usec'] >= 0
    assert type(context['attached']) is bool and type(context['needed']) is bool
    return ('import json,re,time\n' + inspect.getsource(classify) + inspect.getsource(kernel_health)
        + '\n_xhci_context=' + repr(context) + '\n_xhci_last=-float("inf")\n'
        + 'def xhci_poll(force=False):\n'
        + '    global _xhci_last\n'
        + '    if not force and time.monotonic()-_xhci_last<1: return\n'
        + '    _xhci_last=time.monotonic()\n'
        + '    try: value=kernel_health(_xhci_context)\n'
        + '    except Exception: raise SystemExit("STOP: kernel health check unavailable or inconsistent") from None\n'
        + '    if value["stop"]:\n'
        # framed() redirects stdout to its result file and aborts on failure.
        # Counts must therefore go to stderr to survive an early health STOP.
        + '        print(json.dumps(dict(xhci_health=value)),file=__import__("sys").stderr,flush=True)\n'
        + '        raise SystemExit("STOP: xHCI death/disconnect while tools stick attached or needed")\n')


def guard(source, context):
    """Poll outside observer exception handlers; never swallow a health STOP.

    Inject only into the read-only readiness observers. Original deadlines,
    predicates and protocol are preserved; no guest keyboard settings change.
    """
    if context is None: return source
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    inserts = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            first = node.body[0]
            if first.lineno == node.lineno:
                index = node.lineno - 1
                line = lines[index]
                indent = ' ' * (node.col_offset + 4)
                lines[index] = line[:first.col_offset] + '\n' + indent + 'xhci_poll()\n' + indent + line[first.col_offset:]
            else:
                inserts.append((first.lineno - 1, ' ' * first.col_offset + 'xhci_poll()\n'))
    for index, text in sorted(inserts, reverse=True): lines.insert(index, text)
    return preamble(context) + '\nxhci_poll(True)\n' + ''.join(lines) + '\nxhci_poll(True)\n'


def checkpoint(guest, stage, **changes):
    """The guest owns context, so older harnesses have no health state to alter."""
    if context(guest) is None: return
    import shlex
    import switch_vm as sw
    import two_disk_vm as td
    state = context(guest)
    state.update(changes)
    source = preamble(state) + '\nprint(json.dumps(kernel_health(_xhci_context)))\n'
    value = guest.capture_json(stage + '-xhci-health', sw.framed('python3 -c ' + shlex.quote(source)))
    td.save(stage + '-xhci-health', value)
    assert not value['stop'], 'STOP: xHCI death/disconnect while tools stick attached or needed'
