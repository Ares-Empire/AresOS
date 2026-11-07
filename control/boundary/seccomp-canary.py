import errno
import socket

for family in (socket.AF_UNIX, socket.AF_VSOCK):
    try:
        socket.socket(family, socket.SOCK_STREAM)
    except OSError as error:
        if error.errno != errno.EPERM:
            raise
    else:
        raise SystemExit('seccomp canary unexpectedly created socket')
print('SECCOMP_CANARY_OK')
