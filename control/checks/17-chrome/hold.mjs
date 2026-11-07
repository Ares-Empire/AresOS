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
  constructor(cdp){
    super();this.cdp=cdp;
    this.listener=p=>{this.pause(p).catch(e=>{this.errors.push(e.message);this.emit('problem',e);});};
    cdp.on('Fetch.requestPaused',this.listener);
  }
  async enable(){await this.cdp.send('Network.enable');await this.cdp.send('Fetch.enable',{patterns:[{urlPattern:'*',requestStage:'Request'}]});}
  async pause(p){
    const isFixture=new URL(p.request.url).pathname==='/receive';
    const reason=classify(p,this.intent||{});
    if(this.publicMode){
      // Independent guard: background APIs are dropped even when this candidate rule misses them.
      const drop=!!reason||['XHR','Fetch','Ping','WebSocket'].includes(p.resourceType);
      this.history.push({url:p.request.url,method:p.request.method,type:p.resourceType,reason,decision:drop?'drop':'allow-read'});
      await this.cdp.send(drop?'Fetch.failRequest':'Fetch.continueRequest',drop?{requestId:p.requestId,errorReason:'Aborted'}:{requestId:p.requestId});return;
    }
    if(!isFixture||this.trusted.has(new URL(p.request.url).origin)){
      await this.cdp.send('Fetch.continueRequest',{requestId:p.requestId});return;
    }
    let data=p.request.postData??null;
    if(data===null&&p.request.hasPostData&&p.networkId){
      try{data=(await this.cdp.send('Network.getRequestPostData',{requestId:p.networkId})).postData;}catch{/* Explicit missing-data flag below. */}
    }
    const preview={site:new URL(p.request.url).origin,address:p.request.url,method:p.request.method,data,bodyEntries:p.request.postDataEntries||null,bodyUnavailable:!!p.request.hasPostData&&data===null,type:p.resourceType};
    const entry={id:p.requestId,preview,hash:fingerprint(preview),state:'held',at:Date.now()};
    this.pending.set(entry.id,entry);this.history.push(entry);this.emit('held',entry);
  }
  async decide(id,decision,hash){
    const entry=this.pending.get(id);
    if(!entry||entry.state!=='held')throw new Error('NOT_PENDING: decision already consumed or unknown');
    if(entry.hash!==hash)throw new Error('PREVIEW_MISMATCH');
    // Consume before the call: a transport failure means unknown, never automatic retry.
    this.pending.delete(id);entry.state='unknown';entry.decidedAt=Date.now();
    await this.cdp.send(decision==='release'?'Fetch.continueRequest':'Fetch.failRequest',decision==='release'?{requestId:id}:{requestId:id,errorReason:'Aborted'});
    entry.state=decision==='release'?'released':'dropped';
  }
  async close(){
    for(const entry of this.pending.values())await this.decide(entry.id,'drop',entry.hash);
    await this.cdp.send('Fetch.disable');this.cdp.off('Fetch.requestPaused',this.listener);
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
