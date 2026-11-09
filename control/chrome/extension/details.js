const root=document.querySelector('#entries');
const request=arguments_=>chrome.runtime.sendMessage({command:'sites',arguments:arguments_});
function button(label,action){const element=document.createElement('button');element.textContent=label;element.addEventListener('click',async()=>{await action();await refresh();});return element;}
async function refresh() {
  const result=await request({command:'list'});root.replaceChildren();
  if(!result?.ok){root.textContent=result?.error?.message || 'Use sudo aresos admin chrome allowed.';return;}
  const data=result.data.untrusted_content;
  for(const [key,entry] of data.allowed){
    const row=document.createElement('p');row.textContent=JSON.stringify(entry.adapter)+(entry.revoked ? ' (revoked)':'');
    if(!entry.revoked)row.append(button('Revoke',()=>request({command:'revoke',id:key.replace('chrome:allow:','')})));
    root.append(row);
  }
  for(const recent of data.recent){
    const row=document.createElement('p');row.textContent=recent.question;
    if(recent.eligible)row.append(button("Don't ask again for this kind",()=>request({command:'allow',operation_id:recent.operation_id})));
    root.append(row);
  }
}
refresh();
