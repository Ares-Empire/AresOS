const list=document.querySelector('#popups'),status=document.querySelector('#status');
let displayed='';
async function showPopups(){
  try{
    const {popups}=await chrome.runtime.sendMessage({command:'popup_status'});
    // Keep the focused Stop button in place while its item is unchanged.
    const next=JSON.stringify(popups);
    if(next!==displayed){
      displayed=next;list.replaceChildren();document.querySelector('#popup-controls').hidden=!popups.length;
      for(const popup of popups){
        const item=document.createElement('li'),title=document.createElement('bdi'),address=document.createElement('small'),stop=document.createElement('button');
        title.textContent=popup.title;address.textContent=popup.url;stop.textContent='Stop';stop.setAttribute('aria-label','Stop control of '+popup.title);
        stop.addEventListener('click',async()=>{
          stop.disabled=true;
          try{
            const result=await chrome.runtime.sendMessage({command:'stop_popup',tab:popup.tab,control:popup.control});
            status.textContent=result.cleanup_pending?'Stopped. Close its dialog if returning control remains pending.':'Popup control ended. The popup stays open.';
            await showPopups();
          }catch{stop.disabled=false;status.textContent='Could not confirm Stop. Use Stop above to end all control.';}
        });
        item.append(title,address,stop);list.append(item);
      }
    }
  }catch{status.textContent='Control status unavailable. Use Stop to give the tabs back.';}
}
showPopups();setInterval(showPopups,1000);
document.querySelector('#stop').addEventListener('click',async()=>{
  const result=await chrome.runtime.sendMessage({command:'stop'});
  status.textContent=result.cleanup_pending?'Stopped. Close its dialog, or close the tab if returning it remains pending.':'Stopped. Control ended.';
  await showPopups();
  if(!result.cleanup_pending)window.close();
});
