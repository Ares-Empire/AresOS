import test from 'node:test';
import assert from 'node:assert/strict';
import {recordCheck,writePartialResults,assertChecksPassed,pendingCheck} from '../chrome/ci/failure.mjs';
import {assertComplete} from '../chrome/ci/verdicts.mjs';

test('a shard records later passes and failures and rejects their full inventory at the end',async()=>{
  const rows=[],written=new Map(),write=(path,value)=>written.set(path,JSON.parse(value));
  const first='GROUP 1 REVIEW modified deletion keys normalized words malformed URLs and visible names';
  await recordCheck(rows,first,()=>{throw Error('first failure');});
  writePartialResults(rows,{},write);
  assert.deepEqual(written.get('/out/matrices.json'),rows);
  const qualification=written.get('/out/qualification-result.json');assert.equal(qualification.groups[12],false);assert.ok(Object.values(qualification.core).every(value=>value===false));assert.ok(Object.values(qualification.adapters).every(value=>value===false));
  assert.throws(()=>assertComplete(rows,qualification),/Incomplete|failing/);
  await recordCheck(rows,'later pass',async()=>{});
  await recordCheck(rows,'later failure',async()=>{
    const input=pendingCheck(Promise.reject(Error('input refused')));
    await new Promise(resolve=>setImmediate(resolve));
    await input;
  });
  assert.deepEqual(rows.map(row=>row.passed),[false,true,false]);
  assert.throws(()=>assertChecksPassed(rows),error=>{
    assert.ok(error instanceof AggregateError);
    assert.equal(error.message,'Failed browser checks (2):\n'+first+'\nlater failure');
    assert.match(error.errors[0].message,/first failure/);
    assert.match(error.errors[1].message,/input refused/);
    return true;
  });
  assert.doesNotThrow(()=>assertChecksPassed([rows[1]]));
});
