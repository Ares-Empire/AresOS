import fs from 'node:fs';
import {verdicts} from './verdicts.mjs';

export function failBrowserCase(results,baseline,error,write=fs.writeFileSync){
  write('/out/matrices.json',JSON.stringify(results,null,2));
  write('/out/qualification-result.json',JSON.stringify(verdicts(results,baseline,{}),null,2));
  throw error;
}
