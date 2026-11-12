import socket
import time
for host, port in (("greenmail", 3993), ("greenmail", 3465), ("dovecot", 993)):
    for attempt in range(90):
        try:
            with socket.create_connection((host, port), timeout=1):
                break
        except OSError:
            time.sleep(1)
    else:
        raise SystemExit(f"Fixture not ready: {host}:{port}")
    print(f"Fixture ready: {host}:{port}")
