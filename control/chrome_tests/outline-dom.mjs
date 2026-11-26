// Shared DOM double used by the outline suite and X1 review-probe regressions.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
export const XHTML='http://www.w3.org/1999/xhtml',BASE='https://fixture.test/';
// nodes.py: ROLES and the keys a node may hold.
const ROLES=new Set('main navigation banner contentinfo complementary region search form article group list listitem table row cell columnheader rowheader figure img separator toolbar dialog alertdialog alert status tooltip progressbar frame h1 h2 h3 h4 h5 h6 p text link button textbox searchbox combobox listbox option checkbox radio radiogroup switch slider spinbutton tab tablist tabpanel menu menubar menuitem menuitemcheckbox menuitemradio tree treeitem grid gridcell password'.split(' '));
const KEYS=new Set('id parent role name text value unread filled error states href method action hidden option_count chosen options title frame fingerprint'.split(' '));

export function page(build,{watched=true}={}){
  class NativeNode{get baseURI(){return BASE;}}
  NativeNode.TEXT_NODE=3;
  class Text extends NativeNode{constructor(value){super();this.nodeType=3;this.textContent=value;}}
  const within=node=>node.childNodes.flatMap(child=>child.nodeType===1?[child,...within(child)]:[]);
  const matches=(element,selector)=>selector==='*'||selector.split(',').some(part=>{
    const attribute=part.match(/^(\w*)\[([\w-]+)\]$/);
    return attribute?(!attribute[1]||element.localName===attribute[1])&&element.hasAttribute(attribute[2]):element.localName===part;
  });
  const select=(node,selector)=>within(node).filter(element=>matches(element,selector));
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
    get firstElementChild(){return this.childNodes.find(node=>node.nodeType===1)||null;}
    get text(){
      const optionText=node=>node.nodeType===3?node.textContent:node.localName==='script'?'':node.childNodes.map(optionText).join('');
      return optionText(this).replace(/[\t\n\f\r ]+/g,' ').replace(/^ | $/g,'');
    }
    get value(){
      if(this.attrs.type==='password'||this.secret)throw Error('A PROTECTED VALUE WAS READ');
      return this.attrs.value??(this.localName==='option'?this.text:'');
    }
    getRootNode(){return this.parentElement?this.parentElement.getRootNode():this.root||document;}
    matches(selector){
      if(selector===':disabled')return this.hasAttribute('disabled');
      if(selector.startsWith('dialog[open]'))return this.localName==='dialog'&&this.hasAttribute('open')||['dialog','alertdialog'].includes(this.attrs.role)&&this.attrs['aria-modal']==='true';
      return matches(this,selector);
    }
    querySelectorAll(selector){return select(this,selector);}
    querySelector(selector){return select(this,selector)[0]||null;}
    // A box from $box (brief 28a's reveal and facts), else a small one on screen.
    getBoundingClientRect(){const {x=1,y=1,width=10,height=10}=this.box||{};return {x,y,width,height,top:y,left:x,right:x+width,bottom:y+height};}
    scrollIntoView(options){(this.scrolled??=[]).push(options);}
    contains(node){for(let ancestor=node;ancestor;ancestor=ancestor.parentElement)if(ancestor===this)return true;return false;}
    // Tags and [attribute=value] parts, as the reader asks for a page dialog.
    closest(selector){
      const parts=selector.split(',').map(part=>part.match(/^\[([\w-]+)=([\w-]+)\]$/)||part);
      for(let node=this;node;node=node.parentElement)if(parts.some(part=>typeof part==='string'?node.localName===part:node.attrs[part[1]]===part[2]))return node;
      return null;
    }
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
  let listener,reader;
  const chrome={dom:{openOrClosedShadowRoot:element=>element.shadowRoot||null},runtime:{id:'fixture',getFrameId:element=>element.frameId??-1,sendMessage:async()=>({}),onMessage:{addListener(fn){listener=fn;},removeListener(){}}}};
  class MutationObserver{observe(){}takeRecords(){return [];}disconnect(){}}
  const context=vm.createContext({document,chrome,crypto:{getRandomValues:array=>array.fill(7)},MutationObserver,TextEncoder,URL,console,Element,HTMLElement:Element,HTMLInputElement,HTMLTextAreaElement,HTMLSelectElement,HTMLButtonElement,HTMLAnchorElement,HTMLFormElement,Node:NativeNode,
    getComputedStyle:element=>({display:element.attrs.style==='display:none'||element.localName==='area'?'none':'block',visibility:'visible',webkitTextSecurity:'none',whiteSpace:element.localName==='pre'?'pre':'normal'}),
    [Symbol.for('aresos.chrome.document-start.v1')]:watched,[Symbol.for('aresos.chrome.guard.v2')]:{watch(){},reader(api){reader=api;},protectedPeer:()=>false},
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
      // Brief 28a, item 2: every node carries its fingerprint. Its own tests
      // are in fingerprint.test.mjs; the shapes below are brief 28's.
      assert.match(node.fingerprint,/^[0-9a-f]{32}$/);
    }
    for(const node of result.data.nodes)delete node.fingerprint;
    return result.data;
  };
  return {run,outline,body,h,key:element=>reader.id(element)};
}

