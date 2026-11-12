// Plain HTTP fixture test. It starts no browser and writes no output/profile.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
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
    assert.ok(first.indexOf('firstScriptSubmit=')>=0,'capture must exist');assert.ok(first.indexOf('firstScriptSubmit=')<first.indexOf('</head>'));assert.ok(first.indexOf('firstScriptSubmit=')<first.indexOf('<body>'));
    const excluded=await(await fetch(base+'/?case=excluded-form&id=excluded-get&method=get')).text();assert.match(excluded,/<input type="hidden" name="case" value="excluded-get">/);
  }finally{fixture.close();}
});

test('review fixtures compile without starting a browser',async()=>{
  const {reviewPage}=await import('../chrome/ci/review-fixtures.mjs');
  const {passwordPage}=await import('../chrome/ci/password-fixtures.mjs');
  for(const mode of ['quantity','ordinary-search','compose-key','search-label','owner-overlap','shadow-binding','shadow-fallback','inline-editor','owner-file','native-dialog','inline-dialog','preexisting-dialog','borrowed-dialog','inline-hold','new-frame','new-frame-inner','shadow','label','binding','confirmation','file','rich','title','notice','owner-mark','independent-dialog'])for(const variant of ['editable-native','editable-aria','blank','srcdoc','borrowed','conversion-message','conversion-default','changed-dialog','other-form','other-submitter','closed-event','form','submit','submit-send','li-open','li-closed','row-open','row-closed','slot-li-open','slot-li-closed','slot-row-open','slot-row-closed']){
    const page=reviewPage(new URL('http://fixture.test/?mode='+mode+'&variant='+variant+'&id=fixture'));new vm.Script(page.script);assert.ok(page.body);
  }
  for(const cross of [false,true])new vm.Script(passwordPage(cross).script);
});

test('review pages reach the HTTP response without falling through to the default 404',async()=>{
  const fixture=await fixtures({port:0,secondPort:0}),base='http://127.0.0.1:'+fixture.port;
  try{
    for(const [mode,expected]of [['inline-hold','Continue'],['binding','Delete'],['independent-dialog','reviewChange']]){
      const response=await fetch(base+'/?case=review-page&mode='+mode+'&variant=listitem&id=review-http');assert.equal(response.status,200);assert.ok((await response.text()).includes(expected));
    }
  }finally{fixture.close();}
});

test('combined S12 native-dialog review fixtures consume only untrusted dialog data',async()=>{
  const source=fs.readFileSync('control/chrome/ci/review-matrices.mjs','utf8');
  const context=vm.createContext({assert,URL,URLSearchParams,delay:async()=>{},console:{log(){}}});
  vm.runInContext(source.slice(source.indexOf('export async function reviewMatrices')).replace('export ',''),context);
  const arrivals=[];let parameters,dialog,answer,reads=0,checks=0;
  await context.reviewMatrices({
    check:async(name,run)=>{
      if(!['GROUP 4 REVIEW ordinary native dialogs from Claude owner and page tasks keep working',
        'GROUP 4 REVIEW blank and srcdoc native dialogs answer with a held continuation'].includes(name))return;
      checks++;await run();
    },
    nav:async query=>{parameters=new URLSearchParams(query);dialog={id:parameters.get('id'),kind:parameters.get('dialog'),frame:parameters.get('mode')==='inline-dialog'?2:0};},
    call:async(name,args)=>{
      if(name==='read'){
        reads++;
        return {untrusted_content:{dialog},get dialog(){throw Error('The fixture read page data outside untrusted_content');}};
      }
      assert.equal(name,'dialog');assert.equal(args.expected,dialog);answer=args;
      return {followups:[{approval:{operation_id:dialog.id}}]};
    },
    rpc:async name=>{assert.equal(name,'click');return {ok:true};},
    target:async()=>({}),getTab:()=>7,ownerKey(){},
    fixture:{arrivals,mutate:async()=>{}},
    eventually:async predicate=>{const value=await predicate();assert.ok(value,'the current native dialog must be found');return value;},
    receiverEvidence:id=>({count:arrivals.filter(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')===id).length}),
    approval:async(result,id)=>{
      assert.equal(result.followups[0].approval.operation_id,id);
      const reply=dialog.kind==='alert'?'undefined':dialog.kind==='prompt'?(answer.accept?answer.text:'null'):String(answer.accept);
      arrivals.push({url:'http://fixture.test/receive?case='+id,body:new URLSearchParams({reply}).toString()});
    },
  });
  assert.equal(checks,2);assert.equal(reads,21);assert.equal(arrivals.length,21);
});
