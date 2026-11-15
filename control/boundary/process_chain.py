"""Process chains of the MCP server and the managed hooks under the real Claude Code (brief 18e, item 6).

The "used" mark is named after the MCP proxy's parent process; the Stop hook finds it among its own ancestors. That
only works while Claude Code starts both from the same process, so the interactive suite pins it per session.
"""
import json
import os
from pathlib import Path

FOLDER = Path('/home/assistant/process-chains')
LEVELS = 4


def describe(pid):
    data = Path(f'/proc/{pid}/stat').read_bytes()
    # The command name may contain spaces and brackets; fields resume after the last ')'.
    fields = data[data.rindex(b')') + 2:].split()
    try:
        exe = os.readlink(f'/proc/{pid}/exe')
    except OSError:
        exe = None
    argv = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
    return {'pid': pid, 'ppid': int(fields[1]), 'start': int(fields[19]),
            'comm': data[data.index(b'(') + 1:data.rindex(b')')].decode(errors='replace'), 'exe': exe,
            'argv': [part.decode(errors='replace')[:160] for part in argv if part][:12]}


def chain(pid, levels=LEVELS):
    """The process itself, then up to `levels` ancestors, stopping at PID 1."""
    found = []
    while pid > 1 and len(found) <= levels:
        item = describe(pid)
        found.append(item)
        pid = item['ppid']
    return found


def record(kind):
    """Called by the container's stand-ins; never fails them. No folder (other suites): no record.

    A hook also records what the real `usage.used()` answers from its place in the real process tree.
    """
    try:
        if FOLDER.is_dir():
            found = chain(os.getpid())
            if kind.startswith('hook-'):
                from aresos_control import usage
                found[0]['used'] = usage.used()
            (FOLDER / f'{kind}-{os.getpid()}.json').write_text(json.dumps(found))
    except Exception:
        pass


def mark():
    """The MCP stand-in marks its session with the real `usage.mark()` on each tool call, as the proxy does."""
    try:
        if FOLDER.is_dir():
            from aresos_control import usage
            usage.mark()
    except Exception as exc:
        (FOLDER / f'mark-error-{os.getpid()}.txt').write_text(repr(exc))


def check(folder):
    """Every Stop hook has an MCP server's parent (same pid and start time) among its four nearest ancestors."""
    load = lambda pattern: [json.loads(path.read_text()) for path in sorted(folder.glob(pattern))]
    servers, stops, prompts = load('mcp-*.json'), load('hook-Stop-*.json'), load('hook-UserPromptSubmit-*.json')
    assert servers and stops, ('no process chains recorded', len(servers), len(stops))
    parents = {(server[1]['pid'], server[1]['start']) for server in servers if len(server) > 1}
    for stop in stops:
        ancestors = [(item['pid'], item['start']) for item in stop[1:LEVELS + 1]]
        assert parents & set(ancestors), ('STOP: the MCP server and the Stop hook have no common Claude Code process',
                                          servers, stop)
    assert not list(folder.glob('mark-error-*.txt')), [p.read_text() for p in folder.glob('mark-error-*.txt')]
    return {'mcp': servers, 'stop': stops, 'prompt': prompts}


def check_used(chains, arrivals):
    """Quiet unless used, with the real code: a Stop hook finds a mark exactly when its session's tool ran."""
    used = [stop[0].get('used') for stop in chains['stop']]
    assert all(type(value) is bool for value in used), used
    assert any(used) == (arrivals > 0), ('STOP: usage marks disagree with the tool calls', used, arrivals)
    return used


def summary(chains):
    """One line per chain: comm:pid from the process up."""
    return {kind: [' <- '.join(f"{item['comm']}:{item['pid']}" for item in found) for found in chains[kind]]
            for kind in chains}
