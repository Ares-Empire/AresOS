// Keep the receiver's actual rows beside each temporal assertion.
export function receiverSnapshot(arrivals,id,phase){
  const matching=arrivals.filter(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')===id);
  return {id,phase,count:matching.length,arrivals:matching};
}
