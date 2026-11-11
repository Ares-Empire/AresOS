// Read retained Linux artifacts only. This program starts no browser.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {assertComplete} from '../../control/chrome/ci/verdicts.mjs';
import {assertOwnerOverlap} from '../../control/chrome/ci/owner-evidence.mjs';
import {jsonLines,completeIngressStream,containsText,digestFile} from './audit-streams.mjs';

const walk=directory=>fs.readdirSync(directory,{withFileTypes:true}).flatMap(entry=>entry.isDirectory()?walk(path.join(directory,entry.name)):[path.join(directory,entry.name)]);
const read=file=>fs.readFileSync(file,'utf8');
const json=file=>JSON.parse(read(file));
const caseId=row=>new URL(row.url,'http://fixture.test').searchParams.get('case');
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
  const rawIdentities=new Set(),counts=new Map(),ownerRows=[],ownerTraces=[];
  for await(const row of jsonLines(path.join(folder,'receiver.jsonl'))){rawIdentities.add(JSON.stringify(row));const id=caseId(row);counts.set(id,(counts.get(id)||0)+1);if(['owner-recheck-owner-overlap','trace-recheck-owner-overlap'].includes(id))ownerRows.push(row);}
  const receiverAudits=[];
  for(const name of ['page-receiver.jsonl','adapters-receiver.jsonl']){
    const sequences=new Map();let snapshots=0;
    for await(const row of jsonLines(path.join(folder,name))){
      snapshots++;
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
    receiverAudits.push({file:name,snapshots,complete_0_1_1_sequences:sequences.size,independent_arrivals_match:true});
  }
  let ingress=0,nullRows=0,events=0,getters=0;const getterKinds=new Map();
  for await(const row of completeIngressStream(path.join(folder,'browser-boundary.jsonl'))){
    ingress++;if(row===null)nullRows++;if(row?.owner_trace)ownerTraces.push(row.owner_trace);
    if(row?.protocol_event){events++;assert.equal(['Runtime.consoleAPICalled','Runtime.exceptionThrown'].includes(row.protocol_event.method),false);}
    if(row?.reader_ingress){getters++;const kind=row.reader_ingress.kind;getterKinds.set(kind,(getterKinds.get(kind)||0)+1);}
    assert(!JSON.stringify(row).includes('SENTINEL_PRIVATE_PASSWORD_20'),'Password sentinel reached browser-boundary.jsonl');
  }
  assert(events>0&&getters>0,'Missing protocol or sensitive-getter coverage');
  const ownerOverlap=assertOwnerOverlap('recheck-owner-overlap',ownerRows,ownerTraces);
  assert.deepEqual(ownerOverlap,json(path.join(folder,'owner-overlap.json')),'owner overlap must match raw private observations and independent receiver');
  for(const name of ['tool.jsonl','service.txt'])assert(!await containsText(path.join(folder,name),'SENTINEL_PRIVATE_PASSWORD_20'),`Password sentinel reached ${name}`);
  const python=read(path.join(folder,'python.txt')),py=/^Ran (\d+) tests in ([0-9.]+)s$/m.exec(python);
  assert(py&&/^OK$/m.test(python),'Full Python suite missing or failed');
  assert.equal(Number(py[1]),222);
  const node=Object.fromEntries([...read(path.join(folder,'node.txt')).matchAll(/^(?:# |ℹ )?(tests|pass|fail|cancelled|skipped)\s+(\d+)/gm)].map(match=>[match[1],Number(match[2])]));
  assert.deepEqual(node,{tests:251,pass:251,fail:0,cancelled:0,skipped:0});
  const hashes={};for(const name of ['browser.txt','matrices.json','receiver.jsonl','page-receiver.jsonl','adapters-receiver.jsonl','browser-boundary.jsonl','tool.jsonl','service.txt','python.txt','node.txt','owner-overlap.json'])hashes[name]=await digestFile(path.join(folder,name));
  results.push({artifact:path.basename(folder),chrome:read(path.join(folder,'chrome-version.txt')).trim(),named_passes:rows.length,test_index:testIndex,verdicts:verdict,receiver_audit:receiverAudits,owner_overlap:ownerOverlap,password_audit:{rows:ingress,null_rows:nullRows,protocol_events:events,forbidden_runtime_value_events:0,sensitive_getters:getters,getter_kinds:Object.fromEntries(getterKinds),password_sentinel_absent:true},python:{tests:Number(py[1]),seconds:Number(py[2])},node,sha256:hashes});
}
assert(results.length>0,'No artifacts found');
console.log(JSON.stringify(results,null,2));
