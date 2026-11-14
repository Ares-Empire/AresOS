// Destination authority must be read from the action's document, including inherited bases.
export const destinationSources=['a','area','svg-href','svg-xlink','form-action','button-formaction','input-formaction'];
export function destinationRows(){
  return ['top','blank','srcdoc'].flatMap(frame=>[
    ...destinationSources.flatMap(source=>['base','attribute'].map(change=>({source,frame,change}))),
    ...['button-formaction','input-formaction'].map(source=>({source,frame,change:'owner'})),
    ...['a','form-action','button-formaction','input-formaction'].map(source=>({source,frame,change:'target'})),
  ]).concat(['svg-href','svg-xlink'].flatMap(source=>['animation','animation-target','svg-self'].map(change=>({source,frame:'top',change}))))
    .concat(finalTargetRows()).map(row=>({...row,id:`post18d-destination-${row.source}-${row.frame}-${row.change}`}));
}
// Final F3: each browsing-target route the reader resolves itself, plus the
// target change on area, the plain SVG target change and form-owner changes
// beyond formaction controls.
export function finalTargetRows(){
  return [
    ...['top','blank','srcdoc'].flatMap(frame=>[
      ...['area','svg-href','svg-xlink'].map(source=>({source,frame,change:'target'})),
      {source:'form-action',frame,change:'owner'},
    ]),
    ...['form-action','button-formaction','input-formaction'].map(source=>({source,frame:'top',change:'owner-target'})),
    ...['a','area','form-action','button-formaction','input-formaction'].map(source=>({source,frame:'top',change:'decoy-target'})),
    ...['newline','bracket'].flatMap(kind=>['a','form-action'].map(source=>({source,frame:'top',change:`sanitize-${kind}-target`}))),
    ...['svg-href','svg-xlink'].map(source=>({source,frame:'top',change:'xlink-show'})),
    ...['a','area','form-action','button-formaction'].map(source=>({source,frame:'top',change:'empty-target'})),
  ];
}
// Window names that the HTML sanitising rule must leave alone: a newline
// without "<", or "<" without a newline.
export function sinkNames(change){
  if(change==='sanitize-newline-target')return {first:'sink\nfirst',second:'sink\nsecond'};
  if(change==='sanitize-bracket-target')return {first:'sink<first',second:'sink<second'};
  return {first:'sink-first',second:'sink-second'};
}
// What the question must bind before and after the page's change, and where
// Chrome then navigates. An empty target follows Chrome: the base target.
// Approval descriptions pass through visible(), which escapes a newline;
// Chrome's own window name (sink) stays raw.
export function destinationExpectation({change}){
  const names=sinkNames(change),targetChange=change.endsWith('target')||change==='xlink-show';
  const before=change==='svg-self'?'_self':change==='xlink-show'?'_blank':names.first;
  const after=['svg-self','xlink-show'].includes(change)?'_self':targetChange?names.second:names.first;
  const shown=value=>value.replace(/\n/g,'\\u000a');
  return {before:{path:'/first/receive',target:shown(before)},after:{path:targetChange?'/first/receive':'/second/receive',target:shown(after)},top:after==='_self',sink:after==='_self'?null:after};
}
const attribute=value=>value.replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/\n/g,'&#10;');
export function destinationPage(url){
  const source=url.searchParams.get('source'),frame=url.searchParams.get('frame'),change=url.searchParams.get('change'),id=url.searchParams.get('id');
  const names=sinkNames(change),relative='receive?case='+encodeURIComponent(id);
  const decoy=change==='decoy-target'?'<svg width="1" height="1"><base target="sink-first"/></svg>':'';
  const base=decoy+`<base id="destination-base" href="/first/" target="${attribute(names.first)}">`;
  let content;
  if(source==='a')content=`<a id="asking" href="${relative}">Delete</a>`;
  else if(source==='area')content=`<img alt="Map" usemap="#map" width="160" height="70" src="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22160%22 height=%2270%22%3E%3Crect width=%22160%22 height=%2270%22/%3E%3C/svg%3E"><map name="map"><area id="asking" alt="Delete" href="${relative}" shape="rect" coords="0,0,160,70"></map>`;
  else if(source.startsWith('svg'))content=`<svg width="160" height="70" xmlns:xlink="http://www.w3.org/1999/xlink"><a id="asking" aria-label="Delete" ${change==='svg-self'?'':change==='xlink-show'?'xlink:show="new"':'target="sink-first"'} ${source==='svg-xlink'?'xlink:href':'href'}="${relative}"><rect width="160" height="70"/><text x="10" y="35">Delete</text></a></svg>`;
  else{
    const control=source==='input-formaction'?`<input type="submit" value="Delete"`:`<button type="submit"`;
    const ending=source==='input-formaction'?'>':'>Delete</button>';
    content=`<form id="first" method="post" action="${relative}"><input name="draft" value="Destination fixture"></form><form id="second" method="post" action="/second/${relative}"></form>${change==='owner-target'?`<form method="post" id="third" target="sink-second" action="${relative}"></form>`:''}${control} id="asking" form="first"${source==='form-action'?'':` formaction="${relative}"`}${ending}`;
  }
  if(change==='empty-target')content=source==='form-action'?content.replace('<form id="first"','<form id="first" target=""'):content.replace('id="asking"',source==='button-formaction'?'id="asking" formtarget=""':'id="asking" target=""');
  if(frame!=='top')content=content.replaceAll('id="asking"','id="asking" target="sink-first"').replaceAll('<form id=','<form target="sink-first" id=');
  const sinks=`<iframe name="${attribute(names.first)}" src="/?case=destination-sink&name=first" hidden></iframe><iframe name="${attribute(names.second)}" src="/?case=destination-sink&name=second" hidden></iframe>`;
  const body=base+(frame==='top'?content+sinks:'<iframe id="inline" width="700" height="350"></iframe>'+sinks);
  const script=`const child=${frame==='top'?'null':"document.querySelector('#inline')"};
    ${frame==='srcdoc'?`child.srcdoc=${JSON.stringify(content)};`:frame==='blank'?`child.contentDocument.body.innerHTML=${JSON.stringify(content)};`:''}
    globalThis.reviewChange=()=>{
      const doc=child?child.contentDocument:document,node=doc.querySelector('#asking');
      ${change.startsWith('animation')?`const animation=doc.createElementNS('http://www.w3.org/2000/svg','set');animation.setAttribute('attributeName',${JSON.stringify(change==='animation-target'?'target':source==='svg-xlink'?'xlink:href':'href')});animation.setAttribute('to',${JSON.stringify(change==='animation-target'?'sink-second':'/second/'+relative)});animation.setAttribute('dur','indefinite');node.append(animation);animation.beginElement();`:(change==='base'||change==='svg-self')?(frame==='top'?"document.querySelector('#destination-base').href='/second/';":"const base=doc.createElement('base');base.href='http://fixture.test:8765/second/';doc.head.prepend(base);"):change==='xlink-show'?"node.removeAttributeNS('http://www.w3.org/1999/xlink','show');":change==='owner-target'?"node.setAttribute('form','third');":change==='target'&&source.startsWith('svg')?"node.setAttribute('target','sink-second');":change.endsWith('target')&&change!=='target'?`document.querySelector('#destination-base').target=${JSON.stringify(names.second)};`:change==='target'?(frame==='top'?"document.querySelector('#destination-base').target='sink-second';":['a','area'].includes(source)?"node.setAttribute('target','sink-second');":source==='form-action'?"doc.querySelector('#first').setAttribute('target','sink-second');":"node.setAttribute('formtarget','sink-second');"):change==='owner'?"node.setAttribute('form','second');node.removeAttribute('formaction');":source==='form-action'?`doc.querySelector('#first').setAttribute('action','/second/${relative}');`:source.includes('formaction')?`node.setAttribute('formaction','/second/${relative}');`:source==='svg-xlink'?`node.setAttributeNS('http://www.w3.org/1999/xlink','xlink:href','/second/${relative}');`:`node.setAttribute('href','/second/${relative}');`}
    };`;
  return {body,script};
}
