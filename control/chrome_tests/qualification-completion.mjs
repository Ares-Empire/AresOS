// Observe the real harness's final exit without changing its exceptions or tests.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';

export const LOGICAL_FAILURE='Strict owner-input and page-forgery regressions failed';
export function recordCompletion(directory, identity, outcome) {
  const digests=Object.fromEntries(['qualification-result.json','matrices.json'].map(name=>
    [name,createHash('sha256').update(fs.readFileSync(path.join(directory,name))).digest('hex')]));
  fs.writeFileSync(path.join(directory,'qualification-complete.json'),JSON.stringify({format:1,identity,outcome,digests}));
}
export function completedFailure(error) {
  return error instanceof AggregateError && error.message===LOGICAL_FAILURE && error.errors.length>0;
}

export function observeHarness(directory, identity){
  fs.rmSync(path.join(directory,'qualification-complete.json'),{force:true});
  let logical=false;
  process.on('uncaughtExceptionMonitor',error=>{
    if(completedFailure(error)){
      logical=true;
      recordCompletion(directory,identity,'failure');
    }
  });
  process.on('exit',code=>{
    if(code===0 && !logical)recordCompletion(directory,identity,'success');
  });
}
if(path.resolve(process.argv[1] || '').endsWith('/control/chrome/ci/browser.mjs'))
  observeHarness('/out',JSON.parse(process.env.QUALIFICATION_PAIR));
