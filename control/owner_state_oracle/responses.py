"""Read actual replies without losing an assertion-specific schema failure."""
import re
from unittest.mock import patch

from jsonschema import ValidationError
import response_checks

from .records import canonical


def describe(error):
    value = {'rule': error.validator, 'path': list(error.absolute_path),
             'schema': list(error.absolute_schema_path), 'constraint': error.validator_value}
    if error.validator == 'required':
        value['missing'] = sorted(set(error.validator_value) - error.instance.keys())
    elif error.validator == 'additionalProperties':
        properties, patterns = error.schema.get('properties', {}), error.schema.get('patternProperties', {})
        value['extra'] = sorted(key for key in error.instance if key not in properties
                                and not any(re.search(pattern, key) for pattern in patterns))
    elif isinstance(error.instance, (str, int, float, bool)) or error.instance is None:
        value['actual'] = error.instance
    else:
        value['actual_type'] = type(error.instance).__name__
        value['actual_length'] = len(error.instance)
    return canonical(value)


def read_response(call):
    validate, failed = response_checks.validate_response, []
    def observed(value, result):
        try:
            return validate(value, result)
        except ValidationError as error:
            failed.append((value, result, error))
            raise
    with patch.object(response_checks, 'validate_response', side_effect=observed):
        try:
            return call(), []
        except ValidationError as error:
            # Never catch a business-logic error or a transport assertion. Only
            # the existing public-response validator can supply this failure.
            if not failed or failed[-1][2] is not error:
                raise
            value, result, _ = failed[-1]
            errors = list(response_checks.VALIDATORS[value['action']].iter_errors(result))
            if not errors:
                raise
            return result, [describe(error) for error in errors]
