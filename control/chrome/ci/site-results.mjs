// Keep a completed adapter failure in the final matrix without treating a crash
// or a partial suite as completion. The browser entry point still exits nonzero.
import {REQUIRED} from './verdicts.mjs';

const expected=Object.values(REQUIRED).flat().filter(name=>name.includes(' ADAPTER ')).sort();
function complete(rows){
  return Array.isArray(rows)&&rows.every(row=>typeof row?.passed==='boolean')&&
    JSON.stringify(rows.map(row=>row.name).sort())===JSON.stringify(expected);
}
export async function collectSiteResults(run){
  try{
    const rows=await run();
    if(!complete(rows))throw Error('Incomplete adapter fixture result inventory');
    return rows;
  }catch(error){
    if(!(error instanceof AggregateError)||error.message!=='Adapter requirements failed; see adapters.json and adapters-receiver.jsonl'||
        !complete(error.results)||!error.results.some(row=>!row.passed))throw error;
    return error.results;
  }
}
