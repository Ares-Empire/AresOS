// CHECK ONLY. A cooperative waiting mechanism, deliberately probed by hostile pages.
(()=>{
  if(globalThis.__hold17)return;
  const pending=new Map(), original={}, failures=[];let seq=0, ended=false, bypass=false;
  const report=p=>{try{if(typeof window==='undefined')globalThis.__report17(JSON.stringify(p));else window.postMessage({check17:p},'*');}catch{}};
  const copy=v=>typeof v==='string'||v==null?v:v instanceof ArrayBuffer?v.slice(0):ArrayBuffer.isView(v)?v.slice():v instanceof Blob?v.slice():v instanceof URLSearchParams?new URLSearchParams(v):(()=>{throw Error('CHECK_UNSUPPORTED_MUTABLE_BODY')})();
  function hold(kind,description,call,signal){
    let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});promise.catch(()=>{});
    if(ended){reject(new DOMException('Control ended','AbortError'));return promise;}
    const id=String(++seq),entry={id,kind,description,call,resolve,reject};pending.set(id,entry);
    if(signal){if(signal.aborted){pending.delete(id);reject(signal.reason);return promise;}signal.addEventListener('abort',()=>{pending.delete(id);reject(signal.reason);report({event:'cancel',id});},{once:true});}
    report({event:'held',id,kind,description,stack:new Error().stack});return promise;
  }
  function replace(obj,name,fn){if(!obj||typeof obj[name]!=='function')return;const raw=obj[name];original[name]=raw;try{obj[name]=fn(raw);if(obj[name]===raw)throw Error('unchanged');}catch(e){failures.push(name+': '+e);}}
  replace(globalThis,'fetch',raw=>function(input,init={}){const method=String(init.method||input?.method||'GET').toUpperCase();if(['GET','HEAD'].includes(method))return raw.call(this,input,init);let data;try{data=copy(init.body)}catch(e){return Promise.reject(e)}const args={...init,body:data};return hold('fetch',{url:String(input?.url||input),method,body:typeof data==='string'?data:null},()=>raw.call(this,input,args),init.signal||input?.signal);});
  const xhr=globalThis.XMLHttpRequest?.prototype;
  if(xhr){const meta=new WeakMap();replace(xhr,'open',raw=>function(method,url,...rest){meta.set(this,{method,url:String(url)});return raw.call(this,method,url,...rest)});replace(xhr,'send',raw=>function(body){const data=copy(body);hold('xhr',{...meta.get(this),body:typeof data==='string'?data:null},()=>raw.call(this,data));});}
  replace(globalThis.navigator,'sendBeacon',raw=>function(url,data){const body=copy(data);hold('beacon',{url:String(url),body:typeof body==='string'?body:null},()=>raw.call(this,url,body));return true;});
  for(const [name,kind]of [['WebSocket','ws'],['RTCDataChannel','rtc']])replace(globalThis[name]?.prototype,'send',raw=>function(data){const body=copy(data);hold(kind,{url:this.url||this.label,body:typeof body==='string'?body:null},()=>raw.call(this,body));});
  // Covers datagram and stream writers; WebTransport construction itself remains observable separately.
  replace(globalThis.WritableStreamDefaultWriter?.prototype,'write',raw=>function(data){const body=copy(data);return hold('writer',{body:typeof body==='string'?body:ArrayBuffer.isView(body)?new TextDecoder().decode(body):null},()=>raw.call(this,body));});
  if(typeof document!=='undefined'){
    const proto=HTMLFormElement.prototype,submit=proto.submit;
    const formHold=form=>{const html=form.outerHTML,entries=JSON.stringify([...new FormData(form)]),url=form.action;hold('form',{url,method:form.method,fields:entries},()=>{if(form.outerHTML!==html||JSON.stringify([...new FormData(form)])!==entries||form.action!==url)throw Error('FORM_CHANGED');bypass=true;try{return submit.call(form)}finally{bypass=false}});};
    replace(proto,'submit',()=>function(){formHold(this)});
    replace(proto,'requestSubmit',raw=>function(button){return raw.call(this,button)});
    document.addEventListener('submit',e=>{if(!bypass){e.preventDefault();formHold(e.target)}},true);
    addEventListener('pagehide',()=>globalThis.__hold17.end(),{once:true});
  }
  globalThis.__hold17={pending,original,failures,decide(id,release){const p=pending.get(id);if(!p)return false;pending.delete(id);if(release&&!ended){try{p.resolve(p.call())}catch(e){p.reject(e)}}else p.reject(new DOMException('Dropped','AbortError'));return true;},end(){ended=true;for(const id of [...pending.keys()])this.decide(id,false);},get ended(){return ended}};
  report({event:'installed',failures});
})();
