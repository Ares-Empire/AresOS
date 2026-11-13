// ISOLATED, document_start. Only extension messages can relax these private holds.
(() => {
  'use strict';
  if(globalThis[Symbol.for('aresos.chrome.guard.v2')])return;
  // DOM wrappers can keep their original realm after native adoption.
  const elementAttribute=Element.prototype.getAttribute;
  const isElement=node=>{try{elementAttribute.call(node,'');return true;}catch{return false;}};
  const html=(node,Constructor,tag=null)=>node instanceof Constructor||isElement(node)&&node.namespaceURI==='http://www.w3.org/1999/xhtml'&&(!tag||node.localName===tag);
  const native = {
    submit: HTMLFormElement.prototype.submit, requestSubmit: HTMLFormElement.prototype.requestSubmit,
    click: HTMLElement.prototype.click, dispatch: EventTarget.prototype.dispatchEvent,
  };
  const getAttribute=Element.prototype.getAttribute,setAttribute=Element.prototype.setAttribute,removeAttribute=Element.prototype.removeAttribute;
  const getAttributeNS=Element.prototype.getAttributeNS,setAttributeNS=Element.prototype.setAttributeNS,removeAttributeNS=Element.prototype.removeAttributeNS;
  const quarantined=new WeakMap();
  const captured=new WeakMap();
  function capturedBefore(event,root){
    const previous=captured.get(event);if(!previous)return false;
    const path=event.composedPath();
    // A native dispatch visits each capture root once. Seeing its first root
    // again, or a different path, is a new dispatch of the same page-owned Event.
    if(previous.path.length===path.length&&previous.path.every((node,index)=>node===path[index])&&!previous.roots.has(root)){
      previous.roots.add(root);return true;
    }
    captured.delete(event);return false;
  }
  function capturedHere(event,root){captured.set(event,{path:event.composedPath(),roots:new Set([root])});}
  function stopDefault(element){
    // A non-cancellable native activation still runs its default after capture.
    // Strip hyperlink/submitter authority synchronously; remaining defaults
    // use only the content-free, session-blocked address.
    // New browsing contexts cannot escape the source tab's network fence.
    if(!config?.defaultBlock)return false;
    if(element.form&&['BUTTON','INPUT'].includes(element.tagName)&&['submit','image','reset'].includes(element.type)){
      if(quarantined.has(element))return true;
      const previous=getAttribute.call(element,'disabled');setAttribute.call(element,'disabled','');
      quarantined.set(element,previous);
      setTimeout(()=>{quarantined.delete(element);if(getAttribute.call(element,'disabled')===''){if(previous===null)removeAttribute.call(element,'disabled');else setAttribute.call(element,'disabled',previous);}},0);
      return true;
    }
    const hyperlink=['A','AREA'].includes(element.tagName)||element.namespaceURI==='http://www.w3.org/2000/svg'&&element.localName==='a';
    const node=element;
    // Stopping handlers alone cannot establish that an unknown default stopped.
    if(!hyperlink&&node.tagName!=='FORM')return false;
    if(quarantined.has(node))return true;
    const names=hyperlink?['href','ping']:['action','target'];
    const previous=names.map(name=>[name,getAttribute.call(node,name)]);
    const xlink='http://www.w3.org/1999/xlink';
    const legacy=hyperlink&&getAttributeNS?getAttributeNS.call(node,xlink,'href'):null;
    quarantined.set(node,previous);
    if(hyperlink){
      // No hyperlink remains for the uncancellable default to follow. In
      // particular it cannot create a new browsing context outside tabIds.
      removeAttribute.call(node,'href');
      if(legacy!==null)removeAttributeNS.call(node,xlink,'href');
      if(getAttribute.call(node,'ping'))setAttribute.call(node,'ping',config.defaultBlock);
    }else{setAttribute.call(node,'action',config.defaultBlock);setAttribute.call(node,'target','_self');}
    const blockedAddress=config.defaultBlock;
    setTimeout(()=>{if(quarantined.get(node)!==previous)return;quarantined.delete(node);for(const [name,value]of previous){
      const held=name==='target'?'_self':name==='href'?null:blockedAddress;
      if(getAttribute.call(node,name)!==held)continue;
      if(value===null)removeAttribute.call(node,name);else setAttribute.call(node,name,value);
    }if(legacy!==null&&getAttributeNS.call(node,xlink,'href')===null)setAttributeNS.call(node,xlink,'xlink:href',legacy);},0);
    return true;
  }
  const phase = Object.getOwnPropertyDescriptor(Event.prototype, 'eventPhase')?.get;
  const eventType = Object.getOwnPropertyDescriptor(Event.prototype, 'type')?.get;
  const formElements=Object.getOwnPropertyDescriptor(HTMLFormElement.prototype,'elements')?.get;
  const ownDocument=document,nativeRoot=Node.prototype?.getRootNode;
  const defaultView=globalThis.Document&&Object.getOwnPropertyDescriptor(Document.prototype,'defaultView')?.get;
  const held = new Map(), roots = new WeakMap(), rootRefs = new Set(), consumed = new Set();
  function* watchedRoots(){for(const ref of rootRefs){const root=ref.deref();if(root)yield [root,roots.get(root)];else rootRefs.delete(ref);}}
  let privacyCheck=null,reader, generation = null, dispatchNonce = null, config, until = 0, inFlight = false, mark = null, owner = null, sequence = 0;
  const clipboardRoutes=new Set();
  function noteClipboard(route){if(generation!==null&&['write','writeText','copy'].includes(route)){clipboardRoutes.add(route);try{reader?.clipboard?.(route,generation);}catch{}}}
  function clipboardObservation(take=false){
    if(!clipboardRoutes.size)return null;
    const result={written:true,message:'The page wrote to the clipboard.',routes:[...clipboardRoutes].sort()};
    if(take)clipboardRoutes.clear();return result;
  }
  let endingDialog=null;
  function nativeDialogReturned(token){
    endingDialog=token;
    // Installed before page scripts. The native modal has returned, but its
    // caller cannot continue until the extension has processed this pause.
    debugger;
    reader?.dialog?.('end',token,generation,dispatchNonce);
    endingDialog=null;
  }
  // Real documents never accept page-forgeable reports, even before private linking.
  let relayNode=null,relayMarker=null,relayControl=null,legacyBridge=typeof globalThis.Document!=='function',requestDepth=0;const relayListeners=[];
  function requestNative(form,submitter){requestDepth++;try{return submitter?native.requestSubmit.call(form,submitter):native.requestSubmit.call(form);}finally{requestDepth--;}}
  const currentPhase = event => phase ? phase.call(event) : event.eventPhase;
  const type = event => eventType ? eventType.call(event) : event.type;
  const peers=new Map(),peerDocuments=new WeakMap();let queryingSources=false,inheritedCapture=null;
  const alive=peer=>{const node=peer.node.deref();if(!node||getAttribute.call(node,peer.key)!==peer.value)return false;if(!defaultView)return true;try{const doc=node.ownerDocument,view=defaultView.call(doc);return !!view&&view.document===doc;}catch{return false;}};
  function peerAPI(peer){
    if(peer.api)return peer.api;
    const node=peer.node.deref();if(!node||!alive(peer))return null;
    // Native wiring happens while Debugger pauses the document. DOM listeners
    // cannot run then; exchange private ISOLATED references on first live use.
    const detail={};native.dispatch.call(node.firstElementChild,new CustomEvent('aresos-relay-guard',{detail}));
    return peer.api=detail.api||null;
  }
  function holdConfig(){
    if(generation===null)return null;
    let combined=inFlight||performance.now()<until?config:null;
    if(inheritedCapture?.config)combined={...inheritedCapture.config,conservative:inheritedCapture.config.conservative||combined?.conservative};
    if(queryingSources)return combined;
    queryingSources=true;
    try{for(const peer of peers.values()){
      if(!alive(peer)){reader?.protectPeers?.();peers.delete(peer.value);continue;}
      const source=peerAPI(peer);
      if(source&&!source.privateCurrent()){reader?.protectPeers?.();peers.delete(peer.value);continue;}
      if(!peer.enabled)continue;
      const candidate=source?source.privateHold():{...config,conservative:true,holdMs:config?.holdMs||500,defaultBlock:config?.defaultBlock||'https://aresos-hold.invalid/'};
      if(candidate)combined={...candidate,conservative:candidate.conservative||combined?.conservative};
    }}finally{queryingSources=false;}
    if(combined)config=combined;return combined;
  }
  const active=()=>!!holdConfig();
  const ownerTasks=new MessageChannel();
  ownerTasks.port1.onmessage=event=>{if(owner?.token===event.data)owner=null;};
  const ownerMutations=globalThis.MutationObserver?new MutationObserver(()=>{if(owner)owner.changed=true;}):null;
  const ownerMutationOptions={subtree:true,attributes:true,childList:true,characterData:true};
  ownerMutations?.observe(document,ownerMutationOptions);
  function nativeDefault(element,form,submitter){
    if(!form)return false;
    if(submitter)return !submitter.matches(':disabled');
    if(!(html(element,HTMLInputElement,'input'))||!['','text','search','url','tel','email','password'].includes(element.type))return false;
    const blocking=['','text','search','url','tel','email','password','date','month','week','time','datetime-local','number'];
    try{const fields=formElements?formElements.call(form):form.elements||[element];let count=0;for(let index=0;index<fields.length;index++)if(html(fields[index],HTMLInputElement,'input')&&blocking.includes(fields[index].type))count++;return count<=1;}catch{return false;}
  }
  function ownerInput(event,element) {
    if(!event.isTrusted||inFlight)return;
    const kind=type(event),key=event.key;
    let form=null,submitter=null,defaultSubmission=false;
    if(kind==='click'&&isElement(element)){const target=control(element);if(target.form&&reader.target(target).submit){form=target.form;submitter=target;defaultSubmission=nativeDefault(target,form,submitter);}}
    if(['keydown','keypress','keyup'].includes(kind)&&key==='Enter'&&isElement(element)){
      form=element.form||null;
      if(form&&reader.target(element).submit)submitter=element;
      else if(form){const implicit=reader.target(element).implicit_submitter;submitter=implicit?reader.element(implicit):null;}
      defaultSubmission=['keydown','keypress'].includes(kind)&&nativeDefault(element,form,submitter);
    }
    const token=++sequence;
    ownerMutations?.takeRecords();
    owner={event,form,submitter,token,defaultSubmission,consumed:false,changed:false};
    ownerTasks.port2.postMessage(token);
  }
  function ownerSubmission(form,submitter,event=null) {
    if(inFlight||!owner||owner.consumed||!owner.event.isTrusted||owner.form!==form||owner.submitter!==(submitter||null))return false;
    if(currentPhase(owner.event)===0&&(requestDepth||!owner.defaultSubmission||owner.event.defaultPrevented||!event?.isTrusted||owner.changed||ownerMutations?.takeRecords().length))return false;
    owner.consumed=true;return true;
  }
  const control=element=>element.closest('button,input,a,area,[role=button],[role=link],[role=menuitem],[onclick]') || element;
  const eventElement=node=>isElement(node)?node:node?.parentElement||(globalThis.ShadowRoot&&node instanceof ShadowRoot?node.host:null);
  function facts(element) { return reader.target(element); }
  function decoded(value) { return value.replace(/(?:%[0-9a-f]{2})+/gi,encoded=>new TextDecoder('utf-8',{ignoreBOM:true}).decode(Uint8Array.from(encoded.match(/%../g),byte=>parseInt(byte.slice(1),16)))); }
  function listed(value) {
    const unicode=config.unicodeWords;if(!unicode)return true;
    const folded=Array.from(value.normalize('NFC'),char=>unicode.fold[char]??char).join('');let word='';
    for(const char of folded){
      const point=char.codePointAt(0);let low=0,high=unicode.ranges.length;
      while(low<high){const middle=(low+high)>>>1;if(unicode.ranges[middle][0]<=point)low=middle+1;else high=middle;}
      if(low>0&&point<=unicode.ranges[low-1][1])word+=char;
      else{if(config.words.includes(word))return true;word='';}
    }
    return config.words.includes(word);
  }
  function asks(element) {
    element=control(element);
    if(config?.conservative)return true;
    const target = facts(element), form = reader.form(element);
    if (!target.editable && explicit(target,form)) return true;
    if (form && target.submit) return !search(form,element);
    if (target.editable) return false;
    return false;
  }
  function explicit(target,form) {
    return listed([target?.name,target?.label,target?.title,target?.role,target?.page_dialog?.text,target?.password ? '' : target?.value,form?.action ? decoded(form.action):''].join(' '));
  }
  function search(form,element=null) {
    if(config?.conservative||form?.method!=='get'||!form.search)return false;
    // A search container never exempts an explicit Pay/Delete/Send control.
    if(explicit(element?facts(element):null,form)||(form.fields||[]).some(field=>['submit','image'].includes(field.type)&&explicit(field,null)))return false;
    try{const url=new URL(form.action),host=url.hostname.replace(/\.+$/,'');return ['http:','https:'].includes(url.protocol)&&!url.username&&!url.password&&!(config.blockedHosts||config.fixedHosts||[]).some(blocked=>host===blocked||host.endsWith('.'+blocked));}catch{return false;}
  }
  function report(kind, element, submitter = null, cancellable = true) {
    const id = 'h' + (++sequence);
    let label='';if(kind.startsWith('activation'))try{label=reader.target(element).name;}catch{label='an uninspectable control';}
    const step = {id,kind,document:reader.document,label,element:reader.id(element),submitter:submitter ? reader.id(submitter) : null,cancellable};
    held.set(id,{...step,node:element,button:submitter});
    // A default navigation can destroy this document before the later poll.
    // This private observation grants no allowance and never resumes anything.
    try{reader.report?.(step,generation);}catch{}
  }
  function allowance(form,event=null,submitter=null) {
    if (!mark || !mark.input || mark.form !== form) return false;
    if(mark.implicit&&!mark.primary&&(!mark.keydown||!event||submitter!==mark.implicit))return false;
    if(event&&submitter&&submitter!==mark.submitter)return false;
    if(mark.expected_form){const actual=reader.form(form,submitter);if(['action','method','encoding','target'].some(key=>actual?.[key]!==mark.expected_form[key]))return false;}
    if (!mark.primary) { mark.primary=true;mark.event=event;return true; }
    if (!mark.further && (mark.consequential || mark.event && currentPhase(mark.event)!==0)) {
      mark.further=true;
      // Replace the enclosing event's default before the extra call can send.
      if(mark.event)mark.event.preventDefault();
      return true;
    }
    return false;
  }
  function submit(form, submitter, kind) {
    if (!(html(form,HTMLFormElement,'form'))) return;
    if (!active() || ownerSubmission(form,submitter) || search(reader.form(form,submitter),submitter||form) || allowance(form,null,submitter)) {
      if (kind === 'native_submit') native.submit.call(form);
      else requestNative(form,submitter);
    } else report(kind,form,submitter);
  }
  function capture(event,root) {
    try{return captureInput(event,root);}catch{
      if(!active())return;
      if(event.cancelable)event.preventDefault();event.stopImmediatePropagation();
      const element=event.composedPath()[0];
      if(isElement(element))report(event.cancelable?'activation':'activation_unknown',element,null,event.cancelable);
    }
  }
  function captureInput(event,root) {
    let element=eventElement(event.composedPath()[0]);
    if(element&&nativeRoot&&nativeRoot.call(element,{composed:true})!==ownDocument){
      const peer=peerDocuments.get(element.ownerDocument);
      if(peer&&alive(peer)){const other=peerAPI(peer),hold=active()?{config}:null;if(other)other.capture(event,root,hold);else if(hold){if(event.cancelable)event.preventDefault();event.stopImmediatePropagation();report('activation_unknown',element,null,event.cancelable);}}
      return;
    }
    if (!active()) return;
    if (!(isElement(element))) return;
    const nodeRoot=element.getRootNode();
    if(root===window){
      // Native-created roots may have bypassed the MAIN attachShadow wrapper.
      // Install capture while this composed event is still above the root.
      if(nodeRoot!==document){watch(nodeRoot);return;}
      const shadow=html(element,HTMLElement)&&globalThis.chrome?.dom?.openOrClosedShadowRoot(element);
      if(shadow)watch(shadow);
    }else if(nodeRoot!==root&&root!==element)return;
    if(capturedBefore(event,root))return;
    if(type(event)==='invalid'&&owner)owner.changed=true;
    if(['pointerdown','pointerup','pointermove','mousedown','mouseup','click','keydown','keypress','keyup'].includes(type(event)))ownerInput(event,element);
    if(type(event)==='click')element=control(element);
    if (inFlight && event.isTrusted && mark && element === mark.target) {
      if(['keydown','input','change'].includes(type(event)))mark.input=true;
      const expected=mark.expected_key;
      if(type(event)==='keydown'&&expected&&event.key===expected.key&&!!event.ctrlKey===!!(expected.modifiers&2)&&!!event.metaKey===!!(expected.modifiers&4)&&!!event.altKey===!!(expected.modifiers&1)&&!!event.shiftKey===!!(expected.modifiers&8))mark.keydown=true;
    }
    if (type(event) === 'submit') {
      capturedHere(event,root);
      if (ownerSubmission(element,event.submitter,event) || search(reader.form(element,event.submitter),event.submitter||element) || allowance(element,event,event.submitter)) return;
      event.preventDefault();event.stopImmediatePropagation();report('submit_event',element,event.submitter);
    } else if (type(event) === 'click' && asks(element)) {
      capturedHere(event,root);
      if(!inFlight&&event.isTrusted&&owner?.event===event&&!owner.consumed)return;
      // Only the browser's trusted event for this private, approved dispatch consumes the mark.
      if (inFlight && event.isTrusted && mark && !mark.activation && (element === mark.target || mark.implicit===element&&mark.keydown&&element.form===mark.form)) { mark.input=true;mark.activation=true;return; }
      if (event.cancelable) event.preventDefault();
      const stopped=event.cancelable||stopDefault(element);
      event.stopImmediatePropagation();report(stopped ? 'activation' : 'activation_unknown',element,null,event.cancelable);
    }
  }
  function foreignGuard(node){
    let doc;try{doc=nativeRoot?nativeRoot.call(node,{composed:true}):node.getRootNode({composed:true});}catch{return null;}
    if(doc===ownDocument)return null;
    let view;try{view=defaultView?defaultView.call(doc):doc.defaultView;}catch{return {unknown:true};}
    if(!view)return null;
    try{return view[Symbol.for('aresos.chrome.guard.v2')]||(view.top&&view.top===window.top?{unknown:true}:{outside:true});}catch{return {unknown:true};}
  }
  function outsideCall(event,stage){const {target,detail}=stage;if(detail.kind==='native_submit')native.submit.call(target);else if(detail.kind==='request_submit')requestNative(detail.with_submitter?target.form:target,detail.with_submitter?target:null);else event.preventDefault();}
  function onCall(event,request=null) {
    // A page may forge this report. It can only request another normally guarded page step.
    // The element comes from native event dispatch, never a page-supplied identity string.
    event.stopImmediatePropagation();
    const element=request?request.target:event.composedPath()[0];
    const other=foreignGuard(element);
    if(other){if(other.outside)return outsideCall(event,request||{target:element,detail:event.detail});if(other.route)return other.route(event,request||{target:element,detail:event.detail},active()?{config}:null);event.preventDefault();return;}
    if (!reader) { event.preventDefault();return; }
    let delivery=false;
    try {
      const detail=request?request.detail:event.detail;
      if(detail?.kind==='clipboard_write'){if(element===ownDocument)noteClipboard(detail.route);return;}
      if(detail?.kind==='dialog_begin'){reader.dialog?.('begin',detail.token,generation,null,detail.dialog_kind);event.preventDefault();return;}
      if(detail?.kind==='dialog_end'){nativeDialogReturned(detail.token);event.preventDefault();return;}
      if(isElement(element))watch(element.getRootNode());
      if (detail?.kind === 'native_submit') {delivery=true;submit(element,null,'native_submit');}
      else if (detail?.kind === 'request_submit') {
        // Validation and the native submit event must precede interception.
        delivery=true;
        if(detail.with_submitter===true){if(!(html(element,HTMLElement))||!(html(element.form,HTMLFormElement,'form'))){event.preventDefault();return;}requestNative(element.form,element);}
        else if(html(element,HTMLFormElement,'form'))requestNative(element);
        else event.preventDefault();
      } else if (detail?.kind === 'click' || detail?.kind === 'dispatch') {
        let original=null;
        if(detail.kind==='dispatch'){
          if(request?.original){original=request.original;if(type(original)!==detail.event_type)throw Error('event type changed');}
          else{
            const name=detail.event_type,flags=detail.event_flags;
            const prevented=flags?.prevented===true;
            if(typeof name!=='string'||!name.length||name.length>128)throw Error('invalid event type');
            const options={};
            for(const key of ['bubbles','cancelable','composed']){const value=flags?.[key];if(typeof value==='boolean')options[key]=value;}
            // Never read keyboard/input payloads for a protected field. A forged
            // descriptor can change only this fresh event, never the original.
            let protectedPayload=isElement(element)&&facts(element).password;
            const allowedPayload=()=>!(protectedPayload ||= isElement(element)&&facts(element).password);
            if(allowedPayload()){
              const data=detail.event_data??detail;
              for(const key of ['key','code','data','inputType']){if(!allowedPayload())break;const value=data?.[key];if(typeof value==='string'&&value.length<=65536)options[key]=value;}
              for(const key of ['repeat','ctrlKey','shiftKey','altKey','metaKey','isComposing']){if(!allowedPayload())break;const value=data?.[key];if(typeof value==='boolean')options[key]=value;}
              for(const key of ['location','button','buttons','clientX','clientY','screenX','screenY']){if(!allowedPayload())break;const value=data?.[key];if(typeof value==='number'&&Number.isFinite(value))options[key]=value;}
            }
            const Constructor=/^key(?:down|up|press)$/.test(name)?globalThis.KeyboardEvent:/^(?:click|dblclick|mouse\w+|contextmenu)$/.test(name)?globalThis.MouseEvent:/^(?:beforeinput|input)$/.test(name)?globalThis.InputEvent:Event;
            original=new (Constructor||Event)(name,options);
            if(prevented)original.preventDefault();
          }
        }
        const isClick=detail.kind === 'click' || type(original) === 'click';
        // All page-controlled getters have finished before this final check.
        if (isElement(element) && active() && isClick && asks(element)) {
          report('activation',control(element),null,original?.cancelable ?? true);event.preventDefault();return;
        }
        delivery=true;
        if (original) { if (!native.dispatch.call(element,original)) event.preventDefault(); }
        else native.click.call(element);
      } else event.preventDefault();
    } catch {
      event.preventDefault();
      if(active()&&isElement(element))report(delivery?'activation_unknown':'activation',element,null,!delivery);
      console.warn(delivery?'AresOS page API failed during native delivery; outcome uncertain.':'AresOS page descriptor was held before native delivery.');
    } // Invalid/forged reports can only add a hold.
  }
  function watch(root,hold=null) {
    if(hold){config=hold.config;until=Math.max(until,performance.now()+config.holdMs);owner=null;mark=null;}
    if (!root?.addEventListener || root===document || roots.has(root)) return;
    if(root instanceof Node)ownerMutations?.observe(root,ownerMutationOptions);
    const listeners=[];
    const listen=(kind,listener,capture)=>{root.addEventListener(kind,listener,capture);listeners.push([kind,listener,capture]);};
    roots.set(root,listeners);rootRefs.add(new WeakRef(root));
    if(legacyBridge){listen('aresos-page-call-v2',event=>{
      const element=event.composedPath()[0],shadow=isElement(element)?globalThis.chrome?.dom?.openOrClosedShadowRoot(element):null;
      // A closed root hides its inner target here. Install its native listener
      // before this report reaches it; a host's own report uses the bubble fallback.
      if(shadow){watch(shadow);return;}
      onCall(event);
    },true);
    listen('aresos-page-call-v2',onCall,false);}
    listen('copy',event=>{try{if(event.isTrusted&&nativeRoot.call(event.composedPath()[0],{composed:true})===ownDocument)noteClipboard('copy');}catch{}},true);
    for (const kind of ['pointerdown','pointerup','pointermove','mousedown','mouseup','click','keydown','keypress','keyup','input','change','invalid','submit']) listen(kind,event=>capture(event,root),true);
  }
  watch(window);
  // This object exists only in the extension's isolated world. MAIN has no API or capability.
  const api=globalThis[Symbol.for('aresos.chrome.guard.v2')] = {
    get ready(){return !!reader;},
    clipboard:clipboardObservation,
    control(epoch){if(generation!==epoch)clipboardRoutes.clear();generation=epoch;},
    route(event,stage,hold){if(hold){config=hold.config;until=Math.max(until,performance.now()+config.holdMs);owner=null;mark=null;}if(stage.detail.kind==='click'||stage.detail.kind==='dispatch'){const node=eventElement(stage.target),name=stage.detail.kind==='click'?'click':stage.detail.event_type;if(node)watch(node.getRootNode());if(active()&&node&&(name==='click'&&asks(node)||name==='submit'&&!search(reader.form(node),node))){report('activation',control(node));return;}event.preventDefault();}else onCall(event,stage);},
    identity(){return reader?.document;},
    dialogBoundary(){return {document:reader?.document,token:endingDialog};},
    relay(node){
      if(!reader||!(html(node,HTMLElement))||node.ownerDocument!==document||node.isConnected||node.parentNode||!node.firstElementChild)throw Error('invalid private relay');
      const carrier=node.firstElementChild,stack=[];
      const listen=(kind,listener)=>{carrier.addEventListener(kind,listener);relayListeners.push([kind,listener]);};
      const ranges=InputEvent.prototype.getTargetRanges;
      relayNode=node;
      listen('aresos-relay-guard',event=>{event.detail.api=api;});
      legacyBridge=false;relayControl=carrier;
      for(const [root,listeners]of watchedRoots())for(const [kind,listener,capture]of listeners)if(kind==='aresos-page-call-v2')root.removeEventListener(kind,listener,capture);
      const drop=request=>{if(stack.at(-1)?.detail.request===request)stack.pop();};
      listen('aresos-relay-meta',event=>{
        const detail=event.detail;
        if(stack.length>=32||!['native_submit','request_submit','click','dispatch','watch_root','watch_node','clipboard_write','dialog_begin','dialog_end'].includes(detail?.kind))return;
        if(!Number.isSafeInteger(detail.request))return;
        const stage={detail};stack.push(stage);
      });
      // The container getter's owning interface differs across Chrome versions.
      // Read the real range in our isolated world, returned by the saved native
      // method on a private event, without assuming that prototype layout.
      listen('aresos-relay-target',event=>{const stage=stack.at(-1);if(stage&&''+stage.detail.request===event.data){
        // Transfer the outer host through the native event, then resolve its
        // exact shadow endpoint entirely in this isolated world. No range
        // endpoint crosses a shadow boundary and no MAIN DOM object is trusted.
        let target=ranges.call(event)[0].startContainer;
        for(const part of stage.detail.target_path?.split('.')||[]){
          if(!part)continue;
          target=part==='s'?chrome.dom.openOrClosedShadowRoot(target):/^\d+$/.test(part)?target.childNodes[Number(part)]:null;
          if(!target)throw Error('native shadow path changed');
        }
        stage.target=target;
      }});
      listen('aresos-relay-deliver',event=>{
        const stage=stack.at(-1);if(!stage?.target||stage.detail.request!==event.detail)return;
        // Pop before entering page handlers; nested requests get their own record.
        drop(stage.detail.request);
        if(stage.detail.kind==='clipboard_write'){if(stage.target===ownDocument)noteClipboard(stage.detail.route);return;}
        const source=peers.get(stage.detail.source_id);if(source)source.enabled=true;
        if(stage.detail.kind==='watch_node'){const other=foreignGuard(stage.target.ownerDocument||stage.target);if(other?.watch)other.watch(stage.target,active()?{config}:null);else if(!other&&stage.target.ownerDocument===ownDocument)watch(stage.target);event.preventDefault();return;}
        if(stage.detail.kind==='watch_root'){const other=foreignGuard(stage.target.ownerDocument||stage.target);if(other?.watch)other.watch(stage.target,active()?{config}:null);else if(!other)watch(stage.target);event.preventDefault();return;}
        const other=foreignGuard(stage.target);if(other){if(other.outside)outsideCall(event,stage);else if(other.route)other.route(event,stage,active()?{config}:null);return;}
        const element=eventElement(stage.target);
        if(['click','dispatch'].includes(stage.detail.kind)){
          const name=stage.detail.kind==='click'?'click':stage.detail.event_type;
          if(typeof name!=='string')return;
          if(element)watch(element.getRootNode());
          if(active()&&element&&(name==='click'&&asks(element)||name==='submit'&&!search(reader.form(element),element))){report('activation',control(element));return;}
          // This decision never leaves the private, detached control node. No
          // original Event is transferred, so page code cannot discover the relay.
          event.preventDefault();return;
        }
        onCall(event,stage);
      });
      listen('aresos-relay-drop',event=>drop(event.detail));
      return reader.document;
    },
    source(node,key,value){
      if(getAttribute.call(node,key)!==value||!node.firstElementChild)return false;
      const peer={node:new WeakRef(node),key,value,api:null,enabled:false};
      peers.set(value,peer);peerDocuments.set(node.ownerDocument,peer);return true;
    },
    privatePassword(node){return privacyCheck?.(node)===true;},
    protectedPeer(node){return [...peers.values()].some(peer=>peerAPI(peer)?.privatePassword(node));},
    privateCurrent(){if(!defaultView)return true;const view=defaultView.call(ownDocument);return !!view&&view.document===ownDocument;},
    privateHold(){return this.privateCurrent()?holdConfig():null;},
    capture(event,root,hold){const previous=inheritedCapture;inheritedCapture=hold;try{return capture(event,root);}finally{inheritedCapture=previous;}},
    privateRelay(key,value){const node=document.createElement('div');node.appendChild(document.createElement('span'));setAttribute.call(node,key,value);this.relay(node);relayMarker=key;return node;},
    reader(value) { reader=value;privacyCheck=value.protected; }, watch,
    arm(value) {
      generation=value.generation;dispatchNonce=value.dispatch_nonce;config={...value.config,words:value.config.words.map(word=>word.toLowerCase())};inFlight=true;owner=null;until=performance.now()+config.holdMs;
      const target=reader.element(value.target),implicit=reader.element(value.implicit);
      mark=value.operation ? {id:value.operation,target,form:reader.element(value.form),implicit,submitter:implicit||(value.primary_submission&&reader.target(target).submit?target:null),keydown:false,expected_key:value.key_input,expected_form:value.approved_form,input:false,primary:!value.primary_submission,consequential:!value.primary_submission,further:false} : null;
    },
    inherit(value){this.arm(value);inFlight=value.in_flight===true;mark=null;},
    direct(element) { if(inFlight && mark && reader.element(element)===mark.target)mark.input=true; },
    async finish(epoch,nonce) {
      // A private message plus a later browser task over-covers the synchronous input handlers.
      await new Promise(resolve=>setTimeout(resolve,0));
      if (generation===epoch && dispatchNonce===nonce) { until=Math.max(until,performance.now()+config.holdMs);inFlight=false;mark=null; }
    },
    clear() { peers.clear();clipboardRoutes.clear();generation=null;until=0;inFlight=false;mark=null;owner=null;held.clear(); },
    dispose() { let restored=true;if(relayNode&&relayMarker)removeAttribute.call(relayNode,relayMarker);relayNode=null;relayMarker=null;if(relayControl){restored=!native.dispatch.call(relayControl,new Event('aresos-relay-cleanup',{cancelable:true}));for(const [kind,listener]of relayListeners)relayControl.removeEventListener(kind,listener);}relayControl=null;relayListeners.length=0;reader?.protectPeers?.();this.clear();ownerMutations?.disconnect();for(const [root,listeners] of watchedRoots())for(const [kind,listener,capture]of listeners)root.removeEventListener(kind,listener,capture);rootRefs.clear();ownerTasks.port1.close();ownerTasks.port2.close();reader?.dispose?.();reader=null;delete globalThis[Symbol.for('aresos.chrome.guard.v2')];return restored; },
    steps() { const result=[...held.values()].filter(step=>!step.reported).map(step=>{step.reported=true;return {id:step.id,kind:step.kind,document:step.document,label:step.label,element:step.element,submitter:step.submitter,cancellable:step.cancellable};});return result; },
    resume(id,operation,element,form) {
      const step=held.get(id);
      if (!step || reader.element(form)!==step.node || reader.element(element)!==(step.button||step.node) || consumed.has(operation) || !['native_submit','submit_event'].includes(step.kind) || !step.node.isConnected || step.button && (!step.button.isConnected || step.button.form!==step.node)) throw Error('stale_reference: form, submitter or operation changed');
      consumed.add(operation);held.delete(id);
      const expected=mark?.id===operation?mark.expected_form:null;
      mark={id:operation,target:step.button,form:step.node,submitter:step.button,expected_form:expected,input:true,primary:step.kind==='native_submit',consequential:false,further:false};
      if (step.kind==='native_submit') native.submit.call(step.node);
      else requestNative(step.node,step.button);
      return {resumed:step.kind};
    },
  };
})();
