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
                refuse("authored marker is not shown in full in the approval")

    def readable(headers, payload):
        try:
            text = payload.decode(headers.get_content_charset() or "utf8", "strict")
        except (UnicodeError, LookupError):
            refuse("text cannot be decoded exactly for disclosure")
        return html_text(text) if headers.get_content_type() == "text/html" else text

    def walk(data, inherited=False, root_body=False, depth=0, default="text/plain"):
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
        lines(head, marker_allowed=True, private_allowed=draft and depth == 0)
        attached = headers.get_content_disposition() == "attachment" or headers.get_filename() is not None
        if root_body and attached:
            inherited, root_body = False, False
        own_marker = "X-AresOS-Authored" in headers
        described = str(headers.get("Content-Description", "")) == "AresOS authored text; full approval required"
        marked = inherited or own_marker or described
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
        # Private header-shaped lines are refused anywhere, including plain files.
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
                walk(chunk, marked, root_body, depth + 1, child_default)
            return
        if major == "message":
            if headers.get_content_type() not in {"message/rfc822", "message/global"}:
                refuse("unsupported encapsulated message type")
            walk(payload, marked if not root_body else own_marker, False, depth + 1)
            return
        allowed_texts = root_texts if root_body else disclosed_texts
        if root_body and major == "text":
            if normalized(readable(headers, payload)) not in root_texts:
                refuse("generated body differs from the approved composition")
        # Every decoded leaf is parsed again, regardless of its filename/type.
        # A non-entity stays opaque only after both line scanning and this parse.
        candidate = content(payload)
        nested_head, _ = split(candidate)
        nested = BytesHeaderParser(policy=policy.default).parsebytes(nested_head + b"\r\n\r\n")
        if nested.keys() or re.search(rb"(?im)^[ \t]*[\x21-\x39\x3b-\x7e]+[ \t]*:", nested_head):
            walk(candidate, marked if not root_body else False, False, depth + 1)
        else:
            if marked and major == "text" and not root_body and normalized(readable(headers, payload)) not in disclosed_texts:
                refuse("authored text is not shown in full in the approval")
            marker_allowed = major == "text" and normalized(readable(headers, payload)) in allowed_texts if (own_marker or re.search(rb"(?im)^[ \t]*x-aresos-authored[ \t]*:", payload)) else False
            lines(payload, marker_allowed=marker_allowed)
            if own_marker and not marker_allowed:
                refuse("marked non-text payload cannot be disclosed safely")

    walk(raw, root_body=True)
