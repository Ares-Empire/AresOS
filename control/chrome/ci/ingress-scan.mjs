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
