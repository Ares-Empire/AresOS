// CHECK ONLY. Cooperative observations, never proof against saved native functions.
(()=>{
 if(globalThis.__audit17)return;
 const rows=globalThis.__audit17=[],rawPost=globalThis.postMessage;
 const mark=(api)=>{const row={event:'write-or-handoff',api,at:Date.now()};rows.push(row);try{if(typeof window==='undefined')globalThis.__report17(JSON.stringify(row));else rawPost.call(window,{check17:row},'*')}catch{}};
 const wrap=(obj,key,label)=>{if(!obj||typeof obj[key]!=='function')return;const raw=obj[key];try{obj[key]=function(...args){mark(label||key);return raw.apply(this,args)}}catch{}};
 for(const key of ['setItem','removeItem','clear'])wrap(globalThis.Storage?.prototype,key,'webStorage.'+key);
 for(const key of ['put','add','delete','clear'])wrap(globalThis.IDBObjectStore?.prototype,key,'indexedDB.'+key);
 for(const key of ['put','add','addAll','delete'])wrap(globalThis.Cache?.prototype,key,'cache.'+key);
 for(const key of ['getDirectory'])wrap(globalThis.navigator?.storage,key,'opfs.'+key);
 for(const key of ['createWritable','createSyncAccessHandle'])wrap(globalThis.FileSystemFileHandle?.prototype,key,'opfs.'+key);
 for(const key of ['write','truncate']){wrap(globalThis.FileSystemWritableFileStream?.prototype,key,'opfs.'+key);wrap(globalThis.FileSystemSyncAccessHandle?.prototype,key,'opfs.sync.'+key);}
 for(const [type,key,label]of [[globalThis.ServiceWorkerContainer,'register','serviceWorker.register'],[globalThis.SyncManager,'register','sync.register'],[globalThis.PeriodicSyncManager,'register','periodicSync.register'],[globalThis.BroadcastChannel,'postMessage','broadcast.postMessage'],[globalThis.Worker,'postMessage','worker.postMessage'],[globalThis.ServiceWorker,'postMessage','serviceWorker.postMessage'],[globalThis.MessagePort,'postMessage','port.postMessage']])wrap(type?.prototype,key,label);
 if(typeof window!=='undefined'){
  const cookie=Object.getOwnPropertyDescriptor(Document.prototype,'cookie');
  if(cookie?.set)Object.defineProperty(Document.prototype,'cookie',{...cookie,set(v){mark('cookie.set');cookie.set.call(this,v)}});
  wrap(window,'postMessage','window.postMessage');
 }
})();
