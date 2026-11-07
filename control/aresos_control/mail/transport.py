from contextlib import contextmanager
import imaplib
import os
import re
import smtplib
import ssl
import stat

from ..common import Refused
from .codec import utf7, unutf7


def context(account):
    # cafile is service-owned configuration, never a tool/caller path.
    ctx = ssl.create_default_context(cafile=account.get("ca_file"))
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


def quote(value):
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise Refused("invalid_input", "IMAP name contains controls; choose another name.")
    return '"' + utf7(value).replace('\\', '\\\\').replace('"', '\\"') + '"'


def ok(response, purpose):
    if response[0] != "OK":
        # Server text may include credentials or hostile content. Never echo it.
        raise Refused("server_refused", purpose + " refused by the server; refresh state or ask the owner to check capabilities.")
    return response[1]


class Transport:
    def __init__(self, password_dir):
        self.password_dir = password_dir
        password_dir.mkdir(mode=0o700, exist_ok=True)
        os.chmod(password_dir, 0o700)

    def password(self, account):
        from ..common import digest
        try:
            fd = os.open(self.password_dir / digest(account["id"]), os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "r") as stream:
                info = os.fstat(stream.fileno())
                if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600 or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise OSError()
                value = stream.read(8193)
                if not value or len(value) > 8192:
                    raise OSError()
                return value
        except OSError as exc:
            raise Refused("account_password", "Service password is missing, unreadable or not private; owner must add the account again over admin.sock.") from exc

    def store_password(self, account_id, value):
        from ..common import digest
        from ..storage import sync_directory
        import tempfile
        fd, name = tempfile.mkstemp(dir=self.password_dir)
        try:
            with os.fdopen(fd, "w") as stream:
                os.fchmod(stream.fileno(), 0o600)
                stream.write(value)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.password_dir / digest(account_id))
            sync_directory(self.password_dir)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    @contextmanager
    def imap(self, account):
        client = None
        try:
            client = imaplib.IMAP4_SSL(account["imap_host"], account["imap_port"], ssl_context=context(account), timeout=20)
            # TLS construction/hostname validation finished before the password is read.
            ok(client.login(account["username"], self.password(account)), "IMAP login")
            client.capabilities = tuple(x.decode("ascii").upper() for x in b" ".join(ok(client.capability(), "CAPABILITY")).split())
            if "CONDSTORE" in client.capabilities and "ENABLE" in client.capabilities:
                # Read HIGHESTMODSEQ where available; full re-reads remain authoritative.
                client.enable("QRESYNC" if "QRESYNC" in client.capabilities else "CONDSTORE")
            yield client
        finally:
            if client is not None:
                # LOGOUT never expunges; CLOSE does. UNSELECT where supported.
                try:
                    if client.state == "SELECTED" and "UNSELECT" in client.capabilities:
                        client.unselect()
                    client.logout()
                except (OSError, imaplib.IMAP4.error):
                    client.shutdown()

    @contextmanager
    def smtp(self, account):
        client = None
        try:
            if account["smtp_tls"] == "implicit":
                client = smtplib.SMTP_SSL(account["smtp_host"], account["smtp_port"], context=context(account), timeout=20)
                client.ehlo()
            elif account["smtp_tls"] == "starttls":
                client = smtplib.SMTP(account["smtp_host"], account["smtp_port"], timeout=20)
                client.ehlo()
                client.starttls(context=context(account))
                client.ehlo()
            else:
                raise Refused("refused", "Only implicit TLS or required STARTTLS submission is supported.")
            client.login(account["username"], self.password(account))
            yield client
        finally:
            if client is not None:
                # A QUIT failure cannot change a recorded successful DATA answer.
                client.close()


def folders(client):
    result = []
    for row in ok(client.list(), "LIST"):
        if not isinstance(row, bytes):
            raise Refused("unsupported_server", "Literal LIST names are unsupported; ask the owner to rename this folder in his mail program.")
        match = re.fullmatch(rb'\(([^)]*)\) (NIL|"(?:[^"\\]|\\.)*") (.*)', row)
        if not match:
            raise Refused("unsupported_server", "Unrecognized LIST response; stop and qualify this server.")
        flags, delimiter, name = match.groups()
        def unquote(value):
            if value.startswith(b'"'):
                value = re.sub(rb'\\(.)', rb'\1', value[1:-1])
            return value.decode("ascii")
        result.append({"name": unutf7(unquote(name)), "flags": flags.decode().split(),
                       "delimiter": None if delimiter == b"NIL" else unquote(delimiter)})
    return result


def select(client, folder, readonly=True):
    ok(client.select(quote(folder), readonly=readonly), "Open folder")
    values = client.response("UIDVALIDITY")[1]
    if not values or not values[0] or not values[0].isdigit():
        raise Refused("unsupported_server", "Server omitted UIDVALIDITY; exact references cannot be made safely.")
    return int(values[0])


def uids(client):
    values = ok(client.uid("SEARCH", None, "ALL"), "UID SEARCH")
    return [int(i) for i in (values[0] or b"").split()]


def fetch(client, uid, limit):
    # Refuse oversized literals before retrieving their body.
    metadata = ok(client.uid("FETCH", str(uid), "(UID FLAGS RFC822.SIZE)"), "UID metadata")
    rows = b" ".join(x for x in metadata if isinstance(x, bytes))
    size = re.search(rb"RFC822.SIZE (\d+)", rows)
    if size is None:
        raise Refused("stale_reference", "Message is stale, search again.")
    if int(size[1]) > limit:
        raise Refused("mail_too_large", "Mail exceeds the configured per-message byte limit; inspect it in the owner's mail program.")
    data = ok(client.uid("FETCH", str(uid), "(UID FLAGS BODY.PEEK[])"), "UID BODY.PEEK")
    for row in data:
        if isinstance(row, tuple) and re.search(rb"\bUID " + str(uid).encode() + rb"\b", row[0]):
            return row[1], sorted(f.decode("ascii", "replace") for f in imaplib.ParseFlags(row[0]))
    raise Refused("stale_reference", "Message is stale, search again.")
