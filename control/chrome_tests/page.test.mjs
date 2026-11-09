import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {execFileSync} from 'node:child_process';

const policy=JSON.parse(fs.readFileSync('control/chrome/extension/policy.js','utf8').match(/\{[\s\S]*\}/)[0]);

function fixture() {
  const windowListeners=new Map(),reports=[],arrivals=[],nodes=[];let now=0;
  class Event {
    constructor(type,options={}) {Object.assign(this,{type,cancelable:true,defaultPrevented:false,stopped:false,eventPhase:0,isTrusted:false,...options});}
    preventDefault(){if(this.cancelable)this.defaultPrevented=true;}
    stopImmediatePropagation(){this.stopped=true;}
    composedPath(){return [this.target];}
  }
  class CustomEvent extends Event {constructor(type,options={}){super(type,options);this.detail=options.detail;}}
  class EventTarget {
    listeners=new Map();
    addEventListener(type,fn){if(!this.listeners.has(type))this.listeners.set(type,[]);this.listeners.get(type).push(fn);}
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
  class Element extends EventTarget {
    isConnected=true;tagName='DIV';type='';textContent='';form=null;role='';
    constructor(){super();nodes.push(this);}
    get childNodes(){return [{nodeType:3,textContent:this.textContent}];}
    getRootNode(){return document;}
    closest(){return this;}
    getAttribute(name){return this[name]||null;}
    matches(){return false;}
    querySelector(){return null;}
  }
  class HTMLElement extends Element {click(){originalDispatch.call(this,new Event('click'));}}
  class HTMLInputElement extends HTMLElement {}
  class HTMLFormElement extends HTMLElement {
    tagName='FORM'; method='post';action='/receive';valid=true;
    submit(){arrivals.push('native');}
    requestSubmit(submitter){if(!this.valid)return;const event=new Event('submit',{submitter});if(originalDispatch.call(this,event))arrivals.push('event');}
  }
  const document=new EventTarget();document.getElementById=key=>document.labels?.[key];
  const window={addEventListener(type,fn){if(!windowListeners.has(type))windowListeners.set(type,[]);windowListeners.get(type).push(fn);}};
  const globals={window,document,performance:{now:()=>now},setTimeout,Symbol,Event,CustomEvent,EventTarget,Element,HTMLElement,HTMLInputElement,HTMLFormElement,DOMException};
  const isolated=vm.createContext({...globals});
  vm.runInContext(fs.readFileSync('control/chrome/extension/guard.js','utf8'),isolated);
  const guard=vm.runInContext("globalThis[Symbol.for('aresos.chrome.guard.v2')]",isolated);
  const ids=new Map(), elements=new Map();let sequence=0;
  function id(node){if(!ids.has(node)){const key='e'+(++sequence);ids.set(node,key);elements.set(key,node);}return ids.get(node);}
  function name(node){const labels=(node['aria-labelledby']||'').split(/\s+/).map(key=>document.getElementById(key)).filter(Boolean);return labels.length ? labels.map(label=>label.textContent).join(' ') : node['aria-label'] || node.labels?.map(label=>label.textContent).join(' ') || node.textContent;}
  guard.reader({document:'document-1',id,element:key=>elements.get(key),target:node=>({name:name(node),title:node.title,role:node.role,password:!!node.password,submit:!!node.form && node.type==='submit',editable:node instanceof HTMLInputElement}),form:(node,button)=>{const form=node.form || (node.tagName==='FORM' ? node:null);return form ? {method:button?.formmethod || form.method,search:form.role==='search',action:button?.formAction || form.action,encoding:form.encoding||'application/x-www-form-urlencoded',target:form.target||''}:null;}});
  const main=vm.createContext({...globals});
  vm.runInContext(fs.readFileSync('control/chrome/extension/page.js','utf8'),main);
  assert.equal(vm.runInContext("globalThis[Symbol.for('aresos.chrome.page.v1')]",main),undefined);
  assert.equal(vm.runInContext("globalThis[Symbol.for('aresos.chrome.guard.v2')]",main),undefined);
  function arm(target,form,operation=null,conservative=false){guard.arm({generation:'epoch',config:{...policy,conservative},target:id(target),form:form ? id(form):null,operation,primary_submission:false});}
  const api={...guard,resume:(id,operation)=>{const step=reports.find(item=>item.id===id);return guard.resume(id,operation,step?.submitter||step?.element,step?.element);}};
  return {api,guard,arrivals,get reports(){reports.push(...guard.steps());return reports;},document,HTMLFormElement,HTMLElement,Event,CustomEvent,originalDispatch,arm,main,id,advance:milliseconds=>{now+=milliseconds;}};
}

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
  const f=fixture(),form=new f.HTMLFormElement();form.method='get';form.role='search';
  f.arm(form,form,null);form.requestSubmit();assert.equal(f.arrivals.length,1);assert.equal(f.reports.length,0);
  const button=new f.HTMLElement();button.formmethod='post';button.form=form;form.requestSubmit(button);
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

test('group2 owner exemption is synchronous and never covers delayed or in-flight input',async()=>{
  const f=fixture(),form=new f.HTMLFormElement(),button=new f.HTMLElement();f.arm(button,null);
  button.addEventListener('click',()=>form.submit());
  f.originalDispatch.call(button,new f.Event('click',{isTrusted:true}));assert.equal(f.arrivals.length,0,'in-flight owner is held');
  await f.api.finish('epoch');
  f.originalDispatch.call(button,new f.Event('click',{isTrusted:true}));assert.equal(f.arrivals.length,1,'synchronous owner handler is exempt');
  form.submit();assert.equal(f.arrivals.length,1,'the exemption ends when dispatch ends');
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
  assert.throws(()=>{f.HTMLFormElement.prototype.submit=function(){};});
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
