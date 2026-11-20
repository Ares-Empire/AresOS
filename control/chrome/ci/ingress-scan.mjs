import fs from 'node:fs';

const BOUNDARY='/out/browser-boundary.jsonl';
export const boundaryLog={
  size:()=>fs.statSync(BOUNDARY).size,
  since(offset){
    const descriptor=fs.openSync(BOUNDARY,'r');
    try{
      const length=Math.max(0,fs.fstatSync(descriptor).size-offset),buffer=Buffer.alloc(length);
      const read=fs.readSync(descriptor,buffer,0,length,offset);
      return buffer.toString('utf8',0,read);
    }finally{fs.closeSync(descriptor);}
  },
};

// Audit fragments are consecutive, offset-bound parts of one browser reply.
export function completeIngress(text){
  const result=[];let pending=null;
  for(const line of text.split('\n').filter(Boolean)){
    const row=JSON.parse(line);
    if(typeof row?.json_fragment!=='string'){if(pending)throw Error('Interrupted audit fragment');result.push(row);continue;}
    if(row.offset===0){if(pending)throw Error('Overlapping audit fragment');pending={text:'',total:row.total};}
    if(!pending||row.offset!==pending.text.length||row.total!==pending.total)throw Error('Invalid audit fragment offset');
    pending.text+=row.json_fragment;
    if(pending.text.length===pending.total){result.push(JSON.parse(pending.text));pending=null;}
    else if(pending.text.length>pending.total)throw Error('Oversize audit fragment');
  }
  if(pending)throw Error('Incomplete audit fragment');return result;
}

// Protocol commands legitimately return null; retain those rows for the value
// scan while selecting event records independently.
export function protocolEvents(rows){return rows.filter(row=>row?.protocol_event).map(row=>row.protocol_event);}

export function auditRows(offset,keys,log=boundaryLog){
  const prefixes=[keys].flat().map(key=>'{"'+key+'":');
  return log.since(offset).split('\n').slice(0,-1)
    .filter(line=>prefixes.some(prefix=>line.startsWith(prefix))).map(line=>JSON.parse(line));
}
