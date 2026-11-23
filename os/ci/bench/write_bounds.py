"""Kernel write restrictions for the bench's regular-file workload contract."""
import ctypes
import errno
import os
import platform
import resource
import stat

# Linux x86-64 syscall numbers. Other hosts must fail before executing a workload.
CREATE_RULESET, ADD_RULE, RESTRICT_SELF = 444, 445, 446
WRITE_FILE = 1 << 1
TRUNCATE = 1 << 14
# Deny file creation, removal, reparenting and writes outside the allowed files.
HANDLE = WRITE_FILE | TRUNCATE | sum(1 << bit for bit in range(4, 14))

# The regular-file contract excludes allocation/ioctl shortcuts, xattr storage and host brokers.
BLOCKED_SYSCALLS = {
    'ioctl': 16, 'socket': 41, 'setxattr': 188, 'lsetxattr': 189, 'fsetxattr': 190,
    'fallocate': 285, 'io_uring_setup': 425, 'setxattrat': 463,
}


class PathRule(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('access', ctypes.c_uint64), ('parent_fd', ctypes.c_int32)]


class Instruction(ctypes.Structure):
    _fields_ = [('op', ctypes.c_uint16), ('yes', ctypes.c_uint8), ('no', ctypes.c_uint8),
                ('value', ctypes.c_uint32)]


class Filter(ctypes.Structure):
    _fields_ = [('length', ctypes.c_uint16), ('instructions', ctypes.POINTER(Instruction))]


def checked(result):
    if result < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return result


def restrict_file_operations(libc):
    load, equal, at_least, ret = 0x20, 0x15, 0x35, 0x06
    deny, allow = 0x50000 | errno.EPERM, 0x7fff0000
    instructions = [
        (load, 0, 0, 4),                 # seccomp_data.arch
        (equal, 1, 0, 0xc000003e),       # AUDIT_ARCH_X86_64
        (ret, 0, 0, deny),
        (load, 0, 0, 0),                 # seccomp_data.nr
        (at_least, 0, 1, 0x40000000),    # Reject the x32 syscall table.
        (ret, 0, 0, deny),
    ]
    for number in BLOCKED_SYSCALLS.values():
        instructions.extend([(equal, 0, 1, number), (ret, 0, 0, deny)])
    instructions.append((ret, 0, 0, allow))
    program = (Instruction * len(instructions))(*(Instruction(*line) for line in instructions))
    rule = Filter(len(program), program)
    checked(libc.prctl(22, 2, ctypes.byref(rule), 0, 0))  # PR_SET_SECCOMP, filter mode


def restrict_writes(files, file_limit):
    if platform.machine() != 'x86_64':
        raise ValueError('bench write enforcement requires Linux x86-64')
    libc = ctypes.CDLL(None, use_errno=True)
    if checked(libc.syscall(CREATE_RULESET, None, 0, 1)) < 3:
        raise ValueError('bench write enforcement requires Landlock ABI 3 or newer')
    rights = ctypes.c_uint64(HANDLE)
    ruleset = checked(libc.syscall(CREATE_RULESET, ctypes.byref(rights), ctypes.sizeof(rights), 0))
    try:
        for file in files:
            fd = os.open(file, os.O_PATH | os.O_NOFOLLOW)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid():
                    raise ValueError('declared writable file is not private to the bench phase')
                rule = PathRule(WRITE_FILE | TRUNCATE, fd)
                checked(libc.syscall(ADD_RULE, ruleset, 1, ctypes.byref(rule), 0))
            finally:
                os.close(fd)
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        checked(libc.prctl(38, 1, 0, 0, 0))  # PR_SET_NO_NEW_PRIVS
        checked(libc.syscall(RESTRICT_SELF, ruleset, 0))
        restrict_file_operations(libc)
    finally:
        os.close(ruleset)
