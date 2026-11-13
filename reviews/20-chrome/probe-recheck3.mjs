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
for(const mode of ['open','closed']){
  const caller=factory({relay:true,nativeShadows:true}),owner=factory({relay:true,nativeShadows:true});
  owner.document.root=owner.document;owner.guard.control('epoch');caller.arm(new caller.HTMLElement(),null);
  const host=new owner.HTMLElement(),button=new owner.HTMLElement();button.root=button;button.tagName='BUTTON';button.textContent='Delete';let handlers=0;
  caller.EventTarget.prototype.addEventListener.call(button,'click',()=>handlers++);
  const root=owner.nativeAttach.call(host,{mode});owner.nativeAppend.call(root,button);owner.originalDispatch.call(button,new owner.Event('click',{composed:false,cancelable:true}));
  results.push({mask:4,mode,composed:false,order:'before',foreign:true,handlers,held:owner.reports.length,known_limit:false});assert.equal(handlers,0);assert.equal(owner.reports.length,1);
  caller.cleanup();owner.cleanup();caller.guard.dispose();owner.guard.dispose();
}
if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(results,null,2)+'\n');
console.log(`${results.length} generated mixes passed; only ${results.filter(row=>row.known_limit).length} all-native non-composed rows run their handler`);
