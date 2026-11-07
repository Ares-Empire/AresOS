import hashlib
import json
import unicodedata

WIRE_LIMIT = 6 * 1024 * 1024
FILE_LIMIT = 25 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
ASK_LIMIT = 16 * 1024
QUESTION_LIMIT = 4096
RESULT_LIMIT = 48 * 1024


class Refused(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


class _JSONPairs(list):
    pass


class JSONInputError(Refused):
    def __init__(self, raw):
        super().__init__("invalid_input", "Malformed JSON, repeated fields or non-finite numbers are refused; send one unchanged JSON request.")
        # Recover routing/id candidates without collapsing any repeated field.
        # This tree is only for refusing input, never for executing it.
        try:
            self.pairs = json.loads(raw, object_pairs_hook=_JSONPairs, parse_constant=lambda _: None)
        except (ValueError, UnicodeError):
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


def strict_json_loads(raw):
    def object_pairs(pairs):
        seen = set()
        for key, _ in pairs:
            if key in seen:
                raise ValueError("Repeated JSON field")
            seen.add(key)
        return dict(pairs)

    def nonfinite(_):
        raise ValueError("Non-finite JSON number")

    try:
        return json.loads(raw, object_pairs_hook=object_pairs, parse_constant=nonfinite)
    except (ValueError, UnicodeError) as exc:
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
