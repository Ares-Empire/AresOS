"""Shared test harness: check successful and failed service replies at the boundary."""
from functools import wraps

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError as exc:
    if exc.name != 'jsonschema':
        raise
    Draft202012Validator = None

from aresos_control.definitions import BY_NAME
from aresos_control.engine import Engine
from aresos_control.proxy import Proxy
from aresos_control.protocol import receive, send


def transport_response(result):
    class Frame:
        def sendall(self, wire):
            self.wire = wire
        def recv(self, count):
            chunk, self.wire = self.wire[:count], self.wire[count:]
            return chunk
    frame = Frame()
    send(frame, result, result=True)
    assert receive(frame) == result
    return result


class ResponseValidationError(ValueError):
    def __init__(self, rule, path, detail):
        super().__init__(f'{("response", *path)}: {detail}')
        self.validator = rule
        self.absolute_path = path


class StandardResponseValidator:
    """Check the generated response-schema subset on plain Python CI shards."""

    def __init__(self, schema):
        self.schema = schema

    def iter_errors(self, result):
        return self._errors(result, self.schema, ())

    def validate(self, result):
        error = next(self.iter_errors(result), None)
        if error is not None:
            raise error

    @classmethod
    def _errors(cls, value, schema, path):
        kind = type(value)
        number = kind in (int, float)
        valid_types = {
            'object': kind is dict, 'array': kind is list, 'string': kind is str,
            'number': number, 'integer': kind is int or kind is float and value.is_integer(),
            'boolean': kind is bool, 'null': value is None,
        }
        for rule, constraint in schema.items():
            if rule == 'type' and not valid_types[constraint]:
                yield ResponseValidationError(rule, path, f'expected {constraint}')
            # The output enums contain scalars. JSON distinguishes booleans from numbers.
            elif rule == 'enum' and not any(
                value == option and (kind is bool) == (type(option) is bool)
                for option in constraint
            ):
                yield ResponseValidationError(rule, path, f'expected one of {constraint}')
            elif rule == 'anyOf' and all(
                next(cls._errors(value, option, path), None) is not None for option in constraint
            ):
                yield ResponseValidationError(rule, path, 'does not match any allowed schema')
            elif rule == 'properties' and kind is dict:
                for key, child in constraint.items():
                    if key in value:
                        yield from cls._errors(value[key], child, (*path, key))
            elif rule == 'required' and kind is dict:
                for key in constraint:
                    if key not in value:
                        yield ResponseValidationError(rule, path, f'missing {key!r}')
            elif rule == 'additionalProperties' and kind is dict and constraint is False:
                extra = value.keys() - schema.get('properties', {}).keys()
                if extra:
                    yield ResponseValidationError(rule, path, f'unexpected fields {sorted(extra)}')
            elif rule == 'items' and kind is list:
                for index, item in enumerate(value):
                    yield from cls._errors(item, constraint, (*path, index))
            elif (
                kind is list and (rule == 'minItems' and len(value) < constraint
                                  or rule == 'maxItems' and len(value) > constraint)
                or kind is str and (rule == 'minLength' and len(value) < constraint
                                    or rule == 'maxLength' and len(value) > constraint)
                or number and (rule == 'minimum' and value < constraint
                               or rule == 'maximum' and value > constraint)
            ):
                yield ResponseValidationError(rule, path, f'outside {rule} {constraint}')


response_validator = Draft202012Validator or StandardResponseValidator
VALIDATORS = {name: response_validator(action.tool()['outputSchema']) for name, action in BY_NAME.items()}


def validate_response(value, result):
    transport_response(result)
    if isinstance(value, dict) and value.get('method') == 'call':
        name = value.get('action')
        if isinstance(name, str) and name in VALIDATORS:
            VALIDATORS[name].validate(result)
    return result


def check_responses():
    if getattr(Engine.request, 'schema_checked', False):
        return
    request = Engine.request
    @wraps(request)
    def checked(engine, value, admin=False):
        return validate_response(value, request(engine, value, admin))
    checked.schema_checked = True
    Engine.request = checked
    proxy_call = Proxy.call
    @wraps(proxy_call)
    def checked_proxy(proxy, verb, arguments):
        # Caller-side saves/refusals add facts after the service response.
        return transport_response(proxy_call(proxy, verb, arguments))
    Proxy.call = checked_proxy
