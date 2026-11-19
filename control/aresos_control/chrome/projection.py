"""What an operation shows of its page (brief 28a, items 3 and 3a).

The binding an operation keeps, and every comparison made with it, holds the
page's facts whole: full addresses and every option of every list. What
leaves the service about them is a projected copy, made here and nowhere else:

- `addresses` writes every address through `public_address` (item 3): in the
  public form for a question, a description and what a tool returns, in the
  short form (no query, no fragment) for the texts the audit log holds, which
  are an operation's stage texts and a notice's text.
- `lists` writes a list's options as the ones chosen and their number
  (item 3a), and for a `select` step also the option it will choose, so a long
  list can't fill an approval. What a form sends is still shown whole.
- `shown` is the description's page facts: item 3b's described copy with both.

Nothing reads a projected copy back for a comparison, and nothing prepares
from one.
"""
import copy

from ..common import ASK_LIMIT, QUESTION_LIMIT, Refused, canonical, visible
from .address import public_address

# The keys whose value is an address wherever they sit: the page, a frame, a
# link's target, a dialog's frame, the fields of a send outside a form, a
# confirmation, the page the extension reports after an input.
ADDRESS_KEYS = frozenset(('url', 'frame_url', 'effective_url', 'href'))
# A form's own address is its `action`; elsewhere `action` names a tool.
FORM_KEYS = frozenset(('form', 'forms'))

# Item 3a: Chrome's two fixed pieces of advice after a refusal for size.
SHORTEN = 'Shorten the text you filled, or ask the owner to send it himself; nothing is cut to make it fit.'
OWNER = ('This form sends more than a question can show, whatever you fill in; ask the owner to send it himself; '
         'nothing is cut to make it fit.')
# Field kinds whose value Claude fills as text: what "the text you filled" can shorten.
TYPED = frozenset(('text', 'search', 'email', 'tel', 'url', 'number', 'password', 'date', 'datetime-local', 'month',
                   'week', 'time', 'textarea', 'editable', 'textbox'))


def addresses(value, short=False, form=False):
    """A copy of `value` in which every address went through `public_address`."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if isinstance(item, str) and (key in ADDRESS_KEYS or form and key == 'action'):
                result[key] = public_address(item, short=short)
            else:
                result[key] = addresses(item, short, key in FORM_KEYS)
        return result
    if isinstance(value, list):
        return [addresses(item, short, form) for item in value]
    return value


def record(value):
    """The short form for what the audit log holds (a stage text, a notice): addresses without query or fragment."""
    return addresses(value, short=True)


def lists(value, choosing=None):
    """Item 3a, in place: every field with options shows `chosen` and `option_count` instead of `options`.

    `chosen` holds the options selected now, each exactly as the binding holds
    it. `choosing` is a `select` step's value: the target (the top-level
    `target`) then also shows every option of the binding with that value.
    """
    target = value.get('target') if isinstance(value, dict) else None
    if choosing is not None and isinstance(target, dict) and isinstance(target.get('options'), list):
        target['choosing'] = [copy.deepcopy(option) for option in target['options']
                              if isinstance(option, dict) and option.get('value') == choosing]
    _lists(value)
    return value


def _lists(item):
    if isinstance(item, dict):
        if isinstance(item.get('options'), list):
            options = item.pop('options')
            item['chosen'] = [copy.deepcopy(option) for option in options
                              if isinstance(option, dict) and option.get('selected') is True]
            item['option_count'] = len(options)
        for child in item.values():
            _lists(child)
    elif isinstance(item, list):
        for child in item:
            _lists(child)


def choosing(payload):
    """The value a `select` step will choose, or None for every other step."""
    data = payload.get('input') or {}
    return data.get('value') if data.get('verb') == 'select' else None


def shown(described, payload):
    """The description's page facts: item 3b's described copy with item 3's public addresses and item 3a's lists."""
    return lists(addresses(described), choosing(payload))


def blank(payload):
    """A copy of an action's payload with every typed field's value and the text next to Send left empty.

    Only to choose the advice after a refusal for size (item 3a); nothing is
    prepared or sent from it.
    """
    result = copy.deepcopy(payload)
    def walk(item):
        if isinstance(item, dict):
            typed = item.get('type') in TYPED or item.get('editable') is True and 'type' not in item
            if typed and isinstance(item.get('value'), str):
                item['value'] = ''
            for child in item.values():
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)
    state = result.get('binding') or {}
    for key in ('form', 'editable', 'item_fields', 'target'):
        walk(state.get(key))
    if isinstance((state.get('target') or {}).get('page_dialog'), dict):
        walk(state['target']['page_dialog'])
    if isinstance(state.get('compose'), dict) and isinstance(state['compose'].get('text'), str):
        state['compose']['text'] = ''
    if isinstance(result.get('input'), dict) and result['input'].get('verb') == 'fill':
        result['input']['text'] = ''
    return result


def fits(question, description, operation_id, expires):
    """Whether an approval would pass the base's own count (`approval_input`)."""
    approval = {'question': visible(question), 'operation_id': operation_id,
                'description': visible({**description, 'expires_at': expires})}
    return len(approval['question']) <= QUESTION_LIMIT and len(canonical(approval).encode()) <= ASK_LIMIT


def advised(exc, advice):
    """The refusal for size with its own sentence and then Chrome's advice; code and content unchanged."""
    refusal = Refused(exc.code, f'{exc} {advice}')
    refusal.untrusted_content = getattr(exc, 'untrusted_content', None)
    return refusal
