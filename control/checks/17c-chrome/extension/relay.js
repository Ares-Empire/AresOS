// Untrusted page reports can describe a candidate, never authorize it.
addEventListener('message',e=>{if(e.source===window&&e.data?.check17)chrome.runtime.sendMessage({report:e.data.check17}).catch(()=>{});});
chrome.runtime.onMessage.addListener(m=>{if(m.probeForge)chrome.runtime.sendMessage({decision:m.decision||'send',id:m.id}).catch(()=>{});});
