"""What case 5 reads from Chrome's network log (--log-net-log): brief 18c-b, item 2.

With our policy in place two things must hold:
- nothing but a file: address names our extension's ID;
- no request at all goes to Google's update service (an address with
  /service/update2/). For an extension whose update address is empty or the
  store's, Chrome posts the ID there in a request body the log doesn't record,
  so only the address shows that path.
And the log must be one that would have shown it: the probe's ID is in at least
two update requests to the test's own server, so two update checks ran.

Standard library only: the VM pass reads the same log in a guest without node.
"""
import json
import re
from urllib.parse import urlsplit

UPDATE_SERVICE = '/service/update2/'
ESCAPED_UPDATE_SERVICE = UPDATE_SERVICE.replace('/', '\\/')
OUTSIDE = '(in a part of the log outside its parsed events)'
NAMED_ID = re.compile('id(?:=|%3D)([a-p]{32})')


def events(text):
    """The log's events. A log whose Chrome was killed ends mid-list: its complete lines still count."""
    try:
        found = json.loads(text)['events']
        if isinstance(found, list):
            return [event for event in found if isinstance(event, dict)]
    except (ValueError, KeyError, TypeError):
        pass
    found = []
    for line in text.splitlines():
        line = line.strip().rstrip(',')
        if line.startswith('{') and line.endswith('}'):
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict) and 'source' in event:
                found.append(event)
    return found


def request_start(text):
    """Chrome's number for the event that starts a request, from the log's own constants; None when it names none.

    The constants are the file's first line, also in a log that ends mid-list.
    """
    for candidate in (text, text.split('\n', 1)[0].strip().rstrip(',') + '}'):
        try:
            number = json.loads(candidate)['constants']['logEventTypes']['URL_REQUEST_START_JOB']
        except (ValueError, KeyError, TypeError):
            continue
        if isinstance(number, int):
            return number
    return None


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def scan(text, extension_id, probe_id, probe_address):
    """Read one log. Returns what was found; `problems` says whether that is a pass."""
    named, service, checks, hosts, asks = [], [], set(), set(), set()
    counted_id = counted_service = 0
    found, start = events(text), request_start(text)
    for event in found:
        params = event.get('params')
        for value in _strings(params):
            if extension_id in value:
                counted_id += value.count(extension_id)
                if not value.startswith('file:'):
                    named.append(value[:400])
            if UPDATE_SERVICE in value:
                counted_service += value.count(UPDATE_SERVICE)
                service.append(value[:400])
                # What the request asks, as far as the log shows it: the address, and the IDs in it.
                asks.add(value.split('?')[0][:200])
                asks.update(NAMED_ID.findall(value))
        url = params.get('url') if isinstance(params, dict) else None
        if isinstance(url, str):
            parts = urlsplit(url)
            hosts.add(parts.hostname or parts.scheme + ':')
            # One request is one source. Its start is the event the log's constants name; a log without
            # them is read by the method that only a start carries. Later events repeat the address.
            starts = 'method' in params if start is None else event.get('type') == start
            if starts and url.startswith(probe_address) and probe_id in url:
                checks.add((event.get('source') or {}).get('id'))
    # Every occurrence in the file must be one the events account for, whatever else the log holds.
    if text.count(extension_id) > counted_id:
        named.append(OUTSIDE)
    if text.count(UPDATE_SERVICE) + text.count(ESCAPED_UPDATE_SERVICE) > counted_service:
        service.append(OUTSIDE)
    return {'events': len(found), 'hosts': sorted(hosts), 'named_elsewhere': named, 'update_service': service,
            'update_service_asks': sorted(asks), 'probe_checks': len(checks)}


def added(result, baseline):
    """What a run's update-service requests have that the baseline's lack: addresses and named IDs.

    The pinned Chrome asks the store for two extensions of its own on a fresh
    profile whatever our policy says, so the brief's fallback applies: compared
    with a run of the probe alone, ours must add none.
    """
    more = set(result['update_service_asks']) - set(baseline['update_service_asks'])
    # A mention the events don't account for (a line cut off mid-write) can't be compared: it counts as added.
    return sorted(more | ({OUTSIDE} & set(result['update_service'])))


def problems(result, checks=2):
    """Why this log fails case 5, as (kind, text); empty when it passes."""
    found = []
    if result['named_elsewhere']:
        found.append(('named', 'our extension ID is named outside a file: address: ' + '; '.join(result['named_elsewhere'][:3])))
    if result['update_service']:
        found.append(('update_service', "a request went to Google's update service: " + '; '.join(result['update_service'][:3])))
    if result['probe_checks'] < checks:
        found.append(('control', f"the probe's ID is in {result['probe_checks']} update requests, not in at least {checks}: "
                                 'the log does not show that update checks ran'))
    return found
