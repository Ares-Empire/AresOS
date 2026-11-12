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
  }else if(mode==='search-label'){
    const label=variant==='delete'?'Delete':'Pay';
    const asking=variant==='editable-aria'?'<div role="button" contenteditable="true" id="asking">Pay</div>':'<button type="submit"'+(variant==='editable-native'?' contenteditable="true"':'')+' id="asking">'+label+'</button>';
    body='<button type="button" id="continue">Continue</button><form role="search" method="get" action="/query" target="sink"><input type="search" name="q">'+asking+'</form>'+sink;
    script=`document.querySelector('#asking').onclick=event=>{event.preventDefault();${send};};document.querySelector('#continue').onclick=()=>document.querySelector('#asking').click();`;
  }else if(mode==='ordinary-search'){
    body='<form role="search" method="get" action="/receive" target="sink"><input type="hidden" name="case" value="'+id+'"><input type="search" aria-label="Query" name="q" value="'+url.searchParams.get('query')+'"><button>Search</button></form>'+sink;
  }else if(mode==='compose-key'){
    body='<textarea aria-label="Message">Pay for lunch</textarea><textarea id="other" aria-label="Other draft">Approved draft</textarea>';
    script=`document.querySelector('textarea').onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();fetch(${JSON.stringify(receive)},{method:'POST',body:document.querySelector('#other').value});}};globalThis.reviewChange=()=>document.querySelector('#other').value='Different draft';`;
  }else if(mode==='owner-overlap'){
    // Queue an overdue timer behind real owner input, without changing private
    // mark lifetime. Focus first so Tab cannot consume the queued input slot.
    body='<button type="button" id="continue">Continue</button><form id="owner-form" method="post" action="/receive?case=owner-'+id+'" target="sink"><input id="owner" name="draft" value="Saved"><button>Submit</button><button id="second">Submit another</button></form><form id="other-form" method="post" action="'+receive+'" target="sink"><input name="draft" value="Other"></form>'+sink;
    script=`const trace=phase=>fetch('/receive?case=trace-'+${JSON.stringify(id)},{method:'POST',body:JSON.stringify({phase,time:performance.timeOrigin+performance.now()})});document.querySelector('#continue').onclick=()=>{fetch('/receive?case=task-start',{method:'POST',body:${JSON.stringify(id)}});setTimeout(()=>{trace('busy-begin');const end=performance.now()+240;while(performance.now()<end){}trace('busy-end');},70);setTimeout(()=>{trace('timer-fire');document.querySelector('#other-form').submit();},150);document.querySelector('#owner').focus();};document.querySelector('#owner').onkeydown=event=>{if(event.key==='Enter')trace('owner-enter');};document.querySelector('#owner-form').onsubmit=()=>trace('owner-submit');`;
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
    const composed=url.searchParams.get('composed')==='true',cancel=url.searchParams.get('cancel')==='true',native=url.searchParams.get('native')==='true';
    body='<button type="button" id="continue">Continue</button><div id="host"></div>'+sink;
    script=`document.querySelector('#continue').onclick=()=>{const host=document.querySelector('#host'),root=${native?'opener.Element.prototype.attachShadow.call(host,':'host.attachShadow('}{mode:${JSON.stringify(variant)}}),link=document.createElement('a');link.textContent='Delete';link.href=${JSON.stringify(receive)};link.target='sink';link.onclick=()=>fetch('/receive?case=handler-'+${JSON.stringify(id)},{method:'POST'});${native&&composed?'opener.Node.prototype.appendChild.call(root,link)':'root.append(link)'};opener.EventTarget.prototype.dispatchEvent.call(link,new MouseEvent('click',{bubbles:true,composed:${composed},cancelable:${cancel}}));};`;
  }else if(mode==='label'){
    const word=variant==='nfc-delete'?'lo\u0308schen':variant==='nfc-send'?'vero\u0308ffentlichen':variant==='title'?'Delete':'Continue';
    body='<textarea aria-label="Draft">Saved</textarea><form action="https://fixture.test/%73end?bad='+variant+'"><button type="button"'+(variant==='title'?' title="More information"':'')+'>'+word+'</button></form>';
    script=`document.querySelector('button').onclick=()=>${send};`;
  }else if(mode==='binding'){
    const container=['unsubscribe','abbestellen'].includes(variant)?'div role="listitem"':variant==='region'?'section aria-label="Selected region"':variant==='section'?'section aria-labelledby="item-label"':'div role="'+variant+'"';
    body='<'+container+'><span id="item-label">Quarterly report</span><button type="button">'+(variant==='unsubscribe'?'Unsubscribe':variant==='abbestellen'?'Abbestellen':'Delete')+'</button></'+container.split(' ')[0]+'>';
    script=`document.querySelector('button').onclick=()=>${send};globalThis.reviewChange=()=>document.querySelector('#item-label').textContent='Different report';`;
  }else if(mode==='shadow-binding'){
    const slotted=variant.startsWith('slot-'),native=variant.includes('li-'),tag=native?'li':'div role="row"',closed=variant.endsWith('closed');
    body=slotted?'<div id="host"><button type="button" slot="action">Delete</button></div>':'<'+tag+'><span id="item-label">Invoice A</span><div id="host"></div></'+tag.split(' ')[0]+'>';
    const content=slotted?'<'+tag+'><span id="item-label">Invoice A</span><slot name="action"></slot></'+tag.split(' ')[0]+'>':'<button type="button">Delete</button>';
    script=`const root=document.querySelector('#host').attachShadow({mode:${JSON.stringify(closed?'closed':'open')}});root.innerHTML=${JSON.stringify(content)};const button=${slotted?"document.querySelector('button')":"root.querySelector('button')"},label=()=>${slotted?"root.querySelector('#item-label')":"document.querySelector('#item-label')"};button.onclick=()=>fetch(${JSON.stringify(receive)},{method:'POST',body:label().textContent});globalThis.reviewChange=()=>label().textContent='Invoice B';${slotted?`fetch('/receive?case=slot-probe-'+${JSON.stringify(id)},{method:'POST',body:JSON.stringify({closed:${closed},public_slot:button.assignedSlot!==null})});`:''}`;
  }else if(mode==='quantity'){
    body='<article>Unit price 25 <input type="number" aria-label="Quantity" value="1"><button type="button">Pay</button></article>';
    script=`document.querySelector('button').onclick=()=>fetch(${JSON.stringify(receive)},{method:'POST',body:document.querySelector('input').value});globalThis.reviewChange=()=>document.querySelector('input').value='2';`;
  }else if(mode==='confirmation'){
    const submit=variant==='submit'||variant==='submit-send',label=variant==='submit-send'?'Send':'OK';
    body='<textarea aria-label="Draft">Approved draft</textarea>'+(variant?'<dialog open><form method="dialog">':'<div role="dialog" aria-modal="true">')+'<p>Send this message?</p><button type="'+(submit?'submit':'button')+'">'+label+'</button>'+(variant?'</form></dialog>':'</div>');
    script=`document.querySelector('button').onclick=event=>{event.preventDefault();fetch(${JSON.stringify(receive)},{method:'POST',body:document.querySelector('textarea').value});};globalThis.reviewChange=()=>document.querySelector('textarea').value='Different draft';`;
  }else if(mode==='file'||mode==='owner-file'){
    body=form('<input type="file" name="attachment" aria-label="File"><button type="submit">Submit</button>').replace('method="post"','method="post" enctype="multipart/form-data"')+sink;
    script="const field=document.querySelector('[type=file]');const install=bytes=>{const old=field.files[0],transfer=new DataTransfer();transfer.items.add(new File([bytes],old?.name||'proof.txt',{lastModified:old?.lastModified||0}));field.files=transfer.files;};"+(mode==='file'?"install('GOOD');":"")+"globalThis.reviewChange=()=>install('EVIL');"+(mode==='owner-file'?`for(const type of ['input','change','cancel'])field.addEventListener(type,()=>fetch('/compat-report',{method:'POST',body:JSON.stringify({id:${JSON.stringify(id)},phase:'owner-file-'+type,files:[...field.files].map(file=>({name:file.name,size:file.size,lastModified:file.lastModified}))})}));`:'');
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
  }else if(mode==='preexisting-dialog'){
    const kind=url.searchParams.get('dialog')||'confirm';
    body='<button type="button">Ready</button>'+form('<input type="hidden" name="reply">')+sink;
    script=`const key=${JSON.stringify('preexisting-'+id)};if(!sessionStorage.getItem(key)){sessionStorage.setItem(key,'opened');setTimeout(()=>{const reply=globalThis.firstScriptDialogs[${JSON.stringify(kind)}].call(window,'Already open','Original prompt');fetch(${JSON.stringify(receive)},{method:'POST',body:String(reply)});},300);}`;
  }else if(mode==='borrowed-dialog'){
    const kind=url.searchParams.get('dialog')||'confirm';body=form('<input type="hidden" name="reply">')+sink;
    script=`let generation=0;globalThis.reviewChange=()=>setTimeout(()=>{const current=generation++;const borrowed=()=>opener.firstScriptDialogs[${JSON.stringify(kind)}].call(window,${variant==='changed-dialog'?"current?'Changed borrowed native':'Borrowed native'":"'Borrowed native'"},'Original prompt');const converted={[Symbol.toPrimitive](hint){if(hint!=='string')throw Error('Native string hint changed');borrowed();return 'Converted native argument';}};const reply=${variant==='conversion-message'?`globalThis[${JSON.stringify(kind)}](converted,'Original prompt')`:variant==='conversion-default'?`globalThis[${JSON.stringify(kind)}]('Outer native',converted)`:'borrowed()'};${variant==='changed-dialog'?"if(current===0)return;":''}document.querySelector('[name=reply]').value=String(reply);document.querySelector('form').submit();},20);`;
  }else if(mode==='inline-dialog'){
    const kind=url.searchParams.get('dialog');body='<button type="button">Continue</button><iframe id="child"></iframe>'+sink;
    const markup=form('<input type="hidden" name="reply">');
    script=`const child=document.querySelector('#child');${variant==='srcdoc'?`child.srcdoc=${JSON.stringify(markup)};`:`child.contentDocument.body.innerHTML=${JSON.stringify(markup)};`}document.querySelector('button').onclick=()=>{const reply=child.contentWindow[${JSON.stringify(kind)}]('Inline native','Synthetic default');child.contentDocument.querySelector('[name=reply]').value=String(reply);child.contentDocument.querySelector('form').submit();};`;
  }else if(mode==='native-dialog'){
    const kind=url.searchParams.get('dialog');
    body='<button type="button">Continue</button>'+form('<input type="hidden" name="reply" value="Unanswered">')+sink;
    script=`const openDialog=()=>{const reply=globalThis.firstScriptDialogs[${JSON.stringify(kind)}].call(window,'Continue?','Synthetic default');document.querySelector('[name=reply]').value=String(reply);document.querySelector('form').submit();};document.querySelector('button').onclick=openDialog;globalThis.reviewChange=()=>setTimeout(openDialog,20);`;
  }else return null;
  return {body,script};
}
