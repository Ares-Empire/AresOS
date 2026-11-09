// MAIN, document_start. No state, identities, approval marks or callable control API.
// With no isolated listener a wrapper holds. All native effects run in ISOLATED.
(() => {
  const dispatch=EventTarget.prototype.dispatchEvent, Report=CustomEvent;
  const invoke=Reflect.apply, define=Object.defineProperty;
  function report(target,detail) {
    return invoke(dispatch,target,[new Report('aresos-page-call-v2',{bubbles:true,cancelable:true,composed:false,detail})]);
  }
  // Page replacement of a wrapper must not turn a held call into native delivery.
  function install(prototype,name,value) { define(prototype,name,{value,writable:false,configurable:false}); }
  install(HTMLFormElement.prototype,'submit',function() { report(this,{kind:'native_submit'}); });
  install(HTMLFormElement.prototype,'requestSubmit',function(submitter) { report(this,{kind:'request_submit',submitter}); });
  install(HTMLElement.prototype,'click',function() { report(this,{kind:'click'}); });
  install(EventTarget.prototype,'dispatchEvent',function(event) { return report(this,{kind:'dispatch',event}); });
})();
