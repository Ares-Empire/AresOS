const id=new URLSearchParams(location.search).get('id');
chrome.runtime.sendMessage({preview:id}).then(p=>document.querySelector('#details').textContent=JSON.stringify(p,null,2));
for(const decision of ['send','drop','retire'])document.querySelector('#'+decision).onclick=()=>chrome.runtime.sendMessage({decision,id}).then(r=>document.querySelector('#status').textContent=JSON.stringify(r));
