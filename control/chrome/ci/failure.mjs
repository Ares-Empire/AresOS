import fs from 'node:fs';
import {verdicts} from './verdicts.mjs';

// Some cases start an input, wait for an independent observation, then await the input.
// Observe rejection immediately so Node cannot terminate the shard during that wait.
// The case still awaits the original promise and receives its original exception.
export function pendingCheck(promise){
  promise.catch(()=>{});
  return promise;
}

export async function recordCheck(results,name,run){
  let row;
  try{
    await run();
    row={name,passed:true};
  }catch(error){
    row={name,passed:false,error:String(error?.stack??error)};
    console.error(name,'FAIL',row.error);
  }
  results.push(row);
  return row;
}

// Keep partial evidence if a later fixture crashes or the job times out.
export function writePartialResults(results,baseline,write=fs.writeFileSync){
  write('/out/matrices.json',JSON.stringify(results,null,2));
  write('/out/qualification-result.json',JSON.stringify(verdicts(results,baseline,{}),null,2));
}

export function assertChecksPassed(results,message){
  const failed=results.filter(row=>!row.passed);
  if(!failed.length)return;
  const summary='Failed browser checks ('+failed.length+'):\n'+failed.map(row=>row.name).join('\n');
  console.error(summary);
  throw new AggregateError(failed.map(row=>Error(row.name+'\n'+row.error)),message??summary);
}
