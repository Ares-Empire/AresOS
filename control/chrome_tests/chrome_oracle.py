"""Test-owned decoder and owner-warning rules. Deliberately imports no production code."""
import json
from pathlib import Path
import sqlite3


def committed(state_dir, evidence_dir):
    records={};commits=set()
    for line in (Path(evidence_dir)/'operations.jsonl').read_text().splitlines():
        value=json.loads(line)
        if 'commit' in value:commits.add(value['commit'])
        else:records[value['seq']]=value
    connection=sqlite3.connect(Path(state_dir)/'control.sqlite')
    try:
        events={seq:json.loads(value) for seq,value in connection.execute('SELECT seq,value FROM events')}
    finally:connection.close()
    rows={}
    for seq in sorted(commits):
        changes=events.get(seq,{}).get('set',{})
        # Chrome updates are independently retained even when the prepared SQLite event was lost.
        projected=records[seq].get('chrome',{})
        for key,value in projected.items():
            if key in changes:assert changes[key]==value, 'Independent Chrome update disagrees with its committed full event'
        for key,value in {**changes,**projected}.items():
            if value is None:rows.pop(key,None)
            else:rows[key]=value
    return rows


def warnings(rows):
    expected={value['id'] for key,value in rows.items() if key.startswith('notice:') and value.get('app')=='chrome' and not value.get('ack')}
    for key,value in rows.items():
        if not isinstance(value,dict) or value.get('app')!='chrome':continue
        if key.startswith('op:') and value['state']=='failed' and value.get('notice') and not value.get('ack'):
            expected.add(value['id'])
        if key.startswith('op:') and value['state'] in {'submitting','unknown','partial'}:
            identifier='recovery-'+value['id']
        elif key.startswith('intent:') and value.get('state') in {'started','unknown'}:
            identifier=value['id']
        else:continue
        if 'notice:'+identifier not in rows:expected.add(identifier)
    return expected
