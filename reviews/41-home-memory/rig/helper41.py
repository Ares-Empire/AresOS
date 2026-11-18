#!/usr/bin/python3
# DEVELOPMENT AID of package 41 (measurement only): the worktree's app helper, seeing only the rig's test apps.
"""usage: helper41.py <apps folder> [aresos-shell arguments...]

Runs the worktree's os/config/usr/libexec/aresos-shell unchanged, except that its discovery looks only at
<apps folder>/applications and its icon lookup only at <apps folder>/icons (make-apps.py writes both): the system's
and Flatpak's program folders would put the laptop's installed programs into the town."""
import importlib.machinery, importlib.util, os, sys

apps = os.path.abspath(sys.argv[1])
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../os/config/usr/libexec/aresos-shell')
loader = importlib.machinery.SourceFileLoader('aresos_shell', os.path.abspath(path))
spec = importlib.util.spec_from_loader('aresos_shell', loader)
shell = importlib.util.module_from_spec(spec)
sys.modules['aresos_shell'] = shell
loader.exec_module(shell)
shell.desktop_directories = lambda environ=None: (os.path.join(apps, 'applications'),)
shell.icon_directories = lambda environ=None: (os.path.join(apps, 'icons'),)
shell.flatpak_deployments = lambda environ=None: ()
sys.exit(shell.main(sys.argv[2:]))
