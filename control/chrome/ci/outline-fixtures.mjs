// Synthetic pages for brief 28's remaining read cases. No owner data.
export const LONG_TEXT='0123456789'.repeat(10000);
export const LONG_VALUE='Value "\\ 漢 '.repeat(2000).slice(0,20000);
export const WIDE_CELL='abcdefghij'.repeat(300);
export const BYTE_TEXT={unicode:'漢'.repeat(24000),quotes:'"'.repeat(24000)};
const js=value=>JSON.stringify(value).replaceAll('<','\\u003c');

export function outlinePage(url){
  const kind=url.searchParams.get('case'),mode=url.searchParams.get('mode'),id=url.searchParams.get('id')||'outline';
  if(kind==='outline-paging'){
    const text=BYTE_TEXT[mode]||LONG_TEXT;
    if(mode in BYTE_TEXT)return {body:'<h1>Paging fixture</h1>'+Array.from({length:Math.ceil(text.length/180)},(_,i)=>'<p>'+text.slice(i*180,(i+1)*180)+'</p><hr>').join(''),script:"document.title='Paging';"};
    return {body:'<h1>Paging fixture</h1>'+(mode==='row'?'<table aria-label="Wide"><tr><th>A</th><th>B</th></tr><tr><td>'+WIDE_CELL+'</td><td>'+WIDE_CELL+'</td></tr></table>':mode==='value'?'<textarea aria-label="Long value"></textarea>':'<p id="long"></p><button type="button">Other</button>'),
      script:"document.title='Paging';document.querySelector("+js(mode==='value'?'textarea':mode==='row'?'h1':'#long')+")["+js(mode==='value'?'defaultValue':'textContent')+"]="+js(mode==='value'?LONG_VALUE:mode==='row'?'Paging fixture':text)+';'};
  }
  if(kind==='outline-state'){
    if(mode==='child')return {body:'<p id="changing">Frame before</p>',script:"document.title='State child';globalThis.reviewChange=()=>document.querySelector('#changing').textContent='Frame after';"};
    if(mode==='busy')return {body:'<h1>Busy fixture</h1><p id="tick">Idle</p><p id="answer"></p>',script:"document.title='Busy';globalThis.reviewChange=()=>{let tick=0;setInterval(()=>{document.querySelector('#tick').textContent='Tick '+(++tick);if(tick===20)document.querySelector('#answer').textContent='Busy answer arrived';},25);};"};
    return {body:'<h1>State fixture</h1><iframe src="http://second.test:8766/?case=outline-state&amp;mode=child&amp;id='+id+'-child"></iframe>',script:"document.title='State';"};
  }
  if(kind!=='password-outline')return null;
  const report=phase=>"fetch('/compat-report',{method:'POST',body:JSON.stringify({id:"+js(id)+",phase:"+js(phase)+"})});";
  if(mode==='child')return {body:'<input aria-label="Frame note" value="ASK_FRAME_28">',script:report('ask-frame-'+(url.searchParams.get('version')||'first'))};
  const child='http://second.test:8766/?case=password-outline&mode=child&id='+encodeURIComponent(id);
  const changes={
    added:"const field=document.createElement('input');field.setAttribute('aria-label','Added field');field.value='ASK_ADDED_28';document.body.append(field);",
    replacement:"document.querySelector('#text').outerHTML='<input id=\"text\" aria-label=\"Text note\" value=\"ASK_REPLACED_28\">';",
    label:"document.querySelector('#text').setAttribute('aria-label','Renamed note');",
    duplicate:"const a=document.querySelector('#same-a'),b=document.querySelector('#same-b');a.before(b);",
    unlabelled:"const a=document.querySelector('#bare-a'),b=document.querySelector('#bare-b');a.before(b);",
    frame:"document.querySelector('iframe').src="+js(child+'&version=next')+';',
    type:"document.querySelector('#text').type='password';",
    mask:"document.querySelector('#text').style.webkitTextSecurity='disc';",
  };
  return {body:'<h1>Asking fixture</h1><input id="text" aria-label="Text note" value="ASK_TEXT_28"><input type="search" aria-label="Search note" value="ASK_SEARCH_28"><input type="email" aria-label="Email note" value="ASK_EMAIL_28"><textarea aria-label="Area note">ASK_AREA_28</textarea>'
    +'<input id="same-a" aria-label="Same" value="ASK_SAME_A_28"><input id="same-b" aria-label="Same" value="ASK_SAME_B_28"><input id="bare-a" value="ASK_BARE_A_28"><input id="bare-b" value="ASK_BARE_B_28"><input aria-label="Empty note">'
    +'<input name="otp" aria-label="One time" value="SENTINEL_PRIVATE_PASSWORD_20"><input aria-label="Password" value="SENTINEL_PRIVATE_PASSWORD_20"><input aria-label="Covered" style="-webkit-text-security:disc" value="SENTINEL_PRIVATE_PASSWORD_20"><iframe src="'+child+'"></iframe>',
    script:"document.title='Asking';globalThis.reviewChange=()=>{"+(changes[mode]||'')+'};'+report('ask-top')};
}
