"""Independent reference rules for 22c B2. No owner-tool or fake-host imports.

One word per meaning (briefs/22c-forward-command.md): update stages the bundle's
release or changes nothing; forward selects the newest installed AresOS and never
stages. Each installed system is one command away again.

The ledger records events that happened, including interrupted commands. Boot age
and trial session are equivalence classes, never literal ids: the trial's own
login, or a fresh one; in the trial's boot the owner can go back to its own login,
which is still open. Profiles stay literal: all three supported console/X11
profiles are explored, including mixed settings.
"""
from dataclasses import dataclass, replace

RELEASES = ('13', '27', '28')
PROFILES = ('de', 'us', 'us-intl')


@dataclass(frozen=True)
class Journal:
    word: str
    mode: str
    phase: str
    target: str
    running: str
    before: tuple
    same_boot: bool = True

    def intended(self):
        if self.mode == 'staging':
            return (self.target, self.running, 'S')
        return (self.target,) + tuple(r for r in self.before if r != self.target)


@dataclass(frozen=True)
class Trial:
    row: str
    old: str
    new: str
    same_boot: bool = True
    fresh: bool = False
    proof: bool = False
    reverted: bool = False
    finishing: bool = False


@dataclass(frozen=True)
class Ledger:
    bundle: str
    rows: tuple
    running: str
    stage: str = ''
    journal: Journal | None = None
    trial: Trial | None = None
    repairs: tuple = ()  # (deployment, old profile, attempted profile)
    settings: tuple = ()  # (deployment, console profile, X11 profile)
    loaded: str = 'de'
    restoring: tuple = ()  # (deployment, console, X11) at the durable restoration intent

    def keyboard(self, role=None):
        return next(p[1:] for p in self.settings if p[0] == (role or self.running))

    def setting(self, role, console, x11):
        return replace(self, settings=tuple(sorted([p for p in self.settings if p[0] != role] + [(role, console, x11)])))

    def outcome(self):
        j = self.journal
        if not j:
            return 'none'
        if j.mode == 'staging' and j.same_boot:
            return 'retry' if j.phase == 'intent' and not self.stage else 'complete' if j.phase == 'intent' else 'waiting'
        if self.rows == j.before and not self.stage:
            return 'not-applied'
        assert self.rows == j.intended() and not self.stage, (self, 'neither before nor intended')
        if j.same_boot:
            return 'selection-applied' if self.running == j.target else 'waiting'
        return 'target-boot-confirmed' if self.running == j.target else 'in-place-not-started'


def starts():
    return [Ledger(bundle, rows, rows[0], settings=tuple(sorted((r, 'de', 'de') for r in rows)))
            for rows in (('13', 'S'), ('27', '13', 'S'), ('27', 'S')) for bundle in ('27', '28')]


@dataclass(frozen=True)
class Result:
    state: Ledger
    stop: str = ''
    cut: bool = False
    archives: tuple = ()
    confirmation: bool = False
    announcement: str = ''


def transition(s, event):
    """Predict a step solely from the ledger and the chosen event, before calling any tools."""
    word, phase = event
    t, j = s.trial, s.journal
    if word in ('restart', 'power-off'):
        rows = s.rows
        if s.stage:
            rows = (s.stage, s.running, 'S') if word == 'restart' else rows[1:]
            if word == 'restart':
                s = s.setting(s.stage, *s.keyboard())
        chosen = phase if phase != 'default' else rows[0]
        assert chosen in rows
        s = replace(s, rows=rows, running=chosen, stage='',
                    journal=replace(j, same_boot=False) if j else None,
                    trial=replace(t, same_boot=False, fresh=True) if t else None,
                    settings=tuple(p for p in s.settings if p[0] in rows))
        return Result(replace(s, loaded=s.keyboard()[0]))
    if word == 'fresh-login':
        return Result(replace(s, trial=replace(t, fresh=True)) if t else s)
    if word == 'original-login':
        # Back to the trial's own administrator login, still open in this boot (review 2).
        assert t and t.same_boot, 'the original login does not survive a restart'
        return Result(replace(s, trial=replace(t, fresh=False)))

    archives = []
    # All list-reading commands resolve first, even when their own side/preflight refuses.
    reads = word not in ('proof', 'revert', 'finish')
    outcome = s.outcome()
    if reads:
        if outcome in ('retry', 'complete') and word != 'update':
            return Result(s, stop='update')
        if outcome == 'not-applied':
            archives.append('not-applied')
            s, j, outcome = replace(s, journal=None), None, 'none'
        elif j and outcome not in ('retry', 'complete') and j.phase == 'intent':
            j = replace(j, phase='recorded')
            s = replace(s, journal=j)
            if phase == 'record':
                return Result(s, cut=True)

    def result(state=s, stop='', cut=False, confirm=False, announce=''):
        return Result(state, stop, cut, tuple(archives), confirm, announce)

    def title(state):
        if state.outcome() == 'target-boot-confirmed':
            archives.append('confirmed')
            return replace(state, journal=None), True
        return state, False

    if word in ('check', 'title', 'records', 'reboot'):
        if word == 'reboot':
            if t:
                return result(stop='Layout trial')
            # Only title confirms. The adapter supplies the saved title that reboot checks.
            return result()
        if word == 'check' and ((s.loaded == 'de') != (s.keyboard()[0] == 'de')):
            return result(stop='layout')
        s, confirmed = title(s)
        return result(s, confirm=confirmed)

    if word == 'begin':
        if t:
            return result(stop='Layout trial')
        if outcome == 'waiting':
            return result(stop='restart first')
        if s.stage:
            return result(stop='staged')
        if s.running == 'S':
            return result(stop='German layout')
        if s.running != s.rows[0]:
            return result(stop='does not start next')
        if any(n[0] == s.running for n in s.repairs):
            return result(stop='layout abandon')
        old = s.keyboard()[0]
        if phase == old:
            return result(stop='already selected')
        return result(replace(s, trial=Trial(s.running, old, phase), loaded=phase))

    if word == 'abandon':
        if s.stage:
            return result(stop='staged')
        mine = [n for n in s.repairs if n[0] == s.running]
        if not t and not mine:
            return result(stop='No layout trial')
        def restore(state, role, old):
            if state.keyboard(role) == (old, old):
                return state, False
            if not any(n[0] == role for n in state.restoring):
                state = replace(state, restoring=tuple(sorted((*state.restoring, (role, *state.keyboard(role))))))
            if phase == 'intent':
                return state, True
            state = state.setting(role, old, state.keyboard(role)[1])
            if phase == 'console':
                return state, True
            state = state.setting(role, old, old)
            return state, phase == 'persistent'

        if t:
            if not t.fresh:
                return result(stop='fresh physical')
            if t.row == s.running:
                s, cut = restore(s, s.running, t.old)
                if cut:
                    return result(s, cut=True)
                s = replace(s, restoring=tuple(n for n in s.restoring if n[0] != t.row))
            elif t.finishing:
                s = replace(s, repairs=tuple(sorted((*s.repairs, (t.row, t.old, t.new)))))
            s = replace(s, trial=None, loaded=s.keyboard()[0])
        for role, old, new in mine:
            s, cut = restore(s, role, old)
            if cut:
                return result(s, cut=True)
        s = replace(s, repairs=tuple(n for n in s.repairs if n[0] != s.running), loaded=s.keyboard()[0],
                    restoring=tuple(n for n in s.restoring if n[0] != s.running))
        s, confirmed = title(s)
        return result(s, confirm=confirmed)

    if word in ('proof', 'revert', 'finish'):
        if not t:
            return result(stop='Missing private layout-pending')
        if not t.same_boot:
            return result(stop='crossed a reboot')
        if word == 'finish' and any(n[0] == t.row for n in s.restoring):
            # Restoration is an exclusive phase (review 2): abandon completes it, from any login.
            return result(stop='layout abandon')
        if word == 'proof':
            if s.keyboard() != (t.old, t.old):
                return result(stop='settings changed')
            expected = t.old if t.reverted else t.new
            if (s.loaded == 'de') != (expected == 'de'):
                return result(stop='not actually loaded')
            return result(replace(s, trial=replace(t, proof=True)))
        if t.fresh:
            return result(stop='original')
        if word == 'revert':
            return result(replace(s, loaded=t.old, trial=replace(t, reverted=True, proof=False)))
        if not t.proof:
            return result(stop='proof first')
        if s.keyboard() != (t.old, t.old):
            return result(stop='settings changed')
        s, confirmed = title(s)
        if not t.reverted:
            s = replace(s, trial=replace(t, finishing=True))
            if phase == 'intent':
                return result(s, cut=True, confirm=confirmed)
            s = s.setting(s.running, t.new, t.old)
            if phase == 'console':
                return result(s, cut=True, confirm=confirmed)
            s = s.setting(s.running, t.new, t.new)
            if phase == 'persistent':
                return result(s, cut=True, confirm=confirmed)
        return result(replace(s, trial=None), confirm=confirmed)

    assert word in ('update', 'forward', 'previous', 'rollback', 'keep-stock'), word
    if word == 'rollback' and s.running == 'S':
        return result(stop='keep-stock')
    if word == 'keep-stock' and s.running != 'S':
        return result(stop='rollback')
    releases = [r for r in s.rows if r != 'S' and r != s.stage]
    if word == 'previous' and len(releases) != 2:
        return result(stop='Only one AresOS')
    # update is the only word that stages, and staging is all it does: it never reorders.
    stage = word == 'update'
    if stage:
        if outcome == 'complete':
            s = replace(s, journal=replace(j, phase='recorded'))
            return result(s, cut=phase == 'record')
        if s.bundle in releases:
            # Nothing to install. Nothing to do where it runs and starts next; otherwise the
            # refusal names the word that selects an installed system.
            return result() if s.rows[0] == s.bundle == s.running else result(stop='at forward')
        target = s.bundle
    else:
        target = max(releases) if word == 'forward' else min(releases) if word == 'previous' else 'S'
        if s.rows[0] == target:
            return result()
    if t:
        return result(stop='Layout trial')
    if outcome == 'waiting':
        return result(stop='restart first')
    if s.stage:
        return result(stop='staged')
    if stage and (s.running == 'S' or s.rows[0] != s.running):
        return result(stop='at forward')
    if stage and any(n[0] == s.running for n in s.repairs):
        return result(stop='layout abandon')
    archived = {'target-boot-confirmed': 'confirmed', 'selection-applied': 'applied-not-restarted',
                'in-place-not-started': 'in-place-not-started', 'retry': 'retried'}
    if j:
        archives.append(archived[outcome])
    j = Journal(word, 'staging' if stage else 'reorder', 'intent', target, s.running, s.rows)
    s = replace(s, journal=j)
    removed = next((r for r in releases if r != s.running), '') if stage else ''
    if phase == 'intent':
        return result(s, cut=True)
    if stage:
        s = replace(s, rows=(target, *s.rows), stage=target)
    else:
        s = replace(s, rows=j.intended())
    if phase == 'primitive':
        return result(s, cut=True, announce=removed)
    s = replace(s, journal=replace(j, phase='recorded'))
    return result(s, cut=phase == 'record', announce=removed)


def steps(s):
    """Compute each candidate once; events and the exploration share these predictions."""
    for word in ('check', 'title', 'records', 'reboot', 'update', 'forward', 'previous', 'rollback', 'keep-stock', 'abandon'):
        event = word, 'full'
        yield event, transition(s, event)
    for word in ('update', 'forward', 'previous', 'rollback', 'keep-stock', 'abandon'):
        for phase in (('intent', 'console', 'persistent') if word == 'abandon' else ('intent', 'primitive', 'record')):
            # A refused/no-op command never reaches a phase to cut. Its full event
            # above still runs; omit only these physically nonexistent cut points.
            event = word, phase
            result = transition(s, event)
            if result.cut:
                yield event, result
    for profile in PROFILES:
        event = 'begin', profile
        yield event, transition(s, event)
    if s.trial:
        if not s.trial.fresh:
            event = 'fresh-login', 'full'
            yield event, transition(s, event)
        elif s.trial.same_boot:
            event = 'original-login', 'full'
            yield event, transition(s, event)
        for word in ('proof', 'revert'):
            event = word, 'full'
            yield event, transition(s, event)
        for phase in ('intent', 'console', 'persistent', 'full'):
            event = 'finish', phase
            result = transition(s, event)
            if phase == 'full' or result.cut:
                yield event, result
    for kind in ('restart', 'power-off'):
        rows = (s.stage, s.running, 'S') if s.stage and kind == 'restart' else s.rows[1:] if s.stage else s.rows
        for choice in ('default', *rows):
            event = kind, choice
            yield event, transition(s, event)


def events(s):
    return (event for event, result in steps(s))


def resting(s):
    """Nothing staged, nothing waiting (an interrupted staging included) and no active layout trial."""
    return not (s.stage or s.outcome() in ('waiting', 'retry', 'complete') or s.trial)


def destinations(s):
    """B2 at its original strength: from every resting state, each installed system that does
    not start next, with the ONE command that makes it the next start. No boot-menu path."""
    if not resting(s):
        return
    newest = max(r for r in s.rows if r != 'S')
    for row in s.rows[1:]:
        yield row, ((('keep-stock' if s.running == 'S' else 'rollback') if row == 'S' else
                     'forward' if row == newest else 'previous'), 'full')


def invariants(s, predicted=None):
    """Assert the reference rules: the destination invariant and one word per meaning."""
    def step(state, event):
        if state is s and predicted is not None and event in predicted:
            return predicted[event]
        return transition(state, event)

    # One word per meaning, over every phase of both words (full, and each cut that exists).
    installed = tuple(r for r in s.rows if r != s.stage)
    newest = max(r for r in installed if r != 'S')
    for (word, phase), result in (predicted if predicted is not None else dict(steps(s))).items():
        after = result.state
        if word == 'update':
            # It never selects an installed system: the installed rows keep their order, and the
            # only row it may add is the bundle's release, staged in front.
            assert tuple(r for r in after.rows if r != after.stage) == installed and after.stage in (s.stage, s.bundle), \
                ('update selected an installed system', s, after)
            assert not (after.journal and after.journal.word == 'update' and after.journal.mode != 'staging'), \
                ('update journalled a reorder', s, after)
        if word == 'forward':
            # It never stages and never changes the set of deployments; where it changes the
            # order, the newest installed AresOS moves to the front and nothing else moves.
            assert sorted(after.rows) == sorted(s.rows) and after.stage == s.stage, ('forward changed the deployments', s, after)
            assert after.rows in (s.rows, (newest,) + tuple(r for r in s.rows if r != newest)), ('forward selected another system', s, after)
            assert not (after.journal and after.journal.word == 'forward' and after.journal.mode != 'reorder'), \
                ('forward journalled a staging', s, after)
    update = step(s, ('update', 'full'))
    if resting(s):
        if update.stop == 'at forward':
            # The refusal names the right word: forward then puts the newest installed AresOS first.
            forward = step(s, ('forward', 'full'))
            assert not forward.stop and forward.state.rows[0] == newest and not forward.state.stage, ('update named a word that refuses', s, forward)
        if s.bundle not in installed and s.running != 'S' and s.running == s.rows[0]:
            # Staging keeps today's rule (A6), also from the older AresOS beside a newer one: it
            # names the other release, which goes at shutdown. A repair note still refuses it.
            if any(n[0] == s.running for n in s.repairs):
                assert update.stop == 'layout abandon', ('staged from a system with a repair note', s, update)
            else:
                assert update.state.stage == s.bundle and update.announcement == next((r for r in installed if r not in ('S', s.running)), ''), \
                    ('update must stage the bundle', s, update)

    for role, console, x11 in s.settings:
        if console != x11:
            assert (s.trial and s.trial.row == role and s.trial.finishing) or any(n[0] == role for n in s.repairs), 'half-written layout lost its owner'
            old = s.trial.old if s.trial and s.trial.row == role else next(n[1] for n in s.repairs if n[0] == role)
            booted = step(s, ('power-off' if s.stage else 'restart', role)).state
            repaired = step(booted, ('abandon', 'full'))
            assert not repaired.stop and repaired.state.keyboard(role) == (old, old), 'abandon did not restore the owning /etc'
            assert all(p in repaired.state.settings for p in s.settings if p[0] != role), 'abandon wrote another /etc'
            if role == s.running:
                attempt = step(s, ('update', 'full'))
                assert attempt.state.stage == s.stage, 'staged from a half-written /etc'
    checked = step(s, ('check', 'full'))
    if checked.stop:
        if checked.stop == 'update':
            repaired = step(checked.state, ('update', 'full'))
        else:
            assert checked.stop == 'layout', checked
            fresh = step(checked.state, ('fresh-login', 'full'))
            repaired = step(fresh.state, ('abandon', 'full'))
        assert not repaired.stop, ('check next step refuses', s, repaired)
        assert not step(repaired.state, ('check', 'full')).stop, 'check recovery did not recover'
        assert set(s.rows) <= set(repaired.state.rows), 'check recovery deleted a row'
    if s.stage or s.outcome() == 'waiting':
        for kind in ('restart', 'power-off'):
            available = (s.stage, s.running, 'S') if s.stage and kind == 'restart' else s.rows[1:] if s.stage else s.rows
            for row in available:
                restarted = step(s, (kind, row)).state
                assert not restarted.stage and restarted.outcome() != 'waiting'
    if s.trial:
        # Every trial, including interrupted finishes, can end by fresh-login abandon.
        fresh = step(s, ('fresh-login', 'full')).state
        abandoned = step(fresh, ('abandon', 'full'))
        assert not abandoned.stop and abandoned.state.trial is None, 'abandon cannot end trial'
        if s.trial.same_boot and not s.trial.fresh and not s.trial.finishing:
            for revert in (False, True):
                attempt = step(s, ('revert', 'full')).state if revert else s
                proof = step(attempt, ('proof', 'full'))
                assert not proof.stop
                finished = step(proof.state, ('finish', 'full'))
                assert not finished.stop and not finished.state.trial, 'proof/finish cannot end trial'
    for row, event in destinations(s):
        selected = step(s, event)
        assert not selected.stop, ('destination refuses', row, s, selected)
        assert selected.state.rows[0] == row and not selected.state.stage, ('destination missing', row, s)


def reduced(s):
    """A future-equivalence key; keep the representative's full evidence for each edge.

    Once a journal is in place its before-order and original running row are
    provenance: a restart cannot change the order, and a new change archives it.
    Before application, the current rows supply before. Keep the mode, word,
    phase, target, boot age AND outcome, so no journal outcome is merged.

    After a trial crosses a boot, proof/revert/finish all refuse before reading
    proof or reverted; abandon uses old/new/finishing and its saved authority.
    Notes for removed releases can never apply again: the fixed bundle only
    stages its own target, and that target can never be removed by these events.
    All live notes and every installed /etc pair remain literal, not shared.
    For reachable settings, an already-saved restoration intent is provenance:
    abandon publishes it again before writes, and a retry only restores old.
    Without an intent the original old/forward/new pairs authorize that same
    first restoration. Reverse partial pairs are reachable only with intent.
    Retain full intent evidence in representatives and actual execution checks;
    quotient only the history of which authorized pair began the restoration.
    WHETHER a restoration began is state for a trial still in its own boot: finish
    then refuses (review 2: restoration is an exclusive phase), also from the
    original login. Once the trial crossed a boot, finish refuses before that.
    """
    j, t = s.journal, s.trial
    journal = None if j is None else (j.mode, j.word, j.phase, j.target, j.same_boot, s.outcome())
    if t is None:
        trial = None
    elif t.same_boot:
        trial = t, any(n[0] == t.row for n in s.restoring)
    else:
        trial = t.row, t.old, t.new, t.finishing
    repairs = tuple(n for n in s.repairs if n[0] in s.rows)
    return s.bundle, s.rows, s.running, s.stage, journal, trial, repairs, s.settings, s.loaded
