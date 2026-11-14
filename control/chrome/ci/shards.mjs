export const BROWSER_SHARDS=['core','review','recheck2','recheck3','adapters','word-0','word-1','word-2','word-3'];
export const WORD_LABELS=['name','aria','title','value','labelledby','hidden_labelledby','label','role','formaction'];
export function wordShard(wordIndex,labelIndex){return 'word-'+((wordIndex*WORD_LABELS.length+labelIndex)%4);}
export function selected(shard,block){
  if(!shard)return true;
  if(!BROWSER_SHARDS.includes(shard))throw Error('Unknown browser shard');
  return block==='word'?shard.startsWith('word-'):shard===block;
}
export function wordInventory(words,shard=null){return words.flatMap((word,wi)=>WORD_LABELS.flatMap((label,li)=>!shard||wordShard(wi,li)===shard?['click','Enter','Space'].map(route=>'word-'+word+'-'+label+'-'+route):[]));}

// The same source inventory used by the qualification completeness regression.
export async function caseInventories(){
  const fs=await import('node:fs');
  const files={core:['matrices.mjs','destination-matrix.mjs','late-reader-matrix.mjs','late-binding-matrix.mjs','animated-default-matrix.mjs'],review:['review-matrices.mjs'],recheck2:['recheck2-matrices.mjs','popups.mjs'],recheck3:['recheck3-matrices.mjs'],adapters:['sites/matrices.mjs']};
  return Object.fromEntries(Object.entries(files).map(([block,names])=>[block,names.flatMap(file=>[...fs.readFileSync('control/chrome/ci/'+file,'utf8').matchAll(/await check\('([^']+)'/g)].flatMap(match=>match[1]==='GROUP 10 adapter '?['gmail','whatsapp','github','gemini','deezer'].map(site=>match[1]+site):[match[1]])).filter(name=>name!=='GROUP 1 what asks word/label/key matrix').sort()]));
}
