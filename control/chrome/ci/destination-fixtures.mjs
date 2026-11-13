// Destination authority must be read from the action's document, including inherited bases.
export const destinationSources=['a','area','svg-href','svg-xlink','form-action','button-formaction','input-formaction'];
export function destinationRows(){
  return ['top','blank','srcdoc'].flatMap(frame=>[
    ...destinationSources.flatMap(source=>['base','attribute'].map(change=>({source,frame,change}))),
    ...['button-formaction','input-formaction'].map(source=>({source,frame,change:'owner'})),
    ...['a','form-action','button-formaction','input-formaction'].map(source=>({source,frame,change:'target'})),
  ]).concat(['svg-href','svg-xlink'].flatMap(source=>['animation','animation-target','svg-self'].map(change=>({source,frame:'top',change})))).map(row=>({...row,id:`post18d-destination-${row.source}-${row.frame}-${row.change}`}));
}
export function destinationPage(url){
  const source=url.searchParams.get('source'),frame=url.searchParams.get('frame'),change=url.searchParams.get('change'),id=url.searchParams.get('id');
  const relative='receive?case='+encodeURIComponent(id),base='<base id="destination-base" href="/first/" target="sink-first">';
  let content;
  if(source==='a')content=`<a id="asking" href="${relative}">Delete</a>`;
  else if(source==='area')content=`<img alt="Map" usemap="#map" width="160" height="70" src="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22160%22 height=%2270%22%3E%3Crect width=%22160%22 height=%2270%22/%3E%3C/svg%3E"><map name="map"><area id="asking" alt="Delete" href="${relative}" shape="rect" coords="0,0,160,70"></map>`;
  else if(source.startsWith('svg'))content=`<svg width="160" height="70" xmlns:xlink="http://www.w3.org/1999/xlink"><a id="asking" aria-label="Delete" ${change==='svg-self'?'':'target="sink-first"'} ${source==='svg-xlink'?'xlink:href':'href'}="${relative}"><rect width="160" height="70"/><text x="10" y="35">Delete</text></a></svg>`;
  else{
    const control=source==='input-formaction'?`<input type="submit" value="Delete"`:`<button type="submit"`;
    const ending=source==='input-formaction'?'>':'>Delete</button>';
    content=`<form id="first" method="post" action="${relative}"><input name="draft" value="Destination fixture"></form><form id="second" method="post" action="/second/${relative}"></form>${control} id="asking" form="first"${source==='form-action'?'':` formaction="${relative}"`}${ending}`;
  }
  if(frame!=='top')content=content.replaceAll('id="asking"','id="asking" target="sink-first"').replaceAll('<form id=','<form target="sink-first" id=');
  const sinks='<iframe name="sink-first" src="/?case=destination-sink&name=first" hidden></iframe><iframe name="sink-second" src="/?case=destination-sink&name=second" hidden></iframe>';
  const body=base+(frame==='top'?content+sinks:'<iframe id="inline" width="700" height="350"></iframe>'+sinks);
  const script=`const child=${frame==='top'?'null':"document.querySelector('#inline')"};
    ${frame==='srcdoc'?`child.srcdoc=${JSON.stringify(content)};`:frame==='blank'?`child.contentDocument.body.innerHTML=${JSON.stringify(content)};`:''}
    globalThis.reviewChange=()=>{
      const doc=child?child.contentDocument:document,node=doc.querySelector('#asking');
      ${change.startsWith('animation')?`const animation=doc.createElementNS('http://www.w3.org/2000/svg','set');animation.setAttribute('attributeName',${JSON.stringify(change==='animation-target'?'target':source==='svg-xlink'?'xlink:href':'href')});animation.setAttribute('to',${JSON.stringify(change==='animation-target'?'sink-second':'/second/'+relative)});animation.setAttribute('dur','indefinite');node.append(animation);animation.beginElement();`:(change==='base'||change==='svg-self')?(frame==='top'?"document.querySelector('#destination-base').href='/second/';":"const base=doc.createElement('base');base.href='http://fixture.test:8765/second/';doc.head.prepend(base);"):change==='target'?(frame==='top'?"document.querySelector('#destination-base').target='sink-second';":source==='a'?"node.setAttribute('target','sink-second');":source==='form-action'?"doc.querySelector('#first').setAttribute('target','sink-second');":"node.setAttribute('formtarget','sink-second');"):change==='owner'?"node.setAttribute('form','second');node.removeAttribute('formaction');":source==='form-action'?`doc.querySelector('#first').setAttribute('action','/second/${relative}');`:source.includes('formaction')?`node.setAttribute('formaction','/second/${relative}');`:source==='svg-xlink'?`node.setAttributeNS('http://www.w3.org/1999/xlink','xlink:href','/second/${relative}');`:`node.setAttribute('href','/second/${relative}');`}
    };`;
  return {body,script};
}
