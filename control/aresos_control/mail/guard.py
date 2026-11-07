"""Validate final bytes independently: no imports or MIME decisions from the builder."""
import base64
import binascii
from email import policy
from email.parser import BytesHeaderParser
from html.parser import HTMLParser
import quopri
import re

from ..common import Refused

MAX_BYTES = 64 * 1024 * 1024
MAX_WORK = 256 * 1024 * 1024
MAX_DEPTH = 40


class ReadableHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text, self.links, self.hidden = [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "head"}:
            self.hidden += 1
        if self.hidden:
            return
        if tag in {"br", "p", "div", "li", "tr", "blockquote", "h1", "h2", "h3"}:
            self.text.append("\n" + ("- " if tag == "li" else ""))
        if tag == "a":
            self.links.append(dict(attrs).get("href", ""))
        if tag == "img" and dict(attrs).get("alt"):
            self.text.append("[" + dict(attrs)["alt"] + "]")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "head"}:
            self.hidden = max(0, self.hidden - 1)
        if self.hidden:
            return
        if tag == "a" and self.links:
            self.text.append(" (" + self.links.pop() + ")")
        if tag in {"p", "div", "li", "tr", "blockquote"}:
            self.text.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.text.append(data)


def html_text(value):
    parser = ReadableHTML()
    parser.feed(value.replace("\r\n", "\n").replace("\r", "\n"))
    return re.sub(r"\n[ \t]*\n[ \t]*\n+", "\n\n", "".join(parser.text)).strip()



def check(raw, root_texts, disclosed_texts, draft=False):
    def refuse(reason):
        raise Refused("file_refused", "Outgoing MIME guard: " + reason + "; nothing submitted.")

    def normalized(text):
        return text.replace("\r\n", "\n").replace("\r", "\n").removesuffix("\n")

    root_texts = {normalized(text) for text in root_texts}
    disclosed_texts = {normalized(text) for text in disclosed_texts}
    work = 0

    def content(data):
        data = data.lstrip()
        return data[3:].lstrip() if data.startswith(b"\xef\xbb\xbf") else data

    def split(data):
        for line in re.finditer(rb"[^\r\n]*(?:\r\n|\r|\n|$)", data):
            if not line.group().rstrip(b"\r\n"):
                return data[:line.start()], data[line.end():]
        return data, b""

    def lines(data, marker_allowed=False, private_allowed=False):
        for line in re.split(rb"\r\n|\r|\n", data):
            if not private_allowed and re.match(rb"[ \t]*(?:bcc|resent-bcc)[ \t]*:", line, re.I):
                refuse("Bcc or Resent-Bcc line in decoded content (even a literal text-file line is refused)")
            if not marker_allowed and re.match(rb"[ \t]*x-aresos-authored[ \t]*:", line, re.I):
                refuse("authored marker outside the fully disclosed main body; drafts cannot be attachments")

    def readable(headers, payload):
        try:
            text = payload.decode(headers.get_content_charset() or "utf8", "strict")
        except (UnicodeError, LookupError):
            refuse("text cannot be decoded exactly for disclosure")
        return html_text(text) if headers.get_content_type() == "text/html" else text

    def complete_entity(data):
        head, _ = split(data)
        if not head or len(head) == len(data):
            return False
        continuation = False
        for index, line in enumerate(re.split(rb"\r\n|\n|\r", head.rstrip(b"\r\n"))):
            if index == 0 and line.startswith(b"From ") and not re.match(rb"From[ \t]*:", line):
                continue
            if line[:1] in (b" ", b"\t") and continuation:
                continue
            if not re.fullmatch(rb"[\x21-\x39\x3b-\x7e]+:[^\r\n]*", line):
                return False
            continuation = True
        parsed = BytesHeaderParser(policy=policy.default).parsebytes(head + b"\r\n\r\n")
        return bool(parsed.keys()) and not parsed.defects and not any(value.defects for value in parsed.values())

    def walk(data, root_body=False, depth=0, default="text/plain"):
        nonlocal work
        work += len(data)
        if depth > MAX_DEPTH or len(data) > MAX_BYTES or work > MAX_WORK:
            refuse("decoded content exceeds the safe depth or size limit")
        head, payload = split(data)
        continuation = False
        for index, line in enumerate(re.split(rb"\r\n|\n|\r", head.rstrip(b"\r\n"))):
            if not line and not head:
                break
            if index == 0 and line.startswith(b"From ") and not re.match(rb"From[ \t]*:", line):
                continue
            if line[:1] in (b" ", b"\t") and continuation:
                continue
            if not re.fullmatch(rb"[\x21-\x39\x3b-\x7e]+:[^\r\n]*", line):
                refuse("defective nested header block")
            continuation = True
        headers = BytesHeaderParser(policy=policy.default).parsebytes(head + b"\r\n\r\n")
        headers.set_default_type(default)
        if headers.defects or any(value.defects for value in headers.values()):
            refuse("defective MIME headers")
        for name in ("Content-Type", "Content-Transfer-Encoding", "Content-Disposition", "Content-Description"):
            if len(headers.get_all(name, [])) > 1:
                refuse("ambiguous MIME headers")
        lines(head, marker_allowed=draft and depth == 0, private_allowed=draft and depth == 0)
        if any(name.lower().startswith("x-aresos") for name in headers
               if not (draft and depth == 0 and name.lower() == "x-aresos-authored")):
            refuse("private X-AresOS header in outgoing mail")
        attached = headers.get_content_disposition() == "attachment" or headers.get_filename() is not None
        if root_body and attached:
            root_body = False
        encoding = str(headers.get("Content-Transfer-Encoding", "7bit")).lower().strip()
        major = headers.get_content_maintype()
        if major == "multipart" and encoding not in {"7bit", "8bit", "binary"}:
            refuse("transfer-encoded multipart cannot be inspected safely")
        if encoding == "base64":
            try:
                payload = base64.b64decode(re.sub(rb"[ \t\r\n]", b"", payload), validate=True)
            except (ValueError, binascii.Error):
                refuse("broken base64 transfer encoding")
        elif encoding == "quoted-printable":
            if re.search(rb"=(?![0-9A-Fa-f]{2}|\r?\n)", payload):
                refuse("broken quoted-printable transfer encoding")
            payload = quopri.decodestring(payload)
        elif encoding not in {"7bit", "8bit", "binary"}:
            refuse("unknown transfer encoding")
        elif major != "multipart" and encoding == "7bit" and not payload.isascii():
            refuse("non-ASCII bytes declared as 7bit")
        # Scan private lines at every decoded level. Marker checks on multipart
        # bytes wait for children, so literal, fully disclosed main text is allowed.
        lines(payload, marker_allowed=True)
        if major == "multipart":
            boundary = headers.get_boundary()
            if not boundary or not boundary.isascii():
                refuse("missing or unsupported multipart boundary")
            delimiter = b"--" + boundary.encode("ascii")
            chunks, start, end = [], None, None
            for line in re.finditer(rb"[^\r\n]*(?:\r\n|\r|\n|$)", payload):
                marker = line.group().rstrip(b"\r\n").rstrip(b" \t")
                if marker.startswith(delimiter) and marker not in {delimiter, delimiter + b"--"}:
                    refuse("ambiguous multipart boundary suffix")
                if marker not in {delimiter, delimiter + b"--"}:
                    continue
                if start is None:
                    lines(payload[:line.start()])
                else:
                    chunk = payload[start:line.start()]
                    chunks.append(chunk[:-2] if chunk.endswith(b"\r\n") else chunk[:-1] if chunk.endswith((b"\r", b"\n")) else chunk)
                if marker == delimiter + b"--":
                    end = line.end()
                    break
                start = line.end()
            if end is None or not chunks:
                refuse("broken multipart boundaries")
            lines(payload[end:])
            child_default = "message/rfc822" if headers.get_content_type() == "multipart/digest" else "text/plain"
            for chunk in chunks:
                walk(chunk, root_body, depth + 1, child_default)
            return
        if major == "message":
            if headers.get_content_type() not in {"message/rfc822", "message/global"}:
                refuse("unsupported encapsulated message type")
            walk(payload, False, depth + 1)
            return
        if major == "text":
            text = readable(headers, payload)
            if root_body and normalized(text) not in root_texts:
                refuse("generated body differs from the approved composition")
            # Text stays text, including complete From/Subject-looking prose.
            # Approval by reference is insufficient for a literal marker line.
            marker_allowed = root_body and normalized(text) in disclosed_texts
            lines(payload, marker_allowed=marker_allowed)
            try:
                decoded_text = payload.decode(headers.get_content_charset() or "utf8", "strict")
            except (UnicodeError, LookupError):
                refuse("text cannot be decoded exactly for disclosure")
            lines(decoded_text.encode("utf8"), marker_allowed=marker_allowed)
            lines(text.encode("utf8"), marker_allowed=marker_allowed)
        else:
            lines(payload)
            candidate = content(payload)
            if complete_entity(candidate):
                walk(candidate, False, depth + 1)

    walk(raw, root_body=True)


def check_headers(raw, approved, envelope, draft=False):
    """Decode the exact wire headers and compare semantic names and addresses."""
    from email.utils import getaddresses

    def refuse():
        raise Refused("file_refused", "Outgoing header guard: decoded headers or SMTP envelope differ from approval; nothing submitted.")

    head = re.split(rb"\r\n\r\n|\n\n|\r\r", raw, maxsplit=1)[0]
    headers = BytesHeaderParser(policy=policy.default).parsebytes(head + b"\r\n\r\n")
    if headers.defects:
        refuse()
    for key in ("Subject", "From", "To", "Cc", "Bcc"):
        values = headers.get_all(key, [])
        expected = approved[key.lower()]
        if len(values) > 1 or any(v.defects for v in values):
            refuse()
        if key == "Subject":
            actual = str(values[0]) if values else ""
            if actual != expected:
                refuse()
        else:
            expected_values = [expected] if key == "From" else expected
            if key == "Bcc" and not draft:
                expected_values = []
            actual = [(a.display_name, a.addr_spec) for v in values for a in v.addresses]
            wanted = getaddresses(expected_values) if expected_values else []
            if actual != wanted:
                refuse()
        for v in values:
            if any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in str(v)):
                refuse()
    wanted_envelope = [addr for _, addr in getaddresses(approved["to"] + approved["cc"] + approved["bcc"])]
    if list(envelope) != wanted_envelope:
        refuse()
