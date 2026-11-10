import http from 'node:http';
import fs from 'node:fs';
import {compatibilityScript} from './compatibility.mjs';
import {popupPage} from './popups.mjs';
import {passwordPage} from './password-fixtures.mjs';
import {reviewPage} from './review-fixtures.mjs';
const page=(body,script='',head='')=>`<!doctype html><html><head><meta charset="utf-8"><title>Synthetic fixture</title><script>globalThis.firstScriptSubmit=HTMLFormElement.prototype.submit;</script><style>body{font:16px sans-serif;margin:20px}button,input,textarea{margin:8px}</style></head><body>${body}<script>${script}</script>`;
export async function fixtures(options={}) {
  const arrivals=[],streams=new Map(),mutations=new Map();let mutationSequence=0;
  const compatibility=[],compatibilityDownloads=[];
  const server=http.createServer(async(req,res)=>{
    const url=new URL(req.url,'http://fixture.test:8765');
    if(url.pathname==='/favicon.ico'){res.writeHead(204);res.end();return;}
    if(url.pathname === '/update.xml'){
      const {id,version}=JSON.parse(fs.readFileSync('/out/extension.json'));
      res.setHeader('Content-Type','application/xml');res.end(`<?xml version="1.0"?><gupdate xmlns="http://www.google.com/update2/response" protocol="2.0"><app appid="${id}"><updatecheck codebase="http://127.0.0.1:8765/extension.crx" version="${version}"/></app></gupdate>`);return;
    }
    if(url.pathname === '/extension.crx'){res.end(fs.readFileSync('/workspace/.work/20-package/own-extension.crx'));return;}
    if(url.pathname === '/download'){compatibilityDownloads.push(url.searchParams.get('id'));res.setHeader('Content-Disposition','attachment; filename="synthetic-'+url.searchParams.get('id')+'.txt"');res.setHeader('Content-Type','text/plain');res.end('Synthetic downloadable bytes');return;}
    if(url.pathname==='/compat-report'){let body='';for await(const part of req)body+=part;const value=JSON.parse(body);compatibility.push(value);fs.appendFileSync('/out/native-compatibility.jsonl',JSON.stringify(value)+'\n');res.end('ok');return;}
    if(url.pathname==='/tone.wav'){
      const wav=Buffer.alloc(44+16000);wav.write('RIFF',0);wav.writeUInt32LE(wav.length-8,4);wav.write('WAVEfmt ',8);wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);wav.writeUInt32LE(8000,24);wav.writeUInt32LE(16000,28);wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);wav.write('data',36);wav.writeUInt32LE(16000,40);for(let index=0;index<8000;index++)wav.writeInt16LE(Math.round(6000*Math.sin(2*Math.PI*220*index/8000)),44+index*2);res.setHeader('Content-Type','audio/wav');res.end(wav);return;
    }
    if(url.pathname==='/post-document'){
      let body='';for await(const part of req)body+=part;const record={time:Date.now(),url:req.url,method:req.method,body,host:req.headers.host};arrivals.push(record);fs.appendFileSync('/out/receiver.jsonl',JSON.stringify(record)+'\n');res.end(page('<button type="button">Continue</button>'));return;
    }
    if(url.pathname === '/events'){res.writeHead(200,{'Content-Type':'text/event-stream','Cache-Control':'no-cache'});res.write(': ready\n\n');const id=url.searchParams.get('id');streams.set(id,res);res.on('close',()=>{if(streams.get(id)===res)streams.delete(id);});return;}
    if(url.pathname === '/observe'){let body='';for await(const part of req)body+=part;fs.appendFileSync('/out/page-events.jsonl',body+'\n');res.end('observed');return;}
    if(url.pathname==='/mutation-ack'){const pending=mutations.get(url.searchParams.get('nonce'));if(pending)pending();res.writeHead(204);res.end();return;}
    if(url.pathname === '/receive'||url.pathname==='/'&&url.searchParams.has('field')&&url.searchParams.get('case')?.startsWith('submit-empty-')) {
      let body='';for await(const part of req)body+=part;
      const record={time:Date.now(),url:req.url,method:req.method,body,host:req.headers.host};arrivals.push(record);fs.appendFileSync('/out/receiver.jsonl',JSON.stringify(record)+'\n');
      res.end(page('<p>Received synthetic input</p>'));return;
    }
    if(url.pathname!=='/'){res.writeHead(404);res.end('Unknown fixture path');return;}
    const kind=url.searchParams.get('case') || 'compose';
    // Mutation channels belong to the current fixture document. Old SSEs must
    // not exhaust Chrome's six HTTP/1.1 connections and hide later receivers.
    if(!['draft-inner','password-inner'].includes(kind))for(const [id,stream]of streams){stream.end();streams.delete(id);}
    let body,script='';
    if(kind==='review-page'){const review=reviewPage(url);if(!review)throw Error('Unknown review fixture');({body,script}=review);}
    else if(['popup-opener','popup-child'].includes(kind)){const popup=popupPage(url);res.end(page(popup.body,popup.script));return;}
    else if(kind==='adapter-sites'){const site=(await import('./sites/fixture.mjs')).sitePage(url,req.headers.host);res.end(page(site.body,site.script));return;}
    else if(kind==='native-donor'){
      const id=url.searchParams.get('id');body='<p id="native-donor">Ordinary native donor</p><button type="button" style="position:fixed;inset:0;width:100vw;height:100vh">Open controlled page</button>';
      script="document.title='Native donor '+"+JSON.stringify(id)+";document.querySelector('button').onclick=()=>window.open('/?case=compose&id='+"+JSON.stringify(id)+",'native-root-'+"+JSON.stringify(id)+");fetch('/compat-report',{method:'POST',body:JSON.stringify({id:"+JSON.stringify(id)+",phase:'donor-ready'})});";
    }else if(kind==='stop-modal'){
      body='<form action="/receive?case=stop-modal" method="post" target="sink"><input name="draft" value="Saved"><button type="button" id="send">Send</button></form><button type="button" id="continue">Continue</button><iframe name="sink" hidden></iframe>';
      script="const cachedClick=HTMLElement.prototype.click;document.querySelector('#send').onclick=()=>fetch('/receive?case=stop-modal',{method:'POST'});document.querySelector('#continue').onclick=()=>confirm('Continue browsing?');globalThis.afterControlProbe=()=>cachedClick.call(document.querySelector('#send'));";
    }else if(kind==='preload-origin'){
      const id=url.searchParams.get('id');body='<form method="post" action="/receive?case='+id+'" target="sink"><input name="draft" value="Saved"><button type="button">Continue</button></form><iframe name="sink" hidden></iframe>';
      script="document.querySelector('button').onclick=()=>firstScriptSubmit.call(document.querySelector('form'));";
    }else if(kind==='preload-frame'){
      const id=url.searchParams.get('id'),origin=url.searchParams.get('cross')==='1'?'http://cross.test:8766':'';body='<iframe width="800" height="300" src="'+origin+'/?case=preload-origin&id='+id+'"></iframe>';
    }else if(kind==='preload-popup'){
      body='<button type="button">Open window</button>';script="document.querySelector('button').onclick=()=>window.open('http://popup.test:8766/?case=preload-origin&id=first-popup','_blank');";
    }else if(kind==='native-compat'){
      body='<button type="button" id="continue" style="position:fixed;inset:0;width:100vw;height:100vh;margin:0;z-index:99999">Continue</button>';script=compatibilityScript(url.searchParams.get('id'));
    }else if(kind==='take-post'){
      body='<form method="post" action="/post-document?case=taken-post"><button type="submit">Load POST</button></form>';
    }else if(kind==='take-state'){
      const id=url.searchParams.get('id'),mode=url.searchParams.get('mode');
      body='<button type="button" id="play">Play media</button><input aria-label="Draft" value="Saved"><button type="button" id="continue">Continue</button><audio loop src="/tone.wav"></audio><form method="post" action="/post-document?case='+id+'"><button type="submit">Load POST</button></form>';
      script=`fetch('/receive?case=loaded-${id}',{method:'POST'});${mode==='dirty'?"document.querySelector('input').value='Unsaved';":''}${mode==='blank-editor'?"const child=document.createElement('iframe');document.body.append(child);child.contentDocument.designMode='on';child.contentDocument.body.textContent='Unsaved iframe draft';":''}document.querySelector('#play').onclick=()=>{${mode==='detached-media'?"const media=new Audio('/tone.wav');media.loop=true;globalThis.fixtureMedia=media;return media.play().then(()=>fetch('/receive?case=playing-"+id+"',{method:'POST'}));":mode==='web-audio'?"const audio=new AudioContext(),oscillator=audio.createOscillator();oscillator.connect(audio.destination);oscillator.start();globalThis.fixtureMedia=audio;return audio.resume().then(()=>fetch('/receive?case=playing-"+id+"',{method:'POST'}));":"return document.querySelector('audio').play().then(()=>fetch('/receive?case=playing-"+id+"',{method:'POST'}));"}};`;
    } else if(kind==='features') {
      body='<form><input aria-label="First" name="first" value="Original first"><input aria-label="Second" name="second" value="Original second"><select name="choice" aria-label="Choice"><option value="a">First option</option><option value="b">Second option</option><option value="c" disabled>Disabled option</option></select><input type="hidden" name="hidden" value="Hidden field"><input type="checkbox" name="tick" aria-label="Tick"></form><a href="/download?id='+url.searchParams.get('id')+'">Download fixture</a><p>Findable synthetic paragraph</p>';
    } else if(kind==='compose') {
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
    } else if(kind==='action-matrix') {
      const id=url.searchParams.get('id'),mode=url.searchParams.get('mode'),tag=url.searchParams.get('tag')||'textarea';
      const action='/receive?case='+encodeURIComponent(id);
      if(mode==='submit'){
        const button='<button'+(tag==='default'?'':' type="submit"')+(tag==='external'?' form="target-form"':'')+(tag==='override'?' formaction="'+action+'" formmethod="post" formenctype="text/plain" formtarget="sink"':tag==='empty'?' formaction="" formmethod="" formenctype="" formtarget="sink"':tag==='invalid'?' formaction="'+action+'" formmethod="invalid" formenctype="invalid" formtarget="sink"':'')+'>Continue</button>';
        body=(tag==='external'?button:'')+'<form id="target-form" method="'+(tag==='override'?'get':'post')+'" action="'+(['override','empty','invalid'].includes(tag)?'/receive?case=unapproved-'+id:action)+'" target="sink"><input name="field" aria-label="Form field" value="Current">'+(['empty','invalid'].includes(tag)?'<input type="hidden" name="case" value="'+id+'">':'')+(tag==='external'?'':button)+'</form><iframe name="sink" hidden></iframe>';
        if(tag==='clobbered')body=body.replace('</form>',['elements','action','method','enctype','target'].map(name=>'<input name="'+name+'" value="Synthetic clobber">').join('')+'</form>');
      }
      else if(mode==='compose'){
        body=(tag==='div'?'<div contenteditable="true" aria-label="Compose">Existing draft</div>':'<'+tag+' aria-label="Compose" value="Existing draft">Existing draft</'+tag+'>');
        script=`document.querySelector('[aria-label=Compose]').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();fetch(${JSON.stringify(action)},{method:'POST',body:'compose'});}};`;
      } else if(mode==='delete'){
        body='<article tabindex="0" aria-label="Selected item">Synthetic selected item</article>';
        script=`document.querySelector('article').onkeydown=e=>{if(['Delete','Backspace'].includes(e.key)){e.preventDefault();fetch(${JSON.stringify(action)},{method:'POST',body:'delete'});}};`;
      } else if(mode==='javascript'){
        body='<a href="javascript:void(0)">Delete</a>';
        script=`document.querySelector('a').onclick=()=>fetch(${JSON.stringify(action)},{method:'POST',body:'javascript link'});`;
      } else if(mode==='badlink'){
        body='<a href="'+url.searchParams.get('url').replaceAll('&','&amp;').replaceAll('"','&quot;')+'">Read more</a>';
        script=`document.querySelector('a').onclick=()=>fetch(${JSON.stringify(action)},{method:'POST',body:'must never click'});`;
      } else if(mode==='conservative'){
        body='<button type="button" id="plain">Continue</button><textarea aria-label="Text">Existing draft</textarea><select aria-label="Choice"><option value="a">A</option><option value="b">B</option></select><input type="checkbox" aria-label="Tick"><a href="'+action+'" target="sink">Read more</a><form role="search" action="'+action+'" target="sink"><input type="hidden" name="case" value="'+id+'"><input type="search" name="q" value="Search" aria-label="Search"><button>Search now</button></form><iframe name="sink" hidden></iframe>';
        script=`const send=()=>fetch(${JSON.stringify(action)},{method:'POST',body:'conservative'});document.querySelector('#plain').onclick=send;document.querySelector('select').onchange=send;document.querySelector('[type=checkbox]').onchange=send;`;
      } else if(mode==='free'){
        body='<form role="search" action="'+action+'" target="sink"><input type="hidden" name="case" value="'+id+'"><input type="search" name="q" aria-label="Search"><button>Continue</button></form><textarea aria-label="Text">Initial</textarea><select aria-label="Choice"><option value="a">A</option><option value="b">B</option></select><input type="checkbox" aria-label="Tick"><a target="sink" href="'+action+'">Read more</a><iframe name="sink" hidden></iframe>';
        script=`document.querySelector('textarea').onkeydown=e=>{if(e.key==='Enter')fetch('/receive?case=unexpected-enter',{method:'POST'});};`;
      }
    } else if(kind==='excluded-form') {
      const id=url.searchParams.get('id'),method=url.searchParams.get('method'),override=url.searchParams.get('override')==='true',destination='http://approval.test:8765/receive?case='+encodeURIComponent(id);
      body='<form role="'+(method==='get'?'search':'form')+'" action="'+(override?'/receive?case=wrong-'+id:destination)+'" method="'+method+'" target="_blank"><input type="hidden" name="case" value="'+id+'"><input type="search" name="q" value="Synthetic query" aria-label="Search"><button type="submit"'+(override?' formaction="'+destination+'"':'')+'>Continue</button></form>';
      script=`document.querySelector('button').onclick=()=>fetch('/receive?case=handler-'+${JSON.stringify(id)},{method:'POST'});`;
    } else if(kind==='submitter-hijack') {
      const id=url.searchParams.get('id'),mode=url.searchParams.get('mode');
      body='<button type="button" id="continue">Continue</button><form action="/receive?case='+id+'" method="post" target="sink"><input aria-label="Form field" name="field" value="Current"><button type="submit" name="which" value="bound">Bound button</button><button type="submit" name="which" value="other">Other button</button></form><iframe name="sink" hidden></iframe>';
      script=`const form=document.querySelector('form'),other=form.querySelector('[value=other]');${mode==='implicit'?"form.querySelector('input').onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();form.requestSubmit(other);}};":"document.querySelector('#continue').onclick=()=>form.requestSubmit();form.onsubmit=event=>{if(!event.submitter){event.preventDefault();queueMicrotask(()=>form.requestSubmit(other));}};"}`;
    } else if(kind==='resume-matrix') {
      const id=url.searchParams.get('id'),mode=url.searchParams.get('mode');
      body='<button type="button">Continue</button><form action="/receive?case='+id+'" method="post" target="sink"><input name="value" required '+(mode==='invalid'?'':'value="valid"')+'><button type="submit">Submit</button></form><form id="other" action="/receive?case=other-'+id+'" method="post" target="sink"><input name="value" value="other"></form><iframe name="sink" hidden></iframe>';
      script=`const form=document.querySelector('form');document.querySelector('button').onclick=()=>form.${mode==='invalid'?'submit()':'requestSubmit()'};let count=0;form.onsubmit=function handler(event){fetch('/receive?case=handler-'+${JSON.stringify(id)},{method:'POST'});${mode==='double'?"event.preventDefault();form.submit();form.submit();":mode==='other'?"document.querySelector('#other').submit();":mode==='nested'?"if(++count===1)handler(event);form.submit();":''}};`;
    } else if(kind==='cross-draft') {
      const mode=url.searchParams.get('mode'),id=url.searchParams.get('id');
      body='<button type="button">Send</button>'+(mode==='empty'?'':mode==='oversized'?'<textarea aria-label="Long draft">'+('Synthetic long draft '.repeat(1200))+'</textarea>':'<iframe src="http://second.test:8766/?case=draft-inner&id='+id+'"></iframe>');
      script=`document.querySelector('button').onclick=()=>fetch('/receive?case='+${JSON.stringify(id)},{method:'POST',body:'sent'});`;
    } else if(kind==='draft-inner') {
      body='<textarea aria-label="Frame draft">Existing cross-frame draft</textarea>';
    } else if(kind==='fresh-activation') {
      const id=url.searchParams.get('id'),cancel=url.searchParams.get('cancel')==='true';
      body='<button type="button">Continue</button><a target="'+(url.searchParams.get('target')==='self'?'_self':'sink')+'" href="/receive?case='+id+'">Delete</a><iframe name="sink" hidden></iframe>';
      script=`document.querySelector('button').onclick=()=>{const donor=opener;if(!donor?.document.getElementById('native-donor'))throw Error('Ordinary native donor is missing');const frame=donor.document.createElement('iframe');frame.sandbox='allow-same-origin';donor.document.body.append(frame);const raw=frame.contentWindow.EventTarget.prototype.dispatchEvent,hasPrototype=Object.prototype.hasOwnProperty.call(raw,'prototype'),ownRealm=frame.contentWindow.EventTarget!==EventTarget,native=Function.prototype.toString.call(raw).includes('[native code]')&&!hasPrototype;frame.remove();fetch('/observe',{method:'POST',body:JSON.stringify({id:${JSON.stringify(id)},phase:'fallback-source',native,hasPrototype,ownRealm})});if(!native)throw Error('Fixture did not obtain a native dispatch function');raw.call(document.querySelector('a'),new MouseEvent('click',{bubbles:true,cancelable:${cancel}}));};document.querySelector('a').onclick=()=>fetch('/receive?case=handler-'+${JSON.stringify(id)},{method:'POST'});`;
    } else if(kind==='native-child') {
      const id=url.searchParams.get('id');body='<p>Native confirmation opener frame</p>';
      script=`onmessage=()=>{if(confirm('Delete branch fixture-repository / branch-1?'))fetch('/receive?case='+${JSON.stringify(id+'-Delete branch')},{method:'POST',body:'confirmed from frame'});};`;
    } else if(kind==='native-confirm') {
      const id=url.searchParams.get('id'),text=url.searchParams.get('text')||'Delete this item?',mode=url.searchParams.get('mode')||'confirm';
      body='<button type="button">Continue</button>'+(mode==='form'?'<form action="/receive?case='+id+'" method="post" target="sink"><input name="request" value="Current"><input type="hidden" name="hidden" value="Bound after dialog"></form><iframe name="sink" hidden></iframe>':'');
      script=`document.querySelector('button').onclick=()=>{if(${mode==='prompt'?'prompt':mode==='alert'?'(value=>{alert(value);return true;})':'confirm'}(${JSON.stringify(text)}))${mode==='form'?"document.querySelector('form').submit()":"fetch('/receive?case='+"+JSON.stringify(id)+",{method:'POST',body:'confirmed'})"};};`;
    } else if(kind==='owner-timer') {
      const id=url.searchParams.get('id'),variant=url.searchParams.get('variant');
      body='<button type="button" id="continue">Continue</button><form id="owner-form" action="/receive?case='+id+'" method="post" target="sink"><input id="owner" name="draft" required value=""><button id="first">Submit</button><button id="second">Submit another</button></form><form id="other-form" action="/receive?case='+id+'" method="post" target="sink"><input name="draft" value="Another form"><button id="other">Submit</button></form><iframe name="sink" hidden></iframe>';
      script=`document.querySelector('#continue').onclick=()=>{fetch('/receive?case=task-start',{method:'POST',body:${JSON.stringify(id)}});setTimeout(()=>{document.querySelector('#owner').value='Property repair';${variant==='other-form'?"document.querySelector('#other-form').requestSubmit(document.querySelector('#other'))":`document.querySelector('#owner-form').requestSubmit(document.querySelector('#${variant==='other-submitter'?'second':'first'}'))`};},230);};`;
    } else if(kind==='owner-task') {
      const id=url.searchParams.get('id')||'owner-task',delay=Number(url.searchParams.get('delay')||100),replay=url.searchParams.get('replay')==='1',busy=Number(url.searchParams.get('busy')||0);
      body='<button type="button" id="continue">Continue</button><form action="/receive?case='+id+'" method="post" target="sink"><input id="owner" aria-label="Owner input" name="source" value="owner task"></form><iframe name="sink" hidden></iframe>';
      script=`const observe=(phase,event)=>fetch('/observe',{method:'POST',body:JSON.stringify({id:${JSON.stringify(id)},phase,time:Date.now(),trusted:event?.isTrusted,eventPhase:event?.eventPhase})});const form=document.querySelector('form');document.querySelector('#continue').onclick=()=>{fetch('/receive?case=task-start',{method:'POST',body:${JSON.stringify(id)}});const until=performance.now()+${busy};while(performance.now()<until){};};
        document.querySelector('#owner').onkeydown=event=>{if(event.key==='Enter')event.preventDefault();};document.querySelector('#owner').${replay?'onkeyup':'onkeydown'}=event=>{if(event.key==='Enter'){observe('owner-handler',event);event.preventDefault();form.submit();if(event.isTrusted)setTimeout(()=>{observe('delayed-handler',event);${replay?"document.querySelector('#owner').dispatchEvent(event)":'form.submit()'}},${delay});}};`;
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
    } else if(kind==='password-matrix'||kind==='password-inner') {
      ({body,script}=passwordPage(kind==='password-inner'));
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
      const confirmation=url.searchParams.get('confirm');
      if(['frame','site'].includes(confirmation))body+='<iframe src="http://'+(confirmation==='site'?'second':site)+'.test:8765/?case=native-child&id='+token+'"></iframe>';
      script=`const send=label=>fetch('/receive?case='+encodeURIComponent(${JSON.stringify(token)}+'-'+label),{method:'POST',body:JSON.stringify({label,fields:[...document.querySelectorAll('input,textarea')].map(field=>({name:field.name||field.getAttribute('aria-label'),value:field.value}))})});
        for(const button of document.querySelectorAll('button'))button.onclick=()=>{if(button.textContent==='Delete branch'){${['frame','site'].includes(confirmation)?"document.querySelector('iframe').contentWindow.postMessage('ask','*');return;":'if(!'+(confirmation==='prompt'?'prompt':'confirm')+'('+JSON.stringify(confirmation==='text'?'Delete another branch?':'Delete branch '+context+'?')+'))return;'+(confirmation==='twice'?'if(!confirm('+JSON.stringify('Delete branch '+context+'?')+'))return;':'')}}send(button.textContent);};
        for(const field of document.querySelectorAll('textarea'))field.onkeydown=event=>{if(event.key==='#' && ${JSON.stringify(site)}==='gmail'){event.preventDefault();send('Delete shortcut');}if(event.key==='Enter' && (${JSON.stringify(site)}!=='gmail'||event.ctrlKey||event.metaKey)){event.preventDefault();send('Enter');}};`;
    } else if(kind==='matrix') {
      const token=url.searchParams.get('id'),route=url.searchParams.get('route')||'click',mode=url.searchParams.get('mode')||'word',word=url.searchParams.get('word')||'Send',label=url.searchParams.get('label')||'name';
      const action='/receive?case='+encodeURIComponent(token);
      const esc=value=>value.replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;');
      if(mode==='word'){
        const attrs={name:'',aria:'aria-label="'+esc(word)+'"',title:'title="'+esc(word)+'"',value:'value="'+esc(word)+'"',labelledby:'aria-labelledby="external"',hidden_labelledby:'aria-labelledby="external"',role:'role="'+esc(word)+'"',formaction:'',label:'id="word-control"'};
        body='<textarea aria-label="Message">Matrix draft</textarea><button type="button" '+attrs[label]+'>'+esc(label==='name'?word:'Continue')+'</button><span id="external" '+(label==='hidden_labelledby'?'hidden':'')+'>'+esc(word)+'</span>'+(label==='label'?'<label for="word-control">'+esc(word)+'</label>':'');
        if(label==='formaction')body=body.replace('<button','<form method="post" action="'+action+'&verb='+encodeURIComponent(word)+'"><button').replace('</button>','</button></form>');
        script=`let lastKey;document.querySelector('button').onkeydown=event=>{lastKey=event.key===' '?'Space':event.key;};document.querySelector('button').onclick=event=>{const route=event.detail===0?lastKey:'click';fetch('/receive?case='+encodeURIComponent(${JSON.stringify(token)}+'-'+route),{method:'POST',body:'word'});};`;
      } else if(mode==='stopped'){
        body='<form action="'+action+'" method="post" target="sink"><input name="content" value="bound"><button type="submit">Submit</button></form><button type="button" id="trigger">Continue</button><input aria-label="Trigger text"><select aria-label="Trigger choice"><option value="a">A</option><option value="b">B</option></select><input type="checkbox" aria-label="Trigger check"><iframe name="sink" hidden></iframe>';
        const submit=url.searchParams.get('submit')||'native';
        const step=submit==='native'?'form.submit()':submit==='event'?'form.requestSubmit()':submit==='button'?"form.querySelector('button').click()":'form.requestSubmit()';
        script=`const form=document.querySelector('form'),trigger=document.querySelector('#trigger'),field=document.querySelector('[aria-label="Trigger text"]'),choice=document.querySelector('select'),check=document.querySelector('[type=checkbox]');
          const step=()=>{${step}};
          ${route==='click'?'trigger.onclick=step':route==='key'?'trigger.onkeydown=step':route==='fill'?'field.oninput=step':route==='select'?'choice.onchange=step':'check.onchange=step'};`;
      } else if(mode==='activation'||mode==='conservative-script'){
        body='<button type="button">Continue</button><input aria-label="Trigger text"><select aria-label="Trigger choice"><option value="a">A</option><option value="b">B</option></select><input type="checkbox" aria-label="Trigger check"><a target="sink" href="'+action+'" aria-labelledby="external">Continue</a><textarea aria-label="Message">Existing draft</textarea><span id="external">'+(mode==='conservative-script'?'Read more':url.searchParams.get('word')||'Delete')+'</span><iframe name="sink" hidden></iframe>';
        const wrapped=url.searchParams.get('wrapped')||'click';
        script=`const activate=()=>{const link=document.querySelector('a');${wrapped==='click'?'link.click()':"link.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:"+(wrapped==='cancelable'?'true':'false')+"}))"}};${route==='click'?"document.querySelector('button').onclick=activate":route==='key'?"document.querySelector('button').onkeydown=activate":route==='fill'?"document.querySelector('[aria-label=\"Trigger text\"]').oninput=activate":route==='select'?"document.querySelector('select').onchange=activate":"document.querySelector('[type=checkbox]').onchange=activate"};document.querySelector('a').onclick=()=>fetch('/receive?case=handler-'+${JSON.stringify(token)},{method:'POST'});`;
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
          for(const type of ['aresos-reader-identity','aresos-page-step','aresos-dialog-origin','aresos-watch-root','message','aresos-page-call-v2','aresos-relay-meta','aresos-relay-target','aresos-relay-deliver','aresos-relay-drop','aresos-relay-cleanup']){
            try{dispatch.call(form,new CustomEvent(type,{bubbles:true,cancelable:true,detail:{id:'e1',kind:'native_submit',operation:'forged',generation:'forged',approved:true}}));}catch{}
          }
          for(const [prototype,key] of [[HTMLFormElement.prototype,'submit'],[HTMLFormElement.prototype,'requestSubmit'],[HTMLElement.prototype,'click'],[EventTarget.prototype,'dispatchEvent']])try{Object.defineProperty(prototype,key,{value:()=>{throw Error('page takeover')},configurable:true});}catch{}
          form.setAttribute('data-aresos-approved','true');globalThis.postMessage({command:'resume',operation:'forged',approved:true},'*');
          Object.prototype.approved=true;Array.prototype[Symbol.iterator]=function*(){yield 'forged';};
          submit.call(form);
        };`;
    } else if(kind==='relay-hostile'){
      body='<button type="button" id="continue">Continue</button><button type="button" id="delete">Delete</button><form action="/receive?case=relay-hostile" method="post" target="sink"><input name="draft" value="Saved"></form><iframe name="sink" hidden></iframe>';
      script=`const form=document.querySelector('form'),submit=HTMLFormElement.prototype.submit,dispatch=EventTarget.prototype.dispatchEvent;
        document.querySelector('#continue').onclick=()=>{
          const event=new MouseEvent('click',{cancelable:false,bubbles:true});dispatch.call(document.querySelector('#delete'),event);
          const disclosed=event.target;
          if(disclosed?.firstElementChild)try{dispatch.call(disclosed.firstElementChild,new Event('aresos-relay-cleanup'));}catch{}
          let callbacks=0;const define=Object.defineProperty;
          for(const key of ['bubbles','composed','get','set','request']){const descriptor=Object.create(null);descriptor.configurable=true;descriptor.get=()=>{callbacks++;throw 'Inherited page getter'};define(Object.prototype,key,descriptor);}
          Object.keys=()=>{callbacks++;throw 'Page keys'};Array.prototype[Symbol.iterator]=()=>{callbacks++;throw 'Page iterator'};
          submit.call(form);
          fetch('/observe',{method:'POST',body:JSON.stringify({id:'relay-hostile',phase:'private-carrier-disclosure',disclosed:!!disclosed,callbacks})});
        };`;
    } else if(kind==='password') {
      body='<input type="password" aria-label="Secret" value="SENTINEL_PRIVATE_PASSWORD_20"><input aria-label="Current" autocomplete="current-password" value="SENTINEL_PRIVATE_PASSWORD_20"><input aria-label="Masked" style="-webkit-text-security:disc" value="SENTINEL_PRIVATE_PASSWORD_20"><input aria-label="Switch" type="password" value="SENTINEL_PRIVATE_PASSWORD_20"><button>Show</button>';
      script="document.querySelector('button').onclick=()=>document.querySelector('[aria-label=Switch]').type='text';";
    } else if(kind==='residual') {
      body='<button aria-label="">●</button><textarea aria-label="Autosave"></textarea>';
      script="document.querySelector('button').onclick=()=>fetch('/receive?case=residual-click',{method:'POST',body:'ordinary click'});document.querySelector('textarea').oninput=e=>fetch('/receive?case=residual-autosave',{method:'POST',body:e.target.value});";
    } else {res.statusCode=404;res.end('Unknown synthetic fixture');return;}
    const mutationId=['review-page','binding','page-dialog','upload','draft-inner','stop-modal'].includes(kind)||kind==='site'&&url.searchParams.get('id')?.startsWith('adapter-bind-')?url.searchParams.get('id'):null;
    if(mutationId)script+=`;new EventSource('/events?id='+${JSON.stringify(mutationId)}).onmessage=event=>{
      const mutation=JSON.parse(event.data),change=mutation.change,form=document.querySelector('form'),button=document.querySelector('button');
      if(change==='review-change')globalThis.reviewChange();
      if(change==='label')button.textContent='Changed label';
      if(change==='element')button.replaceWith(button.cloneNode(true));
      if(change==='visible')document.querySelector('[name=visible]').value='Changed visible';
      if(change==='hidden')document.querySelector('[name=hidden]').value='Changed hidden';
      if(change==='action')form.action='/receive?case=changed-destination';
      if(change==='method')form.method='get';
      if(change==='encoding')form.enctype='text/plain';
      if(change==='target')form.target='_self';
      if(change==='text'){const field=document.querySelector('[contenteditable],textarea');if(field.matches('input,textarea'))field.value='Changed draft';else field.textContent='Changed draft';}
      if(change==='preview')document.querySelector('[aria-label="Message preview"]').textContent='Changed read-only preview';
      if(change==='dialog')document.querySelector('[role=alertdialog] p').textContent='Delete another item?';
      if(change==='document'){location.href=location.href+'&generation=changed&mutation_nonce='+encodeURIComponent(mutation.nonce);return;}
      if(change==='account'){const account=document.querySelector('[name=from],[aria-label="Signed in as"]');if('value'in account)account.value='Changed account';else account.textContent='Changed account';}
      if(change==='recipient')document.querySelector('[name=to]').value='other@example.invalid';
      if(change==='chat')document.querySelector('[aria-label="Chat name"]').textContent='Changed chat';
      if(change==='owner-native-click')globalThis.afterControlProbe();
      fetch('/mutation-ack?nonce='+encodeURIComponent(mutation.nonce),{keepalive:true});
    };if(new URL(location.href).searchParams.has('mutation_nonce'))fetch('/mutation-ack?nonce='+encodeURIComponent(new URL(location.href).searchParams.get('mutation_nonce')),{keepalive:true});`;
    res.setHeader('Content-Type','text/html');res.setHeader('Cache-Control','no-store');res.end(page(body,script));
  });
  await new Promise(resolve=>server.listen(options.port??8765,'0.0.0.0',resolve));
  const second=http.createServer(server.listeners('request')[0]);
  await new Promise(resolve=>second.listen(options.secondPort??8766,'0.0.0.0',resolve));
  return {arrivals,compatibility,compatibilityDownloads,port:server.address().port,mutate:async(id,change)=>{
    const deadline=Date.now()+5000;
    while(!streams.has(id)&&Date.now()<deadline)await new Promise(resolve=>setTimeout(resolve,10));
    const stream=streams.get(id);if(!stream)throw Error('Mutation fixture stream is not connected: '+id);
    const nonce=String(++mutationSequence);
    await new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>{mutations.delete(nonce);reject(Error('Mutation did not complete: '+id+' '+change));},5000);
      mutations.set(nonce,()=>{clearTimeout(timer);mutations.delete(nonce);resolve();});
      stream.write('data: '+JSON.stringify({change,nonce})+'\n\n');
    });
  },close:()=>{for(const stream of streams.values())stream.end();server.close();second.close();}};
}
