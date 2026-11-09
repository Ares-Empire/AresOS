import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

function fixture() {
  const windowListeners=new Map(),reports=[],arrivals=[];
  class Event {
    constructor(type,options={}) {Object.assign(this,{type,cancelable:true,defaultPrevented:false,stopped:false,...options});}
    preventDefault(){if(this.cancelable)this.defaultPrevented=true;}
    stopImmediatePropagation(){this.stopped=true;}
    composedPath(){return [this.target];}
  }
  class CustomEvent extends Event {constructor(type,options={}){super(type,options);this.detail=options.detail;}}
  class EventTarget {
    listeners=new Map();
    addEventListener(type,fn){if(!this.listeners.has(type))this.listeners.set(type,[]);this.listeners.get(type).push(fn);}
    dispatchEvent(event){
      event.target ||= this;
      for(const fn of windowListeners.get(event.type)||[]){fn(event);if(event.stopped)return !event.defaultPrevented;}
      for(const fn of this.listeners.get(event.type)||[]){fn(event);if(event.stopped)break;}
      if(this!==document && event.bubbles)for(const fn of document.listeners.get(event.type)||[])fn(event);
      return !event.defaultPrevented;
    }
  }
  class Element extends EventTarget {
    isConnected=true;tagName='DIV';type='';textContent='';form=null;role='';
    closest(){return this;}
    getAttribute(name){return this[name]||null;}
    matches(){return false;}
    querySelector(){return null;}
    attachShadow(){return new EventTarget();}
  }
  class HTMLElement extends Element {click(){this.dispatchEvent(new Event('click'));}}
  class HTMLInputElement extends HTMLElement {}
  class HTMLFormElement extends HTMLElement {
    tagName='FORM'; method='post';action='/receive';valid=true;
    submit(){arrivals.push('native');}
    requestSubmit(submitter){if(!this.valid)return;const event=new Event('submit',{submitter});if(this.dispatchEvent(event))arrivals.push('event');}
  }
  const document=new EventTarget();document.addEventListener('aresos-page-step',event=>reports.push(event.detail));
  const window={addEventListener(type,fn){if(!windowListeners.has(type))windowListeners.set(type,[]);windowListeners.get(type).push(fn);}};
  const context=vm.createContext({window,document,performance:{now:()=>0},Symbol,Event,CustomEvent,EventTarget,Element,HTMLElement,HTMLInputElement,HTMLFormElement});
  vm.runInContext(fs.readFileSync('control/chrome/extension/page.js','utf8'),context);
  const api=vm.runInContext("globalThis[Symbol.for('aresos.chrome.page.v1')]",context);
  function identify(id,element){if(!element)return;element.dispatchEvent(new CustomEvent('aresos-reader-identity',{bubbles:true,composed:true,detail:{id}}));}
  const config={words:['send','delete'],holdMs:500};
  return {api,arrivals,reports,HTMLFormElement,HTMLElement,Event,identify,arm:(target,form,op=null)=>{identify('target',target);identify('form',form);api.arm(config,'target','form',op);}};
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
  assert.equal(f.arrivals.length,0);assert.deepEqual(f.reports.map(report=>report.kind),['native_submit','submit_event']);
});

test('group2 an approved change has only one same-form consequential submission',()=>{
  const f=fixture(),form=new f.HTMLFormElement(),field=new f.HTMLElement();field.form=form;
  f.arm(field,form,'approved-change');form.submit();form.submit();
  assert.equal(f.arrivals.length,1);assert.equal(f.reports.length,1);
});

test('group1 GET searches stay free but a POST submitter override is held',()=>{
  const f=fixture(),form=new f.HTMLFormElement();form.method='get';form.role='search';
  f.arm(form,form,null);form.requestSubmit();assert.equal(f.arrivals.length,1);assert.equal(f.reports.length,0);
  const button=new f.HTMLElement();button.formmethod='post';form.requestSubmit(button);
  assert.equal(f.arrivals.length,1);assert.equal(f.reports.length,1);
});
