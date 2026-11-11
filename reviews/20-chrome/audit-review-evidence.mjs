// Read retained Linux artifacts only. This program starts no browser.
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {assertComplete} from '../../control/chrome/ci/verdicts.mjs';
import {completeIngress,protocolEvents} from '../../control/chrome/ci/ingress-scan.mjs';

const walk=directory=>fs.readdirSync(directory,{withFileTypes:true}).flatMap(entry=>entry.isDirectory()?walk(path.join(directory,entry.name)):[path.join(directory,entry.name)]);
const read=file=>fs.readFileSync(file,'utf8');
const json=file=>JSON.parse(read(file));
const lines=file=>read(file).split('\n').filter(Boolean).map(line=>JSON.parse(line));
const caseId=row=>new URL(row.url,'http://fixture.test').searchParams.get('case');
const digest=value=>crypto.createHash('sha256').update(value).digest('hex');
const results=[];
for(const root of process.argv.slice(2))for(const matrix of walk(root).filter(file=>path.basename(file)==='matrices.json')){
  const folder=path.dirname(matrix),rows=json(matrix),verdict=json(path.join(folder,'qualification-result.json'));
  assertComplete(rows,verdict);
  const browser=read(path.join(folder,'browser.txt')).split('\n');
  const testIndex=rows.map(row=>{
    const matches=browser.flatMap((line,index)=>line===row.name+' PASS'?[index+1]:[]);
    assert.equal(matches.length,1,row.name);
    return {name:row.name,line:matches[0]};
  });
  const raw=lines(path.join(folder,'receiver.jsonl')),rawIdentities=new Set(raw.map(row=>JSON.stringify(row)));
  const counts=new Map();
  for(const row of raw){const id=caseId(row);counts.set(id,(counts.get(id)||0)+1);}
  const receiverAudits=[];
  for(const name of ['page-receiver.jsonl','adapters-receiver.jsonl']){
    const snapshots=lines(path.join(folder,name)),sequences=new Map();
    for(const row of snapshots){
      assert.equal(row.count,row.arrivals.length,`${name}: ${row.id} ${row.phase}`);
      for(const arrival of row.arrivals){
        assert.equal(caseId(arrival),row.id);
        assert(rawIdentities.has(JSON.stringify(arrival)),`${row.id}: arrival missing from independent receiver`);
      }
      if(['before approval','after approval','after repeat'].includes(row.phase)){
        if(!sequences.has(row.id))sequences.set(row.id,[]);
        sequences.get(row.id).push([row.phase,row.count]);
      }
    }
    for(const [id,phases]of sequences){
      assert.deepEqual(phases,[['before approval',0],['after approval',1],['after repeat',1]],id);
      assert.equal(counts.get(id),1,`${id}: independent final receiver count`);
    }
    assert(sequences.size>0,`${name}: missing approval evidence`);
    receiverAudits.push({file:name,snapshots:snapshots.length,complete_0_1_1_sequences:sequences.size,independent_arrivals_match:true});
  }
  const ingress=completeIngress(read(path.join(folder,'browser-boundary.jsonl'))),events=protocolEvents(ingress),getters=ingress.filter(row=>row?.reader_ingress);
  assert(events.length>0&&getters.length>0,'Missing protocol or sensitive-getter coverage');
  assert.equal(events.filter(event=>['Runtime.consoleAPICalled','Runtime.exceptionThrown'].includes(event.method)).length,0);
  for(const [name,value]of [['browser-boundary.jsonl',JSON.stringify(ingress)],['tool.jsonl',read(path.join(folder,'tool.jsonl'))],['service.txt',read(path.join(folder,'service.txt'))]])assert(!value.includes('SENTINEL_PRIVATE_PASSWORD_20'),`Password sentinel reached ${name}`);
  const python=read(path.join(folder,'python.txt')),py=/^Ran (\d+) tests in ([0-9.]+)s$/m.exec(python);
  assert(py&&/^OK$/m.test(python),'Full Python suite missing or failed');
  assert.equal(Number(py[1]),220);
  const node=Object.fromEntries([...read(path.join(folder,'node.txt')).matchAll(/^(?:# |ℹ )?(tests|pass|fail|cancelled|skipped)\s+(\d+)/gm)].map(match=>[match[1],Number(match[2])]));
  assert.deepEqual(node,{tests:234,pass:234,fail:0,cancelled:0,skipped:0});
  const hashes=Object.fromEntries(['browser.txt','matrices.json','receiver.jsonl','page-receiver.jsonl','adapters-receiver.jsonl','browser-boundary.jsonl','tool.jsonl','service.txt','python.txt','node.txt'].map(name=>[name,digest(fs.readFileSync(path.join(folder,name)))]));
  results.push({artifact:path.basename(folder),chrome:read(path.join(folder,'chrome-version.txt')).trim(),named_passes:rows.length,test_index:testIndex,verdicts:verdict,receiver_audit:receiverAudits,password_audit:{rows:ingress.length,null_rows:ingress.filter(row=>row===null).length,protocol_events:events.length,forbidden_runtime_value_events:0,sensitive_getters:getters.length,getter_kinds:Object.fromEntries([...new Set(getters.map(row=>row.reader_ingress.kind))].map(kind=>[kind,getters.filter(row=>row.reader_ingress.kind===kind).length])),password_sentinel_absent:true},python:{tests:Number(py[1]),seconds:Number(py[2])},node,sha256:hashes});
}
assert(results.length>0,'No artifacts found');
console.log(JSON.stringify(results,null,2));
