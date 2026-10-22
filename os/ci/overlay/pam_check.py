"""Use login's unchanged PAM stack with a conversation callback, not a TTY."""
import ctypes as c
import json
import pwd
import sys


class Message(c.Structure):
    _fields_ = [('style', c.c_int), ('message', c.c_char_p)]


class Response(c.Structure):
    _fields_ = [('response', c.c_void_p), ('code', c.c_int)]


Callback = c.CFUNCTYPE(c.c_int, c.c_int, c.POINTER(c.POINTER(Message)),
                      c.POINTER(c.POINTER(Response)), c.c_void_p)


class Conversation(c.Structure):
    _fields_ = [('callback', Callback), ('data', c.c_void_p)]


def authenticate(password):
    pam = c.CDLL('libpam.so.0')
    libc = c.CDLL(None)
    libc.calloc.argtypes = [c.c_size_t, c.c_size_t]
    libc.calloc.restype = c.c_void_p
    libc.strdup.argtypes = [c.c_char_p]
    libc.strdup.restype = c.c_void_p
    libc.free.argtypes = [c.c_void_p]
    pam.pam_start.argtypes = [c.c_char_p, c.c_char_p, c.POINTER(Conversation), c.POINTER(c.c_void_p)]
    pam.pam_set_item.argtypes = [c.c_void_p, c.c_int, c.c_void_p]
    pam.pam_get_item.argtypes = [c.c_void_p, c.c_int, c.POINTER(c.c_void_p)]
    for name in ('pam_authenticate', 'pam_acct_mgmt', 'pam_end'):
        getattr(pam, name).argtypes = [c.c_void_p, c.c_int]
    prompts = []

    @Callback
    def converse(count, messages, responses, _data):
        # Linux-PAM owns and frees successful responses. Never return Python memory.
        if not 0 < count <= 32:
            return 19  # PAM_CONV_ERR
        allocation = libc.calloc(count, c.sizeof(Response))
        if not allocation:
            return 5  # PAM_BUF_ERR
        answers = c.cast(allocation, c.POINTER(Response))
        for index in range(count):
            style = messages[index].contents.style
            prompts.append(style)
            if style in (1, 2):  # PAM_PROMPT_ECHO_OFF / PAM_PROMPT_ECHO_ON
                answers[index].response = libc.strdup(password.encode() if style == 1 else b'root')
                if answers[index].response:
                    continue
            elif style in (3, 4):  # PAM_ERROR_MSG / PAM_TEXT_INFO
                continue
            for allocated in range(index + 1):
                libc.free(answers[allocated].response)
            libc.free(allocation)
            return 19
        responses[0] = answers
        return 0

    handle = c.c_void_p()
    conversation = Conversation(converse, None)
    status = pam.pam_start(b'login', b'root', c.byref(conversation), c.byref(handle))
    result = dict(service='login', tty='/dev/tty3', start=status)
    if status:
        return result
    try:
        status = pam.pam_set_item(handle, 3, c.cast(c.c_char_p(b'/dev/tty3'), c.c_void_p))  # PAM_TTY
        assert status == 0, status
        status = pam.pam_authenticate(handle, 1)  # PAM_DISALLOW_NULL_AUTHTOK
        result.update(authenticate=status, password_prompts=prompts.count(1))
        if status == 0:
            status = pam.pam_acct_mgmt(handle, 0)
            result['account'] = status
            username = c.c_void_p()
            assert pam.pam_get_item(handle, 2, c.byref(username)) == 0  # PAM_USER
            result['user'] = c.string_at(username).decode()
            result['uid'] = pwd.getpwnam(result['user']).pw_uid
        return result
    finally:
        pam.pam_end(handle, status)


if __name__ == '__main__':
    password = json.load(sys.stdin)['password']
    # A root-run probe must still reject a wrong password; rootok cannot fake a pass.
    rejected = authenticate(password + '-wrong')
    accepted = authenticate(password)
    result = dict(wrong_password=rejected, correct_password=accepted)
    print(json.dumps(result), flush=True)
    assert rejected.get('authenticate') == 7 and rejected['password_prompts'] > 0, result
    assert accepted.get('authenticate') == 0 and accepted.get('account') == 0, result
    assert accepted['password_prompts'] > 0 and accepted['user'] == 'root' and accepted['uid'] == 0, result
