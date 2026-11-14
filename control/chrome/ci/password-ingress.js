// Test-build only, ISOLATED before the reader; records native getter results.
(() => {
  const query=new URL(location.href).searchParams;
  if(!/^password(?:-|$)/.test(query.get('case')||'')&&!(query.get('case')==='review-page'&&['late-reader','late-binding','late-binding-child','late-withheld-form'].includes(query.get('mode'))))return;
  const emit=(kind,value)=>{chrome.runtime.sendMessage({event:'reader_ingress',kind,value}).catch(()=>{});return value;};
  for(const [prototype,key]of [[HTMLInputElement.prototype,'value'],[HTMLTextAreaElement.prototype,'value'],[HTMLSelectElement.prototype,'value'],[Node.prototype,'textContent'],[HTMLElement.prototype,'innerText'],[HTMLIFrameElement.prototype,'srcdoc']]){
    const descriptor=Object.getOwnPropertyDescriptor(prototype,key);if(!descriptor?.get)throw Error('Missing sensitive getter '+key);
    const get=descriptor.get;Object.defineProperty(prototype,key,{...descriptor,get(){return emit(key,get.call(this));}});
  }
  const attribute=Element.prototype.getAttribute;
  Element.prototype.getAttribute=function(key){const value=attribute.call(this,key);return /^(?:value|srcdoc)$/i.test(key)?emit('attribute:'+key,value):value;};
})();
