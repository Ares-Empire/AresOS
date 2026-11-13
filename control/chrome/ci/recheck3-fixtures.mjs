// Synthetic fixtures only; no account, real site or external asset.
export const whitespaceKinds=['pre','pre-wrap','pre-line','break-spaces','PRE','TEXTAREA','CODE'];
export const whitespaceText={before:'if approved:\n    send()\naudit()',indent:'if approved:\n    send()\n    audit()',line:'if approved:\n    send() audit()'};
export const defaultKinds=['a','area','svg-href','svg-xlink','svg-both','button','input-submit','input-image','external-button','button-reset','input-reset'];
export function defaultRows(){
  return defaultKinds.flatMap(kind=>(kind.endsWith('reset')?['frame']:['self','blank','frame',...(['a','area'].includes(kind)?['ping','download']:[])]).map(route=>({kind,route,id:'recheck3-default-'+kind+'-'+route})));
}
export function recheck3Page(url){
  const mode=url.searchParams.get('mode'),id=url.searchParams.get('id'),receive='/receive?case='+encodeURIComponent(id);
  const sink='<iframe name="sink" hidden></iframe>';
  let body='',script='';
  if(mode==='mixed'){
    const mask=Number(url.searchParams.get('mask')),rootMode=url.searchParams.get('root'),order=url.searchParams.get('order'),composed=url.searchParams.get('composed')==='true';
    body='<button type="button" id="continue">Continue</button><div id="host"></div>';
    script=`document.querySelector('#continue').onclick=()=>{
      const donor=opener,host=document.querySelector('#host');
      const root=${mask&1?'host.attachShadow(':'donor.Element.prototype.attachShadow.call(host,'}{mode:${JSON.stringify(rootMode)}});
      const button=donor.Document.prototype.createElement.call(document,'button');button.textContent='Delete';button.type='button';
      const insert=()=>${mask&2?'root.appendChild(button)':'donor.Node.prototype.appendChild.call(root,button)'};
      const listen=()=>${mask&4?"EventTarget.prototype.addEventListener.call(button,'click',handler)":"donor.EventTarget.prototype.addEventListener.call(button,'click',handler)"};
      const handler=()=>fetch(${JSON.stringify(receive)},{method:'POST',body:'mixed handler'});
      ${order==='before'?'listen();insert();':'insert();listen();'}
      ${mask&8?'EventTarget.prototype.dispatchEvent':'donor.EventTarget.prototype.dispatchEvent'}.call(button,new donor.MouseEvent('click',{bubbles:true,composed:${composed},cancelable:true}));
    };`;
  }else if(mode==='activation-default'){
    const kind=url.searchParams.get('kind'),route=url.searchParams.get('route'),target=route==='blank'?'_blank':route==='self'?'_self':'sink';
    const attrs=` id="asking" aria-label="Delete" href="${receive}" target="${target}"`+(route==='ping'?` ping="/receive?case=ping-${id}"`:'')+(route==='download'?' download="proof.txt"':'');
    let asking;
    if(kind==='a')asking='<a'+attrs+'>Delete</a>';
    else if(kind==='area')asking='<img alt="Map" usemap="#deletions" width="160" height="70" src="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22160%22 height=%2270%22%3E%3Crect width=%22160%22 height=%2270%22 fill=%22lightgray%22/%3E%3C/svg%3E"><map name="deletions"><area'+attrs+' alt="Delete" shape="rect" coords="0,0,160,70"></map>';
    else if(kind.startsWith('svg'))asking='<svg width="160" height="70" xmlns:xlink="http://www.w3.org/1999/xlink"><a'+attrs.replace(kind==='svg-xlink'?` href="${receive}"`:'__absent__','')+(kind!=='svg-href'?` xlink:href="${receive}"`:'')+'><rect width="160" height="70" fill="lightgray"/><text x="10" y="35">Delete</text></a></svg>';
    else{
      const image=kind==='input-image',reset=kind.endsWith('reset');
      const control=kind.startsWith('input')?`<input id="asking" type="${image?'image':reset?'reset':'submit'}" aria-label="Delete" value="Delete"${image?' alt="Delete" width="160" height="70" src="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22160%22 height=%2270%22%3E%3Ctext x=%2210%22 y=%2235%22%3EDelete%3C/text%3E%3C/svg%3E"':''}>`:'<button id="asking" type="'+(reset?'reset':'submit')+'">Delete</button>';
      asking='<form id="deletions" method="post" action="'+receive+'" target="'+target+'"><input name="draft" value="Native default">'+(kind==='external-button'?'':control)+'</form>'+(kind==='external-button'?control.replace('id="asking"','id="asking" form="deletions"'):'');
    }
    body='<button type="button" id="continue">Continue</button>'+asking+sink;
    script=`document.querySelector('#continue').onclick=()=>opener.EventTarget.prototype.dispatchEvent.call(document.querySelector('#asking'),new MouseEvent('click',{bubbles:true,cancelable:false}));`;
    if(kind.endsWith('reset'))script+=`document.querySelector('input[name=draft]').value='Changed';document.querySelector('form').addEventListener('reset',()=>fetch(${JSON.stringify(receive)},{method:'POST',body:'reset'}));`;
  }else if(mode==='compose-whitespace'){
    const kind=url.searchParams.get('kind'),tag=['PRE','TEXTAREA','CODE'].includes(kind)?kind.toLowerCase():'div';
    const style=kind==='CODE'?'pre-wrap':kind==='PRE'?'pre':kind==='TEXTAREA'?'pre-wrap':kind;
    body='<main><div contenteditable="true" aria-label="Draft">Existing draft</div><'+tag+' id="preview" style="white-space:'+style+'"></'+tag+'><button type="button">Send</button></main>';
    script=`const preview=document.querySelector('#preview'),texts=${JSON.stringify(whitespaceText)};let phase=0;
      const set=text=>${kind==='TEXTAREA'?'preview.value=text':'preview.textContent=text'};set(texts.before);
      document.querySelector('button').onclick=()=>fetch(${JSON.stringify(receive)},{method:'POST',body:${kind==='TEXTAREA'?'preview.value':'preview.textContent'}});
      globalThis.reviewChange=()=>{phase++;set(phase===1?texts[${JSON.stringify(url.searchParams.get('change')||'indent')}]:texts.line+'\\n');};`;
  }else throw Error('Unknown recheck3 fixture');
  return {body,script};
}
