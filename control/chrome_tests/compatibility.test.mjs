import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

test('a failed fixture click is recorded without an unhandled rejection aborting later matrices',async()=>{
  const source=fs.readFileSync('control/chrome/ci/compatibility.mjs','utf8');
  const context=vm.createContext({execFileSync:()=> 'Ordinary browser window',key:()=>{throw Error('No picker was opened');}});
  vm.runInContext(source.slice(source.indexOf('export async function measureCompatibility('),source.indexOf('export async function withoutExtension(')).replace('export ',''),context);
  const failure=Error('Synthetic failed tool click');
  const eventually=async read=>{
    let last;
    for(let attempt=0;attempt<8;attempt++){try{const value=await read();if(value)return value;}catch(error){last=error;}}
    throw last||Error('Native picker never opened');
  };
  await assert.rejects(context.measureCompatibility({id:'fixture',fixture:{compatibility:[{id:'fixture',phase:'ready'}]},eventually,start:async()=>{throw failure;}}),error=>error===failure);
});
