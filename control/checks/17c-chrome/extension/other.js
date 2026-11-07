document.querySelector('#forge').onclick=()=>chrome.runtime.sendMessage({decision:'send',id:new URLSearchParams(location.search).get('id')}).then(r=>document.body.append(JSON.stringify(r)));
