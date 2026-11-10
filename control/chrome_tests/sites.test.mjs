// Compile synthetic page code locally; this test never starts a browser.
import assert from 'node:assert/strict';
import test from 'node:test';
import vm from 'node:vm';
import fs from 'node:fs';
import {sitePage} from '../chrome/ci/sites/fixture.mjs';

test('adapter fixture scripts compile for every site and confirmation mismatch',()=>{
  for(const site of ['gmail','whatsapp','github','gemini','deezer','bank'])for(const variant of ['', 'two','quoted','unknown','incomplete','form-playback'])for(const mismatch of ['', 'kind','text','frame','site','button','twice']){
    const url=new URL('http://'+site+'.test:8765/?case=adapter-sites&id=fixture&variant='+variant+'&mismatch='+mismatch);
    const page=sitePage(url,url.host);new vm.Script(page.script);
    assert.ok(page.body.length);assert.doesNotMatch(page.script,/https?:\/\/(?![^\s"']*\.test)/);
  }
  new vm.Script(sitePage(new URL('http://second.test:8765/?id=child&variant=child'),'second.test:8765').script);
});

test('actual extension confirmation handler compares each field and consumes a match once',async()=>{
  const source=fs.readFileSync('control/chrome/extension/background.js','utf8');
  const handler=source.slice(source.indexOf('chrome.debugger.onEvent.addListener('),source.indexOf('chrome.debugger.onDetach.addListener('));
  for(const mismatch of [null,'kind','text','frame_url','button','frame','document']){
    const accepted=[],expected={kind:'confirm',text:'Delete tag fixture-tag?',frame_url:'http://github.test/',button:'OK',frame:0};
    if(mismatch&&mismatch!=='document')expected[mismatch]=mismatch==='frame'?3:'Different synthetic '+mismatch;
    const plan={expected,browser_document:mismatch==='document'?'different-document':'document-1',matched:[]};
    let listener;
    const chrome={debugger:{onEvent:{addListener:fn=>{listener=fn;}}},webNavigation:{getAllFrames:async()=>[{frameId:0,documentId:'document-1',url:'http://github.test/'}]}};
    const context=vm.createContext({chrome,crypto:{randomUUID:()=> 'dialog'},safeURL:()=>{},wakeDialog:()=>{},
      dialogs:new Map(),controlled:new Map([[7,{epoch:'epoch',inputNonce:'nonce'}]]),dialogInputs:new WeakMap(),confirmationPlans:new Map([[7,plan]]),
      cdp:async(tab,method,args)=>accepted.push({tab,method,args})});
    vm.runInContext(handler,context);
    await listener({tabId:7},'Page.javascriptDialogOpening',{type:'confirm',message:'Delete tag fixture-tag?',url:'http://github.test/'});
    assert.equal(accepted.length,mismatch?0:1,mismatch||'exact match');
    assert.equal(plan.matched.length,mismatch?0:1);
    await listener({tabId:7},'Page.javascriptDialogOpening',{type:'confirm',message:'Delete tag fixture-tag?',url:'http://github.test/'});
    assert.equal(accepted.length,mismatch?0:1,'no second acceptance: '+mismatch);
  }
});
