"""Read-only probe: which deployment lists do today's pure shape checks accept?
Imports the main checkout's test model (machine/release_row/stock_row) and owner.py; runs no test, writes nothing."""
import sys, itertools
sys.dont_write_bytecode = True
sys.path.insert(0, '/var/home/ares/AresOS/os/tests')
import test_owner_update as t
owner = t.owner
R13, R21 = t.R13, t.R21
refs = [r['reference'] for r in t.H21]
saved = t.prepared()

def verdict(fn):
    try:
        fn(); return 'accepted'
    except owner.Stop as e:
        return 'STOP: ' + str(e)

def name(rows):
    out = []
    for r in rows:
        d = r['container-image-reference-digest']
        n = 'S' if d == owner.BASE else ('A2' if d == R21.split('@')[1] else 'A1')
        out.append(n + ('*' if r['booted'] else ''))
    return '[' + ', '.join(out) + ']'

print('== pair (A = R21 known), every order and booted ==')
for order in itertools.permutations(['A', 'S']):
    for booted in order:
        rows = [t.release_row(R21, booted=(booted == 'A')) if x == 'A' else t.stock_row(booted == 'S') for x in order]
        st = t.machine(rows)
        print(name(rows), 'queued=%s' % st['bootc']['status']['rollbackQueued'])
        print('   qualified_state :', verdict(lambda: owner.qualified_state(st, saved, R21, refs)))
        print('   rollback preflt :', verdict(lambda: owner.preflight_recovery(st, [], saved, R21, False, refs)))
        print('   keep-stock prefl:', verdict(lambda: owner.preflight_recovery(st, [], saved, R21, True, refs)))

print('== triple (A1 = R13, A2 = R21), every order and booted ==')
for order in itertools.permutations(['A2', 'A1', 'S']):
    for booted in order:
        rows = []
        for x in order:
            rows.append(t.stock_row(booted == 'S') if x == 'S' else t.release_row(R21 if x == 'A2' else R13, booted=(booted == x)))
        st = t.machine(rows)
        print(name(rows), 'queued=%s' % st['bootc']['status']['rollbackQueued'])
        print('   qualified_state :', verdict(lambda: owner.qualified_state(st, saved, R21, refs)))
        print('   rollback preflt :', verdict(lambda: owner.preflight_recovery(st, [], saved, R21, False, refs)))
        print('   keep-stock prefl:', verdict(lambda: owner.preflight_recovery(st, [], saved, R21, True, refs)))
