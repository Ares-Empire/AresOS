// Public observations must not exercise the unqualified worker-startup boundary.
// Inserted in the public phase's signed manifest only, in every document/frame.
(()=>{
 const attempts=[];Object.defineProperty(globalThis,'__publicLive17',{value:attempts});
 for(const name of ['Worker','SharedWorker','WebTransport','RTCPeerConnection'])Object.defineProperty(globalThis,name,{value:class{constructor(url){attempts.push({api:name,url:String(url)});throw Error('Disabled for public no-send check')}},configurable:false});
 if(globalThis.ServiceWorkerContainer)Object.defineProperty(ServiceWorkerContainer.prototype,'register',{value:function(url){attempts.push({api:'serviceWorker.register',url:String(url)});return Promise.reject(Error('Disabled for public no-send check'))},configurable:false});
})();
