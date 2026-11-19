"""Every field an asking question names can be told apart (brief 28a, item 3b).

Bound element ids already stop a swap, but two fields labelled "Note" didn't
tell the owner which one he was allowing. So every field that a question or
its description lists carries `description`: its label as the question quotes
it, and, when another field of the same question reads the same, its position
among them in the question's order, `"Note" (1 of 2)`.

Labels count as equal as the owner would read them: after item 0's repair
(the native wire hands the service repaired text, so two raw labels that
repair alike arrive equal), after the cut at 80 characters, and every unnamed
field of one kind reads the same. Positions count over the whole question:
frames in the order the binding holds them, fields in their list's order
within a frame. So two equal labels in two frames that look alike still differ
by position, and no frame needs a description of its own; the typed-field
question still names each frame by its number and site, as before. A field
listed twice (a form's field that is also in its page dialog) is one field
with one description.

Only bound facts go in: the label, the reader's `unnamed` mark, the type, the
element, frame and document, and the lists' order. No value is read for it.
Both the service and the extension compare the whole binding that holds those
facts before an approved read or input, so a description can't change after
the owner saw it: a typed-field list that changed asks afresh, and a send's
changed fields refuse before input.

The service derives the descriptions here, from the bound list, and nowhere
else: `prepare` takes its question and description from one call, `free`
commits the same copy, and an approved typed read returns each value under the
words this same function gives the same bound list. The binding itself, which
the payload keeps and the extension compares, never holds a description.
Loss reports are numbered the same way by the extension (`background.js`,
`distinctDescriptions`), which alone sees every field before the report's cut.
"""
from collections import Counter
import copy

LABEL = 80
# An unnamed field reads as its kind, in fixed words: never page text.
KINDS = {'textarea': 'textarea', 'hidden': 'hidden field', 'checkbox': 'checkbox', 'radio': 'radio button',
         'select-one': 'list', 'select-multiple': 'list', 'file': 'file field', 'password': 'password field',
         'submit': 'button', 'button': 'button', 'reset': 'button', 'image': 'button'}
SINGLE_LINE = {'text', 'search', 'email', 'tel', 'url', 'number'}


def quoted(label, limit=LABEL):
    """A label in double quotes it can't contain, cut at `limit`, so one hostile label can't pass for several fields."""
    shown = '"' + label[:limit].replace('"', "'") + ('…' if len(label) > limit else '') + '"'
    return shown + (f' ({len(label)} characters)' if len(label) > limit else '')


def shown(field):
    """How a field reads without its position: its quoted label, or `unnamed <kind>`."""
    label = field.get('label')
    if isinstance(label, str) and label and field.get('unnamed') is not True:
        return quoted(label)
    kind = field.get('type')
    return 'unnamed ' + (KINDS.get(kind) or ('single-line field' if kind in SINGLE_LINE else 'field'))


def numbered(entries):
    """{identity: (reading, position, count)} for (identity, field) pairs in question order.

    The first entry of an identity decides how it reads. Equal readings are
    counted in order, so no two identities with the same reading share a position.
    """
    first = {}
    for identity, field in entries:
        first.setdefault(identity, shown(field))
    totals, seen, result = Counter(first.values()), Counter(), {}
    for identity, text in first.items():
        seen[text] += 1
        result[identity] = (text, seen[text], totals[text])
    return result


def description(name):
    """The words of a numbered field: its reading, and its position when another field reads the same."""
    text, position, count = name
    return f'{text} ({position} of {count})' if count > 1 else text


def _identity(frame, document, field, place):
    element = field.get('element')
    # A field always has its reader id; without one it is only itself.
    return (frame, document, element) if isinstance(element, str) and element else (frame, document, None, place)


def _lists(state):
    """An action binding's field lists in question order, each with the frame and document of its fields."""
    here = (state.get('frame'), state.get('document'))
    elsewhere = lambda key: [((entry.get('frame'), entry.get('document')), entry.get('fields'))
                             for entry in state.get(key) or [] if isinstance(entry, dict)]
    target = state.get('target') if isinstance(state.get('target'), dict) else {}
    dialog = target.get('page_dialog') if isinstance(target.get('page_dialog'), dict) else {}
    form = state.get('form') if isinstance(state.get('form'), dict) else {}
    # The editable fields of a send outside a form are every frame's, in document order, so they go first.
    lists = elsewhere('editable') + [(here, form.get('fields')), (here, dialog.get('fields')), (here, state.get('item_fields'))]
    return [(place, [field for field in fields if isinstance(field, dict)]) for place, fields in lists + elsewhere('selected_files')
            if isinstance(fields, list)]


def described(state):
    """A copy of an action's binding whose every listed field carries its description.

    Returns the copy and the target's mark for the question: None, or the
    target's (reading, position, count) when it is a listed field and another
    field of the question reads the same.
    """
    result = copy.deepcopy(state)
    entries = [(_identity(*place, field, (index, position)), field)
               for index, (place, fields) in enumerate(_lists(result)) for position, field in enumerate(fields)]
    names = numbered(entries)
    for identity, field in entries:
        field['description'] = description(names[identity])
    target, mark = result.get('target'), None
    if isinstance(target, dict):
        name = names.get(_identity(result.get('frame'), result.get('document'), target, 'target'))
        if name is not None:
            target['description'] = description(name)
            mark = name if name[2] > 1 else None
    return result, mark


def typed(state):
    """A copy of a typed-field list whose every field carries its description."""
    result = copy.deepcopy(state)
    entries = [(_identity(frame.get('frame'), frame.get('document'), field, (index, position)), field)
               for index, frame in enumerate(result.get('frames') or []) if isinstance(frame, dict)
               for position, field in enumerate(frame.get('fields') or []) if isinstance(field, dict)]
    names = numbered(entries)
    for identity, field in entries:
        field['description'] = description(names[identity])
    return result


def read_values(values, state):
    """Approved values with the descriptions the owner approved, matched by frame and element."""
    names = {(frame.get('frame'), field.get('element')): field['description']
             for frame in typed(state).get('frames') or [] for field in frame.get('fields') or []}
    result = copy.deepcopy(values)
    for frame in result.get('frames') or []:
        for field in frame.get('fields') or []:
            name = names.get((frame.get('frame'), field.get('element')))
            if name is not None:
                field['description'] = name
    return result
