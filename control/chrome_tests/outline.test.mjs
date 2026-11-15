// Brief 28, item 1: the reader's `outline`, `options` and `page_state`, run in
// a VM against a small tree of DOM doubles. A protected value's getter throws,
// so a test fails when the reader touches one.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const XHTML='http://www.w3.org/1999/xhtml',BASE='https://fixture.test/';
// nodes.py: ROLES and the keys a node may hold.
const ROLES=new Set('main navigation banner contentinfo complementary region search form article group list listitem table row cell columnheader rowheader figure img separator toolbar dialog alertdialog alert status tooltip progressbar frame h1 h2 h3 h4 h5 h6 p text link button textbox searchbox combobox listbox option checkbox radio radiogroup switch slider spinbutton tab tablist tabpanel menu menubar menuitem menuitemcheckbox menuitemradio tree treeitem grid gridcell password'.split(' '));
const KEYS=new Set('id parent role name text value unread filled error states href method action hidden option_count chosen options title frame'.split(' '));

function page(build,{watched=true}={}){
  class NativeNode{get baseURI(){return BASE;}}
  NativeNode.TEXT_NODE=3;
  class Text extends NativeNode{constructor(value){super();this.nodeType=3;this.textContent=value;}}
  const within=node=>node.childNodes.flatMap(child=>child.nodeType===1?[child,...within(child)]:[]);
  const select=(node,selector)=>within(node).filter(element=>selector==='*'||selector.split(',').some(part=>part==='[contenteditable]'?element.hasAttribute('contenteditable'):element.localName===part));
  let document;
  class Element extends NativeNode{
    constructor(tag,attrs={},children=[]){
      super();this.nodeType=1;this.localName=tag;this.tagName=tag.toUpperCase();this.namespaceURI=XHTML;this.isConnected=true;this.attrs={};this.childNodes=[];this.parentElement=null;this.root=null;
      for(const [key,value] of Object.entries(attrs)){if(key.startsWith('$'))this[key.slice(1)]=value;else this.attrs[key]=String(value);}
      for(const child of children)this.append(child);
    }
    append(child){const node=typeof child==='string'?new Text(child):child;node.parentElement=this;this.childNodes.push(node);return node;}
    getAttribute(name){if(this.nodeType!==1)throw TypeError('Illegal invocation');return Object.hasOwn(this.attrs,name)?this.attrs[name]:null;}
    hasAttribute(name){return this.getAttribute(name)!==null;}
    getAttributeNS(){return null;}
    hasAttributeNS(){return false;}
    get hidden(){return this.hasAttribute('hidden');}
    get isContentEditable(){return this.getAttribute('contenteditable')==='true';}
    get type(){return this.localName==='input'?this.attrs.type||'text':this.localName==='textarea'?'textarea':this.localName==='select'?'select-one':undefined;}
    get labels(){const found=[];for(let node=this.parentElement;node;node=node.parentElement)if(node.localName==='label')found.push(node);return found;}
    get options(){return this.childNodes.filter(node=>node.localName==='option');}
    get selected(){return this.hasAttribute('selected');}
    get checked(){return this.hasAttribute('checked');}
    get required(){return this.hasAttribute('required');}
    get readOnly(){return this.hasAttribute('readonly');}
    get multiple(){return this.hasAttribute('multiple');}
    get size(){return Number(this.attrs.size||0);}
    get open(){return this.hasAttribute('open');}
    get files(){return [];}
    get value(){
      if(this.attrs.type==='password'||this.secret)throw Error('A PROTECTED VALUE WAS READ');
      return this.attrs.value??(this.localName==='option'?this.childNodes.map(node=>node.textContent).join(''):'');
    }
    getRootNode(){return this.parentElement?this.parentElement.getRootNode():this.root||document;}
    matches(selector){
      if(selector===':disabled')return this.hasAttribute('disabled');
      if(selector.startsWith('dialog[open]'))return this.localName==='dialog'&&this.hasAttribute('open')||['dialog','alertdialog'].includes(this.attrs.role)&&this.attrs['aria-modal']==='true';
      return false;
    }
    querySelectorAll(selector){return select(this,selector);}
  }
  class HTMLInputElement extends Element{}
  class HTMLTextAreaElement extends Element{}
  class HTMLSelectElement extends Element{}
  class HTMLButtonElement extends Element{}
  class HTMLAnchorElement extends Element{get href(){return new URL(this.attrs.href,BASE).href;}}
  class HTMLFormElement extends Element{
    get elements(){return within(this).filter(element=>['input','textarea','select','button'].includes(element.localName));}
    get action(){return new URL(this.attrs.action||'',BASE).href;}
    get method(){return (this.attrs.method||'get').toLowerCase();}
    get enctype(){return '';}
    get target(){return '';}
  }
  const classes={input:HTMLInputElement,textarea:HTMLTextAreaElement,select:HTMLSelectElement,button:HTMLButtonElement,a:HTMLAnchorElement,form:HTMLFormElement};
  const h=(tag,attrs={},...children)=>new (classes[tag]||Element)(tag,attrs,children);
  // A shadow root for a host: its elements have no parent element, as in a page.
  h.shadow=(host,...children)=>{
    const root={host,childNodes:[],getElementById:()=>null,querySelectorAll:selector=>select(root,selector)};
    for(const child of children){child.root=root;root.childNodes.push(child);}
    host.shadowRoot=root;return host;
  };
  const body=h('body',{},...build(h)),top=h('html',{},h('head',{},h('title',{},'In the head')),body);
  document={title:'Fixture',readyState:'complete',body,documentElement:top,childNodes:[top],
    implementation:{createHTMLDocument(){return {importNode:element=>({validity:{valueMissing:!element.attrs.value}})};}},
    getElementById:key=>key?within(document).find(element=>element.attrs.id===key)||null:null,querySelectorAll:selector=>select(document,selector),querySelector:()=>null,addEventListener(){}};
  let listener;
  const chrome={dom:{openOrClosedShadowRoot:element=>element.shadowRoot||null},runtime:{id:'fixture',getFrameId:element=>element.frameId??-1,sendMessage:async()=>({}),onMessage:{addListener(fn){listener=fn;},removeListener(){}}}};
  class MutationObserver{observe(){}takeRecords(){return [];}disconnect(){}}
  const context=vm.createContext({document,chrome,crypto:{getRandomValues:array=>array.fill(7)},MutationObserver,TextEncoder,URL,console,Element,HTMLElement:Element,HTMLInputElement,HTMLTextAreaElement,HTMLSelectElement,HTMLButtonElement,HTMLAnchorElement,HTMLFormElement,Node:NativeNode,
    getComputedStyle:element=>({display:element.attrs.style==='display:none'?'none':'block',visibility:'visible',webkitTextSecurity:'none',whiteSpace:element.localName==='pre'?'pre':'normal'}),
    [Symbol.for('aresos.chrome.document-start.v1')]:watched,[Symbol.for('aresos.chrome.guard.v2')]:{watch(){},reader(){},protectedPeer:()=>false},
    origin:'https://fixture.test',location:{href:BASE+'page'},scrollX:0,scrollY:120.4,innerWidth:100,innerHeight:100});
  vm.runInContext(fs.readFileSync('control/chrome/extension/reader.js','utf8'),context);
  assert.equal(typeof listener,'function','the reader installed');
  const run=message=>{let result;listener(message,{id:'fixture'},value=>result=value);return JSON.parse(JSON.stringify(result));};
  const outline=()=>{
    const result=run({command:'outline'});assert.equal(result.ok,true,JSON.stringify(result));
    // The contract of nodes.py, on every reply: known keys, numbers as ids, a parent before its children.
    const seen=new Set();
    for(const node of result.data.nodes){
      assert.deepEqual(Object.keys(node).filter(key=>!KEYS.has(key)),[]);
      assert.ok(Number.isInteger(node.id)&&node.id>=1&&!seen.has(node.id));assert.ok(node.parent===null||seen.has(node.parent));seen.add(node.id);
      assert.ok(ROLES.has(node.role),String(node.role));
      for(const part of node.text||[])assert.ok(typeof part==='string'||result.data.nodes.some(child=>child.id===part&&child.parent===node.id));
      if(node.unread||node.role==='password'){assert.deepEqual(['value','text','chosen','options'].filter(key=>key in node),[]);assert.ok(!result.data.nodes.some(child=>child.parent===node.id));}
    }
    return result.data;
  };
  return {run,outline,body,h};
}

test('inline formatting is text of its element, and only the link stands between the runs',()=>{
  const f=page(h=>[h('p',{},'Order ',h('b',{},'confirmed'),' today, see ',h('i',{},'the ',h('a',{href:'/t'},'timetable')),'.')]);
  const data=f.outline();
  assert.deepEqual(data.nodes,[
    {id:1,parent:null,role:'p',text:['Order confirmed today, see the ',2,'.']},
    {id:2,parent:1,role:'link',name:'timetable',href:'https://fixture.test/t',text:['timetable']}]);
  assert.deepEqual([data.watched,data.url,data.title,data.origin,data.scroll,data.height,data.omitted],[true,BASE+'page','Fixture','https://fixture.test',120,0,0]);
  assert.match(data.document,/^[0-9a-f]{32}$/);assert.match(data.reader,/^[0-9a-f]{32}$/);
});

test('a role comes from the list or the tag, never from a page\'s own string',()=>{
  const f=page(h=>[
    h('div',{role:'h1 injected'},'A'),h('div',{role:'password'},'B'),h('span',{role:'BUTTON'},'Go'),h('div',{role:'link\n"evil'},'C'),
    h('div',{role:'heading','aria-level':'3'},'D'),h('nav',{},h('a',{href:'/x'},'X')),h('section',{},'plain'),h('section',{'aria-label':'Named'},'in'),
    h('table',{},h('tr',{},h('th',{scope:'row'},'R'),h('th',{},'H'),h('td',{},'c')))]);
  const nodes=f.outline().nodes;
  assert.deepEqual(nodes.map(node=>node.role),['text','text','button','link','h3','navigation','link','text','region','table','row','rowheader','columnheader','cell']);
  assert.deepEqual(nodes[2],{id:nodes[2].id,parent:null,role:'button',name:'Go',text:['Go']});
  assert.deepEqual(nodes[8],{id:nodes[8].id,parent:null,role:'region',name:'Named',text:['in']});
  assert.ok(!JSON.stringify(nodes.map(node=>node.role)).includes('evil'));
});

test('a form: labels, hidden names, states, an error text once, a list field, and password fields as leaves',()=>{
  const f=page(h=>[h('form',{'aria-label':'Account',method:'post',action:'/account?step=2'},
    h('input',{type:'hidden',name:'csrf',value:'x'}),
    h('label',{},'Line 0 ',h('input',{name:'line0',value:'Value 0'})),
    h('label',{},h('input',{type:'checkbox',name:'news',checked:''}),' News'),
    h('label',{},'Country ',h('select',{name:'country'},...Array.from({length:60},(_,index)=>h('option',{value:'c'+index,...(index===7?{selected:''}:{})},'Country '+index)))),
    h('label',{},'Email ',h('input',{type:'email',name:'email',value:'not-an-address',required:'','aria-invalid':'true','aria-describedby':'email-error'})),
    h('span',{id:'email-error'},'Enter a valid address'),
    h('label',{},'Password ',h('input',{type:'password',name:'password',value:'never'})),
    h('label',{},'One-time code ',h('input',{name:'one_time',autocomplete:'one-time-code',value:'123456',$secret:true})),
    h('button',{type:'submit'},'Save'))]);
  const data=f.outline(),nodes=data.nodes,options=Array.from({length:60},(_,index)=>({label:'Country '+index,value:'c'+index,chosen:index===7,disabled:false}));
  assert.deepEqual(nodes,[
    {id:1,parent:null,role:'form',name:'Account',method:'post',action:'https://fixture.test/account?step=2',hidden:['csrf']},
    {id:2,parent:1,role:'text',text:['Line 0 ',3]},{id:3,parent:2,role:'textbox',name:'Line 0',value:'Value 0'},
    {id:4,parent:1,role:'text',text:[5,' News']},{id:5,parent:4,role:'checkbox',name:'News',states:['checked']},
    {id:6,parent:1,role:'text',text:['Country ',7]},{id:7,parent:6,role:'combobox',name:'Country',option_count:60,chosen:'Country 7',options:options.slice(0,50)},
    {id:8,parent:1,role:'text',text:['Email ',9]},{id:9,parent:8,role:'textbox',name:'Email',value:'not-an-address',states:['required','invalid'],error:'Enter a valid address'},
    {id:10,parent:1,role:'text',text:['Password ',11]},{id:11,parent:10,role:'password',name:'Password',unread:true},
    {id:12,parent:1,role:'text',text:['One-time code ',13]},{id:13,parent:12,role:'password',name:'One-time code',unread:true},
    {id:14,parent:1,role:'button',name:'Save',text:['Save']}]);
  // `options` returns every option of one list field, by the number the outline gave,
  // and only to the document and reader instance that gave it.
  const from={document:data.document,reader:data.reader};
  assert.deepEqual(f.run({command:'options',element:7,...from}),{ok:true,data:options});
  for(const element of [3,11,'e7',0,999,null]){const refused=f.run({command:'options',element,...from});assert.equal(refused.ok,false);assert.match(refused.error,/^stale_reference: /);}
  for(const other of [{},{document:data.document},{reader:data.reader},{...from,reader:'0'.repeat(32)},{...from,document:'0'.repeat(32)}]){
    const refused=f.run({command:'options',element:7,...other});assert.equal(refused.ok,false,JSON.stringify(other));assert.match(refused.error,/^stale_reference: /);
  }
});

test('in a document the reader has not watched, a typed field says only filled or empty',()=>{
  const f=page(h=>[
    h('input',{'aria-label':'Code',value:'typed',$secret:true}),h('input',{'aria-label':'Nickname',$secret:true}),
    h('textarea',{'aria-label':'Notes',value:'draft',$secret:true}),h('input',{type:'date','aria-label':'Born',value:'2001-02-03'}),
    h('input',{type:'checkbox','aria-label':'Tick',checked:''})],{watched:false});
  const data=f.outline();
  assert.equal(data.watched,false);
  assert.deepEqual(data.nodes.map(({id,parent,...rest})=>rest),[
    {role:'textbox',name:'Code',unread:true,filled:true},{role:'textbox',name:'Nickname',unread:true,filled:false},
    {role:'textbox',name:'Notes',unread:true,filled:true},{role:'textbox',name:'Born',value:'2001-02-03'},
    {role:'checkbox',name:'Tick',states:['checked']}]);
  assert.equal(f.run({command:'page_state'}).ok,true);
});

test('hidden parts, scripts and the head are left out; a shadow root and a pre are read; a modal hides the rest',()=>{
  const f=page(h=>[h('p',{hidden:''},'no'),h('p',{style:'display:none'},'no'),h('script',{},'x()'),h('p',{},'yes'),
    h.shadow(h('div',{}),h('p',{},'in the shadow root')),h('pre',{},'a\n  b')]);
  assert.deepEqual(f.outline().nodes.map(({role,text})=>[role,text]),[['p',['yes']],['p',['in the shadow root']],['p',['a\n  b']]]);
  const modal=page(h=>[h('p',{},'behind'),h('dialog',{open:''},h('p',{},'inside'))]);
  assert.deepEqual(modal.outline().nodes.map(({role,text})=>[role,text]),[['dialog',undefined],['p',['inside']]]);
});

test('beyond 20,000 nodes the reply says how many were left out',()=>{
  const f=page(h=>Array.from({length:20001},(_,index)=>h('p',{},'Paragraph '+index)));
  const data=f.outline();
  assert.equal(data.nodes.length,20000);assert.equal(data.omitted,1);assert.deepEqual(data.nodes.at(-1).text,['Paragraph 19999']);
  // The background passes what is left of the tab's nodes; a parent that is cut takes its children along.
  const small=page(h=>[h('p',{},'One'),h('ul',{},h('li',{},'Two'),h('li',{},'Three')),h('p',{},'Four')]);
  const cut=limit=>{const result=small.run({command:'outline',limit});assert.equal(result.ok,true,JSON.stringify(result));return [result.data.nodes.map(node=>node.role),result.data.omitted];};
  assert.deepEqual(cut(3),[['p','list','listitem'],2]);assert.deepEqual(cut(1),[['p'],4]);assert.deepEqual(cut(0),[[],5]);
  for(const limit of [5,20001,-1,1.5,'2',null])assert.deepEqual(cut(limit),[['p','list','listitem','listitem','p'],0],String(limit));
});

test('page_state moves with a typed value and a tick, and carries no value',()=>{
  const f=page(h=>[h('input',{'aria-label':'A',value:'one'}),h('input',{type:'checkbox','aria-label':'B'}),h('input',{type:'password',value:'never'})]);
  const state=()=>{const result=f.run({command:'page_state'});assert.equal(result.ok,true,JSON.stringify(result));return result.data;};
  const first=state();
  assert.deepEqual(Object.keys(first).sort(),['address','document','fields','origin','reader','ready','revision']);assert.equal(first.origin,'https://fixture.test');
  assert.match(first.fields,/^[0-9a-f]{64}$/);assert.match(first.address,/^[0-9a-f]{64}$/);assert.deepEqual([first.ready,first.revision],[true,0]);
  assert.deepEqual(state(),first);
  f.body.childNodes[0].attrs.value='two words';const typed=state();
  f.body.childNodes[1].attrs.checked='';const ticked=state();
  assert.equal(new Set([first.fields,typed.fields,ticked.fields]).size,3);
  assert.deepEqual([typed.address,ticked.address],[first.address,first.address]);
  assert.ok(!JSON.stringify([first,typed,ticked]).includes('two words'));
});
