// Browser-free extraction guard. The real all-frame/shadow test belongs in CI.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {webcrypto,createHash} from 'node:crypto';

function fixture(fields,{subtle=true,NativeBlob=Blob,protectedPeer=()=>false,watched=true}={}) {
  let calls=0,fileSequence=0,clipboardInfo=null;const timers=[];
  let base='https://fixture.test/';
  class NativeNode {get baseURI(){return base;}}
  NativeNode.TEXT_NODE=3;
  class Element extends NativeNode {
    isConnected=true;nodeType=1;tagName='INPUT';textContent='';childNodes=[];hidden=false;type='text';isContentEditable=false;labels=[];files=[];name='';
    constructor(config={}){super();Object.assign(this,config);}
    get textLength(){return this.empty?0:17;}
    get value(){calls++;if(this.forbidden)throw Error('PASSWORD VALUE WAS READ');return 'safe visible text';}
    getAttribute(name){if(name==='value' && this.forbidden)throw Error('PASSWORD SOURCE ATTRIBUTE WAS READ');return this.attrs?.[name] ?? null;}
    hasAttribute(name){return this.getAttribute(name)!==null;}
    getAttributeNS(namespace,name){return this.getAttribute('xlink:'+name);}
    hasAttributeNS(namespace,name){return this.getAttributeNS(namespace,name)!==null;}
    get href(){return new URL(this.getAttribute('href'),this.baseURI).href;}
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
  const document={implementation:{createHTMLDocument(){return {importNode:element=>{if(element.forbidden)throw Error('PROTECTED CONTROL WAS CLONED');return {validity:{valueMissing:!!element.empty}};}};}},title:'Fixture',childNodes:[],getElementById(){return null;},
    querySelector(selector){return selector==='base[target]'?nodes.find(node=>node.tagName==='BASE'&&node.hasAttribute('target'))||null:null;},querySelectorAll(selector){return nodes;},addEventListener(){},dispatchEvent(){}};
  let listener,observer,readerAPI;const observationOptions=[];
  const chrome={dom:{openOrClosedShadowRoot:element=>element.fixtureShadow||null},runtime:{id:'fixture',sendMessage:async()=>({}),onMessage:{addListener(fn){listener=fn;},removeListener(){}}}};
  class MutationObserver {constructor(fn){this.fn=fn;this.records=[];observer=this;}observe(root,options){observationOptions.push(options);}takeRecords(){return this.records.splice(0);}disconnect(){}}
  const context=vm.createContext({document,chrome,Blob:NativeBlob,crypto:{subtle:subtle?webcrypto.subtle:undefined,getRandomValues:array=>array.fill(++fileSequence)},MutationObserver,
    Element,HTMLElement:Element,HTMLInputElement,HTMLTextAreaElement,HTMLSelectElement,HTMLButtonElement,HTMLAnchorElement:Element,HTMLAreaElement:Element,Node:NativeNode,CustomEvent:class{},
    atob:value=>Buffer.from(value,'base64').toString('binary'),setTimeout:fn=>timers.push(fn),
    URL,getComputedStyle:element=>({display:['DIV','P','PRE'].includes(element.tagName)?'block':'inline',visibility:element.visibility||'visible',webkitTextSecurity:element.mask || 'none',whiteSpace:element.whiteSpace||(element.tagName==='PRE'?'pre':undefined)}),
    [Symbol.for('aresos.chrome.document-start.v1')]:watched,
    [Symbol.for('aresos.chrome.guard.v2')]:{protectedPeer,clipboard(take){const value=clipboardInfo;if(take)clipboardInfo=null;return value;},watch(){},reader(value){readerAPI=value;},arm(){},clear(){},resume(){return {resumed:'native_submit'};},steps(){return [];}},
    origin:'https://fixture.test',location:{href:'https://fixture.test/'},scrollX:0,scrollY:0,innerWidth:100,innerHeight:100});
  vm.runInContext(fs.readFileSync('control/chrome/extension/reader.js','utf8'),context);
  function read(){let result;listener({command:'read'},{id:'fixture'},value=>result=value);assert.equal(result.ok,true,JSON.stringify(result));return result;}
  function command(message){let result;listener(message,{id:'fixture'},value=>result=value);return result;}
  const readAsync=()=>new Promise(resolve=>listener({command:'read'},{id:'fixture'},resolve));
  return {nodes,Element,setBase:value=>{base=value;},atPoint:node=>{document.elementFromPoint=()=>node;},textarea:node=>Object.setPrototypeOf(node,HTMLTextAreaElement.prototype),setClipboard:value=>{clipboardInfo=value},observeAsync:()=>new Promise(resolve=>listener({command:'observe'},{id:'fixture'},resolve)),designMode:value=>{document.designMode=value},generic:node=>Object.setPrototypeOf(node,Element.prototype),reinject:()=>{readerAPI.dispose();vm.runInContext(fs.readFileSync('control/chrome/extension/reader.js','utf8'),context);},read,readAsync,command,form:(element,submitter)=>readerAPI.form(element,submitter),observationOptions,expire:()=>{for(const fn of timers.splice(0))fn();},mutations:()=>observer.records,calls:()=>calls};
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

test('recheck2 compose text binds the smallest common area and ignores live outside text',()=>{
  const f=fixture([{tagName:'BUTTON',type:'button',attrs:{'aria-label':'Send'}},{tagName:'DIV',isContentEditable:true,childNodes:[{nodeType:3,textContent:'Draft'}]}]);
  const [button,draft]=f.nodes;f.generic(button);f.generic(draft);
  const area=new f.Element({tagName:'SECTION'}),preview=new f.Element({tagName:'P',childNodes:[{nodeType:3,textContent:'Original preview'}]}),outside=new f.Element({tagName:'P',childNodes:[{nodeType:3,textContent:'Timestamp 1 Autosaved 1 Counter 1'}]}),body=new f.Element({tagName:'BODY'});
  area.childNodes=[draft,preview,button];area.parentElement=body;body.childNodes=[outside,area];outside.parentElement=body;for(const child of area.childNodes)child.parentElement=area;
  f.nodes.push(area,preview,outside,body);const row=f.read().data.rows.find(row=>row.name==='Send');
  const current=()=>f.command({command:'facts',element:row.element}).data.compose;
  const initial=current();assert.match(initial.text,/Original preview/);assert.equal(initial.whole_page,false);
  outside.childNodes[0].textContent='Timestamp 2 Autosaved 2 Counter 2';assert.deepEqual(current(),initial);
  preview.childNodes[0].textContent='Changed preview';assert.notDeepEqual(current(),initial);assert.match(current().text,/Changed preview/);
});

test('2c post-input observations expose only the private clipboard fact and consume it once',async()=>{
  const f=fixture([]),fact={written:true,message:'The page wrote to the clipboard.',routes:['writeText']};f.setClipboard(fact);
  const first=await f.observeAsync();assert.equal(first.ok,true);assert.deepEqual(first.data.clipboard,fact);
  const second=await f.observeAsync();assert.equal(second.ok,true);assert.equal(second.data.clipboard,undefined);
});


test('recheck3 compose preserves rendered indentation linebreaks and significant spaces without protected reads',()=>{
  for(const kind of ['pre','pre-wrap','pre-line','break-spaces','PRE','TEXTAREA','CODE']){
    const f=fixture([{tagName:'BUTTON',type:'button',attrs:{'aria-label':'Send'}},{tagName:'DIV',isContentEditable:true}]);
    const [button,draft]=f.nodes;f.generic(button);f.generic(draft);
    let content='if approved:\n    send()\naudit()';
    const preview=new f.Element({tagName:['PRE','TEXTAREA','CODE'].includes(kind)?kind:'DIV',whiteSpace:kind==='CODE'?'pre-wrap':kind.toLowerCase(),childNodes:[]});
    const text={nodeType:3,parentElement:preview,get textContent(){return content;}};preview.childNodes=[text];if(kind==='PRE')preview.hidden=true;
    if(kind==='TEXTAREA'){f.textarea(preview);Object.defineProperty(preview,'value',{get(){return content;}});}
    const secret=new f.Element({tagName:'INPUT',type:'password',forbidden:true,childNodes:[{nodeType:3,get textContent(){throw Error('PASSWORD TEXT READ');}}]});
    Object.setPrototypeOf(secret,Object.getPrototypeOf(draft));secret.isContentEditable=true;
    const area=new f.Element({tagName:'SECTION',childNodes:[draft,preview,secret,button]});for(const node of area.childNodes)node.parentElement=area;
    f.nodes.push(area,preview,secret);const row=f.read().data.rows.find(row=>row.name==='Send');
    const current=()=>f.command({command:'facts',element:row.element}).data.compose.text;
    const before=current();assert.ok(before.includes(kind==='pre-line'?'if approved:\nsend()\naudit()':content),kind);
    content='if approved:\n    send()\n    audit()';
    if(kind==='pre-line')assert.equal(current(),before,'pre-line collapses indentation as rendered');
    else{assert.notEqual(current(),before,kind+' indentation');assert.ok(current().includes(content));}
    content='if approved:\n    send() audit()';assert.notEqual(current(),before,kind+' linebreak');
  }
});

test('recheck3 ordinary collapsed whitespace stays free while br blocks inline runs and nonbreaking spaces remain visible',()=>{
  const f=fixture([{tagName:'BUTTON',type:'button',attrs:{'aria-label':'Send'}},{tagName:'DIV',isContentEditable:true}]);const [button,draft]=f.nodes;f.generic(button);f.generic(draft);
  const first=new f.Element({tagName:'SPAN',childNodes:[{nodeType:3,textContent:'one  '}]}),second=new f.Element({tagName:'SPAN',childNodes:[{nodeType:3,textContent:' two'}]}),br=new f.Element({tagName:'BR'});
  const preview=new f.Element({tagName:'DIV',childNodes:[first,second,br,{nodeType:3,textContent:'three\u00a0 four'}]}),area=new f.Element({tagName:'SECTION',childNodes:[draft,preview,button]});
  for(const node of area.childNodes)node.parentElement=area;f.nodes.push(preview,area);f.read();const key=f.read().data.rows.find(row=>row.name==='Send').element;
  const current=()=>f.command({command:'facts',element:key}).data.compose.text;const before=current();assert.match(before,/one two\nthree\u00a0 four/);
  first.childNodes[0].textContent='one\n  ';assert.equal(current(),before);
  preview.childNodes[3].textContent='three four';assert.notEqual(current(),before);
});


test('recheck3 area and SVG links expose native destinations and mapped area input stays on its own shape',()=>{
  const f=fixture([]),map=new f.Element({tagName:'MAP',attrs:{name:'map'}}),image=new f.Element({tagName:'IMG',attrs:{usemap:'#map'}});
  image.getBoundingClientRect=()=>({x:20,y:30,width:160,height:70,bottom:100,right:180});
  const area=new f.Element({tagName:'AREA',attrs:{alt:'Delete',href:'/delete',shape:'rect',coords:'0,0,160,70'}});
  area.closest=selector=>selector==='map'?map:null;map.querySelectorAll=()=>[area];f.nodes.push(map,image,area);f.atPoint(image);
  const row=f.read().data.rows.find(row=>row.role==='link');assert.equal(row.name,'Delete');assert.equal(row.href,'https://fixture.test/delete');
  assert.deepEqual(JSON.parse(JSON.stringify(row.box)),{x:20,y:30,width:160,height:70});assert.equal(f.command({command:'hit',element:row.element,x:100,y:65}).data.hit,true);
  const earlier=new f.Element({tagName:'AREA',attrs:{shape:'circle',coords:'80,35,20'}});map.querySelectorAll=()=>[earlier,area];
  assert.equal(f.command({command:'hit',element:row.element,x:100,y:65}).data.hit,false,'an earlier map region must win');
  for(const href of ['/delete','']){
    const svg=new f.Element({tagName:'a',namespaceURI:'http://www.w3.org/2000/svg',localName:'a',attrs:{'aria-label':'Delete',href}});f.nodes.push(svg);
    const found=f.read().data.rows.filter(row=>row.role==='link').at(-1);assert.equal(found.name,'Delete');assert.equal(found.href,new URL(href,'https://fixture.test/').href);
  }
});

test('recheck3 leading pre-line newlines and block br blank lines cannot alias their absence',()=>{
  const f=fixture([{tagName:'BUTTON',type:'button',attrs:{'aria-label':'Send'}},{tagName:'DIV',isContentEditable:true,childNodes:[{nodeType:3,textContent:'Draft'}]}]);
  const [button,draft]=f.nodes;f.generic(button);f.generic(draft);button.childNodes=[{nodeType:3,textContent:'Send'}];
  const preview=new f.Element({tagName:'DIV',whiteSpace:'pre-line',childNodes:[{nodeType:3,textContent:'line'}]}),area=new f.Element({tagName:'SECTION',childNodes:[draft,preview,button]});
  for(const node of area.childNodes)node.parentElement=area;f.nodes.push(area,preview);const key=f.read().data.rows.find(row=>row.name==='Send').element;
  const current=()=>f.command({command:'facts',element:key}).data.compose.text,before=current();
  preview.childNodes[0].textContent='line\n';assert.notEqual(current(),before,'a trailing preserved linebreak remains separate from its block boundary');assert.match(current(),/line\n\nSend/);
  preview.childNodes[0].textContent='\nline';assert.notEqual(current(),before,'a leading preserved linebreak adds a blank line');assert.match(current(),/Draft\n\nline/);
  preview.childNodes=[new f.Element({tagName:'BR'}),{nodeType:3,textContent:'line'}];assert.match(current(),/Draft\n\nline/,'a block-leading br also adds a blank line');
});


test('recheck3 significant visible descendant text survives a visibility hidden ancestor',()=>{
  const f=fixture([{tagName:'BUTTON',type:'button',attrs:{'aria-label':'Send'}},{tagName:'DIV',isContentEditable:true}]);const [button,draft]=f.nodes;f.generic(button);f.generic(draft);
  const preview=new f.Element({tagName:'CODE',whiteSpace:'pre-wrap',visibility:'visible',childNodes:[{nodeType:3,textContent:'one\n    two'}]}),hidden=new f.Element({tagName:'DIV',visibility:'hidden',childNodes:[{nodeType:3,textContent:'HIDDEN SOURCE'},preview]}),area=new f.Element({tagName:'SECTION',childNodes:[draft,hidden,button]});
  for(const node of area.childNodes)node.parentElement=area;preview.parentElement=hidden;f.nodes.push(area,hidden,preview);const key=f.read().data.rows.find(row=>row.name==='Send').element;
  const current=()=>f.command({command:'facts',element:key}).data.compose.text,before=current();assert.ok(before.includes('one\n    two'));assert.ok(!before.includes('HIDDEN SOURCE'));
  preview.childNodes[0].textContent='one\ntwo';assert.notEqual(current(),before);
});

test('recheck3 adopted HTML controls retain their native field brand and current password exclusion',()=>{
  const f=fixture([{namespaceURI:'http://www.w3.org/1999/xhtml',localName:'input'}]);f.generic(f.nodes[0]);
  assert.equal(f.read().data.editable[0].value,'safe visible text');const before=f.calls();
  f.nodes[0].mask='disc';f.nodes[0].forbidden=true;assert.equal(f.read().data.editable[0].password,true);assert.equal(f.calls(),before);
  f.nodes[0].mask='none';f.read();assert.equal(f.calls(),before);
});

test('recheck3 adopted peer password provenance stays private and sticky across peer release and retake',()=>{
  let protectedPeer=true;const f=fixture([{forbidden:true,namespaceURI:'http://www.w3.org/1999/xhtml',localName:'input'}],{protectedPeer:()=>protectedPeer});f.generic(f.nodes[0]);
  assert.equal(f.read().data.editable[0].password,true);assert.equal(f.calls(),0);
  protectedPeer=false;f.read();f.reinject();f.read();assert.equal(f.calls(),0);
  const recipient=fixture([]);recipient.nodes.push(f.nodes[0]);assert.equal(recipient.read().data.editable[0].password,true);assert.equal(f.calls(),0,'private node provenance survives adoption into another reader realm');
});

for(const [source,config] of [
  ['a',{tagName:'A',attrs:{href:'delete'}}],['area',{tagName:'AREA',attrs:{href:'delete'}}],
  ['svg-href',{tagName:'a',namespaceURI:'http://www.w3.org/2000/svg',localName:'a',attrs:{href:'delete'}}],
  ['svg-xlink',{tagName:'a',namespaceURI:'http://www.w3.org/2000/svg',localName:'a',attrs:{'xlink:href':'delete'}}],
])test('post18d destination '+source+' follows the effective base on every read',()=>{
  const f=fixture([]),node=new f.Element(config);f.nodes.push(node);
  f.setBase('https://fixture.test/invoice-1/');const before=f.read().data.rows.find(row=>row.role==='link');
  assert.equal(before.href,'https://fixture.test/invoice-1/delete');
  f.setBase('https://fixture.test/invoice-2/');const after=f.read().data.rows.find(row=>row.role==='link');
  assert.equal(after.href,'https://fixture.test/invoice-2/delete');assert.notEqual(before.href,after.href);
  node.attrs.target='sink';assert.equal(f.read().data.rows.find(row=>row.role==='link').browsing_target,'sink');
});

test('post18d destination target and formtarget inherit the live base target',()=>{
  const f=fixture([]),base=new f.Element({tagName:'BASE',attrs:{target:'first'}}),link=new f.Element({tagName:'A',attrs:{href:'delete'}});f.nodes.push(base,link);
  const form={tagName:'FORM',elements:[],action:'https://fixture.test/delete',method:'post',enctype:'application/x-www-form-urlencoded',target:'',querySelector(){return null;}};
  const submitter=new f.Element({tagName:'BUTTON',type:'submit',form,attrs:{}});
  assert.equal(f.read().data.rows.find(row=>row.role==='link').browsing_target,'first');assert.equal(f.form(form,submitter).browsing_target,'first');
  base.attrs.target='second';assert.equal(f.read().data.rows.find(row=>row.role==='link').browsing_target,'second');assert.equal(f.form(form,submitter).browsing_target,'second');
  submitter.attrs.formtarget='explicit';submitter.formTarget='explicit';assert.equal(f.form(form,submitter).browsing_target,'explicit');
  submitter.attrs.formtarget='';submitter.formTarget='';form.target='ignored';assert.equal(f.form(form,submitter).browsing_target,'second');
  base.attrs.target='unsafe\nname';assert.equal(f.form(form,submitter).browsing_target,'_blank');
});

for(const source of ['form-action','button-formaction','input-formaction'])test('post18d destination '+source+' uses the native resolved action',()=>{
  const f=fixture([]);let base='https://fixture.test/first/';
  const form={tagName:'FORM',elements:[],get action(){return new URL('delete',base).href;},method:'post',enctype:'application/x-www-form-urlencoded',target:'',querySelector(){return null;}};
  const submitter=new f.Element({tagName:source==='input-formaction'?'INPUT':'BUTTON',type:'submit',form,attrs:source==='form-action'?{}:{formaction:'override'}});
  Object.defineProperty(submitter,'formAction',{get(){return new URL('override',base).href;}});
  const path=source==='form-action'?'delete':'override';assert.equal(f.form(form,submitter).action,'https://fixture.test/first/'+path);
  base='https://fixture.test/second/';assert.equal(f.form(form,submitter).action,'https://fixture.test/second/'+path);
  const other={...form,action:'https://fixture.test/other'};submitter.form=other;assert.notEqual(f.form(other,submitter).element,f.form(form,submitter).element);
});

for(const signal of ['name','id','autocomplete','aria-label','placeholder','label'])test('post18d credential signal '+signal+' excludes values before extraction in watched and late documents',()=>{
  for(const watched of [false,true])for(const term of ['Password','PIN','Passcode','one-time code','security code','Passwort','Kennwort','Einmalcode','Sicherheitscode','Bestätigungscode','userPassword','oneTimeCode']){
    const f=fixture([{type:'text',forbidden:true,attrs:signal==='label'?{}:{[signal]:term}}],{watched});
    if(signal==='label')f.nodes[0].labels=[new f.Element({tagName:'LABEL',childNodes:[{nodeType:3,textContent:term}]})];
    const row=f.read().data.rows[0];assert.equal(row.password,true,signal+' '+term);assert.equal(f.calls(),0);
    f.nodes[0].attrs={};f.nodes[0].labels=[];assert.equal(f.read().data.rows[0].password,true,'credential exclusion is sticky');
  }
});

test('post18d late single-line values show filled or empty without reading their value getter',()=>{
  for(const type of ['text','tel','number','unknown'])for(const empty of [false,true]){
    const f=fixture([{type,empty}],{watched:false});f.read();const row=f.command({command:'facts',element:'e1'}).data.target;
    assert.equal(row.value_status,empty?'empty':'filled');assert.equal(row.value,undefined);assert.equal(f.calls(),0);
    assert.doesNotMatch(JSON.stringify(f.read()),/safe visible text/);
    f.command({command:'set_control',generation:'epoch'});f.reinject();f.read();assert.equal(f.command({command:'facts',element:'e1'}).data.target.value,undefined,'late history never upgrades on control or reinjection');
  }
});
test('post18d watched input types and late choices formatted values textarea and editors stay readable',()=>{
  for(const watched of [false,true])for(const type of ['text','tel','number','unknown','checkbox','radio','date','email','url','search']){
    const f=fixture([{type}],{watched}),row=f.read().data.rows[0];
    assert.equal(typeof row.value==='string',watched||!['text','tel','number','unknown'].includes(type),type+' '+watched);
  }
  const f=fixture([{tagName:'TEXTAREA'},{tagName:'DIV',isContentEditable:true,childNodes:[{nodeType:3,textContent:'Editable draft'}]}],{watched:false});
  f.textarea(f.nodes[0]);f.generic(f.nodes[1]);const rows=f.read().data.rows;assert.equal(rows[0].value,'safe visible text');assert.equal(rows[1].value,'Editable draft');
});
test('post18d credential checks precede late filled-state and preserve ordinary shipping labels',()=>{
  const f=fixture([{attrs:{name:'PIN'}}],{watched:false});Object.defineProperty(f.nodes[0],'textLength',{get(){assert.fail('credential filled state was read');}});
  assert.equal(f.read().data.rows[0].password,true);assert.equal(f.calls(),0);
  const ordinary=fixture([{attrs:{name:'shipping',placeholder:'Spin count'}}]);assert.equal(ordinary.read().data.rows[0].password,undefined);
});

test('post18d typed read approval is one call credential-free and never changes ordinary reads',()=>{
  const f=fixture([{attrs:{'aria-label':'Draft'}},{attrs:{}},{attrs:{name:'password'},forbidden:true}],{watched:false});
  const before=f.read();assert.doesNotMatch(JSON.stringify(before),/safe visible text/);assert.equal(f.calls(),0);
  const expected=f.command({command:'typed_fields'}).data;assert.equal(expected.fields.length,2);assert.equal(expected.fields[1].label,'single-line field 2');
  assert.equal(f.command({command:'read_typed_fields',operation:'first',expected}).ok,false);assert.equal(f.calls(),0);
  const approved=f.command({command:'read_typed_fields',approved:true,operation:'first',expected});assert.equal(approved.ok,true,JSON.stringify(approved));
  assert.equal(approved.data.fields.length,2);assert.equal(f.calls(),2);assert.equal(approved.data.fields[0].value,'safe visible text');
  assert.equal(f.command({command:'read_typed_fields',approved:true,operation:'first',expected}).ok,false);assert.equal(f.calls(),2);
  assert.doesNotMatch(JSON.stringify(f.read()),/safe visible text/);assert.equal(f.calls(),2);
});
test('post18d typed field additions relabelling credential changes and document replacement refuse before values',()=>{
  for(const change of ['added','relabelled','credential','document']){
    const f=fixture([{attrs:{'aria-label':'Draft'}}],{watched:false}),expected=f.command({command:'typed_fields'}).data;
    if(change==='added')f.nodes.push(new f.Element({tagName:'INPUT',namespaceURI:'http://www.w3.org/1999/xhtml',localName:'input'}));
    if(change==='relabelled')f.nodes[0].attrs['aria-label']='Changed draft';
    if(change==='credential')f.nodes[0].attrs.name='Passwort';
    if(change==='document')expected.document+='changed';
    const result=f.command({command:'read_typed_fields',approved:true,operation:'changed',expected});assert.equal(result.ok,false,change);assert.match(result.error,/field|document/);assert.equal(f.calls(),0);
  }
});

test('post18d late reload warning never extracts unapproved typed text to compare defaults',()=>{
  const f=fixture([{type:'text',forbidden:true}],{watched:false});
  const state=f.command({command:'reload_state'});assert.equal(state.ok,true,JSON.stringify(state));assert.equal(state.data.unsaved,true);assert.equal(f.calls(),0);
});

test('post18d hidden late fields disclose presence without extracting a value or claiming emptiness',()=>{
  const f=fixture([{type:'hidden',forbidden:true}],{watched:false});f.read();
  const row=f.command({command:'facts',element:'e1'}).data.target;assert.equal(row.value,undefined);assert.equal(row.value_status,'not_read');assert.equal(f.calls(),0);
});
