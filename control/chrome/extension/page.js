// MAIN, document_start. Wrapper-local recursion tracking grants no authority.
// Private ISOLATED decisions permit native clicks/events; missing decisions hold.
// Forms and resumptions stay in ISOLATED. No page can reach the private carrier.
(() => {
  'use strict';
  const dispatch=EventTarget.prototype.dispatchEvent, Report=CustomEvent;
  const invoke=Reflect.apply, define=Object.defineProperty;
  const create=Object.create,keys=Object.keys,iterator=Symbol.iterator;
  const options=values=>{const result=create(null),names=keys(values);for(let index=0;index<names.length;index++)result[names[index]]=values[names[index]];return result;};
  const property=(object,key,value,enumerable=false)=>{const description=create(null);description.value=value;description.enumerable=enumerable;define(object,key,description);};
  const descriptor=Object.getOwnPropertyDescriptor;
  const ownDocument=document,root=globalThis.Node?.prototype.getRootNode;
  const defaultView=globalThis.Document&&descriptor(Document.prototype,'defaultView')?.get;
  const windowDocument=descriptor(globalThis,'document')?.get||(globalThis.Window&&descriptor(Window.prototype,'document')?.get);
  const nodeType=globalThis.Node?descriptor(Node.prototype,'nodeType')?.get:null;
  const shadowHost=globalThis.ShadowRoot&&descriptor(ShadowRoot.prototype,'host')?.get;
  const parentNode=globalThis.Node&&descriptor(Node.prototype,'parentNode')?.get;
  const previousSibling=globalThis.Node&&descriptor(Node.prototype,'previousSibling')?.get;
  const saved={submit:HTMLFormElement.prototype.submit,requestSubmit:HTMLFormElement.prototype.requestSubmit,click:HTMLElement.prototype.click,dispatchEvent:dispatch,attachShadow:globalThis.Element?.prototype.attachShadow};
  const nativeString=Function.prototype.toString,nativeStrings=new WeakMap(),getString=WeakMap.prototype.get,setString=WeakMap.prototype.set;
  const connected=target=>{try{const owner=root?invoke(root,target,[options({composed:true})]):target.getRootNode({composed:true});return owner===ownDocument||!!(defaultView?invoke(defaultView,owner,[]):owner.defaultView);}catch{return false;}};
  const installed=[];
  const privateRelay=globalThis.StaticRange&&globalThis.InputEvent&&document.createElement?document.createElement('div'):null;
  const privateControl=privateRelay?document.createElement('span'):null;
  if(typeof globalThis.Document==='function'&&!privateRelay)throw Error('The private native relay is unavailable; this document cannot be controlled.');
  if(privateRelay)privateRelay.appendChild(privateControl);
  const TargetEvent=globalThis.InputEvent,TargetRange=globalThis.StaticRange,Signal=Event;
  const removeListener=EventTarget.prototype.removeEventListener;
  let enabled=false,closed=false;
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
  function payload(event,key){
    let value;try{value=read(event,key);}catch{}
    if(value===undefined)try{value=event[key];}catch{}
    const kind=typeof value;
    return kind==='string'||kind==='number'||kind==='boolean'?value:undefined;
  }
  const prevent=Event.prototype.preventDefault;
  const dispatching=new WeakSet();
  const has=WeakSet.prototype.has,add=WeakSet.prototype.add,remove=WeakSet.prototype.delete;
  let requestSequence=0;
  let dialogSequence=0;
  function report(target,detail,original=null) {
    if(privateRelay){
      const request=++requestSequence;property(detail,'request',request,true);
      let anchor=target,path='';
      while(shadowHost){
        const localRoot=invoke(root,anchor,[]);let host;try{host=invoke(shadowHost,localRoot,[]);}catch{break;}if(!host)break;
        let node=anchor,relative='';
        while(node!==localRoot){let index=0,sibling=invoke(previousSibling,node,[]);while(sibling){index++;sibling=invoke(previousSibling,sibling,[]);}relative='.'+index+relative;node=invoke(parentNode,node,[]);if(!node)throw Error('native shadow path changed');}
        path='s'+relative+(path?'.'+path:'');anchor=host;
      }
      property(detail,'target_path',path,true);
      invoke(dispatch,privateControl,[new Report('aresos-relay-meta',options({detail}))]);
      try{
        const range=new TargetRange(options({startContainer:anchor,startOffset:0,endContainer:anchor,endOffset:0}));
        const ranges=create(null);property(ranges,iterator,()=>{let done=false;const result=create(null);result.next=()=>{const step=create(null);step.done=done;if(!done){done=true;step.value=range;}return step;};return result;});
        invoke(dispatch,privateControl,[new TargetEvent('aresos-relay-target',options({data:''+request,targetRanges:ranges}))]);
        const allowed=!invoke(dispatch,privateControl,[new Report('aresos-relay-deliver',options({cancelable:true,detail:request}))]);
        if(original){if(!allowed||read(original,'type')!==detail.event_type||!connected(target))return false;return invoke(saved.dispatchEvent,target,[original]);}
        if(detail.kind==='click'&&allowed&&connected(target))invoke(saved.click,target,[]);
        return allowed;
      }finally{invoke(dispatch,privateControl,[new Report('aresos-relay-drop',options({detail:request}))]);}
    }
    // Browser-free DOM doubles exercise the same guard through primitive reports.
    return invoke(dispatch,target,[new Report('aresos-page-call-v2',{bubbles:true,cancelable:true,composed:true,detail})]);
  }
  // Replacement cannot recover a saved native. A borrowed fresh-frame native is
  // the separately reported fallback; sites may still patch their own methods.
  function install(prototype,name,implementation) { const value=({method(...args){return invoke(implementation,this,args);}}).method;const previous=options(descriptor(prototype,name));invoke(setString,nativeStrings,[value,invoke(nativeString,previous.value,[])]);define(value,'name',options({value:previous.value.name,configurable:true}));define(value,'length',options({value:previous.value.length,configurable:true}));define(prototype,name,options({...previous,value}));installed.push({prototype,name,value,previous}); }
  function activate(){
  if(closed)throw Error('The document guard was disposed');if(enabled)return;enabled=true;
  if(saved.attachShadow)install(Element.prototype,'attachShadow',function(){const result=invoke(saved.attachShadow,this,arguments);report(result,{kind:'watch_root'});return result;});
  for(const name of ['alert','confirm','prompt']){
    let prototype=globalThis;while(prototype&&!descriptor(prototype,name))prototype=Object.getPrototypeOf(prototype);
    const method=prototype&&descriptor(prototype,name)?.value;if(typeof method!=='function')continue;
    install(prototype,name,function(){
      if(!enabled)return invoke(method,this,arguments);
      let target;try{target=this==null||this===globalThis?ownDocument:windowDocument?invoke(windowDocument,this,[]):this.document;}catch{return invoke(method,this,arguments);}
      if(!target||!connected(target))return invoke(method,this,arguments);
      const token='d'+(++dialogSequence);report(target,{kind:'dialog_begin',token,dialog_kind:name});
      try{return invoke(method,this,arguments);}finally{report(target,{kind:'dialog_end',token,dialog_kind:name});}
    });
  }
  install(Function.prototype,'toString',function(){return invoke(getString,nativeStrings,[this])??invoke(nativeString,this,[]);});
  install(HTMLFormElement.prototype,'submit',function() { if(!enabled||!connected(this))return invoke(saved.submit,this,[]);report(this,{kind:'native_submit'}); });
  install(HTMLFormElement.prototype,'requestSubmit',function(submitter) {
    if(!enabled||!connected(this))return invoke(saved.requestSubmit,this,arguments);
    if(formElements)invoke(formElements,this,[]);
    if(submitter==null){report(this,{kind:'request_submit'});return;}
    let form,type,valid=false;
    for(let index=0;index<submitterGetters.length;index++){const getter=submitterGetters[index];if(!getter.form||!getter.type)continue;try{form=invoke(getter.form,submitter,[]);type=invoke(getter.type,submitter,[]);valid=true;break;}catch{}}
    if(!formElements){form=submitter.form;type=submitter.type;valid=true;} // browser-free test doubles
    if(!valid||(type!=='submit'&&type!=='image'))throw new TypeError('The submitter is not a submit button.');
    if(form!==this)throw new DOMException('The submitter belongs to another form.','NotFoundError');
    report(submitter,{kind:'request_submit',with_submitter:true});
  });
  install(HTMLElement.prototype,'click',function() { if(!enabled||!connected(this))return invoke(saved.click,this,[]);report(this,{kind:'click'}); });
  install(EventTarget.prototype,'dispatchEvent',function(event) {
    if(!enabled||!connected(this))return invoke(saved.dispatchEvent,this,[event]);
    if(nodeType&&invoke(nodeType,this,[])===10)return invoke(saved.dispatchEvent,this,[event]);
    // These event types have no asking native activation. Their handlers still
    // enter the click/submit wrappers, while object identity and custom data stay native.
    if(getters.type){const kind=read(event,'type');if(kind!=='click'&&kind!=='submit')return invoke(saved.dispatchEvent,this,[event]);}
    if(invoke(has,dispatching,[event]))throw new DOMException('The event is already being dispatched.','InvalidStateError');
    invoke(add,dispatching,[event]);
    try{
    if(read(event,'eventPhase'))throw new DOMException('The event is already being dispatched.','InvalidStateError');
    if(privateRelay){const delivered=report(this,{kind:'dispatch',event_type:read(event,'type')},event);if(!delivered)invoke(prevent,event,[]);return delivered;}
    const detail={kind:'dispatch',event_type:read(event,'type'),event_flags:{bubbles:read(event,'bubbles'),cancelable:read(event,'cancelable'),composed:read(event,'composed'),prevented:read(event,'defaultPrevented')}};
    // No Event or DOM reference crosses this page-forgeable bridge. The private
    // listener constructs and classifies a fresh untrusted event from data only.
    const keys=['key','code','location','repeat','ctrlKey','shiftKey','altKey','metaKey','button','buttons','clientX','clientY','screenX','screenY','data','inputType','isComposing'];
    for(let index=0;index<keys.length;index++){const key=keys[index];define(detail,key,{enumerable:true,get(){return payload(event,key);}});}
    const delivered=report(this,detail);if(!delivered)invoke(prevent,event,[]);return delivered;
    }
    finally{invoke(remove,dispatching,[event]);}
  });
  }
  // Runtime.evaluate retains this return value as a private remote handle. It is
  // never a global or a DOM capability the page can invoke to end its hold.
  function cleanup(){closed=true;enabled=false;let restored=true;for(let index=0;index<installed.length;index++){const item=installed[index],current=descriptor(item.prototype,item.name);if(current&&descriptor(current,'value')&&current.value===item.value){try{define(item.prototype,item.name,item.previous);}catch{try{define(item.prototype,item.name,options({value:item.previous.value}));}catch{restored=false;}}}}return restored;}
  if(privateControl)privateControl.addEventListener('aresos-relay-cleanup',event=>{if(cleanup())event.preventDefault();});
  if(privateRelay)return {activate,cleanup,relay:privateRelay};
  activate();return cleanup;
})();
