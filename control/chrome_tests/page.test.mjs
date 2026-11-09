import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {execFileSync} from 'node:child_process';

const policy=JSON.parse(fs.readFileSync('control/chrome/extension/policy.js','utf8').match(/\{[\s\S]*\}/)[0]);

function fixture({relay=false}={}) {
  const windowListeners=new Map(),reports=[],arrivals=[],nodes=[],bridgeDetails=[];let now=0;
  class Event {
    constructor(type,options={}) {Object.assign(this,{type,cancelable:true,defaultPrevented:false,stopped:false,eventPhase:0,isTrusted:false,...options});}
    preventDefault(){if(this.cancelable)this.defaultPrevented=true;}
    stopImmediatePropagation(){this.stopped=true;}
    composedPath(){return [this.target];}
  }
  class CustomEvent extends Event {constructor(type,options={}){super(type,options);this.detail=options.detail;if(type==='aresos-page-call-v2')bridgeDetails.push(options.detail);}}
  class EventTarget {
    listeners=new Map();
    addEventListener(type,fn){if(!this.listeners.has(type))this.listeners.set(type,[]);this.listeners.get(type).push(fn);}
    removeEventListener(type,fn){this.listeners.set(type,(this.listeners.get(type)||[]).filter(value=>value!==fn));}
    dispatchEvent(event){
      event.target=this;event.eventPhase=1;
      try {
        for(const fn of windowListeners.get(event.type)||[]){fn(event);if(event.stopped)return !event.defaultPrevented;}
        event.eventPhase=2;
        for(const fn of this.listeners.get(event.type)||[]){fn(event);if(event.stopped)break;}
        return !event.defaultPrevented;
      } finally {event.eventPhase=0;}
    }
  }
  const originalDispatch=EventTarget.prototype.dispatchEvent;
  class Node extends EventTarget {getRootNode(){return this.root??document;}}
  class Element extends Node {
    isConnected=true;tagName='DIV';type='';textContent='';form=null;role='';
    constructor(){super();nodes.push(this);}
    get childNodes(){return [{nodeType:3,textContent:this.textContent}];}
    closest(){return this;}
    getAttribute(name){return this[name]||null;}
    matches(){return false;}
    querySelector(){return null;}
    appendChild(node){node.parentNode=this;this.firstElementChild??=node;return node;}
  }
  class HTMLElement extends Element {click(){originalDispatch.call(this,new Event('click'));}}
  class HTMLInputElement extends HTMLElement {}
  class HTMLFormElement extends HTMLElement {
    tagName='FORM'; method='post';action='/receive';valid=true;
    submit(){arrivals.push('native');}
    requestSubmit(submitter){if(!this.valid)return;const event=new Event('submit',{submitter,isTrusted:true});if(originalDispatch.call(this,event))arrivals.push('event');}
  }
  const document=new EventTarget();document.getElementById=key=>document.labels?.[key];
  if(relay)document.createElement=()=>{const node=new HTMLElement();node.root=node;node.ownerDocument=document;node.isConnected=false;node.parentNode=null;return node;};
  const window={addEventListener(type,fn){if(!windowListeners.has(type))windowListeners.set(type,[]);windowListeners.get(type).push(fn);},removeEventListener(type,fn){windowListeners.set(type,(windowListeners.get(type)||[]).filter(value=>value!==fn));}};
  class MessageChannel {port1={close(){}};port2={postMessage:token=>setImmediate(()=>this.port1.onmessage?.({data:token})),close(){}};}
  class AbstractRange {get startContainer(){return this.start;}}
  class StaticRange extends AbstractRange {constructor(options){super();this.start=options.startContainer;}}
  class InputEvent extends Event {constructor(type,options={}){super(type,options);this.ranges=options.targetRanges?Array.from(options.targetRanges):[];}getTargetRanges(){return this.ranges;}}
  const globals={window,document,performance:{now:()=>now},setTimeout,MessageChannel,Symbol,Event,CustomEvent,EventTarget,Node,Element,HTMLElement,HTMLInputElement,HTMLFormElement,DOMException,URL,...(relay?{AbstractRange,StaticRange,InputEvent}:{})};
  const isolated=vm.createContext({...globals});
  vm.runInContext(fs.readFileSync('control/chrome/extension/guard.js','utf8'),isolated);
  const guard=vm.runInContext("globalThis[Symbol.for('aresos.chrome.guard.v2')]",isolated);
  const ids=new Map(), elements=new Map();let sequence=0;
  function id(node){if(!ids.has(node)){const key='e'+(++sequence);ids.set(node,key);elements.set(key,node);}return ids.get(node);}
  function name(node){const labels=(node['aria-labelledby']||'').split(/\s+/).map(key=>document.getElementById(key)).filter(Boolean);return labels.length ? labels.map(label=>label.textContent).join(' ') : node['aria-label'] || node.labels?.map(label=>label.textContent).join(' ') || node.textContent;}
  guard.reader({document:'document-1',id,element:key=>elements.get(key),target:node=>({name:name(node),title:node.title,role:node.role,password:!!node.password,submit:!!node.form && node.type==='submit',editable:node instanceof HTMLInputElement}),form:(node,button)=>{const form=node.form || (node.tagName==='FORM' ? node:null);return form ? {method:button?.formmethod || form.method,search:form.role==='search',action:button?.formAction || form.action,encoding:form.encoding||'application/x-www-form-urlencoded',target:form.target||''}:null;}});
  const main=vm.createContext({...globals});
  const nativeStrings=[HTMLFormElement.prototype.submit,HTMLFormElement.prototype.requestSubmit,HTMLElement.prototype.click,EventTarget.prototype.dispatchEvent].map(fn=>Function.prototype.toString.call(fn));
  const installed=vm.runInContext(fs.readFileSync('control/chrome/extension/page.js','utf8'),main);
  if(relay){guard.relay(installed.relay);installed.activate();}
  const cleanup=relay?installed.cleanup:installed;
  assert.equal(vm.runInContext("globalThis[Symbol.for('aresos.chrome.page.v1')]",main),undefined);
  assert.equal(vm.runInContext("globalThis[Symbol.for('aresos.chrome.guard.v2')]",main),undefined);
  function arm(target,form,operation=null,conservative=false){guard.arm({generation:'epoch',config:{...policy,conservative},target:id(target),form:form ? id(form):null,operation,primary_submission:false});}
  const api={...guard,resume:(id,operation)=>{const step=reports.find(item=>item.id===id);return guard.resume(id,operation,step?.submitter||step?.element,step?.element);}};
  return {api,guard,arrivals,bridgeDetails,cleanup,nativeStrings,Node,EventTarget,get reports(){reports.push(...guard.steps());return reports;},document,HTMLFormElement,HTMLElement,HTMLInputElement,Event,CustomEvent,originalDispatch,arm,main,id,advance:milliseconds=>{now+=milliseconds;}};
}

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
  const f=fixture({relay:true}),button=new f.HTMLElement();button.textContent='Ordinary control';button.tagName='BUTTON';f.arm(button,null);let received=0;button.addEventListener('click',()=>received++);
  vm.runInContext("globalThis.callbacks=0;Object.keys=()=>{callbacks++;throw 'page keys'};for(const key of ['bubbles','composed','get','set','request']){const description=Object.create(null);description.configurable=true;description.get=function(){callbacks++;throw 'page getter'};Object.defineProperty(Object.prototype,key,description);}Array.prototype[Symbol.iterator]=function(){callbacks++;throw 'page iterator'}",f.main);
  assert.equal(button.dispatchEvent(new f.Event('click')),true);assert.equal(received,1);assert.equal(vm.runInContext('callbacks',f.main),0);
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
  form.requestSubmit();assert.equal(f.arrivals.length,1,'default action after eventPhase resets still belongs to this exact input');
  form.requestSubmit();assert.equal(f.arrivals.length,1,'the task mark grants exactly one submission');
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
  f.originalDispatch.call(field,new f.Event('keydown',{key:'Enter',isTrusted:true}));form.requestSubmit();assert.equal(f.arrivals.length,0,'Enter cannot submit a multi-field form without a default button');
  form.elements=[field];f.originalDispatch.call(field,new f.Event('keydown',{key:'Enter',isTrusted:true}));form.requestSubmit();assert.equal(f.arrivals.length,1,'the same one-field implicit submission is its native default');
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
