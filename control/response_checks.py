"""Shared test harness: check successful and failed service replies at the boundary."""
from functools import wraps

from jsonschema import Draft202012Validator

from aresos_control.definitions import BY_NAME
from aresos_control.engine import Engine
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

VALIDATORS = {name: Draft202012Validator(action.tool()['outputSchema']) for name, action in BY_NAME.items()}


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
