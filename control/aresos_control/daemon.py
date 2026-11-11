import argparse
import os
from pathlib import Path
import selectors
import signal
import socket
import stat
import struct

from .common import FILE_LIMIT, Refused, cleanup, strict_json_loads, storage_refusal
from .engine import Engine
from .protocol import receive, send


class Daemon:
    def __init__(self, config, checkpoint=lambda _: None):
        self.config = config
        if config["owner_uid"] in {0, os.geteuid()}:
            raise ValueError("Owner must be a non-root user distinct from aresos-tools")
        self.engine = Engine(config["state_dir"], config["evidence_dir"], config.get("approval_ttl", 900), checkpoint, config.get("file_limit", FILE_LIMIT))
        self.selector, self.sockets, self.stopping = selectors.DefaultSelector(), [], False
        directory = Path(config["socket_dir"])
        directory.mkdir(mode=0o711, exist_ok=True)
        for kind in ("act", "admin", "chrome"):
            path = directory / (kind + ".sock")
            if path.exists():
                info = path.lstat()
                if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.geteuid():
                    raise ValueError("Refusing to replace an unexpected socket path")
                path.unlink()
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            listener.bind(str(path))
            # Peer credentials enforce identity even if the filesystem is made permissive.
            # act must be reachable without changing the service's supplementary groups.
            os.chmod(path, 0o666 if kind == "act" else 0o600)
            listener.listen(16)
            self.selector.register(listener, selectors.EVENT_READ, kind)
            self.sockets.append(listener)

    def serve(self):
        while not self.stopping:
            try:
                self.engine.expire()
            except Exception:
                # Engine records the cause and owner notice before re-raising.
                pass
            for key, _ in self.selector.select(timeout=0.1):
                connection, _ = key.fileobj.accept()
                with connection:
                    connection.settimeout(2)
                    authorized = False
                    try:
                        _, uid, _ = struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))
                        kind = key.data
                        if kind == "chrome" or uid != (0 if kind == "admin" else self.config["owner_uid"]):
                            raise Refused("permission_denied", "This peer is not permitted on this socket; use act as owner, admin via sudo. Chrome bridge accepts nothing.")
                        authorized = True
                        request = receive(connection)
                        if kind == "act" and type(request) is dict and request.get("method") in {"upload", "download"}:
                            self.engine.transfer(connection, request)
                            continue
                        result = self.engine.request(request, admin=kind == "admin")
                    except Exception as exc:
                        result = self.error_result(exc, authorized)
                    try:
                        send(connection, result, result=True)
                    except Exception:
                        pass

    def error_result(self, exc, authorized):
        from .results import bound_result
        exc = storage_refusal(exc) or exc
        pending = {"items": [], "total": 0, "cursor": None}
        if authorized:
            try:
                pending = self.engine.pending(resolve_checks=False)
            except Exception:
                pending = {**pending, 'restore_required': self.engine.store.locked,
                    'unavailable': 'Committed owner facts could not be read; inspect the independent evidence and service state before further changes.'}
        result = {"ok": False, "error": {"code": getattr(exc, "code", "internal_error"),
            "message": str(exc) if isinstance(exc, Refused) else "Request failed unexpectedly; inspect operation status before repeating changes."},
            "pending": pending}
        return bound_result(result, self.engine.store)

    def close(self):
        self.selector.close()
        for listener in self.sockets:
            listener.close()
        self.engine.close()


def main():
    parser = argparse.ArgumentParser(description="AresOS Unix-only tool service")
    parser.add_argument("--config", default="/etc/aresos-control/service.json")
    args = parser.parse_args()
    with open(args.config) as stream:
        config = strict_json_loads(stream.read())
    daemon = Daemon(config)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: setattr(daemon, "stopping", True))
    try:
        daemon.serve()
    finally:
        with cleanup('daemon close'):
            daemon.close()


if __name__ == "__main__":
    main()
