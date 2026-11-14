"""Memoize actual executions by their observed environment reads, not oracle results.

Each branch in the trie is an input the real Tools read during the first execution.
A hit reuses that execution's observed writes/output. Unread per-deployment /etc
values are framed through unchanged; they are NEVER merged in the exploration.
This avoids rerunning e.g. a trial-locked refusal for every unrelated /etc pair.
The driver still executes and verifies every new observed-input combination.
"""
from dataclasses import fields, replace


class Executions:
    def __init__(self, driver):
        self.driver = driver
        self.roots = {}
        self.executed = 0
        self.reused = 0

    @staticmethod
    def input(s, name):
        if name.startswith('keyboard-'):
            role = name.removeprefix('keyboard-')
            return next((p[1:] for p in s.settings if p[0] == role), None)
        if name == 'loaded':
            return s.loaded
        if name == 'session':
            return bool(s.trial and s.trial.fresh)
        operation, record = name.split(':', 1)
        value = {'outcome-pending': s.journal, 'layout-pending': s.trial,
                 'layout-repair': s.repairs}.get(record, 'fixed')
        # Other private inputs are fixed by Driver.install; title depends only
        # on the rows/running/stage already in the root key. Writes during a call
        # can cause further reads; recording the initial input overapproximates.
        if operation == 'exists':
            return bool(value)
        # The restoration equivalence test executes both sides: on reachable
        # settings, a pre-existing intent and the same newly saved intent have
        # the same effects. Frame its literal provenance below, just like /etc.
        return value

    @staticmethod
    def owners(s):
        return {n[0] for n in s.repairs} | ({s.trial.row} if s.trial else set())

    def step(self, s, event, expected):
        # Restart is a host event and reads the chosen /etc as well as the
        # running /etc at finalize. Both, the trial and journal must be keyed.
        host_inputs = ()
        if event[0] in ('restart', 'power-off', 'fresh-login'):
            host_inputs = (None if s.journal is None else s.journal.same_boot,
                           None if s.trial is None else (s.trial.same_boot, s.trial.fresh), s.loaded)
        key = s.bundle, s.rows, s.running, s.stage, event, host_inputs
        root = self.roots.setdefault(key, {})
        node = root
        while 'read' in node:
            value = self.input(s, node['read'])
            if value not in node['branches']:
                break
            node = node['branches'][value]
        if 'effect' not in node:
            found = self.driver.step(s, event, expected)
            changes = {f.name: getattr(found, f.name) for f in fields(s)
                       if f.name not in ('settings', 'restoring') and getattr(found, f.name) != getattr(s, f.name)}
            if host_inputs:
                # The simulated boot changes ages, not record contents. Frame
                # the unobserved fields through, just like nonrunning /etc.
                for name in ('journal', 'trial'):
                    old, new = getattr(s, name), getattr(found, name)
                    if name in changes and old is not None and new is not None:
                        changes[name] = {f.name: getattr(new, f.name) for f in fields(old)
                                         if getattr(old, f.name) != getattr(new, f.name)}
            before = {p[0]: p[1:] for p in s.settings}
            after = {p[0]: p[1:] for p in found.settings}
            writes = {r: p for r, p in after.items() if before.get(r) != p}
            removed = tuple(r for r in before if r not in after)
            before_intents = {p[0]: p[1:] for p in s.restoring}
            after_intents = {p[0]: p[1:] for p in found.restoring}
            intents = {r: p for r, p in after_intents.items() if before_intents.get(r) != p}
            # Removing a trial/note clears its intent even when this execution
            # started without one. A cache hit may carry that extra provenance.
            cleared = (set(before_intents) - set(after_intents)) | (self.owners(s) - self.owners(found))
            _, error, cut, archives, text = self.driver.observed
            effect = changes, writes, removed, intents, cleared, error, cut, archives, text
            node = root
            for name in self.driver.reads:
                if 'read' not in node:
                    assert 'effect' not in node, 'same inputs changed the environment read path'
                    node.update(read=name, branches={})
                assert node['read'] == name, 'nondeterministic environment read order'
                node = node['branches'].setdefault(self.input(s, name), {})
            assert 'read' not in node
            node['effect'] = effect
            self.executed += 1
            return found
        self.reused += 1
        changes, writes, removed, intents, cleared, error, cut, archives, text = node['effect']
        if not changes and not writes and not removed and not intents and not cleared:
            found = s
        else:
            settings = {p[0]: p[1:] for p in s.settings if p[0] not in removed}
            settings.update(writes)
            restoring = {p[0]: p[1:] for p in s.restoring if p[0] not in cleared}
            for role, pair in intents.items():
                # A retry republishes the original snapshot, never replaces it.
                restoring.setdefault(role, pair)
            if host_inputs:
                changes = {name: replace(getattr(s, name), **value) if name in ('journal', 'trial') and isinstance(value, dict)
                           else value for name, value in changes.items()}
            found = replace(s, **changes, settings=tuple(sorted((r, *p) for r, p in settings.items())),
                            restoring=tuple(sorted((r, *p) for r, p in restoring.items())))
        assert bool(error) == bool(expected.stop), ('cached accept/refuse', event, expected.stop, error)
        if error:
            assert expected.stop.lower() in error.lower(), ('cached STOP next step', error)
        assert cut == expected.cut, ('cached cut', event)
        assert found == expected.state, ('cached ledger differs', event, expected.state, found)
        assert archives == expected.archives, ('cached archives', event)
        assert ('confirmed after the restart' in text) == (expected.confirmation and not cut), ('cached confirmation', event)
        if expected.announcement:
            # Same rows, running identity and bundle in the root key, so the
            # concrete removal/settings text was checked by the first execution.
            assert 'removes ' in text or ' is removed ' in text
        return found
