const root=document.querySelector('#entries'),statusLine=document.querySelector('#status');
const request=arguments_=>chrome.runtime.sendMessage({command:'sites',arguments:arguments_});
// A loosening button names its change while the password dialog is up, so the
// owner can match the dialog to the button he pressed.
function button(label,action,change){const element=document.createElement('button');element.textContent=label;element.addEventListener('click',async()=>{
  statusLine.textContent=change?'Waiting for your password in the system dialog: '+change:'';
  const result=await action();
  statusLine.textContent=result?.ok===false?(result.error?.message||'Nothing changed.'):change?'Changed: '+change:'';
  await refresh();});return element;}
async function refresh(cursor) {
  const result=await request({command:'list',...(cursor?{cursor}:{})});
  if(!cursor)root.replaceChildren();root.querySelector('#more')?.remove();
  if(!result?.ok){root.textContent=result?.error?.message || 'Use sudo aresos admin chrome allowed.';return;}
  for(const entry of result.data.items){
    const row=document.createElement('p');
    if(entry.kind==='allowed'){
      row.textContent=JSON.stringify(entry.value.adapter)+(entry.value.revoked?' (revoked)':'');
      if(!entry.value.revoked)row.append(button('Revoke',()=>request({command:'revoke',id:entry.id})));
    }else if(entry.kind==='readonly'){
      row.textContent=entry.id+(entry.value?' (read-only)':' (editable)');
      row.append(button(entry.value?'Allow editing':'Make read-only',()=>request({command:'readonly',site:'https://'+entry.id+'/',enabled:!entry.value}),entry.value?'read-only off for '+entry.id:null));
    }else{
      row.textContent=entry.question;
      if(entry.eligible)row.append(button("Don't ask again for this kind",()=>request({command:'allow',operation_id:entry.operation_id}),"don't ask again for "+entry.question));
    }
    root.append(row);
  }
  if(result.data.cursor){const more=document.createElement('button');more.id='more';more.textContent='More';more.onclick=()=>refresh(result.data.cursor);root.append(more);}
}
refresh();
