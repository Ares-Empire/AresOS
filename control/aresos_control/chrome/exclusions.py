"""Owner infrastructure comes from protected image configuration, never guesses."""
import re

from ..boundary import Boundary
from ..common import Refused
from .policy import FIXED_HOSTS

SETTING = '/etc/aresos/control/chrome-excluded-sites.json'


def owner_hosts(path=SETTING):
    try:
        # Reuse the base's no-symlink, root-owned component walk. The image
        # grants the service read access, while only root can replace the list.
        data = Boundary.read(None, path)
        if type(data) is not dict or set(data) != {'format', 'hosts'} or data['format'] != 1 or type(data['hosts']) is not list or len(data['hosts']) > 128:
            raise ValueError('expected format 1 and a bounded hosts list')
        for host in data['hosts']:
            if type(host) is not str or len(host) > 253 or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', host) or any(not label or len(label) > 63 or label.startswith('-') or label.endswith('-') for label in host.split('.')):
                raise ValueError('entries must be lowercase DNS host names')
        return sorted(set(data['hosts']))
    except (Refused, ValueError, TypeError) as exc:
        raise Refused('chrome_settings_unavailable', 'Chrome refuses reads and actions: its owner-only excluded-sites setting is missing, unreadable or unsafe; ask the owner to install it.') from exc


def excluded_hosts(path=SETTING):
    return sorted(set(FIXED_HOSTS) | set(owner_hosts(path)))
