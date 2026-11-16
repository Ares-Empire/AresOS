// Brief 28, group 14's password fixtures: fields the reader may not read
// although they look plain when it arrives. They are served as
// case=password-unread, so the test build's recording of the content
// script's reads covers them (password-ingress.js). Every name and value is
// synthetic. PASSWORD is group 7's known password: no result may hold it.
export const PASSWORD='SENTINEL_PRIVATE_PASSWORD_20';
const MASK='-webkit-text-security:disc';

// Nine ways a password field is plain before the reader comes. Each is
// labelled "Code", which names nothing; data-plain says how the page undoes
// its protection: a new type, or the attribute it removes.
const madePlain=secret=>[
  ...['text','search','email','url'].map(type=>`<input type="password" data-plain="${type}" aria-label="Code" value="${secret}">`),
  `<input autocomplete="current-password" data-plain="autocomplete" aria-label="Code" value="${secret}">`,
  `<input style="${MASK}" data-plain="style" aria-label="Code" value="${secret}">`,
  `<input class="masked" data-plain="class" aria-label="Code" value="${secret}">`,
  `<textarea style="${MASK}" data-plain="style" aria-label="Code">${secret}</textarea>`,
  `<textarea class="masked" data-plain="class" aria-label="Code">${secret}</textarea>`,
];
// The mutation check's page (probe=1) holds this value in the same nine fields, and the password nowhere: the case
// reads it once with the history rule switched off in the test build (prepare.mjs), where every field shows it.
export const PROBE='MUTATION_PROBE_VALUE_28';
// The page, an open root and a closed root, in the top document and again in a frame of the second site.
export const PLAIN_KINDS=madePlain(PASSWORD).length,PLAIN_ROOTS=3;

// The name rule, and a mask that is on right now: each holds the password.
// Listed by the name the outline shows for it.
export const NAMED=['Verification code','Password','Stored','Recovery phrase','Private key','Area','Box'];
const NAMED_FIELDS=`<label for="signin-field">Verification code</label><input id="signin-field" name="otp" value="${PASSWORD}">`
  +`<div contenteditable="true" aria-label="Password">${PASSWORD}</div>`
  +`<textarea name="secret_value" aria-label="Stored">${PASSWORD}</textarea>`
  +`<textarea aria-label="Recovery phrase">${PASSWORD}</textarea><textarea aria-label="Private key">${PASSWORD}</textarea>`
  +`<div contenteditable="true" style="${MASK}" aria-label="Area">${PASSWORD}</div><textarea style="${MASK}" aria-label="Box">${PASSWORD}</textarea>`;

// What a document shows that the reader didn't watch from its start: a typed
// kind only as filled or empty, a kind whose value isn't typed text as it is.
export const TYPED_KINDS={text:'PUBLIC_KIND_text_28',search:'PUBLIC_KIND_search_28',email:'kind-email-28@fixture.test',url:'http://fixture.test/kind-url-28',tel:'PUBLIC_KIND_tel_28',number:'282828282828',unknown:'PUBLIC_KIND_unknown_28'};
export const TYPED_AREA='PUBLIC_KIND_textarea_28',DRAFT_AREA='PUBLIC_DRAFT_AREA_28 written as a draft',OPTION='PUBLIC_OPTION_28';
const SHOWN=Object.entries(TYPED_KINDS).map(([type,value])=>`<input type="${type}" aria-label="Kind ${type}" value="${value}">`).join('')
  +`<textarea aria-label="Kind textarea">${TYPED_AREA}</textarea><input type="text" aria-label="Kind empty"><textarea aria-label="Kind empty area"></textarea>`
  +`<div contenteditable="true" aria-label="Draft area">${DRAFT_AREA}</div>`
  +'<input type="date" aria-label="Kind date" value="2026-11-16"><input type="checkbox" aria-label="Kind box" checked><input type="radio" name="choice" aria-label="Kind radio" checked>'
  +'<input type="range" aria-label="Kind range" value="42"><input type="color" aria-label="Kind colour" value="#112233">'
  +`<select aria-label="Kind option"><option>First</option><option selected>${OPTION}</option></select>`;

// The limit, shown honestly: an editable area that was masked by a style, is
// labelled "Value" and was unmasked before the reader came is read. It holds
// LIMIT, not the password, because the case asserts that it is read. A
// textarea with the same history is not read, and holds the password.
export const LIMIT='LIMIT_UNMASKED_EDITOR_28';
const LIMIT_FIELDS=`<div contenteditable="true" style="${MASK}" data-plain="style" aria-label="Value">${LIMIT}</div><textarea style="${MASK}" data-plain="style" aria-label="Value">${PASSWORD}</textarea>`;

// What the owner types into the late root's form as a draft; an approved asking read may show it once.
export const LATE_DRAFT='PRIVATE_LATE_DRAFT_28';

function plainPage(cross,id,probe){
  const frame=cross?'child':'top';
  const body=`<h1>${cross?'Plain child':'Plain top'}</h1><div id="light"></div><div id="open"></div><div id="closed"></div>`
    +(cross||probe?'':`<form id="named">${NAMED_FIELDS}</form><form id="shown">${SHOWN}</form><form id="limit">${LIMIT_FIELDS}</form>`
      +`<iframe style="width:100%;height:300px;display:block" src="http://second.test:8766/?case=password-unread&mode=plain-child&id=${encodeURIComponent(id)}"></iframe>`);
  // The fields stand as password fields for one task and are plain from the
  // next one on, as after the owner's "show". A reader that comes later (a
  // taken tab) has seen none of it; one that watched from the start has.
  const script=`const made=${JSON.stringify('<style>.masked{'+MASK+'}</style>'+madePlain(probe?PROBE:PASSWORD).join(''))};
    const shadows=[document.querySelector('#open').attachShadow({mode:'open'}),document.querySelector('#closed').attachShadow({mode:'closed'})];
    for(const root of [document.querySelector('#light'),...shadows]){const form=document.createElement('form');form.innerHTML=made;root.append(form);}
    setTimeout(()=>{
      for(const root of [document,...shadows])for(const field of root.querySelectorAll('[data-plain]')){
        const how=field.getAttribute('data-plain');
        if(['autocomplete','style','class'].includes(how))field.removeAttribute(how);else field.type=how;
      }
      const done=document.createElement('p');done.textContent=${JSON.stringify(cross?'Plain child ready':'Plain top ready')};document.body.append(done);
      fetch('/compat-report',{method:'POST',body:JSON.stringify({id:${JSON.stringify(id)},phase:'plain-ready',frame:${JSON.stringify(frame)}})});
    },0);`;
  return {body,script};
}

// A shadow root the reader meets late, in a document it watched from its
// start: <late-box> is in the page from the load and is upgraded later (the
// driver's first 'review-change'). Its constructor attaches a closed root to
// an element that is already there, which changes nothing an observer of the
// page sees. The owner then types with real keys; Enter in a field makes it
// plain, as a "show" control would, and moves on. None of this touches the
// light DOM, so the reader first meets the root in the read that follows.
//   password: a field labelled "Password", one labelled "Code", a textarea and an empty field;
//   form, moved: a form with a draft field, an empty second field and Send;
//   known: the same form with group 7's known password field in the draft's place.
function latePage(id,variant){
  const receive='/receive?case='+encodeURIComponent(id);
  const inner=variant==='password'
    ?'<input type="password" data-step aria-label="Password"><input type="password" data-step aria-label="Code"><textarea data-step aria-label="Notes"></textarea><input aria-label="Comment">'
    :`<form method="post" action="${receive}" target="sink">`+(variant==='known'?`<input type="password" aria-label="Secret" value="${PASSWORD}">`:'<input name="draft" data-step aria-label="Draft">')
      +'<input name="comment" aria-label="Comment"><button type="submit">Send</button></form>';
  const body='<h1>Late root</h1><late-box></late-box>'
    +(variant==='password'?`<form id="named">${NAMED_FIELDS}</form>`:'<button type="button" id="start">Continue</button>')
    +(variant==='moved'?`<form id="other" method="post" action="${receive}-other" target="sink"><input name="subject" aria-label="Subject" value="Saved subject"><button type="submit">Send other</button></form>`:'')
    +'<iframe name="sink" hidden></iframe>';
  const script=`let root=null,changes=0;const id=${JSON.stringify(id)},variant=${JSON.stringify(variant)};
    const tell=(phase,extra={})=>fetch('/compat-report',{method:'POST',body:JSON.stringify({id,phase,...extra})});
    const onKey=event=>{
      if(event.key!=='Enter'||!event.target.hasAttribute('data-step'))return;
      event.preventDefault();
      const steps=[...root.querySelectorAll('[data-step]')],next=steps[steps.indexOf(event.target)+1];
      if(event.target.type==='password')event.target.type='text';
      if(next)next.focus();
      else{event.target.blur();tell('late-typed',{filled:steps.filter(field=>field.value.length>0).length,trusted:event.isTrusted});}
    };
    const upgrade=()=>{
      customElements.define('late-box',class extends HTMLElement{constructor(){super();root=this.attachShadow({mode:'closed'});root.innerHTML=${JSON.stringify(inner)};root.addEventListener('keydown',onKey);}});
      if(!root)throw Error('late-box was not upgraded');
      const first=root.querySelector('[data-step]');if(first)first.focus();
      tell('late-ready');
    };
    // A later change: the draft's text changes (standing in for the owner's edit), or the page moves the draft into its other form.
    const change=()=>{
      const draft=root.querySelector('[name=draft]');
      if(variant==='moved')document.querySelector('#other').prepend(draft);else if(draft)draft.value=draft.value+' changed';
      tell('late-changed');
    };
    globalThis.reviewChange=()=>{changes++;if(changes===1)upgrade();else change();};
    const start=document.querySelector('#start');if(start)start.onclick=()=>{const form=root&&root.querySelector('form');if(form)form.requestSubmit();};`;
  return {body,script};
}

export function unreadPage(url){
  const mode=url.searchParams.get('mode'),id=url.searchParams.get('id')||'unread',variant=url.searchParams.get('variant')||'';
  if(mode==='plain'||mode==='plain-child')return plainPage(mode==='plain-child',id,url.searchParams.has('probe'));
  if(mode==='late'&&['password','form','moved','known'].includes(variant))return latePage(id,variant);
  return null;
}
