import {createHash} from 'node:crypto';
import {EventEmitter} from 'node:events';

export const fingerprint=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
// Candidate rule, not a semantic or security boundary. Every fixture /receive is held.
// Public runs drop candidates instead of delivering any form data or analytics writes.
export function classify(p,{form=false,typing=false}={}){
  if(!['GET','HEAD','OPTIONS'].includes(p.request.method))return 'non-read method';
  if(['Ping','CSPViolationReport'].includes(p.resourceType))return 'ping/report';
  if(form)return 'form submission, including GET';
  if(typing&&['XHR','Fetch'].includes(p.resourceType))return 'request during typing';
  if(p.resourceType==='Document'&&new URL(p.request.url).search)return 'document with query (ambiguous)';
  return null;
}
export class Hold extends EventEmitter {
  pending=new Map(); history=[]; errors=[]; trusted=new Set(); publicMode=false;
  pwRoutes=new Map(); pwSequence=0;
  inFlight=new Set(); documents=new Set(); currentDocument=null;
  constructor(cdp){
    super();this.cdp=cdp;this.network=new Map();this.cancelled=new Set();this.publicRows=new Map();
    this.onRequest=p=>{const meta={documentURL:p.documentURL,initiator:p.initiator?.type};this.network.set(p.requestId,meta);if(this.publicRows.has(p.requestId))Object.assign(this.publicRows.get(p.requestId),meta);};
    this.onFailed=p=>{if(p.canceled||p.errorText==='net::ERR_ABORTED')this.cancelled.add(p.requestId);};
    this.onFrame=p=>{if(!p.frame.parentId){this.currentDocument=p.frame.url;this.documents.add(p.frame.url);}};
    cdp.on('Network.requestWillBeSent',this.onRequest);
    cdp.on('Network.loadingFailed',this.onFailed);
    cdp.on('Page.frameNavigated',this.onFrame);
    this.listener=(p,sessionId)=>{const task=this.pause(p,sessionId).catch(async e=>{
      // Navigation can cancel a request between its pause event and our decision.
      // Accept only an independently observed network cancellation, never an unknown error.
      if(this.publicMode&&e.message.includes('Invalid InterceptionId')){
        await new Promise(r=>setTimeout(r,100));
        const doc=this.network.get(p.networkId)?.documentURL;
        const oldDocument=doc&&this.documents.has(doc)&&doc!==this.currentDocument;
        if(this.cancelled.has(p.networkId)||oldDocument){this.history.push({event:'cancelled',networkId:p.networkId,url:p.request.url,documentURL:doc,currentDocument:this.currentDocument});return;}
      }
      this.errors.push(JSON.stringify({error:e.message,url:p.request.url,networkId:p.networkId,sessionId}));this.emit('problem',e);
    });this.inFlight.add(task);task.finally(()=>this.inFlight.delete(task));};
    cdp.on('Fetch.requestPaused',this.listener);
  }
  async command(method,params,sessionId){
    if(this.cdp.pwPage&&params.requestId){
      const route=this.pwRoutes.get(params.requestId);if(!route)throw Error('NOT_PENDING: Playwright route');
      this.pwRoutes.delete(params.requestId);
      return method==='Fetch.continueRequest'?route.continue():route.abort('aborted');
    }
    return this.cdp.send(method,params,sessionId);
  }
  async enable(){
    await this.cdp.send('Network.enable');
    if(this.cdp.pwPage){
      // Playwright's network manager owns Fetch and auto-continues unknown raw pauses.
      // Use its routing API, not a second competing Fetch consumer on the same session.
      this.cdp.off('Fetch.requestPaused',this.listener);
      this.pwHandler=async route=>{
        const request=route.request(),id='pw-route-'+(++this.pwSequence);
        this.pwRoutes.set(id,route);
        const type={document:'Document',xhr:'XHR',fetch:'Fetch',ping:'Ping',image:'Image'}[request.resourceType()]||request.resourceType();
        const data=request.postData();
        await this.pause({requestId:id,request:{url:request.url(),method:request.method(),postData:data,hasPostData:data!==null},resourceType:type});
      };
      await this.cdp.pwPage.route('**/*',this.pwHandler);
    }else await this.cdp.send('Fetch.enable',{patterns:[{urlPattern:'*',requestStage:'Request'}]});
  }
  async pause(p,sessionId){
    const send=(method,params)=>this.command(method,params,sessionId);
    const isFixture=new URL(p.request.url).pathname==='/receive';
    const reason=classify(p,this.intent||{});
    if(this.publicMode){
      // Independent guard: background APIs are dropped even when this candidate rule misses them.
      const drop=!!reason||['XHR','Fetch','Ping','WebSocket'].includes(p.resourceType);
      const row={networkId:p.networkId,url:p.request.url,method:p.request.method,type:p.resourceType,...this.network.get(p.networkId),phase:this.phase||'load',reason,decision:drop?'drop':'allow-read'};
      this.publicRows.set(p.networkId,row);this.history.push(row);
      await send(drop?'Fetch.failRequest':'Fetch.continueRequest',drop?{requestId:p.requestId,errorReason:'Aborted'}:{requestId:p.requestId});return;
    }
    if(!isFixture||this.trusted.has(new URL(p.request.url).origin)){
      await send('Fetch.continueRequest',{requestId:p.requestId});return;
    }
    let data=p.request.postData??null;
    if(data===null&&p.request.hasPostData&&p.networkId){
      try{data=(await this.cdp.send('Network.getRequestPostData',{requestId:p.networkId})).postData;}catch{/* Explicit missing-data flag below. */}
    }
    const preview={site:new URL(p.request.url).origin,address:p.request.url,method:p.request.method,data,bodyEntries:p.request.postDataEntries||null,bodyUnavailable:!!p.request.hasPostData&&data===null,type:p.resourceType};
    const entry={id:p.requestId,sessionId,preview,classifierReason:reason,hash:fingerprint(preview),state:'held',at:Date.now()};
    this.pending.set(entry.id,entry);this.history.push(entry);this.emit('held',entry);
  }
  async decide(id,decision,hash){
    const entry=this.pending.get(id);
    if(!entry||entry.state!=='held')throw new Error('NOT_PENDING: decision already consumed or unknown');
    if(entry.hash!==hash)throw new Error('PREVIEW_MISMATCH');
    // Consume before the call: a transport failure means unknown, never automatic retry.
    this.pending.delete(id);entry.state='unknown';entry.decidedAt=Date.now();
    await this.command(decision==='release'?'Fetch.continueRequest':'Fetch.failRequest',decision==='release'?{requestId:id}:{requestId:id,errorReason:'Aborted'},entry.sessionId);
    entry.state=decision==='release'?'released':'dropped';
  }
  async close(){
    for(const entry of this.pending.values())await this.decide(entry.id,'drop',entry.hash);
    if(this.cdp.pwPage)await this.cdp.pwPage.unroute('**/*',this.pwHandler);
    else await this.cdp.send('Fetch.disable');
    this.cdp.off('Fetch.requestPaused',this.listener);
    this.cdp.off('Network.requestWillBeSent',this.onRequest);
    this.cdp.off('Network.loadingFailed',this.onFailed);
    this.cdp.off('Page.frameNavigated',this.onFrame);
    while(this.inFlight.size)await Promise.all([...this.inFlight]);
    if(this.errors.length)throw new Error('Hold event errors: '+this.errors.join(';'));
  }
}

// Demonstrates a cooperative-page shim only. Same-world code can undo/bypass it.
export const websocketShim=`(()=>{
  const original=WebSocket.prototype.send;
  const pending=new Map();let seq=0;
  Object.defineProperty(window,'__checkWS',{value:{
    list:()=>[...pending].map(([id,x])=>({id,url:x.ws.url,data:x.data})),
    decide:(id,release)=>{const x=pending.get(id);if(!x)throw Error('NOT_PENDING');pending.delete(id);if(release)original.call(x.ws,x.data);}
  }});
  WebSocket.prototype.send=function(data){pending.set(++seq,{ws:this,data});};
})()`;
