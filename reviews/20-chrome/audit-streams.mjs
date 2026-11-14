// Evidence readers only: never launch a browser or retain a whole large log.
import fs from 'node:fs';
import crypto from 'node:crypto';

export async function* jsonLines(file){
  let pending='';
  for await(const chunk of fs.createReadStream(file,{encoding:'utf8',highWaterMark:64*1024})){
    pending+=chunk;
    let end;
    while((end=pending.indexOf('\n'))!==-1){
      const line=pending.slice(0,end);pending=pending.slice(end+1);
      if(line)yield JSON.parse(line);
    }
  }
  if(pending)yield JSON.parse(pending);
}

// Keep completeIngress's offset, interruption and EOF checks, yielding each
// reconstructed reply instead of holding every reply in memory together.
export async function* completeIngressStream(file){
  let pending=null;
  for await(const row of jsonLines(file)){
    if(typeof row?.json_fragment!=='string'){if(pending)throw Error('Interrupted audit fragment');yield row;continue;}
    if(row.offset===0){if(pending)throw Error('Overlapping audit fragment');pending={text:'',total:row.total};}
    if(!pending||row.offset!==pending.text.length||row.total!==pending.total)throw Error('Invalid audit fragment offset');
    pending.text+=row.json_fragment;
    if(pending.text.length===pending.total){yield JSON.parse(pending.text);pending=null;}
    else if(pending.text.length>pending.total)throw Error('Oversize audit fragment');
  }
  if(pending)throw Error('Incomplete audit fragment');
}

export async function containsText(file,needle){
  if(!needle)throw Error('Empty evidence scan needle');
  let tail='';
  for await(const chunk of fs.createReadStream(file,{encoding:'utf8',highWaterMark:64*1024})){
    const text=tail+chunk;if(text.includes(needle))return true;
    tail=needle.length===1?'':text.slice(-(needle.length-1));
  }
  return false;
}

export async function digestFile(file){
  const digest=crypto.createHash('sha256');
  for await(const chunk of fs.createReadStream(file))digest.update(chunk);
  return digest.digest('hex');
}
