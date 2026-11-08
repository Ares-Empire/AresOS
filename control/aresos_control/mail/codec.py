import base64
import binascii
from datetime import timezone
from email import policy
from email.message import EmailMessage
from email.parser import BytesHeaderParser
from email.feedparser import BytesFeedParser
from email.utils import getaddresses, parsedate_to_datetime
from html import escape
from html.parser import HTMLParser
import re
import quopri
from urllib.parse import urlsplit

from ..common import canonical, Refused, sha256

SMTP_POLICY = policy.SMTP.clone(cte_type="7bit", max_line_length=78)
AUTHORED_HEADER = "X-AresOS-Authored"


MIME_DEPTH_LIMIT = 40
MIME_PART_LIMIT = 1000


class BoundedParser(BytesFeedParser):
    def __init__(self):
        super().__init__(policy=policy.default)
        self.part_count = 0

    def _new_message(self):
        # Enforce bounds before allocating/attaching a node or recursing into it.
        # This hook also covers implicit children of multipart/digest and message/*.
        self.part_count += 1
        if len(self._msgstack) > MIME_DEPTH_LIMIT or self.part_count > MIME_PART_LIMIT:
            raise Refused('mime_limit', f'MIME exceeds depth {MIME_DEPTH_LIMIT} or part count {MIME_PART_LIMIT}.')
        super()._new_message()


def parse(raw, reference=None):
    try:
        if len(raw) > 64 * 1024 * 1024:
            raise Refused('mime_limit', 'Mail exceeds 64 MiB parse limit.')
        parser = BoundedParser()
        for offset in range(0, len(raw), 65536):
            parser.feed(raw[offset:offset + 65536])
        return parser.close()
    except (Refused, RecursionError, MemoryError) as exc:
        name = canonical(reference) if reference else 'unidentified message'
        raise Refused('mime_limit', f'Message {name} cannot be parsed within MIME bounds; read another message or use your mail program. {exc}') from exc


def mail_content(raw):
    raw = raw.lstrip()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:].lstrip()
    return raw


def is_mail(raw):
    # Local names and MIME types are caller-controlled; inspect the header block.
    headers = set()
    for line in re.split(rb"\r\n|\n|\r", mail_content(raw)):
        if not line:
            break
        match = re.match(rb"[ \t]*([\x21-\x39\x3b-\x7e]+)[ \t]*:", line)
        if match:
            headers.add(match[1].lower())
    return b"from" in headers and bool(headers & {
        b"date", b"subject", b"message-id", b"received", b"mime-version",
        b"bcc", b"resent-bcc", b"x-aresos-authored"})


def clean_header(value, authored=True):
    if any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in value):
        raise Refused("invalid_input", "Header contains a control character; use a single line.")
    if authored and (re.search(r"=\?[^\r\n]*?\?=", value) or any(
            0x200b <= ord(c) <= 0x200f or 0x202a <= ord(c) <= 0x202e
            or 0x2060 <= ord(c) <= 0x2064 or 0x2066 <= ord(c) <= 0x2069
            or ord(c) in {0x061c, 0xfeff} for c in value)):
        raise Refused("invalid_input", "Write decoded Unicode header values without encoded words, bidi or invisible formatting characters.")
    return value


def address(value, utf8=False, authored=True, normalize=False):
    if normalize:
        value = value.strip(" \t")
    clean_header(value.replace("\t", "") if normalize else value, authored)
    pairs = getaddresses([value])
    if len(pairs) != 1 or not pairs[0][1] or pairs[0][1].count("@") != 1:
        raise Refused("invalid_input", "Use one explicit mailbox per address, including its domain.")
    name, addr = pairs[0]
    if normalize:
        name = name.strip(" \t")
    clean_header(name, authored)
    clean_header(addr, authored)
    local, domain = addr.rsplit("@", 1)
    if not local or any(c in local for c in '<> ,;:()\\"'):
        raise Refused("invalid_input", "This mailbox syntax is unsupported; use a simple explicit address.")
    if not utf8 and not local.isascii():
        raise Refused("smtputf8_required", "Non-ASCII local part requires SMTPUTF8; this account's server does not advertise it.")
    try:
        domain = domain.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise Refused("invalid_input", "Invalid international domain name.") from exc
    if not re.fullmatch(r"[a-z0-9.-]+", domain) or domain.startswith(".") or domain.endswith("."):
        raise Refused("invalid_input", "Invalid mailbox domain.")
    from email.headerregistry import Address
    return str(Address(display_name=name, username=local, domain=domain))


def mailbox(value):
    return getaddresses([value])[0][1]


def addresses(msg, *headers):
    return [str(a) for h in headers for v in msg.get_all(h, [])
            for a in getattr(v, "addresses", []) if a.addr_spec and a.domain]


def message_ids(value):
    return re.findall(r"<[^<>\s]+@[^<>\s]+>", str(value or ""))


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


def decoded(part):
    if part.get_content_type() == "message/rfc822":
        payload = part.get_payload()
        return payload[0].as_bytes(policy=SMTP_POLICY) if isinstance(payload, list) else bytes(str(payload), "utf8")
    return part.get_payload(decode=True) or b""


def text_part(part):
    data = decoded(part)
    try:
        text = data.decode(part.get_content_charset() or "utf8", "replace")
    except LookupError:
        text = data.decode("utf8", "replace")
    return html_text(text) if part.get_content_type() == "text/html" else text


def parts(msg):
    # Stable MIME tree paths include nested forwarded messages.
    def walk(node, path):
        yield path, node
        if node.is_multipart():
            for index, child in enumerate(node.get_payload(), 1):
                yield from walk(child, path + "." + str(index))
    return dict(walk(msg, "1"))


def attachments(msg):
    return [{"part": path, "name": p.get_filename() or ("forward.eml" if p.get_content_type() == "message/rfc822" else "attachment"),
             "type": p.get_content_type(), "size": len(decoded(p)), "sha256": sha256(decoded(p))}
            for path, p in parts(msg).items() if p.get_filename() or p.get_content_disposition() == "attachment"
            or p.get_content_type() == "message/rfc822"]


def body(msg):
    if msg.get_content_type() in {"text/plain", "text/html"}:
        return text_part(msg)
    selected = msg.get_body(preferencelist=("plain", "html"))
    return text_part(selected) if selected is not None else ""


def _transfer(msg, payload):
    encoding = str(msg.get("Content-Transfer-Encoding", "7bit")).strip().lower()
    try:
        if encoding == "base64":
            return base64.b64decode(re.sub(rb"[ \t\r\n]", b"", payload), validate=True)
        if encoding == "quoted-printable":
            if re.search(rb"=(?![0-9a-fA-F]{2}|\r?\n)", payload):
                raise ValueError("broken quoted-printable")
            return quopri.decodestring(payload)
        if encoding in {"7bit", "8bit", "binary"}:
            if encoding == "7bit" and not payload.isascii():
                raise ValueError("non-ASCII 7bit payload")
            return payload
    except (ValueError, binascii.Error) as exc:
        raise Refused("file_refused", "Broken mail transfer encoding; cannot inspect outgoing attachment safely.") from exc
    raise Refused("file_refused", "Unknown mail transfer encoding; cannot inspect outgoing attachment safely.")


# Rebuilt messages never inherit a source header block. Draft provenance is checked
# on the original bytes, before any headers can be dropped.
MESSAGE_HEADERS = frozenset(name.lower() for name in (
    "From", "Sender", "Reply-To", "To", "Cc", "Date", "Subject", "Message-ID",
    "In-Reply-To", "References", "MIME-Version"))
MIME_HEADERS = frozenset(name.lower() for name in (
    "Content-Type", "Content-Transfer-Encoding", "Content-Disposition", "Content-ID",
    "Content-Description", "Content-Language"))
AUTHORED_DESCRIPTION = "AresOS authored text; full approval required"
DRAFT_ATTACHMENT_REASON = 'Drafts cannot be attachments or attached parts; send the draft itself (mode=draft), or forward it inline.'
INSPECTION_LIMIT = 64 * 1024 * 1024
WORK_LIMIT = 256 * 1024 * 1024


def has_authored_marker(data):
    return bool(re.search(rb"(?:^|[\r\n])[ \t]*x-aresos-authored[ \t]*:", data, re.I))


def split_entity(raw):
    # A headerless digest child starts with one empty line. Whitespace-only
    # continuation lines remain in the header block, including their exact bytes.
    for line in re.finditer(rb"[^\r\n]*(?:\r\n|\r|\n|$)", raw):
        if not line.group().rstrip(b"\r\n"):
            return raw[:line.start()], raw[line.end():]
    return raw, b""


def entity(raw, default_type="text/plain"):
    head, payload = split_entity(raw)
    continuation = False
    for index, line in enumerate(re.split(rb"\r\n|\n|\r", head.rstrip(b"\r\n"))):
        if not line and not head:
            break
        if index == 0 and line.startswith(b"From ") and not re.match(rb"From[ \t]*:", line):
            continue
        if line[:1] in (b" ", b"\t") and continuation:
            continue
        if not re.fullmatch(rb"[\x21-\x39\x3b-\x7e]+:[^\r\n]*", line):
            raise Refused("file_refused", "Mail has a defective header block; cannot rebuild outgoing attachment safely.")
        continuation = True
    headers = BytesHeaderParser(policy=policy.default).parsebytes(head + b"\r\n\r\n")
    headers.set_default_type(default_type)
    if headers.defects or any(value.defects for value in headers.values()):
        raise Refused("file_refused", "Mail has defective MIME headers; cannot rebuild outgoing attachment safely.")
    for name in MIME_HEADERS:
        if len(headers.get_all(name, [])) > 1:
            raise Refused("file_refused", "Mail has ambiguous MIME headers; cannot rebuild outgoing attachment safely.")
    return headers, payload


def multipart_children(headers, payload):
    boundary = headers.get_boundary()
    if not boundary or not boundary.isascii():
        raise Refused("file_refused", "Mail has no safe multipart boundary; cannot rebuild attachment.")
    delimiter = b"--" + boundary.encode("ascii")
    chunks, start = [], None
    for line in re.finditer(rb"[^\r\n]*(?:\r\n|\r|\n|$)", payload):
        marker = line.group().rstrip(b"\r\n").rstrip(b" \t")
        if marker.startswith(delimiter) and marker not in {delimiter, delimiter + b"--"}:
            raise Refused("file_refused", "Mail has ambiguous multipart boundaries; cannot rebuild attachment.")
        if marker not in {delimiter, delimiter + b"--"}:
            continue
        if start is not None:
            chunk = payload[start:line.start()]
            chunks.append(chunk[:-2] if chunk.endswith(b"\r\n") else chunk[:-1] if chunk.endswith((b"\r", b"\n")) else chunk)
        if marker == delimiter + b"--":
            if not chunks:
                break
            return chunks
        start = line.end()
    raise Refused("file_refused", "Mail has broken multipart boundaries; cannot rebuild attachment.")


def possible_entity(data):
    data = mail_content(data)
    head, payload = split_entity(data)
    # Speculative parsing of opaque bytes requires a complete, valid block.
    # A text leaf never calls this detector, even when its prose resembles mail.
    if not head or len(head) == len(data):
        return False
    try:
        headers, _ = entity(data)
    except Refused:
        return False
    return bool(headers.keys())


def source_part(raw, path):
    """Select original bytes without serializing a parser tree (binary is opaque)."""
    remaining = path.split(".")
    if not remaining or remaining.pop(0) != "1":
        raise Refused("stale_reference", "MIME part is stale, read again.")
    default_type, authored = "text/plain", False
    raw = mail_content(raw)
    for depth in range(41):
        headers, payload = entity(raw, default_type)
        authored = authored or has_authored_marker(split_entity(raw)[0]) or str(headers.get("Content-Description", "")) == AUTHORED_DESCRIPTION
        if not remaining:
            return raw, headers, payload, authored, default_type
        major = headers.get_content_maintype()
        encoding = str(headers.get("Content-Transfer-Encoding", "7bit")).strip().lower()
        if major == "multipart":
            if encoding not in {"7bit", "8bit", "binary"}:
                raise Refused("file_refused", "Transfer-encoded multipart mail cannot be inspected safely.")
            children = multipart_children(headers, payload)
            default_type = "message/rfc822" if headers.get_content_type() == "multipart/digest" else "text/plain"
        elif major == "message":
            if encoding not in {"7bit", "8bit", "binary"}:
                raise Refused("file_refused", 'Encoded message descendants have no stable decoded MIME path; attach the enclosing part or part: "source".')
            children, default_type = [payload], "text/plain"
        else:
            break
        try:
            index = int(remaining.pop(0))
            if index < 1:
                break
            raw = children[index - 1]
        except (ValueError, IndexError):
            break
    raise Refused("stale_reference", "MIME part is stale or too deep, read again.")


def rebuild(raw, authored=False, default_type="text/plain", message=True):
    work = 0

    def build(data, inherited, default, full_message, depth):
        nonlocal work
        work += len(data)
        if depth > 40 or len(data) > INSPECTION_LIMIT or work > WORK_LIMIT:
            raise Refused("file_refused", "Mail exceeds the safe rebuild depth or size limit.")
        headers, payload = entity(data, default)
        marked = inherited or AUTHORED_HEADER in headers or str(headers.get("Content-Description", "")) == AUTHORED_DESCRIPTION
        if marked or has_authored_marker(split_entity(data)[0]):
            raise Refused("file_refused", DRAFT_ATTACHMENT_REASON)
        fresh = EmailMessage(policy=SMTP_POLICY)
        allowed = MIME_HEADERS | (MESSAGE_HEADERS if full_message else frozenset())
        for name, value in headers.raw_items():
            if name.lower() in allowed:
                fresh.set_raw(name, value)
        kind = headers.get_content_type()
        if "Content-Type" not in fresh and default != "text/plain":
            fresh["Content-Type"] = default
        major = headers.get_content_maintype()
        encoding = str(headers.get("Content-Transfer-Encoding", "7bit")).strip().lower()
        texts = []
        if major == "multipart":
            if encoding not in {"7bit", "8bit", "binary"}:
                raise Refused("file_refused", "Transfer-encoded multipart mail is unsupported; cannot rebuild it safely.")
            children = []
            child_default = "message/rfc822" if kind == "multipart/digest" else "text/plain"
            for child in multipart_children(headers, payload):
                clean, child_texts = build(child, marked, child_default, False, depth + 1)
                children.append(clean)
                texts.extend(child_texts)
            delimiter = b"--" + headers.get_boundary().encode("ascii")
            output = b"".join(delimiter + b"\r\n" + child + b"\r\n" for child in children) + delimiter + b"--\r\n"
        else:
            original_data = decoded_data = _transfer(headers, payload)
            if major == "message":
                if kind not in {"message/rfc822", "message/global"}:
                    raise Refused("file_refused", "Unsupported encapsulated message type; cannot rebuild it safely.")
                decoded_data, texts = build(decoded_data, marked, "text/plain", True, depth + 1)
            elif major != "text" and possible_entity(decoded_data):
                decoded_data, texts = build(mail_content(decoded_data), marked, "text/plain", True, depth + 1)
            if has_authored_marker(decoded_data):
                raise Refused("file_refused", DRAFT_ATTACHMENT_REASON)
            # Binary bytes never pass through an email generator. Retain valid
            # wire encodings when unchanged; otherwise base64 the decoded bytes.
            if decoded_data == original_data and encoding != "binary" and b"\r" not in payload.replace(b"\r\n", b"") and b"\n" not in payload.replace(b"\r\n", b""):
                output = payload
            else:
                del fresh["Content-Transfer-Encoding"]
                fresh["Content-Transfer-Encoding"] = "base64"
                output = base64.encodebytes(decoded_data).replace(b"\n", b"\r\n")
        fresh.set_payload("")
        result = fresh.as_bytes() + output
        if len(result) > INSPECTION_LIMIT:
            raise Refused("file_refused", "Rebuilt mail exceeds the safe size limit.")
        return result, texts

    return build(raw, authored, default_type, message, 0)


def approval_texts(msg, authored=False):
    return rebuild(msg.as_bytes(policy=policy.default.clone(linesep="\r\n", cte_type="8bit")), authored)[1]


def without_bcc(raw):
    return rebuild(mail_content(raw))[0]


def timestamp(msg):
    try:
        value = parsedate_to_datetime(str(msg.get("Date", "")))
        return value.replace(tzinfo=value.tzinfo or timezone.utc).timestamp()
    except (ValueError, TypeError, OverflowError):
        return 0


def formatted(text):
    """Small literal Markdown subset; raw HTML stays literal text in both parts."""
    def inline(value):
        value = escape(value)
        def link(match):
            label, url = match.groups()
            if urlsplit(url).scheme.lower() not in {"https", "http", "mailto"}:
                raise Refused("invalid_input", "Formatted links support only https, http and mailto.")
            return '<a href="' + url + '">' + label + '</a>'
        value = re.sub(r"\[([^\]\n]+)\]\(([^\s)]+)\)", link, value)
        value = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", value)
        return re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", value)
    lines, in_list = [], False
    for line in text.splitlines():
        item = re.match(r"^(?:[-*]|\d+\.) (.*)", line)
        if item and not in_list:
            lines.append("<ul>")
            in_list = True
        if not item and in_list:
            lines.append("</ul>")
            in_list = False
        if item:
            lines.append("<li>" + inline(item[1]) + "</li>")
        elif line.startswith("> "):
            lines.append("<blockquote>" + inline(line[2:]) + "</blockquote>")
        else:
            lines.append("<p>" + inline(line) + "</p>")
    if in_list:
        lines.append("</ul>")
    html = "\n".join(lines)
    return html_text(html), html


def utf7(value):
    out, run = [], []
    def flush():
        if run:
            out.append("&" + base64.b64encode("".join(run).encode("utf-16be")).decode().rstrip("=").replace("/", ",") + "-")
            run.clear()
    for char in value:
        if 0x20 <= ord(char) <= 0x7e:
            flush()
            out.append("&-" if char == "&" else char)
        else:
            run.append(char)
    flush()
    return "".join(out)


def unutf7(value):
    def convert(match):
        chunk = match[1]
        return "&" if not chunk else base64.b64decode(chunk.replace(",", "/") + "=" * (-len(chunk) % 4)).decode("utf-16be")
    return re.sub(r"&([^-]*)-", convert, value)
