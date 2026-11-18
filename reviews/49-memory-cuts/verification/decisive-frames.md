# Decisive frame timestamps retained for review fix 1

`decisive-frame-timestamps.json` contains only run identifiers, window-boundary timestamps and recorded frame-start timestamps in monotonic nanoseconds. It was extracted directly from the ignored raw frame logs without invoking any rig script. The matching marks were checked byte for byte against the committed `runs/<run>/marks.txt`. No table, summary, threshold or rig code changed.

The excerpts retain complete comparison windows: the first flat pair's roughly 60-second flights, and the first-creation pair's first 30 seconds after joining. Each array includes the last frame start before the window, then every frame start within it. As in `analyze.py`, a gap belongs to the window in which it ends: `start <= b < end`, with duration `(b - a) / 1_000_000` ms. Including the predecessor matters for the candidate's first startup gap, which straddles `joined`. `town_built` permits the shorter town-building window to be reconstructed from the same arrays. These are recorder start gaps, not presentation timestamps or evidence of their cause.

The decisive candidate flight gap is between **273177130322909** and **273177150270838** ns: **19.947929 ms**, rounded to **19.948 ms** in the report's observation. Its paired control maximum is **15.072578 ms**, from **272512390779477** to **272512405852055** ns. Both complete flight windows remain available around these endpoints, including ordinary neighboring frames.

| Run | Window | Gaps | Maximum, ms | > 17 ms | > 33 ms |
|---|---|---:|---:|---:|---:|
| `v1-flat-1` | flight | 7198 | 15.072578 | 0 | 0 |
| `winner-flat-1` | flight | 7194 | 19.947929 | 1 | 0 |
| `v1-create` | first 30 s | 3567 | 105.628670 | 6 | 1 |
| `winner-create` | first 30 s | 3564 | 101.973190 | 6 | 3 |
| `v1-create` | town | 287 | 32.218305 | 5 | 0 |
| `winner-create` | town | 274 | 101.973190 | 5 | 2 |

The startup gaps over 33 ms have these endpoints:

| Run | First frame start, ns | Next frame start, ns | Gap, ms |
|---|---:|---:|---:|
| `v1-create` | 271072400729148 | 271072506357818 | 105.628670 |
| `winner-create` | 271697556526914 | 271697601279112 | 44.752198 |
| `winner-create` | 271698356519602 | 271698458492792 | 101.973190 |
| `winner-create` | 271700059376318 | 271700136243529 | 76.867211 |

The control's 105.6 ms gap ends after `town_built=271072418103108`; the candidate's 76.9 ms gap likewise ends after `town_built=271700114338665`. The candidate's other two > 33 ms gaps end within its town window. This preserves both the extra startup tail counts and the report's distinction between whole-startup and town maxima.

This read-only command independently checks the retained timestamps against the committed marks and summary frame counts, maxima and threshold counts. It neither imports nor runs any rig script:

```bash
python3 - <<'PY'
import json
from pathlib import Path

root = Path('reviews/49-memory-cuts')
data = json.loads((root / 'verification/decisive-frame-timestamps.json').read_text())
for run, record in data.items():
    marks = dict((label, int(ns)) for label, ns in
                 (line.split() for line in (root / 'runs' / run / 'marks.txt').read_text().splitlines()))
    saved = record['marks_ns']
    for label, ns in saved.items():
        assert ns == (marks['joined'] + 30 * 10**9 if label == 'first_30s_end' else marks[label])
    frames = record['frame_start_ns']
    assert all(a < b for a, b in zip(frames, frames[1:]))
    if 'flight_start' in saved:
        windows = [('flight', saved['flight_start'], saved['flight_end'])]
    else:
        windows = [('first_30s', saved['joined'], saved['first_30s_end']),
                   ('town', saved['joined'], saved['town_built'])]
    summary = json.loads((root / 'runs' / run / 'summary.json').read_text())
    for label, start, end in windows:
        assert frames[0] < start <= frames[1]
        gaps = [(b - a) / 1e6 for a, b in zip(frames, frames[1:]) if start <= b < end]
        expected = summary['windows'][label]
        assert len(gaps) == expected['frames']
        assert round(max(gaps), 1) == expected['max_ms']
        counts = [sum(g > threshold for g in gaps) for threshold in (17, 33, 50, 100)]
        assert counts == [expected[f'over_{threshold}ms'] for threshold in (17, 33, 50, 100)]
        print(f'{run} {label}: {len(gaps)} gaps, max {max(gaps):.6f} ms, >17/33/50/100 {counts}')
candidate = data['winner-flat-1']['frame_start_ns']
assert (273177130322909, 273177150270838) in list(zip(candidate, candidate[1:]))
print('Decisive flight endpoints and all six comparison windows match.')
PY
```

These excerpts make the named comparisons independently reconstructable. Other raw frame windows remain local; the excerpts do not assign a cause to either discrepancy or qualify the arena cap for release.
