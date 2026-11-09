document.querySelector('#stop').addEventListener('click',async()=>{await chrome.runtime.sendMessage({command:'stop'});window.close();});
