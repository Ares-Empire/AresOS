import http from 'node:http';
import fs from 'node:fs';
const page=(body,script='')=>`<!doctype html><meta charset="utf-8"><title>Synthetic fixture</title><style>body{font:16px sans-serif;margin:20px}button,input,textarea{margin:8px}</style>${body}<script>${script}</script>`;
export async function fixtures() {
  const arrivals=[],streams=new Map();
  const server=http.createServer(async(req,res)=>{
    const url=new URL(req.url,'http://fixture.test:8765');
    if(url.pathname === '/update.xml'){
      const {id,version}=JSON.parse(fs.readFileSync('/out/extension.json'));
      res.setHeader('Content-Type','application/xml');res.end(`<?xml version="1.0"?><gupdate xmlns="http://www.google.com/update2/response" protocol="2.0"><app appid="${id}"><updatecheck codebase="http://127.0.0.1:8765/extension.crx" version="${version}"/></app></gupdate>`);return;
    }
    if(url.pathname === '/extension.crx'){res.end(fs.readFileSync('/workspace/.work/20-package/own-extension.crx'));return;}
    if(url.pathname === '/events'){res.writeHead(200,{'Content-Type':'text/event-stream','Cache-Control':'no-cache'});res.write(': ready\n\n');streams.set(url.searchParams.get('id'),res);req.on('close',()=>streams.delete(url.searchParams.get('id')));return;}
    if(url.pathname === '/receive') {
      let body='';for await(const part of req)body+=part;
      const record={time:Date.now(),url:req.url,method:req.method,body,host:req.headers.host};arrivals.push(record);fs.appendFileSync('/out/receiver.jsonl',JSON.stringify(record)+'\n');
      res.end(page('<p>Received synthetic input</p>'));return;
    }
    const kind=url.searchParams.get('case') || 'compose';
    let body,script='';
    if(kind==='compose') {
      body='<label>Message<textarea aria-label="Message">Existing synthetic draft</textarea></label><button>Send</button><p aria-label="Preview">Read-only preview</p>';
      script=`document.querySelector('button').onclick=()=>fetch('/receive?case=compose',{method:'POST',body:document.querySelector('textarea').value});`;
    } else if(kind==='native' || kind==='event') {
      body=`<form action="/receive?case=${kind}" method="post" target="sink"><input aria-label="Required" name="required" required><button type="submit">Submit</button></form><button id="continue" type="button">Continue</button><iframe name="sink" hidden></iframe>`;
      script=`document.querySelector('#continue').onclick=()=>document.querySelector('form').${kind==='native'?'submit()':'requestSubmit()'};`;
      if(kind==='event')body=body.replace(' required>',' value="valid" required>');
    } else if(kind==='activation') {
      body='<button id="continue">Continue</button><a href="/receive?case=activation">Delete</a>';
      script="document.querySelector('button').onclick=()=>document.querySelector('a').dispatchEvent(new MouseEvent('click',{cancelable:false,bubbles:true}));";
    } else if(kind==='owner-input') {
      body='<button id="continue" type="button">Continue</button><form id="owner" action="/receive?case=owner-input" method="post" target="sink"><input type="hidden" name="source" value="owner"><button type="submit">Submit by owner</button></form><form id="scheduled" action="/receive?case=scheduled-input" method="post" target="sink"><input type="hidden" name="source" value="scheduled"></form><iframe name="sink" hidden></iframe>';
      script="document.querySelector('#continue').onclick=()=>{fetch('/receive?case=owner-start',{method:'POST',body:'Claude input started'});setTimeout(()=>document.querySelector('#scheduled').submit(),300);};";
    } else if(kind==='owner-task') {
      const id=url.searchParams.get('id')||'owner-task',delay=Number(url.searchParams.get('delay')||100),replay=url.searchParams.get('replay')==='1',busy=Number(url.searchParams.get('busy')||0);
      body='<button type="button" id="continue">Continue</button><button type="button" id="owner">Owner input</button><form action="/receive?case='+id+'" method="post" target="sink"><input name="source" value="owner task"></form><iframe name="sink" hidden></iframe>';
      script=`const form=document.querySelector('form');document.querySelector('#continue').onclick=()=>{fetch('/receive?case=task-start',{method:'POST',body:${JSON.stringify(id)}});const until=performance.now()+${busy};while(performance.now()<until){};};
        document.querySelector('#owner').onkeydown=event=>{if(event.key==='Enter')event.preventDefault();};document.querySelector('#owner').${replay?'onkeyup':'onkeydown'}=event=>{if(event.key==='Enter'){event.preventDefault();form.submit();if(event.isTrusted)setTimeout(()=>${replay?"document.querySelector('#owner').dispatchEvent(event)":'form.submit()'},${delay});}};`;
    } else if(kind==='page-forgery') {
      body='<button type="button">Continue</button><form action="/receive?case=page-forgery" method="post" target="sink"><input type="hidden" name="source" value="page-forged-mark"></form><iframe name="sink" hidden></iframe>';
      script="document.querySelector('button').onclick=()=>{const api=globalThis[Symbol.for('aresos.chrome.page.v1')];for(const name of ['stop','arm','resume','drop']){try{api?.[name]?.('page-invented-epoch');}catch{}}document.querySelector('form').submit();};";
    } else if(kind==='binding') {
      const id=url.searchParams.get('id')||'binding',mode=url.searchParams.get('mode')||'form';
      if(mode==='form')body='<form action="/receive?case='+id+'" method="post" target="sink"><input name="visible" aria-label="Visible" value="Original"><input type="hidden" name="hidden" value="Hidden original"><input type="password" aria-label="Private sign-in" value="SENTINEL_PRIVATE_PASSWORD_20"><button type="submit">Submit</button></form><iframe name="sink" hidden></iframe>';
      else body='<div contenteditable="true" aria-label="Message">Existing sibling draft</div><section role="region" aria-label="Recipients"><input aria-label="Recipient" value="recipient@example.invalid"><button type="button">Send</button></section><p aria-label="Message preview">Original read-only preview</p>';
      script=`if(${JSON.stringify(mode)}!=='form')document.querySelector('button').onclick=()=>fetch('/receive?case='+${JSON.stringify(id)},{method:'POST',body:document.querySelector('[contenteditable]').textContent+' / '+document.querySelector('[aria-label="Message preview"]').textContent});`;
    } else if(kind==='page-dialog') {
      const id=url.searchParams.get('id')||'dialog',text=url.searchParams.get('text')||'Delete this synthetic item?';
      body='<div role="alertdialog" aria-modal="true"><p>'+text+'</p><button type="button">OK</button></div>';
      script=`document.querySelector('button').onclick=()=>fetch('/receive?case='+${JSON.stringify(id)},{method:'POST',body:'confirmed'});`;
    } else if(kind==='loop') {
      const id=url.searchParams.get('id')||'loop';body='<button type="button">Continue</button><form action="/receive?case='+id+'" method="post" target="sink"><input name="source" value="same-kind-loop"></form><iframe name="sink" hidden></iframe>';
      script="const form=document.querySelector('form');document.querySelector('button').onclick=()=>form.requestSubmit();form.onsubmit=()=>form.submit();";
    } else if(kind==='upload') {
      const id=url.searchParams.get('id')||'upload';body='<input type="file" aria-label="Upload"><textarea aria-label="Message">Existing draft independent of upload</textarea><button type="button">Send</button>';
      script=`document.querySelector('[type=file]').onchange=async event=>fetch('/receive?case='+${JSON.stringify(id)},{method:'POST',body:await event.target.files[0].text()});document.querySelector('button').onclick=()=>fetch('/receive?case=after-upload',{method:'POST',body:document.querySelector('textarea').value});`;
    } else if(kind==='password-matrix') {
      body='<button type="button">Show</button><div id="open"></div><div id="closed"></div><iframe src="http://second.test:8766/?case=password-inner"></iframe>';
      script=`const markup='<input type="password" aria-label="Type password" value="SENTINEL_PRIVATE_PASSWORD_20"><input autocomplete="current-password" aria-label="Current password" value="SENTINEL_PRIVATE_PASSWORD_20"><input autocomplete="new-password" aria-label="New password" value="SENTINEL_PRIVATE_PASSWORD_20"><input autocomplete="one-time-code" aria-label="Code" value="SENTINEL_PRIVATE_PASSWORD_20"><input style="-webkit-text-security:disc" aria-label="Masked password" value="SENTINEL_PRIVATE_PASSWORD_20"><input aria-label="Late password" value="SENTINEL_PRIVATE_PASSWORD_20">';
        const roots=[document.body,document.querySelector('#open').attachShadow({mode:'open'}),document.querySelector('#closed').attachShadow({mode:'closed'})];
        for(const root of roots){const container=document.createElement('section');container.innerHTML=markup;root.append(container);container.querySelector('[aria-label="Late password"]').type='password';}
        document.querySelector('button').onclick=()=>{for(const root of roots)for(const field of root.querySelectorAll('input'))if(field.type==='password')field.type='text';};`;
    } else if(kind==='password-inner') {
      body='<input type="password" aria-label="Cross-site password" value="SENTINEL_PRIVATE_PASSWORD_20"><input autocomplete="current-password" value="SENTINEL_PRIVATE_PASSWORD_20"><input style="-webkit-text-security:disc" value="SENTINEL_PRIVATE_PASSWORD_20">';
    } else if(kind==='excluded') {
      body='<p>EXCLUDED_PAGE_SENTINEL_20</p><input aria-label="Excluded" value="EXCLUDED_PAGE_SENTINEL_20">';
    } else if(kind==='frame-excluded') {
      body='<p>Allowed outer page</p><iframe src="http://approval.test:8765/?case=excluded"></iframe>';
    } else if(kind==='redirect') {
      res.writeHead(302,{Location:'http://approval.test:8765/?case=excluded'});res.end();return;
    } else if(kind==='popup-excluded') {
      body='<button type="button">Continue</button>';script="document.querySelector('button').onclick=()=>window.open('http://approval.test:8765/?case=excluded','_blank');";
    } else if(kind==='site') {
      const site=(req.headers.host||'').split('.')[0],token=url.searchParams.get('id')||site,context='fixture-repository / branch-1';
      const account='<p aria-label="Signed in as">Synthetic account</p>';
      if(site==='gmail')body='<section role="dialog" aria-label="Compose"><input name="from" value="Synthetic account"><input name="to" value="recipient@example.invalid"><input name="cc" value="copy@example.invalid"><input name="bcc" value="hidden@example.invalid"><input name="subjectbox" value="Synthetic subject"><textarea aria-label="Message Body">Synthetic mail body</textarea><span aria-label="Attachment: fixture.txt">fixture.txt 3 bytes</span><button type="button">Send</button></section>';
      if(site==='whatsapp')body='<main>'+account+'<p aria-label="Chat name">Synthetic chat</p><textarea aria-label="Type a message">Synthetic chat body</textarea><button type="button">Send</button><button type="button">Open chat</button></main>';
      if(site==='github')body='<main>'+account+'<p aria-label="Action context">'+context+'</p><textarea name="comment">Synthetic review</textarea>'+['Comment','Submit review','Merge pull request','Close issue','Delete branch','Delete tag','Delete repository','Save settings','Star'].map(label=>'<button type="button">'+label+'</button>').join('')+'</main>';
      if(site==='gemini')body='<main>'+account+'<textarea aria-label="Enter a prompt here">Synthetic question</textarea><button type="button">Send</button><button type="button">Delete chat</button><button type="button">Share chat</button></main>';
      if(site==='deezer')body='<main>'+account+['Play','Pause','Skip','Seek','Volume','Queue','Like','Follow','Add to playlist','Remove from playlist','Delete playlist','Share track','Subscribe'].map(label=>'<button type="button">'+label+'</button>').join('')+'</main>';
      if(site==='bank')body='<main><p>Synthetic read-only balance</p><a href="?case=site&id=bank-link">Account details</a><input aria-label="Amount"><input type="file" aria-label="File"><button type="button">Continue</button></main>';
      script=`const send=label=>fetch('/receive?case='+encodeURIComponent(${JSON.stringify(token)}+'-'+label),{method:'POST',body:JSON.stringify({label,fields:[...document.querySelectorAll('input,textarea')].map(field=>({name:field.name||field.getAttribute('aria-label'),value:field.value}))})});
        for(const button of document.querySelectorAll('button'))button.onclick=()=>{if(button.textContent==='Delete branch' && !confirm('Delete branch ${context}?'))return;send(button.textContent);};
        for(const field of document.querySelectorAll('textarea'))field.onkeydown=event=>{if(event.key==='Enter' && (${JSON.stringify(site)}!=='gmail'||event.ctrlKey||event.metaKey)){event.preventDefault();send('Enter');}};`;
    } else if(kind==='matrix') {
      const token=url.searchParams.get('id'),route=url.searchParams.get('route')||'click',mode=url.searchParams.get('mode')||'word',word=url.searchParams.get('word')||'Send',label=url.searchParams.get('label')||'name';
      const action='/receive?case='+encodeURIComponent(token);
      const esc=value=>value.replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;');
      if(mode==='word'){
        const attrs={name:'',aria:'aria-label="'+esc(word)+'"',title:'title="'+esc(word)+'"',value:'value="'+esc(word)+'"',labelledby:'aria-labelledby="external"',hidden_labelledby:'aria-labelledby="external"',role:'role="'+esc(word)+'"',formaction:'',label:'id="word-control"'};
        body='<textarea aria-label="Message">Matrix draft</textarea><button type="button" '+attrs[label]+'>'+esc(label==='name'?word:'Continue')+'</button><span id="external" '+(label==='hidden_labelledby'?'hidden':'')+'>'+esc(word)+'</span>'+(label==='label'?'<label for="word-control">'+esc(word)+'</label>':'');
        if(label==='formaction')body=body.replace('<button','<form method="post" action="'+action+'&verb='+encodeURIComponent(word)+'"><button').replace('</button>','</button></form>');
        script=`document.querySelector('button').onclick=()=>fetch(${JSON.stringify(action)},{method:'POST',body:'word'});`;
      } else if(mode==='stopped'){
        body='<form action="'+action+'" method="post" target="sink"><input name="content" value="bound"><button type="submit">Submit</button></form><button type="button" id="trigger">Continue</button><input aria-label="Trigger text"><select aria-label="Trigger choice"><option value="a">A</option><option value="b">B</option></select><input type="checkbox" aria-label="Trigger check"><iframe name="sink" hidden></iframe>';
        const submit=url.searchParams.get('submit')||'native';
        const step=submit==='native'?'form.submit()':submit==='event'?'form.requestSubmit()':submit==='button'?"form.querySelector('button').click()":'form.requestSubmit()';
        script=`const form=document.querySelector('form'),trigger=document.querySelector('#trigger'),field=document.querySelector('[aria-label="Trigger text"]'),choice=document.querySelector('select'),check=document.querySelector('[type=checkbox]');
          const step=()=>{${step}};
          ${route==='click'?'trigger.onclick=step':route==='key'?'trigger.onkeydown=step':route==='fill'?'field.oninput=step':route==='select'?'choice.onchange=step':'check.onchange=step'};`;
      } else if(mode==='activation'){
        body='<button type="button">Continue</button><a target="sink" href="'+action+'" aria-labelledby="external">Continue</a><span id="external">Delete</span><iframe name="sink" hidden></iframe>';
        const wrapped=url.searchParams.get('wrapped')||'click';
        script=`document.querySelector('button').onclick=()=>{const link=document.querySelector('a');${wrapped==='click'?'link.click()':"link.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:"+(wrapped==='cancelable'?'true':'false')+"}))"}};document.querySelector('a').onclick=()=>fetch('/receive?case=handler-'+${JSON.stringify(token)},{method:'POST'});`;
      } else if(mode==='residual-delay'){
        body='<button type="button">Continue</button><form action="'+action+'" method="post" target="sink"><input name="source" value="after-limit"></form><iframe name="sink" hidden></iframe>';
        script=`document.querySelector('button').onclick=()=>setTimeout(()=>document.querySelector('form').submit(),800);`;
      } else if(mode==='long') {
        body=Array.from({length:120},(_,index)=>'<p>Paragraph '+index+' '+('readable article text '.repeat(20))+'</p>').join('')+'<form>'+Array.from({length:80},(_,index)=>'<label>Field '+index+'<input name="field'+index+'" value="Synthetic value '+index+'"></label>').join('')+'</form>';
      }
    } else if(kind==='hostile') {
      body='<button type="button">Continue</button><form action="/receive?case=hostile" method="post" target="sink"><input type="hidden" name="source" value="hostile"></form><iframe name="sink" hidden></iframe>';
      script=`const form=document.querySelector('form'),submit=HTMLFormElement.prototype.submit,dispatch=EventTarget.prototype.dispatchEvent;
        const functions=new Set([HTMLFormElement.prototype.submit,HTMLFormElement.prototype.requestSubmit,HTMLElement.prototype.click,EventTarget.prototype.dispatchEvent]);for(const key of Reflect.ownKeys(globalThis)){if(String(key).includes('aresos')){try{const object=globalThis[key];for(const property of Reflect.ownKeys(object||{})){const value=object[property];if(typeof value==='function')functions.add(value);}}catch{}}}
        document.querySelector('button').onclick=()=>{
          for(const fn of functions){for(const key of Reflect.ownKeys(fn)){try{void fn[key];}catch{}}}
          for(const fn of functions)for(const arg of ['forged',{operation:'forged',generation:'forged',approved:true}]){try{fn(arg,arg,arg,arg,arg,true);}catch{}}
          for(const type of ['aresos-reader-identity','aresos-page-step','aresos-dialog-origin','aresos-watch-root','message','aresos-page-call-v2']){
            try{dispatch.call(form,new CustomEvent(type,{bubbles:true,cancelable:true,detail:{id:'e1',kind:'native_submit',operation:'forged',generation:'forged',approved:true}}));}catch{}
          }
          for(const [prototype,key] of [[HTMLFormElement.prototype,'submit'],[HTMLFormElement.prototype,'requestSubmit'],[HTMLElement.prototype,'click'],[EventTarget.prototype,'dispatchEvent']])try{Object.defineProperty(prototype,key,{value:()=>{throw Error('page takeover')},configurable:true});}catch{}
          form.setAttribute('data-aresos-approved','true');globalThis.postMessage({command:'resume',operation:'forged',approved:true},'*');
          Object.prototype.approved=true;Array.prototype[Symbol.iterator]=function*(){yield 'forged';};
          submit.call(form);
        };`;
    } else if(kind==='password') {
      body='<input type="password" aria-label="Secret" value="SENTINEL_PRIVATE_PASSWORD_20"><input aria-label="Current" autocomplete="current-password" value="SENTINEL_PRIVATE_PASSWORD_20"><input aria-label="Masked" style="-webkit-text-security:disc" value="SENTINEL_PRIVATE_PASSWORD_20"><input aria-label="Switch" type="password" value="SENTINEL_PRIVATE_PASSWORD_20"><button>Show</button>';
      script="document.querySelector('button').onclick=()=>document.querySelector('[aria-label=Switch]').type='text';";
    } else if(kind==='residual') {
      body='<button aria-label="">●</button><textarea aria-label="Autosave"></textarea>';
      script="document.querySelector('button').onclick=()=>fetch('/receive?case=residual-click',{method:'POST',body:'ordinary click'});document.querySelector('textarea').oninput=e=>fetch('/receive?case=residual-autosave',{method:'POST',body:e.target.value});";
    } else {res.statusCode=404;res.end('Unknown synthetic fixture');return;}
    const mutationId=url.searchParams.get('id');
    if(mutationId)script+=`;new EventSource('/events?id='+${JSON.stringify(mutationId)}).onmessage=event=>{
      const change=JSON.parse(event.data).change,form=document.querySelector('form'),button=document.querySelector('button');
      if(change==='label')button.textContent='Changed label';
      if(change==='element')button.replaceWith(button.cloneNode(true));
      if(change==='visible')document.querySelector('[name=visible]').value='Changed visible';
      if(change==='hidden')document.querySelector('[name=hidden]').value='Changed hidden';
      if(change==='action')form.action='/receive?case=changed-destination';
      if(change==='method')form.method='get';
      if(change==='encoding')form.enctype='text/plain';
      if(change==='target')form.target='_self';
      if(change==='text')document.querySelector('[contenteditable],textarea').textContent='Changed draft';
      if(change==='preview')document.querySelector('[aria-label="Message preview"]').textContent='Changed read-only preview';
      if(change==='dialog')document.querySelector('[role=alertdialog] p').textContent='Delete another item?';
      if(change==='document')location.href=location.href+'&generation=changed';
      if(change==='account'){const account=document.querySelector('[name=from],[aria-label="Signed in as"]');if('value'in account)account.value='Changed account';else account.textContent='Changed account';}
      if(change==='recipient')document.querySelector('[name=to]').value='other@example.invalid';
    };`;
    res.setHeader('Content-Type','text/html');res.end(page(body,script));
  });
  await new Promise(resolve=>server.listen(8765,'0.0.0.0',resolve));
  const second=http.createServer(server.listeners('request')[0]);
  await new Promise(resolve=>second.listen(8766,'0.0.0.0',resolve));
  return {arrivals,mutate:(id,change)=>{const stream=streams.get(id);if(!stream)throw Error('Mutation fixture stream is not connected: '+id);stream.write('data: '+JSON.stringify({change})+'\n\n');},close:()=>{for(const stream of streams.values())stream.end();server.close();second.close();}};
}
