"""Installation precondition; actual confinement is qualified by 18b/18c."""
import os
import stat

from .common import WIRE_LIMIT, Refused, strict_json_loads
from .definitions import ACTIONS, APPS

DEFAULT_SETTINGS = '/etc/claude-code/managed-settings.json'
DEFAULT_MCP = '/etc/claude-code/managed-mcp.json'


def asking_rules():
    return [f'mcp__{a.app}__{a.verb}' for a in ACTIONS
            if a.effect in {'send', 'delete'} and not a.owner_only]


def managed_servers():
    return {app: {'type': 'stdio', 'command': '/usr/bin/env', 'args': [
        '-i', 'PATH=/usr/bin:/bin', 'LANG=C.UTF-8', '/usr/bin/python3', '-I', '-S',
        '/usr/libexec/aresos-control/launch.py', 'proxy', app]}
        for app in sorted(APPS - {'testapp'})}


class Boundary:
    def __init__(self, config=None):
        config = config or {}
        self.settings = config.get('managed_settings', DEFAULT_SETTINGS)
        self.mcp = config.get('managed_mcp', DEFAULT_MCP)
        self.socket_dir = config.get('socket_dir', '/run/aresos-tools')
        # Startup records the fault without disabling reads and free changes.
        self.reason = None
        try:
            self.require()
        except Refused:
            pass

    def read(self, path):
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, 'rb') as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode):
                    raise ValueError('must be a regular file (no symlinks)')
                if info.st_uid != 0:
                    raise ValueError('must be owned by root')
                if info.st_mode & 0o022:
                    raise ValueError('must not be group- or world-writable')
                return strict_json_loads(stream.read(WIRE_LIMIT + 1))
        except (OSError, ValueError, Refused, TypeError) as exc:
            raise Refused('boundary_not_installed', f'{path}: {exc}; install the managed Claude Code boundary.') from exc

    def require(self):
        try:
            settings = self.read(self.settings)
            required = {
                'sandbox.enabled': True, 'sandbox.failIfUnavailable': True,
                'sandbox.allowUnsandboxedCommands': False, 'sandbox.network.allowAllUnixSockets': False,
                'permissions.disableBypassPermissionsMode': 'disable',
                'allowManagedPermissionRulesOnly': True, 'allowManagedHooksOnly': True,
            }
            for path, expected in required.items():
                value = settings
                for part in path.split('.'):
                    value = value.get(part) if type(value) is dict else None
                if type(value) is not type(expected) or value != expected:
                    raise ValueError(f'{path} must equal {expected!r}')
            sandbox = settings['sandbox']
            filesystem = sandbox.get('filesystem')
            denied = filesystem.get('denyRead') if type(filesystem) is dict else None
            if type(denied) is not list or self.socket_dir not in denied:
                raise ValueError(f'sandbox.filesystem.denyRead must include {self.socket_dir}')
            permissions = settings['permissions']
            ask, allow = permissions.get('ask'), permissions.get('allow')
            if type(ask) is not list or not all(type(v) is str for v in ask):
                raise ValueError('permissions.ask must be a list of asking rules')
            if type(allow) is not list or not all(type(v) is str for v in allow):
                raise ValueError('permissions.allow must be a list')
            import fnmatch
            for rule in asking_rules():
                if rule not in ask:
                    raise ValueError(f'permissions.ask is missing {rule}')
                if any(fnmatch.fnmatchcase(rule, grant) for grant in allow):
                    raise ValueError(f'permissions.allow grants asking tool {rule}')
            mcp = self.read(self.mcp)
            servers = mcp.get('mcpServers') if type(mcp) is dict else None
            expected = managed_servers()
            if type(servers) is not dict:
                raise ValueError(f'{self.mcp}: mcpServers must be an object')
            if servers.keys() != expected.keys():
                raise ValueError(f'{self.mcp}: mcpServers missing {sorted(expected.keys() - servers.keys())}; unexpected {sorted(servers.keys() - expected.keys())}')
            for name, server in expected.items():
                if servers[name] != server:
                    raise ValueError(f'{self.mcp}: mcpServers.{name} has an unexpected command, arguments or configuration')
        except (ValueError, TypeError, AttributeError, Refused) as exc:
            self.reason = str(exc)
            raise Refused('boundary_not_installed', self.reason) from exc
        self.reason = None
