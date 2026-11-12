"""Closed service envelopes; action payloads use the shared tool catalogue."""
from .common import CHUNK_SIZE, Refused, json_value, validate
from .definitions import APPS, BLOB, obj, string
from .mail.definitions import ACCOUNT_CONFIG, SAVED_RESULT

APP = {'type': 'string', 'enum': sorted(APPS)}
FIELDS = {
    'pending': {},
    'tools': {'app': APP},
    'call': {'action': string(128), 'arguments': {'type': 'object'}},
    'mail_account_add': {'arguments': ACCOUNT_CONFIG, 'password': string(8192)},
    'upload': {'app': APP, 'file': BLOB},
    'download': {'app': APP, 'sha256': string(64), 'export_id': string(32)},
    'saved': {'app': APP, 'outcome': {'anyOf': [
        {'type': 'string', 'enum': ['refused']}, SAVED_RESULT]}, 'export_id': string(32)},
}
ENVELOPES = {name: obj({'v': {'type': 'integer', 'enum': [1]},
                       'method': {'type': 'string', 'enum': [name]}, **fields},
                      ['v', 'method'] + [key for key in fields if key != 'export_id'])
             for name, fields in FIELDS.items()}
OFFSET = {'type': 'integer', 'minimum': 0}
UPLOAD_CHUNK = {'anyOf': [obj({'offset': OFFSET, 'bytes': string(4 * ((CHUNK_SIZE + 2) // 3))}),
                          obj({'offset': OFFSET, 'end': {'type': 'boolean', 'enum': [True]}})]}
DOWNLOAD_CHUNK = {'anyOf': [obj({'offset': OFFSET}),
                            obj({'offset': OFFSET, 'end': {'type': 'boolean', 'enum': [True]}})]}


def changing(request):
    from .definitions import BY_NAME
    action = BY_NAME.get(request.get('action')) if request.get('method') == 'call' else None
    return (request.get('method') in {'upload', 'download', 'saved', 'mail_account_add'}
            or bool(action and action.effect != 'read'))


def envelope(request):
    json_value(request)
    if type(request) is not dict or type(request.get('method')) is not str or request['method'] not in ENVELOPES:
        raise Refused('invalid_input', 'Use a version 1 service request with a known method.')
    validate(request, ENVELOPES[request['method']], 'request')
