"""Independent reference rules for 22c B2. No owner-tool or fake-host imports.

The ledger records events that happened, including interrupted commands. Boot age
and trial session are equivalence classes, never literal ids. Profiles stay literal:
all three supported console/X11 profiles are explored, including mixed settings.
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
            for rows in (('13', 'S'), ('27', '13', 'S')) for bundle in ('27', '28')]


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
        if t:
            if not t.fresh:
                return result(stop='fresh physical')
            if t.row == s.running:
                s = s.setting(s.running, t.old, t.old)
            elif t.finishing:
                s = replace(s, repairs=tuple(sorted((*s.repairs, (t.row, t.old, t.new)))))
            s = replace(s, trial=None, loaded=s.keyboard()[0])
        for role, old, new in mine:
            s = s.setting(role, old, old)
        s = replace(s, repairs=tuple(n for n in s.repairs if n[0] != s.running), loaded=s.keyboard()[0])
        s, confirmed = title(s)
        return result(s, confirm=confirmed)

    if word in ('proof', 'revert', 'finish'):
        if not t:
            return result(stop='Missing private layout-pending')
        if not t.same_boot:
            return result(stop='crossed a reboot')
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

    assert word in ('update', 'previous', 'rollback', 'keep-stock'), word
    if word == 'rollback' and s.running == 'S':
        return result(stop='keep-stock')
    if word == 'keep-stock' and s.running != 'S':
        return result(stop='rollback')
    releases = [r for r in s.rows if r != 'S' and r != s.stage]
    if word == 'previous' and len(releases) != 2:
        return result(stop='Only one AresOS')
    stage = word == 'update' and s.bundle not in releases and s.running != 'S' and s.rows[0] == s.running
    target = s.bundle if stage else max(releases) if word == 'update' else min(releases) if word == 'previous' else 'S'
    if outcome == 'complete':
        s = replace(s, journal=replace(j, phase='recorded'))
        return result(s, cut=phase == 'record')
    if not stage and s.rows[0] == target:
        return result()
    if t:
        return result(stop='Layout trial')
    if outcome == 'waiting':
        return result(stop='restart first')
    if s.stage:
        return result(stop='staged')
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


def events(s):
    for word in ('check', 'title', 'records', 'reboot', 'update', 'previous', 'rollback', 'keep-stock', 'abandon'):
        yield word, 'full'
    for word in ('update', 'previous', 'rollback', 'keep-stock'):
        for phase in ('intent', 'primitive', 'record'):
            # A refused/no-op command never reaches a phase to cut. Its full event
            # above still runs; omit only these physically nonexistent cut points.
            if transition(s, (word, phase)).cut:
                yield word, phase
    for profile in PROFILES:
        yield 'begin', profile
    if s.trial:
        if not s.trial.fresh:
            yield 'fresh-login', 'full'
        yield 'proof', 'full'
        yield 'revert', 'full'
        for phase in ('intent', 'console', 'persistent', 'full'):
            if phase == 'full' or transition(s, ('finish', phase)).cut:
                yield 'finish', phase
    for kind in ('restart', 'power-off'):
        rows = (s.stage, s.running, 'S') if s.stage and kind == 'restart' else s.rows[1:] if s.stage else s.rows
        for choice in ('default', *rows):
            yield kind, choice


def invariants(s):
    """Return the unsatisfiable destination clause's counterexamples; assert the rest.

    A4(b) and A6 explicitly stage over the running older AresOS. B2 cannot also
    promise a command selecting the newer installed AresOS in that state. The
    caller reports this as a blocking plan gap, never as a proved invariant.
    """
    for role, console, x11 in s.settings:
        if console != x11:
            assert (s.trial and s.trial.row == role and s.trial.finishing) or any(n[0] == role for n in s.repairs), 'half-written layout lost its owner'
            if role == s.running:
                attempt = transition(s, ('update', 'full'))
                assert attempt.state.stage == s.stage, 'staged from a half-written /etc'
    checked = transition(s, ('check', 'full'))
    if checked.stop:
        if checked.stop == 'update':
            repaired = transition(checked.state, ('update', 'full'))
        else:
            assert checked.stop == 'layout', checked
            fresh = transition(checked.state, ('fresh-login', 'full'))
            repaired = transition(fresh.state, ('abandon', 'full'))
        assert not repaired.stop, ('check next step refuses', s, repaired)
        assert not transition(repaired.state, ('check', 'full')).stop, 'check recovery did not recover'
        assert set(s.rows) <= set(repaired.state.rows), 'check recovery deleted a row'
    if s.stage or s.outcome() == 'waiting':
        for kind in ('restart', 'power-off'):
            available = (s.stage, s.running, 'S') if s.stage and kind == 'restart' else s.rows[1:] if s.stage else s.rows
            for row in available:
                restarted = transition(s, (kind, row)).state
                assert not restarted.stage and restarted.outcome() != 'waiting'
    if s.trial:
        # Every trial, including interrupted finishes, can end by fresh-login abandon.
        fresh = transition(s, ('fresh-login', 'full')).state
        abandoned = transition(fresh, ('abandon', 'full'))
        assert not abandoned.stop and abandoned.state.trial is None, 'abandon cannot end trial'
        if s.trial.same_boot and not s.trial.fresh and not s.trial.finishing:
            for revert in (False, True):
                attempt = transition(s, ('revert', 'full')).state if revert else s
                proof = transition(attempt, ('proof', 'full'))
                assert not proof.stop
                finished = transition(proof.state, ('finish', 'full'))
                assert not finished.stop and not finished.state.trial, 'proof/finish cannot end trial'
    missing = []
    # A5's same-boot staging intent still waits for update to continue, even
    # before its primitive. Keep it distinct from a restart waiting on an
    # applied selection; neither is a resting state for destination commands.
    if not s.stage and s.outcome() not in ('waiting', 'retry', 'complete') and not s.trial:
        releases = sorted(r for r in s.rows if r != 'S')
        for row in s.rows:
            if row == s.rows[0]:
                continue  # already selected: no change is needed
            word = ('keep-stock' if s.running == 'S' else 'rollback') if row == 'S' else 'update' if row == releases[-1] else 'previous'
            selected = transition(s, (word, 'full'))
            if selected.stop or selected.state.rows[0] != row:
                missing.append(row)
    return tuple(missing)
