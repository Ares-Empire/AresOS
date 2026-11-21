"""Loss refusals: a fixed service sentence, with page text only as untrusted data (brief 28a, item 5b).

The extension refuses an act that would drop a Claude tab's document (the
first input's guarded reload, a reload, back, forward, an address, a close)
with the code `reload_required` and a bounded report of what would be lost.
Field labels in it are page text. So the report never enters a message, an
operation's reason, a stage's prose or a notice's prose: the service writes its
own sentence and carries the checked, escaped report under
`untrusted_content.loss`. A missing or malformed report still refuses with that
sentence, marked `unavailable`; it never falls back to the extension's text.

This module imports nothing from the definitions: the bridge imports it, and
the definitions import it for the declared shapes.
"""
import copy

from ..common import Refused, validate, visible

MESSAGE = 'This action may discard work. Nothing was done; inspect the loss report.'
# The acts of the extension's requireDiscard, in its own words.
ACTS = ['first_input', 'reload', 'navigate', 'back', 'forward', 'close']
# The extension lists at most FIELDS fields and counts the rest in more_fields.
FIELDS = 10
# A field's description as the extension sends it. visible() writes a
# character as at most six (\uXXXX), so the public form allows six times this.
DESCRIPTION = 256
COUNT = {'type': 'integer', 'minimum': 0, 'maximum': 1_000_000}


def _obj(properties, required=None):
    return {'type': 'object', 'properties': properties,
            'required': list(properties) if required is None else required, 'additionalProperties': False}


def _report(description, extra=None):
    field = _obj({'description': {'type': 'string', 'minLength': 1, 'maxLength': description},
                  'by': {'type': 'string', 'enum': ['owner', 'claude']}})
    base = {'act': {'type': 'string', 'enum': ACTS},
            'fields': {'type': 'array', 'items': field, 'maxItems': FIELDS},
            'more_fields': COUNT, 'frames_uninspected': COUNT, 'media': {'type': 'boolean'},
            'owner_work_present': {'type': 'boolean'}}
    return _obj({**base, **(extra or {})}, list(base))


# What the extension sends beside {"ok": false, "error": "reload_required"}.
WIRE = _report(DESCRIPTION)
# In a batched result, the index of the step whose act would lose the work.
STEP = {'step': COUNT}
# What a result carries: the report, or `unavailable` when the extension's was missing or malformed.
LOSS = {'anyOf': [_report(6 * DESCRIPTION, STEP),
                  _obj({'unavailable': {'type': 'boolean', 'enum': [True]}, **STEP}, ['unavailable'])]}
UNTRUSTED = _obj({'loss': LOSS})
# The `error` of a Chrome tool's result. Other keys (storage notes) stay allowed as before.
ERROR = {'type': 'object', 'properties': {'code': {'type': 'string'}, 'message': {'type': 'string'},
                                          'untrusted_content': UNTRUSTED},
         'required': ['code', 'message']}


class LossRefused(Refused):
    """reload_required with the fixed MESSAGE; the report is only in untrusted_content."""

    def __init__(self, report):
        super().__init__('reload_required', MESSAGE)
        self.untrusted_content = {'loss': report}


def checked(raw):
    """The extension's report, checked and escaped like page text, or `unavailable`.

    Its descriptions are the reader's, with the extension's positions for those
    that read alike (brief 28a, item 3b); a report where two still read alike
    is malformed too.
    """
    try:
        validate(raw, WIRE, 'loss report')
    except Refused:
        return {'unavailable': True}
    # The extension numbers fields that read alike (item 3b); two that still read alike can't be told apart.
    if len({field['description'] for field in raw['fields']}) != len(raw['fields']) or \
            (not raw['owner_work_present'] and any(field['by'] == 'owner' for field in raw['fields'])):
        return {'unavailable': True}
    return {**raw, 'fields': [{'description': visible(field['description']), 'by': field['by']} for field in raw['fields']]}


def at_step(exc, step):
    """A batched step's loss: the refusal's report with the step's index, so it is never another step's."""
    content = copy.deepcopy(exc.untrusted_content)
    content['loss']['step'] = step
    return content
