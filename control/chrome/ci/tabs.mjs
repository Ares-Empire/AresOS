export async function allTabs(call){
  const items=[];let cursor;
  do{const page=await call('tabs',{limit:10,...(cursor?{cursor}:{})});items.push(...page.items);cursor=page.cursor;}while(cursor);
  return {items};
}
