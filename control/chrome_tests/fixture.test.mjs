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


test('popup state probe uses the receiver mutation protocol and preserves document identity',async()=>{
  let probe;const sent=[];const input={value:'Draft kept'};
  const page=popupPage(new URL('http://popup.test/?case=popup-child&id=probe&mode=clean'));
  vm.runInNewContext(page.script,{
    document:{title:'',querySelector:selector=>selector==='input'?input:{}},
    HTMLFormElement:{prototype:{submit(){throw Error('probe must never submit')}}},Date:{now:()=>123},Math:{random:()=>0.5},
    EventSource:class{set onmessage(value){probe=value;}},fetch:(...args)=>{sent.push(args);return Promise.resolve();},
    opener:{closed:false},window:{name:'same-popup'},outerWidth:620,outerHeight:480,
  });
  for(const nonce of ['1','2'])await probe({data:JSON.stringify({change:'popup-probe',nonce})});
  const states=sent.filter(([url])=>url==='/receive?case=state-probe').map(([,options])=>JSON.parse(options.body));
  assert.equal(states.length,2);assert.deepEqual(states[0],states[1]);assert.equal(states[0].document,'123-0.5');assert.equal(states[0].draft,'Draft kept');assert.equal(states[0].opener,true);
  assert.ok(sent.some(([url])=>url==='/mutation-ack?nonce=1'));assert.ok(sent.some(([url])=>url==='/mutation-ack?nonce=2'));
});

test('P31 first script captures natives inside head and excluded GET carries the receiver identity',async()=>{
  const fixture=await fixtures({port:0,secondPort:0}),base='http://127.0.0.1:'+fixture.port;
  try{
    const first=await(await fetch(base+'/?case=preload-origin&id=early')).text();
    assert.ok(first.indexOf('firstScriptSubmit=')<first.indexOf('</head>'));assert.ok(first.indexOf('firstScriptSubmit=')<first.indexOf('<body>'));
    const excluded=await(await fetch(base+'/?case=excluded-form&id=excluded-get&method=get')).text();assert.match(excluded,/<input type="hidden" name="case" value="excluded-get">/);
  }finally{fixture.close();}
});

test('review fixtures compile without starting a browser',async()=>{
  const {reviewPage}=await import('../chrome/ci/review-fixtures.mjs');
  const {passwordPage}=await import('../chrome/ci/password-fixtures.mjs');
  for(const mode of ['inline-hold','new-frame','new-frame-inner','shadow','label','binding','confirmation','file','rich','title','notice','owner-mark','independent-dialog'])for(const variant of ['blank','srcdoc','borrowed','other-form','other-submitter','closed-event']){
    const page=reviewPage(new URL('http://fixture.test/?mode='+mode+'&variant='+variant+'&id=fixture'));new vm.Script(page.script);assert.ok(page.body);
  }
  for(const cross of [false,true])new vm.Script(passwordPage(cross).script);
});
