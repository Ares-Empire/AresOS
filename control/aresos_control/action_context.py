"""Commit mutation identity and arguments before effects; never replay them."""
from contextlib import contextmanager
import copy

from .common import Refused


@contextmanager
def action_scope(store, action, arguments, source_key=None):
    previous = getattr(store, '_action_scope', None)
    store._action_scope = {'action': action, 'arguments': copy.deepcopy(arguments), 'source_key': source_key}
    try:
        yield
    finally:
        store._action_scope = previous


def context(store, command, account, *, identities=(), source=None, destination=None,
            roles=None, recipients=(), arguments=None, **details):
    scope = getattr(store, '_action_scope', None) or {}
    result = {'format': 1, 'command': command, 'account': account,
              'identities': list(identities), 'source': source, 'destination': destination,
              'roles': roles or {}, 'recipients': list(recipients),
              'arguments': scope.get('arguments', {}) if arguments is None else arguments, **details}
    for field in ('operation_id', 'stage'):
        if field in scope.get('arguments', {}):
            result[field] = scope['arguments'][field]
    return copy.deepcopy(result)


@contextmanager
def mutation(store, value, *, source_key=None, action=None, changes=None):
    store.ensure_writable()
    scope = getattr(store, '_action_scope', None) or {}
    key = source_key or scope.get('source_key')
    action = action or scope.get('action') or ('testapp_' if value['account'] == 'fixture' else 'mail_') + value['command'].lower()
    own = key is None
    if own:
        store.write(changes or {}, action, 'Mutation context committed before command', outcome='started',
                    intent_context=value, intent_arguments=value['arguments'])
        key = store.active_intents[action]
    else:
        row = store.get(key)
        required_state = 'submitting' if key.startswith('op:') else 'started'
        if not isinstance(row, dict) or row.get('state') != required_state or not key.startswith(('op:', 'intent:', 'mail:filing:', 'mail:rename:')):
            raise Refused('invalid_evidence', 'Mutation requires its own committed unfinished source identity.')
        if row.get('context') != value or row.get('context_version') != 1:
            row.update(context=copy.deepcopy(value), context_version=1)
            store.write({**(changes or {}), key: row}, action, 'Mutation context committed before command',
                        key[3:] if key.startswith('op:') else None, outcome='started')
        elif changes:
            store.write(changes, action, 'Mutation preparation committed before command',
                        key[3:] if key.startswith('op:') else None, outcome='started')
    # A failed admission or either commit prevents entering the effect. A lost
    # effect/result leaves this exact context open for inspection, never replay.
    yield key
    if own and store.get(key) is not None:
        store.write({}, action, 'Mutation completion recorded', outcome='done')


def fold_context(store, value, changes, *, source_key=None):
    """Put the next command's context in a write that already precedes it.

    mutation() still checks the committed row at dispatch. A changed live input
    therefore needs its own commit instead of trusting this earlier snapshot.
    """
    scope = getattr(store, '_action_scope', None) or {}
    key = source_key or scope.get('source_key')
    row = changes[key] if key in changes else store.get(key) if key else None
    required_state = 'submitting' if key and key.startswith('op:') else 'started'
    if (not isinstance(row, dict) or row.get('state') != required_state or
            not key.startswith(('op:', 'intent:', 'mail:filing:', 'mail:rename:'))):
        raise Refused('invalid_evidence', 'Folded context requires its own unfinished source identity.')
    return {**changes, key: {**row, 'context': copy.deepcopy(value), 'context_version': 1}}
