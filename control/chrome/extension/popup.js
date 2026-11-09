document.querySelector('#stop').addEventListener('click',async()=>{
  const result=await chrome.runtime.sendMessage({command:'stop'});
  if(result.cleanup_pending){document.querySelector('#status').textContent='Stopped. Close the page’s dialog to finish returning its tab.';return;}
  window.close();
});
