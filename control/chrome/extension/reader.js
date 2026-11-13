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
  const randomToken=()=>[...crypto.getRandomValues(new Uint8Array(16))].map(value=>value.toString(16).padStart(2,'0')).join('');
  const documentId = privacy.documentId??=randomToken();
  let sequence = 0, revision = 0, controlGeneration = null;
  const traces = [], files = new Map(), watchedRoots = new WeakSet();
  const formGetters=globalThis.HTMLFormElement?Object.fromEntries(['elements','action','method','enctype','target'].map(key=>[key,Object.getOwnPropertyDescriptor(HTMLFormElement.prototype,key)?.get])):{};
  const formProperty=(form,key)=>formGetters[key]?formGetters[key].call(form):form[key];
  const formQuery=(form,selector)=>Element.prototype.querySelector?Element.prototype.querySelector.call(form,selector):form.querySelector(selector);
  const shadow=element=>element instanceof HTMLElement ? chrome.dom.openOrClosedShadowRoot(element):null;
  function composedParent(element) {
    if(element.assignedSlot)return element.assignedSlot;
    // assignedSlot hides a closed root. Its native slots still expose their
    // assigned nodes through the extension's privileged root reference.
    const assignedRoot=shadow(element.parentElement);
    if(assignedRoot)for(const slot of assignedRoot.querySelectorAll('slot'))if(typeof slot.assignedNodes==='function'&&slot.assignedNodes().includes(element))return slot;
    return element.parentElement || element.getRootNode().host;
  }
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
  function text(node, includeHidden=false, composed=false) {
    if(node.nodeType===Node.TEXT_NODE)return node.parentElement&&password(node.parentElement)?'':node.textContent;
    if (!(node instanceof Element) || ['SCRIPT','STYLE','NOSCRIPT','INPUT','TEXTAREA','SELECT'].includes(node.tagName) || password(node)) return '';
    if (!includeHidden && (node.hidden || getComputedStyle(node).display === 'none' || getComputedStyle(node).visibility === 'hidden')) return '';
    if(node.tagName==='IMG')return node.getAttribute('alt')||'';
    const assigned=composed&&node.tagName==='SLOT'?node.assignedNodes?.():null;
    const children=composed?(assigned?.length?assigned:shadow(node)?.childNodes||node.childNodes):node.childNodes;
    return [...children].map(child=>text(child,includeHidden,composed)).join(' ');
  }
  function name(element) {
    const root = element.getRootNode();
    const labelled = (element.getAttribute('aria-labelledby') || '').split(/\s+/).map(key => root.getElementById?.(key)).filter(Boolean);
    const buttonValue=element instanceof HTMLInputElement && ['button','submit','reset'].includes(element.type) ? safeValue(element).value || (element.type==='submit'?'Submit':element.type==='reset'?'Reset':''):null;
    return (labelled.length ? labelled.map(node=>text(node,true)).join(' ') : element.getAttribute('aria-label') ||
      (element.labels?.length ? [...element.labels].map(node=>text(node,true)).join(' ') : element.getAttribute('alt') || buttonValue ||
      ((['BUTTON','A','SUMMARY'].includes(element.tagName) || hyperlink(element) || element.hasAttribute('role') ? text(element) : element.getAttribute('placeholder') || '') || element.getAttribute('title') || ''))).replace(/\s+/g, ' ').trim();
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
  function richIdentity(node){
    if(node.nodeType===Node.TEXT_NODE)return node.parentElement&&password(node.parentElement)?'':node.textContent;
    if(!(node instanceof Element))return null;
    if(password(node))return {element:id(node),password:true};
    if(['SCRIPT','STYLE','NOSCRIPT','INPUT','TEXTAREA','SELECT'].includes(node.tagName))return null;
    const style=getComputedStyle(node);if(node.hidden||style.display==='none'||style.visibility==='hidden')return null;
    return {tag:node.tagName,display:style.display,whiteSpace:style.whiteSpace||'',children:[...node.childNodes].map(richIdentity)};
  }
  const blobSize=globalThis.Blob&&Object.getOwnPropertyDescriptor(Blob.prototype,'size')?.get;
  const blobBytes=globalThis.Blob?.prototype.arrayBuffer;
  function fileIdentity(file){
    if(!blobSize)throw Error('refused: selected file content identity cannot be verified');
    blobSize.call(file);
    if(!fileIdentities.has(file))fileIdentities.set(file,{identity:randomToken()});
    return fileIdentities.get(file);
  }
  const selectedFileLists=()=>all().filter(element=>element instanceof HTMLInputElement&&element.type==='file'&&!password(element)).map(element=>({element,files:[...element.files]}));
  function prepareSelectedFiles(){
    const pending=[],selections=selectedFileLists();
    for(const {files} of selections){
      for(const file of files){
        const identity=fileIdentity(file);
        identity.hashing??=(async()=>{
          const bytes=await blobBytes.call(file);
          const digest=crypto.subtle?Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),byte=>byte.toString(16).padStart(2,'0')).join(''):sha256(new Uint8Array(bytes));
          if(identity.staged&&digest!==identity.staged)throw Error('staged attachment bytes changed');
          identity.sha256=digest;
        })().finally(()=>{identity.hashing=null;});
        pending.push(identity.hashing);
      }
    }
    return {pending,unchanged:()=>{const current=selectedFileLists();return current.length===selections.length&&current.every((entry,index)=>entry.element===selections[index].element&&entry.files.length===selections[index].files.length&&entry.files.every((file,position)=>file===selections[index].files[position]));}};
  }
  // HTTP documents do not expose SubtleCrypto, including their isolated world.
  // SHA-256 here keeps owner-picked files usable there without exporting bytes.
  function sha256(bytes){
    const constants=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
    const hash=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19],words=new Uint32Array(64),rotate=(value,count)=>(value>>>count)|(value<<(32-count));
    const size=Math.ceil((bytes.length+9)/64)*64;
    for(let offset=0;offset<size;offset+=64){
      for(let index=0;index<16;index++){let word=0;for(let part=0;part<4;part++){const position=offset+index*4+part;let byte=position<bytes.length?bytes[position]:position===bytes.length?128:0;if(position>=size-8)byte=Number((BigInt(bytes.length)*8n>>BigInt((size-1-position)*8))&255n);word=(word<<8)|byte;}words[index]=word;}
      for(let index=16;index<64;index++){const x=words[index-15],y=words[index-2];words[index]=(words[index-16]+(rotate(x,7)^rotate(x,18)^(x>>>3))+words[index-7]+(rotate(y,17)^rotate(y,19)^(y>>>10)))>>>0;}
      let[a,b,c,d,e,f,g,h]=hash;
      for(let index=0;index<64;index++){const first=(h+(rotate(e,6)^rotate(e,11)^rotate(e,25))+((e&f)^(~e&g))+constants[index]+words[index])>>>0,second=((rotate(a,2)^rotate(a,13)^rotate(a,22))+((a&b)^(a&c)^(b&c)))>>>0;[a,b,c,d,e,f,g,h]=[(first+second)>>>0,a,b,c,(d+first)>>>0,e,f,g];}
      for(const[index,value]of[a,b,c,d,e,f,g,h].entries())hash[index]=(hash[index]+value)>>>0;
    }
    return hash.map(value=>value.toString(16).padStart(8,'0')).join('');
  }
  function selectedFile(file){
    const identity=fileIdentity(file);
    if(!identity.sha256)throw Error('refused: selected file digest is not ready; read the page again');
    return {name:file.name,size:blobSize.call(file),lastModified:file.lastModified,identity:identity.identity,sha256:identity.sha256};
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
    return {value,...(element.isContentEditable?{rich:richIdentity(element)}:{})};
  }
  function role(element) {
    if (element.getAttribute('role')) return element.getAttribute('role');
    const tag = element.tagName;
    if(hyperlink(element))return 'link';
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
  function mappedImage(area){
    if(area.tagName!=='AREA')return null;
    const map=area.closest('map'),name=map?.getAttribute('name');
    return name?[...document.querySelectorAll('img[usemap]')].find(image=>image.getAttribute('usemap')==='#'+name):null;
  }
  function areaContains(area,x,y){
    const shape=(area.getAttribute('shape')||'rect').toLowerCase(),coords=(area.getAttribute('coords')||'').split(/[ ,]+/).map(Number);
    if(shape==='default')return true;
    if(!coords.every(Number.isFinite))return false;
    if(shape==='rect'&&coords.length===4)return x>=Math.min(coords[0],coords[2])&&x<=Math.max(coords[0],coords[2])&&y>=Math.min(coords[1],coords[3])&&y<=Math.max(coords[1],coords[3]);
    if(shape==='circle'&&coords.length===3)return coords[2]>=0&&(x-coords[0])**2+(y-coords[1])**2<=coords[2]**2;
    if(shape==='poly'&&coords.length>=6&&coords.length%2===0){let inside=false;for(let i=0,j=coords.length-2;i<coords.length;j=i,i+=2)if((coords[i+1]>y)!==(coords[j+1]>y)&&x<(coords[j]-coords[i])*(y-coords[i+1])/(coords[j+1]-coords[i+1])+coords[i])inside=!inside;return inside;}
    return false;
  }
  function targetFacts(element) {
    let box = element.getBoundingClientRect();
    const image=mappedImage(element);
    if(image){
      const bounds=image.getBoundingClientRect(),shape=(element.getAttribute('shape')||'rect').toLowerCase(),coords=(element.getAttribute('coords')||'').split(/[ ,]+/).map(Number);
      let left=0,top=0,right=bounds.width,bottom=bounds.height;
      if(coords.every(Number.isFinite)){
        if(shape==='rect'&&coords.length===4)[left,top,right,bottom]=[Math.min(coords[0],coords[2]),Math.min(coords[1],coords[3]),Math.max(coords[0],coords[2]),Math.max(coords[1],coords[3])];
        else if(shape==='circle'&&coords.length===3)[left,top,right,bottom]=[coords[0]-coords[2],coords[1]-coords[2],coords[0]+coords[2],coords[1]+coords[2]];
        else if(shape==='poly'&&coords.length>=6){const xs=coords.filter((_,i)=>i%2===0),ys=coords.filter((_,i)=>i%2===1);[left,top,right,bottom]=[Math.min(...xs),Math.min(...ys),Math.max(...xs),Math.max(...ys)];}
      }
      left=Math.max(0,left);top=Math.max(0,top);right=Math.min(bounds.width,right);bottom=Math.min(bounds.height,bottom);
      box={x:bounds.x+left,y:bounds.y+top,width:Math.max(0,right-left),height:Math.max(0,bottom-top),top:bounds.y+top,left:bounds.x+left,right:bounds.x+right,bottom:bounds.y+bottom};
    }
    const value = safeValue(element);
    const clickControl=['BUTTON','A','AREA','SUMMARY'].includes(element.tagName) || hyperlink(element) ||
      element instanceof HTMLInputElement && ['button','submit','image','checkbox','radio','range','color','file','reset'].includes(element.type) ||
      (element.getAttribute('role')||'').toLowerCase().split(/\s+/).some(role=>['button','link','menuitem','menuitemcheckbox','menuitemradio','checkbox','radio','switch','option','tab','treeitem'].includes(role));
    const dialog=element.closest('dialog,[role=dialog],[role=alertdialog]');
    const page_dialog=dialog ? {element:id(dialog),kind:role(dialog),text:text(dialog).replace(/\s+/g,' ').trim(),button:name(element),fields:[...dialog.querySelectorAll('input,textarea,select,[contenteditable]')].map(field)} : null;
    return {element: id(element), role: role(element), page_dialog, name: name(element), label:element.labels?.length?[...element.labels].map(node=>text(node,true)).join(' ').replace(/\s+/g,' ').trim():name(element), title: element.getAttribute('title') || '', ...value,
      ...(element instanceof HTMLSelectElement && !value.password ? {options:field(element).options}:{}),
      ...(implicitSubmitter(element) ? {implicit_submitter:id(implicitSubmitter(element))}:{}),
      href: hyperlinkAddress(element),
      editable: !clickControl && (element instanceof HTMLInputElement && !['button','submit','image','checkbox','radio','file','hidden'].includes(element.type) || element instanceof HTMLTextAreaElement || element.isContentEditable),
      search: element.type === 'search' || element.getAttribute('role') === 'searchbox', submit: !!element.form && (element.type === 'submit' || element.type === 'image'),
      states: {checked: !!element.checked, selected: !!element.selected, disabled: !!element.disabled, required: !!element.required, invalid: element.getAttribute('aria-invalid') === 'true', expanded: element.getAttribute('aria-expanded')},
      box: {x:box.x,y:box.y,width:box.width,height:box.height}, onscreen: box.bottom > 0 && box.right > 0 && box.top < innerHeight && box.left < innerWidth && box.width > 0 && box.height > 0};
  }
  function affectedItem(element) {
    const selector='li,tr,article,[role=listitem],[role=row],[role=article],section[aria-label],section[aria-labelledby],form,dialog,[role=dialog],[role=alertdialog],[role=region]';
    // closest() stops at a shadow root; a component can act on its outer row.
    for(let node=element;node;node=composedParent(node)){
      if(node.matches(selector))return node;
    }
    return element;
  }
  function itemText(element) {
    return text(affectedItem(element),false,true).replace(/\s+/g, ' ').trim();
  }
  function hyperlinkAddress(element){
    if(!hyperlink(element))return null;
    const address=element.getAttribute('href')??element.getAttributeNS?.('http://www.w3.org/1999/xlink','href');
    try{return new URL(address,location.href).href;}catch{return address;}
  }
  function hyperlink(element){
    return (['A','AREA'].includes(element.tagName)||element.namespaceURI==='http://www.w3.org/2000/svg'&&element.localName==='a')&&
      (element.hasAttribute('href')||element.hasAttributeNS?.('http://www.w3.org/1999/xlink','href'));
  }
  function renderedCompose(area){
    // innerText/textContent on an ancestor could read protected descendants.
    // Walk the composed tree ourselves, applying whitespace rules per text run.
    let result='',pending='';
    const flush=()=>{if(result&&pending&&!result.endsWith('\n'))result+=pending;pending='';};
    function append(value,space){
      value=value.replace(/\r\n?/g,'\n');
      if(['pre','pre-wrap','break-spaces','preserve'].includes(space)){flush();result+=value;return;}
      for(const part of value.split(/([ \t\n\f]+)/)){
        if(!part)continue;
        if(/^[ \t\n\f]+$/.test(part)){
          if(space==='pre-line'&&part.includes('\n')){if(pending==='\n')flush();pending='';result+='\n'.repeat((part.match(/\n/g)||[]).length);}
          else if(pending!=='\n')pending=' ';
        }else{flush();result+=part;}
      }
    }
    function visit(node,space='normal',visible=true){
      if(node.nodeType===Node.TEXT_NODE){if(visible&&(!node.parentElement||!password(node.parentElement)))append(node.textContent,space);return;}
      if(!(node instanceof Element)||password(node)||['SCRIPT','STYLE','NOSCRIPT','INPUT','SELECT'].includes(node.tagName))return;
      const style=getComputedStyle(node);
      if(node.hidden||style.display==='none')return;
      visible=style.visibility!=='hidden'&&style.visibility!=='collapse';
      if(node.tagName==='BR'){if(visible){if(pending==='\n')flush();pending='';result+='\n';}return;}
      const block=['block','list-item','table-row','flex','grid','table','flow-root'].includes(style.display);
      if(block&&result)pending='\n';
      const whiteSpace=style.whiteSpace|| (node.tagName==='PRE'?'pre':space);
      if(node instanceof HTMLTextAreaElement){if(visible){const safe=safeValue(node);if(!safe.password)append(safe.value,'pre-wrap');}}
      else if(node.tagName==='IMG'){if(visible)append(node.getAttribute('alt')||'',whiteSpace);}
      else{
        const assigned=node.tagName==='SLOT'?node.assignedNodes?.():null;
        for(const child of assigned?.length?assigned:shadow(node)?.childNodes||node.childNodes)visit(child,whiteSpace,visible);
      }
      if(block&&result)pending='\n';
    }
    visit(area);return result;
  }
  function composeText(element,nodes){
    const candidates=nodes.filter(node=>node!==element&&
      (node instanceof HTMLTextAreaElement||node.isContentEditable||node instanceof HTMLInputElement&&!['hidden','button','submit','reset','image','file','checkbox','radio'].includes(node.type))&&
      !password(node)&&!node.hidden&&getComputedStyle(node).display!=='none'&&getComputedStyle(node).visibility!=='hidden');
    // A recipient input beside Send is not the message when a body editor is
    // present farther out (including the generic sibling-editor layout).
    const bodies=candidates.filter(node=>node instanceof HTMLTextAreaElement||node.isContentEditable);
    const drafts=bodies.length?bodies:candidates;
    // The activated editor is itself the draft for Enter. Start at its parent
    // so the neighbouring Send and read-only preview participate as well.
    if(element.isContentEditable||element instanceof HTMLTextAreaElement||element instanceof HTMLInputElement)drafts.push(element);
    const contains=(area,node)=>{for(let parent=node;parent;parent=composedParent(parent))if(parent===area)return true;return false;};
    for(let area=composedParent(element);area;area=composedParent(area)){
      const content=renderedCompose(area);
      if(drafts.some(draft=>contains(area,draft))||!drafts.length&&content!==renderedCompose(element))return {element:id(area),whole_page:['BODY','HTML'].includes(area.tagName),text:content};
    }
    return null;
  }
  function itemFields(element,nodes) {
    const item=affectedItem(element);
    return nodes.filter(node=>{
      if(!(node instanceof HTMLInputElement || node instanceof HTMLTextAreaElement || node instanceof HTMLSelectElement || node.isContentEditable) || ['hidden','button','submit','reset','image'].includes(node.type))return false;
      for(let ancestor=node;ancestor;ancestor=composedParent(ancestor)){
        const style=getComputedStyle(ancestor);
        if(ancestor.hidden || style.display==='none' || style.visibility==='hidden')return false;
        if(ancestor===item)return true;
      }
      return false;
    }).map(field);
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
    const image=mappedImage(element);
    if(image&&actual===image){const box=image.getBoundingClientRect();return [...element.closest('map').querySelectorAll('area')].find(area=>areaContains(area,x-box.x,y-box.y))===element;}
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
      editable, compose:element?composeText(element,nodes):null, selected_files:nodes.filter(node=>node instanceof HTMLInputElement&&node.type==='file').map(field), embeds:nodes.filter(node=>node.tagName==='IFRAME').map(embedding), item: element ? itemText(element) : '', item_fields:element?itemFields(element,nodes):[], adapter: adapterRead(nodes, element), trace: traces.splice(0)};
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
      rich_drafts:fields.filter(node=>node.isContentEditable).map(node=>({element:id(node),...safeValue(node)})),
      attachments:fields.filter(node=>node.matches('[aria-label^="Attachment:"]')).map(node=>({label:name(node),text:text(node)})),target:target ? name(target):null};
  }
  guard.reader({document:documentId,id,clipboard:(route,generation)=>{chrome.runtime.sendMessage({event:'clipboard_write',document:documentId,route,generation}).catch(()=>{});},element:key=>elements.get(key),target:targetFacts,form:(element,submitter)=>formFacts(element.form || (element.tagName==='FORM' ? element:null),submitter || element),report:(step,generation)=>{chrome.runtime.sendMessage({event:'held_step',step,generation}).catch(()=>{});},dialog:(phase,token,generation,nonce,kind)=>{chrome.runtime.sendMessage({event:'native_dialog_boundary',phase,token,generation,nonce,kind,document:documentId}).catch(()=>{});},dispose:()=>{revisionObserver.disconnect();files.clear();elements.clear();traces.length=0;chrome.runtime.onMessage.removeListener(onMessage);}});
  function reloadState(){
    let unsaved=document.designMode?.toLowerCase()==='on';
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
  function onMessage(message, sender, reply, filesReady=false) {
    if (sender.id !== chrome.runtime.id || !message || typeof message.command !== 'string') return;
    try {
      if(message.expected_document&&message.expected_document!==documentId)throw Error('refused: private password history was lost for this surviving document; ask the owner to reload');
      if(message.expected_origin&&message.expected_origin!==globalThis.origin)throw Error('refused: inherited frame origin cannot be authenticated');
      if(!filesReady&&['read','facts','observe'].includes(message.command)){
        const {pending,unchanged}=prepareSelectedFiles();
        if(pending.length){Promise.all(pending).then(()=>{if(!unchanged())throw Error('file selection changed during verification');onMessage(message,sender,reply,true);}).catch(error=>reply({ok:false,error:'refused: selected file could not be hashed: '+String(error.message)}));return true;}
      }
      let value;
      if (message.command === 'arm') { guard.arm(message); value={armed:true}; }
      else if (message.command === 'finish_input') { guard.finish(message.generation,message.dispatch_nonce).then(()=>reply({ok:true,data:{finished:true}})); return true; }
      else if (message.command === 'resume') { if(message.generation!==controlGeneration)throw Error('stale_reference: control ended'); value=guard.resume(message.hold,message.operation,message.element,message.form); }
      else if (message.command === 'set_control') { controlGeneration=message.generation;guard.control?.(message.generation); value={controlled:true}; }
      else if (['focus','select','check','stage_file','install_file'].includes(message.command) && message.generation !== controlGeneration) throw Error('stale_reference: control ended');
      if (message.command === 'install_file') {
        const staged=files.get(message.token),element=elements.get(message.element);
        if(!staged?.ready || !element?.isConnected || element.type !== 'file')throw Error('stale_reference: upload field or staged bytes changed');
        guard.direct(message.element);
        files.delete(message.token);
        const identity={identity:randomToken(),sha256:staged.file.sha256,staged:staged.file.sha256};
        const transfer=new DataTransfer();transfer.items.add(staged.ready);element.files=transfer.files;fileIdentities.set(element.files[0],identity);
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
        const actual=node?.isConnected?safeValue(node):{},observed=typeof actual.value==='string'?{value:actual.value.slice(0,2048),value_more:Math.max(0,actual.value.length-2048)}:Array.isArray(actual.value)?{value:actual.value.slice(0,3),value_more:Math.max(0,actual.value.length-3)}:actual;
        const clipboard=guard.clipboard?.();
        value={url:location.href,title:document.title,...(clipboard?{clipboard}:{}),notices:all().filter(element=>element.matches('[role=status],[role=alert],dialog[open],[role=dialog],[role=alertdialog]')).slice(0,5).map(element=>text(element).slice(0,2048)),change:node?.isConnected?{element:id(node),name:name(node),checked:!!node.checked,selected:!!node.selected,...observed}: {element_present:false}};
        if(clipboard)guard.clipboard(true);
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
  chrome.runtime.sendMessage({event:'reader_ready',document:documentId}).catch(()=>{});
  } catch(error) { console.error('AresOS reader preload',error); chrome.runtime.sendMessage({event:'reader_error',error:String(error.stack || error)}); }
})();
