// Four interception opportunities; node factories are always borrowed natives.
export function* mixedRows(){
  for(let mask=0;mask<16;mask++)for(const mode of ['open','closed'])for(const composed of [false,true])for(const order of ['before','after'])
    yield {mask,mode,composed,order,root:!!(mask&1),insert:!!(mask&2),listen:!!(mask&4),dispatch:!!(mask&8)};
}
export const browserMixes=()=>[...[...mixedRows()].filter(row=>[1,2,4,8,15].includes(row.mask)),...[...mixedRows()].filter(row=>[1,2,4,8].includes(row.mask)&&!row.composed).map(row=>({...row,foreign:true}))];
