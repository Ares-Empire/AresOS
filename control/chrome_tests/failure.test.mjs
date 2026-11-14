import test from 'node:test';
import assert from 'node:assert/strict';
import {failBrowserCase} from '../chrome/ci/failure.mjs';
import {assertComplete} from '../chrome/ci/verdicts.mjs';

test('browser failure stops with retained failing rows and incomplete verdicts that cannot qualify',()=>{
  const rows=[{name:'GROUP 1 REVIEW modified deletion keys normalized words malformed URLs and visible names',passed:false,error:'original failure'}],written=new Map(),error=Error('original failure');
  assert.throws(()=>failBrowserCase(rows,{},error,(path,value)=>written.set(path,JSON.parse(value))),value=>value===error);
  assert.deepEqual(written.get('/out/matrices.json'),rows);
  const qualification=written.get('/out/qualification-result.json');assert.equal(qualification.groups[12],false);assert.ok(Object.values(qualification.core).every(value=>value===false));assert.ok(Object.values(qualification.adapters).every(value=>value===false));
  assert.throws(()=>assertComplete(rows,qualification),/Incomplete|failing/);
});
