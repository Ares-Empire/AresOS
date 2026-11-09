import http from 'node:http';
import fs from 'node:fs';
const page=(body,script='')=>`<!doctype html><meta charset="utf-8"><title>Synthetic fixture</title><style>body{font:16px sans-serif;margin:20px}button,input,textarea{margin:8px}</style>${body}<script>${script}</script>`;
export async function fixtures() {
  const arrivals=[];
  const server=http.createServer(async(req,res)=>{
    const url=new URL(req.url,'http://fixture.test:8765');
    if(url.pathname === '/update.xml'){
      const {id,version}=JSON.parse(fs.readFileSync('/out/extension.json'));
      res.setHeader('Content-Type','application/xml');res.end(`<?xml version="1.0"?><gupdate xmlns="http://www.google.com/update2/response" protocol="2.0"><app appid="${id}"><updatecheck codebase="http://127.0.0.1:8765/extension.crx" version="${version}"/></app></gupdate>`);return;
    }
    if(url.pathname === '/extension.crx'){res.end(fs.readFileSync('/workspace/.work/20-package/own-extension.crx'));return;}
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
    } else if(kind==='page-forgery') {
      body='<button type="button">Continue</button><form action="/receive?case=page-forgery" method="post" target="sink"><input type="hidden" name="source" value="page-forged-mark"></form><iframe name="sink" hidden></iframe>';
      script="document.querySelector('button').onclick=()=>{const api=globalThis[Symbol.for('aresos.chrome.page.v1')];for(const name of ['stop','arm','resume','drop']){try{api?.[name]?.('page-invented-epoch');}catch{}}document.querySelector('form').submit();};";
    } else if(kind==='matrix') {
      const token=url.searchParams.get('id'),route=url.searchParams.get('route')||'click',mode=url.searchParams.get('mode')||'word',word=url.searchParams.get('word')||'Send',label=url.searchParams.get('label')||'name';
      const action='/receive?case='+encodeURIComponent(token);
      const esc=value=>value.replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;');
      if(mode==='word'){
        const attrs={name:'',aria:'aria-label="'+esc(word)+'"',title:'title="'+esc(word)+'"',value:'value="'+esc(word)+'"',labelledby:'aria-labelledby="external"',label:'id="word-control"'};
        body='<textarea aria-label="Message">Matrix draft</textarea><button type="button" '+attrs[label]+'>'+esc(label==='name'?word:'Continue')+'</button><span id="external">'+esc(word)+'</span>'+(label==='label'?'<label for="word-control">'+esc(word)+'</label>':'');
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
        const functions=new Set();for(const key of Reflect.ownKeys(globalThis)){if(String(key).includes('aresos')){try{const object=globalThis[key];for(const property of Reflect.ownKeys(object||{})){const value=object[property];if(typeof value==='function')functions.add(value);}}catch{}}}
        document.querySelector('button').onclick=()=>{
          for(const fn of functions)for(const arg of ['forged',{operation:'forged',generation:'forged',approved:true}]){try{fn(arg,arg,arg,arg,arg,true);}catch{}}
          for(const type of ['aresos-reader-identity','aresos-page-step','aresos-dialog-origin','aresos-watch-root','message','aresos-page-call-v2']){
            try{dispatch.call(form,new CustomEvent(type,{bubbles:true,cancelable:true,detail:{id:'e1',kind:'native_submit',operation:'forged',generation:'forged',approved:true}}));}catch{}
          }
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
    res.setHeader('Content-Type','text/html');res.end(page(body,script));
  });
  await new Promise(resolve=>server.listen(8765,'0.0.0.0',resolve));
  const second=http.createServer((req,res)=>{res.setHeader('Content-Type','text/html');res.end(page('<input aria-label="Cross-site message" value="Cross-origin draft">'));});
  await new Promise(resolve=>second.listen(8766,'0.0.0.0',resolve));
  return {arrivals,close:()=>{server.close();second.close();}};
}
