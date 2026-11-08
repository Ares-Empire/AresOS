"""Single policy definition used by artifact generation and installation checks."""


def asking_rules():
    from .definitions import ACTIONS
    return [f'mcp__{a.app}__{a.verb}' for a in ACTIONS
            if a.effect in {'send', 'delete'} and not a.owner_only]


def managed_servers():
    from .definitions import APPS
    return {app: {'type': 'stdio', 'command': '/usr/bin/env', 'args': [
        '-i', 'PATH=/usr/bin:/bin', 'LANG=C.UTF-8', '/usr/bin/python3', '-I', '-S',
        '/usr/libexec/aresos-control/launch.py', 'proxy', app]}
        for app in sorted(APPS - {'testapp'})}


def managed_mcp():
    return {'_comment': 'DRAFT: fixed root-owned proxy. Final names/settings require owner decision 3 and brief 18b qualification.',
            'mcpServers': managed_servers()}


def managed_settings():
    settings = {'allowManagedPermissionRulesOnly': True,
     'allowManagedHooksOnly': True,
     'disableSideloadFlags': True,
     'strictKnownMarketplaces': [],
     'enabledPlugins': {},
     'syncClaudeAiPlugins': False,
     'disableCommandPluginSources': True,
     'allowAllClaudeAiMcps': False,
     'allowClaudeInChromeWithManagedMcp': False,
     'permissions': {'defaultMode': 'default',
                     'disableBypassPermissionsMode': 'disable',
                     'blockWritesOutsideWorkingDirectories': True,
                     'blockReadsOutsideWorkingDirectories': True,
                     'additionalDirectories': [],
                     'allow': [],
                     'ask': ['WebFetch', 'WebSearch'],
                     'deny': ['Read(//run/aresos-tools/**)',
                              'Read(//var/lib/aresos-tools/**)',
                              'Read(~/.config/**)',
                              'Read(~/.local/share/keyrings/**)',
                              'Read(~/.claude/**)',
                              'Read(~/.claude.json)',
                              'Edit(~/.claude/**)',
                              'Edit(~/.claude.json)',
                              'Edit(~/.config/**)',
                              'Edit(~/.local/share/applications/**)',
                              'Edit(~/.local/bin/**)',
                              'Edit(~/.bashrc)',
                              'Edit(~/.bash_profile)',
                              'Edit(~/.bash_login)',
                              'Edit(~/.profile)',
                              'Edit(~/.zshrc)',
                              'Edit(~/.zprofile)',
                              'Edit(~/.zshenv)',
                              'Edit(~/.gitconfig)',
                              'Edit(**/.git/hooks/**)',
                              'Edit(**/.git/config)',
                              'Edit(**/.envrc)',
                              'Edit(**/.claude/**)',
                              'Edit(**/.mcp.json)',
                              'Edit(**/.vscode/**)',
                              'Edit(**/.idea/**)',
                              'Edit(//etc/claude-code/**)',
                              'Edit(//opt/aresos-control/**)']},
     'sandbox': {'enabled': True,
                 'failIfUnavailable': True,
                 'autoAllowBashIfSandboxed': False,
                 'allowUnsandboxedCommands': False,
                 'excludedCommands': [],
                 'enableWeakerNestedSandbox': False,
                 'allowNestedUserNamespaces': False,
                 'bwrapPath': '/usr/bin/bwrap',
                 'socatPath': '/usr/bin/socat',
                 'ripgrep': {'command': '/usr/bin/rg', 'args': []},
                 'ignoreViolations': {},
                 'credentials': {'files': [],
                                 'envVars': [],
                                 'allowPlaintextInject': False,
                                 'awsPairs': [],
                                 'sigv4': {'streaming': 'deny', 'presigned': 'deny', 'sigv4a': 'deny'}},
                 'network': {'allowManagedDomainsOnly': True,
                             'strictAllowlist': True,
                             'allowedDomains': [],
                             'deniedDomains': [],
                             'allowAllUnixSockets': False,
                             'allowLocalBinding': False,
                             'allowUnixSockets': [],
                             'allowMachLookup': []},
                 'filesystem': {'disabled': False,
                                'allowManagedReadPathsOnly': True,
                                'denyRead': ['/home',
                                             '/root',
                                             '/run/aresos-tools',
                                             '/var/lib/aresos-tools',
                                             '/run/user',
                                             '/tmp/.X11-unix'],
                                'allowRead': ['/home/assistant/work'],
                                'allowWrite': ['/home/assistant/work'],
                                'denyWrite': ['~/.bashrc',
                                              '~/.bash_profile',
                                              '~/.bash_login',
                                              '~/.profile',
                                              '~/.zshrc',
                                              '~/.zprofile',
                                              '~/.zshenv',
                                              '~/.gitconfig',
                                              '~/.config',
                                              '~/.local',
                                              '~/.claude',
                                              '~/.claude.json',
                                              '/etc/claude-code',
                                              '/opt/aresos-control',
                                              '/home/assistant/work']}},
     'allowManagedMcpServersOnly': True,
     'allowedMcpServers': []}
    settings['allowedMcpServers'] = [{'serverCommand': [v['command'], *v['args']]}
                                     for v in managed_servers().values()]
    settings['permissions']['ask'] += asking_rules()
    return settings
