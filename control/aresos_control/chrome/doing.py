"""Brief 28a, item 5: chrome_do, before item 8's step 1d offers it.

Up to 20 steps in one Claude tab: click, fill, select, check, press, scroll
(each by the short reference a read gave), dialog and wait.

- **Check first.** Every reference is resolved and checked by item 2's rule
  (`Chrome.acting`, the fingerprint included) before the first step runs. If
  one fails, nothing has run.
- **Each step is brief 20's path.** An input step goes through `payload`
  (fresh facts, item 2's rule again with the value compared whole, the
  classification, the binding), then `free` (committed as its own operation,
  dispatched once) or `engine.reserve` (prepared, not dispatched). After a free
  input the element's fingerprint moves to what the reader observed of it
  (`References.acted`): that alone moves "what Claude last saw" inside a list.
  A dialog step is brief 20's dialog branch (`Chrome.dialog_payload`), on the
  dialog the service last showed Claude for the tab. A wait waits as brief 28's
  `until` does.
- **The look between steps.** After every step that ran, the service asks
  `page_state`. Another top document, an open dialog or a queued page step
  stops the list; a queued step goes through brief 20's `steps`, as a read
  handles it.
- **The list stops** after the first step that isn't `done` or `unchanged`, and
  after one that was prepared, made the page start something the tool held,
  opened a dialog, loaded another page or ended `unknown`. Nothing is retried.
- **The report.** The outline before the first step and again once the page
  has gone quiet (or, after a new top document, loaded) give `changed`
  (`view.changes`); a new top document gives its outline instead.

**Time** (item 5, "Time"): the call answers by second CALL of its own clock.
No step starts after second DISPATCH and every command before an input's
dispatch carries the time to it, the input command too (`Chrome.free`'s
`dispatch_by`); the bridge waits for an input's reply two seconds longer. A
wait ends by second DISPATCH. The report's waiting ends by second REPORT and
its outline read answers by second READ. A step that was answered `expired`
dispatched nothing: it counts in `not_run` and `deadline` is true.
"""
import time

from ..common import RESULT_LIMIT, Refused, canonical, visible
from . import going
from . import loss
from . import view as outline_view
from .address import public_address
from .deadline import NOT_READ, Deadline
from .references import Stale

CALL, DISPATCH, REPORT, READ = 18.0, 12.0, 16.0, 17.0
QUIET_MAX, POLL = 1.5, .1
STEPS, TEXT, KEY, DIALOG_TEXT, UNTIL = 20, 20000, 64, 4096, 200
WAIT_MS, WAIT_MAX = 3000, 8000
MAX, MAX_LOW, MAX_HIGH, NEW_PAGE = 2000, 500, 8000, 4000

# What each step needs, and what it may have besides.
NEEDS = {'click': ('ref',), 'fill': ('ref', 'text'), 'select': ('ref', 'value'), 'check': ('ref', 'checked'),
         'press': ('ref', 'key'), 'scroll': ('ref', 'y'), 'dialog': ('accept',), 'wait': ('until',)}
MAY = {'dialog': ('text',), 'wait': ('timeout_ms',)}

NO_OPTION = 'no such option'
DISABLED = 'that option is disabled'
SEVERAL = 'several options carry this label; pass the value'
OTHER_DIALOG = ("This isn't the dialog the last result showed in this tab; "
                "the dialog open now is in untrusted_content.dialog.")


def query(args):
    """chrome_do's input, checked before anything is asked of Chrome."""
    def refuse(message):
        raise Refused('invalid_input', message)
    if type(args) is not dict or set(args) - {'tab', 'steps', 'max', 'discard_unsaved'} or not {'tab', 'steps'} <= set(args):
        refuse('chrome_do takes tab and steps, and max and discard_unsaved.')
    if type(args['tab']) is not int or args['tab'] < 0:
        refuse('tab is a tab number.')
    steps = args['steps']
    if type(steps) is not list or not 1 <= len(steps) <= STEPS:
        refuse('steps holds 1 to 20 steps.')
    for index, step in enumerate(steps):
        where = 'steps[%d]: ' % index
        if type(step) is not dict or step.get('do') not in NEEDS:
            refuse(where + 'do is one of ' + ', '.join(NEEDS) + '.')
        verb = step['do']
        allowed = {'do', *NEEDS[verb], *MAY.get(verb, ())}
        if set(step) - allowed or any(key not in step for key in NEEDS[verb]):
            refuse(where + '%s takes %s.' % (verb, ', '.join(key for key in (*NEEDS[verb], *MAY.get(verb, ())))))
        if 'ref' in step and (type(step['ref']) is not str or not 1 <= len(step['ref']) <= 32):
            refuse(where + 'ref is a reference a read gave.')
        if verb == 'fill' and (type(step['text']) is not str or len(step['text']) > TEXT):
            refuse(where + 'text is at most 20000 characters.')
        if verb == 'select' and (type(step['value']) is not str or len(step['value']) > TEXT):
            refuse(where + "value is an option's value or its label.")
        if verb == 'check' and type(step['checked']) is not bool:
            refuse(where + 'checked is true or false.')
        if verb == 'press' and (type(step['key']) is not str or not 1 <= len(step['key']) <= KEY):
            refuse(where + 'key names one key, at most 64 characters.')
        if verb == 'scroll' and type(step['y']) is not int:
            refuse(where + 'y is whole pixels, negative is up.')
        if verb == 'dialog' and (type(step['accept']) is not bool or
                                 'text' in step and (type(step['text']) is not str or len(step['text']) > DIALOG_TEXT)):
            refuse(where + 'accept is true or false; text, for a prompt, at most 4096 characters.')
        if verb == 'wait':
            until = step['until']
            if not (type(until) is dict and len(until) == 1 and next(iter(until)) in ('text', 'gone') and
                    type(next(iter(until.values()))) is str and 1 <= len(next(iter(until.values()))) <= UNTIL):
                refuse(where + 'until is {"text": ...} or {"gone": ...}.')
            timeout = step.get('timeout_ms', WAIT_MS)
            if type(timeout) is not int or not 0 <= timeout <= WAIT_MAX:
                refuse(where + 'timeout_ms is a whole number from 0 to 8000.')
    limit = args.get('max', MAX)
    if type(limit) is not int or not MAX_LOW <= limit <= MAX_HIGH:
        refuse('max is a whole number from 500 to 8000.')
    if type(args.get('discard_unsaved', False)) is not bool:
        refuse('discard_unsaved is true or false.')


def label(text):
    """A label as the label rule compares it: trimmed, runs of spaces joined."""
    return ' '.join(text.split())


def chosen_value(target, value):
    """The option value a `select` step gives the extension: `value` as an option's value, else as its label."""
    options = target.get('options') if isinstance(target, dict) else None
    if not isinstance(options, list):
        return value  # not a list: brief 20's path refuses or handles it as before
    by_value = [option for option in options if option.get('value') == value]
    if by_value:
        if all(option.get('disabled') for option in by_value):
            raise Refused('refused', DISABLED)
        return value
    by_label = [option for option in options if isinstance(option.get('label'), str) and label(option['label']) == label(value)]
    if not by_label:
        raise Refused('refused', NO_OPTION)
    if len(by_label) > 1:
        raise Refused('refused', SEVERAL)
    if by_label[0].get('disabled'):
        raise Refused('refused', DISABLED)
    return by_label[0]['value']


def inputs(step):
    """What brief 20's verb takes besides its element."""
    verb = step['do']
    if verb == 'scroll':
        return {'x': 0, 'y': step['y']}
    return {key: step[key] for key in ('text', 'value', 'checked', 'key') if key in step}


class Stop(Exception):
    """The list stops here; the step's entry is written."""


class Doing:
    """One chrome_do call on the adapter `chrome`."""

    def __init__(self, chrome, args):
        query(args)
        self.chrome, self.bridge, self.args = chrome, chrome.bridge, args
        self.tab, self.steps = args['tab'], args['steps']
        self.clock = Deadline()
        self.entries, self.prepared, self.unknown, self.stopped = [], [], [], []
        self.deadline, self.loaded, self.new_page = False, None, False
        self.now = self.dialog = self.loss = self.clipboard = self.error = None
        self.start = None      # the top document (Chrome's id) the list started on
        self.before = None     # the outline before the first step
        self.ran = False       # whether any step ran past its checks
        self.token = None      # the page's token at the last look

    # --- the call -----------------------------------------------------------

    def run(self):
        with self.bridge.bounded(self.clock.at(READ)):
            self.mode = self.chrome.mode(acting=True)
            if self.bridge.call('tab_context', tab=self.tab).get('control') is None:
                raise Refused('take_first', going.TAKE_FIRST)
            try:
                if self.checked():
                    self.start = self.bridge.call('page_state', tab=self.tab).get('document')
                    _, self.before = self.chrome.outline_view(self.tab)
                    self.run_steps()
                return self.result()
            finally:
                self.chrome.references.trim(self.tab)

    def checked(self):
        """Item 2's rule for every reference before the first step. False when one failed: nothing has run.

        The first step's own check comes right before it with nothing run
        before it, so it isn't asked twice.
        """
        for index, step in enumerate(self.steps):
            if 'ref' not in step or index == 0:
                continue
            try:
                with self.bridge.bounded(self.clock.at(DISPATCH)):
                    self.chrome.acting(self.tab, step['ref'])
            except Refused as exc:
                try:
                    self.refusal(index, step, exc)
                except Stop:
                    return False
        return True

    def run_steps(self):
        for index, step in enumerate(self.steps):
            if index and self.look():
                return
            if time.monotonic() >= self.clock.at(DISPATCH):
                self.deadline = True  # no step starts after second DISPATCH
                return
            try:
                {'dialog': self.answer, 'wait': self.wait}.get(step['do'], self.act)(index, step)
            except Stop:
                if self.ran:
                    self.look()
                return
        self.look()

    # --- the steps ----------------------------------------------------------

    def act(self, index, step):
        """An input step: brief 20's verb through `payload`, then `free` once or `engine.reserve`."""
        verb = step['do']
        args = {'tab': self.tab, 'ref': step['ref'], **inputs(step)}
        if self.args.get('discard_unsaved'):
            args['discard_unsaved'] = True  # the first input's reload of a taken tab or a popup, as on main
        try:
            with self.bridge.bounded(self.clock.at(DISPATCH)):
                if verb == 'select':
                    # By value, else by label, on the fresh facts; the extension always gets the option's value.
                    _, frame, _ = self.chrome.acting(self.tab, step['ref'])
                    args['value'] = chosen_value(frame.get('target'), step['value'])
                payload, _ = self.chrome.payload(verb, args)
            if payload['kind']:
                self.prepare(index, step, verb, payload)
            result = self.chrome.free(verb, payload, dispatch_by=self.clock.at(DISPATCH))
        except Refused as exc:
            self.refusal(index, step, exc)
        page = result['untrusted_content'].get('page') if isinstance(result['untrusted_content'], dict) else None
        self.chrome.references.acted(self.tab, step['ref'], page.get('change') if isinstance(page, dict) else None)
        self.dispatched(index, step, result)

    def answer(self, index, step):
        """A dialog step: brief 20's dialog branch, on the dialog the last result showed Claude in this tab."""
        try:
            with self.bridge.bounded(self.clock.at(DISPATCH)):
                facts = self.bridge.call('dialog_facts', tab=self.tab)
                dialog = facts.get('dialog') if isinstance(facts, dict) else None
                present = None if not isinstance(dialog, dict) else {'kind': dialog.get('kind'), 'text': dialog.get('text', '')}
                if present is None or present != self.chrome.references.dialog(self.tab):
                    if present is not None:
                        # The dialog open now is shown, and counts as shown, as a stale reference's present line does.
                        self.chrome.references.dialog_shown(self.tab, present)
                        self.dialog = visible(present)
                    self.entry(step, 'stale', code='stale_reference', message=OTHER_DIALOG)
                    raise Stop()
                args = {'tab': self.tab, 'expected': dialog, 'accept': step['accept'],
                        **({'text': step['text']} if 'text' in step else {})}
                payload = self.chrome.dialog_payload(args)
            if payload['kind']:
                self.prepare(index, step, 'dialog', payload)
            result = self.chrome.free('dialog', payload, dispatch_by=self.clock.at(DISPATCH))
        except Refused as exc:
            self.refusal(index, step, exc)
        self.dispatched(index, step, result)

    def wait(self, index, step):
        """A wait: brief 28's `until`, at most `timeout_ms`, and never past second DISPATCH. Not an input."""
        own = time.monotonic() + step.get('timeout_ms', WAIT_MS) / 1000
        end = min(own, self.clock.at(DISPATCH))
        until = step['until']
        self.ran = True
        try:
            with self.bridge.bounded(self.clock.at(DISPATCH)):
                state, view = self.chrome.outline_view(self.tab)
                met = self.chrome.until_met(view, until)
                while not met and view.dialog is None and time.monotonic() < end:
                    time.sleep(max(0, min(POLL, end - time.monotonic())))
                    current = self.bridge.call('page_state', tab=self.tab)
                    if current.get('dialog') or current.get('token') != state.get('token'):
                        state, view = self.chrome.outline_view(self.tab)
                        met = self.chrome.until_met(view, until)
        except Refused as exc:
            if exc.code != 'expired':
                self.refusal(index, step, exc)
            met = False
        if met:
            self.entry(step, 'done')
            return
        if own > self.clock.at(DISPATCH) and time.monotonic() >= self.clock.at(DISPATCH) - POLL:
            self.deadline = True  # cut off at second DISPATCH, before its own timeout
        self.entry(step, 'timeout')
        raise Stop()

    def prepare(self, index, step, verb, payload):
        """An asking step: its operation is reserved, nothing is dispatched, and the list stops."""
        try:
            prepared = self.chrome.engine.reserve('chrome', 'submit', payload)
        except Refused as exc:
            if exc.code != 'asking_input_too_large':
                raise
            raise self.chrome.too_large(exc, verb, payload) from None  # item 3a's advice; a `refused` step
        self.prepared.append(prepared)
        self.entry(step, 'prepared')
        raise Stop()

    def dispatched(self, index, step, result):
        """A free step that ran: its outcome from the committed operation, and what stops the list after it."""
        self.ran = True
        operation_id = result['operation_id']
        operation = self.chrome.store.get('op:' + operation_id) or {}
        reply = result['untrusted_content'] if isinstance(result['untrusted_content'], dict) else {}
        page = reply.get('page') if isinstance(reply.get('page'), dict) else {}
        if isinstance(page.get('clipboard'), dict):
            routes = sorted(set((self.clipboard or {}).get('routes', [])) | set(page['clipboard'].get('routes') or []))
            self.clipboard = {**page['clipboard'], 'routes': routes}
        followups = self.followups(result.get('followups') or [])
        if operation.get('state') == 'unknown':
            self.unknown.append(operation_id)
            self.entry(step, 'unknown', operation_id=operation_id, code='unknown', message=operation.get('reason', ''))
            raise Stop()
        self.entry(step, 'unchanged' if reply.get('no_change') else 'done', operation_id=operation_id)
        if followups or reply.get('dialog'):
            raise Stop()  # it made the page start something the tool held, or opened a dialog

    def refusal(self, index, step, exc):
        """A step that didn't run, or may have: its entry, and the list stops."""
        if exc.code == 'expired':
            # Nothing was dispatched: the step counts in not_run, like one that never started.
            self.deadline = True
            raise Stop()
        if isinstance(exc, Stale):
            exc = self.chrome.stale_shown(self.tab, exc)
            if isinstance(exc.untrusted_content, dict) and 'now' in exc.untrusted_content:
                self.now = exc.untrusted_content['now']
        operation_id = getattr(exc, 'operation_id', None)
        if exc.code in ('stale_reference', 'stale_approval'):
            self.entry(step, 'stale', operation_id=operation_id, code='stale_reference', message=str(exc))
        elif exc.code in ('unknown', 'transport_error'):
            if operation_id:
                self.unknown.append(operation_id)
            self.entry(step, 'unknown', operation_id=operation_id, code=exc.code, message=str(exc))
        else:
            if isinstance(exc, loss.LossRefused):
                # Item 5b: the report is untrusted data with this step's index, so it is never another step's.
                self.loss = loss.at_step(exc, index)['loss']
            self.entry(step, 'refused', operation_id=operation_id, code=exc.code, message=str(exc))
        raise Stop()

    def entry(self, step, outcome, operation_id=None, code=None, message=None):
        entry = {'do': step['do'], **({'ref': step['ref']} if 'ref' in step else {}), 'outcome': outcome}
        if operation_id:
            entry['operation_id'] = operation_id
        if code is not None:
            entry.update(code=code, message=message)
        self.entries.append(entry)

    # --- the look between steps -----------------------------------------------

    def look(self):
        """page_state after a step: True when the list must stop before the next one."""
        try:
            with self.bridge.bounded(self.clock.at(REPORT)):
                state = self.bridge.call('page_state', tab=self.tab)
                self.token = state.get('token')
                if state.get('dialog'):
                    return True
                document = state.get('document')
                if document is None:
                    return True  # no top document right now: a navigation is under way
                if self.start is None:
                    self.start = document  # the list started behind a dialog
                if document != self.start:
                    self.new_page = True
                    return True
                if state.get('queued'):
                    queued = self.bridge.call('queued_steps', tab=self.tab)
                    self.chrome.reconcile_checks({'tab': self.tab}, queued)
                    if self.followups(self.chrome.steps(queued, self.tab)):
                        return True
        except Refused as exc:
            self.error = {'code': exc.code, 'message': str(exc)}
            return True
        return False

    def followups(self, items):
        """Brief 20's page steps: a held submission is prepared, everything else is named in `stopped`."""
        for item in items:
            if isinstance(item, dict) and item.get('approval'):
                self.prepared.append(item)
            else:
                self.stopped.append(visible(item))
        return bool(items)

    # --- the report -----------------------------------------------------------

    def settle(self):
        """Wait until the page has gone quiet (at most QUIET_MAX), or, after a new top document, loaded (to REPORT).

        Quiet: ready, and the token the same in two looks in a row. Each input
        has already waited out its hold of half a second, so the look after
        the last step counts as the first of the two.
        """
        end = min(time.monotonic() + QUIET_MAX, self.clock.at(REPORT))
        token = self.token
        while True:
            try:
                with self.bridge.bounded(self.clock.at(REPORT)):
                    state = self.bridge.call('page_state', tab=self.tab)
            except Refused:
                break
            now = time.monotonic()
            if state.get('dialog'):
                break
            if not self.new_page and self.start is not None and state.get('document') not in (None, self.start):
                self.new_page = True
            if self.new_page:
                end = self.clock.at(REPORT)
            if state.get('ready') is True and state.get('token') is not None and state.get('token') == token:
                if self.new_page:
                    self.loaded = True
                return
            token = state.get('token')
            if now >= end:
                break
            time.sleep(max(0, min(POLL, end - now)))
        if self.new_page:
            self.loaded = False

    def result(self):
        content = {'url': None, 'title': None, 'changed': '', 'more_changes': 0, 'outline': None, 'dialog': self.dialog,
                   'clipboard': self.clipboard, 'stopped': self.stopped, 'now': self.now}
        if self.loss is not None:
            content['loss'] = self.loss
        result = {'tab': self.tab, 'steps': self.entries, 'not_run': 0, 'deadline': self.deadline,
                  'prepared': self.prepared, 'unknown': self.unknown, 'loaded': None, 'untrusted_content': content,
                  'version_notice': self.mode['notice']}
        # Entries are written in order, one per step that ran or stopped the list; a step answered
        # `expired` has none: every step after the last entry counts.
        result['not_run'] = len(self.steps) - len(self.entries)
        try:
            self.report(result)
        except Refused as exc:
            if exc.code == 'expired':
                exc = Refused('not_read', NOT_READ)
            self.error = self.error or {'code': exc.code, 'message': str(exc)}
        if self.error is not None:
            result['error'] = self.error
        return result

    def report(self, result):
        content = result['untrusted_content']
        if self.before is None:
            # Nothing ran: the page as the tab shows it.
            context = self.bridge.call('tab_context', tab=self.tab)
            content.update(url=public_address(context.get('url', '')), title=visible(context.get('title', '')))
            return
        # Also after a step that ran nothing of its own: a taken tab's first-input reload replaces the page.
        self.settle()
        result['loaded'] = self.loaded
        with self.bridge.bounded(self.clock.at(READ)):
            if self.new_page:
                self.page(result)
                return
            _, after = self.chrome.outline_view(self.tab)
        header = outline_view.header(after)
        content.update(url=header['url'], title=header['title'])
        self.chrome.references.dialog_shown(self.tab, after.dialog)
        if after.dialog is not None or self.before.dialog is not None:
            content['dialog'] = header['dialog']
            return
        text, more, shown = outline_view.changes(self.before, after, self.chrome.references, self.args.get('max', MAX))
        self.chrome.references.returned(self.tab, shown)
        content.update(changed=text, more_changes=more)

    def page(self, result):
        """A new top document: its outline, at most NEW_PAGE characters, in place of `changed`."""
        reading = self.chrome.outline_tab(self.tab, {}, outline_view.asked(), NEW_PAGE, None)
        pending = self.chrome.engine.pending('chrome', resolve_checks=False)
        notice = self.mode['notice']
        if notice:
            pending = {**pending, 'chrome_version_notice': notice}
        content = result['untrusted_content']

        def measure(reads):
            shown = reads[0]['untrusted_content']
            sized = {**result, 'untrusted_content': {**content, 'url': shown['url'], 'title': shown['title'],
                                                     'dialog': shown['dialog'], 'outline': shown['outline']}}
            return len(canonical({'ok': True, 'data': sized, 'pending': pending}).encode())
        from .adapter import PENDING_DRIFT
        [entry] = outline_view.fit([reading], measure, self.chrome.references, RESULT_LIMIT - PENDING_DRIFT)
        shown = entry['untrusted_content']
        content.update(url=shown['url'], title=shown['title'], dialog=shown['dialog'], outline=shown['outline'])
