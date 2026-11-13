"""Asking-tool installation precondition. Does not confine Claude Code."""
import os
from pathlib import PurePosixPath
import stat

from .common import storage_stream, cleanup, WIRE_LIMIT, Refused, strict_json_loads
from .boundary_policy import asking_rules

DEFAULT_SETTINGS = '/etc/claude-code/managed-settings.json'

def protected(info):
    if info.st_uid != 0:
        raise ValueError('must be owned by root')
    if info.st_mode & 0o022:
        raise ValueError('must not be group- or world-writable')


class Boundary:
    def __init__(self):
        self.settings = DEFAULT_SETTINGS
        self.reason = None
        try:
            self.require()
        except Refused:
            pass

    def read(self, path):
        fd = None
        try:
            components = PurePosixPath(path).parts
            if not components or components[0] != '/' or '..' in components:
                raise ValueError('requires an absolute production path')
            fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            protected(os.fstat(fd))
            for component in components[1:-1]:
                parent = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = parent
                protected(os.fstat(fd))
            leaf = os.open(components[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            with storage_stream(os.fdopen(leaf, 'rb')) as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode):
                    raise ValueError('must be a regular file (no symlinks)')
                protected(info)
                return strict_json_loads(stream.read(WIRE_LIMIT + 1))
        except (OSError, ValueError, Refused, TypeError) as exc:
            raise Refused('boundary_not_installed', f'{path}: {exc}; install the managed Claude Code ask rules.') from exc
        finally:
            with cleanup('policy descriptor close'):
                if fd is not None:
                    os.close(fd)

    def require(self):
        try:
            actual = self.read(self.settings)
            permissions = actual.get('permissions') if type(actual) is dict else None
            rules = permissions.get('ask') if type(permissions) is dict else None
            if type(rules) is not list or any(type(rule) is not str for rule in rules):
                raise ValueError(f'{self.settings}: permissions.ask must be a list of rules')
            missing = [rule for rule in asking_rules() if rule not in rules]
            if missing:
                raise ValueError(f'{self.settings}: missing permissions.ask: ' + ', '.join(missing))
        except (ValueError, TypeError, AttributeError, Refused) as exc:
            self.reason = str(exc)
            raise Refused('boundary_not_installed', self.reason) from exc
        self.reason = None
