"""Shared test harness: check successful and failed service replies at the boundary."""
from functools import wraps

from jsonschema import Draft202012Validator

from aresos_control.definitions import BY_NAME
from aresos_control.engine import Engine


def check_responses():
    if getattr(Engine.request, 'schema_checked', False):
        return
    request = Engine.request
    validators = {name: Draft202012Validator(action.tool()['outputSchema']) for name, action in BY_NAME.items()}

    @wraps(request)
    def checked(engine, value, admin=False):
        result = request(engine, value, admin)
        if isinstance(value, dict) and value.get('method') == 'call':
            name = value.get('action')
            if isinstance(name, str) and name in validators:
                validators[name].validate(result)
        return result
    checked.schema_checked = True
    Engine.request = checked
