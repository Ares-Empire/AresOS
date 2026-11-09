// Disposable runner experiment, never included in the installed extension.
const report=value=>fetch('http://fixture.test:8765/report',{method:'POST',body:JSON.stringify(value)});
const command=(tabId,method,parameters={})=>chrome.debugger.sendCommand({tabId},method,parameters);
const privateTabs=new Set();
const contexts=new Map(),contextWaiters=new Map(),installed=new Set();
chrome.debugger.onEvent.addListener(async(source,method,params)=>{
  if(method==='Runtime.executionContextCreated'){
    await report({phase:'context',context:params.context});
    if(params.context.origin===chrome.runtime.getURL('').replace(/\/$/,'')){
      contexts.set(source.tabId,params.context);contextWaiters.get(source.tabId)?.(params.context);
    }
  }
  if(method!=='Debugger.paused'||!privateTabs.has(source.tabId))return;
  const started=Date.now();let timeout;
  try{
    if(installed.has(source.tabId))return;
    const ready=new Promise(resolve=>{contextWaiters.set(source.tabId,resolve);});
    const injection=chrome.scripting.executeScript({target:{tabId:source.tabId},func:()=>{},injectImmediately:true});
    injection.catch(error=>report({phase:'late-injection-error',error:String(error)}));
    const context=contexts.get(source.tabId)||await Promise.race([ready,new Promise((_,reject)=>{timeout=setTimeout(()=>reject(Error('No real extension world while paused')),5000);})]);
    clearTimeout(timeout);
    const evaluated=await command(source.tabId,'Runtime.evaluate',{contextId:context.id,disableBreaks:true,expression:`globalThis.probePrivate=true;
      window.addEventListener('probe-event',event=>{event.preventDefault();event.stopImmediatePropagation();},true);
      const nativeDispatch=EventTarget.prototype.dispatchEvent,nativeType=Object.getOwnPropertyDescriptor(Event.prototype,'type').get;
      window.addEventListener('probe-original',event=>{let type,delivered,error;try{type=nativeType.call(event.detail.event);delivered=nativeDispatch.call(event.target,event.detail.event);}catch(value){error=String(value);}fetch('/report',{method:'POST',body:JSON.stringify({phase:'original-event-native-delivery',type,delivered,error})});},true);
      JSON.stringify({runtime:chrome.runtime.id,closedShadowAPI:typeof chrome.dom.openOrClosedShadowRoot})`,returnByValue:true});
    await report({phase:'private-extension-evaluation-before-resume',evaluated});
    const relay=await command(source.tabId,'Runtime.evaluate',{disableBreaks:true,expression:`(()=>{
      const relay=document.createElement('aresos-private-probe'),dispatch=EventTarget.prototype.dispatchEvent,type=Object.getOwnPropertyDescriptor(Event.prototype,'type').get;
      EventTarget.prototype.dispatchEvent=function(event){if(type.call(event)!=='probe-relayed')return dispatch.call(this,event);dispatch.call(relay,new InputEvent('probe-target',{targetRanges:[new StaticRange({startContainer:this,startOffset:0,endContainer:this,endOffset:0})]}));dispatch.call(relay,event);return dispatch.call(relay,new Event('probe-deliver',{cancelable:true}));};return relay;
    })()`});
    const described=await command(source.tabId,'DOM.describeNode',{objectId:relay.result.objectId,depth:0});
    const resolved=await command(source.tabId,'DOM.resolveNode',{backendNodeId:described.node.backendNodeId,executionContextId:context.id});
    await command(source.tabId,'Runtime.callFunctionOn',{objectId:resolved.object.objectId,functionDeclaration:`function(){
      let original,target;const dispatch=EventTarget.prototype.dispatchEvent;
      this.addEventListener('probe-target',event=>{target=event.getTargetRanges()[0].startContainer;},true);
      this.addEventListener('probe-relayed',event=>{original=event;event.stopImmediatePropagation();},true);
      this.addEventListener('probe-deliver',event=>{try{const result=dispatch.call(target,original);if(!result)event.preventDefault();fetch('/report',{method:'POST',body:JSON.stringify({phase:'native-relay-delivery',result})});}catch(error){fetch('/report',{method:'POST',body:JSON.stringify({phase:'native-relay-error',error:String(error)})});}},true);
    }`});
    installed.add(source.tabId);
    const result='Extension world installed before page scripts';
    await report({phase:'isolated-before-resume',elapsed:Date.now()-started,result});
  }catch(error){await report({phase:'injection-error',error:String(error)});}
  finally{clearTimeout(timeout);await command(source.tabId,'Debugger.resume');}
});
(async()=>{
  await report({phase:'ready'});
  await chrome.scripting.registerContentScripts([{id:'inert-context',matches:['http://*/*'],js:['context.js'],world:'ISOLATED',runAt:'document_start',allFrames:true}]);
  const tab=await chrome.tabs.create({url:'about:blank'});privateTabs.add(tab.id);
  await chrome.debugger.attach({tabId:tab.id},'1.3');
  await command(tab.id,'Page.enable');await command(tab.id,'Debugger.enable');await command(tab.id,'Runtime.enable');
  await command(tab.id,'Debugger.setBreakpointByUrl',{url:chrome.runtime.getURL('context.js'),lineNumber:1});
  await command(tab.id,'Page.navigate',{url:'http://fixture.test:8765/page'});
})().catch(error=>report({phase:'error',error:String(error)}));
