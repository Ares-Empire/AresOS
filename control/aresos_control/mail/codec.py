import base64
from datetime import timezone
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from html import escape
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit

from ..common import Refused, sha256

SMTP_POLICY = policy.SMTP.clone(cte_type="7bit", max_line_length=78)
AUTHORED_HEADER = "X-AresOS-Authored"


def parse(raw):
    return BytesParser(policy=policy.default).parsebytes(raw)


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
    parser.feed(value)
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


def approval_texts(msg, authored=False):
    """Markers travel with MIME bytes, including through IMAP COPY/MOVE and nesting."""
    authored = authored or AUTHORED_HEADER in msg
    if msg.is_multipart():
        return [text for child in msg.get_payload() for text in approval_texts(child, authored)]
    if (msg.get_filename() or "").lower().endswith(".eml"):
        return approval_texts(parse(decoded(msg)), authored)
    if authored and msg.get_content_type() in {"text/plain", "text/html"}:
        return [text_part(msg)]
    return []


def without_bcc(raw):
    msg = parse(raw)
    changed = False
    for part in msg.walk():
        for header in ("Bcc", "Resent-Bcc"):
            if header in part:
                del part[header]
                changed = True
        # Our attached .eml files use octet-stream to freeze their wire bytes.
        if not part.is_multipart() and (part.get_filename() or "").lower().endswith(".eml"):
            data = decoded(part)
            clean = without_bcc(data)
            if clean != data:
                del part["Content-Transfer-Encoding"]
                part.set_payload(clean)
                from email.encoders import encode_base64
                encode_base64(part)
                changed = True
    return msg.as_bytes(policy=SMTP_POLICY) if changed else raw


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
