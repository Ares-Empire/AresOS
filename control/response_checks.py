"""Shared test harness: check successful and failed service replies at the boundary."""
from functools import wraps

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError as exc:
    if exc.name != 'jsonschema':
        raise
    Draft202012Validator = None

from aresos_control.common import validate

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

def response_validator(schema):
    # The plain Chrome and qualification shards also run with the standard library alone.
    # generate.py checks that every output schema fits the service validator's subset.
    if Draft202012Validator is None:
        return lambda result: validate(result, schema, 'response')
    return Draft202012Validator(schema).validate


VALIDATORS = {name: response_validator(action.tool()['outputSchema']) for name, action in BY_NAME.items()}


def validate_response(value, result):
    transport_response(result)
    if isinstance(value, dict) and value.get('method') == 'call':
        name = value.get('action')
        if isinstance(name, str) and name in VALIDATORS:
            VALIDATORS[name](result)
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
