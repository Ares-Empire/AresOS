// MAIN, document_start. Wrapper-local recursion tracking grants no authority.
// Private ISOLATED decisions permit native clicks/events; missing decisions hold.
// Forms and resumptions stay in ISOLATED. No page can reach the private carrier.
(() => {
  'use strict';
  const dispatch=EventTarget.prototype.dispatchEvent, Report=CustomEvent;
  const invoke=Reflect.apply, define=Object.defineProperty;
  const ownClipboard=globalThis.navigator?.clipboard,clipboardThen=Promise.prototype.then;
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
  const removeListener=EventTarget.prototype.removeEventListener,nativeListen=EventTarget.prototype.addEventListener;
  const ownerDocument=globalThis.Node&&descriptor(Node.prototype,'ownerDocument')?.get;
  const Ref=WeakRef,deref=WeakRef.prototype.deref,foreignNodes=new WeakSet(),foreignRefs=[];
  const foreignCarriers=new WeakMap(),mapGet=WeakMap.prototype.get,mapSet=WeakMap.prototype.set;
  const getAttribute=Element.prototype.getAttribute,setAttribute=Element.prototype.setAttribute,removeAttribute=Element.prototype.removeAttribute;
  const firstElement=globalThis.Element&&descriptor(Element.prototype,'firstElementChild')?.get;
  let relayKey=null,relayValue=null;
  const nodeDocument=node=>node===ownDocument||nodeType&&invoke(nodeType,node,[])===9?node:(ownerDocument?invoke(ownerDocument,node,[]):node.ownerDocument);
  function identify(key,value){if(closed||!privateRelay)return false;relayKey=key;relayValue=value;invoke(setAttribute,privateRelay,[key,value]);return true;}
  function link(node,key,value){
    if(closed||!node||invoke(getAttribute,node,[key])!==value)return false;
    const control=firstElement?invoke(firstElement,node,[]):node.firstElementChild,doc=nodeDocument(node);
    if(!control||!doc||doc===ownDocument)return false;
    invoke(mapSet,foreignCarriers,[doc,{node,control,key,value}]);return true;
  }
  function carrier(target){
    const doc=nodeDocument(target);if(!doc||doc===ownDocument)return privateControl;
    const record=invoke(mapGet,foreignCarriers,[doc]);
    return record&&invoke(getAttribute,record.node,[record.key])===record.value?record.control:null;
  }
  function sourceHold(){if(!enabled)return null;if(defaultView&&windowDocument){try{const view=invoke(defaultView,ownDocument,[]);if(!view||invoke(windowDocument,view,[])!==ownDocument)return null;}catch{return null;}}const detail=create(null);invoke(dispatch,privateControl,[new Report('aresos-relay-source-hold',options({detail}))]);return detail.value;}

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
  function endpoint(target){
      let anchor=target,path='';
      while(shadowHost){
        const localRoot=invoke(root,anchor,[]);let host;try{host=invoke(shadowHost,localRoot,[]);}catch{break;}if(!host)break;
        let node=anchor,relative='';
        while(node!==localRoot){let index=0,sibling=invoke(previousSibling,node,[]);while(sibling){index++;sibling=invoke(previousSibling,sibling,[]);}relative='.'+index+relative;node=invoke(parentNode,node,[]);if(!node)throw Error('native shadow path changed');}
        path='s'+relative+(path?'.'+path:'');anchor=host;
      }
      return {anchor,path};
  }
  function watchForeign(node){
    if(!invoke(has,foreignNodes,[node])){
      invoke(add,foreignNodes,[node]);const record=create(null);record.node=new Ref(node);
      record.listener=event=>{if(event.isTrusted)return;const target=invoke(deref,record.node,[]);if(target)report(target,{kind:read(event,'type')==='click'?'foreign_click':'watch_node'},event);};
      foreignRefs[foreignRefs.length]=new Ref(record);
      for(const kind of ['click','submit'])invoke(nativeListen,node,[kind,record.listener,true]);
    }
    report(node,{kind:'watch_node'});
  }
  function report(target,detail,original=null) {
    if(privateRelay){
      const control=carrier(target);
      if(!control){if(original&&detail.kind==='dispatch')return invoke(saved.dispatchEvent,target,[original]);if(detail.kind==='click')invoke(saved.click,target,[]);else if(detail.kind==='native_submit')invoke(saved.submit,target,[]);else if(detail.kind==='request_submit')invoke(saved.requestSubmit,detail.with_submitter?target.form:target,detail.with_submitter?[target]:[]);return true;}
      if(control!==privateControl)invoke(dispatch,control,[new Report('aresos-relay-source',options({detail:sourceHold}))]);
      const request=++requestSequence;property(detail,'request',request,true);
      const {anchor,path}=endpoint(target);property(detail,'target_path',path,true);
      invoke(dispatch,control,[new Report('aresos-relay-meta',options({detail}))]);
      try{
        if(detail.kind==='foreign_click')invoke(dispatch,control,[new Report('aresos-relay-original',options({detail:original}))]);
        const range=new TargetRange(options({startContainer:anchor,startOffset:0,endContainer:anchor,endOffset:0}));
        const ranges=create(null);property(ranges,iterator,()=>{let done=false;const result=create(null);result.next=()=>{const step=create(null);step.done=done;if(!done){done=true;step.value=range;}return step;};return result;});
        invoke(dispatch,control,[new TargetEvent('aresos-relay-target',options({data:''+request,targetRanges:ranges}))]);
        const allowed=!invoke(dispatch,control,[new Report('aresos-relay-deliver',options({cancelable:true,detail:request}))]);
        if(original&&detail.kind==='dispatch'){if(!allowed||read(original,'type')!==detail.event_type||!connected(target))return false;return invoke(saved.dispatchEvent,target,[original]);}
        if(detail.kind==='click'&&allowed&&connected(target))invoke(saved.click,target,[]);
        return allowed;
      }finally{invoke(dispatch,control,[new Report('aresos-relay-drop',options({detail:request}))]);}
    }
    // Browser-free DOM doubles exercise the same guard through primitive reports.
    return invoke(dispatch,target,[new Report('aresos-page-call-v2',{bubbles:true,cancelable:true,composed:true,detail})]);
  }
  // Replacement cannot recover a saved native. A borrowed fresh-frame native is
  // the separately reported fallback; sites may still patch their own methods.
  function install(prototype,name,implementation) { const value=({method(...args){return invoke(implementation,this,args);}}).method;const previous=options(descriptor(prototype,name));invoke(setString,nativeStrings,[value,invoke(nativeString,previous.value,[])]);define(value,'name',options({value:previous.value.name,configurable:true}));define(value,'length',options({value:previous.value.length,configurable:true}));define(prototype,name,options({...previous,value}));installed.push({prototype,name,value,previous}); }
  function activate(){
  if(closed)throw Error('The document guard was disposed');if(enabled)return;enabled=true;
  if(ownClipboard&&globalThis.Clipboard)for(const name of ['write','writeText']){
    const method=descriptor(Clipboard.prototype,name)?.value;if(typeof method!=='function')continue;
    install(Clipboard.prototype,name,function(){
      const result=invoke(method,this,arguments);
      if(!enabled||this!==ownClipboard)return result;
      try{return invoke(clipboardThen,result,[value=>{
        // Observe only successful completion. Arguments and clipboard contents
        // never enter the relay; a reporting failure cannot change the write.
        if(enabled)try{report(ownDocument,{kind:'clipboard_write',route:name});}catch{}
        return value;
      }]);}catch{return result;}
    });
  }
  if(saved.attachShadow)install(Element.prototype,'attachShadow',function(){const result=invoke(saved.attachShadow,this,arguments);report(result,{kind:'watch_root'});return result;});
  // Capture travels with the node even when a borrowed native inserts it into
  // a new closed root and dispatches a non-composed event in the same stack.
  function watchCreated(node){if(!enabled)return node;if(nodeType){const kind=invoke(nodeType,node,[]);if(kind===2||kind===10)return node;}const doc=ownerDocument?invoke(ownerDocument,node,[]):node.ownerDocument;if(doc&&doc!==ownDocument){if(carrier(node))watchForeign(node);return node;}report(node,{kind:'watch_node'});return node;}
  for(const [prototype,names] of [[globalThis.Document?.prototype,['createElement','createElementNS','importNode']],
    [globalThis.Node?.prototype,['cloneNode']]])for(const name of names){
    const method=prototype&&descriptor(prototype,name)?.value;
    if(typeof method==='function')install(prototype,name,function(){return watchCreated(invoke(method,this,arguments));});
  }
  for(const prototype of [globalThis.HTMLElement?.prototype,globalThis.SVGElement?.prototype]){
    const previous=prototype&&descriptor(prototype,'onclick');if(!previous?.set)continue;
    const method=previous.set,value=({set onclick(handler){watchCreated(this);invoke(method,this,[handler]);}});
    const setter=descriptor(value,'onclick').set;
    invoke(setString,nativeStrings,[setter,invoke(nativeString,method,[])]);
    define(prototype,'onclick',options({...previous,set:setter}));installed.push({prototype,name:'onclick',value:setter,previous,setter:true});
  }
  // A fresh realm's native attachShadow bypasses the wrapper above. Register
  // the receiving root before content insertion or listener registration, so
  // even a non-composed event in the same handler meets isolated capture.
  function watchReceiver(target){
    if(!enabled||!shadowHost)return;
    let localRoot,host;try{localRoot=invoke(root,target,[]);host=invoke(shadowHost,localRoot,[]);}catch{return;}
    if(host)report(localRoot,{kind:'watch_root'});
  }
  for(const [prototype,names] of [[globalThis.Node?.prototype,['appendChild','insertBefore','replaceChild']],
    [globalThis.Element?.prototype,['append','prepend','replaceChildren','insertAdjacentElement','insertAdjacentHTML']],
    [globalThis.DocumentFragment?.prototype,['append','prepend','replaceChildren']]])for(const name of names){
      const method=prototype&&descriptor(prototype,name)?.value;
      if(typeof method==='function')install(prototype,name,function(){watchReceiver(this);return invoke(method,this,arguments);});
    }
  const listen=EventTarget.prototype.addEventListener;
  install(EventTarget.prototype,'addEventListener',function(){
    // Registration can precede insertion into a root made with borrowed natives.
    // Capture must already travel with the detached receiver, before its handler.
    let node=false;try{invoke(root,this,[]);node=true;}catch{}
    if(node)watchCreated(this);
    watchReceiver(this);return invoke(listen,this,arguments);
  });
  for(const prototype of [globalThis.Element?.prototype,globalThis.ShadowRoot?.prototype]){
    const previous=prototype&&descriptor(prototype,'innerHTML');if(!previous?.set)continue;
    const method=previous.set;
    const value=({set innerHTML(html){watchReceiver(this);invoke(method,this,[html]);}});
    const setter=descriptor(value,'innerHTML').set;
    invoke(setString,nativeStrings,[setter,invoke(nativeString,method,[])]);
    define(prototype,'innerHTML',options({...previous,set:setter}));installed.push({prototype,name:'innerHTML',value:setter,previous,setter:true});
  }
  for(const name of ['alert','confirm','prompt']){
    let prototype=globalThis;while(prototype&&!descriptor(prototype,name))prototype=Object.getPrototypeOf(prototype);
    const method=prototype&&descriptor(prototype,name)?.value;if(typeof method!=='function')continue;
    install(prototype,name,function(){
      if(!enabled)return invoke(method,this,arguments);
      let target;try{target=this==null||this===globalThis?ownDocument:windowDocument?invoke(windowDocument,this,[]):this.document;}catch{return invoke(method,this,arguments);}
      if(!target||!connected(target))return invoke(method,this,arguments);
      // DOMString conversion may run page code and open another realm's
      // native dialog. It must finish before this call has a private token.
      for(let index=0;index<arguments.length&&index<(name==='prompt'?2:1);index++){
        if(typeof arguments[index]==='symbol')return invoke(method,this,arguments);
        if(arguments[index]!==undefined)arguments[index]=`${arguments[index]}`;
      }
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
  function cleanup(){closed=true;enabled=false;if(relayKey&&privateRelay)invoke(removeAttribute,privateRelay,[relayKey]);let restored=true;for(let index=0;index<foreignRefs.length;index++){const record=invoke(deref,foreignRefs[index],[]),node=record&&invoke(deref,record.node,[]);if(node)for(const kind of ['click','submit'])try{invoke(removeListener,node,[kind,record.listener,true]);}catch{restored=false;}}foreignRefs.length=0;for(let index=0;index<installed.length;index++){const item=installed[index],current=descriptor(item.prototype,item.name),key=item.setter?'set':'value';if(current&&descriptor(current,key)&&current[key]===item.value){try{define(item.prototype,item.name,item.setter?options({...current,set:item.previous.set}):item.previous);}catch{try{define(item.prototype,item.name,options({[key]:item.previous[key]}));}catch{restored=false;}}}}return restored;}
  if(privateControl)privateControl.addEventListener('aresos-relay-cleanup',event=>{if(cleanup())event.preventDefault();});
  if(privateRelay)return {activate,cleanup,identify,link,relay:privateRelay};
  activate();return cleanup;
})();
