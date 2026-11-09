document.querySelector('#stop').addEventListener('click',async()=>{
  const result=await chrome.runtime.sendMessage({command:'stop'});
  if(result.cleanup_pending){document.querySelector('#status').textContent='Stopped. Close its dialog, or close the tab if returning it remains pending.';return;}
  window.close();
});
