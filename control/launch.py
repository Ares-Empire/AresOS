"""Installed root-owned. ALWAYS invoke /usr/bin/python3 -I -S with env -i.

-S prevents sitecustomize AND .pth execution, including .pth in vendor. -I blocks
the current directory, user site and PYTHONPATH before this script starts.
"""
import json
import os
from pathlib import Path
import stat
import sys

PREFIX = Path("/usr/libexec/aresos-control")
VENDOR = Path("/usr/lib/aresos-control/vendor")
CONFIG = Path("/etc/aresos-control")


def protected(path):
    for part in [path, *path.parents]:
        metadata = part.lstat()
        if stat.S_ISLNK(metadata.st_mode) or metadata.st_uid != 0 or metadata.st_mode & 0o022:
            raise SystemExit("AresOS requires root-owned non-writable code, dependencies and configuration: " + str(part))


def main():
    if not sys.flags.isolated or not sys.flags.no_site:
        raise SystemExit("Use the fixed isolated launcher: /usr/bin/python3 -I -S")
    for path in (PREFIX, VENDOR, CONFIG):
        protected(path)
        # No writable package files or symlinks under a protected top-level folder.
        for child in path.rglob("*"):
            protected(child)
    os.environ.clear()
    os.environ.update({"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"})
    sys.dont_write_bytecode = True
    sys.path.extend([str(PREFIX), str(VENDOR)])
    if len(sys.argv) < 2:
        raise SystemExit("Expected proxy, cli, hook or service")
    mode = sys.argv[1]
    with (CONFIG / ("service.json" if mode == "service" else "proxy.json")).open() as stream:
        config = json.load(stream)
    if mode == "proxy" and len(sys.argv) == 3:
        owner_uid = json.loads((CONFIG / "service.json").read_text())["owner_uid"]
        if owner_uid <= 0 or os.getuid() != owner_uid:
            raise SystemExit("AresOS MCP proxy requires the configured assistant user.")
        from aresos_control.proxy import main as proxy_main
        proxy_main(sys.argv[2], config)
    elif mode == "cli":
        from aresos_control.cli import main as cli_main
        raise SystemExit(cli_main(config, sys.argv[2:]))
    elif mode == "hook" and len(sys.argv) == 3 and sys.argv[2] in {"Stop", "UserPromptSubmit"}:
        from aresos_control.hooks import main as hook_main
        hook_main(config, sys.argv[2])
    elif mode == "service" and len(sys.argv) == 2:
        from aresos_control.daemon import main as daemon_main
        sys.argv = [sys.argv[0], "--config", str(CONFIG / "service.json")]
        daemon_main()
    else:
        raise SystemExit("Invalid launcher arguments")


if __name__ == "__main__":
    try:
        main()
    except (Exception, SystemExit):
        # The prompt event is known before parsing input or loading configuration.
        # Even a broken installation must never discard the owner's prompt.
        if sys.argv[1:] != ["hook", "UserPromptSubmit"]:
            raise
