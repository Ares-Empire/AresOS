// Every address and identity here belongs to the disposable receiver.
export function reviewPage(url){
  const id=url.searchParams.get('id'),mode=url.searchParams.get('mode'),variant=url.searchParams.get('variant')||'';
  const receive='/receive?case='+encodeURIComponent(id),send=`fetch(${JSON.stringify(receive)},{method:'POST',body:'review fixture'})`;
  let body='',script='';
  const form=(extra='')=>`<form method="post" action="${receive}" target="sink"><input name="draft" value="Saved">${extra}</form>`;
  const sink='<iframe name="sink" hidden></iframe>';
  if(mode==='cross-tab'){
    body='<button type="button" id="open">Open window</button><button type="button" id="continue">Continue</button>';
    script=`let child;document.querySelector('#open').onclick=()=>{child=window.open('/?case=review-page&mode=cross-tab-inner&id='+${JSON.stringify(id)},'_blank');};document.querySelector('#continue').onclick=()=>HTMLFormElement.prototype.submit.call(child.document.querySelector('form'));`;
  }else if(mode==='cross-tab-inner'){
    body=form('<button type="button">Ready</button>')+sink;
  }else if(mode==='mixed-adapter'){
    body='<main><p aria-label="Signed in as">Synthetic account</p><textarea aria-label="Enter a prompt here">Synthetic question</textarea><button type="button"'+(variant==='none'?'':' title="'+variant+'"')+'>Send</button></main>';
    script=`document.querySelector('button').onclick=()=>${send};`;
  }else if(mode==='inline-hold'){
    body='<button type="button">Continue</button><iframe id="child"></iframe>'+sink;
    const markup=form();
    script=`const child=document.querySelector('#child');${variant==='srcdoc'?`child.srcdoc=${JSON.stringify(markup)};`:`child.contentDocument.body.innerHTML=${JSON.stringify(markup)};`}document.querySelector('button').onclick=()=>${variant==='borrowed'?'HTMLFormElement.prototype.submit.call(child.contentDocument.querySelector(\'form\'))':"child.contentDocument.querySelector('form').submit()"};`;
  }else if(mode==='inline-editor'){
    body='<button type="button">Send</button><iframe id="child" style="width:700px;height:250px"></iframe>';
    const markup='<div contenteditable="true" aria-label="Draft"><div>First draft line</div><div>Second draft line</div></div>';
    script=`const child=document.querySelector('#child');${variant==='srcdoc'?`child.srcdoc=${JSON.stringify(markup)};`:`child.contentDocument.body.innerHTML=${JSON.stringify(markup)};`}document.querySelector('button').onclick=()=>fetch(${JSON.stringify(receive)},{method:'POST',body:child.contentDocument.querySelector('[contenteditable]').innerText});globalThis.reviewChange=()=>child.contentDocument.querySelector('[contenteditable]').textContent='Changed inline draft';`;
  }else if(mode==='script-post'){
    body='<form method="post" action="/post-document?case='+id+'"><input name="draft" value="Script-started"></form>';
    script="setTimeout(()=>document.querySelector('form').submit(),100);";
  }else if(mode==='script-popup'){
    body='<button type="button">Open window</button>';
    script=`document.querySelector('button').onclick=()=>window.open('/?case=review-page&mode=script-post&id='+${JSON.stringify(id)},'_blank','popup,width=620,height=480');`;
  }else if(mode==='owner-mark'){
    body='<button type="button" id="continue">Continue</button><form id="owner-form" method="post" action="'+receive+'" target="sink"><input id="owner" name="draft" value="Saved"><button id="first">Submit</button><button id="second">Submit another</button></form><form id="other-form" method="post" action="'+receive+'" target="sink"><input name="draft" value="Other"></form>'+sink;
    script=`document.querySelector('#continue').onclick=()=>fetch('/receive?case=task-start',{method:'POST',body:${JSON.stringify(id)}});document.querySelector('#owner').onkeydown=event=>{if(event.key!=='Enter')return;event.preventDefault();${variant==='other-form'?"document.querySelector('#other-form').submit()":variant==='other-submitter'?"document.querySelector('#owner-form').requestSubmit(document.querySelector('#second'))":"setTimeout(()=>document.querySelector('#owner-form').submit(),100)"};};`;
  }else if(mode==='new-frame'){
    body='<button type="button">Continue</button>'+sink;
    script=`document.querySelector('button').onclick=()=>{const child=document.createElement('iframe');child.src='/?case=review-page&mode=new-frame-inner&id='+${JSON.stringify(id)};document.body.append(child);};`;
  }else if(mode==='new-frame-inner'){
    body=form()+sink;script="setTimeout(()=>document.querySelector('form').submit(),0);";
  }else if(mode==='shadow'){
    body='<button type="button" id="continue">Continue</button><div id="host"></div>'+sink;
    const markup=form('<button type="submit">Submit</button>');
    script=`document.querySelector('#continue').onclick=()=>{const root=document.querySelector('#host').attachShadow({mode:${JSON.stringify(variant.startsWith('closed')?'closed':'open')}});root.innerHTML=${JSON.stringify(markup)};const form=root.querySelector('form');${variant.endsWith('click')?"form.querySelector('button').click()":variant.endsWith('event')?'form.requestSubmit()':'form.submit()'};};`;
  }else if(mode==='shadow-fallback'){
    const composed=url.searchParams.get('composed')==='true',cancel=url.searchParams.get('cancel')==='true';
    body='<button type="button" id="continue">Continue</button><div id="host"></div>'+sink;
    script=`document.querySelector('#continue').onclick=()=>{const root=document.querySelector('#host').attachShadow({mode:${JSON.stringify(variant)}}),link=document.createElement('a');link.textContent='Delete';link.href=${JSON.stringify(receive)};link.target='sink';link.onclick=()=>fetch('/receive?case=handler-'+${JSON.stringify(id)},{method:'POST'});root.append(link);opener.EventTarget.prototype.dispatchEvent.call(link,new MouseEvent('click',{bubbles:true,composed:${composed},cancelable:${cancel}}));};`;
  }else if(mode==='label'){
    const word=variant==='nfc-delete'?'lo\u0308schen':variant==='nfc-send'?'vero\u0308ffentlichen':variant==='title'?'Delete':'Continue';
    body='<textarea aria-label="Draft">Saved</textarea><form action="https://fixture.test/%73end?bad='+variant+'"><button type="button"'+(variant==='title'?' title="More information"':'')+'>'+word+'</button></form>';
    script=`document.querySelector('button').onclick=()=>${send};`;
  }else if(mode==='binding'){
    const container=['unsubscribe','abbestellen'].includes(variant)?'div role="listitem"':variant==='region'?'section aria-label="Selected region"':variant==='section'?'section aria-labelledby="item-label"':'div role="'+variant+'"';
    body='<'+container+'><span id="item-label">Quarterly report</span><button type="button">'+(variant==='unsubscribe'?'Unsubscribe':variant==='abbestellen'?'Abbestellen':'Delete')+'</button></'+container.split(' ')[0]+'>';
    script=`document.querySelector('button').onclick=()=>${send};globalThis.reviewChange=()=>document.querySelector('#item-label').textContent='Different report';`;
  }else if(mode==='confirmation'){
    body='<textarea aria-label="Draft">Approved draft</textarea><div role="dialog" aria-modal="true"><p>Send this message?</p><button type="button">OK</button></div>';
    script=`document.querySelector('button').onclick=()=>${send};globalThis.reviewChange=()=>document.querySelector('textarea').value='Different draft';`;
  }else if(mode==='file'||mode==='owner-file'){
    body=form('<input type="file" name="attachment" aria-label="File"><button type="submit">Submit</button>').replace('method="post"','method="post" enctype="multipart/form-data"')+sink;
    script="const field=document.querySelector('[type=file]');const install=bytes=>{const old=field.files[0],transfer=new DataTransfer();transfer.items.add(new File([bytes],old?.name||'proof.txt',{lastModified:old?.lastModified||0}));field.files=transfer.files;};"+(mode==='file'?"install('GOOD');":"")+"globalThis.reviewChange=()=>install('EVIL');";
  }else if(mode==='rich'){
    body='<div contenteditable="true" aria-label="Draft"><div>Line one</div><div>Line two</div></div><button type="button">Send</button>';
    script=`document.querySelector('button').onclick=()=>${send};globalThis.reviewChange=()=>document.querySelector('[contenteditable]').textContent='Line one Line two';`;
  }else if(mode==='title'){
    body='<textarea aria-label="Draft">Approved draft</textarea><button type="button">Send</button>';
    script=`document.querySelector('button').onclick=()=>${send};globalThis.reviewChange=()=>document.title='Different title';`;
  }else if(mode==='frozen-stop'){
    body='<button type="button">Continue</button>';
    script="document.querySelector('button').onclick=()=>Object.freeze(HTMLElement.prototype);";
  }else if(mode==='notice'){
    body='<button type="button">Continue</button><p role="status">Waiting</p>';
    script="document.querySelector('button').onclick=()=>document.querySelector('[role=status]').textContent='ERROR: the change failed';";
  }else if(mode==='independent-dialog'){
    body=form()+sink;
    script=`globalThis.reviewChange=()=>setTimeout(()=>{confirm('Continue?');document.querySelector('form').submit();},20);`;
  }else if(mode==='native-dialog'){
    const kind=url.searchParams.get('dialog');
    body='<button type="button">Continue</button>'+form('<input type="hidden" name="reply" value="Unanswered">')+sink;
    script=`const openDialog=()=>{const reply=globalThis.firstScriptDialogs[${JSON.stringify(kind)}].call(window,'Continue?','Synthetic default');document.querySelector('[name=reply]').value=String(reply);document.querySelector('form').submit();};document.querySelector('button').onclick=openDialog;globalThis.reviewChange=()=>setTimeout(openDialog,20);`;
  }else return null;
  return {body,script};
}
