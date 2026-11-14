import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {instrumentOwnerGuard,assertOwnerOverlap} from '../chrome/ci/owner-evidence.mjs';
test('recheck owner instrumentation compiles and only observes private mark transitions',()=>{
  const source=fs.readFileSync('control/chrome/extension/guard.js','utf8'),instrumented=instrumentOwnerGuard(source);
  new vm.Script(instrumented);assert.match(instrumented,/traceOwner\('held',id\)/);
  assert.throws(()=>instrumentOwnerGuard(source.replace('owner.consumed=true;return true;','')),/AssertionError/);
});
test('recheck owner evidence requires a real timer inside independently timestamped mark endpoints',()=>{
  const id='overlap',arrival=(key,time,body='')=>({url:'/receive?case='+key,time,body});
  const arrivals=[...['owner-enter','owner-submit','timer-fire'].map((phase,index)=>arrival('trace-'+id,12+index,JSON.stringify({phase,time:2+index}))),arrival('owner-'+id,3)];
  const traces=[{id,phase:'set',token:7,time:1,key:'Enter',input:'keydown',in_flight:false},{id,phase:'pass',token:7,time:2.5,key:'Enter',input:'keydown',consumed:true,in_flight:false},{id,phase:'held',token:7,time:4,key:'Enter',in_flight:false},{id,phase:'clear',token:7,time:5}];
  assert.equal(assertOwnerOverlap(id,arrivals,traces).mark.held.token,7);
  const implicit=[traces[0],{id,phase:'set',token:8,time:2.2,input:'click',key:null,in_flight:false},{id,phase:'pass',token:8,time:2.5,input:'click',key:null,consumed:true,in_flight:false},{id,phase:'set',token:9,time:3.3,key:'Enter',input:'keyup',in_flight:false},{id,phase:'held',token:9,time:4.2,key:'Enter',input:'keyup',in_flight:false},{id,phase:'clear',token:9,time:5}];
  assert.equal(assertOwnerOverlap(id,arrivals,implicit).owner_pass.input,'click');
  // Keep temporal rejection independent of the earlier native admission proof.
  for(const change of [
    rows=>rows.map(row=>row.phase==='set'&&row.token===9?{...row,time:4.1}:row),
    rows=>rows.filter(row=>!(row.phase==='set'&&row.token===7)),
    rows=>rows.filter(row=>!(row.phase==='set'&&row.token===8)),
    rows=>rows.map(row=>row.phase==='set'&&row.token===8?{...row,token:88}:row),
  ])assert.throws(()=>assertOwnerOverlap(id,arrivals,change(implicit)));
  for(const mutation of [rows=>rows.map(row=>row.phase==='held'?{...row,key:'Space'}:row),rows=>rows.filter(row=>row.phase!=='set'||row.key!=='Enter'),rows=>rows.map(row=>row.phase==='pass'?{...row,consumed:false}:row),rows=>rows.map(row=>row.phase==='pass'?{...row,time:4.5}:row),rows=>rows.filter(row=>row.phase!=='pass'),rows=>rows.filter(row=>row.phase!=='held'),rows=>rows.map(row=>row.phase==='held'?{...row,in_flight:true}:row),rows=>rows.map(row=>row.phase==='set'?{...row,time:4.5}:row),rows=>rows.filter(row=>row.phase!=='clear')])assert.throws(()=>assertOwnerOverlap(id,arrivals,mutation(traces)));
});
