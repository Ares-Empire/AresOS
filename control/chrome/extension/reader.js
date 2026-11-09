// Isolated world only. Never serialise HTML, attributes or forms in bulk.
(() => {
  const elements = new Map(), ids = new WeakMap(), protectedFields = new WeakSet(), held = new Map();
  const documentId = crypto.randomUUID();
  let sequence = 0, revision = 0;
  const traces = [], files = new Map();
  function roots(root = document) {
    const found = [root];
    for (const element of root.querySelectorAll('*')) {
      const shadow = chrome.dom.openOrClosedShadowRoot(element);
      if (shadow) found.push(...roots(shadow));
    }
    return found;
  }
  const all = () => roots().flatMap(root => [...root.querySelectorAll('*')]);
  function password(element) {
    if (!(element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement || element.isContentEditable)) return false;
    let unsafe = protectedFields.has(element);
    try {
      unsafe ||= element.type === 'password' || /(?:^|\s)(current-password|new-password|one-time-code)(?:\s|$)/i.test(element.getAttribute('autocomplete') || '') ||
        getComputedStyle(element).webkitTextSecurity !== 'none';
    } catch { unsafe = true; }
    if (unsafe) protectedFields.add(element);
    return unsafe;
  }
  function remember(root) {
    for (const element of root.querySelectorAll('input,textarea,[contenteditable]')) password(element);
    for (const element of root.querySelectorAll('*')) {
      const shadow = chrome.dom.openOrClosedShadowRoot(element);
      if (shadow) { observer.observe(shadow, {subtree: true, attributes: true, childList: true, characterData: true, attributeOldValue: true}); remember(shadow); }
    }
  }
  const observer = new MutationObserver(changes => {
    revision++;
    for (const change of changes) {
      if (change.type === 'attributes') {
        if (change.attributeName === 'type' && change.oldValue === 'password' || change.attributeName === 'autocomplete' && /(?:password|one-time-code)/.test(change.oldValue || '')) protectedFields.add(change.target);
        password(change.target);
      }
    }
    remember(document);
  });
  observer.observe(document, {subtree: true, attributes: true, childList: true, characterData: true, attributeOldValue: true});
  remember(document);
  const id = element => {
    if (!ids.has(element)) { const key = 'e' + (++sequence); ids.set(element, key); elements.set(key, element); document.dispatchEvent(new CustomEvent('aresos-reader-identity', {detail:{id:key, element}})); }
    return ids.get(element);
  };
  function text(node) {
    if (node.nodeType === Node.TEXT_NODE) return node.textContent;
    if (!(node instanceof Element) || ['SCRIPT','STYLE','NOSCRIPT','INPUT','TEXTAREA','SELECT'].includes(node.tagName) || password(node)) return '';
    if (node.hidden || getComputedStyle(node).display === 'none' || getComputedStyle(node).visibility === 'hidden') return '';
    return [...node.childNodes].map(text).join(' ');
  }
  function name(element) {
    const root = element.getRootNode();
    const labelled = (element.getAttribute('aria-labelledby') || '').split(/\s+/).map(key => root.getElementById?.(key)).filter(Boolean);
    return (labelled.length ? labelled.map(text).join(' ') : element.getAttribute('aria-label') ||
      (element.labels?.length ? [...element.labels].map(text).join(' ') : element.getAttribute('alt') || element.getAttribute('title') ||
      (['BUTTON','A','SUMMARY'].includes(element.tagName) || element.hasAttribute('role') ? text(element) : element.getAttribute('placeholder') || ''))).replace(/\s+/g, ' ').trim();
  }
  function safeValue(element) {
    // The exclusion is repeated immediately before EACH value/text read.
    if (password(element)) return {password: true};
    let value;
    if (element instanceof HTMLInputElement) {
      if (element.type === 'file') value = [...element.files].map(file => ({name: file.name, size: file.size, lastModified: file.lastModified}));
      else value = element.value;
    } else if (element instanceof HTMLTextAreaElement || element instanceof HTMLSelectElement) value = element.value;
    else if (element.isContentEditable) value = text(element);
    else return {};
    traces.push({element: id(element), value});
    return {value};
  }
  function role(element) {
    if (element.getAttribute('role')) return element.getAttribute('role');
    const tag = element.tagName;
    if (tag === 'INPUT') return {checkbox:'checkbox',radio:'radio',submit:'button',button:'button',range:'slider',search:'searchbox',hidden:'hidden'}[element.type] || 'textbox';
    return {BUTTON:'button',A:element.href ? 'link':'generic',TEXTAREA:'textbox',SELECT:'combobox',OPTION:'option',FORM:'form',DIALOG:'dialog',LI:'listitem',TR:'row',ARTICLE:'article',SECTION:'region',H1:'heading',H2:'heading',H3:'heading',P:'paragraph',TD:'cell',TH:'columnheader',IFRAME:'iframe'}[tag] || (element.isContentEditable ? 'textbox' : 'generic');
  }
  function field(element) {
    return {element: id(element), name: element.getAttribute('name') || '', label: name(element), type: element.type || element.getAttribute('role') || 'editable',
      hidden: element.type === 'hidden', ...safeValue(element),
      ...(element instanceof HTMLSelectElement ? {options: [...element.options].map(option => ({label: text(option), value: option.value, selected: option.selected, disabled: option.disabled}))} : {})};
  }
  function formFacts(form, submitter) {
    if (!form) return null;
    return {element: id(form), action: submitter?.getAttribute('formaction') ? submitter.formAction : form.action,
      method: (submitter?.getAttribute('formmethod') || form.method).toLowerCase(), encoding: submitter?.getAttribute('formenctype') || form.enctype,
      target: submitter?.getAttribute('formtarget') ?? form.target, search: form.role === 'search' || !!form.querySelector('input[type=search]'),
      fields: [...form.elements].map(field)};
  }
  function targetFacts(element) {
    const box = element.getBoundingClientRect(), value = safeValue(element);
    return {element: id(element), role: role(element), name: name(element), label: name(element), title: element.getAttribute('title') || '', ...value,
      href: element.tagName === 'A' ? element.href : null,
      editable: element instanceof HTMLInputElement && !['button','submit','image','checkbox','radio','file','hidden'].includes(element.type) || element instanceof HTMLTextAreaElement || element.isContentEditable,
      search: element.type === 'search' || element.getAttribute('role') === 'searchbox', submit: !!element.form && (element.type === 'submit' || element.type === 'image'),
      states: {checked: !!element.checked, selected: !!element.selected, disabled: !!element.disabled, required: !!element.required, invalid: element.getAttribute('aria-invalid') === 'true', expanded: element.getAttribute('aria-expanded')},
      box: {x:box.x,y:box.y,width:box.width,height:box.height}, onscreen: box.bottom > 0 && box.right > 0 && box.top < innerHeight && box.left < innerWidth && box.width > 0 && box.height > 0};
  }
  function itemText(element) {
    return text(element.closest('li,tr,article,form,dialog,[role=dialog],[role=alertdialog],[role=region]') || element).replace(/\s+/g, ' ').trim();
  }
  function snapshot(elementId) {
    const element = elementId ? elements.get(elementId) : null;
    if (elementId && (!element || !element.isConnected)) throw Error('stale_reference: element is gone; read again');
    const nodes = all(), modal = nodes.find(node => node.matches('dialog[open],[role=dialog][aria-modal=true],[role=alertdialog][aria-modal=true]'));
    const rows = nodes.filter(node => (!modal || modal.contains(node)) && !['SCRIPT','STYLE','NOSCRIPT','OPTION'].includes(node.tagName)).map(node => {
      const facts = targetFacts(node);
      if (facts.role === 'generic' && !node.isContentEditable) return null;
      if (facts.role === 'hidden' || !facts.box.width || !facts.box.height) return null;
      return {...facts, text: ['textbox','combobox','button','link','iframe'].includes(facts.role) ? '' : text(node).replace(/\s+/g, ' ').trim()};
    }).filter(Boolean);
    const editable = nodes.filter(node => node.matches('input,textarea,select,[contenteditable]')).map(field);
    return {document: documentId, revision, url: location.href, title: document.title, scroll: {x:scrollX,y:scrollY}, rows,
      target: element ? targetFacts(element) : null, form: element ? formFacts(element.form || (element.tagName === 'FORM' ? element : null), element) : null,
      editable, item: element ? itemText(element) : '', adapter: adapterRead(nodes, element), trace: traces.splice(0)};
  }
  function adapterRead(nodes, target) {
    // Semantic selectors for the named sites; an incomplete shape never claims recognition.
    const find = selectors => { for (const selector of selectors) { const found = nodes.find(node => node.matches(selector)); if (found) return found; } return null; };
    const read = selectors => { const node = find(selectors); if (!node) return null; return node.matches('input,textarea,[contenteditable]') ? safeValue(node).value ?? null : text(node).trim(); };
    return {account: read(['[aria-label^="Google Account:"]','[data-login]','[aria-label="Signed in as"]']),
      to: read(['[name=to]','[aria-label=To]']), cc: read(['[name=cc]','[aria-label=Cc]']), bcc: read(['[name=bcc]','[aria-label=Bcc]']),
      subject: read(['[name=subjectbox]','[name=subject]']), text: read(['[aria-label="Message Body"]','[aria-label="Type a message"]','[aria-label="Enter a prompt here"]','[name=comment]']),
      chat: read(['header [title]','[aria-label="Chat name"]']),
      context: read(['[aria-label="Action context"]']), preview: read(['[aria-label="Message preview"]']),
      attachments: nodes.filter(node => node.matches('[aria-label^="Attachment:"]')).map(node => ({label:name(node), text:text(node)})),
      target: target ? name(target) : null};
  }
  document.addEventListener('aresos-dialog-origin',event=>{
    if(['alert','confirm','prompt'].includes(event.detail?.kind) && typeof event.detail?.text === 'string')
      chrome.runtime.sendMessage({event:'dialog_origin',kind:event.detail.kind,text:event.detail.text});
  },true);
  document.addEventListener('aresos-page-step', event => {
    const value = event.detail;
    if (!value || !['native_submit','submit_event','activation','activation_unknown'].includes(value.kind) || !(value.target instanceof Element)) return;
    held.set(value.id, {id:value.id, kind:value.kind, element:id(value.target), submitter:value.submitter ? id(value.submitter):null, cancellable:value.cancellable});
  }, true);
  chrome.runtime.onMessage.addListener((message, sender, reply) => {
    if (sender.id !== chrome.runtime.id || !message || typeof message.command !== 'string') return;
    if (message.command === 'install_file') {
      (async()=>{
        const staged=files.get(message.token), element=elements.get(message.element);
        if(!staged || !element?.isConnected || element.type !== 'file')throw Error('stale_reference: upload field or bytes changed');
        const file=new File(staged.chunks,staged.file.name,{type:'application/octet-stream',lastModified:0});
        const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',await file.arrayBuffer()))].map(value=>value.toString(16).padStart(2,'0')).join('');
        if(hash !== staged.file.sha256 || file.size !== staged.file.size)throw Error('stale_approval: upload hash mismatch');
        files.delete(message.token);
        const transfer=new DataTransfer();transfer.items.add(file);element.files=transfer.files;
        element.dispatchEvent(new Event('input',{bubbles:true}));element.dispatchEvent(new Event('change',{bubbles:true}));
        reply({ok:true,data:{installed:true,sha256:hash,size:file.size}});
      })().catch(error=>reply({ok:false,error:String(error.message)}));
      return true;
    }
    try {
      let value;
      if (message.command === 'stage_file') {
        if(!files.has(message.token)) {
          if(message.offset !== 0 || files.size >= 2)throw Error('refused: upload staging limit');
          files.set(message.token,{file:message.file,chunks:[],size:0});
        }
        const staged=files.get(message.token), bytes=Uint8Array.from(atob(message.bytes),char=>char.charCodeAt(0));
        if(staged.size !== message.offset || staged.size+bytes.length > staged.file.size || staged.size+bytes.length > 25*1024*1024)throw Error('refused: upload offset or size mismatch');
        staged.chunks.push(bytes);staged.size+=bytes.length;value={offset:staged.size};
      }
      else if (message.command === 'clear') { files.clear(); held.clear(); value={cleared:true}; }
      else if (message.command === 'ready') value = {preload:true,document:documentId};
      else if (message.command === 'read' || message.command === 'facts') value = snapshot(message.element);
      else if (message.command === 'steps') { value = [...held.values()]; held.clear(); }
      else if (message.command === 'focus') {
        const element = elements.get(message.element);
        if (!element?.isConnected) throw Error('stale_reference: read again');
        if (password(element)) throw Error('owner_signin: password fields belong to the owner');
        element.focus(); value = {focused:true};
      } else if (message.command === 'select' || message.command === 'check') {
        const element = elements.get(message.element);
        if (!element?.isConnected || password(element)) throw Error('stale_reference: read again');
        if (message.command === 'select') element.value = message.value;
        else element.checked = message.checked;
        element.dispatchEvent(new Event('input', {bubbles:true})); element.dispatchEvent(new Event('change', {bubbles:true}));
        value = {changed:true};
      } else throw Error('permission_denied: unknown content command');
      reply({ok:true, data:value});
    } catch (error) { reply({ok:false, error:String(error.message)}); }
  });
  // Fixed functions used by scripting.executeScript; DOM identity never comes from a selector supplied by the caller.
  globalThis[Symbol.for('aresos.chrome.reader.v1')] = {element: key => elements.get(key)};
})();
