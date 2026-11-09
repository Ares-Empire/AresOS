// MAIN, document_start. No state, identities, approval marks or callable control API.
// With no isolated listener a wrapper holds. All native effects run in ISOLATED.
(() => {
  const dispatch=EventTarget.prototype.dispatchEvent, Report=CustomEvent;
  function report(target,detail) {
    return dispatch.call(target,new Report('aresos-page-call-v2',{bubbles:true,cancelable:true,composed:false,detail}));
  }
  HTMLFormElement.prototype.submit=function() { report(this,{kind:'native_submit'}); };
  HTMLFormElement.prototype.requestSubmit=function(submitter) { report(this,{kind:'request_submit',submitter}); };
  HTMLElement.prototype.click=function() { report(this,{kind:'click'}); };
  EventTarget.prototype.dispatchEvent=function(event) { return report(this,{kind:'dispatch',event}); };
})();
