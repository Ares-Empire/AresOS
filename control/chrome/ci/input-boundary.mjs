// Group 15: delay one real reader answer during the input's last facts read.
// The worker keeps running, including the input deadline and hold cleanup.
export function instrumentInputBoundary(source,exactly){
  const dispatch='async function dispatch(command,expires=null) {';
  source=exactly(source,dispatch,`let fixtureBoundaryTab=null,fixtureBoundaryRead=null;
function fixtureBoundaryAnswer(tab,message,options){
  const answer=fixtureSendMessage(tab,message,options),hold=fixtureBoundaryRead;
  if(!hold||hold.tab!==tab||message.command!=='facts'||hold.held)return answer;
  hold.held=true;
  const connection=port;
  return answer.then(async value=>{
    hold.trace('held',{remainingMs:hold.expires-performance.now(),answered:value?.ok===true});
    await new Promise(resolve=>setTimeout(resolve,Math.max(0,hold.expires+1000-performance.now())));
    hold.released=true;
    hold.trace('released',{remainingMs:hold.expires-performance.now(),sameConnection:port===connection});
    return value;
  });
}
async function fixtureBoundaryFacts(command,tab,reference,expires){
  if(tab!==fixtureBoundaryTab||command.name!=='input'||command.input?.verb!=='fill'||expires===null)return facts(tab,reference,false,expires);
  fixtureBoundaryTab=null;
  const trace=(phase,details)=>audit({fixture_input_boundary:{tab,operation:command.operation,session,phase,at:Date.now(),...details}});
  const hold={tab,expires,trace,held:false,released:false};fixtureBoundaryRead=hold;
  try{return await facts(tab,reference,false,expires);}
  catch(error){trace('setup-ended',{expired:expired(error),whileHeld:hold.held&&!hold.released});throw error;}
  finally{fixtureBoundaryRead=null;}
}
${dispatch}
  if(command.name==='fixture_hold_input_boundary'){fixtureBoundaryTab=command.tab;return {held:command.tab};}`);
  source=exactly(source,'fixtureSendMessage(tab,{command,...parameters},','fixtureBoundaryAnswer(tab,{command,...parameters},');
  return exactly(source,'  snapshot=await facts(tab,reference,false,expires);','  snapshot=await fixtureBoundaryFacts(command,tab,reference,expires);');
}
