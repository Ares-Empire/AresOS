document.querySelector('#stop').onclick=()=>chrome.runtime.sendMessage({stop:true}).then(()=>window.close());
