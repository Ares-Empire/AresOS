import hashlib
import json
import unicodedata

WIRE_LIMIT = 6 * 1024 * 1024
FILE_LIMIT = 1024 * 1024
ASK_LIMIT = 16 * 1024
RESULT_LIMIT = 48 * 1024


class Refused(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


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


def approval_input(operation_id, description):
    result = {"operation_id": operation_id, "description": visible(description)}
    if len(canonical(result).encode()) > ASK_LIMIT:
        raise Refused("asking_input_too_large", "The whole approval exceeds 16384 bytes; prepare a smaller operation. Nothing was reserved.")
    return result


def validate(value, schema, path="input"):
    """The closed schema subset used by definitions; unknown schema keywords fail generation."""
    kind = schema.get("type")
    valid = {"object": type(value) is dict, "array": type(value) is list,
             "string": type(value) is str, "integer": type(value) is int,
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
