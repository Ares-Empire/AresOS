import hashlib
import errno
import json
import math
import sqlite3
import unicodedata
from contextlib import contextmanager
from contextvars import ContextVar
import sys

WIRE_LIMIT = 6 * 1024 * 1024
FILE_LIMIT = 25 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
ASK_LIMIT = 16 * 1024
QUESTION_LIMIT = 4096
RESULT_LIMIT = 48 * 1024
JSON_DEPTH_LIMIT = 64
JSON_INTEGER_LIMIT = 2**63 - 1


class Refused(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def _storage_refusal(exc):
    """Classify local storage failures without exposing paths or server text."""
    if isinstance(exc, Refused):
        return exc if exc.code in {'storage_limit', 'storage_error', 'journal_incomplete', 'restore_required'} else None
    code = getattr(exc, 'sqlite_errorcode', 0) & 0xff
    if (isinstance(exc, OSError) and exc.errno in {errno.ENOSPC, errno.EDQUOT}
            or code == sqlite3.SQLITE_FULL):
        return Refused('storage_limit', 'Disk full or storage quota exhausted; free storage and check the recorded request or operation before retrying.')
    if (isinstance(exc, OSError) and exc.errno == errno.EIO
            or code == sqlite3.SQLITE_IOERR):
        return Refused('storage_error', 'Storage I/O failed; check the disk and recorded request or operation before retrying.')
    return None


def storage_refusal(exc):
    error = _storage_refusal(exc)
    if error is not None:
        current, seen = exc, set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            for note in getattr(current, '__notes__', ()):
                if note not in getattr(error, '__notes__', ()):
                    error.add_note(note)
            current = current.__cause__ or current.__context__
    return error


CLEANUP = ContextVar('storage_cleanup', default=None)


@contextmanager
def cleanup(purpose, primary=None):
    """A failing cleanup annotates the active error instead of replacing it."""
    primary = primary or sys.exception()
    token = CLEANUP.set(purpose)
    try:
        yield
    except (OSError, sqlite3.Error, Refused) as exc:
        if primary is None:
            raise
        error = storage_refusal(exc)
        primary.add_note('Cleanup ' + purpose + ' failed: ' +
                         (str(error) if error else 'Storage cleanup failed; inspect the disk and recorded state.'))
    finally:
        CLEANUP.reset(token)


class _JSONPairs(list):
    pass


class JSONInputError(Refused):
    def __init__(self, raw):
        super().__init__("invalid_input", "Malformed, oversized or deeply nested JSON, repeated fields, invalid UTF-8/Unicode and out-of-range numbers are refused; send one unchanged JSON request.")
        # Recover routing/id candidates without collapsing any repeated field.
        # This tree is only for refusing input, never for executing it.
        try:
            self.pairs = _decode_json(raw, _JSONPairs)
        except (ValueError, UnicodeError, RecursionError):
            self.pairs = None

    def values(self, *path):
        values = [self.pairs]
        for key in path:
            values = [v for obj in values if isinstance(obj, _JSONPairs) for k, v in obj if k == key]
        return values

    def for_actions(self, names):
        from .definitions import BY_NAME
        if any(isinstance(name, str) and name in BY_NAME and BY_NAME[name].effect in {"send", "delete"} for name in names):
            self.code = "stale_approval"
        return self


def json_value(value):
    """Also validate internal/programmatic values before serialization or dispatch."""
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > JSON_DEPTH_LIMIT:
            raise ValueError("JSON nesting exceeds 64 levels")
        if type(item) is str:
            item.encode('utf-8', errors='strict')
        elif type(item) is int:
            if abs(item) > JSON_INTEGER_LIMIT:
                raise ValueError("JSON integer exceeds signed 63-bit magnitude")
        elif type(item) is float:
            if not math.isfinite(item):
                raise ValueError("Non-finite JSON number")
        elif type(item) in {list, dict, _JSONPairs}:
            if type(item) is dict:
                if any(type(k) is not str for k in item):
                    raise ValueError("JSON keys must be strings")
                children = [*item.keys(), *item.values()]
            elif type(item) is _JSONPairs:
                children = [v for pair in item for v in pair]
            else:
                children = item
            pending.extend((child, depth + 1) for child in children)
        elif item is not None and type(item) is not bool:
            raise ValueError("Not a JSON value")
    return value


def _decode_json(raw, pairs):
    # Scan the syntax depth before Python's recursive decoder sees the input.
    if isinstance(raw, bytes):
        if len(raw) > WIRE_LIMIT:
            raise ValueError("JSON exceeds 6 MiB")
        raw = raw.decode('utf-8', errors='strict')
    if type(raw) is not str or len(raw.encode('utf-8', errors='strict')) > WIRE_LIMIT or raw.startswith('\ufeff'):
        raise ValueError("JSON encoding or byte limit")
    depth, quoted, escaped = 0, False, False
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in '[{':
            depth += 1
            if depth > JSON_DEPTH_LIMIT:
                raise ValueError("JSON nesting exceeds 64 levels")
        elif char in ']}':
            depth -= 1

    def integer(token):
        if len(token.lstrip('-')) > 19 or abs(value := int(token)) > JSON_INTEGER_LIMIT:
            raise ValueError("JSON integer exceeds signed 63-bit magnitude")
        return value

    def floating(token):
        value = float(token)
        if not math.isfinite(value):
            raise ValueError("Non-finite JSON number")
        return value

    def nonfinite(_):
        raise ValueError("Non-finite JSON number")

    return json_value(json.loads(raw, object_pairs_hook=pairs, parse_float=floating,
                                 parse_int=integer, parse_constant=nonfinite))


def strict_json_loads(raw):
    def object_pairs(pairs):
        seen = set()
        for key, _ in pairs:
            if key in seen:
                raise ValueError("Repeated JSON field")
            seen.add(key)
        return dict(pairs)

    try:
        return _decode_json(raw, object_pairs)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise JSONInputError(raw) from exc


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def visible(value):
    """Escape in the string itself, so even a JSON renderer cannot hide bidi controls."""
    if isinstance(value, str):
        return "".join(f"\\u{ord(c):04x}" if unicodedata.category(c) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
                       else "\\\\" if c == "\\" else c for c in value)
    if isinstance(value, list):
        return [visible(v) for v in value]
    if isinstance(value, dict):
        return {visible(k): visible(v) for k, v in value.items()}
    return value


def approval_input(operation_id, description, question):
    result = {"question": visible(question), "operation_id": operation_id, "description": visible(description)}
    if len(result["question"]) > QUESTION_LIMIT:
        raise Refused("asking_input_too_large", "The question exceeds 4096 displayed characters; prepare a smaller operation. Nothing was reserved.")
    if len(canonical(result).encode()) > ASK_LIMIT:
        raise Refused("asking_input_too_large", "The whole approval exceeds 16384 bytes; prepare a smaller operation. Nothing was reserved.")
    return result


def approval_order(value):
    """Storage/hash JSON sorts keys; presentation must still put the question first."""
    if isinstance(value, dict):
        first = ["question", "operation_id", "description"] if {"question", "operation_id", "description"} <= value.keys() else []
        return {k: approval_order(value[k]) for k in first + [k for k in value if k not in first]}
    if isinstance(value, list):
        return [approval_order(v) for v in value]
    return value


def display_json(value):
    return json.dumps(approval_order(value), ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def require_question(arguments):
    # Check the received order before schema validation, hashing or presentation.
    if type(arguments) is not dict or list(arguments) != ["question", "operation_id", "description"]:
        raise Refused("stale_approval", "Pass exactly question, operation_id, description in that order, unchanged from the service approval, or prepare anew.")


def validate(value, schema, path="input"):
    """The closed schema subset used by definitions; unknown schema keywords fail generation."""
    if "anyOf" in schema:
        for option in schema["anyOf"]:
            try:
                validate(value, option, path)
                return
            except Refused:
                pass
        raise Refused("invalid_input", f"{path}: value does not match any allowed schema.")
    kind = schema.get("type")
    valid = {"object": type(value) is dict, "array": type(value) is list,
             "string": type(value) is str, "integer": type(value) is int,
             "number": type(value) in {int, float},
             "boolean": type(value) is bool, "null": value is None}
    if kind and not valid[kind]:
        raise Refused("invalid_input", f"{path}: expected {kind}; inspect the tool schema.")
    if "enum" in schema and value not in schema["enum"]:
        raise Refused("invalid_input", f"{path}: choose one of {schema['enum']}.")
    if kind == "object":
        props = schema.get("properties", {})
        if not set(schema.get("required", [])) <= value.keys():
            raise Refused("invalid_input", f"{path}: missing required fields; inspect the tool schema.")
        if schema.get("additionalProperties") is False and not value.keys() <= props.keys():
            raise Refused("invalid_input", f"{path}: unknown fields are refused.")
        for key, item in value.items():
            if key in props:
                validate(item, props[key], f"{path}.{key}")
    if kind in {"array", "string"}:
        lo, hi = ("minItems", "maxItems") if kind == "array" else ("minLength", "maxLength")
        if len(value) < schema.get(lo, 0) or len(value) > schema.get(hi, WIRE_LIMIT):
            raise Refused("invalid_input", f"{path}: length outside the allowed range; use a smaller page or input.")
        if kind == "array":
            for item in value:
                validate(item, schema["items"], path + "[]")
    if kind == "integer" and not schema.get("minimum", value) <= value <= schema.get("maximum", value):
        raise Refused("invalid_input", f"{path}: integer outside the allowed range.")
