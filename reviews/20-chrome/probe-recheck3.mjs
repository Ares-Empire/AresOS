// Production MAIN/ISOLATED code in the same browser-free DOM double as the unit layer.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {mixedRows} from '../../control/chrome/ci/guard-matrix.mjs';
const source=fs.readFileSync('control/chrome_tests/page.test.mjs','utf8');
const factory=Function('assert','fs','vm',source.slice(source.indexOf('const policy='),source.indexOf("test('private factory"))+'return fixture;')(assert,fs,vm);
const results=[];
for(const row of mixedRows()){
  const f=factory({relay:true,nativeShadows:true}),host=new f.HTMLElement(),button=new f.HTMLElement();
  button.root=button;button.isConnected=false;button.textContent='Delete';button.tagName='BUTTON';let handlers=0;f.arm(host,null);
  const root=(row.root?host.attachShadow:f.nativeAttach).call(host,{mode:row.mode});
  const insert=()=>(row.insert?root.appendChild:f.nativeAppend).call(root,button);
  const listen=()=>(row.listen?button.addEventListener:f.nativeListen).call(button,'click',()=>handlers++);
  if(row.order==='before'){listen();insert();}else{insert();listen();}
  (row.dispatch?button.dispatchEvent:f.originalDispatch).call(button,new f.Event('click',{bubbles:true,composed:row.composed,cancelable:true}));
  const held=f.reports.length,limit=row.mask===0&&!row.composed;
  results.push({...row,handlers,held,known_limit:limit});
  assert.equal(handlers,limit?1:0,JSON.stringify(row));assert.equal(held,limit?0:1,JSON.stringify(row));
  f.cleanup();f.guard.dispose();
}
for(const row of mixedRows()){
  const caller=factory({relay:true,nativeShadows:true}),owner=factory({relay:true,nativeShadows:true});
  owner.document.defaultView={};owner.factory.identify('data-private-test','nonce');assert.equal(caller.wire(owner,'data-private-test','nonce'),true);owner.guard.control('epoch');caller.arm(new caller.HTMLElement(),null);
  const host=new owner.HTMLElement(),button=new owner.HTMLElement();button.root=button;button.tagName='BUTTON';button.textContent='Delete';let handlers=0;
  const root=(row.root?caller.main.Element.prototype.attachShadow:owner.nativeAttach).call(host,{mode:row.mode});
  const insert=()=>(row.insert?caller.Node.prototype.appendChild:owner.nativeAppend).call(root,button);
  const listen=()=>(row.listen?caller.EventTarget.prototype.addEventListener:owner.nativeListen).call(button,'click',()=>handlers++);
  if(row.order==='before'){listen();insert();}else{insert();listen();}
  owner.advance(5000);
  (row.dispatch?caller.EventTarget.prototype.dispatchEvent:owner.originalDispatch).call(button,new owner.Event('click',{composed:row.composed,cancelable:true}));
  results.push({...row,foreign:true,handlers,held:owner.reports.length,known_limit:!row.mask});assert.equal(handlers,row.mask?0:1,JSON.stringify(row));assert.equal(owner.reports.length,row.mask?1:0,JSON.stringify(row));
  caller.cleanup();owner.cleanup();caller.guard.dispose();owner.guard.dispose();
}
for(const row of mixedRows()){
    const caller=factory({relay:true,nativeShadows:true}),initial=factory({relay:true,nativeShadows:true}),recipient=factory({relay:true,nativeShadows:true});
    initial.factory.identify('data-initial','initial');recipient.factory.identify('data-recipient','recipient');
    assert.equal(caller.wire(initial,'data-initial','initial'),true);assert.equal(caller.wire(recipient,'data-recipient','recipient'),true);
    assert.equal(initial.guard.source(recipient.factory.relay,'data-recipient','recipient'),true);
    initial.guard.control('epoch');recipient.guard.control('epoch');caller.arm(new caller.HTMLElement(),null);
    const button=new initial.HTMLElement();button.root=button;button.textContent='Delete';button.tagName='BUTTON';let handlers=0;
    const root=(row.root?caller.main.Element.prototype.attachShadow:recipient.nativeAttach).call(new recipient.HTMLElement(),{mode:row.mode});
    const listen=()=>(row.listen?caller.EventTarget.prototype.addEventListener:initial.nativeListen).call(button,'click',()=>handlers++);
    const insert=()=>(row.insert?caller.Node.prototype.appendChild:recipient.nativeAppend).call(root,button);
    if(row.order==='before'){listen();insert();}else{insert();listen();}
    assert.equal(button.ownerDocument,recipient.document);recipient.advance(5000);
    (row.dispatch?caller.EventTarget.prototype.dispatchEvent:initial.originalDispatch).call(button,new initial.Event('click',{composed:row.composed,cancelable:true}));
    assert.equal(handlers,row.mask?0:1,JSON.stringify(row));assert.equal(recipient.reports.length,row.mask?1:0,JSON.stringify(row));assert.equal(initial.reports.length,0);assert.equal(caller.reports.length,0);results.push({...row,adopted:true,handlers,held:recipient.reports.length,known_limit:!row.mask});
    caller.guard.dispose();initial.guard.dispose();recipient.guard.dispose();
  }
if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(results,null,2)+'\n');
console.log(`${results.length} generated mixes passed; only ${results.filter(row=>row.known_limit).length} all-native rows run their handler`);
