import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {execFileSync} from 'node:child_process';
import {mixedRows} from '../chrome/ci/guard-matrix.mjs';

const policy=JSON.parse(fs.readFileSync('control/chrome/extension/policy.js','utf8').match(/\{[\s\S]*\}/)[0]);

function fixture({relay=false,activate=true,link=true,browserDOM=false,nativeShadows=false,retarget=false,dialogs=false,nativeNodeKinds=false,clipboard=false,onDialogBoundary=()=>{}}={}) {
  const windowListeners=new Map(),reports=[],arrivals=[],nodes=[],bridgeDetails=[];let now=0;
  class Event {
    constructor(type,options={}) {Object.assign(this,{type,cancelable:true,defaultPrevented:false,stopped:false,eventPhase:0,isTrusted:false,...options});}
    preventDefault(){if(this.cancelable)this.defaultPrevented=true;}
    stopImmediatePropagation(){this.stopped=true;}
    composedPath(){const target=this.visibleTarget||this.target,root=target?.getRootNode?.();return root&&root!==target?[target,root]:[target];}
  }
  class CustomEvent extends Event {constructor(type,options={}){super(type,options);this.detail=nativeShadows&&type==='aresos-relay-meta'?structuredClone(options.detail):options.detail;if(type==='aresos-page-call-v2')bridgeDetails.push(options.detail);}}
  class EventTarget {
    listeners=new Map();
    addEventListener(type,fn){if(!this.listeners.has(type))this.listeners.set(type,[]);this.listeners.get(type).push(fn);}
    removeEventListener(type,fn){this.listeners.set(type,(this.listeners.get(type)||[]).filter(value=>value!==fn));}
    dispatchEvent(event){
      event.target=this;event.eventPhase=1;event.stopped=false;
      try {
        const localRoot=this.getRootNode?.();
        event.visibleTarget=localRoot?.mode==='closed'?localRoot.host:null;
        for(const fn of localRoot?.host&&event.composed!==true?[]:windowListeners.get(event.type)||[]){fn(event);if(event.stopped)return !event.defaultPrevented;}
        event.visibleTarget=null;
        if(localRoot?.host)for(const fn of localRoot.listeners.get(event.type)||[]){fn(event);if(event.stopped)return !event.defaultPrevented;}
        event.eventPhase=2;
        for(const fn of this.listeners.get(event.type)||[]){fn(event);if(event.stopped)break;}
        return !event.defaultPrevented;
      } finally {event.eventPhase=0;}
    }
  }
  const originalDispatch=EventTarget.prototype.dispatchEvent;
  const shadowHosts=new WeakMap(),hostShadows=new WeakMap(),parents=new WeakMap(),children=new WeakMap();class Node extends EventTarget {
    get parentNode(){return parents.get(this)||null;}set parentNode(value){parents.set(this,value);}
    get previousSibling(){const parent=parents.get(this),list=parent&&children.get(parent)||[];return list[list.indexOf(this)-1]||null;}
    get childNodes(){return children.get(this)||[];}set childNodes(value){children.set(this,value);}
    get host(){return shadowHosts.get(this);}set host(value){shadowHosts.set(this,value);hostShadows.set(value,this);}
    getRootNode(options={}){const root=this.root??this.ownerDocument??document;return options.composed&&root.host?root.host.getRootNode(options):root;}
  }
  Node.prototype.appendChild=function(node){node.parentNode=this;node.root=this.getRootNode();this.childNodes=[...this.childNodes,node];return node;};
  Node.prototype.append=function(...nodes){for(const node of nodes)Node.prototype.appendChild.call(this,node);};
  const nativeAppend=Node.prototype.appendChild,markup=new WeakMap();
  const nativeHTMLSetter=function(value){markup.set(this,String(value));};Object.defineProperty(Node.prototype,'innerHTML',{configurable:true,get(){return markup.get(this)||'';},set:nativeHTMLSetter});
  class Element extends Node {
    isConnected=true;tagName='DIV';type='';textContent='';form=null;role='';
    constructor(){super();this.ownerDocument=document;nodes.push(this);}
    get childNodes(){return [{nodeType:3,textContent:this.textContent}];}
    closest(){return this;}
    getAttribute(name){return this[name]??null;}
    setAttribute(name,value){this[name]=String(value);}
    removeAttribute(name){delete this[name];}
    getAttributeNS(ns,name){return this.namespaceAttrs?.[ns+' '+name]??null;}
    setAttributeNS(ns,name,value){(this.namespaceAttrs??={})[ns+' '+name.split(':').at(-1)]=String(value);}
    removeAttributeNS(ns,name){delete this.namespaceAttrs?.[ns+' '+name];}
    matches(){return false;}
    querySelector(){return null;}
    attachShadow(options={}){const root=new Node();root.root=root;root.ownerDocument=this.ownerDocument;root.host=this;root.mode=options.mode;return root;}
    appendChild(node){node.parentNode=this;this.firstElementChild??=node;return node;}
  }
  class HTMLElement extends Element {click(){originalDispatch.call(this,new Event('click'));}get onclick(){return this.fixtureClick;}set onclick(handler){this.fixtureClick=handler;if(!this.fixtureClickListener){this.fixtureClickListener=event=>this.fixtureClick?.call(this,event);nativeListen.call(this,'click',this.fixtureClickListener);}}}
  class SVGElement extends Element {}
  class HTMLInputElement extends HTMLElement {}
  class HTMLFormElement extends HTMLElement {
    tagName='FORM'; method='post';action='/receive';valid=true;
    submit(){arrivals.push('native');}
    requestSubmit(submitter){if(!this.valid)return;const event=new Event('submit',{submitter,isTrusted:true});if(originalDispatch.call(this,event))arrivals.push('event');}
  }
  const originalRequestSubmit=HTMLFormElement.prototype.requestSubmit,nativeAttach=Element.prototype.attachShadow,nativeListen=EventTarget.prototype.addEventListener;
  class Document extends EventTarget {createElement(){const node=new HTMLElement();node.root=node;node.isConnected=false;node.parentNode=null;return node;}}
  if(nativeNodeKinds){Object.defineProperty(Node.prototype,'nodeType',{get(){return this.fixtureKind??1;}});Node.prototype.cloneNode=function(){const clone=new Node();clone.fixtureKind=this.fixtureKind??1;clone.ownerDocument=document;clone.root=clone;return clone;};}
  const document=new Document();document.getElementById=key=>document.labels?.[key];
  if(!relay)document.createElement=undefined;
  const window={addEventListener(type,fn){if(!windowListeners.has(type))windowListeners.set(type,[]);windowListeners.get(type).push(fn);},removeEventListener(type,fn){windowListeners.set(type,(windowListeners.get(type)||[]).filter(value=>value!==fn));}};
  class MessageChannel {port1={close(){}};port2={postMessage:token=>setImmediate(()=>this.port1.onmessage?.({data:token})),close(){}};}
  class AbstractRange {}
  const rangeNodes=new WeakMap();class StaticRange extends AbstractRange {constructor(options){super();if([2,10].includes(options.startContainer.fixtureKind))throw new DOMException('Invalid range node','InvalidNodeTypeError');rangeNodes.set(this,options.startContainer);}get startContainer(){if(!rangeNodes.has(this))throw TypeError('Invalid StaticRange');return rangeNodes.get(this);}}
  class InputEvent extends Event {constructor(type,options={}){super(type,options);this.ranges=options.targetRanges?Array.from(options.targetRanges):[];}getTargetRanges(){return retarget?this.ranges.filter(range=>!range.startContainer.getRootNode().host):this.ranges;}}
  const clipboardCalls=[],clipboardOutcome={value:undefined,error:null,synchronous:false};
  class Clipboard {
    write(value){clipboardCalls.push({route:'write',receiver:this,value});if(clipboardOutcome.synchronous)throw clipboardOutcome.error;return clipboardOutcome.error?Promise.reject(clipboardOutcome.error):Promise.resolve(clipboardOutcome.value);}
    writeText(value){clipboardCalls.push({route:'writeText',receiver:this,value});if(clipboardOutcome.synchronous)throw clipboardOutcome.error;return clipboardOutcome.error?Promise.reject(clipboardOutcome.error):Promise.resolve(clipboardOutcome.value);}
    read(){throw Error('Clipboard read is forbidden');}readText(){throw Error('Clipboard read is forbidden');}
  }
  const clipboardObject=new Clipboard(),nativeClipboard={write:Clipboard.prototype.write,writeText:Clipboard.prototype.writeText};
  const globals={window,document,...(clipboard?{Clipboard,navigator:{clipboard:clipboardObject}}:{}),performance:{now:()=>now},setTimeout,MessageChannel,Symbol,Event,CustomEvent,EventTarget,Node,DocumentFragment:Node,Element,HTMLElement,SVGElement,HTMLInputElement,HTMLFormElement,DOMException,URL,TextDecoder,Uint8Array,...(relay?{AbstractRange,StaticRange,InputEvent}:{}),...(nativeShadows?{Document,ShadowRoot:Node,chrome:{dom:{openOrClosedShadowRoot:host=>{if(!(host instanceof HTMLElement))throw TypeError('chrome.dom requires an HTMLElement');return hostShadows.get(host);}}}}:browserDOM?{Document}:{})};
  const dialogCalls=[],dialogReports=[],dialogValues=[],dialogValue=value=>value===undefined?'':`${value}`;if(dialogs)Object.assign(globals,{alert:({alert(value){dialogValues.push([dialogValue(value)]);dialogCalls.push('alert');}}).alert,confirm:({confirm(value){dialogValues.push([dialogValue(value)]);dialogCalls.push('confirm');return true;}}).confirm,prompt:({prompt(value,initial){dialogValues.push([dialogValue(value),dialogValue(initial)]);dialogCalls.push('prompt');return 'native response';}}).prompt});const nativeDialogs=dialogs?{alert:globals.alert,confirm:globals.confirm,prompt:globals.prompt}:{};
  let guard;const isolated=vm.createContext({...globals,fixtureDialogPause:()=>onDialogBoundary(guard)});
  vm.runInContext(fs.readFileSync('control/chrome/extension/guard.js','utf8').replace('debugger;','fixtureDialogPause();'),isolated);
  guard=vm.runInContext("globalThis[Symbol.for('aresos.chrome.guard.v2')]",isolated);
  document.defaultView={[Symbol.for('aresos.chrome.guard.v2')]:guard};
  const ids=new Map(), elements=new Map();let sequence=0;
  function id(node){if(!ids.has(node)){const key='e'+(++sequence);ids.set(node,key);elements.set(key,node);}return ids.get(node);}
  function name(node){const labels=(node['aria-labelledby']||'').split(/\s+/).map(key=>document.getElementById(key)).filter(Boolean);return labels.length ? labels.map(label=>label.textContent).join(' ') : node['aria-label'] || node.labels?.map(label=>label.textContent).join(' ') || node.textContent;}
  guard.reader({dialog:(...value)=>dialogReports.push(value),document:'document-1',id,element:key=>elements.get(key),target:node=>({name:name(node),title:node.title,role:node.role,password:!!node.password,submit:!!node.form && node.type==='submit',editable:node instanceof HTMLInputElement}),form:(node,button)=>{const form=node.form || (node.tagName==='FORM' ? node:null);return form ? {method:button?.formmethod || form.method,search:form.role==='search',action:button?.formAction || form.action,encoding:form.encoding||'application/x-www-form-urlencoded',target:form.target||'',fields:nodes.filter(node=>node.form===form).map(node=>({type:node.type,label:name(node)}))}:null;}});
  const main=vm.createContext({...globals});
  const nativeFunctions=[HTMLFormElement.prototype.submit,HTMLFormElement.prototype.requestSubmit,HTMLElement.prototype.click,EventTarget.prototype.dispatchEvent];
  const nativeStrings=nativeFunctions.map(fn=>Function.prototype.toString.call(fn));
  const installed=vm.runInContext(fs.readFileSync('control/chrome/extension/page.js','utf8'),main);
  if(relay){if(link)guard.relay(installed.relay);if(activate)installed.activate();}
  const cleanup=relay?installed.cleanup:installed;
  assert.equal(vm.runInContext("globalThis[Symbol.for('aresos.chrome.page.v1')]",main),undefined);
  assert.equal(vm.runInContext("globalThis[Symbol.for('aresos.chrome.guard.v2')]",main),undefined);
  function arm(target,form,operation=null,conservative=false){guard.arm({generation:'epoch',config:{...policy,conservative},target:id(target),form:form ? id(form):null,operation,primary_submission:false});}
  const api={...guard,resume:(id,operation)=>{const step=reports.find(item=>item.id===id);return guard.resume(id,operation,step?.submitter||step?.element,step?.element);}};
  return {api,guard,clipboard:clipboardObject,nativeClipboard,clipboardCalls,clipboardOutcome,arrivals,dialogCalls,dialogReports,dialogValues,nativeDialogs,bridgeDetails,cleanup,nativeStrings,nativeFunctions,factory:relay?installed:null,Node,SVGElement,EventTarget,get reports(){reports.push(...guard.steps());return reports;},document,HTMLFormElement,HTMLElement,HTMLInputElement,Event,CustomEvent,originalDispatch,originalRequestSubmit,nativeAttach,nativeAppend,nativeListen,nativeHTMLSetter,arm,main,id,advance:milliseconds=>{now+=milliseconds;}};
}

test('private factory creation changes no prototype before its cleanup handle can be retained',()=>{
  const f=fixture({relay:true,activate:false});
  const methods=()=>[f.HTMLFormElement.prototype.submit,f.HTMLFormElement.prototype.requestSubmit,f.HTMLElement.prototype.click,f.EventTarget.prototype.dispatchEvent];
  assert.deepEqual(methods(),f.nativeFunctions);f.factory.activate();assert.ok(methods().every((value,index)=>value!==f.nativeFunctions[index]));
  assert.equal(f.cleanup(),true);assert.deepEqual(methods(),f.nativeFunctions);
});

test('a failed private activation restores every earlier native mutation',()=>{
  const f=fixture({relay:true,activate:false});
  Object.defineProperty(f.EventTarget.prototype,'dispatchEvent',{value:f.nativeFunctions[3],writable:false,configurable:false});
  assert.throws(()=>f.factory.activate(),/redefine|read only/i);assert.equal(f.cleanup(),true);
  assert.deepEqual([f.HTMLFormElement.prototype.submit,f.HTMLFormElement.prototype.requestSubmit,f.HTMLElement.prototype.click,f.EventTarget.prototype.dispatchEvent],f.nativeFunctions);
});

test('real browser startup and late readers never accept the public primitive report bridge',()=>{
  const f=fixture({relay:true,activate:false,link:false,browserDOM:true}),form=new f.HTMLFormElement();
  f.originalDispatch.call(form,new f.CustomEvent('aresos-page-call-v2',{detail:{kind:'native_submit'}}));
  assert.equal(f.arrivals.length,0,'page reports have no native-delivery capability even before relay linking');
});

test('missing native relay support fails before any real-browser prototype mutation',()=>{
  const f=fixture({relay:true,activate:false,browserDOM:true});vm.runInContext('StaticRange=undefined',f.main);
  assert.throws(()=>vm.runInContext(fs.readFileSync('control/chrome/extension/page.js','utf8'),f.main),/private native relay is unavailable/);
  assert.deepEqual([f.HTMLFormElement.prototype.submit,f.HTMLFormElement.prototype.requestSubmit,f.HTMLElement.prototype.click,f.EventTarget.prototype.dispatchEvent],f.nativeFunctions);
});

test('private permit keeps native Event identity and payload without exposing a carrier',()=>{
  const f=fixture({relay:true}),button=new f.HTMLElement();button.textContent='Ordinary control';button.tagName='BUTTON';f.arm(button,null);
  const event=new f.CustomEvent('click',{detail:{unchanged:true}});let same=false,payload;
  button.addEventListener('click',actual=>{same=actual===event;payload=actual.detail;actual.preventDefault();});
  assert.equal(button.dispatchEvent(event),false);assert.equal(same,true);assert.equal(payload,event.detail);assert.equal(event.target,button);assert.equal(f.reports.length,0);
});

test('held and failed private requests never disclose a relay or accept a forged cleanup',()=>{
  const f=fixture({relay:true}),button=new f.HTMLElement(),form=new f.HTMLFormElement();button.textContent='Delete';button.tagName='BUTTON';let delivered=0;button.addEventListener('click',()=>delivered++);f.arm(button,null);
  const event=new f.Event('click');assert.equal(button.dispatchEvent(event),false);assert.notEqual(event.target?.firstElementChild?.ownerDocument,f.document);assert.equal(event.target,undefined);assert.equal(delivered,0);
  f.originalDispatch.call(form,new f.Event('aresos-relay-cleanup'));form.submit();assert.equal(f.arrivals.length,0);assert.equal(f.reports.filter(step=>step.kind==='native_submit').length,1);
  const approved=f.reports.find(step=>step.kind==='native_submit');f.api.resume(approved.id,'one');assert.equal(f.arrivals.length,1);assert.throws(()=>f.api.resume(approved.id,'one'));
  const cached=button.click;f.cleanup();f.guard.dispose();cached.call(button);assert.equal(delivered,1,'cached wrappers also return to native behavior after release');
});

test('private options never run inherited getters, patched enumeration or array iterators',()=>{
  for(const nativeShadows of [false,true]){
  const f=fixture({relay:true,nativeShadows}),button=new f.HTMLElement();button.textContent='Ordinary control';button.tagName='BUTTON';f.arm(button,null);let received=0;button.addEventListener('click',()=>received++);
  if(nativeShadows){button.root=new f.HTMLElement().attachShadow({mode:'closed'});button.parentNode=button.root;button.root.childNodes=[button];}
  vm.runInContext("globalThis.callbacks=0;Object.keys=()=>{callbacks++;throw 'page keys'};for(const key of ['bubbles','composed','get','set','request','target_path']){const description=Object.create(null);description.configurable=true;description.get=function(){callbacks++;throw 'page getter'};Object.defineProperty(Object.prototype,key,description);}Array.prototype[Symbol.iterator]=function(){callbacks++;throw 'page iterator'}",f.main);
  assert.equal(button.dispatchEvent(new f.Event('click')),true);assert.equal(received,1);assert.equal(vm.runInContext('callbacks',f.main),0);
  }
});

test('cleanup preserves a site seal and reports a frozen wrapper without abandoning the other natives',()=>{
  for(const frozen of [false,true]){
    const f=fixture({relay:true});Object.defineProperty(f.HTMLElement.prototype,'click',{configurable:false,writable:!frozen});
    assert.equal(f.cleanup(),!frozen);assert.equal(f.EventTarget.prototype.dispatchEvent,f.originalDispatch,'one frozen property cannot abandon restoration of other methods');
    assert.equal(f.guard.dispose(),!frozen);
    const button=new f.HTMLElement();let delivered=0;button.addEventListener('click',()=>delivered++);button.click();assert.equal(delivered,1,'a retained frozen wrapper has native behavior after deactivation');
  }
});

test('native behavior outside the own composed document includes detached and inert targets',()=>{
  const f=fixture();
  for(const root of [new f.EventTarget(),{inert:'DOMParser'},{inert:'createHTMLDocument'},{inert:'template'}]){
    const node=new f.HTMLElement();node.root=root;let received=0;node.addEventListener('click',event=>{received++;event.preventDefault();});
    f.arm(node,null);assert.equal(node.dispatchEvent(new f.Event('click')),false);assert.equal(received,1);
    node.click();assert.equal(received,2);assert.equal(f.reports.length,0);
  }
  const bus=new f.EventTarget();let delivered=0;bus.addEventListener('message',()=>delivered++);
  assert.equal(bus.dispatchEvent(new f.Event('message')),true);assert.equal(delivered,1);
});

test('native root check cannot be replaced and private cleanup restores the four natives',()=>{
  const f=fixture(),button=new f.HTMLElement();button.tagName='BUTTON';button.textContent='Delete';f.arm(button,null);
  f.Node.prototype.getRootNode=()=>({detached:true});button.click();assert.equal(f.reports.length,1);
  const strings=vm.runInContext('[HTMLFormElement.prototype.submit,HTMLFormElement.prototype.requestSubmit,HTMLElement.prototype.click,EventTarget.prototype.dispatchEvent].map(fn=>Function.prototype.toString.call(fn))',f.main);
  assert.deepEqual(Array.from(strings),f.nativeStrings);
  const wrapped=f.HTMLElement.prototype.click;
  f.cleanup();assert.notEqual(f.HTMLElement.prototype.click,wrapped);assert.equal(f.EventTarget.prototype.dispatchEvent,f.originalDispatch);
  assert.equal(vm.runInContext('globalThis.cleanup',f.main),undefined);
});

test('group2 native submit resumes without checks or submit events',()=>{
  const f=fixture(),form=new f.HTMLFormElement();form.valid=false;
  let handlers=0;form.addEventListener('submit',()=>handlers++);
  f.arm(form,form);form.submit();assert.equal(f.arrivals.length,0);assert.equal(f.reports[0].kind,'native_submit');
  f.api.resume(f.reports[0].id,'op');assert.equal(f.arrivals.length,1);assert.equal(handlers,0);
  assert.throws(()=>f.api.resume(f.reports[0].id,'op'));
});
test('group2 event resume checks fields, handles submit once, and has one further same-form pass',()=>{
  const f=fixture(),form=new f.HTMLFormElement();let handlers=0;
  form.addEventListener('submit',event=>{handlers++;event.preventDefault();form.submit();form.submit();});
  f.arm(form,form);form.requestSubmit();assert.equal(handlers,0);assert.equal(f.arrivals.length,0);
  f.api.resume(f.reports[0].id,'op');assert.equal(handlers,1);assert.equal(f.arrivals.length,1);assert.equal(f.reports.length,2);
});
test('group2 nested requestSubmit cannot regain either consumed allowance',()=>{
  const f=fixture(),form=new f.HTMLFormElement();let handlers=0;
  form.addEventListener('submit',event=>{handlers++;event.preventDefault();form.requestSubmit();});
  f.arm(form,form);form.requestSubmit();f.api.resume(f.reports[0].id,'op');
  assert.equal(handlers,2);assert.equal(f.arrivals.length,0);assert.equal(f.reports.length,2);
});
test('group2 wrapped click and non-cancellable dispatch never deliver or resume',()=>{
  const f=fixture(),button=new f.HTMLElement();button.tagName='BUTTON';button.textContent='Delete';let handlers=0;
  button.addEventListener('click',()=>handlers++);f.arm(button,null);
  button.click();button.dispatchEvent(new f.Event('click',{cancelable:false}));
  assert.equal(handlers,0);assert.equal(f.reports.length,2);assert.equal(f.arrivals.length,0);
  for(const report of f.reports)assert.throws(()=>f.api.resume(report.id,'op'));
});

test('group2 free input in a form has no primary or further submission allowance',()=>{
  const f=fixture(),form=new f.HTMLFormElement(),field=new f.HTMLElement();field.form=form;
  // A durable dispatch ID is kept outside the page's approval mark.
  f.arm(field,form,null);form.submit();form.requestSubmit();
  assert.equal(f.arrivals.length,0);assert.deepEqual(Array.from(f.reports,report=>report.kind),['native_submit','submit_event']);
});

test('group2 an approved change has only one same-form consequential submission',()=>{
  const f=fixture(),form=new f.HTMLFormElement(),field=new f.HTMLElement();field.form=form;
  f.arm(field,form,'approved-change');f.api.direct('e1');form.submit();form.submit();
  assert.equal(f.arrivals.length,1);assert.equal(f.reports.length,1);
});

test('group1 GET searches stay free but a POST submitter override is held',()=>{
  const f=fixture(),form=new f.HTMLFormElement();form.method='get';form.role='search';form.action='http://fixture.test/search';
  f.arm(form,form,null);form.requestSubmit();assert.equal(f.arrivals.length,1);assert.equal(f.reports.length,0);
  const button=new f.HTMLElement();button.tagName='BUTTON';button.type='submit';button.formmethod='post';button.form=form;form.requestSubmit(button);
  assert.equal(f.arrivals.length,1);assert.equal(f.reports.length,1);
});

test('review1 external accessible labels ask in both wrappers and capture fallback',()=>{
  for(const source of ['labelledby','label'])for(const route of ['click','dispatch','fallback']){
    const f=fixture(),button=new f.HTMLElement(),label=new f.HTMLElement();
    button.tagName='BUTTON';label.textContent='Delete';
    if(source==='labelledby'){button['aria-labelledby']='deletion';f.document.labels={deletion:label};}
    else button.labels=[label];
    let delivered=0;button.addEventListener('click',()=>delivered++);f.arm(button,null);
    if(route==='click')button.click();
    else if(route==='dispatch')button.dispatchEvent(new f.Event('click'));
    else {
      // A different realm's dispatch bypasses the wrapper but reaches capture.
      const event=new f.Event('click');event.target=button;
      // The fixture's pre-wrapper dispatch is saved below via the returned class.
      f.originalDispatch.call(button,event);
    }
    assert.equal(delivered,0,`${source}/${route}`);assert.equal(f.reports.length,1,`${source}/${route}`);
  }
});


test('group7 public controls and forged identity/report events cannot relax isolated holds',()=>{
  const f=fixture(),form=new f.HTMLFormElement();f.arm(form,form);
  vm.runInContext("globalThis[Symbol.for('aresos.chrome.page.v1')]={stop(){},arm(){},resume(){}}",f.main);
  for(const kind of ['aresos-reader-identity','aresos-page-step','aresos-dialog-origin','aresos-watch-root','message'])
    f.originalDispatch.call(form,new f.CustomEvent(kind,{detail:{id:'target',kind:'native_submit',generation:'epoch',operation:'forged'}}));
  for(const kind of ['native_submit','request_submit','click','dispatch'])
    f.originalDispatch.call(form,new f.CustomEvent('aresos-page-call-v2',{detail:{kind,event:new f.Event('click')}}));
  form.submit();assert.equal(f.arrivals.length,0);
  const step=f.reports.find(item=>item.kind==='native_submit');f.api.resume(step.id,'approved');assert.equal(f.arrivals.length,1);
  assert.throws(()=>f.api.resume(step.id,'approved'));assert.equal(f.arrivals.length,1);
});

test('group2 owner task exempts exactly its form once and never delayed or in-flight input',async()=>{
  const f=fixture(),form=new f.HTMLFormElement(),field=new f.HTMLInputElement();field.form=form;f.arm(field,null);
  field.addEventListener('keydown',()=>form.submit());
  f.originalDispatch.call(field,new f.Event('keydown',{key:'Enter',isTrusted:true}));assert.equal(f.arrivals.length,0,'in-flight owner is held');
  await f.api.finish('epoch');
  f.originalDispatch.call(field,new f.Event('keydown',{key:'Enter',isTrusted:true}));assert.equal(f.arrivals.length,1,'synchronous owner handler is exempt');
  form.submit();assert.equal(f.arrivals.length,1,'one input cannot grant a second submission');
  await new Promise(resolve=>setImmediate(resolve));
  form.submit();assert.equal(f.arrivals.length,1,'the exemption ends on the private channel task');
  assert.ok(f.reports.length>=2);
});

test('group2 owner default after event dispatch is exact-form exact-submitter and one-use',async()=>{
  const f=fixture(),form=new f.HTMLFormElement(),other=new f.HTMLFormElement(),field=new f.HTMLInputElement(),button=new f.HTMLElement();field.form=form;button.form=form;button.type='submit';
  f.arm(field,null);await f.api.finish('epoch');
  f.originalDispatch.call(field,new f.Event('keydown',{key:'Enter',isTrusted:true}));
  other.submit();form.requestSubmit(button);assert.equal(f.arrivals.length,0,'a timer cannot use another form or submitter while the owner mark waits');
  form.requestSubmit();assert.equal(f.arrivals.length,0,'a scripted requestSubmit of the same form still belongs to the page timer');
  f.originalRequestSubmit.call(form);assert.equal(f.arrivals.length,1,'the native browser default after eventPhase resets belongs to this exact input');
  f.originalRequestSubmit.call(form);assert.equal(f.arrivals.length,1,'the task mark grants exactly one submission');
  f.originalDispatch.call(field,new f.Event('keyup',{key:'Enter',isTrusted:true}));await new Promise(resolve=>setImmediate(resolve));
  form.submit();assert.equal(f.arrivals.length,1,'a later task cannot retain ownership');
});

test('owner marks cannot make cancelled defaults, keyup or a timer native submit count as owner input',async()=>{
  for(const mode of ['cancelled','keyup','native-timer']){
    const f=fixture(),form=new f.HTMLFormElement(),field=new f.HTMLInputElement();field.form=form;f.arm(field,null);await f.api.finish('epoch');
    if(mode==='cancelled')field.addEventListener('keydown',event=>event.preventDefault());
    f.originalDispatch.call(field,new f.Event(mode==='keyup'?'keyup':'keydown',{key:'Enter',isTrusted:true}));
    if(mode==='native-timer')form.submit();else form.requestSubmit();
    assert.equal(f.arrivals.length,0,mode+' cannot borrow the pending private task mark');assert.ok(f.reports.length);
  }
});

test('owner defaults require an enabled submitter or an actual one-field implicit submission',async()=>{
  const f=fixture(),form=new f.HTMLFormElement(),field=new f.HTMLInputElement(),other=new f.HTMLInputElement();field.form=form;other.form=form;form.elements=[field,other];f.arm(field,null);await f.api.finish('epoch');
  f.originalDispatch.call(field,new f.Event('keydown',{key:'Enter',isTrusted:true}));f.originalRequestSubmit.call(form);assert.equal(f.arrivals.length,0,'Enter cannot submit a multi-field form without a default button');
  form.elements=[field];f.originalDispatch.call(field,new f.Event('keydown',{key:'Enter',isTrusted:true}));f.originalRequestSubmit.call(form);assert.equal(f.arrivals.length,1,'the same one-field implicit submission is its native default');
});

test('validation-suppressed owner defaults never exempt property-repaired timer requests',async()=>{
  const f=fixture({relay:true}),form=new f.HTMLFormElement(),button=new f.HTMLElement();button.form=form;button.type='submit';f.arm(button,null);await f.api.finish('epoch');
  f.originalDispatch.call(button,new f.Event('click',{isTrusted:true}));form.valid=false;f.originalRequestSubmit.call(form,button);assert.equal(f.arrivals.length,0);
  form.valid=true;form.requestSubmit(button);assert.equal(f.arrivals.length,0,'trusted submit generated inside a scripted native call cannot borrow owner defaults');
  f.originalDispatch.call(button,new f.Event('invalid',{isTrusted:true}));f.originalRequestSubmit.call(form,button);assert.equal(f.arrivals.length,0,'native validation failure invalidates even a later borrowed-native request');
  assert.ok(f.reports.length>=2);
});

test('group7 preparation cannot grant a page a submission before trusted dispatch',()=>{
  const f=fixture(),form=new f.HTMLFormElement(),button=new f.HTMLElement();button.form=form;
  f.arm(button,form,'approved');form.submit();assert.equal(f.arrivals.length,0);
  f.originalDispatch.call(button,new f.Event('click',{isTrusted:true}));
  form.submit();assert.equal(f.arrivals.length,0,'an unlabelled control without a trusted handler has no authority');
});

test('group2 a further native submit cancels the resumed event default even without page cancellation',()=>{
  const f=fixture(),form=new f.HTMLFormElement();let handlers=0;
  form.addEventListener('submit',()=>{handlers++;form.submit();});
  f.arm(form,form);form.requestSubmit();assert.equal(f.arrivals.length,0);
  f.api.resume(f.reports[0].id,'op');assert.equal(handlers,1);assert.equal(f.arrivals.length,1);
});

test('group7 replay of a formerly trusted owner event cannot reuse the owner exemption',async()=>{
  const f=fixture(),form=new f.HTMLFormElement(),button=new f.HTMLElement();f.arm(button,null);await f.api.finish('epoch');
  const event=new f.Event('click',{isTrusted:true});f.originalDispatch.call(button,event);
  button.addEventListener('click',()=>form.submit());event.isTrusted=false;
  f.originalDispatch.call(button,event);assert.equal(f.arrivals.length,0);assert.equal(f.reports[0].kind,'native_submit');
});
test('group1 capitalized shipped Papierkorb holds wrappers and capture equally',()=>{
  for(const route of ['click','dispatch','capture']){
    const f=fixture(),button=new f.HTMLElement();button.tagName='BUTTON';button.textContent='Papierkorb';let delivered=0;
    button.addEventListener('click',()=>delivered++);f.arm(button,null);
    if(route==='click')button.click();else if(route==='dispatch')button.dispatchEvent(new f.Event('click'));else f.originalDispatch.call(button,new f.Event('click'));
    assert.equal(delivered,0);assert.equal(f.reports.length,1);
  }
});

test('group7 replacing public wrapper prototypes and call intrinsics only adds holds',()=>{
  const f=fixture(),form=new f.HTMLFormElement();f.arm(form,form);
  vm.runInContext("Function.prototype.call=function(){throw Error('page replaced call')};Reflect.apply=()=>{throw Error('page replaced apply')};Object.defineProperty=()=>{throw Error('page replaced define')}",f.main);
  const wrapper=f.HTMLFormElement.prototype.submit;
  f.HTMLFormElement.prototype.submit=function(){return wrapper.apply(this,arguments);};
  form.submit();assert.equal(f.arrivals.length,0);
  f.api.resume(f.reports[0].id,'approved');assert.equal(f.arrivals.length,1);
});


test('conservative mode holds ordinary page-script activations after free input',()=>{
  for(const route of ['click','dispatch','fallback']){
    const f=fixture(),button=new f.HTMLElement();button.tagName='BUTTON';button.textContent='Continue';let received=0;
    button.addEventListener('click',()=>received++);f.arm(button,null,null,true);
    if(route==='click')button.click();else if(route==='dispatch')button.dispatchEvent(new f.Event('click'));else f.originalDispatch.call(button,new f.Event('click'));
    assert.equal(received,0);assert.equal(f.reports.length,1);assert.equal(f.reports[0].kind,'activation');
  }
});


test('approved field Enter allows only its bound trusted implicit submitter and effective destination',()=>{
  const f=fixture(),form=new f.HTMLFormElement(),field=new f.HTMLElement(),button=new f.HTMLElement(),other=new f.HTMLElement();
  field.form=form;button.form=form;other.form=form;button.type=other.type='submit';button.formAction='/approved-override';form.action='/bare-form';
  const expected={action:'/approved-override',method:'post',encoding:'application/x-www-form-urlencoded',target:''};
  f.guard.arm({generation:'epoch',config:{words:['send'],holdMs:500},operation:'approved',target:f.id(field),form:f.id(form),implicit:f.id(button),key_input:{key:'Enter',modifiers:0},approved_form:expected,primary_submission:true});
  // The page cannot use a known submitter before the approved trusted key arrives.
  f.originalDispatch.call(button,new f.Event('click',{isTrusted:true}));assert.equal(f.reports.length,1);
  f.originalDispatch.call(field,new f.Event('input',{isTrusted:true}));f.originalDispatch.call(button,new f.Event('click',{isTrusted:true}));assert.equal(f.reports.length,2,'input/change is not the approved keydown');
  f.originalDispatch.call(field,new f.Event('keydown',{isTrusted:true,key:'Enter'}));
  form.requestSubmit(other);assert.equal(f.arrivals.length,0,'another successful submitter cannot consume the primary allowance');
  form.submit();assert.equal(f.arrivals.length,0,'a native call with another destination gets its own question');
  f.originalDispatch.call(button,new f.Event('click',{isTrusted:true}));
  form.requestSubmit(button);assert.deepEqual(f.arrivals,['event']);
  f.originalDispatch.call(other,new f.Event('click',{isTrusted:true}));
  assert.equal(f.reports.length,5,'the other submitter never inherits this approval');
});


test('a resumed event with no submitter cannot add a successful button through its further allowance',()=>{
  const f=fixture(),form=new f.HTMLFormElement(),other=new f.HTMLElement();other.form=form;other.type='submit';let handlers=0;
  form.addEventListener('submit',event=>{handlers++;event.preventDefault();form.requestSubmit(other);});
  f.arm(form,form);form.requestSubmit();f.api.resume(f.reports[0].id,'approved-no-submitter');
  assert.equal(handlers,1);assert.equal(f.arrivals.length,0);assert.equal(f.reports.length,2);
});


test('a page-induced reader exception in submit capture can only add a hold',()=>{
  const f=fixture(),form=new f.HTMLFormElement();let handlers=0;
  form.addEventListener('submit',()=>handlers++);f.arm(form,form);
  f.guard.reader({document:'document-1',id:f.id,element:()=>form,target(){throw Error('Synthetic DOM clobber');},form(){throw Error('Synthetic DOM clobber');}});
  form.requestSubmit();assert.equal(f.arrivals.length,0);assert.equal(handlers,0);assert.equal(f.reports[0].kind,'activation');
  f.originalDispatch.call(form,new f.Event('click',{cancelable:false}));assert.equal(f.reports[1].kind,'activation_unknown');assert.equal(f.reports[1].cancellable,false);
});


test('slow frame arming cannot consume the post-input hold window',async()=>{
  const f=fixture(),form=new f.HTMLFormElement();f.arm(form,form);f.advance(1000);
  await f.api.finish('epoch');form.submit();assert.equal(f.arrivals.length,0);assert.equal(f.reports.length,1);
  f.advance(501);form.submit();assert.equal(f.arrivals.length,1,'after-limit ordinary work stays free');
});


test('service and isolated guard agree on frozen Unicode folding and whole-word boundaries',()=>{
  const cases=['ſend','veröﬀentlichen','beﬅellen','İsend','resend','Send later','SEND','Papierkorb',...Object.keys(policy.unicodeWords.fold).flatMap(char=>[char+'send','send'+char])];
  const source="import json,sys;from aresos_control.chrome.policy import listed;print(json.dumps([bool(listed(text)) for text in json.load(sys.stdin)]))";
  const expected=JSON.parse(execFileSync('python3',['-c',source],{input:JSON.stringify(cases),encoding:'utf8',env:{...process.env,PYTHONPATH:'control',PYTHONDONTWRITEBYTECODE:'1'}}));
  const f=fixture(),button=new f.HTMLElement();let received=0;button.tagName='BUTTON';button.addEventListener('click',()=>received++);
  for(let index=0;index<cases.length;index++){
    button.textContent=cases[index];f.arm(button,null);const before=received;button.click();
    assert.equal(received===before,expected[index],cases[index]);
  }
});

test('opaque event hints cannot deliver an original click or forge trusted ownership',async()=>{
  const f=fixture(),button=new f.HTMLElement(),form=new f.HTMLFormElement();button.textContent='Delete';
  let clicks=0;button.addEventListener('click',()=>clicks++);button.addEventListener('keyup',event=>{assert.equal(event.isTrusted,false);form.submit();});
  f.arm(button,null);await f.api.finish('epoch');
  const send=detail=>f.originalDispatch.call(button,new f.CustomEvent('aresos-page-call-v2',{detail:{kind:'dispatch',...detail}}));
  send({event:{type:'click',isTrusted:true},event_type:'keyup',event_flags:{bubbles:true},event_data:{key:'Enter',isTrusted:true}});
  assert.equal(clicks,0);assert.equal(f.arrivals.length,0);assert.equal(f.reports[0].kind,'native_submit');
  send({event:{type:'keyup'},event_type:'click',event_flags:{cancelable:false}});
  assert.equal(clicks,0);assert.equal(f.reports[1].kind,'activation');
  send({event:{},event_type:{toString(){return 'click';}}});assert.equal(clicks,0);
});
test('opaque data getters finish before classification and are skipped for password targets',()=>{
  const f=fixture(),button=new f.HTMLElement();button.textContent='Continue';let delivered=0,reads=0;button.addEventListener('click',()=>delivered++);f.arm(button,null);
  const detail={kind:'dispatch',event:{},event_type:'click',event_flags:{cancelable:true},get event_data(){reads++;button.textContent='Delete';return {};}};
  f.originalDispatch.call(button,new f.CustomEvent('aresos-page-call-v2',{detail}));assert.equal(delivered,0);assert.equal(reads,1);assert.equal(f.reports.length,1);
  button.password=true;f.originalDispatch.call(button,new f.CustomEvent('aresos-page-call-v2',{detail}));assert.equal(reads,1);assert.equal(delivered,0);
});
test('dispatch wrappers reject recursive reuse of an event',()=>{
  const f=fixture(),button=new f.HTMLElement(),event=new f.Event('keyup');let handlers=0;
  button.addEventListener('keyup',()=>{handlers++;assert.throws(()=>button.dispatchEvent(event),/already being dispatched/);});
  button.dispatchEvent(event);assert.equal(handlers,1);
});
test('an old delayed finish cannot clear a newly armed private dispatch',async()=>{
  const f=fixture(),button=new f.HTMLElement(),form=new f.HTMLFormElement();button.addEventListener('click',()=>form.submit());
  f.guard.arm({generation:'epoch',dispatch_nonce:'first',config:policy,target:f.id(button)});const old=f.guard.finish('epoch','first');
  f.guard.arm({generation:'epoch',dispatch_nonce:'second',config:policy,target:f.id(button)});await old;
  f.originalDispatch.call(button,new f.Event('click',{isTrusted:true}));assert.equal(f.arrivals.length,0);assert.equal(f.reports.length,1);
});

test('flat lazy primitive fields replay keyboard data as a fresh untrusted event',()=>{
  const f=fixture(),button=new f.HTMLElement();button.textContent='Continue';f.arm(button,null);
  const original=new f.Event('keyup',{key:'Enter',code:'Enter',location:1,shiftKey:true,repeat:true,bubbles:true});let received;
  button.addEventListener('keyup',event=>{received=event;});
  assert.equal(button.dispatchEvent(original),true);assert.ok(received);
  assert.notEqual(received,original,'the page-owned Event object must not cross the isolated bridge');
  assert.equal(received.isTrusted,false);assert.equal(received.key,'Enter');assert.equal(received.code,'Enter');
  assert.equal(received.location,1);assert.equal(received.shiftKey,true);assert.equal(received.repeat,true);
});

test('flat input payload remains lazy for a protected target',()=>{
  const f=fixture(),field=new f.HTMLElement();field.password=true;f.arm(field,null);
  const original=new f.Event('input',{bubbles:true});let reads=0,received;
  Object.defineProperty(original,'data',{get(){reads++;return 'SENTINEL_PROTECTED_EVENT_PAYLOAD';}});
  field.addEventListener('input',event=>{received=event;});field.dispatchEvent(original);
  assert.equal(reads,0,'neither MAIN nor ISOLATED may demand protected payload data');
  assert.ok(received);assert.equal(received.data,undefined);assert.equal(received.isTrusted,false);
});

test('flat primitive getter mutations complete before the final activation decision',()=>{
  const f=fixture(),button=new f.HTMLElement();button.textContent='Continue';f.arm(button,null);
  const original=new f.Event('click',{cancelable:true});let reads=0,delivered=0;
  Object.defineProperty(original,'key',{get(){reads++;button.textContent='Delete';return 'x';}});
  button.addEventListener('click',()=>delivered++);
  assert.equal(button.dispatchEvent(original),false);assert.equal(reads,1);assert.equal(delivered,0);
  assert.equal(f.reports[0].kind,'activation');
});

test('MAIN reports carry no Event or submitter objects and preserve receiver validation',()=>{
  const f=fixture(),form=new f.HTMLFormElement(),other=new f.HTMLFormElement(),button=new f.HTMLElement();button.tagName='BUTTON';button.type='submit';button.form=form;
  f.arm(button,form);form.requestSubmit(button);assert.equal(f.arrivals.length,0);
  assert.deepEqual(Object.keys(f.bridgeDetails[0]).sort(),['kind','with_submitter']);
  const before=f.bridgeDetails.length;assert.throws(()=>other.requestSubmit(button),/another form/);assert.equal(f.bridgeDetails.length,before);
  const event=new f.Event('click');button.dispatchEvent(event);const detail=f.bridgeDetails.at(-1);
  assert.equal(detail.event,undefined);assert.equal(detail.submitter,undefined);assert.equal(detail.event_type,'click');
});
test('fresh script events preserve prior cancellation and never acquire trust',()=>{
  const f=fixture(),button=new f.HTMLElement(),event=new f.Event('keyup');event.preventDefault();
  button.addEventListener('keyup',copy=>{assert.notEqual(copy,event);assert.equal(copy.isTrusted,false);assert.equal(copy.defaultPrevented,true);});
  assert.equal(button.dispatchEvent(event),false);
});

test('a descriptor getter protecting the target prevents every later payload read',()=>{
  const f=fixture(),field=new f.HTMLElement(),event=new f.Event('input');let reads=0;
  Object.defineProperty(event,'key',{get(){field.password=true;return '';}});
  Object.defineProperty(event,'data',{get(){reads++;return 'SYNTHETIC_PROTECTED_SENTINEL';}});
  f.arm(field,null);field.dispatchEvent(event);
  assert.equal(field.password,true);assert.equal(reads,0);
});

test('GET search cannot bypass private excluded destinations or unsafe URLs',()=>{
  for(const action of ['http://approval.test/search','https://child.approval.test./search','javascript:alert(1)','http://user:pass@fixture.test/search']){
    const f=fixture(),form=new f.HTMLFormElement();form.method='get';form.role='search';form.action=action;
    f.guard.arm({generation:'epoch',config:{...policy,blockedHosts:['approval.test']},target:f.id(form),form:f.id(form)});
    form.submit();form.requestSubmit();assert.equal(f.arrivals.length,0,action);assert.equal(f.reports.length,2,action);
  }
});


test('P7 malformed escapes and invalid UTF-8 keep script activation asking',()=>{
  for(const suffix of ['%ZZ','%FF','%E2%82']){
    const f=fixture(),form=new f.HTMLFormElement(),button=new f.HTMLElement();
    button.tagName='BUTTON';button.textContent='Continue';button.form=form;form.action='https://fixture.test/%73end?bad='+suffix;
    let handlers=0;button.addEventListener('click',()=>handlers++);f.arm(button,form);button.click();
    assert.equal(handlers,0);assert.equal(f.reports.length,1);
  }
});
test('P8 decomposed canonical list words ask before delivery',()=>{
  for(const word of ['lo\u0308schen','vero\u0308ffentlichen']){
    const f=fixture(),button=new f.HTMLElement();button.tagName='BUTTON';button.textContent=word;
    let handlers=0;button.addEventListener('click',()=>handlers++);f.arm(button,null);button.click();
    assert.equal(handlers,0);assert.equal(f.reports.length,1);
  }
});


test('P20 synchronous owner Enter pins the exact form and exact submitter independently',async()=>{
  for(const mode of ['other-form','other-submitter']){
    const f=fixture(),form=new f.HTMLFormElement(),other=new f.HTMLFormElement(),field=new f.HTMLInputElement(),button=new f.HTMLElement();field.form=form;button.form=form;button.type='submit';
    f.arm(field,null);await f.api.finish('epoch');
    field.addEventListener('keydown',()=>mode==='other-form'?other.submit():form.requestSubmit(button));
    f.originalDispatch.call(field,new f.Event('keydown',{key:'Enter',isTrusted:true}));
    assert.equal(f.arrivals.length,0,mode+' must stay held during owner dispatch');assert.equal(f.reports.length,1);
  }
});
test('P20 an untrusted Enter on the exact field never establishes owner authority',async()=>{
  const f=fixture(),form=new f.HTMLFormElement(),field=new f.HTMLInputElement();field.form=form;f.arm(field,null);await f.api.finish('epoch');
  field.addEventListener('keydown',()=>form.submit());f.originalDispatch.call(field,new f.Event('keydown',{key:'Enter',isTrusted:false}));
  assert.equal(f.arrivals.length,0);assert.equal(f.reports.length,1);
});
test('P20 an unconsumed owner mark expires before a delayed trusted native default',async()=>{
  const f=fixture(),form=new f.HTMLFormElement(),field=new f.HTMLInputElement();field.form=form;f.arm(field,null);await f.api.finish('epoch');
  f.originalDispatch.call(field,new f.Event('keydown',{key:'Enter',isTrusted:true}));
  await new Promise(resolve=>setImmediate(resolve));f.originalRequestSubmit.call(form);
  assert.equal(f.arrivals.length,0,'clearing is required even without consumption or cancellation');assert.equal(f.reports.length,1);
});
test('P26 wrappers have native nonconstructible method shapes',()=>{
  const f=fixture();for(const fn of [f.HTMLFormElement.prototype.submit,f.HTMLFormElement.prototype.requestSubmit,f.HTMLElement.prototype.click,f.EventTarget.prototype.dispatchEvent]){
    assert.equal(Object.hasOwn(fn,'prototype'),false);assert.deepEqual(Object.getOwnPropertyNames(fn),['length','name']);assert.throws(()=>Reflect.construct(fn,[]),TypeError);
  }
});
test('P4 borrowed wrappers route to another controlled document guard',()=>{
  const source=fixture({relay:true}),target=fixture({relay:true}),form=new target.HTMLFormElement();source.arm(new source.HTMLElement(),null);target.guard.control('target-epoch');
  source.HTMLFormElement.prototype.submit.call(form);assert.equal(source.arrivals.length,0);assert.equal(target.arrivals.length,0);assert.equal(target.reports.length,1);
  const outside=fixture({relay:true}),ordinary=new outside.HTMLFormElement();outside.cleanup();outside.guard.dispose();delete outside.document.defaultView[Symbol.for('aresos.chrome.guard.v2')];
  source.HTMLFormElement.prototype.submit.call(ordinary);assert.equal(source.arrivals.length,1,'the saved source native is used for an uncontrolled document');
});
test('P5 composed root keeps asking controls inside shadow DOM held',()=>{
  const f=fixture(),host=new f.HTMLElement(),root=new f.Node(),form=new f.HTMLFormElement();root.host=host;form.root=root;f.arm(host,null);
  form.submit();assert.equal(f.arrivals.length,0);assert.equal(f.reports.length,1,'composed:false would bypass the guard');
});


test('P5 new roots install capture before a borrowed native dispatch can activate a control',()=>{
  for(const composed of [false,true])for(const cancelable of [false,true]){
    const f=fixture({relay:true}),host=new f.HTMLElement(),button=new f.HTMLElement();button.tagName='BUTTON';button.textContent='Delete';f.arm(host,null);
    const root=host.attachShadow({mode:'closed'});assert.ok(root.listeners.get('click')?.length,'wrapped creation synchronously installs capture');button.root=root;let handlers=0;button.addEventListener('click',()=>handlers++);
    f.originalDispatch.call(button,new f.Event('click',{composed,cancelable}));
    assert.equal(handlers,0);assert.equal(f.reports.length,1);assert.equal(f.reports[0].kind,cancelable?'activation':'activation_unknown');
  }
});
test('P5 native shadow identity survives InputEvent range retargeting without touching page getters',()=>{
  for(const kind of ['native','request','dispatch'])for(const nested of [false,true]){
    const f=fixture({relay:true,nativeShadows:true,retarget:true}),host=new f.HTMLElement();f.arm(host,null);
    let root=host.attachShadow({mode:'closed'});if(nested){const inner=new f.HTMLElement();inner.root=root;inner.parentNode=root;root.childNodes=[new f.HTMLElement(),inner];root=inner.attachShadow({mode:'closed'});}
    const form=new f.HTMLFormElement();form.root=root;form.parentNode=root;root.childNodes=[new f.HTMLElement(),form];
    for(const name of ['parentNode','previousSibling'])Object.defineProperty(form,name,{get(){assert.fail('page getter read');}});
    if(kind==='native')form.submit();else if(kind==='request')form.requestSubmit();else form.dispatchEvent(new f.Event('submit'));
    assert.equal(f.arrivals.length,0);assert.equal(f.reports.length,1,kind);
    assert.equal(f.reports[0].kind,kind==='native'?'native_submit':kind==='request'?'submit_event':'activation');
  }
});


test('P3 inheriting only the remaining window grants no allowance or permanent in-flight mark',()=>{
  const f=fixture(),form=new f.HTMLFormElement();f.guard.inherit({generation:'epoch',dispatch_nonce:'source',config:policy,in_flight:false});
  form.submit();assert.equal(f.arrivals.length,0);assert.equal(f.reports.length,1);
  f.advance(policy.holdMs+1);form.submit();assert.equal(f.arrivals.length,1,'the inherited mark ends with the window without an async finish during startup');
});
test('P1 native dialog return values survive and the private boundary precedes the caller continuation',()=>{
  for(const [kind,expected]of [['alert',undefined],['confirm',true],['prompt','native response']]){
    const f=fixture({relay:true,dialogs:true,onDialogBoundary:guard=>{assert.equal(guard.dialogBoundary().token,'d1');guard.arm({generation:'epoch',dispatch_nonce:'dialog',config:policy});}}),form=new f.HTMLFormElement();
    f.guard.control('epoch');f.main.continueAfterDialog=()=>form.submit();
    const result=vm.runInContext(`(()=>{const value=${kind}('DIALOG_ARGUMENT_MUST_STAY_IN_PAGE');continueAfterDialog();return value;})()`,f.main);
    assert.equal(result,expected);assert.deepEqual(f.dialogCalls,[kind]);assert.equal(f.arrivals.length,0);assert.equal(f.reports.length,1);
    assert.equal(vm.runInContext(`Object.hasOwn(${kind},'prototype')`,f.main),false);
    assert.doesNotMatch(JSON.stringify(f.dialogReports),/DIALOG_ARGUMENT_MUST_STAY_IN_PAGE|native response/);
  }
});
test('P1 a native owner answer keeps native form behavior when no tool answer armed a hold',()=>{
  const f=fixture({relay:true,dialogs:true}),form=new f.HTMLFormElement();f.guard.control('epoch');f.main.continueAfterDialog=()=>form.submit();
  assert.equal(vm.runInContext("confirm('Continue?')",f.main),true);f.main.continueAfterDialog();assert.equal(f.arrivals.length,1);assert.equal(f.reports.length,0);
});


test('P1 borrowed dialogs during native string conversion cannot borrow the outer return token',()=>{
  for(const kind of ['alert','confirm','prompt'])for(const argument of kind==='prompt'?[0,1]:[0]){
    const f=fixture({relay:true,dialogs:true});f.guard.control('epoch');let calls=0;
    f.main.convert=hint=>{assert.equal(hint,'string');assert.equal(f.dialogReports.length,0,'argument conversion precedes private dialog authority');calls++;f.nativeDialogs[kind]('Borrowed native');return 'Converted native argument';};
    const value=vm.runInContext(`(()=>{const value={[Symbol.toPrimitive](hint){return convert(hint);}};return ${kind}(${argument===0?'value':"'Outer native',value"});})()`,f.main);
    assert.equal(calls,1);assert.deepEqual(f.dialogCalls,[kind,kind]);assert.equal(value,kind==='alert'?undefined:kind==='confirm'?true:'native response');assert.deepEqual(f.dialogReports.map(row=>row[0]),['begin','end']);
  }
});


test('P1 dialog conversion keeps native defaults ignored extras and thrown identities',()=>{
  for(const kind of ['alert','confirm','prompt'])for(const value of [undefined,null,42]){
    const f=fixture({relay:true,dialogs:true});f.guard.control('epoch');f.main.value=value;const extra={toString(){throw Error('An ignored argument was converted');}};f.main.extra=extra;
    const args=kind==='prompt'?[value,undefined,extra]:[value,extra];f.nativeDialogs[kind](...args);
    vm.runInContext(`${kind}(value,${kind==='prompt'?'undefined,extra':'extra'})`,f.main);assert.deepEqual(f.dialogValues[0],f.dialogValues[1]);
  }
  for(const kind of ['alert','confirm','prompt']){
    const f=fixture({relay:true,dialogs:true});f.guard.control('epoch');
    assert.throws(()=>vm.runInContext(`${kind}(Symbol('not a DOMString'))`,f.main),error=>error.name==='TypeError');assert.equal(f.dialogReports.length,0);
    const failure={fixture:'conversion failure'};f.main.fail=()=>{throw failure;};
    assert.throws(()=>vm.runInContext(`${kind}({toString(){return fail();}})`,f.main),error=>error===failure);assert.equal(f.dialogReports.length,0);
  }
});

// Recheck: a GET search container cannot override an explicit asking label.
test('recheck search labels win in activation and every submission route',()=>{
  for(const label of ['Pay','Delete'])for(const route of ['click','dispatch','fallback','native-submit','request-submit','submit-event','relay-submit']){
    const f=fixture({relay:true}),form=new f.HTMLFormElement(),button=new f.HTMLElement();
    form.method='get';form.role='search';form.action='http://fixture.test/search';
    button.tagName='BUTTON';button.type='submit';button.textContent=label;button.form=form;
    let handlers=0;button.addEventListener('click',()=>handlers++);form.addEventListener('submit',()=>handlers++);f.arm(button,form);
    if(route==='click')button.click();
    else if(route==='dispatch')button.dispatchEvent(new f.Event('click'));
    else if(route==='fallback')f.originalDispatch.call(button,new f.Event('click'));
    else if(route==='native-submit')form.submit();
    else if(route==='request-submit')form.requestSubmit(button);
    else if(route==='submit-event')f.originalDispatch.call(form,new f.Event('submit',{submitter:button}));
    else form.dispatchEvent(new f.Event('submit'));
    assert.equal(handlers,0,label+' '+route);assert.equal(f.arrivals.length,0);assert.equal(f.reports.length,1);
  }
});
test('recheck composed native roots discover capture without prior registration',()=>{
  for(const mode of ['open','closed'])for(const cancelable of [false,true]){
    const f=fixture({relay:true,nativeShadows:true}),host=new f.HTMLElement(),button=new f.HTMLElement();
    const root=f.nativeAttach.call(host,{mode});f.nativeAppend.call(root,button);
    button.tagName='BUTTON';button.textContent='Delete';let handlers=0;f.nativeListen.call(button,'click',()=>handlers++);f.arm(host,null);
    f.originalDispatch.call(button,new f.Event('click',{composed:true,cancelable}));
    assert.equal(handlers,0);assert.equal(f.reports.length,1);assert.equal(f.reports[0].kind,cancelable?'activation':'activation_unknown');
  }
});
test('recheck native roots register before noncomposed content or listeners',()=>{
  for(const mode of ['open','closed'])for(const route of ['append','appendChild','listener','markup'])for(const cancelable of [false,true]){
    const f=fixture({relay:true,nativeShadows:true}),host=new f.HTMLElement(),button=new f.HTMLElement();
    const root=f.nativeAttach.call(host,{mode});button.tagName='BUTTON';button.textContent='Delete';let handlers=0;
    if(route==='listener'){f.nativeAppend.call(root,button);button.addEventListener('click',()=>handlers++);}
    else if(route==='markup'){f.nativeAppend.call(root,button);f.nativeListen.call(button,'click',()=>handlers++);root.innerHTML='native setter still runs';assert.equal(root.innerHTML,'native setter still runs');}
    else{f.nativeListen.call(button,'click',()=>handlers++);root[route](button);}
    f.arm(host,null);f.originalDispatch.call(button,new f.Event('click',{composed:false,cancelable}));
    assert.equal(handlers,0,mode+' '+route);assert.equal(f.reports.length,1);assert.equal(f.reports[0].kind,cancelable?'activation':'activation_unknown');
    if(route==='markup')Object.defineProperty(f.Node.prototype,'innerHTML',{...Object.getOwnPropertyDescriptor(f.Node.prototype,'innerHTML'),get(){return 'page replacement getter';}});
    assert.equal(f.cleanup(),true);if(route==='markup')assert.equal(root.innerHTML,'page replacement getter');assert.equal(f.Node.prototype.appendChild,f.nativeAppend);assert.equal(f.EventTarget.prototype.addEventListener,f.nativeListen);assert.equal(Object.getOwnPropertyDescriptor(f.Node.prototype,'innerHTML').set,f.nativeHTMLSetter);
  }
});
test('recheck a shadow host itself still meets window activation capture',()=>{
  const f=fixture({relay:true,nativeShadows:true}),host=new f.HTMLElement();host.textContent='Delete';
  f.nativeAttach.call(host,{mode:'closed'});let handlers=0;f.nativeListen.call(host,'click',()=>handlers++);f.arm(host,null);
  f.originalDispatch.call(host,new f.Event('click',{composed:true,cancelable:true}));
  assert.equal(handlers,0);assert.equal(f.reports.length,1);
});

// Neither native insertion nor dispatch passes through a MAIN wrapper.
test('recheck2 native insertion and noncomposed events meet capture installed at creation',()=>{
  for(const mode of ['open','closed'])for(const cancelable of [false,true]){
    const f=fixture({relay:true,nativeShadows:true}),host=new f.HTMLElement();f.arm(host,null);
    const root=f.nativeAttach.call(host,{mode}),button=f.document.createElement('a');
    button.tagName='A';button.textContent='Delete';let handlers=0;
    f.nativeListen.call(button,'click',()=>handlers++);f.nativeAppend.call(root,button);
    f.originalDispatch.call(button,new f.Event('click',{composed:false,cancelable}));
    assert.equal(handlers,0);assert.equal(f.reports.length,1);
  }
});
test('recheck2 uncancellable defaults lose hyperlink ping and new-window authority only during native activation',async()=>{
  for(const target of ['_blank','frame','_self'])for(const download of [false,true]){
    const f=fixture({relay:true,nativeShadows:true}),link=f.document.createElement('a');link.root=f.document;link.tagName='A';link.textContent='Delete';link.href='https://fixture.test/delete';link.target=target;link.ping='https://fixture.test/ping';link.download=download?'proof.txt':'';
    f.guard.arm({generation:'epoch',config:{...policy,defaultBlock:'https://aresos-hold.invalid/'},target:f.id(link)});
    let handlers=0;f.nativeListen.call(link,'click',()=>handlers++);
    f.originalDispatch.call(link,new f.Event('click',{cancelable:false}));
    assert.equal(handlers,0);assert.equal(link.getAttribute('href'),null);assert.equal(link.ping,'https://aresos-hold.invalid/');assert.equal(f.reports[0].kind,'activation');
    await new Promise(resolve=>setTimeout(resolve,5));assert.equal(link.href,'https://fixture.test/delete');assert.equal(link.ping,'https://fixture.test/ping');assert.equal(link.target,target);
    f.cleanup();f.guard.dispose();
  }
});
test('recheck2 the owners trusted click keeps its native navigation inside the hold',()=>{
  const f=fixture({relay:true,nativeShadows:true}),link=f.document.createElement('a');link.root=f.document;link.tagName='A';link.textContent='Delete';link.href='https://fixture.test/owner';
  f.guard.arm({generation:'epoch',config:{...policy,defaultBlock:'https://aresos-hold.invalid/'},target:f.id(link)});
  // Finish the extension dispatch but retain its hold window.
  f.advance(0);
  return f.guard.finish('epoch',undefined).then(()=>{
    f.originalDispatch.call(link,new f.Event('click',{isTrusted:true}));
    assert.equal(link.href,'https://fixture.test/owner');assert.equal(f.reports.length,0);
  });
});

test('recheck2 node and ancestor capture consume one approved activation only once',()=>{
  const f=fixture({relay:true,nativeShadows:true}),button=f.document.createElement('button');button.root=f.document;button.tagName='BUTTON';button.textContent='Delete';
  let handlers=0;f.nativeListen.call(button,'click',()=>handlers++);f.arm(button,null,'approved');
  f.originalDispatch.call(button,new f.Event('click',{isTrusted:true}));
  assert.equal(handlers,1);assert.equal(f.reports.length,0);
});

test('recheck2 native markup nodes meet capture when their click handler is installed',()=>{
  const f=fixture({relay:true,nativeShadows:true}),host=new f.HTMLElement(),button=new f.HTMLElement();f.arm(host,null);
  const root=f.nativeAttach.call(host,{mode:'closed'});button.tagName='A';button.textContent='Delete';f.nativeAppend.call(root,button);
  let handlers=0;button.onclick=()=>handlers++;
  f.originalDispatch.call(button,new f.Event('click',{composed:false}));assert.equal(handlers,0);assert.equal(f.reports.length,1);
});

test('recheck2 reusing a native Event never inherits a prior dispatch capture decision',()=>{
  for(const move of ['same','other','root'])for(const composed of [false,true]){
    const f=fixture({relay:true,nativeShadows:true}),host=new f.HTMLElement(),first=f.document.createElement('button'),second=f.document.createElement('button');
    for(const button of [first,second]){button.root=f.document;button.tagName='BUTTON';button.textContent='Delete';}
    let handlers=0;f.nativeListen.call(first,'click',()=>handlers++);f.nativeListen.call(second,'click',()=>handlers++);f.arm(host,null);
    const event=new f.Event('click',{composed});f.originalDispatch.call(first,event);
    if(move==='root'){const root=f.nativeAttach.call(host,{mode:'closed'});f.nativeAppend.call(root,first);}
    f.originalDispatch.call(move==='other'?second:first,event);
    assert.equal(handlers,0,move+' '+composed);assert.equal(f.reports.length,2,move+' '+composed);
  }
});

test('recheck2 irrelevant slot capture cannot erase the light-DOM approval decision',()=>{
  const f=fixture({relay:true,nativeShadows:true}),button=f.document.createElement('button');button.root=f.document;button.tagName='BUTTON';button.textContent='Delete';f.arm(button,null,'approved');
  // A slotted node keeps its light-DOM root; the slot root sees a different
  // closed-tree path but is not this node's activation-capture root.
  const slotRoot=f.nativeAttach.call(new f.HTMLElement(),{mode:'closed'});f.guard.watch(slotRoot);
  const listeners=slotRoot.listeners.get('click');let handlers=0;f.nativeListen.call(button,'click',()=>handlers++);
  const original=button.listeners.get('click'),capture=original[0];
  button.listeners.set('click',[event=>{event.visibleTarget=slotRoot.host;for(const listener of listeners)listener(event);event.visibleTarget=null;capture(event);},...original.slice(1)]);
  f.originalDispatch.call(button,new f.Event('click',{isTrusted:true,composed:true}));assert.equal(handlers,1);assert.equal(f.reports.length,0);
});

test('recheck2 clone hooks preserve native Attr and DocumentType results',()=>{
  const f=fixture({relay:true,nativeShadows:true,nativeNodeKinds:true});
  for(const kind of [2,10]){const node=new f.Node();node.fixtureKind=kind;node.ownerDocument=f.document;let clone;assert.doesNotThrow(()=>clone=node.cloneNode());assert.equal(clone.fixtureKind,kind);}
});
test('recheck2 cached creation hooks issue no private reports after release',()=>{
  const f=fixture({relay:true,nativeShadows:true,nativeNodeKinds:true}),node=new f.HTMLElement(),cached=node.cloneNode;let reports=0;
  f.nativeListen.call(f.factory.relay.firstElementChild,'aresos-relay-meta',()=>reports++);
  f.cleanup();cached.call(node);assert.equal(reports,0);f.guard.dispose();
});

for(const route of ['write','writeText'])test('2c Clipboard '+route+' reports success without reading or serializing content',async()=>{
  const f=fixture({relay:true,nativeShadows:true,clipboard:true}),button=new f.HTMLElement();f.arm(button,null);
  const value={toJSON(){throw Error('Observer serialized clipboard content');}},result={native:'result'};f.clipboardOutcome.value=result;
  assert.equal(await f.clipboard[route](value),result);assert.equal(f.clipboardCalls.length,1);assert.equal(f.clipboardCalls[0].value,value);assert.equal(f.clipboardCalls[0].receiver,f.clipboard);
  assert.deepEqual(JSON.parse(JSON.stringify(f.guard.clipboard())),{written:true,message:'The page wrote to the clipboard.',routes:[route]});
  f.cleanup();f.guard.dispose();
});
test('2c clipboard observers preserve rejection and synchronous native failure without reporting success',async()=>{
  const f=fixture({relay:true,nativeShadows:true,clipboard:true}),button=new f.HTMLElement();f.arm(button,null);
  const error=Error('Native permission denied');f.clipboardOutcome.error=error;
  await assert.rejects(f.clipboard.writeText('synthetic'),value=>value===error);assert.equal(f.guard.clipboard(),null);
  f.clipboardOutcome.synchronous=true;assert.throws(()=>f.clipboard.write([]),value=>value===error);assert.equal(f.guard.clipboard(),null);
  f.cleanup();f.guard.dispose();
});
test('2c trusted copy events are observed without cancellation propagation changes or clipboard-data reads',()=>{
  const f=fixture({relay:true,nativeShadows:true,clipboard:true}),button=new f.HTMLElement();f.arm(button,null);let delivered=0;
  f.nativeListen.call(button,'copy',()=>delivered++);const event=new f.Event('copy',{isTrusted:true});Object.defineProperty(event,'clipboardData',{get(){throw Error('Clipboard data was read');}});
  assert.equal(f.originalDispatch.call(button,event),true);assert.equal(delivered,1);assert.equal(event.defaultPrevented,false);
  assert.equal(f.guard.clipboard().routes[0],'copy');assert.equal(f.guard.clipboard(true).written,true);assert.equal(f.guard.clipboard(),null);
  f.cleanup();f.guard.dispose();
});
test('2c forged copy events cannot claim a clipboard write',()=>{
  const f=fixture({relay:true,nativeShadows:true,clipboard:true}),button=new f.HTMLElement();f.arm(button,null);
  f.originalDispatch.call(button,new f.Event('copy'));assert.equal(f.guard.clipboard(),null);f.cleanup();f.guard.dispose();
});
test('2c a watched node adopted into an ordinary document cannot report that documents copy',()=>{
  const f=fixture({relay:true,nativeShadows:true,clipboard:true}),button=f.document.createElement('button');f.arm(button,null);
  assert.ok(button.listeners.get('copy')?.length,'created nodes carry the synchronous capture listener');
  const outside=new f.Node();outside.root=outside;button.ownerDocument=outside;button.root=outside;
  let delivered=0;f.nativeListen.call(button,'copy',()=>delivered++);
  const event=new f.Event('copy',{isTrusted:true});assert.equal(f.originalDispatch.call(button,event),true);
  assert.equal(delivered,1);assert.equal(event.defaultPrevented,false);assert.equal(f.guard.clipboard(),null);
  f.cleanup();f.guard.dispose();
});
test('2c borrowed clipboard natives remain undetected and cached wrappers become native after release',async()=>{
  const f=fixture({relay:true,nativeShadows:true,clipboard:true}),button=new f.HTMLElement();f.arm(button,null);
  await f.nativeClipboard.writeText.call(f.clipboard,'synthetic');assert.equal(f.guard.clipboard(),null);
  const cached=f.clipboard.writeText;f.cleanup();await cached.call(f.clipboard,'synthetic');assert.equal(f.guard.clipboard(),null);assert.equal(f.clipboardCalls.length,2);f.guard.dispose();
});


test('recheck3 every wrapped native mix captures both listener insertion orderings',()=>{
  const results=[];
  for(const row of mixedRows()){
    const f=fixture({relay:true,nativeShadows:true}),host=new f.HTMLElement(),button=new f.HTMLElement();
    button.root=button;button.isConnected=false;button.tagName='BUTTON';button.textContent='Delete';let handlers=0;
    f.arm(host,null);
    const root=row.root?host.attachShadow({mode:row.mode}):f.nativeAttach.call(host,{mode:row.mode});
    const insert=()=>row.insert?root.appendChild(button):f.nativeAppend.call(root,button);
    const listen=()=>row.listen?button.addEventListener('click',()=>handlers++):f.nativeListen.call(button,'click',()=>handlers++);
    if(row.order==='before'){listen();insert();}else{insert();listen();}
    const event=new f.Event('click',{composed:row.composed,cancelable:true});
    if(row.dispatch)button.dispatchEvent(event);else f.originalDispatch.call(button,event);
    const limit=row.mask===0&&!row.composed;
    assert.equal(handlers,limit?1:0,JSON.stringify(row));assert.equal(f.reports.length,limit?0:1,JSON.stringify(row));
    results.push({...row,handlers,held:f.reports.length});f.cleanup();f.guard.dispose();
  }
  assert.equal(results.length,128);
  console.log('RECHECK3 MIX MATRIX',JSON.stringify(results));
});

test('recheck3 every hyperlink type loses both href authorities and restores only unchanged attributes',async()=>{
  const xlink='http://www.w3.org/1999/xlink';
  for(const type of ['A','AREA','svg-href','svg-xlink','svg-both'])for(const target of ['_self','_blank','sink']){
    const f=fixture({relay:true,nativeShadows:true}),link=type.startsWith('svg')?new f.SVGElement():new f.HTMLElement();link.tagName=type.startsWith('svg')?'a':type;link.textContent='Delete';link.target=target;link.ping='https://fixture.test/ping';
    if(type.startsWith('svg')){link.namespaceURI='http://www.w3.org/2000/svg';link.localName='a';}
    if(type!=='svg-xlink')link.href='https://fixture.test/delete';
    if(['svg-xlink','svg-both'].includes(type))link.setAttributeNS(xlink,'xlink:href','https://fixture.test/legacy');
    f.guard.arm({generation:'epoch',config:{...policy,defaultBlock:'https://aresos-hold.invalid/'},target:f.id(link)});
    f.originalDispatch.call(link,new f.Event('click',{cancelable:false}));
    assert.equal(link.getAttribute('href'),null,type);assert.equal(link.getAttributeNS(xlink,'href'),null,type);assert.equal(link.ping,'https://aresos-hold.invalid/');assert.equal(f.reports[0].kind,'activation');
    // A page's new destination must survive the later restoration task.
    if(target==='sink')link.href='https://fixture.test/new';
    await new Promise(resolve=>setTimeout(resolve,5));
    assert.equal(link.href,target==='sink'?'https://fixture.test/new':type==='svg-xlink'?undefined:'https://fixture.test/delete');
    assert.equal(link.getAttributeNS(xlink,'href'),['svg-xlink','svg-both'].includes(type)?'https://fixture.test/legacy':null);
    assert.equal(link.ping,'https://fixture.test/ping');f.cleanup();f.guard.dispose();
  }
});

test('recheck3 native submitters including images external form buttons and resets are disabled through default',async()=>{
  for(const [tag,type]of [['BUTTON','submit'],['INPUT','submit'],['INPUT','image'],['BUTTON','reset'],['INPUT','reset']]){
    const f=fixture({relay:true,nativeShadows:true}),form=new f.HTMLFormElement(),button=new f.HTMLElement();
    button.tagName=tag;button.type=type;button.textContent='Delete';button.form=form;button.setAttribute('form','external');
    f.guard.arm({generation:'epoch',config:{...policy,defaultBlock:'https://aresos-hold.invalid/'},target:f.id(button)});
    for(let repeat=0;repeat<2;repeat++){f.originalDispatch.call(button,new f.Event('click',{cancelable:false}));assert.equal(button.getAttribute('disabled'),'');}
    assert.ok(f.reports.every(row=>row.kind==='activation'));await new Promise(resolve=>setTimeout(resolve,5));assert.equal(button.getAttribute('disabled'),null);
    f.cleanup();f.guard.dispose();
  }
});

test('recheck3 unrecognised defaults and checkbox preactivation are never falsely reported stopped',()=>{
  for(const [tag,type]of [['SUMMARY',''],['LABEL',''],['SELECT',''],['INPUT','checkbox'],['INPUT','radio'],['INPUT','file'],['DIV','']]){
    const f=fixture({relay:true,nativeShadows:true}),element=new f.HTMLElement();element.tagName=tag;element.type=type;element.textContent='Delete';element.form=new f.HTMLFormElement();
    f.guard.arm({generation:'epoch',config:{...policy,defaultBlock:'https://aresos-hold.invalid/'},target:f.id(element)});
    f.originalDispatch.call(element,new f.Event('click',{cancelable:false}));assert.equal(f.reports[0].kind,'activation_unknown',tag+' '+type);
    f.cleanup();f.guard.dispose();
  }
});


test('recheck3 detached listener branding uses a saved native after the page replaces Node',()=>{
  const f=fixture({relay:true,nativeShadows:true}),host=new f.HTMLElement(),button=new f.HTMLElement();
  button.root=button;button.tagName='BUTTON';button.textContent='Delete';f.main.Node=function PageNode(){};f.arm(host,null);let handlers=0;
  button.addEventListener('click',()=>handlers++);const root=f.nativeAttach.call(host,{mode:'closed'});f.nativeAppend.call(root,button);
  f.originalDispatch.call(button,new f.Event('click',{composed:false}));assert.equal(handlers,0);assert.equal(f.reports.length,1);
  f.cleanup();f.guard.dispose();
});

test('recheck3 a wrapped detached listener from another controlled document installs capture in its owner',()=>{
  for(const mode of ['open','closed']){
    const caller=fixture({relay:true,nativeShadows:true}),owner=fixture({relay:true,nativeShadows:true});
    owner.document.root=owner.document;owner.document.defaultView={};owner.guard.control('epoch');caller.arm(new caller.HTMLElement(),null);
    const host=new owner.HTMLElement(),button=new owner.HTMLElement();button.root=button;button.tagName='BUTTON';button.textContent='Delete';let handlers=0;
    caller.EventTarget.prototype.addEventListener.call(button,'click',()=>handlers++);
    const root=owner.nativeAttach.call(host,{mode});owner.nativeAppend.call(root,button);
    owner.originalDispatch.call(button,new owner.Event('click',{composed:false,cancelable:true}));
    assert.equal(handlers,0,mode);assert.equal(owner.reports.length,1,mode);assert.equal(caller.reports.length,0);
    caller.cleanup();owner.cleanup();caller.guard.dispose();owner.guard.dispose();
  }
});
