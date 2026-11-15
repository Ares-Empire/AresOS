// Same timing overlay for current and historical bundles; no authority or payload changes.
export function instrumentLatencyBackground(source){
  const helper=`
let __latencyContext=null,__latencySequence=0,__latencyWire=null;
async function __latencyTime(stage,fn){const context=__latencyContext,start=performance.now();try{return await fn();}finally{port?.postMessage({event:'latency_stage',stage,milliseconds:performance.now()-start,context});}}
`;
  source=source.replace("import {POLICY} from './policy.js';", "import {POLICY} from './policy.js';\n"+helper);
  source=source.replace("effectStarted=false;dispatchEpoch=null;audit({command:message.command?.name,phase:'begin'});","__latencyWire=message.id;effectStarted=false;dispatchEpoch=null;audit({command:message.command?.name,phase:'begin'});");
  source=source.replace('function expireDefaults(tab,nonce,delay=POLICY.holdMs){','function expireDefaults(tab,nonce,delay=POLICY.holdMs){const __expiryContext=__latencyContext;').replace('networkHolds.delete(tab);rules().catch(()=>{});','networkHolds.delete(tab);const previous=__latencyContext;__latencyContext=__expiryContext;try{rules().catch(()=>{});}finally{__latencyContext=previous;}');
  source=source.replace('await new Promise(resolve=>setTimeout(resolve,POLICY.holdMs+25));',"await __latencyTime('post_input_observation_wait',()=>new Promise(resolve=>setTimeout(resolve,POLICY.holdMs+25)));");
  const wrappers=`
const __content=typeof content==='function'?content:null;if(__content)content=(tab,frame,command,parameters={},document=null)=>__content(tab,frame,command,{...parameters,__latency_wire:__latencyContext?.wire},document);
const __dispatch=dispatch;dispatch=async command=>{const previous=__latencyContext;__latencyContext={sequence:++__latencySequence,command:command.name,wire:__latencyWire};try{return await __latencyTime('extension_total',()=>__dispatch(command));}finally{__latencyContext=previous;}};
for(const [stage,get,set]of [
 ['session_rule_add',()=>typeof holdDefaults==='function'?holdDefaults:null,value=>{holdDefaults=value;}],
 ['session_rule_update',()=>rules,value=>{rules=value;}],
 ['frame_facts',()=>facts,value=>{facts=value;}],
 ['finish_input',()=>finishFrames,value=>{finishFrames=value;}],
 ['post_input_steps',()=>collectSteps,value=>{collectSteps=value;}],
 ['page_observation',()=>typeof observation==='function'?observation:null,value=>{observation=value;}]
]){const original=get();if(original)set((...args)=>__latencyTime(stage==='session_rule_update'&&typeof networkHolds!=='undefined'&&!networkHolds.size?'session_rule_remove':stage,()=>original(...args)));}
`;
  // Before connect installs any command listeners, after the function declarations.
  return source.replace('async function connect() {',wrappers+'\nasync function connect() {');
}
export function instrumentLatencyReader(source){
  const helper=`
let __latencyReaderWire=null;
function __latencyRead(stage,fn){const start=performance.now();try{return fn();}finally{chrome.runtime.sendMessage({event:'latency_reader',context:{wire:__latencyReaderWire},stage,milliseconds:performance.now()-start}).catch(()=>{});}}
`;
  source=source.replace("  'use strict';", "  'use strict';\n"+helper);
  source=source.replace('function onMessage(message, sender, reply, filesReady=false) {','function onMessage(message, sender, reply, filesReady=false) {__latencyReaderWire=message.__latency_wire;');
  if(source.includes('function composeText('))source=source.replace('  guard.reader(',"  const __composeText=composeText;composeText=(...args)=>__latencyRead('compose_binding',()=>__composeText(...args));\n  guard.reader(");
  source=source.replace("clipboard:(route,generation)=>{chrome.runtime.sendMessage({event:'clipboard_write',document:documentId,route,generation}).catch(()=>{});}","clipboard:(route,generation)=>{__latencyRead('clipboard_hooks',()=>chrome.runtime.sendMessage({event:'clipboard_write',document:documentId,route,generation}).catch(()=>{}));}");
  source=source.replace('const clipboard=guard.clipboard?.();',"const clipboard=__latencyRead('clipboard_hooks',()=>guard.clipboard?.());");
  return source;
}
