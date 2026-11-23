import assert from 'node:assert/strict';

// Match the service's ASCII JSON encoding, including surrogate pairs.
export const asciiBytes=value=>Buffer.byteLength(JSON.stringify(value).replace(/[\u007f-\uffff]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0')));
// Only reference identities vary between processes. Keep their equality and
// order; no page text, whitespace, counts, roles or addresses are rewritten.
export function stableReferences(text){
  const ids=new Map();
  return text.replace(/\b[bcdfghjklmnpqrstvwxyz]{5}\d+\b/g,ref=>{if(!ids.has(ref))ids.set(ref,'REF'+(ids.size+1));return ids.get(ref);});
}
export function completeEscapes(text){
  for(let i=0;i<text.length;i++)if(text[i]==='\\'){
    assert.ok(i+1<text.length,'page split a backslash escape');
    if(text[i+1]==='u'){assert.match(text.slice(i+2,i+6),/^[0-9a-f]{4}$/);i+=5;}else i++;
  }
}
// Everything a page wrote must stay in a quoted run. Once those runs are
// removed, only the tool's grammar remains. Also reject raw direction/control
// characters, so an escaped quote cannot hide a new physical outline line.
export function hostileGrammar(text){
  assert.doesNotMatch(text.replaceAll('\n',''),/[\p{Cc}\p{Cf}\p{Cs}\p{Zl}\p{Zp}]/u);
  const skeleton=text.replace(/"(?:[^"\\]|\\.)*"/g,'""');
  assert.doesNotMatch(skeleton,/[^a-z0-9A-Z\s".,:()|=→·›\[\]…+?\/%&;_#~@-]/,'page text escaped its quotes');
  for(const line of skeleton.split('\n')){
    assert.doesNotMatch(line,/[^\\]\\|^\\/,'unquoted escape');
    assert.ok(!line.includes('"')||line.replaceAll('""','').indexOf('"')===-1,'unbalanced quote');
  }
  return skeleton;
}
export function visible(text){
  return Array.from(text,c=>/[\p{Cc}\p{Cf}\p{Cs}\p{Zl}\p{Zp}]/u.test(c)?'\\u'+c.codePointAt(0).toString(16).padStart(4,'0'):c==='\\'?'\\\\':c).join('');
}
export const quoted=text=>'"'+visible(text).replaceAll('"','\\"')+'"';
export const squeezed=text=>text.replace(/\s+/g,' ').trim();
