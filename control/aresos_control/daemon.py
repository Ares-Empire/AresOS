import argparse
import os
from pathlib import Path
import selectors
import signal
import socket
import stat
import struct
import time

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
            os.chmod(path, 0o666 if kind in {"act", "chrome"} else 0o600)
            listener.listen(16)
            self.selector.register(listener, selectors.EVENT_READ, kind)
            self.sockets.append(listener)

    def serve(self):
        refresh_at = 0
        while not self.stopping:
            bridge=getattr(self,'chrome_bridge',None)
            if bridge is not None and bridge.connection is not None and b'\n' in bridge.buffer:
                self.drain_chrome_events(bridge.connection,buffered=True)
                if b'\n' in bridge.buffer:
                    continue
            if time.monotonic() >= refresh_at:
                refresh_at = time.monotonic() + 60
                try:
                    self.engine.adapters['chrome'].maintenance()
                except Exception as exc:
                    self.engine.background_error(exc)
            try:
                self.engine.expire()
            except Exception:
                # Engine records the cause and owner notice before re-raising.
                pass
            for key, _ in self.selector.select(timeout=0.1):
                if key.data == 'chrome-peer':
                    self.drain_chrome_events(key.fileobj)
                    if b'\n' in self.engine.adapters['chrome'].bridge.buffer:
                        break
                    continue
                connection, _ = key.fileobj.accept()
                connection.settimeout(2)
                if key.data == 'chrome':
                    try:
                        _, uid, _ = struct.unpack('3i', connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i')))
                        if uid != self.config['owner_uid']:
                            raise Refused('permission_denied', 'Chrome native host must run as the configured owner.')
                        self.register_chrome_host(connection)
                        # A coalesced hello can already contain observations.
                        if b'\n' in self.chrome_bridge.buffer:
                            break
                    except Exception as exc:
                        try:
                            send(connection, self.error_result(exc, False), result=True)
                        except Exception:
                            pass
                        finally:
                            connection.close()
                    continue
                with connection:
                    connection.settimeout(2)
                    authorized = False
                    try:
                        _, uid, _ = struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))
                        kind = key.data
                        if uid != (0 if kind == "admin" else self.config["owner_uid"]):
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

    def drain_chrome_events(self,connection,buffered=False):
        bridge=self.engine.adapters['chrome'].bridge
        try:
            for index in range(128):
                if (buffered or index) and b'\n' not in bridge.buffer:
                    break
                bridge.on_event(bridge.read())
        except Exception as exc:
            try:self.selector.unregister(connection)
            except Exception:pass
            bridge.close()
            self.engine.background_error(exc)

    def register_chrome_host(self, connection):
        bridge = self.engine.adapters['chrome'].bridge
        for key in list(self.selector.get_map().values()):
            if key.data=='chrome-peer' and key.fileobj is not bridge.connection:
                self.selector.unregister(key.fd)
        previous = bridge.connection
        previous_fd = previous.fileno() if previous is not None else None
        try:
            try:
                bridge.accept(connection)
            finally:
                # A peer may be retired before its replacement is rejected.
                if previous is not None and bridge.connection is not previous:
                    try:
                        self.selector.unregister(previous_fd)
                    except KeyError:
                        pass
            connection.settimeout(15)
            self.selector.register(connection, selectors.EVENT_READ, 'chrome-peer')
            self.chrome_bridge=bridge
        except Exception:
            if bridge.connection is connection:
                # The caller sends a refusal before closing this descriptor.
                bridge.connection, bridge.buffer = None, b''
                bridge.session = bridge.version = None
            raise
        # An uncovered build/version is refreshed on connection, even before
        # the first tool call; daily maintenance remains the offline retry.
        try:
            self.engine.adapters['chrome'].maintenance()
        except Exception as exc:
            self.engine.background_error(exc)

    def error_result(self, exc, authorized):
        from .results import bound_result
        exc = storage_refusal(exc) or exc
        pending = {"items": [], "total": 0, "cursor": None}
        if authorized:
            try:
                pending = self.engine.pending(resolve_checks=False)
            except Exception:
                pending = {**self.engine._last_pending.get(None, pending),
                           "unavailable": "Live pending read failed; inspect this snapshot and service state before further changes."}
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
