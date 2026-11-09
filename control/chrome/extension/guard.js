// ISOLATED, document_start. Only extension messages can relax these private holds.
(() => {
  'use strict';
  const native = {
    submit: HTMLFormElement.prototype.submit, requestSubmit: HTMLFormElement.prototype.requestSubmit,
    click: HTMLElement.prototype.click, dispatch: EventTarget.prototype.dispatchEvent,
  };
  const phase = Object.getOwnPropertyDescriptor(Event.prototype, 'eventPhase')?.get;
  const eventType = Object.getOwnPropertyDescriptor(Event.prototype, 'type')?.get;
  const held = new Map(), roots = new WeakSet(), consumed = new Set();
  let reader, generation = null, dispatchNonce = null, config, until = 0, inFlight = false, mark = null, owner = null, sequence = 0;
  const currentPhase = event => phase ? phase.call(event) : event.eventPhase;
  const type = event => eventType ? eventType.call(event) : event.type;
  const active = () => generation !== null && (inFlight || performance.now() < until);
  // eventPhase proves only synchronous dispatch, never the following default action/task.
  const ownerDispatch = () => !inFlight && owner && owner.isTrusted && currentPhase(owner) !== 0;
  const control=element=>element.closest('button,input,a,[role=button],[role=link],[role=menuitem],[onclick]') || element;
  function facts(element) { return reader.target(element); }
  function decoded(value) { try{return decodeURIComponent(value);}catch{return value;} }
  function listed(value) {
    const unicode=config.unicodeWords;if(!unicode)return true;
    const folded=Array.from(value,char=>unicode.fold[char]??char).join('');let word='';
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
  const search = form => !config?.conservative && form?.method === 'get' && form.search;
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
    if (!active() || ownerDispatch() || search(reader.form(form,submitter)) || allowance(form,null,submitter)) {
      if (kind === 'native_submit') native.submit.call(form);
      else if (submitter) native.requestSubmit.call(form,submitter);
      else native.requestSubmit.call(form);
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
    if (event.isTrusted && ['pointerdown','mousedown','click','keydown','keyup','input','change'].includes(type(event)) && !inFlight) owner=event;
    if (!active() || ownerDispatch()) return;
    let element=event.composedPath()[0];
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
      if (search(reader.form(element,event.submitter)) || allowance(element,event,event.submitter)) return;
      event.preventDefault();event.stopImmediatePropagation();report('submit_event',element,event.submitter);
    } else if (type(event) === 'click' && asks(element)) {
      // Only the browser's trusted event for this private, approved dispatch consumes the mark.
      if (inFlight && event.isTrusted && mark && !mark.activation && (element === mark.target || mark.implicit===element&&mark.keydown&&element.form===mark.form)) { mark.input=true;mark.activation=true;return; }
      if (event.cancelable) event.preventDefault();
      event.stopImmediatePropagation();report(event.cancelable ? 'activation' : 'activation_unknown',element,null,event.cancelable);
    }
  }
  function onCall(event) {
    // A page may forge this report. It can only request another normally guarded page step.
    // The element comes from native event dispatch, never a page-supplied identity string.
    event.stopImmediatePropagation();
    const element=event.composedPath()[0];
    if (!reader) { event.preventDefault();return; }
    let delivery=false;
    try {
      const detail=event.detail;
      if (detail?.kind === 'native_submit') {delivery=true;submit(element,null,'native_submit');}
      else if (detail?.kind === 'request_submit') {
        // Validation and the native submit event must precede interception.
        delivery=true;
        if(detail.with_submitter===true){if(!(element instanceof HTMLElement)||!(element.form instanceof HTMLFormElement)){event.preventDefault();return;}native.requestSubmit.call(element.form,element);}
        else if(element instanceof HTMLFormElement)native.requestSubmit.call(element);
        else event.preventDefault();
      } else if (detail?.kind === 'click' || detail?.kind === 'dispatch') {
        let original=null;
        if(detail.kind==='dispatch'){
            const name=detail.event_type,flags=detail.event_flags;
            const prevented=flags?.prevented===true;
            if(typeof name!=='string'||!name.length||name.length>128)throw Error('invalid event type');
            const options={};
            for(const key of ['bubbles','cancelable','composed']){const value=flags?.[key];if(typeof value==='boolean')options[key]=value;}
            // Never read keyboard/input payloads for a protected field. A forged
            // descriptor can change only this fresh event, never the original.
            if(!(element instanceof Element)||!facts(element).password){
              const data=detail.event_data;
              for(const key of ['key','code','data','inputType']){const value=data?.[key];if(typeof value==='string'&&value.length<=65536)options[key]=value;}
              for(const key of ['repeat','ctrlKey','shiftKey','altKey','metaKey','isComposing']){const value=data?.[key];if(typeof value==='boolean')options[key]=value;}
              for(const key of ['location','button','buttons','clientX','clientY','screenX','screenY']){const value=data?.[key];if(typeof value==='number'&&Number.isFinite(value))options[key]=value;}
            }
            const Constructor=/^key(?:down|up|press)$/.test(name)?globalThis.KeyboardEvent:/^(?:click|dblclick|mouse\w+|contextmenu)$/.test(name)?globalThis.MouseEvent:/^(?:beforeinput|input)$/.test(name)?globalThis.InputEvent:Event;
            original=new (Constructor||Event)(name,options);
            if(prevented)original.preventDefault();
        }
        const isClick=detail.kind === 'click' || type(original) === 'click';
        // All page-controlled getters have finished before this final check.
        if (element instanceof Element && active() && !ownerDispatch() && isClick && asks(element)) {
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
  function watch(root) {
    if (root===document || roots.has(root)) return;
    roots.add(root);
    root.addEventListener('aresos-page-call-v2',onCall,true);
    for (const kind of ['pointerdown','mousedown','click','keydown','keyup','input','change','submit']) root.addEventListener(kind,event=>capture(event,root),true);
  }
  watch(window);
  // This object exists only in the extension's isolated world. MAIN has no API or capability.
  globalThis[Symbol.for('aresos.chrome.guard.v2')] = {
    reader(value) { reader=value; }, watch,
    arm(value) {
      generation=value.generation;dispatchNonce=value.dispatch_nonce;config={...value.config,words:value.config.words.map(word=>word.toLowerCase())};inFlight=true;owner=null;until=performance.now()+config.holdMs;
      const target=reader.element(value.target),implicit=reader.element(value.implicit);
      mark=value.operation ? {id:value.operation,target,form:reader.element(value.form),implicit,submitter:implicit||(value.primary_submission&&reader.target(target).submit?target:null),keydown:false,expected_key:value.key_input,expected_form:value.approved_form,input:false,primary:!value.primary_submission,consequential:!value.primary_submission,further:false} : null;
    },
    direct(element) { if(inFlight && mark && reader.element(element)===mark.target)mark.input=true; },
    async finish(epoch,nonce) {
      // A private message plus a later browser task over-covers the synchronous input handlers.
      await new Promise(resolve=>setTimeout(resolve,0));
      if (generation===epoch && dispatchNonce===nonce) { until=Math.max(until,performance.now()+config.holdMs);inFlight=false;mark=null; }
    },
    clear() { generation=null;until=0;inFlight=false;mark=null;owner=null;held.clear(); },
    steps() { const result=[...held.values()].filter(step=>!step.reported).map(step=>{step.reported=true;return {id:step.id,kind:step.kind,document:step.document,label:step.label,element:step.element,submitter:step.submitter,cancellable:step.cancellable};});return result; },
    resume(id,operation,element,form) {
      const step=held.get(id);
      if (!step || reader.element(form)!==step.node || reader.element(element)!==(step.button||step.node) || consumed.has(operation) || !['native_submit','submit_event'].includes(step.kind) || !step.node.isConnected || step.button && (!step.button.isConnected || step.button.form!==step.node)) throw Error('stale_reference: form, submitter or operation changed');
      consumed.add(operation);held.delete(id);
      const expected=mark?.id===operation?mark.expected_form:null;
      mark={id:operation,target:step.button,form:step.node,submitter:step.button,expected_form:expected,input:true,primary:step.kind==='native_submit',consequential:false,further:false};
      if (step.kind==='native_submit') native.submit.call(step.node);
      else if (step.button) native.requestSubmit.call(step.node,step.button);
      else native.requestSubmit.call(step.node);
      return {resumed:step.kind};
    },
  };
})();
