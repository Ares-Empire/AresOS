#!/usr/bin/python3
# DEVELOPMENT AID of package 25 (the real-game check), headless use only.
"""usage: supervisor.py <config.json>

Runs the worktree's real supervisor (os/config/usr/libexec/aresos-desktop, its real loop) for the rig, as
os/tests/test_aresos_guardian_loop.py's harness does: with stand-ins for Prism (never to be started here), the app
helper, the cover, the message window and systemd-inhibit, and without a scope for a game it never starts. check.py
starts it under `env -i` with HOME, the run's temporary XDG_RUNTIME_DIR, PATH and the LABWC_PID of a stand-in, so it
can reach nothing of the owner's session. The game it adopts is the rig's own."""
import importlib.machinery
import json
import os
import sys
import types

sys.dont_write_bytecode = True
config = json.load(open(sys.argv[1]))
loader = importlib.machinery.SourceFileLoader('aresos_desktop', config['desktop'])
desktop = types.ModuleType(loader.name)
sys.modules[loader.name] = desktop
loader.exec_module(desktop)
desktop.HELPER, desktop.COVER, desktop.VIEW_COMMAND = config['helper'], config['cover'], [config['view']]
desktop.SYSTEMD_INHIBIT = config['inhibit']  # always the stand-in: the rig takes no logind inhibitor
desktop.prism_command = lambda lock, launch_id, world=None: [config['prism']]
desktop.game_scope = lambda launch_id: []
desktop.Runner.real = False
paths = desktop.Paths(os.environ['HOME'], os.environ['XDG_RUNTIME_DIR'], config['share'])
sys.exit(desktop.supervise(paths))
