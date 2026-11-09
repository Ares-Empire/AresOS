const root=document.querySelector('#entries');
const request=arguments_=>chrome.runtime.sendMessage({command:'sites',arguments:arguments_});
function button(label,action){const element=document.createElement('button');element.textContent=label;element.addEventListener('click',async()=>{await action();await refresh();});return element;}
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
      row.append(button(entry.value?'Allow editing':'Make read-only',()=>request({command:'readonly',site:'https://'+entry.id+'/',enabled:!entry.value})));
    }else{
      row.textContent=entry.question;
      if(entry.eligible)row.append(button("Don't ask again for this kind",()=>request({command:'allow',operation_id:entry.operation_id})));
    }
    root.append(row);
  }
  if(result.data.cursor){const more=document.createElement('button');more.id='more';more.textContent='More';more.onclick=()=>refresh(result.data.cursor);root.append(more);}
}
refresh();
