import base64
import binascii
from datetime import timezone
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from html import escape
from html.parser import HTMLParser
import re
import quopri
from urllib.parse import urlsplit

from ..common import Refused, sha256

SMTP_POLICY = policy.SMTP.clone(cte_type="7bit", max_line_length=78)
AUTHORED_HEADER = "X-AresOS-Authored"


def parse(raw):
    return BytesParser(policy=policy.default).parsebytes(raw)


def mail_content(raw):
    raw = raw.lstrip()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:].lstrip()
    return raw


def is_mail(raw):
    # Local names and MIME types are caller-controlled; inspect the header block.
    headers = set()
    for line in mail_content(raw).splitlines():
        if not line.strip():
            break
        match = re.match(rb"[ \t]*([\x21-\x39\x3b-\x7e]+)[ \t]*:", line)
        if match:
            headers.add(match[1].lower())
    return b"from" in headers and bool(headers & {
        b"date", b"subject", b"message-id", b"received", b"mime-version",
        b"bcc", b"resent-bcc", b"x-aresos-authored"})


def clean_header(value):
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise Refused("invalid_input", "Header contains a control character; use a single line.")
    return value


def address(value, utf8=False):
    clean_header(value)
    pairs = getaddresses([value])
    if len(pairs) != 1 or not pairs[0][1] or pairs[0][1].count("@") != 1:
        raise Refused("invalid_input", "Use one explicit mailbox per address, including its domain.")
    name, addr = pairs[0]
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


def _outgoing(raw, authored=False, depth=0):
    """Normalize encapsulated messages before trusting the parser's MIME tree."""
    if depth > 40:
        raise Refused("file_refused", "Mail nesting exceeds the safe inspection limit.")
    content = mail_content(raw)
    split = re.search(rb"\r\n\r\n|\n\n|\r\r", content)
    head, payload = (content[:split.start()], content[split.end():]) if split else (content, b"")
    continuation = False
    for index, line in enumerate(re.split(rb"\r\n|\n|\r", head)):
        if index == 0 and line.startswith(b"From ") and not re.match(rb"From[ \t]*:", line):
            continue
        if line[:1] in (b" ", b"\t") and continuation:
            continue
        if not re.fullmatch(rb"[\x21-\x39\x3b-\x7e]+:[^\r\n]*", line):
            raise Refused("file_refused", "Mail has a defective header block; cannot inspect outgoing attachment safely.")
        continuation = True
    headers = BytesParser(policy=policy.default).parsebytes(head + b"\r\n\r\n", headersonly=True)
    if headers.defects or any(value.defects for value in headers.values()):
        raise Refused("file_refused", "Mail has a defective header block; cannot inspect outgoing attachment safely.")
    for name in ("Content-Type", "Content-Transfer-Encoding", "Content-Disposition"):
        if len(headers.get_all(name, [])) > 1:
            raise Refused("file_refused", "Mail has ambiguous MIME headers; cannot inspect outgoing attachment safely.")
    msg = parse(content)
    authored = authored or AUTHORED_HEADER in headers
    changed, texts = False, []
    for name in ("Bcc", "Resent-Bcc"):
        if name in msg:
            del msg[name]
            changed = True
    major = headers.get_content_maintype()
    encoding = str(headers.get("Content-Transfer-Encoding", "7bit")).strip().lower()
    if major == "message":
        if headers.get_content_type() not in {"message/rfc822", "message/global"}:
            raise Refused("file_refused", "Unsupported encapsulated message type; cannot inspect outgoing attachment safely.")
        data = _transfer(headers, payload)
        clean, texts = _outgoing(data, authored, depth + 1)
        if clean != data or encoding not in {"7bit", "8bit", "binary"}:
            del msg["Content-Transfer-Encoding"]
            msg.set_payload([parse(mail_content(clean))])
            changed = True
    elif major == "multipart":
        if encoding not in {"7bit", "8bit", "binary"}:
            raise Refused("file_refused", "Transfer-encoded multipart mail is unsupported; nothing can be sent unchecked.")
        if msg.defects or not msg.is_multipart():
            raise Refused("file_refused", "Broken multipart mail; cannot inspect outgoing attachment safely.")
        children = []
        for child in msg.get_payload():
            if child.defects or any(value.defects for value in child.values()):
                raise Refused("file_refused", "Mail has a defective nested header block; cannot inspect outgoing attachment safely.")
            child_raw = child.as_bytes(policy=policy.default.clone(linesep="\r\n", cte_type="8bit"))
            clean, child_texts = _outgoing(child_raw, authored, depth + 1)
            children.append(parse(clean) if clean != child_raw else child)
            changed = changed or clean != child_raw
            texts.extend(child_texts)
        msg.set_payload(children)
    else:
        data = _transfer(headers, payload)
        data_head = re.split(rb"\r\n\r\n|\n\n|\r\r", mail_content(data), maxsplit=1)[0]
        mime_entity = re.search(rb"(?im)^(?:content-type[ \t]*:[ \t\r\n]*(?:multipart|message)/|x-aresos-authored[ \t]*:)", data_head)
        if is_mail(data) or mime_entity or (msg.get_filename() or "").lower().endswith((".eml", ".msg")):
            clean, texts = _outgoing(data, authored, depth + 1)
            if clean != data:
                del msg["Content-Transfer-Encoding"]
                msg.set_payload(clean)
                from email.encoders import encode_base64
                encode_base64(msg)
                changed = True
        elif authored and msg.get_content_type() in {"text/plain", "text/html"}:
            texts = [text_part(msg)]
    return (msg.as_bytes(policy=SMTP_POLICY) if changed else raw), texts


def approval_texts(msg, authored=False):
    """Markers travel with MIME bytes, including encoded encapsulated messages."""
    return _outgoing(msg.as_bytes(policy=policy.default.clone(linesep="\r\n", cte_type="8bit")), authored)[1]


def without_bcc(raw):
    return _outgoing(raw)[0]


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
