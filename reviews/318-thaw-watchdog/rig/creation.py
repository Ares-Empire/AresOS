#!/usr/bin/python3
"""Require the observed current product creation to match the requested home before publishing its marks."""
import pathlib
import sys


def record(rig, home, flow):
    rig = pathlib.Path(rig)
    rows = [line.split('\t') for line in (rig/'creation-marks.txt').read_text().splitlines()]
    expected = {'flat':'flat', 'nether':'Nether'}[home]
    if len(rows) != 1 or rows[0][0] != expected:
        raise ValueError(f'expected one {expected} creation, observed {rows!r}')
    nanos = int(rows[0][1])
    marks = dict(line.split() for line in (rig/'marks.txt').read_text().splitlines())
    if flow == 'menu' and 'create_start' not in marks:
        raise ValueError('the menu creation has no confirmation input mark')
    if flow not in ('automatic','menu'): raise ValueError('not an observed product creation flow')
    with (rig/'marks.txt').open('a') as output:
        output.write(f'world_create_start {nanos}\n')
        if flow == 'automatic': output.write(f'create_start {nanos}\n')


if __name__ == '__main__': record(*sys.argv[1:])
