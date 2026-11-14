"""How an address is written when it leaves the service (brief 28, item 2).

One function, `public_address`, in two forms. The public form shows the site,
the path and the query, with everything that looks like a sign-in replaced by
the mark. The short form shows the site and the path only. Full addresses stay
inside the service and the extension.
"""
import re
from urllib.parse import unquote, urlsplit

MARK = "…"
LIMIT = 300
RANDOM_RUN = 20
RANDOM_HEX = 24

# A path segment that holds one of these hides everything after it.
SIGN_IN_WORDS = frozenset(
    "reset verify confirm activate magic token invite auth oauth sso saml login signin logon "
    "callback password passwort otp".split())
# A query parameter whose name holds one of these never shows its value.
CREDENTIAL_WORDS = frozenset(
    "token code key secret signature sig password passwd pwd auth session sid otp ticket state "
    "nonce jwt".split())

_DEFAULT_PORTS = {"http": 80, "https": 443}
# Everything outside this set is percent-encoded, so an address can never
# hold a quote, a bracket, a space or a line break of the outline.
_KEPT = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_~/%:?&=+#;,")
_SCHEME = re.compile(r"[a-z][a-z0-9+.-]{0,19}")
_ALNUM_RUN = re.compile(r"[A-Za-z0-9]{%d,}" % RANDOM_RUN)
_HEX_RUN = re.compile(r"[0-9A-Fa-f]{%d,}" % RANDOM_HEX)
# The parts of a name: split at every character that is no ASCII letter or
# digit, and at a change of case (sessionToken, JWTToken, oauth2).
_NAME_PART = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+")


def looks_random(text):
    """The one test for a value that could be a token, a code or a key."""
    for run in _ALNUM_RUN.findall(text):
        if re.search("[A-Za-z]", run) and re.search("[0-9]", run):
            return True
    return _HEX_RUN.search(text.replace("-", "")) is not None


def _parts(name):
    return [part.lower() for part in _NAME_PART.findall(unquote(name))]


def credential_name(name):
    """A parameter name with a credential word as a part, or as the start or end of a part."""
    return any(part == word or part.startswith(word) or part.endswith(word)
               for part in _parts(name) for word in CREDENTIAL_WORDS)


def sign_in_segment(segment):
    """A path segment with a sign-in word as a part, also written in two parts (sign-in)."""
    parts = _parts(segment)
    joined = [first + second for first, second in zip(parts, parts[1:])]
    return any(part in SIGN_IN_WORDS for part in parts + joined)


def _safe(text):
    return "".join(character if character in _KEPT else
                   "".join("%%%02X" % byte for byte in character.encode("utf-8", "surrogatepass"))
                   for character in text)


def _site(parts):
    host = parts.hostname
    if not host:
        raise ValueError("an address without a host")
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        pass  # not a name the browser would resolve; shown percent-encoded
    if ":" in host:
        host = "[" + host + "]"
    port = parts.port  # raises ValueError when it is no port number
    shown = _safe(host)
    if port is not None and port != _DEFAULT_PORTS[parts.scheme]:
        shown += ":%d" % port
    return ("http://" if parts.scheme == "http" else "") + shown


def _path(path):
    shown = []
    segments = path.split("/")
    for index, segment in enumerate(segments):
        shown.append(MARK if looks_random(unquote(segment)) else _safe(segment))
        if sign_in_segment(segment) and any(segments[index + 1:]):
            shown.append(MARK)
            break
    return "/".join(shown)


def _parameter(text):
    name, equals, value = text.partition("=")
    if not equals:
        return MARK if looks_random(unquote(text)) else _safe(text)
    hidden = value and (credential_name(name) or looks_random(unquote(value)))
    return ((MARK if looks_random(unquote(name)) else _safe(name)) + "=" +
            (MARK if hidden else _safe(value)))


def _query(query):
    return "&".join(_parameter(parameter) for parameter in query.split("&") if parameter)


def _fragment(fragment):
    if "/" in fragment:
        # A single-page site's route, with a query of its own after "?".
        path, question, query = fragment.partition("?")
        return _path(path) + (question + _query(query) if question else "")
    if "=" in fragment:
        return _query(fragment)
    return MARK if looks_random(unquote(fragment)) else _safe(fragment)


def _bounded(text):
    if len(text) <= LIMIT:
        return text
    kept = text[:LIMIT]
    escape = kept.rfind("%", LIMIT - 2)
    if escape >= 0:
        kept = kept[:escape]  # never half of a percent-escape
    return "%s%s+%s" % (kept, MARK, format(len(text) - len(kept), ","))


def site_of(address):
    """The site of an address as the public form writes it, or None when it has none."""
    try:
        parts = urlsplit(address)
        return _site(parts) if parts.scheme in _DEFAULT_PORTS else None
    except ValueError:
        return None


def public_address(address, short=False):
    """Write an address for a result, a question or a record.

    `short` is the form for lists and records: the site and the path, with
    only a mark where a query or a fragment was.
    """
    if not isinstance(address, str):
        return MARK
    try:
        parts = urlsplit(address)
        if parts.scheme not in _DEFAULT_PORTS:
            # mailto:, javascript:, data: and the like can hold anything.
            return (parts.scheme + ":" if _SCHEME.fullmatch(parts.scheme) else "") + MARK
        shown = _site(parts) + _path(parts.path)
    except ValueError:
        return MARK
    if parts.query:
        shown += "?" + (MARK if short else _query(parts.query))
    if parts.fragment:
        shown += "#" + (MARK if short else _fragment(parts.fragment))
    return _bounded(shown)
