// ISOLATED, document_start. Only extension messages can relax these private holds.
(() => {
  const native = {
    submit: HTMLFormElement.prototype.submit, requestSubmit: HTMLFormElement.prototype.requestSubmit,
    click: HTMLElement.prototype.click, dispatch: EventTarget.prototype.dispatchEvent,
  };
  const phase = Object.getOwnPropertyDescriptor(Event.prototype, 'eventPhase')?.get;
  const eventType = Object.getOwnPropertyDescriptor(Event.prototype, 'type')?.get;
  const held = new Map(), roots = new WeakSet(), consumed = new Set();
  let reader, generation = null, config, until = 0, inFlight = false, mark = null, owner = null, sequence = 0;
  const currentPhase = event => phase ? phase.call(event) : event.eventPhase;
  const type = event => eventType ? eventType.call(event) : event.type;
  const active = () => generation !== null && (inFlight || performance.now() < until);
  // eventPhase proves only synchronous dispatch, never the following default action/task.
  const ownerDispatch = () => !inFlight && owner && currentPhase(owner) !== 0;
  function facts(element) { return reader.target(element); }
  function asks(element) {
    const target = facts(element), form = reader.form(element);
    if (form && target.submit && !search(form)) return true;
    if (target.editable) return false;
    return [target.name,target.label,target.title,target.role,target.password ? '' : target.value,form?.action]
      .join(' ').toLocaleLowerCase().match(/[\p{L}\p{N}_]+/gu)?.some(word => config.words.includes(word)) || false;
  }
  const search = form => !config?.conservative && form?.method === 'get' && form.search;
  function report(kind, element, submitter = null, cancellable = true) {
    const id = 'h' + (++sequence);
    const step = {id,kind,element:reader.id(element),submitter:submitter ? reader.id(submitter) : null,cancellable};
    held.set(id,{...step,node:element,button:submitter});
  }
  function allowance(form) {
    if (!mark || mark.form !== form) return false;
    if (!mark.primary) { mark.primary = true; return true; }
    if (!mark.further) { mark.further = true; return true; }
    return false;
  }
  function submit(form, submitter, kind) {
    if (!(form instanceof HTMLFormElement)) return;
    if (!active() || ownerDispatch() || search(reader.form(form,submitter)) || allowance(form)) {
      if (kind === 'native_submit') native.submit.call(form);
      else if (submitter) native.requestSubmit.call(form,submitter);
      else native.requestSubmit.call(form);
    } else report(kind,form,submitter);
  }
  function capture(event) {
    if (event.isTrusted && ['pointerdown','mousedown','click','keydown','keyup','input','change'].includes(type(event)) && !inFlight) owner=event;
    if (!active() || ownerDispatch()) return;
    const element=event.composedPath()[0];
    if (!(element instanceof Element)) return;
    if (type(event) === 'submit') {
      if (search(reader.form(element,event.submitter)) || allowance(element)) return;
      event.preventDefault();event.stopImmediatePropagation();report('submit_event',element,event.submitter);
    } else if (type(event) === 'click' && asks(element)) {
      // Only the browser's trusted event for this private, approved dispatch consumes the mark.
      if (inFlight && event.isTrusted && mark && !mark.input && element === mark.target) { mark.input=true;return; }
      if (event.cancelable) event.preventDefault();
      event.stopImmediatePropagation();report(event.cancelable ? 'activation' : 'activation_unknown',element,null,event.cancelable);
    }
  }
  function onCall(event) {
    // A page may forge this report. It can only request another normally guarded page step.
    // The element comes from native event dispatch, never a page-supplied identity string.
    event.stopImmediatePropagation();
    const element=event.composedPath()[0];
    if (!(element instanceof Element) || !reader) { event.preventDefault();return; }
    try {
      const detail=event.detail;
      if (detail?.kind === 'native_submit') submit(element,null,'native_submit');
      else if (detail?.kind === 'request_submit') {
        // Validation and the native submit event must precede interception.
        const button=detail.submitter;
        if (button != null && (!(button instanceof HTMLElement) || button.form !== element)) {event.preventDefault();return;}
        if (element instanceof HTMLFormElement) {
          if (button) native.requestSubmit.call(element,button); else native.requestSubmit.call(element);
        }
      } else if (detail?.kind === 'click' || detail?.kind === 'dispatch') {
        const original=detail.kind === 'dispatch' ? detail.event : null;
        const isClick=detail.kind === 'click' || type(original) === 'click';
        if (active() && !ownerDispatch() && isClick && asks(element)) {
          report('activation',element,null,original?.cancelable ?? true);event.preventDefault();return;
        }
        if (original) { if (!native.dispatch.call(element,original)) event.preventDefault(); }
        else native.click.call(element);
      } else event.preventDefault();
    } catch { event.preventDefault(); } // Invalid/forged reports can only add a hold.
  }
  function watch(root) {
    if (roots.has(root)) return;
    roots.add(root);
    root.addEventListener('aresos-page-call-v2',onCall,true);
    for (const kind of ['pointerdown','mousedown','click','keydown','keyup','input','change','submit']) root.addEventListener(kind,capture,true);
  }
  watch(window);
  // This object exists only in the extension's isolated world. MAIN has no API or capability.
  globalThis[Symbol.for('aresos.chrome.guard.v2')] = {
    reader(value) { reader=value; }, watch,
    arm(value) {
      generation=value.generation;config=value.config;inFlight=true;owner=null;until=performance.now()+config.holdMs;
      mark=value.operation ? {id:value.operation,target:reader.element(value.target),form:reader.element(value.form),input:false,primary:!value.primary_submission,further:false} : null;
    },
    async finish(epoch) {
      // A private message plus a later browser task over-covers the synchronous input handlers.
      await new Promise(resolve=>setTimeout(resolve,0));
      if (generation===epoch) { inFlight=false;mark=null; }
    },
    clear() { generation=null;until=0;inFlight=false;mark=null;owner=null;held.clear(); },
    steps() { const result=[...held.values()].filter(step=>!step.reported).map(step=>{step.reported=true;return {id:step.id,kind:step.kind,element:step.element,submitter:step.submitter,cancellable:step.cancellable};});return result; },
    resume(id,operation) {
      const step=held.get(id);
      if (!step || consumed.has(operation) || !['native_submit','submit_event'].includes(step.kind) || !step.node.isConnected || step.button && (!step.button.isConnected || step.button.form!==step.node)) throw Error('stale_reference: form, submitter or operation changed');
      consumed.add(operation);held.delete(id);
      mark={id:operation,target:step.button,form:step.node,input:true,primary:step.kind==='native_submit',further:false};
      if (step.kind==='native_submit') native.submit.call(step.node);
      else if (step.button) native.requestSubmit.call(step.node,step.button);
      else native.requestSubmit.call(step.node);
      return {resumed:step.kind};
    },
  };
})();
