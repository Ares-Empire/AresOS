// Translate the inherited fixture vocabulary at the transport boundary.
// Explicit public calls and the measured baseline go straight to the wire.
import assert from 'node:assert/strict';

const STEPS={click:[],fill:['text'],select:['value'],check:['checked'],press:['key'],scroll:['y']};
const TOOLS_WITH_REFS=new Set([...Object.keys(STEPS),'upload']);
const LOSS_MESSAGE='This action may discard work. Nothing was done; inspect the loss report.';
const QUOTED=/"(?:[^"\\]|\\.)*"/g;
const REFERENCE=/ ([bcdfghjklmnpqrstvwxyz]{5}\d+)(?=$| · in )/;
const bestRoles=new Set(['button','link','textbox','searchbox','combobox','checkbox','radio','option']);

const fields=(source,keys)=>Object.fromEntries(keys.filter(key=>key in source).map(key=>[key,source[key]]));
const targetArgs=({reference,expected})=>({reference,expected});

function failure(result,code,message,content){
  const {data,...rest}=result;
  return {...rest,ok:false,error:{code,message,...(content?{untrusted_content:content}:{})}};
}

function lossReport(location,step){
  assert.equal(location.code,'reload_required');
  assert.equal(location.message,LOSS_MESSAGE);
  assert.ok(location.untrusted_content?.loss,'loss belongs in untrusted_content.loss');
  const {loss}=location.untrusted_content;
  if(step===undefined)assert.equal('step' in loss,false);
  else assert.equal(loss.step,step);
  for(const field of loss.fields??[])assert.ok(!location.message.includes(field.description),'field description stays out of trusted prose');
  return {loss};
}

function matchingRefs(outline,name){
  const quoted=name&&'"'+name.replaceAll('"','\\"')+'"';
  return outline.split('\n').flatMap(line=>{
    const [,role,rest]=line.match(/^\s*([a-z][a-z0-9-]*) (.*)$/)??[];
    if(!rest || (quoted ? !rest.startsWith(quoted) : rest.startsWith('"')))return [];
    const ref=(' '+rest.replace(QUOTED,'""')).match(REFERENCE)?.[1];
    return ref?[{role,ref}]:[];
  });
}

export function harnessTools({wire,modern,eventually,currentTab}){
  async function outline(tab,query={}){
    const result=await wire('chrome_read',{tab,...query});
    if(!result.ok)return result;
    const [entry]=result.data.reads;
    if(entry.error)return failure(result,entry.error.code,entry.error.message,entry.untrusted_content);
    return {...result,data:entry};
  }

  async function readRows(tab=currentTab()){
    let tree='',cursor;
    do{
      const result=await wire('read',{tab,...(cursor?{cursor}:{})});
      assert.ok(result.ok,JSON.stringify(result.error));
      tree+=result.data.untrusted_content.tree;
      cursor=result.data.cursor;
    }while(cursor);
    return tree.split('\n').filter(line=>line.startsWith('{')).map(JSON.parse);
  }

  async function selectedTarget(row,rows){
    if(!row)return;
    const old=targetArgs(row);
    if(!await modern())return old;
    const {name,role}=row.expected,{tab}=row.reference;
    const sameName=rows.filter(item=>item.expected.name===name);
    const peers=sameName.filter(item=>item.expected.role===role);
    const query=name?{find:name,max:40000}:{full:true,max:40000};
    let cursor,text='';
    do{
      const result=await outline(tab,{...query,...(cursor?{cursor}:{})});
      assert.ok(result.ok,JSON.stringify(result.error));
      cursor=result.data.cursor;
      text+=result.data.untrusted_content.outline;
    }while(cursor);
    const shown=matchingRefs(text,name);
    const sameRole=shown.filter(item=>item.role===role);
    // Some native controls have a more specific role in the outline. A
    // role change is safe to match by name only if both reads show one match.
    const selected=sameRole.length===peers.length?sameRole[peers.indexOf(row)]:
      sameName.length===1&&shown.length===1?shown[0]:undefined;
    assert.ok(selected,'a short reference for '+role+' '+JSON.stringify(name));
    return {...old,ref:selected.ref};
  }

  async function target(label,tab=currentTab()){
    return eventually(async()=>{
      const rows=await readRows(tab);
      const named=rows.filter(row=>row.expected.name===label);
      return selectedTarget(named.find(row=>bestRoles.has(row.expected.role))||named[0],rows);
    },label);
  }

  function step(verb,args){
    assert.equal(typeof args.ref,'string','select a public reference before '+verb);
    if(verb==='scroll')assert.ok(!args.x,'chrome_do scroll is vertical');
    return {do:verb,ref:args.ref,...fields(args,STEPS[verb])};
  }

  async function doResult(result,{committed=false}={}){
    if(!result.ok)return result;
    const {data}=result;
    const [entry]=data.steps;
    const content=data.untrusted_content;
    const {prepared}=data;
    if(entry?.outcome==='prepared'){
      assert.equal(prepared.length,1,'one prepared operation for one asking step');
      return {...result,data:prepared[0]};
    }
    let page;
    if(entry?.operation_id&&(committed||entry.outcome==='unknown')){
      const status=await wire('chrome_operation_status',{operation_id:entry.operation_id});
      assert.ok(status.ok,JSON.stringify(status.error));
      page=status.data.operation.stages.page?.untrusted_content;
      if(committed)assert.ok(page,'committed browser evidence for '+entry.operation_id);
    }
    if(entry?.code && (entry.outcome!=='unknown'||!page)){
      const untrusted=entry.code==='reload_required'?lossReport({...entry,untrusted_content:content},0):
        content.now?{now:content.now}:undefined;
      return failure(result,entry.code,entry.message,untrusted);
    }
    if(!entry&&data.error)return failure(result,data.error.code,data.error.message);
    assert.ok(entry&&!data.deadline,'expected a completed one-step call '+JSON.stringify(data));
    return {...result,data:{operation_id:entry.operation_id,
      untrusted_content:page??{dialog:content.dialog},
      followups:[...prepared,...content.stopped]}};
  }

  async function rpc(action,args={},options={}){
    if(action.startsWith('chrome_')||action.startsWith('control_')||options.legacy||!await modern())return wire(action,args);
    if(TOOLS_WITH_REFS.has(action)){
      const tab=args.reference?.tab??args.tab;
      if(action==='upload'){
        assert.equal(typeof args.ref,'string','select a public reference before upload');
        return wire('chrome_upload',{tab,...fields(args,['ref','path','file'])});
      }
      return doResult(await wire('chrome_do',{tab,steps:[step(action,args)],...fields(args,['discard_unsaved'])}),options);
    }
    if(action==='dialog'){
      return doResult(await wire('chrome_do',{tab:args.tab,steps:[{do:'dialog',...fields(args,['accept','text'])}]}),options);
    }
    if(action==='fill_form'){
      const [first]=args.fields,tab=first.reference.tab;
      assert.ok(args.fields.every(field=>field.reference.tab===tab),'one tab for a fill batch');
      const result=await wire('chrome_do',{tab,steps:args.fields.map(field=>step('fill',field))});
      if(!result.ok)return result;
      const {steps,not_run}=result.data;
      if(steps[0]?.code==='readonly_site')return doResult(result);
      return {...result,data:{completed:steps.filter(entry=>['done','unchanged'].includes(entry.outcome)),
        remaining:not_run+steps.filter(entry=>!['done','unchanged'].includes(entry.outcome)).length}};
    }
    if(action==='open'){
      const result=await wire('chrome_open',args);
      if(!result.ok)return result;
      const {data}=result;
      return {...result,data:{...data,untrusted_content:{...data.untrusted_content,tab:data.tab}}};
    }
    if(action==='navigate'){
      const {direction,...input}=args;
      const result=await wire('chrome_go',{...input,...(direction?{to:direction}:{})});
      if(!result.ok&&result.error.code==='reload_required')lossReport(result.error);
      return result;
    }
    if(action==='take_tab'){
      const list=await wire('chrome_tabs');
      if(!list.ok)return list;
      return wire('chrome_take',{tab:args.tab,seen:list.data.seen});
    }
    if(action==='release_tab')return wire('chrome_release',args);
    if(action==='close_tab'){
      const {tab,...input}=args;
      const result=await wire('chrome_close',{tabs:[tab],...input});
      if(!result.ok)return result;
      const {closed,kept}=result.data;
      if(kept.length){
        assert.equal(kept[0].tab,tab);
        const content=kept[0].code==='reload_required'?lossReport(kept[0]):undefined;
        return failure(result,kept[0].code,kept[0].message,content);
      }
      assert.deepEqual(closed.map(item=>item.tab),[tab],'the named tab closed');
      return result;
    }
    if(action==='wait'){
      const {tab,text,timeout_ms}=args;
      const result=await wire('chrome_do',{tab,steps:[{do:'wait',until:{text},timeout_ms}]});
      if(!result.ok)return result;
      const [entry]=result.data.steps;
      if(!entry||!['done','timeout'].includes(entry.outcome))return doResult(result);
      return {...result,data:{condition_met:entry.outcome==='done'}};
    }
    if(action==='find'||action==='read'&&options.fullOutline){
      const {tab,text,...query}=args;
      const result=await outline(tab,action==='find'?{...query,find:text}:{...query,full:true,max:16000});
      if(!result.ok)return result;
      const {data}=result;
      return {...result,data:{...data,untrusted_content:{...data.untrusted_content,tree:data.untrusted_content.outline}}};
    }
    const result=await wire(action,args);
    if(action==='read'&&result.ok&&result.data.untrusted_content.dialog){
      const {dialog}=result.data.untrusted_content;
      const shown=await outline(args.tab);
      assert.ok(shown.ok,JSON.stringify(shown.error));
      assert.deepEqual(shown.data.untrusted_content.dialog,{kind:dialog.kind,text:dialog.text});
    }
    return result;
  }

  async function call(action,args={},options={}){
    const result=await rpc(action,args,options);
    assert.ok(result.ok,JSON.stringify(result));
    return result.data;
  }

  return {rpc,call,readRows,target,selectedTarget};
}
