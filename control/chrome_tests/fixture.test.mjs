// Plain HTTP fixture test. It starts no browser and writes no output/profile.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {fixtures} from '../chrome/ci/fixture.mjs';
import {popupPage} from '../chrome/ci/popups.mjs';

test('popup fixtures compile for clean dirty and POST opener flows',()=>{
  for(const kind of ['popup-opener','popup-child'])for(const mode of ['clean','dirty','post']){
    const page=popupPage(new URL('http://fixture.test/?case='+kind+'&id=fixture&mode='+mode));
    new vm.Script(page.script);assert.ok(page.body);
  }
});

test('favicon and unrelated requests preserve mutation channels; applied mutations require acknowledgement',async()=>{
  const fixture=await fixtures({port:0,secondPort:0});const base='http://127.0.0.1:'+fixture.port;
  let reader;
  try{
    await(await fetch(base+'/?case=binding&id=mutator')).text();
    const channel=await fetch(base+'/events?id=mutator');reader=channel.body.getReader();await reader.read();
    assert.equal((await fetch(base+'/favicon.ico')).status,204);
    assert.equal((await fetch(base+'/.well-known/irrelevant')).status,404);
    let settled=false;const pending=fixture.mutate('mutator','label').then(()=>{settled=true;});
    const message=Buffer.from((await reader.read()).value).toString();const mutation=JSON.parse(message.match(/data: (.+)/)[1]);
    await Promise.resolve();assert.equal(settled,false,'writing an SSE is not proof its mutation ran');
    await fetch(base+'/mutation-ack?nonce='+mutation.nonce);await pending;assert.equal(settled,true);
  }finally{await reader?.cancel();fixture.close();}
});
