// Isolated world only. Never serialise HTML, attributes or forms in bulk.
(() => {
  'use strict';
  try {
  const elements = new Map(), ids = new WeakMap();
  // This passive ISOLATED tracker has document lifetime, including release/retake.
  const privacyKey=Symbol.for('aresos.chrome.passwords.v1');
  const privacy=globalThis[privacyKey]??={protectedFields:new WeakSet(),observed:new WeakSet(),fileIdentities:new WeakMap()};
  const {protectedFields,fileIdentities}=privacy;
  const guard=globalThis[Symbol.for('aresos.chrome.guard.v2')];
  if(guard.ready)return;
  const documentId = privacy.documentId??=[...crypto.getRandomValues(new Uint8Array(16))].map(value=>value.toString(16).padStart(2,'0')).join('');
  let sequence = 0, revision = 0, controlGeneration = null;
  const traces = [], files = new Map(), watchedRoots = new WeakSet();
  const formGetters=globalThis.HTMLFormElement?Object.fromEntries(['elements','action','method','enctype','target'].map(key=>[key,Object.getOwnPropertyDescriptor(HTMLFormElement.prototype,key)?.get])):{};
  const formProperty=(form,key)=>formGetters[key]?formGetters[key].call(form):form[key];
  const formQuery=(form,selector)=>Element.prototype.querySelector?Element.prototype.querySelector.call(form,selector):form.querySelector(selector);
  const shadow=element=>element instanceof HTMLElement ? chrome.dom.openOrClosedShadowRoot(element):null;
  function roots(root = document) {
    const found = [root];
    for (const element of root.querySelectorAll('*')) {
      const childShadow = shadow(element);
      if (childShadow) { guard.watch(childShadow); found.push(...roots(childShadow)); }
    }
    return found;
  }
  const all = () => roots().flatMap(root => [...root.querySelectorAll('*')]);
  let observer, revisionObserver;
  function observe(root) {
    revisionObserver.observe(root,{subtree:true,attributes:true,childList:true,characterData:true});
    // Never ask the browser to include old value attributes in mutation records.
    if(!privacy.observed.has(root)){privacy.observed.add(root);observer.observe(root,{subtree:true,attributes:true,attributeOldValue:true,attributeFilter:['type','autocomplete','style']});}
  }
  function protect(changes) {
    for(const change of changes)if(change.type==='attributes' && (change.attributeName==='type' && (change.oldValue||'').toLowerCase()==='password' || change.attributeName==='autocomplete' && /(?:password|one-time-code)/i.test(change.oldValue||'') || change.attributeName==='style' && /-webkit-text-security\s*:\s*(?!none\b)/i.test(change.oldValue||'')))protectedFields.add(change.target);
  }
  function ownPassword(element) {
    if(protectedFields.has(element))return true;
    if (!(element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement || element instanceof HTMLSelectElement || element instanceof HTMLButtonElement || element.isContentEditable)) return false;
    let unsafe = protectedFields.has(element);
    try {
      unsafe ||= element.type === 'password' || /(?:^|\s)(current-password|new-password|one-time-code)(?:\s|$)/i.test(element.getAttribute('autocomplete') || '') ||
        getComputedStyle(element).webkitTextSecurity !== 'none';
    } catch { unsafe = true; }
    if (unsafe) protectedFields.add(element);
    return unsafe;
  }
  function password(element) {
    if(observer?.takeRecords)protect(observer.takeRecords());
    for(let node=element;node;node=node.parentElement||node.getRootNode?.().host){
      if(node instanceof Element && ownPassword(node))return true;
    }
    return false;
  }
  function remember(root) {
    if(!watchedRoots.has(root)){watchedRoots.add(root);guard.watch(root);}
    for (const element of root.querySelectorAll('input,textarea,[contenteditable]')) password(element);
    for (const element of root.querySelectorAll('*')) {
      const childShadow = shadow(element);
      if (childShadow) { guard.watch(childShadow); observe(childShadow); remember(childShadow); }
    }
  }
  const changed = changes => {
    revision++;protect(changes);
    for (const change of changes) {
      if (change.type === 'attributes') {
        if (change.attributeName === 'type' && (change.oldValue||'').toLowerCase() === 'password' || change.attributeName === 'autocomplete' && /(?:password|one-time-code)/i.test(change.oldValue || '')) protectedFields.add(change.target);
        password(change.target);
      }
    }
    remember(document);
  };
  revisionObserver = new MutationObserver(changed);
  observer = privacy.observer??=new MutationObserver(protect);
  observe(document);
  remember(document);
  const id = element => {
    if (!ids.has(element)) { const key = 'e' + (++sequence); ids.set(element, key); elements.set(key, element); }
    return ids.get(element);
  };
  function text(node, includeHidden=false) {
    if(node.nodeType===Node.TEXT_NODE)return node.parentElement&&password(node.parentElement)?'':node.textContent;
    if (!(node instanceof Element) || ['SCRIPT','STYLE','NOSCRIPT','INPUT','TEXTAREA','SELECT'].includes(node.tagName) || password(node)) return '';
    if (!includeHidden && (node.hidden || getComputedStyle(node).display === 'none' || getComputedStyle(node).visibility === 'hidden')) return '';
    if(node.tagName==='IMG')return node.getAttribute('alt')||'';
    return [...node.childNodes].map(child=>text(child,includeHidden)).join(' ');
  }
  function name(element) {
    const root = element.getRootNode();
    const labelled = (element.getAttribute('aria-labelledby') || '').split(/\s+/).map(key => root.getElementById?.(key)).filter(Boolean);
    const buttonValue=element instanceof HTMLInputElement && ['button','submit','reset'].includes(element.type) ? safeValue(element).value || (element.type==='submit'?'Submit':element.type==='reset'?'Reset':''):null;
    return (labelled.length ? labelled.map(node=>text(node,true)).join(' ') : element.getAttribute('aria-label') ||
      (element.labels?.length ? [...element.labels].map(node=>text(node,true)).join(' ') : element.getAttribute('alt') || buttonValue ||
      ((['BUTTON','A','SUMMARY'].includes(element.tagName) || element.hasAttribute('role') ? text(element) : element.getAttribute('placeholder') || '') || element.getAttribute('title') || ''))).replace(/\s+/g, ' ').trim();
  }
  function editableText(node) {
    if(node.nodeType===Node.TEXT_NODE)return node.parentElement&&password(node.parentElement)?'':node.textContent;
    if(!(node instanceof Element)||password(node)||['SCRIPT','STYLE','NOSCRIPT','INPUT','TEXTAREA','SELECT'].includes(node.tagName))return '';
    const style=getComputedStyle(node);if(node.hidden||style.display==='none'||style.visibility==='hidden')return '';
    if(node.tagName==='BR')return '\n';
    let result='';
    for(const child of node.childNodes){
      const block=child instanceof Element&&(['DIV','P','LI','TR','SECTION','ARTICLE','BLOCKQUOTE','PRE'].includes(child.tagName)||['block','list-item','table-row'].includes(getComputedStyle(child).display));
      if(block&&result&&!result.endsWith('\n'))result+='\n';
      result+=editableText(child);
      if(block&&!result.endsWith('\n'))result+='\n';
    }
    return result;
  }
  const blobSize=globalThis.Blob&&Object.getOwnPropertyDescriptor(Blob.prototype,'size')?.get;
  function selectedFile(file){
    if(!blobSize)throw Error('refused: selected file content identity cannot be verified');
    const size=blobSize.call(file); // Native Blob identity denotes immutable bytes.
    if(!fileIdentities.has(file))fileIdentities.set(file,{identity:crypto.randomUUID()});
    return {name:file.name,size,lastModified:file.lastModified,...fileIdentities.get(file)};
  }
  function safeValue(element) {
    // The exclusion is repeated immediately before EACH value/text read.
    if (password(element)) return {password: true};
    let value;
    if (element instanceof HTMLInputElement) {
      if (element.type === 'file') value = [...element.files].map(selectedFile);
      else value = element.value;
    } else if (element instanceof HTMLTextAreaElement || element instanceof HTMLSelectElement || element instanceof HTMLButtonElement) value = element.value;
    else if (element.isContentEditable) value = editableText(element).replace(/\n$/, '');
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
    const safe=safeValue(element);
    return {element: id(element), name: element.getAttribute('name') || '', label: name(element), type: element.type || element.getAttribute('role') || 'editable',
      hidden: element.type === 'hidden', checked:!!element.checked, disabled:element.matches(':disabled'), multiple:!!element.multiple, readOnly:!!element.readOnly, ...safe,
      ...(element instanceof HTMLSelectElement && !safe.password ? {options: [...element.options].map(option => ({label: text(option), value: option.value, selected: option.selected, disabled: option.matches(':disabled')}))} : {})};
  }
  function formFacts(form, submitter) {
    if (!form) return null;
    const button=submitter?.form===form&&['submit','image'].includes(submitter.type)?submitter:null;
    return {element: id(form), action: button?.hasAttribute('formaction') ? button.formAction : formProperty(form,'action'),
      method: (button?.hasAttribute('formmethod') ? button.formMethod : formProperty(form,'method')).toLowerCase(),
      encoding: button?.hasAttribute('formenctype') ? button.formEnctype : formProperty(form,'enctype'),
      target: button?.hasAttribute('formtarget') ? button.formTarget : formProperty(form,'target'),
      search: form.role === 'search' || !!formQuery(form,'input[type=search]'),
      fields: [...formProperty(form,'elements')].map(field)};
  }
  function implicitSubmitter(element) {
    if(!(element instanceof HTMLInputElement) || !element.form || ['button','submit','image','checkbox','radio','file','hidden','range','color'].includes(element.type))return null;
    return [...element.getRootNode().querySelectorAll('button,input')].find(control=>control.form===element.form&&['submit','image'].includes(control.type)) || null;
  }
  function targetFacts(element) {
    const box = element.getBoundingClientRect(), value = safeValue(element);
    const dialog=element.closest('dialog,[role=dialog],[role=alertdialog]');
    const page_dialog=dialog ? {element:id(dialog),kind:role(dialog),text:text(dialog).replace(/\s+/g,' ').trim(),button:name(element),fields:[...dialog.querySelectorAll('input,textarea,select,[contenteditable]')].map(field)} : null;
    return {element: id(element), role: role(element), page_dialog, name: name(element), label:element.labels?.length?[...element.labels].map(node=>text(node,true)).join(' ').replace(/\s+/g,' ').trim():name(element), title: element.getAttribute('title') || '', ...value,
      ...(element instanceof HTMLSelectElement && !value.password ? {options:field(element).options}:{}),
      ...(implicitSubmitter(element) ? {implicit_submitter:id(implicitSubmitter(element))}:{}),
      href: element.tagName === 'A' ? element.href : null,
      editable: element instanceof HTMLInputElement && !['button','submit','image','checkbox','radio','file','hidden'].includes(element.type) || element instanceof HTMLTextAreaElement || element.isContentEditable,
      search: element.type === 'search' || element.getAttribute('role') === 'searchbox', submit: !!element.form && (element.type === 'submit' || element.type === 'image'),
      states: {checked: !!element.checked, selected: !!element.selected, disabled: !!element.disabled, required: !!element.required, invalid: element.getAttribute('aria-invalid') === 'true', expanded: element.getAttribute('aria-expanded')},
      box: {x:box.x,y:box.y,width:box.width,height:box.height}, onscreen: box.bottom > 0 && box.right > 0 && box.top < innerHeight && box.left < innerWidth && box.width > 0 && box.height > 0};
  }
  function itemText(element) {
    return text(element.closest('li,tr,article,[role=listitem],[role=row],[role=article],section[aria-label],section[aria-labelledby],form,dialog,[role=dialog],[role=alertdialog],[role=region]') || element).replace(/\s+/g, ' ').trim();
  }
  function embedding(element) {
    const box=element.getBoundingClientRect();let aligned=true;
    for(let ancestor=element;ancestor;ancestor=ancestor.parentElement || ancestor.getRootNode().host){
      const transform=getComputedStyle(ancestor).transform;
      if(transform && transform!=='none'){
        const matrix=new DOMMatrixReadOnly(transform);
        if(!matrix.is2D || matrix.b!==0 || matrix.c!==0 || matrix.a<=0 || matrix.d<=0)aligned=false;
      }
    }
    return {element:id(element),url:element.hasAttribute('srcdoc') ? 'about:srcdoc':element.src || 'about:blank',box:{x:box.x,y:box.y,width:box.width,height:box.height},
      width:element.offsetWidth,height:element.offsetHeight,borderX:element.clientLeft,borderY:element.clientTop,aligned};
  }
  function hit(element,x,y){
    let actual=document.elementFromPoint(x,y);
    while(actual){const root=shadow(actual),deeper=root?.elementFromPoint(x,y);if(!deeper || deeper===actual)break;actual=deeper;}
    for(let node=actual;node;node=node.parentElement || node.getRootNode().host)if(node===element)return true;
    return false;
  }
  function snapshot(elementId) {
    const element = elementId ? elements.get(elementId) : null;
    if (elementId && (!element || !element.isConnected)) throw Error('stale_reference: element is gone; read again');
    const nodes = all(), modal = nodes.find(node => node.matches('dialog[open],[role=dialog][aria-modal=true],[role=alertdialog][aria-modal=true]'));
    const rows = nodes.filter(node => (!modal || modal.contains(node)) && !['SCRIPT','STYLE','NOSCRIPT','OPTION'].includes(node.tagName)).map(node => {
      const facts = targetFacts(node);
      if (facts.role === 'generic' && !node.isContentEditable) {
        if(password(node))return null;
        const own=[...node.childNodes].filter(child=>child.nodeType===Node.TEXT_NODE).map(child=>child.textContent).join(' ').replace(/\s+/g,' ').trim();
        if(!own || password(node) || node.hidden || getComputedStyle(node).display==='none' || getComputedStyle(node).visibility==='hidden')return null;
        facts.role='text';facts.name=own;
      }
      if (facts.role === 'hidden' || !facts.box.width || !facts.box.height) return null;
      return {...facts, text: ['textbox','combobox','button','link','iframe'].includes(facts.role) ? '' : text(node).replace(/\s+/g, ' ').trim()};
    }).filter(Boolean);
    const editable = nodes.filter(node => node.matches('input,textarea,select,[contenteditable]') && !['hidden','button','submit','reset','image','file'].includes(node.type)).map(field);
    return {document: documentId, revision, url: location.href, origin:globalThis.origin, title: document.title, scroll: {x:scrollX,y:scrollY}, rows,
      target: element ? targetFacts(element) : null, form: element ? formFacts(element.form || (element.tagName === 'FORM' ? element : null), implicitSubmitter(element) || element) : null,
      editable, embeds:nodes.filter(node=>node.tagName==='IFRAME').map(embedding), item: element ? itemText(element) : '', adapter: adapterRead(nodes, element), trace: traces.splice(0)};
  }
  function adapterRead(nodes, target) {
    const scope=target?.closest('form,[role=dialog],[role=region][aria-label],main,[role=main]');
    const scoped=scope ? nodes.filter(node=>scope===node || scope.contains(node)):nodes;
    const read=(selectors,collection=scoped)=>{
      for(const selector of selectors) {
        const found=collection.filter(node=>node.matches(selector));
        if(found.length>1)return null;
        if(found.length===1){const node=found[0];return node.matches('input,textarea,[contenteditable]') ? safeValue(node).value ?? null : text(node).trim();}
      }
      return null;
    };
    const recognizedScope=scope;
    const fields=recognizedScope ? scoped:[];
    return {scope:recognizedScope ? id(scope):null,scope_role:recognizedScope ? role(scope):null,
      account:read(['[name=from]','[aria-label=From]'],fields) ?? read(['[aria-label^="Google Account:"]','[data-login]','[aria-label="Signed in as"]'],nodes),
      to:read(['[name=to]','[aria-label=To]'],fields),cc:read(['[name=cc]','[aria-label=Cc]'],fields),bcc:read(['[name=bcc]','[aria-label=Bcc]'],fields),
      subject:read(['[name=subjectbox]','[name=subject]'],fields),text:read(['[aria-label="Message Body"]','[aria-label="Type a message"]','[aria-label="Enter a prompt here"]','[name=comment]'],fields),
      chat:read(['header [title]','[aria-label="Chat name"]'],fields),context:read(['[aria-label="Action context"]'],fields),preview:read(['[aria-label="Message preview"]'],fields),
      attachments:fields.filter(node=>node.matches('[aria-label^="Attachment:"]')).map(node=>({label:name(node),text:text(node)})),target:target ? name(target):null};
  }
  guard.reader({document:documentId,id,element:key=>elements.get(key),target:targetFacts,form:(element,submitter)=>formFacts(element.form || (element.tagName==='FORM' ? element:null),submitter || element),report:(step,generation)=>{chrome.runtime.sendMessage({event:'held_step',step,generation}).catch(()=>{});},dispose:()=>{revisionObserver.disconnect();files.clear();elements.clear();traces.length=0;chrome.runtime.onMessage.removeListener(onMessage);}});
  function reloadState(){
    let unsaved=false;
    for(const element of all()){
      if(element.matches('input,textarea,select,[contenteditable]')){
        if(password(element)){unsaved=true;continue;}
        // There is no native defaultValue for rich text. A late reader cannot
        // prove it unchanged, including an editor the owner emptied.
        if(element.isContentEditable){unsaved=true;continue;}
        if(element instanceof HTMLSelectElement)unsaved ||= [...element.options].some(option=>option.selected!==option.defaultSelected);
        else if(['checkbox','radio'].includes(element.type))unsaved ||= element.checked!==element.defaultChecked;
        else unsaved ||= element.value!==element.defaultValue;
      }
    }
    return {unsaved,playing:all().some(element=>['AUDIO','VIDEO'].includes(element.tagName)&&!element.paused&&!element.ended)};
  }
  function onMessage(message, sender, reply) {
    if (sender.id !== chrome.runtime.id || !message || typeof message.command !== 'string') return;
    try {
      let value;
      if (message.command === 'arm') { guard.arm(message); value={armed:true}; }
      else if (message.command === 'finish_input') { guard.finish(message.generation,message.dispatch_nonce).then(()=>reply({ok:true,data:{finished:true}})); return true; }
      else if (message.command === 'resume') { if(message.generation!==controlGeneration)throw Error('stale_reference: control ended'); value=guard.resume(message.hold,message.operation,message.element,message.form); }
      else if (message.command === 'set_control') { controlGeneration=message.generation; value={controlled:true}; }
      else if (['focus','select','check','stage_file','install_file'].includes(message.command) && message.generation !== controlGeneration) throw Error('stale_reference: control ended');
      if (message.command === 'install_file') {
        const staged=files.get(message.token),element=elements.get(message.element);
        if(!staged?.ready || !element?.isConnected || element.type !== 'file')throw Error('stale_reference: upload field or staged bytes changed');
        guard.direct(message.element);
        files.delete(message.token);
        fileIdentities.set(staged.ready,{identity:crypto.randomUUID(),sha256:staged.file.sha256});
        const transfer=new DataTransfer();transfer.items.add(staged.ready);element.files=transfer.files;
        element.dispatchEvent(new Event('input',{bubbles:true}));element.dispatchEvent(new Event('change',{bubbles:true}));
        value={installed:true,sha256:staged.file.sha256,size:staged.file.size};
      }
      else if (message.command === 'stage_file') {
        if(!files.has(message.token)) {
          if(message.offset !== 0 || files.size >= 2)throw Error('refused: upload staging limit');
          const staged={file:message.file,chunks:[],size:0};files.set(message.token,staged);
          setTimeout(()=>{if(files.get(message.token)===staged)files.delete(message.token);},900000);
        }
        const staged=files.get(message.token), bytes=Uint8Array.from(atob(message.bytes),char=>char.charCodeAt(0));
        if(staged.size !== message.offset || staged.size+bytes.length > staged.file.size || staged.size+bytes.length > 25*1024*1024)throw Error('refused: upload offset or size mismatch');
        staged.chunks.push(bytes);staged.size+=bytes.length;
        if(staged.size===staged.file.size)staged.ready=new File(staged.chunks,staged.file.name,{type:'application/octet-stream',lastModified:0});
        value={offset:staged.size};
      }
      else if (message.command === 'clear') { controlGeneration=null; files.clear();value={cleared:true,restored:guard.dispose(),document:documentId}; }
      else if (message.command === 'dispose') {value={disposed:true,restored:guard.dispose(),document:documentId}; }
      else if (['set_control','arm','resume'].includes(message.command)) {}
      else if (message.command === 'hit') value={hit:hit(elements.get(message.element),message.x,message.y)};
      else if(message.command==='observe'){
        const node=elements.get(message.element);
        value={url:location.href,title:document.title,notices:all().filter(element=>element.matches('[role=status],[role=alert],dialog[open],[role=dialog],[role=alertdialog]')).slice(0,5).map(element=>text(element).slice(0,2048)),change:node?.isConnected?{element:id(node),name:name(node),checked:!!node.checked,selected:!!node.selected}: {element_present:false}};
      }
      else if (message.command === 'reload_state') value=reloadState();
      else if (message.command === 'ready') value = {preload:true,document:documentId,...(message.element?{element_present:!!elements.get(message.element)?.isConnected}:{})};
      else if (message.command === 'read' || message.command === 'facts') value = snapshot(message.element);
      else if (message.command === 'steps') { value = guard.steps(); }
      else if (message.command === 'focus') {
        const element = elements.get(message.element);
        if (!element?.isConnected) throw Error('stale_reference: read again');
        if (password(element)) throw Error('owner_signin: password fields belong to the owner');
        element.focus();
        let focused=document.activeElement;
        while(focused && shadow(focused)?.activeElement)focused=shadow(focused).activeElement;
        if(focused !== element)throw Error('refused: this element cannot receive keyboard input; use a focusable control');
        value = {focused:true};
      } else if (message.command === 'select' || message.command === 'check') {
        const element = elements.get(message.element);
        if (!element?.isConnected || password(element)) throw Error('stale_reference: read again');
        guard.direct(message.element);
        if (message.command === 'select') {
          if(!(element instanceof HTMLSelectElement) || element.matches(':disabled'))throw Error('refused: choose an enabled native select control');
          const choices=[...element.options].filter(option=>option.value===message.value);
          if(choices.length!==1 || choices[0].matches(':disabled'))throw Error('stale_reference: the exact enabled option is missing or ambiguous; read again');
          element.value = message.value;
        }
        else element.checked = message.checked;
        element.dispatchEvent(new Event('input', {bubbles:true})); element.dispatchEvent(new Event('change', {bubbles:true}));
        value = {changed:true};
      } else throw Error('permission_denied: unknown content command');
      reply({ok:true, data:value});
    } catch (error) { reply({ok:false, error:String(error.message)}); }
  }
  chrome.runtime.onMessage.addListener(onMessage);
  } catch(error) { console.error('AresOS reader preload',error); chrome.runtime.sendMessage({event:'reader_error',error:String(error.stack || error)}); }
})();
