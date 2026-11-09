// Runs at document_start in MAIN. Page-owned activations are never queued for replay.
(() => {
  const key = Symbol.for('aresos.chrome.page.v1');
  if (globalThis[key]) return;
  const native = {
    submit: HTMLFormElement.prototype.submit,
    requestSubmit: HTMLFormElement.prototype.requestSubmit,
    click: HTMLElement.prototype.click,
    dispatch: EventTarget.prototype.dispatchEvent,
    attachShadow: Element.prototype.attachShadow,
  };
  let until = 0, policy = null, mark = null, sequence = 0;
  const identities = new Map();
  document.addEventListener('aresos-reader-identity', event => { if (event.detail?.element instanceof Element) identities.set(event.detail.id, event.detail.element); }, true);
  for (const kind of ['alert','confirm','prompt']) {
    const original=window[kind];
    if(typeof original !== 'function')continue;
    window[kind]=function(...args) {
      const remaining=active() ? Math.max(0,until-performance.now()):0;
      native.dispatch.call(document,new CustomEvent('aresos-dialog-origin',{detail:{kind,text:String(args[0] ?? '')}}));
      try { return original.apply(this,args); }
      finally { if(remaining)until=performance.now()+remaining; }
    };
  }
  const held = new Map(), seenRoots = new WeakSet();
  const active = () => performance.now() < until;
  const words = text => policy && String(text).toLocaleLowerCase().match(/[\p{L}\p{N}_]+/gu)?.some(w => policy.words.includes(w));
  function control(node) {
    return node instanceof Element ? node.closest('button,input,a,[role=button],[role=link],[role=menuitem],[onclick]') || node : null;
  }
  function asks(node) {
    const element = control(node);
    if (!element) return false;
    if (element.form && ((element.tagName === 'BUTTON' && (!element.type || element.type === 'submit')) || element.type === 'submit' || element.type === 'image')) {
      const form = element.form;
      if (!(form.method.toLowerCase() === 'get' && (form.role === 'search' || form.querySelector('input[type=search]')))) return true;
    }
    if (element.matches('textarea,[contenteditable]') || element instanceof HTMLInputElement && ['password','text','search','email','tel','url'].includes(element.type)) return false;
    const labels = [element.getAttribute('aria-label'), element.getAttribute('title'), element.getAttribute('role'), element.textContent,
      element instanceof HTMLInputElement && !['password', 'text', 'search', 'email', 'tel', 'url'].includes(element.type) ? element.value : '', element.form?.action];
    return words(labels.join(' '));
  }
  function report(kind, target, submitter, cancellable = true) {
    const id = 'h' + (++sequence);
    if (kind === 'native_submit' || kind === 'submit_event') held.set(id, {kind, form: target, submitter});
    native.dispatch.call(document, new CustomEvent('aresos-page-step', {detail: {id, kind, target, submitter, cancellable}}));
    return id;
  }
  function allowSubmission(form) {
    if (!mark || mark.form !== form) return false;
    if (!mark.primarySubmission) { mark.primarySubmission = true; return true; }
    if (!mark.furtherSubmission) { mark.furtherSubmission = true; return true; }
    return false;
  }
  HTMLFormElement.prototype.submit = function() {
    if (!active() || allowSubmission(this)) return native.submit.call(this);
    report('native_submit', this, null);
  };
  // requestSubmit must first perform browser validation and create its submit event.
  HTMLFormElement.prototype.requestSubmit = function(submitter) {
    return arguments.length ? native.requestSubmit.call(this, submitter) : native.requestSubmit.call(this);
  };
  HTMLElement.prototype.click = function() {
    if (active() && asks(this)) { report('activation', control(this), null); return; }
    return native.click.call(this);
  };
  EventTarget.prototype.dispatchEvent = function(event) {
    if (active() && event.type === 'click' && asks(this)) { report('activation', control(this), null, event.cancelable); return true; }
    return native.dispatch.call(this, event);
  };
  function capture(event) {
    if (!active()) return;
    if (event.type === 'submit') {
      if (allowSubmission(event.target)) return;
      event.preventDefault(); event.stopImmediatePropagation();
      report('submit_event', event.target, event.submitter);
    } else if (asks(event.composedPath()[0])) {
      if (mark && !mark.input && control(event.composedPath()[0]) === mark.target) { mark.input = true; return; }
      if (event.cancelable) event.preventDefault();
      event.stopImmediatePropagation();
      report(event.cancelable ? 'activation' : 'activation_unknown', control(event.composedPath()[0]), null, event.cancelable);
    }
  }
  function watch(root) {
    if (seenRoots.has(root)) return;
    seenRoots.add(root);
    root.addEventListener('submit', capture, true);
    root.addEventListener('click', capture, true);
  }
  watch(window);
  Element.prototype.attachShadow = function(options) {
    const root = native.attachShadow.call(this, options); watch(root); return root;
  };
  // Called only by fixed extension functions; no script text or CDP methods cross the host channel.
  globalThis[key] = {
    arm(config, target, form, operation) {
      target = identities.get(target); form = identities.get(form);
      policy = config; until = performance.now() + config.holdMs;
      mark = operation ? {id: operation, target, form, input: false, primarySubmission: false, furtherSubmission: false} : null;
    },
    stop() { until = 0; mark = null; held.clear(); },
    drop(id) { held.delete(id); },
    resume(id, operation) {
      const step = held.get(id);
      if (!step || !step.form.isConnected || step.submitter && (!step.submitter.isConnected || step.submitter.form !== step.form)) throw Error('stale_reference: form or submitter is gone');
      held.delete(id);
      until = performance.now() + policy.holdMs;
      mark = {id: operation, target: step.submitter, form: step.form, input: true, primarySubmission: true, furtherSubmission: false};
      // The primary pass is consumed BEFORE the native function enters nested handlers.
      if (step.kind === 'native_submit') native.submit.call(step.form);
      else {
        mark.primarySubmission = false;
        if (step.submitter) native.requestSubmit.call(step.form, step.submitter);
        else native.requestSubmit.call(step.form);
      }
      return {resumed: step.kind};
    },
  };
})();
