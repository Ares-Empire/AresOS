// No external message listener. Only the extension's selection page starts a session.
let port, selected;
chrome.runtime.onMessage.addListener((message,sender,reply)=>{
  if(sender.id!==chrome.runtime.id || !message.attach) return;
  (async()=>{
    if(port) throw new Error('Already connected');
    selected=message.attach;
    await chrome.debugger.attach({tabId:selected},'1.3');
    port=chrome.runtime.connectNative('org.aresos.chrome_check');
    port.onMessage.addListener(async command=>{
      try {
        let result;
        if(command.op==='tabs') result=await chrome.tabs.query({});
        else if(command.op==='detach') {await chrome.debugger.detach({tabId:selected});result={detached:true};}
        else {
          const target={tabId:selected};
          if(command.sessionId) target.sessionId=command.sessionId;
          result=await chrome.debugger.sendCommand(target,command.method,command.params||{});
        }
        port.postMessage({id:command.id,result:result||{}});
      } catch(e){port.postMessage({id:command.id,error:String(e)});}
    });
    port.onDisconnect.addListener(()=>{chrome.debugger.detach({tabId:selected}).catch(()=>{});port=undefined;selected=undefined;});
    port.postMessage({method:'check.connected',params:{tabId:selected,version:chrome.runtime.getManifest().version}});
    reply({attached:selected});
  })().catch(e=>reply({error:String(e)}));
  return true;
});
chrome.debugger.onEvent.addListener((source,method,params)=>{
  if(port && source.tabId===selected) port.postMessage({method,params,sessionId:source.sessionId});
});
chrome.debugger.onDetach.addListener((source,reason)=>{
  if(port && source.tabId===selected) port.postMessage({method:'check.detached',params:{reason}});
});
