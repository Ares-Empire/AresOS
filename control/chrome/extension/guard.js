// ISOLATED, document_start. Only extension messages can relax these private holds.
(() => {
  'use strict';
  if(globalThis[Symbol.for('aresos.chrome.guard.v2')])return;
  const native = {
    submit: HTMLFormElement.prototype.submit, requestSubmit: HTMLFormElement.prototype.requestSubmit,
    click: HTMLElement.prototype.click, dispatch: EventTarget.prototype.dispatchEvent,
  };
  const phase = Object.getOwnPropertyDescriptor(Event.prototype, 'eventPhase')?.get;
  const eventType = Object.getOwnPropertyDescriptor(Event.prototype, 'type')?.get;
  const formElements=Object.getOwnPropertyDescriptor(HTMLFormElement.prototype,'elements')?.get;
  const ownDocument=document,nativeRoot=Node.prototype?.getRootNode;
  const defaultView=globalThis.Document&&Object.getOwnPropertyDescriptor(Document.prototype,'defaultView')?.get;
  const held = new Map(), roots = new Map(), consumed = new Set();
  let reader, generation = null, dispatchNonce = null, config, until = 0, inFlight = false, mark = null, owner = null, sequence = 0;
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
  let relayControl=null,legacyBridge=typeof globalThis.Document!=='function',requestDepth=0;const relayListeners=[];
  function requestNative(form,submitter){requestDepth++;try{return submitter?native.requestSubmit.call(form,submitter):native.requestSubmit.call(form);}finally{requestDepth--;}}
  const currentPhase = event => phase ? phase.call(event) : event.eventPhase;
  const type = event => eventType ? eventType.call(event) : event.type;
  const active = () => generation !== null && (inFlight || performance.now() < until);
  const ownerTasks=new MessageChannel();
  ownerTasks.port1.onmessage=event=>{if(owner?.token===event.data)owner=null;};
  const ownerMutations=globalThis.MutationObserver?new MutationObserver(()=>{if(owner)owner.changed=true;}):null;
  const ownerMutationOptions={subtree:true,attributes:true,childList:true,characterData:true};
  ownerMutations?.observe(document,ownerMutationOptions);
  function nativeDefault(element,form,submitter){
    if(!form)return false;
    if(submitter)return !submitter.matches(':disabled');
    if(!(element instanceof HTMLInputElement)||!['','text','search','url','tel','email','password'].includes(element.type))return false;
    const blocking=['','text','search','url','tel','email','password','date','month','week','time','datetime-local','number'];
    try{const fields=formElements?formElements.call(form):form.elements||[element];let count=0;for(let index=0;index<fields.length;index++)if(fields[index] instanceof HTMLInputElement&&blocking.includes(fields[index].type))count++;return count<=1;}catch{return false;}
  }
  function ownerInput(event,element) {
    if(!event.isTrusted||inFlight)return;
    const kind=type(event),key=event.key;
    let form=null,submitter=null,defaultSubmission=false;
    if(kind==='click'&&element instanceof Element){const target=control(element);if(target.form&&reader.target(target).submit){form=target.form;submitter=target;defaultSubmission=nativeDefault(target,form,submitter);}}
    if(['keydown','keypress','keyup'].includes(kind)&&key==='Enter'&&element instanceof Element){
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
  const control=element=>element.closest('button,input,a,[role=button],[role=link],[role=menuitem],[onclick]') || element;
  const eventElement=node=>node instanceof Element?node:node?.parentElement||(globalThis.ShadowRoot&&node instanceof ShadowRoot?node.host:null);
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
    if (form && target.submit) return !search(form);
    if (target.editable) return false;
    return listed([target.name,target.label,target.title,target.role,target.page_dialog?.text,target.password ? '' : target.value,form?.action ? decoded(form.action):'']
      .join(' '));
  }
  function search(form) {
    if(config?.conservative||form?.method!=='get'||!form.search)return false;
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
    if (!(form instanceof HTMLFormElement)) return;
    if (!active() || ownerSubmission(form,submitter) || search(reader.form(form,submitter)) || allowance(form,null,submitter)) {
      if (kind === 'native_submit') native.submit.call(form);
      else requestNative(form,submitter);
    } else report(kind,form,submitter);
  }
  function capture(event,root) {
    try{return captureInput(event,root);}catch{
      if(!active())return;
      if(event.cancelable)event.preventDefault();event.stopImmediatePropagation();
      const element=event.composedPath()[0];
      if(element instanceof Element)report(event.cancelable?'activation':'activation_unknown',element,null,event.cancelable);
    }
  }
  function captureInput(event,root) {
    let element=eventElement(event.composedPath()[0]);
    if(element&&nativeRoot&&nativeRoot.call(element,{composed:true})!==ownDocument)return;
    if(type(event)==='invalid'&&owner)owner.changed=true;
    if(['pointerdown','pointerup','pointermove','mousedown','mouseup','click','keydown','keypress','keyup'].includes(type(event)))ownerInput(event,element);
    if (!active()) return;
    if (!(element instanceof Element)) return;
    const nodeRoot=element.getRootNode();
    if(root===window ? nodeRoot!==document || globalThis.chrome?.dom?.openOrClosedShadowRoot(element) : nodeRoot!==root)return;
    if(type(event)==='click')element=control(element);
    if (inFlight && event.isTrusted && mark && element === mark.target) {
      if(['keydown','input','change'].includes(type(event)))mark.input=true;
      const expected=mark.expected_key;
      if(type(event)==='keydown'&&expected&&event.key===expected.key&&!!event.ctrlKey===!!(expected.modifiers&2)&&!!event.metaKey===!!(expected.modifiers&4)&&!!event.altKey===!!(expected.modifiers&1)&&!!event.shiftKey===!!(expected.modifiers&8))mark.keydown=true;
    }
    if (type(event) === 'submit') {
      if (ownerSubmission(element,event.submitter,event) || search(reader.form(element,event.submitter)) || allowance(element,event,event.submitter)) return;
      event.preventDefault();event.stopImmediatePropagation();report('submit_event',element,event.submitter);
    } else if (type(event) === 'click' && asks(element)) {
      if(!inFlight&&event.isTrusted)return;
      // Only the browser's trusted event for this private, approved dispatch consumes the mark.
      if (inFlight && event.isTrusted && mark && !mark.activation && (element === mark.target || mark.implicit===element&&mark.keydown&&element.form===mark.form)) { mark.input=true;mark.activation=true;return; }
      if (event.cancelable) event.preventDefault();
      event.stopImmediatePropagation();report(event.cancelable ? 'activation' : 'activation_unknown',element,null,event.cancelable);
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
      if(detail?.kind==='dialog_begin'){reader.dialog?.('begin',detail.token,generation,null,detail.dialog_kind);event.preventDefault();return;}
      if(detail?.kind==='dialog_end'){nativeDialogReturned(detail.token);event.preventDefault();return;}
      if(element instanceof Element)watch(element.getRootNode());
      if (detail?.kind === 'native_submit') {delivery=true;submit(element,null,'native_submit');}
      else if (detail?.kind === 'request_submit') {
        // Validation and the native submit event must precede interception.
        delivery=true;
        if(detail.with_submitter===true){if(!(element instanceof HTMLElement)||!(element.form instanceof HTMLFormElement)){event.preventDefault();return;}requestNative(element.form,element);}
        else if(element instanceof HTMLFormElement)requestNative(element);
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
            let protectedPayload=element instanceof Element&&facts(element).password;
            const allowedPayload=()=>!(protectedPayload ||= element instanceof Element&&facts(element).password);
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
        if (element instanceof Element && active() && isClick && asks(element)) {
          report('activation',control(element),null,original?.cancelable ?? true);event.preventDefault();return;
        }
        delivery=true;
        if (original) { if (!native.dispatch.call(element,original)) event.preventDefault(); }
        else native.click.call(element);
      } else event.preventDefault();
    } catch {
      event.preventDefault();
      if(active()&&element instanceof Element)report(delivery?'activation_unknown':'activation',element,null,!delivery);
      console.warn(delivery?'AresOS page API failed during native delivery; outcome uncertain.':'AresOS page descriptor was held before native delivery.');
    } // Invalid/forged reports can only add a hold.
  }
  function watch(root,hold=null) {
    if(hold){config=hold.config;until=Math.max(until,performance.now()+config.holdMs);owner=null;mark=null;}
    if (root===document || roots.has(root)) return;
    if(root instanceof Node)ownerMutations?.observe(root,ownerMutationOptions);
    const listeners=[];
    const listen=(kind,listener,capture)=>{root.addEventListener(kind,listener,capture);listeners.push([kind,listener,capture]);};
    roots.set(root,listeners);
    if(legacyBridge){listen('aresos-page-call-v2',event=>{
      const element=event.composedPath()[0],shadow=element instanceof Element?globalThis.chrome?.dom?.openOrClosedShadowRoot(element):null;
      // A closed root hides its inner target here. Install its native listener
      // before this report reaches it; a host's own report uses the bubble fallback.
      if(shadow){watch(shadow);return;}
      onCall(event);
    },true);
    listen('aresos-page-call-v2',onCall,false);}
    for (const kind of ['pointerdown','pointerup','pointermove','mousedown','mouseup','click','keydown','keypress','keyup','input','change','invalid','submit']) listen(kind,event=>capture(event,root),true);
  }
  watch(window);
  // This object exists only in the extension's isolated world. MAIN has no API or capability.
  globalThis[Symbol.for('aresos.chrome.guard.v2')] = {
    get ready(){return !!reader;},
    control(epoch){generation=epoch;},
    route(event,stage,hold){if(hold){config=hold.config;until=Math.max(until,performance.now()+config.holdMs);owner=null;mark=null;}if(stage.detail.kind==='click'||stage.detail.kind==='dispatch'){const node=eventElement(stage.target),name=stage.detail.kind==='click'?'click':stage.detail.event_type;if(node)watch(node.getRootNode());if(active()&&node&&(name==='click'&&asks(node)||name==='submit'&&!search(reader.form(node)))){report('activation',control(node));return;}event.preventDefault();}else onCall(event,stage);},
    identity(){return reader?.document;},
    dialogBoundary(){return {document:reader?.document,token:endingDialog};},
    relay(node){
      if(!reader||!(node instanceof HTMLElement)||node.ownerDocument!==document||node.isConnected||node.parentNode||!node.firstElementChild)throw Error('invalid private relay');
      const carrier=node.firstElementChild,stack=[];
      const listen=(kind,listener)=>{carrier.addEventListener(kind,listener);relayListeners.push([kind,listener]);};
      const ranges=InputEvent.prototype.getTargetRanges;
      legacyBridge=false;relayControl=carrier;
      for(const [root,listeners]of roots)for(const [kind,listener,capture]of listeners)if(kind==='aresos-page-call-v2')root.removeEventListener(kind,listener,capture);
      const drop=request=>{if(stack.at(-1)?.detail.request===request)stack.pop();};
      listen('aresos-relay-meta',event=>{
        const detail=event.detail;
        if(stack.length>=32||!['native_submit','request_submit','click','dispatch','watch_root','dialog_begin','dialog_end'].includes(detail?.kind))return;
        if(!Number.isSafeInteger(detail.request))return;
        const stage={detail};stack.push(stage);
      });
      // The container getter's owning interface differs across Chrome versions.
      // Read the real range in our isolated world, returned by the saved native
      // method on a private event, without assuming that prototype layout.
      listen('aresos-relay-target',event=>{const stage=stack.at(-1);if(stage&&''+stage.detail.request===event.data)stage.target=ranges.call(event)[0].startContainer;});
      listen('aresos-relay-deliver',event=>{
        const stage=stack.at(-1);if(!stage?.target||stage.detail.request!==event.detail)return;
        // Pop before entering page handlers; nested requests get their own record.
        drop(stage.detail.request);
        if(stage.detail.kind==='watch_root'){const other=foreignGuard(stage.target.ownerDocument||stage.target);if(other?.watch)other.watch(stage.target,active()?{config}:null);else if(!other)watch(stage.target);event.preventDefault();return;}
        const other=foreignGuard(stage.target);if(other){if(other.outside)outsideCall(event,stage);else if(other.route)other.route(event,stage,active()?{config}:null);return;}
        const element=eventElement(stage.target);
        if(['click','dispatch'].includes(stage.detail.kind)){
          const name=stage.detail.kind==='click'?'click':stage.detail.event_type;
          if(typeof name!=='string')return;
          if(element)watch(element.getRootNode());
          if(active()&&element&&(name==='click'&&asks(element)||name==='submit'&&!search(reader.form(element)))){report('activation',control(element));return;}
          // This decision never leaves the private, detached control node. No
          // original Event is transferred, so page code cannot discover the relay.
          event.preventDefault();return;
        }
        onCall(event,stage);
      });
      listen('aresos-relay-drop',event=>drop(event.detail));
      return reader.document;
    },
    reader(value) { reader=value; }, watch,
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
    clear() { generation=null;until=0;inFlight=false;mark=null;owner=null;held.clear(); },
    dispose() { let restored=true;if(relayControl){restored=!native.dispatch.call(relayControl,new Event('aresos-relay-cleanup',{cancelable:true}));for(const [kind,listener]of relayListeners)relayControl.removeEventListener(kind,listener);}relayControl=null;relayListeners.length=0;this.clear();ownerMutations?.disconnect();for(const [root,listeners] of roots)for(const [kind,listener,capture]of listeners)root.removeEventListener(kind,listener,capture);roots.clear();ownerTasks.port1.close();ownerTasks.port2.close();reader?.dispose?.();reader=null;delete globalThis[Symbol.for('aresos.chrome.guard.v2')];return restored; },
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
