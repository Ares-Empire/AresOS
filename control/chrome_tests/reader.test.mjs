// Browser-free extraction guard. The real all-frame/shadow test belongs in CI.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

function fixture(fields) {
  let calls=0,fileSequence=0;const timers=[];
  class Element {
    isConnected=true;nodeType=1;tagName='INPUT';textContent='';childNodes=[];hidden=false;type='text';isContentEditable=false;labels=[];files=[];name='';
    constructor(config={}){Object.assign(this,config);}
    get value(){calls++;if(this.forbidden)throw Error('PASSWORD VALUE WAS READ');return 'safe visible text';}
    getAttribute(name){if(name==='value' && this.forbidden)throw Error('PASSWORD SOURCE ATTRIBUTE WAS READ');return this.attrs?.[name] ?? null;}
    hasAttribute(name){return this.getAttribute(name)!==null;}
    matches(selector){if(selector===':disabled')return !!this.disabled;return selector==='input,textarea,select,[contenteditable]' || selector.includes('input') && this.tagName==='INPUT';}
    getRootNode(){return document;}
    getBoundingClientRect(){return {x:1,y:1,width:10,height:10,bottom:11,right:11};}
    closest(selector){return selector==='dialog,[role=dialog],[role=alertdialog]' ? this.dialog || null : this;}
    dispatchEvent(){}
  }
  class HTMLInputElement extends Element{}
  class HTMLTextAreaElement extends Element{}
  class HTMLSelectElement extends Element{}
  class HTMLButtonElement extends Element{}
  const nodes=fields.map(config=>new HTMLInputElement(config));
  const document={title:'Fixture',childNodes:[],getElementById(){return null;},
    querySelectorAll(selector){return nodes;},addEventListener(){},dispatchEvent(){}};
  let listener,observer,readerAPI;const observationOptions=[];
  const chrome={dom:{openOrClosedShadowRoot:()=>null},runtime:{id:'fixture',onMessage:{addListener(fn){listener=fn;},removeListener(){}}}};
  class MutationObserver {constructor(fn){this.fn=fn;this.records=[];observer=this;}observe(root,options){observationOptions.push(options);}takeRecords(){return this.records.splice(0);}disconnect(){}}
  const context=vm.createContext({document,chrome,Blob,crypto:{getRandomValues:array=>array.fill(1),randomUUID:()=>String(++fileSequence)},MutationObserver,
    Element,HTMLElement:Element,HTMLInputElement,HTMLTextAreaElement,HTMLSelectElement,HTMLButtonElement,Node:{TEXT_NODE:3},CustomEvent:class{},
    atob:value=>Buffer.from(value,'base64').toString('binary'),setTimeout:fn=>timers.push(fn),
    getComputedStyle:element=>({display:['DIV','P'].includes(element.tagName)?'block':'inline',visibility:'visible',webkitTextSecurity:element.mask || 'none'}),
    [Symbol.for('aresos.chrome.guard.v2')]:{watch(){},reader(value){readerAPI=value;},arm(){},clear(){},resume(){return {resumed:'native_submit'};},steps(){return [];}},
    location:{href:'https://fixture.test/'},scrollX:0,scrollY:0,innerWidth:100,innerHeight:100});
  vm.runInContext(fs.readFileSync('control/chrome/extension/reader.js','utf8'),context);
  function read(){let result;listener({command:'read'},{id:'fixture'},value=>result=value);assert.equal(result.ok,true,JSON.stringify(result));return result;}
  function command(message){let result;listener(message,{id:'fixture'},value=>result=value);return result;}
  return {nodes,Element,generic:node=>Object.setPrototypeOf(node,Element.prototype),reinject:()=>{readerAPI.dispose();vm.runInContext(fs.readFileSync('control/chrome/extension/reader.js','utf8'),context);},read,command,form:(element,submitter)=>readerAPI.form(element,submitter),observationOptions,expire:()=>{for(const fn of timers.splice(0))fn();},mutations:()=>observer.records,calls:()=>calls};
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

test('group3 every field records checked, disabled and multiple state',()=>{
  const f=fixture([{type:'checkbox',checked:false,disabled:false}]);
  const before=f.read().data.editable[0];f.nodes[0].checked=true;f.nodes[0].disabled=true;f.nodes[0].multiple=true;
  const after=f.read().data.editable[0];
  assert.equal(before.checked,false);assert.equal(after.checked,true);assert.equal(after.disabled,true);assert.equal(after.multiple,true);
  assert.notDeepEqual(before,after);
});

test('isolated arm and resume messages reach the guard without falling through dispatch',()=>{
  const f=fixture([]);assert.equal(f.command({command:'set_control',generation:'epoch'}).ok,true);
  assert.equal(f.command({command:'arm',generation:'epoch'}).ok,true);
  assert.equal(f.command({command:'resume',generation:'epoch',hold:'h1',operation:'op'}).ok,true);
  assert.equal(f.command({command:'resume',generation:'forged',hold:'h1',operation:'op'}).ok,false);
});

test('group7 password-to-text transitions in one task are excluded before observer delivery',()=>{
  const f=fixture([{}]);f.read();const before=f.calls();
  f.nodes[0].forbidden=true;f.mutations().push({type:'attributes',attributeName:'type',oldValue:'password',target:f.nodes[0]});
  f.read();assert.equal(f.calls(),before);
});

test('group7 uppercase historical password attributes stay excluded',()=>{
  for(const [attributeName,oldValue] of [['type','PASSWORD'],['autocomplete','CURRENT-PASSWORD'],['autocomplete','ONE-TIME-CODE'],['style','-webkit-text-security: disc;']]){
    const f=fixture([{}]);f.read();const before=f.calls();f.nodes[0].forbidden=true;
    f.mutations().push({type:'attributes',attributeName,oldValue,target:f.nodes[0]});f.read();assert.equal(f.calls(),before);
  }
});


test('group7 mutation API never requests old source values or character data',()=>{
  const f=fixture([{}]);f.read();
  for(const options of f.observationOptions)if(options.attributeOldValue){
    assert.deepEqual([...options.attributeFilter],['type','autocomplete','style']);
    assert.equal(options.characterDataOldValue,undefined);
  }
  assert.ok(f.observationOptions.some(options=>options.attributes&&!options.attributeOldValue));
});


test('group5 interrupted partial uploads expire instead of occupying both slots forever',()=>{
  const f=fixture([]);f.command({command:'set_control',generation:'epoch'});
  const stage=token=>f.command({command:'stage_file',generation:'epoch',token,offset:0,bytes:'YQ==',file:{size:2,name:'fixture.txt'}});
  assert.equal(stage('one').ok,true);assert.equal(stage('two').ok,true);assert.equal(stage('three').ok,false);
  f.expire();assert.equal(stage('three').ok,true);
});


test('form binding uses normalized native getters for present-empty and invalid submitter overrides',()=>{
  for(const attribute of ['', 'invalid']){
    const f=fixture([{type:'submit',attrs:{formaction:attribute,formmethod:attribute,formenctype:attribute,formtarget:''}}]);
    const form={tagName:'FORM',elements:[],action:'https://fixture.test/bare',method:'post',enctype:'multipart/form-data',target:'old',querySelector(){return null;}};
    const button=f.nodes[0];Object.assign(button,{form,formAction:'https://fixture.test/current',formMethod:'get',formEnctype:'application/x-www-form-urlencoded',formTarget:''});
    const state=f.form(form,button);assert.equal(state.action,button.formAction);assert.equal(state.method,'get');assert.equal(state.encoding,button.formEnctype);assert.equal(state.target,'');
  }
});


test('P15 visible button contents precede a conflicting title',()=>{
  const f=fixture([{tagName:'BUTTON',type:'button',attrs:{title:'More information'},childNodes:[{nodeType:3,textContent:'Delete'}]}]);
  f.generic(f.nodes[0]);assert.equal(f.read().data.rows[0].name,'Delete');
});
test('P16 iframe address reads srcdoc presence without collecting its HTML',()=>{
  const f=fixture([{tagName:'IFRAME',attrs:{srcdoc:''},offsetWidth:10,offsetHeight:10,clientLeft:0,clientTop:0}]);
  Object.defineProperty(f.nodes[0],'srcdoc',{get(){assert.fail('raw srcdoc was collected');}});
  assert.equal(f.read().data.embeds[0].url,'about:srcdoc');
});
test('P17 sticky password identity survives reader disposal and reinjection',()=>{
  const f=fixture([{type:'password',forbidden:true}]);f.read();f.nodes[0].type='text';f.reinject();f.read();assert.equal(f.calls(),0);
});
test('P18 protected descendants and a formerly editable field never expose content',()=>{
  const f=fixture([{tagName:'DIV',isContentEditable:true,attrs:{autocomplete:'current-password'}},{tagName:'SPAN'}]);
  for(const node of f.nodes)f.generic(node);
  const [parent,child]=f.nodes;child.parentElement=parent;
  Object.defineProperty(child,'childNodes',{get(){assert.fail('protected descendant text getter was read');}});
  parent.childNodes=[child];f.read();parent.isContentEditable=false;parent.attrs={};f.read();
  assert.doesNotMatch(JSON.stringify(f.read()),/safe visible text/);
});
test('P13 rich text keeps block boundaries and explicit breaks distinct from spaces',()=>{
  const f=fixture([{tagName:'DIV',isContentEditable:true}]);const editor=f.nodes[0];f.generic(editor);
  const text=value=>({nodeType:3,textContent:value});
  editor.childNodes=[new f.Element({tagName:'DIV',childNodes:[text('Line one')]}),new f.Element({tagName:'DIV',childNodes:[text('Line two')]})];
  const multiline=f.read().data.editable[0].value;assert.equal(multiline,'Line one\nLine two');
  editor.childNodes=[text('Line one Line two')];assert.notEqual(f.read().data.editable[0].value,multiline);
  editor.childNodes=[text('Line one'),new f.Element({tagName:'BR'}),text('Line two')];assert.equal(f.read().data.editable[0].value,multiline);
});
test('P12 identical file metadata cannot substitute different immutable bytes',()=>{
  const f=fixture([{type:'file'}]),node=f.nodes[0];
  const form={tagName:'FORM',elements:[node],action:'https://fixture.test/',method:'post',enctype:'multipart/form-data',target:'',querySelector(){return null;}};
  node.files=[new File(['GOOD'],'proof.txt',{lastModified:0})];const first=f.form(form).fields[0].value;
  assert.deepEqual(JSON.parse(JSON.stringify(f.form(form).fields[0].value)),JSON.parse(JSON.stringify(first)));
  node.files=[new File(['EVIL'],'proof.txt',{lastModified:0})];assert.notEqual(f.form(form).fields[0].value[0].identity,first[0].identity);
  node.files=[{name:'proof.txt',size:4,lastModified:0}];assert.throws(()=>f.form(form),/Blob|instance|receiver/i);
});
test('P10 affected item includes every ARIA item and named section',()=>{
  for(const selector of ['[role=listitem]','[role=row]','[role=article]','section[aria-label]','section[aria-labelledby]']){
    const f=fixture([{tagName:'BUTTON',type:'button'}]),button=f.nodes[0];f.generic(button);
    const item=new f.Element({tagName:'DIV',childNodes:[{nodeType:3,textContent:'Invoice A'}]});
    button.closest=selectors=>selectors==='dialog,[role=dialog],[role=alertdialog]'?null:selectors.includes(selector)?item:button;
    assert.equal(f.read().data.item,''); // target-free reads have no affected item
    const before=f.command({command:'facts',element:'e1'}).data.item;
    item.childNodes[0].textContent='Invoice B';assert.notEqual(f.command({command:'facts',element:'e1'}).data.item,before,selector);
  }
});
