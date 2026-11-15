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
from urllib.parse import urlsplit

UPDATE_SERVICE = '/service/update2/'
ESCAPED_UPDATE_SERVICE = UPDATE_SERVICE.replace('/', '\\/')
OUTSIDE = '(in a part of the log outside its parsed events)'


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
    named, service, checks, hosts = [], [], set(), set()
    counted_id = counted_service = 0
    found = events(text)
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
        url = params.get('url') if isinstance(params, dict) else None
        if isinstance(url, str):
            parts = urlsplit(url)
            hosts.add(parts.hostname or parts.scheme + ':')
            # The event that starts a request carries its method; later events of the same request repeat the address.
            if 'method' in params and url.startswith(probe_address) and probe_id in url:
                checks.add((event.get('source') or {}).get('id'))
    # Every occurrence in the file must be one the events account for, whatever else the log holds.
    if text.count(extension_id) > counted_id:
        named.append(OUTSIDE)
    if text.count(UPDATE_SERVICE) + text.count(ESCAPED_UPDATE_SERVICE) > counted_service:
        service.append(OUTSIDE)
    return {'events': len(found), 'hosts': sorted(hosts), 'named_elsewhere': named, 'update_service': service,
            'probe_checks': len(checks)}


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
