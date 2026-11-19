// Brief 28a, groups 14 and 15 in the browser: the fixture pages of act-matrix.mjs,
// served by fixture.mjs as /?case=act-<name>&id=<id>. Invented content only.
// Every page reports what reaches it to the fixture's receiver
// (/receive?case=act-<what>-<id>), so a case counts inputs and sends there:
// `input` events with the field and its value, clicks, and form submissions.
// A page with an id also takes the fixture's mutations (fixture.mjs: a change
// named act-<change> calls globalThis.actChange).
import {efficiencyPage,HOSTILE} from './efficiency-fixtures.mjs';

export const ACT_MARK='Wq4Lk8Zr2Np6Xt0Bv3Mc7Hd9Jf1Gs5Ya8Ue2Ko6i';
export const STAGE_MS=3500,LONG_NOTE=5000,LARGE_FIELDS=120;
const escape=value=>String(value).replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;');
const inline=value=>JSON.stringify(value).replaceAll('<','\\u003c');
const titled=title=>'document.title='+inline(title)+';';
// The page's reporter: what reached it, with the page's own clock.
const reporter=id=>'const id='+inline(id)+',report=(what,body={})=>fetch("/receive?case="+encodeURIComponent("act-"+what+"-"+id),{method:"POST",body:JSON.stringify({...body,at:Date.now()})});';
const inputs='document.addEventListener("input",event=>report("input",{field:event.target.name||event.target.getAttribute("aria-label"),value:event.target.value}),true);';
const clicks=(selector,what)=>'for(const node of document.querySelectorAll('+inline(selector)+'))node.addEventListener("click",()=>report('+inline(what)+',{name:node.textContent}));';
export const actUrl=(name,id,query='')=>'http://fixture.test:8765/?case=act-'+name+'&id='+encodeURIComponent(id)+query;
// The long value the fingerprint case changes in its last character.
export const longNote=()=>Array.from({length:LONG_NOTE},(_,index)=>'abcdefghij'[index%10]).join('');

function steps(id){
  // Fills outside a form, a Send that asks (its form posts to act-send), the select of
  // "the steps as defined", a box, and a dialog the page opens on its own.
  const fruit='<label>Fruit <select name="fruit"><option value="a">Apple</option><option value="b">Banana  split</option>'
    +'<option value="c" disabled>Cherry</option><option value="d">Twin</option><option value="e">Twin</option></select></label>';
  return {body:'<h1>Steps</h1><label>Alpha <input name="alpha"></label><label>Beta <input name="beta"></label>'
    +'<form method="post" action="/receive?case=act-send-'+escape(id)+'" target="sink"><label>Gamma <input name="gamma"></label><button type="submit">Send</button></form>'
    +'<label>Delta <input name="delta"></label><label>Epsilon <input name="epsilon"></label>'+fruit
    +'<label><input type="checkbox" name="extra"> Extra</label><button type="button" id="later">Notice later</button><button type="button" id="draft">Load draft</button><iframe name="sink" hidden></iframe>',
    script:titled('Steps')+reporter(id)+inputs
      +'document.querySelector("#later").onclick=()=>setTimeout(()=>alert("Unseen notice"),3000);'
      +'document.querySelector("#draft").onclick=()=>{document.querySelector("[name=epsilon]").value="Page draft";};'};
}

function f4(id){
  // F4 (efficiency-fixtures.mjs) as it is, with its inputs reported, and four changes of the
  // Country list while an approval waits: an unchosen option renamed, one given another value,
  // one removed and another added (still 200), the chosen option's value under the same label.
  const page=efficiencyPage(new URL('http://fixture.test:8765/?case=efficiency-f4&id='+encodeURIComponent(id)));
  return {body:page.body,script:page.script+reporter(id)+inputs
    +'globalThis.actChange=change=>{const list=document.querySelector("select[name=country]");'
    +'if(change==="act-rename")list.options[50].textContent="Country 50 renamed";'
    +'if(change==="act-revalue")list.options[60].value="c60x";'
    +'if(change==="act-swap"){list.options[70].remove();const option=document.createElement("option");option.value="c200";option.textContent="Country 200";list.append(option);}'
    +'if(change==="act-chosen")list.options[7].value="c7x";};'};
}

function large(id,mode){
  // Too large to ask about: 120 short fields, or a textarea of 5,000 characters. Start makes
  // the page submit the 120-field form itself.
  const action='/receive?case=act-large-'+escape(id);
  const fields=mode==='text'?'<label>Body <textarea name="body">'+escape(longNote())+'</textarea></label>'
    :Array.from({length:LARGE_FIELDS},(_,index)=>'<label>Item '+index+' <input name="item'+index+'" value="v'+index+'"></label>').join('');
  return {body:'<h1>Large form</h1><form method="post" action="'+action+'" target="sink">'+fields+'<button type="submit">Send</button></form>'
    +'<button type="button" id="start">Start</button><iframe name="sink" hidden></iframe>',
    script:titled('Large form')+reporter(id)+'document.querySelector("#start").onclick=()=>document.querySelector("form").requestSubmit();'};
}

function far(id,mode){
  // Elements 10,000 pixels below the fold and in a scrolled inner box; each reports what reaches it.
  const spacer='<div style="height:10000px">Spacer</div>';
  if(mode==='scroll'){
    // A page that submits a form from its scroll handler, once, when the scroll comes.
    return {body:'<h1>Scroll sender</h1><form method="post" action="/receive?case=act-scroll-'+escape(id)+'" target="sink"><input name="note" value="Scrolled"></form>'
      +spacer+'<button type="button" id="go">Far go</button><iframe name="sink" hidden></iframe>',
      script:titled('Scroll sender')+reporter(id)+clicks('#go','go')
        +'let sent=false;addEventListener("scroll",()=>{if(!sent){sent=true;document.querySelector("form").requestSubmit();}});'};
  }
  return {body:'<h1>Far page</h1><button type="button" id="top">Top button</button>'+spacer
    +'<button type="button" id="far">Far button</button><label>Far field <input name="far"></label><label><input type="checkbox" name="tick" id="tick"> Far tick</label>'
    +'<div aria-label="Inner box" style="height:120px;overflow:auto"><div style="height:2000px">Inner spacer</div><button type="button" id="inner">Inner button</button></div>'
    +'<form method="post" action="/receive?case=act-farsend-'+escape(id)+'" target="sink"><input name="note" value="Far"><button type="submit">Send far</button></form><iframe name="sink" hidden></iframe>',
    script:titled('Far page')+reporter(id)+inputs+clicks('#far,#inner,#top','click')
      +'document.querySelector("#tick").addEventListener("change",event=>report("tick",{checked:event.target.checked}));'};
}

function fingerprint(id){
  // Group 14's fingerprint cases. Each "change" button makes the page change one other element
  // the way a page does it; act-matrix.mjs clicks it and then acts on that element in one list.
  const long=longNote();
  return {body:'<h1>Fingerprints</h1>'
    +'<p><a id="link" href="/receive?case=act-fplink-'+escape(id)+'&v=1">Report</a></p>'
    +'<label>Plan list <select id="plan" name="plan"><option value="a" selected>Alpha plan</option><option value="b">Beta plan</option><option value="c">Gamma plan</option></select></label>'
    +'<label><input type="checkbox" id="agree" name="agree"> Agree</label>'
    +'<button type="button" id="menu" aria-haspopup="menu" aria-expanded="false">Menu</button>'
    +'<label>Long note <textarea id="note" name="note">'+escape(long)+'</textarea></label>'
    +'<button type="button" id="later" disabled>Later</button>'
    +'<label>Code box <input id="code" name="code"></label>'
    +'<div id="mover-box"><button type="button" id="mover">Mover</button></div>'
    +'<ul aria-label="Rows"><li id="row">Item: Apple <button type="button" id="open">Open</button></li></ul>'
    +['Change path','Change query','Change options','Tick it','Expand menu','Change end','Enable','Require','Move','Swap row'].map((name,index)=>'<button type="button" class="change" data-change="'+index+'">'+name+'</button>').join(''),
    script:titled('Fingerprints')+reporter(id)+inputs+clicks('#link,#menu,#later,#mover,#open','click')
      +'document.querySelector("#agree").addEventListener("change",event=>report("tick",{checked:event.target.checked}));'
      +'document.querySelector("#plan").addEventListener("change",event=>report("plan",{value:event.target.value}));'
      +'const changes=['
      +'()=>{document.querySelector("#link").href="/other/receive?case=act-fplink-"+id+"&v=1";},'
      +'()=>{document.querySelector("#link").href="/receive?case=act-fplink-"+id+"&v=2";},'
      +'()=>{const plan=document.querySelector("#plan");plan.options[2].remove();const option=document.createElement("option");option.value="d";option.textContent="Delta plan";plan.append(option);},'
      +'()=>{document.querySelector("#agree").checked=true;},'
      +'()=>{document.querySelector("#menu").setAttribute("aria-expanded","true");},'
      +'()=>{const note=document.querySelector("#note");note.value=note.value.slice(0,-1)+"Z";},'
      +'()=>{document.querySelector("#later").disabled=false;},'
      +'()=>{const code=document.querySelector("#code");code.required=true;code.setAttribute("aria-invalid","true");},'
      +'()=>{document.querySelector("#mover-box").style.marginTop="300px";},'
      +'()=>{document.querySelector("#row").firstChild.textContent="Item: Pear ";}];'
      +'for(const node of document.querySelectorAll(".change"))node.onclick=()=>changes[Number(node.dataset.change)]();'};
}

function hostile(id,text){
  // Group 14's hostile text in a change report and in a stale present line.
  return {body:'<h1>Hostile change</h1><p id="status">Status plain</p><button type="button" id="target">Target</button>'
    +'<button type="button" id="rename-status">Rename status</button><button type="button" id="rename-target">Rename target</button>',
    script:titled('Hostile change')+reporter(id)+clicks('#target','click')+'const hostile='+inline(text)+';'
      +'document.querySelector("#rename-status").onclick=()=>{document.querySelector("#status").textContent=hostile;};'
      +'document.querySelector("#rename-target").onclick=()=>{document.querySelector("#target").setAttribute("aria-label",hostile);};'};
}

function look(id,mode){
  if(mode==='landed')return {body:'<h1>Landed page</h1><p>The page loaded another document.</p>',script:titled('Landed')};
  // A submission the page starts while handling a click, a dialog and a new document during a wait.
  return {body:'<h1>Look</h1><form method="post" action="/receive?case=act-look-'+escape(id)+'" target="sink"><input name="subject" value="Held"></form>'
    +'<button type="button" id="start">Start</button><label>Next field <input name="next"></label>'
    +'<button type="button" id="arm-dialog">Arm dialog</button><button type="button" id="arm-load">Arm load</button><iframe name="sink" hidden></iframe>',
    script:titled('Look')+reporter(id)+inputs
      +'document.querySelector("#start").onclick=()=>setTimeout(()=>document.querySelector("form").requestSubmit(),300);'
      +'document.querySelector("#arm-dialog").onclick=()=>setTimeout(()=>alert("Look notice"),1500);'
      +'document.querySelector("#arm-load").onclick=()=>setTimeout(()=>{location.href="/?case=act-look&mode=landed&id="+encodeURIComponent(id);},1500);'};
}

function loaded(id,mode){
  // "Loaded": a load stamp that changes only with a new document, a fragment far below, a
  // single-page view switched by pushState, and a page that never goes quiet.
  if(mode==='busy')return {body:'<h1>Busy page</h1><p>Busy ready</p><p id="tick">0</p>',
    script:titled('Busy')+'setInterval(()=>{document.querySelector("#tick").textContent=String(Date.now());},50);'};
  return {body:'<h1>Loaded page</h1><p id="stamp"></p><p id="view">View 1</p><button type="button" id="next">Go to view 2</button>'
    +'<div style="height:3000px">Spacer</div><h2 id="part2">Part two</h2>',
    script:titled('Loaded')+'document.querySelector("#stamp").textContent="Load stamp "+Math.random().toString(36).slice(2,10);'
      +'const render=()=>{document.querySelector("#view").textContent=new URL(location.href).searchParams.get("view")==="2"?"View 2":"View 1";};'
      +'document.querySelector("#next").onclick=()=>{const url=new URL(location.href);url.searchParams.set("view","2");history.pushState({view:2},"",url);render();};'
      +'addEventListener("popstate",render);render();'};
}

function address(id){
  // Group 14's addresses: the marker in the page's own address, a link's, a form's action;
  // beside an ordinary query. The page reports its own full address when it loads.
  const query='q=red+shoes&page=2';
  return {body:'<h1>Address acts</h1><p><a href="'+escape('/receive?case=act-addrlink-'+id+'&'+query+'&code='+ACT_MARK)+'">Plain link</a></p>'
    +'<form aria-label="Order form" method="post" target="sink" action="'+escape('/receive?case=act-addrsend-'+id+'&'+query+'&session='+ACT_MARK)+'">'
    +'<label>Item <input name="item" value="Lamp"></label><button type="submit">Send order</button></form>'
    +'<button type="button" id="note">Note</button><iframe name="sink" hidden></iframe>',
    script:titled('Address acts')+reporter(id)+clicks('#note','note')+'report("addrseen",{href:location.href});'
      +'globalThis.actChange=change=>{if(change==="act-session"){const form=document.querySelector("form");form.action=form.action.replace('+inline(ACT_MARK)+','+inline(ACT_MARK.split('').reverse().join(''))+');}};'};
}

function links(id){
  // Links whose click would ask (Delete, Unsubscribe), next to an ordinary one; all GET.
  return {body:'<h1>Links</h1>'+[['Delete','delete'],['Unsubscribe','unsub'],['Read more','plain']].map(([name,what])=>
    '<p><a href="/receive?case=act-link'+what+'-'+escape(id)+'">'+name+'</a></p>').join(''),script:titled('Links')};
}

function fold(id){
  // A control labelled Delete deep inside a folded list.
  return {body:'<h1>Archive</h1><ul aria-label="Archive">'+Array.from({length:120},(_,index)=>'<li>Archived note '+index
    +(index===100?' <button type="button" id="delete">Delete</button>':'')+'</li>').join('')+'</ul>',
    script:titled('Archive')+reporter(id)+clicks('#delete','delete')};
}

function stage(id,mode){
  // "stage 1", "stage 2", ... one every 3.5 seconds from the fixture's act-start (sent right
  // before the call); the note reports every value.
  return {body:'<h1>Stages</h1><p id="stage">stage 0</p><label>Stage note <input name="note"></label>',
    script:titled('Stages')+reporter(id)+inputs+'let stage=0,timer=null;globalThis.actChange=change=>{if(change==="act-start"&&timer===null)'
      +'timer=setInterval(()=>{stage++;document.querySelector("#stage").textContent="stage "+stage;},'+(mode==='boundary'?5500:STAGE_MS)+');};'};
}

function ownerDraft(id){
  // The runner clicks the center of the native Chrome window. Leave space for its browser chrome.
  return {body:'<h1>Owner draft</h1><p id="state">Waiting for keys</p>'
    +'<label style="position:fixed;inset:20% 15%;display:grid;grid-template-rows:auto 1fr">Draft <input name="draft"></label>',
    script:titled('Owner draft '+id)+reporter(id)
      +'const draft=document.querySelector("[name=draft]");'
      +'const focus=event=>({trusted:event.isTrusted,field:event.target.name,'
      +'focused:document.hasFocus()&&document.activeElement===draft,visible:document.visibilityState==="visible"});'
      +'document.addEventListener("click",event=>report("focus",focus(event)));'
      +'document.addEventListener("keydown",event=>report("key",focus(event)));'
      +'draft.addEventListener("input",event=>{report("input",{...focus(event),value:draft.value});'
      +'if(event.isTrusted&&draft.value==="Owner words")document.querySelector("#state").textContent="Draft entered";});'};
}

function inputDialog(id){
  return {body:'<h1>Input dialog</h1><button type="button" id="notice">Show notice</button><label>Next field <input name="next"></label>',
    script:titled('Input dialog')+reporter(id)+inputs+'document.querySelector("#notice").onclick=event=>{'
      +'report("notice-click",{trusted:event.isTrusted});alert("Input handler notice");};'};
}

function plain(id,mode){
  return {body:'<h1>Plain page</h1><button type="button" id="press">Press me</button>'+(mode==='empty'?'':'<label>Note <textarea name="note"></textarea></label>'),
    script:titled('Plain '+id)+reporter(id)+inputs+clicks('#press','press')};
}

function typed(id){
  // A page he types into: the field has the focus from the start.
  return {body:'<h1>Typing page</h1><label>Owner note <textarea name="owner" autofocus></textarea></label>',script:titled('Typing '+id)};
}

function media(id){
  return {body:'<h1>Media</h1><audio src="/tone.wav" loop></audio><button type="button" id="play">Play</button>',
    script:titled('Media')+reporter(id)+'const audio=document.querySelector("audio");'
      +'document.querySelector("#play").onclick=()=>audio.play();'
      +'audio.addEventListener("timeupdate",()=>{if(!audio.paused)report("playback",{position:audio.currentTime});});'};
}

function popup(id,mode){
  if(mode==='child')return {body:'<h1>Popup child</h1>',script:titled('Popup child')};
  return {body:'<h1>Opener</h1><button type="button" id="open">Open window</button>',
    script:titled('Opener')+'document.querySelector("#open").onclick=()=>window.open("/?case=act-popup&mode=child&id="+encodeURIComponent('+inline(id)+'),"act-popup","popup,width=420,height=320");'};
}

export function actPage(url){
  const name=url.searchParams.get('case').slice('act-'.length);
  const id=String(url.searchParams.get('id')||'fixture').slice(0,40),mode=url.searchParams.get('mode');
  const pages={steps:()=>steps(id),f4:()=>f4(id),large:()=>large(id,mode),far:()=>far(id,mode),fingerprint:()=>fingerprint(id),
    hostile:()=>hostile(id,HOSTILE[Math.max(0,Math.min(HOSTILE.length-1,Number.parseInt(url.searchParams.get('index')||'0',10)||0))]),look:()=>look(id,mode),loaded:()=>loaded(id,mode),
    address:()=>address(id),links:()=>links(id),fold:()=>fold(id),stage:()=>stage(id,mode),plain:()=>plain(id,mode),typed:()=>typed(id),
    'owner-draft':()=>ownerDraft(id),'input-dialog':()=>inputDialog(id),
    media:()=>media(id),popup:()=>popup(id,mode)};
  return Object.hasOwn(pages,name)?pages[name]():null;
}
