// This source is injected into the disposable CI copy by prepare.mjs.
// Use the current reader and keep raw field values out of the observer reply.
export const observerCommands=`
    if(command.name==='fixture_observe_tabs'){
      const observed=await everyTab();
      return {session:observed.session,items:observed.tabs.map(({front,group,...row})=>({
        ...row,focused:front,controlled:group,cleanup_pending:releasing.has(row.tab),
      }))};
    }
    if(command.name==='fixture_observe_page'){
      const observed=await facts(tab,null,'outline',expires);
      const view=await sha256Hex(JSON.stringify(observed.frames));
      return {dialog:observed.dialog,rows:observed.frames.flatMap(frame=>frame.nodes.map(node=>({
        reference:{tab,session,frame:frame.frame,document:frame.document,element:'e'+node.id,view},
        expected:{name:node.name||'',role:node.role},
      })))};
    }
`;
