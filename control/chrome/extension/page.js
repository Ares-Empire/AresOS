// MAIN, document_start. No state, identities, approval marks or callable control API.
// With no isolated listener a wrapper holds. All native effects run in ISOLATED.
(() => {
  'use strict';
  const dispatch=EventTarget.prototype.dispatchEvent, Report=CustomEvent;
  const invoke=Reflect.apply, define=Object.defineProperty;
  const descriptor=Object.getOwnPropertyDescriptor;
  const getters={};
  const formElements=descriptor(HTMLFormElement.prototype,'elements')?.get;
  const submitterGetters=[globalThis.HTMLButtonElement?.prototype,globalThis.HTMLInputElement?.prototype].filter(Boolean).map(prototype=>({form:descriptor(prototype,'form')?.get,type:descriptor(prototype,'type')?.get}));
  for(const prototype of [Event.prototype,globalThis.UIEvent?.prototype,globalThis.MouseEvent?.prototype,globalThis.KeyboardEvent?.prototype,globalThis.InputEvent?.prototype]){
    if(!prototype)continue;
    for(const key of ['type','eventPhase','defaultPrevented','bubbles','cancelable','composed','key','code','location','repeat','ctrlKey','shiftKey','altKey','metaKey','button','buttons','clientX','clientY','screenX','screenY','data','inputType','isComposing']){
      const getter=descriptor(prototype,key)?.get;if(getter)(getters[key]??=[]).push(getter);
    }
  }
  const read=(event,key)=>{
    const alternatives=getters[key];
    if(alternatives){for(let index=0;index<alternatives.length;index++)try{return invoke(alternatives[index],event,[]);}catch{}throw new TypeError('Invalid event brand');}
    // Test doubles have no native descriptors; Chrome never reads expandos.
    if(!getters.type)return event[key];
  };
  const prevent=Event.prototype.preventDefault;
  const dispatching=new WeakSet();
  const has=WeakSet.prototype.has,add=WeakSet.prototype.add,remove=WeakSet.prototype.delete;
  function report(target,detail) {
    return invoke(dispatch,target,[new Report('aresos-page-call-v2',{bubbles:true,cancelable:true,composed:false,detail})]);
  }
  // Page replacement of a wrapper must not turn a held call into native delivery.
  function install(prototype,name,value) { define(prototype,name,{value,writable:false,configurable:false}); }
  install(HTMLFormElement.prototype,'submit',function() { report(this,{kind:'native_submit'}); });
  install(HTMLFormElement.prototype,'requestSubmit',function(submitter) {
    if(formElements)invoke(formElements,this,[]);
    if(submitter==null){report(this,{kind:'request_submit'});return;}
    let form,type,valid=false;
    for(let index=0;index<submitterGetters.length;index++){const getter=submitterGetters[index];if(!getter.form||!getter.type)continue;try{form=invoke(getter.form,submitter,[]);type=invoke(getter.type,submitter,[]);valid=true;break;}catch{}}
    if(!formElements){form=submitter.form;type=submitter.type;valid=true;} // browser-free test doubles
    if(!valid||!['submit','image'].includes(type))throw new TypeError('The submitter is not a submit button.');
    if(form!==this)throw new DOMException('The submitter belongs to another form.','NotFoundError');
    report(submitter,{kind:'request_submit',with_submitter:true});
  });
  install(HTMLElement.prototype,'click',function() { report(this,{kind:'click'}); });
  install(EventTarget.prototype,'dispatchEvent',function(event) {
    if(invoke(has,dispatching,[event]))throw new DOMException('The event is already being dispatched.','InvalidStateError');
    invoke(add,dispatching,[event]);
    try{
    if(read(event,'eventPhase'))throw new DOMException('The event is already being dispatched.','InvalidStateError');
    const detail={kind:'dispatch',event_type:read(event,'type'),event_flags:{bubbles:read(event,'bubbles'),cancelable:read(event,'cancelable'),composed:read(event,'composed'),prevented:read(event,'defaultPrevented')}};
    // No Event or DOM reference crosses this page-forgeable bridge. The private
    // listener constructs and classifies a fresh untrusted event from data only.
    define(detail,'event_data',{get(){const data={},keys=['key','code','location','repeat','ctrlKey','shiftKey','altKey','metaKey','button','buttons','clientX','clientY','screenX','screenY','data','inputType','isComposing'];for(let index=0;index<keys.length;index++){const key=keys[index];try{data[key]=read(event,key);}catch{}}return data;}});
    const delivered=report(this,detail);if(!delivered)invoke(prevent,event,[]);return delivered;
    }
    finally{invoke(remove,dispatching,[event]);}
  });
})();
