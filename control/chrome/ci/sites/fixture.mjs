// Synthetic site pages only. No production selectors or runtime modules are imported.
const esc=value=>String(value).replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;');
const buttons=labels=>labels.map(label=>`<button type="button">${esc(label)}</button>`).join('');
const account='<p aria-label="Signed in as">Synthetic account</p>';
const attachment='<span aria-label="Attachment: fixture.txt">fixture.txt 3 bytes</span>';
const context='fixture-repository / branch-1';
const confirmations={
  'Merge pull request':'Merge pull request '+context+'?',
  'Close issue':'Close issue '+context+'?',
  'Close pull request':'Close pull request '+context+'?',
  'Delete branch':'Delete branch '+context+'?',
  'Delete tag':'Delete tag '+context+'?',
  'Delete repository':'Delete repository '+context+'?',
  'Save settings':'Save settings for '+context+'?',
};

export function sitePage(url,host) {
  const variant=url.searchParams.get('variant'),site=variant==='child'?'github':host.split('.')[0],id=url.searchParams.get('id'),mismatch=url.searchParams.get('mismatch');
  if(!['gmail','whatsapp','github','gemini','deezer','bank'].includes(site)||!id)throw Error('Unknown synthetic adapter fixture');
  let body;
  const preview='<p aria-label="Message preview">Full quoted preview</p>';
  const compose=(which,to,text)=>`<section role="dialog" aria-label="Compose ${which}" data-compose="${which}"><input name="from" value="Synthetic account"><input name="to" value="${esc(to)}"><input name="cc" value="copy@mail.test"><input name="bcc" value="hidden@mail.test"><input name="subjectbox" value="Synthetic subject ${which}"><textarea aria-label="Message Body">${esc(text)}</textarea>${attachment}${preview}${buttons(['Send'])}</section>`;
  if(site==='gmail')body=compose('first','one@mail.test,two@mail.test','Full synthetic message\nSecond line')+(variant==='two'?compose('second','other@mail.test','Second compose text'):'')+'<main>'+account+'<p aria-label="Action context">Selected synthetic message</p><button type="button">Selected message</button></main>';
  if(site==='gmail'&&variant==='quoted')body=compose('first','"Last, First" <one@mail.test>,two@mail.test','Full synthetic message\nSecond line');
  if(site==='whatsapp')body='<main>'+account+'<p aria-label="Chat name">Synthetic chat</p><textarea aria-label="Type a message">Full synthetic message\nSecond line</textarea>'+attachment+preview+buttons(['Send','Open chat'])+'</main>';
  if(site==='github')body='<main>'+account+'<p aria-label="Action context">'+context+'</p><textarea name="comment">Full synthetic review</textarea>'+attachment+preview+buttons(['Comment','Submit review','Approve review','Request changes','Merge pull request','Close issue','Close pull request','Delete branch','Delete tag','Delete repository','Save settings','Star','Unstar'])+'</main>';
  if(site==='gemini')body='<main>'+account+'<textarea aria-label="Enter a prompt here">Full synthetic question</textarea>'+attachment+preview+buttons(['Send','Delete chat','Share chat'])+'</main>';
  if(site==='deezer')body='<main>'+account+'<p aria-label="Action context">Synthetic playlist</p><textarea name="comment">Full synthetic music comment</textarea>'+buttons(['Play','Pause','Skip','Next','Previous','Seek','Volume','Queue','Like','Follow','Add to playlist','Add to library','Unlike','Unfollow','Remove from playlist','Remove from favorites','Remove from favourites','Delete playlist','Post comment','Share track','Share playlist','Pay','Subscribe'])+'<select aria-label="Playback position"><option value="a">Start</option><option value="b">Middle</option></select><select aria-label="Playback volume"><option value="a">Quiet</option><option value="b">Loud</option></select><input type="checkbox" aria-label="Library addition"></main>';
  if(site==='bank')body='<main><p>Synthetic read-only balance</p><input aria-label="Amount"><input type="file" aria-label="File"><input type="checkbox" aria-label="Tick"><select aria-label="Choice"><option value="a">A</option><option value="b">B</option></select>'+buttons(['Continue'])+'<a href="/receive?case='+encodeURIComponent(id+':link')+'">Account details</a></main>';
  if(variant==='unknown')body='<div contenteditable="true" aria-label="Draft">Unrecognised existing draft</div>'+buttons(['Send']);
  if(variant==='incomplete')body=body.replace(/<input name="from"[^>]*>|<p aria-label="Signed in as">.*?<\/p>/g,'');
  if(variant==='form-playback')body=account+'<form action="/receive?case='+encodeURIComponent(id+':Play:main')+'" method="post" target="sink"><input name="track" value="Synthetic track"><button type="submit">Play</button></form><iframe name="sink" hidden></iframe>';
  const child=new URL(url);child.searchParams.set('variant','child');child.hostname=mismatch==='site'?'second.test':'github.test';
  if(['frame','site'].includes(mismatch))body+='<iframe src="'+esc(child.href)+'"></iframe>';
  if(variant==='child')body='<p>Separate native confirmation opener</p>';
  const script=`
    const id=${JSON.stringify(id)},site=${JSON.stringify(site)},variant=${JSON.stringify(variant)},mismatch=${JSON.stringify(mismatch)},plans=${JSON.stringify(confirmations)};
    const scope=node=>node.closest('[data-compose],main')||document.body;
    const snapshot=root=>({fields:[...root.querySelectorAll('input,textarea,[contenteditable]')].map(node=>({name:node.name||node.getAttribute('aria-label'),value:node.value??node.textContent})),attachments:[...root.querySelectorAll('[aria-label^="Attachment:"]')].map(node=>({label:node.getAttribute('aria-label'),text:node.textContent})),preview:root.querySelector('[aria-label="Message preview"]')?.textContent,chat:root.querySelector('[aria-label="Chat name"]')?.textContent,account:root.querySelector('[aria-label="Signed in as"]')?.textContent,context:root.querySelector('[aria-label="Action context"]')?.textContent});
    const send=(label,root=document.body)=>fetch('/receive?case='+encodeURIComponent(id+':'+label+':'+(root.dataset.compose||'main')),{method:'POST',body:JSON.stringify({label,...snapshot(root)})});
    const confirmAction=(label,root)=>{
      const text=plans[label];
      if(!text){send(label,root);return;}
      if(['frame','site'].includes(mismatch)){document.querySelector('iframe').contentWindow.postMessage({label,text},'*');return;}
      if(mismatch==='button'){
        const dialog=document.createElement('section');dialog.setAttribute('role','dialog');dialog.setAttribute('aria-label',text);dialog.innerHTML='<p>'+text+'</p><button type="button">Delete now</button>';document.body.append(dialog);dialog.querySelector('button').onclick=()=>{send(label,root);dialog.remove();};return;
      }
      const accepted=mismatch==='kind'?prompt(text):confirm(mismatch==='text'?text+' Different item':text);
      if(!accepted)return;
      if(mismatch==='twice'&&!confirm(text))return;
      send(label,root);
    };
    if(variant==='child')addEventListener('message',event=>{if(event.data?.label&&confirm(event.data.text))send(event.data.label);});
    if(variant!=='form-playback')for(const button of document.querySelectorAll('button'))button.onclick=()=>confirmAction(button.textContent,scope(button));
    if(site==='bank')for(const field of document.querySelectorAll('input,select'))for(const event of ['input','change','keydown'])field.addEventListener(event,()=>send('Unexpected bank input',scope(field)));
    if(site==='deezer')for(const field of document.querySelectorAll('select,input[type=checkbox]'))field.onchange=()=>send(field.getAttribute('aria-label'),scope(field));
    for(const field of document.querySelectorAll('textarea'))field.onkeydown=event=>{
      if(event.key==='#'&&site==='gmail'){event.preventDefault();send('Delete shortcut',scope(field));}
      if(event.key==='Enter'&&(site!=='gmail'||event.ctrlKey||event.metaKey)){event.preventDefault();send('Enter',scope(field));}
    };
    for(const button of document.querySelectorAll('button'))button.addEventListener('keydown',event=>{if(event.key==='#'&&site==='gmail'){event.preventDefault();send('Delete shortcut',scope(event.target));}});
    const channel=new EventSource('/events?id='+encodeURIComponent(id));
    channel.onmessage=event=>{
      const {change,nonce}=JSON.parse(event.data),[field,which='first']=change.split(':'),root=document.querySelector('[data-compose="'+which+'"]')||document.querySelector('main')||document.body;
      const selectors={account:'[name=from],[aria-label="Signed in as"]',to:'[name=to]',cc:'[name=cc]',bcc:'[name=bcc]',subject:'[name=subjectbox]',text:'textarea,[contenteditable]',chat:'[aria-label="Chat name"]',context:'[aria-label="Action context"]',preview:'[aria-label="Message preview"]',attachments:'[aria-label^="Attachment:"]'};
      const node=root.querySelector(selectors[field]||'textarea');
      if(field==='dialog')setTimeout(()=>{if(confirm('Delete synthetic transfer?'))send('Unexpected bank dialog',document.body);},100);
      else if(field==='recipients-order')root.querySelector('[name=to]').value='two@mail.test,one@mail.test';
      else if(field==='recipient-collision')root.querySelector('[name=to]').value='First" <one@mail.test>,"Last,two@mail.test';
      else if(field==='recipient-role'){const cc=root.querySelector('[name=cc]'),bcc=root.querySelector('[name=bcc]');[cc.value,bcc.value]=[bcc.value,cc.value];}
      else if(node){if('value'in node)node.value='Changed synthetic '+field;else node.textContent='Changed synthetic '+field;}
      fetch('/mutation-ack?nonce='+encodeURIComponent(nonce));
    };
  `;
  return {body,script};
}
