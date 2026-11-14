import {dismissNativePicker} from '../chrome/ci/compatibility.mjs';
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

test('native picker dismissal waits for chooser cancellation and Chrome focus',async()=>{
  const visited=[],calls=[];let active='picker';
  const exec=(command,args)=>{calls.push(args);if(args[0]==='getactivewindow')return active;if(args[0]==='search')return 'picker\nbrowser\n';return '';};
  await dismissNativePicker({picker:{window:'picker'},exec,eventually:async check=>{
    for(const window of ['picker','unrelated','browser']){active=window;visited.push(window);if(await check())break;}
  }});
  assert.deepEqual(visited,['picker','unrelated','browser']);assert.deepEqual(calls[0],['key','--clearmodifiers','Escape']);
  assert.equal(calls.filter(args=>args[0]==='key').length,1,'dismissal is not replayed');
});
