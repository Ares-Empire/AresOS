// CHECK ONLY. Explicitly enabled in fixture tests; raw bypasses test the floor.
(()=>{
 if(globalThis.__floor)return;
 const raw=fetch, pending=new Map();let seq=0;
 const digest=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(v=>v.toString(16).padStart(2,'0')).join('');
 const report=p=>window.postMessage({check17:p},'*');
 globalThis.__floor={enabled:false,pending,raw,async release(id){const p=pending.get(id);if(!p)throw Error('NOT_PENDING');pending.delete(id);p.resolve(raw(p.url,{method:p.method,headers:p.headers,body:p.bytes}));return true;}};
 globalThis.fetch=function(input,init={}){
  const method=String(init.method||input?.method||'GET').toUpperCase();
  if(!__floor.enabled||['GET','HEAD'].includes(method))return raw.call(this,input,init);
  if(init.body instanceof ReadableStream){report({event:'stream-refused',missing:true});return Promise.reject(Error('UNFREEZABLE_STREAM'));}
  return new Promise(async(resolve,reject)=>{try{
   const request=new Request(input,init),bytes=await request.arrayBuffer(),id=String(++seq),headers=[...request.headers];
   const description={url:request.url,method,headers,length:bytes.byteLength,sha256:await digest(bytes),complete:true};
   pending.set(id,{...description,bytes,resolve,reject});report({event:'held',id,kind:'fetch',description});
  }catch(e){reject(e)}});
 };
})();
