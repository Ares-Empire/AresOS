// Disposable runner experiment, never included in the installed extension.
const report=value=>fetch('http://fixture.test:8765/report',{method:'POST',body:JSON.stringify(value)});
const command=(tabId,method,parameters={})=>chrome.debugger.sendCommand({tabId},method,parameters);
const privateTabs=new Set();
chrome.debugger.onEvent.addListener(async(source,method,params)=>{
  if(method!=='Debugger.paused'||!privateTabs.has(source.tabId))return;
  const started=Date.now();let timeout;
  try{
    const injection=chrome.scripting.executeScript({target:{tabId:source.tabId},files:['isolated.js'],injectImmediately:true});
    const result=await Promise.race([injection,new Promise((_,reject)=>{timeout=setTimeout(()=>reject(Error('executeScript did not complete while paused')),5000);})]);
    await report({phase:'isolated-before-resume',elapsed:Date.now()-started,result});
  }catch(error){await report({phase:'injection-error',error:String(error)});}
  finally{clearTimeout(timeout);await command(source.tabId,'Debugger.resume');}
});
(async()=>{
  await report({phase:'ready'});
  const tab=await chrome.tabs.create({url:'about:blank'});privateTabs.add(tab.id);
  await chrome.debugger.attach({tabId:tab.id},'1.3');
  await command(tab.id,'Page.enable');await command(tab.id,'Debugger.enable');
  await command(tab.id,'Page.addScriptToEvaluateOnNewDocument',{source:'debugger;'});
  await command(tab.id,'Page.navigate',{url:'http://fixture.test:8765/page'});
})().catch(error=>report({phase:'error',error:String(error)}));
