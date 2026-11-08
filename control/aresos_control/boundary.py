"""Installation precondition; actual confinement is qualified by 18b/18c."""
import os
from pathlib import PurePosixPath
import stat

from .common import WIRE_LIMIT, Refused, canonical, strict_json_loads
from .boundary_policy import asking_rules, managed_servers, managed_settings, managed_mcp

DEFAULT_SETTINGS = '/etc/claude-code/managed-settings.json'
DEFAULT_MCP = '/etc/claude-code/managed-mcp.json'
DEFAULT_REMOTE = '/home/assistant/.claude/remote-settings.json'


def differences(expected, actual, path=''):
    if type(expected) is dict and type(actual) is dict:
        for key in sorted(expected.keys() | actual.keys()):
            child = path + '.' + key if path else key
            if key not in expected or key not in actual:
                yield child
            else:
                yield from differences(expected[key], actual[key], child)
    elif canonical(expected) != canonical(actual):
        # Arrays are ordered policy values. Include their full differing entries
        # so a missing ask rule is as diagnosable as an extra Bash grant.
        yield path + ': expected ' + canonical(expected) + ', installed ' + canonical(actual)


def protected(info):
    if info.st_uid != 0:
        raise ValueError('must be owned by root')
    if info.st_mode & 0o022:
        raise ValueError('must not be group- or world-writable')


class Boundary:
    def __init__(self):
        self.settings, self.mcp = DEFAULT_SETTINGS, DEFAULT_MCP
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
            with os.fdopen(leaf, 'rb') as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode):
                    raise ValueError('must be a regular file (no symlinks)')
                protected(info)
                return strict_json_loads(stream.read(WIRE_LIMIT + 1))
        except (OSError, ValueError, Refused, TypeError) as exc:
            raise Refused('boundary_not_installed', f'{path}: {exc}; install the managed Claude Code boundary.') from exc
        finally:
            if fd is not None:
                os.close(fd)

    def absent_or_empty(self, path, directory=False):
        """Walk even optional sources without following a link, including dangling ones."""
        fd = None
        try:
            parts = PurePosixPath(path).parts
            if not parts or parts[0] != '/' or '..' in parts:
                raise ValueError('requires an absolute production path')
            fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            for part in parts[1:-1]:
                if directory:
                    protected(os.fstat(fd))
                parent = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = parent
            if directory:
                protected(os.fstat(fd))
                leaf = os.open(parts[-1], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = leaf
                protected(os.fstat(fd))
                entries = sorted(os.listdir(fd))
                if entries:
                    raise ValueError('must be empty; unexpected entry ' + canonical(entries[0]))
            else:
                os.stat(parts[-1], dir_fd=fd, follow_symlinks=False)
                raise ValueError('remote policy is unsupported; source must be absent')
        except FileNotFoundError:
            return
        except (OSError, ValueError) as exc:
            raise Refused('boundary_not_installed', f'{path}: {exc}') from exc
        finally:
            if fd is not None:
                os.close(fd)

    def require(self):
        try:
            self.absent_or_empty(str(PurePosixPath(self.settings).with_name('managed-settings.d')), directory=True)
            self.absent_or_empty(DEFAULT_REMOTE)
            for path, expected in ((self.settings, managed_settings()), (self.mcp, managed_mcp())):
                actual = self.read(path)
                if canonical(expected) != canonical(actual):
                    paths = '; '.join(differences(expected, actual))
                    raise ValueError(f'{path}: generated policy differs at {paths}')
        except (ValueError, TypeError, AttributeError, Refused) as exc:
            self.reason = str(exc)
            raise Refused('boundary_not_installed', self.reason) from exc
        self.reason = None
