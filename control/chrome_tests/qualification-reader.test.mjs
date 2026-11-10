// Execute the actual isolated reader in a VM. No browser or profile is used.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

function readerFixture(security) {
  let reads=0, listener, api;
  class Element {
    nodeType=1;tagName='INPUT';childNodes=[];type='text';labels=[];files=[];name='';
    get value(){reads++;return 'FIXTURE_UNCERTAIN_SECRET';}
    getAttribute(){return null;}
    hasAttribute(){return false;}
    matches(selector){return selector==='input,textarea,select,[contenteditable]' || selector==='input,textarea,[contenteditable]';}
    getRootNode(){return document;}
    getBoundingClientRect(){return {x:1,y:1,width:10,height:10,bottom:11,right:11};}
    closest(){return null;}
  }
  class Input extends Element {}
  const input=new Input();
  const document={title:'Fixture',childNodes:[],querySelectorAll:()=>[input],getElementById:()=>null,addEventListener(){},dispatchEvent(){}};
  const style={display:'block',visibility:'visible',get webkitTextSecurity(){return security();}};
  const context=vm.createContext({document,Element,HTMLElement:Element,HTMLInputElement:Input,
    HTMLTextAreaElement:class extends Element{},HTMLSelectElement:class extends Element{},HTMLButtonElement:class extends Element{},
    Node:{TEXT_NODE:3},MutationObserver:class {observe(){}takeRecords(){return [];}},
    chrome:{dom:{openOrClosedShadowRoot:()=>null},runtime:{id:'fixture',onMessage:{addListener(fn){listener=fn;}}}},
    crypto:{getRandomValues:array=>array.fill(1)},getComputedStyle:()=>style,
    [Symbol.for('aresos.chrome.guard.v2')]:{watch(){},reader(value){api=value;},arm(){},clear(){},steps(){return [];}},
    setTimeout(){},location:{href:'https://fixture.test/'},scrollX:0,scrollY:0,innerWidth:100,innerHeight:100});
  vm.runInContext(fs.readFileSync('control/chrome/extension/reader.js','utf8'),context);
  const command=message=>{let reply;listener(message,{id:'fixture'},value=>reply=value);assert.equal(reply.ok,true,JSON.stringify(reply));return reply;};
  return {command,readCount:()=>reads,form:()=>api.form({tagName:'FORM',elements:[input],action:'https://form.test/',method:'post',enctype:'text/plain',target:'',querySelector:()=>null})};
}

for(const [name,security] of [['missing style property',()=>undefined],['throwing style getter',()=>{throw Error('Fixture safety unavailable');}]]){
  test('QUALIFICATION conservative reader excludes unknown safety: '+name,()=>{
    const fixture=readerFixture(security);
    fixture.command({command:'set_control',generation:'fixture-control'});
    fixture.command({command:'arm',generation:'fixture-control',conservative:true});
    const result=fixture.command({command:'read'});
    const form=fixture.form();
    assert.equal(fixture.readCount(),0);
    assert.equal(form.fields[0].password,true);
    assert.doesNotMatch(JSON.stringify({result,form}),/FIXTURE_UNCERTAIN_SECRET/);
  });
}
