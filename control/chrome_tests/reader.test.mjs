// Browser-free extraction guard. The real all-frame/shadow test belongs in CI.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {webcrypto,createHash} from 'node:crypto';

function fixture(fields,{subtle=true,NativeBlob=Blob}={}) {
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
    contains(node){for(let ancestor=node;ancestor;ancestor=ancestor.parentElement)if(ancestor===this)return true;return false;}
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
  const chrome={dom:{openOrClosedShadowRoot:element=>element.fixtureShadow||null},runtime:{id:'fixture',sendMessage:async()=>({}),onMessage:{addListener(fn){listener=fn;},removeListener(){}}}};
  class MutationObserver {constructor(fn){this.fn=fn;this.records=[];observer=this;}observe(root,options){observationOptions.push(options);}takeRecords(){return this.records.splice(0);}disconnect(){}}
  const context=vm.createContext({document,chrome,Blob:NativeBlob,crypto:{subtle:subtle?webcrypto.subtle:undefined,getRandomValues:array=>array.fill(++fileSequence)},MutationObserver,
    Element,HTMLElement:Element,HTMLInputElement,HTMLTextAreaElement,HTMLSelectElement,HTMLButtonElement,Node:{TEXT_NODE:3},CustomEvent:class{},
    atob:value=>Buffer.from(value,'base64').toString('binary'),setTimeout:fn=>timers.push(fn),
    getComputedStyle:element=>({display:['DIV','P'].includes(element.tagName)?'block':'inline',visibility:'visible',webkitTextSecurity:element.mask || 'none'}),
    [Symbol.for('aresos.chrome.guard.v2')]:{watch(){},reader(value){readerAPI=value;},arm(){},clear(){},resume(){return {resumed:'native_submit'};},steps(){return [];}},
    origin:'https://fixture.test',location:{href:'https://fixture.test/'},scrollX:0,scrollY:0,innerWidth:100,innerHeight:100});
  vm.runInContext(fs.readFileSync('control/chrome/extension/reader.js','utf8'),context);
  function read(){let result;listener({command:'read'},{id:'fixture'},value=>result=value);assert.equal(result.ok,true,JSON.stringify(result));return result;}
  function command(message){let result;listener(message,{id:'fixture'},value=>result=value);return result;}
  const readAsync=()=>new Promise(resolve=>listener({command:'read'},{id:'fixture'},resolve));
  return {nodes,Element,designMode:value=>{document.designMode=value},generic:node=>Object.setPrototypeOf(node,Element.prototype),reinject:()=>{readerAPI.dispose();vm.runInContext(fs.readFileSync('control/chrome/extension/reader.js','utf8'),context);},read,readAsync,command,form:(element,submitter)=>readerAPI.form(element,submitter),observationOptions,expire:()=>{for(const fn of timers.splice(0))fn();},mutations:()=>observer.records,calls:()=>calls};
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
test('P12 owner selected bytes are hashed privately and identical metadata cannot substitute content',async()=>{
  const f=fixture([{type:'file'}]),node=f.nodes[0];
  const form={tagName:'FORM',elements:[node],action:'https://fixture.test/',method:'post',enctype:'multipart/form-data',target:'',querySelector(){return null;}};
  node.files=[new File(['GOOD'],'proof.txt',{lastModified:0})];assert.equal((await f.readAsync()).ok,true);const first=f.form(form).fields[0].value;
  assert.equal(first[0].sha256,createHash('sha256').update('GOOD').digest('hex'));
  assert.equal(JSON.stringify(first).includes('GOOD'),false,'only the digest and metadata leave the isolated reader');
  assert.deepEqual(JSON.parse(JSON.stringify(f.form(form).fields[0].value)),JSON.parse(JSON.stringify(first)));
  node.files=[new File(['EVIL'],'proof.txt',{lastModified:0})];assert.equal((await f.readAsync()).ok,true);const changed=f.form(form).fields[0].value[0];assert.notEqual(changed.identity,first[0].identity);assert.notEqual(changed.sha256,first[0].sha256);
  node.files=[{name:'proof.txt',size:4,lastModified:0}];assert.throws(()=>f.form(form),/Blob|instance|receiver/i);
});
test('P12 HTTP selected-file hashing matches SHA-256 across padding and multi-block boundaries',async()=>{
  const f=fixture([{type:'file'}],{subtle:false});
  for(const size of [0,1,55,56,63,64,65,128,1000000]){
    const bytes=Buffer.alloc(size,0xa5);f.nodes[0].files=[new File([bytes],'fixture.bin',{lastModified:0})];
    const reply=await f.readAsync();assert.equal(reply.ok,true,JSON.stringify(reply));
    assert.equal(reply.data.selected_files[0].value[0].sha256,createHash('sha256').update(bytes).digest('hex'),String(size));
  }
});
test('P12 every binding rehashes the selected native File even when its object and metadata survive',async()=>{
  let bytes='GOOD',reads=0;
  class NativeBlob {get size(){return 4;}async arrayBuffer(){reads++;return Uint8Array.from(Buffer.from(bytes)).buffer;}}
  const file=Object.assign(new NativeBlob(),{name:'owner-picked.txt',lastModified:1700000000000});
  const f=fixture([{type:'file',files:[file]}],{NativeBlob});
  const first=(await f.readAsync()).data.selected_files[0].value[0];bytes='EVIL';
  const changed=(await f.readAsync()).data.selected_files[0].value[0];
  assert.equal(reads,2);assert.equal(first.identity,changed.identity);assert.equal(first.name,changed.name);assert.equal(first.size,changed.size);assert.equal(first.lastModified,changed.lastModified);
  assert.equal(first.sha256,createHash('sha256').update('GOOD').digest('hex'));assert.equal(changed.sha256,createHash('sha256').update('EVIL').digest('hex'));
});
test('P12 a selection changed during asynchronous hashing refuses before snapshot extraction',async()=>{
  let finish;class NativeBlob {get size(){return 4;}arrayBuffer(){return new Promise(resolve=>{finish=resolve;});}}
  const file=()=>Object.assign(new NativeBlob(),{name:'owner-picked.txt',lastModified:0});
  const f=fixture([{type:'file',files:[file()]}],{NativeBlob});const pending=f.readAsync();f.nodes[0].files=[file()];finish(new Uint8Array([1,2,3,4]).buffer);
  const refused=await pending;assert.equal(refused.ok,false);assert.match(refused.error,/selection changed/);
});
test('P24 document designMode counts as an unsaved editor without a contenteditable attribute',()=>{
  const f=fixture([]);assert.equal(f.command({command:'reload_state'}).data.unsaved,false);f.designMode('on');assert.equal(f.command({command:'reload_state'}).data.unsaved,true);
});
test('P10 affected item includes every ARIA item and named section',()=>{
  for(const selector of ['[role=listitem]','[role=row]','[role=article]','section[aria-label]','section[aria-labelledby]']){
    const f=fixture([{tagName:'BUTTON',type:'button'}]),button=f.nodes[0];f.generic(button);
    const item=new f.Element({tagName:'DIV',childNodes:[{nodeType:3,textContent:'Invoice A'}]});
    button.parentElement=item;item.matches=selectors=>selectors.split(',').includes(selector);button.matches=()=>false;
    assert.equal(f.read().data.item,''); // target-free reads have no affected item
    const before=f.command({command:'facts',element:'e1'}).data.item;
    item.childNodes[0].textContent='Invoice B';assert.notEqual(f.command({command:'facts',element:'e1'}).data.item,before,selector);
  }
});


test('P17 lost-history identity refuses before collecting any field value',()=>{
  const f=fixture([{}]);const identity=f.read().data.document,before=f.calls();f.nodes[0].forbidden=true;
  const refused=f.command({command:'read',expected_document:identity+'-lost'});assert.equal(refused.ok,false);assert.match(refused.error,/password history was lost/);assert.equal(f.calls(),before);
});
test('P2 inherited origin is checked before any field getter',()=>{
  const f=fixture([{forbidden:true}]);const refused=f.command({command:'read',expected_origin:'https://different.test'});
  assert.equal(refused.ok,false);assert.match(refused.error,/origin cannot be authenticated/);assert.equal(f.calls(),0);
});

test('recheck affected items cross open closed nested and slotted shadow ancestry',()=>{
  for(const kind of ['li','[role=row]'])for(const mode of ['open','closed'])for(const nested of [false,true]){
    const f=fixture([{tagName:'BUTTON',type:'button'}]),button=f.nodes[0];f.generic(button);button.matches=()=>false;
    const label={nodeType:3,textContent:'Invoice A'},item=new f.Element({tagName:kind==='li'?'LI':'DIV',childNodes:[label]}),host=new f.Element({tagName:'DIV',parentElement:item});
    item.matches=selector=>selector.split(',').includes(kind);item.childNodes.push(host);
    let root={host,mode,childNodes:[],querySelectorAll:()=>[]};host.fixtureShadow=root;
    if(nested){const inner=new f.Element({tagName:'DIV'});inner.getRootNode=()=>root;root.childNodes=[inner];const outer=root;root={host:inner,mode,childNodes:[],querySelectorAll:()=>[]};inner.fixtureShadow=root;inner.getRootNode=()=>outer;}
    button.getRootNode=()=>root;root.childNodes=[button];
    f.read();const before=f.command({command:'facts',element:'e1'}).data.item;assert.match(before,/Invoice A/);
    label.textContent='Invoice B';const after=f.command({command:'facts',element:'e1'}).data.item;assert.match(after,/Invoice B/);assert.notEqual(before,after);
    // Identifying text inside a closed component also belongs to the item.
    label.textContent='';root.childNodes=[{nodeType:3,textContent:'Shadow invoice C'},button];
    assert.match(f.command({command:'facts',element:'e1'}).data.item,/Shadow invoice C/);
    const slot=new f.Element({tagName:'SLOT',parentElement:item});slot.matches=()=>false;button.assignedSlot=slot;
    assert.match(f.command({command:'facts',element:'e1'}).data.item,/Shadow invoice C/);
  }
});
test('recheck slotted affected items include native rows hidden by closed-slot ancestry',()=>{
  for(const mode of ['open','closed'])for(const selector of ['li','[role=row]']){
    const f=fixture([{tagName:'BUTTON',type:'button',childNodes:[{nodeType:3,textContent:'Delete'}]}]),button=f.nodes[0];f.generic(button);button.matches=()=>false;
    const host=new f.Element({tagName:'DIV'}),label={nodeType:3,textContent:'Invoice A'},row=new f.Element({tagName:selector==='li'?'LI':'DIV'}),slot=new f.Element({tagName:'SLOT',parentElement:row});
    const root={host,childNodes:[row],querySelectorAll:query=>query==='slot'?[slot]:[row,slot]};host.fixtureShadow=root;
    row.childNodes=[label,slot];row.matches=query=>query.split(',').includes(selector);row.getRootNode=()=>root;slot.matches=()=>false;slot.getRootNode=()=>root;slot.assignedNodes=()=>[button];button.parentElement=host;
    Object.defineProperty(button,'assignedSlot',{get(){return mode==='closed'?null:slot;}});
    f.read();const before=f.command({command:'facts',element:'e1'}).data.item;assert.match(before,/Invoice A/);
    label.textContent='Invoice B';assert.match(f.command({command:'facts',element:'e1'}).data.item,/Invoice B/);
  }
});
test('recheck editable asking controls retain control semantics while message fields stay editable',()=>{
  for(const config of [{tagName:'BUTTON',type:'button',isContentEditable:true},{tagName:'DIV',isContentEditable:true,attrs:{role:'button'}},{tagName:'INPUT',type:'button',isContentEditable:true,attrs:{role:'textbox'}}]){
    const f=fixture([config]);if(config.tagName!=='INPUT')f.generic(f.nodes[0]);f.read();
    assert.equal(f.command({command:'facts',element:'e1'}).data.target.editable,false);
  }
  const f=fixture([{tagName:'TEXTAREA',isContentEditable:true,attrs:{role:'textbox'}}]);f.generic(f.nodes[0]);f.read();assert.equal(f.command({command:'facts',element:'e1'}).data.target.editable,true);
});
test('recheck item quantities are bound as fields and protected item fields never read values',()=>{
  const f=fixture([{type:'number',attrs:{'aria-label':'Quantity'}},{type:'password',forbidden:true},{tagName:'BUTTON',type:'button',childNodes:[{nodeType:3,textContent:'Pay'}]}]);
  const [quantity,password,button]=f.nodes;f.generic(button);let value='1';Object.defineProperty(quantity,'value',{get(){return value;}});
  const article=new f.Element({tagName:'ARTICLE',childNodes:[quantity,password,button]});article.matches=selector=>selector.split(',').includes('article');for(const node of f.nodes){node.parentElement=article;node.matches=()=>false;}
  f.read();const key=f.read().data.rows.find(row=>row.name==='Pay').element;
  const before=f.command({command:'facts',element:key}).data.item_fields;
  assert.equal(before?.find(field=>field.label==='Quantity')?.value,'1');assert.equal(before?.find(field=>field.password)?.value,undefined);
  value='2';assert.equal(f.command({command:'facts',element:key}).data.item_fields?.find(field=>field.label==='Quantity')?.value,'2');
});
