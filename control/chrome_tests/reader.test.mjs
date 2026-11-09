// Browser-free extraction guard. The real all-frame/shadow test belongs in CI.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

function fixture(fields) {
  let calls=0;
  class Element {
    nodeType=1;tagName='INPUT';textContent='';childNodes=[];hidden=false;type='text';isContentEditable=false;labels=[];files=[];name='';
    constructor(config={}){Object.assign(this,config);}
    get value(){calls++;if(this.forbidden)throw Error('PASSWORD VALUE WAS READ');return 'safe visible text';}
    getAttribute(name){if(name==='value' && this.forbidden)throw Error('PASSWORD SOURCE ATTRIBUTE WAS READ');return this.attrs?.[name] ?? null;}
    hasAttribute(name){return this.getAttribute(name)!==null;}
    matches(selector){return selector==='input,textarea,select,[contenteditable]' || selector.includes('input') && this.tagName==='INPUT';}
    getRootNode(){return document;}
    getBoundingClientRect(){return {x:1,y:1,width:10,height:10,bottom:11,right:11};}
    closest(){return this;}
    dispatchEvent(){}
  }
  class HTMLInputElement extends Element{}
  class HTMLTextAreaElement extends Element{}
  class HTMLSelectElement extends Element{}
  const nodes=fields.map(config=>new HTMLInputElement(config));
  const document={title:'Fixture',childNodes:[],getElementById(){return null;},
    querySelectorAll(selector){return nodes;},addEventListener(){},dispatchEvent(){}};
  let listener;
  const chrome={dom:{openOrClosedShadowRoot:()=>null},runtime:{id:'fixture',onMessage:{addListener(fn){listener=fn;}}}};
  class MutationObserver {constructor(fn){this.fn=fn;}observe(){}}
  const context=vm.createContext({document,chrome,crypto:{randomUUID:()=> 'doc'},MutationObserver,
    Element,HTMLInputElement,HTMLTextAreaElement,HTMLSelectElement,Node:{TEXT_NODE:3},CustomEvent:class{},
    getComputedStyle:element=>({display:'block',visibility:'visible',webkitTextSecurity:element.mask || 'none'}),
    location:{href:'https://fixture.test/'},scrollX:0,scrollY:0,innerWidth:100,innerHeight:100});
  vm.runInContext(fs.readFileSync('control/chrome/extension/reader.js','utf8'),context);
  function read(){let result;listener({command:'read'},{id:'fixture'},value=>result=value);assert.equal(result.ok,true,JSON.stringify(result));return result;}
  return {nodes,read,calls:()=>calls};
}

test('group7 protected values never reach a getter, source attribute, trace or binding',()=>{
  const f=fixture([
    {type:'password',forbidden:true},
    {attrs:{autocomplete:'current-password'},forbidden:true},
    {attrs:{autocomplete:'new-password'},forbidden:true},
    {attrs:{autocomplete:'one-time-code'},forbidden:true},
    {mask:'disc',forbidden:true},
  ]);
  assert.doesNotMatch(JSON.stringify(f.read()),/safe visible text/);assert.equal(f.calls(),0);
  f.nodes[0].type='text';f.read();assert.equal(f.calls(),0);
});
test('group7 before every read, a newly protected field is excluded and stays excluded',()=>{
  const f=fixture([{}]);f.read();assert.ok(f.calls()>0);
  const previous=f.calls();f.nodes[0].type='password';f.nodes[0].forbidden=true;f.read();assert.equal(f.calls(),previous);
  f.nodes[0].type='text';f.read();assert.equal(f.calls(),previous);
});
