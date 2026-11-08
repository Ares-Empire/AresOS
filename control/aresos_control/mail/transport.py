from contextlib import contextmanager
import base64
import imaplib
import os
import re
import smtplib
import ssl
import stat

from ..common import Refused
from ..adapters import Uncertain
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


def nonempty_refusal(response):
    if response[0] != "NO":
        return False
    text = b" ".join(row for row in response[1] if isinstance(row, bytes)).upper()
    codes = re.findall(rb"\[([A-Z0-9-]+)(?:[^\]]*)\]", text)
    # CANNOT alone is generic too; require explicit nonempty semantics as well.
    return (all(code == b"CANNOT" for code in codes)
            and bool(re.search(rb"NON[- ]?EMPTY|NOT EMPTY|CONTAINS MESSAGES|HOLDS MAIL", text)))


class Transport:
    def __init__(self, password_dir, ledger=None):
        self.password_dir = password_dir
        from ..space import SpaceLedger
        self.ledger = ledger or SpaceLedger((password_dir,))
        self.secrets = set()
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
                self.remember(account["username"], value)
                return value
        except OSError as exc:
            raise Refused("account_password", "Service password is missing, unreadable or not private; owner must add the account again over admin.sock.") from exc

    def store_password(self, account_id, value):
        from ..common import digest
        from ..storage import sync_directory
        import tempfile
        self.ledger.admit(len(value.encode()) + 16384)
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

    def remember(self, username, password):
        values = [password, "\0" + username + "\0" + password, username + "\0" + username + "\0" + password]
        self.secrets.add(password)
        self.secrets.add(password.replace("\\", "\\\\").replace('"', '\\"'))
        for value in values:
            self.secrets.add(base64.b64encode(value.encode()).decode())

    def scrub(self, value):
        if isinstance(value, str):
            for secret in sorted(self.secrets, key=len, reverse=True):
                if secret:
                    value = value.replace(secret, "[credential removed]")
            return value
        if isinstance(value, list):
            return [self.scrub(v) for v in value]
        if isinstance(value, dict):
            return {self.scrub(k): self.scrub(v) for k, v in value.items()}
        return value

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
        except imaplib.IMAP4.abort:
            raise Uncertain("IMAP connection lost; outcome uncertain. Inspect operation status; never retry automatically.") from None
        except imaplib.IMAP4.error:
            raise Refused("imap_error", "IMAP command failed; inspect operation status before repeating changes. No automatic retry.") from None
        finally:
            if client is not None:
                # LOGOUT never expunges; CLOSE does. UNSELECT where supported.
                try:
                    if client.state == "SELECTED" and "UNSELECT" in client.capabilities:
                        client.unselect()
                    client.logout()
                except (OSError, imaplib.IMAP4.error):
                    try:
                        client.shutdown()
                    except OSError:
                        pass

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
        except smtplib.SMTPResponseException as exc:
            # Retain DATA's numeric refusal evidence, never its untrusted response text.
            error = smtplib.SMTPDataError if isinstance(exc, smtplib.SMTPDataError) else smtplib.SMTPResponseException
            raise error(exc.smtp_code, b"SMTP command refused; inspect operation status.") from None
        except smtplib.SMTPException as exc:
            if isinstance(exc, smtplib.SMTPNotSupportedError):
                raise smtplib.SMTPNotSupportedError("Required SMTP capability unavailable; no plaintext fallback.") from None
            raise smtplib.SMTPException("SMTP transport failed; inspect operation status. No automatic retry.") from None
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


def fetch_headers(client, uid):
    data = ok(client.uid("FETCH", str(uid), "(UID FLAGS RFC822.SIZE BODY.PEEK[HEADER])"), "UID headers PEEK")
    for row in data:
        if isinstance(row, tuple) and re.search(rb"\bUID " + str(uid).encode() + rb"\b", row[0]):
            size = re.search(rb"RFC822.SIZE (\d+)", row[0])
            if not size:
                raise Refused("unsupported_server", "Server omitted message size from header fetch.")
            return row[1], sorted(f.decode("ascii", "replace") for f in imaplib.ParseFlags(row[0])), int(size[1])
    raise Refused("stale_reference", "Message is stale, search again.")
