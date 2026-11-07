"""Recipient-side validation of final wire bytes, independent of the sanitizer tree."""
import base64
import binascii
from email import policy
from email.parser import BytesHeaderParser
import quopri
import re

from ..common import Refused
from .codec import AUTHORED_HEADER, html_text, is_mail, mail_content


def check(raw, root_texts, disclosed_texts, draft=False):
    def refuse(reason):
        raise Refused("file_refused", "Outgoing MIME guard: " + reason + "; nothing submitted.")

    def normalized(text):
        return text.replace("\r\n", "\n").replace("\r", "\n").removesuffix("\n")

    root_texts = {normalized(text) for text in root_texts}
    disclosed_texts = {normalized(text) for text in disclosed_texts}

    def walk(data, inherited=False, root_body=False, depth=0):
        if depth > 40:
            refuse("mail nesting exceeds the safe inspection limit")
        data = mail_content(data)
        split = re.search(rb"\r\n\r\n|\n\n|\r\r", data)
        head, payload = (data[:split.start()], data[split.end():]) if split else (data, b"")
        # Scan actual lines, even ones the MIME parser would discard after a defect.
        continuation = False
        for index, line in enumerate(re.split(rb"\r\n|\n|\r", head)):
            if index == 0 and line.startswith(b"From ") and not re.match(rb"From[ \t]*:", line):
                continue
            if line[:1] in (b" ", b"\t") and continuation:
                continue
            if not re.fullmatch(rb"[\x21-\x39\x3b-\x7e]+:[^\r\n]*", line):
                refuse("defective nested header block")
            continuation = True
        headers = BytesHeaderParser(policy=policy.default).parsebytes(head + b"\r\n\r\n")
        if headers.defects or any(value.defects for value in headers.values()):
            refuse("defective MIME headers")
        for name in ("Content-Type", "Content-Transfer-Encoding", "Content-Disposition"):
            if len(headers.get_all(name, [])) > 1:
                refuse("ambiguous MIME headers")
        if ("Bcc" in headers or "Resent-Bcc" in headers) and not (draft and depth == 0):
            refuse("Bcc or Resent-Bcc remains in recipient-visible headers")
        attached = headers.get_content_disposition() == "attachment" or headers.get_filename() is not None
        if root_body and attached:
            inherited, root_body = False, False
        marked = inherited or AUTHORED_HEADER in headers
        encoding = str(headers.get("Content-Transfer-Encoding", "7bit")).lower().strip()
        major = headers.get_content_maintype()
        if major == "multipart" and encoding not in {"7bit", "8bit", "binary"}:
            refuse("transfer-encoded multipart cannot be inspected safely")
        if encoding == "base64":
            try:
                payload = base64.b64decode(b"".join(payload.split()), validate=True)
            except (ValueError, binascii.Error):
                refuse("broken base64 transfer encoding")
        elif encoding == "quoted-printable":
            if re.search(rb"=(?![0-9A-Fa-f]{2}|\r?\n)", payload):
                refuse("broken quoted-printable transfer encoding")
            payload = quopri.decodestring(payload)
        elif encoding not in {"7bit", "8bit", "binary"}:
            refuse("unknown transfer encoding")
        elif encoding == "7bit" and not payload.isascii():
            refuse("non-ASCII bytes declared as 7bit")
        if major == "multipart":
            boundary = headers.get_boundary()
            if not boundary or not boundary.isascii():
                refuse("missing or unsupported multipart boundary")
            delimiter = b"--" + boundary.encode("ascii")
            chunks, current, closed = [], None, False
            for line in payload.splitlines(keepends=True):
                marker = line.rstrip(b"\r\n").rstrip(b" \t")
                if marker in {delimiter, delimiter + b"--"}:
                    if current is not None:
                        chunk = b"".join(current)
                        # The CRLF introducing a delimiter belongs to the boundary (RFC 2046).
                        chunks.append(chunk.removesuffix(b"\r\n") if chunk.endswith(b"\r\n") else chunk.removesuffix(b"\n"))
                    if marker == delimiter + b"--":
                        closed = True
                        break
                    current = []
                elif current is not None:
                    current.append(line)
            if not closed or not chunks:
                refuse("broken multipart boundaries")
            for chunk in chunks:
                walk(chunk, marked, root_body, depth + 1)
            return
        payload_head = re.split(rb"\r\n\r\n|\n\n|\r\r", mail_content(payload), maxsplit=1)[0]
        frozen_entity = re.search(rb"(?im)^(?:content-type[ \t]*:[ \t\r\n]*(?:multipart|message)/|x-aresos-authored[ \t]*:)", payload_head)
        mail_name = (headers.get_filename() or "").lower().endswith((".eml", ".msg"))
        if major == "message" or is_mail(payload) or frozen_entity or mail_name:
            if major == "message" and headers.get_content_type() not in {"message/rfc822", "message/global"}:
                refuse("unsupported encapsulated message type")
            # The service marker covers its body, not unrelated source attachments.
            walk(payload, marked if not root_body else AUTHORED_HEADER in headers, False, depth + 1)
            return
        if headers.get_content_type() in {"text/plain", "text/html"}:
            try:
                text = payload.decode(headers.get_content_charset() or "utf8", "strict")
            except (UnicodeError, LookupError):
                refuse("text cannot be decoded exactly for disclosure")
            if headers.get_content_type() == "text/html":
                text = html_text(text)
            allowed = root_texts if root_body and not attached else disclosed_texts
            if (marked or root_body and not attached) and normalized(text) not in allowed:
                refuse("authored text is not shown in full in the approval")
        elif AUTHORED_HEADER in headers:
            refuse("marked non-text payload cannot be disclosed safely")

    walk(raw, root_body=True)
