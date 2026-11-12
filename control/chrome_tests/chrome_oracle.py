"""Scenario/receiver oracle. Its decoder and rules import no production code.

Only the independent format-2 journal supplies local commit facts. SQLite is
explicitly excluded: its readable rows can be ahead of or behind those commits.
"""
import hashlib
import json
from pathlib import Path

_OPEN=open


def identity(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()


def history(evidence_dir):
    rows={};ever={};acks=set();records=[];pending=None
    with _OPEN(Path(evidence_dir)/'operations.jsonl','rb') as stream:
        for line in stream:
            if not line.endswith(b'\n'):break
            value=json.loads(line)
            if 'commit' not in value:
                pending=value;continue
            assert pending is not None and value=={'commit':pending['seq'],'hash':pending['hash']}
            assert pending['seq']==len(records)+1
            assert pending['previous']==(records[-1]['hash'] if records else '')
            assert identity({key:item for key,item in pending.items() if key!='hash'})==pending['hash']
            records.append(pending)
            for key,item in pending.get('chrome',{}).items():
                if item is None:rows.pop(key,None)
                else:
                    if isinstance(item,dict) and item.get('ack'):acks.add(key)
                    item=dict(item) if isinstance(item,dict) else item
                    if key in acks and isinstance(item,dict):item['ack']=True
                    rows[key]=item;ever[key]=item
            pending=None
    return {'rows':rows,'ever':ever,'acks':acks,'records':records}


def committed(state_dir,evidence_dir):
    return history(evidence_dir)['rows']


def expectations(script,receiver,record):
    """Semantic triggers come from calls and receiver observations, not notices.

    Local commits determine whether a check/result/ack actually committed and
    provide opaque occurrence identities. A notice row cannot create its own
    expected warning; extra warnings fail exactly like missing ones.
    """
    rows=record['rows'];ever=record['ever'];expected=set();pending={}
    observed_steps={identity([call['session'],call['tab'],call['step']]):call
                    for call in script if call['kind']=='step'}
    for source_id,call in observed_steps.items():
        key='intent:chrome:'+source_id;source=ever.get(key)
        if source is None:continue
        if key in rows and source['state'] in {'started','unknown'}:
            expected.add(source_id);continue
        # A stopped activation is a warning even without a receiver arrival.
        # A stale native submission is clean; an uncertain activation never is.
        if call['step']['kind'] not in {'activation','activation_unknown'}:continue
        if source.get('result')=='stale' and call['step']['kind']!='activation_unknown':continue
        occurrence=source.get('warning_checks',{}).get('page_activation',{}).get('occurrence_id',source_id)
        assert 'notice:'+occurrence in ever,'A check closed without its scenario-required warning result'
        if 'notice:'+occurrence not in record['acks']:expected.add(occurrence)
    for key,operation in rows.items():
        if not key.startswith('op:'):continue
        state=operation['state'];identifier=operation['id']
        if state in {'reserved','submitting','unknown','partial'}:
            pending[identifier]=state
        if state=='failed' and operation.get('notice') and not operation.get('ack'):
            assert any(call['kind'] in {'release','cancel','expiry','restore','compose_change'} for call in script),'Unexpected terminal warning in clean scenario'
            expected.add(identifier);pending[identifier]=state
        if state in {'submitting','unknown','partial'}:
            notice_key='notice:recovery-'+identifier
            if notice_key not in record['acks']:expected.add('recovery-'+identifier)
    for arrival in receiver:
        assert arrival['authorized'],'Receiver saw input without scenario authorization'
        assert arrival['committed_submitting'],'Input preceded its committed context'
    identifiers=[arrival['operation'] for arrival in receiver]
    assert len(identifiers)==len(set(identifiers)),'Receiver saw a replay'
    return {'warnings':expected,'pending':pending,
            'operations':{value['id']:value['state'] for key,value in rows.items() if key.startswith('op:')}}


def compare(expected,*,warnings,pending=None,operations=None):
    assert set(warnings)==expected['warnings'],('warning mismatch',set(warnings),expected['warnings'])
    if pending is not None:assert pending==expected['pending'],('pending mismatch',pending,expected['pending'])
    if operations is not None:assert operations==expected['operations'],('operation mismatch',operations,expected['operations'])


def compare_validity(operation,reported,live):
    payload=operation['payload'];bound=payload['binding']
    current=(operation['generation']==live['generation'] and operation['expires']>live['now']
        and payload.get('process_session')==live['process_session'] and bound.get('session')==live['session']
        and live['documents'].get(bound.get('frame'))==bound.get('document'))
    assert reported==('current' if current else 'refused'),'Cached or missing live validity'
