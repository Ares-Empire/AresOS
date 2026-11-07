import {performance} from 'node:perf_hooks';
import {session} from './protocol.mjs';

// Use Chrome's accessibility names and roles, with DOM layout joined by backend node ID.
// References are document + frame + backend-node identities, never ordinal selectors.
export class PageView {
  refs=new Map(); children=new Map();
  constructor(cdp,frameSessions){
    this.cdp=cdp;this.frameSessions=frameSessions;
    this.onAttached=p=>{
      if(p.targetInfo.type==='iframe')this.children.set(p.targetInfo.targetId,{cdp:session(cdp,p.sessionId),sessionId:p.sessionId});
    };
    this.onDetached=p=>{for(const [id,s]of this.children)if(s.sessionId===p.sessionId){s.cdp.close?.();this.children.delete(id);}};
    if(!frameSessions){cdp.on('Target.attachedToTarget',this.onAttached);cdp.on('Target.detachedFromTarget',this.onDetached);}
  }
  async enable(){
    await this.cdp.send('Page.enable');await this.cdp.send('DOM.enable');await this.cdp.send('Accessibility.enable');
    if(!this.frameSessions)await this.cdp.send('Target.setAutoAttach',{autoAttach:true,waitForDebuggerOnStart:false,flatten:true,filter:[{type:'iframe',exclude:false}]});
  }
  async read({offset=0,limit=120}={}){
    const start=performance.now();
    if(this.frameSessions)this.children=new Map((await this.frameSessions()).map(s=>[s.sessionId,s]));
    const all=[],frames=[],errors=[];
    const visit=async(cdp,childSession)=>{
      let tree;
      try{tree=(await cdp.send('Page.getFrameTree')).frameTree;}catch(e){errors.push(e.message);return;}
      const snapshot=await cdp.send('DOMSnapshot.captureSnapshot',{computedStyles:[],includeDOMRects:true});
      const strings=snapshot.strings;
      const documents=new Map(snapshot.documents.map(d=>[strings[d.frameId],d]));
      const walk=async(ft)=>{
        const f=ft.frame,doc=documents.get(f.id);
        if(!doc)return; // OOPIF has its own session, visited below.
        const boxes=new Map();
        doc.layout.nodeIndex.forEach((ni,i)=>{
          const b=doc.layout.bounds[i];
          boxes.set(doc.nodes.backendNodeId[ni],[b[0]-doc.scrollOffsetX,b[1]-doc.scrollOffsetY,b[2],b[3]]);
        });
        const world=await cdp.send('Page.createIsolatedWorld',{frameId:f.id,worldName:'aresos-check'});
        const viewport=await cdp.send('Runtime.evaluate',{expression:'({width:innerWidth,height:innerHeight})',contextId:world.executionContextId,returnByValue:true});
        const size=viewport.result.value;
        const ax=await cdp.send('Accessibility.getFullAXTree',{frameId:f.id});
        const text=[];
        for(const n of ax.nodes){
          if(n.ignored)continue;
          const role=n.role?.value,name=n.name?.value||'';
          if(role==='StaticText'){text.push(name);continue;}
          if(['InlineTextBox','generic','none'].includes(role))continue;
          const box=boxes.get(n.backendDOMNodeId)||null;
          const ref=n.backendDOMNodeId?`${childSession||'root'}:${f.id}:${f.loaderId}:${n.backendDOMNodeId}`:null;
          const properties=Object.fromEntries((n.properties||[]).map(p=>[p.name,p.value.value]));
          const state={};
          for(const prop of ['checked','selected','disabled','required','invalid','expanded','focused','modal','multiselectable'])if(prop in properties)state[prop]=properties[prop];
          const onScreen=!!box && box[0]<size.width&&box[1]<size.height&&box[0]+box[2]>0&&box[1]+box[3]>0;
          const row={ref,frame:f.id,role,name,...(n.value?{value:n.value.value}:{}),state,box,onScreen};
          all.push(row);
          if(ref)this.refs.set(ref,{cdp,frameId:f.id,loaderId:f.loaderId,backendNodeId:n.backendDOMNodeId,contextId:world.executionContextId,role,name});
        }
        frames.push({id:f.id,parent:f.parentId||null,url:f.url,document:f.loaderId,coordinates:'frame viewport CSS pixels',viewport:size,text:text.join('\n')});
        for(const child of ft.childFrames||[])await walk(child);
      };
      await walk(tree);
    };
    await visit(this.cdp);
    for(const s of this.children.values())await visit(s.cdp,s.sessionId);
    return {format:'aresos-check-ax-layout-v1',frames,elements:all.slice(offset,offset+limit),offset,total:all.length,next:offset+limit<all.length?offset+limit:null,errors,ms:Math.round((performance.now()-start)*100)/100};
  }
  async resolve(ref){
    const r=this.refs.get(ref);if(!r)throw new Error('STALE_REF: unknown reference');
    const tree=(await r.cdp.send('Page.getFrameTree')).frameTree;
    const find=t=>t.frame.id===r.frameId?t.frame:(t.childFrames||[]).map(find).find(Boolean);
    const frame=find(tree);
    if(!frame||frame.loaderId!==r.loaderId)throw new Error('STALE_REF: document changed');
    try{
      const obj=await r.cdp.send('DOM.resolveNode',{backendNodeId:r.backendNodeId,executionContextId:r.contextId});
      const check=await r.cdp.send('Runtime.callFunctionOn',{objectId:obj.object.objectId,functionDeclaration:'function(){return this.isConnected}',returnByValue:true});
      if(!check.result.value)throw new Error('removed');
      return {...r,objectId:obj.object.objectId};
    }catch(e){throw new Error('STALE_REF: '+e.message);}
  }
  async act(ref,action,value){
    const r=await this.resolve(ref);
    if(action==='file')return r.cdp.send('DOM.setFileInputFiles',{backendNodeId:r.backendNodeId,files:[value]});
    const functions={
      click:'function(){this.scrollIntoView({block:"center"});this.click();}',
      focus:'function(){this.focus();}',
      fill:'function(value){if(this.disabled)throw Error("disabled");const proto=this.tagName==="TEXTAREA"?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,"value").set.call(this,value);this.dispatchEvent(new Event("input",{bubbles:true}));this.dispatchEvent(new Event("change",{bubbles:true}));return this.value;}',
      select:'function(value){this.value=value;this.dispatchEvent(new Event("input",{bubbles:true}));this.dispatchEvent(new Event("change",{bubbles:true}));return this.value;}',
      check:'function(value){if(this.checked!==value)this.click();return this.checked;}',
      scroll:'function(){this.scrollIntoView({block:"center"});return this.getBoundingClientRect().y;}'
    };
    if(!functions[action])throw new Error('Unknown action');
    const result=await r.cdp.send('Runtime.callFunctionOn',{objectId:r.objectId,functionDeclaration:functions[action],arguments:[{value}],returnByValue:true});
    if(result.exceptionDetails)throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result?.value;
  }
  close(){
    this.cdp.off('Target.attachedToTarget',this.onAttached);this.cdp.off('Target.detachedFromTarget',this.onDetached);
    if(!this.frameSessions)for(const c of this.children.values())c.cdp.close?.();
  }
}
