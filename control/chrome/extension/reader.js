// Isolated world only. Never serialise HTML, attributes or forms in bulk.
(() => {
  'use strict';
  try {
  // DOM wrappers can keep their original realm after native adoption.
  const elementAttribute=Element.prototype.getAttribute;
  const isElement=node=>{try{elementAttribute.call(node,'');return true;}catch{return false;}};
  const html=(node,Constructor,tag=null)=>node instanceof Constructor||isElement(node)&&node.namespaceURI==='http://www.w3.org/1999/xhtml'&&(!tag||node.localName===tag);
  const elements = new Map(), ids = new WeakMap();
  // This passive ISOLATED tracker has document lifetime, including release/retake.
  const privacyKey=Symbol.for('aresos.chrome.passwords.v1');
  const privacy=globalThis[privacyKey]??={protectedFields:new WeakSet(),observed:new WeakSet(),fileIdentities:new WeakMap()};
  const watched=privacy.watched??=globalThis[Symbol.for('aresos.chrome.document-start.v1')]===true;
  const {protectedFields,fileIdentities}=privacy;
  // Shadow roots the reader has met, and the typed fields that already held
  // text at that first meeting (meet, below). Document lifetime, like the rest.
  privacy.metRoots??=new WeakSet();privacy.lateFields??=new WeakSet();
  const protectedKey=Symbol.for('aresos.chrome.password-node.v1');
  const protectNode=node=>{protectedFields.add(node);if(!Object.getOwnPropertyDescriptor(node,protectedKey))Object.defineProperty(node,protectedKey,{value:true});};
  const guard=globalThis[Symbol.for('aresos.chrome.guard.v2')];
  if(guard.ready)return;
  const randomToken=()=>[...crypto.getRandomValues(new Uint8Array(16))].map(value=>value.toString(16).padStart(2,'0')).join('');
  const documentId = privacy.documentId??=randomToken();
  const readerInstance=randomToken();
  let sequence = 0, revision = 0, controlGeneration = null;
  const traces = [], files = new Map(), watchedRoots = new WeakSet(), typedReads = new Set();
  const formGetters=globalThis.HTMLFormElement?Object.fromEntries(['elements','action','method','enctype','target'].map(key=>[key,Object.getOwnPropertyDescriptor(HTMLFormElement.prototype,key)?.get])):{};
  const formProperty=(form,key)=>formGetters[key]?formGetters[key].call(form):form[key];
  const nativeGetter=(Constructor,key)=>Constructor?.prototype&&Object.getOwnPropertyDescriptor(Constructor.prototype,key)?.get;
  const anchorHref=nativeGetter(globalThis.HTMLAnchorElement,'href'),areaHref=nativeGetter(globalThis.HTMLAreaElement,'href');
  const svgHref=nativeGetter(globalThis.SVGAElement,'href'),svgTarget=nativeGetter(globalThis.SVGAElement,'target');
  const animatedValue=nativeGetter(globalThis.SVGAnimatedString,'animVal');
  const svgLink=element=>element.namespaceURI==='http://www.w3.org/2000/svg'&&element.localName==='a';
  const nodeBase=nativeGetter(globalThis.Node,'baseURI');
  const elementHidden=nativeGetter(globalThis.HTMLElement,'hidden');
  const baseURI=node=>nodeBase?nodeBase.call(node):node.baseURI;
  const xlinkNamespace='http://www.w3.org/1999/xlink',elementAttributeNS=Element.prototype.getAttributeNS;
  const documentQueryAll=globalThis.Document?.prototype.querySelectorAll;
  // Chrome reads the base target only from the first HTML <base> that has one;
  // a <base> in SVG or another namespace is an ordinary element to it.
  const htmlBase=node=>isElement(node)&&node.namespaceURI==='http://www.w3.org/1999/xhtml'&&node.localName==='base';
  // While `outline` fingerprints every node (brief 28a, item 2), the base
  // target and each form's implicit submitter are looked up once, not once
  // for each link and field: each lookup walks the whole page.
  let outlineMemo=null;
  function documentBaseTarget(){
    if(outlineMemo&&'base' in outlineMemo)return outlineMemo.base;
    let found=null;
    for(const base of documentQueryAll?documentQueryAll.call(document,'base[target]'):document.querySelectorAll?.('base[target]')||[]){
      const target=htmlBase(base)?elementAttribute.call(base,'target'):null;
      if(target!==null){found=target;break;}
    }
    if(outlineMemo)outlineMemo.base=found;
    return found;
  }
  function browsingTarget(element,attribute,explicit=element.getAttribute(attribute)) {
    if(attribute==='target'&&svgLink(element)){
      // Chrome's SVG link uses its own (animated) target and never the base
      // target; an empty one opens a new window only with xlink:show="new".
      const own=svgTarget&&animatedValue?animatedValue.call(svgTarget.call(element)):explicit||'';
      return own||(elementAttributeNS.call(element,xlinkNamespace,'show')==='new'?'_blank':'_self');
    }
    // Chrome treats an empty target like a missing one, then sanitises the
    // result as HTML does: a tab or newline together with "<" means _blank.
    const target=explicit||documentBaseTarget()||'';
    return /[\t\n\r]/.test(target)&&target.includes('<')?'_blank':target||'_self';
  }
  const formQuery=(form,selector)=>Element.prototype.querySelector?Element.prototype.querySelector.call(form,selector):form.querySelector(selector);
  const shadow=element=>html(element,HTMLElement) ? chrome.dom.openOrClosedShadowRoot(element):null;
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
      if (childShadow) { guard.watch(childShadow); if(meet(childShadow))observe(childShadow); found.push(...roots(childShadow)); }
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
    for(const change of changes)if(change.type==='attributes' && (change.attributeName==='type' && (change.oldValue||'').toLowerCase()==='password' || change.attributeName==='autocomplete' && /(?:password|one-time-code|cc-csc)/i.test(change.oldValue||'') || change.attributeName==='style' && /-webkit-text-security\s*:\s*(?!none\b)/i.test(change.oldValue||'')))protectNode(change.target);
  }
  function ownPassword(element) {
    if(protectedFields.has(element)||Object.getOwnPropertyDescriptor(element,protectedKey)?.value===true)return true;
    if (!(html(element,HTMLInputElement,'input') || html(element,HTMLTextAreaElement,'textarea') || html(element,HTMLSelectElement,'select') || html(element,HTMLButtonElement,'button') || element.isContentEditable)) return false;
    let unsafe = protectedFields.has(element);
    try {
      unsafe ||= credentialLike(element) || element.type === 'password' || /(?:^|\s)(current-password|new-password|one-time-code)(?:\s|$)/i.test(element.getAttribute('autocomplete') || '') ||
        getComputedStyle(element).webkitTextSecurity !== 'none';
    } catch { unsafe = true; }
    if (unsafe) protectNode(element);
    return unsafe;
  }
  // A word heuristic, English and German (KNOWN-LIMITS). Stems match inside
  // longer words; short names must stand alone as a token, so "Distanz",
  // "Tank" or "Spin count" stay ordinary fields. There is no bare "token":
  // hidden CSRF fields are commonly named *_token, and withholding them would
  // make ordinary forms refuse.
  const credentialStems=String.raw`pass[\s_-]*(?:word|wort|code|phrase)|passwd|kennwort|sicherheits[\s_-]*(?:code|antwort)|einmal[\s_-]*(?:code|kennwort|passwort)|best(?:ä|ae)tigungs[\s_-]*code|zugangs[\s_-]*code|one[\s_-]*time[\s_-]*(?:code|password)|security[\s_-]*(?:code|answer)|card[\s_-]*(?:verification|code)|pr(?:ü|ue)f[\s_-]*nummer|kartenpr(?:ü|ue)f|geheim[\s_-]*(?:zahl|nummer|code|wort)|transaktions[\s_-]*nummer|(?:verification|verify|authentication|auth|access|activation|recovery|backup|login|sms)[\s_-]*code|(?:verifizierungs|verifikations|authentifizierungs|authentisierungs|aktivierungs|wiederherstellungs|freigabe|anmelde|sicherungs)[\s_-]*code`;
  const credentialTokens=String.raw`pin(?:[\s_-]?(?:code|nummer|number))?\d*|otp(?:code|pin)?|[th]otp|2fa|mfa|pwd?\d*|passwd\d*|secret|puk\d*|cvc\d*|cvv\d*|csc|cvn|(?:sms|push|chip|photo|foto|app|mobile|m)?[\s_-]?tans?|user[\s_-]*pass|api[\s_-]?keys?|api[\s_-]?schl(?:ü|ue)ssel`;
  const credentialWords=new RegExp(`${credentialStems}|(?:^|[^\\p{L}\\p{N}])(?:${credentialTokens})(?:$|[^\\p{L}\\p{N}])`,'u');
  // Brief 28, item 1 (the name rule): the credential words of the definitions,
  // a copy of control/aresos_control/chrome/credentials.py that
  // test_credentials.py compares with it. Either list makes a field
  // password-kind. This one counts only for a field a person types into, so
  // a hidden *_token field stays an ordinary field and its form is still sent.
  const credentialNames={"version":1,"words":["password","passwort","kennwort","passcode","passphrase","pwd","pin","otp","totp","tan","mtan","2fa","mfa","secret","token","seed","mnemonic","cvv","cvc"],"pairs":{"code":["verification","verify","security","sms","login","auth","recovery","backup","card","einmal","bestätigung","sicherheit"],"key":["private","api","secret","access","recovery","signing"],"phrase":["recovery","seed","secret"]}};
  const foldName=value=>value.toLowerCase().replace(/ä/g,'ae').replace(/ö/g,'oe').replace(/ü/g,'ue').replace(/ß/g,'ss');
  const namedWords=new Set(credentialNames.words.map(foldName));
  const namedPairs=Object.entries(credentialNames.pairs).map(([word,beside])=>[foldName(word),new Set(beside.map(foldName))]);
  // A word counts whole or as a part of a name (user_password, otpCode,
  // PIN2), never inside another word (shipping, pinned). A paired word
  // counts beside a companion: as neighbours in either order, or written as
  // one word, with the s German puts between them (Einmalcode, Sicherheitscode).
  function namesCredential(value){
    const parts=value.normalize('NFKC').replace(/(\p{Ll})(\p{Lu})/gu,'$1 $2').replace(/(\p{Lu})(\p{Lu}\p{Ll})/gu,'$1 $2').split(/[^\p{L}\p{N}]+/u).filter(Boolean)
      .map(part=>{const folded=foldName(part);return folded.replace(/\d+$/,'')||folded;});
    return parts.some((part,index)=>namedWords.has(part)||namedPairs.some(([word,beside])=>{
      if(part===word)return beside.has(parts[index-1])||beside.has(parts[index+1]);
      const before=part.endsWith(word)?part.slice(0,-word.length):null;
      return before!==null&&(beside.has(before)||beside.has(before.replace(/s$/,'')));
    }));
  }
  // A verdict depends on the field's kind and its name strings alone, and a
  // read asks for it many times a field: it is kept until one of them changes.
  const credentialVerdicts=new WeakMap();
  function credentialLike(element) {
    // Text is joined twice: with spaces between nodes for words in separate
    // elements, and without for a word split by markup (P<b>a</b>sswort).
    const labelText=(node,joiner)=>{
      if(node.nodeType===Node.TEXT_NODE)return node.textContent;
      if(!isElement(node)||['INPUT','TEXTAREA','SELECT'].includes(node.tagName)||node.isContentEditable)return '';
      return [...node.childNodes].map(child=>labelText(child,joiner)).join(joiner);
    };
    const signals=['name','id','autocomplete','aria-label','placeholder'].map(key=>element.getAttribute(key)||'');
    const root=element.getRootNode();
    const referenced=(element.getAttribute('aria-labelledby')||'').split(/\s+/).map(key=>root.getElementById?.(key)).filter(Boolean);
    for(const joiner of [' ','']){
      signals.push(referenced.map(node=>labelText(node,joiner)).join(' '));
      signals.push([...element.labels||[]].map(node=>labelText(node,joiner)).join(' '));
    }
    const typed=!!element.isContentEditable||html(element,HTMLTextAreaElement,'textarea')||html(element,HTMLInputElement,'input')&&element.type!=='hidden';
    const key=JSON.stringify([typed,...signals]),known=credentialVerdicts.get(element);
    if(known?.key===key)return known.verdict;
    const verdict=signals.some(value=>credentialWords.test(value.replace(/([a-z])([A-Z])/g,'$1 $2').normalize('NFKC').toLowerCase())||typed&&namesCredential(value));
    credentialVerdicts.set(element,{key,verdict});
    return verdict;
  }
  function password(element) {
    if(observer?.takeRecords)protect(observer.takeRecords());
    if(guard.protectedPeer?.(element))protectNode(element);
    for(let node=element;node;node=node.parentElement||node.getRootNode?.().host){
      if(isElement(node) && ownPassword(node))return true;
    }
    return false;
  }
  // Brief 28, item 1 (the history rule inside a watched document). A shadow
  // root attached to an element that is already in the page causes no change
  // an observer sees, so the owner can type into its field and make it plain
  // before the reader meets the root at all. A typed field that already
  // holds text at that first meeting has no known history, for the life of
  // the document; an empty one is watched from then on. The check looks at
  // whether a field is filled, never at its value. True when the root is new.
  function meet(root){
    if(privacy.metRoots.has(root))return false;
    privacy.metRoots.add(root);
    for(const element of root.querySelectorAll('input,textarea'))if(typedField(element)&&!password(element)&&filledStatus(element)==='filled')privacy.lateFields.add(element);
    return true;
  }
  function remember(root) {
    if(!watchedRoots.has(root)){watchedRoots.add(root);guard.watch(root);}
    for (const element of root.querySelectorAll('input,textarea,[contenteditable]')) password(element);
    for (const element of root.querySelectorAll('*')) {
      const childShadow = shadow(element);
      if (childShadow) { guard.watch(childShadow); meet(childShadow); observe(childShadow); remember(childShadow); }
    }
  }
  const changed = changes => {
    revision++;protect(changes);
    for (const change of changes) {
      if (change.type === 'attributes') {
        if (change.attributeName === 'type' && (change.oldValue||'').toLowerCase() === 'password' || change.attributeName === 'autocomplete' && /(?:password|one-time-code)/i.test(change.oldValue || '')) protectNode(change.target);
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
    if (!(isElement(node)) || ['SCRIPT','STYLE','NOSCRIPT','INPUT','TEXTAREA','SELECT'].includes(node.tagName) || password(node)) return '';
    if (!includeHidden && (node.hidden || getComputedStyle(node).display === 'none' || getComputedStyle(node).visibility === 'hidden')) return '';
    if(node.tagName==='IMG')return node.getAttribute('alt')||'';
    const assigned=composed&&node.tagName==='SLOT'?node.assignedNodes?.():null;
    const children=composed?(assigned?.length?assigned:shadow(node)?.childNodes||node.childNodes):node.childNodes;
    return [...children].map(child=>text(child,includeHidden,composed)).join(' ');
  }
  function name(element, fromContent=['BUTTON','A','SUMMARY'].includes(element.tagName) || hyperlink(element) || element.hasAttribute('role')) {
    const root = element.getRootNode();
    const labelled = (element.getAttribute('aria-labelledby') || '').split(/\s+/).map(key => root.getElementById?.(key)).filter(Boolean);
    const buttonValue=html(element,HTMLInputElement,'input') && ['button','submit','reset'].includes(element.type) ? safeValue(element).value || (element.type==='submit'?'Submit':element.type==='reset'?'Reset':''):null;
    return (labelled.length ? labelled.map(node=>text(node,true)).join(' ') : element.getAttribute('aria-label') ||
      (element.labels?.length ? [...element.labels].map(node=>text(node,true)).join(' ') : element.getAttribute('alt') || buttonValue ||
      ((fromContent ? text(element) : element.getAttribute('placeholder') || '') || element.getAttribute('title') || ''))).replace(/\s+/g, ' ').trim();
  }
  function editableText(node) {
    if(node.nodeType===Node.TEXT_NODE)return node.parentElement&&password(node.parentElement)?'':node.textContent;
    if(!(isElement(node))||password(node)||['SCRIPT','STYLE','NOSCRIPT','INPUT','TEXTAREA','SELECT'].includes(node.tagName))return '';
    const style=getComputedStyle(node);if(node.hidden||style.display==='none'||style.visibility==='hidden')return '';
    if(node.tagName==='BR')return '\n';
    let result='';
    for(const child of node.childNodes){
      const block=isElement(child)&&(['DIV','P','LI','TR','SECTION','ARTICLE','BLOCKQUOTE','PRE'].includes(child.tagName)||['block','list-item','table-row'].includes(getComputedStyle(child).display));
      if(block&&result&&!result.endsWith('\n'))result+='\n';
      result+=editableText(child);
      if(block&&!result.endsWith('\n'))result+='\n';
    }
    return result;
  }
  function richIdentity(node){
    if(node.nodeType===Node.TEXT_NODE)return node.parentElement&&password(node.parentElement)?'':node.textContent;
    if(!(isElement(node)))return null;
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
  const selectedFileLists=()=>all().filter(element=>html(element,HTMLInputElement,'input')&&element.type==='file'&&!password(element)).map(element=>({element,files:[...element.files]}));
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
      // An outline hashes every node. Keep the rounds scalar rather than
      // allocating and unpacking 64 arrays for each block of each node.
      for(let index=0;index<64;index++){
        const first=(h+(rotate(e,6)^rotate(e,11)^rotate(e,25))+((e&f)^(~e&g))+constants[index]+words[index])>>>0,second=((rotate(a,2)^rotate(a,13)^rotate(a,22))+((a&b)^(a&c)^(b&c)))>>>0;
        h=g;g=f;f=e;e=(d+first)>>>0;d=c;c=b;b=a;a=(first+second)>>>0;
      }
      hash[0]=(hash[0]+a)>>>0;hash[1]=(hash[1]+b)>>>0;hash[2]=(hash[2]+c)>>>0;hash[3]=(hash[3]+d)>>>0;
      hash[4]=(hash[4]+e)>>>0;hash[5]=(hash[5]+f)>>>0;hash[6]=(hash[6]+g)>>>0;hash[7]=(hash[7]+h)>>>0;
    }
    return hash.map(value=>value.toString(16).padStart(8,'0')).join('');
  }
  function selectedFile(file){
    const identity=fileIdentity(file);
    if(!identity.sha256)throw Error('refused: selected file digest is not ready; read the page again');
    return {name:file.name,size:blobSize.call(file),lastModified:file.lastModified,identity:identity.identity,sha256:identity.sha256};
  }
  function safeValue(element, traced=true) {
    // The exclusion is repeated immediately before EACH value/text read.
    if (password(element)) return {password: true};
    if(unknownHistory(element)&&typedField(element))return {typed_text:true,unknown_history:true,value_status:filledStatus(element)};
    if(!watched&&html(element,HTMLInputElement,'input')&&element.type==='hidden')return {unknown_history:true,value_status:'not_read'};
    let value;
    if (html(element,HTMLInputElement,'input')) {
      if (element.type === 'file') value = [...element.files].map(selectedFile);
      else value = element.value;
    } else if (html(element,HTMLTextAreaElement,'textarea') || html(element,HTMLSelectElement,'select') || html(element,HTMLButtonElement,'button')) value = element.value;
    else if (element.isContentEditable) value = editableText(element).replace(/\n$/, '');
    else return {};
    // The outline's reply holds what it read; brief 20's trace and rich identity stay with brief 20's reads.
    if(!traced)return {value};
    traces.push({element: id(element), value});
    return {value,...(element.isContentEditable?{rich:richIdentity(element)}:{})};
  }
  // Whether the reader can't know what a typed field held before it looked
  // (brief 28, item 1, the history rule): its value is not read, the asking
  // read may list it, and Claude doesn't type into it.
  const unknownHistory=element=>!watched||privacy.lateFields.has(element);
  function typedField(element) {
    // This shared predicate controls normal reads, approval scope and reload warnings.
    return html(element,HTMLTextAreaElement,'textarea')||html(element,HTMLInputElement,'input')&&!['hidden','password','checkbox','radio','date','datetime-local','month','week','time','range','color','file','button','submit','reset','image'].includes(element.type);
  }
  function filledStatus(element) {
    // Native import copies the live control state without extracting its value.
    // An inert document has no page custom-element registry or event handlers.
    const inert=privacy.emptyProbe??=document.implementation.createHTMLDocument('');
    const copy=inert.importNode(element,false);
    copy.disabled=false;copy.readOnly=false;copy.required=true;
    return element.validity?.badInput||!copy.validity.valueMissing?'filled':'empty';
  }
  function typedFields() {
    // An unnamed field keeps its numbered label for the binding and says it has
    // no name, so the question calls it unnamed and counts it among its kind
    // (brief 28a, item 3b), never as a label the page could also have written.
    return {document:documentId,reader:readerInstance,fields:all().filter(element=>typedField(element)&&!password(element)&&unknownHistory(element)).map((element,index)=>{
      const label=name(element);
      return {element:id(element),label:label||(html(element,HTMLTextAreaElement,'textarea')?'textarea ':'single-line field ')+(index+1),type:element.type,...(label?{}:{unnamed:true})};
    })};
  }
  function readTypedFields(message) {
    if(message.approved!==true||!message.operation||typedReads.has(message.operation))throw Error('refused: typed fields require a fresh one-call approval');
    typedReads.add(message.operation);
    const current=typedFields(),expected=message.expected;
    if(expected?.document!==documentId||expected.reader!==readerInstance||expected.fields.length!==current.fields.length||current.fields.some((field,index)=>['element','label','type'].some(key=>field[key]!==expected.fields[index][key])))throw Error('stale_approval: typed field list changed; ask again');
    return {document:documentId,reader:readerInstance,fields:current.fields.map(field=>{
      const element=elements.get(field.element);
      if(password(element)||!typedField(element))throw Error('stale_approval: typed field became a credential; ask again');
      return {...field,value:element.value};
    })};
  }
  // Brief 28, item 1: the outline. A node holds its own text and facts, never
  // its descendants' text, a box or a style. Everything a page wrote leaves as
  // a string value; a role leaves only as a word of this list (nodes.py ROLES).
  const outlineRoles=new Set('main navigation banner contentinfo complementary region search form article group list listitem table row cell columnheader rowheader figure img separator toolbar dialog alertdialog alert status tooltip progressbar frame h1 h2 h3 h4 h5 h6 p text link button textbox searchbox combobox listbox option checkbox radio radiogroup switch slider spinbutton tab tablist tabpanel menu menubar menuitem menuitemcheckbox menuitemradio tree treeitem grid gridcell password'.split(' '));
  // Roles the reader gives by its own rules; a role attribute can't claim them.
  // A page's role="password" on a container would make the service refuse the
  // whole reply (a field that isn't read has no children).
  const readerRoles=new Set(['password','frame','text','p','h1','h2','h3','h4','h5','h6']);
  const tagRoles=new Map(Object.entries({main:'main',nav:'navigation',aside:'complementary',form:'form',article:'article',fieldset:'group',details:'group',ul:'list',ol:'list',dl:'list',menu:'list',li:'listitem',dt:'listitem',dd:'listitem',table:'table',tr:'row',td:'cell',figure:'figure',hr:'separator',dialog:'dialog',iframe:'frame',h1:'h1',h2:'h2',h3:'h3',h4:'h4',h5:'h5',h6:'h6',p:'p',blockquote:'p',pre:'p',button:'button',summary:'button',textarea:'textbox',option:'option',progress:'progressbar',meter:'progressbar'}));
  const inputRoles=new Map(Object.entries({checkbox:'checkbox',radio:'radio',range:'slider',number:'spinbutton',search:'searchbox',button:'button',submit:'button',reset:'button',image:'button'}));
  // Inline formatting is text of the element it stands in (brief 28, section 7, decision 6).
  const formattingTags=new Set('a b strong i em code span small mark abbr sub sup time u s q cite kbd var samp dfn del ins bdi bdo font big tt data ruby rt rp'.split(' '));
  const unreadTags=new Set(['script','style','noscript','template','head','title']);
  const contentNamed=new Set(['link','button','checkbox','radio','switch','tab','menuitem','menuitemcheckbox','menuitemradio','option','treeitem']);
  const XHTML='http://www.w3.org/1999/xhtml',NODE_LIMIT=20000,OPTION_LIMIT=50;
  const squeeze=value=>String(value??'').replace(/\s+/g,' ').trim();
  // The reader's element id as a number (decision 4): e12 is 12.
  const number=element=>Number(id(element).slice(1));
  function outlineRole(element,tag){
    const word=(element.getAttribute('role')||'').trim().split(/\s+/)[0].toLowerCase();
    if(word==='heading'){const level=Number(element.getAttribute('aria-level')||2);return Number.isInteger(level)&&level>=1&&level<=6?'h'+level:'h2';}
    if(outlineRoles.has(word)&&!readerRoles.has(word))return word;
    if(hyperlink(element))return 'link';
    if(element.namespaceURI!==XHTML)return null;
    if(tag==='input')return element.type==='hidden'?null:inputRoles.get(element.type)||'textbox';
    if(tag==='select')return element.multiple||element.size>1?'listbox':'combobox';
    // Native controls still take the value/withholding path under presentation roles.
    if(tag==='textarea')return 'textbox';
    if(tag==='button')return 'button';
    if(element.isContentEditable)return 'textbox';
    if(word==='presentation'||word==='none')return null;
    if(tag==='header'||tag==='footer')return element.parentElement?.localName==='body'?(tag==='header'?'banner':'contentinfo'):null;
    if(tag==='section')return element.hasAttribute('aria-label')||element.hasAttribute('aria-labelledby')?'region':null;
    if(tag==='th')return (element.getAttribute('scope')||'').toLowerCase()==='row'?'rowheader':'columnheader';
    if(tag==='img')return element.getAttribute('alt')?'img':null;
    return tagRoles.get(tag)||null;
  }
  function outlineStates(element,tag){
    const aria=key=>element.getAttribute('aria-'+key),states=[];
    const control=['input','textarea','select','button'].includes(tag);
    if(tag==='input'&&['checkbox','radio'].includes(element.type)?element.checked===true:aria('checked')==='true')states.push('checked');
    if(aria('selected')==='true')states.push('selected');
    if(control&&element.matches(':disabled')||aria('disabled')==='true')states.push('disabled');
    if(control&&element.required===true||aria('required')==='true')states.push('required');
    if(aria('invalid')==='true')states.push('invalid');
    const expanded=tag==='details'?String(element.open===true):aria('expanded');
    if(expanded==='true')states.push('expanded');else if(expanded==='false')states.push('collapsed');
    if(aria('current')&&aria('current')!=='false')states.push('current');
    if((tag==='input'||tag==='textarea')&&element.readOnly===true||aria('readonly')==='true')states.push('readonly');
    return states;
  }
  // The elements that hold a field's error text (shown with the field while it is invalid).
  const errorParts=element=>{const root=element.getRootNode();return (element.getAttribute('aria-errormessage')||element.getAttribute('aria-describedby')||'').split(/\s+/).map(key=>key&&root.getElementById?.(key)).filter(Boolean);};
  const optionFacts=option=>({label:squeeze(text(option)),value:String(option.value??''),chosen:option.selected===true,disabled:!!option.matches(':disabled')});
  const composedChildren=node=>{const assigned=node.localName==='slot'?node.assignedNodes?.():null;return assigned?.length?assigned:shadow(node)?.childNodes||node.childNodes;};
  // Fills a node's own facts. True when the element's content is its value or
  // nothing the outline reads, so its children get no nodes.
  function describe(node,tag,role,out){
    const label=name(node,contentNamed.has(role));if(label)out.name=label;
    const title=squeeze(node.getAttribute('title'));if(title&&title!==label)out.title=title;
    const states=outlineStates(node,tag);if(states.length)out.states=states;
    if(node.getAttribute('aria-invalid')==='true'){const error=squeeze(errorParts(node).map(part=>text(part,true)).join(' '));if(error)out.error=error;}
    if(role==='link'){const href=hyperlinkAddress(node);if(typeof href==='string')out.href=href;}
    if(node.namespaceURI!==XHTML)return false;
    if(tag==='form'){
      out.method=String(formProperty(node,'method')||'get').toLowerCase();out.action=String(formProperty(node,'action')||'');
      const hidden=[...formProperty(node,'elements')].filter(control=>html(control,HTMLInputElement,'input')&&control.type==='hidden').map(control=>control.getAttribute('name')||'').filter(Boolean);
      if(hidden.length)out.hidden=hidden;
      return false;
    }
    if(tag==='iframe'){const frame=chrome.runtime.getFrameId?.(node);if(Number.isInteger(frame)&&frame>0)out.frame=frame;return true;}
    if(tag==='select'){
      const options=[...node.options];
      out.option_count=options.length;out.chosen=options.filter(option=>option.selected).map(option=>squeeze(text(option))).join(', ');
      out.options=options.slice(0,OPTION_LIMIT).map(optionFacts);
      return true;
    }
    const input=tag==='input';
    if(input&&node.type==='file'){out.value=[...node.files].map(file=>String(file.name)).join(', ');return true;}
    if(input&&!['checkbox','radio','button','submit','reset','image'].includes(node.type)||tag==='textarea'||node.isContentEditable){
      // safeValue repeats the exclusion right before the read (the password
      // rule, the history rule); an unread field carries filled or empty only.
      const safe=safeValue(node,false);
      if(safe.password||safe.unknown_history){out.unread=true;if(['filled','empty'].includes(safe.value_status))out.filled=safe.value_status==='filled';}
      else if(typeof safe.value==='string')out.value=safe.value;
      return true;
    }
    return input||tag==='img'||tag==='progress'||tag==='meter';
  }
  // Brief 28a, items 0 and 2: page text as the native wire repairs it (lone
  // surrogates become U+FFFD, valid pairs stay), for the fingerprint's hash only.
  const wellFormed=value=>typeof value.toWellFormed==='function'?value.toWellFormed():Array.from(value,c=>c.length===1&&c.charCodeAt(0)>=0xd800&&c.charCodeAt(0)<=0xdfff?'\ufffd':c).join('');
  // Brief 28a, item 2: what an element means, for the check before an action.
  // `outline` (every node), `facts` (the target) and `observe` (the element
  // acted on) all take it from here, so the read and the check can't drift
  // apart. It is taken from the element, not from a line: a name or value a
  // line cut, and a link's whole address, count whole. Left out on purpose:
  // where the element sits (its box, on screen or not) and the states
  // disabled, required and invalid. A password-kind field means only that it
  // is one, and an unread field only that it is unread: nothing the password
  // rule keeps out is read for it.
  function meaning(element){
    if(password(element))return ['password'];
    const tag=element.localName,kind=outlineRole(element,tag),aria=key=>element.getAttribute('aria-'+key),native=element.namespaceURI===XHTML;
    const dialog=element.closest('dialog,[role=dialog],[role=alertdialog]');
    let value=null;
    if(html(element,HTMLInputElement,'input')&&element.type==='file')value=['files',[...element.files].map(file=>String(file.name))];
    else{const safe=safeValue(element,false);if(safe.password)value=['password'];else if(safe.unknown_history)value=['unread'];else if('value' in safe)value=['value',safe.value];}
    return [kind,name(element,contentNamed.has(kind)),element.labels?.length?squeeze([...element.labels].map(node=>text(node,true)).join(' ')):'',element.getAttribute('title')||'',
      hyperlinkAddress(element),hyperlink(element)?browsingTarget(element,'target'):null,submitsForm(element),!!implicitSubmitter(element),editableTarget(element),searchTarget(element),
      dialog?[id(dialog),role(dialog)]:null,
      native&&tag==='input'&&['checkbox','radio'].includes(element.type)?element.checked===true:aria('checked'),
      native&&tag==='option'?element.selected===true:aria('selected'),
      native&&tag==='details'?element.open===true:aria('expanded'),
      html(element,HTMLSelectElement,'select')?[...element.options].map(option=>{const facts=optionFacts(option);return [facts.label,facts.value,facts.chosen];}):null,
      value];
  }
  // Its short digest: 128 bits of SHA-256 over the repaired JSON of `meaning`.
  // The service only stores and compares these.
  let fingerprintEncoder;
  function fingerprint(element){
    const text=JSON.stringify(meaning(element),(key,value)=>typeof value==='string'?wellFormed(value):value);
    // Sibling containers often have identical meanings. Read every element
    // freshly, but hash each distinct byte string only once in this outline.
    const known=outlineMemo?.digests.get(text);
    if(known!==undefined)return known;
    const digest=sha256((fingerprintEncoder??=new TextEncoder()).encode(text)).slice(0,32);
    outlineMemo?.digests.set(text,digest);
    return digest;
  }
  function outline(budget){
    // The background passes what is left of the tab's nodes; a frame never gets more than the limit.
    const limit=Number.isInteger(budget)&&budget>=0?Math.min(budget,NODE_LIMIT):NODE_LIMIT;
    const mark=traces.length;
    outlineMemo={forms:new Map(),digests:new Map()};
    try{
      let modal=null;const errors=new Set();
      for(const element of all()){
        if(!modal&&element.matches('dialog[open],[role=dialog][aria-modal=true],[role=alertdialog][aria-modal=true]'))modal=element;
        if(element.getAttribute('aria-invalid')==='true')for(const part of errorParts(element))errors.add(part);
      }
      const flush=owner=>{if(owner.run){owner.parts.push(owner.pre?owner.run.replace(/\r\n?/g,'\n'):owner.run.replace(/\s+/g,' '));owner.run='';}};
      function visit(node,owner){
        if(node.nodeType===Node.TEXT_NODE){owner.run+=node.textContent;return;}
        if(!isElement(node))return;
        const tag=node.localName;
        if(unreadTags.has(tag)||errors.has(node))return;
        // The exclusion comes before anything of the element is read.
        const kept=password(node);
        const style=getComputedStyle(node);
        // A form's named controls can shadow hidden with an element. Read the
        // native state so a control called "hidden" cannot hide its form.
        if(html(node,HTMLElement)&&(elementHidden?elementHidden.call(node):node.hidden)||style.visibility==='hidden')return;
        if(tag==='area'&&hyperlink(node)){
          // Chrome gives the area no layout box. Its hit region belongs to the image.
          const image=mappedImage(node);
          if(!image||image.hidden||getComputedStyle(image).visibility!=='visible')return;
          const {width,height}=elementBox(node,image);
          if(!width||!height)return;
        }else if(style.display==='none')return;
        if(kept){flush(owner);const label=name(node,false);owner.parts.push({element:node,out:{role:'password',...(label?{name:label}:{}),unread:true},parts:[]});return;}
        if(tag==='br'){owner.run+=owner.pre?'\n':' ';return;}
        const role=outlineRole(node,tag);
        if(role===null&&(node.namespaceURI!==XHTML||formattingTags.has(tag))){for(const child of composedChildren(node))visit(child,owner);return;}
        flush(owner);
        const record={element:node,out:{role},parts:[],run:'',pre:tag==='pre'||/^(?:pre|break-spaces)/.test(style.whiteSpace||'')};
        // A textarea's default text is never generic page text, whatever its role.
        if((role===null||!describe(node,tag,role,record.out))&&tag!=='textarea')for(const child of composedChildren(node))visit(child,record);
        flush(record);
        // No role and no text of its own: no node, and its children move up.
        if(role===null&&!record.parts.some(part=>typeof part==='string'&&part.trim()))owner.parts.push(...record.parts.filter(part=>typeof part!=='string'));
        else{if(role===null)record.out.role='text';owner.parts.push(record);}
      }
      const top={parts:[],run:'',pre:false};
      visit(modal||document.body||document.documentElement,top);
      const nodes=[];let omitted=0;
      const lost=record=>{omitted++;for(const part of record.parts)if(typeof part!=='string')lost(part);};
      // Document order: a parent stands before its children.
      function emit(record,parent){
        if(nodes.length>=limit){lost(record);return false;}
        const out={id:number(record.element),parent,...record.out,fingerprint:fingerprint(record.element)};nodes.push(out);
        const parts=[];
        for(const part of record.parts){
          if(typeof part==='string')parts.push(part);
          else{const child=nodes.length;if(emit(part,out.id))parts.push(nodes[child].id);}
        }
        if(typeof parts[0]==='string')parts[0]=parts[0].trimStart();
        if(typeof parts.at(-1)==='string')parts[parts.length-1]=parts.at(-1).trimEnd();
        const own=parts.filter(part=>part!=='');
        if(own.some(part=>typeof part==='string'&&part.trim()))out.text=own;
        return true;
      }
      for(const part of top.parts)if(typeof part!=='string')emit(part,null);
      return {document:documentId,reader:readerInstance,watched,origin:globalThis.origin,url:location.href,title:document.title,
        scroll:Math.max(0,Math.round(scrollY)||0),height:Math.max(0,Math.round(document.documentElement?.scrollHeight)||0),omitted,nodes};
    }finally{traces.length=mark;outlineMemo=null;}
  }
  // Every option of one list field, for a read of that field by its reference.
  // A number names an element only for the reader instance that gave it: a
  // new instance in the same document counts from one again.
  function fieldOptions(message){
    if(message.document!==documentId||message.reader!==readerInstance)throw Error('stale_reference: the document or its reader is new; read again');
    const key=message.element,element=Number.isInteger(key)&&key>0?elements.get('e'+key):null;
    if(!element?.isConnected||!html(element,HTMLSelectElement,'select')||password(element))throw Error('stale_reference: the list field is gone or is not read; read again');
    return [...element.options].map(optionFacts);
  }
  // The reader's part of page_state: what moves whenever a read of this
  // document could return something else. Values are digested here; a field
  // that isn't read adds only what the outline shows of it.
  function pageState(){
    const digest=value=>sha256(new TextEncoder().encode(value)),fields=[];
    for(const element of all()){
      const tag=element.localName;
      if(element.namespaceURI!==XHTML||!['input','textarea','select'].includes(tag))continue;
      let state;
      if(password(element))state='p';
      else if(tag==='select')state='s'+[...element.options].map(option=>option.selected?1:0).join('');
      else if(['checkbox','radio'].includes(element.type))state=element.checked?'c1':'c0';
      else if(element.type==='file')state='f'+JSON.stringify([...element.files].map(file=>String(file.name)));
      else{const safe=safeValue(element,false);state=typeof safe.value==='string'?'v'+safe.value:'u'+(safe.value_status||'');}
      fields.push(state.length+':'+state);
    }
    return {document:documentId,reader:readerInstance,origin:globalThis.origin,revision,address:digest(location.href),fields:digest(fields.join('')),ready:document.readyState==='complete'};
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
      ...(html(element,HTMLSelectElement,'select') && !safe.password ? {options: [...element.options].map(option => ({label: text(option), value: option.value, selected: option.selected, disabled: option.matches(':disabled')}))} : {})};
  }
  function formFacts(form, submitter) {
    if (!form) return null;
    const button=submitter?.form===form&&['submit','image'].includes(submitter.type)?submitter:null;
    return {element: id(form), action: button?.hasAttribute('formaction') ? button.formAction : formProperty(form,'action'),
      method: (button?.hasAttribute('formmethod') ? button.formMethod : formProperty(form,'method')).toLowerCase(),
      encoding: button?.hasAttribute('formenctype') ? button.formEnctype : formProperty(form,'enctype'),
      target: button?.hasAttribute('formtarget') ? button.formTarget : formProperty(form,'target'),
      browsing_target: button?.hasAttribute('formtarget') ? browsingTarget(button,'formtarget') : browsingTarget(form,'target',formProperty(form,'target')),
      search: form.role === 'search' || !!formQuery(form,'input[type=search]'),
      fields: [...formProperty(form,'elements')].map(field)};
  }
  function implicitSubmitter(element) {
    if(!(html(element,HTMLInputElement,'input')) || !element.form || ['button','submit','image','checkbox','radio','file','hidden','range','color'].includes(element.type))return null;
    const root=element.getRootNode(),forms=outlineMemo?.forms.get(root);
    if(forms?.has(element.form))return forms.get(element.form);
    const found=[...root.querySelectorAll('button,input')].find(control=>control.form===element.form&&['submit','image'].includes(control.type)) || null;
    if(outlineMemo){if(!forms)outlineMemo.forms.set(root,new Map());outlineMemo.forms.get(root).set(element.form,found);}
    return found;
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
  // Where an element is on the screen; an image map's area lies inside its image.
  function elementBox(element,image=mappedImage(element)) {
    let box = element.getBoundingClientRect();
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
    return box;
  }
  // Brief 20's three kinds of a target, for its facts and its fingerprint alike.
  function clickControl(element) {
    return ['BUTTON','A','AREA','SUMMARY'].includes(element.tagName) || hyperlink(element) ||
      html(element,HTMLInputElement,'input') && ['button','submit','image','checkbox','radio','range','color','file','reset'].includes(element.type) ||
      (element.getAttribute('role')||'').toLowerCase().split(/\s+/).some(role=>['button','link','menuitem','menuitemcheckbox','menuitemradio','checkbox','radio','switch','option','tab','treeitem'].includes(role));
  }
  const editableTarget=element=>!clickControl(element) && (html(element,HTMLInputElement,'input') && !['button','submit','image','checkbox','radio','file','hidden'].includes(element.type) || html(element,HTMLTextAreaElement,'textarea') || element.isContentEditable);
  const searchTarget=element=>element.type === 'search' || element.getAttribute('role') === 'searchbox';
  const submitsForm=element=>!!element.form && (element.type === 'submit' || element.type === 'image');
  function targetFacts(element) {
    const box = elementBox(element);
    const value = safeValue(element);
    const dialog=element.closest('dialog,[role=dialog],[role=alertdialog]');
    const page_dialog=dialog ? {element:id(dialog),kind:role(dialog),text:text(dialog).replace(/\s+/g,' ').trim(),button:name(element),fields:[...dialog.querySelectorAll('input,textarea,select,[contenteditable]')].map(field)} : null;
    return {element: id(element), role: role(element), page_dialog, name: name(element), label:element.labels?.length?[...element.labels].map(node=>text(node,true)).join(' ').replace(/\s+/g,' ').trim():name(element), title: element.getAttribute('title') || '', ...value,
      ...(html(element,HTMLSelectElement,'select') && !value.password ? {options:field(element).options}:{}),
      ...(implicitSubmitter(element) ? {implicit_submitter:id(implicitSubmitter(element))}:{}),
      href: hyperlinkAddress(element),
      ...(hyperlink(element)?{browsing_target:browsingTarget(element,'target')}:{}),
      editable: editableTarget(element),
      search: searchTarget(element), submit: submitsForm(element),
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
    if(element.tagName==='A'&&anchorHref)return anchorHref.call(element);
    if(element.tagName==='AREA'&&areaHref)return areaHref.call(element);
    const address=svgHref&&animatedValue?animatedValue.call(svgHref.call(element)):element.getAttribute('href')??element.getAttributeNS?.('http://www.w3.org/1999/xlink','href');
    try{return new URL(address,baseURI(element)).href;}catch{return address;}
  }
  function hyperlink(element){
    return (['A','AREA'].includes(element.tagName)||svgLink(element))&&
      (element.hasAttribute('href')||element.hasAttributeNS?.('http://www.w3.org/1999/xlink','href')||svgLink(element)&&svgHref&&animatedValue&&animatedValue.call(svgHref.call(element))!=='');
  }
  function renderedCompose(area){
    // innerText/textContent on an ancestor could read protected descendants.
    // Walk the composed tree ourselves, applying whitespace rules per text run.
    let result='',pending='';
    const flush=()=>{if(result&&pending&&(pending==='\n'||!result.endsWith('\n')))result+=pending;pending='';};
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
      if(!(isElement(node))||password(node)||['SCRIPT','STYLE','NOSCRIPT','INPUT','SELECT'].includes(node.tagName))return;
      const style=getComputedStyle(node);
      if(style.display==='none')return;
      visible=style.visibility!=='hidden'&&style.visibility!=='collapse';
      if(node.tagName==='BR'){if(visible){if(pending==='\n')flush();pending='';result+='\n';}return;}
      const block=['block','list-item','table-row','flex','grid','table','flow-root'].includes(style.display);
      if(block&&result)pending='\n';
      const whiteSpace=style.whiteSpace|| (node.tagName==='PRE'?'pre':space);
      if(html(node,HTMLTextAreaElement,'textarea')){if(visible){const safe=safeValue(node);if(!safe.password&&typeof safe.value==='string')append(safe.value,'pre-wrap');}}
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
      (html(node,HTMLTextAreaElement,'textarea')||node.isContentEditable||html(node,HTMLInputElement,'input')&&!['hidden','button','submit','reset','image','file','checkbox','radio'].includes(node.type))&&
      !password(node)&&getComputedStyle(node).display!=='none'&&getComputedStyle(node).visibility!=='hidden');
    // A recipient input beside Send is not the message when a body editor is
    // present farther out (including the generic sibling-editor layout).
    const bodies=candidates.filter(node=>html(node,HTMLTextAreaElement,'textarea')||node.isContentEditable);
    const drafts=bodies.length?bodies:candidates;
    // The activated editor is itself the draft for Enter. Start at its parent
    // so the neighbouring Send and read-only preview participate as well.
    if(element.isContentEditable||html(element,HTMLTextAreaElement,'textarea')||html(element,HTMLInputElement,'input'))drafts.push(element);
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
      if(!(html(node,HTMLInputElement,'input') || html(node,HTMLTextAreaElement,'textarea') || html(node,HTMLSelectElement,'select') || node.isContentEditable) || ['hidden','button','submit','reset','image'].includes(node.type))return false;
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
      // Native controls already went through safeValue; their child text is not a fallback name.
      if (facts.role === 'generic' && !node.isContentEditable && !['INPUT','TEXTAREA','SELECT','BUTTON'].includes(node.tagName)) {
        if(password(node))return null;
        const own=[...node.childNodes].filter(child=>child.nodeType===Node.TEXT_NODE).map(child=>child.textContent).join(' ').replace(/\s+/g,' ').trim();
        if(!own || password(node) || node.hidden || getComputedStyle(node).display==='none' || getComputedStyle(node).visibility==='hidden')return null;
        facts.role='text';facts.name=own;
      }
      if (facts.role === 'hidden' || !facts.box.width || !facts.box.height) return null;
      return {...facts, text: ['textbox','combobox','button','link','iframe'].includes(facts.role) ? '' : text(node).replace(/\s+/g, ' ').trim()};
    }).filter(Boolean);
    const editable = nodes.filter(node => node.matches('input,textarea,select,[contenteditable]') && !['hidden','button','submit','reset','image','file'].includes(node.type)).map(field);
    // Brief 28a, item 2: `facts` also says which reader instance numbered the
    // element, and gives the target's fingerprint beside its facts.
    return {document: documentId, reader: readerInstance, revision, url: location.href, origin:globalThis.origin, title: document.title, scroll: {x:scrollX,y:scrollY}, rows,
      target: element ? targetFacts(element) : null, ...(element ? {fingerprint: fingerprint(element)} : {}), form: element ? formFacts(element.form || (element.tagName === 'FORM' ? element : null), implicitSubmitter(element) || element) : null,
      editable, typed_fields:typedFields(), compose:element?composeText(element,nodes):null, selected_files:nodes.filter(node=>html(node,HTMLInputElement,'input')&&node.type==='file').map(field), embeds:nodes.filter(node=>node.tagName==='IFRAME').map(embedding), item: element ? itemText(element) : '', item_fields:element?itemFields(element,nodes):[], adapter: adapterRead(nodes, element), trace: traces.splice(0)};
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
  guard.reader({protected:node=>protectedFields.has(node),protectPeers:()=>remember(document),document:documentId,id,clipboard:(route,generation)=>{chrome.runtime.sendMessage({event:'clipboard_write',document:documentId,route,generation}).catch(()=>{});},element:key=>elements.get(key),target:targetFacts,form:(element,submitter)=>formFacts(element.form || (element.tagName==='FORM' ? element:null),submitter || element),report:(step,generation)=>{chrome.runtime.sendMessage({event:'held_step',step,generation}).catch(()=>{});},dialog:(phase,token,generation,nonce,kind)=>{chrome.runtime.sendMessage({event:'native_dialog_boundary',phase,token,generation,nonce,kind,document:documentId}).catch(()=>{});},dispose:()=>{revisionObserver.disconnect();files.clear();elements.clear();traces.length=0;chrome.runtime.onMessage.removeListener(onMessage);}});
  // The unsaved-typing report names a field by its label, never by anything it
  // holds: no value, no editor text, no labelling node that is or holds an
  // editor. Each label is quoted and capped, so one can't pass for several.
  function unsavedLabel(element){
    const editor=node=>node.isContentEditable||!!node.querySelector?.('[contenteditable]');
    const root=element.getRootNode();
    const from=nodes=>nodes.length&&!nodes.some(editor)?nodes.map(node=>text(node,true)).join(' '):'';
    const labelled=(element.getAttribute('aria-labelledby')||'').split(/\s+/).map(key=>root.getElementById?.(key)).filter(Boolean);
    // name()'s order: aria-labelledby, aria-label, <label>, then hints.
    const label=from(labelled)||element.getAttribute('aria-label')||from([...(element.labels||[])])||
      element.getAttribute('placeholder')||element.getAttribute('aria-placeholder')||element.getAttribute('title')||'';
    const kind=element.isContentEditable?'editor':html(element,HTMLTextAreaElement,'textarea')?'text area':html(element,HTMLSelectElement,'select')?'list':
      password(element)?'password field':{hidden:'hidden field',checkbox:'checkbox',radio:'radio button'}[element.type]||'field';
    const clean=label.replace(/\s+/g,' ').trim();
    return clean?kind+' "'+clean.slice(0,80).replace(/"/g,"'")+(clean.length>80?'…':'')+'"':'an unlabelled '+kind;
  }
  // Who typed (guard.js): only typing the guard saw Claude do, and nobody
  // else, is Claude's, and only while that is certain. A mark made before the
  // latest release isn't: the owner may have edited the field while no guard
  // listened. Nor is one from a dispatch whose finish hasn't come: the
  // owner's keystrokes in that field got Claude's mark too. Anything else,
  // including a change no one typed, counts as the owner's, so Claude asks him.
  const typist=node=>{const marks=guard.typedBy?.(node);return marks?.claude&&!marks.owner&&marks.release===guard.typingReleases&&guard.typingUnconfirmed?.(node)===false?'Claude':'the owner';};
  function reloadState(){
    const fields=[];let claudeOnly=true;
    // Each field as data, never as one text (brief 28a, item 5b): its
    // description is page text and travels apart from whose typing it is.
    const add=(label,node)=>{const by=typist(node);if(by!=='Claude')claudeOnly=false;fields.push({description:label,by:by==='Claude'?'claude':'owner'});};
    // The guard has listened since before page scripts in a watched document,
    // unless a release left a gap; only then is "no input since load" known.
    // After that gap (a release and a retake of the same document without a
    // reload) typing went unseen, so what the fields hold now counts.
    const sinceLoad=watched&&guard.typingGap===false;
    const retaken=guard.typingGap===true;
    const gotInput=node=>!!guard.typedBy?.(node);
    // A rich-text frame (design mode) counts once it got input since load.
    if(document.designMode?.toLowerCase()==='on'&&(!sinceLoad||gotInput(document)))add('the whole page in design mode',document);
    for(const element of all()){
      if(element.matches('input,textarea,select,[contenteditable]')){
        let changed;
        if(password(element))changed=true;
        else if(!watched&&(typedField(element)||html(element,HTMLInputElement,'input')&&element.type==='hidden'))changed=true;
        // Rich text has no native default. An editor counts only once it got
        // input since load (an untouched one holds nothing of anyone's). Where
        // that isn't known, a late reader or a gap, every editor still counts,
        // including one the owner emptied. An editor inside another is part of
        // it and named once.
        else if(element.isContentEditable){if(element.parentElement?.isContentEditable)continue;changed=!sinceLoad||gotInput(element);}
        // A list is changed when it differs from HTML's reset state: the
        // options marked selected (the last of them for a single choice), or,
        // with none marked, a one-row drop-down's first enabled option. A
        // page that marks nothing shows that option without anyone choosing.
        else if(html(element,HTMLSelectElement,'select')){
          const options=[...element.options],marked=options.filter(option=>option.defaultSelected),single=!element.multiple;
          const reset=new Set(!single?marked:marked.length?marked.slice(-1):(element.size||1)===1?options.filter(option=>!option.matches(':disabled')).slice(0,1):[]);
          changed=options.some(option=>option.selected!==reset.has(option));
        }
        else if(['checkbox','radio'].includes(element.type))changed=element.checked!==element.defaultChecked;
        // Changed from the page's default, or typed since load and still
        // holding text. A page that moves the default along with typing
        // (React does for controlled fields) hides typing from the first
        // rule; a field emptied again holds nothing of anyone's. After a
        // retake every non-empty text field counts, as editors do after a
        // gap: typing in the gap was unseen, and whoever typed, it's the
        // owner's (typist: a release voids Claude's earlier marks).
        else{const value=element.value;changed=value!==element.defaultValue||(gotInput(element)||retaken&&typedField(element))&&value!=='';}
        if(changed)add(unsavedLabel(element),element);
      }
    }
    return {unsaved:fields.length>0,fields,claude_only:fields.length>0&&claudeOnly,playing:all().some(element=>['AUDIO','VIDEO'].includes(element.tagName)&&!element.paused&&!element.ended)};
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
      else if (['focus','select','check','stage_file','install_file','reveal'].includes(message.command) && message.generation !== controlGeneration) throw Error('stale_reference: control ended');
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
      else if (message.command === 'reveal') {
        // Brief 28a, item 5 ("On screen first"): inside the armed hold, a
        // pointer input's target whose centre isn't on screen is scrolled to
        // the centre at once. Brief 20's facts read and hit test follow.
        const element=elements.get(message.element);
        if(!element?.isConnected)throw Error('stale_reference: read again');
        if(password(element))throw Error('owner_signin: password fields belong to the owner');
        const box=elementBox(element),x=box.x+box.width/2,y=box.y+box.height/2,shown=box.width>0&&box.height>0&&x>=0&&y>=0&&x<innerWidth&&y<innerHeight;
        if(!shown)(mappedImage(element)||element).scrollIntoView({block:'center',inline:'center',behavior:'instant'});
        value={revealed:!shown};
      }
      else if(message.command==='observe'){
        const node=elements.get(message.element);
        const actual=node?.isConnected?safeValue(node):{},observed=typeof actual.value==='string'?{value:actual.value.slice(0,2048),value_more:Math.max(0,actual.value.length-2048)}:Array.isArray(actual.value)?{value:actual.value.slice(0,3),value_more:Math.max(0,actual.value.length-3)}:actual;
        const clipboard=guard.clipboard?.();
        // Brief 28a, item 2: the fingerprint of the element acted on, with the
        // document and reader instance that numbered it, so the service moves
        // the fingerprint only for that element.
        value={url:location.href,title:document.title,...(clipboard?{clipboard}:{}),notices:all().filter(element=>element.matches('[role=status],[role=alert],dialog[open],[role=dialog],[role=alertdialog]')).slice(0,5).map(element=>text(element).slice(0,2048)),change:node?.isConnected?{element:id(node),name:name(node),checked:!!node.checked,selected:!!node.selected,...observed,document:documentId,reader:readerInstance,fingerprint:fingerprint(node)}: {element_present:false}};
        if(clipboard)guard.clipboard(true);
      }
      else if (message.command === 'reload_state') value=reloadState();
      else if (message.command === 'ready') value = {preload:true,document:documentId,...(message.element?{element_present:!!elements.get(message.element)?.isConnected}:{})};
      else if (message.command === 'typed_fields') value={...typedFields(),origin:globalThis.origin,url:location.href,title:document.title};
      else if (message.command === 'read_typed_fields') value=readTypedFields(message);
      else if (message.command === 'outline') value=outline(message.limit);
      else if (message.command === 'options') value=fieldOptions(message);
      else if (message.command === 'page_state') value=pageState();
      else if (message.command === 'read' || message.command === 'facts') value = snapshot(message.element);
      else if (message.command === 'steps') { value = guard.steps(); }
      else if (message.command === 'focus') {
        const element = elements.get(message.element);
        if (!element?.isConnected) throw Error('stale_reference: read again');
        if (password(element)) throw Error('owner_signin: password fields belong to the owner');
        // A fill or a key would overwrite what Claude can't see.
        if (typedField(element)&&unknownHistory(element)) throw Error('owner_signin: the tool may not read this field, so it does not type into it either; the owner types here himself');
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
          if(!(html(element,HTMLSelectElement,'select')) || element.matches(':disabled'))throw Error('refused: choose an enabled native select control');
          const choices=[...element.options].filter(option=>option.value===message.value);
          if(choices.length!==1 || choices[0].matches(':disabled'))throw Error('stale_reference: the exact enabled option is missing or ambiguous; read again');
          element.value = message.value;
        }
        else element.checked = message.checked;
        guard.typedByClaude?.(element);
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
