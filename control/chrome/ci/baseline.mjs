import fs from 'node:fs';
import assert from 'node:assert/strict';
import {setTimeout as delay} from 'node:timers/promises';
import {fixtures} from './fixture.mjs';
import {withoutExtension} from './compatibility.mjs';
if(process.platform!=='linux'||process.env.GITHUB_ACTIONS!=='true'||!fs.existsSync('/.dockerenv'))throw Error('GitHub Linux container only');
assert.equal(fs.existsSync('/out/extension.json'),false,'baseline runs before extension packaging or installation');
const fixture=await fixtures();
async function eventually(fn,label){const deadline=Date.now()+20000;while(Date.now()<deadline){const value=await fn();if(value)return value;await delay(100);}throw Error(label);}
try{await withoutExtension({fixture,eventually,descriptor:fs.openSync('/out/baseline-chrome.txt','a')});console.log('Native compatibility baseline measured before extension installation');}
finally{fixture.close();}
